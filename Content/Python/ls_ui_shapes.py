"""Draw the UI's simple panel, focus rule and diamond primitives at double resolution."""
from pathlib import Path
from PIL import Image, ImageDraw
import random

out = Path(__file__).resolve().parents[1] / "LastSeed/SourceUI"
out.mkdir(parents=True, exist_ok=True)
panel = Image.new("RGBA", (1080, 330))
p = panel.load()
for y in range(330):
    for x in range(1080):
        alpha = int(222 * min(1, x / 250) * min(1, (1080 - x) / 90))
        p[x, y] = (69, 64, 33, alpha)
d = ImageDraw.Draw(panel)
d.line([(12, 4), (994, 4), (1025, 30), (1078, 30)], fill=(239, 230, 199, 210), width=2)
d.line([(20, 325), (1000, 325), (1030, 300), (1070, 300)], fill=(239, 230, 199, 210), width=2)
rng = random.Random(19)
for _ in range(120):
    x = rng.randrange(30, 1030)
    y = rng.choice((4, 325))
    d.line([(x, y), (x + rng.randrange(2, 10), y + rng.choice((-1, 1)))], fill=(240, 231, 202, rng.randrange(50, 140)))
panel.save(out / "T_UI_HintPanel.png")
diamond = Image.new("RGBA", (96, 96))
d = ImageDraw.Draw(diamond)
d.polygon([(48, 4), (92, 48), (48, 92), (4, 48)], fill=(55, 51, 31, 230), outline=(238, 227, 189, 255), width=3)
d.line([(48, 13), (83, 48), (48, 83), (13, 48), (48, 13)], fill=(207, 189, 131, 220), width=2)
d.line([(48, 29), (48, 53)], fill=(255, 243, 209, 255), width=6)
d.ellipse((45, 61, 51, 67), fill=(255, 243, 209, 255))
diamond.save(out / "T_UI_HintDiamond.png")
rule = Image.new("RGBA", (800, 100))
d = ImageDraw.Draw(rule)
d.line([(0, 96), (640, 96), (800, 97)], fill=(240, 207, 105, 240), width=2)
rule.save(out / "T_UI_FocusRule.png")
shade = Image.new("RGBA", (512, 32))
for x in range(512):
    for y in range(32):
        shade.putpixel((x, y), (5, 8, 7, int(210 * (1 - x / 511) ** 1.3)))
shade.save(out / "T_UI_PauseShade.png")
print("Generated four UI primitives.")
