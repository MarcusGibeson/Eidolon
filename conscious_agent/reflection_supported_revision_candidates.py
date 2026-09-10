from __future__ import annotations
"""v1128.1 durable accountable revision candidates; candidacy never mutates targets."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from reflection_supported_revision_signals import ReflectionSupportedRevisionSignalStore
CONTRACT_VERSION='v1128.1';SCHEMA_VERSION='1'
STATES={'active','suppressed','deferred','awaiting_prerequisite','requires_operator_review','merged','superseded','retracted','stale','retired'}
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v:Any,n=240): return ' '.join(str(v or '').split())[:n]
def _digest(*p:Any): return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'candidates':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{'can_revise_target':False,'can_apply_revision':False,'can_create_approval':False,'can_authorize':False,'can_execute':False}}
class ReflectionSupportedRevisionCandidateStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/'reflection_supported_revision_candidates.json';self.signals=ReflectionSupportedRevisionSignalStore(self.runtime_root);self.clock=clock or _now
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id:str,*,signal_ids:list[str],revision_kind:str='update',prerequisite_ids:list[str]|None=None,recovery_compatible:bool=True,operator_review_required:bool=False):
  ids=list(dict.fromkeys(_clean(x,220) for x in signal_ids if _clean(x,220))); prereqs=list(dict.fromkeys(_clean(x,220) for x in (prerequisite_ids or []) if _clean(x,220))); event_id=_clean(event_id,180);revision_kind=_clean(revision_kind,40)
  known={x.get('signal_id'):x for x in self.signals.snapshot().get('signals',[])}
  if not event_id or not ids or any(i not in known for i in ids): raise ValueError('known revision signal lineage required')
  targets={(known[i].get('target_type'),known[i].get('target_id')) for i in ids}
  if len(targets)!=1: raise ValueError('candidate signals must share one target')
  target_type,target_id=next(iter(targets)); semantic=_digest(target_type,target_id,revision_kind,*sorted(ids),*sorted(prereqs))
  states={known[i].get('state') for i in ids}; state='requires_operator_review' if operator_review_required or 'requires_operator_review' in states else ('suppressed' if 'suppressed' in states else ('awaiting_prerequisite' if prereqs else ('deferred' if not recovery_compatible else 'active')))
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,'status':'duplicate_event_ignored','result':deepcopy(prior['result']),'idempotent':True}
   dup=next((x for x in s['candidates'] if x.get('semantic_key')==semantic and x.get('state') in {'active','deferred','requires_operator_review','awaiting_prerequisite'}),None)
   if dup:result={'status':'duplicate_candidate_ignored','candidate_id':dup['candidate_id']}
   else:
    now=self.clock();cid=f'revision-candidate-{semantic[:24]}';row={'candidate_id':cid,'semantic_key':semantic,'signal_ids':ids,'target_type':target_type,'target_id':target_id,'revision_kind':revision_kind,'prerequisite_ids':prereqs,'recovery_compatible':bool(recovery_compatible),'operator_review_required':bool(operator_review_required),'state':state,'created_at':now,'updated_at':now,'history':[{'change':'registered','occurred_at':now,'content_free':True}],'revision_session_id':'','revision_outcome_id':'','approval_id':'','authorization_id':'','action_id':''};s['candidates'].append(row);result={'status':'revision_candidate_registered','candidate_id':cid,'state':state}
   now=self.clock();s['processed_events'].append({'event_id':event_id,'event_digest':_digest(event_id),'occurred_at':now,'result':deepcopy(result),'content_free':True});s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,'status':result['status'],'result':result,'idempotent':False}
 def inspection_summary(self):
  s=self._load();counts={}
  for x in s['candidates']:counts[x.get('state')]=counts.get(x.get('state'),0)+1
  keys=('candidate_id','signal_ids','target_type','target_id','revision_kind','prerequisite_ids','recovery_compatible','operator_review_required','state','revision_session_id','revision_outcome_id','approval_id','authorization_id','action_id')
  return {'ok':True,'contract_version':CONTRACT_VERSION,'candidate_count':len(s['candidates']),'state_counts':counts,'recent_candidates':[{k:x.get(k) for k in keys} for x in s['candidates'][-24:]],'authority_boundary':deepcopy(s['authority_boundary']),'raw_content_exposed':False,'conclusion_text_exposed':False,'evidence_text_exposed':False,'hidden_reasoning_exposed':False,'target_revised':False,'runtime_mutated':False}
def build_reflection_supported_revision_candidate_inspection(runtime_root=None): return ReflectionSupportedRevisionCandidateStore(runtime_root).inspection_summary()
