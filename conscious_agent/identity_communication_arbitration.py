from __future__ import annotations
"""Deterministic identity-consistency review for non-sending communication proposals."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable, Iterable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from persistent_identity_model import PersistentIdentityModelStore
CONTRACT_VERSION='v1110.7'
OUTCOMES={'consistent','revise_tone','defer','deliberate_silence','unresolved'}
def _now():return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v,n=500):return ' '.join(str(v or '').split())[:n]
def _digest(*p):return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root():return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default():return {'schema_version':'1','contract_version':CONTRACT_VERSION,'decisions':[],'processed_events':[],'revision':0,'updated_at':'','controls':{'max_decisions':512,'max_claims':6,'minimum_confidence':0.4,'maximum_uncertainty':0.7},'state_separation':{'identity_consistency_is_message':False,'communication_decision_is_delivery':False,'identity_claim_is_intention':False,'decision_is_proposal_authority':False,'proposal_is_authorization':False,'authorization_is_execution':False},'authority_boundary':{'can_browse':False,'can_send':False,'can_execute':False,'can_modify_files':False,'can_manage_models':False,'can_authorize':False,'can_approve':False,'can_promote':False,'can_certify':False}}
class IdentityCommunicationArbitrator:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None):self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/'identity_communication_arbitration.json';self.clock=clock or _now;self.claims=PersistentIdentityModelStore(self.runtime_root,clock=self.clock)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get('schema_version')!='1':s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self):return deepcopy(self._load())
 def arbitrate(self,event_id,*,proposal_ref,claim_ids:Iterable[str],contradiction_count=0,sensitivity=0.0,uncertainty=0.0,quiet=False,paused=False):
  event_id=_clean(event_id,180);proposal=_clean(proposal_ref,220);ids=tuple(dict.fromkeys(_clean(x,180) for x in claim_ids if _clean(x,180)))
  if not event_id or not proposal:raise ValueError('event_id and proposal_ref required')
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,'status':'duplicate_arbitration_event_ignored','result':deepcopy(prior['result']),'idempotent':True}
   rows={x.get('claim_id'):x for x in self.claims.snapshot().get('claims',[])};eligible=[rows[x] for x in ids[:int(s['controls']['max_claims'])] if x in rows and rows[x].get('active_influence') and rows[x].get('eligible')];now=self.clock()
   if quiet or paused:outcome='defer';reason='control_boundary'
   elif float(sensitivity)>=0.8 or float(uncertainty)>=0.8:outcome='deliberate_silence';reason='sensitivity_or_uncertainty'
   elif int(contradiction_count)>0:outcome='revise_tone';reason='identity_contradiction'
   elif not eligible:outcome='unresolved';reason='insufficient_identity_evidence'
   else:outcome='consistent';reason='bounded_consistency'
   key=_digest(proposal,outcome,*[x['claim_id'] for x in eligible]);existing=next((x for x in s['decisions'] if x.get('decision_key')==key),None)
   if existing:result={'status':'duplicate_decision_ignored','decision_id':existing['decision_id'],'outcome':existing['outcome']}
   else:
    did=f'identity-communication-{key[:24]}';row={'decision_id':did,'decision_key':key,'proposal_digest':_digest(proposal),'claim_ids':[x['claim_id'] for x in eligible],'claim_count':len(eligible),'outcome':outcome,'reason_code':reason,'eligible_for_normal_chat_surface':outcome=='consistent','message_id':'','notification_id':'','provider_contacted':False,'message_sent':False,'delivery_triggered':False,'proposal_authority_granted':False,'authorization_id':'','action_id':'','created_at':now,'content_free':True};s['decisions'].append(row);result={'status':'identity_communication_arbitrated','decision_id':did,'outcome':outcome,'eligible_for_normal_chat_surface':row['eligible_for_normal_chat_surface']}
   s['decisions']=s['decisions'][-int(s['controls']['max_decisions']):];s['processed_events']=(s['processed_events']+[{'event_id':event_id,'event_digest':_digest(event_id),'occurred_at':now,'result':deepcopy(result)}])[-1024:];s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,'status':result['status'],'result':result,'idempotent':False}
 def inspection_summary(self):
  s=self._load();counts={}
  for x in s['decisions']:counts[x.get('outcome','unresolved')]=counts.get(x.get('outcome','unresolved'),0)+1
  return {'ok':True,'contract_version':CONTRACT_VERSION,'revision':s['revision'],'decision_count':len(s['decisions']),'outcome_counts':counts,'recent_decisions':deepcopy(s['decisions'][-24:]),'controls':deepcopy(s['controls']),'state_separation':deepcopy(s['state_separation']),'authority_boundary':deepcopy(s['authority_boundary']),'runtime_mutated':False,'provider_contacted':False,'message_sent':False,'external_action_executed':False,'hidden_reasoning_exposed':False,'private_content_exposed':False}
def build_identity_communication_arbitration_inspection(runtime_root=None):return IdentityCommunicationArbitrator(runtime_root).inspection_summary()
