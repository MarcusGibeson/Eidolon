from __future__ import annotations
"""v1138.4 deterministic structural test_plan arbitration."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from test_plan_deliberation_sessions import TestPlanDeliberationSessionStore
CONTRACT_VERSION='v1138.4'; SCHEMA_VERSION='1'
OUTCOMES={'test_plan_supported','test_plan_probable','defer_for_more_evidence','defer_for_operator_review','await_prerequisite','defer_for_recovery','defer_for_resource_budget','await_scope_review','await_coverage_review','await_reproducibility_review','await_determinism_review','suppress_weak_support','suppress_low_reproducibility','suppress_low_determinism','contradicted','retracted','deliberate_no_test_plan'}
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v:Any,n=240): return ' '.join(str(v or '').split())[:n]
def _digest(*p): return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'outcomes':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{k:False for k in ('can_write_test_plan_text','can_modify_source','can_create_test_plan','can_create_test_plan','can_create_sandbox','can_run_tests','can_approve','can_authorize','can_execute','can_promote','can_certify')}}
class TestPlanArbitrationStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/'test_plan_arbitration.json'; self.clock=clock or _now; self.sessions=TestPlanDeliberationSessionStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def arbitrate(self,event_id:str,*,session_id:str,evidence_support:float=.5,scope_support:float=.5,coverage_support:float=.5,reproducibility_support:float=.5,determinism_support:float=.5,operator_review_ready:bool=False,prerequisites_satisfied:bool=True,recovery_ready:bool=True,resource_budget_available:bool=True,deliberate_no_test_plan:bool=False,contradicted:bool=False,retracted:bool=False):
  row=next((x for x in self.sessions.snapshot().get('sessions',[]) if x.get('session_id')==session_id),None)
  if not row: raise ValueError('test_plan deliberation session required')
  clamp=lambda x:round(max(0,min(float(x),1)),4); evidence,scope,coverage,repro,det=map(clamp,(evidence_support,scope_support,coverage_support,reproducibility_support,determinism_support)); pause=row.get('pause_reason',''); outcome='defer_for_more_evidence'; reason='insufficient_structural_support'
  if deliberate_no_test_plan: outcome='deliberate_no_test_plan'; reason='bounded_no_test_plan_selected'
  elif retracted: outcome='retracted'; reason='retraction_lineage'
  elif contradicted: outcome='contradicted'; reason='contradiction_lineage'
  elif pause=='operator_review_required' and not operator_review_ready: outcome='defer_for_operator_review'; reason=pause
  elif pause=='prerequisite_pending' or not prerequisites_satisfied: outcome='await_prerequisite'; reason='prerequisite_pending'
  elif pause=='recovery_constraint' or not recovery_ready: outcome='defer_for_recovery'; reason='recovery_constraint'
  elif pause=='resource_budget_constraint' or not resource_budget_available: outcome='defer_for_resource_budget'; reason='resource_budget_constraint'
  elif pause=='evidence_insufficient' or evidence<.45: outcome='suppress_weak_support'; reason='weak_support'
  elif pause=='scope_review_pending' or scope<.55: outcome='await_scope_review'; reason='scope_review_pending'
  elif pause=='coverage_review_pending': outcome='await_coverage_review'; reason='coverage_review_pending'
  elif pause=='reproducibility_review_pending': outcome='await_reproducibility_review'; reason='reproducibility_review_pending'
  elif pause=='determinism_review_pending': outcome='await_determinism_review'; reason='determinism_review_pending'
  elif repro<.35: outcome='suppress_low_reproducibility'; reason='reproducibility_insufficient'
  elif det<.35: outcome='suppress_low_determinism'; reason='determinism_insufficient'
  elif evidence>=.8 and scope>=.75 and coverage>=.7 and repro>=.65 and det>=.65: outcome='test_plan_supported'; reason='bounded_structural_support'
  elif evidence>=.6 and scope>=.6 and coverage>=.55 and repro>=.5 and det>=.5: outcome='test_plan_probable'; reason='probable_structural_support'
  semantic=_digest(session_id,outcome,evidence,scope,coverage,repro,det)
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,**deepcopy(prior['result']),'idempotent':True}
   now=self.clock(); aid=f'test_plan-arbitration-{semantic[:24]}'; record={'arbitration_id':aid,'session_id':session_id,'candidate_id':row.get('candidate_id'),'eligibility_ids':row.get('eligibility_ids',[]),'deficiency_candidate_ids':row.get('deficiency_candidate_ids',[]),'test_plan_categories':row.get('test_plan_categories',[]),'component_ids':row.get('component_ids',[]),'project_digests':row.get('project_digests',[]),'scope_digests':row.get('scope_digests',[]),'evidence_ids':row.get('evidence_ids',[]),'evidence_support':evidence,'scope_support':scope,'coverage_support':coverage,'reproducibility_support':repro,'determinism_support':det,'outcome':outcome,'reason':reason,'structural_digest':_digest(semantic,reason),'created_at':now,'test_plan_text_digest':'','test_plan_id':'','sandbox_change_id':'','approval_id':'','authorization_id':'','execution_id':'','promotion_id':'','certification_id':''}; s['outcomes'].append(record); result={'status':'test_plan_arbitrated','arbitration_id':aid,'outcome':outcome,'reason':reason}; s['processed_events'].append({'event_id':_clean(event_id,180),'occurred_at':now,'result':deepcopy(result),'content_free':True}); s['revision']+=1; s['updated_at']=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {'ok':True,**result,'idempotent':False,'provider_contacted':False,'external_action_executed':False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s['outcomes']: counts[x.get('outcome')]=counts.get(x.get('outcome'),0)+1
  return {'ok':True,'contract_version':CONTRACT_VERSION,'outcome_count':len(s['outcomes']),'outcome_counts':counts,'recognized_outcomes':sorted(OUTCOMES),'recent_outcomes':deepcopy(s['outcomes'][-24:]),'authority_boundary':deepcopy(s['authority_boundary']),'test_plan_text_exposed':False,'raw_source_exposed':False,'evidence_text_exposed':False,'hidden_reasoning_exposed':False,'provider_contacted':False,'external_action_executed':False}
def build_test_plan_arbitration_inspection(runtime_root=None): return TestPlanArbitrationStore(runtime_root).inspection_summary()
