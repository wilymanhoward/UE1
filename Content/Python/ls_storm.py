"""The witch's storm over Wildwood: a dark, rough grade, black clouds, lightning everywhere and rain.

Every value is a setting on ARestorationDriver and fades back to the level's own look as notes restore the forest.
configure(driver) is called by build_level1_wildwood.set_opening_weather; build() applies it to the open Wildwood map.
"""
import unreal

RAIN = "/Game/Wildwood/VFX/Niagara/NS_Rain"


def configure(driver):
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    sun = next(a for a in actors if isinstance(a, unreal.DirectionalLight))
    sky = next(a for a in actors if isinstance(a, unreal.SkyLight))
    rain = unreal.load_asset(RAIN)
    assert rain
    # The healed forest should feel bright. The sky light fills the shade under the canopy, which the demo map's 2.0
    # left near black, and the volume's exposure lifts the whole picture. The storm dims both (storm_sky_scale,
    # storm_exposure_bias) and fades back to them as notes are collected. Absolute, so a rerun doesn't keep raising them.
    sky.light_component.set_intensity(6.0)
    volume = next(a for a in actors if isinstance(a, unreal.PostProcessVolume))
    settings = volume.get_editor_property("settings")
    settings.set_editor_properties({"override_auto_exposure_bias": True, "auto_exposure_bias": 2.8})
    volume.set_editor_property("settings", settings)
    driver.set_editor_properties({
        # No wind leaves: they swirl round the camera all the time and read as clutter.
        "storm_grade": True, "sun": sun, "sky_light": sky, "rain_effect": rain, "storm_wind_effect": None,
        # Harsh and cold rather than flat grey.
        "withered_contrast": 1.15, "withered_tint": unreal.LinearColor(0.8, 0.87, 1.0, 1.0),
        "storm_exposure_bias": 1.6, "storm_vignette": 0.7, "storm_grain": 0.1, "storm_fringe": 1.0,
        "storm_sun_scale": 0.4, "storm_sky_scale": 0.3, "storm_fog_color": unreal.LinearColor(0.02, 0.024, 0.032, 1.0),
        "storm_cloud_albedo": unreal.LinearColor(0.04, 0.045, 0.055, 1.0), "storm_cloud_coverage": 0.5,
        # Thunder everywhere: often, sometimes several bolts, now and then one close by.
        "lightning_interval_min": 2.0, "lightning_interval_max": 4.5, "max_bolts_per_strike": 3,
        # The flash lights the land through the sky light only: a jump in sun brightness makes the volumetric clouds
        # re-render as blocky noise for a moment.
        "close_strike_chance": 0.3, "flash_sun_intensity": 0.0, "flash_sky_intensity": 5.0,
    })


def build():
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    driver = next(a for a in actors if isinstance(a, unreal.RestorationDriver))
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    configure(driver)
    assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    print("Saved the witch's storm on", driver.get_actor_label())
