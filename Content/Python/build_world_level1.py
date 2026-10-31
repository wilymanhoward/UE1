# Last Seed - turns the straight Level 1 greybox into a winding Withered Forest at sunset.
#
# Purpose: copies L_Level1 to L_Level1_World, bends the route along a curved road with hills, moves every gameplay actor
# onto it, adds the extra challenges that make the level last about 4:45, and builds the ground, forest, boundaries and
# light around it. The art follows three concept pictures, one per zone.
#
# How the bending works: every greybox position (x, y, z) becomes distance along the road s = to_road(x), distance to its
# right d = y, and height z + hills(s). Sections with a jump or a block puzzle are straight and flat, so they play the same.
#
# Safe to rerun: each greybox actor remembers its original place in a tag, generated actors are tagged LS_Generated and
# replaced, and a fixed random seed gives the same forest. L_Level1 itself is never changed.
# Requires: Python Editor Script Plugin. Run with Tools > Execute Python Script.

import importlib
import math
import random

import unreal

import ls_curved_route
import ls_generate_player_meshes
import ls_generate_world_meshes
import ls_material_helpers
import ls_world_common

for module in (ls_curved_route, ls_generate_player_meshes, ls_generate_world_meshes, ls_material_helpers, ls_world_common):
    importlib.reload(module)

from ls_generate_player_meshes import Mesh
from ls_material_helpers import blend, colour, combine, finish, fresh_material, mask, node, number, output, texture, world_uv
from ls_world_common import (Scatter, Terrain, base_height_offset, clear_generated, greybox_actors, hide_component, import_generated_mesh,
                             invisible_wall, jittered_grid, kill_volume, lerp, mesh_actor, niagara, open_world_map, point_light,
                             preview_camera, report, set_up_sky, smooth_noise, smoothstep, spawn, spread_coordinates, take_preview_screenshots, zone_grade)

SOURCE_MAP = "/Game/L_Level1"
WORLD_MAP = "L_Level1_World"
SEED = 1711
LANE = 600.0  # Half the width of the walkable road.
EDGE = 650.0  # Half the width including its low banks. The invisible walls start here.
ROAD_SIDE = 1050.0  # How far the fine road mesh reaches, where it meets the coarser terrain.
CHASM = -1300.0
ORIGIN_TAG = "LS_Origin"

# --- The layout, all in one place ---

ROAD_LENGTH = 41700.0
# (start, end, degrees). Positive turns right. Everything between bends is straight on purpose: gaps, ledge, cave, plates, gate, marsh.
BENDS = [(500, 3200, 35), (4100, 5500, -60), (8900, 11800, 70), (12200, 14000, -50), (16000, 16600, 20),
         (19500, 20800, 40), (20800, 22800, -50), (22800, 24800, 55), (29700, 33800, -85), (33800, 36000, 40), (39900, 41700, -30)]
# (greybox x, extra length). This is where the new challenges fit between the greybox's own.
INSERTS = [(6490, 2400), (14300, 2000), (17100, 1000), (21500, 1500), (24400, 1000), (29500, 1600)]
# Height added to the greybox's own, as (s, height). Flat wherever two neighbours match. Steepest about 9 degrees.
HILLS = [(0, 0), (300, 0), (1700, 130), (3200, 0), (4100, 0), (4800, -70), (5500, 0), (12200, 0), (14000, 150), (19700, 150),
         (21000, 40), (23200, 40), (24800, 0), (29700, 0), (31500, 150), (33800, 0), (39700, 0), (41000, 80), (41700, 80)]
# How much the land rises on the left and falls on the right, as (s, height). Negative rises on the right instead.
SIDE_TILT = [(0, 750), (6000, 750), (8000, 200), (12200, 300), (13000, 0), (23000, 0), (24800, 300), (33800, -300), (41700, 200)]
# How much the land rises on both sides, which makes a canyon.
CANYON = [(0, 0), (12200, 0), (13200, 1800), (22500, 1800), (23500, 0), (41700, 0)]

# The greybox's floor as (x0, x1, z0, z1), which gives the height the road starts from.
GREYBOX_FLOOR = [(0, 6500, 0, 0), (6500, 8000, 0, 300), (8000, 26100, 300, 300), (26100, 28100, 300, 800), (28100, 30200, 800, 800), (30200, 32200, 300, 300)]
MARSH = (25000.0, 29500.0)
MARSH_GREYBOX = (19600.0, 22600.0)
WATER_LEVEL = 300.0
MARSH_BED = -50.0
ISLAND_CHAIN = (6490.0, 8890.0)
GAPS = [(3500.0, 3900.0), ISLAND_CHAIN, (36700.0, 37700.0), (38500.0, 39700.0)]
GLIDE_ISLAND = (37700.0, 38500.0, 500.0)  # A landing that splits the glide in two.
# The road's solid pieces, between gaps and the marsh. The first two stay in colour, as the start of picture 1.
ROAD_PIECES = [(-800.0, 3500.0, True), (3900.0, 6490.0, True), (8890.0, 25000.0, False), (29500.0, 36700.0, False), (37700.0, 38500.0, False), (39700.0, ROAD_LENGTH + 800.0, False)]
# (s, d, height). A full-speed jump travels about 890 cm, so 333 cm gaps and 700 cm islands land safely from anywhere near an edge.
ISLANDS = [(7173.0, -120.0, 0.0), (8206.0, 120.0, 40.0)]
ISLAND_RADIUS = 350.0
# (s of the ledge, half width, far side, has a floor). Side areas that lead to the hidden petals. All are on the right.
POCKETS = [(5200.0, 500.0, 2700.0, True), (13400.0, 500.0, 2700.0, True), (37000.0, 500.0, 2500.0, False)]

ZONES = [("1_1", 0.0, 12200.0), ("1_2", 12200.0, 23200.0), ("1_3", 23200.0, ROAD_LENGTH)]
# Zone 1-2. The cave's mouth is just before the wall that breaks, and it opens out before the first plate.
CAVE = (14440.0, 15320.0)
CAVE_WALL_S = 14500.0
# A pool to the right of the road, below a rocky edge. Scenery only, as the walls stop the ball.
POOL = (15400.0, 19000.0)
POOL_BED = 180.0
POOL_WATER = 260.0
# Patch 1 is 200 cm clear of patch 2 at a walking line, so these give Stone room to cross the lane between them.
THORN_SHIFT = 250.0
HEART_TREE = (3000.0, -2700.0)  # (s, d). Where it stands in view from the start, with its roots clear of the road.
# The hop up to the ledge moved back from the first island jump. Coming off it at full speed carries a ball about 330 cm.
LEDGE_SHIFT = -300.0

# Cubes that lose their collision, because the road mesh replaces them.
REPLACED_BY_ROAD = ("Floor", "Curb", "Bank", "GoalMarker")
STAYS_PUT = ("PostProcess", "Fog", "RestorationDriver", "MusicManager", "OpeningStory", "KillVolume")
# These stretch with the marsh, which has more lily pads now.
MARSH_PARTS = ("MarshBed", "MarshWall", "WaterSurface", "Water")

road = ls_curved_route.CurvedRoad(ROAD_LENGTH, BENDS)
SHAPE_SAMPLES = [(float(s), *road.point(s), road.heading(s)) for s in range(0, int(ROAD_LENGTH) + 1, 500)]
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


# --- From the greybox's straight line to the road ---

def to_road(x):
    return x + sum(amount for at, amount in INSERTS if x > at)


def greybox_x(s):
    """The inverse of to_road. It stays still across an inserted section, which has no greybox of its own."""
    x = s
    for at, amount in INSERTS:
        if x <= at:
            break
        x = max(at, x - amount)
    return x


def curve_value(points, s):
    """Eases between (s, value) pairs. Each pair is a flat spot, so joined sections never make a sudden kink."""
    if s <= points[0][0]:
        return points[0][1]
    for (s0, v0), (s1, v1) in zip(points, points[1:]):
        if s <= s1:
            return lerp(v0, v1, smoothstep(s0, s1, s))
    return points[-1][1]


def hills(s):
    return curve_value(HILLS, s)


def level(s):
    """The road's height at s, as if it had no gaps. The ground beside the road follows this."""
    if GLIDE_ISLAND[0] <= s <= GLIDE_ISLAND[1]:
        return GLIDE_ISLAND[2]
    x = greybox_x(s)
    for x0, x1, z0, z1 in GREYBOX_FLOOR:
        if x < x1:
            return lerp(z0, z1, max(x - x0, 0.0) / (x1 - x0)) + hills(s)
    return GREYBOX_FLOOR[-1][3] + hills(s)


def has_road(s):
    return any(s0 <= s <= s1 for s0, s1, _ in ROAD_PIECES)


def gap_amount(s):
    for s0, s1 in GAPS:
        if s0 < s < s1:
            return min(smoothstep(s0, s0 + 60.0, s), 1.0 - smoothstep(s1 - 60.0, s1, s))
    return 0.0


def marsh_amount(s):
    return smoothstep(MARSH[0] - 300.0, MARSH[0] + 100.0, s) * (1.0 - smoothstep(MARSH[1] - 100.0, MARSH[1] + 300.0, s))


def pool_amount(s, d):
    along = smoothstep(POOL[0], POOL[0] + 400.0, s) * (1.0 - smoothstep(POOL[1] - 400.0, POOL[1], s))
    return along * smoothstep(655.0, 820.0, d) * (1.0 - smoothstep(3000.0, 3800.0, d))


def in_pocket(x, y, margin=0.0):
    """Pockets are straight-sided rectangles, so this measures from the ledge's own spot, not along the curved road."""
    for s0, half, far, _ in POCKETS:
        px, py = road.point(s0)
        heading = road.heading(s0)
        along = (x - px) * math.cos(heading) + (y - py) * math.sin(heading)
        side = -(x - px) * math.sin(heading) + (y - py) * math.cos(heading)
        if abs(along) <= half + margin and -margin <= side <= far + margin:
            return True
    return False


def outside_distance(s, d):
    """Distance from the walkable area, 0 inside it."""
    return math.hypot(max(abs(d) - EDGE, 0.0), max(-s, s - ROAD_LENGTH, 0.0))


def shaped_land(x, y):
    """The road's height, hillsides and canyon walls at a point, averaged over the nearby road.
    Taking them only from the nearest road point would make a cliff wherever a different stretch of road becomes nearest."""
    total = base = shape = 0.0
    for s, px, py, heading in SHAPE_SAMPLES:
        dx, dy = x - px, y - py
        distance_squared = dx * dx + dy * dy
        weight = 1.0 / (distance_squared + 90000.0) ** 2
        distance = math.sqrt(distance_squared)
        side = 1.0 if -dx * math.sin(heading) + dy * math.cos(heading) > 0.0 else -1.0
        total += weight
        base += weight * level(s)
        # Picture 1's hillside: the land climbs on one side of the road and drops into a valley on the other.
        shape -= weight * curve_value(SIDE_TILT, s) * side * smoothstep(700.0, 3000.0, distance) * (1.0 - smoothstep(4000.0, 9000.0, distance))
        shape += weight * curve_value(CANYON, s) * smoothstep(700.0, 1500.0, distance) * (1.0 - smoothstep(3500.0, 7000.0, distance))
    return base / total, shape / total


def side_ground(s, d, x, y):
    """The natural ground away from the road: banks, then hills, then mountains."""
    near_s = min(max(s, 0.0), ROAD_LENGTH)
    base, shape = shaped_land(x, y)
    distance = outside_distance(s, d)
    height = base - 20.0 + 100.0 * (1.0 - smoothstep(0.0, 250.0, distance)) + shape
    height += smoothstep(300.0, 4500.0, distance) * (300.0 + 500.0 * smooth_noise(x, y, 1.3))
    height += 25.0 * smooth_noise(x * 7.0, y * 7.0, 4.1)
    # Mountains on every horizon, so the world never visibly ends.
    height += smoothstep(9000.0, 70000.0, distance) * (3500.0 + 2500.0 * smooth_noise(x * 0.5, y * 0.5, 2.7))

    if in_pocket(x, y):
        height = level(near_s) - 20.0
    side = max(abs(d) - EDGE, 0.0)
    height = lerp(height, WATER_LEVEL - 70.0, marsh_amount(near_s) * (1.0 - smoothstep(200.0, 2400.0, side)))
    height = lerp(height, POOL_BED, pool_amount(near_s, d))
    return lerp(height, CHASM, gap_amount(near_s) * (1.0 - smoothstep(150.0, 1600.0, side)))


def road_height(s, d, x, y):
    """The surface the road mesh shows. It is flat across the lane, so a ball never drifts sideways on its own."""
    if abs(d) <= LANE:
        return level(s)
    if abs(d) <= EDGE:
        return level(s) + 78.0 * smoothstep(LANE, EDGE, abs(d))
    return side_ground(s, d, x, y)


def terrain_height(x, y):
    s, d = road.project(x, y)
    if 0.0 <= s <= ROAD_LENGTH and abs(d) < ROAD_SIDE - 100.0:
        if MARSH[0] <= s <= MARSH[1]:
            if abs(d) <= LANE:
                return WATER_LEVEL - 400.0
            return WATER_LEVEL + 15.0
        if has_road(s):
            # Sunk under the road mesh, which is the surface here.
            return road_height(s, d, x, y) - 40.0
    return side_ground(s, d, x, y)


def path_mask_at(s, d, x, y):
    if in_pocket(x, y):
        return 0.4
    inside = 1.0 - smoothstep(0.0, 200.0, max(-s, s - ROAD_LENGTH, 0.0))
    path = inside * (1.0 - smoothstep(LANE - 200.0, EDGE + 110.0, abs(d) + 60.0 * smooth_noise(x * 5.0, y * 5.0, 3.3)))
    # Picture 1's dead mud plain, on the low side of the start.
    mud = smoothstep(1000.0, 2500.0, d) * (1.0 - smoothstep(9000.0, 12000.0, s)) * 0.85
    return max(path, mud)


def terrain_path_mask(x, y):
    s, d = road.project(x, y)
    return path_mask_at(s, d, x, y)


# --- Generated meshes ---

def build_road_mesh(s0, s1, index):
    """A strip following the curve, used as both the visible ground and the floor the ball rolls on."""
    columns = [0.0, 200.0, 400.0, LANE - 50.0, LANE, EDGE, 800.0, 950.0, ROAD_SIDE]
    columns = [-c for c in reversed(columns[1:])] + columns
    rows = []
    s = s0
    while s < s1:
        rows.append(s)
        s += 100.0
    rows.append(s1)

    built = Mesh()
    # Each lip of a gap drops straight down, so the edge is a cliff and not a sheet of paper.
    edge_rows = [(s0, -500.0)] + [(s, 0.0) for s in rows] + [(s1, -500.0)]
    for row, drop in edge_rows:
        for d in columns:
            x, y = road.point(row, d)
            z = road_height(row, d, x, y) + drop
            built.add_vertex((x, y, z), (path_mask_at(row, d, x, y), 0.0))
    width = len(columns)
    for row in range(len(edge_rows) - 1):
        for column in range(width - 1):
            a = row * width + column
            b = a + 1
            c = a + width
            d = c + 1
            built.triangles += [(a, c, b), (b, c, d)]
    built.smooth_normals()
    return import_generated_mesh("SM_LS_Road_L1_{}".format(index), built, solid=True)


def build_stair_mesh(s0, s1):
    """Picture 1's stone stairs. Scenery only: the ball keeps rolling on the smooth ramp beneath, as a bumpy step would stop it."""
    built = Mesh()
    half_width = LANE - 120.0
    step = 110.0
    s = s0
    while s < s1:
        low = level(s) + 1.0
        high = low + 7.0
        for s_near, s_far, z_near, z_far in ((s, s, low, high), (s, s + step, high, high)):
            first = len(built.points)
            for along, z in ((s_near, z_near), (s_far, z_far)):
                for d in (-half_width, half_width):
                    x, y = road.point(along, d)
                    built.add_vertex((x, y, z), (0.0, 0.0))
            built.triangles += [(first, first + 2, first + 1), (first + 1, first + 2, first + 3)]
        s += step
    built.smooth_normals()
    return import_generated_mesh("SM_LS_Stairs_L1", built)


def build_cave_shell():
    """A rock hill with a tunnel through it, following the road. The ball rolls on the road and the rock is solid, which also keeps the camera inside."""
    built = Mesh()
    rows, columns = 24, 26
    inner_half, inner_high = 800.0, 680.0
    outer_half, outer_high = 2000.0, 1500.0
    base = level((CAVE[0] + CAVE[1]) / 2.0)

    def lumps(row, column, size):
        return size * (math.sin(row * 1.3 + column * 0.7) * 0.5 + math.sin(row * 0.4 - column * 1.9 + 2.0) * 0.5)

    for surface, half, high, sink, lump in ((0, inner_half, inner_high, 30.0, 26.0), (1, outer_half, outer_high, 120.0, 90.0)):
        for row in range(rows + 1):
            s = lerp(CAVE[0], CAVE[1], row / rows)
            for column in range(columns + 1):
                angle = math.pi * (1.0 - column / columns)
                rough = lumps(row, column, lump) if 0 < column < columns else 0.0
                x, y = road.point(s, math.cos(angle) * (half + rough))
                built.add_vertex((x, y, base - sink + math.sin(angle) * (high + rough)), (0.0, 0.0))
    width = columns + 1
    outer = (rows + 1) * width
    for row in range(rows):
        for column in range(columns):
            a = row * width + column
            b = a + 1
            c = a + width
            d = c + 1
            built.triangles += [(a, b, c), (b, d, c)]  # The tunnel's surface faces inward.
            built.triangles += [(outer + a, outer + c, outer + b), (outer + b, outer + c, outer + d)]
    for column in range(columns):
        for row, facing_ahead in ((0, False), (rows, True)):
            i = row * width + column
            i2 = i + 1
            o = outer + i
            o2 = o + 1
            if facing_ahead:
                built.triangles += [(i, i2, o), (i2, o2, o)]
            else:
                built.triangles += [(i, o, i2), (i2, o, o2)]
    built.smooth_normals()
    return import_generated_mesh("SM_LS_CaveShell", built, solid=True)


def import_world_meshes():
    return {"tree": import_generated_mesh("SM_LS_GnarledTree", ls_generate_world_meshes.build_gnarled_tree()),
            "note": import_generated_mesh("SM_LS_MusicNote", ls_generate_world_meshes.build_music_note(), nanite=False),
            "ring": import_generated_mesh("SM_LS_GateRing", ls_generate_world_meshes.build_gate_ring()),
            "log": import_generated_mesh("SM_LS_Log", ls_generate_world_meshes.build_log()),
            "root_arch": import_generated_mesh("SM_LS_RootArch", ls_generate_world_meshes.build_root_arch()),
            "island": import_generated_mesh("SM_LS_FloatingIsland", ls_generate_world_meshes.build_floating_island())}


# --- Materials ---

def build_terrain_material(name, grass_tint):
    terrain_folder = "/Game/Stylized_PBR_Nature/Terrain"
    material = fresh_material(name)
    uv = node(material, unreal.MaterialExpressionTextureCoordinate)
    path = mask(material, uv, True)
    # V is written as 1 - steepness in the OBJ file, and comes back through the importer's flip as plain steepness.
    steep = mask(material, uv, False)
    grass = combine(material, unreal.MaterialExpressionMultiply, texture(material, terrain_folder + "/T_Grass_2", world_uv(material, 500.0)), colour(material, *grass_tint))
    dirt = combine(material, unreal.MaterialExpressionMultiply, texture(material, terrain_folder + "/T_Dirt", world_uv(material, 420.0)), colour(material, 1.8, 1.6, 1.35))
    rock = combine(material, unreal.MaterialExpressionMultiply, texture(material, terrain_folder + "/T_rock", world_uv(material, 900.0)), colour(material, 0.42, 0.4, 0.38))
    base = blend(material, blend(material, grass, dirt, path), rock, steep)
    output(material, base, unreal.MaterialProperty.MP_BASE_COLOR)
    output(material, number(material, 0.92), unreal.MaterialProperty.MP_ROUGHNESS)
    return finish(material)


def build_materials():
    terrain_folder = "/Game/Stylized_PBR_Nature/Terrain"
    materials = {"terrain": build_terrain_material("M_LS_Terrain", (0.62, 0.52, 0.34)),
                 "living": build_terrain_material("M_LS_TerrainLiving", (0.75, 1.0, 0.35))}

    material = fresh_material("M_LS_Rock")
    # Three flat projections blended by the surface direction would be sharper, but this cube only shows rough stone.
    world_rock = texture(material, terrain_folder + "/T_rock", world_uv(material, 400.0))
    output(material, combine(material, unreal.MaterialExpressionMultiply, world_rock, colour(material, 0.75, 0.7, 0.65)), unreal.MaterialProperty.MP_BASE_COLOR)
    output(material, number(material, 0.9), unreal.MaterialProperty.MP_ROUGHNESS)
    materials["rock"] = finish(material)

    material = fresh_material("M_LS_MossRock")
    # Moss grows where a surface faces up, so every rock gets it in the right place, whatever its shape or rotation.
    facing = node(material, unreal.MaterialExpressionVertexNormalWS)
    up = node(material, unreal.MaterialExpressionComponentMask, r=False, g=False, b=True, a=False)
    ls_material_helpers.library.connect_material_expressions(facing, "", up, "")
    moss_amount = node(material, unreal.MaterialExpressionSaturate)
    ls_material_helpers.library.connect_material_expressions(
        combine(material, unreal.MaterialExpressionMultiply, combine(material, unreal.MaterialExpressionSubtract, up, number(material, 0.35)), number(material, 3.0)), "", moss_amount, "")
    stone = combine(material, unreal.MaterialExpressionMultiply, texture(material, terrain_folder + "/T_rock", world_uv(material, 300.0)), colour(material, 0.55, 0.5, 0.45))
    moss = combine(material, unreal.MaterialExpressionMultiply, texture(material, terrain_folder + "/T_Grass_2", world_uv(material, 180.0)), colour(material, 0.55, 0.8, 0.22))
    output(material, blend(material, stone, moss, moss_amount), unreal.MaterialProperty.MP_BASE_COLOR)
    output(material, number(material, 0.95), unreal.MaterialProperty.MP_ROUGHNESS)
    materials["moss"] = finish(material)

    material = fresh_material("M_LS_Bark")
    uv = node(material, unreal.MaterialExpressionTextureCoordinate)
    bark = "/Game/StyleHex_Studio/Free_Packs/FREE_Stylized_Forest_Sample/Textures/Trees/T_Tree_Trunk_Broadleaf_"
    output(material, combine(material, unreal.MaterialExpressionMultiply, texture(material, bark + "BC", uv), colour(material, 0.55, 0.5, 0.48)), unreal.MaterialProperty.MP_BASE_COLOR)
    normal_sample = node(material, unreal.MaterialExpressionTextureSample, texture=unreal.load_asset(bark + "N"), sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    ls_material_helpers.library.connect_material_expressions(uv, "", normal_sample, "UVs")
    output(material, normal_sample, unreal.MaterialProperty.MP_NORMAL)
    output(material, number(material, 0.9), unreal.MaterialProperty.MP_ROUGHNESS)
    materials["bark"] = finish(material)

    material = fresh_material("M_LS_Waterfall")
    material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    material.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property("two_sided", True)
    # A stretched texture sliding downward reads as falling streaks, for less than a particle effect would cost.
    streak_uv = combine(material, unreal.MaterialExpressionMultiply, node(material, unreal.MaterialExpressionTextureCoordinate),
                        node(material, unreal.MaterialExpressionConstant2Vector, r=3.0, g=0.5))
    panner = node(material, unreal.MaterialExpressionPanner, speed_x=0.0, speed_y=0.7)
    ls_material_helpers.library.connect_material_expressions(streak_uv, "", panner, "Coordinate")
    streaks = mask(material, texture(material, terrain_folder + "/T_Dirt", panner), True)
    output(material, combine(material, unreal.MaterialExpressionMultiply, streaks, colour(material, 1.6, 1.7, 1.8)), unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    output(material, combine(material, unreal.MaterialExpressionMultiply, streaks, number(material, 0.9)), unreal.MaterialProperty.MP_OPACITY)
    materials["waterfall"] = finish(material)

    material = fresh_material("M_LS_CrackedRock")
    # Glowing cracks like the Stone Shell's own, which hints that Stone is what breaks this wall.
    position = node(material, unreal.MaterialExpressionWorldPosition)
    cracks = node(material, unreal.MaterialExpressionNoise, noise_function=unreal.NoiseFunction.NOISEFUNCTION_VORONOI_ALU, scale=0.02, levels=1, output_min=0.0, output_max=1.0, turbulence=False)
    ls_material_helpers.library.connect_material_expressions(position, "", cracks, "Position")
    shaped = combine(material, unreal.MaterialExpressionMultiply, combine(material, unreal.MaterialExpressionSubtract, cracks, number(material, 0.72)), number(material, 14.0))
    limit = node(material, unreal.MaterialExpressionSaturate)
    ls_material_helpers.library.connect_material_expressions(shaped, "", limit, "")
    output(material, combine(material, unreal.MaterialExpressionMultiply, texture(material, terrain_folder + "/T_rock", world_uv(material, 160.0)), colour(material, 0.2, 0.18, 0.16)), unreal.MaterialProperty.MP_BASE_COLOR)
    output(material, combine(material, unreal.MaterialExpressionMultiply, limit, colour(material, 4.0, 1.8, 0.35)), unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    materials["cracked"] = finish(material)

    def glow(name, r, g, b, strength):
        glow_material = fresh_material(name)
        base_colour = colour(glow_material, r, g, b)
        output(glow_material, base_colour, unreal.MaterialProperty.MP_BASE_COLOR)
        output(glow_material, combine(glow_material, unreal.MaterialExpressionMultiply, base_colour, number(glow_material, strength)), unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        return finish(glow_material)

    # Strong emissive values burn out to white, so these stay low to keep their colour.
    materials["guide"] = glow("M_LS_GuideGlow", 1.0, 0.42, 0.06, 0.9)
    materials["teal"] = glow("M_LS_GuideTeal", 0.1, 0.9, 0.8, 1.6)

    material = fresh_material("M_LS_Plate")
    # Gold rings around the plate's centre, cut from the distance to the middle of its top face.
    uv = node(material, unreal.MaterialExpressionTextureCoordinate)
    offset = combine(material, unreal.MaterialExpressionSubtract, uv, node(material, unreal.MaterialExpressionConstant2Vector, r=0.5, g=0.5))
    radius = node(material, unreal.MaterialExpressionLength)
    ls_material_helpers.library.connect_material_expressions(offset, "", radius, "")
    wave = node(material, unreal.MaterialExpressionSine, period=0.22)
    ls_material_helpers.library.connect_material_expressions(radius, "", wave, "")
    rings = node(material, unreal.MaterialExpressionSaturate)
    ls_material_helpers.library.connect_material_expressions(combine(material, unreal.MaterialExpressionMultiply, combine(material, unreal.MaterialExpressionSubtract, wave, number(material, 0.55)), number(material, 6.0)), "", rings, "")
    output(material, combine(material, unreal.MaterialExpressionMultiply, texture(material, terrain_folder + "/T_rock", world_uv(material, 200.0)), colour(material, 0.5, 0.48, 0.44)), unreal.MaterialProperty.MP_BASE_COLOR)
    output(material, combine(material, unreal.MaterialExpressionMultiply, rings, colour(material, 3.0, 1.7, 0.4)), unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    materials["plate"] = finish(material)

    material = fresh_material("M_LS_Planks")
    # Boards from the cube's own UVs, so the texture rises with the door. Dark gaps come from where each board starts and ends.
    boards = combine(material, unreal.MaterialExpressionMultiply, node(material, unreal.MaterialExpressionTextureCoordinate),
                     node(material, unreal.MaterialExpressionConstant2Vector, r=10.0, g=1.0))
    fraction = node(material, unreal.MaterialExpressionFrac)
    ls_material_helpers.library.connect_material_expressions(boards, "", fraction, "")
    across = mask(material, fraction, True)
    left_gap = node(material, unreal.MaterialExpressionSaturate)
    ls_material_helpers.library.connect_material_expressions(combine(material, unreal.MaterialExpressionMultiply, combine(material, unreal.MaterialExpressionSubtract, across, number(material, 0.05)), number(material, 25.0)), "", left_gap, "")
    right_gap = node(material, unreal.MaterialExpressionSaturate)
    ls_material_helpers.library.connect_material_expressions(combine(material, unreal.MaterialExpressionMultiply, combine(material, unreal.MaterialExpressionSubtract, number(material, 0.95), across), number(material, 25.0)), "", right_gap, "")
    wood = texture(material, "/Game/StyleHex_Studio/Free_Packs/FREE_Stylized_Forest_Sample/Textures/Trees/T_Tree_Trunk_Broadleaf_BC", boards)
    tinted = combine(material, unreal.MaterialExpressionMultiply, wood, colour(material, 0.8, 0.6, 0.42))
    output(material, combine(material, unreal.MaterialExpressionMultiply, tinted, combine(material, unreal.MaterialExpressionMultiply, left_gap, right_gap)), unreal.MaterialProperty.MP_BASE_COLOR)
    output(material, number(material, 0.85), unreal.MaterialProperty.MP_ROUGHNESS)
    materials["planks"] = finish(material)
    materials["pad"] = glow("M_LS_LilyPad", 0.16, 0.34, 0.1, 0.05)
    materials["thorn"] = glow("M_LS_Thorn", 0.5, 0.03, 0.05, 0.6)
    materials["blob"] = glow("M_LS_Blob", 0.02, 0.01, 0.03, 0.0)
    materials["note"] = glow("M_LS_Note", 1.0, 0.62, 0.1, 2.0)
    materials["petal"] = glow("M_LS_Petal", 1.0, 0.25, 0.4, 1.3)
    materials["shrine"] = glow("M_LS_Shrine", 0.3, 0.75, 1.0, 1.2)
    materials["gate_glow"] = glow("M_LS_GateGlow", 0.15, 0.95, 0.85, 6.0)
    return materials


# --- Moving the greybox onto the road ---

def origin_of(actor):
    """The actor's place in the straight greybox. The first run saves it in a tag, because later runs find the actor already moved."""
    for tag in actor.tags:
        text = str(tag)
        if text.startswith(ORIGIN_TAG):
            return [float(value) for value in text.split("|")[1:]]
    location = actor.get_actor_location()
    rotation = actor.get_actor_rotation()
    scale = actor.get_actor_scale3d()
    values = [location.x, location.y, location.z, rotation.yaw, rotation.pitch, scale.x, scale.y, scale.z]
    actor.tags = list(actor.tags) + ["{}|{}".format(ORIGIN_TAG, "|".join("{:.3f}".format(value) for value in values))]
    return values


def place_on_road(actor, s, d, z, yaw=0.0, pitch=0.0):
    x, y = road.point(s, d)
    actor.set_actor_location(unreal.Vector(x, y, z), False, False)
    actor.set_actor_rotation(unreal.Rotator(0.0, pitch, yaw + road.yaw(s)), False)


def bend_greybox():
    """Moves every greybox actor from the straight line onto the road, and turns off the cubes the road mesh replaces."""
    for actor in greybox_actors():
        label = actor.get_actor_label()
        if label in STAYS_PUT:
            continue
        x, y, z, yaw, pitch, scale_x, scale_y, scale_z = origin_of(actor)
        is_cube = isinstance(actor, unreal.StaticMeshActor)
        if is_cube and label in REPLACED_BY_ROAD or (label == "Ramp" and scale_y * 50.0 > LANE - 1.0):
            actor.static_mesh_component.set_collision_profile_name("NoCollision")
            continue
        if label in MARSH_PARTS:
            # Stretched, not only moved. The basin has room for three more lily pads now.
            s = (MARSH[0] + MARSH[1]) / 2.0
            stretch = (MARSH[1] - MARSH[0]) / (MARSH_GREYBOX[1] - MARSH_GREYBOX[0])
            actor.set_actor_scale3d(unreal.Vector(scale_x * stretch, scale_y, scale_z))
        elif label == "Ramp":
            # The way out of the marsh, as wide as the road and half as steep. A floating ball couldn't climb the greybox's narrow 21 degree one.
            run, rise = 1800.0, WATER_LEVEL - MARSH_BED
            length = math.hypot(run, rise)
            pitch = math.degrees(math.atan2(rise, run))
            s = MARSH[1] - run / 2.0
            half_thick = scale_z * 50.0
            z = (MARSH_BED + WATER_LEVEL) / 2.0 + half_thick - half_thick / math.cos(math.radians(pitch)) - hills(s)
            actor.set_actor_scale3d(unreal.Vector(length / 100.0, LANE * 2.0 / 100.0, scale_z))
        elif abs(x - 16800.0) < 1.0:
            s = to_road(x) + THORN_SHIFT
        elif label == "Ledge" or (actor.get_class().get_name() == "BP_LifeNote_C" and abs(x - 5900.0) < 1.0):
            s = to_road(x) + LEDGE_SHIFT
        else:
            s = to_road(x)
        place_on_road(actor, s, y, z + hills(s), yaw, pitch)
    # The level's big safety net has to cover the whole bent road.
    for actor in greybox_actors():
        if actor.get_actor_label() == "KillVolume":
            actor.set_actor_location(unreal.Vector(18000.0, 6000.0, -1500.0), False, False)
            actor.set_actor_scale3d(unreal.Vector(150.0, 150.0, 1.0))


def actors_of(class_name):
    return [actor for actor in greybox_actors() if actor.get_class().get_name() == class_name]


def find_by_origin(class_name, x, y):
    for actor in actors_of(class_name):
        origin = origin_of(actor)
        if abs(origin[0] - x) < 1.0 and abs(origin[1] - y) < 1.0:
            return actor
    raise RuntimeError("Last Seed world: no {} at {}, {}".format(class_name, x, y))


def clone(source, label, s, d, z, folder="Added Challenges", yaw=0.0):
    x, y = road.point(s, d)
    return spawn(source.get_class(), x, y, z, label, folder, yaw + road.yaw(s))


def block_physical_material():
    """Stone Shell's grip is so strong that pushing a block also presses it into the ground, which jams it. This lets it slide.
    Stone's spin can only drive about 16000 of push, and 0.12 needs about 7500, which leaves enough to get a block moving at a fair pace.
    Seed can push it too, which is fine, as only Stone or a block is heavy enough to hold a plate down."""
    path = "/Game/LastSeed/Physics/PM_Block"
    physical = unreal.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "PM_Block", "/Game/LastSeed/Physics", unreal.PhysicalMaterial, unreal.PhysicalMaterialFactoryNew())
    physical.set_editor_property("friction", 0.12)
    physical.set_editor_property("override_friction_combine_mode", True)
    physical.set_editor_property("friction_combine_mode", unreal.FrictionCombineMode.MIN)
    unreal.EditorAssetLibrary.save_loaded_asset(physical, False)
    return physical


def add_challenges():
    """The new gameplay that brings the level to about 4:45. Every piece is an existing gameplay class."""
    # 1-1: the note that sat beside the road now rewards the island jumps.
    note = find_by_origin("BP_LifeNote_C", 5000.0, 400.0)
    place_on_road(note, ISLANDS[1][0], ISLANDS[1][1], hills(ISLANDS[1][0]) + ISLANDS[1][2] + 80.0)

    # 1-2: the gate now needs a second plate. It is 1200 cm from the gate, and Stone covers about 1100 in the 3 seconds
    # a gate stays open, so holding it and racing through doesn't work. A block has to be pushed onto it.
    plate_a = actors_of("PressurePlate")[0]
    block_a = actors_of("PushableBlock")[0]
    z = hills(17000.0) + 300.0
    plate_b = clone(plate_a, "PressurePlate", 18000.0, 0.0, z - 10.0)
    plate_b.get_component_by_class(unreal.StaticMeshComponent).set_material(0, plate_a.get_component_by_class(unreal.StaticMeshComponent).get_material(0))
    block_b = clone(block_a, "PushableBlock", 17050.0, 0.0, z + 60.0)
    block_b.set_editor_property("mass_kg", 52.0)
    slippery = block_physical_material()
    for block in (block_a, block_b):
        component = block.get_component_by_class(unreal.StaticMeshComponent)
        component.set_phys_material_override(slippery)
        # A block that could turn would wedge itself across a chute.
        body = component.get_editor_property("body_instance")
        body.set_editor_property("lock_z_rotation", True)
        component.set_editor_property("body_instance", body)
    actors_of("Gate")[0].set_editor_property("required_plates", [plate_a, plate_b])

    # 1-2: a third thorn patch, which makes the clear lane wind once more.
    thorns = actors_of("HazardVolume")[0]
    third = clone(thorns, "Thorns", 22400.0, -200.0, hills(22400.0) + 350.0)
    third.set_actor_scale3d(thorns.get_actor_scale3d())

    # 1-3: three more lily pads and a third blob.
    pad = actors_of("SinkingPad")[0]
    for s, d in ((27400.0, -250.0), (27900.0, 250.0), (28400.0, 0.0)):
        clone(pad, "SinkingPad", s, d, 300.0)
    blob_source = actors_of("WitherBlob")[0]
    blob = clone(blob_source, "WitherBlob", 31800.0, -300.0, hills(31800.0) + 370.0)
    blob.set_editor_property("patrol_points", [unreal.Vector(0.0, 0.0, 0.0), unreal.Vector(0.0, 600.0, 0.0)])

    return [note, plate_b, block_b, third, blob]


def build_island_chain(materials):
    """Picture 1's floating rocks, playable. A hidden cylinder is the smooth floor, and the rock is only what you see."""
    for s, d, height in ISLANDS:
        x, y = road.point(s, d)
        top = hills(s) + height
        solid = spawn(unreal.StaticMeshActor, x, y, top - 100.0, "IslandFloor", "Floating Islands")
        solid.set_actor_scale3d(unreal.Vector(ISLAND_RADIUS / 50.0, ISLAND_RADIUS / 50.0, 2.0))
        solid.static_mesh_component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Cylinder"))
        solid.static_mesh_component.set_collision_profile_name("BlockAll")
        hide_component(solid.static_mesh_component)
        size = ISLAND_RADIUS / 100.0 * 1.04
        mesh_actor(WORLD_MESHES["island"], x, y, top, "Floating Islands", (size, size, size * 1.5), s, material=materials["moss"], label="FloatingIsland")
    kill_x, kill_y = road.point(7690.0)
    kill_volume(kill_x, kill_y, -750.0, 1400.0, 1000.0, yaw=road.yaw(7690.0))


# --- Dressing what the greybox left ---

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


def dress_actor(actor, materials, thorns, rng):
    class_name = actor.get_class().get_name()
    label = actor.get_actor_label()
    if isinstance(actor, unreal.StaticMeshActor):
        if label in REPLACED_BY_ROAD or label in ("MarshBed", "MarshWall", "WaterSurface") or (label == "Ramp" and actor.get_actor_scale3d().y * 50.0 > LANE - 1.0):
            hide_component(actor.static_mesh_component)
        elif label == "Ledge":
            actor.static_mesh_component.set_material(0, materials["moss"])
        elif label in ("SecretLedge", "Ramp"):
            actor.static_mesh_component.set_material(0, materials["rock"])
    elif class_name == "CrackedWall":
        # Still the wall that breaks, but hidden. The rock pile in front of it is what the player sees. See build_cave.
        hide_component(actor.get_component_by_class(unreal.StaticMeshComponent))
    elif class_name == "Gate":
        actor.get_component_by_class(unreal.StaticMeshComponent).set_material(0, materials["planks"])
    elif class_name == "PushableBlock":
        actor.get_component_by_class(unreal.StaticMeshComponent).set_material(0, materials["planks"])
    elif class_name == "PressurePlate":
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        component.set_material(0, materials["plate"])
        # Flush with the road it would flicker, as both surfaces fight to be drawn. This small lip is too low for a ball to notice.
        component.set_relative_location(unreal.Vector(0.0, 0.0, 3.0), False, False)
    elif class_name == "SinkingPad":
        # A cylinder has simple collision like the cube's, and its round shape reads as a lily pad.
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Cylinder"))
        component.set_material(0, materials["pad"])
    elif class_name == "WitherBlob":
        actor.get_component_by_class(unreal.StaticMeshComponent).set_material(0, materials["blob"])
    elif class_name == "BP_LifeNote_C":
        component = keep_coloured(actor, None)
        component.set_static_mesh(unreal.load_asset(WORLD_MESHES["note"]))
        component.set_relative_scale3d(unreal.Vector(1.0, 1.0, 1.0))
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
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        hide_component(component)
        # Measured from the mesh, as a rotated actor's world bounds are larger than its real shape.
        extent = component.static_mesh.get_bounds().box_extent
        scale = component.get_world_scale()
        half_x, half_y = extent.x * scale.x, extent.y * scale.y
        location = actor.get_actor_location()
        heading = math.radians(actor.get_actor_rotation().yaw)
        for along, side in jittered_grid(-half_x + 60, half_x, -half_y + 60, half_y, 130.0, rng):
            x = location.x + along * math.cos(heading) - side * math.sin(heading)
            y = location.y + along * math.sin(heading) + side * math.cos(heading)
            thorns.add(mesh("SM_Generic_Shrub_01_dead"), x, y, location.z - extent.z * scale.z, rng.uniform(0.7, 1.15), rng)
    elif class_name == "RestorableActor":
        # Regrowth rests on the new ground. On the inside of a tight bend its old spot could land on the road, so it swaps sides.
        location = actor.get_actor_location()
        s, d = road.project(location.x, location.y)
        if outside_distance(s, d) < 300.0:
            x, y, *_ = origin_of(actor)
            location.x, location.y = road.point(to_road(x), -y)
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        if component.static_mesh:
            location.z = terrain_height(location.x, location.y) - base_height_offset(component.static_mesh, actor.get_actor_scale3d().z)
            actor.set_actor_location(location, False, False)


def dress_greybox(materials, added):
    rng = random.Random(SEED + 1)
    thorns = Scatter("Thorns", 0, 0, material=materials["thorn"], stencil=True)
    for actor in greybox_actors() + added:
        dress_actor(actor, materials, thorns, rng)
    thorns.build()

    # The cube is still the wall that breaks. Its hint now talks about what the player can see.
    for actor in actors_of("TutorialTrigger"):
        if "cracked wall" in str(actor.get_editor_property("message")):
            actor.set_editor_property("message", unreal.Text("Rocks block the way. Roll into them as Stone Shell. Press 2 first."))


# --- Scenery rings ---

def zone_at(s):
    for name, s0, s1 in ZONES:
        if s < s1:
            return name
    return ZONES[-1][0]


# What grows where. Each zone has its own feel using the same packs.
PALETTES = {
    "1_1": {"trees": ["SM_Pine_Tree_03_dead", "SM_Pine_Tree_03_dead", "SM_Fruit_Tree_01_dead", "SM_Pine_Tree_03_dead_cut"],
            "rocks": ["SM_R_Rock_01", "SM_R_Rock_02", "SM_S_Rock_01", "SM_S_Rock_11"],
            "edge": ["SM_Generic_Shrub_01_dead", "SM_Generic_Shrub_01_dead", "SM_Pine_Tree_03_stump", "SM_Fruit_Tree_01_logs", "SM_Fruit_Tree_01_stump"],
            "under": ["SM_Fol_Grass_Clump_1", "SM_Fern", "SM_Generic_Shrub_01_dead"]},
    "1_2": {"trees": ["SM_Pine_Tree_03_dead_cut", "SM_Fruit_Tree_01_dead_cut", "SM_Pine_Tree_03_dead", "SM_Fruit_Tree_01_dead"],
            "rocks": ["SM_S_Rock_02", "SM_R_Rock_03"],
            "edge": ["SM_Pine_Tree_03_logs", "SM_Fruit_Tree_01_logs", "SM_Pine_Tree_03_stump", "SM_Fruit_Tree_01_stump"],
            "under": ["SM_Fern", "SM_Clover", "SM_Generic_Shrub_01_dead"]},
    "1_3": {"trees": ["SM_Fruit_Tree_01_dead", "SM_Fruit_Tree_01_dead", "SM_Pine_Tree_03_dead", "SM_Fruit_Tree_01_dead_cut"],
            "rocks": ["SM_River_Rock_Pile_02", "SM_R_Rock_04"],
            "edge": ["SM_Generic_Shrub_01_dead", "SM_Fruit_Tree_01_logs", "SM_Pine_Tree_03_logs"],
            "under": ["SM_Fern", "SM_Fern", "SM_Clover", "SM_Fol_Grass_Clump_1"]},
}
LIVING_PLANTS = ["SM_Fol_Grass_Clump_1", "SM_Fol_Grass_Clump_2", "SM_Fol_Grass_Clump_3", "SM_Fol_Grass_Clump_4", "SM_Fol_Grass_Clump_5", "SM_Grass_02", "SM_Clover"]
LIVING_FLOWERS = ["SM_Fol_Flower_Clump_1", "SM_Fol_Flower_Clump_2", "SM_Fol_Flower_Clump_3", "SM_Fol_Flower_Clump_4", "SM_Poppy_02"]


def usable(x, y, distance_range, margin=120.0):
    """False on the walkable area, over water and in the chasms. Everything left is safe to fill."""
    s, d = road.project(x, y)
    if not distance_range[0] <= outside_distance(s, d) < distance_range[1] or in_pocket(x, y, margin):
        return False
    near_s = min(max(s, 0.0), ROAD_LENGTH)
    if gap_amount(near_s) > 0.0 and abs(d) < 1500.0:
        return False
    if marsh_amount(near_s) > 0.0 and terrain_height(x, y) < WATER_LEVEL + 5.0:
        return False
    if pool_amount(near_s, d) > 0.3:
        return False
    tree_x, tree_y = road.point(*HEART_TREE)
    return math.hypot(x - tree_x, y - tree_y) > 1300.0


def along_road(s0, s1, d0, d1, spacing, rng):
    """World points in a band beside the road, given as distances from its centre."""
    for s, d in jittered_grid(s0, s1, d0, d1, spacing, rng):
        yield road.point(s, d) + (min(max(s, 0.0), ROAD_LENGTH),)


def scatter_rings(materials):
    rng = random.Random(SEED)

    # Boundary ring: rocks, logs and shrubs right beside the road, with a tight line of dead trees behind them.
    rocks = Scatter("Ring1_MossRocks", 9000, 12000, material=materials["moss"])
    edge = Scatter("Ring1_Edge", 9000, 12000)
    trees_near = Scatter("Ring1_Trees", 16000, 22000)
    under = Scatter("Ring1_Undergrowth", 5000, 7000, shadows=False)
    for side in (-1, 1):
        d0, d1 = (EDGE + 60.0, EDGE + 500.0) if side > 0 else (-EDGE - 500.0, -EDGE - 60.0)
        for x, y, s in along_road(-400, ROAD_LENGTH + 400, d0, d1, 210.0, rng):
            if usable(x, y, (40.0, 900.0)):
                palette = PALETTES[zone_at(s)]
                # Pack rocks are 3 to 6 m tall, which would tower over a 1 m ball right beside the road.
                if rng.random() < 0.3:
                    rocks.add(mesh(rng.choice(palette["rocks"])), x, y, terrain_height(x, y), rng.uniform(0.2, 0.5), rng, tilt=4.0)
                else:
                    edge.add(mesh(rng.choice(palette["edge"])), x, y, terrain_height(x, y), rng.uniform(0.7, 1.3), rng, tilt=4.0)
        d0, d1 = (EDGE + 350.0, EDGE + 1300.0) if side > 0 else (-EDGE - 1300.0, -EDGE - 350.0)
        for x, y, s in along_road(-800, ROAD_LENGTH + 800, d0, d1, 400.0, rng):
            if usable(x, y, (300.0, 1500.0)):
                trees_near.add(mesh(rng.choice(PALETTES[zone_at(s)]["trees"])), x, y, terrain_height(x, y), rng.uniform(0.9, 1.7), rng, sink=20.0, tilt=3.0)
        d0, d1 = (EDGE + 40.0, EDGE + 1400.0) if side > 0 else (-EDGE - 1400.0, -EDGE - 40.0)
        for x, y, s in along_road(-400, ROAD_LENGTH + 400, d0, d1, 170.0, rng):
            if usable(x, y, (20.0, 1500.0)):
                under.add(mesh(rng.choice(PALETTES[zone_at(s)]["under"])), x, y, terrain_height(x, y), rng.uniform(0.7, 1.3), rng)
    # The two ends of the road need closing off too.
    for x, y, s in along_road(-1500, -100, -2000, 2000, 300.0, rng):
        trees_near.add(mesh(rng.choice(PALETTES["1_1"]["trees"])), x, y, terrain_height(x, y), rng.uniform(1.0, 1.7), rng, sink=20.0)
    for x, y, s in along_road(ROAD_LENGTH + 300, ROAD_LENGTH + 1800, -2000, 2000, 300.0, rng):
        trees_near.add(mesh(rng.choice(PALETTES["1_3"]["trees"])), x, y, terrain_height(x, y), rng.uniform(1.0, 1.7), rng, sink=20.0)

    # Middle ring: forest in depth, with large rocks breaking it up. It covers a box around the bent road.
    x0, x1, y0, y1 = min(road.xs), max(road.xs), min(road.ys), max(road.ys)
    middle = Scatter("Ring2_Middle", 26000, 36000)
    for x, y in jittered_grid(x0 - 6000, x1 + 6000, y0 - 6500, y1 + 6500, 750.0, rng):
        if usable(x, y, (1500.0, 6000.0)):
            s = road.project(x, y)[0]
            kind = rng.random()
            if kind < 0.72:
                middle.add(mesh(rng.choice(PALETTES[zone_at(s)]["trees"])), x, y, terrain_height(x, y), rng.uniform(1.2, 2.0), rng, sink=20.0, tilt=3.0)
            elif kind < 0.9:
                middle.add(mesh(rng.choice(["SM_S_Rock_09", "SM_S_Rock_04", "SM_RockPack_RockGroups_01_A", "SM_R_Rock_05"])), x, y, terrain_height(x, y), rng.uniform(0.6, 1.3), rng, sink=30.0)
            else:
                middle.add(mesh(rng.choice(["SM_Bush", "SM_Fol_Bush_2"])), x, y, terrain_height(x, y), rng.uniform(1.2, 2.2), rng)

    # Far ring: big living trees, which the withering post-process turns grey. They regain their green as the world
    # recovers, which shows the player how far the restoration reaches.
    far = Scatter("Ring3_Far", 110000, 150000, shadows=False)
    far_trees = ["SM_Common_Tree_{:02d}".format(number_) for number_ in range(1, 12)]
    for x, y in jittered_grid(x0 - 30000, x1 + 30000, y0 - 38000, y1 + 38000, 2500.0, rng):
        if usable(x, y, (6000.0, 42000.0)):
            far.add(mesh(rng.choice(far_trees)), x, y, terrain_height(x, y), rng.uniform(2.2, 3.4), rng, sink=30.0)

    for scatter in (rocks, edge, trees_near, under, middle, far):
        scatter.build()


def living_start():
    """Picture 1's foreground: grass and flowers that stay in colour, thinning out as the road leaves the start."""
    rng = random.Random(SEED + 4)
    plants = Scatter("Living_Grass", 5000, 7000, shadows=False, stencil=True)
    flowers = Scatter("Living_Flowers", 5000, 7000, shadows=False, stencil=True)
    for side in (-1, 1):
        d0, d1 = (LANE - 260.0, ROAD_SIDE + 500.0) if side > 0 else (-ROAD_SIDE - 500.0, -LANE + 260.0)
        for x, y, s in along_road(0, 6490, d0, d1, 62.0, rng):
            if gap_amount(s) > 0.0 or rng.random() > 1.0 - smoothstep(2500.0, 6490.0, s) * 0.85:
                continue
            ground_s, ground_d = road.project(x, y)
            ground = road_height(ground_s, ground_d, x, y) if abs(ground_d) < ROAD_SIDE and has_road(ground_s) else terrain_height(x, y)
            if rng.random() < 0.2:
                flowers.add(mesh(rng.choice(LIVING_FLOWERS)), x, y, ground, rng.uniform(0.6, 1.1), rng, sink=2.0)
            else:
                plants.add(mesh(rng.choice(LIVING_PLANTS)), x, y, ground, rng.uniform(0.9, 1.5), rng, sink=2.0)
    plants.build()
    flowers.build()


def rest_on_ground(mesh_path, s, d, sink, folder, scale, yaw=0.0, material=None, label=None, pitch=0.0):
    """Places a mesh with its base on the terrain, at a spot given along the road."""
    x, y = road.point(s, d)
    loaded = unreal.load_asset(mesh_path)
    return mesh_actor(mesh_path, x, y, terrain_height(x, y) - sink - base_height_offset(loaded, scale), folder, (scale, scale, scale), yaw, material, label, pitch)


def awakening_grove_landmarks(materials):
    """Zone 1-1, built to match its concept picture: dead giant, waterfalls, fallen log, floating rocks and a glowing gate ahead."""
    folder = "Zone 1-1"
    rng = random.Random(SEED + 5)

    rest_on_ground(WORLD_MESHES["tree"], HEART_TREE[0], HEART_TREE[1], 30.0, folder, 1.0, 40.0, materials["bark"], "HeartTree")

    # Waterfalls down cliffs beneath the giant. A plane is flat, so it stands up by pitching it.
    for s, d, scale, high in ((3300.0, -3600.0, 1.3, 1100.0), (4500.0, -3300.0, 1.0, 800.0)):
        rest_on_ground(mesh("SM_RockPack_Cliff_07_B"), s, d, 80.0, folder, scale, road.yaw(s) + 90.0, label="WaterfallCliff")
        x, y = road.point(s, d + 260.0 * scale)
        fall = mesh_actor("/Engine/BasicShapes/Plane", x, y, terrain_height(x, y) + high / 2.0, folder, (high / 100.0, 2.4, 1.0), road.yaw(s) + 90.0,
                          materials["waterfall"], "Waterfall", pitch=90.0)
        fall.static_mesh_component.set_cast_shadow(False)

    # The great fallen trunk across the view to the right of the road.
    x, y = road.point(1900.0, 1000.0)
    mesh_actor(WORLD_MESHES["log"], x, y, terrain_height(x, y) + 90.0, folder, (2.2, 2.4, 2.4), road.yaw(1900.0) + 6.0, materials["bark"], "FallenTrunk", pitch=2.0)

    # Large mossy boulders close by, on the high side.
    for s, d, scale in ((700.0, -1250.0, 0.65), (2100.0, -1300.0, 0.8), (3100.0, -1150.0, 0.5), (4700.0, -1350.0, 0.7)):
        rest_on_ground(mesh("SM_R_Rock_02"), s, d, 40.0, folder, scale, rng.uniform(0, 360), materials["moss"], "MossBoulder")

    # More floating rocks to the side, purely scenery, which make the playable ones feel part of the place.
    for s, d, height, scale in ((8000.0, 2600.0, 400.0, 3.5), (9000.0, 3400.0, 650.0, 4.5), (7000.0, 3300.0, 150.0, 2.5), (10000.0, 2500.0, 900.0, 3.0)):
        x, y = road.point(s, d)
        mesh_actor(WORLD_MESHES["island"], x, y, hills(s) + height, folder, (scale, scale, scale * 1.4), rng.uniform(0, 360), materials["moss"], "DistantIsland")

    # Stone stairs up the ramp, then the gate at its top. Fab has no ruins, so standing stones and a glowing ring stand in.
    stairs = build_stair_mesh(8900.0, 10400.0)
    mesh_actor(stairs, 0.0, 0.0, 0.0, folder, material=materials["rock"], label="Stairs")

    gate_s = 12120.0
    ground = level(gate_s)
    stone = mesh("SM_Menhir_Rock_02")
    loaded = unreal.load_asset(stone)
    for d, scale in ((-880.0, 5.2), (880.0, 5.2), (-1300.0, 3.6), (1300.0, 3.6), (-1700.0, 2.4), (1700.0, 2.4)):
        x, y = road.point(gate_s, d)
        mesh_actor(stone, x, y, ground - 20.0 - base_height_offset(loaded, scale), folder, (scale, scale, scale), road.yaw(gate_s) + rng.uniform(-15, 15), label="GateStone")
    x, y = road.point(gate_s)
    ring = mesh_actor(WORLD_MESHES["ring"], x, y, ground + 1000.0, folder, (1.6, 1.6, 1.6), road.yaw(gate_s), materials["gate_glow"], "GateRing")
    ring.static_mesh_component.set_render_custom_depth(True)
    ring.static_mesh_component.set_custom_depth_stencil_value(ls_world_common.FULL_COLOUR_STENCIL)
    niagara("/Game/FreeParticle_SoftTofu/Niagara/NS_Sparkling_Glow", x, y, ground + 1000.0, folder, 5.0)
    point_light(x, y, ground + 1000.0, unreal.LinearColor(0.2, 1.0, 0.9, 1.0), 120.0, 1800.0, folder)


def build_cave(materials):
    """The tunnel, then the rock pile blocking its mouth. The pile's glowing cracks hint that Stone is what breaks it."""
    folder = "Zone 1-2"
    rng = random.Random(SEED + 6)
    mesh_actor(build_cave_shell(), 0.0, 0.0, 0.0, folder, material=materials["moss"], label="CaveShell").static_mesh_component.set_collision_profile_name("BlockAll")

    # Cliffs around the mouth hide where the hill meets the land.
    for d, up, scale, yaw in ((-1650.0, -60.0, 1.5, 200.0), (1650.0, -60.0, 1.5, 20.0), (-900.0, 900.0, 1.2, 80.0), (900.0, 950.0, 1.1, 300.0)):
        path = mesh("SM_RockPack_Cliff_07_B")
        x, y = road.point(CAVE[0] - 60.0, d)
        mesh_actor(path, x, y, level(CAVE[0]) + up - base_height_offset(unreal.load_asset(path), scale), folder, (scale, scale, scale), yaw, label="CaveCliff")

    # Rough rocks around the arch, which hide the shell's flat front. Together they read as a cave mouth.
    cliff = mesh("SM_RockPack_Cliff_07_D")
    bounds = unreal.load_asset(cliff).get_bounds()
    for step in range(11):
        angle = math.pi * step / 10.0
        scale = rng.uniform(0.55, 0.8)
        x, y = road.point(CAVE[0] - 40.0, math.cos(angle) * 1120.0)
        z = level(CAVE[0]) + math.sin(angle) * 960.0 - bounds.origin.z * scale
        mesh_actor(cliff, x, y, z, folder, (scale, scale, scale), rng.uniform(0, 360), label="CaveMouthRock")

    # Rows of boulders that fill the arch, largest at the bottom. Nothing here is solid: the hidden wall behind them stops the ball.
    rubble = []
    ground = level(CAVE_WALL_S)
    names = ["SM_R_Rock_01", "SM_R_Rock_02", "SM_R_Rock_03", "SM_S_Rock_01"]
    # Pack rocks are 3 to 6 m tall, so these are small scales. Two layers leave no gaps to see through.
    rows = ((0.0, 700.0, 9, 0.6), (140.0, 660.0, 8, 0.55), (270.0, 560.0, 7, 0.5), (400.0, 400.0, 5, 0.45), (510.0, 220.0, 3, 0.4))
    for layer, up, half_width, count, scale in [(layer, *row) for layer in (0, 1) for row in rows]:
        for index in range(count):
            d = -half_width + 2.0 * half_width * index / (count - 1) + rng.uniform(-30.0, 30.0)
            s = CAVE_WALL_S + 60.0 + layer * 130.0 + rng.uniform(-20.0, 30.0)
            path = mesh(rng.choice(names))
            x, y = road.point(s, d)
            size = scale * rng.uniform(0.85, 1.1)
            rubble.append(mesh_actor(path, x, y, ground + up - 40.0 - base_height_offset(unreal.load_asset(path), size), folder, (size, size, size), rng.uniform(0, 360), materials["cracked"], "RockPile"))
    wall = actors_of("CrackedWall")[0]
    wall.set_editor_property("rubble_actors", rubble)
    # Boulders fly out, not cubes. This mesh has simple collision, which a physics body needs.
    wall.set_editor_property("debris_mesh", unreal.load_asset(mesh("SM_RockPack_Rock_04")))
    wall.set_editor_property("debris_scale", 1.1)
    wall.set_editor_property("debris_count", 16)

    x, y = road.point(CAVE_WALL_S - 300.0)
    point_light(x, y, ground + 350.0, unreal.LinearColor(1.0, 0.55, 0.2, 1.0), 12.0, 1000.0, folder)
    for s in (14800.0, 15150.0):
        x, y = road.point(s)
        point_light(x, y, ground + 420.0, unreal.LinearColor(0.15, 0.95, 0.85, 1.0), 12.0, 1000.0, folder)


def rootwood_hollow(materials):
    """Zone 1-2, built to match its concept picture: a dark hollow of roots, with a still pool to one side and teal light along the road."""
    folder = "Zone 1-2"
    rng = random.Random(SEED + 7)
    build_cave(materials)

    # Great roots arching over the road. They have no collision and clear the highest jump, so they are only scenery.
    arches = [(13200.0, -12.0, 1.0)]
    s = 15450.0
    while s < 23000.0:
        arches.append((s, rng.uniform(-16.0, 16.0), rng.uniform(0.95, 1.15)))
        s += rng.uniform(520.0, 780.0)
    for s, turn, scale in arches:
        x, y = road.point(s)
        mesh_actor(WORLD_MESHES["root_arch"], x, y, level(s) - 10.0, folder, (scale, scale, scale), road.yaw(s) + turn, materials["bark"], "RootArch")

    # Giant dead trees looming behind the walls.
    for s, d, scale, yaw in ((17500.0, -3000.0, 0.8, 120.0), (21000.0, 3100.0, 0.75, 250.0), (13600.0, -2700.0, 0.65, 10.0)):
        rest_on_ground(WORLD_MESHES["tree"], s, d, 30.0, folder, scale, yaw, materials["bark"], "HollowTree")

    # Rocks along the pool's edge, as in picture 2.
    rim = Scatter("Pool_Rim", 9000, 12000, material=materials["moss"])
    for x, y, s in along_road(POOL[0], POOL[1], 720.0, 900.0, 170.0, rng):
        rim.add(mesh(rng.choice(["SM_S_Rock_02", "SM_R_Rock_01", "SM_R_Rock_03"])), x, y, POOL_BED + 240.0, rng.uniform(0.16, 0.3), rng, tilt=8.0)
    rim.build()

    # The still pool, and waterfalls feeding it from the far bank.
    s = (POOL[0] + POOL[1]) / 2.0
    x, y = road.point(s, 2100.0)
    water = unreal.load_asset("/Game/Stylized_PBR_Nature/Terrain/M_Water_Basic")
    mesh_actor("/Engine/BasicShapes/Plane", x, y, POOL_WATER, folder, ((POOL[1] - POOL[0] + 400.0) / 100.0, 36.0, 1.0), road.yaw(s), water, "Pool")
    for s, d, high in ((16300.0, 3000.0, 900.0), (17900.0, 3050.0, 1100.0)):
        rest_on_ground(mesh("SM_RockPack_Cliff_07_B"), s, d + 350.0, 100.0, folder, 1.4, road.yaw(s), label="PoolCliff")
        x, y = road.point(s, d)
        fall = mesh_actor("/Engine/BasicShapes/Plane", x, y, POOL_WATER + high / 2.0, folder, (high / 100.0, 2.6, 1.0), road.yaw(s), materials["waterfall"], "Waterfall", pitch=90.0)
        fall.static_mesh_component.set_cast_shadow(False)

    # Picture 2's tilted log on a stump. It does nothing, as the game has no seesaw.
    rest_on_ground(mesh("SM_R_Rock_03"), 17100.0, 1700.0, 60.0, folder, 0.7, 40.0, materials["moss"], "LogRest")
    x, y = road.point(17100.0, 1700.0)
    mesh_actor(WORLD_MESHES["log"], x - 380.0, y + 150.0, POOL_WATER + 60.0, folder, (1.2, 1.2, 1.2), road.yaw(17100.0) + 30.0, materials["bark"], "TiltedLog", pitch=12.0)

    # Log chutes guide each block onto its plate and stop it just past. A block pushed against a wall could never be pulled back, which would
    # leave the gate shut for good. A chute is just wider than the ball, so the ball can't slip past the block, and its mouth flares to guide the ball in.
    def chute_log(s0, d0, s1, d1):
        x0, y0 = road.point(s0, d0)
        x1, y1 = road.point(s1, d1)
        top = level(s0)
        invisible_wall(x0, y0, x1, y1, top - 50.0, top + 120.0, folder)
        length = math.hypot(x1 - x0, y1 - y0)
        mesh_actor(WORLD_MESHES["log"], x0, y0, top + 28.0, folder, (length / 800.0, 0.75, 0.75), math.degrees(math.atan2(y1 - y0, x1 - x0)), materials["bark"], "ChuteLog")

    plate_s = to_road(13300.0)
    for side in (-1.0, 1.0):
        chute_log(plate_s + side * 150.0, 430.0, plate_s + side * 150.0, -430.0)
        chute_log(plate_s + side * 340.0, 610.0, plate_s + side * 150.0, 430.0)
        chute_log(16930.0, side * 150.0, 18130.0, side * 150.0)
        chute_log(16720.0, side * 340.0, 16930.0, side * 150.0)
    chute_log(plate_s - 150.0, -430.0, plate_s + 150.0, -430.0)
    chute_log(18130.0, -150.0, 18130.0, 150.0)

    # A frame of logs around the plank gate.
    s = to_road(14800.0)
    for side in (-1, 1):
        x, y = road.point(s, side * 730.0)
        mesh_actor(WORLD_MESHES["log"], x, y, level(s) - 40.0, folder, (1.5, 1.5, 1.2), rng.uniform(0, 360), materials["bark"], "GatePost", pitch=90.0)
    x, y = road.point(s, -900.0)
    mesh_actor(WORLD_MESHES["log"], x, y, level(s) + 660.0, folder, (2.3, 1.4, 1.4), road.yaw(s) + 90.0, materials["bark"], "GateLintel")

    # Dark inside, with a slight teal cast. Three boxes, because a box can't bend with the road.
    for s0, s1 in ((14300.0, 19700.0), (19500.0, 21000.0), (20800.0, 23200.0)):
        middle = (s0 + s1) / 2.0
        x, y = road.point(middle)
        zone_grade(x, y, level(middle) + 800.0, (s1 - s0) / 2.0 + 200.0, 2000.0, 2000.0, road.yaw(middle), -1.5, unreal.LinearColor(0.72, 0.9, 0.92, 1.0), "HollowGrade")


def rock_set_pieces():
    """Cliffs where the player should feel enclosed, and at each edge the eye is drawn to."""
    folder = "Set Pieces"

    def rock(name, s, d, height_offset, scale, yaw=0.0):
        path = mesh(name)
        loaded = unreal.load_asset(path)
        x, y = road.point(s, d)
        return mesh_actor(path, x, y, terrain_height(x, y) + height_offset - base_height_offset(loaded, scale), folder, (scale, scale, scale), yaw)

    # Rootwood Hollow: high walls either side of the whole zone, so it feels like a canyon among old roots.
    rng = random.Random(SEED + 2)
    s = 13000.0
    while s < 22800.0:
        for side in (-1, 1):
            in_cave = CAVE[0] - 300.0 < s < CAVE[1] + 200.0
            over_pool = side > 0 and POOL[0] - 200.0 < s < POOL[1] + 200.0
            if not in_cave and not over_pool:
                rock(rng.choice(["SM_RockPack_Cliff_07_B", "SM_RockPack_Cliff_07_D", "SM_S_Rock_10", "SM_S_Rock_04"]),
                     s + rng.uniform(-150, 150), side * rng.uniform(1350, 1800), -40.0, rng.uniform(0.8, 1.3), rng.uniform(0, 360))
        s += 850.0

    # Rock under each lip of a gap, so the chasm has a real edge and not a sheer cut in the ground.
    for gap0, gap1 in GAPS:
        for lip, direction in ((gap0, 1.0), (gap1, -1.0)):
            cliff = mesh("SM_RockPack_Cliff_07_D")
            bounds = unreal.load_asset(cliff).get_bounds()
            for d in (-420.0, 0.0, 420.0):
                x, y = road.point(lip + direction * 210.0, d)
                # The rock's top stays just under the walkable surface, so it can't catch the eye as a bump.
                z = level(lip) - 12.0 - (bounds.origin.z + bounds.box_extent.z)
                mesh_actor(cliff, x, y, z, folder, (1.0, 1.0, 1.0), road.yaw(lip) + 90.0 * direction + d * 0.05)

    # Frame the cracked wall and gate, which are the zone's landmarks.
    for actor in greybox_actors():
        label = actor.get_actor_label()
        name = actor.get_class().get_name()
        if label == "Ledge":
            # Rubble against the step's straight front edge. It has no collision, so it can't change the hop.
            origin = origin_of(actor)
            front = to_road(origin[0]) + LEDGE_SHIFT - origin[5] * 50.0
            d = -LANE + 60.0
            while d < LANE:
                rock(rng.choice(["SM_R_Rock_01", "SM_R_Rock_02", "SM_S_Rock_01"]), front - rng.uniform(5, 30), d, -30.0, rng.uniform(0.18, 0.3), rng.uniform(0, 360))
                d += 170.0
        if name == "Gate":
            s = to_road(origin_of(actor)[0])
            for side in (-1, 1):
                rock("SM_RockPack_Cliff_07_B", s, side * 1050.0, -60.0, 1.25, side * 60.0)
            location = actor.get_actor_location()
            x, y = road.point(s - 250.0)
            niagara("/Game/FreeParticle_SoftTofu/Niagara/NS_Sparkling_Glow", x, y, location.z - 150.0, folder, 2.0)


def build_water():
    water = unreal.load_asset("/Game/Stylized_PBR_Nature/Terrain/M_Water_Basic")
    s = (MARSH[0] + MARSH[1]) / 2.0
    x, y = road.point(s)
    length = MARSH[1] - MARSH[0] + 900.0
    mesh_actor("/Engine/BasicShapes/Plane", x, y, WATER_LEVEL - 3.0, "Water", (length / 100.0, 56.0, 1.0), road.yaw(s), water, "MarshWater")


def build_boundaries():
    top = 4500.0
    bottom = -1400.0
    for side in (-1, 1):
        s = -50.0
        while s < ROAD_LENGTH + 50.0:
            following = s + 400.0
            # The right-hand wall has openings where a side area leads to a hidden petal.
            middle = (s + following) / 2.0
            if side < 0 or not any(abs(middle - s0) < half + 200.0 for s0, half, _, _ in POCKETS):
                invisible_wall(*road.point(s, side * (EDGE + 50.0)), *road.point(following, side * (EDGE + 50.0)), bottom, top)
            s = following
    invisible_wall(*road.point(-50.0, -EDGE - 50.0), *road.point(-50.0, EDGE + 50.0), bottom, top)
    invisible_wall(*road.point(ROAD_LENGTH + 50.0, -EDGE - 50.0), *road.point(ROAD_LENGTH + 50.0, EDGE + 50.0), bottom, top)

    # Each side area is a straight-sided room with its own three walls. Most have a hidden floor as well.
    for s0, half, far, has_floor in POCKETS:
        heading = road.heading(s0)
        px, py = road.point(s0)

        def corner(along, side):
            return px + along * math.cos(heading) - side * math.sin(heading), py + along * math.sin(heading) + side * math.cos(heading)

        half_walls = half + 200.0
        # They start inside the road's edge, because the curved edge bends away from this straight room and would leave a slit.
        invisible_wall(*corner(-half_walls, EDGE - 200.0), *corner(-half_walls, far), bottom, top)
        invisible_wall(*corner(half_walls, EDGE - 200.0), *corner(half_walls, far), bottom, top)
        invisible_wall(*corner(-half_walls, far + 50.0), *corner(half_walls, far + 50.0), bottom, top)
        if has_floor:
            floor_x, floor_y = corner(0.0, (EDGE + far) / 2.0)
            floor = spawn(unreal.StaticMeshActor, floor_x, floor_y, level(s0) - 20.0 - 50.0, "PocketFloor", "Boundaries", road.yaw(s0))
            floor.set_actor_scale3d(unreal.Vector(half_walls * 2.0 / 100.0, (far - EDGE) / 100.0, 1.0))
            floor.static_mesh_component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Cube"))
            floor.static_mesh_component.set_collision_profile_name("BlockAll")
            hide_component(floor.static_mesh_component)

    # Each gap gets its own kill volume, closer than the level's big one, so a fall resets quickly.
    for gap0, gap1 in GAPS:
        if (gap0, gap1) != ISLAND_CHAIN:
            s = (gap0 + gap1) / 2.0
            x, y = road.point(s)
            kill_volume(x, y, level(s) - 750.0, (gap1 - gap0) / 2.0 + 100.0, 2000.0, yaw=road.yaw(s))


def build_guides(materials):
    """Warm lights lead the eye along the road. Their stencil keeps them coloured while the world around is grey."""
    rng = random.Random(SEED + 3)
    glow = Scatter("Guide_Mushrooms", 9000, 12000, shadows=False, material=materials["guide"], stencil=True)
    teal = Scatter("Guide_TealMushrooms", 9000, 12000, shadows=False, material=materials["teal"], stencil=True)
    mushroom = mesh("SM_Caesars_Mushroom_01")
    s = 200.0
    while s < ROAD_LENGTH:
        if has_road(s):
            for side in (-1, 1):
                x, y = road.point(s + rng.uniform(-60, 60), side * (LANE - rng.uniform(10, 40)))
                in_hollow = ZONES[1][1] <= s < ZONES[1][2]
                (teal if in_hollow else glow).add(mushroom, x, y, level(s), rng.uniform(1.3, 2.2) if in_hollow else rng.uniform(1.0, 1.5), rng, sink=2.0)
        s += 260.0
    glow.build()
    teal.build()

    # Stones scattered on the dirt, as the road would look bare without them. They have no collision, so the ball rolls over them.
    pebbles = Scatter("Road_Pebbles", 4000, 5500, shadows=False)
    for x, y, s in along_road(100, ROAD_LENGTH, -LANE + 40.0, LANE - 40.0, 150.0, rng):
        if has_road(s) and rng.random() < 0.3:
            pebbles.add(mesh(rng.choice(["SM_Stone_Pebble_1", "SM_Stone_Pebble_2", "SM_Stone_Pebble_3", "SM_Generic_Rock_01"])), x, y, level(s), rng.uniform(0.35, 0.8), rng, sink=4.0)
    pebbles.build()

    warm = unreal.LinearColor(1.0, 0.62, 0.28, 1.0)
    for actor in greybox_actors():
        name = actor.get_class().get_name()
        location = actor.get_actor_location()
        if name in ("BP_CheckpointShrine_C", "BP_FormFlower_Stone_C", "CrackedWall", "Gate", "LevelGoal", "BP_GoldenPetal_C"):
            point_light(location.x, location.y, location.z + 300.0, warm, 90.0 if name == "LevelGoal" else 30.0, 1400.0)
    for gap0, gap1 in GAPS:
        x, y = road.point(gap1 + 150.0)
        point_light(x, y, level(gap1) + 300.0, warm, 45.0, 1500.0)

    # The end of the level: a living tree, which is what the whole climb back to colour has been about.
    goal_s = ROAD_LENGTH - 200.0
    tree = mesh("SM_Tree_Broadleaf_1")
    x, y = road.point(goal_s)
    z = level(goal_s)
    mesh_actor(tree, x, y, z - base_height_offset(unreal.load_asset(tree), 1.3), "Guide Lights", (1.3, 1.3, 1.3))
    niagara("/Game/FreeParticle_SoftTofu/Niagara/NS_Sparkling_Glow", x, y, z + 300.0, "Guide Lights", 4.0)


def build_preview_cameras():
    def camera(name, s_from, d_from, up_from, s_to, d_to, up_to):
        x0, y0 = road.point(s_from, d_from)
        x1, y1 = road.point(s_to, d_to)
        ground_from = level(min(max(s_from, 0.0), ROAD_LENGTH)) if abs(d_from) <= EDGE else terrain_height(x0, y0)
        return preview_camera(name, (x0, y0, ground_from + up_from), (x1, y1, level(min(max(s_to, 0.0), ROAD_LENGTH)) + up_to))

    cameras = [camera("Preview_1_1_A", 150.0, 0.0, 190.0, 1900.0, 180.0, 150.0),   # Matches picture 1.
               camera("Preview_1_1_B", 1500.0, 300.0, 170.0, 3000.0, -2700.0, 800.0),   # Back toward the giant.
               camera("Preview_1_1_C", 5900.0, -6000.0, 3500.0, 7500.0, 0.0, 0.0),
               camera("Preview_1_1_D", 6440.0, 0.0, 200.0, 8490.0, 0.0, 60.0),   # The island jumps.
               camera("Preview_1_1_E", 10000.0, 0.0, 200.0, 12120.0, 0.0, 500.0),   # Up the stairs to the gate.
               camera("Preview_1_1_F", 2800.0, -1200.0, 300.0, 4000.0, -3400.0, 500.0),   # Waterfalls.
               camera("Preview_1_2_D", 13500.0, 0.0, 240.0, 14500.0, 0.0, 300.0),   # The blocked cave.
               camera("Preview_1_2_E", 14720.0, -150.0, 170.0, 15300.0, 80.0, 180.0),   # Inside the tunnel.
               camera("Preview_1_2_F", 15250.0, 300.0, 330.0, 15720.0, -100.0, 0.0),   # The first plate.
               camera("Preview_1_2_H", 16800.0, -300.0, 230.0, 17900.0, 1900.0, -100.0),   # Plate and pool, like picture 2.
               camera("Preview_1_2_G", 18300.0, 300.0, 210.0, 19200.0, 0.0, 250.0),   # The plank gate.
               camera("Preview_Route", 20000.0, -18000.0, 22000.0, 20000.0, 0.0, 0.0)]
    for name, s0, s1 in ZONES[1:]:
        middle = (s0 + s1) / 2.0
        cameras.append(camera("Preview_{}_A".format(name), s0 + 400.0, -200.0, 220.0, s0 + 2800.0, 0.0, 120.0))
        cameras.append(camera("Preview_{}_B".format(name), middle, 420.0, 170.0, middle - 2200.0, -400.0, 300.0))
        cameras.append(camera("Preview_{}_C".format(name), middle - 1800.0, -7000.0, 4200.0, middle + 1000.0, 0.0, 0.0))
    return cameras


def check_layout():
    """Stops the build if an edit to the tables above broke a rule the level depends on."""
    assert abs(to_road(32200.0) - ROAD_LENGTH) < 1.0, "the inserts and ROAD_LENGTH disagree"
    for x in (0.0, 5000.0, 12100.0, 14800.0, 22600.0, 31700.0):
        assert abs(greybox_x(to_road(x)) - x) < 1.0, x
    for s in range(100, int(ROAD_LENGTH), 100):
        if has_road(s) and has_road(s + 100):
            slope = abs(level(s + 100) - level(s)) / 100.0
            # 14 degrees is the steepest ramp the greybox already has.
            assert slope < 0.26, "too steep at s = {}: {:.2f}".format(s, slope)
    for s0, s1, _ in BENDS:
        for gap0, gap1 in [(3300.0, 4100.0), (14000.0, 16000.0), (16600.0, 19500.0), (MARSH[0], MARSH[1])]:
            assert s1 <= gap0 or s0 >= gap1, "a bend overlaps a section that must stay straight: {}".format((s0, s1))
    for i in range(0, int(ROAD_LENGTH), 300):
        for j in range(i + 4000, int(ROAD_LENGTH), 300):
            a, b = road.point(i), road.point(j)
            assert math.hypot(a[0] - b[0], a[1] - b[1]) > ROAD_SIDE * 2.0, "the road runs into itself at {} and {}".format(i, j)


def main():
    global WORLD_MESHES
    check_layout()
    world_path = open_world_map(SOURCE_MAP, WORLD_MAP)
    clear_generated()
    materials = build_materials()
    WORLD_MESHES = import_world_meshes()

    bend_greybox()
    added = add_challenges()

    x0, x1, y0, y1 = min(road.xs), max(road.xs), min(road.ys), max(road.ys)
    xs = spread_coordinates(x0 - 110000.0, x1 + 110000.0, x0 - 3000.0, x1 + 3000.0, 150.0)
    ys = spread_coordinates(y0 - 110000.0, y1 + 110000.0, y0 - 6000.0, y1 + 6000.0, 150.0)
    terrain_path = Terrain(terrain_height, terrain_path_mask).write_and_import("SM_LS_Terrain_L1", xs, ys)
    mesh_actor(terrain_path, 0.0, 0.0, 0.0, "Terrain", material=materials["terrain"], label="Terrain")

    for index, (s0, s1, living) in enumerate(ROAD_PIECES):
        path = build_road_mesh(s0, s1, index)
        piece = mesh_actor(path, 0.0, 0.0, 0.0, "Road", material=materials["living"] if living else materials["terrain"], label="Road")
        piece.static_mesh_component.set_collision_profile_name("BlockAll")
        if living:
            piece.static_mesh_component.set_render_custom_depth(True)
            piece.static_mesh_component.set_custom_depth_stencil_value(ls_world_common.FULL_COLOUR_STENCIL)

    build_island_chain(materials)
    dress_greybox(materials, added)
    scatter_rings(materials)
    living_start()
    awakening_grove_landmarks(materials)
    rootwood_hollow(materials)
    rock_set_pieces()
    build_water()
    build_boundaries()
    build_guides(materials)

    set_up_sky(sun_pitch=-8.0, sun_yaw=196.0, sun_colour=unreal.LinearColor(1.0, 0.58, 0.32, 1.0), sun_lux=7.0,
               cloud_material="/Game/StylizedVolClouds/Materials/MI/MI_VolumetricCloud_Cloudy",
               driver_fog=(0.02, 0.008), fog_colour=unreal.LinearColor(0.42, 0.2, 0.12, 1.0), exposure=-0.8, sky_light=1.0)

    # The world starts black and white, and notes bring its colour back. Only stencil-marked things keep their colour from the start.
    driver = ls_world_common.find_actor(unreal.RestorationDriver)
    driver.set_editor_property("withered_saturation", 0.0)
    driver.set_editor_property("withered_tint", unreal.LinearColor(1.05, 0.9, 0.78, 1.0))

    cameras = build_preview_cameras()
    report(world_path)
    take_preview_screenshots(cameras)


main()
