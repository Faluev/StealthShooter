"""Build the separate mechanics test scene used in lessons 11.3-11.5."""
import unreal
import maze_graph as m
from maze_graph import g

MAP='/Game/StealthShooter/Maps/L_MazeMechanics'
def build():
    levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if unreal.EditorAssetLibrary.does_asset_exist(MAP):assert levels.load_level(MAP)
    else:assert levels.new_level(MAP)
    sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    def actor(cls,label,loc,rot=None):
        a=next((a for a in sub.get_all_level_actors() if a.get_actor_label()==label),None)
        if a is None:a=sub.spawn_actor_from_class(cls,unreal.Vector(*loc),rot or unreal.Rotator())
        a.set_actor_label(label);a.set_actor_location(unreal.Vector(*loc),False,False)
        if rot is not None:a.set_actor_rotation(rot,False)
        return a
    def mesh(label,loc,scale,mat,collision=True):
        a=actor(unreal.StaticMeshActor,label,loc);a.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'))
        a.set_actor_scale3d(unreal.Vector(*scale));a.static_mesh_component.set_material(0,unreal.load_asset('/Game/StealthShooter/MaterialLibrary/'+mat))
        a.static_mesh_component.set_collision_profile_name('BlockAll' if collision else 'NoCollision');a.set_folder_path('Maze/Environment');return a
    def label(name,text,loc,size=24):
        a=actor(unreal.TextRenderActor,name,loc,unreal.Rotator(yaw=180));a.text_render.set_text(text);a.text_render.set_world_size(size);a.text_render.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
        a.text_render.set_editor_property('text_material',unreal.load_asset('/Game/StealthShooter/MaterialLibrary/Environment/M_LabRoom_Text'));a.set_folder_path('Maze/Instructions');return a
    floor='Environment/M_LabRoom_Floor';wall='Environment/M_LabRoom_Wall';body='Lighting/M_LightFixture';accent='Environment/M_LabRoom_Accent'
    mesh('MazeFloor',(200,0,-20),(32,26,.4),floor)
    for x in [-1400,1800]:mesh('BoundaryX'+str(x),(x,0,150),(.3,26,3),wall)
    for y in [-1300,1300]:mesh('BoundaryY'+str(y),(200,y,150),(32,.3,3),wall)
    for i,(y,length) in enumerate([(-1005,590),(-270,540),(187.5,375),(962.5,675)]):mesh('Divider'+str(i),(200,y,140),(.3,length/100,2.8),wall)
    for suffix,y in [('Left',-715),('Right',-525)]:mesh('DoorFrame'+suffix,(200,y,140),(.5,.2,2.8),body)
    mesh('DoorLintel',(200,-620,275),(.5,2.1,.2),body)
    for suffix,y in [('Left',360),('Right',640)]:mesh('GateFrame'+suffix,(200,y,170),(.5,.25,3.4),body)
    mesh('GateLintel',(200,500,335),(.5,3.05,.2),body)
    for i,(x,y,sx,sy) in enumerate([(950,100,2,1.6),(1450,150,1.5,2),(650,-650,1.6,2)]):mesh('TurretCover'+str(i),(x,y,115),(sx,sy,2.3),body)
    for y in [-620,500]:mesh('RouteMark'+str(y),(-450,y,1),(10,.07,.02),accent,False)
    door=actor(m.asset('BP_Door').generated_class(),'MazeDoor',(200,-700,0));door.set_folder_path('Maze/Puzzles')
    lever=actor(m.asset('BP_Lever').generated_class(),'MazeLever',(-350,-950,0));lever.set_editor_property('ControlledActor',door);lever.set_folder_path('Maze/Puzzles')
    gate=actor(m.asset('BP_LiftingGate').generated_class(),'MazeLiftingGate',(200,500,0));gate.set_folder_path('Maze/Puzzles')
    plate=actor(m.asset('BP_PressurePlate').generated_class(),'MazePressurePlate',(-350,500,0));plate.set_editor_property('ControlledActor',gate);plate.set_folder_path('Maze/Puzzles')
    trophy=actor(m.asset('BP_Trophy').generated_class(),'MazeTrophy',(1350,800,0));trophy.set_folder_path('Maze/Items')
    heal=actor(m.asset('BP_HealPickup').generated_class(),'MazeHeal',(850,900,0));heal.set_folder_path('Maze/Items')
    exit=actor(m.asset('BP_WinZone').generated_class(),'MazeExit',(-900,-700,0));exit.set_folder_path('Maze/World')
    turret=actor(m.asset('BP_MazeTurret').generated_class(),'MazeTurret',(1200,-650,0),unreal.Rotator(yaw=90));turret.set_folder_path('Maze/Enemies')
    actor(unreal.PlayerStart,'MazePlayerStart',(-900,-700,96),unreal.Rotator(yaw=0))
    for n,t,p in [('Exit','EXIT / BRING THE TROPHY',(-1100,-700,260)),('Lever','E: UNLOCK DOOR',(-350,-950,220)),('Door','E: OPEN AFTER LEVER',(190,-620,320)),('Plate','STAND 3s / GATE CLOSES 3s AFTER EXIT',(-350,500,250)),('Gate','TIMED GATE',(190,500,380)),('Trophy','TROPHY / RETURN TO EXIT',(1350,800,245)),('Heal','E: HEAL',(850,900,190)),('Turret','DANGER / USE COVER',(1200,-650,250))]:label('Instruction'+n,t,p,19 if n=='Plate' else 24)
    sun=actor(unreal.DirectionalLight,'MazeSun',(0,0,1200),unreal.Rotator(pitch=-55,yaw=-35));sun.light_component.set_intensity(4);sun.light_component.set_editor_property('atmosphere_sun_light',True)
    actor(unreal.SkyAtmosphere,'MazeAtmosphere',(0,0,0))
    sky=actor(unreal.SkyLight,'MazeSky',(0,0,1200));sky.light_component.set_editor_property('real_time_capture',True);sky.light_component.set_intensity(.8)
    pp=actor(unreal.PostProcessVolume,'MazeExposure',(0,0,0));pp.set_editor_property('unbound',True);settings=pp.get_editor_property('settings')
    for key,value in [('override_auto_exposure_min_brightness',True),('override_auto_exposure_max_brightness',True),('auto_exposure_min_brightness',1),('auto_exposure_max_brightness',1)]:settings.set_editor_property(key,value)
    pp.set_editor_property('settings',settings)
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world();world.get_world_settings().set_editor_property('default_game_mode',m.asset('BP_MazeGameMode').generated_class())
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(unreal.Vector(-1500,-1800,1800),unreal.Rotator(pitch=-32,yaw=35))
    assert levels.save_current_level()
    return {'map':MAP,'puzzles':2,'turrets':1,'trophy':1,'healing_pickups':1}
