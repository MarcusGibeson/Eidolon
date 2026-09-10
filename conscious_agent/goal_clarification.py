from __future__ import annotations
"""v1305 minimal consequential clarification."""
from typing import Any,Mapping
from cognitive_coding_foundations import DENIED_AUTHORITY,digest
CONTRACT_VERSION='v1305.8';CONSEQUENTIAL=('delete','destroy','publish','production','secret','credential','outside workspace','payment','install model','remove model')
def clarify_goal(goal:Mapping[str,Any],*,known_requirements:Mapping[str,Any]|None=None,reversible_choices=()):
 req=dict(known_requirements or {});missing=[k for k in ('workspace','acceptance') if not req.get(k)];risk=sorted({x for x in CONSEQUENTIAL if req.get('request_text') and x in str(req['request_text']).lower()});questions=[]
 if 'workspace' in missing:questions.append('selected_workspace_required')
 if risk:questions.append('consequential_scope_or_side_effect_confirmation_required')
 if 'acceptance' in missing and not risk:questions.append('acceptance_criteria_required')
 return {'ok':True,'status':'clarification_required' if questions else 'goal_clear_enough','goal_id':goal.get('goal_id'),'question_codes':questions[:3],'question_count':len(questions[:3]),'reversible_choice_digests':[digest(str(x)) for x in list(reversible_choices)[:16]],'reversible_choices_need_confirmation':False,'consequential_ambiguity_requires_confirmation':bool(risk),'action_executed':False,**DENIED_AUTHORITY}
__all__=['CONTRACT_VERSION','clarify_goal']
