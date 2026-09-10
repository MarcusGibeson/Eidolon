import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from representative_existing_project_feature import *;from v1392_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 r=Path(td);p=project(r);before=(p/'src/text_utils.py').read_text();req(not run_existing_project_feature(project_root=p,request=REQ,operator_authorized=False)['ok'],'operator');N+=1
 req((p/'src/text_utils.py').read_text()==before,'no mutation');N+=1
 req(not run_existing_project_feature(project_root=p,request='add a database',operator_authorized=True)['ok'],'unsupported');N+=1
 b=project(r/'broken',True);req(not run_existing_project_feature(project_root=b,request=REQ,operator_authorized=True)['ok'],'baseline');N+=1
 req('def slugify' not in (b/'src/text_utils.py').read_text(),'baseline untouched');N+=1
 q=run_existing_project_feature(project_root=p,request=REQ,operator_authorized=True);req(q['ok'],'success');N+=1
 req(not run_existing_project_feature(project_root=p,request=REQ,operator_authorized=True)['ok'],'replay');N+=1
print({'ok':N==7,'passed':N,'total':7,'suite':'v1392-reliability'})
