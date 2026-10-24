import json
from pathlib import Path
import re,unreal
import lab_graph as g
import standardize_project as style
B=unreal.BlueprintEditorLibrary
REPORT=Path(unreal.Paths.project_dir())/'Docs/StyleValidation54.json'

def run():
    checks=[];graphs=[]
    def check(name,condition):
        checks.append({'name':name,'passed':bool(condition)})
        assert condition,name
    registry=unreal.AssetRegistryHelpers.get_asset_registry()
    assets=registry.get_assets_by_path('/Game/StealthShooter',recursive=True)
    check('All 28 project assets retained',len(assets)==28)
    for a in assets:
        path=str(a.package_name);name=str(a.asset_name)
        check('ASCII package identifier: '+name,bool(re.fullmatch(r'[A-Za-z0-9_/]+',path)))
        check('Asset prefix: '+name,name.startswith(('BP_','BPI_','WBP_','M_','S_','L_')))
        check('No redirector: '+name,'ObjectRedirector' not in str(a.asset_class_path))
    for new in style.MOVES.values():check('Moved package exists: '+new,unreal.EditorAssetLibrary.does_asset_exist(new))
    for a in assets:
        asset=a.get_asset()
        if isinstance(asset,unreal.Blueprint):
            check('Compile: '+asset.get_name(),B.compile_blueprint(asset))
            for graph in B.list_graphs(asset):
                e=unreal.BlueprintGraphEditor.get_graph_editor(graph)
                check(asset.get_name()+'.'+str(graph.get_name())+' no errors or warnings',not e.list_nodes_with_errors() and not e.list_nodes_with_warnings())
            g.save(asset)
    for path in style.PATHS:
        bp=unreal.load_asset(path);is_interface=bp.get_name().startswith('BPI_');dispatchers=list(map(str,B.list_event_dispatchers(bp)))
        for name in B.list_member_variable_names(bp,False):
            name=str(name);kind=str(B.pin_type_to_json_schema(B.get_member_variable_type(bp,name),bp.generated_class()))
            boolean='boolean' in kind.lower()
            check(bp.get_name()+'.'+name+' follows naming',bool(re.fullmatch(r'b[A-Z][A-Za-z0-9]*' if boolean else r'[A-Z][A-Za-z0-9]*',name)))
            check(bp.get_name()+'.'+name+' has a category',str(B.get_blueprint_variable_category(bp,name)) not in ['','Default','Lesson Examples','По умолчанию'])
        for graph in B.list_graphs(bp):
            name=str(graph.get_name());e=unreal.BlueprintGraphEditor.get_graph_editor(graph)
            nodes=[n for n in e.list_all_nodes() if not isinstance(n,unreal.EdGraphNode_Comment)]
            if name in ['UserConstructionScript'] or name in dispatchers:continue
            check(bp.get_name()+'.'+name+' has a logical comment',bool(e.list_comment_nodes()))
            if name!='EventGraph' and not is_interface:
                check(bp.get_name()+'.'+name+' at most 30 nodes',len(nodes)<=30)
                check(bp.get_name()+'.'+name+' explicit Return',any(isinstance(n,unreal.K2Node_FunctionResult) for n in nodes))
            graphs.append({'asset':bp.get_name(),'graph':name,'nodes':len(nodes),'comments':len(e.list_comment_nodes())})
    result={'scope':'Interaction module 3.8 and shared 4.4 assets; project content organization','assets':len(assets),'checks':checks,'graphs':graphs,'passed':sum(c['passed'] for c in checks)}
    REPORT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return {'passed':result['passed'],'assets':len(assets)}
