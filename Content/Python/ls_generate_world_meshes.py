# Last Seed - generates world pieces that the Fab packs don't have, using only the Python standard library.
#
# Purpose: the giant dead tree and its moss, the music note, the gate's ring, the floating island, and the marsh's roots, brambles and blob. The same random seed always gives
# the same shapes. build_world_level1.py imports these, and the files are not stored in git.
# Coordinates are Unreal's: X forward, Y right, Z up, in cm. UVs: U runs around a branch and V along it, for the bark.

import math
import random

from ls_generate_player_meshes import Mesh, add, cross, icosphere, normalize, perpendicular_axes, scale, smoothstep


def add_tube(mesh, path, radii, sides):
    """A closed-tip tube along a list of points. Each ring is turned from the last one, so the surface never twists."""
    first = len(mesh.points)
    direction = normalize((path[1][0] - path[0][0], path[1][1] - path[0][1], path[1][2] - path[0][2]))
    side, up = perpendicular_axes(direction)
    for index, point in enumerate(path):
        following = path[min(index + 1, len(path) - 1)]
        previous = path[max(index - 1, 0)]
        direction = normalize((following[0] - previous[0], following[1] - previous[1], following[2] - previous[2]))
        side = normalize(cross(up, direction))
        up = cross(direction, side)
        for i in range(sides):
            angle = 2.0 * math.pi * i / sides
            offset = add(scale(side, math.cos(angle) * radii[index]), scale(up, math.sin(angle) * radii[index]))
            mesh.add_vertex(add(point, offset), (i / sides * max(radii[index] / 40.0, 1.0), index * 0.5))
    for row in range(len(path) - 1):
        for i in range(sides):
            a = first + row * sides + i
            b = first + row * sides + (i + 1) % sides
            c = a + sides
            d = b + sides
            mesh.triangles += [(a, b, c), (b, d, c)]


def bend_path(rng, start, direction, length, segments, wander, upward=0.0):
    """Points that drift from a straight line. The drift keeps its direction for a while, which reads as a twisted limb."""
    path = [start]
    current = normalize(direction)
    drift = (0.0, 0.0, 0.0)
    for _ in range(segments):
        drift = add(scale(drift, 0.6), (rng.uniform(-wander, wander), rng.uniform(-wander, wander), rng.uniform(-wander, wander) + upward))
        current = normalize(add(current, drift))
        path.append(add(path[-1], scale(current, length / segments)))
    return path


def grow_branch(mesh, rng, start, direction, length, radius, depth, hang_points=None):
    segments = 6 if depth > 1 else 4
    path = bend_path(rng, start, direction, length, segments, 0.32 if depth > 1 else 0.45, 0.02)
    radii = [radius * (1.0 - 0.72 * i / segments) for i in range(segments + 1)]
    add_tube(mesh, path, radii, 10 if depth > 2 else 6 if depth > 0 else 4)
    if hang_points is not None and depth <= 2:
        hang_points += path[2::2]
    if depth == 0:
        return
    for child in range(3 if depth > 1 else 2):
        at = rng.randint(segments // 2, segments)
        ahead = normalize((path[at][0] - path[at - 1][0], path[at][1] - path[at - 1][1], path[at][2] - path[at - 1][2]))
        side, up = perpendicular_axes(ahead)
        angle = rng.uniform(0.0, 2.0 * math.pi)
        spread = rng.uniform(0.6, 1.1)
        outward = add(scale(side, math.cos(angle) * spread), scale(up, math.sin(angle) * spread))
        grow_branch(mesh, rng, path[at], add(ahead, outward), length * rng.uniform(0.55, 0.75), radii[at] * 0.72, depth - 1, hang_points)


def build_gnarled_tree(hang_points=None):
    """The dead Heart Tree: a thick twisted trunk on spreading roots, with bare branches. About 3000 cm tall.
    A list passed as hang_points collects spots along the branches, in the tree's own coordinates."""
    rng = random.Random(1711)
    mesh = Mesh()

    # Several trunks wound together, which gives a fatter and more twisted silhouette than one thick cylinder.
    for strand in range(5):
        angle = 2.0 * math.pi * strand / 5.0
        path = []
        radii = []
        for row in range(11):
            t = row / 10.0
            twist = angle + t * 2.4
            spread = 130.0 + 170.0 * (1.0 - t) ** 3
            path.append((math.cos(twist) * spread, math.sin(twist) * spread, t * 1500.0 - 40.0))
            radii.append(135.0 - 55.0 * t)
        add_tube(mesh, path, radii, 12)
        # Each strand ends in one of the great limbs.
        top = path[-1]
        grow_branch(mesh, rng, top, (math.cos(angle + 2.4), math.sin(angle + 2.4), 1.0), 1300.0, 80.0, 3, hang_points)

    # Roots leave the base, arch over the ground and dive back in.
    for root in range(9):
        angle = 2.0 * math.pi * (root + rng.uniform(-0.2, 0.2)) / 9.0
        out = (math.cos(angle), math.sin(angle), 0.0)
        reach = rng.uniform(900.0, 1500.0)
        path = []
        radii = []
        wobble = rng.uniform(0.0, 6.0)
        for row in range(11):
            t = row / 10.0
            sideways = math.sin(t * 5.0 + wobble) * 90.0 * t
            distance = 180.0 + reach * t
            height = 240.0 * (1.0 - t) ** 2 + 70.0 * math.sin(t * math.pi) - 90.0 * t * t
            path.append((out[0] * distance - out[1] * sideways, out[1] * distance + out[0] * sideways, height))
            radii.append(120.0 * (1.0 - 0.8 * t))
        add_tube(mesh, path, radii, 10)
    mesh.smooth_normals()
    return mesh


def build_tree_moss():
    """Moss hanging from the gnarled tree's branches. It shares the tree's origin, so placing both alike lines them up."""
    points = []
    build_gnarled_tree(points)
    rng = random.Random(61)
    mesh = Mesh()
    for point in points:
        if rng.random() > 0.55:
            continue
        for _ in range(rng.randint(2, 4)):
            length = rng.uniform(180.0, 750.0)
            wander = rng.uniform(0.0, 6.0)
            top = (point[0] + rng.uniform(-25.0, 25.0), point[1] + rng.uniform(-25.0, 25.0), point[2])
            path = [(top[0] + 14.0 * math.sin(i + wander), top[1] + 14.0 * math.cos(i * 0.8 + wander), top[2] - length * i / 5.0) for i in range(6)]
            add_tube(mesh, path, [rng.uniform(9.0, 14.0) * (1.0 - 0.17 * i) for i in range(6)], 4)
    mesh.smooth_normals()
    return mesh


def build_root_clump():
    """Roots spreading from one spot, arching up a little and then diving 400 cm. They cover the sides of the raised path."""
    rng = random.Random(77)
    mesh = Mesh()
    for root in range(7):
        angle = 2.0 * math.pi * (root + rng.uniform(-0.3, 0.3)) / 7.0
        reach = rng.uniform(170.0, 280.0)
        wobble = rng.uniform(0.0, 6.0)
        path = []
        for row in range(9):
            t = row / 8.0
            distance = 20.0 + reach * t
            sideways = math.sin(t * 5.0 + wobble) * 40.0 * t
            path.append((math.cos(angle) * distance - math.sin(angle) * sideways, math.sin(angle) * distance + math.cos(angle) * sideways,
                         50.0 * math.sin(t * math.pi * 0.8) - 420.0 * t ** 3))
        add_tube(mesh, path, [rng.uniform(26.0, 38.0) * (1.0 - 0.7 * row / 8.0) for row in range(9)], 7)
    mesh.smooth_normals()
    return mesh


def build_bramble():
    """Arching thorny stems about 400 cm across and 180 cm high, with spikes all along them. Picture 3's foreground."""
    rng = random.Random(31)
    mesh = Mesh()
    for stem in range(7):
        angle = rng.uniform(0.0, 2.0 * math.pi)
        turn = rng.uniform(-0.9, 0.9)
        rise = rng.uniform(90.0, 180.0)
        path = []
        for row in range(11):
            t = row / 10.0
            heading = angle + turn * t
            distance = -200.0 + 400.0 * t
            path.append((math.cos(heading) * distance, math.sin(heading) * distance, rise * math.sin(math.pi * t) - 15.0))
        add_tube(mesh, path, [rng.uniform(9.0, 13.0)] * 11, 6)
        for row in range(1, 10):
            for _ in range(2):
                out = normalize((rng.uniform(-1.0, 1.0), rng.uniform(-1.0, 1.0), rng.uniform(-0.4, 1.0)))
                add_tube(mesh, [path[row], add(path[row], scale(out, rng.uniform(26.0, 48.0)))], [7.0, 0.5], 4)
    mesh.smooth_normals()
    return mesh


def build_blob():
    """A squat dark blob with two eyes on its +X side, in a pool of goo. Radius about 70 cm. U tells the material which part is which: 0 body, 0.5 goo, 1 eye."""
    mesh = Mesh()
    points, triangles = icosphere(3)

    def ball(centre, sizes, u, lumps=0.0):
        first = len(mesh.points)
        for p in points:
            bump = 1.0 + lumps * math.sin(p[0] * 7.0 + 1.0) * math.sin(p[1] * 6.0) * math.sin(p[2] * 5.0 + 2.0)
            mesh.add_vertex((centre[0] + p[0] * sizes[0] * bump, centre[1] + p[1] * sizes[1] * bump, centre[2] + p[2] * sizes[2] * bump), (u, 0.0))
        mesh.triangles += [(a + first, b + first, c + first) for a, b, c in triangles]

    ball((0.0, 0.0, -8.0), (70.0, 70.0, 60.0), 0.0, 0.12)
    for side in (-1.0, 1.0):
        ball((56.0, side * 25.0, 14.0), (15.0, 17.0, 19.0), 1.0)
        ball((68.0, side * 25.0, 14.0), (5.0, 7.0, 8.0), 0.0)
    # The pool of goo is a flat wavy disc around the body. It hides where the blob meets the ground.
    centre = mesh.add_vertex((0.0, 0.0, -66.0), (0.5, 0.0))
    sides = 36
    for side in range(sides):
        angle = 2.0 * math.pi * side / sides
        radius = 112.0 + 16.0 * math.sin(angle * 3.0 + 1.0) + 10.0 * math.sin(angle * 5.0)
        mesh.add_vertex((math.cos(angle) * radius, math.sin(angle) * radius, -69.0), (0.5, 0.0))
    mesh.triangles += [(centre, centre + 1 + side, centre + 1 + (side + 1) % sides) for side in range(sides)]
    mesh.smooth_normals()
    return mesh


def build_log():
    """A bare log 800 cm long and 45 cm in radius, along X from the origin. The Fab trunks all keep their branches."""
    mesh = Mesh()
    path = [(800.0 * i / 8, 8.0 * math.sin(i * 1.1), 8.0 * math.sin(i * 0.7)) for i in range(9)]
    radii = [45.0 + 4.0 * math.sin(i * 1.7) for i in range(9)]
    # A ring shrunk to almost nothing closes each end, so the sawn faces don't look hollow.
    add_tube(mesh, [(0.1, path[0][1], path[0][2])] + path[1:-1] + [(799.9, path[-1][1], path[-1][2])], radii[:1] + radii[1:-1] + radii[-1:], 12)
    add_tube(mesh, [path[0], (0.1, path[0][1], path[0][2])], [0.1, radii[0]], 12)
    add_tube(mesh, [(799.9, path[-1][1], path[-1][2]), path[-1]], [radii[-1], 0.1], 12)
    mesh.smooth_normals()
    return mesh


def build_log_pivot():
    """A stump with spreading roots, like the one under the log in picture 2. Its top is at Z = 0, and it reaches 500 cm down."""
    rng = random.Random(9)
    mesh = Mesh()
    add_tube(mesh, [(0.0, 0.0, -520.0), (8.0, -6.0, -340.0), (-6.0, 5.0, -170.0), (0.0, 0.0, 0.0)], [150.0, 100.0, 75.0, 90.0], 14)
    for root in range(8):
        angle = 2.0 * math.pi * root / 8.0 + rng.uniform(-0.2, 0.2)
        out = (math.cos(angle), math.sin(angle))
        path = []
        for row in range(8):
            t = row / 7.0
            distance = 60.0 + 340.0 * t
            path.append((out[0] * distance, out[1] * distance, -170.0 - 340.0 * t * t))
        add_tube(mesh, path, [48.0 * (1.0 - 0.75 * row / 7.0) for row in range(8)], 8)
    mesh.smooth_normals()
    return mesh


def build_light_shaft():
    """A cone of light widening downward from Z = 0 to Z = -1900, seen from both sides. V is 0 at the top and 1 at the bottom."""
    mesh = Mesh()
    rows, sides = 6, 20
    for row in range(rows + 1):
        t = row / rows
        radius = 300.0 + 420.0 * t
        for side in range(sides):
            angle = 2.0 * math.pi * side / sides
            mesh.add_vertex((math.cos(angle) * radius, math.sin(angle) * radius, -1900.0 * t), (side / sides, t))
    for row in range(rows):
        for side in range(sides):
            a = row * sides + side
            b = row * sides + (side + 1) % sides
            c = a + sides
            d = b + sides
            mesh.triangles += [(a, b, c), (b, d, c)]
    mesh.smooth_normals()
    return mesh


def build_root_arch():
    """Three roots twisted together, arching 900 cm high across a 2500 cm span along Y. The ends sink below ground at Z = 0."""
    rng = random.Random(23)
    mesh = Mesh()
    for strand in range(3):
        angle = 2.0 * math.pi * strand / 3.0
        path = []
        radii = []
        for row in range(25):
            t = row / 24.0
            twist = angle + t * 9.0
            wobble = 28.0 + 20.0 * math.sin(t * 7.0 + strand)
            y = -1250.0 + 2500.0 * t
            z = 960.0 * math.sin(math.pi * t) - 60.0
            path.append((math.cos(twist) * wobble, y, z + math.sin(twist) * wobble))
            radii.append(26.0 + 52.0 * abs(2.0 * t - 1.0) ** 1.6 + 6.0 * math.sin(t * 20.0 + strand))
        add_tube(mesh, path, radii, 8)
        # Thin side roots leave the arch low down and reach for the ground, away from the road.
        for side in (0.08, 0.92):
            at = int(side * 24)
            grow_branch(mesh, rng, path[at], (rng.uniform(-0.8, 0.8), -1.0 if side < 0.5 else 1.0, -0.6), 500.0, radii[at] * 0.5, 1)
    mesh.smooth_normals()
    return mesh


def build_music_note():
    """An eighth note, about 110 cm tall and centred on the pickup. The head is a flattened sphere, tilted like a printed note."""
    mesh = Mesh()
    points, triangles = icosphere(2)
    tilt = math.radians(20.0)
    for p in points:
        x, y, z = p[0] * 24.0, p[1] * 14.0, p[2] * 16.0
        # Tilted in the XZ plane, so the note reads from the side and spins around Z.
        mesh.add_vertex((x * math.cos(tilt) - z * math.sin(tilt) - 8.0, y, x * math.sin(tilt) + z * math.cos(tilt) - 42.0), (0.0, 0.0))
    mesh.triangles = list(triangles)

    stem_x = 12.0
    add_tube(mesh, [(stem_x, 0.0, -40.0), (stem_x, 0.0, 10.0), (stem_x, 0.0, 58.0)], [4.0, 4.0, 4.0], 6)
    # The flag sweeps back and down from the top of the stem.
    flag = [(stem_x, 0.0, 56.0), (stem_x + 14.0, 0.0, 40.0), (stem_x + 28.0, 0.0, 26.0), (stem_x + 26.0, 0.0, 8.0)]
    add_tube(mesh, flag, [6.0, 7.0, 5.0, 1.5], 6)
    mesh.smooth_normals()
    return mesh


def build_gate_ring():
    """A torus 300 cm in radius standing upright. It faces along X."""
    mesh = Mesh()
    major, minor, rows, sides = 300.0, 26.0, 48, 10
    for row in range(rows):
        around = 2.0 * math.pi * row / rows
        for side in range(sides):
            angle = 2.0 * math.pi * side / sides
            radial = major + math.cos(angle) * minor
            mesh.add_vertex((math.sin(angle) * minor, math.cos(around) * radial, math.sin(around) * radial), (0.0, 0.0))
    for row in range(rows):
        for side in range(sides):
            a = row * sides + side
            b = row * sides + (side + 1) % sides
            c = ((row + 1) % rows) * sides + side
            d = ((row + 1) % rows) * sides + (side + 1) % sides
            mesh.triangles += [(a, c, b), (b, c, d)]
    mesh.smooth_normals()
    return mesh


def build_floating_island():
    """A rock with a flat top at Z = 0 and a jagged point below. Radius 100 cm, so scaling by 2.25 gives a 225 cm island."""
    rng = random.Random(44)
    mesh = Mesh()
    rings, sides = 8, 18
    jitter = [rng.uniform(0.82, 1.12) for _ in range(sides)]
    mesh.add_vertex((0.0, 0.0, 0.0), (0.0, 0.0))
    for ring in range(rings + 1):
        t = ring / rings
        # A flat disc first, then a rough rim, then the tapering underside.
        radius = 100.0 * smoothstep(0.0, 0.25, t) * (1.0 - 0.9 * smoothstep(0.3, 1.0, t))
        depth = 150.0 * smoothstep(0.25, 1.0, t)
        for side in range(sides):
            angle = 2.0 * math.pi * side / sides
            wobble = jitter[side] if t > 0.25 else 1.0
            lump = rng.uniform(-8.0, 8.0) * smoothstep(0.25, 0.5, t)
            mesh.add_vertex((math.cos(angle) * (radius * wobble + lump), math.sin(angle) * (radius * wobble + lump), -depth), (0.0, 0.0))
    for side in range(sides):
        mesh.triangles.append((0, 1 + (side + 1) % sides, 1 + side))
    for ring in range(rings):
        for side in range(sides):
            a = 1 + ring * sides + side
            b = 1 + ring * sides + (side + 1) % sides
            c = a + sides
            d = b + sides
            mesh.triangles += [(a, b, c), (b, d, c)]
    bottom = mesh.add_vertex((0.0, 0.0, -160.0), (0.0, 0.0))
    last = 1 + rings * sides
    for side in range(sides):
        mesh.triangles.append((last + side, last + (side + 1) % sides, bottom))
    mesh.triangles = [(a, c, b) for a, b, c in mesh.triangles]
    mesh.smooth_normals()
    return mesh


def faces_outward(mesh, centre):
    """True when most triangles face away from a point inside the shape. It catches a reversed winding before import."""
    good = 0
    for a, b, c in mesh.triangles:
        pa, pb, pc = mesh.points[a], mesh.points[b], mesh.points[c]
        u = (pb[0] - pa[0], pb[1] - pa[1], pb[2] - pa[2])
        v = (pc[0] - pa[0], pc[1] - pa[1], pc[2] - pa[2])
        n = cross(u, v)
        out = (pa[0] - centre[0], pa[1] - centre[1], pa[2] - centre[2])
        good += 1 if n[0] * out[0] + n[1] * out[1] + n[2] * out[2] > 0.0 else 0
    return good > len(mesh.triangles) * 0.8


if __name__ == "__main__":
    for name, built, centre in (("tree", build_gnarled_tree(), None), ("note", build_music_note(), None),
                                ("ring", build_gate_ring(), None), ("island", build_floating_island(), (0.0, 0.0, -50.0)),
                                ("moss", build_tree_moss(), None), ("roots", build_root_clump(), None), ("bramble", build_bramble(), None),
                                ("blob", build_blob(), None)):
        print(name, len(built.points), "points", len(built.triangles), "triangles", "outward" if centre is None or faces_outward(built, centre) else "REVERSED")
        for normal in built.normals:
            assert normal is not None
