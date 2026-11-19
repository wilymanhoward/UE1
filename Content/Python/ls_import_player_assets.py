# Last Seed - builds the player's art and assigns it to BP_SeedBall.
#
# Purpose: generates and imports the form meshes, creates their materials and physical materials under Content/LastSeed/,
# creates the post-process material that keeps the player in colour, then fills in each form's data on BP_SeedBall.
# It is safe to rerun: each asset is replaced or rebuilt in place, and nothing in the Fab pack folders is changed.
# Requires: Python Editor Script Plugin. Run with Tools > Execute Python Script.

import importlib
import math
import os

import unreal

import ls_generate_player_meshes
import ls_generate_seed_textures
from ls_material_helpers import MATERIAL_FOLDER, blend, colour, combine, finish, fresh_material, library, mask, node, number

ROOT = "/Game/LastSeed"
MESH_FOLDER = ROOT + "/Meshes"
PHYSICS_FOLDER = ROOT + "/Physics"
BALL_BLUEPRINT = "/Game/Blueprint/BP_SeedBall"
GLOW_EFFECT = "/Game/FreeParticle_SoftTofu/Niagara/NS_Sparkling_Glow"

assets = unreal.AssetToolsHelpers.get_asset_tools()


# --- Meshes ---

def import_meshes():
    importlib.reload(ls_generate_player_meshes).main()

    tasks = []
    for file_name in sorted(os.listdir(ls_generate_player_meshes.OUTPUT_FOLDER)):
        name, extension = os.path.splitext(file_name)
        if extension != ".obj":
            continue
        task = unreal.AssetImportTask()
        task.filename = os.path.normpath(os.path.join(ls_generate_player_meshes.OUTPUT_FOLDER, file_name))
        task.destination_path = MESH_FOLDER
        task.destination_name = name
        task.automated = True
        task.replace_existing = True
        task.save = True
        tasks.append(task)
    assets.import_asset_tasks(tasks)

    meshes = {}
    for task in tasks:
        name = os.path.splitext(os.path.basename(task.filename))[0]
        meshes[name] = unreal.load_asset("{}/{}".format(MESH_FOLDER, name))
        if not meshes[name]:
            raise RuntimeError("Last Seed player assets: {} did not import".format(name))
        # Nanite cannot draw the Dandelion's translucent material, and these small meshes gain nothing from it.
        nanite = meshes[name].get_editor_property("nanite_settings")
        nanite.set_editor_property("enabled", False)
        unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).set_nanite_settings(meshes[name], nanite, True)
        unreal.EditorAssetLibrary.save_loaded_asset(meshes[name], False)
    return meshes


def check_mesh_placement(meshes):
    """The sprout only stays on top of the ball if the import kept Z as up, so this catches a wrong axis or scale."""
    sprout = meshes["SM_LS_SeedSprout"].get_bounds()
    lowest = sprout.origin.z - sprout.box_extent.z
    shell = meshes["SM_LS_SeedShell"].get_bounds()
    if lowest < 40.0 or abs(shell.box_extent.z - 43.65) > 1.0:
        raise RuntimeError("Last Seed player assets: meshes imported at the wrong scale or axis (sprout bottom {:.1f}, shell half height {:.1f})".format(
            lowest, shell.box_extent.z))


# --- The materials ---

def import_seed_textures():
    ls_generate_seed_textures.bake()
    tasks = []
    for suffix in ("Color", "Normal"):
        name = "T_LS_SeedShell_" + suffix
        task = unreal.AssetImportTask()
        task.set_editor_properties({
            "filename": str(ls_generate_seed_textures.SOURCE / (name + ".png")),
            "destination_path": ROOT + "/Textures/Seed", "destination_name": name,
            "automated": True, "replace_existing": True, "save": False,
        })
        tasks.append(task)
    assets.import_asset_tasks(tasks)

    albedo, normal = (task.get_objects()[0] for task in tasks)
    albedo.set_editor_properties({"srgb": True, "compression_no_alpha": False})
    normal.set_editor_properties({"srgb": False, "compression_settings": unreal.TextureCompressionSettings.TC_NORMALMAP})
    for texture in (albedo, normal):
        if not unreal.EditorAssetLibrary.save_loaded_asset(texture, False):
            raise RuntimeError("Could not save " + texture.get_path_name())
    return albedo, normal


def seat_seed_on_collider(material):
    """Compensate for the seed's narrower profile as its spherical collider rolls."""
    local_up = node(material, unreal.MaterialExpressionTransform,
                    transform_source_type=unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD,
                    transform_type=unreal.MaterialVectorCoordTransform.TRANSFORM_LOCAL)
    library.connect_material_expressions(colour(material, 0.0, 0.0, 1.0), "", local_up, "")
    lean = ls_generate_player_meshes.SEED_LEAN
    sin_lean, cos_lean = math.sin(lean), math.cos(lean)
    sections = [ls_generate_player_meshes.seed_section(*section) for section in ls_generate_player_meshes.SEED_PROFILE]
    profile = ", ".join(f"float3({radius:.5f}, {center:.5f}, {height:.5f})" for radius, center, height in sections)
    offset = node(material, unreal.MaterialExpressionCustom, description="Seed contact with rolling sphere",
                  output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT3,
                  code=f"""
float3 up = normalize(LocalUp);
float side = dot(up, float3(0.0, {cos_lean:.8f}, {-sin_lean:.8f}));
float axis = dot(up, float3(0.0, {sin_lean:.8f}, {cos_lean:.8f}));
float width = length(float2(up.x * {ls_generate_player_meshes.SEED_DEPTH:.5f}, side));
const float3 sections[{len(sections)}] = {{ {profile} }};
float bottom = 0.0;
[unroll]
for (int i = 0; i < {len(sections)}; ++i)
{{
    float3 ring = sections[i];
    bottom = min(bottom, ring.y * side + ring.z * axis - ring.x * width);
}}
float scale = length(TransformLocalVectorToWorld(Parameters, float3(1.0, 0.0, 0.0)));
return float3(0.0, 0.0, -max(0.0, {ls_generate_player_meshes.BALL_RADIUS - 0.8:.2f} + bottom) * scale);
""")
    up_input = unreal.CustomInput()
    up_input.set_editor_property("input_name", "LocalUp")
    offset.set_editor_property("inputs", [up_input])
    assert library.connect_material_expressions(local_up, "", offset, "LocalUp")
    assert library.connect_material_property(offset, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)


def build_seed_material():
    """Matte seed coat with a tangent-space normal map for the seams and grain."""
    albedo, normal = import_seed_textures()
    material = fresh_material("M_LS_Seed")
    paint = node(material, unreal.MaterialExpressionTextureSample, texture=albedo,
                 sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
    detail = node(material, unreal.MaterialExpressionTextureSample, texture=normal,
                  sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    assert library.connect_material_property(paint, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    assert library.connect_material_property(paint, "A", unreal.MaterialProperty.MP_ROUGHNESS)
    assert library.connect_material_property(detail, "RGB", unreal.MaterialProperty.MP_NORMAL)
    assert library.connect_material_property(number(material, 0.28), "", unreal.MaterialProperty.MP_SPECULAR)
    seat_seed_on_collider(material)
    return finish(material)


def seed_appearance(mesh, material):
    return {
        "mesh": mesh, "material": material, "upright_mesh": None, "upright_material": None,
        "glow_effect": None, "glow_color": unreal.LinearColor(1.0, 0.72, 0.3, 1.0), "glow_brightness": 0.0,
    }


def build_stone_material():
    """Rough slate with a restrained amber mineral seam."""
    material = fresh_material("M_LS_Stone")
    uv = node(material, unreal.MaterialExpressionTextureCoordinate)
    crack = mask(material, uv, True)
    tone = mask(material, uv, False)
    rock = blend(material, colour(material, 0.065, 0.095, 0.12), colour(material, 0.19, 0.24, 0.29), tone)
    base = blend(material, rock, colour(material, 0.095, 0.055, 0.023), crack)
    library.connect_material_property(base, "", unreal.MaterialProperty.MP_BASE_COLOR)
    library.connect_material_property(number(material, 0.92), "", unreal.MaterialProperty.MP_ROUGHNESS)
    library.connect_material_property(number(material, 0.19), "", unreal.MaterialProperty.MP_SPECULAR)
    glow = combine(material, unreal.MaterialExpressionMultiply, crack, colour(material, 2.4, 1.05, 0.24))
    library.connect_material_property(glow, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    return finish(material)


def build_dandelion_material():
    """Soft white and slightly see-through. Stalks are more solid at the base and hairs fade out toward their tips."""
    material = fresh_material("M_LS_Dandelion")
    material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    material.set_editor_property("two_sided", True)
    # Lets the fluff write the stencil that keeps it in full colour, which translucent materials skip by default.
    material.set_editor_property("allow_translucent_custom_depth_writes", True)
    along = mask(material, node(material, unreal.MaterialExpressionTextureCoordinate), False)
    library.connect_material_property(colour(material, 0.95, 0.94, 0.88), "", unreal.MaterialProperty.MP_BASE_COLOR)
    library.connect_material_property(colour(material, 0.55, 0.53, 0.46), "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    opacity = blend(material, number(material, 0.85), number(material, 0.4), along)
    library.connect_material_property(opacity, "", unreal.MaterialProperty.MP_OPACITY)
    return finish(material)


def build_core_material():
    material = fresh_material("M_LS_DandelionCore")
    gold = colour(material, 1.0, 0.65, 0.15)
    library.connect_material_property(gold, "", unreal.MaterialProperty.MP_BASE_COLOR)
    glow = combine(material, unreal.MaterialExpressionMultiply, gold, number(material, 2.0))
    library.connect_material_property(glow, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    return finish(material)


def build_wither_post_material():
    """Greys the screen by the Saturation parameter, except pixels showing something marked with stencil 1. ARestorationDriver loads this.
    Custom depth holds the nearest marked object even when something else stands in front of it, so the two depths are compared to find what is really on screen."""
    material = fresh_material("M_LS_WitherPost")
    material.set_editor_property("material_domain", unreal.MaterialDomain.MD_POST_PROCESS)

    scene = node(material, unreal.MaterialExpressionSceneTexture, scene_texture_id=unreal.SceneTextureId.PPI_POST_PROCESS_INPUT0)
    stencil = node(material, unreal.MaterialExpressionSceneTexture, scene_texture_id=unreal.SceneTextureId.PPI_CUSTOM_STENCIL)
    scene_depth = node(material, unreal.MaterialExpressionSceneTexture, scene_texture_id=unreal.SceneTextureId.PPI_SCENE_DEPTH)
    custom_depth = node(material, unreal.MaterialExpressionSceneTexture, scene_texture_id=unreal.SceneTextureId.PPI_CUSTOM_DEPTH)
    saturation = node(material, unreal.MaterialExpressionScalarParameter, parameter_name="Saturation", default_value=1.0)

    grey = node(material, unreal.MaterialExpressionCustom)
    grey.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    grey.set_editor_property("code",
        "float Luminance = dot(Scene.rgb, float3(0.2126, 0.7152, 0.0722));\n"
        "bool Marked = Stencil.r > 0.5 && CustomDepth.r <= SceneDepth.r * 1.002 + 2.0;\n"
        "return Marked ? Scene.rgb : lerp(Luminance.xxx, Scene.rgb, Saturation);")
    inputs = []
    for name in ("Scene", "Stencil", "SceneDepth", "CustomDepth", "Saturation"):
        custom_input = unreal.CustomInput()
        custom_input.set_editor_property("input_name", name)
        inputs.append(custom_input)
    grey.set_editor_property("inputs", inputs)

    library.connect_material_expressions(scene, "Color", grey, "Scene")
    library.connect_material_expressions(stencil, "Color", grey, "Stencil")
    library.connect_material_expressions(scene_depth, "Color", grey, "SceneDepth")
    library.connect_material_expressions(custom_depth, "Color", grey, "CustomDepth")
    library.connect_material_expressions(saturation, "", grey, "Saturation")
    library.connect_material_property(grey, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    return finish(material)


# --- Physical materials ---

def build_physical_material(name, friction, restitution, combine_max=False):
    path = "{}/{}".format(PHYSICS_FOLDER, name)
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        physical = unreal.load_asset(path)
    else:
        physical = assets.create_asset(name, PHYSICS_FOLDER, unreal.PhysicalMaterial, unreal.PhysicalMaterialFactoryNew())
    physical.set_editor_property("friction", friction)
    physical.set_editor_property("restitution", restitution)
    if combine_max:
        # Max outranks the Min on PM_Ice. Without this, Stone has no grip on ice and cannot climb Level 2's slope.
        physical.set_editor_property("override_friction_combine_mode", True)
        physical.set_editor_property("friction_combine_mode", unreal.FrictionCombineMode.MAX)
    unreal.EditorAssetLibrary.save_loaded_asset(physical, False)
    return physical


# --- Blueprint ---

def assign_to_ball(form_assets):
    blueprint = unreal.load_asset(BALL_BLUEPRINT)
    if not blueprint:
        raise RuntimeError("Last Seed player assets: {} not found".format(BALL_BLUEPRINT))
    # Compiling first gives the Blueprint the new components and fields from C++ before they are filled in.
    unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)

    defaults = unreal.get_default_object(blueprint.generated_class())
    form_data = defaults.get_editor_property("form_data")
    for form, values in form_assets.items():
        entry = form_data[form]
        for key, value in values.items():
            entry.set_editor_property(key, value)
        form_data[form] = entry
    defaults.set_editor_property("form_data", form_data)

    unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
    # False saves even when not marked dirty. Editing class defaults from Python doesn't mark it, so a plain save does nothing.
    if not unreal.EditorAssetLibrary.save_loaded_asset(blueprint, False):
        raise RuntimeError("Last Seed player assets: could not save " + BALL_BLUEPRINT)


def main():
    meshes = import_meshes()
    check_mesh_placement(meshes)

    seed_material = build_seed_material()
    stone_material = build_stone_material()
    dandelion_material = build_dandelion_material()
    core_material = build_core_material()
    build_wither_post_material()

    glow = unreal.load_asset(GLOW_EFFECT)
    if not glow:
        unreal.log_warning("Last Seed player assets: {} not found, so the forms have no particles".format(GLOW_EFFECT))

    assign_to_ball({
        unreal.SeedForm.SEED: dict(seed_appearance(meshes["SM_LS_SeedShell"], seed_material),
                                  physical_material=build_physical_material("PM_Seed", 0.7, 0.1)),
        unreal.SeedForm.STONE: {
            "mesh": meshes["SM_LS_StoneShell"], "material": stone_material,
            "upright_mesh": None, "upright_material": None,
            "glow_effect": None, "glow_color": unreal.LinearColor(1.0, 0.6, 0.2, 1.0), "glow_brightness": 0.0,
            "physical_material": build_physical_material("PM_Stone", 1.5, 0.0, combine_max=True),
        },
        unreal.SeedForm.DANDELION: {
            "mesh": meshes["SM_LS_DandelionFluff"], "material": dandelion_material,
            "upright_mesh": meshes["SM_LS_DandelionCore"], "upright_material": core_material,
            "glow_effect": glow, "glow_color": unreal.LinearColor(1.0, 0.9, 0.65, 1.0), "glow_brightness": 25.0,
            "physical_material": build_physical_material("PM_Dandelion", 0.5, 0.2),
        },
    })

    unreal.log("Last Seed player assets: imported {} meshes to {}".format(len(meshes), MESH_FOLDER))
    unreal.log("Last Seed player assets: built 5 materials in {} and 3 physical materials in {}".format(MATERIAL_FOLDER, PHYSICS_FOLDER))
    unreal.log("Last Seed player assets: assigned everything to {}. Press Play to see it.".format(BALL_BLUEPRINT))


if __name__ == "__main__":
    main()
