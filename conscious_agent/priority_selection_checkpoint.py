from __future__ import annotations

"""v1263.9 read-only Priority Selection checkpoint."""

from pathlib import Path
from typing import Any

from checkpoint_registry import build_read_only_checkpoint_report
from priority_selection_foundations import PRIORITY_DENIED_AUTHORITY
from priority_selection_reliability import inspect_priority_selection_health

CONTRACT_VERSION = "v1263.9"


def build_priority_selection_checkpoint(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    health = inspect_priority_selection_health(source_root=root)
    checks = {
        "priority_foundations_present": (root / "conscious_agent/priority_selection_foundations.py").is_file(),
        "priority_integration_present": (root / "conscious_agent/priority_selection.py").is_file(),
        "priority_reliability_present": (root / "conscious_agent/priority_selection_reliability.py").is_file(),
        "v1261_inspection_retained": (root / "conscious_agent/evidence_based_project_inspection.py").is_file(),
        "v1262_backlog_retained": (root / "conscious_agent/development_backlog_generation.py").is_file(),
        "all_health_checks_pass": health.get("ok") is True,
    }
    details = {
        "behavioral_evidence": [
            "tools/v1263_0_2_priority_selection_foundations_tests.py",
            "tools/v1263_3_5_priority_selection_integration_tests.py",
            "tools/v1263_6_8_priority_selection_reliability_tests.py",
        ],
        "priority_factor_contract": ["user_value", "reliability_impact", "urgency", "reversibility", "effort_cost", "uncertainty_cost", "risk_cost", "dependency_readiness"],
        "tie_handling": "explicit_no_defensible_selection",
        "development_proposal_created": False,
        "schedule_created": False,
        "provider_contacted": False,
        "commands_executed": False,
        "runtime_data_read": False,
        "project_modified": False,
        "native_windows_validation": "desktop_review_required",
        "next_bounded_unit": "v1264 Alternative Planning and Simulation",
        **PRIORITY_DENIED_AUTHORITY,
    }
    return build_read_only_checkpoint_report(
        version="1263.9",
        status="priority_selection_checkpoint_ready",
        checks=checks,
        details=details,
        source_root=root,
    )


__all__ = ["CONTRACT_VERSION", "build_priority_selection_checkpoint"]
