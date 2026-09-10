from __future__ import annotations

"""Exact authority-free handoff and result validation for one consumer use.

The handoff plan never discovers or executes a consumer.  Result validation
accepts one explicitly supplied content-free result declaration and never turns
that result into installation, promotion, certification, policy, provider,
model, native-platform, or future-use authority.
"""

from pathlib import Path
import secrets
from typing import Any, Mapping, Sequence

try:
    from metadata_mutation_coordination import MetadataMutationBusy, metadata_mutation_lock
    from release_candidate_identity import atomic_json, digest_payload, read_json, utc_now
    from release_authority_consumer import _consumer_key, _record_digest, _normalize_scopes
    from release_authority_consumer_daily_use import RECEIPT_BINDING_FIELDS, _authorization, _daily_root, _identity, _load_authorization, _operation, _runtime_binding, _selection_private, _use_identity, _use_root
    from release_authority_consumer_daily_use_recovery import release_authority_consumer_daily_use_binding_status
except ImportError:
    from metadata_mutation_coordination import MetadataMutationBusy, metadata_mutation_lock
    from release_candidate_identity import atomic_json, digest_payload, read_json, utc_now
    from release_authority_consumer import _consumer_key, _record_digest, _normalize_scopes
    from release_authority_consumer_daily_use import (
        RECEIPT_BINDING_FIELDS, _authorization, _daily_root, _identity, _load_authorization,
        _operation, _runtime_binding, _selection_private, _use_identity, _use_root,
    )
    from release_authority_consumer_daily_use_recovery import release_authority_consumer_daily_use_binding_status

USE_HANDOFF_CONTRACT_VERSION = "1"
PLAN_CONFIRMATION = "ACKNOWLEDGE EXACT CONSUMER USE HANDOFF PLAN"
RESULT_CONFIRMATION = "ACKNOWLEDGE EXACT DOWNSTREAM CONSUMER RESULT VALIDATION"
PLAN_SCHEMA = "eidolon-release-authority-consumer-use-handoff-plan-v1"
PLAN_OPERATION_SCHEMA = "eidolon-release-authority-consumer-use-handoff-plan-operation-v1"
RESULT_SCHEMA = "eidolon-release-authority-consumer-result-validation-receipt-v1"
RESULT_OPERATION_SCHEMA = "eidolon-release-authority-consumer-result-validation-operation-v1"
RESULT_STATUSES = {"completed", "failed", "declined"}
AUTHORITY_FLAGS = (
    "grants_authority", "installation_authorized", "promotion_authorized", "certification_authorized",
    "policy_migration_authorized", "provider_access_authorized", "model_access_authorized",
    "native_platform_certification_authorized", "future_use_authorized",
)


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
        "status": str(data.get("status") or "consumer_use_handoff_unavailable"),
        "contract_version": USE_HANDOFF_CONTRACT_VERSION,
        "consumer_id": str(data.get("consumer_id") or ""),
        "consumer_schema": str(data.get("consumer_schema") or ""),
        "consumer_version": str(data.get("consumer_version") or ""),
        "expected_use": str(data.get("expected_use") or ""),
        "selection_purpose": str(data.get("selection_purpose") or ""),
        "use_id": str(data.get("use_id") or ""),
        "use_schema": str(data.get("use_schema") or ""),
        "use_version": str(data.get("use_version") or ""),
        "declared_use": str(data.get("declared_use") or ""),
        "downstream_consumer_id": str(data.get("downstream_consumer_id") or ""),
        "downstream_consumer_schema": str(data.get("downstream_consumer_schema") or ""),
        "downstream_consumer_version": str(data.get("downstream_consumer_version") or ""),
        "downstream_expected_use": str(data.get("downstream_expected_use") or ""),
        "expected_result_schema": str(data.get("expected_result_schema") or ""),
        "expected_result_version": str(data.get("expected_result_version") or ""),
        "expected_outcome": str(data.get("expected_outcome") or ""),
        "handoff_plan_id": str(data.get("handoff_plan_id") or ""),
        "handoff_plan_sha256": str(data.get("handoff_plan_sha256") or ""),
        "handoff_plan_present": bool(data.get("handoff_plan_present")),
        "handoff_plan_stale": bool(data.get("handoff_plan_stale")),
        "handoff_operation_status": str(data.get("handoff_operation_status") or ""),
        "handoff_recovery_performed": bool(data.get("handoff_recovery_performed")),
        "result_id": str(data.get("result_id") or ""),
        "result_status": str(data.get("result_status") or ""),
        "result_validation_id": str(data.get("result_validation_id") or ""),
        "result_validation_sha256": str(data.get("result_validation_sha256") or ""),
        "result_validation_present": bool(data.get("result_validation_present")),
        "result_validation_stale": bool(data.get("result_validation_stale")),
        "result_operation_status": str(data.get("result_operation_status") or ""),
        "result_recovery_performed": bool(data.get("result_recovery_performed")),
        "authorization_token": str(data.get("authorization_token") or ""),
        "literal_confirmation_required": str(data.get("literal_confirmation_required") or ""),
        "findings": findings,
        "finding_count": sum(int(item["count"]) for item in findings),
        "consumer_discovery_performed": False,
        "newest_consumer_inferred": False,
        "newest_handoff_plan_inferred": False,
        "newest_result_inferred": False,
        "downstream_consumer_executed": False,
        "result_content_imported": False,
        "authority_granted": False,
        "installation_authorized": False,
        "promotion_authorized": False,
        "certification_authorized": False,
        "policy_migration_authorized": False,
        "provider_access_authorized": False,
        "model_access_authorized": False,
        "native_platform_certification_authorized": False,
        "future_use_authorized": False,
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


def _active_preflight(runtime_root: str | Path | None, consumer: tuple[str, str, str, str], use: tuple[str, str, str, str]) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    root = _use_root(runtime_root, consumer, use)
    pointer = read_json(root / "active_preflight.json")
    receipt_id = str(pointer.get("preflight_receipt_id") or "")
    receipt = read_json(root / "receipts" / f"{receipt_id}.json") if receipt_id else {}
    return root, pointer, receipt


def _handoff_root(runtime_root: str | Path | None, consumer: tuple[str, str, str, str], use: tuple[str, str, str, str]) -> Path:
    return _use_root(runtime_root, consumer, use) / "handoff"


def _current_use_material(
    runtime_root: str | Path | None,
    consumer: tuple[str, str, str, str], purpose: str, use: tuple[str, str, str, str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    daily_status = release_authority_consumer_daily_use_binding_status(*consumer, purpose, *use, runtime_root=runtime_root)
    daily_root, selection_pointer, selection = _selection_private(runtime_root, consumer)
    use_root, preflight_pointer, preflight = _active_preflight(runtime_root, consumer, use)
    findings: list[dict[str, Any]] = []
    if not daily_status.get("ok"):
        findings.append({"kind": "coherent_consumer_daily_use_binding_required"})
    if not selection or str(selection.get("selection_sha256") or "") != _record_digest(selection, "selection_sha256"):
        findings.append({"kind": "consumer_selection_record_invalid"})
    if not preflight or str(preflight.get("preflight_receipt_sha256") or "") != _record_digest(preflight, "preflight_receipt_sha256"):
        findings.append({"kind": "consumer_use_preflight_record_invalid"})
    if str(preflight.get("selection_sha256") or "") != str(selection.get("selection_sha256") or ""):
        findings.append({"kind": "consumer_selection_preflight_binding_mismatch"})
    material: dict[str, Any] = {
        **dict(zip(("consumer_id", "consumer_schema", "consumer_version", "expected_use"), consumer)),
        **dict(zip(("use_id", "use_schema", "use_version", "declared_use"), use)),
        "selection_purpose": purpose, "consumer_key_sha256": _consumer_key(*consumer),
        "runtime_root_sha256": _runtime_binding(runtime_root),
        "selection_id": selection.get("selection_id"), "selection_sha256": selection.get("selection_sha256"),
        "selection_expires_at": selection.get("selection_expires_at"),
        "preflight_receipt_id": preflight.get("preflight_receipt_id"), "preflight_receipt_sha256": preflight.get("preflight_receipt_sha256"),
        "preflight_expires_at": preflight.get("preflight_expires_at"),
        "required_scopes": _normalize_scopes(preflight.get("required_scopes") or []),
        "unsupported_scopes": _normalize_scopes(preflight.get("unsupported_scopes") or []),
        "scope_sources": dict(preflight.get("scope_sources") or {}),
    }
    for field in RECEIPT_BINDING_FIELDS:
        material[field] = selection.get(field)
    material["consumer_use_binding_sha256"] = digest_payload(material)
    return material, findings


def _active_plan(runtime_root: str | Path | None, consumer: tuple[str, str, str, str], use: tuple[str, str, str, str]) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    root = _handoff_root(runtime_root, consumer, use)
    pointer = read_json(root / "active_plan.json")
    plan_id = str(pointer.get("handoff_plan_id") or "")
    plan = read_json(root / "plans" / f"{plan_id}.json") if plan_id else {}
    return root, pointer, plan


def consumer_use_handoff_plan_status(
    consumer_id: str, consumer_schema: str, consumer_version: str, expected_use: str,
    selection_purpose: str, use_id: str, use_schema: str, use_version: str, declared_use: str,
    downstream_consumer_id: str, downstream_consumer_schema: str, downstream_consumer_version: str, downstream_expected_use: str,
    expected_result_schema: str, expected_result_version: str, expected_outcome: str,
    *, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    consumer, use = _identities((consumer_id, consumer_schema, consumer_version, expected_use), (use_id, use_schema, use_version, declared_use))
    downstream = _identity((downstream_consumer_id, downstream_consumer_schema, downstream_consumer_version, downstream_expected_use))
    purpose, result_schema, result_version, outcome = str(selection_purpose or "").strip(), str(expected_result_schema or "").strip(), str(expected_result_version or "").strip(), str(expected_outcome or "").strip()
    root, pointer, plan = _active_plan(runtime_root, consumer, use)
    findings: list[dict[str, Any]] = []
    if not all(consumer) or not all(use) or not all(downstream) or not purpose or not result_schema or not result_version or not outcome:
        findings.append({"kind": "exact_consumer_use_handoff_declaration_required"})
    if not pointer or not plan:
        findings.append({"kind": "consumer_use_handoff_plan_not_created"})
    elif str(plan.get("handoff_plan_sha256") or "") != _record_digest(plan, "handoff_plan_sha256"):
        findings.append({"kind": "consumer_use_handoff_plan_invalid"})
    else:
        expected_identity = {
            "downstream_consumer_id": downstream[0], "downstream_consumer_schema": downstream[1],
            "downstream_consumer_version": downstream[2], "downstream_expected_use": downstream[3],
            "expected_result_schema": result_schema, "expected_result_version": result_version, "expected_outcome": outcome,
        }
        for field, expected in expected_identity.items():
            if str(plan.get(field) or "") != expected:
                findings.append({"kind": f"consumer_use_handoff_{field}_mismatch"})
        current, current_findings = _current_use_material(runtime_root, consumer, purpose, use)
        findings.extend(current_findings)
        if plan.get("consumer_use") != current:
            findings.append({"kind": "consumer_use_handoff_plan_drift"})
        if str(pointer.get("handoff_plan_sha256") or "") != str(plan.get("handoff_plan_sha256") or ""):
            findings.append({"kind": "consumer_use_handoff_pointer_drift"})
        operation_id = str(plan.get("handoff_operation_id") or "")
        operation = read_json(root / "operations" / f"{operation_id}.json") if operation_id else {}
        if not operation or str(operation.get("operation_sha256") or "") != _record_digest(operation, "operation_sha256") or operation.get("status") != "completed":
            findings.append({"kind": "consumer_use_handoff_operation_incomplete"})
    return _public({
        **plan, "ok": not findings,
        "status": "consumer_use_handoff_plan_current" if not findings else "consumer_use_handoff_plan_stale",
        "handoff_plan_present": bool(plan), "handoff_plan_stale": bool(findings),
        "handoff_operation_status": "completed" if plan and not findings else "attention_required", "findings": findings,
    })


def preview_consumer_use_handoff_plan(
    consumer_id: str, consumer_schema: str, consumer_version: str, expected_use: str,
    selection_purpose: str, use_id: str, use_schema: str, use_version: str, declared_use: str,
    downstream_consumer_id: str, downstream_consumer_schema: str, downstream_consumer_version: str, downstream_expected_use: str,
    expected_result_schema: str, expected_result_version: str, expected_outcome: str,
    *, operator_tab_id: str, operation_revision: int, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    consumer, use = _identities((consumer_id, consumer_schema, consumer_version, expected_use), (use_id, use_schema, use_version, declared_use))
    downstream = _identity((downstream_consumer_id, downstream_consumer_schema, downstream_consumer_version, downstream_expected_use))
    purpose, result_schema, result_version, outcome = str(selection_purpose or "").strip(), str(expected_result_schema or "").strip(), str(expected_result_version or "").strip(), str(expected_outcome or "").strip()
    tab, revision = str(operator_tab_id or "").strip(), int(operation_revision)
    if not all(consumer) or not all(use) or not all(downstream) or not purpose or not result_schema or not result_version or not outcome or not tab or revision <= 0:
        return _public({"status": "exact_consumer_use_handoff_declaration_required", "findings": [{"kind": "exact_consumer_use_handoff_declaration_required"}]})
    current = consumer_use_handoff_plan_status(*consumer, purpose, *use, *downstream, result_schema, result_version, outcome, runtime_root=runtime_root)
    if current.get("ok"):
        return _public({**current, "ok": False, "status": "consumer_use_handoff_plan_already_current", "findings": [{"kind": "consumer_use_handoff_plan_already_current"}]})
    consumer_use, findings = _current_use_material(runtime_root, consumer, purpose, use)
    if findings:
        return _public({"status": "consumer_use_handoff_plan_blocked", "findings": findings})
    plan_id = "consumer-use-handoff-plan-" + secrets.token_hex(12)
    material = {
        "consumer_use": consumer_use,
        "downstream_consumer_id": downstream[0], "downstream_consumer_schema": downstream[1],
        "downstream_consumer_version": downstream[2], "downstream_expected_use": downstream[3],
        "expected_result_schema": result_schema, "expected_result_version": result_version, "expected_outcome": outcome,
        "handoff_plan_id": plan_id, "runtime_root_sha256": _runtime_binding(runtime_root),
        "operator_tab_id": tab, "operation_revision": revision,
    }
    material["handoff_binding_sha256"] = digest_payload(material)
    root = _handoff_root(runtime_root, consumer, use)
    token = _authorization(root, "consumer-use-handoff-plan", material)
    atomic_json(root / "previews" / f"{plan_id}.json", {"schema": PLAN_SCHEMA, **material, "preview_only": True, "content_free": True})
    return _public({
        **dict(zip(("consumer_id", "consumer_schema", "consumer_version", "expected_use"), consumer)),
        **dict(zip(("use_id", "use_schema", "use_version", "declared_use"), use)),
        "selection_purpose": purpose, **dict(zip(("downstream_consumer_id", "downstream_consumer_schema", "downstream_consumer_version", "downstream_expected_use"), downstream)),
        "expected_result_schema": result_schema, "expected_result_version": result_version, "expected_outcome": outcome,
        "handoff_plan_id": plan_id, "ok": True, "status": "consumer_use_handoff_plan_preview_ready",
        "authorization_token": token, "literal_confirmation_required": PLAN_CONFIRMATION,
    })


def create_consumer_use_handoff_plan(
    token: str, *, confirm: str,
    consumer_id: str, consumer_schema: str, consumer_version: str, expected_use: str,
    selection_purpose: str, use_id: str, use_schema: str, use_version: str, declared_use: str,
    downstream_consumer_id: str, downstream_consumer_schema: str, downstream_consumer_version: str, downstream_expected_use: str,
    expected_result_schema: str, expected_result_version: str, expected_outcome: str,
    operator_tab_id: str, operation_revision: int, interrupt_after: str = "", runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    consumer, use = _identities((consumer_id, consumer_schema, consumer_version, expected_use), (use_id, use_schema, use_version, declared_use))
    downstream = _identity((downstream_consumer_id, downstream_consumer_schema, downstream_consumer_version, downstream_expected_use))
    purpose, result_schema, result_version, outcome = str(selection_purpose or "").strip(), str(expected_result_schema or "").strip(), str(expected_result_version or "").strip(), str(expected_outcome or "").strip()
    tab, revision = str(operator_tab_id or "").strip(), int(operation_revision)
    root = _handoff_root(runtime_root, consumer, use)
    auth = _load_authorization(root, "consumer-use-handoff-plan", token)
    if auth.get("reused"):
        return _public({"status": "authorization_reused", "findings": [{"kind": "authorization_reused"}]})
    current, findings = _current_use_material(runtime_root, consumer, purpose, use)
    material = dict(auth.get("material") or {})
    expected = {
        "consumer_use": current,
        "downstream_consumer_id": downstream[0], "downstream_consumer_schema": downstream[1],
        "downstream_consumer_version": downstream[2], "downstream_expected_use": downstream[3],
        "expected_result_schema": result_schema, "expected_result_version": result_version, "expected_outcome": outcome,
        "handoff_plan_id": material.get("handoff_plan_id"), "runtime_root_sha256": _runtime_binding(runtime_root),
        "operator_tab_id": tab, "operation_revision": revision,
    }
    expected["handoff_binding_sha256"] = digest_payload(expected)
    if confirm != PLAN_CONFIRMATION or not auth or findings or material != expected:
        return _public({"status": "consumer_use_handoff_plan_binding_rejected", "findings": findings or [{"kind": "consumer_use_handoff_plan_binding_rejected"}]})
    plan_id = str(material["handoff_plan_id"])
    operation_id = "consumer-use-handoff-operation-" + digest_payload({"authorization": auth.get("binding_sha256"), "plan_id": plan_id})[:24]
    operation_path = root / "operations" / f"{operation_id}.json"
    try:
        with metadata_mutation_lock(root / "active_plan.json"):
            operation = read_json(operation_path)
            recovery = bool(operation)
            if operation and str(operation.get("operation_sha256") or "") != _record_digest(operation, "operation_sha256"):
                return _public({"status": "consumer_use_handoff_operation_invalid", "findings": [{"kind": "consumer_use_handoff_operation_invalid"}]})
            if not operation:
                plan = {
                    "schema": PLAN_SCHEMA, **material, "handoff_operation_id": operation_id,
                    "created_at": utc_now(), "grants_authority": False, "executes_consumer": False,
                    "content_free": True,
                }
                plan["handoff_plan_sha256"] = _record_digest(plan, "handoff_plan_sha256")
                operation = _operation(operation_path, {
                    "schema": PLAN_OPERATION_SCHEMA, "handoff_operation_id": operation_id,
                    "status": "prepared", "plan": plan, "authorization_binding_sha256": auth.get("binding_sha256"),
                    "started_at": utc_now(), "updated_at": utc_now(), "content_free": True,
                })
            plan = dict(operation.get("plan") or {})
            if interrupt_after == "prepared" and operation.get("status") == "prepared":
                return _public({"status": "consumer_use_handoff_plan_interrupted", "handoff_operation_status": "prepared", "findings": [{"kind": "consumer_use_handoff_interrupted_after_prepared"}]})
            plan_path = root / "plans" / f"{plan_id}.json"
            existing = read_json(plan_path)
            if existing and existing != plan:
                return _public({"status": "consumer_use_handoff_plan_contradiction", "findings": [{"kind": "consumer_use_handoff_plan_contradiction"}]})
            if not existing:
                atomic_json(plan_path, plan)
            operation.update({"status": "plan_written", "updated_at": utc_now()})
            operation = _operation(operation_path, operation)
            if interrupt_after == "plan_written":
                return _public({"status": "consumer_use_handoff_plan_interrupted", "handoff_plan_id": plan_id, "handoff_operation_status": "plan_written", "findings": [{"kind": "consumer_use_handoff_interrupted_after_plan"}]})
            pointer = {"schema": PLAN_SCHEMA, "handoff_plan_id": plan_id, "handoff_plan_sha256": plan["handoff_plan_sha256"], "preflight_receipt_sha256": current["preflight_receipt_sha256"], "content_free": True}
            existing_pointer = read_json(root / "active_plan.json")
            if existing_pointer and existing_pointer != pointer:
                return _public({"status": "consumer_use_handoff_active_plan_contradiction", "findings": [{"kind": "consumer_use_handoff_active_plan_contradiction"}]})
            if not existing_pointer:
                atomic_json(root / "active_plan.json", pointer)
            operation.update({"status": "completed", "completed_at": utc_now(), "updated_at": utc_now()})
            _operation(operation_path, operation)
            used = root / "authorizations" / "used" / f"{digest_payload({'token': token})}.json"
            atomic_json(used, {"schema": "eidolon-used-consumer-use-handoff-token-v1", "category": "consumer-use-handoff-plan", "record_id": plan_id, "used_at": utc_now(), "content_free": True})
    except MetadataMutationBusy:
        return _public({"status": "consumer_use_handoff_plan_busy", "findings": [{"kind": "consumer_use_handoff_plan_busy"}]})
    return _public({**plan, "ok": True, "status": "consumer_use_handoff_plan_created", "handoff_plan_present": True, "handoff_plan_stale": False, "handoff_operation_status": "completed", "handoff_recovery_performed": recovery})


def _result_declaration_findings(result: Mapping[str, Any], plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    required = ("result_id", "result_schema", "result_version", "result_status", "output_sha256", "handoff_plan_id", "handoff_plan_sha256", "downstream_consumer_id", "downstream_consumer_schema", "downstream_consumer_version", "downstream_expected_use")
    if any(not str(result.get(field) or "").strip() for field in required):
        findings.append({"kind": "exact_downstream_result_declaration_required"})
    if str(result.get("result_status") or "") not in RESULT_STATUSES:
        findings.append({"kind": "unsupported_downstream_result_status"})
    expected = {
        "result_schema": plan.get("expected_result_schema"), "result_version": plan.get("expected_result_version"),
        "handoff_plan_id": plan.get("handoff_plan_id"), "handoff_plan_sha256": plan.get("handoff_plan_sha256"),
        "downstream_consumer_id": plan.get("downstream_consumer_id"), "downstream_consumer_schema": plan.get("downstream_consumer_schema"),
        "downstream_consumer_version": plan.get("downstream_consumer_version"), "downstream_expected_use": plan.get("downstream_expected_use"),
    }
    for field, value in expected.items():
        if str(result.get(field) or "") != str(value or ""):
            findings.append({"kind": f"downstream_result_{field}_mismatch"})
    if any(bool(result.get(flag)) for flag in AUTHORITY_FLAGS):
        findings.append({"kind": "downstream_result_authority_overclaim"})
    if result.get("content_free") is not True:
        findings.append({"kind": "downstream_result_must_be_content_free"})
    forbidden = {"content", "output", "path", "file_path", "evidence", "payload"}
    if any(key in result for key in forbidden):
        findings.append({"kind": "downstream_result_private_content_rejected"})
    return findings


def _active_result(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    pointer = read_json(root / "active_result_validation.json")
    result_id = str(pointer.get("result_validation_id") or "")
    receipt = read_json(root / "result_validations" / f"{result_id}.json") if result_id else {}
    return pointer, receipt


def downstream_consumer_result_validation_status(
    consumer_id: str, consumer_schema: str, consumer_version: str, expected_use: str,
    selection_purpose: str, use_id: str, use_schema: str, use_version: str, declared_use: str,
    downstream_consumer_id: str, downstream_consumer_schema: str, downstream_consumer_version: str, downstream_expected_use: str,
    expected_result_schema: str, expected_result_version: str, expected_outcome: str,
    *, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    consumer, use = _identities((consumer_id, consumer_schema, consumer_version, expected_use), (use_id, use_schema, use_version, declared_use))
    plan_status = consumer_use_handoff_plan_status(*consumer, selection_purpose, *use, downstream_consumer_id, downstream_consumer_schema, downstream_consumer_version, downstream_expected_use, expected_result_schema, expected_result_version, expected_outcome, runtime_root=runtime_root)
    root, _, plan = _active_plan(runtime_root, consumer, use)
    pointer, receipt = _active_result(root)
    findings: list[dict[str, Any]] = []
    if not plan_status.get("ok"):
        findings.append({"kind": "current_consumer_use_handoff_plan_required"})
    if not pointer or not receipt:
        findings.append({"kind": "downstream_result_validation_not_created"})
    elif str(receipt.get("result_validation_sha256") or "") != _record_digest(receipt, "result_validation_sha256"):
        findings.append({"kind": "downstream_result_validation_invalid"})
    else:
        if str(receipt.get("handoff_plan_sha256") or "") != str(plan.get("handoff_plan_sha256") or ""):
            findings.append({"kind": "downstream_result_validation_plan_drift"})
        if str(pointer.get("result_validation_sha256") or "") != str(receipt.get("result_validation_sha256") or ""):
            findings.append({"kind": "downstream_result_validation_pointer_drift"})
        operation_id = str(receipt.get("result_operation_id") or "")
        operation = read_json(root / "result_operations" / f"{operation_id}.json") if operation_id else {}
        if not operation or str(operation.get("operation_sha256") or "") != _record_digest(operation, "operation_sha256") or operation.get("status") != "completed":
            findings.append({"kind": "downstream_result_validation_operation_incomplete"})
    return _public({
        **receipt, "ok": not findings,
        "status": "downstream_consumer_result_validation_current" if not findings else "downstream_consumer_result_validation_stale",
        "result_validation_present": bool(receipt), "result_validation_stale": bool(findings),
        "result_operation_status": "completed" if receipt and not findings else "attention_required", "findings": findings,
    })


def preview_downstream_consumer_result_validation(
    consumer_id: str, consumer_schema: str, consumer_version: str, expected_use: str,
    selection_purpose: str, use_id: str, use_schema: str, use_version: str, declared_use: str,
    downstream_consumer_id: str, downstream_consumer_schema: str, downstream_consumer_version: str, downstream_expected_use: str,
    expected_result_schema: str, expected_result_version: str, expected_outcome: str,
    result: Mapping[str, Any], *, operator_tab_id: str, operation_revision: int, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    consumer, use = _identities((consumer_id, consumer_schema, consumer_version, expected_use), (use_id, use_schema, use_version, declared_use))
    root, _, plan = _active_plan(runtime_root, consumer, use)
    plan_status = consumer_use_handoff_plan_status(*consumer, selection_purpose, *use, downstream_consumer_id, downstream_consumer_schema, downstream_consumer_version, downstream_expected_use, expected_result_schema, expected_result_version, expected_outcome, runtime_root=runtime_root)
    tab, revision = str(operator_tab_id or "").strip(), int(operation_revision)
    findings = _result_declaration_findings(result, plan)
    if not plan_status.get("ok"):
        findings.append({"kind": "current_consumer_use_handoff_plan_required"})
    if not tab or revision <= 0:
        findings.append({"kind": "exact_operator_tab_and_revision_required"})
    existing_pointer, _ = _active_result(root)
    if existing_pointer:
        findings.append({"kind": "downstream_result_validation_already_created"})
    if findings:
        return _public({"status": "downstream_consumer_result_validation_rejected", "findings": findings})
    validation_id = "downstream-result-validation-" + secrets.token_hex(12)
    declaration = {key: result.get(key) for key in sorted(result)}
    material = {
        "handoff_plan_id": plan["handoff_plan_id"], "handoff_plan_sha256": plan["handoff_plan_sha256"],
        "result_validation_id": validation_id, "result": declaration,
        "runtime_root_sha256": _runtime_binding(runtime_root), "operator_tab_id": tab, "operation_revision": revision,
    }
    material["result_binding_sha256"] = digest_payload(material)
    token = _authorization(root, "downstream-result-validation", material)
    atomic_json(root / "result_previews" / f"{validation_id}.json", {"schema": RESULT_SCHEMA, **material, "preview_only": True, "content_free": True})
    return _public({
        "ok": True, "status": "downstream_consumer_result_validation_preview_ready",
        "handoff_plan_id": plan["handoff_plan_id"], "handoff_plan_sha256": plan["handoff_plan_sha256"],
        "result_id": str(result.get("result_id") or ""), "result_status": str(result.get("result_status") or ""),
        "result_validation_id": validation_id, "authorization_token": token, "literal_confirmation_required": RESULT_CONFIRMATION,
    })


def create_downstream_consumer_result_validation_receipt(
    token: str, *, confirm: str,
    consumer_id: str, consumer_schema: str, consumer_version: str, expected_use: str,
    use_id: str, use_schema: str, use_version: str, declared_use: str,
    result: Mapping[str, Any], operator_tab_id: str, operation_revision: int,
    interrupt_after: str = "", runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    consumer, use = _identities((consumer_id, consumer_schema, consumer_version, expected_use), (use_id, use_schema, use_version, declared_use))
    root, _, plan = _active_plan(runtime_root, consumer, use)
    auth = _load_authorization(root, "downstream-result-validation", token)
    if auth.get("reused"):
        return _public({"status": "authorization_reused", "findings": [{"kind": "authorization_reused"}]})
    declaration = {key: result.get(key) for key in sorted(result)}
    material = dict(auth.get("material") or {})
    expected = {
        "handoff_plan_id": plan.get("handoff_plan_id"), "handoff_plan_sha256": plan.get("handoff_plan_sha256"),
        "result_validation_id": material.get("result_validation_id"), "result": declaration,
        "runtime_root_sha256": _runtime_binding(runtime_root), "operator_tab_id": str(operator_tab_id or "").strip(),
        "operation_revision": int(operation_revision),
    }
    expected["result_binding_sha256"] = digest_payload(expected)
    findings = _result_declaration_findings(result, plan)
    if confirm != RESULT_CONFIRMATION or not auth or findings or material != expected:
        return _public({"status": "downstream_consumer_result_validation_binding_rejected", "findings": findings or [{"kind": "downstream_consumer_result_validation_binding_rejected"}]})
    validation_id = str(material["result_validation_id"])
    operation_id = "downstream-result-operation-" + digest_payload({"authorization": auth.get("binding_sha256"), "validation": validation_id})[:24]
    operation_path = root / "result_operations" / f"{operation_id}.json"
    try:
        with metadata_mutation_lock(root / "active_result_validation.json"):
            operation = read_json(operation_path)
            recovery = bool(operation)
            if operation and str(operation.get("operation_sha256") or "") != _record_digest(operation, "operation_sha256"):
                return _public({"status": "downstream_result_operation_invalid", "findings": [{"kind": "downstream_result_operation_invalid"}]})
            if not operation:
                receipt = {
                    "schema": RESULT_SCHEMA, "result_validation_id": validation_id,
                    "handoff_plan_id": plan["handoff_plan_id"], "handoff_plan_sha256": plan["handoff_plan_sha256"],
                    "result_id": declaration["result_id"], "result_schema": declaration["result_schema"],
                    "result_version": declaration["result_version"], "result_status": declaration["result_status"],
                    "output_sha256": declaration["output_sha256"],
                    "downstream_consumer_id": declaration["downstream_consumer_id"],
                    "downstream_consumer_schema": declaration["downstream_consumer_schema"],
                    "downstream_consumer_version": declaration["downstream_consumer_version"],
                    "downstream_expected_use": declaration["downstream_expected_use"],
                    "result_declaration_sha256": digest_payload(declaration), "result_operation_id": operation_id,
                    "created_at": utc_now(), "grants_authority": False, "future_use_authorized": False,
                    "content_free": True,
                }
                receipt["result_validation_sha256"] = _record_digest(receipt, "result_validation_sha256")
                operation = _operation(operation_path, {
                    "schema": RESULT_OPERATION_SCHEMA, "result_operation_id": operation_id,
                    "status": "prepared", "receipt": receipt, "authorization_binding_sha256": auth.get("binding_sha256"),
                    "started_at": utc_now(), "updated_at": utc_now(), "content_free": True,
                })
            receipt = dict(operation.get("receipt") or {})
            if interrupt_after == "prepared" and operation.get("status") == "prepared":
                return _public({"status": "downstream_result_validation_interrupted", "result_operation_status": "prepared", "findings": [{"kind": "downstream_result_interrupted_after_prepared"}]})
            receipt_path = root / "result_validations" / f"{validation_id}.json"
            existing = read_json(receipt_path)
            if existing and existing != receipt:
                return _public({"status": "downstream_result_validation_contradiction", "findings": [{"kind": "downstream_result_validation_contradiction"}]})
            if not existing:
                atomic_json(receipt_path, receipt)
            operation.update({"status": "receipt_written", "updated_at": utc_now()})
            operation = _operation(operation_path, operation)
            if interrupt_after == "receipt_written":
                return _public({"status": "downstream_result_validation_interrupted", "result_validation_id": validation_id, "result_operation_status": "receipt_written", "findings": [{"kind": "downstream_result_interrupted_after_receipt"}]})
            pointer = {"schema": RESULT_SCHEMA, "result_validation_id": validation_id, "result_validation_sha256": receipt["result_validation_sha256"], "handoff_plan_sha256": plan["handoff_plan_sha256"], "content_free": True}
            existing_pointer = read_json(root / "active_result_validation.json")
            if existing_pointer and existing_pointer != pointer:
                return _public({"status": "downstream_result_active_pointer_contradiction", "findings": [{"kind": "downstream_result_active_pointer_contradiction"}]})
            if not existing_pointer:
                atomic_json(root / "active_result_validation.json", pointer)
            operation.update({"status": "completed", "completed_at": utc_now(), "updated_at": utc_now()})
            _operation(operation_path, operation)
            used = root / "authorizations" / "used" / f"{digest_payload({'token': token})}.json"
            atomic_json(used, {"schema": "eidolon-used-downstream-result-validation-token-v1", "category": "downstream-result-validation", "record_id": validation_id, "used_at": utc_now(), "content_free": True})
    except MetadataMutationBusy:
        return _public({"status": "downstream_result_validation_busy", "findings": [{"kind": "downstream_result_validation_busy"}]})
    return _public({**receipt, "ok": True, "status": "downstream_consumer_result_validation_created", "result_validation_present": True, "result_validation_stale": False, "result_operation_status": "completed", "result_recovery_performed": recovery})


def release_authority_consumer_use_lifecycle_status(
    consumer_id: str = "", consumer_schema: str = "", consumer_version: str = "", expected_use: str = "",
    selection_purpose: str = "", use_id: str = "", use_schema: str = "", use_version: str = "", declared_use: str = "",
    downstream_consumer_id: str = "", downstream_consumer_schema: str = "", downstream_consumer_version: str = "", downstream_expected_use: str = "",
    expected_result_schema: str = "", expected_result_version: str = "", expected_outcome: str = "",
    *, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    consumer, use = _identities((consumer_id, consumer_schema, consumer_version, expected_use), (use_id, use_schema, use_version, declared_use))
    selected = any(consumer) or any(use) or bool(str(selection_purpose or "").strip())
    if not selected:
        return _public({"ok": True, "status": "consumer_use_lifecycle_not_selected"})
    daily = release_authority_consumer_daily_use_binding_status(*consumer, selection_purpose, *use, runtime_root=runtime_root)
    downstream_selected = any((downstream_consumer_id, downstream_consumer_schema, downstream_consumer_version, downstream_expected_use, expected_result_schema, expected_result_version, expected_outcome))
    plan = _public({"ok": True, "status": "consumer_use_handoff_not_selected"})
    result = _public({"ok": True, "status": "downstream_result_not_selected"})
    if downstream_selected:
        plan = consumer_use_handoff_plan_status(*consumer, selection_purpose, *use, downstream_consumer_id, downstream_consumer_schema, downstream_consumer_version, downstream_expected_use, expected_result_schema, expected_result_version, expected_outcome, runtime_root=runtime_root)
        if plan.get("handoff_plan_present"):
            result = downstream_consumer_result_validation_status(*consumer, selection_purpose, *use, downstream_consumer_id, downstream_consumer_schema, downstream_consumer_version, downstream_expected_use, expected_result_schema, expected_result_version, expected_outcome, runtime_root=runtime_root)
    findings: list[dict[str, Any]] = []
    if not daily.get("ok"):
        findings.append({"kind": "consumer_daily_use_binding_attention_required"})
    if downstream_selected and not plan.get("ok"):
        findings.append({"kind": "consumer_use_handoff_plan_attention_required"})
    if downstream_selected and plan.get("ok") and result.get("result_validation_present") and not result.get("ok"):
        findings.append({"kind": "downstream_result_validation_attention_required"})
    return _public({
        **dict(zip(("consumer_id", "consumer_schema", "consumer_version", "expected_use"), consumer)),
        **dict(zip(("use_id", "use_schema", "use_version", "declared_use"), use)),
        "selection_purpose": str(selection_purpose or "").strip(),
        "downstream_consumer_id": downstream_consumer_id, "downstream_consumer_schema": downstream_consumer_schema,
        "downstream_consumer_version": downstream_consumer_version, "downstream_expected_use": downstream_expected_use,
        "expected_result_schema": expected_result_schema, "expected_result_version": expected_result_version, "expected_outcome": expected_outcome,
        "handoff_plan_id": plan.get("handoff_plan_id"), "handoff_plan_sha256": plan.get("handoff_plan_sha256"),
        "handoff_plan_present": plan.get("handoff_plan_present"), "handoff_plan_stale": plan.get("handoff_plan_stale"),
        "result_id": result.get("result_id"), "result_status": result.get("result_status"),
        "result_validation_id": result.get("result_validation_id"), "result_validation_sha256": result.get("result_validation_sha256"),
        "result_validation_present": result.get("result_validation_present"), "result_validation_stale": result.get("result_validation_stale"),
        "ok": not findings,
        "status": "release_authority_consumer_use_lifecycle_coherent" if not findings else "release_authority_consumer_use_lifecycle_attention_required",
        "findings": findings,
    })
