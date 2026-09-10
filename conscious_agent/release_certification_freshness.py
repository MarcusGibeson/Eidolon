from __future__ import annotations

"""Evidence freshness, explicit replacement, and recertification preview.

No directory scanning, provider contact, native checks, automatic renewal,
revocation, supersession, or certification occurs here.
"""

from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
import secrets
from typing import Any, Iterable, Mapping

try:
    from release_candidate_identity import atomic_json, digest_payload, read_json, utc_now
    from release_certification_evidence import CERTIFICATION_SCOPE_REQUIREMENTS, EVIDENCE_SCOPES, _current_evidence, _parse_time, _promotion_context, _public_evidence, _record_digest, certification_directory, select_certification_evidence
    from release_certification_plan import _current_certification_state
except ImportError:
    from release_candidate_identity import atomic_json, digest_payload, read_json, utc_now
    from release_certification_evidence import CERTIFICATION_SCOPE_REQUIREMENTS, EVIDENCE_SCOPES, _current_evidence, _parse_time, _promotion_context, _public_evidence, _record_digest, certification_directory, select_certification_evidence
    from release_certification_plan import _current_certification_state

CERTIFICATION_FRESHNESS_CONTRACT_VERSION = "1"
EVIDENCE_REPLACEMENT_CONFIRMATION = "REPLACE EXACT CERTIFICATION EVIDENCE"
EVIDENCE_REPLACEMENT_ACTION = "replace_exact_certification_evidence"
DEFAULT_POLICY = {
    "schema": "eidolon-certification-evidence-freshness-policy-v1",
    "version": "1097.5-1",
    "max_age_days": {
        "source_package_integrity": 30,
        "startup_daily_use": 30,
        "installation_recovery": 30,
        "promotion_behavior": 30,
        "native_windows_behavior": 14,
        "provider_ollama_behavior": 7,
        "model_specific_behavior": 7,
    },
    "explicit_expiry_required": False,
    "scope_implication_allowed": False,
}


def _counts(rows: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    found: Counter[str] = Counter()
    for row in rows or []:
        found[str(row.get("kind") or "unknown")] += max(1, int(row.get("count") or 1))
    return [{"kind": key, "count": found[key]} for key in sorted(found)]


def _policy(runtime_root: str | Path | None) -> dict[str, Any]:
    custom = read_json(certification_directory(runtime_root) / "freshness_policy.json")
    policy = dict(DEFAULT_POLICY)
    if custom:
        policy.update({k: v for k, v in custom.items() if k in {"schema", "version", "max_age_days", "explicit_expiry_required", "scope_implication_allowed"}})
    policy["policy_sha256"] = digest_payload({k: v for k, v in policy.items() if k != "policy_sha256"})
    return policy


def _freshness(record: Mapping[str, Any], policy: Mapping[str, Any], now: datetime | None = None) -> dict[str, Any]:
    moment = now or datetime.now(timezone.utc)
    payload = record.get("payload") if isinstance(record.get("payload"), Mapping) else {}
    findings: list[dict[str, Any]] = list(record.get("contradictions") or [])
    finished = _parse_time(payload.get("finished_at"))
    explicit_expiry = _parse_time(payload.get("expires_at"))
    scope = str(record.get("scope") or "")
    max_days = int(dict(policy.get("max_age_days") or {}).get(scope) or 0)
    calculated_expiry = finished + timedelta(days=max_days) if finished and max_days > 0 else None
    expires = explicit_expiry or calculated_expiry
    if bool(payload.get("withdrawn")):
        findings.append({"kind": "evidence_withdrawn"})
    if explicit_expiry and finished and explicit_expiry < finished:
        findings.append({"kind": "evidence_expiry_precedes_completion"})
    if bool(policy.get("explicit_expiry_required")) and not explicit_expiry:
        findings.append({"kind": "explicit_evidence_expiry_required"})
    if not finished:
        findings.append({"kind": "evidence_completion_time_invalid"})
    if expires and moment > expires:
        findings.append({"kind": "evidence_expired"})
    if str(record.get("record_sha256") or "") != _record_digest(record):
        findings.append({"kind": "evidence_record_digest_mismatch"})
    fresh = bool(record.get("sufficient")) and not findings
    return {
        "evidence_id": str(record.get("evidence_id") or ""), "scope": scope,
        "artifact_sha256": str(record.get("artifact_sha256") or ""),
        "producer_version": str(record.get("producer_version") or ""),
        "candidate_id": str(record.get("candidate_id") or ""),
        "archive_sha256": str(record.get("archive_sha256") or ""),
        "installed_receipt_sha256": str(record.get("installed_receipt_sha256") or ""),
        "promotion_receipt_sha256": str(record.get("promotion_receipt_sha256") or ""),
        "finished_at": str(payload.get("finished_at") or ""),
        "expires_at": expires.isoformat() if expires else "", "fresh": fresh,
        "status": "evidence_fresh" if fresh else ("evidence_expired" if any(x.get("kind") == "evidence_expired" for x in findings) else "evidence_stale_or_contradictory"),
        "contradictions": findings,
    }


def _active_by_scope(runtime_root: str | Path | None, context: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    rows = _current_evidence(runtime_root, context)
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        scope = str(row.get("scope") or "")
        prior = result.get(scope)
        if prior is None or int(row.get("generation") or 0) > int(prior.get("generation") or 0):
            result[scope] = row
    return result


def _public(row: Mapping[str, Any] | None) -> dict[str, Any]:
    record = dict(row or {})
    contradictions = _counts(record.get("contradictions") if isinstance(record.get("contradictions"), list) else [])
    return {
        "ok": bool(record.get("ok")) and not contradictions,
        "status": str(record.get("status") or "evidence_freshness_unavailable"),
        "contract_version": CERTIFICATION_FRESHNESS_CONTRACT_VERSION,
        "scope": str(record.get("scope") or record.get("certification_scope") or ""),
        "evidence_id": str(record.get("evidence_id") or ""),
        "replacement_preview_id": str(record.get("replacement_preview_id") or ""),
        "generation": int(record.get("generation") or 0),
        "artifact_sha256": str(record.get("artifact_sha256") or ""),
        "previous_artifact_sha256": str(record.get("previous_artifact_sha256") or ""),
        "replacement_artifact_sha256": str(record.get("replacement_artifact_sha256") or ""),
        "policy_version": str(record.get("policy_version") or ""),
        "policy_sha256": str(record.get("policy_sha256") or ""),
        "fresh_scope_count": int(record.get("fresh_scope_count") or 0),
        "expired_scope_count": int(record.get("expired_scope_count") or 0),
        "stale_scope_count": int(record.get("stale_scope_count") or 0),
        "fresh_scopes": list(record.get("fresh_scopes") or []),
        "expired_scopes": list(record.get("expired_scopes") or []),
        "stale_scopes": list(record.get("stale_scopes") or []),
        "recertification_required": bool(record.get("recertification_required")),
        "ready_to_recertify": bool(record.get("ready_to_recertify")) and not contradictions,
        "authorization_token": str(record.get("authorization_token") or ""),
        "literal_confirmation_required": str(record.get("literal_confirmation_required") or EVIDENCE_REPLACEMENT_CONFIRMATION),
        "contradictions": contradictions,
        "contradiction_count": sum(int(item["count"]) for item in contradictions),
        "certification_changed": False,
        "certification_renewed": False,
        "certification_revoked": False,
        "provider_contacted": False,
        "native_check_run": False,
        "models_mutated": False,
        "source_files_mutated": False,
        "paths_suppressed": True,
        "records_external": True,
        "content_free": True,
        "ordinary_conversation_affected": False,
    }


def evidence_freshness_status(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    context, findings = _promotion_context(runtime_root)
    policy = _policy(runtime_root)
    active = _active_by_scope(runtime_root, context)
    statuses = {scope: _freshness(row, policy) for scope, row in active.items()}
    fresh = sorted(scope for scope, row in statuses.items() if row["fresh"])
    expired = sorted(scope for scope, row in statuses.items() if row["status"] == "evidence_expired")
    stale = sorted(scope for scope, row in statuses.items() if not row["fresh"] and scope not in expired)
    return _public({
        "ok": not findings, "status": "evidence_freshness_current" if not findings else "evidence_freshness_contradictory",
        "policy_version": policy["version"], "policy_sha256": policy["policy_sha256"],
        "fresh_scopes": fresh, "expired_scopes": expired, "stale_scopes": stale,
        "fresh_scope_count": len(fresh), "expired_scope_count": len(expired), "stale_scope_count": len(stale),
        "contradictions": findings,
    })


def _replacement_binding(row: Mapping[str, Any]) -> str:
    return digest_payload({
        "contract": "eidolon-certification-evidence-replacement-v1",
        "replacement_preview_id": str(row.get("replacement_preview_id") or ""),
        "generation": int(row.get("generation") or 0), "scope": str(row.get("scope") or ""),
        "previous_evidence_id": str(row.get("previous_evidence_id") or ""),
        "previous_artifact_sha256": str(row.get("previous_artifact_sha256") or ""),
        "replacement_evidence_id": str(row.get("replacement_evidence_id") or ""),
        "replacement_artifact_sha256": str(row.get("replacement_artifact_sha256") or ""),
        "replacement_record_sha256": str(row.get("replacement_record_sha256") or ""),
        "candidate_id": str(row.get("candidate_id") or ""), "archive_sha256": str(row.get("archive_sha256") or ""),
        "installed_receipt_sha256": str(row.get("installed_receipt_sha256") or ""),
        "promotion_receipt_sha256": str(row.get("promotion_receipt_sha256") or ""),
        "policy_sha256": str(row.get("policy_sha256") or ""), "action": EVIDENCE_REPLACEMENT_ACTION,
    })


def preview_evidence_replacement(evidence_path: str | Path, scope: str, *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    context, context_findings = _promotion_context(runtime_root)
    active = _active_by_scope(runtime_root, context)
    previous = active.get(scope, {})
    selected = select_certification_evidence(evidence_path, runtime_root=runtime_root, _activation_state="pending_replacement")
    directory = certification_directory(runtime_root)
    replacement = read_json(directory / "evidence" / f"{selected.get('evidence_id','')}.json")
    findings = list(context_findings)
    if scope not in EVIDENCE_SCOPES:
        findings.append({"kind": "unsupported_evidence_scope"})
    if not previous:
        findings.append({"kind": "existing_coherent_evidence_required"})
    if not replacement or not selected.get("ok") or str(replacement.get("scope") or "") != scope:
        findings.append({"kind": "replacement_evidence_invalid_or_scope_mismatched"})
    policy = _policy(runtime_root)
    if replacement and not _freshness(replacement, policy).get("fresh"):
        findings.append({"kind": "replacement_evidence_not_fresh"})
    pointer = read_json(directory / "active_replacement_preview.json")
    generation = int(pointer.get("generation") or 0) + 1
    row = {
        "schema": "eidolon-certification-evidence-replacement-preview-v1",
        "replacement_preview_id": f"evidence-replacement-{generation}-{secrets.token_hex(8)}", "generation": generation,
        "created_at": utc_now(), "scope": scope,
        "previous_evidence_id": str(previous.get("evidence_id") or ""), "previous_artifact_sha256": str(previous.get("artifact_sha256") or ""),
        "replacement_evidence_id": str(replacement.get("evidence_id") or ""), "replacement_artifact_sha256": str(replacement.get("artifact_sha256") or ""),
        "replacement_record_sha256": str(replacement.get("record_sha256") or ""),
        "candidate_id": str(context.get("candidate_id") or ""), "archive_sha256": str(context.get("archive_sha256") or ""),
        "installed_receipt_sha256": str(context.get("installed_receipt_sha256") or ""), "promotion_receipt_sha256": str(context.get("promotion_receipt_sha256") or ""),
        "policy_version": policy["version"], "policy_sha256": policy["policy_sha256"],
        "status": "evidence_replacement_previewed" if not findings else "evidence_replacement_blocked", "ok": not findings,
        "contradictions": findings,
    }
    row["replacement_binding_sha256"] = _replacement_binding(row)
    row["record_sha256"] = digest_payload(row)
    atomic_json(directory / "replacement_previews" / f"{row['replacement_preview_id']}.json", row)
    if findings:
        atomic_json(directory / "last_failed_replacement_preview.json", row)
        return _public(row)
    token_id = f"evidence-replacement-auth-{secrets.token_hex(8)}"; nonce = secrets.token_hex(16)
    auth = {**{k: row[k] for k in row if k not in {"contradictions", "record_sha256", "status", "ok", "created_at"}}, "schema": "eidolon-certification-evidence-replacement-authorization-v1", "token_id": token_id, "nonce": nonce, "content_free": True}
    auth["binding_sha256"] = digest_payload({"contract": "eidolon-certification-evidence-replacement-token-v1", "token_id": token_id, "nonce": nonce, "replacement_binding_sha256": row["replacement_binding_sha256"], "replacement_preview_id": row["replacement_preview_id"]})
    token = f"{token_id}.{auth['binding_sha256']}.{nonce}"
    atomic_json(directory / "replacement_authorizations" / f"{token_id}.json", auth)
    atomic_json(directory / "active_replacement_preview.json", {"schema": row["schema"], "replacement_preview_id": row["replacement_preview_id"], "generation": generation, "replacement_binding_sha256": row["replacement_binding_sha256"], "record_sha256": row["record_sha256"], "scope": scope, "content_free": True})
    row.update({"authorization_token": token, "literal_confirmation_required": EVIDENCE_REPLACEMENT_CONFIRMATION})
    return _public(row)


def _used_path(runtime_root: str | Path | None, token: str) -> Path:
    return certification_directory(runtime_root) / "used_replacement_tokens" / f"{digest_payload({'token': token})}.json"


def replace_certification_evidence(token: str, *, confirm: str, runtime_root: str | Path | None = None) -> dict[str, Any]:
    if confirm != EVIDENCE_REPLACEMENT_CONFIRMATION:
        return _public({"ok": False, "status": "literal_confirmation_required", "contradictions": [{"kind": "literal_confirmation_required"}]})
    parts = token.split(".") if isinstance(token, str) else []
    directory = certification_directory(runtime_root)
    if len(parts) != 3:
        return _public({"ok": False, "status": "replacement_token_invalid", "contradictions": [{"kind": "replacement_token_invalid"}]})
    auth = read_json(directory / "replacement_authorizations" / f"{parts[0]}.json")
    if not auth or parts != [str(auth.get("token_id") or ""), str(auth.get("binding_sha256") or ""), str(auth.get("nonce") or "")]:
        return _public({"ok": False, "status": "replacement_token_invalid", "contradictions": [{"kind": "replacement_token_invalid"}]})
    if _used_path(runtime_root, token).is_file():
        return _public({"ok": False, "status": "authorization_reused", "contradictions": [{"kind": "authorization_reused"}]})
    pointer = read_json(directory / "active_replacement_preview.json")
    preview = read_json(directory / "replacement_previews" / f"{auth.get('replacement_preview_id','')}.json")
    if not preview or str(preview.get("record_sha256") or "") != digest_payload({k: v for k, v in preview.items() if k != "record_sha256"}) or str(preview.get("replacement_binding_sha256") or "") != _replacement_binding(preview):
        return _public({"ok": False, "status": "replacement_token_stale", "contradictions": [{"kind": "replacement_preview_invalid"}]})
    for field in ("replacement_preview_id", "generation", "replacement_binding_sha256", "scope"):
        if str(pointer.get(field) or "") != str(preview.get(field) or ""):
            return _public({"ok": False, "status": "replacement_token_stale", "contradictions": [{"kind": "replacement_preview_pointer_drift"}]})
    context, findings = _promotion_context(runtime_root)
    active = _active_by_scope(runtime_root, context)
    previous = active.get(str(preview.get("scope") or ""), {})
    replacement = read_json(directory / "evidence" / f"{preview.get('replacement_evidence_id','')}.json")
    if str(previous.get("evidence_id") or "") != str(preview.get("previous_evidence_id") or "") or str(previous.get("artifact_sha256") or "") != str(preview.get("previous_artifact_sha256") or ""):
        findings.append({"kind": "active_evidence_changed_since_preview"})
    if not replacement or str(replacement.get("record_sha256") or "") != str(preview.get("replacement_record_sha256") or "") or str(replacement.get("record_sha256") or "") != _record_digest(replacement):
        findings.append({"kind": "replacement_evidence_record_drift"})
    policy = _policy(runtime_root)
    if replacement and not _freshness(replacement, policy).get("fresh"):
        findings.append({"kind": "replacement_evidence_no_longer_fresh"})
    for field in ("candidate_id", "archive_sha256", "installed_receipt_sha256", "promotion_receipt_sha256"):
        if str(preview.get(field) or "") != str(context.get(field) or ""):
            findings.append({"kind": f"replacement_{field}_drift"})
    if str(preview.get("policy_sha256") or "") != str(policy.get("policy_sha256") or ""):
        findings.append({"kind": "replacement_policy_drift"})
    if findings:
        return _public({"ok": False, "status": "replacement_token_stale", "scope": preview.get("scope"), "contradictions": findings})
    replacements = read_json(directory / "active_evidence_replacements.json")
    mapping = dict(replacements.get("active_evidence_by_scope") or {})
    mapping[str(preview["scope"])] = str(preview["replacement_evidence_id"])
    generation = int(replacements.get("generation") or 0) + 1
    relation = {
        "schema": "eidolon-certification-evidence-replacement-receipt-v1", "replacement_id": f"evidence-replacement-receipt-{generation}-{secrets.token_hex(6)}",
        "generation": generation, "scope": preview["scope"], "previous_evidence_id": preview["previous_evidence_id"],
        "previous_artifact_sha256": preview["previous_artifact_sha256"], "replacement_evidence_id": preview["replacement_evidence_id"],
        "replacement_artifact_sha256": preview["replacement_artifact_sha256"], "replacement_binding_sha256": preview["replacement_binding_sha256"],
        "replaced_at": utc_now(), "content_free": True,
    }
    relation["receipt_sha256"] = digest_payload(relation)
    atomic_json(directory / "replacement_receipts" / f"{relation['replacement_id']}.json", relation)
    atomic_json(directory / "active_evidence_replacements.json", {"schema": "eidolon-certification-active-evidence-v1", "generation": generation, "active_evidence_by_scope": mapping, "last_replacement_receipt_sha256": relation["receipt_sha256"], "content_free": True})
    atomic_json(_used_path(runtime_root, token), {"schema": "eidolon-certification-evidence-used-token-v1", "token_sha256": digest_payload({"token": token}), "outcome": "evidence_replaced", "used_at": utc_now(), "content_free": True})
    return _public({"ok": True, "status": "evidence_replaced", "scope": preview["scope"], "evidence_id": preview["replacement_evidence_id"], "previous_artifact_sha256": preview["previous_artifact_sha256"], "replacement_artifact_sha256": preview["replacement_artifact_sha256"], "policy_version": policy["version"], "policy_sha256": policy["policy_sha256"]})


def create_recertification_readiness_preview(certification_scope: str = "general_release", *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    context, findings = _promotion_context(runtime_root)
    policy = _policy(runtime_root)
    if certification_scope not in CERTIFICATION_SCOPE_REQUIREMENTS:
        findings.append({"kind": "unsupported_certification_scope"})
    required = list(CERTIFICATION_SCOPE_REQUIREMENTS.get(certification_scope, ()))
    active = _active_by_scope(runtime_root, context)
    statuses = {scope: _freshness(active[scope], policy) for scope in required if scope in active}
    missing = sorted(set(required) - set(statuses))
    stale = sorted(scope for scope, row in statuses.items() if not row["fresh"])
    _, authority = _current_certification_state(runtime_root)
    certified = certification_scope in list(authority.get("certified_scopes") or [])
    scope_receipt_sha = str(dict(authority.get("scope_receipts") or {}).get(certification_scope) or "")
    certified_receipt = {}
    if scope_receipt_sha:
        for path in (certification_directory(runtime_root) / "receipts").glob("*.json"):
            row = read_json(path)
            if str(row.get("receipt_sha256") or "") == scope_receipt_sha:
                certified_receipt = row; break
    current_set = sorted([{"scope": scope, "evidence_id": active[scope]["evidence_id"], "artifact_sha256": active[scope]["artifact_sha256"], "record_sha256": active[scope]["record_sha256"]} for scope in required if scope in active and statuses[scope]["fresh"]], key=lambda x: (x["scope"], x["artifact_sha256"]))
    current_set_sha = digest_payload(current_set)
    prior_set_sha = str(certified_receipt.get("evidence_set_sha256") or "")
    policy_changed = bool(certified_receipt and str(certified_receipt.get("decision_policy_sha256") or "") != str(policy["policy_sha256"]))
    evidence_changed = bool(certified and prior_set_sha and prior_set_sha != current_set_sha)
    recert_required = certified and bool(missing or stale or policy_changed or evidence_changed)
    ready = not findings and not missing and not stale
    directory = certification_directory(runtime_root)
    pointer = read_json(directory / "active_recertification_preview.json"); generation = int(pointer.get("generation") or 0) + 1
    row = {
        "schema": "eidolon-certification-recertification-readiness-v1", "preview_id": f"recertification-readiness-{generation}-{secrets.token_hex(8)}", "generation": generation,
        "created_at": utc_now(), "certification_scope": certification_scope, "candidate_id": context.get("candidate_id"), "archive_sha256": context.get("archive_sha256"),
        "installed_receipt_sha256": context.get("installed_receipt_sha256"), "promotion_receipt_sha256": context.get("promotion_receipt_sha256"),
        "policy_version": policy["version"], "policy_sha256": policy["policy_sha256"], "required_scopes": required,
        "fresh_scopes": sorted(scope for scope, row2 in statuses.items() if row2["fresh"]), "expired_scopes": sorted(scope for scope, row2 in statuses.items() if row2["status"] == "evidence_expired"),
        "stale_scopes": stale, "missing_scopes": missing, "current_evidence_set_sha256": current_set_sha, "certified_evidence_set_sha256": prior_set_sha,
        "certified": certified, "policy_changed": policy_changed, "evidence_changed": evidence_changed,
        "recertification_required": recert_required, "ready_to_recertify": ready,
        "status": "recertification_ready" if ready else "recertification_not_ready", "ok": not findings, "contradictions": findings,
    }
    row["preview_binding_sha256"] = digest_payload({k: v for k, v in row.items() if k not in {"created_at", "contradictions", "status", "ok"}})
    row["record_sha256"] = digest_payload(row)
    atomic_json(directory / "recertification_previews" / f"{row['preview_id']}.json", row)
    atomic_json(directory / "active_recertification_preview.json", {"schema": row["schema"], "preview_id": row["preview_id"], "generation": generation, "preview_binding_sha256": row["preview_binding_sha256"], "record_sha256": row["record_sha256"], "certification_scope": certification_scope, "content_free": True})
    return _public(row)


def recertification_readiness_status(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    directory = certification_directory(runtime_root)
    pointer = read_json(directory / "active_recertification_preview.json")
    preview_id = str(pointer.get("preview_id") or "")
    record = read_json(directory / "recertification_previews" / f"{preview_id}.json") if preview_id else {}
    if not record:
        return _public({"ok": True, "status": "recertification_not_previewed"})
    findings: list[dict[str, Any]] = []
    material = dict(record); expected_record = str(material.pop("record_sha256", ""))
    if not expected_record or expected_record != digest_payload(material):
        findings.append({"kind": "recertification_preview_record_digest_mismatch"})
    binding = digest_payload({k: v for k, v in record.items() if k not in {"created_at", "contradictions", "status", "ok", "record_sha256", "preview_binding_sha256"}})
    if str(record.get("preview_binding_sha256") or "") != binding:
        findings.append({"kind": "recertification_preview_binding_mismatch"})
    for field in ("preview_id", "generation", "preview_binding_sha256", "record_sha256", "certification_scope"):
        if str(pointer.get(field) or "") != str(record.get(field) or ""):
            findings.append({"kind": f"recertification_preview_pointer_{field}_mismatch"})
    policy = _policy(runtime_root)
    if str(record.get("policy_sha256") or "") != str(policy.get("policy_sha256") or ""):
        findings.append({"kind": "recertification_preview_policy_drift"})
    context, context_findings = _promotion_context(runtime_root); findings.extend(context_findings)
    for field in ("candidate_id", "archive_sha256", "installed_receipt_sha256", "promotion_receipt_sha256"):
        if str(record.get(field) or "") != str(context.get(field) or ""):
            findings.append({"kind": f"recertification_preview_{field}_drift"})
    current = dict(record)
    current["contradictions"] = findings
    current["ok"] = not findings
    current["ready_to_recertify"] = bool(record.get("ready_to_recertify")) and not findings
    current["status"] = str(record.get("status") or "recertification_not_ready") if not findings else "recertification_preview_stale"
    return _public(current)
