# Last Seed - the form switch transition's sounds and settings.
#
# Purpose: two stages, like ls_wildwood_plan.py and build_level1_wildwood.py.
#   python ls_form_switch.py <folder> (outside Unreal, needs numpy and imageio-ffmpeg) cuts three Freesound recordings,
#     downloaded into <folder> as their public HQ preview MP3s, into short switch sounds in LastSeed/SourceSounds:
#     SFX_LS_SwitchSeed       a lip pop, like a seed popping free (deraj, 202230)
#     SFX_LS_SwitchStone      a stone dropped on grass, for the heavy form (dichardson, 570976)
#     SFX_LS_SwitchDandelion  one puff of breath, like blowing a dandelion clock (rykenn, 432170)
#   import ls_form_switch; ls_form_switch.build() (in the editor) imports them and fills in BP_SeedBall's
#     Form Switch Burst and each form's Switch Sound, colour, burst radius and shake.
# All three are CC0 field recordings, credited in AUDIO_CREDITS.md. Output is 48 kHz, 16-bit mono.

import os
import subprocess
import sys
import wave

SOURCE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "LastSeed", "SourceSounds")
RATE = 48000
NAMES = ("SFX_LS_SwitchSeed", "SFX_LS_SwitchStone", "SFX_LS_SwitchDandelion")
# name: (preview file, start s, end s, peak dBFS). Each excerpt is one clean event from the recording.
CUTS = {
    NAMES[0]: ("202230_3725006-hq.mp3", 0.12, 0.62, -6.0),
    NAMES[1]: ("570976_7987826-hq.mp3", 0.0, 0.53, -5.0),
    NAMES[2]: ("432170_2273357-hq.mp3", 8.33, 9.05, -8.0),
}


def decode(path):
    import imageio_ffmpeg
    import numpy as np

    raw = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-i", path, "-ac", "1", "-ar", str(RATE),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def cut(samples, start, end, peak_db):
    import numpy as np

    clip = samples[int(start * RATE):int(end * RATE)].copy()
    clip -= clip.mean()  # Removes any DC offset, which would thump at the fades.
    t = np.arange(clip.size) / RATE
    clip *= np.minimum(1.0, t / 0.004) * np.minimum(1.0, (t[-1] - t) / 0.08)  # No clicks at either end.
    return clip / np.abs(clip).max() * 10.0 ** (peak_db / 20.0)


def main(folder):
    import numpy as np

    for name, (file, start, end, peak_db) in CUTS.items():
        samples = cut(decode(os.path.join(folder, file)), start, end, peak_db)
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
