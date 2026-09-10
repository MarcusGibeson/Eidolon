from __future__ import annotations
"""v1145.6 content-free cross-cycle conversation-cognition continuity records."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from unified_conversational_context_eligibility import _clean, _identifier

CONTRACT_VERSION="v1145.6"; SCHEMA_VERSION="1"
STATES={"coherent","stale_context","correction_required","relationship_boundary_review","mood_goal_drift","silence_preserved","superseded","retracted","retired"}
CATEGORIES=("thought","memory","relationship","mood","goal","motivation","concern","attention","correction","session","provider","workload")
AUTHORITY_KEYS=("can_contact_provider","can_generate_conversation","can_send_message","can_create_notification","can_mutate_cognition","can_mutate_memory","can_mutate_relationship","can_mutate_mood","can_mutate_goal","can_approve","can_authorize","can_install","can_promote","can_certify")
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _digest(*parts): return hashlib.sha256("\x1f".join(_clean(x,12000) for x in parts).encode()).hexdigest()
def _root(): return (Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition")
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"records":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{k:False for k in AUTHORITY_KEYS}}
class ConversationCognitionCrossCycleContinuityStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None):
  self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/'conversation_cognition_cross_cycle_continuity.json'; self.clock=clock or _now
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def record(self,event_id:str,*,session_id:str,conversation_id:str,prior_generation_receipt_id:str,current_generation_receipt_id:str,source_revisions:dict[str,int],current_categories:list[str],historical_categories:list[str],stale_source_ids:list[str]|None=None,contradiction_ids:list[str]|None=None,correction_ids:list[str]|None=None,accepted_guidance_ids:list[str]|None=None,relationship_boundary_clear:bool=True,mood_goal_coherent:bool=True,silence_preserved:bool=True,current_thought_grounded:bool=True,memory_consistent:bool=True,correction_effective:bool=True,observed_at:str|None=None,expires_at:str|None=None):
  vals={n:_identifier(v) for n,v in {'event_id':event_id,'session_id':session_id,'conversation_id':conversation_id,'prior_generation_receipt_id':prior_generation_receipt_id,'current_generation_receipt_id':current_generation_receipt_id}.items()}
  if not all(vals.values()): raise ValueError('exact event, session, conversation, and generation lineage required')
  cur=sorted(set(current_categories)&set(CATEGORIES)); hist=sorted(set(historical_categories)&set(CATEGORIES)); stale=sorted({_identifier(x) for x in stale_source_ids or [] if _identifier(x)}); contra=sorted({_identifier(x) for x in contradiction_ids or [] if _identifier(x)}); corr=sorted({_identifier(x) for x in correction_ids or [] if _identifier(x)}); accepted=sorted({_identifier(x) for x in accepted_guidance_ids or [] if _identifier(x)})
  revs={_identifier(k):max(0,int(v)) for k,v in sorted(source_revisions.items()) if _identifier(k)}
  state='coherent'; reason='cross_cycle_lineage_coherent'
  if stale: state,reason='stale_context','stale_source_lineage'
  elif contra or (corr and not correction_effective): state,reason='correction_required','correction_or_contradiction_unresolved'
  elif not relationship_boundary_clear: state,reason='relationship_boundary_review','relationship_context_boundary_unclear'
  elif not mood_goal_coherent: state,reason='mood_goal_drift','mood_goal_lineage_incoherent'
  elif not silence_preserved: state,reason='correction_required','silence_authority_broadened'
  digest=_digest(*vals.values(),revs,cur,hist,stale,contra,corr,accepted,state,reason)
  rid=f'conversation-cognition-continuity-{digest[:24]}'
  with metadata_mutation_lock(self.path):
   s=self._load()
   if event_id in s['processed_events']: return next(r for r in s['records'] if r['event_id']==event_id)
   row={"record_id":rid,**vals,"source_revisions":revs,"current_categories":cur,"historical_categories":hist,"stale_source_ids":stale,"contradiction_ids":contra,"correction_ids":corr,"accepted_guidance_ids":accepted,"current_thought_grounded":bool(current_thought_grounded),"memory_consistent":bool(memory_consistent),"relationship_boundary_clear":bool(relationship_boundary_clear),"mood_goal_coherent":bool(mood_goal_coherent),"correction_effective":bool(correction_effective),"silence_preserved":bool(silence_preserved),"state":state,"reason_code":reason,"observed_at":_clean(observed_at or self.clock(),80),"expires_at":_clean(expires_at,80),"structural_digest":digest,"content_free":True,"raw_text_stored":False,"message_sent":False,"cognition_mutated":False,"authority_boundary":{k:False for k in AUTHORITY_KEYS}}
   s['records'].append(row); s['processed_events'].append(event_id); s['revision']=int(s['revision'])+1; s['updated_at']=self.clock(); write_json_atomic(self.path,s); return deepcopy(row)
def build_conversation_cognition_cross_cycle_continuity_inspection(runtime_root=None):
 s=ConversationCognitionCrossCycleContinuityStore(runtime_root).snapshot(); rows=s.get('records',[])
 return {"contract_version":CONTRACT_VERSION,"record_count":len(rows),"revision":s.get('revision',0),"state_counts":{x:sum(r.get('state')==x for r in rows) for x in sorted(STATES)},"recent_records":deepcopy(rows[-24:]),"current_historical_separated":all(set(r.get('current_categories',[])).isdisjoint(set(r.get('historical_categories',[]))) for r in rows),"stale_context_detected":True,"silence_preserved":all(r.get('silence_preserved') for r in rows),"content_free":all(r.get('content_free') and not r.get('raw_text_stored') for r in rows),"authority_boundary":deepcopy(s.get('authority_boundary',{})),"message_sent":False,"cognition_mutated":False}
