"""Compare the supplied dash with its GAS refactor using real Enhanced Input in Play."""
import json,time,traceback
from pathlib import Path
import unreal

PROJECT=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()));ROOT_DOCS=PROJECT/'Docs'
mode='baseline';checks=[];trials=[];stage=0;case_index=0;started=wall=0;handle=None
world=pawn=controller=input_system=None
origin=None;before=None;before_particles=set();records={}
cases=[('forward',0,False),('right',90,False),('backward',180,False),('airborne',45,True),('wall_no_sweep',0,False)]

def check(name,ok,detail=None):
 checks.append({'check':name,'passed':bool(ok),'detail':detail})
 if not ok:raise AssertionError(name+': '+str(detail))
def clock():return unreal.GameplayStatics.get_time_seconds(world)
def vector(v):return [round(v.x,4),round(v.y,4),round(v.z,4)]
def particles():
 return [p for p in unreal.ObjectIterator(unreal.ParticleSystemComponent) if p.get_editor_property('template') and p.get_editor_property('template').get_path_name()=='/Game/FXVarietyPack/Particles/P_ky_hit1.P_ky_hit1' and 'UEDPIE_' in p.get_path_name()]
def inject(value):input_system.inject_input_vector_for_action(unreal.load_asset('/Game/ThirdPerson/Input/Actions/IA_Dash'),unreal.Vector(value,0,0),[],[])
def settings():
 movement=pawn.character_movement;mesh=pawn.mesh;capsule=pawn.capsule_component
 data={'DashDistance':pawn.get_editor_property('DashDistance'),'movement':{},'capsule_radius':capsule.get_unscaled_capsule_radius(),'capsule_half_height':capsule.get_unscaled_capsule_half_height(),'mesh':mesh.get_skeletal_mesh_asset().get_path_name(),'animation_class':mesh.get_editor_property('anim_class').get_path_name(),'mesh_location':vector(mesh.get_editor_property('relative_location'))}
 for key in ['gravity_scale','jump_z_velocity','air_control','max_walk_speed','max_acceleration','braking_deceleration_walking','orient_rotation_to_movement']:data['movement'][key]=movement.get_editor_property(key)
 for comp in pawn.get_components_by_class(unreal.SpringArmComponent):data['spring_arm']={'length':comp.get_editor_property('target_arm_length'),'control_rotation':comp.get_editor_property('use_pawn_control_rotation'),'relative_location':vector(comp.get_editor_property('relative_location'))}
 for comp in pawn.get_components_by_class(unreal.CameraComponent):data['camera']={'fov':comp.get_editor_property('field_of_view'),'control_rotation':comp.get_editor_property('use_pawn_control_rotation')}
 return data

def finish(error=None):
 global handle
 if handle:unreal.unregister_slate_post_tick_callback(handle);handle=None
 if error and world and pawn and input_system and origin:
  inject(0);pawn.character_movement.stop_movement_immediately();pawn.set_actor_location(origin,False,True);pawn.character_movement.set_movement_mode(unreal.MovementMode.MOVE_WALKING)
  unreal.AudioMixerLibrary.stop_recording_output(world,unreal.AudioRecordingExportType.WAV_FILE,mode+'_failed',str(PROJECT/'Saved/DashAudio'))
 ROOT_DOCS.mkdir(parents=True,exist_ok=True)
 report={'mode':mode,'checks':checks,'trials':trials,'settings':records.get('settings'),'passed':sum(c['passed'] for c in checks),'failed':sum(not c['passed'] for c in checks),'error':error,'elapsed_seconds':round(time.monotonic()-wall,2)}
 filename={'baseline':'DashBaseline.json','refactored':'DashGASValidation.json','collision':'DashCollisionValidation.json'}[mode]
 (ROOT_DOCS/filename).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 unreal.log('HW09_DASH_VALIDATION_FINISHED '+mode)

def setup_case():
 global before,before_particles,stage,started
 name,yaw,air=cases[case_index];pawn.character_movement.stop_movement_immediately();pawn.character_movement.set_movement_mode(unreal.MovementMode.MOVE_FLYING)
 pawn.set_actor_location(origin+unreal.Vector(0,0,200 if air else 0),False,True);pawn.set_actor_rotation(unreal.Rotator(yaw=yaw),False)
 before=pawn.get_actor_location();before_particles={p.get_path_name() for p in particles()};inject(1);started=clock();stage=2
 if name=='wall_no_sweep':
  candidates=[]
  for actor in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.StaticMeshActor):
   center,extent=actor.get_actor_bounds(True)
   if extent.x<70 and extent.y>300 and extent.z>100:candidates.append((actor.get_name(),center,extent))
  check('Existing wall is available for no-sweep parity',bool(candidates))
  _,center,extent=sorted(candidates,key=lambda x:x[0])[0];before=unreal.Vector(center.x-extent.x-100,center.y,origin.z);pawn.set_actor_location(before,False,True)


def tick(dt):
 global world,pawn,controller,input_system,origin,stage,case_index,started,before,before_particles
 try:
  if time.monotonic()-wall>70:raise TimeoutError('Dash scenarios timed out')
  if stage==0:
   worlds=unreal.EditorLevelLibrary.get_pie_worlds(False)
   if not worlds:return
   world=worlds[0];pawn=unreal.GameplayStatics.get_player_pawn(world,0);controller=unreal.GameplayStatics.get_player_controller(world,0)
   if not pawn or not controller:return
   systems=[s for s in unreal.ObjectIterator(unreal.EnhancedInputLocalPlayerSubsystem) if not s.get_name().startswith('Default__') and s.get_outer().get_world()==world]
   if len(systems)!=1:raise RuntimeError('Ambiguous Enhanced Input subsystem: '+str(systems))
   input_system=systems[0];origin=pawn.get_actor_location();records['settings']=settings()
   check('Dash distance remains 300 cm',abs(pawn.get_editor_property('DashDistance')-300)<.001)
   if mode!='baseline':
    base=json.loads((ROOT_DOCS/'DashBaseline.json').read_text());check('Character and camera settings equal baseline',records['settings']==base['settings'],records['settings'])
    check('Ability System Component is present',len(pawn.get_components_by_class(unreal.AbilitySystemComponent))==1)
   else:check('Original character has no Ability System Component',not pawn.get_components_by_class(unreal.AbilitySystemComponent))
   audio_dir=PROJECT/'Saved/DashAudio';audio_dir.mkdir(parents=True,exist_ok=True);unreal.AudioMixerLibrary.start_recording_output(world,2)
   stage=1;started=clock()
  elif stage==1 and clock()-started>.2:setup_case()
  elif stage==2:
   delta=pawn.get_actor_location()-before;expected=pawn.get_actor_forward_vector()*pawn.get_editor_property('DashDistance')
   if delta.length()<1 and clock()-started<.3:return
   name=cases[case_index][0];new=[p for p in particles() if p.get_path_name() not in before_particles]
   if mode=='collision' and name=='wall_no_sweep':
    check('wall: sweep shortens the dash at the obstacle',0<delta.length()<299,vector(delta))
    radius=pawn.capsule_component.get_scaled_capsule_radius();gap=100-delta.x
    check('wall: capsule retains its radius of clearance',radius-.05<=gap<=radius+3,{'gap':gap,'radius':radius})
   else:check(name+': instantaneous displacement matches forward distance',(delta-expected).length()<.1,vector(delta))
   check(name+': one original emitter is spawned',len(new)==1,len(new))
   emitter=new[0];check(name+': effect stays at the pre-dash position',(emitter.get_world_location()-before).length()<.1,vector(emitter.get_world_location()))
   scale=emitter.get_world_scale();check(name+': effect scale remains 0.6',max(abs(scale.x-.6),abs(scale.y-.6),abs(scale.z-.6))<.001,vector(scale))
   trials.append({'case':name,'start':vector(before),'displacement':vector(delta),'emitter_location':vector(emitter.get_world_location()),'emitter_scale':vector(scale)})
   inject(0);case_index+=1;stage=3;started=clock()
  elif stage==3 and clock()-started>.08:
   if case_index<len(cases):setup_case()
   else:
    pawn.character_movement.stop_movement_immediately();pawn.set_actor_rotation(unreal.Rotator(),False);pawn.set_actor_location(origin,False,True);before=pawn.get_actor_location();records['held_start']=clock();inject(1);stage=4
  elif stage==4:
   if clock()-records['held_start']<.35:inject(1)
   else:
    check('Holding the dash action does not repeat',abs((pawn.get_actor_location()-before).length()-300)<.1,vector(pawn.get_actor_location()-before));inject(0);stage=5;started=clock();records['rapid']=0
  elif stage==5 and clock()-started>.03:
   before=pawn.get_actor_location();inject(1);stage=6
  elif stage==6:
   check('Repeated press '+str(records['rapid']+1)+' has no new cooldown',abs((pawn.get_actor_location()-before).length()-300)<.1,vector(pawn.get_actor_location()-before));inject(0);records['rapid']+=1
   if records['rapid']<5:stage=5;started=clock()
   else:stage=7;started=clock()
  elif stage==7 and clock()-started>.6:
   unreal.AudioMixerLibrary.stop_recording_output(world,unreal.AudioRecordingExportType.WAV_FILE,mode+'_dash',str(PROJECT/'Saved/DashAudio'))
   if mode!='baseline':
    asc=pawn.get_components_by_class(unreal.AbilitySystemComponent)[0];check('Gameplay Cue handles every accepted dash',pawn.get_editor_property('DashCueCount')==len(cases)+1+5,pawn.get_editor_property('DashCueCount'))
   pawn.character_movement.stop_movement_immediately();pawn.set_actor_location(origin,False,True);pawn.character_movement.set_movement_mode(unreal.MovementMode.MOVE_WALKING);finish()
 except Exception:finish(traceback.format_exc())

def run(kind='collision'):
 global mode,checks,trials,stage,case_index,records,wall,handle
 assert handle is None
 mode=kind;checks=[];trials=[];stage=0;case_index=0;records={};wall=time.monotonic();handle=unreal.register_slate_post_tick_callback(tick);return 'Started '+kind+' dash parity scenarios'
