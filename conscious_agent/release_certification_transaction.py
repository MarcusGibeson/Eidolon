from __future__ import annotations

"""Exact certification decision recording, scope authority, and revocation.

Certification changes external release authority only. It never mutates installed
source, providers, models, conversations, or operator project registries.
"""

from collections import Counter
import json
from pathlib import Path
import secrets
from typing import Any, Iterable, Mapping

try:
    from release_candidate_identity import atomic_json, digest_payload, read_json, utc_now
    from release_certification_evidence import certification_directory
    from release_certification_plan import CERTIFICATION_AUTHORIZATION_CONFIRMATION, active_certification_plan_private, certification_authorization_valid, certification_plan_status, _current_certification_state
    from release_promotion_preview import current_promotion_state_private, promotion_directory
    from release_promotion_transaction import active_promotion_transaction_private, promotion_transaction_status
    from release_installation_preview import _target_inventory
except ImportError:
    from release_candidate_identity import atomic_json, digest_payload, read_json, utc_now
    from release_certification_evidence import certification_directory
    from release_certification_plan import CERTIFICATION_AUTHORIZATION_CONFIRMATION, active_certification_plan_private, certification_authorization_valid, certification_plan_status, _current_certification_state
    from release_promotion_preview import current_promotion_state_private, promotion_directory
    from release_promotion_transaction import active_promotion_transaction_private, promotion_transaction_status
    from release_installation_preview import _target_inventory

CERTIFICATION_TRANSACTION_CONTRACT_VERSION = "1"
CERTIFICATION_TRANSACTION_SCHEMA = "eidolon-certification-transaction-v1"
CERTIFICATION_APPLY_CONFIRMATION = "APPLY EXACT CERTIFICATION DECISION"
CERTIFICATION_REVOCATION_CONFIRMATION = "REVOKE EXACT CERTIFICATION SCOPE"
CERTIFICATION_APPLY_ACTION = "apply_exact_certification_decision"
CERTIFICATION_REVOCATION_ACTION = "revoke_exact_certification_scope"


def _counts(rows: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    found: Counter[str] = Counter()
    for row in rows or []:
        found[str(row.get("kind") or "unknown")] += max(1, int(row.get("count") or 1))
    return [{"kind": key, "count": found[key]} for key in sorted(found)]


def _token_digest(token: str) -> str:
    return digest_payload({"contract": "eidolon-certification-token-v1", "token": token})


def _transaction_binding(record: Mapping[str, Any]) -> str:
    return digest_payload({
        "contract": "eidolon-certification-transaction-identity-v1",
        "certification_transaction_id": str(record.get("certification_transaction_id") or ""),
        "generation": int(record.get("generation") or 0),
        "action": str(record.get("action") or ""),
        "plan_id": str(record.get("plan_id") or ""),
        "plan_generation": int(record.get("plan_generation") or 0),
        "plan_binding_sha256": str(record.get("plan_binding_sha256") or ""),
        "candidate_id": str(record.get("candidate_id") or ""),
        "archive_sha256": str(record.get("archive_sha256") or ""),
        "installed_receipt_sha256": str(record.get("installed_receipt_sha256") or ""),
        "promotion_receipt_sha256": str(record.get("promotion_receipt_sha256") or ""),
        "target_project_id": str(record.get("target_project_id") or ""),
        "target_inventory_sha256": str(record.get("target_inventory_sha256") or ""),
        "promotion_state_sha256": str(record.get("promotion_state_sha256") or ""),
        "evidence_set_sha256": str(record.get("evidence_set_sha256") or ""),
        "certification_scope": str(record.get("certification_scope") or ""),
        "decision": str(record.get("decision") or ""),
        "previous_certification_generation": int(record.get("previous_certification_generation") or 0),
        "previous_certification_state_sha256": str(record.get("previous_certification_state_sha256") or ""),
        "authorization_binding_sha256": str(record.get("authorization_binding_sha256") or ""),
    })


def _state_digest(record: Mapping[str, Any]) -> str:
    return digest_payload({
        "contract": "eidolon-certification-transaction-state-v1",
        "certification_transaction_identity_sha256": str(record.get("certification_transaction_identity_sha256") or ""),
        "state": str(record.get("state") or ""),
        "event_sequence": int(record.get("event_sequence") or 0),
        "certification_receipt_sha256": str(record.get("certification_receipt_sha256") or ""),
        "certification_state_sha256": str(record.get("certification_state_sha256") or ""),
        "revocation_receipt_sha256": str(record.get("revocation_receipt_sha256") or ""),
    })


def _record_digest(record: Mapping[str, Any], field: str = "record_sha256") -> str:
    material = dict(record)
    material.pop(field, None)
    return digest_payload(material)


def _public(record: Mapping[str, Any] | None) -> dict[str, Any]:
    row = dict(record or {})
    contradictions = _counts(row.get("contradictions") if isinstance(row.get("contradictions"), list) else [])
    status = str(row.get("status") or row.get("state") or "promoted_uncertified")
    return {
        "ok": bool(row.get("ok")) and not contradictions,
        "status": status,
        "contract_version": CERTIFICATION_TRANSACTION_CONTRACT_VERSION,
        "certification_transaction_present": bool(row),
        "certification_transaction_id": str(row.get("certification_transaction_id") or ""),
        "certification_transaction_identity_sha256": str(row.get("certification_transaction_identity_sha256") or ""),
        "certification_transaction_state_sha256": str(row.get("certification_transaction_state_sha256") or ""),
        "generation": int(row.get("generation") or 0),
        "plan_id": str(row.get("plan_id") or ""),
        "candidate_id": str(row.get("candidate_id") or ""),
        "packaged_version": str(row.get("packaged_version") or ""),
        "archive_sha256": str(row.get("archive_sha256") or ""),
        "installed_receipt_sha256": str(row.get("installed_receipt_sha256") or ""),
        "promotion_receipt_sha256": str(row.get("promotion_receipt_sha256") or ""),
        "target_project_id": str(row.get("target_project_id") or ""),
        "target_inventory_sha256": str(row.get("target_inventory_sha256") or ""),
        "evidence_set_sha256": str(row.get("evidence_set_sha256") or ""),
        "certification_scope": str(row.get("certification_scope") or ""),
        "decision": str(row.get("decision") or ""),
        "certification_receipt_sha256": str(row.get("certification_receipt_sha256") or ""),
        "certification_state_sha256": str(row.get("certification_state_sha256") or ""),
        "revocation_receipt_sha256": str(row.get("revocation_receipt_sha256") or ""),
        "certified_scopes": list(row.get("certified_scopes") or []),
        "general_release_certified": "general_release" in list(row.get("certified_scopes") or []),
        "scope_certified": status in {"scope_certified", "partially_certified", "certified"},
        "partially_certified": status == "partially_certified",
        "certification_declined": status == "certification_declined",
        "insufficient_evidence": status == "insufficient_evidence",
        "authorization_token": str(row.get("authorization_token") or ""),
        "literal_confirmation_required": str(row.get("literal_confirmation_required") or CERTIFICATION_APPLY_CONFIRMATION),
        "contradictions": contradictions,
        "contradiction_count": sum(int(item["count"]) for item in contradictions),
        "source_files_mutated": False,
        "installed_source_mutated": False,
        "provider_configuration_mutated": False,
        "models_mutated": False,
        "certification_inferred_from_package": False,
        "certification_inferred_from_installation": False,
        "certification_inferred_from_promotion": False,
        "paths_suppressed": True,
        "records_external": True,
        "content_free": True,
        "provider_contacted": False,
        "ordinary_conversation_affected": False,
    }


def _append_event(runtime_root: str | Path | None, txid: str, record: dict[str, Any], event: dict[str, Any]) -> None:
    path = certification_directory(runtime_root) / "events" / f"{txid}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    record["event_sequence"] = int(record.get("event_sequence") or 0) + 1
    row = {
        "schema": "eidolon-certification-event-v1",
        "sequence": record["event_sequence"],
        "certification_transaction_id": txid,
        "certification_transaction_identity_sha256": record.get("certification_transaction_identity_sha256", ""),
        "recorded_at": utc_now(),
        **event,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def _save(runtime_root: str | Path | None, record: dict[str, Any]) -> None:
    directory = certification_directory(runtime_root)
    record["certification_transaction_state_sha256"] = _state_digest(record)
    record["record_sha256"] = _record_digest(record)
    atomic_json(directory / "transactions" / f"{record['certification_transaction_id']}.json", record)
    atomic_json(directory / "active_transaction.json", {
        "schema": CERTIFICATION_TRANSACTION_SCHEMA,
        "certification_transaction_id": record["certification_transaction_id"],
        "generation": record["generation"],
        "certification_transaction_identity_sha256": record["certification_transaction_identity_sha256"],
        "certification_transaction_state_sha256": record["certification_transaction_state_sha256"],
        "record_sha256": record["record_sha256"],
        "content_free": True,
    })


def active_certification_transaction_private(runtime_root: str | Path | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    directory = certification_directory(runtime_root)
    pointer = read_json(directory / "active_transaction.json")
    txid = str(pointer.get("certification_transaction_id") or "")
    return pointer, read_json(directory / "transactions" / f"{txid}.json") if txid else {}


def _used(runtime_root: str | Path | None, token: str) -> bool:
    return (certification_directory(runtime_root) / "used_tokens" / f"{_token_digest(token)}.json").is_file()


def _mark_used(runtime_root: str | Path | None, token: str, outcome: str, txid: str) -> None:
    atomic_json(certification_directory(runtime_root) / "used_tokens" / f"{_token_digest(token)}.json", {
        "schema": "eidolon-certification-used-token-v1",
        "token_sha256": _token_digest(token),
        "outcome": outcome,
        "certification_transaction_id": txid,
        "used_at": utc_now(),
        "content_free": True,
    })


def _receipt_valid(receipt: Mapping[str, Any]) -> bool:
    material = dict(receipt)
    expected = str(material.pop("receipt_sha256", ""))
    return bool(expected and expected == digest_payload(material))


def _promotion_authority_for_scopes(runtime_root: str | Path | None, record: Mapping[str, Any], certified_scopes: list[str], certification_receipt_sha256: str, previous_state: Mapping[str, Any]) -> dict[str, Any]:
    state_name = "certified" if "general_release" in certified_scopes else ("partially_certified" if certified_scopes else "promoted_uncertified")
    state = {
        "schema": "eidolon-promotion-authority-state-v1",
        "state_id": f"promotion-state-{int(previous_state.get('generation') or 0)+1}-{secrets.token_hex(6)}",
        "generation": int(previous_state.get("generation") or 0) + 1,
        "state": state_name,
        "previous_state": str(previous_state.get("state") or "promoted_uncertified"),
        "previous_state_sha256": str(previous_state.get("state_sha256") or ""),
        "promotion_transaction_id": record["promotion_transaction_id"],
        "promotion_transaction_identity_sha256": record["promotion_transaction_identity_sha256"],
        "promotion_receipt_sha256": record["promotion_receipt_sha256"],
        "certification_transaction_id": record["certification_transaction_id"],
        "certification_receipt_sha256": certification_receipt_sha256,
        "certified_scopes": sorted(certified_scopes),
        "candidate_id": record["candidate_id"],
        "packaged_version": record["packaged_version"],
        "target_project_id": record["target_project_id"],
        "target_inventory_sha256": record["target_inventory_sha256"],
        "certified": bool(certified_scopes),
        "created_at": utc_now(),
        "content_free": True,
    }
    state["state_sha256"] = digest_payload(state)
    directory = promotion_directory(runtime_root)
    atomic_json(directory / "states" / f"{state['state_id']}.json", state)
    atomic_json(directory / "active_promotion_state.json", {
        "schema": "eidolon-promotion-authority-state-v1",
        "state_id": state["state_id"],
        "generation": state["generation"],
        "state_sha256": state["state_sha256"],
        "state": state["state"],
        "content_free": True,
    })
    return state


def _certification_state(
    record: Mapping[str, Any],
    receipt: Mapping[str, Any],
    previous_state: Mapping[str, Any],
) -> dict[str, Any]:
    certified_scopes = list(previous_state.get("certified_scopes") or [])
    scope_receipts = dict(previous_state.get("scope_receipts") or {})
    revoked_scope_receipts = dict(previous_state.get("revoked_scope_receipts") or {})
    decision = str(record.get("decision") or "")
    scope = str(record.get("certification_scope") or "")
    if decision == "certified":
        if scope not in certified_scopes:
            certified_scopes.append(scope)
        scope_receipts[scope] = receipt["receipt_sha256"]
        revoked_scope_receipts.pop(scope, None)
        state_name = "scope_certified" if len(certified_scopes) == 1 else "partially_certified"
    elif decision == "declined":
        state_name = "certification_declined"
    else:
        state_name = "insufficient_evidence"
    state = {
        "schema": "eidolon-certification-authority-state-v1",
        "state_id": f"certification-state-{int(previous_state.get('generation') or 0)+1}-{secrets.token_hex(6)}",
        "generation": int(previous_state.get("generation") or 0) + 1,
        "state": state_name,
        "previous_state": str(previous_state.get("state") or "promoted_uncertified"),
        "previous_state_sha256": str(previous_state.get("state_sha256") or ""),
        "certification_transaction_id": record["certification_transaction_id"],
        "certification_transaction_identity_sha256": record["certification_transaction_identity_sha256"],
        "certification_receipt_sha256": receipt["receipt_sha256"],
        "certification_scope": scope,
        "decision": decision,
        "certified_scopes": sorted(certified_scopes),
        "scope_receipts": scope_receipts,
        "revoked_scope_receipts": revoked_scope_receipts,
        "candidate_id": record["candidate_id"],
        "archive_sha256": record["archive_sha256"],
        "installed_receipt_sha256": record["installed_receipt_sha256"],
        "promotion_receipt_sha256": record["promotion_receipt_sha256"],
        "target_project_id": record["target_project_id"],
        "target_inventory_sha256": record["target_inventory_sha256"],
        "created_at": utc_now(),
        "content_free": True,
    }
    state["state_sha256"] = digest_payload(state)
    return state


def _state_by_digest(runtime_root: str | Path | None, directory_name: str, digest: str) -> dict[str, Any]:
    if not digest:
        return {}
    base = (certification_directory(runtime_root) if directory_name == "certification" else promotion_directory(runtime_root)) / "states"
    for path in sorted(base.glob("*.json")):
        row = read_json(path)
        if str(row.get("state_sha256") or "") == digest:
            return row
    return {}


def _decision_receipt(record: Mapping[str, Any], previous_state: Mapping[str, Any]) -> dict[str, Any]:
    supersedes = str(dict(previous_state.get("scope_receipts") or {}).get(record["certification_scope"]) or dict(previous_state.get("revoked_scope_receipts") or {}).get(record["certification_scope"]) or "")
    receipt = {
        "schema": "eidolon-certification-decision-receipt-v1",
        "certification_transaction_id": record["certification_transaction_id"],
        "certification_transaction_identity_sha256": record["certification_transaction_identity_sha256"],
        "plan_id": record["plan_id"],
        "candidate_id": record["candidate_id"],
        "packaged_version": record["packaged_version"],
        "archive_sha256": record["archive_sha256"],
        "source_manifest_sha256": record["source_manifest_sha256"],
        "archive_manifest_sha256": record["archive_manifest_sha256"],
        "installed_receipt_sha256": record["installed_receipt_sha256"],
        "promotion_receipt_sha256": record["promotion_receipt_sha256"],
        "target_project_id": record["target_project_id"],
        "target_inventory_sha256": record["target_inventory_sha256"],
        "evidence_set": record["evidence_set"],
        "evidence_set_sha256": record["evidence_set_sha256"],
        "decision_policy_sha256": record["decision_policy_sha256"],
        "certification_scope": record["certification_scope"],
        "decision": record["decision"],
        "prior_authority_generation": record["previous_certification_generation"],
        "prior_authority_state_sha256": record["previous_certification_state_sha256"],
        "supersedes_receipt_sha256": supersedes,
        "recorded_at": utc_now(),
        "content_free": True,
    }
    receipt["receipt_sha256"] = digest_payload(receipt)
    return receipt


def _complete_certification_decision(
    runtime_root: str | Path | None,
    record: dict[str, Any],
    *,
    interrupt_at: str = "",
) -> dict[str, Any]:
    directory = certification_directory(runtime_root)
    txid = record["certification_transaction_id"]
    previous_certification_state = _state_by_digest(runtime_root, "certification", str(record.get("previous_certification_state_sha256") or ""))
    if not previous_certification_state and int(record.get("previous_certification_generation") or 0) == 0:
        previous_certification_state = {}
    previous_promotion_state = _state_by_digest(runtime_root, "promotion", str(record.get("promotion_state_sha256") or ""))

    receipt_path = directory / "receipts" / f"{txid}.json"
    receipt = read_json(receipt_path)
    if receipt:
        if not _receipt_valid(receipt) or str(receipt.get("certification_transaction_identity_sha256") or "") != str(record.get("certification_transaction_identity_sha256") or ""):
            record.setdefault("contradictions", []).append({"kind": "certification_receipt_contradictory"})
            record["state"] = record["status"] = "certification_uncertain"
            _save(runtime_root, record)
            return record
    else:
        receipt = _decision_receipt(record, previous_certification_state)
        atomic_json(receipt_path, receipt)
    record["certification_receipt_sha256"] = receipt["receipt_sha256"]
    record["receipt_persisted"] = True
    _append_event(runtime_root, txid, record, {"kind": "certification_receipt_written", "receipt_sha256": receipt["receipt_sha256"]})
    _save(runtime_root, record)
    if interrupt_at == "after_receipt":
        record["state"] = record["status"] = "certification_interrupted"
        record["interrupted_after"] = "receipt"
        _append_event(runtime_root, txid, record, {"kind": "interrupted_after_certification_receipt"})
        _save(runtime_root, record)
        return record

    state_id = str(record.get("certification_state_id") or "")
    state = read_json(directory / "states" / f"{state_id}.json") if state_id else {}
    if state:
        material = dict(state); expected = str(material.pop("state_sha256", ""))
        if not expected or expected != digest_payload(material) or str(state.get("certification_transaction_id") or "") != txid:
            record.setdefault("contradictions", []).append({"kind": "certification_authority_state_contradictory"})
            record["state"] = record["status"] = "certification_uncertain"
            _save(runtime_root, record)
            return record
    else:
        state = _certification_state(record, receipt, previous_certification_state)
        record["certification_state_id"] = state["state_id"]
        atomic_json(directory / "states" / f"{state['state_id']}.json", state)
    atomic_json(directory / "active_certification_state.json", {
        "schema": "eidolon-certification-authority-state-v1", "state_id": state["state_id"],
        "generation": state["generation"], "state_sha256": state["state_sha256"],
        "state": state["state"], "content_free": True,
    })
    record["certification_state_sha256"] = state["state_sha256"]
    record["certified_scopes"] = state["certified_scopes"]
    record["scope_state_persisted"] = True
    _append_event(runtime_root, txid, record, {"kind": "certification_scope_state_written", "state_sha256": state["state_sha256"]})
    _save(runtime_root, record)
    if interrupt_at == "after_scope_state":
        record["state"] = record["status"] = "certification_interrupted"
        record["interrupted_after"] = "scope_state"
        _append_event(runtime_root, txid, record, {"kind": "interrupted_after_certification_scope_state"})
        _save(runtime_root, record)
        return record

    if record["decision"] == "certified":
        promotion_state_sha = str(record.get("promotion_authority_state_sha256") or "")
        promotion_state = _state_by_digest(runtime_root, "promotion", promotion_state_sha) if promotion_state_sha else {}
        if not promotion_state:
            promotion_state = _promotion_authority_for_scopes(runtime_root, record, state["certified_scopes"], receipt["receipt_sha256"], previous_promotion_state)
            record["promotion_authority_state_sha256"] = promotion_state["state_sha256"]
        record["promotion_authority_persisted"] = True
        _append_event(runtime_root, txid, record, {"kind": "promotion_authority_updated", "state_sha256": record["promotion_authority_state_sha256"]})
        _save(runtime_root, record)
        if interrupt_at == "after_promotion_authority":
            record["state"] = record["status"] = "certification_interrupted"
            record["interrupted_after"] = "promotion_authority"
            _append_event(runtime_root, txid, record, {"kind": "interrupted_after_promotion_authority"})
            _save(runtime_root, record)
            return record

    record["state"] = record["status"] = state["state"]
    record["completed_at"] = utc_now()
    record["decision_finalized"] = True
    _append_event(runtime_root, txid, record, {"kind": "certification_decision_finalized", "state": state["state"]})
    _save(runtime_root, record)
    atomic_json(directory / "active_certification_receipt.json", {
        "schema": "eidolon-certification-decision-receipt-v1", "certification_transaction_id": txid,
        "receipt_sha256": receipt["receipt_sha256"], "state_sha256": state["state_sha256"],
        "scope": record["certification_scope"], "decision": record["decision"], "content_free": True,
    })
    return record


def apply_authorized_certification(
    authorization_token: str,
    *,
    confirm: str,
    runtime_root: str | Path | None = None,
    _interrupt_at: str = "",
) -> dict[str, Any]:
    token = authorization_token if isinstance(authorization_token, str) else ""
    if confirm != CERTIFICATION_APPLY_CONFIRMATION:
        return _public({"status": "literal_confirmation_required", "ok": False, "contradictions": [{"kind": "literal_confirmation_required"}]})
    if _used(runtime_root, token):
        return _public({"status": "authorization_reused", "ok": False, "contradictions": [{"kind": "authorization_reused"}]})
    auth, findings = certification_authorization_valid(token, runtime_root)
    plan_status = certification_plan_status(runtime_root=runtime_root)
    _, plan = active_certification_plan_private(runtime_root)
    if findings or not plan_status.get("ok") or not plan:
        return _public({"status": "authorization_stale_or_mismatched", "ok": False, "contradictions": findings or [{"kind": "certification_plan_stale"}]})
    promotion_status = promotion_transaction_status(runtime_root=runtime_root)
    _, promotion_transaction = active_promotion_transaction_private(runtime_root)
    if not promotion_status.get("ok") or str(promotion_status.get("status") or "") != "promoted_uncertified":
        return _public({"status": "certification_apply_blocked", "ok": False, "contradictions": [{"kind": "exact_promoted_release_required"}]})
    root = Path(str(promotion_transaction.get("target_root_path") or ""))
    inventory = _target_inventory(root) if root.is_dir() else {"ok": False, "digest": ""}
    if not inventory.get("ok") or str(inventory.get("digest") or "") != str(plan.get("target_inventory_sha256") or ""):
        return _public({"status": "authorization_stale_or_mismatched", "ok": False, "contradictions": [{"kind": "target_inventory_drift"}]})
    pointer, _ = active_certification_transaction_private(runtime_root)
    generation = int(pointer.get("generation") or 0) + 1
    _, previous_certification_state = _current_certification_state(runtime_root)
    record = {
        "schema": CERTIFICATION_TRANSACTION_SCHEMA,
        "certification_transaction_id": f"certification-transaction-{generation}-{secrets.token_hex(8)}",
        "generation": generation, "action": CERTIFICATION_APPLY_ACTION, "created_at": utc_now(),
        "state": "recording_certification_decision", "status": "recording_certification_decision", "ok": True,
        "event_sequence": 0, "plan_id": plan["plan_id"], "plan_generation": plan["generation"],
        "plan_binding_sha256": plan["plan_binding_sha256"], "candidate_id": plan["candidate_id"],
        "packaged_version": plan["packaged_version"], "archive_sha256": plan["archive_sha256"],
        "source_manifest_sha256": plan["source_manifest_sha256"], "archive_manifest_sha256": plan["archive_manifest_sha256"],
        "installed_transaction_id": plan["installed_transaction_id"], "installed_receipt_sha256": plan["installed_receipt_sha256"],
        "promotion_transaction_id": plan["promotion_transaction_id"], "promotion_transaction_identity_sha256": plan["promotion_transaction_identity_sha256"],
        "promotion_receipt_sha256": plan["promotion_receipt_sha256"], "target_project_id": plan["target_project_id"],
        "target_inventory_sha256": plan["target_inventory_sha256"], "promotion_state_sha256": plan["promotion_state_sha256"],
        "evidence_set": plan["evidence_set"], "evidence_set_sha256": plan["evidence_set_sha256"],
        "decision_policy_sha256": plan["decision_policy_sha256"], "certification_scope": plan["certification_scope"],
        "decision": plan["proposed_decision"], "previous_certification_generation": plan["previous_certification_generation"],
        "previous_certification_state_sha256": plan["previous_certification_state_sha256"],
        "authorization_binding_sha256": auth["authorization_binding_sha256"],
        "certification_receipt_sha256": "", "certification_state_sha256": "", "revocation_receipt_sha256": "",
        "certified_scopes": list(previous_certification_state.get("certified_scopes") or []),
        "start_event_persisted": False, "receipt_persisted": False, "scope_state_persisted": False,
        "promotion_authority_persisted": False, "decision_finalized": False, "contradictions": [],
    }
    record["certification_transaction_identity_sha256"] = _transaction_binding(record)
    _save(runtime_root, record)
    _mark_used(runtime_root, token, "certification_decision_started", record["certification_transaction_id"])
    if _interrupt_at == "before_event_persistence":
        record["state"] = record["status"] = "certification_interrupted"
        record["interrupted_after"] = "before_event_persistence"
        _save(runtime_root, record)
        return _public(record)
    _append_event(runtime_root, record["certification_transaction_id"], record, {"kind": "certification_decision_started", "decision": record["decision"], "scope": record["certification_scope"]})
    record["start_event_persisted"] = True
    _save(runtime_root, record)
    if _interrupt_at == "after_event_persistence":
        record["state"] = record["status"] = "certification_interrupted"
        record["interrupted_after"] = "event_persistence"
        _append_event(runtime_root, record["certification_transaction_id"], record, {"kind": "interrupted_after_certification_start_event"})
        _save(runtime_root, record)
        return _public(record)
    return _public(_complete_certification_decision(runtime_root, record, interrupt_at=_interrupt_at))

def certification_status(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    promotion_status = promotion_transaction_status(runtime_root=runtime_root)
    if not promotion_status.get("promotion_transaction_present"):
        return _public({"status": "not_installed", "ok": True})
    pointer, state = _current_certification_state(runtime_root)
    if not pointer:
        return _public({
            "status": "promoted_uncertified",
            "ok": bool(promotion_status.get("ok")),
            "candidate_id": promotion_status.get("candidate_id"),
            "archive_sha256": promotion_status.get("archive_sha256"),
            "installed_receipt_sha256": promotion_status.get("installed_receipt_sha256"),
            "promotion_receipt_sha256": promotion_status.get("promotion_receipt_sha256"),
            "target_project_id": promotion_status.get("target_project_id"),
            "target_inventory_sha256": promotion_status.get("target_inventory_sha256"),
            "contradictions": promotion_status.get("contradictions") or [],
        })
    findings: list[dict[str, Any]] = []
    material = dict(state)
    expected_state = str(material.pop("state_sha256", ""))
    if not expected_state or expected_state != digest_payload(material):
        findings.append({"kind": "certification_state_digest_mismatch"})
    if str(pointer.get("state_sha256") or "") != expected_state or str(pointer.get("state_id") or "") != str(state.get("state_id") or "") or int(pointer.get("generation") or 0) != int(state.get("generation") or 0):
        findings.append({"kind": "certification_state_pointer_mismatch"})
    txid = str(state.get("certification_transaction_id") or "")
    receipt = read_json(certification_directory(runtime_root) / "receipts" / f"{txid}.json") if txid else {}
    if not receipt or not _receipt_valid(receipt) or str(receipt.get("receipt_sha256") or "") != str(state.get("certification_receipt_sha256") or ""):
        findings.append({"kind": "certification_receipt_invalid"})
    _, promotion_transaction = active_promotion_transaction_private(runtime_root)
    root = Path(str(promotion_transaction.get("target_root_path") or ""))
    inventory = _target_inventory(root) if root.is_dir() else {"ok": False, "digest": ""}
    if not inventory.get("ok") or str(inventory.get("digest") or "") != str(state.get("target_inventory_sha256") or ""):
        findings.append({"kind": "certification_target_inventory_drift"})
    for field in ("candidate_id", "archive_sha256", "installed_receipt_sha256", "promotion_receipt_sha256", "target_project_id", "target_inventory_sha256"):
        if str(state.get(field) or "") != str(promotion_status.get(field) or ""):
            findings.append({"kind": f"certification_{field}_drift"})
    status = str(state.get("state") or "certification_uncertain")
    current = {
        "ok": not findings,
        "status": status if not findings else "certification_stale",
        "certification_transaction_id": txid,
        "candidate_id": state.get("candidate_id"),
        "archive_sha256": state.get("archive_sha256"),
        "installed_receipt_sha256": state.get("installed_receipt_sha256"),
        "promotion_receipt_sha256": state.get("promotion_receipt_sha256"),
        "target_project_id": state.get("target_project_id"),
        "target_inventory_sha256": state.get("target_inventory_sha256"),
        "certification_scope": state.get("certification_scope"),
        "decision": state.get("decision"),
        "certification_receipt_sha256": state.get("certification_receipt_sha256"),
        "certification_state_sha256": state.get("state_sha256"),
        "generation": state.get("generation"),
        "certified_scopes": state.get("certified_scopes") or [],
        "contradictions": findings,
    }
    return _public(current)


def preview_certification_revocation(scope: str, *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    status = certification_status(runtime_root=runtime_root)
    _, state = _current_certification_state(runtime_root)
    certified_scopes = list(state.get("certified_scopes") or [])
    scope_receipt = str(dict(state.get("scope_receipts") or {}).get(scope) or "")
    if not status.get("ok") or scope not in certified_scopes or not scope_receipt:
        return _public({"status": "certification_revocation_blocked", "ok": False, "contradictions": [{"kind": "exact_certified_scope_required"}]})
    token_id = f"cert-revoke-{secrets.token_hex(8)}"
    nonce = secrets.token_hex(16)
    binding = digest_payload({
        "contract": "eidolon-certification-revocation-token-v1",
        "token_id": token_id,
        "scope": scope,
        "state_generation": int(state.get("generation") or 0),
        "state_sha256": str(state.get("state_sha256") or ""),
        "scope_receipt_sha256": scope_receipt,
        "candidate_id": str(state.get("candidate_id") or ""),
        "promotion_receipt_sha256": str(state.get("promotion_receipt_sha256") or ""),
        "target_inventory_sha256": str(state.get("target_inventory_sha256") or ""),
    })
    token = f"{token_id}.{binding}.{nonce}"
    atomic_json(certification_directory(runtime_root) / "revocation_authorizations" / f"{token_id}.json", {
        "schema": "eidolon-certification-revocation-authorization-v1",
        "token_id": token_id,
        "binding_sha256": binding,
        "nonce": nonce,
        "scope": scope,
        "state_generation": state["generation"],
        "state_sha256": state["state_sha256"],
        "scope_receipt_sha256": scope_receipt,
        "candidate_id": state["candidate_id"],
        "promotion_receipt_sha256": state["promotion_receipt_sha256"],
        "target_inventory_sha256": state["target_inventory_sha256"],
        "content_free": True,
    })
    current = dict(status)
    current.update({"status": "certification_revocation_previewed", "ok": True, "authorization_token": token, "literal_confirmation_required": CERTIFICATION_REVOCATION_CONFIRMATION, "certification_scope": scope})
    return _public(current)


def revoke_certification_scope(token: str, *, confirm: str, runtime_root: str | Path | None = None) -> dict[str, Any]:
    if confirm != CERTIFICATION_REVOCATION_CONFIRMATION:
        return _public({"status": "literal_confirmation_required", "ok": False, "contradictions": [{"kind": "literal_confirmation_required"}]})
    parts = token.split(".") if isinstance(token, str) else []
    if len(parts) != 3:
        return _public({"status": "revocation_token_invalid", "ok": False, "contradictions": [{"kind": "revocation_token_invalid"}]})
    directory = certification_directory(runtime_root)
    auth = read_json(directory / "revocation_authorizations" / f"{parts[0]}.json")
    if not auth or parts != [str(auth.get("token_id") or ""), str(auth.get("binding_sha256") or ""), str(auth.get("nonce") or "")]:
        return _public({"status": "revocation_token_invalid", "ok": False, "contradictions": [{"kind": "revocation_token_invalid"}]})
    if _used(runtime_root, token):
        return _public({"status": "authorization_reused", "ok": False, "contradictions": [{"kind": "authorization_reused"}]})
    status = certification_status(runtime_root=runtime_root)
    _, state = _current_certification_state(runtime_root)
    scope = str(auth.get("scope") or "")
    scope_receipt = str(dict(state.get("scope_receipts") or {}).get(scope) or "")
    for field, expected in (
        ("state_generation", state.get("generation")), ("state_sha256", state.get("state_sha256")),
        ("scope_receipt_sha256", scope_receipt), ("candidate_id", state.get("candidate_id")),
        ("promotion_receipt_sha256", state.get("promotion_receipt_sha256")), ("target_inventory_sha256", state.get("target_inventory_sha256")),
    ):
        if str(auth.get(field) or "") != str(expected or ""):
            return _public({"status": "revocation_token_stale", "ok": False, "contradictions": [{"kind": "revocation_token_stale"}]})
    if not status.get("ok") or scope not in list(state.get("certified_scopes") or []):
        return _public({"status": "certification_revocation_blocked", "ok": False, "contradictions": [{"kind": "exact_certified_scope_required"}]})
    txid = f"certification-revocation-{int(state.get('generation') or 0)+1}-{secrets.token_hex(8)}"
    _mark_used(runtime_root, token, "certification_scope_revoked", txid)
    receipt = {
        "schema": "eidolon-certification-revocation-receipt-v1",
        "revocation_transaction_id": txid,
        "scope": scope,
        "revoked_receipt_sha256": scope_receipt,
        "prior_state_generation": state["generation"],
        "prior_state_sha256": state["state_sha256"],
        "candidate_id": state["candidate_id"],
        "promotion_receipt_sha256": state["promotion_receipt_sha256"],
        "target_project_id": state["target_project_id"],
        "target_inventory_sha256": state["target_inventory_sha256"],
        "revoked_at": utc_now(),
        "content_free": True,
    }
    receipt["receipt_sha256"] = digest_payload(receipt)
    atomic_json(directory / "revocation_receipts" / f"{txid}.json", receipt)
    scopes = [item for item in list(state.get("certified_scopes") or []) if item != scope]
    scope_receipts = dict(state.get("scope_receipts") or {})
    scope_receipts.pop(scope, None)
    revoked = dict(state.get("revoked_scope_receipts") or {})
    revoked[scope] = scope_receipt
    new_state_name = "scope_certified" if len(scopes) == 1 else ("partially_certified" if len(scopes) > 1 else "certification_revoked")
    new_state = {
        "schema": "eidolon-certification-authority-state-v1",
        "state_id": f"certification-state-{int(state['generation'])+1}-{secrets.token_hex(6)}",
        "generation": int(state["generation"]) + 1,
        "state": new_state_name,
        "previous_state": state["state"],
        "previous_state_sha256": state["state_sha256"],
        "certification_transaction_id": str(state.get("certification_transaction_id") or ""),
        "certification_transaction_identity_sha256": str(state.get("certification_transaction_identity_sha256") or ""),
        "certification_receipt_sha256": str(state.get("certification_receipt_sha256") or ""),
        "revocation_receipt_sha256": receipt["receipt_sha256"],
        "certification_scope": scope,
        "decision": "revoked",
        "certified_scopes": sorted(scopes),
        "scope_receipts": scope_receipts,
        "revoked_scope_receipts": revoked,
        "candidate_id": state["candidate_id"],
        "archive_sha256": state["archive_sha256"],
        "installed_receipt_sha256": state["installed_receipt_sha256"],
        "promotion_receipt_sha256": state["promotion_receipt_sha256"],
        "target_project_id": state["target_project_id"],
        "target_inventory_sha256": state["target_inventory_sha256"],
        "created_at": utc_now(),
        "content_free": True,
    }
    new_state["state_sha256"] = digest_payload(new_state)
    atomic_json(directory / "states" / f"{new_state['state_id']}.json", new_state)
    atomic_json(directory / "active_certification_state.json", {"schema": "eidolon-certification-authority-state-v1", "state_id": new_state["state_id"], "generation": new_state["generation"], "state_sha256": new_state["state_sha256"], "state": new_state["state"], "content_free": True})
    _, promotion_transaction = active_promotion_transaction_private(runtime_root)
    _, promotion_state = current_promotion_state_private(runtime_root)
    pseudo_record = {
        "certification_transaction_id": txid,
        "promotion_transaction_id": str(promotion_transaction.get("promotion_transaction_id") or ""),
        "promotion_transaction_identity_sha256": str(promotion_transaction.get("promotion_transaction_identity_sha256") or ""),
        "promotion_receipt_sha256": str(state.get("promotion_receipt_sha256") or ""),
        "candidate_id": str(state.get("candidate_id") or ""),
        "packaged_version": str(promotion_transaction.get("packaged_version") or ""),
        "target_project_id": str(state.get("target_project_id") or ""),
        "target_inventory_sha256": str(state.get("target_inventory_sha256") or ""),
    }
    _promotion_authority_for_scopes(runtime_root, pseudo_record, scopes, receipt["receipt_sha256"], promotion_state)
    return _public({
        "ok": True,
        "status": new_state["state"],
        "certification_transaction_id": txid,
        "candidate_id": new_state["candidate_id"],
        "archive_sha256": new_state["archive_sha256"],
        "installed_receipt_sha256": new_state["installed_receipt_sha256"],
        "promotion_receipt_sha256": new_state["promotion_receipt_sha256"],
        "target_project_id": new_state["target_project_id"],
        "target_inventory_sha256": new_state["target_inventory_sha256"],
        "certification_scope": scope,
        "decision": "revoked",
        "revocation_receipt_sha256": receipt["receipt_sha256"],
        "certification_state_sha256": new_state["state_sha256"],
        "generation": new_state["generation"],
        "certified_scopes": scopes,
        "contradictions": [],
    })
