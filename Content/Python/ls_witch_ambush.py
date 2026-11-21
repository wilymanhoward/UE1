"""Place the illustrated ambush where Dandelion lands across the river."""
from pathlib import Path
import unreal

LABEL = 'RiverbankWitchAmbush'
AUDIO = 'SFX_LS_RiverAmbush'
ART = '/Game/LastSeed/Intro/RiverAmbush'


def shot_art(name, folder=ART, source_folder='RiverAmbush'):
    path = f'{folder}/T_LS_{name}'
    if not unreal.EditorAssetLibrary.does_asset_exist(path):
        source = Path(unreal.Paths.project_content_dir()) / 'LastSeed/SourceIntro' / source_folder
        task = unreal.AssetImportTask()
        task.set_editor_properties({'filename': str(source / (name + '.png')), 'destination_path': folder,
                                    'destination_name': 'T_LS_' + name, 'automated': True})
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        assert task.imported_object_paths, task.filename
        art = unreal.load_asset(path)
        art.set_editor_properties({'lod_group': unreal.TextureGroup.TEXTUREGROUP_UI,
                                    'mip_gen_settings': unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS,
                                    'never_stream': True})
        assert unreal.EditorAssetLibrary.save_loaded_asset(art, False)
    return unreal.load_asset(path)


def shot_motion(name, art, surge, folder=ART, material_name='M_LS_RiverAmbushMotion', shader=None, textures=None):
    editor = unreal.MaterialEditingLibrary
    assets = unreal.AssetToolsHelpers.get_asset_tools()
    material_path = f'{folder}/{material_name}'
    if not unreal.EditorAssetLibrary.does_asset_exist(material_path):
        material = assets.create_asset(material_name, folder, unreal.Material, unreal.MaterialFactoryNew())
        material.set_editor_property('material_domain', unreal.MaterialDomain.MD_UI)
        material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
        uv = editor.create_material_expression(material, unreal.MaterialExpressionTextureCoordinate, -500, 0)
        frame = editor.create_material_expression(material, unreal.MaterialExpressionTextureObjectParameter, -500, 130)
        frame.set_editor_properties({'parameter_name': 'FrameTex', 'texture': art,
                                      'sampler_type': unreal.MaterialSamplerType.SAMPLERTYPE_COLOR})
        clock = editor.create_material_expression(material, unreal.MaterialExpressionScalarParameter, -500, 270)
        clock.set_editor_property('parameter_name', 'ShotTime')
        cue = editor.create_material_expression(material, unreal.MaterialExpressionScalarParameter, -500, 370)
        cue.set_editor_property('parameter_name', 'Surge')
        render = editor.create_material_expression(material, unreal.MaterialExpressionCustom, -100, 0)
        inputs = {'UV': uv, 'FrameTex': frame, 'ShotTime': clock, 'Surge': cue}
        for index, (parameter, texture) in enumerate((textures or {}).items()):
            node = editor.create_material_expression(material, unreal.MaterialExpressionTextureObjectParameter, -500, 490 + index * 130)
            node.set_editor_properties({'parameter_name': parameter, 'texture': texture,
                                        'sampler_type': unreal.MaterialSamplerType.SAMPLERTYPE_COLOR})
            inputs[parameter] = node
        pins = []
        for label in inputs:
            pin = unreal.CustomInput()
            pin.set_editor_property('input_name', label)
            pins.append(pin)
        render.set_editor_properties({'inputs': pins, 'output_type': unreal.CustomMaterialOutputType.CMOT_FLOAT3,
                                      'code': (shader or Path(__file__).with_suffix('.hlsl')).read_text()})
        for label, node in inputs.items():
            assert editor.connect_material_expressions(node, '', render, label)
        assert editor.connect_material_property(render, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        opacity = editor.create_material_expression(material, unreal.MaterialExpressionConstant, -100, 300)
        opacity.set_editor_property('r', 1.0)
        assert editor.connect_material_property(opacity, '', unreal.MaterialProperty.MP_OPACITY)
        editor.recompile_material(material)
        assert unreal.EditorAssetLibrary.save_loaded_asset(material, False)
    else:
        material = unreal.load_asset(material_path)
    instance_name = 'MI_LS_' + name
    instance_path = f'{folder}/{instance_name}'
    if not unreal.EditorAssetLibrary.does_asset_exist(instance_path):
        instance = assets.create_asset(instance_name, folder, unreal.MaterialInstanceConstant,
                                       unreal.MaterialInstanceConstantFactoryNew())
    else:
        instance = unreal.load_asset(instance_path)
    editor.set_material_instance_parent(instance, material)
    editor.set_material_instance_texture_parameter_value(instance, 'FrameTex', art)
    editor.set_material_instance_scalar_parameter_value(instance, 'Surge', float(surge))
    editor.update_material_instance(instance)
    assert editor.get_material_instance_texture_parameter_value(instance, 'FrameTex') == art
    assert editor.get_material_instance_scalar_parameter_value(instance, 'Surge') == surge
    assert unreal.EditorAssetLibrary.save_loaded_asset(instance)
    return instance


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
    for name, surge, duration, caption in [
        ('WitchReveal', 0, 5.45, 'The Heart Tree’s last seed…\nI’ll crush you myself.'),
        ('WitchScream', 1, 3.25, '[The witch screams]'),
    ]:
        art = shot_art(name)
        motion = shot_motion(name, art, surge)
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
    from ls_river_curse import configure
    configure(actor)
    return actor


def build():
    import build_level1_wildwood as builder

    builder.require_map()
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    actor = place(15300, -2115, 2580, 26, (640, 560, 245), (12256, 1251, 4070))
    assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    print('Saved riverbank witch ambush:', actor.get_path_name())
