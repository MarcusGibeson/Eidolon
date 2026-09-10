from __future__ import annotations
"""v1126.6 durable reflection-quality outcome lineage without revision authority."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from reflection_quality_arbitration import ReflectionQualityArbitrationStore
CONTRACT_VERSION="v1126.6"; SCHEMA_VERSION="1"
RECOGNIZED={"retain_supported_conclusion","mark_unsupported","reconcile_contradiction","recalibrate_confidence","defer_for_provider_recovery","defer_for_operator_review","unresolved"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=220): return " ".join(str(v or "").split())[:n]
def _digest(*v:Any): return hashlib.sha256("\x1f".join(_clean(x,2000) for x in v).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"outcomes":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{"can_revise_internal_records":False,"can_contact_provider":False,"can_send_message":False,"can_execute":False}}
class ReflectionQualityOutcomeLineageStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/"reflection_quality_outcome_lineage.json"; self.clock=clock or _now; self.arbitration=ReflectionQualityArbitrationStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def record(self,event_id:str,*,arbitration_id:str,predecessor_quality_outcome_id:str="",continuity_state:str="continuous"):
  row=next((x for x in self.arbitration.snapshot().get("outcomes",[]) if x.get("arbitration_id")==arbitration_id),None)
  if not row: raise ValueError("existing quality arbitration outcome required")
  outcome=row.get("outcome")
  if outcome not in RECOGNIZED: raise ValueError("recognized quality outcome required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,**deepcopy(prior["result"]),"idempotent":True}
   structural=_digest(arbitration_id,outcome,predecessor_quality_outcome_id,continuity_state); existing=next((x for x in s["outcomes"] if x.get("structural_digest")==structural),None)
   if existing: result={"status":"duplicate_quality_outcome_suppressed","quality_outcome_id":existing["quality_outcome_id"]}
   else:
    now=self.clock(); qid=f"reflection-quality-outcome-{structural[:24]}"; s["outcomes"].append({"quality_outcome_id":qid,"arbitration_id":arbitration_id,"session_id":row.get("session_id"),"candidate_id":row.get("candidate_id"),"signal_id":row.get("signal_id"),"reflection_outcome_id":row.get("outcome_id"),"category":row.get("category"),"outcome":outcome,"reason_code":row.get("reason_code"),"provider_recovered":bool(row.get("provider_recovered")),"predecessor_quality_outcome_id":_clean(predecessor_quality_outcome_id),"continuity_state":_clean(continuity_state,80),"structural_digest":structural,"state":"recorded","created_at":now,"history":[{"change":"recorded","occurred_at":now,"content_free":True}],"belief_id":"","goal_id":"","self_model_id":"","message_id":"","action_id":""}); result={"status":"reflection_quality_outcome_lineage_recorded","quality_outcome_id":qid}
   now=self.clock();s["processed_events"].append({"event_id":_clean(event_id,180),"occurred_at":now,"result":deepcopy(result)});s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,**result,"idempotent":False}
 def inspection_summary(self):
  s=self._load();counts={}
  for x in s["outcomes"]: counts[x.get("outcome")]=counts.get(x.get("outcome"),0)+1
  return {"ok":True,"contract_version":CONTRACT_VERSION,"outcome_count":len(s["outcomes"]),"outcome_counts":counts,"recent_outcomes":deepcopy(s["outcomes"][-24:]),"authority_boundary":deepcopy(s["authority_boundary"]),"conclusions_exposed":False,"evidence_text_exposed":False,"hidden_reasoning_exposed":False,"belief_updated":False,"goal_updated":False,"self_model_updated":False,"provider_contacted":False,"message_sent":False,"external_action_executed":False}
def build_reflection_quality_outcome_lineage_inspection(runtime_root=None): return ReflectionQualityOutcomeLineageStore(runtime_root).inspection_summary()
