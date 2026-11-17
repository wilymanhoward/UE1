"""Bake the Seed's dry seed coat on the same UVs as its rolling mesh."""

import math
from pathlib import Path
import random
import struct
import zlib

from ls_generate_player_meshes import seed_panels, smoothstep

SOURCE = Path(__file__).resolve().parents[1] / "LastSeed" / "SourceTextures" / "Seed"
SIZE = 512


def write_png(path, data, channels):
    def chunk(kind, payload):
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))

    stride = SIZE * channels
    scanlines = b"".join(b"\0" + data[row:row + stride] for row in range(0, len(data), stride))
    header = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6 if channels == 4 else 2, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) +
                     chunk(b"IDAT", zlib.compress(scanlines, 9)) + chunk(b"IEND", b""))


def bake():
    rng = random.Random(607)

    def noise_field(width, height):
        samples = [rng.uniform(-1.0, 1.0) for _ in range(width * (height + 1))]

        def sample(u, v):
            x, y = (u % 1.0) * width, min(0.999999, max(0.0, v)) * height
            col, row = int(x), int(y)
            sx, sy = smoothstep(0.0, 1.0, x - col), smoothstep(0.0, 1.0, y - row)
            next_col = (col + 1) % width
            a = samples[row * width + col] * (1.0 - sx) + samples[row * width + next_col] * sx
            b = samples[(row + 1) * width + col] * (1.0 - sx) + samples[(row + 1) * width + next_col] * sx
            return a * (1.0 - sy) + b * sy

        return sample

    mottling = noise_field(19, 23)
    fibres = noise_field(133, 18)
    pores = noise_field(199, 167)
    colour = bytearray()
    heightmap = []
    for y in range(SIZE):
        height = 1.0 - (y + 0.5) / SIZE
        for x in range(SIZE):
            u = (x + 0.5) / SIZE
            phase, inner, outer = seed_panels(u, height)
            cloud = mottling(u, height)
            fibre = fibres(u + 0.018 * cloud + 0.036 * height * height, height)
            pit = smoothstep(0.54, 0.91, pores(u, height))
            core = smoothstep(0.272, 0.318, phase) * (1.0 - smoothstep(0.66, 0.73, phase))
            cap = smoothstep(0.04, 0.18, height) * (1.0 - smoothstep(0.86, 0.99, height))
            seam = max(0.56 * (1.0 - smoothstep(0.004, 0.020, inner)),
                       0.39 * (1.0 - smoothstep(0.003, 0.016, outer))) * cap
            shade = cap * (0.73 * core + 0.27 * math.sin(math.pi * height))
            weathering = cap * (10.0 * cloud + 7.0 * fibre - 12.0 * pit)
            for base, lift, line in ((105, 39, 63), (75, 33, 43), (49, 23, 29)):
                coat = base + lift * shade - 13.0 * smoothstep(0.84, 1.0, height) + weathering
                colour.append(round(coat * (1.0 - seam) + line * seam))
            roughness = 0.76 - 0.09 * shade + 0.12 * seam + 0.07 * cloud + 0.045 * pit
            colour.append(round(255 * roughness))
            heightmap.append(cap * (0.30 * fibre + 0.22 * cloud - 0.25 * pit - 1.22 * seam))

    normals = bytearray()
    for y in range(SIZE):
        for x in range(SIZE):
            dx = (heightmap[y * SIZE + (x - 1) % SIZE] - heightmap[y * SIZE + (x + 1) % SIZE]) * 0.65
            dy = (heightmap[min(y + 1, SIZE - 1) * SIZE + x] - heightmap[max(y - 1, 0) * SIZE + x]) * 0.65
            length = math.sqrt(1.0 + dx * dx + dy * dy)
            normals.extend(round(127.5 * (1.0 + value / length)) for value in (dx, dy, 1.0))
    assert len(colour) == SIZE * SIZE * 4 and len(normals) == SIZE * SIZE * 3
    SOURCE.mkdir(parents=True, exist_ok=True)
    write_png(SOURCE / "T_LS_SeedShell_Color.png", colour, 4)
    write_png(SOURCE / "T_LS_SeedShell_Normal.png", normals, 3)


if __name__ == "__main__":
    bake()
