from __future__ import annotations
"""v1131.1 governed read-only perception candidates."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from read_only_perception_signals import ReadOnlyPerceptionSignalStore
CONTRACT_VERSION='v1131.1'; SCHEMA_VERSION='1'
STATES={'active','suppressed','deferred','awaiting_prerequisite','requires_operator_review','merged','superseded','stale','obsolete','retracted','retired'}
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v:Any,n=240): return ' '.join(str(v or '').split())[:n]
def _digest(*p:Any): return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'candidates':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{'can_read_raw_file_content':False,'can_browse':False,'can_contact_provider':False,'can_execute':False,'can_modify_files':False,'can_send_message':False,'can_create_notification':False,'can_approve':False,'can_authorize':False,'can_promote':False,'can_certify':False}}
class ReadOnlyPerceptionCandidateStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/'read_only_perception_candidates.json'; self.signals=ReadOnlyPerceptionSignalStore(self.runtime_root); self.clock=clock or _now
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id:str,*,signal_ids:list[str],perception_purpose:str='structural_review',scope_digest:str='',semantic_overlap_key:str='',prerequisite_ids:list[str]|None=None,operator_review_required:bool=False):
  event_id=_clean(event_id,180); ids=list(dict.fromkeys(_clean(x,220) for x in signal_ids if _clean(x,220))); prereqs=list(dict.fromkeys(_clean(x,220) for x in (prerequisite_ids or []) if _clean(x,220))); known={x.get('signal_id'):x for x in self.signals.snapshot().get('signals',[])}
  if not event_id or not ids or any(i not in known for i in ids): raise ValueError('known perception signal lineage required')
  rows=[known[i] for i in ids]; categories=sorted({x.get('category') for x in rows}); semantic=_digest(*sorted(ids),perception_purpose,scope_digest,semantic_overlap_key)
  weak=all(x.get('state')=='suppressed' for x in rows); review=operator_review_required or any(x.get('operator_review_required') for x in rows); recovery=all(x.get('recovery_compatible') for x in rows)
  state='requires_operator_review' if review else ('suppressed' if weak else ('awaiting_prerequisite' if prereqs else ('deferred' if not recovery else 'active')))
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,'status':'duplicate_event_ignored','result':deepcopy(prior['result']),'idempotent':True}
   dup=next((x for x in s['candidates'] if x.get('semantic_key')==semantic and x.get('state') in {'active','deferred','awaiting_prerequisite','requires_operator_review'}),None)
   if dup: result={'status':'duplicate_candidate_ignored','candidate_id':dup['candidate_id']}
   else:
    now=self.clock(); cid=f'perception-candidate-{semantic[:24]}'; row={'candidate_id':cid,'semantic_key':semantic,'signal_ids':ids,'categories':categories,'perception_purpose':_clean(perception_purpose,80),'scope_digest':_clean(scope_digest,128),'semantic_overlap_key':_clean(semantic_overlap_key,128),'importance':max(x.get('importance',0) for x in rows),'uncertainty':max(x.get('uncertainty',0) for x in rows),'sensitivity':max(x.get('sensitivity',0) for x in rows),'cognitive_cost':max(x.get('cognitive_cost',0) for x in rows),'recovery_compatible':recovery,'prerequisite_ids':prereqs,'operator_review_required':review,'state':state,'created_at':now,'updated_at':now,'history':[{'change':'registered','occurred_at':now,'content_free':True}],'perception_session_id':'','perception_outcome_id':'','inquiry_candidate_id':'','message_id':'','notification_id':'','approval_id':'','authorization_id':'','action_id':''}; s['candidates'].append(row); result={'status':'perception_candidate_registered','candidate_id':cid,'state':state}
   now=self.clock(); s['processed_events'].append({'event_id':event_id,'event_digest':_digest(event_id),'occurred_at':now,'result':deepcopy(result),'content_free':True}); s['revision']+=1; s['updated_at']=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {'ok':True,'status':result['status'],'result':result,'idempotent':False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s['candidates']: counts[x.get('state')]=counts.get(x.get('state'),0)+1
  keys=('candidate_id','signal_ids','categories','perception_purpose','scope_digest','semantic_overlap_key','importance','uncertainty','sensitivity','cognitive_cost','recovery_compatible','prerequisite_ids','operator_review_required','state','perception_session_id','perception_outcome_id','inquiry_candidate_id','message_id','notification_id','approval_id','authorization_id','action_id')
  return {'ok':True,'contract_version':CONTRACT_VERSION,'candidate_count':len(s['candidates']),'state_counts':counts,'recent_candidates':[{k:x.get(k) for k in keys} for x in s['candidates'][-24:]],'authority_boundary':deepcopy(s['authority_boundary']),'raw_file_content_exposed':False,'raw_event_payload_exposed':False,'hidden_reasoning_exposed':False,'filesystem_modified':False,'browser_contacted':False,'provider_contacted':False,'external_action_executed':False}
def build_read_only_perception_candidate_inspection(runtime_root=None): return ReadOnlyPerceptionCandidateStore(runtime_root).inspection_summary()
