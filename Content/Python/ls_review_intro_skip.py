"""Install in PIE, then press the intro's Skip button; verify a continuous fade and cleanup."""
import unreal

state = {'started': False, 'opacity': 1.0, 'top': 0.0}


def review(_delta):
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    if not world:
        unreal.unregister_slate_post_tick_callback(handle)
        return
    try:
        intro = next((w for w in unreal.ObjectIterator(unreal.LSIntroWidget) if w.is_in_viewport()), None)
        if intro:
            w = {x.get_name(): x for x in unreal.ObjectIterator(unreal.Widget)
                 if x.get_outer() and x.get_outer().get_outer() == intro}
            if w['SkipButton'].get_is_enabled():
                return
            state['started'] = True
            opacity = w['PictureLayer'].get_render_opacity()
            top = w['TopBar'].get_editor_property('render_transform').translation.y
            assert opacity <= state['opacity'] + .001, 'Skip must not brighten the picture'
            assert top <= state['top'] + .001, 'Bars must keep moving outward'
            state.update(opacity=opacity, top=top)
        else:
            assert state['started']
            pc = unreal.GameplayStatics.get_player_controller(world, 0)
            assert pc.get_view_target() == unreal.GameplayStatics.get_player_pawn(world, 0)
            assert not unreal.GameplayStatics.is_game_paused(world)
            print('INTRO_SKIP_PASSED: monotonic dissolve, bars exiting, gameplay restored.')
            unreal.unregister_slate_post_tick_callback(handle)
    except Exception:
        unreal.unregister_slate_post_tick_callback(handle)
        raise


handle = unreal.register_slate_post_tick_callback(review)
print('Ready for Skip test.')
