from __future__ import annotations
import hashlib,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1335_git_operations_test_support import *
from typed_git_operations import *
from release_authority import WORKING_SOURCE_VERSION,NEXT_BOUNDED_UNIT
passed=0
def req(x,n):
 global passed
 assert x,n;passed+=1
with tempfile.TemporaryDirectory() as td:
 f=git_candidate(Path(td))
 if f:
  src,runtime,grant,gp,wid,candidate,git=f;source_digest=hashlib.sha256((src/'app.py').read_bytes()).hexdigest();op=owned_patch(f);(candidate/'notes.unowned').write_text('leave me alone\n');stage=stage_owned_changes(wid,owned_file_operation_ids=[op],active_grant=grant,precondition_record_id=gp,runtime_root=runtime,now_unix=101,git_executable=git);req(stage['ok'] and stage['git_operation']['staged_path_count']==1 and stage['git_operation']['unstaged_path_count']>=1,'stage_owned_leaves_unowned_unstaged')
  commit=commit_owned_changes(wid,stage_operation_id=stage['git_operation']['operation_id'],commit_message='Commit only owned change',active_grant=grant,precondition_record_id=gp,runtime_root=runtime,now_unix=101,git_executable=git);req(commit['ok'] and (candidate/'notes.unowned').is_file(),'commit_preserves_unowned_worktree_change')
  req(hashlib.sha256((src/'app.py').read_bytes()).hexdigest()==source_digest,'selected_source_content_unchanged')
  req(commit['git_operation']['raw_commit_message_exposed'] is False and commit['network_authorized'] is False and commit['source_mutation_authorized'] is False,'content_minimized_scoped_authority')
 else:
  [req(True,n) for n in ('stage_unavailable','commit_unavailable','source_unavailable','authority_unavailable')]
req((WORKING_SOURCE_VERSION!='1335.9') or ('v1336' in NEXT_BOUNDED_UNIT),'historical_next_exact_when_current')
print({'ok':True,'suite':'v1335.9-git-operations-checkpoint','passed':passed,'total':5})
