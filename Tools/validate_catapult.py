"""Play validation for the constraint catapult: real physics, reload and repeated input."""
import unreal,json,time,traceback
from pathlib import Path
ROOT='/Game/StealthShooter/Physics/Catapult/'
REPORT=Path(unreal.Paths.project_dir())/'Docs/CatapultValidation310.json'
checks=[];cycles=[];stage=0;started=0;handle=None;wall_started=0
world=cat=arm=hinge=ball=None
max_x=max_z=max_angle=0;sample_count=0;landed=False;count=0;fire_time=0

def prop(a,n):return a.get_editor_property(n)
def check(name,value,detail=None):
    checks.append({'check':name,'passed':bool(value),'detail':detail})
    if not value:raise AssertionError(name+': '+str(detail))
def now():return unreal.GameplayStatics.get_time_seconds(world)
def ready():return prop(cat,'bReady')
def finish(error=None):
    global handle
    if handle:unreal.unregister_slate_post_tick_callback(handle);handle=None
    REPORT.write_text(json.dumps({'map':'L_Catapult','mode':'Play In Editor','checks':checks,'cycles':cycles,'passed':sum(c['passed'] for c in checks),'failed':sum(not c['passed'] for c in checks),'error':error,'elapsed_seconds':round(time.monotonic()-wall_started,2)},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    unreal.log('CATAPULT_TESTS_FINISHED '+str(REPORT))
def start_cycle():
    global ball,max_x,max_z,max_angle,sample_count,landed,count,fire_time,stage,started
    ball=prop(cat,'LoadedBall');mesh=prop(ball,'BallMesh');p=mesh.get_world_location()
    check('Cycle '+str(count+1)+': ammunition is in spoon',abs(p.x+270)<55 and abs(p.y)<25 and 205<p.z<255,str(p))
    check('Loaded ammunition has no expiry',ball.get_life_span()==0)
    check('Physical mesh is ammunition root',ball.root_component==mesh)
    before=prop(cat,'ShotCount');n=len(unreal.GameplayStatics.get_all_actors_of_class(world,ball.get_class()))
    for _ in range(8):cat.call_method('Fire')
    check('Repeated Fire while busy creates one shot',prop(cat,'ShotCount')==before+1)
    check('Fire does not spawn extra ammunition',len(unreal.GameplayStatics.get_all_actors_of_class(world,ball.get_class()))==n)
    check('Fire sets busy and clears ready',prop(cat,'bBusy') and not ready())
    check('Only fired ammunition gets cleanup timer',20<ball.get_life_span()<=25)
    max_x=p.x;max_z=p.z;max_angle=0;sample_count=0;landed=False;fire_time=now();stage=2;started=now()

def tick(dt):
    global stage,started,world,cat,arm,hinge,ball,max_x,max_z,max_angle,sample_count,landed,count
    try:
        if time.monotonic()-wall_started>100:raise TimeoutError('Catapult Play validation timed out')
        if stage==0:
            worlds=unreal.EditorLevelLibrary.get_pie_worlds(False)
            if not worlds:return
            world=worlds[0];actors=unreal.GameplayStatics.get_all_actors_of_class(world,unreal.load_asset(ROOT+'BP_Catapult').generated_class())
            if not actors:return
            cat=actors[0];arm=prop(cat,'ThrowingArm');hinge=prop(cat,'ArmConstraint');started=now();stage=1
        if stage==1:
            if not ready():
                if now()-started>15:raise TimeoutError('Initial reload failed')
                return
            ball=prop(cat,'LoadedBall')
            check('Hinge and payload Physics Constraint Components',len(cat.get_components_by_class(unreal.PhysicsConstraintComponent))==2)
            bodies=hinge.get_constrained_components();check('Constraint binds fixed base and throwing arm',bodies[0]==prop(cat,'Base') and bodies[2]==arm)
            check('Arm simulates physics',arm.is_simulating_physics())
            check('Cannonball simulates physics',prop(ball,'BallMesh').is_simulating_physics())
            check('Cannonball uses continuous collision detection',prop(prop(ball,'BallMesh'),'body_instance').get_editor_property('use_ccd'))
            check('Base remains fixed',not prop(cat,'Base').is_simulating_physics())
            check('Loading angle is settled',abs(hinge.get_current_swing2())<2)
            # Wait for gravity to seat the newly spawned ball before the first throw.
            started=now();stage=3
        elif stage==3:
            if now()-started>.8:start_cycle()
        elif stage==2:
            p=prop(ball,'BallMesh').get_world_location();max_x=max(max_x,p.x);max_z=max(max_z,p.z);max_angle=max(max_angle,abs(hinge.get_current_swing2()));sample_count+=1
            if p.x>200 and p.z<25:landed=True
            if now()-started>15:raise TimeoutError('Automatic reload failed')
            if ready() and now()-started>2:
                check('Cycle '+str(count+1)+': cannonball leaves spoon forward',max_x>300,round(max_x,2))
                check('Cycle '+str(count+1)+': physical ballistic arc rises',max_z>280,round(max_z,2))
                check('Cycle '+str(count+1)+': cannonball collides with ground',landed)
                check('Cycle '+str(count+1)+': hinge stays within angular limit',max_angle<78,round(max_angle,2))
                check('Cycle '+str(count+1)+': arm returns before loading',abs(hinge.get_current_swing2())<2)
                check('Cycle '+str(count+1)+': reload creates a different ball',prop(cat,'LoadedBall')!=ball)
                check('Cycle '+str(count+1)+': base position is unchanged',prop(cat,'Base').get_world_location().distance(unreal.Vector(-70,0,20))<.01)
                cycles.append({'shot':count+1,'maximum_forward_x_cm':round(max_x,2),'apex_z_cm':round(max_z,2),'maximum_hinge_degrees':round(max_angle,2),'physics_frames':sample_count,'reload_seconds':round(now()-fire_time,2)})
                count+=1
                if count==3:finish();return
                started=now();stage=3
    except Exception:
        error=traceback.format_exc();checks.append({'check':'Play validation completed','passed':False,'detail':error});finish(error)

def run():
    global checks,cycles,stage,wall_started,handle,count
    assert not handle,'Validation already running'
    checks=[];cycles=[];stage=0;count=0;wall_started=time.monotonic();handle=unreal.register_slate_post_tick_callback(tick)
    return 'Started three physical firing/reload cycles in Play'

