"""Place Wildwood's landing sigil across the river from the updraft."""
import math

import unreal

from ls_generate_player_meshes import Mesh
from ls_world_common import FULL_COLOUR_STENCIL, import_generated_mesh

LABEL = "River Landing Guide"
LANDING = (15060.0, -2150.0)


def sigil():
    mesh = Mesh()

    def stroke(points, width):
        first = len(mesh.points)
        for i, (y, z) in enumerate(points):
            a, b = points[max(0, i - 1)], points[min(i + 1, len(points) - 1)]
            dy, dz = b[0] - a[0], b[1] - a[1]
            scale = width / (2 * math.hypot(dy, dz))
            for side in (-1, 1):
                mesh.add_vertex((0, y - side * dz * scale, z + side * dy * scale), (0, 0))
        for i in range(first, len(mesh.points) - 2, 2):
            mesh.triangles += [(i, i + 2, i + 1), (i + 1, i + 2, i + 3)]

    for start, end in ((30, 149), (207, 330)):
        angles = [math.radians(start + (end - start) * i / 16) for i in range(17)]
        stroke([(155 * math.cos(angle), 280 + 142 * math.sin(angle)) for angle in angles], 9)
    stroke([(-60, 213), (-62, 254), (-36, 296), (12, 326), (65, 365),
            (58, 307), (35, 256), (-7, 225), (-60, 213)], 13)
    stroke([(-75, 192), (-39, 231), (-3, 266), (26, 307), (65, 365)], 8)
    stroke([(-75, 120), (0, 71), (75, 120)], 15)
    stroke([(-43, 63), (0, 33), (43, 63)], 10)

    # Keep both directions visible when the player looks back from the landing.
    mesh.triangles += [(a, c, b) for a, b, c in mesh.triangles]
    mesh.normals = [(-1.0, 0.0, 0.0)] * len(mesh.points)
    return mesh


def place():
    import build_level1_wildwood as builder

    world = builder.require_map()
    actors = builder.actors.get_all_level_actors()
    updraft = next(a for a in actors if isinstance(a, unreal.WindVolume) and a.get_actor_label() == "Updraft")
    guide = next((a for a in actors if a.get_actor_label() == LABEL), None)
    x, y = LANDING
    ignore = [a for a in actors if not isinstance(a, unreal.LandscapeProxy)
              and a.get_actor_label() != "SM_LS_WildwoodTrail_05"]
    hit = unreal.SystemLibrary.line_trace_single(
        world, unreal.Vector(x, y, 4000), unreal.Vector(x, y, 2000),
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, ignore, unreal.DrawDebugTrace.NONE, True)
    assert hit and hit.to_tuple()[0], "Missing Trail 5 landing surface"
    ground = hit.to_tuple()[4].z
    origin = updraft.get_actor_location()
    yaw = math.degrees(math.atan2(y - origin.y, x - origin.x))
    mesh = import_generated_mesh("SM_LS_RiverLandingGuide", sigil(), nanite=False)
    if guide is None:
        guide = builder.mesh_actor(mesh, x, y, ground + 55, "Parkour", yaw=yaw,
                                   material=builder.material("M_LS_GoalGlow"), label=LABEL)
    guide.set_actor_location(unreal.Vector(x, y, ground + 55), False, False)
    guide.set_actor_rotation(unreal.Rotator(yaw=yaw), False)
    component = guide.static_mesh_component
    component.set_cast_shadow(False)
    component.set_render_custom_depth(True)
    component.set_custom_depth_stencil_value(FULL_COLOUR_STENCIL)
    assert component.get_collision_profile_name() == "NoCollision"
    return guide
