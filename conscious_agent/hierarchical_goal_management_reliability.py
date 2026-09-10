from __future__ import annotations
from pathlib import Path
from typing import Any,Mapping
from hierarchical_goal_management_foundations import AUTHORITY_FLAGS
CONTRACT_VERSION="v1285.8"
def inspect_hierarchical_goal_health(*,source_root:str|Path|None=None)->dict[str,Any]:
 root=Path(source_root or Path(__file__).resolve().parents[1]).resolve();checks={"foundations":(root/'conscious_agent/hierarchical_goal_management_foundations.py').is_file(),"integration":(root/'conscious_agent/hierarchical_goal_management.py').is_file(),"v1171_hierarchical_planning":(root/'conscious_agent/hierarchical_planning_runtime.py').is_file(),"v1264_alternative_planning":(root/'conscious_agent/alternative_planning.py').is_file(),"v1284_learning":(root/'conscious_agent/experiential_learning_foundations.py').is_file()};return {"ok":all(checks.values()),"checks":checks,"read_only":True,**AUTHORITY_FLAGS}
def compare_goal_hierarchies(before:Mapping[str,Any],after:Mapping[str,Any])->dict[str,Any]:return {"ok":bool(before.get("ok") and after.get("ok")),"intent_preserved":before.get("original_intent_digest")==after.get("original_intent_digest"),"milestone_change":int(after.get("milestone_count") or 0)-int(before.get("milestone_count") or 0),"authority_changed":False,**AUTHORITY_FLAGS}
def build_hierarchical_goal_handoff(*,source_root=None)->dict[str,Any]:
 h=inspect_hierarchical_goal_health(source_root=source_root);return {"ok":h["ok"],"next_bounded_unit":"v1286 Dynamic Replanning","v1286_started":False,"native_windows_review":["restart_preserves_intent_digest","durable_progress_reconstruction","long_path_campaign_goal_state","interruption_before_completion"],**AUTHORITY_FLAGS}
__all__=["CONTRACT_VERSION","inspect_hierarchical_goal_health","compare_goal_hierarchies","build_hierarchical_goal_handoff"]
