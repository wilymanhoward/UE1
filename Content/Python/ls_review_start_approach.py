"""PIE check: new spawn has trail underneath and rolls across the old entrance without jumping."""
import json
from pathlib import Path
import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert world
for intro in unreal.ObjectIterator(unreal.LSIntroWidget):
    if intro.is_in_viewport(): intro.call_method('Finish',())
pawn = unreal.GameplayStatics.get_player_pawn(world,0)
pc = unreal.GameplayStatics.get_player_controller(world,0)
start = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.PlayerStart))
forward = start.get_actor_forward_vector()
origin = unreal.Vector(-23000,17200,2671.0211)
body = next(c for c in pawn.get_components_by_class(unreal.StaticMeshComponent) if c.get_name() == 'BallMesh')
actions = {a.get_name():a for a in unreal.ObjectIterator(unreal.InputAction) if a.get_outer()==pc}
subsystem = next(s for s in unreal.ObjectIterator(unreal.EnhancedInputLocalPlayerSubsystem)
                 if isinstance(s.get_outer(),unreal.LocalPlayer))
output = Path(unreal.Paths.project_saved_dir())/'Screenshots/StartApproach'
output.mkdir(parents=True,exist_ok=True)
began = unreal.GameplayStatics.get_time_seconds(world)
samples = []


def review(_delta):
    if not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
        unreal.unregister_slate_post_tick_callback(handle)
        return
    t = unreal.GameplayStatics.get_time_seconds(world)-began
    p = pawn.get_actor_location()
    along = (p.x-origin.x)*forward.x+(p.y-origin.y)*forward.y
    try:
        assert not pawn.is_dead() and p.z > 2450
        hit = unreal.SystemLibrary.line_trace_single(world,p,p-unreal.Vector(0,0,300),
            unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,False,[pawn],unreal.DrawDebugTrace.NONE,True)
        assert hit and hit.to_tuple()[0], 'No collision surface beneath the Seed'
        assert 'WildwoodTrail' in hit.to_tuple()[9].get_actor_label(), hit.to_tuple()[9].get_actor_label()
        if t < 1:
            assert along < -1800, 'Spawn is not on the new approach'
        else:
            pc.set_control_rotation(unreal.Rotator(pitch=-20,yaw=start.get_actor_rotation().yaw))
            subsystem.inject_input_vector_for_action(actions['InputAction_0'],unreal.Vector(0,1,0),[],[])
        if not samples or t-samples[-1]['time']>.25:
            samples.append(dict(time=round(t,2),along=round(along),z=round(p.z,1),speed=round(pawn.get_velocity().length())))
        assert t < 16, 'Could not roll onto the original trail'
        if along > 350:
            subsystem.inject_input_vector_for_action(actions['InputAction_0'],unreal.Vector(0,0,0),[],[])
            body.set_physics_linear_velocity(unreal.Vector(0,0,0))
            body.set_physics_angular_velocity_in_radians(unreal.Vector(0,0,0))
            unreal.unregister_slate_post_tick_callback(handle)
            (output/'passed.json').write_text(json.dumps(samples,indent=2))
            print(f'START_APPROACH_PASSED: solid trail under spawn; rolled across seam without jumping in {t-1:.2f}s.')
    except Exception as error:
        subsystem.inject_input_vector_for_action(actions['InputAction_0'],unreal.Vector(0,0,0),[],[])
        unreal.unregister_slate_post_tick_callback(handle)
        (output/'failed.json').write_text(json.dumps(dict(error=str(error),samples=samples),indent=2))
        raise


handle = unreal.register_slate_post_tick_callback(review)
