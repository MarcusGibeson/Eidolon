from __future__ import annotations
import sys,tempfile,json,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1333_workspace_isolation_test_support import *
from workspace_isolation import *
passed=0
def req(x,n):
 global passed
 assert x,n;passed+=1
with tempfile.TemporaryDirectory() as td:
 base=Path(td);src=make_source(base);runtime=base/'runtime';grant=active_grant();pid=precondition(runtime)
 bad=create_disposable_workspace(source_root=src,source_workspace_digest='c'*64,active_grant=grant,precondition_record_id=pid,runtime_root=runtime,now_unix=101);req(bad['status']=='standing_grant_workspace_mismatch','grant_workspace_mismatch_blocks')
 badpid=precondition(runtime,available=False);bad=create_disposable_workspace(source_root=src,source_workspace_digest=WS,active_grant=grant,precondition_record_id=badpid,runtime_root=runtime,now_unix=101);req(bad['status']=='sealed_satisfied_tool_preconditions_required','unsatisfied_precondition_blocks')
 r=create_disposable_workspace(source_root=src,source_workspace_digest=WS,active_grant=grant,precondition_record_id=pid,runtime_root=runtime,now_unix=101);rid=r['workspace_id'];rec=next((runtime/'development_campaigns'/'phase4_workspace_isolation'/'records').glob(rid+'.json'));data=json.loads(rec.read_text());candidate=Path(data['candidate_private_path']);(candidate/'app.py').write_text('changed\n')
 blocked=cleanup_disposable_workspace(rid,active_grant=grant,runtime_root=runtime,now_unix=101);req(blocked['status']=='workspace_has_unreviewed_changes','retention_preserves_unreviewed_changes')
 cleaned=cleanup_disposable_workspace(rid,active_grant=grant,discard_owned_changes=True,runtime_root=runtime,now_unix=101);req(cleaned['cleaned'] and not candidate.exists(),'explicit_owned_discard_cleans')
 data=json.loads(rec.read_text());data['mode']='git_worktree';rec.write_text(json.dumps(data));req(inspect_workspace_isolation(rid,runtime_root=runtime)['status']=='workspace_isolation_record_missing_or_invalid','tamper_rejected')
print({'ok':True,'suite':'v1333.6-8-workspace-isolation-reliability','passed':passed,'total':5})
