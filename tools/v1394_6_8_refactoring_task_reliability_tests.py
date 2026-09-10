import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from representative_refactoring_task import *;from v1394_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 r=Path(td);p=project(r);before=(p/'src/profile_service.py').read_text();req(not run_refactoring_task(project_root=p,request=REQ,operator_authorized=False)['ok'],'operator');N+=1
 req((p/'src/profile_service.py').read_text()==before,'no mutation');N+=1
 req(not run_refactoring_task(project_root=p,request='add a feature',operator_authorized=True)['ok'],'unsupported');N+=1
 clean=project(r/'clean',False);req(not run_refactoring_task(project_root=clean,request=REQ,operator_authorized=True)['ok'],'no smell');N+=1
 broken=project(r/'broken',True,True);req(not run_refactoring_task(project_root=broken,request=REQ,operator_authorized=True)['ok'],'baseline');N+=1
 req(not (broken/'src/text_policy.py').exists(),'baseline no new');N+=1
 q=run_refactoring_task(project_root=p,request=REQ,operator_authorized=True);req(q['ok'],'success');N+=1
print({'ok':N==7,'passed':N,'total':7,'suite':'v1394-reliability'})
