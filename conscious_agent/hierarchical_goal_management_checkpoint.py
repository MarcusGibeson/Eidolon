from __future__ import annotations
from pathlib import Path
from checkpoint_registry import build_read_only_checkpoint_report
from hierarchical_goal_management_foundations import CONTRACT_VERSION as F,AUTHORITY_FLAGS
from hierarchical_goal_management import CONTRACT_VERSION as I
from hierarchical_goal_management_reliability import CONTRACT_VERSION as R,inspect_hierarchical_goal_health
CONTRACT_VERSION="v1285.9"
def build_hierarchical_goal_management_checkpoint(*,source_root=None):
 root=Path(source_root or Path(__file__).resolve().parents[1]).resolve();h=inspect_hierarchical_goal_health(source_root=root);checks={"foundations_current":F=="v1285.2","integration_current":I=="v1285.5","reliability_current":R=="v1285.8","health":h.get("ok") is True,"v1171_lineage":(root/'conscious_agent/hierarchical_planning_runtime.py').is_file()};return build_read_only_checkpoint_report(version="1285.9",status="hierarchical_goal_management_checkpoint_ready",checks=checks,source_root=root,details={"next_bounded_unit":"v1286 Dynamic Replanning","v1286_started":False,"objective_decomposed_to_milestones_tasks_tests_recovery_completion":True,"original_operator_intent_preserved":True,"hierarchy_is_not_execution_authority":True,"checkpoint_executes_provider":False,"checkpoint_executes_tests":False,"checkpoint_mutates_source":False,**AUTHORITY_FLAGS})
__all__=["CONTRACT_VERSION","build_hierarchical_goal_management_checkpoint"]
