"""Build the standalone examples for structures, containers and ForEach."""
import json,re
from pathlib import Path
import unreal
from project_paths import load_asset,resolve_reference
import lab_graph as g

ROOT='/Game/StealthShooter'
BP=ROOT+'/Blueprints'
B=unreal.BlueprintEditorLibrary
INT=B.get_basic_type_by_name('int')
BOOL=B.get_basic_type_by_name('bool')
TEXT=B.get_basic_type_by_name('text')
STRING=B.get_basic_type_by_name('string')

def setup():
    g.ROOT=ROOT;g.BP_ROOT=BP;g.MAP_ROOT=ROOT+'/Maps'

def variable(bp,name,kind,default='',editable=False):
    if bp.get_name() in ['BP_LightSwitch','BP_SwitchableLamp','BP_GroupSwitch']:name={'IsOn':'bOn','Bound':'bBound','IsNearby':'bNearby'}.get(name,name)
    if name not in [str(n) for n in B.list_member_variable_names(bp,False)]:
        assert g.graph(bp).add_member_variable(name,kind,default),name
    B.set_blueprint_variable_instance_editable(bp,name,editable)
    B.set_blueprint_variable_category(bp,name,'Lesson Examples')

def prepare():
    setup()
    for name in ['S_Example','S_StaticObjInfo']:
        s=load_asset(ROOT+'/Data/'+name)
        assert s
        g.save(s)
        unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(s)
    cube=g.blueprint('BP_Cube',unreal.StaticMeshActor)
    g.compile_bp(cube)
    cdo=unreal.get_default_object(cube.generated_class())
    cdo.static_mesh_component.set_static_mesh(load_asset('/Engine/BasicShapes/Cube'))
    cdo.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    g.save(cube)
    obj=g.blueprint('BP_StaticObject',unreal.StaticMeshActor)
    variable(obj,'Info',B.get_struct_type(load_asset(ROOT+'/Data/S_StaticObjInfo')),editable=True)
    g.compile_bp(obj)
    controller=g.blueprint('BP_ColorControl',unreal.Actor)
    cube_type=B.get_object_reference_type(cube.generated_class())
    variable(controller,'TargetCubes',B.get_array_type(cube_type),editable=True)
    variable(controller,'TargetCubeSet',B.get_set_type(cube_type),editable=True)
    variable(controller,'UseSet',BOOL,'false',True)
    variable(controller,'AppliedCount',INT,'0')
    variable(controller,'Completed',BOOL,'false')
    variable(controller,'AppliedMaterial',B.get_object_reference_type(unreal.MaterialInterface.static_class()),editable=True)
    g.compile_bp(controller)
    examples=g.blueprint('BP_ContainerExamples',unreal.Actor)
    for n,t,default in [('IntArray',B.get_array_type(INT),'(1,1,2,3)'),('IntSet',B.get_set_type(INT),'(1,2,3)'),('OtherSet',B.get_set_type(INT),'(1,2,4)'),('Numbers',B.get_map_type(INT,STRING),'((1,"one"),(2,"two"),(3,"three"))'),('MapCount',INT,'0'),('BreakCount',INT,'0'),('BreakFound',BOOL,'false'),('Completed',BOOL,'false')]:variable(examples,n,t,default)
    for name in ['IntArray', 'Numbers']:
        B.set_blueprint_variable_instance_editable(examples,name,True)
    g.compile_bp(examples)
    structs=g.blueprint('BP_StructureExamples',unreal.Actor)
    variable(structs,'Item',B.get_struct_type(load_asset(ROOT+'/Data/S_Example')))
    g.compile_bp(structs)
    result={'nodes':[str(n) for n in g.graph(obj).list_available_nodes([]) if any(x in str(n).lower() for x in ['s_staticobjinfo','s_example','foreach'])], 'info':str(unreal.get_default_object(obj.generated_class()).get_editor_property('Info'))}
    return result

def ref(e,name):return g.result(g.get_variable(e,name))

def after(entry,node):
    p=node.find_execute_pin()
    if p.is_valid():g.wire(entry,p);return g.then(node)
    return entry

def store(e,entry,name,value=None,literal=None):
    n=g.set_variable(e,name)
    if value is not None:g.wire(value,g.pin(n,name))
    else:g.value(n,name,literal)
    g.wire(entry,n.find_execute_pin())
    return g.then(n)

def field(node,name,output=False):
    pins=node.list_output_pins() if output else node.list_input_pins()
    return next(p for p in pins if str(p.get_pin_name()).split('_')[0].lower()==name.lower())

def struct_node(e,operation,name):
    target=(operation+name).replace('_','').replace(' ','').lower()
    return g.named_node(e,lambda n:n.replace('_','').endswith('|'+target),operation+' '+name)

def finalize(bp):
    g.compile_bp(bp);g.layout(bp);g.save(bp)

def objects():
    setup();bp=load_asset(BP+'/BP_StaticObject');e=g.clear_graph(bp)
    ev=g.event(bp,'ReceiveBeginPlay')
    info=g.get_variable(e,'Info');br=struct_node(e,'Break','S_StaticObjInfo')
    g.wire(g.result(info),next(p for p in br.list_input_pins() if p.get_pin_type_as_json_schema()))
    mesh=g.get_variable(e,'StaticMeshComponent')
    set_mesh=g.call(e,'/Script/Engine.StaticMeshComponent.SetStaticMesh')
    g.wire(g.result(mesh),g.pin(set_mesh,'self'));g.wire(field(br,'Mesh',True),g.pin(set_mesh,'NewMesh'))
    g.wire(g.then(ev),set_mesh.find_execute_pin())
    finalize(bp)
    return {'break_pins':[str(p.get_pin_name()) for p in br.list_all_pins()]}

def color_loop(e,entry,array):
    loop=e.add_macro_node('/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForEachLoop')
    assert loop
    g.wire(array,g.pin(loop,'Array'));g.wire(entry,g.pin(loop,'Exec'))
    valid=g.call(e,'/Script/Engine.KismetSystemLibrary.IsValid')
    g.wire(g.pin(loop,'Array Element',True),g.pin(valid,'Object'))
    branch=e.add_branch_node();g.wire(g.result(valid),g.pin(branch,'Condition'));g.wire(g.pin(loop,'LoopBody',True),branch.find_execute_pin())
    component=g.get_variable(e,'StaticMeshComponent','/Script/Engine.StaticMeshActor')
    g.wire(g.pin(loop,'Array Element',True),g.pin(component,'self'))
    material=g.call(e,'/Script/Engine.PrimitiveComponent.SetMaterial')
    g.wire(g.result(component),g.pin(material,'self'));g.wire(ref(e,'AppliedMaterial'),g.pin(material,'Material'));g.value(material,'ElementIndex','0')
    g.wire(g.pin(branch,'then',True),material.find_execute_pin())
    add=g.call(e,'/Script/Engine.KismetMathLibrary.Add_IntInt');g.wire(ref(e,'AppliedCount'),g.pin(add,'A'));g.value(add,'B','1')
    store(e,g.then(material),'AppliedCount',g.result(add))
    store(e,g.pin(loop,'Completed',True),'Completed',literal='true')
    return loop

def colors():
    setup();bp=load_asset(BP+'/BP_ColorControl');e=g.new_function(bp,'ApplyColors')
    entry=store(e,e.find_graph_entry_pin(),'AppliedCount',literal='0')
    entry=store(e,entry,'Completed',literal='false')
    branch=e.add_branch_node();g.wire(entry,branch.find_execute_pin());g.wire(ref(e,'UseSet'),g.pin(branch,'Condition'))
    convert=g.call(e,'/Script/Engine.BlueprintSetLibrary.Set_ToArray');g.wire(ref(e,'TargetCubeSet'),g.pin(convert,'A'))
    set_entry=after(g.pin(branch,'then',True),convert)
    color_loop(e,set_entry,g.pin(convert,'Result',True))
    color_loop(e,g.pin(branch,'else',True),ref(e,'TargetCubes'))
    g.compile_bp(bp)
    eg=g.clear_graph(bp);ev=g.event(bp,'ReceiveBeginPlay');call=g.call(eg,bp.generated_class().get_path_name()+':ApplyColors');g.wire(g.then(ev),call.find_execute_pin())
    finalize(bp)
    return True

def containers():
    setup();bp=load_asset(BP+'/BP_ContainerExamples')
    for name,kind,default in [('MapLines',B.get_array_type(STRING),''),('Difference',B.get_set_type(INT),''),('Intersection',B.get_set_type(INT),''),('Union',B.get_set_type(INT),''),('UniqueIndex',INT,'0'),('MapCompleted',BOOL,'false'),('BreakCompleted',BOOL,'false')]:variable(bp,name,kind,default)
    g.compile_bp(bp)
    e=g.new_function(bp,'RunExamples');entry=e.find_graph_entry_pin()
    for name,val in [('MapCount','0'),('BreakCount','0'),('BreakFound','false'),('Completed','false'),('MapCompleted','false'),('BreakCompleted','false')]:entry=store(e,entry,name,literal=val)
    clear=g.call(e,'/Script/Engine.KismetArrayLibrary.Array_Clear');g.wire(ref(e,'MapLines'),g.pin(clear,'TargetArray'));entry=after(entry,clear)
    for function,variable_name in [('Set_Difference','Difference'),('Set_Intersection','Intersection'),('Set_Union','Union')]:
        n=g.call(e,'/Script/Engine.BlueprintSetLibrary.'+function);g.wire(ref(e,'IntSet'),g.pin(n,'A'));g.wire(ref(e,'OtherSet'),g.pin(n,'B'))
        entry=after(entry,n);entry=store(e,entry,variable_name,g.pin(n,'Result',True))
    unique=g.call(e,'/Script/Engine.KismetArrayLibrary.Array_AddUnique');g.wire(ref(e,'IntArray'),g.pin(unique,'TargetArray'));g.value(unique,'NewItem','1')
    entry=after(entry,unique);entry=store(e,entry,'UniqueIndex',g.result(unique))
    keys=g.call(e,'/Script/Engine.BlueprintMapLibrary.Map_Keys');g.wire(ref(e,'Numbers'),g.pin(keys,'TargetMap'));entry=after(entry,keys)
    loop=e.add_macro_node('/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForEachLoop')
    g.wire(g.pin(keys,'Keys',True),g.pin(loop,'Array'));g.wire(entry,g.pin(loop,'Exec'))
    find=g.call(e,'/Script/Engine.BlueprintMapLibrary.Map_Find');g.wire(ref(e,'Numbers'),g.pin(find,'TargetMap'));g.wire(g.pin(loop,'Array Element',True),g.pin(find,'Key'))
    body=after(g.pin(loop,'LoopBody',True),find)
    text=g.call(e,'/Script/Engine.KismetStringLibrary.Conv_IntToString');g.wire(g.pin(loop,'Array Element',True),g.pin(text,'InInt'))
    append1=g.call(e,'/Script/Engine.KismetStringLibrary.Concat_StrStr');g.value(append1,'A','Number: ');g.wire(g.result(text),g.pin(append1,'B'))
    append2=g.call(e,'/Script/Engine.KismetStringLibrary.Concat_StrStr');g.wire(g.result(append1),g.pin(append2,'A'));g.value(append2,'B',' is ')
    append3=g.call(e,'/Script/Engine.KismetStringLibrary.Concat_StrStr');g.wire(g.result(append2),g.pin(append3,'A'));g.wire(g.pin(find,'Value',True),g.pin(append3,'B'))
    add_line=g.call(e,'/Script/Engine.KismetArrayLibrary.Array_Add');g.wire(ref(e,'MapLines'),g.pin(add_line,'TargetArray'));g.wire(g.result(append3),g.pin(add_line,'NewItem'));body=after(body,add_line)
    print_line=g.call(e,'/Script/Engine.KismetSystemLibrary.PrintString');g.wire(g.result(append3),g.pin(print_line,'InString'));g.value(print_line,'Duration','30');body=after(body,print_line)
    inc=g.call(e,'/Script/Engine.KismetMathLibrary.Add_IntInt');g.wire(ref(e,'MapCount'),g.pin(inc,'A'));g.value(inc,'B','1');store(e,body,'MapCount',g.result(inc))
    entry=store(e,g.pin(loop,'Completed',True),'MapCompleted',literal='true')
    br=e.add_macro_node('/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForEachLoopWithBreak')
    g.wire(ref(e,'IntArray'),g.pin(br,'Array'));g.wire(entry,g.pin(br,'Exec'))
    inc2=g.call(e,'/Script/Engine.KismetMathLibrary.Add_IntInt');g.wire(ref(e,'BreakCount'),g.pin(inc2,'A'));g.value(inc2,'B','1')
    body=store(e,g.pin(br,'LoopBody',True),'BreakCount',g.result(inc2))
    eq=g.call(e,'/Script/Engine.KismetMathLibrary.EqualEqual_IntInt');g.wire(g.pin(br,'Array Element',True),g.pin(eq,'A'));g.value(eq,'B','2')
    condition=e.add_branch_node();g.wire(g.result(eq),g.pin(condition,'Condition'));g.wire(body,condition.find_execute_pin())
    found=store(e,g.pin(condition,'then',True),'BreakFound',literal='true');g.wire(found,g.pin(br,'Break'))
    entry=store(e,g.pin(br,'Completed',True),'BreakCompleted',literal='true');store(e,entry,'Completed',literal='true')
    g.compile_bp(bp)
    eg=g.clear_graph(bp);ev=g.event(bp,'ReceiveBeginPlay');call=g.call(eg,bp.generated_class().get_path_name()+':RunExamples');g.wire(g.then(ev),call.find_execute_pin())
    finalize(bp)
    return True

def structures():
    setup();bp=load_asset(BP+'/BP_StructureExamples')
    for n,t,d in [('FinalCost',INT,'0'),('FinalName',TEXT,''),('Completed',BOOL,'false')]:variable(bp,n,t,d)
    g.compile_bp(bp)
    e=g.new_function(bp,'InitializeItem')
    make=struct_node(e,'Make','S_Example')
    assert field(make,'Name').set_pin_value('Keycard')
    assert field(make,'Description').set_pin_value('Opens a secure door')
    assert field(make,'Cost').set_pin_value('100')
    entry=store(e,e.find_graph_entry_pin(),'Item',g.result(make))
    members=struct_node(e,'Setmembersin','S_Example')
    options=[]
    for option in members.get_editor_property('show_pin_for_properties'):
        option.set_editor_property('show_pin',str(option.get_editor_property('property_name')).startswith('Cost_'))
        options.append(option)
    members.set_editor_property('show_pin_for_properties',options)
    g.wire(ref(e,'Item'),g.pin(members,'StructRef'))
    if not any(str(p.get_pin_name()).startswith('Cost_') for p in members.list_input_pins()):
        unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).open_editor_for_assets([bp])
        return {'refresh_required':True,'action':'File > Refresh All Nodes, then structures_finish()'}
    return structures_finish()

def structures_finish():
    setup();bp=load_asset(BP+'/BP_StructureExamples');e=g.new_function(bp,'InitializeItem') if not B.find_graph(bp,'InitializeItem') else unreal.BlueprintGraphEditor.get_graph_editor(B.find_graph(bp,'InitializeItem'))
    members=next(n for n in e.list_all_nodes() if n.get_class().get_name()=='K2Node_SetFieldsInStruct')
    item_set=next(n for n in e.list_all_nodes() if n.get_class().get_name()=='K2Node_VariableSet')
    entry=g.then(item_set)
    assert field(members,'Cost').set_pin_value('75')
    entry=after(entry,members)
    br=struct_node(e,'Break','S_Example');g.wire(ref(e,'Item'),g.pin(br,'S_Example'))
    entry=store(e,entry,'FinalCost',field(br,'Cost',True));entry=store(e,entry,'FinalName',field(br,'Name',True));store(e,entry,'Completed',literal='true')
    g.compile_bp(bp)
    eg=g.clear_graph(bp);ev=g.event(bp,'ReceiveBeginPlay');n=g.call(eg,bp.generated_class().get_path_name()+':InitializeItem');g.wire(g.then(ev),n.find_execute_pin())
    finalize(bp)
    return True

def material(name,color):
    path=ROOT+'/Materials/'+name
    m=load_asset(path) or unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,ROOT+'/Materials',unreal.Material,unreal.MaterialFactoryNew())
    lib=unreal.MaterialEditingLibrary;lib.delete_all_material_expressions(m)
    n=lib.create_material_expression(m,unreal.MaterialExpressionConstant3Vector,0,0);n.set_editor_property('constant',unreal.LinearColor(*color,1))
    lib.connect_material_property(n,'',unreal.MaterialProperty.MP_BASE_COLOR)
    rough=lib.create_material_expression(m,unreal.MaterialExpressionConstant,0,150);rough.set_editor_property('r',.75)
    lib.connect_material_property(rough,'',unreal.MaterialProperty.MP_ROUGHNESS)
    lib.recompile_material(m);g.save(m)
    return m

def level():
    setup();sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    path=ROOT+'/Maps/L_BlueprintLab'
    if not unreal.EditorAssetLibrary.does_asset_exist(path):assert levels.new_level(path)
    else:
        current=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        assert current.get_path_name().split('.')[0]==path,'Open the existing lab map before updating its examples.'
    control_bp=load_asset(BP+'/BP_ColorControl');B.set_blueprint_variable_instance_editable(control_bp,'AppliedMaterial',True);g.compile_bp(control_bp)
    cyan=material('M_Cyan',(0.015,.65,.72));white=material('M_White',(.65,.7,.75));floor_mat=material('M_LabFloor',(.035,.055,.075))
    def actor(cls,label,loc,rotation=None):
        a=next((a for a in sub.get_all_level_actors() if a.get_actor_label()==label),None)
        if not a:a=sub.spawn_actor_from_class(cls,unreal.Vector(*loc),rotation or unreal.Rotator())
        a.set_actor_label(label);return a
    def static(mesh,label,loc,scale=(1,1,1),mat=white):
        a=actor(unreal.StaticMeshActor,label,loc);a.static_mesh_component.set_static_mesh(load_asset(mesh));a.set_actor_scale3d(unreal.Vector(*scale));a.static_mesh_component.set_material(0,mat);return a
    def text(label,content,loc,size=38):
        a=actor(unreal.TextRenderActor,label,loc,unreal.Rotator(pitch=0,yaw=180,roll=0));a.text_render.set_text(content);a.text_render.set_world_size(size);a.text_render.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER);return a
    static('/Engine/BasicShapes/Cube','LabFloor',(200,0,-30),(20,20,.5),floor_mat)
    cube_class=load_asset(BP+'/BP_Cube').generated_class()
    controls=[]
    for name,y,use_set in [('Array',-550,False),('Set',0,True)]:
        cubes=[]
        for i,x in enumerate([0,250,500]):
            a=actor(cube_class,name+'_Cube_'+str(i+1),(x,y,75));a.static_mesh_component.set_material(0,white);cubes.append(a)
        c=actor(load_asset(BP+'/BP_ColorControl').generated_class(),name+'_ColorControl',(0,y,-100))
        c.set_editor_property('TargetCubes',cubes if not use_set else [])
        c.set_editor_property('TargetCubeSet',set(cubes) if use_set else set())
        c.set_editor_property('UseSet',use_set);c.set_editor_property('AppliedMaterial',cyan);controls.append(c)
        text(name+'_Label','ARRAY' if not use_set else 'SET -> ARRAY',(-160,y,210),48)
    info_class=load_asset(BP+'/BP_StaticObject').generated_class()
    for i,mesh in enumerate(['Sphere','Cone','Cylinder']):
        a=actor(info_class,'Structure_'+mesh,(i*250,550,75))
        a.static_mesh_component.set_static_mesh(load_asset('/Engine/BasicShapes/Cube'))
        a.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE);a.static_mesh_component.set_material(0,white)
        value=a.get_editor_property('Info')
        for key in re.findall(r'([A-Za-z][A-Za-z0-9_]+)=',value.export_text()):
            if key.startswith('Name_'):value.set_editor_property(key,unreal.Text(mesh))
            if key.startswith('Mesh_'):value.set_editor_property(key,load_asset('/Engine/BasicShapes/'+mesh))
        a.set_editor_property('Info',value)
    text('Struct_Label','STRUCTURE -> MESH',(-160,550,210),42)
    text('Lab_Title','BLUEPRINT LAB',(850,0,600),85)
    text('Lab_Subtitle','1.3 STRUCTURES  /  1.4 CONTAINERS  /  1.5 FOREACH',(850,0,495),30)
    text('Map_Notes','MAP: 1 = one  |  2 = two  |  3 = three',(850,0,365),35)
    text('Break_Notes','ForEach + Break: [1, 1, 2, 3] -> stop at 2',(850,0,280),32)
    actor(load_asset(BP+'/BP_ContainerExamples').generated_class(),'ContainerExamples',(0,0,-100))
    actor(load_asset(BP+'/BP_StructureExamples').generated_class(),'StructureExamples',(100,0,-100))
    light=actor(unreal.DirectionalLight,'Sun',(0,0,1000),unreal.Rotator(pitch=-50,yaw=-30,roll=0));light.light_component.set_intensity(4)
    actor(unreal.SkyLight,'SkyLight',(0,0,500))
    actor(unreal.SkyAtmosphere,'SkyAtmosphere',(0,0,0))
    actor(unreal.PlayerStart,'PlayerStart',(-1400,0,850),unreal.Rotator(pitch=-20,yaw=0,roll=0))
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(unreal.Vector(-1400,0,850),unreal.Rotator(pitch=-20,yaw=0,roll=0))
    assert levels.save_current_level()
    return {'map':path,'actors':len(sub.get_all_level_actors())}
