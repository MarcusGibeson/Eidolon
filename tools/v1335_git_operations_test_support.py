from __future__ import annotations
import hashlib,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1333_workspace_isolation_test_support import WS,make_source,active_grant,precondition,init_git
from workspace_isolation import create_disposable_workspace,_record_path
from ordinary_chat_development_campaign import _read_json
from structured_file_operations import patch_candidate_file

def git_candidate(base:Path, *, mode='git_branch_worktree'):
    src=make_source(base);git=init_git(src)
    if not git:return None
    runtime=base/'runtime';grant=active_grant(commands=('git_worktree','git'));gitpre=precondition(runtime,'git')
    made=create_disposable_workspace(source_root=src,source_workspace_digest=WS,active_grant=grant,precondition_record_id=gitpre,mode=mode,runtime_root=runtime,now_unix=101,git_executable=git)
    assert made['ok'],made
    rec=_read_json(_record_path(made['workspace_id'],runtime));candidate=Path(rec['candidate_private_path'])
    return src,runtime,grant,gitpre,made['workspace_id'],candidate,git

def owned_patch(fixture, *, old='hello',new='owned'):
    src,runtime,grant,gitpre,wid,candidate,git=fixture
    writepre=precondition(runtime,'file_patch');path=candidate/'app.py';before=hashlib.sha256(path.read_bytes()).hexdigest()
    result=patch_candidate_file(wid,'app.py',expected_content_digest=before,patches=[{'type':'replace_text','old':old,'new':new}],active_grant=grant,precondition_record_id=writepre,runtime_root=runtime,now_unix=101)
    assert result['ok'],result
    return result['file_operation']['operation_id']
