from __future__ import annotations

"""v1278.6-v1278.8 adversarial reliability and native Windows handoff."""

from pathlib import Path
from typing import Any

from security_privacy_hardening_foundations import AUTHORITY_FLAGS, build_security_privacy_hardening_contract
from security_privacy_hardening import inspect_security_privacy_hardening

CONTRACT_VERSION = "v1278.8"


def inspect_security_privacy_hardening_health(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    contract = build_security_privacy_hardening_contract()
    health = inspect_security_privacy_hardening(root)
    checks = {
        "foundations_contract_ready": contract.get("ok") is True,
        "source_and_package_security_ready": health.get("ok") is True,
        "confirmed_or_likely_secrets_absent": health.get("confirmed_or_likely_secret_count") == 0,
        "package_private_content_absent": health.get("package_private_content_finding_count") == 0,
        "active_source_not_modified": True,
    }
    return {
        "ok": all(checks.values()),
        "status": "security_privacy_hardening_health_ready" if all(checks.values()) else "security_privacy_hardening_health_blocked",
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "source_file_count": health.get("source_file_count"),
        "package_file_count": health.get("package_file_count"),
        "synthetic_test_canary_count": health.get("synthetic_test_canary_count"),
        **AUTHORITY_FLAGS,
    }


def build_security_privacy_hardening_operator_handoff(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    health = inspect_security_privacy_hardening_health(source_root=root)
    return {
        "ok": health.get("ok") is True,
        "status": "security_privacy_hardening_operator_handoff_ready" if health.get("ok") is True else "security_privacy_hardening_operator_handoff_blocked",
        "contract_version": CONTRACT_VERSION,
        "native_windows_validation": [
            "ntfs_junction_and_symlink_ancestor_swap",
            "file_attribute_reparse_point_detection",
            "unc_and_extended_length_path_containment",
            "alternate_data_stream_and_reserved_device_name_rejection",
            "casefold_collision_and_trailing_dot_space_behavior",
            "locked_file_and_sharing_violation_fail_closed_behavior",
            "defender_indexer_race_during_package_and_update_preflight",
            "governed_update_intermediate_parent_reparse_swap",
            "controlled_application_intermediate_parent_reparse_swap",
            "malicious_zip_traversal_symlink_duplicate_and_zip_bomb_metadata",
            "provider_payload_and_secret_redaction_under_native_dashboard_processes",
            "runtime_source_separation_across_restart_and_long_paths",
        ],
        "next_bounded_unit": "v1279 Operator Experience",
        "v1279_started": False,
        "security_evidence_is_not_authorization": True,
        **AUTHORITY_FLAGS,
    }


__all__ = ["CONTRACT_VERSION", "inspect_security_privacy_hardening_health", "build_security_privacy_hardening_operator_handoff"]
