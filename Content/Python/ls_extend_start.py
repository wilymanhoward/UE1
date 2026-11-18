"""Extend the opening trail backward without shifting the existing level layout."""
import math
from pathlib import Path
import unreal
from ls_generate_player_meshes import Mesh, smoothstep, write_obj

NAME = 'SM_LS_WildwoodTrail_Approach'
TAG = 'LS_StartApproach'
LENGTH = 3000.0
SPAWN_DISTANCE = -1900.0


def build():
    import build_level1_wildwood as builder
    import ls_world_common
    world = builder.require_map()
    actors = builder.actors.get_all_level_actors()
    approach = next((a for a in actors if a.get_actor_label() == NAME and TAG in map(str, a.tags)), None)
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages(), 'Save existing map edits first'
    starts = [a for a in actors if isinstance(a, unreal.PlayerStart)]
    assert len(starts) == 1
    source = Path(builder.WORK) / 'SM_LS_WildwoodTrail_00.obj'
    vertices, uvs = [], []
    for line in source.read_text().splitlines():
        if line.startswith('v '):
            x, y, z = map(float, line.split()[1:])
            vertices.append((x, -y, z))
        elif line.startswith('vt '):
            u, v = map(float, line.split()[1:])
            uvs.append((u, 1-v))
    width = next(i for i, uv in enumerate(uvs) if uv[0] != uvs[0][0])
    assert width % 2 == 1 and width >= 3
    origin = vertices[width//2]
    next_row = vertices[width+width//2]
    dx, dy = next_row[0]-origin[0], next_row[1]-origin[1]
    length = math.hypot(dx, dy)
    forward = (dx/length, dy/length)
    side = (-forward[1], forward[0])
    offsets = [(v[0]-origin[0])*side[0]+(v[1]-origin[1])*side[1] for v in vertices[:width]]
    back_wall = [a for a in actors if a.get_actor_label() == 'InvisibleWall'
                 and math.hypot(a.get_actor_location().x-origin[0], a.get_actor_location().y-origin[1]) < 2]
    assert approach or len(back_wall) == 1
    ignore = [a for a in actors if not isinstance(a, unreal.Landscape)]

    def point(s, d=0):
        return origin[0]+forward[0]*s+side[0]*d, origin[1]+forward[1]*s+side[1]*d

    def ground(x, y):
        hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x,y,6500), unreal.Vector(x,y,1500),
            unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, ignore, unreal.DrawDebugTrace.NONE, True)
        assert hit and hit.to_tuple()[0], (x,y)
        return hit.to_tuple()[4].z

    rows, heights = [], []
    row_count = int(LENGTH/50)+1
    for row in range(row_count):
        s = -LENGTH + row*50
        terrain = [ground(*point(s,d)) for d in offsets]
        walk = terrain[width//2]+12
        heights.append(walk if row < row_count-1 else origin[2])
        rows.append((s,terrain))
    flat_rows = [i for i,(s,_) in enumerate(rows) if -2400 <= s <= -1400]
    level = max(z+12 for i in flat_rows for z,d in zip(rows[i][1],offsets) if abs(d) <= 200)
    for i in flat_rows: heights[i] = level
    # Raise low samples rather than cutting through the landscape to limit the rolling slope.
    for indices in (range(1,row_count), range(row_count-2,-1,-1)):
        for i in indices:
            neighbor = i-1 if indices.step > 0 else i+1
            heights[i] = max(heights[i], heights[neighbor]-8)
    assert abs(heights[-1]-origin[2]) < .01, 'Approach cannot meet the existing trail smoothly'
    mesh = Mesh()
    for row, (s,terrain) in enumerate(rows):
        for col,d in enumerate(offsets):
            x,y = point(s,d)
            crown = 0 if row in flat_rows and abs(d) <= 200 else .03*abs(d)
            z = max(heights[row]-crown,terrain[col]+8)
            # Run the grass skirt below the landscape so there is no exposed mesh lip.
            rear = 1-smoothstep(0, 620, s+LENGTH)
            shoulder = smoothstep(380, 730, abs(d))*smoothstep(0, 250, -s)
            taper = max(rear, shoulder)
            z += (terrain[col]-18-z)*taper
            if row == row_count-1: x,y,z = vertices[col]
            grass = max(uvs[col][1], 1.3*(1-smoothstep(300, 980, s+LENGTH)))
            mesh.add_vertex((x,y,z),(s/400,grass))
    for row in range(row_count-1):
        for col in range(width-1):
            a = row*width+col
            mesh.triangles += [(a,a+width,a+1),(a+1,a+width,a+width+1)]
    mesh.smooth_normals()
    write_obj(str(Path(builder.WORK)/(NAME+'.obj')),mesh)
    path = builder.import_trail_mesh(NAME)
    if approach:
        approach.static_mesh_component.set_static_mesh(unreal.load_asset(path))
        approach.static_mesh_component.set_material(0,builder.trail_material())
        assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
        return 'Refreshed the opening trail mesh with tapered grass edges'
    approach = builder.mesh_actor(path,0,0,0,'Trail',label=NAME,material=builder.trail_material())
    approach.tags = list(approach.tags)+[TAG]
    approach.static_mesh_component.set_collision_profile_name('BlockAll')
    for s in range(-int(LENGTH),0,500):
        z = heights[int((s+LENGTH)/50)]
        for d in (-390,390):
            a,b = point(s,d),point(s+500,d)
            wall = ls_world_common.invisible_wall(*a,*b,z-300,z+2600,'Walls')
            wall.tags = list(wall.tags)+[TAG]
    x,y = point(-LENGTH)
    back_wall[0].set_actor_location(unreal.Vector(x,y,heights[0]+1150),False,False)
    x,y = point(SPAWN_DISTANCE)
    z = heights[int((SPAWN_DISTANCE+LENGTH)/50)]
    starts[0].set_actor_location(unreal.Vector(x,y,z+150),False,False)
    starts[0].set_actor_rotation(unreal.Rotator(yaw=math.degrees(math.atan2(forward[1],forward[0]))),False)
    tutorial = next(a for a in actors if isinstance(a,unreal.TutorialTrigger)
                    and str(a.get_editor_property('message')).startswith('WASD to roll'))
    tx,ty = point(SPAWN_DISTANCE+350)
    tutorial.set_actor_location(unreal.Vector(tx,ty,z+200),False,False)
    story = next(a for a in actors if isinstance(a,unreal.StoryTrigger) and a.get_editor_property('play_on_start'))
    story.set_actor_location(unreal.Vector(x,y,z+600),False,False)
    cleared = 0
    for actor in actors:
        for component in actor.get_components_by_class(unreal.HierarchicalInstancedStaticMeshComponent):
            remove = []
            for i in range(component.get_instance_count()):
                p = component.get_instance_transform(i,world_space=True).translation
                px,py = p.x-origin[0],p.y-origin[1]
                along,across = px*forward[0]+py*forward[1],px*side[0]+py*side[1]
                if -LENGTH-100 < along < 0 and abs(across) < 450: remove.append(i)
            if remove:
                assert component.remove_instances(remove)
                cleared += len(remove)
    assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    print(f'Added {LENGTH/100:.0f}m of opening trail; spawn 19m behind the old entrance; cleared {cleared} foliage instances.')
    return {'spawn':[x,y,z+150], 'forward':forward, 'origin':origin, 'length':LENGTH}


if __name__ == '__main__': build()
