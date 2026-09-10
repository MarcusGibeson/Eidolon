from __future__ import annotations

"""Exact release-candidate identity bound to a frozen Eidolon source tree."""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping

try:
    from package_integrity import iter_source_tree_entries, source_package_bytes
    from release_metadata import WORKING_SOURCE_VERSION
    from version_roles import normalize_version
except ImportError:
    from package_integrity import iter_source_tree_entries, source_package_bytes
    from release_metadata import WORKING_SOURCE_VERSION
    from version_roles import normalize_version

CANDIDATE_IDENTITY_CONTRACT_VERSION = "1"
EXPECTED_ARCHIVE_ROOT = "Eidolon"
RUNTIME_CANDIDATE_DIRECTORY = "release_candidates"
SOURCE_MANIFEST_SCHEMA = "eidolon-source-manifest-v1"
CANDIDATE_RECORD_SCHEMA = "eidolon-candidate-record-v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def digest_payload(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(dict(value), handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        try:
            Path(temp_name).unlink()
        except FileNotFoundError:
            pass


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def runtime_data_root(runtime_root: str | Path | None = None) -> Path:
    if runtime_root is not None:
        return Path(runtime_root).expanduser().resolve()
    override = os.environ.get("EIDOLON_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    # Never fall back to the source tree for candidate identity records.
    return (Path.home() / ".eidolon" / "runtime").resolve()


def candidate_directory(runtime_root: str | Path | None = None) -> Path:
    return runtime_data_root(runtime_root) / RUNTIME_CANDIDATE_DIRECTORY


def source_manifest_entries(root_dir: str | Path) -> list[dict[str, Any]]:
    root = Path(root_dir).resolve()
    entries: list[dict[str, Any]] = []
    for relative in iter_source_tree_entries(root):
        path = root / relative
        raw = path.read_bytes()
        packaged = source_package_bytes(root, relative)
        entries.append(
            {
                "path": relative,
                "raw_sha256": sha256_bytes(raw),
                "raw_size": len(raw),
                "package_sha256": sha256_bytes(packaged),
                "package_size": len(packaged),
            }
        )
    return sorted(entries, key=lambda row: str(row["path"]))


def build_source_manifest(root_dir: str | Path, *, expected_version: str | None = None) -> dict[str, Any]:
    version = normalize_version(expected_version or WORKING_SOURCE_VERSION)
    entries = source_manifest_entries(root_dir)
    payload = {
        "schema": SOURCE_MANIFEST_SCHEMA,
        "contract_version": CANDIDATE_IDENTITY_CONTRACT_VERSION,
        "working_source_version": version,
        "archive_root": EXPECTED_ARCHIVE_ROOT,
        "file_count": len(entries),
        "entries": entries,
        "contains_absolute_paths": False,
        "contains_source_contents": False,
    }
    payload["manifest_sha256"] = digest_payload(payload)
    return payload


def candidate_id_for(version: str, manifest_sha256: str) -> str:
    return f"eidolon-v{normalize_version(version)}-{manifest_sha256[:20]}"


def canonical_candidate_archive_name(version: str, candidate_id: str) -> str:
    suffix = candidate_id.rsplit("-", 1)[-1][:12]
    return f"Eidolon_v{normalize_version(version).replace('.', '_')}_candidate_{suffix}_source_only.zip"


def freeze_release_candidate(
    root_dir: str | Path,
    *,
    runtime_root: str | Path | None = None,
    expected_version: str | None = None,
) -> dict[str, Any]:
    """Assign identity only after an external manifest survives three scans."""
    root = Path(root_dir).resolve()
    version = normalize_version(expected_version or WORKING_SOURCE_VERSION)
    authoritative = normalize_version(WORKING_SOURCE_VERSION)
    if version != authoritative:
        return {
            "ok": False,
            "status": "working_version_mismatch",
            "working_source_version": authoritative,
            "requested_version": version,
            "candidate_assigned": False,
            "content_free": True,
        }

    first = build_source_manifest(root, expected_version=version)
    second = build_source_manifest(root, expected_version=version)
    if first["manifest_sha256"] != second["manifest_sha256"]:
        return {
            "ok": False,
            "status": "source_changed_during_freeze",
            "candidate_assigned": False,
            "working_source_version": version,
            "content_free": True,
        }

    candidate_id = candidate_id_for(version, first["manifest_sha256"])
    directory = candidate_directory(runtime_root)
    manifest_path = directory / "manifests" / f"{candidate_id}.json"
    record_path = directory / "records" / f"{candidate_id}.json"
    active_path = directory / "active_candidate.json"
    atomic_json(manifest_path, first)

    final = build_source_manifest(root, expected_version=version)
    if final["manifest_sha256"] != first["manifest_sha256"]:
        try:
            manifest_path.unlink()
        except FileNotFoundError:
            pass
        return {
            "ok": False,
            "status": "source_changed_after_manifest",
            "candidate_assigned": False,
            "working_source_version": version,
            "content_free": True,
        }

    record = {
        "schema": CANDIDATE_RECORD_SCHEMA,
        "candidate_id": candidate_id,
        "candidate_version": version,
        "source_manifest_sha256": first["manifest_sha256"],
        "source_file_count": first["file_count"],
        "state": "frozen",
        "created_at": utc_now(),
        "installed": False,
        "promoted": False,
        "certified": False,
        "content_free": True,
        "contains_source_paths": False,
        "contains_source_contents": False,
    }
    atomic_json(record_path, record)
    atomic_json(
        active_path,
        {
            "schema": CANDIDATE_RECORD_SCHEMA,
            "candidate_id": candidate_id,
            "candidate_version": version,
            "source_manifest_sha256": first["manifest_sha256"],
            "content_free": True,
        },
    )
    return {
        "ok": True,
        "status": "frozen",
        "candidate_assigned": True,
        "candidate_id": candidate_id,
        "candidate_version": version,
        "source_manifest_sha256": first["manifest_sha256"],
        "source_file_count": first["file_count"],
        "record_external": True,
        "manifest_external": True,
        "installed": False,
        "promoted": False,
        "certified": False,
        "content_free": True,
    }


def active_candidate(runtime_root: str | Path | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    directory = candidate_directory(runtime_root)
    pointer = read_json(directory / "active_candidate.json")
    candidate_id = str(pointer.get("candidate_id") or "").strip()
    if not candidate_id:
        return {}, {}
    record = read_json(directory / "records" / f"{candidate_id}.json")
    manifest = read_json(directory / "manifests" / f"{candidate_id}.json")
    return record, manifest


def candidate_status(root_dir: str | Path, *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(root_dir).resolve()
    record, manifest = active_candidate(runtime_root)
    if not record:
        return {
            "ok": True,
            "status": "not_frozen",
            "candidate_present": False,
            "candidate_inferred_from_archive": False,
            "working_source_version": normalize_version(WORKING_SOURCE_VERSION),
            "content_free": True,
        }
    expected_digest = str(record.get("source_manifest_sha256") or "")
    version = normalize_version(record.get("candidate_version"))
    current = build_source_manifest(root, expected_version=version)
    manifest_valid = bool(manifest) and manifest.get("manifest_sha256") == expected_digest
    source_fresh = current.get("manifest_sha256") == expected_digest
    stale = not (manifest_valid and source_fresh and version == normalize_version(WORKING_SOURCE_VERSION))
    return {
        "ok": not stale,
        "status": "stale" if stale else "frozen",
        "candidate_present": True,
        "candidate_id": str(record.get("candidate_id") or ""),
        "candidate_version": version,
        "working_source_version": normalize_version(WORKING_SOURCE_VERSION),
        "source_manifest_sha256": expected_digest,
        "source_file_count": int(record.get("source_file_count") or 0),
        "source_manifest_record_valid": manifest_valid,
        "source_tree_matches_manifest": source_fresh,
        "candidate_inferred_from_archive": False,
        "installed": False,
        "promoted": False,
        "certified": False,
        "content_free": True,
    }
