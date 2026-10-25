"""Refactor the supplied HW_09 dash without changing its observable behavior."""
import unreal
import lab_graph as g
import maze_graph as m
from build_blueprint_lab import variable, ref, after
from build_switchable_room import component

B = unreal.BlueprintEditorLibrary
ROOT = '/Game/HW09'
BASE = ROOT + '/Characters/BP_DashCharacterBase'
SOURCE = '/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter'


def load(path):
    obj = unreal.load_asset(path)
    assert obj, path
    return obj


def member(e, target, name):
    n = g.get_variable(e, name, load(BASE).generated_class().get_path_name())
    g.wire(target, g.pin(n, 'self'))
    return g.result(n)


def target_call(e, path, target):
    n = g.call(e, path)
    g.wire(target, g.pin(n, 'self'))
    return n


def cast_base(e, obj, entry):
    return m.cast(e, 'BP_DashCharacterBase', obj, entry)


def finish(bp, comment):
    g.compile_bp(bp)
    for gr in B.list_graphs(bp):
        e = unreal.BlueprintGraphEditor.get_graph_editor(gr)
        for c in e.list_comment_nodes():
            e.remove_comment_node(c)
        if e.list_all_nodes() and str(gr.get_name()) != 'UserConstructionScript':
            e.add_comment_to_nodes(comment, e.list_all_nodes())
    g.layout(bp)
    g.compile_bp(bp)


def build_base():
    base = load(BASE)
    e = g.graph(base)
    e.remove_nodes([n for n in e.list_all_nodes() if str(n.get_node_title()) in ['Try Activate Ability by Class', 'Give Ability'] or ('BeginPlay' in str(n.get_node_title()) and n.get_name() != 'K2Node_Event_1')])
    variable(base, 'DashCueCount', m.INT, '0')
    for name, kind, default in [
        ('DashEmitter', B.get_object_reference_type(unreal.ParticleSystem), '/Game/FXVarietyPack/Particles/P_ky_hit1.P_ky_hit1'),
        ('DashSound', B.get_object_reference_type(unreal.SoundBase), '/Engine/VREditor/Sounds/VR_teleport_Cue.VR_teleport_Cue'),
        ('DashEffectScale', m.VECTOR, '(X=0.6,Y=0.6,Z=0.6)'),
        ('DashSoundVolume', m.REAL, '0.5'),
    ]:
        variable(base, name, kind, default, True)
        B.set_blueprint_variable_category(base, name, 'Dash|Presentation')
    B.set_blueprint_variable_category(base, 'DashDistance', 'Dash|Movement')
    B.set_blueprint_variable_category(base, 'DashCueCount', 'Dash|Diagnostics')
    component(base, 'AbilitySystem', unreal.AbilitySystemComponent)
    g.compile_bp(base)
    e = g.graph(base)
    # Remove only the supplied dash chain; movement, look, jump and mapping stay intact.
    original_dash = {'K2Node_CallFunction_8','K2Node_CallFunction_13','K2Node_CallFunction_11',
                     'K2Node_PromotableOperator_0','K2Node_PromotableOperator_1','K2Node_VariableGet_0',
                     'K2Node_CallFunction_12','K2Node_CallFunction_19','K2Node_CallFunction_14',
                     'K2Node_CallFunction_18','K2Node_CallFunction_10'}
    e.remove_nodes([n for n in e.list_all_nodes() if n.get_name() in original_dash])
    dash = next(n for n in e.list_all_nodes() if str(n.get_node_title()) == 'EnhancedInputAction IA_Dash')
    g.pin(dash, 'Started', True).break_pin_links()
    activate = target_call(e, '/Script/GameplayAbilities.AbilitySystemComponent.TryActivateAbilityByClass', ref(e, 'AbilitySystem'))
    g.value(activate, 'InAbilityToActivate', load(ROOT+'/Abilities/GA_Dash').generated_class().get_path_name())
    g.wire(g.pin(dash, 'Started', True), activate.find_execute_pin())
    begin = next(n for n in e.list_all_nodes() if n.get_name() == 'K2Node_Event_1')
    mapping_cast = next(n for n in e.list_all_nodes() if n.get_name() == 'K2Node_DynamicCast_0')
    old = [mapping_cast.find_execute_pin()]
    g.then(begin).break_pin_links()
    give = target_call(e, '/Script/GameplayAbilities.AbilitySystemComponent.K2_GiveAbility', ref(e, 'AbilitySystem'))
    g.value(give, 'AbilityClass', load(ROOT+'/Abilities/GA_Dash').generated_class().get_path_name())
    g.value(give, 'Level', '1'); g.value(give, 'InputID', '-1')
    g.chain(begin, give)
    for dest in old:
        g.wire(g.then(give), dest)
    finish(base, 'Base settings preserve the supplied character, camera and input. BeginPlay grants GA_Dash once. IA_Dash Started requests activation only; all dash behavior belongs to GAS.')


def build_child():
    child = load(SOURCE)
    g.clear_graph(child)
    e = g.graph(child)
    if 'DashDistance' in [str(x) for x in B.list_member_variable_names(child, False)]:
        e.remove_member_variable('DashDistance')
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    handles = sub.k2_gather_subobject_data_for_blueprint(child)
    own = []
    for h in handles:
        obj = lib.get_object(lib.get_data(h))
        if obj and obj.get_name() in ['FollowCamera_GEN_VARIABLE', 'CameraBoom_GEN_VARIABLE']:
            own.append(h)
    if own:
        sub.delete_subobjects(handles[0], list(reversed(own)), child)
    B.reparent_blueprint(child, load(BASE).generated_class())
    finish(child, 'Concrete character used by the original map and GameMode. All common settings and controls are inherited from BP_DashCharacterBase.')


def build_cue():
    bp = load(ROOT+'/Abilities/Cues/GC_Dash')
    B.add_function_override(bp, 'OnExecute')
    e = g.new_function(bp, 'OnExecute')
    entry = next(n for n in e.list_all_nodes() if isinstance(n, unreal.K2Node_FunctionEntry))
    avatar, flow = cast_base(e, g.pin(entry, 'MyTarget', True), g.then(entry))
    loc = g.result(target_call(e, '/Script/Engine.Actor.K2_GetActorLocation', avatar))
    rot = g.result(target_call(e, '/Script/Engine.Actor.K2_GetActorRotation', avatar))
    emit = g.call(e, '/Script/Engine.GameplayStatics.SpawnEmitterAtLocation')
    g.wire(avatar, g.pin(emit, 'WorldContextObject'))
    for name, value in [('EmitterTemplate', member(e, avatar, 'DashEmitter')), ('Location',loc), ('Rotation',rot), ('Scale',member(e,avatar,'DashEffectScale'))]:
        g.wire(value, g.pin(emit, name))
    flow = after(flow, emit)
    sound = g.call(e, '/Script/Engine.GameplayStatics.PlaySoundAtLocation')
    g.wire(avatar,g.pin(sound,'WorldContextObject'))
    g.wire(member(e,avatar,'DashSound'),g.pin(sound,'Sound'))
    g.wire(loc,g.pin(sound,'Location'))
    g.wire(member(e,avatar,'DashSoundVolume'),g.pin(sound,'VolumeMultiplier'))
    g.value(sound,'PitchMultiplier','1')
    flow=after(flow,sound)
    count=g.set_variable(e,'DashCueCount',load(BASE).generated_class().get_path_name())
    g.wire(avatar,g.pin(count,'self'))
    g.wire(m.op(e,'Add_IntInt',member(e,avatar,'DashCueCount'),'1'),g.pin(count,'DashCueCount'))
    flow=after(flow,count)
    ret=next(n for n in e.list_all_nodes() if isinstance(n,unreal.K2Node_FunctionResult))
    g.wire(flow,ret.find_execute_pin());g.value(ret,'ReturnValue','true')
    g.compile_bp(bp)
    tag=unreal.GameplayTag();tag.import_text('(TagName="GameplayCue.Dash")')
    unreal.get_default_object(bp.generated_class()).set_editor_property('gameplay_cue_tag',tag)
    finish(bp,'Executed by the instant GE_Dash at the departure point BEFORE movement. Preserve original emitter scale 0.6 and teleport sound volume 0.5. The static cue stores no mutable instance state.')


def build_effect():
    bp=load(ROOT+'/Abilities/GE_Dash')
    cdo=unreal.get_default_object(bp.generated_class())
    cdo.set_editor_property('duration_policy',unreal.GameplayEffectDurationType.INSTANT)
    tags=unreal.GameplayTagContainer();tags.import_text('(GameplayTags=((TagName="GameplayCue.Dash")))')
    cue=unreal.GameplayEffectCue();cue.import_text('(GameplayCueTags=(GameplayTags=((TagName="GameplayCue.Dash"))))')
    cdo.set_editor_property('gameplay_cues',[cue])
    cdo.set_editor_property('require_modifier_success_to_trigger_cues',False)
    cdo.set_editor_property('suppress_stacking_cues',False)
    g.compile_bp(bp)


def build_ability():
    bp=load(ROOT+'/Abilities/GA_Dash')
    probe=B.find_graph(bp,'ProbeNativeAPI')
    if probe:B.remove_graph(bp,probe)
    e=g.clear_graph(bp)
    ev=g.event(bp,'K2_ActivateAbility')
    commit=g.call(e,'/Script/GameplayAbilities.GameplayAbility.K2_CommitAbility')
    flow=after(g.then(ev),commit)
    branch=m.branch(e,flow,g.result(commit))
    end_fail=g.call(e,'/Script/GameplayAbilities.GameplayAbility.K2_EndAbility')
    g.wire(g.pin(branch,'else',True),end_fail.find_execute_pin())
    actor=g.call(e,'/Script/GameplayAbilities.GameplayAbility.GetAvatarActorFromActorInfo')
    avatar,flow=cast_base(e,g.result(actor),g.pin(branch,'then',True))
    cast=next(n for n in e.list_all_nodes() if isinstance(n,unreal.K2Node_DynamicCast))
    g.wire(g.pin(cast,'CastFailed',True),end_fail.find_execute_pin())
    effect=g.call(e,'/Script/GameplayAbilities.GameplayAbility.BP_ApplyGameplayEffectToOwner')
    g.value(effect,'GameplayEffectClass',load(ROOT+'/Abilities/GE_Dash').generated_class().get_path_name())
    flow=after(flow,effect)
    loc=g.result(target_call(e,'/Script/Engine.Actor.K2_GetActorLocation',avatar))
    forward=g.result(target_call(e,'/Script/Engine.Actor.GetActorForwardVector',avatar))
    offset=m.op(e,'Multiply_VectorFloat',forward,member(e,avatar,'DashDistance'))
    dest=m.op(e,'Add_VectorVector',loc,offset)
    move=target_call(e,'/Script/Engine.Actor.K2_SetActorLocation',avatar)
    g.wire(dest,g.pin(move,'NewLocation'));g.value(move,'bSweep','false');g.value(move,'bTeleport','true')
    flow=after(flow,move)
    end=g.call(e,'/Script/GameplayAbilities.GameplayAbility.K2_EndAbility');after(flow,end)
    g.compile_bp(bp)
    cdo=unreal.get_default_object(bp.generated_class())
    cdo.set_editor_property('instancing_policy',unreal.GameplayAbilityInstancingPolicy.INSTANCED_PER_ACTOR)
    tags=unreal.GameplayTagContainer();tags.import_text('(GameplayTags=((TagName="Ability.Dash")))')
    cdo.set_editor_property('ability_tags',tags)
    finish(bp,'Commit -> GE_Dash / GameplayCue at departure -> instant forward teleport -> EndAbility. Exactly preserve DashDistance=300, no sweep, teleport=true, no cost or cooldown. Every Started press can activate again.')


def run():
    assert unreal.Paths.get_base_filename(unreal.Paths.get_project_file_path()) == 'HW_09_GAS', 'Open HW_09_GAS.uproject; never run this conversion on another project.'
    assert 'DashDistance' in [str(x) for x in B.list_member_variable_names(load(SOURCE), False)], 'The supplied character has already been refactored. This conversion is intentionally one-time.'
    build_base()
    build_child()
    build_cue()
    build_effect()
    build_ability()
    return {'base':BASE,'character':SOURCE,'ability':ROOT+'/Abilities/GA_Dash','effect':ROOT+'/Abilities/GE_Dash','cue':ROOT+'/Abilities/Cues/GC_Dash'}
