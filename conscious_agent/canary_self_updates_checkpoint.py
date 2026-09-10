from __future__ import annotations
"""v1296.9 read-only Canary Self-Updates checkpoint."""
from pathlib import Path
from typing import Any
from checkpoint_registry import build_read_only_checkpoint_report
from canary_self_updates_foundations import DENIED_AUTHORITY, MANDATORY_SIGNALS
from canary_self_updates_reliability import inspect_canary_surface_health
CONTRACT_VERSION = "v1296.9"

def build_canary_self_updates_checkpoint(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve(); health = inspect_canary_surface_health(source_root=root)
    checks = {
        "foundations_present": (root / "conscious_agent/canary_self_updates_foundations.py").is_file(),
        "integration_present": (root / "conscious_agent/canary_self_updates.py").is_file(),
        "reliability_present": (root / "conscious_agent/canary_self_updates_reliability.py").is_file(),
        "governed_update_retained": (root / "conscious_agent/governed_self_update.py").is_file(),
        "comprehensive_verification_retained": (root / "conscious_agent/comprehensive_verification.py").is_file(),
        "surface_health": health.get("ok") is True,
    }
    details = {
        "behavioral_evidence": [
            "tools/v1296_0_2_canary_self_updates_foundations_tests.py",
            "tools/v1296_3_5_canary_self_updates_integration_tests.py",
            "tools/v1296_6_8_canary_self_updates_reliability_tests.py",
        ],
        "mandatory_signals": list(MANDATORY_SIGNALS),
        "contract": ["separate_baseline_candidate_workspaces", "fixed_health_signal_comparison", "no_private_leakage", "no_shared_mutable_runtime", "no_regression", "native_windows_truth", "separate_v1269_exact_authorization"],
        "checkpoint_executes_canary": False,
        "checkpoint_applies_update": False,
        "checkpoint_mutates_source": False,
        "next_bounded_unit": "v1297 Automated Recovery",
        "native_windows_validation": "desktop_review_required",
        **DENIED_AUTHORITY,
    }
    return build_read_only_checkpoint_report(version="1296.9", status="canary_self_updates_checkpoint_ready", checks=checks, details=details, source_root=root)
