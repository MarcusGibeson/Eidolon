import sys;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R),str(R/'conscious_agent'),str(R/'tools')]
from self_model_map import *
from v1381_test_support import *
N=0
r=build_self_model(source_root=R);req(r['ok'],'model');N+=1
x=r['self_model'];req(tuple(map(int,x['working_source_version'].split('.'))) >= (1381,9) and x['module_count']>100,'version/modules');N+=1
req(all(c['status']=='evidence_present' for c in x['capabilities']),'evidence');N+=1
req('no_independent_authority' in x['known_limits'] and 'authority' in x['protected_boundary_categories'],'limits');N+=1
req(x['content_free'] and not x['raw_source_content_exposed'] and not r['self_change_authorized'],'privacy/authority');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1381-foundations'})
