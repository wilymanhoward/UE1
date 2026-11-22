"""Builds Emberwood, Level 2, inside a copy of the lava pack's references map (L_Level2_Emberwood).

Seed lands in the pack's lava basin (all of its ground is safe), then the route runs east out of it over open lava:

1. Ember Steps: hop basalt stones over the lava, then a run of stones that sink a moment after Seed lands.
2. Updraft Chasm: as Dandelion, ride the hot updrafts across a lava gap too wide to jump.
3. Ruined Keep: walls and columns from the pack's castle set. Stone Shell pushes a crate onto a lever that raises the inner gate.
   The goal behind it opens only with every energy. The witch confronts Seed (placeholder frames from
   SourceIntro/EmberwoodWitch), then Seed shakes, bursts and wakes up in a fully restored Wildwood (ALevelGoal::bEnergyFinale).

Energy is the level's Life Notes, shown as glowing green orbs; the HUD calls them Energy in this level.
The route is laid out along its own +X (the numbers below) and turned onto the map by to_world: it leaves the basin's
east shore, world y 7500, heading +Y. Run in the editor with nothing unsaved: import ls_emberwood; ls_emberwood.build()
To swap the witch art, replace the PNGs in SourceIntro/EmberwoodWitch and run it again.
"""
import math
import random
from pathlib import Path

import unreal

import build_level1_wildwood as builder
import ls_lantern_post
from ls_material_helpers import colour, combine, finish, fresh_material, node, number, output
from ls_witch_exile import LAVA_Z, basalt_material, basalt_shelf, lava_plane
from ls_world_common import hide_component, kill_volume, mesh_actor, niagara, point_light, spawn

MAP = "/Game/LastSeed/Maps/L_Level2_Emberwood"
SOURCE_MAP = "/Game/Lava/Maps/references"  # Copied once into MAP; the pack's own map is never changed.
ORIGIN = (0.0, 2300.0)  # World x, y of the route's (0, 0): the basin's east shore, world y 7500, is route x 5200.
SHORE = 5200.0
START = (1500.0, 0.0)  # Where Seed lands in the basin, in route coordinates.
WILDWOOD = "/Game/LastSeed/Maps/L_Level1_Wildwood"
LAVA = "/Game/Lava"
ROOT = "Emberwood"  # Everything here goes under World/Emberwood/..., which a rerun clears.
WITCH_ART = "/Game/LastSeed/Intro/EmberwoodWitch"
WITCH_SOURCE = Path(unreal.Paths.project_content_dir()) / "LastSeed/SourceIntro/EmberwoodWitch"
# Placeholder frames: (file, seconds, caption). Replace the PNGs to change the art; the captions stay.
WITCH_SHOTS = [("EmberWitch_1", 4.0, "So the little seed crawled out of my fire…"),
               ("EmberWitch_2", 4.0, "Then burn with the rest of Emberwood!"),
               ("EmberWitch_3", 4.0, "No… what is that light?!")]

# Section 1: (x, y, top, half x, half y) basalt stones, then crumbling stones (x, y, top).
STEPS = [(5650, 150, 190, 190, 170), (6250, -130, 230, 175, 165), (6850, 90, 270, 185, 170), (7450, 320, 250, 180, 175),
         (8300, 250, 260, 520, 470),  # Checkpoint 1.
         (11250, 80, 330, 200, 185),
         (12400, 100, 300, 620, 560)]  # Checkpoint 2, where Dandelion is first needed.
SINKING = [(9050, 200, 270), (9600, 10, 290), (10150, -190, 310), (10700, -60, 330)]
# Section 2: updrafts (x, y) rising from the lava, and two rest stones between them.
UPDRAFTS = [(13900, 60), (15400, -80), (16900, 40)]
REST_STONES = [(14650, -40, 230, 170, 160), (16150, 0, 240, 170, 165)]
# Section 3: the keep's floor runs x 17650..22850, y -1300..1300, with its top at KEEP_TOP.
KEEP = (17650.0, 22850.0, -1300.0, 1300.0)
KEEP_TOP = 300.0
GATE_X = 21050.0
LEVER = (20500.0, 950.0)
CRATE = (19500.0, 950.0)  # In line with the lever, so Stone pushes it straight on. The lever ignores Seed itself.
GOAL = (22250.0, 0.0)
# Energy orbs (x, y, z): about 80 cm over a stone, higher where a jump or an updraft reaches them.
ENERGY = [(2600, -900, 0), (4300, 700, 0),  # In the basin; their height comes from the ground there.
          (5650, 150, 290), (6550, -20, 520), (7450, 320, 350), (8500, 450, 360), (9600, 10, 390), (10700, -60, 430),
          (12600, -150, 400),
          (13900, 60, 950), (14650, -40, 330), (15400, -80, 950), (16900, 40, 950),
          (18900, -900, 400), (20500, -950, 400), (19700, 900, 400)]


def to_world(x, y):
    """Route x runs along world +Y and route y along world -X."""
    return ORIGIN[0] - y, ORIGIN[1] + x


TURN = 90.0  # Added to every yaw, to match to_world.


def at_spawn(cls, x, y, z, label, folder, yaw=0.0):
    return spawn(cls, *to_world(x, y), z, label, folder, yaw + TURN)


def at_mesh(mesh, x, y, z, folder, scale=(1.0, 1.0, 1.0), yaw=0.0, material=None, label=None):
    return mesh_actor(mesh, *to_world(x, y), z, folder, scale, yaw + TURN, material, label)


def at_fit(mesh, x, y, top, yaw, size_x, size_y, size_z, folder, label):
    return builder.fit_box(mesh, *to_world(x, y), top, yaw + TURN, size_x, size_y, size_z, folder, label)


def at_light(x, y, z, colour_, brightness, radius, folder):
    return point_light(*to_world(x, y), z, colour_, brightness, radius, folder)


def at_niagara(path, x, y, z, folder, scale=1.0):
    return niagara(path, *to_world(x, y), z, folder, scale)


def ground(wx, wy):
    """The top of whatever is solid at a world x, y: the basin's rocks and lava floor."""
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(wx, wy, 3000.0), unreal.Vector(wx, wy, -3000.0),
                                                 unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [], unreal.DrawDebugTrace.NONE, True)
    assert hit and hit.to_tuple()[0], (wx, wy)
    return hit.to_tuple()[4].z


def placed(entry, folder, plates=None):
    """Wildwood's builder places the puzzle pieces; this files whatever it made under folder, so a rerun clears it."""
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    before = set(a.get_name() for a in actors.get_all_level_actors())
    entry = dict(entry)
    entry["x"], entry["y"] = to_world(entry["x"], entry["y"])
    entry["yaw"] = entry.get("yaw", 0.0) + TURN
    builder.place(entry, {} if plates is None else plates)
    for actor in actors.get_all_level_actors():
        if actor.get_name() not in before:
            actor.set_folder_path("World/" + folder)


def clear():
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    old = [a for a in actors.get_all_level_actors() if str(a.get_folder_path()).startswith("World/" + ROOT + "/")]
    if old:
        assert actors.destroy_actors(old)


def energy_material():
    """A bright green-gold orb that reads at once against orange lava."""
    material = fresh_material("M_LS_EnergyOrb")
    output(material, colour(material, 0.2, 0.6, 0.25), unreal.MaterialProperty.MP_BASE_COLOR)
    output(material, combine(material, unreal.MaterialExpressionMultiply, colour(material, 0.45, 1.0, 0.4), number(material, 30.0)),
           unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    return finish(material)


def charge_shell_material():
    """The energy swelling round Seed before the burst: see-through in the middle, bright green at the rim."""
    material = fresh_material("M_LS_EnergyCharge")
    material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_ADDITIVE)
    material.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    rim = node(material, unreal.MaterialExpressionFresnel, exponent=2.5, base_reflect_fraction=0.08)
    glow = combine(material, unreal.MaterialExpressionMultiply, colour(material, 0.45, 1.0, 0.4), number(material, 12.0))
    output(material, combine(material, unreal.MaterialExpressionMultiply, glow, rim), unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    return finish(material)


def stone(x, y, top, rx, ry, folder, index, rock, island, label="Basalt stone"):
    """A basalt stone like the arrival's: the shelf mesh for looks, a hidden flat cylinder for a fair landing."""
    at_mesh(island, x, y, top, folder, (rx / 100.0, ry / 100.0, 3.0 + 0.2 * (index % 4)), index * 47.0, rock, label)
    collision = at_mesh("/Engine/BasicShapes/Cylinder", x, y, top - 44.0, folder, (rx / 50.0 * 0.96, ry / 50.0 * 0.96, 0.88), 0.0,
                           label=label + " collision")
    hide_component(collision.static_mesh_component)
    collision.static_mesh_component.set_collision_profile_name("BlockAll")


def sinking_stone(x, y, top, folder):
    """A CrumblingPlatform dressed as the pack's dark slab, thickened so it reads as a stone and not a tile."""
    actor = at_spawn(unreal.load_class(None, "/Script/Assignment1.CrumblingPlatform"), x, y, top, "Sinking stone", folder)
    slab = unreal.load_asset(LAVA + "/Mesh/floor_02")
    bounds = slab.get_bounds()
    sx, sy, sz = 300.0 / (bounds.box_extent.x * 2.0), 300.0 / (bounds.box_extent.y * 2.0), 4.0
    component = actor.get_editor_property("mesh")
    component.set_static_mesh(slab)
    component.set_editor_property("override_materials", [])
    component.set_relative_scale3d(unreal.Vector(sx, sy, sz))
    component.set_relative_location(unreal.Vector(-bounds.origin.x * sx, -bounds.origin.y * sy,
                                                  -(bounds.origin.z + bounds.box_extent.z) * sz), False, False)
    actor.set_editor_properties({"shake_duration": 0.9, "shake_amplitude": 3.0, "fall_speed": 500.0})


def checkpoint(x, y, top, yaw, side, folder):
    """A lantern post on the stone's edge, side cm off the path's line to the right."""
    actor = at_spawn(builder.gameplay_class("BP_CheckpointShrine", "CheckpointShrine"), x, y, top + 55.0, "Shrine", folder, yaw)
    builder.keep_coloured(actor)
    # configure() measures the lane from the nearest wall; a wall this far out puts the post at side.
    gap = side - ls_lantern_post.EDGE + ls_lantern_post.WALL_GAP
    here = actor.get_actor_location()
    ls_lantern_post.configure(actor, [(here.x - 1.0, here.y + gap, here.x + 1.0, here.y + gap, 0.0, 0.0)])


def orb(x, y, z, folder, mesh, material):
    if x < SHORE:
        z = ground(*to_world(x, y)) + 110.0  # In the basin the orbs float just above its uneven ground.
    actor = at_spawn(builder.gameplay_class("BP_LifeNote", "LifeNote"), x, y, z, "Energy", folder)
    component = builder.keep_coloured(actor)
    component.set_static_mesh(mesh)
    component.set_relative_scale3d(unreal.Vector(0.5, 0.5, 0.5))
    component.set_material(0, material)
    actor.set_editor_property("collect_sound", builder.fun_assets()["chime"])
    at_light(x, y, z, unreal.LinearColor(0.45, 1.0, 0.4), 30.0, 450.0, folder)


def updraft(x, y, folder):
    """Hot air from a vent in the lava: rises from the surface to well above the stones, strong enough for Dandelion."""
    half = (300.0, 300.0, 900.0)
    z = LAVA_Z + half[2]
    actor = at_spawn(builder.gameplay_class("BP_WindVolume", "WindVolume"), x, y, z, "Updraft", folder)
    actor.set_actor_scale3d(unreal.Vector(*[h / 200.0 for h in half]))
    actor.set_editor_properties({"wind_direction": unreal.Vector(0.0, 0.0, 1.0), "strength": 900.0})
    for k in range(3):
        at_niagara(LAVA + "/VFX/Niagara_sparks_only", x, y, LAVA_Z + 20.0 + k * 450.0, folder, 1.6)
    at_mesh(LAVA + "/Mesh/lava_floor_06_low", x, y, LAVA_Z - 20.0, folder, (1.4, 1.4, 1.0), x % 360, label="Lava vent")
    at_light(x, y, LAVA_Z + 250.0, unreal.LinearColor(1.0, 0.45, 0.1), 160.0, 1800.0, folder)


def keep(folder, rock):
    x0, x1, y0, y1 = KEEP
    floors = [LAVA + "/Mesh/arch_models/floor_a1_low", LAVA + "/Mesh/arch_models/floor_a2_low"]
    tile = 520.0
    nx, ny = int(round((x1 - x0) / tile)), int(round((y1 - y0) / tile))
    for i in range(nx):
        for j in range(ny):
            x, y = x0 + (i + 0.5) * (x1 - x0) / nx, y0 + (j + 0.5) * (y1 - y0) / ny
            at_fit(floors[(i + j) % 2], x, y, KEEP_TOP, 90.0 * ((i * 3 + j) % 4),
                            (x1 - x0) / nx + 6.0, (y1 - y0) / ny + 6.0, 70.0, folder, "Keep floor")
    # The tiles' rocky tops trap a rolling ball, so Seed rolls on one flat hidden slab at their top instead.
    slab = at_mesh("/Engine/BasicShapes/Cube", (x0 + x1) / 2.0, 0.0, KEEP_TOP - 50.0, folder,
                      ((x1 - x0) / 100.0, (y1 - y0) / 100.0, 1.0), label="Keep floor collision")
    hide_component(slab.static_mesh_component)
    slab.static_mesh_component.set_collision_profile_name("BlockAll")
    # The keep stands on a great basalt foot going down into the lava.
    at_mesh(basalt_shelf(), (x0 + x1) / 2.0, 0.0, KEEP_TOP - 40.0, folder, ((x1 - x0) / 190.0, (y1 - y0) / 190.0, 4.0), 0.0, rock,
               "Keep foundation")

    walls = [LAVA + "/Mesh/arch_models/wall_sw_0{}_low".format(k) for k in (1, 2, 3, 4)]
    arches = [LAVA + "/Mesh/arch_models/arch_hole_01_low", LAVA + "/Mesh/arch_models/arch_hole_02_low"]
    span = 500.0
    for side in (-1, 1):
        # The long side walls, with an arched window now and then; solid, so the ball stays in the keep.
        count = int((x1 - x0) // span)
        for k in range(count):
            x = x0 + (k + 0.5) * span
            path = arches[k % 2] if k % 4 == 2 else walls[k % 4]
            height = 430.0 if k % 3 == 1 else 500.0  # Uneven, like a ruin.
            builder.collide(at_fit(path, x, side * (y1 + 20.0), KEEP_TOP + height, 0.0, span + 4.0, 70.0, height, folder,
                                            "Keep wall"))
    for k in range(int((y1 - y0) // span)):
        y = y0 + (k + 0.5) * span
        builder.collide(at_fit(walls[(k + 1) % 4], x1 + 20.0, y, KEEP_TOP + 500.0, 90.0, span + 4.0, 70.0, 500.0, folder,
                                        "Keep wall"))
    # The entrance side: walls either side of an open arch 1200 wide where the chasm's ledge meets the keep.
    for y in (-1050.0, -650.0, 650.0, 1050.0):
        builder.collide(at_fit(walls[0], x0 - 20.0, y, KEEP_TOP + 450.0, 90.0, 404.0, 70.0, 450.0, folder, "Keep wall"))
    for x in (x0, x1):
        for y in (y0, y1):
            builder.collide(at_fit(LAVA + "/Mesh/arch_models/column_02_low", x, y, KEEP_TOP + 620.0, 0.0, 180.0, 180.0, 620.0,
                                            folder, "Keep column"))
    for k, x in enumerate((18700.0, 19900.0)):
        for y in (-700.0, 700.0):
            builder.collide(at_fit(LAVA + "/Mesh/arch_models/column_01_low", x, y, KEEP_TOP + 520.0, 30.0 * k, 130.0, 130.0,
                                            520.0, folder, "Keep column"))

    # The inner gate across the keep, opened by the lever in the north alcove.
    # The lever faces back toward the entrance (its local -X), so the crate meets it pushed on through the keep.
    plates = {}
    placed({"kind": "lever", "x": LEVER[0], "y": LEVER[1], "z": KEEP_TOP, "yaw": 0.0, "id": "keep_lever"}, folder, plates)
    # Wildwood's crate is 52 kg, more than the lever's 40: Seed can hardly shift it, Stone Shell can.
    placed({"kind": "push_block", "x": CRATE[0], "y": CRATE[1], "z": KEEP_TOP + 60.0, "yaw": 0.0, "mass": 52.0}, folder)
    # A portcullis: one of the pack's wall pieces, stretched across the keep, that slides up into the air.
    gate = at_spawn(unreal.load_class(None, "/Script/Assignment1.Gate"), GATE_X, 0.0, KEEP_TOP, "Keep portcullis", folder)
    gate.set_editor_properties({"required_levers": [plates["keep_lever"]], "open_offset": unreal.Vector(0.0, 0.0, 760.0),
                                "hinge_offset": 0.0, "default_open_duration": 3.0,
                                "opening_sound": unreal.load_asset("/Game/LastSeed/Audio/SFX_LS_StoneShake")})
    door = gate.get_editor_property("door")
    slab = unreal.load_asset(LAVA + "/Mesh/arch_models/wall_sw_03_low")
    bounds = slab.get_bounds()
    sx, sy, sz = (y1 - y0 - 40.0) / (bounds.box_extent.x * 2.0), 1.2, 680.0 / (bounds.box_extent.z * 2.0)
    door.set_static_mesh(slab)
    door.set_editor_property("override_materials", [])
    door.set_relative_rotation(unreal.Rotator(yaw=90.0), False, False)
    door.set_relative_scale3d(unreal.Vector(sx, sy, sz))
    # Turned a quarter, the slab's own X runs along the gate's Y, so its centre offsets swap axes.
    door.set_relative_location(unreal.Vector(bounds.origin.y * sy, -bounds.origin.x * sx,
                                             -(bounds.origin.z - bounds.box_extent.z) * sz), False, False)
    gate.get_editor_property("right_door").set_visibility(False, False)
    placed({"kind": "tutorial", "x": x0 + 500.0, "y": 0.0, "z": KEEP_TOP + 150.0, "yaw": 0.0, "half": [300.0, 1200.0, 300.0],
            "message": "The gate is barred. As Stone Shell (press 2), push the crate up against the old lever."}, folder)
    for x, y in ((18300.0, -900.0), (20300.0, 900.0), (22400.0, -900.0), (22400.0, 900.0)):
        at_light(x, y, KEEP_TOP + 420.0, unreal.LinearColor(1.0, 0.42, 0.12), 90.0, 1600.0, folder)


def witch_shots():
    shots = []
    for name, seconds, caption in WITCH_SHOTS:
        task = unreal.AssetImportTask()
        task.set_editor_properties({"filename": str(WITCH_SOURCE / (name + ".png")), "destination_path": WITCH_ART,
                                    "destination_name": "T_LS_" + name, "replace_existing": True, "automated": True, "save": True})
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        art = unreal.load_asset(WITCH_ART + "/T_LS_" + name)
        assert art, name
        art.set_editor_properties({"lod_group": unreal.TextureGroup.TEXTUREGROUP_UI, "never_stream": True,
                                   "mip_gen_settings": unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS})
        assert unreal.EditorAssetLibrary.save_loaded_asset(art, False)
        shot = unreal.LSIntroShot()
        shot.set_editor_properties({"image": art, "duration": seconds, "fade_in": 0.4, "caption": unreal.Text(caption)})
        shots.append(shot)
    return shots


def goal(folder):
    actor = at_spawn(unreal.load_class(None, "/Script/Assignment1.LevelGoal"), GOAL[0], GOAL[1], KEEP_TOP + 235.0, "LevelGoal", folder)
    actor.set_actor_scale3d(unreal.Vector(600.0 / 200.0, 1100.0 / 200.0, 235.0 / 200.0))
    actor.set_editor_properties({
        "energy_finale": True, "travel_shots": witch_shots(), "next_level": unreal.load_asset(WILDWOOD),
        "charge_effect": unreal.load_asset("/Game/FreeParticle_SoftTofu/Niagara/NS_Sparkling_Glow"),
        "burst_effect": unreal.load_asset("/Game/FreeParticle_SoftTofu/Niagara/NS_Sparkling"), "burst_scale": 8.0,
        "charge_shell_mesh": unreal.load_asset("/Engine/BasicShapes/Sphere"), "charge_shell_material": charge_shell_material(),
        "charge_shell_size": 450.0,
        "charge_sound": unreal.load_asset("/Game/LastSeed/Audio/SFX_LS_StormRumble"),
        "burst_sound": unreal.load_asset("/Game/LastSeed/Audio/SFX_LS_DistantThunder"),
        "par_time_seconds": 420.0, "required_petals": 0, "ending_cards": [], "credits_cards": []})
    ring = at_mesh("/Game/LastSeed/Meshes/SM_LS_GateRing", GOAL[0] + 300.0, GOAL[1], KEEP_TOP + 720.0, folder, (2.1, 2.1, 2.1), 0.0,
                      builder.material("M_LS_GoalGlow"), "GoalRing")
    at_light(GOAL[0], GOAL[1], KEEP_TOP + 650.0, unreal.LinearColor(0.5, 1.0, 0.45), 120.0, 3000.0, folder)
    placed({"kind": "tutorial", "x": GATE_X + 350.0, "y": 0.0, "z": KEEP_TOP + 150.0, "yaw": 0.0, "half": [200.0, 1200.0, 300.0],
            "message": "Carry every energy into the ring to face the witch."}, folder)
    return actor


def scenery(folder, rng):
    """Lava cliffs and falls far out on both sides, burning trees and ash rocks round the route, glowing lava floes."""
    for x in (7000.0, 14000.0, 21000.0, 27000.0):
        for side in (-1, 1):
            cliff = LAVA + "/Mesh/lava_a{}".format(1 + (int(x) // 7000 + side) % 2)
            at_mesh(cliff, x + rng.uniform(-600, 600), side * rng.uniform(4300, 5200), LAVA_Z - 80.0, folder, (1.6, 1.6, 1.4),
                       (0.0 if side > 0 else 180.0) + rng.uniform(-8, 8), label="Lava cliff")
    for x, y in ((9500.0, 4200.0), (15200.0, -4300.0), (19800.0, 4400.0)):
        top = LAVA_Z + 1450.0
        at_mesh(LAVA + "/Mesh/waterfal_small", x, y, top, folder, (1.3, 1.3, 1.1), 0.0 if y > 0 else 180.0, label="Lava fall")
        at_niagara(LAVA + "/VFX/Niagara_lava_splash", x, y - math.copysign(250.0, y), LAVA_Z + 10.0, folder, 2.0)
        at_light(x, y - math.copysign(500.0, y), LAVA_Z + 400.0, unreal.LinearColor(1.0, 0.35, 0.08), 220.0, 3500.0, folder)
    floes = [LAVA + "/Mesh/lava_floor_0{}_low".format(k) for k in (1, 2, 3, 4, 5, 7)]
    for k in range(70):
        x, y = rng.uniform(5000, 27000), rng.choice((-1, 1)) * rng.uniform(900, 4000)
        at_mesh(rng.choice(floes), x, y, LAVA_Z + 5.0, folder, (rng.uniform(1.0, 2.4),) * 2 + (1.0,), rng.uniform(0, 360),
                   label="Lava floe")
    for x, y, top in ((8300.0, 250.0, 260.0), (12400.0, 100.0, 300.0)):
        for k in range(3):
            a = rng.uniform(0, 2 * math.pi)
            at_mesh(LAVA + "/Mesh/tree_bush0{}".format(1 + k), x + 380.0 * math.cos(a), y + 330.0 * math.sin(a), top - 10.0, folder,
                       (0.6,) * 3, rng.uniform(0, 360), label="Ember bush")
    for k in range(9):
        x, y = rng.uniform(5500, 23000), rng.choice((-1, 1)) * rng.uniform(1700, 3500)
        at_mesh(basalt_shelf(), x, y, LAVA_Z + rng.uniform(60, 160), folder, (rng.uniform(2.5, 4.5),) * 2 + (2.0,),
                   rng.uniform(0, 360), basalt_material(), "Burnt outcrop")
        scale = rng.uniform(0.28, 0.45)
        at_mesh(LAVA + "/Mesh/tree_new_01", x, y, LAVA_Z + 120.0, folder, (scale,) * 3, rng.uniform(0, 360), label="Burning tree")
    bed = at_spawn(unreal.AmbientSound, 15000.0, 0.0, 0.0, "Lava ambience", folder)
    bed.audio_component.set_sound(unreal.load_asset(LAVA + "/Sound/lava_amb_Cue"))
    bed.audio_component.set_volume_multiplier(0.35)
    bed.audio_component.set_editor_property("allow_spatialization", False)


def open_map():
    """Opens MAP, copying the pack's references map into it the first time."""
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    if editor.get_editor_world().get_path_name().split(".")[0] == MAP:
        return
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages(), "Save your map edits first."
    if not unreal.EditorAssetLibrary.does_asset_exist(MAP):
        assert levels.load_level(SOURCE_MAP)
        assert unreal.EditorLoadingAndSavingUtils.save_map(editor.get_editor_world(), MAP)
    # Save As can leave the source open; build must only ever change the copy.
    assert levels.load_level(MAP)
    assert editor.get_editor_world().get_path_name().split(".")[0] == MAP


def arrival(folder):
    """Seed lands in the basin facing the route, with the painted arrival shot from ls_witch_exile."""
    from ls_witch_exile import exile_shots, sound

    _, shot = exile_shots()
    fire = sound("SFX_LS_EmberwoodFire", loop=True)
    x, y = to_world(*START)
    at_spawn(unreal.PlayerStart, START[0], START[1], ground(x, y) + 110.0, "PlayerStart", folder)
    story = spawn(unreal.StoryTrigger, x, y, 5000.0, "Emberwood landing", folder)
    story.set_editor_properties({"intro_shots": [shot], "intro_music": fire, "play_on_start": True, "arrival_cutscene": True})
    bed = spawn(unreal.AmbientSound, x, y, 0.0, "Emberwood fire", folder)
    bed.audio_component.set_sound(fire)
    bed.audio_component.set_volume_multiplier(0.4)
    bed.audio_component.set_editor_property("allow_spatialization", False)
    # The pack's showcase camera move would take over the view if it played.
    for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        if isinstance(actor, unreal.LevelSequenceActor):
            settings = actor.get_editor_property("playback_settings")
            settings.set_editor_property("auto_play", False)
            actor.set_editor_property("playback_settings", settings)


def lava_beyond(folder, rng):
    """The basin's lava floor stops at its east shore. Beyond it, lower open lava that kills, edged with rocks."""
    sea = at_mesh(lava_plane(), SHORE + 10000.0, 0.0, LAVA_Z, folder,
                  material=unreal.load_asset(LAVA + "/Mesh/plane_lava_10_11").get_material(0), label="Open lava")  # The basin's own lava.
    sea.static_mesh_component.set_cast_shadow(False)
    killer = kill_volume(*to_world(SHORE + 13100.0, 0.0), LAVA_Z - 370.0, 12900.0, 13000.0, 365.0, TURN)
    killer.set_folder_path("World/" + folder)
    # Under the whole map, below the pack's deep lava pit: a fall anywhere returns Seed to its checkpoint.
    kill_volume(3500.0, -3000.0, -1650.0, 25000.0, 25000.0, 200.0).set_folder_path("World/" + folder)
    for v in range(-2900, 2901, 420):
        at_fit(LAVA + "/Mesh/lava_a3", SHORE + 80.0, v, 75.0, rng.uniform(0, 360), 560.0, 560.0, 420.0, folder, "Shore rock")


def build():
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    open_map()
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    clear()
    rng = random.Random(1117)
    rock, island = basalt_material(), basalt_shelf()
    energy_mesh, energy = unreal.load_asset("/Engine/BasicShapes/Sphere"), energy_material()

    arrival(ROOT + "/0 Arrival")
    lava_beyond(ROOT + "/Lava", rng)

    steps = ROOT + "/1 Ember Steps"
    for index, (x, y, top, rx, ry) in enumerate(STEPS):
        stone(x, y, top, rx, ry, steps, index, rock, island)
    for x, y, top in SINKING:
        sinking_stone(x, y, top, steps)
    checkpoint(8300.0, 250.0, 260.0, 0.0, 330.0, steps)
    placed({"kind": "tutorial", "x": 8700.0, "y": 150.0, "z": 410.0, "yaw": 0.0, "half": [250.0, 500.0, 300.0],
            "message": "These stones sink into the lava soon after you land. Keep moving!"}, steps)

    chasm = ROOT + "/2 Updraft Chasm"
    checkpoint(12400.0, 100.0, 300.0, 0.0, 420.0, chasm)
    placed({"kind": "tutorial", "x": 12600.0, "y": 100.0, "z": 450.0, "yaw": 0.0, "half": [300.0, 560.0, 300.0],
            "message": "Too far to jump. Press 3 for Dandelion, ride the hot updrafts, and hold Space to glide."}, chasm)
    for x, y in UPDRAFTS:
        updraft(x, y, chasm)
    for index, (x, y, top, rx, ry) in enumerate(REST_STONES):
        stone(x, y, top, rx, ry, chasm, index + 2, rock, island)

    castle = ROOT + "/3 Ruined Keep"
    keep(castle, rock)
    checkpoint(KEEP[0] + 350.0, 0.0, KEEP_TOP, 0.0, 700.0, castle)
    finale = goal(castle)

    for x, y, z in ENERGY:
        orb(x, y, z, ROOT + "/Energy", energy_mesh, energy)
    scenery(ROOT + "/Scenery", rng)

    assert len(ENERGY) == len(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.LifeNote))
    assert finale.get_editor_property("energy_finale")
    assert levels.save_current_level()
    print("Emberwood built: {} energy, {} stones, {} sinking stones, {} updrafts".format(
        len(ENERGY), len(STEPS) + len(REST_STONES), len(SINKING), len(UPDRAFTS)))
