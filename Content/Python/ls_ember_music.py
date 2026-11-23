# Last Seed - Emberwood's background music: "Juggernaut" by Scott Buckley (scottbuckley.com.au), CC BY 4.0.
# Chugging, malevolent strings, brass and percussion building to an epic march: a journey through Mordor. From the
# composer of Wildwood's "A Dragon's Lullaby", so the two levels sound like one serious score.
#
# Purpose: two stages, like ls_lantern_sound.py.
#   python -E -P ls_ember_music.py <Juggernaut.mp3> (outside Unreal, needs numpy and imageio-ffmpeg) turns the composer's
#     MP3 (scottbuckley.com.au/library/juggernaut/) into
#     SourceSounds/MUS_LS_Juggernaut_Loop.wav: stereo 48 kHz, brought down to sit under the witch's voice and the lava,
#     and with its last seconds crossfaded into its first, so the loop has no seam.
#   import ls_ember_music; ls_ember_music.build() (in the editor, Emberwood open) imports it as a looping sound and
#     gives Emberwood a MusicManager that plays it from the start of the level.

import os
import subprocess
import sys
import wave

from ls_form_switch import RATE, SOURCE

NAME = "MUS_LS_Juggernaut_Loop"
LOUDNESS_DB = -22.0  # Wildwood's loop sits at about -23 dBFS; the witch speaks at about -14 over it.
SEAM = 4.0  # Seconds of the end laid over the start: long, so the big ending eases back into the opening.


def decode_stereo(path):
    import imageio_ffmpeg
    import numpy as np

    raw = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-i", path, "-ac", "2", "-ar", str(RATE),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64).reshape(-1, 2)


def main(source):
    import numpy as np

    music = decode_stereo(source)
    music -= music.mean(axis=0)
    # Equal-power crossfade of the last SEAM seconds into the first, then the tail is dropped: the end now leads
    # straight back into the start.
    seam = int(SEAM * RATE)
    t = np.linspace(0.0, np.pi / 2.0, seam)[:, None]
    looped = music[:-seam].copy()
    looped[:seam] = music[:seam] * np.sin(t) + music[-seam:] * np.cos(t)
    level = 10.0 * np.log10((looped[np.abs(looped).max(axis=1) > 1e-4] ** 2).mean())
    looped *= 10.0 ** ((LOUDNESS_DB - level) / 20.0)
    # Self-check: finite, never clipping, at the level asked, and the loop's join matches its start.
    assert np.isfinite(looped).all() and np.abs(looped).max() < 0.99, np.abs(looped).max()
    assert abs(10.0 * np.log10((looped[np.abs(looped).max(axis=1) > 1e-4] ** 2).mean()) - LOUDNESS_DB) < 0.5
    with wave.open(os.path.join(SOURCE, NAME + ".wav"), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        handle.writeframes((looped * 32767).astype("<i2").tobytes())
    print("Wrote {} ({:.1f} s, peak {:.1f} dBFS)".format(NAME, looped.shape[0] / RATE, 20 * np.log10(np.abs(looped).max())))


def build():
    import unreal

    task = unreal.AssetImportTask()
    task.set_editor_properties({"filename": os.path.join(SOURCE, NAME + ".wav"), "destination_path": "/Game/LastSeed/Audio",
                                "destination_name": NAME, "replace_existing": True, "automated": True, "save": True})
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    sound = unreal.load_asset("/Game/LastSeed/Audio/" + NAME)
    assert sound, NAME
    sound.set_editor_property("looping", True)
    assert unreal.EditorAssetLibrary.save_loaded_asset(sound, False)

    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    managers = [a for a in actors.get_all_level_actors() if a.get_class().get_name() == "MusicManager"]
    if not managers:
        manager = actors.spawn_actor_from_class(unreal.load_class(None, "/Script/Assignment1.MusicManager"), unreal.Vector(0, 0, 2000))
        manager.set_actor_label("MusicManager")
        manager.set_folder_path("World/Emberwood/Flow")
        managers = [manager]
    for manager in managers:
        music = manager.get_component_by_class(unreal.AdaptiveMusicComponent)
        music.set_editor_properties({"stems": [sound], "finale_track": None})
    assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    print("Emberwood plays", NAME)


if __name__ == "__main__":
    main(sys.argv[1])
