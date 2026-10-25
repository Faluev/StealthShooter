"""Lesson 11.5: live HUD, result screens and round rules."""
import unreal
import maze_graph as m
from maze_graph import g,B,ref,store,after,self_ref

def clean_widget(bp):
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    g.clear_graph(bp)
    for gr in list(B.list_graphs(bp)):
        if gr.get_name()!='EventGraph':B.remove_graph(bp,gr)
    for name in list(B.list_member_variable_names(bp,False)):g.graph(bp).remove_member_variable(str(name))
    tree=unreal.find_object(bp,'WidgetTree');root=unreal.find_object(tree,'CanvasPanel_2');root.clear_children()
    return tree,root

def text(tree,name,label,size=20,color=(.85,.92,1)):
    w=unreal.find_object(tree,name) or unreal.new_object(unreal.TextBlock,tree,name)
    w.set_text(label);font=w.get_editor_property('font');font.set_editor_property('size',size);w.set_font(font)
    w.set_color_and_opacity(unreal.SlateColor(specified_color=unreal.LinearColor(*color,1)))
    return w
def canvas(root,w,anchor,alignment,position,size):
    s=root.add_child_to_canvas(w);s.set_anchors(unreal.Anchors(unreal.Vector2D(*anchor),unreal.Vector2D(*anchor)))
    s.set_alignment(unreal.Vector2D(*alignment));s.set_position(unreal.Vector2D(*position));s.set_size(unreal.Vector2D(*size));return s

def design():
    bp=m.asset('WBP_MazeHUD');t,r=clean_widget(bp)
    canvas(r,text(t,'StatusText','ВРЕМЯ  03:00',27),(0,0),(0,0),(34,28),(440,55))
    canvas(r,text(t,'HealthLabel','ЗДОРОВЬЕ',16),(1,0),(1,0),(-34,26),(280,26))
    bar=unreal.find_object(t,'HealthBar') or unreal.new_object(unreal.ProgressBar,t,'HealthBar');bar.set_percent(1);bar.set_fill_color_and_opacity(unreal.LinearColor(.05,.72,.38,1))
    canvas(r,bar,(1,0),(1,0),(-34,56),(280,22))
    icon=unreal.find_object(t,'TrophyIcon') or unreal.new_object(unreal.Image,t,'TrophyIcon')
    brush=icon.get_editor_property('brush');brush.set_editor_property('tint_color',unreal.SlateColor(specified_color=unreal.LinearColor(1,.68,.12,1)));icon.set_brush(brush)
    icon.set_visibility(unreal.SlateVisibility.HIDDEN);canvas(r,icon,(1,1),(1,1),(-34,-34),(34,34))
    canvas(r,text(t,'TrophyLabel','ТРОФЕЙ',17,(1,.75,.25)),(1,1),(1,1),(-80,-33),(120,34))
    canvas(r,text(t,'ControlsHint','WASD — движение · E — взаимодействие',17),(0,1),(0,1),(34,-30),(700,32))
    canvas(r,text(t,'ObjectiveHint','Найдите сокровище и вернитесь к выходу',18),(0,0),(0,0),(34,82),(740,32))
    m.function(bp,'RefreshHUD');m.function(bp,'RefreshHealth');m.function(bp,'RefreshTime');m.function(bp,'RefreshTrophy');g.compile_bp(bp)
    for name,victory in [('WBP_MazeWin',True),('WBP_MazeLose',False)]:
        bp=m.asset(name);t,r=clean_widget(bp)
        panel=unreal.find_object(t,'ResultPanel') or unreal.new_object(unreal.Border,t,'ResultPanel');panel.set_brush_color(unreal.LinearColor(.015,.025,.045,.98));panel.set_padding(unreal.Margin(30))
        canvas(r,panel,(.5,.5),(.5,.5),(0,0),(600,330))
        box=unreal.find_object(t,'ResultContent') or unreal.new_object(unreal.VerticalBox,t,'ResultContent');box.clear_children();panel.set_content(box)
        title=text(t,'StatusText','ПОБЕДА' if victory else 'ПОРАЖЕНИЕ',40,(.35,.95,.68) if victory else (1,.4,.36));title.set_editor_property('justification',unreal.TextJustify.CENTER)
        box.add_child_to_vertical_box(title).set_padding(unreal.Margin(0,12,0,25))
        subtitle=text(t,'ResultDescription','Сокровище успешно вынесено!' if victory else 'Закончилось здоровье или время.',21);subtitle.set_editor_property('justification',unreal.TextJustify.CENTER)
        box.add_child_to_vertical_box(subtitle).set_padding(unreal.Margin(0,0,0,32))
        button=unreal.find_object(t,'ButtonOn');button.set_is_enabled(True);button.set_editor_property('is_focusable',True)
        button.set_background_color(unreal.LinearColor(.04,.28,.48,1));label=text(t,'RestartLabel','НАЧАТЬ СНАЧАЛА',22);label.set_editor_property('justification',unreal.TextJustify.CENTER);button.set_content(label)
        box.add_child_to_vertical_box(button).set_padding(unreal.Margin(30,10,30,10))
        m.function(bp,'OnRestartClicked');g.compile_bp(bp)
    gm=m.asset('BP_MazeGameMode')
    m.var(gm,'HUDWidget',B.get_object_reference_type(m.asset('WBP_MazeHUD').generated_class()))
    m.var(gm,'ResultWidget',B.get_object_reference_type(unreal.UserWidget))
    cdo=unreal.get_default_object(gm.generated_class());cdo.set_editor_property('default_pawn_class',m.asset('BP_MazeCharacter').generated_class())
    g.compile_bp(gm)
    return True

def set_text(e,target,value,entry):
    conv=g.call(e,'/Script/Engine.KismetTextLibrary.Conv_StringToText');g.wire(value,g.pin(conv,'InString'))
    n=g.call(e,'/Script/UMG.TextBlock.SetText');g.wire(target,g.pin(n,'self'));g.wire(g.result(conv),g.pin(n,'InText'));return after(entry,n)
def concat(e,a,b):
    n=g.call(e,'/Script/Engine.KismetStringLibrary.Concat_StrStr')
    for key,val in [('A',a),('B',b)]:
        if hasattr(val,'is_valid'):g.wire(val,g.pin(n,key))
        else:g.value(n,key,val)
    return g.result(n)

def hud():
    bp=m.asset('WBP_MazeHUD')
    e=m.function(bp,'RefreshHealth');player,entry=m.player(e,e.find_graph_entry_pin())
    health=m.member(e,'BP_MazeCharacter','HealthComponent',player)
    pct=m.op(e,'Divide_DoubleDouble',m.member(e,'BPC_Health','Health',health),100)
    n=g.call(e,'/Script/UMG.ProgressBar.SetPercent');g.wire(ref(e,'HealthBar'),g.pin(n,'self'));g.wire(pct,g.pin(n,'InPercent'));m.ret(e,after(entry,n));g.compile_bp(bp)
    e=m.function(bp,'RefreshTrophy');player,entry=m.player(e,e.find_graph_entry_pin())
    br=m.branch(e,entry,m.member(e,'BP_MazeCharacter','bHasTrophy',player))
    for pin,visibility in [('then','Visible'),('else','Hidden')]:
        n=g.call(e,'/Script/UMG.Widget.SetVisibility');g.wire(ref(e,'TrophyIcon'),g.pin(n,'self'));g.value(n,'InVisibility',visibility);m.ret(e,after(g.pin(br,pin,True),n))
    g.compile_bp(bp)
    e=m.function(bp,'RefreshTime');mode,entry=m.mode(e,e.find_graph_entry_pin())
    seconds=g.call(e,'/Script/Engine.KismetMathLibrary.FCeil');g.wire(m.member(e,'BP_MazeGameMode','RemainingTime',mode),g.pin(seconds,'A'))
    minutes=m.op(e,'Divide_IntInt',g.result(seconds),60);remainder=m.op(e,'Percent_IntInt',g.result(seconds),60)
    minstr=g.call(e,'/Script/Engine.KismetStringLibrary.Conv_IntToString');g.wire(minutes,g.pin(minstr,'InInt'))
    secstr=g.call(e,'/Script/Engine.KismetStringLibrary.Conv_IntToString');g.wire(remainder,g.pin(secstr,'InInt'))
    select=g.call(e,'/Script/Engine.KismetMathLibrary.SelectString');g.wire(concat(e,'0',g.result(secstr)),g.pin(select,'A'));g.wire(g.result(secstr),g.pin(select,'B'));g.wire(m.op(e,'Less_IntInt',remainder,10),g.pin(select,'bPickA'))
    combined=concat(e,concat(e,concat(e,'ВРЕМЯ  ',g.result(minstr)),':'),g.result(select))
    m.ret(e,set_text(e,ref(e,'StatusText'),combined,entry));g.compile_bp(bp)
    e=m.function(bp,'RefreshHUD');entry=e.find_graph_entry_pin()
    for f in ['RefreshHealth','RefreshTime','RefreshTrophy']:entry=after(entry,m.own(e,bp,f))
    m.ret(e,entry)
    m.finish(bp,{'RefreshHealth':'Read the reusable component and normalize Health 0..100 to ProgressBar 0..1.', 'RefreshTime':'Display rounded-up remaining time as minutes:two-digit-seconds.', 'RefreshTrophy':'The trophy image stays hidden until the character owns the collectible.', 'RefreshHUD':'GameMode refreshes the existing HUD every 0.1 seconds; no widgets are recreated during updates.'})
    return True

def result_widgets():
    for name in ['WBP_MazeWin','WBP_MazeLose']:
        bp=m.asset(name);e=m.function(bp,'OnRestartClicked');mode,entry=m.mode(e,e.find_graph_entry_pin());m.ret(e,after(entry,m.method(e,'BP_MazeGameMode','RestartLevel',mode)))
        g.compile_bp(bp);e=g.clear_graph(bp);ev=g.event(bp,'Construct')
        bind=g.named_node(e,lambda n:n=='кнопка|событие|bindeventtoonclicked','Button OnClicked');g.wire(ref(e,'ButtonOn'),g.pin(bind,'self'))
        delegate=g.named_node(e,lambda n:n.endswith('|создатьсобытие') or n.endswith('|createevent'),'Create Event');g.wire(self_ref(e),g.pin(delegate,'self'));g.wire(g.pin(delegate,'OutputDelegate',True),g.pin(bind,'Delegate'))
        B.set_create_delegate_function(delegate,'OnRestartClicked');assert str(B.get_create_delegate_function(delegate))=='OnRestartClicked';after(g.then(ev),bind)
        m.finish(bp,{'EventGraph':'Bind the visible restart button to this result screen instance.', 'OnRestartClicked':'Restart through GameMode so the whole current level is recreated.'})
    return True

def create_widget(e,name,entry):
    n=g.named_node(e,lambda s:s.endswith('|создатьвиджет') or s.endswith('|createwidget'),'Create Widget')
    g.value(n,'Class',m.asset(name).generated_class().get_path_name());g.wire(m.pc(e),g.pin(n,'OwningPlayer'));return g.result(n),after(entry,n)
def add_view(e,widget,entry):
    n=g.call(e,'/Script/UMG.UserWidget.AddToViewport');g.wire(widget,g.pin(n,'self'));return after(entry,n)

def world():
    bp=m.asset('BP_MazeGameMode');e=g.clear_graph(bp);ev=g.event(bp,'ReceiveBeginPlay');after(g.then(ev),m.own(e,bp,'StartRound'))
    ev=g.event(bp,'ReceiveEndPlay');m.clear_timer(e,g.then(ev),'UpdateRound')
    e=m.function(bp,'FocusResult');entry=e.find_graph_entry_pin()
    n=g.call(e,'/Script/UMG.WidgetBlueprintLibrary.SetInputMode_UIOnlyEx');g.wire(m.pc(e),g.pin(n,'PlayerController'));g.wire(ref(e,'ResultWidget'),g.pin(n,'InWidgetToFocus'));entry=after(entry,n)
    n=g.set_variable(e,'bShowMouseCursor','/Script/Engine.PlayerController');g.wire(m.pc(e),g.pin(n,'self'));g.value(n,'bShowMouseCursor','true');m.ret(e,after(entry,n));g.compile_bp(bp)
    e=m.function(bp,'StartRound');entry=store(e,e.find_graph_entry_pin(),'RoundStartedAt',m.now(e))
    entry=store(e,entry,'RemainingTime',ref(e,'RoundDuration'));entry=store(e,entry,'bFinished',literal='false');entry=store(e,entry,'bWon',literal='false')
    hud,entry=create_widget(e,'WBP_MazeHUD',entry);entry=store(e,entry,'HUDWidget',hud);entry=add_view(e,ref(e,'HUDWidget'),entry)
    n=g.call(e,'/Script/UMG.WidgetBlueprintLibrary.SetInputMode_GameOnly');g.wire(m.pc(e),g.pin(n,'PlayerController'));entry=after(entry,n)
    n=g.set_variable(e,'bShowMouseCursor','/Script/Engine.PlayerController');g.wire(m.pc(e),g.pin(n,'self'));g.value(n,'bShowMouseCursor','false');entry=after(entry,n)
    m.ret(e,m.timer(e,entry,'UpdateRound',.1,True));g.compile_bp(bp)
    e=m.function(bp,'UpdateRound');br=m.branch(e,e.find_graph_entry_pin(),m.op(e,'Not_PreBool',ref(e,'bFinished')));entry=g.pin(br,'then',True)
    remaining=m.op(e,'FMax',m.op(e,'Subtract_DoubleDouble',ref(e,'RoundDuration'),m.op(e,'Subtract_DoubleDouble',m.now(e),ref(e,'RoundStartedAt'))),0)
    entry=store(e,entry,'RemainingTime',remaining);entry=m.valid(e,ref(e,'HUDWidget'),entry);entry=after(entry,m.method(e,'WBP_MazeHUD','RefreshHUD',ref(e,'HUDWidget')))
    br=m.branch(e,entry,m.op(e,'LessEqual_DoubleDouble',ref(e,'RemainingTime'),0));after(g.pin(br,'then',True),m.own(e,bp,'Lose'));g.compile_bp(bp)
    e=m.function(bp,'FinishRound');victory=g.input_parameter(e,'bVictory',m.BOOL)
    br=m.branch(e,e.find_graph_entry_pin(),m.op(e,'Not_PreBool',ref(e,'bFinished')));entry=store(e,g.pin(br,'then',True),'bFinished',literal='true');entry=store(e,entry,'bWon',victory)
    entry=m.clear_timer(e,entry,'UpdateRound')
    n=g.call(e,'/Script/UMG.Widget.RemoveFromParent');g.wire(ref(e,'HUDWidget'),g.pin(n,'self'));entry=after(entry,n)
    br=m.branch(e,entry,victory)
    for pin,widget in [('then','WBP_MazeWin'),('else','WBP_MazeLose')]:
        result,entry=create_widget(e,widget,g.pin(br,pin,True));entry=store(e,entry,'ResultWidget',result);entry=add_view(e,ref(e,'ResultWidget'),entry)
        m.ret(e,after(entry,m.own(e,bp,'FocusResult')))
    g.compile_bp(bp)
    for name,value in [('Win','true'),('Lose','false')]:
        e=m.function(bp,name);n=m.own(e,bp,'FinishRound');g.value(n,'bVictory',value);m.ret(e,after(e.find_graph_entry_pin(),n))
    e=m.function(bp,'RestartLevel');n=g.call(e,'/Script/Engine.GameplayStatics.GetCurrentLevelName');g.value(n,'bRemovePrefixString','true')
    level=g.call(e,'/Script/Engine.GameplayStatics.OpenLevel');g.wire(g.result(n),g.pin(level,'LevelName'));entry=after(e.find_graph_entry_pin(),n);m.ret(e,after(entry,level))
    m.finish(bp,{'StartRound':'Create one HUD for this map and start the configurable round clock. Input starts in GameOnly mode.', 'UpdateRound':'Refresh remaining time and HUD. Expiration requests one loss.', 'FinishRound':'Resolve the round once, stop the clock, replace HUD with the correct result screen and hand mouse input to its restart button.', 'RestartLevel':'Reload the current map without a PIE prefix. All actors, health, trophy and round time return to initial state.'})
    return True
