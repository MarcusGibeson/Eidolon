import tempfile
from pathlib import Path
from conscious_agent.workload_budget_eligibility import WorkloadBudgetEligibilityStore
from conscious_agent.continuity_soak_eligibility import ContinuitySoakEligibilityStore, SOAK_SCENARIOS
from conscious_agent.continuity_soak_campaign_candidates import ContinuitySoakCampaignCandidateStore
from conscious_agent.continuity_soak_live_execution import ContinuitySoakLiveExecutionStore
from conscious_agent.continuity_soak_recovery_receipts import ContinuitySoakRecoveryReceiptStore
from conscious_agent.continuity_soak_reliability_review import ContinuitySoakReliabilityReviewStore
from conscious_agent.continuity_soak_visible_evidence import ContinuitySoakVisibleEvidenceStore
p=0
def ok(x):
 global p; assert x; p+=1
with tempfile.TemporaryDirectory() as td:
 r=Path(td);w=WorkloadBudgetEligibilityStore(r);ids=[w.register('w'+k,workload_id='w'+k,workload_kind=k,owner_id='o'+k,cpu_budget_ms=100,memory_budget_mb=128,latency_budget_ms=500,token_budget=256)['eligibility_id'] for k in ('cognition','conversation','inquiry','development')];e=ContinuitySoakEligibilityStore(r).register('e',soak_scope_id='scope',baseline_checkpoint_digest='a'*64,runtime_profile_digest='b'*64,provider_profile_digest='c'*64,workload_eligibility_ids=ids,scenario_ids=sorted(SOAK_SCENARIOS),duration_days=3,observation_interval_minutes=30);c=ContinuitySoakCampaignCandidateStore(r).register('c',eligibility_id=e['eligibility_id'],campaign_action='prepare',campaign_group_id='g',observation_profile_id='o',recovery_profile_id='r',scenario_sequence=sorted(SOAK_SCENARIOS),planned_sleep_cycles=2,planned_restart_count=2,planned_interruption_count=2,planned_provider_outage_count=2,max_provider_outage_minutes=30,stale_work_threshold_minutes=60);x=ContinuitySoakLiveExecutionStore(r).register('x',campaign_id=c['campaign_id'],operator_confirmation_id='confirm',launch_token_id='token');z=ContinuitySoakRecoveryReceiptStore(r).register('z',execution_id=x['execution_id'],scenario_id='restart',recovery_attempted=True,recovery_succeeded=True);q=ContinuitySoakReliabilityReviewStore(r).register('q',receipt_id=z['receipt_id'],expected_scenario_count=6,observed_scenario_count=6);v=ContinuitySoakVisibleEvidenceStore(r);a=v.register('ev',review_id=q['review_id']);ok(a['status']=='evidence_recorded');ok(v.register('ev',review_id=q['review_id'])['idempotent']);i=v.inspection_summary();ok(i['evidence_count']==1);ok(i['recent_evidence'][0]['advisory_only']);ok(not i['raw_content_exposed']);ok(not any(i['authority_boundary'].values()))
print({'passed':p,'total':6,'suite':'v1144.7'})
