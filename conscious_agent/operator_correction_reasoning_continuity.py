from __future__ import annotations
"""v1142.4 restart-safe continuity for bounded operator-guidance application."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from operator_correction_reasoning_application import OperatorCorrectionReasoningApplicationStore
CONTRACT_VERSION="v1142.4"; SCHEMA_VERSION="1"
STATES={"pending","claimed","resumable","completed","stale_released","deferred","superseded","retracted","retired"}
AUTHORITY_KEYS=("can_start_reasoning","can_generate_reasoning_text","can_mutate_history","can_mutate_belief","can_mutate_goal","can_execute","can_approve","can_authorize","can_install","can_promote","can_certify")
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*p:Any): return hashlib.sha256("\x1f".join(_clean(x,4000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"continuity_records":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{k:False for k in AUTHORITY_KEYS}}
class OperatorCorrectionReasoningContinuityStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/"operator_correction_reasoning_continuity.json"; self.clock=clock or _now; self.applications=OperatorCorrectionReasoningApplicationStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id:str,*,application_id:str,continuity_key:str,owner_id:str="",worker_claim_id:str="",restart_epoch:int=0,claim_stale:bool=False,completed:bool=False,retraction_ids:list[str]|None=None,supersession_ids:list[str]|None=None,retirement_ids:list[str]|None=None):
  event_id=_clean(event_id,180); application_id=_clean(application_id); continuity_key=_clean(continuity_key); owner_id=_clean(owner_id); worker_claim_id=_clean(worker_claim_id)
  if not event_id or not application_id or not continuity_key: raise ValueError("event, application, and continuity key required")
  app=next((r for r in self.applications.snapshot().get("application_records",[]) if r.get("application_id")==application_id),None)
  if not app: raise ValueError("exact v1142.3 application required")
  retractions=sorted({_clean(x) for x in retraction_ids or [] if _clean(x)}); supersessions=sorted({_clean(x) for x in supersession_ids or [] if _clean(x)}); retirements=sorted({_clean(x) for x in retirement_ids or [] if _clean(x)})
  state="pending"
  if retirements: state="retired"
  elif retractions: state="retracted"
  elif supersessions: state="superseded"
  elif completed: state="completed"
  elif claim_stale: state="stale_released"
  elif app.get("state")!="selected": state="deferred"
  elif worker_claim_id: state="claimed"
  elif int(restart_epoch)>0: state="resumable"
  structural=_digest(application_id,continuity_key,owner_id,worker_claim_id,restart_epoch,state,*retractions,*supersessions,*retirements)
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,**deepcopy(prior["result"]),"idempotent":True}
   duplicate=next((x for x in s["continuity_records"] if x.get("continuity_key")==continuity_key and x.get("state") in {"pending","claimed","resumable"}),None)
   if duplicate: result={"status":"duplicate_suppressed","continuity_id":duplicate["continuity_id"],"state":"deferred"}
   else:
    now=self.clock(); cid=f"operator-guidance-continuity-{structural[:24]}"; row={"continuity_id":cid,"application_id":application_id,"continuity_key":continuity_key,"owner_id":owner_id,"worker_claim_id":"" if claim_stale else worker_claim_id,"restart_epoch":max(0,int(restart_epoch)),"selected_guidance_ids":list(app.get("selected_guidance_ids") or []),"application_structural_digest":app.get("structural_digest"),"state":state,"stale_claim_released":bool(claim_stale),"historical_record_preserved":True,"reasoning_started":False,"reasoning_text_generated":False,"state_mutated":False,"retraction_ids":retractions,"supersession_ids":supersessions,"retirement_ids":retirements,"structural_digest":structural,"created_at":now,"history":[{"change":"continuity_recorded","state":state,"occurred_at":now,"content_free":True}]};s["continuity_records"].append(row);result={"status":"continuity_recorded","continuity_id":cid,"state":state}
   now=self.clock();s["processed_events"].append({"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True});s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,**result,"idempotent":False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for r in s["continuity_records"]:counts[r.get("state")]=counts.get(r.get("state"),0)+1
  keys=("continuity_id","application_id","continuity_key","owner_id","worker_claim_id","restart_epoch","selected_guidance_ids","application_structural_digest","state","stale_claim_released","historical_record_preserved","reasoning_started","reasoning_text_generated","state_mutated","retraction_ids","supersession_ids","retirement_ids","structural_digest")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"record_count":len(s["continuity_records"]),"state_counts":counts,"recent_records":[{k:r.get(k) for k in keys} for r in s["continuity_records"][-32:]],"authority_boundary":deepcopy(s["authority_boundary"]),"raw_content_exposed":False,"operator_text_exposed":False,"reasoning_text_exposed":False,"history_rewritten":False,"reasoning_started":False}
def build_operator_correction_reasoning_continuity_inspection(runtime_root=None): return OperatorCorrectionReasoningContinuityStore(runtime_root).inspection_summary()
