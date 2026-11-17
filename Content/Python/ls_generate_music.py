# Last Seed - composes Level 1's music and its game sounds as WAV files.
#
# Purpose: the project has no audio, so this writes it from scratch to Content/LastSeed/SourceSounds/.
# build_level1_wildwood.fun_assets() imports them.
#   MUS_LS_Forest_0..4  five looping stems of one 16-bar piece (84 bpm, D major), all exactly the same length so they
#                       stay in sync: 0 soft pads, 1 woody percussion, 2 plucked bass, 3 flute melody, 4 high strings
#                       and birdsong. UAdaptiveMusicComponent starts them together and fades one in at the start and
#                       at each restoration milestone (25, 50, 75 and 100 percent), so the music grows back as the
#                       forest does.
#   MUS_LS_Finale       the whole band, brighter, ending on a held chord, for when the Heart Tree blooms.
#   SFX_LS_Boing        a bouncy mushroom.
#   SFX_LS_NoteChime    a Life Note. Each note found plays it a step higher up the scale (ALifeNote).
#   SFX_LS_StormRumble  a seamless loop of low thunder and wind for the Withering.
# The same input always gives the same sounds. 44.1 kHz, 16-bit mono.
# Run: python ls_generate_music.py (from Content/Python). Needs numpy.

import math
import os
import wave

import numpy as np

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "LastSeed", "SourceSounds")
RATE = 44100
BPM = 84.0
BEAT = 60.0 / BPM
BARS = 16
LOOP = int(round(RATE * BEAT * 4 * BARS))
rng = np.random.default_rng(84)

# Two bars per chord: D, Bm, G, A, D, Bm, Em, A. Each as MIDI notes of its triad.
CHORDS = [(50, 54, 57), (47, 50, 54), (43, 47, 50), (45, 49, 52), (50, 54, 57), (47, 50, 54), (52, 55, 59), (45, 49, 52)]
# The flute melody, as (start beat, length in beats, MIDI note), in D major pentatonic.
MELODY = [(0, 2, 69), (2, 1, 66), (3, 1, 69), (4, 3, 74),
          (8, 2, 71), (10, 1, 69), (11, 1, 66), (12, 3, 62),
          (16, 1, 71), (17, 1, 74), (18, 2, 76), (20, 2, 74), (22, 2, 71),
          (24, 2, 69), (26, 1, 71), (27, 1, 69), (28, 3, 64),
          (32, 1, 66), (33, 1, 69), (34, 2, 74), (36, 2, 78), (38, 2, 76),
          (40, 2, 74), (42, 1, 71), (43, 1, 69), (44, 3, 66),
          (48, 1, 64), (49, 1, 66), (50, 2, 71), (52, 2, 69), (54, 2, 76),
          (56, 1, 74), (57, 1, 76), (58, 1, 78), (59, 1, 76), (60, 3, 69)]


def hz(midi):
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)


def place(buffer, start_seconds, signal, wrap=True):
    """Adds signal into buffer at start_seconds. In a loop, what runs past the end comes back in at the start, so
    a note's tail rings across the seam and the loop is seamless."""
    start = int(round(start_seconds * RATE))
    n = len(signal)
    if wrap:
        idx = (start + np.arange(n)) % len(buffer)
        np.add.at(buffer, idx, signal)
    else:
        end = min(start + n, len(buffer))
        buffer[start:end] += signal[:end - start]


def envelope(n, attack, release, total=None):
    t = np.arange(n) / RATE
    total = total if total is not None else n / RATE
    up = np.clip(t / max(attack, 1e-4), 0, 1)
    down = np.clip((total - t) / max(release, 1e-4), 0, 1)
    return np.minimum(up, down)


def smooth(signal, width):
    return np.convolve(signal, np.ones(width) / width, mode="same")


def pad_note(freq, seconds):
    n = int(seconds * RATE)
    t = np.arange(n) / RATE
    vib = 1.0 + 0.003 * np.sin(2 * np.pi * 0.4 * t)
    tone = sum(np.sin(2 * np.pi * freq * k * vib * t) / k ** 1.6 for k in range(1, 6))
    return tone * envelope(n, 1.2, 1.6)


def pads(bars=None, tail=True):
    out = np.zeros(LOOP)
    for k, chord in enumerate(CHORDS):
        start = k * 8 * BEAT
        for note in chord:
            place(out, start, pad_note(hz(note + 12), 8 * BEAT + (1.6 if tail else 0.0)))
    return out


def percussion():
    out = np.zeros(LOOP)
    for beat in range(BARS * 4):
        t0 = beat * BEAT
        if beat % 2 == 0:  # A soft, low thump on beats one and three.
            n = int(0.35 * RATE)
            t = np.arange(n) / RATE
            freq = 55 + 35 * np.exp(-t * 18)
            place(out, t0, np.sin(2 * np.pi * np.cumsum(freq) / RATE) * np.exp(-t * 9) * 0.9)
        n = int(0.07 * RATE)  # A shaker on every off-beat.
        noise = rng.normal(size=n)
        noise = noise - smooth(noise, 6)
        place(out, t0 + BEAT / 2, noise * np.exp(-np.arange(n) / RATE * 55) * 0.18)
        if beat % 8 == 7:  # A woodblock to round off every second bar.
            n = int(0.12 * RATE)
            t = np.arange(n) / RATE
            place(out, t0 + BEAT / 2, np.sin(2 * np.pi * 820 * t) * np.exp(-t * 45) * 0.45)
    return out


def bass():
    out = np.zeros(LOOP)
    for k, chord in enumerate(CHORDS):
        for half in range(4):  # Root on beats one and three, a fifth on the second of each pair.
            note = chord[0] - 12 if half % 2 == 0 else chord[2] - 12
            n = int(1.4 * RATE)
            t = np.arange(n) / RATE
            f = hz(note)
            tone = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t)) * np.exp(-t * 2.6)
            place(out, (k * 8 + half * 2) * BEAT, tone * envelope(n, 0.01, 0.2))
    return out


def flute_note(freq, seconds):
    n = int((seconds + 0.25) * RATE)
    t = np.arange(n) / RATE
    vibrato = 1.0 + 0.006 * np.sin(2 * np.pi * 5.2 * t) * np.clip((t - 0.25) / 0.3, 0, 1)
    phase = 2 * np.pi * np.cumsum(freq * vibrato) / RATE
    tone = np.sin(phase) + 0.18 * np.sin(2 * phase) + 0.05 * np.sin(3 * phase)
    breath = smooth(rng.normal(size=n), 3) * 0.06
    return (tone + breath) * envelope(n, 0.07, 0.25)


def melody(notes=MELODY, length=LOOP, wrap=True):
    out = np.zeros(length)
    for beat, dur, note in notes:
        place(out, beat * BEAT, flute_note(hz(note), dur * BEAT * 0.95), wrap)
    return out


def strings():
    out = np.zeros(LOOP)
    for k, chord in enumerate(CHORDS):
        for note in chord[1:]:  # The third and fifth, two octaves up, from three slightly detuned voices.
            n = int((8 * BEAT + 2.0) * RATE)
            t = np.arange(n) / RATE
            tone = np.zeros(n)
            for cents in (-7, 0, 7):
                f = hz(note + 24) * 2 ** (cents / 1200)
                tone += sum(np.sin(2 * np.pi * f * h * t) / h for h in range(1, 5))
            place(out, k * 8 * BEAT, smooth(tone, 4) * envelope(n, 2.0, 2.0) * 0.5)
    for k in range(10):  # Birds: quick rising chirps, scattered through the loop.
        t0 = rng.uniform(0, LOOP / RATE)
        for c in range(rng.integers(2, 5)):
            n = int(0.09 * RATE)
            t = np.arange(n) / RATE
            f = rng.uniform(2600, 3800) * (1 + 0.6 * t / 0.09)
            place(out, t0 + c * 0.13, np.sin(2 * np.pi * np.cumsum(f) / RATE) * np.sin(np.pi * t / 0.09) * 0.35)
    return out


def finale():
    """The whole band through D, G, A, then a long held D chord with a chime arpeggio rising over it."""
    seconds = 4 * 4 * BEAT + 9.0
    n = int(seconds * RATE)
    out = np.zeros(n)
    chords = [(50, 54, 57), (43, 47, 50), (45, 49, 52), (50, 54, 57)]
    for k, chord in enumerate(chords):
        held = 4 * BEAT if k < 3 else 9.0
        for note in chord:
            place(out, k * 4 * BEAT, pad_note(hz(note + 12), held + 1.5) * 0.9, wrap=False)
            place(out, k * 4 * BEAT, pad_note(hz(note + 24), held + 1.5) * 0.35, wrap=False)
        tt = np.arange(int(1.6 * RATE)) / RATE
        place(out, k * 4 * BEAT, np.sin(2 * np.pi * hz(chord[0] - 12) * tt) * np.exp(-tt * 1.8) * 0.9, wrap=False)
    tune = [(0, 1, 69), (1, 1, 74), (2, 2, 78), (4, 1, 79), (5, 1, 78), (6, 2, 74), (8, 1, 76), (9, 1, 78), (10, 2, 81), (12, 4, 86)]
    out += melody(tune, n, wrap=False) * 0.8
    for k, note in enumerate((74, 78, 81, 86, 90, 93)):  # The chimes.
        tt = np.arange(int(2.5 * RATE)) / RATE
        bell = (np.sin(2 * np.pi * hz(note) * tt) + 0.3 * np.sin(2 * np.pi * hz(note) * 2.76 * tt)) * np.exp(-tt * 2.2)
        place(out, 12 * BEAT + k * 0.35, bell * 0.35, wrap=False)
    fade = np.clip((seconds - np.arange(n) / RATE) / 4.0, 0, 1)
    return out * fade


def boing():
    n = int(0.7 * RATE)
    t = np.arange(n) / RATE
    f = 170 + 420 * (1 - np.exp(-t * 7)) + 35 * np.sin(2 * np.pi * 16 * t) * np.exp(-t * 4)
    tone = np.sin(2 * np.pi * np.cumsum(f) / RATE) * np.exp(-t * 4.5)
    thump = np.sin(2 * np.pi * 70 * t) * np.exp(-t * 30)
    return (tone + 0.7 * thump) * envelope(n, 0.003, 0.05)


def chime():
    """A soft bell on G4. ALifeNote plays it up to a little over three times higher."""
    n = int(1.6 * RATE)
    t = np.arange(n) / RATE
    f = hz(67)
    tone = np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * 2.0 * f * t) * np.exp(-t * 3) + 0.25 * np.sin(2 * np.pi * 2.76 * f * t) * np.exp(-t * 6)
    shimmer = np.sin(2 * np.pi * 4 * f * t) * np.exp(-t * 9) * 0.15
    return (tone + shimmer) * np.exp(-t * 2.4) * envelope(n, 0.004, 0.1)


def rumble():
    seconds = 8.0
    n = int(seconds * RATE)
    t = np.arange(n) / RATE
    brown = np.cumsum(rng.normal(size=n))
    brown -= smooth(brown, 4000)
    low = smooth(brown, 60)
    wind = smooth(rng.normal(size=n), 12) * (0.5 + 0.5 * np.sin(2 * np.pi * t / seconds * 3 + 1.0))
    drone = np.sin(2 * np.pi * 42 * t) * (0.6 + 0.4 * np.sin(2 * np.pi * t / seconds * 2))
    sound = low / np.abs(low).max() + 0.35 * wind / np.abs(wind).max() + 0.5 * drone
    # Seamless: the last second fades into the first.
    fade = int(1.0 * RATE)
    w = np.linspace(0, 1, fade)
    sound[:fade] = sound[:fade] * w + sound[-fade:] * (1 - w)
    return sound[:-fade]


def write(name, samples, peak=0.8):
    samples = samples / max(np.abs(samples).max(), 1e-9) * peak if peak else samples
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        handle.writeframes((np.clip(samples, -1.0, 1.0) * 32767).astype("<i2").tobytes())


def main():
    os.makedirs(OUT, exist_ok=True)
    stems = [pads() * 0.8, percussion(), bass(), melody(), strings()]
    # Balance by ear-ish weights, then scale all five together so even the full mix never clips.
    weights = [0.30, 0.22, 0.32, 0.30, 0.16]
    stems = [s / np.abs(s).max() * w for s, w in zip(stems, weights)]
    full = sum(stems)
    scale = 0.92 / np.abs(full).max()
    for k, stem in enumerate(stems):
        assert len(stem) == LOOP
        write("MUS_LS_Forest_{}".format(k), stem * scale, peak=None)
    write("MUS_LS_Finale", finale(), 0.85)
    write("SFX_LS_Boing", boing(), 0.8)
    write("SFX_LS_NoteChime", chime(), 0.7)
    write("SFX_LS_StormRumble", rumble(), 0.85)
    print("Last Seed music: {} s loop in 5 stems, plus finale and 3 sounds, in {}".format(round(LOOP / RATE, 2), os.path.normpath(OUT)))


if __name__ == "__main__":
    main()
