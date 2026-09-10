from __future__ import annotations

"""v2504.4 structural cognitive outcome integration.

Outcomes describe durable consequences without storing hidden reasoning. This
store records candidate integrations only; it does not mutate belief, goal,
plan, memory, self-model, provider, communication, or protected-action stores.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import re
from pathlib import Path
from typing import Any, Callable, Mapping

from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock

CONTRACT_VERSION='v2504.4';SCHEMA_VERSION='1'
OUTCOME_TYPES={'NO_DURABLE_CHANGE','BELIEF_REVISION_CANDIDATE','GOAL_UPDATE_CANDIDATE','PLAN_UPDATE_CANDIDATE','MEMORY_INTEGRATION_CANDIDATE','SELF_MODEL_EVIDENCE_CANDIDATE','CONFLICT_RESOLUTION_CANDIDATE','THOUGHT_CONTINUATION','THOUGHT_COMPLETED'}
TARGETS={'none','beliefs','goals','planning','memory','self_model','conflict','continuity'}

def _now():return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v,n=260):return ' '.join(str(v or '').split())[:n]
def _digest(*p):return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in p).encode()).hexdigest()
def _ref(v):
 r=_clean(v,220)
 return r if re.fullmatch(r'[A-Za-z0-9._:/#-]{1,220}',r or '') else ('subject-digest:'+hashlib.sha256(r.encode()).hexdigest()[:32] if r else '')
def _default():return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'outcomes':[],'processed_events':[],'revision':0,'updated_at':'','controls':{'max_outcomes':512},'authority_boundary':{'can_apply_candidate':False,'can_authorize_action':False,'can_execute_action':False,'can_contact_provider':False,'can_send_message':False,'operator_authority_unchanged':True}}

class CognitiveOutcomeIntegrationStore:
 def __init__(self,runtime_root:str|Path,*,clock:Callable[[],str]|None=None):self.root=Path(runtime_root).expanduser().resolve();self.path=self.root/'unified_cognitive_outcomes.json';self.clock=clock or _now
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get('schema_version')!=SCHEMA_VERSION:s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def record(self,event_id:str,*,cycle_id:str,operation:str,outcome_type:str,target:str='none',subject_ref:str='',evidence_digests:list[str]|None=None,changed_fields:list[str]|None=None,confidence:float=0.5):
  event_id=_clean(event_id,180);cycle_id=_clean(cycle_id,220);operation=_clean(operation,60).upper();outcome_type=_clean(outcome_type,80).upper();target=_clean(target,40).lower()
  if not event_id or not cycle_id or not operation:raise ValueError('event_id, cycle_id, and operation required')
  if outcome_type not in OUTCOME_TYPES:raise ValueError('unsupported outcome_type')
  if target not in TARGETS:raise ValueError('unsupported target')
  if outcome_type=='NO_DURABLE_CHANGE' and target!='none':raise ValueError('no-durable-change must target none')
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,'status':'duplicate_event_ignored','result':deepcopy(prior['result']),'idempotent':True}
   ed=sorted({_clean(x,64) for x in (evidence_digests or []) if len(_clean(x,64))==64})[:32];fields=sorted({_clean(x,120) for x in (changed_fields or []) if _clean(x,120)})[:32];conf=round(max(0.0,min(float(confidence),1.0)),4)
   semantic=_digest(cycle_id,operation,outcome_type,target,subject_ref,*ed,*fields);dup=next((x for x in s['outcomes'] if x.get('semantic_key')==semantic),None)
   if dup:result={'status':'duplicate_outcome_ignored','outcome_id':dup['outcome_id'],'outcome_type':dup['outcome_type']}
   else:
    now=self.clock();oid='cognitive-outcome-'+semantic[:24];row={'outcome_id':oid,'semantic_key':semantic,'cycle_id':cycle_id,'operation':operation,'outcome_type':outcome_type,'target':target,'subject_ref':_ref(subject_ref),'evidence_digests':ed,'changed_fields':fields,'confidence':conf,'candidate_only':target!='none','applied':False,'created_at':now,'raw_chain_of_thought_stored':False};s['outcomes']=(s['outcomes']+[row])[-int(s['controls']['max_outcomes']):];result={'status':'outcome_recorded','outcome_id':oid,'outcome_type':outcome_type,'target':target}
   now=self.clock();s['processed_events']=(s['processed_events']+[{'event_id':event_id,'event_digest':_digest(event_id),'occurred_at':now,'result':deepcopy(result),'content_free':True}])[-1024:];s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,**result,'idempotent':False}
 def inspection_summary(self):
  s=self._load();counts={}
  for x in s['outcomes']:counts[x.get('outcome_type')]=counts.get(x.get('outcome_type'),0)+1
  keys=('outcome_id','cycle_id','operation','outcome_type','target','subject_ref','evidence_digests','changed_fields','confidence','candidate_only','applied','created_at')
  return {'ok':True,'contract_version':CONTRACT_VERSION,'revision':s['revision'],'outcome_count':len(s['outcomes']),'outcome_counts':counts,'recent_outcomes':[{k:x.get(k) for k in keys} for x in s['outcomes'][-24:]],'authority_boundary':deepcopy(s['authority_boundary']),'provider_contacted':False,'message_sent':False,'external_action_executed':False,'hidden_reasoning_exposed':False,'raw_chain_of_thought_stored':False}

def build_cognitive_outcome_integration_inspection(runtime_root:str|Path):return CognitiveOutcomeIntegrationStore(runtime_root).inspection_summary()
