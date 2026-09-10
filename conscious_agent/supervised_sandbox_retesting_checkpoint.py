from __future__ import annotations
"""Read-only v1183.8 governed sandbox retesting checkpoint."""
import hashlib,json,tempfile
from pathlib import Path
from supervised_sandbox_repair_draft_checkpoint import _lineage
from supervised_sandbox_repair_draft_foundations import draft_supervised_sandbox_repair
from supervised_sandbox_repair_review_materialization import review_repair_draft, materialize_reviewed_sandbox_repair
from supervised_sandbox_retesting import review_sandbox_retest, execute_reviewed_sandbox_retest, build_bounded_repair_result, sandbox_repair_result_public_summary
CONTRACT_VERSION='v1183.8'
def _digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def build_supervised_sandbox_retesting_checkpoint(*,source_root=None,runtime_root=None):
 checks=[]
 def req(v):checks.append(bool(v))
 before='def broken(:\n pass\n'; after='def fixed():\n return 1\n'; target='pkg/case.py'
 lineage=_lineage(target,before,status='failed',error_class='python_compile_failed')
 draft=draft_supervised_sandbox_repair(*lineage,before,after); req(draft.get('draft_status')=='private_draft_ready')
 review=review_repair_draft(draft,decision='approve',operator_actor='checkpoint-operator'); req(review.get('review_status')=='approved_for_sandbox_repair')
 with tempfile.TemporaryDirectory() as td,tempfile.TemporaryDirectory() as sd:
  sandbox=Path(td); source=Path(sd); p=sandbox/target;p.parent.mkdir(parents=True);p.write_text(before)
  mat=materialize_reviewed_sandbox_repair(draft,review,sandbox_root=sandbox,source_root=source,current_target_text=before,replacement_text=after);req(mat.get('materialization_status')=='materialized')
  rr=review_sandbox_retest(draft,mat,decision='approve',operator_actor='checkpoint-operator',requested_tests=['python_compile','content_digest_match']);req(rr.get('review_status')=='approved_for_sandbox_retest')
  retest=execute_reviewed_sandbox_retest(draft,mat,rr,sandbox_root=sandbox,source_root=source);req(retest.get('retest_status')=='passed');req(retest.get('tests_rerun') is True)
  result=build_bounded_repair_result(draft,mat,retest);req(result.get('repair_classification')=='repair_succeeded');req(result.get('production_source_modified') is False)
  public=sandbox_repair_result_public_summary(result); blob=json.dumps(public);req('def fixed' not in blob);req(public.get('authority_granted') is False)
 report={'schema_version':'1','contract_version':CONTRACT_VERSION,'checkpoint_id':'supervised-sandbox-retesting:v1183.8','status':'ready' if all(checks) else 'review_required','ok':all(checks),'passed':sum(checks),'total':len(checks),'read_only':True,'content_free':True,'governed_retesting_exercised':True,'before_after_evidence_exercised':True,'regression_detection_exercised':True,'bounded_repair_results_exercised':True,'production_source_modified':False,'source_application_authorized':False,'promotion_authorized':False,'release_authorized':False,'desktop_verification_deferred_until_v1200':True}
 report['structural_digest']=_digest(report);return report
