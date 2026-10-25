"""Catapult presentation using original materials and an optional locally licensed Fab scene."""
import math,random
import unreal
import build_catapult as c
from build_switchable_room import component

FAB_MAP='/Game/StealthShooter/Maps/L_Catapult_Ruins'

def material(name,color,roughness=.7,metallic=0,grain=False):
    obj=c.asset(name)
    if obj:return obj
    obj=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,c.ROOT,unreal.Material,unreal.MaterialFactoryNew());lib=unreal.MaterialEditingLibrary
    if grain:
        uv=lib.create_material_expression(obj,unreal.MaterialExpressionTextureCoordinate,-600,0)
        node=lib.create_material_expression(obj,unreal.MaterialExpressionCustom,-350,0)
        entry=unreal.CustomInput();entry.set_editor_property('input_name','UV');node.set_editor_property('inputs',[entry]);node.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT3)
        node.set_editor_property('code','float k=sin(UV.x*6.283)*0.02+sin(UV.x*21)*0.008; float g=0.5+0.5*sin((UV.y+k)*180); float b=0.5+0.5*sin(UV.y*37+UV.x*3); return lerp(float3(0.055,0.021,0.008),float3(0.22,0.095,0.032),saturate(0.35+0.32*g+0.16*b));')
        lib.connect_material_expressions(uv,'',node,'UV')
    else:
        node=lib.create_material_expression(obj,unreal.MaterialExpressionConstant3Vector,-350,0);node.set_editor_property('constant',unreal.LinearColor(*color,1))
    lib.connect_material_property(node,'',unreal.MaterialProperty.MP_BASE_COLOR)
    for value,prop,y in [(roughness,unreal.MaterialProperty.MP_ROUGHNESS,160),(metallic,unreal.MaterialProperty.MP_METALLIC,280)]:
        node=lib.create_material_expression(obj,unreal.MaterialExpressionConstant,-200,y);node.set_editor_property('r',value);lib.connect_material_property(node,'',prop)
    lib.recompile_material(obj);c.g.save(obj);return obj

def original_style():
    assert not unreal.EditorLevelLibrary.get_pie_worlds(False)
    wood=material('M_Catapult_Wood',(.14,.055,.016),.74,grain=True)
    iron=material('M_Catapult_Iron',(.065,.077,.085),.36,.88)
    stone=material('M_Catapult_RangeStone',(.18,.17,.145),.92)
    gold=material('M_Catapult_Brass',(.48,.26,.055),.32,.75)
    red=material('M_Catapult_Target',(.42,.035,.018),.7)
    cat=c.asset('BP_Catapult')
    for name in ['Base','SupportLeft','SupportRight','ThrowingArm']:component(cat,name,unreal.StaticMeshComponent).set_material(0,wood)
    component(cat,'Axle',unreal.StaticMeshComponent).set_material(0,iron)
    for x in [-200,80]:
        for y in [-145,145]:
            name='Wheel'+str(x).replace('-','N')+str(y).replace('-','N')
            wheel=c.shape(cat,name,'Cylinder',(x,y,45),(.9,.9,.24),'Lighting/M_LightFixture','NoCollision');wheel.set_editor_property('relative_rotation',unreal.Rotator(roll=90));wheel.set_material(0,iron)
        strap=c.shape(cat,'BaseStrap'+str(x).replace('-','N'),'Cube',(x,0,42),(.13,2.75,.05),'Lighting/M_LightFixture','NoCollision');strap.set_material(0,iron)
    for side,y in [('Left',-106),('Right',106)]:
        brace=c.shape(cat,'Brace'+side,'Cube',(-75,y,105),(2.1,.16,.16),'Lighting/M_LightFixture','NoCollision');brace.set_editor_property('relative_rotation',unreal.Rotator(pitch=45));brace.set_material(0,wood)
    c.g.compile_bp(cat)
    levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem);levels.load_level(c.MAP);sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in sub.get_all_level_actors():
        if a.get_actor_label()=='CatapultRangeFloor':a.static_mesh_component.set_material(0,stone)
        elif a.get_actor_label().startswith('RangeMark'):a.static_mesh_component.set_material(0,gold)
        elif a.get_actor_label().startswith('Target'):a.static_mesh_component.set_material(0,wood)
    for i,y in enumerate([-150,0,150]):
        for suffix,x,size,mat in [('Outer',1979,.95,red),('Inner',1975,.35,gold)]:
            label='Bullseye'+str(i)+suffix;a=next((x for x in sub.get_all_level_actors() if x.get_actor_label()==label),None)
            if not a:a=sub.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(x,y,90),unreal.Rotator(pitch=90));a.set_actor_label(label)
            a.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cylinder'));a.set_actor_scale3d(unreal.Vector(size,size,.03));a.static_mesh_component.set_material(0,mat);a.static_mesh_component.set_collision_profile_name('NoCollision')
    levels.save_current_level()
    return {'materials':5,'cosmetic_wheels':4,'unchanged_physics_bodies':True}

def fab_scene():
    assert not unreal.EditorLevelLibrary.get_pie_worlds(False)
    levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not unreal.EditorAssetLibrary.does_asset_exist(FAB_MAP):
        assert levels.new_level_from_template(FAB_MAP,c.MAP)
    else:assert levels.load_level(FAB_MAP)
    sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);rng=random.Random(310)
    def mesh(label,path,loc,scale=1,yaw=0):
        a=next((x for x in sub.get_all_level_actors() if x.get_actor_label()==label),None)
        if not a:a=sub.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(*loc),unreal.Rotator(yaw=yaw));a.set_actor_label(label)
        a.set_actor_location(unreal.Vector(*loc),False,False);a.set_actor_rotation(unreal.Rotator(yaw=yaw),False);a.set_actor_scale3d(unreal.Vector(scale,scale,scale));a.static_mesh_component.set_static_mesh(unreal.load_asset(path));a.static_mesh_component.set_collision_profile_name('NoCollision');a.set_folder_path('Catapult/FabDecoration');return a
    base='/Game/Abandoned_Cathedral/Assets/'
    for ix,x in enumerate(range(-800,3200,400)):
        for iy,y in enumerate(range(-800,1200,400)):
            variant=1;mesh('CourtyardTile_%02d_%02d'%(ix,iy),base+'floor_1/Static_Mesh/SM_floor_'+str(variant),(x,y,-14.5),1,90*((ix+iy)%4))
    for side,y in [('North',1180),('South',-1300)]:
        for i,x in enumerate([-500,700,1900]):mesh('Arcade'+side+str(i),base+'arch_1-2/Static_Mesh/SM_arch_1_',(x+500,y,0),1.25,90)
        for i,x in enumerate(range(-800,3200,400)):mesh('Wall'+side+str(i),base+'Wall_1/Static_Mesh/SM_wall_1',(x+400,y+(150 if y>0 else -150),0),1,90)
        for i in range(12):
            x=-900+i*350+rng.uniform(-80,80);y2=y+rng.uniform(-70,100);variant=1+i%4
            mesh('Rock'+side+str(i),'/Game/Rock_Collection_04/Meshes/Rock_%02d/StaticMeshes/SM_Rock_%02d'%(variant,variant),(x,y2,-25),rng.uniform(.65,1.6),rng.uniform(0,360))
    for i in range(14):mesh('MasonryDebris'+str(i),base+'debris/Static_Mesh/SM_brick_1',(rng.uniform(-700,2700),rng.choice([-1,1])*rng.uniform(850,1050),0),rng.uniform(.8,1.6),rng.uniform(0,360))
    mesh('BackdropGround','/Engine/BasicShapes/Cube',(1100,0,-80),1)
    backdrop=next(a for a in sub.get_all_level_actors() if a.get_actor_label()=='BackdropGround');backdrop.set_actor_scale3d(unreal.Vector(500,500,1));backdrop.static_mesh_component.set_material(0,c.asset('M_Catapult_RangeStone'))
    fog=next((a for a in sub.get_all_level_actors() if a.get_actor_label()=='CatapultDistanceFog'),None)
    if not fog:fog=sub.spawn_actor_from_class(unreal.ExponentialHeightFog,unreal.Vector(0,0,0));fog.set_actor_label('CatapultDistanceFog')
    fog_component=fog.get_component_by_class(unreal.ExponentialHeightFogComponent);fog_component.set_editor_property('fog_density',.015);fog_component.set_editor_property('fog_height_falloff',.18)
    for a in sub.get_all_level_actors():
        if a.get_actor_label()=='CatapultRangeFloor':a.static_mesh_component.set_visibility(False)
        if a.get_actor_label()=='CatapultSky':a.light_component.set_intensity(1.5)
        if a.get_actor_label()=='CatapultSun':
            a.set_actor_rotation(unreal.Rotator(pitch=-34,yaw=-55),False);a.light_component.set_intensity(5);a.light_component.set_editor_property('use_temperature',True);a.light_component.set_editor_property('temperature',4900)
    pp=next((x for x in sub.get_all_level_actors() if x.get_actor_label()=='CatapultExposure'),None)
    if not pp:pp=sub.spawn_actor_from_class(unreal.PostProcessVolume,unreal.Vector());pp.set_actor_label('CatapultExposure')
    pp.set_editor_property('unbound',True);settings=pp.get_editor_property('settings')
    for name,value in [('override_auto_exposure_min_brightness',True),('override_auto_exposure_max_brightness',True),('auto_exposure_min_brightness',.8),('auto_exposure_max_brightness',.8)]:settings.set_editor_property(name,value)
    pp.set_editor_property('settings',settings)
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(unreal.Vector(-900,-900,500),unreal.Rotator(pitch=-15,yaw=28));levels.save_current_level()
    return {'map':FAB_MAP,'floor_tiles':50,'arches':6,'rocks':24,'decor_collision':'NoCollision','mechanics':'same BP_Catapult'}
