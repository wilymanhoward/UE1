"""Turns each checkpoint into a wooden post with a hanging lantern, standing at the edge of the trail.

The checkpoint actor stays on the trail's centre line, where the ball respawns. Its trigger sphere widens to span the trail,
so rolling past lights the lantern, while only the post and its light move out to the edge. The model comes from
maya_lantern_post.py (SM_LS_LanternPost.fbx); the glass panes glow when ACheckpointShrine sets the material's Lit to 1.
Run in the editor: import ls_lantern_post; ls_lantern_post.build()
"""
import math
from pathlib import Path

import unreal

from ls_material_helpers import colour, combine, finish, fresh_material, library, node, number, output

MESH = "/Game/LastSeed/Meshes/SM_LS_LanternPost"
SOURCE = Path(__file__).resolve().parent.parent / "LastSeed" / "SourceMeshes" / "SM_LS_LanternPost.fbx"
WALL_GAP = 70.0  # ls_wildwood_plan puts the side walls this far past the lane's edge.
EDGE = 90.0  # The post stands this far past the lane's edge, on the shoulder.
ARM = 62.0  # The lantern hangs this far along the arm (see maya_lantern_post.py).
FLAME = 166.0  # The lantern's centre above the post's foot.


def import_mesh():
    task = unreal.AssetImportTask()
    task.set_editor_properties({"filename": str(SOURCE), "destination_path": MESH.rsplit("/", 1)[0], "destination_name": "SM_LS_LanternPost",
                                "replace_existing": True, "automated": True, "save": True})
    options = unreal.FbxImportUI()
    options.set_editor_properties({"import_mesh": True, "import_materials": False, "import_textures": False,
                                   "import_as_skeletal": False})
    options.static_mesh_import_data.set_editor_properties({"combine_meshes": True, "generate_lightmap_u_vs": False})
    task.set_editor_property("options", options)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = unreal.load_asset(MESH)
    assert mesh, "Lantern post did not import"
    return mesh


def iron_material():
    material = fresh_material("M_LS_LanternIron")
    output(material, colour(material, 0.05, 0.05, 0.055), unreal.MaterialProperty.MP_BASE_COLOR)
    output(material, number(material, 0.8), unreal.MaterialProperty.MP_METALLIC)
    output(material, number(material, 0.55), unreal.MaterialProperty.MP_ROUGHNESS)
    return finish(material)


def glass_material():
    """Frosted amber panes: dim and cold until Lit, then a warm firelight glow."""
    material = fresh_material("M_LS_LanternGlass")
    lit = node(material, unreal.MaterialExpressionScalarParameter, parameter_name="Lit", default_value=0.0)
    warm = colour(material, 1.0, 0.55, 0.18)
    strength = combine(material, unreal.MaterialExpressionMultiply, lit, number(material, 40.0))
    output(material, colour(material, 0.35, 0.28, 0.2), unreal.MaterialProperty.MP_BASE_COLOR)
    output(material, combine(material, unreal.MaterialExpressionMultiply, warm, strength), unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    output(material, number(material, 0.3), unreal.MaterialProperty.MP_ROUGHNESS)
    return finish(material)


def lane_half(x, y, walls):
    """Half the trail's width here: the nearest planned side wall, less the gap the planner left past the lane."""
    def distance(x0, y0, x1, y1):
        dx, dy = x1 - x0, y1 - y0
        t = max(0.0, min(1.0, ((x - x0) * dx + (y - y0) * dy) / max(dx * dx + dy * dy, 1e-6)))
        return math.hypot(x - x0 - t * dx, y - y0 - t * dy)
    return min(distance(x0, y0, x1, y1) for x0, y0, x1, y1, _, _ in walls) - WALL_GAP


def configure(actor, walls, mesh=None, materials=None):
    mesh = mesh or unreal.load_asset(MESH)
    materials = materials or {"Wood": unreal.load_asset("/Game/LastSeed/Materials/M_LS_Bark"),
                              "Iron": unreal.load_asset("/Game/LastSeed/Materials/M_LS_LanternIron"),
                              "Glass": unreal.load_asset("/Game/LastSeed/Materials/M_LS_LanternGlass")}
    location = actor.get_actor_location()
    side = lane_half(location.x, location.y, walls) + EDGE
    component = [c for c in actor.get_components_by_class(unreal.StaticMeshComponent) if c.get_name() == "Mesh"][0]
    component.set_static_mesh(mesh)
    component.set_editor_property("override_materials", [])
    for index, slot in enumerate(mesh.get_editor_property("static_materials")):
        name = str(slot.material_slot_name)
        component.set_material(index, next(m for key, m in materials.items() if name.startswith(key)))
    # The post stands on the right shoulder with its arm reaching back over the trail.
    component.set_relative_location(unreal.Vector(0.0, side, -55.0), False, False)
    component.set_relative_rotation(unreal.Rotator(yaw=-90.0), False, False)
    component.set_relative_scale3d(unreal.Vector(1.0, 1.0, 1.0))
    glow = actor.get_component_by_class(unreal.PointLightComponent)
    glow.set_relative_location(unreal.Vector(0.0, side - ARM, FLAME - 55.0), False, False)
    glow.set_editor_properties({"light_color": unreal.Color(r=255, g=150, b=70, a=255), "intensity": 6000.0,
                                "attenuation_radius": 1100.0})
    # Wide enough to reach from the centre line past the post, so passing anywhere across the trail lights it.
    actor.get_component_by_class(unreal.SphereComponent).set_sphere_radius(side + 60.0)
    return side


def build():
    import build_level1_wildwood as builder

    builder.require_map()
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages(), "Save your map edits first."
    mesh = import_mesh()
    materials = {"Wood": unreal.load_asset("/Game/LastSeed/Materials/M_LS_Bark"), "Iron": iron_material(), "Glass": glass_material()}
    walls = builder.load_plan()["walls"]
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    shrines = [a for a in actors if isinstance(a, unreal.CheckpointShrine)]
    for actor in shrines:
        actor.modify()
        print(actor.get_actor_label(), "post at", round(configure(actor, walls, mesh, materials)), "cm from the centre line")
    assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    print("Lantern posts on", len(shrines), "checkpoints")
