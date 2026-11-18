"""PIE checks for departure timing, independent pillars, death reset and reuse."""
import json
from pathlib import Path
import unreal

editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world = editor.get_game_world()
assert world
for intro in unreal.ObjectIterator(unreal.LSIntroWidget):
    if intro.is_in_viewport(): intro.call_method('Finish', ())
pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
body = next(c for c in pawn.get_components_by_class(unreal.StaticMeshComponent) if c.get_name() == 'BallMesh')
safe = pawn.get_actor_location()
pawn.set_checkpoint(safe)
caps = sorted([a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.StaticMeshActor)
               if a.get_component_by_class(unreal.CollapsingStoneComponent)], key=lambda a: a.get_actor_location().x)
assert len(caps) == 4
components = [a.get_component_by_class(unreal.CollapsingStoneComponent) for a in caps]
groups = [list(c.get_editor_property('support_actors')) + [a] for a, c in zip(caps, components)]
original = {a: a.get_actor_transform() for group in groups for a in group}
positions = {a: a.get_actor_location() for a in original}
assert all(c.get_editor_property('collapse_delay') == 3 for c in components)
output = Path(unreal.Paths.project_saved_dir())/'Screenshots/CollapsingCrossing'
output.mkdir(parents=True, exist_ok=True)


def move(location):
    pawn.set_actor_location(location, False, True)
    body.set_physics_linear_velocity(unreal.Vector(0, 0, 0))
    body.set_physics_angular_velocity_in_radians(unreal.Vector(0, 0, 0))


def land(cap):
    center, extent, _ = unreal.SystemLibrary.get_component_bounds(cap.static_mesh_component)
    move(unreal.Vector(center.x, center.y, center.z + extent.z + 53))


def intact(group):
    for a in group:
        assert unreal.MathLibrary.vector_distance(a.get_actor_location(), positions[a]) < .1, a.get_name()
        assert a.get_actor_enable_collision(), a.get_name()
        assert not a.get_editor_property('hidden'), a.get_name()


land(caps[0])
began = unreal.GameplayStatics.get_time_seconds(world)
steps = [4.0, 6.8, 7.35, 8.25, 11.05, 11.65, 12.6, 14.0, 14.6, 17.9, 19.3, 23.0]
samples = []


def review(_delta):
    if not editor.get_game_world(): unreal.unregister_slate_post_tick_callback(handle); return
    elapsed = unreal.GameplayStatics.get_time_seconds(world) - began
    # Counter the rock's slight slope during the stationary timing checks.
    if elapsed < 8.25:
        body.set_physics_linear_velocity(unreal.Vector(0, 0, 0))
        body.set_physics_angular_velocity_in_radians(unreal.Vector(0, 0, 0))
    if elapsed < steps[0]: return
    step = steps.pop(0)
    try:
        if step < 12.6: assert not pawn.is_dead(), 'Unexpected fall during the timing setup'
        if step == 4.0:
            intact(groups[0])
            assert not components[0].is_collapsing(), 'Standing on a cap must not start collapse'
            land(caps[1])
        elif step == 6.8:
            intact(groups[0])
            assert not components[0].is_collapsing(), 'Departure delay must last three seconds'
        elif step == 7.35:
            assert components[0].is_collapsing()
            assert caps[0].get_actor_location().z < positions[caps[0]].z - 1
            intact(groups[1])
            assert not components[1].is_collapsing()
        elif step == 8.25:
            assert all(a.get_editor_property('hidden') and not a.get_actor_enable_collision() for a in groups[0])
            move(safe)
        elif step == 11.05:
            intact(groups[1])
            assert not components[1].is_collapsing()
        elif step == 11.65:
            assert components[1].is_collapsing()
            intact(groups[2]); intact(groups[3])
        elif step == 12.6:
            assert all(a.get_editor_property('hidden') for a in groups[1])
            pawn.die()
        elif step == 14.0:
            assert not pawn.is_dead()
            for group in groups: intact(group)
            assert all(not c.is_collapsing() for c in components)
            land(caps[0])
        elif step == 14.6:
            move(safe)
        elif step == 17.9:
            assert components[0].is_collapsing(), 'A rebuilt pillar must work again'
            # Dying during a fall must also cancel the animation and restore the stack.
            pawn.die()
        elif step == 19.3:
            for group in groups: intact(group)
            land(caps[1])
            move(safe)
            pawn.die()
        elif step == 23.0:
            for group in groups: intact(group)
            assert all(not c.is_collapsing() for c in components), 'Respawn must clear pending collapse timers'
            print('COLLAPSING_CROSSING_PASSED: stationary safety, 3s departure delay, independent collapse, death reset, repeated use and timer cancellation.')
        samples.append(dict(step=step, time=round(elapsed, 3), collapsing=[c.is_collapsing() for c in components]))
        if step in [7.35, 12.6, 14.0]:
            unreal.SystemLibrary.execute_console_command(world, f'Shot SHOWUI filename="{(output/(str(step)+".png")).as_posix()}" -nosuffix')
    except Exception:
        unreal.unregister_slate_post_tick_callback(handle)
        (output/'failed.json').write_text(json.dumps(samples, indent=2))
        raise
    if not steps:
        unreal.unregister_slate_post_tick_callback(handle)
        (output/'passed.json').write_text(json.dumps(samples, indent=2))


handle = unreal.register_slate_post_tick_callback(review)
print('Checking collapsing crossing over 23 game seconds.')
