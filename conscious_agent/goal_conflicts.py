from __future__ import annotations
"""v1307 conflict detection without authority arbitration."""
from typing import Mapping,Sequence
from cognitive_coding_foundations import DENIED_AUTHORITY,digest
CONTRACT_VERSION='v1307.8'
def detect_goal_conflicts(*,operator_rules:Sequence[str]=(),repository_rules:Sequence[str]=(),plan_actions:Sequence[str]=(),runtime_constraints:Sequence[str]=()):
 rules=[('operator',x) for x in operator_rules]+[('repository',x) for x in repository_rules]+[('runtime',x) for x in runtime_constraints];conf=[]
 for action in plan_actions:
  a=str(action).lower()
  for source,rule in rules:
   r=str(rule).lower()
   if (r.startswith('deny:') and r[5:].strip() in a) or ('must not ' in r and r.split('must not ',1)[1].strip() in a):conf.append({'source':source,'action_digest':digest(action),'rule_digest':digest(rule),'conflict_code':'explicit_denial'})
 return {'ok':True,'status':'goal_conflict_detected' if conf else 'goal_conflict_clear','conflicts':conf,'conflict_count':len(conf),'silent_authority_choice':False,'requires_operator_resolution':bool(conf),'action_executed':False,**DENIED_AUTHORITY}
__all__=['CONTRACT_VERSION','detect_goal_conflicts']
