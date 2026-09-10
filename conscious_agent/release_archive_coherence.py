from __future__ import annotations

"""Deterministic candidate archive creation and exact manifest coherence."""

from collections import Counter, defaultdict
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Any, Iterable, Mapping
import zipfile

try:
    from package_integrity import package_privacy_summary_for_zip, source_package_bytes
    from release_candidate_identity import EXPECTED_ARCHIVE_ROOT, active_candidate, atomic_json, candidate_status, canonical_candidate_archive_name, digest_payload, normalize_version, read_json, runtime_data_root, sha256_bytes, sha256_file, utc_now
    from version_roles import version_from_artifact_name
except ImportError:
    from package_integrity import package_privacy_summary_for_zip, source_package_bytes
    from release_candidate_identity import (
        EXPECTED_ARCHIVE_ROOT,
        active_candidate,
        atomic_json,
        candidate_status,
        canonical_candidate_archive_name,
        digest_payload,
        normalize_version,
        read_json,
        runtime_data_root,
        sha256_bytes,
        sha256_file,
        utc_now,
    )
    from version_roles import version_from_artifact_name

ARCHIVE_COHERENCE_CONTRACT_VERSION = "1"
RUNTIME_PACKAGE_DIRECTORY = "candidate_packages"
ARCHIVE_MANIFEST_SCHEMA = "eidolon-archive-manifest-v1"
PACKAGE_RECORD_SCHEMA = "eidolon-package-record-v1"
DETERMINISTIC_ZIP_TIMESTAMP = (2020, 1, 1, 0, 0, 0)
NESTED_ARCHIVE_SUFFIXES = {".zip", ".tar", ".tgz", ".gz", ".bz2", ".xz", ".7z", ".rar"}
BYTECODE_SUFFIXES = {".pyc", ".pyo"}
PRIVATE_BACKUP_SUFFIXES = {".bak", ".backup", ".orig", ".old"}
CREDENTIAL_FILENAMES = {".env", "credentials.json", "secrets.json", "id_rsa", "id_ed25519"}
CREDENTIAL_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}
_VERSION_ASSIGNMENT = re.compile(r'^WORKING_SOURCE_VERSION\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)


def package_directory(runtime_root: str | Path | None = None) -> Path:
    return runtime_data_root(runtime_root) / RUNTIME_PACKAGE_DIRECTORY


def archive_manifest_from_rows(
    version: str,
    candidate_id: str,
    source_manifest_sha256: str,
    rows: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    entries = [
        {"path": str(row["path"]), "sha256": str(row["sha256"]), "size": int(row["size"])}
        for row in rows
    ]
    payload = {
        "schema": ARCHIVE_MANIFEST_SCHEMA,
        "contract_version": ARCHIVE_COHERENCE_CONTRACT_VERSION,
        "packaged_version": normalize_version(version),
        "candidate_id": candidate_id,
        "source_manifest_sha256": source_manifest_sha256,
        "archive_root": EXPECTED_ARCHIVE_ROOT,
        "entry_count": len(entries),
        "entries": sorted(entries, key=lambda row: row["path"]),
        "contains_absolute_paths": False,
        "contains_source_contents": False,
    }
    payload["archive_manifest_sha256"] = digest_payload(payload)
    return payload


def deterministic_zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, DETERMINISTIC_ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    permissions = 0o755 if PurePosixPath(name).suffix.lower() in {".sh", ".command"} else 0o644
    info.external_attr = (stat.S_IFREG | permissions) << 16
    return info


def build_candidate_archive(
    root_dir: str | Path,
    *,
    runtime_root: str | Path | None = None,
    destination_dir: str | Path | None = None,
    candidate_id: str | None = None,
) -> dict[str, Any]:
    """Build deterministic bytes without installing, promoting, or certifying."""
    root = Path(root_dir).resolve()
    status = candidate_status(root, runtime_root=runtime_root)
    if not status.get("ok") or status.get("status") != "frozen":
        return {"ok": False, "status": "candidate_not_fresh", "content_free": True}
    if candidate_id and candidate_id != status.get("candidate_id"):
        return {"ok": False, "status": "candidate_id_mismatch", "content_free": True}

    record, source_manifest = active_candidate(runtime_root)
    version = normalize_version(record.get("candidate_version"))
    selected_candidate_id = str(record.get("candidate_id") or "")
    package_name = canonical_candidate_archive_name(version, selected_candidate_id)
    destination = Path(destination_dir).resolve() if destination_dir else package_directory(runtime_root) / "archives"
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / package_name
    temp = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    expected_entries = {
        str(row["path"]): row
        for row in source_manifest.get("entries", [])
        if isinstance(row, dict) and row.get("path")
    }
    archive_rows: list[dict[str, Any]] = []

    try:
        with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9, strict_timestamps=True) as archive:
            for relative in sorted(expected_entries):
                payload = source_package_bytes(root, relative)
                expected = expected_entries[relative]
                if sha256_bytes(payload) != expected.get("package_sha256") or len(payload) != expected.get("package_size"):
                    raise RuntimeError(f"source changed before packaging: {relative}")
                archive_name = f"{EXPECTED_ARCHIVE_ROOT}/{relative}"
                archive.writestr(
                    deterministic_zip_info(archive_name),
                    payload,
                    compress_type=zipfile.ZIP_DEFLATED,
                    compresslevel=9,
                )
                archive_rows.append({"path": archive_name, "sha256": sha256_bytes(payload), "size": len(payload)})
        if not candidate_status(root, runtime_root=runtime_root).get("ok"):
            raise RuntimeError("source changed during package creation")
        os.replace(temp, target)
    except Exception as error:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass
        return {
            "ok": False,
            "status": "package_build_rejected",
            "candidate_id": selected_candidate_id,
            "reason": f"{type(error).__name__}: {error}",
            "content_free": True,
        }

    archive_manifest = archive_manifest_from_rows(
        version,
        selected_candidate_id,
        str(source_manifest.get("manifest_sha256") or ""),
        archive_rows,
    )
    directory = package_directory(runtime_root)
    archive_sha256 = sha256_file(target)
    atomic_json(directory / "manifests" / f"{selected_candidate_id}.json", archive_manifest)
    package_record = {
        "schema": PACKAGE_RECORD_SCHEMA,
        "candidate_id": selected_candidate_id,
        "packaged_version": version,
        "package_filename": package_name,
        "archive_root": EXPECTED_ARCHIVE_ROOT,
        "source_manifest_sha256": source_manifest.get("manifest_sha256"),
        "archive_manifest_sha256": archive_manifest.get("archive_manifest_sha256"),
        "archive_sha256": archive_sha256,
        "archive_entry_count": len(archive_rows),
        "state": "packaged_unpromoted",
        "created_at": utc_now(),
        "installed": False,
        "promoted": False,
        "certified": False,
        "verification_is_native_certification": False,
        "content_free": True,
        "contains_absolute_paths": False,
        "contains_source_contents": False,
    }
    atomic_json(directory / "records" / f"{selected_candidate_id}.json", package_record)
    atomic_json(
        directory / "active_package.json",
        {
            "schema": PACKAGE_RECORD_SCHEMA,
            "candidate_id": selected_candidate_id,
            "package_filename": package_name,
            "archive_sha256": archive_sha256,
            "content_free": True,
        },
    )
    verified = verify_candidate_archive(root, target, runtime_root=runtime_root, candidate_id=selected_candidate_id)
    if not verified.get("ok"):
        try:
            target.unlink()
        except FileNotFoundError:
            pass
        return verified
    return {
        "ok": True,
        "status": "packaged_unpromoted",
        "candidate_id": selected_candidate_id,
        "packaged_version": version,
        "package_filename": package_name,
        "archive_root": EXPECTED_ARCHIVE_ROOT,
        "source_manifest_sha256": source_manifest.get("manifest_sha256"),
        "archive_manifest_sha256": archive_manifest.get("archive_manifest_sha256"),
        "archive_sha256": archive_sha256,
        "archive_entry_count": len(archive_rows),
        "installed": False,
        "promoted": False,
        "certified": False,
        "verification_is_native_certification": False,
        "content_free": True,
    }


def zip_path_findings(info: zipfile.ZipInfo) -> list[str]:
    findings: list[str] = []
    name = info.filename
    pure = PurePosixPath(name)
    if not name or name.startswith(("/", "\\")) or pure.is_absolute():
        findings.append("absolute_path")
    if "\\" in name:
        findings.append("backslash_path")
    if ".." in pure.parts:
        findings.append("traversal_path")
    mode = (info.external_attr >> 16) & 0xFFFF
    if stat.S_ISLNK(mode):
        findings.append("symlink_entry")
    basename = pure.name.lower()
    suffix = Path(basename).suffix.lower()
    expected_permissions = 0o755 if suffix in {".sh", ".command"} else 0o644
    if stat.S_IMODE(mode) != expected_permissions:
        findings.append("incorrect_file_permissions")
    if basename in {"agents.md", "continuation_checkpoint.md"}:
        findings.append("agent_workflow_artifact")
    lowered_parts = {part.lower() for part in pure.parts}
    if suffix in NESTED_ARCHIVE_SUFFIXES:
        findings.append("nested_archive")
    if suffix in BYTECODE_SUFFIXES or "__pycache__" in lowered_parts:
        findings.append("bytecode_entry")
    if suffix in PRIVATE_BACKUP_SUFFIXES or "backups" in lowered_parts:
        findings.append("private_backup")
    if basename in CREDENTIAL_FILENAMES or suffix in CREDENTIAL_SUFFIXES or "credentials" in lowered_parts or "secrets" in lowered_parts:
        findings.append("credential_entry")
    return findings


def parse_internal_working_version(raw: bytes) -> str:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return ""
    match = _VERSION_ASSIGNMENT.search(text)
    return normalize_version(match.group(1) if match else "")


def json_version(raw: bytes, *keys: str) -> str:
    try:
        value = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return ""
    if not isinstance(value, dict):
        return ""
    for key in keys:
        result = normalize_version(value.get(key))
        if result:
            return result
    return ""


def metadata_version_contradictions(
    packaged_version: str,
    *,
    internal_version: str,
    settings_version: str = "",
    project_version: str = "",
    settings_present: bool = False,
    project_present: bool = False,
) -> list[dict[str, Any]]:
    """Validate mandatory source authority and any optional source metadata.

    Source-only archives intentionally may omit runtime-owned settings and project
    registries. Absence is therefore not a contradiction; when either allowlisted
    metadata file is packaged, its version remains exact and fail-closed.
    """
    expected = normalize_version(packaged_version)
    surfaces = (
        ("internal_release_metadata", normalize_version(internal_version), True),
        ("settings_metadata", normalize_version(settings_version), bool(settings_present)),
        ("project_metadata", normalize_version(project_version), bool(project_present)),
    )
    return [
        {"kind": f"{surface}_version_mismatch", "observed": observed, "expected": expected}
        for surface, observed, required_or_present in surfaces
        if required_or_present and observed != expected
    ]


def verify_candidate_archive(
    root_dir: str | Path,
    archive_path: str | Path,
    *,
    runtime_root: str | Path | None = None,
    candidate_id: str | None = None,
) -> dict[str, Any]:
    root = Path(root_dir).resolve()
    archive = Path(archive_path).resolve()
    candidate = candidate_status(root, runtime_root=runtime_root)
    record, source_manifest = active_candidate(runtime_root)
    expected_candidate_id = str(candidate_id or record.get("candidate_id") or "")
    contradictions: list[dict[str, Any]] = []
    structure_findings: list[dict[str, Any]] = []
    missing: list[str] = []
    extra: list[str] = []
    modified: list[str] = []
    renamed: list[dict[str, str]] = []

    if not archive.exists():
        return {"ok": False, "status": "archive_missing", "content_free": True}
    if not candidate.get("ok") or candidate.get("candidate_id") != expected_candidate_id:
        contradictions.append({"kind": "candidate_not_fresh_or_mismatched"})

    try:
        with zipfile.ZipFile(archive, "r") as zf:
            infos = [info for info in zf.infolist() if not info.is_dir()]
            names = [info.filename for info in infos]
            for name, count in sorted(Counter(names).items()):
                if count > 1:
                    structure_findings.append({"kind": "duplicate_entry", "entry": name, "count": count})
            for folded, count in sorted(Counter(name.casefold() for name in names).items()):
                variants = {name for name in names if name.casefold() == folded}
                if count > 1 and len(variants) > 1:
                    structure_findings.append({"kind": "case_colliding_entry", "entry": folded, "count": count})

            roots: set[str] = set()
            actual_rows: list[dict[str, Any]] = []
            actual_relative: dict[str, dict[str, Any]] = {}
            for info in infos:
                findings = zip_path_findings(info)
                for kind in findings:
                    structure_findings.append({"kind": kind, "entry": info.filename})
                pure = PurePosixPath(info.filename)
                if pure.parts:
                    roots.add(pure.parts[0])
                if findings:
                    continue
                payload = zf.read(info)
                row = {"path": info.filename, "sha256": sha256_bytes(payload), "size": len(payload)}
                actual_rows.append(row)
                if pure.parts and pure.parts[0] == EXPECTED_ARCHIVE_ROOT:
                    actual_relative[PurePosixPath(*pure.parts[1:]).as_posix()] = row

            if roots != {EXPECTED_ARCHIVE_ROOT}:
                contradictions.append({"kind": "archive_root_mismatch", "observed_roots": sorted(roots), "expected_root": EXPECTED_ARCHIVE_ROOT})

            expected = {
                str(row.get("path")): row
                for row in source_manifest.get("entries", [])
                if isinstance(row, dict) and row.get("path")
            }
            missing = sorted(set(expected) - set(actual_relative))
            extra = sorted(set(actual_relative) - set(expected))
            modified = sorted(
                relative
                for relative in set(expected) & set(actual_relative)
                if actual_relative[relative]["sha256"] != expected[relative].get("package_sha256")
                or actual_relative[relative]["size"] != expected[relative].get("package_size")
            )
            extra_by_hash: dict[str, list[str]] = defaultdict(list)
            for relative in extra:
                extra_by_hash[str(actual_relative[relative].get("sha256") or "")].append(relative)
            for relative in missing:
                digest = str(expected[relative].get("package_sha256") or "")
                matches = extra_by_hash.get(digest) or []
                if matches:
                    renamed.append({"from": relative, "to": matches.pop(0)})

            version = normalize_version(record.get("candidate_version"))
            archive_manifest = archive_manifest_from_rows(
                version,
                expected_candidate_id,
                str(source_manifest.get("manifest_sha256") or ""),
                actual_rows,
            )
            release_key = f"{EXPECTED_ARCHIVE_ROOT}/conscious_agent/release_metadata.py"
            settings_key = f"{EXPECTED_ARCHIVE_ROOT}/data/settings.json"
            project_key = f"{EXPECTED_ARCHIVE_ROOT}/data/workspaces/projects.json"
            internal_version = parse_internal_working_version(zf.read(release_key)) if release_key in names else ""
            settings_version = json_version(zf.read(settings_key), "working_source_version", "version", "root_version") if settings_key in names else ""
            project_version = json_version(zf.read(project_key), "working_source_version", "version", "root_version") if project_key in names else ""
    except (OSError, zipfile.BadZipFile, RuntimeError) as error:
        return {"ok": False, "status": "archive_unreadable", "reason": f"{type(error).__name__}: {error}", "content_free": True}

    packaged_version = normalize_version(record.get("candidate_version"))
    filename_version = version_from_artifact_name(archive.name)
    if filename_version != packaged_version:
        contradictions.append({"kind": "archive_filename_version_mismatch", "filename_version": filename_version, "packaged_version": packaged_version})
    contradictions.extend(
        metadata_version_contradictions(
            packaged_version,
            internal_version=internal_version,
            settings_version=settings_version,
            project_version=project_version,
            settings_present=settings_key in names,
            project_present=project_key in names,
        )
    )

    directory = package_directory(runtime_root)
    package_record = read_json(directory / "records" / f"{expected_candidate_id}.json")
    stored_manifest = read_json(directory / "manifests" / f"{expected_candidate_id}.json")
    archive_sha256 = sha256_file(archive)
    archive_manifest_sha256 = str(archive_manifest.get("archive_manifest_sha256") or "")
    if package_record:
        comparisons = (
            ("package_filename", archive.name),
            ("archive_root", EXPECTED_ARCHIVE_ROOT),
            ("source_manifest_sha256", source_manifest.get("manifest_sha256")),
            ("archive_manifest_sha256", archive_manifest_sha256),
            ("archive_sha256", archive_sha256),
            ("candidate_id", expected_candidate_id),
            ("packaged_version", packaged_version),
        )
        for key, observed in comparisons:
            if package_record.get(key) != observed:
                contradictions.append({"kind": f"package_record_{key}_mismatch"})
    if stored_manifest and stored_manifest.get("archive_manifest_sha256") != archive_manifest_sha256:
        contradictions.append({"kind": "stored_archive_manifest_mismatch"})

    privacy = package_privacy_summary_for_zip(archive)
    if not privacy.get("ok"):
        structure_findings.append({"kind": "source_only_privacy_failure", "count": int(privacy.get("forbidden_count") or 0)})
    if missing:
        contradictions.append({"kind": "missing_archive_entries", "count": len(missing)})
    if extra:
        contradictions.append({"kind": "extra_archive_entries", "count": len(extra)})
    if modified:
        contradictions.append({"kind": "modified_archive_entries", "count": len(modified)})
    if renamed:
        contradictions.append({"kind": "renamed_archive_entries", "count": len(renamed)})

    ok = not contradictions and not structure_findings
    return {
        "ok": ok,
        "status": "coherent" if ok else "contradiction_detected",
        "candidate_id": expected_candidate_id,
        "packaged_version": packaged_version,
        "package_filename": archive.name,
        "archive_root": EXPECTED_ARCHIVE_ROOT,
        "source_manifest_sha256": source_manifest.get("manifest_sha256"),
        "archive_manifest_sha256": archive_manifest_sha256,
        "archive_sha256": archive_sha256,
        "archive_entry_count": int(archive_manifest.get("entry_count") or 0),
        "missing_count": len(missing),
        "extra_count": len(extra),
        "modified_count": len(modified),
        "renamed_count": len(renamed),
        "missing_entries": missing[:25],
        "extra_entries": extra[:25],
        "modified_entries": modified[:25],
        "renamed_entries": renamed[:25],
        "structure_findings": structure_findings[:50],
        "contradictions": contradictions[:50],
        "source_only": bool(privacy.get("source_only")),
        "privacy_finding_count": int(privacy.get("private_content_finding_count") or 0),
        "installed": False,
        "promoted": False,
        "certified": False,
        "verification_is_native_certification": False,
        "content_free": True,
    }


def active_package_record(runtime_root: str | Path | None = None) -> dict[str, Any]:
    directory = package_directory(runtime_root)
    pointer = read_json(directory / "active_package.json")
    candidate_id = str(pointer.get("candidate_id") or "")
    if not candidate_id:
        return {}
    return read_json(directory / "records" / f"{candidate_id}.json")
