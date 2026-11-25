"""Close the gaps under Wildwood's trail: a grassy bank from each trail piece's outer edge down to the ground.

The trail pieces keep their own height, so where the landscape dips the trail hung in the air with a dark hollow under
its edge. Each piece now gets a skirt: from every outer edge vertex a slope runs outward and down to just below the
ground beside it. It looks like the trail sits on a raised bank of earth. The skirt has no collision, so the surface the
ball rolls on and every drop stay exactly as they were. A drop deeper than MAX_DROP (a gorge or river crossing, meant to
be there) gets no bank.
Run in the editor with Wildwood open, after the trail pieces are built: import ls_trail_skirts; ls_trail_skirts.build()
"""
import math
from pathlib import Path

import unreal

from ls_generate_player_meshes import Mesh, smoothstep
from ls_world_common import import_generated_mesh

MAX_DROP = 500.0  # Deeper than this below an edge is a real drop: no bank there.
SINK = 30.0  # The bank's foot ends this far under the ground, so no seam shows.
RINGS = 5  # Points down each slope.
FOLDER = "World/Trail/Banks"


def source_obj(name):
    import build_level1_wildwood as builder

    work = Path(builder.WORK)
    blended = work / "BlendedBanks" / (name + ".obj")
    return blended if blended.exists() else work / (name + ".obj")


def read_obj(path):
    """Positions in Unreal space (the files store -y) and triangles, with any quads split."""
    points, triangles = [], []
    for line in path.read_text().splitlines():
        if line.startswith("v "):
            x, y, z = map(float, line.split()[1:4])
            points.append((x, -y, z))
        elif line.startswith("f "):
            ids = [int(part.split("/")[0]) - 1 for part in line.split()[1:]]
            triangles += [(ids[0], ids[i], ids[i + 1]) for i in range(1, len(ids) - 1)]
    return points, triangles


def outer_edges(points, triangles):
    """Each edge used by one triangle, with its outward direction across the ground (away from that triangle)."""
    uses = {}
    for tri in triangles:
        for i in range(3):
            a, b, c = tri[i], tri[(i + 1) % 3], tri[(i + 2) % 3]
            uses.setdefault((min(a, b), max(a, b)), []).append(c)
    edges = []
    for (a, b), opposite in uses.items():
        if len(opposite) != 1:
            continue
        (ax, ay, _), (bx, by, _), (cx, cy, _) = points[a], points[b], points[opposite[0]]
        nx, ny = -(by - ay), bx - ax
        if nx * (cx - ax) + ny * (cy - ay) > 0:
            nx, ny = -nx, -ny
        length = math.hypot(nx, ny)
        if length > 1e-6:
            edges.append((a, b, nx / length, ny / length))
    return edges


def build(only=None):
    """Rebuilds every trail piece's bank, or just the piece named only (e.g. "SM_LS_WildwoodTrail_Approach")."""
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    old = [a for a in actors.get_all_level_actors() if a.get_actor_label().endswith("_Bank")
           and (only is None or a.get_actor_label() == only + "_Bank")]
    if old:
        actors.destroy_actors(old)
    # Every piece is left out of the ground traces, so a bank never rests on a trail. Banks have no collision anyway.
    trails = [a for a in actors.get_all_level_actors()
              if isinstance(a, unreal.StaticMeshActor) and a.get_actor_label().startswith("SM_LS_WildwoodTrail")
              and not a.get_actor_label().endswith("_Bank")]
    assert trails, "Open Wildwood first"
    rebuild = [t for t in trails if only is None or t.get_actor_label() == only]
    assert rebuild, only

    def ground(x, y, top):
        hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, top + 300.0), unreal.Vector(x, y, top - 3000.0),
                                                     unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, trails,
                                                     unreal.DrawDebugTrace.NONE, True)
        data = hit.to_tuple() if hit else None
        return data[4].z if data and data[0] else None

    for trail in rebuild:
        name = trail.get_actor_label()
        description = trail.static_mesh_component.static_mesh.get_static_mesh_description(0)
        points, triangles = read_obj(source_obj(name))
        # The source must be the mesh in the level, or the bank would follow an old shape.
        assert len(points) == description.get_vertex_count(), (name, len(points), description.get_vertex_count())
        for i in (0, len(points) // 2, len(points) - 1):
            live = description.get_vertex_position(unreal.VertexID(i))
            assert math.dist(points[i], (live.x, live.y, live.z)) < 1.0, (name, i)

        edges = outer_edges(points, triangles)
        outward = {}
        for a, b, nx, ny in edges:
            for v in (a, b):
                ox, oy = outward.get(v, (0.0, 0.0))
                outward[v] = (ox + nx, oy + ny)

        mesh = Mesh()
        rings, skipped = {}, 0
        for v, (ox, oy) in outward.items():
            length = math.hypot(ox, oy)
            x, y, z = points[v]
            below = ground(x, y, z)
            if length < 1e-6 or below is None or z - below > MAX_DROP:
                skipped += 1
                continue
            ox, oy = ox / length, oy / length
            reach = min(max((z - below) * 1.4 + 50.0, 50.0), 700.0)
            ring = []
            for k in range(RINGS + 1):
                f = k / RINGS
                px, py = x + ox * (2.0 + reach * f), y + oy * (2.0 + reach * f)
                floor = ground(px, py, z)
                floor = below if floor is None else floor
                pz = z - 2.0 + (floor - SINK - (z - 2.0)) * smoothstep(0.0, 1.0, f)
                ring.append(len(mesh.points))
                mesh.add_vertex((px, py, pz), ((px + py) / 400.0, 1.12 + 0.9 * f))
            rings[v] = (ring, ox, oy)

        for a, b, nx, ny in edges:
            if a not in rings or b not in rings:
                continue
            ra, rb = rings[a][0], rings[b][0]
            for k in range(RINGS):
                quad = (ra[k], rb[k], rb[k + 1], ra[k + 1])
                for tri in ((quad[0], quad[1], quad[2]), (quad[0], quad[2], quad[3])):
                    p, q, r = (mesh.points[i] for i in tri)
                    u = (q[0] - p[0], q[1] - p[1], q[2] - p[2])
                    w = (r[0] - p[0], r[1] - p[1], r[2] - p[2])
                    normal = (u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0])
                    # Face up and out, away from the trail, so the bank is seen from the side people look at it from.
                    if normal[0] * nx + normal[1] * ny + normal[2] < 0:
                        tri = (tri[0], tri[2], tri[1])
                    mesh.triangles.append(tri)
        assert mesh.triangles and all(math.isfinite(c) for p in mesh.points for c in p), name
        mesh.smooth_normals()

        asset = unreal.load_asset(import_generated_mesh(name + "_Bank", mesh, nanite=False))
        # The importer wraps the whole bank, trail hole and all, in one convex hull; Seed rolled on top of it in mid-air.
        unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).remove_collisions(asset)
        assert unreal.EditorAssetLibrary.save_loaded_asset(asset, False)
        bank = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, 0))
        bank.set_actor_label(name + "_Bank")
        bank.set_folder_path(FOLDER)
        component = bank.static_mesh_component
        component.set_static_mesh(asset)
        component.set_material(0, trail.static_mesh_component.get_material(0))
        component.set_collision_profile_name("NoCollision")
        print("{}: {} edge points banked, {} left open (deep drops), {} triangles".format(
            name, len(rings), skipped, len(mesh.triangles)))
    assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
