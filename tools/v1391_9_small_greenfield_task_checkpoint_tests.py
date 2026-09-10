import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from representative_greenfield_task import *;from v1391_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 q=run_small_greenfield_task(request=REQ,runtime_root=td,task_id=TID);x=q['greenfield_task'];req(q['ok'],'checkpoint');N+=1
 req(x['conversational_request_consumed'],'conversation');N+=1
 req(x['runnable_entrypoint']=='index.html' and x['runnable_result_ready'],'runnable');N+=1
 req(x['content_free_evidence'],'evidence');N+=1
 req(not x['release_authorized'] and not x['independent_authority_granted'],'authority');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1391-checkpoint'})
