"""Traverse the collapsing crossing with Seed inputs, then verify a complete death reset."""
import json
import math
from pathlib import Path
import unreal

editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world=editor.get_game_world()
assert world
for intro in unreal.ObjectIterator(unreal.LSIntroWidget):
    if intro.is_in_viewport(): intro.call_method('Finish',())
pc=unreal.GameplayStatics.get_player_controller(world,0)
pawn=unreal.GameplayStatics.get_player_pawn(world,0)
assert pawn.get_current_form()==unreal.SeedForm.SEED
body=next(c for c in pawn.get_components_by_class(unreal.StaticMeshComponent) if c.get_name()=='BallMesh')
caps=sorted([a for a in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.StaticMeshActor)
             if a.get_component_by_class(unreal.CollapsingStoneComponent)],key=lambda a:a.get_actor_location().x)
caps=[a for a in caps if a.get_actor_label().startswith('PillarRock')]
platforms=sorted([a for a in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.Actor)
                  if a.get_component_by_class(unreal.CollapsingStoneComponent)],key=lambda a:a.get_actor_location().x)
components=[a.get_component_by_class(unreal.CollapsingStoneComponent) for a in platforms]
assert len(caps)==4 and len(platforms)==6 and all(not c.is_collapsing() for c in components)
groups=[list(c.get_editor_property('support_actors'))+[a] for a,c in zip(platforms,components)]
original={a:a.get_actor_location() for g in groups for a in g}
nodes=[(a.get_actor_location().x,a.get_actor_location().y) for a in caps]+[(-13000,-6900)]
actions={a.get_name():a for a in unreal.ObjectIterator(unreal.InputAction) if a.get_outer()==pc}
subsystem=next(s for s in unreal.ObjectIterator(unreal.EnhancedInputLocalPlayerSubsystem)
               if isinstance(s.get_outer(),unreal.LocalPlayer))
center,extent,_=unreal.SystemLibrary.get_component_bounds(caps[0].static_mesh_component)
pawn.set_actor_location(unreal.Vector(center.x-150,center.y,center.z+extent.z+53),False,True)
body.set_physics_linear_velocity(unreal.Vector(0,0,0));body.set_physics_angular_velocity_in_radians(unreal.Vector(0,0,0))
began=unreal.GameplayStatics.get_time_seconds(world)
state={'jumps':[],'wood_contacts':{},'samples':[],'bank_time':None,'death_time':None}
output=Path(unreal.Paths.project_saved_dir())/'Screenshots/CollapsingCrossing'
output.mkdir(parents=True,exist_ok=True)


def stop(success,reason):
    subsystem.inject_input_vector_for_action(actions['InputAction_0'],unreal.Vector(0,0,0),[],[])
    body.set_physics_linear_velocity(unreal.Vector(0,0,0));body.set_physics_angular_velocity_in_radians(unreal.Vector(0,0,0))
    unreal.unregister_slate_post_tick_callback(handle)
    (output/'traversal.json').write_text(json.dumps(dict(success=success,reason=reason,**state),indent=2))
    assert success,reason
    print('COLLAPSING_CROSSING_TRAVERSAL_PASSED:',reason)


def drive(delta):
    if not editor.get_game_world():unreal.unregister_slate_post_tick_callback(handle);return
    t=unreal.GameplayStatics.get_time_seconds(world)-began
    pos=pawn.get_actor_location()
    if state['death_time'] is not None:
        if t-state['death_time']>1.4:
            for actor,start in original.items():
                assert unreal.MathLibrary.vector_distance(actor.get_actor_location(),start)<.1
                assert actor.get_actor_enable_collision() and not actor.get_editor_property('hidden')
            stop(True,'crossed using Seed inputs, both logs collapsed, all platforms rebuilt after death')
        return
    if state['bank_time'] is not None:
        body.set_physics_linear_velocity(unreal.Vector(0,0,0));body.set_physics_angular_velocity_in_radians(unreal.Vector(0,0,0))
        if t-state['bank_time']>4:
            # A fast jump can skip a stone; only platforms actually touched should fall.
            assert all(c.is_collapsing() and a.get_editor_property('hidden')
                       for a,c in zip(platforms,components) if a not in caps)
            state['death_time']=t;pawn.die()
        return
    if pawn.is_dead() or pos.z<2500 or t>35:stop(False,'fell or did not reach the far bank');return
    if pos.x>=-13000:
        state['bank_time']=t
        subsystem.inject_input_vector_for_action(actions['InputAction_0'],unreal.Vector(0,0,0),[],[])
        return
    target_x=pos.x+220
    for a,b in zip(nodes,nodes[1:]):
        if a[0]<=target_x<=b[0]:
            target_y=a[1]+(b[1]-a[1])*(target_x-a[0])/(b[0]-a[0]);break
    else: target_y=nodes[0][1] if target_x<nodes[0][0] else nodes[-1][1]
    dx,dy=target_x-pos.x,target_y-pos.y;length=math.hypot(dx,dy);velocity=pawn.get_velocity()
    ax,ay=(dx/length*550-velocity.x)/350,(dy/length*550-velocity.y)/350
    magnitude=max(1,math.hypot(ax,ay));ax/=magnitude;ay/=magnitude
    pc.set_control_rotation(unreal.Rotator(pitch=-20,yaw=0,roll=0))
    subsystem.inject_input_vector_for_action(actions['InputAction_0'],unreal.Vector(ay,ax,0),[],[])
    jump=False
    for i in range(4):
        if i not in state['jumps'] and nodes[i][0]-70<=pos.x<nodes[i][0]+120 and pawn.is_grounded():
            state['jumps'].append(i);jump=True;break
    for actor,component in zip(platforms,components):
        if actor in caps or not component.is_shaking(): continue
        name=actor.get_name()
        state['wood_contacts'].setdefault(name,t)
        if name not in state['jumps'] and t-state['wood_contacts'][name]>.85 and pawn.is_grounded():
            state['jumps'].append(name);jump=True
    subsystem.inject_input_vector_for_action(actions['InputAction_2'],unreal.Vector(1 if jump else 0,0,0),[],[])
    if not state['samples'] or t-state['samples'][-1]['time']>.2:
        state['samples'].append(dict(time=round(t,2),x=round(pos.x),y=round(pos.y),z=round(pos.z),
                                     collapsed=[c.is_collapsing() for c in components]))


handle=unreal.register_slate_post_tick_callback(drive)
print('Started collapsing crossing traversal with real Seed inputs.')
