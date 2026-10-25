"""Lessons 11.3: reusable health and an isolated ThirdPerson character."""
import unreal
import maze_graph as m
from maze_graph import g,B,REAL,BOOL,ACTOR,ref,store,after,self_ref

def prepare():
    health=m.bp('BPC_Health',unreal.ActorComponent)
    m.var(health,'Health',REAL,'100')
    for name in ['IncreaseHealth','DecreaseHealth']:
        e=m.function(health,name);g.input_parameter(e,'Amount',REAL)
    g.compile_bp(health)
    char=m.bp('BP_MazeCharacter',source='/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter')
    m.var(char,'CurrentInteract',ACTOR)
    m.var(char,'bHasTrophy',BOOL,'false')
    m.var(char,'InteractCount',m.INT,'0',category='Diagnostics')
    m.component(char,'HealthComponent',health.generated_class())
    cdo=unreal.get_default_object(char.generated_class())
    capsule=cdo.capsule_component
    capsule.set_editor_property('generate_overlap_events',True)
    capsule.set_collision_response_to_channel(unreal.CollisionChannel.ECC_WORLD_DYNAMIC,unreal.CollisionResponseType.ECR_OVERLAP)
    capsule.set_collision_response_to_channel(unreal.CollisionChannel.ECC_VISIBILITY,unreal.CollisionResponseType.ECR_BLOCK)
    for name in ['RefreshInteraction','TryInteract','InitializeMazeCharacter','ReceiveHitDamage']:
        e=m.function(char,name)
        if name=='ReceiveHitDamage':g.input_parameter(e,'Amount',REAL)
    g.compile_bp(char)
    return True

def health():
    bp=m.asset('BPC_Health');g.clear_graph(bp)
    for name,operation in [('IncreaseHealth','Add_DoubleDouble'),('DecreaseHealth','Subtract_DoubleDouble')]:
        e=m.function(bp,name);amount=g.input_parameter(e,'Amount',REAL)
        positive=m.op(e,'FMax',amount,0)
        total=m.op(e,operation,ref(e,'Health'),positive)
        clamp=g.call(e,'/Script/Engine.KismetMathLibrary.FClamp');g.wire(total,g.pin(clamp,'Value'));g.value(clamp,'Min',0);g.value(clamp,'Max',100)
        m.ret(e,store(e,e.find_graph_entry_pin(),'Health',g.result(clamp)))
    m.finish(bp,{name:'Reusable health component. Ignore negative amounts and clamp Health to the closed range 0..100.' for name in ['IncreaseHealth','DecreaseHealth']})
    return True

def character():
    bp=m.asset('BP_MazeCharacter')
    e=m.function(bp,'RefreshInteraction');entry=store(e,e.find_graph_entry_pin(),'CurrentInteract',literal='None')
    overlaps=g.call(e,'/Script/Engine.Actor.GetOverlappingActors');entry=after(entry,overlaps)
    loop=e.add_macro_node('/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForEachLoopWithBreak')
    g.wire(g.pin(overlaps,'OverlappingActors',True),g.pin(loop,'Array'));g.wire(entry,g.pin(loop,'Exec'))
    does=g.call(e,'/Script/Engine.KismetSystemLibrary.DoesImplementInterface');g.wire(g.pin(loop,'Array Element',True),g.pin(does,'TestObject'));g.value(does,'Interface',m.asset('BPI_Interactable').generated_class().get_path_name())
    br=m.branch(e,g.pin(loop,'LoopBody',True),g.result(does))
    entry=store(e,g.pin(br,'then',True),'CurrentInteract',g.pin(loop,'Array Element',True));g.wire(entry,g.pin(loop,'Break'))
    m.ret(e,g.pin(loop,'Completed',True));g.compile_bp(bp)
    e=m.function(bp,'TryInteract');entry=after(e.find_graph_entry_pin(),m.own(e,bp,'RefreshInteraction'))
    entry=m.valid(e,ref(e,'CurrentInteract'),entry)
    overlap=g.call(e,'/Script/Engine.Actor.IsOverlappingActor');g.wire(ref(e,'CurrentInteract'),g.pin(overlap,'Other'))
    br=m.branch(e,entry,g.result(overlap));entry=g.pin(br,'then',True)
    from build_switchable_room import increment
    entry=increment(e,entry,'InteractCount');m.ret(e,after(entry,m.iface(e,ref(e,'CurrentInteract'))));g.compile_bp(bp)
    e=m.function(bp,'ReceiveHitDamage');amount=g.input_parameter(e,'Amount',REAL)
    entry=m.valid(e,ref(e,'HealthComponent'),e.find_graph_entry_pin())
    mode,entry=m.mode(e,entry)
    active=m.op(e,'Not_PreBool',m.member(e,'BP_MazeGameMode','bFinished',mode))
    br=m.branch(e,entry,active);entry=g.pin(br,'then',True)
    n=m.method(e,'BPC_Health','DecreaseHealth',ref(e,'HealthComponent'));g.wire(amount,g.pin(n,'Amount'));entry=after(entry,n)
    dead=m.op(e,'LessEqual_DoubleDouble',m.member(e,'BPC_Health','Health',ref(e,'HealthComponent')),0)
    br=m.branch(e,entry,dead);after(g.pin(br,'then',True),m.method(e,'BP_MazeGameMode','Lose',mode));g.compile_bp(bp)
    e=m.function(bp,'InitializeMazeCharacter');entry=e.find_graph_entry_pin();m.ret(e,m.timer(e,entry,'RefreshInteraction',.1,True));g.compile_bp(bp)
    e=g.graph(bp)
    # Keep every original movement / look / jump node and mapping intact.
    source=g.graph(unreal.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter'))
    original={(n.get_class().get_path_name(),n.get_name()) for n in source.list_all_nodes()}
    e.remove_nodes([n for n in e.list_all_nodes() if (n.get_class().get_path_name(),n.get_name()) not in original])
    add=next(n for n in e.list_all_nodes() if str(n.get_node_title())=='AddMappingContext')
    subsystem=g.pin(add,'self').list_connected_pins()[0]
    n=g.call(e,'/Script/EnhancedInput.EnhancedInputSubsystemInterface.AddMappingContext')
    g.wire(subsystem,g.pin(n,'self'));g.value(n,'MappingContext',m.path('IMC_Maze'));g.value(n,'Priority',1)
    entry=after(g.then(add),n);after(entry,m.own(e,bp,'InitializeMazeCharacter'))
    event=g.named_node(e,lambda s:'enhancedactionevents|' in s and s.endswith('ia_interact'),'IA_Interact event')
    g.wire(g.pin(event,'Started',True),m.own(e,bp,'TryInteract').find_execute_pin())
    for event_name in ['ReceiveActorBeginOverlap','ReceiveActorEndOverlap']:
        ev=g.event(bp,event_name);after(g.then(ev),m.own(e,bp,'RefreshInteraction'))
    ev=g.event(bp,'ReceiveAnyDamage');n=m.own(e,bp,'ReceiveHitDamage');g.wire(g.pin(ev,'Damage',True),g.pin(n,'Amount'));after(g.then(ev),n)
    ev=g.event(bp,'ReceiveEndPlay');m.clear_timer(e,g.then(ev),'RefreshInteraction')
    m.finish(bp,{'EventGraph':'Preserve ThirdPerson movement. Add a separate E mapping context. Started fires once per key press; overlaps refresh interactable references; AnyDamage routes to the reusable health component.',
      'RefreshInteraction':'Rebuild the current candidate from live overlaps. Ignore unrelated actors and recover when overlapping one object while leaving another.',
      'TryInteract':'Revalidate the target and overlap at the moment E is pressed, then dispatch BPI_Interactable.Interact.',
      'ReceiveHitDamage':'Apply damage only during an active round. Zero Health ends the round through GameMode.'})
    return True
