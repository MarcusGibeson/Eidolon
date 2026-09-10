from __future__ import annotations
"""v2609 operator-facing structural summary for project outcome learning."""
from typing import Any
try:
 from project_outcome_learning_observability_v2604 import build_project_outcome_learning_observability
except ImportError:
 from project_outcome_learning_observability_v2604 import build_project_outcome_learning_observability
CONTRACT_VERSION='v2609.0'
def build_project_outcome_mind_observability(runtime_root=None)->dict[str,Any]:
 x=build_project_outcome_learning_observability(runtime_root);return {'ok':True,'contract_version':CONTRACT_VERSION,'state':x.get('state','no_history'),'project_count':int(x.get('project_count') or 0),'strategy_count':int(x.get('strategy_count') or 0),'underperforming_strategy_count':int(x.get('underperforming_strategy_count') or 0),'learning_candidate_count':int(x.get('candidate_count') or 0),'automatic_strategy_change_permitted':False,'automatic_plan_reprioritization_permitted':False,'raw_project_content_stored':False,'authority_granted':False}
__all__=['CONTRACT_VERSION','build_project_outcome_mind_observability']
