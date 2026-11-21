"""Gives BP_SeedBall its rolling trail: the pack's sparkle effect, driven by ASeedBall::UpdateTrail.

Run in the editor: import ls_seed_trail; ls_seed_trail.build()
"""
import unreal


def build():
    blueprint = unreal.load_asset("/Game/Blueprint/BP_SeedBall")
    trail = unreal.load_asset("/Game/FreeParticle_SoftTofu/Niagara/NS_Sparkling")
    assert blueprint and trail
    # Compiling first gives the Blueprint the new fields from C++ before they are filled in.
    unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
    unreal.get_default_object(blueprint.generated_class()).set_editor_properties({"trail_effect": trail, "trail_rate": 50.0})
    unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
    # False saves even when not marked dirty. Editing class defaults from Python doesn't mark it.
    assert unreal.EditorAssetLibrary.save_loaded_asset(blueprint, False)
    print("Last Seed trail: BP_SeedBall now leaves sparkles while rolling")
