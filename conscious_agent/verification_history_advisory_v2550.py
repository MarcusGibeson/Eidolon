from __future__ import annotations
"""v2550 history-aware verification advisories.

Annotates an existing tiered verification plan using bounded history intelligence.
It cannot remove tests, waive failures, change timeouts, or certify releases.
"""
import hashlib,json
from typing import Any,Mapping,Sequence
from verification_flakiness_v2548 import classify_test_history
from verification_performance_v2549 import assess_duration_drift
CONTRACT_VERSION='v2550.0'
AUTHORITY={'test_suppression_authorized':False,'required_test_waiver_authorized':False,'timeout_change_authorized':False,'release_authorized':False,'certification_authorized':False,'independent_authority_granted':False}
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def advise_plan(plan:Mapping[str,Any], history:Mapping[str,Sequence[Mapping[str,Any]]])->dict[str,Any]:
    if not isinstance(plan,Mapping) or not isinstance(plan.get('tiers'),Mapping): raise ValueError('tiered_plan_required')
    selected=[]
    for tier in (1,2):
        row=plan['tiers'].get(str(tier),plan['tiers'].get(tier,{}))
        if isinstance(row,Mapping): selected.extend(str(x) for x in list(row.get('tests') or []))
    advisories=[]
    for test in selected:
        rows=list(history.get(test) or [])
        flaky=classify_test_history(test,rows)
        perf=assess_duration_drift(test,rows)
        priority='normal'; action='run_as_selected'
        if flaky['classification']=='persistent_failure': priority='critical'; action='repair_before_progress'
        elif flaky['classification'] in {'intermittent','timeout_prone'}: priority='high'; action='run_as_selected_then_rerun_on_failure'
        elif perf['status'] in {'regression','severe_regression'}: priority='high'; action='run_as_selected_and_investigate_duration'
        advisories.append({'test':test,'priority':priority,'action':action,'flakiness':flaky['classification'],'performance':perf['status'],'required_test_still_required':True})
    out={'ok':True,'contract_version':CONTRACT_VERSION,'selected_tests':selected,'selected_test_count':len(selected),'advisories':advisories,'removed_tests':[],'added_waivers':[],'timeouts_changed':False,'plan_digest':str(plan.get('plan_digest') or ''),**AUTHORITY};out['advisory_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','advise_plan']
