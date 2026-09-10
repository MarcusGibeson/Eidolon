from __future__ import annotations

"""v2504.3 content-bounded continuity for unfinished cognitive operations."""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import re
from pathlib import Path
from typing import Any, Callable, Mapping

from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock

CONTRACT_VERSION='v2504.3';SCHEMA_VERSION='1'

def _now():return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v,n=300):return ' '.join(str(v or '').split())[:n]
def _digest(*p):return hashlib.sha256('\x1f'.join(_clean(x,2000) for x in p).encode()).hexdigest()
def _ref(v):
 r=_clean(v,220)
 return r if re.fullmatch(r'[A-Za-z0-9._:/#-]{1,220}',r or '') else ('subject-digest:'+hashlib.sha256(r.encode()).hexdigest()[:32] if r else '')
def _default():return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'thoughts':[],'processed_events':[],'revision':0,'updated_at':'','controls':{'max_active':32,'max_history':128},'authority_boundary':{'can_authorize_action':False,'can_execute_action':False,'can_contact_provider':False,'can_send_message':False,'operator_authority_unchanged':True}}

class CognitiveThoughtContinuityStore:
 def __init__(self,runtime_root:str|Path,*,clock:Callable[[],str]|None=None):
  self.root=Path(runtime_root).expanduser().resolve();self.path=self.root/'unified_cognitive_thought_continuity.json';self.clock=clock or _now
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get('schema_version')!=SCHEMA_VERSION:s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self):return deepcopy(self._load())
 def record(self,event_id:str,*,operation:str,subject_ref:str,frame_digest:str,status:str='unfinished',progress_marker:str='',evidence_digests:list[str]|None=None,next_step:str=''):
  event_id=_clean(event_id,180);operation=_clean(operation,60).upper();subject_ref=_ref(subject_ref);frame_digest=_clean(frame_digest,64);status=_clean(status,40).lower()
  if not event_id or not operation or not subject_ref or len(frame_digest)!=64:raise ValueError('event_id, operation, subject_ref, and frame_digest required')
  if status not in {'unfinished','completed','abandoned','superseded'}:raise ValueError('invalid thought status')
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,'status':'duplicate_event_ignored','result':deepcopy(prior['result']),'idempotent':True}
   key=_digest(operation,subject_ref);existing=next((x for x in reversed(s['thoughts']) if x.get('semantic_key')==key and x.get('status')=='unfinished'),None)
   now=self.clock();digests=sorted({_clean(x,64) for x in (evidence_digests or []) if len(_clean(x,64))==64})[:24]
   if existing:
    row=existing;row.update({'frame_digest':frame_digest,'status':status,'progress_marker':_clean(progress_marker,240),'next_step':_clean(next_step,240),'evidence_digests':digests,'updated_at':now});row['revision']=int(row.get('revision') or 1)+1
    result={'status':'thought_updated','thought_id':row['thought_id'],'thought_status':status}
   else:
    tid='cognitive-thought-'+key[:24];row={'thought_id':tid,'semantic_key':key,'operation':operation,'subject_ref':subject_ref,'frame_digest':frame_digest,'status':status,'progress_marker':_clean(progress_marker,240),'next_step':_clean(next_step,240),'evidence_digests':digests,'created_at':now,'updated_at':now,'revision':1,'raw_chain_of_thought_stored':False};s['thoughts'].append(row);s['thoughts']=s['thoughts'][-int(s['controls']['max_history']):];result={'status':'thought_recorded','thought_id':tid,'thought_status':status}
   s['processed_events']=(s['processed_events']+[{'event_id':event_id,'event_digest':_digest(event_id),'occurred_at':now,'result':deepcopy(result),'content_free':True}])[-512:];s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,**result,'idempotent':False}
 def inspection_summary(self):
  s=self._load();active=[x for x in s['thoughts'] if x.get('status')=='unfinished'];keys=('thought_id','operation','subject_ref','frame_digest','status','progress_marker','next_step','evidence_digests','updated_at','revision','raw_chain_of_thought_stored')
  return {'ok':True,'contract_version':CONTRACT_VERSION,'revision':s['revision'],'active_count':len(active),'history_count':len(s['thoughts']),'active_thoughts':[{k:x.get(k) for k in keys} for x in active[-int(s['controls']['max_active']):]],'authority_boundary':deepcopy(s['authority_boundary']),'provider_contacted':False,'message_sent':False,'external_action_executed':False,'hidden_reasoning_exposed':False,'raw_chain_of_thought_stored':False}

def build_cognitive_thought_continuity_inspection(runtime_root:str|Path):return CognitiveThoughtContinuityStore(runtime_root).inspection_summary()
