from __future__ import annotations

"""v1146.4 deterministic control enforcement and structural decision receipts."""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib, json
from pathlib import Path
import re
from typing import Any

from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from understandable_cognitive_control_activation import build_cognitive_control_activation_inspection
from understandable_cognitive_control_definitions import AUTHORITY_BOUNDARY, CONTROL_DOMAINS, SAFE_DEFAULTS

CONTRACT_VERSION = "v1146.4"
SCHEMA_VERSION = "1"
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,239}$")


def _now() -> str: return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
def _digest(v: Any) -> str: return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
def _identifier(v: Any) -> str:
    token=" ".join(str(v or "").split())[:240]
    return token if _IDENTIFIER.fullmatch(token) else ""
def _path(root: Path) -> Path: return root / "understandable_cognitive_control_enforcement.json"
def _default() -> dict[str, Any]: return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"revision":0,"receipts":[],"processed_event_ids":{},"updated_at":"","authority_boundary":deepcopy(AUTHORITY_BOUNDARY)}


def evaluate_cognitive_control(
    *, runtime_root: Path | str, domain: str, event_id: str, consumer_id: str,
    requested_intensity: float = 0.0, resource_cost: float = 0.0,
) -> dict[str, Any]:
    root=Path(runtime_root).resolve(); root.mkdir(parents=True,exist_ok=True); path=_path(root)
    domain_id,event,consumer=_identifier(domain),_identifier(event_id),_identifier(consumer_id)
    if domain_id not in CONTROL_DOMAINS or not event or not consumer: raise ValueError("valid domain, event, and consumer identifiers are required")
    requested=round(max(0.0,min(float(requested_intensity),1.0)),4); cost=round(max(0.0,min(float(resource_cost),1.0)),4)
    with metadata_mutation_lock(path):
        state=load_json_file(path,default=_default()) or _default()
        prior=(state.get("processed_event_ids") or {}).get(event)
        if prior: return {"ok":True,"idempotent":True,"receipt":deepcopy(prior)}
        activation=build_cognitive_control_activation_inspection(root)
        active=(activation.get("active_controls") or {}).get(domain_id)
        effective=deepcopy(active) if active else {"mode":SAFE_DEFAULTS[domain_id]["mode"],"intensity":SAFE_DEFAULTS[domain_id]["intensity"],"activation_id":"","structural_digest":"","state":"safe_default"}
        mode=str(effective.get("mode") or SAFE_DEFAULTS[domain_id]["mode"]); limit=float(effective.get("intensity",SAFE_DEFAULTS[domain_id]["intensity"]))
        decision="allow"
        reason="within_active_control"
        effective_intensity=min(requested,limit)
        if mode in {"paused","disabled"}: decision,reason,effective_intensity="deny","control_paused_or_disabled",0.0
        elif requested>limit: decision,reason="constrain","requested_intensity_exceeds_limit"
        if domain_id=="privacy" and mode=="strict" and requested>0: decision,reason,effective_intensity="constrain","strict_privacy_boundary",min(requested,limit)
        if domain_id=="resource_use" and cost>limit: decision,reason,effective_intensity="deny","resource_cost_exceeds_limit",0.0
        if domain_id=="development_proposals" and mode!="suggest_only": decision,reason,effective_intensity="deny","development_proposals_not_enabled",0.0
        revision=int(state.get("revision") or 0)+1
        receipt={
            "receipt_id":f"control-enforcement:{event}:{revision}","revision":revision,"event_id":event,"consumer_id":consumer,"domain":domain_id,
            "activation_id":effective.get("activation_id", ""),"activation_digest":effective.get("structural_digest", ""),"control_source":"active" if active else "safe_default",
            "mode":mode,"control_intensity":round(limit,4),"requested_intensity":requested,"effective_intensity":round(effective_intensity,4),"resource_cost":cost,
            "decision":decision,"reason_code":reason,"consumer_may_continue":decision in {"allow","constrain"},
            "execution_performed":False,"cognition_mutated":False,"provider_contacted":False,"message_sent":False,"proposal_created":False,
            "occurred_at":_now(),"authority_boundary":deepcopy(AUTHORITY_BOUNDARY),
        }
        receipt["structural_digest"]=_digest(receipt)
        state.setdefault("receipts",[]).append(receipt);state["receipts"]=state["receipts"][-500:]
        state.setdefault("processed_event_ids",{})[event]=receipt;state["processed_event_ids"]=dict(list(state["processed_event_ids"].items())[-1000:])
        state["revision"]=revision;state["updated_at"]=receipt["occurred_at"];write_json_atomic(path,state)
    return {"ok":True,"idempotent":False,"receipt":deepcopy(receipt)}


def build_cognitive_control_enforcement_inspection(runtime_root: Path | str) -> dict[str, Any]:
    root=Path(runtime_root).resolve();state=load_json_file(_path(root),default=_default()) or _default();receipts=deepcopy(state.get("receipts") or [])[-50:]
    counts={key:sum(1 for r in receipts if r.get("decision")==key) for key in ("allow","constrain","deny")}
    return {"contract_version":CONTRACT_VERSION,"schema_version":SCHEMA_VERSION,"revision":int(state.get("revision") or 0),"receipt_count":len(state.get("receipts") or []),"recent_receipts":receipts,"decision_counts":counts,"execution_performed":False,"content_free":True,"authority_boundary":deepcopy(AUTHORITY_BOUNDARY),"structural_digest":_digest({"revision":state.get("revision",0),"receipts":receipts})}
