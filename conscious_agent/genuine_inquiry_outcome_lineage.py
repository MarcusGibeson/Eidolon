from __future__ import annotations
"""v1130.6 durable content-free genuine inquiry outcome lineage."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from genuine_inquiry_arbitration import GenuineInquiryArbitrationStore, OUTCOMES
from genuine_inquiry_candidates import GenuineInquiryCandidateStore
CONTRACT_VERSION='v1130.6'; SCHEMA_VERSION='1'
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v:Any,n=220): return ' '.join(str(v or '').split())[:n]
def _digest(*v:Any): return hashlib.sha256('\x1f'.join(_clean(x,2000) for x in v).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'outcomes':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{'can_browse':False,'can_contact_provider':False,'can_generate_question_text':False,'can_send_message':False,'can_create_notification':False,'can_mutate_initiative':False,'can_approve':False,'can_authorize':False,'can_execute':False}}
class GenuineInquiryOutcomeLineageStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root();self.path=self.runtime_root/'genuine_inquiry_outcome_lineage.json';self.clock=clock or _now;self.arbitration=GenuineInquiryArbitrationStore(self.runtime_root);self.candidates=GenuineInquiryCandidateStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def record(self,event_id:str,*,arbitration_id:str,predecessor_outcome_id:str='',continuity_state:str='continuous',timing_state:str='not_applicable',interruption_respected:bool=True):
  row=next((x for x in self.arbitration.snapshot().get('outcomes',[]) if x.get('arbitration_id')==arbitration_id),None)
  if not row or row.get('outcome') not in OUTCOMES: raise ValueError('existing recognized inquiry arbitration outcome required')
  candidate=next((x for x in self.candidates.snapshot().get('candidates',[]) if x.get('candidate_id')==row.get('candidate_id')), {})
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,**deepcopy(prior['result']),'idempotent':True}
   structural=_digest(arbitration_id,row.get('outcome'),predecessor_outcome_id,continuity_state,timing_state,interruption_respected);existing=next((x for x in s['outcomes'] if x.get('structural_digest')==structural),None)
   if existing: result={'status':'duplicate_inquiry_outcome_suppressed','inquiry_outcome_id':existing['inquiry_outcome_id']}
   else:
    now=self.clock();oid=f'inquiry-outcome-{structural[:24]}';s['outcomes'].append({'inquiry_outcome_id':oid,'arbitration_id':arbitration_id,'session_id':row.get('session_id'),'candidate_id':row.get('candidate_id'),'signal_ids':row.get('signal_ids',[]),'purpose_categories':row.get('purpose_categories',[]),'source_categories':row.get('source_categories',[]),'inquiry_classification':candidate.get('inquiry_classification',''),'bounded_scope_digest':candidate.get('bounded_scope_digest',''),'outcome':row.get('outcome'),'reason_code':row.get('reason_code'),'predecessor_outcome_id':_clean(predecessor_outcome_id),'continuity_state':_clean(continuity_state,80),'timing_state':_clean(timing_state,80),'interruption_respected':bool(interruption_respected),'structural_digest':structural,'state':'recorded','created_at':now,'history':[{'change':'recorded','occurred_at':now,'content_free':True}],'question_id':'','browse_request_id':'','provider_request_id':'','message_id':'','notification_id':'','initiative_id':''});result={'status':'inquiry_outcome_lineage_recorded','inquiry_outcome_id':oid}
   now=self.clock();s['processed_events'].append({'event_id':_clean(event_id,180),'occurred_at':now,'result':deepcopy(result)});s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,**result,'idempotent':False,'browser_contacted':False,'provider_contacted':False,'message_sent':False,'notification_created':False}
 def inspection_summary(self):
  s=self._load();counts={}
  for x in s['outcomes']:counts[x.get('outcome')]=counts.get(x.get('outcome'),0)+1
  return {'ok':True,'contract_version':CONTRACT_VERSION,'outcome_count':len(s['outcomes']),'outcome_counts':counts,'recent_outcomes':deepcopy(s['outcomes'][-24:]),'authority_boundary':deepcopy(s['authority_boundary']),'raw_content_exposed':False,'question_text_exposed':False,'hidden_reasoning_exposed':False,'browser_contacted':False,'provider_contacted':False,'message_sent':False,'notification_created':False,'initiative_mutated':False,'external_action_executed':False}
def build_genuine_inquiry_outcome_lineage_inspection(runtime_root=None): return GenuineInquiryOutcomeLineageStore(runtime_root).inspection_summary()
