from __future__ import annotations
import hashlib,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1333_workspace_isolation_test_support import WS,make_source,active_grant,precondition
from workspace_isolation import create_disposable_workspace,_record_path
from ordinary_chat_development_campaign import _read_json

def process_candidate(base:Path):
    src=make_source(base);runtime=base/'runtime';grant=active_grant(commands=('shell',));isopre=precondition(runtime,'file_patch')
    made=create_disposable_workspace(source_root=src,source_workspace_digest=WS,active_grant=grant,precondition_record_id=isopre,mode='filesystem_copy',runtime_root=runtime,now_unix=101)
    assert made['ok'],made
    rec=_read_json(_record_path(made['workspace_id'],runtime));candidate=Path(rec['candidate_private_path']);shellpre=precondition(runtime,'shell')
    return src,runtime,grant,made['workspace_id'],candidate,shellpre

def wait_terminal(operation_id:str,runtime:Path,timeout=8.0):
    from typed_process_operations import monitor_candidate_process
    deadline=time.monotonic()+timeout;last={}
    while time.monotonic()<deadline:
        last=monitor_candidate_process(operation_id,runtime_root=runtime,include_log_tail=True)
        if (last.get('process_operation') or {}).get('process_state') in {'completed','failed','cancelled','interrupted','uncertain'}:
            return last
        time.sleep(.05)
    return last
