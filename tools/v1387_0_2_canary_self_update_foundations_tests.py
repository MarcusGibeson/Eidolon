import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from canary_self_update import *;from self_change_isolation import *;from v1387_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 r=Path(td);x=create_self_change_workspace(source_root=src(r),runtime_root=r/'rt',candidate_id=CID,self_model_digest=SM,backlog_candidate_digest=BC);d,s=evidence();q=run_canary_self_update(private_workspace=x['private_workspace'],expected_lineage_digest=x['self_change_workspace']['lineage_digest'],dogfood_verification=d,expected_dogfood_digest=d['verification_digest'],shadow_execution=s,expected_shadow_digest=s['shadow_digest'],health_scenarios=['canary/health.py']);req(q['ok'],'run');N+=1
 v=q['canary_self_update'];req(v['passed']==1 and v['canary_passed'],'pass');N+=1
 req(v['eligible_for_install_review'],'review eligibility');N+=1
 req(not v['candidate_was_live_source'],'isolation');N+=1
 req(not v['installation_authorized'] and not v['release_authorized'],'authority');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1387-foundations'})
