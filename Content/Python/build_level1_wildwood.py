# Last Seed - builds Level 1 in the Wildwood forest: a long winding trail with parkour, through a forest that starts
# dead and grows back as Life Notes are found.
#
# Purpose: L_Level1_Wildwood is a copy of the Wildwood demo map, so it has that pack's landscape, lighting and forest.
# ls_wildwood_plan.py (run outside Unreal) works out the trail, and this script applies it in the editor:
#   trail      imports the walkable trail meshes the plan wrote, laid over the untouched landscape
#   foliage    rebuilds the Wildwood foliage without what stood on the trail
#   scenery    removes the demo's loose rocks on the trail and its animals, and turns nearby trees into regrowing ones
#   gameplay   places every set piece, pickup, volume and hidden wall from the plan
#   hand       puts back the rocks and logs placed by hand (ls_hand_placed.json); protect records them first
#   extras     adds the planner's extra obstacles to a level that is already open, touching nothing else
#   world      the restoration driver, music, sky and game mode
#   leaves     makes the Wildwood leaf material bare until restoration brings the leaves back
# Run each stage in STAGES order, one call each: run("foliage"), run("clear"), and so on.
# Safe to rerun: generated actors are tagged and replaced.
# Requires: Python Editor Script Plugin, and the plan files in Saved/LS.

import importlib
import json
import math
import os
import random

import unreal

import ls_world_common

for module in (ls_world_common,):
    importlib.reload(module)

from ls_world_common import base_height_offset, hide_component, invisible_wall, kill_volume, mesh_actor, niagara, point_light, spawn

MAP = "/Game/LastSeed/Maps/L_Level1_Wildwood"
WORK = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()) + "LS/"
FOLIAGE_TAG = "LS_Foliage"  # The rebuilt Wildwood foliage. Kept apart from LS_Generated, which every rerun clears.
MOVED_TAG = "LS_Moved"
SEED = 4127

MESH_FOLDERS = ["/Game/Wildwood/Model/Tree", "/Game/Wildwood/Model/Rocks", "/Game/Wildwood/Model/Foliage",
                "/Game/Wildwood/Model/DeadTrunk", "/Game/Wildwood/Model/Mushroom", "/Game/LastSeed/Meshes"]
LS = "/Game/LastSeed/Materials/"
DEAD_STUMPS = ["SM_DeadTrunk_01", "SM_DeadTrunk_02", "SM_DeadTrunk_03"]
BOULDERS = ["SM_Boulder_07", "SM_Boulder_08", "SM_Boulder_09", "SM_Boulder_10"]
LEAF_MASTER = "/Game/Wildwood/Material/Snow/MM_Tree_LeavesWind_Snow_01"
LEAF_TAG = "LS_LeafGrowth"

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
rng = random.Random(SEED)
_meshes = {}


def mesh(name):
    """A mesh's asset path from its name, looked up in the Wildwood and Last Seed folders."""
    if name not in _meshes:
        for folder in MESH_FOLDERS:
            path = "{}/{}".format(folder, name)
            if unreal.EditorAssetLibrary.does_asset_exist(path):
                _meshes[name] = path
                break
        else:
            raise RuntimeError("Last Seed Wildwood: no mesh called " + name)
    return _meshes[name]


def load_plan():
    from ls_natural_trail01 import patch_plan
    from ls_trail05_riverbank import obsolete_obstacle

    plan = patch_plan(json.load(open(WORK + "plan.json")))
    plan["actors"] = [entry for entry in plan["actors"] if not obsolete_obstacle(entry)]
    return plan


def require_map():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world.get_path_name().split(".")[0] != MAP:
        raise RuntimeError("Last Seed Wildwood: open {} first. Nothing was changed.".format(MAP))
    return world


def tagged(tag):
    return [actor for actor in actors.get_all_level_actors() if tag in [str(t) for t in actor.tags]]


def material(name):
    return unreal.load_asset(LS + name)


# --- The trail ---

TRAIL_FOLDER = "/Game/LastSeed/Generated/WildwoodTrail"
TRAIL_MATERIAL = "/Game/LastSeed/Materials/M_LS_WildwoodTrail"
DIRT_TEXTURE = "/Game/Wildwood/Texture/Landscape/T_Dirt_01_BaseColor"
GRASS_TEXTURE = "/Game/Wildwood/Model/Grass/Grass/Grass/Textures/T_Grass_Tile_C"


def trail_material():
    """The Wildwood dirt down the middle of the trail, fading to the landscape's own tinted grass on the banks.
    The trail mesh's V coordinate is the distance from the middle, 1 at the lane's edge."""
    if unreal.EditorAssetLibrary.does_asset_exist(TRAIL_MATERIAL):
        return unreal.load_asset(TRAIL_MATERIAL)
    lib = unreal.MaterialEditingLibrary
    folder, name = TRAIL_MATERIAL.rsplit("/", 1)
    built = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
    world_position = lib.create_material_expression(built, unreal.MaterialExpressionWorldPosition, -1400, 0)
    flat = lib.create_material_expression(built, unreal.MaterialExpressionComponentMask, -1200, 0)
    flat.set_editor_properties({"r": True, "g": True, "b": False, "a": False})
    lib.connect_material_expressions(world_position, "", flat, "")

    def tiled(texture, size, y):
        scale = lib.create_material_expression(built, unreal.MaterialExpressionDivide, -1000, y)
        scale.set_editor_property("const_b", size)
        lib.connect_material_expressions(flat, "", scale, "A")
        sample = lib.create_material_expression(built, unreal.MaterialExpressionTextureSample, -800, y)
        sample.set_editor_property("texture", unreal.load_asset(texture))
        lib.connect_material_expressions(scale, "", sample, "UVs")
        return sample

    dirt = tiled(DIRT_TEXTURE, 400.0, -200)
    grass = tiled(GRASS_TEXTURE, 600.0, 200)
    tint = lib.create_material_expression(built, unreal.MaterialExpressionConstant3Vector, -800, 450)
    tint.set_editor_property("constant", unreal.LinearColor(0.72, 0.76, 0.5, 1.0))  # The landscape's own grass tint.
    tinted = lib.create_material_expression(built, unreal.MaterialExpressionMultiply, -550, 250)
    lib.connect_material_expressions(grass, "RGB", tinted, "A")
    lib.connect_material_expressions(tint, "", tinted, "B")
    coordinate = lib.create_material_expression(built, unreal.MaterialExpressionTextureCoordinate, -1000, 650)
    across = lib.create_material_expression(built, unreal.MaterialExpressionComponentMask, -800, 650)
    across.set_editor_properties({"r": False, "g": True, "b": False, "a": False})
    lib.connect_material_expressions(coordinate, "", across, "")
    edge = lib.create_material_expression(built, unreal.MaterialExpressionSmoothStep, -550, 650)
    edge.set_editor_properties({"const_min": 0.72, "const_max": 1.05})
    lib.connect_material_expressions(across, "", edge, "Value")
    blend = lib.create_material_expression(built, unreal.MaterialExpressionLinearInterpolate, -300, 0)
    lib.connect_material_expressions(dirt, "RGB", blend, "A")
    lib.connect_material_expressions(tinted, "", blend, "B")
    lib.connect_material_expressions(edge, "", blend, "Alpha")
    lib.connect_material_property(blend, "", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = lib.create_material_expression(built, unreal.MaterialExpressionConstant, -300, 300)
    rough.set_editor_property("r", 0.95)
    lib.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    lib.recompile_material(built)
    unreal.EditorAssetLibrary.save_loaded_asset(built)
    return built


def import_trail_mesh(name, source=None):
    """Imports one trail piece with its exact triangles as collision, so the ball rolls on the surface it sees."""
    path = "{}/{}".format(TRAIL_FOLDER, name)
    task = unreal.AssetImportTask()
    task.filename = str(source) if source else WORK + name + ".obj"
    task.destination_path = TRAIL_FOLDER
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    loaded = unreal.load_asset(path)
    if not loaded:
        raise RuntimeError("Last Seed Wildwood: trail piece {} did not import".format(name))
    subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    settings = loaded.get_editor_property("nanite_settings")
    settings.set_editor_property("enabled", False)
    subsystem.set_nanite_settings(loaded, settings, True)
    subsystem.remove_collisions(loaded)
    loaded.get_editor_property("body_setup").set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    unreal.EditorAssetLibrary.save_loaded_asset(loaded, False)
    return path


def trail(plan):
    from ls_blend_trail_banks import NAMES, blend_source

    surface = trail_material()
    for name in plan["trail_meshes"]:
        source = blend_source(name) if name in NAMES else None
        actor = mesh_actor(import_trail_mesh(name, source), 0.0, 0.0, 0.0, "Trail", label=name, material=surface)
        actor.static_mesh_component.set_collision_profile_name("BlockAll")
    return len(plan["trail_meshes"])


# --- Foliage ---

def ground_cover_distances(mesh_name):
    if mesh_name == "SM_Grass_01":
        return 2200, 3500
    if mesh_name.startswith("SM_Flowers_"):
        return 3000, 4500
    return None


def add_instanced(label, folder, mesh_path, transforms, settings, tag):
    """One actor holding one hierarchical instanced mesh, like a foliage type."""
    actor = spawn(unreal.Actor, 0, 0, 0, label, folder)
    actor.tags = [tag]
    systems = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    handles = systems.k2_gather_subobject_data_for_instance(actor)
    params = unreal.AddNewSubobjectParams(parent_handle=handles[0], new_class=unreal.HierarchicalInstancedStaticMeshComponent, blueprint_context=None)
    systems.add_new_subobject(params)
    component = actor.get_components_by_class(unreal.HierarchicalInstancedStaticMeshComponent)[0]
    component.set_static_mesh(unreal.load_asset(mesh_path))
    for index, path in enumerate(settings.get("materials", [])):
        if path:
            component.set_material(index, unreal.load_asset(path))
    name = mesh_path.rsplit("/", 1)[-1].split(".")[0]
    start, end = ground_cover_distances(name) or settings.get("cull", [0, 0])
    component.set_cull_distances(start, end)
    component.set_cast_shadow(settings.get("shadow", True))
    component.set_collision_profile_name(settings.get("collision", "NoCollision"))
    if settings.get("wpo_distance"):
        component.set_editor_property("world_position_offset_disable_distance", settings["wpo_distance"])
    component.add_instances(transforms, False, True)
    return actor


def transform_of(row):
    x, y, z, pitch, yaw, roll, sx, sy, sz = row
    return unreal.Transform(location=unreal.Vector(x, y, z), rotation=unreal.Rotator(roll, pitch, yaw), scale=unreal.Vector(sx, sy, sz))


def rebuild_foliage():
    """Replaces the demo's foliage actor with plain instanced meshes, which a script can edit safely."""
    for actor in tagged(FOLIAGE_TAG):
        actors.destroy_actor(actor)
    groups = json.load(open(WORK + "foliage_new.json"))
    total = 0
    for group in groups:
        if not group["t"]:
            continue
        name = group["mesh"].rsplit("/", 1)[-1].split(".")[0]
        add_instanced("Foliage_" + name, "Foliage", group["mesh"].split(".")[0], [transform_of(row) for row in group["t"]], group, FOLIAGE_TAG)
        total += len(group["t"])
    for actor in actors.get_all_level_actors():
        if isinstance(actor, unreal.InstancedFoliageActor):
            actors.destroy_actor(actor)
    return total


# --- Regrowing trees ---

TREE_SOUND_SOURCE = os.path.join(unreal.Paths.project_content_dir(), "LastSeed", "SourceSounds", "SFX_LS_TreeGrow.wav")
TREE_SOUND = "/Game/LastSeed/Audio/SFX_LS_TreeGrow"


def tree_sound():
    """Imports the recorded tree growth sound once, with a falloff so a tree is loud close by
    and silent from across the map."""
    if not unreal.EditorAssetLibrary.does_asset_exist(TREE_SOUND):
        folder, name = TREE_SOUND.rsplit("/", 1)
        task = unreal.AssetImportTask()
        task.filename = TREE_SOUND_SOURCE
        task.destination_path = folder
        task.destination_name = name
        task.automated = True
        task.replace_existing = True
        task.save = True
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        falloff = unreal.AssetToolsHelpers.get_asset_tools().create_asset("SA_LS_TreeGrow", folder, unreal.SoundAttenuation, unreal.SoundAttenuationFactory())
        settings = falloff.get_editor_property("attenuation")
        settings.set_editor_property("attenuation_shape_extents", unreal.Vector(800.0, 0.0, 0.0))  # Full volume within 8 m.
        settings.set_editor_property("falloff_distance", 5000.0)  # Silent 58 m away.
        falloff.set_editor_property("attenuation", settings)
        unreal.EditorAssetLibrary.save_loaded_asset(falloff)
        sound = unreal.load_asset(TREE_SOUND)
        sound.set_editor_property("attenuation_settings", falloff)
        unreal.EditorAssetLibrary.save_loaded_asset(sound)
    return unreal.load_asset(TREE_SOUND)


def restorable(x, y, z, yaw, mesh_path, scale, withered_path=None, withered_scale=1.0, threshold=2.0, radius=900.0,
               grow=0.6, bounce=1.7, folder="Regrowth", label="Regrowth", pitch=0.0, roll=0.0, shake=0.0, delay=0.0, sound=None):
    actor = spawn(unreal.load_class(None, "/Script/Assignment1.RestorableActor"), x, y, z, label, folder, yaw)
    actor.set_actor_rotation(unreal.Rotator(roll, pitch, yaw), False)
    actor.set_editor_property("restoration_threshold", threshold)
    actor.set_editor_property("note_radius", radius)
    actor.set_editor_property("grow_duration", grow)
    actor.set_editor_property("bounce_amount", bounce)
    actor.set_editor_properties({"shake_degrees": shake, "shake_frequency": 2.5, "max_start_delay": delay, "grow_sound": sound})
    components = {c.get_name(): c for c in actor.get_components_by_class(unreal.StaticMeshComponent)}
    grown = components["Mesh"]
    grown.set_static_mesh(unreal.load_asset(mesh_path))
    grown.set_relative_scale3d(scale if isinstance(scale, unreal.Vector) else unreal.Vector(scale, scale, scale))
    if withered_path:
        withered = components["WitheredMesh"]
        loaded = unreal.load_asset(withered_path)
        withered.set_static_mesh(loaded)
        withered.set_relative_scale3d(unreal.Vector(withered_scale, withered_scale, withered_scale))
        # Rests on the ground, as a dead trunk's origin isn't always at its base.
        withered.set_relative_location(unreal.Vector(0.0, 0.0, -base_height_offset(loaded, withered_scale) - 15.0), False, False)
    return actor


def dead_tree(x, y, z, yaw, tree_path, scale, pitch=0.0, roll=0.0):
    """A tree that stands as a dead stump until a note is found nearby, or the world is restored enough."""
    stump = rng.choice(DEAD_STUMPS)
    size = max(scale.z if isinstance(scale, unreal.Vector) else scale, 0.6)
    # Slow and swaying, with a sound, and a moment's wait so the trees round a note rise one after another.
    return restorable(x, y, z, yaw, tree_path, scale, mesh(stump), rng.uniform(0.9, 1.4) * min(size, 1.6), threshold=rng.uniform(0.45, 1.0),
                      radius=4200.0, grow=rng.uniform(3.5, 4.5), bounce=0.5, folder="Regrowth/Trees", label="DeadTree", pitch=pitch, roll=roll,
                      shake=4.0, delay=1.5, sound=tree_sound())


# --- Scenery ---

def scenery(plan):
    """The demo's loose rocks and trees: removed from the trail, moved with the ground, nearby trees made to regrow.
    Its animals go, as they'd wander onto the trail."""
    by_key = {}
    for actor in actors.get_all_level_actors():
        if isinstance(actor, unreal.StaticMeshActor) and not tagged_with(actor, ls_world_common.TAG):
            location = actor.get_actor_location()
            by_key[(actor.get_actor_label(), round(location.x), round(location.y))] = actor
    find = lambda key: by_key.get((key[0], key[1], key[2]))
    removed = moved = regrown = 0
    for key in plan["scenery"]["remove"]:
        actor = find(key)
        if actor:
            actors.destroy_actor(actor)
            removed += 1
    for key in plan["scenery"]["move"]:
        actor = find(key)
        if actor and not tagged_with(actor, MOVED_TAG):
            location = actor.get_actor_location()
            actor.set_actor_location(unreal.Vector(location.x, location.y, location.z + key[3]), False, False)
            actor.tags = list(actor.tags) + [MOVED_TAG]
            moved += 1
    # shortcut: these trees are the demo's own actors, so once replaced they are gone. Rerunning after "clear" loses
    # them; reopen a fresh copy of the Wildwood map if that matters.
    for key in plan["scenery"]["restore"]:
        actor = find(key)
        if actor:
            location, rotation = actor.get_actor_location(), actor.get_actor_rotation()
            dead_tree(location.x, location.y, location.z, rotation.yaw, actor.static_mesh_component.static_mesh.get_path_name().split(".")[0],
                      actor.get_actor_scale3d(), rotation.pitch, rotation.roll)
            actors.destroy_actor(actor)
            regrown += 1
    for actor in actors.get_all_level_actors():
        name = actor.get_class().get_name()
        if name in ("BP_Deer_C", "BP_Squirell_C") or isinstance(actor, unreal.PlayerStart):
            actors.destroy_actor(actor)
    for row in plan["restore_trees"]:
        path, x, y, z, pitch, yaw, roll, sx, sy, sz = row
        dead_tree(x, y, z, yaw, path.split(".")[0], unreal.Vector(sx, sy, sz), pitch, roll)
        regrown += 1
    return removed, moved, regrown


def tagged_with(actor, tag):
    return tag in [str(t) for t in actor.tags]


# --- Gameplay ---

def gameplay_class(blueprint, cpp):
    """Prefers the project's Blueprint child, which carries its art, and falls back to the C++ class."""
    path = "/Game/Blueprint/" + blueprint
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        return unreal.load_class(None, "{}.{}_C".format(path, blueprint))
    return unreal.load_class(None, "/Script/Assignment1." + cpp)


def keep_coloured(actor):
    """Things the player needs to find stay in colour while the world around them is grey."""
    components = actor.get_components_by_class(unreal.StaticMeshComponent)
    component = [item for item in components if item.get_name() == "Mesh"][0]
    for other in components:
        if other != component:
            hide_component(other)
            other.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    component.set_render_custom_depth(True)
    component.set_custom_depth_stencil_value(ls_world_common.FULL_COLOUR_STENCIL)
    return component


def fit_mesh(component, mesh_path, height, floor_offset):
    loaded = unreal.load_asset(mesh_path)
    bounds = loaded.get_bounds()
    scale = height / max(bounds.box_extent.z * 2.0, 1.0)
    component.set_static_mesh(loaded)
    component.set_editor_property("override_materials", [])
    component.set_relative_scale3d(unreal.Vector(scale, scale, scale))
    component.set_relative_location(unreal.Vector(0.0, 0.0, floor_offset - (bounds.origin.z - bounds.box_extent.z) * scale), False, False)


def fit_box(mesh_path, x, y, top, yaw, size_x, size_y, size_z, folder, label, material_asset=None):
    """A mesh stretched to fill a box whose top is at top, for rocks and logs that dress a plain collision shape."""
    loaded = unreal.load_asset(mesh_path)
    bounds = loaded.get_bounds()
    sx, sy, sz = (size_x / max(bounds.box_extent.x * 2.0, 1.0), size_y / max(bounds.box_extent.y * 2.0, 1.0),
                  size_z / max(bounds.box_extent.z * 2.0, 1.0))
    h = math.radians(yaw)
    ox, oy = bounds.origin.x * sx, bounds.origin.y * sy
    cx, cy = x - (ox * math.cos(h) - oy * math.sin(h)), y - (ox * math.sin(h) + oy * math.cos(h))
    cz = top - (bounds.origin.z + bounds.box_extent.z) * sz
    return mesh_actor(mesh_path, cx, cy, cz, folder, (sx, sy, sz), yaw, material_asset, label)


FLAT_ROCKS = ["/Game/Wildwood/Model/Rocks/SM_Boulder_08", "/Game/Wildwood/Model/Rocks/SM_Boulder_09", "/Game/Wildwood/Model/Rocks/SM_Boulder_10",
              "/Game/Wildwood/Model/Rocks/SM_Boulder_07"]
STACK_ROCKS = ["/Game/RocksPackDEMO/Environment/Rocks/SM_RockPack_Cliff_07_B", "/Game/RocksPackDEMO/Environment/Rocks/SM_RockPack_Cliff_07_D"]
TOP_ROCK = "/Game/RocksPackDEMO/Environment/Rocks/SM_RockPack_Rock_02"  # Low and broad, so a stone's top reads as flat.


def fit_rock(mesh_path, x, y, top, yaw, size_x, size_y, size_z, folder, label):
    """Like fit_box, but the rock keeps close to its own proportions: no side is stretched more than a third past the
    others. A stretched boulder reads as a spike."""
    bounds = unreal.load_asset(mesh_path).get_bounds()
    sx, sy, sz = (size_x / (bounds.box_extent.x * 2.0), size_y / (bounds.box_extent.y * 2.0), size_z / (bounds.box_extent.z * 2.0))
    u = math.sqrt(sx * sy)
    sx, sy = min(max(sx, 0.75 * u), 1.33 * u), min(max(sy, 0.75 * u), 1.33 * u)
    sz = min(max(sz, 0.6 * u), 1.4 * u)
    return fit_box(mesh_path, x, y, top, yaw, sx * bounds.box_extent.x * 2.0, sy * bounds.box_extent.y * 2.0, sz * bounds.box_extent.z * 2.0,
                   folder, label)


def stone_sound(name):
    folder = '/Game/LastSeed/Audio'
    path = folder + '/' + name
    if not unreal.EditorAssetLibrary.does_asset_exist(path):
        task = unreal.AssetImportTask()
        task.filename = os.path.join(unreal.Paths.project_content_dir(), 'LastSeed', 'SourceSounds', name + '.wav')
        task.destination_path = folder
        task.destination_name = name
        task.automated = True
        task.save = True
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        assert task.imported_object_paths, task.filename
    sound = unreal.load_asset(path)
    falloff_path = folder + '/SA_LS_CrossingStone'
    falloff = unreal.load_asset(falloff_path) if unreal.EditorAssetLibrary.does_asset_exist(falloff_path) else None
    if not falloff:
        falloff = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            'SA_LS_CrossingStone', folder, unreal.SoundAttenuation, unreal.SoundAttenuationFactory())
        settings = falloff.get_editor_property('attenuation')
        settings.set_editor_property('attenuation_shape_extents', unreal.Vector(450, 0, 0))
        settings.set_editor_property('falloff_distance', 2000.0)
        falloff.set_editor_property('attenuation', settings)
        unreal.EditorAssetLibrary.save_loaded_asset(falloff)
    sound.set_editor_property('attenuation_settings', falloff)
    unreal.EditorAssetLibrary.save_loaded_asset(sound)
    return sound


def add_collapsing_stone(cap, supports, wood=False):
    component = cap.get_component_by_class(unreal.CollapsingStoneComponent)
    if not component:
        subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        parent = subsystem.k2_gather_subobject_data_for_instance(cap)[0]
        handle, reason = subsystem.add_new_subobject(unreal.AddNewSubobjectParams(
            parent_handle=parent, new_class=unreal.CollapsingStoneComponent))
        assert not str(reason), str(reason)
        library = unreal.SubobjectDataBlueprintFunctionLibrary
        component = library.get_object(library.get_data(handle))
        assert isinstance(component, unreal.CollapsingStoneComponent)
    component.set_editor_property('support_actors', sorted(supports, key=lambda a: a.get_actor_location().z))
    component.set_editor_property('collapse_delay', 1.0)
    surface = 'Wood' if wood else 'Stone'
    component.set_editor_property('shake_sound', stone_sound('SFX_LS_' + surface + 'Shake'))
    component.set_editor_property('fall_sound', stone_sound('SFX_LS_' + surface + 'Fall'))
    return component


def rock_stack(x, y, top, radius, bottom, label, collapses=False):
    """A natural column of rock standing up from the riverbed: rough cliff chunks stacked down from a broad flat rock on
    top, each at its own proportions and turned a different way."""
    cap = collide(fit_rock(TOP_ROCK, x, y, top, rng.uniform(0, 360), radius * 2.3, radius * 2.3, 120.0, "Parkour", label))
    supports = []
    z = top - 60.0
    while z > bottom:
        chunk = rng.choice(STACK_ROCKS)
        bounds = unreal.load_asset(chunk).get_bounds()
        scale = radius * 2.1 / (bounds.box_extent.x * 2.0)
        supports.append(collide(fit_box(chunk, x + rng.uniform(-20, 20), y + rng.uniform(-20, 20), z, rng.uniform(0, 360), bounds.box_extent.x * 2.0 * scale,
                        bounds.box_extent.y * 2.0 * scale, bounds.box_extent.z * 2.0 * scale, "Parkour", label)))
        z -= bounds.box_extent.z * 2.0 * scale * 0.8
    if collapses:
        add_collapsing_stone(cap, supports)


def platform_rock(component):
    """Swaps a moving or crumbling platform's plain slab for a flat rock about the same size, which it also collides
    as. Returns how far above the actor the rock's top is, so the caller can set it at the planned height."""
    loaded = unreal.load_asset(TOP_ROCK)
    bounds = loaded.get_bounds()
    sx, sy = 300.0 / (bounds.box_extent.x * 2.0), 300.0 / (bounds.box_extent.y * 2.0)
    sz = (sx + sy) / 2.0 * 0.6
    component.set_static_mesh(loaded)
    component.set_editor_property("override_materials", [])
    component.set_relative_scale3d(unreal.Vector(sx, sy, sz))
    component.set_relative_location(unreal.Vector(-bounds.origin.x * sx, -bounds.origin.y * sy, -bounds.origin.z * sz), False, False)
    return bounds.box_extent.z * sz


def collide(actor):
    """Makes a rock or log solid with the collision of its own mesh, so the ball meets the shape it sees. The boulders
    collide as their exact triangles; the log and the stacked rocks as a hull wrapped round the mesh."""
    actor.static_mesh_component.set_collision_profile_name("BlockAll")
    return actor


LOG = "/Game/LastSeed/Meshes/SM_LS_Log"  # Runs along its X from 0 to about 800 cm, 110 cm thick.
WALL_STONES = ["/Game/Wildwood/Model/Rocks/SM_Boulder_04", "/Game/Wildwood/Model/Rocks/SM_Boulder_05", "/Game/Wildwood/Model/Rocks/SM_Boulder_06",
               "/Game/StyleHex_Studio/Free_Packs/FREE_Stylized_Rocks_and_Stones/Meshes/SM_Stone_Large_1"]
STONE_COURSES = 5


def log_between(a, b, thickness, folder, label, solid=True):
    """A log from point a to point b, as thick as asked, solid as its own shape unless told otherwise."""
    dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    actor = mesh_actor(LOG, a[0], a[1], a[2], folder, (length / 806.0, thickness / 110.0, thickness / 110.0),
                       math.degrees(math.atan2(dy, dx)), material("M_LS_Bark"), label, math.degrees(math.atan2(dz, math.hypot(dx, dy))))
    return collide(actor) if solid else actor


def palisade_gate(gate, x, y, z, yaw, width, height, *, wings_only=False):
    """Build the gate and stockade, or rebuild the static wings around an installed gate."""
    hinge = 380.0
    peak = max(1190.0, height * 1.65)
    opening = unreal.load_asset("/Game/LastSeed/Audio/SFX_LS_TrailGateOpen")
    bark = material("M_LS_Bark")
    iron = unreal.load_asset("/Game/LastSeed/Meshes/Lever/M_LS_LeverIron")
    assert opening and bark and iron, "Missing Trail 2 gate assets"
    if not wings_only:
        gate.set_editor_properties({"hinge_offset": hinge, "swing_angle": 92.0, "default_open_duration": 3.6,
                                    "open_curve": None, "opening_sound": opening})
    folder = "Puzzles/Trail 2 Gate"
    cube = "/Engine/BasicShapes/Cube"
    cone = "/Engine/BasicShapes/Cone"
    gate_rng = random.Random(982)
    angle = math.radians(yaw)
    world = require_map()
    ignored = [
        actor for actor in actors.get_all_level_actors()
        if actor.get_actor_label() == "InvisibleWall" or str(actor.get_folder_path()) == "World/" + folder
    ]

    def at(cross, forward, up):
        return (x - math.sin(angle) * cross + math.cos(angle) * forward,
                y + math.cos(angle) * cross + math.sin(angle) * forward, z + up)

    def ground(cross, forward=0.0):
        hit = unreal.SystemLibrary.line_trace_single(
            world, unreal.Vector(*at(cross, forward, 1900.0)), unreal.Vector(*at(cross, forward, -1900.0)),
            unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, ignored, unreal.DrawDebugTrace.NONE, True)
        return hit.to_tuple()[4].z - z if hit else 0.0

    def stake(cross, forward, base, top, thickness, label, solid=False):
        timber = log_between(at(cross, forward, base), at(cross, forward, top), thickness, folder, label, solid)
        tip = mesh_actor(cone, *at(cross, forward, top + thickness * 0.45), folder,
                         (thickness / 100.0, thickness / 100.0, thickness * 0.0095), yaw, bark, label + " Tip")
        return timber, tip

    def attach(piece, leaf):
        piece.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE)
        assert piece.attach_to_component(leaf, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD,
                                         unreal.AttachmentRule.KEEP_WORLD, False)

    inner, outer = hinge + 100.0, width / 2.0 + 1160.0
    cells = max(1, math.ceil((outer - inner) / 560.0))

    def wing_depth(cross):
        return 180.0 * ((abs(cross) - inner) / (outer - inner)) ** 2

    def wing_at(cross, forward, up):
        return at(cross, wing_depth(cross) + forward, up)

    # Take all foundation samples before placing geometry.
    posts = {side: [side * (inner + (outer - inner) * k / cells) for k in range(cells + 1)] for side in (-1, 1)}
    floor = {side: [ground(cross, wing_depth(cross) - 90.0) for cross in points] for side, points in posts.items()}
    def build_doors_and_buttress(side, ground_level):
        leaf = gate.get_editor_property("door" if side < 0 else "right_door")
        leaf.set_static_mesh(unreal.load_asset(cube))
        leaf.set_relative_location(unreal.Vector(20.0, side * hinge / 2.0, peak * 0.44), False, False)
        leaf.set_relative_scale3d(unreal.Vector(0.96, hinge / 100.0, peak * 0.0095))
        ls_world_common.hide_component(leaf)
        leaf.set_collision_profile_name("BlockAll")
        leaf.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
        leaf.set_collision_response_to_channel(unreal.CollisionChannel.ECC_CAMERA, unreal.CollisionResponseType.ECR_IGNORE)

        for index in range(6):
            t = (index + 0.5) / 6.0
            top = peak - 245.0 * t + gate_rng.uniform(-19.0, 19.0)
            for piece in stake(side * hinge * t, 20.0, -32.0, top, 75.0, "Gate Door Timber"):
                attach(piece, leaf)
        for up in (195.0, 670.0, 885.0):
            strap = fit_box(cube, *at(side * hinge / 2.0, -28.0, up + 21.0), yaw, 24.0, hinge - 17.0, 42.0,
                            folder, "Gate Iron Strap", iron)
            attach(strap, leaf)
            for cross in (46.0, 190.0, 335.0):
                boss = mesh_actor("/Engine/BasicShapes/Sphere", *at(side * cross, -43.0, up), folder,
                                  (0.15, 0.22, 0.22), yaw, iron, "Gate Iron Rivet")
                attach(boss, leaf)
        brace = log_between(at(side * 321.0, -23.0, 225.0), at(side * 42.0, -23.0, 647.0),
                            72.0, folder, "Gate Diagonal Brace", False)
        attach(brace, leaf)

        foot = min(ground_level, 0.0) - 35.0
        dimensions = ((325.0, 285.0, 330.0), (284.0, 240.0, 315.0), (258.0, 220.0, 310.0), (230.0, 210.0, 300.0))
        for row, (breadth, depth, rise) in enumerate(dimensions):
            collide(fit_box(WALL_STONES[row], *at(side * (inner + 24.0), -22.0 + row * 7.0, foot + rise),
                            yaw + side * (6.0 - 3.0 * row), depth, breadth, rise + 40.0, folder, "Gate Stone Buttress"))
            foot += rise - 24.0
        stake(side * inner, -94.0, min(ground_level, 0.0) - 35.0, peak + 125.0, 145.0, "Gate Crown Post", True)
        stake(side * (hinge + 43.0), 20.0, -55.0, peak - 120.0, 108.0, "Gate Hinge Post", True)

    for side in (-1, 1):
        points, levels = posts[side], floor[side]
        if not wings_only:
            build_doors_and_buttress(side, ground(points[0]))

        crests = [peak - 88.0 - 130.0 * k / cells + 0.68 * min(low, 0.0)
                  for k, low in enumerate(levels)]
        for cross, low, crest in zip(points[1:], levels[1:], crests[1:]):
            stake(cross, wing_depth(cross) - 102.0, low - 65.0, crest + 47.0, 108.0, "Gate Wing Post", True)
            for up in (crest - 35.0, low + 180.0):
                fit_box(cube, *wing_at(cross, -101.0, up + 18.0), yaw, 122.0, 122.0, 36.0,
                        folder, "Gate Wing Iron Collar", iron)

        for k in range(cells):
            c0, c1 = points[k:k + 2]
            low0, low1 = levels[k:k + 2]
            crest0, crest1 = crests[k:k + 2]
            cell = abs(c1 - c0)
            for row in range(STONE_COURSES):
                depth = 236.0 - 17.0 * row
                split = gate_rng.uniform(0.43, 0.57)
                for start, end in ((0.0, split), (split, 1.0)):
                    t = (start + end) * 0.5
                    cross = c0 + (c1 - c0) * t
                    bottom = low0 + (low1 - low0) * t - 135.0
                    crest = crest0 + (crest1 - crest0) * t
                    rise = (crest - bottom) / STONE_COURSES
                    top = bottom + (row + 1) * rise + gate_rng.uniform(-17.0, 17.0)
                    collide(fit_box(gate_rng.choice(WALL_STONES), *wing_at(cross, 14.0, top),
                                    yaw + gate_rng.uniform(-6.0, 6.0), depth, cell * (end - start) + 24.0,
                                    rise + 62.0, folder, "Gate Wing Stone"))

            for fraction, thickness in ((0.08, 62.0), (0.50, 47.0), (0.98, 69.0)):
                up0 = low0 + (crest0 - low0) * fraction
                up1 = low1 + (crest1 - low1) * fraction
                log_between(wing_at(c0, -107.0, up0), wing_at(c1, -107.0, up1), thickness, folder, "Gate Wing Beam")
            a, b = (0.13, 0.92) if k % 2 == 0 else (0.92, 0.13)
            up0 = low0 + (crest0 - low0) * a
            up1 = low1 + (crest1 - low1) * b
            log_between(wing_at(c0, -125.0, up0), wing_at(c1, -125.0, up1), 66.0, folder, "Gate Wing Brace")

            for t in (0.32, 0.68):
                cross = c0 + (c1 - c0) * t
                crest = crest0 + (crest1 - crest0) * t
                stake(cross, wing_depth(cross) - 29.0, crest - 165.0, crest + gate_rng.uniform(15.0, 47.0),
                      65.0, "Gate Wing Spike")


LEVER_SOURCE = os.path.join(ls_world_common.SOURCE_FOLDER, "Lever")
LEVER_FOLDER = "/Game/LastSeed/Meshes/Lever"
LEVER_PARTS = [("base", "SM_LS_LeverBase", "Wood"), ("iron", "SM_LS_LeverIron", "Iron"), ("cap", "SM_LS_LeverCap", "Wood"),
               ("rod", "SM_LS_LeverRod", "Iron"), ("grip", "SM_LS_LeverGrip", "Leather")]


def import_art(source, folder, prefix, solid_parts, finishes, glowing=()):
    """Imports a set of generated meshes (OBJ) and painted textures (PNG) from source into folder, makes solid_parts
    collide as their exact shape, and builds a material M_LS_<prefix><finish> for each finish from its T_LS_<prefix>
    <finish>_BC, _N and _ORM textures. A glowing finish also glows where its colour texture's alpha is set. Runs once:
    delete the folder to import fresh ones."""
    if unreal.EditorAssetLibrary.does_asset_exist("{}/M_LS_{}{}".format(folder, prefix, finishes[-1])):
        return
    tasks = []
    for name in sorted(os.listdir(source)):
        if name.endswith((".obj", ".png")):
            task = unreal.AssetImportTask()
            task.filename = os.path.join(source, name)
            task.destination_path = folder
            task.destination_name = os.path.splitext(name)[0]
            task.automated = True
            task.replace_existing = True
            task.save = True
            tasks.append(task)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    meshes = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    for part in solid_parts:
        loaded = unreal.load_asset(folder + "/" + part)
        meshes.remove_collisions(loaded)
        loaded.get_editor_property("body_setup").set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        unreal.EditorAssetLibrary.save_loaded_asset(loaded, False)
    lib = unreal.MaterialEditingLibrary
    for finish in finishes:
        textures = {}
        for kind, compression in (("BC", None), ("N", unreal.TextureCompressionSettings.TC_NORMALMAP), ("ORM", unreal.TextureCompressionSettings.TC_MASKS)):
            texture = unreal.load_asset("{}/T_LS_{}{}_{}".format(folder, prefix, finish, kind))
            if compression is not None:
                texture.set_editor_property("srgb", False)
                texture.set_editor_property("compression_settings", compression)
                unreal.EditorAssetLibrary.save_loaded_asset(texture, False)
            textures[kind] = texture
        built = unreal.AssetToolsHelpers.get_asset_tools().create_asset("M_LS_{}{}".format(prefix, finish), folder, unreal.Material,
                                                                         unreal.MaterialFactoryNew())

        def sample(kind, sampler, y):
            node = lib.create_material_expression(built, unreal.MaterialExpressionTextureSample, -500, y)
            node.set_editor_property("texture", textures[kind])
            node.set_editor_property("sampler_type", sampler)
            return node
        colour = sample("BC", unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, -300)
        normal = sample("N", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL, 0)
        orm = sample("ORM", unreal.MaterialSamplerType.SAMPLERTYPE_MASKS, 300)
        lib.connect_material_property(colour, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
        lib.connect_material_property(normal, "RGB", unreal.MaterialProperty.MP_NORMAL)
        lib.connect_material_property(orm, "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
        lib.connect_material_property(orm, "G", unreal.MaterialProperty.MP_ROUGHNESS)
        lib.connect_material_property(orm, "B", unreal.MaterialProperty.MP_METALLIC)
        if finish in glowing:
            masked = lib.create_material_expression(built, unreal.MaterialExpressionMultiply, -250, -500)
            lib.connect_material_expressions(colour, "RGB", masked, "A")
            lib.connect_material_expressions(colour, "A", masked, "B")
            bright = lib.create_material_expression(built, unreal.MaterialExpressionMultiply, -100, -500)
            bright.set_editor_property("const_b", 1.4)
            lib.connect_material_expressions(masked, "", bright, "A")
            lib.connect_material_property(bright, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        lib.recompile_material(built)
        unreal.EditorAssetLibrary.save_loaded_asset(built)


def lever_assets():
    """The lever's meshes and its wood, iron and leather materials (written by ls_generate_lever.py)."""
    import_art(LEVER_SOURCE, LEVER_FOLDER, "Lever", ("SM_LS_LeverBase", "SM_LS_LeverIron"), ("Wood", "Iron", "Leather"))


MUSHROOM_SOURCE = os.path.join(ls_world_common.SOURCE_FOLDER, "Mushroom")
MUSHROOM_FOLDER = "/Game/LastSeed/Meshes/Mushroom"
SOUND_SOURCE = os.path.join(unreal.Paths.project_content_dir(), "LastSeed", "SourceSounds")
AUDIO = "/Game/LastSeed/Audio"
MUSIC_LOOP = "MUS_LS_DragonsLullaby_Loop"
MUSIC_FINALE = "MUS_LS_DragonsLullaby_Finale"
LOOPING = [MUSIC_LOOP, "SFX_LS_StormRumble"]
WITHER_WALL = LS + "M_LS_WitherWall"


def fun_assets():
    """The bouncy mushroom's art, gameplay music and sound effects, and the
    Withering's wall material. Each is made once."""
    import_art(MUSHROOM_SOURCE, MUSHROOM_FOLDER, "Mushroom", ("SM_LS_MushroomStem", "SM_LS_MushroomCap"), ("Cap", "Stem"), glowing=("Cap",))
    tasks = []
    for name in [MUSIC_LOOP, MUSIC_FINALE, "SFX_LS_Boing", "SFX_LS_NoteChime", "SFX_LS_StormRumble"]:
        if not unreal.EditorAssetLibrary.does_asset_exist("{}/{}".format(AUDIO, name)):
            task = unreal.AssetImportTask()
            task.filename = os.path.join(SOUND_SOURCE, name + ".wav")
            task.destination_path = AUDIO
            task.destination_name = name
            task.automated = True
            task.replace_existing = True
            task.save = True
            tasks.append(task)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    for name in LOOPING:
        sound = unreal.load_asset("{}/{}".format(AUDIO, name))
        if not sound.get_editor_property("looping"):
            sound.set_editor_property("looping", True)
            unreal.EditorAssetLibrary.save_loaded_asset(sound, False)
    if not unreal.EditorAssetLibrary.does_asset_exist(WITHER_WALL):
        # A dark, see-through wall that glows violet at its edges, where you look across it.
        lib = unreal.MaterialEditingLibrary
        folder, name = WITHER_WALL.rsplit("/", 1)
        built = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
        built.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
        built.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
        built.set_editor_property("two_sided", True)
        dark = lib.create_material_expression(built, unreal.MaterialExpressionConstant3Vector, -700, -100)
        dark.set_editor_property("constant", unreal.LinearColor(0.02, 0.0, 0.035, 1.0))
        glow = lib.create_material_expression(built, unreal.MaterialExpressionConstant3Vector, -700, 50)
        glow.set_editor_property("constant", unreal.LinearColor(0.45, 0.06, 0.7, 1.0))
        rim = lib.create_material_expression(built, unreal.MaterialExpressionFresnel, -700, 200)
        rim.set_editor_property("exponent", 2.5)
        blend = lib.create_material_expression(built, unreal.MaterialExpressionLinearInterpolate, -400, 0)
        lib.connect_material_expressions(dark, "", blend, "A")
        lib.connect_material_expressions(glow, "", blend, "B")
        lib.connect_material_expressions(rim, "", blend, "Alpha")
        lib.connect_material_property(blend, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        opacity = lib.create_material_expression(built, unreal.MaterialExpressionConstant, -400, 250)
        opacity.set_editor_property("r", 0.82)
        lib.connect_material_property(opacity, "", unreal.MaterialProperty.MP_OPACITY)
        lib.recompile_material(built)
        unreal.EditorAssetLibrary.save_loaded_asset(built)
    sound = lambda name: unreal.load_asset("{}/{}".format(AUDIO, name))
    return {"stems": [sound(MUSIC_LOOP)], "finale": sound(MUSIC_FINALE), "boing": sound("SFX_LS_Boing"),
            "chime": sound("SFX_LS_NoteChime"), "rumble": sound("SFX_LS_StormRumble")}


INTRO_SOURCE = os.path.join(unreal.Paths.project_content_dir(), "LastSeed", "SourceIntro", "Anime")
INTRO_FOLDER = "/Game/LastSeed/Intro/Anime"


def import_intro_frames(numbers):
    tasks = []
    for number in numbers:
        task = unreal.AssetImportTask()
        task.filename = os.path.join(INTRO_SOURCE, "Intro_{:02d}.png".format(number))
        task.destination_path = INTRO_FOLDER
        task.destination_name = "T_LS_Intro_{:02d}".format(number)
        task.automated = True
        task.replace_existing = True
        task.save = True
        tasks.append(task)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    frames = {}
    for number in numbers:
        texture = unreal.load_asset("{}/T_LS_Intro_{:02d}".format(INTRO_FOLDER, number))
        if not isinstance(texture, unreal.Texture2D):
            raise RuntimeError("Missing intro texture for shot {:02d}".format(number))
        # Full screen and sharp: no mipmaps, never streamed out. Default (block) compression keeps each frame near
        # 2 MB of video memory; uncompressed they would take 8 MB each.
        texture.set_editor_properties({"compression_settings": unreal.TextureCompressionSettings.TC_DEFAULT,
                                       "lod_group": unreal.TextureGroup.TEXTUREGROUP_UI,
                                       "mip_gen_settings": unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS,
                                       "never_stream": True})
        unreal.EditorAssetLibrary.save_loaded_asset(texture, False)
        frames[number] = texture
    return frames


def intro_shots():
    """Imports the opening artwork and music, then builds the shot list."""
    import ls_intro_shots
    importlib.reload(ls_intro_shots)
    frames = import_intro_frames(sorted({shot[0] for shot in ls_intro_shots.SHOTS}))
    music = unreal.AssetImportTask()
    music.filename = os.path.join(SOUND_SOURCE, "MUS_LS_Intro_Recordings.wav")
    music.destination_path = AUDIO
    music.destination_name = "MUS_LS_Intro_Recordings"
    music.automated = True
    music.replace_existing = True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([music])
    soundtrack = unreal.load_asset(AUDIO + "/MUS_LS_Intro_Recordings")
    soundtrack.set_editor_property("volume", ls_intro_shots.SOUNDTRACK_VOLUME)
    unreal.EditorAssetLibrary.save_loaded_asset(soundtrack)
    shots = []
    for number, seconds, zoom0, zoom1, pan0, pan1, fade, flash, caption in ls_intro_shots.SHOTS:
        shot = unreal.LSIntroShot()
        shot.set_editor_properties({"image": frames[number], "duration": seconds, "start_zoom": zoom0, "end_zoom": zoom1,
                                    "start_pan": unreal.Vector2D(*pan0), "end_pan": unreal.Vector2D(*pan1),
                                    "fade_in": fade, "flash": flash, "caption": unreal.Text(caption)})
        motion_path = f"{INTRO_FOLDER}/Motion/MI_LS_IntroMotion_{number:02d}"
        if unreal.EditorAssetLibrary.does_asset_exist(motion_path):
            shot.set_editor_property("motion_material", unreal.load_asset(motion_path))
        shots.append(shot)
    return shots, soundtrack


def intro():
    """Gives the open level's opening story its painted cutscene, in place of its story cards."""
    shots, music = intro_shots()
    for actor in actors.get_all_level_actors():
        if actor.get_class().get_name() == "StoryTrigger" and actor.get_editor_property("play_on_start"):
            actor.set_editor_properties({"intro_shots": shots, "intro_music": music})
            return {"shots": len(shots), "story": actor.get_actor_label()}
    return "no opening story in this level"


def remove_ghost():
    """Remove legacy replay actors without touching the player's saved progress."""
    ghosts = [actor for actor in actors.get_all_level_actors() if isinstance(actor, unreal.GhostRacer)]
    for actor in ghosts:
        assert actors.destroy_actor(actor), 'Could not remove replay ghost'
    return len(ghosts)


def set_music(sounds):
    """Gives Wildwood its exploration loop and finale."""
    for actor in actors.get_all_level_actors():
        if actor.get_class().get_name() == "MusicManager":
            music = actor.get_component_by_class(unreal.AdaptiveMusicComponent)
            music.set_editor_properties({"stems": sounds["stems"], "finale_track": sounds["finale"]})
            return True
    return False


def place(entry, plates):
    kind, x, y, z, yaw = entry["kind"], entry["x"], entry["y"], entry["z"], entry["yaw"]
    # Older cached plans still include the purple chase replaced by the riverbank witch curse.
    if entry.get('id') == 'storm1' or entry.get('storm') == 'storm1' or str(entry.get('message', '')).startswith('The Withering is coming!'):
        return
    if kind == "player_start":
        spawn(unreal.PlayerStart, x, y, z, "PlayerStart", "Flow", yaw)
    elif kind == "witch_ambush":
        from ls_witch_ambush import place as place_ambush
        place_ambush(x, y, z, yaw, entry['half'], entry['target'])
    elif kind == "story":
        story = spawn(unreal.load_class(None, "/Script/Assignment1.StoryTrigger"), x, y, z, "OpeningStory", "Flow")
        story.set_editor_properties({"cards": [unreal.Text(card) for card in entry["cards"]], "play_on_start": entry["on_start"]})
        if entry["on_start"]:
            # The painted cutscene plays instead of the cards, which stay as a fallback.
            shots, music = intro_shots()
            story.set_editor_properties({"intro_shots": shots, "intro_music": music})
            voice_path = AUDIO + "/VO_LS_HeartTree"
            if unreal.EditorAssetLibrary.does_asset_exist(voice_path):
                story.set_editor_property("intro_voice_over", unreal.load_asset(voice_path))
    elif kind == "tutorial":
        actor = spawn(unreal.load_class(None, "/Script/Assignment1.TutorialTrigger"), x, y, z, "Tutorial", "Flow", yaw)
        actor.set_editor_properties({"message": unreal.Text(entry["message"]), "display_duration": 6.0})
        actor.set_actor_scale3d(unreal.Vector(*[h / 200.0 for h in entry["half"]]))
    elif kind == "note":
        actor = spawn(gameplay_class("BP_LifeNote", "LifeNote"), x, y, z, "LifeNote", "Pickups")
        component = keep_coloured(actor)
        component.set_static_mesh(unreal.load_asset("/Game/LastSeed/Meshes/SM_LS_MusicNote"))
        component.set_relative_scale3d(unreal.Vector(1.0, 1.0, 1.0))
        component.set_material(0, material("M_LS_Note"))
        actor.set_editor_property("collect_sound", fun_assets()["chime"])
    elif kind == "petal":
        actor = spawn(gameplay_class("BP_GoldenPetal", "GoldenPetal"), x, y, z, "GoldenPetal", "Pickups")
        fit_mesh(keep_coloured(actor), "/Game/Polytope_Studio/Nature_Free/Meshes/Flowers/SM_Poppy_02", 170.0, -40.0)
    elif kind == "shrine":
        actor = spawn(gameplay_class("BP_CheckpointShrine", "CheckpointShrine"), x, y, z, "Shrine", "Flow", yaw)
        keep_coloured(actor)
        import ls_lantern_post  # The post with its hanging lantern, at the trail's edge.
        ls_lantern_post.configure(actor, load_plan()["walls"])
    elif kind == "flower":
        actor = spawn(gameplay_class("BP_FormFlower_Stone", "FormFlower"), x, y, z, "FormFlower", "Pickups")
        form = getattr(unreal.SeedForm, entry["form"])
        actor.set_editor_properties({"form_to_unlock": form, "prompt_message": unreal.Text(entry["message"])})
        if entry["form"] == "STONE":
            from ls_stone_unlock import configure
            configure(actor)
        else:
            fit_mesh(keep_coloured(actor), mesh("SM_Flowers_White_03"), 160.0, -80.0)
    elif kind == "block":
        name = entry.get("name", "Block")  # Extras are named apart, so rebuilding the hand-placed rocks never touches them.
        # Rocks side by side across the width, each kept close to its own proportions, solid as their own shape.
        count = max(1, int(round(entry["width"] / max(entry["length"], 300.0))))
        h = math.radians(yaw)
        for k in range(count):
            d = (k - (count - 1) / 2.0) * entry["width"] / count
            collide(fit_rock(rng.choice(FLAT_ROCKS), x - d * math.sin(h), y + d * math.cos(h), z, yaw + rng.uniform(-10, 10),
                             entry["length"] * 1.1, entry["width"] / count * 1.15, entry["depth"] + 40.0, "Parkour", name + "Rock"))
    elif kind == "pillar":
        r = entry["radius"]
        rock_stack(x, y, z, r, entry["bottom"], "PillarRock", entry.get('collapses', False))
    elif kind == "tower":
        r = entry["radius"]
        rock_stack(x, y, z, r, entry["bottom"], "TowerRock")
    elif kind == "fallen_log":
        # A dead tree lying across the trail, solid as its own shape, so only a jump gets over.
        across = yaw + 90.0 + entry.get("lean", 0.0)
        name = entry.get("name")
        collide(fit_box("/Game/LastSeed/Meshes/SM_LS_Log", x, y, z + entry["height"], across, entry["length"], 130.0, 130.0,
                        "Parkour", name + "Log" if name else "FallenLog", material("M_LS_Bark")))
    elif kind == "log_bridge":
        h = math.radians(yaw)
        actor = collide(fit_box("/Game/LastSeed/Meshes/SM_LS_Log", x, y, z, yaw, entry["length"], entry["width"] + 60.0, entry["width"] + 40.0,
                               "Parkour", "BridgeLog", material("M_LS_Bark")))
        if entry.get('collapses', False): add_collapsing_stone(actor, [], wood=True)
    elif kind == "tilting_log":
        actor = spawn(unreal.load_class(None, "/Script/Assignment1.TiltingLog"), x, y, z, "TiltingLog", "Parkour", yaw)
        half = entry["half_length"]
        actor.set_editor_properties({"half_length": half, "half_width": entry["half_width"], "max_tilt_degrees": entry["max_tilt"],
                                     "counterweight_kg_cm": entry["counterweight"], "tilt_response": 0.025})
        log_mesh = actor.get_editor_property("log_mesh")
        log_mesh.set_static_mesh(unreal.load_asset("/Game/LastSeed/Meshes/SM_LS_Log"))
        log_mesh.set_material(0, material("M_LS_Bark"))
        log_mesh.set_relative_scale3d(unreal.Vector(half * 2.0 / 800.0, entry["half_width"] / 45.0, 1.5))
        log_mesh.set_relative_location(unreal.Vector(-half, 0.0, -68.0), False, False)
        if entry.get('collapses', False): add_collapsing_stone(actor, [], wood=True)
        stump_top = z - 140.0
        mesh_actor("/Game/LastSeed/Meshes/SM_LS_LogPivot", x, y, stump_top, "Parkour", (1.0, 1.0, (stump_top - entry["floor"]) / 500.0),
                   yaw, material("M_LS_Bark"), "LogStump")
    elif kind == "crumbling":
        actor = spawn(unreal.load_class(None, "/Script/Assignment1.CrumblingPlatform"), x, y, z, "CrumblingStone", "Parkour", yaw)
        drop = platform_rock(actor.get_editor_property("mesh"))
        actor.set_actor_location(unreal.Vector(x, y, z - drop), False, False)
    elif kind == "moving":
        actor = spawn(unreal.load_class(None, "/Script/Assignment1.MovingPlatform"), x, y, z, "MovingPlatform", "Parkour", yaw)
        actor.set_editor_properties({"speed": entry["speed"], "wait_time": entry["wait"]})
        drop = platform_rock(actor.get_editor_property("mesh"))
        actor.set_actor_location(unreal.Vector(x, y, z - drop), False, False)
        path = actor.get_component_by_class(unreal.SplineComponent)
        end = entry["end"]
        path.set_location_at_spline_point(1, unreal.Vector(end[0], end[1], end[2] - drop), unreal.SplineCoordinateSpace.WORLD)
    elif kind == "cracked_wall":
        from ls_wildwood_wall import configure
        height, width = entry["height"], entry["width"]
        actor = spawn(unreal.load_class(None, "/Script/Assignment1.CrackedWall"), x, y, z + height / 2.0, "CrackedWall", "Puzzles", yaw)
        # Its mesh is its root, so the actor's scale is the wall's whole size (a 1 m cube scaled to fit).
        actor.set_actor_scale3d(unreal.Vector(0.5, width / 100.0, height / 100.0))
        configure(actor)
    elif kind == "lever":
        # Faces down the trail (local -X toward the player), so a block pushed along the trail meets the plinth's front end.
        lever_assets()
        actor = spawn(unreal.load_class(None, "/Script/Assignment1.Lever"), x, y, z, "Lever", "Puzzles", yaw)
        for prop, part, finish in LEVER_PARTS:
            component = actor.get_editor_property(prop)
            component.set_static_mesh(unreal.load_asset(LEVER_FOLDER + "/" + part))
            component.set_material(0, unreal.load_asset(LEVER_FOLDER + "/M_LS_Lever" + finish))
            # In colour while the forest is grey, like the pickups, so the player spots it.
            component.set_render_custom_depth(True)
            component.set_custom_depth_stencil_value(ls_world_common.FULL_COLOUR_STENCIL)
        # Leaning back, as it starts in play.
        actor.get_editor_property("arm_pivot").set_relative_rotation(unreal.Rotator(0.0, 40.0, 0.0), False, False)
        plates[entry["id"]] = actor
    elif kind == "push_block":
        actor = spawn(gameplay_class("BP_IceBlock", "PushableBlock"), x, y, z, "PushableBlock", "Puzzles", yaw)
        actor.set_editor_property("mass_kg", entry["mass"])
        actor.get_component_by_class(unreal.StaticMeshComponent).set_material(0, material("M_LS_Planks"))
    elif kind == "gate":
        actor = spawn(gameplay_class("BP_Gate", "Gate"), x, y, z, "Gate", "Puzzles", yaw)
        actor.set_editor_property("required_plates", [plates[name] for name in entry.get("plates", [])])
        actor.set_editor_property("required_levers", [plates[name] for name in entry.get("levers", [])])
        palisade_gate(actor, x, y, z, yaw, entry["width"], entry["height"])
    elif kind == "blob":
        actor = spawn(gameplay_class("BP_WitherBlob", "WitherBlob"), x, y, z, "WitherBlob", "Enemies", yaw)
        actor.set_editor_property("patrol_points", [unreal.Vector(dx, dy, 0.0) for dx, dy in entry["patrol"]])
        component = keep_coloured(actor)
        component.set_static_mesh(unreal.load_asset("/Game/LastSeed/Meshes/SM_LS_Blob"))
        component.set_material(0, material("M_LS_Blob"))
    elif kind == "wind":
        actor = spawn(gameplay_class("BP_WindVolume", "WindVolume"), x, y, z, "Updraft", "Parkour", yaw)
        actor.set_actor_scale3d(unreal.Vector(*[h / 200.0 for h in entry["half"]]))
        actor.set_editor_properties({"wind_direction": unreal.Vector(0.0, 0.0, 1.0), "strength": entry["strength"]})
        # Drifting leaves show where the updraft is, since wind itself can't be seen.
        for k in range(3):
            niagara("/Game/Wildwood/VFX/Niagara/NS_ParticleDust", x, y, z - entry["half"][2] + k * entry["half"][2] * 0.7, "Parkour", 1.5)
        point_light(x, y, z - entry["half"][2] + 200.0, unreal.LinearColor(0.6, 1.0, 0.8, 1.0), 40.0, 1500.0, "Parkour")
    elif kind == "goal":
        actor = spawn(unreal.load_class(None, "/Script/Assignment1.LevelGoal"), x, y, z, "LevelGoal", "Flow", yaw)
        actor.set_actor_scale3d(unreal.Vector(*[h / 200.0 for h in entry["half"]]))
        actor.set_editor_properties({"ending_cards": [unreal.Text(card) for card in entry["cards"]], "credits_cards": [],
                                     "par_time_seconds": entry["par"], "required_petals": entry["petals"]})
        if unreal.EditorAssetLibrary.does_asset_exist("/Game/L_Level2"):
            actor.set_editor_property("next_level", unreal.load_asset("/Game/L_Level2"))
        ground = z - entry["half"][2]
        ring = mesh_actor("/Game/LastSeed/Meshes/SM_LS_GateRing", x, y, ground + 720.0, "Flow", (2.1, 2.1, 2.1), yaw, material("M_LS_GoalGlow"), "GoalRing")
        ring.static_mesh_component.set_render_custom_depth(True)
        ring.static_mesh_component.set_custom_depth_stencil_value(ls_world_common.FULL_COLOUR_STENCIL)
        point_light(x, y, ground + 700.0, unreal.LinearColor(1.0, 0.62, 0.2, 1.0), 110.0, 3200.0, "Flow")
    elif kind == "heart_tree":
        # The Heart Tree: a giant dead trunk that becomes the biggest living tree in the forest.
        restorable(x, y, z, yaw, mesh("SM_Tree_09"), 1.5, "/Game/LastSeed/Meshes/SM_LS_GnarledTree", 0.55, threshold=0.75, radius=5000.0,
                   grow=6.0, bounce=0.4, folder="Flow", label="HeartTree", shake=2.5, sound=tree_sound())
    elif kind == "mushroom":
        sounds = fun_assets()
        actor = spawn(unreal.load_class(None, "/Script/Assignment1.BounceMushroom"), x, y, z, "BounceMushroom", "Parkour", rng.uniform(0, 360))
        actor.set_actor_scale3d(unreal.Vector(entry["scale"], entry["scale"], entry["scale"]))
        actor.set_editor_properties({"launch_speed": entry["launch"], "bounce_sound": sounds["boing"]})
        for prop, part in (("stem", "Stem"), ("cap", "Cap")):
            component = actor.get_editor_property(prop)
            component.set_static_mesh(unreal.load_asset("{}/SM_LS_Mushroom{}".format(MUSHROOM_FOLDER, part)))
            component.set_material(0, unreal.load_asset("{}/M_LS_Mushroom{}".format(MUSHROOM_FOLDER, part)))
            component.set_render_custom_depth(False)
        actor.get_editor_property("cap").set_relative_location(unreal.Vector(0.0, 0.0, 145.0), False, False)
    elif kind == "storm":
        sounds = fun_assets()
        actor = spawn(unreal.load_class(None, "/Script/Assignment1.WitheringStorm"), x, y, z, "WitheringStorm", "Flow", yaw)
        ex, ey, ez = entry["half"]
        actor.root_component.set_box_extent(unreal.Vector(ex, ey, ez))
        wall = actor.get_editor_property("mesh")
        wall.set_relative_scale3d(unreal.Vector(ex / 50.0, ey / 50.0, ez / 50.0))
        wall.set_material(0, unreal.load_asset(WITHER_WALL))
        actor.get_editor_property("rumble_audio").set_sound(sounds["rumble"])
        actor.set_editor_properties({"rise_speed": entry["speed"], "note_pushback": entry["pushback"], "respawn_clearance": 600.0,
                                     "close_distance": 2200.0, "max_rise_distance": 1000000.0,
                                     "chase_points": [unreal.Vector(*point) for point in entry["points"]]})
        plates[entry["id"]] = actor
    elif kind == "storm_trigger":
        actor = spawn(unreal.load_class(None, "/Script/Assignment1.StormTrigger"), x, y, z, "StormTrigger", "Flow", yaw)
        actor.set_actor_scale3d(unreal.Vector(*[h / 200.0 for h in entry["half"]]))
        actor.set_editor_property("storm", plates[entry["storm"]])
    else:
        raise RuntimeError("Last Seed Wildwood: unknown plan entry " + kind)


def gameplay(plan):
    plates = {}
    # Gates and storm triggers last, so the plates, levers and storm they point at exist.
    order = sorted(plan["actors"], key=lambda entry: entry["kind"] in ("gate", "storm_trigger"))
    for entry in order:
        place(entry, plates)
    for x0, y0, x1, y1, bottom, top in plan["walls"]:
        invisible_wall(x0, y0, x1, y1, bottom, top, "Walls")
    for kill in plan["kills"]:
        kill_volume(kill["x"], kill["y"], kill["z"], *kill["half"], yaw=kill["yaw"])
    # Under the whole map, in case anything ever slips through the ground.
    kill_volume(0.0, 5000.0, -200.0, 60000.0, 60000.0, 200.0)

    edge = ls_world_common.Scatter("TrailEdge", 0, 0)
    for name, x, y, ground, yaw, scale in plan["scatter"]:
        edge.add(mesh(name), x, y, ground, scale, rng, sink=12.0)
    edge.build()
    for name, x, y, ground, yaw, scale in plan["regrowth"]:
        loaded = unreal.load_asset(mesh(name))
        restorable(x, y, ground - base_height_offset(loaded, scale) - 4.0, yaw, mesh(name), scale, threshold=2.0, radius=900.0)


# --- Extras, and the rocks and logs placed by hand ---

HAND_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ls_hand_placed.json")
HAND_REGION = (-26500.0, -21400.0, 3400.0, 18500.0)  # x0, x1, y0, y1: trail piece 00 and the start of 01, where rocks and logs were placed by hand.
HAND_VISUALS = ("BlockRock", "FallenLog")  # Label prefixes. The planner's extras are named Trail..., so they never match.
EXTRA_TAG = "LS_Extra"


def in_hand_region(location):
    return HAND_REGION[0] < location.x < HAND_REGION[1] and HAND_REGION[2] < location.y < HAND_REGION[3]


def hand_actors():
    return [a for a in actors.get_all_level_actors() if isinstance(a, unreal.StaticMeshActor) and in_hand_region(a.get_actor_location())]


def protect_hand_placed():
    """Makes every hand-placed rock and log solid as its own shape (copies made in the editor came with collision off),
    then records them all in HAND_FILE, so a rebuild (which starts from a fresh map) can put them back."""
    visuals = []
    for a in hand_actors():
        label, location, rotation, scale = a.get_actor_label(), a.get_actor_location(), a.get_actor_rotation(), a.get_actor_scale3d()
        if label.startswith(HAND_VISUALS):
            collide(a)
            component = a.static_mesh_component
            visuals.append({"label": label, "mesh": component.static_mesh.get_path_name(), "loc": [location.x, location.y, location.z],
                            "rot": [rotation.pitch, rotation.yaw, rotation.roll], "scale": [scale.x, scale.y, scale.z],
                            "materials": [m.get_path_name() if m else "" for m in component.get_materials()]})
    json.dump({"visuals": visuals}, open(HAND_FILE, "w"), indent=1)
    return {"rocks and logs recorded": len(visuals)}


def hand_placed():
    """Puts back the hand-placed rocks and logs from HAND_FILE on a freshly built level: the rocks and logs the build made in
    that area are replaced by the recorded ones, each solid as its own shape. The new ones are made first, so a failure
    leaves the old ones in place."""
    if not os.path.exists(HAND_FILE):
        return "no hand-placed file"
    data = json.load(open(HAND_FILE))
    old = [a for a in hand_actors() if a.get_actor_label().startswith(HAND_VISUALS)]
    for e in data["visuals"]:
        x, y, z = e["loc"]
        pitch, yaw, roll = e["rot"]
        actor = mesh_actor(e["mesh"], x, y, z, "Parkour", tuple(e["scale"]), yaw, None, e["label"], pitch)
        actor.set_actor_rotation(unreal.Rotator(roll, pitch, yaw), False)
        collide(actor)
        for index, path in enumerate(e["materials"]):
            if path:
                actor.static_mesh_component.set_material(index, unreal.load_asset(path))
    for a in old:
        actors.destroy_actor(a)
    return "{} rocks and logs".format(len(data["visuals"]))


FUN_TAG = "LS_Fun"


def fun():
    """Adds the planner's fun extras to a level that is already open: bouncy mushrooms, the Withering's chase, the
    music, a chime on every Life Note, and the two notes raised over mushrooms. Leaves everything else alone and
    refuses to run twice."""
    if tagged(FUN_TAG):
        return "already added"
    sounds = fun_assets()
    plan = load_plan()
    before = {a.get_name() for a in actors.get_all_level_actors()}
    found = {}
    entries = [e for e in plan["actors"] if e.get("extra") == "fun"]
    for entry in sorted(entries, key=lambda e: e["kind"] == "storm_trigger"):
        place(entry, found)
    for a in actors.get_all_level_actors():
        if a.get_name() not in before:
            a.tags = list(a.tags) + [FUN_TAG]
    notes = [a for a in actors.get_all_level_actors() if a.get_actor_label() == "LifeNote"]
    for note in notes:
        note.set_editor_property("collect_sound", sounds["chime"])
    raised = 0
    for entry in plan["actors"]:
        if entry.get("raised"):
            # The note already stands at this spot, only lower.
            note = min(notes, key=lambda a: (a.get_actor_location().x - entry["x"]) ** 2 + (a.get_actor_location().y - entry["y"]) ** 2)
            location = note.get_actor_location()
            note.set_actor_location(unreal.Vector(location.x, location.y, entry["z"]), False, False)
            raised += 1
    return {"placed": len(entries), "notes with chime": len(notes), "notes raised": raised, "music": set_music(sounds)}


def extras():
    """Adds the planner's extra obstacles to a level that is already open, leaving everything else (hand-placed work
    included) alone. Refuses to run twice."""
    if tagged(EXTRA_TAG):
        return "already added"
    before = {a.get_name() for a in actors.get_all_level_actors()}
    count = 0
    for entry in load_plan()["actors"]:
        if entry.get("extra"):
            place(entry, {})
            count += 1
    for a in actors.get_all_level_actors():
        if a.get_name() not in before:
            a.tags = list(a.tags) + [EXTRA_TAG]
    return count


# --- World ---

def set_opening_weather(driver):
    thunder_name = "SFX_LS_DistantThunder"
    thunder_path = AUDIO + "/" + thunder_name
    if not unreal.EditorAssetLibrary.does_asset_exist(thunder_path):
        task = unreal.AssetImportTask()
        task.set_editor_properties({"filename": os.path.join(SOUND_SOURCE, thunder_name + ".wav"),
                                    "destination_path": AUDIO, "destination_name": thunder_name,
                                    "automated": True, "save": True})
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    thunder = unreal.load_asset(thunder_path)
    if not isinstance(thunder, unreal.SoundWave):
        raise RuntimeError("Wildwood distant thunder did not import")
    driver.set_editor_properties({"weather_clouds": ls_world_common.find_actor(unreal.VolumetricCloud),
                                  "distant_thunder": thunder})
    from ls_sky_lightning import configure
    configure(driver)
    import ls_storm
    ls_storm.configure(driver)


def world_setup():
    volume = ls_world_common.find_actor(unreal.PostProcessVolume)
    volume.set_editor_property("unbound", True)
    fog = ls_world_common.find_actor(unreal.ExponentialHeightFog)
    density = fog.get_component_by_class(unreal.ExponentialHeightFogComponent).get_editor_property("fog_density")
    driver = spawn(unreal.load_class(None, "/Script/Assignment1.RestorationDriver"), 0, 0, 8000, "RestorationDriver", "Flow")
    driver.set_editor_properties({"parameter_collection": unreal.load_asset("/Game/MPC_Restoration"), "post_process_volume": volume,
                                  "height_fog": fog, "withered_saturation": 0.0, "withered_tint": unreal.LinearColor(1.05, 0.95, 0.88, 1.0),
                                  "withered_fog_density": density * 2.0, "restored_fog_density": density})
    set_opening_weather(driver)
    spawn(unreal.load_class(None, "/Script/Assignment1.MusicManager"), 0, 0, 8100, "MusicManager", "Flow")
    set_music(fun_assets())
    remove_ghost()
    # The project's game mode (BP_LSGameMode) runs the level, not any override the demo map had.
    settings = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_world_settings()
    settings.set_editor_property("default_game_mode", None)


# --- Bare trees until the world recovers ---

def leaves():
    """Multiplies the leaf material's opacity mask by how far restoration has gone. Each foliage tree has its own
    random threshold, so the forest greens a little more with every note rather than all at once. A tree that is its
    own actor (the regrowing ones) has no per-instance random, so its leaves show as soon as restoration starts."""
    lib = unreal.MaterialEditingLibrary
    master = unreal.load_asset(LEAF_MASTER)
    if unreal.EditorAssetLibrary.get_metadata_tag(master, LEAF_TAG) == "1":
        return "already done"
    original = lib.get_material_property_input_node(master, unreal.MaterialProperty.MP_OPACITY_MASK)
    output = lib.get_material_property_input_node_output_name(master, unreal.MaterialProperty.MP_OPACITY_MASK) if original else ""
    restoration = lib.create_material_expression(master, unreal.MaterialExpressionCollectionParameter, -1400, 900)
    restoration.set_editor_property("collection", unreal.load_asset("/Game/MPC_Restoration"))
    restoration.set_editor_property("parameter_name", "Restoration")
    random_value = lib.create_material_expression(master, unreal.MaterialExpressionPerInstanceRandom, -1400, 1000)
    scaled = lib.create_material_expression(master, unreal.MaterialExpressionMultiply, -1200, 900)
    scaled.set_editor_property("const_b", 1.25)
    ahead = lib.create_material_expression(master, unreal.MaterialExpressionSubtract, -1050, 950)
    sharp = lib.create_material_expression(master, unreal.MaterialExpressionMultiply, -900, 950)
    sharp.set_editor_property("const_b", 12.0)
    growth = lib.create_material_expression(master, unreal.MaterialExpressionSaturate, -750, 950)
    final = lib.create_material_expression(master, unreal.MaterialExpressionMultiply, -600, 900)
    for node in (restoration, random_value, scaled, ahead, sharp, growth, final):
        node.set_editor_property("desc", LEAF_TAG)
    lib.connect_material_expressions(restoration, "", scaled, "A")
    lib.connect_material_expressions(scaled, "", ahead, "A")
    lib.connect_material_expressions(random_value, "", ahead, "B")
    lib.connect_material_expressions(ahead, "", sharp, "A")
    lib.connect_material_expressions(sharp, "", growth, "")
    if original:
        lib.connect_material_expressions(original, output, final, "A")
    else:
        final.set_editor_property("const_a", 1.0)
    lib.connect_material_expressions(growth, "", final, "B")
    lib.connect_material_property(final, "", unreal.MaterialProperty.MP_OPACITY_MASK)
    lib.recompile_material(master)
    unreal.EditorAssetLibrary.set_metadata_tag(master, LEAF_TAG, "1")
    unreal.EditorAssetLibrary.save_loaded_asset(master)
    return "leaves now grow with restoration"


# --- Running it ---

def clear():
    removed = ls_world_common.clear_generated()
    return removed


STAGES = ["foliage", "clear", "trail", "scenery", "gameplay", "hand", "start_approach", "natural_trail01", "riverbank_trail05", "world", "leaves", "save"]


def run(stage):
    require_map()
    if stage == "foliage":
        result = rebuild_foliage()
    elif stage == "trail":
        result = trail(load_plan())
    elif stage == "clear":
        result = clear()
    elif stage == "scenery":
        result = scenery(load_plan())
    elif stage == "gameplay":
        gameplay(load_plan())
        result = dict(ls_world_common.counts)
    elif stage == "hand":
        result = hand_placed()
    elif stage == "protect":
        result = protect_hand_placed()
    elif stage == "extras":
        result = extras()
    elif stage == "fun":
        result = fun()
    elif stage == "ghost":
        result = remove_ghost()
    elif stage == "collapsing_crossing":
        import ls_apply_collapsing_crossing
        importlib.reload(ls_apply_collapsing_crossing)
        result = ls_apply_collapsing_crossing.build()
    elif stage == "start_approach":
        import ls_extend_start
        importlib.reload(ls_extend_start)
        assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
        result = ls_extend_start.build()
    elif stage == "natural_trail01":
        import ls_natural_trail01
        importlib.reload(ls_natural_trail01)
        result = ls_natural_trail01.build()
    elif stage == "riverbank_trail05":
        import ls_trail05_riverbank
        importlib.reload(ls_trail05_riverbank)
        result = ls_trail05_riverbank.build()
    elif stage == "intro":
        result = intro()
    elif stage == "world":
        result = world_setup()
    elif stage == "leaves":
        result = leaves()
    elif stage == "save":
        result = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    else:
        raise RuntimeError("Last Seed Wildwood: unknown stage " + stage)
    unreal.log("Last Seed Wildwood: {} -> {}".format(stage, result))
    return result
