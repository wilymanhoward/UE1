"""The witch's castle in Emberwood, which the user built from the lava pack's wall, column and arch pieces.

This file only adds its gameplay. Across the inner archway (arch_hole_01_low4) it puts a prison-style portcullis of
molten-lava bars. A lever in the hall opens it, but only when Stone pushes the crate onto the lever. Run in the editor
with Emberwood open: import ls_witch_castle; ls_witch_castle.build()
"""
import unreal

from ls_generate_player_meshes import Mesh
from ls_world_common import import_generated_mesh

FOLDER = "World/Emberwood/4 Witch Castle"
ARCH = "arch_hole_01_low4"  # The doorway the gate closes; the castle's hall is on its -Y side.
GATE_WIDTH = 340.0  # A little wider than the 290 cm opening, so the outer bars sit in the wall.
GATE_HEIGHT = 460.0  # The opening's top is about 690 cm, 440 above the floor; the rest hides in the wall.
BAR = 14.0  # Bar thickness. Bars are BAR_PITCH apart, centre to centre: gaps of 26 cm, far too narrow for Seed.
BAR_PITCH = 40.0
LAVA = "/Game/Lava"


def box(mesh, x0, x1, y0, y1, z0, z1, tile=100.0):
    """An axis-aligned box with flat faces wound outward, each with planar UVs at tile cm a repeat."""
    faces = (((x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (0, 0, -1)),
             ((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1), (0, 0, 1)),
             ((x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1), (0, -1, 0)),
             ((x0, y1, z0), (x0, y1, z1), (x1, y1, z1), (x1, y1, z0), (0, 1, 0)),
             ((x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0), (-1, 0, 0)),
             ((x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1), (1, 0, 0)))
    for *corners, normal in faces:
        axis = [abs(n) for n in normal].index(1)
        a, b = [i for i in range(3) if i != axis]
        first = len(mesh.points)
        for p in corners:
            mesh.add_vertex(p, (p[a] / tile, p[b] / tile), normal)
        # Wound so the cross product of the first two edges points along the face's normal, the way Mesh faces out.
        mesh.triangles += [(first, first + 1, first + 2), (first, first + 2, first + 3)]


def gate_mesh():
    """Upright bars and three crossbars, centred on x, standing on z = 0, BAR thick in y. Planar UVs at 1 m a tile."""
    mesh = Mesh()
    half_w, half_t = GATE_WIDTH / 2.0, BAR / 2.0
    count = int(GATE_WIDTH // BAR_PITCH) + 1
    first = -(count - 1) * BAR_PITCH / 2.0
    for k in range(count):
        x = first + k * BAR_PITCH
        box(mesh, x - BAR / 2.0, x + BAR / 2.0, -half_t, half_t, 0.0, GATE_HEIGHT)
    for z in (0.0, GATE_HEIGHT * 0.42, GATE_HEIGHT - 20.0):
        box(mesh, -half_w, half_w, -half_t - 3.0, half_t + 3.0, z, z + 20.0)
    return mesh


def build():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    arch = next(a for a in actors.get_all_level_actors() if a.get_actor_label() == ARCH)
    old = [a for a in actors.get_all_level_actors() if a.get_actor_label() == "Castle portcullis"]
    if old:
        actors.destroy_actors(old)

    centre, _ = arch.get_actor_bounds(False)
    x, y = -15.0, centre.y  # The opening runs x -150..+130 at Seed's height.
    hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, 1000.0), unreal.Vector(x, y, 0.0),
                                                 unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [arch], unreal.DrawDebugTrace.NONE, True)
    floor = hit.to_tuple()[4].z if hit and hit.to_tuple()[0] else 250.0

    asset = unreal.load_asset(import_generated_mesh("SM_LS_CastlePortcullis", gate_mesh(), solid=True))
    gate = actors.spawn_actor_from_class(unreal.load_class(None, "/Script/Assignment1.Gate"), unreal.Vector(x, y, floor))
    gate.set_actor_label("Castle portcullis")
    gate.set_folder_path(FOLDER)
    door = gate.get_editor_property("door")
    door.set_static_mesh(asset)
    # The basin's molten lava, so the bars glow like they were forged in it.
    door.set_material(0, unreal.load_asset(LAVA + "/Mesh/plane_lava_10_11").get_material(0))
    door.set_relative_location(unreal.Vector(0.0, 0.0, 0.0), False, False)
    door.set_relative_rotation(unreal.Rotator(0.0, 0.0, 0.0), False, False)
    door.set_relative_scale3d(unreal.Vector(1.0, 1.0, 1.0))
    gate.set_editor_properties({"open_offset": unreal.Vector(0.0, 0.0, GATE_HEIGHT - 20.0), "hinge_offset": 0.0,
                                "default_open_duration": 3.0,
                                "opening_sound": unreal.load_asset("/Game/LastSeed/Audio/SFX_LS_StoneShake")})
    print("Castle portcullis at", gate.get_actor_location(), "floor", round(floor))
    return gate
