from __future__ import annotations
"""v1137.0 durable content-free supervised specification eligibility."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from development_proposal_arbitration import DevelopmentProposalArbitrationStore
CONTRACT_VERSION='v1137.0'; SCHEMA_VERSION='1'
SPECIFICATION_CATEGORIES={'capability_specification','reliability_specification','usability_specification','architecture_specification','test_coverage_specification','documentation_or_operator_control_specification','privacy_or_governance_specification','deliberate_no_specification_review'}
STATES={'eligible','suppressed','deferred','awaiting_prerequisite','requires_operator_review','superseded','retracted','stale','retired'}
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v:Any,n=240): return ' '.join(str(v or '').split())[:n]
def _digest(*p): return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'eligibility_records':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{k:False for k in ('can_read_raw_source','can_write_specification_text','can_modify_source','can_create_specification','can_create_test_plan','can_create_sandbox','can_run_tests','can_approve','can_authorize','can_execute','can_promote','can_certify')}}
class SpecificationEligibilityStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/'specification_eligibility.json'; self.clock=clock or _now; self.arbitration=DevelopmentProposalArbitrationStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id:str,*,arbitration_id:str,specification_category:str,scope_component_ids:list[str],prerequisite_ids:list[str]|None=None,operator_review_required:bool=True,estimated_complexity:float=.5,estimated_risk:float=.5,reversibility:float=.5):
  outcome=next((x for x in self.arbitration._load().get('outcomes',[]) if x.get('arbitration_id')==arbitration_id),None)
  comps=list(dict.fromkeys(_clean(x,220) for x in scope_component_ids if _clean(x,220))); prereqs=list(dict.fromkeys(_clean(x,220) for x in (prerequisite_ids or []) if _clean(x,220)))
  if not event_id or not outcome or specification_category not in SPECIFICATION_CATEGORIES or not comps: raise ValueError('exact supported-proposal lineage and structural scope required')
  clamp=lambda x:round(max(0,min(float(x),1)),4); complexity,risk,rev=map(clamp,(estimated_complexity,estimated_risk,reversibility))
  supported=outcome.get('outcome') in {'proposal_supported','proposal_probable'}; verified=outcome.get('outcome')=='proposal_supported'; no_proposal=specification_category=='deliberate_no_specification_review'
  state='suppressed'
  reason='unsupported_proposal_outcome'
  if no_proposal: state='deferred'; reason='deliberate_no_specification'
  elif prereqs: state='awaiting_prerequisite'; reason='prerequisite_pending'
  elif operator_review_required: state='requires_operator_review'; reason='operator_review_required'
  elif supported: state='eligible'; reason='bounded_structural_eligibility'
  semantic=_digest(arbitration_id,specification_category,*comps,*prereqs)
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,**deepcopy(prior['result']),'idempotent':True}
   dup=next((x for x in s['eligibility_records'] if x.get('semantic_key')==semantic and x.get('state') in {'eligible','deferred','awaiting_prerequisite','requires_operator_review'}),None)
   if dup: result={'status':'specification_eligibility_reused','eligibility_id':dup['eligibility_id'],'state':dup['state']}
   else:
    now=self.clock(); eid=f'specification-eligibility-{semantic[:24]}'; row={'eligibility_id':eid,'arbitration_id':arbitration_id,'session_id':outcome.get('session_id'),'proposal_candidate_id':outcome.get('candidate_id'),'proposal_eligibility_ids':outcome.get('eligibility_ids',[]),'deficiency_candidate_ids':outcome.get('deficiency_candidate_ids',[]),'proposal_categories':outcome.get('proposal_categories',[]),'specification_category':specification_category,'component_ids':comps,'project_digests':outcome.get('project_digests',[]),'scope_digests':outcome.get('scope_digests',[]),'evidence_ids':outcome.get('evidence_ids',[]),'supported_proposal':verified,'eligible_proposal':supported,'estimated_complexity':complexity,'estimated_risk':risk,'reversibility':rev,'prerequisite_ids':prereqs,'operator_review_required':bool(operator_review_required),'eligibility_reason':reason,'semantic_key':semantic,'structural_digest':_digest(semantic,state,complexity,risk,rev),'state':state,'created_at':now,'updated_at':now,'development_proposal_id':'','specification_id':'','test_plan_id':'','sandbox_change_id':'','approval_id':'','authorization_id':'','execution_id':'','promotion_id':'','certification_id':''}; s['eligibility_records'].append(row); result={'status':'specification_eligibility_registered','eligibility_id':eid,'state':state,'reason':reason}
   now=self.clock(); s['processed_events'].append({'event_id':_clean(event_id,180),'occurred_at':now,'result':deepcopy(result),'content_free':True}); s['revision']+=1; s['updated_at']=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {'ok':True,**result,'idempotent':False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s['eligibility_records']: counts[x.get('state')]=counts.get(x.get('state'),0)+1
  return {'ok':True,'contract_version':CONTRACT_VERSION,'record_count':len(s['eligibility_records']),'state_counts':counts,'specification_categories':sorted(SPECIFICATION_CATEGORIES),'recent_records':deepcopy(s['eligibility_records'][-24:]),'authority_boundary':deepcopy(s['authority_boundary']),'raw_source_exposed':False,'specification_text_exposed':False,'evidence_text_exposed':False,'hidden_reasoning_exposed':False,'provider_contacted':False,'external_action_executed':False}
def build_specification_eligibility_inspection(runtime_root=None): return SpecificationEligibilityStore(runtime_root).inspection_summary()
