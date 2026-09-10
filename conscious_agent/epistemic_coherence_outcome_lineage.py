from __future__ import annotations
"""v1119.6 durable, content-free epistemic coherence outcome lineage."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
CONTRACT_VERSION='v1119.6'; SCHEMA_VERSION='1'
OUTCOMES={'retain_separation','merge_candidate','weaken_claim','suspend_claim','replace_dependency','request_more_evidence','unresolved','deliberate_no_repair','requires_operator_review'}
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v:Any,n=240): return ' '.join(str(v or '').split())[:n]
def _digest(*parts:Any): return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in parts).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'outcomes':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{'can_repair_records':False,'can_merge_records':False,'can_mutate_evidence':False,'can_mutate_knowledge':False,'can_mutate_belief':False,'can_mutate_self_model':False,'can_apply_policy':False,'can_approve':False,'can_authorize':False,'can_execute':False}}
class EpistemicCoherenceOutcomeLineageStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/'epistemic_coherence_outcome_lineage.json'; self.clock=clock or _now
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def record(self,event_id:str,*,candidate_id:str,session_id:str,outcome:str,signal_ids:list[str],predecessor_outcome_id:str='',replacement_dependency_id:str='',confidence:float=.5,uncertainty:float=.5):
  event_id=_clean(event_id,180); candidate_id=_clean(candidate_id,220); session_id=_clean(session_id,220); outcome=_clean(outcome,80); signals=sorted({_clean(x,220) for x in signal_ids if _clean(x,220)})
  if not event_id or not candidate_id or not session_id or outcome not in OUTCOMES or not signals: raise ValueError('valid structural outcome lineage required')
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,'status':'duplicate_event_ignored','result':deepcopy(prior['result']),'idempotent':True}
   structural=_digest(candidate_id,session_id,outcome,*signals,predecessor_outcome_id,replacement_dependency_id)
   existing=next((x for x in s['outcomes'] if x.get('structural_digest')==structural),None)
   if existing: result={'status':'duplicate_outcome_suppressed','outcome_id':existing['outcome_id']}
   else:
    now=self.clock(); oid=f'coherence-outcome-{structural[:24]}'; row={'outcome_id':oid,'candidate_id':candidate_id,'session_id':session_id,'signal_ids':signals,'outcome':outcome,'predecessor_outcome_id':_clean(predecessor_outcome_id,220),'replacement_dependency_id':_clean(replacement_dependency_id,220),'confidence':max(0,min(float(confidence),1)),'uncertainty':max(0,min(float(uncertainty),1)),'structural_digest':structural,'state':'recorded','superseded_by_outcome_id':'','created_at':now,'history':[{'change':'recorded','occurred_at':now,'content_free':True}],'records_repaired':False,'records_deleted':False}; s['outcomes'].append(row); result={'status':'coherence_outcome_recorded','outcome_id':oid,'records_repaired':False}
   now=self.clock(); s['processed_events'].append({'event_id':event_id,'event_digest':_digest(event_id),'occurred_at':now,'result':deepcopy(result),'content_free':True}); s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,'status':result['status'],'result':result,'idempotent':False}
 def supersede(self,event_id:str,*,outcome_id:str,successor_outcome_id:str):
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,'status':'duplicate_event_ignored','result':deepcopy(prior['result']),'idempotent':True}
   row=next((x for x in s['outcomes'] if x.get('outcome_id')==outcome_id),None); successor=next((x for x in s['outcomes'] if x.get('outcome_id')==successor_outcome_id),None)
   if not row or not successor: raise ValueError('known outcomes required')
   now=self.clock(); row['state']='superseded'; row['superseded_by_outcome_id']=successor_outcome_id; row['history'].append({'change':'superseded','successor_outcome_id':successor_outcome_id,'occurred_at':now,'content_free':True}); result={'status':'coherence_outcome_superseded','outcome_id':outcome_id,'history_preserved':True,'records_repaired':False}; s['processed_events'].append({'event_id':event_id,'event_digest':_digest(event_id),'occurred_at':now,'result':deepcopy(result),'content_free':True});s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,'status':result['status'],'result':result,'idempotent':False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s['outcomes']: counts[x.get('outcome')]=counts.get(x.get('outcome'),0)+1
  keys=('outcome_id','candidate_id','session_id','signal_ids','outcome','predecessor_outcome_id','replacement_dependency_id','confidence','uncertainty','state','superseded_by_outcome_id','structural_digest')
  return {'ok':True,'contract_version':CONTRACT_VERSION,'outcome_count':len(s['outcomes']),'outcome_counts':counts,'recent_outcomes':[{k:x.get(k) for k in keys} for x in s['outcomes'][-32:]],'authority_boundary':deepcopy(s['authority_boundary']),'history_preserved':True,'records_repaired':False,'records_deleted':False,'raw_messages_exposed':False,'evidence_text_exposed':False,'knowledge_text_exposed':False,'belief_text_exposed':False,'self_model_text_exposed':False,'hidden_reasoning_exposed':False,'runtime_mutated':False}
def build_epistemic_coherence_outcome_lineage_inspection(runtime_root=None): return EpistemicCoherenceOutcomeLineageStore(runtime_root).inspection_summary()
