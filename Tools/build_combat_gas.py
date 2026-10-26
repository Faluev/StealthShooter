"""Practical 10.5, isolated assets/map. Existing practicals are never rebuilt."""
import unreal
from pathlib import Path

ROOT = '/Game/StealthShooter/CombatGAS'
MAP = '/Game/StealthShooter/Maps/L_CombatGAS'
B = unreal.BlueprintEditorLibrary
EAL = unreal.EditorAssetLibrary


def save(obj):
    assert EAL.save_loaded_asset(obj, False), obj.get_path_name()


def bp(folder, name, parent, note):
    path = ROOT + '/' + folder + '/' + name
    obj = unreal.load_asset(path) if EAL.does_asset_exist(path) else None
    if not obj:
        if issubclass(parent, unreal.UserWidget):
            factory = unreal.WidgetBlueprintFactory()
            factory.set_editor_property('parent_class',parent)
            obj = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, ROOT+'/'+folder, unreal.WidgetBlueprint, factory)
        else:
            factory = unreal.BlueprintFactory()
            factory.set_editor_property('parent_class',parent)
            obj = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, ROOT+'/'+folder, unreal.Blueprint, factory)
    assert obj and B.compile_blueprint(obj), path
    if hasattr(unreal, 'BlueprintGraphEditor'):
        editor = unreal.BlueprintGraphEditor.get_graph_editor_by_name(obj, 'EventGraph')
        if editor:
            for comment in editor.list_comment_nodes(): editor.remove_comment_node(comment)
            editor.add_comment_to_nodes(note, editor.list_all_nodes())
    save(obj)
    return obj


def material(name, color, roughness=.7, metallic=0., emissive=False):
    path = ROOT + '/Materials/' + name
    mat = unreal.load_asset(path)
    if mat: return mat
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, ROOT+'/Materials', unreal.Material, unreal.MaterialFactoryNew())
    lib = unreal.MaterialEditingLibrary
    rgb = lib.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -250, 0)
    rgb.set_editor_property('constant', unreal.LinearColor(*color, 1))
    lib.connect_material_property(rgb, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR if emissive else unreal.MaterialProperty.MP_BASE_COLOR)
    for value, prop, y in [(roughness,unreal.MaterialProperty.MP_ROUGHNESS,180), (metallic,unreal.MaterialProperty.MP_METALLIC,280)]:
        node = lib.create_material_expression(mat, unreal.MaterialExpressionConstant, -250, y)
        node.set_editor_property('r', value)
        lib.connect_material_property(node,'',prop)
    lib.recompile_material(mat)
    save(mat)
    return mat


def build():
    assert not unreal.EditorLevelLibrary.get_pie_worlds(False), 'Stop Play first.'
    assert not EAL.does_asset_exist(MAP), 'The scene already exists; do not destructively regenerate it.'
    unreal.SystemLibrary.collect_garbage()
    assert hasattr(unreal, 'CombatAttributeSet'), 'Build and load the CombatGAS C++ plugin first.'
    mats = {
        'ground': material('M_CombatFloor',(.055,.075,.095),.85),
        'cover': material('M_CombatConcrete',(.23,.27,.3),.92),
        'dark': material('M_CombatMetal',(.035,.045,.06),.3,.8),
        'accent': material('M_CombatOrange',(.8,.21,.035),.45,.2),
        'light': material('M_CombatLight',(.25,1.2,1.8),.4,emissive=True),
        'tracer': material('M_CombatTracer',(8.,2.5,.3),.4,emissive=True),
    }
    damage = bp('Abilities/Effects','GE_BotShotDamage',unreal.CombatDamageEffect,
        'Instant Gameplay Effect: additive -10 CombatAttributeSet.Health. The AttributeSet clamps Health to [0, MaxHealth].')
    cooldown = bp('Abilities/Effects','GE_BotShotCooldown',unreal.CombatShotCooldown,
        'Duration 1.25 seconds. Grant Cooldown.Bot.Shoot through TargetTagsGameplayEffectComponent. CommitAbility applies this effect; no fire timer.')
    cue = bp('Abilities/Cues','GC_Bot_Shoot',unreal.CombatShotCue,
        'GameplayCue.Bot.Shoot -> native OnExecute. Cosmetic muzzle flash, tracer and sound only. No damage or collision in presentation.')
    shoot = bp('Abilities','GA_BotShoot',unreal.CombatShootAbility,
        'Sight/target check -> CommitAbility -> collision trace -> Gameplay Cue -> GE damage to target ASC -> EndAbility. Failed cooldown commits cannot fire.')
    unreal.get_default_object(shoot.generated_class()).set_editor_property('cooldown_gameplay_effect_class',cooldown.generated_class())
    save(shoot)
    hud = bp('UI','WBP_CombatHUD',unreal.CombatHUD,
        'UMG created in native Construct. Health / MaxHealth updates from ASC attribute-change delegates, removed in Destruct. Bot/cooldown text aids presentation.')
    player = bp('Characters','BP_CombatPlayer',unreal.CombatPlayer,
        'Player owns ASC and UCombatAttributeSet (Health, MaxHealth). Third-person movement and camera; health bar subscribes to the GAS attribute.')
    bot = bp('Characters','BP_CombatBot',unreal.CombatBot,
        'Patrol -> detect -> draw weapon -> aim -> request GA_BotShoot. Lose sight -> stop shots -> holster -> resume NavMesh patrol. GAS owns shot cadence.')
    for asset in [player,bot]:
        cdo = unreal.get_default_object(asset.generated_class())
        cdo.mesh.set_skeletal_mesh_asset(unreal.load_asset('/Game/Characters/Mannequins/Meshes/SKM_Manny'))
        cdo.mesh.set_anim_instance_class(unreal.load_asset('/Game/Characters/Mannequins/Animations/ABP_Manny').generated_class())
        if asset == player:
            cdo.set_editor_property('hud_class',hud.generated_class())
        else:
            cdo.set_editor_property('shoot_ability',shoot.generated_class())
            cdo.set_editor_property('damage_effect',damage.generated_class())
            cdo.set_editor_property('shot_cue',cue.generated_class())
            cdo.set_editor_property('tracer_material',mats['tracer'])
            cdo.weapon_body.set_material(0,mats['dark'])
            cdo.weapon_barrel.set_material(0,mats['dark'])
            sound = unreal.load_asset(ROOT+'/Audio/S_BotShot')
            if sound:cdo.set_editor_property('shot_sound',sound)
        assert B.compile_blueprint(asset)
        save(asset)
    gm = bp('Core','BP_CombatGameMode',unreal.CombatGameMode,'This GameMode belongs only to L_CombatGAS; other maps keep their original GameModes.')
    unreal.get_default_object(gm.generated_class()).set_editor_property('default_pawn_class',player.generated_class())
    save(gm)

    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    assert levels.new_level(MAP)
    sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    def actor(cls,name,loc,rot=None):
        a=sub.spawn_actor_from_class(cls,unreal.Vector(*loc),rot or unreal.Rotator())
        a.set_actor_label(name)
        a.set_folder_path('CombatGAS')
        return a
    def box(name,loc,scale,key):
        a=actor(unreal.StaticMeshActor,name,loc)
        a.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'))
        a.set_actor_scale3d(unreal.Vector(*scale))
        a.static_mesh_component.set_material(0,mats[key])
        a.static_mesh_component.set_collision_profile_name('BlockAll')
        return a
    box('TrainingFloor',(0,0,-25),(34,26,.5),'ground')
    for name,loc,scale in [
        ('NorthWall',(0,1300,160),(34,.35,3.2)),('SouthWall',(0,-1300,160),(34,.35,3.2)),
        ('EastWall',(1700,0,160),(.35,26,3.2)),('WestWall',(-1700,0,160),(.35,26,3.2)),
        ('SightCover',(-300,0,130),(.6,5.6,2.6)),
        ('CoverWingA',(-650,730,90),(4,1.2,1.8)),('CoverWingB',(600,-700,90),(4,1.2,1.8))]:
        box(name,loc,scale,'cover')
    # Collidable cover is deliberate: it must block both sight and the weapon trace.
    for y in [-1200,1200]:
        box('AccentRail'+str(y),(0,y,190),(30,.08,.1),'accent')
        for x in [-1400,-700,0,700,1400]: box('WallRib'+str((x,y)),(x,y,150),(.12,.24,3),'dark')
    for x in [-1300,-1100,-900,-700,900,1100,1300]:
        box('FloorStripe'+str(x),(x,0,1),(.025,22,.01),'accent')
    start=actor(unreal.PlayerStart,'CombatPlayerStart',(-1050,0,95),unreal.Rotator(yaw=0))
    bot_actor=actor(bot.generated_class(),'CombatGuard',(700,0,95),unreal.Rotator(yaw=180))
    bot_actor.set_editor_property('patrol_points',[unreal.Vector(700,-380,95),unreal.Vector(700,380,95)])
    bot_actor.set_editor_property('sight_radius',1800.)
    light=actor(unreal.DirectionalLight,'CombatSun',(0,0,700),unreal.Rotator(pitch=-45,yaw=-45))
    light.light_component.set_intensity(4.)
    sky=actor(unreal.SkyLight,'CombatSky',(0,0,600))
    sky.light_component.set_intensity(.8)
    actor(unreal.SkyAtmosphere,'CombatAtmosphere',(0,0,0))
    pp=actor(unreal.PostProcessVolume,'CombatExposure',(0,0,0))
    pp.set_editor_property('unbound',True)
    settings=pp.get_editor_property('settings')
    for key,value in [('override_auto_exposure_min_brightness',True),('override_auto_exposure_max_brightness',True),('auto_exposure_min_brightness',1.),('auto_exposure_max_brightness',1.)]:settings.set_editor_property(key,value)
    pp.set_editor_property('settings',settings)
    nav=actor(unreal.NavMeshBoundsVolume,'CombatNavigation',(0,0,100))
    nav.set_actor_scale3d(unreal.Vector(18,14,4))
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.NavigationSystemV1.get_navigation_system(world).on_navigation_bounds_updated(nav)
    world.get_world_settings().set_editor_property('default_game_mode',gm.generated_class())
    for label,text,loc,yaw in [
        ('TrainingTitle','10.5  /  COMBAT SYSTEM',(1675,-620,260),180),
        ('CoverLabel','COVER  /  BREAK LINE OF SIGHT',(-334,-240,210),180),
        ('LaneLabel','STEP OUT TO ENGAGE',(-1650,580,230),0)]:
        a=actor(unreal.TextRenderActor,label,loc,unreal.Rotator(yaw=yaw))
        a.text_render.set_text(text);a.text_render.set_world_size(30)
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(unreal.Vector(-1500,-1900,1600),unreal.Rotator(pitch=-34,yaw=48))
    assert levels.save_current_level()
    unreal.SystemLibrary.execute_console_command(world,'RebuildNavigation')
    assert levels.save_current_level()
    return {'map':MAP,'player':player.get_path_name(),'bot':bot.get_path_name(),'health':100,'damage':10,'cooldown':1.25}
