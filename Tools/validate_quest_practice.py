"""Functional 12.7 scenarios in actual Play. Offense tests isolate incoming fire; death tests use normal bot GAS shots."""
import json,traceback
from pathlib import Path
import unreal

RUN=None

def aimed_at(player,bot):
    hit=player.trace_aim()
    return hit is not None and bot.get_name() in hit.export_text()

def aim(player,bot):
    pc=unreal.GameplayStatics.get_player_controller(player,0)
    point=bot.get_actor_location()+unreal.Vector(0,0,25)
    pc.set_control_rotation(unreal.MathLibrary.find_look_at_rotation(player.follow_camera.get_world_location(),point))

class Validation:
    def __init__(self):
        self.world=unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        self.mode=unreal.GameplayStatics.get_game_mode(self.world)
        assert isinstance(self.mode,unreal.QuestGameMode)
        self.director=self.mode.get_director()
        self.spawner=unreal.GameplayStatics.get_all_actors_of_class(self.world,unreal.QuestBotSpawner)[0]
        self.checks=[];self.error=None;self.isolate=True;self.target=None;self.half_checked=False
        self.mode.restart_run();self.refresh();self.quest.set_editor_property('time_limit',90.)
        self.phase='baseline';self.started=self.now();self.last_shot=-100.;self.kills=0
        self.initial_spawn_count=self.spawner.total_spawned
        self.handle=unreal.register_slate_post_tick_callback(self.tick)
    def refresh(self):
        self.player=unreal.GameplayStatics.get_player_pawn(self.world,0)
        self.quest=self.director.get_active_quest()
    def now(self):return unreal.GameplayStatics.get_time_seconds(self.world)
    def live(self):return [b for b in unreal.GameplayStatics.get_all_actors_of_class(self.world,unreal.QuestBot) if not b.is_dead()]
    def check(self,name,condition,data=None):
        self.checks.append({'name':name,'passed':bool(condition),'data':data})
        if not condition:raise AssertionError(name+': '+str(data))
    def go(self,phase):self.phase=phase;self.started=self.now()
    def finish(self):
        unreal.unregister_slate_post_tick_callback(self.handle)
        out=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))/'Docs/QuestPracticeValidation.json'
        report={'map':'/Game/StealthShooter/Maps/L_QuestArena','passed':sum(c['passed'] for c in self.checks),'failed':sum(not c['passed'] for c in self.checks),'error':self.error,'phase':self.phase,'checks':self.checks}
        out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
        unreal.log('QUEST_VALIDATION_FINISHED '+str(report['passed']))
    def tick(self,delta):
        try:
            age=self.now()-self.started
            if self.isolate:
                for b in self.live():b.set_editor_property('sight_radius',0.)
            if self.phase=='baseline' and age>3:
                self.check('Quest active at round start',self.quest.state==unreal.QuestState.ACTIVE)
                self.check('Own kill counter starts at zero',self.quest.current_kills==0)
                self.check('Required kills editable and configured',self.quest.required_kills==3)
                self.check('Player GAS Health starts at 100',self.player.get_health()==100)
                self.check('HUD health matches GAS',self.player.hud.get_displayed_health()==1.)
                self.check('HUD displays quest progress','0 / 3' in self.player.hud.get_displayed_progress())
                self.check('No result panel during active quest',not self.player.hud.is_result_visible())
                self.check('Bots spawn dynamically to living cap',len(self.live())==2 and self.spawner.get_living_count()==2)
                self.check('Timer spawned a second bot',self.spawner.total_spawned>self.initial_spawn_count)
                self.check('Overflow spawn rejected',self.spawner.try_spawn_bot() is None)
                self.check('Bots own real GAS AttributeSets',all(isinstance(b.bot_attributes,unreal.CombatAttributeSet) for b in self.live()))
                self.check('Bot Health starts at 50',all(b.get_bot_health()==50 for b in self.live()))
                self.destroyed_bot=self.live()[0];self.destroyed_bot.destroy_actor();self.go('replace_destroyed')
            elif self.phase=='replace_destroyed' and age>2.5:
                self.check('Destroying a live bot does not credit a kill',self.quest.current_kills==0)
                self.check('Invalid weak references free spawn capacity',len(self.live())==2)
                self.player.set_actor_location(unreal.Vector(-350,-500,95),False,True)
                self.go('shoot')
            elif self.phase=='shoot':
                if not unreal.SystemLibrary.is_valid(self.target) or self.target.is_dead():
                    self.target=self.live()[0] if self.live() else None;self.half_checked=False
                if self.target:
                    aim(self.player,self.target)
                    if aimed_at(self.player,self.target) and self.now()-self.last_shot>.45:
                        before=self.target.get_bot_health();target=self.target
                        self.check('Shot activates through Gameplay Ability',self.player.try_fire())
                        self.last_shot=self.now()
                        self.check('Gameplay Effect subtracts exactly 25 Health',target.get_bot_health()==max(0,before-25))
                        self.check('One Gameplay Cue per player shot',self.player.shot_cues==self.player.shots_fired)
                        if not target.is_dead():
                            self.check('Partial damage does not complete a kill',self.quest.current_kills==self.kills)
                            self.check('Cooldown prevents immediate extra shot',not self.player.try_fire())
                        else:
                            self.kills+=1
                            self.check('Bot death credited once',self.quest.current_kills==self.kills)
                            self.check('Dead bot cannot shoot',not target.request_shot())
                            self.director.notify_bot_killed(target,self.player)
                            self.check('Duplicate death notification ignored',self.quest.current_kills==self.kills)
                            self.check('UI follows kill progress',f'{self.kills} / 3' in self.player.hud.get_displayed_progress())
                            if self.kills<3:
                                count=self.spawner.total_spawned;replacement=self.spawner.try_spawn_bot()
                                self.check('Death opens a replacement slot',replacement is not None and self.spawner.total_spawned==count+1)
                                self.check('Replacement still respects cap',self.spawner.get_living_count()<=2)
                            else:
                                self.check('Kill objective completed',self.quest.state==unreal.QuestState.COMPLETED)
                                self.check('Run succeeded at required count',self.director.get_editor_property('bSucceeded'))
                                self.check('Completion form visible',self.player.hud.is_result_visible())
                                self.check('Completion form has correct text','ВЫПОЛНЕНО' in self.player.hud.get_displayed_result())
                                self.check('Spawning stops on completion',not self.spawner.get_editor_property('bSpawning') and self.spawner.try_spawn_bot() is None)
                                self.check('Player cannot fire after completion',not self.player.try_fire())
                                self.director.fail_active_quest('Late failure')
                                self.check('Completed quest cannot fail later',self.quest.state==unreal.QuestState.COMPLETED)
                                self.go('restart_for_death')
                if age>25:raise AssertionError('Aim/shot scenario exceeded 25 seconds')
            elif self.phase=='restart_for_death' and age>.5:
                old=self.player;world_name=self.world.get_path_name();count=self.mode.restart_count
                self.player.hud.replay();self.refresh()
                self.check('Replay creates a new player pawn',old!=self.player)
                self.check('Respawn keeps same world',self.world.get_path_name()==world_name and self.mode.restart_count==count+1)
                self.check('Respawn restores Health',self.player.get_health()==100)
                self.check('Replay resets counter',self.quest.current_kills==0 and self.quest.state==unreal.QuestState.ACTIVE)
                self.check('Replay clears result panel',not self.player.hud.is_result_visible())
                self.check('Replay clears stale corpses',all(not b.is_dead() for b in unreal.GameplayStatics.get_all_actors_of_class(self.world,unreal.QuestBot)))
                self.isolate=False
                self.player.set_actor_location(unreal.Vector(-100,-450,95),False,True)
                self.go('death')
            elif self.phase=='death':
                if self.player.get_health()<=0:
                    self.check('Bots damage player through normal combat',self.player.get_health()==0)
                    self.check('Player death fails active quest',self.quest.state==unreal.QuestState.FAILED)
                    self.check('Failed run is not successful',not self.director.get_editor_property('bSucceeded'))
                    self.check('Failure reason identifies player death','Игрок погиб' in str(self.quest.failure_reason))
                    self.check('Failure form visible with correct title',self.player.hud.is_result_visible() and 'ПРОВАЛЕНО' in self.player.hud.get_displayed_result())
                    self.check('Spawning stops on failure',not self.spawner.get_editor_property('bSpawning'))
                    reason=str(self.quest.failure_reason);self.quest.fail_quest('Second reason')
                    self.check('Failure terminal state is idempotent',str(self.quest.failure_reason)==reason)
                    self.quest.set_editor_property('time_limit',.6);self.mode.restart_run();self.refresh();self.isolate=True;self.go('timeout')
                elif age>18:raise AssertionError('Normal bot fire did not kill the exposed player')
            elif self.phase=='timeout' and age>1:
                self.check('Deadline fails an incomplete objective',self.quest.state==unreal.QuestState.FAILED)
                self.check('Timeout has its own reason','Время вышло' in str(self.quest.failure_reason))
                self.check('Timeout displays failure form',self.player.hud.is_result_visible())
                self.check('Failure does not fabricate progress',self.quest.current_kills==0)
                self.quest.set_editor_property('time_limit',90.);self.mode.restart_run();self.refresh()
                self.check('Restart after timeout works',self.quest.state==unreal.QuestState.ACTIVE and self.quest.get_remaining_seconds()>89)
                self.check('Final UI has no stale result',not self.player.hud.is_result_visible())
                self.finish()
        except Exception:
            self.error=traceback.format_exc();self.finish()

def run():
    global RUN
    RUN=Validation();return 'Running quest validation in Play'
