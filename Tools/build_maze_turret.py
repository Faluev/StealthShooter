"""Lesson 11.4: sector patrol, visibility traces and real damage."""
import unreal
import maze_graph as m
from maze_graph import g,ref,store,after,self_ref

def location(e):return g.result(g.call(e,'/Script/Engine.Actor.K2_GetActorLocation'))
def target(e):
    n=g.call(e,'/Script/Engine.GameplayStatics.GetPlayerPawn');g.value(n,'PlayerIndex',0);return g.result(n)
def target_location(e):
    n=g.call(e,'/Script/Engine.Actor.K2_GetActorLocation');g.wire(target(e),g.pin(n,'self'));return g.result(n)
def set_yaw(e,entry,yaw):
    rot=g.call(e,'/Script/Engine.KismetMathLibrary.MakeRotator');g.wire(yaw,g.pin(rot,'Yaw'))
    smooth=g.call(e,'/Script/Engine.KismetMathLibrary.RInterpTo');g.wire(g.result(g.call(e,'/Script/Engine.Actor.K2_GetActorRotation')),g.pin(smooth,'Current'));g.wire(g.result(rot),g.pin(smooth,'Target'));g.value(smooth,'DeltaTime',.1);g.value(smooth,'InterpSpeed',5)
    n=g.call(e,'/Script/Engine.Actor.K2_SetActorRotation');g.wire(g.result(smooth),g.pin(n,'NewRotation'));return after(entry,n)

def prepare():
    bp=m.bp('BP_MazeTurret')
    for n,t,d,editable in [('SearchDistance',m.REAL,'1400',True),('RotationSpeed',m.REAL,'45',True),('ShotInterval',m.REAL,'1',True),('Damage',m.REAL,'10',True),('bHasTarget',m.BOOL,'false',False),('InitialYaw',m.REAL,'0',False),('PatrolOffset',m.REAL,'0',False),('bPatrolRight',m.BOOL,'true',False),('NextShotTime',m.REAL,'0',False),('ShotCount',m.INT,'0',False)]:
        m.var(bp,n,t,d,editable,'Configuration' if editable else 'State')
    m.mesh(bp,'TurretBase','Cylinder',(0,0,50),(1.1,1.1,1),'Lighting/M_LightFixture','BlockAll')
    m.mesh(bp,'TurretHead','Sphere',(0,0,125),(.8,.8,.65),'Environment/M_LabRoom_Accent')
    m.mesh(bp,'Barrel','Cube',(65,0,135),(1.25,.18,.18),'Lighting/M_LightFixture')
    light=m.component(bp,'MuzzleLight',unreal.PointLightComponent);light.set_editor_property('relative_location',unreal.Vector(130,0,135));light.set_mobility(unreal.ComponentMobility.MOVABLE);light.set_editor_property('intensity',1000);light.set_editor_property('attenuation_radius',280);light.set_light_color(unreal.LinearColor(1,.3,.05));light.set_visibility(False)
    for name in ['CanSeePlayer','Patrol','TrackPlayer','TryShoot','ClearFlash','UpdateTurret','StartTurret']:
        e=m.function(bp,name)
        if name=='CanSeePlayer':g.output_parameter(e,'bVisible',m.BOOL)
    g.compile_bp(bp);return True

def graphs():
    bp=m.asset('BP_MazeTurret')
    e=m.function(bp,'CanSeePlayer');player,entry=m.player(e,e.find_graph_entry_pin())
    failure=g.output_parameter(e,'bVisible',m.BOOL);g.value(failure,'bVisible','false')
    distance=g.call(e,'/Script/Engine.Actor.GetDistanceTo');g.wire(player,g.pin(distance,'OtherActor'))
    br=m.branch(e,entry,m.op(e,'LessEqual_DoubleDouble',g.result(distance),ref(e,'SearchDistance')));g.wire(g.pin(br,'else',True),failure.find_execute_pin());entry=g.pin(br,'then',True)
    direction=g.call(e,'/Script/Engine.KismetMathLibrary.GetDirectionUnitVector');g.wire(location(e),g.pin(direction,'From'));g.wire(target_location(e),g.pin(direction,'To'))
    dot=m.op(e,'Dot_VectorVector',g.result(g.call(e,'/Script/Engine.Actor.GetActorForwardVector')),g.result(direction))
    br=m.branch(e,entry,m.op(e,'GreaterEqual_DoubleDouble',dot,.5));g.wire(g.pin(br,'else',True),failure.find_execute_pin());entry=g.pin(br,'then',True)
    start=g.call(e,'/Script/Engine.SceneComponent.K2_GetComponentLocation');g.wire(ref(e,'MuzzleLight'),g.pin(start,'self'))
    trace=g.call(e,'/Script/Engine.KismetSystemLibrary.LineTraceSingle');g.wire(g.result(start),g.pin(trace,'Start'));g.wire(target_location(e),g.pin(trace,'End'));g.value(trace,'TraceChannel','TraceTypeQuery1');g.value(trace,'bIgnoreSelf','true');g.value(trace,'DrawDebugType','None');entry=after(entry,trace)
    hit=g.call(e,'/Script/Engine.GameplayStatics.BreakHitResult');g.wire(g.pin(trace,'OutHit',True),g.pin(hit,'Hit'))
    result=e.add_return_node();g.wire(m.op(e,'EqualEqual_ObjectObject',g.pin(hit,'HitActor',True),player),g.pin(result,'bVisible'));g.wire(entry,result.find_execute_pin());g.compile_bp(bp)
    e=m.function(bp,'TrackPlayer');look=g.call(e,'/Script/Engine.KismetMathLibrary.FindLookAtRotation');g.wire(location(e),g.pin(look,'Start'));g.wire(target_location(e),g.pin(look,'Target'))
    split=g.call(e,'/Script/Engine.KismetMathLibrary.BreakRotator');g.wire(g.result(look),g.pin(split,'InRot'));m.ret(e,set_yaw(e,e.find_graph_entry_pin(),g.pin(split,'Yaw',True)));g.compile_bp(bp)
    e=m.function(bp,'Patrol');direction=g.call(e,'/Script/Engine.KismetMathLibrary.SelectFloat');g.value(direction,'A',1);g.value(direction,'B',-1);g.wire(ref(e,'bPatrolRight'),g.pin(direction,'bPickA'))
    step=m.op(e,'Multiply_DoubleDouble',m.op(e,'Multiply_DoubleDouble',ref(e,'RotationSpeed'),.1),g.result(direction))
    clamp=g.call(e,'/Script/Engine.KismetMathLibrary.FClamp');g.wire(m.op(e,'Add_DoubleDouble',ref(e,'PatrolOffset'),step),g.pin(clamp,'Value'));g.value(clamp,'Min',-60);g.value(clamp,'Max',60)
    entry=store(e,e.find_graph_entry_pin(),'PatrolOffset',g.result(clamp))
    br=m.branch(e,entry,m.op(e,'GreaterEqual_DoubleDouble',ref(e,'PatrolOffset'),60))
    entry=store(e,g.pin(br,'then',True),'bPatrolRight',literal='false')
    br2=m.branch(e,entry,m.op(e,'LessEqual_DoubleDouble',ref(e,'PatrolOffset'),-60));g.wire(g.pin(br,'else',True),br2.find_execute_pin())
    entry=store(e,g.pin(br2,'then',True),'bPatrolRight',literal='true')
    n=g.call(e,'/Script/Engine.Actor.K2_SetActorRotation')
    rotation=g.call(e,'/Script/Engine.KismetMathLibrary.MakeRotator');g.wire(m.op(e,'Add_DoubleDouble',ref(e,'InitialYaw'),ref(e,'PatrolOffset')),g.pin(rotation,'Yaw'))
    g.wire(g.result(rotation),g.pin(n,'NewRotation'));g.wire(entry,n.find_execute_pin());g.wire(g.pin(br2,'else',True),n.find_execute_pin());m.ret(e,g.then(n));g.compile_bp(bp)
    e=m.function(bp,'ClearFlash');n=g.call(e,'/Script/Engine.SceneComponent.SetVisibility');g.wire(ref(e,'MuzzleLight'),g.pin(n,'self'));g.value(n,'bNewVisibility','false');m.ret(e,after(e.find_graph_entry_pin(),n));g.compile_bp(bp)
    e=m.function(bp,'PlayShotFlash');n=g.call(e,'/Script/Engine.SceneComponent.SetVisibility');g.wire(ref(e,'MuzzleLight'),g.pin(n,'self'));g.value(n,'bNewVisibility','true');entry=after(e.find_graph_entry_pin(),n);m.ret(e,m.timer(e,entry,'ClearFlash',.08));g.compile_bp(bp)
    e=m.function(bp,'TryShoot');mode,entry=m.mode(e,e.find_graph_entry_pin())
    active=m.op(e,'Not_PreBool',m.member(e,'BP_MazeGameMode','bFinished',mode))
    ready=m.op(e,'GreaterEqual_DoubleDouble',m.now(e),ref(e,'NextShotTime'));br=m.branch(e,entry,m.op(e,'BooleanAND',active,ready));entry=g.pin(br,'then',True)
    see=m.own(e,bp,'CanSeePlayer');entry=after(entry,see);br=m.branch(e,entry,g.pin(see,'bVisible',True));entry=g.pin(br,'then',True)
    entry=store(e,entry,'NextShotTime',m.op(e,'Add_DoubleDouble',m.now(e),m.op(e,'FMax',ref(e,'ShotInterval'),.1)))
    damage=g.call(e,'/Script/Engine.GameplayStatics.ApplyDamage');g.wire(target(e),g.pin(damage,'DamagedActor'));g.wire(ref(e,'Damage'),g.pin(damage,'BaseDamage'));g.wire(self_ref(e),g.pin(damage,'DamageCauser'));entry=after(entry,damage)
    from build_switchable_room import increment
    entry=increment(e,entry,'ShotCount')
    m.ret(e,after(entry,m.own(e,bp,'PlayShotFlash')));g.compile_bp(bp)
    e=m.function(bp,'UpdateTurret');see=m.own(e,bp,'CanSeePlayer');entry=after(e.find_graph_entry_pin(),see);entry=store(e,entry,'bHasTarget',g.pin(see,'bVisible',True));br=m.branch(e,entry,ref(e,'bHasTarget'))
    entry=after(g.pin(br,'then',True),m.own(e,bp,'TrackPlayer'));m.ret(e,after(entry,m.own(e,bp,'TryShoot')));m.ret(e,after(g.pin(br,'else',True),m.own(e,bp,'Patrol')));g.compile_bp(bp)
    e=m.function(bp,'StartTurret');rot=g.call(e,'/Script/Engine.KismetMathLibrary.BreakRotator');g.wire(g.result(g.call(e,'/Script/Engine.Actor.K2_GetActorRotation')),g.pin(rot,'InRot'))
    entry=store(e,e.find_graph_entry_pin(),'InitialYaw',g.pin(rot,'Yaw',True));m.ret(e,m.timer(e,entry,'UpdateTurret',.1,True));g.compile_bp(bp)
    e=g.clear_graph(bp);ev=g.event(bp,'ReceiveBeginPlay');after(g.then(ev),m.own(e,bp,'StartTurret'))
    ev=g.event(bp,'ReceiveEndPlay');entry=m.clear_timer(e,g.then(ev),'UpdateTurret');m.clear_timer(e,entry,'ClearFlash')
    m.finish(bp,{'CanSeePlayer':'Range + forward sector + Visibility trace. A wall or closed door blocks the actual shot; self is ignored.', 'Patrol':'Sweep a configurable sector around the placed initial yaw.', 'TrackPlayer':'Use native LookAt and rotation interpolation while the player is visible.', 'TryShoot':'Rate-limited ApplyDamage reaches the Maze character health component. Finished rounds cannot receive new shots.', 'UpdateTurret':'Choose patrol or tracking from the current visibility result, then request a shot only while tracking.'})
    return True
