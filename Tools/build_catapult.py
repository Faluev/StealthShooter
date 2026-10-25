"""Practical 3.10: native constraint-driven catapult and physical ammunition."""
import unreal
import lab_graph as g
import maze_graph as m
from build_blueprint_lab import variable,ref,store,after
from build_switchable_room import component,self_ref,increment
B=unreal.BlueprintEditorLibrary
ROOT='/Game/StealthShooter/Physics/Catapult'
MAP='/Game/StealthShooter/Maps/L_Catapult'

def asset(name):return unreal.load_asset(ROOT+'/'+name)
def bp(name,parent=unreal.Actor):
    a=asset(name)
    if not a:
        f=unreal.BlueprintFactory();f.set_editor_property('parent_class',parent)
        a=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,ROOT,unreal.Blueprint,f)
    return a

def shape(bp,name,mesh,loc,scale,mat,collision='BlockAll'):
    c=component(bp,name,unreal.StaticMeshComponent)
    c.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/'+mesh))
    c.set_editor_property('relative_location',unreal.Vector(*loc));c.set_editor_property('relative_scale3d',unreal.Vector(*scale))
    c.set_material(0,unreal.load_asset('/Game/StealthShooter/MaterialLibrary/'+mat));c.set_mobility(unreal.ComponentMobility.MOVABLE);c.set_collision_profile_name(collision)
    return c

def own(e,bp,name):return g.call(e,bp.generated_class().get_path_name()+':'+name)
def call(e,cls,fn,target=None,**values):
    n=g.call(e,'/Script/Engine.'+cls+'.'+fn)
    if target is not None:g.wire(target,g.pin(n,'self'))
    for k,v in values.items():
        if cls=='TextRenderComponent' and k=='Value' and isinstance(v,str):
            text=call(e,'KismetTextLibrary','Conv_StringToText',InString=v);g.wire(g.result(text),g.pin(n,k));continue
        if hasattr(v,'is_valid'):g.wire(v,g.pin(n,k))
        else:g.value(n,k,v)
    return n

def make_root(blueprint,name):
    root=unreal.get_default_object(blueprint.generated_class()).root_component
    if root and str(root.get_name()).removesuffix('_GEN_VARIABLE')==name:return
    sub=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem);lib=unreal.SubobjectDataBlueprintFunctionLibrary
    handles=sub.k2_gather_subobject_data_for_blueprint(blueprint)
    target=next(h for h in handles if str(lib.get_object(lib.get_data(h)).get_name()).removesuffix('_GEN_VARIABLE')==name)
    assert sub.make_new_scene_root(handles[0],target,blueprint)

def arm_mesh():
    if asset('SM_CatapultArm'):return asset('SM_CatapultArm')
    sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);parts=[]
    # A single rigid body with simple convex boxes: beam, spoon floor and three rims.
    for loc,scale in [((-100,0,0),(4,.22,.22)),((-270,0,18),(.9,.95,.14)),((-315,0,35),(.12,.95,.4)),((-270,-47,35),(.9,.1,.4)),((-270,47,35),(.9,.1,.4))]:
        a=sub.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(*loc));a.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'));a.set_actor_scale3d(unreal.Vector(*scale));a.static_mesh_component.set_material(0,unreal.load_asset('/Game/StealthShooter/MaterialLibrary/Lighting/M_SwitchCap'));parts.append(a)
    options=unreal.MergeStaticMeshActorsOptions();options.set_editor_property('base_package_name',ROOT+'/CatapultArm');options.set_editor_property('destroy_source_actors',True);options.set_editor_property('spawn_merged_actor',True)
    settings=options.get_editor_property('mesh_merging_settings');settings.set_editor_property('merge_physics_data',True);settings.set_editor_property('merge_materials',False);settings.set_editor_property('pivot_type',unreal.MeshMergePivotType.WORLD_ORIGIN);options.set_editor_property('mesh_merging_settings',settings)
    merged=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).merge_static_mesh_actors(parts,options)
    assert merged
    mesh=merged.static_mesh_component.static_mesh;g.save(mesh);sub.destroy_actor(merged);return mesh

def prepare():
    levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    assert not unreal.EditorLevelLibrary.get_pie_worlds(False)
    if unreal.EditorAssetLibrary.does_asset_exist(MAP):levels.load_level(MAP)
    else:levels.new_level(MAP)
    unreal.EditorAssetLibrary.make_directory(ROOT)
    mesh=arm_mesh()
    ball=bp('BP_Cannonball');c=shape(ball,'BallMesh','Sphere',(0,0,0),(.44,.44,.44),'Lighting/M_LightFixture','PhysicsActor')
    make_root(ball,'BallMesh')
    c.set_simulate_physics(True);c.set_enable_gravity(True);c.set_mass_override_in_kg('None',4,True);c.set_linear_damping(.01);c.set_angular_damping(.1);c.set_editor_property('body_instance',c.get_editor_property('body_instance'))
    # Physics remains owned by the mesh. CCD prevents tunnelling during the throw.
    body=c.get_editor_property('body_instance');body.set_editor_property('use_ccd',True);c.set_editor_property('body_instance',body)
    g.clear_graph(ball);m.finish(ball,{'EventGraph':'Physical cannonball. Gravity and collision provide the complete flight; ammunition stays loaded until fired.'})
    cat=bp('BP_Catapult')
    shape(cat,'Base','Cube',(-70,0,20),(5,2.7,.4),'Lighting/M_LightFixture')
    for side,y in [('Left',-105),('Right',105)]:
        shape(cat,'Support'+side,'Cube',(0,y,110),(.4,.35,1.8),'Environment/M_LabRoom_Accent')
    shape(cat,'Axle','Cylinder',(0,0,180),(.3,.3,2.7),'Lighting/M_LightFixture','NoCollision').set_editor_property('relative_rotation',unreal.Rotator(roll=90))
    arm=component(cat,'ThrowingArm',unreal.StaticMeshComponent);arm.set_static_mesh(mesh);arm.set_editor_property('relative_location',unreal.Vector(0,0,180));arm.set_mobility(unreal.ComponentMobility.MOVABLE);arm.set_collision_profile_name('PhysicsActor');arm.set_simulate_physics(True);arm.set_enable_gravity(False);arm.set_mass_override_in_kg('None',45,True);arm.set_linear_damping(.05);arm.set_angular_damping(.05)
    hinge=component(cat,'ArmConstraint',unreal.PhysicsConstraintComponent);hinge.set_editor_property('relative_location',unreal.Vector(0,0,180))
    p=unreal.ConstrainComponentPropName();p.import_text('(ComponentName=Base)');hinge.set_editor_property('component_name1',p)
    p=unreal.ConstrainComponentPropName();p.import_text('(ComponentName=ThrowingArm)');hinge.set_editor_property('component_name2',p)
    hinge.set_disable_collision(True)
    for fn in [hinge.set_linear_x_limit,hinge.set_linear_y_limit,hinge.set_linear_z_limit]:fn(unreal.LinearConstraintMotion.LCM_LOCKED,0)
    hinge.set_angular_twist_limit(unreal.AngularConstraintMotion.ACM_LOCKED,0);hinge.set_angular_swing1_limit(unreal.AngularConstraintMotion.ACM_LOCKED,0);hinge.set_angular_swing2_limit(unreal.AngularConstraintMotion.ACM_LIMITED,75)
    hinge.set_angular_drive_mode(unreal.AngularDriveMode.TWIST_AND_SWING);hinge.set_angular_orientation_drive(True,False);hinge.set_angular_velocity_drive(True,False);hinge.set_angular_velocity_target(unreal.Vector());hinge.set_angular_drive_params(100,15,0);hinge.set_angular_orientation_target(unreal.Rotator())
    for name,typ,default in [('bReady',m.BOOL,'false'),('bBusy',m.BOOL,'true'),('ShotCount',m.INT,'0'),('LoadedBall',B.get_object_reference_type(ball.generated_class()),''),('FireAngle',m.REAL,'65'),('ReloadSeconds',m.REAL,'2')]:
        variable(cat,name,typ,default,name in ['FireAngle','ReloadSeconds']);B.set_blueprint_variable_category(cat,name,'Catapult|Configuration' if name in ['FireAngle','ReloadSeconds'] else 'Catapult|State')
    for name in ['Fire','Reload','LoadBall','InitializeCatapult','SetReady']:g.new_function(cat,name)
    g.compile_bp(cat)
    unreal.get_default_object(cat.generated_class()).set_editor_property('FireAngle',65)
    g.save(cat)
    return {'arm':mesh.get_path_name(),'ball':ball.get_path_name(),'catapult':cat.get_path_name()}


def prepare_payload_latch(cat):
    latch=component(cat,'PayloadLatch',unreal.PhysicsConstraintComponent);latch.set_disable_collision(True)
    for fn in [latch.set_linear_x_limit,latch.set_linear_y_limit,latch.set_linear_z_limit]:fn(unreal.LinearConstraintMotion.LCM_FREE,0)
    latch.set_angular_twist_limit(unreal.AngularConstraintMotion.ACM_FREE,0);latch.set_angular_swing1_limit(unreal.AngularConstraintMotion.ACM_FREE,0);latch.set_angular_swing2_limit(unreal.AngularConstraintMotion.ACM_FREE,0)
    variable(cat,'bPayloadLatched',m.BOOL,'false')
    for name in ['LatchPayload','ReleasePayload','CheckPayloadRelease']:g.new_function(cat,name)
    g.compile_bp(cat)

def payload_graphs(cat):
    e=g.new_function(cat,'LatchPayload');entry=e.find_graph_entry_pin()
    loc=call(e,'Actor','K2_GetActorLocation',ref(e,'LoadedBall'))
    entry=after(entry,call(e,'SceneComponent','K2_SetWorldLocation',ref(e,'PayloadLatch'),NewLocation=g.result(loc)))
    mesh=g.get_variable(e,'BallMesh',asset('BP_Cannonball').generated_class().get_path_name());g.wire(ref(e,'LoadedBall'),g.pin(mesh,'self'))
    entry=after(entry,call(e,'PhysicsConstraintComponent','SetConstrainedComponents',ref(e,'PayloadLatch'),Component1=ref(e,'ThrowingArm'),Component2=g.result(mesh)))
    for axis in ['X','Y','Z']:entry=after(entry,call(e,'PhysicsConstraintComponent','SetLinear'+axis+'Limit',ref(e,'PayloadLatch'),ConstraintType='LCM_Locked',LimitSize=0))
    store(e,entry,'bPayloadLatched',literal='true')
    e=g.new_function(cat,'ReleasePayload');guard=m.branch(e,e.find_graph_entry_pin(),ref(e,'bPayloadLatched'));entry=g.pin(guard,'then',True)
    # All degrees become free: the joint exerts no forces and preserves the pair collision filter.
    # The released ball keeps its simulated momentum, never an assigned velocity or impulse.
    for axis in ['X','Y','Z']:entry=after(entry,call(e,'PhysicsConstraintComponent','SetLinear'+axis+'Limit',ref(e,'PayloadLatch'),ConstraintType='LCM_Free',LimitSize=0))
    entry=store(e,entry,'bPayloadLatched',literal='false');m.clear_timer(e,entry,'CheckPayloadRelease')
    e=g.new_function(cat,'CheckPayloadRelease');angle=call(e,'PhysicsConstraintComponent','GetCurrentSwing2',ref(e,'ArmConstraint'))
    guard=m.branch(e,e.find_graph_entry_pin(),m.op(e,'LessEqual_DoubleDouble',g.result(angle),-35));after(g.pin(guard,'then',True),own(e,cat,'ReleasePayload'))

def graphs():
    cat=asset('BP_Catapult');prepare_payload_latch(cat);payload_graphs(cat);e=g.clear_graph(cat)
    ev=g.event(cat,'ReceiveBeginPlay');entry=after(g.then(ev),own(e,cat,'InitializeCatapult'))
    pc=m.pc(e);n=call(e,'Actor','EnableInput',PlayerController=pc);after(entry,n)
    for key,fn in [('F','Fire')]:
        n=g.named_node(e,lambda s:s.endswith('|keyboardevents|'+key.lower()),key+' keyboard event')
        after(g.pin(n,'Pressed',True),own(e,cat,fn))
    ev=g.event(cat,'ReceiveEndPlay');entry=g.then(ev)
    for fn in ['LoadBall','BeginReload','CheckPayloadRelease']:entry=m.clear_timer(e,entry,fn)
    e=g.new_function(cat,'InitializeCatapult');entry=e.find_graph_entry_pin()
    n=call(e,'PhysicsConstraintComponent','SetConstrainedComponents',ref(e,'ArmConstraint'),Component1=ref(e,'Base'),Component2=ref(e,'ThrowingArm'));entry=after(entry,n)
    entry=store(e,entry,'bBusy',literal='false');after(entry,own(e,cat,'Reload'))
    e=g.new_function(cat,'Fire');br=m.branch(e,e.find_graph_entry_pin(),ref(e,'bReady'));entry=g.pin(br,'then',True)
    entry=store(e,entry,'bReady',literal='false');entry=store(e,entry,'bBusy',literal='true');entry=increment(e,entry,'ShotCount')
    entry=after(entry,call(e,'Actor','SetLifeSpan',ref(e,'LoadedBall'),InLifespan=25))
    entry=after(entry,call(e,'PhysicsConstraintComponent','SetAngularDriveParams',ref(e,'ArmConstraint'),PositionStrength=100,VelocityStrength=25,InForceLimit=0))
    rot=call(e,'KismetMathLibrary','MakeRotator',Yaw=0,Pitch=ref(e,'FireAngle'))
    entry=after(entry,call(e,'PrimitiveComponent','WakeAllRigidBodies',ref(e,'ThrowingArm')))
    entry=after(entry,call(e,'PhysicsConstraintComponent','SetAngularOrientationTarget',ref(e,'ArmConstraint'),InPosTarget=g.result(rot)))
    entry=m.timer(e,entry,'CheckPayloadRelease',.005,True)
    entry=m.timer(e,entry,'BeginReload',1.5)
    after(entry,call(e,'TextRenderComponent','K2_SetText',ref(e,'StatusText'),Value='FIRING / RELOADING'))
    e=g.new_function(cat,'BeginReload');entry=after(e.find_graph_entry_pin(),own(e,cat,'ReleasePayload'));entry=store(e,entry,'bBusy',literal='false');after(entry,own(e,cat,'Reload'))
    e=g.new_function(cat,'Reload');condition=m.op(e,'Not_PreBool',m.op(e,'BooleanOR',ref(e,'bBusy'),ref(e,'bReady')))
    br=m.branch(e,e.find_graph_entry_pin(),condition);entry=store(e,g.pin(br,'then',True),'bBusy',literal='true')
    entry=after(entry,call(e,'PhysicsConstraintComponent','SetAngularDriveParams',ref(e,'ArmConstraint'),PositionStrength=100,VelocityStrength=100,InForceLimit=0))
    rot=call(e,'KismetMathLibrary','MakeRotator',Pitch=0)
    entry=after(entry,call(e,'PrimitiveComponent','WakeAllRigidBodies',ref(e,'ThrowingArm')))
    entry=after(entry,call(e,'PhysicsConstraintComponent','SetAngularOrientationTarget',ref(e,'ArmConstraint'),InPosTarget=g.result(rot)))
    n=call(e,'KismetSystemLibrary','K2_SetTimer',Object=self_ref(e),FunctionName='LoadBall',Time=ref(e,'ReloadSeconds'),bLooping='false');entry=after(entry,n)
    after(entry,call(e,'TextRenderComponent','K2_SetText',ref(e,'StatusText'),Value='RELOADING...'))
    e=g.new_function(cat,'LoadBall');entry=e.find_graph_entry_pin()
    angle=call(e,'PhysicsConstraintComponent','GetCurrentSwing2',ref(e,'ArmConstraint'))
    absolute=call(e,'KismetMathLibrary','Abs',A=g.result(angle))
    slow=call(e,'PrimitiveComponent','GetPhysicsAngularVelocityInDegrees',ref(e,'ThrowingArm'))
    speed=call(e,'KismetMathLibrary','VSize',A=g.result(slow))
    settled=m.op(e,'BooleanAND',m.op(e,'Less_DoubleDouble',g.result(absolute),2),m.op(e,'Less_DoubleDouble',g.result(speed),5))
    guard=m.branch(e,entry,settled);retry=after(g.pin(guard,'else',True),call(e,'PrimitiveComponent','WakeAllRigidBodies',ref(e,'ThrowingArm')));m.timer(e,retry,'LoadBall',.1);entry=g.pin(guard,'then',True)
    transform=call(e,'SceneComponent','K2_GetComponentToWorld',ref(e,'ThrowingArm'))
    pos=call(e,'KismetMathLibrary','TransformLocation',T=g.result(transform),Location='(X=-270,Y=0,Z=47)')
    spawntransform=call(e,'KismetMathLibrary','MakeTransform',Location=g.result(pos))
    n=call(e,'GameplayStatics','BeginDeferredActorSpawnFromClass',ActorClass=asset('BP_Cannonball').generated_class().get_path_name(),SpawnTransform=g.result(spawntransform),CollisionHandlingOverride='AlwaysSpawn');entry=after(entry,n)
    n2=call(e,'GameplayStatics','FinishSpawningActor',Actor=g.result(n),SpawnTransform=g.result(spawntransform));entry=after(entry,n2)
    cast=g.named_node(e,lambda s:s.endswith('|casttobp_cannonball'),'Cast cannonball');g.wire(g.result(n2),g.pin(cast,'Object'));entry=after(entry,cast)
    out=next(p for p in cast.list_output_pins() if str(p.get_pin_name()).startswith('As'))
    entry=store(e,entry,'LoadedBall',out);entry=after(entry,own(e,cat,'LatchPayload'));entry=store(e,entry,'bBusy',literal='false');entry=store(e,entry,'bReady',literal='true')
    after(entry,call(e,'TextRenderComponent','K2_SetText',ref(e,'StatusText'),Value='READY / F: FIRE'))
    # Remove unused placeholder; only meaningful, commented functions remain.
    for gr in B.list_graphs(cat):
        if str(gr.get_name())=='SetReady':B.remove_graph(cat,gr)
    m.finish(cat,{'EventGraph':'F fires once; reload is automatic. Busy/ready guards prevent duplicate ammunition. EndPlay cancels callbacks.',
      'InitializeCatapult':'Bind the fixed base and the physical throwing arm to the one-axis constraint before starting the first reload.',
      'Fire':'Change only the angular drive target. The motor moves the constrained spoon and contact transfers momentum to the free cannonball. No impulse or assigned projectile velocity.',
      'BeginReload':'The firing window ends before the motor returns the spoon to the loading angle.',
      'Reload':'Return using the same physics drive. One named timer prevents stacked reload callbacks.',
      'LoadBall':'Spawn one physical cannonball above the actual spoon after the return drive has settled. Gravity seats it in the spoon.'})
    return True

def status_component():
    cat=asset('BP_Catapult');c=component(cat,'StatusText',unreal.TextRenderComponent)
    c.set_editor_property('relative_location',unreal.Vector(-180,-150,320));c.set_editor_property('relative_rotation',unreal.Rotator(yaw=-90));c.set_world_size(25);c.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER);c.set_text('F: FIRE / AUTO RELOAD');c.set_text_render_color(unreal.Color(255,215,110,255));g.compile_bp(cat)

def level():
    levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem);levels.load_level(MAP)
    sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    def actor(cls,label,loc,rot=None):
        a=next((x for x in sub.get_all_level_actors() if x.get_actor_label()==label),None)
        if not a:a=sub.spawn_actor_from_class(cls,unreal.Vector(*loc),rot or unreal.Rotator())
        a.set_actor_label(label);a.set_actor_location(unreal.Vector(*loc),False,False)
        if rot:a.set_actor_rotation(rot,False)
        return a
    def block(label,loc,scale,mat):
        a=actor(unreal.StaticMeshActor,label,loc);a.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'));a.set_actor_scale3d(unreal.Vector(*scale));a.static_mesh_component.set_material(0,unreal.load_asset('/Game/StealthShooter/MaterialLibrary/'+mat));return a
    block('CatapultRangeFloor',(1100,0,-20),(40,20,.4),'Environment/M_LabRoom_Floor')
    catapult=actor(asset('BP_Catapult').generated_class(),'TrainingCatapult',(0,0,0));catapult.set_editor_property('FireAngle',65)
    for i,x in enumerate([800,1400,2000]):
        block('RangeMark'+str(i),(x,0,1),(.06,14,.02),'Environment/M_LabRoom_Accent')
    for i,y in enumerate([-150,0,150]):block('Target'+str(i),(2000,y,70),(.35,1.1,1.4),'Lighting/M_SwitchCap')
    actor(unreal.PlayerStart,'CatapultPlayerStart',(-350,-500,96),unreal.Rotator(yaw=45))
    sun=actor(unreal.DirectionalLight,'CatapultSun',(0,0,1200),unreal.Rotator(pitch=-55,yaw=-35));sun.light_component.set_intensity(4);sun.light_component.set_editor_property('atmosphere_sun_light',True)
    actor(unreal.SkyAtmosphere,'CatapultAtmosphere',(0,0,0));sky=actor(unreal.SkyLight,'CatapultSky',(0,0,1200));sky.light_component.set_editor_property('real_time_capture',True);sky.light_component.set_intensity(.8)
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world();world.get_world_settings().set_editor_property('default_game_mode',unreal.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonGameMode').generated_class())
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(unreal.Vector(-800,-1200,900),unreal.Rotator(pitch=-25,yaw=40));levels.save_current_level()
    return MAP
