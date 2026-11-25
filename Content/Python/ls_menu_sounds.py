# Last Seed - the title menu's button sounds.
#
# Purpose: two stages, like ls_form_switch.py.
#   python ls_menu_sounds.py <folder> (outside Unreal, needs numpy and imageio-ffmpeg) cuts Freesound recordings,
#     downloaded into <folder> as their public HQ preview MP3s, into two sounds in LastSeed/SourceSounds:
#     SFX_LS_MenuHover  one soft woodblock hit (hollandm 692828)
#     SFX_LS_MenuClick  a wooden camera-handling click (qubodup 822568) over a short shimmer of a mark tree
#                       (jcdecha 235463)
#   import ls_menu_sounds; ls_menu_sounds.build() (in the editor) imports them and sets them as the hovered and
#     pressed sounds of every button in WBP_MainMenu and WBP_Controls.
# All are CC0 recordings, credited in AUDIO_CREDITS.md. Output is 48 kHz, 16-bit mono.

import os
import sys
import wave

from ls_form_switch import RATE, SOURCE, mix

NAMES = ("SFX_LS_MenuHover", "SFX_LS_MenuClick")
# Same layout as ls_form_switch.CUTS: (peak dBFS, [(file, start s, end s, fade-in s, starts at s, weight)]).
CUTS = {
    NAMES[0]: (-16.0, [("692828_5309408-hq.mp3", 0.0, 0.20, 0.001, 0.0, 1.0)]),
    NAMES[1]: (-9.0, [("822568_71257-hq.mp3", 0.0, 0.26, 0.001, 0.0, 1.0),
                      ("235463_3843719-hq.mp3", 0.25, 1.55, 0.15, 0.0, 0.35)]),
}
TAIL = 0.5  # Seconds of extra fade-out, so the chime rings off instead of stopping.
WIDGETS = ("/Game/UI/WBP_MainMenu", "/Game/UI/WBP_Controls")


def main(folder):
    import numpy as np

    for name, (peak_db, layers) in CUTS.items():
        samples = mix(folder, layers, peak_db)
        tail = min(samples.size // 3, int(TAIL * RATE))  # Never fades the attack of a short hit.
        samples[-tail:] *= np.cos(np.linspace(0, np.pi / 2, tail)) ** 2
        assert np.isfinite(samples).all() and np.abs(samples).max() <= 10.0 ** (peak_db / 20.0) + 1e-6, name
        with wave.open(os.path.join(SOURCE, name + ".wav"), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(RATE)
            handle.writeframes((samples * 32767).astype("<i2").tobytes())
        print("Last Seed menu sounds: wrote {} ({:.2f} s)".format(name, samples.size / RATE))


def build():
    import unreal
    from ls_style_menus import widgets_for

    sounds = []
    for name in NAMES:
        task = unreal.AssetImportTask()
        task.set_editor_properties({"filename": os.path.join(SOURCE, name + ".wav"), "destination_path": "/Game/LastSeed/Audio",
                                    "destination_name": name, "replace_existing": True, "automated": True, "save": True})
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        assert task.imported_object_paths, name
        sounds.append(unreal.load_asset("/Game/LastSeed/Audio/" + name))

    hover, click = (unreal.SlateSound() for _ in NAMES)
    hover.set_editor_property("resource_object", sounds[0])
    click.set_editor_property("resource_object", sounds[1])
    for path in WIDGETS:
        bp = unreal.load_asset(path)
        bp.modify()
        buttons = [w for w in widgets_for(bp).values() if isinstance(w, unreal.Button)]
        assert buttons, path
        for button in buttons:
            style = button.get_editor_property("widget_style")
            style.set_editor_property("hovered_slate_sound", hover)
            style.set_editor_property("pressed_slate_sound", click)
            button.set_style(style)
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        assert unreal.EditorAssetLibrary.save_loaded_asset(bp, False)
        print("Last Seed menu sounds: {} buttons in {}".format(len(buttons), path))


if __name__ == "__main__":
    main(sys.argv[1])
