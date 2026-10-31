# Last Seed - builds a rough playable layout of every zone, then dresses it with the Fab assets.
#
# Purpose: run this in an empty L_Level1 or L_Level2 to get floors, puzzles, pickups and flow actors in the
# right order, with distances worked out from the ball's real speed and jump height. Everything it spawns is
# tagged, so running it again replaces only its own actors. Nothing is permanent until you save the level.
# Requires: Python Editor Script Plugin. Run with Tools > Execute Python Script.
#
# Numbers used for spacing (from SeedBall.cpp, with gravity at 980):
#   Seed:      628 cm/s, jumps 250 cm high and up to about 890 cm far, so gaps here are at most 500.
#   Stone:     366 cm/s, jumps 69 cm high and about 240 cm far, so Stone paths have no jumps above 40.
#   Dandelion: 523 cm/s, jumps 359 cm high, and glides at 150 cm/s falling, so a 300 cm drop glides about 1000 cm.

import math
import random

import unreal

TAG = "LS_Greybox"
WIDTH = 1200
THICKNESS = 100
CURB = 80
BLOCKER_WIDTH = WIDTH + 200  # Walls and gates overlap the curbs by this much, so they can't be walked around.

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assets = unreal.EditorAssetLibrary
random_source = random.Random(7)  # A fixed seed, so a rebuild scatters the dressing in the same places.
warnings = []
current_zone = "Setup"

FOREST_TREES = ["/Game/Polytope_Studio/Nature_Free/Meshes/Trees/SM_Pine_Tree_03_dead",
                "/Game/Polytope_Studio/Nature_Free/Meshes/Trees/SM_Fruit_Tree_01_dead",
                "/Game/Polytope_Studio/Nature_Free/Meshes/Trees/SM_Pine_Tree_03_dead_cut"]
FOREST_ROCKS = ["/Game/Stylized_PBR_Nature/Rocks/Assets/SM_R_Rock_01",
                "/Game/Stylized_PBR_Nature/Rocks/Assets/SM_S_Rock_01",
                "/Game/Polytope_Studio/Nature_Free/Meshes/Rocks/SM_Generic_Rock_01",
                "/Game/Polytope_Studio/Nature_Free/Meshes/Shrubs/SM_Generic_Shrub_01_dead"]
FOREST_REGROWTH = ["/Game/Polytope_Studio/Nature_Free/Meshes/Flowers/SM_Poppy_02",
                   "/Game/Polytope_Studio/Nature_Free/Meshes/Shrubs/SM_Generic_Shrub_01_green",
                   "/Game/StyleHex_Studio/Free_Packs/FREE_Stylized_Forest_Sample/Meshes/Foliage/SM_Fol_Flower_Clump_1",
                   "/Game/StyleHex_Studio/Free_Packs/FREE_Stylized_Forest_Sample/Meshes/Foliage/SM_Fol_Bush_1",
                   "/Game/StyleHex_Studio/Free_Packs/FREE_Stylized_Forest_Sample/Meshes/Trees/SM_Tree_Broadleaf_1"]
PEAK_TREES = ["/Game/Stylized_PBR_Nature/Foliage/Assets/SM_Pine_Tree_1",
              "/Game/Polytope_Studio/Nature_Free/Meshes/Trees/SM_Pine_Tree_03_dead"]
PEAK_ROCKS = ["/Game/RocksPackDEMO/Environment/Rocks/SM_RockPack_Rock_02",
              "/Game/RocksPackDEMO/Environment/Rocks/SM_RockPack_Rock_04",
              "/Game/RocksPackDEMO/Environment/Rocks/SM_RockPack_RockGroups_01_A",
              "/Game/Polytope_Studio/Nature_Free/Meshes/Rocks/SM_Menhir_Rock_02"]
PEAK_REGROWTH = ["/Game/Polytope_Studio/Nature_Free/Meshes/Trees/SM_Pine_Tree_03_green",
                 "/Game/Polytope_Studio/Nature_Free/Meshes/Shrubs/SM_Generic_Shrub_01_green"]


# --- Helpers -------------------------------------------------------------------------------------------------

def warn(message):
    if message not in warnings:
        warnings.append(message)


def load_asset(path):
    return unreal.load_asset(path) if assets.does_asset_exist(path) else None


def gameplay_class(blueprint, cpp):
    """Prefers the user's Blueprint child, which has their art, and falls back to the C++ class."""
    for folder in ("/Game/Blueprint", "/Game/Blueprints"):
        path = "{}/{}".format(folder, blueprint)
        if assets.does_asset_exist(path):
            return unreal.load_class(None, "{}.{}_C".format(path, blueprint))
    return unreal.load_class(None, "/Script/Assignment1.{}".format(cpp))


def spawn(cls, x, y, z, label=None, yaw=0.0, **properties):
    actor = actors.spawn_actor_from_class(cls, unreal.Vector(x, y, z), unreal.Rotator(0, 0, yaw))
    actor.tags = [TAG]
    actor.set_folder_path("Greybox/" + current_zone)
    if label:
        actor.set_actor_label(label)
    for name, value in properties.items():
        actor.set_editor_property(name, value)
    return actor


def box(cx, cy, top, size_x, size_y, thickness=THICKNESS, material=None, label="Block", pitch=0.0, yaw=0.0):
    """A solid cube whose top surface is at height top."""
    actor = spawn(unreal.StaticMeshActor, cx, cy, top - thickness / 2, label)
    actor.set_actor_rotation(unreal.Rotator(0, pitch, yaw), False)
    actor.set_actor_scale3d(unreal.Vector(size_x / 100.0, size_y / 100.0, thickness / 100.0))
    mesh = actor.static_mesh_component
    mesh.set_static_mesh(CUBE)
    mesh.set_material(0, material or GROUND)
    return actor


def floor(x0, x1, z, width=WIDTH, y=0, material=None, curbs=True, physical=None):
    """A strip of floor running along X, with low curbs so a slip doesn't always mean a fall."""
    piece = box((x0 + x1) / 2.0, y, z, x1 - x0, width, material=material, label="Floor")
    if physical:
        piece.static_mesh_component.set_phys_material_override(physical)
    if curbs:
        for side in (-1, 1):
            box((x0 + x1) / 2.0, y + side * (width / 2.0 + 25), z + CURB, x1 - x0, 50, thickness=CURB + THICKNESS, label="Curb")
    return piece


def ramp(x0, z0, x1, z1, y=0, width=WIDTH):
    """A slope from (x0, z0) to (x1, z1). The top surface passes exactly through both points."""
    run = float(x1 - x0)
    rise = float(z1 - z0)
    length = math.hypot(run, rise)
    pitch = math.degrees(math.atan2(rise, abs(run))) * (1 if run > 0 else -1)
    # Moved along the slope's normal, so it is the top surface, not the centre, that meets the end points.
    centre_z = (z0 + z1) / 2.0 + THICKNESS / 2.0 - (THICKNESS / 2.0) / math.cos(math.atan2(rise, abs(run)))
    return box((x0 + x1) / 2.0, y, centre_z, length, width, label="Ramp", pitch=pitch)


def scale_volume(actor, half_x, half_y, half_z, default_half=200.0):
    """Volumes are resized by scaling the actor. ALSVolumeBase's box is 200 half-size in every direction."""
    actor.set_actor_scale3d(unreal.Vector(half_x / default_half, half_y / default_half, half_z / default_half))
    return actor


def note(x, y, z):
    spawn(LIFE_NOTE, x, y, z + 80, "LifeNote")


def petal(x, y, z):
    spawn(GOLDEN_PETAL, x, y, z + 80, "GoldenPetal")


def shrine(x, y, z):
    spawn(SHRINE, x, y, z + 50, "Shrine")


def tutorial(x, z, message, half_x=300, y=0):
    scale_volume(spawn(TUTORIAL, x, y, z + 200, "Tutorial", message=unreal.Text(message), display_duration=6.0), half_x, WIDTH / 2.0, 300)


def flower(x, y, z, form, message):
    spawn(FORM_FLOWER, x, y, z + 80, "FormFlower", form_to_unlock=form, prompt_message=unreal.Text(message))


def blob(x, y, z, *route):
    spawn(WITHER_BLOB, x, y, z + 70, "WitherBlob", patrol_points=[unreal.Vector(dx, dy, 0) for dx, dy in route])


def moving(x, y, z, end_x, end_y, end_z=None, speed=200.0, width=300):
    actor = spawn(MOVING_PLATFORM, x, y, z, "MovingPlatform", speed=speed)
    path = actor.get_component_by_class(unreal.SplineComponent)
    path.set_location_at_spline_point(1, unreal.Vector(end_x, end_y, z if end_z is None else end_z), unreal.SplineCoordinateSpace.WORLD)
    return actor


def dress_mesh(path, x, y, ground, height, no_collision=True):
    """Places a Fab mesh with its base on the ground, scaled from its real size to the wanted height."""
    mesh = load_asset(path)
    if not mesh:
        warn("Skipped missing Fab mesh: " + path)
        return None
    bounds = mesh.get_bounds()
    scale = height / max(bounds.box_extent.z * 2.0, 1.0)
    # The origin of a mesh isn't always at its base, so the offset comes from its bounds.
    bottom_offset = (bounds.origin.z - bounds.box_extent.z) * scale
    actor = spawn(unreal.StaticMeshActor, x, y, ground - bottom_offset, "Dressing", yaw=random_source.uniform(0, 360))
    actor.set_actor_scale3d(unreal.Vector(scale, scale, scale))
    component = actor.static_mesh_component
    component.set_static_mesh(mesh)
    if no_collision:
        # Fab collision is often rough, which feels bad for a rolling ball, so scenery is never solid.
        component.set_collision_profile_name("NoCollision")
    return actor


def regrow(path, x, y, ground, height, threshold):
    """A RestorableActor showing a Fab mesh. It stays hidden until the world is this restored, or a note is near."""
    mesh = load_asset(path)
    if not mesh:
        warn("Skipped missing Fab mesh: " + path)
        return
    bounds = mesh.get_bounds()
    scale = height / max(bounds.box_extent.z * 2.0, 1.0)
    bottom_offset = (bounds.origin.z - bounds.box_extent.z) * scale
    actor = spawn(RESTORABLE, x, y, ground - bottom_offset, "Regrowth", restoration_threshold=threshold)
    actor.set_actor_scale3d(unreal.Vector(scale, scale, scale))
    actor.get_component_by_class(unreal.StaticMeshComponent).set_static_mesh(mesh)


def bank(x0, x1, z, width=WIDTH, trees=None, rocks=None, regrowth=None, tree_height=(900, 1500), count=10):
    """A wide ground strip on both sides of the path, scattered with Fab scenery."""
    bank_width = 2400
    for side in (-1, 1):
        box((x0 + x1) / 2.0, side * (width / 2.0 + 50 + bank_width / 2.0), z - 20, x1 - x0, bank_width, label="Bank")
    for _ in range(count):
        side = random_source.choice((-1, 1))
        x = random_source.uniform(x0, x1)
        y = side * (width / 2.0 + random_source.uniform(250, bank_width - 150))
        kind = random_source.random()
        if trees and kind < 0.45:
            dress_mesh(random_source.choice(trees), x, y, z - 20, random_source.uniform(*tree_height))
        elif rocks and kind < 0.75:
            dress_mesh(random_source.choice(rocks), x, y, z - 20, random_source.uniform(120, 400))
        elif regrowth:
            threshold = random_source.choice((0.25, 0.5, 0.75, 1.0))
            regrow(random_source.choice(regrowth), x, y, z - 20, random_source.uniform(150, 800), threshold)


# --- Parts every level needs ---------------------------------------------------------------------------------

def level_setup(start_z, opening_cards):
    global current_zone
    current_zone = "Setup"

    spawn(unreal.PlayerStart, 300, 0, start_z + 150, "PlayerStart")
    post_process = spawn(unreal.PostProcessVolume, 0, 0, 0, "PostProcess", unbound=True)
    fog = spawn(unreal.ExponentialHeightFog, 0, 0, 0, "Fog")

    collection = load_asset("/Game/MPC_Restoration") or load_asset("/Game/Materials/MPC_Restoration")
    if not collection:
        warn("MPC_Restoration not found. Assign Parameter Collection on the RestorationDriver.")
    spawn(unreal.load_class(None, "/Script/Assignment1.RestorationDriver"), 0, 0, 500, "RestorationDriver",
          parameter_collection=collection, post_process_volume=post_process, height_fog=fog)

    spawn(unreal.load_class(None, "/Script/Assignment1.MusicManager"), 0, 0, 600, "MusicManager")

    spawn(STORY_TRIGGER, 0, 0, 700, "OpeningStory", cards=[unreal.Text(card) for card in opening_cards], play_on_start=True)


def goal(x, y, z, cards, credits_cards):
    actor = spawn(LEVEL_GOAL, x, y, z + 200, "LevelGoal", ending_cards=[unreal.Text(card) for card in cards],
                  credits_cards=[unreal.Text(card) for card in credits_cards], par_time_seconds=300.0, required_petals=2)
    scale_volume(actor, 300, WIDTH / 2.0, 300)
    box(x, y, z + 900, 150, WIDTH, thickness=900, label="GoalMarker").static_mesh_component.set_collision_profile_name("NoCollision")


# --- Level 1: Withered Forest (6 + 7 + 7 = 20 notes, 3 petals) ------------------------------------------------

def zone_1_1():
    global current_zone
    current_zone = "1-1 Awakening Grove"
    z = 0
    floor(0, 3500, z)
    bank(0, 3500, z, trees=FOREST_TREES, rocks=FOREST_ROCKS, regrowth=FOREST_REGROWTH, count=14)
    tutorial(700, z, "WASD to roll, and the mouse to look.")
    note(1500, 0, z)
    note(2500, -400, z)

    # The first jump: a gap the player can't roll across, with nothing below but a respawn.
    tutorial(3200, z, "Press Space to jump the gap.")
    floor(3900, 6500, z)
    bank(3900, 6500, z, trees=FOREST_TREES, rocks=FOREST_ROCKS, regrowth=FOREST_REGROWTH, count=12)
    note(3700, 0, z + 250)  # Over the gap, to teach that a note can sit along a jump.
    note(5000, 400, z)

    # A hop up, then a ramp, which is the first time height matters.
    box(5900, 0, z + 150, 500, WIDTH, thickness=250, label="Ledge")
    note(5900, 0, z + 150)
    ramp(6500, z, 8000, z + 300)
    floor(8000, 9800, z + 300)
    note(8900, 0, z + 300)

    # Hidden: over the curb and behind the scenery on the far bank.
    box(5200, 2200, z + 100, 400, 400, label="SecretLedge")
    petal(5200, 2200, z + 100)

    shrine(9500, 0, z + 300)
    return 9800, z + 300


def zone_1_2(x, z):
    global current_zone
    current_zone = "1-2 Rootwood Hollow"
    floor(x, x + 2500, z)
    # The bank stops before the wall, or the player could walk around it.
    bank(x, x + 1900, z, trees=FOREST_TREES, rocks=FOREST_ROCKS, regrowth=FOREST_REGROWTH, count=8)
    flower(x + 1000, 0, z, unreal.SeedForm.STONE, "Stone Shell unlocked! Press 2 to transform. Stone is heavy and can smash walls.")
    note(x + 1700, -400, z)

    # Hidden: on the bank, behind the scenery.
    box(x + 1200, 2200, z + 150, 400, 400, label="SecretLedge")
    petal(x + 1200, 2200, z + 150)

    # A wall only Stone can break. It is wider than the path so the curbs can't be used to get around it.
    wall_x = x + 2300
    wall = spawn(CRACKED_WALL, wall_x, 0, z + 300, "CrackedWall")
    wall.set_actor_scale3d(unreal.Vector(0.5, BLOCKER_WIDTH / 100.0, 6.0))
    tutorial(x + 2000, z, "Roll into the cracked wall as Stone Shell. Press 2 first.")

    next_x = x + 2500
    floor(next_x, next_x + 3000, z)
    note(next_x + 300, 400, z)

    # Heavy forms only: the plate needs 50 kg, and Seed is 20 kg.
    plate_a = spawn(PRESSURE_PLATE, next_x + 1000, -300, z - 10, "PressurePlate")
    tutorial(next_x + 800, z, "Stone Shell is heavy enough to hold a pressure plate. Push the block onto it.")
    spawn(PUSHABLE_BLOCK, next_x + 1000, 300, z + 60, "PushableBlock", mass_kg=52.0)

    gate_x = next_x + 2500
    gate = spawn(GATE, gate_x, 0, z + 300, "Gate")
    # Taller and wider than the door's default, so a jump from the curb can't clear it.
    gate.set_actor_scale3d(unreal.Vector(1.0, BLOCKER_WIDTH / 300.0, 2.0))
    gate.set_editor_property("required_plates", [plate_a])
    note(next_x + 1800, 0, z)

    # Thorns kill light forms and knock Stone back, so a full-width patch would block everyone.
    # Each patch covers one side, which leaves a winding lane 400 wide.
    next_x += 3000
    floor(next_x, next_x + 2500, z)
    for offset, y in ((700, -200), (1500, 200)):
        thorns = spawn(HAZARD, next_x + offset, y, z + 50, "Thorns")
        thorns.set_actor_scale3d(unreal.Vector(1.0, 2.0, 1.0))
    note(next_x + 700, 400, z)
    note(next_x + 1500, -400, z)
    tutorial(next_x + 200, z, "Thorns destroy light forms, and even knock Stone Shell back. Stay on the clear lane.")

    note(next_x + 2100, -400, z)
    note(next_x + 2100, 400, z)
    shrine(next_x + 2300, 0, z)
    return next_x + 2500, z


def zone_1_3(x, z):
    global current_zone
    current_zone = "1-3 Thornmire Marsh"
    floor(x, x + 1800, z)
    bank(x, x + 1800, z, trees=FOREST_TREES, rocks=FOREST_ROCKS, regrowth=FOREST_REGROWTH, count=8)
    flower(x + 800, 0, z, unreal.SeedForm.DANDELION, "Dandelion unlocked! Press 3, then hold Space while falling to glide.")

    # The marsh: a basin with water over it, and lily pads across. A ramp lets a sunken ball climb out.
    marsh_x = x + 1800
    basin_length = 3000
    box(marsh_x + basin_length / 2.0, 0, z - 350, basin_length, WIDTH, label="MarshBed")
    water = spawn(WATER, marsh_x + basin_length / 2.0, 0, z - 175, "Water")
    scale_volume(water, basin_length / 2.0, WIDTH / 2.0, 175)
    box(marsh_x + basin_length / 2.0, 0, z - 2, basin_length, WIDTH, thickness=2, material=WATER_LOOK, label="WaterSurface") \
        .static_mesh_component.set_collision_profile_name("NoCollision")
    for side in (-1, 1):
        box(marsh_x + basin_length / 2.0, side * (WIDTH / 2.0 + 25), z + CURB, basin_length, 50, thickness=450, label="MarshWall")
    for index, offset in enumerate((400, 900, 1400, 1900, 2400)):
        y = -250 if index % 2 == 0 else 250
        spawn(SINKING_PAD, marsh_x + offset, y, z, "SinkingPad")
    note(marsh_x + 900, 250, z + 50)
    note(marsh_x + 1900, 250, z + 50)
    ramp(marsh_x + basin_length - 900, z - 350, marsh_x + basin_length, z, width=500)
    tutorial(marsh_x - 400, z, "Water holds up light forms. Lily pads sink, so keep moving.")

    # Blobs: wide open ground to dodge them on, and a Stone slam kills them.
    field_x = marsh_x + basin_length
    floor(field_x, field_x + 3500, z)
    bank(field_x, field_x + 3500, z, trees=FOREST_TREES, rocks=FOREST_ROCKS, regrowth=FOREST_REGROWTH, count=10)
    blob(field_x + 1000, -300, z, (0, 0), (0, 600))
    blob(field_x + 2200, 300, z, (0, 0), (0, -600))
    note(field_x + 1000, 0, z)
    note(field_x + 2200, 0, z)
    tutorial(field_x + 300, z, "Wither Blobs drain the colour from the world. Slam on them from above as Stone Shell.")

    # The glide: a climb, then a gap only Dandelion can cross. From 500 cm up it glides about 1740 cm,
    # while Seed's best jump from the same ledge reaches about 1225 cm.
    climb_x = field_x + 3500
    ramp(climb_x, z, climb_x + 2000, z + 500)
    floor(climb_x + 2000, climb_x + 2700, z + 500)
    note(climb_x + 2400, 0, z + 500)
    tutorial(climb_x + 2200, z + 500, "Hold Space as Dandelion to glide across.")
    far_x = climb_x + 2700 + 1400
    note(climb_x + 3400, 0, z + 300)
    floor(far_x, far_x + 2000, z)
    bank(far_x, far_x + 2000, z, trees=FOREST_TREES, rocks=FOREST_ROCKS, regrowth=FOREST_REGROWTH, count=8)
    note(far_x + 600, 400, z)

    # Hidden: reachable only by gliding sideways from the high ledge.
    box(climb_x + 3000, 2000, z + 100, 400, 400, label="SecretLedge")
    petal(climb_x + 3000, 2000, z + 100)

    goal(far_x + 1500, 0, z, ["The forest blooms again.", "A spirit light drifts toward the frozen mountain."], [])
    return far_x + 2000


def build_level_1():
    level_setup(0, ["The Heart Tree is dead. The Withering has taken all colour and sound from the world.",
                    "Its last seed falls, still glowing."])
    end_x, end_z = zone_1_1()
    end_x, end_z = zone_1_2(end_x, end_z)
    length = zone_1_3(end_x, end_z)
    warn("Set Next Level on the LevelGoal to L_Level2 by hand, once that level exists.")
    add_kill_floor(length, -1500)


def add_kill_floor(length, z):
    global current_zone
    current_zone = "Setup"
    scale_volume(spawn(KILL_VOLUME, length / 2.0, 0, z, "KillVolume"), length / 2.0 + 3000, 25000, 200)


# --- Level 2: Frozen Peaks (8 + 8 + 8 = 24 notes, 3 petals) ---------------------------------------------------

def zone_2_1():
    global current_zone
    current_zone = "2-1 Frostgate Ruins"
    z = 0
    ice = load_asset("/Game/Physics/PM_Ice") or load_asset("/Game/PM_Ice")
    if not ice:
        warn("PM_Ice not found, so ice floors aren't slippery. Create it (ASSET_SETUP.md, Phase 3) and rebuild.")

    floor(0, 2000, z)
    bank(0, 2000, z, trees=PEAK_TREES, rocks=PEAK_ROCKS, regrowth=PEAK_REGROWTH, count=8)
    note(1200, 0, z)
    tutorial(1700, z, "The ice ahead is slippery. Only Stone Shell keeps its grip.")

    # The two-plate puzzle on ice. Blocks use their 150 kg default here, as only Stone can shift them on ice.
    floor(2000, 6500, z, physical=ice)
    plate_a = spawn(PRESSURE_PLATE, 4000, -350, z - 10, "PlateA")
    plate_b = spawn(PRESSURE_PLATE, 4000, 350, z - 10, "PlateB")
    spawn(PUSHABLE_BLOCK, 3200, -350, z + 60, "BlockA")
    spawn(PUSHABLE_BLOCK, 3200, 350, z + 60, "BlockB")
    gate = spawn(GATE, 5000, 0, z + 300, "Gate")
    gate.set_actor_scale3d(unreal.Vector(1.0, BLOCKER_WIDTH / 300.0, 2.0))
    gate.set_editor_property("required_plates", [plate_a, plate_b])
    note(2600, -400, z)
    note(2600, 400, z)
    note(4500, 0, z)
    note(5700, 0, z)
    tutorial(2300, z, "Push a block onto each plate as Stone Shell to open the gate.")

    # Thin ice: it holds Seed and Dandelion, but breaks under Stone.
    gap_x = 6500
    length = 2000
    box(gap_x + length / 2.0, 0, z - 700, length, WIDTH, label="BelowThinIce")
    scale_volume(spawn(KILL_VOLUME, gap_x + length / 2.0, 0, z - 550, "ColdWater"), length / 2.0, WIDTH / 2.0, 100)
    for ix in range(10):
        for iy in range(6):
            # Each tile is 200 cm wide. Its origin sits 50 above its surface, so the surface matches the floor.
            spawn(THIN_ICE, gap_x + 100 + ix * 200, -500 + iy * 200, z + 50, "ThinIce")
    note(gap_x + 1000, 0, z)
    note(gap_x + 1500, -300, z)
    tutorial(gap_x - 400, z, "Thin ice won't hold Stone Shell. Change form before crossing.")

    far = gap_x + length
    floor(far, far + 2000, z)
    bank(far, far + 2000, z, trees=PEAK_TREES, rocks=PEAK_ROCKS, regrowth=PEAK_REGROWTH, count=8)
    note(far + 900, 0, z)

    # Hidden: behind the rocks on the far bank.
    box(far + 1400, 2300, z + 150, 400, 400, label="SecretLedge")
    petal(far + 1400, 2300, z + 150)

    shrine(far + 1800, 0, z)
    return far + 2000, z


def zone_2_2(x, z):
    global current_zone
    current_zone = "2-2 Windcrag Bridges"

    # A narrow bridge in a side wind. Stone crosses it easily, and light forms are blown off.
    bridge = x + 3000
    floor(x, bridge, z, width=500, curbs=False)
    wind = spawn(WIND, x + 1500, 0, z + 300, "SideWind", wind_direction=unreal.Vector(0, 1, 0), strength=1200.0, pulsing=True)
    scale_volume(wind, 1200, 700, 400)
    note(x + 800, 0, z)
    note(x + 2200, 0, z)
    tutorial(x + 200, z, "Strong wind barely moves Stone Shell.")

    # Moving platforms: Seed's jump clears the small gaps at each end of the route.
    gap_start = bridge + 300
    floor(bridge, bridge + 300, z, width=800, curbs=False)
    moving(gap_start + 200, 0, z - 15, gap_start + 1500, 0)
    note(gap_start + 850, 0, z + 150)
    side_x = gap_start + 1900
    floor(side_x, side_x + 800, z, width=800, curbs=False)

    # The second platform runs sideways across a gap, between two floors offset in Y.
    y2 = 900
    moving(side_x + 1050, -100, z - 15, side_x + 1050, 700, speed=160.0)
    note(side_x + 1050, 300, z + 150)
    floor(side_x + 1300, side_x + 1800, z, width=800, y=y2, curbs=False)

    # Crumbling platforms: a run where stopping means falling.
    crumble_x = side_x + 1800
    for index in range(5):
        y = y2 - 200 if index % 2 == 0 else y2 + 200
        spawn(CRUMBLING, crumble_x + 300 + index * 500, y, z - 15, "CrumblingPlatform")
    note(crumble_x + 1300, y2 - 200, z + 150)
    tutorial(crumble_x - 300, z, "These platforms fall soon after you land. Keep moving.", y=y2)

    # Pulsing updraft to a high ledge. Its 1500 lifts Seed and Dandelion, but not Stone.
    lift_x = crumble_x + 2700
    floor(lift_x, lift_x + 1200, z, width=800, y=y2, curbs=False)
    updraft = spawn(WIND, lift_x + 700, y2, z + 600, "Updraft", wind_direction=unreal.Vector(0, 0, 1), strength=1500.0, pulsing=True)
    scale_volume(updraft, 200, 200, 600)
    tutorial(lift_x + 100, z, "Ride the updraft as a light form. It blows in pulses.", y=y2)
    high = z + 800
    floor(lift_x + 1200, lift_x + 3200, high, width=800, y=y2)
    note(lift_x + 1800, y2, high)
    note(lift_x + 2400, y2, high)
    note(lift_x + 2900, y2, high)

    # Hidden: a jump off the top of the updraft to the side.
    box(lift_x + 700, y2 + 1500, z + 900, 400, 400, label="SecretLedge")
    petal(lift_x + 700, y2 + 1500, z + 900)

    shrine(lift_x + 3000, y2, high)

    # Wide enough to join the high ledge to the next zone, which runs along Y = 0.
    floor(lift_x + 3200, lift_x + 3800, high, width=2000, y=y2 / 2.0, curbs=False)
    return lift_x + 3800, high


def zone_2_3(x, z):
    global current_zone
    current_zone = "2-3 Storm Ascent"
    rise = 400
    run = 3000
    flights = 8

    floor(x, x + 1200, z, width=1200)
    tutorial(x + 200, z, "The Withering storm is rising. Climb! Each Life Note pushes it back.")

    # Switchbacks: ramps alternate along X, each on its own row in Y, joined by flat landings.
    row_gap = WIDTH + 400
    left = x + 1200
    level_z = z
    notes_left = 8
    for flight in range(flights):
        y = flight * row_gap
        going_right = flight % 2 == 0
        start, end = (left, left + run) if going_right else (left + run, left)
        ramp(start, level_z, end, level_z + rise, y=y)
        if notes_left > 0:
            note((start + end) / 2.0, y, level_z + rise / 2.0 + 30)
            notes_left -= 1
        level_z += rise
        # The landing sits past the end of the ramp, and is wide enough to reach the next row.
        landing_x = end + (600 if going_right else -600)
        box(landing_x, y + row_gap / 2.0, level_z, 1200, row_gap + WIDTH, label="Landing")

    # Hidden: a ledge partway up, a jump off the outside of a landing.
    box(left + run + 2000, 3 * row_gap, z + 3 * rise + 100, 400, 400, label="SecretLedge")
    petal(left + run + 2000, 3 * row_gap, z + 3 * rise + 100)

    # The storm starts 1000 below the climb. Seed climbs about 55 cm/s and Stone about 32 cm/s, ramp and landing
    # together. At 40 cm/s Seed stays ahead, while Stone relies on the 300 cm each note pushes the storm back.
    top_y = (flights - 1) * row_gap
    center_x = left + run / 2.0
    center_y = top_y / 2.0
    storm = spawn(STORM, center_x, center_y, z - 1000 - 500, "WitheringStorm", rise_speed=40.0, max_rise_distance=(flights - 1) * rise + 1000.0)
    storm.set_actor_scale3d(unreal.Vector(1.2, 3.0, 1.0))  # The box starts 10000 wide. The climb needs more in Y.
    trigger = spawn(STORM_TRIGGER, x + 900, 0, z + 200, "StormTrigger", storm=storm)
    scale_volume(trigger, 100, WIDTH / 2.0, 300)

    # The summit, on the last landing.
    summit_end = left + run + 600 if (flights - 1) % 2 == 0 else left - 600
    floor(summit_end - 1500, summit_end + 1500, level_z, width=1200, y=top_y + row_gap)
    for offset in (-800, 0, 800):
        dress_mesh(random_source.choice(PEAK_ROCKS), summit_end + offset, top_y + row_gap + 900, level_z, 500)
    goal(summit_end, top_y + row_gap, level_z,
         ["The seed reaches the summit, and plants itself in the frozen ground.", "A new Heart Tree begins to grow."],
         ["Even the smallest seed can bring a world back to life.", "Last Seed"])
    return left + run + 3000


def build_level_2():
    level_setup(0, ["The spirit light rises above the frozen peaks.", "The seed follows it into the cold."])
    end_x, end_z = zone_2_1()
    end_x, end_z = zone_2_2(end_x, end_z)
    length = zone_2_3(end_x, end_z)
    # Lower than the storm's start, so the storm is what kills on the climb, and not this.
    add_kill_floor(length, -2500)


# --- Entry point ---------------------------------------------------------------------------------------------

def clear_previous():
    for actor in actors.get_all_level_actors():
        if TAG in [str(tag) for tag in actor.tags]:
            actors.destroy_actor(actor)
        # A Basic level starts with a floor and a Player Start at the origin, which would be in the way.
        elif actor.get_actor_label() == "Floor" or isinstance(actor, unreal.PlayerStart):
            actors.destroy_actor(actor)


level_name = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_name()

CUBE = unreal.load_asset("/Engine/BasicShapes/Cube")
GROUND = load_asset("/Game/M_TestGround") or load_asset("/Game/Materials/M_TestGround") or unreal.load_asset("/Engine/BasicShapes/BasicShapeMaterial")
WATER_LOOK = unreal.load_asset("/Engine/BasicShapes/BasicShapeMaterial")

LIFE_NOTE = gameplay_class("BP_LifeNote", "LifeNote")
GOLDEN_PETAL = gameplay_class("BP_GoldenPetal", "GoldenPetal")
SHRINE = gameplay_class("BP_CheckpointShrine", "CheckpointShrine")
FORM_FLOWER = gameplay_class("BP_FormFlower_Stone", "FormFlower")
WITHER_BLOB = gameplay_class("BP_WitherBlob", "WitherBlob")
CRACKED_WALL = gameplay_class("BP_CrackedWall", "CrackedWall")
PRESSURE_PLATE = gameplay_class("BP_PressurePlate", "PressurePlate")
PUSHABLE_BLOCK = gameplay_class("BP_IceBlock", "PushableBlock")
GATE = gameplay_class("BP_Gate", "Gate")
HAZARD = gameplay_class("BP_Thorns", "HazardVolume")
WATER = gameplay_class("BP_WaterVolume", "WaterVolume")
SINKING_PAD = gameplay_class("BP_SinkingPad", "SinkingPad")
WIND = gameplay_class("BP_WindVolume", "WindVolume")
THIN_ICE = gameplay_class("BP_ThinIce", "ThinIce")
MOVING_PLATFORM = gameplay_class("BP_MovingPlatform", "MovingPlatform")
CRUMBLING = gameplay_class("BP_CrumblingPlatform", "CrumblingPlatform")
STORM = gameplay_class("BP_WitheringStorm", "WitheringStorm")
RESTORABLE = gameplay_class("BP_Flower", "RestorableActor")
STORM_TRIGGER = unreal.load_class(None, "/Script/Assignment1.StormTrigger")
STORY_TRIGGER = unreal.load_class(None, "/Script/Assignment1.StoryTrigger")
LEVEL_GOAL = unreal.load_class(None, "/Script/Assignment1.LevelGoal")
KILL_VOLUME = unreal.load_class(None, "/Script/Assignment1.KillVolume")
TUTORIAL = unreal.load_class(None, "/Script/Assignment1.TutorialTrigger")

if "Level1" in level_name:
    clear_previous()
    build_level_1()
elif "Level2" in level_name:
    clear_previous()
    build_level_2()
else:
    unreal.log_error("Open L_Level1 or L_Level2 first. This level is called {}, so nothing was changed.".format(level_name))

for message in warnings:
    unreal.log_warning("Last Seed greybox: " + message)
unreal.log("Last Seed greybox: finished {} with {} warnings.".format(level_name, len(warnings)))
