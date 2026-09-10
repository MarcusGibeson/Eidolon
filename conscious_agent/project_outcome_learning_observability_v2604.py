from __future__ import annotations
"""v2604 content-minimized observability for comparative project learning."""
from pathlib import Path
from typing import Any
try:
 from project_outcome_history_v2599 import load_project_outcome_history
 from project_strategy_reliability_v2600 import build_project_strategy_reliability
 from project_value_calibration_v2601 import build_project_value_calibration
 from project_strategy_learning_v2602 import build_project_strategy_learning_candidates
except ImportError:
 from project_outcome_history_v2599 import load_project_outcome_history
 from project_strategy_reliability_v2600 import build_project_strategy_reliability
 from project_value_calibration_v2601 import build_project_value_calibration
 from project_strategy_learning_v2602 import build_project_strategy_learning_candidates
CONTRACT_VERSION='v2604.0'
def build_project_outcome_learning_observability(runtime_root=None)->dict[str,Any]:
 h=load_project_outcome_history(runtime_root);r=build_project_strategy_reliability(h.get('rows') or []);c=build_project_value_calibration(h.get('rows') or []);l=build_project_strategy_learning_candidates(r,c);under=sum(1 for x in r.get('profiles') or [] if x.get('reliability')=='underperforming');state='attention' if under else ('learning' if h.get('rows') else 'no_history');return {'ok':True,'contract_version':CONTRACT_VERSION,'state':state,'project_count':len(h.get('rows') or []),'strategy_count':int(r.get('strategy_count') or 0),'underperforming_strategy_count':under,'candidate_count':int(l.get('candidate_count') or 0),'automatic_strategy_change_permitted':False,'raw_project_content_stored':False,'authority_granted':False}
__all__=['CONTRACT_VERSION','build_project_outcome_learning_observability']
