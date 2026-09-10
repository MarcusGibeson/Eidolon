from __future__ import annotations
"""Non-authorizing evidence-acquisition proposals for active inquiries (v1113.3)."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from active_inquiry_records import ActiveInquiryStore
CONTRACT_VERSION='v1113.3'
ALLOWED_SOURCE_CLASSES={'existing_structural_records','operator_supplied_evidence','approved_local_knowledge','approved_provider_path','approved_browsing_path'}
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v,n=300): return ' '.join(str(v or '').split())[:n]
def _digest(*p): return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':'1','contract_version':CONTRACT_VERSION,'proposals':[],'processed_events':[],'revision':0,'updated_at':'','controls':{'operator_review_required':True,'automatic_browsing':False,'automatic_provider_contact':False,'automatic_user_prompt':False,'max_active_proposals':64},'state_separation':{'active_inquiry_is_proposal':False,'proposal_is_approval':False,'approval_is_authorization':False,'authorization_is_acquisition':False,'acquisition_is_verified_evidence':False},'authority_boundary':{'can_browse':False,'can_contact_provider':False,'can_ask_user':False,'can_authorize':False,'can_execute':False,'can_modify_files':False}}
class InquiryEvidenceAcquisitionProposalStore:
 def __init__(self,runtime_root=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/'inquiry_evidence_acquisition_proposals.json'; self.inquiries=ActiveInquiryStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get('schema_version')!='1': s=_default()
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def propose(self,event_id,*,active_inquiry_id,source_class,scope_digest='',resource_cost=.25,sensitivity=.25,reason_code=''):
  if source_class not in ALLOWED_SOURCE_CLASSES: raise ValueError('unsupported source_class')
  inquiry=next((x for x in self.inquiries.snapshot()['records'] if x.get('active_inquiry_id')==active_inquiry_id),None)
  if not inquiry or inquiry.get('state')!='active_internal': raise ValueError('active inquiry required')
  cost=round(max(0,min(float(resource_cost),1)),4); sens=round(max(0,min(float(sensitivity),1)),4)
  reasons=[]
  if cost>inquiry.get('resource_budget',0): reasons.append('resource_budget_exceeded')
  if sens>inquiry.get('sensitivity',1): reasons.append('sensitivity_exceeded')
  state='suspended' if reasons else 'pending_operator_review'
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,'status':'duplicate_event_ignored','result':deepcopy(prior['result']),'idempotent':True}
   key=_digest(active_inquiry_id,source_class,scope_digest,reason_code); existing=next((x for x in s['proposals'] if x.get('semantic_key')==key),None)
   if existing: result={'status':'duplicate_proposal_ignored','proposal_id':existing['proposal_id'],'state':existing['state']}
   else:
    now=_now(); pid=f'inquiry-evidence-proposal-{key[:24]}'; row={'proposal_id':pid,'semantic_key':key,'active_inquiry_id':active_inquiry_id,'inquiry_candidate_id':inquiry.get('inquiry_candidate_id',''),'source_class':source_class,'scope_digest':_clean(scope_digest,64),'resource_cost':cost,'sensitivity':sens,'state':state,'reason_codes':reasons,'reason_code_digest':_digest(reason_code),'operator_review_required':True,'approval_id':'','authorization_id':'','acquisition_receipt_id':'','browse_receipt_id':'','provider_receipt_id':'','user_prompt_id':'','action_id':'','created_at':now,'updated_at':now,'content_free':True}; s['proposals'].append(row); result={'status':'proposal_recorded','proposal_id':pid,'state':state}
   now=_now(); s['processed_events']=(s['processed_events']+[{'event_id':event_id,'event_digest':_digest(event_id),'occurred_at':now,'result':deepcopy(result),'content_free':True}])[-2048:]; s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,'status':result['status'],'result':result,'idempotent':False}
 def inspection_summary(self):
  s=self._load();p=s['proposals'];return {'ok':True,'contract_version':CONTRACT_VERSION,'proposal_count':len(p),'pending_review_count':sum(x.get('state')=='pending_operator_review' for x in p),'suspended_count':sum(x.get('state')=='suspended' for x in p),'recent_proposals':[{k:x.get(k) for k in ('proposal_id','active_inquiry_id','inquiry_candidate_id','source_class','scope_digest','resource_cost','sensitivity','state','reason_codes','operator_review_required','approval_id','authorization_id','acquisition_receipt_id','browse_receipt_id','provider_receipt_id','user_prompt_id','action_id')} for x in p[-24:]],'controls':deepcopy(s['controls']),'state_separation':deepcopy(s['state_separation']),'authority_boundary':deepcopy(s['authority_boundary']),'provider_contacted':False,'external_browsing_performed':False,'message_sent':False,'runtime_mutated':False,'hidden_reasoning_exposed':False,'private_content_exposed':False}
def build_inquiry_evidence_acquisition_proposal_inspection(runtime_root=None): return InquiryEvidenceAcquisitionProposalStore(runtime_root).inspection_summary()
