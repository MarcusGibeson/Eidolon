from tempfile import TemporaryDirectory
from conscious_agent.daily_use_reliability_v2710 import build_daily_use_reliability
from conscious_agent.daily_use_reliability_history_v2711 import append_daily_use_reliability,load_daily_use_reliability_history,build_daily_use_reliability_trend
from conscious_agent.daily_use_reliability_review_v2712 import build_daily_use_reliability_review

def snap(conv='nominal',resp='unknown',mem='no_useful_memory',preserve=True,ctx='current_turn_only',pressure=.3,recovery=.7):
 return {'now':{'pressure':pressure,'recovery_margin':recovery},'conversation_health':{'state':conv},'response_quality':{'state':resp},'memory_retrieval':{'feedback':{'state':mem,'should_preserve_uncertainty':preserve}},'conversation_context':{'state':ctx},'signals':{'state':'nominal'}}
def run():
 c=[]
 def ck(n,v):c.append((n,bool(v)))
 good=build_daily_use_reliability(snap());ck('weak_memory_with_restraint_ok',good['state']=='nominal' and 'memory_uncertainty_restraint_working' in good['strengths'])
 bad=build_daily_use_reliability(snap(conv='degraded',resp='quality_concern',preserve=False,pressure=.9,recovery=.1));ck('cross_system_degraded',bad['state']=='degraded' and bad['concern_count']>=3)
 empty=build_daily_use_reliability({});ck('absence_not_healthy',empty['state']=='insufficient_data')
 ck('no_authority',not bad['authority_granted'] and not bad['automatic_action'])
 with TemporaryDirectory() as td:
  for i,state in enumerate([good,good,bad,bad,bad,bad]):append_daily_use_reliability(state,operation_id=f'o{i}',runtime_root=td)
  rows=load_daily_use_reliability_history(td)['rows'];t=build_daily_use_reliability_trend(rows,window=3);ck('trend_worsening',t['direction']=='worsening')
  r=build_daily_use_reliability_review(bad,t);ck('review_only',r['review_required'] and not r['automatic_repair'] and not r['automatic_trial_start'])
  ck('history_content_free',not load_daily_use_reliability_history(td)['raw_conversation_text_stored'])
 return {'ok':all(v for _,v in c),'checks':c,'passed':sum(v for _,v in c),'total':len(c)}
if __name__=='__main__':
 r=run();print(r);raise SystemExit(0 if r['ok'] else 1)
