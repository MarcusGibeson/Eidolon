from __future__ import annotations
"""v1138.1 governed content-free supervised test-plan candidates."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from test_plan_eligibility import TestPlanEligibilityStore
CONTRACT_VERSION='v1138.1'; SCHEMA_VERSION='1'
STATES={'active','suppressed','deferred','awaiting_prerequisite','requires_operator_review','merged','superseded','stale','obsolete','retracted','retired'}
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v:Any,n=240): return ' '.join(str(v or '').split())[:n]
def _digest(*p): return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'candidates':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{k:False for k in ('can_write_test_plan_text','can_read_raw_source','can_modify_source','can_create_test_plan','can_create_test_code','can_create_fixture','can_create_sandbox','can_run_tests','can_approve','can_authorize','can_execute','can_promote','can_certify')}}
class TestPlanCandidateStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/'test_plan_candidates.json'; self.clock=clock or _now; self.eligibility=TestPlanEligibilityStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def register(self,event_id:str,*,eligibility_ids:list[str],predecessor_candidate_ids:list[str]|None=None,contradiction_ids:list[str]|None=None,retraction_ids:list[str]|None=None):
  clean=lambda xs:list(dict.fromkeys(_clean(x,220) for x in (xs or []) if _clean(x,220)))
  ids,pred,contradictions,retractions=map(clean,(eligibility_ids,predecessor_candidate_ids,contradiction_ids,retraction_ids)); rows=[x for x in self.eligibility.snapshot().get('eligibility_records',[]) if x.get('eligibility_id') in ids]
  if not event_id or not rows or len(rows)!=len(ids): raise ValueError('exact test-plan eligibility lineage required')
  cats=sorted({x.get('test_plan_category') for x in rows}); comps=sorted({c for x in rows for c in x.get('component_ids',[])}); semantic=_digest(*cats,*comps,*sorted(x.get('arbitration_id','') for x in rows)); weak=all(x.get('state')=='suppressed' for x in rows); prereqs=sorted({p for x in rows for p in x.get('prerequisite_ids',[])}); review=any(x.get('operator_review_required') for x in rows); state='retracted' if retractions else ('requires_operator_review' if review else ('awaiting_prerequisite' if prereqs else ('suppressed' if weak else 'active')))
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,**deepcopy(prior['result']),'idempotent':True}
   dup=next((x for x in s['candidates'] if x.get('semantic_overlap_key')==semantic and x.get('state') in {'active','deferred','awaiting_prerequisite','requires_operator_review'}),None)
   if dup: result={'status':'test_plan_candidate_overlap_merged','candidate_id':dup['candidate_id'],'state':dup['state']}
   else:
    now=self.clock(); cid=f'test-plan-candidate-{semantic[:24]}'; row={'candidate_id':cid,'eligibility_ids':ids,'arbitration_ids':sorted({x.get('arbitration_id') for x in rows}),'specification_candidate_ids':sorted({x.get('specification_candidate_id') for x in rows}),'specification_eligibility_ids':sorted({i for x in rows for i in x.get('specification_eligibility_ids',[])}),'proposal_candidate_ids':sorted({i for x in rows for i in x.get('proposal_candidate_ids',[])}),'deficiency_candidate_ids':sorted({i for x in rows for i in x.get('deficiency_candidate_ids',[])}),'test_plan_categories':cats,'component_ids':comps,'coverage_target_ids':sorted({i for x in rows for i in x.get('coverage_target_ids',[])}),'environment_ids':sorted({i for x in rows for i in x.get('environment_ids',[])}),'dependency_ids':sorted({i for x in rows for i in x.get('dependency_ids',[])}),'project_digests':sorted({i for x in rows for i in x.get('project_digests',[])}),'scope_digests':sorted({i for x in rows for i in x.get('scope_digests',[])}),'evidence_ids':sorted({i for x in rows for i in x.get('evidence_ids',[])}),'predecessor_candidate_ids':pred,'contradiction_ids':contradictions,'retraction_ids':retractions,'estimated_cost':max(x.get('estimated_cost',0) for x in rows),'minimum_reproducibility':min(x.get('reproducibility',1) for x in rows),'minimum_determinism':min(x.get('determinism',1) for x in rows),'prerequisite_ids':prereqs,'operator_review_required':review,'semantic_overlap_key':semantic,'structural_digest':_digest(semantic,state,*contradictions,*retractions),'state':state,'created_at':now,'updated_at':now,'test_plan_text_digest':'','test_plan_id':'','test_code_digest':'','fixture_digest':'','sandbox_change_id':'','approval_id':'','authorization_id':'','execution_id':'','promotion_id':'','certification_id':''}; s['candidates'].append(row); result={'status':'test_plan_candidate_registered','candidate_id':cid,'state':state}
   now=self.clock(); s['processed_events'].append({'event_id':_clean(event_id,180),'occurred_at':now,'result':deepcopy(result),'content_free':True}); s['revision']+=1; s['updated_at']=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {'ok':True,**result,'idempotent':False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s['candidates']: counts[x.get('state')]=counts.get(x.get('state'),0)+1
  return {'ok':True,'contract_version':CONTRACT_VERSION,'candidate_count':len(s['candidates']),'state_counts':counts,'recognized_states':sorted(STATES),'recent_candidates':deepcopy(s['candidates'][-24:]),'authority_boundary':deepcopy(s['authority_boundary']),'test_plan_text_exposed':False,'test_code_exposed':False,'raw_source_exposed':False,'evidence_text_exposed':False,'hidden_reasoning_exposed':False,'provider_contacted':False,'external_action_executed':False}
def build_test_plan_candidate_inspection(runtime_root=None): return TestPlanCandidateStore(runtime_root).inspection_summary()
