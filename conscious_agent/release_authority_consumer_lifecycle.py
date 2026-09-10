from __future__ import annotations

"""Bounded lifecycle controls for exact release-authority consumer receipts.

This module never scans consumers, selects a newest record, grants authority, or
changes installation, promotion, certification, policy, provider, model, or
native-platform state.
"""

from pathlib import Path
import secrets
from typing import Any, Mapping

try:
    from metadata_mutation_coordination import MetadataMutationBusy, metadata_mutation_lock
    from release_candidate_identity import atomic_json, digest_payload, read_json, utc_now
    from release_authority_consumer import _consumer_key, _consumer_root, _record_digest, release_authority_consumer_receipt_status
except ImportError:
    from metadata_mutation_coordination import MetadataMutationBusy, metadata_mutation_lock
    from release_candidate_identity import atomic_json, digest_payload, read_json, utc_now
    from release_authority_consumer import _consumer_key, _consumer_root, _record_digest, release_authority_consumer_receipt_status

CONSUMER_LIFECYCLE_CONTRACT_VERSION = "1"
RETIREMENT_CONFIRMATION = "ACKNOWLEDGE EXACT CONSUMER RECEIPT RETIREMENT PREVIEW"
RECOVERY_CONFIRMATION = "RECOVER EXACT CONSUMER RECEIPT OPERATION"
CLEANUP_CONFIRMATION = "CLEAN EXACT ABANDONED CONSUMER RECEIPT ARTIFACTS"
SUPERSESSION_CONFIRMATION = "ACKNOWLEDGE EXACT CONSUMER HANDOFF SUPERSESSION"


def _counts(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    found: dict[str, int] = {}
    for row in rows:
        kind = str(row.get("kind") or "unknown")
        found[kind] = found.get(kind, 0) + max(1, int(row.get("count") or 1))
    return [{"kind": k, "count": found[k]} for k in sorted(found)]


def _public(row: Mapping[str, Any] | None) -> dict[str, Any]:
    data = dict(row or {})
    findings = _counts(list(data.get("findings") or []))
    return {
        "ok": bool(data.get("ok")) and not findings,
        "status": str(data.get("status") or "consumer_lifecycle_unavailable"),
        "contract_version": CONSUMER_LIFECYCLE_CONTRACT_VERSION,
        "consumer_id": str(data.get("consumer_id") or ""),
        "consumer_schema": str(data.get("consumer_schema") or ""),
        "consumer_version": str(data.get("consumer_version") or ""),
        "expected_use": str(data.get("expected_use") or ""),
        "consumer_receipt_id": str(data.get("consumer_receipt_id") or ""),
        "consumer_receipt_sha256": str(data.get("consumer_receipt_sha256") or ""),
        "recovery_available": bool(data.get("recovery_available")),
        "cleanup_available": bool(data.get("cleanup_available")),
        "retirement_preview_available": bool(data.get("retirement_preview_available")),
        "retirement_preview_id": str(data.get("retirement_preview_id") or ""),
        "supersession_preview_id": str(data.get("supersession_preview_id") or ""),
        "supersession_record_id": str(data.get("supersession_record_id") or ""),
        "predecessor_receipt_sha256": str(data.get("predecessor_receipt_sha256") or ""),
        "successor_receipt_sha256": str(data.get("successor_receipt_sha256") or ""),
        "authorization_token": str(data.get("authorization_token") or ""),
        "literal_confirmation_required": str(data.get("literal_confirmation_required") or ""),
        "operation_status": str(data.get("operation_status") or ""),
        "findings": findings,
        "finding_count": sum(int(x["count"]) for x in findings),
        "consumer_discovery_performed": False,
        "newest_receipt_inferred": False,
        "authority_granted": False,
        "installation_authorized": False,
        "promotion_authorized": False,
        "certification_authorized": False,
        "policy_migration_authorized": False,
        "provider_access_authorized": False,
        "model_access_authorized": False,
        "native_platform_certification_authorized": False,
        "paths_suppressed": True,
        "records_external": True,
        "content_free": True,
        "ordinary_conversation_affected": False,
        "provider_contacted": False,
        "native_checks_run": False,
        "models_mutated": False,
        "installation_changed": False,
        "promotion_changed": False,
        "certification_changed": False,
        "policy_migrated": False,
    }


def _identity(values: tuple[str, str, str, str]) -> tuple[str, str, str, str]:
    return tuple(str(v or "").strip() for v in values)  # type: ignore[return-value]


def _receipt(identity: tuple[str, str, str, str], runtime_root: str | Path | None) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    key = _consumer_key(*identity)
    root = _consumer_root(runtime_root, key)
    pointer = read_json(root / "active_receipt.json")
    rid = str(pointer.get("consumer_receipt_id") or "")
    receipt = read_json(root / "receipts" / f"{rid}.json") if rid else {}
    return root, pointer, receipt


def _token(root: Path, category: str, material: Mapping[str, Any]) -> str:
    token = secrets.token_urlsafe(32)
    record = {"schema": f"eidolon-consumer-{category}-authorization-v1", "category": category, "material": dict(material), "created_at": utc_now(), "token_sha256": digest_payload({"token": token})}
    atomic_json(root / "authorizations" / category / f"{token}.json", record)
    return token


def _load_token(root: Path, category: str, token: str) -> dict[str, Any]:
    if not token or token.strip() != token or token.lower() in {"true", "yes", "1"}:
        return {}
    used = root / "authorizations" / "used" / f"{digest_payload({'token': token})}.json"
    if used.exists():
        return {"reused": True}
    record = read_json(root / "authorizations" / category / f"{token}.json")
    if str(record.get("token_sha256") or "") != digest_payload({"token": token}):
        return {}
    return record


def _consume(root: Path, token: str, category: str) -> None:
    atomic_json(root / "authorizations" / "used" / f"{digest_payload({'token': token})}.json", {"category": category, "used_at": utc_now()})


def consumer_receipt_lifecycle_status(consumer_id: str, consumer_schema: str, consumer_version: str, expected_use: str, *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    identity = _identity((consumer_id, consumer_schema, consumer_version, expected_use))
    if not all(identity):
        return _public({"status": "exact_consumer_identity_required", "findings": [{"kind": "exact_consumer_identity_required"}]})
    root, pointer, receipt = _receipt(identity, runtime_root)
    status = release_authority_consumer_receipt_status(*identity, runtime_root=runtime_root)
    findings: list[dict[str, Any]] = []
    operations = root / "operations"
    incomplete = []
    if operations.exists():
        for path in operations.glob("*.json"):
            op = read_json(path)
            if str(op.get("status") or "") != "completed":
                incomplete.append(op)
    if len(incomplete) > 1:
        findings.append({"kind": "contradictory_consumer_receipt_operations", "count": len(incomplete)})
    elif incomplete:
        findings.append({"kind": "incomplete_consumer_receipt_operation"})
    if pointer and not receipt:
        findings.append({"kind": "orphaned_consumer_receipt_pointer"})
    abandoned = []
    if (root / "abandoned").exists():
        abandoned = [p for p in (root / "abandoned").glob("*.json") if p.is_file()]
    return _public({
        **status,
        "ok": bool(status.get("ok")) and not findings,
        "status": "consumer_receipt_lifecycle_current" if status.get("ok") and not findings else "consumer_receipt_lifecycle_attention_required",
        "recovery_available": len(incomplete) == 1,
        "cleanup_available": bool(abandoned),
        "retirement_preview_available": bool(status.get("ok") and status.get("receipt_present")),
        "operation_status": str(incomplete[0].get("status") or "") if len(incomplete) == 1 else "",
        "findings": findings,
    })


def preview_consumer_receipt_recovery(consumer_id: str, consumer_schema: str, consumer_version: str, expected_use: str, *, operator_tab_id: str, operation_revision: int, runtime_root: str | Path | None = None) -> dict[str, Any]:
    identity = _identity((consumer_id, consumer_schema, consumer_version, expected_use))
    status = consumer_receipt_lifecycle_status(*identity, runtime_root=runtime_root)
    if not status.get("recovery_available"):
        return _public({**status, "ok": False, "status": "consumer_receipt_recovery_not_available", "findings": [{"kind": "consumer_receipt_recovery_not_available"}]})
    root, _, receipt = _receipt(identity, runtime_root)
    material = {"identity": list(identity), "receipt_sha256": receipt.get("consumer_receipt_sha256"), "operator_tab_id": str(operator_tab_id), "operation_revision": int(operation_revision)}
    token = _token(root, "recovery", material)
    return _public({**status, "ok": True, "status": "consumer_receipt_recovery_preview_ready", "authorization_token": token, "literal_confirmation_required": RECOVERY_CONFIRMATION, "findings": []})


def recover_consumer_receipt(token: str, *, confirm: str, consumer_id: str, consumer_schema: str, consumer_version: str, expected_use: str, operator_tab_id: str, operation_revision: int, runtime_root: str | Path | None = None) -> dict[str, Any]:
    identity = _identity((consumer_id, consumer_schema, consumer_version, expected_use))
    root, _, receipt = _receipt(identity, runtime_root)
    auth = _load_token(root, "recovery", token)
    if auth.get("reused"):
        return _public({"status": "authorization_reused", "findings": [{"kind": "authorization_reused"}]})
    expected = {"identity": list(identity), "receipt_sha256": receipt.get("consumer_receipt_sha256"), "operator_tab_id": str(operator_tab_id), "operation_revision": int(operation_revision)}
    if confirm != RECOVERY_CONFIRMATION or auth.get("material") != expected:
        return _public({"status": "consumer_receipt_recovery_binding_rejected", "findings": [{"kind": "consumer_receipt_recovery_binding_rejected"}]})
    try:
        with metadata_mutation_lock(root):
            for path in (root / "operations").glob("*.json"):
                op = read_json(path)
                if str(op.get("status") or "") != "completed":
                    op["status"] = "completed"
                    op["recovered_at"] = utc_now()
                    op["operation_sha256"] = digest_payload({k: v for k, v in op.items() if k != "operation_sha256"})
                    atomic_json(path, op)
            _consume(root, token, "recovery")
    except MetadataMutationBusy:
        return _public({"status": "consumer_receipt_recovery_busy", "findings": [{"kind": "consumer_receipt_recovery_busy"}]})
    return _public({**consumer_receipt_lifecycle_status(*identity, runtime_root=runtime_root), "ok": True, "status": "consumer_receipt_recovered"})


def preview_consumer_receipt_retirement(consumer_id: str, consumer_schema: str, consumer_version: str, expected_use: str, *, operator_tab_id: str, operation_revision: int, runtime_root: str | Path | None = None) -> dict[str, Any]:
    identity = _identity((consumer_id, consumer_schema, consumer_version, expected_use))
    status = release_authority_consumer_receipt_status(*identity, runtime_root=runtime_root)
    if not status.get("ok") or not status.get("receipt_present"):
        return _public({**status, "ok": False, "status": "current_consumer_receipt_required", "findings": [{"kind": "current_consumer_receipt_required"}]})
    root, _, receipt = _receipt(identity, runtime_root)
    preview_id = "retire-" + secrets.token_hex(12)
    material = {"identity": list(identity), "receipt_sha256": receipt.get("consumer_receipt_sha256"), "operator_tab_id": str(operator_tab_id), "operation_revision": int(operation_revision), "preview_id": preview_id}
    token = _token(root, "retirement", material)
    return _public({**status, "ok": True, "status": "consumer_receipt_retirement_preview_ready", "retirement_preview_id": preview_id, "authorization_token": token, "literal_confirmation_required": RETIREMENT_CONFIRMATION})


def create_consumer_receipt_retirement_preview(token: str, *, confirm: str, consumer_id: str, consumer_schema: str, consumer_version: str, expected_use: str, operator_tab_id: str, operation_revision: int, runtime_root: str | Path | None = None) -> dict[str, Any]:
    identity = _identity((consumer_id, consumer_schema, consumer_version, expected_use))
    root, _, receipt = _receipt(identity, runtime_root)
    auth = _load_token(root, "retirement", token)
    if auth.get("reused"):
        return _public({"status": "authorization_reused", "findings": [{"kind": "authorization_reused"}]})
    material = dict(auth.get("material") or {})
    expected_base = {"identity": list(identity), "receipt_sha256": receipt.get("consumer_receipt_sha256"), "operator_tab_id": str(operator_tab_id), "operation_revision": int(operation_revision)}
    if confirm != RETIREMENT_CONFIRMATION or any(material.get(k) != v for k, v in expected_base.items()):
        return _public({"status": "retirement_preview_binding_rejected", "findings": [{"kind": "retirement_preview_binding_rejected"}]})
    preview_id = str(material.get("preview_id") or "")
    record = {"schema": "eidolon-consumer-retirement-preview-v1", "retirement_preview_id": preview_id, **expected_base, "created_at": utc_now(), "grants_authority": False, "deletes_receipt": False, "revokes_receipt": False, "supersedes_receipt": False}
    record["retirement_preview_sha256"] = digest_payload(record)
    try:
        with metadata_mutation_lock(root):
            path = root / "retirement_previews" / f"{preview_id}.json"
            if path.exists():
                return _public({"status": "retirement_preview_already_created", "findings": [{"kind": "retirement_preview_already_created"}]})
            atomic_json(path, record)
            _consume(root, token, "retirement")
    except MetadataMutationBusy:
        return _public({"status": "retirement_preview_busy", "findings": [{"kind": "retirement_preview_busy"}]})
    return _public({**record, "ok": True, "status": "consumer_receipt_retirement_preview_created"})


def preview_consumer_handoff_supersession(predecessor: tuple[str, str, str, str], successor: tuple[str, str, str, str], *, operator_tab_id: str, operation_revision: int, runtime_root: str | Path | None = None) -> dict[str, Any]:
    old_id, new_id = _identity(predecessor), _identity(successor)
    old = release_authority_consumer_receipt_status(*old_id, runtime_root=runtime_root)
    new = release_authority_consumer_receipt_status(*new_id, runtime_root=runtime_root)
    findings = []
    if old_id == new_id:
        findings.append({"kind": "self_supersession_rejected"})
    if not old.get("ok") or not old.get("receipt_present"):
        findings.append({"kind": "current_predecessor_required"})
    if not new.get("ok") or not new.get("receipt_present"):
        findings.append({"kind": "current_successor_required"})
    if old_id[:2] != new_id[:2]:
        findings.append({"kind": "cross_consumer_supersession_rejected"})
    if findings:
        return _public({"status": "consumer_handoff_supersession_rejected", "findings": findings})
    root, _, old_receipt = _receipt(old_id, runtime_root)
    _, _, new_receipt = _receipt(new_id, runtime_root)
    preview_id = "supersede-" + secrets.token_hex(12)
    material = {"predecessor": list(old_id), "successor": list(new_id), "predecessor_receipt_sha256": old_receipt.get("consumer_receipt_sha256"), "successor_receipt_sha256": new_receipt.get("consumer_receipt_sha256"), "operator_tab_id": str(operator_tab_id), "operation_revision": int(operation_revision), "preview_id": preview_id}
    token = _token(root, "supersession", material)
    return _public({"ok": True, "status": "consumer_handoff_supersession_preview_ready", "supersession_preview_id": preview_id, "predecessor_receipt_sha256": material["predecessor_receipt_sha256"], "successor_receipt_sha256": material["successor_receipt_sha256"], "authorization_token": token, "literal_confirmation_required": SUPERSESSION_CONFIRMATION})


def create_consumer_handoff_supersession(token: str, *, confirm: str, predecessor: tuple[str, str, str, str], successor: tuple[str, str, str, str], operator_tab_id: str, operation_revision: int, runtime_root: str | Path | None = None) -> dict[str, Any]:
    old_id, new_id = _identity(predecessor), _identity(successor)
    root, _, old_receipt = _receipt(old_id, runtime_root)
    _, _, new_receipt = _receipt(new_id, runtime_root)
    auth = _load_token(root, "supersession", token)
    if auth.get("reused"):
        return _public({"status": "authorization_reused", "findings": [{"kind": "authorization_reused"}]})
    material = dict(auth.get("material") or {})
    expected = {"predecessor": list(old_id), "successor": list(new_id), "predecessor_receipt_sha256": old_receipt.get("consumer_receipt_sha256"), "successor_receipt_sha256": new_receipt.get("consumer_receipt_sha256"), "operator_tab_id": str(operator_tab_id), "operation_revision": int(operation_revision)}
    if confirm != SUPERSESSION_CONFIRMATION or any(material.get(k) != v for k, v in expected.items()):
        return _public({"status": "consumer_handoff_supersession_binding_rejected", "findings": [{"kind": "consumer_handoff_supersession_binding_rejected"}]})
    record_id = "supersession-" + secrets.token_hex(12)
    record = {"schema": "eidolon-consumer-handoff-supersession-v1", "supersession_record_id": record_id, **expected, "preview_id": material.get("preview_id"), "created_at": utc_now(), "grants_authority": False}
    record["supersession_record_sha256"] = digest_payload(record)
    try:
        with metadata_mutation_lock(root):
            existing = root / "supersessions" / f"{digest_payload({'old': old_receipt.get('consumer_receipt_sha256')})}.json"
            if existing.exists():
                return _public({"status": "predecessor_already_superseded", "findings": [{"kind": "predecessor_already_superseded"}]})
            atomic_json(existing, record)
            _consume(root, token, "supersession")
    except MetadataMutationBusy:
        return _public({"status": "consumer_handoff_supersession_busy", "findings": [{"kind": "consumer_handoff_supersession_busy"}]})
    return _public({**record, "ok": True, "status": "consumer_handoff_supersession_record_created"})


def release_authority_handoff_lifecycle_status(consumer_id: str = "", consumer_schema: str = "", consumer_version: str = "", expected_use: str = "", *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    identity = _identity((consumer_id, consumer_schema, consumer_version, expected_use))
    selected = any(identity)
    lifecycle = consumer_receipt_lifecycle_status(*identity, runtime_root=runtime_root) if all(identity) else _public({"ok": not selected, "status": "consumer_not_selected" if not selected else "exact_consumer_identity_required", "findings": [] if not selected else [{"kind": "exact_consumer_identity_required"}]})
    return _public({**lifecycle, "ok": lifecycle.get("ok"), "status": "release_authority_handoff_lifecycle_coherent" if lifecycle.get("ok") else "release_authority_handoff_lifecycle_attention_required"})
