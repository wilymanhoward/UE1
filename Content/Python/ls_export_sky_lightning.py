"""Bake the supplied Blender geometry-node lightning into three portable OBJ meshes.

Run Blender in background with --disable-autoexec, the source .blend, and --python this file.
The source project is only read; its evaluated geometry is exported in Unreal centimetres.
"""
from pathlib import Path
import sys
import bpy

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from ls_generate_player_meshes import Mesh,write_obj

source=bpy.data.objects.get('Lightning')
assert source and source.type=='CURVE', 'Expected the supplied Lightning curve.'
group=next(m.node_group for m in source.modifiers if m.type=='NODES')
noise=next(n for n in group.nodes if n.bl_idname=='ShaderNodeTexNoise')
output=HERE.parent/'LastSeed/SourceMeshes'
output.mkdir(parents=True,exist_ok=True)
for index,w in enumerate((2.0,3.7,5.4),1):
    noise.inputs['W'].default_value=w
    source.update_tag()
    bpy.context.view_layer.update()
    evaluated=source.evaluated_get(bpy.context.evaluated_depsgraph_get())
    geometry=evaluated.to_mesh()
    geometry.calc_loop_triangles()
    points=[source.matrix_world @ v.co for v in geometry.vertices]
    low=[min(v[i] for v in points) for i in range(3)]
    high=[max(v[i] for v in points) for i in range(3)]
    scale=100/(high[2]-low[2])
    mesh=Mesh()
    mesh.points=[((v.x-(low[0]+high[0])/2)*scale,-(v.y-(low[1]+high[1])/2)*scale,(v.z-low[2])*scale) for v in points]
    mesh.uvs=[(0,0)]*len(points)
    mesh.triangles=[tuple(t.vertices) for t in geometry.loop_triangles]
    mesh.smooth_normals()
    assert 0< len(mesh.triangles)<30000
    assert abs(max(v[2] for v in mesh.points)-100)<.01
    name=f'SM_LS_SkyLightning_{index:02d}'
    write_obj(str(output/(name+'.obj')),mesh)
    print('EXPORTED_LIGHTNING',name,len(mesh.points),len(mesh.triangles))
    evaluated.to_mesh_clear()
