import sys;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from self_improvement_backlog import *;from v1382_test_support import *
N=0
r=build_self_improvement_backlog(self_model_digest=SM,observations=[obs(),obs('performance','slow','latency',7,80,3),obs('architecture_debt','coupling','mod',6,70,5)]);req(r['ok'],'build');N+=1
x=r['self_improvement_backlog'];req(x['candidate_count']==3,'count');N+=1
req(x['candidates'][0]['priority_score']>=x['candidates'][-1]['priority_score'],'rank');N+=1
req(all(not c['selected_for_execution'] and not c['automatic_execution_allowed'] for c in x['candidates']),'no select');N+=1
req(x['content_free'] and not r['self_change_authorized'],'boundary');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1382-foundations'})
