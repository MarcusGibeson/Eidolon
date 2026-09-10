from __future__ import annotations
"""Operator-reviewed adaptation lifecycle and bounded weight receipts (v1112.7)."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from behavioral_adaptation_proposals import BehavioralAdaptationProposalStore, ALLOWED_STATES
CONTRACT_VERSION='v1112.7'
TRANSITIONS={'pending_operator_review':{'suspended','rejected','retired','approved_for_bounded_apply'},'suspended':{'pending_operator_review','rejected','retired'},'approved_for_bounded_apply':{'rolled_back','retired'},'rejected':{'retired'},'rolled_back':{'retired'},'draft':{'pending_operator_review','retired'}}
def _now():return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v,n=300):return ' '.join(str(v or '').split())[:n]
def _digest(*p):return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root():return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default():return {'schema_version':'1','contract_version':CONTRACT_VERSION,'decisions':[],'weight_receipts':[],'processed_events':[],'revision':0,'updated_at':'','controls':{'explicit_operator_confirmation_required':True,'approval_does_not_authorize':True,'apply_path_not_implemented':True,'maximum_absolute_delta':0.15,'rollback_requires_receipt':True},'authority_boundary':{'can_apply':False,'can_authorize':False,'can_execute':False,'can_modify_prompts':False,'can_modify_source':False,'can_manage_models':False}}
class BehavioralAdaptationLifecycleStore:
 def __init__(self,runtime_root=None):self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/'behavioral_adaptation_lifecycle.json';self.proposals=BehavioralAdaptationProposalStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get('schema_version')!='1':s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def decide(self,event_id,*,proposal_id,new_state,operator_confirmation=False,decision_code=''):
  if new_state not in ALLOWED_STATES:raise ValueError('unsupported state')
  if not operator_confirmation:raise PermissionError('explicit operator confirmation required')
  with metadata_mutation_lock(self.proposals.path,timeout_seconds=5):
   ps=self.proposals._load();proposal=next((x for x in ps['proposals'] if x.get('proposal_id')==proposal_id),None)
   if not proposal:raise ValueError('unknown proposal_id')
   with metadata_mutation_lock(self.path,timeout_seconds=5):
    s=self._load();prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
    if prior:return {'ok':True,'status':'duplicate_event_ignored','result':deepcopy(prior['result']),'idempotent':True}
    current=proposal.get('state');allowed=TRANSITIONS.get(current,set())
    if new_state not in allowed:raise ValueError('invalid lifecycle transition')
    now=_now();did=f'adaptation-decision-{_digest(event_id,proposal_id,new_state)[:24]}';proposal['state']=new_state;proposal['updated_at']=now;proposal['approval_granted']=new_state=='approved_for_bounded_apply';proposal['authorization_granted']=False;proposal['applied']=False
    row={'decision_id':did,'proposal_id_digest':_digest(proposal_id),'from_state':current,'to_state':new_state,'decision_code_digest':_digest(decision_code),'operator_confirmed':True,'occurred_at':now,'content_free':True,'approval_granted':new_state=='approved_for_bounded_apply','authorization_granted':False,'execution_occurred':False}
    s['decisions'].append(row)
    if new_state in {'approved_for_bounded_apply','rolled_back'}:
     s['weight_receipts'].append({'receipt_id':f'weight-receipt-{_digest(did)[:24]}','proposal_id_digest':_digest(proposal_id),'scope_code':proposal.get('scope_code'),'bounded_delta':proposal.get('requested_delta'),'receipt_state':'approved_not_applied' if new_state=='approved_for_bounded_apply' else 'rollback_recorded_no_apply','occurred_at':now,'behavior_mutated':False,'authorization_granted':False,'content_free':True})
    result={'status':'lifecycle_decision_recorded','decision_id':did,'proposal_id':proposal_id,'state':new_state};s['processed_events']=(s['processed_events']+[{'event_id':event_id,'event_digest':_digest(event_id),'occurred_at':now,'result':deepcopy(result),'content_free':True}])[-2048:];s['revision']+=1;s['updated_at']=now;ps['revision']+=1;ps['updated_at']=now;write_json_atomic(self.proposals.path,ps,expected_type=dict,sort_keys=True);write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,'status':result['status'],'result':result,'idempotent':False}
 def inspection_summary(self):
  s=self._load();d=s['decisions'];r=s['weight_receipts'];return {'ok':True,'contract_version':CONTRACT_VERSION,'decision_count':len(d),'weight_receipt_count':len(r),'recent_decisions':[{k:x.get(k) for k in ('decision_id','proposal_id_digest','from_state','to_state','operator_confirmed','approval_granted','authorization_granted','execution_occurred')} for x in d[-24:]],'recent_weight_receipts':[{k:x.get(k) for k in ('receipt_id','proposal_id_digest','scope_code','bounded_delta','receipt_state','behavior_mutated','authorization_granted')} for x in r[-24:]],'controls':deepcopy(s['controls']),'authority_boundary':deepcopy(s['authority_boundary']),'raw_content_exposed':False,'hidden_reasoning_exposed':False,'behavior_changed':False,'authorization_granted':False,'external_action_executed':False}
def build_behavioral_adaptation_lifecycle_inspection(runtime_root=None):return BehavioralAdaptationLifecycleStore(runtime_root).inspection_summary()
