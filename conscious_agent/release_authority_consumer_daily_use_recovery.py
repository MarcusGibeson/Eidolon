from __future__ import annotations

"""Recovery, replacement, and successor revalidation for exact consumer daily-use bindings.

All records live beneath an explicitly supplied external runtime root.  The module
never discovers consumers, infers a newest record, executes a consumer, or grants
installation, promotion, certification, policy, provider, model, or native-platform
authority.
"""

from pathlib import Path
import secrets
from typing import Any, Mapping, Sequence

try:
    from metadata_mutation_coordination import MetadataMutationBusy, metadata_mutation_lock
    from release_candidate_identity import atomic_json, digest_payload, read_json, runtime_data_root, utc_now
    from release_authority_consumer import _consumer_key, _record_digest, _normalize_scopes
    from release_authority_consumer_daily_use import _authorization, _current_binding, _daily_root, _expired, _future, _identity, _load_authorization, _operation, _public as _daily_public, _runtime_binding, _selection_private, _use_identity, _use_root, consumer_selection_status, consumer_use_preflight_status, release_authority_consumer_daily_use_status
except ImportError:
    from metadata_mutation_coordination import MetadataMutationBusy, metadata_mutation_lock
    from release_candidate_identity import atomic_json, digest_payload, read_json, runtime_data_root, utc_now
    from release_authority_consumer import _consumer_key, _record_digest, _normalize_scopes
    from release_authority_consumer_daily_use import (
        _authorization, _current_binding, _daily_root, _expired, _future, _identity,
        _load_authorization, _operation, _public as _daily_public, _runtime_binding,
        _selection_private, _use_identity, _use_root, consumer_selection_status,
        consumer_use_preflight_status, release_authority_consumer_daily_use_status,
    )

RECOVERY_CONTRACT_VERSION = "1"
RECOVERY_CONFIRMATION = "RECOVER EXACT CONSUMER DAILY USE BINDING"
REPLACEMENT_CONFIRMATION = "REPLACE EXACT EXPIRED CONSUMER DAILY USE BINDING"
CLEANUP_CONFIRMATION = "REMOVE EXACT ABANDONED CONSUMER DAILY USE ARTIFACTS"
SUCCESSOR_CONFIRMATION = "ACKNOWLEDGE EXACT SUCCESSOR CONSUMER DAILY USE REVALIDATION"
RECOVERY_SCHEMA = "eidolon-release-authority-consumer-daily-use-recovery-v1"
REPLACEMENT_SCHEMA = "eidolon-release-authority-consumer-daily-use-replacement-v1"
SUCCESSOR_SCHEMA = "eidolon-release-authority-consumer-daily-use-successor-revalidation-v1"


def _counts(rows: Sequence[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for row in rows or []:
        kind = str(row.get("kind") or "unknown")
        counts[kind] = counts.get(kind, 0) + max(1, int(row.get("count") or 1))
    return [{"kind": key, "count": counts[key]} for key in sorted(counts)]


def _public(row: Mapping[str, Any] | None) -> dict[str, Any]:
    data = dict(row or {})
    findings = _counts(data.get("findings") if isinstance(data.get("findings"), list) else [])
    return {
        "ok": bool(data.get("ok")) and not findings,
        "status": str(data.get("status") or "consumer_daily_use_recovery_unavailable"),
        "contract_version": RECOVERY_CONTRACT_VERSION,
        "consumer_id": str(data.get("consumer_id") or ""),
        "consumer_schema": str(data.get("consumer_schema") or ""),
        "consumer_version": str(data.get("consumer_version") or ""),
        "expected_use": str(data.get("expected_use") or ""),
        "selection_purpose": str(data.get("selection_purpose") or ""),
        "use_id": str(data.get("use_id") or ""),
        "use_schema": str(data.get("use_schema") or ""),
        "use_version": str(data.get("use_version") or ""),
        "declared_use": str(data.get("declared_use") or ""),
        "selection_id": str(data.get("selection_id") or ""),
        "selection_sha256": str(data.get("selection_sha256") or ""),
        "preflight_receipt_id": str(data.get("preflight_receipt_id") or ""),
        "preflight_receipt_sha256": str(data.get("preflight_receipt_sha256") or ""),
        "recovery_target": str(data.get("recovery_target") or ""),
        "recovery_available": bool(data.get("recovery_available")),
        "replacement_available": bool(data.get("replacement_available")),
        "cleanup_available": bool(data.get("cleanup_available")),
        "selection_expired": bool(data.get("selection_expired")),
        "preflight_expired": bool(data.get("preflight_expired")),
        "selection_operation_status": str(data.get("selection_operation_status") or ""),
        "preflight_operation_status": str(data.get("preflight_operation_status") or ""),
        "replacement_id": str(data.get("replacement_id") or ""),
        "replacement_recovery_performed": bool(data.get("replacement_recovery_performed")),
        "successor_revalidation_id": str(data.get("successor_revalidation_id") or ""),
        "successor_revalidation_sha256": str(data.get("successor_revalidation_sha256") or ""),
        "successor_revalidation_present": bool(data.get("successor_revalidation_present")),
        "successor_revalidation_stale": bool(data.get("successor_revalidation_stale")),
        "successor_revalidation_recovery_performed": bool(data.get("successor_revalidation_recovery_performed")),
        "authorization_token": str(data.get("authorization_token") or ""),
        "literal_confirmation_required": str(data.get("literal_confirmation_required") or ""),
        "findings": findings,
        "finding_count": sum(int(item["count"]) for item in findings),
        "consumer_discovery_performed": False,
        "newest_consumer_inferred": False,
        "newest_selection_inferred": False,
        "newest_preflight_inferred": False,
        "successor_inferred": False,
        "consumer_executed": False,
        "authority_granted": False,
        "installation_authorized": False,
        "promotion_authorized": False,
        "certification_authorized": False,
        "policy_migration_authorized": False,
        "provider_access_authorized": False,
        "model_access_authorized": False,
        "native_platform_certification_authorized": False,
        "paths_suppressed": True,
        "content_free": True,
        "records_external": True,
        "source_files_mutated": False,
        "installed_source_mutated": False,
        "installation_changed": False,
        "promotion_changed": False,
        "certification_changed": False,
        "policy_migrated": False,
        "provider_contacted": False,
        "models_mutated": False,
        "native_checks_run": False,
        "ordinary_conversation_affected": False,
    }


def _identities(consumer: Sequence[str], use: Sequence[str]) -> tuple[tuple[str, str, str, str], tuple[str, str, str, str]]:
    return _identity(tuple(consumer)), _use_identity(*tuple(use))


def _operation_rows(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    incomplete: list[dict[str, Any]] = []
    contradictory: list[dict[str, Any]] = []
    operations = root / "operations"
    if not operations.exists():
        return incomplete, contradictory
    for path in sorted(operations.glob("*.json")):
        row = read_json(path)
        if not row or str(row.get("operation_sha256") or "") != _record_digest(row, "operation_sha256"):
            contradictory.append({"kind": "malformed_daily_use_operation"})
            continue
        if str(row.get("status") or "") != "completed":
            incomplete.append(row)
    return incomplete, contradictory


def _active_preflight(runtime_root: str | Path | None, consumer: tuple[str, str, str, str], use: tuple[str, str, str, str]) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    root = _use_root(runtime_root, consumer, use)
    pointer = read_json(root / "active_preflight.json")
    receipt_id = str(pointer.get("preflight_receipt_id") or "")
    receipt = read_json(root / "receipts" / f"{receipt_id}.json") if receipt_id else {}
    return root, pointer, receipt


def _exact_abandoned(root: Path, runtime_root: str | Path | None) -> list[dict[str, Any]]:
    expected_runtime = _runtime_binding(runtime_root)
    rows: list[dict[str, Any]] = []
    abandoned = root / "abandoned"
    if not abandoned.exists():
        return rows
    for path in sorted(abandoned.glob("*.json")):
        record = read_json(path)
        if (
            record.get("abandoned") is True
            and str(record.get("runtime_root_sha256") or "") == expected_runtime
            and str(record.get("record_sha256") or "") == _record_digest(record, "record_sha256")
        ):
            rows.append({"name": path.name, "record_sha256": record["record_sha256"]})
    return rows


def consumer_daily_use_recovery_status(
    consumer_id: str, consumer_schema: str, consumer_version: str, expected_use: str,
    selection_purpose: str, use_id: str, use_schema: str, use_version: str, declared_use: str,
    *, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    consumer, use = _identities((consumer_id, consumer_schema, consumer_version, expected_use), (use_id, use_schema, use_version, declared_use))
    purpose = str(selection_purpose or "").strip()
    if not all(consumer) or not all(use) or not purpose:
        return _public({"status": "exact_consumer_selection_and_use_required", "findings": [{"kind": "exact_consumer_selection_and_use_required"}]})
    daily_root, selection_pointer, selection = _selection_private(runtime_root, consumer)
    use_root, preflight_pointer, preflight = _active_preflight(runtime_root, consumer, use)
    selection_ops, selection_bad = _operation_rows(daily_root)
    preflight_ops, preflight_bad = _operation_rows(use_root)
    findings: list[dict[str, Any]] = [*selection_bad, *preflight_bad]
    if len(selection_ops) > 1:
        findings.append({"kind": "contradictory_incomplete_selection_operations", "count": len(selection_ops)})
    if len(preflight_ops) > 1:
        findings.append({"kind": "contradictory_incomplete_preflight_operations", "count": len(preflight_ops)})
    if selection_pointer and not selection:
        findings.append({"kind": "orphaned_selection_pointer"})
    if preflight_pointer and not preflight:
        findings.append({"kind": "orphaned_preflight_pointer"})
    selection_expired = bool(selection) and _expired(str(selection.get("selection_expires_at") or ""))
    preflight_expired = bool(preflight) and _expired(str(preflight.get("preflight_expires_at") or ""))
    abandoned = _exact_abandoned(daily_root, runtime_root) + _exact_abandoned(use_root, runtime_root)
    recovery_target = "selection" if len(selection_ops) == 1 and not preflight_ops else "preflight" if len(preflight_ops) == 1 and not selection_ops else ""
    return _public({
        **dict(zip(("consumer_id", "consumer_schema", "consumer_version", "expected_use"), consumer)),
        **dict(zip(("use_id", "use_schema", "use_version", "declared_use"), use)),
        "selection_purpose": purpose,
        "selection_id": selection.get("selection_id"), "selection_sha256": selection.get("selection_sha256"),
        "preflight_receipt_id": preflight.get("preflight_receipt_id"), "preflight_receipt_sha256": preflight.get("preflight_receipt_sha256"),
        "selection_operation_status": selection_ops[0].get("status") if len(selection_ops) == 1 else "",
        "preflight_operation_status": preflight_ops[0].get("status") if len(preflight_ops) == 1 else "",
        "selection_expired": selection_expired, "preflight_expired": preflight_expired,
        "recovery_target": recovery_target,
        "recovery_available": bool(recovery_target and not findings),
        "replacement_available": bool((selection_expired or preflight_expired) and not findings),
        "cleanup_available": bool(abandoned),
        "ok": not findings and not recovery_target and not selection_expired and not preflight_expired,
        "status": "consumer_daily_use_binding_current" if not findings and not recovery_target and not selection_expired and not preflight_expired else "consumer_daily_use_binding_attention_required",
        "findings": findings + ([{"kind": f"incomplete_{recovery_target}_operation"}] if recovery_target else []) + ([{"kind": "consumer_selection_expired"}] if selection_expired else []) + ([{"kind": "consumer_use_preflight_expired"}] if preflight_expired else []),
    })


def _find_incomplete(root: Path) -> dict[str, Any]:
    rows, bad = _operation_rows(root)
    return rows[0] if len(rows) == 1 and not bad else {}


def preview_consumer_daily_use_recovery(
    consumer_id: str, consumer_schema: str, consumer_version: str, expected_use: str,
    selection_purpose: str, use_id: str, use_schema: str, use_version: str, declared_use: str,
    recovery_target: str, *, operator_tab_id: str, operation_revision: int,
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    consumer, use = _identities((consumer_id, consumer_schema, consumer_version, expected_use), (use_id, use_schema, use_version, declared_use))
    purpose, target, tab, revision = str(selection_purpose or "").strip(), str(recovery_target or "").strip(), str(operator_tab_id or "").strip(), int(operation_revision)
    status = consumer_daily_use_recovery_status(*consumer, purpose, *use, runtime_root=runtime_root)
    if target not in {"selection", "preflight"} or target != status.get("recovery_target") or not status.get("recovery_available") or not tab or revision <= 0:
        return _public({**status, "ok": False, "status": "consumer_daily_use_recovery_not_available", "findings": [{"kind": "consumer_daily_use_recovery_not_available"}]})
    root = _daily_root(runtime_root, consumer) if target == "selection" else _use_root(runtime_root, consumer, use)
    operation = _find_incomplete(root)
    material = {
        "consumer_identity": list(consumer), "use_identity": list(use), "selection_purpose": purpose,
        "recovery_target": target, "operation_id": str(operation.get("selection_operation_id") or operation.get("preflight_operation_id") or ""),
        "operation_sha256": operation.get("operation_sha256"), "original_authorization_binding_sha256": operation.get("authorization_binding_sha256"),
        "runtime_root_sha256": _runtime_binding(runtime_root), "operator_tab_id": tab, "operation_revision": revision,
    }
    token = _authorization(root, "daily-use-recovery", material)
    return _public({**status, **material, "ok": True, "status": "consumer_daily_use_recovery_preview_ready", "authorization_token": token, "literal_confirmation_required": RECOVERY_CONFIRMATION, "findings": []})


def _burn_original(root: Path, category: str, binding_sha256: str, record_id: str) -> None:
    auth_dir = root / "authorizations" / category
    if not auth_dir.exists():
        return
    for path in auth_dir.glob("*.json"):
        auth = read_json(path)
        if str(auth.get("binding_sha256") or "") != str(binding_sha256 or ""):
            continue
        token = f"{auth.get('token_id')}.{auth.get('binding_sha256')}.{auth.get('nonce')}"
        used = root / "authorizations" / "used" / f"{digest_payload({'token': token})}.json"
        if not used.exists():
            atomic_json(used, {"schema": "eidolon-used-consumer-daily-use-token-v1", "category": category, "record_id": record_id, "used_at": utc_now(), "content_free": True})
        return


def recover_consumer_daily_use_binding(
    token: str, *, confirm: str, consumer_id: str, consumer_schema: str, consumer_version: str, expected_use: str,
    selection_purpose: str, use_id: str, use_schema: str, use_version: str, declared_use: str,
    recovery_target: str, operator_tab_id: str, operation_revision: int,
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    consumer, use = _identities((consumer_id, consumer_schema, consumer_version, expected_use), (use_id, use_schema, use_version, declared_use))
    purpose, target, tab, revision = str(selection_purpose or "").strip(), str(recovery_target or "").strip(), str(operator_tab_id or "").strip(), int(operation_revision)
    root = _daily_root(runtime_root, consumer) if target == "selection" else _use_root(runtime_root, consumer, use)
    auth = _load_authorization(root, "daily-use-recovery", token)
    if auth.get("reused"):
        return _public({"status": "authorization_reused", "findings": [{"kind": "authorization_reused"}]})
    operation = _find_incomplete(root)
    material = {
        "consumer_identity": list(consumer), "use_identity": list(use), "selection_purpose": purpose,
        "recovery_target": target, "operation_id": str(operation.get("selection_operation_id") or operation.get("preflight_operation_id") or ""),
        "operation_sha256": operation.get("operation_sha256"), "original_authorization_binding_sha256": operation.get("authorization_binding_sha256"),
        "runtime_root_sha256": _runtime_binding(runtime_root), "operator_tab_id": tab, "operation_revision": revision,
    }
    if confirm != RECOVERY_CONFIRMATION or not auth or dict(auth.get("material") or {}) != material or target not in {"selection", "preflight"}:
        return _public({"status": "consumer_daily_use_recovery_binding_rejected", "findings": [{"kind": "consumer_daily_use_recovery_binding_rejected"}]})
    try:
        pointer_path = root / ("active_selection.json" if target == "selection" else "active_preflight.json")
        with metadata_mutation_lock(pointer_path):
            if target == "selection":
                record = dict(operation.get("selection") or {})
                record_id, digest_field, record_dir = str(record.get("selection_id") or ""), "selection_sha256", "selections"
                pointer = {"schema": record.get("schema"), "selection_id": record_id, "selection_sha256": record.get(digest_field), "consumer_receipt_sha256": record.get("consumer_receipt_sha256"), "content_free": True}
                auth_category = "selection"
            else:
                record = dict(operation.get("receipt") or {})
                record_id, digest_field, record_dir = str(record.get("preflight_receipt_id") or ""), "preflight_receipt_sha256", "receipts"
                pointer = {"schema": record.get("schema"), "preflight_receipt_id": record_id, "preflight_receipt_sha256": record.get(digest_field), "selection_sha256": record.get("selection_sha256"), "content_free": True}
                auth_category = "preflight"
            if not record_id or str(record.get(digest_field) or "") != _record_digest(record, digest_field):
                return _public({"status": "consumer_daily_use_recovery_record_invalid", "findings": [{"kind": "consumer_daily_use_recovery_record_invalid"}]})
            record_path = root / record_dir / f"{record_id}.json"
            existing_record = read_json(record_path)
            if existing_record and existing_record != record:
                return _public({"status": "consumer_daily_use_recovery_record_contradiction", "findings": [{"kind": "consumer_daily_use_recovery_record_contradiction"}]})
            if not existing_record:
                atomic_json(record_path, record)
            existing_pointer = read_json(pointer_path)
            if existing_pointer and existing_pointer != pointer:
                return _public({"status": "consumer_daily_use_recovery_pointer_contradiction", "findings": [{"kind": "consumer_daily_use_recovery_pointer_contradiction"}]})
            if not existing_pointer:
                atomic_json(pointer_path, pointer)
            _burn_original(root, auth_category, str(operation.get("authorization_binding_sha256") or ""), record_id)
            operation.update({"status": "completed", "recovered_at": utc_now(), "updated_at": utc_now(), "recovery_operation_revision": revision})
            operation = _operation(root / "operations" / f"{material['operation_id']}.json", operation)
            used = root / "authorizations" / "used" / f"{digest_payload({'token': token})}.json"
            atomic_json(used, {"schema": "eidolon-used-consumer-daily-use-recovery-token-v1", "category": "daily-use-recovery", "record_id": record_id, "used_at": utc_now(), "content_free": True})
    except MetadataMutationBusy:
        return _public({"status": "consumer_daily_use_recovery_busy", "findings": [{"kind": "consumer_daily_use_recovery_busy"}]})
    return _public({**material, **record, "ok": True, "status": "consumer_daily_use_binding_recovered", "recovery_available": False})


def preview_expired_daily_use_replacement(
    consumer_id: str, consumer_schema: str, consumer_version: str, expected_use: str,
    selection_purpose: str, use_id: str, use_schema: str, use_version: str, declared_use: str,
    *, operator_tab_id: str, operation_revision: int, replacement_ttl_seconds: int = 3600,
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    consumer, use = _identities((consumer_id, consumer_schema, consumer_version, expected_use), (use_id, use_schema, use_version, declared_use))
    purpose, tab, revision = str(selection_purpose or "").strip(), str(operator_tab_id or "").strip(), int(operation_revision)
    status = consumer_daily_use_recovery_status(*consumer, purpose, *use, runtime_root=runtime_root)
    if not status.get("replacement_available") or not tab or revision <= 0:
        return _public({**status, "ok": False, "status": "consumer_daily_use_replacement_not_available", "findings": [{"kind": "consumer_daily_use_replacement_not_available"}]})
    daily_root, _, old_selection = _selection_private(runtime_root, consumer)
    use_root, _, old_preflight = _active_preflight(runtime_root, consumer, use)
    if not old_selection or not old_preflight:
        return _public({"status": "expired_selection_and_preflight_required", "findings": [{"kind": "expired_selection_and_preflight_required"}]})
    binding, binding_findings = _current_binding(runtime_root, consumer)
    if binding_findings:
        return _public({"status": "consumer_daily_use_replacement_blocked", "findings": binding_findings})
    replacement_id = "daily-use-replacement-" + secrets.token_hex(12)
    expires_at = _future(replacement_ttl_seconds)
    material = {
        "consumer_identity": list(consumer), "use_identity": list(use), "selection_purpose": purpose,
        "old_selection_id": old_selection.get("selection_id"), "old_selection_sha256": old_selection.get("selection_sha256"),
        "old_preflight_receipt_id": old_preflight.get("preflight_receipt_id"), "old_preflight_receipt_sha256": old_preflight.get("preflight_receipt_sha256"),
        "current_consumer_binding_sha256": binding.get("consumer_binding_sha256"), "runtime_root_sha256": _runtime_binding(runtime_root),
        "replacement_id": replacement_id, "replacement_expires_at": expires_at, "operator_tab_id": tab, "operation_revision": revision,
    }
    token = _authorization(daily_root, "daily-use-replacement", material)
    atomic_json(daily_root / "replacement_previews" / f"{replacement_id}.json", {"schema": REPLACEMENT_SCHEMA, **material, "preview_only": True, "content_free": True})
    return _public({**status, **material, "ok": True, "status": "consumer_daily_use_replacement_preview_ready", "authorization_token": token, "literal_confirmation_required": REPLACEMENT_CONFIRMATION, "findings": []})


def replace_expired_daily_use_binding(
    token: str, *, confirm: str, consumer_id: str, consumer_schema: str, consumer_version: str, expected_use: str,
    selection_purpose: str, use_id: str, use_schema: str, use_version: str, declared_use: str,
    operator_tab_id: str, operation_revision: int, interrupt_after: str = "",
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    consumer, use = _identities((consumer_id, consumer_schema, consumer_version, expected_use), (use_id, use_schema, use_version, declared_use))
    purpose, tab, revision = str(selection_purpose or "").strip(), str(operator_tab_id or "").strip(), int(operation_revision)
    daily_root, old_pointer, old_selection = _selection_private(runtime_root, consumer)
    use_root, old_preflight_pointer, old_preflight = _active_preflight(runtime_root, consumer, use)
    auth = _load_authorization(daily_root, "daily-use-replacement", token)
    if auth.get("reused"):
        return _public({"status": "authorization_reused", "findings": [{"kind": "authorization_reused"}]})
    material = dict(auth.get("material") or {})
    binding, binding_findings = _current_binding(runtime_root, consumer)
    expected = {
        "consumer_identity": list(consumer), "use_identity": list(use), "selection_purpose": purpose,
        "old_selection_id": old_selection.get("selection_id"), "old_selection_sha256": old_selection.get("selection_sha256"),
        "old_preflight_receipt_id": old_preflight.get("preflight_receipt_id"), "old_preflight_receipt_sha256": old_preflight.get("preflight_receipt_sha256"),
        "current_consumer_binding_sha256": binding.get("consumer_binding_sha256"), "runtime_root_sha256": _runtime_binding(runtime_root),
        "replacement_id": material.get("replacement_id"), "replacement_expires_at": material.get("replacement_expires_at"),
        "operator_tab_id": tab, "operation_revision": revision,
    }
    if confirm != REPLACEMENT_CONFIRMATION or not auth or binding_findings or material != expected or not (_expired(str(old_selection.get("selection_expires_at") or "")) or _expired(str(old_preflight.get("preflight_expires_at") or ""))):
        return _public({"status": "consumer_daily_use_replacement_binding_rejected", "findings": binding_findings or [{"kind": "consumer_daily_use_replacement_binding_rejected"}]})
    replacement_id = str(material["replacement_id"])
    operation_path = daily_root / "replacement_operations" / f"{replacement_id}.json"
    try:
        with metadata_mutation_lock(daily_root / "active_selection.json"):
            operation = read_json(operation_path)
            recovery = bool(operation)
            if operation and str(operation.get("operation_sha256") or "") != _record_digest(operation, "operation_sha256"):
                return _public({"status": "consumer_daily_use_replacement_operation_invalid", "findings": [{"kind": "consumer_daily_use_replacement_operation_invalid"}]})
            if not operation:
                selection_id = "consumer-selection-" + secrets.token_hex(12)
                selection = {
                    "schema": "eidolon-release-authority-consumer-selection-v1", **binding,
                    "selection_id": selection_id, "selection_purpose": purpose, "operator_tab_id": tab,
                    "operation_revision": revision, "selection_expires_at": material["replacement_expires_at"],
                    "selection_operation_id": "replacement-" + replacement_id, "created_at": utc_now(),
                    "grants_authority": False, "content_free": True,
                }
                selection["selection_sha256"] = _record_digest(selection, "selection_sha256")
                preflight_id = "consumer-use-preflight-" + secrets.token_hex(12)
                preflight = {
                    "schema": "eidolon-release-authority-consumer-use-preflight-v1",
                    **dict(zip(("consumer_id", "consumer_schema", "consumer_version", "expected_use"), consumer)),
                    **dict(zip(("use_id", "use_schema", "use_version", "declared_use"), use)),
                    "consumer_key_sha256": _consumer_key(*consumer), "runtime_root_sha256": _runtime_binding(runtime_root),
                    "consumer_receipt_sha256": selection.get("consumer_receipt_sha256"), "selection_id": selection_id,
                    "selection_sha256": selection["selection_sha256"], "selection_purpose": purpose,
                    "selection_expires_at": selection["selection_expires_at"], "preflight_receipt_id": preflight_id,
                    "preflight_expires_at": selection["selection_expires_at"],
                    "required_scopes": _normalize_scopes(old_preflight.get("required_scopes") or selection.get("required_scopes") or []),
                    "unsupported_scopes": _normalize_scopes(old_preflight.get("unsupported_scopes") or selection.get("unsupported_scopes") or []),
                    "scope_sources": dict(old_preflight.get("scope_sources") or {}), "operator_tab_id": tab,
                    "operation_revision": revision, "preflight_operation_id": "replacement-" + replacement_id,
                    "created_at": utc_now(), "grants_authority": False, "executes_consumer": False, "content_free": True,
                }
                preflight["preflight_receipt_sha256"] = _record_digest(preflight, "preflight_receipt_sha256")
                operation = _operation(operation_path, {"schema": REPLACEMENT_SCHEMA, "replacement_id": replacement_id, "status": "prepared", "selection": selection, "preflight": preflight, "old_selection_pointer": old_pointer, "old_preflight_pointer": old_preflight_pointer, "authorization_binding_sha256": auth.get("binding_sha256"), "started_at": utc_now(), "updated_at": utc_now(), "content_free": True})
            selection, preflight = dict(operation["selection"]), dict(operation["preflight"])
            if interrupt_after == "prepared" and operation.get("status") == "prepared":
                return _public({**material, "status": "consumer_daily_use_replacement_interrupted", "findings": [{"kind": "consumer_daily_use_replacement_interrupted_after_prepared"}]})
            atomic_json(daily_root / "selections" / f"{selection['selection_id']}.json", selection)
            atomic_json(use_root / "receipts" / f"{preflight['preflight_receipt_id']}.json", preflight)
            operation.update({"status": "records_written", "updated_at": utc_now()})
            operation = _operation(operation_path, operation)
            if interrupt_after == "records_written":
                return _public({**material, "status": "consumer_daily_use_replacement_interrupted", "findings": [{"kind": "consumer_daily_use_replacement_interrupted_after_records"}]})
            selection_operation = {
                "schema": "eidolon-release-authority-consumer-selection-operation-v1",
                "selection_operation_id": selection["selection_operation_id"],
                "status": "completed", "selection": selection, "replacement_id": replacement_id,
                "started_at": operation.get("started_at"), "completed_at": utc_now(), "updated_at": utc_now(),
                "content_free": True,
            }
            _operation(daily_root / "operations" / f"{selection['selection_operation_id']}.json", selection_operation)
            preflight_operation = {
                "schema": "eidolon-release-authority-consumer-use-preflight-operation-v1",
                "preflight_operation_id": preflight["preflight_operation_id"],
                "status": "completed", "receipt": preflight, "replacement_id": replacement_id,
                "started_at": operation.get("started_at"), "completed_at": utc_now(), "updated_at": utc_now(),
                "content_free": True,
            }
            _operation(use_root / "operations" / f"{preflight['preflight_operation_id']}.json", preflight_operation)
            new_selection_pointer = {"schema": selection["schema"], "selection_id": selection["selection_id"], "selection_sha256": selection["selection_sha256"], "consumer_receipt_sha256": selection["consumer_receipt_sha256"], "content_free": True}
            new_preflight_pointer = {"schema": preflight["schema"], "preflight_receipt_id": preflight["preflight_receipt_id"], "preflight_receipt_sha256": preflight["preflight_receipt_sha256"], "selection_sha256": preflight["selection_sha256"], "content_free": True}
            atomic_json(use_root / "active_preflight.json", new_preflight_pointer)
            atomic_json(daily_root / "active_selection.json", new_selection_pointer)
            operation.update({"status": "completed", "completed_at": utc_now(), "updated_at": utc_now()})
            _operation(operation_path, operation)
            used = daily_root / "authorizations" / "used" / f"{digest_payload({'token': token})}.json"
            atomic_json(used, {"schema": "eidolon-used-consumer-daily-use-replacement-token-v1", "category": "daily-use-replacement", "record_id": replacement_id, "used_at": utc_now(), "content_free": True})
    except MetadataMutationBusy:
        return _public({"status": "consumer_daily_use_replacement_busy", "findings": [{"kind": "consumer_daily_use_replacement_busy"}]})
    return _public({**material, "selection_id": selection["selection_id"], "selection_sha256": selection["selection_sha256"], "preflight_receipt_id": preflight["preflight_receipt_id"], "preflight_receipt_sha256": preflight["preflight_receipt_sha256"], "ok": True, "status": "consumer_daily_use_binding_replaced", "replacement_available": False, "recovery_available": False, "replacement_recovery_performed": recovery})


def preview_consumer_daily_use_cleanup(
    consumer_id: str, consumer_schema: str, consumer_version: str, expected_use: str,
    selection_purpose: str, use_id: str, use_schema: str, use_version: str, declared_use: str,
    *, operator_tab_id: str, operation_revision: int, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    consumer, use = _identities((consumer_id, consumer_schema, consumer_version, expected_use), (use_id, use_schema, use_version, declared_use))
    tab, revision = str(operator_tab_id or "").strip(), int(operation_revision)
    daily_root = _daily_root(runtime_root, consumer)
    use_root = _use_root(runtime_root, consumer, use)
    rows = [{"root": "daily", **row} for row in _exact_abandoned(daily_root, runtime_root)] + [{"root": "use", **row} for row in _exact_abandoned(use_root, runtime_root)]
    if not rows or not tab or revision <= 0:
        return _public({"status": "consumer_daily_use_cleanup_not_available", "findings": [{"kind": "consumer_daily_use_cleanup_not_available"}]})
    material = {"consumer_identity": list(consumer), "use_identity": list(use), "runtime_root_sha256": _runtime_binding(runtime_root), "artifacts": rows, "operator_tab_id": tab, "operation_revision": revision}
    token = _authorization(daily_root, "daily-use-cleanup", material)
    return _public({"ok": True, "status": "consumer_daily_use_cleanup_preview_ready", "cleanup_available": True, "authorization_token": token, "literal_confirmation_required": CLEANUP_CONFIRMATION})


def cleanup_consumer_daily_use_artifacts(
    token: str, *, confirm: str, consumer_id: str, consumer_schema: str, consumer_version: str, expected_use: str,
    use_id: str, use_schema: str, use_version: str, declared_use: str,
    operator_tab_id: str, operation_revision: int, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    consumer, use = _identities((consumer_id, consumer_schema, consumer_version, expected_use), (use_id, use_schema, use_version, declared_use))
    daily_root, use_root = _daily_root(runtime_root, consumer), _use_root(runtime_root, consumer, use)
    auth = _load_authorization(daily_root, "daily-use-cleanup", token)
    rows = [{"root": "daily", **row} for row in _exact_abandoned(daily_root, runtime_root)] + [{"root": "use", **row} for row in _exact_abandoned(use_root, runtime_root)]
    expected = {"consumer_identity": list(consumer), "use_identity": list(use), "runtime_root_sha256": _runtime_binding(runtime_root), "artifacts": rows, "operator_tab_id": str(operator_tab_id or "").strip(), "operation_revision": int(operation_revision)}
    if confirm != CLEANUP_CONFIRMATION or not auth or dict(auth.get("material") or {}) != expected:
        return _public({"status": "consumer_daily_use_cleanup_binding_rejected", "findings": [{"kind": "consumer_daily_use_cleanup_binding_rejected"}]})
    try:
        with metadata_mutation_lock(daily_root / "cleanup.lock"):
            for row in rows:
                root = daily_root if row["root"] == "daily" else use_root
                path = root / "abandoned" / row["name"]
                record = read_json(path)
                if str(record.get("record_sha256") or "") != row["record_sha256"]:
                    return _public({"status": "consumer_daily_use_cleanup_artifact_drift", "findings": [{"kind": "consumer_daily_use_cleanup_artifact_drift"}]})
            for row in rows:
                root = daily_root if row["root"] == "daily" else use_root
                (root / "abandoned" / row["name"]).unlink(missing_ok=True)
            used = daily_root / "authorizations" / "used" / f"{digest_payload({'token': token})}.json"
            atomic_json(used, {"schema": "eidolon-used-consumer-daily-use-cleanup-token-v1", "category": "daily-use-cleanup", "record_id": digest_payload(rows), "used_at": utc_now(), "content_free": True})
    except MetadataMutationBusy:
        return _public({"status": "consumer_daily_use_cleanup_busy", "findings": [{"kind": "consumer_daily_use_cleanup_busy"}]})
    return _public({"ok": True, "status": "consumer_daily_use_cleanup_completed", "cleanup_available": False})


def _chain_material(
    runtime_root: str | Path | None,
    consumer: tuple[str, str, str, str],
    purpose: str,
    use: tuple[str, str, str, str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    daily_root, selection_pointer, selection = _selection_private(runtime_root, consumer)
    use_root, preflight_pointer, preflight = _active_preflight(runtime_root, consumer, use)
    findings: list[dict[str, Any]] = []
    if not selection or str(selection.get("selection_sha256") or "") != _record_digest(selection, "selection_sha256"):
        findings.append({"kind": "consumer_selection_record_invalid"})
    if not preflight or str(preflight.get("preflight_receipt_sha256") or "") != _record_digest(preflight, "preflight_receipt_sha256"):
        findings.append({"kind": "consumer_use_preflight_record_invalid"})
    if selection and str(selection.get("selection_purpose") or "") != purpose:
        findings.append({"kind": "consumer_selection_purpose_mismatch"})
    if preflight and str(preflight.get("selection_sha256") or "") != str(selection.get("selection_sha256") or ""):
        findings.append({"kind": "consumer_selection_preflight_binding_mismatch"})
    if selection_pointer and str(selection_pointer.get("selection_sha256") or "") != str(selection.get("selection_sha256") or ""):
        findings.append({"kind": "consumer_selection_pointer_drift"})
    if preflight_pointer and str(preflight_pointer.get("preflight_receipt_sha256") or "") != str(preflight.get("preflight_receipt_sha256") or ""):
        findings.append({"kind": "consumer_preflight_pointer_drift"})
    current_binding, current_binding_findings = _current_binding(runtime_root, consumer)
    material = {
        "consumer_identity": list(consumer), "use_identity": list(use), "selection_purpose": purpose,
        "consumer_key_sha256": _consumer_key(*consumer), "runtime_root_sha256": _runtime_binding(runtime_root),
        "selection_id": selection.get("selection_id"), "selection_sha256": selection.get("selection_sha256"),
        "selection_expires_at": selection.get("selection_expires_at"),
        "preflight_receipt_id": preflight.get("preflight_receipt_id"), "preflight_receipt_sha256": preflight.get("preflight_receipt_sha256"),
        "preflight_expires_at": preflight.get("preflight_expires_at"),
        "consumer_receipt_sha256": selection.get("consumer_receipt_sha256"),
        "required_scopes": _normalize_scopes(preflight.get("required_scopes") or []),
        "unsupported_scopes": _normalize_scopes(preflight.get("unsupported_scopes") or []),
        "scope_sources": dict(preflight.get("scope_sources") or {}),
        "current_consumer_binding_sha256": current_binding.get("consumer_binding_sha256"),
        "current_binding_finding_kinds": sorted(str(row.get("kind") or "") for row in current_binding_findings),
    }
    material["chain_binding_sha256"] = digest_payload(material)
    return material, findings


def _successor_pointer_path(root: Path, predecessor_preflight_sha256: str) -> Path:
    return root / "successor_revalidations" / "by_predecessor" / f"{predecessor_preflight_sha256}.json"


def preview_successor_consumer_daily_use_revalidation(
    predecessor_consumer: Sequence[str], predecessor_selection_purpose: str, predecessor_use: Sequence[str],
    successor_consumer: Sequence[str], successor_selection_purpose: str, successor_use: Sequence[str],
    *, operator_tab_id: str, operation_revision: int, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    predecessor, pred_use = _identities(predecessor_consumer, predecessor_use)
    successor, succ_use = _identities(successor_consumer, successor_use)
    pred_purpose, succ_purpose = str(predecessor_selection_purpose or "").strip(), str(successor_selection_purpose or "").strip()
    tab, revision = str(operator_tab_id or "").strip(), int(operation_revision)
    findings: list[dict[str, Any]] = []
    if not all(predecessor) or not all(successor) or not all(pred_use) or not all(succ_use) or not pred_purpose or not succ_purpose or not tab or revision <= 0:
        findings.append({"kind": "exact_predecessor_successor_declarations_required"})
    if predecessor == successor and pred_use == succ_use:
        findings.append({"kind": "self_replacement_rejected"})
    if predecessor[:2] != successor[:2]:
        findings.append({"kind": "cross_consumer_revalidation_rejected"})
    if pred_use[:2] != succ_use[:2]:
        findings.append({"kind": "cross_use_revalidation_rejected"})
    pred_material, pred_findings = _chain_material(runtime_root, predecessor, pred_purpose, pred_use)
    succ_material, succ_findings = _chain_material(runtime_root, successor, succ_purpose, succ_use)
    findings.extend(pred_findings)
    findings.extend(succ_findings)
    successor_selection = consumer_selection_status(*successor, succ_purpose, runtime_root=runtime_root)
    successor_preflight = consumer_use_preflight_status(*successor, succ_purpose, *succ_use, runtime_root=runtime_root)
    if not successor_selection.get("ok") or not successor_preflight.get("ok"):
        findings.append({"kind": "coherent_successor_selection_preflight_required"})
    if pred_material.get("required_scopes") != succ_material.get("required_scopes"):
        findings.append({"kind": "successor_required_scope_overclaim"})
    if pred_material.get("unsupported_scopes") != succ_material.get("unsupported_scopes"):
        findings.append({"kind": "successor_unsupported_scope_mismatch"})
    root = _daily_root(runtime_root, predecessor)
    pointer = read_json(_successor_pointer_path(root, str(pred_material.get("preflight_receipt_sha256") or "")))
    if pointer:
        findings.append({"kind": "predecessor_successor_fork_rejected"})
    if findings:
        return _public({"status": "successor_consumer_daily_use_revalidation_rejected", "findings": findings})
    revalidation_id = "consumer-daily-use-revalidation-" + secrets.token_hex(12)
    material = {
        "predecessor": pred_material, "successor": succ_material,
        "successor_revalidation_id": revalidation_id,
        "runtime_root_sha256": _runtime_binding(runtime_root), "operator_tab_id": tab, "operation_revision": revision,
    }
    material["revalidation_binding_sha256"] = digest_payload(material)
    token = _authorization(root, "successor-daily-use-revalidation", material)
    atomic_json(root / "successor_revalidations" / "previews" / f"{revalidation_id}.json", {"schema": SUCCESSOR_SCHEMA, **material, "preview_only": True, "content_free": True})
    return _public({
        "ok": True, "status": "successor_consumer_daily_use_revalidation_preview_ready",
        "successor_revalidation_id": revalidation_id, "authorization_token": token,
        "literal_confirmation_required": SUCCESSOR_CONFIRMATION,
    })


def create_successor_consumer_daily_use_revalidation(
    token: str, *, confirm: str,
    predecessor_consumer: Sequence[str], predecessor_selection_purpose: str, predecessor_use: Sequence[str],
    successor_consumer: Sequence[str], successor_selection_purpose: str, successor_use: Sequence[str],
    operator_tab_id: str, operation_revision: int, interrupt_after: str = "",
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    predecessor, pred_use = _identities(predecessor_consumer, predecessor_use)
    successor, succ_use = _identities(successor_consumer, successor_use)
    pred_purpose, succ_purpose = str(predecessor_selection_purpose or "").strip(), str(successor_selection_purpose or "").strip()
    tab, revision = str(operator_tab_id or "").strip(), int(operation_revision)
    root = _daily_root(runtime_root, predecessor)
    auth = _load_authorization(root, "successor-daily-use-revalidation", token)
    if auth.get("reused"):
        return _public({"status": "authorization_reused", "findings": [{"kind": "authorization_reused"}]})
    pred_material, pred_findings = _chain_material(runtime_root, predecessor, pred_purpose, pred_use)
    succ_material, succ_findings = _chain_material(runtime_root, successor, succ_purpose, succ_use)
    material = dict(auth.get("material") or {})
    expected = {
        "predecessor": pred_material, "successor": succ_material,
        "successor_revalidation_id": material.get("successor_revalidation_id"),
        "runtime_root_sha256": _runtime_binding(runtime_root), "operator_tab_id": tab, "operation_revision": revision,
    }
    expected["revalidation_binding_sha256"] = digest_payload(expected)
    if (
        confirm != SUCCESSOR_CONFIRMATION or not auth or pred_findings or succ_findings
        or material != expected or predecessor == successor or predecessor[:2] != successor[:2] or pred_use[:2] != succ_use[:2]
        or pred_material.get("required_scopes") != succ_material.get("required_scopes")
        or pred_material.get("unsupported_scopes") != succ_material.get("unsupported_scopes")
    ):
        return _public({"status": "successor_consumer_daily_use_revalidation_binding_rejected", "findings": pred_findings + succ_findings or [{"kind": "successor_consumer_daily_use_revalidation_binding_rejected"}]})
    pointer_path = _successor_pointer_path(root, str(pred_material.get("preflight_receipt_sha256") or ""))
    revalidation_id = str(material["successor_revalidation_id"])
    operation_path = root / "successor_revalidations" / "operations" / f"{revalidation_id}.json"
    try:
        with metadata_mutation_lock(pointer_path):
            operation = read_json(operation_path)
            recovery = bool(operation)
            if operation and str(operation.get("operation_sha256") or "") != _record_digest(operation, "operation_sha256"):
                return _public({"status": "successor_revalidation_operation_invalid", "findings": [{"kind": "successor_revalidation_operation_invalid"}]})
            if not operation:
                record = {
                    "schema": SUCCESSOR_SCHEMA, **material, "created_at": utc_now(),
                    "grants_authority": False, "executes_consumer": False, "future_use_authorized": False,
                    "content_free": True,
                }
                record["successor_revalidation_sha256"] = _record_digest(record, "successor_revalidation_sha256")
                operation = _operation(operation_path, {
                    "schema": "eidolon-release-authority-consumer-daily-use-successor-revalidation-operation-v1",
                    "successor_revalidation_id": revalidation_id, "status": "prepared", "record": record,
                    "authorization_binding_sha256": auth.get("binding_sha256"), "started_at": utc_now(), "updated_at": utc_now(), "content_free": True,
                })
            record = dict(operation.get("record") or {})
            if interrupt_after == "prepared" and operation.get("status") == "prepared":
                return _public({"status": "successor_revalidation_interrupted", "findings": [{"kind": "successor_revalidation_interrupted_after_prepared"}]})
            record_path = root / "successor_revalidations" / "receipts" / f"{revalidation_id}.json"
            existing = read_json(record_path)
            if existing and existing != record:
                return _public({"status": "successor_revalidation_record_contradiction", "findings": [{"kind": "successor_revalidation_record_contradiction"}]})
            if not existing:
                atomic_json(record_path, record)
            operation.update({"status": "record_written", "updated_at": utc_now()})
            operation = _operation(operation_path, operation)
            if interrupt_after == "record_written":
                return _public({"status": "successor_revalidation_interrupted", "successor_revalidation_id": revalidation_id, "findings": [{"kind": "successor_revalidation_interrupted_after_record"}]})
            pointer = read_json(pointer_path)
            pointer_record = {
                "schema": SUCCESSOR_SCHEMA, "successor_revalidation_id": revalidation_id,
                "successor_revalidation_sha256": record["successor_revalidation_sha256"],
                "predecessor_preflight_receipt_sha256": pred_material["preflight_receipt_sha256"],
                "successor_preflight_receipt_sha256": succ_material["preflight_receipt_sha256"], "content_free": True,
            }
            if pointer and pointer != pointer_record:
                return _public({"status": "predecessor_successor_fork_rejected", "findings": [{"kind": "predecessor_successor_fork_rejected"}]})
            if not pointer:
                atomic_json(pointer_path, pointer_record)
            operation.update({"status": "completed", "completed_at": utc_now(), "updated_at": utc_now()})
            _operation(operation_path, operation)
            used = root / "authorizations" / "used" / f"{digest_payload({'token': token})}.json"
            atomic_json(used, {"schema": "eidolon-used-successor-revalidation-token-v1", "category": "successor-daily-use-revalidation", "record_id": revalidation_id, "used_at": utc_now(), "content_free": True})
    except MetadataMutationBusy:
        return _public({"status": "successor_revalidation_busy", "findings": [{"kind": "successor_revalidation_busy"}]})
    return _public({
        "ok": True, "status": "successor_consumer_daily_use_revalidation_created",
        "successor_revalidation_id": revalidation_id, "successor_revalidation_sha256": record["successor_revalidation_sha256"],
        "successor_revalidation_present": True, "successor_revalidation_stale": False,
        "successor_revalidation_recovery_performed": recovery,
    })


def successor_consumer_daily_use_revalidation_status(
    predecessor_consumer: Sequence[str], predecessor_selection_purpose: str, predecessor_use: Sequence[str],
    successor_consumer: Sequence[str], successor_selection_purpose: str, successor_use: Sequence[str],
    *, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    predecessor, pred_use = _identities(predecessor_consumer, predecessor_use)
    successor, succ_use = _identities(successor_consumer, successor_use)
    pred_material, pred_findings = _chain_material(runtime_root, predecessor, str(predecessor_selection_purpose or "").strip(), pred_use)
    succ_material, succ_findings = _chain_material(runtime_root, successor, str(successor_selection_purpose or "").strip(), succ_use)
    root = _daily_root(runtime_root, predecessor)
    pointer = read_json(_successor_pointer_path(root, str(pred_material.get("preflight_receipt_sha256") or "")))
    record_id = str(pointer.get("successor_revalidation_id") or "")
    record = read_json(root / "successor_revalidations" / "receipts" / f"{record_id}.json") if record_id else {}
    findings = [*pred_findings, *succ_findings]
    if not pointer or not record:
        findings.append({"kind": "successor_revalidation_not_created"})
    elif str(record.get("successor_revalidation_sha256") or "") != _record_digest(record, "successor_revalidation_sha256"):
        findings.append({"kind": "successor_revalidation_record_invalid"})
    else:
        if record.get("predecessor") != pred_material:
            findings.append({"kind": "successor_revalidation_predecessor_drift"})
        if record.get("successor") != succ_material:
            findings.append({"kind": "successor_revalidation_successor_drift"})
        if str(pointer.get("successor_revalidation_sha256") or "") != str(record.get("successor_revalidation_sha256") or ""):
            findings.append({"kind": "successor_revalidation_pointer_drift"})
    return _public({
        "ok": not findings,
        "status": "successor_consumer_daily_use_revalidation_current" if not findings else "successor_consumer_daily_use_revalidation_stale",
        "successor_revalidation_id": record_id, "successor_revalidation_sha256": record.get("successor_revalidation_sha256"),
        "successor_revalidation_present": bool(record), "successor_revalidation_stale": bool(findings), "findings": findings,
    })


def release_authority_consumer_daily_use_binding_status(
    consumer_id: str = "", consumer_schema: str = "", consumer_version: str = "", expected_use: str = "",
    selection_purpose: str = "", use_id: str = "", use_schema: str = "", use_version: str = "", declared_use: str = "",
    successor_consumer: Sequence[str] | None = None, successor_selection_purpose: str = "", successor_use: Sequence[str] | None = None,
    *, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    consumer, use = _identities((consumer_id, consumer_schema, consumer_version, expected_use), (use_id, use_schema, use_version, declared_use))
    purpose = str(selection_purpose or "").strip()
    selected = any(consumer) or any(use) or bool(purpose)
    if not selected:
        return _public({"ok": True, "status": "consumer_daily_use_binding_not_selected"})
    daily = release_authority_consumer_daily_use_status(*consumer, purpose, *use, runtime_root=runtime_root)
    recovery = consumer_daily_use_recovery_status(*consumer, purpose, *use, runtime_root=runtime_root)
    successor_selected = bool(successor_consumer or successor_use or successor_selection_purpose)
    successor = _public({"ok": True, "status": "successor_consumer_not_selected"})
    if successor_selected:
        successor = successor_consumer_daily_use_revalidation_status(
            consumer, purpose, use, tuple(successor_consumer or ()), str(successor_selection_purpose or "").strip(), tuple(successor_use or ()), runtime_root=runtime_root,
        )
    findings: list[dict[str, Any]] = []
    if not daily.get("ok"):
        findings.append({"kind": "consumer_daily_use_attention_required"})
    if recovery.get("recovery_available"):
        findings.append({"kind": "consumer_daily_use_recovery_available"})
    if recovery.get("replacement_available"):
        findings.append({"kind": "consumer_daily_use_replacement_available"})
    if recovery.get("finding_count") and not recovery.get("recovery_available") and not recovery.get("replacement_available"):
        findings.append({"kind": "consumer_daily_use_recovery_state_contradictory"})
    if successor_selected and not successor.get("ok"):
        findings.append({"kind": "successor_consumer_revalidation_attention_required"})
    return _public({
        **dict(zip(("consumer_id", "consumer_schema", "consumer_version", "expected_use"), consumer)),
        **dict(zip(("use_id", "use_schema", "use_version", "declared_use"), use)),
        "selection_purpose": purpose,
        "selection_id": daily.get("selection_id"), "selection_sha256": daily.get("selection_sha256"),
        "preflight_receipt_id": daily.get("preflight_receipt_id"), "preflight_receipt_sha256": daily.get("preflight_receipt_sha256"),
        "recovery_available": recovery.get("recovery_available"), "replacement_available": recovery.get("replacement_available"),
        "cleanup_available": recovery.get("cleanup_available"), "selection_expired": recovery.get("selection_expired"),
        "preflight_expired": recovery.get("preflight_expired"), "recovery_target": recovery.get("recovery_target"),
        "successor_revalidation_id": successor.get("successor_revalidation_id"),
        "successor_revalidation_sha256": successor.get("successor_revalidation_sha256"),
        "successor_revalidation_present": successor.get("successor_revalidation_present"),
        "successor_revalidation_stale": successor.get("successor_revalidation_stale"),
        "ok": not findings,
        "status": "release_authority_consumer_daily_use_binding_coherent" if not findings else "release_authority_consumer_daily_use_binding_attention_required",
        "findings": findings,
    })
