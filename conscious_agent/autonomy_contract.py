from __future__ import annotations
"""v1310 autonomy-contract integration over profiles, grants, goals, and budgets."""
from typing import Mapping
from standing_session_grants import standing_session_allows
from session_budgets import consume_budget
from cognitive_coding_foundations import DENIED_AUTHORITY,digest
CONTRACT_VERSION='v1310.8'
def evaluate_routine_step(*,grant:Mapping,goal:Mapping,budget:Mapping,action_class:str,workspace_digest:str,cost:Mapping[str,int]|None=None,now_unix:int|None=None):
 same=workspace_digest==grant.get('workspace_digest')==goal.get('workspace_digest');allowed=same and not budget.get('exhausted') and standing_session_allows(grant,action_class,now_unix=now_unix);updated=consume_budget(budget,cost or {}) if allowed else dict(budget);allowed=allowed and not updated.get('exhausted');return {'ok':True,'status':'routine_step_permitted_under_standing_session' if allowed else 'routine_step_blocked','permitted':allowed,'workspace_bound':same,'profile_bound':grant.get('profile_digest')==(grant.get('profile_snapshot') or {}).get('profile_digest'),'new_prompt_required':False if allowed else True,'protected_action_allowed':False,'updated_budget':updated,'decision_digest':digest({'grant':grant.get('grant_id'),'goal':goal.get('goal_id'),'action':action_class,'allowed':allowed}),'action_executed':False,**DENIED_AUTHORITY}
__all__=['CONTRACT_VERSION','evaluate_routine_step']
