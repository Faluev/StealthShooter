"""Real Play checks: alternate transient data drives GAS damage/cooldown and round settings; source assets stay untouched."""
import unreal,json,traceback
from pathlib import Path
from validate_quest_practice import aim,aimed_at
RUN=None
class DataCheck:
 def __init__(self):
  self.w=unreal.EditorLevelLibrary.get_pie_worlds(False)[0];self.mode=unreal.GameplayStatics.get_game_mode(self.w)
  self.table=self.mode.weapon_definitions;self.definition=self.mode.round_definition;self.row=self.mode.player_weapon_row
  self.spawner=unreal.GameplayStatics.get_all_actors_of_class(self.w,unreal.QuestBotSpawner)[0]
  self.checks=[];self.error=None;self.probe_table=unreal.new_object(unreal.DataTable);self.probe_round=unreal.new_object(unreal.QuestRoundDefinition)
  self.mode.restart_run();self.refresh();self.phase='baseline';self.started=self.now();self.handle=unreal.register_slate_post_tick_callback(self.tick)
 def now(self):return unreal.GameplayStatics.get_time_seconds(self.w)
 def refresh(self):self.p=unreal.GameplayStatics.get_player_pawn(self.w,0);self.q=self.mode.get_director().get_active_quest()
 def go(self,name):self.phase=name;self.started=self.now()
 def check(self,name,value,data=None):
  self.checks.append({'name':name,'passed':bool(value),'data':data})
  if not value:raise AssertionError(name+': '+str(data))
 def live(self):return [b for b in unreal.GameplayStatics.get_all_actors_of_class(self.w,unreal.QuestBot) if not b.is_dead()]
 def fill(self,damage=13,interval=.8,range=6000):
  rows=[{'Name':'Probe','DisplayName':'Validation only','Damage':damage,'ShotInterval':interval,'Range':range,'Mesh':'/Game/Weapons/Rifle/Meshes/SM_Rifle.SM_Rifle','Sound':'/Game/StealthShooter/CombatGAS/Audio/S_BotShot.S_BotShot'}]
  assert unreal.DataTableFunctionLibrary.fill_data_table_from_json_string(self.probe_table,json.dumps(rows),unreal.QuestWeaponRow.static_struct())
 def restore(self):
  self.mode.set_editor_property('weapon_definitions',self.table);self.mode.set_editor_property('player_weapon_row',self.row);self.mode.set_editor_property('round_definition',self.definition)
  self.mode.get_director().fail_active_quest('Validation cleanup');self.mode.apply_round_definition();self.mode.restart_run();self.refresh()
 def finish(self):
  unreal.unregister_slate_post_tick_callback(self.handle)
  try:self.restore()
  except Exception:self.error=(self.error or '')+'\nCleanup: '+traceback.format_exc()
  Path('C:/Users/Aluev/StealthShooter/Docs/QuestDataValidation.json').write_text(json.dumps({'passed':sum(c['passed'] for c in self.checks),'failed':sum(not c['passed'] for c in self.checks),'error':self.error,'phase':self.phase,'checks':self.checks},ensure_ascii=False,indent=2),encoding='utf8')
 def target(self):
  b=self.live()[0];b.set_actor_tick_enabled(False);b.character_movement.stop_movement_immediately();b.set_actor_location(unreal.Vector(550,-500,95),False,True)
  self.p.set_actor_location(unreal.Vector(-350,-500,95),False,True);self.p.character_movement.stop_movement_immediately();return b
 def tick(self,delta):
  try:
   for b in self.live():b.set_editor_property('sight_radius',0.)
   age=self.now()-self.started
   if self.phase=='baseline' and age>3:
    names=[str(x) for x in self.mode.get_weapon_row_names()];row=self.mode.read_weapon_row('Rifle')
    self.check('DataTable row names can be read',names==['Rifle'],names)
    self.check('DataTable row resolves',row is not None)
    self.check('Weapon snapshot matches original balance',self.p.active_weapon.damage==25 and abs(self.p.active_weapon.shot_interval-.35)<.001 and self.p.active_weapon.range==6000)
    self.check('Asynchronous presentation finished',self.p.get_editor_property('bWeaponPresentationReady'))
    self.check('Soft mesh resolved to rifle',self.p.rifle.static_mesh.get_name()=='SM_Rifle')
    self.check('Soft sound resolved',self.p.get_editor_property('shot_sound').get_name()=='S_BotShot')
    self.check('Default round preserved',self.q.required_kills==3 and self.q.time_limit==90 and self.spawner.max_alive==2 and self.spawner.spawn_interval==2)
    self.check('Default health preserved',self.p.get_health()==100 and all(b.get_bot_health()==50 for b in self.live()))
    self.check('Missing row rejected safely',self.mode.read_weapon_row('Missing') is None)
    self.fill();self.mode.set_editor_property('weapon_definitions',self.probe_table);self.mode.set_editor_property('player_weapon_row','Probe')
    for key,value in [('required_kills',4),('time_limit',120.),('max_alive',1),('spawn_interval',.3),('player_health',125.),('bot_health',75.)]:self.probe_round.set_editor_property(key,value)
    self.mode.set_editor_property('round_definition',self.probe_round)
    self.check('Active round configuration cannot change mid-objective',not self.mode.apply_round_definition())
    self.mode.get_director().fail_active_quest('Validation transition')
    self.check('Round definition applies between rounds',self.mode.apply_round_definition())
    self.mode.restart_run();self.refresh();self.go('alternate')
   elif self.phase=='alternate' and age>1:
    self.check('Alternate row drives player',self.p.active_weapon.damage==13 and abs(self.p.active_weapon.shot_interval-.8)<.001)
    self.check('Alternate health reaches GAS and HUD',self.p.get_health()==125 and self.p.get_max_health()==125 and self.p.hud.get_displayed_health()==1.)
    self.check('Alternate objective and deadline apply',self.q.required_kills==4 and self.q.time_limit==120 and self.q.get_remaining_seconds()>115)
    self.check('Alternate spawn cap and interval apply',len(self.live())==1 and self.spawner.max_alive==1 and abs(self.spawner.spawn_interval-.3)<.001)
    self.bot=self.target();self.check('Alternate bot health reaches GAS',self.bot.get_bot_health()==75)
    self.go('aim')
   elif self.phase=='aim':
    aim(self.p,self.bot)
    if aimed_at(self.p,self.bot) and age>.2:
     self.check('Configured shot activates',self.p.try_fire())
     self.check('DataTable Damage reaches Gameplay Effect',self.bot.get_bot_health()==62,self.bot.get_bot_health())
     self.check('Configured cooldown blocks immediate shot',not self.p.try_fire())
     self.go('cooldown')
    elif age>4:raise AssertionError('Aim did not resolve')
   elif self.phase=='cooldown':
    aim(self.p,self.bot)
    if age>.45 and not hasattr(self,'mid_checked'):
     self.check('Longer table cooldown still blocks at 0.45 seconds',not self.p.try_fire());self.mid_checked=True
    if age>1:
     self.check('Shot allowed after configured cooldown',self.p.try_fire())
     self.check('Second shot uses same configured damage',self.bot.get_bot_health()==49)
     self.fill(range=200);self.mode.restart_run();self.refresh();self.go('short_range')
   elif self.phase=='short_range' and age>1:
    self.bot=self.target();self.check('Range is read from alternate row',self.p.active_weapon.range==200);self.go('range_aim')
   elif self.phase=='range_aim':
    aim(self.p,self.bot)
    if age>.3:
     before=self.bot.get_bot_health();self.check('Short range still permits firing',self.p.try_fire())
     self.check('Out of range bot receives no damage',self.bot.get_bot_health()==before and self.p.hits==0)
     self.fill(damage=-1)
     self.check('Invalid weapon row is rejected',self.mode.read_weapon_row('Probe') is None)
     self.mode.restart_run();self.refresh();self.check('Invalid row falls back to original balance',self.p.active_weapon.damage==25 and abs(self.p.active_weapon.shot_interval-.35)<.001)
     self.probe_round.set_editor_property('max_alive',0)
     self.mode.get_director().fail_active_quest('Validation invalid settings')
     self.check('Invalid round definition rejected without partial application',not self.mode.apply_round_definition() and self.spawner.max_alive==1)
     self.restore();self.go('restored')
   elif self.phase=='restored' and age>3:
    self.check('Source round values restored',self.q.required_kills==3 and self.q.time_limit==90 and self.spawner.max_alive==2)
    self.check('Source player and bot health restored',self.p.get_health()==100 and len(self.live())==2 and all(b.get_bot_health()==50 for b in self.live()))
    self.check('Source table remains unchanged',self.mode.read_weapon_row('Rifle').damage==25 and self.mode.read_weapon_row('Probe') is None)
    self.check('Source DataAsset remains unchanged',self.definition.player_health==100 and self.definition.bot_health==50 and self.definition.required_kills==3)
    self.check('Presentation resolves after repeated respawns',self.p.get_editor_property('bWeaponPresentationReady') and self.p.rifle.static_mesh.get_name()=='SM_Rifle')
    self.finish()
  except Exception:self.error=traceback.format_exc();self.finish()
def run():
 global RUN
 RUN=DataCheck();return 'Data-driven gameplay checks running in Play'
