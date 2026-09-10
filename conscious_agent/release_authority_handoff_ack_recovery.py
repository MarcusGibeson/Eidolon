from __future__ import annotations

"""Exact recovery, replacement, expiry, and cleanup for handoff acknowledgments."""

from collections import Counter
import json
from pathlib import Path
import secrets
from typing import Any, Iterable, Mapping

try:
    from metadata_mutation_coordination import MetadataMutationBusy, metadata_mutation_lock
    from release_candidate_identity import atomic_json, digest_payload, read_json, sha256_file, utc_now
    from release_authority_handoff_plan import ACK_PLAN_BINDING_FIELDS, DEFAULT_ACK_RECEIPT_TTL_SECONDS, HANDOFF_ACK_OPERATION_SCHEMA, _active_ack_private, _authorization_token, _execute_acknowledgment, _is_expired, _load_authorization, _operation_digest, _record_digest, _tab_digest, handoff_plan_directory, release_authority_handoff_acknowledgment_status, release_authority_handoff_plan_status
except ImportError:
    from metadata_mutation_coordination import MetadataMutationBusy, metadata_mutation_lock
    from release_candidate_identity import atomic_json, digest_payload, read_json, sha256_file, utc_now
    from release_authority_handoff_plan import (
        ACK_PLAN_BINDING_FIELDS,
        DEFAULT_ACK_RECEIPT_TTL_SECONDS,
        HANDOFF_ACK_OPERATION_SCHEMA,
        _active_ack_private,
        _authorization_token,
        _execute_acknowledgment,
        _is_expired,
        _load_authorization,
        _operation_digest,
        _record_digest,
        _tab_digest,
        handoff_plan_directory,
        release_authority_handoff_acknowledgment_status,
        release_authority_handoff_plan_status,
    )

HANDOFF_ACK_RECOVERY_CONTRACT_VERSION = "1"
RECOVERY_AUTH_SCHEMA = "eidolon-release-authority-handoff-ack-recovery-authorization-v1"
RECOVERY_CONFIRMATION = "RESUME EXACT RELEASE AUTHORITY HANDOFF ACKNOWLEDGMENT"
REPLACEMENT_CONFIRMATION = "REPLACE EXACT RELEASE AUTHORITY HANDOFF ACKNOWLEDGMENT"
CLEANUP_CONFIRMATION = "REMOVE ABANDONED RELEASE AUTHORITY HANDOFF ACKNOWLEDGMENT ARTIFACTS"


def _counts(rows: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    found: Counter[str] = Counter()
    for row in rows or []:
        found[str(row.get("kind") or "unknown")] += max(1, int(row.get("count") or 1))
    return [{"kind": key, "count": found[key]} for key in sorted(found)]


def _public(record: Mapping[str, Any] | None) -> dict[str, Any]:
    row = dict(record or {})
    findings = _counts(row.get("findings") if isinstance(row.get("findings"), list) else [])
    return {
        "ok": bool(row.get("ok")) and not findings,
        "status": str(row.get("status") or "handoff_acknowledgment_recovery_unavailable"),
        "contract_version": HANDOFF_ACK_RECOVERY_CONTRACT_VERSION,
        "acknowledgment_id": str(row.get("acknowledgment_id") or ""),
        "acknowledgment_receipt_sha256": str(row.get("acknowledgment_receipt_sha256") or row.get("receipt_sha256") or ""),
        "acknowledgment_expires_at": str(row.get("acknowledgment_expires_at") or row.get("expires_at") or ""),
        "acknowledgment_expired": bool(row.get("acknowledgment_expired")),
        "acknowledgment_operation_id": str(row.get("acknowledgment_operation_id") or ""),
        "acknowledgment_operation_status": str(row.get("acknowledgment_operation_status") or ""),
        "plan_id": str(row.get("plan_id") or ""),
        "plan_binding_sha256": str(row.get("plan_binding_sha256") or ""),
        "readiness_generation": int(row.get("readiness_generation") or 0),
        "readiness_binding_sha256": str(row.get("readiness_binding_sha256") or ""),
        "candidate_id": str(row.get("candidate_id") or ""),
        "archive_sha256": str(row.get("archive_sha256") or ""),
        "target_project_id": str(row.get("target_project_id") or ""),
        "installed_receipt_sha256": str(row.get("installed_receipt_sha256") or ""),
        "promotion_receipt_sha256": str(row.get("promotion_receipt_sha256") or ""),
        "certification_receipt_sha256": str(row.get("certification_receipt_sha256") or ""),
        "history_sha256": str(row.get("history_sha256") or ""),
        "policy_sha256": str(row.get("policy_sha256") or ""),
        "migration_preview_sha256": str(row.get("migration_preview_sha256") or ""),
        "operator_tab_id_sha256": str(row.get("operator_tab_id_sha256") or ""),
        "operation_revision": int(row.get("operation_revision") or 0),
        "recovery_available": bool(row.get("recovery_available")),
        "replacement_available": bool(row.get("replacement_available")),
        "cleanup_available": bool(row.get("cleanup_available")),
        "cleanup_artifact_count": int(row.get("cleanup_artifact_count") or 0),
        "authorization_token": str(row.get("authorization_token") or ""),
        "literal_confirmation_required": str(row.get("literal_confirmation_required") or ""),
        "previous_coherent_handoff_preserved": bool(row.get("previous_coherent_handoff_preserved", True)),
        "previous_coherent_acknowledgment_preserved": bool(row.get("previous_coherent_acknowledgment_preserved", True)),
        "automatic_recreation_performed": False,
        "expiry_extended": False,
        "authority_applied": False,
        "duplicate_execution_allowed": False,
        "findings": findings,
        "finding_count": sum(int(item["count"]) for item in findings),
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


def _auth_dir(runtime_root: str | Path | None, category: str) -> Path:
    return handoff_plan_directory(runtime_root) / "ack_recovery_authorizations" / category


def _used_path(runtime_root: str | Path | None, token: str) -> Path:
    return handoff_plan_directory(runtime_root) / "ack_recovery_used_tokens" / f"{digest_payload({'token': token})}.json"


def _make_authorization(category: str, material: Mapping[str, Any], runtime_root: str | Path | None) -> dict[str, Any]:
    token_id = f"handoff-ack-{category}-{secrets.token_hex(8)}"
    auth = {
        "schema": RECOVERY_AUTH_SCHEMA,
        "category": category,
        "token_id": token_id,
        "nonce": secrets.token_hex(16),
        "created_at": utc_now(),
        **dict(material),
        "content_free": True,
    }
    auth["binding_sha256"] = _record_digest(auth, "binding_sha256")
    atomic_json(_auth_dir(runtime_root, category) / f"{token_id}.json", auth)
    return auth


def _load_auth(runtime_root: str | Path | None, category: str, token: str) -> dict[str, Any]:
    parts = token.split(".") if isinstance(token, str) else []
    if len(parts) != 3:
        return {}
    auth = read_json(_auth_dir(runtime_root, category) / f"{parts[0]}.json")
    if not auth:
        return {}
    if str(auth.get("binding_sha256") or "") != _record_digest(auth, "binding_sha256"):
        return {}
    if parts != [str(auth.get("token_id") or ""), str(auth.get("binding_sha256") or ""), str(auth.get("nonce") or "")]:
        return {}
    return auth


def _operation_record(runtime_root: str | Path | None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    private = _active_ack_private(runtime_root)
    pointer = dict(private.get("operation") or {})
    findings: list[dict[str, Any]] = []
    if not pointer:
        return {}, findings
    op_id = str(pointer.get("acknowledgment_operation_id") or "")
    if not op_id:
        findings.append({"kind": "handoff_acknowledgment_operation_id_missing"})
        return {}, findings
    operation = read_json(handoff_plan_directory(runtime_root) / "operations" / f"{op_id}.json")
    if not operation:
        findings.append({"kind": "handoff_acknowledgment_operation_missing_or_malformed"})
        return {}, findings
    if str(operation.get("operation_sha256") or "") != _operation_digest(operation):
        findings.append({"kind": "handoff_acknowledgment_operation_digest_mismatch"})
    for field in ("acknowledgment_operation_id", "operation_sha256", "status"):
        if str(pointer.get(field) or "") != str(operation.get(field) or ""):
            findings.append({"kind": f"handoff_acknowledgment_operation_pointer_{field}_mismatch"})
    return operation, findings


def _abandoned_artifacts(runtime_root: str | Path | None) -> list[dict[str, Any]]:
    root = handoff_plan_directory(runtime_root).resolve()
    active = _active_ack_private(runtime_root)
    active_ack_id = str(active.get("pointer", {}).get("acknowledgment_id") or "")
    active_op_id = str(active.get("operation", {}).get("acknowledgment_operation_id") or "")
    rows: list[dict[str, Any]] = []
    candidates: list[Path] = []
    ack_dir = root / "acknowledgments"
    if ack_dir.exists():
        for path in ack_dir.glob("*.json"):
            if path.stem == active_ack_id:
                continue
            try:
                value = json.loads(path.read_text(encoding="utf-8-sig"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                candidates.append(path)
                continue
            if not isinstance(value, dict) or str(value.get("receipt_sha256") or "") != _record_digest(value, "receipt_sha256"):
                candidates.append(path)
    op_dir = root / "operations"
    if op_dir.exists():
        for path in op_dir.glob("*.json"):
            if path.stem == active_op_id:
                continue
            operation = read_json(path)
            if not operation or str(operation.get("operation_sha256") or "") != _operation_digest(operation) or str(operation.get("status") or "") != "completed":
                candidates.append(path)
    for path in sorted(set(candidates), key=lambda item: item.as_posix()):
        resolved = path.resolve()
        if root not in resolved.parents or path.is_symlink() or not path.is_file():
            continue
        try:
            relative = resolved.relative_to(root).as_posix()
            rows.append({"relative_path": relative, "sha256": sha256_file(path), "size": path.stat().st_size})
        except OSError:
            continue
    return rows


def handoff_acknowledgment_recovery_status(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    plan = release_authority_handoff_plan_status(runtime_root=runtime_root)
    ack = release_authority_handoff_acknowledgment_status(runtime_root=runtime_root)
    operation, findings = _operation_record(runtime_root)
    op_status = str(operation.get("status") or "")
    receipt = dict(operation.get("receipt") or {})
    recovery_available = bool(operation and op_status not in {"", "completed"} and plan.get("ok"))
    if recovery_available:
        for field in ACK_PLAN_BINDING_FIELDS:
            if str(receipt.get(field) or "") != str(plan.get(field) or ""):
                findings.append({"kind": f"handoff_acknowledgment_recovery_{field}_drift"})
                recovery_available = False
        if _is_expired(str(receipt.get("expires_at") or "")):
            findings.append({"kind": "handoff_acknowledgment_recovery_receipt_expired"})
            recovery_available = False
    replacement_available = bool(plan.get("ok") and ack.get("acknowledgment_present") and (ack.get("acknowledgment_expired") or not ack.get("ok")) and not recovery_available)
    artifacts = _abandoned_artifacts(runtime_root)
    status = "handoff_acknowledgment_recovery_not_required"
    ok = not findings
    if recovery_available:
        status = "handoff_acknowledgment_recovery_available"
    elif replacement_available:
        status = "handoff_acknowledgment_replacement_available"
    elif findings:
        status = "handoff_acknowledgment_recovery_attention_required"
    return _public({
        **plan,
        "ok": ok,
        "status": status,
        "acknowledgment_id": ack.get("acknowledgment_id"),
        "acknowledgment_receipt_sha256": ack.get("acknowledgment_receipt_sha256"),
        "acknowledgment_expires_at": ack.get("acknowledgment_expires_at"),
        "acknowledgment_expired": ack.get("acknowledgment_expired"),
        "acknowledgment_operation_id": operation.get("acknowledgment_operation_id"),
        "acknowledgment_operation_status": op_status,
        "recovery_available": recovery_available,
        "replacement_available": replacement_available,
        "cleanup_available": bool(artifacts),
        "cleanup_artifact_count": len(artifacts),
        "findings": findings,
    })


def preview_handoff_acknowledgment_recovery(
    *, operator_tab_id: str, operation_revision: int, runtime_root: str | Path | None = None
) -> dict[str, Any]:
    status = handoff_acknowledgment_recovery_status(runtime_root=runtime_root)
    operation, findings = _operation_record(runtime_root)
    if not status.get("recovery_available") or findings:
        return _public({**status, "ok": False, "status": "handoff_acknowledgment_recovery_not_available", "findings": findings or [{"kind": "handoff_acknowledgment_recovery_not_available"}]})
    if str(operation.get("operator_tab_id_sha256") or "") != _tab_digest(operator_tab_id) or int(operation.get("operation_revision") or 0) != int(operation_revision or 0):
        return _public({**status, "ok": False, "status": "handoff_acknowledgment_recovery_owner_mismatch", "findings": [{"kind": "handoff_acknowledgment_recovery_owner_mismatch"}]})
    receipt = dict(operation.get("receipt") or {})
    auth = _make_authorization("recovery", {
        "acknowledgment_operation_id": operation["acknowledgment_operation_id"],
        "operation_sha256": operation["operation_sha256"],
        "acknowledgment_id": receipt.get("acknowledgment_id"),
        "receipt_sha256": receipt.get("receipt_sha256"),
        "expires_at": receipt.get("expires_at"),
        "operator_tab_id_sha256": operation.get("operator_tab_id_sha256"),
        "operation_revision": operation.get("operation_revision"),
        **{field: receipt.get(field) for field in ACK_PLAN_BINDING_FIELDS},
        "action": "resume_exact_release_authority_handoff_acknowledgment",
    }, runtime_root)
    return _public({**status, "ok": True, "status": "handoff_acknowledgment_recovery_previewed", "authorization_token": _authorization_token(auth), "literal_confirmation_required": RECOVERY_CONFIRMATION, "operator_tab_id_sha256": auth["operator_tab_id_sha256"], "operation_revision": auth["operation_revision"]})


def _original_authorization(runtime_root: str | Path | None, operation: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    token_id = str(operation.get("authorization_token_id") or "")
    if not token_id:
        return "", {}
    # Initial acknowledgments use the standard directory; replacements use the replacement directory.
    standard = read_json(handoff_plan_directory(runtime_root) / "authorizations" / f"{token_id}.json")
    if standard and str(standard.get("binding_sha256") or "") == _record_digest(standard, "binding_sha256"):
        return _authorization_token(standard), standard
    replacement = read_json(_auth_dir(runtime_root, "replacement") / f"{token_id}.json")
    if replacement and str(replacement.get("binding_sha256") or "") == _record_digest(replacement, "binding_sha256"):
        return _authorization_token(replacement), replacement
    return "", {}


def recover_handoff_acknowledgment(
    token: str,
    *,
    confirm: str,
    operator_tab_id: str,
    operation_revision: int,
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    if confirm != RECOVERY_CONFIRMATION:
        return _public({"ok": False, "status": "literal_confirmation_required", "findings": [{"kind": "literal_confirmation_required"}]})
    auth = _load_auth(runtime_root, "recovery", token)
    if not auth or _used_path(runtime_root, token).is_file():
        return _public({"ok": False, "status": "handoff_acknowledgment_recovery_authorization_invalid", "findings": [{"kind": "handoff_acknowledgment_recovery_authorization_invalid"}]})
    operation, findings = _operation_record(runtime_root)
    plan = release_authority_handoff_plan_status(runtime_root=runtime_root)
    if findings or not operation or not plan.get("ok"):
        return _public({**plan, "ok": False, "status": "handoff_acknowledgment_recovery_stale", "findings": findings or plan.get("findings") or [{"kind": "handoff_acknowledgment_recovery_stale"}]})
    for field, expected in (
        ("acknowledgment_operation_id", operation.get("acknowledgment_operation_id")),
        ("operation_sha256", operation.get("operation_sha256")),
        ("operator_tab_id_sha256", _tab_digest(operator_tab_id)),
        ("operation_revision", int(operation_revision or 0)),
    ):
        if str(auth.get(field) or "") != str(expected or ""):
            return _public({**plan, "ok": False, "status": "handoff_acknowledgment_recovery_stale", "findings": [{"kind": f"handoff_acknowledgment_recovery_{field}_mismatch"}]})
    receipt = dict(operation.get("receipt") or {})
    if _is_expired(str(receipt.get("expires_at") or "")):
        return _public({**plan, "ok": False, "status": "handoff_acknowledgment_recovery_expired", "findings": [{"kind": "handoff_acknowledgment_recovery_receipt_expired"}]})
    for field in ACK_PLAN_BINDING_FIELDS:
        if str(auth.get(field) or "") != str(plan.get(field) or "") or str(receipt.get(field) or "") != str(plan.get(field) or ""):
            return _public({**plan, "ok": False, "status": "handoff_acknowledgment_recovery_stale", "findings": [{"kind": f"handoff_acknowledgment_recovery_{field}_drift"}]})
    original_token, original_auth = _original_authorization(runtime_root, operation)
    if not original_token or not original_auth:
        return _public({**plan, "ok": False, "status": "handoff_acknowledgment_recovery_stale", "findings": [{"kind": "handoff_acknowledgment_original_authorization_missing"}]})
    try:
        with metadata_mutation_lock(handoff_plan_directory(runtime_root) / "active_acknowledgment.json"):
            result = _execute_acknowledgment(
                original_token,
                original_auth,
                plan,
                operator_tab_id=operator_tab_id,
                operation_revision=operation_revision,
                runtime_root=runtime_root,
                replacement_of_acknowledgment_id=str(operation.get("replacement_of_acknowledgment_id") or ""),
                allow_expired_authorization=True,
                expected_operation_id=str(operation.get("acknowledgment_operation_id") or ""),
            )
            if result.get("ok"):
                atomic_json(_used_path(runtime_root, token), {"schema": "eidolon-used-handoff-ack-recovery-token-v1", "used_at": utc_now(), "action": auth.get("action"), "content_free": True})
                result["status"] = "release_authority_handoff_acknowledgment_recovered"
                result["acknowledgment_recovery_performed"] = True
            return result
    except MetadataMutationBusy:
        return _public({**plan, "ok": False, "status": "handoff_acknowledgment_recovery_busy", "findings": [{"kind": "handoff_acknowledgment_recovery_busy"}]})


def preview_handoff_acknowledgment_replacement(
    *,
    operator_tab_id: str,
    operation_revision: int,
    acknowledgment_ttl_seconds: int = DEFAULT_ACK_RECEIPT_TTL_SECONDS,
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    status = handoff_acknowledgment_recovery_status(runtime_root=runtime_root)
    ack = release_authority_handoff_acknowledgment_status(runtime_root=runtime_root)
    plan = release_authority_handoff_plan_status(runtime_root=runtime_root)
    if not status.get("replacement_available") or not plan.get("ok") or not ack.get("acknowledgment_present"):
        return _public({**status, "ok": False, "status": "handoff_acknowledgment_replacement_not_available", "findings": [{"kind": "handoff_acknowledgment_replacement_not_available"}]})
    auth = _make_authorization("replacement", {
        "acknowledgment_id": ack.get("acknowledgment_id"),
        "acknowledgment_receipt_sha256": ack.get("acknowledgment_receipt_sha256"),
        "acknowledgment_expires_at": ack.get("acknowledgment_expires_at"),
        "operator_tab_id_sha256": _tab_digest(operator_tab_id),
        "operation_revision": int(operation_revision or 0),
        "acknowledgment_ttl_seconds": max(1, int(acknowledgment_ttl_seconds)),
        **{field: plan.get(field) for field in ACK_PLAN_BINDING_FIELDS},
        "action": "replace_exact_release_authority_handoff_acknowledgment",
    }, runtime_root)
    return _public({**status, **plan, "ok": True, "status": "handoff_acknowledgment_replacement_previewed", "authorization_token": _authorization_token(auth), "literal_confirmation_required": REPLACEMENT_CONFIRMATION, "operator_tab_id_sha256": auth["operator_tab_id_sha256"], "operation_revision": auth["operation_revision"]})


def replace_handoff_acknowledgment(
    token: str,
    *,
    confirm: str,
    operator_tab_id: str,
    operation_revision: int,
    interrupt_after: str = "",
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    if confirm != REPLACEMENT_CONFIRMATION:
        return _public({"ok": False, "status": "literal_confirmation_required", "findings": [{"kind": "literal_confirmation_required"}]})
    auth = _load_auth(runtime_root, "replacement", token)
    if not auth or _used_path(runtime_root, token).is_file():
        return _public({"ok": False, "status": "handoff_acknowledgment_replacement_authorization_invalid", "findings": [{"kind": "handoff_acknowledgment_replacement_authorization_invalid"}]})
    plan = release_authority_handoff_plan_status(runtime_root=runtime_root)
    ack = release_authority_handoff_acknowledgment_status(runtime_root=runtime_root)
    if not plan.get("ok") or not ack.get("acknowledgment_present"):
        return _public({**plan, "ok": False, "status": "handoff_acknowledgment_replacement_stale", "findings": plan.get("findings") or [{"kind": "handoff_acknowledgment_replacement_stale"}]})
    for field, expected in (
        ("acknowledgment_id", ack.get("acknowledgment_id")),
        ("acknowledgment_receipt_sha256", ack.get("acknowledgment_receipt_sha256")),
        ("acknowledgment_expires_at", ack.get("acknowledgment_expires_at")),
        ("operator_tab_id_sha256", _tab_digest(operator_tab_id)),
        ("operation_revision", int(operation_revision or 0)),
    ):
        if str(auth.get(field) or "") != str(expected or ""):
            return _public({**plan, "ok": False, "status": "handoff_acknowledgment_replacement_stale", "findings": [{"kind": f"handoff_acknowledgment_replacement_{field}_mismatch"}]})
    for field in ACK_PLAN_BINDING_FIELDS:
        if str(auth.get(field) or "") != str(plan.get(field) or ""):
            return _public({**plan, "ok": False, "status": "handoff_acknowledgment_replacement_stale", "findings": [{"kind": f"handoff_acknowledgment_replacement_{field}_drift"}]})
    try:
        with metadata_mutation_lock(handoff_plan_directory(runtime_root) / "active_acknowledgment.json"):
            result = _execute_acknowledgment(
                token,
                auth,
                plan,
                operator_tab_id=operator_tab_id,
                operation_revision=operation_revision,
                runtime_root=runtime_root,
                interrupt_after=interrupt_after,
                replacement_of_acknowledgment_id=str(ack.get("acknowledgment_id") or ""),
            )
            if result.get("ok"):
                atomic_json(_used_path(runtime_root, token), {"schema": "eidolon-used-handoff-ack-replacement-token-v1", "used_at": utc_now(), "action": auth.get("action"), "content_free": True})
                result["status"] = "release_authority_handoff_acknowledgment_replaced"
            return result
    except MetadataMutationBusy:
        return _public({**plan, "ok": False, "status": "handoff_acknowledgment_replacement_busy", "findings": [{"kind": "handoff_acknowledgment_replacement_busy"}], "previous_coherent_acknowledgment_preserved": True})


def preview_handoff_acknowledgment_cleanup(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    artifacts = _abandoned_artifacts(runtime_root)
    inventory_sha = digest_payload(artifacts)
    auth = _make_authorization("cleanup", {
        "inventory_sha256": inventory_sha,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "action": "remove_exact_abandoned_release_authority_handoff_acknowledgment_artifacts",
    }, runtime_root)
    return _public({"ok": bool(artifacts), "status": "handoff_acknowledgment_cleanup_previewed" if artifacts else "handoff_acknowledgment_cleanup_not_required", "cleanup_available": bool(artifacts), "cleanup_artifact_count": len(artifacts), "authorization_token": _authorization_token(auth) if artifacts else "", "literal_confirmation_required": CLEANUP_CONFIRMATION if artifacts else "", "findings": [] if artifacts else []})


def cleanup_handoff_acknowledgment_artifacts(
    token: str, *, confirm: str, runtime_root: str | Path | None = None
) -> dict[str, Any]:
    if confirm != CLEANUP_CONFIRMATION:
        return _public({"ok": False, "status": "literal_confirmation_required", "findings": [{"kind": "literal_confirmation_required"}]})
    auth = _load_auth(runtime_root, "cleanup", token)
    if not auth or _used_path(runtime_root, token).is_file():
        return _public({"ok": False, "status": "handoff_acknowledgment_cleanup_authorization_invalid", "findings": [{"kind": "handoff_acknowledgment_cleanup_authorization_invalid"}]})
    current = _abandoned_artifacts(runtime_root)
    if digest_payload(current) != str(auth.get("inventory_sha256") or "") or current != list(auth.get("artifacts") or []):
        return _public({"ok": False, "status": "handoff_acknowledgment_cleanup_stale", "findings": [{"kind": "handoff_acknowledgment_cleanup_inventory_changed"}]})
    root = handoff_plan_directory(runtime_root).resolve()
    removed = 0
    try:
        with metadata_mutation_lock(root / "active_acknowledgment.json"):
            for item in current:
                path = (root / str(item.get("relative_path") or "")).resolve()
                if root not in path.parents or path.is_symlink() or not path.is_file() or sha256_file(path) != str(item.get("sha256") or ""):
                    return _public({"ok": False, "status": "handoff_acknowledgment_cleanup_stale", "findings": [{"kind": "handoff_acknowledgment_cleanup_artifact_changed"}]})
            for item in current:
                path = (root / str(item.get("relative_path") or "")).resolve()
                path.unlink()
                removed += 1
            atomic_json(_used_path(runtime_root, token), {"schema": "eidolon-used-handoff-ack-cleanup-token-v1", "used_at": utc_now(), "action": auth.get("action"), "content_free": True})
    except (MetadataMutationBusy, OSError):
        return _public({"ok": False, "status": "handoff_acknowledgment_cleanup_failed", "findings": [{"kind": "handoff_acknowledgment_cleanup_failed"}]})
    return _public({"ok": True, "status": "handoff_acknowledgment_cleanup_completed", "cleanup_available": False, "cleanup_artifact_count": removed})
