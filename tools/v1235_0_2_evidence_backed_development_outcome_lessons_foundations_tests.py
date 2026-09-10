from __future__ import annotations

import hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))

import evidence_backed_development_outcome_lessons as lessons
import requirement_quality_assessment as quality
from v1234_quality_fixture import build_quality_fixture, clone_runtime, evidence_spec, requirement_spec

checks=[]
def check(v): checks.append(bool(v))
def signature():
    rows=[]
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc','.pyo'}:
            rows.append(f"{p.relative_to(ROOT).as_posix()}:{hashlib.sha256(p.read_bytes()).hexdigest()}")
    return hashlib.sha256('\n'.join(rows).encode()).hexdigest(),len(rows)

before=signature()
base_fixture=build_quality_fixture('v1235-foundations')
base=base_fixture['runtime']; ra=base_fixture['resource_assessment']; rr=base_fixture['resource_review']

def make(rt, states=None, ambiguous=False, disposition=None):
    assessment=quality.prepare_requirement_quality_assessment(
        ra['assessment_id'],expected_resource_assessment_digest=ra['assessment_digest'],
        resource_review_id=rr['review_id'],expected_resource_review_digest=rr['review_digest'],
        requirements=requirement_spec(ambiguous=ambiguous),evidence=evidence_spec(states),runtime_root=rt)
    assert assessment.get('ok'),assessment
    if disposition is None:
        disposition='accept_assessment' if assessment.get('all_required_requirements_satisfied') else 'request_remediation'
    review=quality.review_requirement_quality_assessment(
        assessment['assessment_id'],expected_assessment_digest=assessment['assessment_digest'],
        disposition=disposition,runtime_root=rt)
    assert review.get('ok'),review
    candidate=lessons.prepare_evidence_backed_development_lesson(
        assessment['assessment_id'],expected_assessment_digest=assessment['assessment_digest'],
        quality_review_id=review['review_id'],expected_quality_review_digest=review['review_digest'],runtime_root=rt)
    return assessment,review,candidate

contract=lessons.build_evidence_backed_development_outcome_lessons_contract()
for v in (
    contract.get('ok'),contract.get('contract_version')=='v1235.8',
    contract.get('milestone_name')=='Evidence-Backed Lessons from Development Outcomes',
    contract.get('roadmap_path')=='Balanced Mind-and-Action Path 3',
    contract.get('exact_quality_assessment_and_review_binding') is True,
    contract.get('deterministic_lesson_derivation') is True,
    contract.get('project_scoped_external_revisable_learning') is True,
    contract.get('later_evidence_reconsideration') is True,
    contract.get('accepted_lessons_do_not_write_cognition') is True,
    set(contract.get('lesson_codes') or [])==lessons.LESSON_CODES,
    set(contract.get('review_dispositions') or [])==lessons.REVIEW_DISPOSITIONS,
): check(v)
for k,e in lessons.AUTHORITY_FLAGS.items(): check(contract.get(k) is e)

rt=clone_runtime(base,'v1235-satisfied')
a,r,c=make(rt)
for v in (
    c.get('ok'),c.get('status')=='evidence_backed_development_lesson_ready_for_operator_review',
    c.get('assessment_id')==a.get('assessment_id'),c.get('quality_review_id')==r.get('review_id'),
    c.get('project_reference')==a.get('project_reference'),c.get('lesson_confidence')=='high',
    c.get('candidate_lesson_codes')==['retain_verified_approach','preserve_rollback_validation','preserve_goal_alignment'],
    c.get('deliberate_silence') is False,c.get('lesson_review_required') is True,
    len(c.get('candidate_digest',''))==64,len(c.get('evidence_basis_digest',''))==64,
): check(v)
for k,e in lessons.AUTHORITY_FLAGS.items(): check(c.get(k) is e)
for k in ('provider_contacted','commands_executed','tests_executed','project_modified','requirements_modified','queue_modified','schedule_modified','cognition_written','hidden_retry_created'):
    check(c.get(k) is False)
replay=lessons.prepare_evidence_backed_development_lesson(a['assessment_id'],expected_assessment_digest=a['assessment_digest'],quality_review_id=r['review_id'],expected_quality_review_digest=r['review_digest'],runtime_root=rt)
check(replay.get('ok')); check(replay.get('operation_status')=='replayed'); check(replay.get('candidate_digest')==c.get('candidate_digest'))

cases=(
    ({'core_behavior':'partial'},False,'medium',{'strengthen_partial_coverage'}),
    ({'core_behavior':'contradicts'},False,'low',{'repair_requirement_gap'}),
    ({'core_behavior':'missing'},False,'low',{'collect_missing_evidence','require_more_evidence'}),
    ({'performance_budget':'missing'},False,'low',{'clarify_acceptance_criteria','require_more_evidence'}),
    ({'performance_budget':'out_of_scope'},False,'high',{'retain_verified_approach','constrain_out_of_scope_work'}),
)
for i,(states,ambiguous,confidence,expected) in enumerate(cases):
    _,_,row=make(clone_runtime(base,f'v1235-case-{i}'),states=states,ambiguous=ambiguous)
    check(row.get('ok')); check(row.get('lesson_confidence')==confidence); check(expected.issubset(set(row.get('candidate_lesson_codes') or [])))

_,_,amb=make(clone_runtime(base,'v1235-ambiguous'),ambiguous=True)
check(amb.get('ok')); check('clarify_acceptance_criteria' in (amb.get('candidate_lesson_codes') or [])); check(amb.get('lesson_confidence')=='low')

# Ineligible quality dispositions remain blocked.
for i,disp in enumerate(('hold','reject')):
    rt2=clone_runtime(base,f'v1235-ineligible-{i}')
    a2=quality.prepare_requirement_quality_assessment(ra['assessment_id'],expected_resource_assessment_digest=ra['assessment_digest'],resource_review_id=rr['review_id'],expected_resource_review_digest=rr['review_digest'],requirements=requirement_spec(),evidence=evidence_spec(),runtime_root=rt2)
    r2=quality.review_requirement_quality_assessment(a2['assessment_id'],expected_assessment_digest=a2['assessment_digest'],disposition=disp,runtime_root=rt2)
    row=lessons.prepare_evidence_backed_development_lesson(a2['assessment_id'],expected_assessment_digest=a2['assessment_digest'],quality_review_id=r2['review_id'],expected_quality_review_digest=r2['review_digest'],runtime_root=rt2)
    check(row.get('ok') is False); check(row.get('status')=='evidence_backed_lesson_quality_review_not_eligible')

check(before==signature())
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks)},sort_keys=True))
raise SystemExit(0 if all(checks) else 1)
