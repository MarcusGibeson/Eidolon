from __future__ import annotations
"""Accountable merge, reformulation, retirement, and unresolved lifecycle for curiosity records."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from curiosity_inquiry_promotion import CuriosityInquiryPromotionStore
CONTRACT_VERSION="v1111.7"
OUTCOMES={"retain","reformulate","merge","retire_answered","retire_obsolete","retire_duplicate","suspend","reopen","unresolved"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=300): return " ".join(str(v or "").split())[:n]
def _digest(*p): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":"1","contract_version":CONTRACT_VERSION,"decisions":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{"can_activate_inquiry":False,"can_browse":False,"can_ask_user":False,"can_contact_provider":False,"can_message_user":False,"can_execute":False,"can_authorize":False}}
class CuriosityQuestionLifecycleStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/"curiosity_question_lifecycle.json"; self.clock=clock or _now; self.promotions=CuriosityInquiryPromotionStore(self.runtime_root,clock=self.clock)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1":s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self):return deepcopy(self._load())
 def decide(self,event_id,*,inquiry_candidate_id,outcome,replacement_digest="",merge_target_id="",reason_code=""):
  event_id=_clean(event_id,180); iid=_clean(inquiry_candidate_id,220); outcome=_clean(outcome,40)
  if not event_id or not iid or outcome not in OUTCOMES:raise ValueError("valid event_id, inquiry_candidate_id, and outcome required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   p=next((x for x in self.promotions.snapshot()["promotions"] if x.get("inquiry_candidate_id")==iid),None)
   if not p:result={"status":"lifecycle_rejected","reason":"missing_inquiry_candidate","decision_id":""}
   elif outcome=="merge" and not _clean(merge_target_id,220):result={"status":"lifecycle_rejected","reason":"merge_target_required","decision_id":""}
   elif outcome=="reformulate" and not _clean(replacement_digest,64):result={"status":"lifecycle_rejected","reason":"replacement_digest_required","decision_id":""}
   else:
    now=self.clock(); did=f"curiosity-lifecycle-{_digest(event_id)[:24]}"; terminal=outcome.startswith("retire_") or outcome=="merge"; result={"status":"lifecycle_decided","decision_id":did,"inquiry_candidate_id":iid,"outcome":outcome,"reason_code":_clean(reason_code,80),"replacement_digest":_clean(replacement_digest,64),"merge_target_id":_clean(merge_target_id,220),"active_influence":not terminal and outcome!="suspend","active_inquiry_id":"","browse_receipt_id":"","user_prompt_id":"","proposal_id":"","authorization_id":"","action_id":""}; s["decisions"]=(s["decisions"]+[{**result,"event_digest":_digest(event_id),"occurred_at":now,"content_free":True}])[-512:]
   now=self.clock();s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-1024:];s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load();rows=s["decisions"];counts={};
  for x in rows:counts[x.get("outcome")]=counts.get(x.get("outcome"),0)+1
  return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"decision_count":len(rows),"outcome_counts":counts,"recent_decisions":[{k:x.get(k) for k in ("decision_id","inquiry_candidate_id","outcome","reason_code","replacement_digest","merge_target_id","active_influence","active_inquiry_id","browse_receipt_id","user_prompt_id","proposal_id","authorization_id","action_id")} for x in rows[-24:]],"authority_boundary":deepcopy(s["authority_boundary"]),"provider_contacted":False,"external_browsing_performed":False,"message_sent":False,"hidden_reasoning_exposed":False,"private_content_exposed":False,"runtime_mutated":False}
def build_curiosity_question_lifecycle_inspection(runtime_root=None):return CuriosityQuestionLifecycleStore(runtime_root).inspection_summary()
