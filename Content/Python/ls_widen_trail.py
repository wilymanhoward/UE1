"""Moves Wildwood's soft trail-edge walls further out, so the Seed can roll onto the shoulder.

Each wall's two ends move straight out from the trail's centre line by up to WIDEN cm. The push eases to nothing near
anything that spans the trail from wall to wall (gates, the cracked wall, blocks, logs, platforms) and near kill
volumes, so no puzzle or drop can be rolled around. Moving ends, not whole walls, keeps neighbouring walls joined.
Run in the editor: import ls_widen_trail; ls_widen_trail.build()
"""
import math

import unreal

WIDEN = 200.0
KEEP = 600.0  # Within this of a protected thing, walls stay where they are.
RAMP = 800.0  # Then ease out to the full WIDEN over this distance.
SPANNING = {"block", "fallen_log", "cracked_wall", "gate", "log_bridge", "tilting_log", "crumbling", "moving", "pillar",
            "push_block", "lever", "tower", "wind"}
DONE = "LS_TrailWidened"


def shift_at(x, y, protected):
    gap = min((math.hypot(x - px, y - py) - reach for px, py, reach in protected), default=1e9)
    t = min(max((gap - KEEP) / RAMP, 0.0), 1.0)
    return WIDEN * t * t * (3.0 - 2.0 * t)


def outward(x, y, trail):
    px, py = min(trail, key=lambda p: (p[0] - x) ** 2 + (p[1] - y) ** 2)[:2]
    length = math.hypot(x - px, y - py) or 1.0
    return (x - px) / length, (y - py) / length


def ends(wall):
    centre, yaw, length = wall.get_actor_location(), math.radians(wall.get_actor_rotation().yaw), wall.get_actor_scale3d().x * 100.0
    dx, dy = math.cos(yaw) * length / 2.0, math.sin(yaw) * length / 2.0
    return (centre.x - dx, centre.y - dy), (centre.x + dx, centre.y + dy)


def joined(walls):
    points = [p for wall in walls for p in ends(wall)]
    return sum(1 for i, p in enumerate(points) if any(math.dist(p, q) < 40.0 for j, q in enumerate(points) if j != i))


def build(save=True):
    import build_level1_wildwood as builder

    builder.require_map()
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    walls = [a for a in actors if a.get_actor_label() == "InvisibleWall" and "LS_SoftTrailEdge" in map(str, a.tags)]
    assert walls and not any(DONE in map(str, w.tags) for w in walls), "Trail walls already widened"
    plan = builder.load_plan()
    trail = plan["trail"]
    protected = [(e["x"], e["y"], max(e.get("length", 0.0), e.get("width", 0.0)) / 2.0) for e in plan["actors"]
                 if e["kind"] in SPANNING]
    for kill in actors:
        if isinstance(kill, unreal.KillVolume):
            origin, extent, _ = unreal.SystemLibrary.get_component_bounds(kill.get_component_by_class(unreal.BoxComponent))
            if max(extent.x, extent.y) < 20000.0:  # Not the catch-all volume under the whole map.
                protected.append((origin.x, origin.y, math.hypot(extent.x, extent.y)))

    before = joined(walls)
    moved = 0
    for wall in walls:
        new = []
        for x, y in ends(wall):
            ox, oy = outward(x, y, trail)
            push = shift_at(x, y, protected)
            new.append((x + ox * push, y + oy * push))
        (ax, ay), (bx, by) = new
        if math.hypot(ax - bx, ay - by) < 1.0:
            continue
        moved += any(shift_at(x, y, protected) > 1.0 for x, y in ends(wall))
        wall.modify()
        z = wall.get_actor_location().z
        wall.set_actor_location(unreal.Vector((ax + bx) / 2.0, (ay + by) / 2.0, z), False, False)
        wall.set_actor_rotation(unreal.Rotator(yaw=math.degrees(math.atan2(by - ay, bx - ax))), False)
        scale = wall.get_actor_scale3d()
        scale.x = math.hypot(bx - ax, by - ay) / 100.0
        wall.set_actor_scale3d(scale)
        wall.tags = list(wall.tags) + [DONE]
    after = joined(walls)
    print("Widened trail walls: moved {} of {}, joined ends {} before, {} after".format(moved, len(walls), before, after))
    assert after >= before, "A wall end lost its neighbour"
    if save:
        assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
