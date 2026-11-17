# Last Seed - generates the floor lever's meshes and textures.
#
# Purpose: writes the lever by the plate puzzle as five OBJ meshes and three painted texture sets to
# Content/LastSeed/SourceMeshes/Lever/. build_level1_wildwood.lever_assets() imports them and builds the materials.
#   SM_LS_LeverBase  a bevelled wooden plinth                     (wood)
#   SM_LS_LeverIron  riveted rails, the arc bracket, a gear, axle  (iron)
#   SM_LS_LeverCap   the painted band over the arc                 (wood)
#   SM_LS_LeverRod   the handle's rod, collars and ball knob       (iron)
#   SM_LS_LeverGrip  the wrapped leather grip                      (leather)
# The base meshes sit on the ground at the origin. The handle meshes start at the axle (46 cm up), where the lever's
# ArmPivot turns them. Units are cm, in Unreal's axes: X along the swing, Y across, Z up. UVs are in metres of
# surface, so the textures keep one scale everywhere. The same input always gives the same output.
# Run: python ls_generate_lever.py (from Content/Python). Needs numpy and Pillow for the textures.

import math
import os

import numpy as np
from PIL import Image

from ls_generate_player_meshes import Mesh, add, cross, dot, normalize, scale, sub, write_obj

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "LastSeed", "SourceMeshes", "Lever")
AXLE_Z = 46.0  # Must match ALever's ArmPivot.
TILE = 100.0  # cm of surface per texture repeat.


# --- Shapes ---

def box_uv(point, normal, tile):
    """Planar UVs from the two world axes the face lies along, so a texture keeps its scale on every face."""
    ax = max(range(3), key=lambda i: abs(normal[i]))
    a, b = [i for i in range(3) if i != ax]
    return (point[a] / tile, point[b] / tile)


def poly(mesh, points, outward, tile=TILE):
    """A flat convex face, wound so it faces outward, with its own flat-shaded vertices."""
    normal = normalize(cross(sub(points[1], points[0]), sub(points[2], points[0])))
    if dot(normal, outward) < 0.0:
        points = points[::-1]
        normal = scale(normal, -1.0)
    first = len(mesh.points)
    for p in points:
        mesh.add_vertex(p, box_uv(p, normal, tile), normal)
    for k in range(1, len(points) - 1):
        mesh.triangles.append((first, first + k, first + k + 1))


def frustum(mesh, bottom, top, z0, z1):
    """A box whose top is smaller than its bottom: (half x, half y) at each end."""
    lo = [(sx * bottom[0], sy * bottom[1], z0) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    hi = [(sx * top[0], sy * top[1], z1) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    poly(mesh, lo, (0, 0, -1))
    poly(mesh, hi, (0, 0, 1))
    for k in range(4):
        j = (k + 1) % 4
        mid = scale(add(lo[k], lo[j]), 0.5)
        poly(mesh, [lo[k], lo[j], hi[j], hi[k]], (mid[0], mid[1], 0.0))


def box(mesh, x0, x1, y0, y1, z0, z1):
    corners = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
    lo = [(x, y, z0) for x, y in corners]
    hi = [(x, y, z1) for x, y in corners]
    centre = ((x0 + x1) / 2.0, (y0 + y1) / 2.0)
    poly(mesh, lo, (0, 0, -1))
    poly(mesh, hi, (0, 0, 1))
    for k in range(4):
        j = (k + 1) % 4
        mid = scale(add(lo[k], lo[j]), 0.5)
        poly(mesh, [lo[k], lo[j], hi[j], hi[k]], (mid[0] - centre[0], mid[1] - centre[1], 0.0))


def arc_plate(mesh, r_in, r_out, y0, y1, centre_z=AXLE_Z, segments=28):
    """Half a ring standing upright over the axle, from angle 0 (+X) over the top to 180 (-X), y0 to y1 thick."""
    ring = lambda r, a, y: (r * math.cos(a), y, centre_z + r * math.sin(a))
    for k in range(segments):
        a0, a1 = math.pi * k / segments, math.pi * (k + 1) / segments
        for y, side in ((y0, -1.0), (y1, 1.0)):
            poly(mesh, [ring(r_in, a0, y), ring(r_out, a0, y), ring(r_out, a1, y), ring(r_in, a1, y)], (0, side, 0))
        mid = (a0 + a1) / 2.0
        poly(mesh, [ring(r_out, a0, y0), ring(r_out, a1, y0), ring(r_out, a1, y1), ring(r_out, a0, y1)], (math.cos(mid), 0, math.sin(mid)))
        poly(mesh, [ring(r_in, a0, y0), ring(r_in, a1, y0), ring(r_in, a1, y1), ring(r_in, a0, y1)], (-math.cos(mid), 0, -math.sin(mid)))
    for a in (0.0, math.pi):
        poly(mesh, [ring(r_in, a, y0), ring(r_out, a, y0), ring(r_out, a, y1), ring(r_in, a, y1)], (0, 0, -1))


def gear(mesh, r_root, r_tip, teeth, y0, y1, centre_z=AXLE_Z):
    """A toothed wheel on the axle, as a flat-shaded extruded star."""
    outline = []
    for k in range(teeth):
        base = 2.0 * math.pi * k / teeth
        step = 2.0 * math.pi / teeth
        for frac, r in ((0.0, r_root), (0.2, r_tip), (0.55, r_tip), (0.75, r_root)):
            a = base + frac * step
            outline.append((r * math.cos(a), r * math.sin(a)))
    to3 = lambda p, y: (p[0], y, centre_z + p[1])
    for y, side in ((y0, -1.0), (y1, 1.0)):
        for k in range(len(outline)):
            j = (k + 1) % len(outline)
            poly(mesh, [to3((0.0, 0.0), y), to3(outline[k], y), to3(outline[j], y)], (0, side, 0))
    for k in range(len(outline)):
        j = (k + 1) % len(outline)
        mid = ((outline[k][0] + outline[j][0]) / 2.0, (outline[k][1] + outline[j][1]) / 2.0)
        poly(mesh, [to3(outline[k], y0), to3(outline[j], y0), to3(outline[j], y1), to3(outline[k], y1)], (mid[0], 0, mid[1]))


def cylinder(mesh, p0, p1, radius, segments=24, tile=TILE, caps=True):
    """A smooth round bar from p0 to p1, with flat end caps."""
    axis = normalize(sub(p1, p0))
    side = normalize(cross(axis, (0.0, 0.0, 1.0) if abs(axis[2]) < 0.9 else (1.0, 0.0, 0.0)))
    up = cross(side, axis)
    length = math.sqrt(dot(sub(p1, p0), sub(p1, p0)))
    first = len(mesh.points)
    for k in range(segments + 1):
        a = 2.0 * math.pi * k / segments
        n = add(scale(side, math.cos(a)), scale(up, math.sin(a)))
        u = a * radius / tile
        mesh.add_vertex(add(p0, scale(n, radius)), (u, 0.0), n)
        mesh.add_vertex(add(p1, scale(n, radius)), (u, length / tile), n)
    for k in range(segments):
        a, b = first + 2 * k, first + 2 * k + 2
        tri = [(a, b, b + 1), (a, b + 1, a + 1)]
        for t in tri:
            pa, pb, pc = (mesh.points[i] for i in t)
            if dot(cross(sub(pb, pa), sub(pc, pa)), mesh.normals[t[0]]) < 0.0:
                t = (t[0], t[2], t[1])
            mesh.triangles.append(t)
    if caps:
        for centre, out in ((p0, scale(axis, -1.0)), (p1, axis)):
            ring = []
            for k in range(segments):
                a = 2.0 * math.pi * k / segments
                ring.append(add(centre, scale(add(scale(side, math.cos(a)), scale(up, math.sin(a))), radius)))
            poly(mesh, ring, out, tile)


def sphere(mesh, centre, radius, rings=12, segments=24, tile=TILE):
    first = len(mesh.points)
    for i in range(rings + 1):
        lat = math.pi * i / rings - math.pi / 2.0
        for k in range(segments + 1):
            lon = 2.0 * math.pi * k / segments
            n = (math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat))
            mesh.add_vertex(add(centre, scale(n, radius)), (lon * radius / tile, (lat + math.pi / 2.0) * radius / tile), n)
    width = segments + 1
    for i in range(rings):
        for k in range(segments):
            a = first + i * width + k
            for t in ((a, a + 1, a + width + 1), (a, a + width + 1, a + width)):
                pa, pb, pc = (mesh.points[j] for j in t)
                if dot(cross(sub(pb, pa), sub(pc, pa)), sub(pa, centre)) < 0.0:
                    t = (t[0], t[2], t[1])
                mesh.triangles.append(t)


# --- The lever's parts ---

def build_base():
    mesh = Mesh()
    frustum(mesh, (125.0, 55.0), (113.0, 43.0), 0.0, 26.0)
    return mesh


def build_iron():
    mesh = Mesh()
    for y in (-1.0, 1.0):
        # A riveted rail down each side of the plinth's top, which the arc stands on.
        box(mesh, -100.0, 100.0, y * 22.0 - 4.0, y * 22.0 + 4.0, 26.0, 48.0)
        for x in (-88.0, -62.0, 62.0, 88.0):
            for z in (32.0, 42.0):
                cylinder(mesh, (x, y * 26.0, z), (x, y * 29.0, z), 3.0, segments=10)
    # The two arc plates, either side of the gear.
    arc_plate(mesh, 48.0, 72.0, -26.0, -18.0)
    arc_plate(mesh, 48.0, 72.0, 18.0, 26.0)
    gear(mesh, 30.0, 38.0, 12, -6.0, 6.0)
    cylinder(mesh, (0.0, -30.0, AXLE_Z), (0.0, 30.0, AXLE_Z), 11.0)  # The axle, through everything.
    cylinder(mesh, (0.0, -34.0, AXLE_Z), (0.0, -30.0, AXLE_Z), 15.0)  # Its end caps.
    cylinder(mesh, (0.0, 30.0, AXLE_Z), (0.0, 34.0, AXLE_Z), 15.0)
    return mesh


def build_cap():
    mesh = Mesh()
    arc_plate(mesh, 72.0, 80.0, -26.0, 26.0)
    return mesh


def build_rod():
    """From the axle upward: the rod, a collar under and over the grip, and a ball knob. Relative to the axle."""
    mesh = Mesh()
    cylinder(mesh, (0.0, 0.0, 0.0), (0.0, 0.0, 250.0), 6.0)
    for z0, z1 in ((180.0, 188.0), (236.0, 244.0)):
        cylinder(mesh, (0.0, 0.0, z0), (0.0, 0.0, z1), 10.0)
    sphere(mesh, (0.0, 0.0, 256.0), 13.0)
    return mesh


def build_grip():
    """Leather wrapped round the rod between the collars, in raised turns."""
    mesh = Mesh()
    cylinder(mesh, (0.0, 0.0, 188.0), (0.0, 0.0, 236.0), 8.0, tile=40.0)
    for k in range(5):
        z = 191.0 + k * 9.4
        cylinder(mesh, (0.0, 0.0, z), (0.0, 0.0, z + 6.0), 9.6, tile=40.0)
    return mesh


# --- Textures ---

SIZE = 1024


def noise(seed, beta, stretch=1.0):
    """Tileable fractal noise from a random spectrum, 0 to 1. stretch above 1 draws it out along the image's height."""
    rng = np.random.default_rng(seed)
    ky = np.fft.fftfreq(SIZE)[:, None] * stretch
    kx = np.fft.rfftfreq(SIZE)[None, :]
    k = np.sqrt(kx * kx + ky * ky)
    k[0, 0] = 1.0
    spectrum = (rng.normal(size=k.shape) + 1j * rng.normal(size=k.shape)) / k ** beta
    spectrum[0, 0] = 0.0
    out = np.fft.irfft2(spectrum, s=(SIZE, SIZE))
    return (out - out.min()) / (out.max() - out.min())


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def mix(a, b, t):
    return np.asarray(a, float)[None, None, :] * (1.0 - t[..., None]) + np.asarray(b, float)[None, None, :] * t[..., None]


def normal_map(height, strength):
    dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * strength
    dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * strength
    n = np.stack([-dx, -dy, np.ones_like(height)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n * 0.5 + 0.5


def save(name, colour, normal, rough, metal, ao):
    to8 = lambda a: Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    to8(colour / 255.0).save(os.path.join(OUT, name + "_BC.png"))
    to8(normal).save(os.path.join(OUT, name + "_N.png"))
    to8(np.stack([ao, rough, metal], -1)).save(os.path.join(OUT, name + "_ORM.png"))


def wood():
    """Red-stained planks: long grain lines, darker in the grooves, as on the plinth in the reference."""
    v = np.linspace(0.0, 1.0, SIZE, endpoint=False)[None, :] * np.ones((SIZE, 1))
    warp = noise(11, 2.4, stretch=6.0)
    grain = (np.sin(2.0 * math.pi * (v * 14.0 + warp * 7.0)) * 0.5 + 0.5) ** 3 * (0.55 + 0.45 * noise(14, 1.8, stretch=4.0))
    streak = noise(12, 1.6, stretch=10.0)
    fine = noise(13, 0.9)
    tone = grain * 0.45 + streak * 0.4 + fine * 0.15
    colour = mix((150, 64, 42), (66, 26, 18), tone)
    height = 1.0 - (grain * 0.6 + streak * 0.3 + fine * 0.1)
    save("T_LS_LeverWood", colour, normal_map(height, 6.0), 0.72 + 0.15 * grain, np.zeros_like(tone), 1.0 - 0.35 * grain)


def iron():
    """Dark worn iron with rust blooms, rougher and duller where it has rusted, and small pits all over."""
    mottle = noise(21, 2.0)
    rust = smooth(0.56, 0.74, noise(22, 1.3) * 0.6 + noise(23, 0.9) * 0.4) * 0.85
    pits = smooth(0.62, 0.8, noise(24, 0.7))
    steel = mix((84, 86, 90), (150, 150, 148), mottle)
    rusted = mix((86, 40, 20), (160, 86, 42), noise(25, 1.4))
    colour = steel * (1.0 - rust[..., None]) + rusted * rust[..., None]
    colour *= (1.0 - 0.35 * pits)[..., None]
    height = mottle * 0.2 + rust * 0.5 - pits * 0.4
    save("T_LS_LeverIron", colour, normal_map(height, 5.0), 0.5 + 0.4 * rust + 0.1 * pits, 0.55 - 0.45 * rust, 1.0 - 0.4 * pits)


def leather():
    """Oxblood leather with a fine crinkle."""
    crinkle = noise(31, 1.0)
    broad = noise(32, 2.2)
    colour = mix((128, 40, 30), (70, 20, 16), crinkle * 0.6 + broad * 0.4)
    save("T_LS_LeverLeather", colour, normal_map(crinkle, 8.0), 0.55 + 0.25 * crinkle, np.zeros_like(crinkle), 1.0 - 0.25 * crinkle)


def main():
    os.makedirs(OUT, exist_ok=True)
    parts = [("SM_LS_LeverBase", build_base()), ("SM_LS_LeverIron", build_iron()), ("SM_LS_LeverCap", build_cap()),
             ("SM_LS_LeverRod", build_rod()), ("SM_LS_LeverGrip", build_grip())]
    for name, mesh in parts:
        assert mesh.triangles and all(n is not None for n in mesh.normals), name
        write_obj(os.path.join(OUT, name + ".obj"), mesh)
        print("Last Seed lever: {} has {} triangles".format(name, len(mesh.triangles)))
    wood()
    iron()
    leather()
    print("Last Seed lever: wrote meshes and textures to", os.path.normpath(OUT))


if __name__ == "__main__":
    main()
