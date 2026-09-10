import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from self_change_isolation import *;from v1383_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 r=Path(td);s=source(r);x=create_self_change_workspace(source_root=s,runtime_root=r/'rt',candidate_id=CID,self_model_digest=SM,backlog_candidate_digest=BC);req(x['ok'],'create');N+=1
 w=x['private_workspace'];req(Path(w['input_root']).is_dir() and Path(w['work_root']).is_dir(),'trees');N+=1
 req(x['self_change_workspace']['source_manifest_digest']==x['self_change_workspace']['initial_work_manifest_digest'],'identity');N+=1
 req(not x['self_change_workspace']['active_source_is_mutation_target'] and x['self_change_workspace']['work_is_only_candidate_mutation_target'],'target');N+=1
 req(not x['source_mutation_authorized'] and not x['release_authorized'],'authority');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1383-foundations'})
