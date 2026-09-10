from __future__ import annotations
"""v2523 bounded novelty/cadence policy for state-grounded internal voice."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Any, Callable, Mapping
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock

CONTRACT_VERSION='v2523.0'; SCHEMA_VERSION='1'
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v,n=200): return ' '.join(str(v or '').split())[:n]
def _dig(v): return hashlib.sha256(_clean(v,2000).encode()).hexdigest()
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'revision':0,'recent':[],'controls':{'max_recent':96,'repeat_window':12,'max_lines_per_source':3},'authority_boundary':{'can_contact_provider':False,'can_send_message':False,'can_execute_action':False,'hidden_reasoning_exposed':False}}
class InternalVoiceCadence:
 def __init__(self,runtime_root:str|Path,*,clock:Callable[[],str]|None=None): self.root=Path(runtime_root).expanduser().resolve(); self.path=self.root/'internal_voice_cadence_v2523.json'; self.clock=clock or _now
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get('schema_version')!=SCHEMA_VERSION:s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def admit(self,event_id:str,*,voice_text:str,source_digest:str=''):
  eid=_clean(event_id,180); text=_clean(voice_text,260); sd=_clean(source_digest,64)
  if not eid or not text: raise ValueError('event_id and voice_text required')
  vd=_dig(text.lower())
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s['recent'] if x.get('event_id')==eid),None)
   if prior:return {'ok':True,'status':'voice_event_replayed','emit':bool(prior.get('emit')),'idempotent':True,'voice_digest':vd}
   window=s['recent'][-int(s['controls']['repeat_window']):]
   repeat=any(x.get('voice_digest')==vd for x in window)
   same_source=sum(1 for x in window if sd and x.get('source_digest')==sd)
   emit=not repeat and same_source < int(s['controls']['max_lines_per_source'])
   row={'event_id':eid,'voice_digest':vd,'source_digest':sd,'emit':emit,'suppression_reason':'repeated_voice' if repeat else ('source_voice_budget' if same_source>=int(s['controls']['max_lines_per_source']) else ''),'observed_at':self.clock(),'content_free':True}
   s['recent']=(s['recent']+[row])[-int(s['controls']['max_recent']):];s['revision']+=1;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True)
   return {'ok':True,'status':'voice_admitted' if emit else 'voice_suppressed','emit':emit,'idempotent':False,'voice_digest':vd,'suppression_reason':row['suppression_reason'],'provider_contacted':False,'hidden_reasoning_exposed':False}
 def inspection_summary(self):
  s=self._load();return {'ok':True,'contract_version':CONTRACT_VERSION,'revision':s['revision'],'recent_count':len(s['recent']),'emitted_count':sum(1 for x in s['recent'] if x.get('emit')),'authority_boundary':deepcopy(s['authority_boundary'])}
__all__=['CONTRACT_VERSION','InternalVoiceCadence']
