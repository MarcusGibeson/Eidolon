from __future__ import annotations

"""Preview-first recovery for interrupted certification decisions.

Recovery is limited to exact external transaction records. It never reruns checks,
contacts providers, mutates models, or creates certification from inference.
"""

from collections import Counter
import json
from pathlib import Path
import secrets
from typing import Any, Iterable, Mapping

try:
    from release_candidate_identity import atomic_json, digest_payload, read_json, utc_now
    from release_certification_evidence import certification_directory
    from release_certification_plan import active_certification_plan_private, certification_plan_status
    from release_certification_transaction import _append_event, _complete_certification_decision, _mark_used, _receipt_valid, _save, _record_digest, _state_digest, _transaction_binding, _used, active_certification_transaction_private
    from release_installation_preview import _target_inventory
    from release_promotion_transaction import active_promotion_transaction_private, promotion_transaction_status
except ImportError:
    from release_candidate_identity import atomic_json, digest_payload, read_json, utc_now
    from release_certification_evidence import certification_directory
    from release_certification_plan import active_certification_plan_private, certification_plan_status
    from release_certification_transaction import _append_event, _complete_certification_decision, _mark_used, _receipt_valid, _save, _record_digest, _state_digest, _transaction_binding, _used, active_certification_transaction_private
    from release_installation_preview import _target_inventory
    from release_promotion_transaction import active_promotion_transaction_private, promotion_transaction_status

CERTIFICATION_RECOVERY_CONTRACT_VERSION = "1"
CERTIFICATION_RECOVERY_SCHEMA = "eidolon-certification-recovery-preview-v1"
CERTIFICATION_RECOVERY_CONFIRMATION = "RESUME EXACT CERTIFICATION DECISION"
CERTIFICATION_RECOVERY_ACTION = "resume_exact_certification_decision"
COMPLETED_STATES = {"scope_certified", "partially_certified", "certified", "certification_declined", "insufficient_evidence"}


def _counts(rows: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    found: Counter[str] = Counter()
    for row in rows or []:
        found[str(row.get("kind") or "unknown")] += max(1, int(row.get("count") or 1))
    return [{"kind": key, "count": found[key]} for key in sorted(found)]


def _public(row: Mapping[str, Any] | None) -> dict[str, Any]:
    record = dict(row or {})
    contradictions = _counts(record.get("contradictions") if isinstance(record.get("contradictions"), list) else [])
    status = str(record.get("status") or "no_certification_transaction")
    return {
        "ok": bool(record.get("ok")) and not contradictions,
        "status": status,
        "contract_version": CERTIFICATION_RECOVERY_CONTRACT_VERSION,
        "certification_transaction_id": str(record.get("certification_transaction_id") or ""),
        "generation": int(record.get("generation") or 0),
        "certification_scope": str(record.get("certification_scope") or ""),
        "decision": str(record.get("decision") or ""),
        "candidate_id": str(record.get("candidate_id") or ""),
        "archive_sha256": str(record.get("archive_sha256") or ""),
        "installed_receipt_sha256": str(record.get("installed_receipt_sha256") or ""),
        "promotion_receipt_sha256": str(record.get("promotion_receipt_sha256") or ""),
        "evidence_set_sha256": str(record.get("evidence_set_sha256") or ""),
        "certification_transaction_identity_sha256": str(record.get("certification_transaction_identity_sha256") or ""),
        "certification_transaction_state_sha256": str(record.get("certification_transaction_state_sha256") or ""),
        "completed_steps": list(record.get("completed_steps") or []),
        "remaining_steps": list(record.get("remaining_steps") or []),
        "recovery_available": bool(record.get("recovery_available")) and not contradictions,
        "authorization_token": str(record.get("authorization_token") or ""),
        "literal_confirmation_required": str(record.get("literal_confirmation_required") or CERTIFICATION_RECOVERY_CONFIRMATION),
        "contradictions": contradictions,
        "contradiction_count": sum(int(item["count"]) for item in contradictions),
        "completed_decision_replayable": False,
        "native_checks_rerun": False,
        "provider_contacted": False,
        "models_mutated": False,
        "source_files_mutated": False,
        "paths_suppressed": True,
        "records_external": True,
        "content_free": True,
        "ordinary_conversation_affected": False,
    }


def _steps(record: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    ordered = ["start_event", "receipt", "scope_state"]
    if str(record.get("decision") or "") == "certified":
        ordered.append("promotion_authority")
    ordered.append("finalization")
    flags = {
        "start_event": bool(record.get("start_event_persisted")),
        "receipt": bool(record.get("receipt_persisted") or record.get("certification_receipt_sha256")),
        "scope_state": bool(record.get("scope_state_persisted") or record.get("certification_state_sha256")),
        "promotion_authority": bool(record.get("promotion_authority_persisted") or record.get("promotion_authority_state_sha256")),
        "finalization": bool(record.get("decision_finalized")) or str(record.get("state") or "") in COMPLETED_STATES,
    }
    return [step for step in ordered if flags.get(step)], [step for step in ordered if not flags.get(step)]


def _event_findings(runtime_root: str | Path | None, record: Mapping[str, Any]) -> list[dict[str, Any]]:
    path = certification_directory(runtime_root) / "events" / f"{record.get('certification_transaction_id','')}.jsonl"
    if not path.is_file():
        return [] if not record.get("start_event_persisted") else [{"kind": "certification_event_log_missing"}]
    try:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except Exception:
        return [{"kind": "certification_event_log_malformed"}]
    seq = [int(row.get("sequence") or 0) for row in rows]
    if seq != list(range(1, len(rows) + 1)) or (seq and seq[-1] != int(record.get("event_sequence") or 0)):
        return [{"kind": "certification_event_sequence_contradictory"}]
    return []


def certification_recovery_status(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    pointer, record = active_certification_transaction_private(runtime_root)
    if not record:
        return _public({"ok": True, "status": "no_certification_transaction"})
    findings: list[dict[str, Any]] = []
    if str(record.get("record_sha256") or "") != _record_digest(record):
        findings.append({"kind": "certification_transaction_record_digest_mismatch"})
    if str(record.get("certification_transaction_identity_sha256") or "") != _transaction_binding(record):
        findings.append({"kind": "certification_transaction_identity_mismatch"})
    if str(record.get("certification_transaction_state_sha256") or "") != _state_digest(record):
        findings.append({"kind": "certification_transaction_state_digest_mismatch"})
    for field in ("certification_transaction_id", "generation", "certification_transaction_identity_sha256", "certification_transaction_state_sha256", "record_sha256"):
        if str(pointer.get(field) or "") != str(record.get(field) or ""):
            findings.append({"kind": f"certification_transaction_pointer_{field}_mismatch"})
    findings.extend(_event_findings(runtime_root, record))

    plan_status = certification_plan_status(runtime_root=runtime_root)
    _, plan = active_certification_plan_private(runtime_root)
    if not plan or str(plan.get("plan_id") or "") != str(record.get("plan_id") or ""):
        findings.append({"kind": "certification_recovery_plan_missing_or_mismatched"})
    for field in ("candidate_id", "archive_sha256", "installed_receipt_sha256", "promotion_receipt_sha256", "target_project_id", "target_inventory_sha256", "evidence_set_sha256", "certification_scope", "decision"):
        if plan and str(plan.get(field if field != "decision" else "proposed_decision") or "") != str(record.get(field) or ""):
            findings.append({"kind": f"certification_recovery_{field}_mismatch"})

    promotion = promotion_transaction_status(runtime_root=runtime_root)
    _, promotion_private = active_promotion_transaction_private(runtime_root)
    root = Path(str(promotion_private.get("target_root_path") or ""))
    inventory = _target_inventory(root) if root.is_dir() else {"ok": False, "digest": ""}
    if not inventory.get("ok") or str(inventory.get("digest") or "") != str(record.get("target_inventory_sha256") or ""):
        findings.append({"kind": "certification_recovery_target_inventory_drift"})
    for field in ("candidate_id", "archive_sha256", "installed_receipt_sha256", "promotion_receipt_sha256", "target_project_id", "target_inventory_sha256"):
        if str(promotion.get(field) or "") != str(record.get(field) or ""):
            findings.append({"kind": f"certification_recovery_promotion_{field}_mismatch"})

    directory = certification_directory(runtime_root)
    txid = str(record.get("certification_transaction_id") or "")
    receipt = read_json(directory / "receipts" / f"{txid}.json") if txid else {}
    if record.get("certification_receipt_sha256"):
        if not receipt or not _receipt_valid(receipt) or str(receipt.get("receipt_sha256") or "") != str(record.get("certification_receipt_sha256") or ""):
            findings.append({"kind": "certification_recovery_receipt_corrupt_or_missing"})
    state_id = str(record.get("certification_state_id") or "")
    state = read_json(directory / "states" / f"{state_id}.json") if state_id else {}
    if record.get("certification_state_sha256"):
        material = dict(state); expected = str(material.pop("state_sha256", ""))
        if not state or expected != digest_payload(material) or expected != str(record.get("certification_state_sha256") or ""):
            findings.append({"kind": "certification_recovery_authority_state_corrupt_or_missing"})

    completed, remaining = _steps(record)
    state_name = str(record.get("state") or "")
    completed_decision = state_name in COMPLETED_STATES and not remaining
    interrupted = state_name in {"certification_interrupted", "recording_certification_decision"} or bool(remaining)
    status = "certification_decision_complete" if completed_decision else ("certification_recovery_ready" if interrupted and not findings else "certification_recovery_uncertain")
    current = dict(record)
    current.update({"ok": not findings, "status": status, "completed_steps": completed, "remaining_steps": remaining, "recovery_available": interrupted and not findings and not completed_decision, "contradictions": findings})
    return _public(current)


def _recovery_binding(record: Mapping[str, Any]) -> str:
    return digest_payload({
        "contract": "eidolon-certification-recovery-authorization-v1",
        "token_id": str(record.get("token_id") or ""),
        "action": CERTIFICATION_RECOVERY_ACTION,
        "certification_transaction_id": str(record.get("certification_transaction_id") or ""),
        "generation": int(record.get("generation") or 0),
        "identity_sha256": str(record.get("certification_transaction_identity_sha256") or ""),
        "state_sha256": str(record.get("certification_transaction_state_sha256") or ""),
        "completed_steps_sha256": str(record.get("completed_steps_sha256") or ""),
        "remaining_steps_sha256": str(record.get("remaining_steps_sha256") or ""),
        "receipt_sha256": str(record.get("certification_receipt_sha256") or ""),
        "authority_state_sha256": str(record.get("certification_state_sha256") or ""),
        "candidate_id": str(record.get("candidate_id") or ""),
        "plan_id": str(record.get("plan_id") or ""),
        "scope": str(record.get("certification_scope") or ""),
        "evidence_set_sha256": str(record.get("evidence_set_sha256") or ""),
    })


def preview_certification_recovery(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    status = certification_recovery_status(runtime_root=runtime_root)
    _, record = active_certification_transaction_private(runtime_root)
    if not status.get("recovery_available") or not record:
        return _public({"ok": False, "status": "certification_recovery_blocked", "contradictions": status.get("contradictions") or [{"kind": "exact_interrupted_certification_required"}]})
    token_id = f"cert-recovery-{secrets.token_hex(8)}"
    nonce = secrets.token_hex(16)
    auth = {
        "schema": "eidolon-certification-recovery-authorization-v1", "token_id": token_id,
        "nonce": nonce, "action": CERTIFICATION_RECOVERY_ACTION,
        "certification_transaction_id": record["certification_transaction_id"], "generation": record["generation"],
        "certification_transaction_identity_sha256": record["certification_transaction_identity_sha256"],
        "certification_transaction_state_sha256": record["certification_transaction_state_sha256"],
        "completed_steps_sha256": digest_payload(status.get("completed_steps") or []),
        "remaining_steps_sha256": digest_payload(status.get("remaining_steps") or []),
        "certification_receipt_sha256": str(record.get("certification_receipt_sha256") or ""),
        "certification_state_sha256": str(record.get("certification_state_sha256") or ""),
        "candidate_id": record["candidate_id"], "plan_id": record["plan_id"],
        "certification_scope": record["certification_scope"], "evidence_set_sha256": record["evidence_set_sha256"],
        "content_free": True,
    }
    auth["binding_sha256"] = _recovery_binding(auth)
    atomic_json(certification_directory(runtime_root) / "recovery_authorizations" / f"{token_id}.json", auth)
    token = f"{token_id}.{auth['binding_sha256']}.{nonce}"
    current = dict(record)
    current.update({"ok": True, "status": "certification_recovery_previewed", "completed_steps": status.get("completed_steps"), "remaining_steps": status.get("remaining_steps"), "recovery_available": True, "authorization_token": token, "literal_confirmation_required": CERTIFICATION_RECOVERY_CONFIRMATION, "contradictions": []})
    return _public(current)


def resume_certification_decision(token: str, *, confirm: str, runtime_root: str | Path | None = None) -> dict[str, Any]:
    if confirm != CERTIFICATION_RECOVERY_CONFIRMATION:
        return _public({"ok": False, "status": "literal_confirmation_required", "contradictions": [{"kind": "literal_confirmation_required"}]})
    parts = token.split(".") if isinstance(token, str) else []
    if len(parts) != 3:
        return _public({"ok": False, "status": "recovery_token_invalid", "contradictions": [{"kind": "recovery_token_invalid"}]})
    auth = read_json(certification_directory(runtime_root) / "recovery_authorizations" / f"{parts[0]}.json")
    if not auth or parts != [str(auth.get("token_id") or ""), str(auth.get("binding_sha256") or ""), str(auth.get("nonce") or "")] or str(auth.get("binding_sha256") or "") != _recovery_binding(auth):
        return _public({"ok": False, "status": "recovery_token_invalid", "contradictions": [{"kind": "recovery_token_invalid"}]})
    if _used(runtime_root, token):
        return _public({"ok": False, "status": "authorization_reused", "contradictions": [{"kind": "authorization_reused"}]})
    status = certification_recovery_status(runtime_root=runtime_root)
    _, record = active_certification_transaction_private(runtime_root)
    expected = {
        "certification_transaction_id": record.get("certification_transaction_id"), "generation": record.get("generation"),
        "certification_transaction_identity_sha256": record.get("certification_transaction_identity_sha256"),
        "certification_transaction_state_sha256": record.get("certification_transaction_state_sha256"),
        "completed_steps_sha256": digest_payload(status.get("completed_steps") or []),
        "remaining_steps_sha256": digest_payload(status.get("remaining_steps") or []),
        "certification_receipt_sha256": record.get("certification_receipt_sha256"),
        "certification_state_sha256": record.get("certification_state_sha256"), "candidate_id": record.get("candidate_id"),
        "plan_id": record.get("plan_id"), "certification_scope": record.get("certification_scope"),
        "evidence_set_sha256": record.get("evidence_set_sha256"),
    }
    for field, value in expected.items():
        if str(auth.get(field) or "") != str(value or ""):
            return _public({"ok": False, "status": "recovery_token_stale", "contradictions": [{"kind": f"recovery_token_{field}_mismatch"}]})
    if not status.get("recovery_available"):
        return _public({"ok": False, "status": "certification_recovery_blocked", "contradictions": status.get("contradictions") or [{"kind": "recovery_no_longer_available"}]})
    _mark_used(runtime_root, token, "certification_recovery_started", record["certification_transaction_id"])
    if not record.get("start_event_persisted"):
        _append_event(runtime_root, record["certification_transaction_id"], record, {"kind": "certification_decision_started", "decision": record["decision"], "scope": record["certification_scope"], "recovered": True})
        record["start_event_persisted"] = True
    record["state"] = record["status"] = "recording_certification_decision"
    record["interrupted_after"] = ""
    _append_event(runtime_root, record["certification_transaction_id"], record, {"kind": "certification_recovery_started"})
    _save(runtime_root, record)
    completed = _complete_certification_decision(runtime_root, record)
    result = certification_recovery_status(runtime_root=runtime_root)
    if str(completed.get("state") or "") in COMPLETED_STATES and result.get("status") == "certification_decision_complete":
        result["status"] = str(completed.get("state") or "")
        result["ok"] = True
    return result
