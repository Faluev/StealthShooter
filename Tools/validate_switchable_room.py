"""Validate practical 3.8 against actual actors in Play In Editor."""
import json
from pathlib import Path
import unreal

def actors():
    worlds=unreal.EditorLevelLibrary.get_pie_worlds(False)
    assert worlds,'Start Play on L_SwitchableRoom.'
    world=worlds[0]
    all_actors=unreal.GameplayStatics.get_all_actors_of_class(world,unreal.Actor)
    button=next(a for a in all_actors if a.get_class().get_name()=='BP_LightSwitch_C')
    lamps=sorted([a for a in all_actors if a.get_class().get_name()=='BP_SwitchableLamp_C'],key=lambda a:a.get_actor_label())
    pawn=unreal.GameplayStatics.get_player_pawn(world,0)
    return world,button,lamps,pawn

def run():
    world,button,lamps,pawn=actors()
    checks=[]
    def check(name,actual,expected=True):
        assert actual==expected,f'{name}: {actual!r} != {expected!r}'
        checks.append({'name':name,'passed':True})
    def state(expected,group=lamps,label=''):
        for index,lamp in enumerate(group,1):
            check(f'{label} lamp {index} interface query',lamp.call_method('IsSwitchOn'),expected)
            check(f'{label} lamp {index} Point Light',lamp.get_editor_property('LampLight').is_visible(),expected)
            check(f'{label} lamp {index} bulb',lamp.get_editor_property('Bulb').get_material(0).get_name(),'M_BulbOn' if expected else 'M_BulbOff')
    check('Four lamps',len(lamps),4)
    interface=unreal.load_asset('/Game/StealthShooter/Interaction/BPI_Switchable').generated_class()
    for actor in [button,*lamps]:check(actor.get_actor_label()+' implements BPI_Switchable',unreal.SystemLibrary.does_implement_interface(actor,interface))
    for lamp in lamps:check(lamp.get_actor_label()+' subscribed at Begin Play',lamp.get_editor_property('Bound'))
    check('Third Person pawn',pawn.get_class().get_name(),'BP_ThirdPersonCharacter_C')
    state(True,label='Initial')
    location=button.get_actor_location()
    original=pawn.get_actor_location()
    def position(x,y,z):pawn.set_actor_location(location+unreal.Vector(x,y,z),False,True)
    try:
        presses=button.get_editor_property('PressCount')
        position(-600,0,96);button.call_method('TryInteract')
        check('Outside radius rejects press',button.get_editor_property('PressCount'),presses)
        state(True,label='Outside')
        position(-120,0,96);button.call_method('TryInteract')
        check('Inside radius accepts press',button.get_editor_property('PressCount'),presses+1)
        check('Switch query after press',button.call_method('IsSwitchOn'),False)
        state(False,label='Inside')
        before=button.get_editor_property('BroadcastCount');button.call_method('SwitchOff')
        check('SwitchOff is idempotent',button.get_editor_property('BroadcastCount'),before)
        button.call_method('SwitchOn');state(True,label='Interface SwitchOn')
        before=button.get_editor_property('BroadcastCount');button.call_method('SwitchOn')
        check('SwitchOn is idempotent',button.get_editor_property('BroadcastCount'),before)
        position(200.1,0,150);before=button.get_editor_property('PressCount');button.call_method('TryInteract')
        check('Just outside spherical boundary',button.get_editor_property('PressCount'),before)
        position(200,0,150);button.call_method('TryInteract')
        check('Exact spherical boundary accepted',button.get_editor_property('PressCount'),before+1)
        state(False,label='Boundary')
        for lamp in lamps:
            lamp.call_method('BindToButton');lamp.call_method('BindToButton')
        previous=[lamp.get_editor_property('SwitchCount') for lamp in lamps]
        button.call_method('SwitchOn')
        for index,lamp in enumerate(lamps):check(f'Rebinding does not duplicate callback {index+1}',lamp.get_editor_property('SwitchCount'),previous[index]+1)
        state(True,label='Rebind')
        lamps[0].call_method('UnbindFromButton');button.call_method('SwitchOff')
        check('Unsubscribed lamp remains on',lamps[0].call_method('IsSwitchOn'))
        state(False,lamps[1:],'Other subscribers')
        lamps[0].call_method('BindToButton')
        check('Rejoined lamp syncs to switch',lamps[0].call_method('IsSwitchOn'),False)
        state(False,label='Rejoin')
        position(-120,0,96)
        for iteration in range(12):
            button.call_method('TryInteract')
            state(iteration%2==0,label='Repeat '+str(iteration+1))
        check('All subscribers still active',all(l.get_editor_property('Bound') for l in lamps))
    finally:
        pawn.set_actor_location(original,False,True)
        for lamp in lamps:
            lamp.call_method('BindToButton')
        button.call_method('SwitchOn')
    report={'map':'L_SwitchableRoom','engine':unreal.SystemLibrary.get_engine_version(),'checks':checks,'passed':len(checks)}
    path=Path(__file__).resolve().parents[1]/'Docs/SwitchableRoomValidation.json'
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return {'passed':len(checks)}

def run_lifecycle():
    world,button,lamps,pawn=actors()
    checks=[]
    lamp=lamps[0]
    lamp.call_method('UnbindFromButton')
    lamp.set_editor_property('ControlButton',None,notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
    lamp.call_method('BindToButton')
    assert not lamp.get_editor_property('Bound')
    checks.append({'name':'Missing button leaves lamp safely unbound','passed':True})
    lamp.call_method('SwitchOff');assert not lamp.get_editor_property('LampLight').is_visible()
    lamp.call_method('SwitchOn');assert lamp.get_editor_property('LampLight').is_visible()
    checks.append({'name':'Unbound lamp still implements its interface','passed':True})
    lamp.set_editor_property('ControlButton',button,notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
    lamp.call_method('BindToButton');assert lamp.get_editor_property('Bound')
    checks.append({'name':'Restoring button reference permits rebinding','passed':True})
    lamp.destroy_actor()
    assert not unreal.SystemLibrary.is_valid(lamp)
    checks.append({'name':'Subscriber destroyed during Play','passed':True})
    button.call_method('SwitchOff')
    assert all(not a.get_editor_property('LampLight').is_visible() for a in lamps[1:])
    button.call_method('SwitchOn')
    assert all(a.get_editor_property('LampLight').is_visible() for a in lamps[1:])
    checks.append({'name':'Remaining subscribers work after subscriber destruction','passed':True})
    path=Path(__file__).resolve().parents[1]/'Docs/SwitchableRoomValidation.json'
    report=json.loads(path.read_text(encoding='utf-8'));report['checks'].extend(checks);report['passed']=len(report['checks'])
    path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    return {'lifecycle':len(checks),'total':report['passed']}
