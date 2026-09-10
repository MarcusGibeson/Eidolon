from __future__ import annotations

"""v1268.3-v1268.5 exact operator review disposition and v1269 handoff."""
from pathlib import Path
from typing import Any, Mapping
from ordinary_chat_development_campaign import _proposal_lock
from operator_review_handoff_foundations import REVIEW_DECISIONS,REVIEW_DENIED_AUTHORITY,_decision_path,_digest,_read_json,_record_digest,_runtime_root,_write_json,load_operator_review_packet,validate_operator_review_packet

CONTRACT_VERSION="v1268.5"


def record_operator_review_decision(review_id: str, *, packet_digest: str, decision: str, runtime_root: str | Path | None) -> dict[str,Any]:
    if decision not in REVIEW_DECISIONS: raise ValueError("operator_review_decision_invalid")
    runtime=_runtime_root(runtime_root)
    with _proposal_lock("devc_"+review_id.split("_",1)[1],runtime):
        packet=load_operator_review_packet(review_id,runtime_root=runtime)
        if not packet or not validate_operator_review_packet(packet).get("ok"): raise ValueError("valid_operator_review_packet_required")
        if packet_digest!=packet.get("record_digest"): return {"ok":False,"status":"operator_review_packet_digest_mismatch","review_id":review_id,**REVIEW_DENIED_AUTHORITY}
        path=_decision_path(review_id,runtime); existing=_read_json(path)
        if existing:
            if existing.get("packet_digest")==packet_digest and existing.get("decision")==decision: return {**existing,"operation_status":"restored"}
            return {"ok":False,"status":"conflicting_operator_review_decision_rejected","review_id":review_id,**REVIEW_DENIED_AUTHORITY}
        row={"ok":True,"contract_version":CONTRACT_VERSION,"status":"operator_review_decision_recorded","review_id":review_id,"packet_digest":packet_digest,"decision":decision,"eligible_for_v1269_consideration":decision=="approve_for_v1269_consideration","decision_is_authority":False,"active_source_modified":False,"content_minimized":True,**REVIEW_DENIED_AUTHORITY}
        row["record_digest"]=_record_digest(row);_write_json(path,row);return {**row,"operation_status":"created"}


def build_v1269_review_handoff(review_id: str, *, runtime_root: str | Path | None) -> dict[str,Any]:
    packet=load_operator_review_packet(review_id,runtime_root=runtime_root); decision=_read_json(_decision_path(review_id,runtime_root))
    if not packet or not validate_operator_review_packet(packet).get("ok"): return {"ok":False,"status":"operator_review_packet_invalid_or_missing",**REVIEW_DENIED_AUTHORITY}
    if not decision or decision.get("decision")!="approve_for_v1269_consideration": return {"ok":False,"status":"operator_review_not_approved_for_v1269_consideration","review_id":review_id,**REVIEW_DENIED_AUTHORITY}
    return {"ok":True,"contract_version":CONTRACT_VERSION,"status":"v1269_review_handoff_ready","review_id":review_id,"review_packet_digest":packet.get("record_digest"),"decision_digest":decision.get("record_digest"),"source_manifest_digest":packet.get("source_manifest_digest"),"candidate_manifest_digest":packet.get("candidate_manifest_digest"),"changed_files_digest":packet.get("changed_files_digest"),"verification_digest":_digest(packet.get("verification") or {}),"risk_digest":_digest(packet.get("risks") or []),"uncertainty_digest":_digest(packet.get("unresolved_uncertainty") or []),"fresh_v1269_preflight_required":True,"fresh_v1269_authorization_required":True,"decision_is_authority":False,"active_source_modified":False,"content_minimized":True,**REVIEW_DENIED_AUTHORITY}

__all__=["CONTRACT_VERSION","record_operator_review_decision","build_v1269_review_handoff"]
