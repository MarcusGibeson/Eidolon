from __future__ import annotations
"""v2548 advisory flakiness intelligence from bounded verification history."""
import hashlib,json
from typing import Any,Mapping,Sequence
from verification_history_v2547 import CONTRACT_VERSION as HISTORY_CONTRACT
CONTRACT_VERSION='v2548.0'
AUTHORITY={'required_test_waiver_authorized':False,'test_suppression_authorized':False,'release_authorized':False,'certification_authorized':False,'independent_authority_granted':False}
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def classify_test_history(test:str, rows:Sequence[Mapping[str,Any]], *, min_samples:int=4)->dict[str,Any]:
    sample=[r for r in rows[-32:] if str(r.get('contract_version') or '')==HISTORY_CONTRACT]
    n=len(sample); passes=sum(bool(r.get('ok')) for r in sample); fails=n-passes; timeouts=sum(bool(r.get('timed_out')) for r in sample)
    transitions=sum(bool(sample[i].get('ok'))!=bool(sample[i-1].get('ok')) for i in range(1,n))
    if n<min_samples: cls='insufficient_history'
    elif passes==n: cls='stable_pass'
    elif fails==n and timeouts==0: cls='persistent_failure'
    elif timeouts>=max(2,n//2): cls='timeout_prone'
    elif passes and fails and transitions>=1: cls='intermittent'
    else: cls='mixed'
    confidence=0.0 if n==0 else min(1.0,n/8.0)
    advisory='none'
    if cls=='intermittent': advisory='rerun_and_investigate_nondeterminism'
    elif cls=='persistent_failure': advisory='repair_before_progress'
    elif cls=='timeout_prone': advisory='investigate_runtime_or_timeout_budget'
    out={'ok':True,'contract_version':CONTRACT_VERSION,'test':str(test)[:240],'classification':cls,'sample_count':n,'pass_count':passes,'failure_count':fails,'timeout_count':timeouts,'transition_count':transitions,'confidence':round(confidence,3),'advisory':advisory,'required_test_still_required':True,**AUTHORITY}
    out['assessment_digest']=_digest(out);return out
def classify_history(history:Mapping[str,Sequence[Mapping[str,Any]]])->dict[str,Any]:
    rows=[classify_test_history(k,v) for k,v in sorted(history.items())]
    out={'ok':True,'contract_version':CONTRACT_VERSION,'tests':rows,'test_count':len(rows),'intermittent_count':sum(r['classification']=='intermittent' for r in rows),'persistent_failure_count':sum(r['classification']=='persistent_failure' for r in rows),'timeout_prone_count':sum(r['classification']=='timeout_prone' for r in rows),'required_tests_waived':0,**AUTHORITY};out['report_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','classify_test_history','classify_history']
