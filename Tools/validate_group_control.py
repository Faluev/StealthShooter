"""Runtime checks for the UMG group-control map. Run only in Play In Editor."""
import json
from pathlib import Path
import unreal
from project_paths import load_asset,resolve_reference
ROOT='/Game/StealthShooter/GroupControl'
REPORT=Path(unreal.Paths.project_dir())/'Docs/GroupControlValidation.json'

def actors():
    worlds=unreal.EditorLevelLibrary.get_pie_worlds(False);assert worlds,'Start Play first'
    world=worlds[0]
    buttons=sorted(unreal.GameplayStatics.get_all_actors_of_class(world,load_asset(ROOT+'/BP_GroupSwitch').generated_class()),key=lambda a:a.get_actor_label())
    pawn=unreal.GameplayStatics.get_player_pawn(world,0)
    return world,buttons,pawn

def run():
    world,buttons,pawn=actors();checks=[]
    initial_targets={b:list(b.get_editor_property('SwitchTargets')) for b in buttons}
    def check(name,condition):
        checks.append({'name':name,'passed':bool(condition)})
        assert condition,name
    def update():
        for b in buttons:b.call_method('UpdateProximity')
    def move(b,offset):pawn.set_actor_location(b.get_actor_location()+unreal.Vector(*offset),False,True);update()
    def state(b,on):
        targets=b.get_editor_property('SwitchTargets')
        return b.call_method('IsSwitchOn')==on and all(t.call_method('IsSwitchOn')==on and t.get_editor_property('LampLight').get_editor_property('visible')==on for t in targets if t)
    bpi=load_asset('/Game/StealthShooter/Interaction/BPI_Switchable').generated_class()
    check('Three group switches',len(buttons)==3)
    check('Original ThirdPerson pawn',pawn.get_class().get_name()=='BP_ThirdPersonCharacter_C')
    for b in buttons:b.call_method('SwitchOn')
    try:
        for b in buttons:
            name=b.get_actor_label();ui=b.get_editor_property('ControlWidget');targets=list(b.get_editor_property('SwitchTargets'))
            check(name+' implements BPI_Switchable',unreal.SystemLibrary.does_implement_interface(b,bpi))
            check(name+' has two configured targets',len(targets)==2)
            check(name+' targets implement interface',all(unreal.SystemLibrary.does_implement_interface(t,bpi) for t in targets))
            check(name+' widget knows its owning switch',ui.get_editor_property('OwnerSwitch')==b)
            move(b,(-450,0,96))
            check(name+' panel hidden outside radius',not ui.call_method('IsInViewport'))
            ui.call_method('OnDisableClicked');check(name+' stale widget action rejected',state(b,True))
            move(b,(-120,0,96))
            check(name+' panel appears inside radius',ui.call_method('IsInViewport'))
            check(name+' no other group panel visible',sum(x.get_editor_property('ControlWidget').call_method('IsInViewport') for x in buttons)==1)
            ui.call_method('OnDisableClicked');check(name+' widget turns group off',state(b,False))
            check(name+' other groups remain on',all(state(x,True) for x in buttons if x!=b))
            check(name+' state label updated',str(ui.get_editor_property('StatusText').get_text()).endswith('выключена'))
            check(name+' redundant Off disabled',not ui.get_editor_property('ButtonOff').get_is_enabled() and ui.get_editor_property('ButtonOn').get_is_enabled())
            ui.call_method('OnEnableClicked');check(name+' widget turns group on',state(b,True))
            for cycle in range(3):ui.call_method('OnDisableClicked');ui.call_method('OnEnableClicked')
            check(name+' repeated cycles preserve state',state(b,True))
            move(b,(-450,0,96));check(name+' panel removed after exit',not ui.call_method('IsInViewport'))
            move(b,(-120,0,96));check(name+' reentry reuses same widget',b.get_editor_property('ControlWidget')==ui and ui.call_method('IsInViewport'))
        b=buttons[0];original=list(b.get_editor_property('SwitchTargets'))
        b.set_editor_property('SwitchTargets',[],notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER);b.call_method('SwitchOff');check('Empty target array is safe',not b.call_method('IsSwitchOn'))
        b.set_editor_property('SwitchTargets',[None]+original,notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER);b.call_method('SwitchOff');check('Null target is skipped',state(b,False))
        b.set_editor_property('SwitchTargets',original+[buttons[1].get_editor_property('SwitchTargets')[0]],notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER);b.call_method('SwitchOff')
        check('Array additions are processed',not buttons[1].get_editor_property('SwitchTargets')[0].call_method('IsSwitchOn'))
        b.set_editor_property('SwitchTargets',original,notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
        for b in buttons:b.call_method('SwitchOn')
        move(buttons[1],(-550,0,96));check('All panels removed away from consoles',not any(b.get_editor_property('ControlWidget').call_method('IsInViewport') for b in buttons))
        pc=unreal.GameplayStatics.get_player_controller(world,0);check('Cursor hidden after leaving',not pc.get_editor_property('show_mouse_cursor'))
    finally:
        for b in buttons:
            b.set_editor_property('SwitchTargets',initial_targets[b],notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
            b.call_method('SwitchOn')
        pawn.set_actor_location(unreal.Vector(-550,0,96),False,True);update()
    result={'map':'L_GroupControl','checks':checks,'passed':sum(x['passed'] for x in checks)}
    REPORT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return {'passed':result['passed']}
