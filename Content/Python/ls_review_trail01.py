"""PIE traversal check using the real Seed inputs and physics, without teleporting past obstacles.

Run with MODE='opening', 'main', 'log_reward', or 'hill_reward' through runpy.run_path.
Each check teleports once to its start, then drives Enhanced Input along the route.
"""
from pathlib import Path
import json
import math
import unreal

mode=globals().get('MODE','main')
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world=editor.get_game_world()
assert world
for intro in unreal.ObjectIterator(unreal.LSIntroWidget):
    if intro.is_in_viewport(): intro.call_method('Finish',())
pc=unreal.GameplayStatics.get_player_controller(world,0)
pawn=unreal.GameplayStatics.get_player_pawn(world,0)
assert pawn.get_current_form()==unreal.SeedForm.SEED
assert not unreal.GameplayStatics.get_all_actors_of_class(world,unreal.GhostRacer), 'Replay ghosts should not be spawned'
actions={a.get_name():a for a in unreal.ObjectIterator(unreal.InputAction) if a.get_outer()==pc}
subsystem=next(s for s in unreal.ObjectIterator(unreal.EnhancedInputLocalPlayerSubsystem)
               if isinstance(s.get_outer(),unreal.LocalPlayer))
body=next(c for c in pawn.get_components_by_class(unreal.StaticMeshComponent) if c.get_name()=='BallMesh')
trail=json.loads((Path(unreal.Paths.project_saved_dir())/'LS/plan.json').read_text())['trail']


def point(s,d=0):
    i=min(int(s//200),len(trail)-2);a,b=trail[i],trail[i+1];t=(s-i*200)/200
    yaw=math.atan2(b[1]-a[1],b[0]-a[0])
    return ((1-t)*a[0]+t*b[0]-d*math.sin(yaw),(1-t)*a[1]+t*b[1]+d*math.cos(yaw),
            (1-t)*a[2]+t*b[2]-.03*abs(d),yaw)


def project(loc):
    best=(1e30,0,0)
    for i in (range(0,35) if mode=='opening' else range(74,134)):
        a,b=trail[i],trail[i+1];dx,dy=b[0]-a[0],b[1]-a[1]
        t=max(0,min(1,((loc.x-a[0])*dx+(loc.y-a[1])*dy)/(dx*dx+dy*dy)))
        x,y=a[0]+t*dx,a[1]+t*dy;distance=(loc.x-x)**2+(loc.y-y)**2
        if distance<best[0]: best=(distance,i*200+t*200,(-(loc.x-x)*dy+(loc.y-y)*dx)/math.hypot(dx,dy))
    return best[1],best[2]


if mode=='opening':
    start,end,speed=0,5000,350
    line=[(0,0),(1700,150),(2300,150),(3000,0),(3450,-150),(4050,-150),(4400,150),(5000,0)]
    jumps=[2700]
elif mode=='main':
    start,end,speed=15500,26400,420
    line=[(15500,0),(17000,0),(17500,200),(17850,200),(18450,-200),(19000,-200),
          (19300,0),(19900,0),(20500,-245),(21450,-245),(22200,245),(22750,245),
          (23100,-230),(24750,-230),(25100,0),(26400,0)]
    jumps=[15950,19200,25550]
elif mode=='log_reward':
    start,end,speed=20500,21750,350
    line=[(20500,160),(21750,160)];jumps=[20900]
else:
    assert mode=='hill_reward'
    start,end,speed=23000,25100,250
    line=[(23000,180),(25100,180)];jumps=[23350,23800,24250]


def side_at(s):
    for (a,da),(b,db) in zip(line,line[1:]):
        if a<=s<=b:return da+(db-da)*(s-a)/(b-a)
    return line[0][1] if s<line[0][0] else line[-1][1]


x,y,z,yaw=point(start,side_at(start))
pawn.set_actor_location(unreal.Vector(x,y,z+53),False,True)
body.set_physics_linear_velocity(unreal.Vector(0,0,0));body.set_physics_angular_velocity_in_radians(unreal.Vector(0,0,0))
pc.set_control_rotation(unreal.Rotator(pitch=-20,yaw=math.degrees(yaw),roll=0))
began=unreal.GameplayStatics.get_time_seconds(world)
state={'max_s':start,'last_progress':0,'samples':[],'jumped':[],'last_jump':-10,'captured':False}
output=Path(unreal.Paths.project_saved_dir())/'Screenshots/Trail01';output.mkdir(parents=True,exist_ok=True)


def finish(success,reason):
    if success and mode in ('log_reward','hill_reward'):
        label='Trail01_OptionalPetal_'+('1' if mode=='log_reward' else '2')
        if any(a.get_actor_label()==label for a in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.GoldenPetal)):
            success=False;reason='reached the exit but missed the optional reward'
    if success and mode=='opening':
        target=point(2000,150)
        if any(math.hypot(a.get_actor_location().x-target[0],a.get_actor_location().y-target[1])<150
               for a in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.LifeNote)):
            success=False;reason='first note was not collected without a bounce mushroom'
    subsystem.inject_input_vector_for_action(actions['InputAction_0'],unreal.Vector(0,0,0),[],[])
    body.set_physics_linear_velocity(unreal.Vector(0,0,0))
    body.set_physics_angular_velocity_in_radians(unreal.Vector(0,0,0))
    unreal.unregister_slate_post_tick_callback(handle)
    report=dict(mode=mode,success=success,reason=reason,**state)
    (output/(mode+'.json')).write_text(json.dumps(report,indent=2))
    unreal.SystemLibrary.execute_console_command(world,f'Shot SHOWUI filename="{(output/(mode+".png")).as_posix()}" -nosuffix')
    assert success, str(report)[:700]
    print('TRAIL01_TRAVERSAL_PASSED',mode,reason,'jumps',state['jumped'])


def drive(delta):
    if not editor.get_game_world(): unreal.unregister_slate_post_tick_callback(handle);return
    elapsed=unreal.GameplayStatics.get_time_seconds(world)-began
    loc=pawn.get_actor_location();s,side=project(loc)
    if s>state['max_s']+20:state['max_s']=s;state['last_progress']=elapsed
    if not state['samples'] or elapsed-state['samples'][-1]['time']>.2:
        state['samples'].append(dict(time=round(elapsed,2),s=round(s),side=round(side),z=round(loc.z)))
    if s>=end:finish(True,'reached the end in Seed form');return
    if pawn.is_dead() or loc.z<point(s)[2]-500:finish(False,'fell or died');return
    if elapsed>60 or elapsed-state['last_progress']>8:finish(False,'no forward progress');return
    if abs(side)>440:finish(False,'left the trail corridor');return
    target=point(s+260,side_at(s+260));dx,dy=target[0]-loc.x,target[1]-loc.y
    length=max(math.hypot(dx,dy),1);velocity=pawn.get_velocity()
    ax,ay=(dx/length*speed-velocity.x)/350,(dy/length*speed-velocity.y)/350
    magnitude=max(1,math.hypot(ax,ay));ax/=magnitude;ay/=magnitude
    yaw=point(s)[3];pc.set_control_rotation(unreal.Rotator(pitch=-20,yaw=math.degrees(yaw),roll=0))
    subsystem.inject_input_vector_for_action(actions['InputAction_0'],unreal.Vector(-ax*math.sin(yaw)+ay*math.cos(yaw),ax*math.cos(yaw)+ay*math.sin(yaw),0),[],[])
    subsystem.inject_input_vector_for_action(actions['InputAction_1'],unreal.Vector(.001,0,0),[],[])
    jump=False
    for mark in jumps:
        if mark not in state['jumped'] and mark<=s<mark+300 and pawn.is_grounded() and elapsed-state['last_jump']>1.0:
            state['jumped'].append(mark);state['last_jump']=elapsed;jump=True;break
    subsystem.inject_input_vector_for_action(actions['InputAction_2'],unreal.Vector(1 if jump else 0,0,0),[],[])
    if not state['captured'] and s>(start+end)/2:
        state['captured']=True
        unreal.SystemLibrary.execute_console_command(world,f'Shot SHOWUI filename="{(output/(mode+"_mid.png")).as_posix()}" -nosuffix')


handle=unreal.register_slate_post_tick_callback(drive)
print('Started Seed traversal',mode,start,end)
