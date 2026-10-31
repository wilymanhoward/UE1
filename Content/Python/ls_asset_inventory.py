# Last Seed - lists what the Fab packs contain, so the world scripts can choose assets by real size and type.
#
# Purpose: writes every static mesh, material, Niagara system and sky or cloud asset to Saved/LS_AssetInventory.csv,
# with its bounds size and a guessed category. It only reads: nothing is changed or saved in the Fab folders.
# Requires: Python Editor Script Plugin. Run with Tools > Execute Python Script.

import csv
import os

import unreal

FAB_FOLDERS = ["/Game/Polytope_Studio", "/Game/StyleHex_Studio", "/Game/Stylized_PBR_Nature",
               "/Game/RocksPackDEMO", "/Game/FreeParticle_SoftTofu", "/Game/StylizedVolClouds"]

MESH_CLASSES = {"StaticMesh"}
MATERIAL_CLASSES = {"Material", "MaterialInstanceConstant"}
PARTICLE_CLASSES = {"NiagaraSystem"}
# A sky blueprint or a map shows how a pack sets up its sky, so those are listed from the cloud pack only.
CLOUD_ONLY_CLASSES = {"Blueprint", "World", "VolumeTexture"}

# Checked in order, so more specific words come first: "tree_dead" is a dead tree, "tree_stump" is a log.
NAME_RULES = [
    ("ice/snow", ("snow", "frost", "frozen", "_ice", "icicle")),
    ("water", ("water", "river", "lake", "ocean", "puddle")),
    ("log", ("log", "stump", "trunk", "_cut")),
    ("root", ("root",)),
    ("ruin", ("ruin", "pillar", "column", "arch", "wall", "brick", "statue", "fence")),
    ("cliff", ("cliff", "background", "mountain", "rockgroup", "menhir")),
    ("dead tree", ("tree_01_dead", "tree_03_dead", "dead_tree", "tree_dead", "deadtree")),
    ("living tree", ("tree", "birch", "broadleaf", "pine", "oak", "fir")),
    ("grass", ("grass", "clover", "fern", "plant", "weed")),
    ("flower", ("flower", "poppy", "daisy", "mushroom")),
    ("bush", ("bush", "shrub", "hedge")),
    ("rock", ("rock", "stone", "boulder", "pebble", "ore")),
]


def guess_category(name, class_name):
    if class_name in PARTICLE_CLASSES:
        return "particles"
    lowered = name.lower()
    for category, words in NAME_RULES:
        if any(word in lowered for word in words):
            return category
    if "cloud" in lowered or "sky" in lowered:
        return "sky/cloud"
    return "unknown"


def describe_mesh(mesh):
    """Returns size in cm, triangles, collision shapes and whether Nanite is on."""
    bounds = mesh.get_bounds()
    extent = bounds.box_extent
    # This subsystem only exists with the editor window open. The column is left blank otherwise.
    meshes = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    collision = meshes.get_simple_collision_count(mesh) if meshes else ""
    nanite = mesh.get_editor_property("nanite_settings").get_editor_property("enabled")
    return (round(extent.x * 2), round(extent.y * 2), round(extent.z * 2), mesh.get_num_triangles(0), collision, nanite)


def main():
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    rows = []
    counts = {}

    for folder in FAB_FOLDERS:
        for data in registry.get_assets_by_path(folder, recursive=True):
            class_name = str(data.asset_class_path.asset_name)
            is_cloud_extra = folder.endswith("StylizedVolClouds") and class_name in CLOUD_ONLY_CLASSES
            if class_name not in MESH_CLASSES | MATERIAL_CLASSES | PARTICLE_CLASSES and not is_cloud_extra:
                continue

            name = str(data.asset_name)
            path = str(data.package_name)
            category = "sky/cloud" if folder.endswith("StylizedVolClouds") else guess_category(name, class_name)
            size_x = size_y = size_z = triangles = collision = nanite = ""
            if class_name in MESH_CLASSES:
                size_x, size_y, size_z, triangles, collision, nanite = describe_mesh(unreal.load_asset(path))

            rows.append([folder.split("/")[-1], class_name, category, name, path, size_x, size_y, size_z, triangles, collision, nanite])
            counts[category] = counts.get(category, 0) + 1

    rows.sort(key=lambda row: (row[1], row[2], row[0], row[3]))

    output = os.path.join(unreal.Paths.project_saved_dir(), "LS_AssetInventory.csv")
    with open(output, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Pack", "Class", "Category", "Name", "Path", "SizeX_cm", "SizeY_cm", "SizeZ_cm", "Triangles", "SimpleCollision", "Nanite"])
        writer.writerows(rows)

    unreal.log("Last Seed inventory: {} assets written to {}".format(len(rows), output))
    for category in sorted(counts):
        unreal.log("Last Seed inventory: {} = {}".format(category, counts[category]))


main()
