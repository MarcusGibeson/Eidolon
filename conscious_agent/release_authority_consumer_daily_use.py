from __future__ import annotations

"""Exact daily-use binding for one named release-authority consumer.

Selection snapshots and use-preflight receipts are external-runtime records only.
They never discover consumers, infer a newest record, execute a downstream
consumer, or grant installation, promotion, certification, policy, provider,
model, or native-platform authority.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import secrets
from typing import Any, Mapping, Sequence

try:
    from metadata_mutation_coordination import MetadataMutationBusy, metadata_mutation_lock
    from release_candidate_identity import atomic_json, digest_payload, read_json, runtime_data_root, utc_now
    from release_authority_consumer import AUTHORITY_SCOPES, _consumer_key, _consumer_root, _normalize_scopes, _record_digest, release_authority_consumer_receipt_status
    from release_authority_consumer_lifecycle import consumer_receipt_lifecycle_status
except ImportError:
    from metadata_mutation_coordination import MetadataMutationBusy, metadata_mutation_lock
    from release_candidate_identity import atomic_json, digest_payload, read_json, runtime_data_root, utc_now
    from release_authority_consumer import (
        AUTHORITY_SCOPES,
        _consumer_key,
        _consumer_root,
        _normalize_scopes,
        _record_digest,
        release_authority_consumer_receipt_status,
    )
    from release_authority_consumer_lifecycle import consumer_receipt_lifecycle_status

CONSUMER_DAILY_USE_CONTRACT_VERSION = "1"
SELECTION_CONFIRMATION = "ACKNOWLEDGE EXACT RELEASE AUTHORITY CONSUMER SELECTION"
PREFLIGHT_CONFIRMATION = "ACKNOWLEDGE EXACT RELEASE AUTHORITY CONSUMER USE PREFLIGHT"
SELECTION_SCHEMA = "eidolon-release-authority-consumer-selection-v1"
SELECTION_OPERATION_SCHEMA = "eidolon-release-authority-consumer-selection-operation-v1"
PREFLIGHT_SCHEMA = "eidolon-release-authority-consumer-use-preflight-v1"
PREFLIGHT_OPERATION_SCHEMA = "eidolon-release-authority-consumer-use-preflight-operation-v1"

RECEIPT_BINDING_FIELDS = (
    "consumer_receipt_id", "consumer_receipt_sha256", "validation_id", "validation_binding_sha256",
    "acknowledgment_id", "acknowledgment_receipt_sha256", "acknowledgment_expires_at",
    "plan_id", "plan_binding_sha256", "plan_record_sha256", "readiness_preview_id",
    "readiness_generation", "readiness_binding_sha256", "candidate_id", "source_manifest_sha256",
    "archive_manifest_sha256", "archive_sha256", "installation_transaction_id",
    "installation_transaction_identity_sha256", "installed_receipt_sha256", "target_project_id",
    "target_inventory_sha256", "promotion_transaction_id", "promotion_transaction_identity_sha256",
    "promotion_receipt_sha256", "promotion_state_sha256", "certification_transaction_id",
    "certification_receipt_sha256", "certification_state_sha256", "certification_generation",
    "history_sha256", "history_generation", "authority_generation", "authority_state_sha256",
    "policy_id", "policy_sha256", "policy_generation", "migration_preview_id",
    "migration_preview_sha256", "scope_statuses_sha256", "evidence_state_sha256",
)


def _identity(values: Sequence[str]) -> tuple[str, str, str, str]:
    padded = [str(value or "").strip() for value in values]
    padded.extend([""] * (4 - len(padded)))
    return tuple(padded[:4])  # type: ignore[return-value]


def _counts(rows: Sequence[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    found: dict[str, int] = {}
    for row in rows or []:
        kind = str(row.get("kind") or "unknown")
        found[kind] = found.get(kind, 0) + max(1, int(row.get("count") or 1))
    return [{"kind": key, "count": found[key]} for key in sorted(found)]


def _public(row: Mapping[str, Any] | None) -> dict[str, Any]:
    data = dict(row or {})
    findings = _counts(data.get("findings") if isinstance(data.get("findings"), list) else [])
    return {
        "ok": bool(data.get("ok")) and not findings,
        "status": str(data.get("status") or "release_authority_consumer_daily_use_unavailable"),
        "contract_version": CONSUMER_DAILY_USE_CONTRACT_VERSION,
        "consumer_id": str(data.get("consumer_id") or ""),
        "consumer_schema": str(data.get("consumer_schema") or ""),
        "consumer_version": str(data.get("consumer_version") or ""),
        "expected_use": str(data.get("expected_use") or ""),
        "selection_purpose": str(data.get("selection_purpose") or ""),
        "consumer_receipt_id": str(data.get("consumer_receipt_id") or ""),
        "consumer_receipt_sha256": str(data.get("consumer_receipt_sha256") or ""),
        "selection_id": str(data.get("selection_id") or ""),
        "selection_sha256": str(data.get("selection_sha256") or ""),
        "selection_operation_id": str(data.get("selection_operation_id") or ""),
        "selection_operation_status": str(data.get("selection_operation_status") or ""),
        "selection_present": bool(data.get("selection_present")),
        "selection_expired": bool(data.get("selection_expired")),
        "selection_stale": bool(data.get("selection_stale")),
        "selection_recovery_performed": bool(data.get("selection_recovery_performed")),
        "selection_expires_at": str(data.get("selection_expires_at") or ""),
        "use_id": str(data.get("use_id") or ""),
        "use_schema": str(data.get("use_schema") or ""),
        "use_version": str(data.get("use_version") or ""),
        "declared_use": str(data.get("declared_use") or ""),
        "preflight_receipt_id": str(data.get("preflight_receipt_id") or ""),
        "preflight_receipt_sha256": str(data.get("preflight_receipt_sha256") or ""),
        "preflight_operation_id": str(data.get("preflight_operation_id") or ""),
        "preflight_operation_status": str(data.get("preflight_operation_status") or ""),
        "preflight_present": bool(data.get("preflight_present")),
        "preflight_stale": bool(data.get("preflight_stale")),
        "preflight_expired": bool(data.get("preflight_expired")),
        "preflight_recovery_performed": bool(data.get("preflight_recovery_performed")),
        "required_scopes": list(data.get("required_scopes") or []),
        "unsupported_scopes": list(data.get("unsupported_scopes") or []),
        "authorization_token": str(data.get("authorization_token") or ""),
        "literal_confirmation_required": str(data.get("literal_confirmation_required") or ""),
        "findings": findings,
        "finding_count": sum(int(item["count"]) for item in findings),
        "consumer_discovery_performed": False,
        "newest_consumer_inferred": False,
        "newest_selection_inferred": False,
        "newest_preflight_inferred": False,
        "downstream_consumer_executed": False,
        "duplicate_execution_allowed": False,
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
        "source_files_mutated": False,
        "installed_source_mutated": False,
        "installation_changed": False,
        "promotion_changed": False,
        "certification_changed": False,
        "policy_migrated": False,
    }


def _parse_time(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _expired(value: str) -> bool:
    parsed = _parse_time(value)
    return parsed is None or parsed <= datetime.now(timezone.utc)


def _future(seconds: int) -> str:
    bounded = max(60, min(int(seconds), 86400))
    return (datetime.now(timezone.utc) + timedelta(seconds=bounded)).isoformat()


def _daily_root(runtime_root: str | Path | None, identity: tuple[str, str, str, str]) -> Path:
    return _consumer_root(runtime_root, _consumer_key(*identity)) / "daily_use"


def _receipt_private(runtime_root: str | Path | None, identity: tuple[str, str, str, str]) -> dict[str, Any]:
    root = _consumer_root(runtime_root, _consumer_key(*identity))
    pointer = read_json(root / "active_receipt.json")
    receipt_id = str(pointer.get("consumer_receipt_id") or "")
    return read_json(root / "receipts" / f"{receipt_id}.json") if receipt_id else {}


def _runtime_binding(runtime_root: str | Path | None) -> str:
    return digest_payload({"runtime_data_root": str(runtime_data_root(runtime_root).resolve())})


def _current_binding(runtime_root: str | Path | None, identity: tuple[str, str, str, str]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    receipt_status = release_authority_consumer_receipt_status(*identity, runtime_root=runtime_root)
    lifecycle = consumer_receipt_lifecycle_status(*identity, runtime_root=runtime_root)
    receipt = _receipt_private(runtime_root, identity)
    findings: list[dict[str, Any]] = []
    if not receipt_status.get("ok") or not receipt_status.get("receipt_present"):
        findings.append({"kind": "current_consumer_receipt_required"})
    if not lifecycle.get("ok"):
        findings.append({"kind": "current_consumer_receipt_lifecycle_required"})
    if not receipt or str(receipt.get("consumer_receipt_sha256") or "") != _record_digest(receipt, "consumer_receipt_sha256"):
        findings.append({"kind": "consumer_receipt_private_record_invalid"})
    material = {
        "consumer_id": identity[0],
        "consumer_schema": identity[1],
        "consumer_version": identity[2],
        "expected_use": identity[3],
        "consumer_key_sha256": _consumer_key(*identity),
        "runtime_root_sha256": _runtime_binding(runtime_root),
        "required_scopes": _normalize_scopes(receipt.get("required_scopes") or receipt_status.get("required_scopes") or []),
        "unsupported_scopes": _normalize_scopes(receipt.get("unsupported_scopes") or receipt_status.get("unsupported_scopes") or []),
        "consumer_lifecycle_sha256": digest_payload({
            "status": lifecycle.get("status"),
            "consumer_receipt_sha256": lifecycle.get("consumer_receipt_sha256"),
            "operation_status": lifecycle.get("operation_status"),
            "finding_count": lifecycle.get("finding_count"),
        }),
    }
    for field in RECEIPT_BINDING_FIELDS:
        material[field] = receipt.get(field)
    material["consumer_binding_sha256"] = digest_payload(material)
    return material, findings


def _authorization(root: Path, category: str, material: Mapping[str, Any]) -> str:
    token_id = f"{category}-{secrets.token_hex(10)}"
    auth = {
        "schema": f"eidolon-release-authority-consumer-{category}-authorization-v1",
        "token_id": token_id,
        "nonce": secrets.token_hex(16),
        "category": category,
        "material": dict(material),
        "created_at": utc_now(),
        "expires_at": _future(900),
    }
    auth["binding_sha256"] = _record_digest(auth, "binding_sha256")
    atomic_json(root / "authorizations" / category / f"{token_id}.json", auth)
    return f"{token_id}.{auth['binding_sha256']}.{auth['nonce']}"


def _load_authorization(root: Path, category: str, token: str) -> dict[str, Any]:
    if not isinstance(token, str) or token.strip() != token or token.lower() in {"true", "yes", "1"}:
        return {}
    parts = token.split(".")
    if len(parts) != 3:
        return {}
    used = root / "authorizations" / "used" / f"{digest_payload({'token': token})}.json"
    if used.exists():
        return {"reused": True}
    auth = read_json(root / "authorizations" / category / f"{parts[0]}.json")
    if not auth or str(auth.get("category") or "") != category:
        return {}
    if parts != [str(auth.get("token_id") or ""), str(auth.get("binding_sha256") or ""), str(auth.get("nonce") or "")]:
        return {}
    if str(auth.get("binding_sha256") or "") != _record_digest(auth, "binding_sha256") or _expired(str(auth.get("expires_at") or "")):
        return {}
    return auth


def _consume(root: Path, category: str, token: str, record_id: str) -> None:
    atomic_json(root / "authorizations" / "used" / f"{digest_payload({'token': token})}.json", {
        "schema": "eidolon-used-consumer-daily-use-token-v1",
        "category": category,
        "record_id": record_id,
        "used_at": utc_now(),
        "content_free": True,
    })


def _operation(path: Path, row: Mapping[str, Any]) -> dict[str, Any]:
    record = dict(row)
    record["operation_sha256"] = _record_digest(record, "operation_sha256")
    atomic_json(path, record)
    return record


def _selection_private(runtime_root: str | Path | None, identity: tuple[str, str, str, str]) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    root = _daily_root(runtime_root, identity)
    pointer = read_json(root / "active_selection.json")
    selection_id = str(pointer.get("selection_id") or "")
    selection = read_json(root / "selections" / f"{selection_id}.json") if selection_id else {}
    return root, pointer, selection


def consumer_selection_status(
    consumer_id: str, consumer_schema: str, consumer_version: str, expected_use: str,
    selection_purpose: str, *, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    identity = _identity((consumer_id, consumer_schema, consumer_version, expected_use))
    purpose = str(selection_purpose or "").strip()
    if not all(identity) or not purpose:
        return _public({"status": "exact_consumer_identity_and_selection_purpose_required", "findings": [{"kind": "exact_consumer_identity_and_selection_purpose_required"}]})
    root, pointer, selection = _selection_private(runtime_root, identity)
    if not pointer:
        return _public({**dict(zip(("consumer_id", "consumer_schema", "consumer_version", "expected_use"), identity)), "selection_purpose": purpose, "status": "consumer_selection_not_created", "findings": [{"kind": "consumer_selection_not_created"}]})
    findings: list[dict[str, Any]] = []
    if not selection or str(selection.get("selection_sha256") or "") != _record_digest(selection, "selection_sha256"):
        findings.append({"kind": "consumer_selection_invalid"})
    for field in ("selection_id", "selection_sha256", "consumer_receipt_sha256"):
        if str(pointer.get(field) or "") != str(selection.get(field) or ""):
            findings.append({"kind": f"consumer_selection_pointer_{field}_mismatch"})
    expected_identity = dict(zip(("consumer_id", "consumer_schema", "consumer_version", "expected_use"), identity))
    for field, expected in {**expected_identity, "selection_purpose": purpose}.items():
        if str(selection.get(field) or "") != str(expected):
            findings.append({"kind": f"consumer_selection_{field}_mismatch"})
    current, current_findings = _current_binding(runtime_root, identity)
    findings.extend(current_findings)
    for field, expected in current.items():
        if selection.get(field) != expected:
            findings.append({"kind": f"consumer_selection_{field}_drift"})
    expired = _expired(str(selection.get("selection_expires_at") or ""))
    if expired:
        findings.append({"kind": "consumer_selection_expired"})
    operation_id = str(selection.get("selection_operation_id") or "")
    operation = read_json(root / "operations" / f"{operation_id}.json") if operation_id else {}
    if not operation or str(operation.get("operation_sha256") or "") != _record_digest(operation, "operation_sha256"):
        findings.append({"kind": "consumer_selection_operation_invalid"})
    elif str(operation.get("status") or "") != "completed":
        findings.append({"kind": "consumer_selection_operation_incomplete"})
    return _public({
        **selection,
        "ok": not findings,
        "status": "release_authority_consumer_selection_current" if not findings else "release_authority_consumer_selection_stale",
        "selection_present": bool(selection),
        "selection_expired": expired,
        "selection_stale": bool(findings),
        "selection_operation_status": str(operation.get("status") or "attention_required"),
        "findings": findings,
    })


def preview_consumer_selection(
    consumer_id: str, consumer_schema: str, consumer_version: str, expected_use: str,
    selection_purpose: str, *, operator_tab_id: str, operation_revision: int,
    selection_ttl_seconds: int = 3600, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    identity = _identity((consumer_id, consumer_schema, consumer_version, expected_use))
    purpose, tab = str(selection_purpose or "").strip(), str(operator_tab_id or "").strip()
    revision = int(operation_revision)
    if not all(identity) or not purpose or not tab or revision <= 0:
        return _public({"status": "exact_consumer_selection_declaration_required", "findings": [{"kind": "exact_consumer_selection_declaration_required"}]})
    current = consumer_selection_status(*identity, purpose, runtime_root=runtime_root)
    if current.get("ok"):
        return _public({**current, "ok": False, "status": "consumer_selection_already_current", "findings": [{"kind": "consumer_selection_already_current"}]})
    binding, findings = _current_binding(runtime_root, identity)
    if findings:
        return _public({**binding, "status": "consumer_selection_blocked", "findings": findings})
    selection_id = f"consumer-selection-{secrets.token_hex(12)}"
    material = {
        **binding,
        "selection_id": selection_id,
        "selection_purpose": purpose,
        "operator_tab_id": tab,
        "operation_revision": revision,
        "selection_expires_at": _future(selection_ttl_seconds),
    }
    root = _daily_root(runtime_root, identity)
    token = _authorization(root, "selection", material)
    atomic_json(root / "selection_previews" / f"{selection_id}.json", {**material, "schema": SELECTION_SCHEMA, "preview_only": True, "content_free": True})
    return _public({**material, "ok": True, "status": "consumer_selection_preview_ready", "authorization_token": token, "literal_confirmation_required": SELECTION_CONFIRMATION})


def create_consumer_selection(
    token: str, *, confirm: str, consumer_id: str, consumer_schema: str, consumer_version: str,
    expected_use: str, selection_purpose: str, operator_tab_id: str, operation_revision: int,
    interrupt_after: str = "", runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    identity = _identity((consumer_id, consumer_schema, consumer_version, expected_use))
    purpose, tab, revision = str(selection_purpose or "").strip(), str(operator_tab_id or "").strip(), int(operation_revision)
    root = _daily_root(runtime_root, identity)
    auth = _load_authorization(root, "selection", token)
    if auth.get("reused"):
        return _public({"status": "authorization_reused", "findings": [{"kind": "authorization_reused"}]})
    if confirm != SELECTION_CONFIRMATION or not auth:
        return _public({"status": "consumer_selection_authorization_invalid", "findings": [{"kind": "consumer_selection_authorization_invalid"}]})
    material = dict(auth.get("material") or {})
    binding, findings = _current_binding(runtime_root, identity)
    exact = {**binding, "selection_id": material.get("selection_id"), "selection_purpose": purpose, "operator_tab_id": tab, "operation_revision": revision, "selection_expires_at": material.get("selection_expires_at")}
    if findings or material != exact or _expired(str(material.get("selection_expires_at") or "")):
        return _public({"status": "consumer_selection_binding_rejected", "findings": findings or [{"kind": "consumer_selection_binding_rejected"}]})
    operation_id = f"selection-operation-{digest_payload({'authorization': auth.get('binding_sha256'), 'selection': material.get('selection_id')})[:24]}"
    operation_path = root / "operations" / f"{operation_id}.json"
    try:
        with metadata_mutation_lock(root / "active_selection.json"):
            operation = read_json(operation_path)
            recovery = bool(operation)
            if operation and str(operation.get("operation_sha256") or "") != _record_digest(operation, "operation_sha256"):
                return _public({"status": "consumer_selection_operation_contradictory", "findings": [{"kind": "consumer_selection_operation_invalid"}]})
            selection = dict(operation.get("selection") or {}) if operation else {}
            if not operation:
                selection = {
                    "schema": SELECTION_SCHEMA,
                    **material,
                    "selection_operation_id": operation_id,
                    "created_at": utc_now(),
                    "grants_authority": False,
                    "content_free": True,
                }
                selection["selection_sha256"] = _record_digest(selection, "selection_sha256")
                operation = _operation(operation_path, {
                    "schema": SELECTION_OPERATION_SCHEMA,
                    "selection_operation_id": operation_id,
                    "status": "prepared",
                    "selection": selection,
                    "authorization_binding_sha256": auth.get("binding_sha256"),
                    "started_at": utc_now(),
                    "updated_at": utc_now(),
                    "content_free": True,
                })
            if interrupt_after == "prepared" and str(operation.get("status")) == "prepared":
                return _public({**selection, "status": "consumer_selection_interrupted", "selection_operation_status": "prepared", "findings": [{"kind": "consumer_selection_interrupted_after_prepared"}]})
            selection_path = root / "selections" / f"{selection['selection_id']}.json"
            existing = read_json(selection_path)
            if existing and existing != selection:
                return _public({"status": "consumer_selection_operation_contradictory", "findings": [{"kind": "consumer_selection_record_contradiction"}]})
            if not existing:
                atomic_json(selection_path, selection)
            operation.update({"status": "selection_written", "updated_at": utc_now()})
            operation = _operation(operation_path, operation)
            if interrupt_after == "selection_written":
                return _public({**selection, "status": "consumer_selection_interrupted", "selection_present": True, "selection_operation_status": "selection_written", "findings": [{"kind": "consumer_selection_interrupted_after_selection"}]})
            pointer_path = root / "active_selection.json"
            pointer = read_json(pointer_path)
            pointer_record = {"schema": SELECTION_SCHEMA, "selection_id": selection["selection_id"], "selection_sha256": selection["selection_sha256"], "consumer_receipt_sha256": selection["consumer_receipt_sha256"], "content_free": True}
            if pointer and pointer != pointer_record:
                old_id = str(pointer.get("selection_id") or "")
                old = read_json(root / "selections" / f"{old_id}.json") if old_id else {}
                if not old or not _expired(str(old.get("selection_expires_at") or "")):
                    return _public({"status": "consumer_selection_active_pointer_contradiction", "findings": [{"kind": "consumer_selection_active_pointer_contradiction"}]})
            atomic_json(pointer_path, pointer_record)
            operation.update({"status": "pointer_written", "updated_at": utc_now()})
            operation = _operation(operation_path, operation)
            if interrupt_after == "pointer_written":
                return _public({**selection, "status": "consumer_selection_interrupted", "selection_present": True, "selection_operation_status": "pointer_written", "findings": [{"kind": "consumer_selection_interrupted_after_pointer"}]})
            _consume(root, "selection", token, str(selection["selection_id"]))
            operation.update({"status": "completed", "completed_at": utc_now(), "updated_at": utc_now()})
            _operation(operation_path, operation)
    except MetadataMutationBusy:
        return _public({"status": "consumer_selection_busy", "findings": [{"kind": "consumer_selection_busy"}]})
    return _public({**selection, "ok": True, "status": "release_authority_consumer_selection_created", "selection_present": True, "selection_operation_status": "completed", "selection_recovery_performed": recovery})


def _use_identity(use_id: str, use_schema: str, use_version: str, declared_use: str) -> tuple[str, str, str, str]:
    return _identity((use_id, use_schema, use_version, declared_use))


def _use_root(runtime_root: str | Path | None, consumer_identity: tuple[str, str, str, str], use_identity: tuple[str, str, str, str]) -> Path:
    return _daily_root(runtime_root, consumer_identity) / "uses" / digest_payload({"use_identity": list(use_identity)})


def _selection_record(runtime_root: str | Path | None, identity: tuple[str, str, str, str]) -> dict[str, Any]:
    return _selection_private(runtime_root, identity)[2]


def _scope_findings(required: Sequence[str], unsupported: Sequence[str], sources: Mapping[str, str] | None, selection: Mapping[str, Any]) -> tuple[list[str], list[str], dict[str, str], list[dict[str, Any]]]:
    req, uns = _normalize_scopes(required), _normalize_scopes(unsupported)
    src = {str(k or "").strip(): str(v or "").strip() for k, v in dict(sources or {}).items() if str(k or "").strip()}
    findings: list[dict[str, Any]] = []
    allowed = set(AUTHORITY_SCOPES)
    if set(req) & set(uns):
        findings.append({"kind": "consumer_use_scope_overlap"})
    if any(scope not in allowed for scope in req + uns):
        findings.append({"kind": "consumer_use_unknown_authority_scope"})
    if req != _normalize_scopes(selection.get("required_scopes") or []):
        findings.append({"kind": "consumer_use_required_scope_declaration_mismatch"})
    if uns != _normalize_scopes(selection.get("unsupported_scopes") or []):
        findings.append({"kind": "consumer_use_unsupported_scope_declaration_mismatch"})
    exact_sources = {scope: src.get(scope, scope) for scope in req}
    for scope in req:
        if exact_sources.get(scope) != scope:
            findings.append({"kind": f"consumer_use_{scope}_authority_inferred_from_{exact_sources.get(scope) or 'unknown'}"})
    for scope, source in src.items():
        if scope not in req or source != scope:
            findings.append({"kind": "consumer_use_scope_source_overclaim"})
    return req, uns, exact_sources, findings


def consumer_use_preflight_status(
    consumer_id: str, consumer_schema: str, consumer_version: str, expected_use: str, selection_purpose: str,
    use_id: str, use_schema: str, use_version: str, declared_use: str,
    *, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    consumer_identity = _identity((consumer_id, consumer_schema, consumer_version, expected_use))
    use_identity = _use_identity(use_id, use_schema, use_version, declared_use)
    purpose = str(selection_purpose or "").strip()
    if not all(consumer_identity) or not all(use_identity) or not purpose:
        return _public({"status": "exact_consumer_selection_and_use_identity_required", "findings": [{"kind": "exact_consumer_selection_and_use_identity_required"}]})
    selection_status = consumer_selection_status(*consumer_identity, purpose, runtime_root=runtime_root)
    use_root = _use_root(runtime_root, consumer_identity, use_identity)
    pointer = read_json(use_root / "active_preflight.json")
    receipt_id = str(pointer.get("preflight_receipt_id") or "")
    receipt = read_json(use_root / "receipts" / f"{receipt_id}.json") if receipt_id else {}
    if not pointer:
        return _public({**dict(zip(("consumer_id", "consumer_schema", "consumer_version", "expected_use"), consumer_identity)), **dict(zip(("use_id", "use_schema", "use_version", "declared_use"), use_identity)), "selection_purpose": purpose, "status": "consumer_use_preflight_not_created", "findings": [{"kind": "consumer_use_preflight_not_created"}]})
    findings: list[dict[str, Any]] = []
    if not selection_status.get("ok"):
        findings.append({"kind": "current_consumer_selection_required"})
    if not receipt or str(receipt.get("preflight_receipt_sha256") or "") != _record_digest(receipt, "preflight_receipt_sha256"):
        findings.append({"kind": "consumer_use_preflight_receipt_invalid"})
    for field in ("preflight_receipt_id", "preflight_receipt_sha256", "selection_sha256"):
        if str(pointer.get(field) or "") != str(receipt.get(field) or ""):
            findings.append({"kind": f"consumer_use_preflight_pointer_{field}_mismatch"})
    expected = {**dict(zip(("consumer_id", "consumer_schema", "consumer_version", "expected_use"), consumer_identity)), **dict(zip(("use_id", "use_schema", "use_version", "declared_use"), use_identity)), "selection_purpose": purpose}
    for field, value in expected.items():
        if str(receipt.get(field) or "") != str(value):
            findings.append({"kind": f"consumer_use_preflight_{field}_mismatch"})
    if str(receipt.get("selection_sha256") or "") != str(selection_status.get("selection_sha256") or ""):
        findings.append({"kind": "consumer_use_preflight_selection_drift"})
    if str(receipt.get("consumer_receipt_sha256") or "") != str(selection_status.get("consumer_receipt_sha256") or ""):
        findings.append({"kind": "consumer_use_preflight_consumer_receipt_drift"})
    expired = _expired(str(receipt.get("preflight_expires_at") or ""))
    if expired:
        findings.append({"kind": "consumer_use_preflight_expired"})
    operation_id = str(receipt.get("preflight_operation_id") or "")
    operation = read_json(use_root / "operations" / f"{operation_id}.json") if operation_id else {}
    if not operation or str(operation.get("operation_sha256") or "") != _record_digest(operation, "operation_sha256") or str(operation.get("status") or "") != "completed":
        findings.append({"kind": "consumer_use_preflight_operation_incomplete"})
    return _public({**receipt, "ok": not findings, "status": "release_authority_consumer_use_preflight_current" if not findings else "release_authority_consumer_use_preflight_stale", "preflight_present": bool(receipt), "preflight_stale": bool(findings), "preflight_expired": expired, "preflight_operation_status": str(operation.get("status") or "attention_required"), "findings": findings})


def preview_consumer_use_preflight(
    consumer_id: str, consumer_schema: str, consumer_version: str, expected_use: str, selection_purpose: str,
    use_id: str, use_schema: str, use_version: str, declared_use: str,
    required_scopes: Sequence[str], unsupported_scopes: Sequence[str], *, scope_sources: Mapping[str, str] | None = None,
    operator_tab_id: str, operation_revision: int, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    consumer_identity = _identity((consumer_id, consumer_schema, consumer_version, expected_use))
    use_identity = _use_identity(use_id, use_schema, use_version, declared_use)
    purpose, tab, revision = str(selection_purpose or "").strip(), str(operator_tab_id or "").strip(), int(operation_revision)
    if not all(consumer_identity) or not all(use_identity) or not purpose or not tab or revision <= 0:
        return _public({"status": "exact_consumer_use_declaration_required", "findings": [{"kind": "exact_consumer_use_declaration_required"}]})
    selection_status = consumer_selection_status(*consumer_identity, purpose, runtime_root=runtime_root)
    selection = _selection_record(runtime_root, consumer_identity)
    req, uns, sources, findings = _scope_findings(required_scopes, unsupported_scopes, scope_sources, selection)
    if not selection_status.get("ok"):
        findings.append({"kind": "current_consumer_selection_required"})
    current = consumer_use_preflight_status(*consumer_identity, purpose, *use_identity, runtime_root=runtime_root)
    if current.get("ok"):
        findings.append({"kind": "consumer_use_preflight_already_current"})
    if findings:
        return _public({**selection_status, **dict(zip(("use_id", "use_schema", "use_version", "declared_use"), use_identity)), "status": "consumer_use_preflight_blocked", "required_scopes": req, "unsupported_scopes": uns, "findings": findings})
    receipt_id = f"consumer-use-preflight-{secrets.token_hex(12)}"
    material = {
        **dict(zip(("consumer_id", "consumer_schema", "consumer_version", "expected_use"), consumer_identity)),
        **dict(zip(("use_id", "use_schema", "use_version", "declared_use"), use_identity)),
        "consumer_key_sha256": _consumer_key(*consumer_identity),
        "runtime_root_sha256": _runtime_binding(runtime_root),
        "consumer_receipt_sha256": selection["consumer_receipt_sha256"],
        "selection_id": selection["selection_id"],
        "selection_sha256": selection["selection_sha256"],
        "selection_purpose": purpose,
        "selection_expires_at": selection["selection_expires_at"],
        "preflight_receipt_id": receipt_id,
        "preflight_expires_at": selection["selection_expires_at"],
        "required_scopes": req,
        "unsupported_scopes": uns,
        "scope_sources": sources,
        "operator_tab_id": tab,
        "operation_revision": revision,
    }
    use_root = _use_root(runtime_root, consumer_identity, use_identity)
    token = _authorization(use_root, "preflight", material)
    atomic_json(use_root / "previews" / f"{receipt_id}.json", {**material, "schema": PREFLIGHT_SCHEMA, "preview_only": True, "content_free": True})
    return _public({**material, "ok": True, "status": "consumer_use_preflight_preview_ready", "authorization_token": token, "literal_confirmation_required": PREFLIGHT_CONFIRMATION})


def create_consumer_use_preflight_receipt(
    token: str, *, confirm: str, consumer_id: str, consumer_schema: str, consumer_version: str, expected_use: str,
    selection_purpose: str, use_id: str, use_schema: str, use_version: str, declared_use: str,
    required_scopes: Sequence[str], unsupported_scopes: Sequence[str], scope_sources: Mapping[str, str] | None,
    operator_tab_id: str, operation_revision: int, interrupt_after: str = "", runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    consumer_identity = _identity((consumer_id, consumer_schema, consumer_version, expected_use))
    use_identity = _use_identity(use_id, use_schema, use_version, declared_use)
    purpose, tab, revision = str(selection_purpose or "").strip(), str(operator_tab_id or "").strip(), int(operation_revision)
    use_root = _use_root(runtime_root, consumer_identity, use_identity)
    auth = _load_authorization(use_root, "preflight", token)
    if auth.get("reused"):
        return _public({"status": "authorization_reused", "findings": [{"kind": "authorization_reused"}]})
    if confirm != PREFLIGHT_CONFIRMATION or not auth:
        return _public({"status": "consumer_use_preflight_authorization_invalid", "findings": [{"kind": "consumer_use_preflight_authorization_invalid"}]})
    selection_status = consumer_selection_status(*consumer_identity, purpose, runtime_root=runtime_root)
    selection = _selection_record(runtime_root, consumer_identity)
    req, uns, sources, findings = _scope_findings(required_scopes, unsupported_scopes, scope_sources, selection)
    material = dict(auth.get("material") or {})
    expected = {
        **dict(zip(("consumer_id", "consumer_schema", "consumer_version", "expected_use"), consumer_identity)),
        **dict(zip(("use_id", "use_schema", "use_version", "declared_use"), use_identity)),
        "consumer_key_sha256": _consumer_key(*consumer_identity), "runtime_root_sha256": _runtime_binding(runtime_root),
        "consumer_receipt_sha256": selection.get("consumer_receipt_sha256"), "selection_id": selection.get("selection_id"),
        "selection_sha256": selection.get("selection_sha256"), "selection_purpose": purpose,
        "selection_expires_at": selection.get("selection_expires_at"), "preflight_receipt_id": material.get("preflight_receipt_id"),
        "preflight_expires_at": material.get("preflight_expires_at"), "required_scopes": req, "unsupported_scopes": uns,
        "scope_sources": sources, "operator_tab_id": tab, "operation_revision": revision,
    }
    if not selection_status.get("ok"):
        findings.append({"kind": "current_consumer_selection_required"})
    if findings or material != expected or _expired(str(material.get("preflight_expires_at") or "")):
        return _public({"status": "consumer_use_preflight_binding_rejected", "findings": findings or [{"kind": "consumer_use_preflight_binding_rejected"}]})
    operation_id = f"preflight-operation-{digest_payload({'authorization': auth.get('binding_sha256'), 'receipt': material.get('preflight_receipt_id')})[:24]}"
    operation_path = use_root / "operations" / f"{operation_id}.json"
    try:
        with metadata_mutation_lock(use_root / "active_preflight.json"):
            operation = read_json(operation_path)
            recovery = bool(operation)
            if operation and str(operation.get("operation_sha256") or "") != _record_digest(operation, "operation_sha256"):
                return _public({"status": "consumer_use_preflight_operation_contradictory", "findings": [{"kind": "consumer_use_preflight_operation_invalid"}]})
            receipt = dict(operation.get("receipt") or {}) if operation else {}
            if not operation:
                receipt = {"schema": PREFLIGHT_SCHEMA, **material, "preflight_operation_id": operation_id, "created_at": utc_now(), "grants_authority": False, "executes_consumer": False, "content_free": True}
                receipt["preflight_receipt_sha256"] = _record_digest(receipt, "preflight_receipt_sha256")
                operation = _operation(operation_path, {"schema": PREFLIGHT_OPERATION_SCHEMA, "preflight_operation_id": operation_id, "status": "prepared", "receipt": receipt, "authorization_binding_sha256": auth.get("binding_sha256"), "started_at": utc_now(), "updated_at": utc_now(), "content_free": True})
            if interrupt_after == "prepared" and str(operation.get("status")) == "prepared":
                return _public({**receipt, "status": "consumer_use_preflight_interrupted", "preflight_operation_status": "prepared", "findings": [{"kind": "consumer_use_preflight_interrupted_after_prepared"}]})
            receipt_path = use_root / "receipts" / f"{receipt['preflight_receipt_id']}.json"
            existing = read_json(receipt_path)
            if existing and existing != receipt:
                return _public({"status": "consumer_use_preflight_operation_contradictory", "findings": [{"kind": "consumer_use_preflight_receipt_contradiction"}]})
            if not existing:
                atomic_json(receipt_path, receipt)
            operation.update({"status": "receipt_written", "updated_at": utc_now()})
            operation = _operation(operation_path, operation)
            if interrupt_after == "receipt_written":
                return _public({**receipt, "status": "consumer_use_preflight_interrupted", "preflight_present": True, "preflight_operation_status": "receipt_written", "findings": [{"kind": "consumer_use_preflight_interrupted_after_receipt"}]})
            pointer = {"schema": PREFLIGHT_SCHEMA, "preflight_receipt_id": receipt["preflight_receipt_id"], "preflight_receipt_sha256": receipt["preflight_receipt_sha256"], "selection_sha256": receipt["selection_sha256"], "content_free": True}
            existing_pointer = read_json(use_root / "active_preflight.json")
            if existing_pointer and existing_pointer != pointer:
                return _public({"status": "consumer_use_preflight_active_pointer_contradiction", "findings": [{"kind": "consumer_use_preflight_active_pointer_contradiction"}]})
            if not existing_pointer:
                atomic_json(use_root / "active_preflight.json", pointer)
            operation.update({"status": "pointer_written", "updated_at": utc_now()})
            operation = _operation(operation_path, operation)
            if interrupt_after == "pointer_written":
                return _public({**receipt, "status": "consumer_use_preflight_interrupted", "preflight_present": True, "preflight_operation_status": "pointer_written", "findings": [{"kind": "consumer_use_preflight_interrupted_after_pointer"}]})
            _consume(use_root, "preflight", token, str(receipt["preflight_receipt_id"]))
            operation.update({"status": "completed", "completed_at": utc_now(), "updated_at": utc_now()})
            _operation(operation_path, operation)
    except MetadataMutationBusy:
        return _public({"status": "consumer_use_preflight_busy", "findings": [{"kind": "consumer_use_preflight_busy"}]})
    return _public({**receipt, "ok": True, "status": "release_authority_consumer_use_preflight_created", "preflight_present": True, "preflight_operation_status": "completed", "preflight_recovery_performed": recovery})


def release_authority_consumer_daily_use_status(
    consumer_id: str = "", consumer_schema: str = "", consumer_version: str = "", expected_use: str = "",
    selection_purpose: str = "", use_id: str = "", use_schema: str = "", use_version: str = "", declared_use: str = "",
    *, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    identity = _identity((consumer_id, consumer_schema, consumer_version, expected_use))
    selected = any(identity) or bool(str(selection_purpose or "").strip())
    if not selected:
        return _public({"ok": True, "status": "release_authority_consumer_not_selected"})
    lifecycle = consumer_receipt_lifecycle_status(*identity, runtime_root=runtime_root) if all(identity) else {"ok": False}
    selection = consumer_selection_status(*identity, selection_purpose, runtime_root=runtime_root)
    use_identity = _use_identity(use_id, use_schema, use_version, declared_use)
    use_selected = any(use_identity)
    preflight = consumer_use_preflight_status(*identity, selection_purpose, *use_identity, runtime_root=runtime_root) if all(use_identity) else _public({"ok": True, "status": "consumer_use_not_selected"})
    findings: list[dict[str, Any]] = []
    if not lifecycle.get("ok"):
        findings.append({"kind": "consumer_receipt_lifecycle_attention_required"})
    if not selection.get("ok"):
        findings.append({"kind": "consumer_selection_attention_required"})
    if use_selected and not preflight.get("ok"):
        findings.append({"kind": "consumer_use_preflight_attention_required"})
    return _public({
        **selection,
        **({k: v for k, v in preflight.items() if k.startswith("preflight_") or k in {"use_id", "use_schema", "use_version", "declared_use"}} if use_selected else {}),
        "ok": not findings,
        "status": "release_authority_consumer_daily_use_coherent" if not findings else "release_authority_consumer_daily_use_attention_required",
        "findings": findings,
    })
