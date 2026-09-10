from __future__ import annotations
"""v1145.7 content-free conversation-cognition coherence and reliability reviews."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from unified_conversational_context_eligibility import _clean, _identifier
from conversation_cognition_cross_cycle_continuity import ConversationCognitionCrossCycleContinuityStore
CONTRACT_VERSION="v1145.7"; SCHEMA_VERSION="1"; STATES={"reliable","review_required","degraded","superseded","retired"}
AUTHORITY_KEYS=("can_contact_provider","can_generate_conversation","can_send_message","can_mutate_cognition","can_mutate_memory","can_approve","can_authorize","can_install","can_promote","can_certify")
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _digest(*parts): return hashlib.sha256("\x1f".join(_clean(x,12000) for x in parts).encode()).hexdigest()
def _root(): return (Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition")
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"reviews":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{k:False for k in AUTHORITY_KEYS}}
class ConversationCognitionReliabilityReviewStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/'conversation_cognition_reliability_review.json'; self.clock=clock or _now; self.continuity=ConversationCognitionCrossCycleContinuityStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def review(self,event_id:str,*,continuity_record_ids:list[str],visible_behavior_class:str,retry_count:int=0,duplicate_count:int=0,stale_count:int=0,correction_success_count:int=0,correction_failure_count:int=0,coherence_score:float=1.0,uncertainty:float=0.0):
  event_id=_identifier(event_id); behavior=_identifier(visible_behavior_class)
  if not event_id or not behavior: raise ValueError('bounded event and visible behavior class required')
  state=self.continuity.snapshot(); byid={r.get('record_id'):r for r in state.get('records',[])}; ids=sorted({_identifier(x) for x in continuity_record_ids if _identifier(x)})
  if not ids or any(x not in byid for x in ids): raise ValueError('exact continuity lineage required')
  score=round(max(0,min(float(coherence_score),1)),4); unc=round(max(0,min(float(uncertainty),1)),4); bad=sum(byid[x].get('state')!='coherent' for x in ids)
  status='reliable'; reason='bounded_reliability_supported'
  if bad or stale_count or correction_failure_count: status,reason='review_required','continuity_or_correction_review_required'
  if score<0.5 or unc>0.7: status,reason='degraded','coherence_below_bound'
  dig=_digest(event_id,ids,behavior,retry_count,duplicate_count,stale_count,correction_success_count,correction_failure_count,score,unc,status); rid=f'conversation-cognition-reliability-{dig[:24]}'
  with metadata_mutation_lock(self.path):
   s=self._load()
   if event_id in s['processed_events']: return next(r for r in s['reviews'] if r['event_id']==event_id)
   row={"review_id":rid,"event_id":event_id,"continuity_record_ids":ids,"visible_behavior_class":behavior,"retry_count":max(0,int(retry_count)),"duplicate_count":max(0,int(duplicate_count)),"stale_count":max(0,int(stale_count)),"correction_success_count":max(0,int(correction_success_count)),"correction_failure_count":max(0,int(correction_failure_count)),"coherence_score":score,"uncertainty":unc,"state":status,"reason_code":reason,"reviewed_at":self.clock(),"structural_digest":dig,"content_free":True,"raw_output_stored":False,"message_sent":False,"authority_boundary":{k:False for k in AUTHORITY_KEYS}}
   s['reviews'].append(row); s['processed_events'].append(event_id); s['revision']=int(s['revision'])+1; s['updated_at']=self.clock(); write_json_atomic(self.path,s); return deepcopy(row)
def build_conversation_cognition_reliability_review_inspection(runtime_root=None):
 s=ConversationCognitionReliabilityReviewStore(runtime_root).snapshot(); rows=s.get('reviews',[])
 return {"contract_version":CONTRACT_VERSION,"review_count":len(rows),"revision":s.get('revision',0),"state_counts":{x:sum(r.get('state')==x for r in rows) for x in sorted(STATES)},"recent_reviews":deepcopy(rows[-24:]),"correction_effectiveness_visible":all('correction_success_count' in r and 'correction_failure_count' in r for r in rows),"visible_behavior_structural_only":all(r.get('visible_behavior_class') and r.get('content_free') and not r.get('raw_output_stored') for r in rows),"authority_boundary":deepcopy(s.get('authority_boundary',{})),"message_sent":False}
