# Last Seed - the parts every world script shares.
#
# Purpose: creates the new map from a greybox level, generates terrain, scatters instanced scenery, adds boundaries,
# lighting and preview cameras. build_world_level1.py and build_world_level2.py decide what goes where, and this file
# knows how to place it.
# Rules every script here follows: new assets go under Content/LastSeed/, the Fab folders and the greybox maps are
# never changed, and everything placed is tagged LS_Generated, so a rerun replaces only its own work.

import math
import os
import random

import unreal

import ls_generate_player_meshes

TAG = "LS_Generated"
GREYBOX_TAG = "LS_Greybox"
MAP_FOLDER = "/Game/LastSeed/Maps"
MESH_FOLDER = "/Game/LastSeed/Meshes"
MATERIAL_FOLDER = "/Game/LastSeed/Materials"
SOURCE_FOLDER = os.path.join(unreal.Paths.project_content_dir(), "LastSeed", "SourceMeshes")
# Marks a component to stay in full colour under the withering post-process. See ARestorationDriver.
FULL_COLOUR_STENCIL = 1

actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
asset_library = unreal.EditorAssetLibrary
counts = {}


def smoothstep(edge0, edge1, x):
    t = min(max((x - edge0) / (edge1 - edge0), 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)


def lerp(a, b, t):
    return a + (b - a) * t


# --- The map ---

def open_world_map(source_map, world_map):
    """Copies the greybox map the first time, so the original stays as a backup. After that, only reopens the copy."""
    path = "{}/{}".format(MAP_FOLDER, world_map)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world.get_name() == world_map:
        return path
    if asset_library.does_asset_exist(path):
        if not level_subsystem.load_level(path):
            raise RuntimeError("Last Seed world: could not open " + path)
        return path
    # Save As, not duplicate_asset: a duplicated map stays in memory, and opening it then stops the editor with a fatal error.
    if not level_subsystem.load_level(source_map):
        raise RuntimeError("Last Seed world: could not open " + source_map)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not unreal.EditorLoadingAndSavingUtils.save_map(world, path):
        raise RuntimeError("Last Seed world: could not save " + path)
    # Save As leaves the source map open, and the build must never touch that. Saving the level later would overwrite the backup.
    if not level_subsystem.load_level(path):
        raise RuntimeError("Last Seed world: could not open " + path)
    return path


def clear_generated():
    removed = 0
    for actor in actor_subsystem.get_all_level_actors():
        if TAG in [str(tag) for tag in actor.tags]:
            actor_subsystem.destroy_actor(actor)
            removed += 1
    return removed


def greybox_actors():
    return [actor for actor in actor_subsystem.get_all_level_actors() if GREYBOX_TAG in [str(tag) for tag in actor.tags]]


def spawn(cls, x, y, z, label, folder, yaw=0.0, pitch=0.0):
    actor = actor_subsystem.spawn_actor_from_class(cls, unreal.Vector(x, y, z), unreal.Rotator(0, pitch, yaw))
    actor.tags = [TAG]
    actor.set_actor_label(label)
    actor.set_folder_path("World/" + folder)
    counts[folder] = counts.get(folder, 0) + 1
    return actor


def hide_component(component):
    """Hidden, but still solid. This is how a plain cube keeps its smooth collision under the art."""
    component.set_visibility(False, False)
    component.set_cast_shadow(False)


def mesh_actor(mesh_path, x, y, z, folder, scale=(1.0, 1.0, 1.0), yaw=0.0, material=None, label=None, pitch=0.0):
    actor = spawn(unreal.StaticMeshActor, x, y, z, label or mesh_path.rsplit("/", 1)[-1], folder, yaw, pitch)
    actor.set_actor_scale3d(unreal.Vector(*scale))
    component = actor.static_mesh_component
    component.set_mobility(unreal.ComponentMobility.STATIC)
    component.set_static_mesh(unreal.load_asset(mesh_path))
    component.set_collision_profile_name("NoCollision")
    if material:
        component.set_material(0, material)
    return actor


def base_height_offset(mesh, scale):
    """The origin of a Fab mesh isn't always at its base, so resting one on the ground starts from its bounds."""
    bounds = mesh.get_bounds()
    return (bounds.origin.z - bounds.box_extent.z) * scale


# --- Terrain: a grid of heights with extra rows and columns where the route needs sharp edges ---

class Terrain:
    def __init__(self, height_at, path_mask_at):
        self.height_at = height_at
        self.path_mask_at = path_mask_at

    def write_and_import(self, name, xs, ys):
        """Writes the grid as an OBJ file and imports it, unless the file hasn't changed since the last run."""
        heights = [[self.height_at(x, y) for x in xs] for y in ys]
        lines = []
        for row, y in enumerate(ys):
            for column, x in enumerate(xs):
                # The importer maps OBJ (x, y, z) to Unreal (x, -y, z). See ls_generate_player_meshes.write_obj.
                lines.append("v {:.1f} {:.1f} {:.1f}".format(x, -y, heights[row][column]))
        for row, y in enumerate(ys):
            for column, x in enumerate(xs):
                # The material reads these masks: U is the dirt path, and V is how steep the ground is, for bare rock.
                left, right = max(column - 1, 0), min(column + 1, len(xs) - 1)
                down, up = max(row - 1, 0), min(row + 1, len(ys) - 1)
                dx = (heights[row][right] - heights[row][left]) / max(xs[right] - xs[left], 1.0)
                dy = (heights[up][column] - heights[down][column]) / max(ys[up] - ys[down], 1.0)
                steep = smoothstep(0.55, 1.1, math.hypot(dx, dy))
                lines.append("vt {:.3f} {:.3f}".format(self.path_mask_at(x, y), 1.0 - steep))
                length = math.sqrt(dx * dx + dy * dy + 1.0)
                lines.append("vn {:.3f} {:.3f} {:.3f}".format(-dx / length, dy / length, 1.0 / length))
        width = len(xs)
        for row in range(len(ys) - 1):
            for column in range(width - 1):
                a = row * width + column + 1
                b = a + 1
                c = a + width
                d = c + 1
                # Unreal's front faces need this order. See ls_generate_player_meshes.write_obj.
                lines.append("f {0}/{0}/{0} {1}/{1}/{1} {2}/{2}/{2}".format(a, c, b))
                lines.append("f {0}/{0}/{0} {1}/{1}/{1} {2}/{2}/{2}".format(b, c, d))
        text = "\n".join(lines) + "\n"

        os.makedirs(SOURCE_FOLDER, exist_ok=True)
        path = os.path.join(SOURCE_FOLDER, name + ".obj")
        asset_path = "{}/{}".format(MESH_FOLDER, name)
        unchanged = os.path.exists(path) and open(path, encoding="ascii").read() == text and asset_library.does_asset_exist(asset_path)
        if not unchanged:
            with open(path, "w", encoding="ascii", newline="\n") as handle:
                handle.write(text)
            task = unreal.AssetImportTask()
            task.filename = os.path.normpath(path)
            task.destination_path = MESH_FOLDER
            task.destination_name = name
            task.automated = True
            task.replace_existing = True
            task.save = True
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        if not asset_library.does_asset_exist(asset_path):
            raise RuntimeError("Last Seed world: terrain {} did not import".format(name))
        return asset_path


def import_generated_mesh(name, mesh, solid=False, nanite=True):
    """Imports a mesh built in Python, unless its file hasn't changed. A solid mesh uses its exact triangles as collision."""
    os.makedirs(SOURCE_FOLDER, exist_ok=True)
    path = os.path.join(SOURCE_FOLDER, name + ".obj")
    new_path = path + ".new"
    ls_generate_player_meshes.write_obj(new_path, mesh)
    asset_path = "{}/{}".format(MESH_FOLDER, name)
    unchanged = os.path.exists(path) and asset_library.does_asset_exist(asset_path) and open(path, "rb").read() == open(new_path, "rb").read()
    os.replace(new_path, path)
    if not unchanged:
        task = unreal.AssetImportTask()
        task.filename = os.path.normpath(path)
        task.destination_path = MESH_FOLDER
        task.destination_name = name
        task.automated = True
        task.replace_existing = True
        task.save = True
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        if not asset_library.does_asset_exist(asset_path):
            raise RuntimeError("Last Seed world: mesh {} did not import".format(name))
        loaded = unreal.load_asset(asset_path)
        subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
        settings = loaded.get_editor_property("nanite_settings")
        settings.set_editor_property("enabled", nanite and not solid)
        subsystem.set_nanite_settings(loaded, settings, True)
        if solid:
            subsystem.remove_collisions(loaded)
            body = loaded.get_editor_property("body_setup")
            body.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        asset_library.save_loaded_asset(loaded, False)
    return asset_path


def spread_coordinates(lowest, highest, fine_from, fine_to, fine_step, growth=1.18, sharp=()):
    """Evenly spaced near the route, growing further apart toward the horizon, plus exact values at each sharp edge."""
    values = set()
    value = fine_from
    while value <= fine_to:
        values.add(round(value, 1))
        value += fine_step
    for start, direction, limit in ((fine_from, -1, lowest), (fine_to, 1, highest)):
        step = fine_step
        value = start
        while (value - limit) * direction < 0:
            step *= growth
            value += step * direction
            values.add(round(value, 1))
    values.update(round(edge, 1) for edge in sharp)
    return sorted(values)


def smooth_noise(x, y, seed=0.0):
    """Rolling hills from a few sine waves. Unlike random numbers, nearby points get similar heights. Range about -1 to 1."""
    return (math.sin(x * 0.00031 + seed) * math.cos(y * 0.00027 + seed * 1.7) * 0.5
            + math.sin(x * 0.00083 + y * 0.00061 + seed * 2.3) * 0.3
            + math.sin(x * 0.0021 - y * 0.0017 + seed * 0.7) * 0.2)


# --- Instanced scatter ---

class Scatter:
    """Collects transforms per mesh, then creates one instanced component for each mesh in a ring."""

    # Spots this returns true for are left empty. It runs after the random numbers are drawn, so everything else keeps its place.
    excluded = None

    def __init__(self, folder, cull_start, cull_end, shadows=True, material=None, stencil=False):
        self.folder = folder
        self.cull_start = cull_start
        self.cull_end = cull_end
        self.shadows = shadows
        self.material = material
        self.stencil = stencil
        self.transforms = {}
        self.meshes = {}

    def add(self, mesh_path, x, y, ground, scale, rng, sink=8.0, tilt=0.0):
        if mesh_path not in self.meshes:
            self.meshes[mesh_path] = unreal.load_asset(mesh_path)
            if not self.meshes[mesh_path]:
                raise RuntimeError("Last Seed world: missing mesh " + mesh_path)
        z = ground - base_height_offset(self.meshes[mesh_path], scale) - sink
        rotation = unreal.Rotator(rng.uniform(-tilt, tilt), rng.uniform(-tilt, tilt), rng.uniform(0, 360))
        if self.excluded and self.excluded(x, y):
            return
        transform = unreal.Transform(location=unreal.Vector(x, y, z), rotation=rotation, scale=unreal.Vector(scale, scale, scale))
        self.transforms.setdefault(mesh_path, []).append(transform)

    def build(self):
        systems = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        total = 0
        for mesh_path, transforms in self.transforms.items():
            actor = spawn(unreal.Actor, 0, 0, 0, "{}_{}".format(self.folder, mesh_path.rsplit("/", 1)[-1]), self.folder)
            handles = systems.k2_gather_subobject_data_for_instance(actor)
            params = unreal.AddNewSubobjectParams(parent_handle=handles[0], new_class=unreal.HierarchicalInstancedStaticMeshComponent, blueprint_context=None)
            systems.add_new_subobject(params)
            component = actor.get_components_by_class(unreal.HierarchicalInstancedStaticMeshComponent)[0]
            component.set_static_mesh(self.meshes[mesh_path])
            if self.material:
                component.set_material(0, self.material)
            component.set_collision_profile_name("NoCollision")
            component.set_cull_distances(self.cull_start, self.cull_end)
            component.set_cast_shadow(self.shadows)
            if self.stencil:
                component.set_render_custom_depth(True)
                component.set_custom_depth_stencil_value(FULL_COLOUR_STENCIL)
            component.add_instances(transforms, False, True)
            total += len(transforms)
        counts[self.folder + " instances"] = counts.get(self.folder + " instances", 0) + total


def jittered_grid(x0, x1, y0, y1, spacing, rng):
    """Points roughly spacing apart. It looks random but never clumps, and the same seed always gives the same forest."""
    x = x0
    while x < x1:
        y = y0
        while y < y1:
            yield x + rng.uniform(-0.45, 0.45) * spacing, y + rng.uniform(-0.45, 0.45) * spacing
            y += spacing
        x += spacing


# --- Boundaries ---

def invisible_wall(x0, y0, x1, y1, bottom, top, folder="Boundaries"):
    """A hidden solid box between two points. The camera ignores it, so the view doesn't jump when the ball rolls beside one."""
    thickness = 100.0
    length = max(math.hypot(x1 - x0, y1 - y0), thickness)
    yaw = math.degrees(math.atan2(y1 - y0, x1 - x0))
    actor = spawn(unreal.StaticMeshActor, (x0 + x1) / 2.0, (y0 + y1) / 2.0, (bottom + top) / 2.0, "InvisibleWall", folder, yaw)
    actor.set_actor_scale3d(unreal.Vector(length / 100.0, thickness / 100.0, (top - bottom) / 100.0))
    component = actor.static_mesh_component
    component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Cube"))
    component.set_collision_profile_name("BlockAll")
    component.set_collision_response_to_channel(unreal.CollisionChannel.ECC_CAMERA, unreal.CollisionResponseType.ECR_IGNORE)
    if folder == 'Walls':
        actor.tags = list(actor.tags) + ['LS_SoftTrailEdge']
    hide_component(component)
    return actor


def kill_volume(x, y, z, half_x, half_y, half_z=200.0, yaw=0.0):
    actor = spawn(unreal.load_class(None, "/Script/Assignment1.KillVolume"), x, y, z, "KillVolume", "Boundaries", yaw)
    # ALSVolumeBase's box is 200 half-size in every direction, so volumes are resized by scaling.
    actor.set_actor_scale3d(unreal.Vector(half_x / 200.0, half_y / 200.0, half_z / 200.0))
    return actor


# --- Effects and light ---

def niagara(path, x, y, z, folder, scale=1.0):
    system = unreal.load_asset(path)
    if not system:
        return None
    actor = spawn(unreal.NiagaraActor, x, y, z, path.rsplit("/", 1)[-1], folder)
    actor.niagara_component.set_asset(system)
    actor.set_actor_scale3d(unreal.Vector(scale, scale, scale))
    return actor


def point_light(x, y, z, colour, brightness, radius, folder="Guide Lights"):
    actor = spawn(unreal.PointLight, x, y, z, "GuideLight", folder)
    component = actor.point_light_component
    component.set_intensity_units(unreal.LightUnits.CANDELAS)
    component.set_intensity(brightness)
    component.set_light_color(colour)
    component.set_attenuation_radius(radius)
    component.set_cast_shadows(False)
    return actor


def zone_grade(x, y, z, half_x, half_y, half_z, yaw, exposure, tint, label):
    """A box that changes the picture only while the camera is inside it, fading at its edges. It adds to the level's main grade."""
    systems = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    actor = spawn(unreal.Actor, x, y, z, label, "Zone Grades", yaw)
    root = systems.k2_gather_subobject_data_for_instance(actor)[0]
    box_handle, _ = systems.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=root, new_class=unreal.BoxComponent, blueprint_context=None))
    systems.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=box_handle, new_class=unreal.PostProcessComponent, blueprint_context=None))
    box = actor.get_component_by_class(unreal.BoxComponent)
    box.set_box_extent(unreal.Vector(half_x, half_y, half_z), False)
    # The grade measures the camera against the box's collision shape, so it needs one, but this one never reports overlaps.
    box.set_collision_profile_name("OverlapAll")
    box.set_editor_property("generate_overlap_events", False)
    grade = actor.get_component_by_class(unreal.PostProcessComponent)
    grade.set_editor_property("unbound", False)
    grade.set_editor_property("blend_radius", 500.0)
    grade.set_editor_property("priority", 1.0)
    settings = grade.get_editor_property("settings")
    settings.set_editor_property("override_auto_exposure_bias", True)
    settings.set_editor_property("auto_exposure_bias", exposure)
    settings.set_editor_property("override_scene_color_tint", True)
    settings.set_editor_property("scene_color_tint", tint)
    grade.set_editor_property("settings", settings)
    return actor


def find_actor(cls):
    for actor in actor_subsystem.get_all_level_actors():
        if isinstance(actor, cls):
            return actor
    return None


def set_up_sky(sun_pitch, sun_yaw, sun_colour, sun_lux, cloud_material, driver_fog, fog_colour, fog_start=1200.0, sky_light=1.0, exposure=-1.0):
    """Changes the sky actors the greybox map already has, and adds any that are missing. Their settings stay in the new map."""
    volume = find_actor(unreal.PostProcessVolume)
    if volume:
        settings = volume.get_editor_property("settings")
        # Below 0 darkens the image. Auto exposure alone brightens a sunset into plain daylight.
        settings.set_editor_property("override_auto_exposure_bias", True)
        settings.set_editor_property("auto_exposure_bias", exposure)
        volume.set_editor_property("settings", settings)

    sun = find_actor(unreal.DirectionalLight) or spawn(unreal.DirectionalLight, 0, 0, 1000, "Sun", "Sky")
    sun.set_actor_rotation(unreal.Rotator(0, sun_pitch, sun_yaw), False)
    light = sun.get_component_by_class(unreal.DirectionalLightComponent)
    light.set_mobility(unreal.ComponentMobility.MOVABLE)
    light.set_light_color(sun_colour)
    light.set_intensity(sun_lux)
    light.set_editor_property("atmosphere_sun_light", True)

    if not find_actor(unreal.SkyAtmosphere):
        spawn(unreal.SkyAtmosphere, 0, 0, -6000, "SkyAtmosphere", "Sky")
    sky = find_actor(unreal.SkyLight) or spawn(unreal.SkyLight, 0, 0, 500, "SkyLight", "Sky")
    sky_component = sky.get_component_by_class(unreal.SkyLightComponent)
    sky_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sky_component.set_editor_property("real_time_capture", True)
    sky_component.set_intensity(sky_light)

    clouds = find_actor(unreal.VolumetricCloud) or spawn(unreal.VolumetricCloud, 0, 0, 700, "Clouds", "Sky")
    material = unreal.load_asset(cloud_material)
    if material:
        clouds.get_component_by_class(unreal.VolumetricCloudComponent).set_material(material)

    # The greybox map may hold two fogs. Two would add up and hide the distance, so only the driver's stays.
    driver = find_actor(unreal.RestorationDriver)
    fog = driver.get_editor_property("height_fog") if driver else None
    for actor in actor_subsystem.get_all_level_actors():
        if isinstance(actor, unreal.ExponentialHeightFog) and actor != fog:
            actor_subsystem.destroy_actor(actor)
    if fog:
        component = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
        component.set_fog_inscattering_color(fog_colour)
        component.set_start_distance(fog_start)
        component.set_fog_height_falloff(0.2)
        component.set_fog_density(driver_fog[0])
        # The driver sets the density in play, so these are what the fog actually uses.
        driver.set_editor_property("withered_fog_density", driver_fog[0])
        driver.set_editor_property("restored_fog_density", driver_fog[1])


# --- Preview cameras and screenshots ---

def preview_camera(name, location, look_at):
    actor = spawn(unreal.CameraActor, location[0], location[1], location[2], name, "Preview Cameras")
    rotation = unreal.MathLibrary.find_look_at_rotation(unreal.Vector(*location), unreal.Vector(*look_at))
    actor.set_actor_rotation(rotation, False)
    return actor


def take_preview_screenshots(cameras, width=1920, height=1080):
    """Moves the level viewport to each camera in turn and takes a shot. A shot takes several frames, so an editor tick drives it."""
    queue = list(cameras)
    # The first shot waits longest, as new shaders and meshes are still settling after the build.
    state = {"wait": 300, "pending": None}
    folder = os.path.join(unreal.Paths.project_saved_dir(), "Screenshots", "LS_Previews").replace("\\", "/")
    os.makedirs(folder, exist_ok=True)
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    # Game view hides the editor's icons and wireframes, and realtime keeps the lighting and particles running.
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_set_game_view(True)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_invalidate_viewports()

    def tick(_delta):
        if state["wait"] > 0:
            state["wait"] -= 1
            return
        if state["pending"]:
            command = 'HighResShot {}x{} filename="{}/{}.png"'.format(width, height, folder, state["pending"])
            unreal.SystemLibrary.execute_console_command(editor.get_editor_world(), command)
            state["pending"] = None
            state["wait"] = 40
            return
        if not queue:
            unreal.unregister_slate_post_tick_callback(state["handle"])
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_set_game_view(False)
            unreal.log("Last Seed world: preview screenshots saved in " + folder)
            return
        camera = queue.pop(0)
        editor.set_level_viewport_camera_info(camera.get_actor_location(), camera.get_actor_rotation())
        state["pending"] = camera.get_actor_label()
        # Lumen and streaming need a moment to catch up after a camera jump.
        state["wait"] = 90

    state["handle"] = unreal.register_slate_post_tick_callback(tick)


def report(world_path):
    level_subsystem.save_current_level()
    for name in sorted(counts):
        unreal.log("Last Seed world: {} = {}".format(name, counts[name]))
    unreal.log("Last Seed world: saved " + world_path)
