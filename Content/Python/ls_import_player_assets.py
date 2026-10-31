# Last Seed - builds the player's art and assigns it to BP_SeedBall.
#
# Purpose: generates and imports the form meshes, creates their materials and physical materials under Content/LastSeed/,
# creates the post-process material that keeps the player in colour, then fills in each form's data on BP_SeedBall.
# It is safe to rerun: each asset is replaced or rebuilt in place, and nothing in the Fab pack folders is changed.
# Requires: Python Editor Script Plugin. Run with Tools > Execute Python Script.

import importlib
import os

import unreal

import ls_generate_player_meshes

ROOT = "/Game/LastSeed"
MESH_FOLDER = ROOT + "/Meshes"
MATERIAL_FOLDER = ROOT + "/Materials"
PHYSICS_FOLDER = ROOT + "/Physics"
BALL_BLUEPRINT = "/Game/Blueprint/BP_SeedBall"
GLOW_EFFECT = "/Game/FreeParticle_SoftTofu/Niagara/NS_Sparkling_Glow"

assets = unreal.AssetToolsHelpers.get_asset_tools()
library = unreal.MaterialEditingLibrary


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
        unreal.EditorAssetLibrary.save_loaded_asset(meshes[name])
    return meshes


def check_mesh_placement(meshes):
    """The sprout only stays on top of the ball if the import kept Z as up, so this catches a wrong axis or scale."""
    sprout = meshes["SM_LS_SeedSprout"].get_bounds()
    lowest = sprout.origin.z - sprout.box_extent.z
    shell = meshes["SM_LS_SeedShell"].get_bounds()
    if lowest < 40.0 or abs(shell.box_extent.z - 50.0) > 2.0:
        raise RuntimeError("Last Seed player assets: meshes imported at the wrong scale or axis (sprout bottom {:.1f}, shell half height {:.1f})".format(
            lowest, shell.box_extent.z))


# --- Material helpers ---

def fresh_material(name):
    """Returns an empty material, so a rerun rebuilds the graph instead of adding to it."""
    path = "{}/{}".format(MATERIAL_FOLDER, name)
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        material = unreal.load_asset(path)
        library.delete_all_material_expressions(material)
        return material
    return assets.create_asset(name, MATERIAL_FOLDER, unreal.Material, unreal.MaterialFactoryNew())


def node(material, expression_class, **properties):
    expression = library.create_material_expression(material, expression_class)
    for key, value in properties.items():
        expression.set_editor_property(key, value)
    return expression


def colour(material, r, g, b):
    return node(material, unreal.MaterialExpressionConstant3Vector, constant=unreal.LinearColor(r, g, b, 1.0))


def number(material, value):
    return node(material, unreal.MaterialExpressionConstant, r=value)


def mask(material, source, red):
    """Picks the red or green channel of a node, which is how the graphs read the masks stored in the UVs."""
    picked = node(material, unreal.MaterialExpressionComponentMask, r=red, g=not red, b=False, a=False)
    library.connect_material_expressions(source, "", picked, "")
    return picked


def blend(material, a, b, alpha):
    lerp = node(material, unreal.MaterialExpressionLinearInterpolate)
    library.connect_material_expressions(a, "", lerp, "A")
    library.connect_material_expressions(b, "", lerp, "B")
    library.connect_material_expressions(alpha, "", lerp, "Alpha")
    return lerp


def combine(material, expression_class, a, b):
    result = node(material, expression_class)
    library.connect_material_expressions(a, "", result, "A")
    library.connect_material_expressions(b, "", result, "B")
    return result


def finish(material):
    library.layout_material_expressions(material)
    library.recompile_material(material)
    unreal.EditorAssetLibrary.save_loaded_asset(material)
    return material


# --- The materials ---

def build_seed_material():
    """Warm gold with a soft glow, plus a brighter rim at the edge of the ball."""
    material = fresh_material("M_LS_Seed")
    ridge = mask(material, node(material, unreal.MaterialExpressionTextureCoordinate), True)
    base = blend(material, colour(material, 0.62, 0.32, 0.06), colour(material, 1.0, 0.68, 0.22), ridge)
    library.connect_material_property(base, "", unreal.MaterialProperty.MP_BASE_COLOR)
    library.connect_material_property(number(material, 0.22), "", unreal.MaterialProperty.MP_ROUGHNESS)

    body_glow = combine(material, unreal.MaterialExpressionMultiply, base, number(material, 0.15))
    fresnel = node(material, unreal.MaterialExpressionFresnel, exponent=3.0)
    rim = combine(material, unreal.MaterialExpressionMultiply, fresnel, colour(material, 1.5, 0.8, 0.2))
    emissive = combine(material, unreal.MaterialExpressionAdd, body_glow, rim)
    library.connect_material_property(emissive, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    return finish(material)


def build_sprout_material():
    material = fresh_material("M_LS_Sprout")
    material.set_editor_property("two_sided", True)
    along = mask(material, node(material, unreal.MaterialExpressionTextureCoordinate), False)
    base = blend(material, colour(material, 0.28, 0.5, 0.08), colour(material, 0.55, 0.85, 0.2), along)
    library.connect_material_property(base, "", unreal.MaterialProperty.MP_BASE_COLOR)
    library.connect_material_property(number(material, 0.55), "", unreal.MaterialProperty.MP_ROUGHNESS)
    glow = combine(material, unreal.MaterialExpressionMultiply, base, number(material, 0.4))
    library.connect_material_property(glow, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    return finish(material)


def build_stone_material():
    """Grey rock plates with glowing golden light in the cracks between them."""
    material = fresh_material("M_LS_Stone")
    uv = node(material, unreal.MaterialExpressionTextureCoordinate)
    crack = mask(material, uv, True)
    tone = mask(material, uv, False)
    rock = blend(material, colour(material, 0.13, 0.13, 0.14), colour(material, 0.27, 0.26, 0.25), tone)
    base = blend(material, rock, colour(material, 0.03, 0.02, 0.01), crack)
    library.connect_material_property(base, "", unreal.MaterialProperty.MP_BASE_COLOR)
    library.connect_material_property(number(material, 0.92), "", unreal.MaterialProperty.MP_ROUGHNESS)
    glow = combine(material, unreal.MaterialExpressionMultiply, crack, colour(material, 9.0, 5.0, 1.2))
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
    """Greys the screen by the Saturation parameter, except pixels marked with stencil 1. ARestorationDriver loads this."""
    material = fresh_material("M_LS_WitherPost")
    material.set_editor_property("material_domain", unreal.MaterialDomain.MD_POST_PROCESS)

    scene = node(material, unreal.MaterialExpressionSceneTexture, scene_texture_id=unreal.SceneTextureId.PPI_POST_PROCESS_INPUT0)
    stencil = node(material, unreal.MaterialExpressionSceneTexture, scene_texture_id=unreal.SceneTextureId.PPI_CUSTOM_STENCIL)
    saturation = node(material, unreal.MaterialExpressionScalarParameter, parameter_name="Saturation", default_value=1.0)

    grey = node(material, unreal.MaterialExpressionCustom)
    grey.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    grey.set_editor_property("code",
        "float Luminance = dot(Scene.rgb, float3(0.2126, 0.7152, 0.0722));\n"
        "return Stencil.r > 0.5 ? Scene.rgb : lerp(Luminance.xxx, Scene.rgb, Saturation);")
    inputs = []
    for name in ("Scene", "Stencil", "Saturation"):
        custom_input = unreal.CustomInput()
        custom_input.set_editor_property("input_name", name)
        inputs.append(custom_input)
    grey.set_editor_property("inputs", inputs)

    library.connect_material_expressions(scene, "Color", grey, "Scene")
    library.connect_material_expressions(stencil, "Color", grey, "Stencil")
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
    unreal.EditorAssetLibrary.save_loaded_asset(physical)
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
    unreal.EditorAssetLibrary.save_loaded_asset(blueprint)


def main():
    meshes = import_meshes()
    check_mesh_placement(meshes)

    seed_material = build_seed_material()
    sprout_material = build_sprout_material()
    stone_material = build_stone_material()
    dandelion_material = build_dandelion_material()
    core_material = build_core_material()
    build_wither_post_material()

    glow = unreal.load_asset(GLOW_EFFECT)
    if not glow:
        unreal.log_warning("Last Seed player assets: {} not found, so the forms have no particles".format(GLOW_EFFECT))

    assign_to_ball({
        unreal.SeedForm.SEED: {
            "mesh": meshes["SM_LS_SeedShell"], "material": seed_material,
            "upright_mesh": meshes["SM_LS_SeedSprout"], "upright_material": sprout_material,
            "glow_effect": glow, "glow_color": unreal.LinearColor(1.0, 0.72, 0.3, 1.0), "glow_brightness": 40.0,
            "physical_material": build_physical_material("PM_Seed", 0.7, 0.1),
        },
        unreal.SeedForm.STONE: {
            "mesh": meshes["SM_LS_StoneShell"], "material": stone_material,
            "upright_mesh": None, "upright_material": None,
            "glow_effect": None, "glow_color": unreal.LinearColor(1.0, 0.6, 0.2, 1.0), "glow_brightness": 12.0,
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
    unreal.log("Last Seed player assets: built 6 materials in {} and 3 physical materials in {}".format(MATERIAL_FOLDER, PHYSICS_FOLDER))
    unreal.log("Last Seed player assets: assigned everything to {}. Press Play to see it.".format(BALL_BLUEPRINT))


main()
