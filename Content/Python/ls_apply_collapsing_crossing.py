"""Attach collapse behaviour to the four existing gorge pillars without replacing their art."""
import unreal


def build():
    import build_level1_wildwood as builder
    builder.require_map()
    rocks = [a for a in builder.actors.get_all_level_actors()
             if isinstance(a, unreal.StaticMeshActor) and a.get_actor_label().startswith('PillarRock')
             and -17500 < a.get_actor_location().x < -12800 and -8200 < a.get_actor_location().y < -5800]
    caps = [a for a in rocks if a.static_mesh_component.static_mesh.get_path_name().split('.')[0] == builder.TOP_ROCK]
    assert len(caps) == 4, f'Expected four gorge caps, found {len(caps)}'
    supports = {cap: [] for cap in caps}
    for rock in rocks:
        if rock in caps: continue
        p = rock.get_actor_location()
        cap = min(caps, key=lambda c: (c.get_actor_location().x-p.x)**2 + (c.get_actor_location().y-p.y)**2)
        center = cap.get_actor_location()
        assert (center.x-p.x)**2 + (center.y-p.y)**2 < 100**2
        supports[cap].append(rock)
    assert all(len(group) >= 3 for group in supports.values())
    for cap in sorted(caps, key=lambda a: a.get_actor_location().x):
        builder.add_collapsing_stone(cap, supports[cap])
    tutorial = next(a for a in builder.actors.get_all_level_actors() if a.get_name() == 'TutorialTrigger_3')
    tutorial.set_editor_property('message', unreal.Text(
        'Stone pillars collapse 3 seconds after you leave. Keep moving! They rebuild when you respawn.'))
    tutorial.set_editor_property('display_duration', 8.0)
    assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    print('Saved four collapsing stone pillars; each restores its complete stack when the player respawns.')
    return len(caps)


if __name__ == '__main__': build()
