"""Builds Emberwood, Level 2, inside a copy of the lava pack's references map (L_Level2_Emberwood).

Seed lands in the pack's lava basin (all of its ground is safe), then the route runs east out of it over open lava:

1. Ember Steps: hop basalt stones over the lava, then a run of stones that sink a moment after Seed lands.
2. Updraft Chasm: as Dandelion, ride the hot updrafts across a lava gap too wide to jump.
3. The witch's castle: built by hand in the editor from the pack's castle set. Stone Shell pushes a crate onto a lever that
   raises the molten-bar portcullis across its inner arch (ls_witch_castle.py).
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
from ls_material_helpers import colour, combine, finish, fresh_material, library, node, number, output, texture
from ls_witch_exile import LAVA_Z, basalt_material, basalt_shelf, lava_plane
from ls_world_common import hide_component, kill_volume, mesh_actor, niagara, point_light, spawn

MAP = "/Game/LastSeed/Maps/L_Level2_Emberwood"
SOURCE_MAP = "/Game/Lava/Maps/references"  # Copied once into MAP; the pack's own map is never changed.
ORIGIN = (0.0, 2300.0)  # World x, y of the route's (0, 0): the basin's east shore, world y 7500, is route x 5200.
SHORE = 5200.0
START = (-2480.0, 2134.0, 0.0)  # Where Seed lands: world x, y and facing yaw, between the ruined pillars, looking at the old wall.
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
         (12400, 100, 300, 620, 560),  # Checkpoint 2, before the sliding stones.
         (16900, 100, 300, 620, 560)]  # Checkpoint 3, where Dandelion is first needed.
# Section 1b: six stones in a row of their own, each sliding across the lane on its own beat, so Seed has to time each
# hop. (x, top, speed cm/s); each swings SLIDE_SWING either side of the lane's middle and pauses SLIDE_WAIT at the ends.
SLIDERS = [(13100, 300, 260), (13700, 300, 330), (14300, 300, 290), (14900, 300, 380), (15500, 300, 310), (16100, 300, 420)]
SLIDE_SWING = 380.0
SLIDE_WAIT = 0.35
# Everything from the updraft chasm on sits this much further along than it first did, to make room for the rows.
ROWS = 4500.0
ORB_SPARKS = "/Game/FreeParticle_SoftTofu/Niagara/NS_Sparkling_Noise"  # Crackling sparkles on each energy orb.
LAVA_END = 30900.0  # The open lava ends just past here (route x 31200); rocks and effects stop short of it.
# The open lava past the shore, raised to meet the basin's lava; vents and their hot wind start from it.
OPEN_LAVA_Z = 90.0
EFFECT_REACH = 6000.0  # Lava splashes, sparks and glows reach this far either side of the route.
ROCK_CLEAR = 1100.0  # Lava rocks stay at least this far to either side of the route's centre line, near enough to see
# through the haze. A long jump can reach some of them, which is accepted.
# Stones placed by hand across the basin lava before the Ember Steps: (x, y, top), each 190 x 170 cm, unturned.
BASIN_STONES = [(500, 440, 270), (1170, 430, 270), (1910, 420, 380), (2600, 410, 380), (3420, 400, 310), (4200, 390, 310),
                (4920, 250, 250)]
SINKING = [(9050, 200, 270), (9600, 10, 290), (10150, -190, 310), (10700, -60, 330)]
# Section 2: updrafts (x, y) rising from the lava, and two rest stones between them.
UPDRAFTS = [(13900 + ROWS, 60), (15400 + ROWS, -80), (16900 + ROWS, 40)]
REST_STONES = [(14650 + ROWS, -40, 230, 170, 160), (16150 + ROWS, 0, 240, 170, 165)]
# Section 3: the witch's castle. The user built it in the editor from the lava pack's walls, columns, floors and arches,
# outside World/Emberwood, so a rebuild leaves it standing; this script only places its gameplay. Positions are route
# (x, y, z), read from the castle as built. CASTLE is its footprint (x0, x1, y0, y1), which rocks and lava effects avoid.
CASTLE = (23580.0, 29600.0, -1310.0, 1310.0)
CASTLE_CHECKPOINT = (24100.0, -100.0, 250.0)  # In the entrance corridor; its floor top is the z.
CASTLE_LEVER = (27600.0, -950.0, 237.0)  # Right of the inner arch's doorway, facing back down the hall.
CASTLE_CRATE = (27120.0, -950.0, 297.0)  # Where it was moved in the editor: behind the lever in a clear lane.
CASTLE_HINT = (25450.0, -350.0, 387.0)  # Where the hall begins.
GOAL = (29000.0, -300.0)  # Past the gate, in the inner court.
GOAL_FLOOR = 246.0
# The witch taunts Seed across Emberwood: (x, y, z, half x, half y, line). Each plays once, the first time Seed rolls
# through. Her voice is VO_LS_EmberWitch_<n> in LastSeed/Audio (ElevenLabs, the riverbank's Kristen voice); until a
# take is imported the line is a caption alone. They sit clear of the tutorial boxes, which share the prompt.
WITCH_LINES = [
    (50, 1700, 350, 500, 500,
     "Welcome to Emberwood, little seed. Nothing grows here. Nothing ever will. You will burn like all the others."),
    (7450, 320, 400, 250, 350,
     "Hop, hop, little seed. Every stone you trust, I will drag down into the fire."),
    (11250, 80, 480, 250, 350,
     "Still breathing? How tiresome. The lava is patient, little seed. And so am I."),
    (14650 + ROWS, -40, 380, 250, 300,
     "Ride my burning breath, then. One gust from me, and you fall screaming into the flames."),
    (24700, -100, 426, 200, 1300,
     "My castle. My ashes. Its gates obey only me. Turn back, or be buried here with the rest."),
    (28300, 15, 419, 150, 1300,
     "So, you gathered your precious little sparks. Come to me, then. I will snuff out your light myself."),
]
# Energy orbs (x, y, z): about 80 cm over a stone, higher where a jump or an updraft reaches them.
ENERGY = [(2600, -900, 0), (4300, 700, 0),  # In the basin; their height comes from the ground there.
          (5650, 150, 290), (6550, -20, 520), (7450, 320, 350), (8500, 450, 360), (9600, 10, 390), (10700, -60, 430),
          (12600 + ROWS, -150, 400),
          (13900 + ROWS, 60, 950), (14650 + ROWS, -40, 330), (15400 + ROWS, -80, 950), (16900 + ROWS, 40, 950),
          (26400, 350, 394), (27400, -1050, 363), (29000, 350, 388)]  # In the castle: two in the hall, one past the gate.


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


def ground(wx, wy, top=3000.0):
    """The top of whatever is solid at a world x, y: the basin's rocks and lava floor."""
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(wx, wy, top), unreal.Vector(wx, wy, -3000.0),
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
    """A bright green-gold orb that reads at once against orange lava. Its glow surges and flickers, two fast sine waves
    out of step, as if the power inside is straining to get out."""
    material = fresh_material("M_LS_EnergyOrb")
    output(material, colour(material, 0.2, 0.6, 0.25), unreal.MaterialProperty.MP_BASE_COLOR)

    def wave(speed, size):
        sine = node(material, unreal.MaterialExpressionSine)
        library.connect_material_expressions(
            combine(material, unreal.MaterialExpressionMultiply, node(material, unreal.MaterialExpressionTime), number(material, speed)), "", sine, "")
        return combine(material, unreal.MaterialExpressionMultiply, sine, number(material, size))

    surge = combine(material, unreal.MaterialExpressionAdd, number(material, 0.85),
                    combine(material, unreal.MaterialExpressionAdd, wave(7.0, 0.35), wave(23.0, 0.2)))
    glow = combine(material, unreal.MaterialExpressionMultiply, colour(material, 0.45, 1.0, 0.4), number(material, 14.0))
    output(material, combine(material, unreal.MaterialExpressionMultiply, glow, surge), unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    return finish(material)


def energy_arc_material():
    """Lightning crackling off the energy orbs: additive and unlit like the storm bolts, but hot green-white."""
    material = fresh_material("M_LS_EnergyArc")
    material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_ADDITIVE)
    material.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property("two_sided", True)
    output(material, combine(material, unreal.MaterialExpressionMultiply, colour(material, 0.7, 1.0, 0.65), number(material, 28.0)),
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


def paving_material():
    """The keep floor's (floor_a1_low) textures projected from world space, so they don't stretch up a tall stone's sides."""
    material = fresh_material("M_LS_BasaltPaving")
    textures = LAVA + "/Textures/arch/T_floor_a1_low_2_"

    def picked(source, r, g, b):
        mask = node(material, unreal.MaterialExpressionComponentMask, r=r, g=g, b=b, a=False)
        library.connect_material_expressions(source, "", mask, "")
        return mask

    def op(cls, a, b=None, a_pin="A", b_pin="B"):
        result = node(material, cls)
        library.connect_material_expressions(a, "", result, a_pin)
        if b is not None:
            library.connect_material_expressions(b, "", result, b_pin)
        return result

    # The face's own flat normal from screen derivatives: the shelf's smoothed vertex normals smear the rim otherwise.
    position = node(material, unreal.MaterialExpressionWorldPosition)
    face = op(unreal.MaterialExpressionCrossProduct, op(unreal.MaterialExpressionDDY, position, a_pin="Value"),
              op(unreal.MaterialExpressionDDX, position, a_pin="Value"))
    face = op(unreal.MaterialExpressionNormalize, face, a_pin="VectorInput")
    weight = op(unreal.MaterialExpressionPower, op(unreal.MaterialExpressionAbs, face, a_pin=""), number(material, 4.0),
                a_pin="Base", b_pin="Exp")
    weight = op(unreal.MaterialExpressionDivide, weight, op(unreal.MaterialExpressionDotProduct, weight, colour(material, 1.0, 1.0, 1.0)))
    uv = op(unreal.MaterialExpressionDivide, position, number(material, 300.0))  # 300 cm per repeat, near the floor tiles' scale.
    planes = [(picked(uv, True, True, False), picked(weight, False, False, True)),   # Seen from above: x, y.
              (picked(uv, True, False, True), picked(weight, False, True, False)),   # From the side along y: x, z.
              (picked(uv, False, True, True), picked(weight, True, False, False))]   # From the side along x: y, z.

    def projected(name, normal=False):
        total = None
        for coords, share in planes:
            sample = node(material, unreal.MaterialExpressionTextureSample, texture=unreal.load_asset(textures + name))
            if normal:
                sample.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
            library.connect_material_expressions(coords, "", sample, "UVs")
            part = op(unreal.MaterialExpressionMultiply, picked(sample, True, True, True), share)
            total = part if total is None else op(unreal.MaterialExpressionAdd, total, part)
        return total

    output(material, projected("BaseColor"), unreal.MaterialProperty.MP_BASE_COLOR)
    # shortcut: the tangent-space normal is blended as is, not swizzled per plane; fine for rough rock, wrong for sharp detail.
    output(material, projected("Normal", True), unreal.MaterialProperty.MP_NORMAL)
    orm = projected("OcclusionRoughnessMetallic")
    output(material, picked(orm, True, False, False), unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    output(material, picked(orm, False, True, False), unreal.MaterialProperty.MP_ROUGHNESS)
    output(material, picked(orm, False, False, True), unreal.MaterialProperty.MP_METALLIC)
    output(material, number(material, 0.1), unreal.MaterialProperty.MP_SPECULAR)
    # The floor's base material masks its glow with tiling noise; a low flat strength gives the same faint ember cracks.
    output(material, op(unreal.MaterialExpressionMultiply, projected("Emissive"), number(material, 3.0)),
           unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    return finish(material)


def stone(x, y, top, rx, ry, folder, index, rock, island, label="Basalt stone", yaw=None, height=None):
    """A basalt stone like the arrival's: the shelf mesh for looks, a hidden flat cylinder for a fair landing."""
    height = 3.0 + 0.2 * (index % 4) if height is None else height
    at_mesh(island, x, y, top, folder, (rx / 100.0, ry / 100.0, height), index * 47.0 if yaw is None else yaw, rock, label)
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


def sliding_slab():
    """floor_02 with one box for collision. Its own convex hulls never touched Seed once a MovingPlatform moved it."""
    path = "/Game/LastSeed/Meshes/SM_LS_SlidingSlab"
    if not unreal.EditorAssetLibrary.does_asset_exist(path):
        assert unreal.EditorAssetLibrary.duplicate_asset(LAVA + "/Mesh/floor_02", path)
        mesh = unreal.load_asset(path)
        meshes = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
        meshes.remove_collisions(mesh)
        meshes.add_simple_collisions(mesh, unreal.ScriptCollisionShapeType.BOX)
        assert unreal.EditorAssetLibrary.save_loaded_asset(mesh, False)
    return unreal.load_asset(path)


def slider(x, top, speed, from_right, material, folder):
    """A MovingPlatform dressed like the sinking stones (the pack's floor_02 slab, 3 m across), sliding across the lane
    at x and pausing at each end."""
    slab = sliding_slab()
    bounds = slab.get_bounds()
    sx, sy, sz = 300.0 / (bounds.box_extent.x * 2.0), 300.0 / (bounds.box_extent.y * 2.0), 4.0
    # The platform puts the mesh's pivot on its path, so the path is offset to put the slab's top centre at (x, 0, top).
    offset = unreal.Vector(-bounds.origin.x * sx, -bounds.origin.y * sy, top - (bounds.origin.z + bounds.box_extent.z) * sz)
    ends = [to_world(x, -SLIDE_SWING), to_world(x, SLIDE_SWING)]
    if from_right:
        ends.reverse()  # Neighbouring rows start on opposite sides, so the beats don't line up.
    (ax, ay), (bx, by) = ends
    actor = spawn(unreal.load_class(None, "/Script/Assignment1.MovingPlatform"), ax, ay, 0.0, "Sliding stone", folder)
    actor.set_editor_properties({"speed": float(speed), "wait_time": SLIDE_WAIT, "loop": False})
    mesh = actor.get_editor_property("mesh")
    mesh.set_static_mesh(slab)
    mesh.set_editor_property("override_materials", [])  # The slab's own pack material, as on the sinking stones.
    mesh.set_relative_scale3d(unreal.Vector(sx, sy, sz))
    path = actor.get_component_by_class(unreal.SplineComponent)
    path.set_location_at_spline_point(0, unreal.Vector(ax, ay, 0.0) + offset, unreal.SplineCoordinateSpace.WORLD)
    path.set_location_at_spline_point(1, unreal.Vector(bx, by, 0.0) + offset, unreal.SplineCoordinateSpace.WORLD)
    mesh.set_world_location(unreal.Vector(ax, ay, 0.0) + offset, False, False)
    return actor


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
    # Sparks crackling off it and a hard tremble: it looks barely able to hold its power. Both go when it is collected.
    actor.set_editor_properties({"idle_effect": unreal.load_asset(ORB_SPARKS), "idle_effect_scale": 1.6, "shake_amount": 8.0})
    # Lightning: Wildwood's storm bolts, shrunk to arcs that leap out of the orb in new directions many times a second.
    actor.set_editor_properties({"arc_meshes": [unreal.load_asset("/Game/LastSeed/Weather/SM_LS_SkyLightning_0%d" % k) for k in (1, 2, 3)],
                                 "arc_material": unreal.load_asset("/Game/LastSeed/Materials/M_LS_EnergyArc"), "arc_count": 4,
                                 "arc_length": 110.0, "arc_flicker_time": 0.07})
    # Attached, so collecting the orb takes its glow with it.
    glow = at_light(x, y, z, unreal.LinearColor(0.45, 1.0, 0.4), 30.0, 450.0, folder)
    glow.attach_to_actor(actor, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD,
                         unreal.AttachmentRule.KEEP_WORLD, False)


def heat_wind_material():
    """Hot air you can see: lava-noise smoke streaming upward, glowing ember-orange low down and fading to grey smoke
    high up, soft at the column's edges and its ends. For a 1 m engine cylinder stretched over an updraft."""
    material = fresh_material("M_LS_HeatWind")
    material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    material.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property("two_sided", True)

    def streak(u_tiles, v_tiles, speed_u, speed_v):
        coords = node(material, unreal.MaterialExpressionTextureCoordinate, u_tiling=u_tiles, v_tiling=v_tiles)
        pan = node(material, unreal.MaterialExpressionPanner, speed_x=speed_u, speed_y=speed_v)
        library.connect_material_expressions(coords, "", pan, "Coordinate")
        return node_mask(texture(material, LAVA + "/VFX/textures_vfx/T_lava_dif_noise", pan), "r")

    def node_mask(source, channel):
        picked = node(material, unreal.MaterialExpressionComponentMask, r=channel == "r", g=channel == "g", b=False, a=False)
        library.connect_material_expressions(source, "", picked, "")
        return picked

    # Two layers of noise rising at different speeds read as turbulent smoke rather than a sliding texture.
    smoke = combine(material, unreal.MaterialExpressionMultiply,
                    combine(material, unreal.MaterialExpressionMultiply, streak(2.0, 1.0, 0.03, 0.35), streak(3.0, 1.6, -0.05, 0.6)),
                    number(material, 2.2))
    height = node_mask(node(material, unreal.MaterialExpressionTextureCoordinate), "g")  # 0 at the top, 1 at the bottom.
    ends = combine(material, unreal.MaterialExpressionMultiply, number(material, 4.0),
                   combine(material, unreal.MaterialExpressionMultiply, height,
                           combine(material, unreal.MaterialExpressionSubtract, number(material, 1.0), height)))
    rim = node(material, unreal.MaterialExpressionFresnel, exponent=1.5, base_reflect_fraction=0.0)
    edge = combine(material, unreal.MaterialExpressionSubtract, number(material, 1.0), rim)
    shape = combine(material, unreal.MaterialExpressionMultiply, smoke, combine(material, unreal.MaterialExpressionMultiply, ends, edge))
    fire = combine(material, unreal.MaterialExpressionMultiply, colour(material, 1.0, 0.25, 0.03), number(material, 3.0))
    ash = colour(material, 0.09, 0.075, 0.065)
    tint = node(material, unreal.MaterialExpressionLinearInterpolate)
    library.connect_material_expressions(ash, "", tint, "A")
    library.connect_material_expressions(fire, "", tint, "B")
    library.connect_material_expressions(combine(material, unreal.MaterialExpressionMultiply, height, height), "", tint, "Alpha")
    output(material, combine(material, unreal.MaterialExpressionMultiply, tint, shape), unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    opacity = node(material, unreal.MaterialExpressionSaturate)
    library.connect_material_expressions(combine(material, unreal.MaterialExpressionMultiply, shape, number(material, 0.6)), "", opacity, "")
    output(material, opacity, unreal.MaterialProperty.MP_OPACITY)
    return finish(material)


def updraft(x, y, folder, wind):
    """Hot air from a vent in the lava: rises from the surface to well above the stones, strong enough for Dandelion.
    It shows: a glowing vent, a column of hot smoke, and embers streaming up through it."""
    half = (300.0, 300.0, 900.0)
    z = LAVA_Z + half[2]
    actor = at_spawn(builder.gameplay_class("BP_WindVolume", "WindVolume"), x, y, z, "Updraft", folder)
    actor.set_actor_scale3d(unreal.Vector(*[h / 200.0 for h in half]))
    actor.set_editor_properties({"wind_direction": unreal.Vector(0.0, 0.0, 1.0), "strength": 900.0})
    top = LAVA_Z + 2.0 * half[2]
    rise = top - OPEN_LAVA_Z  # The visible column runs from the lava surface to the top of the wind.
    for k in range(4):
        at_niagara(LAVA + "/VFX/Niagara_sparks_only", x, y, OPEN_LAVA_Z + 20.0 + k * rise / 4.0, folder, 1.6)
    at_niagara(LAVA + "/VFX/Niagara_sparks_1000_1000", x, y, OPEN_LAVA_Z + 10.0, folder, 1.0)
    at_mesh(LAVA + "/Mesh/lava_floor_06_low", x, y, OPEN_LAVA_Z - 20.0, folder, (1.4, 1.4, 1.0), x % 360, label="Lava vent")
    middle = OPEN_LAVA_Z + rise / 2.0
    at_mesh("/Engine/BasicShapes/Cylinder", x, y, middle, folder, (5.5, 5.5, rise / 100.0), 0.0, wind, "Hot wind")
    at_light(x, y, OPEN_LAVA_Z + 250.0, unreal.LinearColor(1.0, 0.45, 0.1), 160.0, 1800.0, folder)


def lava_boulder(scale=0.48):
    """Dresses the castle's crate as the pack's lava boulder (lava_a3). A box collider keeps it sliding flat like the
    crate it replaces, and its bottom sits where the crate's did."""
    path = "/Game/LastSeed/Meshes/SM_LS_LavaBoulder"
    if not unreal.EditorAssetLibrary.does_asset_exist(path):
        unreal.EditorAssetLibrary.duplicate_asset(LAVA + "/Mesh/lava_a3", path)
        mesh = unreal.load_asset(path)
        meshes = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
        meshes.remove_collisions(mesh)
        meshes.add_simple_collisions(mesh, unreal.ScriptCollisionShapeType.BOX)
        unreal.EditorAssetLibrary.save_asset(path)
    mesh = unreal.load_asset(path)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    block = next(a for a in actors.get_all_level_actors() if isinstance(a, unreal.PushableBlock))
    component = block.get_component_by_class(unreal.StaticMeshComponent)
    component.set_static_mesh(mesh)
    component.set_material(0, mesh.get_material(0))
    floor = block.get_actor_location().z - 50.0  # The crate is a 1 m cube on its centre.
    block.set_actor_scale3d(unreal.Vector(scale, scale, scale))
    where = block.get_actor_location()
    block.set_actor_location(unreal.Vector(where.x, where.y, floor - mesh.get_bounding_box().min.z * scale + 1.0), False, False)
    block.set_actor_label("Lava boulder")


def castle_gameplay(folder):
    """The witch's castle's puzzle: a checkpoint in its entrance, the crate and lever in its hall, and the molten-bar
    portcullis across its inner arch (ls_witch_castle.py), opened when Stone pushes the crate onto the lever."""
    import ls_witch_castle

    x, y, top = CASTLE_CHECKPOINT
    checkpoint(x, y, top, 0.0, 180.0, folder)  # The corridor is 5 m wide, so the lantern stands close to the path.
    plates = {}
    x, y, z = CASTLE_LEVER
    # The lever faces back down the hall (its local -X), so the crate meets it pushed on toward the gate.
    placed({"kind": "lever", "x": x, "y": y, "z": z, "yaw": 0.0, "id": "castle_lever"}, folder, plates)
    x, y, z = CASTLE_CRATE
    # Wildwood's crate is 52 kg, more than the lever's 40: Seed can hardly shift it, Stone Shell can.
    placed({"kind": "push_block", "x": x, "y": y, "z": z, "yaw": 0.0, "mass": 52.0}, folder)
    lava_boulder()
    x, y, z = CASTLE_HINT
    placed({"kind": "tutorial", "x": x, "y": y, "z": z, "yaw": 0.0, "half": [300.0, 1200.0, 300.0],
            "message": "The gate is barred. As Stone Shell (press 2), push the boulder up against the old lever."}, folder)
    gate = ls_witch_castle.build()
    gate.set_editor_property("required_levers", [plates["castle_lever"]])


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
    actor = at_spawn(unreal.load_class(None, "/Script/Assignment1.LevelGoal"), GOAL[0], GOAL[1], GOAL_FLOOR + 235.0, "LevelGoal", folder)
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
    ring = at_mesh("/Game/LastSeed/Meshes/SM_LS_GateRing", GOAL[0] + 300.0, GOAL[1], GOAL_FLOOR + 720.0, folder, (2.1, 2.1, 2.1), 0.0,
                      builder.material("M_LS_GoalGlow"), "GoalRing")
    at_light(GOAL[0], GOAL[1], GOAL_FLOOR + 650.0, unreal.LinearColor(0.5, 1.0, 0.45), 120.0, 3000.0, folder)
    placed({"kind": "tutorial", "x": 28650.0, "y": 15.0, "z": 399.0, "yaw": 0.0, "half": [200.0, 1200.0, 300.0],
            "message": "Carry every energy into the ring to face the witch."}, folder)
    return actor


def lava_effects(folder):
    """The reference basin's lava effects, spread thickly over the open lava: splashes of mixed sizes, spark
    bursts and plumes, small red-orange glows, and its glowing fog sheet lying just above the surface. They stay within
    EFFECT_REACH of the route, the part the haze lets anyone see, and out of the castle."""
    rng = random.Random(2701)  # Its own seed, so the scenery and rocks keep their layout.
    x0, x1 = SHORE + 200.0, min(CASTLE[1] + 2500.0, LAVA_END)

    def spot(reach=EFFECT_REACH):
        while True:
            x, y = rng.uniform(x0, x1), rng.uniform(-reach, reach)
            if not (CASTLE[0] - 200.0 < x < CASTLE[1] + 200.0 and abs(y) < CASTLE[3] + 200.0):
                return x, y

    # (effect, count, height over the lava, smallest and largest size, how far out). Half the splashes crowd the
    # route, where they are seen; the big ones are rarer bursts of molten rock.
    effects = (("Niagara_lava_splash", 180, 5.0, 0.8, 1.6, EFFECT_REACH), ("Niagara_lava_splash", 180, 5.0, 0.8, 1.6, 2800.0),
               ("Niagara_lava_splash", 40, 5.0, 2.2, 3.2, EFFECT_REACH),
               ("Niagara_sparks_1000_1000", 170, 15.0, 0.9, 1.5, EFFECT_REACH),
               ("Niagara_sparks_only", 60, 140.0, 1.0, 1.8, EFFECT_REACH))
    for path, count, lift, low, high, reach in effects:
        for _ in range(count):
            at_niagara(LAVA + "/VFX/" + path, *spot(reach), OPEN_LAVA_Z + lift, folder, rng.uniform(low, high))
    for _ in range(26):
        at_light(*spot(), OPEN_LAVA_Z + 120.0, unreal.LinearColor(1.0, 0.12, 0.0), 300.0, 1400.0, folder)
    # The basin's fog sheet (Plane4) is the engine plane at scale 65 with mtl_FOG_inst, 23 cm over the lava: the same
    # sheets tile the open lava. They have no collision, unlike the basin's.
    fog = unreal.load_asset(LAVA + "/VFX/mtl/mtl_FOG_inst")
    for col in range(4):
        for side in (-1, 1):
            at_mesh("/Engine/BasicShapes/Plane", SHORE + 3250.0 + 6500.0 * col, side * 3250.0, OPEN_LAVA_Z + 23.0, folder,
                    (65.0, 65.0, 65.0), 0.0, fog, "Lava fog")


def lava_rocks(folder):
    """Clusters of the basin's own rocks across the open lava, so it reads like the reference map and not a flat sea.
    Low dark hell_02 boulders and rocky lava-floor patches, at least ROCK_CLEAR off the route."""
    rng = random.Random(2611)  # Its own seed, so the scenery's random layout stays as it was.
    pieces = [("hell_02", 60.0, 1.2, 2.6)] * 4 + [("lava_floor_0{}_low".format(k), 45.0, 1.0, 1.9) for k in (2, 4, 5, 7)]
    placed_rocks = 0
    for _ in range(95):
        cx = rng.uniform(SHORE + 400.0, min(CASTLE[1] + 1500.0, LAVA_END))
        cy = rng.choice((-1, 1)) * rng.uniform(ROCK_CLEAR + 200.0, 3800.0)
        for _ in range(rng.randint(2, 5)):
            name, rise, low, high = rng.choice(pieces)
            mesh = unreal.load_asset(LAVA + "/Mesh/" + name)
            bounds = mesh.get_bounds()
            size = rng.uniform(low, high)
            x, y = cx + rng.uniform(-500, 500), cy + rng.uniform(-450, 450)
            if abs(y) < ROCK_CLEAR or (CASTLE[0] - 300.0 < x < CASTLE[1] + 300.0 and abs(y) < CASTLE[3] + 700.0):
                continue  # Off the route, and out of the castle.
            # Each shows its top a little above the lava, as in the basin, however its pivot sits.
            top = OPEN_LAVA_Z + rise * rng.uniform(0.6, 1.4) * size
            z = top - (bounds.origin.z + bounds.box_extent.z) * size
            rock = at_mesh(LAVA + "/Mesh/" + name, x, y, z, folder, (size, size, size), rng.uniform(0, 360), label="Lava rock")
            rock.static_mesh_component.set_collision_profile_name("BlockAll")  # Solid, like the basin's rocks.
            placed_rocks += 1
    return placed_rocks


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
    x, y, yaw = START
    spawn(unreal.PlayerStart, x, y, ground(x, y, 700.0) + 110.0, "PlayerStart", folder, yaw)  # From below the ruin's arches.
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


def burning(volume, surface):
    """Lava kills with a splash of molten rock, sparks and a fire catching, instead of Seed just vanishing.
    It kills only while surface (the lava itself) is what Seed rests on, so floors and rocks over the lava are safe."""
    volume.set_editor_properties({
        "lava_surface": surface,
        "burn_effects": [unreal.load_asset(LAVA + "/VFX/Niagara_lava_splash"), unreal.load_asset(LAVA + "/VFX/Niagara_sparks_only")],
        "burn_sound": unreal.load_asset("/Game/LastSeed/Audio/SFX_LS_LanternLight"),
        "burn_effect_scale": 1.5,
        # Droplets of the basin's own molten lava burst up where Seed goes in (ALSLavaSplash).
        "splash_material": unreal.load_asset(LAVA + "/Mesh/plane_lava_10_11").get_material(0),
        "splash_size": 1.0})


def witch_lines(folder):
    """Invisible boxes along the route; each shows one of the witch's lines and speaks it once."""
    for n, (x, y, z, hx, hy, line) in enumerate(WITCH_LINES, 1):
        actor = at_spawn(unreal.load_class(None, "/Script/Assignment1.TutorialTrigger"), x, y, z, "Witch line %d" % n, folder)
        actor.set_actor_scale3d(unreal.Vector(hx / 200.0, hy / 200.0, 300.0 / 200.0))
        actor.set_editor_properties({"title": unreal.Text("THE WITCH"), "message": unreal.Text("“%s”" % line),
                                     "display_duration": 7.0})
        voice = "/Game/LastSeed/Audio/VO_LS_EmberWitch_%d" % n
        if unreal.EditorAssetLibrary.does_asset_exist(voice):  # Made by ls_ember_witch_voice.py.
            sound = unreal.load_asset(voice)
            actor.set_editor_properties({"voice": sound, "display_duration": max(7.0, sound.get_editor_property("duration") - 1.5)})


def lava_tile_killer(tile, folder, label="Lava tile"):
    """A burning kill box under one lava tile or lava floor piece, its top 5 cm above the surface and turned with the tile."""
    origin, extent = tile.static_mesh_component.static_mesh.get_bounds().origin, tile.static_mesh_component.static_mesh.get_bounds().box_extent
    scale = tile.get_actor_scale3d()
    top = tile.get_actor_transform().transform_location(unreal.Vector(origin.x, origin.y, origin.z + extent.z))
    centre = top + tile.get_actor_up_vector() * (5.0 - 200.0)
    volume = kill_volume(centre.x, centre.y, centre.z, extent.x * abs(scale.x), extent.y * abs(scale.y), 200.0)
    volume.set_actor_rotation(tile.get_actor_rotation(), False)
    volume.set_actor_label(label)
    volume.set_folder_path("World/" + folder)
    # A surface Seed can't rest on (the open lava has no collision) can't be the thing under it, so entering kills.
    solid = tile.static_mesh_component.get_collision_enabled() != unreal.CollisionEnabled.NO_COLLISION
    burning(volume, tile if solid else None)


def lava_beyond(folder, rng):
    """The basin's lava floor stops at its east shore. Beyond it, lower open lava that kills, edged with rocks."""
    sea = at_mesh(lava_plane(), SHORE + 10000.0, 0.0, OPEN_LAVA_Z, folder,
                  material=unreal.load_asset(LAVA + "/Mesh/plane_lava_10_11").get_material(0), label="Open lava")  # The basin's own lava.
    sea.static_mesh_component.set_cast_shadow(False)
    lava_tile_killer(sea, folder, "Open lava burn")  # Its top just above the surface Seed rolls on.
    # The reference map's glowing lava sheet over the basin (Plane4): touching it burns Seed up. The box tops out just above it.
    sheet = next(a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
                 if a.get_actor_label() == "Plane4")
    # The sheet is tilted a quarter degree (13 cm across), so the box takes its rotation to stay just above it everywhere.
    centre = sheet.get_actor_location() - sheet.get_actor_up_vector() * 195.0
    half = sheet.get_actor_scale3d() * 50.0  # The engine plane is 100 cm across.
    basin = kill_volume(centre.x, centre.y, centre.z, half.x, half.y, 200.0)
    basin.set_actor_rotation(sheet.get_actor_rotation(), False)
    basin.set_actor_label("Basin lava")
    basin.set_folder_path("World/" + folder)
    burning(basin, sheet)
    # Every lava tile of the reference map burns too, wherever it shows between the rocks.
    for tile in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        if isinstance(tile, unreal.StaticMeshActor) and tile.static_mesh_component.static_mesh \
                and tile.static_mesh_component.static_mesh.get_name() == "plane_lava_10_11" and tile.get_folder_path().is_none():
            lava_tile_killer(tile, folder)
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
    # The stepping stones wear the keep floor's own stone, so the route reads as one ruin.
    paving = paving_material()
    energy_mesh, energy = unreal.load_asset("/Engine/BasicShapes/Sphere"), energy_material()
    energy_arc_material()  # The orbs' lightning, set up before them.
    wind = heat_wind_material()

    arrival(ROOT + "/0 Arrival")
    lava_beyond(ROOT + "/Lava", rng)

    steps = ROOT + "/1 Ember Steps"
    for x, y, top in BASIN_STONES:
        stone(x, y, top, 190, 170, steps, 0, paving, island, yaw=0.0, height=3.0)
    for index, (x, y, top, rx, ry) in enumerate(STEPS):
        stone(x, y, top, rx, ry, steps, index, paving, island)
    for x, y, top in SINKING:
        sinking_stone(x, y, top, steps)
    checkpoint(8300.0, 250.0, 260.0, 0.0, 330.0, steps)
    placed({"kind": "tutorial", "x": 8700.0, "y": 150.0, "z": 410.0, "yaw": 0.0, "half": [250.0, 500.0, 300.0],
            "message": "These stones sink into the lava soon after you land. Keep moving!"}, steps)

    rows = ROOT + "/1b Sliding Stones"
    checkpoint(12400.0, 100.0, 300.0, 0.0, 420.0, rows)
    placed({"kind": "tutorial", "x": 12600.0, "y": 100.0, "z": 450.0, "yaw": 0.0, "half": [250.0, 560.0, 300.0],
            "message": "These stones slide from side to side. Watch their rhythm, and jump when the next one swings in front of you."},
           rows)
    for index, (x, top, speed) in enumerate(SLIDERS):
        slider(x, top, speed, index % 2 == 1, paving, rows)

    chasm = ROOT + "/2 Updraft Chasm"
    checkpoint(16900.0, 100.0, 300.0, 0.0, 420.0, chasm)
    placed({"kind": "tutorial", "x": 12600.0 + ROWS, "y": 100.0, "z": 450.0, "yaw": 0.0, "half": [300.0, 560.0, 300.0],
            "message": "Too far to jump. Press 3 for Dandelion, ride the hot updrafts, and hold Space to glide."}, chasm)
    for x, y in UPDRAFTS:
        updraft(x, y, chasm, wind)
    for index, (x, y, top, rx, ry) in enumerate(REST_STONES):
        stone(x, y, top, rx, ry, chasm, index + 2, paving, island)

    castle = ROOT + "/4 Witch Castle"
    castle_gameplay(castle)
    finale = goal(castle)

    for x, y, z in ENERGY:
        orb(x, y, z, ROOT + "/Energy", energy_mesh, energy)
    scenery(ROOT + "/Scenery", rng)
    lava_rocks(ROOT + "/Lava Rocks")
    lava_effects(ROOT + "/Lava Effects")
    witch_lines(ROOT + "/Witch")
    import ls_ember_music
    ls_ember_music.build()  # The level's music, "Juggernaut" by Scott Buckley.
    # The glowing lava_floor_01_low pieces, the map's own and the scenery's, burn like the lava tiles.
    for piece in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        mesh = piece.static_mesh_component.static_mesh if isinstance(piece, unreal.StaticMeshActor) else None
        if mesh and mesh.get_name() == "lava_floor_01_low":
            lava_tile_killer(piece, ROOT + "/Lava", "Lava floor")

    assert len(ENERGY) == len(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.LifeNote))
    assert finale.get_editor_property("energy_finale")
    assert levels.save_current_level()
    print("Emberwood built: {} energy, {} stones, {} sinking stones, {} updrafts".format(
        len(ENERGY), len(STEPS) + len(REST_STONES), len(SINKING), len(UPDRAFTS)))
