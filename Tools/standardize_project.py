"""Organize existing lesson assets and apply the module 5 Blueprint conventions."""
import json
from pathlib import Path
import unreal
import lab_graph as g
from build_blueprint_lab import variable,ref,store,after,finalize
B=unreal.BlueprintEditorLibrary
ROOT='/Game/StealthShooter'
MOVES={
ROOT+'/Interaction/BPI_Switchable':ROOT+'/Core/BPI_Switchable',
ROOT+'/Interaction/BP_LightSwitch':ROOT+'/Interaction/Lighting/BP_LightSwitch',
ROOT+'/Interaction/BP_SwitchableLamp':ROOT+'/Interaction/Lighting/BP_SwitchableLamp',
ROOT+'/GroupControl/BP_GroupSwitch':ROOT+'/Interaction/GroupControl/BP_GroupSwitch',
ROOT+'/UI/WBP_GroupSwitch':ROOT+'/Interaction/GroupControl/WBP_GroupSwitch',
}
for old,new,folder in [('M_BulbOn','M_LampBulb_On','Lighting'),('M_BulbOff','M_LampBulb_Off','Lighting'),('M_Body','M_LightFixture','Lighting'),('M_ButtonCap','M_SwitchCap','Lighting'),('M_Floor','M_LabRoom_Floor','Environment'),('M_Wall','M_LabRoom_Wall','Environment'),('M_Accent','M_LabRoom_Accent','Environment'),('M_LabText','M_LabRoom_Text','Environment')]:MOVES[ROOT+'/Interaction/'+old]=ROOT+'/MaterialLibrary/'+folder+'/'+new
for old,new in [('M_White','M_Example_White'),('M_Cyan','M_Example_Cyan'),('M_LabFloor','M_Example_Floor')]:MOVES[ROOT+'/Materials/'+old]=ROOT+'/MaterialLibrary/Examples/'+new
for name in ['BP_TimingExamples','BP_StructureExamples','BP_StaticObject','BP_DataTableExamples','BP_Cube','BP_ContainerExamples','BP_ColorControl']:MOVES[ROOT+'/Blueprints/'+name]=ROOT+'/Examples/Foundations/'+name
for name in ['S_StaticObjInfo','S_Example']:MOVES[ROOT+'/Data/'+name]=ROOT+'/Examples/Foundations/'+name
PATHS=[ROOT+'/Core/BPI_Switchable',ROOT+'/Interaction/Lighting/BP_LightSwitch',ROOT+'/Interaction/Lighting/BP_SwitchableLamp',ROOT+'/Interaction/GroupControl/BP_GroupSwitch',ROOT+'/Interaction/GroupControl/WBP_GroupSwitch']

def move_assets():
    assert not unreal.EditorLevelLibrary.get_pie_worlds(False)
    sub=unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
    for old in MOVES:
        asset=unreal.load_asset(old)
        if asset:sub.close_all_editors_for_asset(asset)
    renamed=[]
    data=[]
    for old,new in MOVES.items():
        if unreal.EditorAssetLibrary.does_asset_exist(new):continue
        asset=unreal.load_asset(old);assert asset,old
        folder,name=new.rsplit('/',1);data.append(unreal.AssetRenameData(asset,folder,name));renamed.append([old,new])
    if data:assert unreal.AssetToolsHelpers.get_asset_tools().rename_assets(data)
    for new in MOVES.values():g.save(unreal.load_asset(new))
    Path(unreal.Paths.project_dir()+'Docs/AssetPathChanges54.json').write_text(json.dumps(MOVES,indent=2),encoding='utf-8')
    return {'moved':len(renamed)}

def rename_bool(bp,old,new):
    names=list(map(str,B.list_member_variable_names(bp,False)))
    if old not in names:return
    default=bool(unreal.get_default_object(bp.generated_class()).get_editor_property(old))
    variable(bp,new,B.get_member_variable_type(bp,old),str(default).lower())
    B.replace_variable_references(bp,old,new)
    assert g.graph(bp).remove_member_variable(old)
    g.compile_bp(bp)

def rename_function(bp,old,new):
    graph=B.find_graph(bp,old)
    if graph:B.rename_graph(graph,new)
    g.compile_bp(bp)
    for graph in B.list_graphs(bp):
        for node in unreal.BlueprintGraphEditor.get_graph_editor(graph).list_all_nodes():
            if 'CreateDelegate' in node.get_class().get_name() and str(B.get_create_delegate_function(node))==old:B.set_create_delegate_function(node,new)
    g.compile_bp(bp)

def names_and_categories():
    for path in PATHS[1:]:
        bp=unreal.load_asset(path)
        unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
        for old,new in [('IsOn','bOn'),('Bound','bBound'),('IsNearby','bNearby')]:rename_bool(bp,old,new)
        for name in B.list_member_variable_names(bp,False):
            name=str(name)
            category='Interaction|Configuration' if name in ['InteractionRadius','ControlButton','SwitchTargets','GroupLabel'] else 'Interaction|State'
            if name.endswith('Count'):category='Diagnostics'
            if name=='OnSwitched':category='Interaction|Events'
            if name in ['OwnerSwitch','UseRadius','PanelLabel','ControlWidget']:category='UI|Context'
            B.set_blueprint_variable_category(bp,name,category)
        if bp.get_name()=='BP_SwitchableLamp':rename_function(bp,'HandleSwitchChanged','OnSwitchChanged')
        if bp.get_name()=='WBP_GroupSwitch':
            rename_function(bp,'HandleOn','OnEnableClicked');rename_function(bp,'HandleOff','OnDisableClicked')
        g.compile_bp(bp)
    return True

def simplify_group_events():
    import build_group_control as h
    bp=unreal.load_asset(ROOT+'/Interaction/GroupControl/BP_GroupSwitch');widget=unreal.load_asset(ROOT+'/Interaction/GroupControl/WBP_GroupSwitch')
    e=g.new_function(bp,'SetGroupState');enabled=g.input_parameter(e,'bEnabled',B.get_basic_type_by_name('bool'));entry=store(e,e.find_graph_entry_pin(),'bOn',enabled)
    branch=e.add_branch_node();g.wire(entry,branch.find_execute_pin());g.wire(enabled,g.pin(branch,'Condition'))
    setters=[]
    for output,path in [('then',ROOT+'/MaterialLibrary/Lighting/M_SwitchCap.M_SwitchCap'),('else',ROOT+'/MaterialLibrary/Lighting/M_LampBulb_Off.M_LampBulb_Off')]:
        n=g.call(e,'/Script/Engine.PrimitiveComponent.SetMaterial');g.wire(ref(e,'SwitchCap'),g.pin(n,'self'));g.value(n,'Material',path);after(g.pin(branch,output,True),n);setters.append(n)
    loop=e.add_macro_node('/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForEachLoop');g.wire(ref(e,'SwitchTargets'),g.pin(loop,'Array'))
    for n in setters:g.wire(g.then(n),g.pin(loop,'Exec'))
    obj=g.pin(loop,'Array Element',True);entry=h.valid(e,obj,g.pin(loop,'LoopBody',True));choose=e.add_branch_node();g.wire(entry,choose.find_execute_pin());g.wire(enabled,g.pin(choose,'Condition'))
    for output,name in [('then','SwitchOn'),('else','SwitchOff')]:after(g.pin(choose,output,True),h.message(e,name,obj))
    entry=h.valid(e,ref(e,'ControlWidget'),g.pin(loop,'Completed',True));refresh=g.call(e,widget.generated_class().get_path_name()+':RefreshDisplay');g.wire(ref(e,'ControlWidget'),g.pin(refresh,'self'));after(entry,refresh)
    g.compile_bp(bp)
    e=g.new_function(bp,'InitializeControls')
    create=g.named_node(e,lambda n:n.endswith('|создатьвиджет') or n.endswith('|createwidget'),'Create Widget');g.value(create,'Class',widget.generated_class().get_path_name());g.wire(h.controller(e),g.pin(create,'OwningPlayer'));entry=after(e.find_graph_entry_pin(),create);entry=store(e,entry,'ControlWidget',g.result(create))
    for name,value in [('OwnerSwitch',h.self_ref(e)),('UseRadius',ref(e,'InteractionRadius')),('PanelLabel',ref(e,'GroupLabel'))]:
        n=g.set_variable(e,name,widget.generated_class().get_path_name());g.wire(ref(e,'ControlWidget'),g.pin(n,'self'));g.wire(value,g.pin(n,name));entry=after(entry,n)
    entry=after(entry,h.message(e,'SwitchOn',h.self_ref(e)))
    timer=g.call(e,'/Script/Engine.KismetSystemLibrary.K2_SetTimer');g.wire(h.self_ref(e),g.pin(timer,'Object'));g.value(timer,'FunctionName','UpdateProximity');g.value(timer,'Time',.1);g.value(timer,'bLooping','true');after(entry,timer)
    g.compile_bp(bp)
    e=g.clear_graph(bp)
    for name,value in [('SwitchOn','true'),('SwitchOff','false')]:
        ev=g.event(bp,name);n=h.call_self(e,bp,'SetGroupState');g.value(n,'bEnabled',value);after(g.then(ev),n)
    ev=g.event(bp,'ReceiveBeginPlay');after(g.then(ev),h.call_self(e,bp,'InitializeControls'))
    ev=g.event(bp,'ReceiveEndPlay');entry=h.valid(e,ref(e,'ControlWidget'),g.then(ev));n=g.call(e,'/Script/UMG.Widget.RemoveFromParent');g.wire(ref(e,'ControlWidget'),g.pin(n,'self'));after(entry,n)
    g.compile_bp(bp)
    return True

def add_returns(bp):
    count=0
    for graph in B.list_graphs(bp):
        name=str(graph.get_name())
        if name in ['EventGraph','UserConstructionScript'] or name in list(map(str,B.list_event_dispatchers(bp))):continue
        e=unreal.BlueprintGraphEditor.get_graph_editor(graph);nodes=e.list_all_nodes()
        if not any(isinstance(n,unreal.K2Node_FunctionEntry) for n in nodes):continue
        # Loop bodies return to the macro implicitly; only Completed may finish the function.
        loop_body=set()
        def visit(node):
            if node in loop_body:return
            loop_body.add(node)
            for p in node.list_output_pins():
                if 'exec' in str(p.get_pin_type_as_json_schema()).lower():
                    for target in p.list_connected_pins():visit(target.get_owning_node())
        for node in nodes:
            p=node.find_output_pin('LoopBody')
            if p.is_valid():
                for target in p.list_connected_pins():visit(target.get_owning_node())
        leaves=[]
        for node in nodes:
            if node in loop_body or isinstance(node,(unreal.K2Node_FunctionResult,unreal.EdGraphNode_Comment)):continue
            for p in node.list_output_pins():
                if 'exec' in str(p.get_pin_type_as_json_schema()).lower() and not p.list_connected_pins():leaves.append(p)
        for p in leaves:
            ret=e.add_return_node();g.wire(p,ret.find_execute_pin());count+=1
    return count

def finish_graphs():
    report=[]
    for path in PATHS:
        bp=unreal.load_asset(path)
        returns=0 if bp.get_name().startswith('BPI_') else add_returns(bp)
        for graph in B.list_graphs(bp):
            name=str(graph.get_name());e=unreal.BlueprintGraphEditor.get_graph_editor(graph)
            for comment in e.list_comment_nodes():e.remove_comment_node(comment)
            nodes=e.list_all_nodes()
            if name=='UserConstructionScript':continue
            if name in list(map(str,B.list_event_dispatchers(bp))):continue
            if name=='EventGraph':
                # One comment per event flow; short helpers keep the event graph readable.
                for node in nodes:
                    if isinstance(node,unreal.K2Node_Event):
                        block=set()
                        def upstream(current):
                            if current in block:return
                            block.add(current)
                            for pin in current.list_input_pins():
                                if 'exec' not in str(pin.get_pin_type_as_json_schema()).lower():
                                    for source in pin.list_connected_pins():upstream(source.get_owning_node())
                        def flow(current):
                            if current in block:return
                            upstream(current)
                            for pin in current.list_output_pins():
                                if 'exec' in str(pin.get_pin_type_as_json_schema()).lower():
                                    for target in pin.list_connected_pins():flow(target.get_owning_node())
                        flow(node)
                        e.add_comment_to_nodes('Event flow: '+str(node.get_node_title()),list(block))
                continue
            descriptions={'TryInteract':'Reject invalid players and out-of-range input; toggle through BPI_Switchable.', 'BindToButton':'Subscribe this lamp once and synchronize its initial state.', 'UnbindFromButton':'Remove only this lamp subscription when it ends play.', 'OnSwitchChanged':'React to OnSwitched by forwarding the requested state through the interface.', 'IsSwitchOn':'Read the current on/off state without changing it.', 'SetGroupState':'Apply one requested state to the editable target collection, then refresh the panel.', 'InitializeControls':'Create and initialize one reusable UMG panel and start the proximity timer.', 'UpdateProximity':'Show or hide controls only when the player crosses the configured radius.', 'ShowControls':'Show the panel and allow UI clicks alongside character movement.', 'HideControls':'Remove the panel and restore game-only input.', 'RefreshDisplay':'Reflect the owner state in the label and enable only the available action.', 'OnEnableClicked':'Validate owner and range, then request SwitchOn through the interface.', 'OnDisableClicked':'Validate owner and range, then request SwitchOff through the interface.', 'SwitchOn':'Interface contract: enable the target.', 'SwitchOff':'Interface contract: disable the target.'}
            if nodes:e.add_comment_to_nodes(descriptions.get(name,'Process '+name+' and return explicitly.'),nodes)
        g.layout(bp);g.compile_bp(bp)
        report.append({'asset':path,'returns_added':returns})
    return report
