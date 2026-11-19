"""Dress the Stone form pickup as a cracked shell resting on a Wildwood rock."""
from pathlib import Path
import unreal


def configure(pickup):
    import build_level1_wildwood as builder

    assert pickup.get_editor_property('form_to_unlock') == unreal.SeedForm.STONE
    pickup.set_actor_label('Stone Shell Unlock')
    component = pickup.get_editor_property('mesh')
    builder.fit_mesh(component, '/Game/LastSeed/Meshes/SM_LS_StoneShell', 106.0, -53.0)
    component.set_relative_location(unreal.Vector(), False, False)
    component.set_material(0, builder.material('M_LS_Stone'))
    component.set_render_custom_depth(False)
    for other in pickup.get_components_by_class(unreal.StaticMeshComponent):
        if other != component:
            other.set_visibility(False, False)
            other.set_collision_profile_name('NoCollision')

    p = pickup.get_actor_location()
    world = builder.require_map()
    ignore = [a for a in builder.actors.get_all_level_actors() if not (
        isinstance(a, unreal.LandscapeProxy) or a.get_actor_label() == 'SM_LS_WildwoodTrail_02')]
    hit = unreal.SystemLibrary.line_trace_single(world, p + unreal.Vector(0, 0, 300),
        p - unreal.Vector(0, 0, 400), unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
        True, ignore, unreal.DrawDebugTrace.NONE, True)
    assert hit and hit.to_tuple()[0], 'No ground under the Stone unlock pickup'
    ground = hit.to_tuple()[4].z
    pickup.set_actor_location(unreal.Vector(p.x, p.y, ground+62), False, False)
    ledge_label = 'Stone Shell Ledge'
    ledge = next((a for a in builder.actors.get_all_level_actors() if a.get_actor_label() == ledge_label), None)
    path = builder.mesh('SM_Boulder_07')
    mesh = unreal.load_asset(path)
    scale = .31
    z = ground - 42 - builder.base_height_offset(mesh, scale)
    if ledge is None:
        ledge = builder.mesh_actor(path, p.x, p.y, z, 'Pickups', (scale, scale, scale),
            pickup.get_actor_rotation().yaw, label=ledge_label)
        ledge.static_mesh_component.set_collision_profile_name('NoCollision')
    else:
        ledge.set_actor_location(unreal.Vector(p.x, p.y, z), False, False)

    folder = '/Game/LastSeed/Audio'
    name = 'SFX_LS_StoneUnlock'
    path = f'{folder}/{name}'
    if not unreal.EditorAssetLibrary.does_asset_exist(path):
        task = unreal.AssetImportTask()
        task.filename = str(Path(unreal.Paths.project_content_dir()) / 'LastSeed/SourceSounds' / (name+'.wav'))
        task.destination_path = folder
        task.automated = True
        task.save = True
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        assert task.imported_object_paths
    chips = unreal.load_asset('/Game/LastSeed/Generated/SM_LS_WildwoodRockFragment')
    assert chips
    pickup.set_editor_properties({'bob_height': 0.0, 'spin_speed': 0.0, 'collect_effect': None,
        'collect_chip_mesh': chips, 'collect_sound': unreal.load_asset(path),
        'prompt_message': unreal.Text('Stone Shell unlocked. Press 2 to transform.')})
