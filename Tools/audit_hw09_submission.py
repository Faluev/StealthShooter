"""Read-only submission audit for practical 9.6; no project regeneration."""
import unreal,json,re
from pathlib import Path
ROOT='/Game/HW09/'
def audit():
 paths={'base':ROOT+'Characters/BP_DashCharacterBase','character':'/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter','ability':ROOT+'Abilities/GA_Dash','effect':ROOT+'Abilities/GE_Dash','cue':ROOT+'Abilities/Cues/GC_Dash'}
 assets={key:unreal.load_asset(path) for key,path in paths.items()};checks=[];graphs={}
 def check(name,value):
  checks.append({'check':name,'passed':bool(value)})
  if not value:raise AssertionError(name)
 for key,asset in assets.items():
  check(key+' exists',bool(asset));check(key+' compiles',unreal.BlueprintEditorLibrary.compile_blueprint(asset))
  nodes=[];comments=0
  for graph in unreal.BlueprintEditorLibrary.list_graphs(asset):
   e=unreal.BlueprintGraphEditor.get_graph_editor(graph)
   check(key+': '+graph.get_name()+' has no compile errors',not e.list_nodes_with_errors())
   nodes.extend(str(n.get_node_title()) for n in e.list_all_nodes());comments+=len(e.list_comment_nodes())
  graphs[key]={'nodes':nodes,'comments':comments}
 normal=lambda key:re.sub('[^a-z]','',','.join(graphs[key]['nodes']).lower())
 check('Concrete character inherits shared base',unreal.MathLibrary.class_is_child_of(assets['character'].generated_class(),assets['base'].generated_class()))
 check('Input requests ability activation','tryactivateabilitybyclass' in normal('base'))
 check('Base contains no direct dash particle or sound spawning','spawnemitteratlocation' not in normal('base') and 'playsoundatlocation' not in normal('base'))
 check('Ability commits and applies Gameplay Effect','commitability' in normal('ability') and 'applygameplayeffecttoowner' in normal('ability'))
 check('Ability ends after execution','endability' in normal('ability'))
 effect=unreal.get_default_object(assets['effect'].generated_class());ability=unreal.get_default_object(assets['ability'].generated_class());cue=unreal.get_default_object(assets['cue'].generated_class())
 check('Gameplay Effect is instant',effect.get_editor_property('duration_policy')==unreal.GameplayEffectDurationType.INSTANT)
 check('Gameplay Effect references dash Cue',any('GameplayCue.Dash' in x.export_text() for x in effect.get_editor_property('gameplay_cues')))
 check('Gameplay Cue has correct tag','GameplayCue.Dash' in cue.get_editor_property('gameplay_cue_tag').export_text())
 check('Cue owns both particle and sound','spawnemitteratlocation' in normal('cue') and 'playsoundatlocation' in normal('cue'))
 check('No new ability cost or cooldown',not ability.get_editor_property('cost_gameplay_effect_class') and not ability.get_editor_property('cooldown_gameplay_effect_class'))
 check('Blueprints have explanatory comments',sum(g['comments'] for g in graphs.values())>=3)
 result={'checks':checks,'passed':sum(c['passed'] for c in checks),'failed':sum(not c['passed'] for c in checks),'graphs':graphs}
 Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()),'Docs','DashSubmissionAudit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
 return result
