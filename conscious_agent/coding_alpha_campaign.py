from __future__ import annotations

"""v1260.3-v1260.5 evidence projection for the real supervised coding chain."""

import hashlib, json
from typing import Any

from coding_alpha_checkpoint_foundations import DENIED_AUTHORITY, build_coding_alpha_contract
from isolated_coding_execution_foundations import load_coding_work_request, load_coding_project_inspection, load_coding_work_plan
from isolated_coding_execution import load_isolated_coding_execution, load_isolated_coding_review
from complete_application_construction_foundations import load_complete_application_construction
from complete_application_construction import load_complete_application_quality
from persistent_development_sessions_foundations import create_or_restore_persistent_development_session
from persistent_development_sessions import resume_persistent_development_session
from controlled_application_rollback_foundations import load_controlled_application
from controlled_application_rollback import load_controlled_application_execution, load_controlled_rollback, load_controlled_rollback_result

SCHEMA_VERSION="1"
CONTRACT_VERSION="v1260.5"


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()


def build_coding_alpha_lineage(request_id: str, *, runtime_root=None) -> dict[str, Any]:
    request=load_coding_work_request(request_id,runtime_root=runtime_root)
    if not request:
        return {"ok":False,"status":"coding_alpha_request_missing_or_tampered","request_id":request_id,**DENIED_AUTHORITY}
    inspection=load_coding_project_inspection(request_id,runtime_root=runtime_root)
    plan=load_coding_work_plan(request_id,runtime_root=runtime_root)
    execution=load_isolated_coding_execution(request_id,runtime_root=runtime_root)
    review=load_isolated_coding_review(request_id,runtime_root=runtime_root)
    construction=load_complete_application_construction(request_id,runtime_root=runtime_root)
    app=load_controlled_application(request_id,runtime_root=runtime_root)
    app_result=load_controlled_application_execution(request_id,runtime_root=runtime_root)
    rollback=load_controlled_rollback(request_id,runtime_root=runtime_root)
    rollback_result=load_controlled_rollback_result(request_id,runtime_root=runtime_root)
    attempts=[]
    result=execution.get("result") if isinstance(execution.get("result"),dict) else {}
    for n in range(1,int(result.get("attempt_count") or 0)+1):
        q=load_complete_application_quality(request_id,n,runtime_root=runtime_root)
        attempts.append({"attempt":n,"quality_digest":q.get("quality_record_digest", ""),"quality_passed":q.get("passed") if isinstance(q.get("passed"),bool) else None})
    session=create_or_restore_persistent_development_session(request_id,runtime_root=runtime_root)
    session_public={}
    if session.get("ok"):
        resumed=resume_persistent_development_session(str(session.get("session_id") or ""),runtime_root=runtime_root)
        session_public=dict(resumed.get("persistent_session") or resumed.get("session") or {})
    stage={
        "request":bool(request),"inspection":bool(inspection),"plan":bool(plan),"isolated_execution":bool(execution),
        "review":bool(review),"complete_application_contract":bool(construction),"controlled_application_packet":bool(app),
        "application_result":bool(app_result),"rollback_packet":bool(rollback),"rollback_result":bool(rollback_result),
    }
    lineage={
        "ok":True,"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"status":"coding_alpha_lineage_ready",
        "request_id":request_id,"request_digest":request.get("request_digest", ""),"stage_presence":stage,"attempts":attempts,
        "attempt_count":int(result.get("attempt_count") or 0),"repair_attempt_count":int(result.get("repair_attempt_count") or 0),
        "diagnostic_cycle_count":int(result.get("diagnostic_cycle_count") or 0),"reviewable_diff_available":bool(review.get("reviewable_diff_available")),
        "application_completed":bool((app_result.get("result") or app_result).get("ok")),
        "rollback_completed":bool(rollback_result.get("ok")),"persistent_session":session_public,
        "scenario_contract_digest":build_coding_alpha_contract()["contract_digest"],"content_minimized":True,
        **DENIED_AUTHORITY,
    }
    lineage["lineage_digest"]=_digest(lineage)
    return lineage

__all__=["CONTRACT_VERSION","build_coding_alpha_lineage"]
