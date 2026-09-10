from __future__ import annotations

"""v1264.9 read-only Alternative Planning and Simulation checkpoint."""

from pathlib import Path
from typing import Any

from checkpoint_registry import build_read_only_checkpoint_report
from alternative_planning_foundations import PLAN_DENIED_AUTHORITY
from alternative_planning_reliability import inspect_alternative_planning_health

CONTRACT_VERSION = "v1264.9"


def build_alternative_planning_checkpoint(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    health = inspect_alternative_planning_health(source_root=root)
    checks = {
        "alternative_planning_foundations_present": (root / "conscious_agent/alternative_planning_foundations.py").is_file(),
        "alternative_planning_integration_present": (root / "conscious_agent/alternative_planning.py").is_file(),
        "alternative_planning_reliability_present": (root / "conscious_agent/alternative_planning_reliability.py").is_file(),
        "v1261_inspection_retained": (root / "conscious_agent/evidence_based_project_inspection.py").is_file(),
        "v1262_backlog_retained": (root / "conscious_agent/development_backlog_generation.py").is_file(),
        "v1263_priority_retained": (root / "conscious_agent/priority_selection.py").is_file(),
        "all_health_checks_pass": health.get("ok") is True,
    }
    details = {
        "behavioral_evidence": [
            "tools/v1264_0_2_alternative_planning_foundations_tests.py",
            "tools/v1264_3_5_alternative_planning_integration_tests.py",
            "tools/v1264_6_8_alternative_planning_reliability_tests.py",
        ],
        "planning_factor_contract": ["success_confidence", "reversibility", "estimated_effort", "risk", "uncertainty"],
        "failure_mode_contract": ["failure_code", "likelihood", "impact", "mitigation_code", "falsification_condition", "predicted_epistemic_status"],
        "tie_handling": "explicit_no_defensible_plan",
        "development_proposal_created": False,
        "schedule_created": False,
        "provider_contacted": False,
        "commands_executed": False,
        "runtime_data_read": False,
        "project_modified": False,
        "self_modification_started": False,
        "native_windows_validation": "desktop_review_required",
        "next_bounded_unit": "v1265 Isolated Self-Modification",
        **PLAN_DENIED_AUTHORITY,
    }
    return build_read_only_checkpoint_report(
        version="1264.9",
        status="alternative_planning_simulation_checkpoint_ready",
        checks=checks,
        details=details,
        source_root=root,
    )


__all__ = ["CONTRACT_VERSION", "build_alternative_planning_checkpoint"]
