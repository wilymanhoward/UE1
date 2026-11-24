"""Remove unsupported grass in the Wildwood crossing areas."""
import json
from pathlib import Path
import shutil
import unreal


FIRST_CROSSING = ((-17700, -6600, 1500, -15800, -5500, 4300),)
RIVERBANK = (
    (-15750, -8100, 2180, -15450, -7750, 4050),
    (-15850, -9350, 2180, -15200, -8650, 4050),
)


def build(bounds=FIRST_CROSSING, minimum_gap=60):
    editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    assert world.get_path_name().split('.')[0]=='/Game/LastSeed/Maps/L_Level1_Wildwood'
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages(), 'Save the current layout first.'
    actors=list(editor.get_all_level_actors())
    def poses():
        result={}
        for a in editor.get_all_level_actors():
            p,r,s=a.get_actor_location(),a.get_actor_rotation(),a.get_actor_scale3d()
            result[a.get_name()]=(p.x,p.y,p.z,r.pitch,r.yaw,r.roll,s.x,s.y,s.z)
        return result
    before=poses()
    backup_name = 'BeforeTrail01RiverbankGrassFix' if bounds == RIVERBANK else 'BeforeFloatingCrossingFix'
    backup=Path(unreal.Paths.project_saved_dir())/backup_name
    backup.mkdir(exist_ok=True)
    source=Path(unreal.Paths.project_content_dir())/'LastSeed/Maps/L_Level1_Wildwood.umap'
    if not (backup/source.name).exists():shutil.copy2(source,backup/source.name)
    supports=[]
    for actor in actors:
        component=actor.get_component_by_class(unreal.StaticMeshComponent)
        if isinstance(actor,unreal.LandscapeProxy) or (component and component.static_mesh and component.static_mesh.get_name().startswith('SM_Boulder_')):
            supports.append(actor)
    if bounds == RIVERBANK:
        supports.extend(a for a in actors if a.get_actor_label() == 'SM_LS_WildwoodTrail_01')
    ignore=[a for a in actors if a not in supports]
    boxes = [unreal.Box(min=unreal.Vector(*b[:3]), max=unreal.Vector(*b[3:])) for b in bounds]
    removed=[]
    for actor in actors:
        for component in actor.get_components_by_class(unreal.InstancedStaticMeshComponent):
            if not component.static_mesh or component.static_mesh.get_name()!='SM_Grass_01':continue
            indices=[]
            overlap = {i for box in boxes for i in component.get_instances_overlapping_box(box, True)}
            for i in overlap:
                pose=component.get_instance_transform(i,world_space=True)
                p=pose.translation
                if not any(x0<p.x<x1 and y0<p.y<y1 and z0<p.z<z1 for x0,y0,z0,x1,y1,z1 in bounds):continue
                hit=unreal.SystemLibrary.line_trace_single(world,p+unreal.Vector(0,0,100),unreal.Vector(p.x,p.y,500),
                    unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,bounds == RIVERBANK,ignore,unreal.DrawDebugTrace.NONE,True)
                if not hit or not hit.to_tuple()[0]:continue
                gap=p.z-hit.to_tuple()[4].z
                if gap<=minimum_gap:continue
                indices.append(i)
                removed.append(dict(actor=actor.get_name(),component=component.get_name(),index=i,
                    location=[p.x,p.y,p.z],gap=gap,transform=str(pose)))
            if indices:
                count=component.get_instance_count()
                assert component.remove_instances(sorted(indices,reverse=True))
                assert component.get_instance_count()==count-len(indices)
    assert before==poses(), 'An actor was moved during foliage cleanup.'
    if removed:
        (backup/'removed_grass.json').write_text(json.dumps(removed,indent=2))
        assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    print('Removed',len(removed),'unsupported grass instances; all actor transforms preserved.')
    return len(removed)


def fix_riverbank():
    return build(RIVERBANK, minimum_gap=90)
