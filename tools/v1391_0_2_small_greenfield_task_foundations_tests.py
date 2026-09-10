import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from representative_greenfield_task import *;from v1391_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 q=run_small_greenfield_task(request=REQ,runtime_root=td,task_id=TID);req(q['ok'],'build');N+=1
 x=q['greenfield_task'];req(x['file_count']==5,'files');N+=1
 req(x['node_test_exit_code']==0,'tests');N+=1
 req(all(x['structural_checks'].values()),'accessibility responsive');N+=1
 req(x['runnable_result_ready'] and not x['release_authorized'],'result');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1391-foundations'})
