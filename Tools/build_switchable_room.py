"""Build practical 3.8 with an interface, per-lamp subscriptions and nearby input."""
import unreal
import lab_graph as g
from build_blueprint_lab import variable,ref,after,store,finalize

ROOT='/Game/StealthShooter/Interaction'
B=unreal.BlueprintEditorLibrary
BOOL=B.get_basic_type_by_name('bool')
INT=B.get_basic_type_by_name('int')
REAL=B.get_basic_type_by_name('real')

def setup():g.BP_ROOT=ROOT

def component(bp,name,cls):
    subsystem=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    handles=subsystem.k2_gather_subobject_data_for_blueprint(bp)
    library=unreal.SubobjectDataBlueprintFunctionLibrary
    for handle in handles:
        obj=library.get_object(library.get_data(handle))
        if obj and str(obj.get_name()).removesuffix('_GEN_VARIABLE')==name:return obj
    handle,reason=subsystem.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=handles[0],new_class=cls,blueprint_context=bp))
    assert not str(reason),str(reason)
    assert subsystem.rename_subobject(handle,name)
    obj=library.get_object(library.get_data(handle))
    return obj

def prepare():
    setup()
    bpi=unreal.load_asset(ROOT+'/BPI_Switchable')
    for gr in B.list_graphs(bpi):
        if str(gr.get_name()).startswith('NewFunction'):B.remove_graph(bpi,gr)
    for name in ['SwitchOn','SwitchOff']:g.new_function(bpi,name)
    e=g.new_function(bpi,'IsSwitchOn');g.output_parameter(e,'IsOn',BOOL)
    g.compile_bp(bpi)
    button=g.blueprint('BP_LightSwitch',unreal.Actor)
    variable(button,'IsOn',BOOL,'true')
    variable(button,'InteractionRadius',REAL,'250',True)
    variable(button,'PressCount',INT,'0')
    variable(button,'BroadcastCount',INT,'0')
    if 'OnSwitched' not in [str(x) for x in B.list_event_dispatchers(button)]:
        assert B.add_event_dispatcher(button,'OnSwitched')
        assert B.add_event_dispatcher_parameter(button,'OnSwitched','Enabled',BOOL)
    g.compile_bp(button)
    lamp=g.blueprint('BP_SwitchableLamp',unreal.Actor)
    variable(lamp,'IsOn',BOOL,'true')
    variable(lamp,'ControlButton',B.get_object_reference_type(button.generated_class()),editable=True)
    variable(lamp,'SwitchCount',INT,'0')
    variable(lamp,'Bound',BOOL,'false')
    g.compile_bp(lamp)
    component(button,'SwitchBody',unreal.StaticMeshComponent)
    component(button,'SwitchCap',unreal.StaticMeshComponent)
    component(button,'Prompt',unreal.TextRenderComponent)
    component(lamp,'Stand',unreal.StaticMeshComponent)
    component(lamp,'Bulb',unreal.StaticMeshComponent)
    component(lamp,'LampLight',unreal.PointLightComponent)
    g.compile_bp(button);g.compile_bp(lamp)
    return {'interface':bpi.get_path_name(),'button':button.get_path_name(),'lamp':lamp.get_path_name()}

def self_ref(e):
    return g.result(g.named_node(e,lambda n:n.endswith('|getareferencetoself') or n.endswith('|получитьссылкунасебя'),'Self'))

def message(e,name,target):
    n=g.named_node(e,lambda n:n.endswith('|'+name.lower()+'(сообщение)') or n.endswith('|'+name.lower()+'(message)'),name+' message')
    g.wire(target,g.pin(n,'self'))
    return n

def increment(e,entry,name):
    add=g.call(e,'/Script/Engine.KismetMathLibrary.Add_IntInt');g.wire(ref(e,name),g.pin(add,'A'));g.value(add,'B',1)
    return store(e,entry,name,g.result(add))

def query(bp):
    e=g.new_function(bp,'IsSwitchOn');ret=g.output_parameter(e,'IsOn',BOOL)
    g.wire(e.find_graph_entry_pin(),ret.find_execute_pin());g.wire(ref(e,'IsOn'),g.pin(ret,'IsOn'))
    g.compile_bp(bp)

def button_graphs():
    setup();bp=unreal.load_asset(ROOT+'/BP_LightSwitch');g.clear_graph(bp);query(bp)
    e=g.new_function(bp,'TryInteract');entry=e.find_graph_entry_pin()
    pawn=g.call(e,'/Script/Engine.GameplayStatics.GetPlayerPawn');g.value(pawn,'PlayerIndex',0)
    valid=g.call(e,'/Script/Engine.KismetSystemLibrary.IsValid');g.wire(g.result(pawn),g.pin(valid,'Object'))
    exists=e.add_branch_node();g.wire(entry,exists.find_execute_pin());g.wire(g.result(valid),g.pin(exists,'Condition'))
    distance=g.call(e,'/Script/Engine.Actor.GetDistanceTo');g.wire(g.result(pawn),g.pin(distance,'OtherActor'))
    close=g.call(e,'/Script/Engine.KismetMathLibrary.LessEqual_DoubleDouble');g.wire(g.result(distance),g.pin(close,'A'));g.wire(ref(e,'InteractionRadius'),g.pin(close,'B'))
    nearby=e.add_branch_node();g.wire(g.pin(exists,'then',True),nearby.find_execute_pin());g.wire(g.result(close),g.pin(nearby,'Condition'))
    entry=increment(e,g.pin(nearby,'then',True),'PressCount')
    state=e.add_branch_node();g.wire(entry,state.find_execute_pin());g.wire(ref(e,'IsOn'),g.pin(state,'Condition'))
    for output,name in [('then','SwitchOff'),('else','SwitchOn')]:
        call=message(e,name,self_ref(e));g.wire(g.pin(state,output,True),call.find_execute_pin())
    g.compile_bp(bp)
    e=g.graph(bp)
    for name,on in [('SwitchOn',True),('SwitchOff',False)]:
        ev=g.event(bp,name);branch=e.add_branch_node();g.wire(g.then(ev),branch.find_execute_pin());g.wire(ref(e,'IsOn'),g.pin(branch,'Condition'))
        entry=store(e,g.pin(branch,'else' if on else 'then',True),'IsOn',literal=str(on).lower())
        entry=increment(e,entry,'BroadcastCount')
        dispatch=g.named_node(e,lambda n:n.endswith('|callonswitched'),'Call OnSwitched');g.value(dispatch,'Enabled',str(on).lower());entry=after(entry,dispatch)
        text=g.call(e,'/Script/Engine.KismetTextLibrary.Conv_StringToText');g.value(text,'InString','E: LIGHTS '+('OFF' if on else 'ON')+'  |  RANGE 2.5m')
        prompt=g.call(e,'/Script/Engine.TextRenderComponent.K2_SetText');g.wire(ref(e,'Prompt'),g.pin(prompt,'self'));g.wire(g.result(text),g.pin(prompt,'Value'));after(entry,prompt)
    ev=g.event(bp,'ReceiveBeginPlay');controller=g.call(e,'/Script/Engine.GameplayStatics.GetPlayerController');g.value(controller,'PlayerIndex',0)
    enable=g.call(e,'/Script/Engine.Actor.EnableInput');g.wire(g.result(controller),g.pin(enable,'PlayerController'));g.wire(g.then(ev),enable.find_execute_pin())
    key=g.named_node(e,lambda n:n.endswith('|keyboardevents|e'),'E key')
    interact=g.call(e,bp.generated_class().get_path_name()+':TryInteract');g.wire(g.pin(key,'Pressed',True),interact.find_execute_pin())
    finalize(bp)
    return True

def delegate(e,target_pin):
    n=g.named_node(e,lambda x:x.endswith('|создатьсобытие') or x.endswith('|createevent'),'Create Event')
    g.wire(self_ref(e),g.pin(n,'self'))
    g.wire(g.pin(n,'OutputDelegate',True),target_pin)
    B.set_create_delegate_function(n,'HandleSwitchChanged')
    return n

def lamp_graphs():
    setup();bp=unreal.load_asset(ROOT+'/BP_SwitchableLamp');g.clear_graph(bp);query(bp)
    e=g.new_function(bp,'HandleSwitchChanged');enabled=g.input_parameter(e,'Enabled',BOOL)
    branch=e.add_branch_node();g.wire(e.find_graph_entry_pin(),branch.find_execute_pin());g.wire(enabled,g.pin(branch,'Condition'))
    for output,name in [('then','SwitchOn'),('else','SwitchOff')]:
        n=message(e,name,self_ref(e));g.wire(g.pin(branch,output,True),n.find_execute_pin())
    g.compile_bp(bp)
    e=g.new_function(bp,'BindToButton');entry=e.find_graph_entry_pin()
    already=e.add_branch_node();g.wire(entry,already.find_execute_pin());g.wire(ref(e,'Bound'),g.pin(already,'Condition'))
    valid=g.call(e,'/Script/Engine.KismetSystemLibrary.IsValid');g.wire(ref(e,'ControlButton'),g.pin(valid,'Object'))
    exists=e.add_branch_node();g.wire(g.pin(already,'else',True),exists.find_execute_pin());g.wire(g.result(valid),g.pin(exists,'Condition'))
    bind=g.named_node(e,lambda n:n.endswith('|bindeventtoonswitched'),'Bind OnSwitched');g.wire(ref(e,'ControlButton'),g.pin(bind,'self'));delegate(e,g.pin(bind,'Delegate'))
    entry=after(g.pin(exists,'then',True),bind);entry=store(e,entry,'Bound',literal='true')
    current=message(e,'IsSwitchOn',ref(e,'ControlButton'));entry=after(entry,current)
    sync=g.call(e,bp.generated_class().get_path_name()+':HandleSwitchChanged');g.wire(g.pin(current,'IsOn',True),g.pin(sync,'Enabled'));after(entry,sync)
    g.compile_bp(bp)
    e=g.new_function(bp,'UnbindFromButton');entry=store(e,e.find_graph_entry_pin(),'Bound',literal='false')
    valid=g.call(e,'/Script/Engine.KismetSystemLibrary.IsValid');g.wire(ref(e,'ControlButton'),g.pin(valid,'Object'))
    exists=e.add_branch_node();g.wire(entry,exists.find_execute_pin());g.wire(g.result(valid),g.pin(exists,'Condition'))
    unbind=g.named_node(e,lambda n:n.endswith('|unbindeventfromonswitched'),'Unbind OnSwitched');g.wire(ref(e,'ControlButton'),g.pin(unbind,'self'));delegate(e,g.pin(unbind,'Delegate'));after(g.pin(exists,'then',True),unbind)
    g.compile_bp(bp)
    e=g.graph(bp)
    for name,on in [('SwitchOn',True),('SwitchOff',False)]:
        ev=g.event(bp,name);entry=store(e,g.then(ev),'IsOn',literal=str(on).lower());entry=increment(e,entry,'SwitchCount')
        visibility=g.call(e,'/Script/Engine.SceneComponent.SetVisibility');g.wire(ref(e,'LampLight'),g.pin(visibility,'self'));g.value(visibility,'bNewVisibility',str(on).lower());entry=after(entry,visibility)
        material=g.call(e,'/Script/Engine.PrimitiveComponent.SetMaterial');g.wire(ref(e,'Bulb'),g.pin(material,'self'));g.value(material,'Material',ROOT+'/M_Bulb'+('On' if on else 'Off')+'.M_Bulb'+('On' if on else 'Off'));after(entry,material)
    for event,method in [('ReceiveBeginPlay','BindToButton'),('ReceiveEndPlay','UnbindFromButton')]:
        ev=g.event(bp,event);n=g.call(e,bp.generated_class().get_path_name()+':'+method);g.wire(g.then(ev),n.find_execute_pin())
    finalize(bp)
    return True

def material(name,color,emission=0):
    path=ROOT+'/'+name
    m=unreal.load_asset(path) or unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,ROOT,unreal.Material,unreal.MaterialFactoryNew())
    lib=unreal.MaterialEditingLibrary;lib.delete_all_material_expressions(m)
    base=lib.create_material_expression(m,unreal.MaterialExpressionConstant3Vector,0,0);base.set_editor_property('constant',unreal.LinearColor(*color,1));lib.connect_material_property(base,'',unreal.MaterialProperty.MP_BASE_COLOR)
    if emission:
        glow=lib.create_material_expression(m,unreal.MaterialExpressionConstant3Vector,0,160);glow.set_editor_property('constant',unreal.LinearColor(*(c*emission for c in color),1));lib.connect_material_property(glow,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    rough=lib.create_material_expression(m,unreal.MaterialExpressionConstant,0,300);rough.set_editor_property('r',.65);lib.connect_material_property(rough,'',unreal.MaterialProperty.MP_ROUGHNESS)
    lib.recompile_material(m);g.save(m);return m

def appearance():
    setup()
    materials={name:material(name,color,emission) for name,color,emission in [('M_BulbOn',(1,.67,.29),2),('M_BulbOff',(.035,.04,.05),0),('M_Body',(.035,.055,.08),0),('M_ButtonCap',(.03,.6,.25),.4),('M_Floor',(.075,.10,.13),0),('M_Wall',(.17,.20,.24),0),('M_Accent',(.04,.3,.5),.2)]}
    button=unreal.load_asset(ROOT+'/BP_LightSwitch');lamp=unreal.load_asset(ROOT+'/BP_SwitchableLamp')
    def mesh(bp,name,shape,loc,scale,mat,collision=True):
        c=component(bp,name,unreal.StaticMeshComponent);c.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/'+shape));c.set_editor_property('relative_location',unreal.Vector(*loc));c.set_editor_property('relative_scale3d',unreal.Vector(*scale));c.set_material(0,materials[mat]);c.set_collision_profile_name('BlockAllDynamic' if collision else 'NoCollision');c.set_mobility(unreal.ComponentMobility.MOVABLE);return c
    mesh(button,'SwitchBody','Cube',(0,0,60),(.45,.45,1.2),'M_Body')
    mesh(button,'SwitchCap','Sphere',(0,0,132),(.33,.33,.16),'M_ButtonCap',False)
    prompt=component(button,'Prompt',unreal.TextRenderComponent);prompt.set_editor_property('relative_location',unreal.Vector(0,0,225));prompt.set_editor_property('relative_rotation',unreal.Rotator(yaw=180));prompt.set_text('E: LIGHTS OFF  |  RANGE 2.5m');prompt.set_world_size(17);prompt.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
    mesh(lamp,'Stand','Cylinder',(0,0,135),(.18,.18,2.7),'M_Body')
    bulb=mesh(lamp,'Bulb','Sphere',(0,0,285),(.62,.62,.62),'M_BulbOn',False);bulb.set_editor_property('cast_shadow',False)
    light=component(lamp,'LampLight',unreal.PointLightComponent);light.set_editor_property('relative_location',unreal.Vector(0,0,285));light.set_mobility(unreal.ComponentMobility.MOVABLE);light.set_editor_property('intensity_units',unreal.LightUnits.LUMENS);light.set_editor_property('intensity',3000);light.set_editor_property('attenuation_radius',800);light.set_light_color(unreal.LinearColor(1,.75,.43));light.set_editor_property('source_radius',20)
    g.compile_bp(button);g.compile_bp(lamp)
    return True

def level():
    levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    path='/Game/StealthShooter/Maps/L_SwitchableRoom'
    if unreal.EditorAssetLibrary.does_asset_exist(path):assert levels.load_level(path)
    else:assert levels.new_level(path)
    sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    def actor(cls,label,loc,rot=None):
        a=next((a for a in sub.get_all_level_actors() if a.get_actor_label()==label),None)
        if a is None:a=sub.spawn_actor_from_class(cls,unreal.Vector(*loc),rot or unreal.Rotator())
        a.set_actor_label(label);a.set_actor_location(unreal.Vector(*loc),False,False)
        if rot is not None:a.set_actor_rotation(rot,False)
        return a
    def mesh(label,loc,scale,mat):
        a=actor(unreal.StaticMeshActor,label,loc);a.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'));a.set_actor_scale3d(unreal.Vector(*scale));a.static_mesh_component.set_material(0,unreal.load_asset(ROOT+'/'+mat));return a
    def text(label,value,loc,size):
        a=actor(unreal.TextRenderActor,label,loc,unreal.Rotator(yaw=180));a.text_render.set_text(value);a.text_render.set_world_size(size);a.text_render.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER);return a
    mesh('Room_Floor',(100,0,-20),(18,16,.4),'M_Floor')
    mesh('Room_BackWall',(1000,0,180),(.25,16,3.6),'M_Wall')
    for name,y in [('Left',-800),('Right',800)]:mesh('Room_'+name+'Wall',(100,y,180),(18,.25,3.6),'M_Wall')
    mesh('Room_FrontRail',(-800,0,45),(.25,16,.9),'M_Body')
    for y in [-770,770]:mesh('Room_Edge_'+str(y),(100,y,10),(17,.12,.1),'M_Accent')
    button=actor(unreal.load_asset(ROOT+'/BP_LightSwitch').generated_class(),'MasterLightSwitch',(0,-120,0))
    for index,(x,y) in enumerate([(-300,-550),(-300,550),(600,-550),(600,550)],1):
        lamp=actor(unreal.load_asset(ROOT+'/BP_SwitchableLamp').generated_class(),'SwitchableLamp_'+str(index),(x,y,0))
        lamp.set_editor_property('ControlButton',button)
        mesh('Lamp_Platform_'+str(index),(x,y,4),(1.2,1.2,.08),'M_Body')
    text('Room_Title','SWITCHABLE  /  LIGHTING LAB',(980,0,290),42)
    text('Room_Subtitle','3.8   INTERFACE  +  EVENT DISPATCHER',(978,0,225),23)
    text('Room_Instructions','APPROACH THE CONSOLE  /  PRESS E',(976,0,170),21)
    actor(unreal.PlayerStart,'PlayerStart',(-280,0,96),unreal.Rotator(yaw=0))
    sun=actor(unreal.DirectionalLight,'AmbientFill',(0,0,700),unreal.Rotator(pitch=-55,yaw=-30));sun.light_component.set_intensity(.35);sun.light_component.set_light_color(unreal.LinearColor(.35,.55,1))
    pp=actor(unreal.PostProcessVolume,'FixedExposure',(0,0,0));pp.set_editor_property('unbound',True)
    settings=pp.get_editor_property('settings');settings.set_editor_property('override_auto_exposure_min_brightness',True);settings.set_editor_property('override_auto_exposure_max_brightness',True);settings.set_editor_property('auto_exposure_min_brightness',1);settings.set_editor_property('auto_exposure_max_brightness',1);pp.set_editor_property('settings',settings)
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world();world.get_world_settings().set_editor_property('default_game_mode',unreal.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonGameMode').generated_class())
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(unreal.Vector(-680,0,250),unreal.Rotator(pitch=-7,yaw=0))
    assert levels.save_current_level()
    return {'map':path,'lamps':4,'radius_cm':250}

def comments():
    notes={'BP_LightSwitch':{'TryInteract':'Only the local player within InteractionRadius may press E. Interface messages change the switch state.', 'EventGraph':'SwitchOn / SwitchOff broadcast only on a real state change. The switch never stores or iterates lamp references.'},'BP_SwitchableLamp':{'BindToButton':'Each lamp subscribes once at Begin Play and synchronizes with the switch state.', 'HandleSwitchChanged':'Dispatcher callback invokes this lamp through BPI_Switchable.', 'UnbindFromButton':'Remove this lamp callback at End Play; never unbind other subscribers.', 'EventGraph':'Interface events update the actual Point Light visibility and the bulb material.'}}
    for name,graphs in notes.items():
        bp=unreal.load_asset(ROOT+'/'+name)
        for graph_name,note in graphs.items():
            e=unreal.BlueprintGraphEditor.get_graph_editor(B.find_graph(bp,graph_name));e.add_comment_to_nodes(note,e.list_all_nodes())
        g.save(bp)
    return True

def readable_text():
    button=unreal.load_asset(ROOT+'/BP_LightSwitch')
    prompt=component(button,'Prompt',unreal.TextRenderComponent)
    path=ROOT+'/M_LabText'
    text_material=unreal.load_asset(path)
    if text_material is None:
        source=prompt.get_editor_property('text_material')
        text_material=unreal.EditorAssetLibrary.duplicate_asset(source.get_path_name().split('.')[0],path)
        text_material.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
        glow=unreal.MaterialEditingLibrary.create_material_expression(text_material,unreal.MaterialExpressionConstant3Vector,0,500)
        glow.set_editor_property('constant',unreal.LinearColor(.8,.9,1))
        unreal.MaterialEditingLibrary.connect_material_property(glow,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        unreal.MaterialEditingLibrary.recompile_material(text_material)
        g.save(text_material)
    prompt.modify();prompt.set_editor_property('text_material',text_material);g.compile_bp(button)
    for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        text_component=None
        if isinstance(actor,unreal.TextRenderActor):text_component=actor.text_render
        elif actor.get_class().get_name()=='BP_LightSwitch_C':text_component=actor.get_editor_property('Prompt')
        if text_component:
            actor.modify();text_component.modify();text_component.set_editor_property('text_material',text_material)
    assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    return True
