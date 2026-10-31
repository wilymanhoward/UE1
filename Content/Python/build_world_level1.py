# Last Seed - turns the Level 1 greybox into the Withered Forest at sunset.
#
# Purpose: copies L_Level1 to L_Level1_World, hides the cubes (which stay as smooth collision), and builds natural
# ground, three rings of forest, invisible boundaries, sunset lighting and preview cameras around the same route.
# Every gameplay actor keeps its place. Safe to rerun: it replaces only actors tagged LS_Generated, and a fixed random
# seed gives the same forest each time. L_Level1 itself is never changed.
# Requires: Python Editor Script Plugin. Run with Tools > Execute Python Script.

import importlib
import math
import random

import unreal

import ls_material_helpers
import ls_world_common

importlib.reload(ls_material_helpers)
importlib.reload(ls_world_common)

from ls_material_helpers import blend, colour, combine, finish, fresh_material, mask, node, number, output, texture, world_uv
from ls_world_common import (Scatter, Terrain, base_height_offset, clear_generated, greybox_actors, hide_component, invisible_wall,
                             jittered_grid, kill_volume, lerp, mesh_actor, niagara, open_world_map, point_light, preview_camera,
                             report, set_up_sky, smooth_noise, smoothstep, spread_coordinates, take_preview_screenshots)

SOURCE_MAP = "/Game/L_Level1"
WORLD_MAP = "L_Level1_World"
SEED = 1711
LANE = 600.0  # Half the width of the walkable path.
EDGE = 650.0  # Half the width including the curbs. The invisible walls start here.
CHASM = -1300.0

ZONES = [("1_1", 0.0, 9800.0), ("1_2", 9800.0, 17800.0), ("1_3", 17800.0, 32200.0)]
SHOW_AS_ROCK = ("Ledge", "SecretLedge")
HIDE = ("Floor", "Curb", "Bank", "MarshBed", "MarshWall", "WaterSurface", "GoalMarker")

mesh_paths = {}


def mesh(name):
    """Finds a Fab mesh by name, so the lists below stay readable and survive a pack's folders changing."""
    if not mesh_paths:
        registry = unreal.AssetRegistryHelpers.get_asset_registry()
        for folder in ("/Game/Polytope_Studio", "/Game/StyleHex_Studio", "/Game/Stylized_PBR_Nature", "/Game/RocksPackDEMO"):
            for data in registry.get_assets_by_path(folder, recursive=True):
                if str(data.asset_class_path.asset_name) == "StaticMesh":
                    mesh_paths[str(data.asset_name)] = str(data.package_name)
    return mesh_paths[name]


# --- Reading the route from the greybox actors ---

class Route:
    def __init__(self):
        self.pieces = []  # (x0, x1, z0, z1), sorted along X.
        self.pockets = []  # (x0, x1, y_far), side areas that lead to a hidden petal. All are on the +Y side here.
        self.water = None
        self.marsh = None
        for actor in greybox_actors():
            if not isinstance(actor, unreal.StaticMeshActor):
                continue
            label = actor.get_actor_label()
            origin, extent = actor.get_actor_bounds(False)
            if label == "Floor":
                self.pieces.append((origin.x - extent.x, origin.x + extent.x, origin.z + extent.z, origin.z + extent.z))
            elif label == "MarshBed":
                top = origin.z + extent.z
                self.pieces.append((origin.x - extent.x, origin.x + extent.x, top, top))
                self.marsh = (origin.x - extent.x, origin.x + extent.x)
            elif label == "WaterSurface":
                self.water = origin.z + extent.z
            elif label == "SecretLedge":
                self.pockets.append((origin.x - extent.x - 300.0, origin.x + extent.x + 300.0, origin.y + extent.y + 300.0))
            elif label == "Ramp" and extent.y > LANE - 1.0:
                # The surface ends come from the rotated box, as bounds alone can't tell which end is higher.
                forward = actor.get_actor_forward_vector()
                up = actor.get_actor_up_vector()
                scale = actor.get_actor_scale3d()
                centre = actor.get_actor_location()
                ends = []
                for sign in (-1.0, 1.0):
                    ends.append((centre.x + forward.x * scale.x * 50.0 * sign + up.x * scale.z * 50.0,
                                 centre.z + forward.z * scale.x * 50.0 * sign + up.z * scale.z * 50.0))
                ends.sort()
                self.pieces.append((ends[0][0], ends[1][0], ends[0][1], ends[1][1]))
        self.pieces.sort()
        self.start = self.pieces[0][0]
        self.end = self.pieces[-1][1]
        self.gaps = [(a[1], b[0]) for a, b in zip(self.pieces, self.pieces[1:]) if b[0] - a[1] > 50.0]

    def surface(self, x):
        """The floor height at x, or None over a gap."""
        for x0, x1, z0, z1 in self.pieces:
            if x0 - 1.0 <= x <= x1 + 1.0:
                return lerp(z0, z1, (x - x0) / max(x1 - x0, 1.0))
        return None

    def base(self, x):
        """Like surface, but it bridges the gaps and ignores the marsh basin, which suits the ground beside the path."""
        below = self.pieces[0][2]
        for x0, x1, z0, z1 in self.pieces:
            if self.marsh and x0 == self.marsh[0]:
                continue
            if x > x1:
                below = z1
            elif x >= x0:
                return lerp(z0, z1, (x - x0) / max(x1 - x0, 1.0))
            else:
                return below + (z0 - below) * 0.5
        return below

    def in_pocket(self, x, y, margin=0.0):
        return any(x0 - margin <= x <= x1 + margin and -margin <= y <= far + margin for x0, x1, far in self.pockets)

    def outside_distance(self, x, y):
        """Distance from the walkable area, 0 inside it."""
        if self.in_pocket(x, y):
            return 0.0
        return math.hypot(max(abs(y) - EDGE, 0.0), max(self.start - x, x - self.end, 0.0))

    def gap_amount(self, x):
        for x0, x1 in self.gaps:
            if x0 < x < x1:
                return min(smoothstep(x0, x0 + 60.0, x), 1.0 - smoothstep(x1 - 60.0, x1, x))
        return 0.0

    def marsh_amount(self, x):
        if not self.marsh:
            return 0.0
        return smoothstep(self.marsh[0] - 300.0, self.marsh[0] + 100.0, x) * (1.0 - smoothstep(self.marsh[1] - 100.0, self.marsh[1] + 300.0, x))

    def height(self, x, y):
        on_route = self.start <= x <= self.end
        if on_route and abs(y) <= EDGE:
            surface = self.surface(x)
            if surface is None:
                return CHASM
            if abs(y) <= LANE:
                return surface - 2.0
            if self.marsh and self.marsh[0] <= x <= self.marsh[1]:
                return self.water + 15.0
            # Low earth banks hide the curbs' straight lines.
            return surface + 78.0 * smoothstep(LANE, EDGE, abs(y))

        base = self.base(x)
        distance = self.outside_distance(x, y)
        side = max(abs(y) - EDGE, 0.0)
        height = base - 20.0 + 100.0 * (1.0 - smoothstep(0.0, 250.0, distance))
        height += smoothstep(300.0, 4500.0, distance) * (250.0 + 350.0 * smooth_noise(x, y, 1.3))
        height += 25.0 * smooth_noise(x * 7.0, y * 7.0, 4.1)
        # Mountains on every horizon, so the world never visibly ends.
        height += smoothstep(9000.0, 70000.0, distance) * (3500.0 + 2500.0 * smooth_noise(x * 0.5, y * 0.5, 2.7))

        if self.in_pocket(x, y):
            height = base - 20.0
        height = lerp(height, self.water - 70.0, self.marsh_amount(x) * (1.0 - smoothstep(200.0, 2400.0, side))) if self.water else height
        return lerp(height, CHASM, self.gap_amount(x) * (1.0 - smoothstep(150.0, 1600.0, side)))

    def path_mask(self, x, y):
        if self.in_pocket(x, y):
            return 0.4
        inside_route = 1.0 - smoothstep(0.0, 200.0, max(self.start - x, x - self.end, 0.0))
        return inside_route * (1.0 - smoothstep(LANE - 60.0, EDGE + 110.0, abs(y) + 40.0 * smooth_noise(x * 5.0, y, 3.3)))


# --- Materials ---

def build_materials():
    terrain_folder = "/Game/Stylized_PBR_Nature/Terrain"
    materials = {}

    material = fresh_material("M_LS_Terrain")
    uv = node(material, unreal.MaterialExpressionTextureCoordinate)
    path = mask(material, uv, True)
    # V is written as 1 - steepness in the OBJ file, and comes back through the importer's flip as plain steepness.
    steep = mask(material, uv, False)
    grass = combine(material, unreal.MaterialExpressionMultiply, texture(material, terrain_folder + "/T_Grass_2", world_uv(material, 500.0)), colour(material, 0.62, 0.52, 0.34))
    dirt = combine(material, unreal.MaterialExpressionMultiply, texture(material, terrain_folder + "/T_Dirt", world_uv(material, 420.0)), colour(material, 1.15, 1.05, 0.9))
    rock = texture(material, terrain_folder + "/T_rock", world_uv(material, 900.0))
    base = blend(material, blend(material, grass, dirt, path), rock, steep)
    output(material, base, unreal.MaterialProperty.MP_BASE_COLOR)
    output(material, number(material, 0.92), unreal.MaterialProperty.MP_ROUGHNESS)
    materials["terrain"] = finish(material)

    material = fresh_material("M_LS_Rock")
    # Three flat projections blended by the surface direction would be sharper, but this cube only shows rough stone.
    world_rock = texture(material, terrain_folder + "/T_rock", world_uv(material, 400.0))
    output(material, combine(material, unreal.MaterialExpressionMultiply, world_rock, colour(material, 0.75, 0.7, 0.65)), unreal.MaterialProperty.MP_BASE_COLOR)
    output(material, number(material, 0.9), unreal.MaterialProperty.MP_ROUGHNESS)
    materials["rock"] = finish(material)

    material = fresh_material("M_LS_CrackedRock")
    # Glowing cracks like the Stone Shell's own, which hints that Stone is what breaks this wall.
    position = node(material, unreal.MaterialExpressionWorldPosition)
    cracks = node(material, unreal.MaterialExpressionNoise, noise_function=unreal.NoiseFunction.NOISEFUNCTION_VORONOI_ALU, scale=0.012, levels=1, output_min=0.0, output_max=1.0, turbulence=False)
    ls_material_helpers.library.connect_material_expressions(position, "", cracks, "Position")
    shaped = combine(material, unreal.MaterialExpressionMultiply, combine(material, unreal.MaterialExpressionSubtract, cracks, number(material, 0.7)), number(material, 14.0))
    limit = node(material, unreal.MaterialExpressionSaturate)
    ls_material_helpers.library.connect_material_expressions(shaped, "", limit, "")
    output(material, combine(material, unreal.MaterialExpressionMultiply, texture(material, terrain_folder + "/T_rock", world_uv(material, 400.0)), colour(material, 0.6, 0.55, 0.5)), unreal.MaterialProperty.MP_BASE_COLOR)
    output(material, combine(material, unreal.MaterialExpressionMultiply, limit, colour(material, 9.0, 4.5, 1.0)), unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    materials["cracked"] = finish(material)

    def glow(name, r, g, b, strength):
        glow_material = fresh_material(name)
        base_colour = colour(glow_material, r, g, b)
        output(glow_material, base_colour, unreal.MaterialProperty.MP_BASE_COLOR)
        output(glow_material, combine(glow_material, unreal.MaterialExpressionMultiply, base_colour, number(glow_material, strength)), unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        return finish(glow_material)

    # Strong emissive values burn out to white, so these stay low to keep their colour.
    materials["guide"] = glow("M_LS_GuideGlow", 1.0, 0.42, 0.06, 0.9)
    materials["plate"] = glow("M_LS_Plate", 0.8, 0.5, 0.15, 1.5)
    materials["pad"] = glow("M_LS_LilyPad", 0.16, 0.34, 0.1, 0.05)
    materials["thorn"] = glow("M_LS_Thorn", 0.5, 0.03, 0.05, 0.6)
    materials["blob"] = glow("M_LS_Blob", 0.02, 0.01, 0.03, 0.0)
    materials["note"] = glow("M_LS_Note", 1.0, 0.55, 0.08, 1.3)
    materials["petal"] = glow("M_LS_Petal", 1.0, 0.25, 0.4, 1.3)
    materials["shrine"] = glow("M_LS_Shrine", 0.3, 0.75, 1.0, 1.2)
    return materials


# --- Dressing the greybox ---

def keep_coloured(actor, material):
    """Things the player needs to find stay in colour while the world around them is grey."""
    components = actor.get_components_by_class(unreal.StaticMeshComponent)
    # Only the class's own Mesh is used. It bobs and spins, and any placeholder shapes added in the Blueprint don't.
    component = [item for item in components if item.get_name() == "Mesh"][0]
    for other in components:
        if other != component:
            hide_component(other)
            other.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    component.set_render_custom_depth(True)
    component.set_custom_depth_stencil_value(ls_world_common.FULL_COLOUR_STENCIL)
    if material:
        component.set_material(0, material)
    return component


def fit_mesh(component, mesh_path, height, floor_offset):
    """Swaps in a mesh, scaled to the wanted height, with its base floor_offset below the actor's origin."""
    loaded = unreal.load_asset(mesh_path)
    bounds = loaded.get_bounds()
    scale = height / max(bounds.box_extent.z * 2.0, 1.0)
    component.set_static_mesh(loaded)
    component.set_editor_property("override_materials", [])
    component.set_relative_scale3d(unreal.Vector(scale, scale, scale))
    component.set_relative_location(unreal.Vector(0.0, 0.0, floor_offset - (bounds.origin.z - bounds.box_extent.z) * scale), False, False)


def dress_greybox(route, materials):
    rng = random.Random(SEED + 1)
    thorns = Scatter("Thorns", 0, 0, material=materials["thorn"], stencil=True)
    for actor in greybox_actors():
        label = actor.get_actor_label()
        class_name = actor.get_class().get_name()

        if isinstance(actor, unreal.StaticMeshActor):
            if label == "Dressing":
                # The greybox's few scattered meshes. The forest rings below replace them.
                ls_world_common.actor_subsystem.destroy_actor(actor)
            elif label in HIDE or (label == "Ramp" and actor.get_actor_scale3d().y * 50.0 > LANE - 1.0):
                hide_component(actor.static_mesh_component)
            elif label in SHOW_AS_ROCK or label == "Ramp":
                actor.static_mesh_component.set_material(0, materials["rock"])
        elif class_name == "CrackedWall":
            actor.get_component_by_class(unreal.StaticMeshComponent).set_material(0, materials["cracked"])
        elif class_name == "Gate":
            actor.get_component_by_class(unreal.StaticMeshComponent).set_material(0, materials["rock"])
        elif class_name == "PressurePlate":
            actor.get_component_by_class(unreal.StaticMeshComponent).set_material(0, materials["plate"])
        elif class_name == "PushableBlock":
            actor.get_component_by_class(unreal.StaticMeshComponent).set_material(0, materials["rock"])
        elif class_name == "SinkingPad":
            # A cylinder has simple collision like the cube's, and its round shape reads as a lily pad.
            component = actor.get_component_by_class(unreal.StaticMeshComponent)
            component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Cylinder"))
            component.set_material(0, materials["pad"])
        elif class_name == "WitherBlob":
            actor.get_component_by_class(unreal.StaticMeshComponent).set_material(0, materials["blob"])
        elif class_name == "BP_LifeNote_C":
            component = keep_coloured(actor, None)
            component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Sphere"))
            component.set_relative_scale3d(unreal.Vector(0.55, 0.55, 0.55))
            component.set_material(0, materials["note"])
        elif class_name == "BP_GoldenPetal_C":
            component = keep_coloured(actor, None)
            fit_mesh(component, mesh("SM_Poppy_02"), 170.0, -40.0)
        elif class_name == "BP_CheckpointShrine_C":
            component = keep_coloured(actor, None)
            fit_mesh(component, mesh("SM_Menhir_Rock_02"), 280.0, -50.0)
            component.set_material(0, materials["shrine"])
        elif class_name == "BP_FormFlower_Stone_C":
            component = keep_coloured(actor, None)
            fit_mesh(component, mesh("SM_Fol_Flower_Clump_1"), 160.0, -80.0)
        elif class_name == "HazardVolume":
            hide_component(actor.get_component_by_class(unreal.StaticMeshComponent))
            origin, extent = actor.get_actor_bounds(False)
            for x, y in jittered_grid(origin.x - extent.x + 60, origin.x + extent.x, origin.y - extent.y + 60, origin.y + extent.y, 130.0, rng):
                thorns.add(mesh("SM_Generic_Shrub_01_dead"), x, y, origin.z - extent.z, rng.uniform(0.7, 1.15), rng)
        elif class_name == "RestorableActor":
            # Regrowth rests on the new ground, which has hills the flat greybox bank didn't.
            location = actor.get_actor_location()
            component = actor.get_component_by_class(unreal.StaticMeshComponent)
            scale = actor.get_actor_scale3d().z
            if component.static_mesh:
                location.z = route.height(location.x, location.y) - base_height_offset(component.static_mesh, scale)
                actor.set_actor_location(location, False, False)
    thorns.build()


# --- Scenery rings ---

def zone_at(x):
    for name, x0, x1 in ZONES:
        if x < x1:
            return name
    return ZONES[-1][0]


# What grows where. Each zone has its own feel using the same packs.
PALETTES = {
    "1_1": {"trees": ["SM_Pine_Tree_03_dead", "SM_Pine_Tree_03_dead", "SM_Fruit_Tree_01_dead", "SM_Pine_Tree_03_dead_cut"],
            "edge": ["SM_R_Rock_01", "SM_R_Rock_02", "SM_S_Rock_01", "SM_Generic_Shrub_01_dead", "SM_Generic_Shrub_01_dead", "SM_Pine_Tree_03_stump", "SM_Fruit_Tree_01_logs"],
            "under": ["SM_Fol_Grass_Clump_1", "SM_Fern", "SM_Generic_Shrub_01_dead"]},
    "1_2": {"trees": ["SM_Pine_Tree_03_dead_cut", "SM_Fruit_Tree_01_dead_cut", "SM_Pine_Tree_03_dead", "SM_Fruit_Tree_01_dead"],
            "edge": ["SM_Pine_Tree_03_logs", "SM_Fruit_Tree_01_logs", "SM_Pine_Tree_03_stump", "SM_Fruit_Tree_01_stump", "SM_S_Rock_02", "SM_R_Rock_03"],
            "under": ["SM_Fern", "SM_Clover", "SM_Generic_Shrub_01_dead"]},
    "1_3": {"trees": ["SM_Fruit_Tree_01_dead", "SM_Fruit_Tree_01_dead", "SM_Pine_Tree_03_dead", "SM_Fruit_Tree_01_dead_cut"],
            "edge": ["SM_River_Rock_Pile_02", "SM_R_Rock_04", "SM_Generic_Shrub_01_dead", "SM_Fruit_Tree_01_logs", "SM_Pine_Tree_03_logs"],
            "under": ["SM_Fern", "SM_Fern", "SM_Clover", "SM_Fol_Grass_Clump_1"]},
}


def usable(route, x, y, distance_range, margin=120.0):
    """False on the walkable area, over water and in the chasms. Everything left is safe to fill."""
    distance = route.outside_distance(x, y)
    if not distance_range[0] <= distance < distance_range[1] or route.in_pocket(x, y, margin):
        return False
    if route.gap_amount(x) > 0.0 and abs(y) < 1500.0:
        return False
    if route.water and route.marsh_amount(x) > 0.0 and route.height(x, y) < route.water + 5.0:
        return False
    return True


def scatter_rings(route, materials):
    rng = random.Random(SEED)
    x0, x1 = route.start, route.end

    # Boundary ring: rocks, logs and shrubs right beside the path, with a tight line of dead trees behind them.
    edge = Scatter("Ring1_Edge", 9000, 12000)
    trees_near = Scatter("Ring1_Trees", 16000, 22000)
    under = Scatter("Ring1_Undergrowth", 5000, 7000, shadows=False)
    for side in (-1, 1):
        y0, y1 = (EDGE + 60.0, EDGE + 500.0) if side > 0 else (-EDGE - 500.0, -EDGE - 60.0)
        for x, y in jittered_grid(x0 - 400, x1 + 400, y0, y1, 210.0, rng):
            if usable(route, x, y, (40.0, 900.0)):
                palette = PALETTES[zone_at(x)]
                name = rng.choice(palette["edge"])
                # Pack rocks are 3 to 6 m tall, which would tower over a 1 m ball right beside the path.
                scale = rng.uniform(0.2, 0.5) if "Rock_0" in name else rng.uniform(0.7, 1.3)
                edge.add(mesh(name), x, y, route.height(x, y), scale, rng, tilt=4.0)
        y0, y1 = (EDGE + 350.0, EDGE + 1300.0) if side > 0 else (-EDGE - 1300.0, -EDGE - 350.0)
        for x, y in jittered_grid(x0 - 800, x1 + 800, y0, y1, 400.0, rng):
            if usable(route, x, y, (300.0, 1500.0)):
                palette = PALETTES[zone_at(x)]
                trees_near.add(mesh(rng.choice(palette["trees"])), x, y, route.height(x, y), rng.uniform(0.9, 1.7), rng, sink=20.0, tilt=3.0)
        y0, y1 = (EDGE + 40.0, EDGE + 1400.0) if side > 0 else (-EDGE - 1400.0, -EDGE - 40.0)
        for x, y in jittered_grid(x0 - 400, x1 + 400, y0, y1, 170.0, rng):
            if usable(route, x, y, (20.0, 1500.0)):
                palette = PALETTES[zone_at(x)]
                under.add(mesh(rng.choice(palette["under"])), x, y, route.height(x, y), rng.uniform(0.7, 1.3), rng)
    # The two ends of the route need closing off too.
    for x, y in jittered_grid(x0 - 1500, x0 - 100, -2000, 2000, 300.0, rng):
        trees_near.add(mesh(rng.choice(PALETTES["1_1"]["trees"])), x, y, route.height(x, y), rng.uniform(1.0, 1.7), rng, sink=20.0)
    for x, y in jittered_grid(x1 + 300, x1 + 1800, -2000, 2000, 300.0, rng):
        trees_near.add(mesh(rng.choice(PALETTES["1_3"]["trees"])), x, y, route.height(x, y), rng.uniform(1.0, 1.7), rng, sink=20.0)

    # Middle ring: forest in depth, with large rocks breaking it up.
    middle = Scatter("Ring2_Middle", 26000, 36000)
    for x, y in jittered_grid(x0 - 6000, x1 + 6000, -6500, 6500, 750.0, rng):
        if usable(route, x, y, (1500.0, 6000.0)):
            kind = rng.random()
            if kind < 0.72:
                middle.add(mesh(rng.choice(PALETTES[zone_at(x)]["trees"])), x, y, route.height(x, y), rng.uniform(1.2, 2.0), rng, sink=20.0, tilt=3.0)
            elif kind < 0.9:
                middle.add(mesh(rng.choice(["SM_S_Rock_09", "SM_S_Rock_04", "SM_RockPack_RockGroups_01_A", "SM_R_Rock_05"])), x, y, route.height(x, y), rng.uniform(0.6, 1.3), rng, sink=30.0)
            else:
                middle.add(mesh(rng.choice(["SM_Bush", "SM_Fol_Bush_2"])), x, y, route.height(x, y), rng.uniform(1.2, 2.2), rng)

    # Far ring: big living trees, which the withering post-process turns grey. They regain their green as the world
    # recovers, which shows the player how far the restoration reaches.
    far = Scatter("Ring3_Far", 110000, 150000, shadows=False)
    far_trees = ["SM_Common_Tree_{:02d}".format(number_) for number_ in range(1, 12)]
    for x, y in jittered_grid(x0 - 30000, x1 + 30000, -38000, 38000, 2500.0, rng):
        if usable(route, x, y, (6000.0, 42000.0)):
            far.add(mesh(rng.choice(far_trees)), x, y, route.height(x, y), rng.uniform(2.2, 3.4), rng, sink=30.0)

    for scatter in (edge, trees_near, under, middle, far):
        scatter.build()


def rock_set_pieces(route, materials):
    """Cliffs where the player should feel enclosed, and at each edge the eye is drawn to."""
    folder = "Set Pieces"

    def rock(name, x, y, height_offset, scale, yaw=0.0):
        path = mesh(name)
        loaded = unreal.load_asset(path)
        ground = route.height(x, y) + height_offset
        return mesh_actor(path, x, y, ground - base_height_offset(loaded, scale), folder, (scale, scale, scale), yaw)

    # Rootwood Hollow: high walls either side of the whole zone, so it feels like a canyon among old roots.
    rng = random.Random(SEED + 2)
    x = 10600.0
    while x < 17400.0:
        for side in (-1, 1):
            rock(rng.choice(["SM_RockPack_Cliff_07_B", "SM_RockPack_Cliff_07_D", "SM_S_Rock_10", "SM_S_Rock_04"]),
                 x + rng.uniform(-150, 150), side * rng.uniform(1100, 1500), -40.0, rng.uniform(1.0, 1.7), rng.uniform(0, 360))
        x += 850.0

    # Fallen trunks high across the path. They have no collision, so they can't block a jump.
    for x, z_extra, yaw in ((11300.0, 700.0, 82.0), (14100.0, 800.0, 97.0), (16300.0, 680.0, 75.0)):
        trunk = mesh("SM_Pine_Tree_03_dead_cut")
        base = route.height(x, 0.0)
        mesh_actor(trunk, x, -900.0 * math.cos(math.radians(yaw - 90.0)), base + z_extra, folder, (2.2, 2.2, 2.2), yaw, pitch=-88.0)

    # Rock under each lip of a gap, so the chasm has a real edge and not a sheer cut in the ground.
    for gap0, gap1 in route.gaps:
        for lip, direction in ((gap0, 1.0), (gap1, -1.0)):
            top = route.surface(lip)
            for y in (-420.0, 0.0, 420.0):
                scale = 1.0
                cliff = mesh("SM_RockPack_Cliff_07_D")
                loaded = unreal.load_asset(cliff)
                bounds = loaded.get_bounds()
                # The rock's top stays just under the walkable surface, so it can't catch the eye as a bump.
                z = top - 12.0 - (bounds.origin.z + bounds.box_extent.z) * scale
                mesh_actor(cliff, lip + direction * 210.0, y, z, folder, (scale, scale, scale), 90.0 * direction + y * 0.05)

    # Hide the plain ends of the marsh walls and frame the cracked wall and gate, which are the zone's landmarks.
    for actor in greybox_actors():
        name = actor.get_class().get_name()
        if actor.get_actor_label() == "Ledge":
            # Rubble against the step's straight front edge. It has no collision, so it can't change the hop.
            origin, extent = actor.get_actor_bounds(False)
            y = -LANE + 60.0
            while y < LANE:
                rock(rng.choice(["SM_R_Rock_01", "SM_R_Rock_02", "SM_S_Rock_01"]), origin.x - extent.x - rng.uniform(5, 30), y, -30.0, rng.uniform(0.18, 0.3), rng.uniform(0, 360))
                y += 170.0
        if name in ("CrackedWall", "Gate"):
            location = actor.get_actor_location()
            for side in (-1, 1):
                rock("SM_RockPack_Cliff_07_B", location.x, side * 1050.0, -60.0, 1.25, side * 60.0)
            niagara("/Game/FreeParticle_SoftTofu/Niagara/NS_Sparkling_Glow", location.x - 250.0, 0.0, location.z - 150.0, folder, 2.0)


def build_water(route):
    x0, x1 = route.marsh
    water = unreal.load_asset("/Game/Stylized_PBR_Nature/Terrain/M_Water_Basic")
    length = x1 - x0 + 900.0
    mesh_actor("/Engine/BasicShapes/Plane", (x0 + x1) / 2.0, 0.0, route.water - 3.0, "Water", (length / 100.0, 56.0, 1.0), material=water, label="MarshWater")


def build_boundaries(route):
    top = 4500.0
    bottom = -1400.0
    x0, x1 = route.start - 50.0, route.end + 50.0
    invisible_wall(x0, -EDGE - 50.0, x0, EDGE + 50.0, bottom, top)
    invisible_wall(x1, -EDGE - 50.0, x1, EDGE + 50.0, bottom, top)
    invisible_wall(x0, -EDGE - 50.0, x1, -EDGE - 50.0, bottom, top)

    # The +Y wall has openings where a side area leads to a hidden petal, each with its own three walls.
    cursor = x0
    for pocket_x0, pocket_x1, far in sorted(route.pockets):
        invisible_wall(cursor, EDGE + 50.0, pocket_x0, EDGE + 50.0, bottom, top)
        invisible_wall(pocket_x0, EDGE, pocket_x0, far, bottom, top)
        invisible_wall(pocket_x1, EDGE, pocket_x1, far, bottom, top)
        invisible_wall(pocket_x0, far + 50.0, pocket_x1, far + 50.0, bottom, top)
        cursor = pocket_x1
    invisible_wall(cursor, EDGE + 50.0, x1, EDGE + 50.0, bottom, top)

    # Each gap gets its own kill volume, closer than the level's big one, so a fall resets quickly.
    for gap0, gap1 in route.gaps:
        kill_volume((gap0 + gap1) / 2.0, 800.0, -750.0, (gap1 - gap0) / 2.0 + 100.0, 2000.0)


def build_guides(route, materials):
    """Warm lights lead the eye along the route. Their stencil keeps them coloured while the world around is grey."""
    rng = random.Random(SEED + 3)
    glow = Scatter("Guide_Mushrooms", 9000, 12000, shadows=False, material=materials["guide"], stencil=True)
    mushroom = mesh("SM_Caesars_Mushroom_01")
    x = route.start + 200.0
    while x < route.end:
        surface = route.surface(x)
        if surface is not None and route.marsh_amount(x) == 0.0:
            for side in (-1, 1):
                glow.add(mushroom, x + rng.uniform(-60, 60), side * (LANE - rng.uniform(10, 40)), surface, rng.uniform(1.0, 1.5), rng, sink=2.0)
        x += 260.0
    glow.build()

    warm = unreal.LinearColor(1.0, 0.62, 0.28, 1.0)
    for actor in greybox_actors():
        name = actor.get_class().get_name()
        location = actor.get_actor_location()
        if name in ("BP_CheckpointShrine_C", "BP_FormFlower_Stone_C", "CrackedWall", "Gate", "LevelGoal", "BP_GoldenPetal_C"):
            point_light(location.x, location.y, location.z + 300.0, warm, 90.0 if name == "LevelGoal" else 30.0, 1400.0)
    for gap0, gap1 in route.gaps:
        point_light(gap1 + 150.0, 0.0, route.surface(gap1) + 300.0, warm, 45.0, 1500.0)

    # The end of the level: a living tree, which is what the whole climb back to colour has been about.
    goal_x = route.end - 200.0
    tree = mesh("SM_Tree_Broadleaf_1")
    loaded = unreal.load_asset(tree)
    z = route.surface(goal_x)
    mesh_actor(tree, goal_x, 0.0, z - base_height_offset(loaded, 1.3), "Guide Lights", (1.3, 1.3, 1.3))
    niagara("/Game/FreeParticle_SoftTofu/Niagara/NS_Sparkling_Glow", goal_x, 0.0, z + 300.0, "Guide Lights", 4.0)


def build_preview_cameras(route):
    cameras = []
    for name, x0, x1 in ZONES:
        middle = (x0 + x1) / 2.0
        z = route.base(middle)
        cameras.append(preview_camera("Preview_{}_A".format(name), (x0 + 400.0, -200.0, route.base(x0 + 400.0) + 220.0), (x0 + 3400.0, 0.0, route.base(x0 + 3400.0) + 120.0)))
        cameras.append(preview_camera("Preview_{}_B".format(name), (middle, 420.0, z + 170.0), (middle - 2200.0, -400.0, z + 300.0)))
        cameras.append(preview_camera("Preview_{}_C".format(name), (middle - 1800.0, -7000.0, z + 4200.0), (middle + 1000.0, 0.0, z)))
    return cameras


def main():
    world_path = open_world_map(SOURCE_MAP, WORLD_MAP)
    clear_generated()
    route = Route()
    materials = build_materials()

    sharp_x = []
    for x0, x1 in route.gaps:
        sharp_x += [x0, x0 + 60.0, x1 - 60.0, x1]
    for piece in route.pieces:
        sharp_x += [piece[0], piece[1]]
    xs = spread_coordinates(route.start - 110000.0, route.end + 110000.0, route.start - 3000.0, route.end + 3000.0, 150.0, sharp=sharp_x)
    ys = spread_coordinates(-110000.0, 110000.0, -6000.0, 6000.0, 150.0, sharp=[-EDGE, -LANE, LANE, EDGE])
    terrain_path = Terrain(route.height, route.path_mask).write_and_import("SM_LS_Terrain_L1", xs, ys)
    mesh_actor(terrain_path, 0.0, 0.0, 0.0, "Terrain", material=materials["terrain"], label="Terrain")

    dress_greybox(route, materials)
    scatter_rings(route, materials)
    rock_set_pieces(route, materials)
    build_water(route)
    build_boundaries(route)
    build_guides(route, materials)

    set_up_sky(sun_pitch=-8.0, sun_yaw=196.0, sun_colour=unreal.LinearColor(1.0, 0.58, 0.32, 1.0), sun_lux=7.0,
               cloud_material="/Game/StylizedVolClouds/Materials/MI/MI_VolumetricCloud_Cloudy",
               driver_fog=(0.02, 0.008), fog_colour=unreal.LinearColor(0.42, 0.2, 0.12, 1.0), exposure=-0.8, sky_light=1.0)

    # The default grade is cold and almost colourless, which would hide the sunset this level is built around.
    driver = ls_world_common.find_actor(unreal.RestorationDriver)
    driver.set_editor_property("withered_saturation", 0.4)
    driver.set_editor_property("withered_tint", unreal.LinearColor(1.05, 0.9, 0.78, 1.0))

    cameras = build_preview_cameras(route)
    report(world_path)
    take_preview_screenshots(cameras)


main()
