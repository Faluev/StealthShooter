"""Restore the optional Fab presentation from locally licensed source packages.

Source packages stay local; only the scene recipe is published.
"""
from pathlib import Path
import shutil
import unreal

SOURCE=Path('C:/Users/Aluev/Unreal-Engine/DodgeStone/Content')
PREFIX='/Game/Abandoned_Cathedral/Assets/'
SEEDS=['/Game/Rock_Collection_04/Meshes/Rock_%02d/StaticMeshes/SM_Rock_%02d'%(i,i) for i in [1,2,3,4]]
SEEDS += [PREFIX+'floor_1/Static_Mesh/SM_floor_'+str(i) for i in [1,2,3]]
SEEDS += [PREFIX+'arch_1-2/Static_Mesh/'+n for n in ['SM_arch_1_','SM_arch_2_','SM_arch_pillar_1']]
SEEDS += [PREFIX+'Wall_1/Static_Mesh/SM_wall_1',PREFIX+'debris/Static_Mesh/SM_brick_1']

def restore(source=SOURCE):
    source=Path(source).resolve();target=Path(unreal.Paths.project_content_dir()).resolve()
    registry=unreal.AssetRegistryHelpers.get_asset_registry();options=unreal.AssetRegistryDependencyOptions()
    options.set_editor_property('include_hard_package_references',True);options.set_editor_property('include_soft_package_references',False)
    pending=list(SEEDS);visited=set();copied=[];missing=[]
    while pending:
        package=pending.pop()
        if package in visited or not package.startswith(('/Game/Abandoned_Cathedral/','/Game/Rock_Collection_04/')):continue
        visited.add(package);relative=package.removeprefix('/Game/')+'.uasset';src=(source/relative).resolve();dst=(target/relative).resolve()
        assert src.is_relative_to(source) and dst.is_relative_to(target)
        if not dst.exists():
            if not src.exists():missing.append(package);continue
            dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);copied.append(relative)
        registry.scan_files_synchronous([str(dst)],True)
        pending.extend(str(x) for x in registry.get_dependencies(package,options))
    assert not missing,missing
    return {'packages_required':len(visited),'copied':copied,'missing':missing}
