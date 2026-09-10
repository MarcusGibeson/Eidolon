from __future__ import annotations
"""v1143.7 restrained operator-visible workload coordination evidence."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from workload_coordination_reliability_review import WorkloadCoordinationReliabilityReviewStore
CONTRACT_VERSION="v1143.7"; SCHEMA_VERSION="1"
AUTHORITY_KEYS=("can_execute_underlying_work","can_change_scheduler","can_contact_provider","can_send_message","can_modify_source","can_approve","can_authorize","can_install","can_promote","can_certify")
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*p:Any): return hashlib.sha256("\x1f".join(_clean(x,4000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"evidence":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{k:False for k in AUTHORITY_KEYS}}
class WorkloadCoordinationVisibleEvidenceStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/"workload_coordination_visible_evidence.json"; self.clock=clock or _now; self.reviews=WorkloadCoordinationReliabilityReviewStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id:str,*,review_id:str,visibility_class:str="operator_summary"):
  event_id=_clean(event_id,180);visibility_class=_clean(visibility_class,80)
  r=next((x for x in self.reviews.snapshot().get("reviews",[]) if x.get("review_id")==review_id),None)
  if not event_id or not r: raise ValueError("event and exact v1143.6 review required")
  structural=_digest(review_id,visibility_class,r.get("outcome"),r.get("workload_kind"),r.get("fairness_class_id"))
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,**deepcopy(prior["result"]),"idempotent":True}
   now=self.clock();eid=f"workload-visible-evidence-{structural[:24]}";row={"evidence_id":eid,"review_id":review_id,"workload_id":r.get("workload_id"),"workload_kind":r.get("workload_kind"),"fairness_class_id":r.get("fairness_class_id"),"outcome":r.get("outcome"),"visibility_class":visibility_class,"operator_review_required":r.get("operator_review_required"),"advisory_only":True,"scheduler_authority_granted":False,"underlying_work_authority_granted":False,"structural_digest":structural,"created_at":now};s["evidence"].append(row);result={"status":"evidence_recorded","evidence_id":eid};s["processed_events"].append({"event_id":event_id,"occurred_at":now,"result":deepcopy(result),"content_free":True});s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,**result,"idempotent":False}
 def inspection_summary(self):
  s=self._load();keys=("evidence_id","review_id","workload_id","workload_kind","fairness_class_id","outcome","visibility_class","operator_review_required","advisory_only","scheduler_authority_granted","underlying_work_authority_granted","structural_digest")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"evidence_count":len(s["evidence"]),"recent_evidence":[{k:r.get(k) for k in keys} for r in s["evidence"][-32:]],"authority_boundary":deepcopy(s["authority_boundary"]),"raw_content_exposed":False,"workload_payload_exposed":False,"scheduler_mutated":False,"underlying_work_executed":False}
def build_workload_coordination_visible_evidence_inspection(runtime_root=None): return WorkloadCoordinationVisibleEvidenceStore(runtime_root).inspection_summary()
