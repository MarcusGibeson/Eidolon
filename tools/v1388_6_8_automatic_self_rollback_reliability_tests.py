import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from automatic_self_rollback import *;from v1388_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 r=Path(td);old,cand=trees(r);c=canary();base=dict(installed_root=old,candidate_work_root=cand,runtime_root=r/'rt',transaction_id=TX,canary_self_update=c,expected_canary_digest=c['canary_digest'],health_scenarios=['health/post.py'])
 req(not execute_self_update_with_auto_rollback(**base,operator_authorized=False)['ok'],'operator');N+=1
 bad=dict(c);bad['canary_passed']=False;req(not execute_self_update_with_auto_rollback(**{**base,'canary_self_update':bad},operator_authorized=True)['ok'],'canary tamper');N+=1
 req(not execute_self_update_with_auto_rollback(**{**base,'transaction_id':'bad'},operator_authorized=True)['ok'],'tx');N+=1
 req(not execute_self_update_with_auto_rollback(**{**base,'health_scenarios':['../x.py']},operator_authorized=True)['ok'],'path');N+=1
 q=execute_self_update_with_auto_rollback(**base,operator_authorized=True);req(q['ok'],'once');N+=1
 req(not execute_self_update_with_auto_rollback(**base,operator_authorized=True)['ok'],'replay');N+=1
 req(q['self_update_transaction']['previous_manifest_digest']!=q['self_update_transaction']['candidate_manifest_digest'],'distinct');N+=1
print({'ok':N==7,'passed':N,'total':7,'suite':'v1388-reliability'})
