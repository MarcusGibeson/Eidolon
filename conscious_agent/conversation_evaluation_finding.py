from __future__ import annotations

"""Private v1089.0 operator evaluation-finding intake.

Findings are explicit operator records beneath EIDOLON_DATA_DIR. Public evidence
contains bounded labels, opaque references, presence flags, counts, and digests
only. No transcript is inspected and no task, patch, provider call, approval,
installation, promotion, or release decision is created here.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib, json, os, re, threading, time, uuid
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping

from paths import DATA_DIR
from conversation_daily_evaluation_protocol import ISSUE_DOMAINS, ISSUE_SEVERITIES

FINDING_SCHEMA_VERSION = "1"
EVALUATION_FINDINGS_DIR = DATA_DIR / "conversation_evaluation_findings"
FINDING_STATES = ("open", "under_review", "resolved", "dismissed")
MAX_FINDING_TITLE_CHARS = 240
MAX_FINDING_DETAILS_CHARS = 4000
MAX_FINDINGS_RETURNED = 256
_ID_RE = re.compile(r"^eval_finding_[0-9]{8}T[0-9]{6}_[a-f0-9]{12}$")
_LOCK = threading.RLock(); _LOCK_TIMEOUT=8.0; _STALE=120.0

class EvaluationFindingError(ValueError): pass

def _now() -> str: return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()
def _new_id() -> str: return f"eval_finding_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:12]}"
def _valid_id(value: str) -> str:
    token=str(value or "").strip()
    if not _ID_RE.fullmatch(token): raise EvaluationFindingError("Invalid evaluation finding identifier.")
    return token
def _path(fid: str) -> Path: return EVALUATION_FINDINGS_DIR/f"{_valid_id(fid)}.json"
def _lock_path() -> Path: return EVALUATION_FINDINGS_DIR/".findings.lock"
def _load(path: Path) -> dict[str,Any] | None:
    try: value=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError): return None
    return value if isinstance(value,dict) else None
def _write(path: Path, value: Mapping[str,Any]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        tmp.write_text(json.dumps(dict(value),indent=2,sort_keys=True),encoding="utf-8")
        tmp.replace(path)
    finally: tmp.unlink(missing_ok=True)
@contextmanager
def finding_storage_lock() -> Iterator[None]:
    with _LOCK:
        lp=_lock_path(); lp.parent.mkdir(parents=True,exist_ok=True); deadline=time.monotonic()+_LOCK_TIMEOUT; fd=None
        while fd is None:
            try:
                fd=os.open(lp,os.O_CREAT|os.O_EXCL|os.O_WRONLY); os.write(fd,f"{os.getpid()}\n".encode()); os.fsync(fd)
            except FileExistsError:
                try: age=max(0.0,time.time()-lp.stat().st_mtime)
                except OSError: age=0.0
                if age>=_STALE:
                    try: lp.unlink()
                    except OSError: pass
                    continue
                if time.monotonic()>=deadline: raise EvaluationFindingError("Evaluation findings are being updated by another process. Reload before trying again.")
                time.sleep(.02)
        try: yield
        finally:
            try: os.close(fd)
            except OSError: pass
            try: lp.unlink()
            except OSError: pass

def _bounded(value: str, maximum: int, label: str, *, required: bool=False) -> str:
    token=str(value or "").strip()
    if required and not token: raise EvaluationFindingError(f"{label} is required.")
    if len(token)>maximum: raise EvaluationFindingError(f"{label} exceeds the {maximum}-character limit.")
    return token

def load_evaluation_finding_private(finding_id: str) -> dict[str,Any]:
    value=_load(_path(finding_id))
    if not value or value.get("type")!="desktop_alpha_evaluation_finding": raise EvaluationFindingError("Evaluation finding not found.")
    return value

def iter_evaluation_findings_private() -> Iterator[dict[str,Any]]:
    if not EVALUATION_FINDINGS_DIR.exists(): return
    for path in sorted(EVALUATION_FINDINGS_DIR.glob("eval_finding_*.json")):
        value=_load(path)
        if value and value.get("type")=="desktop_alpha_evaluation_finding": yield value

def finding_public_summary(value: Mapping[str,Any]) -> dict[str,Any]:
    title=str(value.get("private_title") or ""); details=str(value.get("private_details") or "")
    attempts=[x for x in list(value.get("reproduction_attempts") or []) if isinstance(x,Mapping)]
    refs=[x for x in list(value.get("repair_candidate_refs") or []) if isinstance(x,Mapping)]
    return {
      "ok":True,"type":"desktop_alpha_evaluation_finding_summary","schema_version":FINDING_SCHEMA_VERSION,
      "finding_id":str(value.get("finding_id") or ""),"state":str(value.get("state") or "open"),
      "revision":max(0,int(value.get("revision") or 0)),"created_at":str(value.get("created_at") or ""),"updated_at":str(value.get("updated_at") or ""),
      "campaign_id":str(value.get("campaign_id") or ""),"evaluation_id":str(value.get("evaluation_id") or ""),
      "issue_domain":str(value.get("issue_domain") or "none"),"severity":str(value.get("severity") or "none"),
      "finding_title_present":bool(title),"finding_title_digest":_digest(title) if title else "",
      "finding_details_present":bool(details),"finding_details_digest":_digest(details) if details else "",
      "reproduction_attempt_count":len(attempts),"repair_candidate_reference_count":len(refs),
      "record_digest":_digest({"finding_id":value.get("finding_id"),"state":value.get("state"),"revision":value.get("revision"),"campaign_id":value.get("campaign_id"),"evaluation_id":value.get("evaluation_id"),"issue_domain":value.get("issue_domain"),"severity":value.get("severity"),"title":_digest(title) if title else "","details":_digest(details) if details else "","attempt_count":len(attempts),"reference_count":len(refs)}),
      "private_title_returned":False,"private_details_returned":False,"operator_confirmation_required":True,"optimistic_revision_required":True,
      "transcript_inspected":False,"prompt_inspected":False,"memory_inspected":False,"provider_invoked":False,"automatic_reproduction":False,
      "automatic_task_created":False,"automatic_work_item_created":False,"patch_generated":False,"patch_applied":False,"approval_granted":False,
      "rollback_authorized":False,"installation_performed":False,"promotion_performed":False,"release_certified":False,
      "source_tree_written":False,"content_free":True,"redacted":True,
    }

def _validate_refs(campaign_id: str, evaluation_id: str) -> tuple[str,str]:
    campaign=str(campaign_id or "").strip(); evaluation=str(evaluation_id or "").strip()
    if not campaign and not evaluation: raise EvaluationFindingError("A campaign_id, evaluation_id, or both is required.")
    if campaign:
        from conversation_evaluation_campaign import load_evaluation_campaign_private, EvaluationCampaignError
        try: c=load_evaluation_campaign_private(campaign)
        except EvaluationCampaignError as e: raise EvaluationFindingError(str(e)) from e
        if evaluation:
            enrolled={str(x.get("evaluation_id") or "") for x in list(c.get("evaluation_refs") or []) if isinstance(x,Mapping)}
            if evaluation not in enrolled: raise EvaluationFindingError("The evaluation is not enrolled in the referenced campaign.")
    if evaluation:
        from conversation_daily_evaluation import load_daily_evaluation, DailyEvaluationError
        try: load_daily_evaluation(evaluation)
        except DailyEvaluationError as e: raise EvaluationFindingError(str(e)) from e
    return campaign,evaluation

def create_evaluation_finding(*,finding_title:str,finding_details:str="",issue_domain:str,severity:str,campaign_id:str="",evaluation_id:str="",operator_confirmed:bool,finding_id:str="") -> dict[str,Any]:
    if not operator_confirmed: raise EvaluationFindingError("Explicit operator confirmation is required to create a finding.")
    domain=str(issue_domain or "").strip().lower(); sev=str(severity or "").strip().lower()
    if domain not in ISSUE_DOMAINS or domain=="none": raise EvaluationFindingError("A supported non-none issue domain is required.")
    if sev not in ISSUE_SEVERITIES or sev=="none": raise EvaluationFindingError("A supported non-none severity is required.")
    campaign,evaluation=_validate_refs(campaign_id,evaluation_id)
    title=_bounded(finding_title,MAX_FINDING_TITLE_CHARS,"Finding title",required=True); details=_bounded(finding_details,MAX_FINDING_DETAILS_CHARS,"Finding details")
    token=_valid_id(finding_id) if finding_id else _new_id(); now=_now()
    with finding_storage_lock():
        # Open duplicate with the same explicit refs/domain/title is idempotent.
        for existing in iter_evaluation_findings_private() or ():
            if str(existing.get("state") or "open") in {"open","under_review"} and str(existing.get("campaign_id") or "")==campaign and str(existing.get("evaluation_id") or "")==evaluation and str(existing.get("issue_domain") or "")==domain and str(existing.get("private_title") or "")==title:
                result=finding_public_summary(existing); result["duplicate_finding"]=True; return result
        path=_path(token)
        if path.exists(): raise EvaluationFindingError("Evaluation finding already exists.")
        record={"type":"desktop_alpha_evaluation_finding","schema_version":FINDING_SCHEMA_VERSION,"finding_id":token,"state":"open","revision":1,"created_at":now,"updated_at":now,"resolved_at":"","dismissed_at":"","campaign_id":campaign,"evaluation_id":evaluation,"issue_domain":domain,"severity":sev,"private_title":title,"private_details":details,"reproduction_attempts":[],"repair_candidate_refs":[],"operator_confirmed":True}
        _write(path,record)
    result=finding_public_summary(record); result["duplicate_finding"]=False; return result

def mutate_evaluation_finding(finding_id:str,*,expected_revision:int|None,operator_confirmed:bool,mutator:Callable[[dict[str,Any]],None]) -> dict[str,Any]:
    if not operator_confirmed: raise EvaluationFindingError("Explicit operator confirmation is required to update a finding.")
    token=_valid_id(finding_id)
    with finding_storage_lock():
        record=load_evaluation_finding_private(token); current=max(0,int(record.get("revision") or 0))
        if expected_revision is None or int(expected_revision)!=current: raise EvaluationFindingError("Finding revision is stale. Reload before trying again.")
        mutator(record); record["revision"]=current+1; record["updated_at"]=_now(); _write(_path(token),record)
    return finding_public_summary(record)

def update_evaluation_finding_details(finding_id:str,*,finding_title:str,finding_details:str,issue_domain:str,severity:str,expected_revision:int|None,operator_confirmed:bool)->dict[str,Any]:
    domain=str(issue_domain or "").strip().lower(); sev=str(severity or "").strip().lower()
    if domain not in ISSUE_DOMAINS or domain=="none": raise EvaluationFindingError("A supported non-none issue domain is required.")
    if sev not in ISSUE_SEVERITIES or sev=="none": raise EvaluationFindingError("A supported non-none severity is required.")
    title=_bounded(finding_title,MAX_FINDING_TITLE_CHARS,"Finding title",required=True); details=_bounded(finding_details,MAX_FINDING_DETAILS_CHARS,"Finding details")
    def apply(r): r.update(private_title=title,private_details=details,issue_domain=domain,severity=sev)
    return mutate_evaluation_finding(finding_id,expected_revision=expected_revision,operator_confirmed=operator_confirmed,mutator=apply)

def set_evaluation_finding_state(finding_id:str,*,state:str,expected_revision:int|None,operator_confirmed:bool)->dict[str,Any]:
    token=str(state or "").strip().lower()
    if token not in FINDING_STATES: raise EvaluationFindingError("Unsupported finding state.")
    def apply(r):
        r["state"]=token
        if token=="resolved": r["resolved_at"]=_now()
        if token=="dismissed": r["dismissed_at"]=_now()
    return mutate_evaluation_finding(finding_id,expected_revision=expected_revision,operator_confirmed=operator_confirmed,mutator=apply)

def load_evaluation_finding(finding_id:str,*,include_private:bool=False)->dict[str,Any]:
    record=load_evaluation_finding_private(finding_id); result=finding_public_summary(record)
    if include_private:
        result["private_title"]=str(record.get("private_title") or ""); result["private_details"]=str(record.get("private_details") or ""); result["private_title_returned"]=True; result["private_details_returned"]=True; result["content_free"]=False; result["redacted"]=False
    return result

def list_evaluation_findings(*,campaign_id:str="",evaluation_id:str="",state:str="",limit:int=100)->dict[str,Any]:
    cap=max(1,min(MAX_FINDINGS_RETURNED,int(limit or 100))); rows=[]
    for record in iter_evaluation_findings_private() or ():
        if campaign_id and str(record.get("campaign_id") or "")!=campaign_id: continue
        if evaluation_id and str(record.get("evaluation_id") or "")!=evaluation_id: continue
        if state and str(record.get("state") or "")!=state: continue
        rows.append(finding_public_summary(record))
    rows=rows[-cap:]
    return {"ok":True,"type":"desktop_alpha_evaluation_finding_list","finding_count":len(rows),"maximum_findings":MAX_FINDINGS_RETURNED,"findings":rows,"findings_digest":_digest(rows),"private_content_returned":False,"provider_invoked":False,"automatic_task_created":False,"patch_generated":False,"release_certified":False,"writes_state":False,"content_free":True,"redacted":True}

def evaluation_finding_summary_contains_private_fields(value: Mapping[str,Any]|None)->bool:
    forbidden={"private_title","private_details","finding_title","finding_details","content","text","message","messages","transcript","prompt","note","notes","environment_label","reference_value","private_reference_value","provider_payload","credentials","vectors","embedding","hidden_reasoning","chain_of_thought"}
    stack=[value]
    while stack:
        cur=stack.pop()
        if isinstance(cur,Mapping):
            if forbidden & {str(k) for k in cur}: return True
            stack.extend(cur.values())
        elif isinstance(cur,(list,tuple)): stack.extend(cur)
    return False
