from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for value in (ROOT/'conscious_agent',ROOT/'tools'):
    if str(value) not in sys.path:sys.path.insert(0,str(value))
import execution_outcome_reflection_learning_integration as subject
from v1229_outcome_fixture import build_outcome_fixture
checks=[]
def check(v):checks.append(bool(v))
# One real completed lineage exercises v1226-v1228 binding.
f=build_outcome_fixture('foundations-completed','completed')
row=subject.prepare_execution_outcome(f['launch']['launch_id'],outcome_type='completed',expected_launch_digest=f['launch']['launch_digest'],expected_monitor_digest=f['monitor']['monitor_digest'],expected_control_digest=f['control']['control_digest'],runtime_root=f['runtime'])
for value in (row.get('ok'),row.get('outcome_type')=='completed',subject._validate_outcome(row),row.get('achievement_classification')=='achieved',row.get('cognition_written') is False,row.get('project_mutation_authorized') is False,row.get('project_reference','').startswith('project_')):check(value)
replay=subject.prepare_execution_outcome(f['launch']['launch_id'],outcome_type='completed',expected_launch_digest=f['launch']['launch_digest'],expected_monitor_digest=f['monitor']['monitor_digest'],expected_control_digest=f['control']['control_digest'],runtime_root=f['runtime'])
check(replay.get('operation_status')=='replayed')
bad=subject.prepare_execution_outcome(f['launch']['launch_id'],outcome_type='completed',expected_launch_digest='0'*64,expected_monitor_digest=f['monitor']['monitor_digest'],expected_control_digest=f['control']['control_digest'],runtime_root=f['runtime'])
check(bad.get('ok') is False);check(bad.get('reason')=='stale_or_invalid_launch')
# Classification matrix is deterministic and content-free.
cases={
 'completed':({'current_stage':'completed_pending_review','progress_percent':100,'blocker_codes':[],'risk_codes':['none']},{'session_state':'active','recovery_attempts':0},True),
 'failed':({'current_stage':'blocked','progress_percent':50,'blocker_codes':['dependency_blocked'],'risk_codes':['uncertainty_high']},{'session_state':'active','recovery_attempts':0},True),
 'cancelled':({'current_stage':'operator_review_required','progress_percent':25,'blocker_codes':[],'risk_codes':['none']},{'session_state':'cancelled','recovery_attempts':0},True),
 'paused':({'current_stage':'operator_review_required','progress_percent':25,'blocker_codes':[],'risk_codes':['none']},{'session_state':'paused','recovery_attempts':0},True),
 'recovered':({'current_stage':'operator_review_required','progress_percent':25,'blocker_codes':[],'risk_codes':['none']},{'session_state':'paused','recovery_attempts':1},True),
 'abandoned':({'current_stage':'operator_review_required','progress_percent':25,'blocker_codes':[],'risk_codes':['none']},{'session_state':'cancelled','recovery_attempts':0},True),
 'inconclusive':({'current_stage':'launched_waiting_for_step_authorization','progress_percent':0,'blocker_codes':['authorization_required'],'risk_codes':['none']},{'session_state':'active','recovery_attempts':0},True),
}
for kind,(monitor,control,expected) in cases.items():
    supported,facts,uncertainty=subject._outcome_supported(kind,monitor,control);check(supported is expected);check(bool(facts));check(isinstance(uncertainty,list))
check(subject._candidate_codes({'outcome_type':'inconclusive','observed_fact_codes':['monitor_stage:launched_waiting_for_step_authorization','control_state:active','progress_bucket:0','blocker:authorization_required','risk:none'],'uncertainty_codes':['terminal_outcome_not_established']})==['no_durable_lesson'])
check(subject.OUTCOME_TYPES==set(cases))
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks)},sort_keys=True));raise SystemExit(0 if all(checks) else 1)
