import sys;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from self_improvement_backlog import *;from v1382_test_support import *
N=0
cats=['failure','performance','operator_friction','architecture_debt','missing_capability_evidence'];r=build_self_improvement_backlog(self_model_digest=SM,observations=[obs(c,c,'s'+str(i)) for i,c in enumerate(cats)]);x=r['self_improvement_backlog'];req(r['ok'],'checkpoint');N+=1
req(set(x['categories_present'])==set(cats),'sources');N+=1
req(x['backlog_only'] and not x['automatic_selection_performed'],'backlog');N+=1
req(x['content_free'] and x['read_only'],'privacy');N+=1
req(not r['work_execution_authorized'] and not r['independent_authority_granted'],'authority');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1382-checkpoint'})
