# Last Seed - sets up the game's UI in the editor.
#
# Purpose: the screens' layouts (WBP_MainMenu, WBP_PauseMenu, WBP_Controls, WBP_HUD, WBP_StoryCard, WBP_Results) are
# Widget Blueprints in /Game/UI, built on the C++ classes that hold their logic. This script does the parts around them:
#   textures   imports the icons and the menu backdrop painted by ls_generate_ui.py, as UI textures
#   menu_level makes L_MainMenu, with a game mode that shows the main menu and spawns no ball
#   wire       points the player controller, the HUD and the menus at their layouts, levels and icons
# Run each stage once, from the editor's Python console: import build_ui; build_ui.run("textures"), and so on.
# Safe to rerun.

import os

import unreal

SOURCE = os.path.join(unreal.Paths.project_content_dir(), "LastSeed", "SourceUI")
TEXTURES = "/Game/UI/Textures"
MENU_MAP = "/Game/LastSeed/Maps/L_MainMenu"
MENU_MODE = "/Game/Blueprint/BP_LSGameMode_Menu"
LEVEL1 = "/Game/LastSeed/Maps/L_Level1_Wildwood"
LEVEL2 = "/Game/LastSeed/Maps/L_Level2_Emberwood"
STAGES = ["textures", "menu_level", "wire"]

assets = unreal.EditorAssetLibrary


def textures():
    """Every PNG in SourceUI, as a crisp UI texture: no mipmaps, never streamed out, no compression artefacts."""
    tasks = []
    for name in sorted(os.listdir(SOURCE)):
        if name.endswith(".png"):
            task = unreal.AssetImportTask()
            task.filename = os.path.join(SOURCE, name)
            task.destination_path = TEXTURES
            task.destination_name = os.path.splitext(name)[0]
            task.automated = True
            task.replace_existing = True
            task.save = True
            tasks.append(task)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    for task in tasks:
        texture = unreal.load_asset("{}/{}".format(TEXTURES, task.destination_name))
        texture.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_UI)
        texture.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
        texture.set_editor_property("never_stream", True)
        if task.destination_name != "T_UI_MenuBackdrop":
            texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_EDITOR_ICON)
        assets.save_loaded_asset(texture, False)
    return len(tasks)


def menu_level():
    """L_MainMenu: an empty level (the menu's backdrop picture fills the screen) run by a game mode that shows the main
    menu and spawns no ball. Leaves the editor back on the level it started in."""
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages():
        raise RuntimeError("Last Seed UI: save the open level first. Nothing was changed.")
    if not assets.does_asset_exist(MENU_MODE):
        folder, name = MENU_MODE.rsplit("/", 1)
        factory = unreal.BlueprintFactory()
        factory.set_editor_property("parent_class", unreal.load_class(None, "/Game/Blueprint/BP_LSGameMode.BP_LSGameMode_C"))
        unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.Blueprint, factory)
    mode = unreal.load_asset(MENU_MODE)
    unreal.BlueprintEditorLibrary.compile_blueprint(mode)
    defaults = unreal.get_default_object(unreal.load_class(None, MENU_MODE + "." + MENU_MODE.rsplit("/", 1)[1] + "_C"))
    defaults.set_editor_property("menu_level", True)
    defaults.set_editor_property("default_pawn_class", None)
    save_defaults(mode)
    start = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name().split(".")[0]
    if not assets.does_asset_exist(MENU_MAP):
        levels.new_level(MENU_MAP)
    else:
        levels.load_level(MENU_MAP)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    world.get_world_settings().set_editor_property("default_game_mode", mode.generated_class())
    levels.save_current_level()
    levels.load_level(start)
    return MENU_MAP


def save_defaults(blueprint):
    """Recompiles after editing a Blueprint's defaults, then saves. Saved without the compile, the edit is lost the
    next time the editor compiles the Blueprint (pressing Play does)."""
    unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
    assets.save_loaded_asset(blueprint, False)


def wire():
    """Points the player controller at every screen and the menu level, the HUD at its form icons, and the main menu at
    the two levels. Edits the Blueprints' defaults, as the Details panel does, and saves them."""
    controller_bp = unreal.load_asset("/Game/Blueprint/BP_LSPlayerController")
    controller = unreal.get_default_object(controller_bp.generated_class())
    ui = lambda name: unreal.load_asset("/Game/UI/" + name).generated_class()
    controller.set_editor_properties({"hud_class": ui("WBP_HUD"), "main_menu_class": ui("WBP_MainMenu"),
                                      "pause_menu_class": ui("WBP_PauseMenu"), "results_class": ui("WBP_Results"),
                                      "story_card_class": ui("WBP_StoryCard"), "main_menu_level": unreal.load_asset(MENU_MAP)})
    save_defaults(controller_bp)
    hud_bp = unreal.load_asset("/Game/UI/WBP_HUD")
    icon = lambda name: unreal.load_asset("{}/{}".format(TEXTURES, name))
    unreal.get_default_object(hud_bp.generated_class()).set_editor_property("form_icons", {
        unreal.SeedForm.SEED: icon("T_UI_FormSeed"), unreal.SeedForm.STONE: icon("T_UI_FormStone"),
        unreal.SeedForm.DANDELION: icon("T_UI_FormDandelion")})
    save_defaults(hud_bp)
    menu_bp = unreal.load_asset("/Game/UI/WBP_MainMenu")
    menu = unreal.get_default_object(menu_bp.generated_class())
    menu.set_editor_property("level1", unreal.load_asset(LEVEL1))
    if assets.does_asset_exist(LEVEL2):
        menu.set_editor_property("level2", unreal.load_asset(LEVEL2))
    save_defaults(menu_bp)
    return "wired"


def run(stage):
    if stage == "textures":
        result = textures()
    elif stage == "menu_level":
        result = menu_level()
    elif stage == "wire":
        result = wire()
    else:
        raise RuntimeError("Last Seed UI: unknown stage " + stage)
    unreal.log("Last Seed UI: {} -> {}".format(stage, result))
    return result
