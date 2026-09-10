from __future__ import annotations
"""v1136.3 bounded content-free development-proposal deliberation sessions."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from development_proposal_candidates import DevelopmentProposalCandidateStore
CONTRACT_VERSION='v1136.3'; SCHEMA_VERSION='1'
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v:Any,n=240): return ' '.join(str(v or '').split())[:n]
def _digest(*p:Any): return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'sessions':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{k:False for k in ('can_write_proposal_text','can_read_raw_source','can_modify_source','can_create_specification','can_create_test_plan','can_create_sandbox','can_run_tests','can_approve','can_authorize','can_execute','can_promote','can_certify')}}
class DevelopmentProposalDeliberationSessionStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/'development_proposal_deliberation_sessions.json'; self.clock=clock or _now; self.candidates=DevelopmentProposalCandidateStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def open(self,event_id:str,*,candidate_id:str,comparison_candidate_ids:list[str]|None=None,deliberation_budget:int=1,evidence_sufficient:bool=True,scope_review_ready:bool=True,risk_review_ready:bool=True,reversibility_review_ready:bool=True,prerequisites_satisfied:bool=True,operator_review_ready:bool=False,recovery_ready:bool=True,resource_budget_available:bool=True):
  rows=self.candidates._load().get('candidates',[]); c=next((x for x in rows if x.get('candidate_id')==candidate_id),None); comparisons=list(dict.fromkeys(_clean(x,220) for x in (comparison_candidate_ids or []) if _clean(x,220)))
  if not c or c.get('state') not in {'active','deferred','awaiting_prerequisite','requires_operator_review'}: raise ValueError('eligible development proposal candidate required')
  if any(not any(x.get('candidate_id')==cid for x in rows) for cid in comparisons): raise ValueError('exact comparison proposal candidate lineage required')
  pause=''; budget=max(1,min(int(deliberation_budget),6))
  if c.get('operator_review_required') and not operator_review_ready: pause='operator_review_required'
  elif c.get('prerequisite_ids') and not prerequisites_satisfied: pause='prerequisite_pending'
  elif not recovery_ready: pause='recovery_constraint'
  elif not resource_budget_available: pause='resource_budget_constraint'
  elif not evidence_sufficient: pause='evidence_insufficient'
  elif not scope_review_ready: pause='scope_review_pending'
  elif not risk_review_ready: pause='risk_review_pending'
  elif not reversibility_review_ready: pause='reversibility_review_pending'
  semantic=_digest(candidate_id,*comparisons,budget,pause)
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,**deepcopy(prior['result']),'idempotent':True}
   existing=next((x for x in s['sessions'] if x.get('semantic_key')==semantic and x.get('state') in {'open','paused'}),None)
   if existing: result={'status':'development_proposal_deliberation_session_reused','session_id':existing['session_id'],'state':existing['state']}
   else:
    now=self.clock(); sid=f'dev-proposal-deliberation-{semantic[:24]}'; state='paused' if pause else 'open'; row={'session_id':sid,'semantic_key':semantic,'candidate_id':candidate_id,'comparison_candidate_ids':comparisons,'eligibility_ids':c.get('eligibility_ids',[]),'arbitration_ids':c.get('arbitration_ids',[]),'deficiency_candidate_ids':c.get('deficiency_candidate_ids',[]),'proposal_categories':c.get('proposal_categories',[]),'component_ids':c.get('component_ids',[]),'project_digests':c.get('project_digests',[]),'scope_digests':c.get('scope_digests',[]),'evidence_ids':c.get('evidence_ids',[]),'estimated_complexity':c.get('estimated_complexity',0),'estimated_risk':c.get('estimated_risk',0),'minimum_reversibility':c.get('minimum_reversibility',1),'prerequisite_ids':c.get('prerequisite_ids',[]),'operator_review_required':c.get('operator_review_required',False),'deliberation_budget':budget,'pause_reason':pause,'state':state,'created_at':now,'updated_at':now,'proposal_id':'','proposal_text_digest':'','specification_id':'','test_plan_id':'','sandbox_change_id':'','approval_id':'','authorization_id':'','execution_id':''}; s['sessions'].append(row); result={'status':'development_proposal_deliberation_session_opened','session_id':sid,'state':state,'pause_reason':pause}
   now=self.clock(); s['processed_events'].append({'event_id':_clean(event_id,180),'occurred_at':now,'result':deepcopy(result),'content_free':True}); s['revision']+=1; s['updated_at']=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {'ok':True,**result,'idempotent':False,'provider_contacted':False,'external_action_executed':False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s['sessions']: counts[x.get('state')]=counts.get(x.get('state'),0)+1
  return {'ok':True,'contract_version':CONTRACT_VERSION,'session_count':len(s['sessions']),'state_counts':counts,'recent_sessions':deepcopy(s['sessions'][-24:]),'authority_boundary':deepcopy(s['authority_boundary']),'proposal_text_exposed':False,'raw_source_exposed':False,'evidence_text_exposed':False,'hidden_reasoning_exposed':False,'provider_contacted':False,'external_action_executed':False}
def build_development_proposal_deliberation_session_inspection(runtime_root=None): return DevelopmentProposalDeliberationSessionStore(runtime_root).inspection_summary()
