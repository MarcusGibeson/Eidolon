import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from representative_greenfield_task import *;from v1391_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 req(not run_small_greenfield_task(request='Build a notes app',runtime_root=td,task_id=TID)['ok'],'scope');N+=1
 req(not run_small_greenfield_task(request=REQ,runtime_root=td,task_id='bad')['ok'],'id');N+=1
 q=run_small_greenfield_task(request=REQ,runtime_root=td,task_id=TID);req(q['ok'],'first');N+=1
 req(not run_small_greenfield_task(request=REQ,runtime_root=td,task_id=TID)['ok'],'replay');N+=1
 p=Path(q['greenfield_task']['workspace_path']);req('Cannot divide by zero' in (p/'app.js').read_text(),'zero');N+=1
 req('keydown' in (p/'app.js').read_text(),'keyboard');N+=1
 req(not q['greenfield_task']['independent_authority_granted'],'authority');N+=1
print({'ok':N==7,'passed':N,'total':7,'suite':'v1391-reliability'})
