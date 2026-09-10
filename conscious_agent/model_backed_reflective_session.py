from __future__ import annotations
"""v1125.0 bounded provider-neutral model-backed reflective session foundation."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, json, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from reflective_subject_intake import ReflectiveSubjectIntakeStore
from local_model import LocalModelClient, LocalModelError
CONTRACT_VERSION="v1125.0"; SCHEMA_VERSION="1"
OUTCOMES={"conclusion","remain_uncertain","deliberate_silence","provider_failure","deferred"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=1200): return " ".join(str(v or "").split())[:n]
def _digest(*v:Any): return hashlib.sha256("\x1f".join(_clean(x,5000) for x in v).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"sessions":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{"can_update_belief":False,"can_update_goal":False,"can_update_self_model":False,"can_create_initiative":False,"can_send_message":False,"can_browse":False,"can_execute":False,"can_approve":False}}
def _parse(text:str)->dict[str,Any]:
 text=str(text or "").strip(); candidate=text
 if "```" in candidate:
  pieces=candidate.split("```"); candidate=next((p.strip()[4:].strip() if p.strip().startswith("json") else p.strip() for p in pieces if "{" in p and "}" in p),candidate)
 try: data=json.loads(candidate)
 except Exception:
  a=candidate.find("{");b=candidate.rfind("}");
  try:data=json.loads(candidate[a:b+1]) if a>=0 and b>a else {}
  except Exception:data={}
 if not isinstance(data,dict):data={}
 outcome=_clean(data.get("outcome"),60)
 if outcome not in {"conclusion","remain_uncertain","deliberate_silence"}: outcome="remain_uncertain"
 return {"outcome":outcome,"conclusion":_clean(data.get("conclusion"),1200),"uncertainty":max(0.0,min(float(data.get("uncertainty",0.5)),1.0)),"evidence_refs":sorted({_clean(x,220) for x in data.get("evidence_refs",[]) if _clean(x,220)})[:16],"communication_recommendation":"silence" if _clean(data.get("communication_recommendation"),40)!="communicate" else "communicate"}
class ModelBackedReflectiveSessionStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None,model_generate:Callable[[str],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root();self.path=self.runtime_root/"model_backed_reflective_sessions.json";self.clock=clock or _now;self.subjects=ReflectiveSubjectIntakeStore(self.runtime_root);self.model_generate=model_generate
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self):return deepcopy(self._load())
 def run(self,event_id:str,*,subject_id:str,max_cycles:int=1,max_tokens:int=500):
  event_id=_clean(event_id,180);subject_id=_clean(subject_id,220);max_cycles=max(1,min(int(max_cycles),3));max_tokens=max(64,min(int(max_tokens),1200))
  subject=next((x for x in self.subjects.snapshot().get("subjects",[]) if x.get("subject_id")==subject_id and x.get("state")=="active" and not x.get("operator_review_required")),None)
  if not subject:raise ValueError("active operator-cleared reflective subject required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   active=next((x for x in s["sessions"] if x.get("subject_id")==subject_id and x.get("state") in {"running","paused"}),None)
   if active: result={"status":"reflective_session_reused","session_id":active["session_id"],"outcome":active.get("outcome","")}
   else:
    now=self.clock(); structural=_digest(subject_id,subject.get("structural_digest"),max_cycles,max_tokens);sid=f"reflective-session-{structural[:24]}"; prompt=("Return one JSON object only with keys outcome, conclusion, uncertainty, evidence_refs, communication_recommendation. " "Allowed outcomes: conclusion, remain_uncertain, deliberate_silence. Use only the structural subject lineage supplied. Do not invent facts, actions, messages, or authority. " f"subject_kind={subject['subject_kind']}; source_contract={subject['source_contract']}; source_id={subject['source_id']}; importance={subject['importance']}; uncertainty={subject['uncertainty']}; max_tokens={max_tokens}")
    provider_error={}; raw=""
    try:
     if self.model_generate: raw=self.model_generate(prompt)
     else:
      client=LocalModelClient();raw=client.generate(prompt);client.close()
     parsed=_parse(raw); outcome=parsed["outcome"]
    except LocalModelError as exc: parsed={"outcome":"provider_failure","conclusion":"","uncertainty":1.0,"evidence_refs":[],"communication_recommendation":"silence"};outcome="provider_failure";provider_error=exc.to_safe_dict()
    except Exception as exc: parsed={"outcome":"provider_failure","conclusion":"","uncertainty":1.0,"evidence_refs":[],"communication_recommendation":"silence"};outcome="provider_failure";provider_error={"code":"bounded_generation_failure","exception_type":type(exc).__name__,"redacted":True}
    conclusion=parsed.get("conclusion",""); row={"session_id":sid,"subject_id":subject_id,"subject_lineage_digest":subject.get("structural_digest"),"provider_used":outcome!="provider_failure","max_cycles":max_cycles,"max_tokens":max_tokens,"cycles_completed":1,"state":"failed" if outcome=="provider_failure" else "closed","outcome":outcome,"conclusion":conclusion,"conclusion_digest":_digest(conclusion),"uncertainty":parsed.get("uncertainty",1.0),"evidence_refs":parsed.get("evidence_refs",[]),"communication_recommendation":parsed.get("communication_recommendation","silence"),"provider_error":provider_error,"prompt_digest":_digest(prompt),"raw_provider_payload":"","hidden_reasoning":"","created_at":now,"updated_at":now,"history":[{"change":"bounded_reflection_completed" if outcome!="provider_failure" else "provider_failure_recorded","occurred_at":now}],"belief_id":"","goal_id":"","self_model_id":"","initiative_id":"","message_id":"","action_id":""};s["sessions"].append(row);result={"status":"reflective_session_completed" if outcome!="provider_failure" else "reflective_session_provider_failure","session_id":sid,"outcome":outcome,"communication_recommendation":row["communication_recommendation"],"belief_updated":False,"goal_updated":False,"self_model_updated":False,"message_sent":False,"action_executed":False}
   now=self.clock();s["processed_events"].append({"event_id":event_id,"occurred_at":now,"result":deepcopy(result)});s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,**result,"idempotent":False}
 def inspection_summary(self):
  s=self._load();counts={}
  for x in s["sessions"]:counts[x.get("outcome")]=counts.get(x.get("outcome"),0)+1
  recent=[{k:x.get(k) for k in ("session_id","subject_id","subject_lineage_digest","provider_used","max_cycles","max_tokens","cycles_completed","state","outcome","conclusion_digest","uncertainty","evidence_refs","communication_recommendation","provider_error","prompt_digest","created_at","updated_at")} for x in s["sessions"][-24:]]
  return {"ok":True,"contract_version":CONTRACT_VERSION,"session_count":len(s["sessions"]),"outcome_counts":counts,"recent_sessions":recent,"authority_boundary":deepcopy(s["authority_boundary"]),"conclusions_exposed":False,"prompts_exposed":False,"provider_payloads_exposed":False,"hidden_reasoning_exposed":False,"belief_updated":False,"goal_updated":False,"self_model_updated":False,"initiative_created":False,"message_sent":False,"browsing_performed":False,"external_action_executed":False}
def build_model_backed_reflective_session_inspection(runtime_root=None):return ModelBackedReflectiveSessionStore(runtime_root).inspection_summary()
