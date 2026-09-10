from __future__ import annotations

"""Exact refresh, recovery, replacement, and cleanup for release readiness.

All detailed records live below an external runtime root.  These operations
refresh or acknowledge read-only authority summaries only; they never install,
promote, certify, migrate policy, contact providers, or modify models.
"""

from collections import Counter
import json
from pathlib import Path
import secrets
from typing import Any, Iterable, Mapping

try:
    from release_candidate_identity import atomic_json, digest_payload, read_json, sha256_file, utc_now
    from release_authority_readiness import READINESS_SCHEMA, _binding, _current_components, _public as readiness_public, _record_digest as readiness_record_digest, _runtime_identity, _summary, release_authority_readiness_directory, release_authority_readiness_status
except ImportError:
    from release_candidate_identity import atomic_json, digest_payload, read_json, sha256_file, utc_now
    from release_authority_readiness import (
        READINESS_SCHEMA,
        _binding,
        _current_components,
        _public as readiness_public,
        _record_digest as readiness_record_digest,
        _runtime_identity,
        _summary,
        release_authority_readiness_directory,
        release_authority_readiness_status,
    )

READINESS_RECOVERY_CONTRACT_VERSION = "1"
REFRESH_SCHEMA = "eidolon-release-authority-readiness-refresh-v1"
REPLACEMENT_SCHEMA = "eidolon-release-authority-readiness-replacement-v1"
CLEANUP_SCHEMA = "eidolon-release-authority-readiness-cleanup-v1"
REFRESH_RECOVERY_CONFIRMATION = "RESUME EXACT RELEASE AUTHORITY READINESS REFRESH"
REPLACEMENT_CONFIRMATION = "REPLACE EXACT RELEASE AUTHORITY READINESS SNAPSHOT"
CLEANUP_CONFIRMATION = "REMOVE ABANDONED RELEASE AUTHORITY READINESS ARTIFACTS"


def _counts(rows: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    found: Counter[str] = Counter()
    for row in rows or []:
        found[str(row.get("kind") or "unknown")] += max(1, int(row.get("count") or 1))
    return [{"kind": key, "count": found[key]} for key in sorted(found)]


def _record_digest(record: Mapping[str, Any]) -> str:
    material = dict(record)
    material.pop("record_sha256", None)
    return digest_payload(material)


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


def _directory(runtime_root: str | Path | None) -> Path:
    return release_authority_readiness_directory(runtime_root)


def _used_token_path(runtime_root: str | Path | None, token: str) -> Path:
    return _directory(runtime_root) / "used_tokens" / f"{digest_payload({'token': token})}.json"


def _authorization_token(auth: Mapping[str, Any]) -> str:
    return ".".join((str(auth.get("token_id") or ""), str(auth.get("binding_sha256") or ""), str(auth.get("nonce") or "")))


def _load_authorization(runtime_root: str | Path | None, category: str, token: str) -> dict[str, Any]:
    parts = token.split(".") if isinstance(token, str) else []
    if len(parts) != 3:
        return {}
    auth = read_json(_directory(runtime_root) / "authorizations" / category / f"{parts[0]}.json")
    if not auth:
        return {}
    expected = digest_payload({key: value for key, value in auth.items() if key != "binding_sha256"})
    if parts != [str(auth.get("token_id") or ""), str(auth.get("binding_sha256") or ""), str(auth.get("nonce") or "")]:
        return {}
    if str(auth.get("binding_sha256") or "") != expected:
        return {}
    return auth


def _active_private(runtime_root: str | Path | None) -> dict[str, Any]:
    directory = _directory(runtime_root)
    pointer_state, pointer = _json_state(directory / "active_readiness.json")
    findings: list[dict[str, Any]] = []
    if pointer_state != "ok":
        if pointer_state != "missing":
            findings.append({"kind": f"active_readiness_pointer_{pointer_state}"})
        return {
            "ok": pointer_state == "missing",
            "status": "readiness_not_active" if pointer_state == "missing" else "readiness_pointer_attention_required",
            "pointer_state": pointer_state,
            "pointer": {},
            "record_state": "missing",
            "record": {},
            "findings": findings,
        }
    preview_id = str(pointer.get("preview_id") or "")
    record_state, record = _json_state(directory / "previews" / f"{preview_id}.json") if preview_id else ("missing", {})
    if not preview_id:
        findings.append({"kind": "active_readiness_preview_id_missing"})
    if record_state != "ok":
        findings.append({"kind": f"active_readiness_record_{record_state}"})
    else:
        if str(record.get("schema") or "") != READINESS_SCHEMA:
            findings.append({"kind": "active_readiness_record_schema_mismatch"})
        if str(record.get("record_sha256") or "") != readiness_record_digest(record):
            findings.append({"kind": "active_readiness_record_digest_mismatch"})
        for field in ("preview_id", "generation", "readiness_binding_sha256", "record_sha256"):
            if str(pointer.get(field) or "") != str(record.get(field) or ""):
                findings.append({"kind": f"active_readiness_pointer_{field}_mismatch"})
        if str(record.get("runtime_root_identity_sha256") or "") != _runtime_identity(runtime_root):
            findings.append({"kind": "active_readiness_runtime_root_mismatch"})
    return {
        "ok": not findings,
        "status": "active_readiness_coherent" if not findings else "active_readiness_attention_required",
        "pointer_state": pointer_state,
        "pointer": pointer,
        "record_state": record_state,
        "record": record,
        "findings": _counts(findings),
    }


def _build_snapshot(runtime_root: str | Path | None, generation: int, *, reason: str, source_preview_id: str = "") -> dict[str, Any]:
    components = _current_components(runtime_root)
    summary = _summary(components, runtime_root)
    record = {
        "schema": READINESS_SCHEMA,
        "preview_id": f"release-authority-readiness-{generation}-{secrets.token_hex(8)}",
        "generation": int(generation),
        "created_at": utc_now(),
        "refresh_reason": reason,
        "source_preview_id": source_preview_id,
        **summary,
    }
    binding = _binding(components, runtime_root)
    record["readiness_binding_sha256"] = digest_payload({key: record.get(key) for key in sorted(binding)})
    record["record_sha256"] = readiness_record_digest(record)
    return record


def _activate_snapshot(runtime_root: str | Path | None, record: Mapping[str, Any]) -> None:
    atomic_json(_directory(runtime_root) / "active_readiness.json", {
        "schema": READINESS_SCHEMA,
        "preview_id": str(record.get("preview_id") or ""),
        "generation": int(record.get("generation") or 0),
        "readiness_binding_sha256": str(record.get("readiness_binding_sha256") or ""),
        "record_sha256": str(record.get("record_sha256") or ""),
        "content_free": True,
    })


def _refresh_digest(record: Mapping[str, Any]) -> str:
    return digest_payload({
        "schema": REFRESH_SCHEMA,
        "refresh_id": str(record.get("refresh_id") or ""),
        "runtime_root_identity_sha256": str(record.get("runtime_root_identity_sha256") or ""),
        "previous_preview_id": str(record.get("previous_preview_id") or ""),
        "previous_generation": int(record.get("previous_generation") or 0),
        "previous_record_sha256": str(record.get("previous_record_sha256") or ""),
        "proposed_preview_id": str(record.get("proposed_preview_id") or ""),
        "proposed_generation": int(record.get("proposed_generation") or 0),
        "proposed_record_sha256": str(record.get("proposed_record_sha256") or ""),
        "proposed_readiness_binding_sha256": str(record.get("proposed_readiness_binding_sha256") or ""),
        "status": str(record.get("status") or ""),
    })


def _public(record: Mapping[str, Any] | None) -> dict[str, Any]:
    row = dict(record or {})
    findings = _counts(row.get("findings") if isinstance(row.get("findings"), list) else [])
    return {
        "ok": bool(row.get("ok")) and not findings,
        "status": str(row.get("status") or "release_authority_refresh_unavailable"),
        "contract_version": READINESS_RECOVERY_CONTRACT_VERSION,
        "refresh_id": str(row.get("refresh_id") or ""),
        "refresh_generation": int(row.get("refresh_generation") or row.get("proposed_generation") or 0),
        "previous_preview_id": str(row.get("previous_preview_id") or ""),
        "previous_generation": int(row.get("previous_generation") or 0),
        "proposed_preview_id": str(row.get("proposed_preview_id") or ""),
        "proposed_generation": int(row.get("proposed_generation") or 0),
        "active_preview_id": str(row.get("active_preview_id") or ""),
        "active_generation": int(row.get("active_generation") or 0),
        "runtime_root_identity_sha256": str(row.get("runtime_root_identity_sha256") or ""),
        "readiness_binding_sha256": str(row.get("readiness_binding_sha256") or row.get("proposed_readiness_binding_sha256") or ""),
        "record_sha256": str(row.get("record_sha256") or ""),
        "recovery_available": bool(row.get("recovery_available")),
        "replacement_available": bool(row.get("replacement_available")),
        "cleanup_available": bool(row.get("cleanup_available")),
        "authorization_token": str(row.get("authorization_token") or ""),
        "literal_confirmation_required": str(row.get("literal_confirmation_required") or ""),
        "artifact_count": int(row.get("artifact_count") or 0),
        "findings": findings,
        "finding_count": sum(int(item["count"]) for item in findings),
        "previous_coherent_snapshot_preserved": bool(row.get("previous_coherent_snapshot_preserved", True)),
        "duplicate_execution_allowed": False,
        "read_only": True,
        "preview_first": True,
        "paths_suppressed": True,
        "records_external": True,
        "content_free": True,
        "ordinary_conversation_affected": False,
        "provider_contacted": False,
        "native_checks_run": False,
        "models_mutated": False,
        "source_files_mutated": False,
        "installed_source_mutated": False,
        "installation_changed": False,
        "promotion_changed": False,
        "certification_changed": False,
        "policy_migrated": False,
    }


def refresh_release_authority_readiness(*, runtime_root: str | Path | None = None, interrupt_after: str = "") -> dict[str, Any]:
    active = _active_private(runtime_root)
    current_status = release_authority_readiness_status(runtime_root=runtime_root)
    if not active.get("ok") or not current_status.get("ok"):
        return _public({"ok": False, "status": "coherent_active_readiness_required", "findings": active.get("findings") or [{"kind": "coherent_active_readiness_required"}]})
    pointer = active["pointer"]
    previous = active["record"]
    generation = int(pointer.get("generation") or 0) + 1
    proposed = _build_snapshot(runtime_root, generation, reason="refresh", source_preview_id=str(previous.get("preview_id") or ""))
    directory = _directory(runtime_root)
    refresh_id = f"readiness-refresh-{generation}-{secrets.token_hex(8)}"
    record = {
        "schema": REFRESH_SCHEMA,
        "refresh_id": refresh_id,
        "created_at": utc_now(),
        "runtime_root_identity_sha256": _runtime_identity(runtime_root),
        "previous_preview_id": str(previous.get("preview_id") or ""),
        "previous_generation": int(previous.get("generation") or 0),
        "previous_record_sha256": str(previous.get("record_sha256") or ""),
        "proposed_preview_id": str(proposed.get("preview_id") or ""),
        "proposed_generation": int(proposed.get("generation") or 0),
        "proposed_record_sha256": str(proposed.get("record_sha256") or ""),
        "proposed_readiness_binding_sha256": str(proposed.get("readiness_binding_sha256") or ""),
        "status": "refresh_prepared",
        "ok": bool(proposed.get("ok")),
        "content_free": True,
    }
    record["refresh_binding_sha256"] = _refresh_digest(record)
    record["record_sha256"] = _record_digest(record)
    atomic_json(directory / "refreshes" / f"{refresh_id}.json", record)
    atomic_json(directory / "previews" / f"{proposed['preview_id']}.json", proposed)
    atomic_json(directory / "active_refresh.json", {
        "schema": REFRESH_SCHEMA,
        "refresh_id": refresh_id,
        "refresh_binding_sha256": record["refresh_binding_sha256"],
        "record_sha256": record["record_sha256"],
        "content_free": True,
    })
    if not proposed.get("ok"):
        record["status"] = "refresh_failed"
        record["ok"] = False
        record["refresh_binding_sha256"] = _refresh_digest(record)
        record["record_sha256"] = _record_digest(record)
        atomic_json(directory / "refreshes" / f"{refresh_id}.json", record)
        atomic_json(directory / "last_failed_refresh.json", record)
        return _public({**record, "previous_coherent_snapshot_preserved": True, "findings": proposed.get("findings") or [{"kind": "refreshed_readiness_not_coherent"}]})
    if interrupt_after in {"prepared", "preview_written", "before_activation"}:
        record["status"] = "refresh_interrupted"
        record["ok"] = False
        record["refresh_binding_sha256"] = _refresh_digest(record)
        record["record_sha256"] = _record_digest(record)
        atomic_json(directory / "refreshes" / f"{refresh_id}.json", record)
        atomic_json(directory / "active_refresh.json", {
            "schema": REFRESH_SCHEMA,
            "refresh_id": refresh_id,
            "refresh_binding_sha256": record["refresh_binding_sha256"],
            "record_sha256": record["record_sha256"],
            "content_free": True,
        })
        return _public({**record, "status": "readiness_refresh_interrupted", "recovery_available": True, "previous_coherent_snapshot_preserved": True})
    _activate_snapshot(runtime_root, proposed)
    record["status"] = "refresh_complete"
    record["ok"] = True
    record["completed_at"] = utc_now()
    record["refresh_binding_sha256"] = _refresh_digest(record)
    record["record_sha256"] = _record_digest(record)
    atomic_json(directory / "refreshes" / f"{refresh_id}.json", record)
    atomic_json(directory / "active_refresh.json", {
        "schema": REFRESH_SCHEMA,
        "refresh_id": refresh_id,
        "refresh_binding_sha256": record["refresh_binding_sha256"],
        "record_sha256": record["record_sha256"],
        "content_free": True,
    })
    return _public({**record, "status": "release_authority_readiness_refreshed", "active_preview_id": proposed["preview_id"], "active_generation": generation})


def readiness_refresh_status(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    directory = _directory(runtime_root)
    pointer_state, pointer = _json_state(directory / "active_refresh.json")
    active = _active_private(runtime_root)
    if pointer_state == "missing":
        return _public({"ok": True, "status": "readiness_refresh_not_started", "active_preview_id": active.get("record", {}).get("preview_id"), "active_generation": active.get("record", {}).get("generation")})
    findings: list[dict[str, Any]] = []
    if pointer_state != "ok":
        findings.append({"kind": f"readiness_refresh_pointer_{pointer_state}"})
        return _public({"ok": False, "status": "readiness_refresh_attention_required", "findings": findings})
    refresh_id = str(pointer.get("refresh_id") or "")
    record_state, record = _json_state(directory / "refreshes" / f"{refresh_id}.json") if refresh_id else ("missing", {})
    if record_state != "ok":
        findings.append({"kind": f"readiness_refresh_record_{record_state}"})
    else:
        if str(record.get("record_sha256") or "") != _record_digest(record):
            findings.append({"kind": "readiness_refresh_record_digest_mismatch"})
        if str(record.get("refresh_binding_sha256") or "") != _refresh_digest(record):
            findings.append({"kind": "readiness_refresh_binding_mismatch"})
        for field in ("refresh_id", "refresh_binding_sha256", "record_sha256"):
            if str(pointer.get(field) or "") != str(record.get(field) or ""):
                findings.append({"kind": f"readiness_refresh_pointer_{field}_mismatch"})
        if str(record.get("runtime_root_identity_sha256") or "") != _runtime_identity(runtime_root):
            findings.append({"kind": "readiness_refresh_runtime_root_mismatch"})
    status = str(record.get("status") or "")
    recovery = status == "refresh_interrupted" and not findings
    return _public({
        **record,
        "ok": not findings and status == "refresh_complete",
        "status": "release_authority_readiness_refreshed" if not findings and status == "refresh_complete" else ("readiness_refresh_interrupted" if recovery else "readiness_refresh_attention_required"),
        "recovery_available": recovery,
        "active_preview_id": active.get("record", {}).get("preview_id"),
        "active_generation": active.get("record", {}).get("generation"),
        "findings": findings,
    })


def preview_readiness_refresh_recovery(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    status = readiness_refresh_status(runtime_root=runtime_root)
    if not status.get("recovery_available"):
        return _public({"ok": False, "status": "readiness_refresh_recovery_unavailable", "findings": [{"kind": "interrupted_refresh_required"}]})
    directory = _directory(runtime_root)
    pointer = read_json(directory / "active_refresh.json")
    refresh = read_json(directory / "refreshes" / f"{pointer.get('refresh_id','')}.json")
    active = _active_private(runtime_root)
    proposed = read_json(directory / "previews" / f"{refresh.get('proposed_preview_id','')}.json")
    findings: list[dict[str, Any]] = []
    if not active.get("ok"):
        findings.append({"kind": "previous_active_readiness_not_coherent"})
    if str(active.get("record", {}).get("preview_id") or "") != str(refresh.get("previous_preview_id") or ""):
        findings.append({"kind": "previous_active_readiness_changed"})
    if str(active.get("record", {}).get("record_sha256") or "") != str(refresh.get("previous_record_sha256") or ""):
        findings.append({"kind": "previous_active_readiness_digest_changed"})
    if not proposed or str(proposed.get("record_sha256") or "") != readiness_record_digest(proposed):
        findings.append({"kind": "proposed_readiness_record_invalid"})
    current = release_authority_readiness_status(runtime_root=runtime_root)
    if not current.get("ok"):
        findings.append({"kind": "current_authority_not_coherent"})
    components = _current_components(runtime_root)
    expected_binding = digest_payload({key: _summary(components, runtime_root).get(key) for key in sorted(_binding(components, runtime_root))})
    if str(proposed.get("readiness_binding_sha256") or "") != expected_binding:
        findings.append({"kind": "proposed_readiness_stale"})
    if findings:
        return _public({"ok": False, "status": "readiness_refresh_recovery_blocked", "findings": findings})
    token_id = f"readiness-refresh-recovery-{secrets.token_hex(8)}"
    nonce = secrets.token_hex(16)
    auth = {
        "schema": "eidolon-release-authority-readiness-refresh-recovery-authorization-v1",
        "token_id": token_id,
        "nonce": nonce,
        "runtime_root_identity_sha256": _runtime_identity(runtime_root),
        "refresh_id": str(refresh.get("refresh_id") or ""),
        "refresh_binding_sha256": str(refresh.get("refresh_binding_sha256") or ""),
        "previous_preview_id": str(refresh.get("previous_preview_id") or ""),
        "previous_record_sha256": str(refresh.get("previous_record_sha256") or ""),
        "proposed_preview_id": str(refresh.get("proposed_preview_id") or ""),
        "proposed_record_sha256": str(refresh.get("proposed_record_sha256") or ""),
        "proposed_readiness_binding_sha256": str(refresh.get("proposed_readiness_binding_sha256") or ""),
        "action": "resume_exact_release_authority_readiness_refresh",
        "content_free": True,
    }
    auth["binding_sha256"] = digest_payload(auth)
    atomic_json(directory / "authorizations" / "refresh_recovery" / f"{token_id}.json", auth)
    return _public({**refresh, "ok": True, "status": "readiness_refresh_recovery_previewed", "recovery_available": True, "authorization_token": _authorization_token(auth), "literal_confirmation_required": REFRESH_RECOVERY_CONFIRMATION})


def resume_release_authority_readiness_refresh(token: str, *, confirm: str, runtime_root: str | Path | None = None) -> dict[str, Any]:
    if confirm != REFRESH_RECOVERY_CONFIRMATION:
        return _public({"ok": False, "status": "literal_confirmation_required", "findings": [{"kind": "literal_confirmation_required"}]})
    auth = _load_authorization(runtime_root, "refresh_recovery", token)
    if not auth:
        return _public({"ok": False, "status": "readiness_refresh_recovery_token_invalid", "findings": [{"kind": "readiness_refresh_recovery_token_invalid"}]})
    used = _used_token_path(runtime_root, token)
    if used.is_file():
        return _public({"ok": False, "status": "authorization_reused", "findings": [{"kind": "authorization_reused"}]})
    if str(auth.get("runtime_root_identity_sha256") or "") != _runtime_identity(runtime_root):
        return _public({"ok": False, "status": "readiness_refresh_recovery_cross_runtime", "findings": [{"kind": "runtime_root_mismatch"}]})
    preview = preview_readiness_refresh_recovery(runtime_root=runtime_root)
    if not preview.get("ok"):
        return _public({"ok": False, "status": "readiness_refresh_recovery_stale", "findings": preview.get("findings") or [{"kind": "readiness_refresh_recovery_stale"}]})
    directory = _directory(runtime_root)
    refresh = read_json(directory / "refreshes" / f"{auth.get('refresh_id','')}.json")
    for field in ("refresh_binding_sha256", "previous_preview_id", "previous_record_sha256", "proposed_preview_id", "proposed_record_sha256", "proposed_readiness_binding_sha256"):
        if str(auth.get(field) or "") != str(refresh.get(field) or ""):
            return _public({"ok": False, "status": "readiness_refresh_recovery_stale", "findings": [{"kind": f"refresh_{field}_changed"}]})
    proposed = read_json(directory / "previews" / f"{refresh.get('proposed_preview_id','')}.json")
    _activate_snapshot(runtime_root, proposed)
    refresh["status"] = "refresh_complete"
    refresh["ok"] = True
    refresh["completed_at"] = utc_now()
    refresh["refresh_binding_sha256"] = _refresh_digest(refresh)
    refresh["record_sha256"] = _record_digest(refresh)
    atomic_json(directory / "refreshes" / f"{refresh['refresh_id']}.json", refresh)
    atomic_json(directory / "active_refresh.json", {"schema": REFRESH_SCHEMA, "refresh_id": refresh["refresh_id"], "refresh_binding_sha256": refresh["refresh_binding_sha256"], "record_sha256": refresh["record_sha256"], "content_free": True})
    atomic_json(used, {"schema": "eidolon-used-release-authority-token-v1", "used_at": utc_now(), "action": auth.get("action"), "content_free": True})
    return _public({**refresh, "status": "release_authority_readiness_refresh_recovered", "active_preview_id": proposed.get("preview_id"), "active_generation": proposed.get("generation")})


def preview_readiness_snapshot_replacement(preview_id: str, *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    active = _active_private(runtime_root)
    target = read_json(_directory(runtime_root) / "previews" / f"{preview_id}.json")
    findings: list[dict[str, Any]] = []
    if not active.get("ok"):
        findings.append({"kind": "coherent_active_readiness_required"})
    if not target or str(target.get("record_sha256") or "") != readiness_record_digest(target):
        findings.append({"kind": "replacement_readiness_record_invalid"})
    if str(target.get("runtime_root_identity_sha256") or "") != _runtime_identity(runtime_root):
        findings.append({"kind": "replacement_runtime_root_mismatch"})
    components = _current_components(runtime_root)
    current_summary = _summary(components, runtime_root)
    current_binding = digest_payload({key: current_summary.get(key) for key in sorted(_binding(components, runtime_root))})
    if str(target.get("readiness_binding_sha256") or "") != current_binding:
        findings.append({"kind": "replacement_readiness_stale"})
    if findings:
        return _public({"ok": False, "status": "readiness_snapshot_replacement_blocked", "findings": findings})
    token_id = f"readiness-replacement-{secrets.token_hex(8)}"
    nonce = secrets.token_hex(16)
    auth = {
        "schema": REPLACEMENT_SCHEMA,
        "token_id": token_id,
        "nonce": nonce,
        "runtime_root_identity_sha256": _runtime_identity(runtime_root),
        "active_preview_id": str(active["record"].get("preview_id") or ""),
        "active_generation": int(active["record"].get("generation") or 0),
        "active_record_sha256": str(active["record"].get("record_sha256") or ""),
        "replacement_source_preview_id": str(target.get("preview_id") or ""),
        "replacement_source_record_sha256": str(target.get("record_sha256") or ""),
        "replacement_readiness_binding_sha256": str(target.get("readiness_binding_sha256") or ""),
        "action": "replace_exact_release_authority_readiness_snapshot",
        "content_free": True,
    }
    auth["binding_sha256"] = digest_payload(auth)
    atomic_json(_directory(runtime_root) / "authorizations" / "replacement" / f"{token_id}.json", auth)
    return _public({"ok": True, "status": "readiness_snapshot_replacement_previewed", "replacement_available": True, "active_preview_id": auth["active_preview_id"], "active_generation": auth["active_generation"], "proposed_preview_id": auth["replacement_source_preview_id"], "readiness_binding_sha256": auth["replacement_readiness_binding_sha256"], "authorization_token": _authorization_token(auth), "literal_confirmation_required": REPLACEMENT_CONFIRMATION})


def replace_release_authority_readiness_snapshot(token: str, *, confirm: str, runtime_root: str | Path | None = None) -> dict[str, Any]:
    if confirm != REPLACEMENT_CONFIRMATION:
        return _public({"ok": False, "status": "literal_confirmation_required", "findings": [{"kind": "literal_confirmation_required"}]})
    auth = _load_authorization(runtime_root, "replacement", token)
    if not auth:
        return _public({"ok": False, "status": "readiness_snapshot_replacement_token_invalid", "findings": [{"kind": "readiness_snapshot_replacement_token_invalid"}]})
    used = _used_token_path(runtime_root, token)
    if used.is_file():
        return _public({"ok": False, "status": "authorization_reused", "findings": [{"kind": "authorization_reused"}]})
    if str(auth.get("runtime_root_identity_sha256") or "") != _runtime_identity(runtime_root):
        return _public({"ok": False, "status": "readiness_snapshot_replacement_cross_runtime", "findings": [{"kind": "runtime_root_mismatch"}]})
    active = _active_private(runtime_root)
    if not active.get("ok"):
        return _public({"ok": False, "status": "readiness_snapshot_replacement_stale", "findings": active.get("findings") or [{"kind": "active_readiness_changed"}]})
    for field, value in (("active_preview_id", active["record"].get("preview_id")), ("active_generation", active["record"].get("generation")), ("active_record_sha256", active["record"].get("record_sha256"))):
        if str(auth.get(field) or "") != str(value or ""):
            return _public({"ok": False, "status": "readiness_snapshot_replacement_stale", "findings": [{"kind": f"{field}_changed"}]})
    target = read_json(_directory(runtime_root) / "previews" / f"{auth.get('replacement_source_preview_id','')}.json")
    if not target or str(target.get("record_sha256") or "") != str(auth.get("replacement_source_record_sha256") or "") or str(target.get("record_sha256") or "") != readiness_record_digest(target):
        return _public({"ok": False, "status": "readiness_snapshot_replacement_stale", "findings": [{"kind": "replacement_source_changed"}]})
    preview = preview_readiness_snapshot_replacement(str(target.get("preview_id") or ""), runtime_root=runtime_root)
    if not preview.get("ok"):
        return _public({"ok": False, "status": "readiness_snapshot_replacement_stale", "findings": preview.get("findings") or [{"kind": "replacement_source_stale"}]})
    generation = int(active["record"].get("generation") or 0) + 1
    replacement = dict(target)
    replacement["preview_id"] = f"release-authority-readiness-{generation}-{secrets.token_hex(8)}"
    replacement["generation"] = generation
    replacement["created_at"] = utc_now()
    replacement["refresh_reason"] = "explicit_replacement"
    replacement["source_preview_id"] = str(target.get("preview_id") or "")
    replacement["replaced_active_preview_id"] = str(active["record"].get("preview_id") or "")
    replacement["record_sha256"] = readiness_record_digest(replacement)
    atomic_json(_directory(runtime_root) / "previews" / f"{replacement['preview_id']}.json", replacement)
    _activate_snapshot(runtime_root, replacement)
    atomic_json(used, {"schema": "eidolon-used-release-authority-token-v1", "used_at": utc_now(), "action": auth.get("action"), "content_free": True})
    return _public({"ok": True, "status": "release_authority_readiness_snapshot_replaced", "active_preview_id": replacement["preview_id"], "active_generation": generation, "readiness_binding_sha256": replacement.get("readiness_binding_sha256"), "previous_coherent_snapshot_preserved": True})


def preview_readiness_cleanup(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    temporary = _directory(runtime_root) / "temporary"
    rows: list[dict[str, Any]] = []
    if temporary.is_dir():
        for path in sorted(temporary.rglob("*")):
            if path.is_file() and not path.is_symlink():
                rows.append({"relative_path": path.relative_to(temporary).as_posix(), "sha256": sha256_file(path), "size": path.stat().st_size})
    if not rows:
        return _public({"ok": True, "status": "readiness_cleanup_not_required", "artifact_count": 0})
    token_id = f"readiness-cleanup-{secrets.token_hex(8)}"
    nonce = secrets.token_hex(16)
    auth = {
        "schema": CLEANUP_SCHEMA,
        "token_id": token_id,
        "nonce": nonce,
        "runtime_root_identity_sha256": _runtime_identity(runtime_root),
        "artifacts_sha256": digest_payload(rows),
        "artifacts": rows,
        "action": "remove_abandoned_release_authority_readiness_artifacts",
        "content_free": True,
    }
    auth["binding_sha256"] = digest_payload(auth)
    atomic_json(_directory(runtime_root) / "authorizations" / "cleanup" / f"{token_id}.json", auth)
    return _public({"ok": True, "status": "readiness_cleanup_previewed", "cleanup_available": True, "artifact_count": len(rows), "authorization_token": _authorization_token(auth), "literal_confirmation_required": CLEANUP_CONFIRMATION})


def cleanup_readiness_artifacts(token: str, *, confirm: str, runtime_root: str | Path | None = None) -> dict[str, Any]:
    if confirm != CLEANUP_CONFIRMATION:
        return _public({"ok": False, "status": "literal_confirmation_required", "findings": [{"kind": "literal_confirmation_required"}]})
    auth = _load_authorization(runtime_root, "cleanup", token)
    if not auth:
        return _public({"ok": False, "status": "readiness_cleanup_token_invalid", "findings": [{"kind": "readiness_cleanup_token_invalid"}]})
    used = _used_token_path(runtime_root, token)
    if used.is_file():
        return _public({"ok": False, "status": "authorization_reused", "findings": [{"kind": "authorization_reused"}]})
    if str(auth.get("runtime_root_identity_sha256") or "") != _runtime_identity(runtime_root):
        return _public({"ok": False, "status": "readiness_cleanup_cross_runtime", "findings": [{"kind": "runtime_root_mismatch"}]})
    temporary = (_directory(runtime_root) / "temporary").resolve()
    current: list[dict[str, Any]] = []
    for row in auth.get("artifacts") or []:
        rel = str(row.get("relative_path") or "")
        path = (temporary / rel).resolve()
        try:
            path.relative_to(temporary)
        except ValueError:
            return _public({"ok": False, "status": "readiness_cleanup_stale", "findings": [{"kind": "cleanup_artifact_outside_runtime_root"}]})
        if not path.is_file() or path.is_symlink() or sha256_file(path) != str(row.get("sha256") or ""):
            return _public({"ok": False, "status": "readiness_cleanup_stale", "findings": [{"kind": "cleanup_artifact_changed"}]})
        current.append({"relative_path": rel, "sha256": sha256_file(path), "size": path.stat().st_size})
    if digest_payload(current) != str(auth.get("artifacts_sha256") or ""):
        return _public({"ok": False, "status": "readiness_cleanup_stale", "findings": [{"kind": "cleanup_artifact_set_changed"}]})
    for row in current:
        (temporary / row["relative_path"]).unlink(missing_ok=True)
    for path in sorted(temporary.rglob("*"), reverse=True) if temporary.exists() else []:
        if path.is_dir():
            try:
                path.rmdir()
            except OSError:
                pass
    atomic_json(used, {"schema": "eidolon-used-release-authority-token-v1", "used_at": utc_now(), "action": auth.get("action"), "content_free": True})
    return _public({"ok": True, "status": "readiness_cleanup_complete", "artifact_count": len(current)})
