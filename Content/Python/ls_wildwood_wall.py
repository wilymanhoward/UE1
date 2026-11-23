"""Dress the Trail 2 Stone gate with one Wildwood boulder and physical rock fragments."""
import unreal


def configure(wall):
    import build_level1_wildwood as builder

    world = builder.require_map()
    root = wall.get_editor_property('mesh')
    rocks = list(wall.get_editor_property('rubble_actors'))
    assert all(rock.get_actor_label().startswith(('WallRubble_', 'Trail02_BreakableBoulder')) for rock in rocks)
    mesh = unreal.load_asset(builder.mesh('SM_Boulder_08'))
    assert mesh.get_editor_property('body_setup').get_editor_property('collision_trace_flag') == unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE

    if rocks:
        wall.set_actor_transform(rocks[0].get_actor_transform(), False, False)
    elif root.static_mesh != mesh:
        p = wall.get_actor_location() - wall.get_actor_right_vector() * 30
        ignore = [a for a in builder.actors.get_all_level_actors() if not (
            isinstance(a, unreal.LandscapeProxy) or a.get_actor_label() == 'SM_LS_WildwoodTrail_02')]
        hit = unreal.SystemLibrary.line_trace_single(world, p + unreal.Vector(0, 0, 1200),
            p - unreal.Vector(0, 0, 1800), unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
            True, ignore, unreal.DrawDebugTrace.NONE, True)
        assert hit and hit.to_tuple()[0], 'No ground under the breakable boulder'
        scale = 1.03
        p.z = hit.to_tuple()[4].z - 125 - builder.base_height_offset(mesh, scale)
        wall.set_actor_scale3d(unreal.Vector(scale, scale, scale))
        wall.set_actor_rotation(unreal.Rotator(yaw=wall.get_actor_rotation().yaw+90), False)
        wall.set_actor_location(p, False, False)

    # The breakable actor owns the visible mesh so the ball hits its real surface.
    root.set_static_mesh(mesh)
    root.set_editor_property('override_materials', [])
    root.set_collision_profile_name('BlockAll')
    root.set_visibility(True, False)
    root.set_cast_shadow(True)

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
    wall.set_editor_properties({'break_speed': 175.0, 'rubble_actors': [], 'debris_mesh': debris, 'debris_count': 3,
        'debris_scale': .62, 'debris_mass_kg': 45.0, 'debris_speed': 325.0, 'debris_lifetime': 3.2,
        'break_sound': unreal.load_asset('/Game/LastSeed/Audio/SFX_LS_WildwoodBoulderBreak')})
    for old_rock in rocks:
        assert builder.actors.destroy_actor(old_rock)
