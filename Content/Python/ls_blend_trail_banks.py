"""Blend the Wildwood trail banks into the live landscape."""
from pathlib import Path
import shutil
import unreal
from ls_generate_player_meshes import Mesh, smoothstep, write_obj

NAMES = ('SM_LS_WildwoodTrail_00', 'SM_LS_WildwoodTrail_01', 'SM_LS_WildwoodTrail_02')


def blend_source(name):
    import build_level1_wildwood as builder

    world = builder.require_map()
    work = Path(builder.WORK)
    vertices, uvs = [], []
    for line in (work / (name + '.obj')).read_text().splitlines():
        if line.startswith('v '):
            x, y, z = map(float, line.split()[1:])
            vertices.append((x, -y, z))
        elif line.startswith('vt '):
            u, v = map(float, line.split()[1:])
            uvs.append((u, 1-v))
    width = next(i for i, uv in enumerate(uvs) if uv[0] != uvs[0][0])
    assert width == 17 and len(vertices) == len(uvs) and len(vertices) % width == 0

    ignore = [a for a in builder.actors.get_all_level_actors() if not isinstance(a, unreal.LandscapeProxy)]

    def terrain_height(x, y):
        hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x,y,6500), unreal.Vector(x,y,500),
            unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, ignore, unreal.DrawDebugTrace.NONE, True)
        assert hit and hit.to_tuple()[0], (name,x,y)
        return hit.to_tuple()[4].z

    mesh = Mesh()
    row_width = 0
    for start in range(0, len(vertices), width):
        row = vertices[start:start+width]
        u = uvs[start][0]
        # Preserve the opening approach's shared seam and ease the new bank in past it.
        strength = smoothstep(0, 1.25, u) if name == NAMES[0] else 1
        row_start = len(mesh.points)
        for col, a in enumerate(row):
            v = uvs[start+col][1]
            steps = 1
            if col+1 < width and min(v, uvs[start+col+1][1]) >= .99999:
                steps = 4
            for step in range(steps):
                t = step/steps
                x, y, z = a
                across = v
                if step:
                    b = row[col+1]
                    x,y,z = (lo+(hi-lo)*t for lo,hi in zip(a,b))
                    across += (uvs[start+col+1][1]-v)*t
                blend = strength * smoothstep(1, 2.25, across)
                if name == NAMES[1]:
                    # Settle the shoulders at the gorge without lowering the center of the launch ledge.
                    at_crossing = 1 - smoothstep(0, 1.5, uvs[-1][0] - u)
                    blend = max(blend, at_crossing * smoothstep(.28, .90, across))
                elif name == NAMES[2]:
                    # Keep the middle of the log landing and the shared row with Trail 03.
                    at_landing = 1 - smoothstep(0, 1.5, u - uvs[0][0])
                    blend = max(smoothstep(.85, 1.85, across), at_landing * smoothstep(.35, 1.05, across))
                    blend *= smoothstep(0, .85, uvs[-1][0] - u)
                if blend > 0:
                    ground = terrain_height(x, y)
                    z += (ground - 20 - z) * blend
                grass = across
                if name == NAMES[1]:
                    fade = 1 - smoothstep(0, .52, uvs[-1][0] - u)
                    grass = across + max(0, 1.12 - across) * fade
                elif name == NAMES[2]:
                    fade = 1 - smoothstep(0, .5, u - uvs[0][0])
                    grass = across + max(0, 1.12 - across) * fade
                mesh.add_vertex((x,y,z), (u,grass))
        new_width = len(mesh.points)-row_start
        assert not row_width or new_width == row_width
        row_width = new_width
        if row_start:
            for col in range(row_width-1):
                a = row_start-row_width+col
                mesh.triangles += [(a,a+row_width,a+1),(a+1,a+row_width,a+row_width+1)]
    if name in (NAMES[1], NAMES[2]):
        at_start = name == NAMES[2]
        end = mesh.points[:row_width] if at_start else mesh.points[-row_width:]
        mid = row_width // 2
        inner = mesh.points[row_width+mid] if at_start else mesh.points[-2*row_width+mid]
        dx = end[mid][0] - inner[0]
        dy = end[mid][1] - inner[1]
        forward = (dx*dx + dy*dy)**.5
        # Follow the actual bank profile and ease out the lip's remaining height over it.
        lip_lift = [z - terrain_height(x, y) for x, y, z in end]
        blend_length = 125
        for distance in (25, 50, 75, 100, blend_length):
            start = len(mesh.points)
            blend = smoothstep(0, blend_length, distance)
            for (x, y, _), lift in zip(end, lip_lift):
                x += distance * dx / forward
                y += distance * dy / forward
                z = terrain_height(x, y) + lift * (1 - blend) - 24 * blend
                u = uvs[0][0]-distance/400 if at_start else uvs[-1][0]+distance/400
                mesh.add_vertex((x,y,z),(u, 1.12))
            for col in range(row_width-1):
                a = col if at_start and distance == 25 else start-row_width+col
                b = start+col
                if at_start:
                    mesh.triangles += [(b,a,b+1),(b+1,a,a+1)]
                else:
                    mesh.triangles += [(a,b,a+1),(a+1,b,b+1)]
    mesh.smooth_normals()
    output = work / 'BlendedBanks' / (name + '.obj')
    output.parent.mkdir(exist_ok=True)
    write_obj(str(output), mesh)
    return output


def build():
    import build_level1_wildwood as builder

    builder.require_map()
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    sources = {name: blend_source(name) for name in NAMES}
    backup = Path(unreal.Paths.project_saved_dir()) / 'BeforeTrailBankBlend'
    backup.mkdir(exist_ok=True)
    content = Path(unreal.Paths.project_content_dir()) / 'LastSeed'
    for file in [content/'Maps/L_Level1_Wildwood.umap',
                 *(content/'Generated/WildwoodTrail'/(name+'.uasset') for name in NAMES)]:
        if not (backup/file.name).exists(): shutil.copy2(file, backup/file.name)
    for name, source in sources.items():
        builder.import_trail_mesh(name, source)
    assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    print('Blended both grass shoulders along the first Wildwood trail run.')
