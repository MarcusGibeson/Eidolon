from __future__ import annotations
"""v1135.4 deterministic content-free deficiency arbitration."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from deficiency_deliberation_sessions import DeficiencyDeliberationSessionStore
CONTRACT_VERSION='v1135.4'; SCHEMA_VERSION='1'
OUTCOMES={'verified_deficiency','probable_deficiency','defer_for_more_evidence','defer_for_operator_review','await_prerequisite','defer_for_recovery','defer_for_resource_budget','await_impact_review','await_feasibility_review','suppress_single_sample','suppress_false_severity','suppress_low_confidence','architectural_suspicion_only','contradicted','retracted','deliberate_no_deficiency'}
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v:Any,n=240): return ' '.join(str(v or '').split())[:n]
def _digest(*p:Any): return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'outcomes':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{k:False for k in ('can_read_raw_files','can_modify_source','can_create_sandbox','can_run_tests','can_create_proposal','can_approve','can_authorize','can_execute','can_promote','can_certify')}}
class DeficiencyArbitrationStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/'deficiency_arbitration.json'; self.clock=clock or _now; self.sessions=DeficiencyDeliberationSessionStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def arbitrate(self,event_id:str,*,session_id:str,evidence_support:float=.5,impact_support:float=.5,feasibility_support:float=.5,operator_review_ready:bool=False,prerequisites_satisfied:bool=True,recovery_ready:bool=True,resource_budget_available:bool=True,deliberate_no_deficiency:bool=False,architectural_suspicion:bool=False,verified_defect_evidence:bool=False):
  row=next((x for x in self.sessions.snapshot().get('sessions',[]) if x.get('session_id')==session_id),None)
  if not row: raise ValueError('deficiency deliberation session required')
  clamp=lambda x:round(max(0,min(float(x),1)),4); evidence,impact,feasibility=map(clamp,(evidence_support,impact_support,feasibility_support)); pause=row.get('pause_reason',''); outcome='defer_for_more_evidence'; reason='insufficient_structural_support'
  if deliberate_no_deficiency: outcome='deliberate_no_deficiency'; reason='bounded_no_deficiency_selected'
  elif row.get('retraction_ids'): outcome='retracted'; reason='retraction_lineage'
  elif row.get('contradiction_ids') and evidence<.75: outcome='contradicted'; reason='unresolved_contradiction'
  elif pause=='operator_review_required' and not operator_review_ready: outcome='defer_for_operator_review'; reason=pause
  elif pause=='prerequisite_pending' or not prerequisites_satisfied: outcome='await_prerequisite'; reason='prerequisite_pending'
  elif pause=='recovery_constraint' or not recovery_ready: outcome='defer_for_recovery'; reason='recovery_constraint'
  elif pause=='resource_budget_constraint' or not resource_budget_available: outcome='defer_for_resource_budget'; reason='resource_budget_constraint'
  elif pause=='impact_review_pending': outcome='await_impact_review'; reason=pause
  elif pause=='feasibility_review_pending': outcome='await_feasibility_review'; reason=pause
  elif row.get('recurrence_count',1)<2 and row.get('reproducibility',0)<.6: outcome='suppress_single_sample'; reason='single_sample_noise'
  elif row.get('severity',0)>.8 and row.get('confidence',0)<.5: outcome='suppress_false_severity'; reason='severity_not_supported'
  elif row.get('confidence',0)<.45 or row.get('uncertainty',1)>.75 or evidence<.45: outcome='suppress_low_confidence'; reason='confidence_threshold'
  elif architectural_suspicion and not verified_defect_evidence: outcome='architectural_suspicion_only'; reason='suspicion_not_verified'
  elif verified_defect_evidence and evidence>=.75 and impact>=.5 and row.get('reproducibility',0)>=.6: outcome='verified_deficiency'; reason='structurally_verified_deficiency'
  elif evidence>=.6 and impact>=.4: outcome='probable_deficiency'; reason='supported_but_not_verified'
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,**deepcopy(prior['result']),'idempotent':True}
   existing=next((x for x in s['outcomes'] if x.get('session_id')==session_id),None)
   if existing: result={'status':'deficiency_arbitration_outcome_reused','arbitration_id':existing['arbitration_id'],'outcome':existing['outcome']}
   else:
    now=self.clock(); aid=f'def-arbitration-{session_id.rsplit("-",1)[-1]}'; rec={'arbitration_id':aid,'session_id':session_id,'candidate_id':row.get('candidate_id'),'comparison_candidate_ids':row.get('comparison_candidate_ids',[]),'signal_ids':row.get('signal_ids',[]),'deficiency_categories':row.get('deficiency_categories',[]),'component_ids':row.get('component_ids',[]),'evidence_ids':row.get('evidence_ids',[]),'project_digests':row.get('project_digests',[]),'scope_digests':row.get('scope_digests',[]),'predecessor_candidate_ids':row.get('predecessor_candidate_ids',[]),'outcome':outcome,'reason_code':reason,'evidence_support':evidence,'impact_support':impact,'feasibility_support':feasibility,'state':'recorded','created_at':now,'proposal_id':'','specification_id':'','test_plan_id':'','sandbox_change_id':'','approval_id':'','authorization_id':'','execution_id':'','promotion_id':'','certification_id':''}; s['outcomes'].append(rec); result={'status':'deficiency_arbitration_recorded','arbitration_id':aid,'outcome':outcome,'reason_code':reason}
   now=self.clock(); s['processed_events'].append({'event_id':_clean(event_id,180),'occurred_at':now,'result':deepcopy(result),'content_free':True}); s['revision']+=1; s['updated_at']=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {'ok':True,**result,'idempotent':False,'provider_contacted':False,'external_action_executed':False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s['outcomes']:counts[x.get('outcome')]=counts.get(x.get('outcome'),0)+1
  return {'ok':True,'contract_version':CONTRACT_VERSION,'outcome_count':len(s['outcomes']),'outcome_counts':counts,'recognized_outcomes':sorted(OUTCOMES),'recent_outcomes':deepcopy(s['outcomes'][-24:]),'authority_boundary':deepcopy(s['authority_boundary']),'raw_content_exposed':False,'source_content_exposed':False,'evidence_text_exposed':False,'proposal_text_exposed':False,'hidden_reasoning_exposed':False,'provider_contacted':False,'external_action_executed':False}
def build_deficiency_arbitration_inspection(runtime_root=None): return DeficiencyArbitrationStore(runtime_root).inspection_summary()
