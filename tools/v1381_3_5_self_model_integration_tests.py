import sys;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R),str(R/'conscious_agent'),str(R/'tools')]
from self_model_map import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1381_test_support import *
N=0
r=build_self_model(source_root=R);x=r['self_model'];N+=int(r['ok'])
c=compare_self_model_version(self_model=x,expected_self_model_digest=x['self_model_digest'],current_version=x['working_source_version']);req(c['ok'] and not c['stale'],'current');N+=1
s=compare_self_model_version(self_model=x,expected_self_model_digest=x['self_model_digest'],current_version='9999.0');req(s['stale'] and s['refresh_required'],'stale');N+=1
q=process_ordinary_chat_development_turn('show self model',project_state={'self_model':x});req(q.get('active') and q.get('ok'),'chat');N+=1
req(not q['action_executed'] and not q['source_mutation_authorized'],'read only');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1381-integration'})
