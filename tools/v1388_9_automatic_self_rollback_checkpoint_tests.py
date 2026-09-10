import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from automatic_self_rollback import *;from v1388_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 r=Path(td);old,cand=trees(r,2);c=canary();q=execute_self_update_with_auto_rollback(installed_root=old,candidate_work_root=cand,runtime_root=r/'rt',transaction_id=TX,canary_self_update=c,expected_canary_digest=c['canary_digest'],health_scenarios=['health/post.py'],operator_authorized=True);v=q['self_update_transaction'];req(not q['ok'],'checkpoint failure');N+=1
 req(v['rollback_performed'] and v['rollback_verified'],'safe');N+=1
 req(v['active_manifest_digest']==v['previous_manifest_digest'],'exact restore');N+=1
 req(v['diagnostic_evidence_retained'],'diagnostics');N+=1
 req(not v['release_authorized'] and not v['independent_authority_granted'],'authority');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1388-checkpoint'})
