# Last Seed - generates world pieces that the Fab packs don't have, using only the Python standard library.
#
# Purpose: the giant dead tree, the music note, the gate's ring and the floating island. The same random seed always gives
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


def grow_branch(mesh, rng, start, direction, length, radius, depth):
    segments = 6 if depth > 1 else 4
    path = bend_path(rng, start, direction, length, segments, 0.32 if depth > 1 else 0.45, 0.02)
    radii = [radius * (1.0 - 0.72 * i / segments) for i in range(segments + 1)]
    add_tube(mesh, path, radii, 10 if depth > 2 else 6 if depth > 0 else 4)
    if depth == 0:
        return
    for child in range(3 if depth > 1 else 2):
        at = rng.randint(segments // 2, segments)
        ahead = normalize((path[at][0] - path[at - 1][0], path[at][1] - path[at - 1][1], path[at][2] - path[at - 1][2]))
        side, up = perpendicular_axes(ahead)
        angle = rng.uniform(0.0, 2.0 * math.pi)
        spread = rng.uniform(0.6, 1.1)
        outward = add(scale(side, math.cos(angle) * spread), scale(up, math.sin(angle) * spread))
        grow_branch(mesh, rng, path[at], add(ahead, outward), length * rng.uniform(0.55, 0.75), radii[at] * 0.72, depth - 1)


def build_gnarled_tree():
    """The dead Heart Tree: a thick twisted trunk on spreading roots, with bare branches. About 3000 cm tall."""
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
        grow_branch(mesh, rng, top, (math.cos(angle + 2.4), math.sin(angle + 2.4), 1.0), 1300.0, 80.0, 3)

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
                                ("ring", build_gate_ring(), None), ("island", build_floating_island(), (0.0, 0.0, -50.0))):
        print(name, len(built.points), "points", len(built.triangles), "triangles", "outward" if centre is None or faces_outward(built, centre) else "REVERSED")
        for normal in built.normals:
            assert normal is not None
