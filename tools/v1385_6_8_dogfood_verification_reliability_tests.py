import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from dogfood_verification import *;from self_change_isolation import *;from protected_core import *;from v1385_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 r=Path(td);x=create_self_change_workspace(source_root=src(r,True),runtime_root=r/'rt',candidate_id=CID,self_model_digest=SM,backlog_candidate_digest=BC);s=classify_self_change_scope(changed_paths=['app.py'])['scope'];base=dict(private_workspace=x['private_workspace'],expected_lineage_digest=x['self_change_workspace']['lineage_digest'],protected_scope=s,expected_scope_digest=s['scope_digest'])
 q=run_dogfood_verification(**base,test_paths=['tools/self_test.py']);req(not q['ok'] and q['dogfood_verification']['failed']==1,'failure');N+=1
 req(not q['dogfood_verification']['candidate_installable'],'block installability');N+=1
 req(not run_dogfood_verification(**base,test_paths=[])['ok'],'empty');N+=1
 req(not run_dogfood_verification(**base,test_paths=['../x.py'])['ok'],'traversal');N+=1
 req(not run_dogfood_verification(**base,test_paths=['tools/missing_test.py'])['ok'],'missing');N+=1
 req(not run_dogfood_verification(**{**base,'expected_scope_digest':'0'*64},test_paths=['tools/self_test.py'])['ok'],'scope');N+=1
 req(not run_dogfood_verification(**{**base,'expected_lineage_digest':'0'*64},test_paths=['tools/self_test.py'])['ok'],'lineage');N+=1
print({'ok':N==7,'passed':N,'total':7,'suite':'v1385-reliability'})
