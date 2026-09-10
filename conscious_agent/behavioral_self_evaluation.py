from __future__ import annotations
"""Bounded behavioral self-evaluation and non-adaptive improvement hypotheses (v1112.4)."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from behavioral_pattern_detection import BehavioralPatternStore
CONTRACT_VERSION='v1112.4'
EVALUATION_OUTCOMES={'retain','watch','question','hypothesis_eligible','suppressed','corrected','unresolved'}
def _now():return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v,n=300):return ' '.join(str(v or '').split())[:n]
def _digest(*p):return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root():return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default():return {'schema_version':'1','contract_version':CONTRACT_VERSION,'evaluations':[],'hypotheses':[],'processed_events':[],'revision':0,'updated_at':'','controls':{'minimum_pattern_evidence':3,'minimum_pattern_confidence':0.45,'minimum_hypothesis_evidence':4,'max_hypotheses':256},'state_separation':{'pattern_is_evaluation':False,'evaluation_is_hypothesis':False,'hypothesis_is_adaptation_proposal':False,'proposal_is_approval':False,'approval_is_authorization':False,'authorization_is_execution':False},'authority_boundary':{'can_adapt':False,'can_change_preferences':False,'can_modify_prompts':False,'can_modify_source':False,'can_manage_models':False,'can_authorize':False,'can_execute':False}}
class BehavioralSelfEvaluationStore:
 def __init__(self,runtime_root=None):self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/'behavioral_self_evaluations.json'
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get('schema_version')!='1':s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def evaluate(self,event_id,*,pattern_id,evaluation_code,proposed_direction_code='',uncertainty=0.5):
  pattern=next((x for x in BehavioralPatternStore(self.runtime_root)._load()['patterns'] if x.get('pattern_id')==pattern_id),None)
  if not pattern:raise ValueError('unknown pattern_id')
  reasons=[]
  if pattern.get('state')!='supported':reasons.append('pattern_not_supported')
  if pattern.get('evidence_count',0)<3:reasons.append('insufficient_evidence')
  if pattern.get('confidence',0)<.45:reasons.append('insufficient_confidence')
  if pattern.get('false_pattern_reason_codes'):reasons.append('false_pattern_risk')
  outcome='suppressed' if reasons else ('hypothesis_eligible' if pattern.get('evidence_count',0)>=4 and proposed_direction_code else 'watch')
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,'status':'duplicate_event_ignored','result':deepcopy(prior['result']),'idempotent':True}
   key=_digest(pattern_id,evaluation_code,proposed_direction_code,outcome);existing=next((x for x in s['evaluations'] if x.get('semantic_key')==key),None)
   if existing:result={'status':'duplicate_evaluation_ignored','evaluation_id':existing['evaluation_id']}
   else:
    now=_now();eid=f'evaluation-{key[:24]}';row={'evaluation_id':eid,'semantic_key':key,'pattern_id_digest':_digest(pattern_id),'evaluation_code_digest':_digest(evaluation_code),'outcome':outcome,'uncertainty':round(max(0,min(1,float(uncertainty))),4),'evidence_count':pattern.get('evidence_count',0),'pattern_confidence':pattern.get('confidence',0),'suppression_reason_codes':reasons,'created_at':now,'content_free':True,'active_influence':outcome not in {'suppressed','corrected'},'authority_granted':False};s['evaluations'].append(row);result={'status':'evaluation_recorded','evaluation_id':eid,'outcome':outcome}
    if outcome=='hypothesis_eligible':
     hkey=_digest(eid,proposed_direction_code);hid=f'hypothesis-{hkey[:24]}';s['hypotheses']=(s['hypotheses']+[{'hypothesis_id':hid,'semantic_key':hkey,'evaluation_id_digest':_digest(eid),'direction_code_digest':_digest(proposed_direction_code),'evidence_count':pattern.get('evidence_count',0),'uncertainty':round(max(.1,min(1,float(uncertainty))),4),'state':'unreviewed','created_at':now,'content_free':True,'adaptation_proposal_created':False,'authority_granted':False}])[-256:];result['hypothesis_id']=hid
   now=_now();s['processed_events']=(s['processed_events']+[{'event_id':event_id,'event_digest':_digest(event_id),'occurred_at':now,'result':deepcopy(result),'content_free':True}])[-2048:];s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,'status':result['status'],'result':result,'idempotent':False}
 def inspection_summary(self):
  s=self._load();ev=s['evaluations'];hy=s['hypotheses'];return {'ok':True,'contract_version':CONTRACT_VERSION,'evaluation_count':len(ev),'hypothesis_count':len(hy),'suppressed_evaluation_count':sum(x.get('outcome')=='suppressed' for x in ev),'outcome_counts':{k:sum(x.get('outcome')==k for x in ev) for k in sorted(EVALUATION_OUTCOMES)},'recent_evaluations':[{k:x.get(k) for k in ('evaluation_id','pattern_id_digest','outcome','uncertainty','evidence_count','pattern_confidence','suppression_reason_codes','active_influence')} for x in ev[-24:]],'recent_hypotheses':[{k:x.get(k) for k in ('hypothesis_id','evaluation_id_digest','evidence_count','uncertainty','state','adaptation_proposal_created','authority_granted')} for x in hy[-24:]],'state_separation':deepcopy(s['state_separation']),'authority_boundary':deepcopy(s['authority_boundary']),'raw_content_exposed':False,'hidden_reasoning_exposed':False,'behavior_changed':False,'adaptation_proposal_created':False,'external_action_executed':False}
def build_behavioral_self_evaluation_inspection(runtime_root=None):return BehavioralSelfEvaluationStore(runtime_root).inspection_summary()
