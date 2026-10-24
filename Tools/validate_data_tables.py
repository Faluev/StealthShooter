"""Check Data Table iteration and missing-row fallback in the play world."""
import json
from pathlib import Path
import unreal
from project_paths import load_asset,resolve_reference

def run_lab():
    world=unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
    actor=next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.Actor) if a.get_actor_label()=='DataTableExamples')
    checks=[]
    for label,actual,expected in [('Three row names',actor.get_editor_property('RowCount'),3),('Three typed rows read',actor.get_editor_property('FoundCount'),3),('Iteration completed',actor.get_editor_property('Completed'),True)]:
        assert actual==expected,label
        checks.append({'name':label,'passed':True})
    table=load_asset('/Game/Blueprints/DT_TrafficSettings')
    assert {str(n) for n in unreal.DataTableFunctionLibrary.get_data_table_row_names(table)}=={'Default','LowBrightness','HighVisibility'}
    checks.append({'name':'Expected named profiles exist','passed':True})
    report={'checks':checks,'passed':len(checks)}
    (Path(__file__).resolve().parents[1]/'Docs/DataTableValidation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report

def run_manager():
    world=unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
    manager=next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.Actor) if a.get_class().get_name()=='BP_TrafficLightsManager_C')
    original=manager.get_editor_property('SettingsRow')
    before=manager.get_editor_property('ColorSettings').export_text()
    checks=[]
    try:
        missing=unreal.DataTableRowHandle(data_table=original.data_table,row_name='MissingValidationRow')
        manager.set_editor_property('SettingsRow',missing,notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
        manager.call_method('LoadSettings')
        assert not manager.get_editor_property('LoadedSettings')
        checks.append({'name':'Missing row is reported as not found','passed':True})
        assert manager.get_editor_property('ColorSettings').export_text()==before
        checks.append({'name':'Missing row retains ColorSettings','passed':True})
    finally:
        manager.set_editor_property('SettingsRow',original,notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
        manager.call_method('LoadSettings')
    path=Path(__file__).resolve().parents[1]/'Docs/DataTableValidation.json'
    report=json.loads(path.read_text(encoding='utf-8'))
    report['checks'].extend(checks);report['passed']=len(report['checks'])
    path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report
