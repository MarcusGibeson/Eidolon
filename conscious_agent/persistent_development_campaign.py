from __future__ import annotations
"""v1185.0-v1185.2 persistent supervised development-campaign foundations.

Defines one content-free campaign charter, bounded goals, limits, work ledger,
and an explicit operator review. It performs no project work and grants no
execution, installation, promotion, certification, release, or autonomous authority.
"""
import hashlib, json, re
from typing import Any, Mapping, Sequence

CONTRACT_VERSION="v1185.2"; SCHEMA_VERSION="1"; MAX_BYTES=262_144; MAX_GOALS=16; MAX_LEDGER=128
DIGEST_RE=re.compile(r"^[0-9a-f]{64}$")
DECISIONS=frozenset({"approve","reject","defer"})
STATUSES=frozenset({"planned","ready_for_review","blocked","closed"})

def _digest(v:object)->str:
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
def _bounded(v:object)->bool:
    return len(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode())<=MAX_BYTES

def create_campaign_charter(*, campaign_id:str, source_baseline_digest:str, scope_digest:str,
        goal_digests:Sequence[str], limits:Mapping[str,int], operator_review_digest:str="") -> dict[str,Any]:
    errors=[]; cid=str(campaign_id or "").strip(); goals=[str(x).lower() for x in goal_digests]
    allowed_limits={"max_work_items","max_sessions","max_elapsed_seconds","max_disk_bytes","max_token_budget"}
    clean_limits={str(k):int(v) for k,v in dict(limits or {}).items() if str(k) in allowed_limits and isinstance(v,int)}
    if not cid or len(cid)>128: errors.append("invalid_campaign_id")
    for name,value in (("source_baseline_digest",source_baseline_digest),("scope_digest",scope_digest)):
        if not DIGEST_RE.fullmatch(str(value or "").lower()): errors.append(f"invalid_{name}")
    if not goals or len(goals)>MAX_GOALS or any(not DIGEST_RE.fullmatch(x) for x in goals): errors.append("invalid_goal_digests")
    if len(set(goals))!=len(goals): errors.append("duplicate_goals")
    if set(dict(limits or {})) - allowed_limits or not clean_limits or any(v<=0 for v in clean_limits.values()): errors.append("invalid_limits")
    if operator_review_digest and not DIGEST_RE.fullmatch(str(operator_review_digest).lower()): errors.append("invalid_operator_review_digest")
    row={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"campaign_id":cid,
         "source_baseline_digest":str(source_baseline_digest or "").lower(),"scope_digest":str(scope_digest or "").lower(),
         "goal_digests":goals,"limits":clean_limits,"operator_review_digest":str(operator_review_digest or "").lower(),
         "status":"ready_for_review" if not errors else "blocked","errors":sorted(set(errors)),"error_count":len(set(errors)),
         "content_free":True,"private_content_included":False,"work_started":False,"source_modified":False,
         "execution_invoked":False,"approval_created":False,"authority_granted":False,"autonomous_action_authorized":False}
    if not _bounded(row): row["errors"]=["oversized_contract"]; row["error_count"]=1; row["status"]="blocked"
    row["charter_digest"]=_digest(row); return row

def create_campaign_review(*, charter:Mapping[str,Any], decision:str, operator_decision_digest:str)->dict[str,Any]:
    errors=[]; decision=str(decision or "").strip(); charter=dict(charter)
    unsigned=dict(charter); digest=str(unsigned.pop("charter_digest","")).lower()
    if not DIGEST_RE.fullmatch(digest) or digest!=_digest(unsigned): errors.append("tampered_charter")
    if charter.get("status")!="ready_for_review" or charter.get("error_count")!=0: errors.append("charter_not_reviewable")
    if decision not in DECISIONS: errors.append("unsupported_decision")
    if not DIGEST_RE.fullmatch(str(operator_decision_digest or "").lower()): errors.append("invalid_operator_decision_digest")
    row={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"campaign_id":charter.get("campaign_id",""),
         "charter_digest":digest,"decision":decision,"operator_decision_digest":str(operator_decision_digest or "").lower(),
         "status":"approved_not_started" if not errors and decision=="approve" else ("rejected" if not errors and decision=="reject" else ("deferred" if not errors else "blocked")),
         "errors":sorted(set(errors)),"error_count":len(set(errors)),"content_free":True,"work_started":False,
         "execution_invoked":False,"approval_limited_to_campaign_charter":decision=="approve" and not errors,
         "implementation_authorized":False,"source_application_authorized":False,"release_authorized":False,"authority_granted":False}
    row["review_digest"]=_digest(row); return row

def create_campaign_ledger(*, charter:Mapping[str,Any], review:Mapping[str,Any], work_items:Sequence[Mapping[str,Any]]=())->dict[str,Any]:
    errors=[]; charter=dict(charter); review=dict(review); items=[dict(x) for x in work_items]
    cu=dict(charter); cd=str(cu.pop("charter_digest","")).lower(); ru=dict(review); rd=str(ru.pop("review_digest","")).lower()
    if not DIGEST_RE.fullmatch(cd) or cd!=_digest(cu): errors.append("tampered_charter")
    if not DIGEST_RE.fullmatch(rd) or rd!=_digest(ru): errors.append("tampered_review")
    if review.get("charter_digest")!=cd: errors.append("review_charter_mismatch")
    if review.get("status")!="approved_not_started": errors.append("campaign_not_approved")
    if len(items)>MAX_LEDGER: errors.append("oversized_ledger")
    seen=set()
    for item in items:
        iid=str(item.get("work_item_id") or ""); status=str(item.get("status") or "")
        if not iid or iid in seen: errors.append("invalid_or_duplicate_work_item")
        seen.add(iid)
        if status not in {"queued","blocked","completed","cancelled"}: errors.append("unsupported_work_item_status")
        if not DIGEST_RE.fullmatch(str(item.get("work_item_digest") or "").lower()): errors.append("invalid_work_item_digest")
        if item.get("content_free") is not True: errors.append("privacy_contract_violation")
    row={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"campaign_id":charter.get("campaign_id",""),
         "charter_digest":cd,"review_digest":rd,"work_item_count":len(items),"work_item_ids":[x.get("work_item_id","") for x in items],
         "status":"approved_empty_ledger" if not errors and not items else ("approved_bounded_ledger" if not errors else "blocked"),
         "errors":sorted(set(errors)),"error_count":len(set(errors)),"content_free":True,"private_content_included":False,
         "work_started":False,"execution_invoked":False,"source_modified":False,"authority_granted":False,
         "operator_review_required_for_work_selection":True}
    if not _bounded(row): row["errors"]=["oversized_contract"]; row["error_count"]=1; row["status"]="blocked"
    row["ledger_digest"]=_digest(row); return row

def campaign_public_summary(charter:Mapping[str,Any], review:Mapping[str,Any], ledger:Mapping[str,Any])->dict[str,Any]:
    return {"contract_version":CONTRACT_VERSION,"campaign_id":charter.get("campaign_id",""),"charter_status":charter.get("status",""),
            "review_status":review.get("status",""),"ledger_status":ledger.get("status",""),"goal_count":len(charter.get("goal_digests") or []),
            "work_item_count":int(ledger.get("work_item_count") or 0),"charter_digest":charter.get("charter_digest",""),
            "review_digest":review.get("review_digest",""),"ledger_digest":ledger.get("ledger_digest",""),"content_free":True,
            "work_started":False,"operator_review_required_for_work_selection":True,"authority_granted":False}
