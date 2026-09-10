import sys;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R),str(R/'conscious_agent'),str(R/'tools')]
from self_model_map import *
from v1381_test_support import *
N=0
r=build_self_model(source_root=R);x=r['self_model'];req(r['ok'],'checkpoint');N+=1
req(x['capability_count']>=6 and all(c['evidence_count']>=2 for c in x['capabilities']),'capabilities');N+=1
req(len(x['protected_boundary_categories'])==5,'boundaries');N+=1
req(x['read_only'] and x['content_free'],'read only');N+=1
req(not r['self_change_authorized'] and not r['independent_authority_granted'],'authority');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1381-checkpoint'})
