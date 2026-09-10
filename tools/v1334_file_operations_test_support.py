from __future__ import annotations
import hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1333_workspace_isolation_test_support import WS,make_source,active_grant,precondition
from workspace_isolation import create_disposable_workspace,_record_path
from ordinary_chat_development_campaign import _read_json

def candidate(base:Path, *, configure=None):
    src=make_source(base)
    if configure:configure(src)
    runtime=base/'runtime';grant=active_grant();create_pre=precondition(runtime,'file_patch')
    made=create_disposable_workspace(source_root=src,source_workspace_digest=WS,active_grant=grant,precondition_record_id=create_pre,runtime_root=runtime,now_unix=101)
    assert made['ok'],made
    rec=_read_json(_record_path(made['workspace_id'],runtime));root=Path(rec['candidate_private_path'])
    return src,runtime,grant,made['workspace_id'],root

def sha(path:Path):return hashlib.sha256(path.read_bytes()).hexdigest()
