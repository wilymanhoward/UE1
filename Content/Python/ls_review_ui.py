"""PIE assertions for tutorial completion, progressive controls and unlock hints.

Run after completing the three opening lessons and opening Pause. Restores the
session's unlocked forms before the pause menu can save anything.
"""
import unreal

world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert world, 'Start PIE first'
pc=unreal.GameplayStatics.get_player_controller(world,0)
gi=unreal.GameplayStatics.get_game_instance(world)
pause=next(w for w in unreal.ObjectIterator(unreal.LSPauseMenuWidget) if w.is_in_viewport())
hud=next(w for w in unreal.ObjectIterator(unreal.LSHUDWidget) if w.is_in_viewport())
controls=next(w for w in unreal.ObjectIterator(unreal.LSControlsWidget)
              if w.get_outer() and w.get_outer().get_outer()==pause)
def tree(widget):
    return {w.get_name():w for w in unreal.ObjectIterator(unreal.Widget)
            if w.get_outer() and w.get_outer().get_outer()==widget}
controls_text=tree(controls)['ControlsText']
hw=tree(hud)
original=set(gi.get_editor_property('unlocked_forms'))

try:
    gi.set_editor_property('unlocked_forms',{unreal.SeedForm.SEED})
    pause.call_method('HandleControls',())
    text=str(controls_text.get_text())
    assert 'Roll' in text and 'Jump' in text and 'Pause' in text
    assert 'Cycle' not in text and 'Stone' not in text and 'Dandelion' not in text
    gi.unlock_form(unreal.SeedForm.STONE)
    pause.call_method('HandleControls',())
    text=str(controls_text.get_text())
    assert 'Stone' in text and 'Cycle' in text and 'Dandelion' not in text
    gi.unlock_form(unreal.SeedForm.DANDELION)
    pause.call_method('HandleControls',())
    text=str(controls_text.get_text())
    assert 'Dandelion' in text and 'Glide' in text
    pc.show_form_unlock(unreal.SeedForm.STONE,unreal.Text('Use your weight to break stone barriers.'),12)
    assert 'STONE SHELL' in str(hw['PromptTitleText'].get_text())
    assert '2 / D-PAD LEFT' in str(hw['PromptKeyText'].get_text())
    assert hw['PromptPanel'].get_render_opacity()==1.0
    assert str(hw['FormNameText'].get_text())=='Seed'
    print('UI_REVIEW_PASSED: Seed-only controls, Stone controls, Dandelion controls, visible unlock hint, HUD binding.')
finally:
    gi.set_editor_property('unlocked_forms',original)
    pause.call_method('HandleControlsClosed',())

