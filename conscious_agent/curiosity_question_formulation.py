from __future__ import annotations
"""Bounded internal question formulation from selected curiosity receipts."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from curiosity_arbitration import CuriosityArbitrator
CONTRACT_VERSION="v1111.3"
def _now():return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=600):return " ".join(str(v or "").split())[:n]
def _digest(*p):return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root():return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default():return {"schema_version":"1","contract_version":CONTRACT_VERSION,"questions":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"max_questions":256,"max_words":24,"max_active":64},"state_separation":{"question_is_inquiry":False,"question_is_user_prompt":False,"question_is_proposal":False,"proposal_is_authorization":False,"authorization_is_execution":False},"authority_boundary":{"can_create_inquiry":False,"can_ask_user":False,"can_browse":False,"can_contact_provider":False,"can_message_user":False,"can_execute":False,"can_authorize":False}}
class CuriosityQuestionStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None):self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/"curiosity_questions.json";self.clock=clock or _now;self.arbitrator=CuriosityArbitrator(self.runtime_root,clock=self.clock)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1":s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self):return deepcopy(self._load())
 def formulate(self,event_id,*,selection_receipt_id,question_text,scope="internal",specificity=.5,answerability=.5,information_value=.5,sensitivity=.2,resource_cost=.2):
  event_id=_clean(event_id,180);rid=_clean(selection_receipt_id,220);q=_clean(question_text,800)
  if not event_id or not rid or not q:raise ValueError("event_id, selection_receipt_id, and question_text required")
  if scope!="internal":raise ValueError("only internal question scope is allowed")
  words=q.split()
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   receipt=next((x for x in self.arbitrator.snapshot()["receipts"] if x.get("receipt_id")==rid and x.get("candidate_id")),None)
   if not receipt:result={"status":"question_not_formulated","reason":"invalid_selection_receipt","question_id":""}
   elif len(words)>s["controls"]["max_words"] or not q.endswith("?"):result={"status":"question_not_formulated","reason":"bounded_formulation_failed","question_id":""}
   elif sum(x.get("state")=="candidate" for x in s["questions"])>=s["controls"]["max_active"]:result={"status":"question_not_formulated","reason":"active_limit","question_id":""}
   else:
    key=_digest(receipt.get("candidate_id"),q.lower());existing=next((x for x in s["questions"] if x.get("semantic_key")==key and x.get("state")=="candidate"),None)
    if existing:result={"status":"duplicate_question_ignored","question_id":existing["question_id"]}
    else:
     b=lambda v:round(max(0,min(1,float(v))),4);now=self.clock();qid=f"curiosity-question-{key[:24]}";row={"question_id":qid,"semantic_key":key,"selection_receipt_id":rid,"candidate_id":receipt.get("candidate_id"),"question_digest":_digest(q),"word_count":len(words),"scope":"internal","specificity":b(specificity),"answerability":b(answerability),"information_value":b(information_value),"sensitivity":b(sensitivity),"resource_cost":b(resource_cost),"state":"candidate","eligible_for_inquiry":False,"inquiry_id":"","user_prompt_id":"","proposal_id":"","authorization_id":"","action_id":"","created_at":now,"updated_at":now,"history":[{"change":"formulated","occurred_at":now,"content_free":True}]};s["questions"]=(s["questions"]+[row])[-s["controls"]["max_questions"]:];result={"status":"question_formulated","question_id":qid}
   now=self.clock();s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-1024:];s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load();rows=s["questions"];return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"question_count":len(rows),"active_question_count":sum(x.get("state")=="candidate" for x in rows),"recent_questions":[{k:x.get(k) for k in ("question_id","selection_receipt_id","candidate_id","question_digest","word_count","scope","specificity","answerability","information_value","sensitivity","resource_cost","state","eligible_for_inquiry","inquiry_id","user_prompt_id","proposal_id","authorization_id","action_id")} for x in rows[-24:]],"controls":deepcopy(s["controls"]),"state_separation":deepcopy(s["state_separation"]),"authority_boundary":deepcopy(s["authority_boundary"]),"provider_contacted":False,"external_browsing_performed":False,"message_sent":False,"hidden_reasoning_exposed":False,"private_content_exposed":False,"runtime_mutated":False}
def build_curiosity_question_inspection(runtime_root=None):return CuriosityQuestionStore(runtime_root).inspection_summary()
