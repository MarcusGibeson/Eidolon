from __future__ import annotations
"""Deterministic evidence arbitration for revisable identity claims."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable, Iterable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from persistent_identity_model import PersistentIdentityModelStore
CONTRACT_VERSION="v1110.1"
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=500): return " ".join(str(v or "").split())[:n]
def _digest(*p): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":"1","contract_version":CONTRACT_VERSION,"receipts":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"minimum_support_to_retain":1,"contradiction_suspend_threshold":2,"max_receipts":512},"authority_boundary":{"can_browse":False,"can_send":False,"can_execute":False,"can_modify_files":False,"can_manage_models":False,"can_authorize":False,"can_approve":False,"can_promote":False,"can_certify":False}}
class IdentityEvidenceArbitrator:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/"identity_evidence_arbitration.json";self.clock=clock or _now;self.claims=PersistentIdentityModelStore(self.runtime_root,clock=self.clock)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1":s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self):return deepcopy(self._load())
 def arbitrate(self,event_id,*,claim_id,supporting_refs:Iterable[str]=(),contradicting_refs:Iterable[str]=(),correction=False,retraction=False):
  event_id=_clean(event_id,180);claim_id=_clean(claim_id,180);support=tuple(_clean(x,220) for x in supporting_refs if _clean(x,220));contra=tuple(_clean(x,220) for x in contradicting_refs if _clean(x,220))
  if not event_id or not claim_id:raise ValueError("event_id and claim_id required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   with metadata_mutation_lock(self.claims.path,timeout_seconds=5):
    cs=self.claims._load();row=next((x for x in cs["claims"] if x.get("claim_id")==claim_id),None)
    if not row:result={"status":"claim_missing","claim_id":claim_id,"outcome":"unresolved"}
    else:
     now=self.clock();row["support_count"]=int(row.get("support_count") or 0)+len(support);row["contradiction_count"]=int(row.get("contradiction_count") or 0)+len(contra)
     if retraction: outcome="retract";row["state"]="retracted";row["active_influence"]=False;row["eligible"]=False;row["confidence"]=0.0;row["uncertainty"]=1.0
     elif correction: outcome="revise";row["state"]="uncertain";row["active_influence"]=True;row["confidence"]=round(max(0.1,float(row.get("confidence") or .5)-.2),4);row["uncertainty"]=round(min(1,float(row.get("uncertainty") or .5)+.2),4)
     elif row["contradiction_count"]>=s["controls"]["contradiction_suspend_threshold"] and row["contradiction_count"]>row["support_count"]: outcome="suspend";row["state"]="suspended";row["active_influence"]=False;row["eligible"]=False
     elif row["support_count"]>=s["controls"]["minimum_support_to_retain"] and row["support_count"]>=row["contradiction_count"]: outcome="retain";row["state"]="active";row["active_influence"]=True;row["eligible"]=True;row["confidence"]=round(min(1,float(row.get("confidence") or .5)+.05*len(support)),4);row["uncertainty"]=round(max(0,float(row.get("uncertainty") or .5)-.05*len(support)),4)
     else: outcome="unresolved";row["state"]="uncertain";row["active_influence"]=True
     row["revision"]=int(row.get("revision") or 0)+1;row["updated_at"]=now;row["evidence_ref_digests"]=(list(row.get("evidence_ref_digests") or [])+[_digest(x) for x in support+contra])[-32:];row["evidence_count"]=len(row["evidence_ref_digests"]);row["update_history"]=(list(row.get("update_history") or [])+[{"event_digest":_digest(event_id),"occurred_at":now,"change":outcome,"content_free":True}])[-64:];cs["revision"]+=1;cs["updated_at"]=now;write_json_atomic(self.claims.path,cs,expected_type=dict,sort_keys=True);result={"status":"identity_evidence_arbitrated","claim_id":claim_id,"outcome":outcome,"active_influence":row["active_influence"]}
   now=self.clock();receipt={"receipt_id":f"identity-arbitration-{_digest(event_id)[:24]}","event_digest":_digest(event_id),"claim_id":claim_id,"outcome":result.get("outcome","unresolved"),"support_count":len(support),"contradiction_count":len(contra),"occurred_at":now,"content_free":True,"proposal_id":"","authorization_id":"","action_id":""};s["receipts"]=(s["receipts"]+[receipt])[-s["controls"]["max_receipts"]:];s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"result":deepcopy(result)}])[-1024:];s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load();counts={};
  for x in s["receipts"]:counts[x.get("outcome","unresolved")]=counts.get(x.get("outcome","unresolved"),0)+1
  return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"arbitration_count":len(s["receipts"]),"outcome_counts":counts,"recent_receipts":deepcopy(s["receipts"][-24:]),"authority_boundary":deepcopy(s["authority_boundary"]),"provider_contacted":False,"external_action_executed":False,"hidden_reasoning_exposed":False,"private_content_exposed":False,"runtime_mutated":False}
def build_identity_evidence_arbitration_inspection(runtime_root=None):return IdentityEvidenceArbitrator(runtime_root).inspection_summary()
