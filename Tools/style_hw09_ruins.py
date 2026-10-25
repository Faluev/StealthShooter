"""Create a local Fab courtyard from the owner's installed licensed packages."""
import random
import shutil
from pathlib import Path
import unreal

MAP='/Game/HW09Local/Maps/L_DashRuins'
SOURCE='/Game/ThirdPerson/Maps/ThirdPersonMap'
ROCK='/Game/Rock_Collection_04/Meshes/Rock_{0:02d}/StaticMeshes/SM_Rock_{0:02d}'
CAT='/Game/Abandoned_Cathedral/Assets/'


def restore(source_content='C:/Users/Aluev/StealthShooter/Content'):
    source=Path(source_content).resolve()
    target=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())).resolve()
    assert target.as_posix().endswith('/Practicals/HW09_GAS/Content')
    for folder in ['Rock_Collection_04','Abandoned_Cathedral']:
        assert (source/folder).is_dir(), 'Install your licensed Fab pack first: '+folder
        shutil.copytree(source/folder,target/folder,dirs_exist_ok=True)
    unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(['/Game/Rock_Collection_04','/Game/Abandoned_Cathedral'],True)


def material(name,color,metal=0,emissive=False):
    path='/Game/HW09/Materials/'+name
    obj=unreal.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else None
    if obj:return obj
    obj=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,'/Game/HW09/Materials',unreal.Material,unreal.MaterialFactoryNew())
    lib=unreal.MaterialEditingLibrary
    n=lib.create_material_expression(obj,unreal.MaterialExpressionConstant3Vector,-220,0)
    n.set_editor_property('constant',unreal.LinearColor(*color,1))
    lib.connect_material_property(n,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR if emissive else unreal.MaterialProperty.MP_BASE_COLOR)
    for val,prop,y in [(.65,unreal.MaterialProperty.MP_ROUGHNESS,100),(metal,unreal.MaterialProperty.MP_METALLIC,200)]:
        c=lib.create_material_expression(obj,unreal.MaterialExpressionConstant,-200,y);c.set_editor_property('r',val);lib.connect_material_property(c,'',prop)
    lib.recompile_material(obj);unreal.EditorAssetLibrary.save_loaded_asset(obj)
    return obj


def run():
    assert 'HW_09_GAS' in unreal.Paths.get_project_file_path()
    assert not unreal.EditorLevelLibrary.get_pie_worlds(False)
    for p in [ROCK.format(1),CAT+'arch_1-2/Static_Mesh/SM_arch_1_']:
        assert unreal.EditorAssetLibrary.does_asset_exist(p),p
    levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not unreal.EditorAssetLibrary.does_asset_exist(MAP):assert levels.new_level_from_template(MAP,SOURCE)
    else:assert levels.load_level(MAP)
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    # Only this optional map is dressed. Preserve the public source map and old projects.
    for a in actors.get_all_level_actors():
        if isinstance(a,unreal.StaticMeshActor) and a.get_actor_label() not in ['SM_Cube','SM_SkySphere'] and not a.get_actor_label().startswith('Ruins_'):
            actors.destroy_actor(a)
        if a.get_actor_label().startswith('Ruins_'):actors.destroy_actor(a)
    rng=random.Random(96)
    stone=material('M_DashGround',(.095,.105,.09))
    bronze=material('M_DashBronze',(.19,.12,.045),.8)
    glow=material('M_DashRelic',(.05,1.4,2.0),emissive=True)
    def mesh(label,path,loc,scale=1,yaw=0,collision=True,mat=None):
        asset=unreal.load_asset(path);assert asset,path
        a=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(*loc),unreal.Rotator(yaw=yaw))
        a.set_actor_label('Ruins_'+label);a.set_folder_path('DashRuins')
        a.static_mesh_component.set_static_mesh(asset)
        a.set_actor_scale3d(unreal.Vector(*scale) if isinstance(scale,tuple) else unreal.Vector(scale,scale,scale))
        a.static_mesh_component.set_collision_profile_name('BlockAll' if collision else 'NoCollision')
        if mat:a.static_mesh_component.set_material(0,mat)
        return a
    floor=next(a for a in actors.get_all_level_actors() if a.get_actor_label()=='SM_Cube')
    floor.modify();floor.static_mesh_component.modify()
    floor.static_mesh_component.set_material(0,stone)
    floor.set_actor_hidden_in_game(True)
    floor.static_mesh_component.set_visibility(False)
    mesh('EarthUnderPaving','/Engine/BasicShapes/Cube',(1500,1750,-31),(30,35,.5),collision=False,mat=stone)
    for ix in range(8):
        for iy in range(9):
            mesh('Paving_%d_%d'%(ix,iy),CAT+'floor_1/Static_Mesh/SM_floor_1',(200+ix*400,200+iy*400,-14.5),yaw=90*((ix+iy)%4),collision=False)
    # Accurate triangle collision leaves arch openings traversable and blocks the stone pillars.
    arch=unreal.load_asset(CAT+'arch_1-2/Static_Mesh/SM_arch_1_')
    arch.get_editor_property('body_setup').set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    unreal.EditorAssetLibrary.save_loaded_asset(arch)
    for side,y in [('South',320),('North',3100)]:
        for i,x in enumerate([700,1350,2100,2750]):mesh('Arcade_'+side+str(i),arch.get_path_name(),(x,y,0),yaw=90)
    mesh('Gateway',arch.get_path_name(),(2350,1450,0),scale=1.15)
    for i,y in enumerate(range(100,3400,400)):
        for side,x in [('West',20),('East',3000)]:mesh('Wall_'+side+str(i),CAT+'Wall_1/Static_Mesh/SM_wall_1',(x,y,-5))
    for side,y in [('South',-50),('North',3500)]:
        for i,x in enumerate(range(150,3200,350)):
            mesh('Cliff_'+side+str(i),ROCK.format(1+i%4),(x,y+rng.uniform(-60,60),-25),rng.uniform(1.4,2.5),rng.uniform(0,360))
    for side,x in [('West',-120),('East',3140)]:
        for i,y in enumerate(range(100,3500,500)):
            mesh('Ridge_'+side+str(i),ROCK.format(1+i%4),(x,y,-30),rng.uniform(1.6,2.6),rng.uniform(0,360))
    for i,(x,y,s,yaw) in enumerate([(1430,1190,1.25,24),(1740,2370,1.2,-32),(1050,2730,.9,98),(2480,900,1.1,54)]):
        mesh('DashRock_'+str(i),ROCK.format(1+i%4),(x,y,-8),s,yaw)
    for i in range(22):
        mesh('Rubble_'+str(i),CAT+'debris/Static_Mesh/SM_brick_1',(rng.uniform(400,2700),rng.choice([rng.uniform(420,600),rng.uniform(2850,3050)]),1),rng.uniform(.8,1.5),rng.uniform(0,360))
    mesh('RelicPlinth','/Engine/BasicShapes/Cylinder',(2700,1720,35),(1.5,1.5,.7),mat=bronze)
    mesh('Relic','/Engine/BasicShapes/Sphere',(2700,1720,113),(.46,.46,.46),mat=glow)
    for i,(x,y,z,color,intensity) in enumerate([(2350,1420,230,(1,.52,.22),250),(2350,2025,230,(1,.52,.22),250),(2680,1720,140,(.15,.65,1),140)]):
        a=actors.spawn_actor_from_class(unreal.PointLight,unreal.Vector(x,y,z));a.set_actor_label('Ruins_Light'+str(i));a.set_folder_path('DashRuins')
        a.light_component.set_light_color(unreal.LinearColor(*color,1));a.light_component.set_intensity(intensity);a.light_component.set_editor_property('attenuation_radius',450)
    fog=actors.spawn_actor_from_class(unreal.ExponentialHeightFog,unreal.Vector());fog.set_actor_label('Ruins_Mist')
    fog.get_component_by_class(unreal.ExponentialHeightFogComponent).set_editor_property('fog_density',.012)
    for a in actors.get_all_level_actors():
        if isinstance(a,unreal.PlayerStart):
            a.modify()
            a.set_actor_location(unreal.Vector(800,1720,96),False,False);a.set_actor_rotation(unreal.Rotator(yaw=0),False)
        if isinstance(a,unreal.DirectionalLight):
            a.modify();a.light_component.modify()
            a.set_actor_rotation(unreal.Rotator(pitch=-32,yaw=-38),False);a.light_component.set_intensity(5)
            a.light_component.set_editor_property('use_temperature',True);a.light_component.set_editor_property('temperature',5200)
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(unreal.Vector(250,1250,400),unreal.Rotator(pitch=-12,yaw=20))
    assert levels.save_current_level()
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True,True)
    return {'map':MAP,'dressing_actors':sum(a.get_actor_label().startswith('Ruins_') for a in actors.get_all_level_actors()),'blocking_rocks':4,'licensed_assets_local_only':True}
