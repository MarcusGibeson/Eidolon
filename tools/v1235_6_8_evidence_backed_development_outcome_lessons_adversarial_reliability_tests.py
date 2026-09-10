from __future__ import annotations

import json, os, shutil, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))

import evidence_backed_development_outcome_lessons as lessons
import requirement_quality_assessment as quality
from v1234_quality_fixture import build_quality_fixture,clone_runtime,evidence_spec,requirement_spec
from v1235_lesson_fixture import build_lesson_fixture

checks=[]
def check(v): checks.append(bool(v))
fixture=build_lesson_fixture('v1235-adversarial'); base=fixture['runtime']; a=fixture['quality_assessment']; qr=fixture['quality_review']

def prepare(rt):
    return lessons.prepare_evidence_backed_development_lesson(a['assessment_id'],expected_assessment_digest=a['assessment_digest'],quality_review_id=qr['review_id'],expected_quality_review_digest=qr['review_digest'],runtime_root=rt)

# Determinism across restart-equivalent runtime copies.
a1=prepare(clone_runtime(base,'v1235-det-a')); a2=prepare(clone_runtime(base,'v1235-det-b'))
check(a1.get('ok')); check(a2.get('ok')); check(a1.get('candidate_id')==a2.get('candidate_id')); check(a1.get('candidate_digest')==a2.get('candidate_digest'))

# Stale and mismatched lineage fails closed.
for kwargs,status in (
    ({'expected_assessment_digest':'0'*64},'evidence_backed_development_lesson_blocked'),
    ({'expected_quality_review_digest':'0'*64},'evidence_backed_development_lesson_blocked'),
):
    rt=clone_runtime(base,'v1235-stale-'+str(len(checks)))
    row=lessons.prepare_evidence_backed_development_lesson(a['assessment_id'],expected_assessment_digest=kwargs.get('expected_assessment_digest',a['assessment_digest']),quality_review_id=qr['review_id'],expected_quality_review_digest=kwargs.get('expected_quality_review_digest',qr['review_digest']),runtime_root=rt)
    check(row.get('ok') is False); check(row.get('status')==status)

# Tampered candidate and review are rejected.
rt=clone_runtime(base,'v1235-tamper-candidate'); c=prepare(rt)
p=lessons._root(rt)/'evidence_backed_development_lesson_candidates'/f"{c['candidate_id']}.json"; data=json.loads(p.read_text()); data['lesson_confidence']='impossible'; p.write_text(json.dumps(data))
blocked=lessons.review_evidence_backed_development_lesson(c['candidate_id'],expected_candidate_digest=c['candidate_digest'],disposition='accept',runtime_root=rt)
check(blocked.get('ok') is False); check('integrity' in blocked.get('status',''))

rt=clone_runtime(base,'v1235-tamper-review'); c=prepare(rt); r=lessons.review_evidence_backed_development_lesson(c['candidate_id'],expected_candidate_digest=c['candidate_digest'],disposition='accept',runtime_root=rt)
p=lessons._root(rt)/'evidence_backed_development_lesson_reviews'/f"{r['review_id']}.json"; data=json.loads(p.read_text()); data['lesson_active']=False; p.write_text(json.dumps(data))
# Public listing suppresses invalid rows.
listed=lessons.public_evidence_backed_development_lesson_reviews(runtime_root=rt)
check(listed.get('review_count')==0)

# Stale lock recovery.
rt=clone_runtime(base,'v1235-stale-lock'); lock=lessons._root(rt)/'locks'/'evidence-backed-development-lessons.lock'; lock.mkdir(parents=True); os.utime(lock,(time.time()-120,time.time()-120))
row=prepare(rt); check(row.get('ok')); check(not lock.exists())

# Revised codes reject unsupported, duplicates, and contradictions.
for codes in (['made_up'],['retain_verified_approach','retain_verified_approach'],['retain_verified_approach','repair_requirement_gap']):
    rt=clone_runtime(base,'v1235-invalid-code-'+str(len(checks))); c=prepare(rt)
    row=lessons.review_evidence_backed_development_lesson(c['candidate_id'],expected_candidate_digest=c['candidate_digest'],disposition='revise',revised_lesson_codes=codes,runtime_root=rt)
    check(row.get('ok') is False); check(row.get('status')=='evidence_backed_lesson_review_blocked')

# Same-project later evidence can trigger explicit reconsideration; history remains immutable.
rt=clone_runtime(base,'v1235-reconsider'); c=prepare(rt); r=lessons.review_evidence_backed_development_lesson(c['candidate_id'],expected_candidate_digest=c['candidate_digest'],disposition='accept',runtime_root=rt)
# A fresh v1234 generation on the same resource/session with changed evidence.
ra=fixture['resource_assessment']; rr=fixture['resource_review']
later_a=quality.prepare_requirement_quality_assessment(ra['assessment_id'],expected_resource_assessment_digest=ra['assessment_digest'],resource_review_id=rr['review_id'],expected_resource_review_digest=rr['review_digest'],requirements=requirement_spec(),evidence=evidence_spec({'core_behavior':'contradicts'}),runtime_root=rt)
check(later_a.get('ok'))
later_qr=quality.review_requirement_quality_assessment(later_a['assessment_id'],expected_assessment_digest=later_a['assessment_digest'],disposition='request_remediation',runtime_root=rt)
check(later_qr.get('ok'))
rec=lessons.reconsider_evidence_backed_development_lesson(r['review_id'],expected_review_digest=r['review_digest'],later_assessment_id=later_a['assessment_id'],expected_later_assessment_digest=later_a['assessment_digest'],later_quality_review_id=later_qr['review_id'],expected_later_quality_review_digest=later_qr['review_digest'],decision='revise',runtime_root=rt)
for v in (rec.get('ok'),rec.get('decision')=='revise',rec.get('evidence_changed') is True,rec.get('historical_lesson_preserved') is True,rec.get('new_operator_review_required_for_revision') is True,'repair_requirement_gap' in (rec.get('later_candidate_lesson_codes') or [])): check(v)
replay=lessons.reconsider_evidence_backed_development_lesson(r['review_id'],expected_review_digest=r['review_digest'],later_assessment_id=later_a['assessment_id'],expected_later_assessment_digest=later_a['assessment_digest'],later_quality_review_id=later_qr['review_id'],expected_later_quality_review_digest=later_qr['review_digest'],decision='revise',runtime_root=rt)
check(replay.get('ok')); check(replay.get('operation_status')=='replayed')
conflict=lessons.reconsider_evidence_backed_development_lesson(r['review_id'],expected_review_digest=r['review_digest'],later_assessment_id=later_a['assessment_id'],expected_later_assessment_digest=later_a['assessment_digest'],later_quality_review_id=later_qr['review_id'],expected_later_quality_review_digest=later_qr['review_digest'],decision='retain',runtime_root=rt)
check(conflict.get('ok') is False); check(conflict.get('status')=='evidence_backed_lesson_conflicting_reconsideration')

# Accepting a contradictory later candidate is blocked while the original lesson is active.
later_c=lessons.prepare_evidence_backed_development_lesson(later_a['assessment_id'],expected_assessment_digest=later_a['assessment_digest'],quality_review_id=later_qr['review_id'],expected_quality_review_digest=later_qr['review_digest'],runtime_root=rt)
check(later_c.get('ok'))
blocked=lessons.review_evidence_backed_development_lesson(later_c['candidate_id'],expected_candidate_digest=later_c['candidate_digest'],disposition='accept',runtime_root=rt)
check(blocked.get('ok') is False); check(blocked.get('reason')=='contradictory_active_project_lesson')

# Same assessment is not later evidence.
same=lessons.reconsider_evidence_backed_development_lesson(r['review_id'],expected_review_digest=r['review_digest'],later_assessment_id=a['assessment_id'],expected_later_assessment_digest=a['assessment_digest'],later_quality_review_id=qr['review_id'],expected_later_quality_review_digest=qr['review_digest'],decision='retain',runtime_root=rt)
check(same.get('ok') is False); check(same.get('status')=='evidence_backed_lesson_later_evidence_required')

# Cross-project reconsideration fails closed.
other=build_lesson_fixture('v1235-other-project')
cross=lessons.reconsider_evidence_backed_development_lesson(r['review_id'],expected_review_digest=r['review_digest'],later_assessment_id=other['quality_assessment']['assessment_id'],expected_later_assessment_digest=other['quality_assessment']['assessment_digest'],later_quality_review_id=other['quality_review']['review_id'],expected_later_quality_review_digest=other['quality_review']['review_digest'],decision='retain',runtime_root=other['runtime'])
check(cross.get('ok') is False)

# Rejected/deferred lesson reviews cannot be reconsidered.
for disp in ('reject','defer'):
    rt2=clone_runtime(base,'v1235-ineligible-reconsider-'+disp); c2=prepare(rt2); r2=lessons.review_evidence_backed_development_lesson(c2['candidate_id'],expected_candidate_digest=c2['candidate_digest'],disposition=disp,runtime_root=rt2)
    row=lessons.reconsider_evidence_backed_development_lesson(r2['review_id'],expected_review_digest=r2['review_digest'],later_assessment_id=a['assessment_id'],expected_later_assessment_digest=a['assessment_digest'],later_quality_review_id=qr['review_id'],expected_later_quality_review_digest=qr['review_digest'],decision='retain',runtime_root=rt2)
    check(row.get('ok') is False); check(row.get('status')=='evidence_backed_lesson_reconsideration_ineligible_review')

# Public projections never expose raw requirement/evidence rows or private content.
rt=clone_runtime(base,'v1235-privacy'); c=prepare(rt); r=lessons.review_evidence_backed_development_lesson(c['candidate_id'],expected_candidate_digest=c['candidate_digest'],disposition='accept',runtime_root=rt)
candidate_payload=lessons.public_evidence_backed_development_lessons(runtime_root=rt)
review_payload=lessons.public_evidence_backed_development_lesson_reviews(runtime_root=rt)
for row in (candidate_payload.get('candidates') or []) + (review_payload.get('reviews') or []):
    check('requirements' not in row); check('evidence' not in row); check('criterion_digest' not in row); check('source_receipt_digest' not in row)
check(candidate_payload.get('private_content_exposed') is False); check(review_payload.get('private_content_exposed') is False)

# Authority remains absent across candidate, review, and reconsideration records.
for row in (a1, c, r, rec, later_c):
    check(row.get('ok'))
    for k in ('lesson_writes_cognition','lesson_is_execution_authority','project_mutation_authorized','test_execution_authorized','execution_session_launch_authorized','resume_authorized','queue_mutation_authorized','schedule_mutation_authorized','old_authority_reusable'):
        check(row.get(k) is False)

print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks)},sort_keys=True))
raise SystemExit(0 if all(checks) else 1)
