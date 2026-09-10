from __future__ import annotations
"""v1133.0 durable content-free internally generated goal-formation signals."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
CONTRACT_VERSION="v1133.0"; SCHEMA_VERSION="1"
SOURCE_CATEGORIES={"motivation","inquiry_outcome","world_model_outcome","memory","concern","obligation","unfinished_thought","goal_predecessor"}
PURPOSE_CATEGORIES={"capability_improvement","reliability","knowledge","relationship_continuity","project_progress","self_understanding","maintenance","deliberate_no_goal_review"}
STATES={"active","suppressed","deferred","awaiting_prerequisite","requires_operator_review","superseded","retracted","stale","retired"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*p:Any): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"signals":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{"can_activate_goal":False,"can_create_plan":False,"can_create_initiative":False,"can_browse":False,"can_contact_provider":False,"can_execute":False,"can_modify_files":False,"can_send_message":False,"can_create_notification":False,"can_approve":False,"can_authorize":False,"can_promote":False,"can_certify":False}}
class InternallyGeneratedGoalSignalStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/"internally_generated_goal_signals.json"; self.clock=clock or _now
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id:str,*,origin_ids:list[str],source_categories:list[str],purpose_category:str,evidence_ids:list[str],relevance:float=.5,importance:float=.5,urgency:float=.0,uncertainty:float=.5,expected_value:float=.5,estimated_cost:float=.5,time_horizon:str="unspecified",dependency_ids:list[str]|None=None,predecessor_goal_ids:list[str]|None=None,project_id:str="",conversation_id:str="",scope_digest:str="",operator_review_required:bool=False):
  event_id=_clean(event_id,180); origins=list(dict.fromkeys(_clean(x,220) for x in origin_ids if _clean(x,220))); sources=sorted(set(source_categories)); evidence=list(dict.fromkeys(_clean(x,220) for x in evidence_ids if _clean(x,220))); deps=list(dict.fromkeys(_clean(x,220) for x in (dependency_ids or []) if _clean(x,220))); preds=list(dict.fromkeys(_clean(x,220) for x in (predecessor_goal_ids or []) if _clean(x,220)))
  if not event_id or not origins or not evidence or not sources or not set(sources).issubset(SOURCE_CATEGORIES) or purpose_category not in PURPOSE_CATEGORIES: raise ValueError("complete structural goal-formation lineage required")
  clamp=lambda x:round(max(0.0,min(float(x),1.0)),4); relevance,importance,urgency,uncertainty,expected_value,estimated_cost=[clamp(x) for x in (relevance,importance,urgency,uncertainty,expected_value,estimated_cost)]
  false_pressure=(urgency>.8 and importance<.35) or (importance<.2 and expected_value<.25); semantic=_digest(*origins,*sources,purpose_category,*evidence,scope_digest,time_horizon)
  state="requires_operator_review" if operator_review_required else ("awaiting_prerequisite" if deps else ("suppressed" if false_pressure or uncertainty>.97 else "active"))
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   dup=next((x for x in s["signals"] if x.get("semantic_key")==semantic and x.get("state") in {"active","deferred","awaiting_prerequisite","requires_operator_review"}),None)
   if dup: result={"status":"duplicate_signal_ignored","signal_id":dup["signal_id"]}
   else:
    now=self.clock(); sid=f"goal-signal-{semantic[:24]}"; row={"signal_id":sid,"semantic_key":semantic,"origin_ids":origins,"source_categories":sources,"purpose_category":purpose_category,"evidence_ids":evidence,"relevance":relevance,"importance":importance,"urgency":urgency,"uncertainty":uncertainty,"expected_value":expected_value,"estimated_cost":estimated_cost,"time_horizon":_clean(time_horizon,80),"dependency_ids":deps,"predecessor_goal_ids":preds,"project_id":_clean(project_id,160),"conversation_id":_clean(conversation_id,160),"scope_digest":_clean(scope_digest,128),"operator_review_required":bool(operator_review_required),"false_pressure_suppressed":bool(false_pressure),"state":state,"created_at":now,"updated_at":now,"goal_candidate_id":"","goal_id":"","plan_id":"","initiative_id":"","message_id":"","approval_id":"","authorization_id":"","action_id":""}; s["signals"].append(row); result={"status":"goal_signal_registered","signal_id":sid,"state":state}
   now=self.clock(); s["processed_events"].append({"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}); s["revision"]+=1; s["updated_at"]=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s["signals"]: counts[x.get("state")]=counts.get(x.get("state"),0)+1
  keys=("signal_id","origin_ids","source_categories","purpose_category","evidence_ids","relevance","importance","urgency","uncertainty","expected_value","estimated_cost","time_horizon","dependency_ids","predecessor_goal_ids","project_id","conversation_id","scope_digest","operator_review_required","false_pressure_suppressed","state","goal_candidate_id","goal_id","plan_id","initiative_id","message_id","approval_id","authorization_id","action_id")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"signal_count":len(s["signals"]),"state_counts":counts,"recent_signals":[{k:x.get(k) for k in keys} for x in s["signals"][-24:]],"authority_boundary":deepcopy(s["authority_boundary"]),"raw_content_exposed":False,"goal_text_exposed":False,"motivation_text_exposed":False,"memory_text_exposed":False,"hidden_reasoning_exposed":False,"provider_contacted":False,"external_action_executed":False}
def build_internally_generated_goal_signal_inspection(runtime_root=None): return InternallyGeneratedGoalSignalStore(runtime_root).inspection_summary()
