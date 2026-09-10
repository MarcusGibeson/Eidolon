from __future__ import annotations

"""Recovery, replacement, and cleanup for one explicit release handoff.

All exact archive and extraction paths remain in private records below the
external handoff runtime root. No function scans archive directories, installs
source, changes project registries, approves, promotes, or certifies a release.
"""

import json
import os
from pathlib import Path
import shutil
from typing import Any, Callable, Mapping
import uuid

try:
    from metadata_mutation_coordination import MetadataMutationBusy, metadata_mutation_lock
    from release_candidate_identity import atomic_json, build_source_manifest, digest_payload, read_json, sha256_file, utc_now
    from release_handoff_inspection import EXPECTED_ARCHIVE_ROOT, HANDOFF_RECORD_SCHEMA, _public_summary, activate_handoff_record, handoff_directory, handoff_record_binding, handoff_runtime_binding, inspect_selected_candidate_archive
    from version_roles import normalize_version
except ImportError:
    from metadata_mutation_coordination import MetadataMutationBusy, metadata_mutation_lock
    from release_candidate_identity import atomic_json, build_source_manifest, digest_payload, read_json, sha256_file, utc_now
    from release_handoff_inspection import (
        EXPECTED_ARCHIVE_ROOT,
        HANDOFF_RECORD_SCHEMA,
        _public_summary,
        activate_handoff_record,
        handoff_directory,
        handoff_record_binding,
        handoff_runtime_binding,
        inspect_selected_candidate_archive,
    )
    from version_roles import normalize_version

HANDOFF_RECOVERY_CONTRACT_VERSION = "1"
REPLACEMENT_PREVIEW_SCHEMA = "eidolon-handoff-replacement-preview-v1"
RECOVERY_PREVIEW_SCHEMA = "eidolon-handoff-recovery-preview-v1"
CLEANUP_PREVIEW_SCHEMA = "eidolon-handoff-cleanup-preview-v1"
CLEANUP_CONFIRMATION_PHRASE = "REMOVE ABANDONED HANDOFF ARTIFACTS"


def _json_state(path: Path) -> tuple[str, dict[str, Any]]:
    if not path.exists():
        return "missing", {}
    if not path.is_file() or path.is_symlink():
        return "invalid", {}
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return "malformed", {}
    return ("ok", value) if isinstance(value, dict) else ("malformed", {})


def _within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except (OSError, ValueError):
        return False


def _dedupe_findings(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for row in rows:
        kind = str(row.get("kind") or "unknown")
        try:
            count = max(1, int(row.get("count", 1)))
        except (TypeError, ValueError):
            count = 1
        counts[kind] = max(counts.get(kind, 0), count)
    return [{"kind": key, "count": counts[key]} for key in sorted(counts)]


def _record_path(runtime_root: str | Path | None, inspection_id: str) -> Path:
    return handoff_directory(runtime_root) / "records" / f"{inspection_id}.json"


def _preview_directory(runtime_root: str | Path | None, kind: str) -> Path:
    return handoff_directory(runtime_root) / "previews" / kind


def _used_directory(runtime_root: str | Path | None) -> Path:
    return handoff_directory(runtime_root) / "used_tokens"


def _active_private_state(runtime_root: str | Path | None = None) -> dict[str, Any]:
    directory = handoff_directory(runtime_root)
    pointer_path = directory / "active_handoff.json"
    pointer_state, pointer = _json_state(pointer_path)
    findings: list[dict[str, Any]] = []
    if pointer_state == "missing":
        return {
            "ok": True,
            "status": "not_selected",
            "pointer_state": pointer_state,
            "pointer": {},
            "record_state": "missing",
            "record": {},
            "findings": [],
            "runtime_root_binding": handoff_runtime_binding(runtime_root),
            "recoverable": False,
        }
    if pointer_state != "ok":
        findings.append({"kind": f"active_pointer_{pointer_state}"})
        return {
            "ok": False,
            "status": "active_pointer_attention_required",
            "pointer_state": pointer_state,
            "pointer": {},
            "record_state": "unknown",
            "record": {},
            "findings": findings,
            "runtime_root_binding": handoff_runtime_binding(runtime_root),
            "recoverable": False,
        }

    runtime_binding = handoff_runtime_binding(runtime_root)
    if str(pointer.get("schema") or "") != HANDOFF_RECORD_SCHEMA:
        findings.append({"kind": "active_pointer_schema_mismatch"})
    if str(pointer.get("runtime_root_binding") or "") != runtime_binding:
        findings.append({"kind": "active_pointer_runtime_root_mismatch"})
    try:
        generation = int(pointer.get("record_generation") or 0)
    except (TypeError, ValueError):
        generation = 0
    if generation <= 0:
        findings.append({"kind": "active_pointer_generation_missing"})
    inspection_id = str(pointer.get("inspection_id") or "")
    if not inspection_id:
        findings.append({"kind": "active_pointer_inspection_id_missing"})

    record_state, record = _json_state(_record_path(runtime_root, inspection_id)) if inspection_id else ("missing", {})
    if record_state != "ok":
        findings.append({"kind": f"inspection_record_{record_state}"})
    else:
        if str(record.get("schema") or "") != HANDOFF_RECORD_SCHEMA:
            findings.append({"kind": "inspection_record_schema_mismatch"})
        if str(record.get("runtime_root_binding") or "") != runtime_binding:
            findings.append({"kind": "inspection_record_runtime_root_mismatch"})
        try:
            record_generation = int(record.get("record_generation") or 0)
        except (TypeError, ValueError):
            record_generation = 0
        if record_generation != generation:
            findings.append({"kind": "inspection_record_generation_mismatch"})
        if str(record.get("record_binding_sha256") or "") != handoff_record_binding(record):
            findings.append({"kind": "inspection_record_binding_mismatch"})
        for field in (
            "inspection_id",
            "runtime_root_binding",
            "record_generation",
            "archive_sha256",
            "candidate_id",
            "source_manifest_sha256",
            "archive_manifest_sha256",
            "packaged_version",
            "selected_archive_path",
            "extracted_root_path",
        ):
            left = normalize_version(pointer.get(field)) if field == "packaged_version" else pointer.get(field)
            right = normalize_version(record.get(field)) if field == "packaged_version" else record.get(field)
            if str(left or "") != str(right or ""):
                findings.append({"kind": f"active_pointer_{field}_mismatch"})
        if str(pointer.get("record_binding_sha256") or "") != str(record.get("record_binding_sha256") or ""):
            findings.append({"kind": "active_pointer_record_binding_mismatch"})

    binding = record if record_state == "ok" else pointer
    selected_text = str(binding.get("selected_archive_path") or "")
    selected = Path(selected_text) if selected_text else None
    expected_archive_sha = str(binding.get("archive_sha256") or "")
    archive_exact = False
    if not selected_text:
        findings.append({"kind": "selected_archive_path_binding_missing"})
    elif selected is None or selected.is_symlink() or not selected.is_file():
        findings.append({"kind": "selected_archive_missing_or_invalid"})
    else:
        try:
            archive_exact = bool(expected_archive_sha) and sha256_file(selected) == expected_archive_sha
        except OSError:
            archive_exact = False
        if not archive_exact:
            findings.append({"kind": "selected_archive_digest_changed"})

    extracted_text = str(binding.get("extracted_root_path") or "")
    extracted = Path(extracted_text) if extracted_text else None
    extraction_parent = directory / "extractions"
    extraction_bound = bool(extracted and _within(extracted, extraction_parent) and extracted.name == EXPECTED_ARCHIVE_ROOT)
    candidate_fresh = False
    if not extracted_text:
        findings.append({"kind": "inspection_extraction_binding_missing"})
    elif not extraction_bound:
        findings.append({"kind": "inspection_extraction_outside_runtime_root"})
    elif extracted is None or not extracted.is_dir():
        findings.append({"kind": "inspection_extraction_missing"})
    else:
        version = normalize_version(binding.get("packaged_version"))
        expected_manifest = str(binding.get("source_manifest_sha256") or "")
        if not version or not expected_manifest:
            findings.append({"kind": "candidate_identity_binding_incomplete"})
        else:
            try:
                manifest = build_source_manifest(extracted, expected_version=version)
                candidate_fresh = manifest.get("manifest_sha256") == expected_manifest
            except OSError:
                candidate_fresh = False
            if not candidate_fresh:
                findings.append({"kind": "candidate_source_stale"})

    required_identity = all(str(binding.get(field) or "") for field in (
        "archive_sha256", "candidate_id", "source_manifest_sha256", "packaged_version", "selected_archive_path"
    ))
    recoverable = bool(pointer_state == "ok" and generation > 0 and archive_exact and required_identity and str(pointer.get("runtime_root_binding") or "") == runtime_binding)
    findings = _dedupe_findings(findings)
    coherent = not findings and record_state == "ok" and archive_exact and candidate_fresh and bool(record.get("ok"))
    return {
        "ok": coherent,
        "status": "coherent_preview" if coherent else "recovery_required",
        "pointer_state": pointer_state,
        "pointer": pointer,
        "record_state": record_state,
        "record": record,
        "binding": binding,
        "findings": findings,
        "runtime_root_binding": runtime_binding,
        "record_generation": generation,
        "archive_exact": archive_exact,
        "candidate_fresh": candidate_fresh,
        "recoverable": recoverable,
    }


def build_handoff_recovery_status(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    state = _active_private_state(runtime_root)
    if state.get("status") == "not_selected":
        return _public_summary({})
    record = dict(state.get("record") or state.get("pointer") or {})
    record["contradictions"] = list(record.get("contradictions") or []) + list(state.get("findings") or [])
    record["candidate_fresh"] = bool(state.get("candidate_fresh"))
    record["package_coherent"] = bool(state.get("ok"))
    record["ok"] = bool(state.get("ok"))
    record["status"] = str(state.get("status") or "recovery_required")
    public = _public_summary(record)
    public.update({
        "recovery_required": not bool(state.get("ok")),
        "recovery_available": bool(state.get("recoverable")),
        "replacement_requires_explicit_selection": True,
        "active_record_state": str(state.get("record_state") or "unknown"),
        "active_pointer_state": str(state.get("pointer_state") or "unknown"),
        "private_paths_returned": False,
    })
    return public


def _token_material(kind: str, payload: Mapping[str, Any]) -> str:
    return digest_payload({"contract": f"eidolon-handoff-{kind}-token-v1", **dict(payload)})


def _preview_public(record: Mapping[str, Any], *, kind: str) -> dict[str, Any]:
    return {
        "ok": bool(record.get("ok")),
        "status": str(record.get("status") or "attention_required"),
        "contract_version": HANDOFF_RECOVERY_CONTRACT_VERSION,
        "preview_kind": kind,
        "preview_token": str(record.get("preview_token") or ""),
        "operator_confirmation_required": bool(record.get("ok")),
        "literal_confirmation_required": bool(record.get("literal_confirmation_required")),
        "record_generation": int(record.get("active_record_generation") or 0),
        "old_archive_sha256": str(record.get("old_archive_sha256") or ""),
        "new_archive_sha256": str(record.get("new_archive_sha256") or ""),
        "candidate_id": str(record.get("new_candidate_id") or record.get("candidate_id") or ""),
        "source_manifest_sha256": str(record.get("new_source_manifest_sha256") or record.get("source_manifest_sha256") or ""),
        "archive_manifest_sha256": str(record.get("new_archive_manifest_sha256") or record.get("archive_manifest_sha256") or ""),
        "active_preserved": bool(record.get("active_preserved", True)),
        "archive_path_suppressed": True,
        "extraction_path_suppressed": True,
        "directory_scan_performed": False,
        "automatic_selection_performed": False,
        "records_external": True,
        "installed": False,
        "promoted": False,
        "certified": False,
        "project_registry_changed": False,
        "provider_contacted": False,
        "content_free": True,
    }


def _load_preview(runtime_root: str | Path | None, kind: str, token: str) -> dict[str, Any]:
    return read_json(_preview_directory(runtime_root, kind) / f"{token}.json")


def _token_used(runtime_root: str | Path | None, token: str) -> bool:
    return (_used_directory(runtime_root) / f"{token}.json").is_file()


def _mark_used(runtime_root: str | Path | None, token: str, kind: str) -> None:
    atomic_json(_used_directory(runtime_root) / f"{token}.json", {
        "schema": "eidolon-handoff-used-token-v1",
        "preview_token": token,
        "preview_kind": kind,
        "used_at": utc_now(),
        "content_free": True,
    })


def _staged_record(runtime_root: str | Path | None, inspection_id: str) -> dict[str, Any]:
    return read_json(_record_path(runtime_root, inspection_id))


def _staged_record_fresh(record: Mapping[str, Any], runtime_root: str | Path | None) -> bool:
    if not record or not record.get("ok"):
        return False
    if str(record.get("runtime_root_binding") or "") != handoff_runtime_binding(runtime_root):
        return False
    if str(record.get("record_binding_sha256") or "") != handoff_record_binding(record):
        return False
    selected = Path(str(record.get("selected_archive_path") or ""))
    extracted = Path(str(record.get("extracted_root_path") or ""))
    if selected.is_symlink() or not selected.is_file() or not extracted.is_dir():
        return False
    try:
        if sha256_file(selected) != str(record.get("archive_sha256") or ""):
            return False
        manifest = build_source_manifest(extracted, expected_version=normalize_version(record.get("packaged_version")))
    except OSError:
        return False
    return manifest.get("manifest_sha256") == str(record.get("source_manifest_sha256") or "")


def preview_handoff_replacement(
    archive_path: str | Path,
    *,
    runtime_root: str | Path | None = None,
    fault_hook: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    state = _active_private_state(runtime_root)
    if not state.get("ok"):
        return {**build_handoff_recovery_status(runtime_root=runtime_root), "ok": False, "status": "active_handoff_must_be_coherent"}
    selected = Path(str(archive_path or "").strip()).expanduser().absolute()
    if not str(archive_path or "").strip():
        raise ValueError("archive_path is required; replacement archives are never discovered automatically")
    active = dict(state.get("record") or {})
    try:
        new_sha = sha256_file(selected)
    except OSError:
        return {**_public_summary(active), "ok": False, "status": "replacement_archive_unreadable", "active_preserved": True}
    if new_sha == str(active.get("archive_sha256") or ""):
        return {**_public_summary(active), "ok": False, "status": "replacement_matches_active_archive", "active_preserved": True}

    preview_nonce = uuid.uuid4().hex
    staged_id = f"handoff-replacement-preview-{preview_nonce}"
    staged_public = inspect_selected_candidate_archive(
        selected,
        runtime_root=runtime_root,
        activate=False,
        inspection_id_override=staged_id,
        record_generation=int(state.get("record_generation") or 0) + 1,
    )
    if fault_hook:
        fault_hook("after_replacement_inspection")
    if not staged_public.get("ok"):
        return {**staged_public, "status": "replacement_inspection_failed", "active_preserved": True}
    staged = _staged_record(runtime_root, staged_id)
    material = {
        "action": "replace_active_handoff",
        "runtime_root_binding": str(state.get("runtime_root_binding") or ""),
        "active_record_generation": int(state.get("record_generation") or 0),
        "active_record_binding_sha256": str(active.get("record_binding_sha256") or ""),
        "old_archive_sha256": str(active.get("archive_sha256") or ""),
        "new_archive_sha256": str(staged.get("archive_sha256") or ""),
        "new_candidate_id": str(staged.get("candidate_id") or ""),
        "new_source_manifest_sha256": str(staged.get("source_manifest_sha256") or ""),
        "new_archive_manifest_sha256": str(staged.get("archive_manifest_sha256") or ""),
        "staged_inspection_id": staged_id,
    }
    token = _token_material("replacement", material)
    record = {
        "schema": REPLACEMENT_PREVIEW_SCHEMA,
        "preview_token": token,
        "created_at": utc_now(),
        "status": "replacement_confirmation_required",
        "ok": True,
        **material,
        "new_archive_path": str(selected),
        "active_preserved": True,
        "literal_confirmation_required": False,
        "content_free": True,
    }
    atomic_json(_preview_directory(runtime_root, "replacement") / f"{token}.json", record)
    if fault_hook:
        fault_hook("after_replacement_preview_persisted")
    return _preview_public(record, kind="replacement")


def confirm_handoff_replacement(
    *,
    preview_token: str,
    operator_confirmed: bool,
    runtime_root: str | Path | None = None,
    fault_hook: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    token = str(preview_token or "").strip()
    if operator_confirmed is not True:
        return {"ok": False, "status": "literal_confirmation_required", "content_free": True}
    if not token or _token_used(runtime_root, token):
        return {"ok": False, "status": "stale_reused_or_mismatched_preview", "stale_confirmation": True, "content_free": True}
    preview = _load_preview(runtime_root, "replacement", token)
    if not preview or str(preview.get("schema") or "") != REPLACEMENT_PREVIEW_SCHEMA:
        return {"ok": False, "status": "stale_reused_or_mismatched_preview", "stale_confirmation": True, "content_free": True}
    material = {key: preview.get(key) for key in (
        "action", "runtime_root_binding", "active_record_generation", "active_record_binding_sha256",
        "old_archive_sha256", "new_archive_sha256", "new_candidate_id", "new_source_manifest_sha256",
        "new_archive_manifest_sha256", "staged_inspection_id",
    )}
    if token != _token_material("replacement", material):
        return {"ok": False, "status": "stale_reused_or_mismatched_preview", "stale_confirmation": True, "content_free": True}
    active_path = handoff_directory(runtime_root) / "active_handoff.json"
    try:
        with metadata_mutation_lock(active_path, timeout_seconds=5.0):
            state = _active_private_state(runtime_root)
            active = dict(state.get("record") or {})
            if (
                not state.get("ok")
                or int(state.get("record_generation") or 0) != int(preview.get("active_record_generation") or 0)
                or str(active.get("record_binding_sha256") or "") != str(preview.get("active_record_binding_sha256") or "")
                or str(active.get("archive_sha256") or "") != str(preview.get("old_archive_sha256") or "")
            ):
                return {"ok": False, "status": "stale_reused_or_mismatched_preview", "stale_confirmation": True, "content_free": True}
            staged = _staged_record(runtime_root, str(preview.get("staged_inspection_id") or ""))
            if (
                not _staged_record_fresh(staged, runtime_root)
                or str(staged.get("archive_sha256") or "") != str(preview.get("new_archive_sha256") or "")
                or str(staged.get("candidate_id") or "") != str(preview.get("new_candidate_id") or "")
                or str(staged.get("source_manifest_sha256") or "") != str(preview.get("new_source_manifest_sha256") or "")
                or str(staged.get("archive_manifest_sha256") or "") != str(preview.get("new_archive_manifest_sha256") or "")
            ):
                return {"ok": False, "status": "replacement_candidate_changed", "stale_confirmation": True, "active_preserved": True, "content_free": True}
            if fault_hook:
                fault_hook("before_replacement_activation")
            result = activate_handoff_record(
                str(preview.get("staged_inspection_id") or ""),
                runtime_root=runtime_root,
                expected_generation=int(preview.get("active_record_generation") or 0),
            )
            if not result.get("ok"):
                return {**result, "active_preserved": True}
            if fault_hook:
                fault_hook("after_replacement_activation")
            _mark_used(runtime_root, token, "replacement")
            return {
                **result,
                "status": "handoff_replaced",
                "replacement_applied": True,
                "previous_archive_preserved_in_history": True,
                "installation_changed": False,
                "promotion_changed": False,
                "certification_performed": False,
            }
    except MetadataMutationBusy:
        return {"ok": False, "status": "handoff_mutation_busy", "safe_retry": True, "content_free": True}


def preview_handoff_recovery(
    *,
    runtime_root: str | Path | None = None,
    fault_hook: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    state = _active_private_state(runtime_root)
    if state.get("ok"):
        return {**build_handoff_recovery_status(runtime_root=runtime_root), "status": "already_coherent", "recovery_required": False}
    if not state.get("recoverable"):
        return {**build_handoff_recovery_status(runtime_root=runtime_root), "ok": False, "status": "explicit_archive_selection_required"}
    binding = dict(state.get("binding") or {})
    staged_id = f"handoff-recovery-preview-{uuid.uuid4().hex}"
    staged_public = inspect_selected_candidate_archive(
        str(binding.get("selected_archive_path") or ""),
        runtime_root=runtime_root,
        activate=False,
        inspection_id_override=staged_id,
        record_generation=int(state.get("record_generation") or 0) + 1,
    )
    if fault_hook:
        fault_hook("after_recovery_inspection")
    if not staged_public.get("ok"):
        return {**staged_public, "status": "recovery_reinspection_failed", "active_preserved": True}
    staged = _staged_record(runtime_root, staged_id)
    if (
        str(staged.get("archive_sha256") or "") != str(binding.get("archive_sha256") or "")
        or str(staged.get("candidate_id") or "") != str(binding.get("candidate_id") or "")
        or str(staged.get("source_manifest_sha256") or "") != str(binding.get("source_manifest_sha256") or "")
    ):
        return {**staged_public, "ok": False, "status": "recovery_identity_contradiction", "active_preserved": True}
    material = {
        "action": "reconcile_exact_active_handoff",
        "runtime_root_binding": str(state.get("runtime_root_binding") or ""),
        "active_record_generation": int(state.get("record_generation") or 0),
        "active_record_binding_sha256": str(binding.get("record_binding_sha256") or state.get("pointer", {}).get("record_binding_sha256") or ""),
        "archive_sha256": str(staged.get("archive_sha256") or ""),
        "candidate_id": str(staged.get("candidate_id") or ""),
        "source_manifest_sha256": str(staged.get("source_manifest_sha256") or ""),
        "archive_manifest_sha256": str(staged.get("archive_manifest_sha256") or ""),
        "staged_inspection_id": staged_id,
    }
    token = _token_material("recovery", material)
    record = {
        "schema": RECOVERY_PREVIEW_SCHEMA,
        "preview_token": token,
        "created_at": utc_now(),
        "status": "recovery_confirmation_required",
        "ok": True,
        **material,
        "active_preserved": True,
        "literal_confirmation_required": False,
        "content_free": True,
    }
    atomic_json(_preview_directory(runtime_root, "recovery") / f"{token}.json", record)
    return _preview_public(record, kind="recovery")


def confirm_handoff_recovery(
    *,
    preview_token: str,
    operator_confirmed: bool,
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    token = str(preview_token or "").strip()
    if operator_confirmed is not True:
        return {"ok": False, "status": "literal_confirmation_required", "content_free": True}
    if not token or _token_used(runtime_root, token):
        return {"ok": False, "status": "stale_reused_or_mismatched_preview", "stale_confirmation": True, "content_free": True}
    preview = _load_preview(runtime_root, "recovery", token)
    if not preview or str(preview.get("schema") or "") != RECOVERY_PREVIEW_SCHEMA:
        return {"ok": False, "status": "stale_reused_or_mismatched_preview", "stale_confirmation": True, "content_free": True}
    material = {key: preview.get(key) for key in (
        "action", "runtime_root_binding", "active_record_generation", "active_record_binding_sha256",
        "archive_sha256", "candidate_id", "source_manifest_sha256", "archive_manifest_sha256", "staged_inspection_id",
    )}
    if token != _token_material("recovery", material):
        return {"ok": False, "status": "stale_reused_or_mismatched_preview", "stale_confirmation": True, "content_free": True}
    active_path = handoff_directory(runtime_root) / "active_handoff.json"
    try:
        with metadata_mutation_lock(active_path, timeout_seconds=5.0):
            state = _active_private_state(runtime_root)
            binding = dict(state.get("binding") or {})
            if (
                int(state.get("record_generation") or 0) != int(preview.get("active_record_generation") or 0)
                or str(binding.get("archive_sha256") or "") != str(preview.get("archive_sha256") or "")
                or str(binding.get("candidate_id") or "") != str(preview.get("candidate_id") or "")
                or str(binding.get("source_manifest_sha256") or "") != str(preview.get("source_manifest_sha256") or "")
            ):
                return {"ok": False, "status": "stale_reused_or_mismatched_preview", "stale_confirmation": True, "content_free": True}
            staged = _staged_record(runtime_root, str(preview.get("staged_inspection_id") or ""))
            if not _staged_record_fresh(staged, runtime_root):
                return {"ok": False, "status": "recovery_candidate_changed", "active_preserved": True, "content_free": True}
            result = activate_handoff_record(
                str(preview.get("staged_inspection_id") or ""),
                runtime_root=runtime_root,
                expected_generation=int(preview.get("active_record_generation") or 0),
            )
            if not result.get("ok"):
                return {**result, "active_preserved": True}
            _mark_used(runtime_root, token, "recovery")
            return {**result, "status": "handoff_recovered", "recovery_applied": True}
    except MetadataMutationBusy:
        return {"ok": False, "status": "handoff_mutation_busy", "safe_retry": True, "content_free": True}


def _artifact_fingerprint(path: Path, root: Path) -> str:
    if not _within(path, root) or path.is_symlink():
        return ""
    rows: list[dict[str, Any]] = []
    if path.is_file():
        try:
            rows.append({"path": path.relative_to(root).as_posix(), "sha256": sha256_file(path), "size": path.stat().st_size})
        except OSError:
            return ""
    elif path.is_dir():
        for child in sorted(path.rglob("*")):
            if child.is_symlink():
                return ""
            if child.is_file():
                try:
                    rows.append({"path": child.relative_to(root).as_posix(), "sha256": sha256_file(child), "size": child.stat().st_size})
                except OSError:
                    return ""
    else:
        return ""
    return digest_payload({"contract": "eidolon-handoff-cleanup-artifact-v1", "rows": rows})


def _referenced_extraction_parents(runtime_root: str | Path | None) -> set[Path]:
    directory = handoff_directory(runtime_root)
    references: set[Path] = set()
    state = _active_private_state(runtime_root)
    binding = dict(state.get("binding") or {})
    active_root = str(binding.get("extracted_root_path") or "")
    if active_root:
        references.add(Path(active_root).parent.resolve())
    for kind in ("replacement", "recovery"):
        preview_dir = _preview_directory(runtime_root, kind)
        if not preview_dir.is_dir():
            continue
        for preview_path in preview_dir.glob("*.json"):
            preview = read_json(preview_path)
            token = str(preview.get("preview_token") or "")
            if not token or _token_used(runtime_root, token):
                continue
            staged = _staged_record(runtime_root, str(preview.get("staged_inspection_id") or ""))
            extracted = str(staged.get("extracted_root_path") or "")
            if extracted:
                references.add(Path(extracted).parent.resolve())
    return references


def preview_abandoned_handoff_cleanup(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    directory = handoff_directory(runtime_root)
    extraction_root = directory / "extractions"
    references = _referenced_extraction_parents(runtime_root)
    artifacts: list[dict[str, Any]] = []
    if extraction_root.is_dir():
        for child in sorted(extraction_root.iterdir()):
            resolved = child.resolve()
            if resolved in references or child.is_symlink() or not _within(child, extraction_root):
                continue
            fingerprint = _artifact_fingerprint(child, extraction_root)
            if fingerprint:
                artifacts.append({"relative_path": child.relative_to(directory).as_posix(), "fingerprint": fingerprint})
    active_generation = int(_active_private_state(runtime_root).get("record_generation") or 0)
    material = {
        "action": "remove_abandoned_handoff_artifacts",
        "runtime_root_binding": handoff_runtime_binding(runtime_root),
        "active_record_generation": active_generation,
        "artifacts": artifacts,
    }
    token = _token_material("cleanup", material)
    record = {
        "schema": CLEANUP_PREVIEW_SCHEMA,
        "preview_token": token,
        "created_at": utc_now(),
        "status": "cleanup_confirmation_required" if artifacts else "nothing_to_clean",
        "ok": True,
        **material,
        "artifact_count": len(artifacts),
        "literal_confirmation_required": bool(artifacts),
        "confirmation_phrase": CLEANUP_CONFIRMATION_PHRASE,
        "content_free": True,
    }
    atomic_json(_preview_directory(runtime_root, "cleanup") / f"{token}.json", record)
    public = _preview_public(record, kind="cleanup")
    public.update({
        "artifact_count": len(artifacts),
        "cleanup_available": bool(artifacts),
        "confirmation_phrase": CLEANUP_CONFIRMATION_PHRASE if artifacts else "",
    })
    return public


def confirm_abandoned_handoff_cleanup(
    *,
    preview_token: str,
    operator_confirmed: bool,
    confirmation_phrase: str,
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    token = str(preview_token or "").strip()
    if operator_confirmed is not True or str(confirmation_phrase or "") != CLEANUP_CONFIRMATION_PHRASE:
        return {"ok": False, "status": "literal_confirmation_required", "content_free": True}
    if not token or _token_used(runtime_root, token):
        return {"ok": False, "status": "stale_reused_or_mismatched_preview", "stale_confirmation": True, "content_free": True}
    preview = _load_preview(runtime_root, "cleanup", token)
    if not preview or str(preview.get("schema") or "") != CLEANUP_PREVIEW_SCHEMA:
        return {"ok": False, "status": "stale_reused_or_mismatched_preview", "stale_confirmation": True, "content_free": True}
    material = {key: preview.get(key) for key in ("action", "runtime_root_binding", "active_record_generation", "artifacts")}
    if token != _token_material("cleanup", material):
        return {"ok": False, "status": "stale_reused_or_mismatched_preview", "stale_confirmation": True, "content_free": True}
    directory = handoff_directory(runtime_root)
    extraction_root = directory / "extractions"
    state = _active_private_state(runtime_root)
    if int(state.get("record_generation") or 0) != int(preview.get("active_record_generation") or 0):
        return {"ok": False, "status": "stale_reused_or_mismatched_preview", "stale_confirmation": True, "content_free": True}
    references = _referenced_extraction_parents(runtime_root)
    targets: list[Path] = []
    for row in preview.get("artifacts") or []:
        relative = str(row.get("relative_path") or "")
        target = directory / relative
        if (
            not relative.startswith("extractions/")
            or not _within(target, extraction_root)
            or target.resolve() in references
            or target.is_symlink()
            or _artifact_fingerprint(target, extraction_root) != str(row.get("fingerprint") or "")
        ):
            return {"ok": False, "status": "stale_reused_or_mismatched_preview", "stale_confirmation": True, "content_free": True}
        targets.append(target)
    removed = 0
    for target in targets:
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()
        removed += 1
    _mark_used(runtime_root, token, "cleanup")
    return {
        "ok": True,
        "status": "abandoned_handoff_artifacts_removed",
        "removed_count": removed,
        "active_handoff_preserved": True,
        "installed": False,
        "promoted": False,
        "certified": False,
        "content_free": True,
    }
