from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import goal_motivation_work_priority_integration as integration
import operator_governed_work_prioritization_scheduling as priority
from persistent_motivation import MotivationStore
from v1236_priority_fixture import build_priority_integration_fixture, clone_runtime

checks = []
def check(value): checks.append(bool(value))

def signature():
    rows=[]
    for path in sorted(ROOT.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix not in {'.pyc','.pyo'}:
            rows.append(f"{path.relative_to(ROOT).as_posix()}:{hashlib.sha256(path.read_bytes()).hexdigest()}")
    return hashlib.sha256('\n'.join(rows).encode()).hexdigest(), len(rows)

before = signature()
fixture = build_priority_integration_fixture('v1236-foundations')
base = fixture['runtime']
qid = fixture['queue_item_id']
ranking = fixture['ranking']
lesson_review = fixture['lesson_review']

def prepare(rt, *, ranking_row=ranking, with_lesson=True):
    return integration.prepare_goal_motivation_work_priority_integration(
        qid,
        expected_prioritization_digest=ranking_row['prioritization_digest'],
        lesson_review_id=lesson_review['review_id'] if with_lesson else '',
        expected_lesson_review_digest=lesson_review['review_digest'] if with_lesson else '',
        runtime_root=rt,
    )

contract = integration.build_goal_motivation_work_priority_integration_contract()
for value in (
    contract.get('ok'), contract.get('contract_version') == 'v1236.8',
    contract.get('milestone_name') == 'Goal, Motivation, and Work-Priority Integration',
    contract.get('roadmap_path') == 'Balanced Mind-and-Action Path 3',
    contract.get('exact_operator_governed_priority_item_binding') is True,
    contract.get('sanitized_goal_and_motivation_snapshot_binding') is True,
    contract.get('optional_exact_active_lesson_review_binding') is True,
    contract.get('deterministic_alignment_assessment') is True,
    contract.get('priority_change_is_proposal_only') is True,
    contract.get('append_only_refresh_on_state_change') is True,
    contract.get('accepted_alignment_does_not_change_priority') is True,
    set(contract.get('alignment_states') or []) == integration.ALIGNMENT_STATES,
    set(contract.get('review_dispositions') or []) == integration.REVIEW_DISPOSITIONS,
    set(contract.get('recommendation_codes') or []) == integration.RECOMMENDATION_CODES,
): check(value)
for key, expected in integration.AUTHORITY_FLAGS.items(): check(contract.get(key) is expected)

rt = clone_runtime(base, 'v1236-base')
a = prepare(rt)
for value in (
    a.get('ok'), a.get('status') == 'goal_motivation_work_priority_integration_ready_for_operator_review',
    a.get('queue_item_id') == qid, a.get('project_reference') == fixture['project_reference'],
    a.get('prioritization_digest') == ranking['prioritization_digest'],
    a.get('goal_count') == 1, a.get('motivation_count') == 1,
    a.get('ignored_other_project_count') == 1,
    a.get('lesson_evidence_applied') is True,
    a.get('lesson_review_digest') == lesson_review['review_digest'],
    a.get('alignment_state') == 'strongly_aligned', a.get('alignment_confidence') == 'high',
    a.get('current_priority_level') == 'normal', a.get('recommended_priority_level') == 'high',
    a.get('priority_change_recommended') is True, 'raise_priority' in (a.get('recommendation_codes') or []),
    'apply_verified_lesson' in (a.get('recommendation_codes') or []),
    len(a.get('assessment_digest','')) == 64, len(a.get('combined_snapshot_digest','')) == 64,
): check(value)
for key, expected in integration.AUTHORITY_FLAGS.items(): check(a.get(key) is expected)
for key in ('provider_contacted','commands_executed','tests_executed','project_modified','goals_modified','motivations_modified','queue_modified','schedule_modified','cognition_written','hidden_retry_created'):
    check(a.get(key) is False)

replay = prepare(rt)
check(replay.get('ok')); check(replay.get('operation_status') == 'replayed'); check(replay.get('assessment_digest') == a.get('assessment_digest'))

# Optional lesson evidence is genuinely optional and changes only the sealed basis.
rt_no_lesson = clone_runtime(base, 'v1236-no-lesson')
no_lesson = prepare(rt_no_lesson, with_lesson=False)
check(no_lesson.get('ok')); check(no_lesson.get('lesson_evidence_applied') is False)
check(no_lesson.get('lesson_alignment_adjustment') == 0.0); check('apply_verified_lesson' not in (no_lesson.get('recommendation_codes') or []))

# Conflicting and mixed established state remain visible rather than silently flattened.
rt_conflict = clone_runtime(base, 'v1236-conflict')
store = MotivationStore(Path(rt_conflict) / 'cognition')
for mid in ('mot-v1236-goal','mot-v1236-motivation'):
    result = store.update_motivation(f'conflict:{mid}', mid, reason_code='verified_conflict', valence=-1.0, urgency=1.0, confidence=1.0)
    check(result.get('ok'))
conflict = prepare(rt_conflict, with_lesson=False)
check(conflict.get('ok')); check(conflict.get('alignment_state') == 'conflicted')
check(conflict.get('recommended_priority_level') == 'low'); check('defer_for_goal_conflict' in (conflict.get('recommendation_codes') or []))

rt_mixed = clone_runtime(base, 'v1236-mixed')
store = MotivationStore(Path(rt_mixed) / 'cognition')
result = store.update_motivation('mixed:motivation', 'mot-v1236-motivation', reason_code='verified_counterpressure', valence=-1.0, urgency=1.0, confidence=1.0)
check(result.get('ok'))
mixed = prepare(rt_mixed, with_lesson=False)
check(mixed.get('ok')); check(mixed.get('alignment_state') == 'mixed')
check('clarify_goal_alignment' in (mixed.get('recommendation_codes') or [])); check('supporting_and_conflicting_signals' in (mixed.get('uncertainty_codes') or []))

# Missing active evidence is explicit and cannot create a priority change.
rt_missing = clone_runtime(base, 'v1236-missing')
store = MotivationStore(Path(rt_missing) / 'cognition')
for mid in ('mot-v1236-goal','mot-v1236-motivation'):
    result = store.update_motivation(f'resolve:{mid}', mid, reason_code='fixture_resolution', lifecycle_state='resolved')
    check(result.get('ok'))
missing = prepare(rt_missing, with_lesson=False)
check(missing.get('ok')); check(missing.get('alignment_state') == 'insufficient_evidence')
check(missing.get('recommended_priority_level') == 'normal'); check(missing.get('priority_change_recommended') is False)
check('goal_and_motivation_evidence_missing' in (missing.get('uncertainty_codes') or []))

# A changed motivation snapshot creates a new immutable generation.
rt_refresh = clone_runtime(base, 'v1236-refresh')
first = prepare(rt_refresh, with_lesson=False)
first_path = integration._assessment_path(first['assessment_id'], rt_refresh)
first_bytes = first_path.read_bytes()
store = MotivationStore(Path(rt_refresh) / 'cognition')
result = store.update_motivation('refresh:urgency', 'mot-v1236-motivation', reason_code='later_evidence', urgency=0.2, confidence=0.8)
check(result.get('ok'))
second = prepare(rt_refresh, with_lesson=False)
check(second.get('ok')); check(second.get('operation_status') == 'refreshed'); check(second.get('generation') == 2)
check(second.get('previous_assessment_digest') == first.get('assessment_digest')); check(second.get('assessment_digest') != first.get('assessment_digest'))
check(first_path.read_bytes() == first_bytes)

# Operator pinning is preserved even when alignment would otherwise raise priority.
rt_pinned = clone_runtime(base, 'v1236-pinned')
override = priority.record_work_priority_override(qid, expected_prioritization_digest=ranking['prioritization_digest'], pinned=True, runtime_root=rt_pinned)
check(override.get('ok'))
pinned_ranking = priority.build_operator_governed_work_prioritization(runtime_root=rt_pinned)
check(pinned_ranking.get('ok')); check(pinned_ranking.get('prioritization_digest') != ranking.get('prioritization_digest'))
pinned = prepare(rt_pinned, ranking_row=pinned_ranking)
check(pinned.get('ok')); check(pinned.get('priority_pinned') is True)
check(pinned.get('recommended_priority_level') == pinned.get('current_priority_level'))
check('preserve_operator_priority' in (pinned.get('recommendation_codes') or []))

# Stale and malformed exact references fail closed.
for bad_item, bad_digest in (('work_'+'0'*24, ranking['prioritization_digest']), (qid, '0'*64)):
    row = integration.prepare_goal_motivation_work_priority_integration(bad_item, expected_prioritization_digest=bad_digest, runtime_root=clone_runtime(base,'v1236-stale-'+bad_item[-4:]))
    check(row.get('ok') is False); check(row.get('status') == 'goal_motivation_work_priority_integration_blocked')

partial = integration.prepare_goal_motivation_work_priority_integration(qid, expected_prioritization_digest=ranking['prioritization_digest'], lesson_review_id=lesson_review['review_id'], runtime_root=clone_runtime(base,'v1236-partial'))
check(partial.get('ok') is False); check('incomplete_lesson_review_reference' in partial.get('reason',''))

check(before == signature())
print(json.dumps({'ok': all(checks), 'passed': sum(checks), 'total': len(checks)}, sort_keys=True))
raise SystemExit(0 if all(checks) else 1)
