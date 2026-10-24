"""Resolve historical lesson package names after the module 5 reorganization."""
import json
from pathlib import Path
import unreal
MOVES=json.loads((Path(__file__).resolve().parents[1]/'Docs/AssetPathChanges54.json').read_text(encoding='utf-8'))

def resolve_reference(reference):
    value=str(reference)
    for old,new in sorted(MOVES.items(),key=lambda item:len(item[0]),reverse=True):
        if value==old:return new
        if value.startswith(old+'.'):
            suffix=value[len(old)+1:]
            old_name=old.rsplit('/',1)[1];new_name=new.rsplit('/',1)[1]
            if suffix.startswith(old_name):suffix=new_name+suffix[len(old_name):]
            return new+'.'+suffix
    return value

def load_asset(path):return unreal.load_asset(resolve_reference(path))
