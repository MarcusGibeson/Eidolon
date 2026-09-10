from __future__ import annotations
"""v2504.5 operator-readable structural receipts for unified cognitive cycles."""
from copy import deepcopy
from datetime import datetime,timezone
import hashlib
from pathlib import Path
from typing import Any,Callable,Mapping
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
CONTRACT_VERSION='v2504.5';SCHEMA_VERSION='1'
def _now():return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v,n=260):return ' '.join(str(v or '').split())[:n]
def _digest(*p):return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in p).encode()).hexdigest()
def _default():return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'receipts':[],'processed_events':[],'revision':0,'updated_at':'','controls':{'max_receipts':1024},'authority_boundary':{'receipt_can_authorize_action':False,'receipt_can_execute_action':False,'receipt_can_contact_provider':False,'receipt_can_send_message':False}}
class CognitiveCycleReceiptStore:
 def __init__(self,runtime_root:str|Path,*,clock:Callable[[],str]|None=None):self.root=Path(runtime_root).expanduser().resolve();self.path=self.root/'unified_cognitive_cycle_receipts.json';self.clock=clock or _now
 def append(self,event_id:str,receipt:Mapping[str,Any]):
  event_id=_clean(event_id,180)
  if not event_id or not isinstance(receipt,Mapping):raise ValueError('event_id and receipt required')
  cycle_id=_clean(receipt.get('cycle_id'),220);frame_digest=_clean(receipt.get('frame_digest'),64);operation=_clean(receipt.get('selected_operation'),60).upper();status=_clean(receipt.get('status'),80)
  if not cycle_id or len(frame_digest)!=64 or not operation or not status:raise ValueError('incomplete cognitive receipt')
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,'status':'duplicate_event_ignored','receipt_id':prior['receipt_id'],'idempotent':True}
   now=self.clock();rid='cognitive-receipt-'+_digest(cycle_id,frame_digest,operation,status,receipt.get('outcome_id',''))[:24]
   row={'receipt_id':rid,'cycle_id':cycle_id,'trigger_type':_clean(receipt.get('trigger_type'),80),'frame_digest':frame_digest,'selected_operation':operation,'selected_utility':round(max(0.0,min(float(receipt.get('selected_utility') or 0),1.0)),4),'status':status,'subject_ref':_clean(receipt.get('subject_ref'),220),'outcome_type':_clean(receipt.get('outcome_type'),80),'outcome_id':_clean(receipt.get('outcome_id'),220),'durable_targets':sorted({_clean(x,60) for x in receipt.get('durable_targets',[]) if _clean(x,60)})[:12],'communication':'none','provider_contacted':False,'external_action_executed':False,'authority_broadened':False,'hidden_reasoning_exposed':False,'created_at':now}
   s['receipts']=(s['receipts']+[row])[-int(s['controls']['max_receipts']):];s['processed_events']=(s['processed_events']+[{'event_id':event_id,'event_digest':_digest(event_id),'receipt_id':rid,'occurred_at':now,'content_free':True}])[-2048:];s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,'status':'receipt_recorded','receipt_id':rid,'idempotent':False}
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get('schema_version')!=SCHEMA_VERSION:s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def inspection_summary(self):
  s=self._load();return {'ok':True,'contract_version':CONTRACT_VERSION,'revision':s['revision'],'receipt_count':len(s['receipts']),'recent_receipts':deepcopy(s['receipts'][-32:]),'authority_boundary':deepcopy(s['authority_boundary']),'provider_contacted':False,'message_sent':False,'external_action_executed':False,'hidden_reasoning_exposed':False}
def build_cognitive_cycle_receipt_inspection(runtime_root:str|Path):return CognitiveCycleReceiptStore(runtime_root).inspection_summary()
