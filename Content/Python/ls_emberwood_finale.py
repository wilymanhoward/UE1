"""Import the illustrated finale cards without rebuilding either level."""

from pathlib import Path

import unreal

from ls_witch_ambush import shot_art, shot_motion


FOLDER = "/Game/LastSeed/Intro/EmberwoodFinale"
SOURCE = "EmberwoodFinale"
MATERIAL = "M_LS_EmberwoodFinaleMotion"


def build():
    def import_art(name):
        return shot_art(name, folder=FOLDER, source_folder=SOURCE)

    exile = "/Game/LastSeed/Intro/WitchExile"
    planting = unreal.load_asset(exile + "/T_LS_PlantingSoil")
    seed = unreal.load_asset(exile + "/T_LS_PlantingSeedSprite")
    forest = import_art("WildwoodRestored")
    witch = import_art("CastleWitchShock")
    tree = import_art("HeartTreeSprite")
    assert all((planting, seed, forest, witch, tree))
    textures = {"SeedTex": seed, "TreeTex": tree}
    shader = Path(__file__).with_suffix(".hlsl")
    shots = (("SeedTakesRoot", planting, 0), ("WildwoodRestored", forest, 1), ("CastleWitchShock", witch, 2))
    for name, art, cue in shots:
        assert shot_motion(name, art, cue, folder=FOLDER, material_name=MATERIAL,
                           shader=shader, textures=textures)

    material = unreal.load_asset(FOLDER + "/" + MATERIAL)
    graph = unreal.MaterialEditingLibrary
    node = graph.get_material_property_input_node(material, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    code = shader.read_text()
    if node.get_editor_property("code") != code:
        node.modify()
        node.set_editor_property("code", code)
        graph.recompile_material(material)
        assert unreal.EditorAssetLibrary.save_loaded_asset(material, False)
