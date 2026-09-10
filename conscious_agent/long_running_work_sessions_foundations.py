from __future__ import annotations

"""v1271.0-v1271.2 durable long-running work-session foundations.

The session is a content-minimized supervisory envelope around the existing
v1270 self-development campaign.  It records progress and operator controls;
it never substitutes for the exact v1265/v1267/v1269 authorizations.
"""

import hashlib, json, os, re, tempfile, time
from pathlib import Path
from typing import Any, Iterable, Mapping

from ordinary_chat_development_campaign import _proposal_lock
from self_development_alpha_foundations import (
    ALPHA_DENIED_AUTHORITY, _runtime_root, load_self_development_alpha_campaign,
    validate_self_development_alpha_campaign,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1271.2"
MAX_RECEIPTS = 48
MAX_SUMMARIES = 8
MAX_COMPLETED_CODES = 64
MAX_ATTEMPTED_CODES = 64
DEFAULT_LEASE_SECONDS = 120
DEFAULT_PHASE_BUDGET_SECONDS = 900
MAX_RECORD_BYTES = 4 * 1024 * 1024

SESSION_STATES = frozenset({"active", "paused", "interrupted", "cancelled", "completed", "blocked"})
OUTCOMES = frozenset({"attempted", "completed", "blocked", "cancelled", "skipped"})
PHASE_ORDER = {
    "prepared": 0,
    "candidate_execution": 1,
    "repair_authorization_required": 2,
    "verification_and_repair": 3,
    "operator_review_required": 4,
    "review_decided": 5,
    "cancelled": 6,
    "blocked": 7,
}
AUTHORITY_FLAGS = {
    **ALPHA_DENIED_AUTHORITY,
    "long_session_resume_authorized": False,
    "long_session_control_is_execution_authority": False,
    "lease_is_execution_authority": False,
    "heartbeat_is_execution_authority": False,
    "verification_budget_is_test_authority": False,
    "automatic_resume_authorized": False,
    "automatic_retry_authorized": False,
}
_HEX64 = re.compile(r"^[a-f0-9]{64}$")
_ID = re.compile(r"^longwork_[a-f0-9]{24}$")
_OWNER = re.compile(r"^[a-zA-Z0-9_.:-]{1,96}$")
_SAFE_CODE = re.compile(r"^[a-z0-9][a-z0-9_.:-]{0,95}$")


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()


def _root(runtime_root: str | Path | None) -> Path:
    return _runtime_root(runtime_root) / "long_running_work_sessions"


def _path(session_id: str, runtime_root: str | Path | None) -> Path:
    if not _ID.fullmatch(str(session_id or "")):
        raise ValueError("invalid_long_running_work_session_id")
    return _root(runtime_root) / "sessions" / f"{session_id}.json"


def _write(path: Path, row: Mapping[str, Any]) -> None:
    data=(json.dumps(dict(row),indent=2,sort_keys=True,ensure_ascii=True)+"\n").encode()
    if len(data)>MAX_RECORD_BYTES: raise ValueError("long_running_work_session_record_too_large")
    path.parent.mkdir(parents=True,exist_ok=True); tmp=None
    try:
        with tempfile.NamedTemporaryFile("wb",delete=False,dir=path.parent,suffix=".tmp") as h:
            h.write(data);h.flush();os.fsync(h.fileno());tmp=Path(h.name)
        os.replace(tmp,path);tmp=None
    finally:
        if tmp is not None: tmp.unlink(missing_ok=True)


def _read(path: Path) -> dict[str,Any]:
    if not path.exists(): return {}
    if path.stat().st_size>MAX_RECORD_BYTES: raise ValueError("long_running_work_session_record_too_large")
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict): raise ValueError("long_running_work_session_record_invalid")
    return value


def _record_digest(row: Mapping[str,Any]) -> str:
    return _digest({k:v for k,v in row.items() if k not in {"record_digest","operation_status"}})


def _seal(row: Mapping[str,Any]) -> dict[str,Any]:
    out=dict(row);out["record_digest"]=_record_digest(out);return out


def _bounded_codes(values: Iterable[Any], limit: int) -> list[str]:
    rows=[]
    for value in values or ():
        text=str(value or "").lower().strip()
        if not _SAFE_CODE.fullmatch(text): raise ValueError("invalid_long_running_work_code")
        if text not in rows: rows.append(text)
    return rows[-limit:]


def _bounded_summary(receipts: list[Mapping[str,Any]], completed: list[str], attempted: list[str]) -> dict[str,Any]:
    recent=receipts[-8:]
    return {
        "summary_version":"1","receipt_count_total":len(receipts),"recent_receipt_digests":[str(x.get("receipt_digest") or "") for x in recent],
        "completed_count":len(completed),"attempted_count":len(attempted),"latest_phase":str(recent[-1].get("phase") if recent else "prepared"),
        "latest_outcome":str(recent[-1].get("outcome") if recent else "skipped"),"content_free":True,
    }


def map_alpha_phase(alpha_phase: str) -> tuple[str,str]:
    phase=str(alpha_phase or "prepared")
    if phase=="prepared": return "prepared","v1265_exact_candidate_authorization"
    if phase=="repair_authorization_required": return "repair_authorization_required","v1267_exact_verification_repair_authorization"
    if phase=="operator_review_required": return "operator_review_required","operator_review_disposition"
    if phase=="review_decided": return "review_decided","v1269_fresh_preflight_and_exact_update_authorization_if_considered"
    if phase=="cancelled": return "cancelled","none"
    return "blocked","operator_reconciliation"


def validate_long_running_work_session(row: Mapping[str,Any]) -> dict[str,Any]:
    digest_ok=bool(row.get("record_digest")) and row.get("record_digest")==_record_digest(row)
    authority_ok=all(row.get(k) is v for k,v in AUTHORITY_FLAGS.items())
    receipts=list(row.get("progress_receipts") or []); summaries=list(row.get("bounded_summaries") or [])
    semantic=(
        bool(_ID.fullmatch(str(row.get("session_id") or ""))) and str(row.get("state")) in SESSION_STATES
        and str(row.get("campaign_id") or "").startswith("selfalpha_") and len(receipts)<=MAX_RECEIPTS and len(summaries)<=MAX_SUMMARIES
        and all(str(x.get("receipt_digest") or "")==_digest({k:v for k,v in x.items() if k!="receipt_digest"}) for x in receipts)
        and row.get("content_free") is True and row.get("active_source_modified") is False
    )
    ok=digest_ok and authority_ok and semantic
    return {"ok":ok,"status":"long_running_work_session_valid" if ok else "long_running_work_session_invalid","digest_valid":digest_ok,"authority_contained":authority_ok,"semantic_valid":semantic}


def prepare_long_running_work_session(campaign_id: str, *, runtime_root: str | Path | None, now: float | None=None,
                                      lease_seconds: int=DEFAULT_LEASE_SECONDS, phase_budget_seconds: int=DEFAULT_PHASE_BUDGET_SECONDS) -> dict[str,Any]:
    runtime=_runtime_root(runtime_root); alpha=load_self_development_alpha_campaign(campaign_id,runtime_root=runtime)
    if not alpha or not validate_self_development_alpha_campaign(alpha).get("ok"): raise ValueError("valid_v1270_self_development_campaign_required")
    if not (15<=int(lease_seconds)<=3600): raise ValueError("lease_seconds_out_of_bounds")
    if not (30<=int(phase_budget_seconds)<=7200): raise ValueError("phase_budget_seconds_out_of_bounds")
    session_id="longwork_"+hashlib.sha256(f"{campaign_id}:{alpha.get('source_manifest_digest')}".encode()).hexdigest()[:24]
    path=_path(session_id,runtime); phase,next_auth=map_alpha_phase(str(alpha.get("phase") or "prepared")); clock=float(time.time() if now is None else now)
    with _proposal_lock("devc_"+session_id.split("_",1)[1],runtime):
        existing=_read(path)
        if existing:
            if not validate_long_running_work_session(existing).get("ok"): raise ValueError("stored_long_running_work_session_invalid")
            return {**existing,"operation_status":"restored"}
        row=_seal({
            "ok":True,"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"status":"long_running_work_session_prepared",
            "session_id":session_id,"campaign_id":campaign_id,"campaign_record_digest":alpha.get("record_digest",""),"source_manifest_digest":alpha.get("source_manifest_digest",""),
            "state":"active","current_phase":phase,"next_required_authorization":next_auth,"created_at":clock,"updated_at":clock,
            "lease_seconds":int(lease_seconds),"phase_budget_seconds":int(phase_budget_seconds),"lease_owner":"","lease_generation":0,"heartbeat_at":0.0,"lease_expires_at":0.0,
            "completed_work_codes":[],"attempted_work_codes":[],"progress_receipts":[],"bounded_summaries":[],"action_receipts":{},
            "pause_reason":"","interruption_reason":"","cancel_reason":"","content_free":True,"summary_is_bounded":True,"progress_is_durable":True,
            "attempted_distinct_from_completed":True,"resume_never_reuses_underlying_authorization":True,"active_source_modified":False,**AUTHORITY_FLAGS,
        })
        _write(path,row);return {**row,"operation_status":"created"}


def load_long_running_work_session(session_id: str, *, runtime_root: str | Path | None) -> dict[str,Any]:
    return _read(_path(session_id,runtime_root))


def record_progress_receipt(session_id: str, *, runtime_root: str | Path | None, phase: str, work_code: str, outcome: str,
                            elapsed_seconds: float=0.0, action_key: str="", now: float | None=None, detail_codes: Iterable[Any]=()) -> dict[str,Any]:
    runtime=_runtime_root(runtime_root); clock=float(time.time() if now is None else now)
    if str(outcome) not in OUTCOMES: raise ValueError("invalid_progress_outcome")
    if not _SAFE_CODE.fullmatch(str(work_code or "")): raise ValueError("invalid_progress_work_code")
    if action_key and not _SAFE_CODE.fullmatch(str(action_key)): raise ValueError("invalid_progress_action_key")
    with _proposal_lock("devc_"+session_id.split("_",1)[1],runtime):
        row=load_long_running_work_session(session_id,runtime_root=runtime)
        if not validate_long_running_work_session(row).get("ok"): raise ValueError("valid_long_running_work_session_required")
        action_receipts=dict(row.get("action_receipts") or {})
        if action_key and action_key in action_receipts: return {**row,"operation_status":"restored","duplicate_action_suppressed":True}
        receipt={"index":int(row.get("receipt_count_total") or len(row.get("progress_receipts") or []))+1,"phase":str(phase),"work_code":str(work_code),"outcome":str(outcome),"elapsed_seconds":round(max(0.0,float(elapsed_seconds)),3),"detail_codes":_bounded_codes(detail_codes,12),"recorded_at":clock,"content_free":True}
        receipt["receipt_digest"]=_digest(receipt)
        receipts=list(row.get("progress_receipts") or [])+[receipt]; receipts=receipts[-MAX_RECEIPTS:]
        completed=_bounded_codes(row.get("completed_work_codes") or [],MAX_COMPLETED_CODES); attempted=_bounded_codes(row.get("attempted_work_codes") or [],MAX_ATTEMPTED_CODES)
        if outcome=="completed" and work_code not in completed: completed.append(work_code)
        if outcome in {"attempted","blocked"} and work_code not in attempted: attempted.append(work_code)
        if action_key: action_receipts[action_key]=receipt["receipt_digest"]
        summaries=list(row.get("bounded_summaries") or []); summaries.append(_bounded_summary(receipts,completed,attempted)); summaries=summaries[-MAX_SUMMARIES:]
        updated=dict(row);updated.update({"progress_receipts":receipts,"bounded_summaries":summaries,"completed_work_codes":completed[-MAX_COMPLETED_CODES:],"attempted_work_codes":attempted[-MAX_ATTEMPTED_CODES:],"action_receipts":action_receipts,"receipt_count_total":int(row.get("receipt_count_total") or 0)+1,"updated_at":clock,"current_phase":str(phase)})
        updated=_seal(updated);_write(_path(session_id,runtime),updated);return {**updated,"operation_status":"recorded","duplicate_action_suppressed":False}


def public_long_running_work_session(row: Mapping[str,Any]) -> dict[str,Any]:
    keys=("ok","status","session_id","campaign_id","state","current_phase","next_required_authorization","created_at","updated_at","lease_seconds","phase_budget_seconds","lease_owner","lease_generation","heartbeat_at","lease_expires_at","completed_work_codes","attempted_work_codes","receipt_count_total","bounded_summaries","pause_reason","interruption_reason","cancel_reason","content_free","summary_is_bounded","progress_is_durable","attempted_distinct_from_completed","resume_never_reuses_underlying_authorization","active_source_modified")
    return {**{k:row.get(k) for k in keys},**AUTHORITY_FLAGS}


def build_verification_harness_budget(test_ids: Iterable[str], *, phase_budget_seconds: int=DEFAULT_PHASE_BUDGET_SECONDS, estimated_seconds_per_test: float=30.0, max_chunk_tests: int=4) -> dict[str,Any]:
    tests=[]
    for test in test_ids:
        t=str(test or "").strip()
        if not t or len(t)>240: raise ValueError("invalid_test_identifier")
        tests.append(t)
    budget=int(phase_budget_seconds); estimate=max(1.0,float(estimated_seconds_per_test)); chunk=max(1,min(int(max_chunk_tests),16))
    capacity=max(1,min(chunk,int(budget//estimate) or 1)); chunks=[tests[i:i+capacity] for i in range(0,len(tests),capacity)]
    predicted=round(len(tests)*estimate,3)
    return {"ok":True,"status":"verification_harness_budget_ready","test_count":len(tests),"phase_budget_seconds":budget,"estimated_seconds_per_test":estimate,"predicted_total_seconds":predicted,"chunk_capacity":capacity,"chunk_count":len(chunks),"chunks":chunks,"monolithic_run_within_budget":predicted<=budget,"split_required":predicted>budget or len(chunks)>1,"global_timeout_increased":False,"budget_exhaustion_requires_checkpoint":True,"content_free":True,**AUTHORITY_FLAGS}


__all__=["CONTRACT_VERSION","AUTHORITY_FLAGS","MAX_RECEIPTS","MAX_SUMMARIES","prepare_long_running_work_session","load_long_running_work_session","record_progress_receipt","public_long_running_work_session","validate_long_running_work_session","build_verification_harness_budget","map_alpha_phase"]
