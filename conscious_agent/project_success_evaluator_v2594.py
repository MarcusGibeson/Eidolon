from __future__ import annotations
"""v2594 generic criterion evaluator; evidence only, never goal completion authority."""
from typing import Any, Mapping
import hashlib,json
CONTRACT_VERSION='v2594.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def _compare(kind:str,value:Any,target:Any)->bool:
    try:
        if kind=='less_than':return float(value)<float(target)
        if kind=='less_or_equal':return float(value)<=float(target)
        if kind=='greater_than':return float(value)>float(target)
        if kind=='greater_or_equal':return float(value)>=float(target)
        if kind=='equal':return value==target
        if kind=='boolean_true':return value is True
        if kind=='boolean_false':return value is False
        if kind=='max_zero':return float(value)<=0
    except (TypeError,ValueError):return False
    return False
def evaluate_project_success(contract:Mapping[str,Any],evidence:Mapping[str,Any])->dict[str,Any]:
    if contract.get('goal_digest')!=evidence.get('goal_digest') or contract.get('project_id')!=evidence.get('project_id'):
        return {'ok':False,'contract_version':CONTRACT_VERSION,'status':'evidence_binding_mismatch','goal_completed_automatically':False,'authority_granted':False}
    metrics=dict(evidence.get('current_metrics') or {});metrics.update(dict(evidence.get('verification') or {}));metrics.update(dict(evidence.get('governance') or {}))
    rows=[]
    for c in contract.get('criteria') or []:
        metric=str(c.get('metric') or '');value=metrics.get(metric);passed=_compare(str(c.get('comparison') or ''),value,c.get('target'))
        rows.append({'criterion_id':str(c.get('criterion_id') or ''),'metric':metric,'passed':passed,'required':bool(c.get('required',True)),'evidence_present':metric in metrics})
    failed=[r['criterion_id'] for r in rows if r['required'] and not r['passed']];complete=all(r['evidence_present'] for r in rows if r['required']);satisfied=complete and not failed
    out={'ok':True,'contract_version':CONTRACT_VERSION,'status':'criteria_satisfied' if satisfied else ('evidence_incomplete' if not complete else 'criteria_not_satisfied'),'project_id':str(contract.get('project_id') or ''),'goal_digest':str(contract.get('goal_digest') or ''),'criterion_results':rows,'passed_count':sum(r['passed'] for r in rows),'failed_required_criteria':failed,'evidence_complete':complete,'criteria_satisfied':satisfied,'project_completed_automatically':False,'operator_review_required':True,'installation_authorized':False,'release_authorized':False,'source_modified':False,'authority_granted':False}
    out['evaluation_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','evaluate_project_success']
