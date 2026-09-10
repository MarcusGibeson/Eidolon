from __future__ import annotations
"""v1279.6-v1279.8 dashboard/restart/usability reliability evidence."""
from pathlib import Path
from typing import Any

from operator_experience_foundations import AUTHORITY_FLAGS

CONTRACT_VERSION = "v1279.8"


def inspect_operator_experience_health(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    dashboard = (root / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8", errors="ignore") if (root / "conscious_agent" / "dashboard.py").is_file() else ""
    panel = (root / "conscious_agent" / "dashboard_operator_experience_panel.py").read_text(encoding="utf-8", errors="ignore") if (root / "conscious_agent" / "dashboard_operator_experience_panel.py").is_file() else ""
    checks = {
        "foundations_present": (root / "conscious_agent/operator_experience_foundations.py").is_file(),
        "integration_present": (root / "conscious_agent/operator_experience.py").is_file(),
        "reliability_present": (root / "conscious_agent/operator_experience_reliability.py").is_file(),
        "dashboard_panel_present": bool(panel),
        "dashboard_get_route_present": "/api/operator-experience/snapshots" in dashboard,
        "dashboard_control_route_present": "/api/operator-experience/control" in dashboard,
        "dashboard_panel_embedded": "_operator_experience_panel()" in dashboard,
        "generic_approval_warning_visible": "Generic approval does not authorize" in panel,
        "exact_authority_language_visible": "Exact authorization" in panel,
        "rollback_separate_language_visible": "separately governed" in panel,
        "uncertainty_surface_visible": "Uncertainty" in panel,
        "review_surface_visible": "Review packet" in panel,
        "v1277_observability_retained": (root / "conscious_agent/development_observability.py").is_file(),
        "v1278_security_retained": (root / "conscious_agent/security_privacy_hardening.py").is_file(),
    }
    return {"ok": all(checks.values()), "status": "operator_experience_health_ready" if all(checks.values()) else "operator_experience_health_blocked", "checks": checks, "read_only": True, "active_source_modified": False, **AUTHORITY_FLAGS}


def build_operator_experience_operator_handoff(*, source_root: str | Path | None = None) -> dict[str, Any]:
    health = inspect_operator_experience_health(source_root=source_root)
    return {
        "ok": health["ok"], "contract_version": CONTRACT_VERSION,
        "status": "operator_experience_operator_handoff_ready" if health["ok"] else "operator_experience_operator_handoff_blocked",
        "next_bounded_unit": "v1280 Reliability Checkpoint",
        "operator_surfaces": ["plan", "diff", "tests", "progress", "exact_authorization", "pause_resume_cancel", "recovery", "rollback", "uncertainty", "review_packet"],
        "native_windows_review": ["dashboard_restart_preserves_projection", "multi_tab_control_convergence", "long_path_runtime_records", "locked_runtime_record_failure_is_readable", "browser_keyboard_and_screen_reader_labels", "dashboard_close_does_not_change_authority", "recovery_control_after_force_kill"],
        "v1280_started": False,
        **AUTHORITY_FLAGS,
    }


__all__ = ["CONTRACT_VERSION", "inspect_operator_experience_health", "build_operator_experience_operator_handoff"]
