import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from automatic_self_rollback import *;from v1388_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 r=Path(td);old,cand=trees(r);c=canary();q=execute_self_update_with_auto_rollback(installed_root=old,candidate_work_root=cand,runtime_root=r/'rt',transaction_id=TX,canary_self_update=c,expected_canary_digest=c['canary_digest'],health_scenarios=['health/post.py'],operator_authorized=True);req(q['ok'],'install');N+=1
 v=q['self_update_transaction'];req(v['health_passed'] and not v['rollback_performed'],'health');N+=1
 req('new' in (old/'app.py').read_text(),'candidate active');N+=1
 req(v['external_installed_tree_only'] and v['diagnostic_evidence_retained'],'bounded');N+=1
 req(not v['release_authorized'] and not v['independent_authority_granted'],'authority');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1388-foundations'})
