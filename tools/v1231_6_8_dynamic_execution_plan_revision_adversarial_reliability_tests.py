from __future__ import annotations
import hashlib,importlib,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for value in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(value) not in sys.path: sys.path.insert(0,str(value))
import dynamic_execution_plan_revision as revision
import execution_session_pause_resume_cancel_recovery as control
import live_execution_monitoring_operator_intervention as monitoring
from v1228_control_fixture import build_control_fixture
from v1231_plan_revision_fixture import clone_runtime,_apply_transition
checks=[]
def check(v): checks.append(bool(v))
def tree_signature():
    rows=[]
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc','.pyo'}:
            rows.append(f"{p.relative_to(ROOT).as_posix()}:{hashlib.sha256(p.read_bytes()).hexdigest()}")
    return hashlib.sha256('\n'.join(rows).encode()).hexdigest(),len(rows)
before=tree_signature()
fixture=build_control_fixture('v1231-reliability'); launch=fixture['launch']; base=fixture['runtime']
seed=monitoring.record_live_execution_progress(launch['launch_id'],expected_launch_digest=launch['launch_digest'],event_type='blocker_reported',current_stage='blocked',completed_units=0,total_units=2,blocker_codes=['dependency_blocked'],risk_codes=['scope_drift','test_coverage_gap'],operator_attention_required=True,runtime_root=base)
assert seed.get('ok'),seed
names=('restart','request','contradiction','paused','stale_monitor','stale_control','tamper_proposal','tamper_review','completed','cancelled','recovered','expansion','privacy')
runtimes={name:clone_runtime(base,f'v1231-reliability-{name}') for name in names}
def state(rt): return control.inspect_execution_session_control(launch['launch_id'],runtime_root=rt,reconcile_runtime=False)
def monitor(rt): return monitoring.inspect_live_execution_monitoring(launch['launch_id'],runtime_root=rt)
def prepare(rt,codes):
    m=monitor(rt); c=state(rt)
    return revision.prepare_dynamic_execution_plan_revision(launch['launch_id'],expected_launch_digest=launch['launch_digest'],expected_monitor_digest=m['monitor_digest'],expected_control_digest=c['control_digest'],verified_change_codes=codes,runtime_root=rt)
# Restart and deterministic replay.
rt=runtimes['restart']; proposal=prepare(rt,['dependency_state_changed','test_evidence_changed']); check(proposal.get('ok'))
path=revision._proposal_path(proposal['revision_id'],rt); original_bytes=path.read_bytes(); revision=importlib.reload(revision)
loaded=revision.inspect_dynamic_execution_plan_revision(proposal['revision_id'],runtime_root=rt); check(loaded.get('ok')); check(loaded.get('revision_digest')==proposal.get('revision_digest'))
replay=prepare(rt,['test_evidence_changed','dependency_state_changed']); check(replay.get('operation_status')=='replayed'); check(replay.get('revision_id')==proposal.get('revision_id')); check(path.read_bytes()==original_bytes)
# Request changes permits append-only next generation on fresh evidence.
rt=runtimes['request']; first=prepare(rt,['dependency_state_changed','test_evidence_changed']); check(first.get('ok'))
first_path=revision._proposal_path(first['revision_id'],rt); first_bytes=first_path.read_bytes()
review=revision.review_dynamic_execution_plan_revision(first['revision_id'],expected_revision_digest=first['revision_digest'],disposition='request_changes',runtime_root=rt); check(review.get('ok'))
changed=monitoring.record_live_execution_progress(launch['launch_id'],expected_launch_digest=launch['launch_digest'],event_type='risk_reported',current_stage='blocked',completed_units=0,total_units=2,blocker_codes=['dependency_blocked'],risk_codes=['uncertainty_high','operator_attention'],operator_attention_required=True,runtime_root=rt)
second=revision.prepare_dynamic_execution_plan_revision(launch['launch_id'],expected_launch_digest=launch['launch_digest'],expected_monitor_digest=changed['monitor_digest'],expected_control_digest=state(rt)['control_digest'],verified_change_codes=['risk_profile_changed','operator_goal_clarified'],runtime_root=rt)
check(second.get('ok')); check(second.get('generation')==2); check(second.get('previous_revision_id')==first.get('revision_id')); check(second.get('previous_revision_digest')==first.get('revision_digest')); check(first_path.read_bytes()==first_bytes)
# Accepted contradictory scope direction fails closed after later fresh evidence.
rt=runtimes['contradiction']; contracted=prepare(rt,['scope_contraction_required','risk_profile_changed']); check(contracted.get('ok'))
accepted=revision.review_dynamic_execution_plan_revision(contracted['revision_id'],expected_revision_digest=contracted['revision_digest'],disposition='accept',runtime_root=rt); check(accepted.get('ok'))
new_monitor=monitoring.record_live_execution_progress(launch['launch_id'],expected_launch_digest=launch['launch_digest'],event_type='risk_reported',current_stage='blocked',completed_units=0,total_units=2,blocker_codes=['dependency_blocked'],risk_codes=['scope_drift','uncertainty_high'],operator_attention_required=True,runtime_root=rt)
blocked=revision.prepare_dynamic_execution_plan_revision(launch['launch_id'],expected_launch_digest=launch['launch_digest'],expected_monitor_digest=new_monitor['monitor_digest'],expected_control_digest=state(rt)['control_digest'],verified_change_codes=['scope_expansion_required'],runtime_root=rt)
check(blocked.get('ok') is False); check(blocked.get('status')=='dynamic_execution_plan_revision_contradiction_blocked'); check(blocked.get('queue_mutation_authorized') is False); check(blocked.get('schedule_mutation_authorized') is False)
# Paused acceptance remains paused.
rt=runtimes['paused']; _apply_transition({**fixture,'runtime':rt},'pause'); paused=prepare(rt,['dependency_state_changed']); check(paused.get('ok'))
control_before=state(rt); accepted_paused=revision.review_dynamic_execution_plan_revision(paused['revision_id'],expected_revision_digest=paused['revision_digest'],disposition='accept',runtime_root=rt); control_after=state(rt)
check(accepted_paused.get('ok')); check(accepted_paused.get('accepted_revision_does_not_resume_session') is True); check(control_after.get('session_state')=='paused'); check(control_after.get('control_digest')==control_before.get('control_digest')); check(control_after.get('generation')==control_before.get('generation'))
# Stale state after monitor/control changes.
rt=runtimes['stale_monitor']; old_m=monitor(rt); old_c=state(rt); changed=monitoring.record_live_execution_progress(launch['launch_id'],expected_launch_digest=launch['launch_digest'],event_type='risk_reported',current_stage='blocked',completed_units=0,total_units=2,blocker_codes=['dependency_blocked'],risk_codes=['uncertainty_high'],operator_attention_required=True,runtime_root=rt)
stale=revision.prepare_dynamic_execution_plan_revision(launch['launch_id'],expected_launch_digest=launch['launch_digest'],expected_monitor_digest=old_m['monitor_digest'],expected_control_digest=old_c['control_digest'],verified_change_codes=['risk_profile_changed'],runtime_root=rt)
check(changed.get('ok')); check(stale.get('ok') is False); check(stale.get('status')=='dynamic_execution_plan_revision_stale_monitor_digest')
rt=runtimes['stale_control']; old_m=monitor(rt); old_c=state(rt); _apply_transition({**fixture,'runtime':rt},'pause')
stale=revision.prepare_dynamic_execution_plan_revision(launch['launch_id'],expected_launch_digest=launch['launch_digest'],expected_monitor_digest=monitor(rt)['monitor_digest'],expected_control_digest=old_c['control_digest'],verified_change_codes=['risk_profile_changed'],runtime_root=rt)
check(stale.get('ok') is False); check(stale.get('status')=='dynamic_execution_plan_revision_stale_control_digest')
# Tampered proposal cannot be inspected or reviewed.
rt=runtimes['tamper_proposal']; p=prepare(rt,['dependency_state_changed']); path=revision._proposal_path(p['revision_id'],rt); stored=json.loads(path.read_text()); stored['goal_alignment']='silently_changed'; path.write_text(json.dumps(stored,sort_keys=True))
check(revision.inspect_dynamic_execution_plan_revision(p['revision_id'],runtime_root=rt).get('ok') is False)
review_blocked=revision.review_dynamic_execution_plan_revision(p['revision_id'],expected_revision_digest=p['revision_digest'],disposition='accept',runtime_root=rt); check(review_blocked.get('ok') is False); check(review_blocked.get('provider_execution_authorized') is False)
# Tampered review blocks the whole review inventory.
rt=runtimes['tamper_review']; p=prepare(rt,['test_evidence_changed']); rr=revision.review_dynamic_execution_plan_revision(p['revision_id'],expected_revision_digest=p['revision_digest'],disposition='accept',runtime_root=rt)
path=revision._review_path(rr['review_id'],rt); stored=json.loads(path.read_text()); stored['resume_authorized']=True; path.write_text(json.dumps(stored,sort_keys=True))
listed=revision.public_dynamic_execution_plan_revision_reviews(runtime_root=rt); check(listed.get('ok') is False); check(listed.get('status')=='dynamic_execution_plan_revision_review_list_blocked')
# Completed/cancelled states block revision.
rt=runtimes['completed']; completed=monitoring.record_live_execution_progress(launch['launch_id'],expected_launch_digest=launch['launch_digest'],event_type='session_completed_pending_review',current_stage='completed_pending_review',completed_units=2,total_units=2,blocker_codes=[],risk_codes=['none'],runtime_root=rt)
result=revision.prepare_dynamic_execution_plan_revision(launch['launch_id'],expected_launch_digest=launch['launch_digest'],expected_monitor_digest=completed['monitor_digest'],expected_control_digest=state(rt)['control_digest'],verified_change_codes=['unknown_verified_change'],runtime_root=rt)
check(result.get('ok') is False); check(result.get('resume_authorized') is False); check(result.get('project_mutation_authorized') is False)
rt=runtimes['cancelled']; cancel_monitor=monitor(rt); _apply_transition({**fixture,'runtime':rt},'cancel'); cancelled_state=state(rt)
result=revision.prepare_dynamic_execution_plan_revision(launch['launch_id'],expected_launch_digest=launch['launch_digest'],expected_monitor_digest=cancel_monitor['monitor_digest'],expected_control_digest=cancelled_state.get('control_digest','0'*64),verified_change_codes=['unknown_verified_change'],runtime_root=rt)
check(result.get('ok') is False); check(result.get('status') in {'dynamic_execution_plan_revision_session_state_blocked','dynamic_execution_plan_revision_control_evidence_unavailable','dynamic_execution_plan_revision_launch_evidence_unavailable'}); check(result.get('resume_authorized') is False); check(result.get('project_mutation_authorized') is False)
# Crash recovery returns to paused and remains eligible without authority.
rt=runtimes['recovered']; shutil.rmtree(control._runtime_namespace_path(launch['launch_id'],rt),ignore_errors=True); required=control.inspect_execution_session_control(launch['launch_id'],runtime_root=rt,reconcile_runtime=True); check(required.get('session_state')=='recovery_required')
_apply_transition({**fixture,'runtime':rt},'recover'); result=prepare(rt,['unknown_verified_change']); check(result.get('ok') is True); check(result.get('session_state_at_proposal')=='paused'); check(result.get('resume_authorized') is False)
# Accepted scope expansion remains disclosure only.
rt=runtimes['expansion']; expansion=prepare(rt,['scope_expansion_required']); er=revision.review_dynamic_execution_plan_revision(expansion['revision_id'],expected_revision_digest=expansion['revision_digest'],disposition='accept',runtime_root=rt)
for key in ('scope_expansion_authorized','execution_session_launch_authorized','provider_execution_authorized','command_execution_authorized','test_execution_authorized','workspace_materialization_authorized','project_mutation_authorized','queue_mutation_authorized','schedule_mutation_authorized','resume_authorized','background_execution_authorized','cognition_write_authorized','old_authority_reusable'):
    check(er.get(key) is False)
check(er.get('accepted_revision_requires_fresh_future_authority') is True)
# Privacy.
rt=runtimes['privacy']; p=prepare(rt,['operator_goal_clarified']); revision.review_dynamic_execution_plan_revision(p['revision_id'],expected_revision_digest=p['revision_digest'],disposition='defer',runtime_root=rt)
public=revision.public_dynamic_execution_plan_revisions(runtime_root=rt); reviews=revision.public_dynamic_execution_plan_revision_reviews(runtime_root=rt); encoded=json.dumps({'p':public,'r':reviews},sort_keys=True)
check(public.get('ok')); check(reviews.get('ok')); check(str(rt) not in encoded); check('private request' not in encoded.lower()); check('raw_provider_output' not in encoded or public.get('raw_provider_output_exposed') is False)
check(public.get('private_request_exposed') is False); check(public.get('private_path_exposed') is False); check(public.get('private_content_exposed') is False); check(public.get('raw_provider_output_exposed') is False); check(public.get('raw_test_output_exposed') is False)
check(before==tree_signature())
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks)},sort_keys=True))
raise SystemExit(0 if all(checks) else 1)
