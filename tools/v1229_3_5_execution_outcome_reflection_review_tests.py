from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for value in (ROOT/'conscious_agent',ROOT/'tools'):
    if str(value) not in sys.path:sys.path.insert(0,str(value))
import execution_outcome_reflection_learning_integration as subject
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1229_outcome_fixture import build_outcome_fixture
checks=[]
def check(v):checks.append(bool(v))
f=build_outcome_fixture('review-complete','completed')
out=subject.prepare_execution_outcome(f['launch']['launch_id'],outcome_type='completed',expected_launch_digest=f['launch']['launch_digest'],expected_monitor_digest=f['monitor']['monitor_digest'],expected_control_digest=f['control']['control_digest'],runtime_root=f['runtime'])
reflection=subject.prepare_execution_outcome_reflection(out['outcome_id'],expected_outcome_digest=out['outcome_digest'],runtime_root=f['runtime'])
for value in (reflection.get('ok'),reflection.get('reflection_status')=='candidate_ready','retain_bounded_approach' in reflection.get('candidate_lesson_codes',[]),reflection.get('cognition_written') is False):check(value)
review=subject.review_execution_outcome_lesson(reflection['reflection_id'],expected_reflection_digest=reflection['reflection_digest'],disposition='accept',runtime_root=f['runtime'])
for value in (review.get('ok'),review.get('durable_project_scoped_learning_recorded') is True,review.get('durable_project_scoped_learning_authorized') is True,review.get('cognition_written') is False):check(value)
replay=subject.review_execution_outcome_lesson(reflection['reflection_id'],expected_reflection_digest=reflection['reflection_digest'],disposition='accept',runtime_root=f['runtime']);check(replay.get('operation_status')=='replayed')
conflict=subject.review_execution_outcome_lesson(reflection['reflection_id'],expected_reflection_digest=reflection['reflection_digest'],disposition='reject',runtime_root=f['runtime']);check(conflict.get('ok') is False);check(conflict.get('reason')=='conflicting_lesson_review')
# Exact ordinary-chat path uses a separate real lineage.
f2=build_outcome_fixture('review-chat','completed')
phrase=f"Prepare execution outcome completed for bounded development execution session {f2['launch']['launch_id']} digest {f2['launch']['launch_digest']} monitor digest {f2['monitor']['monitor_digest']} control digest {f2['control']['control_digest']}."
chat=process_ordinary_chat_development_turn(phrase,runtime_root=f2['runtime']);check(chat.get('active'));check(chat['execution_outcome_reflection_learning'].get('ok'))
check(subject.process_execution_outcome_reflection_learning_control('It would be nice to learn from this.',runtime_root=f2['runtime'])=={'active':False})
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks)},sort_keys=True));raise SystemExit(0 if all(checks) else 1)
