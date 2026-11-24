"""Dress the Wildwood Dandelion unlock with a hovering seed and stone stand."""

from math import cos, sin, tau
from pathlib import Path
from random import Random

from ls_generate_player_meshes import Mesh, add_tapered_stalk, write_obj

TUFT = "SM_LS_DandelionPickupTuft"
SOUND = "SFX_LS_DandelionUnlock"
STAND = "Dandelion Unlock Stand"
GLOW = "Dandelion Unlock Glow"
ROOT = "/Game/LastSeed"


def make_tuft():
    mesh = Mesh()
    up = (0, 0, 1)
    rng = Random(15)
    add_tapered_stalk(mesh, (0, 0, -25), (0, 0, 24), up, 2.2, 0)
    for count, spread, rise in ((24, 52, 21), (16, 41, 37), (10, 28, 50)):
        for index in range(count):
            angle = tau * (index + rng.uniform(-.25, .25)) / count
            x, y = cos(angle), sin(angle)
            radius = spread * rng.uniform(.87, 1.11)
            height = rise + rng.uniform(-4, 4)
            root = mesh.add_vertex((x * 1.5, y * 1.5, 21), (1, 0), up)
            last = (root, root)
            for t, half_width in ((.3, 1.5), (.64, 2.9), (.84, 2.2), (1, .12)):
                z = 21 + height * (2 * t - t * t) - 8 * t**4
                ring = tuple(mesh.add_vertex((x * radius * t - y * w, y * radius * t + x * w, z), (1, t), up)
                             for w in (-half_width, half_width))
                mesh.triangles.append((last[0], ring[0], ring[1]))
                if last[0] != last[1]:
                    mesh.triangles.append((last[0], ring[1], last[1]))
                last = ring
    mesh.smooth_normals()
    return mesh


def import_asset(name, folder, source):
    import unreal

    path = f"{ROOT}/{folder}/{name}"
    asset = unreal.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else None
    if asset is None:
        task = unreal.AssetImportTask()
        task.set_editor_properties({
            "filename": str(source), "destination_path": f"{ROOT}/{folder}", "destination_name": name,
            "automated": True, "save": True,
        })
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        asset = unreal.load_asset(path)
        assert task.imported_object_paths and asset, source
    return asset


def configure(pickup):
    import unreal
    import build_level1_wildwood as builder
    from ls_world_common import FULL_COLOUR_STENCIL, point_light

    assert pickup.get_editor_property("form_to_unlock") == unreal.SeedForm.DANDELION
    world = builder.require_map()
    pos = pickup.get_actor_location()
    actors = builder.actors.get_all_level_actors()
    stand = next((a for a in actors if a.get_actor_label() == STAND), None)
    hit = unreal.SystemLibrary.line_trace_single(
        world, pos + unreal.Vector(0, 0, 180), pos - unreal.Vector(0, 0, 450),
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [pickup] + ([stand] if stand else []),
        unreal.DrawDebugTrace.NONE, True,
    ).to_tuple()
    assert hit[0], "No ground under the Dandelion unlock"
    ground = hit[4].z

    content = Path(unreal.Paths.project_content_dir())
    obj = Path(unreal.Paths.project_saved_dir()) / "DandelionUnlock" / f"{TUFT}.obj"
    obj.parent.mkdir(parents=True, exist_ok=True)
    write_obj(obj, make_tuft())
    tuft = import_asset(TUFT, "Meshes", obj)
    assert 85 < tuft.get_bounds().box_extent.z * 2 < 120, "Unexpected tuft import size"
    sound = import_asset(SOUND, "Audio", content / "LastSeed" / "SourceSounds" / f"{SOUND}.wav")
    assert 1 < sound.get_editor_property("duration") < 3, "Unexpected pickup sound duration"

    pickup.modify()
    pickup.set_actor_label("Dandelion Unlock")
    pickup.set_actor_location(unreal.Vector(pos.x, pos.y, ground + 86), False, False)
    canopy = builder.keep_coloured(pickup)
    canopy.set_static_mesh(tuft)
    canopy.set_relative_scale3d(unreal.Vector(1, 1, 1))
    canopy.set_relative_location(unreal.Vector(), False, False)
    canopy.set_material(0, builder.material("M_LS_Dandelion"))
    canopy.set_cast_shadow(False)

    body = next((c for c in pickup.get_components_by_class(unreal.StaticMeshComponent)
                 if c.get_name() == "DandelionAchene"), None)
    if body is None:
        subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        library = unreal.SubobjectDataBlueprintFunctionLibrary
        parent = next(handle for handle in subobjects.k2_gather_subobject_data_for_instance(pickup)
                      if library.get_object(library.get_data(handle)) == canopy)
        handle, reason = subobjects.add_new_subobject(unreal.AddNewSubobjectParams(
            parent_handle=parent, new_class=unreal.StaticMeshComponent, blueprint_context=None))
        body = library.get_object(library.get_data(handle))
        assert body, str(reason)
        assert subobjects.rename_subobject(handle, unreal.Text("DandelionAchene"))
    body.modify()
    body.set_mobility(unreal.ComponentMobility.MOVABLE)
    rule = unreal.AttachmentRule.KEEP_RELATIVE
    assert body.attach_to_component(canopy, "", rule, rule, rule, False)
    body.set_static_mesh(unreal.load_asset(f"{ROOT}/Meshes/SM_LS_SeedShell"))
    body.set_material(0, builder.material("M_LS_Seed"))
    body.set_relative_location(unreal.Vector(0, 1, -30), False, False)
    body.set_relative_rotation(unreal.Rotator(), False, False)
    body.set_relative_scale3d(unreal.Vector(.27, .27, .34))
    body.set_collision_profile_name("NoCollision")
    body.set_render_custom_depth(True)
    body.set_custom_depth_stencil_value(FULL_COLOUR_STENCIL)
    body.set_hidden_in_game(False)
    body.set_visibility(True)

    rock_path = builder.mesh("SM_Boulder_07")
    bounds = unreal.load_asset(rock_path).get_bounds()
    scale = .29
    rock_z = ground + 34 - (bounds.origin.z + bounds.box_extent.z) * scale
    if stand is None:
        stand = builder.mesh_actor(rock_path, pos.x, pos.y, rock_z, "Pickups",
                                   (scale, scale, scale), pickup.get_actor_rotation().yaw, label=STAND)
    else:
        stand.modify()
        stand.set_actor_location(unreal.Vector(pos.x, pos.y, rock_z), False, False)
        stand.set_actor_scale3d(unreal.Vector(scale, scale, scale))
    stand.static_mesh_component.set_collision_profile_name("NoCollision")

    glow = next((a for a in actors if a.get_actor_label() == GLOW), None)
    if glow is None:
        glow = point_light(pos.x - 40, pos.y - 30, ground + 105,
                           unreal.LinearColor(1, .89, .68), .65, 150, "Pickups")
        glow.set_actor_label(GLOW)
    else:
        glow.set_actor_location(unreal.Vector(pos.x - 40, pos.y - 30, ground + 105), False, False)
        glow.point_light_component.set_intensity(.65)
        glow.point_light_component.set_attenuation_radius(150)
    keep_world = unreal.AttachmentRule.KEEP_WORLD
    assert glow.attach_to_actor(pickup, "", keep_world, keep_world, keep_world, False)
    pickup.set_editor_properties({"bob_height": 8.0, "spin_speed": 24.0, "collect_sound": sound})
