# Last Seed - small helpers for building material graphs from Python.
#
# Purpose: shared by the scripts that create materials, so each material function reads as a short list of nodes.
# Rebuilding is safe: fresh_material empties an existing material instead of adding to its old graph.

import unreal

MATERIAL_FOLDER = "/Game/LastSeed/Materials"

library = unreal.MaterialEditingLibrary


def fresh_material(name):
    path = "{}/{}".format(MATERIAL_FOLDER, name)
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        material = unreal.load_asset(path)
        library.delete_all_material_expressions(material)
        return material
    return unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, MATERIAL_FOLDER, unreal.Material, unreal.MaterialFactoryNew())


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
    unreal.EditorAssetLibrary.save_loaded_asset(material, False)
    return material


def output(material, source, pin):
    library.connect_material_property(source, "", pin)


def world_uv(material, tile_size_cm):
    """Texture coordinates from the world position, so a texture keeps the same size however an object is stretched."""
    position = mask_rg(material, node(material, unreal.MaterialExpressionWorldPosition))
    return combine(material, unreal.MaterialExpressionDivide, position, number(material, tile_size_cm))


def mask_rg(material, source):
    picked = node(material, unreal.MaterialExpressionComponentMask, r=True, g=True, b=False, a=False)
    library.connect_material_expressions(source, "", picked, "")
    return picked


def texture(material, path, uv):
    sample = node(material, unreal.MaterialExpressionTextureSample, texture=unreal.load_asset(path))
    library.connect_material_expressions(uv, "", sample, "UVs")
    return sample
