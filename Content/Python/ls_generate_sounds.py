# Last Seed - renders the original synthesized tree sound as a preview.
#
# Wildwood uses the recorded sound in Content/LastSeed/SourceSounds/. This preview is written to Saved/.
#   SFX_LS_TreeGrow  about 4.5 s: a low wooden groan as the dead trunk stirs, leaves rustling up as the crown fills
#                    out, and a rising run of soft bells over a warm swell, for the magic of it coming back to life.
# The same input always gives the same sound. 44.1 kHz, 16-bit mono.
# Run: python ls_generate_sounds.py (from Content/Python). Needs numpy.

import os
import wave

import numpy as np

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "Saved", "GeneratedAudio")
RATE = 44100


def envelope(t, attack, peak, release):
    """Rises from 0 at attack to 1 at peak, then falls back to 0 at release."""
    up = np.clip((t - attack) / max(peak - attack, 1e-6), 0.0, 1.0)
    down = np.clip((release - t) / max(release - peak, 1e-6), 0.0, 1.0)
    return np.minimum(up, down) ** 1.5


def smooth(signal, width):
    """A gentle low-pass: a moving average over width samples."""
    kernel = np.ones(width) / width
    return np.convolve(signal, kernel, mode="same")


def tree_grow():
    rng = np.random.default_rng(7)
    length = 4.6
    t = np.arange(int(RATE * length)) / RATE

    # Wood groan: a buzzy tone sliding up slowly, with an uneven wobble, kept low and muffled.
    pitch = 70.0 + 45.0 * np.clip(t / 1.6, 0.0, 1.0) + 6.0 * np.sin(2 * np.pi * 3.1 * t) + 4.0 * smooth(rng.normal(size=t.size), 2000) * 40.0
    phase = 2 * np.pi * np.cumsum(pitch) / RATE
    groan = sum(np.sin(phase * k) / k for k in range(1, 7))
    groan = smooth(groan, 12) * (0.6 + 0.4 * np.abs(smooth(rng.normal(size=t.size), 3000)) * 30.0)
    groan *= envelope(t, 0.0, 0.35, 1.9) * 0.35

    # Leaves: bright noise in bursts, swelling as the crown grows, fading as it settles.
    hiss = rng.normal(size=t.size)
    hiss = hiss - smooth(hiss, 9)  # Drops the low end, so it sounds like leaves, not wind.
    flutter = np.clip(smooth(rng.normal(size=t.size), 900) * 25.0 + 0.6, 0.0, 1.5)
    leaves = hiss * flutter * envelope(t, 0.4, 2.4, 4.5) * 0.22

    # Bells: a rising pentatonic run, each note a soft bell (a sine with a slightly out-of-tune upper partial).
    bells = np.zeros_like(t)
    notes = [523.25, 587.33, 659.25, 783.99, 880.0, 1046.5, 1174.66, 1318.51, 1567.98]
    for k, freq in enumerate(notes):
        start = 0.55 + k * 0.32
        local = t - start
        on = local >= 0.0
        decay = np.exp(-np.clip(local, 0.0, None) * 2.4) * on
        tone = np.sin(2 * np.pi * freq * local) + 0.35 * np.sin(2 * np.pi * freq * 2.76 * local) * np.exp(-np.clip(local, 0.0, None) * 5.0)
        bells += tone * decay * (0.16 + 0.02 * k)

    # A warm swell under it all, so it feels like something rising.
    pad = sum(np.sin(2 * np.pi * f * t) for f in (261.63, 329.63, 392.0)) * envelope(t, 0.3, 2.6, 4.6) * 0.07

    mix = groan + leaves + bells + pad
    mix *= np.minimum(1.0, t / 0.02) * np.minimum(1.0, (length - t) / 0.3)  # No clicks at either end.
    return mix / np.abs(mix).max() * 0.7


def write(name, samples):
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        handle.writeframes((np.clip(samples, -1.0, 1.0) * 32767).astype("<i2").tobytes())


def main():
    os.makedirs(OUT, exist_ok=True)
    sound = tree_grow()
    assert np.isfinite(sound).all() and np.abs(sound).max() <= 0.71
    write("SFX_LS_TreeGrow", sound)
    print("Last Seed sounds: wrote SFX_LS_TreeGrow ({:.1f} s) to {}".format(sound.size / RATE, os.path.normpath(OUT)))


if __name__ == "__main__":
    main()
