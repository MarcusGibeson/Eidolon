from __future__ import annotations
"""Accountable active inquiry resolution and retirement lifecycle (v1113.8)."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from active_inquiry_records import ActiveInquiryStore
from inquiry_evidence_assimilation_v1113 import InquiryEvidenceAssimilationStore
CONTRACT_VERSION='v1113.8';OUTCOMES={'resolved_supported','resolved_with_uncertainty','unresolved','retired_obsolete','retired_duplicate','suspended'}
def _now():return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _digest(*p):return hashlib.sha256('\x1f'.join(str(x or '') for x in p).encode()).hexdigest()
def _root():return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default():return {'schema_version':'1','contract_version':CONTRACT_VERSION,'resolutions':[],'processed_events':[],'revision':0,'updated_at':'','controls':{'operator_confirmation_required':True,'minimum_assimilated_evidence':1,'unsupported_completion_forbidden':True},'authority_boundary':{'can_browse':False,'can_contact_provider':False,'can_modify_beliefs':False,'can_authorize':False,'can_execute':False}}
class InquiryResolutionLifecycleStore:
 def __init__(self,runtime_root=None):self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/'inquiry_resolution_lifecycle_v1113.json';self.inquiries=ActiveInquiryStore(self.runtime_root);self.assim=InquiryEvidenceAssimilationStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def decide(self,event_id,*,active_inquiry_id,outcome,operator_confirmation=False,residual_question_digest=''):
  if not operator_confirmation:raise PermissionError('operator confirmation required')
  if outcome not in OUTCOMES:raise ValueError('unsupported outcome')
  inquiry=next((x for x in self.inquiries.snapshot()['records'] if x.get('active_inquiry_id')==active_inquiry_id),None)
  if not inquiry:raise ValueError('unknown active inquiry')
  evidence=[x for x in self.assim._load()['assimilations'] if x.get('active_inquiry_id')==active_inquiry_id and x.get('outcome') in {'assimilated','assimilated_with_uncertainty'}]
  if outcome=='resolved_supported' and not any(x.get('outcome')=='assimilated' for x in evidence):raise ValueError('supported evidence required')
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,'status':'duplicate_event_ignored','result':deepcopy(prior['result']),'idempotent':True}
   now=_now();rid='inquiry-resolution-'+_digest(event_id,active_inquiry_id,outcome)[:24];row={'resolution_id':rid,'active_inquiry_id':active_inquiry_id,'inquiry_candidate_id':inquiry.get('inquiry_candidate_id',''),'outcome':outcome,'assimilated_evidence_count':len(evidence),'supporting_assimilation_digests':[_digest(x.get('assimilation_id')) for x in evidence[:16]],'residual_question_digest':str(residual_question_digest or '')[:64],'operator_confirmed':True,'belief_changed':False,'external_action_authorized':False,'created_at':now,'content_free':True};s['resolutions'].append(row);result={'status':'inquiry_resolution_recorded','resolution_id':rid,'outcome':outcome}
   s['processed_events']=(s['processed_events']+[{'event_id':event_id,'event_digest':_digest(event_id),'occurred_at':now,'result':deepcopy(result)}])[-2048:];s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,'status':result['status'],'result':result,'idempotent':False}
 def inspection_summary(self):
  s=self._load();r=s['resolutions'];return {'ok':True,'contract_version':CONTRACT_VERSION,'resolution_count':len(r),'recent_resolutions':deepcopy(r[-24:]),'controls':deepcopy(s['controls']),'authority_boundary':deepcopy(s['authority_boundary']),'belief_changed':False,'authorization_granted':False,'external_action_executed':False,'external_browsing_performed':False,'provider_contacted':False,'hidden_reasoning_exposed':False}
def build_inquiry_resolution_lifecycle_inspection(runtime_root=None):return InquiryResolutionLifecycleStore(runtime_root).inspection_summary()
