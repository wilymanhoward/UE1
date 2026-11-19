"""Remove unsupported grass beside the first crossing without moving any level actors."""
import json
from pathlib import Path
import shutil
import unreal


def build():
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
    backup=Path(unreal.Paths.project_saved_dir())/'BeforeFloatingCrossingFix'
    backup.mkdir(exist_ok=True)
    source=Path(unreal.Paths.project_content_dir())/'LastSeed/Maps/L_Level1_Wildwood.umap'
    if not (backup/source.name).exists():shutil.copy2(source,backup/source.name)
    supports=[]
    for actor in actors:
        component=actor.get_component_by_class(unreal.StaticMeshComponent)
        if isinstance(actor,unreal.LandscapeProxy) or (component and component.static_mesh and component.static_mesh.get_name().startswith('SM_Boulder_')):
            supports.append(actor)
    ignore=[a for a in actors if a not in supports]
    box=unreal.Box(min=unreal.Vector(-17700,-6600,1500),max=unreal.Vector(-15800,-5500,4300))
    removed=[]
    for actor in actors:
        for component in actor.get_components_by_class(unreal.InstancedStaticMeshComponent):
            if not component.static_mesh or component.static_mesh.get_name()!='SM_Grass_01':continue
            indices=[]
            for i in component.get_instances_overlapping_box(box,True):
                pose=component.get_instance_transform(i,world_space=True)
                p=pose.translation
                if not (-17700<p.x< -15800 and -6600<p.y< -5500):continue
                hit=unreal.SystemLibrary.line_trace_single(world,p+unreal.Vector(0,0,100),unreal.Vector(p.x,p.y,500),
                    unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,False,ignore,unreal.DrawDebugTrace.NONE,True)
                if not hit or not hit.to_tuple()[0]:continue
                gap=p.z-hit.to_tuple()[4].z
                if gap<=60:continue
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
