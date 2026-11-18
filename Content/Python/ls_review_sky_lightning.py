"""Fresh PIE: inspect two real strikes, delayed thunder, and clear skies after restoration.

Pauses on the first strike for a screenshot; resume PIE to finish the assertions.
"""
import json
from pathlib import Path
import unreal

editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world=editor.get_game_world()
assert world, 'Start a fresh PIE session with background throttling disabled.'
for intro in unreal.ObjectIterator(unreal.LSIntroWidget):
    if intro.is_in_viewport():intro.call_method('Finish',())
driver=next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.RestorationDriver))
bolt=driver.get_editor_property('lightning_bolt')
thunder=driver.get_editor_property('distant_thunder')
restoration=next(s for s in unreal.ObjectIterator(unreal.RestorationSubsystem) if s.get_outer()==world)
assert len(driver.get_editor_property('lightning_meshes'))==3 and thunder
assert not bolt.is_visible() and restoration.get_restoration()==0
report=Path(unreal.Paths.project_saved_dir())/'SkyLightningReview.json'
state={'phase':'first','start':unreal.GameplayStatics.get_time_seconds(world),'thunder':False}

def save():report.write_text(json.dumps(state,indent=2))

def check(_):
    if not editor.get_game_world():unreal.unregister_slate_post_tick_callback(handle);return
    if unreal.GameplayStatics.is_game_paused(world):return
    try:
        now=unreal.GameplayStatics.get_time_seconds(world)
        assert now-state['start']<65,state
        if state['phase']=='first' and bolt.is_visible():
            assert 4.3<now<4.8,now
            state.update(phase='flash',first=now,mesh=bolt.static_mesh.get_name())
            assert bolt.get_world_location().z>unreal.GameplayStatics.get_player_pawn(world,0).get_actor_location().z+5000
            save()
            unreal.GameplayStatics.set_game_paused(world,True)
            print('SKY_LIGHTNING_FROZEN: first real strike; resume PIE after the screenshot.')
        elif state['phase']=='flash':
            if any(a.get_editor_property('sound')==thunder and a.is_playing() for a in unreal.ObjectIterator(unreal.AudioComponent)):
                assert now-state['first']>.45
                state['thunder']=True
            if not bolt.is_visible():
                assert .55<now-state['first']<.85,state
                assert state['thunder'], 'Strike did not produce delayed thunder.'
                state['phase']='second'
                save()
        elif state['phase']=='second' and bolt.is_visible():
            assert 11.8<now-state['first']<22.2,state
            state.update(phase='restoring',second=now)
            for _ in range(restoration.get_notes_total()-restoration.get_notes_collected()):
                restoration.report_note_collected(unreal.Vector())
            assert restoration.get_restoration()==1
            save()
        elif state['phase']=='restoring':
            if now-state['second']>3:
                assert not bolt.is_visible(), 'Lightning continued after restoration.'
                assert not any(a.get_editor_property('sound')==thunder and a.is_playing() for a in unreal.ObjectIterator(unreal.AudioComponent)), 'Thunder continued after restoration.'
            if now-state['second']>24:
                state.update(phase='passed',finished=now)
                save()
                print('SKY_LIGHTNING_PASSED',state)
                unreal.unregister_slate_post_tick_callback(handle)
    except Exception as exc:
        state['error']=str(exc)
        save()
        unreal.unregister_slate_post_tick_callback(handle)
        raise

handle=unreal.register_slate_post_tick_callback(check)
print('Sky lightning review running; first strike will pause for visual inspection.')
