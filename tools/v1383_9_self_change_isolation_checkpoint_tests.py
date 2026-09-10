import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from self_change_isolation import *;from v1383_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 r=Path(td);s=source(r);x=create_self_change_workspace(source_root=s,runtime_root=r/'rt',candidate_id=CID,self_model_digest=SM,backlog_candidate_digest=BC);req(x['ok'],'checkpoint');N+=1
 p=x['self_change_workspace'];req(p['isolated'] and p['content_free'],'isolated');N+=1
 req(p['sealed_input_manifest_digest']==p['source_manifest_digest'],'sealed');N+=1
 req(p['work_is_only_candidate_mutation_target'] and not p['input_is_mutation_target'],'topology');N+=1
 req(not p['installation_authorized'] and not p['independent_authority_granted'],'authority');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1383-checkpoint'})
