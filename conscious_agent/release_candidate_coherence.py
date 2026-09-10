from __future__ import annotations

"""Read-only candidate/package handoff coherence for daily-use surfaces."""

from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

try:
    from release_archive_coherence import active_package_record, package_directory, verify_candidate_archive
    from release_candidate_identity import active_candidate, candidate_status
    from release_metadata import WORKING_SOURCE_VERSION
    from version_roles import build_version_role_contract, normalize_version
except ImportError:
    from release_archive_coherence import active_package_record, package_directory, verify_candidate_archive
    from release_candidate_identity import active_candidate, candidate_status
    from release_metadata import WORKING_SOURCE_VERSION
    from version_roles import build_version_role_contract, normalize_version

CANDIDATE_HANDOFF_CONTRACT_VERSION = "1"
RELEASE_PACKAGING_COHERENCE_CHECKPOINT_VERSION = "1"


def _kinds(rows: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    for row in rows or ():
        kind = str(row.get("kind") or "unknown").strip() or "unknown"
        counts[kind] += 1
    return [{"kind": kind, "count": count} for kind, count in sorted(counts.items())]


def _declared_role(role: str, version: str, source: str) -> dict[str, Any]:
    normalized = normalize_version(version)
    return {
        "role": role,
        "version": normalized,
        "status": "declared" if normalized else "unknown",
        "authoritative_evidence_supplied": bool(normalized),
        "source": source if normalized else "no direct authoritative evidence supplied",
        "content_free": True,
    }


def _safe_package_filename(value: Any) -> str:
    filename = str(value or "").strip()
    if not filename or Path(filename).name != filename or not filename.lower().endswith(".zip"):
        return ""
    return filename


def candidate_package_handoff_status(
    root_dir: str | Path | None = None,
    *,
    runtime_root: str | Path | None = None,
    installed_version: str = "",
    promoted_version: str = "",
    certified_version: str = "",
) -> dict[str, Any]:
    """Return bounded handoff state without changing source or mutable runtime data."""
    root = Path(root_dir or Path(__file__).resolve().parents[1]).resolve()
    candidate = candidate_status(root, runtime_root=runtime_root)
    candidate_record, _source_manifest = active_candidate(runtime_root)
    package_record = active_package_record(runtime_root)

    candidate_id = str(candidate_record.get("candidate_id") or candidate.get("candidate_id") or "")
    candidate_version = normalize_version(candidate_record.get("candidate_version") or candidate.get("candidate_version"))
    package_filename = _safe_package_filename(package_record.get("package_filename"))
    package_version = normalize_version(package_record.get("packaged_version"))

    package_verification: dict[str, Any] = {}
    package_contradictions: list[dict[str, Any]] = []
    if package_record and not package_filename:
        package_contradictions.append({"kind": "package_record_filename_invalid"})
    elif package_record:
        archive = package_directory(runtime_root) / "archives" / package_filename
        package_verification = verify_candidate_archive(
            root,
            archive,
            runtime_root=runtime_root,
            candidate_id=candidate_id or None,
        )
        package_contradictions.extend(package_verification.get("contradictions") or [])
        package_contradictions.extend(package_verification.get("structure_findings") or [])
        if not package_verification.get("ok"):
            verification_status = str(package_verification.get("status") or "verification_failed").strip() or "verification_failed"
            if verification_status == "archive_missing":
                package_contradictions.append({"kind": "package_archive_missing"})
            elif verification_status == "archive_unreadable":
                package_contradictions.append({"kind": "package_archive_unreadable"})
            elif not package_verification.get("contradictions") and not package_verification.get("structure_findings"):
                package_contradictions.append({"kind": "package_verification_failed"})

    package_present = bool(package_record)
    package_ok = bool(package_present and package_verification.get("ok"))
    if not package_present:
        package_status = "not_packaged"
    elif package_ok:
        package_status = "coherent"
    else:
        package_status = str(package_verification.get("status") or "contradiction_detected")

    role_contract = build_version_role_contract(
        root,
        installed_version=installed_version,
        candidate_version=candidate_version if candidate.get("status") == "frozen" else "",
        packaged_archive_name=package_filename if package_ok else "",
        promoted_version=promoted_version,
        certified_version=certified_version,
    )

    candidate_stale = candidate.get("status") == "stale"
    contradictions = list(package_contradictions)
    if candidate_stale:
        contradictions.append({"kind": "candidate_source_stale"})
    if candidate_record and candidate_record.get("candidate_id") != package_record.get("candidate_id") and package_record:
        contradictions.append({"kind": "candidate_package_identity_mismatch"})
    if package_record and package_version != candidate_version:
        contradictions.append({"kind": "candidate_package_version_mismatch"})

    if candidate_stale or contradictions:
        overall_status = "attention_required"
    elif candidate.get("status") == "frozen" and package_ok:
        overall_status = "candidate_and_package_coherent"
    elif candidate.get("status") == "frozen":
        overall_status = "candidate_frozen_not_packaged"
    else:
        overall_status = "not_frozen"

    return {
        "ok": overall_status not in {"attention_required"},
        "status": overall_status,
        "contract_version": CANDIDATE_HANDOFF_CONTRACT_VERSION,
        "working_source": {
            "role": "working_source",
            "version": normalize_version(WORKING_SOURCE_VERSION),
            "status": "current",
            "authoritative_evidence_supplied": True,
            "source": "working-source release metadata",
            "content_free": True,
        },
        "frozen_candidate": {
            "role": "frozen_candidate",
            "version": candidate_version,
            "candidate_id": candidate_id,
            "source_manifest_sha256": str(candidate_record.get("source_manifest_sha256") or ""),
            "status": str(candidate.get("status") or "not_frozen"),
            "present": bool(candidate.get("candidate_present")),
            "stale": candidate_stale,
            "source_tree_matches_manifest": bool(candidate.get("source_tree_matches_manifest")),
            "candidate_inferred_from_archive": False,
            "content_free": True,
        },
        "packaged_archive": {
            "role": "packaged_archive",
            "version": package_version,
            "candidate_id": str(package_record.get("candidate_id") or ""),
            "package_filename": package_filename,
            "archive_root": str(package_record.get("archive_root") or ""),
            "source_manifest_sha256": str(package_record.get("source_manifest_sha256") or ""),
            "archive_manifest_sha256": str(package_record.get("archive_manifest_sha256") or ""),
            "archive_sha256": str(package_record.get("archive_sha256") or ""),
            "status": package_status,
            "present": package_present,
            "coherent": package_ok,
            "source_only": bool(package_verification.get("source_only")) if package_present else False,
            "verification_is_native_certification": False,
            "content_free": True,
        },
        "installed_version": _declared_role("installed_version", installed_version, "explicit installed-state evidence supplied by caller"),
        "promoted_release": _declared_role("promoted_release", promoted_version, "explicit promotion evidence supplied by caller"),
        "certified_release": _declared_role("certified_release", certified_version, "explicit certification evidence supplied by caller"),
        "role_contract": role_contract,
        "contradictions": _kinds(contradictions),
        "contradiction_count": sum(row["count"] for row in _kinds(contradictions)),
        "candidate_records_external": True,
        "package_records_external": True,
        "contains_absolute_paths": False,
        "contains_source_paths": False,
        "contains_source_contents": False,
        "ordinary_conversation_affected": False,
        "provider_contacted": False,
        "installation_changed": False,
        "promotion_changed": False,
        "certification_performed": False,
        "verification_is_native_certification": False,
        "content_free": True,
        "read_only": True,
    }

def release_packaging_coherence_checkpoint(
    root_dir: str | Path | None = None,
    *,
    runtime_root: str | Path | None = None,
    installed_version: str = "",
    promoted_version: str = "",
    certified_version: str = "",
) -> dict[str, Any]:
    """Consolidate the exact v1095 candidate/package handoff contract read-only.

    This checkpoint persists nothing and grants no installation, promotion,
    certification, or native-platform authority.  It intentionally summarizes
    the existing candidate and package boundaries instead of creating a new
    release ledger or evidence store.
    """
    handoff = candidate_package_handoff_status(
        root_dir,
        runtime_root=runtime_root,
        installed_version=installed_version,
        promoted_version=promoted_version,
        certified_version=certified_version,
    )
    candidate = handoff.get("frozen_candidate") or {}
    package = handoff.get("packaged_archive") or {}
    role_rows = {str(row.get("role") or ""): row for row in (handoff.get("role_contract") or {}).get("roles", [])}
    expected_roles = {
        "working_source",
        "candidate",
        "packaged_archive",
        "installed",
        "promoted_release",
        "certified_release",
    }

    checks = {
        "candidate_frozen": candidate.get("status") == "frozen" and candidate.get("present") is True,
        "candidate_matches_working_source": normalize_version(candidate.get("version")) == normalize_version(WORKING_SOURCE_VERSION),
        "candidate_manifest_bound": bool(candidate.get("candidate_id") and candidate.get("source_manifest_sha256")),
        "candidate_source_fresh": candidate.get("source_tree_matches_manifest") is True and candidate.get("stale") is False,
        "package_present": package.get("present") is True,
        "package_coherent": package.get("coherent") is True and package.get("status") == "coherent",
        "candidate_package_identity_match": bool(candidate.get("candidate_id")) and candidate.get("candidate_id") == package.get("candidate_id"),
        "candidate_package_version_match": normalize_version(candidate.get("version")) == normalize_version(package.get("version")),
        "candidate_package_manifest_match": bool(candidate.get("source_manifest_sha256")) and candidate.get("source_manifest_sha256") == package.get("source_manifest_sha256"),
        "archive_root_exact": package.get("archive_root") == "Eidolon",
        "archive_manifest_bound": bool(package.get("archive_manifest_sha256")),
        "archive_digest_bound": bool(package.get("archive_sha256")),
        "source_only": package.get("source_only") is True,
        "six_release_roles_explicit": expected_roles <= set(role_rows),
        "candidate_not_inferred_from_archive": candidate.get("candidate_inferred_from_archive") is False,
        "package_check_not_native_certification": package.get("verification_is_native_certification") is False and handoff.get("verification_is_native_certification") is False,
        "records_external": handoff.get("candidate_records_external") is True and handoff.get("package_records_external") is True,
        "content_free_read_only": handoff.get("content_free") is True and handoff.get("read_only") is True,
        "ordinary_conversation_unaffected": handoff.get("ordinary_conversation_affected") is False,
        "no_authority_mutation": handoff.get("installation_changed") is False and handoff.get("promotion_changed") is False and handoff.get("certification_performed") is False,
    }
    failed_checks = sorted(name for name, passed in checks.items() if not passed)
    contradictions = list(handoff.get("contradictions") or [])
    ok = bool(handoff.get("ok")) and not contradictions and not failed_checks
    return {
        "ok": ok,
        "status": "coherent" if ok else "attention_required",
        "checkpoint_version": RELEASE_PACKAGING_COHERENCE_CHECKPOINT_VERSION,
        "working_source_version": normalize_version(WORKING_SOURCE_VERSION),
        "candidate_id": str(candidate.get("candidate_id") or ""),
        "candidate_version": normalize_version(candidate.get("version")),
        "source_manifest_sha256": str(candidate.get("source_manifest_sha256") or ""),
        "package_filename": str(package.get("package_filename") or ""),
        "packaged_version": normalize_version(package.get("version")),
        "archive_root": str(package.get("archive_root") or ""),
        "archive_manifest_sha256": str(package.get("archive_manifest_sha256") or ""),
        "archive_sha256": str(package.get("archive_sha256") or ""),
        "checks": checks,
        "failed_checks": failed_checks,
        "contradictions": contradictions,
        "installation_claimed": bool(normalize_version(installed_version)),
        "promotion_claimed": bool(normalize_version(promoted_version)),
        "certification_claimed": bool(normalize_version(certified_version)),
        "installation_changed": False,
        "promotion_changed": False,
        "certification_performed": False,
        "verification_is_native_certification": False,
        "provider_contacted": False,
        "ordinary_conversation_affected": False,
        "records_external": True,
        "content_free": True,
        "read_only": True,
    }

