# Last Seed - plans Level 1 on the Wildwood landscape: the trail, its parkour, and the forest around it.
#
# Purpose: runs outside Unreal (it needs numpy and Pillow, which the editor's Python lacks). It reads the landscape
# heights and foliage exported from the Wildwood map, and writes:
#   SM_LS_WildwoodTrail_*.obj  the walkable trail, as mesh pieces laid on the landscape
#   plan.json        every set piece, pickup and volume to place, and the trees that become regrowing trees
#   foliage_new.json the Wildwood foliage without what stood on the trail
#   preview.png      a map of the route, and profile.png its height along the way, for checking by eye
# How the trail works: a smooth curve through hand-placed control points, chosen to keep to the gentler slopes. The
# trail is a dirt ribbon that hugs the ground, with at most a short, grassy fill where a bump is too sharp to roll over.
# Where the ground climbs too steeply, rocks stand on the trail as stairs. The parkour is all stone, wood and rock:
# stepping stones, logs and platforms over the three water crossings, a rock tower to glide from, and rocks to climb.
# Run: python ls_wildwood_plan.py (from Content/Python). Same input always gives the same output.

import json
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw
from ls_widen_opening import opening_padding

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.normpath(os.path.join(HERE, "..", "..", "Saved", "LS"))

# The landscape's grid, from its actor transform: 39.35 cm per quad, first vertex at (X0, Y0).
CELL = 39.3543313
X0 = -49980.0 + 381 * CELL
Y0 = -49980.0 + 635 * CELL
Z_UNIT = 100.0 / 128.0  # cm per height unit
WATER = 1990.0  # The Wildwood water plane covers the whole map at this height.

LANE = 320.0  # Half the trail's width.
CLEAR = 8.0  # How far the trail floats over the ground, so the landscape never pokes through.
MAX_GRADE = math.tan(math.radians(11.0))  # Steeper bumps get a little fill, up to FILL_CAP.
FILL_CAP = 200.0  # The most the trail ever stands above the ground. Higher than this, rocks make stairs instead.
STAIR_GRADE = math.tan(math.radians(15.0))  # Climbs steeper than this get rock stairs.
STAIR_RISE = 100.0  # Each stair is at most this much above the last. Seed jumps about 250.
CROWN = 0.03  # The lane falls 3 cm per metre from the middle, as a real path does.
BANK = 0.5  # Past the lane's edge, a fill slopes down 1 cm per 2 cm outward, under grass.
SMOOTH = 350.0  # How far along the trail small bumps are averaged, in cm.
STEP = 25.0  # Sample spacing along the trail.
SEED = 4127

# --- The route ---
# Control points in cm, in walking order. A name marks a point that set pieces below refer to. A name ending in _end
# closes a water crossing opened by the same name without it: there the trail stops, and stones carry on.
ROUTE = [
    # 1-1 Awakening Glade: down the gentle west bank to the gorge.
    (-23000, 17200, "start"), (-24600, 14600, None), (-24400, 12000, "jump1"), (-24800, 9000, None), (-23600, 6000, "ledges"),
    (-21500, 3200, None), (-19500, 0, None), (-18400, -3600, None), (-17900, -6000, None),
    # Over the gorge on rock stacks, a fallen log and a tipping log, bank top to bank top.
    (-17100, -7000, "cross1"), (-13300, -7000, "cross1_end"),
    # 1-2 Rootwood Heights: up onto the island. Stone Shell, the wall, the plate puzzle, then Dandelion.
    (-11500, -6300, None), (-10000, -4300, None), (-7600, -2600, "stone"), (-6300, 0, "wall"), (-3800, 1600, "plates"),
    (-900, 700, None), (2000, -1000, None), (5000, -1500, None), (7100, -900, None), (8000, 2500, "dandelion"), (10300, 3600, None),
    # 1-3 Bloom Ridge: an updraft up a rock tower, a glide over the river, Wither Blobs, the last river, the hill.
    (12000, 1600, "glide"), (14900, -2200, "glide_end"), (16700, -800, "blobs"), (19000, 1300, None), (21000, 1800, None),
    (21900, 3000, None), (21500, 4100, "cross3"), (18800, 7300, "cross3_end"), (17500, 9200, "climb"), (15500, 10500, "goal"), (14000, 11000, None),
]


def catmull_rom(points, step):
    """A smooth curve through every control point, sampled every step cm. Centripetal, so it never loops or overshoots."""
    pts = np.array(points, float)
    pts = np.vstack([pts[0] * 2 - pts[1], pts, pts[-1] * 2 - pts[-2]])
    dense = []
    for k in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[k - 1], pts[k], pts[k + 1], pts[k + 2]
        t0 = 0.0
        t1 = t0 + np.linalg.norm(p1 - p0) ** 0.5
        t2 = t1 + np.linalg.norm(p2 - p1) ** 0.5
        t3 = t2 + np.linalg.norm(p3 - p2) ** 0.5
        n = max(int(np.linalg.norm(p2 - p1) / (step / 4.0)), 2)
        for t in np.linspace(t1, t2, n, endpoint=False):
            a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
            a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
            b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
            b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
            dense.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    dense.append(pts[-2])
    dense = np.array(dense)
    # Resample at an even spacing, so s is true distance along the trail.
    seg = np.linalg.norm(np.diff(dense, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    s = np.arange(0.0, cum[-1], step)
    return s, np.interp(s, cum, dense[:, 0]), np.interp(s, cum, dense[:, 1])


class Trail:
    def __init__(self, ground):
        self.ground = ground
        self.s, self.x, self.y = catmull_rom([(x, y) for x, y, _ in ROUTE], STEP)
        heading = np.unwrap(np.arctan2(np.gradient(self.y), np.gradient(self.x)))
        self.heading = heading
        # Where each named control point falls along the trail.
        self.mark = {}
        for x, y, name in ROUTE:
            if name:
                self.mark[name] = float(self.s[np.argmin((self.x - x) ** 2 + (self.y - y) ** 2)])

    def at(self, s):
        s = float(np.clip(s, 0.0, self.s[-1]))
        return float(np.interp(s, self.s, self.x)), float(np.interp(s, self.s, self.y))

    def yaw(self, s):
        return math.degrees(float(np.interp(s, self.s, self.heading)))

    def point(self, s, d=0.0):
        """A point d cm to the right of the trail at distance s."""
        x, y = self.at(s)
        h = math.radians(self.yaw(s))
        return x - d * math.sin(h), y + d * math.cos(h)

    def length(self):
        return float(self.s[-1])


def sample(grid, x, y):
    """Bilinear height from the landscape grid at world (x, y)."""
    fj = np.clip((np.asarray(x) - X0) / CELL, 0, grid.shape[1] - 1.001)
    fi = np.clip((np.asarray(y) - Y0) / CELL, 0, grid.shape[0] - 1.001)
    j, i = np.floor(fj).astype(int), np.floor(fi).astype(int)
    tj, ti = fj - j, fi - i
    return (grid[i, j] * (1 - tj) * (1 - ti) + grid[i, j + 1] * tj * (1 - ti) + grid[i + 1, j] * (1 - tj) * ti + grid[i + 1, j + 1] * tj * ti)


def highest_near(ground, radius=2):
    """Each landscape vertex replaced by the highest one within radius quads. A mesh laid on this, with its vertices
    closer together than that, never has the landscape poke through between them."""
    out = ground.copy()
    for di in range(-radius, radius + 1):
        for dj in range(-radius, radius + 1):
            out = np.maximum(out, np.roll(np.roll(ground, di, 0), dj, 1))
    return out


def smooth_along(values, sigma_cm):
    sigma = sigma_cm / STEP
    radius = int(3 * sigma)
    kernel = np.exp(-0.5 * (np.arange(-radius, radius + 1) / sigma) ** 2)
    kernel /= kernel.sum()
    padded = np.concatenate([np.full(radius, values[0]), values, np.full(radius, values[-1])])
    return np.convolve(padded, kernel, mode="valid")


# --- Set pieces, as distances from the named control points ---
CROSSINGS = [("cross1", "cross1_end"), ("glide", "glide_end"), ("cross3", "cross3_end")]
# Level stretches: (mark, start offset, end offset). Puzzles and arenas need flat ground. They were placed where the
# ground is nearly flat already, so the fill under them stays small.
FLATS = [("start", 0.0, 900.0), ("plates", 400.0, 3300.0), ("blobs", -600.0, 1700.0), ("goal", 0.0, 1600.0)]
# Where the trail and its walls stand wider, as (mark, start offset, end offset, half width).
WIDE = [("blobs", -1800.0, 1800.0, 1000.0), ("plates", -400.0, 3200.0, 800.0)]
CROSSING_HALF = 560.0  # Half the walled width over a crossing, so a stone's edge is never against a wall.
WALL_GAP = 70.0  # The hidden walls stand this far past the lane's edge.
WALL_HEIGHT = 2600.0  # Tall enough that a glide from the tower can't go over one.
# Hidden petals: (mark, offset, side). A gap in the wall on that side leads into a small pocket behind the scenery.
SECRETS = [("ledges", 1700.0, -1), ("plates", 500.0, -1), ("blobs", 1200.0, -1)]
POCKET = 1000.0
GLIDE_RATIO = 3.0  # Dandelion covers about 3.5 cm for each cm it falls. The tower allows for less, so the glide is easy.
TOWER_RADIUS = 400.0


def lane_halves(trail):
    """Half the lane's width at each sample: LANE, widened for an arena, a puzzle or a crossing, with a short ramp at
    each end, so the walls always stand just past the lane's edge."""
    halves = np.full(len(trail.s), LANE)
    zones = [(trail.mark[m] + a, trail.mark[m] + b, half) for m, a, b, half in WIDE]
    zones += [(trail.mark[a], trail.mark[b], CROSSING_HALF) for a, b in CROSSINGS]
    for start, end, half in zones:
        ramp = np.minimum(np.clip((trail.s - (start - 800.0)) / 800.0, 0, 1), np.clip(((end + 800.0) - trail.s) / 800.0, 0, 1))
        halves = np.maximum(halves, LANE + (half - LANE) * ramp)
    return halves


def raise_grade(z, breaks):
    """Raises the trail wherever it would be steeper than MAX_GRADE, never lowering it, except across a break."""
    rise = MAX_GRADE * STEP
    for k in range(1, len(z)):
        if not breaks[k]:
            z[k] = max(z[k], z[k - 1] - rise)
    for k in range(len(z) - 2, -1, -1):
        if not breaks[k + 1]:
            z[k] = max(z[k], z[k + 1] - rise)
    return z


def crossing_mask(trail):
    air = np.zeros(len(trail.s), bool)
    for a, b in CROSSINGS:
        air |= (trail.s >= trail.mark[a]) & (trail.s <= trail.mark[b])
    return air


def build_profile(trail, ground, high):
    """The trail's height down its middle: the ground, lightly smoothed, with a little fill where a bump is too sharp
    and level stretches for the puzzles and arenas. It never cuts into the landscape, and never stands more than
    FILL_CAP above it, so it always looks like a path worn into this forest."""
    s = trail.s
    halves = lane_halves(trail)
    centre = sample(high, trail.x, trail.y)
    side = lambda d: sample(high, trail.x - d * np.sin(trail.heading), trail.y + d * np.cos(trail.heading))
    # On a slope the middle sits at the average of the two sides, so the downhill half is level with a small fill
    # and the uphill half rises with the hill.
    base = np.maximum(centre, (side(-0.7 * halves) + side(0.7 * halves)) / 2.0) + CLEAR
    hugging = np.maximum(smooth_along(base, SMOOTH), centre + CLEAR)
    air = crossing_mask(trail)
    walk = hugging.copy()
    for mark, a, b in FLATS:
        m = trail.mark[mark]
        mask = (s >= m + a) & (s <= m + b) & ~air
        walk[mask] = walk[mask].max()
    ground_index = np.flatnonzero(~air)
    breaks = np.concatenate([[False], np.diff(ground_index) > 1])
    raised = raise_grade(walk[ground_index].copy(), breaks)
    walk[ground_index] = np.maximum(walk[ground_index], raised)
    # Never more than FILL_CAP over the ground, even in a hollow or under a puzzle. Too steep then means rock stairs.
    walk = np.minimum(walk, np.maximum(sample(ground, trail.x, trail.y) + FILL_CAP, centre + CLEAR))
    # Over a crossing nothing is laid. A straight line between the banks gives the stones their heights.
    edges = np.flatnonzero(np.diff(air.astype(int)))
    for start, stop in zip(edges[::2], edges[1::2]):
        walk[start:stop + 2] = np.linspace(walk[start], walk[stop + 1], stop - start + 2)
    floor = np.where(air, sample(ground, trail.x, trail.y), walk)
    return walk, floor, air, halves


def find_climbs(trail, walk, air):
    """Stretches climbing more steeply than STAIR_GRADE for more than one stair's height, as (start s, end s)."""
    look = 8  # Two metres, so one sharp bump doesn't count as a climb.
    rise = (np.roll(walk, -look) - walk) / (look * STEP)
    steep = (rise > STAIR_GRADE) & ~air & ~np.roll(air, -look)
    steep[-look:] = False
    climbs = []
    k = 0
    while k < len(steep):
        if steep[k]:
            j = k
            while j < len(steep) and (steep[j] or (j + 8 < len(steep) and steep[j + 1:j + 9].any())):
                j += 1
            s0, s1 = trail.s[k], trail.s[min(j + look, len(walk) - 1)]
            if walk[min(j + look, len(walk) - 1)] - walk[k] > STAIR_RISE * 1.2:
                climbs.append((float(s0), float(s1)))
            k = j + look
        else:
            k += 1
    return climbs


# --- The trail mesh ---

def nearest_on_trail(trail, xs, ys, reach):
    """For each point, the nearest trail sample's index and the signed distance to the trail (positive is right).
    Points further than reach get index -1."""
    best = np.full(len(xs), np.inf)
    index = np.full(len(xs), -1)
    block = 160
    for start in range(0, len(trail.s), block):
        tx, ty = trail.x[start:start + block], trail.y[start:start + block]
        near = (xs > tx.min() - reach) & (xs < tx.max() + reach) & (ys > ty.min() - reach) & (ys < ty.max() + reach)
        candidates = np.flatnonzero(near)
        for chunk in np.array_split(candidates, max(1, len(candidates) // 20000)):
            if not len(chunk):
                continue
            d2 = (xs[chunk, None] - tx[None, :]) ** 2 + (ys[chunk, None] - ty[None, :]) ** 2
            k = d2.argmin(axis=1)
            dist = d2[np.arange(len(chunk)), k]
            better = dist < best[chunk]
            best[chunk[better]] = dist[better]
            index[chunk[better]] = start + k[better]
    index[best > reach * reach] = -1
    side = np.zeros(len(xs))
    valid = index >= 0
    h = trail.heading[index[valid]]
    side[valid] = -(xs[valid] - trail.x[index[valid]]) * np.sin(h) + (ys[valid] - trail.y[index[valid]]) * np.cos(h)
    return index, side


EDGE = 60.0  # Past the lane's edge, the dirt fades into grass over this far.
SKIRT = [120.0, 280.0, 520.0]  # How far past that each bank vertex stands.
ROW_STEP = 2  # Trail samples per mesh row, so one row every 50 cm, closer than highest_near reaches.
ROWS_PER_PIECE = 280


def surface(walk_z, high_z, d, half=LANE):
    """Height of the trail mesh d cm from the middle. The lane follows the ground under it but never dips below its
    crown. Past it, a grassy bank slopes down to the ground, or the mesh tucks just under a rising hillside."""
    inner = half + EDGE
    if abs(d) <= inner:
        return max(walk_z - abs(d) * CROWN, high_z + CLEAR)
    edge = max(walk_z - inner * CROWN, high_z + CLEAR)
    past = abs(d) - inner
    return max(edge - past * BANK, high_z - 25.0 * min(past / SKIRT[-1], 1.0))


def build_trail_meshes(trail, high, walk, air, halves, folder):
    """The walkable trail as OBJ pieces: a dirt lane on the ground, fading to grassy banks. The editor imports them
    with exact collision. Each stretch between crossings is its own run, ending flat on the ground at the bank."""
    from ls_generate_player_meshes import Mesh, write_obj

    def columns_at(half):
        right = [half * 0.33, half * 0.66, half - EDGE, half, half + EDGE] + [half + EDGE + k for k in SKIRT]
        return [-c for c in reversed(right)] + [0.0] + right
    index = np.flatnonzero(~air)
    names = []
    for run in np.split(index, np.flatnonzero(np.diff(index) > 1) + 1):
        if len(run) < 2:
            continue
        rows = list(run[::ROW_STEP])
        if rows[-1] != run[-1]:
            rows.append(run[-1])
        for first in range(0, len(rows) - 1, ROWS_PER_PIECE):
            piece = rows[first:first + ROWS_PER_PIECE + 1]
            mesh = Mesh()
            for k in piece:
                h = trail.heading[k]
                for d in columns_at(halves[k]):
                    x = trail.x[k] - d * math.sin(h)
                    y = trail.y[k] + d * math.cos(h)
                    z = surface(walk[k], float(sample(high, x, y)), d, halves[k])
                    mesh.add_vertex((x, y, z), (trail.s[k] / 400.0, abs(d) / (halves[k] + EDGE)))
            width = len(columns_at(LANE))
            for row in range(len(piece) - 1):
                for column in range(width - 1):
                    a = row * width + column
                    b, c = a + 1, a + width
                    mesh.triangles += [(a, c, b), (b, c, c + 1)]
            mesh.smooth_normals()
            name = "SM_LS_WildwoodTrail_{:02d}".format(len(names))
            write_obj(os.path.join(folder, name + ".obj"), mesh)
            names.append(name)
    return names


# --- Placing the set pieces ---

STORY_START = ["The Heart Tree is dead. The Withering has taken all colour and sound from the world.",
               "Its last seed falls, still glowing."]
STORY_END = ["The forest blooms again.", "A spirit light drifts toward the frozen mountain."]
LOG_TILT = 8.0
LOG_COUNTERWEIGHT = 2000.0  # Light enough for every form, as in the old cavern: Seed tips it from 100 cm past the pivot.
SHRINES = [("cross1", -600.0), ("plates", 3100.0), ("glide", -1200.0), ("cross3", -700.0)]


class Placer:
    def __init__(self, trail, walk, floor, ground, high, halves):
        self.trail, self.walk, self.floor, self.ground_grid, self.high = trail, walk, floor, ground, high
        self.halves = halves
        self.actors = []
        self.solids = []  # (x, y, radius) of everything solid placed, so foliage and dressing keep off it.

    def s(self, mark, offset=0.0):
        return self.trail.mark[mark] + offset

    def z(self, s):
        return float(np.interp(s, self.trail.s, self.walk))

    def ground(self, x, y):
        return float(sample(self.ground_grid, x, y))

    def surface(self, s, d):
        """What stands d cm beside the trail: the trail mesh, its bank, or the forest floor beyond it."""
        x, y = self.trail.point(s, d)
        return surface(self.z(s), float(sample(self.high, x, y)), d, self.lane_half(s))

    def lane_half(self, s):
        return float(np.interp(s, self.trail.s, self.halves))

    def wall_half(self, s):
        return self.lane_half(s) + WALL_GAP

    def add(self, kind, s, d=0.0, z=None, solid=0.0, **data):
        x, y = self.trail.point(s, d)
        entry = {"kind": kind, "x": round(x, 1), "y": round(y, 1), "z": round(self.z(s) if z is None else z, 1),
                 "yaw": round(self.trail.yaw(s), 2), "s": round(s, 1)}
        entry.update(data)
        self.actors.append(entry)
        if solid:
            self.solids.append((x, y, solid))
        return entry


def rock_stairs(p, s0, s1):
    """Rocks across the trail up a climb too steep to roll, each a short hop above the last. Each rock's top clears
    the trail at its uphill end, so the ball always lands on rock."""
    rise = p.z(s1) - p.z(s0)
    count = max(int(math.ceil(rise / STAIR_RISE)), 1)
    length = (s1 - s0) / count
    placed = []
    for k in range(count):
        a, b = s0 + k * length, s0 + (k + 1) * length
        top = p.z(b) + 15.0
        middle = (a + b) / 2.0
        p.add("block", middle, z=top, length=max(length, 200.0) + 40.0, width=2.0 * p.wall_half(middle),
              depth=top - p.z(a) + 120.0, solid=max(length, p.wall_half(middle)))
        placed.append(middle)
    return placed


def crossing(p, start, end, layout, note_at=()):
    """Lays a crossing's parkour between its banks. Layout entries are (kind, near edge, far edge, settings), as
    distances from the near bank. Heights run in a straight line from one bank to the other."""
    s0, s1 = p.s(start), p.s(end)
    z0, z1 = p.z(s0 - STEP), p.z(s1 + STEP)
    length = s1 - s0
    height = lambda o: z0 + (z1 - z0) * o / length
    for kind, a, b, settings in layout:
        o = (a + b) / 2.0
        s = s0 + o
        x, y = p.trail.point(s)
        if kind == "stone":
            radius = (b - a) / 2.0
            p.add("pillar", s, z=height(o), radius=radius, bottom=round(min(p.ground(x, y), WATER) - 150.0, 1), solid=radius,
                  collapses=start == 'cross1')
        elif kind == "log":
            p.add("log_bridge", s, z=height(o), length=b - a + 160.0, width=150.0, collapses=start == 'cross1')
        elif kind == "tilt":
            half = (b - a) / 2.0
            rim = height(o)
            drop = half * math.sin(math.radians(LOG_TILT))
            p.add("tilting_log", s, z=rim + drop, half_length=half, half_width=200.0, max_tilt=LOG_TILT,
                  counterweight=LOG_COUNTERWEIGHT, floor=round(min(p.ground(x, y), WATER) - 150.0, 1), collapses=start == 'cross1')
        elif kind == "moving":
            x1, y1 = p.trail.point(s0 + b - 150.0)
            top = height(o)
            p.add("moving", s0 + a + 150.0, z=top, end=[round(x1, 1), round(y1, 1), round(top, 1)], speed=200.0, wait=1.5)
        elif kind == "crumble":
            p.add("crumbling", s, z=height(o))
    for o, lift in note_at:
        p.add("note", s0 + o, z=height(o) + lift)
    return s0, s1, z0, z1


def trail01_extras(p):
    """Seed-only jumping and steering beats after the hand-placed rocks at s 14000-15100,
    plus the two approach steps for BlockRock2. Raised reward routes have a low bypass.
    Extras stay separate from hand-placed work when the editor applies the plan."""
    wh = p.wall_half

    def log(s, height, lean=0.0, d=0.0, length=None):
        p.add("fallen_log", s, d, z=p.z(s), length=length or 2.0 * wh(s) + 260.0,
              height=height, lean=lean, name="Trail", extra="trail01", solid=wh(s))

    def rock(s, top, length, d=0.0, width=None):
        width = width or 2.0 * wh(s)
        p.add("block", s, d, z=p.z(s) + top, length=length, width=width, depth=top + 260.0, name="Trail", extra="trail01",
              solid=max(length, width) / 2.0)

    # BlockRock2 (placed by hand, 231 cm tall across the whole lane) gets two steps, so it is a climb rather than a wall.
    rock(9560.0, 80.0, 300.0)
    rock(9915.0, 160.0, 420.0)  # Long, so it meets the hand-placed rock's slanted front edge with no pit between.
    p.add("tutorial", 15500.0, z=p.z(15500.0) + 200.0, message="Hop over the logs and rocks. Steer round the boulders.",
          half=[300.0, wh(15500.0), 300.0], extra="trail01")
    # Warm-up, steering, then optional higher lines, with landing room between beats.
    log(16250.0, 90.0, -12.0)
    rock(17650.0, 120.0, 330.0, d=-210.0, width=300.0)
    rock(18750.0, 130.0, 330.0, d=210.0, width=300.0)
    rock(19650.0, 110.0, 420.0)
    log(21150.0, 85.0, -25.0, d=160.0, length=650.0)
    log(22450.0, 85.0, 25.0, d=-160.0, length=650.0)
    rock(23550.0, 70.0, 300.0, d=180.0, width=480.0)
    rock(24000.0, 145.0, 300.0, d=180.0, width=480.0)
    rock(24450.0, 70.0, 300.0, d=180.0, width=480.0)
    log(25800.0, 80.0, -8.0)
    for s, d, lift in [(21150.0, 160.0, 200.0), (24000.0, 180.0, 230.0)]:
        p.add('petal', s, d, z=p.z(s) + lift, extra='trail01')


MUSHROOM_NOTE_LIFT = 950.0  # A note this high over a mushroom is out of reach of a jump (about 250) but not a bounce (about 1300).


def fun_extras(p):
    """Natural opening obstacles; springcaps are introduced later beside their raised reward."""

    def mushroom(s, d, scale=0.6, launch=1600.0):
        p.add("mushroom", s, d, z=p.surface(s, d) - 5.0, scale=scale, launch=launch, extra="fun", solid=200.0 * scale)

    p.add("tutorial", 1500.0, z=p.z(1500.0) + 200.0, message="Follow the music notes. Press Space to hop over fallen branches.",
          half=[300.0, p.wall_half(1500.0), 300.0], extra="fun")
    p.add('fallen_log',3000.0,-100.0,z=p.z(3000.0),length=500.0,height=55.0,lean=-18.0,name='Opening',extra='fun',solid=330.0)
    for s,d in [(3800.0,240.0),(4600.0,-240.0)]:
        p.add('block',s,d,z=p.surface(s,d)+65.0,length=240.0,width=220.0,depth=200.0,name='Opening',extra='fun',solid=180.0)
    s=p.s('dandelion',-4200.0)
    p.add('tutorial',s,z=p.z(s)+200.0,message='Jump onto the springcap to reach the high music note.',
          half=[300.0,p.wall_half(s),300.0],extra='fun')
    mushroom(p.s("dandelion", -3500.0), 120.0)    # Under the second raised note.
    mushroom(p.s("blobs", 900.0), 600.0, launch=1500.0)  # In the arena: bounce up, then slam a blob as Stone.



def place_pieces(trail, walk, floor, ground, high, halves, climbs):
    p = Placer(trail, walk, floor, ground, high, halves)
    tut = lambda s, text, half=300.0, z=None: p.add("tutorial", s, z=(p.z(s) if z is None else z) + 200.0, message=text,
                                                    half=[half, p.wall_half(s), 300.0])
    note = lambda s, d=0.0, lift=80.0: p.add("note", s, d, z=p.surface(s, d) + lift)

    # 1-1 Awakening Glade
    p.add("player_start", 250.0, z=p.z(250.0) + 150.0)
    p.add("story", 300.0, z=p.z(300.0) + 600.0, cards=STORY_START, on_start=True)
    tut(700.0, "WASD to roll, and the mouse to look.")
    note(2000.0,150.0)
    note(3800.0, -150.0)
    jump = p.s("jump1")
    p.add("fallen_log", jump, z=p.z(jump), length=2.0 * p.wall_half(jump) + 200.0, height=90.0, solid=p.wall_half(jump))
    tut(jump - 500.0, "A fallen log blocks the way. Press Space to jump it.")
    note(jump + 600.0)
    # A rock outcrop on the trail: one rock to hop onto, then a broad ledge, then an easy drop down the far side.
    ledge = p.s("ledges")
    p.add("block", ledge + 150.0, z=p.z(ledge + 300.0) + 100.0, length=300.0, width=2.0 * p.wall_half(ledge),
          depth=220.0, solid=p.wall_half(ledge))
    p.add("block", ledge + 750.0, z=p.z(ledge + 1100.0) + 200.0, length=900.0, width=2.0 * p.wall_half(ledge),
          depth=320.0, solid=p.wall_half(ledge) + 200.0)
    tut(ledge - 500.0, "Hop up the rocks, one at a time.")
    note(ledge + 750.0, lift=p.z(ledge + 1100.0) + 280.0 - p.surface(ledge + 750.0, 0.0))
    note(p.s("ledges", 4500.0), 120.0)

    # The gorge: rock stacks, a fallen log, a wider stack to rest on, and a log that tips under you.
    length = p.s("cross1_end") - p.s("cross1")
    crossing(p, "cross1", "cross1_end", [
        ("stone", 160.0, 520.0, None), ("stone", 660.0, 1020.0, None), ("stone", 1140.0, 1660.0, None),
        ("log", 1660.0, 2560.0, None), ("stone", 2560.0, 3080.0, None), ("tilt", 3080.0, length + 40.0, None)],
        note_at=[(1400.0, 80.0), (2110.0, 90.0)])
    tut(p.s("cross1", -400.0), "Stones and logs collapse 1 second after landing. Jump onward as they shake! They rebuild when you respawn.")

    # 1-2 Rootwood Heights
    p.add("flower", p.s("stone", 200.0), z=p.z(p.s("stone", 200.0)) + 80.0, form="STONE",
          message="Stone Shell unlocked! Press 2 to transform. Stone is heavy and can smash walls.")
    note(p.s("stone", 700.0), 150.0)
    tut(p.s("wall", 600.0), "Rocks block the way. Roll into them as Stone Shell. Press 2 first.")
    wall_s = p.s("wall", 1300.0)
    p.add("cracked_wall", wall_s, z=p.z(wall_s), width=2.0 * p.wall_half(wall_s) + 100.0, height=520.0, solid=p.wall_half(wall_s))
    note(wall_s + 460.0)
    # Each at the trail's height where it stands. The level stretch starts 400 cm past the mark, so the mark's own
    # height is about 1 m under it, which once buried the plate and the block.
    plate_s, block_s, gate_s = p.s("plates", 1100.0), p.s("plates", 750.0), p.s("plates", 2700.0)
    p.add("lever", plate_s, -350.0, z=p.z(plate_s), id="lever1")
    p.add("push_block", block_s, 350.0, z=p.z(block_s) + 60.0, mass=52.0)
    tut(p.s("plates", 300.0), "Push the boulder up against the lever. While it leans there, the lever holds the gate open.", half=500.0)
    p.add("gate", gate_s, z=p.z(gate_s), width=2.0 * p.wall_half(gate_s) + 100.0, height=700.0, levers=["lever1"], solid=p.wall_half(gate_s))
    note(p.s("plates", 2000.0), 400.0)
    note(p.s("plates", 5500.0), -120.0)
    s = p.s("dandelion", -3500.0)
    p.add("note", s, 120.0, z=p.surface(s, 120.0) + MUSHROOM_NOTE_LIFT, raised=True)
    p.add("flower", p.s("dandelion", 200.0), z=p.z(p.s("dandelion", 200.0)) + 80.0, form="DANDELION",
          message="Dandelion unlocked! Press 3, then hold Space while falling to glide.")
    note(p.s("dandelion", 900.0), -120.0)

    # 1-3 Bloom Ridge: an updraft lifts Dandelion onto a rock tower, high enough to glide over the river.
    g0, g1 = p.s("glide"), p.s("glide_end")
    landing = p.z(g1 + STEP)
    tower_s = g0 + TOWER_RADIUS + 40.0
    far_edge = tower_s + TOWER_RADIUS
    top = max(landing + (g1 - far_edge) / GLIDE_RATIO + 250.0, p.z(g0) + 600.0)
    x, y = trail.point(tower_s)
    p.add("tower", tower_s, z=top, radius=TOWER_RADIUS, bottom=round(min(p.ground(x, y), WATER) - 150.0, 1), solid=TOWER_RADIUS)
    base = p.z(g0 - 220.0)
    p.add("wind", g0 - 220.0, z=(base + top + 500.0) / 2.0, half=[220.0, p.wall_half(g0) - 40.0, (top + 500.0 - base) / 2.0], strength=900.0)
    note(g0 - 220.0, lift=top - base - 200.0)
    tut(g0 - 900.0, "Updrafts lift the light Dandelion. Press 3 and roll into the wind.")
    tut(tower_s, "Roll off the far edge, then hold Space to glide over the river.", half=TOWER_RADIUS, z=top)
    glide_note = far_edge + (g1 - far_edge) * 0.4
    p.add("note", glide_note, z=top - (glide_note - far_edge) / 3.5 - 150.0)
    p.add("witch_ambush", g1 + 420, z=landing + 225, half=[640, 560, 245], target=[x,y,top+120])

    tut(p.s("blobs", -900.0), "Wither Blobs drain the colour from the world. Slam on them from above as Stone Shell.", half=400.0)
    for offset, d, sweep in ((500.0, 450.0, -900.0), (1300.0, -450.0, 900.0)):
        s = p.s("blobs", offset)
        h = math.radians(trail.yaw(s))
        # Patrol points are offsets in world space, so the sideways sweep is turned by the trail's heading here.
        p.add("blob", s, d, z=p.z(s) + 70.0, patrol=[[0.0, 0.0], [round(-sweep * math.sin(h), 1), round(sweep * math.cos(h), 1)]])
        note(s, 0.0)

    # The last river: stepping stones, a rock that ferries you across, and cracked stones that fall soon after you land.
    length = p.s("cross3_end") - p.s("cross3")
    crossing(p, "cross3", "cross3_end", [
        ("stone", 160.0, 520.0, None), ("stone", 660.0, 1020.0, None), ("stone", 1140.0, 1700.0, None),
        ("moving", 1700.0, 2780.0, None), ("stone", 2780.0, 3300.0, None),
        ("crumble", 3420.0, 3720.0, None), ("crumble", length - 420.0, length - 120.0, None)],
        note_at=[(1420.0, 80.0), (2240.0, 160.0)])
    tut(p.s("cross3", -400.0), "Wait for the floating rock, ride it across, then keep moving: cracked stones fall.")

    climb_steps = []
    for s0, s1 in climbs:
        climb_steps += rock_stairs(p, s0, s1)
    final = [s for s in climb_steps if s > p.s("cross3_end")]
    note(final[len(final) // 2] if final else p.s("climb"), lift=120.0)
    tut(p.s("climb", -300.0), "Climb the rocks to the top.")

    goal_s = p.s("goal", 600.0)
    p.add("goal", goal_s, z=p.z(goal_s) + 200.0, half=[300.0, p.wall_half(goal_s), 300.0], cards=STORY_END, par=420.0, petals=2)
    p.add("heart_tree", p.s("goal", 1350.0), z=p.z(p.s("goal", 1350.0)), solid=500.0)

    for mark, offset in SHRINES:
        p.add("shrine", p.s(mark, offset), z=p.z(p.s(mark, offset)) + 50.0)
    for mark, offset, side in SECRETS:
        s = p.s(mark, offset)
        middle = side * (p.wall_half(s) + POCKET / 2.0)
        x, y = trail.point(s, middle)
        gap = p.z(s) - p.ground(x, y)
        if gap > 30.0:
            # The pocket's ground is below the trail here, so a flat rock ledge level with it fills the pocket.
            p.add("block", s, middle, z=p.z(s), length=520.0, width=POCKET, depth=gap + 150.0, solid=POCKET / 2.0)
        d = side * (p.wall_half(s) + POCKET * 0.6)
        p.add("petal", s, d, z=max(p.z(s), p.ground(*trail.point(s, d))) + 80.0)
    trail01_extras(p)
    fun_extras(p)
    return p


def build_walls(p, air):
    """Hidden walls down both sides of the trail, with a pocket behind each secret, and kill volumes over the water."""
    trail = p.trail
    walls = []
    secrets = [(p.s(mark, offset), side) for mark, offset, side in SECRETS]
    end = trail.length()
    s = 0.0
    seg = 500.0
    while s < end:
        s1 = min(s + seg, end)
        mid = (s + s1) / 2.0
        low = min(float(np.interp(s, trail.s, p.floor)), float(np.interp(s1, trail.s, p.floor)), p.z(s), p.z(s1))
        high = max(p.z(s), p.z(s1)) + WALL_HEIGHT
        for side in (-1, 1):
            if any(side == secret_side and abs(mid - secret_s) < 260.0 for secret_s, secret_side in secrets):
                continue
            x0, y0 = trail.point(s, side * (p.wall_half(s) + opening_padding(s)))
            x1, y1 = trail.point(s1, side * (p.wall_half(s1) + opening_padding(s1)))
            walls.append([round(v, 1) for v in (x0, y0, x1, y1, low - 300.0, high)])
        s = s1
    for secret_s, side in secrets:
        half = p.wall_half(secret_s)
        z = p.z(secret_s)
        corners = [trail.point(secret_s + along, side * (half + depth)) for along, depth in
                   ((-260.0, 0.0), (-260.0, POCKET), (260.0, POCKET), (260.0, 0.0))]
        for (x0, y0), (x1, y1) in zip(corners, corners[1:]):
            walls.append([round(v, 1) for v in (x0, y0, x1, y1, z - 600.0, z + WALL_HEIGHT)])
    for s, back in ((0.0, -150.0), (end, 150.0)):
        x0, y0 = trail.point(s + back, -p.wall_half(s))
        x1, y1 = trail.point(s + back, p.wall_half(s))
        walls.append([round(v, 1) for v in (x0, y0, x1, y1, p.z(s) - 300.0, p.z(s) + WALL_HEIGHT)])

    kills = []
    for a, b in CROSSINGS:
        s0, s1 = p.s(a), p.s(b)
        mid = (s0 + s1) / 2.0
        x, y = trail.point(mid)
        inside = (trail.s >= s0) & (trail.s <= s1)
        rim = min(p.z(s0 - STEP), p.z(s1 + STEP))
        # Touching the water is fatal. In the high gorge, so is falling well below the stones, where the steep banks
        # could otherwise catch a ball out of reach.
        low = min(float(p.floor[inside].min()), WATER - 150.0) - 100.0
        high = max(WATER + 40.0, rim - 350.0)
        kills.append({"x": round(x, 1), "y": round(y, 1), "z": round((low + high) / 2.0, 1), "yaw": round(trail.yaw(mid), 2),
                      "half": [round((s1 - s0) / 2.0 + 100.0, 1), CROSSING_HALF + WALL_GAP + 400.0, round(max((high - low) / 2.0, 100.0), 1)]})
    return walls, kills


# --- Foliage and scenery ---

SMALL = ("SM_Grass", "SM_Flowers", "SM_Plant", "SM_Sprouts", "SM_Clovers", "SM_WildGreens", "SM_LeafField", "SM_Mushroom")
TREE = "SM_Tree"
RESTORE_REACH = 7000.0  # Trees this close to the trail become regrowing trees. Further out, the leaf material handles it.


def near_solid(xs, ys, solids, margin):
    hit = np.zeros(len(xs), bool)
    for x, y, r in solids:
        hit |= (xs - x) ** 2 + (ys - y) ** 2 < (r + margin) ** 2
    return hit


def foliage_actions(trail, halves, foliage, objects, solids):
    """The Wildwood foliage, rebuilt: each group keeps its settings and loses only what stands on the trail or in a
    rock. Trees near the trail come out of their group, to become RestorableActors that grow when a note is found."""
    groups, restore, removed = [], [], 0
    for group in foliage:
        mesh = group["mesh"].rsplit("/", 1)[-1].split(".")[0]
        t = np.array(group["t"], float).reshape(-1, 9)
        index, side = nearest_on_trail(trail, t[:, 0], t[:, 1], RESTORE_REACH)
        dist = np.where(index >= 0, np.abs(side), np.inf)
        half = np.where(index >= 0, halves[np.maximum(index, 0)], LANE)
        small = mesh.startswith(SMALL)
        is_tree = mesh.startswith(TREE)
        # Plants come off the dirt and its edge. Trees and rocks only go when they would stand in the walled lane:
        # a canopy over the trail is part of a forest path.
        reach = half + (EDGE + 40.0 if small else WALL_GAP + 150.0)
        gone = (dist < reach) | near_solid(t[:, 0], t[:, 1], solids, 300.0 if is_tree else 120.0)
        removed += int(gone.sum())
        regrow = is_tree & ~gone & (dist < RESTORE_REACH)
        for row in t[regrow]:
            restore.append([group["mesh"]] + [round(float(v), 3) for v in row])
        keep = ~gone & ~regrow
        entry = {key: value for key, value in group.items() if key != "t"}
        entry["t"] = [[round(float(v), 3) for v in row] for row in t[keep]]
        groups.append(entry)
    actors = {"remove": [], "move": [], "restore": []}
    for mesh, x, y, z, scale, label in objects:
        if not mesh.startswith("SM_"):
            continue
        i, side = nearest_on_trail(trail, np.array([float(x)]), np.array([float(y)]), RESTORE_REACH)
        dist = abs(float(side[0])) if i[0] >= 0 else np.inf
        half = halves[i[0]] if i[0] >= 0 else LANE
        key = [label, x, y]
        if dist < half + WALL_GAP + 300.0 or near_solid(np.array([float(x)]), np.array([float(y)]), solids, 300.0)[0]:
            actors["remove"].append(key)
        elif mesh.startswith(TREE) and dist < RESTORE_REACH:
            actors["restore"].append(key)
    return {"groups": groups, "restore": restore, "actors": actors, "removed": removed}


EDGE_PLANTS = ["SM_Bush_01", "SM_Plant_01", "SM_Plant_04", "SM_Plant_05", "SM_WildGreens_03"]
EDGE_ROCKS = ["SM_Boulder_04", "SM_Boulder_05", "SM_Boulder_06"]
REGROWTH = ["SM_Flowers_White_01", "SM_Flowers_Blue_05", "SM_Flowers_Pink_05", "SM_Sprouts_03", "SM_Mushroom_Yellow_03",
            "SM_Mushroom_Brown_02", "SM_Clovers_04", "SM_Plant_06"]


def edge_dressing(p, air, rng):
    """Small groups along the trail's edges, the way plants gather where a path lets the light in: a rock half sunk in
    the ground with a few plants around it, or plants alone, every 10 to 18 m on alternating sides. Nothing on the
    dirt, on a rock set piece, on a steep bank, or at a crossing. Small flowers ring each note and grow when it's found."""
    trail = p.trail
    in_air = lambda s: bool(np.interp(s, trail.s, air.astype(float)) > 0.0)
    slope_ok = lambda x, y: abs(p.ground(x + 50.0, y) - p.ground(x - 50.0, y)) < 60.0 and abs(p.ground(x, y + 50.0) - p.ground(x, y - 50.0)) < 60.0
    scatter = []
    s, side = 400.0, 1
    while s < trail.length() - 400.0:
        s += rng.uniform(1000.0, 1800.0)
        side = -side
        if in_air(s - 400.0) or in_air(s + 400.0):
            continue
        d = side * (p.lane_half(s) + EDGE + rng.uniform(80.0, 260.0))
        x, y = trail.point(s, d)
        if near_solid(np.array([x]), np.array([y]), p.solids, 400.0)[0] or not slope_ok(x, y):
            continue
        group = []
        if rng.random() < 0.45:
            group.append((rng.choice(EDGE_ROCKS), x, y, rng.uniform(0.8, 1.4)))
        for _ in range(rng.randint(2, 4)):
            a, r = rng.uniform(0, 2 * math.pi), rng.uniform(60.0, 160.0)
            px, py = x + r * math.cos(a), y + r * math.sin(a)
            index, offset = nearest_on_trail(trail, np.array([px]), np.array([py]), 2000.0)
            if index[0] >= 0 and abs(offset[0]) < p.halves[index[0]] + EDGE:
                continue  # Never on the dirt.
            group.append((rng.choice(EDGE_PLANTS), px, py, rng.uniform(0.9, 1.5)))
        for mesh, gx, gy, scale in group:
            scatter.append([mesh, round(gx, 1), round(gy, 1), round(p.ground(gx, gy), 1), round(rng.uniform(0, 360), 1), round(scale, 2)])
    regrowth = []
    for actor in p.actors:
        if actor["kind"] != "note" or in_air(actor["s"]):
            continue
        for _ in range(5):
            s = actor["s"] + rng.uniform(-400.0, 400.0)
            d = rng.choice((-1, 1)) * (p.lane_half(s) + EDGE + rng.uniform(20.0, 250.0))
            if in_air(s):
                continue
            x, y = trail.point(s, d)
            regrowth.append([rng.choice(REGROWTH), round(x, 1), round(y, 1), round(p.surface(s, d), 1), round(rng.uniform(0, 360), 1),
                             round(rng.uniform(0.9, 1.4), 2)])
    return scatter, regrowth


# --- Files ---

def load_heights(path):
    pixels = np.array(Image.open(path)).astype(np.int64)
    return ((pixels[..., 0] << 8) | pixels[..., 1]).astype(float) * Z_UNIT - 32768 * Z_UNIT


def preview(trail, ground, walk, floor, actors, path_map, path_profile):
    step = 2
    z = ground[::step, ::step]
    gy, gx = np.gradient(z, CELL * step)
    light = np.clip(0.55 + (-gx * 0.7 + gy * 0.7) * 1.5, 0, 1)
    n = np.clip((z - 1500) / 5000, 0, 1)
    img = np.stack([0.35 + 0.4 * n, 0.45 + 0.35 * n, 0.3 + 0.3 * n], -1) * light[..., None]
    img[z < WATER] = [0.25, 0.45, 0.85]
    im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
    draw = ImageDraw.Draw(im)
    to_px = lambda x, y: ((x - X0) / (CELL * step), (y - Y0) / (CELL * step))
    draw.line([to_px(x, y) for x, y in zip(trail.x[::8], trail.y[::8])], fill=(255, 230, 80), width=1)
    for actor in actors:
        if actor["kind"] in ("block", "pillar", "tower"):
            px, py = to_px(actor["x"], actor["y"])
            draw.rectangle((px - 1, py - 1, px + 1, py + 1), fill=(150, 150, 150))
    for name, s in trail.mark.items():
        px, py = to_px(*trail.at(s))
        draw.ellipse((px - 3, py - 3, px + 3, py + 3), outline=(255, 0, 0))
    im = im.transpose(Image.FLIP_TOP_BOTTOM)
    draw = ImageDraw.Draw(im)
    for name, s in trail.mark.items():
        px, py = to_px(*trail.at(s))
        draw.text((px + 4, im.height - py - 6), name, fill=(255, 255, 255))
    im.save(path_map)

    width, height = 1600, 400
    chart = Image.new("RGB", (width, height), (25, 25, 30))
    draw = ImageDraw.Draw(chart)
    zmin, zmax = min(floor.min(), WATER) - 200, max(walk.max(), max(a["z"] for a in actors if a["kind"] == "tower")) + 300
    fx = lambda s: s / trail.length() * (width - 1)
    fy = lambda z: height - 1 - (z - zmin) / (zmax - zmin) * (height - 1)
    original = sample(ground, trail.x, trail.y)
    draw.line([(fx(s), fy(z)) for s, z in zip(trail.s[::4], original[::4])], fill=(110, 110, 110))
    draw.line([(fx(s), fy(z)) for s, z in zip(trail.s[::4], walk[::4])], fill=(240, 220, 90))
    draw.line([(0, fy(WATER)), (width, fy(WATER))], fill=(70, 110, 220))
    for actor in actors:
        if actor["kind"] in ("block", "pillar", "tower", "moving", "crumbling", "log_bridge", "tilting_log"):
            draw.rectangle((fx(actor["s"]) - 1, fy(actor["z"]) - 1, fx(actor["s"]) + 1, fy(actor["z"]) + 1), fill=(220, 120, 220))
    for name, s in trail.mark.items():
        draw.line([(fx(s), 0), (fx(s), height)], fill=(60, 60, 70))
        draw.text((fx(s) + 2, 4 + (hash(name) % 5) * 12), name, fill=(220, 220, 220))
    chart.save(path_profile)


def main():
    ground = load_heights(os.path.join(WORK, "landscape_before.png"))
    high = highest_near(ground)
    trail = Trail(ground)
    walk, floor, air, halves = build_profile(trail, ground, high)
    climbs = find_climbs(trail, walk, air)
    trail_meshes = build_trail_meshes(trail, high, walk, air, halves, WORK)
    fill = walk - sample(ground, trail.x, trail.y)
    print("trail length {:.0f} m, fill under the middle: mean {:.0f}, 95% {:.0f}, max {:.0f} cm".format(
        trail.length() / 100.0, fill[~air].mean(), np.percentile(fill[~air], 95), fill[~air].max()))
    for name, s in trail.mark.items():
        print("  {:<11} s={:>7.0f}  walk z={:>6.0f}  above water {:>5.0f}".format(name, s, np.interp(s, trail.s, walk), np.interp(s, trail.s, walk) - WATER))
    for s0, s1 in climbs:
        print("  rock stairs s={:.0f}..{:.0f}, rise {:.0f}".format(s0, s1, np.interp(s1, trail.s, walk) - np.interp(s0, trail.s, walk)))

    pieces = place_pieces(trail, walk, floor, ground, high, halves, climbs)
    walls, kills = build_walls(pieces, air)
    rng = random.Random(SEED)
    scatter, regrowth = edge_dressing(pieces, air, rng)
    preview(trail, ground, walk, floor, pieces.actors, os.path.join(WORK, "preview.png"), os.path.join(WORK, "profile.png"))
    foliage = json.load(open(os.path.join(WORK, "foliage_full.json")))
    objects = json.load(open(os.path.join(HERE, "..", "..", "Saved", "wildwood_objects.json")))["actors"]
    changes = foliage_actions(trail, halves, foliage, objects, pieces.solids)

    kinds = [actor["kind"] for actor in pieces.actors]
    assert kinds.count("note") == 20, "Level 1 needs 20 Life Notes, found {}".format(kinds.count("note"))
    assert kinds.count("petal") == 3 and kinds.count("player_start") == 1 and kinds.count("goal") == 1

    plan = {"trail_meshes": trail_meshes, "actors": pieces.actors, "walls": walls, "kills": kills, "scatter": scatter, "regrowth": regrowth,
            "restore_trees": changes["restore"], "scenery": changes["actors"],
            "trail": [[round(float(x), 1), round(float(y), 1), round(float(z), 1)] for x, y, z in zip(trail.x[::8], trail.y[::8], walk[::8])],
            "water": WATER, "wall_height": WALL_HEIGHT}
    json.dump(plan, open(os.path.join(WORK, "plan.json"), "w"))
    json.dump(changes["groups"], open(os.path.join(WORK, "foliage_new.json"), "w"))
    print("{} trail mesh pieces, {} actors, {} walls, {} kill volumes, {} edge plants, {} regrowth plants".format(
        len(trail_meshes), len(pieces.actors), len(walls), len(kills), len(scatter), len(regrowth)))
    print("foliage: {} removed, {} trees to regrow; scenery actors: {} removed, {} trees to regrow".format(
        changes["removed"], len(changes["restore"]), len(changes["actors"]["remove"]), len(changes["actors"]["restore"])))
    return trail, ground, walk, floor, air


if __name__ == "__main__":
    main()
