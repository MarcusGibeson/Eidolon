from __future__ import annotations
"""Safe, non-authorizing behavioral adaptation proposals (v1112.6)."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from behavioral_self_evaluation import BehavioralSelfEvaluationStore
CONTRACT_VERSION='v1112.6'
ALLOWED_SCOPES={'attention_weight','restraint_weight','reflection_threshold','initiative_cooldown','curiosity_threshold','communication_timing'}
ALLOWED_STATES={'draft','pending_operator_review','suspended','rejected','retired','approved_for_bounded_apply','rolled_back'}
def _now():return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v,n=300):return ' '.join(str(v or '').split())[:n]
def _digest(*p):return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root():return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default():return {'schema_version':'1','contract_version':CONTRACT_VERSION,'proposals':[],'processed_events':[],'revision':0,'updated_at':'','controls':{'minimum_hypothesis_evidence':4,'maximum_absolute_delta':0.15,'operator_review_required':True,'automatic_apply':False,'automatic_retry':False,'max_active_proposals':64},'state_separation':{'hypothesis_is_proposal':False,'proposal_is_approval':False,'approval_is_authorization':False,'authorization_is_execution':False,'proposal_mutates_behavior':False},'authority_boundary':{'can_apply':False,'can_approve':False,'can_authorize':False,'can_execute':False,'can_modify_source':False,'can_modify_prompts':False,'can_manage_models':False,'can_contact_provider':False}}
class BehavioralAdaptationProposalStore:
 def __init__(self,runtime_root=None):self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/'behavioral_adaptation_proposals.json'
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get('schema_version')!='1':s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def propose(self,event_id,*,hypothesis_id,scope_code,requested_delta,uncertainty=0.5,rationale_code=''):
  if scope_code not in ALLOWED_SCOPES:raise ValueError('unsupported scope_code')
  hypotheses=BehavioralSelfEvaluationStore(self.runtime_root)._load()['hypotheses']
  hypothesis=next((x for x in hypotheses if x.get('hypothesis_id')==hypothesis_id),None)
  if not hypothesis:raise ValueError('unknown hypothesis_id')
  reasons=[]
  if hypothesis.get('state') not in {'unreviewed','retained'}:reasons.append('hypothesis_not_eligible')
  if hypothesis.get('evidence_count',0)<4:reasons.append('insufficient_evidence')
  delta=round(max(-.15,min(.15,float(requested_delta))),4)
  if abs(float(requested_delta))>.15:reasons.append('delta_clamped')
  state='suspended' if any(x!='delta_clamped' for x in reasons) else 'pending_operator_review'
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,'status':'duplicate_event_ignored','result':deepcopy(prior['result']),'idempotent':True}
   key=_digest(hypothesis_id,scope_code,delta,rationale_code);existing=next((x for x in s['proposals'] if x.get('semantic_key')==key),None)
   if existing:result={'status':'duplicate_proposal_ignored','proposal_id':existing['proposal_id'],'state':existing['state']}
   else:
    now=_now();pid=f'adaptation-proposal-{key[:24]}';row={'proposal_id':pid,'semantic_key':key,'hypothesis_id_digest':_digest(hypothesis_id),'scope_code':scope_code,'requested_delta':delta,'uncertainty':round(max(0,min(1,float(uncertainty))),4),'evidence_count':hypothesis.get('evidence_count',0),'state':state,'reason_codes':reasons,'rationale_code_digest':_digest(rationale_code),'created_at':now,'updated_at':now,'content_free':True,'operator_review_required':True,'approval_granted':False,'authorization_granted':False,'applied':False,'authority_granted':False};s['proposals'].append(row);result={'status':'proposal_recorded','proposal_id':pid,'state':state}
   now=_now();s['processed_events']=(s['processed_events']+[{'event_id':event_id,'event_digest':_digest(event_id),'occurred_at':now,'result':deepcopy(result),'content_free':True}])[-2048:];s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,'status':result['status'],'result':result,'idempotent':False}
 def inspection_summary(self):
  s=self._load();p=s['proposals'];return {'ok':True,'contract_version':CONTRACT_VERSION,'proposal_count':len(p),'pending_review_count':sum(x.get('state')=='pending_operator_review' for x in p),'suspended_count':sum(x.get('state')=='suspended' for x in p),'recent_proposals':[{k:x.get(k) for k in ('proposal_id','hypothesis_id_digest','scope_code','requested_delta','uncertainty','evidence_count','state','reason_codes','operator_review_required','approval_granted','authorization_granted','applied')} for x in p[-24:]],'controls':deepcopy(s['controls']),'state_separation':deepcopy(s['state_separation']),'authority_boundary':deepcopy(s['authority_boundary']),'raw_content_exposed':False,'hidden_reasoning_exposed':False,'behavior_changed':False,'approval_granted':False,'authorization_granted':False,'external_action_executed':False}
def build_behavioral_adaptation_proposal_inspection(runtime_root=None):return BehavioralAdaptationProposalStore(runtime_root).inspection_summary()
