# Last Seed - turns the straight Level 1 greybox into a winding Withered Forest at sunset.
#
# Purpose: copies L_Level1 to L_Level1_World, bends the route along a curved road with hills, moves every gameplay actor
# onto it, adds the extra challenges that lengthen the level, and builds the ground, forest, boundaries and
# light around it. The art follows three concept pictures, one per zone.
#
# How the bending works: every greybox position (x, y, z) becomes distance along the road s = to_road(x), distance to its
# right d = y, and height z + hills(s). Sections with a jump or a block puzzle are straight and flat, so they play the same.
#
# Safe to rerun: each greybox actor remembers its original place in a tag, generated actors are tagged LS_Generated and
# replaced, and a fixed random seed gives the same forest. L_Level1 itself is never changed.
# Requires: Python Editor Script Plugin. Run with Tools > Execute Python Script.

import importlib
import json
import math
import os
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

ROAD_LENGTH = 44700.0
# (start, end, degrees). Positive turns right. Everything between bends is straight on purpose: gaps, ledge, cave, plates, gate, marsh.
BENDS = [(500, 3200, 35), (4100, 5500, -60), (8900, 11800, 70), (12200, 14000, -50), (16000, 16600, 20),
         (22500, 23800, 40), (23800, 25800, -50), (25800, 27800, 55), (32700, 36800, -85), (36800, 39000, 40), (42900, 44700, -30)]
# (greybox x, extra length). This is where the new challenges fit between the greybox's own.
INSERTS = [(6490, 2400), (14300, 2000), (15000, 3000), (17100, 1000), (21500, 1500), (24400, 1000), (29500, 1600)]
# Height added to the greybox's own, as (s, height). Flat wherever two neighbours match. Steepest about 9 degrees.
HILLS = [(0, 0), (300, 0), (1700, 130), (3200, 0), (4100, 0), (4800, -70), (5500, 0), (12200, 0), (14000, 150), (22700, 150),
         (24000, 40), (26200, 40), (27800, 0), (32700, 0), (34500, 150), (36800, 0), (42700, 0), (44000, 80), (44700, 80)]
# How much the land rises on the left and falls on the right, as (s, height). Negative rises on the right instead.
SIDE_TILT = [(0, 750), (6000, 750), (8000, 200), (12200, 300), (13000, 0), (26000, 0), (27800, 300), (36800, -300), (44700, 200)]
# How much the land rises on both sides, which makes a canyon.
CANYON = [(0, 0), (12200, 0), (13200, 1800), (25500, 1800), (26500, 0), (44700, 0)]

# The greybox's floor as (x0, x1, z0, z1), which gives the height the road starts from.
GREYBOX_FLOOR = [(0, 6500, 0, 0), (6500, 8000, 0, 300), (8000, 26100, 300, 300), (26100, 28100, 300, 800), (28100, 30200, 800, 800), (30200, 32200, 300, 300)]
MARSH = (28000.0, 32500.0)
MARSH_GREYBOX = (19600.0, 22600.0)
WATER_LEVEL = 300.0
SWAMP = (27200.0, 37400.0)  # Picture 3's open water spreads either side of the road between these. The marsh lane is the middle of it.
SWAMP_WIDTH = 6500.0  # How far the water reaches from the road, before the land climbs out of it.
MIST_LAYERS = (20.0, 60.0, 110.0)  # Heights above the water. Stacked sheets of drifting noise read as mist lying on it.
MARSH_BED = -50.0
ISLAND_CHAIN = (6490.0, 8890.0)
LAVA_LEVEL = -300.0  # The surface of the lava filling the pit under the floating islands.
LAVA_TILE = 800.0  # How many cm one repeat of the lava material's textures covers.
RIVER_BED = -650.0  # The bottom of the lava river's channel.
RIVER_LENGTH = 7600.0  # How far the river runs from the road on each side, before it narrows to nothing.
CAVERN_GAP = (19700.0, 22300.0)
GAPS = [(3500.0, 3900.0), ISLAND_CHAIN, CAVERN_GAP, (39700.0, 40700.0), (41500.0, 42700.0)]
GLIDE_ISLAND = (40700.0, 41500.0, 500.0)  # A landing that splits the glide in two.
# The road's solid pieces, between gaps and the marsh. The first two stay in colour, as the start of picture 1.
ROAD_PIECES = [(-800.0, 3500.0, True), (3900.0, 6490.0, True), (8890.0, 19700.0, False), (22300.0, 28000.0, False), (32500.0, 39700.0, False), (40700.0, 41500.0, False), (42700.0, ROAD_LENGTH + 800.0, False)]
# (s, d, height). A full-speed jump travels about 890 cm, so 333 cm gaps and 700 cm islands land safely from anywhere near an edge.
ISLANDS = [(7173.0, -120.0, 0.0), (8206.0, 120.0, 40.0)]
ISLAND_RADIUS = 350.0
# (s of the ledge, half width, far side, has a floor). Side areas that lead to the hidden petals. All are on the right.
POCKETS = [(5200.0, 500.0, 2700.0, True), (13400.0, 500.0, 2700.0, True), (40000.0, 500.0, 2500.0, False)]

ZONES = [("1_1", 0.0, 12200.0), ("1_2", 12200.0, 26200.0), ("1_3", 26200.0, ROAD_LENGTH)]
# Zone 1-2. Two closed tunnels with the big cavern between them. The first starts at the rock pile and ends just past the gate.
TUNNELS = [(14440.0, 19500.0), (22300.0, 25900.0)]
TUNNEL_HALF = 820.0
TUNNEL_HIGH = 1000.0
CAVE_WALL_S = 14500.0
# The cavern is a dome over dark water, measured from its centre. The hole in its roof lets the sun in.
CAVERN = (21000.0, 2000.0, 3200.0)  # (s of the centre, half length along the road, half width across it)
CAVERN_FLOOR = 60.0
CAVERN_WATER = 170.0
CAVERN_HIGH = 2100.0
PAD_TOP = 450.0  # The same height as the road either side of the cavern.
# The parkour route, in order. Rock pads are (s, d, radius).
# One straight fenced walkway down the middle, as this is the first level: floor, log, sunlit floor, log, floor.
ROUTE_FLOORS = [(19680.0, 19750.0), (20730.0, 21270.0), (22250.0, 22320.0)]
ROUTE_FENCE = 310.0  # How far the fence stands from the middle of the walkway.
LOGS = [20240.0, 21760.0]
SUN_PAD_RADIUS = 620.0  # The rock under the sun shaft, which the walkway crosses.
LOG_HALF = 500.0
LOG_TILT = 10.0
LOG_COUNTERWEIGHT = 2000.0  # Light enough for every form: Seed (20 kg) tips it from 100 cm past the pivot, and Stone (80 kg) from 25.

BLOCK_S = 17050.0
PLATE_S = 18000.0
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


def swamp_amount(s):
    return smoothstep(SWAMP[0], SWAMP[0] + 700.0, s) * (1.0 - smoothstep(SWAMP[1] - 700.0, SWAMP[1], s))


def road_box(s0, s1, margin):
    """The world box around a stretch of road, as (x0, x1, y0, y1)."""
    points = [road.point(s) for s in range(int(s0), int(s1), 200)]
    return (min(p[0] for p in points) - margin, max(p[0] for p in points) + margin, min(p[1] for p in points) - margin, max(p[1] for p in points) + margin)


def river_shape(across):
    """The lava river at a distance across the road: (its middle along the road, its half width). It runs straight only where it passes under the road."""
    side = abs(across)
    bend = smoothstep(1100.0, 3000.0, side)
    middle = bend * (650.0 * math.sin(across / 1500.0 + 0.6) + 250.0 * math.sin(across / 620.0))
    # As wide as the gap at the road, so it meets both lips, then narrower and uneven further out.
    width = lerp(1200.0, 620.0 + 130.0 * math.sin(across / 900.0 + 1.0) + 60.0 * math.sin(across / 210.0), smoothstep(1100.0, 3200.0, side))
    return middle, width * (1.0 - smoothstep(RIVER_LENGTH - 1400.0, RIVER_LENGTH, side))


def river_amount(x, y):
    """1 in the channel, falling to 0 over the bank. The road is straight here, so this measures along and across it from the middle of the island gap."""
    middle_s = (ISLAND_CHAIN[0] + ISLAND_CHAIN[1]) / 2.0
    px, py = road.point(middle_s)
    heading = road.heading(middle_s)
    along = (x - px) * math.cos(heading) + (y - py) * math.sin(heading)
    across = -(x - px) * math.sin(heading) + (y - py) * math.cos(heading)
    if abs(across) >= RIVER_LENGTH:
        return 0.0
    middle, width = river_shape(across)
    if width < 5.0:
        return 0.0
    return 1.0 - smoothstep(width - 500.0, width, abs(along - middle))


def in_river(x, y):
    return river_amount(x, y) > 0.0


def in_cavern(s, d, margin=1.05):
    return ((s - CAVERN[0]) / CAVERN[1]) ** 2 + (d / CAVERN[2]) ** 2 < margin * margin


def in_tunnel(s, d):
    return abs(d) < TUNNEL_HALF + 300.0 and any(s0 - 100.0 < s < s1 + 100.0 for s0, s1 in TUNNELS)


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
    height = lerp(height, WATER_LEVEL - 70.0, swamp_amount(near_s) * (1.0 - smoothstep(SWAMP_WIDTH - 2500.0, SWAMP_WIDTH, side)))
    if in_cavern(s, d):
        return CAVERN_FLOOR
    # The island gap is the lava river instead of a straight cut.
    if not ISLAND_CHAIN[0] < near_s < ISLAND_CHAIN[1]:
        height = lerp(height, CHASM, gap_amount(near_s) * (1.0 - smoothstep(150.0, 1600.0, side)))
    return lerp(height, RIVER_BED, river_amount(x, y))


def road_height(s, d, x, y):
    """The surface the road mesh shows. It is flat across the lane, so a ball never drifts sideways on its own."""
    if abs(d) <= LANE:
        return level(s)
    if abs(d) <= EDGE:
        return level(s) + 78.0 * smoothstep(LANE, EDGE, abs(d))
    return side_ground(s, d, x, y)


def terrain_height(x, y):
    s, d = road.project(x, y)
    if in_cavern(s, d):
        return CAVERN_FLOOR
    if 0.0 <= s <= ROAD_LENGTH and abs(d) < ROAD_SIDE - 100.0:
        if MARSH[0] <= s <= MARSH[1]:
            if abs(d) <= LANE:
                return WATER_LEVEL - 400.0
            return WATER_LEVEL - 70.0
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


def build_tunnel(s0, s1, index):
    """A rock hill with a closed tunnel through it, following the road. It is solid, which also keeps the camera inside."""
    built = Mesh()
    rows, columns = int((s1 - s0) / 100.0), 26
    outer_half, outer_high = 2000.0, 1800.0

    def lumps(row, column, size):
        return size * (math.sin(row * 1.3 + column * 0.7) * 0.5 + math.sin(row * 0.4 - column * 1.9 + 2.0) * 0.5)

    for half, high, sink, lump in ((TUNNEL_HALF, TUNNEL_HIGH, 30.0, 26.0), (outer_half, outer_high, 120.0, 90.0)):
        for row in range(rows + 1):
            s = lerp(s0, s1, row / rows)
            for column in range(columns + 1):
                angle = math.pi * (1.0 - column / columns)
                rough = lumps(row, column, lump) if 0 < column < columns else 0.0
                x, y = road.point(s, math.cos(angle) * (half + rough))
                built.add_vertex((x, y, level(s) - sink + math.sin(angle) * (high + rough)), (0.0, 0.0))
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
    return import_generated_mesh("SM_LS_Tunnel_{}".format(index), built, solid=True)


def build_cavern_dome():
    """The cavern's roof and walls, with a hole at the top. The parts where the two tunnels pass through are left out."""
    built = Mesh()
    centre_s, half_s, half_d = CAVERN
    rows, columns = 22, 54
    first_angle = math.asin(0.16)
    for offset in (0.0, 160.0):
        for row in range(rows + 1):
            theta = lerp(first_angle, math.pi / 2.0, row / rows)
            for column in range(columns):
                phi = 2.0 * math.pi * column / columns
                rough = 45.0 * math.sin(row * 1.1 + column * 0.9) * math.sin(row * 0.5 - column * 1.4) if row < rows else 0.0
                s = centre_s + (half_s + offset + rough) * math.sin(theta) * math.cos(phi)
                d = (half_d + offset + rough) * math.sin(theta) * math.sin(phi)
                x, y = road.point(s, d)
                built.add_vertex((x, y, CAVERN_FLOOR + (CAVERN_HIGH + offset + rough) * math.cos(theta)), (0.0, 0.0))
    per_surface = (rows + 1) * columns
    centre_x, centre_y = road.point(centre_s)
    centre = (centre_x, centre_y, CAVERN_FLOOR)
    for surface in (0, 1):
        for row in range(rows):
            for column in range(columns):
                base = surface * per_surface + row * columns
                a, b = base + column, base + (column + 1) % columns
                c, d = a + columns, b + columns
                for triangle in ((a, b, c), (b, d, c)):
                    p = [built.points[i] for i in triangle]
                    px, py, pz = (p[0][0] + p[1][0] + p[2][0]) / 3.0, (p[0][1] + p[1][1] + p[2][1]) / 3.0, (p[0][2] + p[1][2] + p[2][2]) / 3.0
                    s, side = road.project(px, py)
                    if abs(side) < TUNNEL_HALF + 40.0 and pz < PAD_TOP + TUNNEL_HIGH + 40.0 and abs(s - centre_s) > 1000.0:
                        continue
                    # Each triangle is turned to face the middle on the inner surface, and away from it on the outer.
                    u = [p[1][i] - p[0][i] for i in range(3)]
                    v = [p[2][i] - p[0][i] for i in range(3)]
                    normal = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
                    facing_centre = sum(normal[i] * (centre[i] - p[0][i]) for i in range(3)) > 0.0
                    wanted = surface == 0
                    built.triangles.append(triangle if facing_centre == wanted else (triangle[0], triangle[2], triangle[1]))
    # The thickness of the rock around the hole, seen from below.
    for column in range(columns):
        a, b = column, (column + 1) % columns
        c, d = per_surface + a, per_surface + b
        built.triangles += [(a, c, b), (b, c, d)]
    built.smooth_normals()
    return import_generated_mesh("SM_LS_CavernDome", built, solid=True)


def build_lava():
    """A strip following the river, a little wider than its channel. The banks hide its edges, so the shore is wherever the ground meets LAVA_LEVEL."""
    built = Mesh()
    middle_s = (ISLAND_CHAIN[0] + ISLAND_CHAIN[1]) / 2.0
    px, py = road.point(middle_s)
    heading = road.heading(middle_s)
    columns = 8
    across = -RIVER_LENGTH
    rows = 0
    while across <= RIVER_LENGTH:
        middle, width = river_shape(across)
        for column in range(columns + 1):
            along = middle + (width + 150.0) * (column / columns * 2.0 - 1.0)
            x = px + along * math.cos(heading) - across * math.sin(heading)
            y = py + along * math.sin(heading) + across * math.cos(heading)
            built.add_vertex((x, y, LAVA_LEVEL), (x / LAVA_TILE, y / LAVA_TILE))
        rows += 1
        across += 100.0
    for row in range(rows - 1):
        for column in range(columns):
            a = row * (columns + 1) + column
            b = a + 1
            c = a + columns + 1
            d = c + 1
            for triangle in ((a, b, c), (b, d, c)):
                p0, p1, p2 = (built.points[i] for i in triangle)
                # Each triangle faces up, whichever way the river's heading makes the rows run.
                up = (p1[0] - p0[0]) * (p2[1] - p0[1]) - (p1[1] - p0[1]) * (p2[0] - p0[0])
                built.triangles.append(triangle if up > 0.0 else (triangle[0], triangle[2], triangle[1]))
    built.smooth_normals()
    return import_generated_mesh("SM_LS_Lava", built, nanite=False)


def build_swamp_water():
    """A flat sheet in one mesh, as the road bends under it and overlapping planes would double up. Squares standing on high ground are left out."""
    built = Mesh()
    step = 400.0
    x0, x1, y0, y1 = road_box(SWAMP[0], SWAMP[1], SWAMP_WIDTH)
    x = x0
    while x < x1:
        y = y0
        while y < y1:
            s, d = road.project(x + step / 2.0, y + step / 2.0)
            if swamp_amount(min(max(s, 0.0), ROAD_LENGTH)) > 0.0 and outside_distance(s, d) < SWAMP_WIDTH + 400.0:
                if min(terrain_height(x + a, y + b) for a in (0.0, step) for b in (0.0, step)) < WATER_LEVEL + 20.0:
                    first = len(built.points)
                    for a, b in ((0.0, 0.0), (step, 0.0), (0.0, step), (step, step)):
                        built.add_vertex((x + a, y + b, WATER_LEVEL - 3.0), ((x + a) / 2000.0, (y + b) / 2000.0))
                    built.triangles += [(first, first + 1, first + 2), (first + 1, first + 3, first + 2)]
            y += step
        x += step
    built.smooth_normals()
    return import_generated_mesh("SM_LS_SwampWater", built, nanite=False)


def build_swamp_mist():
    """A sheet like the water's. Its U is how thick the mist is, which fades it out at the swamp's edges and thins it over the road, where the ball must stay easy to see."""
    built = Mesh()
    step = 400.0

    def thickness(x, y):
        s, d = road.project(x, y)
        side = outside_distance(s, d)
        return (swamp_amount(min(max(s, 0.0), ROAD_LENGTH)) * (1.0 - smoothstep(SWAMP_WIDTH - 1800.0, SWAMP_WIDTH - 200.0, side))
                * (0.3 + 0.7 * smoothstep(LANE, LANE + 500.0, abs(d))))

    x0, x1, y0, y1 = road_box(SWAMP[0], SWAMP[1], SWAMP_WIDTH)
    x = x0
    while x < x1:
        y = y0
        while y < y1:
            corners = [(x + a, y + b) for a, b in ((0.0, 0.0), (step, 0.0), (0.0, step), (step, step))]
            amounts = [thickness(*corner) for corner in corners]
            if max(amounts) > 0.0:
                first = len(built.points)
                for corner, amount in zip(corners, amounts):
                    built.add_vertex((corner[0], corner[1], WATER_LEVEL), (amount, 0.0))
                built.triangles += [(first, first + 1, first + 2), (first + 1, first + 3, first + 2)]
            y += step
        x += step
    built.smooth_normals()
    return import_generated_mesh("SM_LS_SwampMist", built, nanite=False)


def build_vines():
    """Thin vines hanging from the cavern's roof, all in one mesh. They have no collision."""
    built = Mesh()
    rng = random.Random(SEED + 8)
    centre_s, half_s, half_d = CAVERN
    for _ in range(90):
        theta = rng.uniform(0.25, 1.15)
        phi = rng.uniform(0.0, 2.0 * math.pi)
        s = centre_s + half_s * math.sin(theta) * math.cos(phi)
        d = half_d * math.sin(theta) * math.sin(phi)
        x, y = road.point(s, d)
        top = CAVERN_FLOOR + CAVERN_HIGH * math.cos(theta) + 20.0
        length = rng.uniform(250.0, 900.0)
        wander = rng.uniform(0.0, 6.0)
        path = [(x + 12.0 * math.sin(i * 0.9 + wander), y + 12.0 * math.cos(i * 0.7 + wander), top - length * i / 7.0) for i in range(8)]
        ls_generate_world_meshes.add_tube(built, path, [rng.uniform(5.0, 8.0) * (1.0 - 0.08 * i) for i in range(8)], 5)
    built.smooth_normals()
    return import_generated_mesh("SM_LS_Vines", built)


def import_world_meshes():
    return {"tree": import_generated_mesh("SM_LS_GnarledTree", ls_generate_world_meshes.build_gnarled_tree()),
            "note": import_generated_mesh("SM_LS_MusicNote", ls_generate_world_meshes.build_music_note(), nanite=False),
            "ring": import_generated_mesh("SM_LS_GateRing", ls_generate_world_meshes.build_gate_ring()),
            "log": import_generated_mesh("SM_LS_Log", ls_generate_world_meshes.build_log()),
            "root_arch": import_generated_mesh("SM_LS_RootArch", ls_generate_world_meshes.build_root_arch()),
            "pivot": import_generated_mesh("SM_LS_LogPivot", ls_generate_world_meshes.build_log_pivot()),
            "shaft": import_generated_mesh("SM_LS_LightShaft", ls_generate_world_meshes.build_light_shaft(), nanite=False),
            "island": import_generated_mesh("SM_LS_FloatingIsland", ls_generate_world_meshes.build_floating_island()),
            "moss": import_generated_mesh("SM_LS_TreeMoss", ls_generate_world_meshes.build_tree_moss()),
            "roots": import_generated_mesh("SM_LS_RootClump", ls_generate_world_meshes.build_root_clump()),
            "bramble": import_generated_mesh("SM_LS_Bramble", ls_generate_world_meshes.build_bramble()),
            "blob": import_generated_mesh("SM_LS_Blob", ls_generate_world_meshes.build_blob(), nanite=False),
            "shrine": import_generated_mesh("SM_LS_Shrine", ls_generate_world_meshes.build_shrine(), nanite=False),
            "water": build_swamp_water(),
            "lava": build_lava(),
            "mist": build_swamp_mist()}


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
    materials["lantern"] = glow("M_LS_Lantern", 1.0, 0.55, 0.15, 5.0)
    materials["vine"] = glow("M_LS_Vine", 0.05, 0.16, 0.04, 0.0)

    material = fresh_material("M_LS_SunShaft")
    material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_ADDITIVE)
    material.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property("two_sided", True)
    # Strongest at the hole, fading to nothing before it reaches the water. V runs from the top to the bottom of the shaft.
    along = mask(material, node(material, unreal.MaterialExpressionTextureCoordinate), False)
    fade = combine(material, unreal.MaterialExpressionSubtract, number(material, 1.0), along)
    # The cone's edges fade out too, or they would show as hard lines in the air.
    edge = node(material, unreal.MaterialExpressionFresnel, exponent=1.6, base_reflect_fraction=0.0)
    soft = combine(material, unreal.MaterialExpressionSubtract, number(material, 1.0), edge)
    strength = combine(material, unreal.MaterialExpressionMultiply, combine(material, unreal.MaterialExpressionMultiply, fade, fade), soft)
    output(material, combine(material, unreal.MaterialExpressionMultiply, strength, colour(material, 0.5, 0.38, 0.18)), unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    materials["sun_shaft"] = finish(material)

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
    material = fresh_material("M_LS_Blob")
    # One mesh, one material: the mesh's U says which part this is. See ls_generate_world_meshes.build_blob.
    part = mask(material, node(material, unreal.MaterialExpressionTextureCoordinate), True)
    eye = node(material, unreal.MaterialExpressionSaturate)
    ls_material_helpers.library.connect_material_expressions(combine(material, unreal.MaterialExpressionMultiply, combine(material, unreal.MaterialExpressionSubtract, part, number(material, 0.75)), number(material, 10.0)), "", eye, "")
    goo = node(material, unreal.MaterialExpressionSaturate)
    ls_material_helpers.library.connect_material_expressions(combine(material, unreal.MaterialExpressionMultiply, combine(material, unreal.MaterialExpressionSubtract, part, number(material, 0.25)), number(material, 10.0)), "", goo, "")
    output(material, colour(material, 0.035, 0.02, 0.05), unreal.MaterialProperty.MP_BASE_COLOR)
    glowing = blend(material, combine(material, unreal.MaterialExpressionMultiply, goo, colour(material, 0.035, 0.005, 0.07)), colour(material, 6.0, 6.0, 6.0), eye)
    output(material, glowing, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    output(material, number(material, 0.35), unreal.MaterialProperty.MP_ROUGHNESS)
    materials["blob"] = finish(material)

    material = fresh_material("M_LS_LilyPad")
    # Darker toward the rim, with the grass texture for its veins. A cylinder's top has round UVs, the same trick as the plate's rings.
    uv = node(material, unreal.MaterialExpressionTextureCoordinate)
    offset = combine(material, unreal.MaterialExpressionSubtract, uv, node(material, unreal.MaterialExpressionConstant2Vector, r=0.5, g=0.5))
    radius = node(material, unreal.MaterialExpressionLength)
    ls_material_helpers.library.connect_material_expressions(offset, "", radius, "")
    centre_light = combine(material, unreal.MaterialExpressionSubtract, number(material, 1.25), combine(material, unreal.MaterialExpressionMultiply, radius, number(material, 1.6)))
    leaf = combine(material, unreal.MaterialExpressionMultiply, texture(material, terrain_folder + "/T_Grass_2", world_uv(material, 180.0)), colour(material, 0.28, 0.55, 0.14))
    output(material, combine(material, unreal.MaterialExpressionMultiply, leaf, centre_light), unreal.MaterialProperty.MP_BASE_COLOR)
    output(material, number(material, 0.55), unreal.MaterialProperty.MP_ROUGHNESS)
    materials["pad"] = finish(material)
    material = fresh_material("M_LS_Mist")
    material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    material.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property("two_sided", True)
    # Two noises drifting at different speeds never repeat in an obvious way.
    slow = node(material, unreal.MaterialExpressionPanner, speed_x=0.012, speed_y=0.006)
    ls_material_helpers.library.connect_material_expressions(world_uv(material, 2600.0), "", slow, "Coordinate")
    fast = node(material, unreal.MaterialExpressionPanner, speed_x=-0.02, speed_y=0.016)
    ls_material_helpers.library.connect_material_expressions(world_uv(material, 900.0), "", fast, "Coordinate")
    wisps = combine(material, unreal.MaterialExpressionAdd, mask(material, texture(material, terrain_folder + "/T_Dirt", slow), True), mask(material, texture(material, terrain_folder + "/T_Dirt", fast), True))
    clear_gaps = node(material, unreal.MaterialExpressionSaturate)
    ls_material_helpers.library.connect_material_expressions(wisps, "", clear_gaps, "")
    amount = mask(material, node(material, unreal.MaterialExpressionTextureCoordinate), True)
    # Where a sheet meets a root or the water it fades out, or it would draw a hard line across it.
    soft = node(material, unreal.MaterialExpressionDepthFade, fade_distance_default=90.0)
    ls_material_helpers.library.connect_material_expressions(combine(material, unreal.MaterialExpressionMultiply, combine(material, unreal.MaterialExpressionMultiply, clear_gaps, amount), number(material, 0.36)), "", soft, "Opacity")
    output(material, colour(material, 0.3, 0.32, 0.32), unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    output(material, soft, unreal.MaterialProperty.MP_OPACITY)
    materials["mist"] = finish(material)
    materials["goal_glow"] = glow("M_LS_GoalGlow", 1.0, 0.6, 0.14, 2.6)
    materials["moss_strand"] = glow("M_LS_MossStrand", 0.1, 0.13, 0.05, 0.0)
    materials["thorn"] = glow("M_LS_Thorn", 0.5, 0.03, 0.05, 0.6)
    materials["note"] = glow("M_LS_Note", 1.0, 0.62, 0.1, 2.0)
    materials["petal"] = glow("M_LS_Petal", 1.0, 0.25, 0.4, 1.3)
    material = fresh_material("M_LS_Shrine")
    # Like the blob, the mesh's U says which part this is. See ls_generate_world_meshes.build_shrine.
    part = mask(material, node(material, unreal.MaterialExpressionTextureCoordinate), True)
    orb = node(material, unreal.MaterialExpressionSaturate)
    ls_material_helpers.library.connect_material_expressions(combine(material, unreal.MaterialExpressionMultiply, combine(material, unreal.MaterialExpressionSubtract, part, number(material, 0.75)), number(material, 10.0)), "", orb, "")
    carved = node(material, unreal.MaterialExpressionSaturate)
    ls_material_helpers.library.connect_material_expressions(combine(material, unreal.MaterialExpressionMultiply, combine(material, unreal.MaterialExpressionSubtract, part, number(material, 0.25)), number(material, 10.0)), "", carved, "")
    stone = combine(material, unreal.MaterialExpressionMultiply, texture(material, terrain_folder + "/T_rock", world_uv(material, 120.0)), colour(material, 0.5, 0.48, 0.42))
    output(material, stone, unreal.MaterialProperty.MP_BASE_COLOR)
    output(material, combine(material, unreal.MaterialExpressionMultiply, carved, colour(material, 0.2, 1.1, 1.0)), unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    output(material, number(material, 0.85), unreal.MaterialProperty.MP_ROUGHNESS)
    materials["shrine"] = finish(material)
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
    """The gameplay added to the greybox. Every piece is an existing gameplay class."""
    # 1-1: the note that sat beside the road now rewards the island jumps.
    note = find_by_origin("BP_LifeNote_C", 5000.0, 400.0)
    place_on_road(note, ISLANDS[1][0], ISLANDS[1][1], hills(ISLANDS[1][0]) + ISLANDS[1][2] + 80.0)

    # 1-2: one plate and one block, in a line down the middle of the tunnel. The block runs in a chute, so it can't jam or get lost.
    plate = actors_of("PressurePlate")[0]
    block = actors_of("PushableBlock")[0]
    z = hills(17000.0) + 300.0
    place_on_road(plate, PLATE_S, 0.0, z - 10.0)
    place_on_road(block, BLOCK_S, 0.0, z + 60.0)
    block.set_editor_property("mass_kg", 52.0)
    component = block.get_component_by_class(unreal.StaticMeshComponent)
    component.set_phys_material_override(block_physical_material())
    # A block that could turn would wedge itself across the chute.
    body = component.get_editor_property("body_instance")
    body.set_editor_property("lock_z_rotation", True)
    component.set_editor_property("body_instance", body)
    actors_of("Gate")[0].set_editor_property("required_plates", [plate])

    # 1-2: both thorn patches on the left, which leaves one straight clear lane on the right. The note waits in that lane.
    for thorns in actors_of("HazardVolume"):
        location = thorns.get_actor_location()
        s, d = road.project(location.x, location.y)
        place_on_road(thorns, s, -abs(d), location.z)
    for note_actor in actors_of("BP_LifeNote_C"):
        location = note_actor.get_actor_location()
        s, d = road.project(location.x, location.y)
        if abs(s - 24450.0) < 50.0:
            place_on_road(note_actor, s, 400.0, location.z)

    # 1-3: three more lily pads and a third blob.
    pad = actors_of("SinkingPad")[0]
    for s, d in ((30400.0, -250.0), (30900.0, 250.0), (31400.0, 0.0)):
        clone(pad, "SinkingPad", s, d, 300.0)
    blob_source = actors_of("WitherBlob")[0]
    blob = clone(blob_source, "WitherBlob", 34800.0, -300.0, hills(34800.0) + 370.0)
    blob.set_editor_property("patrol_points", [unreal.Vector(0.0, 0.0, 0.0), unreal.Vector(0.0, 600.0, 0.0)])

    # Three notes move from the thorn lane onto the cavern's walkway, so following the path collects them.
    for x, y, s, height in ((17400.0, -400.0, LOGS[0], 160.0), (17400.0, 400.0, CAVERN[0], 80.0), (16000.0, 400.0, LOGS[1], 160.0)):
        place_on_road(find_by_origin("BP_LifeNote_C", x, y), s, 0.0, PAD_TOP + height)

    # A checkpoint just before the cavern, as a fall into the water would otherwise cost the whole puzzle.
    shrine = clone(actors_of("BP_CheckpointShrine_C")[0], "Shrine", 19380.0, 0.0, PAD_TOP + 50.0)

    hint = clone(actors_of("TutorialTrigger")[0], "Tutorial", 19620.0, 0.0, PAD_TOP + 200.0)
    hint.set_actor_scale3d(unreal.Vector(1.0, 1.0, 1.5))
    hint.set_editor_property("message", unreal.Text("Follow the lanterns across. The logs tip under your weight, then roll on."))
    hint.set_editor_property("display_duration", 6.0)

    for actor in actors_of("TutorialTrigger"):
        if "pressure plate" in str(actor.get_editor_property("message")):
            place_on_road(actor, BLOCK_S - 700.0, 0.0, actor.get_actor_location().z)
            actor.set_editor_property("message", unreal.Text("Push the block along the logs onto the glowing plate, then go around and through the gate."))

    # The route is longer now, so the time to beat is too.
    actors_of("LevelGoal")[0].set_editor_property("par_time_seconds", 390.0)

    return [note, blob, shrine, hint]


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
    # The top of the volume is just under the surface, so the ball sinks into the lava before it resets.
    kill_volume(kill_x, kill_y, LAVA_LEVEL - 240.0, 1400.0, 1000.0, yaw=road.yaw(7690.0))

    # In colour against the grey world, so the danger reads at once.
    lava = mesh_actor(WORLD_MESHES["lava"], 0.0, 0.0, 0.0, "Floating Islands", material=unreal.load_asset("/Game/Lava_Material/Material/M_Lava_01"), label="Lava")
    lava.static_mesh_component.set_cast_shadow(False)
    lava.static_mesh_component.set_render_custom_depth(True)
    lava.static_mesh_component.set_custom_depth_stencil_value(ls_world_common.FULL_COLOUR_STENCIL)
    for s, d in ((6950.0, 500.0), (7700.0, -500.0), (8450.0, 500.0), *[(7690.0 + river_shape(far)[0], far) for far in (-5400.0, -3300.0, 3300.0, 5400.0)]):
        x, y = road.point(s, d)
        # These only light the pit walls. Their shine on the lava would show as pale patches.
        point_light(x, y, LAVA_LEVEL + 260.0, unreal.LinearColor(1.0, 0.32, 0.06, 1.0), 140.0, 2600.0, "Floating Islands").point_light_component.set_editor_property("specular_scale", 0.0)
    for s, d in ((7200.0, 300.0), (8100.0, -300.0)):
        niagara("/Game/FreeParticle_SoftTofu/Niagara/NS_Sparkling_Noise", *road.point(s, d), LAVA_LEVEL + 120.0, "Floating Islands", 6.0)


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
        # What the player must find stays in colour, and the grey water makes a green leaf easy to spot.
        component.set_render_custom_depth(True)
        component.set_custom_depth_stencil_value(ls_world_common.FULL_COLOUR_STENCIL)
    elif class_name == "WitherBlob":
        component = keep_coloured(actor, None)
        component.set_static_mesh(unreal.load_asset(WORLD_MESHES["blob"]))
        component.set_material(0, materials["blob"])
        component.set_relative_scale3d(unreal.Vector(1.0, 1.0, 1.0))
        # shortcut: the eyes look back down the road, where the player comes from, and never turn. Turn the mesh in AWitherBlob::MoveToward if that shows.
        component.set_relative_rotation(unreal.Rotator(0.0, 0.0, 180.0), False, False)
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
        fit_mesh(component, WORLD_MESHES["shrine"], 255.0, -50.0)
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
    if swamp_amount(near_s) > 0.0 and terrain_height(x, y) < WATER_LEVEL + 5.0:
        return False
    if in_cavern(s, d) or in_tunnel(s, d):
        return False
    tree_x, tree_y = road.point(*HEART_TREE)
    return math.hypot(x - tree_x, y - tree_y) > 1300.0


def along_road(s0, s1, d0, d1, spacing, rng):
    """World points in a band beside the road, given as distances from its centre."""
    for s, d in jittered_grid(s0, s1, d0, d1, spacing, rng):
        yield road.point(s, d) + (min(max(s, 0.0), ROAD_LENGTH),)


def scatter_rings(materials):
    rng = random.Random(SEED)
    Scatter.excluded = staticmethod(in_river)

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
        # The middle stays clear for the goal's arch. See thornmire_marsh.
        if abs(road.project(x, y)[1]) > 1500.0:
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
    """Picture 1's foreground: grass and flowers, thinning out as the road leaves the start. They are grey until the notes bring colour back, like the rest of the world."""
    rng = random.Random(SEED + 4)
    plants = Scatter("Living_Grass", 5000, 7000, shadows=False)
    flowers = Scatter("Living_Flowers", 5000, 7000, shadows=False)
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
    """The first tunnel, then the rock pile blocking its mouth. The pile's glowing cracks hint that Stone is what breaks it."""
    folder = "Zone 1-2"
    rng = random.Random(SEED + 6)
    for index, (s0, s1) in enumerate(TUNNELS):
        mesh_actor(build_tunnel(s0, s1, index), 0.0, 0.0, 0.0, folder, material=materials["moss"], label="Tunnel").static_mesh_component.set_collision_profile_name("BlockAll")

    # Rough rocks around the arch, which hide the shell's flat front. Together they read as a cave mouth.
    cliff = mesh("SM_RockPack_Cliff_07_D")
    bounds = unreal.load_asset(cliff).get_bounds()
    mouth = TUNNELS[0][0]
    for step in range(11):
        angle = math.pi * step / 10.0
        scale = rng.uniform(0.55, 0.8)
        x, y = road.point(mouth - 40.0, math.cos(angle) * 1140.0)
        z = level(mouth) + math.sin(angle) * 1280.0 - bounds.origin.z * scale
        mesh_actor(cliff, x, y, z, folder, (scale, scale, scale), rng.uniform(0, 360), label="CaveMouthRock")
    for d, up, scale, yaw in ((-1650.0, -60.0, 1.5, 200.0), (1650.0, -60.0, 1.5, 20.0)):
        path = mesh("SM_RockPack_Cliff_07_B")
        x, y = road.point(mouth - 60.0, d)
        mesh_actor(path, x, y, level(mouth) + up - base_height_offset(unreal.load_asset(path), scale), folder, (scale, scale, scale), yaw, label="CaveCliff")

    # Rows of boulders that fill the arch, largest at the bottom. Nothing here is solid: the hidden wall behind them stops the ball.
    rubble = []
    ground = level(CAVE_WALL_S)
    names = ["SM_R_Rock_01", "SM_R_Rock_02", "SM_R_Rock_03", "SM_S_Rock_01"]
    # Pack rocks are 3 to 6 m tall, so these are small scales. Two layers leave no gaps to see through.
    rows = ((0.0, 700.0, 9, 0.6), (140.0, 680.0, 8, 0.55), (280.0, 640.0, 8, 0.5), (420.0, 560.0, 7, 0.48), (560.0, 460.0, 6, 0.45), (690.0, 340.0, 5, 0.42), (810.0, 180.0, 3, 0.4))
    for layer, up, half_width, count, scale in [(layer, *row) for layer in (0, 1) for row in rows]:
        for index in range(count):
            d = -half_width + 2.0 * half_width * index / (count - 1) + rng.uniform(-30.0, 30.0)
            s = CAVE_WALL_S + 60.0 + layer * 130.0 + rng.uniform(-20.0, 30.0)
            path = mesh(rng.choice(names))
            x, y = road.point(s, d)
            size = scale * rng.uniform(0.85, 1.1)
            rubble.append(mesh_actor(path, x, y, ground + up - 40.0 - base_height_offset(unreal.load_asset(path), size), folder, (size, size, size), rng.uniform(0, 360), materials["cracked"], "RockPile"))
    wall = actors_of("CrackedWall")[0]
    # As tall as the tunnel now, so nothing can pass above it.
    wall.set_actor_location(unreal.Vector(*road.point(CAVE_WALL_S), ground + TUNNEL_HIGH / 2.0), False, False)
    wall.set_actor_scale3d(unreal.Vector(0.5, 14.0, TUNNEL_HIGH / 100.0))
    wall.set_editor_property("rubble_actors", rubble)
    # Boulders fly out, not cubes. This mesh has simple collision, which a physics body needs.
    wall.set_editor_property("debris_mesh", unreal.load_asset(mesh("SM_RockPack_Rock_04")))
    wall.set_editor_property("debris_scale", 1.1)
    wall.set_editor_property("debris_count", 16)

    x, y = road.point(CAVE_WALL_S - 300.0)
    point_light(x, y, ground + 350.0, unreal.LinearColor(1.0, 0.55, 0.2, 1.0), 12.0, 1000.0, folder)


def rock_pad(s, d, radius, materials, folder="Cavern", top=PAD_TOP):
    """A rock column out of the water. A hidden cylinder is the smooth floor, and the rock is only what you see."""
    x, y = road.point(s, d)
    solid = spawn(unreal.StaticMeshActor, x, y, top - 100.0, "PadFloor", folder)
    solid.set_actor_scale3d(unreal.Vector(radius / 50.0, radius / 50.0, 2.0))
    solid.static_mesh_component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Cylinder"))
    solid.static_mesh_component.set_collision_profile_name("BlockAll")
    hide_component(solid.static_mesh_component)
    size = radius / 100.0 * 1.04
    mesh_actor(WORLD_MESHES["island"], x, y, top, folder, (size, size, (top - CAVERN_FLOOR) / 160.0), s, materials["moss"], "RockPad")


def tilting_log(s, d, counterweight, materials, folder="Cavern"):
    """A log on a rooted stump, as in picture 2. It rests with its near end level with the pad before it, and its far end in the air."""
    drop = LOG_HALF * math.sin(math.radians(LOG_TILT))
    x, y = road.point(s, d)
    actor = spawn(unreal.TiltingLog, x, y, PAD_TOP + drop, "TiltingLog", folder, road.yaw(s))
    actor.set_editor_property("half_length", LOG_HALF)
    actor.set_editor_property("half_width", ROUTE_FENCE - 70.0)
    actor.set_editor_property("max_tilt_degrees", LOG_TILT)
    actor.set_editor_property("counterweight_kg_cm", counterweight)
    # Quick enough that a fast Seed finds the far end already coming down, and doesn't launch off it.
    actor.set_editor_property("tilt_response", 0.025)
    log_mesh = actor.get_editor_property("log_mesh")
    log_mesh.set_static_mesh(unreal.load_asset(WORLD_MESHES["log"]))
    log_mesh.set_material(0, materials["bark"])
    log_mesh.set_relative_scale3d(unreal.Vector(LOG_HALF * 2.0 / 800.0, (ROUTE_FENCE - 70.0) / 45.0, 1.5))
    log_mesh.set_relative_location(unreal.Vector(-LOG_HALF, 0.0, -68.0), False, False)
    mesh_actor(WORLD_MESHES["pivot"], x, y, PAD_TOP + drop - 140.0, folder, (1.0, 1.0, (PAD_TOP + drop - 140.0 - CAVERN_FLOOR) / 500.0), road.yaw(s), materials["bark"], "LogStump")
    # The hub, as a ring on each side of the log.
    for side in (-1.0, 1.0):
        hx, hy = road.point(s, d + side * (ROUTE_FENCE - 55.0))
        mesh_actor(WORLD_MESHES["ring"], hx, hy, PAD_TOP + drop - 70.0, folder, (0.22, 0.22, 0.22), road.yaw(s) + 90.0, materials["plate"], "LogHub")


def route_fence(x0, y0, x1, y1, materials, folder="Cavern"):
    """Two rails on posts, for looks only. Nothing stops the ball at the walkway's edge, so a fall means the water and the checkpoint."""
    length = math.hypot(x1 - x0, y1 - y0)
    yaw = math.degrees(math.atan2(y1 - y0, x1 - x0))
    for up in (70.0, 215.0):
        mesh_actor(WORLD_MESHES["log"], x0, y0, PAD_TOP + up, folder, (length / 800.0, 0.32, 0.32), yaw, materials["bark"], "FenceRail")
    for index in range(int(length / 480.0) + 2):
        t = min(index * 480.0 / length, 1.0)
        mesh_actor(WORLD_MESHES["log"], lerp(x0, x1, t), lerp(y0, y1, t), CAVERN_WATER, folder, ((PAD_TOP + 240.0 - CAVERN_WATER) / 800.0, 0.3, 0.3), 0.0, materials["bark"], "FencePost", pitch=90.0)


def build_cavern(materials):
    """Behind the gate: a dome over dark water, crossed by one fenced walkway with two tilting logs, under a shaft of sun from the roof."""
    folder = "Cavern"
    rng = random.Random(SEED + 9)
    centre_s, half_s, half_d = CAVERN
    dome = mesh_actor(build_cavern_dome(), 0.0, 0.0, 0.0, folder, material=materials["moss"], label="CavernDome")
    dome.static_mesh_component.set_collision_profile_name("BlockAll")
    mesh_actor(build_vines(), 0.0, 0.0, 0.0, folder, material=materials["vine"], label="Vines")

    # Falling in means a fresh try from the checkpoint. The volume sits just under the surface, so the ball goes in with a splash of water around it.
    x, y = road.point(centre_s)
    water = unreal.load_asset("/Game/Stylized_PBR_Nature/Terrain/M_Water_Basic")
    mesh_actor("/Engine/BasicShapes/Plane", x, y, CAVERN_WATER, folder, (half_s * 2.2 / 100.0, half_d * 2.2 / 100.0, 1.0), road.yaw(centre_s), water, "CavernWater")
    kill_volume(x, y, CAVERN_WATER - 260.0, half_s * 1.05, half_d * 1.05, 200.0, road.yaw(centre_s))

    # The route: one straight line from the gate to the exit, which is lit and in view the whole way.
    for s in LOGS:
        tilting_log(s, 0.0, LOG_COUNTERWEIGHT, materials)
    # The floor under each log sits just below the log's lowest point. A ball rolling back under a raised end stays on the walkway, and can't drop through.
    for s0, s1, sink in [(s0, s1, 0.0) for s0, s1 in ROUTE_FLOORS] + [(s - LOG_HALF, s + LOG_HALF, 14.0) for s in LOGS]:
        x, y = road.point((s0 + s1) / 2.0)
        floor = spawn(unreal.StaticMeshActor, x, y, PAD_TOP - 100.0 - sink, "RouteFloor", folder, road.yaw(s0))
        floor.set_actor_scale3d(unreal.Vector((s1 - s0) / 100.0, (ROUTE_FENCE + 10.0) * 2.0 / 100.0, 2.0))
        floor.static_mesh_component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Cube"))
        floor.static_mesh_component.set_material(0, materials["moss"])
        floor.static_mesh_component.set_collision_profile_name("BlockAll")
    for side in (-1.0, 1.0):
        route_fence(*road.point(ROUTE_FLOORS[0][0], side * ROUTE_FENCE), *road.point(ROUTE_FLOORS[-1][1], side * ROUTE_FENCE), materials)
        # Each end flares out to the road's full width, so the ball is led in and not stopped by a post.
        route_fence(*road.point(ROUTE_FLOORS[0][0] - 180.0, side * (LANE - 40.0)), *road.point(ROUTE_FLOORS[0][0], side * ROUTE_FENCE), materials)
        route_fence(*road.point(ROUTE_FLOORS[-1][1], side * ROUTE_FENCE), *road.point(ROUTE_FLOORS[-1][1] + 180.0, side * (LANE - 40.0)), materials)
    ridge_rock = mesh("SM_RockPack_Cliff_07_B")

    # Giant roots across the dome, and rock and waterfalls around its foot. Nothing here is solid.
    for s, turn, scale, up in ((20300.0, 20.0, 2.1, 300.0), (21700.0, -25.0, 2.3, 250.0)):
        x, y = road.point(s)
        mesh_actor(WORLD_MESHES["root_arch"], x, y, CAVERN_FLOOR + up, folder, (scale, scale, scale * 0.9), road.yaw(s) + turn, materials["bark"], "CavernRoot")
    for step in range(16):
        phi = 2.0 * math.pi * step / 16.0
        s = centre_s + half_s * 0.97 * math.cos(phi)
        d = half_d * 0.97 * math.sin(phi)
        if abs(d) < 1000.0:
            continue
        x, y = road.point(s, d)
        scale = rng.uniform(1.1, 1.6)
        mesh_actor(ridge_rock, x, y, CAVERN_FLOOR - 50.0 - base_height_offset(unreal.load_asset(ridge_rock), scale), folder, (scale, scale, scale), rng.uniform(0, 360), label="CavernShore")
    for s, d, high, yaw in ((20200.0, 2850.0, 1100.0, 0.0), (21750.0, 2750.0, 1300.0, -20.0), (20900.0, -2950.0, 1200.0, 10.0)):
        x, y = road.point(s, d)
        fall = mesh_actor("/Engine/BasicShapes/Plane", x, y, CAVERN_WATER + high / 2.0, folder, (high / 100.0, 3.0, 1.0), road.yaw(s) + yaw, materials["waterfall"], "Waterfall", pitch=90.0)
        fall.static_mesh_component.set_cast_shadow(False)

    # Jungle growth wherever there is rock to hold it.
    plants = Scatter("Cavern_Plants", 7000, 9000, shadows=False)
    jungle = ["SM_Fern", "SM_Fern", "SM_Clover", "SM_Fol_Plant_1", "SM_Fol_Plant_5", "SM_Fol_Plant_9", "SM_Fol_Plant_14", "SM_Fol_Grass_Clump_3"]
    for _ in range(40):
        # Outside the fence, on the rock under the sun.
        angle, distance = rng.uniform(0.0, 2.0 * math.pi), SUN_PAD_RADIUS * rng.uniform(0.72, 1.0)
        s, d = CAVERN[0] + math.cos(angle) * distance, math.sin(angle) * distance
        if abs(d) > ROUTE_FENCE + 40.0:
            plants.add(mesh(rng.choice(jungle)), *road.point(s, d), PAD_TOP - 5.0, rng.uniform(0.9, 1.5), rng, sink=2.0)
    for s0, s1 in TUNNELS:
        for side in (-1.0, 1.0):
            d0, d1 = (610.0, 790.0) if side > 0 else (-790.0, -610.0)
            for x, y, s in along_road(s0 + 150.0, s1 - 50.0, d0, d1, 95.0, rng):
                ground_s, ground_d = road.project(x, y)
                plants.add(mesh(rng.choice(jungle)), x, y, road_height(ground_s, ground_d, x, y), rng.uniform(0.8, 1.3), rng, sink=2.0)
    plants.build()

    # Sun through the hole: a real light, shafts you can see, and dust drifting in them.
    x, y = road.point(centre_s)
    top = CAVERN_FLOOR + CAVERN_HIGH
    sun = spawn(unreal.SpotLight, x, y, top + 200.0, "CavernSun", folder, 0.0, -90.0)
    component = sun.get_component_by_class(unreal.SpotLightComponent)
    component.set_mobility(unreal.ComponentMobility.MOVABLE)
    component.set_intensity_units(unreal.LightUnits.CANDELAS)
    component.set_intensity(9000.0)
    component.set_light_color(unreal.LinearColor(1.0, 0.82, 0.55, 1.0))
    component.set_attenuation_radius(4000.0)
    component.set_inner_cone_angle(14.0)
    component.set_outer_cone_angle(24.0)
    component.set_cast_shadows(True)
    for width, pitch, yaw, high, up in ((1.0, 0.0, 0.0, 1.0, 960.0), (0.55, 4.0, 40.0, 0.92, 950.0), (0.45, -5.0, 200.0, 0.85, 80.0)):
        shaft = mesh_actor(WORLD_MESHES["shaft"], x, y, top + up, folder, (width, width, high), yaw, materials["sun_shaft"], "SunShaft", pitch=pitch)
        shaft.static_mesh_component.set_cast_shadow(False)
    niagara("/Game/FreeParticle_SoftTofu/Niagara/NS_Sparkling_Noise", x, y, PAD_TOP + 300.0, folder, 8.0)
    rock_pad(centre_s, 0.0, SUN_PAD_RADIUS, materials, top=PAD_TOP - 5.0)

    # Soft green bounce, as if the light came through leaves, and lanterns to mark the way.
    for s, d in ((20300.0, 1600.0), (21500.0, 1500.0), (20300.0, -1500.0), (21500.0, -1500.0), (21000.0, 0.0)):
        x, y = road.point(s, d)
        point_light(x, y, 1100.0, unreal.LinearColor(0.5, 1.0, 0.4, 1.0), 38.0, 2600.0, folder)
    # A line of lanterns on both fences, in colour against the grey, with the brightest light at the way out.
    for index, s in enumerate((19700.0, 20180.0, 20660.0, 21140.0, 21620.0, 22100.0, 22320.0)):
        for side in (-1.0, 1.0):
            x, y = road.point(s, side * ROUTE_FENCE)
            globe = mesh_actor("/Engine/BasicShapes/Sphere", x, y, PAD_TOP + 275.0, folder, (0.3, 0.3, 0.3), material=materials["lantern"], label="Lantern")
            globe.static_mesh_component.set_render_custom_depth(True)
            globe.static_mesh_component.set_custom_depth_stencil_value(ls_world_common.FULL_COLOUR_STENCIL)
        x, y = road.point(s)
        point_light(x, y, PAD_TOP + 300.0, unreal.LinearColor(1.0, 0.6, 0.25, 1.0), 40.0, 900.0, folder)
    x, y = road.point(22500.0)
    point_light(x, y, level(22500.0) + 400.0, unreal.LinearColor(1.0, 0.7, 0.35, 1.0), 120.0, 1800.0, folder)


def rootwood_hollow(materials):
    """Zone 1-2: a closed cave of roots and teal light, a gate, then the great cavern, then another tunnel out to daylight."""
    folder = "Zone 1-2"
    rng = random.Random(SEED + 7)
    build_cave(materials)
    build_cavern(materials)

    # Great roots arching overhead, made narrower to fit the tunnels. They have no collision and clear the highest jump.
    arches = []
    for s0, s1 in ((15450.0, 19050.0), (22600.0, 25700.0)):
        s = s0
        while s < s1:
            arches.append(s)
            s += rng.uniform(520.0, 780.0)
    for s in arches:
        x, y = road.point(s)
        mesh_actor(WORLD_MESHES["root_arch"], x, y, level(s) - 10.0, folder, (1.0, TUNNEL_HALF / 1300.0, 0.95), road.yaw(s) + rng.uniform(-8.0, 8.0), materials["bark"], "RootArch")

    # Without the sky, the tunnels would be black. Teal light from the mushrooms keeps the road readable.
    for s0, s1 in TUNNELS:
        s = s0 + 600.0
        while s < s1:
            x, y = road.point(s)
            point_light(x, y, level(s) + 500.0, unreal.LinearColor(0.2, 0.95, 0.75, 1.0), 5.0, 1100.0, folder)
            s += 900.0

    # A log chute guides the block onto its plate and stops it just past, so it can't be pushed out of reach. The ball can't slip past the block in there,
    # and the road stays open on both sides of the chute.
    def chute_log(s0, d0, s1, d1):
        x0, y0 = road.point(s0, d0)
        x1, y1 = road.point(s1, d1)
        top = level(s0)
        invisible_wall(x0, y0, x1, y1, top - 50.0, top + 120.0, folder)
        length = math.hypot(x1 - x0, y1 - y0)
        mesh_actor(WORLD_MESHES["log"], x0, y0, top + 28.0, folder, (length / 800.0, 0.75, 0.75), math.degrees(math.atan2(y1 - y0, x1 - x0)), materials["bark"], "ChuteLog")

    for side in (-1.0, 1.0):
        chute_log(BLOCK_S - 120.0, side * 150.0, PLATE_S + 130.0, side * 150.0)
        chute_log(BLOCK_S - 300.0, side * 280.0, BLOCK_S - 120.0, side * 150.0)
    chute_log(PLATE_S + 130.0, -150.0, PLATE_S + 130.0, 150.0)

    # A frame of logs around the plank gate, and planks above it up to the roof.
    s = to_road(14800.0)
    for side in (-1, 1):
        x, y = road.point(s, side * 730.0)
        mesh_actor(WORLD_MESHES["log"], x, y, level(s) - 40.0, folder, (1.5, 1.5, 1.2), rng.uniform(0, 360), materials["bark"], "GatePost", pitch=90.0)
    x, y = road.point(s, -900.0)
    mesh_actor(WORLD_MESHES["log"], x, y, level(s) + 660.0, folder, (2.3, 1.4, 1.4), road.yaw(s) + 90.0, materials["bark"], "GateLintel")
    x, y = road.point(s - 70.0)
    mesh_actor("/Engine/BasicShapes/Cube", x, y, level(s) + 830.0, folder, (0.2, 16.4, 3.6), road.yaw(s), materials["planks"], "GateTop")

    # A grade for each stretch, as a box can't bend with the road. Inside, auto exposure already brightens the picture, so these only add the mood.
    tint = unreal.LinearColor(0.72, 0.92, 0.9, 1.0)
    for s0, s1, tone, exposure in ((14300.0, 19550.0, tint, -0.4), (22250.0, 23800.0, tint, -0.4), (23600.0, 25900.0, tint, -0.4)):
        middle = (s0 + s1) / 2.0
        x, y = road.point(middle)
        zone_grade(x, y, level(middle) + 800.0, (s1 - s0) / 2.0 + 200.0, 1400.0, 1600.0, road.yaw(middle), exposure, tone, "TunnelGrade")
    x, y = road.point(CAVERN[0])
    zone_grade(x, y, 1100.0, CAVERN[1], CAVERN[2], 1300.0, road.yaw(CAVERN[0]), -0.2, unreal.LinearColor(0.92, 1.0, 0.8, 1.0), "CavernGrade")


def stilt_platform(s, d, top, size, materials, rng, folder):
    """A ruined deck on leaning posts, standing in the water away from the road."""
    x, y = road.point(s, d)
    yaw = rng.uniform(0.0, 360.0)
    mesh_actor("/Engine/BasicShapes/Cube", x, y, top, folder, (size / 100.0, size * 0.7 / 100.0, 0.25), yaw, materials["planks"], "StiltDeck")
    turned = math.radians(yaw)
    for along, side in ((-0.4, -0.3), (-0.4, 0.3), (0.4, -0.3), (0.4, 0.3)):
        px = x + size * (along * math.cos(turned) - side * math.sin(turned))
        py = y + size * (along * math.sin(turned) + side * math.cos(turned))
        mesh_actor(WORLD_MESHES["log"], px, py, WATER_LEVEL - 80.0, folder, ((top - WATER_LEVEL + 80.0) / 800.0, 0.5, 0.5), rng.uniform(0.0, 360.0), materials["bark"], "StiltPost", pitch=rng.uniform(84.0, 90.0))


def post_pad(s, d, top, size, materials, rng, folder):
    """A lily pad held up on a post, out of reach, for depth."""
    x, y = road.point(s, d)
    mesh_actor("/Engine/BasicShapes/Cylinder", x, y, top, folder, (size / 50.0, size / 50.0, 0.1), rng.uniform(0.0, 360.0), materials["pad"], "PostPad")
    mesh_actor(WORLD_MESHES["log"], x, y, WATER_LEVEL - 80.0, folder, ((top - WATER_LEVEL + 80.0) / 800.0, 0.7, 0.7), rng.uniform(0.0, 360.0), materials["bark"], "PadPost", pitch=90.0)


def thornmire_marsh(materials):
    """Zone 1-3, after picture 3: open misty water, giant mossy trees on their roots, thorns along the way, and a glowing tree in an arch at the end."""
    folder = "Zone 1-3"
    rng = random.Random(SEED + 11)
    mesh_actor(WORLD_MESHES["water"], 0.0, 0.0, 0.0, folder, material=unreal.load_asset("/Game/Stylized_PBR_Nature/Terrain/M_Water_Basic"), label="SwampWater")

    # The giants. Their roots reach 1500 cm at full size, so each stands far enough out to keep them off the road.
    for s, d, scale in ((28350.0, -2300.0, 1.0), (29500.0, 3000.0, 0.85), (30900.0, -3100.0, 0.95), (31900.0, 2500.0, 0.75),
                        (33300.0, 2700.0, 0.8), (34700.0, -2100.0, 0.7), (35600.0, 3400.0, 0.9), (36700.0, -2600.0, 0.8)):
        x, y = road.point(s, d)
        yaw = rng.uniform(0.0, 360.0)
        z = WATER_LEVEL - 70.0
        mesh_actor(WORLD_MESHES["tree"], x, y, z, folder, (scale, scale, scale), yaw, materials["bark"], "SwampGiant")
        mesh_actor(WORLD_MESHES["moss"], x, y, z, folder, (scale, scale, scale), yaw, materials["moss_strand"], "SwampMoss")

    # Dead trees further out in the water, thinning into the mist.
    drowned = Scatter("Swamp_Drowned", 26000, 36000)
    for x, y in jittered_grid(*road_box(SWAMP[0], SWAMP[1], SWAMP_WIDTH), 620.0, rng):
        s, d = road.project(x, y)
        if 1100.0 < abs(d) < SWAMP_WIDTH and swamp_amount(min(max(s, 0.0), ROAD_LENGTH)) > 0.3 and rng.random() < 0.55:
            drowned.add(mesh(rng.choice(["SM_Fruit_Tree_01_dead", "SM_Pine_Tree_03_dead", "SM_Fruit_Tree_01_dead_cut", "SM_Pine_Tree_03_stump"])), x, y, terrain_height(x, y), rng.uniform(1.0, 1.9), rng, sink=10.0, tilt=7.0)
    drowned.build()

    # Roots wrap the sides of the raised path, and a line of brambles marks where the ball can't go.
    roots = Scatter("Swamp_Roots", 14000, 19000, material=materials["bark"])
    brambles = Scatter("Swamp_Brambles", 12000, 16000, material=materials["bark"])
    blooms = Scatter("Swamp_Blooms", 7000, 9000, shadows=False, stencil=True)
    s = SWAMP[0] + 900.0
    while s < SWAMP[1] - 400.0:
        for side in (-1, 1):
            if s < MARSH[1]:
                brambles.add(WORLD_MESHES["bramble"], *road.point(s, side * (EDGE + rng.uniform(40.0, 150.0))), WATER_LEVEL - 25.0, rng.uniform(0.55, 0.95), rng, sink=0.0, tilt=8.0)
            else:
                # Scatter rests a mesh's lowest point on the ground it is given, and these should hang from the road's edge.
                size = rng.uniform(0.9, 1.4)
                roots.add(WORLD_MESHES["roots"], *road.point(s, side * (EDGE + 130.0)), level(s) + 25.0 + base_height_offset(unreal.load_asset(WORLD_MESHES["roots"]), size), size, rng, sink=0.0)
                brambles.add(WORLD_MESHES["bramble"], *road.point(s + 120.0, side * (EDGE + rng.uniform(180.0, 300.0))), WATER_LEVEL - 25.0, rng.uniform(0.8, 1.3), rng, sink=0.0, tilt=8.0)
                if rng.random() < 0.3:
                    blooms.add(mesh(rng.choice(LIVING_FLOWERS[:4])), *road.point(s, side * (LANE - rng.uniform(0.0, 50.0))), level(s), rng.uniform(0.6, 1.0), rng, sink=2.0)
        s += rng.uniform(190.0, 300.0)

    # The pit under each glide is full of thorns, so a miss looks like the danger it is.
    pit = Scatter("Pit_Brambles", 14000, 19000, material=materials["bark"])
    for gap0, gap1 in GAPS[3:]:
        for s, d in jittered_grid(gap0 - 50.0, gap1 + 50.0, -1700.0, 1700.0, 230.0, rng):
            pit.add(WORLD_MESHES["bramble"], *road.point(s, d), level(gap0) - rng.uniform(560.0, 720.0), rng.uniform(1.6, 2.6), rng, sink=0.0, tilt=14.0)
        # Leaves on the wind the glide rides, as in picture 3.
        for d in (-350.0, 350.0):
            niagara("/Game/FreeParticle_SoftTofu/Niagara/NS_leaf", *road.point((gap0 + gap1) / 2.0 + d, d), level(gap0) - 120.0, folder, 2.5)
    pit.build()
    roots.build()
    brambles.build()
    blooms.build()

    # Posts beside each lily pad, as if something once tied them here.
    for actor in actors_of("SinkingPad"):
        location = actor.get_actor_location()
        s, d = road.project(location.x, location.y)
        px, py = road.point(s + rng.uniform(-80.0, 80.0), d + (190.0 if d >= 0.0 else -190.0))
        mesh_actor(WORLD_MESHES["log"], px, py, WATER_LEVEL - 80.0, folder, (0.33, 0.5, 0.5), rng.uniform(0.0, 360.0), materials["bark"], "PadMooring", pitch=rng.uniform(80.0, 90.0))

    # Out of reach, for depth: pads on posts, ruined decks, and roots arching across the water like bridges.
    for _ in range(26):
        s, d = rng.uniform(MARSH[0] - 300.0, 36500.0), rng.choice((-1.0, 1.0)) * rng.uniform(1000.0, 3600.0)
        post_pad(s, d, WATER_LEVEL + rng.uniform(40.0, 260.0), rng.uniform(130.0, 260.0), materials, rng, folder)
    for s, d, top, size in ((28900.0, 1900.0, 620.0, 520.0), (30100.0, -1700.0, 700.0, 460.0), (31500.0, 3500.0, 760.0, 620.0), (32200.0, -3600.0, 680.0, 540.0),
                            (33800.0, 1800.0, 780.0, 480.0), (35000.0, 2300.0, 830.0, 560.0), (36100.0, -1600.0, 740.0, 500.0)):
        stilt_platform(s, d, top, size, materials, rng, folder)
    for s, d, turn, scale in ((29400.0, -1800.0, 72.0, 1.6), (30600.0, 2200.0, -76.0, 1.5), (32300.0, 1900.0, 65.0, 1.3), (33900.0, -1700.0, -70.0, 1.2), (35900.0, 1800.0, 70.0, 1.4)):
        x, y = road.point(s, d)
        mesh_actor(WORLD_MESHES["root_arch"], x, y, WATER_LEVEL - 40.0, folder, (scale, scale, scale * 0.7), road.yaw(s) + turn, materials["bark"], "RootBridge")
    # Three great roots over the way itself, too high to reach.
    for s in (27950.0, 33000.0, 36300.0):
        x, y = road.point(s)
        mesh_actor(WORLD_MESHES["root_arch"], x, y, level(s) - 10.0, folder, (1.2, 0.9, 1.1), road.yaw(s) + rng.uniform(-8.0, 8.0), materials["bark"], "RootArch")

    # Local Fog Volumes only start 20 m from the camera, so the mist around the ball is made from sheets instead.
    for up in MIST_LAYERS:
        mesh_actor(WORLD_MESHES["mist"], 0.0, 0.0, up, folder, material=materials["mist"], label="SwampMist").static_mesh_component.set_cast_shadow(False)

    # The cold grey of the marsh, a stretch at a time, as a box can't bend with the road.
    tint = unreal.LinearColor(0.8, 0.9, 0.93, 1.0)
    for s0, s1 in ((27200.0, 32700.0), (32700.0, 34800.0), (34800.0, 37400.0)):
        middle = (s0 + s1) / 2.0
        x, y = road.point(middle)
        zone_grade(x, y, 1500.0, (s1 - s0) / 2.0 + 1500.0, 7000.0, 3000.0, road.yaw(middle), -0.25, tint, "MarshGrade")

    # The goal: a glowing tree in a ring, set into a spire of rock at the road's end.
    s = ROAD_LENGTH + 420.0
    x, y = road.point(s)
    z = level(ROAD_LENGTH)
    yaw = road.yaw(ROAD_LENGTH)
    ring_middle = z + 720.0
    ring = mesh_actor(WORLD_MESHES["ring"], x, y, ring_middle, folder, (2.1, 2.1, 2.1), yaw, materials["goal_glow"], "GoalRing")
    tree = mesh_actor(WORLD_MESHES["tree"], *road.point(s + 20.0), z + 110.0, folder, (0.27, 0.27, 0.27), yaw, materials["goal_glow"], "GoalTree")
    for glowing in (ring, tree):
        glowing.static_mesh_component.set_render_custom_depth(True)
        glowing.static_mesh_component.set_custom_depth_stencil_value(ls_world_common.FULL_COLOUR_STENCIL)
    for s_rock, d, name, scale, up in ((s + 2200.0, 0.0, "SM_RockPack_Cliff_07_B", 2.6, -200.0), (s + 300.0, -2300.0, "SM_RockPack_Cliff_07_D", 2.2, -150.0), (s + 300.0, 2300.0, "SM_RockPack_Cliff_07_D", 2.2, -150.0),
                                       (s + 1200.0, -1500.0, "SM_S_Rock_10", 4.0, -100.0), (s + 1200.0, 1600.0, "SM_S_Rock_04", 4.0, -100.0)):
        path = mesh(name)
        rock_x, rock_y = road.point(s_rock, d)
        mesh_actor(path, rock_x, rock_y, z + up - base_height_offset(unreal.load_asset(path), scale), folder, (scale, scale, scale), yaw + rng.uniform(-30.0, 30.0))
    for side in (-1, 1):
        arch_x, arch_y = road.point(s - 380.0, side * 1050.0)
        mesh_actor(WORLD_MESHES["root_arch"], arch_x, arch_y, z - 30.0, folder, (1.0, 0.75, 1.1), yaw + side * 58.0, materials["bark"], "GoalRoot")
    point_light(*road.point(s - 250.0), ring_middle, unreal.LinearColor(1.0, 0.62, 0.2, 1.0), 110.0, 3200.0, folder)
    niagara("/Game/FreeParticle_SoftTofu/Niagara/NS_Sparkling_Glow", *road.point(s - 60.0), ring_middle - 100.0, folder, 5.0)


def rock_set_pieces():
    """Cliffs where the player should feel enclosed, and at each edge the eye is drawn to."""
    folder = "Set Pieces"

    def rock(name, s, d, height_offset, scale, yaw=0.0):
        path = mesh(name)
        loaded = unreal.load_asset(path)
        x, y = road.point(s, d)
        return mesh_actor(path, x, y, terrain_height(x, y) + height_offset - base_height_offset(loaded, scale), folder, (scale, scale, scale), yaw)

    # The road to the cave: high walls on either side.
    rng = random.Random(SEED + 2)
    s = 13000.0
    while s < 14200.0:
        for side in (-1, 1):
            rock(rng.choice(["SM_RockPack_Cliff_07_B", "SM_RockPack_Cliff_07_D", "SM_S_Rock_10", "SM_S_Rock_04"]),
                 s + rng.uniform(-150, 150), side * rng.uniform(1350, 1800), -40.0, rng.uniform(0.8, 1.3), rng.uniform(0, 360))
        s += 600.0

    # Rock under each lip of a gap, so the chasm has a real edge and not a sheer cut in the ground.
    for gap0, gap1 in GAPS:
        if (gap0, gap1) == CAVERN_GAP:
            continue
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


def build_boundaries():
    top = 4500.0
    bottom = -1400.0
    for side in (-1, 1):
        s = -50.0
        while s < ROAD_LENGTH + 50.0:
            following = s + 400.0
            # The right-hand wall has openings where a side area leads to a hidden petal.
            middle = (s + following) / 2.0
            over_cavern = CAVERN_GAP[0] < middle < CAVERN_GAP[1]
            if not over_cavern and (side < 0 or not any(abs(middle - s0) < half + 200.0 for s0, half, _, _ in POCKETS)):
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
        if (gap0, gap1) not in (ISLAND_CHAIN, CAVERN_GAP):
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
        if (gap0, gap1) == CAVERN_GAP:
            continue
        x, y = road.point(gap1 + 150.0)
        point_light(x, y, level(gap1) + 300.0, warm, 45.0, 1500.0)


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
               camera("Preview_1_1_G", 6300.0, 0.0, 420.0, 7500.0, 0.0, -300.0),   # The lava pit, from the road.
               camera("Preview_1_1_H", 7700.0, 2600.0, 1500.0, 7700.0, 0.0, -300.0),   # The lava pit, from above.
               camera("Preview_1_1_I", 5800.0, -5000.0, 4200.0, 7900.0, 0.0, -300.0),   # The whole lava river.
               camera("Preview_1_1_F", 2800.0, -1200.0, 300.0, 4000.0, -3400.0, 500.0),   # Waterfalls.
               camera("Preview_1_2_D", 13500.0, 0.0, 240.0, 14500.0, 0.0, 300.0),   # The blocked cave.
               camera("Preview_1_2_E", 14900.0, -150.0, 170.0, 16000.0, 80.0, 180.0),   # Inside the tunnel.
               camera("Preview_1_2_F", 16400.0, 200.0, 330.0, 18000.0, 0.0, 0.0),   # The block, its chute and the plate.
               camera("Preview_1_2_G", 18300.0, 300.0, 210.0, 19200.0, 0.0, 250.0),   # The plank gate.
               camera("Preview_1_2_H", 19450.0, 0.0, 320.0, 21000.0, 0.0, 200.0),   # The cavern from its entrance.
               camera("Preview_1_2_I", 19600.0, 0.0, 260.0, 20700.0, 0.0, 60.0),   # The first tilting log.
               camera("Preview_1_2_J", 20500.0, 900.0, 420.0, 21300.0, 0.0, 200.0),   # The walkway under the sun shaft.
               camera("Preview_1_2_K", 21000.0, 0.0, 240.0, 22400.0, 0.0, 120.0),   # The second tilting log and the way out.
               camera("Preview_1_2_L", 23300.0, -200.0, 200.0, 24500.0, 0.0, 150.0),   # The thorn tunnel.
               camera("Preview_1_3_D", 27950.0, -120.0, 150.0, 30500.0, 300.0, 250.0),   # The marsh from the lane, like picture 3.
               camera("Preview_1_3_E", 33100.0, 200.0, 230.0, 34800.0, -300.0, 60.0),   # The raised path and its blobs.
               camera("Preview_1_3_F", 39600.0, 0.0, 450.0, 40400.0, 0.0, -500.0),   # The glide over the thorn pit.
               camera("Preview_1_3_G", 43000.0, 0.0, 260.0, 45100.0, 0.0, 600.0),   # The goal.
               camera("Preview_1_3_H", 33500.0, 400.0, 110.0, 33500.0, -300.0, 40.0),   # A blob up close.
               camera("Preview_Route", 20000.0, -18000.0, 22000.0, 20000.0, 0.0, 0.0)]
    for name, s0, s1 in ZONES[1:]:
        middle = (s0 + s1) / 2.0
        cameras.append(camera("Preview_{}_A".format(name), s0 + 400.0, -200.0, 220.0, s0 + 2800.0, 0.0, 120.0))
        cameras.append(camera("Preview_{}_B".format(name), middle, 420.0, 170.0, middle - 2200.0, -400.0, 300.0))
        cameras.append(camera("Preview_{}_C".format(name), middle - 1800.0, -7000.0, 4200.0, middle + 1000.0, 0.0, 0.0))
    return cameras


def check_layout():
    """Stops the build if an edit to the tables above broke a rule the level depends on."""
    for s in range(0, int(ROAD_LENGTH), 100):
        if not ISLAND_CHAIN[0] <= s <= ISLAND_CHAIN[1]:
            for d in (-ROAD_SIDE, 0.0, ROAD_SIDE):
                assert not in_river(*road.point(s, d)), "the lava river runs into the road at s = {}".format(s)
    assert abs(to_road(32200.0) - ROAD_LENGTH) < 1.0, "the inserts and ROAD_LENGTH disagree"
    for x in (0.0, 5000.0, 12100.0, 14800.0, 22600.0, 31700.0):
        assert abs(greybox_x(to_road(x)) - x) < 1.0, x
    for s in range(100, int(ROAD_LENGTH), 100):
        if has_road(s) and has_road(s + 100):
            slope = abs(level(s + 100) - level(s)) / 100.0
            # 14 degrees is the steepest ramp the greybox already has.
            assert slope < 0.26, "too steep at s = {}: {:.2f}".format(s, slope)
    for s0, s1, _ in BENDS:
        for gap0, gap1 in [(3300.0, 4100.0), (14000.0, 16000.0), (16600.0, 22500.0), (MARSH[0], MARSH[1])]:
            assert s1 <= gap0 or s0 >= gap1, "a bend overlaps a section that must stay straight: {}".format((s0, s1))
    for i in range(0, int(ROAD_LENGTH), 300):
        for j in range(i + 4000, int(ROAD_LENGTH), 300):
            a, b = road.point(i), road.point(j)
            assert math.hypot(a[0] - b[0], a[1] - b[1]) > ROAD_SIDE * 2.0, "the road runs into itself at {} and {}".format(i, j)


def apply_hand_edits():
    """Repeats what was moved, deleted or added by hand in the editor, so a rebuild keeps it. level1_edits.json lists each one against where the build puts it."""
    edits = json.load(open(os.path.join(unreal.Paths.project_content_dir(), "Python", "level1_edits.json"), encoding="utf-8"))
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    live = list(actors.get_all_level_actors())

    def take(label, class_name, at):
        for actor in live:
            location = actor.get_actor_location()
            if actor.get_actor_label() == label and actor.get_class().get_name() == class_name and math.dist((location.x, location.y, location.z), at) < 5.0:
                live.remove(actor)
                return actor
        return None

    missing = 0
    for edit in edits["remove"]:
        actor = take(edit["label"], edit["cls"], edit["at"])
        if actor:
            actors.destroy_actor(actor)
    for edit in edits["change"]:
        actor = take(edit["label"], edit["cls"], edit["from"])
        if not actor:
            missing += 1
            continue
        actor.set_actor_location(unreal.Vector(*edit["loc"]), False, False)
        actor.set_actor_rotation(unreal.Rotator(*edit["rot"]), False)
        actor.set_actor_scale3d(unreal.Vector(*edit["scale"]))
    for edit in edits["add"]:
        # What was added by hand has no build tag, so in the map it was made in, it survives a rebuild by itself.
        if take(edit["label"], "StaticMeshActor", edit["loc"]):
            continue
        added = spawn(unreal.StaticMeshActor, *edit["loc"], edit["label"], "Hand Edits")
        added.set_actor_rotation(unreal.Rotator(*edit["rot"]), False)
        added.set_actor_scale3d(unreal.Vector(*edit["scale"]))
        added.static_mesh_component.set_static_mesh(unreal.load_asset(mesh(edit["mesh"])))
    unreal.log("Last Seed world: hand edits applied: {} removed, {} changed ({} not found), {} added".format(len(edits["remove"]), len(edits["change"]), missing, len(edits["add"])))


def solid_cliffs():
    """Every Cliff_07 is a real obstacle, whoever placed it. The Fab mesh already has simple collision shapes, and the Fab folder itself isn't changed."""
    count = 0
    for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        if isinstance(actor, unreal.StaticMeshActor) and actor.static_mesh_component.static_mesh and actor.static_mesh_component.static_mesh.get_name().startswith("SM_RockPack_Cliff_07"):
            actor.static_mesh_component.set_collision_profile_name("BlockAll")
            count += 1
    unreal.log("Last Seed world: {} cliffs made solid".format(count))


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

    build_island_chain(materials)
    dress_greybox(materials, added)
    scatter_rings(materials)
    living_start()
    awakening_grove_landmarks(materials)
    rootwood_hollow(materials)
    thornmire_marsh(materials)
    rock_set_pieces()
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
    apply_hand_edits()
    solid_cliffs()
    report(world_path)
    take_preview_screenshots(cameras)


main()
