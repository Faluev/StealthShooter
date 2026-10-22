"""Complete the supplied traffic-light exercise and related lesson examples."""
import json
import unreal
import lab_graph as g
from build_blueprint_lab import variable, after, store, ref, struct_node, field, finalize

B=unreal.BlueprintEditorLibrary
ROOT='/Game/Blueprints'

def prepare():
    bp=unreal.load_asset(ROOT+'/BP_TrafficLightsManager')
    enum=unreal.load_asset(ROOT+'/E_LightColor')
    enum_type=unreal.EdGraphPinType()
    assert enum_type.import_text('(PinCategory="byte",PinSubCategoryObject=UserDefinedEnum\''+enum.get_path_name()+'\')')
    integer=B.get_basic_type_by_name('int'); boolean=B.get_basic_type_by_name('bool'); real=B.get_basic_type_by_name('real')
    # The template spells the light class TraffictLight. Keep its references intact.
    light=unreal.load_asset(ROOT+'/BP_TraffictLight')
    for name,kind,default,editable in [
        ('ColorOrder',B.get_array_type(enum_type),'',False),
        ('Lights',B.get_array_type(B.get_object_reference_type(light.generated_class())),'',True),
        ('ColorIndex',integer,'0',False),('CycleCount',integer,'0',False),
        ('Interval',real,'2.0',True),('VariableIntervals',boolean,'false',True),
        ('NextDelay',real,'2.0',False),
        ('TimerHandle',B.get_struct_type(unreal.TimerHandle.static_struct()),'',False),
        ('SettingsRow',B.get_struct_type(unreal.DataTableRowHandle.static_struct()),'',True),
        ('LoadedSettings',boolean,'false',False)]:variable(bp,name,kind,default,editable)
    g.compile_bp(bp)
    factory=unreal.DataTableFactory();factory.set_editor_property('struct',unreal.load_asset(ROOT+'/S_LIghtColor'))
    table=unreal.load_asset(ROOT+'/DT_TrafficSettings') or unreal.AssetToolsHelpers.get_asset_tools().create_asset('DT_TrafficSettings',ROOT,unreal.DataTable,factory)
    base={'Green':{'R':0.025297,'G':1,'B':0,'A':1},'Yellow':{'R':1,'G':0.795985,'B':0,'A':1},'Red':{'R':1,'G':0,'B':0.039114,'A':1}}
    data=[]
    for name,multiplier in [('Default',1),('LowBrightness',.5),('HighVisibility',1.5)]:
        colors=json.loads(json.dumps(base))
        for color in colors.values():
            for channel in ['R','G','B']:color[channel]*=multiplier
        data.append({'Name':name,'ColorMap':colors})
    assert unreal.DataTableFunctionLibrary.fill_data_table_from_json_string(table,json.dumps(data))
    g.save(table)
    return {'table':unreal.DataTableFunctionLibrary.export_data_table_to_json_string(table),'enum_nodes':[str(n) for n in g.graph(bp).list_available_nodes([]) if str(n).replace(' ','').lower().endswith('|switchone_lightcolor')]}

def invoke(e,bp,name,entry):
    n=g.call(e,bp.generated_class().get_path_name()+':'+name)
    return after(entry,n)

def increment(e,entry,name):
    add=g.call(e,'/Script/Engine.KismetMathLibrary.Add_IntInt')
    g.wire(ref(e,name),g.pin(add,'A'));g.value(add,'B',1)
    return store(e,entry,name,g.result(add))

def timer(e,entry,function,seconds=None,seconds_pin=None,loop=False):
    n=g.call(e,'/Script/Engine.KismetSystemLibrary.K2_SetTimer')
    self_node=g.named_node(e,lambda n:n.endswith('|getareferencetoself') or n.endswith('|получитьссылкунасебя'),'self')
    g.wire(g.result(self_node),g.pin(n,'Object'));g.value(n,'FunctionName',function);g.value(n,'bLooping',str(loop).lower())
    if seconds_pin is not None:g.wire(seconds_pin,g.pin(n,'Time'))
    else:g.value(n,'Time',seconds)
    return n,after(entry,n)

def build():
    bp=unreal.load_asset(ROOT+'/BP_TrafficLightsManager')
    light=unreal.load_asset(ROOT+'/BP_TraffictLight')
    g.clear_graph(bp)
    previous=B.find_graph(bp,'Recolor_0')
    if previous and not B.find_graph(bp,'Recolor'):B.rename_graph(previous,'Recolor')
    e=g.new_function(bp,'LoadSettings');entry=e.find_graph_entry_pin()
    br=struct_node(e,'Break','DataTableRowHandle')
    g.wire(ref(e,'SettingsRow'),g.pin(br,'DataTableRowHandle'))
    row=g.call(e,'/Script/Engine.DataTableFunctionLibrary.GetDataTableRowFromName')
    g.wire(g.pin(br,'DataTable',True),g.pin(row,'Table'));g.wire(g.pin(br,'RowName',True),g.pin(row,'RowName'))
    entry=after(entry,row)
    entry=store(e,entry,'LoadedSettings',g.result(row))
    branch=e.add_branch_node();g.wire(entry,branch.find_execute_pin());g.wire(g.result(row),g.pin(branch,'Condition'))
    store(e,g.pin(branch,'then',True),'ColorSettings',g.pin(row,'OutRow',True))
    g.compile_bp(bp)

    e=g.new_function(bp,'ScheduleNext');entry=e.find_graph_entry_pin()
    branch=e.add_branch_node();g.wire(entry,branch.find_execute_pin());g.wire(ref(e,'VariableIntervals'),g.pin(branch,'Condition'))
    switch=g.named_node(e,lambda n:n.endswith('|switchone_lightcolor'),'Switch on E_LightColor')
    g.wire(g.pin(branch,'then',True),switch.find_execute_pin());g.wire(ref(e,'CurrentColor'),g.pin(switch,'Selection'))
    paths=[store(e,g.pin(branch,'else',True),'NextDelay',ref(e,'Interval'))]
    # Internal enum identifiers come from the supplied E_LightColor asset.
    for key,duration in [('NewEnumerator0',5),('NewEnumerator1',1),('NewEnumerator2',3)]:
        paths.append(store(e,g.pin(switch,key,True),'NextDelay',literal=str(duration)))
    t,_=timer(e,paths[0],'Recolor',seconds_pin=ref(e,'NextDelay'))
    for path in paths[1:]:g.wire(path,t.find_execute_pin())
    store(e,g.then(t),'TimerHandle',g.result(t))
    g.compile_bp(bp)

    e=g.new_function(bp,'Recolor');entry=e.find_graph_entry_pin()
    length=g.call(e,'/Script/Engine.KismetArrayLibrary.Array_Length');g.wire(ref(e,'ColorOrder'),g.pin(length,'TargetArray'))
    positive=g.call(e,'/Script/Engine.KismetMathLibrary.Greater_IntInt');g.wire(g.result(length),g.pin(positive,'A'));g.value(positive,'B',0)
    guard=e.add_branch_node();g.wire(entry,guard.find_execute_pin());g.wire(g.result(positive),g.pin(guard,'Condition'))
    index=g.call(e,'/Script/Engine.KismetMathLibrary.Percent_IntInt');g.wire(ref(e,'ColorIndex'),g.pin(index,'A'));g.wire(g.result(length),g.pin(index,'B'))
    get=g.call(e,'/Script/Engine.KismetArrayLibrary.Array_Get');g.wire(ref(e,'ColorOrder'),g.pin(get,'TargetArray'));g.wire(g.result(index),g.pin(get,'Index'))
    entry=store(e,g.pin(guard,'then',True),'CurrentColor',g.pin(get,'Item',True))
    br=struct_node(e,'Break','S_LIghtColor');g.wire(ref(e,'ColorSettings'),g.pin(br,'S_LIghtColor'))
    find=g.call(e,'/Script/Engine.BlueprintMapLibrary.Map_Find');g.wire(field(br,'ColorMap',True),g.pin(find,'TargetMap'));g.wire(ref(e,'CurrentColor'),g.pin(find,'Key'))
    found=e.add_branch_node();g.wire(entry,found.find_execute_pin());g.wire(g.result(find),g.pin(found,'Condition'))
    loop=e.add_macro_node('/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForEachLoop')
    g.wire(g.pin(found,'then',True),g.pin(loop,'Exec'));g.wire(ref(e,'Lights'),g.pin(loop,'Array'))
    valid=g.call(e,'/Script/Engine.KismetSystemLibrary.IsValid');g.wire(g.pin(loop,'Array Element',True),g.pin(valid,'Object'))
    ok=e.add_branch_node();g.wire(g.pin(loop,'LoopBody',True),ok.find_execute_pin());g.wire(g.result(valid),g.pin(ok,'Condition'))
    change=g.call(e,light.generated_class().get_path_name()+':ChangeColor');g.wire(g.pin(loop,'Array Element',True),g.pin(change,'self'));g.wire(g.pin(find,'Value',True),g.pin(change,'Color'));g.wire(g.pin(ok,'then',True),change.find_execute_pin())
    entry=increment(e,g.pin(loop,'Completed',True),'CycleCount')
    entry=increment(e,entry,'ColorIndex');invoke(e,bp,'ScheduleNext',entry)
    g.compile_bp(bp)

    e=g.new_function(bp,'InitializeTraffic');entry=invoke(e,bp,'LoadSettings',e.find_graph_entry_pin())
    br=struct_node(e,'Break','S_LIghtColor');g.wire(ref(e,'ColorSettings'),g.pin(br,'S_LIghtColor'))
    keys=g.call(e,'/Script/Engine.BlueprintMapLibrary.Map_Keys');g.wire(field(br,'ColorMap',True),g.pin(keys,'TargetMap'));entry=after(entry,keys)
    entry=store(e,entry,'ColorOrder',g.pin(keys,'Keys',True))
    all_lights=g.call(e,'/Script/Engine.GameplayStatics.GetAllActorsOfClass');g.value(all_lights,'ActorClass',light.generated_class().get_path_name());entry=after(entry,all_lights)
    entry=store(e,entry,'Lights',g.pin(all_lights,'OutActors',True));entry=store(e,entry,'ColorIndex',literal='0');invoke(e,bp,'Recolor',entry)
    g.compile_bp(bp)
    eg=g.clear_graph(bp);ev=g.event(bp,'ReceiveBeginPlay')
    timer(eg,g.then(ev),'InitializeTraffic',seconds=.2)
    finalize(bp)
    comments={'LoadSettings':'1.7: Read the selected Data Table row; retain ColorSettings when the row is missing.',
              'ScheduleNext':'1.6 / 1.8: Enum Switch selects durations. A one-shot timer schedules the next cycle without Tick.',
              'Recolor':'1.9: Select the next ColorSettings key, find its color and call ChangeColor on each valid light.',
              'InitializeTraffic':'Capture the configured key sequence once and gather the supplied light actors after Begin Play.'}
    for name,text in comments.items():
        e=unreal.BlueprintGraphEditor.get_graph_editor(B.find_graph(bp,name))
        e.add_comment_to_nodes(text,e.list_all_nodes())
    g.save(bp)
    return True

def data_table_examples():
    g.BP_ROOT='/Game/StealthShooter/Blueprints'
    bp=g.blueprint('BP_DataTableExamples',unreal.Actor)
    for name,kind in [('RowCount',B.get_basic_type_by_name('int')),('FoundCount',B.get_basic_type_by_name('int')),('Completed',B.get_basic_type_by_name('bool')),('LastSettings',B.get_struct_type(unreal.load_asset(ROOT+'/S_LIghtColor')))]:variable(bp,name,kind)
    g.compile_bp(bp)
    e=g.clear_graph(bp);ev=g.event(bp,'ReceiveBeginPlay')
    names=g.call(e,'/Script/Engine.DataTableFunctionLibrary.GetDataTableRowNames');g.value(names,'Table',ROOT+'/DT_TrafficSettings.DT_TrafficSettings');g.wire(g.then(ev),names.find_execute_pin())
    loop=e.add_macro_node('/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForEachLoop');g.wire(g.then(names),g.pin(loop,'Exec'));g.wire(g.pin(names,'OutRowNames',True),g.pin(loop,'Array'))
    row=g.call(e,'/Script/Engine.DataTableFunctionLibrary.GetDataTableRowFromName');g.value(row,'Table',ROOT+'/DT_TrafficSettings.DT_TrafficSettings');g.wire(g.pin(loop,'LoopBody',True),row.find_execute_pin());g.wire(g.pin(loop,'Array Element',True),g.pin(row,'RowName'))
    valid=e.add_branch_node();g.wire(g.then(row),valid.find_execute_pin());g.wire(g.result(row),g.pin(valid,'Condition'))
    entry=store(e,g.pin(valid,'then',True),'LastSettings',g.pin(row,'OutRow',True));increment(e,entry,'FoundCount')
    length=g.call(e,'/Script/Engine.KismetArrayLibrary.Array_Length');g.wire(g.pin(names,'OutRowNames',True),g.pin(length,'TargetArray'))
    entry=store(e,g.pin(loop,'Completed',True),'RowCount',g.result(length));store(e,entry,'Completed',literal='true')
    finalize(bp);e.add_comment_to_nodes('1.7: Get every row name, read the typed row and count successful results.',e.list_all_nodes());g.save(bp)
    levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem);levels.load_level('/Game/StealthShooter/Maps/L_BlueprintLab')
    sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    if not any(a.get_actor_label()=='DataTableExamples' for a in sub.get_all_level_actors()):
        a=sub.spawn_actor_from_class(bp.generated_class(),unreal.Vector(200,0,-100));a.set_actor_label('DataTableExamples')
    levels.save_current_level()
    return True

def timing_examples():
    g.BP_ROOT='/Game/StealthShooter/Blueprints'
    bp=g.blueprint('BP_TimingExamples',unreal.Actor)
    for name,kind,default in [('Immediate',B.get_basic_type_by_name('bool'),'false'),('Delayed',B.get_basic_type_by_name('bool'),'false'),('TimerCount',B.get_basic_type_by_name('int'),'0')]:variable(bp,name,kind,default)
    for prefix in ['Normal','Retrigger']:
        variable(bp,prefix+'Count',B.get_basic_type_by_name('int'),'0')
        variable(bp,prefix+'Time',B.get_basic_type_by_name('real'),'0')
    g.compile_bp(bp)
    e=g.new_function(bp,'PrintHello');entry=increment(e,e.find_graph_entry_pin(),'TimerCount')
    out=g.call(e,'/Script/Engine.KismetSystemLibrary.PrintString');g.value(out,'InString','Hello from the 2-second timer');after(entry,out)
    g.compile_bp(bp)
    eg=g.clear_graph(bp);ev=g.event(bp,'ReceiveBeginPlay')
    seq=g.named_node(eg,lambda n:n.endswith('|sequence') or n.endswith('|последовательность'),'Sequence')
    g.wire(g.then(ev),seq.find_execute_pin())
    delay=g.call(eg,'/Script/Engine.KismetSystemLibrary.Delay');g.value(delay,'Duration',3)
    g.wire(g.pin(seq,'then_0',True),delay.find_execute_pin());store(eg,g.then(delay),'Delayed',literal='true')
    immediate=store(eg,g.pin(seq,'then_1',True),'Immediate',literal='true')
    timer(eg,immediate,'PrintHello',seconds=2,loop=True)
    for prefix,function in [('Normal','Delay'),('Retrigger','RetriggerableDelay')]:
        event=eg.add_custom_event_node('Start'+prefix+'Delay')
        wait=g.call(eg,'/Script/Engine.KismetSystemLibrary.'+function);g.value(wait,'Duration',1)
        g.wire(g.then(event),wait.find_execute_pin());entry=increment(eg,g.then(wait),prefix+'Count')
        now=g.call(eg,'/Script/Engine.GameplayStatics.GetTimeSeconds')
        store(eg,entry,prefix+'Time',g.result(now))
    finalize(bp)
    eg.add_comment_to_nodes('1.8: Sequence continues immediately; Delay completes after 3 seconds. The timer repeats every 2 seconds.',eg.list_all_nodes())
    g.save(bp)
    return True

def configure_level():
    levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    assert levels.load_level('/Game/ThirdPerson/Maps/ThirdPersonMap')
    sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    world.get_world_settings().set_editor_property('default_game_mode',unreal.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonGameMode').generated_class())
    manager=next(a for a in sub.get_all_level_actors() if a.get_class().get_name()=='BP_TrafficLightsManager_C')
    manager.set_editor_property('SettingsRow',unreal.DataTableRowHandle(data_table=unreal.load_asset(ROOT+'/DT_TrafficSettings'),row_name='Default'))
    manager.set_editor_property('Interval',2.0);manager.set_editor_property('VariableIntervals',False)
    light_class=unreal.load_asset(ROOT+'/BP_TraffictLight').generated_class()
    positions=[('North',1250,700),('South',1250,1000),('East',1550,700),('West',1550,1000)]
    for name,x,y in positions:
        label='TrafficLight_'+name
        a=next((a for a in sub.get_all_level_actors() if a.get_actor_label()==label),None)
        if a is None:a=sub.spawn_actor_from_class(light_class,unreal.Vector(x,y,150))
        a.set_actor_label(label);a.set_actor_location(unreal.Vector(x,y,150),False,False)
    text=next((a for a in sub.get_all_level_actors() if a.get_actor_label()=='Traffic_Lab_Title'),None)
    if text is None:text=sub.spawn_actor_from_class(unreal.TextRenderActor,unreal.Vector(1750,850,380),unreal.Rotator(yaw=180))
    text.set_actor_label('Traffic_Lab_Title');text.text_render.set_text('TRAFFIC LIGHTS  /  STRUCT + MAP + TIMER');text.text_render.set_world_size(25);text.text_render.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
    assert levels.save_current_level()
    # The timing example remains on the foundation lab, away from the practical map.
    assert levels.load_level('/Game/StealthShooter/Maps/L_BlueprintLab')
    if not any(a.get_actor_label()=='TimingExamples' for a in sub.get_all_level_actors()):
        a=sub.spawn_actor_from_class(unreal.load_asset('/Game/StealthShooter/Blueprints/BP_TimingExamples').generated_class(),unreal.Vector(0,0,-100));a.set_actor_label('TimingExamples')
    assert levels.save_current_level()
    return True
