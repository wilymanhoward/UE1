"""Run in PIE during the opening seconds; check and capture the cinematic handoff."""
from pathlib import Path
import time
import unreal

editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world = editor.get_game_world()
assert not unreal.GameplayStatics.get_all_actors_of_class(world, unreal.GhostRacer), 'Replay ghosts should not be spawned'
output = Path(unreal.Paths.project_saved_dir()) / 'Screenshots/IntroHandoff'
output.mkdir(parents=True, exist_ok=True)
steps = [(3.0, 'Bars'), (39.3, 'Illustration'), (40.65, 'Dissolve'),
         (41.65, 'MatchedSeed'), (42.65, 'BarsOpening'), (44.0, 'Gameplay')]
grounded_z = unreal.GameplayStatics.get_player_pawn(world, 0).get_actor_location().z


def tree(owner):
    return {w.get_name(): w for w in unreal.ObjectIterator(unreal.Widget)
            if w.get_outer() and w.get_outer().get_outer() == owner}


intro = next(w for w in unreal.ObjectIterator(unreal.LSIntroWidget) if w.is_in_viewport())
motion = tree(intro)['FrontImage'].get_dynamic_material()
cue = round(motion.get_scalar_parameter_value('Cue'))
start = time.monotonic() - ([0, 4, 9, 15, 18, 23, 29, 34][cue - 1] + motion.get_scalar_parameter_value('ShotTime'))


def review(_delta):
    world = editor.get_game_world()
    if not world:
        unreal.unregister_slate_post_tick_callback(handle)
        return
    if time.monotonic() - start < steps[0][0]:
        return
    _, name = steps.pop(0)
    try:
        pc = unreal.GameplayStatics.get_player_controller(world, 0)
        intro = next((w for w in unreal.ObjectIterator(unreal.LSIntroWidget) if w.is_in_viewport()), None)
        hud = next(w for w in unreal.ObjectIterator(unreal.LSHUDWidget) if w.is_in_viewport())
        if name == 'Gameplay':
            assert intro is None, 'Intro overlay should be removed'
            assert pc.get_view_target() == unreal.GameplayStatics.get_player_pawn(world, 0), 'Restore the pawn camera'
            assert not unreal.GameplayStatics.is_game_paused(world)
            assert abs(unreal.GameplayStatics.get_player_pawn(world, 0).get_actor_location().z - grounded_z) < 5, 'Seed should already be resting on the path'
            assert hud.get_visibility() != unreal.SlateVisibility.COLLAPSED
            assert 'FIRST STEPS' in str(tree(hud)['PromptTitleText'].get_text())
            print('INTRO_HANDOFF_PASSED: bars, dissolve, matched camera, pullback, camera cleanup and tutorial.')
        else:
            assert intro, 'Cinematic should still own the screen'
            w = tree(intro)
            top = w['TopBar'].get_editor_property('render_transform').translation.y
            bottom = w['BottomBar'].get_editor_property('render_transform').translation.y
            assert abs(top + bottom) < .1
            assert hud.get_visibility() == unreal.SlateVisibility.COLLAPSED
            if name in ('Bars', 'Illustration'):
                assert abs(top) < .1 and w['PictureLayer'].get_render_opacity() == 1.0
            elif name == 'BarsOpening':
                assert top < -10 and bottom > 10
                assert w['PictureLayer'].get_render_opacity() == 0.0
            else:
                assert isinstance(pc.get_view_target(), unreal.CameraActor)
                assert 0 < w['PictureLayer'].get_render_opacity() < 1
                pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
                mesh = next(c for c in pawn.get_components_by_class(unreal.StaticMeshComponent) if c.get_name() == 'RollingVisual')
                lo, hi = mesh.get_local_bounds()
                transform = mesh.get_world_transform()
                size = unreal.WidgetLayoutLibrary.get_viewport_size(world)
                points = []
                for i in range(8):
                    local = unreal.Vector(hi.x if i & 1 else lo.x, hi.y if i & 2 else lo.y, hi.z if i & 4 else lo.z)
                    pixel = unreal.GameplayStatics.project_world_to_screen(pc, unreal.MathLibrary.transform_location(transform, local), True)
                    assert pixel is not None
                    points.append((pixel.x / size.x, pixel.y / size.y))
                center = ((min(p[0] for p in points) + max(p[0] for p in points)) / 2,
                          (min(p[1] for p in points) + max(p[1] for p in points)) / 2)
                height = max(p[1] for p in points) - min(p[1] for p in points)
                assert abs(center[0] - .5036) < .015 and abs(center[1] - .5493) < .015, (center, height)
                assert abs(height - .2330) < .02, (center, height)
                print('SEED_ALIGNMENT_PASSED', center, height)
            print('HANDOFF_SAMPLE', name, w['PictureLayer'].get_render_opacity(), top, bottom)
        unreal.SystemLibrary.execute_console_command(world, f'Shot SHOWUI filename="{(output / (name + ".png")).as_posix()}" -nosuffix')
    except Exception:
        unreal.unregister_slate_post_tick_callback(handle)
        raise
    if not steps:
        unreal.unregister_slate_post_tick_callback(handle)


handle = unreal.register_slate_post_tick_callback(review)
print('Scheduled intro handoff checks at 3, 39.3, 40.65, 41.65, 42.65 and 44 seconds.')
