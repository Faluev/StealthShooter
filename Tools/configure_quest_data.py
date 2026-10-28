"""One-time migration to the lesson 13 DataTable and PrimaryDataAsset; preserves existing authored data."""
import unreal,json
ROOT='/Game/StealthShooter/Quests/Data'

def configure():
    assert not unreal.EditorLevelLibrary.get_pie_worlds(False)
    lib=unreal.EditorAssetLibrary;tools=unreal.AssetToolsHelpers.get_asset_tools()
    table_path=ROOT+'/DT_QuestWeapons';round_path=ROOT+'/DA_QuestRound_Default'
    if lib.does_asset_exist(table_path):table=unreal.load_asset(table_path)
    else:
        factory=unreal.DataTableFactory();factory.set_editor_property('struct',unreal.QuestWeaponRow.static_struct())
        table=tools.create_asset('DT_QuestWeapons',ROOT,unreal.DataTable,factory)
        rows=[{'Name':'Rifle','DisplayName':'Винтовка','Damage':25,'ShotInterval':.35,'Range':6000,'Mesh':'/Game/Weapons/Rifle/Meshes/SM_Rifle.SM_Rifle','Sound':'/Game/StealthShooter/CombatGAS/Audio/S_BotShot.S_BotShot'}]
        assert unreal.DataTableFunctionLibrary.fill_data_table_from_json_string(table,json.dumps(rows,ensure_ascii=False))
        lib.save_loaded_asset(table)
    if lib.does_asset_exist(round_path):definition=unreal.load_asset(round_path)
    else:
        factory=unreal.DataAssetFactory();factory.set_editor_property('data_asset_class',unreal.QuestRoundDefinition)
        definition=tools.create_asset('DA_QuestRound_Default',ROOT,unreal.QuestRoundDefinition,factory)
        assert definition;lib.save_loaded_asset(definition)
    bp=unreal.load_asset('/Game/StealthShooter/Quests/Core/BP_QuestGameMode')
    cdo=unreal.get_default_object(bp.generated_class());cdo.modify()
    cdo.set_editor_property('weapon_definitions',table);cdo.set_editor_property('player_weapon_row','Rifle');cdo.set_editor_property('round_definition',definition)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp);lib.save_loaded_asset(bp)
    # Old Blueprint defaults must inherit the new SetByCaller GE magnitudes.
    for path,parent,field in [('GE_QuestDamage',unreal.QuestDamageEffect,'modifiers'),('GE_QuestShotCooldown',unreal.QuestShotCooldown,'duration_magnitude')]:
        effect=unreal.load_asset('/Game/StealthShooter/Quests/Abilities/Effects/'+path)
        target=unreal.get_default_object(effect.generated_class());target.modify()
        target.set_editor_property(field,unreal.get_default_object(parent).get_editor_property(field))
        unreal.BlueprintEditorLibrary.compile_blueprint(effect);lib.save_loaded_asset(effect)
    return {'table':table.get_path_name(),'rows':[str(x) for x in unreal.DataTableFunctionLibrary.get_data_table_row_names(table)],'round':definition.get_path_name()}
