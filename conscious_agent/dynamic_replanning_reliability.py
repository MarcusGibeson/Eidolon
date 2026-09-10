from __future__ import annotations
from pathlib import Path
from typing import Any,Mapping
from dynamic_replanning_foundations import AUTHORITY_FLAGS
CONTRACT_VERSION="v1286.8"
def inspect_dynamic_replanning_health(*,source_root:str|Path|None=None)->dict[str,Any]:
 root=Path(source_root or Path(__file__).resolve().parents[1]).resolve();checks={"foundations":(root/'conscious_agent/dynamic_replanning_foundations.py').is_file(),"integration":(root/'conscious_agent/dynamic_replanning.py').is_file(),"v1231_dynamic_plan_revision":(root/'conscious_agent/dynamic_execution_plan_revision.py').is_file(),"v1285_goal_hierarchy":(root/'conscious_agent/hierarchical_goal_management_foundations.py').is_file(),"v1282_uncertainty":(root/'conscious_agent/calibrated_uncertainty_foundations.py').is_file(),"v1284_learning":(root/'conscious_agent/experiential_learning_foundations.py').is_file()};return {"ok":all(checks.values()),"checks":checks,"read_only":True,**AUTHORITY_FLAGS}
def compare_replan_candidates(a:Mapping[str,Any],b:Mapping[str,Any])->dict[str,Any]:return {"ok":bool(a.get("ok") and b.get("ok")),"deterministic_same_input":a.get("replan_digest")==b.get("replan_digest"),"original_intent_same":a.get("original_intent_digest")==b.get("original_intent_digest"),"completed_work_same":a.get("completed_milestone_codes")==b.get("completed_milestone_codes"),"authority_changed":False,**AUTHORITY_FLAGS}
def build_dynamic_replanning_handoff(*,source_root=None)->dict[str,Any]:
 h=inspect_dynamic_replanning_health(source_root=source_root);return {"ok":h["ok"],"next_bounded_unit":"v1287 Unified Conversation and Action","v1287_started":False,"native_windows_review":["restart_replan_determinism","interrupt_resume_completed_work_preservation","provider_outage_replan_without_replay","late_evidence_after_restart","long_path_campaign_replan"],**AUTHORITY_FLAGS}
__all__=["CONTRACT_VERSION","inspect_dynamic_replanning_health","compare_replan_candidates","build_dynamic_replanning_handoff"]
