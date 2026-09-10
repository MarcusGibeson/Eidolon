from __future__ import annotations
"""Privacy-safe governed evidence receipts for active inquiries (v1113.6)."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from active_inquiry_records import ActiveInquiryStore
CONTRACT_VERSION='v1113.6'
ALLOWED_KINDS={'existing_structural_record','operator_supplied_evidence','approved_local_knowledge','approved_provider_result','approved_browsing_result'}
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v,n=300): return ' '.join(str(v or '').split())[:n]
def _digest(*p): return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':'1','contract_version':CONTRACT_VERSION,'receipts':[],'processed_events':[],'revision':0,'updated_at':'','controls':{'raw_content_forbidden':True,'approved_path_receipt_required':True,'max_receipts':512},'authority_boundary':{'can_browse':False,'can_contact_provider':False,'can_ask_user':False,'can_authorize':False,'can_execute':False}}
class InquiryEvidenceReceiptStore:
 def __init__(self,runtime_root=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/'inquiry_evidence_receipts.json';self.inquiries=ActiveInquiryStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def record(self,event_id,*,active_inquiry_id,evidence_kind,source_digest,evidence_digest,authorization_receipt_id='',reliability=.5,relevance=.5,contradiction=.0):
  if evidence_kind not in ALLOWED_KINDS: raise ValueError('unsupported evidence_kind')
  inquiry=next((x for x in self.inquiries.snapshot()['records'] if x.get('active_inquiry_id')==active_inquiry_id),None)
  if not inquiry or inquiry.get('state') not in {'active_internal','awaiting_natural_evidence'}: raise ValueError('eligible inquiry required')
  if evidence_kind in {'approved_provider_result','approved_browsing_result'} and not _clean(authorization_receipt_id,180): raise ValueError('authorization receipt required')
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,'status':'duplicate_event_ignored','result':deepcopy(prior['result']),'idempotent':True}
   key=_digest(active_inquiry_id,evidence_kind,source_digest,evidence_digest);existing=next((x for x in s['receipts'] if x.get('semantic_key')==key),None)
   if existing: result={'status':'duplicate_evidence_ignored','receipt_id':existing['receipt_id']}
   else:
    now=_now();rid='inquiry-evidence-'+key[:24];row={'receipt_id':rid,'semantic_key':key,'active_inquiry_id':active_inquiry_id,'inquiry_candidate_id':inquiry.get('inquiry_candidate_id',''),'evidence_kind':evidence_kind,'source_digest':_clean(source_digest,64),'evidence_digest':_clean(evidence_digest,64),'authorization_receipt_digest':_digest(authorization_receipt_id) if authorization_receipt_id else '','reliability':round(max(0,min(float(reliability),1)),4),'relevance':round(max(0,min(float(relevance),1)),4),'contradiction':round(max(0,min(float(contradiction),1)),4),'state':'active','corrected_by':'','retracted_at':'','created_at':now,'content_free':True,'raw_content_stored':False};s['receipts']=(s['receipts']+[row])[-512:];result={'status':'evidence_receipt_recorded','receipt_id':rid}
   now=_now();s['processed_events']=(s['processed_events']+[{'event_id':event_id,'event_digest':_digest(event_id),'occurred_at':now,'result':deepcopy(result)}])[-2048:];s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,'status':result['status'],'result':result,'idempotent':False}
 def inspection_summary(self):
  s=self._load();r=s['receipts'];return {'ok':True,'contract_version':CONTRACT_VERSION,'receipt_count':len(r),'active_count':sum(x.get('state')=='active' for x in r),'recent_receipts':[{k:x.get(k) for k in ('receipt_id','active_inquiry_id','inquiry_candidate_id','evidence_kind','source_digest','evidence_digest','authorization_receipt_digest','reliability','relevance','contradiction','state','corrected_by','raw_content_stored')} for x in r[-24:]],'controls':deepcopy(s['controls']),'authority_boundary':deepcopy(s['authority_boundary']),'external_browsing_performed':False,'provider_contacted':False,'private_content_exposed':False,'hidden_reasoning_exposed':False}
def build_inquiry_evidence_receipt_inspection(runtime_root=None):return InquiryEvidenceReceiptStore(runtime_root).inspection_summary()
