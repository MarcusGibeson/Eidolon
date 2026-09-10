from __future__ import annotations
"""v2554 bounded history-aware verification rerun policy."""
import hashlib,json
from typing import Any,Mapping
CONTRACT_VERSION='v2554.0'
AUTHORITY={'failure_erasure_authorized':False,'test_suppression_authorized':False,'required_test_waiver_authorized':False,'timeout_change_authorized':False,'release_authorized':False,'certification_authorized':False,'independent_authority_granted':False}
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def build_rerun_policy(failure:Mapping[str,Any], historical_assessment:Mapping[str,Any], *, reruns_already:int=0)->dict[str,Any]:
    if bool(failure.get('ok')): raise ValueError('failing_test_required')
    cls=str(historical_assessment.get('classification') or '')
    timed_out=bool(failure.get('timed_out'))
    allow=reruns_already<1 and cls in {'intermittent','timeout_prone'}
    reason='historical_intermittence' if cls=='intermittent' else 'historical_timeout_variability' if cls=='timeout_prone' else 'persistent_or_unknown_failure'
    if reruns_already>=1: reason='bounded_rerun_limit_reached'
    out={'ok':True,'contract_version':CONTRACT_VERSION,'test':str(failure.get('test') or '')[:240],'rerun_recommended':allow,'max_additional_reruns':1,'reruns_already':int(reruns_already),'reason':reason,'original_failure_retained':True,'rerun_pass_would_not_erase_failure':True,'required_test_still_required':True,**AUTHORITY};out['policy_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_rerun_policy']
