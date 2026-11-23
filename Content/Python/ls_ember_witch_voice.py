# Last Seed - the witch's voice across Emberwood, heard from far off in a huge stone hall.
#
# Purpose: two stages, like ls_lantern_sound.py.
#   python -E -P ls_ember_witch_voice.py (outside Unreal, needs numpy and imageio-ffmpeg) turns the six ElevenLabs takes
#     in SourceSounds/EmberWitch (VO_LS_EmberWitch_<n>_take.mp3, user-supplied Kristen "Cold Evil Queen Villain") into
#     VO_LS_EmberWitch_<n>.wav: her words clear and in front, with a big stone hall and two faint slow echoes behind
#     them, so she seems to watch Seed from somewhere vast and unseen.
#   import ls_ember_witch_voice; ls_ember_witch_voice.build() (in the editor, Emberwood open) imports them and gives
#     each witch line trigger its voice, holding the caption as long as she speaks.

import os
import sys
import wave

from ls_form_switch import RATE, SOURCE, decode

FOLDER = os.path.join(SOURCE, "EmberWitch")
COUNT = 6
LOUDNESS_DB = -14.0  # Average level while she speaks: loud enough to carry over the lava and fire ambience.
CEILING_DB = -1.0  # The limiter keeps every peak under this, so the louder line never clips.
REVERB_SECONDS = 2.4  # Time for the hall to fade by 60 dB: a big stone hall, short enough to keep words clear.
PRE_DELAY = 0.045  # The first reflections arrive late because the walls are far away.
ECHOES = ((0.42, 0.14), (0.84, 0.05))  # (delay s, level) slap-back off a distant wall.
DRY = 1.0  # Her direct voice leads, so every word is clear; the room sits behind it.
TAIL = 2.5  # Seconds of reverb left ringing after the last word.


def band(samples, low_hz, high_hz):
    """Band-limit by FFT with soft edges: losing the lows and highs is what air and distance do to a voice."""
    import numpy as np

    spectrum = np.fft.rfft(samples)
    hz = np.fft.rfftfreq(samples.size, 1.0 / RATE)
    gain = 1.0 / np.sqrt(1.0 + (low_hz / np.maximum(hz, 1.0)) ** 4) / np.sqrt(1.0 + (hz / high_hz) ** 4)
    return np.fft.irfft(spectrum * gain, samples.size)


def hall_impulse():
    """Decaying noise after a pre-delay, darker as it fades, with a few early reflections: a big stone room."""
    import numpy as np

    rng = np.random.default_rng(1117)
    t = np.arange(int(REVERB_SECONDS * RATE)) / RATE
    tail = rng.standard_normal(t.size) * np.exp(-6.9 * t / REVERB_SECONDS)
    tail = band(tail, 200.0, 3000.0)
    ir = np.zeros(int(PRE_DELAY * RATE) + t.size)
    ir[int(PRE_DELAY * RATE):] = tail
    for delay, level in ((0.023, 0.5), (0.041, 0.38), (0.067, 0.3), (0.097, 0.22)):
        ir[int((PRE_DELAY + delay) * RATE)] += level * np.abs(tail).max()
    return ir / np.sqrt((ir ** 2).sum())


def convolve(a, b):
    import numpy as np

    size = a.size + b.size - 1
    n = 1 << (size - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(a, n) * np.fft.rfft(b, n), n)[:size]


def treat(voice, ir):
    import numpy as np

    voice = voice - voice.mean()
    voice /= np.abs(voice).max()
    far = band(voice, 120.0, 7000.0)
    out = np.zeros(voice.size + int(TAIL * RATE) + ir.size)
    out[:far.size] += DRY * far
    for delay, level in ECHOES:
        start = int(delay * RATE)
        out[start:start + far.size] += level * far
    wet = convolve(out[:far.size + int(ECHOES[-1][0] * RATE)], ir)
    out[:wet.size] += 0.22 * wet[:out.size]  # About 6 dB under her voice: the hall is heard, the words stay clear.
    out = out[:voice.size + int(TAIL * RATE)]
    fade = int(0.8 * RATE)
    out[-fade:] *= np.linspace(1.0, 0.0, fade)
    return loud(out / np.abs(out).max())


def smooth(values, seconds):
    import numpy as np

    width = max(1, int(seconds * RATE))
    return np.convolve(values, np.ones(width) / width, mode="same")


def active_rms_db(samples):
    """Level over the 20 ms frames within 40 dB of the loudest: her speech, not the silences between lines."""
    import numpy as np

    frames = samples[:samples.size // 960 * 960].reshape(-1, 960)
    power = (frames ** 2).mean(axis=1)
    return 10.0 * np.log10(power[power > power.max() * 1e-4].mean())


def loud(mix):
    """Compress (3:1 above -20 dBFS) so quiet words come up to the loud ones, raise to LOUDNESS_DB, then limit."""
    import numpy as np
    from numpy.lib.stride_tricks import sliding_window_view

    level = np.sqrt(smooth(mix ** 2, 0.02)) + 1e-9
    threshold = 0.1
    mix = mix * smooth(np.where(level > threshold, (level / threshold) ** (1.0 / 3.0 - 1.0), 1.0), 0.03)
    mix *= 10.0 ** ((LOUDNESS_DB - active_rms_db(mix)) / 20.0)
    # Look-ahead limiter: the gain dips over the 4 ms around each peak, so it is pulled down smoothly, not clipped.
    ceiling = 10.0 ** (CEILING_DB / 20.0)
    half = int(0.004 * RATE)
    peaks = sliding_window_view(np.pad(np.abs(mix), half, mode="edge"), 2 * half + 1).max(axis=1)
    gain = np.minimum(1.0, ceiling / np.maximum(peaks, 1e-9))
    gain = sliding_window_view(np.pad(gain, half, mode="edge"), 2 * half + 1).min(axis=1)
    return np.clip(mix * smooth(gain, 0.004), -ceiling, ceiling)


def main():
    import numpy as np

    ir = hall_impulse()
    for n in range(1, COUNT + 1):
        voice = decode(os.path.join(FOLDER, "VO_LS_EmberWitch_%d_take.mp3" % n))
        out = treat(voice, ir)
        # Self-check: finite, never over the ceiling, as loud as asked, and the whole line plus its ringing tail kept.
        assert np.isfinite(out).all() and np.abs(out).max() <= 10.0 ** (CEILING_DB / 20.0) + 1e-9
        assert abs(active_rms_db(out) - LOUDNESS_DB) < 2.0, active_rms_db(out)
        assert out.size == voice.size + int(TAIL * RATE)
        with wave.open(os.path.join(FOLDER, "VO_LS_EmberWitch_%d.wav" % n), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(RATE)
            handle.writeframes((out * 32767).astype("<i2").tobytes())
        print("Wrote VO_LS_EmberWitch_%d (%.2f s, take %.2f s, %.1f dBFS while speaking)"
              % (n, out.size / RATE, voice.size / RATE, active_rms_db(out)))


def build():
    import unreal

    tasks = []
    for n in range(1, COUNT + 1):
        task = unreal.AssetImportTask()
        task.set_editor_properties({"filename": os.path.join(FOLDER, "VO_LS_EmberWitch_%d.wav" % n),
                                    "destination_path": "/Game/LastSeed/Audio", "destination_name": "VO_LS_EmberWitch_%d" % n,
                                    "replace_existing": True, "automated": True, "save": True})
        tasks.append(task)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        label = actor.get_actor_label()
        if isinstance(actor, unreal.TutorialTrigger) and label.startswith("Witch line "):
            sound = unreal.load_asset("/Game/LastSeed/Audio/VO_LS_EmberWitch_" + label.split()[-1])
            assert sound, label
            actor.modify()
            # The caption stays up while she speaks, but at least 7 s so a short line can still be read.
            actor.set_editor_properties({"voice": sound, "display_duration": max(7.0, sound.get_editor_property("duration") - 1.5)})
            print(label, "->", sound.get_name(), round(sound.get_editor_property("duration"), 2), "s")
    assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()


if __name__ == "__main__":
    main()
