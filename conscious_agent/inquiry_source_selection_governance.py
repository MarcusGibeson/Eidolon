from __future__ import annotations
"""Operator-reviewed source-selection governance (v1113.4)."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from inquiry_evidence_acquisition_proposals import InquiryEvidenceAcquisitionProposalStore
CONTRACT_VERSION='v1113.4'
TRANSITIONS={'pending_operator_review':{'approved_for_authorization_review','suspended','rejected','retired'},'suspended':{'pending_operator_review','rejected','retired'},'approved_for_authorization_review':{'suspended','retired'},'rejected':{'retired'}}
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v,n=300): return ' '.join(str(v or '').split())[:n]
def _digest(*p): return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':'1','contract_version':CONTRACT_VERSION,'decisions':[],'processed_events':[],'revision':0,'updated_at':'','controls':{'explicit_operator_confirmation_required':True,'approval_does_not_authorize':True,'authorization_path_external':True,'automatic_acquisition':False},'authority_boundary':{'can_browse':False,'can_contact_provider':False,'can_ask_user':False,'can_authorize':False,'can_execute':False}}
class InquirySourceSelectionGovernanceStore:
 def __init__(self,runtime_root=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/'inquiry_source_selection_governance.json';self.proposals=InquiryEvidenceAcquisitionProposalStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get('schema_version')!='1':s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def decide(self,event_id,*,proposal_id,new_state,operator_confirmation=False,decision_code=''):
  if not operator_confirmation:raise PermissionError('explicit operator confirmation required')
  with metadata_mutation_lock(self.proposals.path,timeout_seconds=5):
   ps=self.proposals._load();proposal=next((x for x in ps['proposals'] if x.get('proposal_id')==proposal_id),None)
   if not proposal:raise ValueError('unknown proposal_id')
   with metadata_mutation_lock(self.path,timeout_seconds=5):
    s=self._load();prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
    if prior:return {'ok':True,'status':'duplicate_event_ignored','result':deepcopy(prior['result']),'idempotent':True}
    current=proposal.get('state')
    if new_state not in TRANSITIONS.get(current,set()):raise ValueError('invalid lifecycle transition')
    now=_now();did=f'inquiry-source-decision-{_digest(event_id,proposal_id,new_state)[:24]}';proposal['state']=new_state;proposal['updated_at']=now;proposal['approval_id']=did if new_state=='approved_for_authorization_review' else ''
    row={'decision_id':did,'proposal_id_digest':_digest(proposal_id),'source_class':proposal.get('source_class'),'from_state':current,'to_state':new_state,'decision_code_digest':_digest(decision_code),'operator_confirmed':True,'approval_recorded':new_state=='approved_for_authorization_review','authorization_granted':False,'acquisition_performed':False,'occurred_at':now,'content_free':True};s['decisions'].append(row)
    result={'status':'source_selection_decision_recorded','decision_id':did,'proposal_id':proposal_id,'state':new_state};s['processed_events']=(s['processed_events']+[{'event_id':event_id,'event_digest':_digest(event_id),'occurred_at':now,'result':deepcopy(result),'content_free':True}])[-2048:];s['revision']+=1;s['updated_at']=now;ps['revision']+=1;ps['updated_at']=now;write_json_atomic(self.proposals.path,ps,expected_type=dict,sort_keys=True);write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,'status':result['status'],'result':result,'idempotent':False}
 def inspection_summary(self):
  s=self._load();d=s['decisions'];return {'ok':True,'contract_version':CONTRACT_VERSION,'decision_count':len(d),'recent_decisions':[{k:x.get(k) for k in ('decision_id','proposal_id_digest','source_class','from_state','to_state','operator_confirmed','approval_recorded','authorization_granted','acquisition_performed')} for x in d[-24:]],'controls':deepcopy(s['controls']),'authority_boundary':deepcopy(s['authority_boundary']),'provider_contacted':False,'external_browsing_performed':False,'message_sent':False,'runtime_mutated':False,'hidden_reasoning_exposed':False,'private_content_exposed':False,'authorization_granted':False,'external_action_executed':False}
def build_inquiry_source_selection_governance_inspection(runtime_root=None):return InquirySourceSelectionGovernanceStore(runtime_root).inspection_summary()
