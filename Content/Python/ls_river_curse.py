"""Repeated, jumpable green shockwaves along the far-bank trail."""
import math
from pathlib import Path
import unreal

FOLDER = '/Game/LastSeed/Materials'
BEND = 650.0
HALF_WIDTH = 1400.0


def crescent_mesh():
    from ls_generate_player_meshes import Mesh, write_obj
    path='/Game/LastSeed/Generated/SM_LS_CurseCrescent'
    if unreal.EditorAssetLibrary.does_asset_exist(path): return unreal.load_asset(path)
    mesh=Mesh()
    # Upright wisps and a horizontal energy skirt keep the arc visible from the rolling camera and above.
    for upright in (True,False):
        start=len(mesh.points)
        for i in range(97):
            v=i/96
            y=(v*2-1)*HALF_WIDTH
            x=-BEND*(y/HALF_WIDTH)**2
            for u in (0.0,1.0):
                mesh.points.append((x if upright else x+(u-.5)*190,y,(u-.5)*220 if upright else 0))
                mesh.uvs.append((u,v))
            if i:
                a=start+(i-1)*2
                mesh.triangles.extend([(a,a+1,a+2),(a+1,a+3,a+2)])
    mesh.smooth_normals()
    assert abs(mesh.points[0][0]+BEND)<.01 and abs(mesh.points[96][0])<.01
    source=Path(unreal.Paths.project_content_dir())/'LastSeed/SourceMeshes/SM_LS_CurseCrescent.obj'
    source.parent.mkdir(parents=True,exist_ok=True)
    write_obj(str(source),mesh)
    task=unreal.AssetImportTask()
    task.filename=str(source)
    task.destination_path='/Game/LastSeed/Generated'
    task.destination_name='SM_LS_CurseCrescent'
    task.automated=True
    task.save=True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    result=unreal.load_asset(path)
    assert result and abs(result.get_bounds().box_extent.y-HALF_WIDTH)<1
    nanite=result.get_editor_property('nanite_settings')
    nanite.set_editor_property('enabled',False)
    unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).set_nanite_settings(result,nanite,True)
    return result


def material():
    path = FOLDER + '/M_LS_RiverCurse'
    edit = unreal.MaterialEditingLibrary
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        mat=unreal.load_asset(path)
        edit.delete_all_material_expressions(mat)
    else:
        mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_LS_RiverCurse', FOLDER, unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_properties({'blend_mode': unreal.BlendMode.BLEND_TRANSLUCENT, 'two_sided': True, 'allow_translucent_custom_depth_writes':True,
                               'opacity_mask_clip_value':.333,
                               'shading_model': unreal.MaterialShadingModel.MSM_UNLIT})
    uv = edit.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -500, 0)
    clock = edit.create_material_expression(mat, unreal.MaterialExpressionTime, -500, 200)
    custom = edit.create_material_expression(mat, unreal.MaterialExpressionCustom, -200, 0)
    pins = []
    for name,node in [('UV',uv),('Time',clock)]:
        pin = unreal.CustomInput()
        pin.set_editor_property('input_name',name)
        pins.append(pin)
    custom.set_editor_properties({'inputs':pins,'output_type':unreal.CustomMaterialOutputType.CMOT_FLOAT4,
        'code': '''struct CurseNoise {
 float hash(float2 q) { return frac(sin(dot(q,float2(127.1,311.7)))*43758.5453); }
 float noise(float2 q) {
  float2 i=floor(q), f=frac(q); f=f*f*(3-2*f);
  return lerp(lerp(hash(i),hash(i+float2(1,0)),f.x),lerp(hash(i+float2(0,1)),hash(i+1),f.x),f.y);
 }
 float flow(float2 q) { return .57*noise(q)+.28*noise(q*2.07+17)+.15*noise(q*4.13-11); }
};
CurseNoise N;
float2 p=UV;
float warp=N.flow(float2(p.y*17,p.x*4-Time*.6));
float ribbon=p.x-.5+(warp-.5)*.24;
float n=N.flow(float2(p.y*105+warp*5,p.x*7-Time*1.8));
float core=exp(-pow(ribbon/.06,2))*smoothstep(.22,.7,n);
float wisps=exp(-abs(ribbon)*5)*pow(saturate(n*1.5),3);
float2 grid=float2(p.y*210,p.x*15-Time*2.1);
float2 cell=floor(grid);
float hash=N.hash(cell);
float2 center=float2(.2+.6*hash,.2+.6*frac(hash*7.3));
float mote=(1-smoothstep(.045,.17,length(frac(grid)-center)))*step(.38,hash);
mote*=exp(-abs(p.x-.5)*3);
float edge=(1-smoothstep(.42,.5,abs(p.y-.5)))*(1-smoothstep(.4,.5,abs(p.x-.5)));
float alpha=edge*saturate(core*.5+wisps*1.2+mote);
float3 green=lerp(float3(.003,.08,.018),float3(.015,.85,.18),saturate(core+wisps));
float3 spark=lerp(float3(.06,1.5,.45),float3(1.4,.55,.08),step(.97,hash));
return float4(lerp(green,spark,mote),alpha);'''})
    edit.connect_material_expressions(uv,'',custom,'UV')
    edit.connect_material_expressions(clock,'',custom,'Time')
    rgb = edit.create_material_expression(mat,unreal.MaterialExpressionComponentMask,50,0)
    rgb.set_editor_properties({'r':True,'g':True,'b':True,'a':False})
    alpha = edit.create_material_expression(mat,unreal.MaterialExpressionComponentMask,50,200)
    alpha.set_editor_properties({'r':False,'g':False,'b':False,'a':True})
    for node,prop in [(rgb,unreal.MaterialProperty.MP_EMISSIVE_COLOR),(alpha,unreal.MaterialProperty.MP_OPACITY)]:
        assert edit.connect_material_expressions(custom,'',node,'')
        assert edit.connect_material_property(node,'',prop)
    edit.recompile_material(mat)
    assert unreal.EditorAssetLibrary.save_loaded_asset(mat,False)
    return mat


def configure(story):
    import build_level1_wildwood as builder
    actors = builder.actors.get_all_level_actors()
    storm = next((a for a in actors if a.get_actor_label()=='RiverbankCurse'),None)
    if storm is None: storm=builder.spawn(unreal.WitheringStorm,14000,-2200,3300,'RiverbankCurse','Flow')
    route=[unreal.Vector(14000,-2200,3300),unreal.Vector(15000,-2200,3300),
           unreal.Vector(16700,-800,3200),unreal.Vector(19000,1300,3300)]
    # Follow the actual ground between bends so a low attack does not disappear under a slope.
    samples=[]
    for a,b in zip(route,route[1:]):
        steps=math.ceil(math.hypot(b.x-a.x,b.y-a.y)/200)
        samples.extend(a+(b-a)*(i/steps) for i in range(steps))
    route=samples+[route[-1]]
    world=builder.require_map()
    ground=[]
    for actor in actors:
        component=actor.get_component_by_class(unreal.StaticMeshComponent)
        if isinstance(actor,unreal.LandscapeProxy) or (component and component.static_mesh and
                component.static_mesh.get_name().startswith('SM_LS_WildwoodTrail')): ground.append(actor)
    ignore=[a for a in actors if a not in ground]
    for p in route:
        hit=unreal.SystemLibrary.line_trace_single(world,unreal.Vector(p.x,p.y,3100),unreal.Vector(p.x,p.y,1000),
            unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,False,ignore,unreal.DrawDebugTrace.NONE,True)
        assert hit and hit.to_tuple()[0], f'No trail below {p}'
        p.z=hit.to_tuple()[4].z
    storm.set_editor_properties({'chase_points':list(reversed(route)),'rise_speed':900.0,'note_pushback':0.0,'shockwave_attacks':True,
        'shockwave_bend':BEND,'shockwave_min_launch_distance':1050.0,
        'start_delay':2.0,'max_rise_distance':5200.0,'close_distance':1800.0,'respawn_clearance':1400.0})
    storm.get_editor_property('box').set_box_extent(unreal.Vector(70,1400,25),True)
    audio_path='/Game/LastSeed/Audio/SFX_LS_WitchAttackScream'
    if not unreal.EditorAssetLibrary.does_asset_exist(audio_path):
        task=unreal.AssetImportTask()
        task.filename=unreal.Paths.project_content_dir()+'LastSeed/SourceSounds/SFX_LS_WitchAttackScream.wav'
        task.destination_path='/Game/LastSeed/Audio'
        task.automated=True
        task.save=True
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        assert task.imported_object_paths
    storm.get_editor_property('attack_audio').set_sound(unreal.load_asset(audio_path))
    mesh=storm.get_editor_property('mesh')
    mesh.set_static_mesh(crescent_mesh())
    mesh.set_relative_location(unreal.Vector(0,0,0),False,False)
    mesh.set_relative_rotation(unreal.Rotator(),False,False)
    mesh.set_relative_scale3d(unreal.Vector(1,1,1))
    mesh.set_material(0,material())
    mesh.static_mesh.set_material(0,mesh.get_material(0))
    assert unreal.EditorAssetLibrary.save_loaded_asset(mesh.static_mesh,False)
    mesh.set_render_custom_depth(True)
    mesh.set_custom_depth_stencil_value(1)
    trees=[]
    # Trees in foliage batches need independent meshes before they can wither individually.
    for actor in actors:
        for component in actor.get_components_by_class(unreal.HierarchicalInstancedStaticMeshComponent):
            source=component.static_mesh
            if not source or not source.get_name().startswith('SM_Tree'): continue
            remove=[]
            for index in range(component.get_instance_count()):
                pose=component.get_instance_transform(index,world_space=True)
                p=pose.translation
                if not (14000<p.x<18500 and -3500<p.y<1300): continue
                closest=1e20
                for a,b in zip(route,route[1:]):
                    dx,dy=b.x-a.x,b.y-a.y
                    t=max(0,min(1,((p.x-a.x)*dx+(p.y-a.y)*dy)/(dx*dx+dy*dy)))
                    closest=min(closest,math.hypot(p.x-a.x-t*dx,p.y-a.y-t*dy))
                if closest>1400: continue
                tree=builder.restorable(p.x,p.y,p.z,pose.rotation.rotator().yaw,source.get_path_name(),pose.scale3d,
                    builder.mesh('SM_DeadTrunk_01'),1.0,threshold=2,folder='Regrowth/RiverCurse',label='RiverCurseFoliageTree')
                tree.set_editor_property('start_grown',True)
                trees.append(tree)
                remove.append(index)
            if remove: assert component.remove_instances(remove)
    trees += [a for a in actors if a.get_actor_label().startswith('RiverCurseFoliageTree')]
    for i,(x,y) in enumerate([(14500,-2950),(14600,-1350),(15600,-2800),(15700,-1100),(16400,-1800),(17100,-300)]):
        label=f'RiverCurseTree_{i+1}'
        tree=next((a for a in actors if a.get_actor_label()==label),None)
        if tree is None:
            world=builder.require_map()
            ignore=[a for a in actors if not isinstance(a,unreal.LandscapeProxy)]
            hit=unreal.SystemLibrary.line_trace_single(world,unreal.Vector(x,y,6000),unreal.Vector(x,y,1000),
                unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,False,ignore,unreal.DrawDebugTrace.NONE,True)
            assert hit and hit.to_tuple()[0]
            tree=builder.restorable(x,y,hit.to_tuple()[4].z,0,builder.mesh('SM_Tree_03'),.8,
                builder.mesh('SM_DeadTrunk_01'),1.0,threshold=2,folder='Regrowth/RiverCurse',label=label)
        tree.set_editor_property('start_grown',True)
        trees.append(tree)
    storm.set_editor_property('curse_trees',trees)
    story.set_editor_property('after_cutscene_curse',storm)
    return storm
