from __future__ import annotations
"""Persistent non-sending conversation proposals derived from selected initiative."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable
from initiative_arbitration import InitiativeArbitrator
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
CONTRACT_VERSION='v1108.3'
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v,n=500): return ' '.join(str(v or '').split())[:n]
def _digest(*parts): return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in parts).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':'1','contract_version':CONTRACT_VERSION,'proposals':[],'processed_events':[],'revision':0,'updated_at':'','controls':{'max_proposals':256,'max_active':24},'state_separation':{'initiative_is_proposal':False,'proposal_is_message':False,'message_is_authorization':False,'authorization_is_execution':False},'authority_boundary':{'can_send':False,'can_browse':False,'can_execute':False,'can_authorize':False,'can_modify_files':False,'can_manage_models':False,'can_approve':False,'can_promote':False,'can_certify':False}}
class InitiativeConversationProposalStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/'initiative_conversation_proposals.json'; self.clock=clock or _now; self.arbitration=InitiativeArbitrator(self.runtime_root)
 def _load(self):
  state=load_json_file(self.path,_default(),expected_type=dict)
  if state.get('schema_version')!='1': state=_default()
  for k,v in _default().items(): state.setdefault(k,deepcopy(v))
  return state
 def snapshot(self): return deepcopy(self._load())
 def form(self,event_id,*,selection_receipt_id,audience='current_user',conversation_context_digest='',sensitivity=.25,confidence=.5,eligible=True):
  event_id=_clean(event_id,180); selection_receipt_id=_clean(selection_receipt_id,180)
  if not event_id or not selection_receipt_id: raise ValueError('event_id and selection_receipt_id required')
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   state=self._load(); prior=next((x for x in state['processed_events'] if x.get('event_id')==event_id),None)
   if prior: return {'ok':True,'status':'duplicate_event_ignored','result':deepcopy(prior['result']),'idempotent':True}
   receipt=next((x for x in self.arbitration.snapshot().get('receipts',[]) if x.get('receipt_id')==selection_receipt_id),None)
   if not receipt or receipt.get('decision')!='selected': result={'status':'proposal_not_formed','reason':'selected_initiative_missing','proposal_id':''}
   elif sum(x.get('active') is True for x in state['proposals'])>=int(state['controls']['max_active']): result={'status':'proposal_not_formed','reason':'active_proposal_limit','proposal_id':''}
   else:
    key=_digest(selection_receipt_id,audience,conversation_context_digest); existing=next((x for x in state['proposals'] if x.get('proposal_key')==key),None)
    if existing: result={'status':'duplicate_proposal_ignored','proposal_id':existing['proposal_id']}
    else:
     now=self.clock(); pid=f'conversation-proposal-{key[:24]}'; row={'proposal_id':pid,'proposal_key':key,'selection_receipt_id':selection_receipt_id,'initiative_candidate_id':receipt.get('selected_candidate_id',''),'intention_id':receipt.get('intention_id',''),'subject_digest':receipt.get('subject_digest',''),'audience_digest':_digest(audience),'conversation_context_digest':_clean(conversation_context_digest,128),'sensitivity':round(max(0,min(1,float(sensitivity))),4),'confidence':round(max(0,min(1,float(confidence))),4),'eligible':bool(eligible),'active':True,'state':'draft_candidate','created_at':now,'updated_at':now,'surface_decision_id':'','message_id':'','provider_contacted':False,'authority_granted':False,'content_free':True}; state['proposals']=(state['proposals']+[row])[-int(state['controls']['max_proposals']):]; result={'status':'conversation_proposal_formed','proposal_id':pid}
   now=self.clock(); state['processed_events']=(state['processed_events']+[{'event_id':event_id,'event_digest':_digest(event_id),'occurred_at':now,'result':deepcopy(result)}])[-1024:]; state['revision']+=1; state['updated_at']=now; write_json_atomic(self.path,state,expected_type=dict,sort_keys=True); return {'ok':True,'status':result['status'],'result':result,'idempotent':False}
 def inspection_summary(self):
  state=self._load(); rows=state['proposals']; return {'ok':True,'contract_version':CONTRACT_VERSION,'revision':state['revision'],'proposal_count':len(rows),'active_proposal_count':sum(x.get('active') is True for x in rows),'eligible_proposal_count':sum(x.get('active') is True and x.get('eligible') is True for x in rows),'recent_proposals':[{k:x.get(k) for k in ('proposal_id','selection_receipt_id','initiative_candidate_id','intention_id','subject_digest','audience_digest','conversation_context_digest','sensitivity','confidence','eligible','active','state','surface_decision_id','message_id')} for x in rows[-24:]],'controls':deepcopy(state['controls']),'state_separation':deepcopy(state['state_separation']),'authority_boundary':deepcopy(state['authority_boundary']),'provider_contacted':False,'message_sent':False,'external_action_executed':False,'hidden_reasoning_exposed':False,'private_content_exposed':False,'runtime_mutated':False}
def build_initiative_conversation_proposal_inspection(runtime_root=None): return InitiativeConversationProposalStore(runtime_root).inspection_summary()
