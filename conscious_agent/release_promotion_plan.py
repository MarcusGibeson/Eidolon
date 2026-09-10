from __future__ import annotations

"""Immutable promotion plan and exact single-use authorization preview."""

from collections import Counter
from pathlib import Path
import secrets
from typing import Any, Iterable, Mapping

try:
    from release_candidate_identity import atomic_json, digest_payload, read_json, utc_now
    from release_promotion_preview import active_promotion_preview_private, current_promotion_state_private, promotion_directory, promotion_preview_status, _preview_binding, _record_digest
except ImportError:
    from release_candidate_identity import atomic_json, digest_payload, read_json, utc_now
    from release_promotion_preview import active_promotion_preview_private, current_promotion_state_private, promotion_directory, promotion_preview_status, _preview_binding, _record_digest

PROMOTION_PLAN_CONTRACT_VERSION = "1"
PROMOTION_PLAN_SCHEMA = "eidolon-promotion-plan-v1"
PROMOTION_AUTHORIZATION_SCHEMA = "eidolon-promotion-authorization-v1"
PROMOTION_AUTHORIZATION_ACTION = "authorize_exact_promotion"
PROMOTION_AUTHORIZATION_CONFIRMATION = "AUTHORIZE EXACT PROMOTION"


def _counts(rows: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    found: Counter[str] = Counter()
    for row in rows or []: found[str(row.get("kind") or "unknown")] += max(1, int(row.get("count") or 1))
    return [{"kind": key, "count": found[key]} for key in sorted(found)]


def _plan_binding(record: Mapping[str, Any]) -> str:
    return digest_payload({
        "contract": "eidolon-promotion-plan-binding-v1",
        "plan_id": str(record.get("plan_id") or ""), "generation": int(record.get("generation") or 0),
        "preview_id": str(record.get("preview_id") or ""), "preview_generation": int(record.get("preview_generation") or 0),
        "preview_binding_sha256": str(record.get("preview_binding_sha256") or ""), "preview_record_sha256": str(record.get("preview_record_sha256") or ""),
        "transaction_id": str(record.get("transaction_id") or ""), "transaction_generation": int(record.get("transaction_generation") or 0),
        "transaction_identity_sha256": str(record.get("transaction_identity_sha256") or ""), "transaction_state_sha256": str(record.get("transaction_state_sha256") or ""),
        "installed_receipt_sha256": str(record.get("installed_receipt_sha256") or ""), "candidate_id": str(record.get("candidate_id") or ""),
        "archive_sha256": str(record.get("archive_sha256") or ""), "source_manifest_sha256": str(record.get("source_manifest_sha256") or ""),
        "archive_manifest_sha256": str(record.get("archive_manifest_sha256") or ""), "target_project_id": str(record.get("target_project_id") or ""),
        "target_identity_sha256": str(record.get("target_identity_sha256") or ""), "target_inventory_sha256": str(record.get("target_inventory_sha256") or ""),
        "effects_sha256": str(record.get("effects_sha256") or ""), "previous_promotion_generation": int(record.get("previous_promotion_generation") or 0),
        "previous_promotion_state_sha256": str(record.get("previous_promotion_state_sha256") or ""), "previous_promotion_state": str(record.get("previous_promotion_state") or ""),
        "proposed_promotion_state": str(record.get("proposed_promotion_state") or ""), "metadata_effects_sha256": str(record.get("metadata_effects_sha256") or ""),
        "reversal_plan_sha256": str(record.get("reversal_plan_sha256") or ""), "promotion_policy_sha256": str(record.get("promotion_policy_sha256") or ""),
    })


def _authorization_binding(record: Mapping[str, Any]) -> str:
    return digest_payload({
        "contract": "eidolon-promotion-authorization-binding-v1",
        "token_id": str(record.get("token_id") or ""), "action": str(record.get("action") or ""),
        "plan_id": str(record.get("plan_id") or ""), "plan_generation": int(record.get("plan_generation") or 0),
        "plan_binding_sha256": str(record.get("plan_binding_sha256") or ""), "plan_record_sha256": str(record.get("plan_record_sha256") or ""),
        "transaction_id": str(record.get("transaction_id") or ""), "transaction_identity_sha256": str(record.get("transaction_identity_sha256") or ""),
        "installed_receipt_sha256": str(record.get("installed_receipt_sha256") or ""), "candidate_id": str(record.get("candidate_id") or ""),
        "archive_sha256": str(record.get("archive_sha256") or ""), "target_project_id": str(record.get("target_project_id") or ""),
        "target_inventory_sha256": str(record.get("target_inventory_sha256") or ""), "previous_promotion_generation": int(record.get("previous_promotion_generation") or 0),
        "previous_promotion_state_sha256": str(record.get("previous_promotion_state_sha256") or ""), "proposed_promotion_state": str(record.get("proposed_promotion_state") or ""),
        "metadata_effects_sha256": str(record.get("metadata_effects_sha256") or ""), "reversal_plan_sha256": str(record.get("reversal_plan_sha256") or ""),
    })


def _public(record: Mapping[str, Any] | None) -> dict[str, Any]:
    row=dict(record or {}); contradictions=_counts(row.get("contradictions") if isinstance(row.get("contradictions"),list) else [])
    return {
        "ok": bool(row.get("ok")) and not contradictions, "status": str(row.get("status") or "not_planned"),
        "contract_version": PROMOTION_PLAN_CONTRACT_VERSION, "plan_present": bool(row), "plan_id": str(row.get("plan_id") or ""),
        "plan_binding_sha256": str(row.get("plan_binding_sha256") or ""), "generation": int(row.get("generation") or 0),
        "preview_id": str(row.get("preview_id") or ""), "transaction_id": str(row.get("transaction_id") or ""),
        "transaction_identity_sha256": str(row.get("transaction_identity_sha256") or ""), "installed_receipt_sha256": str(row.get("installed_receipt_sha256") or ""),
        "candidate_id": str(row.get("candidate_id") or ""), "packaged_version": str(row.get("packaged_version") or ""), "archive_sha256": str(row.get("archive_sha256") or ""),
        "target_project_id": str(row.get("target_project_id") or ""), "target_inventory_sha256": str(row.get("target_inventory_sha256") or ""),
        "metadata_effects_sha256": str(row.get("metadata_effects_sha256") or ""), "reversal_plan_sha256": str(row.get("reversal_plan_sha256") or ""),
        "previous_promotion_state": str(row.get("previous_promotion_state") or ""), "proposed_promotion_state": str(row.get("proposed_promotion_state") or ""),
        "authorization_token": str(row.get("authorization_token") or ""), "literal_confirmation_required": PROMOTION_AUTHORIZATION_CONFIRMATION,
        "contradictions": contradictions, "contradiction_count": sum(int(x["count"]) for x in contradictions),
        "source_files_mutated": False, "promotion_applied": False, "certified": False, "paths_suppressed": True, "records_external": True,
        "content_free": True, "ordinary_conversation_affected": False, "provider_contacted": False,
    }


def create_promotion_plan(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    preview_status=promotion_preview_status(runtime_root=runtime_root); pointer, preview=active_promotion_preview_private(runtime_root)
    findings=[]
    if not preview_status.get("ok") or preview_status.get("status")!="promotion_previewed": findings.append({"kind":"coherent_promotion_preview_required"})
    if not preview or str(preview.get("preview_binding_sha256") or "")!=_preview_binding(preview): findings.append({"kind":"promotion_preview_binding_invalid"})
    directory=promotion_directory(runtime_root)
    if findings:
        failed={"status":"promotion_plan_blocked","ok":False,"contradictions":findings}; atomic_json(directory/'last_failed_plan.json',failed); return _public(failed)
    active=read_json(directory/'active_plan.json'); generation=int(active.get('generation') or 0)+1
    reversal={"contract":"eidolon-promotion-reversal-plan-v1","from":"promoted_uncertified","to":str(preview.get('previous_promotion_state') or 'installed_unpromoted'),"requires_no_certification":True,"source_mutation":False}
    record={
        "schema":PROMOTION_PLAN_SCHEMA,"plan_id":f"promotion-plan-{generation}-{secrets.token_hex(8)}","generation":generation,"created_at":utc_now(),"status":"promotion_planned","ok":True,
        "preview_id":preview['preview_id'],"preview_generation":preview['generation'],"preview_binding_sha256":preview['preview_binding_sha256'],"preview_record_sha256":preview['record_sha256'],
        "transaction_id":preview['transaction_id'],"transaction_generation":preview['transaction_generation'],"transaction_identity_sha256":preview['transaction_identity_sha256'],"transaction_state_sha256":preview['transaction_state_sha256'],
        "installed_receipt_sha256":preview['installed_receipt_sha256'],"candidate_id":preview['candidate_id'],"packaged_version":preview['packaged_version'],"archive_sha256":preview['archive_sha256'],
        "source_manifest_sha256":preview['source_manifest_sha256'],"archive_manifest_sha256":preview['archive_manifest_sha256'],"target_project_id":preview['target_project_id'],"target_identity_sha256":preview['target_identity_sha256'],
        "target_inventory_sha256":preview['target_inventory_sha256'],"effects_sha256":preview['effects_sha256'],"previous_promotion_generation":preview['previous_promotion_generation'],
        "previous_promotion_state_sha256":preview['previous_promotion_state_sha256'],"previous_promotion_state":preview['previous_promotion_state'],"proposed_promotion_state":preview['proposed_promotion_state'],
        "metadata_effects":preview['metadata_effects'],"metadata_effects_sha256":preview['metadata_effects_sha256'],"reversal_plan":reversal,"reversal_plan_sha256":digest_payload(reversal),
        "promotion_policy_sha256":preview['promotion_policy_sha256'],"contradictions":[],
    }
    record['plan_binding_sha256']=_plan_binding(record); record['record_sha256']=_record_digest(record,'record_sha256')
    atomic_json(directory/'plans'/f"{record['plan_id']}.json",record)
    atomic_json(directory/'active_plan.json',{"schema":PROMOTION_PLAN_SCHEMA,"plan_id":record['plan_id'],"generation":generation,"plan_binding_sha256":record['plan_binding_sha256'],"record_sha256":record['record_sha256'],"content_free":True})
    return _public(record)


def active_promotion_plan_private(runtime_root: str | Path | None = None) -> tuple[dict[str, Any],dict[str,Any]]:
    d=promotion_directory(runtime_root); pointer=read_json(d/'active_plan.json'); pid=str(pointer.get('plan_id') or ''); return pointer,read_json(d/'plans'/f'{pid}.json') if pid else {}


def promotion_plan_status(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    pointer,record=active_promotion_plan_private(runtime_root)
    if not record:return _public({})
    findings=[]
    if str(record.get('record_sha256') or '')!=_record_digest(record,'record_sha256'): findings.append({'kind':'promotion_plan_record_digest_mismatch'})
    if str(record.get('plan_binding_sha256') or '')!=_plan_binding(record): findings.append({'kind':'promotion_plan_binding_mismatch'})
    for f in ('plan_id','generation','plan_binding_sha256','record_sha256'):
        if str(pointer.get(f) or '')!=str(record.get(f) or ''): findings.append({'kind':f'promotion_plan_pointer_{f}_mismatch'})
    ps=promotion_preview_status(runtime_root=runtime_root); _,preview=active_promotion_preview_private(runtime_root)
    if not ps.get('ok'): findings.append({'kind':'promotion_preview_stale'})
    for f in ('preview_id','preview_binding_sha256','transaction_id','transaction_identity_sha256','installed_receipt_sha256','candidate_id','archive_sha256','target_project_id','target_inventory_sha256','metadata_effects_sha256'):
        if str(record.get(f) or '')!=str(preview.get(f) or ''): findings.append({'kind':f'promotion_plan_{f}_drift'})
    current=dict(record); current['contradictions']=findings; current['ok']=not findings; current['status']='promotion_planned' if not findings else 'promotion_plan_stale'
    return _public(current)


def preview_promotion_authorization(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    status=promotion_plan_status(runtime_root=runtime_root); _,plan=active_promotion_plan_private(runtime_root)
    if not status.get('ok'):
        return _public({'status':'promotion_authorization_blocked','contradictions':[{'kind':'coherent_promotion_plan_required'}]})
    token_id=f"promotion-auth-{secrets.token_hex(8)}"; nonce=secrets.token_hex(16)
    auth={
        "schema":PROMOTION_AUTHORIZATION_SCHEMA,"token_id":token_id,"action":PROMOTION_AUTHORIZATION_ACTION,"created_at":utc_now(),
        "plan_id":plan['plan_id'],"plan_generation":plan['generation'],"plan_binding_sha256":plan['plan_binding_sha256'],"plan_record_sha256":plan['record_sha256'],
        "transaction_id":plan['transaction_id'],"transaction_identity_sha256":plan['transaction_identity_sha256'],"installed_receipt_sha256":plan['installed_receipt_sha256'],
        "candidate_id":plan['candidate_id'],"archive_sha256":plan['archive_sha256'],"target_project_id":plan['target_project_id'],"target_inventory_sha256":plan['target_inventory_sha256'],
        "previous_promotion_generation":plan['previous_promotion_generation'],"previous_promotion_state_sha256":plan['previous_promotion_state_sha256'],
        "proposed_promotion_state":plan['proposed_promotion_state'],"metadata_effects_sha256":plan['metadata_effects_sha256'],"reversal_plan_sha256":plan['reversal_plan_sha256'],"nonce":nonce,
    }
    auth['authorization_binding_sha256']=_authorization_binding(auth); auth['record_sha256']=_record_digest(auth,'record_sha256')
    token=f"{token_id}.{auth['authorization_binding_sha256']}.{nonce}"
    atomic_json(promotion_directory(runtime_root)/'authorizations'/f'{token_id}.json',auth)
    public=_public(plan); public.update({'ok':True,'status':'promotion_authorized','authorization_token':token}); return public


def load_promotion_authorization(token: str, runtime_root: str | Path | None = None) -> dict[str, Any]:
    parts=token.split('.') if isinstance(token,str) else []
    if len(parts)!=3:return {}
    return read_json(promotion_directory(runtime_root)/'authorizations'/f'{parts[0]}.json')


def promotion_authorization_valid(token: str, runtime_root: str | Path | None = None) -> tuple[dict[str,Any],list[dict[str,Any]]]:
    findings=[]; auth=load_promotion_authorization(token,runtime_root)
    parts=token.split('.') if isinstance(token,str) else []
    if not auth: return {},[{'kind':'promotion_authorization_missing_or_malformed'}]
    if str(auth.get('record_sha256') or '')!=_record_digest(auth,'record_sha256'): findings.append({'kind':'promotion_authorization_record_digest_mismatch'})
    if str(auth.get('authorization_binding_sha256') or '')!=_authorization_binding(auth): findings.append({'kind':'promotion_authorization_binding_mismatch'})
    if len(parts)!=3 or parts != [str(auth.get('token_id') or ''),str(auth.get('authorization_binding_sha256') or ''),str(auth.get('nonce') or '')]: findings.append({'kind':'promotion_authorization_token_mismatch'})
    if str(auth.get('action') or '')!=PROMOTION_AUTHORIZATION_ACTION: findings.append({'kind':'promotion_authorization_action_mismatch'})
    status=promotion_plan_status(runtime_root=runtime_root); _,plan=active_promotion_plan_private(runtime_root)
    if not status.get('ok'): findings.append({'kind':'promotion_plan_stale'})
    for af,pf in (("plan_id","plan_id"),("plan_generation","generation"),("plan_binding_sha256","plan_binding_sha256"),("plan_record_sha256","record_sha256"),("transaction_id","transaction_id"),("transaction_identity_sha256","transaction_identity_sha256"),("installed_receipt_sha256","installed_receipt_sha256"),("candidate_id","candidate_id"),("archive_sha256","archive_sha256"),("target_project_id","target_project_id"),("target_inventory_sha256","target_inventory_sha256"),("previous_promotion_generation","previous_promotion_generation"),("previous_promotion_state_sha256","previous_promotion_state_sha256"),("proposed_promotion_state","proposed_promotion_state"),("metadata_effects_sha256","metadata_effects_sha256"),("reversal_plan_sha256","reversal_plan_sha256")):
        if str(auth.get(af) or '')!=str(plan.get(pf) or ''): findings.append({'kind':f'promotion_authorization_{af}_mismatch'})
    return auth,findings
