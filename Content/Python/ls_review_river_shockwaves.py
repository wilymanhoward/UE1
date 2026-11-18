"""Fresh PIE: input-driven jumps, grounded/curved hits, screams, timing and respawn reset."""
import json
from pathlib import Path
import unreal

ed=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world=ed.get_game_world()
assert world, 'Start fresh PIE with background throttling disabled before running this review.'
p=unreal.GameplayStatics.get_player_pawn(world,0)
pc=unreal.GameplayStatics.get_player_controller(world,0)
for widget in unreal.ObjectIterator(unreal.LSIntroWidget):
    if widget.is_in_viewport(): widget.call_method('Finish',())
story=next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.StoryTrigger) if a.get_actor_label()=='RiverbankWitchAmbush')
story.set_actor_enable_collision(False)
storm=story.get_editor_property('after_cutscene_curse')
trees=list(storm.get_editor_property('curse_trees'))
body=p.get_editor_property('ball_mesh')
jump=next(a for a in unreal.ObjectIterator(unreal.InputAction) if a.get_outer()==pc and a.get_name()=='InputAction_2')
inputs=next(a for a in unreal.ObjectIterator(unreal.EnhancedInputLocalPlayerSubsystem) if isinstance(a.get_outer(),unreal.LocalPlayer))
p.try_switch_form(unreal.SeedForm.SEED)
p.set_actor_location(unreal.Vector(15300,-2115,2450),False,True)
body.set_physics_linear_velocity(unreal.Vector())
body.set_physics_angular_velocity_in_radians(unreal.Vector())
p.set_checkpoint(unreal.Vector(15300,-2115,2450))
route=list(storm.get_editor_property('chase_points'))
state={'phase':'settle','start':unreal.GameplayStatics.get_time_seconds(world),'visible':False,'attacks':[],'jumped':False,'cleared':0,'max_z':0}
report=Path(unreal.Paths.project_saved_dir())/'ShockwaveReview.json'

def check(_):
    if not ed.get_game_world():
        unreal.unregister_slate_post_tick_callback(handle)
        return
    try:
        now=unreal.GameplayStatics.get_time_seconds(world)
        assert now-state['start']<25, state
        pos=p.get_actor_location()
        state['max_z']=max(state['max_z'],pos.z)
        if not p.is_dead():
            vel=body.get_physics_linear_velocity()
            body.set_physics_linear_velocity(unreal.Vector(0,0,vel.z))
            body.set_physics_angular_velocity_in_radians(unreal.Vector())
        if state['phase']=='settle':
            if p.is_grounded():
                state['ground_z']=pos.z
                storm.start_rising(p)
                state.update(phase='waves',started=now)
            return
        visible=not storm.get_editor_property('hidden')
        if state['phase']=='waves':
            if visible and not state['visible']:
                assert storm.get_editor_property('attack_audio').is_playing()
                w=storm.get_actor_location()
                t=(w.x-route[0].x)/(route[1].x-route[0].x)
                height=w.z-(route[0].z+(route[1].z-route[0].z)*t)
                state['attacks'].append({'time':now,'height':round(height)})
                if len(state['attacks'])==1: assert now-state['started']>=1.9
                else:
                    a,b=state['attacks'][-2:]
                    assert 2.5<b['time']-a['time']<4.05, state
                    assert a['height']!=b['height'], state
                state['jumped']=False
            if visible:
                w=storm.get_actor_location()
                gap=pos.x-w.x
                if len(state['attacks'])<=3 and 350<gap<650 and not state['jumped']:
                    inputs.inject_input_vector_for_action(jump,unreal.Vector(1,0,0),[],[])
                    state['jumped']=True
                if gap < -200 and state['cleared']<len(state['attacks']) and len(state['attacks'])<=3:
                    assert not p.is_dead(),state
                    assert state['jumped'],state
                    assert state['max_z']>state['ground_z']+130,state
                    state['cleared']+=1
            if p.is_dead():
                assert state['cleared']==3,state
                assert len(state['attacks'])==4,state
                assert any(t.is_cursed() for t in trees),state
                state.update(phase='respawn',died=now)
        elif state['phase']=='respawn' and not p.is_dead():
            assert storm.get_editor_property('hidden')
            assert not any(t.is_cursed() for t in trees)
            state.update(phase='curve_wait',reset=now,visible=False)
            storm.set_editor_properties({'rise_speed':0.0,'start_delay':0.0,
                'chase_points':[unreal.Vector(15300,-2115,2350),unreal.Vector(17000,-2115,2350)]})
            body.set_simulate_physics(False)
            p.set_actor_tick_enabled(False)
            p.set_actor_enable_collision(False)
            p.set_actor_location(unreal.Vector(15300,-1115,2800),False,True)
            storm.start_rising(p)
        elif state['phase']=='curve_wait' and visible:
            assert not p.is_dead()
            p.set_actor_location(storm.get_actor_location()+unreal.Vector(0,1000,0),False,True)
            state.update(phase='curve_safe',at=now)
        elif state['phase']=='curve_safe' and now-state['at']>.12:
            assert not p.is_dead(), 'The old straight hitbox still hits the empty space ahead of the arc.'
            state['curve_hole_safe']=True
            bend=storm.get_editor_property('shockwave_bend')
            p.set_actor_location(storm.get_actor_location()+unreal.Vector(-bend*(1000/1400)**2,1000,0),False,True)
            state.update(phase='curve_hit',at=now)
        elif state['phase']=='curve_hit' and now-state['at']>.12:
            assert p.is_dead(), 'The visible curved wing must hit the seed.'
            p.set_actor_tick_enabled(True)
            state.update(phase='passed',curve_hit=True,visible=False)
            report.write_text(json.dumps(state,indent=2))
            print('SHOCKWAVE_REVIEW_PASSED',state)
            unreal.unregister_slate_post_tick_callback(handle)
        state['visible']=visible
    except Exception as exc:
        state['error']=str(exc)
        report.write_text(json.dumps(state,indent=2))
        unreal.unregister_slate_post_tick_callback(handle)
        raise

handle=unreal.register_slate_post_tick_callback(check)
print('Shockwave review running: three actual input jumps, fourth attack grounded, then death reset.')
