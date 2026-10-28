"""Use the installed Epic rifle/poses; restore optional Fab dressing from the local library."""
import unreal,random
from pathlib import Path
ROOT='/Game/StealthShooter/Quests/'
MAP='/Game/StealthShooter/Maps/L_QuestArena'
FAB_MAP='/Game/StealthShooter/Maps/L_QuestArena_Ruins'

def upgrade_characters():
    assert not unreal.EditorLevelLibrary.get_pie_worlds(False)
    lib=unreal.EditorAssetLibrary
    animroot='/Game/Characters/Mannequins/Anims/Rifle/'
    target=ROOT+'Animations/BS_QuestRifle'
    blend=unreal.load_asset(target) if lib.does_asset_exist(target) else None
    if not blend:
        names=['MF_Rifle_Idle_ADS'];positions=[unreal.Vector()]
        for folder,speed in [('Walk',150),('Jog',450)]:
            for suffix,x,y in [('Fwd',1,0),('Bwd',-1,0),('Left',0,-1),('Right',0,1),('Fwd_Left',.707,-.707),('Fwd_Right',.707,.707),('Bwd_Left',-.707,-.707),('Bwd_Right',-.707,.707)]:
                names.append(folder+'/MF_Rifle_'+folder+'_'+suffix);positions.append(unreal.Vector(x*speed,y*speed,0))
        animations=[unreal.load_asset(animroot+n) for n in names]
        assert all(animations)
        blend=unreal.QuestPresentation.build_rifle_locomotion(target,animations,positions)
        assert blend
        lib.save_loaded_asset(blend)
    rifle=unreal.load_asset('/Game/Weapons/Rifle/Meshes/SM_Rifle');assert rifle
    # Template mesh has a grip origin. A named barrel end drives cosmetics/traces.
    if not rifle.find_socket('Muzzle'):
        socket=unreal.new_object(unreal.StaticMeshSocket,outer=rifle)
        socket.set_editor_property('socket_name','Muzzle')
        socket.set_editor_property('relative_location',unreal.Vector(0,51,4))
        rifle.add_socket(socket);lib.save_loaded_asset(rifle)
    for name in ['BP_QuestPlayer','BP_QuestBot']:
        bp=unreal.load_asset(ROOT+'Characters/'+name);cdo=unreal.get_default_object(bp.generated_class());cdo.modify()
        cdo.set_editor_property('armed_locomotion',blend)
        cdo.set_editor_property('armed_fall',unreal.load_asset(animroot+'Jump/MM_Rifle_Jump_Fall_Loop'))
        part=cdo.rifle if name=='BP_QuestPlayer' else cdo.weapon_body
        part.set_static_mesh(rifle);part.set_editor_property('override_materials',[])
        part.set_editor_property('relative_location',unreal.Vector())
        part.set_editor_property('relative_rotation',unreal.Rotator(pitch=18,yaw=82,roll=9))
        part.set_editor_property('relative_scale3d',unreal.Vector(1,1,1))
        unreal.BlueprintEditorLibrary.compile_blueprint(bp);lib.save_loaded_asset(bp)
    return {'rifle':rifle.get_path_name(),'locomotion':blend.get_path_name(),'directional_samples':17}

def dress_ruins():
    import prepare_catapult_fab
    restored=prepare_catapult_fab.restore()
    levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not unreal.EditorAssetLibrary.does_asset_exist(FAB_MAP):assert levels.new_level_from_template(FAB_MAP,MAP)
    else:assert levels.load_level(FAB_MAP)
    sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);rng=random.Random(127)
    prefix='/Game/Abandoned_Cathedral/Assets/'
    def mesh(name,path,loc,scale=1,yaw=0):
        name='QuestRuins_'+name
        a=next((x for x in sub.get_all_level_actors() if x.get_actor_label()==name),None)
        if not a:a=sub.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(*loc),unreal.Rotator(yaw=yaw))
        a.set_actor_location_and_rotation(unreal.Vector(*loc),unreal.Rotator(yaw=yaw),False,False)
        a.set_actor_label(name);a.set_folder_path('QuestArena/LocalFabDressing')
        asset=unreal.load_asset(path);assert asset,path
        a.static_mesh_component.set_static_mesh(asset);a.set_actor_scale3d(unreal.Vector(scale,scale,scale))
        a.static_mesh_component.set_collision_profile_name('NoCollision')
        return a
    for side,y in [('North',1240),('South',-1240)]:
        for i,x in enumerate([-1000,-300,400,1100]):
            mesh(side+'Arch'+str(i),prefix+'arch_1-2/Static_Mesh/SM_arch_1_',(x,y,0),1.15,90)
        for i in range(10):
            variant=1+i%4
            mesh(side+'Rock'+str(i),'/Game/Rock_Collection_04/Meshes/Rock_%02d/StaticMeshes/SM_Rock_%02d'%(variant,variant),(-1500+i*340+rng.uniform(-80,80),y+rng.choice([-1,1])*rng.uniform(60,160),-30),rng.uniform(.65,1.35),rng.uniform(0,360))
    for i,(x,y) in enumerate([(-1420,-1000),(-1420,1000),(1420,-1000),(1420,1000)]):
        mesh('Pillar'+str(i),prefix+'arch_1-2/Static_Mesh/SM_arch_pillar_1',(x,y,0),1.4)
    for i in range(16):
        mesh('Rubble'+str(i),prefix+'debris/Static_Mesh/SM_brick_1',(rng.uniform(-1350,1350),rng.choice([-1,1])*rng.uniform(930,1040),2),rng.uniform(.8,1.5),rng.uniform(0,360))
    # Tile at the original floor height; the original collision plane remains authoritative.
    for ix,x in enumerate(range(-1400,1500,400)):
        for iy,y in enumerate(range(-1000,1100,400)):
            mesh('FloorTile'+str((ix,iy)),prefix+'floor_1/Static_Mesh/SM_floor_1',(x,y,-14.1),1)
    # Real masonry provides consistent texel scale on the arena boundary.
    for side,y in [('North',1100),('South',-1100)]:
        for i,x in enumerate(range(-1100,1700,400)):
            mesh(side+'Masonry'+str(i),prefix+'Wall_1/Static_Mesh/SM_wall_1',(x,y,0),1,90)
    for side,x in [('East',1500),('West',-1500)]:
        for i,y in enumerate(range(-1100,1100,400)):
            mesh(side+'Masonry'+str(i),prefix+'Wall_1/Static_Mesh/SM_wall_1',(x,y,0),1,0)
    rockmat=unreal.load_asset('/Game/Rock_Collection_04/Meshes/Rock_01/Materials/MI_Rock_01')
    for a in sub.get_all_level_actors():
        label=a.get_actor_label()
        if label in ['NorthWall','SouthWall','EastWall','WestWall','CentralCover','SideCover'] and rockmat:a.static_mesh_component.set_material(0,rockmat)
        if label in ['QuestFloor','NorthWall','SouthWall','EastWall','WestWall'] or label.startswith(('FloorGuide','OrangeRail','WallRib')):a.set_actor_hidden_in_game(True)
    levels.save_current_level()
    return {'map':FAB_MAP,'decor':122,'decor_collision':'NoCollision','restore':restored}
