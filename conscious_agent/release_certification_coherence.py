from __future__ import annotations

"""Bounded certification daily-use and release-authority coherence status."""

from collections import Counter
from pathlib import Path
import secrets
from typing import Any, Iterable, Mapping

try:
    from release_candidate_identity import atomic_json, digest_payload, read_json, utc_now
    from release_certification_evidence import certification_directory, certification_readiness_status
    from release_certification_plan import certification_plan_status
    from release_certification_transaction import certification_status
    from release_certification_recovery import certification_recovery_status
    from release_certification_freshness import evidence_freshness_status, recertification_readiness_status
    from release_installed_state import installed_state_status
    from release_promotion_transaction import promotion_transaction_status
except ImportError:
    from release_candidate_identity import atomic_json, digest_payload, read_json, utc_now
    from release_certification_evidence import certification_directory, certification_readiness_status
    from release_certification_plan import certification_plan_status
    from release_certification_transaction import certification_status
    from release_certification_recovery import certification_recovery_status
    from release_certification_freshness import evidence_freshness_status, recertification_readiness_status
    from release_installed_state import installed_state_status
    from release_promotion_transaction import promotion_transaction_status

CERTIFICATION_COHERENCE_CONTRACT_VERSION = "1"
OPERATION_CLAIM_CONFIRMATION = "CLAIM EXACT CERTIFICATION OPERATION"
OPERATION_RELEASE_CONFIRMATION = "RELEASE EXACT CERTIFICATION OPERATION"
ALLOWED_OPERATIONS = {"decision_recovery", "evidence_replacement", "recertification_preview", "certification_decision", "history_reconciliation", "policy_selection", "policy_migration_preview", "release_authority_readiness_preview", "release_authority_readiness_refresh", "release_authority_readiness_recovery", "release_authority_readiness_replacement", "release_authority_readiness_cleanup", "release_authority_handoff_plan", "release_authority_handoff_acknowledgment", "release_authority_handoff_acknowledgment_recovery", "release_authority_handoff_acknowledgment_replacement", "release_authority_handoff_acknowledgment_cleanup", "release_authority_consumer_validation", "release_authority_consumer_receipt"}


def _counts(rows: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    found: Counter[str] = Counter()
    for row in rows or []:
        found[str(row.get("kind") or "unknown")] += max(1, int(row.get("count") or 1))
    return [{"kind": key, "count": found[key]} for key in sorted(found)]


def _owner_digest(record: Mapping[str, Any]) -> str:
    return digest_payload({
        "contract": "eidolon-certification-operation-owner-v1",
        "generation": int(record.get("generation") or 0), "operation": str(record.get("operation") or ""),
        "tab_digest": str(record.get("tab_digest") or ""), "revision": int(record.get("revision") or 0),
        "claimed_at": str(record.get("claimed_at") or ""),
    })


def _public(row: Mapping[str, Any] | None) -> dict[str, Any]:
    record = dict(row or {})
    contradictions = _counts(record.get("contradictions") if isinstance(record.get("contradictions"), list) else [])
    return {
        "ok": bool(record.get("ok")) and not contradictions,
        "status": str(record.get("status") or "certification_coherence_unavailable"),
        "contract_version": CERTIFICATION_COHERENCE_CONTRACT_VERSION,
        "authority_status": str(record.get("authority_status") or ""),
        "recovery_status": str(record.get("recovery_status") or ""),
        "freshness_status": str(record.get("freshness_status") or ""),
        "recertification_status": str(record.get("recertification_status") or ""),
        "installed_status": str(record.get("installed_status") or ""),
        "promotion_status": str(record.get("promotion_status") or ""),
        "certified_scopes": list(record.get("certified_scopes") or []),
        "fresh_scopes": list(record.get("fresh_scopes") or []),
        "expired_scopes": list(record.get("expired_scopes") or []),
        "recovery_available": bool(record.get("recovery_available")),
        "recertification_required": bool(record.get("recertification_required")),
        "operation_owner_present": bool(record.get("operation_owner_present")),
        "operation": str(record.get("operation") or ""),
        "operation_generation": int(record.get("operation_generation") or 0),
        "operation_revision": int(record.get("operation_revision") or 0),
        "authorization_token": str(record.get("authorization_token") or ""),
        "literal_confirmation_required": str(record.get("literal_confirmation_required") or ""),
        "contradictions": contradictions,
        "contradiction_count": sum(int(item["count"]) for item in contradictions),
        "duplicate_execution_allowed": False,
        "installation_inferred": False,
        "promotion_inferred": False,
        "certification_inferred": False,
        "native_windows_inferred": False,
        "provider_ollama_inferred": False,
        "model_certification_inferred": False,
        "paths_suppressed": True,
        "records_external": True,
        "content_free": True,
        "provider_contacted": False,
        "ordinary_conversation_affected": False,
    }


def _owner(runtime_root: str | Path | None) -> dict[str, Any]:
    row = read_json(certification_directory(runtime_root) / "active_operation_owner.json")
    if not row:
        return {}
    if str(row.get("owner_sha256") or "") != _owner_digest(row):
        return {**row, "invalid": True}
    return row


def certification_coherence_status(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    authority = certification_status(runtime_root=runtime_root)
    recovery = certification_recovery_status(runtime_root=runtime_root)
    freshness = evidence_freshness_status(runtime_root=runtime_root)
    recertification = recertification_readiness_status(runtime_root=runtime_root)
    installed = installed_state_status(runtime_root=runtime_root)
    promotion = promotion_transaction_status(runtime_root=runtime_root)
    owner = _owner(runtime_root)
    findings: list[dict[str, Any]] = []
    if owner.get("invalid"):
        findings.append({"kind": "certification_operation_owner_digest_mismatch"})
    if authority.get("general_release_certified") and "general_release" not in list(authority.get("certified_scopes") or []):
        findings.append({"kind": "general_release_authority_contradictory"})
    if "native_windows" in list(authority.get("certified_scopes") or []) and "general_release" not in list(authority.get("certified_scopes") or []):
        pass  # scopes are intentionally independent
    status = "certification_daily_use_coherent" if not findings else "certification_daily_use_contradictory"
    return _public({
        "ok": not findings, "status": status, "authority_status": authority.get("status"),
        "recovery_status": recovery.get("status"), "freshness_status": freshness.get("status"),
        "recertification_status": recertification.get("status"), "installed_status": installed.get("status"),
        "promotion_status": promotion.get("status"), "certified_scopes": authority.get("certified_scopes") or [],
        "fresh_scopes": freshness.get("fresh_scopes") or [], "expired_scopes": freshness.get("expired_scopes") or [],
        "recovery_available": recovery.get("recovery_available"), "recertification_required": recertification.get("recertification_required"),
        "operation_owner_present": bool(owner and not owner.get("invalid")), "operation": owner.get("operation"),
        "operation_generation": owner.get("generation"), "operation_revision": owner.get("revision"), "contradictions": findings,
    })


def preview_operation_claim(operation: str, tab_id: str, revision: int, *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    if operation not in ALLOWED_OPERATIONS or not tab_id or int(revision) < 1:
        return _public({"ok": False, "status": "operation_claim_blocked", "contradictions": [{"kind": "valid_operation_tab_and_revision_required"}]})
    owner = _owner(runtime_root)
    tab_digest = digest_payload({"tab_id": tab_id})
    if owner and not owner.get("invalid") and str(owner.get("tab_digest") or "") != tab_digest:
        return _public({"ok": False, "status": "operation_owned_by_other_tab", "operation": owner.get("operation"), "operation_generation": owner.get("generation"), "operation_revision": owner.get("revision"), "contradictions": [{"kind": "operation_owned_by_other_tab"}]})
    if owner and int(revision) <= int(owner.get("revision") or 0):
        return _public({"ok": False, "status": "stale_operation_revision", "contradictions": [{"kind": "stale_operation_revision"}]})
    token_id=f"cert-operation-claim-{secrets.token_hex(8)}"; nonce=secrets.token_hex(16)
    auth={"schema":"eidolon-certification-operation-claim-v1","token_id":token_id,"nonce":nonce,"operation":operation,"tab_digest":tab_digest,"revision":int(revision),"previous_generation":int(owner.get("generation") or 0),"previous_owner_sha256":str(owner.get("owner_sha256") or ""),"content_free":True}
    auth["binding_sha256"]=digest_payload(auth)
    atomic_json(certification_directory(runtime_root)/"operation_claim_authorizations"/f"{token_id}.json",auth)
    token=f"{token_id}.{auth['binding_sha256']}.{nonce}"
    return _public({"ok":True,"status":"operation_claim_previewed","operation":operation,"operation_generation":int(owner.get("generation") or 0)+1,"operation_revision":int(revision),"authorization_token":token,"literal_confirmation_required":OPERATION_CLAIM_CONFIRMATION})


def claim_operation(token: str, *, confirm: str, runtime_root: str | Path | None = None) -> dict[str, Any]:
    if confirm != OPERATION_CLAIM_CONFIRMATION:
        return _public({"ok":False,"status":"literal_confirmation_required","contradictions":[{"kind":"literal_confirmation_required"}]})
    parts=token.split('.') if isinstance(token,str) else []; directory=certification_directory(runtime_root)
    auth=read_json(directory/"operation_claim_authorizations"/f"{parts[0]}.json") if len(parts)==3 else {}
    if not auth or parts != [str(auth.get('token_id') or ''),str(auth.get('binding_sha256') or ''),str(auth.get('nonce') or '')] or str(auth.get('binding_sha256') or '') != digest_payload({k:v for k,v in auth.items() if k!='binding_sha256'}):
        return _public({"ok":False,"status":"operation_claim_token_invalid","contradictions":[{"kind":"operation_claim_token_invalid"}]})
    used=directory/"used_operation_tokens"/f"{digest_payload({'token':token})}.json"
    if used.is_file(): return _public({"ok":False,"status":"authorization_reused","contradictions":[{"kind":"authorization_reused"}]})
    owner=_owner(runtime_root)
    if int(auth.get('previous_generation') or 0)!=int(owner.get('generation') or 0) or str(auth.get('previous_owner_sha256') or '')!=str(owner.get('owner_sha256') or ''):
        return _public({"ok":False,"status":"operation_claim_stale","contradictions":[{"kind":"operation_owner_changed"}]})
    generation=int(owner.get('generation') or 0)+1
    row={"schema":"eidolon-certification-operation-owner-v1","generation":generation,"operation":auth['operation'],"tab_digest":auth['tab_digest'],"revision":auth['revision'],"claimed_at":utc_now(),"content_free":True};row['owner_sha256']=_owner_digest(row)
    atomic_json(directory/"active_operation_owner.json",row);atomic_json(used,{"schema":"eidolon-used-operation-token-v1","used_at":utc_now(),"content_free":True})
    return _public({"ok":True,"status":"operation_claimed","operation":row['operation'],"operation_owner_present":True,"operation_generation":generation,"operation_revision":row['revision']})


def release_operation(tab_id: str, generation: int, *, confirm: str, runtime_root: str | Path | None = None) -> dict[str, Any]:
    if confirm != OPERATION_RELEASE_CONFIRMATION:
        return _public({"ok":False,"status":"literal_confirmation_required","contradictions":[{"kind":"literal_confirmation_required"}]})
    owner=_owner(runtime_root); tab_digest=digest_payload({"tab_id":tab_id})
    if not owner or owner.get('invalid') or str(owner.get('tab_digest') or '')!=tab_digest or int(owner.get('generation') or 0)!=int(generation):
        return _public({"ok":False,"status":"operation_release_stale","contradictions":[{"kind":"exact_operation_owner_required"}]})
    path=certification_directory(runtime_root)/"active_operation_owner.json"; path.unlink(missing_ok=True)
    return _public({"ok":True,"status":"operation_released","operation_owner_present":False,"operation":owner.get('operation'),"operation_generation":generation})
