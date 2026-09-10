from __future__ import annotations

"""Transactional promotion apply, interruption recovery, and exact reversal.

All authority evidence remains external. Promotion never mutates installed source
files and never implies certification.
"""

from collections import Counter
import json
from pathlib import Path
import secrets
from typing import Any, Iterable, Mapping

try:
    from release_candidate_identity import atomic_json, digest_payload, read_json, utc_now
    from release_promotion_preview import promotion_directory, current_promotion_state_private, _record_digest
    from release_installation_preview import _target_inventory
    from release_installation_transaction import active_transaction_private
    from release_promotion_plan import PROMOTION_AUTHORIZATION_CONFIRMATION, active_promotion_plan_private, promotion_authorization_valid, promotion_plan_status
except ImportError:
    from release_candidate_identity import atomic_json, digest_payload, read_json, utc_now
    from release_promotion_preview import promotion_directory, current_promotion_state_private, _record_digest
    from release_installation_preview import _target_inventory
    from release_installation_transaction import active_transaction_private
    from release_promotion_plan import PROMOTION_AUTHORIZATION_CONFIRMATION, active_promotion_plan_private, promotion_authorization_valid, promotion_plan_status

PROMOTION_TRANSACTION_CONTRACT_VERSION = "1"
PROMOTION_TRANSACTION_SCHEMA = "eidolon-promotion-transaction-v1"
PROMOTION_APPLY_CONFIRMATION = "APPLY EXACT PROMOTION"
PROMOTION_RESUME_CONFIRMATION = "RESUME EXACT PROMOTION"
PROMOTION_REVERSAL_CONFIRMATION = "REVERSE EXACT PROMOTION"
PROMOTION_APPLY_ACTION = "apply_exact_promotion"
PROMOTION_RESUME_ACTION = "resume_exact_promotion"
PROMOTION_REVERSAL_ACTION = "reverse_exact_promotion"


def _counts(rows: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    c: Counter[str] = Counter()
    for row in rows or []: c[str(row.get("kind") or "unknown")] += max(1, int(row.get("count") or 1))
    return [{"kind": k, "count": c[k]} for k in sorted(c)]


def _token_digest(token: str) -> str:
    return digest_payload({"contract": "eidolon-promotion-token-v1", "token": token})


def _transaction_binding(record: Mapping[str, Any]) -> str:
    return digest_payload({
        "contract":"eidolon-promotion-transaction-identity-v1","promotion_transaction_id":str(record.get("promotion_transaction_id") or ""),
        "generation":int(record.get("generation") or 0),"action":str(record.get("action") or ""),"plan_id":str(record.get("plan_id") or ""),
        "plan_generation":int(record.get("plan_generation") or 0),"plan_binding_sha256":str(record.get("plan_binding_sha256") or ""),
        "transaction_id":str(record.get("transaction_id") or ""),"transaction_identity_sha256":str(record.get("transaction_identity_sha256") or ""),
        "installed_receipt_sha256":str(record.get("installed_receipt_sha256") or ""),"candidate_id":str(record.get("candidate_id") or ""),
        "archive_sha256":str(record.get("archive_sha256") or ""),"source_manifest_sha256":str(record.get("source_manifest_sha256") or ""),
        "archive_manifest_sha256":str(record.get("archive_manifest_sha256") or ""),"target_project_id":str(record.get("target_project_id") or ""),
        "target_inventory_sha256":str(record.get("target_inventory_sha256") or ""),"previous_promotion_generation":int(record.get("previous_promotion_generation") or 0),
        "previous_promotion_state_sha256":str(record.get("previous_promotion_state_sha256") or ""),"proposed_promotion_state":str(record.get("proposed_promotion_state") or ""),
        "metadata_effects_sha256":str(record.get("metadata_effects_sha256") or ""),"reversal_plan_sha256":str(record.get("reversal_plan_sha256") or ""),
        "authorization_binding_sha256":str(record.get("authorization_binding_sha256") or ""),
    })


def _state_digest(record: Mapping[str, Any]) -> str:
    return digest_payload({"contract":"eidolon-promotion-transaction-state-v1","promotion_transaction_identity_sha256":str(record.get("promotion_transaction_identity_sha256") or ""),"state":str(record.get("state") or ""),"event_sequence":int(record.get("event_sequence") or 0),"promotion_receipt_sha256":str(record.get("promotion_receipt_sha256") or ""),"promotion_state_sha256":str(record.get("promotion_state_sha256") or ""),"reversal_receipt_sha256":str(record.get("reversal_receipt_sha256") or "")})


def _public(record: Mapping[str, Any] | None) -> dict[str, Any]:
    row=dict(record or {}); contradictions=_counts(row.get("contradictions") if isinstance(row.get("contradictions"),list) else [])
    status=str(row.get("status") or row.get("state") or "not_promoted")
    return {
        "ok": bool(row.get("ok")) and not contradictions, "status": status, "contract_version":PROMOTION_TRANSACTION_CONTRACT_VERSION,
        "promotion_transaction_present":bool(row),"promotion_transaction_id":str(row.get("promotion_transaction_id") or ""),
        "promotion_transaction_identity_sha256":str(row.get("promotion_transaction_identity_sha256") or ""),"promotion_transaction_state_sha256":str(row.get("promotion_transaction_state_sha256") or ""),
        "generation":int(row.get("generation") or 0),"plan_id":str(row.get("plan_id") or ""),"transaction_id":str(row.get("transaction_id") or ""),
        "transaction_identity_sha256":str(row.get("transaction_identity_sha256") or ""),"installed_receipt_sha256":str(row.get("installed_receipt_sha256") or ""),
        "candidate_id":str(row.get("candidate_id") or ""),"packaged_version":str(row.get("packaged_version") or ""),"archive_sha256":str(row.get("archive_sha256") or ""),
        "source_manifest_sha256":str(row.get("source_manifest_sha256") or ""),"archive_manifest_sha256":str(row.get("archive_manifest_sha256") or ""),
        "target_project_id":str(row.get("target_project_id") or ""),"target_inventory_sha256":str(row.get("target_inventory_sha256") or ""),
        "promotion_receipt_sha256":str(row.get("promotion_receipt_sha256") or ""),"promotion_state_sha256":str(row.get("promotion_state_sha256") or ""),
        "authorization_token":str(row.get("authorization_token") or ""),"literal_confirmation_required":str(row.get("literal_confirmation_required") or PROMOTION_APPLY_CONFIRMATION),
        "contradictions":contradictions,"contradiction_count":sum(int(x["count"]) for x in contradictions),
        "installed_unpromoted":status in {"not_promoted","promotion_previewed","promotion_authorized","reversed_to_installed_unpromoted"},
        "promoting":status=="promoting","promotion_interrupted":status=="promotion_interrupted","promotion_uncertain":status=="promotion_uncertain",
        "promoted":status=="promoted_uncertified","certified":False,"reversed":status=="reversed_to_installed_unpromoted",
        "source_files_mutated":False,"private_runtime_data_mutated":False,"paths_suppressed":True,"records_external":True,"content_free":True,
        "ordinary_conversation_affected":False,"provider_contacted":False,
    }


def _append_event(runtime_root: str|Path|None, txid: str, record: dict[str,Any], event: dict[str,Any]) -> None:
    d=promotion_directory(runtime_root); path=d/'events'/f'{txid}.jsonl'; path.parent.mkdir(parents=True,exist_ok=True)
    record['event_sequence']=int(record.get('event_sequence') or 0)+1
    row={"schema":"eidolon-promotion-event-v1","sequence":record['event_sequence'],"promotion_transaction_id":txid,"promotion_transaction_identity_sha256":record.get('promotion_transaction_identity_sha256',''),"recorded_at":utc_now(),**event}
    with path.open('a',encoding='utf-8') as h: h.write(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n')


def _save(runtime_root: str|Path|None, record: dict[str,Any]) -> None:
    d=promotion_directory(runtime_root); record['promotion_transaction_state_sha256']=_state_digest(record); record['record_sha256']=_record_digest(record,'record_sha256')
    atomic_json(d/'transactions'/f"{record['promotion_transaction_id']}.json",record)
    atomic_json(d/'active_transaction.json',{"schema":PROMOTION_TRANSACTION_SCHEMA,"promotion_transaction_id":record['promotion_transaction_id'],"generation":record['generation'],"promotion_transaction_identity_sha256":record['promotion_transaction_identity_sha256'],"promotion_transaction_state_sha256":record['promotion_transaction_state_sha256'],"record_sha256":record['record_sha256'],"content_free":True})


def active_promotion_transaction_private(runtime_root: str|Path|None=None)->tuple[dict[str,Any],dict[str,Any]]:
    d=promotion_directory(runtime_root); p=read_json(d/'active_transaction.json'); tid=str(p.get('promotion_transaction_id') or ''); return p,read_json(d/'transactions'/f'{tid}.json') if tid else {}


def _used(runtime_root: str|Path|None, token: str)->bool:
    return (promotion_directory(runtime_root)/'used_tokens'/f'{_token_digest(token)}.json').is_file()


def _mark_used(runtime_root: str|Path|None, token: str, outcome: str, txid: str)->None:
    atomic_json(promotion_directory(runtime_root)/'used_tokens'/f'{_token_digest(token)}.json',{"schema":"eidolon-promotion-used-token-v1","token_sha256":_token_digest(token),"outcome":outcome,"promotion_transaction_id":txid,"used_at":utc_now(),"content_free":True})


def _promotion_receipt(record: Mapping[str,Any]) -> dict[str,Any]:
    r={"schema":"eidolon-promoted-state-receipt-v1","promotion_transaction_id":record['promotion_transaction_id'],"promotion_transaction_identity_sha256":record['promotion_transaction_identity_sha256'],"plan_id":record['plan_id'],"transaction_id":record['transaction_id'],"transaction_identity_sha256":record['transaction_identity_sha256'],"installed_receipt_sha256":record['installed_receipt_sha256'],"candidate_id":record['candidate_id'],"packaged_version":record['packaged_version'],"archive_sha256":record['archive_sha256'],"source_manifest_sha256":record['source_manifest_sha256'],"archive_manifest_sha256":record['archive_manifest_sha256'],"target_project_id":record['target_project_id'],"target_inventory_sha256":record['target_inventory_sha256'],"previous_promotion_generation":record['previous_promotion_generation'],"state":"promoted_uncertified","promoted":True,"certified":False,"promoted_at":utc_now(),"content_free":True}
    r['receipt_sha256']=digest_payload(r); return r


def _promotion_state(record: Mapping[str,Any], receipt: Mapping[str,Any]) -> dict[str,Any]:
    s={"schema":"eidolon-promotion-authority-state-v1","state_id":f"promotion-state-{int(record['previous_promotion_generation'])+1}-{secrets.token_hex(6)}","generation":int(record['previous_promotion_generation'])+1,"state":"promoted_uncertified","previous_state":str(record.get('previous_promotion_state') or 'installed_unpromoted'),"previous_state_sha256":record['previous_promotion_state_sha256'],"promotion_transaction_id":record['promotion_transaction_id'],"promotion_transaction_identity_sha256":record['promotion_transaction_identity_sha256'],"promotion_receipt_sha256":receipt['receipt_sha256'],"candidate_id":record['candidate_id'],"packaged_version":record['packaged_version'],"target_project_id":record['target_project_id'],"target_inventory_sha256":record['target_inventory_sha256'],"certified":False,"created_at":utc_now(),"content_free":True}
    s['state_sha256']=digest_payload(s); return s


def _write_promoted_evidence(runtime_root: str|Path|None, record: dict[str,Any], *, interrupt_at: str='')->dict[str,Any]:
    d=promotion_directory(runtime_root)
    receipt=_promotion_receipt(record); atomic_json(d/'receipts'/f"{record['promotion_transaction_id']}.json",receipt); record['promotion_receipt_sha256']=receipt['receipt_sha256']; _append_event(runtime_root,record['promotion_transaction_id'],record,{"kind":"promotion_receipt_written","receipt_sha256":receipt['receipt_sha256']}); _save(runtime_root,record)
    if interrupt_at=='after_receipt': record['state']=record['status']='promotion_interrupted'; _append_event(runtime_root,record['promotion_transaction_id'],record,{"kind":"interrupted_after_promotion_receipt"}); _save(runtime_root,record); return record
    state=_promotion_state(record,receipt); atomic_json(d/'states'/f"{state['state_id']}.json",state); atomic_json(d/'active_promotion_state.json',{"schema":"eidolon-promotion-authority-state-v1","state_id":state['state_id'],"generation":state['generation'],"state_sha256":state['state_sha256'],"state":state['state'],"content_free":True}); record['promotion_state_sha256']=state['state_sha256']; _append_event(runtime_root,record['promotion_transaction_id'],record,{"kind":"promotion_state_activated","state_sha256":state['state_sha256']}); _save(runtime_root,record)
    if interrupt_at=='after_state': record['state']=record['status']='promotion_interrupted'; _append_event(runtime_root,record['promotion_transaction_id'],record,{"kind":"interrupted_after_promotion_state"}); _save(runtime_root,record); return record
    atomic_json(d/'active_promoted_receipt.json',{"schema":"eidolon-promoted-state-receipt-v1","promotion_transaction_id":record['promotion_transaction_id'],"receipt_sha256":receipt['receipt_sha256'],"state_sha256":state['state_sha256'],"content_free":True})
    record['state']=record['status']='promoted_uncertified'; record['completed_at']=utc_now(); _append_event(runtime_root,record['promotion_transaction_id'],record,{"kind":"promotion_finalized","state":"promoted_uncertified"}); _save(runtime_root,record); return record


def apply_authorized_promotion(authorization_token: str, *, confirm: str, runtime_root: str|Path|None=None, _interrupt_at: str='')->dict[str,Any]:
    token=authorization_token if isinstance(authorization_token,str) else ''
    if confirm!=PROMOTION_APPLY_CONFIRMATION:return _public({"status":"literal_confirmation_required","contradictions":[{"kind":"literal_confirmation_required"}]})
    if _used(runtime_root,token):return _public({"status":"authorization_reused","contradictions":[{"kind":"authorization_reused"}]})
    auth,findings=promotion_authorization_valid(token,runtime_root); status=promotion_plan_status(runtime_root=runtime_root); _,plan=active_promotion_plan_private(runtime_root)
    if findings or not status.get('ok'):return _public({"status":"authorization_stale_or_mismatched","contradictions":findings or [{"kind":"promotion_plan_stale"}]})
    pointer,_=active_promotion_transaction_private(runtime_root); generation=int(pointer.get('generation') or 0)+1
    _, installed_transaction = active_transaction_private(runtime_root)
    record={"schema":PROMOTION_TRANSACTION_SCHEMA,"promotion_transaction_id":f"promotion-transaction-{generation}-{secrets.token_hex(8)}","generation":generation,"action":PROMOTION_APPLY_ACTION,"created_at":utc_now(),"state":"promoting","status":"promoting","ok":True,"event_sequence":0,"plan_id":plan['plan_id'],"plan_generation":plan['generation'],"plan_binding_sha256":plan['plan_binding_sha256'],"transaction_id":plan['transaction_id'],"transaction_identity_sha256":plan['transaction_identity_sha256'],"installed_receipt_sha256":plan['installed_receipt_sha256'],"candidate_id":plan['candidate_id'],"packaged_version":plan['packaged_version'],"archive_sha256":plan['archive_sha256'],"source_manifest_sha256":plan['source_manifest_sha256'],"archive_manifest_sha256":plan['archive_manifest_sha256'],"target_project_id":plan['target_project_id'],"target_root_path":str(installed_transaction.get("target_root_path") or ""),"target_inventory_sha256":plan['target_inventory_sha256'],"previous_promotion_generation":plan['previous_promotion_generation'],"previous_promotion_state_sha256":plan['previous_promotion_state_sha256'],"previous_promotion_state":plan['previous_promotion_state'],"proposed_promotion_state":plan['proposed_promotion_state'],"metadata_effects_sha256":plan['metadata_effects_sha256'],"reversal_plan_sha256":plan['reversal_plan_sha256'],"authorization_binding_sha256":auth['authorization_binding_sha256'],"promotion_receipt_sha256":"","promotion_state_sha256":"","reversal_receipt_sha256":"","contradictions":[]}
    record['promotion_transaction_identity_sha256']=_transaction_binding(record); _append_event(runtime_root,record['promotion_transaction_id'],record,{"kind":"promotion_started"}); _save(runtime_root,record); _mark_used(runtime_root,token,'promotion_started',record['promotion_transaction_id'])
    if _interrupt_at=='after_start': record['state']=record['status']='promotion_interrupted'; _append_event(runtime_root,record['promotion_transaction_id'],record,{"kind":"interrupted_after_start"}); _save(runtime_root,record); return _public(record)
    try:return _public(_write_promoted_evidence(runtime_root,record,interrupt_at=_interrupt_at))
    except Exception as exc:
        record['state']=record['status']='promotion_uncertain'; record.setdefault('contradictions',[]).append({'kind':str(exc).split(':',1)[0] or 'promotion_apply_failed'}); _append_event(runtime_root,record['promotion_transaction_id'],record,{"kind":"promotion_failed"}); _save(runtime_root,record); return _public(record)


def _load_receipt(runtime_root: str|Path|None, txid: str)->dict[str,Any]: return read_json(promotion_directory(runtime_root)/'receipts'/f'{txid}.json') if txid else {}

def _receipt_valid(r: Mapping[str,Any])->bool:
    m=dict(r); expected=str(m.pop('receipt_sha256','')); return bool(expected and expected==digest_payload(m))


def promotion_transaction_status(*, runtime_root: str|Path|None=None)->dict[str,Any]:
    pointer,record=active_promotion_transaction_private(runtime_root)
    if not record:return _public({})
    findings=[]
    if str(record.get('promotion_transaction_identity_sha256') or '')!=_transaction_binding(record):findings.append({'kind':'promotion_transaction_identity_mismatch'})
    if str(record.get('promotion_transaction_state_sha256') or '')!=_state_digest(record):findings.append({'kind':'promotion_transaction_state_mismatch'})
    for f in ('promotion_transaction_id','generation','promotion_transaction_identity_sha256','promotion_transaction_state_sha256','record_sha256'):
        if str(pointer.get(f) or '')!=str(record.get(f) or ''):findings.append({'kind':f'promotion_transaction_pointer_{f}_mismatch'})
    state_pointer,state=current_promotion_state_private(runtime_root); receipt=_load_receipt(runtime_root,str(record.get('promotion_transaction_id') or ''))
    root=Path(str(record.get('target_root_path') or '')); inventory=_target_inventory(root) if root.is_dir() else {'ok':False,'digest':''}
    if not inventory.get('ok') or str(inventory.get('digest') or '')!=str(record.get('target_inventory_sha256') or ''): findings.append({'kind':'promoted_target_inventory_drift'})
    if record.get('promotion_receipt_sha256') and (not receipt or str(receipt.get('receipt_sha256') or '')!=str(record.get('promotion_receipt_sha256') or '') or not _receipt_valid(receipt)):findings.append({'kind':'promotion_receipt_invalid'})
    if record.get('promotion_state_sha256') and (not state or str(state.get('state_sha256') or '')!=str(record.get('promotion_state_sha256') or '')):
        descendant = bool(state) and str(state.get('promotion_transaction_id') or '') == str(record.get('promotion_transaction_id') or '') and str(state.get('promotion_receipt_sha256') or '') == str(record.get('promotion_receipt_sha256') or '') and str(state.get('candidate_id') or '') == str(record.get('candidate_id') or '') and str(state.get('target_project_id') or '') == str(record.get('target_project_id') or '') and str(state.get('state') or '') in {'certified','partially_certified','promoted_uncertified'}
        if not descendant:findings.append({'kind':'promotion_state_invalid'})
    current=dict(record); current['contradictions']=findings; current['ok']=not findings
    if findings:current['status']='promotion_uncertain'
    return _public(current)


def preview_promotion_resume(*, runtime_root: str|Path|None=None)->dict[str,Any]:
    status=promotion_transaction_status(runtime_root=runtime_root); _,record=active_promotion_transaction_private(runtime_root)
    if status.get('status')!='promotion_interrupted':return _public({"status":"promotion_resume_blocked","contradictions":[{"kind":"interrupted_promotion_required"}]})
    token_id=f"promotion-resume-{secrets.token_hex(8)}"; binding=digest_payload({"contract":"eidolon-promotion-resume-token-v1","token_id":token_id,"promotion_transaction_id":record['promotion_transaction_id'],"identity":record['promotion_transaction_identity_sha256'],"state":record['promotion_transaction_state_sha256'],"promotion_receipt_sha256":record.get('promotion_receipt_sha256',''),"promotion_state_sha256":record.get('promotion_state_sha256','')}); nonce=secrets.token_hex(16); token=f'{token_id}.{binding}.{nonce}'
    atomic_json(promotion_directory(runtime_root)/'resume_authorizations'/f'{token_id}.json',{"schema":"eidolon-promotion-resume-authorization-v1","token_id":token_id,"binding_sha256":binding,"nonce":nonce,"promotion_transaction_id":record['promotion_transaction_id'],"promotion_transaction_identity_sha256":record['promotion_transaction_identity_sha256'],"promotion_transaction_state_sha256":record['promotion_transaction_state_sha256'],"promotion_receipt_sha256":record.get('promotion_receipt_sha256',''),"promotion_state_sha256":record.get('promotion_state_sha256',''),"content_free":True})
    out=dict(record);out.update({'ok':True,'status':'promotion_resume_previewed','authorization_token':token,'literal_confirmation_required':PROMOTION_RESUME_CONFIRMATION});return _public(out)


def resume_promotion_transaction(token: str, *, confirm: str, runtime_root: str|Path|None=None)->dict[str,Any]:
    if confirm!=PROMOTION_RESUME_CONFIRMATION:return _public({"status":"literal_confirmation_required","contradictions":[{"kind":"literal_confirmation_required"}]})
    parts=token.split('.') if isinstance(token,str) else []
    if len(parts)!=3:return _public({"status":"resume_token_invalid","contradictions":[{"kind":"resume_token_invalid"}]})
    auth=read_json(promotion_directory(runtime_root)/'resume_authorizations'/f'{parts[0]}.json'); _,record=active_promotion_transaction_private(runtime_root)
    if not auth or parts!=[str(auth.get('token_id') or ''),str(auth.get('binding_sha256') or ''),str(auth.get('nonce') or '')]:return _public({"status":"resume_token_invalid","contradictions":[{"kind":"resume_token_invalid"}]})
    if _used(runtime_root,token):return _public({"status":"authorization_reused","contradictions":[{"kind":"authorization_reused"}]})
    for a,r in (("promotion_transaction_id","promotion_transaction_id"),("promotion_transaction_identity_sha256","promotion_transaction_identity_sha256"),("promotion_transaction_state_sha256","promotion_transaction_state_sha256"),("promotion_receipt_sha256","promotion_receipt_sha256"),("promotion_state_sha256","promotion_state_sha256")):
        if str(auth.get(a) or '')!=str(record.get(r) or ''):return _public({"status":"resume_token_stale","contradictions":[{"kind":"resume_token_stale"}]})
    _mark_used(runtime_root,token,'promotion_resume',record['promotion_transaction_id']); record['state']=record['status']='promoting'; _append_event(runtime_root,record['promotion_transaction_id'],record,{"kind":"promotion_resume_started"}); _save(runtime_root,record)
    return _public(_write_promoted_evidence(runtime_root,record))


def preview_promotion_reversal(*, runtime_root: str|Path|None=None)->dict[str,Any]:
    status=promotion_transaction_status(runtime_root=runtime_root); _,record=active_promotion_transaction_private(runtime_root); _,state=current_promotion_state_private(runtime_root)
    if status.get('status')!='promoted_uncertified' or str(state.get('state') or '')!='promoted_uncertified' or state.get('certified'):
        return _public({"status":"promotion_reversal_blocked","contradictions":[{"kind":"promoted_uncertified_state_required"}]})
    token_id=f"promotion-reversal-{secrets.token_hex(8)}"; binding=digest_payload({"contract":"eidolon-promotion-reversal-token-v1","token_id":token_id,"promotion_transaction_id":record['promotion_transaction_id'],"identity":record['promotion_transaction_identity_sha256'],"state_sha256":state['state_sha256'],"generation":state['generation'],"promotion_receipt_sha256":record['promotion_receipt_sha256'],"target_inventory_sha256":record['target_inventory_sha256']});nonce=secrets.token_hex(16);token=f'{token_id}.{binding}.{nonce}'
    atomic_json(promotion_directory(runtime_root)/'reversal_authorizations'/f'{token_id}.json',{"schema":"eidolon-promotion-reversal-authorization-v1","token_id":token_id,"binding_sha256":binding,"nonce":nonce,"promotion_transaction_id":record['promotion_transaction_id'],"promotion_transaction_identity_sha256":record['promotion_transaction_identity_sha256'],"state_sha256":state['state_sha256'],"generation":state['generation'],"promotion_receipt_sha256":record['promotion_receipt_sha256'],"target_inventory_sha256":record['target_inventory_sha256'],"content_free":True})
    out=dict(record);out.update({'ok':True,'status':'promotion_reversal_previewed','authorization_token':token,'literal_confirmation_required':PROMOTION_REVERSAL_CONFIRMATION});return _public(out)


def reverse_promotion(token: str, *, confirm: str, runtime_root: str|Path|None=None)->dict[str,Any]:
    if confirm!=PROMOTION_REVERSAL_CONFIRMATION:return _public({"status":"literal_confirmation_required","contradictions":[{"kind":"literal_confirmation_required"}]})
    parts=token.split('.') if isinstance(token,str) else []
    if len(parts)!=3:return _public({"status":"reversal_token_invalid","contradictions":[{"kind":"reversal_token_invalid"}]})
    auth=read_json(promotion_directory(runtime_root)/'reversal_authorizations'/f'{parts[0]}.json'); _,record=active_promotion_transaction_private(runtime_root); _,state=current_promotion_state_private(runtime_root)
    if not auth or parts!=[str(auth.get('token_id') or ''),str(auth.get('binding_sha256') or ''),str(auth.get('nonce') or '')]:return _public({"status":"reversal_token_invalid","contradictions":[{"kind":"reversal_token_invalid"}]})
    if _used(runtime_root,token):return _public({"status":"authorization_reused","contradictions":[{"kind":"authorization_reused"}]})
    if state.get('certified') or str(state.get('state') or '')=='certified':return _public({"status":"promotion_reversal_blocked","contradictions":[{"kind":"certification_blocks_reversal"}]})
    for a,v in (("promotion_transaction_id",record.get('promotion_transaction_id')),("promotion_transaction_identity_sha256",record.get('promotion_transaction_identity_sha256')),("state_sha256",state.get('state_sha256')),("generation",state.get('generation')),("promotion_receipt_sha256",record.get('promotion_receipt_sha256')),("target_inventory_sha256",record.get('target_inventory_sha256'))):
        if str(auth.get(a) or '')!=str(v or ''):return _public({"status":"reversal_token_stale","contradictions":[{"kind":"reversal_token_stale"}]})
    _mark_used(runtime_root,token,'promotion_reversed',record['promotion_transaction_id']); d=promotion_directory(runtime_root)
    reversal={"schema":"eidolon-promotion-reversal-receipt-v1","promotion_transaction_id":record['promotion_transaction_id'],"promotion_transaction_identity_sha256":record['promotion_transaction_identity_sha256'],"promotion_receipt_sha256":record['promotion_receipt_sha256'],"candidate_id":record['candidate_id'],"target_project_id":record['target_project_id'],"target_inventory_sha256":record['target_inventory_sha256'],"state":"reversed_to_installed_unpromoted","certified":False,"reversed_at":utc_now(),"content_free":True};reversal['receipt_sha256']=digest_payload(reversal);atomic_json(d/'reversal_receipts'/f"{record['promotion_transaction_id']}.json",reversal)
    newstate={"schema":"eidolon-promotion-authority-state-v1","state_id":f"promotion-state-{int(state['generation'])+1}-{secrets.token_hex(6)}","generation":int(state['generation'])+1,"state":"reversed_to_installed_unpromoted","previous_state":"promoted_uncertified","previous_state_sha256":state['state_sha256'],"promotion_transaction_id":record['promotion_transaction_id'],"promotion_transaction_identity_sha256":record['promotion_transaction_identity_sha256'],"promotion_receipt_sha256":record['promotion_receipt_sha256'],"reversal_receipt_sha256":reversal['receipt_sha256'],"candidate_id":record['candidate_id'],"packaged_version":record['packaged_version'],"target_project_id":record['target_project_id'],"target_inventory_sha256":record['target_inventory_sha256'],"certified":False,"created_at":utc_now(),"content_free":True};newstate['state_sha256']=digest_payload(newstate);atomic_json(d/'states'/f"{newstate['state_id']}.json",newstate);atomic_json(d/'active_promotion_state.json',{"schema":"eidolon-promotion-authority-state-v1","state_id":newstate['state_id'],"generation":newstate['generation'],"state_sha256":newstate['state_sha256'],"state":newstate['state'],"content_free":True});record['reversal_receipt_sha256']=reversal['receipt_sha256'];record['promotion_state_sha256']=newstate['state_sha256'];record['state']=record['status']='reversed_to_installed_unpromoted';_append_event(runtime_root,record['promotion_transaction_id'],record,{"kind":"promotion_reversed","reversal_receipt_sha256":reversal['receipt_sha256']});_save(runtime_root,record);return _public(record)
