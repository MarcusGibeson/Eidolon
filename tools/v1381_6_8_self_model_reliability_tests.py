import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R),str(R/'conscious_agent'),str(R/'tools')]
from self_model_map import *
from v1381_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 req(not build_self_model(source_root=td)['ok'],'missing');N+=1
r=build_self_model(source_root=R);x=r['self_model'];req(r['ok'],'valid');N+=1
t=dict(x);t['working_source_version']='bad';req(not compare_self_model_version(self_model=t,expected_self_model_digest=x['self_model_digest'],current_version='1381.9')['ok'],'tamper');N+=1
req(not compare_self_model_version(self_model=x,expected_self_model_digest='a'*64,current_version='1381.9')['ok'],'digest');N+=1
r2=build_self_model(source_root=R,extra_capability_evidence={'missing_cap':['does/not/exist.py']});m=next(c for c in r2['self_model']['capabilities'] if c['capability']=='missing_cap');req(m['status']=='evidence_incomplete','missing evidence');N+=1
req(x['claims_require_evidence'] and x['missing_evidence_does_not_imply_capability'],'epistemic');N+=1
req(not r['release_authorized'] and not r['independent_authority_granted'],'authority');N+=1
print({'ok':N==7,'passed':N,'total':7,'suite':'v1381-reliability'})
