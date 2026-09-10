from tempfile import TemporaryDirectory
from conscious_agent.combined_trial_campaign_catalog_v2720 import build_combined_trial_catalog
from conscious_agent.combined_trial_campaign_plan_v2721 import build_combined_trial_plan
from conscious_agent.combined_trial_stop_rollback_v2723 import build_trial_stop_rollback_matrix
from conscious_agent.combined_trial_campaign_readiness_v2724 import build_combined_trial_campaign_readiness
from conscious_agent.combined_trial_campaign_state_v2725 import prepare_combined_trial_campaign_state,load_combined_trial_campaign_state
from conscious_agent.combined_trial_campaign_runbook_v2726 import build_combined_trial_runbook
from conscious_agent.combined_trial_campaign_observability_v2727 import build_combined_trial_campaign_observability

def run():
 c=[]
 def ck(n,v):c.append((n,bool(v)))
 cat=build_combined_trial_catalog();plan=build_combined_trial_plan(cat);ready=build_combined_trial_campaign_readiness(cat,plan,current_checkpoint='v2729.9',release_certified=True,daily_use_engineering_ready=True);ck('ready',ready['ready_for_operator_campaign_review'] and not ready['campaign_started'])
 bad=build_combined_trial_campaign_readiness(cat,plan,current_checkpoint='v2729.9',release_certified=False);ck('release_blocks',not bad['ready_for_operator_campaign_review'])
 book=build_combined_trial_runbook(cat,plan,build_trial_stop_rollback_matrix(cat));ck('runbook_operator_bound',all(not s['automatic_start_permitted'] and not s['automatic_next_step_permitted'] for s in book['steps']))
 with TemporaryDirectory() as td:
  prepare_combined_trial_campaign_state(cat,plan,ready,runtime_root=td);state=load_combined_trial_campaign_state(td);obs=build_combined_trial_campaign_observability(td);ck('restart_safe_prepared',state['present'] and obs['not_started_count']==8 and not obs['campaign_started'])
 ck('no_authority',not ready['authority_granted'] and not book['authority_granted'])
 return {'ok':all(v for _,v in c),'checks':c,'passed':sum(v for _,v in c),'total':len(c)}
if __name__=='__main__':
 r=run();print(r);raise SystemExit(0 if r['ok'] else 1)
