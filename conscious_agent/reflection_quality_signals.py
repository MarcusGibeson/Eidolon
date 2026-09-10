from __future__ import annotations
"""v1126.0 durable structural reflection-quality signals."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from reflective_outcome_lineage import ReflectiveOutcomeLineageStore
CONTRACT_VERSION="v1126.0"; SCHEMA_VERSION="1"
CATEGORIES={"unsupported_conclusion","contradiction","confidence_mismatch","provider_failure","provider_recovery","well_supported"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=300): return " ".join(str(v or "").split())[:n]
def _digest(*v:Any): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in v).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"signals":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{"can_revise_belief":False,"can_revise_goal":False,"can_revise_self_model":False,"can_contact_provider":False,"can_send_message":False,"can_execute":False}}
class ReflectionQualitySignalStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/"reflection_quality_signals.json"; self.clock=clock or _now; self.lineage=ReflectiveOutcomeLineageStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def derive(self,event_id:str,*,outcome_id:str,contradicts_outcome_id:str=""):
  rows=self.lineage.snapshot().get("outcomes",[]); row=next((x for x in rows if x.get("outcome_id")==outcome_id),None)
  if not row: raise ValueError("existing reflective outcome required")
  category="well_supported"; severity=.1; recovery=False
  if row.get("outcome")=="provider_failure": category="provider_failure";severity=.9;recovery=True
  elif row.get("outcome")=="conclusion" and not row.get("evidence_refs"): category="unsupported_conclusion";severity=.9
  elif float(row.get("uncertainty",1))>.7 and row.get("outcome")=="conclusion": category="confidence_mismatch";severity=.7
  if contradicts_outcome_id:
   other=next((x for x in rows if x.get("outcome_id")==contradicts_outcome_id),None)
   if not other: raise ValueError("contradicted outcome must exist")
   if other.get("conclusion_digest")!=row.get("conclusion_digest"): category="contradiction";severity=.8
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,**deepcopy(prior["result"]),"idempotent":True}
   structural=_digest(outcome_id,contradicts_outcome_id,category); existing=next((x for x in s["signals"] if x.get("structural_digest")==structural),None)
   if existing: result={"status":"duplicate_quality_signal_suppressed","signal_id":existing["signal_id"]}
   else:
    now=self.clock();sid=f"reflection-quality-{structural[:24]}";s["signals"].append({"signal_id":sid,"outcome_id":outcome_id,"subject_id":row.get("subject_id"),"category":category,"severity":severity,"uncertainty":float(row.get("uncertainty",1)),"evidence_ref_count":len(row.get("evidence_refs",[])),"contradicts_outcome_id":_clean(contradicts_outcome_id,220),"recovery_recommended":recovery,"structural_digest":structural,"state":"active","created_at":now,"history":[{"change":"derived","occurred_at":now,"content_free":True}]});result={"status":"reflection_quality_signal_recorded","signal_id":sid,"category":category}
   now=self.clock();s["processed_events"].append({"event_id":event_id,"occurred_at":now,"result":deepcopy(result)});s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,**result,"idempotent":False}
 def inspection_summary(self):
  s=self._load();counts={}
  for x in s["signals"]: counts[x.get("category")]=counts.get(x.get("category"),0)+1
  recent=[{k:x.get(k) for k in ("signal_id","outcome_id","subject_id","category","severity","uncertainty","evidence_ref_count","contradicts_outcome_id","recovery_recommended","structural_digest","state","created_at")} for x in s["signals"][-24:]]
  return {"ok":True,"contract_version":CONTRACT_VERSION,"signal_count":len(s["signals"]),"category_counts":counts,"recent_signals":recent,"authority_boundary":deepcopy(s["authority_boundary"]),"conclusions_exposed":False,"evidence_text_exposed":False,"hidden_reasoning_exposed":False,"belief_updated":False,"goal_updated":False,"self_model_updated":False,"provider_contacted":False,"message_sent":False,"external_action_executed":False}
def build_reflection_quality_signal_inspection(runtime_root=None): return ReflectionQualitySignalStore(runtime_root).inspection_summary()
