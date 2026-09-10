from __future__ import annotations
"""v1138.0 durable content-free supervised test-plan eligibility."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from specification_arbitration import SpecificationArbitrationStore
CONTRACT_VERSION='v1138.0'; SCHEMA_VERSION='1'
TEST_PLAN_CATEGORIES={'unit_test_plan','integration_test_plan','continuity_test_plan','recovery_test_plan','privacy_test_plan','governance_test_plan','usability_test_plan','regression_test_plan','deliberate_no_test_plan_review'}
STATES={'eligible','suppressed','deferred','awaiting_prerequisite','requires_operator_review','superseded','retracted','stale','retired'}
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v:Any,n=240): return ' '.join(str(v or '').split())[:n]
def _digest(*p): return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'eligibility_records':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{k:False for k in ('can_read_raw_source','can_write_test_plan_text','can_modify_source','can_create_test_plan','can_create_test_code','can_create_fixture','can_create_sandbox','can_run_tests','can_approve','can_authorize','can_execute','can_promote','can_certify')}}
class TestPlanEligibilityStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/'test_plan_eligibility.json'; self.clock=clock or _now; self.arbitration=SpecificationArbitrationStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id:str,*,arbitration_id:str,test_plan_category:str,scope_component_ids:list[str],coverage_target_ids:list[str]|None=None,environment_ids:list[str]|None=None,dependency_ids:list[str]|None=None,prerequisite_ids:list[str]|None=None,operator_review_required:bool=True,estimated_cost:float=.5,reproducibility:float=.5,determinism:float=.5):
  outcome=next((x for x in self.arbitration._load().get('outcomes',[]) if x.get('arbitration_id')==arbitration_id),None)
  clean=lambda xs:list(dict.fromkeys(_clean(x,220) for x in (xs or []) if _clean(x,220)))
  comps,coverage,envs,deps,prereqs=map(clean,(scope_component_ids,coverage_target_ids,environment_ids,dependency_ids,prerequisite_ids))
  if not event_id or not outcome or test_plan_category not in TEST_PLAN_CATEGORIES or not comps: raise ValueError('exact supported-specification lineage and structural scope required')
  clamp=lambda x:round(max(0,min(float(x),1)),4); cost,repro,det=map(clamp,(estimated_cost,reproducibility,determinism))
  supported=outcome.get('outcome') in {'specification_supported','specification_probable'}; verified=outcome.get('outcome')=='specification_supported'; no_plan=test_plan_category=='deliberate_no_test_plan_review'
  state,reason='suppressed','unsupported_specification_outcome'
  if no_plan: state,reason='deferred','deliberate_no_test_plan'
  elif prereqs: state,reason='awaiting_prerequisite','prerequisite_pending'
  elif operator_review_required: state,reason='requires_operator_review','operator_review_required'
  elif supported: state,reason='eligible','bounded_structural_eligibility'
  semantic=_digest(arbitration_id,test_plan_category,*comps,*coverage,*envs,*deps,*prereqs)
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,**deepcopy(prior['result']),'idempotent':True}
   dup=next((x for x in s['eligibility_records'] if x.get('semantic_key')==semantic and x.get('state') in {'eligible','deferred','awaiting_prerequisite','requires_operator_review'}),None)
   if dup: result={'status':'test_plan_eligibility_reused','eligibility_id':dup['eligibility_id'],'state':dup['state']}
   else:
    now=self.clock(); eid=f'test-plan-eligibility-{semantic[:24]}'; row={'eligibility_id':eid,'arbitration_id':arbitration_id,'session_id':outcome.get('session_id'),'specification_candidate_id':outcome.get('candidate_id'),'specification_eligibility_ids':outcome.get('eligibility_ids',[]),'proposal_candidate_ids':outcome.get('proposal_candidate_ids',[]),'deficiency_candidate_ids':outcome.get('deficiency_candidate_ids',[]),'specification_categories':outcome.get('specification_categories',[]),'test_plan_category':test_plan_category,'component_ids':comps,'coverage_target_ids':coverage,'environment_ids':envs,'dependency_ids':deps,'project_digests':outcome.get('project_digests',[]),'scope_digests':outcome.get('scope_digests',[]),'evidence_ids':outcome.get('evidence_ids',[]),'supported_specification':verified,'eligible_specification':supported,'estimated_cost':cost,'reproducibility':repro,'determinism':det,'prerequisite_ids':prereqs,'operator_review_required':bool(operator_review_required),'eligibility_reason':reason,'semantic_key':semantic,'structural_digest':_digest(semantic,state,cost,repro,det),'state':state,'created_at':now,'updated_at':now,'test_plan_id':'','test_code_digest':'','fixture_digest':'','sandbox_change_id':'','approval_id':'','authorization_id':'','execution_id':'','promotion_id':'','certification_id':''}; s['eligibility_records'].append(row); result={'status':'test_plan_eligibility_registered','eligibility_id':eid,'state':state,'reason':reason}
   now=self.clock(); s['processed_events'].append({'event_id':_clean(event_id,180),'occurred_at':now,'result':deepcopy(result),'content_free':True}); s['revision']+=1; s['updated_at']=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {'ok':True,**result,'idempotent':False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s['eligibility_records']: counts[x.get('state')]=counts.get(x.get('state'),0)+1
  return {'ok':True,'contract_version':CONTRACT_VERSION,'record_count':len(s['eligibility_records']),'state_counts':counts,'test_plan_categories':sorted(TEST_PLAN_CATEGORIES),'recent_records':deepcopy(s['eligibility_records'][-24:]),'authority_boundary':deepcopy(s['authority_boundary']),'raw_source_exposed':False,'test_plan_text_exposed':False,'test_code_exposed':False,'evidence_text_exposed':False,'hidden_reasoning_exposed':False,'provider_contacted':False,'external_action_executed':False}
def build_test_plan_eligibility_inspection(runtime_root=None): return TestPlanEligibilityStore(runtime_root).inspection_summary()
