import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from representative_refactoring_task import *;from v1394_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 p=project(Path(td));q=run_refactoring_task(project_root=p,request=REQ,operator_authorized=True);req(q['ok'],'refactor');N+=1
 x=q['refactoring_task'];req(x['behavioral_parity'],'parity');N+=1
 req(x['duplicate_reduction']>=3 and x['maintenance_benefit_measured'],'benefit');N+=1
 req(x['compatibility_import_preserved'] and x['migration_safe_api_surface'],'compat');N+=1
 req(not x['release_authorized'] and not x['independent_authority_granted'],'authority');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1394-foundations'})
