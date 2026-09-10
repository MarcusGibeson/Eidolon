from __future__ import annotations
"""Deterministic privacy-safe behavioral pattern detection (v1112.3)."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from behavioral_outcome_evidence import BehavioralOutcomeStore
from behavioral_outcome_attribution import BehavioralAttributionStore
CONTRACT_VERSION='v1112.3'
PATTERN_STATES={'candidate','supported','suppressed','corrected','retracted','unresolved'}
def _now():return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v,n=300):return ' '.join(str(v or '').split())[:n]
def _digest(*p):return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root():return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default():return {'schema_version':'1','contract_version':CONTRACT_VERSION,'patterns':[],'processed_events':[],'revision':0,'updated_at':'','controls':{'max_patterns':256,'minimum_evidence':3,'minimum_distinct_origins':2,'maximum_unknown_fraction':0.34},'authority_boundary':{'can_evaluate':False,'can_adapt':False,'can_change_preferences':False,'can_modify_prompts':False,'can_modify_source':False,'can_authorize':False,'can_execute':False}}
class BehavioralPatternStore:
 def __init__(self,runtime_root=None):self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/'behavioral_patterns.json'
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get('schema_version')!='1':s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def detect(self,event_id,*,pattern_kind,outcome_class,decision_type='',minimum_evidence=None):
  outcomes=[x for x in BehavioralOutcomeStore(self.runtime_root).snapshot()['outcomes'] if x.get('active_influence') and x.get('outcome_class')==outcome_class]
  attrs=BehavioralAttributionStore(self.runtime_root)._load()['attributions']; eligible=[]
  for row in outcomes:
   matching=[a for a in attrs if a.get('active_influence') and a.get('outcome_id_digest')==_digest(row['outcome_id']) and (not decision_type or any(c.get('decision_type')==decision_type for c in a.get('contributors',[])))]
   if matching:eligible.append((row,matching))
  threshold=max(3,int(minimum_evidence or 3)); known=[x for x in eligible if x[0].get('feedback_known')]; origin_diversity=len({x[0].get('origin_id_digest') for x in known}); positive=sum(x[0].get('score',0)>0 for x in known);negative=sum(x[0].get('score',0)<0 for x in known);unknown=len(eligible)-len(known)
  false_reasons=[]
  if len(known)<threshold:false_reasons.append('insufficient_evidence')
  if origin_diversity<2:false_reasons.append('insufficient_origin_diversity')
  if eligible and unknown/len(eligible)>0.34:false_reasons.append('excess_unknown_feedback')
  if positive and negative and min(positive,negative)/max(positive,negative)>=0.67:false_reasons.append('contradictory_evidence')
  state='suppressed' if false_reasons else 'supported'; key=_digest(pattern_kind,outcome_class,decision_type,*(x[0]['outcome_id'] for x in known))
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,'status':'duplicate_event_ignored','result':deepcopy(prior['result']),'idempotent':True}
   existing=next((x for x in s['patterns'] if x.get('semantic_key')==key),None)
   if existing:result={'status':'duplicate_pattern_ignored','pattern_id':existing['pattern_id']}
   else:
    now=_now();pid=f'pattern-{key[:24]}';row={'pattern_id':pid,'semantic_key':key,'pattern_kind':_clean(pattern_kind,80),'outcome_class':outcome_class,'decision_type':_clean(decision_type,80),'state':state,'evidence_count':len(known),'unknown_feedback_count':unknown,'distinct_origin_count':origin_diversity,'positive_count':positive,'negative_count':negative,'evidence_outcome_digests':[_digest(x[0]['outcome_id']) for x in known[:32]],'false_pattern_reason_codes':false_reasons,'confidence':round(min(0.95,len(known)/(len(known)+3)) if state=='supported' else 0.0,4),'created_at':now,'updated_at':now,'content_free':True,'active_influence':state=='supported','authority_granted':False};s['patterns']=(s['patterns']+[row])[-256:];result={'status':'pattern_recorded','pattern_id':pid,'state':state}
   now=_now();s['processed_events']=(s['processed_events']+[{'event_id':event_id,'event_digest':_digest(event_id),'occurred_at':now,'result':deepcopy(result),'content_free':True}])[-2048:];s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,'status':result['status'],'result':result,'idempotent':False}
 def inspection_summary(self):
  s=self._load();rows=s['patterns'];return {'ok':True,'contract_version':CONTRACT_VERSION,'pattern_count':len(rows),'supported_count':sum(x.get('state')=='supported' for x in rows),'suppressed_count':sum(x.get('state')=='suppressed' for x in rows),'state_counts':{k:sum(x.get('state')==k for x in rows) for k in sorted(PATTERN_STATES)},'recent_patterns':[{k:x.get(k) for k in ('pattern_id','pattern_kind','outcome_class','decision_type','state','evidence_count','unknown_feedback_count','distinct_origin_count','positive_count','negative_count','false_pattern_reason_codes','confidence','active_influence')} for x in rows[-24:]],'raw_content_exposed':False,'hidden_reasoning_exposed':False,'evaluation_created':False,'adaptation_created':False,'authority_boundary':deepcopy(s['authority_boundary'])}
def build_behavioral_pattern_inspection(runtime_root=None):return BehavioralPatternStore(runtime_root).inspection_summary()
