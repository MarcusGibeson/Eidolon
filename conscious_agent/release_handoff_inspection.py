from __future__ import annotations

"""Operator-selected, preview-only inspection of one exact candidate archive.

The selected archive path and extracted inspection tree are private runtime
state. Public summaries expose only content-free identity, digest, structure,
and contradiction data. This module never scans for archives, installs source,
changes project registries, promotes a release, or performs certification.
"""

from collections import Counter, defaultdict
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
from typing import Any, Iterable, Mapping
import zipfile

try:
    from package_integrity import package_privacy_summary_for_zip
    from release_archive_coherence import EXPECTED_ARCHIVE_ROOT, archive_manifest_from_rows, json_version, parse_internal_working_version, zip_path_findings
    from release_candidate_identity import atomic_json, build_source_manifest, candidate_id_for, canonical_candidate_archive_name, digest_payload, read_json, runtime_data_root, sha256_bytes, sha256_file, utc_now
    from version_roles import normalize_version, version_from_artifact_name
except ImportError:
    from package_integrity import package_privacy_summary_for_zip
    from release_archive_coherence import (
        EXPECTED_ARCHIVE_ROOT,
        archive_manifest_from_rows,
        json_version,
        parse_internal_working_version,
        zip_path_findings,
    )
    from release_candidate_identity import (
        atomic_json,
        build_source_manifest,
        candidate_id_for,
        canonical_candidate_archive_name,
        digest_payload,
        read_json,
        runtime_data_root,
        sha256_bytes,
        sha256_file,
        utc_now,
    )
    from version_roles import normalize_version, version_from_artifact_name

HANDOFF_INSPECTION_CONTRACT_VERSION = "1"
HANDOFF_RECORD_SCHEMA = "eidolon-operator-selected-handoff-v1"
RUNTIME_HANDOFF_DIRECTORY = "release_handoffs"
HANDOFF_RECORD_BINDING_VERSION = "1"


def handoff_directory(runtime_root: str | Path | None = None) -> Path:
    return runtime_data_root(runtime_root) / RUNTIME_HANDOFF_DIRECTORY


def handoff_runtime_binding(runtime_root: str | Path | None = None) -> str:
    """Bind private handoff records to one exact external runtime directory."""
    return digest_payload({
        "contract": "eidolon-handoff-runtime-binding-v1",
        "runtime_directory": str(handoff_directory(runtime_root).resolve()),
    })


def handoff_record_binding(record: Mapping[str, Any]) -> str:
    """Return a content-free digest over the fields required to activate a record."""
    return digest_payload({
        "contract": "eidolon-handoff-record-binding-v1",
        "inspection_id": str(record.get("inspection_id") or ""),
        "record_generation": int(record.get("record_generation") or 0),
        "runtime_root_binding": str(record.get("runtime_root_binding") or ""),
        "selected_archive_path": str(record.get("selected_archive_path") or ""),
        "extracted_root_path": str(record.get("extracted_root_path") or ""),
        "archive_sha256": str(record.get("archive_sha256") or ""),
        "candidate_id": str(record.get("candidate_id") or ""),
        "source_manifest_sha256": str(record.get("source_manifest_sha256") or ""),
        "archive_manifest_sha256": str(record.get("archive_manifest_sha256") or ""),
        "packaged_version": normalize_version(record.get("packaged_version")),
    })


def _active_pointer(runtime_root: str | Path | None = None) -> dict[str, Any]:
    return read_json(handoff_directory(runtime_root) / "active_handoff.json")


def _next_record_generation(runtime_root: str | Path | None = None) -> int:
    pointer = _active_pointer(runtime_root)
    try:
        return max(0, int(pointer.get("record_generation") or 0)) + 1
    except (TypeError, ValueError):
        return 1


def _kind_counts(rows: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    for row in rows or []:
        kind = str(row.get("kind") or "unknown")
        count = row.get("count", 1)
        try:
            counts[kind] += max(1, int(count))
        except (TypeError, ValueError):
            counts[kind] += 1
    return [{"kind": kind, "count": counts[kind]} for kind in sorted(counts)]


def _public_summary(record: Mapping[str, Any] | None) -> dict[str, Any]:
    row = dict(record or {})
    contradictions = _kind_counts(row.get("contradictions") if isinstance(row.get("contradictions"), list) else [])
    structure = _kind_counts(row.get("structure_findings") if isinstance(row.get("structure_findings"), list) else [])
    contradiction_count = sum(int(item["count"]) for item in contradictions)
    structure_count = sum(int(item["count"]) for item in structure)
    status = str(row.get("status") or "not_selected")
    ok = bool(row.get("ok")) and contradiction_count == 0 and structure_count == 0
    return {
        "ok": ok,
        "status": status,
        "contract_version": HANDOFF_INSPECTION_CONTRACT_VERSION,
        "inspection_present": bool(row),
        "record_generation": int(row.get("record_generation") or 0),
        "runtime_root_bound": bool(row.get("runtime_root_binding")),
        "record_binding_present": bool(row.get("record_binding_sha256")),
        "archive_selected_explicitly": bool(row.get("archive_selected_explicitly")),
        "automatic_selection_performed": False,
        "directory_scan_performed": False,
        "archive_path_suppressed": True,
        "package_filename": str(row.get("package_filename") or ""),
        "archive_root": str(row.get("archive_root") or ""),
        "packaged_version": normalize_version(row.get("packaged_version")),
        "candidate_id": str(row.get("candidate_id") or ""),
        "source_manifest_sha256": str(row.get("source_manifest_sha256") or ""),
        "archive_manifest_sha256": str(row.get("archive_manifest_sha256") or ""),
        "archive_sha256": str(row.get("archive_sha256") or ""),
        "candidate_fresh": bool(row.get("candidate_fresh")),
        "package_coherent": bool(row.get("package_coherent")),
        "source_only": bool(row.get("source_only")),
        "archive_entry_count": int(row.get("archive_entry_count") or 0),
        "contradictions": contradictions,
        "contradiction_count": contradiction_count,
        "structure_findings": structure,
        "structure_finding_count": structure_count,
        "selected_path_recorded_externally": bool(row.get("selected_archive_path")),
        "extraction_recorded_externally": bool(row.get("extracted_root_path")),
        "records_external": True,
        "content_free": True,
        "read_only_preview": True,
        "installed": False,
        "promoted": False,
        "certified": False,
        "installation_changed": False,
        "promotion_changed": False,
        "certification_performed": False,
        "verification_is_native_certification": False,
        "project_registry_changed": False,
        "operator_project_root_modified": False,
        "provider_contacted": False,
        "ordinary_conversation_affected": False,
        "replacement_requires_preview": True,
        "recovery_requires_preview": True,
    }


def _selection_path(value: str | Path) -> Path:
    token = str(value or "").strip()
    if not token:
        raise ValueError("archive_path is required; archive discovery and automatic selection are not supported")
    return Path(token).expanduser().absolute()


def _record_paths(runtime_root: str | Path | None, inspection_id: str) -> tuple[Path, Path, Path, Path]:
    directory = handoff_directory(runtime_root)
    return (
        directory / "records" / f"{inspection_id}.json",
        directory / "manifests" / f"{inspection_id}.source.json",
        directory / "manifests" / f"{inspection_id}.archive.json",
        directory / "active_handoff.json",
    )


def _persist_record(
    record: dict[str, Any],
    *,
    runtime_root: str | Path | None,
    source_manifest: Mapping[str, Any] | None = None,
    archive_manifest: Mapping[str, Any] | None = None,
    activate: bool = True,
) -> dict[str, Any]:
    inspection_id = str(record.get("inspection_id") or "")
    record.setdefault("record_generation", _next_record_generation(runtime_root))
    record.setdefault("runtime_root_binding", handoff_runtime_binding(runtime_root))
    record["record_binding_sha256"] = handoff_record_binding(record)
    record_path, source_path, archive_path, active_path = _record_paths(runtime_root, inspection_id)
    if source_manifest:
        atomic_json(source_path, source_manifest)
    if archive_manifest:
        atomic_json(archive_path, archive_manifest)
    atomic_json(record_path, record)
    if activate:
        atomic_json(
            active_path,
            {
                "schema": HANDOFF_RECORD_SCHEMA,
                "inspection_id": inspection_id,
                "status": str(record.get("status") or "attention_required"),
                "record_generation": int(record.get("record_generation") or 0),
                "runtime_root_binding": str(record.get("runtime_root_binding") or ""),
                "record_binding_sha256": str(record.get("record_binding_sha256") or ""),
                "selected_archive_path": str(record.get("selected_archive_path") or ""),
                "extracted_root_path": str(record.get("extracted_root_path") or ""),
                "archive_sha256": str(record.get("archive_sha256") or ""),
                "candidate_id": str(record.get("candidate_id") or ""),
                "source_manifest_sha256": str(record.get("source_manifest_sha256") or ""),
                "archive_manifest_sha256": str(record.get("archive_manifest_sha256") or ""),
                "packaged_version": normalize_version(record.get("packaged_version")),
                "content_free": True,
                "private_paths_present": True,
            },
        )
    return _public_summary(record)


def activate_handoff_record(
    inspection_id: str,
    *,
    runtime_root: str | Path | None = None,
    expected_generation: int | None = None,
) -> dict[str, Any]:
    """Activate one already-inspected private record after exact binding checks."""
    directory = handoff_directory(runtime_root)
    active_path = directory / "active_handoff.json"
    pointer = read_json(active_path)
    current_generation = int(pointer.get("record_generation") or 0)
    if expected_generation is not None and current_generation != int(expected_generation):
        return {"ok": False, "status": "stale_active_generation", "content_free": True}
    record = read_json(directory / "records" / f"{inspection_id}.json")
    if not record:
        return {"ok": False, "status": "inspection_record_missing", "content_free": True}
    if str(record.get("runtime_root_binding") or "") != handoff_runtime_binding(runtime_root):
        return {"ok": False, "status": "runtime_root_binding_mismatch", "content_free": True}
    if str(record.get("record_binding_sha256") or "") != handoff_record_binding(record):
        return {"ok": False, "status": "inspection_record_binding_mismatch", "content_free": True}
    record = dict(record)
    record["record_generation"] = current_generation + 1
    record["activated_at"] = utc_now()
    record["record_binding_sha256"] = handoff_record_binding(record)
    atomic_json(directory / "records" / f"{inspection_id}.json", record)
    atomic_json(active_path, {
        "schema": HANDOFF_RECORD_SCHEMA,
        "inspection_id": inspection_id,
        "status": str(record.get("status") or "attention_required"),
        "record_generation": int(record.get("record_generation") or 0),
        "runtime_root_binding": str(record.get("runtime_root_binding") or ""),
        "record_binding_sha256": str(record.get("record_binding_sha256") or ""),
        "selected_archive_path": str(record.get("selected_archive_path") or ""),
        "extracted_root_path": str(record.get("extracted_root_path") or ""),
        "archive_sha256": str(record.get("archive_sha256") or ""),
        "candidate_id": str(record.get("candidate_id") or ""),
        "source_manifest_sha256": str(record.get("source_manifest_sha256") or ""),
        "archive_manifest_sha256": str(record.get("archive_manifest_sha256") or ""),
        "packaged_version": normalize_version(record.get("packaged_version")),
        "content_free": True,
        "private_paths_present": True,
    })
    return _public_summary(record)


def _failed_record(
    *,
    selected: Path,
    inspection_id: str,
    status: str,
    runtime_root: str | Path | None,
    archive_sha256: str = "",
    contradictions: list[dict[str, Any]] | None = None,
    structure_findings: list[dict[str, Any]] | None = None,
    activate: bool = True,
    record_generation: int | None = None,
) -> dict[str, Any]:
    record = {
        "schema": HANDOFF_RECORD_SCHEMA,
        "contract_version": HANDOFF_INSPECTION_CONTRACT_VERSION,
        "inspection_id": inspection_id,
        "created_at": utc_now(),
        "status": status,
        "ok": False,
        "selected_archive_path": str(selected),
        "archive_selected_explicitly": True,
        "archive_sha256": archive_sha256,
        "candidate_fresh": False,
        "package_coherent": False,
        "source_only": False,
        "contradictions": list(contradictions or []),
        "structure_findings": list(structure_findings or []),
        "installed": False,
        "promoted": False,
        "certified": False,
        "content_free": True,
        "record_generation": int(record_generation or _next_record_generation(runtime_root)),
        "runtime_root_binding": handoff_runtime_binding(runtime_root),
    }
    return _persist_record(record, runtime_root=runtime_root, activate=activate)


def _safe_extract(
    archive: zipfile.ZipFile,
    infos: list[zipfile.ZipInfo],
    destination: Path,
) -> None:
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    shutil.rmtree(temporary, ignore_errors=True)
    temporary.mkdir(parents=True, exist_ok=False)
    try:
        for info in infos:
            pure = PurePosixPath(info.filename)
            target = temporary.joinpath(*pure.parts)
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            payload = archive.read(info)
            target.write_bytes(payload)
        shutil.rmtree(destination, ignore_errors=True)
        os.replace(temporary, destination)
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


def inspect_selected_candidate_archive(
    archive_path: str | Path,
    *,
    runtime_root: str | Path | None = None,
    activate: bool = True,
    inspection_id_override: str = "",
    record_generation: int | None = None,
) -> dict[str, Any]:
    """Inspect exactly the archive selected by the operator.

    The function writes only external inspection records and an external
    extraction tree. It never scans sibling directories or changes source,
    installed projects, project registries, promotion, or certification state.
    """
    selected = _selection_path(archive_path)
    selection_digest = digest_payload({"selected_archive_path": str(selected)})[:20]
    provisional_id = inspection_id_override or f"handoff-selection-{selection_digest}"
    generation = int(record_generation or _next_record_generation(runtime_root))

    if activate:
        pointer = _active_pointer(runtime_root)
        active_id = str(pointer.get("inspection_id") or "")
        active_record = read_json(handoff_directory(runtime_root) / "records" / f"{active_id}.json") if active_id else {}
        active_path = str(active_record.get("selected_archive_path") or pointer.get("selected_archive_path") or "")
        active_ok = bool(active_record.get("ok")) and str(active_record.get("record_binding_sha256") or "") == handoff_record_binding(active_record)
        if active_ok and active_path and Path(active_path).absolute() != selected:
            return {
                **_public_summary(active_record),
                "ok": False,
                "status": "replacement_preview_required",
                "replacement_required": True,
                "operator_selection_required": True,
                "active_preserved": True,
            }

    if selected.is_symlink():
        return _failed_record(
            selected=selected,
            inspection_id=provisional_id,
            status="selected_archive_symlink_rejected",
            runtime_root=runtime_root,
            structure_findings=[{"kind": "selected_archive_symlink"}],
            activate=activate, record_generation=generation,
        )
    if not selected.exists():
        return _failed_record(
            selected=selected,
            inspection_id=provisional_id,
            status="archive_missing",
            runtime_root=runtime_root,
            contradictions=[{"kind": "selected_archive_missing"}],
            activate=activate, record_generation=generation,
        )
    if not selected.is_file():
        return _failed_record(
            selected=selected,
            inspection_id=provisional_id,
            status="archive_unreadable",
            runtime_root=runtime_root,
            contradictions=[{"kind": "selected_archive_not_regular_file"}],
            activate=activate, record_generation=generation,
        )
    try:
        archive_sha256 = sha256_file(selected)
    except OSError:
        return _failed_record(
            selected=selected,
            inspection_id=provisional_id,
            status="archive_unreadable",
            runtime_root=runtime_root,
            contradictions=[{"kind": "selected_archive_unreadable"}],
            activate=activate, record_generation=generation,
        )

    inspection_id = inspection_id_override or f"handoff-{archive_sha256[:20]}-{selection_digest[:8]}"
    contradictions: list[dict[str, Any]] = []
    structure_findings: list[dict[str, Any]] = []
    actual_rows: list[dict[str, Any]] = []
    infos: list[zipfile.ZipInfo] = []
    internal_release_version = ""
    settings_version = ""
    projects_version = ""
    active_project_version = ""

    try:
        with zipfile.ZipFile(selected, "r") as archive:
            infos = archive.infolist()
            if not infos:
                contradictions.append({"kind": "archive_empty"})
            names = [info.filename for info in infos]
            for name, count in sorted(Counter(names).items()):
                if count > 1:
                    structure_findings.append({"kind": "duplicate_entry", "count": count})
            folded_names: defaultdict[str, set[str]] = defaultdict(set)
            for name in names:
                folded_names[name.casefold()].add(name)
            for variants in folded_names.values():
                if len(variants) > 1:
                    structure_findings.append({"kind": "case_colliding_entry", "count": len(variants)})

            roots: set[str] = set()
            for info in infos:
                pure = PurePosixPath(info.filename)
                if pure.parts:
                    roots.add(pure.parts[0])
                for kind in zip_path_findings(info):
                    structure_findings.append({"kind": kind})
                if info.flag_bits & 0x1:
                    structure_findings.append({"kind": "encrypted_entry"})
                mode = (info.external_attr >> 16) & 0xFFFF
                if mode and not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                    structure_findings.append({"kind": "special_entry"})
                if info.is_dir():
                    continue
                payload = archive.read(info)
                actual_rows.append({"path": info.filename, "sha256": sha256_bytes(payload), "size": len(payload)})

            if roots != {EXPECTED_ARCHIVE_ROOT}:
                contradictions.append({"kind": "archive_root_mismatch", "count": max(1, len(roots))})

            release_key = f"{EXPECTED_ARCHIVE_ROOT}/conscious_agent/release_metadata.py"
            settings_key = f"{EXPECTED_ARCHIVE_ROOT}/data/settings.json"
            projects_key = f"{EXPECTED_ARCHIVE_ROOT}/data/workspaces/projects.json"
            active_key = f"{EXPECTED_ARCHIVE_ROOT}/data/workspaces/active_project.json"
            info_by_name = {info.filename: info for info in infos}
            internal_release_version = parse_internal_working_version(archive.read(info_by_name[release_key])) if release_key in info_by_name else ""
            settings_version = json_version(archive.read(info_by_name[settings_key]), "working_source_version", "version", "root_version") if settings_key in info_by_name else ""
            projects_version = json_version(archive.read(info_by_name[projects_key]), "working_source_version", "version", "root_version") if projects_key in info_by_name else ""
            active_project_version = json_version(archive.read(info_by_name[active_key]), "working_source_version", "version", "root_version") if active_key in info_by_name else ""
    except (OSError, RuntimeError, zipfile.BadZipFile, zipfile.LargeZipFile):
        return _failed_record(
            selected=selected,
            inspection_id=inspection_id,
            status="archive_unreadable",
            runtime_root=runtime_root,
            archive_sha256=archive_sha256,
            contradictions=[{"kind": "selected_archive_unreadable"}],
            activate=activate, record_generation=generation,
        )

    privacy = package_privacy_summary_for_zip(selected)
    if not privacy.get("ok") or not privacy.get("source_only"):
        structure_findings.append({"kind": "source_only_privacy_failure", "count": max(1, int(privacy.get("forbidden_count") or 0) + int(privacy.get("private_content_finding_count") or 0))})

    if contradictions or structure_findings:
        return _failed_record(
            selected=selected,
            inspection_id=inspection_id,
            status="contradiction_detected",
            runtime_root=runtime_root,
            archive_sha256=archive_sha256,
            contradictions=contradictions,
            structure_findings=structure_findings,
            activate=activate, record_generation=generation,
        )

    extraction_parent = handoff_directory(runtime_root) / "extractions" / inspection_id
    try:
        with zipfile.ZipFile(selected, "r") as archive:
            _safe_extract(archive, infos, extraction_parent)
    except (OSError, RuntimeError, zipfile.BadZipFile):
        return _failed_record(
            selected=selected,
            inspection_id=inspection_id,
            status="extraction_failed",
            runtime_root=runtime_root,
            archive_sha256=archive_sha256,
            contradictions=[{"kind": "external_extraction_failed"}],
            activate=activate, record_generation=generation,
        )

    extracted_root = extraction_parent / EXPECTED_ARCHIVE_ROOT
    packaged_version = normalize_version(internal_release_version)
    if not packaged_version:
        contradictions.append({"kind": "internal_release_metadata_missing"})
    for surface, observed, present in (
        ("settings_metadata", settings_version, settings_key in info_by_name),
        ("project_metadata", projects_version, projects_key in info_by_name),
        ("active_project_metadata", active_project_version, active_key in info_by_name),
    ):
        if present and normalize_version(observed) != packaged_version:
            contradictions.append({"kind": f"{surface}_version_mismatch"})

    source_manifest: dict[str, Any] = {}
    archive_manifest: dict[str, Any] = {}
    candidate_id = ""
    missing: list[str] = []
    extra: list[str] = []
    modified: list[str] = []
    renamed: list[dict[str, str]] = []
    if packaged_version:
        first = build_source_manifest(extracted_root, expected_version=packaged_version)
        second = build_source_manifest(extracted_root, expected_version=packaged_version)
        if first.get("manifest_sha256") != second.get("manifest_sha256"):
            contradictions.append({"kind": "extracted_source_changed_during_inspection"})
        else:
            source_manifest = first
            candidate_id = candidate_id_for(packaged_version, str(first.get("manifest_sha256") or ""))
            archive_manifest = archive_manifest_from_rows(
                packaged_version,
                candidate_id,
                str(first.get("manifest_sha256") or ""),
                actual_rows,
            )
            expected = {
                str(row.get("path")): row
                for row in first.get("entries", [])
                if isinstance(row, dict) and row.get("path")
            }
            actual_relative = {
                PurePosixPath(*PurePosixPath(row["path"]).parts[1:]).as_posix(): row
                for row in actual_rows
                if PurePosixPath(row["path"]).parts and PurePosixPath(row["path"]).parts[0] == EXPECTED_ARCHIVE_ROOT
            }
            missing = sorted(set(expected) - set(actual_relative))
            extra = sorted(set(actual_relative) - set(expected))
            modified = sorted(
                path
                for path in set(expected) & set(actual_relative)
                if actual_relative[path].get("sha256") != expected[path].get("package_sha256")
                or actual_relative[path].get("size") != expected[path].get("package_size")
            )
            extra_by_hash: defaultdict[str, list[str]] = defaultdict(list)
            for path in extra:
                extra_by_hash[str(actual_relative[path].get("sha256") or "")].append(path)
            for path in missing:
                matches = extra_by_hash.get(str(expected[path].get("package_sha256") or "")) or []
                if matches:
                    renamed.append({"from": path, "to": matches.pop(0)})
            if missing:
                contradictions.append({"kind": "missing_archive_entries", "count": len(missing)})
            if extra:
                contradictions.append({"kind": "extra_archive_entries", "count": len(extra)})
            if modified:
                contradictions.append({"kind": "modified_archive_entries", "count": len(modified)})
            if renamed:
                contradictions.append({"kind": "renamed_archive_entries", "count": len(renamed)})

            expected_filename = canonical_candidate_archive_name(packaged_version, candidate_id)
            if selected.name != expected_filename:
                contradictions.append({"kind": "archive_filename_identity_mismatch"})
            filename_version = version_from_artifact_name(selected.name)
            if filename_version != packaged_version:
                contradictions.append({"kind": "archive_filename_version_mismatch"})

    final_manifest = build_source_manifest(extracted_root, expected_version=packaged_version) if packaged_version else {}
    candidate_fresh = bool(source_manifest) and final_manifest.get("manifest_sha256") == source_manifest.get("manifest_sha256")
    if source_manifest and not candidate_fresh:
        contradictions.append({"kind": "candidate_source_stale"})

    try:
        final_archive_sha256 = sha256_file(selected)
    except OSError:
        final_archive_sha256 = ""
        contradictions.append({"kind": "selected_archive_unreadable_after_inspection"})
    if final_archive_sha256 and final_archive_sha256 != archive_sha256:
        contradictions.append({"kind": "selected_archive_changed_during_inspection"})

    ok = not contradictions and not structure_findings and candidate_fresh and bool(candidate_id)
    record = {
        "schema": HANDOFF_RECORD_SCHEMA,
        "contract_version": HANDOFF_INSPECTION_CONTRACT_VERSION,
        "inspection_id": inspection_id,
        "created_at": utc_now(),
        "status": "coherent_preview" if ok else "contradiction_detected",
        "ok": ok,
        "selected_archive_path": str(selected),
        "extracted_root_path": str(extracted_root),
        "archive_selected_explicitly": True,
        "package_filename": selected.name,
        "archive_root": EXPECTED_ARCHIVE_ROOT if extracted_root.is_dir() else "",
        "packaged_version": packaged_version,
        "candidate_id": candidate_id,
        "source_manifest_sha256": str(source_manifest.get("manifest_sha256") or ""),
        "archive_manifest_sha256": str(archive_manifest.get("archive_manifest_sha256") or ""),
        "archive_sha256": archive_sha256,
        "archive_entry_count": len(actual_rows),
        "candidate_fresh": candidate_fresh,
        "package_coherent": ok,
        "source_only": bool(privacy.get("ok") and privacy.get("source_only")),
        "contradictions": contradictions,
        "structure_findings": structure_findings,
        "missing_count": len(missing),
        "extra_count": len(extra),
        "modified_count": len(modified),
        "renamed_count": len(renamed),
        "installed": False,
        "promoted": False,
        "certified": False,
        "content_free": True,
        "record_generation": generation,
        "runtime_root_binding": handoff_runtime_binding(runtime_root),
    }
    return _persist_record(
        record,
        runtime_root=runtime_root,
        source_manifest=source_manifest or None,
        archive_manifest=archive_manifest or None,
        activate=activate,
    )


def operator_selected_handoff_status(
    *,
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    """Return bounded status with v1096.1 record and recovery validation."""
    try:
        from release_handoff_recovery import build_handoff_recovery_status
    except ImportError:
        from release_handoff_recovery import build_handoff_recovery_status
    return build_handoff_recovery_status(runtime_root=runtime_root)
