from __future__ import annotations
import hashlib, json, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
import adversarial_execution_cognitive_boundary as a
checks=[]
def check(v): checks.append(bool(v))
rt=tempfile.mkdtemp(prefix='eidolon-v1239-cognitive-')
rows=a.attack_registry().get('attack_cases') or []
selected=[row for row in rows if row.get('category') in {'cognitive_boundary','compound_boundary'}]
check(len(selected)==16)
for index,case in enumerate(selected):
    lineage={
        'plan':hashlib.sha256(f'plan{index}'.encode()).hexdigest(),
        'dependency':hashlib.sha256(f'dep{index}'.encode()).hexdigest(),
        'resource':hashlib.sha256(f'res{index}'.encode()).hexdigest(),
        'quality':hashlib.sha256(f'qual{index}'.encode()).hexdigest(),
        'lesson':hashlib.sha256(f'lesson{index}'.encode()).hexdigest(),
        'alignment':hashlib.sha256(f'align{index}'.encode()).hexdigest(),
        'orchestration':hashlib.sha256(f'orch{index}'.encode()).hexdigest(),
        'adapter':hashlib.sha256(f'adapter{index}'.encode()).hexdigest(),
    }
    result=a.prepare_adversarial_boundary_assessment('project_'+hashlib.sha256(f'c{index}'.encode()).hexdigest()[:16],attack_case_id=case['attack_case_id'],evidence_digest=hashlib.sha256(f'evidence{index}'.encode()).hexdigest(),lineage_digests=lineage,runtime_root=rt)
    check(result.get('ok')); check(result.get('category')==case.get('category')); check(result.get('assessment_state')=='attack_blocked'); check(result.get('authority_state')=='separate_not_granted'); check(result.get('lineage_entry_count')==8); check(result.get('lineage_digests_stored') is False); check(result.get('private_content_exposed') is False); check(result.get('cognition_written') is False); check(result.get('project_modified') is False); check(result.get('automatic_continuation_created') is False); check(result.get('hidden_retry_created') is False)
    review=a.review_adversarial_boundary_assessment(result['assessment_id'],expected_assessment_digest=result['assessment_record_digest'],disposition='acknowledge_blocked',runtime_root=rt)
    check(review.get('ok')); check(review.get('review_effect')=='interpretation_only_no_authority'); check(review.get('cognition_write_authorized') is False); check(review.get('old_authority_reusable') is False)
# Cross-contract audit remains green and dangerous authority never composes.
upstream=a.upstream_boundary_contracts(); check(upstream.get('ok')); check(upstream.get('upstream_contract_count')==8); check(not upstream.get('dangerous_authority_violations'))
for row in upstream.get('upstream_contracts') or []: check(not row.get('dangerous_authority_true'))
contract=a.build_adversarial_execution_cognitive_boundary_contract()
for key in ('missing_timeout_or_incomplete_evidence_never_passes','conversation_reflection_learning_goals_and_motivation_are_not_authority','advisory_records_never_compose_into_execution_authority','cross_project_session_queue_schedule_proposal_outcome_lineage_required','provider_output_untrusted','os_level_sandbox_not_claimed'):
    check(contract.get(key) is True)
# Private and unsafe lineage labels are rejected without writing a record.
for key in ('prompt','private_key','stdout','provider_payload','api_key'):
    out=a.prepare_adversarial_boundary_assessment('project_'+'f'*16,attack_case_id='privacy_exfiltration_via_public_record',evidence_digest='1'*64,lineage_digests={key:'2'*64},runtime_root=tempfile.mkdtemp()); check(not out.get('ok')); check(out.get('reason')=='private_lineage_key_blocked')
# Cross-project records remain distinct and immutable.
case='multi_project_lineage_swap'; evidence='3'*64; lineage={'session':'4'*64}
a1=a.prepare_adversarial_boundary_assessment('project_'+'1'*16,attack_case_id=case,evidence_digest=evidence,lineage_digests=lineage,runtime_root=rt)
a2=a.prepare_adversarial_boundary_assessment('project_'+'2'*16,attack_case_id=case,evidence_digest=evidence,lineage_digests=lineage,runtime_root=rt)
check(a1.get('ok') and a2.get('ok')); check(a1.get('assessment_id')!=a2.get('assessment_id')); check(a1.get('assessment_record_digest')!=a2.get('assessment_record_digest'))
# Public projections contain no raw evidence or lineage values.
public=a.public_adversarial_boundary_assessments(runtime_root=rt); check(public.get('ok')); payload=json.dumps(public,sort_keys=True); check(evidence not in payload); check('raw_content' not in payload); check('private_reasoning' not in payload)
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks)},sort_keys=True)); raise SystemExit(0 if all(checks) else 1)
