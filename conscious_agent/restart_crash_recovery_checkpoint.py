from __future__ import annotations

"""v1272.9 read-only Restart and Crash Recovery checkpoint."""

from pathlib import Path
from typing import Any

from checkpoint_registry import build_read_only_checkpoint_report
from restart_crash_recovery_foundations import AUTHORITY_FLAGS
from restart_crash_recovery_reliability import inspect_restart_crash_recovery_health

CONTRACT_VERSION = "v1272.9"


def build_restart_crash_recovery_checkpoint(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    health = inspect_restart_crash_recovery_health(source_root=root)
    checks = {
        "foundations_present": (root / "conscious_agent/restart_crash_recovery_foundations.py").is_file(),
        "integration_present": (root / "conscious_agent/restart_crash_recovery.py").is_file(),
        "reliability_present": (root / "conscious_agent/restart_crash_recovery_reliability.py").is_file(),
        "v1271_long_session_integration_retained": (root / "conscious_agent/long_running_work_sessions.py").is_file(),
        "v1270_campaign_integration_retained": (root / "conscious_agent/self_development_alpha.py").is_file(),
        "v1269_governed_update_boundary_retained": (root / "conscious_agent/governed_self_update.py").is_file(),
        "checkpoint_is_read_only": True,
        "health_checks_pass": health.get("ok") is True,
    }
    details = {
        "behavioral_evidence": [
            "tools/v1272_0_2_restart_crash_recovery_foundations_tests.py",
            "tools/v1272_3_5_restart_crash_recovery_integration_tests.py",
            "tools/v1272_6_8_restart_crash_recovery_reliability_tests.py",
        ],
        "contract": [
            "write_ahead_stage_intent", "durable_lower_lineage_completion", "crash_after_commit_reconciliation",
            "no_duplicate_provider_or_test_after_restart", "ambiguous_external_effect_fail_closed",
            "provider_outage_pause_return_without_automatic_retry", "stale_lease_restart_reconciliation",
            "corrupt_projection_quarantine", "read_only_governed_update_restart_inspection",
            "restart_does_not_create_or_reuse_authority",
        ],
        "checkpoint_executes_provider": False,
        "checkpoint_executes_tests": False,
        "checkpoint_executes_update": False,
        "checkpoint_mutates_source": False,
        "checkpoint_resumes_work": False,
        "next_bounded_unit": "v1273 Ownership and Concurrency",
        "native_windows_validation": "desktop_review_required",
        **AUTHORITY_FLAGS,
    }
    return build_read_only_checkpoint_report(
        version="1272.9", status="restart_crash_recovery_checkpoint_ready", checks=checks, details=details, source_root=root
    )


__all__ = ["build_restart_crash_recovery_checkpoint"]
