"""Place the illustrated ambush where Dandelion lands across the river."""
from pathlib import Path
import unreal

LABEL = 'RiverbankWitchAmbush'
AUDIO = 'SFX_LS_RiverAmbush'


def place(x, y, z, yaw, half, target):
    import build_level1_wildwood as builder

    folder = '/Game/LastSeed/Audio'
    path = f'{folder}/{AUDIO}'
    if not unreal.EditorAssetLibrary.does_asset_exist(path):
        task = unreal.AssetImportTask()
        task.filename = str(Path(unreal.Paths.project_content_dir()) / 'LastSeed' / 'SourceSounds' / (AUDIO + '.wav'))
        task.destination_path = folder
        task.destination_name = AUDIO
        task.automated = True
        task.save = True
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        assert task.imported_object_paths, task.filename
    audio = unreal.load_asset(path)
    assert isinstance(audio, unreal.SoundWave)
    shots = []
    for number, duration, caption in [
        (5, 4.25, 'The Heart Tree’s last seed…\nI should have crushed you when I had the chance!'),
        (7, 3.25, '[The witch screams]'),
    ]:
        art = unreal.load_asset(f'{builder.INTRO_FOLDER}/T_LS_Intro_{number:02}')
        motion = unreal.load_asset(f'{builder.INTRO_FOLDER}/Motion/MI_LS_IntroMotion_{number:02}')
        assert art and motion
        shot = unreal.LSIntroShot()
        shot.set_editor_properties({'image': art, 'motion_material': motion, 'duration': duration,
                                    'fade_in': 0, 'caption': unreal.Text(caption)})
        shots.append(shot)
    actor = next((a for a in builder.actors.get_all_level_actors() if a.get_actor_label() == LABEL), None)
    if actor is None:
        actor = builder.spawn(unreal.StoryTrigger, x, y, z, LABEL, 'Flow', yaw)
    location = unreal.Vector(x,y,z)
    actor.modify()
    actor.set_actor_location(location, False, False)
    actor.set_actor_rotation(unreal.Rotator(yaw=yaw), False)
    actor.get_editor_property('box').set_box_extent(unreal.Vector(*half), True)
    actor.set_editor_properties({'intro_shots': shots, 'intro_music': audio, 'play_on_start': False,
                                 'wait_for_landing': True, 'reveal_target_offset': unreal.Vector(*target)-location})
    return actor


def build():
    import build_level1_wildwood as builder

    builder.require_map()
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    actor = place(15300, -2115, 2580, 26, (640, 560, 245), (12256, 1251, 4070))
    assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    print('Saved riverbank witch ambush:', actor.get_path_name())
