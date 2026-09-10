from __future__ import annotations
"""Provider-neutral contradiction and durable identity-change detection."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable, Iterable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from persistent_identity_model import PersistentIdentityModelStore
CONTRACT_VERSION="v1110.3"
OUTCOMES={"no_material_change","transient_variation","contradiction_detected","durable_change_candidate","correction_detected","unresolved"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=500): return " ".join(str(v or "").split())[:n]
def _digest(*p): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":"1","contract_version":CONTRACT_VERSION,"detections":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"durable_recurrence_threshold":3,"durable_days_threshold":14,"max_detections":512,"max_refs":32},"state_separation":{"observation_is_identity":False,"contradiction_is_revision":False,"change_candidate_is_intention":False,"revision_is_proposal":False,"proposal_is_authorization":False,"authorization_is_execution":False},"authority_boundary":{"can_browse":False,"can_send":False,"can_execute":False,"can_modify_files":False,"can_manage_models":False,"can_authorize":False,"can_approve":False,"can_promote":False,"can_certify":False}}
class IdentityChangeDetector:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/"identity_change_detection.json";self.clock=clock or _now;self.claims=PersistentIdentityModelStore(self.runtime_root,clock=self.clock)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1":s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self):return deepcopy(self._load())
 def detect(self,event_id,*,claim_id,observation_refs:Iterable[str]=(),contradicting_refs:Iterable[str]=(),recurrence_count=1,observed_days=0,explicit_correction=False,material_change=False):
  event_id=_clean(event_id,180);claim_id=_clean(claim_id,180);obs=tuple(_clean(x,220) for x in observation_refs if _clean(x,220));contra=tuple(_clean(x,220) for x in contradicting_refs if _clean(x,220))
  if not event_id or not claim_id:raise ValueError("event_id and claim_id required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_detection_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   claim=next((x for x in self.claims.snapshot().get("claims",[]) if x.get("claim_id")==claim_id),None);now=self.clock()
   if not claim:result={"status":"change_not_detected","reason":"claim_missing","detection_id":""}
   else:
    recurrence=max(0,int(recurrence_count));days=max(0,int(observed_days));durable=recurrence>=int(s["controls"]["durable_recurrence_threshold"]) and days>=int(s["controls"]["durable_days_threshold"])
    if explicit_correction:outcome="correction_detected"
    elif contra and durable and material_change:outcome="durable_change_candidate"
    elif contra:outcome="contradiction_detected"
    elif material_change and not durable:outcome="transient_variation"
    elif not obs:outcome="unresolved"
    else:outcome="no_material_change"
    key=_digest(claim_id,outcome,recurrence,days,*obs,*contra);existing=next((x for x in s["detections"] if x.get("detection_key")==key),None)
    if existing:result={"status":"duplicate_detection_ignored","detection_id":existing["detection_id"],"outcome":existing["outcome"]}
    else:
     did=f"identity-change-{key[:24]}";row={"detection_id":did,"detection_key":key,"claim_id":claim_id,"claim_revision":int(claim.get("revision") or 0),"outcome":outcome,"eligible_for_revision":outcome in {"durable_change_candidate","correction_detected","contradiction_detected"},"durable_threshold_met":durable,"recurrence_count":recurrence,"observed_days":days,"observation_ref_digests":[_digest(x) for x in obs[:s["controls"]["max_refs"]]],"contradiction_ref_digests":[_digest(x) for x in contra[:s["controls"]["max_refs"]]],"created_at":now,"content_free":True,"provider_bound":False,"proposal_id":"","authorization_id":"","action_id":"","authority_granted":False};s["detections"].append(row);result={"status":"identity_change_detected","detection_id":did,"outcome":outcome,"eligible_for_revision":row["eligible_for_revision"]}
   s["detections"]=s["detections"][-int(s["controls"]["max_detections"]):];s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result)}])[-1024:];s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load();counts={}
  for x in s["detections"]:counts[x.get("outcome","unresolved")]=counts.get(x.get("outcome","unresolved"),0)+1
  return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"detection_count":len(s["detections"]),"eligible_revision_count":sum(bool(x.get("eligible_for_revision")) for x in s["detections"]),"outcome_counts":counts,"recent_detections":deepcopy(s["detections"][-24:]),"controls":deepcopy(s["controls"]),"state_separation":deepcopy(s["state_separation"]),"authority_boundary":deepcopy(s["authority_boundary"]),"runtime_mutated":False,"provider_contacted":False,"external_action_executed":False,"hidden_reasoning_exposed":False,"private_content_exposed":False}
def build_identity_change_detection_inspection(runtime_root=None):return IdentityChangeDetector(runtime_root).inspection_summary()
