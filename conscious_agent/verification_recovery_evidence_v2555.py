from __future__ import annotations
"""v2555 reconciliation of original verification failure and bounded rerun evidence."""
import hashlib,json
from typing import Any,Mapping
CONTRACT_VERSION='v2555.0'
AUTHORITY={'failure_erasure_authorized':False,'required_test_waiver_authorized':False,'release_authorized':False,'certification_authorized':False,'candidate_applied':False,'independent_authority_granted':False}
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def reconcile_rerun(original:Mapping[str,Any], rerun:Mapping[str,Any]|None, *, history_classification:str)->dict[str,Any]:
    if bool(original.get('ok')): raise ValueError('original_failure_required')
    original_test=str(original.get('test') or '')
    if rerun is not None and str(rerun.get('test') or '')!=original_test: raise ValueError('rerun_test_mismatch')
    rerun_ok=bool(rerun and rerun.get('ok'))
    if rerun is None: status='unresolved_failure'
    elif rerun_ok and history_classification in {'intermittent','timeout_prone'}: status='intermittent_failure_confirmed_by_rerun'
    elif rerun_ok: status='failure_then_pass_requires_review'
    else: status='failure_reproduced'
    guidance='repair_or_manual_review' if not rerun_ok else 'manual_review_with_both_receipts'
    out={'ok':True,'contract_version':CONTRACT_VERSION,'test':original_test[:240],'status':status,'history_classification':str(history_classification)[:48],'original_failure_retained':True,'rerun_present':rerun is not None,'rerun_passed':rerun_ok,'verification_considered_clean':False,'guidance':guidance,'raw_output_stored':False,**AUTHORITY};out['evidence_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','reconcile_rerun']
