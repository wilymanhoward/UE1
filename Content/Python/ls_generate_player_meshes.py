# Last Seed - generates the player's meshes as OBJ files, using only the Python standard library.
#
# Purpose: writes the Seed, Stone and Dandelion models to Content/LastSeed/SourceMeshes/. The same random seed always
# gives the same shapes, so these files can be rebuilt at any time and are not stored in git.
# Run it outside Unreal with "python ls_generate_player_meshes.py". ls_import_player_assets.py also runs it inside Unreal.
#
# Every model is centred on the ball's centre, with a radius of about 50 cm, to match the 50 cm physics sphere.
# Coordinates here are Unreal's: X forward, Y right, Z up, in cm. write_obj converts them to OBJ's axes.
#
# Most materials read masks from their UVs:
#   Seed shell: cylindrical unwrap for the painted shell textures
#   Stone shell: U = crack amount, V = how light this rock plate is
#   Dandelion:   U = 0 on a stalk and 1 on a tuft hair, V = distance along the stalk or hair

import math
import os
import random

BALL_RADIUS = 50.0
SEED_LEAN = math.radians(23.0)
SEED_DEPTH = 1.04
SEED_LENGTH = 97.0
SEED_PROFILE = (
    (0.00, 0.0, 0.0), (0.035, -12.0, 7.0), (0.09, -21.5, 15.0),
    (0.17, -31.0, 23.5), (0.27, -38.0, 30.0), (0.37, -39.0, 34.0),
    (0.46, -37.5, 34.3), (0.55, -32.5, 31.5), (0.65, -22.0, 22.0),
    (0.75, -12.0, 10.0), (0.86, -5.0, 2.9), (0.94, -1.7, 1.1),
    (1.00, 0.0, 0.0),
)
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

def seed_panels(u, height):
    """The two curved panel borders on each side, shared by the sculpt and the texture bake."""
    bend = 0.26 * math.sin(math.pi * height) + 0.16 * height
    phase = (2.0 * u + bend + 0.08) % 1.0
    inner = abs(phase - 0.28)
    outer = abs(phase - 0.70)
    return phase, inner, outer


def seed_section(height, left, right):
    return ((right - left) * 0.5, (left + right) * 0.5 + 5.0 * height ** 5,
            SEED_LENGTH * (height - 0.5))


def build_seed_shell():
    """Cross-sections traced along the cutscene seed's diagonal axis, with added depth for rolling."""
    mesh = Mesh()
    sides, rows = 96, 108
    sin_lean, cos_lean = math.sin(SEED_LEAN), math.cos(SEED_LEAN)
    section = 0
    for row in range(rows + 1):
        height = (1.0 - math.cos(math.pi * row / rows)) * 0.5
        while section + 2 < len(SEED_PROFILE) and height > SEED_PROFILE[section + 1][0]:
            section += 1
        before, after = SEED_PROFILE[section:section + 2]
        progress = (height - before[0]) / (after[0] - before[0])
        left = before[1] + progress * (after[1] - before[1])
        right = before[2] + progress * (after[2] - before[2])
        radius, center, z = seed_section(height, left, right)
        for side in range(sides + 1):
            u = side / sides
            angle = u * math.tau
            _, inner, outer = seed_panels(u, height)
            groove = (1.0 - smoothstep(0.006, 0.029, inner)) + 0.60 * (1.0 - smoothstep(0.006, 0.024, outer))
            shell = radius - min(radius * 0.1, 0.87 * groove)
            x = math.cos(angle) * shell * SEED_DEPTH
            y = math.sin(angle) * shell + center
            point = (x, y * cos_lean + z * sin_lean, z * cos_lean - y * sin_lean)
            mesh.add_vertex(point, (u, 1.0 - height))
            if side == sides or row == rows:
                continue
            a = row * (sides + 1) + side
            b, c = a + 1, a + sides + 1
            if row > 0:
                mesh.triangles.append((a, b, c))
            if row < rows - 1:
                mesh.triangles.append((b, c + 1, c))
    mesh.smooth_normals()
    for row in range(rows + 1):
        first, last = row * (sides + 1), row * (sides + 1) + sides
        if row in (0, rows):
            normal = (0.0, sin_lean, cos_lean)
            mesh.normals[first:last + 1] = [scale(normal, -1.0 if row == 0 else 1.0)] * (sides + 1)
        else:
            mesh.normals[first] = mesh.normals[last] = normalize(add(mesh.normals[first], mesh.normals[last]))
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
    """An asymmetric boulder with broad rock faces and one partial mineral fissure."""
    planes = [(normalize(direction), distance) for direction, distance in (
        ((1, .25, .18), 43), ((-.8, .37, -.3), 42), ((.05, 1, .3), 45),
        ((.3, -1, .16), 46), ((.14, -.27, 1), 39), ((-.17, .3, -1), 44),
        ((.65, .7, -.4), 43), ((-.6, -.5, .75), 45), ((-.6, -.8, -.3), 46),
    )]
    mesh = Mesh()
    points, mesh.triangles = icosphere(4)
    for p in points:
        x, y, z = p
        roughness = (1.5 * math.sin(8*x + 3*y) * math.cos(7*z - y)
                     + .6 * math.sin(24*x - 15*y + 11*z))
        radius = min(49.8, 49.2 + roughness,
                     *(distance / max(dot(p, normal), .01) for normal, distance in planes))

        # A broken vein on one side, rather than a closed pattern around the shell.
        line = y - .29*z + .08*math.sin(13*z) + .035*math.sin(34*z + x*8)
        end_fade = (1 - smoothstep(.43, .86, abs(z))) * smoothstep(.18, .72, -x)
        vein = (1 - smoothstep(.008, .048, abs(line))) * end_fade
        branch = (1 - smoothstep(.007, .032, abs(line + .65*(z-.04))))
        branch *= smoothstep(.02, .17, z) * (1 - smoothstep(.34, .57, z)) * end_fade * .42
        crack = max(vein, branch)
        tone = .46 + .20*math.sin(7*z + 3*x + math.sin(5*y)) + .12*math.cos(14*y - 11*x)
        tone += .09*math.sin(38*x + 17*y) * math.cos(32*z - 12*y)
        mesh.add_vertex(scale(p, radius - crack*1.8), (crack, tone))
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
