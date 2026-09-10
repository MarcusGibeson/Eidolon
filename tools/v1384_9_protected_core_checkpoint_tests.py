import sys;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from protected_core import *;from v1384_test_support import *
N=0;m=protected_core_map();req(m['protected_path_count']>=12,'coverage');N+=1
req({x['category'] for x in m['categories']}=={'authority','release','secrets','rollback','evidence_verification'},'domains');N+=1
r=classify_self_change_scope(changed_paths=['conscious_agent/self_model_map.py']);req(r['ok'] and not r['scope']['protected_core_touched'],'ordinary');N+=1
req(r['scope']['required_review_level']=='standard_review','standard');N+=1
req(not r['source_mutation_authorized'] and not r['independent_authority_granted'],'authority');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1384-checkpoint'})
