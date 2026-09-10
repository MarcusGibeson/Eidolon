from __future__ import annotations
"""v1267.9 read-only Iterative Self-Repair checkpoint."""
from pathlib import Path
from typing import Any
from checkpoint_registry import build_read_only_checkpoint_report
from iterative_self_repair_foundations import ITERATIVE_REPAIR_DENIED_AUTHORITY
from iterative_self_repair_reliability import inspect_iterative_self_repair_health
CONTRACT_VERSION="v1267.9"
def build_iterative_self_repair_checkpoint(*,source_root: str | Path | None=None)->dict[str,Any]:
    root=Path(source_root or Path(__file__).resolve().parents[1]).resolve();health=inspect_iterative_self_repair_health(source_root=root)
    checks={"repair_foundations_present":(root/"conscious_agent/iterative_self_repair_foundations.py").is_file(),"repair_integration_present":(root/"conscious_agent/iterative_self_repair.py").is_file(),"repair_reliability_present":(root/"conscious_agent/iterative_self_repair_reliability.py").is_file(),"v1266_selection_retained":(root/"conscious_agent/intelligent_test_selection.py").is_file(),"v1265_isolation_retained":(root/"conscious_agent/isolated_self_modification.py").is_file(),"health_checks_pass":health.get("ok") is True}
    details={"behavioral_evidence":["tools/v1267_0_2_iterative_self_repair_foundations_tests.py","tools/v1267_3_5_iterative_self_repair_integration_tests.py","tools/v1267_6_8_iterative_self_repair_reliability_tests.py"],"repair_contract":["selected_test_execution","content_minimized_failure_evidence","bounded_repair_attempts","strategy_novelty","trusted_test_integrity","active_source_immutability"],"tests_executed":False,"provider_contacted":False,"commands_executed":False,"active_source_modified":False,"candidate_workspace_modified":False,"next_bounded_unit":"v1268 Operator Review Handoff","native_windows_validation":"desktop_review_required",**ITERATIVE_REPAIR_DENIED_AUTHORITY}
    return build_read_only_checkpoint_report(version="1267.9",status="iterative_self_repair_checkpoint_ready",checks=checks,details=details,source_root=root)
__all__=["CONTRACT_VERSION","build_iterative_self_repair_checkpoint"]
