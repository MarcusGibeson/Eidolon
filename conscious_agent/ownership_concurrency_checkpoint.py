from __future__ import annotations

"""v1273.9 read-only Ownership and Concurrency checkpoint."""

from pathlib import Path
from typing import Any

from checkpoint_registry import build_read_only_checkpoint_report
from ownership_concurrency_foundations import AUTHORITY_FLAGS
from ownership_concurrency_reliability import inspect_ownership_concurrency_health

CONTRACT_VERSION = "v1273.9"


def build_ownership_concurrency_checkpoint(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    health = inspect_ownership_concurrency_health(source_root=root)
    checks = {
        "foundations_present": (root / "conscious_agent/ownership_concurrency_foundations.py").is_file(),
        "integration_present": (root / "conscious_agent/ownership_concurrency.py").is_file(),
        "reliability_present": (root / "conscious_agent/ownership_concurrency_reliability.py").is_file(),
        "v1272_recovery_integration_retained": (root / "conscious_agent/restart_crash_recovery.py").is_file(),
        "v1271_long_session_integration_retained": (root / "conscious_agent/long_running_work_sessions.py").is_file(),
        "v1270_campaign_integration_retained": (root / "conscious_agent/self_development_alpha.py").is_file(),
        "checkpoint_is_read_only": True,
        "health_checks_pass": health.get("ok") is True,
    }
    details = {
        "behavioral_evidence": [
            "tools/v1273_0_2_ownership_concurrency_foundations_tests.py",
            "tools/v1273_3_5_ownership_concurrency_integration_tests.py",
            "tools/v1273_6_8_ownership_concurrency_reliability_tests.py",
        ],
        "contract": [
            "one_live_owner_epoch_per_stage", "process_tab_queue_retry_duplicate_suppression", "bounded_lease_and_heartbeat",
            "expired_owner_fencing", "explicit_successor_transfer", "v1272_reconciliation_before_transferred_execution",
            "late_result_rejection", "durable_terminal_completion", "no_underlying_authority_creation",
        ],
        "checkpoint_executes_provider": False,
        "checkpoint_executes_tests": False,
        "checkpoint_executes_update": False,
        "checkpoint_mutates_source": False,
        "checkpoint_transfers_ownership": False,
        "next_bounded_unit": "v1274 Environment Awareness",
        "native_windows_validation": "desktop_review_required",
        **AUTHORITY_FLAGS,
    }
    return build_read_only_checkpoint_report(
        version="1273.9", status="ownership_concurrency_checkpoint_ready", checks=checks, details=details, source_root=root
    )


__all__ = ["build_ownership_concurrency_checkpoint"]
