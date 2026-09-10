from __future__ import annotations
"""v2549 bounded verification duration drift intelligence."""
import hashlib,json,statistics
from typing import Any,Mapping,Sequence
from verification_history_v2547 import CONTRACT_VERSION as HISTORY_CONTRACT
CONTRACT_VERSION='v2549.0'
AUTHORITY={'timeout_change_authorized':False,'required_test_waiver_authorized':False,'release_authorized':False,'independent_authority_granted':False}
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def assess_duration_drift(test:str, rows:Sequence[Mapping[str,Any]], *, baseline_window:int=8,recent_window:int=4)->dict[str,Any]:
    vals=[float(r.get('elapsed_seconds') or 0.0) for r in rows if str(r.get('contract_version') or '')==HISTORY_CONTRACT and float(r.get('elapsed_seconds') or 0.0)>0]
    if len(vals)<max(4,recent_window+2): status='insufficient_history'; baseline=recent=ratio=0.0
    else:
        recent_vals=vals[-recent_window:]; prior=vals[:-recent_window][-baseline_window:]
        if not prior: status='insufficient_history'; baseline=recent=ratio=0.0
        else:
            baseline=statistics.median(prior); recent=statistics.median(recent_vals); ratio=(recent/baseline if baseline>0 else 0.0)
            status='severe_regression' if ratio>=2.0 and recent-baseline>=1.0 else 'regression' if ratio>=1.5 and recent-baseline>=0.5 else 'improved' if ratio<=0.7 else 'stable'
    out={'ok':True,'contract_version':CONTRACT_VERSION,'test':str(test)[:240],'status':status,'sample_count':len(vals),'baseline_median_seconds':round(baseline,3),'recent_median_seconds':round(recent,3),'duration_ratio':round(ratio,3),'advisory':('investigate_verification_performance' if status in {'regression','severe_regression'} else 'none'),'timeout_changed':False,'required_test_still_required':True,**AUTHORITY};out['assessment_digest']=_digest(out);return out
def assess_history_performance(history:Mapping[str,Sequence[Mapping[str,Any]]])->dict[str,Any]:
    tests=[assess_duration_drift(k,v) for k,v in sorted(history.items())]
    out={'ok':True,'contract_version':CONTRACT_VERSION,'tests':tests,'regression_count':sum(t['status'] in {'regression','severe_regression'} for t in tests),'severe_regression_count':sum(t['status']=='severe_regression' for t in tests),'timeouts_changed':0,**AUTHORITY};out['report_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','assess_duration_drift','assess_history_performance']
