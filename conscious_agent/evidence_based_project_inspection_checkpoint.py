from __future__ import annotations

"""v1261.9 read-only Evidence-Based Project Inspection checkpoint."""

from pathlib import Path
from typing import Any

from checkpoint_registry import build_read_only_checkpoint_report
from evidence_based_project_inspection_foundations import DENIED_AUTHORITY
from evidence_based_project_inspection_reliability import inspect_evidence_based_project_inspection_health

CONTRACT_VERSION = "v1261.9"


def build_evidence_based_project_inspection_checkpoint(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    health = inspect_evidence_based_project_inspection_health(source_root=root)
    checks = {
        "inspection_foundations_present": (root / "conscious_agent/evidence_based_project_inspection_foundations.py").is_file(),
        "assessment_integration_present": (root / "conscious_agent/evidence_based_project_inspection.py").is_file(),
        "reliability_surface_present": (root / "conscious_agent/evidence_based_project_inspection_reliability.py").is_file(),
        "all_health_checks_pass": health.get("ok") is True,
        "v1254_containment_retained": (root / "conscious_agent/isolated_coding_execution_foundations.py").is_file(),
        "v1256_session_surface_retained": (root / "conscious_agent/persistent_development_sessions.py").is_file(),
        "v1257_diagnostic_surface_retained": (root / "conscious_agent/diagnostic_repair_reasoning.py").is_file(),
    }
    details = {
        "epistemic_classes": ["observed", "inferred", "assumed", "unknown"],
        "evidence_sources": ["architecture", "tests", "documentation", "configuration", "runtime_health", "operator_feedback", "known_limitation", "development_session", "environment", "privacy_boundary"],
        "behavioral_evidence": [
            "tools/v1261_0_2_evidence_based_project_inspection_foundations_tests.py",
            "tools/v1261_3_5_evidence_based_project_inspection_integration_tests.py",
            "tools/v1261_6_8_evidence_based_project_inspection_reliability_tests.py",
        ],
        "native_windows_validation": "desktop_review_required",
        "next_bounded_unit": "v1262 Development Backlog Generation",
        "provider_contacted": False, "commands_executed": False, "tests_executed": False,
        "runtime_data_read": False, "development_proposal_created": False, "backlog_created": False,
        **DENIED_AUTHORITY,
    }
    return build_read_only_checkpoint_report(version="1261.9", status="evidence_based_project_inspection_checkpoint_ready", checks=checks, details=details, source_root=root)


__all__ = ["CONTRACT_VERSION", "build_evidence_based_project_inspection_checkpoint"]
