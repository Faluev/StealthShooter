"""Create practical 12.7 in its own asset tree and map; never regenerate earlier practicals."""
import unreal

ROOT='/Game/StealthShooter/Quests'
MAP='/Game/StealthShooter/Maps/L_QuestArena'
B=unreal.BlueprintEditorLibrary
EAL=unreal.EditorAssetLibrary

def save(obj):assert EAL.save_loaded_asset(obj,False),obj.get_path_name()

def blueprint(folder,name,parent,note):
    path=ROOT+'/'+folder+'/'+name
    if EAL.does_asset_exist(path):return unreal.load_asset(path)
    factory=unreal.WidgetBlueprintFactory() if issubclass(parent,unreal.UserWidget) else unreal.BlueprintFactory()
    factory.set_editor_property('parent_class',parent)
    kind=unreal.WidgetBlueprint if issubclass(parent,unreal.UserWidget) else unreal.Blueprint
    obj=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,ROOT+'/'+folder,kind,factory)
    assert obj and B.compile_blueprint(obj),path
    editor=unreal.BlueprintGraphEditor.get_graph_editor_by_name(obj,'EventGraph')
    if editor:
        nodes=editor.list_all_nodes()
        if nodes:editor.add_comment_to_nodes(note,nodes)
    save(obj);return obj

def material(name,color,metallic=0.,roughness=.8):
    path=ROOT+'/Materials/'+name
    if EAL.does_asset_exist(path):return unreal.load_asset(path)
    obj=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,ROOT+'/Materials',unreal.Material,unreal.MaterialFactoryNew())
    lib=unreal.MaterialEditingLibrary
    rgb=lib.create_material_expression(obj,unreal.MaterialExpressionConstant3Vector,-300,0)
    rgb.set_editor_property('constant',unreal.LinearColor(*color,1))
    lib.connect_material_property(rgb,'',unreal.MaterialProperty.MP_BASE_COLOR)
    for value,prop,y in [(roughness,unreal.MaterialProperty.MP_ROUGHNESS,150),(metallic,unreal.MaterialProperty.MP_METALLIC,250)]:
        expr=lib.create_material_expression(obj,unreal.MaterialExpressionConstant,-300,y)
        expr.set_editor_property('r',value);lib.connect_material_property(expr,'',prop)
    lib.recompile_material(obj);save(obj);return obj

def build():
    assert not unreal.EditorLevelLibrary.get_pie_worlds(False),'Stop Play before authoring.'
    assert not EAL.does_asset_exist(MAP),'Do not destructively regenerate an existing scene.'
    mats={
      'floor':material('M_QuestFloor',(.055,.09,.12)),
      'wall':material('M_QuestWall',(.18,.24,.29)),
      'dark':material('M_QuestSteel',(.04,.055,.07),.8,.3),
      'accent':material('M_QuestMarkings',(.85,.3,.055),.3,.5),
      'enemy':material('M_QuestEnemy',(.36,.085,.035),.75,.3),
    }
    effect=blueprint('Abilities/Effects','GE_QuestDamage',unreal.QuestDamageEffect,'Instant -25 Health through GAS. Death is emitted by the target only after its Health attribute reaches zero.')
    cooldown=blueprint('Abilities/Effects','GE_QuestShotCooldown',unreal.QuestShotCooldown,'0.35-second Gameplay Effect grants Cooldown.Player.QuestShot; CommitAbility gates semi-automatic fire.')
    cue=blueprint('Abilities/Cues','GC_Quest_Shot',unreal.QuestShotCue,'Cosmetic shot via the Gameplay Cue manager. Explicit reference ensures cooked availability; no damage in the cue.')
    ability=blueprint('Abilities','GA_QuestShoot',unreal.QuestShootAbility,'Check live player and active quest -> commit -> camera aim trace -> muzzle obstruction trace -> cue -> damage GE -> end.')
    unreal.get_default_object(ability.generated_class()).set_editor_property('cooldown_gameplay_effect_class',cooldown.generated_class());save(ability)
    hud=blueprint('UI','WBP_QuestHUD',unreal.QuestHUD,'GAS health delegate and quest-manager delegate drive UI. Common success/failure panel includes a replay button. Subscriptions are removed in Destruct.')
    player=blueprint('Characters','BP_QuestPlayer',unreal.QuestPlayer,'Inherits the completed GAS player. LMB requests GA_QuestShoot; R and the replay button invoke GameMode.RestartPlayer without level reload.')
    bot=blueprint('Characters','BP_QuestBot',unreal.QuestBot,'GAS Health=50. Two 25-damage hits kill. Emit death once, stop combat, ragdoll, free a spawner slot and clean up the corpse.')
    old='/Game/StealthShooter/CombatGAS/'
    for asset in [player,bot]:
        cdo=unreal.get_default_object(asset.generated_class())
        cdo.mesh.set_skeletal_mesh_asset(unreal.load_asset('/Game/Characters/Mannequins/Meshes/SKM_Manny'))
        cdo.mesh.set_anim_instance_class(unreal.load_asset('/Game/Characters/Mannequins/Animations/ABP_Manny').generated_class())
        cdo.set_editor_property('shot_sound',unreal.load_asset(old+'Audio/S_BotShot'))
        cdo.set_editor_property('tracer_material',unreal.load_asset(old+'Materials/M_CombatTracer'))
        if asset==player:
            cdo.set_editor_property('hud_class',hud.generated_class())
            cdo.set_editor_property('fire_ability',ability.generated_class())
            cdo.set_editor_property('shot_damage_effect',effect.generated_class())
            cdo.set_editor_property('shot_cue_class',cue.generated_class())
            cdo.rifle.set_material(0,mats['dark'])
        else:
            cdo.set_editor_property('shoot_ability',unreal.load_asset(old+'Abilities/GA_BotShoot').generated_class())
            cdo.set_editor_property('damage_effect',unreal.load_asset(old+'Abilities/Effects/GE_BotShotDamage').generated_class())
            cdo.set_editor_property('shot_cue',unreal.load_asset(old+'Abilities/Cues/GC_Bot_Shoot').generated_class())
            cdo.set_editor_property('sight_radius',1800.)
            cdo.mesh.set_material(0,mats['enemy']);cdo.mesh.set_material(1,mats['enemy'])
            cdo.weapon_body.set_material(0,mats['dark']);cdo.weapon_barrel.set_material(0,mats['dark'])
        assert B.compile_blueprint(asset);save(asset)
    quest=blueprint('Objectives','BP_QuestKillBots',unreal.QuestKillBots,'Own counter, configurable required kills/time limit. Count only distinct dead bots killed by the player while active. Terminal states are immutable until reset.')
    director=blueprint('Core','BP_QuestDirector',unreal.QuestDirector,'Discover/sort base quest actors; bind their change delegates; activate sequentially; route common completion/failure to HUD and GameMode.')
    spawner=blueprint('Spawning','BP_QuestBotSpawner',unreal.QuestBotSpawner,'Dynamically spawn on NavMesh, cap living bots at two, free capacity on death. Destroying a live bot does not count as a kill.')
    unreal.get_default_object(spawner.generated_class()).modify()
    unreal.get_default_object(spawner.generated_class()).set_editor_property('bot_class',bot.generated_class());save(spawner)
    mode=blueprint('Core','BP_QuestGameMode',unreal.QuestGameMode,'Start quests/spawners, freeze combat on a terminal result. Restart clears old bots, calls RestartPlayer and resets quests without reloading the world.')
    unreal.get_default_object(mode.generated_class()).set_editor_property('default_pawn_class',player.generated_class());save(mode)
    levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem);assert levels.new_level(MAP)
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    def actor(cls,name,loc,rot=None):
        a=actors.spawn_actor_from_class(cls,unreal.Vector(*loc),rot or unreal.Rotator());a.set_actor_label(name);a.set_folder_path('QuestArena');return a
    def box(name,loc,scale,key):
        a=actor(unreal.StaticMeshActor,name,loc);a.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'))
        a.set_actor_scale3d(unreal.Vector(*scale));a.static_mesh_component.set_material(0,mats[key]);a.static_mesh_component.set_collision_profile_name('BlockAll');return a
    box('QuestFloor',(0,0,-25),(30,22,.5),'floor')
    for name,loc,scale in [('NorthWall',(0,1100,180),(30,.3,3.6)),('SouthWall',(0,-1100,180),(30,.3,3.6)),('EastWall',(1500,0,180),(.3,22,3.6)),('WestWall',(-1500,0,180),(.3,22,3.6)),('CentralCover',(-250,0,110),(.55,4,2.2)),('SideCover',(100,-750,70),(3,1,1.4))]:box(name,loc,scale,'wall')
    for y in [-1060,1060]:
        box('OrangeRail'+str(y),(0,y,200),(29,.05,.08),'accent')
        for x in [-1300,-650,0,650,1300]:box('WallRib'+str((x,y)),(x,y,170),(.14,.2,3.4),'dark')
    for x in [-1200,-1000,-800,-600,0,200,400,600,800,1000,1200]:box('FloorGuide'+str(x),(x,0,1),(.025,20,.015),'accent')
    actor(unreal.PlayerStart,'QuestPlayerStart',(-850,0,95),unreal.Rotator(yaw=0))
    actor(director.generated_class(),'QuestDirector',(0,0,0))
    q=actor(quest.generated_class(),'Quest_EliminateThree',(0,0,0));q.set_editor_property('required_kills',3);q.set_editor_property('time_limit',90.)
    s=actor(spawner.generated_class(),'QuestBotSpawner',(750,0,0));s.set_editor_property('bot_class',bot.generated_class());s.spawn_area.set_box_extent(unreal.Vector(220,350,100),False)
    light=actor(unreal.DirectionalLight,'QuestSun',(0,0,600),unreal.Rotator(pitch=-45,yaw=-45));light.light_component.set_intensity(4.)
    sky=actor(unreal.SkyLight,'QuestSky',(0,0,600));sky.light_component.set_intensity(.8)
    actor(unreal.SkyAtmosphere,'QuestAtmosphere',(0,0,0))
    pp=actor(unreal.PostProcessVolume,'QuestExposure',(0,0,0));pp.set_editor_property('unbound',True);settings=pp.get_editor_property('settings')
    for k,v in [('override_auto_exposure_min_brightness',True),('override_auto_exposure_max_brightness',True),('auto_exposure_min_brightness',1.),('auto_exposure_max_brightness',1.)]:settings.set_editor_property(k,v)
    pp.set_editor_property('settings',settings)
    nav=actor(unreal.NavMeshBoundsVolume,'QuestNavigation',(0,0,100));nav.set_actor_scale3d(unreal.Vector(16,12,4))
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.NavigationSystemV1.get_navigation_system(world).on_navigation_bounds_updated(nav)
    world.get_world_settings().set_editor_property('default_game_mode',mode.generated_class())
    for name,text,loc,yaw in [('SectorTitle','SECTOR 12 / TRAINING',(1470,-590,280),180),('CoverTitle','COVER / SAFE START',(-282,-165,170),180)]:
        a=actor(unreal.TextRenderActor,name,loc,unreal.Rotator(yaw=yaw));a.text_render.set_text(text);a.text_render.set_world_size(25)
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(unreal.Vector(-1800,-1800,1600),unreal.Rotator(pitch=-35,yaw=45))
    assert levels.save_current_level()
    unreal.SystemLibrary.execute_console_command(world,'RebuildNavigation')
    return {'map':MAP,'quest_kills':3,'time_limit':90,'spawner_max_alive':2,'bots_preplaced':0}
