"""PIE checks for contact, shaking, one-second collapse, audio and respawn reuse."""
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
caps = sorted([a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
               if a.get_component_by_class(unreal.CollapsingStoneComponent)], key=lambda a: a.get_actor_location().x)
components = [a.get_component_by_class(unreal.CollapsingStoneComponent) for a in caps]
assert len(caps) == 6 and all(c.collapse_delay == 1 for c in components)
groups = [list(c.support_actors) + [a] for a, c in zip(caps, components)]
positions = {a: a.get_actor_location() for g in groups for a in g}
output = Path(unreal.Paths.project_saved_dir()) / 'Screenshots/CollapsingCrossing'
output.mkdir(parents=True, exist_ok=True)
state = dict(phase='air', start=unreal.GameplayStatics.get_time_seconds(world), index=0, reuse=False, samples=[])

def move(location):
    pawn.set_actor_location(location, False, True)
    body.set_physics_linear_velocity(unreal.Vector(0, 0, 0))
    body.set_physics_angular_velocity_in_radians(unreal.Vector(0, 0, 0))

def land(index):
    surface = next(c for c in caps[index].get_components_by_class(unreal.PrimitiveComponent)
                   if c.get_collision_enabled() != unreal.CollisionEnabled.NO_COLLISION
                   and c.get_collision_response_to_channel(unreal.CollisionChannel.ECC_PHYSICS_BODY) == unreal.CollisionResponseType.ECR_BLOCK)
    center, extent, _ = unreal.SystemLibrary.get_component_bounds(surface)
    move(unreal.Vector(center.x, center.y, center.z + extent.z + 53))
    state.update(phase='landing', start=unreal.GameplayStatics.get_time_seconds(world))

def playing(sound):
    return any(a.is_playing() and a.get_editor_property('sound') == sound
               for a in unreal.ObjectIterator(unreal.AudioComponent) if a.get_world() == world)

def intact():
    for actor, position in positions.items():
        assert unreal.MathLibrary.vector_distance(actor.get_actor_location(), position) < .1, actor.get_name()
        assert actor.get_actor_enable_collision() and not actor.get_editor_property('hidden')
    assert all(not c.is_shaking() and not c.is_collapsing() for c in components)

center, extent, _ = unreal.SystemLibrary.get_component_bounds(caps[0].static_mesh_component)
move(unreal.Vector(center.x, center.y, center.z + extent.z + 150))
body.set_enable_gravity(False)

def review(_delta):
    if not editor.get_game_world(): unreal.unregister_slate_post_tick_callback(handle); return
    now = unreal.GameplayStatics.get_time_seconds(world)
    t = now - state['start']
    i = state['index']
    component = components[i]
    try:
        if state['phase'] == 'air':
            if t < 1.2: return
            intact()
            body.set_enable_gravity(True)
            land(0)
        elif state['phase'] == 'landing':
            assert t < 2, 'Landing failed to trigger the pillar'
            if not component.is_shaking(): return
            assert playing(component.shake_sound), 'Missing shaking audio'
            state.update(phase='warning', start=now, checked=False)
        elif state['phase'] == 'warning':
            if i % 2:
                body.set_physics_linear_velocity(unreal.Vector(0, 0, 0))
                body.set_physics_angular_velocity_in_radians(unreal.Vector(0, 0, 0))
            if t >= .35 and not state['checked']:
                assert component.is_shaking() and not component.is_collapsing()
                assert abs(caps[i].get_actor_location().z - positions[caps[i]].z) < .1
                assert unreal.MathLibrary.vector_distance(caps[i].get_actor_location(), positions[caps[i]]) > .1
                state['checked'] = True
                if i % 2 == 0: move(safe)
            if t < .8:
                assert not component.is_collapsing(), 'Collapsed before the one-second warning'
            if not component.is_collapsing():
                assert t < 1.15, 'Collapse missed the one-second deadline'
                return
            assert .9 <= t <= 1.15, t
            assert playing(component.fall_sound), 'Missing collapse audio'
            assert not caps[i].get_actor_enable_collision()
            assert all(not c.is_shaking() and not c.is_collapsing() for c in components[i+1:])
            state['samples'].append(dict(index=i, seconds=round(t, 3), reuse=state['reuse']))
            move(safe)
            state.update(phase='fall', start=now)
        elif state['phase'] == 'fall':
            if t < 1.15: return
            assert all(a.get_editor_property('hidden') and not a.get_actor_enable_collision() for a in groups[i])
            if i < len(caps)-1 and not state['reuse']:
                state['index'] += 1
                land(i+1)
            else:
                pawn.die()
                state.update(phase='respawn', start=now)
        elif state['phase'] == 'respawn':
            if t < 1.4: return
            assert not pawn.is_dead()
            intact()
            for c in components:
                assert not playing(c.shake_sound) and not playing(c.fall_sound)
            if not state['reuse']:
                wood = next(i for i, c in enumerate(components) if 'Wood' in c.shake_sound.get_name())
                state.update(index=wood, reuse=True)
                land(wood)
            else:
                state['index'] = len(caps)-1
                land(state['index'])
                state['phase'] = 'cancel'
        elif state['phase'] == 'cancel':
            if not component.is_shaking():
                assert t < 2
                return
            pawn.die()
            state.update(phase='cancelled', start=now)
        elif state['phase'] == 'cancelled':
            if t < 2.5: return
            intact()
            unreal.unregister_slate_post_tick_callback(handle)
            (output/'passed.json').write_text(json.dumps(state['samples'], indent=2))
            print('COLLAPSING_CROSSING_PASSED: contact only, shaking, 1s collapse, both sounds, six independent platforms, death reset, repeat use and timer cancellation.')
    except Exception as error:
        body.set_enable_gravity(True)
        unreal.unregister_slate_post_tick_callback(handle)
        (output/'failed.json').write_text(json.dumps(dict(state=state, error=str(error)), indent=2))
        raise

handle = unreal.register_slate_post_tick_callback(review)
print('Checking one-second shaking pillars, recorded sounds and respawn resets.')
