from __future__ import annotations

"""Canonical release evidence boundary extracted from self_maintenance.py in v1276.

The functions here are deterministic/read-only builders and validators. They preserve
the historical self_maintenance private call surface through explicit re-exports.
"""

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from release_metadata import RUNTIME_VERSION
from release_packaging import _package_name
from release_installation import build_package_privacy_scan, build_deterministic_release_manifest
from release_signature_primitives import SIGNING_STATUS_VALUES, SIGNING_PAYLOAD_SCHEMA_VERSION, _is_hex_sha256

CONTRACT_VERSION = "v1276.3"
AUTHORITY_FLAGS = {
    "provider_contact_authorized": False,
    "tool_execution_authorized": False,
    "project_mutation_authorized": False,
    "source_mutation_authorized": False,
    "approval_granted": False,
    "release_authorized": False,
}
SELF_MAINTENANCE_VERSION = RUNTIME_VERSION

def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")

def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def _is_metadata_drift_tolerant_path(path: str) -> bool:
    """Return True for source-only metadata files that may be rewritten by install/smoke checks.

    These files are still checked by portable metadata and privacy scans, but the frozen
    candidate hash deliberately excludes their volatile content so v27/v28 governance
    does not block on harmless workspace timestamp churn. Release governance should
    detect real source drift, not faint metadata footprints left by the smoke gremlin.
    """
    rel = path.replace(os.sep, "/")
    return rel in {"data/projects.json", "data/settings.json"} or (rel.startswith("data/workspaces/") and rel.endswith(".json"))


def _evidence_manifest_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [row for row in entries if not _is_metadata_drift_tolerant_path(str(row.get("path", "")))],
        key=lambda row: str(row.get("path", "")),
    )


def _canonical_json_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _canonical_manifest_payload(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None) -> dict[str, Any]:
    package_name = package_name or _package_name()
    manifest = build_deterministic_release_manifest(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False)
    entries = _evidence_manifest_entries(manifest.get("entries", []))
    files = [
        {"path": str(row.get("path", "")), "sha256": str(row.get("sha256", "")), "size": int(row.get("size", 0) or 0)}
        for row in entries
    ]
    payload = {
        "schema_version": "eidolon.canonical_manifest.v1",
        "project_name": "Eidolon",
        "release_version": SELF_MAINTENANCE_VERSION,
        "package_name": package_name,
        "package_profile": "source-only",
        "generated_at": _now(),
        "hash_algorithm": "sha256",
        "files": sorted(files, key=lambda item: item["path"]),
        "excluded_paths": sorted([".git", ".venv", "__pycache__", "reports", "data/release_package", "data/releases", "data/self_maintenance"]),
        "volatile_metadata_paths": sorted(["data/projects.json", "data/settings.json", "data/workspaces/*.json", "data/workspaces/command_profiles/*.json"]),
    }
    payload["deterministic_manifest_hash"] = _canonical_json_hash({k: v for k, v in payload.items() if k not in {"generated_at", "deterministic_manifest_hash"}})
    return payload


def _canonical_evidence_payload(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None) -> dict[str, Any]:
    """Build a lightweight canonical evidence object for signing preparation.

    This deliberately avoids rebuilding the full durable evidence archive so signing
    status commands stay responsive. Full evidence replay remains available through
    the v28/v29 evidence commands; v30 only needs stable signing-ready fields.
    """
    package_name = package_name or _package_name()
    package_sha = _sha256_file(Path(zip_path)) if zip_path and Path(zip_path).exists() else None
    manifest = _canonical_manifest_payload(project_id=project_id, package_name=package_name, zip_path=zip_path)
    privacy = build_package_privacy_scan(project_id=project_id, save=False)
    deterministic = build_deterministic_release_manifest(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False)
    gate_results = {
        "privacy": {"status": privacy.get("status"), "ok": privacy.get("ok"), "message": privacy.get("message")},
        "deterministic_manifest": {"status": deterministic.get("status"), "ok": deterministic.get("ok"), "message": deterministic.get("message")},
        "signing_status": {"status": "warn", "ok": True, "message": "Artifact is explicitly unsigned."},
    }
    rows = []
    for name, step in gate_results.items():
        rows.append({"name": name, "status": str(step.get("status", "warn")), "message": step.get("message", "")})
    payload = {
        "schema_version": "eidolon.release_evidence.v1",
        "release_version": SELF_MAINTENANCE_VERSION,
        "package_name": package_name,
        "package_sha256": package_sha,
        "manifest_sha256": manifest.get("deterministic_manifest_hash"),
        "gate_results": gate_results,
        "warnings": [row for row in rows if str(row.get("status", "")).lower() == "warn"],
        "blocked_items": [row for row in rows if str(row.get("status", "")).lower() == "blocked"],
        "verification_commands": [
            "python -m py_compile conscious_agent/*.py tools/smoke_check.py",
            "python conscious_agent/main.py --package-privacy-scan --readiness-json",
            "python conscious_agent/main.py --deterministic-release-manifest --readiness-json",
            "python conscious_agent/main.py --release-evidence-bundle --readiness-json",
            "python conscious_agent/main.py --release-signing-status --readiness-json",
        ],
        "signing_status": "unsigned",
        "signed": False,
        "operational_ok": True,
        "signature_valid": False,
        "signature_trusted": False,
        "safe_to_publish": False,
        "trust_level": "unsigned",
        "signature_algorithm": None,
        "signature": None,
        "public_key_fingerprint": None,
        "signed_at": None,
        "signed_by": None,
    }
    payload["evidence_hash"] = _canonical_json_hash({k: v for k, v in payload.items() if k != "evidence_hash"})
    return payload


def _validate_canonical_manifest_payload(payload: dict[str, Any], zip_path: str | None = None) -> list[dict[str, Any]]:
    required = ["schema_version", "project_name", "release_version", "package_name", "package_profile", "hash_algorithm", "files", "excluded_paths", "volatile_metadata_paths", "deterministic_manifest_hash"]
    rows: list[dict[str, Any]] = []
    missing = [key for key in required if key not in payload]
    rows.append({"name": "manifest-required-fields", "status": "pass" if not missing else "blocked", "message": f"missing={', '.join(missing) or 'none'}"})
    rows.append({"name": "manifest-schema-version", "status": "pass" if payload.get("schema_version") == "eidolon.canonical_manifest.v1" else "blocked", "message": str(payload.get("schema_version"))})
    rows.append({"name": "manifest-release-version", "status": "pass" if payload.get("release_version") == SELF_MAINTENANCE_VERSION else "blocked", "message": str(payload.get("release_version"))})
    rows.append({"name": "manifest-package-profile", "status": "pass" if payload.get("package_profile") == "source-only" else "blocked", "message": str(payload.get("package_profile"))})
    rows.append({"name": "manifest-hash-algorithm", "status": "pass" if payload.get("hash_algorithm") == "sha256" else "blocked", "message": str(payload.get("hash_algorithm"))})
    files = payload.get("files")
    if not isinstance(files, list):
        rows.append({"name": "manifest-files-list", "status": "blocked", "message": "files must be a list"})
        return rows
    paths = [str(item.get("path", "")) if isinstance(item, dict) else "" for item in files]
    rows.append({"name": "manifest-files-nonempty", "status": "pass" if files else "blocked", "message": f"{len(files)} file(s)"})
    rows.append({"name": "manifest-paths-sorted", "status": "pass" if paths == sorted(paths) else "blocked", "message": "file paths must be canonical sorted order"})
    rows.append({"name": "manifest-paths-unique", "status": "pass" if len(paths) == len(set(paths)) else "blocked", "message": "file paths must not repeat"})
    unsafe = [path for path in paths if not path or path.startswith("/") or ".." in Path(path).parts or "\\" in path]
    rows.append({"name": "manifest-path-safety", "status": "pass" if not unsafe else "blocked", "message": f"unsafe={', '.join(unsafe[:5]) or 'none'}"})
    bad_hashes = []
    bad_sizes = []
    for item in files:
        if not isinstance(item, dict):
            bad_hashes.append("<non-object>")
            continue
        if not _is_hex_sha256(item.get("sha256")):
            bad_hashes.append(str(item.get("path", "<unknown>")))
        if not isinstance(item.get("size"), int) or item.get("size") < 0:
            bad_sizes.append(str(item.get("path", "<unknown>")))
    rows.append({"name": "manifest-file-hashes", "status": "pass" if not bad_hashes else "blocked", "message": f"bad={', '.join(bad_hashes[:5]) or 'none'}"})
    rows.append({"name": "manifest-file-sizes", "status": "pass" if not bad_sizes else "blocked", "message": f"bad={', '.join(bad_sizes[:5]) or 'none'}"})
    expected_hash = _canonical_json_hash({k: v for k, v in payload.items() if k not in {"generated_at", "deterministic_manifest_hash"}})
    rows.append({"name": "manifest-hash-roundtrip", "status": "pass" if payload.get("deterministic_manifest_hash") == expected_hash else "blocked", "message": str(payload.get("deterministic_manifest_hash"))})
    rows.append({"name": "manifest-zip-supplied", "status": "pass" if (not zip_path or Path(zip_path).exists()) else "blocked", "message": str(zip_path or "zip not supplied")})
    return rows


def _validate_canonical_evidence_payload(payload: dict[str, Any], zip_path: str | None = None) -> list[dict[str, Any]]:
    required = ["schema_version", "release_version", "package_name", "package_sha256", "manifest_sha256", "evidence_hash", "gate_results", "warnings", "blocked_items", "verification_commands", "signing_status", "signed", "signature_algorithm", "signature", "public_key_fingerprint", "signature_trusted", "safe_to_publish"]
    rows: list[dict[str, Any]] = []
    missing = [key for key in required if key not in payload]
    rows.append({"name": "evidence-required-fields", "status": "pass" if not missing else "blocked", "message": f"missing={', '.join(missing) or 'none'}"})
    rows.append({"name": "evidence-schema-version", "status": "pass" if payload.get("schema_version") == "eidolon.release_evidence.v1" else "blocked", "message": str(payload.get("schema_version"))})
    rows.append({"name": "evidence-release-version", "status": "pass" if payload.get("release_version") == SELF_MAINTENANCE_VERSION else "blocked", "message": str(payload.get("release_version"))})
    rows.append({"name": "evidence-signing-status-enum", "status": "pass" if payload.get("signing_status") in SIGNING_STATUS_VALUES else "blocked", "message": str(payload.get("signing_status"))})
    package_hash_ok = _is_hex_sha256(payload.get("package_sha256")) if zip_path else payload.get("package_sha256") is None or _is_hex_sha256(payload.get("package_sha256"))
    rows.append({"name": "evidence-package-hash", "status": "pass" if package_hash_ok else "blocked", "message": str(payload.get("package_sha256") or "zip not supplied")})
    rows.append({"name": "evidence-manifest-hash", "status": "pass" if _is_hex_sha256(payload.get("manifest_sha256")) else "blocked", "message": str(payload.get("manifest_sha256"))})
    rows.append({"name": "evidence-gates-object", "status": "pass" if isinstance(payload.get("gate_results"), dict) else "blocked", "message": "gate_results must be an object"})
    rows.append({"name": "evidence-commands-list", "status": "pass" if isinstance(payload.get("verification_commands"), list) and payload.get("verification_commands") else "blocked", "message": f"{len(payload.get('verification_commands', [])) if isinstance(payload.get('verification_commands'), list) else 0} command(s)"})
    unsigned_nulls = payload.get("signing_status") == "unsigned" and payload.get("signed") is False and payload.get("signature_algorithm") is None and payload.get("signature") is None and payload.get("public_key_fingerprint") is None and payload.get("signature_trusted") is False
    rows.append({"name": "unsigned-null-invariants", "status": "pass" if unsigned_nulls else "blocked", "message": "unsigned releases must carry null signature fields and no trust"})
    rows.append({"name": "safe-to-publish-invariant", "status": "pass" if payload.get("safe_to_publish") is False else "blocked", "message": "v32.0 source package is not marked safe_to_publish without trusted detached verification"})
    expected_hash = _canonical_json_hash({k: v for k, v in payload.items() if k != "evidence_hash"})
    rows.append({"name": "evidence-hash-roundtrip", "status": "pass" if payload.get("evidence_hash") == expected_hash else "blocked", "message": str(payload.get("evidence_hash"))})
    return rows


def _signing_payload(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None) -> dict[str, Any]:
    package_name = package_name or _package_name()
    evidence = _canonical_evidence_payload(project_id=project_id, package_name=package_name, zip_path=zip_path)
    return {
        "schema_version": SIGNING_PAYLOAD_SCHEMA_VERSION,
        "project_name": "Eidolon",
        "release_version": SELF_MAINTENANCE_VERSION,
        "package_name": package_name,
        "package_sha256": evidence.get("package_sha256"),
        "manifest_sha256": evidence.get("manifest_sha256"),
        "evidence_sha256": evidence.get("evidence_hash"),
    }


__all__ = ["CONTRACT_VERSION", "AUTHORITY_FLAGS", "_is_metadata_drift_tolerant_path", "_evidence_manifest_entries", "_canonical_json_hash", "_canonical_manifest_payload", "_canonical_evidence_payload", "_validate_canonical_manifest_payload", "_validate_canonical_evidence_payload", "_signing_payload"]
