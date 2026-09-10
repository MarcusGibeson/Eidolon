from __future__ import annotations
"""v1131.0 durable content-free read-only perception signals."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
CONTRACT_VERSION='v1131.0'; SCHEMA_VERSION='1'
CATEGORIES={'project_state','system_event','completed_work','failure','changed_file'}
STATES={'active','suppressed','deferred','awaiting_prerequisite','requires_operator_review','superseded','retracted','stale','retired'}
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v:Any,n=240): return ' '.join(str(v or '').split())[:n]
def _digest(*p:Any): return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'signals':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{'can_read_raw_file_content':False,'can_browse':False,'can_contact_provider':False,'can_execute':False,'can_modify_files':False,'can_send_message':False,'can_create_notification':False,'can_approve':False,'can_authorize':False,'can_promote':False,'can_certify':False}}
class ReadOnlyPerceptionSignalStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/'read_only_perception_signals.json'; self.clock=clock or _now
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id:str,*,origin_ids:list[str],category:str,project_id:str='',conversation_id:str='',event_class:str='',status_class:str='',changed_path_digest:str='',change_kind:str='',occurred_at:str='',importance:float=.5,uncertainty:float=.5,sensitivity:float=.0,cognitive_cost:float=.2,recovery_compatible:bool=True,prerequisite_ids:list[str]|None=None,operator_review_required:bool=False,novelty_only:bool=False,structural_digest:str=''):
  event_id=_clean(event_id,180); origins=list(dict.fromkeys(_clean(x,220) for x in origin_ids if _clean(x,220))); category=_clean(category,64); prereqs=list(dict.fromkeys(_clean(x,220) for x in (prerequisite_ids or []) if _clean(x,220)))
  if not event_id or not origins or category not in CATEGORIES: raise ValueError('complete structural perception lineage required')
  clamp=lambda x:round(max(0.0,min(float(x),1.0)),4)
  importance,uncertainty,sensitivity,cognitive_cost=[clamp(x) for x in (importance,uncertainty,sensitivity,cognitive_cost)]
  semantic=_digest(*sorted(origins),category,project_id,conversation_id,event_class,status_class,changed_path_digest,change_kind,structural_digest)
  state='requires_operator_review' if operator_review_required else ('suppressed' if novelty_only or importance<.2 else ('awaiting_prerequisite' if prereqs else ('deferred' if not recovery_compatible or cognitive_cost>.9 else 'active')))
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,'status':'duplicate_event_ignored','result':deepcopy(prior['result']),'idempotent':True}
   dup=next((x for x in s['signals'] if x.get('semantic_key')==semantic and x.get('state') in {'active','deferred','awaiting_prerequisite','requires_operator_review'}),None)
   if dup: result={'status':'duplicate_signal_ignored','signal_id':dup['signal_id']}
   else:
    now=self.clock(); sid=f'perception-signal-{semantic[:24]}'; row={'signal_id':sid,'semantic_key':semantic,'origin_ids':origins,'category':category,'project_id':_clean(project_id,160),'conversation_id':_clean(conversation_id,160),'event_class':_clean(event_class,80),'status_class':_clean(status_class,80),'changed_path_digest':_clean(changed_path_digest,128),'change_kind':_clean(change_kind,64),'occurred_at':_clean(occurred_at,64),'importance':importance,'uncertainty':uncertainty,'sensitivity':sensitivity,'cognitive_cost':cognitive_cost,'recovery_compatible':bool(recovery_compatible),'prerequisite_ids':prereqs,'operator_review_required':bool(operator_review_required),'novelty_only':bool(novelty_only),'structural_digest':_clean(structural_digest,128),'state':state,'created_at':now,'updated_at':now,'history':[{'change':'registered','occurred_at':now,'content_free':True}],'perception_candidate_id':'','inquiry_candidate_id':'','message_id':'','notification_id':'','approval_id':'','authorization_id':'','action_id':''}; s['signals'].append(row); result={'status':'perception_signal_registered','signal_id':sid,'state':state}
   now=self.clock(); s['processed_events'].append({'event_id':event_id,'event_digest':_digest(event_id),'occurred_at':now,'result':deepcopy(result),'content_free':True}); s['revision']+=1; s['updated_at']=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {'ok':True,'status':result['status'],'result':result,'idempotent':False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s['signals']: counts[x.get('state')]=counts.get(x.get('state'),0)+1
  keys=('signal_id','origin_ids','category','project_id','conversation_id','event_class','status_class','changed_path_digest','change_kind','occurred_at','importance','uncertainty','sensitivity','cognitive_cost','recovery_compatible','prerequisite_ids','operator_review_required','novelty_only','structural_digest','state','perception_candidate_id','inquiry_candidate_id','message_id','notification_id','approval_id','authorization_id','action_id')
  return {'ok':True,'contract_version':CONTRACT_VERSION,'signal_count':len(s['signals']),'state_counts':counts,'recent_signals':[{k:x.get(k) for k in keys} for x in s['signals'][-24:]],'authority_boundary':deepcopy(s['authority_boundary']),'raw_file_content_exposed':False,'raw_event_payload_exposed':False,'message_text_exposed':False,'hidden_reasoning_exposed':False,'filesystem_modified':False,'browser_contacted':False,'provider_contacted':False,'external_action_executed':False}
def build_read_only_perception_signal_inspection(runtime_root=None): return ReadOnlyPerceptionSignalStore(runtime_root).inspection_summary()
