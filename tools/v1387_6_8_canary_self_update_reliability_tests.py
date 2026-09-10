import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from canary_self_update import *;from self_change_isolation import *;from v1387_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 r=Path(td);x=create_self_change_workspace(source_root=src(r,True),runtime_root=r/'rt',candidate_id=CID,self_model_digest=SM,backlog_candidate_digest=BC);d,s=evidence();base=dict(private_workspace=x['private_workspace'],expected_lineage_digest=x['self_change_workspace']['lineage_digest'],dogfood_verification=d,expected_dogfood_digest=d['verification_digest'],shadow_execution=s,expected_shadow_digest=s['shadow_digest'])
 q=run_canary_self_update(**base,health_scenarios=['canary/health.py']);req(not q['ok'],'health fail');N+=1
 req(not q['canary_self_update']['eligible_for_install_review'],'block');N+=1
 req(not run_canary_self_update(**base,health_scenarios=[])['ok'],'empty');N+=1
 bad=dict(d);bad['failed']=1;req(not run_canary_self_update(**{**base,'dogfood_verification':bad},health_scenarios=['canary/health.py'])['ok'],'tamper dogfood');N+=1
 bads=dict(s);bads['regression_count']=1;req(not run_canary_self_update(**{**base,'shadow_execution':bads},health_scenarios=['canary/health.py'])['ok'],'tamper shadow');N+=1
 d2,s2=evidence('selfc_ffffffffffff');req(not run_canary_self_update(**{**base,'shadow_execution':s2,'expected_shadow_digest':s2['shadow_digest']},health_scenarios=['canary/health.py'])['ok'],'candidate mismatch');N+=1
 req(not run_canary_self_update(**base,health_scenarios=['../x.py'])['ok'],'path');N+=1
print({'ok':N==7,'passed':N,'total':7,'suite':'v1387-reliability'})
