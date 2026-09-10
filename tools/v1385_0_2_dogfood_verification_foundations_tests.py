import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from dogfood_verification import *;from self_change_isolation import *;from protected_core import *;from v1385_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 r=Path(td);x=create_self_change_workspace(source_root=src(r),runtime_root=r/'rt',candidate_id=CID,self_model_digest=SM,backlog_candidate_digest=BC);s=classify_self_change_scope(changed_paths=['app.py'])['scope'];q=run_dogfood_verification(private_workspace=x['private_workspace'],expected_lineage_digest=x['self_change_workspace']['lineage_digest'],protected_scope=s,expected_scope_digest=s['scope_digest'],test_paths=['tools/self_test.py']);req(q['ok'],'run');N+=1
 v=q['dogfood_verification'];req(v['passed']==1 and v['failed']==0,'pass');N+=1
 req(v['same_pipeline_required'] and v['isolated_candidate_only'],'pipeline');N+=1
 req(v['content_free'] and len(v['tests'][0]['output_digest'])==64,'privacy');N+=1
 req(not v['installation_authorized'] and not v['release_authorized'],'authority');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1385-foundations'})
