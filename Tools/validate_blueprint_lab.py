"""Check the lesson examples in a running editor play world."""
import json
from pathlib import Path
import unreal


def run():
    worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
    assert worlds, 'Start Play or Simulate before running this check.'
    actors = {a.get_actor_label(): a for a in unreal.GameplayStatics.get_all_actors_of_class(worlds[0], unreal.Actor)}
    checks = []

    def check(name, actual, expected):
        assert actual == expected, f'{name}: {actual!r} != {expected!r}'
        checks.append({'name': name, 'passed': True})

    for group in ['Array', 'Set']:
        control = actors[group + '_ColorControl']
        check(group + ' count', control.get_editor_property('AppliedCount'), 3)
        check(group + ' completed', control.get_editor_property('Completed'), True)
        for index in range(1, 4):
            material = actors[f'{group}_Cube_{index}'].static_mesh_component.get_material(0)
            check(f'{group} cube {index} material', material.get_name(), 'M_Cyan')

    for shape in ['Sphere', 'Cone', 'Cylinder']:
        check('Structure mesh ' + shape, actors['Structure_' + shape].static_mesh_component.static_mesh.get_name(), shape)

    item = actors['StructureExamples']
    check('Set Members cost', item.get_editor_property('FinalCost'), 75)
    check('Set Members keeps name', str(item.get_editor_property('FinalName')), 'Keycard')
    check('Structure completed', item.get_editor_property('Completed'), True)
    check('Set Members keeps description', 'Opens a secure door' in item.get_editor_property('Item').export_text(), True)

    examples = actors['ContainerExamples']
    get = examples.get_editor_property
    check('Array preserves duplicate and order', list(get('IntArray')), [1, 1, 2, 3])
    check('Add Unique duplicate result in UE 5.8', get('UniqueIndex'), -1)
    check('Set difference', set(get('Difference')), {3})
    check('Set intersection', set(get('Intersection')), {1, 2})
    check('Set union', set(get('Union')), {1, 2, 3, 4})
    check('Map visits every key', get('MapCount'), 3)
    check('Map key/value pairs', set(get('MapLines')), {'Number: 1 is one', 'Number: 2 is two', 'Number: 3 is three'})
    check('Break stops at first 2', get('BreakCount'), 3)
    for flag in ['MapCompleted', 'BreakCompleted', 'BreakFound', 'Completed']:
        check(flag, get(flag), True)

    control = actors['Array_ColorControl']
    original_targets = list(control.get_editor_property('TargetCubes'))
    original_numbers = dict(get('Numbers'))
    original_array = list(get('IntArray'))
    try:
        control.set_editor_property('TargetCubes', [])
        control.call_method('ApplyColors')
        check('Empty array count', control.get_editor_property('AppliedCount'), 0)
        check('Empty array completed', control.get_editor_property('Completed'), True)
        control.set_editor_property('TargetCubes', [None, original_targets[0]])
        control.call_method('ApplyColors')
        check('Invalid reference skipped', control.get_editor_property('AppliedCount'), 1)
        examples.set_editor_property('Numbers', {})
        examples.call_method('RunExamples')
        check('Empty map count', get('MapCount'), 0)
        check('Empty map lines', list(get('MapLines')), [])
        check('Empty map completed', get('MapCompleted'), True)
        examples.set_editor_property('IntArray', [1, 3])
        examples.call_method('RunExamples')
        check('No break target visits all', get('BreakCount'), 2)
        check('No break target flag', get('BreakFound'), False)
        check('Normal loop completion', get('BreakCompleted'), True)
    finally:
        control.set_editor_property('TargetCubes', original_targets)
        control.call_method('ApplyColors')
        examples.set_editor_property('Numbers', original_numbers)
        examples.set_editor_property('IntArray', original_array)
        examples.call_method('RunExamples')

    report = {'project': 'StealthShooter', 'engine': unreal.SystemLibrary.get_engine_version(), 'checks': checks, 'passed': len(checks)}
    destination = Path(__file__).resolve().parents[1] / 'Docs/Lessons13-15Validation.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report
