from __future__ import annotations
import sys,tempfile,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1333_workspace_isolation_test_support import *
from workspace_isolation import *
from release_authority import WORKING_SOURCE_VERSION,NEXT_BOUNDED_UNIT
passed=0
def req(x,n):
 global passed
 assert x,n;passed+=1
req(ISOLATION_MODES==('filesystem_copy','git_worktree','git_branch_worktree'),'mode_contract')
req(RETENTION_RULES==('discard_on_close','retain_for_review'),'retention_contract')
with tempfile.TemporaryDirectory() as td:
 base=Path(td);src=make_source(base);git=init_git(src);runtime=base/'runtime';grant=active_grant();
 if git:
  pid=precondition(runtime,'git');r=create_disposable_workspace(source_root=src,source_workspace_digest=WS,active_grant=grant,precondition_record_id=pid,mode='git_branch_worktree',runtime_root=runtime,now_unix=101,git_executable=git);req(r['ok'] and r['repository_metadata_modified'] and not r['source_content_modified'],'git_branch_worktree_created')
  cleaned=cleanup_disposable_workspace(r['workspace_id'],active_grant=grant,discard_owned_changes=True,runtime_root=runtime,now_unix=101,git_executable=git);req(cleaned['cleaned'],'git_worktree_and_owned_branch_cleanup')
 else:
  pid=precondition(runtime,'git',available=False);r=create_disposable_workspace(source_root=src,source_workspace_digest=WS,active_grant=grant,precondition_record_id=pid,mode='git_branch_worktree',runtime_root=runtime,now_unix=101);req(not r['ok'],'git_unavailable_is_not_success');req(r['tool_execution_authorized'] is False,'git_unavailable_no_authority')
req((WORKING_SOURCE_VERSION!='1333.9') or ('v1334' in NEXT_BOUNDED_UNIT),'historical_next_exact_when_current')
print({'ok':True,'suite':'v1333.9-workspace-isolation-checkpoint','passed':passed,'total':5})
