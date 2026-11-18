"""Import bolts baked from the supplied Blender generator and assign the existing weather driver."""
from pathlib import Path
import unreal

FOLDER='/Game/LastSeed/Weather'


def configure(driver):
    assets=unreal.AssetToolsHelpers.get_asset_tools()
    path=FOLDER+'/M_LS_SkyLightning'
    mat=unreal.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else None
    if mat is None:
        mat=assets.create_asset('M_LS_SkyLightning',FOLDER,unreal.Material,unreal.MaterialFactoryNew())
    mat.set_editor_properties({'shading_model':unreal.MaterialShadingModel.MSM_UNLIT,
        'blend_mode':unreal.BlendMode.BLEND_ADDITIVE,'two_sided':True,'use_translucency_vertex_fog':False})
    edit=unreal.MaterialEditingLibrary
    edit.delete_all_material_expressions(mat)
    colour=edit.create_material_expression(mat,unreal.MaterialExpressionConstant3Vector,-400,0)
    colour.set_editor_property('constant',unreal.LinearColor(.45,.62,1))
    power=edit.create_material_expression(mat,unreal.MaterialExpressionScalarParameter,-400,160)
    power.set_editor_properties({'parameter_name':'Brightness','default_value':12.0})
    multiply=edit.create_material_expression(mat,unreal.MaterialExpressionMultiply,-150,0)
    assert edit.connect_material_expressions(colour,'',multiply,'A')
    assert edit.connect_material_expressions(power,'',multiply,'B')
    assert edit.connect_material_property(multiply,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    edit.recompile_material(mat)
    assert unreal.EditorAssetLibrary.save_loaded_asset(mat,False)
    meshes=[]
    for i in range(1,4):
        name=f'SM_LS_SkyLightning_{i:02d}'
        path=FOLDER+'/'+name
        if not unreal.EditorAssetLibrary.does_asset_exist(path):
            source=Path(unreal.Paths.project_content_dir())/'LastSeed/SourceMeshes'/(name+'.obj')
            assert source.exists(), 'Bake the Blender generator with ls_export_sky_lightning.py first.'
            task=unreal.AssetImportTask()
            task.filename=str(source)
            task.destination_path=FOLDER
            task.destination_name=name
            task.automated=True
            task.save=True
            assets.import_asset_tasks([task])
            assert task.imported_object_paths
        mesh=unreal.load_asset(path)
        assert isinstance(mesh,unreal.StaticMesh)
        assert abs(mesh.get_bounds().box_extent.z-50)<.1
        nanite=mesh.get_editor_property('nanite_settings')
        nanite.set_editor_property('enabled',False)
        unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).set_nanite_settings(mesh,nanite,True)
        mesh.set_material(0,mat)
        assert unreal.EditorAssetLibrary.save_loaded_asset(mesh,False)
        meshes.append(mesh)
    driver.set_editor_property('lightning_meshes',meshes)
    return meshes


def build():
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    driver=next(a for a in actors if isinstance(a,unreal.RestorationDriver))
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    configure(driver)
    assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    print('Saved three Blender lightning variations on',driver.get_actor_label())
