from __future__ import annotations
from pathlib import Path
from checkpoint_registry import build_read_only_checkpoint_report
from experiential_learning_foundations import CONTRACT_VERSION as F,AUTHORITY_FLAGS
from experiential_learning import CONTRACT_VERSION as I
from experiential_learning_reliability import CONTRACT_VERSION as R,inspect_experiential_learning_health
CONTRACT_VERSION="v1284.9"
def build_experiential_learning_checkpoint(*,source_root=None):
 root=Path(source_root or Path(__file__).resolve().parents[1]).resolve();h=inspect_experiential_learning_health(source_root=root);checks={"foundations_current":F=="v1284.2","integration_current":I=="v1284.5","reliability_current":R=="v1284.8","health":h.get("ok") is True,"v1283_lineage":(root/'conscious_agent/development_memory_relevance_foundations.py').is_file()};return build_read_only_checkpoint_report(version="1284.9",status="experiential_learning_checkpoint_ready",checks=checks,source_root=root,details={"next_bounded_unit":"v1285 Hierarchical Goal Management","v1285_started":False,"verified_outcomes_only":True,"stale_contradicted_context_inappropriate_lessons_suppressed":True,"lessons_not_permanent_rules":True,"checkpoint_executes_provider":False,"checkpoint_executes_tests":False,"checkpoint_mutates_source":False,**AUTHORITY_FLAGS})
__all__=["CONTRACT_VERSION","build_experiential_learning_checkpoint"]
