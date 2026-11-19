"""Dress the Trail 2 Stone gate with Wildwood boulders and physical rock fragments."""
import unreal


def configure(wall):
    import build_level1_wildwood as builder

    world = builder.require_map()
    root = wall.get_editor_property('mesh')
    builder.hide_component(root)
    origin = wall.get_actor_location()
    yaw = wall.get_actor_rotation().yaw
    width = wall.get_actor_scale3d().y * 100
    right, forward = wall.get_actor_right_vector(), wall.get_actor_forward_vector()
    rocks = list(wall.get_editor_property('rubble_actors'))
    ignore = [a for a in builder.actors.get_all_level_actors() if not (
        isinstance(a, unreal.LandscapeProxy) or a.get_actor_label() == 'SM_LS_WildwoodTrail_02')]

    # Across, along, lift, Wildwood variant, uniform scale and yaw offset.
    layout = [(-.33, 25, -40, 8, .45, -12), (0, 5, -42, 9, .38, 7),
              (.33, 30, -43, 10, .35, 19), (-.23, 45, 80, 7, .69, 24),
              (.16, 12, 80, 8, .52, -14), (.37, -92, -20, 7, .31, 53)]
    for index, (side, along, lift, variant, scale, turn) in enumerate(layout):
        p = origin + right * (width * side) + forward * along
        hit = unreal.SystemLibrary.line_trace_single(world, p + unreal.Vector(0, 0, 1200),
            p - unreal.Vector(0, 0, 1800), unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
            True, ignore, unreal.DrawDebugTrace.NONE, True)
        assert hit and hit.to_tuple()[0], f'No ground under wall rock {index + 1}'
        path = builder.mesh(f'SM_Boulder_{variant:02d}')
        mesh = unreal.load_asset(path)
        p.z = hit.to_tuple()[4].z + lift - builder.base_height_offset(mesh, scale)
        label = f'WallRubble_{index + 1:02d}'
        if index < len(rocks):
            rock = rocks[index]
            rock.set_actor_label(label)
        else:
            rock = builder.mesh_actor(path, p.x, p.y, p.z, 'Puzzles', label=label)
            rocks.append(rock)
        component = rock.static_mesh_component
        component.set_mobility(unreal.ComponentMobility.MOVABLE)
        component.set_static_mesh(mesh)
        component.set_editor_property('override_materials', [])
        component.set_collision_profile_name('NoCollision')
        rock.set_actor_scale3d(unreal.Vector(scale, scale, scale))
        rock.set_actor_rotation(unreal.Rotator(yaw=yaw+90+turn), False)
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
    wall.set_editor_properties({'rubble_actors': rocks, 'debris_mesh': debris, 'debris_count': 14,
        'debris_scale': .085, 'debris_speed': 480.0, 'debris_lifetime': 2.8,
        'break_sound': unreal.load_asset('/Game/LastSeed/Audio/SFX_LS_StoneFall')})
