"""Timed functional checks in a real Play world. Never edits source assets."""
import json, math, traceback
from pathlib import Path
import unreal

RUN = None


class CombatValidation:
    def __init__(self):
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        assert len(worlds) == 1, 'Start Play on L_CombatGAS first.'
        self.world = worlds[0]
        self.player = unreal.GameplayStatics.get_player_pawn(self.world,0)
        self.bot = unreal.GameplayStatics.get_all_actors_of_class(self.world,unreal.CombatBot)[0]
        assert isinstance(self.player,unreal.CombatPlayer)
        self.checks=[];self.error=None;self.phase='covered';self.phase_start=self.now()
        self.origin=self.bot.get_actor_location()
        self.actor_count=len(unreal.GameplayStatics.get_all_actors_of_class(self.world,unreal.Actor))
        self.initial_shots=self.bot.shot_count
        self.check('Health starts at 100',self.player.get_health()==100)
        self.check('MaxHealth is 100',self.player.get_max_health()==100)
        self.check('Player exposes a real ASC',isinstance(self.player.ability_system,unreal.AbilitySystemComponent))
        self.check('Player owns a real AttributeSet',isinstance(self.player.attributes,unreal.CombatAttributeSet))
        self.check('HUD created',self.player.hud is not None)
        self.check('HUD percentage starts at 1',abs(self.player.hud.get_displayed_health_percent()-1)<.001)
        self.check('Sight blocked by cover',not self.bot.can_shoot_target())
        self.check('Hidden target cannot activate shooting',not self.bot.request_shot())
        self.handle=unreal.register_slate_post_tick_callback(self.tick)

    def now(self):return unreal.GameplayStatics.get_time_seconds(self.world)
    def check(self,name,ok,data=None):
        self.checks.append({'name':name,'passed':bool(ok),'data':data})
        if not ok:raise AssertionError(name+': '+str(data))
    def advance(self,phase):self.phase=phase;self.phase_start=self.now()
    def place(self,point):
        self.player.character_movement.stop_movement_immediately()
        self.player.set_actor_location(unreal.Vector(*point),False,True)
    def finish(self):
        unreal.unregister_slate_post_tick_callback(self.handle)
        out=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))/'Docs/CombatGASValidation.json'
        report={'map':'/Game/StealthShooter/Maps/L_CombatGAS','passed':sum(c['passed'] for c in self.checks),
            'failed':sum(not c['passed'] for c in self.checks),'error':self.error,'checks':self.checks,
            'shot_times':list(self.bot.shot_times),'shot_count':self.bot.shot_count,
            'cue_count':self.bot.cue_count,'hit_count':self.bot.hit_count,'final_health':self.player.get_health()}
        out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
        unreal.log('COMBAT_GAS_VALIDATION_FINISHED '+str(report['passed']))

    def tick(self,delta):
        try:
            age=self.now()-self.phase_start
            if self.phase=='covered' and age>3:
                self.check('No shots through cover',self.bot.shot_count==self.initial_shots)
                self.check('No damage through cover',self.player.get_health()==100)
                self.check('Guard patrol moves with navigation',self.bot.get_actor_location().distance(self.origin)>50)
                self.check('Weapon is holstered during patrol',not self.bot.get_editor_property('bWeaponDrawn'))
                self.place((-100,-650,95))
                self.bot.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(self.bot.get_actor_location(),self.player.get_actor_location()),True)
                self.advance('first_shot')
            elif self.phase=='first_shot':
                if self.bot.shot_count>0:
                    self.check('Guard drew weapon',self.bot.get_editor_property('bWeaponDrawn'))
                    self.check('Guard entered combat',self.bot.state==unreal.CombatBotState.COMBAT)
                    self.check('First shot is exactly one activation',self.bot.shot_count==1)
                    self.check('Shot caused exactly one cue',self.bot.cue_count==1)
                    self.check('Shot hit player',self.bot.hit_count==1)
                    self.check('Damage GE changed Health to 90',self.player.get_health()==90)
                    self.check('Health bar updated from attribute delegate',abs(self.player.hud.get_displayed_health_percent()-.9)<.001)
                    self.check('Cooldown Gameplay Effect active',self.bot.get_shot_cooldown_remaining()>1.)
                    self.check('Rapid repeated requests blocked',all(not self.bot.request_shot() for _ in range(30)))
                    self.check('Blocked requests do not emit cues',self.bot.cue_count==1)
                    self.check('Blocked requests do not cause damage',self.player.get_health()==90)
                    self.advance('cadence')
                elif age>5:raise AssertionError('Visible target was not shot within five seconds.')
            elif self.phase=='cadence' and self.bot.shot_count>=3:
                times=list(self.bot.shot_times)
                gaps=[b-a for a,b in zip(times,times[1:])]
                self.check('Cooldown enforces at least 1.25 seconds',all(x>=1.249 for x in gaps),gaps)
                self.check('One cue per committed shot',self.bot.cue_count==self.bot.shot_count)
                self.check('10 Health damage per successful hit',self.player.get_health()==100-10*self.bot.hit_count)
                self.place((-1050,0,95))
                self.cover_shots=self.bot.shot_count;self.cover_health=self.player.get_health()
                self.cover_origin=self.bot.get_actor_location()
                self.advance('lost')
            elif self.phase=='lost' and age>.3 and age<.6:
                self.check('No activation after sight loss',not self.bot.request_shot())
                self.advance('return')
            elif self.phase=='return' and age>3:
                self.check('No damage after target takes cover',self.player.get_health()==self.cover_health)
                self.check('No shooting through wall after loss',self.bot.shot_count==self.cover_shots)
                self.check('Guard returned to patrol',self.bot.state==unreal.CombatBotState.PATROL)
                self.check('Guard holstered weapon after loss',not self.bot.get_editor_property('bWeaponDrawn'))
                self.check('Patrol resumed movement',self.bot.get_actor_location().distance(self.cover_origin)>50)
                self.place((-100,-650,95))
                self.bot.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(self.bot.get_actor_location(),self.player.get_actor_location()),True)
                self.advance('reacquire')
            elif self.phase=='reacquire' and self.bot.shot_count>self.cover_shots:
                self.check('Guard reacquired player and fired again',True)
                self.check('Reacquisition drew weapon',self.bot.get_editor_property('bWeaponDrawn'))
                self.check('Health and HUD remain synchronized',abs(self.player.hud.get_displayed_health_percent()-self.player.get_health()/self.player.get_max_health())<.001)
                self.advance('zero_health')
            elif self.phase=='zero_health':
                if self.player.get_health()<=0:
                    self.check('Health reaches exactly zero',self.player.get_health()==0)
                    self.check('Health bar reaches zero',self.player.hud.get_displayed_health_percent()==0)
                    self.check('Player is no longer alive',not self.player.is_alive())
                    self.dead_shots=self.bot.shot_count
                    self.advance('dead_guard')
                elif age>20:raise AssertionError('Continuous shots did not reduce Health to zero.')
            elif self.phase=='dead_guard' and age>2:
                self.check('Dead target cannot be shot again',not self.bot.request_shot())
                self.check('No extra shots after death',self.bot.shot_count==self.dead_shots)
                self.check('No negative health',self.player.get_health()==0)
                self.check('Final cue/shot parity',self.bot.cue_count==self.bot.shot_count)
                self.check('Final cooldown cadence',all(b-a>=1.249 for a,b in zip(list(self.bot.shot_times),list(self.bot.shot_times)[1:])))
                self.finish()
        except Exception:
            self.error=traceback.format_exc()
            self.finish()


def run():
    global RUN
    RUN=CombatValidation()
    return 'Running timed Play verification; wait for Docs/CombatGASValidation.json.'
