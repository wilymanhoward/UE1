"""Opening boundary width, shared by the planner and the saved-map migration."""
import math


def opening_padding(distance):
    alpha = min(1, max(0, (distance - 1000) / 2000))
    return 200 * (1 - alpha * alpha * (3 - 2 * alpha))


def build():
    import shutil
    from pathlib import Path
    import unreal
    import build_level1_wildwood as builder
    from ls_extend_start import LENGTH, TAG

    builder.require_map()
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    actors = builder.actors.get_all_level_actors()
    walls = [a for a in actors if a.get_actor_label() == 'InvisibleWall' and 'LS_SoftTrailEdge' in map(str, a.tags)]
    approach = [a for a in walls if TAG in map(str, a.tags)]
    assert len(approach) == 12
    start = next(a for a in actors if isinstance(a, unreal.PlayerStart))
    forward = start.get_actor_forward_vector()
    right = unreal.Vector(-forward.y, forward.x, 0)
    origin = unreal.Vector(-23000, 17200, 0)
    rear = min(walls, key=lambda a: (a.get_actor_location() - (origin - forward * LENGTH)).length2d())
    assert (rear.get_actor_location() - (origin - forward * LENGTH)).length2d() < 3
    assert rear.get_actor_scale3d().x < 8, 'Opening boundary already widened'

    # The original plan stores paired endpoints at every 500 cm of the opening trail.
    changes = []
    for index, (x0,y0,x1,y1,_,_) in enumerate(builder.load_plan()['walls'][:12]):
        start_distance = (index // 2) * 500
        midpoint = unreal.Vector((x0+x1)/2, (y0+y1)/2, 0)
        wall = min(walls, key=lambda a: (a.get_actor_location()-midpoint).length2d())
        assert (wall.get_actor_location()-midpoint).length2d() < 2, f'Missing opening wall {index}'
        changes.append((wall, [unreal.Vector(x0,y0,0), unreal.Vector(x1,y1,0)], start_distance))
    assert len({wall for wall, _, _ in changes}) == 12

    backup = Path(unreal.Paths.project_saved_dir()) / 'BeforeOpeningWidth'
    backup.mkdir(exist_ok=True)
    source = Path(unreal.Paths.project_content_dir()) / 'LastSeed/Maps/L_Level1_Wildwood.umap'
    if not (backup / source.name).exists(): shutil.copy2(source, backup / source.name)

    for wall in approach:
        offset = wall.get_actor_location() - origin
        sign = 1 if offset.x * right.x + offset.y * right.y > 0 else -1
        wall.set_actor_location(wall.get_actor_location() + right * (sign * opening_padding(0)), False, False)
    for index, (wall, points, start_distance) in enumerate(changes):
        widened = []
        for endpoint, point in enumerate(points):
            offset = point - changes[index ^ 1][1][endpoint]
            widened.append(point + offset * (opening_padding(start_distance + endpoint * 500) / offset.length()))
        a,b = widened
        delta = b-a
        center = (a+b)*.5
        center.z = wall.get_actor_location().z
        wall.set_actor_location(center, False, False)
        wall.set_actor_rotation(unreal.Rotator(yaw=math.degrees(math.atan2(delta.y,delta.x))), False)
        scale = wall.get_actor_scale3d()
        scale.x = delta.length()/100
        wall.set_actor_scale3d(scale)
    scale = rear.get_actor_scale3d()
    scale.x += 2 * opening_padding(0) / 100
    rear.set_actor_scale3d(scale)
    assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    print('Widened 24 opening side walls and the rear boundary')
