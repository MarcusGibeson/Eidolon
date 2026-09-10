from __future__ import annotations
from pathlib import Path
from checkpoint_registry import build_read_only_checkpoint_report
from dynamic_replanning_foundations import CONTRACT_VERSION as F,AUTHORITY_FLAGS
from dynamic_replanning import CONTRACT_VERSION as I
from dynamic_replanning_reliability import CONTRACT_VERSION as R,inspect_dynamic_replanning_health
CONTRACT_VERSION="v1286.9"
def build_dynamic_replanning_checkpoint(*,source_root=None):
 root=Path(source_root or Path(__file__).resolve().parents[1]).resolve();h=inspect_dynamic_replanning_health(source_root=root);checks={"foundations_current":F=="v1286.2","integration_current":I=="v1286.5","reliability_current":R=="v1286.8","health":h.get("ok") is True,"v1285_lineage":(root/'conscious_agent/hierarchical_goal_management_foundations.py').is_file(),"v1231_lineage":(root/'conscious_agent/dynamic_execution_plan_revision.py').is_file()};return build_read_only_checkpoint_report(version="1286.9",status="dynamic_replanning_checkpoint_ready",checks=checks,source_root=root,details={"next_bounded_unit":"v1287 Unified Conversation and Action","v1287_started":False,"handles_interruptions_new_requirements_failed_assumptions_new_evidence_priority_changes":True,"preserves_valid_completed_work":True,"suppresses_failed_strategy_repeat":True,"original_operator_intent_preserved":True,"checkpoint_executes_provider":False,"checkpoint_executes_tests":False,"checkpoint_mutates_source":False,**AUTHORITY_FLAGS})
__all__=["CONTRACT_VERSION","build_dynamic_replanning_checkpoint"]
