from __future__ import annotations
"""Deterministic restraint and timing for non-sending conversation proposals."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable
from initiative_conversation_proposal import InitiativeConversationProposalStore
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from governed_initiative_boundary import decide_surface
CONTRACT_VERSION='v1108.4'
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v,n=500): return ' '.join(str(v or '').split())[:n]
def _digest(*parts): return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in parts).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':'1','contract_version':CONTRACT_VERSION,'decisions':[],'processed_events':[],'revision':0,'updated_at':'','controls':{'quiet':False,'sleeping':False,'paused':False,'cooldown_active':False,'max_sensitivity':.75,'min_confidence':.35,'max_decisions':256},'authority_boundary':{'can_send':False,'can_notify':False,'can_browse':False,'can_execute':False,'can_authorize':False,'can_modify_files':False,'can_manage_models':False,'can_approve':False,'can_promote':False,'can_certify':False}}
class InitiativeCommunicationRestraint:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/'initiative_communication_restraint.json'; self.clock=clock or _now; self.proposals=InitiativeConversationProposalStore(self.runtime_root)
 def _load(self):
  state=load_json_file(self.path,_default(),expected_type=dict)
  if state.get('schema_version')!='1': state=_default()
  for k,v in _default().items(): state.setdefault(k,deepcopy(v))
  return state
 def snapshot(self): return deepcopy(self._load())
 def decide(self,event_id,*,proposal_id,user_present=False,user_receptive=False,conversation_active=False,topic_allowed=True,context_current=True,meaningful_change=False,artifact_class='suggestion',novelty=1.0,relevance=1.0):
  event_id=_clean(event_id,180); proposal_id=_clean(proposal_id,180)
  if not event_id or not proposal_id: raise ValueError('event_id and proposal_id required')
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   state=self._load(); prior=next((x for x in state['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,'status':'duplicate_decision_ignored','decision':deepcopy(prior['decision']),'idempotent':True}
   proposal=next((x for x in self.proposals.snapshot().get('proposals',[]) if x.get('proposal_id')==proposal_id),None); controls=state['controls']; outcome='abandon'; reason='proposal_missing'
   boundary=decide_surface(artifact_class=artifact_class,novelty=novelty,relevance=relevance,confidence=float((proposal or {}).get('confidence') or 0),muted=bool(controls.get('quiet') or controls.get('sleeping') or controls.get('paused')),repetitive=bool(controls.get('cooldown_active') and not meaningful_change)).public_summary()
   if proposal and proposal.get('active') and proposal.get('eligible'):
    if controls.get('quiet') or controls.get('sleeping') or controls.get('paused'): outcome,reason='deliberate_silence','control_boundary'
    elif not topic_allowed: outcome,reason='abandon','topic_boundary'
    elif not context_current: outcome,reason='abandon','stale_context'
    elif float(proposal.get('sensitivity') or 0)>float(controls['max_sensitivity']): outcome,reason='defer','sensitivity_boundary'
    elif float(proposal.get('confidence') or 0)<float(controls['min_confidence']): outcome,reason='defer','uncertainty_boundary'
    elif controls.get('cooldown_active') and not meaningful_change: outcome,reason='defer','cooldown_boundary'
    elif not user_present or not user_receptive or not conversation_active: outcome,reason='defer','presence_or_receptivity_boundary'
    elif not boundary.get('surface_eligible'): outcome,reason='defer',str(boundary.get('reason') or 'v1489_boundary')
    else: outcome,reason='eligible_to_surface','normal_chat_surface_only'
   now=self.clock(); did=f'initiative-timing-{_digest(event_id,proposal_id,outcome,reason)[:24]}'; decision={'decision_id':did,'proposal_id':proposal_id,'occurred_at':now,'outcome':outcome,'reason_code':reason,'eligible_for_normal_chat_surface':outcome=='eligible_to_surface','v1489_boundary':boundary,'message_id':'','notification_id':'','provider_contacted':False,'authority_granted':False,'content_free':True}; state['decisions']=(state['decisions']+[decision])[-int(controls['max_decisions']):]; state['processed_events']=(state['processed_events']+[{'event_id':event_id,'decision':deepcopy(decision)}])[-1024:]; state['revision']+=1; state['updated_at']=now; write_json_atomic(self.path,state,expected_type=dict,sort_keys=True); return {'ok':True,'status':outcome,'decision':decision,'idempotent':False}
 def inspection_summary(self):
  state=self._load(); rows=state['decisions']; counts={k:sum(x.get('outcome')==k for x in rows) for k in ('eligible_to_surface','defer','deliberate_silence','abandon')}; return {'ok':True,'contract_version':CONTRACT_VERSION,'revision':state['revision'],'decision_count':len(rows),'outcome_counts':counts,'recent_decisions':deepcopy(rows[-24:]),'controls':deepcopy(state['controls']),'authority_boundary':deepcopy(state['authority_boundary']),'provider_contacted':False,'message_sent':False,'notification_sent':False,'external_action_executed':False,'hidden_reasoning_exposed':False,'private_content_exposed':False,'runtime_mutated':False}
def build_initiative_communication_restraint_inspection(runtime_root=None): return InitiativeCommunicationRestraint(runtime_root).inspection_summary()
