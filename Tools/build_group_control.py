"""Create the UMG group-control practical without modifying previous lesson assets."""
import unreal
import lab_graph as g
from build_blueprint_lab import variable,ref,store,after,finalize
from build_switchable_room import component,message,self_ref
B=unreal.BlueprintEditorLibrary
ROOT='/Game/StealthShooter/GroupControl'
UI='/Game/StealthShooter/UI/WBP_GroupSwitch'
BOOL=B.get_basic_type_by_name('bool')
REAL=B.get_basic_type_by_name('real')
STRING=B.get_basic_type_by_name('string')
ACTOR=B.get_object_reference_type(unreal.Actor)

def widget_design():
    bp=unreal.load_asset(UI);tree=unreal.find_object(bp,'WidgetTree');root=unreal.find_object(tree,'CanvasPanel_2')
    assert root,'Create a Canvas Panel root in the Widget Designer first.'
    root.clear_children()
    def new(cls,name):return unreal.find_object(tree,name) or unreal.new_object(cls,tree,name)
    panel=new(unreal.Border,'ControlPanel');root.add_child(panel)
    panel.set_brush_color(unreal.LinearColor(.018,.028,.05,.97));panel.set_padding(unreal.Margin(24))
    slot=panel.slot;slot.set_anchors(unreal.Anchors(unreal.Vector2D(.5,.76),unreal.Vector2D(.5,.76)));slot.set_alignment(unreal.Vector2D(.5,.5));slot.set_position(unreal.Vector2D(0,0));slot.set_size(unreal.Vector2D(470,255))
    box=new(unreal.VerticalBox,'ContentStack');box.clear_children();panel.set_content(box)
    def text(name,value,size,color):
        w=new(unreal.TextBlock,name);w.set_text(value);font=w.get_editor_property('font');font.set_editor_property('size',size);w.set_font(font);w.set_color_and_opacity(unreal.SlateColor(specified_color=unreal.LinearColor(*color,1)));w.set_editor_property('justification',unreal.TextJustify.CENTER)
        s=box.add_child_to_vertical_box(w);s.set_padding(unreal.Margin(0,0,0,10));return w
    text('PanelTitle','УПРАВЛЕНИЕ ГРУППОЙ',22,(.83,.92,1))
    text('StatusText','Группа: включена',17,(.40,.87,.74))
    row=new(unreal.HorizontalBox,'Actions');row.clear_children();box.add_child_to_vertical_box(row)
    for name,label,color in [('ButtonOn','ВКЛЮЧИТЬ',(.035,.38,.24)),('ButtonOff','ВЫКЛЮЧИТЬ',(.35,.07,.10))]:
        button=new(unreal.Button,name);button.set_background_color(unreal.LinearColor(*color,1));button.set_editor_property('is_focusable',False)
        s=row.add_child_to_horizontal_box(button);s.set_size(unreal.SlateChildSize(1,unreal.SlateSizeRule.FILL));s.set_padding(unreal.Margin(5,4,5,12))
        labelwidget=new(unreal.TextBlock,name+'Label');labelwidget.set_text(label);font=labelwidget.get_editor_property('font');font.set_editor_property('size',17);labelwidget.set_font(font);labelwidget.set_editor_property('justification',unreal.TextJustify.CENTER);button.set_content(labelwidget)
        button.get_content_slot().set_padding(unreal.Margin(12,13,12,13)) if hasattr(button,'get_content_slot') else None
    text('HintText','WASD — движение · Отойдите, чтобы закрыть',12,(.62,.70,.80))
    g.compile_bp(bp)
    return 'Designer ready: mark ButtonOn, ButtonOff and StatusText as variables.'

def prepare():
    g.BP_ROOT=ROOT
    path=ROOT+'/BP_GroupSwitch'
    bp=unreal.load_asset(path) or unreal.EditorAssetLibrary.duplicate_asset('/Game/StealthShooter/Interaction/BP_LightSwitch',path)
    for gr in B.list_graphs(bp):
        if str(gr.get_name()) not in ['EventGraph','IsSwitchOn']:B.remove_graph(bp,gr)
    g.clear_graph(bp)
    for name in ['PressCount','BroadcastCount']:g.graph(bp).remove_member_variable(name)
    B.remove_event_dispatcher(bp,'OnSwitched')
    variable(bp,'SwitchTargets',B.get_array_type(ACTOR),editable=True)
    variable(bp,'GroupLabel',STRING,'Группа',True)
    variable(bp,'IsNearby',BOOL,'false')
    widget=unreal.load_asset(UI);g.compile_bp(widget)
    variable(bp,'ControlWidget',B.get_object_reference_type(widget.generated_class()))
    prompt=component(bp,'Prompt',unreal.TextRenderComponent);prompt.set_text('APPROACH TO CONTROL');prompt.set_world_size(17)
    g.compile_bp(bp)
    variable(widget,'OwnerSwitch',ACTOR)
    variable(widget,'UseRadius',REAL,'250')
    g.compile_bp(widget)
    return True


def valid(e,obj,entry):
    n=g.call(e,'/Script/Engine.KismetSystemLibrary.IsValid');g.wire(obj,g.pin(n,'Object'));br=e.add_branch_node();g.wire(entry,br.find_execute_pin());g.wire(g.result(n),g.pin(br,'Condition'));return g.pin(br,'then',True)

def player(e):
    n=g.call(e,'/Script/Engine.GameplayStatics.GetPlayerPawn');g.value(n,'PlayerIndex',0);return g.result(n)

def controller(e):
    n=g.call(e,'/Script/Engine.GameplayStatics.GetPlayerController');g.value(n,'PlayerIndex',0);return g.result(n)

def near(e,owner,pawn,radius):
    distance=g.call(e,'/Script/Engine.Actor.GetDistanceTo');g.wire(owner,g.pin(distance,'self'));g.wire(pawn,g.pin(distance,'OtherActor'))
    compare=g.call(e,'/Script/Engine.KismetMathLibrary.LessEqual_DoubleDouble');g.wire(g.result(distance),g.pin(compare,'A'));g.wire(radius,g.pin(compare,'B'));return g.result(compare)

def call_self(e,bp,name):return g.call(e,bp.generated_class().get_path_name()+':'+name)

def widget_graphs():
    bp=unreal.load_asset(UI);unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp);g.compile_bp(bp)
    variable(bp,'PanelLabel',STRING,'Группа')
    e=g.new_function(bp,'RefreshDisplay');entry=valid(e,ref(e,'OwnerSwitch'),e.find_graph_entry_pin())
    state=message(e,'IsSwitchOn',ref(e,'OwnerSwitch'));entry=after(entry,state)
    br=e.add_branch_node();g.wire(entry,br.find_execute_pin());g.wire(g.pin(state,'IsOn',True),g.pin(br,'Condition'))
    for output,on in [('then',True),('else',False)]:
        entry=g.pin(br,output,True)
        concat=g.call(e,'/Script/Engine.KismetStringLibrary.Concat_StrStr');g.wire(ref(e,'PanelLabel'),g.pin(concat,'A'));g.value(concat,'B',' · '+('включена' if on else 'выключена'))
        text=g.call(e,'/Script/Engine.KismetTextLibrary.Conv_StringToText');g.wire(g.result(concat),g.pin(text,'InString'))
        settext=g.call(e,'/Script/UMG.TextBlock.SetText');g.wire(ref(e,'StatusText'),g.pin(settext,'self'));g.wire(g.result(text),g.pin(settext,'InText'));entry=after(entry,settext)
        for name,enabled in [('ButtonOn',not on),('ButtonOff',on)]:
            n=g.call(e,'/Script/UMG.Widget.SetIsEnabled');g.wire(ref(e,name),g.pin(n,'self'));g.value(n,'bInIsEnabled',str(enabled).lower());entry=after(entry,n)
    g.compile_bp(bp)
    for name,action in [('HandleOn','SwitchOn'),('HandleOff','SwitchOff')]:
        e=g.new_function(bp,name);entry=valid(e,ref(e,'OwnerSwitch'),e.find_graph_entry_pin());pawn=player(e);entry=valid(e,pawn,entry)
        br=e.add_branch_node();g.wire(entry,br.find_execute_pin());g.wire(near(e,ref(e,'OwnerSwitch'),pawn,ref(e,'UseRadius')),g.pin(br,'Condition'))
        n=message(e,action,ref(e,'OwnerSwitch'));entry=after(g.pin(br,'then',True),n);after(entry,call_self(e,bp,'RefreshDisplay'))
        g.compile_bp(bp)
    e=g.clear_graph(bp);ev=g.event(bp,'Construct');entry=g.then(ev)
    for button,handler in [('ButtonOn','HandleOn'),('ButtonOff','HandleOff')]:
        bind=g.named_node(e,lambda n:n=='кнопка|событие|bindeventtoonclicked','Button OnClicked')
        g.wire(ref(e,button),g.pin(bind,'self'))
        delegate=g.named_node(e,lambda n:n.endswith('|создатьсобытие') or n.endswith('|createevent'),'Create Event');g.wire(self_ref(e),g.pin(delegate,'self'));g.wire(g.pin(delegate,'OutputDelegate',True),g.pin(bind,'Delegate'));B.set_create_delegate_function(delegate,handler);assert str(B.get_create_delegate_function(delegate))==handler
        entry=after(entry,bind)
    finalize(bp)
    return True

def button_graphs():
    bp=unreal.load_asset(ROOT+'/BP_GroupSwitch');widget=unreal.load_asset(UI);g.clear_graph(bp)
    for name in ['ShowControls','HideControls','UpdateProximity']:g.new_function(bp,name)
    g.compile_bp(bp)
    for name,show in [('ShowControls',True),('HideControls',False)]:
        e=g.new_function(bp,name);entry=valid(e,ref(e,'ControlWidget'),e.find_graph_entry_pin())
        if show:
            refresh=g.call(e,widget.generated_class().get_path_name()+':RefreshDisplay');g.wire(ref(e,'ControlWidget'),g.pin(refresh,'self'));entry=after(entry,refresh)
        n=g.call(e,'/Script/UMG.UserWidget.AddToViewport' if show else '/Script/UMG.Widget.RemoveFromParent');g.wire(ref(e,'ControlWidget'),g.pin(n,'self'));entry=after(entry,n)
        pc=controller(e)
        mode=g.call(e,'/Script/UMG.WidgetBlueprintLibrary.SetInputMode_GameAndUIEx' if show else '/Script/UMG.WidgetBlueprintLibrary.SetInputMode_GameOnly');g.wire(pc,g.pin(mode,'PlayerController'))
        if show:g.value(mode,'bHideCursorDuringCapture','false')
        entry=after(entry,mode)
        cursor=g.set_variable(e,'bShowMouseCursor','/Script/Engine.PlayerController');g.wire(pc,g.pin(cursor,'self'));g.value(cursor,'bShowMouseCursor',str(show).lower());after(entry,cursor)
        g.compile_bp(bp)
    e=g.new_function(bp,'UpdateProximity');entry=valid(e,ref(e,'ControlWidget'),e.find_graph_entry_pin());pawn=player(e);entry=valid(e,pawn,entry)
    nearby=near(e,self_ref(e),pawn,ref(e,'InteractionRadius'))
    change=g.call(e,'/Script/Engine.KismetMathLibrary.NotEqual_BoolBool');g.wire(nearby,g.pin(change,'A'));g.wire(ref(e,'IsNearby'),g.pin(change,'B'))
    br=e.add_branch_node();g.wire(entry,br.find_execute_pin());g.wire(g.result(change),g.pin(br,'Condition'));entry=store(e,g.pin(br,'then',True),'IsNearby',nearby)
    show=e.add_branch_node();g.wire(entry,show.find_execute_pin());g.wire(ref(e,'IsNearby'),g.pin(show,'Condition'))
    for output,method in [('then','ShowControls'),('else','HideControls')]:after(g.pin(show,output,True),call_self(e,bp,method))
    g.compile_bp(bp)
    e=g.graph(bp)
    for name,on in [('SwitchOn',True),('SwitchOff',False)]:
        ev=g.event(bp,name);entry=store(e,g.then(ev),'IsOn',literal=str(on).lower())
        cap=g.call(e,'/Script/Engine.PrimitiveComponent.SetMaterial');g.wire(ref(e,'SwitchCap'),g.pin(cap,'self'));g.value(cap,'Material','/Game/StealthShooter/Interaction/M_'+('ButtonCap.M_ButtonCap' if on else 'BulbOff.M_BulbOff'));entry=after(entry,cap)
        loop=e.add_macro_node('/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForEachLoop');g.wire(ref(e,'SwitchTargets'),g.pin(loop,'Array'));g.wire(entry,g.pin(loop,'Exec'))
        obj=g.pin(loop,'Array Element',True);entry=valid(e,obj,g.pin(loop,'LoopBody',True));n=message(e,name,obj);after(entry,n)
        entry=valid(e,ref(e,'ControlWidget'),g.pin(loop,'Completed',True));refresh=g.call(e,widget.generated_class().get_path_name()+':RefreshDisplay');g.wire(ref(e,'ControlWidget'),g.pin(refresh,'self'));after(entry,refresh)
    g.compile_bp(bp)
    e=g.graph(bp);ev=g.event(bp,'ReceiveBeginPlay')
    create=g.named_node(e,lambda n:n.endswith('|создатьвиджет') or n.endswith('|createwidget'),'Create Widget');g.value(create,'Class',widget.generated_class().get_path_name());g.wire(controller(e),g.pin(create,'OwningPlayer'));entry=after(g.then(ev),create)
    entry=store(e,entry,'ControlWidget',g.result(create))
    for name,pinvalue in [('OwnerSwitch',self_ref(e)),('UseRadius',ref(e,'InteractionRadius')),('PanelLabel',ref(e,'GroupLabel'))]:
        n=g.set_variable(e,name,widget.generated_class().get_path_name());g.wire(ref(e,'ControlWidget'),g.pin(n,'self'));g.wire(pinvalue,g.pin(n,name));entry=after(entry,n)
    n=message(e,'SwitchOn',self_ref(e));entry=after(entry,n)
    timer=g.call(e,'/Script/Engine.KismetSystemLibrary.K2_SetTimer');g.wire(self_ref(e),g.pin(timer,'Object'));g.value(timer,'FunctionName','UpdateProximity');g.value(timer,'Time',.1);g.value(timer,'bLooping','true');after(entry,timer)
    ev=g.event(bp,'ReceiveEndPlay');entry=valid(e,ref(e,'ControlWidget'),g.then(ev));n=g.call(e,'/Script/UMG.Widget.RemoveFromParent');g.wire(ref(e,'ControlWidget'),g.pin(n,'self'));after(entry,n)
    finalize(bp)
    return True


def level():
    levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    path='/Game/StealthShooter/Maps/L_GroupControl'
    assert not unreal.EditorLevelLibrary.get_pie_worlds(False)
    assert levels.load_level(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else levels.new_level(path)
    sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    def actor(cls,label,loc,rot=None):
        a=next((a for a in sub.get_all_level_actors() if a.get_actor_label()==label),None)
        if a is None:a=sub.spawn_actor_from_class(cls,unreal.Vector(*loc),rot or unreal.Rotator())
        a.set_actor_label(label);a.set_actor_location(unreal.Vector(*loc),False,False)
        if rot:a.set_actor_rotation(rot,False)
        return a
    def mesh(label,loc,scale,mat):
        a=actor(unreal.StaticMeshActor,label,loc);a.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'));a.set_actor_scale3d(unreal.Vector(*scale));a.static_mesh_component.set_material(0,unreal.load_asset('/Game/StealthShooter/Interaction/'+mat));return a
    def text(label,value,loc,size):
        a=actor(unreal.TextRenderActor,label,loc,unreal.Rotator(yaw=180));t=a.text_render;t.set_text(value);t.set_world_size(size);t.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER);t.set_editor_property('text_material',unreal.load_asset('/Game/StealthShooter/Interaction/M_LabText'));return a
    mesh('Hall_Floor',(0,0,-20),(22,31,.4),'M_Floor')
    mesh('Hall_BackWall',(1000,0,180),(.25,31,3.6),'M_Wall')
    for sign in [-1,1]:mesh('Hall_Side_'+str(sign),(0,sign*1550,180),(22,.25,3.6),'M_Wall')
    mesh('Hall_FrontRail',(-1100,0,40),(.25,31,.8),'M_Body')
    for index,y in enumerate([-850,0,850]):
        letter='ABC'[index]
        button=actor(unreal.load_asset(ROOT+'/BP_GroupSwitch').generated_class(),'GroupSwitch_'+letter,(0,y,0))
        button.set_editor_property('GroupLabel','Группа '+letter+' · 2 светильника')
        lamps=[]
        for j,offset in enumerate([-200,200],1):
            lamp=actor(unreal.load_asset('/Game/StealthShooter/Interaction/BP_SwitchableLamp').generated_class(),'Group_'+letter+'_Lamp_'+str(j),(600,y+offset,0))
            lamp.set_editor_property('ControlButton',None)
            lamp.get_editor_property('LampLight').set_light_color(unreal.LinearColor(*[(.35,.68,1),(.30,1,.64),(1,.68,.28)][index]))
            lamps.append(lamp)
            mesh('Pad_'+letter+str(j),(600,y+offset,4),(1.3,1.3,.08),'M_Body')
        button.set_editor_property('SwitchTargets',lamps)
        text('Group_Label_'+letter,'GROUP '+letter,(980,y,255),44)
        text('Group_Details_'+letter,'2 LIGHTS  /  LOCAL ARRAY',(978,y,195),19)
        for dy in [-350,350]:mesh('Zone_Line_'+letter+str(dy),(340,y+dy,4),(12,.09,.04),'M_Accent')
    text('Hall_Title','4.4  /  UMG GROUP CONTROL',(980,0,340),28)
    actor(unreal.PlayerStart,'PlayerStart',(-550,0,96),unreal.Rotator(yaw=0))
    sun=actor(unreal.DirectionalLight,'AmbientFill',(0,0,700),unreal.Rotator(pitch=-55,yaw=-30));sun.light_component.set_intensity(.6);sun.light_component.set_light_color(unreal.LinearColor(.45,.62,1))
    pp=actor(unreal.PostProcessVolume,'FixedExposure',(0,0,0));pp.set_editor_property('unbound',True)
    settings=pp.get_editor_property('settings')
    for name,value in [('override_auto_exposure_min_brightness',True),('override_auto_exposure_max_brightness',True),('auto_exposure_min_brightness',1),('auto_exposure_max_brightness',1)]:settings.set_editor_property(name,value)
    pp.set_editor_property('settings',settings)
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world();world.get_world_settings().set_editor_property('default_game_mode',unreal.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonGameMode').generated_class())
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(unreal.Vector(-800,0,280),unreal.Rotator(pitch=-7,yaw=0))
    assert levels.save_current_level()
    return {'map':path,'groups':3,'lamps':6}
