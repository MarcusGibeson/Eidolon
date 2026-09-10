from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for value in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(value) not in sys.path: sys.path.insert(0,str(value))
from v1225_dispatch_fixture import build_dispatch_fixture
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
import live_execution_monitoring_operator_intervention as monitoring
checks=[]
def check(v): checks.append(bool(v))
fixture=build_dispatch_fixture('v1230-ordinary')
runtime=fixture['runtime']; slot=fixture['schedule']['slots'][0]

def turn(text):
    result=process_ordinary_chat_development_turn(text,runtime_root=runtime)
    check(result.get('active') is True)
    return result

prepared_turn=turn(f"prepare development execution session for item {slot['queue_item_id']} schedule {fixture['schedule']['schedule_digest']}")
prepared=prepared_turn.get('supervised_work_dispatch',{})
for v in (prepared_turn.get('event')=='prepared_development_execution_session_ready', prepared.get('ok'), prepared.get('goal_alignment_review_required') is True, prepared.get('uncertainty_review_required') is True, prepared.get('outcome_reflection_required') is True): check(v)
accepted_turn=turn(prepared['accept_phrase'])
accepted=accepted_turn.get('supervised_work_dispatch',{})
for v in (accepted_turn.get('event')=='prepared_development_execution_session_accepted', accepted.get('launch_readiness_established') is True, accepted.get('execution_session_launch_authorized') is False): check(v)
launch_auth_turn=turn(f"prepare bounded launch authorization for prepared development execution session {prepared['session_id']} digest {prepared['session_digest']}")
launch_auth=launch_auth_turn.get('execution_session_bounded_launch',{})
for v in (launch_auth_turn.get('event')=='bounded_execution_session_launch_authorization_ready', launch_auth.get('authorization_consumed') is False, bool(launch_auth.get('authorize_phrase'))): check(v)
launch_turn=turn(launch_auth['authorize_phrase'])
launch=launch_turn.get('execution_session_bounded_launch',{})
for v in (launch_turn.get('event')=='bounded_development_execution_session_launched', launch.get('execution_session_launched') is True, launch.get('provider_execution_authorized') is False, launch.get('project_mutation_authorized') is False): check(v)
monitor_turn=turn(f"prepare live execution monitoring for bounded development execution session {launch['launch_id']} digest {launch['launch_digest']}")
monitor=monitor_turn.get('live_execution_monitoring',{})
for v in (monitor_turn.get('event')=='live_execution_monitoring_ready', monitor.get('monitoring_authorized') is True, monitor.get('operator_intervention_applied') is False): check(v)
request_turn=turn(f"request bounded operator review intervention for live execution monitoring {monitor['monitor_id']} digest {monitor['monitor_digest']}")
request=request_turn.get('live_execution_monitoring',{})
for v in (request_turn.get('event')=='live_execution_intervention_requested', request.get('intervention_type')=='operator_review', request.get('operator_intervention_applied') is False): check(v)
control_turn=turn(f"prepare execution session control for bounded development execution session {launch['launch_id']} digest {launch['launch_digest']}")
control=control_turn.get('execution_session_control',{})
for v in (control_turn.get('event')=='execution_session_control_ready', control.get('session_state')=='active'): check(v)
auth_turn=turn(f"prepare bounded execution review acknowledgment authorization for intervention request {request['request_id']} digest {request['request_digest']}")
auth=auth_turn.get('execution_session_control',{})
check(auth_turn.get('event')=='execution_session_transition_authorization_ready'); check(bool(auth.get('authorize_phrase')))
transition_turn=turn(auth['authorize_phrase'])
transition=transition_turn.get('execution_session_control',{})
for v in (transition_turn.get('event')=='execution_session_transition_applied', transition.get('action')=='acknowledge_review', transition.get('provider_execution_authorized') is False): check(v)
monitor=monitoring.record_live_execution_progress(
    launch['launch_id'], expected_launch_digest=launch['launch_digest'], event_type='session_completed_pending_review',
    current_stage='completed_pending_review', completed_units=3, total_units=3, blocker_codes=[], risk_codes=['none'], runtime_root=runtime,
)
check(monitor.get('ok') is True)
control_turn=turn(f"show execution session control for bounded development execution session {launch['launch_id']}")
control=control_turn.get('execution_session_control',{})
outcome_turn=turn(f"prepare execution outcome completed for bounded development execution session {launch['launch_id']} digest {launch['launch_digest']} monitor digest {monitor['monitor_digest']} control digest {control['control_digest']}")
outcome=outcome_turn.get('execution_outcome_reflection_learning',{})
for v in (outcome.get('status')=='execution_outcome_ready_for_reflection', outcome.get('achievement_classification')=='achieved', outcome.get('cognition_write_authorized') is False): check(v)
reflection_turn=turn(f"prepare execution outcome reflection for outcome {outcome['outcome_id']} digest {outcome['outcome_digest']}")
reflection=reflection_turn.get('execution_outcome_reflection_learning',{})
for v in (reflection.get('status')=='execution_outcome_reflection_ready_for_review', reflection.get('lesson_review_required') is True, reflection.get('reflection_is_not_cognition_write') is True): check(v)
review_turn=turn(f"review execution outcome lesson accept for reflection {reflection['reflection_id']} digest {reflection['reflection_digest']}")
review=review_turn.get('execution_outcome_reflection_learning',{})
for v in (review.get('status')=='execution_outcome_lesson_accepted', review.get('durable_project_scoped_learning_recorded') is True, review.get('generalized_beyond_project') is False, review.get('cognition_written') is False): check(v)
for casual in ('It would be nice to pause someday.','Maybe you could learn from this later.','"Authorize bounded launch" is a quoted phrase.'):
    result=process_ordinary_chat_development_turn(casual,runtime_root=runtime)
    check(result.get('event') not in {'bounded_development_execution_session_launched','execution_session_paused','execution_outcome_lesson_accepted'})
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks)},sort_keys=True))
raise SystemExit(0 if all(checks) else 1)
