from __future__ import annotations

"""Immutable certification plan and exact single-use authorization preview."""

from collections import Counter
from pathlib import Path
import secrets
from typing import Any, Iterable, Mapping

try:
    from release_candidate_identity import atomic_json, digest_payload, read_json, utc_now
    from release_certification_evidence import active_certification_readiness_private, certification_directory, certification_readiness_status, _readiness_binding, _record_digest
except ImportError:
    from release_candidate_identity import atomic_json, digest_payload, read_json, utc_now
    from release_certification_evidence import active_certification_readiness_private, certification_directory, certification_readiness_status, _readiness_binding, _record_digest

CERTIFICATION_PLAN_CONTRACT_VERSION = "1"
CERTIFICATION_PLAN_SCHEMA = "eidolon-certification-plan-v1"
CERTIFICATION_AUTHORIZATION_SCHEMA = "eidolon-certification-authorization-v1"
CERTIFICATION_AUTHORIZATION_ACTION = "authorize_exact_certification_decision"
CERTIFICATION_AUTHORIZATION_CONFIRMATION = "AUTHORIZE EXACT CERTIFICATION DECISION"
DECISIONS = {"certified", "declined", "insufficient_evidence"}


def _counts(rows: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    found: Counter[str] = Counter()
    for row in rows or []:
        found[str(row.get("kind") or "unknown")] += max(1, int(row.get("count") or 1))
    return [{"kind": key, "count": found[key]} for key in sorted(found)]


def _current_certification_state(runtime_root: str | Path | None) -> tuple[dict[str, Any], dict[str, Any]]:
    directory = certification_directory(runtime_root)
    pointer = read_json(directory / "active_certification_state.json")
    state_id = str(pointer.get("state_id") or "")
    state = read_json(directory / "states" / f"{state_id}.json") if state_id else {}
    if state:
        return pointer, state
    initial = {
        "generation": 0,
        "state": "promoted_uncertified",
        "state_sha256": digest_payload({"contract": "eidolon-initial-certification-state-v1", "generation": 0, "state": "promoted_uncertified"}),
        "certified_scopes": [],
        "scope_receipts": {},
    }
    return {}, initial


def _plan_binding(record: Mapping[str, Any]) -> str:
    return digest_payload({
        "contract": "eidolon-certification-plan-binding-v1",
        "plan_id": str(record.get("plan_id") or ""),
        "generation": int(record.get("generation") or 0),
        "readiness_preview_id": str(record.get("readiness_preview_id") or ""),
        "readiness_generation": int(record.get("readiness_generation") or 0),
        "readiness_binding_sha256": str(record.get("readiness_binding_sha256") or ""),
        "readiness_record_sha256": str(record.get("readiness_record_sha256") or ""),
        "candidate_id": str(record.get("candidate_id") or ""),
        "archive_sha256": str(record.get("archive_sha256") or ""),
        "source_manifest_sha256": str(record.get("source_manifest_sha256") or ""),
        "archive_manifest_sha256": str(record.get("archive_manifest_sha256") or ""),
        "installed_transaction_id": str(record.get("installed_transaction_id") or ""),
        "installed_receipt_sha256": str(record.get("installed_receipt_sha256") or ""),
        "promotion_transaction_id": str(record.get("promotion_transaction_id") or ""),
        "promotion_transaction_identity_sha256": str(record.get("promotion_transaction_identity_sha256") or ""),
        "promotion_receipt_sha256": str(record.get("promotion_receipt_sha256") or ""),
        "target_project_id": str(record.get("target_project_id") or ""),
        "target_inventory_sha256": str(record.get("target_inventory_sha256") or ""),
        "promotion_state_generation": int(record.get("promotion_state_generation") or 0),
        "promotion_state_sha256": str(record.get("promotion_state_sha256") or ""),
        "evidence_set_sha256": str(record.get("evidence_set_sha256") or ""),
        "certification_scope": str(record.get("certification_scope") or ""),
        "decision_policy_sha256": str(record.get("decision_policy_sha256") or ""),
        "proposed_decision": str(record.get("proposed_decision") or ""),
        "proposed_authority_state": str(record.get("proposed_authority_state") or ""),
        "previous_certification_generation": int(record.get("previous_certification_generation") or 0),
        "previous_certification_state_sha256": str(record.get("previous_certification_state_sha256") or ""),
    })


def _authorization_binding(record: Mapping[str, Any]) -> str:
    return digest_payload({
        "contract": "eidolon-certification-authorization-binding-v1",
        "token_id": str(record.get("token_id") or ""),
        "action": str(record.get("action") or ""),
        "plan_id": str(record.get("plan_id") or ""),
        "plan_generation": int(record.get("plan_generation") or 0),
        "plan_binding_sha256": str(record.get("plan_binding_sha256") or ""),
        "plan_record_sha256": str(record.get("plan_record_sha256") or ""),
        "candidate_id": str(record.get("candidate_id") or ""),
        "archive_sha256": str(record.get("archive_sha256") or ""),
        "installed_receipt_sha256": str(record.get("installed_receipt_sha256") or ""),
        "promotion_receipt_sha256": str(record.get("promotion_receipt_sha256") or ""),
        "target_project_id": str(record.get("target_project_id") or ""),
        "target_inventory_sha256": str(record.get("target_inventory_sha256") or ""),
        "promotion_state_sha256": str(record.get("promotion_state_sha256") or ""),
        "evidence_set_sha256": str(record.get("evidence_set_sha256") or ""),
        "certification_scope": str(record.get("certification_scope") or ""),
        "proposed_decision": str(record.get("proposed_decision") or ""),
        "proposed_authority_state": str(record.get("proposed_authority_state") or ""),
        "previous_certification_generation": int(record.get("previous_certification_generation") or 0),
        "previous_certification_state_sha256": str(record.get("previous_certification_state_sha256") or ""),
    })


def _public(record: Mapping[str, Any] | None) -> dict[str, Any]:
    row = dict(record or {})
    contradictions = _counts(row.get("contradictions") if isinstance(row.get("contradictions"), list) else [])
    return {
        "ok": bool(row.get("ok")) and not contradictions,
        "status": str(row.get("status") or "not_planned"),
        "contract_version": CERTIFICATION_PLAN_CONTRACT_VERSION,
        "plan_present": bool(row),
        "plan_id": str(row.get("plan_id") or ""),
        "plan_binding_sha256": str(row.get("plan_binding_sha256") or ""),
        "generation": int(row.get("generation") or 0),
        "readiness_preview_id": str(row.get("readiness_preview_id") or ""),
        "candidate_id": str(row.get("candidate_id") or ""),
        "archive_sha256": str(row.get("archive_sha256") or ""),
        "installed_receipt_sha256": str(row.get("installed_receipt_sha256") or ""),
        "promotion_receipt_sha256": str(row.get("promotion_receipt_sha256") or ""),
        "target_project_id": str(row.get("target_project_id") or ""),
        "target_inventory_sha256": str(row.get("target_inventory_sha256") or ""),
        "evidence_set_sha256": str(row.get("evidence_set_sha256") or ""),
        "evidence_count": len(row.get("evidence_set") or []),
        "certification_scope": str(row.get("certification_scope") or ""),
        "proposed_decision": str(row.get("proposed_decision") or ""),
        "proposed_authority_state": str(row.get("proposed_authority_state") or ""),
        "previous_certification_generation": int(row.get("previous_certification_generation") or 0),
        "authorization_token": str(row.get("authorization_token") or ""),
        "literal_confirmation_required": CERTIFICATION_AUTHORIZATION_CONFIRMATION,
        "contradictions": contradictions,
        "contradiction_count": sum(int(item["count"]) for item in contradictions),
        "certification_applied": False,
        "certified": False,
        "source_files_mutated": False,
        "paths_suppressed": True,
        "records_external": True,
        "content_free": True,
        "provider_contacted": False,
        "ordinary_conversation_affected": False,
    }


def create_certification_plan(
    proposed_decision: str = "auto",
    *,
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    status = certification_readiness_status(runtime_root=runtime_root)
    pointer, readiness = active_certification_readiness_private(runtime_root)
    findings: list[dict[str, Any]] = []
    if not readiness or not status.get("ok") or str(status.get("status") or "") not in {"certification_ready", "certification_not_ready"}:
        findings.append({"kind": "coherent_certification_readiness_required"})
    if readiness and str(readiness.get("preview_binding_sha256") or "") != _readiness_binding(readiness):
        findings.append({"kind": "certification_readiness_binding_invalid"})
    ready = bool(status.get("ready"))
    decision = "certified" if proposed_decision == "auto" and ready else ("insufficient_evidence" if proposed_decision == "auto" else proposed_decision)
    if decision not in DECISIONS:
        findings.append({"kind": "unsupported_certification_decision"})
    if decision == "certified" and not ready:
        findings.append({"kind": "insufficient_evidence_cannot_certify"})
    if decision == "insufficient_evidence" and ready:
        findings.append({"kind": "insufficient_evidence_decision_mismatches_ready_preview"})
    directory = certification_directory(runtime_root)
    if findings:
        failed = {"status": "certification_plan_blocked", "ok": False, "contradictions": findings}
        atomic_json(directory / "last_failed_plan.json", failed)
        return _public(failed)
    active = read_json(directory / "active_plan.json")
    generation = int(active.get("generation") or 0) + 1
    _, previous_state = _current_certification_state(runtime_root)
    evidence_set = sorted(list(readiness.get("satisfied_evidence") or []), key=lambda item: (str(item.get("scope") or ""), str(item.get("artifact_sha256") or "")))
    authority_state = "scope_certified" if decision == "certified" else ("certification_declined" if decision == "declined" else "insufficient_evidence")
    record = {
        "schema": CERTIFICATION_PLAN_SCHEMA,
        "plan_id": f"cert-plan-{generation}-{secrets.token_hex(8)}",
        "generation": generation,
        "created_at": utc_now(),
        "status": "certification_planned",
        "ok": True,
        "readiness_preview_id": readiness["preview_id"],
        "readiness_generation": readiness["generation"],
        "readiness_binding_sha256": readiness["preview_binding_sha256"],
        "readiness_record_sha256": readiness["record_sha256"],
        "candidate_id": readiness["candidate_id"],
        "packaged_version": readiness["packaged_version"],
        "archive_sha256": readiness["archive_sha256"],
        "source_manifest_sha256": readiness["source_manifest_sha256"],
        "archive_manifest_sha256": readiness["archive_manifest_sha256"],
        "installed_transaction_id": readiness["installed_transaction_id"],
        "installed_receipt_sha256": readiness["installed_receipt_sha256"],
        "promotion_transaction_id": readiness["promotion_transaction_id"],
        "promotion_transaction_identity_sha256": readiness["promotion_transaction_identity_sha256"],
        "promotion_receipt_sha256": readiness["promotion_receipt_sha256"],
        "target_project_id": readiness["target_project_id"],
        "target_inventory_sha256": readiness["target_inventory_sha256"],
        "promotion_state_generation": readiness["promotion_state_generation"],
        "promotion_state_sha256": readiness["promotion_state_sha256"],
        "evidence_set": evidence_set,
        "evidence_set_sha256": digest_payload(evidence_set),
        "certification_scope": readiness["certification_scope"],
        "decision_policy": readiness["decision_policy"],
        "decision_policy_sha256": readiness["decision_policy_sha256"],
        "proposed_decision": decision,
        "proposed_authority_state": authority_state,
        "previous_certification_generation": int(previous_state.get("generation") or 0),
        "previous_certification_state_sha256": str(previous_state.get("state_sha256") or ""),
        "contradictions": [],
    }
    record["plan_binding_sha256"] = _plan_binding(record)
    record["record_sha256"] = _record_digest(record)
    atomic_json(directory / "plans" / f"{record['plan_id']}.json", record)
    atomic_json(directory / "active_plan.json", {
        "schema": CERTIFICATION_PLAN_SCHEMA,
        "plan_id": record["plan_id"],
        "generation": generation,
        "plan_binding_sha256": record["plan_binding_sha256"],
        "record_sha256": record["record_sha256"],
        "certification_scope": record["certification_scope"],
        "proposed_decision": decision,
        "content_free": True,
    })
    return _public(record)


def active_certification_plan_private(runtime_root: str | Path | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    directory = certification_directory(runtime_root)
    pointer = read_json(directory / "active_plan.json")
    plan_id = str(pointer.get("plan_id") or "")
    return pointer, read_json(directory / "plans" / f"{plan_id}.json") if plan_id else {}


def certification_plan_status(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    pointer, record = active_certification_plan_private(runtime_root)
    if not record:
        return _public({})
    findings: list[dict[str, Any]] = []
    if str(record.get("record_sha256") or "") != _record_digest(record):
        findings.append({"kind": "certification_plan_record_digest_mismatch"})
    if str(record.get("plan_binding_sha256") or "") != _plan_binding(record):
        findings.append({"kind": "certification_plan_binding_mismatch"})
    for field in ("plan_id", "generation", "plan_binding_sha256", "record_sha256", "certification_scope", "proposed_decision"):
        if str(pointer.get(field) or "") != str(record.get(field) or ""):
            findings.append({"kind": f"certification_plan_pointer_{field}_mismatch"})
    readiness_status = certification_readiness_status(runtime_root=runtime_root)
    _, readiness = active_certification_readiness_private(runtime_root)
    if not readiness_status.get("ok") or not readiness:
        findings.append({"kind": "certification_readiness_stale"})
    for field in (
        "candidate_id", "archive_sha256", "source_manifest_sha256", "archive_manifest_sha256",
        "installed_receipt_sha256", "promotion_receipt_sha256", "target_project_id", "target_inventory_sha256",
        "promotion_state_sha256", "certification_scope", "decision_policy_sha256",
    ):
        if str(record.get(field) or "") != str(readiness.get(field) or ""):
            findings.append({"kind": f"certification_plan_{field}_drift"})
    if int(record.get("promotion_state_generation") or 0) != int(readiness.get("promotion_state_generation") or 0):
        findings.append({"kind": "certification_plan_promotion_generation_drift"})
    if str(record.get("evidence_set_sha256") or "") != digest_payload(sorted(list(readiness.get("satisfied_evidence") or []), key=lambda item: (str(item.get("scope") or ""), str(item.get("artifact_sha256") or "")))):
        findings.append({"kind": "certification_plan_evidence_drift"})
    _, current_state = _current_certification_state(runtime_root)
    if int(record.get("previous_certification_generation") or 0) != int(current_state.get("generation") or 0) or str(record.get("previous_certification_state_sha256") or "") != str(current_state.get("state_sha256") or ""):
        findings.append({"kind": "certification_authority_state_drift"})
    current = dict(record)
    current["contradictions"] = findings
    current["ok"] = not findings
    current["status"] = "certification_planned" if not findings else "certification_plan_stale"
    return _public(current)


def preview_certification_authorization(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    status = certification_plan_status(runtime_root=runtime_root)
    _, plan = active_certification_plan_private(runtime_root)
    if not status.get("ok") or not plan:
        return _public({"status": "certification_authorization_blocked", "ok": False, "contradictions": [{"kind": "coherent_certification_plan_required"}]})
    token_id = f"cert-auth-{secrets.token_hex(8)}"
    nonce = secrets.token_hex(16)
    record = {
        "schema": CERTIFICATION_AUTHORIZATION_SCHEMA,
        "token_id": token_id,
        "nonce": nonce,
        "action": CERTIFICATION_AUTHORIZATION_ACTION,
        "created_at": utc_now(),
        "plan_id": plan["plan_id"],
        "plan_generation": plan["generation"],
        "plan_binding_sha256": plan["plan_binding_sha256"],
        "plan_record_sha256": plan["record_sha256"],
        "candidate_id": plan["candidate_id"],
        "archive_sha256": plan["archive_sha256"],
        "installed_receipt_sha256": plan["installed_receipt_sha256"],
        "promotion_receipt_sha256": plan["promotion_receipt_sha256"],
        "target_project_id": plan["target_project_id"],
        "target_inventory_sha256": plan["target_inventory_sha256"],
        "promotion_state_sha256": plan["promotion_state_sha256"],
        "evidence_set_sha256": plan["evidence_set_sha256"],
        "certification_scope": plan["certification_scope"],
        "proposed_decision": plan["proposed_decision"],
        "proposed_authority_state": plan["proposed_authority_state"],
        "previous_certification_generation": plan["previous_certification_generation"],
        "previous_certification_state_sha256": plan["previous_certification_state_sha256"],
        "content_free": True,
    }
    record["authorization_binding_sha256"] = _authorization_binding(record)
    token = f"{token_id}.{record['authorization_binding_sha256']}.{nonce}"
    atomic_json(certification_directory(runtime_root) / "authorizations" / f"{token_id}.json", record)
    output = dict(plan)
    output.update({"authorization_token": token, "status": "certification_authorization_previewed", "ok": True})
    return _public(output)


def certification_authorization_valid(token: str, runtime_root: str | Path | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    parts = token.split(".") if isinstance(token, str) else []
    if len(parts) != 3:
        return {}, [{"kind": "certification_authorization_token_malformed"}]
    auth = read_json(certification_directory(runtime_root) / "authorizations" / f"{parts[0]}.json")
    if not auth or parts != [str(auth.get("token_id") or ""), str(auth.get("authorization_binding_sha256") or ""), str(auth.get("nonce") or "")]:
        return auth, [{"kind": "certification_authorization_token_mismatched"}]
    if str(auth.get("authorization_binding_sha256") or "") != _authorization_binding(auth):
        findings.append({"kind": "certification_authorization_binding_invalid"})
    status = certification_plan_status(runtime_root=runtime_root)
    _, plan = active_certification_plan_private(runtime_root)
    if not status.get("ok") or not plan:
        findings.append({"kind": "certification_plan_stale"})
    comparisons = {
        "plan_id": plan.get("plan_id"), "plan_generation": plan.get("generation"),
        "plan_binding_sha256": plan.get("plan_binding_sha256"), "plan_record_sha256": plan.get("record_sha256"),
        "candidate_id": plan.get("candidate_id"), "archive_sha256": plan.get("archive_sha256"),
        "installed_receipt_sha256": plan.get("installed_receipt_sha256"), "promotion_receipt_sha256": plan.get("promotion_receipt_sha256"),
        "target_project_id": plan.get("target_project_id"), "target_inventory_sha256": plan.get("target_inventory_sha256"),
        "promotion_state_sha256": plan.get("promotion_state_sha256"), "evidence_set_sha256": plan.get("evidence_set_sha256"),
        "certification_scope": plan.get("certification_scope"), "proposed_decision": plan.get("proposed_decision"),
        "proposed_authority_state": plan.get("proposed_authority_state"), "previous_certification_generation": plan.get("previous_certification_generation"),
        "previous_certification_state_sha256": plan.get("previous_certification_state_sha256"),
    }
    for field, expected in comparisons.items():
        if str(auth.get(field) or "") != str(expected or ""):
            findings.append({"kind": f"certification_authorization_{field}_mismatch"})
    return auth, findings
