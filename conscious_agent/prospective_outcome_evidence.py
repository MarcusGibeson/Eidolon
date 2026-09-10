from __future__ import annotations
"""Content-free prospective outcome evidence for v1117.6."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from prospective_obligation_records import ProspectiveObligationStore
CONTRACT_VERSION="v1117.6"
OUTCOMES={"fulfilled","partially_fulfilled","not_fulfilled","indeterminate","cancelled","superseded","expired_without_evidence"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*parts): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in parts).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":"1","contract_version":CONTRACT_VERSION,"records":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{"can_change_obligation":False,"can_reschedule":False,"can_notify":False,"can_send_message":False,"can_select_attention":False,"can_form_intention":False,"can_propose":False,"can_approve":False,"can_authorize":False,"can_execute":False}}
class ProspectiveOutcomeEvidenceStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/"prospective_outcome_evidence.json"; self.clock=clock or _now; self.obligations=ProspectiveObligationStore(self.runtime_root,clock=self.clock)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1": s=_default()
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def record(self,event_id:str,*,obligation_id:str,outcome:str,evidence_kind:str="structural_receipt",confidence:float=0.5,uncertainty:float=0.5,source_receipt_ids:list[str]|None=None):
  if outcome not in OUTCOMES: raise ValueError("unsupported outcome")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior: return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   obligation=next((x for x in self.obligations.snapshot()["obligations"] if x.get("obligation_id")==obligation_id),None)
   if not obligation: raise ValueError("unknown obligation")
   receipts=sorted(set(_clean(x,220) for x in (source_receipt_ids or []) if _clean(x,220)))
   eid=f"prospective-outcome-{_digest(event_id,obligation_id,outcome,receipts)[:24]}"
   result={"status":"outcome_evidence_recorded","evidence_id":eid,"obligation_id":obligation_id,"origin_digest":obligation.get("structural_digest",""),"outcome":outcome,"evidence_kind":_clean(evidence_kind,80),"confidence":max(0.0,min(1.0,float(confidence))),"uncertainty":max(0.0,min(1.0,float(uncertainty))),"source_receipt_ids":receipts,"success_inferred":False,"failure_inferred":False,"obligation_changed":False,"schedule_changed":False,"notification_id":"","proposal_id":"","approval_id":"","authorization_id":"","action_id":""}
   now=self.clock(); rec={**result,"occurred_at":now,"content_free":True,"structural_digest":_digest(eid,obligation_id,outcome,receipts,result["confidence"],result["uncertainty"])}
   s["records"]=(s["records"]+[rec])[-2048:]; s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-4096:]; s["revision"]+=1; s["updated_at"]=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True)
   return {"ok":True,"status":"outcome_evidence_recorded","result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s["records"]: counts[x.get("outcome")]=counts.get(x.get("outcome"),0)+1
  keys=("evidence_id","obligation_id","origin_digest","outcome","evidence_kind","confidence","uncertainty","source_receipt_ids","success_inferred","failure_inferred","obligation_changed","schedule_changed","notification_id","proposal_id","approval_id","authorization_id","action_id")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"evidence_count":len(s["records"]),"outcome_counts":counts,"recent_evidence":[{k:x.get(k) for k in keys} for x in s["records"][-24:]],"authority_boundary":deepcopy(s["authority_boundary"]),"private_content_exposed":False,"hidden_reasoning_exposed":False,"runtime_mutated":False}
def build_prospective_outcome_evidence_inspection(runtime_root=None): return ProspectiveOutcomeEvidenceStore(runtime_root).inspection_summary()
