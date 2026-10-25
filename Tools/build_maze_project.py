"""Rebuild the committed Maze assets from the editor, keeping older lessons intact.

Use a clean checkout/backup before intentionally regenerating these assets.
The committed BP_ControlActor already implements BPI_Interactable; adding an
interface to a brand-new base class is the one-time editor Class Settings step.
"""
import unreal
import maze_graph as m
import build_maze_character as character
import build_maze_puzzles as puzzles
import build_maze_interface as interface
import build_maze_turret as turret
import build_maze_level as level
from maze_graph import g

def prepare_game_mode():
    bp=m.bp('BP_MazeGameMode',unreal.GameModeBase)
    for name,kind,value in [('bFinished',m.BOOL,'false'),('bWon',m.BOOL,'false'),('RoundDuration',m.REAL,'180'),('RemainingTime',m.REAL,'180'),('RoundStartedAt',m.REAL,'0')]:m.var(bp,name,kind,value,name=='RoundDuration','Configuration' if name=='RoundDuration' else 'State')
    for name in ['Win','Lose','FinishRound','StartRound','UpdateRound','RestartLevel']:
        e=m.function(bp,name)
        if name=='FinishRound':g.input_parameter(e,'bVictory',m.BOOL)
    g.compile_bp(bp)

def build():
    assert not unreal.EditorLevelLibrary.get_pie_worlds(False),'Stop Play before editing assets.'
    assert m.asset('BPI_Interactable') and m.asset('BP_ControlActor'),'Use the committed interface/base class or add BPI_Interactable in Class Settings first.'
    action=m.asset('IA_Interact') or unreal.EditorAssetLibrary.duplicate_asset('/Game/ThirdPerson/Input/Actions/IA_Jump',m.path('IA_Interact'))
    context=m.asset('IMC_Maze') or unreal.EditorAssetLibrary.duplicate_asset('/Game/ThirdPerson/Input/IMC_Default',m.path('IMC_Maze'))
    context.unmap_all();key=unreal.Key();key.import_text('E');context.map_key(action,key);g.save(action);g.save(context)
    for name in ['WBP_MazeHUD','WBP_MazeWin','WBP_MazeLose']:m.bp(name,source='/Game/StealthShooter/Interaction/GroupControl/WBP_GroupSwitch')
    prepare_game_mode();character.prepare();character.health();character.character()
    puzzles.prepare();puzzles.door_and_lever();puzzles.pressure_gate();puzzles.items()
    interface.design();interface.hud();interface.result_widgets();interface.world()
    turret.prepare();turret.graphs()
    return level.build()
