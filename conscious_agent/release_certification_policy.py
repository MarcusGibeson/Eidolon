from __future__ import annotations

"""Explicit certification policy selection and read-only migration impact preview."""

from collections import Counter
import hashlib
import json
from pathlib import Path, PureWindowsPath
import secrets
from typing import Any, Iterable, Mapping

try:
    from release_candidate_identity import atomic_json, digest_payload, read_json, runtime_data_root, utc_now
    from release_certification_evidence import CERTIFICATION_SCOPE_REQUIREMENTS, certification_directory, _promotion_context
    from release_certification_freshness import evidence_freshness_status, _active_by_scope, _freshness, _policy as freshness_policy
    from release_certification_history import certification_history_status, create_certification_history_reconciliation_preview
    from release_certification_plan import _current_certification_state
except ImportError:
    from release_candidate_identity import atomic_json, digest_payload, read_json, runtime_data_root, utc_now
    from release_certification_evidence import CERTIFICATION_SCOPE_REQUIREMENTS, certification_directory, _promotion_context
    from release_certification_freshness import evidence_freshness_status, _active_by_scope, _freshness, _policy as freshness_policy
    from release_certification_history import certification_history_status, create_certification_history_reconciliation_preview
    from release_certification_plan import _current_certification_state

CERTIFICATION_POLICY_CONTRACT_VERSION = "1"
POLICY_SCHEMA = "eidolon-certification-policy-v1"
POLICY_SELECTION_SCHEMA = "eidolon-certification-policy-selection-v1"
POLICY_MIGRATION_SCHEMA = "eidolon-certification-policy-migration-preview-v1"
POLICY_ACK_CONFIRMATION = "ACKNOWLEDGE EXACT CERTIFICATION POLICY MIGRATION PREVIEW"
POLICY_ACK_ACTION = "acknowledge_exact_certification_policy_migration_preview"
BUILTIN_POLICY_ID = "eidolon-certification-policy-1097.8-default"

BUILTIN_POLICY = {
    "schema": POLICY_SCHEMA,
    "policy_id": BUILTIN_POLICY_ID,
    "version": "1097.8-1",
    "producer": {"tool": "eidolon", "version": "1097.8"},
    "supported_scopes": ["general_release", "native_windows", "provider_ollama", "model_specific"],
    "evidence_classes": {k: list(v) for k, v in CERTIFICATION_SCOPE_REQUIREMENTS.items()},
    "freshness_windows_days": {
        "source_package_integrity": 30, "startup_daily_use": 30, "installation_recovery": 30,
        "promotion_behavior": 30, "native_windows_behavior": 14,
        "provider_ollama_behavior": 7, "model_specific_behavior": 7,
    },
    "environment_requirements": {
        "general_release": {"native_required": False},
        "native_windows": {"os": "windows", "native_required": True},
        "provider_ollama": {"provider": "ollama", "available_required": True},
        "model_specific": {"model_identity_required": True},
    },
    "decision_rules": {"all_required_evidence_must_pass": True, "scope_implication_allowed": False, "exact_promoted_receipt_required": True},
    "revocation_rules": {"automatic_revocation_allowed": False, "operator_review_required": True},
    "supersession_rules": {"append_only": True, "exact_prior_receipt_required": True},
    "migration_compatibility": {"compatible_policy_schemas": ["eidolon-certification-decision-policy-v1", "eidolon-certification-evidence-freshness-policy-v1", POLICY_SCHEMA], "automatic_migration_allowed": False},
}


def _counts(rows: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    found: Counter[str] = Counter()
    for row in rows or []: found[str(row.get("kind") or "unknown")] += max(1, int(row.get("count") or 1))
    return [{"kind": k, "count": found[k]} for k in sorted(found)]


def _sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()


def _policy_digest(policy: Mapping[str, Any]) -> str:
    return digest_payload({k:v for k,v in policy.items() if k not in {"policy_sha256","selected_path"}})


def _path_leak(value: Any, key: str="") -> bool:
    if isinstance(value, Mapping): return any(_path_leak(v,str(k)) for k,v in value.items())
    if isinstance(value, list): return any(_path_leak(v,key) for v in value)
    if not isinstance(value,str): return False
    text=value.strip(); lower=key.lower()
    return bool(text and (any(x in lower for x in ("path","directory","root")) or text.startswith(("/","\\\\")) or PureWindowsPath(text).is_absolute()))


def _validate_policy(policy: Mapping[str, Any]) -> list[dict[str, Any]]:
    findings=[]
    if str(policy.get("schema") or "") != POLICY_SCHEMA: findings.append({"kind":"policy_schema_unsupported"})
    for key in ("policy_id","version","producer","supported_scopes","evidence_classes","freshness_windows_days","environment_requirements","decision_rules","revocation_rules","supersession_rules","migration_compatibility"):
        if key not in policy: findings.append({"kind":f"policy_{key}_missing"})
    scopes=list(policy.get("supported_scopes") or [])
    if len(scopes)!=len(set(scopes)): findings.append({"kind":"policy_duplicate_scope"})
    if any(s not in CERTIFICATION_SCOPE_REQUIREMENTS for s in scopes): findings.append({"kind":"policy_scope_unsupported"})
    if _path_leak(policy): findings.append({"kind":"policy_private_path_present"})
    if bool(dict(policy.get("migration_compatibility") or {}).get("automatic_migration_allowed")): findings.append({"kind":"automatic_policy_migration_forbidden"})
    if bool(dict(policy.get("decision_rules") or {}).get("scope_implication_allowed")): findings.append({"kind":"scope_implication_forbidden"})
    return findings


def _public(row: Mapping[str, Any] | None) -> dict[str, Any]:
    r=dict(row or {}); findings=_counts(r.get("findings") if isinstance(r.get("findings"),list) else [])
    return {
        "ok":bool(r.get("ok")) and not findings,"status":str(r.get("status") or "certification_policy_not_selected"),
        "contract_version":CERTIFICATION_POLICY_CONTRACT_VERSION,"policy_id":str(r.get("policy_id") or ""),"policy_version":str(r.get("policy_version") or ""),
        "policy_sha256":str(r.get("policy_sha256") or ""),"artifact_sha256":str(r.get("artifact_sha256") or ""),"generation":int(r.get("generation") or 0),
        "built_in":bool(r.get("built_in")),"supported_scopes":list(r.get("supported_scopes") or []),"preview_id":str(r.get("preview_id") or ""),
        "history_sha256":str(r.get("history_sha256") or ""),"scope_impacts":list(r.get("scope_impacts") or []),
        "classification_counts":list(r.get("classification_counts") or []),"authorization_token":str(r.get("authorization_token") or ""),
        "literal_confirmation_required":POLICY_ACK_CONFIRMATION,"finding_count":sum(int(x["count"]) for x in findings),"findings":findings,
        "policy_migrated":False,"evidence_replaced":False,"certification_renewed":False,"certification_revoked":False,"native_checks_run":False,"provider_contacted":False,"models_mutated":False,
        "paths_suppressed":True,"records_external":True,"content_free":True,"ordinary_conversation_affected":False,
    }


def select_certification_policy(policy_path: str | Path | None = None, *, built_in_policy_id: str = "", runtime_root: str | Path | None = None) -> dict[str, Any]:
    findings=[]; policy={}; artifact_sha=""; built_in=False; selected_path=""
    if built_in_policy_id:
        if policy_path is not None: findings.append({"kind":"select_exactly_one_policy_source"})
        if built_in_policy_id != BUILTIN_POLICY_ID: findings.append({"kind":"built_in_policy_identity_unknown"})
        else: policy=dict(BUILTIN_POLICY); built_in=True; artifact_sha=_policy_digest(policy)
    elif policy_path is not None:
        path=Path(policy_path).expanduser().resolve(); selected_path=str(path)
        if not path.is_file() or path.is_symlink(): findings.append({"kind":"selected_policy_missing_or_unsafe"})
        else:
            try: policy=json.loads(path.read_text(encoding="utf-8-sig")); artifact_sha=_sha256_file(path)
            except Exception: findings.append({"kind":"selected_policy_unreadable"})
    else: findings.append({"kind":"explicit_policy_selection_required"})
    if policy: findings.extend(_validate_policy(policy))
    directory=certification_directory(runtime_root); pointer=read_json(directory/"active_policy_selection.json"); generation=int(pointer.get("generation") or 0)+1
    record={"schema":POLICY_SELECTION_SCHEMA,"selection_id":f"cert-policy-{generation}-{secrets.token_hex(8)}","generation":generation,"selected_at":utc_now(),"selected_path":selected_path,"built_in":built_in,
            "policy":policy,"policy_id":str(policy.get("policy_id") or ""),"policy_version":str(policy.get("version") or ""),"policy_sha256":_policy_digest(policy) if policy else "","artifact_sha256":artifact_sha,
            "supported_scopes":list(policy.get("supported_scopes") or []),"findings":findings,"ok":not findings,"status":"certification_policy_selected" if not findings else "certification_policy_rejected"}
    record["record_sha256"]=digest_payload(record)
    atomic_json(directory/"policy_selections"/f"{record['selection_id']}.json",record)
    if not findings: atomic_json(directory/"active_policy_selection.json",{"schema":POLICY_SELECTION_SCHEMA,"selection_id":record["selection_id"],"generation":generation,"policy_sha256":record["policy_sha256"],"record_sha256":record["record_sha256"],"content_free":True})
    else: atomic_json(directory/"last_failed_policy_selection.json",record)
    return _public(record)


def active_policy_private(runtime_root: str | Path | None = None) -> tuple[dict[str,Any],dict[str,Any]]:
    d=certification_directory(runtime_root); p=read_json(d/"active_policy_selection.json"); sid=str(p.get("selection_id") or ""); return p, read_json(d/"policy_selections"/f"{sid}.json") if sid else {}


def certification_policy_status(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    pointer,record=active_policy_private(runtime_root)
    if not record: return _public({"ok":True,"status":"certification_policy_not_selected"})
    findings=[]; material=dict(record); expected=str(material.pop("record_sha256", ""))
    if not expected or expected != digest_payload(material): findings.append({"kind":"policy_selection_record_digest_mismatch"})
    for f in ("selection_id","generation","policy_sha256","record_sha256"):
        if str(pointer.get(f) or "") != str(record.get(f) or ""): findings.append({"kind":f"policy_selection_pointer_{f}_mismatch"})
    findings.extend(_validate_policy(record.get("policy") if isinstance(record.get("policy"),Mapping) else {}))
    current=dict(record); current["findings"]=findings; current["ok"]=not findings; current["status"]="certification_policy_selected" if not findings else "certification_policy_contradictory"
    return _public(current)


def _migration_binding(row: Mapping[str, Any]) -> str:
    return digest_payload({"contract":"eidolon-certification-policy-migration-preview-binding-v1","preview_id":str(row.get("preview_id") or ""),"generation":int(row.get("generation") or 0),"policy_sha256":str(row.get("policy_sha256") or ""),"artifact_sha256":str(row.get("artifact_sha256") or ""),"history_sha256":str(row.get("history_sha256") or ""),"authority_state_sha256":str(row.get("authority_state_sha256") or ""),"evidence_set_sha256":str(row.get("evidence_set_sha256") or ""),"candidate_id":str(row.get("candidate_id") or ""),"archive_sha256":str(row.get("archive_sha256") or ""),"target_project_id":str(row.get("target_project_id") or ""),"installed_receipt_sha256":str(row.get("installed_receipt_sha256") or ""),"promotion_receipt_sha256":str(row.get("promotion_receipt_sha256") or ""),"scope_impacts_sha256":str(row.get("scope_impacts_sha256") or ""),"proposed_action":str(row.get("proposed_action") or "")})


def create_policy_migration_preview(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    policy_status=certification_policy_status(runtime_root=runtime_root); pointer,selection=active_policy_private(runtime_root)
    if not policy_status.get("ok") or not selection: return _public({"ok":False,"status":"policy_migration_preview_blocked","findings":policy_status.get("findings") or [{"kind":"coherent_policy_selection_required"}]})
    history=create_certification_history_reconciliation_preview(runtime_root=runtime_root)
    context,findings=_promotion_context(runtime_root)
    if not history.get("ok"): findings.extend(history.get("findings") or [{"kind":"coherent_authority_history_required"}])
    _,authority=_current_certification_state(runtime_root); policy=selection["policy"]
    active=_active_by_scope(runtime_root,context); fresh_policy=freshness_policy(runtime_root)
    impacts=[]
    for scope in ("general_release","native_windows","provider_ollama","model_specific"):
        certified=scope in list(authority.get("certified_scopes") or [])
        supported=scope in list(policy.get("supported_scopes") or [])
        required=list(dict(policy.get("evidence_classes") or {}).get(scope) or [])
        statuses={s:_freshness(active[s],fresh_policy) for s in required if s in active}
        missing=sorted(set(required)-set(statuses)); stale=sorted(s for s,v in statuses.items() if not v.get("fresh"))
        receipt_sha=str(dict(authority.get("scope_receipts") or {}).get(scope) or "")
        receipt={}
        if receipt_sha:
            for p in (certification_directory(runtime_root)/"receipts").glob("*.json"):
                r=read_json(p)
                if str(r.get("receipt_sha256") or "")==receipt_sha: receipt=r; break
        old_policy=str(receipt.get("decision_policy_sha256") or "")
        compatible_schemas=set(dict(policy.get("migration_compatibility") or {}).get("compatible_policy_schemas") or [])
        if not supported and certified: cls="unsupported"
        elif not supported: cls="not_applicable"
        elif missing or stale: cls="evidence_refresh_required"
        elif certified and old_policy==selection["policy_sha256"]: cls="unchanged"
        elif certified and old_policy: cls="compatible" if "eidolon-certification-decision-policy-v1" in compatible_schemas else "recertification_preview_required"
        elif certified: cls="contradictory"
        else: cls="not_applicable"
        if certified and not bool(dict(policy.get("revocation_rules") or {}).get("operator_review_required",True)): cls="revocation_review_required"
        impacts.append({"scope":scope,"classification":cls,"certified":certified,"supported":supported,"missing_evidence_count":len(missing),"stale_evidence_count":len(stale),"current_policy_sha256":old_policy,"selected_policy_sha256":selection["policy_sha256"]})
    counts=Counter(x["classification"] for x in impacts)
    evidence_set=[{"scope":s,"artifact_sha256":str(r.get("artifact_sha256") or ""),"record_sha256":str(r.get("record_sha256") or "")} for s,r in sorted(active.items())]
    d=certification_directory(runtime_root); ptr=read_json(d/"active_policy_migration_preview.json"); generation=int(ptr.get("generation") or 0)+1
    record={"schema":POLICY_MIGRATION_SCHEMA,"preview_id":f"policy-migration-{generation}-{secrets.token_hex(8)}","generation":generation,"created_at":utc_now(),"runtime_root_sha256":digest_payload({"runtime_root":str(runtime_data_root(runtime_root).resolve())}),
            "policy_id":selection["policy_id"],"policy_version":selection["policy_version"],"policy_sha256":selection["policy_sha256"],"artifact_sha256":selection["artifact_sha256"],"history_sha256":history.get("history_sha256"),"authority_state_sha256":str(authority.get("state_sha256") or ""),"authority_generation":int(authority.get("generation") or 0),"evidence_set_sha256":digest_payload(evidence_set),
            **{k:context.get(k) for k in ("candidate_id","archive_sha256","target_project_id","installed_receipt_sha256","promotion_receipt_sha256")},"scope_impacts":impacts,"scope_impacts_sha256":digest_payload(impacts),"classification_counts":[{"classification":k,"count":counts[k]} for k in sorted(counts)],"proposed_action":"review_policy_migration_impact","findings":findings,"ok":not findings,"status":"policy_migration_previewed" if not findings else "policy_migration_preview_contradictory"}
    record["preview_binding_sha256"]=_migration_binding(record); record["record_sha256"]=digest_payload(record)
    atomic_json(d/"policy_migration_previews"/f"{record['preview_id']}.json",record)
    if findings: atomic_json(d/"last_failed_policy_migration_preview.json",record); return _public(record)
    token_id=f"policy-migration-auth-{secrets.token_hex(8)}"; nonce=secrets.token_hex(16)
    auth={"schema":"eidolon-certification-policy-migration-authorization-v1","token_id":token_id,"nonce":nonce,"action":POLICY_ACK_ACTION,"preview_id":record["preview_id"],"generation":generation,"preview_binding_sha256":record["preview_binding_sha256"],"record_sha256":record["record_sha256"],"policy_sha256":record["policy_sha256"],"history_sha256":record["history_sha256"],"scope_impacts_sha256":record["scope_impacts_sha256"],"content_free":True}
    auth["binding_sha256"]=digest_payload({"contract":"eidolon-certification-policy-migration-token-v1",**{k:auth[k] for k in ("token_id","nonce","action","preview_id","generation","preview_binding_sha256","record_sha256","policy_sha256","history_sha256","scope_impacts_sha256")}})
    atomic_json(d/"policy_migration_authorizations"/f"{token_id}.json",auth)
    atomic_json(d/"active_policy_migration_preview.json",{"schema":POLICY_MIGRATION_SCHEMA,"preview_id":record["preview_id"],"generation":generation,"preview_binding_sha256":record["preview_binding_sha256"],"record_sha256":record["record_sha256"],"policy_sha256":record["policy_sha256"],"content_free":True})
    record["authorization_token"]=f"{token_id}.{auth['binding_sha256']}.{nonce}"
    return _public(record)


def policy_migration_status(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    d=certification_directory(runtime_root); p=read_json(d/"active_policy_migration_preview.json"); pid=str(p.get("preview_id") or ""); r=read_json(d/"policy_migration_previews"/f"{pid}.json") if pid else {}
    if not r: return _public({"ok":True,"status":"policy_migration_not_previewed"})
    findings=[]; material=dict(r); expected=str(material.pop("record_sha256", ""))
    if not expected or expected!=digest_payload(material): findings.append({"kind":"policy_migration_record_digest_mismatch"})
    if str(r.get("preview_binding_sha256") or "") != _migration_binding(r): findings.append({"kind":"policy_migration_binding_mismatch"})
    for f in ("preview_id","generation","preview_binding_sha256","record_sha256","policy_sha256"):
        if str(p.get(f) or "")!=str(r.get(f) or ""): findings.append({"kind":f"policy_migration_pointer_{f}_mismatch"})
    ps=certification_policy_status(runtime_root=runtime_root); hs=certification_history_status(runtime_root=runtime_root); context,cf=_promotion_context(runtime_root); findings.extend(cf)
    if str(r.get("policy_sha256") or "")!=str(ps.get("policy_sha256") or ""): findings.append({"kind":"policy_migration_policy_drift"})
    if str(r.get("history_sha256") or "")!=str(hs.get("history_sha256") or ""): findings.append({"kind":"policy_migration_history_drift"})
    for f in ("candidate_id","archive_sha256","target_project_id","installed_receipt_sha256","promotion_receipt_sha256"):
        if str(r.get(f) or "")!=str(context.get(f) or ""): findings.append({"kind":f"policy_migration_{f}_drift"})
    cur=dict(r); cur["findings"]=findings; cur["ok"]=not findings; cur["status"]="policy_migration_preview_current" if not findings else "policy_migration_preview_stale"
    return _public(cur)


def _used(runtime_root: str | Path | None, token: str) -> Path:
    return certification_directory(runtime_root)/"used_policy_migration_tokens"/f"{digest_payload({'token':token})}.json"


def acknowledge_policy_migration_preview(token: str, *, confirm: str, runtime_root: str | Path | None = None) -> dict[str, Any]:
    if confirm != POLICY_ACK_CONFIRMATION: return _public({"ok":False,"status":"literal_confirmation_required","findings":[{"kind":"literal_confirmation_required"}]})
    parts=token.split(".") if isinstance(token,str) else []; d=certification_directory(runtime_root)
    if len(parts)!=3: return _public({"ok":False,"status":"policy_migration_token_invalid","findings":[{"kind":"policy_migration_token_invalid"}]})
    auth=read_json(d/"policy_migration_authorizations"/f"{parts[0]}.json")
    if not auth or parts != [str(auth.get("token_id") or ""),str(auth.get("binding_sha256") or ""),str(auth.get("nonce") or "")]: return _public({"ok":False,"status":"policy_migration_token_invalid","findings":[{"kind":"policy_migration_token_invalid"}]})
    binding=digest_payload({"contract":"eidolon-certification-policy-migration-token-v1",**{k:auth.get(k) for k in ("token_id","nonce","action","preview_id","generation","preview_binding_sha256","record_sha256","policy_sha256","history_sha256","scope_impacts_sha256")}})
    if str(auth.get("binding_sha256") or "")!=binding or str(auth.get("action") or "")!=POLICY_ACK_ACTION: return _public({"ok":False,"status":"policy_migration_token_invalid","findings":[{"kind":"policy_migration_token_invalid"}]})
    if _used(runtime_root,token).is_file(): return _public({"ok":False,"status":"authorization_reused","findings":[{"kind":"authorization_reused"}]})
    status=policy_migration_status(runtime_root=runtime_root)
    p=read_json(d/"active_policy_migration_preview.json")
    for f in ("preview_id","generation","preview_binding_sha256","record_sha256","policy_sha256"):
        if str(auth.get(f) or "")!=str(p.get(f) or ""): return _public({"ok":False,"status":"policy_migration_token_stale","findings":[{"kind":f"policy_migration_token_{f}_mismatch"}]})
    if not status.get("ok"): return _public({"ok":False,"status":"policy_migration_token_stale","findings":status.get("findings") or [{"kind":"policy_migration_preview_stale"}]})
    receipt={"schema":"eidolon-certification-policy-migration-acknowledgment-v1","acknowledgment_id":f"policy-migration-ack-{secrets.token_hex(8)}","preview_id":status["preview_id"],"policy_sha256":status["policy_sha256"],"history_sha256":status["history_sha256"],"scope_impacts":status["scope_impacts"],"acknowledged_at":utc_now(),"migration_applied":False,"content_free":True}
    receipt["receipt_sha256"]=digest_payload(receipt)
    atomic_json(d/"policy_migration_acknowledgments"/f"{receipt['acknowledgment_id']}.json",receipt); atomic_json(_used(runtime_root,token),{"schema":"eidolon-used-policy-migration-token-v1","token_sha256":digest_payload({"token":token}),"used_at":utc_now(),"outcome":"migration_preview_acknowledged","content_free":True})
    return _public({"ok":True,"status":"policy_migration_preview_acknowledged","preview_id":status["preview_id"],"policy_id":status["policy_id"],"policy_version":status["policy_version"],"policy_sha256":status["policy_sha256"],"history_sha256":status["history_sha256"],"scope_impacts":status["scope_impacts"],"classification_counts":status["classification_counts"]})
