from __future__ import annotations
"""v1146.6 cross-cycle cognitive-control continuity, drift, and recovery records."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, json, re
from pathlib import Path
from typing import Any
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from understandable_cognitive_control_activation import build_cognitive_control_activation_inspection
from understandable_cognitive_control_definitions import AUTHORITY_BOUNDARY, CONTROL_DOMAINS, SAFE_DEFAULTS
CONTRACT_VERSION="v1146.6"; SCHEMA_VERSION="1"; _ID=re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,239}$")
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _digest(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":" )).encode()).hexdigest()
def _identifier(v):
 t=" ".join(str(v or "").split())[:240]; return t if _ID.fullmatch(t) else ""
def _path(root): return root/"understandable_cognitive_control_continuity.json"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"revision":0,"records":[],"processed_cycle_ids":{},"updated_at":"","authority_boundary":deepcopy(AUTHORITY_BOUNDARY)}
def record_cognitive_control_continuity(*,runtime_root:Path|str,cycle_id:str,prior_cycle_id:str="",operator_correction_id:str="") -> dict[str,Any]:
 root=Path(runtime_root).resolve(); cycle=_identifier(cycle_id); prior=_identifier(prior_cycle_id); correction=_identifier(operator_correction_id)
 if not cycle: raise ValueError("valid cycle identifier required")
 root.mkdir(parents=True,exist_ok=True); path=_path(root)
 with metadata_mutation_lock(path):
  state=load_json_file(path,default=_default()) or _default()
  old=(state.get("processed_cycle_ids") or {}).get(cycle)
  if old: return {"ok":True,"idempotent":True,"record":deepcopy(old)}
  inspection=build_cognitive_control_activation_inspection(root); active=inspection.get("active_controls") or {}
  previous=next((r for r in reversed(state.get("records") or []) if r.get("cycle_id")==prior),None) if prior else None
  previous_domains=(previous or {}).get("domain_digests") or {}
  domain_digests={d:(active.get(d) or {}).get("structural_digest","") for d in CONTROL_DOMAINS}
  stale=[d for d,v in active.items() if v.get("state")!="active" or not v.get("activation_id") or not v.get("structural_digest")]
  conflicts=[d for d,v in active.items() if d not in CONTROL_DOMAINS or v.get("domain")!=d]
  drift=[d for d in CONTROL_DOMAINS if previous_domains and previous_domains.get(d,"")!=domain_digests.get(d,"")]
  recovered=[d for d in CONTROL_DOMAINS if d not in active]
  revision=int(state.get("revision") or 0)+1
  record={"continuity_id":f"control-continuity:{cycle}:{revision}","revision":revision,"cycle_id":cycle,"prior_cycle_id":prior,"operator_correction_id":correction,"activation_revision":inspection.get("revision",0),"active_domains":sorted(active),"domain_digests":domain_digests,"stale_domains":sorted(stale),"conflicting_domains":sorted(conflicts),"drifted_domains":sorted(drift),"safe_default_domains":sorted(recovered),"correction_present":bool(correction),"safe_default_recovery_available":True,"continuity_state":"review" if stale or conflicts else "stable","visible_state":"attention" if stale or conflicts else ("changed" if drift else "steady"),"content_free":True,"execution_performed":False,"cognition_mutated":False,"provider_contacted":False,"message_sent":False,"proposal_created":False,"occurred_at":_now(),"authority_boundary":deepcopy(AUTHORITY_BOUNDARY)}
  record["structural_digest"]=_digest(record); state.setdefault("records",[]).append(record); state["records"]=state["records"][-400:]; state.setdefault("processed_cycle_ids",{})[cycle]=record; state["processed_cycle_ids"]=dict(list(state["processed_cycle_ids"].items())[-800:]); state["revision"]=revision;state["updated_at"]=record["occurred_at"];write_json_atomic(path,state)
 return {"ok":True,"idempotent":False,"record":deepcopy(record)}
def build_cognitive_control_continuity_inspection(runtime_root:Path|str)->dict[str,Any]:
 root=Path(runtime_root).resolve();state=load_json_file(_path(root),default=_default()) or _default();records=deepcopy(state.get("records") or [])[-50:]
 return {"contract_version":CONTRACT_VERSION,"schema_version":SCHEMA_VERSION,"revision":int(state.get("revision") or 0),"record_count":len(state.get("records") or []),"recent_records":records,"stale_count":sum(len(r.get("stale_domains") or []) for r in records),"conflict_count":sum(len(r.get("conflicting_domains") or []) for r in records),"drift_count":sum(len(r.get("drifted_domains") or []) for r in records),"safe_default_recovery_count":sum(len(r.get("safe_default_domains") or []) for r in records),"content_free":True,"authority_boundary":deepcopy(AUTHORITY_BOUNDARY),"structural_digest":_digest({"revision":state.get("revision",0),"records":records})}
