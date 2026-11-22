# Last Seed - the sound of a checkpoint lantern catching fire.
#
# Purpose: two stages, like ls_form_switch.py.
#   python -E -P ls_lantern_sound.py <folder> (outside Unreal, needs numpy and imageio-ffmpeg) writes
#     SourceSounds/SFX_LS_LanternLight.wav: a match struck and flaring (kingsrow's "MatchStrike07.wav", Freesound 181580,
#     its public HQ preview downloaded into <folder>), settling into a soft crackle from the recorded campfire already
#     used for Emberwood (SFX_LS_EmberwoodFire.wav, myLoop 852107). Both are CC0 recordings, credited in AUDIO_CREDITS.md.
#   import ls_lantern_sound; ls_lantern_sound.build() (in the editor) imports it as every checkpoint's Activate Sound.

import os
import sys
import wave

from ls_form_switch import RATE, SOURCE, decode

NAME = "SFX_LS_LanternLight"
MATCH = "181580_1857065-hq.mp3"
PEAK_DB = -6.0


def envelope(size, fade_in, fade_out):
    import numpy as np

    t = np.arange(size) / RATE
    return np.minimum(1.0, t / fade_in) * np.minimum(1.0, (t[-1] - t) / fade_out)


def main(folder):
    import numpy as np

    match = decode(os.path.join(folder, MATCH))[int(0.15 * RATE):int(1.75 * RATE)]
    match -= match.mean()
    # The strike's scrape is about 25 dB above the flame, so it is turned down to let the flare carry.
    t = np.arange(match.size) / RATE
    match *= np.where(t < 0.12, 0.12, 1.0) * envelope(match.size, 0.004, 0.25)
    match /= np.abs(match).max()

    fire = decode(os.path.join(SOURCE, "SFX_LS_EmberwoodFire.wav"))[:int(2.6 * RATE)]
    fire -= fire.mean()
    fire *= envelope(fire.size, 0.6, 1.0) / np.abs(fire).max()

    start = int(0.25 * RATE)
    out = np.zeros(start + fire.size)
    out[:match.size] += match
    out[start:] += 0.55 * fire
    out *= 10.0 ** (PEAK_DB / 20.0) / np.abs(out).max()
    assert np.isfinite(out).all() and 2.5 < out.size / RATE < 3.5
    with wave.open(os.path.join(SOURCE, NAME + ".wav"), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        handle.writeframes((out * 32767).astype("<i2").tobytes())
    print("Wrote {} ({:.2f} s)".format(NAME, out.size / RATE))


def build():
    import unreal

    task = unreal.AssetImportTask()
    task.set_editor_properties({"filename": os.path.join(SOURCE, NAME + ".wav"), "destination_path": "/Game/LastSeed/Audio",
                                "destination_name": NAME, "replace_existing": True, "automated": True, "save": True})
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    sound = unreal.load_asset("/Game/LastSeed/Audio/" + NAME)
    assert sound, NAME

    blueprint = unreal.load_asset("/Game/Blueprint/BP_CheckpointShrine")
    defaults = unreal.get_default_object(blueprint.generated_class())
    defaults.set_editor_property("activate_sound", sound)
    unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
    assert unreal.EditorAssetLibrary.save_loaded_asset(blueprint, False)
    # Placed checkpoints that overrode the sound would keep their own, so they get it too.
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    for actor in [a for a in actors if isinstance(a, unreal.CheckpointShrine)]:
        actor.modify()
        actor.set_editor_property("activate_sound", sound)
    assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    print("Checkpoint lanterns now play", NAME)


if __name__ == "__main__":
    main(sys.argv[1])
