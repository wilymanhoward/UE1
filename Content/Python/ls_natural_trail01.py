"""Naturalise the existing opening and Trail 01 without rebuilding terrain or crossings."""
import json
import math
from pathlib import Path
import shutil
import unreal

HINT='Follow the music notes. Press Space to hop over fallen branches.'
SPRING_HINT='Jump onto the springcap to reach the high music note.'


def point(trail,s,d=0):
    i=min(max(int(s//200),0),len(trail)-2)
    a,b=trail[i],trail[i+1]
    t=(s-i*200)/200
    yaw=math.atan2(b[1]-a[1],b[0]-a[0])
    return ((1-t)*a[0]+t*b[0]-d*math.sin(yaw),(1-t)*a[1]+t*b[1]+d*math.cos(yaw),
            (1-t)*a[2]+t*b[2]-.03*abs(d),math.degrees(yaw))


def patch_plan(plan):
    """Old cached plans must not bring back the removed mushrooms or their unreachable note."""
    trail=plan['trail']
    plan['actors']=[e for e in plan['actors'] if not (e['kind']=='mushroom' and e.get('s',0)<10000)]
    for e in plan['actors']:
        if e['kind']=='note' and 1900<e.get('s',0)<2100 and e.get('raised'):
            e['z']=point(trail,e['s'],e.get('d',150))[2]+80
            e.pop('raised',None)
        if 'giant mushroom' in str(e.get('message','')).lower(): e['message']=HINT
        if e['kind']=='mushroom':e['scale']=.6
    for kind,s,d in [('fallen_log',3000,-100),('block',3800,240),('block',4600,-240)]:
        if any(e['kind']==kind and e.get('s')==s for e in plan['actors']):continue
        x,y,z,yaw=point(trail,s,d)
        e=dict(kind=kind,s=s,d=d,x=x,y=y,z=z,yaw=yaw,name='Opening',extra='fun')
        if kind=='fallen_log':e.update(length=500,height=55,lean=-18)
        else:e.update(z=z+65,length=240,width=220,depth=200)
        plan['actors'].append(e)
    mushrooms=[e for e in plan['actors'] if e['kind']=='mushroom']
    if mushrooms and not any(e.get('message')==SPRING_HINT for e in plan['actors']):
        s=min(e['s'] for e in mushrooms)-700
        x,y,z,yaw=point(trail,s)
        plan['actors'].append(dict(kind='tutorial',s=s,x=x,y=y,z=z+200,yaw=yaw,message=SPRING_HINT,half=[300,390,300],extra='fun'))
    return plan


def build():
    import build_level1_wildwood as builder
    world=builder.require_map()
    editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages(), 'Save existing map edits first.'
    actors=list(editor.get_all_level_actors())
    notes=unreal.GameplayStatics.get_all_actors_of_class(world,unreal.LifeNote)
    before_notes=len(notes)
    plan=builder.load_plan()
    trail=plan['trail']
    backup=Path(unreal.Paths.project_saved_dir())/'BeforeNaturalTrail01'
    backup.mkdir(exist_ok=True)
    source=Path(unreal.Paths.project_content_dir())/'LastSeed/Maps/L_Level1_Wildwood.umap'
    if not (backup/source.name).exists():shutil.copy2(source,backup/source.name)
    old_mushrooms=[a for a in actors if isinstance(a,unreal.BounceMushroom)]
    early=[a for a in old_mushrooms if a.get_actor_location().x< -20000]
    for actor in early:assert editor.destroy_actor(actor)
    actors=[a for a in actors if a not in early]
    for actor in old_mushrooms:
        if actor in early:continue
        actor.set_actor_scale3d(unreal.Vector(.6,.6,.6))
        for component in actor.get_components_by_class(unreal.StaticMeshComponent):component.set_render_custom_depth(False)
    for actor in actors:
        if isinstance(actor,unreal.TutorialTrigger) and 'giant mushroom' in str(actor.get_editor_property('message')).lower():
            actor.set_editor_property('message',unreal.Text(HINT))
    first=point(trail,2000,150)
    note=min(notes,key=lambda a:(a.get_actor_location().x-first[0])**2+(a.get_actor_location().y-first[1])**2)
    location=note.get_actor_location()
    assert math.hypot(location.x-first[0],location.y-first[1])<200
    note.set_actor_location(unreal.Vector(first[0],first[1],first[2]+80),False,False)
    replaced=0
    for actor in actors:
        if not actor.get_actor_label().startswith('Trail01_'):continue
        component=actor.get_component_by_class(unreal.StaticMeshComponent)
        if not component or not component.static_mesh or '/Stylized_PBR_Nature/' not in component.static_mesh.get_path_name():continue
        center,_,_=unreal.SystemLibrary.get_component_bounds(component)
        old=component.static_mesh.get_bounds().box_extent
        mesh=unreal.load_asset(builder.mesh('SM_Boulder_08'))
        new=mesh.get_bounds().box_extent
        scale=actor.get_actor_scale3d()
        component.set_static_mesh(mesh)
        component.set_editor_property('override_materials',[])
        actor.set_actor_scale3d(unreal.Vector(scale.x*old.x/new.x,scale.y*old.y/new.y,scale.z*old.z/new.z))
        after,_,_=unreal.SystemLibrary.get_component_bounds(component)
        actor.set_actor_location(actor.get_actor_location()+center-after,False,False)
        replaced+=1
    for label,s,d,rise,length,lean in [
        ('Trail01_WarmupLog',16250,0,90,1040,-12),
        ('Trail01_DiagonalRight',21150,160,85,650,-25),
        ('Trail01_DiagonalLeft',22450,-160,85,650,25),
        ('Trail01_ExitLog',25800,0,80,1040,-8)]:
        actor=next((a for a in actors if a.get_actor_label()==label),None)
        if actor is None:continue
        component=actor.static_mesh_component
        bounds=component.static_mesh.get_bounds().box_extent
        x,y,z,yaw=point(trail,s,d)
        actor.set_actor_rotation(unreal.Rotator(pitch=0,yaw=yaw+90+lean,roll=0),False)
        actor.set_actor_scale3d(unreal.Vector(length/(2*bounds.x),130/(2*bounds.y),130/(2*bounds.z)))
        center,extent,_=unreal.SystemLibrary.get_component_bounds(component)
        actor.set_actor_location(actor.get_actor_location()+unreal.Vector(x-center.x,y-center.y,z+rise-center.z-extent.z),False,False)
    def ensure(entry,label):
        existing=next((a for a in editor.get_all_level_actors() if a.get_actor_label()==label),None)
        if existing:return existing
        for a in editor.get_all_level_actors():
            if not a.get_actor_label().startswith('Opening'):continue
            c=a.get_component_by_class(unreal.StaticMeshComponent)
            if c:
                center,_,_=unreal.SystemLibrary.get_component_bounds(c)
                if math.hypot(center.x-entry['x'],center.y-entry['y'])<100:
                    a.set_actor_label(label)
                    return a
        before=set(a.get_name() for a in editor.get_all_level_actors())
        builder.place(entry,{})
        created=[a for a in editor.get_all_level_actors() if a.get_name() not in before]
        assert len(created)==1,(label,len(created))
        created[0].set_actor_label(label)
        return created[0]
    for kind,s,label in [('fallen_log',3000,'Trail01_OpeningBranch'),('block',3800,'Trail01_OpeningRockRight'),('block',4600,'Trail01_OpeningRockLeft')]:
        entry=next(e for e in plan['actors'] if e['kind']==kind and e.get('s')==s)
        ensure(entry,label)
    hint=next((e for e in plan['actors'] if e.get('message')==SPRING_HINT),None)
    if hint and not any(isinstance(a,unreal.TutorialTrigger) and str(a.get_editor_property('message'))==SPRING_HINT for a in actors):
        ensure(hint,'SpringcapTutorial')
    grounds=[a for a in actors if isinstance(a,unreal.LandscapeProxy) or a.get_actor_label().startswith('SM_LS_WildwoodTrail')]
    ignore=[a for a in editor.get_all_level_actors() if a not in grounds]
    def decor(label,asset,s,d,height,yaw):
        if any(a.get_actor_label()==label for a in editor.get_all_level_actors()):return
        x,y,z,_=point(trail,s,d)
        hit=unreal.SystemLibrary.line_trace_single(world,unreal.Vector(x,y,z+1200),unreal.Vector(x,y,z-3000),
            unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,False,ignore,unreal.DrawDebugTrace.NONE,True)
        assert hit and hit.to_tuple()[0],label
        mesh=unreal.load_asset(builder.mesh(asset))
        bounds=mesh.get_bounds()
        scale=height/(2*bounds.box_extent.z)
        actor=builder.mesh_actor(mesh.get_path_name(),x,y,hit.to_tuple()[4].z-(bounds.origin.z-bounds.box_extent.z)*scale-3,
            'Scenery/Trail01',(scale,scale,scale),yaw,label=label)
        actor.static_mesh_component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        actor.static_mesh_component.set_render_custom_depth(False)
        ignore.append(actor)
    for k,(s,d) in enumerate([(2200,560),(7000,-560),(16900,600),(20800,-600)]):
        for j in range(3):decor(f'Trail01_ForestMushrooms_{k}_{j}','SM_Mushroom_Brown_02',s+j*30,d+(j%2)*35,10+j*4,k*73+j*51)
    for k,(s,d) in enumerate([(4200,620),(17800,-650),(19900,650),(23600,650)]):
        for j in range(2):decor(f'Trail01_ShoulderStones_{k}_{j}',f'SM_Boulder_{7+(k+j)%4:02d}',s+j*70,d+j*45,35+j*20,k*41+j*113)
    assert len(unreal.GameplayStatics.get_all_actors_of_class(world,unreal.LifeNote))==before_notes
    assert all(a.get_actor_location().x> -20000 for a in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.BounceMushroom))
    assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    print('Natural Trail 01 saved:',len(early),'early bounce mushrooms removed;',replaced,'mismatched rocks replaced; first note reachable; small shoulder decorations added.')
