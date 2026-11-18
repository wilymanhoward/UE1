"""One-time layout migration for the existing Wildwood map; preserve hand-placed rocks.

The full rebuild layout lives in ls_wildwood_plan.trail01_extras. This migration
moves the existing actors instead of rebuilding the landscape or its foliage.
"""
import json
import math
from pathlib import Path
import shutil
import unreal

TAG = 'LS_Trail01_Rework'
# Existing group, previous plan distance, new distance/side/rise, footprint scale, log lean.
BEATS = [
    ('WarmupLog', [613], 16400, 16250, 0, 90, 1, -12),
    ('SlalomLeft', [615], 18200, 17650, -210, 120, .9, None),
    ('SlalomRight', [617], 18800, 18750, 210, 130, .9, None),
    ('HopRock', [619,620], 19400, 19650, 0, 110, 1, None),
    ('DiagonalRight', [622], 20650, 21150, 160, 85, 1, -25),
    ('DiagonalLeft', [624], 21250, 22450, -160, 85, 1, 25),
    ('RaisedEntry', [626,627,628], 22550, 23550, 180, 70, .615384615, None),
    ('RaisedPeak', [630,631,632], 22850, 24000, 180, 145, .615384615, None),
    ('RaisedExit', [634,635,636], 23150, 24450, 180, 70, .615384615, None),
    ('ExitLog', [638], 25500, 25800, 0, 80, 1, -8),
]
REWARDS = [(21150,160,200), (24000,180,230)]


def build():
    editor = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    assert world.get_path_name().split('.')[0] == '/Game/LastSeed/Maps/L_Level1_Wildwood'
    actors = {a.get_name(): a for a in editor.get_all_level_actors()}
    names = ['StaticMeshActor_'+str(i) for beat in BEATS for i in beat[1]]
    assert len(names) == 17 and len(set(names)) == 17
    assert all(n in actors and isinstance(actors[n], unreal.StaticMeshActor) for n in names)
    marked = [n for n in names if TAG in map(str, actors[n].tags)]
    if marked:
        assert len(marked) == len(names), 'Partial migration; inspect Saved/Trail01Before before continuing'
        print('Trail01 layout already applied.')
        return
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages(), 'Save existing map edits first'
    plan = json.loads((Path(unreal.Paths.project_saved_dir())/'LS/plan.json').read_text())
    trail = plan['trail']
    entries = {int(e['s']): e for e in plan['actors'] if e.get('extra') == 'trail01'}

    def point(s, d=0):
        i = min(int(s//200),len(trail)-2)
        a,b = trail[i],trail[i+1]
        t = (s-i*200)/200
        angle = math.atan2(b[1]-a[1],b[0]-a[0])
        return ((1-t)*a[0]+t*b[0]-d*math.sin(angle),
                (1-t)*a[1]+t*b[1]+d*math.cos(angle),
                (1-t)*a[2]+t*b[2]-.03*abs(d), math.degrees(angle))

    backup = Path(unreal.Paths.project_saved_dir())/'Trail01Before'
    backup.mkdir(exist_ok=True)
    source = Path(unreal.Paths.project_content_dir())/'LastSeed/Maps/L_Level1_Wildwood.umap'
    if not (backup/source.name).exists(): shutil.copy2(source,backup/source.name)
    before = []
    for name in names:
        actor=actors[name]
        assert actor.static_mesh_component.get_collision_profile_name() == 'BlockAll'
        loc,rot,scale=actor.get_actor_location(),actor.get_actor_rotation(),actor.get_actor_scale3d()
        before.append(dict(name=name,label=actor.get_actor_label(),location=[loc.x,loc.y,loc.z],
                           rotation=[rot.pitch,rot.yaw,rot.roll],scale=[scale.x,scale.y,scale.z]))
    (backup/'actors.json').write_text(json.dumps(before,indent=2))

    for title,ids,old_s,s,d,rise,factor,lean in BEATS:
        old=entries[old_s]
        x,y,z,yaw=point(s,d)
        delta=math.radians(yaw-old['yaw'])
        for index,number in enumerate(ids):
            actor=actors['StaticMeshActor_'+str(number)]
            component=actor.static_mesh_component
            center,extent,_=unreal.SystemLibrary.get_component_bounds(component)
            dx,dy=(center.x-old['x'])*factor,(center.y-old['y'])*factor
            target_x=x+dx*math.cos(delta)-dy*math.sin(delta)
            target_y=y+dx*math.sin(delta)+dy*math.cos(delta)
            scale=actor.get_actor_scale3d()
            if lean is not None:
                scale.x *= 650/1040 if 'Diagonal' in title else 1
                new_yaw=yaw+90+lean
            else:
                scale*=factor
                new_yaw=actor.get_actor_rotation().yaw+math.degrees(delta)
            actor.set_actor_scale3d(scale)
            actor.set_actor_rotation(unreal.Rotator(pitch=0,yaw=new_yaw,roll=0),True)
            center,extent,_=unreal.SystemLibrary.get_component_bounds(component)
            loc=actor.get_actor_location()
            actor.set_actor_location(unreal.Vector(loc.x+target_x-center.x,loc.y+target_y-center.y,
                                    loc.z+z+rise-center.z-extent.z),False,True)
            actor.set_actor_label('Trail01_'+title+('_'+str(index+1) if len(ids)>1 else ''))
            actor.tags=list(actor.tags)+[TAG]

    import build_level1_wildwood as builder
    previous=set(a.get_name() for a in editor.get_all_level_actors())
    for s,d,lift in REWARDS:
        x,y,z,yaw=point(s,d)
        builder.place(dict(kind='petal',x=x,y=y,z=z+lift,yaw=yaw),{})
    rewards=[a for a in editor.get_all_level_actors() if a.get_name() not in previous]
    assert len(rewards)==2 and all(isinstance(a,unreal.GoldenPetal) for a in rewards)
    for i,a in enumerate(rewards):
        a.tags=list(a.tags)+['LS_Extra',TAG]
        a.set_actor_label('Trail01_OptionalPetal_'+str(i+1))
    actors['TutorialTrigger_12'].set_editor_property('message',unreal.Text(
        'Jump the log, weave between the rocks, then choose your line. Raised routes hold Golden Petals.'))
    assert len(unreal.GameplayStatics.get_all_actors_of_class(world,unreal.LifeNote))==20
    assert all(actors[n].static_mesh_component.get_collision_profile_name()=='BlockAll' for n in names)
    review = [dict(beat=b[0],s=b[3],side=b[4],rise=b[5],point=point(b[3],b[4])) for b in BEATS]
    (backup/'layout_review.json').write_text(json.dumps(review,indent=2))
    assert unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True,False)
    print('Trail01 saved: 17 obstacles repositioned, 2 optional petals, 20 Life Notes preserved.')


if __name__=='__main__': build()
