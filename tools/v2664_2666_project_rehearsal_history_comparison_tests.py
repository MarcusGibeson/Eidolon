import json,tempfile
from conscious_agent.developer_project_rehearsal_history_v2660 import build_rehearsal_history
from conscious_agent.developer_project_rehearsal_persistence_v2664 import persist_rehearsal_history,load_rehearsal_history
from conscious_agent.developer_project_rehearsal_comparison_v2665 import compare_project_rehearsals
from conscious_agent.developer_project_rehearsal_drift_v2666 import build_rehearsal_drift_review
checks=[]
h=build_rehearsal_history([{'project_id':'p','project_digest':'a'*64,'state':'attention','scenario_count':3,'failure_modes':['x','y']},{'project_id':'p','project_digest':'b'*64,'state':'nominal','scenario_count':2,'failure_modes':[]}])
with tempfile.TemporaryDirectory() as td:
 p=persist_rehearsal_history(h,td);l=load_rehearsal_history(td);checks += [p['ok'],p['runtime_only'],not p['real_outcome_history_modified'],l['count']==2]
c=compare_project_rehearsals(l,'p');checks += [c['ok'],c['rehearsal_count']==2,c['trend']=='improving',not c['real_project_outcome_inferred']]
d=build_rehearsal_drift_review(c);checks += [d['ok'],not d['operator_review_required'],not d['queue_mutated'],not d['authority_granted']]
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks)}));raise SystemExit(0 if all(checks) else 1)
