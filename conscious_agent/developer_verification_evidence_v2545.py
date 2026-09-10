from __future__ import annotations
"""v2545 read-only developer evidence bridge for fast-verification feedback."""
import hashlib,json
from typing import Any,Mapping
from verification_feedback_v2544 import CONTRACT_VERSION as FEEDBACK_CONTRACT
CONTRACT_VERSION='v2545.0'
AUTHORITY={'source_mutation_authorized':False,'project_mutation_authorized':False,'approval_granted':False,'release_authorized':False,'certification_authorized':False,'independent_authority_granted':False}
def _digest(v:Any)->str: return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def build_developer_verification_evidence(feedback:Mapping[str,Any], *, candidate_ref:str='')->dict[str,Any]:
    if str(feedback.get('contract_version') or '')!=FEEDBACK_CONTRACT: raise ValueError('verification_feedback_required')
    fd=str(feedback.get('feedback_digest') or '')
    if len(fd)!=64: raise ValueError('feedback_digest_required')
    ref=' '.join(str(candidate_ref or '').split())[:160]
    failures=[]
    for row in list(feedback.get('failures') or [])[:8]:
        if not isinstance(row,Mapping): continue
        failures.append({'tier':int(row.get('tier') or 0),'test':str(row.get('test') or '')[:200],'status':str(row.get('status') or '')[:48],'timed_out':bool(row.get('timed_out'))})
    verified=bool(feedback.get('verification_ok'))
    out={'ok':True,'contract_version':CONTRACT_VERSION,'candidate_ref':ref,'verification_feedback_digest':fd,
         'fast_verification_passed':verified,'highest_fast_tier':int(feedback.get('stopped_after_tier') or 0),
         'failure_count':len(failures),'failures':failures,'developer_guidance':('continue_supervised_review' if verified else 'repair_candidate_before_further_progress'),
         'release_certified':False,'install_authorized':False,'candidate_applied':False,'raw_test_output_stored':False,**AUTHORITY}
    out['evidence_digest']=_digest(out); return out
__all__=['CONTRACT_VERSION','build_developer_verification_evidence']
