"""Build practical 10.7 using navigation and CharacterMovement only."""
import unreal
import lab_graph as g
from build_blueprint_lab import variable, ref, store, after
from build_switchable_room import component, self_ref, increment

B=unreal.BlueprintEditorLibrary
PATH='/Game/StealthShooter/Movement/Patrol/BP_BoundedPatrol'
MAP='/Game/StealthShooter/Maps/L_BoundedPatrol'
MATH='/Script/Engine.KismetMathLibrary.'
REAL=B.get_basic_type_by_name('real')
BOOL=B.get_basic_type_by_name('bool')
INT=B.get_basic_type_by_name('int')
VECTOR=B.get_struct_type(unreal.Vector.static_struct())

def own(e,bp,name):return g.call(e,bp.generated_class().get_path_name()+':'+name)
def op(e,name,a,b):
    n=g.call(e,MATH+name)
    for key,val in [('A',a),('B',b)]:
        if hasattr(val,'is_valid'):g.wire(val,g.pin(n,key))
        else:g.value(n,key,val)
    return g.result(n)
def location(e):return g.result(g.call(e,'/Script/Engine.Actor.K2_GetActorLocation'))
def ret(e,entry):
    n=e.add_return_node();g.wire(entry,n.find_execute_pin());return n
def branch(e,entry,condition):
    n=e.add_branch_node();g.wire(entry,n.find_execute_pin());g.wire(condition,g.pin(n,'Condition'));return n

def prepare():
    bp=unreal.load_asset(PATH) or B.create_blueprint_asset_with_parent(PATH,unreal.Character)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    for name,kind,value,editable in [
        ('Speed',REAL,'220',True),('MinX',REAL,'-900',True),('MaxX',REAL,'900',True),
        ('MinY',REAL,'-800',True),('MaxY',REAL,'800',True),
        ('TargetLocation',VECTOR,'(X=0,Y=0,Z=0)',False),
        ('bNeedsTarget',BOOL,'true',False),('bReturning',BOOL,'false',False),
        ('MoveRequests',INT,'0',False),('CompletedMoves',INT,'0',False),
        ('FailedMoves',INT,'0',False),('BoundaryTurns',INT,'0',False)]:
        variable(bp,name,kind,value,editable)
        B.set_blueprint_variable_category(bp,name,'Patrol|Configuration' if editable else 'Patrol|Diagnostics' if kind==INT else 'Patrol|State')
    for name in ['ContainsPoint','SampleDestination','ChooseDestination','RefreshPatrol','ConfigureMovement','RequestDestination','RestartPatrol']:
        g.new_function(bp,name)
    e=g.clear_graph(bp);e.add_custom_event_node('MoveToTarget')
    g.compile_bp(bp)
    cdo=unreal.get_default_object(bp.generated_class())
    cdo.set_editor_property('auto_possess_ai',unreal.AutoPossessAI.PLACED_IN_WORLD_OR_SPAWNED)
    cdo.set_editor_property('ai_controller_class',unreal.AIController.static_class())
    cdo.set_editor_property('use_controller_rotation_yaw',False)
    cdo.capsule_component.set_capsule_size(34,60)
    movement=cdo.character_movement
    movement.set_editor_property('orient_rotation_to_movement',True)
    movement.set_editor_property('rotation_rate',unreal.Rotator(yaw=540))
    movement.set_editor_property('max_walk_speed',220)
    movement.set_editor_property('max_acceleration',1200)
    movement.set_editor_property('braking_deceleration_walking',1400)
    body=component(bp,'PatrolBody',unreal.StaticMeshComponent)
    body.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cylinder'))
    body.set_editor_property('relative_scale3d',unreal.Vector(.6,.6,.65))
    body.set_editor_property('relative_location',unreal.Vector(0,0,-20))
    body.set_collision_profile_name('NoCollision')
    body.set_material(0,unreal.load_asset('/Game/StealthShooter/MaterialLibrary/Examples/M_Example_Cyan'))
    nose=component(bp,'DirectionMarker',unreal.StaticMeshComponent)
    nose.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cone'))
    nose.set_editor_property('relative_location',unreal.Vector(35,0,0))
    nose.set_editor_property('relative_rotation',unreal.Rotator(pitch=90))
    nose.set_editor_property('relative_scale3d',unreal.Vector(.26,.26,.50))
    nose.set_collision_profile_name('NoCollision')
    nose.set_material(0,unreal.load_asset('/Game/StealthShooter/MaterialLibrary/Lighting/M_LampBulb_On'))
    g.compile_bp(bp)
    return bp

def graphs():
    bp=unreal.load_asset(PATH)
    e=g.new_function(bp,'RestartPatrol')
    entry=store(e,e.find_graph_entry_pin(),'bNeedsTarget',literal='true')
    ret(e,store(e,entry,'bReturning',literal='false'));g.compile_bp(bp)
    e=g.new_function(bp,'RequestDestination');point=g.input_parameter(e,'Destination',VECTOR)
    entry=store(e,e.find_graph_entry_pin(),'TargetLocation',point)
    entry=store(e,entry,'bNeedsTarget',literal='false')
    entry=increment(e,entry,'MoveRequests');ret(e,after(entry,own(e,bp,'MoveToTarget')));g.compile_bp(bp)
    e=g.new_function(bp,'ContainsPoint')
    point=g.input_parameter(e,'Point',VECTOR);margin=g.input_parameter(e,'Margin',REAL)
    split=g.call(e,MATH+'BreakVector');g.wire(point,g.pin(split,'InVec'))
    checks=[]
    for axis in ['X','Y']:
        n=g.call(e,MATH+'InRange_FloatFloat');g.wire(g.pin(split,axis,True),g.pin(n,'Value'))
        g.wire(op(e,'Add_DoubleDouble',ref(e,'Min'+axis),margin),g.pin(n,'Min'))
        g.wire(op(e,'Subtract_DoubleDouble',ref(e,'Max'+axis),margin),g.pin(n,'Max'))
        g.value(n,'InclusiveMin','true');g.value(n,'InclusiveMax','true');checks.append(g.result(n))
    r=g.output_parameter(e,'bInside',BOOL);g.wire(op(e,'BooleanAND',*checks),g.pin(r,'bInside'));g.wire(e.find_graph_entry_pin(),r.find_execute_pin())
    g.compile_bp(bp)
    e=g.new_function(bp,'SampleDestination')
    n=g.call(e,'/Script/NavigationSystem.NavigationSystemV1.K2_GetRandomReachablePointInRadius')
    g.wire(location(e),g.pin(n,'Origin'))
    dx=op(e,'Subtract_DoubleDouble',ref(e,'MaxX'),ref(e,'MinX'))
    dy=op(e,'Subtract_DoubleDouble',ref(e,'MaxY'),ref(e,'MinY'))
    g.wire(op(e,'Add_DoubleDouble',dx,dy),g.pin(n,'Radius'))
    r=g.output_parameter(e,'Candidate',VECTOR);g.output_parameter(e,'bFound',BOOL)
    g.wire(g.pin(n,'RandomLocation',True),g.pin(r,'Candidate'));g.wire(g.result(n),g.pin(r,'bFound'));g.wire(e.find_graph_entry_pin(),r.find_execute_pin())
    g.compile_bp(bp)
    e=g.new_function(bp,'ConfigureMovement')
    n=g.set_variable(e,'MaxWalkSpeed','/Script/Engine.CharacterMovementComponent')
    g.wire(ref(e,'CharacterMovement'),g.pin(n,'self'))
    clamp=g.call(e,MATH+'FMax');g.wire(ref(e,'Speed'),g.pin(clamp,'A'));g.value(clamp,'B',0)
    g.wire(g.result(clamp),g.pin(n,'MaxWalkSpeed'));ret(e,after(e.find_graph_entry_pin(),n));g.compile_bp(bp)
    e=g.new_function(bp,'ChooseDestination');entry=e.find_graph_entry_pin()
    sample=own(e,bp,'SampleDestination');entry=after(entry,sample)
    inside=own(e,bp,'ContainsPoint');g.wire(g.pin(sample,'Candidate',True),g.pin(inside,'Point'));g.value(inside,'Margin',65);entry=after(entry,inside)
    dist=g.call(e,MATH+'Vector_Distance2D');g.wire(location(e),g.pin(dist,'V1'));g.wire(g.pin(sample,'Candidate',True),g.pin(dist,'V2'))
    far=op(e,'Greater_DoubleDouble',g.result(dist),150)
    ok=op(e,'BooleanAND',g.pin(sample,'bFound',True),g.pin(inside,'bInside',True))
    br=branch(e,entry,op(e,'BooleanAND',ok,far));ret(e,g.pin(br,'else',True))
    request=own(e,bp,'RequestDestination');g.wire(g.pin(sample,'Candidate',True),g.pin(request,'Destination'))
    ret(e,after(g.pin(br,'then',True),request));g.compile_bp(bp)
    e=g.new_function(bp,'RefreshPatrol');entry=after(e.find_graph_entry_pin(),own(e,bp,'ConfigureMovement'))
    inside=own(e,bp,'ContainsPoint');g.wire(location(e),g.pin(inside,'Point'));g.value(inside,'Margin',0);entry=after(entry,inside)
    outside=g.call(e,MATH+'Not_PreBool')
    g.wire(g.pin(inside,'bInside',True),g.pin(outside,'A'))
    notreturn=g.call(e,MATH+'Not_PreBool');g.wire(ref(e,'bReturning'),g.pin(notreturn,'A'))
    br=branch(e,entry,op(e,'BooleanAND',g.result(outside),g.result(notreturn)))
    entry=store(e,g.pin(br,'then',True),'bReturning',literal='true')
    entry=store(e,entry,'bNeedsTarget',literal='true');entry=increment(e,entry,'BoundaryTurns')
    # Both branches rejoin before deciding whether a fresh request is needed.
    need=branch(e,entry,ref(e,'bNeedsTarget'));g.wire(g.pin(br,'else',True),need.find_execute_pin())
    ret(e,after(g.pin(need,'then',True),own(e,bp,'ChooseDestination')));ret(e,g.pin(need,'else',True));g.compile_bp(bp)
    e=g.graph(bp)
    move=e.find_event_node('MoveToTarget')
    if not move:move=next(n for n in e.list_all_nodes() if isinstance(n,unreal.K2Node_CustomEvent))
    n=e.create_node_from_name('ИИ|ПеремещениесИИ',unreal.Vector2D(0,0),[],None)
    g.wire(self_ref(e),g.pin(n,'Pawn'));g.wire(ref(e,'TargetLocation'),g.pin(n,'Destination'));g.value(n,'AcceptanceRadius',20);g.value(n,'bStopOnOverlap','false');g.chain(move,n)
    for pinname,counter in [('OnSuccess','CompletedMoves'),('OnFail','FailedMoves')]:
        entry=increment(e,g.pin(n,pinname,True),counter)
        entry=store(e,entry,'bNeedsTarget',literal='true')
        store(e,entry,'bReturning',literal='false')
    ev=g.event(bp,'ReceiveBeginPlay');entry=after(g.then(ev),own(e,bp,'ConfigureMovement'))
    timer=g.call(e,'/Script/Engine.KismetSystemLibrary.K2_SetTimer');g.wire(self_ref(e),g.pin(timer,'Object'));g.value(timer,'FunctionName','RefreshPatrol');g.value(timer,'Time',.2);g.value(timer,'bLooping','true');after(entry,timer)
    ev=g.event(bp,'ReceiveEndPlay');n=g.call(e,'/Script/Engine.KismetSystemLibrary.K2_ClearTimer');g.wire(self_ref(e),g.pin(n,'Object'));g.value(n,'FunctionName','RefreshPatrol');after(g.then(ev),n)
    notes={
      'ContainsPoint':'World-space XY bounds. Margin reserves capsule clearance for destinations; Z stays on the navigation surface.',
      'SampleDestination':'One impure wrapper caches both outputs of the random navigation query in a single evaluation. Uses built-in reachable-point search.',
      'RestartPatrol':'Reset patrol scheduling without moving the actor. Used after an external reposition or a patrol reset.',
      'RequestDestination':'Store one destination and issue one movement request. The caller supplies a valid point on navigation inside the configured zone.',
      'ConfigureMovement':'Speed is cm/s. CharacterMovement owns translation, collision and turning. Negative Speed safely clamps to zero.',
      'ChooseDestination':'Accept only reachable random points inside the configured rectangle and away from the current position. Retry on the next timer tick when sampling fails.',
      'RefreshPatrol':'Check bounds every 0.2 seconds. One replacement request on leaving the zone; do not restart an active return path every frame.',
      'EventGraph':'AIMoveTo is the only movement request. NavMesh routes around Static Mesh obstacles. Success/failure schedules a fresh target; EndPlay clears the timer.'}
    g.compile_bp(bp)
    for gr in B.list_graphs(bp):
        editor=unreal.BlueprintGraphEditor.get_graph_editor(gr)
        if editor.list_all_nodes() and gr.get_name() in notes:
            editor.add_comment_to_nodes(notes[gr.get_name()],editor.list_all_nodes())
    g.layout(bp);g.save(bp)
    return {str(gr.get_name()):len(unreal.BlueprintGraphEditor.get_graph_editor(gr).list_all_nodes()) for gr in B.list_graphs(bp)}

def level():
    levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if unreal.EditorAssetLibrary.does_asset_exist(MAP):assert levels.load_level(MAP)
    else:assert levels.new_level(MAP)
    sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    def actor(cls,label,loc,rot=None):
        a=next((a for a in sub.get_all_level_actors() if a.get_actor_label()==label),None)
        if a is None:a=sub.spawn_actor_from_class(cls,unreal.Vector(*loc),rot or unreal.Rotator())
        a.set_actor_label(label);a.set_actor_location(unreal.Vector(*loc),False,False)
        if rot is not None:a.set_actor_rotation(rot,False)
        return a
    def mesh(label,loc,scale,mat,collision=True):
        a=actor(unreal.StaticMeshActor,label,loc);c=a.static_mesh_component
        c.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'));a.set_actor_scale3d(unreal.Vector(*scale))
        c.set_material(0,unreal.load_asset('/Game/StealthShooter/MaterialLibrary/'+mat))
        c.set_collision_profile_name('BlockAll' if collision else 'NoCollision');return a
    mesh('PatrolFloor',(0,0,-20),(30,28,.4),'Environment/M_LabRoom_Floor')
    for x in [-1450,1450]:mesh('OuterWallX_'+str(x),(x,0,100),(.2,28,2),'Environment/M_LabRoom_Wall')
    for y in [-1350,1350]:mesh('OuterWallY_'+str(y),(0,y,100),(29,.2,2),'Environment/M_LabRoom_Wall')
    # Painted bounds are visual only: the return logic, not an invisible wall, enforces the zone.
    for x in [-900,900]:mesh('ZoneX_'+str(x),(x,0,1),(.06,16,.02),'Environment/M_LabRoom_Accent',False)
    for y in [-800,800]:mesh('ZoneY_'+str(y),(0,y,1),(18,.06,.02),'Environment/M_LabRoom_Accent',False)
    for i,(x,y,sx,sy) in enumerate([(0,0,2.5,6),(-480,380,3,2),(480,-380,3,2)]):
        a=mesh('StaticObstacle_'+str(i+1),(x,y,85),(sx,sy,1.7),'Lighting/M_LightFixture')
        a.set_folder_path('Patrol/Obstacles')
    bp=unreal.load_asset(PATH)
    for i,(loc,speed) in enumerate([((-650,-480,65),180),((650,480,65),280)],1):
        a=actor(bp.generated_class(),'BoundedPatrol_'+str(i),loc);a.set_editor_property('Speed',speed);a.set_folder_path('Patrol/Agents')
    actor(unreal.PlayerStart,'PlayerStart',(-1150,-1050,96),unreal.Rotator(yaw=40))
    sun=actor(unreal.DirectionalLight,'PatrolSun',(0,0,1000),unreal.Rotator(pitch=-60,yaw=-30));sun.light_component.set_intensity(4)
    sky=actor(unreal.SkyLight,'PatrolSky',(0,0,800));sky.light_component.set_intensity(.7)
    pp=actor(unreal.PostProcessVolume,'PatrolExposure',(0,0,0));pp.set_editor_property('unbound',True)
    settings=pp.get_editor_property('settings')
    for key,value in [('override_auto_exposure_min_brightness',True),('override_auto_exposure_max_brightness',True),('auto_exposure_min_brightness',1),('auto_exposure_max_brightness',1)]:settings.set_editor_property(key,value)
    pp.set_editor_property('settings',settings)
    camera=actor(unreal.CameraActor,'PatrolOverview',(-1800,-2000,2600),unreal.Rotator(pitch=-45,yaw=48))
    camera.camera_component.set_field_of_view(65)
    # Overview is an editor-authored demonstration camera; the ThirdPerson template stays intact.
    camera.set_editor_property('auto_activate_for_player',unreal.AutoReceiveInput.PLAYER0)
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    nav_bounds=actor(unreal.NavMeshBoundsVolume,'PatrolNavigationBounds',(0,0,100))
    nav_bounds.set_actor_scale3d(unreal.Vector(20,20,5))
    unreal.NavigationSystemV1.get_navigation_system(world).on_navigation_bounds_updated(nav_bounds)
    world.get_world_settings().set_editor_property('default_game_mode',unreal.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonGameMode').generated_class())
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(unreal.Vector(-1800,-2000,2600),unreal.Rotator(pitch=-45,yaw=48))
    assert levels.save_current_level()
    return {'map':MAP,'agents':2,'static_obstacles':3}
