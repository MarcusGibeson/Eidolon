from __future__ import annotations

"""v1270.9 read-only Self-Development Alpha checkpoint."""
from pathlib import Path
from typing import Any
from checkpoint_registry import build_read_only_checkpoint_report
from self_development_alpha_foundations import ALPHA_DENIED_AUTHORITY
from self_development_alpha_reliability import inspect_self_development_alpha_health

CONTRACT_VERSION = "v1270.9"


def build_self_development_alpha_checkpoint(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    health = inspect_self_development_alpha_health(source_root=root)
    checks = {
        "foundations_present": (root / "conscious_agent/self_development_alpha_foundations.py").is_file(),
        "integration_present": (root / "conscious_agent/self_development_alpha.py").is_file(),
        "reliability_present": (root / "conscious_agent/self_development_alpha_reliability.py").is_file(),
        "v1261_v1269_chain_present": health.get("ok") is True,
        "checkpoint_is_read_only": True,
    }
    details = {
        "behavioral_evidence": ["tools/v1270_0_2_self_development_alpha_foundations_tests.py", "tools/v1270_3_5_self_development_alpha_integration_tests.py", "tools/v1270_6_8_self_development_alpha_reliability_tests.py"],
        "contract": ["inspect_and_evidence_backlog", "select_one_defensible_improvement", "compare_alternative_plans", "modify_only_disposable_self_copy", "select_and_run_trusted_tests", "bounded_repair_without_repeating_failure", "present_operator_review_packet", "no_self_update_authority"],
        "checkpoint_executes_provider": False, "checkpoint_executes_tests": False, "checkpoint_mutates_source": False, "checkpoint_applies_update": False,
        "next_bounded_unit": "v1271 Long-Running Work Sessions", "native_windows_validation": "desktop_review_required", **ALPHA_DENIED_AUTHORITY,
    }
    return build_read_only_checkpoint_report(version="1270.9", status="self_development_alpha_checkpoint_ready", checks=checks, details=details, source_root=root)


__all__ = ["build_self_development_alpha_checkpoint"]
