# Last Seed - generates the giant bouncy mushroom's meshes and textures.
#
# Purpose: writes SM_LS_MushroomStem and SM_LS_MushroomCap, with painted cap and stem textures, to
# Content/LastSeed/SourceMeshes/Mushroom/. build_level1_wildwood.fun_assets() imports them.
# Both are lathed: a side profile spun around the Z axis. The stem stands on the ground at the origin, 150 cm tall. The
# cap's origin is its underside where it meets the stem, so ABounceMushroom squashes it down onto the stem. The cap is
# about 4 m across: a red dome with cream spots (which glow softly, from the colour texture's alpha) over pale gills.
# UVs: U goes once around, V runs along the profile from the stem up over the top.
# Run: python ls_generate_mushroom.py (from Content/Python). Needs numpy and Pillow.

import math
import os

import numpy as np
from PIL import Image, ImageDraw

from ls_generate_lever import mix, noise, normal_map
from ls_generate_player_meshes import Mesh, cross, dot, sub, write_obj

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "LastSeed", "SourceMeshes", "Mushroom")
SIZE = 1024
STEM_TOP = 145.0  # Where the cap sits.
SEGMENTS = 40


def lathe(profile, segments=SEGMENTS):
    """Spins a profile of (radius, height) points around Z. The profile runs from its first point to its last, and
    the faces point to the outside of that path (to the right of it, looking from inside the solid)."""
    mesh = Mesh()
    lengths = [0.0]
    for (r0, z0), (r1, z1) in zip(profile, profile[1:]):
        lengths.append(lengths[-1] + math.hypot(r1 - r0, z1 - z0))
    total = lengths[-1]
    for i, (r, z) in enumerate(profile):
        for k in range(segments + 1):
            a = 2 * math.pi * k / segments
            mesh.add_vertex((r * math.cos(a), r * math.sin(a), z), (k / segments, lengths[i] / total))
    width = segments + 1
    for i in range(len(profile) - 1):
        for k in range(segments):
            a = i * width + k
            b, c, d = a + 1, a + width, a + width + 1
            mesh.triangles += [(a, c, b), (b, c, d)]
    mesh.smooth_normals()
    # Face the triangles outward: check one against the direction away from the axis, and flip all if needed.
    p = mesh.points
    t = mesh.triangles[len(mesh.triangles) // 2]
    n = cross(sub(p[t[1]], p[t[0]]), sub(p[t[2]], p[t[0]]))
    centre = tuple(sum(p[i][j] for i in t) / 3 for j in range(3))
    if dot(n, (centre[0], centre[1], 0.0)) < 0:
        mesh.triangles = [(a, c, b) for a, b, c in mesh.triangles]
        mesh.smooth_normals()
    return mesh


def stem():
    profile = [(0.0, 0.0), (52.0, 0.0), (50.0, 12.0), (45.0, 45.0), (39.0, 95.0), (36.0, 125.0), (40.0, 140.0), (46.0, 150.0), (0.0, 150.0)]
    return lathe(profile)


def cap():
    # From the middle of the underside, out across the gills to the rim, round its lip, then up over the dome.
    profile = [(0.0, 0.0), (40.0, 0.0), (110.0, -4.0), (170.0, -14.0), (196.0, -12.0), (206.0, 2.0), (205.0, 22.0),
               (196.0, 52.0), (178.0, 84.0), (150.0, 112.0), (114.0, 134.0), (70.0, 148.0), (30.0, 154.0), (0.0, 155.0)]
    return lathe(profile)


def cap_texture():
    """V below about 0.38 is the underside (gills), above it the red dome with spots."""
    u = np.linspace(0, 1, SIZE, endpoint=False)[None, :] * np.ones((SIZE, 1))
    v = np.linspace(0, 1, SIZE)[:, None] * np.ones((1, SIZE))
    gills = (np.sin(2 * np.pi * u * 90) * 0.5 + 0.5) ** 2
    under = v < 0.38
    red = mix((214, 48, 30), (150, 22, 16), np.clip((v - 0.38) / 0.62, 0, 1) * 0.6 + noise(41, 1.6) * 0.4)
    rim = np.clip(1 - np.abs(v - 0.42) / 0.06, 0, 1)
    red = red * (1 - rim[..., None] * 0.25) + np.array([240, 140, 60])[None, None, :] * rim[..., None] * 0.25
    gill_col = mix((236, 218, 186), (196, 170, 132), gills)
    colour = np.where(under[..., None], gill_col, red)
    # Spots: round in the world, so wider in U near the top where the rings are short.
    spots = Image.new("L", (SIZE, SIZE), 0)
    draw = ImageDraw.Draw(spots)
    rng = np.random.default_rng(5)
    for _ in range(38):
        sv = rng.uniform(0.47, 0.9)
        su = rng.uniform(0, 1)
        radius = rng.uniform(0.022, 0.045) * SIZE
        ring = max(math.sin(math.pi * (1.0 - sv) * 0.9 + 0.12), 0.35)  # How short the ring is here, roughly.
        for shift in (-SIZE, 0, SIZE):  # Wrap around the seam.
            cx, cy = su * SIZE + shift, sv * SIZE
            draw.ellipse([cx - radius / ring, cy - radius, cx + radius / ring, cy + radius], fill=255)
    spot = np.asarray(spots).astype(float) / 255.0
    cream = np.array([250, 238, 212])[None, None, :]
    colour = colour * (1 - spot[..., None]) + cream * spot[..., None]
    height = np.where(under, gills * 0.5, noise(42, 1.4) * 0.3 + spot * 0.7)
    rough = np.where(under, 0.8, 0.45 - spot * 0.1)
    to8 = lambda a: (np.clip(a, 0, 1) * 255).astype(np.uint8)
    rgba = np.dstack([np.clip(colour, 0, 255).astype(np.uint8), to8(spot)])  # Alpha: where the spots glow.
    Image.fromarray(rgba, "RGBA").save(os.path.join(OUT, "T_LS_MushroomCap_BC.png"))
    Image.fromarray(to8(normal_map(height, 6.0))).save(os.path.join(OUT, "T_LS_MushroomCap_N.png"))
    Image.fromarray(to8(np.dstack([1 - 0.2 * (1 - spot) * under, rough, np.zeros_like(rough)]))).save(os.path.join(OUT, "T_LS_MushroomCap_ORM.png"))


def stem_texture():
    fibre = noise(51, 1.2, stretch=12.0)
    colour = mix((240, 230, 208), (200, 186, 158), fibre * 0.7 + noise(52, 2.0) * 0.3)
    to8 = lambda a: (np.clip(a, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(np.dstack([np.clip(colour, 0, 255).astype(np.uint8), np.zeros((SIZE, SIZE), np.uint8)]), "RGBA").save(
        os.path.join(OUT, "T_LS_MushroomStem_BC.png"))
    Image.fromarray(to8(normal_map(fibre, 5.0))).save(os.path.join(OUT, "T_LS_MushroomStem_N.png"))
    Image.fromarray(to8(np.dstack([np.ones_like(fibre), 0.75 + 0.1 * fibre, np.zeros_like(fibre)]))).save(os.path.join(OUT, "T_LS_MushroomStem_ORM.png"))


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, mesh in (("SM_LS_MushroomStem", stem()), ("SM_LS_MushroomCap", cap())):
        write_obj(os.path.join(OUT, name + ".obj"), mesh)
        print("Last Seed mushroom: {} has {} triangles".format(name, len(mesh.triangles)))
    cap_texture()
    stem_texture()
    print("Last Seed mushroom: wrote meshes and textures to", os.path.normpath(OUT))


if __name__ == "__main__":
    main()
