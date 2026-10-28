"""In-Play checks for weapon attachment, locomotion, jump poses and local Fab dressing."""
import unreal,json,traceback
from pathlib import Path
RUN=None
class PresentationCheck:
 def __init__(self):
  self.w=unreal.EditorLevelLibrary.get_pie_worlds(False)[0];self.mode=unreal.GameplayStatics.get_game_mode(self.w);self.mode.restart_run()
  self.p=unreal.GameplayStatics.get_player_pawn(self.w,0);self.started=self.now();self.checks=[];self.error=None;self.phase=0;self.bot_start={};self.foot_start={};self.travel={};self.pose_motion={};self.jump_seen=False;self.jump_asset_seen=False;self.player_walk_seen=False
  self.handle=unreal.register_slate_post_tick_callback(self.tick)
 def now(self):return unreal.GameplayStatics.get_time_seconds(self.w)
 def check(self,name,value,data=None):
  self.checks.append({'name':name,'passed':bool(value),'data':data})
  if not value:raise AssertionError(name+': '+str(data))
 def finish(self):
  unreal.unregister_slate_post_tick_callback(self.handle)
  Path('C:/Users/Aluev/StealthShooter/Docs/QuestPresentationValidation.json').write_text(json.dumps({'passed':sum(c['passed'] for c in self.checks),'failed':sum(not c['passed'] for c in self.checks),'error':self.error,'checks':self.checks},ensure_ascii=False,indent=2),encoding='utf8')
  self.mode.restart_run()
 def tick(self,delta):
  try:
   age=self.now()-self.started;bots=[b for b in unreal.GameplayStatics.get_all_actors_of_class(self.w,unreal.QuestBot) if not b.is_dead()]
   for b in bots:
    b.set_editor_property('sight_radius',0.)
    if age>2:
     key=b.get_name();pos=b.get_actor_location();foot=b.mesh.get_socket_location('foot_l')-pos
     if key not in self.bot_start:self.bot_start[key]=pos;self.foot_start[key]=foot
     self.travel[key]=max(self.travel.get(key,0),(pos-self.bot_start[key]).length())
     self.pose_motion[key]=max(self.pose_motion.get(key,0),(foot-self.foot_start[key]).length())
   if self.phase==0 and age>3:
    self.check('Player uses Epic rifle mesh',self.p.rifle.static_mesh.get_name()=='SM_Rifle')
    self.check('Rifle follows right hand',self.p.rifle.get_attach_socket_name()=='hand_r')
    self.check('Player rifle has material',all(self.p.rifle.get_materials()))
    self.check('Saved directional locomotion is active',self.p.mesh.get_anim_instance().get_animation_asset()==self.p.get_editor_property('armed_locomotion'))
    axis=(self.p.get_shot_start()-self.p.rifle.get_world_location()).normal()
    dot=unreal.MathLibrary.dot_vector_vector(axis,self.p.get_actor_forward_vector())
    self.check('Barrel points forward with character',dot>.90,dot)
    self.check('Rifle retains visual-only collision',self.p.rifle.get_collision_enabled()==unreal.CollisionEnabled.NO_COLLISION)
    self.phase=1
   if self.phase==1:
    self.p.add_movement_input(unreal.Vector(0,-1,0),.7)
    if self.p.get_velocity().length()>100:self.player_walk_seen=True
    if age>4:
     self.check('Player locomotion responds to actual movement',self.player_walk_seen)
     self.p.character_movement.stop_movement_immediately();self.p.jump();self.phase=2
   elif self.phase==2:
    if self.p.character_movement.is_falling():
     self.jump_seen=True
     if self.p.mesh.get_anim_instance().get_animation_asset()==self.p.get_editor_property('armed_fall'):self.jump_asset_seen=True
    if age>6:
     self.check('Original jump remains functional',self.jump_seen)
     self.check('Airborne rifle pose is used',self.jump_asset_seen)
     self.check('Landing restores directional locomotion',not self.p.character_movement.is_falling() and self.p.mesh.get_anim_instance().get_animation_asset()==self.p.get_editor_property('armed_locomotion'))
     self.phase=3
   elif self.phase==3 and age>10:
    self.check('Dynamic bots are present',len(bots)==2)
    self.check('Bots patrol through navigation',max(self.travel.values(),default=0)>150,self.travel)
    self.check('Bot feet animate while moving',max(self.pose_motion.values(),default=0)>8,self.pose_motion)
    for i,b in enumerate(bots):
     self.check('Bot '+str(i)+' holds rifle at right hand',b.weapon_root.get_attach_socket_name()=='hand_r' and b.weapon_body.static_mesh.get_name()=='SM_Rifle')
     self.check('Bot '+str(i)+' muzzle matches barrel',(b.muzzle.get_world_location()-b.weapon_body.get_socket_location('Muzzle')).length()<3)
     self.check('Bot '+str(i)+' avoids nearby agents',b.character_movement.get_editor_property('bUseRVOAvoidance'))
     self.check('Bot '+str(i)+' has varied patrol route',len(b.patrol_points)>=3)
     self.check('Bot '+str(i)+' retains GAS health',b.get_bot_health()==50)
    decor=[a for a in unreal.GameplayStatics.get_all_actors_of_class(self.w,unreal.StaticMeshActor) if a.get_actor_label().startswith('QuestRuins_')]
    self.check('Fab courtyard dressing is present',len(decor)>=100,len(decor))
    self.check('Decoration does not obstruct navigation or shots',all(a.static_mesh_component.get_collision_enabled()==unreal.CollisionEnabled.NO_COLLISION for a in decor))
    self.check('Quest and health remain unchanged',self.mode.get_director().get_active_quest().current_kills==0 and self.p.get_health()==100)
    self.finish()
  except Exception:self.error=traceback.format_exc();self.finish()
def run():
 global RUN
 RUN=PresentationCheck()
 return 'Presentation checks running in Play'
