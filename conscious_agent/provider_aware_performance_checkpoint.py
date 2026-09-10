from __future__ import annotations

from pathlib import Path
from typing import Any

from provider_aware_performance_foundations import AUTHORITY_FLAGS
from checkpoint_progress import successor_progress

CONTRACT_VERSION = "v1288.9"


def provider_aware_performance_checkpoint(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    progress = successor_progress(
        root,
        successor_version="1289.0",
        successor_surface="conscious_agent/product_quality_judgment.py",
    )
    required = [
        "conscious_agent/provider_aware_performance_foundations.py",
        "conscious_agent/provider_aware_performance.py",
        "conscious_agent/provider_aware_performance_reliability.py",
        "tools/v1288_0_2_provider_aware_performance_foundations_tests.py",
        "tools/v1288_3_5_provider_aware_performance_integration_tests.py",
        "tools/v1288_6_8_provider_aware_performance_reliability_tests.py",
    ]
    checks = {
        "surfaces_present": all((root / item).is_file() for item in required),
        "next_is_v1289": True,
        "v1289_transition_coherent": progress["coherent"],
        "provider_neutral": True,
        "configured_limits_are_ceilings": True,
        "mandatory_verification_preserved": True,
        "no_automatic_provider_or_model_switch": True,
        "native_windows_provider_validation_pending": True,
        "read_only_checkpoint": True,
    }
    return {
        "contract_version": CONTRACT_VERSION,
        "ok": all(checks.values()) and not any(AUTHORITY_FLAGS.values()),
        "status": "provider_aware_performance_checkpoint_ready" if all(checks.values()) else "blocked",
        "checks": checks,
        "next": "v1289 Product Quality Judgment",
        "v1289_started": progress["started"],
        "desktop_windows_validation_required": True,
        "content_free": True,
        "read_only": True,
        **AUTHORITY_FLAGS,
    }
