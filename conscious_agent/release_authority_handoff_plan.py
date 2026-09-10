from __future__ import annotations

"""Immutable release-authority handoff plans and exact acknowledgments.

Plans and acknowledgments are external, content-free authority summaries. They
never install, promote, certify, migrate policy, contact providers, run native
checks, or change models. Acknowledgment is exact, expiring, single-use, and
transactional so an interrupted write can be recovered without replay.
"""

from collections import Counter
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import secrets
from typing import Any, Iterable, Mapping

try:
    from metadata_mutation_coordination import MetadataMutationBusy, metadata_mutation_lock
    from release_candidate_identity import atomic_json, digest_payload, read_json, runtime_data_root, utc_now
    from release_authority_readiness import release_authority_readiness_status
    from release_authority_readiness_recovery import _active_private as active_readiness_private
except ImportError:
    from metadata_mutation_coordination import MetadataMutationBusy, metadata_mutation_lock
    from release_candidate_identity import atomic_json, digest_payload, read_json, runtime_data_root, utc_now
    from release_authority_readiness import release_authority_readiness_status
    from release_authority_readiness_recovery import _active_private as active_readiness_private

RELEASE_AUTHORITY_HANDOFF_PLAN_CONTRACT_VERSION = "2"
HANDOFF_PLAN_DIRECTORY = "release_authority_handoff_plans"
HANDOFF_PLAN_SCHEMA = "eidolon-release-authority-handoff-plan-v1"
HANDOFF_ACK_SCHEMA = "eidolon-release-authority-handoff-acknowledgment-v2"
HANDOFF_ACK_OPERATION_SCHEMA = "eidolon-release-authority-handoff-acknowledgment-operation-v1"
HANDOFF_ACK_CONFIRMATION = "ACKNOWLEDGE EXACT RELEASE AUTHORITY HANDOFF PLAN"
DEFAULT_ACK_AUTHORIZATION_TTL_SECONDS = 900
DEFAULT_ACK_RECEIPT_TTL_SECONDS = 86400

BINDING_FIELDS = (
    "runtime_root_identity_sha256",
    "candidate_id",
    "packaged_version",
    "source_manifest_sha256",
    "archive_manifest_sha256",
    "archive_sha256",
    "installation_transaction_id",
    "installation_transaction_identity_sha256",
    "installed_receipt_sha256",
    "target_project_id",
    "target_inventory_sha256",
    "promotion_transaction_id",
    "promotion_transaction_identity_sha256",
    "promotion_receipt_sha256",
    "promotion_state_sha256",
    "certification_transaction_id",
    "certification_receipt_sha256",
    "certification_state_sha256",
    "certification_generation",
    "history_sha256",
    "history_generation",
    "authority_generation",
    "authority_state_sha256",
    "policy_id",
    "policy_sha256",
    "policy_generation",
    "migration_preview_id",
    "migration_preview_sha256",
    "readiness_binding_sha256",
)

ACK_PLAN_BINDING_FIELDS = (
    "runtime_root_identity_sha256",
    "plan_id",
    "plan_binding_sha256",
    "record_sha256",
    "readiness_preview_id",
    "readiness_generation",
    "readiness_binding_sha256",
    "candidate_id",
    "packaged_version",
    "source_manifest_sha256",
    "archive_manifest_sha256",
    "archive_sha256",
    "installation_transaction_id",
    "installation_transaction_identity_sha256",
    "installed_receipt_sha256",
    "target_project_id",
    "target_inventory_sha256",
    "promotion_transaction_id",
    "promotion_transaction_identity_sha256",
    "promotion_receipt_sha256",
    "promotion_state_sha256",
    "certification_transaction_id",
    "certification_receipt_sha256",
    "certification_state_sha256",
    "certification_generation",
    "history_sha256",
    "history_generation",
    "authority_generation",
    "authority_state_sha256",
    "policy_id",
    "policy_sha256",
    "policy_generation",
    "migration_preview_id",
    "migration_preview_sha256",
    "scope_statuses_sha256",
    "unresolved_blockers_sha256",
)


def handoff_plan_directory(runtime_root: str | Path | None = None) -> Path:
    return runtime_data_root(runtime_root) / HANDOFF_PLAN_DIRECTORY


def _counts(rows: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    found: Counter[str] = Counter()
    for row in rows or []:
        found[str(row.get("kind") or "unknown")] += max(1, int(row.get("count") or 1))
    return [{"kind": key, "count": found[key]} for key in sorted(found)]


def _record_digest(record: Mapping[str, Any], field: str = "record_sha256") -> str:
    return digest_payload({key: value for key, value in record.items() if key != field})


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


def _parse_time(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _expires_after(seconds: int) -> str:
    bounded = max(1, int(seconds))
    return (datetime.now(timezone.utc) + timedelta(seconds=bounded)).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _is_expired(value: str) -> bool:
    parsed = _parse_time(value)
    return parsed is None or parsed <= datetime.now(timezone.utc)


def _tab_digest(operator_tab_id: str) -> str:
    return digest_payload({"operator_tab_id": str(operator_tab_id or "")})


def _plan_binding(record: Mapping[str, Any]) -> str:
    return digest_payload({
        "schema": HANDOFF_PLAN_SCHEMA,
        "plan_id": str(record.get("plan_id") or ""),
        "readiness_preview_id": str(record.get("readiness_preview_id") or ""),
        "readiness_generation": int(record.get("readiness_generation") or 0),
        **{field: record.get(field) for field in BINDING_FIELDS},
        "scope_statuses_sha256": str(record.get("scope_statuses_sha256") or ""),
        "unresolved_blockers_sha256": str(record.get("unresolved_blockers_sha256") or ""),
    })


def _public(record: Mapping[str, Any] | None) -> dict[str, Any]:
    row = dict(record or {})
    findings = _counts(row.get("findings") if isinstance(row.get("findings"), list) else [])
    blockers = _counts(row.get("unresolved_blockers") if isinstance(row.get("unresolved_blockers"), list) else [])
    scope_rows: list[dict[str, Any]] = []
    for item in row.get("scope_statuses") or []:
        if isinstance(item, Mapping):
            scope_rows.append({
                "scope": str(item.get("scope") or ""),
                "certified": bool(item.get("certified")),
                "evidence_expired": bool(item.get("evidence_expired")),
                "evidence_stale": bool(item.get("evidence_stale")),
                "migration_classification": str(item.get("migration_classification") or "not_assessed"),
                "authority_inferred": False,
                "content_free": True,
            })
    return {
        "ok": bool(row.get("ok")) and not findings,
        "status": str(row.get("status") or "release_authority_handoff_not_planned"),
        "contract_version": RELEASE_AUTHORITY_HANDOFF_PLAN_CONTRACT_VERSION,
        "plan_id": str(row.get("plan_id") or ""),
        "plan_binding_sha256": str(row.get("plan_binding_sha256") or ""),
        "record_sha256": str(row.get("record_sha256") or ""),
        "readiness_preview_id": str(row.get("readiness_preview_id") or ""),
        "readiness_generation": int(row.get("readiness_generation") or 0),
        "readiness_binding_sha256": str(row.get("readiness_binding_sha256") or ""),
        "runtime_root_identity_sha256": str(row.get("runtime_root_identity_sha256") or ""),
        "candidate_id": str(row.get("candidate_id") or ""),
        "packaged_version": str(row.get("packaged_version") or ""),
        "source_manifest_sha256": str(row.get("source_manifest_sha256") or ""),
        "archive_manifest_sha256": str(row.get("archive_manifest_sha256") or ""),
        "archive_sha256": str(row.get("archive_sha256") or ""),
        "installation_transaction_id": str(row.get("installation_transaction_id") or ""),
        "installation_transaction_identity_sha256": str(row.get("installation_transaction_identity_sha256") or ""),
        "installed_receipt_sha256": str(row.get("installed_receipt_sha256") or ""),
        "target_project_id": str(row.get("target_project_id") or ""),
        "target_inventory_sha256": str(row.get("target_inventory_sha256") or ""),
        "promotion_transaction_id": str(row.get("promotion_transaction_id") or ""),
        "promotion_transaction_identity_sha256": str(row.get("promotion_transaction_identity_sha256") or ""),
        "promotion_receipt_sha256": str(row.get("promotion_receipt_sha256") or ""),
        "promotion_state_sha256": str(row.get("promotion_state_sha256") or ""),
        "certification_transaction_id": str(row.get("certification_transaction_id") or ""),
        "certification_receipt_sha256": str(row.get("certification_receipt_sha256") or ""),
        "certification_state_sha256": str(row.get("certification_state_sha256") or ""),
        "certification_generation": int(row.get("certification_generation") or 0),
        "history_sha256": str(row.get("history_sha256") or ""),
        "history_generation": int(row.get("history_generation") or 0),
        "authority_generation": int(row.get("authority_generation") or 0),
        "authority_state_sha256": str(row.get("authority_state_sha256") or ""),
        "policy_id": str(row.get("policy_id") or ""),
        "policy_sha256": str(row.get("policy_sha256") or ""),
        "policy_generation": int(row.get("policy_generation") or 0),
        "migration_preview_id": str(row.get("migration_preview_id") or ""),
        "migration_preview_sha256": str(row.get("migration_preview_sha256") or ""),
        "scope_statuses_sha256": str(row.get("scope_statuses_sha256") or ""),
        "unresolved_blockers_sha256": str(row.get("unresolved_blockers_sha256") or ""),
        "scope_statuses": scope_rows,
        "unresolved_blockers": blockers,
        "unresolved_blocker_count": sum(int(item["count"]) for item in blockers),
        "findings": findings,
        "finding_count": sum(int(item["count"]) for item in findings),
        "authorization_token": str(row.get("authorization_token") or ""),
        "authorization_expires_at": str(row.get("authorization_expires_at") or ""),
        "literal_confirmation_required": str(row.get("literal_confirmation_required") or ""),
        "operator_tab_id_sha256": str(row.get("operator_tab_id_sha256") or ""),
        "operation_revision": int(row.get("operation_revision") or 0),
        "acknowledgment_present": bool(row.get("acknowledgment_present")),
        "acknowledgment_id": str(row.get("acknowledgment_id") or ""),
        "acknowledgment_receipt_sha256": str(row.get("acknowledgment_receipt_sha256") or row.get("receipt_sha256") or ""),
        "acknowledgment_expires_at": str(row.get("acknowledgment_expires_at") or row.get("expires_at") or ""),
        "acknowledgment_expired": bool(row.get("acknowledgment_expired")),
        "acknowledgment_operation_id": str(row.get("acknowledgment_operation_id") or ""),
        "acknowledgment_operation_status": str(row.get("acknowledgment_operation_status") or ""),
        "acknowledgment_recovery_performed": bool(row.get("acknowledgment_recovery_performed")),
        "replacement_of_acknowledgment_id": str(row.get("replacement_of_acknowledgment_id") or ""),
        "previous_coherent_plan_preserved": bool(row.get("previous_coherent_plan_preserved")),
        "previous_coherent_acknowledgment_preserved": bool(row.get("previous_coherent_acknowledgment_preserved")),
        "duplicate_execution_allowed": False,
        "read_only_plan": True,
        "acknowledgment_grants_authority": False,
        "installation_inferred": False,
        "promotion_inferred": False,
        "certification_inferred": False,
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


def _active_plan_private(runtime_root: str | Path | None) -> tuple[dict[str, Any], dict[str, Any]]:
    directory = handoff_plan_directory(runtime_root)
    pointer = read_json(directory / "active_plan.json")
    plan_id = str(pointer.get("plan_id") or "")
    return pointer, read_json(directory / "plans" / f"{plan_id}.json") if plan_id else {}


def _active_ack_private(runtime_root: str | Path | None) -> dict[str, Any]:
    directory = handoff_plan_directory(runtime_root)
    pointer_state, pointer = _json_state(directory / "active_acknowledgment.json")
    ack_id = str(pointer.get("acknowledgment_id") or "")
    receipt_state, receipt = _json_state(directory / "acknowledgments" / f"{ack_id}.json") if ack_id else ("missing", {})
    op_state, operation = _json_state(directory / "active_ack_operation.json")
    return {
        "pointer_state": pointer_state,
        "pointer": pointer,
        "receipt_state": receipt_state,
        "receipt": receipt,
        "operation_state": op_state,
        "operation": operation,
    }


def _active_ack_operation_private(runtime_root: str | Path | None) -> dict[str, Any]:
    return dict(_active_ack_private(runtime_root).get("operation") or {})


def create_release_authority_handoff_plan(*, runtime_root: str | Path | None = None, interrupt_after: str = "") -> dict[str, Any]:
    readiness = release_authority_readiness_status(runtime_root=runtime_root)
    active = active_readiness_private(runtime_root)
    findings: list[dict[str, Any]] = []
    if not readiness.get("ok") or not active.get("ok"):
        findings.append({"kind": "coherent_release_authority_readiness_required"})
    if str(active.get("record", {}).get("readiness_binding_sha256") or "") != str(readiness.get("readiness_binding_sha256") or ""):
        findings.append({"kind": "active_readiness_binding_mismatch"})
    required = (
        "candidate_id", "source_manifest_sha256", "archive_manifest_sha256", "archive_sha256",
        "installation_transaction_id", "installed_receipt_sha256", "target_project_id", "target_inventory_sha256",
        "promotion_transaction_id", "promotion_receipt_sha256", "certification_receipt_sha256",
        "history_sha256", "policy_sha256", "migration_preview_sha256", "runtime_root_identity_sha256",
    )
    for field in required:
        if not readiness.get(field):
            findings.append({"kind": f"handoff_plan_{field}_missing"})
    scope_rows = list(readiness.get("scope_statuses") or [])
    blockers = list(readiness.get("findings") or [])
    material = {field: readiness.get(field) for field in BINDING_FIELDS}
    material.update({
        "readiness_preview_id": str(readiness.get("preview_id") or ""),
        "readiness_generation": int(readiness.get("generation") or 0),
        "scope_statuses_sha256": digest_payload(scope_rows),
        "unresolved_blockers_sha256": digest_payload(blockers),
    })
    plan_id = f"release-authority-handoff-{digest_payload(material)[:24]}"
    record = {
        "schema": HANDOFF_PLAN_SCHEMA,
        "plan_id": plan_id,
        "created_at": utc_now(),
        "ok": not findings,
        "status": "release_authority_handoff_plan_bound" if not findings else "release_authority_handoff_plan_attention_required",
        **material,
        "scope_statuses": scope_rows,
        "unresolved_blockers": blockers,
        "findings": findings,
        "content_free": True,
    }
    record["plan_binding_sha256"] = _plan_binding(record)
    record["record_sha256"] = _record_digest(record)
    directory = handoff_plan_directory(runtime_root)
    atomic_json(directory / "plans" / f"{plan_id}.json", record)
    if findings:
        atomic_json(directory / "last_failed_plan.json", record)
        return _public({**record, "previous_coherent_plan_preserved": True})
    if interrupt_after in {"record_written", "before_activation"}:
        atomic_json(directory / "interrupted_plan.json", record)
        return _public({**record, "ok": False, "status": "release_authority_handoff_plan_interrupted", "findings": [{"kind": "handoff_plan_activation_interrupted"}], "previous_coherent_plan_preserved": True})
    atomic_json(directory / "active_plan.json", {
        "schema": HANDOFF_PLAN_SCHEMA,
        "plan_id": plan_id,
        "plan_binding_sha256": record["plan_binding_sha256"],
        "record_sha256": record["record_sha256"],
        "readiness_preview_id": record["readiness_preview_id"],
        "readiness_generation": record["readiness_generation"],
        "content_free": True,
    })
    return _public(record)


def release_authority_handoff_plan_status(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    pointer, record = _active_plan_private(runtime_root)
    if not pointer:
        return _public({"ok": True, "status": "release_authority_handoff_not_planned"})
    findings: list[dict[str, Any]] = []
    if not record:
        findings.append({"kind": "handoff_plan_record_missing"})
    else:
        if str(record.get("record_sha256") or "") != _record_digest(record):
            findings.append({"kind": "handoff_plan_record_digest_mismatch"})
        if str(record.get("plan_binding_sha256") or "") != _plan_binding(record):
            findings.append({"kind": "handoff_plan_binding_mismatch"})
        for field in ("plan_id", "plan_binding_sha256", "record_sha256", "readiness_preview_id", "readiness_generation"):
            if str(pointer.get(field) or "") != str(record.get(field) or ""):
                findings.append({"kind": f"handoff_plan_pointer_{field}_mismatch"})
    readiness = release_authority_readiness_status(runtime_root=runtime_root)
    if not readiness.get("ok"):
        findings.append({"kind": "release_authority_readiness_stale"})
    if record:
        for field in BINDING_FIELDS:
            if str(record.get(field) or "") != str(readiness.get(field) or ""):
                findings.append({"kind": f"handoff_plan_{field}_drift"})
        if str(record.get("readiness_preview_id") or "") != str(readiness.get("preview_id") or ""):
            findings.append({"kind": "handoff_plan_readiness_preview_changed"})
        if int(record.get("readiness_generation") or 0) != int(readiness.get("generation") or 0):
            findings.append({"kind": "handoff_plan_readiness_generation_changed"})
        if str(record.get("scope_statuses_sha256") or "") != digest_payload(readiness.get("scope_statuses") or []):
            findings.append({"kind": "handoff_plan_scope_state_drift"})
        if str(record.get("unresolved_blockers_sha256") or "") != digest_payload(readiness.get("findings") or []):
            findings.append({"kind": "handoff_plan_blockers_drift"})
    out = dict(record)
    out["findings"] = findings
    out["ok"] = not findings
    out["status"] = "release_authority_handoff_plan_current" if not findings else "release_authority_handoff_plan_stale"
    return _public(out)


def _authorization_token(auth: Mapping[str, Any]) -> str:
    return ".".join((str(auth.get("token_id") or ""), str(auth.get("binding_sha256") or ""), str(auth.get("nonce") or "")))


def preview_release_authority_handoff_acknowledgment(
    *,
    operator_tab_id: str = "operator-tab",
    operation_revision: int = 1,
    authorization_ttl_seconds: int = DEFAULT_ACK_AUTHORIZATION_TTL_SECONDS,
    acknowledgment_ttl_seconds: int = DEFAULT_ACK_RECEIPT_TTL_SECONDS,
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    plan = release_authority_handoff_plan_status(runtime_root=runtime_root)
    if not plan.get("ok") or not plan.get("plan_id"):
        return _public({"ok": False, "status": "current_release_authority_handoff_plan_required", "findings": plan.get("findings") or [{"kind": "current_release_authority_handoff_plan_required"}]})
    existing = release_authority_handoff_acknowledgment_status(runtime_root=runtime_root)
    if existing.get("acknowledgment_present") and existing.get("ok") and not existing.get("acknowledgment_expired"):
        return _public({**plan, "ok": False, "status": "release_authority_handoff_already_acknowledged", "findings": [{"kind": "release_authority_handoff_already_acknowledged"}]})
    tab = str(operator_tab_id or "").strip()
    revision = int(operation_revision or 0)
    if not tab or revision <= 0:
        return _public({**plan, "ok": False, "status": "exact_operator_tab_and_revision_required", "findings": [{"kind": "exact_operator_tab_and_revision_required"}]})
    token_id = f"release-authority-handoff-ack-{secrets.token_hex(8)}"
    nonce = secrets.token_hex(16)
    auth = {
        "schema": HANDOFF_ACK_SCHEMA,
        "token_id": token_id,
        "nonce": nonce,
        "created_at": utc_now(),
        "expires_at": _expires_after(authorization_ttl_seconds),
        "acknowledgment_ttl_seconds": max(1, int(acknowledgment_ttl_seconds)),
        "operator_tab_id_sha256": _tab_digest(tab),
        "operation_revision": revision,
        **{field: plan.get(field) for field in ACK_PLAN_BINDING_FIELDS},
        "action": "acknowledge_exact_release_authority_handoff_plan",
        "content_free": True,
    }
    auth["binding_sha256"] = _record_digest(auth, "binding_sha256")
    directory = handoff_plan_directory(runtime_root)
    atomic_json(directory / "authorizations" / f"{token_id}.json", auth)
    return _public({
        **plan,
        "status": "release_authority_handoff_acknowledgment_previewed",
        "authorization_token": _authorization_token(auth),
        "authorization_expires_at": auth["expires_at"],
        "operator_tab_id_sha256": auth["operator_tab_id_sha256"],
        "operation_revision": revision,
        "literal_confirmation_required": HANDOFF_ACK_CONFIRMATION,
    })


def _load_authorization(runtime_root: str | Path | None, token: str) -> dict[str, Any]:
    parts = token.split(".") if isinstance(token, str) else []
    if len(parts) != 3:
        return {}
    auth = read_json(handoff_plan_directory(runtime_root) / "authorizations" / f"{parts[0]}.json")
    if not auth:
        return {}
    expected = _record_digest(auth, "binding_sha256")
    if parts != [str(auth.get("token_id") or ""), str(auth.get("binding_sha256") or ""), str(auth.get("nonce") or "")]:
        return {}
    return auth if str(auth.get("binding_sha256") or "") == expected else {}


def _validate_authorization(
    auth: Mapping[str, Any],
    plan: Mapping[str, Any],
    *,
    operator_tab_id: str,
    operation_revision: int,
    allow_expired_authorization: bool = False,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if not allow_expired_authorization and _is_expired(str(auth.get("expires_at") or "")):
        findings.append({"kind": "handoff_authorization_expired"})
    if str(auth.get("operator_tab_id_sha256") or "") != _tab_digest(operator_tab_id):
        findings.append({"kind": "handoff_authorization_operator_tab_mismatch"})
    if int(auth.get("operation_revision") or 0) != int(operation_revision or 0):
        findings.append({"kind": "handoff_authorization_operation_revision_mismatch"})
    for field in ACK_PLAN_BINDING_FIELDS:
        if str(auth.get(field) or "") != str(plan.get(field) or ""):
            findings.append({"kind": f"handoff_authorization_{field}_mismatch"})
    return findings


def _operation_digest(record: Mapping[str, Any]) -> str:
    return _record_digest(record, "operation_sha256")


def _write_operation(path: Path, operation: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(operation)
    row["operation_sha256"] = _operation_digest(row)
    atomic_json(path, row)
    return row


def _used_token_path(runtime_root: str | Path | None, token: str) -> Path:
    return handoff_plan_directory(runtime_root) / "used_tokens" / f"{digest_payload({'token': token})}.json"


def _execute_acknowledgment(
    token: str,
    auth: Mapping[str, Any],
    plan: Mapping[str, Any],
    *,
    operator_tab_id: str,
    operation_revision: int,
    runtime_root: str | Path | None,
    interrupt_after: str = "",
    replacement_of_acknowledgment_id: str = "",
    allow_expired_authorization: bool = False,
    expected_operation_id: str = "",
) -> dict[str, Any]:
    directory = handoff_plan_directory(runtime_root)
    used_path = _used_token_path(runtime_root, token)
    op_id = expected_operation_id or f"release-authority-handoff-ack-operation-{digest_payload({'token': token, 'action': auth.get('action')})[:24]}"
    op_path = directory / "operations" / f"{op_id}.json"
    existing_op = read_json(op_path)
    recovery_performed = bool(existing_op)
    if existing_op:
        if str(existing_op.get("operation_sha256") or "") != _operation_digest(existing_op):
            return _public({**plan, "ok": False, "status": "release_authority_handoff_acknowledgment_contradictory", "findings": [{"kind": "handoff_acknowledgment_operation_digest_mismatch"}]})
        for field, expected in (
            ("authorization_binding_sha256", auth.get("binding_sha256")),
            ("operator_tab_id_sha256", _tab_digest(operator_tab_id)),
            ("operation_revision", int(operation_revision)),
            ("plan_binding_sha256", plan.get("plan_binding_sha256")),
        ):
            if str(existing_op.get(field) or "") != str(expected or ""):
                return _public({**plan, "ok": False, "status": "release_authority_handoff_acknowledgment_contradictory", "findings": [{"kind": f"handoff_acknowledgment_operation_{field}_mismatch"}]})
        if str(existing_op.get("status") or "") == "completed":
            return _public({**plan, "ok": False, "status": "authorization_reused", "acknowledgment_operation_id": op_id, "acknowledgment_operation_status": "completed", "findings": [{"kind": "authorization_reused"}]})
        operation = dict(existing_op)
        receipt = dict(operation.get("receipt") or {})
        if not receipt or str(receipt.get("receipt_sha256") or "") != _record_digest(receipt, "receipt_sha256"):
            return _public({**plan, "ok": False, "status": "release_authority_handoff_acknowledgment_contradictory", "findings": [{"kind": "handoff_acknowledgment_operation_receipt_invalid"}]})
    else:
        if used_path.is_file():
            return _public({**plan, "ok": False, "status": "authorization_reused", "findings": [{"kind": "authorization_reused"}]})
        ack_id = f"release-authority-handoff-ack-{digest_payload({'token': token, 'plan': plan.get('plan_binding_sha256')})[:24]}"
        acknowledged_at = utc_now()
        receipt = {
            "schema": HANDOFF_ACK_SCHEMA,
            "acknowledgment_id": ack_id,
            "acknowledged_at": acknowledged_at,
            "expires_at": _expires_after(int(auth.get("acknowledgment_ttl_seconds") or DEFAULT_ACK_RECEIPT_TTL_SECONDS)),
            "operator_tab_id_sha256": _tab_digest(operator_tab_id),
            "operation_revision": int(operation_revision),
            **{field: plan.get(field) for field in ACK_PLAN_BINDING_FIELDS},
            "replacement_of_acknowledgment_id": str(replacement_of_acknowledgment_id or ""),
            "grants_authority": False,
            "content_free": True,
        }
        receipt["receipt_sha256"] = _record_digest(receipt, "receipt_sha256")
        operation = {
            "schema": HANDOFF_ACK_OPERATION_SCHEMA,
            "acknowledgment_operation_id": op_id,
            "status": "prepared",
            "started_at": utc_now(),
            "updated_at": utc_now(),
            "authorization_token_sha256": digest_payload({"token": token}),
            "authorization_token_id": str(auth.get("token_id") or ""),
            "authorization_binding_sha256": str(auth.get("binding_sha256") or ""),
            "operator_tab_id_sha256": _tab_digest(operator_tab_id),
            "operation_revision": int(operation_revision),
            "plan_id": str(plan.get("plan_id") or ""),
            "plan_binding_sha256": str(plan.get("plan_binding_sha256") or ""),
            "replacement_of_acknowledgment_id": str(replacement_of_acknowledgment_id or ""),
            "receipt": receipt,
            "content_free": True,
        }
        operation = _write_operation(op_path, operation)
        atomic_json(directory / "active_ack_operation.json", {
            "schema": HANDOFF_ACK_OPERATION_SCHEMA,
            "acknowledgment_operation_id": op_id,
            "operation_sha256": operation["operation_sha256"],
            "status": operation["status"],
            "content_free": True,
        })
    if interrupt_after == "prepared" and str(operation.get("status") or "") == "prepared":
        return _public({**plan, "ok": False, "status": "release_authority_handoff_acknowledgment_interrupted", "acknowledgment_operation_id": op_id, "acknowledgment_operation_status": "prepared", "previous_coherent_acknowledgment_preserved": True, "findings": [{"kind": "handoff_acknowledgment_interrupted_after_prepared"}]})

    ack_id = str(receipt.get("acknowledgment_id") or "")
    receipt_path = directory / "acknowledgments" / f"{ack_id}.json"
    existing_receipt = read_json(receipt_path)
    if existing_receipt and existing_receipt != receipt:
        return _public({**plan, "ok": False, "status": "release_authority_handoff_acknowledgment_contradictory", "findings": [{"kind": "handoff_acknowledgment_existing_receipt_contradiction"}]})
    if not existing_receipt:
        atomic_json(receipt_path, receipt)
    operation.update({"status": "receipt_written", "updated_at": utc_now()})
    operation = _write_operation(op_path, operation)
    atomic_json(directory / "active_ack_operation.json", {"schema": HANDOFF_ACK_OPERATION_SCHEMA, "acknowledgment_operation_id": op_id, "operation_sha256": operation["operation_sha256"], "status": operation["status"], "content_free": True})
    if interrupt_after in {"receipt_written", "after_receipt"}:
        return _public({**plan, **receipt, "ok": False, "status": "release_authority_handoff_acknowledgment_interrupted", "acknowledgment_present": True, "acknowledgment_operation_id": op_id, "acknowledgment_operation_status": "receipt_written", "previous_coherent_acknowledgment_preserved": True, "findings": [{"kind": "handoff_acknowledgment_interrupted_after_receipt"}]})

    pointer_record = {
        "schema": HANDOFF_ACK_SCHEMA,
        "acknowledgment_id": ack_id,
        "plan_id": receipt["plan_id"],
        "plan_binding_sha256": receipt["plan_binding_sha256"],
        "receipt_sha256": receipt["receipt_sha256"],
        "acknowledgment_operation_id": op_id,
        "content_free": True,
    }
    active_pointer = read_json(directory / "active_acknowledgment.json")
    if active_pointer and active_pointer != pointer_record:
        active_id = str(active_pointer.get("acknowledgment_id") or "")
        allowed_replacement = bool(replacement_of_acknowledgment_id and active_id == replacement_of_acknowledgment_id)
        if not allowed_replacement:
            return _public({**plan, "ok": False, "status": "release_authority_handoff_acknowledgment_contradictory", "previous_coherent_acknowledgment_preserved": True, "findings": [{"kind": "handoff_acknowledgment_active_pointer_contradiction"}]})
    if not active_pointer or active_pointer != pointer_record:
        atomic_json(directory / "active_acknowledgment.json", pointer_record)
    operation.update({"status": "pointer_written", "updated_at": utc_now()})
    operation = _write_operation(op_path, operation)
    atomic_json(directory / "active_ack_operation.json", {"schema": HANDOFF_ACK_OPERATION_SCHEMA, "acknowledgment_operation_id": op_id, "operation_sha256": operation["operation_sha256"], "status": operation["status"], "content_free": True})
    if interrupt_after in {"pointer_written", "after_pointer"}:
        return _public({**plan, **receipt, "ok": False, "status": "release_authority_handoff_acknowledgment_interrupted", "acknowledgment_present": True, "acknowledgment_operation_id": op_id, "acknowledgment_operation_status": "pointer_written", "findings": [{"kind": "handoff_acknowledgment_interrupted_after_pointer"}]})

    used_record = {
        "schema": "eidolon-used-release-authority-handoff-token-v2",
        "used_at": operation.get("started_at"),
        "action": auth.get("action"),
        "authorization_binding_sha256": auth.get("binding_sha256"),
        "acknowledgment_operation_id": op_id,
        "acknowledgment_id": ack_id,
        "content_free": True,
    }
    existing_used = read_json(used_path)
    if existing_used and existing_used != used_record:
        return _public({**plan, "ok": False, "status": "release_authority_handoff_acknowledgment_contradictory", "findings": [{"kind": "handoff_acknowledgment_used_token_contradiction"}]})
    if not existing_used:
        atomic_json(used_path, used_record)
    operation.update({"status": "token_burned", "updated_at": utc_now()})
    operation = _write_operation(op_path, operation)
    atomic_json(directory / "active_ack_operation.json", {"schema": HANDOFF_ACK_OPERATION_SCHEMA, "acknowledgment_operation_id": op_id, "operation_sha256": operation["operation_sha256"], "status": operation["status"], "content_free": True})
    if interrupt_after in {"token_burned", "after_token"}:
        return _public({**plan, **receipt, "ok": False, "status": "release_authority_handoff_acknowledgment_interrupted", "acknowledgment_present": True, "acknowledgment_operation_id": op_id, "acknowledgment_operation_status": "token_burned", "findings": [{"kind": "handoff_acknowledgment_interrupted_after_token_burn"}]})

    operation.update({"status": "completed", "completed_at": utc_now(), "updated_at": utc_now()})
    operation = _write_operation(op_path, operation)
    atomic_json(directory / "active_ack_operation.json", {"schema": HANDOFF_ACK_OPERATION_SCHEMA, "acknowledgment_operation_id": op_id, "operation_sha256": operation["operation_sha256"], "status": operation["status"], "content_free": True})
    return _public({
        **plan,
        **receipt,
        "ok": True,
        "status": "release_authority_handoff_plan_acknowledged",
        "acknowledgment_present": True,
        "acknowledgment_receipt_sha256": receipt["receipt_sha256"],
        "acknowledgment_expires_at": receipt["expires_at"],
        "acknowledgment_operation_id": op_id,
        "acknowledgment_operation_status": "completed",
        "acknowledgment_recovery_performed": recovery_performed,
    })


def acknowledge_release_authority_handoff_plan(
    token: str,
    *,
    confirm: str,
    operator_tab_id: str = "operator-tab",
    operation_revision: int = 1,
    interrupt_after: str = "",
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    if confirm != HANDOFF_ACK_CONFIRMATION:
        return _public({"ok": False, "status": "literal_confirmation_required", "findings": [{"kind": "literal_confirmation_required"}]})
    auth = _load_authorization(runtime_root, token)
    if not auth:
        return _public({"ok": False, "status": "release_authority_handoff_authorization_invalid", "findings": [{"kind": "release_authority_handoff_authorization_invalid"}]})
    plan = release_authority_handoff_plan_status(runtime_root=runtime_root)
    if not plan.get("ok"):
        return _public({"ok": False, "status": "release_authority_handoff_authorization_stale", "findings": plan.get("findings") or [{"kind": "release_authority_handoff_authorization_stale"}]})
    findings = _validate_authorization(auth, plan, operator_tab_id=operator_tab_id, operation_revision=operation_revision)
    if findings:
        status = "release_authority_handoff_authorization_expired" if any(item.get("kind") == "handoff_authorization_expired" for item in findings) else "release_authority_handoff_authorization_stale"
        return _public({**plan, "ok": False, "status": status, "findings": findings, "previous_coherent_acknowledgment_preserved": True})
    try:
        with metadata_mutation_lock(handoff_plan_directory(runtime_root) / "active_acknowledgment.json"):
            return _execute_acknowledgment(token, auth, plan, operator_tab_id=operator_tab_id, operation_revision=operation_revision, runtime_root=runtime_root, interrupt_after=interrupt_after)
    except MetadataMutationBusy:
        return _public({**plan, "ok": False, "status": "release_authority_handoff_acknowledgment_busy", "findings": [{"kind": "release_authority_handoff_acknowledgment_busy"}], "previous_coherent_acknowledgment_preserved": True})


def _scan_acknowledgment_records(runtime_root: str | Path | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    directory = handoff_plan_directory(runtime_root) / "acknowledgments"
    valid: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    if not directory.exists():
        return valid, findings
    for path in sorted(directory.glob("*.json"), key=lambda item: item.name):
        state, row = _json_state(path)
        if state != "ok":
            findings.append({"kind": f"handoff_acknowledgment_record_{state}"})
            continue
        if str(row.get("receipt_sha256") or "") != _record_digest(row, "receipt_sha256"):
            findings.append({"kind": "handoff_acknowledgment_record_digest_mismatch"})
            continue
        valid.append(row)
    return valid, findings


def release_authority_handoff_acknowledgment_status(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    directory = handoff_plan_directory(runtime_root)
    private = _active_ack_private(runtime_root)
    pointer_state = str(private.get("pointer_state") or "missing")
    pointer = dict(private.get("pointer") or {})
    receipt_state = str(private.get("receipt_state") or "missing")
    receipt = dict(private.get("receipt") or {})
    operation_state = str(private.get("operation_state") or "missing")
    operation_pointer = dict(private.get("operation") or {})
    plan = release_authority_handoff_plan_status(runtime_root=runtime_root)
    if pointer_state == "missing":
        out = {**plan, "ok": True, "status": "release_authority_handoff_not_acknowledged", "acknowledgment_present": False}
        if operation_state == "ok" and str(operation_pointer.get("status") or "") not in {"", "completed"}:
            out.update({"ok": False, "status": "release_authority_handoff_acknowledgment_recovery_required", "acknowledgment_operation_id": operation_pointer.get("acknowledgment_operation_id"), "acknowledgment_operation_status": operation_pointer.get("status"), "findings": [{"kind": "handoff_acknowledgment_operation_incomplete"}]})
        return _public(out)
    findings: list[dict[str, Any]] = list(plan.get("findings") or [])
    if pointer_state != "ok":
        findings.append({"kind": f"handoff_acknowledgment_pointer_{pointer_state}"})
    if receipt_state != "ok":
        findings.append({"kind": f"handoff_acknowledgment_receipt_{receipt_state}"})
    if receipt:
        if str(receipt.get("receipt_sha256") or "") != _record_digest(receipt, "receipt_sha256"):
            findings.append({"kind": "handoff_acknowledgment_receipt_invalid"})
        for field in ("acknowledgment_id", "plan_id", "plan_binding_sha256", "receipt_sha256", "acknowledgment_operation_id"):
            if str(pointer.get(field) or "") != str(receipt.get(field) if field != "acknowledgment_operation_id" else pointer.get(field) or ""):
                if field != "acknowledgment_operation_id":
                    findings.append({"kind": f"handoff_acknowledgment_pointer_{field}_mismatch"})
        for field in ACK_PLAN_BINDING_FIELDS:
            if str(receipt.get(field) or "") != str(plan.get(field) or ""):
                findings.append({"kind": f"handoff_acknowledgment_{field}_drift"})
        if receipt.get("grants_authority") is not False:
            findings.append({"kind": "handoff_acknowledgment_authority_contradiction"})
    expired = bool(receipt) and _is_expired(str(receipt.get("expires_at") or ""))
    if expired:
        findings.append({"kind": "handoff_acknowledgment_expired"})

    valid_records, scan_findings = _scan_acknowledgment_records(runtime_root)
    findings.extend(scan_findings)
    superseded = {str(item.get("replacement_of_acknowledgment_id") or "") for item in valid_records if item.get("replacement_of_acknowledgment_id")}
    current_plan_records = [item for item in valid_records if str(item.get("plan_binding_sha256") or "") == str(plan.get("plan_binding_sha256") or "") and str(item.get("acknowledgment_id") or "") not in superseded and not _is_expired(str(item.get("expires_at") or ""))]
    if len(current_plan_records) > 1:
        findings.append({"kind": "multiple_current_handoff_acknowledgments"})

    op_id = str(pointer.get("acknowledgment_operation_id") or operation_pointer.get("acknowledgment_operation_id") or "")
    op_status = str(operation_pointer.get("status") or "")
    if op_id:
        op_state, op_record = _json_state(directory / "operations" / f"{op_id}.json")
        if op_state != "ok":
            findings.append({"kind": f"handoff_acknowledgment_operation_{op_state}"})
        elif str(op_record.get("operation_sha256") or "") != _operation_digest(op_record):
            findings.append({"kind": "handoff_acknowledgment_operation_digest_mismatch"})
        else:
            op_status = str(op_record.get("status") or "")
            if op_status != "completed":
                findings.append({"kind": "handoff_acknowledgment_operation_incomplete"})
    status = "release_authority_handoff_plan_acknowledged"
    if expired:
        status = "release_authority_handoff_acknowledgment_expired"
    elif findings:
        status = "release_authority_handoff_acknowledgment_stale"
    return _public({
        **plan,
        **receipt,
        "ok": not findings,
        "status": status,
        "acknowledgment_present": bool(receipt),
        "acknowledgment_id": str(receipt.get("acknowledgment_id") or pointer.get("acknowledgment_id") or ""),
        "acknowledgment_receipt_sha256": str(receipt.get("receipt_sha256") or ""),
        "acknowledgment_expires_at": str(receipt.get("expires_at") or ""),
        "acknowledgment_expired": expired,
        "acknowledgment_operation_id": op_id,
        "acknowledgment_operation_status": op_status,
        "findings": findings,
    })
