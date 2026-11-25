# Last Seed - mixes the riverbank witch ambush's sound (SFX_LS_RiverAmbush.wav), without any river ambience.
#
# The witch's Kristen take (VO_LS_WitchKristen.mp3, user-supplied) starts 1.70 s in and peaks at -3 dBFS; her recorded
# scream (SFX_LS_WitchAttackScream.wav) starts at 6.95 s and peaks at -10 dBFS. 10.7 s long, stereo 48 kHz, as before.
# Run: python -E -P ls_river_ambush_mix.py (from Content/Python). Needs numpy and imageio-ffmpeg.
# Then reimport /Game/LastSeed/Audio/SFX_LS_RiverAmbush in the editor (ls_witch_ambush.place does this on a rebuild).

import os
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # -P leaves this folder off the path.
from ls_form_switch import RATE, SOURCE, decode

LENGTH = 10.7
LAYERS = [("VO_LS_WitchKristen.mp3", 1.70, -3.0), ("SFX_LS_WitchAttackScream.wav", 6.95, -10.2)]  # file, start s, peak dBFS


def load(name):
    path = os.path.join(SOURCE, name)
    if name.endswith(".mp3"):
        return decode(path)
    with wave.open(path) as w:
        assert w.getframerate() == RATE and w.getsampwidth() == 2
        samples = np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, w.getnchannels()).mean(axis=1)
    return samples / 32768.0


def main():
    mix = np.zeros(int(LENGTH * RATE))
    for name, start, peak_db in LAYERS:
        clip = load(name)
        clip = clip - clip.mean()
        clip *= 10 ** (peak_db / 20) / np.abs(clip).max()
        at = int(start * RATE)
        end = min(mix.size, at + clip.size)
        mix[at:end] += clip[:end - at]
    assert np.abs(mix).max() <= 10 ** (-1 / 20), "clipping headroom lost"
    pcm = (np.repeat(mix[:, None], 2, axis=1) * 32767).astype(np.int16)
    with wave.open(os.path.join(SOURCE, "SFX_LS_RiverAmbush.wav"), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())
    print("Wrote SFX_LS_RiverAmbush.wav: voice and scream only, %.1f s" % LENGTH)


if __name__ == "__main__":
    main()
