"""Add hold/release charge input and a compact UMG power meter to the catapult."""
import unreal
import build_catapult as c
import maze_graph as m
import build_maze_interface as ui
from build_blueprint_lab import variable,ref,store,after
from build_switchable_room import self_ref
B=c.B;g=c.g

def widget():
    path=c.ROOT+'/WBP_CatapultHUD';bp=unreal.load_asset(path)
    if bp:return bp
    bp=unreal.EditorAssetLibrary.duplicate_asset('/Game/StealthShooter/Maze/Interface/WBP_MazeHUD',path)
    tree,root=ui.clean_widget(bp)
    panel=unreal.find_object(tree,'ChargePanel') or unreal.new_object(unreal.Border,tree,'ChargePanel')
    panel.set_brush_color(unreal.LinearColor(.008,.015,.025,.92));ui.canvas(root,panel,(.5,1),(.5,1),(0,-25),(570,145))
    content=unreal.find_object(tree,'ChargeContent') or unreal.new_object(unreal.CanvasPanel,tree,'ChargeContent');content.clear_children();panel.set_content(content)
    ui.canvas(content,ui.text(tree,'ChargeTitle','НАТЯЖЕНИЕ КАТАПУЛЬТЫ',16,(.86,.73,.48)),(0,0),(0,0),(22,12),(520,24))
    state=ui.text(tree,'StatusText','Удерживайте F → отпустите для броска',19)
    ui.canvas(content,state,(0,0),(0,0),(22,39),(530,30))
    bar=unreal.find_object(tree,'PowerBar') or unreal.new_object(unreal.ProgressBar,tree,'PowerBar');bar.set_percent(.2);bar.set_fill_color_and_opacity(unreal.LinearColor(.12,.7,.58,1))
    ui.canvas(content,bar,(0,0),(0,0),(22,79),(520,17))
    ui.canvas(content,ui.text(tree,'WeakLabel','СЛАБО',13,(.55,.69,.71)),(0,0),(0,0),(22,106),(200,20))
    strong=ui.text(tree,'StrongLabel','СИЛЬНО',13,(1,.59,.26));strong.set_editor_property('justification',unreal.TextJustify.RIGHT)
    ui.canvas(content,strong,(1,0),(1,0),(-22,106),(200,20))
    e=g.new_function(bp,'UpdateDisplay');percent=g.input_parameter(e,'Percent',m.REAL);message=g.input_parameter(e,'Message',m.STRING)
    n=g.call(e,'/Script/UMG.ProgressBar.SetPercent');g.wire(ref(e,'PowerBar'),g.pin(n,'self'));g.wire(percent,g.pin(n,'InPercent'));entry=after(e.find_graph_entry_pin(),n)
    color=g.call(e,'/Script/Engine.KismetMathLibrary.LinearColorLerp');g.value(color,'A','(R=0.12,G=0.7,B=0.58,A=1)');g.value(color,'B','(R=1,G=0.34,B=0.08,A=1)');g.wire(percent,g.pin(color,'Alpha'))
    n=g.call(e,'/Script/UMG.ProgressBar.SetFillColorAndOpacity');g.wire(ref(e,'PowerBar'),g.pin(n,'self'));g.wire(g.result(color),g.pin(n,'InColor'));entry=after(entry,n)
    ui.set_text(e,ref(e,'StatusText'),message,entry)
    m.finish(bp,{'UpdateDisplay':'Show normalized throw power and the current input/reload state. The meter changes appearance without changing input focus.'})
    return bp

def build():
    assert not unreal.EditorLevelLibrary.get_pie_worlds(False)
    hud=widget();cat=c.asset('BP_Catapult')
    for name,typ,default,editable in [('bCharging',m.BOOL,'false',False),('Charge',m.REAL,'.2',False),('ChargeStartedAt',m.REAL,'0',False),('FullChargeSeconds',m.REAL,'2',True),('MinCharge',m.REAL,'.2',True),('LastShotCharge',m.REAL,'0',False),('HUDWidget',B.get_object_reference_type(hud.generated_class()),'',False)]:
        variable(cat,name,typ,default,editable);B.set_blueprint_variable_category(cat,name,'Catapult|Charge')
    for name in ['BeginCharge','UpdateCharge','ReleaseCharge','InitializeHUD','RefreshHUD']:g.new_function(cat,name)
    g.compile_bp(cat)
    # Rebuild the original physical cycle, then replace only its input and drive-strength selection.
    c.graphs()
    e=unreal.BlueprintGraphEditor.get_graph_editor_by_name(cat,'Fire')
    drive=next(n for n in e.list_all_nodes() if str(n.get_node_title())=='SetAngularDriveParams')
    lerp=c.call(e,'KismetMathLibrary','Lerp',A=30,B=220,Alpha=ref(e,'Charge'));g.wire(g.result(lerp),g.pin(drive,'PositionStrength'))
    # LastShotCharge is recorded on the release path, before the physical drive starts.
    e=g.new_function(cat,'BeginCharge');condition=m.op(e,'BooleanAND',ref(e,'bReady'),m.op(e,'Not_PreBool',ref(e,'bCharging')))
    guard=m.branch(e,e.find_graph_entry_pin(),condition);entry=store(e,g.pin(guard,'then',True),'bCharging',literal='true')
    entry=store(e,entry,'Charge',ref(e,'MinCharge'));entry=store(e,entry,'ChargeStartedAt',m.now(e));m.timer(e,entry,'UpdateCharge',.02,True)
    e=g.new_function(cat,'UpdateCharge');guard=m.branch(e,e.find_graph_entry_pin(),ref(e,'bCharging'));entry=g.pin(guard,'then',True)
    duration=m.op(e,'FMax',ref(e,'FullChargeSeconds'),.1);alpha=m.op(e,'Divide_DoubleDouble',m.op(e,'Subtract_DoubleDouble',m.now(e),ref(e,'ChargeStartedAt')),duration)
    clamp=c.call(e,'KismetMathLibrary','FClamp',Value=alpha,Min=0,Max=1);lerp=c.call(e,'KismetMathLibrary','Lerp',A=ref(e,'MinCharge'),B=1,Alpha=g.result(clamp))
    store(e,entry,'Charge',g.result(lerp))
    e=g.new_function(cat,'ReleaseCharge');guard=m.branch(e,e.find_graph_entry_pin(),ref(e,'bCharging'));entry=after(g.pin(guard,'then',True),c.own(e,cat,'UpdateCharge'))
    entry=store(e,entry,'bCharging',literal='false');entry=m.clear_timer(e,entry,'UpdateCharge');entry=store(e,entry,'LastShotCharge',ref(e,'Charge'));after(entry,c.own(e,cat,'Fire'))
    e=g.new_function(cat,'InitializeHUD');n=g.named_node(e,lambda s:s.endswith('|создатьвиджет') or s.endswith('|createwidget'),'Create Widget');g.value(n,'Class',hud.generated_class().get_path_name());g.wire(m.pc(e),g.pin(n,'OwningPlayer'));entry=after(e.find_graph_entry_pin(),n)
    entry=store(e,entry,'HUDWidget',g.result(n));entry=ui.add_view(e,ref(e,'HUDWidget'),entry);m.timer(e,entry,'RefreshHUD',.05,True)
    e=g.new_function(cat,'RefreshHUD');entry=m.valid(e,ref(e,'HUDWidget'),e.find_graph_entry_pin())
    pct=c.call(e,'KismetMathLibrary','Round',A=m.op(e,'Multiply_DoubleDouble',ref(e,'Charge'),100))
    number=c.call(e,'KismetStringLibrary','Conv_IntToString',InInt=g.result(pct))
    choice=c.call(e,'KismetMathLibrary','SelectString',A='ОТПУСТИТЕ F ДЛЯ БРОСКА',B='УДЕРЖИВАЙТЕ F',bPickA=ref(e,'bCharging'))
    state=c.call(e,'KismetMathLibrary','SelectString',A='ПЕРЕЗАРЯДКА...',B=g.result(choice),bPickA=ref(e,'bBusy'))
    message=ui.concat(e,ui.concat(e,ui.concat(e,'СИЛА ',g.result(number)),' %  ·  '),g.result(state))
    n=c.own(e,hud,'UpdateDisplay');g.wire(ref(e,'HUDWidget'),g.pin(n,'self'));g.wire(ref(e,'Charge'),g.pin(n,'Percent'));g.wire(message,g.pin(n,'Message'));after(entry,n)
    e=g.clear_graph(cat);ev=g.event(cat,'ReceiveBeginPlay');entry=after(g.then(ev),c.own(e,cat,'InitializeCatapult'));entry=after(entry,c.own(e,cat,'InitializeHUD'));after(entry,c.call(e,'Actor','EnableInput',PlayerController=m.pc(e)))
    key=g.named_node(e,lambda s:s.endswith('|keyboardevents|f'),'F keyboard input');after(g.pin(key,'Pressed',True),c.own(e,cat,'BeginCharge'));after(g.pin(key,'Released',True),c.own(e,cat,'ReleaseCharge'))
    ev=g.event(cat,'ReceiveEndPlay');entry=g.then(ev)
    for fn in ['LoadBall','BeginReload','UpdateCharge','RefreshHUD','CheckPayloadRelease']:entry=m.clear_timer(e,entry,fn)
    entry=m.valid(e,ref(e,'HUDWidget'),entry);n=g.call(e,'/Script/UMG.Widget.RemoveFromParent');g.wire(ref(e,'HUDWidget'),g.pin(n,'self'));after(entry,n)
    m.finish(cat,{'EventGraph':'Hold F to charge, release F to throw once. Reload ignores input. EndPlay clears all timers and removes the HUD.',
      'BeginCharge':'Start only while ready; charge begins at the minimum useful power. Repeated key-down events cannot restart the charge timer.',
      'UpdateCharge':'Calculate power from elapsed game time, capped at 100 percent. A fixed time source keeps charging independent of frame rate.',
      'ReleaseCharge':'Capture the final charge, cancel the timer and request one physical throw. A release without a valid press does nothing.',
      'Fire':'Interpolate the constraint motor stiffness from the charge. The spoon alone accelerates the physical cannonball through contact; no impulse or assigned velocity.',
      'InitializeHUD':'Create one non-interactive UMG meter; preserve normal Third Person game input.',
      'RefreshHUD':'Update the visible meter, percentage and ready/charging/reloading prompt at 20 Hz.',
      'Reload':'Return and settle the constrained spoon before loading another ball.',
      'LatchPayload':'Hold the loaded physical ball at the spoon with a second physics constraint; never attach or teleport it during firing.',
      'ReleasePayload':'Free all linear axes at the release angle. The joint no longer applies forces, while pair collision filtering prevents the spoon catching the released ball again.',
      'CheckPayloadRelease':'Release the physical payload at a consistent 35-degree arm angle for predictable power selection.',
      'LoadBall':'Load only when the hinge has returned and stopped. Retry safely while the physical arm is still moving.'})
    status=c.component(cat,'StatusText',unreal.TextRenderComponent);status.set_visibility(False);g.save(cat)
    return {'widget':hud.get_path_name(),'input':'Hold F, release to throw','charge_seconds':2,'strength_range':[20,100]}
