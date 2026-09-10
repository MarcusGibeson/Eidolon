from __future__ import annotations

"""v1262.9 read-only Development Backlog Generation checkpoint."""

from pathlib import Path
from typing import Any

from checkpoint_registry import build_read_only_checkpoint_report
from development_backlog_generation_foundations import BACKLOG_DENIED_AUTHORITY
from development_backlog_generation_reliability import inspect_development_backlog_generation_health

CONTRACT_VERSION = "v1262.9"


def build_development_backlog_generation_checkpoint(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    health = inspect_development_backlog_generation_health(source_root=root)
    checks = {
        "backlog_foundations_present": (root / "conscious_agent/development_backlog_generation_foundations.py").is_file(),
        "backlog_integration_present": (root / "conscious_agent/development_backlog_generation.py").is_file(),
        "backlog_reliability_present": (root / "conscious_agent/development_backlog_generation_reliability.py").is_file(),
        "v1261_inspection_retained": (root / "conscious_agent/evidence_based_project_inspection.py").is_file(),
        "all_health_checks_pass": health.get("ok") is True,
    }
    details = {"behavioral_evidence": ["tools/v1262_0_2_development_backlog_generation_foundations_tests.py", "tools/v1262_3_5_development_backlog_generation_integration_tests.py", "tools/v1262_6_8_development_backlog_generation_reliability_tests.py"],
               "backlog_item_contract": ["evidence_lineage", "acceptance_criteria", "dependencies", "risks", "uncertainty", "estimated_effort"],
               "priority_selected": False, "development_proposal_created": False, "provider_contacted": False, "commands_executed": False, "runtime_data_read": False,
               "native_windows_validation": "desktop_review_required", "next_bounded_unit": "v1263 Priority Selection", **BACKLOG_DENIED_AUTHORITY}
    return build_read_only_checkpoint_report(version="1262.9", status="development_backlog_generation_checkpoint_ready", checks=checks, details=details, source_root=root)


__all__ = ["CONTRACT_VERSION", "build_development_backlog_generation_checkpoint"]
