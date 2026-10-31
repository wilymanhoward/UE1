# Last Seed - generates the player's meshes as OBJ files, using only the Python standard library.
#
# Purpose: writes the Seed, Stone and Dandelion models to Content/LastSeed/SourceMeshes/. The same random seed always
# gives the same shapes, so these files can be rebuilt at any time and are not stored in git.
# Run it outside Unreal with "python ls_generate_player_meshes.py". ls_import_player_assets.py also runs it inside Unreal.
#
# Every model is centred on the ball's centre, with a radius of about 50 cm, to match the 50 cm physics sphere.
# Coordinates here are Unreal's: X forward, Y right, Z up, in cm. write_obj converts them to OBJ's axes.
#
# The materials use no textures. The UVs carry masks that the material graphs read:
#   Seed shell:  U = ridge amount
#   Stone shell: U = crack amount, V = how light this rock plate is
#   Dandelion:   U = 0 on a stalk and 1 on a tuft hair, V = distance along the stalk or hair

import math
import os
import random

BALL_RADIUS = 50.0
OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "LastSeed", "SourceMeshes")


# --- Small vector helpers ---

def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def scale(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def normalize(a):
    length = math.sqrt(dot(a, a))
    return scale(a, 1.0 / length) if length > 1e-9 else (0.0, 0.0, 1.0)


def smoothstep(edge0, edge1, x):
    t = min(max((x - edge0) / (edge1 - edge0), 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)


class Mesh:
    """Vertices with one UV and one normal each, plus triangles wound so that they face outward."""

    def __init__(self):
        self.points = []
        self.uvs = []
        self.normals = []
        self.triangles = []

    def add_vertex(self, point, uv, normal=None):
        self.points.append(point)
        self.uvs.append(uv)
        self.normals.append(normal)
        return len(self.points) - 1

    def smooth_normals(self):
        """Fills in each vertex normal by averaging the faces around it, so displaced surfaces shade correctly."""
        totals = [(0.0, 0.0, 0.0)] * len(self.points)
        for a, b, c in self.triangles:
            # Not normalized: larger faces should count for more.
            face = cross(sub(self.points[b], self.points[a]), sub(self.points[c], self.points[a]))
            totals[a] = add(totals[a], face)
            totals[b] = add(totals[b], face)
            totals[c] = add(totals[c], face)
        self.normals = [normalize(total) for total in totals]


def icosphere(subdivisions):
    """Returns unit-length points and outward-facing triangles. An icosphere has no crowded poles, unlike a UV sphere."""
    t = (1.0 + math.sqrt(5.0)) / 2.0
    points = [normalize(p) for p in [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t),
                                     (0, -1, -t), (0, 1, -t), (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]]
    faces = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6),
             (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10),
             (8, 6, 7), (9, 8, 1)]

    for _ in range(subdivisions):
        midpoints = {}

        def midpoint(a, b):
            key = (min(a, b), max(a, b))
            if key not in midpoints:
                points.append(normalize(add(points[a], points[b])))
                midpoints[key] = len(points) - 1
            return midpoints[key]

        refined = []
        for a, b, c in faces:
            ab, bc, ca = midpoint(a, b), midpoint(b, c), midpoint(c, a)
            refined += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        faces = refined
    return points, faces


def fibonacci_directions(count):
    """Evenly spread directions over a sphere."""
    golden_angle = math.pi * (3.0 - math.sqrt(5.0))
    directions = []
    for i in range(count):
        z = 1.0 - 2.0 * (i + 0.5) / count
        ring = math.sqrt(1.0 - z * z)
        directions.append((math.cos(golden_angle * i) * ring, math.sin(golden_angle * i) * ring, z))
    return directions


def perpendicular_axes(direction):
    side = normalize(cross(direction, (0.0, 0.0, 1.0) if abs(direction[2]) < 0.9 else (1.0, 0.0, 0.0)))
    return side, cross(direction, side)


# --- The models ---

def build_seed_shell():
    """A smooth ball with shallow ridges running pole to pole, like a sunflower seed."""
    mesh = Mesh()
    points, mesh.triangles = icosphere(5)
    for p in points:
        longitude = math.atan2(p[1], p[0])
        # Ridges fade out at the poles, where they would all pinch together.
        ridge = (0.5 + 0.5 * math.cos(longitude * 14.0)) ** 3 * smoothstep(0.0, 0.5, 1.0 - abs(p[2]))
        mesh.add_vertex(scale(p, BALL_RADIUS - 1.6 * (1.0 - ridge)), (ridge, 0.0))
    mesh.smooth_normals()
    return mesh


def add_leaf(mesh, base, direction, length, width):
    """A curved, pointed leaf made from a strip of quads that arcs up and then droops."""
    across = normalize(cross((0.0, 0.0, 1.0), direction))
    rows, columns = 8, 4
    first = len(mesh.points)
    for row in range(rows + 1):
        t = row / rows
        centre = add(base, add(scale(direction, length * t), (0.0, 0.0, length * (0.7 * t - 0.55 * t * t))))
        half_width = width * 0.5 * math.sin(math.pi * min(t * 1.05 + 0.02, 1.0)) ** 0.8
        for column in range(columns + 1):
            s = column / columns - 0.5
            # A shallow V along the middle makes the leaf look like it has a fold.
            point = add(add(centre, scale(across, s * 2.0 * half_width)), (0.0, 0.0, abs(s) * half_width * 0.5))
            mesh.add_vertex(point, (column / columns, t))
    for row in range(rows):
        for column in range(columns):
            a = first + row * (columns + 1) + column
            b = a + 1
            c = a + columns + 1
            d = c + 1
            mesh.triangles += [(a, b, c), (b, d, c)]


def build_seed_sprout():
    """A short curved stem with two leaves. It sits on top of the ball and never rolls."""
    mesh = Mesh()
    sides, rows = 6, 8
    stem_bottom, stem_height = BALL_RADIUS - 2.0, 16.0
    for row in range(rows + 1):
        t = row / rows
        centre = (2.0 * t * t, 0.0, stem_bottom + stem_height * t)
        radius = 1.4 - 0.5 * t
        for side in range(sides):
            angle = 2.0 * math.pi * side / sides
            mesh.add_vertex(add(centre, (math.cos(angle) * radius, math.sin(angle) * radius, 0.0)), (0.5, t * 0.3))
    for row in range(rows):
        for side in range(sides):
            a = row * sides + side
            b = row * sides + (side + 1) % sides
            c = a + sides
            d = b + sides
            mesh.triangles += [(a, b, c), (b, d, c)]

    top = (2.0, 0.0, stem_bottom + stem_height)
    add_leaf(mesh, top, normalize((0.25, 1.0, 0.0)), 15.0, 9.0)
    add_leaf(mesh, top, normalize((0.25, -1.0, 0.0)), 13.0, 8.0)
    mesh.smooth_normals()
    return mesh


def build_stone_shell():
    """Chunky rock plates with deep grooves between them. The plates are Voronoi cells on the sphere."""
    rng = random.Random(20261031)
    cells = fibonacci_directions(24)
    cells = [normalize(add(c, (rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25)))) for c in cells]
    heights = [rng.uniform(0.0, 3.0) for _ in cells]
    tones = [rng.uniform(0.0, 1.0) for _ in cells]

    mesh = Mesh()
    points, mesh.triangles = icosphere(5)
    for p in points:
        nearest, second = sorted(range(len(cells)), key=lambda i: -dot(p, cells[i]))[:2]
        # How far past the border to the next plate this point is, in radians. 0 is exactly on a border.
        edge = math.acos(min(dot(p, cells[second]), 1.0)) - math.acos(min(dot(p, cells[nearest]), 1.0))
        crack = 1.0 - smoothstep(0.015, 0.075, edge)
        bevel = smoothstep(0.0, 0.3, edge)
        lumps = 0.7 * math.sin(p[0] * 9.0 + 1.0) * math.sin(p[1] * 8.0 + 2.0) * math.sin(p[2] * 7.0)
        radius = BALL_RADIUS - 3.5 + heights[nearest] * bevel + lumps - crack * 3.5
        mesh.add_vertex(scale(p, radius), (crack, tones[nearest]))
    mesh.smooth_normals()
    return mesh


def add_tapered_stalk(mesh, start, end, normal, radius, u):
    side, up = perpendicular_axes(normalize(sub(end, start)))
    first = len(mesh.points)
    for i in range(3):
        angle = 2.0 * math.pi * i / 3.0
        offset = add(scale(side, math.cos(angle) * radius), scale(up, math.sin(angle) * radius))
        mesh.add_vertex(add(start, offset), (u, 0.0), normal)
    tip = mesh.add_vertex(end, (u, 1.0), normal)
    for i in range(3):
        mesh.triangles.append((first + i, first + (i + 1) % 3, tip))


def build_dandelion_fluff(stalk_count=220, hairs_per_tuft=9):
    """Thin stalks ending in tufts of flat hairs, together forming a soft sphere. The material draws both sides."""
    rng = random.Random(7)
    mesh = Mesh()
    stalk_inner, stalk_outer = 8.0, 37.0
    for direction in fibonacci_directions(stalk_count):
        tip = scale(direction, stalk_outer)
        add_tapered_stalk(mesh, scale(direction, stalk_inner), tip, direction, 0.35, 0.0)

        side, up = perpendicular_axes(direction)
        for hair in range(hairs_per_tuft):
            # Hairs open out like a small umbrella. Each one is a kite: narrow at the stalk and wider near its end.
            angle = 2.0 * math.pi * (hair + rng.random()) / hairs_per_tuft
            spread = rng.uniform(0.35, 0.8)
            outward = add(scale(side, math.cos(angle)), scale(up, math.sin(angle)))
            hair_direction = normalize(add(direction, scale(outward, spread)))
            # The distance along this hair at which it meets the ball's surface, so slanted hairs still fit inside.
            along = stalk_outer * dot(hair_direction, direction)
            length = (math.sqrt(along * along + BALL_RADIUS ** 2 - stalk_outer ** 2) - along) * rng.uniform(0.85, 1.0)
            end = add(tip, scale(hair_direction, length))
            middle = add(tip, scale(hair_direction, length * 0.65))
            width = scale(normalize(cross(hair_direction, direction)), 0.7)
            a = mesh.add_vertex(tip, (1.0, 0.0), direction)
            b = mesh.add_vertex(add(middle, width), (1.0, 0.65), direction)
            c = mesh.add_vertex(end, (1.0, 1.0), direction)
            d = mesh.add_vertex(sub(middle, width), (1.0, 0.65), direction)
            mesh.triangles += [(a, b, c), (a, c, d)]
    return mesh


def build_dandelion_core():
    """The small golden centre. It is its own mesh because the fluff around it is translucent."""
    mesh = Mesh()
    points, mesh.triangles = icosphere(3)
    for p in points:
        mesh.add_vertex(scale(p, 11.0), (0.0, 0.0), p)
    return mesh


# --- Output ---

def check_mesh(name, mesh, largest_radius):
    """Every part must fit the 50 cm ball, or it would visibly sink through floors the physics sphere rests on."""
    assert mesh.triangles, name
    assert all(normal is not None for normal in mesh.normals), name
    furthest = max(math.sqrt(dot(p, p)) for p in mesh.points)
    assert furthest <= largest_radius + 0.01, "{} reaches {:.1f} cm".format(name, furthest)


def write_obj(path, mesh):
    with open(path, "w", encoding="ascii", newline="\n") as handle:
        # Measured on UE 5.7: the importer maps OBJ (x, y, z) to Unreal (x, -y, z), so writing -y puts every point back
        # where it was built. It keeps the triangle order, and Unreal's front faces use the opposite order to the one
        # built here (checked against the engine's sphere), so each triangle is written as a, c, b.
        for x, y, z in mesh.points:
            handle.write("v {:.4f} {:.4f} {:.4f}\n".format(x, -y, z))
        for u, v in mesh.uvs:
            # OBJ's V runs upward and Unreal's runs downward, so this makes the material read the value written here.
            handle.write("vt {:.5f} {:.5f}\n".format(u, 1.0 - v))
        for x, y, z in mesh.normals:
            handle.write("vn {:.4f} {:.4f} {:.4f}\n".format(x, -y, z))
        for a, b, c in mesh.triangles:
            handle.write("f {0}/{0}/{0} {2}/{2}/{2} {1}/{1}/{1}\n".format(a + 1, b + 1, c + 1))


def main():
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    models = [("SM_LS_SeedShell", build_seed_shell(), BALL_RADIUS),
              # Only the sprout may stick out above the ball, and it never touches the floor.
              ("SM_LS_SeedSprout", build_seed_sprout(), BALL_RADIUS + 30.0),
              ("SM_LS_StoneShell", build_stone_shell(), BALL_RADIUS),
              ("SM_LS_DandelionFluff", build_dandelion_fluff(), BALL_RADIUS),
              ("SM_LS_DandelionCore", build_dandelion_core(), BALL_RADIUS)]
    for name, mesh, largest_radius in models:
        check_mesh(name, mesh, largest_radius)
        write_obj(os.path.join(OUTPUT_FOLDER, name + ".obj"), mesh)
        print("Last Seed meshes: {} has {} triangles".format(name, len(mesh.triangles)))
    print("Last Seed meshes: wrote {} files to {}".format(len(models), os.path.normpath(OUTPUT_FOLDER)))


if __name__ == "__main__":
    main()
