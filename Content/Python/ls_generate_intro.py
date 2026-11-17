# Last Seed - the opening cutscene's pictures and music.
#
# Purpose: scores the opening cut using the storyboard frames selected in ls_intro_shots.py.
# Put full-size frames there (1920x1080 is best). Any that are missing are cut from storyboard.webp, the 4x4
# sheet of small frames, as stand-ins. It also writes MUS_LS_Intro_Recut.wav to Content/LastSeed/SourceSounds/, a score
# timed to the shots in ls_intro_shots.py: a calm forest theme, a dark turn when the witch comes, the curse's
# roar, the crash of the Heart Tree, silence, and a small hopeful glimmer as the seed falls.
# The Wildwood intro uses MUS_LS_Intro_Recordings.wav. This script still writes the earlier synthesized score.
# Run: python ls_generate_intro.py (from Content/Python). Needs numpy and Pillow.

import os

import numpy as np
from PIL import Image

import ls_generate_music as m
from ls_intro_shots import SHOTS, TOTAL, start_of

HERE = os.path.dirname(os.path.abspath(__file__))
FRAMES = os.path.join(HERE, "..", "LastSeed", "SourceIntro")
SHEET = os.path.join(FRAMES, "storyboard.webp")
LABEL = 0.14  # The top of each sheet panel holds its title, which is cut off.
RATE = m.RATE


def placeholders():
    """Cuts each missing frame out of the storyboard sheet and scales it to 1920x1080."""
    sheet = Image.open(SHEET).convert("RGB")
    w, h = sheet.size[0] / 4, sheet.size[1] / 4
    made = []
    for k in range(16):
        path = os.path.join(FRAMES, "Intro_{:02d}.png".format(k + 1))
        if os.path.exists(path):
            continue
        x0, y0 = (k % 4) * w, (k // 4) * h
        top = y0 + h * LABEL
        # Keep 16:9: trim the sides to match the height left after the title is cut off.
        keep = (y0 + h - top) * 16 / 9
        box = (round(x0 + (w - keep) / 2), round(top), round(x0 + (w + keep) / 2), round(y0 + h) - 1)
        sheet.crop(box).resize((1920, 1080), Image.LANCZOS).save(path)
        made.append(k + 1)
    return made


def music():
    n = int((TOTAL + 2.0) * RATE)
    out = np.zeros(n)
    put = lambda t, s, gain=1.0: m.place(out, t, s * gain, wrap=False)

    # Start the darker sound just before the cut to the witch.
    witch, curse, forest, tree, fall, landing = (start_of(frame) for frame in (5, 7, 9, 11, 14, 15))
    for k, chord in enumerate(((50, 54, 57), (47, 50, 54))):
        for note in chord:
            put(k * 4.0, m.pad_note(m.hz(note + 12), 5.0), 0.30)
    for t, duration, note in ((0.5, 1.5, 69), (2.8, 0.8, 66), (3.6, 2.4, 74), (6.5, 1.2, 73)):
        put(t, m.flute_note(m.hz(note), duration), 0.22)
    for note in (38, 41, 45):
        put(witch - 0.5, m.pad_note(m.hz(note), curse - witch + 1.5), 0.35)
    for t in np.arange(witch, curse, 0.9):
        put(t, heartbeat(), 0.6)
    put(curse - 2.0, swell(2.0), 0.5)

    put(curse, boom(2.5), 0.9)
    span = tree - curse
    rumble = m.rumble()
    decay = fade_out(span)
    put(curse, np.resize(rumble, len(decay)) * decay, 0.45)
    for note in (37, 38, 44):
        put(forest, sinking(m.hz(note), tree - forest), 0.22)

    put(tree + 2.5, creak(1.2), 0.4)
    put(tree + 3.8, boom(2.0), 1.0)
    put(fall + 0.5, wind(2.5), 0.18)
    put(fall + 2.0, bell(m.hz(79)), 0.23)
    put(landing, bell(m.hz(74)), 0.3)
    for note in (50, 57, 62, 66):
        put(landing, m.pad_note(m.hz(note + 12), TOTAL - landing + 1.0), 0.20)


    return out * fade_out_at(n, TOTAL + 1.5)


def fade_out(seconds):
    n = int(seconds * RATE)
    return np.linspace(1.0, 0.0, n) ** 1.5


def fade_out_at(n, seconds):
    curve = np.ones(n)
    start = int((seconds - 1.0) * RATE)
    curve[start:] = np.linspace(1, 0, n - start)
    return curve


def heartbeat():
    n = int(0.5 * RATE)
    t = np.arange(n) / RATE
    thump = np.sin(2 * np.pi * 55 * t) * np.exp(-t * 18)
    second = np.sin(2 * np.pi * 50 * t) * np.exp(-np.clip(t - 0.18, 0, None) * 20) * (t > 0.18)
    return thump + 0.7 * second


def swell(seconds):
    n = int(seconds * RATE)
    t = np.arange(n) / RATE
    noise = m.smooth(m.rng.normal(size=n), 40)
    tone = sum(np.sin(2 * np.pi * f * t) for f in (73.4, 77.8, 110.0))
    return (noise / np.abs(noise).max() * 0.5 + tone / 3) * (t / seconds) ** 2


def boom(seconds):
    n = int(seconds * RATE)
    t = np.arange(n) / RATE
    low = np.sin(2 * np.pi * (60 * np.exp(-t * 1.5) + 28) * t) * np.exp(-t * 1.6)
    noise = m.smooth(m.rng.normal(size=n), 8) * np.exp(-t * 3.5)
    return low + 0.6 * noise / np.abs(noise).max()


def sinking(freq, seconds):
    n = int(seconds * RATE)
    t = np.arange(n) / RATE
    f = freq * (1 - 0.12 * t / seconds)
    tone = np.sin(2 * np.pi * np.cumsum(f) / RATE) + 0.3 * np.sin(4 * np.pi * np.cumsum(f) / RATE)
    return tone * m.envelope(n, 0.8, seconds * 0.6)


def creak(seconds):
    n = int(seconds * RATE)
    t = np.arange(n) / RATE
    f = 140 + 60 * np.sin(2 * np.pi * 0.7 * t) + 25 * m.smooth(m.rng.normal(size=n), 2000) * 40
    grain = (np.sin(2 * np.pi * np.cumsum(f) / RATE) > 0.6).astype(float) - 0.2
    return m.smooth(grain, 6) * m.envelope(n, 0.2, 0.4)


def wind(seconds):
    n = int(seconds * RATE)
    t = np.arange(n) / RATE
    noise = m.smooth(m.rng.normal(size=n), 30)
    gust = 0.5 + 0.5 * np.sin(2 * np.pi * t / 3.2) * np.sin(2 * np.pi * t / 1.9 + 1)
    return noise / np.abs(noise).max() * gust * m.envelope(n, 1.0, 1.5)


def bell(freq):
    n = int(2.5 * RATE)
    t = np.arange(n) / RATE
    tone = np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * 2.0 * freq * t) * np.exp(-t * 3) + 0.2 * np.sin(2 * np.pi * 2.76 * freq * t) * np.exp(-t * 6)
    return tone * np.exp(-t * 1.6) * m.envelope(n, 0.004, 0.2)


def main():
    os.makedirs(FRAMES, exist_ok=True)
    made = placeholders()
    print("Last Seed intro: cut stand-ins for frames", made or "none (all frames supplied)")
    m.write("MUS_LS_Intro_Recut", music(), 0.85)
    print("Last Seed intro: wrote MUS_LS_Intro_Recut.wav, {:.1f} s for {} shots".format(TOTAL + 2.0, len(SHOTS)))


if __name__ == "__main__":
    main()
