from __future__ import annotations
"""Durable privacy-safe behavioral outcome evidence ledger (v1112.0)."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable, Iterable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
CONTRACT_VERSION='v1112.0'
OUTCOME_CLASSES={'initiative_response','attention_utility','objective_state','reflection_uncertainty','curiosity_utility','prediction_correction','identity_consistency','stable_user_correction','deliberate_silence'}
STATES={'active','corrected','retracted'}
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v,n=400): return ' '.join(str(v or '').split())[:n]
def _digest(*parts): return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in parts).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':'1','contract_version':CONTRACT_VERSION,'outcomes':[],'processed_events':[],'revision':0,'updated_at':'','controls':{'max_outcomes':512,'max_lineage_refs':24},'state_separation':{'outcome_is_attribution':False,'attribution_is_evaluation':False,'evaluation_is_adaptation_proposal':False,'proposal_is_approval':False,'approval_is_authorization':False,'authorization_is_execution':False},'authority_boundary':{'can_adapt':False,'can_browse':False,'can_contact_provider':False,'can_message':False,'can_execute':False,'can_modify_files':False,'can_authorize':False}}
class BehavioralOutcomeStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/'behavioral_outcomes.json'; self.clock=clock or _now
 def _load(self):
  state=load_json_file(self.path,_default(),expected_type=dict)
  if state.get('schema_version')!='1': state=_default()
  for k,v in _default().items(): state.setdefault(k,deepcopy(v))
  return state
 def snapshot(self): return deepcopy(self._load())
 def record_outcome(self,event_id,*,outcome_class,outcome_state,origin_type,origin_id,lineage_refs:Iterable[str],score=0.0,feedback_known=True,project_id='',provider_id='',correction_of=''):
  eid=_clean(event_id,180); cls=_clean(outcome_class,80); ost=_clean(outcome_state,80); origin_type=_clean(origin_type,80); oid=_clean(origin_id,240); refs=tuple(_clean(x,240) for x in lineage_refs if _clean(x,240))
  if not eid or not oid or not refs: raise ValueError('event_id, origin_id, and lineage_refs required')
  if cls not in OUTCOME_CLASSES: raise ValueError('unsupported outcome_class')
  if not feedback_known and ost in {'success','useful','accepted','completed'}: raise ValueError('missing feedback cannot imply success')
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   state=self._load(); prior=next((x for x in state['processed_events'] if x.get('event_id')==eid),None)
   if prior: return {'ok':True,'status':'duplicate_event_ignored','result':deepcopy(prior['result']),'idempotent':True}
   key=_digest(cls,ost,origin_type,oid,*refs,correction_of); existing=next((x for x in state['outcomes'] if x.get('semantic_key')==key),None)
   if existing: result={'status':'duplicate_outcome_ignored','outcome_id':existing['outcome_id']}
   else:
    now=self.clock(); outcome_id=f'outcome-{key[:24]}'; active=not bool(correction_of)
    row={'outcome_id':outcome_id,'semantic_key':key,'outcome_class':cls,'outcome_state':ost,'origin_type':origin_type,'origin_id_digest':_digest(oid),'lineage_ref_digests':[_digest(x) for x in refs[:24]],'lineage_count':len(refs[:24]),'score':round(max(-1,min(1,float(score))),4),'feedback_known':bool(feedback_known),'project_digest':_digest(project_id),'provider_digest':_digest(provider_id),'record_state':'active','active_influence':active,'correction_of_digest':_digest(correction_of) if correction_of else '','created_at':now,'updated_at':now,'content_free':True,'authority_granted':False}
    if correction_of:
     for old in state['outcomes']:
      if old.get('outcome_id')==correction_of: old['active_influence']=False; old['record_state']='corrected'; old['updated_at']=now
    state['outcomes']=(state['outcomes']+[row])[-state['controls']['max_outcomes']:]; result={'status':'outcome_recorded','outcome_id':outcome_id}
   now=self.clock(); state['processed_events']=(state['processed_events']+[{'event_id':eid,'event_digest':_digest(eid),'occurred_at':now,'result':deepcopy(result),'content_free':True}])[-2048:]; state['revision']+=1; state['updated_at']=now; write_json_atomic(self.path,state,expected_type=dict,sort_keys=True); return {'ok':True,'status':result['status'],'result':result,'idempotent':False}
 def retract(self,event_id,outcome_id):
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   state=self._load(); prior=next((x for x in state['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,'status':'duplicate_event_ignored','result':deepcopy(prior['result']),'idempotent':True}
   row=next((x for x in state['outcomes'] if x.get('outcome_id')==outcome_id),None)
   if not row: raise ValueError('unknown outcome_id')
   now=self.clock(); row['record_state']='retracted'; row['active_influence']=False; row['updated_at']=now; result={'status':'outcome_retracted','outcome_id':outcome_id}; state['processed_events'].append({'event_id':event_id,'event_digest':_digest(event_id),'occurred_at':now,'result':result,'content_free':True}); state['revision']+=1; state['updated_at']=now; write_json_atomic(self.path,state,expected_type=dict,sort_keys=True); return {'ok':True,**result}
 def inspection_summary(self):
  s=self._load(); rows=s['outcomes']; return {'ok':True,'contract_version':CONTRACT_VERSION,'revision':s['revision'],'outcome_count':len(rows),'active_outcome_count':sum(x.get('active_influence') for x in rows),'unknown_feedback_count':sum(not x.get('feedback_known') for x in rows),'corrected_count':sum(x.get('record_state')=='corrected' for x in rows),'retracted_count':sum(x.get('record_state')=='retracted' for x in rows),'class_counts':{k:sum(x.get('outcome_class')==k for x in rows) for k in sorted(OUTCOME_CLASSES)},'recent_outcomes':[{k:x.get(k) for k in ('outcome_id','outcome_class','outcome_state','origin_type','origin_id_digest','lineage_count','score','feedback_known','record_state','active_influence','created_at')} for x in rows[-24:]],'state_separation':deepcopy(s['state_separation']),'authority_boundary':deepcopy(s['authority_boundary']),'raw_content_exposed':False,'hidden_reasoning_exposed':False,'provider_contacted':False,'external_action_executed':False}
def build_behavioral_outcome_inspection(runtime_root=None): return BehavioralOutcomeStore(runtime_root).inspection_summary()
