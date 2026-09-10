from __future__ import annotations
"""v1128.0 durable reflection-supported revision eligibility signals; never mutates targets."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
CONTRACT_VERSION='v1128.0'; SCHEMA_VERSION='1'
TARGET_TYPES={'belief','motivation','goal','self_model'}
STATES={'active','suppressed','deferred','requires_operator_review','superseded','retracted','stale','retired'}
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v:Any,n=240): return ' '.join(str(v or '').split())[:n]
def _digest(*p:Any): return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'signals':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{'can_revise_target':False,'can_apply_revision':False,'can_contact_provider':False,'can_communicate':False,'can_approve':False,'can_authorize':False,'can_execute':False}}
class ReflectionSupportedRevisionSignalStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/'reflection_supported_revision_signals.json'; self.clock=clock or _now
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id:str,*,reflection_outcome_id:str,quality_outcome_id:str,target_type:str,target_id:str,evidence_refs:list[str],support:float,uncertainty:float,correction_required:bool=False,operator_review_required:bool=False,structural_digest:str=''):
  event_id=_clean(event_id,180); reflection_outcome_id=_clean(reflection_outcome_id,220); quality_outcome_id=_clean(quality_outcome_id,220); target_type=_clean(target_type,32); target_id=_clean(target_id,220); refs=list(dict.fromkeys(_clean(x,220) for x in evidence_refs if _clean(x,220)))
  if not event_id or not reflection_outcome_id or not quality_outcome_id or target_type not in TARGET_TYPES or not target_id or not refs: raise ValueError('complete structural lineage required')
  clamp=lambda x:round(max(0.0,min(float(x),1.0)),4); support=clamp(support); uncertainty=clamp(uncertainty)
  semantic=_digest(reflection_outcome_id,quality_outcome_id,target_type,target_id,*sorted(refs),structural_digest)
  state='requires_operator_review' if operator_review_required else ('suppressed' if support<0.55 or uncertainty>0.75 else 'active')
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,'status':'duplicate_event_ignored','result':deepcopy(prior['result']),'idempotent':True}
   dup=next((x for x in s['signals'] if x.get('semantic_key')==semantic and x.get('state') in {'active','requires_operator_review'}),None)
   if dup: result={'status':'duplicate_signal_ignored','signal_id':dup['signal_id']}
   else:
    now=self.clock(); sid=f'revision-signal-{semantic[:24]}'; row={'signal_id':sid,'semantic_key':semantic,'reflection_outcome_id':reflection_outcome_id,'quality_outcome_id':quality_outcome_id,'target_type':target_type,'target_id':target_id,'evidence_refs':refs,'support':support,'uncertainty':uncertainty,'correction_required':bool(correction_required),'operator_review_required':bool(operator_review_required),'structural_digest':_clean(structural_digest,128),'state':state,'created_at':now,'updated_at':now,'history':[{'change':'registered','occurred_at':now,'content_free':True}],'revision_candidate_id':'','revision_outcome_id':'','approval_id':'','authorization_id':'','action_id':''}; s['signals'].append(row); result={'status':'revision_signal_registered','signal_id':sid,'state':state}
   now=self.clock(); s['processed_events'].append({'event_id':event_id,'event_digest':_digest(event_id),'occurred_at':now,'result':deepcopy(result),'content_free':True});s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,'status':result['status'],'result':result,'idempotent':False}
 def inspection_summary(self):
  s=self._load();counts={}
  for x in s['signals']:counts[x.get('state')]=counts.get(x.get('state'),0)+1
  keys=('signal_id','reflection_outcome_id','quality_outcome_id','target_type','target_id','evidence_refs','support','uncertainty','correction_required','operator_review_required','structural_digest','state','revision_candidate_id','revision_outcome_id','approval_id','authorization_id','action_id')
  return {'ok':True,'contract_version':CONTRACT_VERSION,'signal_count':len(s['signals']),'state_counts':counts,'recent_signals':[{k:x.get(k) for k in keys} for x in s['signals'][-24:]],'authority_boundary':deepcopy(s['authority_boundary']),'raw_content_exposed':False,'conclusion_text_exposed':False,'evidence_text_exposed':False,'hidden_reasoning_exposed':False,'target_revised':False,'runtime_mutated':False}
def build_reflection_supported_revision_signal_inspection(runtime_root=None): return ReflectionSupportedRevisionSignalStore(runtime_root).inspection_summary()
