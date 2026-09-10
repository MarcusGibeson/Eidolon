from __future__ import annotations
"""v2552 combined historical verification confidence projection."""
import hashlib,json
from typing import Any,Mapping,Sequence
from verification_flakiness_v2548 import classify_history
from verification_performance_v2549 import assess_history_performance
CONTRACT_VERSION='v2552.0'
AUTHORITY={'required_test_waiver_authorized':False,'test_suppression_authorized':False,'timeout_change_authorized':False,'release_authorized':False,'certification_authorized':False,'independent_authority_granted':False}
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def build_historical_verification_feedback(history:Mapping[str,Sequence[Mapping[str,Any]]])->dict[str,Any]:
    flaky=classify_history(history); perf=assess_history_performance(history)
    concerns=[]
    by_perf={r['test']:r for r in perf['tests']}
    for r in flaky['tests']:
        p=by_perf.get(r['test'],{})
        if r['classification'] in {'intermittent','persistent_failure','timeout_prone'} or p.get('status') in {'regression','severe_regression'}:
            concerns.append({'test':r['test'],'flakiness':r['classification'],'performance':p.get('status','insufficient_history'),'required_test_still_required':True})
    status='attention_required' if concerns else 'nominal_or_insufficient_history'
    out={'ok':True,'contract_version':CONTRACT_VERSION,'status':status,'test_count':len(flaky['tests']),'concern_count':len(concerns),'concerns':concerns[:16],'intermittent_count':flaky['intermittent_count'],'persistent_failure_count':flaky['persistent_failure_count'],'timeout_prone_count':flaky['timeout_prone_count'],'performance_regression_count':perf['regression_count'],'required_tests_waived':0,'raw_test_output_stored':False,**AUTHORITY};out['feedback_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_historical_verification_feedback']
