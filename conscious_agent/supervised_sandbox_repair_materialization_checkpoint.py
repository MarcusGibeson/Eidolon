from __future__ import annotations
"""Read-only/reporting v1183.5 operator repair review and sandbox materialization checkpoint."""
import hashlib, json, tempfile
from pathlib import Path
from typing import Any
from checkpoint_registry import inspect_checkpoint_registry
from package_integrity import package_privacy_summary_for_root
from supervised_sandbox_repair_draft_checkpoint import _lineage
from supervised_sandbox_repair_draft_foundations import draft_supervised_sandbox_repair
from supervised_sandbox_repair_review_materialization import review_repair_draft, materialize_reviewed_sandbox_repair, sandbox_repair_materialization_public_summary

CONTRACT_VERSION = "v1183.5"

def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()

def build_supervised_sandbox_repair_materialization_checkpoint(*, source_root: str|Path|None=None, runtime_root: str|Path|None=None)->dict[str,Any]:
    source=Path(source_root or Path(__file__).resolve().parents[1]).resolve(); runtime=Path(runtime_root or source/'data')
    checks=[]
    def req(v): checks.append(bool(v))
    before='def broken(:\n    pass  # V1183B_SAMPLE_A\n'; after='def repaired():\n    return True  # V1183B_SAMPLE_B\n'
    lineage=_lineage('pkg/repair_case.py',before,status='failed',error_class='python_compile_failed')
    draft=draft_supervised_sandbox_repair(*lineage,before,after)
    review=review_repair_draft(draft,decision='approve',operator_actor='checkpoint-operator')
    req(review.get('review_status')=='approved_for_sandbox_repair'); req(review.get('content_free') is True)
    req(review.get('sandbox_repair_materialization_authorized') is True); req(review.get('retest_authorized') is False)
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); sandbox=root/'sandbox'; fake_source=root/'source'; fake_source.mkdir(); target=sandbox/'pkg/repair_case.py'; target.parent.mkdir(parents=True); target.write_text(before)
        result=materialize_reviewed_sandbox_repair(draft,review,sandbox_root=sandbox,source_root=fake_source,current_target_text=before,replacement_text=after)
        req(result.get('materialization_status')=='materialized'); req(target.read_text()==after)
        req(result.get('rollback_artifact_present') is True and result.get('rollback_artifact_digest_verified') is True)
        req(result.get('rollback_executed') is False); req(result.get('tests_rerun') is False); req(not any(fake_source.rglob('*')))
        replay=materialize_reviewed_sandbox_repair(draft,review,sandbox_root=sandbox,source_root=fake_source,current_target_text=before,replacement_text=after)
        req(replay.get('materialization_status')=='already_materialized'); req(replay.get('sandbox_file_written') is False)
        summary=sandbox_repair_materialization_public_summary(result); text=json.dumps(summary)
        req(summary.get('content_free') is True and summary.get('authority_granted') is False)
        req('V1183B_SAMPLE' not in text and 'replacement_text' not in summary and 'rollback_text' not in summary)
    req(review_repair_draft(draft,decision='reject',operator_actor='operator').get('review_status')=='rejected')
    req(review_repair_draft(draft,decision='defer',operator_actor='operator').get('review_status')=='deferred')
    req(review_repair_draft(draft,decision='approve',operator_actor='').get('block_reason')=='missing_operator_actor')
    req(review_repair_draft({**draft,'draft_digest':'0'*64},decision='approve',operator_actor='operator').get('block_reason')=='invalid_or_tampered_repair_draft')
    registry=inspect_checkpoint_registry(source_root=source); row=next((r for r in registry.get('checkpoints',[]) if r.get('checkpoint_id')=='supervised-sandbox-repair-materialization-checkpoint'),None)
    req(row is not None); req((row or {}).get('contract_version')==CONTRACT_VERSION)
    privacy=package_privacy_summary_for_root(source); req(privacy.get('ok')); req(int(privacy.get('forbidden_entry_count',privacy.get('forbidden_count',0)) or 0)==0); req(int(privacy.get('private_content_finding_count',0) or 0)==0)
    report={
      'schema_version':'1','contract_version':CONTRACT_VERSION,'checkpoint_id':'supervised-sandbox-repair-materialization:v1183.5',
      'status':'ready' if all(checks) else 'review_required','ok':all(checks),'passed':sum(checks),'total':len(checks),
      'read_only':True,'post_available':False,'content_free':True,'authority_preserved':True,
      'operator_repair_review_completed':True,'isolated_sandbox_repair_materialization_exercised':True,'rollback_evidence_exercised':True,
      'production_source_modified':False,'tests_rerun':False,'retest_authorized':False,'source_application_authorized':False,
      'provider_contacted':False,'model_operation_performed':False,'release_authorized':False,'desktop_verification_deferred_until_v1200':True,
    }
    report['structural_digest']=_digest(report); return report
