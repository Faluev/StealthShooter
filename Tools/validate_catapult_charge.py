"""Validate minimum, medium and full hold/release throws in actual Play."""
import unreal,json,time,traceback
from pathlib import Path
import build_catapult as c
REPORT=Path(unreal.Paths.project_dir())/'Docs/CatapultChargeValidation.json'
checks=[];shots=[];stage=0;index=0;handle=None;started=0;wall=0
world=cat=ball=arm=hud=None
maximum_x=maximum_z=0;landing_x=None
holds=[.05,1,2.4]

def p(obj,name):return obj.get_editor_property(name)
def now():return unreal.GameplayStatics.get_time_seconds(world)
def check(name,ok,detail=None):
 checks.append({'check':name,'passed':bool(ok),'detail':detail})
 if not ok:raise AssertionError(name+': '+str(detail))
def finish(error=None):
 global handle
 if handle:unreal.unregister_slate_post_tick_callback(handle);handle=None
 REPORT.write_text(json.dumps({'mode':'Play In Editor','checks':checks,'shots':shots,'passed':sum(x['passed'] for x in checks),'failed':sum(not x['passed'] for x in checks),'error':error,'elapsed_seconds':round(time.monotonic()-wall,2)},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 unreal.log('CATAPULT_CHARGE_TESTS_FINISHED')
def tick(dt):
 global world,cat,ball,arm,hud,stage,index,started,maximum_x,maximum_z,landing_x
 try:
  if time.monotonic()-wall>110:raise TimeoutError('Charge validation timeout')
  if stage==0:
   worlds=unreal.EditorLevelLibrary.get_pie_worlds(False)
   if not worlds:return
   world=worlds[0];actors=unreal.GameplayStatics.get_all_actors_of_class(world,c.asset('BP_Catapult').generated_class())
   if not actors:return
   cat=actors[0];arm=p(cat,'ThrowingArm');hud=p(cat,'HUDWidget')
   if not p(cat,'bReady'):return
   check('UMG meter is visible',hud and hud.is_in_viewport())
   check('Initial meter shows minimum charge',abs(p(p(hud,'PowerBar'),'percent')-.2)<.01)
   n=p(cat,'ShotCount');cat.call_method('ReleaseCharge');check('Release without press does not shoot',p(cat,'ShotCount')==n)
   stage=1;started=now()
  elif stage==1 and now()-started>.8:
   ball=p(cat,'LoadedBall');before=p(cat,'ShotCount');cat.call_method('BeginCharge');cat.call_method('BeginCharge')
   check('Hold begins one charge',p(cat,'bCharging'))
   check('Press alone does not shoot',p(cat,'ShotCount')==before)
   stage=2;started=now()
  elif stage==2 and now()-started>holds[index]:
   check('Holding F never fires automatically',p(cat,'ShotCount')==index)
   charge=p(cat,'Charge')
   if index==2:
    check('Charge is capped at 100 percent',abs(charge-1)<.001)
    check('Full meter reaches 100 percent',abs(p(p(hud,'PowerBar'),'percent')-1)<.01)
   elif index==1:check('Half-duration produces medium charge',.55<charge<.7,charge)
   cat.call_method('ReleaseCharge');check('Release fires exactly once',p(cat,'ShotCount')==index+1)
   check('Release ends charging',not p(cat,'bCharging'))
   before=p(cat,'ShotCount');cat.call_method('ReleaseCharge');cat.call_method('BeginCharge');check('Reload rejects extra presses and releases',p(cat,'ShotCount')==before and not p(cat,'bCharging'))
   shots.append({'hold_seconds':holds[index],'charge':p(cat,'LastShotCharge')});maximum_x=ball.get_actor_location().x;maximum_z=ball.get_actor_location().z;landing_x=None;stage=3;started=now()
  elif stage==3:
   loc=ball.get_actor_location()
   if landing_x is None and loc.x>0 and loc.z<25:landing_x=loc.x
   maximum_x=max(maximum_x,loc.x);maximum_z=max(maximum_z,loc.z)
   check_limit=abs(p(cat,'ArmConstraint').get_current_swing2())
   if check_limit>78:raise AssertionError('Hinge exceeded limit')
   if now()-started>18:raise TimeoutError('Reload did not complete')
   if p(cat,'bReady'):
    shots[-1].update({'maximum_x_cm':round(maximum_x,1),'apex_z_cm':round(maximum_z,1),'first_landing_x_cm':round(landing_x,1) if landing_x is not None else None,'reload_seconds':round(now()-started,2)})
    check('Throw '+str(index+1)+' leaves the spoon',maximum_x>0,maximum_x)
    check('Throw '+str(index+1)+' reloads a fresh cannonball',p(cat,'LoadedBall')!=ball)
    check('Throw '+str(index+1)+' stops before loading',abs(p(cat,'ArmConstraint').get_current_swing2())<2)
    index+=1
    if index==3:
     check('Maximum power throws farther than minimum',shots[2]['first_landing_x_cm']>shots[0]['first_landing_x_cm']+300,shots)
     check('Medium power lands between weak and full',shots[0]['first_landing_x_cm']<shots[1]['first_landing_x_cm']<shots[2]['first_landing_x_cm'],shots)
     check('Power levels are ordered',shots[0]['charge']<shots[1]['charge']<shots[2]['charge'])
     finish();return
    stage=1;started=now()
 except Exception:finish(traceback.format_exc())
def run():
 global checks,shots,stage,index,wall,handle
 checks=[];shots=[];stage=0;index=0;wall=time.monotonic();handle=unreal.register_slate_post_tick_callback(tick);return 'Testing three charge strengths in Play'
