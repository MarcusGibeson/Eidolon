from __future__ import annotations
"""Bounded deterministic outcome-to-decision attribution (v1112.1)."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from behavioral_outcome_evidence import BehavioralOutcomeStore
CONTRACT_VERSION='v1112.1'; STATUSES={'attributed','partially_attributed','ambiguous','unrelated','corrected','unresolved'}; DECISIONS={'agenda','reflection','intention','initiative','proposal','objective','curiosity','self_model','restraint'}
def _now():return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v,n=300):return ' '.join(str(v or '').split())[:n]
def _digest(*p):return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root():return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default():return {'schema_version':'1','contract_version':CONTRACT_VERSION,'attributions':[],'processed_events':[],'revision':0,'updated_at':'','controls':{'max_attributions':512,'max_contributors':8},'authority_boundary':{'can_change_behavior':False,'can_change_preferences':False,'can_modify_source':False,'can_change_prompts':False,'can_manage_models':False,'can_authorize':False,'can_execute':False}}
class BehavioralAttributionStore:
 def __init__(self,runtime_root=None):self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/'behavioral_attributions.json'
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get('schema_version')!='1':s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def record_attribution(self,event_id,*,outcome_id,status,contributors,uncertainty=0.5,notes_code=''):
  if status not in STATUSES:raise ValueError('unsupported attribution status')
  outcome=next((x for x in BehavioralOutcomeStore(self.runtime_root).snapshot()['outcomes'] if x.get('outcome_id')==outcome_id),None)
  if not outcome:raise ValueError('unknown outcome_id')
  normalized=[]; total=0.0
  for c in contributors[:8]:
   kind=_clean(c.get('decision_type'),80); did=_clean(c.get('decision_id'),240); weight=max(0,min(1,float(c.get('weight',0))))
   if kind not in DECISIONS or not did:raise ValueError('invalid contributor')
   normalized.append({'decision_type':kind,'decision_id_digest':_digest(did),'weight':round(weight,4)}); total+=weight
  if status in {'attributed','partially_attributed'} and not normalized:raise ValueError('contributors required')
  if total>1.0001:raise ValueError('contributor weights exceed one')
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,'status':'duplicate_event_ignored','result':deepcopy(prior['result']),'idempotent':True}
   key=_digest(outcome_id,status,*(f"{x['decision_type']}:{x['decision_id_digest']}:{x['weight']}" for x in normalized)); existing=next((x for x in s['attributions'] if x.get('semantic_key')==key),None)
   if existing:result={'status':'duplicate_attribution_ignored','attribution_id':existing['attribution_id']}
   else:
    now=_now(); aid=f'attribution-{key[:24]}'; row={'attribution_id':aid,'semantic_key':key,'outcome_id_digest':_digest(outcome_id),'outcome_class':outcome.get('outcome_class'),'status':status,'contributors':normalized,'uncertainty':round(max(0,min(1,float(uncertainty))),4),'notes_code_digest':_digest(notes_code),'feedback_known':outcome.get('feedback_known',False),'created_at':now,'active_influence':status not in {'corrected','unrelated'},'content_free':True,'causation_certain':False,'authority_granted':False};s['attributions']=(s['attributions']+[row])[-512:];result={'status':'attribution_recorded','attribution_id':aid}
   now=_now();s['processed_events']=(s['processed_events']+[{'event_id':event_id,'event_digest':_digest(event_id),'occurred_at':now,'result':deepcopy(result),'content_free':True}])[-2048:];s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,'status':result['status'],'result':result,'idempotent':False}
 def inspection_summary(self):
  s=self._load();rows=s['attributions'];return {'ok':True,'contract_version':CONTRACT_VERSION,'revision':s['revision'],'attribution_count':len(rows),'status_counts':{k:sum(x.get('status')==k for x in rows) for k in sorted(STATUSES)},'ambiguous_or_unresolved_count':sum(x.get('status') in {'ambiguous','unresolved','partially_attributed'} for x in rows),'recent_attributions':[{k:x.get(k) for k in ('attribution_id','outcome_id_digest','outcome_class','status','contributors','uncertainty','feedback_known','causation_certain','active_influence')} for x in rows[-24:]],'authority_boundary':deepcopy(s['authority_boundary']),'raw_content_exposed':False,'hidden_reasoning_exposed':False,'behavior_changed':False,'external_action_executed':False}
def build_behavioral_attribution_inspection(runtime_root=None):return BehavioralAttributionStore(runtime_root).inspection_summary()
