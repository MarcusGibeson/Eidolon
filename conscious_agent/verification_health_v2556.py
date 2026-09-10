from __future__ import annotations
"""v2556 bounded verification-health projection for operator observability."""
import hashlib,json
from typing import Any,Mapping,Sequence
from historical_verification_feedback_v2552 import build_historical_verification_feedback
CONTRACT_VERSION='v2556.0'
AUTHORITY={'test_suppression_authorized':False,'required_test_waiver_authorized':False,'timeout_change_authorized':False,'release_authorized':False,'certification_authorized':False,'independent_authority_granted':False}
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def build_verification_health(history:Mapping[str,Sequence[Mapping[str,Any]]])->dict[str,Any]:
    fb=build_historical_verification_feedback(history)
    if fb['persistent_failure_count'] or fb['timeout_prone_count']: state='degraded'
    elif fb['intermittent_count'] or fb['performance_regression_count']: state='attention'
    else: state='nominal'
    out={'ok':True,'contract_version':CONTRACT_VERSION,'state':state,'test_count':fb['test_count'],'concern_count':fb['concern_count'],'persistent_failure_count':fb['persistent_failure_count'],'intermittent_count':fb['intermittent_count'],'timeout_prone_count':fb['timeout_prone_count'],'performance_regression_count':fb['performance_regression_count'],'summary':('Verification health degraded.' if state=='degraded' else 'Verification health needs attention.' if state=='attention' else 'Verification health is nominal or history is still sparse.'),'raw_test_output_stored':False,'required_tests_waived':0,**AUTHORITY};out['health_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_verification_health']
