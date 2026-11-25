# Last Seed - colour grades the main menu's Wildwood backdrop.
#
# Purpose: run outside Unreal (needs numpy and Pillow): python ls_menu_backdrop.py <raw capture.png>
# The raw capture is a 1920x1080 HighResShot of L_Level1_Wildwood in the editor's game view, from (-10300, -5900, 4700),
# pitch -9, yaw 106: the river valley. Writes LastSeed/SourceUI/T_UI_MenuBackdrop.png; then reimport it with
# build_ui.run("textures") or by reimporting /Game/UI/Textures/T_UI_MenuBackdrop.
# The grade: filmic contrast, warm golden highlights over cool teal shadows, richer greens, a soft sun glow from the
# upper right, and darker areas behind the logo and the lower-left buttons so both stay readable.

import os
import sys

import numpy as np
from PIL import Image

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "LastSeed", "SourceUI", "T_UI_MenuBackdrop.png")


def grade(img):
    h, w, _ = img.shape
    y, x = np.mgrid[0:h, 0:w]
    u, v = x / w, y / h

    # Filmic S-curve around mid-grey: deeper shadows, brighter but rolled-off highlights.
    img = np.clip(img, 0, 1)
    img = img - 0.06 * np.sin(2 * np.pi * img)
    img = np.clip((img - 0.03) / 0.97, 0, 1) ** 1.08

    # Saturation, a bit stronger in the mids (the foliage) than in the bright sky.
    luma = img @ np.array([0.2126, 0.7152, 0.0722])
    sat = 1.08 - 0.25 * np.clip(luma - 0.7, 0, 1)
    img = luma[..., None] + (img - luma[..., None]) * sat[..., None]

    # Tame the lime moss: where green leads red and blue, pull it towards a deeper emerald.
    lime = np.clip(img[..., 1] - np.maximum(img[..., 0], img[..., 2]), 0, 1)[..., None]
    img = img - lime * np.array([0.20, 0.32, -0.05])

    # Warmer white balance, like late afternoon.
    img = img * np.array([1.05, 1.0, 0.92])

    # Split tone: teal in the shadows, gold in the highlights.
    luma = np.clip(img @ np.array([0.2126, 0.7152, 0.0722]), 0, 1)[..., None]
    img = img + (1 - luma) ** 2 * np.array([-0.035, 0.010, 0.040]) + luma ** 2 * np.array([0.060, 0.025, -0.055])

    # Warm sun glow from the upper right, screened over the image.
    glow = np.clip(1 - np.hypot((u - 0.82) / 0.75, (v - 0.0) / 0.70), 0, 1) ** 1.8
    img = 1 - (1 - img) * (1 - glow[..., None] * np.array([0.42, 0.30, 0.10]))

    # Light shaping: vignette, the logo's darker pool, and the darker lower left behind the buttons.
    vignette = 1 - 0.45 * np.clip(((u - 0.55) ** 2 + (v - 0.45) ** 2 * 1.4) / 0.35, 0, 1) ** 1.5
    logo = 1 - 0.30 * np.clip(1 - np.hypot((u - 0.53) / 0.36, (v - 0.30) / 0.26), 0, 1) ** 0.9
    corner = 1 - 0.60 * np.clip(1 - np.hypot(u / 0.55, (v - 1.0) / 0.75), 0, 1) ** 1.1
    return np.clip(img * (vignette * logo * corner)[..., None], 0, 1)


if __name__ == "__main__":
    raw = np.asarray(Image.open(sys.argv[1]).convert("RGB")).astype(np.float64) / 255
    graded = grade(raw)
    assert graded.shape == raw.shape and np.isfinite(graded).all()
    Image.fromarray((graded * 255 + 0.5).astype(np.uint8)).save(OUT)
    print("wrote", os.path.normpath(OUT))
