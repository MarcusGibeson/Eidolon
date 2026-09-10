from __future__ import annotations
"""v1279.9 read-only Operator Experience checkpoint."""
from pathlib import Path
from checkpoint_registry import build_read_only_checkpoint_report
from operator_experience_foundations import AUTHORITY_FLAGS, CONTRACT_VERSION as F
from operator_experience import CONTRACT_VERSION as I
from operator_experience_reliability import CONTRACT_VERSION as R, inspect_operator_experience_health

CONTRACT_VERSION = "v1279.9"


def build_operator_experience_checkpoint(*, source_root=None):
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    health = inspect_operator_experience_health(source_root=root)
    tests = [
        "tools/v1279_0_2_operator_experience_foundations_tests.py",
        "tools/v1279_3_5_operator_experience_integration_tests.py",
        "tools/v1279_6_8_operator_experience_reliability_tests.py",
        "tools/v1279_9_operator_experience_checkpoint_tests.py",
    ]
    checks = {
        "foundations_contract_current": F == "v1279.2",
        "integration_contract_current": I == "v1279.5",
        "reliability_contract_current": R == "v1279.8",
        "operator_experience_health_ready": health.get("ok") is True,
        "all_v1279_test_surfaces_present": all((root / x).is_file() for x in tests),
        "v1268_review_lineage_present": (root / "conscious_agent/operator_review_handoff.py").is_file(),
        "v1269_update_lineage_present": (root / "conscious_agent/governed_self_update.py").is_file(),
        "v1271_session_lineage_present": (root / "conscious_agent/long_running_work_sessions.py").is_file(),
        "v1272_recovery_lineage_present": (root / "conscious_agent/restart_crash_recovery.py").is_file(),
        "v1277_observability_lineage_present": (root / "conscious_agent/development_observability.py").is_file(),
        "v1278_security_lineage_present": (root / "conscious_agent/security_privacy_hardening.py").is_file(),
    }
    return build_read_only_checkpoint_report(
        version="1279.9", status="operator_experience_checkpoint_ready", checks=checks, source_root=root,
        details={
            "next_bounded_unit": "v1280 Reliability Checkpoint", "v1280_started": False,
            "dashboard_presents_plan_diff_tests_progress": True,
            "dashboard_presents_exact_authorization_without_granting_it": True,
            "dashboard_presents_pause_resume_cancel_recovery": True,
            "dashboard_presents_rollback_as_separately_governed": True,
            "dashboard_presents_uncertainty_and_review_packets": True,
            "generic_approval_remains_non_authorizing": True,
            "checkpoint_executes_provider": False, "checkpoint_executes_commands": False,
            "checkpoint_executes_tests": False, "checkpoint_executes_install": False,
            "checkpoint_executes_update": False, "checkpoint_mutates_source": False,
            "private_provider_payloads_required": False,
            **AUTHORITY_FLAGS,
        },
    )


__all__ = ["CONTRACT_VERSION", "build_operator_experience_checkpoint"]
