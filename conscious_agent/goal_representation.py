from __future__ import annotations
"""v1303 durable goal contracts."""
from typing import Any,Sequence
from cognitive_coding_foundations import DENIED_AUTHORITY,digest
CONTRACT_VERSION='v1303.8'
def create_goal(*,outcome:str,constraints:Sequence[str]=(),acceptance_criteria:Sequence[str]=(),non_goals:Sequence[str]=(),evidence_requirements:Sequence[str]=(),stop_conditions:Sequence[str]=(),workspace_digest:str='')->dict[str,Any]:
 outcome=str(outcome or '').strip();
 if not outcome:raise ValueError('goal_outcome_required')
 def ds(xs):return [digest(str(x)) for x in list(xs)[:64] if str(x).strip()]
 row={'contract_version':CONTRACT_VERSION,'outcome_digest':digest(outcome),'workspace_digest':str(workspace_digest or '')[:64],'constraint_digests':ds(constraints),'acceptance_criteria_digests':ds(acceptance_criteria),'non_goal_digests':ds(non_goals),'evidence_requirement_digests':ds(evidence_requirements),'stop_condition_digests':ds(stop_conditions),'goal_is_authority':False,'raw_goal_content_persisted':False,'state':'draft',**DENIED_AUTHORITY};row['goal_id']='goal_'+digest(row)[:24];row['goal_digest']=digest(row);return row
def validate_goal(row):
 body=dict(row);sup=body.pop('goal_digest','');return {'ok':sup==digest(body) and bool(row.get('outcome_digest')) and row.get('goal_is_authority') is False and row.get('raw_goal_content_persisted') is False and not any(bool(row.get(k)) for k in DENIED_AUTHORITY)}
__all__=['CONTRACT_VERSION','create_goal','validate_goal']
