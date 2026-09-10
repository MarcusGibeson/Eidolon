from __future__ import annotations
"""v1268.9 read-only Operator Review Handoff checkpoint."""
from pathlib import Path
from typing import Any
from checkpoint_registry import build_read_only_checkpoint_report
from operator_review_handoff_foundations import REVIEW_DENIED_AUTHORITY
from operator_review_handoff_reliability import inspect_operator_review_handoff_health
CONTRACT_VERSION="v1268.9"
def build_operator_review_handoff_checkpoint(*,source_root: str | Path | None=None)->dict[str,Any]:
    root=Path(source_root or Path(__file__).resolve().parents[1]).resolve();health=inspect_operator_review_handoff_health(source_root=root)
    checks={"review_foundations_present":(root/'conscious_agent/operator_review_handoff_foundations.py').is_file(),"review_integration_present":(root/'conscious_agent/operator_review_handoff.py').is_file(),"review_reliability_present":(root/'conscious_agent/operator_review_handoff_reliability.py').is_file(),"v1267_repair_retained":(root/'conscious_agent/iterative_self_repair.py').is_file(),"health_checks_pass":health.get('ok') is True}
    details={"behavioral_evidence":["tools/v1268_0_2_operator_review_handoff_foundations_tests.py","tools/v1268_3_5_operator_review_handoff_integration_tests.py","tools/v1268_6_8_operator_review_handoff_reliability_tests.py"],"review_contract":["readable_changed_paths","verification_evidence","risk_summary","limitations","unresolved_uncertainty","rollback_instructions","non_authorizing_operator_disposition"],"tests_executed":False,"provider_contacted":False,"commands_executed":False,"active_source_modified":False,"candidate_workspace_modified":False,"next_bounded_unit":"v1269 Governed Self-Update","native_windows_validation":"desktop_review_required",**REVIEW_DENIED_AUTHORITY}
    return build_read_only_checkpoint_report(version='1268.9',status='operator_review_handoff_checkpoint_ready',checks=checks,details=details,source_root=root)
__all__=["CONTRACT_VERSION","build_operator_review_handoff_checkpoint"]
