import tempfile
from conscious_agent.conversation_health_history_v2697 import append_conversation_health,load_conversation_health_history
from conscious_agent.conversation_health_trend_v2698 import build_conversation_health_trend
checks=[]
def ck(x):checks.append(bool(x))
with tempfile.TemporaryDirectory() as td:
 for i,state in enumerate(['degraded','degraded','attention','attention','nominal','nominal','nominal','nominal']):append_conversation_health({'state':state,'concern_count':2 if state=='degraded' else 1 if state=='attention' else 0,'concerns':[],'health_digest':str(i)*64},operation_id=f'op{i}',runtime_root=td)
 h=load_conversation_health_history(td);ck(len(h['rows'])==8);ck(not h['raw_conversation_text_stored']);t=build_conversation_health_trend(h['rows'],window=4);ck(t['direction']=='improving');ck(t['recent_score']<t['prior_score']);ck(not t['automatic_policy_change']);ck(not t['authority_granted'])
print({'ok':all(checks),'passed':sum(checks),'total':len(checks)});raise SystemExit(0 if all(checks) else 1)
