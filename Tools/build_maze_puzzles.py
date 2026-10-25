"""Lesson 11.4: controllable door, lever, timed pressure gate and items."""
import unreal
import maze_graph as m
from maze_graph import g,B,ref,store,after,self_ref

def prepare():
    parent=m.asset('BP_ControlActor').generated_class()
    for name in ['BP_Door','BP_Lever','BP_LiftingGate','BP_HealPickup']:m.bp(name,parent)
    for name in ['BP_PressurePlate','BP_Trophy','BP_WinZone','BP_MazeTurret']:m.bp(name)
    door=m.asset('BP_Door')
    m.var(door,'bUnlocked',m.BOOL,'false');m.var(door,'bOpen',m.BOOL,'false')
    m.mesh(door,'DoorPanel','Cube',(0,80,120),(.2,1.6,2.4),'Lighting/M_LightFixture','BlockAll');m.trigger(door,(150,170,140),(0,80,120))
    lever=m.asset('BP_Lever');m.var(lever,'ControlledActor',B.get_object_reference_type(parent),editable=True,category='Configuration');m.var(lever,'bActivated',m.BOOL,'false')
    m.mesh(lever,'LeverBase','Cube',(0,0,55),(.6,.6,1.1),'Lighting/M_LightFixture','BlockAll')
    m.mesh(lever,'LeverHandle','Cube',(0,0,125),(.16,.16,.7),'Lighting/M_SwitchCap');m.trigger(lever,(150,150,140))
    gate=m.asset('BP_LiftingGate');m.var(gate,'bDesiredOpen',m.BOOL,'false');m.var(gate,'bOpen',m.BOOL,'false')
    m.var(gate,'DelaySeconds',m.REAL,'3',True,'Configuration');m.var(gate,'OpenHeight',m.REAL,'320',True,'Configuration')
    m.mesh(gate,'GatePanel','Cube',(0,0,130),(.3,2.5,2.6),'Environment/M_LabRoom_Accent','BlockAll')
    m.function(gate,'ApplyGateState')
    plate=m.asset('BP_PressurePlate');m.var(plate,'ControlledActor',B.get_object_reference_type(parent),editable=True,category='Configuration')
    m.mesh(plate,'PlateSurface','Cube',(0,0,5),(1.5,1.5,.1),'Lighting/M_SwitchCap','BlockAll');m.trigger(plate,(80,80,60),(0,0,65))
    heal=m.asset('BP_HealPickup');m.var(heal,'HealAmount',m.REAL,'35',True,'Configuration');m.var(heal,'bConsumed',m.BOOL,'false')
    m.mesh(heal,'HealMesh','Sphere',(0,0,70),(.55,.55,.55),'Lighting/M_SwitchCap');m.trigger(heal,(110,110,110),(0,0,70))
    trophy=m.asset('BP_Trophy');m.mesh(trophy,'TrophyMesh','Sphere',(0,0,85),(.65,.65,.65),'Lighting/M_LampBulb_On');m.trigger(trophy,(90,90,100))
    exit=m.asset('BP_WinZone');m.mesh(exit,'ExitMarker','Cube',(0,0,3),(2.7,2.7,.06),'Examples/M_Example_Cyan');m.trigger(exit,(140,140,120))
    for name in ['BP_Door','BP_Lever','BP_LiftingGate','BP_PressurePlate','BP_HealPickup','BP_Trophy','BP_WinZone']:g.compile_bp(m.asset(name))
    return True

def door_and_lever():
    bp=m.asset('BP_Door');e=g.clear_graph(bp)
    control=g.event(bp,'Control');store(e,g.then(control),'bUnlocked',literal='true')
    ev=g.event(bp,'Interact');condition=m.op(e,'BooleanAND',ref(e,'bUnlocked'),m.op(e,'Not_PreBool',ref(e,'bOpen')))
    br=m.branch(e,g.then(ev),condition);entry=store(e,g.pin(br,'then',True),'bOpen',literal='true')
    rot=g.call(e,'/Script/Engine.KismetMathLibrary.MakeRotator');g.value(rot,'Yaw',90)
    n=g.call(e,'/Script/Engine.Actor.K2_AddActorLocalRotation');g.wire(g.result(rot),g.pin(n,'DeltaRotation'));after(entry,n)
    m.finish(bp,{'EventGraph':'The inherited Control event unlocks this door. Interact is ignored until unlocked and opens exactly once by rotating 90 degrees around the hinge origin.'})
    bp=m.asset('BP_Lever');e=g.clear_graph(bp);ev=g.event(bp,'Interact')
    br=m.branch(e,g.then(ev),m.op(e,'Not_PreBool',ref(e,'bActivated')))
    entry=m.valid(e,ref(e,'ControlledActor'),g.pin(br,'then',True));entry=store(e,entry,'bActivated',literal='true')
    after(entry,m.method(e,'BP_ControlActor','Control',ref(e,'ControlledActor')))
    m.finish(bp,{'EventGraph':'One E interaction activates the linked controllable actor. ControlledActor is assigned per placed instance; null links are safe.'})
    return True

def pressure_gate():
    bp=m.asset('BP_LiftingGate');e=g.clear_graph(bp);ev=g.event(bp,'Control')
    entry=store(e,g.then(ev),'bDesiredOpen',m.op(e,'Not_PreBool',ref(e,'bDesiredOpen')))
    # Same object/function timer replaces an earlier pending transition on quick re-entry.
    n=g.call(e,'/Script/Engine.KismetSystemLibrary.K2_SetTimer');g.wire(self_ref(e),g.pin(n,'Object'));g.value(n,'FunctionName','ApplyGateState');g.wire(ref(e,'DelaySeconds'),g.pin(n,'Time'));g.value(n,'bLooping','false');after(entry,n)
    ev=g.event(bp,'ReceiveEndPlay');m.clear_timer(e,g.then(ev),'ApplyGateState')
    e=m.function(bp,'ApplyGateState');entry=store(e,e.find_graph_entry_pin(),'bOpen',ref(e,'bDesiredOpen'))
    select=g.call(e,'/Script/Engine.KismetMathLibrary.SelectFloat');g.wire(ref(e,'OpenHeight'),g.pin(select,'A'));g.value(select,'B',0);g.wire(ref(e,'bDesiredOpen'),g.pin(select,'bPickA'))
    z=m.op(e,'Add_DoubleDouble',g.result(select),130)
    v=g.call(e,'/Script/Engine.KismetMathLibrary.MakeVector');g.wire(z,g.pin(v,'Z'))
    n=g.call(e,'/Script/Engine.SceneComponent.K2_SetRelativeLocation');g.wire(ref(e,'GatePanel'),g.pin(n,'self'));g.wire(g.result(v),g.pin(n,'NewLocation'));m.ret(e,after(entry,n))
    m.finish(bp,{'EventGraph':'Enter requests opening after DelaySeconds; exit requests closing after the same delay. Repeated transitions replace the pending timer instead of stacking callbacks.', 'ApplyGateState':'Apply the latest desired state to the actual blocking gate mesh. The base location stays fixed.'})
    bp=m.asset('BP_PressurePlate');e=g.clear_graph(bp)
    for name in ['ReceiveActorBeginOverlap','ReceiveActorEndOverlap']:
        ev=g.event(bp,name)
        player=g.call(e,'/Script/Engine.GameplayStatics.GetPlayerPawn');g.value(player,'PlayerIndex',0)
        condition=m.op(e,'EqualEqual_ObjectObject',g.pin(ev,'OtherActor',True),g.result(player))
        br=m.branch(e,g.then(ev),condition);entry=m.valid(e,ref(e,'ControlledActor'),g.pin(br,'then',True))
        after(entry,m.method(e,'BP_ControlActor','Control',ref(e,'ControlledActor')))
    m.finish(bp,{'EventGraph':'Only the player entering or leaving the plate toggles the linked gate request. Unrelated actors never activate it.'})
    return True

def items():
    bp=m.asset('BP_HealPickup');e=g.clear_graph(bp);ev=g.event(bp,'Interact')
    br=m.branch(e,g.then(ev),m.op(e,'Not_PreBool',ref(e,'bConsumed')))
    player,entry=m.player(e,g.pin(br,'then',True));entry=store(e,entry,'bConsumed',literal='true')
    health=m.member(e,'BP_MazeCharacter','HealthComponent',player)
    n=m.method(e,'BPC_Health','IncreaseHealth',health);g.wire(ref(e,'HealAmount'),g.pin(n,'Amount'));entry=after(entry,n)
    after(entry,g.call(e,'/Script/Engine.Actor.K2_DestroyActor'))
    m.finish(bp,{'EventGraph':'A single interaction heals through the reusable health component and consumes the pickup.'})
    bp=m.asset('BP_Trophy');e=g.clear_graph(bp);ev=g.event(bp,'ReceiveActorBeginOverlap')
    player,entry=m.cast(e,'BP_MazeCharacter',g.pin(ev,'OtherActor',True),g.then(ev))
    n=g.set_variable(e,'bHasTrophy',m.asset('BP_MazeCharacter').generated_class().get_path_name());g.wire(player,g.pin(n,'self'));g.value(n,'bHasTrophy','true');entry=after(entry,n)
    after(entry,g.call(e,'/Script/Engine.Actor.K2_DestroyActor'))
    m.finish(bp,{'EventGraph':'Only the Maze character can collect the trophy. Store ownership on the character before destroying the pickup.'})
    bp=m.asset('BP_WinZone');e=g.clear_graph(bp);ev=g.event(bp,'ReceiveActorBeginOverlap')
    player,entry=m.cast(e,'BP_MazeCharacter',g.pin(ev,'OtherActor',True),g.then(ev))
    br=m.branch(e,entry,m.member(e,'BP_MazeCharacter','bHasTrophy',player))
    mode,entry=m.mode(e,g.pin(br,'then',True));after(entry,m.method(e,'BP_MazeGameMode','Win',mode))
    m.finish(bp,{'EventGraph':'Entering the exit without the trophy does nothing. With the trophy, request victory from GameMode; it resolves the active round once.'})
    return True
