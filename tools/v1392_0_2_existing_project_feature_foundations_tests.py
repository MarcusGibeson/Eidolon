import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from representative_existing_project_feature import *;from v1392_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 p=project(Path(td));q=run_existing_project_feature(project_root=p,request=REQ,operator_authorized=True);req(q['ok'],'feature');N+=1
 x=q['existing_project_feature'];req(x['baseline_tests']['passed'] and x['final_tests']['passed'],'tests');N+=1
 req(x['existing_type_annotation_convention_preserved'],'typing');N+=1
 req(x['existing_normalization_helper_reused'],'reuse');N+=1
 req(x['feature_complete'] and not x['release_authorized'],'complete');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1392-foundations'})
