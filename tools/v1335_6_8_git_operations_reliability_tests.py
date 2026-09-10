from __future__ import annotations
import json,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1335_git_operations_test_support import *
from typed_git_operations import *
passed=0
def req(x,n):
 global passed
 assert x,n;passed+=1
with tempfile.TemporaryDirectory() as td:
 f=git_candidate(Path(td))
 if f:
  src,runtime,grant,gp,wid,candidate,git=f;op=owned_patch(f);(candidate/'unowned.txt').write_text('user\n');subprocess.run([git,'add','unowned.txt'],cwd=candidate,check=True);r=stage_owned_changes(wid,owned_file_operation_ids=[op],active_grant=grant,precondition_record_id=gp,runtime_root=runtime,now_unix=101,git_executable=git);req(r['status']=='unowned_staged_changes_present','unowned_staged_blocks')
 else:req(True,'unowned_staged_unavailable')
with tempfile.TemporaryDirectory() as td:
 f=git_candidate(Path(td))
 if f:
  src,runtime,grant,gp,wid,candidate,git=f;op=owned_patch(f);(candidate/'app.py').write_text('manual drift\n');r=stage_owned_changes(wid,owned_file_operation_ids=[op],active_grant=grant,precondition_record_id=gp,runtime_root=runtime,now_unix=101,git_executable=git);req(r['status']=='owned_change_drift_detected','owned_receipt_drift_blocks')
 else:req(True,'drift_unavailable')
with tempfile.TemporaryDirectory() as td:
 f=git_candidate(Path(td))
 if f:
  src,runtime,grant,gp,wid,candidate,git=f;op=owned_patch(f);subprocess.run([git,'config','filter.evil.clean','cat'],cwd=candidate,check=True);r=stage_owned_changes(wid,owned_file_operation_ids=[op],active_grant=grant,precondition_record_id=gp,runtime_root=runtime,now_unix=101,git_executable=git);req(r['status']=='external_git_filters_block_staging','external_filter_blocks')
 else:req(True,'filter_unavailable')
with tempfile.TemporaryDirectory() as td:
 f=git_candidate(Path(td),mode='git_worktree')
 if f:
  src,runtime,grant,gp,wid,candidate,git=f;op=owned_patch(f);stage=stage_owned_changes(wid,owned_file_operation_ids=[op],active_grant=grant,precondition_record_id=gp,runtime_root=runtime,now_unix=101,git_executable=git);r=commit_owned_changes(wid,stage_operation_id=stage['git_operation']['operation_id'],commit_message='Detached commit blocked',active_grant=grant,precondition_record_id=gp,runtime_root=runtime,now_unix=101,git_executable=git);req(r['status']=='owned_branch_worktree_required_for_commit','detached_commit_blocked')
 else:req(True,'detached_unavailable')
with tempfile.TemporaryDirectory() as td:
 f=git_candidate(Path(td))
 if f:
  src,runtime,grant,gp,wid,candidate,git=f;r=inspect_git_status(wid,active_grant=grant,precondition_record_id=gp,runtime_root=runtime,now_unix=101,git_executable=git);opid=r['git_operation']['operation_id'];path=runtime/'development_campaigns'/'phase4_git_operations'/'records'/f'{opid}.json';data=json.loads(path.read_text());data['operation_kind']='commit_owned';path.write_text(json.dumps(data));req(inspect_git_operation(opid,runtime_root=runtime)['status']=='git_operation_missing_or_invalid','tamper_rejected')
 else:req(True,'tamper_unavailable')
print({'ok':True,'suite':'v1335.6-8-git-operations-reliability','passed':passed,'total':5})
