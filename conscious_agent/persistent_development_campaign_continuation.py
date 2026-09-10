from __future__ import annotations
"""v1185.3-v1185.5 persistent campaign continuation, pause/resume, and bounded work selection.

This module creates content-free state and review receipts only. It does not execute
work, consume real resources, modify source, or grant implementation authority.
"""
import hashlib, json, re
from typing import Any, Mapping, Sequence

CONTRACT_VERSION="v1185.5"; SCHEMA_VERSION="1"; MAX_BYTES=262_144; MAX_ITEMS=128
DIGEST_RE=re.compile(r"^[0-9a-f]{64}$")
SESSION_STATES=frozenset({"ready","active","paused","completed","abandoned"})
TRANSITIONS={"ready":{"active","abandoned"},"active":{"paused","completed","abandoned"},"paused":{"active","abandoned"},"completed":set(),"abandoned":set()}
DECISIONS=frozenset({"approve","reject","defer"})

def _digest(v:object)->str:
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
def _bounded(v:object)->bool:
    return len(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode())<=MAX_BYTES

def _verify(row:Mapping[str,Any], field:str)->tuple[str,bool]:
    unsigned=dict(row); digest=str(unsigned.pop(field,"")).lower()
    return digest, bool(DIGEST_RE.fullmatch(digest) and digest==_digest(unsigned))

def create_campaign_session_snapshot(*, charter:Mapping[str,Any], review:Mapping[str,Any], ledger:Mapping[str,Any],
        session_id:str, session_index:int, state:str="ready", prior_snapshot_digest:str="",
        consumed:Mapping[str,int]|None=None)->dict[str,Any]:
    errors=[]; charter=dict(charter); review=dict(review); ledger=dict(ledger); consumed=dict(consumed or {})
    cd,cok=_verify(charter,"charter_digest"); rd,rok=_verify(review,"review_digest"); ld,lok=_verify(ledger,"ledger_digest")
    if not cok: errors.append("tampered_charter")
    if not rok: errors.append("tampered_review")
    if not lok: errors.append("tampered_ledger")
    if review.get("charter_digest")!=cd or ledger.get("charter_digest")!=cd or ledger.get("review_digest")!=rd: errors.append("lineage_mismatch")
    if review.get("status")!="approved_not_started": errors.append("campaign_not_approved")
    sid=str(session_id or "").strip(); state=str(state or "").strip()
    if not sid or len(sid)>128 or not isinstance(session_index,int) or session_index<1: errors.append("invalid_session_identity")
    if state not in SESSION_STATES: errors.append("unsupported_session_state")
    if prior_snapshot_digest and not DIGEST_RE.fullmatch(str(prior_snapshot_digest).lower()): errors.append("invalid_prior_snapshot_digest")
    limits=dict(charter.get("limits") or {}); allowed={"work_items","sessions","elapsed_seconds","disk_bytes","token_budget"}
    clean={str(k):int(v) for k,v in consumed.items() if str(k) in allowed and isinstance(v,int)}
    if set(consumed)-allowed or any(v<0 for v in clean.values()): errors.append("invalid_consumption")
    comparisons={"work_items":"max_work_items","sessions":"max_sessions","elapsed_seconds":"max_elapsed_seconds","disk_bytes":"max_disk_bytes","token_budget":"max_token_budget"}
    for key,limit_key in comparisons.items():
        if key in clean and limit_key in limits and clean[key]>int(limits[limit_key]): errors.append(f"{key}_budget_exceeded")
    row={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"campaign_id":charter.get("campaign_id",""),
         "charter_digest":cd,"review_digest":rd,"ledger_digest":ld,"session_id":sid,"session_index":session_index,
         "state":state,"prior_snapshot_digest":str(prior_snapshot_digest or "").lower(),"consumed":clean,
         "status":"session_snapshot_ready" if not errors else "blocked","errors":sorted(set(errors)),"error_count":len(set(errors)),
         "content_free":True,"private_content_included":False,"durable_write_performed":False,"work_executed":False,
         "source_modified":False,"provider_contacted":False,"model_contacted":False,"authority_granted":False}
    if not _bounded(row): row.update(errors=["oversized_contract"],error_count=1,status="blocked")
    row["snapshot_digest"]=_digest(row); return row

def create_work_selection_review(*, snapshot:Mapping[str,Any], ledger:Mapping[str,Any], candidate_work_item_ids:Sequence[str],
        decision:str, operator_decision_digest:str)->dict[str,Any]:
    errors=[]; snapshot=dict(snapshot); ledger=dict(ledger); sd,sok=_verify(snapshot,"snapshot_digest"); ld,lok=_verify(ledger,"ledger_digest")
    if not sok: errors.append("tampered_snapshot")
    if not lok: errors.append("tampered_ledger")
    if snapshot.get("ledger_digest")!=ld: errors.append("snapshot_ledger_mismatch")
    if snapshot.get("status")!="session_snapshot_ready" or snapshot.get("state") not in {"ready","active","paused"}: errors.append("snapshot_not_selectable")
    ids=[str(x or "").strip() for x in candidate_work_item_ids]
    if not ids or len(ids)>MAX_ITEMS or any(not x or len(x)>128 for x in ids): errors.append("invalid_candidate_work_items")
    if len(set(ids))!=len(ids): errors.append("duplicate_candidate_work_items")
    known=set(ledger.get("work_item_ids") or [])
    if any(x not in known for x in ids): errors.append("unknown_work_item")
    decision=str(decision or "").strip()
    if decision not in DECISIONS: errors.append("unsupported_decision")
    if not DIGEST_RE.fullmatch(str(operator_decision_digest or "").lower()): errors.append("invalid_operator_decision_digest")
    row={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"campaign_id":snapshot.get("campaign_id",""),
         "snapshot_digest":sd,"ledger_digest":ld,"candidate_work_item_ids":ids,"decision":decision,
         "operator_decision_digest":str(operator_decision_digest or "").lower(),
         "status":"selection_approved" if not errors and decision=="approve" else ("selection_rejected" if not errors and decision=="reject" else ("selection_deferred" if not errors else "blocked")),
         "errors":sorted(set(errors)),"error_count":len(set(errors)),"content_free":True,"work_executed":False,
         "selection_only":True,"implementation_authorized":False,"authority_granted":False}
    if not _bounded(row): row.update(errors=["oversized_contract"],error_count=1,status="blocked")
    row["selection_review_digest"]=_digest(row); return row

def create_bounded_work_selection(*, charter:Mapping[str,Any], snapshot:Mapping[str,Any], ledger:Mapping[str,Any],
        selection_review:Mapping[str,Any], max_items:int=1)->dict[str,Any]:
    errors=[]; charter=dict(charter); snapshot=dict(snapshot); ledger=dict(ledger); selection_review=dict(selection_review)
    cd,cok=_verify(charter,"charter_digest"); sd,sok=_verify(snapshot,"snapshot_digest"); ld,lok=_verify(ledger,"ledger_digest"); qd,qok=_verify(selection_review,"selection_review_digest")
    for ok,name in [(cok,"charter"),(sok,"snapshot"),(lok,"ledger"),(qok,"selection_review")]:
        if not ok: errors.append(f"tampered_{name}")
    if snapshot.get("charter_digest")!=cd or snapshot.get("ledger_digest")!=ld or selection_review.get("snapshot_digest")!=sd or selection_review.get("ledger_digest")!=ld: errors.append("lineage_mismatch")
    if selection_review.get("status")!="selection_approved": errors.append("selection_not_approved")
    if not isinstance(max_items,int) or max_items<1: errors.append("invalid_selection_limit")
    charter_limit=int((charter.get("limits") or {}).get("max_work_items",0) or 0)
    if charter_limit and max_items>charter_limit: errors.append("selection_limit_exceeds_campaign")
    ids=list(selection_review.get("candidate_work_item_ids") or [])
    selected=ids[:max_items] if not errors else []
    row={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"campaign_id":charter.get("campaign_id",""),
         "snapshot_digest":sd,"ledger_digest":ld,"selection_review_digest":qd,"selected_work_item_ids":selected,
         "selected_count":len(selected),"status":"bounded_selection_ready" if not errors else "blocked",
         "errors":sorted(set(errors)),"error_count":len(set(errors)),"content_free":True,"work_executed":False,
         "budget_consumed":False,"source_modified":False,"provider_contacted":False,"model_contacted":False,
         "operator_review_required_before_execution":True,"authority_granted":False}
    row["selection_digest"]=_digest(row); return row

def create_session_transition(*, snapshot:Mapping[str,Any], requested_state:str, operator_transition_digest:str)->dict[str,Any]:
    errors=[]; snapshot=dict(snapshot); sd,sok=_verify(snapshot,"snapshot_digest")
    if not sok: errors.append("tampered_snapshot")
    current=str(snapshot.get("state") or ""); requested=str(requested_state or "")
    if requested not in SESSION_STATES or requested not in TRANSITIONS.get(current,set()): errors.append("invalid_state_transition")
    if not DIGEST_RE.fullmatch(str(operator_transition_digest or "").lower()): errors.append("invalid_operator_transition_digest")
    row={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"campaign_id":snapshot.get("campaign_id",""),
         "snapshot_digest":sd,"from_state":current,"to_state":requested,"operator_transition_digest":str(operator_transition_digest or "").lower(),
         "status":"transition_recorded" if not errors else "blocked","errors":sorted(set(errors)),"error_count":len(set(errors)),
         "content_free":True,"durable_write_performed":False,"work_executed":False,"automatic_resume":False,"authority_granted":False}
    row["transition_digest"]=_digest(row); return row

def continuation_public_summary(snapshot:Mapping[str,Any], selection:Mapping[str,Any]|None=None, transition:Mapping[str,Any]|None=None)->dict[str,Any]:
    selection=dict(selection or {}); transition=dict(transition or {})
    return {"contract_version":CONTRACT_VERSION,"campaign_id":snapshot.get("campaign_id",""),"session_id":snapshot.get("session_id",""),
            "session_index":snapshot.get("session_index",0),"session_state":snapshot.get("state",""),"snapshot_digest":snapshot.get("snapshot_digest",""),
            "selection_status":selection.get("status","not_requested"),"selected_count":selection.get("selected_count",0),
            "transition_status":transition.get("status","not_requested"),"content_free":True,"work_executed":False,
            "automatic_resume":False,"operator_review_required_before_execution":True,"authority_granted":False}
