from __future__ import annotations

"""Read-only validation for one explicitly named handoff consumer.

The module never scans consumers, selects a newest consumer, or grants authority.
Every validation and receipt is bound to one exact acknowledged handoff and one
explicit consumer identity, schema, version, use, and authority-scope declaration.
"""

from collections import Counter
from pathlib import Path
import secrets
from typing import Any, Iterable, Mapping, Sequence

try:
    from metadata_mutation_coordination import MetadataMutationBusy, metadata_mutation_lock
    from release_candidate_identity import atomic_json, digest_payload, read_json, runtime_data_root, utc_now
    from release_authority_handoff_plan import ACK_PLAN_BINDING_FIELDS, _active_ack_private, _active_plan_private, _is_expired, _record_digest, release_authority_handoff_acknowledgment_status, release_authority_handoff_plan_status
    from release_authority_readiness import release_authority_readiness_status
    from release_certification_freshness import evidence_freshness_status
except ImportError:
    from metadata_mutation_coordination import MetadataMutationBusy, metadata_mutation_lock
    from release_candidate_identity import atomic_json, digest_payload, read_json, runtime_data_root, utc_now
    from release_authority_handoff_plan import (
        ACK_PLAN_BINDING_FIELDS,
        _active_ack_private,
        _active_plan_private,
        _is_expired,
        _record_digest,
        release_authority_handoff_acknowledgment_status,
        release_authority_handoff_plan_status,
    )
    from release_authority_readiness import release_authority_readiness_status
    from release_certification_freshness import evidence_freshness_status

RELEASE_AUTHORITY_CONSUMER_CONTRACT_VERSION = "1"
CONSUMER_DIRECTORY = "release_authority_consumers"
CONSUMER_VALIDATION_SCHEMA = "eidolon-release-authority-consumer-validation-v1"
CONSUMER_RECEIPT_SCHEMA = "eidolon-release-authority-consumer-receipt-v1"
CONSUMER_RECEIPT_OPERATION_SCHEMA = "eidolon-release-authority-consumer-receipt-operation-v1"
CONSUMER_ACK_CONFIRMATION = "ACKNOWLEDGE EXACT RELEASE AUTHORITY CONSUMER VALIDATION"
AUTHORITY_SCOPES = (
    "installation",
    "promotion",
    "general_release",
    "native_windows",
    "provider_ollama",
    "model_specific",
)


def consumer_directory(runtime_root: str | Path | None = None) -> Path:
    return runtime_data_root(runtime_root) / CONSUMER_DIRECTORY


def _counts(rows: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    found: Counter[str] = Counter()
    for row in rows or []:
        found[str(row.get("kind") or "unknown")] += max(1, int(row.get("count") or 1))
    return [{"kind": key, "count": found[key]} for key in sorted(found)]


def _consumer_key(consumer_id: str, consumer_schema: str, consumer_version: str, expected_use: str) -> str:
    return digest_payload({
        "consumer_id": str(consumer_id),
        "consumer_schema": str(consumer_schema),
        "consumer_version": str(consumer_version),
        "expected_use": str(expected_use),
    })


def _consumer_root(runtime_root: str | Path | None, consumer_key: str) -> Path:
    return consumer_directory(runtime_root) / "consumers" / consumer_key


def _public(record: Mapping[str, Any] | None) -> dict[str, Any]:
    row = dict(record or {})
    findings = _counts(row.get("findings") if isinstance(row.get("findings"), list) else [])
    return {
        "ok": bool(row.get("ok")) and not findings,
        "status": str(row.get("status") or "release_authority_consumer_unavailable"),
        "contract_version": RELEASE_AUTHORITY_CONSUMER_CONTRACT_VERSION,
        "consumer_id": str(row.get("consumer_id") or ""),
        "consumer_schema": str(row.get("consumer_schema") or ""),
        "consumer_version": str(row.get("consumer_version") or ""),
        "expected_use": str(row.get("expected_use") or ""),
        "consumer_key_sha256": str(row.get("consumer_key_sha256") or ""),
        "validation_id": str(row.get("validation_id") or ""),
        "validation_binding_sha256": str(row.get("validation_binding_sha256") or ""),
        "consumer_receipt_id": str(row.get("consumer_receipt_id") or ""),
        "consumer_receipt_sha256": str(row.get("consumer_receipt_sha256") or ""),
        "consumer_receipt_operation_id": str(row.get("consumer_receipt_operation_id") or ""),
        "consumer_receipt_operation_status": str(row.get("consumer_receipt_operation_status") or ""),
        "consumer_receipt_recovery_performed": bool(row.get("consumer_receipt_recovery_performed")),
        "acknowledgment_id": str(row.get("acknowledgment_id") or ""),
        "acknowledgment_receipt_sha256": str(row.get("acknowledgment_receipt_sha256") or ""),
        "plan_id": str(row.get("plan_id") or ""),
        "plan_binding_sha256": str(row.get("plan_binding_sha256") or ""),
        "readiness_binding_sha256": str(row.get("readiness_binding_sha256") or ""),
        "candidate_id": str(row.get("candidate_id") or ""),
        "archive_sha256": str(row.get("archive_sha256") or ""),
        "installed_receipt_sha256": str(row.get("installed_receipt_sha256") or ""),
        "target_project_id": str(row.get("target_project_id") or ""),
        "target_inventory_sha256": str(row.get("target_inventory_sha256") or ""),
        "promotion_receipt_sha256": str(row.get("promotion_receipt_sha256") or ""),
        "certification_receipt_sha256": str(row.get("certification_receipt_sha256") or ""),
        "authority_state_sha256": str(row.get("authority_state_sha256") or ""),
        "history_sha256": str(row.get("history_sha256") or ""),
        "policy_sha256": str(row.get("policy_sha256") or ""),
        "migration_preview_sha256": str(row.get("migration_preview_sha256") or ""),
        "evidence_state_sha256": str(row.get("evidence_state_sha256") or ""),
        "scope_statuses_sha256": str(row.get("scope_statuses_sha256") or ""),
        "required_scopes": list(row.get("required_scopes") or []),
        "unsupported_scopes": list(row.get("unsupported_scopes") or []),
        "available_scopes": list(row.get("available_scopes") or []),
        "authorization_token": str(row.get("authorization_token") or ""),
        "literal_confirmation_required": str(row.get("literal_confirmation_required") or ""),
        "receipt_present": bool(row.get("receipt_present")),
        "receipt_stale": bool(row.get("receipt_stale")),
        "findings": findings,
        "finding_count": sum(int(item["count"]) for item in findings),
        "consumer_discovery_performed": False,
        "newest_consumer_inferred": False,
        "duplicate_execution_allowed": False,
        "consumer_receipt_grants_authority": False,
        "installation_authorized": False,
        "promotion_authorized": False,
        "certification_authorized": False,
        "policy_migration_authorized": False,
        "provider_access_authorized": False,
        "model_access_authorized": False,
        "native_platform_certification_authorized": False,
        "installation_inferred": False,
        "promotion_inferred": False,
        "general_release_certification_inferred": False,
        "native_windows_inferred": False,
        "provider_ollama_inferred": False,
        "model_specific_inferred": False,
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


def _normalize_scopes(values: Sequence[str] | None) -> list[str]:
    return sorted({str(value or "").strip() for value in values or [] if str(value or "").strip()})


def _scope_availability(plan: Mapping[str, Any]) -> dict[str, bool]:
    rows = {str(item.get("scope") or ""): item for item in plan.get("scope_statuses") or [] if isinstance(item, Mapping)}
    return {
        "installation": bool(plan.get("installed_receipt_sha256")),
        "promotion": bool(plan.get("promotion_receipt_sha256")),
        "general_release": bool(rows.get("general_release", {}).get("certified")),
        "native_windows": bool(rows.get("native_windows", {}).get("certified")),
        "provider_ollama": bool(rows.get("provider_ollama", {}).get("certified")),
        "model_specific": bool(rows.get("model_specific", {}).get("certified")),
    }


def _current_binding(runtime_root: str | Path | None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    acknowledgment = release_authority_handoff_acknowledgment_status(runtime_root=runtime_root)
    plan = release_authority_handoff_plan_status(runtime_root=runtime_root)
    readiness = release_authority_readiness_status(runtime_root=runtime_root)
    freshness = evidence_freshness_status(runtime_root=runtime_root)
    ack_private = _active_ack_private(runtime_root)
    receipt = dict(ack_private.get("receipt") or {})
    _, private_plan = _active_plan_private(runtime_root)
    if not acknowledgment.get("ok") or not acknowledgment.get("acknowledgment_present") or acknowledgment.get("acknowledgment_expired"):
        findings.append({"kind": "current_unexpired_handoff_acknowledgment_required"})
    if not plan.get("ok"):
        findings.append({"kind": "current_handoff_plan_required"})
    if not readiness.get("ok"):
        findings.append({"kind": "current_release_authority_readiness_required"})
    if not receipt or str(receipt.get("receipt_sha256") or "") != _record_digest(receipt, "receipt_sha256"):
        findings.append({"kind": "acknowledgment_receipt_invalid"})
    if receipt and _is_expired(str(receipt.get("expires_at") or "")):
        findings.append({"kind": "acknowledgment_receipt_expired"})
    scope_rows = list(plan.get("scope_statuses") or [])
    evidence_material = {
        "status": freshness.get("status"),
        "policy_sha256": freshness.get("policy_sha256"),
        "fresh_scopes": sorted(freshness.get("fresh_scopes") or []),
        "expired_scopes": sorted(freshness.get("expired_scopes") or []),
        "stale_scopes": sorted(freshness.get("stale_scopes") or []),
    }
    binding = {
        "acknowledgment_id": str(receipt.get("acknowledgment_id") or ""),
        "acknowledgment_receipt_sha256": str(receipt.get("receipt_sha256") or ""),
        "acknowledgment_expires_at": str(receipt.get("expires_at") or ""),
        "plan_id": str(plan.get("plan_id") or ""),
        "plan_binding_sha256": str(plan.get("plan_binding_sha256") or ""),
        "plan_record_sha256": str(private_plan.get("record_sha256") or plan.get("record_sha256") or ""),
        "readiness_preview_id": str(plan.get("readiness_preview_id") or ""),
        "readiness_generation": int(plan.get("readiness_generation") or 0),
        "readiness_binding_sha256": str(plan.get("readiness_binding_sha256") or ""),
        **{field: private_plan.get(field) for field in ACK_PLAN_BINDING_FIELDS if field not in {"plan_id", "plan_binding_sha256", "record_sha256", "readiness_preview_id", "readiness_generation", "readiness_binding_sha256"}},
        "scope_statuses_sha256": digest_payload(scope_rows),
        "evidence_state_sha256": digest_payload(evidence_material),
    }
    return binding, findings


def _declaration_findings(
    required_scopes: Sequence[str] | None,
    unsupported_scopes: Sequence[str] | None,
    scope_sources: Mapping[str, str] | None,
    available: Mapping[str, bool],
) -> tuple[list[str], list[str], dict[str, str], list[dict[str, Any]]]:
    required = _normalize_scopes(required_scopes)
    unsupported = _normalize_scopes(unsupported_scopes)
    sources = {str(key): str(value) for key, value in dict(scope_sources or {}).items()}
    findings: list[dict[str, Any]] = []
    allowed = set(AUTHORITY_SCOPES)
    if set(required) & set(unsupported):
        findings.append({"kind": "consumer_scope_declarations_overlap"})
    if set(required) | set(unsupported) != allowed:
        findings.append({"kind": "consumer_scope_declarations_must_be_complete"})
    for scope in required + unsupported:
        if scope not in allowed:
            findings.append({"kind": "unsupported_consumer_authority_scope"})
    for scope in required:
        source = sources.get(scope, scope)
        if source != scope:
            findings.append({"kind": f"consumer_{scope}_authority_inferred_from_{source or 'unknown'}"})
        if not available.get(scope, False):
            findings.append({"kind": f"consumer_required_scope_{scope}_not_available"})
    for scope, source in sources.items():
        if scope not in required or source != scope:
            if scope in allowed and source != scope:
                findings.append({"kind": f"consumer_{scope}_authority_inferred_from_{source or 'unknown'}"})
    exact_sources = {scope: sources.get(scope, scope) for scope in required}
    return required, unsupported, exact_sources, findings


def preview_release_authority_consumer_validation(
    consumer_id: str,
    consumer_schema: str,
    consumer_version: str,
    expected_use: str,
    required_scopes: Sequence[str],
    unsupported_scopes: Sequence[str],
    *,
    scope_sources: Mapping[str, str] | None = None,
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    identity = [str(consumer_id or "").strip(), str(consumer_schema or "").strip(), str(consumer_version or "").strip(), str(expected_use or "").strip()]
    if not all(identity):
        return _public({"ok": False, "status": "exact_consumer_identity_schema_version_and_use_required", "findings": [{"kind": "exact_consumer_identity_schema_version_and_use_required"}]})
    binding, findings = _current_binding(runtime_root)
    plan = release_authority_handoff_plan_status(runtime_root=runtime_root)
    available_map = _scope_availability(plan)
    required, unsupported, exact_sources, declaration_findings = _declaration_findings(required_scopes, unsupported_scopes, scope_sources, available_map)
    findings.extend(declaration_findings)
    consumer_key = _consumer_key(*identity)
    material = {
        "consumer_id": identity[0],
        "consumer_schema": identity[1],
        "consumer_version": identity[2],
        "expected_use": identity[3],
        "consumer_key_sha256": consumer_key,
        "required_scopes": required,
        "unsupported_scopes": unsupported,
        "scope_sources": exact_sources,
        "available_scopes": sorted(scope for scope, available in available_map.items() if available),
        **binding,
    }
    validation_id = f"release-authority-consumer-validation-{digest_payload(material)[:24]}"
    record = {
        "schema": CONSUMER_VALIDATION_SCHEMA,
        "validation_id": validation_id,
        "created_at": utc_now(),
        "ok": not findings,
        "status": "release_authority_consumer_validation_ready" if not findings else "release_authority_consumer_validation_blocked",
        **material,
        "findings": findings,
        "content_free": True,
    }
    record["validation_binding_sha256"] = digest_payload({key: value for key, value in record.items() if key not in {"created_at", "findings", "record_sha256", "ok", "status"}})
    record["record_sha256"] = _record_digest(record, "record_sha256")
    root = _consumer_root(runtime_root, consumer_key)
    atomic_json(root / "validations" / f"{validation_id}.json", record)
    if findings:
        atomic_json(root / "last_failed_validation.json", record)
        return _public(record)
    token_id = f"consumer-validation-ack-{secrets.token_hex(8)}"
    auth = {
        "schema": CONSUMER_VALIDATION_SCHEMA,
        "token_id": token_id,
        "nonce": secrets.token_hex(16),
        "consumer_key_sha256": consumer_key,
        "validation_id": validation_id,
        "validation_binding_sha256": record["validation_binding_sha256"],
        "record_sha256": record["record_sha256"],
        "acknowledgment_receipt_sha256": binding["acknowledgment_receipt_sha256"],
        "plan_binding_sha256": binding["plan_binding_sha256"],
        "readiness_binding_sha256": binding["readiness_binding_sha256"],
        "consumer_version": identity[2],
        "action": "acknowledge_exact_release_authority_consumer_validation",
        "content_free": True,
    }
    auth["binding_sha256"] = _record_digest(auth, "binding_sha256")
    atomic_json(root / "authorizations" / f"{token_id}.json", auth)
    atomic_json(root / "active_validation.json", {
        "schema": CONSUMER_VALIDATION_SCHEMA,
        "validation_id": validation_id,
        "validation_binding_sha256": record["validation_binding_sha256"],
        "record_sha256": record["record_sha256"],
        "content_free": True,
    })
    token = f"{token_id}.{auth['binding_sha256']}.{auth['nonce']}"
    return _public({**record, "authorization_token": token, "literal_confirmation_required": CONSUMER_ACK_CONFIRMATION})


def _load_authorization(runtime_root: str | Path | None, consumer_key: str, token: str) -> dict[str, Any]:
    parts = token.split(".") if isinstance(token, str) else []
    if len(parts) != 3:
        return {}
    auth = read_json(_consumer_root(runtime_root, consumer_key) / "authorizations" / f"{parts[0]}.json")
    if not auth:
        return {}
    expected = _record_digest(auth, "binding_sha256")
    if parts != [str(auth.get("token_id") or ""), str(auth.get("binding_sha256") or ""), str(auth.get("nonce") or "")]:
        return {}
    return auth if str(auth.get("binding_sha256") or "") == expected else {}


def _operation_digest(record: Mapping[str, Any]) -> str:
    return _record_digest(record, "operation_sha256")


def _write_operation(path: Path, operation: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(operation)
    row["operation_sha256"] = _operation_digest(row)
    atomic_json(path, row)
    return row


def acknowledge_release_authority_consumer_validation(
    token: str,
    *,
    confirm: str,
    consumer_id: str,
    consumer_schema: str,
    consumer_version: str,
    expected_use: str,
    interrupt_after: str = "",
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    if confirm != CONSUMER_ACK_CONFIRMATION:
        return _public({"ok": False, "status": "literal_confirmation_required", "findings": [{"kind": "literal_confirmation_required"}]})
    identity = [str(consumer_id or "").strip(), str(consumer_schema or "").strip(), str(consumer_version or "").strip(), str(expected_use or "").strip()]
    if not all(identity):
        return _public({"ok": False, "status": "exact_consumer_identity_schema_version_and_use_required", "findings": [{"kind": "exact_consumer_identity_schema_version_and_use_required"}]})
    consumer_key = _consumer_key(*identity)
    auth = _load_authorization(runtime_root, consumer_key, token)
    if not auth:
        return _public({"ok": False, "status": "consumer_validation_authorization_invalid", "findings": [{"kind": "consumer_validation_authorization_invalid"}]})
    root = _consumer_root(runtime_root, consumer_key)
    used_path = root / "used_tokens" / f"{digest_payload({'token': token})}.json"
    operation_id = f"release-authority-consumer-receipt-operation-{digest_payload({'token': token, 'validation': auth.get('validation_binding_sha256'), 'consumer': consumer_key})[:24]}"
    operation_path = root / "operations" / f"{operation_id}.json"
    try:
        with metadata_mutation_lock(root / "active_receipt.json"):
            pointer = read_json(root / "active_validation.json")
            validation = read_json(root / "validations" / f"{auth.get('validation_id', '')}.json")
            if not validation or str(validation.get("record_sha256") or "") != _record_digest(validation, "record_sha256"):
                return _public({"ok": False, "status": "consumer_validation_stale", "findings": [{"kind": "consumer_validation_record_invalid"}]})
            for field in ("validation_id", "validation_binding_sha256", "record_sha256"):
                if str(pointer.get(field) or "") != str(validation.get(field) or "") or str(auth.get(field) or "") != str(validation.get(field) or ""):
                    return _public({"ok": False, "status": "consumer_validation_stale", "findings": [{"kind": f"consumer_validation_{field}_mismatch"}]})
            for field, expected in (
                ("consumer_key_sha256", consumer_key),
                ("consumer_version", validation.get("consumer_version")),
                ("acknowledgment_receipt_sha256", validation.get("acknowledgment_receipt_sha256")),
                ("plan_binding_sha256", validation.get("plan_binding_sha256")),
                ("readiness_binding_sha256", validation.get("readiness_binding_sha256")),
            ):
                if str(auth.get(field) or "") != str(expected or ""):
                    return _public({"ok": False, "status": "consumer_validation_stale", "findings": [{"kind": f"consumer_validation_authorization_{field}_mismatch"}]})
            binding, findings = _current_binding(runtime_root)
            for field in (
                "acknowledgment_id", "acknowledgment_receipt_sha256", "acknowledgment_expires_at", "plan_id", "plan_binding_sha256",
                "plan_record_sha256", "readiness_preview_id", "readiness_generation", "readiness_binding_sha256", "candidate_id",
                "archive_sha256", "installed_receipt_sha256", "target_project_id", "target_inventory_sha256", "promotion_receipt_sha256",
                "certification_receipt_sha256", "authority_state_sha256", "history_sha256", "policy_sha256", "migration_preview_sha256",
                "scope_statuses_sha256", "evidence_state_sha256",
            ):
                if str(validation.get(field) or "") != str(binding.get(field) or ""):
                    findings.append({"kind": f"consumer_validation_{field}_drift"})
            if findings:
                return _public({**validation, "ok": False, "status": "consumer_validation_stale", "findings": findings})

            operation = read_json(operation_path)
            recovery_performed = bool(operation)
            if operation:
                if str(operation.get("operation_sha256") or "") != _operation_digest(operation):
                    return _public({**validation, "ok": False, "status": "consumer_receipt_operation_contradictory", "findings": [{"kind": "consumer_receipt_operation_digest_mismatch"}]})
                for field, expected in (
                    ("consumer_key_sha256", consumer_key),
                    ("validation_id", validation.get("validation_id")),
                    ("validation_binding_sha256", validation.get("validation_binding_sha256")),
                    ("authorization_binding_sha256", auth.get("binding_sha256")),
                ):
                    if str(operation.get(field) or "") != str(expected or ""):
                        return _public({**validation, "ok": False, "status": "consumer_receipt_operation_contradictory", "findings": [{"kind": f"consumer_receipt_operation_{field}_mismatch"}]})
                if str(operation.get("status") or "") == "completed":
                    return _public({**validation, "ok": False, "status": "authorization_reused", "receipt_present": True, "consumer_receipt_operation_id": operation_id, "consumer_receipt_operation_status": "completed", "findings": [{"kind": "authorization_reused"}]})
                receipt = dict(operation.get("receipt") or {})
                if not receipt or str(receipt.get("consumer_receipt_sha256") or "") != _record_digest(receipt, "consumer_receipt_sha256"):
                    return _public({**validation, "ok": False, "status": "consumer_receipt_operation_contradictory", "findings": [{"kind": "consumer_receipt_operation_receipt_invalid"}]})
            else:
                if used_path.is_file():
                    return _public({"ok": False, "status": "authorization_reused", "findings": [{"kind": "authorization_reused"}]})
                active_pointer = read_json(root / "active_receipt.json")
                if active_pointer:
                    active_receipt = read_json(root / "receipts" / f"{active_pointer.get('consumer_receipt_id', '')}.json")
                    if active_receipt and str(active_receipt.get("validation_binding_sha256") or "") == str(validation.get("validation_binding_sha256") or ""):
                        return _public({**validation, "ok": False, "status": "consumer_receipt_already_created", "receipt_present": True, "findings": [{"kind": "consumer_receipt_already_created"}]})
                receipt_id = f"release-authority-consumer-receipt-{digest_payload({'token': token, 'validation': validation['validation_binding_sha256']})[:24]}"
                receipt = {
                    "schema": CONSUMER_RECEIPT_SCHEMA,
                    "consumer_receipt_id": receipt_id,
                    "consumer_receipt_operation_id": operation_id,
                    "created_at": utc_now(),
                    **{key: validation.get(key) for key in validation if key not in {"schema", "created_at", "ok", "status", "findings", "record_sha256"}},
                    "grants_authority": False,
                    "installation_authorized": False,
                    "promotion_authorized": False,
                    "certification_authorized": False,
                    "policy_migration_authorized": False,
                    "provider_access_authorized": False,
                    "model_access_authorized": False,
                    "native_platform_certification_authorized": False,
                    "content_free": True,
                }
                receipt["consumer_receipt_sha256"] = _record_digest(receipt, "consumer_receipt_sha256")
                operation = {
                    "schema": CONSUMER_RECEIPT_OPERATION_SCHEMA,
                    "consumer_receipt_operation_id": operation_id,
                    "status": "prepared",
                    "started_at": utc_now(),
                    "updated_at": utc_now(),
                    "consumer_key_sha256": consumer_key,
                    "validation_id": validation["validation_id"],
                    "validation_binding_sha256": validation["validation_binding_sha256"],
                    "authorization_binding_sha256": auth["binding_sha256"],
                    "receipt": receipt,
                    "content_free": True,
                }
                operation = _write_operation(operation_path, operation)

            receipt_id = str(receipt.get("consumer_receipt_id") or "")
            receipt_path = root / "receipts" / f"{receipt_id}.json"
            if interrupt_after == "prepared" and str(operation.get("status") or "") == "prepared":
                return _public({**validation, "ok": False, "status": "consumer_receipt_creation_interrupted", "consumer_receipt_operation_id": operation_id, "consumer_receipt_operation_status": "prepared", "findings": [{"kind": "consumer_receipt_creation_interrupted_after_prepared"}]})
            existing_receipt = read_json(receipt_path)
            if existing_receipt and existing_receipt != receipt:
                return _public({**validation, "ok": False, "status": "consumer_receipt_operation_contradictory", "findings": [{"kind": "consumer_receipt_existing_record_contradiction"}]})
            if not existing_receipt:
                atomic_json(receipt_path, receipt)
            operation.update({"status": "receipt_written", "updated_at": utc_now()})
            operation = _write_operation(operation_path, operation)
            if interrupt_after == "receipt_written":
                return _public({**receipt, "ok": False, "status": "consumer_receipt_creation_interrupted", "receipt_present": True, "consumer_receipt_operation_id": operation_id, "consumer_receipt_operation_status": "receipt_written", "findings": [{"kind": "consumer_receipt_creation_interrupted_after_receipt"}]})

            pointer_record = {
                "schema": CONSUMER_RECEIPT_SCHEMA,
                "consumer_receipt_id": receipt_id,
                "consumer_receipt_sha256": receipt["consumer_receipt_sha256"],
                "validation_id": validation["validation_id"],
                "validation_binding_sha256": validation["validation_binding_sha256"],
                "content_free": True,
            }
            existing_pointer = read_json(root / "active_receipt.json")
            if existing_pointer and existing_pointer != pointer_record:
                return _public({**receipt, "ok": False, "status": "consumer_receipt_operation_contradictory", "findings": [{"kind": "consumer_receipt_active_pointer_contradiction"}]})
            if not existing_pointer:
                atomic_json(root / "active_receipt.json", pointer_record)
            operation.update({"status": "pointer_written", "updated_at": utc_now()})
            operation = _write_operation(operation_path, operation)
            if interrupt_after == "pointer_written":
                return _public({**receipt, "ok": False, "status": "consumer_receipt_creation_interrupted", "receipt_present": True, "consumer_receipt_operation_id": operation_id, "consumer_receipt_operation_status": "pointer_written", "findings": [{"kind": "consumer_receipt_creation_interrupted_after_pointer"}]})

            used_record = {
                "schema": "eidolon-used-consumer-validation-token-v1",
                "used_at": operation.get("started_at"),
                "consumer_receipt_id": receipt_id,
                "consumer_receipt_operation_id": operation_id,
                "content_free": True,
            }
            existing_used = read_json(used_path)
            if existing_used and existing_used != used_record:
                return _public({**receipt, "ok": False, "status": "consumer_receipt_operation_contradictory", "findings": [{"kind": "consumer_receipt_used_token_contradiction"}]})
            if not existing_used:
                atomic_json(used_path, used_record)
            operation.update({"status": "completed", "completed_at": utc_now(), "updated_at": utc_now()})
            operation = _write_operation(operation_path, operation)
            return _public({**receipt, "ok": True, "status": "release_authority_consumer_receipt_created", "receipt_present": True, "consumer_receipt_operation_id": operation_id, "consumer_receipt_operation_status": "completed", "consumer_receipt_recovery_performed": recovery_performed})
    except MetadataMutationBusy:
        return _public({"ok": False, "status": "consumer_receipt_creation_busy", "findings": [{"kind": "consumer_receipt_creation_busy"}]})


def release_authority_consumer_receipt_status(
    consumer_id: str,
    consumer_schema: str,
    consumer_version: str,
    expected_use: str,
    *,
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    identity = [str(consumer_id or "").strip(), str(consumer_schema or "").strip(), str(consumer_version or "").strip(), str(expected_use or "").strip()]
    if not all(identity):
        return _public({"ok": False, "status": "exact_consumer_identity_schema_version_and_use_required", "findings": [{"kind": "exact_consumer_identity_schema_version_and_use_required"}]})
    consumer_key = _consumer_key(*identity)
    root = _consumer_root(runtime_root, consumer_key)
    pointer = read_json(root / "active_receipt.json")
    receipt_id = str(pointer.get("consumer_receipt_id") or "")
    if not receipt_id:
        return _public({
            "ok": True,
            "status": "release_authority_consumer_receipt_not_created",
            "consumer_id": identity[0], "consumer_schema": identity[1], "consumer_version": identity[2], "expected_use": identity[3],
            "consumer_key_sha256": consumer_key,
            "receipt_present": False,
        })
    receipt = read_json(root / "receipts" / f"{receipt_id}.json")
    findings: list[dict[str, Any]] = []
    if not receipt or str(receipt.get("consumer_receipt_sha256") or "") != _record_digest(receipt, "consumer_receipt_sha256"):
        findings.append({"kind": "consumer_receipt_invalid"})
    for field in ("consumer_receipt_id", "consumer_receipt_sha256", "validation_id", "validation_binding_sha256"):
        if str(pointer.get(field) or "") != str(receipt.get(field) or ""):
            findings.append({"kind": f"consumer_receipt_pointer_{field}_mismatch"})
    for field, expected in (("consumer_id", identity[0]), ("consumer_schema", identity[1]), ("consumer_version", identity[2]), ("expected_use", identity[3]), ("consumer_key_sha256", consumer_key)):
        if str(receipt.get(field) or "") != str(expected):
            findings.append({"kind": f"consumer_receipt_{field}_mismatch"})
    if receipt.get("grants_authority") is not False:
        findings.append({"kind": "consumer_receipt_authority_contradiction"})
    for field in ("installation_authorized", "promotion_authorized", "certification_authorized", "policy_migration_authorized", "provider_access_authorized", "model_access_authorized", "native_platform_certification_authorized"):
        if receipt.get(field) is not False:
            findings.append({"kind": f"consumer_receipt_{field}_contradiction"})
    binding, binding_findings = _current_binding(runtime_root)
    findings.extend(binding_findings)
    for field in (
        "acknowledgment_id", "acknowledgment_receipt_sha256", "acknowledgment_expires_at", "plan_id", "plan_binding_sha256",
        "plan_record_sha256", "readiness_preview_id", "readiness_generation", "readiness_binding_sha256", "candidate_id",
        "source_manifest_sha256", "archive_manifest_sha256", "archive_sha256", "installation_transaction_id",
        "installation_transaction_identity_sha256", "installed_receipt_sha256", "target_project_id", "target_inventory_sha256",
        "promotion_transaction_id", "promotion_transaction_identity_sha256", "promotion_receipt_sha256", "promotion_state_sha256",
        "certification_transaction_id", "certification_receipt_sha256", "certification_state_sha256", "certification_generation",
        "history_sha256", "history_generation", "authority_generation", "authority_state_sha256", "policy_id", "policy_sha256",
        "policy_generation", "migration_preview_id", "migration_preview_sha256", "scope_statuses_sha256", "evidence_state_sha256",
    ):
        if str(receipt.get(field) or "") != str(binding.get(field) or ""):
            findings.append({"kind": f"consumer_receipt_{field}_drift"})
    operation_id = str(receipt.get("consumer_receipt_operation_id") or "")
    if operation_id:
        operation = read_json(root / "operations" / f"{operation_id}.json")
        if not operation or str(operation.get("operation_sha256") or "") != _operation_digest(operation):
            findings.append({"kind": "consumer_receipt_operation_invalid"})
        elif str(operation.get("status") or "") != "completed":
            findings.append({"kind": "consumer_receipt_operation_incomplete"})
    else:
        findings.append({"kind": "consumer_receipt_operation_id_missing"})
    status = "release_authority_consumer_receipt_current" if not findings else "release_authority_consumer_receipt_stale"
    return _public({**receipt, "ok": not findings, "status": status, "receipt_present": bool(receipt), "receipt_stale": bool(findings), "findings": findings, "consumer_receipt_operation_id": operation_id, "consumer_receipt_operation_status": "completed" if not findings else "attention_required"})
