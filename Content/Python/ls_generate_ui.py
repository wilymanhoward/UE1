# Last Seed - paints the UI's icons and ornaments as PNG files.
#
# Purpose: writes them to Content/LastSeed/SourceUI/. build_ui.py imports them as UI textures.
#   T_UI_Note, T_UI_Petal, T_UI_Clock   the HUD counters' icons
#   T_UI_Star                           white, so the results screen can tint it earned (gold) or missed (dark)
#   T_UI_FormSeed, T_UI_FormStone, T_UI_FormDandelion   the HUD's form icons
#   T_UI_Divider                        a thin gold line with a leaf in the middle, between a title and its text
#   T_UI_Shade                          dark on the left fading to clear, behind the main menu's buttons
#   T_UI_Glow                           a soft white dot, tinted for the energy bar's glow and sparks
# Each is drawn four times larger and shrunk, for smooth edges. The same input always gives the same images.
# Run: python ls_generate_ui.py (from Content/Python). Needs Pillow and numpy.

import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "LastSeed", "SourceUI")
GOLD = (243, 199, 98, 255)
GOLD_DARK = (176, 128, 52, 255)
CREAM = (246, 235, 210, 255)


def canvas(size):
    big = size * 4
    return Image.new("RGBA", (big, big), (0, 0, 0, 0)), big


def finish(image, size, name, glow=True):
    """Shrinks to size, with a soft dark halo so the icon reads on bright scenery too."""
    small = image.resize((size, size), Image.LANCZOS)
    if glow:
        alpha = small.split()[3].filter(ImageFilter.GaussianBlur(size / 28.0))
        halo = Image.new("RGBA", small.size, (0, 0, 0, 0))
        halo.putalpha(alpha.point(lambda a: int(a * 0.55)))
        halo.alpha_composite(small)
        small = halo
    small.save(os.path.join(OUT, name + ".png"))


def note(size=128):
    img, s = canvas(size)
    d = ImageDraw.Draw(img)
    # A beamed pair of notes: two tilted heads, two stems and a thick beam.
    for cx in (0.30, 0.70):
        cy = 0.74 if cx < 0.5 else 0.66
        head = [s * (cx - 0.13), s * (cy - 0.09), s * (cx + 0.11), s * (cy + 0.09)]
        d.ellipse(head, fill=GOLD)
    d.rectangle([s * 0.375, s * 0.22, s * 0.425, s * 0.74], fill=GOLD)
    d.rectangle([s * 0.775, s * 0.14, s * 0.825, s * 0.66], fill=GOLD)
    d.polygon([(s * 0.375, s * 0.22), (s * 0.825, s * 0.14), (s * 0.825, s * 0.26), (s * 0.375, s * 0.34)], fill=GOLD)
    finish(img, size, "T_UI_Note")


def petal(size=128):
    img, s = canvas(size)
    arr = np.zeros((s, s, 4), np.uint8)
    y, x = np.mgrid[0:s, 0:s] / s
    # A teardrop pointing up: wide and round below, narrowing to a tip.
    t = np.clip((0.9 - y) / 0.8, 0, 1)
    half = 0.32 * np.sin(np.pi * t ** 0.75) * (t > 0)
    inside = np.abs(x - 0.5) < half
    shade = 0.75 + 0.25 * (1 - np.abs(x - 0.5) / 0.32)
    vein = np.exp(-((x - 0.5) / 0.012) ** 2) * (t < 0.92) * 0.25
    for c, (lo, hi) in enumerate(zip(GOLD_DARK[:3], GOLD[:3])):
        arr[..., c] = np.clip(lo + (hi - lo) * shade * (0.6 + 0.4 * t) - vein * 120, 0, 255)
    arr[..., 3] = inside * 255
    finish(Image.fromarray(arr, "RGBA"), size, "T_UI_Petal")


def clock(size=128):
    img, s = canvas(size)
    d = ImageDraw.Draw(img)
    w = int(s * 0.07)
    d.ellipse([s * 0.12, s * 0.12, s * 0.88, s * 0.88], outline=CREAM, width=w)
    d.line([(s * 0.5, s * 0.5), (s * 0.5, s * 0.26)], fill=CREAM, width=w)
    d.line([(s * 0.5, s * 0.5), (s * 0.67, s * 0.6)], fill=CREAM, width=w)
    d.ellipse([s * 0.45, s * 0.45, s * 0.55, s * 0.55], fill=CREAM)
    finish(img, size, "T_UI_Clock")


def star(size=128):
    img, s = canvas(size)
    d = ImageDraw.Draw(img)
    points = []
    for k in range(10):
        a = -math.pi / 2 + k * math.pi / 5
        r = 0.46 if k % 2 == 0 else 0.19
        points.append((s * (0.5 + r * math.cos(a)), s * (0.53 + r * math.sin(a))))
    d.polygon(points, fill=(255, 255, 255, 255))  # Plain white: the results screen tints it.
    finish(img, size, "T_UI_Star", glow=False)


def form_seed(size=128):
    img, s = canvas(size)
    d = ImageDraw.Draw(img)
    d.ellipse([s * 0.2, s * 0.36, s * 0.8, s * 0.92], fill=(150, 104, 58, 255))
    d.ellipse([s * 0.28, s * 0.42, s * 0.56, s * 0.62], fill=(190, 140, 86, 255))
    d.line([(s * 0.5, s * 0.4), (s * 0.5, s * 0.16)], fill=(120, 196, 92, 255), width=int(s * 0.05))
    d.ellipse([s * 0.5, s * 0.08, s * 0.8, s * 0.24], fill=(140, 214, 104, 255))
    d.ellipse([s * 0.22, s * 0.14, s * 0.5, s * 0.28], fill=(120, 196, 92, 255))
    finish(img, size, "T_UI_FormSeed")


def form_stone(size=128):
    img, s = canvas(size)
    d = ImageDraw.Draw(img)
    d.polygon([(s * 0.14, s * 0.6), (s * 0.26, s * 0.28), (s * 0.52, s * 0.14), (s * 0.8, s * 0.26), (s * 0.9, s * 0.58),
               (s * 0.72, s * 0.86), (s * 0.34, s * 0.88)], fill=(132, 136, 140, 255))
    d.polygon([(s * 0.26, s * 0.3), (s * 0.52, s * 0.16), (s * 0.66, s * 0.3), (s * 0.4, s * 0.42)], fill=(170, 174, 178, 255))
    d.line([(s * 0.46, s * 0.5), (s * 0.58, s * 0.64), (s * 0.54, s * 0.8)], fill=(80, 82, 86, 255), width=int(s * 0.03))
    d.line([(s * 0.58, s * 0.64), (s * 0.74, s * 0.66)], fill=(80, 82, 86, 255), width=int(s * 0.03))
    finish(img, size, "T_UI_FormStone")


def form_dandelion(size=128):
    img, s = canvas(size)
    d = ImageDraw.Draw(img)
    d.line([(s * 0.5, s * 0.52), (s * 0.54, s * 0.95)], fill=(132, 186, 96, 255), width=int(s * 0.04))
    for k in range(28):
        a = 2 * math.pi * k / 28
        end = (s * (0.5 + 0.34 * math.cos(a)), s * (0.4 + 0.34 * math.sin(a)))
        d.line([(s * 0.5, s * 0.4), end], fill=(240, 244, 250, 255), width=int(s * 0.012))
        d.ellipse([end[0] - s * 0.03, end[1] - s * 0.03, end[0] + s * 0.03, end[1] + s * 0.03], fill=(255, 255, 255, 255))
    d.ellipse([s * 0.44, s * 0.34, s * 0.56, s * 0.46], fill=(214, 200, 150, 255))
    finish(img, size, "T_UI_FormDandelion")


def divider(width=512, height=48):
    img = Image.new("RGBA", (width * 4, height * 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w, h = img.size
    for side in (-1, 1):
        # A line that thins and fades toward each end.
        for k in range(200):
            t = k / 200
            x0 = w / 2 + side * (w * 0.06 + t * w * 0.42)
            x1 = w / 2 + side * (w * 0.06 + (t + 0.005) * w * 0.42)
            a = int(255 * (1 - t) ** 1.2)
            d.line([(x0, h / 2), (x1, h / 2)], fill=GOLD[:3] + (a,), width=max(2, int(6 * (1 - t))))
    # A single leaf lying along the line: two arcs meeting in a point at each end.
    leaf = []
    for k in range(41):
        a = math.pi * k / 40
        leaf.append((w / 2 - h * 0.42 * math.cos(a), h / 2 - h * 0.2 * math.sin(a)))
    for k in range(41):
        a = math.pi * k / 40
        leaf.append((w / 2 + h * 0.42 * math.cos(a), h / 2 + h * 0.2 * math.sin(a)))
    d.polygon(leaf, fill=GOLD)
    d.line([(w / 2 - h * 0.38, h / 2), (w / 2 + h * 0.38, h / 2)], fill=GOLD_DARK, width=4)
    img.resize((width, height), Image.LANCZOS).save(os.path.join(OUT, "T_UI_Divider.png"))


def shade(width=512, height=16):
    alpha = (np.linspace(1.0, 0.0, width) ** 1.15 * 240).astype(np.uint8)
    arr = np.zeros((height, width, 4), np.uint8)
    arr[..., :3] = (6, 12, 8)
    arr[..., 3] = alpha[None, :]
    Image.fromarray(arr, "RGBA").save(os.path.join(OUT, "T_UI_Shade.png"))


def glow(size=64):
    """A white dot that fades softly to clear, for tinted glows and sparks (Emberwood's energy bar)."""
    r = np.hypot(*np.meshgrid(np.linspace(-1, 1, size), np.linspace(-1, 1, size)))
    arr = np.zeros((size, size, 4), np.uint8)
    arr[..., :3] = 255
    arr[..., 3] = (np.exp(-(r / 0.45) ** 2) * np.clip(1.0 - r, 0.0, 1.0) * 255).astype(np.uint8)
    Image.fromarray(arr, "RGBA").save(os.path.join(OUT, "T_UI_Glow.png"))


def main():
    os.makedirs(OUT, exist_ok=True)
    for draw in (note, petal, clock, star, form_seed, form_stone, form_dandelion, divider, shade, glow):
        draw()
    print("Last Seed UI: wrote icons to", os.path.normpath(OUT))


if __name__ == "__main__":
    main()
