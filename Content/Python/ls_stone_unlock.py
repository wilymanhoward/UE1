"""Dress the Stone form pickup as a cracked shell resting on a Wildwood rock."""
from pathlib import Path
import unreal


def cue_material():
    folder = '/Game/LastSeed/Materials'
    name = 'M_LS_StonePickupCue'
    path = f'{folder}/{name}'
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        return unreal.load_asset(path)

    assets = unreal.AssetToolsHelpers.get_asset_tools()
    material = assets.create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
    material.set_editor_properties({'blend_mode': unreal.BlendMode.BLEND_ADDITIVE,
        'shading_model': unreal.MaterialShadingModel.MSM_UNLIT, 'two_sided': True})
    graph = unreal.MaterialEditingLibrary
    uv = graph.create_material_expression(material, unreal.MaterialExpressionTextureCoordinate, -480, 0)
    clock = graph.create_material_expression(material, unreal.MaterialExpressionTime, -480, 180)
    pulse = graph.create_material_expression(material, unreal.MaterialExpressionCustom, -230, 0)
    pins = []
    for name in ('UV', 'Time'):
        pin = unreal.CustomInput()
        pin.set_editor_property('input_name', name)
        pins.append(pin)
    pulse.set_editor_properties({'inputs': pins, 'output_type': unreal.CustomMaterialOutputType.CMOT_FLOAT3,
        'code': '''float2 p = UV - 0.5;
float r = length(p);
float cycle = frac(Time / 2.5);
float shimmer = 0.65 + 0.22 * sin(Time * 2.513);
float core = 1 - smoothstep(0.004, 0.017, abs(r - 0.345));
float halo = (1 - smoothstep(0.012, 0.047, abs(r - 0.345))) * 0.16;
float ripple = (1 - smoothstep(0.003, 0.018, abs(r - lerp(0.35, 0.47, cycle))))
    * sin(cycle * 3.141593) * 0.28;
float angle = atan2(p.y, p.x);
float dots = pow(saturate(cos(angle * 7 - Time * 1.1)), 24)
    * (1 - smoothstep(0.004, 0.021, abs(r - 0.405)));
return float3(1.08, 0.79, 0.40) * (core * shimmer + halo + ripple + dots * 0.6);'''})
    for name, source in [('UV', uv), ('Time', clock)]:
        assert graph.connect_material_expressions(source, '', pulse, name)
    assert graph.connect_material_property(pulse, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    graph.recompile_material(material)
    assert unreal.EditorAssetLibrary.save_loaded_asset(material, False)
    return material


def configure_cue(pickup, ground_hit):
    component = next((c for c in pickup.get_components_by_class(unreal.StaticMeshComponent)
        if c.get_name() in ('Cylinder', 'StonePickupCue')), None)
    if component is None:
        subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        root = subobjects.k2_gather_subobject_data_for_instance(pickup)[0]
        handle, reason = subobjects.add_new_subobject(unreal.AddNewSubobjectParams(
            parent_handle=root, new_class=unreal.StaticMeshComponent, blueprint_context=None))
        component = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(
            unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle))
        assert component, str(reason)
        assert subobjects.rename_subobject(handle, unreal.Text('StonePickupCue'))

    hit = ground_hit.to_tuple()
    normal = hit[6]
    component.set_mobility(unreal.ComponentMobility.MOVABLE)
    component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Plane'))
    component.set_material(0, cue_material())
    component.set_collision_profile_name('NoCollision')
    component.set_cast_shadow(False)
    component.set_visibility(True, False)
    component.set_hidden_in_game(False)
    component.set_world_scale3d(unreal.Vector(2.65, 2.65, 1))
    component.set_world_location_and_rotation(hit[4] + normal * 9,
        unreal.MathLibrary.make_rot_from_z(normal), False, False)


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
    configure_cue(pickup, hit)
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
