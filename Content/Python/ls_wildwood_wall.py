"""Dress the Trail 2 Stone gate with one Wildwood boulder and physical rock fragments."""
import unreal


def configure(wall):
    import build_level1_wildwood as builder

    world = builder.require_map()
    root = wall.get_editor_property('mesh')
    builder.hide_component(root)

    rocks = list(wall.get_editor_property('rubble_actors'))
    assert all(rock.get_actor_label().startswith(('WallRubble_', 'Trail02_BreakableBoulder')) for rock in rocks)
    p = wall.get_actor_location() - wall.get_actor_right_vector() * 30
    ignore = [a for a in builder.actors.get_all_level_actors() if not (
        isinstance(a, unreal.LandscapeProxy) or a.get_actor_label() == 'SM_LS_WildwoodTrail_02')]
    hit = unreal.SystemLibrary.line_trace_single(world, p + unreal.Vector(0, 0, 1200),
        p - unreal.Vector(0, 0, 1800), unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
        True, ignore, unreal.DrawDebugTrace.NONE, True)
    assert hit and hit.to_tuple()[0], 'No ground under the breakable boulder'
    path = builder.mesh('SM_Boulder_08')
    mesh = unreal.load_asset(path)
    scale = 1.03
    # Sink the rounded base into the uphill surface so it reads as a grounded boulder.
    p.z = hit.to_tuple()[4].z - 125 - builder.base_height_offset(mesh, scale)
    label = 'Trail02_BreakableBoulder'
    rock = rocks[0] if rocks else builder.mesh_actor(path, p.x, p.y, p.z, 'Puzzles', label=label)
    rock.set_actor_label(label)
    component = rock.static_mesh_component
    component.set_mobility(unreal.ComponentMobility.MOVABLE)
    component.set_static_mesh(mesh)
    component.set_editor_property('override_materials', [])
    component.set_collision_profile_name('NoCollision')
    rock.set_actor_scale3d(unreal.Vector(scale, scale, scale))
    rock.set_actor_rotation(unreal.Rotator(yaw=wall.get_actor_rotation().yaw+90), False)
    rock.set_actor_location(p, False, False)

    debris_path = '/Game/LastSeed/Generated/SM_LS_WildwoodRockFragment'
    assets = unreal.EditorAssetLibrary
    debris = unreal.load_asset(debris_path) if assets.does_asset_exist(debris_path) else None
    if debris is None:
        debris = assets.duplicate_asset(builder.mesh('SM_Boulder_07'), debris_path)
        assert debris
        debris.get_editor_property('body_setup').set_editor_property('collision_trace_flag', unreal.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
        editor = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
        assert editor.add_simple_collisions(debris, unreal.ScriptCollisionShapeType.NDOP18) >= 0
        assert assets.save_loaded_asset(debris, False)
    assert unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).get_convex_collision_count(debris) > 0
    # Stone loses speed on the uphill approach to this gate.
    wall.set_editor_properties({'break_speed': 175.0, 'rubble_actors': [rock], 'debris_mesh': debris, 'debris_count': 14,
        'debris_scale': .085, 'debris_speed': 480.0, 'debris_lifetime': 2.8,
        'break_sound': unreal.load_asset('/Game/LastSeed/Audio/SFX_LS_StoneFall')})
    for old_rock in rocks[1:]:
        assert builder.actors.destroy_actor(old_rock)
