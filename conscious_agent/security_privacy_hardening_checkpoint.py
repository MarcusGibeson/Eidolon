from __future__ import annotations

"""v1278.9 read-only Security and Privacy Hardening checkpoint."""

from pathlib import Path
from checkpoint_registry import build_read_only_checkpoint_report
from security_privacy_hardening_foundations import AUTHORITY_FLAGS, CONTRACT_VERSION as F
from security_privacy_hardening import CONTRACT_VERSION as I
from security_privacy_hardening_reliability import CONTRACT_VERSION as R, inspect_security_privacy_hardening_health

CONTRACT_VERSION = "v1278.9"


def build_security_privacy_hardening_checkpoint(*, source_root=None):
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    health = inspect_security_privacy_hardening_health(source_root=root)
    tests = [
        "tools/v1278_0_2_security_privacy_hardening_foundations_tests.py",
        "tools/v1278_3_5_security_privacy_hardening_integration_tests.py",
        "tools/v1278_6_8_security_privacy_hardening_reliability_tests.py",
        "tools/v1278_9_security_privacy_hardening_checkpoint_tests.py",
    ]
    checks = {
        "foundations_contract_current": F == "v1278.2",
        "integration_contract_current": I == "v1278.5",
        "reliability_contract_current": R == "v1278.8",
        "security_privacy_health_ready": health.get("ok") is True,
        "all_v1278_test_surfaces_present": all((root / item).is_file() for item in tests),
        "v1275_packaging_lineage_present": (root / "conscious_agent/dependency_packaging_reliability.py").is_file(),
        "v1269_update_lineage_present": (root / "conscious_agent/governed_self_update.py").is_file(),
        "v1255_application_lineage_present": (root / "conscious_agent/controlled_application_rollback.py").is_file(),
        "v1247_secret_audit_lineage_present": (root / "conscious_agent/privacy_security_secret_management_audit.py").is_file(),
        "v1196_adversarial_authority_lineage_present": (root / "conscious_agent/adversarial_privacy_authority.py").is_file(),
    }
    details = {
        "next_bounded_unit": "v1279 Operator Experience",
        "v1279_started": False,
        "path_containment_hardened": True,
        "archive_structure_hardened": True,
        "provider_material_content_minimized": True,
        "generic_approval_remains_non_authorizing": True,
        "governed_update_authority_unchanged": True,
        "checkpoint_executes_provider": False,
        "checkpoint_executes_commands": False,
        "checkpoint_executes_tests": False,
        "checkpoint_executes_install": False,
        "checkpoint_executes_update": False,
        "checkpoint_mutates_source": False,
        "private_provider_payloads_required": False,
        **AUTHORITY_FLAGS,
    }
    return build_read_only_checkpoint_report(
        version="1278.9", status="security_privacy_hardening_checkpoint_ready",
        checks=checks, source_root=root, details=details,
    )


__all__ = ["CONTRACT_VERSION", "build_security_privacy_hardening_checkpoint"]
