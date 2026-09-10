import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from representative_existing_project_feature import *;from v1392_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 p=project(Path(td));q=run_existing_project_feature(project_root=p,request=REQ,operator_authorized=True);x=q['existing_project_feature'];req(q['ok'],'checkpoint');N+=1
 req(x['existing_tests_preserved'],'preserve');N+=1
 req(x['target_before_digest']!=x['target_after_digest'],'change');N+=1
 req(x['rollback_available_from_before_digest'],'rollback');N+=1
 req(not x['release_authorized'] and not x['independent_authority_granted'],'authority');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1392-checkpoint'})
