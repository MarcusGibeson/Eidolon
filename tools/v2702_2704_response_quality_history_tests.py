from tempfile import TemporaryDirectory
from conscious_agent.conversation_outcome_attribution_v2700 import build_conversation_outcome_attribution
from conscious_agent.response_quality_evaluation_v2701 import evaluate_response_quality
from conscious_agent.response_quality_history_v2702 import append_response_quality,load_response_quality_history
from conscious_agent.response_quality_trend_v2703 import build_response_quality_trend
from conscious_agent.response_quality_review_v2704 import build_response_quality_review

def run():
 c=[]
 def ck(n,v):c.append((n,bool(v)))
 with TemporaryDirectory() as td:
  u=build_conversation_outcome_attribution();q=evaluate_response_quality(u);append_response_quality(q,u,operation_id='u',runtime_root=td)
  ck('unknown_stored_as_unknown',load_response_quality_history(td)['rows'][-1]['state']=='unknown')
  for i in range(4):
   a=build_conversation_outcome_attribution(explicit_resolution={'explicit':True,'kind':'correction'});qq=evaluate_response_quality(a);append_response_quality(qq,a,operation_id=f'n{i}',runtime_root=td)
  rows=load_response_quality_history(td)['rows'];ck('bounded_structural_history',len(rows)==5 and all('raw_response' not in r for r in rows))
  t=build_response_quality_trend(rows,window=3);ck('trend_structural',t['recent_known_outcomes']>=1 and not t['automatic_policy_change'])
  rv=build_response_quality_review(evaluate_response_quality(build_conversation_outcome_attribution(explicit_resolution={'explicit':True,'kind':'correction'})),t);ck('review_only',rv['review_required'] and not rv['automatic_response_repair'] and not rv['authority_granted'])
  ck('history_no_authority',not load_response_quality_history(td)['authority_granted'])
 return {'ok':all(v for _,v in c),'checks':c,'passed':sum(v for _,v in c),'total':len(c)}
if __name__=='__main__':
 r=run();print(r);raise SystemExit(0 if r['ok'] else 1)
