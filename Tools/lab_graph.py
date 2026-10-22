"""Shared helpers for the advanced Blueprint lesson assets."""
import unreal
ROOT="/Game/StealthShooter"
BP_ROOT=ROOT+"/Blueprints"
MAP_ROOT=ROOT+"/Maps"
B=unreal.BlueprintEditorLibrary
E=unreal.BlueprintGraphEditor
ASSETS=[]

def fail(message):
    raise RuntimeError(message)


def save(asset):
    if not unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False):
        fail('Could not save ' + asset.get_path_name())


def compile_bp(bp):
    if not B.compile_blueprint(bp):
        fail('Compilation failed: ' + bp.get_path_name())
    errors = []
    for graph in B.list_graphs(bp):
        editor = E.get_graph_editor(graph)
        errors.extend(str(n.get_node_title()) for n in editor.list_nodes_with_errors())
    if errors:
        fail(bp.get_path_name() + ': ' + '; '.join(errors))
    save(bp)
    if bp not in ASSETS:
        ASSETS.append(bp)


def blueprint(name, parent):
    path = BP_ROOT + '/' + name
    bp = unreal.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else None
    if bp is None:
        bp = B.create_blueprint_asset_with_parent(path, parent)
    if not bp:
        fail('Could not create ' + path)
    return bp


def graph(bp):
    editor = E.get_graph_editor_by_name(bp, 'EventGraph')
    if not editor:
        fail('Missing event graph: ' + bp.get_path_name())
    return editor


def clear_graph(bp):
    editor = graph(bp)
    editor.remove_nodes(editor.list_all_nodes())
    return editor


def pin(node, name, output=False):
    p = node.find_output_pin(name) if output else node.find_input_pin(name)
    if not p.is_valid():
        available = [str(x.get_pin_name()) for x in node.list_all_pins()]
        fail(f'{node.get_node_title()}: missing {name}; pins={available}')
    return p


def wire(source, target):
    if not source.is_valid() or not target.is_valid() or not source.try_create_connection(target):
        fail('Pin connection failed: ' + str(source) + ' -> ' + str(target))


def value(node, name, text):
    if not pin(node, name).set_pin_value(str(text)):
        fail(f'Cannot set {node.get_node_title()}.{name}={text}')


def result(node):
    p = node.find_result_pin()
    if p.is_valid():
        return p
    data = [p for p in node.list_output_pins() if 'exec' not in str(p.get_pin_type_as_json_schema()).lower()]
    if len(data) == 1:
        return data[0]
    return pin(node, 'ReturnValue', True)


def then(node):
    p = node.find_then_pin()
    if not p.is_valid():
        fail('Missing then pin: ' + str(node.get_node_title()))
    return p


def chain(source_node, target_node):
    wire(then(source_node), target_node.find_execute_pin())


def call(g, path):
    node = g.add_call_function_node(path)
    if node is None:
        fail('Function not available: ' + path)
    return node


def named_node(g, predicate, label):
    names = [str(x) for x in g.list_available_nodes([])]
    matches = [x for x in names if predicate(x.replace(' ', '').lower())]
    if len(matches) != 1:
        fail(f'{label}: expected one matching node, got {matches}; related={[n for n in names if "pressed" in n.lower()][-15:]}')
    node = g.create_node_from_name(matches[0], unreal.Vector2D(0, 0), [], None)
    if not node:
        fail('Could not create ' + matches[0])
    return node


def event(bp, name):
    node = B.add_event_override(bp, name, unreal.IntPoint(0, 0))
    if not node:
        fail('Could not override ' + name)
    return node


def get_variable(g, name, class_path=''):
    node = g.add_get_member_variable_node(name, class_path)
    if not node:
        fail('Could not get variable ' + name)
    return node


def set_variable(g, name, class_path=''):
    node = g.add_set_member_variable_node(name, class_path)
    if not node:
        fail('Could not set variable ' + name)
    return node


def new_function(bp, name):
    existing = B.find_graph(bp,name)
    if existing:
        editor=E.get_graph_editor(existing)
        editor.remove_nodes([n for n in editor.list_all_nodes() if not isinstance(n,(unreal.K2Node_FunctionEntry,unreal.K2Node_FunctionResult))])
        return editor
    g = E.create_and_edit_function_graph(bp, name)
    if not g:
        fail('Could not create function ' + name)
    return g


def output_parameter(editor,name,pin_type):
    for node in editor.list_all_nodes():
        if isinstance(node,unreal.K2Node_FunctionResult) and node.find_input_pin(name).is_valid():
            return node
    return editor.add_graph_output_parameter(name,pin_type)


def input_parameter(editor,name,pin_type):
    for node in editor.list_all_nodes():
        if isinstance(node,unreal.K2Node_FunctionEntry):
            p=node.find_output_pin(name)
            if p.is_valid():
                return p
    return editor.add_graph_input_parameter(name,pin_type)


def layout(bp):
    from editor_toolset.toolsets.blueprint import BlueprintTools
    for gr in B.list_graphs(bp):
        nodes = E.get_graph_editor(gr).list_all_nodes()
        if len(nodes) > 1:
            BlueprintTools.arrange_nodes(nodes)
