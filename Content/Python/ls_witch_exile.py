"""Author the illustrated Wildwood ending and the playable Emberwood arrival."""

from pathlib import Path
import math
import random

import unreal

from ls_generate_player_meshes import Mesh
from ls_witch_ambush import shot_art, shot_motion
from ls_world_common import (
    hide_component, import_generated_mesh, kill_volume, mesh_actor, point_light, spawn,
)

ART = "/Game/LastSeed/Intro/WitchExile"
WILDWOOD = "/Game/LastSeed/Maps/L_Level1_Wildwood"
DESTINATION = "/Game/LastSeed/Maps/L_Level2_Emberwood"  # Built by ls_emberwood.py in a copy of the lava pack map
FOLDER = "Emberwood Arrival"
LAVA_Z = -285.0


def shot(name, index, duration, caption="", seed_match=None):
    art = shot_art(name, folder=ART, source_folder="WitchExile")
    seed = shot_art("PlantingSeedSprite", folder=ART, source_folder="WitchExile")
    motion = shot_motion(name, art, index, folder=ART, material_name="M_LS_ExilePlantingMotion",
                         shader=Path(__file__).with_suffix(".hlsl"), textures={"SeedTex": seed})
    result = unreal.LSIntroShot()
    result.set_editor_properties({"image": art, "motion_material": motion, "duration": duration,
                                  "fade_in": 0.0, "caption": unreal.Text(caption)})
    if seed_match is not None:
        result.set_editor_property("seed_match", unreal.Vector(*seed_match))
    return result


def sound(name, loop=False):
    folder = "/Game/LastSeed/Audio"
    path = f"{folder}/{name}"
    if not unreal.EditorAssetLibrary.does_asset_exist(path):
        source = Path(unreal.Paths.project_content_dir()) / "LastSeed/SourceSounds" / f"{name}.wav"
        task = unreal.AssetImportTask()
        task.set_editor_properties({"filename": str(source), "destination_path": folder, "destination_name": name,
                                    "automated": True})
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        assert task.imported_object_paths, name
    wave = unreal.load_asset(path)
    assert isinstance(wave, unreal.SoundWave)
    wave.set_editor_property("looping", loop)
    assert unreal.EditorAssetLibrary.save_loaded_asset(wave, False)
    return wave


def lava_plane():
    surface = Mesh()
    for x, y in ((-10000, -13000), (16000, -13000), (16000, 13000), (-10000, 13000)):
        surface.add_vertex((x, y, 0.0), (x / 820.0, y / 820.0))
    surface.triangles = [(0, 1, 2), (0, 2, 3)]
    surface.smooth_normals()
    return import_generated_mesh("SM_LS_EmberwoodLava", surface, nanite=False)


def basalt_material():
    path = "/Game/LastSeed/Materials/M_LS_EmberBasalt"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        return unreal.load_asset(path)
    material = unreal.EditorAssetLibrary.duplicate_asset("/Game/LastSeed/Materials/M_LS_Rock", path)
    editor = unreal.MaterialEditingLibrary
    base = editor.get_material_property_input_node(material, unreal.MaterialProperty.MP_BASE_COLOR)
    tint = editor.create_material_expression(material, unreal.MaterialExpressionConstant3Vector, -190, 365)
    tint.set_editor_property("constant", unreal.LinearColor(0.19, 0.23, 0.32))
    darken = editor.create_material_expression(material, unreal.MaterialExpressionMultiply, 40, 70)
    assert editor.connect_material_expressions(base, "", darken, "A")
    assert editor.connect_material_expressions(tint, "", darken, "B")
    assert editor.connect_material_property(darken, "", unreal.MaterialProperty.MP_BASE_COLOR)
    editor.recompile_material(material)
    assert unreal.EditorAssetLibrary.save_loaded_asset(material, False)
    return material


def basalt_shelf():
    mesh = Mesh()
    rng = random.Random(305)
    sides = 22
    spans = [rng.uniform(93.5, 104.0) for _ in range(sides)]
    for ring, (scale, elevation) in enumerate(((0.48, 0.0), (1, -1.5), (1.06, -10), (0.91, -45), (0.83, -86), (0.65, -151))):
        for side, span in enumerate(spans):
            angle = side * 2 * math.pi / sides
            radius = span * scale + (rng.uniform(-6, 6) if ring >= 2 else 0)
            x, y = radius * math.cos(angle), radius * math.sin(angle)
            mesh.add_vertex((x, y, elevation + rng.uniform(-1, 1) * min(ring * 2.5, 6)), (x/85, y/85))
    for side in range(1, sides-1):
        mesh.triangles.append((0, side, side+1))
    for ring in range(5):
        for side in range(sides):
            a = ring*sides + side
            b = ring*sides + (side+1) % sides
            mesh.triangles.extend(((a, a+sides, b), (b, a+sides, b+sides)))
    mesh.smooth_normals()
    return import_generated_mesh("SM_LS_BasaltShelf", mesh, nanite=False)


def dress_arrival(actors, arrival_shot, ambience):
    current = actors.get_all_level_actors()
    old = [actor for actor in current if str(actor.get_folder_path()) == "World/" + FOLDER]
    if old:
        assert actors.destroy_actors(old)
    start = next(actor for actor in current if isinstance(actor, unreal.PlayerStart))
    floor = next(actor for actor in current if actor.get_actor_label() == "Floor")
    hide_component(floor.static_mesh_component)
    floor.static_mesh_component.set_collision_profile_name("NoCollision")
    start.set_actor_location(unreal.Vector(-235, 0, 104), False, False)
    start.set_actor_rotation(unreal.Rotator(yaw=0, pitch=0, roll=0), False)

    lava = unreal.load_asset("/Game/Lava_Material/Material/M_Lava_01")
    rock = basalt_material()
    island = basalt_shelf()
    assert lava and rock and unreal.EditorAssetLibrary.does_asset_exist(island)
    molten = mesh_actor(lava_plane(), 0, 0, LAVA_Z, FOLDER, material=lava, label="Molten forest floor")
    molten.static_mesh_component.set_cast_shadow(False)
    hazard = kill_volume(3000, 0, LAVA_Z - 370, 13000, 13000, 365)
    hazard.set_folder_path("World/" + FOLDER)

    platforms = ((0, 0, 44, 870, 740), (1480, -70, 86, 410, 405),
                 (2480, 120, 128, 405, 370), (3460, -30, 174, 405, 360), (4760, 80, 164, 710, 635))
    for index, (x, y, top, rx, ry) in enumerate(platforms):
        mesh_actor(island, x, y, top, FOLDER, (rx/100, ry/100, 3.0 + 0.24*index), index*58,
                   rock, "Basalt shelf")
        collision = mesh_actor("/Engine/BasicShapes/Cylinder", x, y, top-44, FOLDER,
                               (rx/50*0.96, ry/50*0.96, 0.88), 0, label="Basalt shelf collision")
        hide_component(collision.static_mesh_component)
        collision.static_mesh_component.set_collision_profile_name("BlockAll")

    rng = random.Random(547)
    for index in range(42):
        side = -1 if index % 2 else 1
        x = rng.uniform(-900, 12100)
        y = side * rng.uniform(1300, 8500)
        radius = rng.uniform(100, 450)
        top = LAVA_Z + rng.uniform(35, 155)
        mesh_actor(island, x, y, top, FOLDER, (radius/100, radius/115, 1.9), rng.uniform(0, 360),
                   rock, "Burnt outcrop")
        tree = ("/Game/LastSeed/Meshes/SM_LS_GnarledTree" if index % 3 == 0 else
                f"/Game/Wildwood/Model/DeadTrunk/SM_DeadTrunk_{1+index%6:02d}")
        scale = rng.uniform(0.45, 1.8) if index % 3 == 0 else rng.uniform(1.8, 4.0)
        mesh_actor(tree, x, y, top-24, FOLDER, (scale, scale, scale), rng.uniform(0, 360), rock, "Charred tree")
    for x, y in ((-240, 1040), (1510, -810), (3180, 900), (5000, -880), (7100, 1260)):
        point_light(x, y, LAVA_Z+220, (unreal.LinearColor(1.0, 0.28, 0.055)), 140.0, 2100.0, FOLDER)
    fog = next(actor for actor in current if isinstance(actor, unreal.ExponentialHeightFog))
    haze = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    haze.set_fog_density(0.032)
    haze.set_fog_height_falloff(0.30)
    haze.set_fog_inscattering_color(unreal.LinearColor(0.088, 0.051, 0.074))
    haze.set_start_distance(550.0)
    fog.set_actor_location(unreal.Vector(0, 0, 110), False, False)
    sun = next(actor for actor in current if isinstance(actor, unreal.DirectionalLight))
    sun.set_actor_rotation(unreal.Rotator(pitch=-11.0, yaw=138.0, roll=0.0), False)
    key = sun.get_component_by_class(unreal.DirectionalLightComponent)
    key.set_intensity(1.9)
    key.set_specular_scale(0.2)
    key.set_light_color(unreal.LinearColor(0.76, 0.63, 0.78))
    sky = next(actor for actor in current if isinstance(actor, unreal.SkyLight))
    sky.get_component_by_class(unreal.SkyLightComponent).set_intensity(0.42)
    grade = spawn(unreal.PostProcessVolume, 0, 0, 0, "Emberwood exposure", FOLDER)
    grade.set_editor_property("unbound", True)
    settings = grade.get_editor_property("settings")
    settings.set_editor_properties({"override_auto_exposure_bias": True, "auto_exposure_bias": -1.05,
                                    "override_bloom_intensity": True, "bloom_intensity": 0.25})
    grade.set_editor_property("settings", settings)

    bed = spawn(unreal.AmbientSound, 0, 0, 0, "Emberwood fire", FOLDER)
    bed.audio_component.set_sound(ambience)
    bed.audio_component.set_volume_multiplier(0.55)
    bed.audio_component.set_editor_property("allow_spatialization", False)
    intro = spawn(unreal.StoryTrigger, 0, 0, -1400, "Emberwood landing", FOLDER)
    intro.set_editor_properties({"intro_shots": [arrival_shot], "intro_music": ambience,
                                 "play_on_start": True, "arrival_cutscene": True})


def exile_shots():
    travel = [shot("PlantingSoil", 0, 3.0),
              shot("WitchNotYet", 1, 3.65, "Not yet."),
              shot("WitchBanishment", 2, 4.5, "By ash and flame… I cast you out!")]
    arrival = shot("ExileEmberwood", 3, 5.3)
    return travel, arrival


def setup_goal(actors, goal, travel):
    goal.set_editor_properties({"travel_shots": travel, "travel_audio": sound("SFX_LS_ExilePlantingVoiced"),
                                "require_jump": True})
    goal.get_editor_property("box").set_box_extent(unreal.Vector(590, 390, 235), True)
    position = goal.get_actor_transform().transform_location(unreal.Vector(-515, 0, -130))
    hint = next((a for a in actors.get_all_level_actors() if a.get_actor_label() == "Exile jump hint"), None)
    if hint is None:
        hint = spawn(unreal.TutorialTrigger, position.x, position.y, position.z, "Exile jump hint", "Flow",
                     goal.get_actor_rotation().yaw)
    hint.get_editor_property("box").set_box_extent(unreal.Vector(175, 340, 210), True)
    hint.set_editor_property("message", unreal.Text("Take Seed form, then jump into the dirt to plant yourself."))
    hint.set_editor_property("display_duration", 7.0)


def build():
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    assert editor.get_editor_world().get_path_name().split(".")[0] == WILDWOOD
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    goals = [actor for actor in actors.get_all_level_actors() if isinstance(actor, unreal.LevelGoal)]
    assert len(goals) == 1 and goals[0].get_editor_property("next_level") == unreal.load_asset(DESTINATION)
    travel, _ = exile_shots()

    # Emberwood, arrival included, is built by ls_emberwood.py in its copy of the lava pack map. dress_arrival made
    # the earlier, plainer L_Level2 and is kept only for that map.
    import ls_emberwood
    ls_emberwood.build()
    assert levels.load_level(WILDWOOD)
    goal = next(actor for actor in actors.get_all_level_actors() if isinstance(actor, unreal.LevelGoal))
    setup_goal(actors, goal, travel)
    assert levels.save_current_level()
