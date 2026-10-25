"""Shared native Blueprint editing helpers for the Maze lessons."""
import unreal
import lab_graph as g
from build_blueprint_lab import variable,ref,store,after
from build_switchable_room import component,self_ref

ROOT='/Game/StealthShooter/Maze'
B=unreal.BlueprintEditorLibrary
REAL=B.get_basic_type_by_name('real')
BOOL=B.get_basic_type_by_name('bool')
INT=B.get_basic_type_by_name('int')
TEXT=B.get_basic_type_by_name('text')
STRING=B.get_basic_type_by_name('string')
ACTOR=B.get_object_reference_type(unreal.Actor)
VECTOR=B.get_struct_type(unreal.Vector.static_struct())
PATHS={
 'BPC_Health':'Core','BPI_Interactable':'Core','BP_ControlActor':'Core','BP_MazeGameMode':'Core',
 'BP_MazeCharacter':'Character','IA_Interact':'Character/Input','IMC_Maze':'Character/Input',
 'BP_Door':'Puzzles','BP_Lever':'Puzzles','BP_PressurePlate':'Puzzles','BP_LiftingGate':'Puzzles',
 'BP_HealPickup':'Items','BP_Trophy':'Items','BP_WinZone':'World','BP_MazeTurret':'Enemies',
 'WBP_MazeHUD':'Interface','WBP_MazeWin':'Interface','WBP_MazeLose':'Interface'}
def path(name):return ROOT+'/'+PATHS[name]+'/'+name
def asset(name):return unreal.load_asset(path(name))
def bp(name,parent=unreal.Actor,source=None):
    obj=asset(name)
    if not obj:
        unreal.EditorAssetLibrary.make_directory(ROOT+'/'+PATHS[name])
        if source:obj=unreal.EditorAssetLibrary.duplicate_asset(source,path(name))
        else:
            factory=unreal.BlueprintFactory();factory.set_editor_property('parent_class',parent)
            obj=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,ROOT+'/'+PATHS[name],unreal.Blueprint,factory)
    assert obj,name
    return obj
def var(bp,name,kind,default='',editable=False,category='State'):
    variable(bp,name,kind,default,editable);B.set_blueprint_variable_category(bp,name,'Maze|'+category)
def own(e,bp,name):return g.call(e,bp.generated_class().get_path_name()+':'+name)
def method(e,name,function,target):
    n=own(e,asset(name),function);g.wire(target,g.pin(n,'self'));return n
def member(e,name,prop,target):
    n=g.get_variable(e,prop,asset(name).generated_class().get_path_name());g.wire(target,g.pin(n,'self'));return g.result(n)
def set_member(e,name,prop,target,value):
    n=g.set_variable(e,prop,asset(name).generated_class().get_path_name());g.wire(target,g.pin(n,'self'));g.wire(value,g.pin(n,prop));return n
def op(e,name,a,b=None):
    n=g.call(e,'/Script/Engine.KismetMathLibrary.'+name)
    for key,val in [('A',a),('B',b)]:
        if val is None:continue
        if hasattr(val,'is_valid'):g.wire(val,g.pin(n,key))
        else:g.value(n,key,val)
    return g.result(n)
def branch(e,entry,condition):
    n=e.add_branch_node();g.wire(entry,n.find_execute_pin());g.wire(condition,g.pin(n,'Condition'));return n
def valid(e,obj,entry):
    n=g.call(e,'/Script/Engine.KismetSystemLibrary.IsValid');g.wire(obj,g.pin(n,'Object'))
    return g.pin(branch(e,entry,g.result(n)),'then',True)
def cast(e,name,obj,entry):
    target=name.removesuffix('_C')
    n=g.named_node(e,lambda s:s.endswith('|castto'+target.lower()),'Cast '+name)
    g.wire(obj,g.pin(n,'Object'));entry=after(entry,n)
    output=next(p for p in n.list_output_pins() if str(p.get_pin_name()).startswith('As'))
    return output,entry
def player(e,entry):
    n=g.call(e,'/Script/Engine.GameplayStatics.GetPlayerCharacter');g.value(n,'PlayerIndex',0)
    return cast(e,'BP_MazeCharacter',g.result(n),entry)
def mode(e,entry):return cast(e,'BP_MazeGameMode',g.result(g.call(e,'/Script/Engine.GameplayStatics.GetGameMode')),entry)
def pc(e):
    n=g.call(e,'/Script/Engine.GameplayStatics.GetPlayerController');g.value(n,'PlayerIndex',0);return g.result(n)
def now(e):return g.result(g.call(e,'/Script/Engine.GameplayStatics.GetTimeSeconds'))
def timer(e,entry,function,seconds,loop=False):
    n=g.call(e,'/Script/Engine.KismetSystemLibrary.K2_SetTimer');g.wire(self_ref(e),g.pin(n,'Object'))
    g.value(n,'FunctionName',function);g.value(n,'Time',seconds);g.value(n,'bLooping',str(loop).lower());return after(entry,n)
def clear_timer(e,entry,function):
    n=g.call(e,'/Script/Engine.KismetSystemLibrary.K2_ClearTimer');g.wire(self_ref(e),g.pin(n,'Object'));g.value(n,'FunctionName',function);return after(entry,n)
def ret(e,entry):
    n=e.add_return_node();g.wire(entry,n.find_execute_pin());return n
def function(bp,name):return g.new_function(bp,name)
def finish(bp,notes):
    from standardize_project import add_returns
    for graph in B.list_graphs(bp):
        e=unreal.BlueprintGraphEditor.get_graph_editor(graph)
        e.remove_nodes([n for n in e.list_all_nodes() if isinstance(n,unreal.K2Node_FunctionResult) and not n.find_execute_pin().list_connected_pins()])
    g.compile_bp(bp);add_returns(bp)
    for gr in B.list_graphs(bp):
        e=unreal.BlueprintGraphEditor.get_graph_editor(gr)
        for c in e.list_comment_nodes():e.remove_comment_node(c)
        if e.list_all_nodes() and gr.get_name()!='UserConstructionScript':e.add_comment_to_nodes(notes.get(str(gr.get_name()),'One responsibility per function. Validate references before accessing gameplay objects.'),e.list_all_nodes())
    g.layout(bp);g.compile_bp(bp)
def mesh(bp,name,shape,loc,scale,mat,collision='NoCollision'):
    c=component(bp,name,unreal.StaticMeshComponent);c.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/'+shape))
    c.set_editor_property('relative_location',unreal.Vector(*loc));c.set_editor_property('relative_scale3d',unreal.Vector(*scale))
    c.set_material(0,unreal.load_asset('/Game/StealthShooter/MaterialLibrary/'+mat));c.set_mobility(unreal.ComponentMobility.MOVABLE);c.set_collision_profile_name(collision);return c
def trigger(bp,extent,loc=(0,0,100)):
    c=component(bp,'InteractionArea',unreal.BoxComponent);c.set_box_extent(unreal.Vector(*extent));c.set_editor_property('relative_location',unreal.Vector(*loc))
    c.set_collision_enabled(unreal.CollisionEnabled.QUERY_ONLY);c.set_collision_object_type(unreal.CollisionChannel.ECC_WORLD_DYNAMIC)
    c.set_collision_response_to_all_channels(unreal.CollisionResponseType.ECR_IGNORE);c.set_collision_response_to_channel(unreal.CollisionChannel.ECC_PAWN,unreal.CollisionResponseType.ECR_OVERLAP)
    c.set_editor_property('generate_overlap_events',True);return c
def iface(e,target):
    n=g.named_node(e,lambda s:s.endswith('|interact(сообщение)') or s.endswith('|interact(message)'),'Interact interface message');g.wire(target,g.pin(n,'self'));return n
