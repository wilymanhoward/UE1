"""Build the Wildwood intro's UI material, shot instances, and painted motion layers."""
from pathlib import Path

import unreal

FOLDER = "/Game/LastSeed/Intro/Anime/Motion"
ART = "/Game/LastSeed/Intro/Anime"
LAYER_SOURCES = ("OpenForestPlate", "OpenForestSprites", "CurseFlightPlate", "FallPlate", "LandingPlate")
SHOT_LAYERS = {1: "OpenForestPlate", 2: "OpenForestPlate", 5: None, 7: "CurseFlightPlate", 9: None, 11: None, 14: "FallPlate", 15: "LandingPlate"}
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
EDITOR = unreal.EditorAssetLibrary
MATERIAL_EDITOR = unreal.MaterialEditingLibrary


def build_material(default_frame, seed):
    name = "M_LS_IntroMotion"
    material = EDITOR.load_asset(f"{FOLDER}/{name}") if EDITOR.does_asset_exist(f"{FOLDER}/{name}") else None
    if not material:
        material = TOOLS.create_asset(name, FOLDER, unreal.Material, unreal.MaterialFactoryNew())
    MATERIAL_EDITOR.delete_all_material_expressions(material)
    material.set_editor_property("material_domain", unreal.MaterialDomain.MD_UI)
    material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)

    uv = MATERIAL_EDITOR.create_material_expression(material, unreal.MaterialExpressionTextureCoordinate, -530, -180)
    inputs = {"UV": uv}
    for row, (param, texture) in enumerate({
        "FrameTex": default_frame, "OtherTex": default_frame, "LayerTex": default_frame, "SeedTex": seed,
    }.items()):
        node = MATERIAL_EDITOR.create_material_expression(material, unreal.MaterialExpressionTextureObjectParameter, -530, row * 120)
        node.set_editor_properties({"parameter_name": param, "texture": texture, "sampler_type": unreal.MaterialSamplerType.SAMPLERTYPE_COLOR})
        inputs[param] = node

    for row, param in enumerate(("Cue", "ShotTime")):
        node = MATERIAL_EDITOR.create_material_expression(material, unreal.MaterialExpressionScalarParameter, -530, 510 + row * 100)
        node.set_editor_property("parameter_name", param)
        inputs[param] = node

    custom = MATERIAL_EDITOR.create_material_expression(material, unreal.MaterialExpressionCustom, -100, 0)
    pins = []
    for name in inputs:
        pin = unreal.CustomInput()
        pin.set_editor_property("input_name", name)
        pins.append(pin)
    custom.set_editor_properties({
        "description": "Wildwood shot motion",
        "inputs": pins,
        "output_type": unreal.CustomMaterialOutputType.CMOT_FLOAT3,
        "code": Path(__file__).with_suffix(".hlsl").read_text(encoding="utf-8-sig"),
    })
    for name, node in inputs.items():
        assert MATERIAL_EDITOR.connect_material_expressions(node, "", custom, name), name
    assert MATERIAL_EDITOR.connect_material_property(custom, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    opacity = MATERIAL_EDITOR.create_material_expression(material, unreal.MaterialExpressionConstant, -100, 260)
    opacity.set_editor_property('r', 1.0)
    assert MATERIAL_EDITOR.connect_material_property(opacity, '', unreal.MaterialProperty.MP_OPACITY)
    MATERIAL_EDITOR.recompile_material(material)
    assert EDITOR.save_loaded_asset(material, False)
    return material


def import_layers(names=LAYER_SOURCES):
    source = Path(unreal.Paths.project_content_dir()) / "LastSeed" / "SourceIntro" / "Anime" / "Motion"
    tasks = []
    for name in names:
        filename = source / f"{name}.png"
        assert filename.is_file(), filename
        task = unreal.AssetImportTask()
        task.set_editor_properties({
            "filename": str(filename), "destination_path": FOLDER, "destination_name": name,
            "automated": True, "replace_existing": True, "save": False,
        })
        tasks.append(task)
    TOOLS.import_asset_tasks(tasks)

    layers = {}
    for name in names:
        texture = unreal.load_asset(f"{FOLDER}/{name}")
        assert isinstance(texture, unreal.Texture2D), name
        texture.set_editor_properties({
            "lod_group": unreal.TextureGroup.TEXTUREGROUP_UI,
            "mip_gen_settings": unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS,
            "never_stream": True,
        })
        if name == "OpenForestSprites":
            texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_EDITOR_ICON)
        assert EDITOR.save_loaded_asset(texture, False)
        layers[name] = texture
    return layers


def build():
    frames = {number: unreal.load_asset(f"{ART}/T_LS_Intro_{number:02d}") for number in SHOT_LAYERS}
    assert all(isinstance(frame, unreal.Texture2D) for frame in frames.values())
    layers = import_layers()
    material = build_material(frames[1], frames[15])
    instances = {}
    for cue, (number, layer) in enumerate(SHOT_LAYERS.items(), start=1):
        name = f"MI_LS_IntroMotion_{number:02d}"
        path = f"{FOLDER}/{name}"
        instance = EDITOR.load_asset(path) if EDITOR.does_asset_exist(path) else None
        if not instance:
            instance = TOOLS.create_asset(name, FOLDER, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        MATERIAL_EDITOR.set_material_instance_parent(instance, material)
        MATERIAL_EDITOR.clear_all_material_instance_parameters(instance)
        MATERIAL_EDITOR.set_material_instance_scalar_parameter_value(instance, "Cue", float(cue))
        MATERIAL_EDITOR.set_material_instance_texture_parameter_value(instance, "FrameTex", frames[number])
        if layer:
            MATERIAL_EDITOR.set_material_instance_texture_parameter_value(instance, "LayerTex", layers[layer])
        if number in (1, 2):
            MATERIAL_EDITOR.set_material_instance_texture_parameter_value(instance, "SeedTex", layers["OpenForestSprites"])
        if number == 5:
            MATERIAL_EDITOR.set_material_instance_texture_parameter_value(instance, "OtherTex", frames[2])
        MATERIAL_EDITOR.update_material_instance(instance)
        assert MATERIAL_EDITOR.get_material_instance_scalar_parameter_value(instance, "Cue") == float(cue)
        assert MATERIAL_EDITOR.get_material_instance_texture_parameter_value(instance, "FrameTex") == frames[number]
        if layer:
            assert MATERIAL_EDITOR.get_material_instance_texture_parameter_value(instance, "LayerTex") == layers[layer]
        assert EDITOR.save_loaded_asset(instance, False)
        instances[number] = instance
    return instances

