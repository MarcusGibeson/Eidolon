from conscious_agent.daily_use_sustained_readiness_v2716 import build_sustained_daily_use_readiness
from conscious_agent.daily_use_failure_mode_review_v2717 import build_daily_use_failure_mode_review
from conscious_agent.daily_use_trial_readiness_packet_v2718 import build_daily_use_trial_readiness_packet

def run():
 c=[]
 def ck(n,v):c.append((n,bool(v)))
 r=build_sustained_daily_use_readiness({'state':'nominal'},continuity_supported=True,background_cognition_supported=True,memory_persistence_supported=True,queue_persistence_supported=True);ck('ready_not_proven',r['engineering_ready'] and not r['real_daily_use_proven'])
 b=build_sustained_daily_use_readiness({'state':'degraded'},continuity_supported=True,background_cognition_supported=True,memory_persistence_supported=True,queue_persistence_supported=True);ck('degraded_blocks',not b['engineering_ready'] and 'current_daily_use_reliability_degraded' in b['blockers'])
 f=build_daily_use_failure_mode_review({'concerns':['weak_memory_without_uncertainty_restraint']},b);ck('failure_mode',f['review_required'] and 'memory_overclaim_risk' in f['failure_modes'])
 p=build_daily_use_trial_readiness_packet(r,build_daily_use_failure_mode_review({'concerns':[]},r));ck('review_not_start',p['eligible_for_operator_trial_review'] and not p['trial_started'] and p['operator_selection_required'])
 ck('no_authority',not r['authority_granted'] and not p['authority_granted'])
 return {'ok':all(v for _,v in c),'checks':c,'passed':sum(v for _,v in c),'total':len(c)}
if __name__=='__main__':
 r=run();print(r);raise SystemExit(0 if r['ok'] else 1)
