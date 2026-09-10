from __future__ import annotations

"""v1274.9 read-only Environment Awareness checkpoint."""

from pathlib import Path
from typing import Any

from checkpoint_registry import build_read_only_checkpoint_report
from environment_awareness_foundations import AUTHORITY_FLAGS
from environment_awareness_reliability import inspect_environment_awareness_health

CONTRACT_VERSION = "v1274.9"


def build_environment_awareness_checkpoint(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    health = inspect_environment_awareness_health(source_root=root)
    checks = {
        "foundations_present": (root / "conscious_agent/environment_awareness_foundations.py").is_file(),
        "integration_present": (root / "conscious_agent/environment_awareness.py").is_file(),
        "reliability_present": (root / "conscious_agent/environment_awareness_reliability.py").is_file(),
        "v1273_ownership_integration_retained": (root / "conscious_agent/ownership_concurrency.py").is_file(),
        "v1272_recovery_integration_retained": (root / "conscious_agent/restart_crash_recovery.py").is_file(),
        "v1271_session_integration_retained": (root / "conscious_agent/long_running_work_sessions.py").is_file(),
        "v1270_campaign_integration_retained": (root / "conscious_agent/self_development_alpha.py").is_file(),
        "checkpoint_is_read_only": True,
        "health_checks_pass": health.get("ok") is True,
    }
    details = {
        "behavioral_evidence": [
            "tools/v1274_0_2_environment_awareness_foundations_tests.py",
            "tools/v1274_3_5_environment_awareness_integration_tests.py",
            "tools/v1274_6_8_environment_awareness_reliability_tests.py",
        ],
        "contract": [
            "observed_inferred_assumed_unknown_preserved", "windows_path_awareness_without_host_guessing", "python_environment_observation",
            "port_permission_configuration_provider_process_resource_awareness", "privacy_minimized_environment_records",
            "stale_fact_refresh_required", "observed_only_sensitive_preflight", "v1273_lineage_binding", "no_authority_creation",
        ],
        "checkpoint_executes_provider": False,
        "checkpoint_executes_commands": False,
        "checkpoint_executes_tests": False,
        "checkpoint_executes_update": False,
        "checkpoint_mutates_source": False,
        "next_bounded_unit": "v1275 Dependency and Packaging Management",
        "native_windows_validation": "desktop_review_required",
        **AUTHORITY_FLAGS,
    }
    return build_read_only_checkpoint_report(version="1274.9", status="environment_awareness_checkpoint_ready", checks=checks, details=details, source_root=root)


__all__ = ["build_environment_awareness_checkpoint"]
