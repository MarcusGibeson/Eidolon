from __future__ import annotations
"""v1146.7 content-free cognitive-control reliability review."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib,json,re
from pathlib import Path
from typing import Any
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from understandable_cognitive_control_continuity import build_cognitive_control_continuity_inspection
from understandable_cognitive_control_enforcement import build_cognitive_control_enforcement_inspection
from understandable_cognitive_control_definitions import AUTHORITY_BOUNDARY
CONTRACT_VERSION="v1146.7";SCHEMA_VERSION="1";_ID=re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,239}$")
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _digest(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":" )).encode()).hexdigest()
def _id(v):
 t=" ".join(str(v or "").split())[:240];return t if _ID.fullmatch(t) else ""
def _path(r):return r/"understandable_cognitive_control_reliability.json"
def _default():return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"revision":0,"reviews":[],"processed_review_ids":{},"updated_at":"","authority_boundary":deepcopy(AUTHORITY_BOUNDARY)}
def review_cognitive_control_reliability(*,runtime_root:Path|str,review_id:str)->dict[str,Any]:
 root=Path(runtime_root).resolve();rid=_id(review_id)
 if not rid:raise ValueError("valid review identifier required")
 root.mkdir(parents=True,exist_ok=True);path=_path(root)
 with metadata_mutation_lock(path):
  state=load_json_file(path,default=_default()) or _default();old=(state.get("processed_review_ids") or {}).get(rid)
  if old:return {"ok":True,"idempotent":True,"review":deepcopy(old)}
  continuity=build_cognitive_control_continuity_inspection(root);enforcement=build_cognitive_control_enforcement_inspection(root)
  recent=continuity.get("recent_records") or []; corrected=sum(1 for r in recent if r.get("correction_present")); unresolved=sum(1 for r in recent if r.get("continuity_state")=="review")
  score=max(0.0,1.0-min(1.0,(continuity.get("stale_count",0)+continuity.get("conflict_count",0)+unresolved)/10.0));revision=int(state.get("revision") or 0)+1
  review={"reliability_id":f"control-reliability:{rid}:{revision}","revision":revision,"review_id":rid,"continuity_revision":continuity.get("revision",0),"enforcement_revision":enforcement.get("revision",0),"continuity_record_count":continuity.get("record_count",0),"enforcement_receipt_count":enforcement.get("receipt_count",0),"stale_count":continuity.get("stale_count",0),"conflict_count":continuity.get("conflict_count",0),"drift_count":continuity.get("drift_count",0),"safe_default_recovery_count":continuity.get("safe_default_recovery_count",0),"correction_effective_count":corrected,"unresolved_review_count":unresolved,"reliability_score":round(score,4),"uncertainty":round(1-score,4),"state":"review_required" if unresolved else "reliable","visible_behavior":"attention" if unresolved else "stable","content_free":True,"execution_performed":False,"cognition_mutated":False,"provider_contacted":False,"message_sent":False,"proposal_created":False,"occurred_at":_now(),"authority_boundary":deepcopy(AUTHORITY_BOUNDARY)}
  review["structural_digest"]=_digest(review);state.setdefault("reviews",[]).append(review);state["reviews"]=state["reviews"][-300:];state.setdefault("processed_review_ids",{})[rid]=review;state["revision"]=revision;state["updated_at"]=review["occurred_at"];write_json_atomic(path,state)
 return {"ok":True,"idempotent":False,"review":deepcopy(review)}
def build_cognitive_control_reliability_inspection(runtime_root:Path|str)->dict[str,Any]:
 root=Path(runtime_root).resolve();state=load_json_file(_path(root),default=_default()) or _default();reviews=deepcopy(state.get("reviews") or [])[-40:]
 return {"contract_version":CONTRACT_VERSION,"schema_version":SCHEMA_VERSION,"revision":int(state.get("revision") or 0),"review_count":len(state.get("reviews") or []),"recent_reviews":reviews,"review_required_count":sum(1 for r in reviews if r.get("state")=="review_required"),"content_free":True,"authority_boundary":deepcopy(AUTHORITY_BOUNDARY),"structural_digest":_digest({"revision":state.get("revision",0),"reviews":reviews})}
