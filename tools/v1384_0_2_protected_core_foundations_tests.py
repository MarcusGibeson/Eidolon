import sys;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from protected_core import *;from v1384_test_support import *
N=0;m=protected_core_map();req(m['category_count']==5,'categories');N+=1
r=classify_self_change_scope(changed_paths=['conscious_agent/release_authority.py','conscious_agent/self_model_map.py']);req(r['ok'],'classify');N+=1
s=r['scope'];req(s['protected_core_touched'] and s['protected_path_count']==1,'hit');N+=1
req(s['required_review_level']=='stronger_review' and not s['automatic_apply_allowed'],'review');N+=1
req(not s['source_mutation_authorized'] and not s['release_authorized'],'authority');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1384-foundations'})
