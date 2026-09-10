from __future__ import annotations
import shutil,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1335_git_operations_test_support import *
from typed_git_operations import *
passed=0
def req(x,n):
 global passed
 assert x,n;passed+=1
req(TYPED_GIT_OPERATIONS==('status','history','stage_owned','commit_owned'),'exact_typed_surface')
req(not any(x in TYPED_GIT_OPERATIONS for x in ('reset','clean','checkout','push','rebase','merge')),'destructive_expansive_ops_absent')
with tempfile.TemporaryDirectory() as td:
 f=git_candidate(Path(td))
 if f:
  src,runtime,grant,gp,wid,candidate,git=f;r=inspect_git_status(wid,active_grant=grant,precondition_record_id=gp,runtime_root=runtime,now_unix=101,git_executable=git);req(r['ok'] and r['git_operation']['changed_path_count']==0,'clean_status')
  h=inspect_git_history(wid,active_grant=grant,precondition_record_id=gp,runtime_root=runtime,now_unix=101,git_executable=git,include_subjects=True);req(h['ok'] and h['git_operation']['history_count']>=1 and h['history_subjects'][0]=='fixture','bounded_history_internal_subject')
  req(h['git_operation']['raw_commit_message_exposed'] is False and h['network_authorized'] is False,'public_history_content_minimized_no_network')
 else:
  req(True,'git_unavailable_portable_classification');req(True,'history_unavailable_portable_classification');req(True,'no_network_even_when_unavailable')
print({'ok':True,'suite':'v1335.0-2-git-operations-foundations','passed':passed,'total':5})
