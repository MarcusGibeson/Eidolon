from __future__ import annotations
"""Deterministic relevance, answerability, and intrusion restraint for curiosity questions."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from curiosity_question_formulation import CuriosityQuestionStore
CONTRACT_VERSION="v1111.4"
def _now():return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=300):return " ".join(str(v or "").split())[:n]
def _digest(*p):return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root():return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default():return {"schema_version":"1","contract_version":CONTRACT_VERSION,"decisions":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"minimum_quality":.52,"max_sensitivity":.72,"max_resource_cost":.7},"authority_boundary":{"can_create_inquiry":False,"can_ask_user":False,"can_browse":False,"can_contact_provider":False,"can_message_user":False,"can_execute":False,"can_authorize":False}}
class CuriosityQualityArbitrator:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None):self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/"curiosity_quality_arbitration.json";self.clock=clock or _now;self.questions=CuriosityQuestionStore(self.runtime_root,clock=self.clock)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1":s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self):return deepcopy(self._load())
 def evaluate(self,event_id,*,question_id,quiet=False,sleep=False,paused=False,topic_allowed=True,user_relevant=True):
  event_id=_clean(event_id,180);qid=_clean(question_id,220)
  if not event_id or not qid:raise ValueError("event_id and question_id required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   q=next((x for x in self.questions.snapshot()["questions"] if x.get("question_id")==qid),None);outcome="abandon";reason="missing_question";score=0.0
   if q:
    score=round(.28*float(q.get("specificity") or 0)+.30*float(q.get("answerability") or 0)+.30*float(q.get("information_value") or 0)-.18*float(q.get("sensitivity") or 0)-.12*float(q.get("resource_cost") or 0),6)
    if quiet or sleep or paused:outcome,reason="deliberate_silence","control_boundary"
    elif not topic_allowed:outcome,reason="defer","topic_boundary"
    elif not user_relevant:outcome,reason="internal_only","user_irrelevant"
    elif float(q.get("sensitivity") or 0)>s["controls"]["max_sensitivity"]:outcome,reason="defer","sensitivity_boundary"
    elif float(q.get("resource_cost") or 0)>s["controls"]["max_resource_cost"]:outcome,reason="defer","resource_boundary"
    elif score>=s["controls"]["minimum_quality"]:outcome,reason="eligible_for_inquiry","quality_threshold_met"
    else:outcome,reason="reformulate","quality_below_threshold"
   now=self.clock();did=f"curiosity-quality-{_digest(event_id)[:24]}";result={"status":"quality_decided","decision_id":did,"question_id":qid if q else "","outcome":outcome,"reason":reason,"score":score,"inquiry_id":"","user_prompt_id":"","provider_contacted":False,"external_browsing_performed":False,"message_sent":False,"authority_granted":False};s["decisions"]=(s["decisions"]+[{**result,"event_digest":_digest(event_id),"occurred_at":now,"content_free":True}])[-512:];s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-1024:];s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load();rows=s["decisions"];return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"decision_count":len(rows),"outcome_counts":{k:sum(x.get("outcome")==k for x in rows) for k in ("eligible_for_inquiry","reformulate","defer","deliberate_silence","internal_only","abandon")},"recent_decisions":[{k:x.get(k) for k in ("decision_id","question_id","outcome","reason","score","inquiry_id","user_prompt_id","provider_contacted","external_browsing_performed","message_sent","authority_granted")} for x in rows[-24:]],"controls":deepcopy(s["controls"]),"authority_boundary":deepcopy(s["authority_boundary"]),"hidden_reasoning_exposed":False,"private_content_exposed":False,"runtime_mutated":False}
def build_curiosity_quality_inspection(runtime_root=None):return CuriosityQualityArbitrator(runtime_root).inspection_summary()
