from __future__ import annotations
"""v1138.7 content-free test_plan reliability review."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from test_plan_outcome_lineage import TestPlanOutcomeLineageStore
CONTRACT_VERSION='v1138.7'; SCHEMA_VERSION='1'
FINDINGS={'stable','repeated_false_positive','possible_missed_test_plan','stale_outcome','continuity_gap','scope_drift','coverage_drift','dependency_drift','reproducibility_drift','determinism_drift','flaky_plan_pattern','operator_review_required','deliberate_no_change'}
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v:Any,n=240): return ' '.join(str(v or '').split())[:n]
def _digest(*p:Any): return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'reviews':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{k:False for k in ('can_write_test_plan_text','can_modify_source','can_create_test_plan','can_create_test_code','can_create_fixture','can_create_sandbox','can_run_tests','can_approve','can_authorize','can_execute','can_promote','can_certify')}}
class TestPlanReliabilityReviewStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/'test_plan_reliability_review.json'; self.clock=clock or _now; self.lineage=TestPlanOutcomeLineageStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def review(self,event_id:str,*,lineage_id:str,false_positive_count=0,missed_signal_count=0,continuity_gap_count=0,scope_drift=False,coverage_drift=False,dependency_drift=False,reproducibility_drift=False,determinism_drift=False,flaky_plan_count=0,stale=False,operator_review_required=False):
  row=next((x for x in self.lineage.inspection_summary().get('recent_lineage',[]) if x.get('lineage_id')==lineage_id),None)
  if not row: raise ValueError('test plan outcome lineage required')
  fp=max(0,int(false_positive_count)); missed=max(0,int(missed_signal_count)); gaps=max(0,int(continuity_gap_count)); flaky=max(0,int(flaky_plan_count)); finding='stable'
  if operator_review_required:finding='operator_review_required'
  elif fp>=2:finding='repeated_false_positive'
  elif missed>=2:finding='possible_missed_test_plan'
  elif stale:finding='stale_outcome'
  elif gaps>0:finding='continuity_gap'
  elif scope_drift:finding='scope_drift'
  elif coverage_drift:finding='coverage_drift'
  elif dependency_drift:finding='dependency_drift'
  elif reproducibility_drift:finding='reproducibility_drift'
  elif determinism_drift:finding='determinism_drift'
  elif flaky>=2:finding='flaky_plan_pattern'
  elif row.get('outcome')=='deliberate_no_test_plan':finding='deliberate_no_change'
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,**deepcopy(prior['result']),'idempotent':True}
   rid='test-plan-reliability-'+_digest(lineage_id,fp,missed,gaps,scope_drift,coverage_drift,dependency_drift,reproducibility_drift,determinism_drift,flaky,stale,operator_review_required)[:20]; now=self.clock(); rec={'review_id':rid,'lineage_id':lineage_id,'arbitration_id':row.get('arbitration_id'),'candidate_id':row.get('candidate_id'),'component_ids':row.get('component_ids',[]),'project_digests':row.get('project_digests',[]),'scope_digests':row.get('scope_digests',[]),'finding':finding,'false_positive_count':fp,'missed_signal_count':missed,'continuity_gap_count':gaps,'scope_drift':bool(scope_drift),'coverage_drift':bool(coverage_drift),'dependency_drift':bool(dependency_drift),'reproducibility_drift':bool(reproducibility_drift),'determinism_drift':bool(determinism_drift),'flaky_plan_count':flaky,'stale':bool(stale),'operator_review_required':bool(operator_review_required),'created_at':now,'structural_digest':_digest(lineage_id,finding,fp,missed,gaps),'policy_proposal_id':'','test_plan_id':'','test_code_id':'','fixture_id':'','sandbox_change_id':'','approval_id':'','authorization_id':'','execution_id':'','promotion_id':'','certification_id':''}; s['reviews'].append(rec); result={'status':'test_plan_reliability_review_recorded','review_id':rid,'finding':finding}; s['processed_events'].append({'event_id':_clean(event_id,180),'occurred_at':now,'result':deepcopy(result),'content_free':True}); s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,**result,'idempotent':False}
 def inspection_summary(self):
  s=self._load(); return {'ok':True,'contract_version':CONTRACT_VERSION,'review_count':len(s['reviews']),'recognized_findings':sorted(FINDINGS),'recent_reviews':deepcopy(s['reviews'][-24:]),'authority_boundary':deepcopy(s['authority_boundary']),'test_plan_text_exposed':False,'raw_source_exposed':False,'evidence_text_exposed':False,'hidden_reasoning_exposed':False,'provider_contacted':False,'external_action_executed':False}
def build_test_plan_reliability_review_inspection(runtime_root=None): return TestPlanReliabilityReviewStore(runtime_root).inspection_summary()
