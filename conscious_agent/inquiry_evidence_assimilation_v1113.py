from __future__ import annotations
"""Deterministic provenance validation and bounded evidence assimilation (v1113.7)."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from inquiry_evidence_receipts import InquiryEvidenceReceiptStore
CONTRACT_VERSION='v1113.7'
def _now():return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _digest(*p):return hashlib.sha256('\x1f'.join(str(x or '') for x in p).encode()).hexdigest()
def _root():return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default():return {'schema_version':'1','contract_version':CONTRACT_VERSION,'assimilations':[],'processed_events':[],'revision':0,'updated_at':'','controls':{'minimum_reliability':.35,'minimum_relevance':.35,'contradiction_requires_uncertainty':True},'authority_boundary':{'can_browse':False,'can_contact_provider':False,'can_modify_beliefs':False,'can_resolve_inquiry':False,'can_execute':False}}
class InquiryEvidenceAssimilationStore:
 def __init__(self,runtime_root=None):self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/'inquiry_evidence_assimilations.json';self.receipts=InquiryEvidenceReceiptStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def assimilate(self,event_id,*,receipt_id):
  receipt=next((x for x in self.receipts._load()['receipts'] if x.get('receipt_id')==receipt_id and x.get('state')=='active'),None)
  if not receipt:raise ValueError('active evidence receipt required')
  rel=float(receipt.get('reliability',0));rev=float(receipt.get('relevance',0));con=float(receipt.get('contradiction',0));reasons=[]
  if rel<.35:reasons.append('low_reliability')
  if rev<.35:reasons.append('low_relevance')
  outcome='deferred' if reasons else ('assimilated_with_uncertainty' if con>.4 else 'assimilated')
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,'status':'duplicate_event_ignored','result':deepcopy(prior['result']),'idempotent':True}
   existing=next((x for x in s['assimilations'] if x.get('receipt_id_digest')==_digest(receipt_id)),None)
   if existing:result={'status':'duplicate_assimilation_ignored','assimilation_id':existing['assimilation_id'],'outcome':existing['outcome']}
   else:
    now=_now();aid='inquiry-assimilation-'+_digest(receipt_id,outcome)[:24];row={'assimilation_id':aid,'receipt_id_digest':_digest(receipt_id),'active_inquiry_id':receipt.get('active_inquiry_id'),'evidence_kind':receipt.get('evidence_kind'),'outcome':outcome,'reason_codes':reasons,'reliability':rel,'relevance':rev,'contradiction':con,'uncertainty_preserved':con>.4 or bool(reasons),'belief_changed':False,'inquiry_resolved':False,'created_at':now,'content_free':True};s['assimilations'].append(row);result={'status':'evidence_assimilation_recorded','assimilation_id':aid,'outcome':outcome}
   now=_now();s['processed_events']=(s['processed_events']+[{'event_id':event_id,'event_digest':_digest(event_id),'occurred_at':now,'result':deepcopy(result)}])[-2048:];s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,'status':result['status'],'result':result,'idempotent':False}
 def inspection_summary(self):
  s=self._load();a=s['assimilations'];return {'ok':True,'contract_version':CONTRACT_VERSION,'assimilation_count':len(a),'recent_assimilations':deepcopy(a[-24:]),'controls':deepcopy(s['controls']),'authority_boundary':deepcopy(s['authority_boundary']),'belief_changed':False,'inquiry_resolved':False,'external_browsing_performed':False,'provider_contacted':False,'hidden_reasoning_exposed':False}
def build_inquiry_evidence_assimilation_inspection(runtime_root=None):return InquiryEvidenceAssimilationStore(runtime_root).inspection_summary()
