from __future__ import annotations

"""v1278.3-v1278.5 integration with existing supervised development surfaces."""

from pathlib import Path
from typing import Any, Iterable, Mapping

from dependency_packaging_foundations import build_reproducible_source_package_manifest
from isolated_self_modification_foundations import source_only_manifest
from package_integrity import package_privacy_summary_for_root, package_privacy_summary_for_zip
from privacy_security_secret_management_audit import scan_source_tree_for_secret_findings
from security_privacy_hardening_foundations import (
    AUTHORITY_FLAGS, build_provider_material_receipt, inspect_archive_structure,
    inspect_contained_path, inspect_runtime_source_separation,
    inspect_untrusted_project_surface, validate_exact_authorization_boundary,
    validate_untrusted_relative_path,
)

CONTRACT_VERSION = "v1278.5"


def guard_governed_update_paths(
    source_root: str | Path,
    candidate_root: str | Path,
    changed_files: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    source = Path(source_root).expanduser().resolve(strict=True)
    candidate = Path(candidate_root).expanduser().resolve(strict=True)
    if source == candidate or source in candidate.parents or candidate in source.parents:
        raise ValueError("security_update_source_candidate_overlap")
    count = 0
    for row in changed_files:
        relative = validate_untrusted_relative_path(str(row.get("relative_path") or ""))
        action = str(row.get("action") or "")
        inspect_contained_path(source, relative, require_exists=False, require_file=False)
        inspect_contained_path(candidate, relative, require_exists=action != "delete", require_file=action != "delete")
        count += 1
    if count == 0:
        raise ValueError("security_update_changes_required")
    return {
        "ok": True, "status": "governed_update_paths_security_ready",
        "changed_file_count": count, "raw_paths_returned": False,
        **AUTHORITY_FLAGS,
    }


def guard_controlled_application_paths(
    project_root: str | Path,
    candidate_root: str | Path,
    changes: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    project = Path(project_root).expanduser().resolve(strict=True)
    candidate = Path(candidate_root).expanduser().resolve(strict=True)
    if project == candidate or project in candidate.parents or candidate in project.parents:
        raise ValueError("security_application_project_candidate_overlap")
    count = 0
    for row in changes:
        relative = validate_untrusted_relative_path(str(row.get("relative_path") or ""))
        operation = str(row.get("operation") or row.get("action") or "")
        inspect_contained_path(project, relative, require_exists=False)
        inspect_contained_path(candidate, relative, require_exists=operation != "delete", require_file=operation != "delete")
        count += 1
    if count == 0:
        raise ValueError("security_application_changes_required")
    return {"ok": True, "status": "controlled_application_paths_security_ready", "changed_file_count": count, "raw_paths_returned": False, **AUTHORITY_FLAGS}


def inspect_security_privacy_hardening(
    source_root: str | Path,
    *, runtime_root: str | Path | None = None,
    package_path: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(source_root).expanduser().resolve(strict=True)
    source_manifest = source_only_manifest(root)
    package_manifest = build_reproducible_source_package_manifest(root)
    package_privacy = package_privacy_summary_for_root(root)
    secrets = scan_source_tree_for_secret_findings(root)
    runtime = inspect_runtime_source_separation(root, runtime_root) if runtime_root is not None else None
    archive = None
    zip_privacy = None
    if package_path is not None:
        archive = inspect_archive_structure(package_path)
        zip_privacy = package_privacy_summary_for_zip(package_path)
    checks = {
        "source_manifest_ready": bool(source_manifest.get("source_manifest_digest")),
        "package_manifest_ready": bool(package_manifest.get("package_manifest_digest")),
        "source_package_privacy_clear": package_privacy.get("ok") is True,
        "source_secret_scan_clear": secrets.get("confirmed_or_likely_count") == 0,
        "runtime_source_separate": runtime is None or runtime.get("ok") is True,
        "archive_structure_secure": archive is None or archive.get("ok") is True,
        "archive_privacy_clear": zip_privacy is None or zip_privacy.get("ok") is True,
    }
    return {
        "ok": all(checks.values()),
        "status": "security_privacy_hardening_ready" if all(checks.values()) else "security_privacy_hardening_blocked",
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "source_file_count": source_manifest.get("file_count"),
        "source_manifest_digest": source_manifest.get("source_manifest_digest"),
        "package_file_count": package_manifest.get("package_file_count"),
        "package_manifest_digest": package_manifest.get("package_manifest_digest"),
        "confirmed_or_likely_secret_count": secrets.get("confirmed_or_likely_count"),
        "synthetic_test_canary_count": (secrets.get("classification_counts") or {}).get("synthetic_test_canary", 0),
        "package_private_content_finding_count": package_privacy.get("private_content_finding_count", 0),
        "raw_paths_returned": False,
        "secret_values_returned": False,
        **AUTHORITY_FLAGS,
    }


def prepare_security_hardened_package_preflight(source_root: str | Path, output_path: str | Path) -> dict[str, Any]:
    root = Path(source_root).expanduser().resolve(strict=True)
    output = Path(output_path).expanduser().resolve(strict=False)
    if output == root or root in output.parents:
        raise ValueError("security_package_output_inside_source_rejected")
    health = inspect_security_privacy_hardening(root)
    return {
        "ok": health.get("ok") is True,
        "status": "security_hardened_package_preflight_ready" if health.get("ok") is True else "security_hardened_package_preflight_blocked",
        "source_manifest_digest": health.get("source_manifest_digest"),
        "package_manifest_digest": health.get("package_manifest_digest"),
        "output_path_digest": __import__("hashlib").sha256(str(output).encode()).hexdigest(),
        "source_modified": False,
        "package_created": False,
        **AUTHORITY_FLAGS,
    }


def public_provider_security_receipt(*, provider_identifier: str, provider_kind: str, status: str, raw_payload: str | bytes | None = None) -> dict[str, Any]:
    return build_provider_material_receipt(provider_identifier=provider_identifier, provider_kind=provider_kind, status=status, raw_payload=raw_payload)


def validate_generic_approval_is_non_authorizing(text: str, expected_exact_phrase: str) -> dict[str, Any]:
    return validate_exact_authorization_boundary(text, expected_exact_phrase)


def inspect_untrusted_project_for_development(project_root: str | Path) -> dict[str, Any]:
    return inspect_untrusted_project_surface(project_root)


__all__ = [
    "CONTRACT_VERSION", "guard_governed_update_paths", "guard_controlled_application_paths",
    "inspect_security_privacy_hardening", "prepare_security_hardened_package_preflight",
    "public_provider_security_receipt", "validate_generic_approval_is_non_authorizing",
    "inspect_untrusted_project_for_development",
]
