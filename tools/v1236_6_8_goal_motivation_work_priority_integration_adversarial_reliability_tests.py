from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))

import goal_motivation_work_priority_integration as integration
import operator_governed_work_prioritization_scheduling as priority
from persistent_motivation import MotivationStore
from v1236_priority_fixture import build_priority_integration_fixture,clone_runtime

checks=[]
def check(v): checks.append(bool(v))

def signature():
    rows=[]
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc','.pyo'}:
            rows.append(f"{p.relative_to(ROOT).as_posix()}:{hashlib.sha256(p.read_bytes()).hexdigest()}")
    return hashlib.sha256('\n'.join(rows).encode()).hexdigest(),len(rows)

before=signature()
fixture=build_priority_integration_fixture('v1236-adversarial')
base=fixture['runtime']; qid=fixture['queue_item_id']; ranking=fixture['ranking']; lesson=fixture['lesson_review']

def prepare(rt, *, ranking_digest=None, with_lesson=True):
    return integration.prepare_goal_motivation_work_priority_integration(
        qid,expected_prioritization_digest=ranking_digest or ranking['prioritization_digest'],
        lesson_review_id=lesson['review_id'] if with_lesson else '',
        expected_lesson_review_digest=lesson['review_digest'] if with_lesson else '',runtime_root=rt)

# Deterministic restart-equivalent copies.
a1=prepare(clone_runtime(base,'v1236-det-a')); a2=prepare(clone_runtime(base,'v1236-det-b'))
for v in (a1.get('ok'),a2.get('ok'),a1.get('assessment_id')==a2.get('assessment_id'),a1.get('assessment_digest')==a2.get('assessment_digest'),a1.get('basis_digest')==a2.get('basis_digest')): check(v)

# Concurrent duplicate preparation creates one record and one replay-equivalent result.
rt=clone_runtime(base,'v1236-concurrent')
with ThreadPoolExecutor(max_workers=2) as pool:
    rows=list(pool.map(lambda _: prepare(rt),range(2)))
check(all(row.get('ok') for row in rows)); check(len({row.get('assessment_digest') for row in rows})==1)
check(sum(row.get('operation_status')=='created' for row in rows)==1); check(sum(row.get('operation_status')=='replayed' for row in rows)==1)

# Stale goal or motivation state blocks review of the historical assessment.
rt=clone_runtime(base,'v1236-stale-state'); a=prepare(rt)
store=MotivationStore(Path(rt)/'cognition')
changed=store.update_motivation('stale:motivation','mot-v1236-motivation',reason_code='later_verified_state',urgency=0.1)
check(changed.get('ok'))
blocked=integration.review_goal_motivation_work_priority_integration(a['assessment_id'],expected_assessment_digest=a['assessment_digest'],disposition='accept_alignment',runtime_root=rt)
check(blocked.get('ok') is False); check('stale_goal_motivation_priority_or_lesson_state' in blocked.get('reason',''))
refreshed=prepare(rt)
check(refreshed.get('ok')); check(refreshed.get('generation')==2); check(refreshed.get('previous_assessment_digest')==a.get('assessment_digest'))

# Stale prioritization blocks review and requires a fresh integration generation.
rt=clone_runtime(base,'v1236-stale-priority'); a=prepare(rt)
override=priority.record_work_priority_override(qid,expected_prioritization_digest=ranking['prioritization_digest'],priority_level='high',runtime_root=rt)
check(override.get('ok'))
new_ranking=priority.build_operator_governed_work_prioritization(runtime_root=rt)
check(new_ranking.get('ok')); check(new_ranking.get('prioritization_digest')!=ranking.get('prioritization_digest'))
blocked=integration.review_goal_motivation_work_priority_integration(a['assessment_id'],expected_assessment_digest=a['assessment_digest'],disposition='accept_alignment',runtime_root=rt)
check(blocked.get('ok') is False); check('stale_or_invalid_prioritization' in blocked.get('reason',''))
new_a=prepare(rt,ranking_digest=new_ranking['prioritization_digest'])
check(new_a.get('ok')); check(new_a.get('generation')==2); check(new_a.get('current_priority_level')=='high')

# Tampered assessment, review, index, priority, and lesson records fail closed or disappear from public views.
rt=clone_runtime(base,'v1236-tamper-assessment'); a=prepare(rt)
p=integration._assessment_path(a['assessment_id'],rt); data=json.loads(p.read_text()); data['alignment_state']='invented'; p.write_text(json.dumps(data))
row=integration.review_goal_motivation_work_priority_integration(a['assessment_id'],expected_assessment_digest=a['assessment_digest'],disposition='accept_alignment',runtime_root=rt)
check(row.get('ok') is False); check('stale_or_invalid_assessment' in row.get('reason',''))
check(integration.public_goal_motivation_work_priority_integrations(runtime_root=rt).get('assessment_count')==0)

rt=clone_runtime(base,'v1236-tamper-review'); a=prepare(rt); r=integration.review_goal_motivation_work_priority_integration(a['assessment_id'],expected_assessment_digest=a['assessment_digest'],disposition='accept_alignment',runtime_root=rt)
p=integration._review_path(a['assessment_id'],rt); data=json.loads(p.read_text()); data['priority_changed']=True; p.write_text(json.dumps(data))
check(integration.public_goal_motivation_work_priority_integration_reviews(runtime_root=rt).get('review_count')==0)

rt=clone_runtime(base,'v1236-tamper-index'); a=prepare(rt)
p=integration._assessment_index_path(qid,rt); data=json.loads(p.read_text()); data['generation']=999; p.write_text(json.dumps(data))
row=prepare(rt); check(row.get('ok') is False); check(row.get('status')=='goal_motivation_work_priority_assessment_index_integrity_blocked')

rt=clone_runtime(base,'v1236-tamper-priority')
p=priority._prioritization_path(rt); data=json.loads(p.read_text()); data['recommended_queue_item_id']='work_'+'f'*24; p.write_text(json.dumps(data))
row=prepare(rt); check(row.get('ok') is False); check('stale_or_invalid_prioritization' in row.get('reason',''))

rt=clone_runtime(base,'v1236-tamper-lesson')
p=Path(rt)/'development_campaigns'/'evidence_backed_development_lesson_reviews'/f"{lesson['review_id']}.json"; data=json.loads(p.read_text()); data['lesson_active']=False; p.write_text(json.dumps(data))
row=prepare(rt); check(row.get('ok') is False); check('stale_or_invalid_lesson_review' in row.get('reason',''))

# Stale lock recovery remains bounded and deterministic.
rt=clone_runtime(base,'v1236-stale-lock'); lock=integration._root(rt)/'locks'/'goal-motivation-work-priority-integration.lock'; lock.mkdir(parents=True); os.utime(lock,(time.time()-120,time.time()-120))
row=prepare(rt); check(row.get('ok')); check(not lock.exists())

# A verified lesson calling for realignment can lower the alignment result but still cannot mutate priority.
negative=build_priority_integration_fixture('v1236-negative-lesson',evidence_states={'goal_fit':'contradicts'},quality_disposition='request_remediation')
rt=clone_runtime(negative['runtime'],'v1236-negative-lesson-copy')
row=integration.prepare_goal_motivation_work_priority_integration(
    negative['queue_item_id'],expected_prioritization_digest=negative['ranking']['prioritization_digest'],
    lesson_review_id=negative['lesson_review']['review_id'],expected_lesson_review_digest=negative['lesson_review']['review_digest'],runtime_root=rt)
check(row.get('ok')); check('realign_with_project_goal' in (row.get('lesson_codes') or [])); check(row.get('lesson_alignment_adjustment')<0)
before_priority=priority.load_operator_governed_work_prioritization(runtime_root=rt)
review=integration.review_goal_motivation_work_priority_integration(row['assessment_id'],expected_assessment_digest=row['assessment_digest'],disposition='accept_alignment',runtime_root=rt)
after_priority=priority.load_operator_governed_work_prioritization(runtime_root=rt)
check(review.get('ok')); check(review.get('priority_changed') is False); check(before_priority.get('prioritization_digest')==after_priority.get('prioritization_digest'))

# Cross-project signals remain excluded and raw summaries never enter stored integration records or public projections.
rt=clone_runtime(base,'v1236-privacy'); a=prepare(rt); r=integration.review_goal_motivation_work_priority_integration(a['assessment_id'],expected_assessment_digest=a['assessment_digest'],disposition='accept_alignment',runtime_root=rt)
check(a.get('ignored_other_project_count')==1)
for payload in (a,r,integration.public_goal_motivation_work_priority_integrations(runtime_root=rt),integration.public_goal_motivation_work_priority_integration_reviews(runtime_root=rt)):
    encoded=json.dumps(payload,sort_keys=True)
    check('content intentionally omitted from v1236 public evidence' not in encoded)
    check('unrelated project content intentionally omitted' not in encoded)
    check('goal-ref' not in encoded); check('motivation-ref' not in encoded)
    check(payload.get('private_content_exposed') is False)

# Historical records are immutable and exact replay cannot be repurposed as a conflicting decision.
rt=clone_runtime(base,'v1236-history'); a=prepare(rt); ap=integration._assessment_path(a['assessment_id'],rt); assessment_bytes=ap.read_bytes()
r=integration.review_goal_motivation_work_priority_integration(a['assessment_id'],expected_assessment_digest=a['assessment_digest'],disposition='hold',runtime_root=rt); rp=integration._review_path(a['assessment_id'],rt); review_bytes=rp.read_bytes()
replay=integration.review_goal_motivation_work_priority_integration(a['assessment_id'],expected_assessment_digest=a['assessment_digest'],disposition='hold',runtime_root=rt)
conflict=integration.review_goal_motivation_work_priority_integration(a['assessment_id'],expected_assessment_digest=a['assessment_digest'],disposition='reject',runtime_root=rt)
check(r.get('ok')); check(replay.get('ok')); check(replay.get('operation_status')=='replayed')
check(conflict.get('ok') is False); check(ap.read_bytes()==assessment_bytes); check(rp.read_bytes()==review_bytes)

# No record in the layer can acquire protected authority, including priority authority.
for row in (a1,a2,new_a,row,review,r):
    check(row.get('ok'))
    for key in ('goal_state_mutation_authorized','motivation_state_mutation_authorized','priority_mutation_authorized','queue_mutation_authorized','schedule_mutation_authorized','project_mutation_authorized','cognition_write_authorized','integration_is_execution_authority','integration_is_priority_authority','execution_session_launch_authorized','resume_authorized','old_authority_reusable'):
        check(row.get(key) is False)

check(before==signature())
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks)},sort_keys=True))
raise SystemExit(0 if all(checks) else 1)
