"""Run actual Play scenarios for lessons 11.3-11.5, including level reloads."""
import json,time,traceback
from pathlib import Path
import unreal

REPORT=Path(unreal.Paths.project_dir())/'Docs/MazeValidation113-115.json'
checks=[]
stage=0
started=0
handle=None
wall_started=0
world=pawn=gm=health=hud=None
actors={}
baseline={}

def check(name,value,detail=None):
    checks.append({'check':name,'passed':bool(value),'detail':detail})
    if not value:raise AssertionError(name+': '+str(detail))
def capture():
    global world,pawn,gm,health,hud,actors
    worlds=unreal.EditorLevelLibrary.get_pie_worlds(False)
    if not worlds:return False
    world=worlds[0];pawn=unreal.GameplayStatics.get_player_pawn(world,0);gm=unreal.GameplayStatics.get_game_mode(world)
    if not pawn or not gm or gm.get_class().get_name()!='BP_MazeGameMode_C':return False
    health=pawn.get_editor_property('HealthComponent');hud=gm.get_editor_property('HUDWidget')
    actors={a.get_actor_label():a for a in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.Actor)}
    return bool(health and hud)
def prop(a,name):return a.get_editor_property(name)
def hp():return prop(health,'Health')
def move(x,y,z=96):
    pawn.character_movement.stop_movement_immediately();pawn.set_actor_location(unreal.Vector(x,y,z),False,True)
def clock():return unreal.GameplayStatics.get_time_seconds(world)
def advance(value):
    global stage,started
    stage=value;started=clock()
def interact():pawn.call_method('TryInteract')
def invoke_health(name,amount):health.call_method(name,args=(amount,))
def result_class():return prop(gm,'ResultWidget').get_class().get_name()
def restart(next_stage):
    global stage
    baseline['old_mode']=gm;baseline['travel_started']=time.monotonic()
    stage=next_stage;prop(gm,'ResultWidget').call_method('OnRestartClicked')
def finish():
    global handle
    if handle:unreal.unregister_slate_post_tick_callback(handle);handle=None
    REPORT.write_text(json.dumps({'map':'L_MazeMechanics','mode':'Play In Editor','checks':checks,'passed':sum(c['passed'] for c in checks),'failed':sum(not c['passed'] for c in checks),'elapsed_seconds':round(time.monotonic()-wall_started,2)},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    unreal.log('MAZE_LESSONS_TESTS_FINISHED '+str(REPORT))

def tick(delta):
    global stage,started,baseline
    try:
        if time.monotonic()-wall_started>300:raise TimeoutError('Play scenarios timed out')
        if stage in [20,22,24]:
            if not capture() or gm==baseline['old_mode']:return
            if clock()<.5:return
            check('Reload creates a new round '+str(stage),not prop(gm,'bFinished'))
            check('Reload restores full health '+str(stage),hp()==100)
            check('Reload clears trophy '+str(stage),not prop(pawn,'bHasTrophy'))
            check('Reload restores closed door '+str(stage),not prop(actors['MazeDoor'],'bOpen') and not prop(actors['MazeDoor'],'bUnlocked'))
            check('Reload recreates HUD '+str(stage),hud.call_method('IsInViewport'))
            check('Reload restores game input cursor '+str(stage),not prop(unreal.GameplayStatics.get_player_controller(world,0),'show_mouse_cursor'))
            if stage==20:
                gm.set_editor_property('RoundDuration',clock()+.5,notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER);advance(21)
            elif stage==22:
                invoke_health('DecreaseHealth',95);check('Damage loss setup at 5 HP',hp()==5)
                unreal.GameplayStatics.apply_damage(pawn,10,None,actors['MazeTurret'],unreal.DamageType)
                advance(23)
            else:
                check('Restart restores the round duration',prop(gm,'RemainingTime')>175)
                finish()
            return
        elapsed=clock()-started
        if stage==0 and elapsed>.2:
            check('Custom character spawned',pawn.get_class().get_name()=='BP_MazeCharacter_C')
            check('Reusable health component attached',health.get_class().get_name()=='BPC_Health_C')
            check('Health starts at 100',hp()==100)
            check('HUD is on screen',hud.call_method('IsInViewport'))
            check('Round timer runs',0<prop(gm,'RemainingTime')<1000)
            check('Exit without trophy does not win',not prop(gm,'bFinished') and not prop(pawn,'bHasTrophy'))
            check('Trophy image initially hidden',prop(hud,'TrophyIcon').get_visibility()==unreal.SlateVisibility.HIDDEN)
            invoke_health('DecreaseHealth',30);check('Damage amount subtracts health',hp()==70)
            invoke_health('IncreaseHealth',1000);check('Healing clamps at 100',hp()==100)
            invoke_health('DecreaseHealth',1000);check('Damage clamps at zero',hp()==0)
            invoke_health('IncreaseHealth',1000)
            invoke_health('DecreaseHealth',-30);invoke_health('IncreaseHealth',-30);check('Negative amounts are ignored',hp()==100)
            invoke_health('DecreaseHealth',30);advance(1)
        elif stage==1 and elapsed>.25:
            check('HUD health bar reflects component',abs(prop(prop(hud,'HealthBar'),'percent')-.7)<.001)
            count=prop(pawn,'InteractCount');interact();check('E action outside interactable areas is safe',prop(pawn,'InteractCount')==count)
            move(60,-620);advance(2)
        elif stage==2 and elapsed>.25:
            interact();check('Locked door does not open',not prop(actors['MazeDoor'],'bOpen'))
            check('Door still needs the lever',not prop(actors['MazeDoor'],'bUnlocked'))
            move(-470,-950);advance(3)
        elif stage==3 and elapsed>.25:
            interact();check('Lever receives interface interaction',prop(actors['MazeLever'],'bActivated'))
            check('Lever unlocks its linked door',prop(actors['MazeDoor'],'bUnlocked'))
            interact();move(60,-620);advance(4)
        elif stage==4 and elapsed>.25:
            interact();check('Unlocked door opens on its own interaction',prop(actors['MazeDoor'],'bOpen'))
            check('Door rotates by 90 degrees',abs(actors['MazeDoor'].get_actor_rotation().yaw-90)<.01)
            interact();check('Repeated door interaction cannot rotate it twice',abs(actors['MazeDoor'].get_actor_rotation().yaw-90)<.01)
            move(850,900);advance(5)
        elif stage==5 and elapsed>.25:
            interact();check('Healing pickup restores health',hp()==100)
            check('Healing pickup is consumed',not unreal.SystemLibrary.is_valid(actors['MazeHeal']))
            interact();check('Consumed interactable reference is safe',hp()==100)
            move(-350,500,106);advance(6)
        elif stage==6 and elapsed>.6:
            check('Plate does not open the gate immediately',not prop(actors['MazeLiftingGate'],'bOpen'))
            advance(7)
        elif stage==7 and elapsed>2.8:
            check('Plate opens the gate after three seconds',prop(actors['MazeLiftingGate'],'bOpen'))
            check('Gate blocking mesh physically lifts',prop(prop(actors['MazeLiftingGate'],'GatePanel'),'relative_location').z>440)
            move(-650,500);advance(8)
        elif stage==8 and elapsed>.6:
            check('Gate stays open during the exit delay',prop(actors['MazeLiftingGate'],'bOpen'));advance(9)
        elif stage==9 and elapsed>2.8:
            check('Gate closes after leaving the plate',not prop(actors['MazeLiftingGate'],'bOpen'))
            check('Closed gate returns to its initial position',abs(prop(prop(actors['MazeLiftingGate'],'GatePanel'),'relative_location').z-130)<.01)
            move(-350,500,106);advance(10)
        elif stage==10 and elapsed>.5:move(-650,500);advance(11)
        elif stage==11 and elapsed>.5:move(-350,500,106);advance(12)
        elif stage==12 and elapsed>3.4:
            check('Rapid plate re-entry keeps the latest open request',prop(actors['MazeLiftingGate'],'bOpen'))
            move(-650,500);baseline['shots']=prop(actors['MazeTurret'],'ShotCount');move(1200,0);advance(13)
        elif stage==13 and elapsed>2.2:
            check('Turret detects an exposed player',prop(actors['MazeTurret'],'bHasTarget'))
            check('Turret fires real shots',prop(actors['MazeTurret'],'ShotCount')>baseline['shots'])
            check('Turret ApplyDamage reaches player health',0<hp()<100)
            baseline['hp']=hp();baseline['shots']=prop(actors['MazeTurret'],'ShotCount');move(950,300);advance(14)
        elif stage==14 and elapsed>2.2:
            check('Cover blocks the turret visibility trace',not prop(actors['MazeTurret'],'bHasTarget'))
            check('Turret does not shoot through cover',prop(actors['MazeTurret'],'ShotCount')==baseline['shots'])
            check('Cover prevents further health loss',hp()==baseline['hp'])
            move(1350,800);advance(15)
        elif stage==15 and elapsed>.3:
            check('Trophy overlap sets character ownership',prop(pawn,'bHasTrophy'))
            check('Trophy pickup disappears',not unreal.SystemLibrary.is_valid(actors['MazeTrophy']))
            check('HUD displays the trophy image',prop(hud,'TrophyIcon').get_visibility()==unreal.SlateVisibility.VISIBLE)
            move(-900,-700);advance(16)
        elif stage==16 and elapsed>.3:
            check('Returning trophy to exit wins',prop(gm,'bFinished') and prop(gm,'bWon'))
            check('Victory screen appears',result_class()=='WBP_MazeWin_C' and prop(gm,'ResultWidget').call_method('IsInViewport'))
            check('Gameplay HUD is removed on result',not hud.call_method('IsInViewport'))
            check('Result screen shows mouse cursor',prop(unreal.GameplayStatics.get_player_controller(world,0),'show_mouse_cursor'))
            baseline['remaining']=prop(gm,'RemainingTime');baseline['result']=prop(gm,'ResultWidget');baseline['hp']=hp()
            gm.call_method('Lose');unreal.GameplayStatics.apply_damage(pawn,100,None,actors['MazeTurret'],unreal.DamageType);advance(17)
        elif stage==17 and elapsed>.5:
            check('Finished round outcome is idempotent',prop(gm,'bWon') and prop(gm,'ResultWidget')==baseline['result'])
            check('Round clock stops after victory',prop(gm,'RemainingTime')==baseline['remaining'])
            check('Finished round ignores later damage',hp()==baseline['hp']);restart(20)
        elif stage==21 and elapsed>1:
            check('Time expiration loses the round',prop(gm,'bFinished') and not prop(gm,'bWon'))
            check('Timeout displays loss screen',result_class()=='WBP_MazeLose_C')
            check('Remaining time clamps at zero',prop(gm,'RemainingTime')==0);restart(22)
        elif stage==23 and elapsed>.3:
            check('Lethal AnyDamage clamps health to zero',hp()==0)
            check('Lethal damage loses the round',prop(gm,'bFinished') and not prop(gm,'bWon'))
            check('Damage loss displays the loss screen',result_class()=='WBP_MazeLose_C');restart(24)
    except Exception as exc:
        if not checks or checks[-1]['passed']:checks.append({'check':'Scenario execution','passed':False,'detail':traceback.format_exc()})
        finish()

def run():
    global handle,started,wall_started
    assert capture(),'Start actual Play on L_MazeMechanics first'
    gm.set_editor_property('RoundDuration',1000,notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
    unreal.GameplayStatics.get_player_controller(world,0).set_ignore_look_input(True)
    started=clock();wall_started=time.monotonic();handle=unreal.register_slate_post_tick_callback(tick)
    return 'Maze scenarios started'
