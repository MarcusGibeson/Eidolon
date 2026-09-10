from pathlib import Path
import json,tempfile,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from conscious_agent.workload_budget_eligibility import WorkloadBudgetEligibilityStore
from conscious_agent.continuity_soak_eligibility import ContinuitySoakEligibilityStore,SOAK_SCENARIOS
from conscious_agent.continuity_soak_campaign_candidates import ContinuitySoakCampaignCandidateStore
from conscious_agent.continuity_soak_live_execution import ContinuitySoakLiveExecutionStore
from conscious_agent.continuity_soak_recovery_receipts import ContinuitySoakRecoveryReceiptStore
p=0
def ok(v):
 global p
 if not v: raise AssertionError(p+1)
 p+=1
with tempfile.TemporaryDirectory() as td:
 r=Path(td);w=WorkloadBudgetEligibilityStore(r);ids=[w.register('w'+k,workload_id='w'+k,workload_kind=k,owner_id='o'+k,cpu_budget_ms=100,memory_budget_mb=128,latency_budget_ms=500,token_budget=256)['eligibility_id'] for k in ('cognition','conversation','inquiry','development')];e=ContinuitySoakEligibilityStore(r).register('e',soak_scope_id='scope',baseline_checkpoint_digest='a'*64,runtime_profile_digest='b'*64,provider_profile_digest='c'*64,workload_eligibility_ids=ids,scenario_ids=sorted(SOAK_SCENARIOS),duration_days=3,observation_interval_minutes=30);c=ContinuitySoakCampaignCandidateStore(r).register('c',eligibility_id=e['eligibility_id'],campaign_action='prepare',campaign_group_id='g',observation_profile_id='o',recovery_profile_id='r',scenario_sequence=sorted(SOAK_SCENARIOS),planned_sleep_cycles=2,planned_restart_count=2,planned_interruption_count=2,planned_provider_outage_count=2,max_provider_outage_minutes=30,stale_work_threshold_minutes=60);x=ContinuitySoakLiveExecutionStore(r).register('x',campaign_id=c['campaign_id'],operator_confirmation_id='confirm',launch_token_id='token');s=ContinuitySoakRecoveryReceiptStore(r);a=s.register('a',execution_id=x['execution_id'],scenario_id='provider_outage',recovery_attempted=True,recovery_succeeded=True,restart_epoch=1);ok(a['state']=='recovered');b=s.register('b',execution_id=x['execution_id'],scenario_id='stale_work',worker_claim_id='old',claim_stale=True);ok(b['state']=='stale_released');row=s.snapshot()['records'][1];ok(row['worker_claim_id']=='');q=s.inspection_summary();ok(not q['raw_content_exposed']);ok(not q['provider_payload_exposed']);ok(not any(q['authority_boundary'].values()))
print(json.dumps({'passed':p,'total':6,'suite':'v1144.4'}))
