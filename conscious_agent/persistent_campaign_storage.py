from __future__ import annotations
"""v1186.0-v1186.2 durable campaign storage and restoration foundations.

Writes only an explicitly supplied external runtime root after an exact operator-
reviewed campaign lineage is provided. Restoration never resumes or executes work.
"""
import hashlib, json, os, re, tempfile
from pathlib import Path
from typing import Any, Mapping

CONTRACT_VERSION="v1186.2"; SCHEMA_VERSION="1"; MAX_BYTES=524_288
DIGEST_RE=re.compile(r"^[0-9a-f]{64}$"); ID_RE=re.compile(r"^[A-Za-z0-9._-]{1,128}$")
DECISIONS=frozenset({"approve","reject","defer"})

def _digest(v:object)->str:
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
def _verify(row:Mapping[str,Any],field:str)->tuple[str,bool]:
    u=dict(row); d=str(u.pop(field,"")).lower(); return d,bool(DIGEST_RE.fullmatch(d) and d==_digest(u))
def _bounded(v:object)->bool:
    return len(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode())<=MAX_BYTES

def create_campaign_storage_record(*,charter:Mapping[str,Any],review:Mapping[str,Any],ledger:Mapping[str,Any],snapshot:Mapping[str,Any],selection:Mapping[str,Any]|None=None,budget_receipt:Mapping[str,Any]|None=None,stale_assessment:Mapping[str,Any]|None=None,recovery_receipt:Mapping[str,Any]|None=None,storage_generation:int=1,prior_record_digest:str="",operator_storage_digest:str)->dict[str,Any]:
    errors=[]; rows={"charter":dict(charter),"review":dict(review),"ledger":dict(ledger),"snapshot":dict(snapshot)}
    optional={"selection":dict(selection or {}),"budget_receipt":dict(budget_receipt or {}),"stale_assessment":dict(stale_assessment or {}),"recovery_receipt":dict(recovery_receipt or {})}
    fields={"charter":"charter_digest","review":"review_digest","ledger":"ledger_digest","snapshot":"snapshot_digest","selection":"selection_digest","budget_receipt":"budget_receipt_digest","stale_assessment":"stale_assessment_digest","recovery_receipt":"recovery_receipt_digest"}
    digests={}
    for name,row in {**rows,**optional}.items():
        if not row:
            digests[name]=""; continue
        d,ok=_verify(row,fields[name]); digests[name]=d
        if not ok: errors.append(f"tampered_{name}")
    cd=digests["charter"]; rd=digests["review"]; ld=digests["ledger"]; sd=digests["snapshot"]
    if review.get("charter_digest")!=cd or ledger.get("charter_digest")!=cd or ledger.get("review_digest")!=rd or snapshot.get("charter_digest")!=cd or snapshot.get("review_digest")!=rd or snapshot.get("ledger_digest")!=ld: errors.append("lineage_mismatch")
    if review.get("status")!="approved_not_started": errors.append("campaign_not_approved")
    cid=str(charter.get("campaign_id") or "")
    if not ID_RE.fullmatch(cid): errors.append("unsafe_campaign_id")
    if not isinstance(storage_generation,int) or storage_generation<1: errors.append("invalid_storage_generation")
    prior=str(prior_record_digest or "").lower()
    if storage_generation==1 and prior: errors.append("unexpected_prior_record_digest")
    if storage_generation>1 and not DIGEST_RE.fullmatch(prior): errors.append("missing_prior_record_digest")
    op=str(operator_storage_digest or "").lower()
    if not DIGEST_RE.fullmatch(op): errors.append("invalid_operator_storage_digest")
    row={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"campaign_id":cid,"storage_generation":storage_generation,"prior_record_digest":prior,"operator_storage_digest":op,"source_baseline_digest":str(charter.get("source_baseline_digest") or ""),"lineage_digests":digests,"campaign_state":str(snapshot.get("state") or ""),"session_id":str(snapshot.get("session_id") or ""),"session_index":int(snapshot.get("session_index") or 0),"status":"ready_for_runtime_storage" if not errors else "blocked","errors":sorted(set(errors)),"error_count":len(set(errors)),"content_free":True,"private_content_included":False,"runtime_write_authorized":not errors,"source_write_authorized":False,"work_execution_authorized":False,"automatic_resume":False,"authority_granted":False}
    if not _bounded(row): row.update(errors=["oversized_contract"],error_count=1,status="blocked",runtime_write_authorized=False)
    row["storage_record_digest"]=_digest(row); return row

def persist_campaign_storage_record(*,runtime_root:str|Path,record:Mapping[str,Any])->dict[str,Any]:
    record=dict(record); errors=[]; digest,ok=_verify(record,"storage_record_digest")
    if not ok: errors.append("tampered_storage_record")
    if record.get("status")!="ready_for_runtime_storage" or not record.get("runtime_write_authorized"): errors.append("storage_not_authorized")
    cid=str(record.get("campaign_id") or "")
    if not ID_RE.fullmatch(cid): errors.append("unsafe_campaign_id")
    root=Path(runtime_root).expanduser().resolve()
    if root.exists() and root.is_symlink(): errors.append("unsafe_runtime_root")
    payload=json.dumps(record,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()
    if len(payload)>MAX_BYTES: errors.append("oversized_contract")
    path=root/"campaigns"/cid/"campaign_state.json"
    previous=""
    if path.exists():
        try:
            old=json.loads(path.read_text(encoding="utf-8")); previous=str(old.get("storage_record_digest") or "")
        except Exception: errors.append("malformed_existing_record")
        if record.get("prior_record_digest")!=previous: errors.append("stale_storage_generation")
    elif int(record.get("storage_generation") or 0)>1: errors.append("missing_prior_record")
    if errors:
        return {"contract_version":CONTRACT_VERSION,"campaign_id":cid,"status":"blocked","errors":sorted(set(errors)),"error_count":len(set(errors)),"runtime_written":False,"source_modified":False,"work_executed":False,"automatic_resume":False,"authority_granted":False,"storage_record_digest":digest}
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=".campaign_state.",suffix=".tmp",dir=str(path.parent))
    try:
        with os.fdopen(fd,"wb") as handle: handle.write(payload); handle.flush(); os.fsync(handle.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
    return {"contract_version":CONTRACT_VERSION,"campaign_id":cid,"status":"stored","errors":[],"error_count":0,"runtime_written":True,"relative_runtime_path":f"campaigns/{cid}/campaign_state.json","storage_record_digest":digest,"stored_payload_digest":hashlib.sha256(payload).hexdigest(),"source_modified":False,"work_executed":False,"automatic_resume":False,"authority_granted":False}

def restore_campaign_storage_record(*,runtime_root:str|Path,campaign_id:str,expected_record_digest:str,current_source_digest:str)->dict[str,Any]:
    errors=[]; cid=str(campaign_id or ""); expected=str(expected_record_digest or "").lower(); current=str(current_source_digest or "").lower()
    if not ID_RE.fullmatch(cid): errors.append("unsafe_campaign_id")
    if not DIGEST_RE.fullmatch(expected): errors.append("invalid_expected_record_digest")
    if not DIGEST_RE.fullmatch(current): errors.append("invalid_current_source_digest")
    path=Path(runtime_root).expanduser().resolve()/"campaigns"/cid/"campaign_state.json"; record={}
    if not errors:
        try: record=json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError: errors.append("record_not_found")
        except Exception: errors.append("malformed_stored_record")
    if record:
        digest,ok=_verify(record,"storage_record_digest")
        if not ok: errors.append("tampered_stored_record")
        if digest!=expected: errors.append("record_digest_mismatch")
        if record.get("campaign_id")!=cid: errors.append("campaign_id_mismatch")
    source_drift=bool(record and current!=str(record.get("source_baseline_digest") or ""))
    status="restoration_review_required" if not errors and not source_drift else ("reconciliation_required" if not errors else "blocked")
    row={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"campaign_id":cid,"expected_record_digest":expected,"restored_record_digest":str(record.get("storage_record_digest") or ""),"storage_generation":int(record.get("storage_generation") or 0),"campaign_state":str(record.get("campaign_state") or ""),"session_id":str(record.get("session_id") or ""),"session_index":int(record.get("session_index") or 0),"current_source_digest":current,"stored_source_baseline_digest":str(record.get("source_baseline_digest") or ""),"source_drift":source_drift,"status":status,"errors":sorted(set(errors)),"error_count":len(set(errors)),"content_free":True,"record_loaded":bool(record) and not errors,"work_resumed":False,"automatic_resume":False,"provider_contacted":False,"model_contacted":False,"source_modified":False,"authority_granted":False}
    row["restoration_digest"]=_digest(row); return row

def create_restoration_review(*,restoration:Mapping[str,Any],decision:str,operator_decision_digest:str)->dict[str,Any]:
    errors=[]; restoration=dict(restoration); dg,ok=_verify(restoration,"restoration_digest")
    if not ok: errors.append("tampered_restoration")
    decision=str(decision or "")
    if decision not in DECISIONS: errors.append("unsupported_decision")
    if restoration.get("status") not in {"restoration_review_required","reconciliation_required"}: errors.append("restoration_not_reviewable")
    op=str(operator_decision_digest or "").lower()
    if not DIGEST_RE.fullmatch(op): errors.append("invalid_operator_decision_digest")
    status=("approved_not_resumed" if decision=="approve" else "rejected" if decision=="reject" else "deferred") if not errors else "blocked"
    row={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"campaign_id":restoration.get("campaign_id",""),"restoration_digest":dg,"decision":decision,"operator_decision_digest":op,"status":status,"errors":sorted(set(errors)),"error_count":len(set(errors)),"content_free":True,"work_resumed":False,"automatic_resume":False,"execution_authorized":False,"authority_granted":False}
    row["restoration_review_digest"]=_digest(row); return row

def storage_public_summary(record:Mapping[str,Any],stored:Mapping[str,Any],restoration:Mapping[str,Any],review:Mapping[str,Any])->dict[str,Any]:
    return {"contract_version":CONTRACT_VERSION,"campaign_id":record.get("campaign_id",""),"storage_status":stored.get("status",""),"storage_generation":record.get("storage_generation",0),"restoration_status":restoration.get("status",""),"source_drift":bool(restoration.get("source_drift")),"review_status":review.get("status",""),"content_free":True,"runtime_written":bool(stored.get("runtime_written")),"source_modified":False,"work_resumed":False,"automatic_resume":False,"authority_granted":False}
