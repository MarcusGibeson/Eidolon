import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from canary_self_update import *;from self_change_isolation import *;from v1387_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 r=Path(td);x=create_self_change_workspace(source_root=src(r),runtime_root=r/'rt',candidate_id=CID,self_model_digest=SM,backlog_candidate_digest=BC);d,s=evidence();q=run_canary_self_update(private_workspace=x['private_workspace'],expected_lineage_digest=x['self_change_workspace']['lineage_digest'],dogfood_verification=d,expected_dogfood_digest=d['verification_digest'],shadow_execution=s,expected_shadow_digest=s['shadow_digest'],health_scenarios=['canary/health.py']);v=q['canary_self_update'];req(q['ok'],'checkpoint');N+=1
 req(v['candidate_id']==CID,'candidate');N+=1
 req(v['canary_passed'],'health');N+=1
 req(v['content_free'],'privacy');N+=1
 req(not v['source_replacement_authorized'] and not v['independent_authority_granted'],'authority');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1387-checkpoint'})
