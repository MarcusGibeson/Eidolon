from __future__ import annotations
"""Bounded, provider-neutral self-model influence on reflection selection."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable, Iterable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from persistent_identity_model import PersistentIdentityModelStore
CONTRACT_VERSION='v1110.6'
OUTCOMES={'eligible_lens','deliberate_no_influence','defer','blocked'}
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v,n=500): return ' '.join(str(v or '').split())[:n]
def _digest(*p): return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':'1','contract_version':CONTRACT_VERSION,'influences':[],'processed_events':[],'revision':0,'updated_at':'','controls':{'max_influences':512,'max_claims_per_lens':4,'minimum_confidence':0.35,'maximum_uncertainty':0.75},'state_separation':{'identity_claim_is_reflection_conclusion':False,'reflection_lens_is_hidden_reasoning':False,'influence_is_intention':False,'influence_is_proposal':False,'proposal_is_authorization':False,'authorization_is_execution':False},'authority_boundary':{'can_browse':False,'can_send':False,'can_execute':False,'can_modify_files':False,'can_manage_models':False,'can_authorize':False,'can_approve':False,'can_promote':False,'can_certify':False}}
class SelfModelReflectionInfluenceStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/'self_model_reflection_influence.json';self.clock=clock or _now;self.claims=PersistentIdentityModelStore(self.runtime_root,clock=self.clock)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get('schema_version')!='1':s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self):return deepcopy(self._load())
 def select_lens(self,event_id,*,reflection_subject_ref,claim_ids:Iterable[str],quiet=False,paused=False,resource_available=True):
  event_id=_clean(event_id,180);subject=_clean(reflection_subject_ref,220);ids=tuple(dict.fromkeys(_clean(x,180) for x in claim_ids if _clean(x,180)))
  if not event_id or not subject:raise ValueError('event_id and reflection_subject_ref required')
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,'status':'duplicate_influence_event_ignored','result':deepcopy(prior['result']),'idempotent':True}
   now=self.clock();claims={x.get('claim_id'):x for x in self.claims.snapshot().get('claims',[])};eligible=[]
   for cid in ids[:int(s['controls']['max_claims_per_lens'])]:
    c=claims.get(cid)
    if c and c.get('active_influence') and c.get('eligible') and float(c.get('confidence') or 0)>=float(s['controls']['minimum_confidence']) and float(c.get('uncertainty') or 1)<=float(s['controls']['maximum_uncertainty']):eligible.append(c)
   if quiet or paused or not resource_available: outcome='defer';reason='control_boundary'
   elif not eligible: outcome='deliberate_no_influence';reason='no_eligible_identity_claim'
   else: outcome='eligible_lens';reason='bounded_identity_context'
   key=_digest(subject,outcome,*[x['claim_id'] for x in eligible]);existing=next((x for x in s['influences'] if x.get('influence_key')==key),None)
   if existing:result={'status':'duplicate_influence_ignored','influence_id':existing['influence_id'],'outcome':existing['outcome']}
   else:
    iid=f'self-model-reflection-{key[:24]}';row={'influence_id':iid,'influence_key':key,'subject_digest':_digest(subject),'claim_ids':[x['claim_id'] for x in eligible],'claim_count':len(eligible),'outcome':outcome,'reason_code':reason,'reflection_step_limit':1,'may_shape_attention':outcome=='eligible_lens','may_dictate_conclusion':False,'contradictory_evidence_allowed':True,'hidden_reasoning_stored':False,'provider_contacted':False,'proposal_id':'','authorization_id':'','action_id':'','authority_granted':False,'created_at':now};s['influences'].append(row);result={'status':'reflection_influence_recorded','influence_id':iid,'outcome':outcome,'claim_count':len(eligible)}
   s['influences']=s['influences'][-int(s['controls']['max_influences']):];s['processed_events']=(s['processed_events']+[{'event_id':event_id,'event_digest':_digest(event_id),'occurred_at':now,'result':deepcopy(result)}])[-1024:];s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,'status':result['status'],'result':result,'idempotent':False}
 def inspection_summary(self):
  s=self._load();return {'ok':True,'contract_version':CONTRACT_VERSION,'revision':s['revision'],'influence_count':len(s['influences']),'eligible_lens_count':sum(x.get('outcome')=='eligible_lens' for x in s['influences']),'deliberate_no_influence_count':sum(x.get('outcome')=='deliberate_no_influence' for x in s['influences']),'recent_influences':deepcopy(s['influences'][-24:]),'controls':deepcopy(s['controls']),'state_separation':deepcopy(s['state_separation']),'authority_boundary':deepcopy(s['authority_boundary']),'runtime_mutated':False,'provider_contacted':False,'external_action_executed':False,'hidden_reasoning_exposed':False,'private_content_exposed':False}
def build_self_model_reflection_influence_inspection(runtime_root=None):return SelfModelReflectionInfluenceStore(runtime_root).inspection_summary()
