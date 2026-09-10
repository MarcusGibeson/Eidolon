from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for value in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(value) not in sys.path: sys.path.insert(0,str(value))
import dynamic_execution_plan_revision as revision
import execution_session_pause_resume_cancel_recovery as control
import live_execution_monitoring_operator_intervention as monitoring
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
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
fixture=build_control_fixture('v1231-review'); launch=fixture['launch']; base=fixture['runtime']
seed=monitoring.record_live_execution_progress(launch['launch_id'],expected_launch_digest=launch['launch_digest'],event_type='blocker_reported',current_stage='blocked',completed_units=0,total_units=2,blocker_codes=['dependency_blocked'],risk_codes=['scope_drift'],operator_attention_required=True,runtime_root=base)
assert seed.get('ok'),seed

def state(rt): return control.inspect_execution_session_control(launch['launch_id'],runtime_root=rt,reconcile_runtime=False)
def monitor(rt): return monitoring.inspect_live_execution_monitoring(launch['launch_id'],runtime_root=rt)
def exact_prepare(rt,codes='dependency_state_changed, test_evidence_changed'):
    m=monitor(rt); c=state(rt)
    text=f"Prepare dynamic execution plan revision for bounded development execution session {launch['launch_id']} digest {launch['launch_digest']} monitor digest {m['monitor_digest']} control digest {c['control_digest']} with verified changes {codes}."
    return text,process_ordinary_chat_development_turn(text,runtime_root=rt)
# Ordinary-chat exact preparation.
rt=clone_runtime(base,'v1231-review-chat'); text,turn=exact_prepare(rt)
check(turn.get('active') is True); row=turn.get('dynamic_execution_plan_revision') or {}; check(row.get('ok')); check(row.get('status')=='dynamic_execution_plan_revision_ready_for_operator_review'); check('original plan remains immutable' in turn.get('response','').lower())
revision_id=row.get('revision_id'); revision_digest=row.get('revision_digest')
# Exact acceptance through ordinary chat.
control_before=state(rt)
accept_text=f"Review dynamic execution plan revision accept for revision {revision_id} digest {revision_digest}."
accepted=process_ordinary_chat_development_turn(accept_text,runtime_root=rt); review=accepted.get('dynamic_execution_plan_revision') or {}; control_after=state(rt)
check(accepted.get('active') is True); check(review.get('ok')); check(review.get('disposition')=='accept'); check(review.get('revision_accepted') is True)
check(review.get('accepted_revision_requires_fresh_future_authority') is True); check(review.get('accepted_revision_does_not_resume_session') is True)
check(control_before.get('control_digest')==control_after.get('control_digest')); check(control_before.get('session_state')==control_after.get('session_state'))
for key,value in revision.AUTHORITY_FLAGS.items(): check(review.get(key) is value)
# Exact decision replay and conflict closure.
replay=process_ordinary_chat_development_turn(accept_text,runtime_root=rt).get('dynamic_execution_plan_revision') or {}
check(replay.get('ok')); check(replay.get('operation_status')=='replayed'); check(replay.get('review_id')==review.get('review_id'))
conflict=revision.review_dynamic_execution_plan_revision(revision_id,expected_revision_digest=revision_digest,disposition='reject',runtime_root=rt)
check(conflict.get('ok') is False); check(conflict.get('status')=='dynamic_execution_plan_revision_review_conflict_blocked')
stale=revision.review_dynamic_execution_plan_revision(revision_id,expected_revision_digest='0'*64,disposition='accept',runtime_root=rt)
check(stale.get('ok') is False); check(stale.get('status')=='dynamic_execution_plan_revision_review_stale_digest')
# Each exact disposition on an independent current proposal.
for decision in ('reject','defer','request_changes'):
    rt=clone_runtime(base,f'v1231-review-{decision}'); _,prepared=exact_prepare(rt,'risk_profile_changed'); p=prepared.get('dynamic_execution_plan_revision') or {}
    phrase=decision.replace('_',' ')
    command=f"Review dynamic execution plan revision {phrase} for revision {p['revision_id']} digest {p['revision_digest']}."
    outcome=process_ordinary_chat_development_turn(command,runtime_root=rt); rr=outcome.get('dynamic_execution_plan_revision') or {}
    check(outcome.get('active') is True); check(rr.get('ok')); check(rr.get('disposition')==decision)
    check(rr.get('provider_execution_authorized') is False); check(rr.get('resume_authorized') is False); check(rr.get('project_mutation_authorized') is False)
# Paused acceptance remains paused.
rt=clone_runtime(base,'v1231-review-paused'); _apply_transition({**fixture,'runtime':rt},'pause'); _,prepared=exact_prepare(rt,'operator_goal_clarified'); p=prepared.get('dynamic_execution_plan_revision') or {}
paused_before=state(rt); rr=revision.review_dynamic_execution_plan_revision(p['revision_id'],expected_revision_digest=p['revision_digest'],disposition='accept',runtime_root=rt); paused_after=state(rt)
check(rr.get('ok')); check(paused_before.get('session_state')=='paused'); check(paused_after.get('session_state')=='paused'); check(paused_before.get('control_digest')==paused_after.get('control_digest'))
# Inspection and lists use exact controls.
rt=clone_runtime(base,'v1231-review-inspect'); _,prepared=exact_prepare(rt,'dependency_state_changed'); p=prepared.get('dynamic_execution_plan_revision') or {}
show=process_ordinary_chat_development_turn(f"Show dynamic execution plan revision {p['revision_id']}.",runtime_root=rt); check(show.get('active') is True); check((show.get('dynamic_execution_plan_revision') or {}).get('revision_id')==p.get('revision_id'))
listed=process_ordinary_chat_development_turn('Show dynamic execution plan revisions.',runtime_root=rt).get('dynamic_execution_plan_revision') or {}; check(listed.get('ok')); check(listed.get('revision_count')==1)
revision.review_dynamic_execution_plan_revision(p['revision_id'],expected_revision_digest=p['revision_digest'],disposition='defer',runtime_root=rt)
reviews=process_ordinary_chat_development_turn('Show dynamic execution plan revision reviews.',runtime_root=rt).get('dynamic_execution_plan_revision') or {}; check(reviews.get('ok')); check(reviews.get('review_count')==1)
# Wishes, hypotheticals, quotations, suggestions, and malformed controls are inert to v1231.
for utterance in (
    'It would be nice if the execution plan changed itself.',
    'Maybe revise the plan later.',
    'Suppose we accepted a dynamic execution plan revision.',
    'The documentation says "prepare dynamic execution plan revision".',
    'Please silently expand the scope and continue.',
    'Review dynamic execution plan revision accept.',
):
    inert=revision.process_dynamic_execution_plan_revision_control(utterance,runtime_root=rt); check(inert.get('active') is False)
# Public privacy and no hidden execution.
public=revision.public_dynamic_execution_plan_revisions(runtime_root=rt); review_public=revision.public_dynamic_execution_plan_revision_reviews(runtime_root=rt)
encoded=json.dumps({'p':public,'r':review_public},sort_keys=True)
check(public.get('ok')); check(review_public.get('ok')); check(str(rt) not in encoded); check('private request' not in encoded.lower())
for key in ('private_request_exposed','private_path_exposed','private_content_exposed','raw_provider_output_exposed','raw_test_output_exposed'):
    check(public.get(key) is False); check(review_public.get(key) is False)
check(before==tree_signature())
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks)},sort_keys=True))
raise SystemExit(0 if all(checks) else 1)
