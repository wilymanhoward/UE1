# Last Seed - the form switch transition's sounds and settings.
#
# Purpose: two stages, like ls_wildwood_plan.py and build_level1_wildwood.py.
#   python ls_form_switch.py <folder> (outside Unreal, needs numpy and imageio-ffmpeg) cuts and layers Freesound
#     recordings, downloaded into <folder> as their public HQ preview MP3s, into short switch sounds in LastSeed/SourceSounds:
#     SFX_LS_SwitchSeed       a rustle of leaves under one soft wind-chime ring (Kinoton 347557, Anthousai 398496)
#     SFX_LS_SwitchStone      a stone dropped on grass, for the heavy form (dichardson, 570976)
#     SFX_LS_SwitchDandelion  one puff of breath, like blowing a dandelion clock (rykenn, 432170)
#   import ls_form_switch; ls_form_switch.build() (in the editor) imports them and fills in BP_SeedBall's
#     Form Switch Burst and each form's Switch Sound, colour, burst radius and shake.
# All are CC0 field recordings, credited in AUDIO_CREDITS.md. Output is 48 kHz, 16-bit mono.

import os
import subprocess
import sys
import wave

SOURCE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "LastSeed", "SourceSounds")
RATE = 48000
NAMES = ("SFX_LS_SwitchSeed", "SFX_LS_SwitchStone", "SFX_LS_SwitchDandelion")
# name: (peak dBFS, layers). Each layer is (preview file, start s, end s, fade-in s, starts at s, weight): one clean
# excerpt, scaled so its own peak is 1, then by weight, and mixed in at its start time.
CUTS = {
    NAMES[0]: (-8.0, [("347557_2247456-hq.mp3", 2.05, 2.75, 0.06, 0.0, 0.8),
                      ("398496_5923045-hq.mp3", 0.0, 1.2, 0.004, 0.05, 0.7)]),
    NAMES[1]: (-5.0, [("570976_7987826-hq.mp3", 0.0, 0.53, 0.004, 0.0, 1.0)]),
    NAMES[2]: (-8.0, [("432170_2273357-hq.mp3", 8.33, 9.05, 0.004, 0.0, 1.0)]),
}


def decode(path):
    import imageio_ffmpeg
    import numpy as np

    raw = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-i", path, "-ac", "1", "-ar", str(RATE),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def cut(samples, start, end, fade_in):
    import numpy as np

    clip = samples[int(start * RATE):int(end * RATE)].copy()
    clip -= clip.mean()  # Removes any DC offset, which would thump at the fades.
    t = np.arange(clip.size) / RATE
    clip *= np.minimum(1.0, t / fade_in) * np.minimum(1.0, (t[-1] - t) / 0.08)  # No clicks at either end.
    return clip / np.abs(clip).max()


def mix(folder, layers, peak_db):
    import numpy as np

    clips = [(int(at * RATE), weight * cut(decode(os.path.join(folder, file)), start, end, fade_in))
             for file, start, end, fade_in, at, weight in layers]
    out = np.zeros(max(offset + clip.size for offset, clip in clips))
    for offset, clip in clips:
        out[offset:offset + clip.size] += clip
    return out / np.abs(out).max() * 10.0 ** (peak_db / 20.0)


def main(folder):
    import numpy as np

    for name, (peak_db, layers) in CUTS.items():
        samples = mix(folder, layers, peak_db)
        assert np.isfinite(samples).all() and np.abs(samples).max() <= 10.0 ** (peak_db / 20.0) + 1e-6, name
        with wave.open(os.path.join(SOURCE, name + ".wav"), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(RATE)
            handle.writeframes((samples * 32767).astype("<i2").tobytes())
        print("Last Seed switch sounds: wrote {} ({:.2f} s)".format(name, samples.size / RATE))


def build():
    import unreal
    from ls_witch_exile import sound

    # Reimport over any older asset of the same name, so a recut WAV replaces it.
    for name in NAMES:
        task = unreal.AssetImportTask()
        task.set_editor_properties({"filename": os.path.join(SOURCE, name + ".wav"), "destination_path": "/Game/LastSeed/Audio",
                                    "destination_name": name, "replace_existing": True, "automated": True, "save": True})
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        assert task.imported_object_paths, name

    blueprint = unreal.load_asset("/Game/Blueprint/BP_SeedBall")
    burst = unreal.load_asset("/Game/FreeParticle_SoftTofu/Niagara/NS_Sparkling")
    assert blueprint and burst
    # Compiling first gives the Blueprint the new fields from C++ before they are filled in.
    unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
    defaults = unreal.get_default_object(blueprint.generated_class())
    defaults.set_editor_property("form_switch_burst", burst)

    settings = {
        unreal.SeedForm.SEED: (NAMES[0], unreal.LinearColor(0.45, 1.0, 0.35, 1.0), 110.0, 0.0),
        unreal.SeedForm.STONE: (NAMES[1], unreal.LinearColor(0.55, 0.5, 0.45, 1.0), 95.0, 6.0),
        unreal.SeedForm.DANDELION: (NAMES[2], unreal.LinearColor(1.0, 0.97, 0.85, 1.0), 170.0, 0.0),
    }
    form_data = defaults.get_editor_property("form_data")
    for form, (name, colour, radius, shake) in settings.items():
        entry = form_data[form]
        entry.set_editor_properties({"switch_sound": sound(name), "switch_color": colour,
                                     "switch_burst_radius": radius, "switch_shake": shake})
        form_data[form] = entry
    defaults.set_editor_property("form_data", form_data)

    unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
    # False saves even when not marked dirty. Editing class defaults from Python doesn't mark it.
    assert unreal.EditorAssetLibrary.save_loaded_asset(blueprint, False)
    print("Last Seed switch: filled in BP_SeedBall's switch burst and sounds")


if __name__ == "__main__":
    main(sys.argv[1])
