import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from representative_refactoring_task import *;from v1394_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 p=project(Path(td));q=run_refactoring_task(project_root=p,request=REQ,operator_authorized=True);x=q['refactoring_task'];req(q['ok'],'checkpoint');N+=1
 req(x['behavior_before']['behavior_digest']==x['behavior_after']['behavior_digest'],'parity digest');N+=1
 req(x['service_duplicate_policy_count_after']==0,'ownership');N+=1
 req(x['rollback_boundary_retained'],'rollback');N+=1
 req(not x['release_authorized'] and not x['independent_authority_granted'],'authority');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1394-checkpoint'})
