from __future__ import annotations
"""v2592 generic, read-only project success contracts."""
from typing import Any, Mapping, Sequence
import hashlib,json
CONTRACT_VERSION='v2592.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_project_success_contract(*,project_id:str,goal_digest:str,criteria:Sequence[Mapping[str,Any]],non_goals:Sequence[str]=())->dict[str,Any]:
    pid=str(project_id or '').strip()[:160];gd=str(goal_digest or '').lower()
    if not pid:raise ValueError('project_id_required')
    if len(gd)!=64 or any(c not in '0123456789abcdef' for c in gd):raise ValueError('goal_digest_required')
    rows=[];seen=set()
    allowed={'less_than','less_or_equal','greater_than','greater_or_equal','equal','boolean_true','boolean_false','max_zero'}
    for raw in criteria[:32]:
        if not isinstance(raw,Mapping):continue
        cid=str(raw.get('criterion_id') or '').strip()[:120];kind=str(raw.get('comparison') or '')
        if not cid or cid in seen or kind not in allowed:continue
        seen.add(cid);rows.append({'criterion_id':cid,'metric':str(raw.get('metric') or cid)[:120],'comparison':kind,'target':raw.get('target'),'baseline':raw.get('baseline'),'required':bool(raw.get('required',True)),'evidence_source':str(raw.get('evidence_source') or 'current_evidence')[:80]})
    if not rows:raise ValueError('criteria_required')
    out={'ok':True,'contract_version':CONTRACT_VERSION,'project_id':pid,'goal_digest':gd,'criteria':rows,'criterion_count':len(rows),'non_goals':[str(x)[:160] for x in non_goals[:16]],'operator_review_required':True,'project_completion_authorized':False,'source_mutation_authorized':False,'action_execution_authorized':False,'authority_granted':False}
    out['contract_digest']=_digest(out);return out

def architecture_acceptance_to_success_contract(goal:Mapping[str,Any])->dict[str,Any]:
    a=goal.get('acceptance_criteria') if isinstance(goal.get('acceptance_criteria'),Mapping) else {}
    rows=[
      {'criterion_id':'target_line_count_reduced','metric':'line_count','comparison':'less_than','baseline':int(a.get('target_line_count_should_decrease') or 0),'target':int(a.get('target_line_count_should_decrease') or 0),'required':True,'evidence_source':'architecture_metrics'},
      {'criterion_id':'target_symbol_count_reduced','metric':'top_level_symbol_count','comparison':'less_than','baseline':int(a.get('target_top_level_symbol_count_should_decrease') or 0),'target':int(a.get('target_top_level_symbol_count_should_decrease') or 0),'required':True,'evidence_source':'architecture_metrics'},
      {'criterion_id':'no_new_dependency_cycles','metric':'dependency_cycle_count','comparison':'less_or_equal','target':int(a.get('baseline_dependency_cycle_count') or 0),'baseline':int(a.get('baseline_dependency_cycle_count') or 0),'required':True,'evidence_source':'architecture_metrics'},
      {'criterion_id':'no_unexplained_regressions','metric':'unexplained_regression_count','comparison':'max_zero','target':0,'required':True,'evidence_source':'verification'},
      {'criterion_id':'behavior_preserved','metric':'behavior_preserved','comparison':'boolean_true','target':True,'required':True,'evidence_source':'verification'},
      {'criterion_id':'governance_authority_unchanged','metric':'governance_authority_unchanged','comparison':'boolean_true','target':True,'required':True,'evidence_source':'governance'},
    ]
    return build_project_success_contract(project_id=str(goal.get('goal_id') or 'architecture_project'),goal_digest=str(goal.get('goal_evidence_digest') or ''),criteria=rows,non_goals=('automatic_completion','authority_expansion','unverified_behavior_claim'))
__all__=['CONTRACT_VERSION','build_project_success_contract','architecture_acceptance_to_success_contract']
