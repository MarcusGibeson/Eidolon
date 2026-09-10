from __future__ import annotations
"""v1139.4 deterministic structural sandbox_change arbitration."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from sandbox_change_deliberation_sessions import SandboxChangeDeliberationSessionStore
CONTRACT_VERSION='v1139.4'; SCHEMA_VERSION='1'
OUTCOMES={'sandbox_change_supported','sandbox_change_probable','defer_for_more_evidence','defer_for_operator_review','await_prerequisite','defer_for_recovery','defer_for_resource_budget','await_scope_review','await_containment_review','await_reversibility_review','await_isolation_review','suppress_weak_support','suppress_low_reversibility','suppress_low_containment','contradicted','retracted','deliberate_no_sandbox_change'}
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v:Any,n=240): return ' '.join(str(v or '').split())[:n]
def _digest(*p): return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'outcomes':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{k:False for k in ('can_write_patch_text','can_modify_source','can_write_sandbox_files','can_write_sandbox_files','can_create_sandbox','can_run_tests','can_approve','can_authorize','can_execute','can_promote','can_certify')}}
class SandboxChangeArbitrationStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/'sandbox_change_arbitration.json'; self.clock=clock or _now; self.sessions=SandboxChangeDeliberationSessionStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def arbitrate(self,event_id:str,*,session_id:str,evidence_support:float=.5,scope_support:float=.5,containment_support:float=.5,reversibility_support:float=.5,isolation_support:float=.5,operator_review_ready:bool=False,prerequisites_satisfied:bool=True,recovery_ready:bool=True,resource_budget_available:bool=True,deliberate_no_sandbox_change:bool=False,contradicted:bool=False,retracted:bool=False):
  row=next((x for x in self.sessions.snapshot().get('sessions',[]) if x.get('session_id')==session_id),None)
  if not row: raise ValueError('sandbox_change deliberation session required')
  clamp=lambda x:round(max(0,min(float(x),1)),4); evidence,scope,coverage,repro,det=map(clamp,(evidence_support,scope_support,containment_support,reversibility_support,isolation_support)); pause=row.get('pause_reason',''); outcome='defer_for_more_evidence'; reason='insufficient_structural_support'
  if deliberate_no_sandbox_change: outcome='deliberate_no_sandbox_change'; reason='bounded_no_sandbox_change_selected'
  elif retracted: outcome='retracted'; reason='retraction_lineage'
  elif contradicted: outcome='contradicted'; reason='contradiction_lineage'
  elif pause=='operator_review_required' and not operator_review_ready: outcome='defer_for_operator_review'; reason=pause
  elif pause=='prerequisite_pending' or not prerequisites_satisfied: outcome='await_prerequisite'; reason='prerequisite_pending'
  elif pause=='recovery_constraint' or not recovery_ready: outcome='defer_for_recovery'; reason='recovery_constraint'
  elif pause=='resource_budget_constraint' or not resource_budget_available: outcome='defer_for_resource_budget'; reason='resource_budget_constraint'
  elif pause=='evidence_insufficient' or evidence<.45: outcome='suppress_weak_support'; reason='weak_support'
  elif pause=='scope_review_pending' or scope<.55: outcome='await_scope_review'; reason='scope_review_pending'
  elif pause=='containment_review_pending': outcome='await_containment_review'; reason='containment_review_pending'
  elif pause=='reversibility_review_pending': outcome='await_reversibility_review'; reason='reversibility_review_pending'
  elif pause=='isolation_review_pending': outcome='await_isolation_review'; reason='isolation_review_pending'
  elif repro<.35: outcome='suppress_low_reversibility'; reason='reversibility_insufficient'
  elif det<.35: outcome='suppress_low_containment'; reason='containment_insufficient'
  elif evidence>=.8 and scope>=.75 and coverage>=.7 and repro>=.65 and det>=.65: outcome='sandbox_change_supported'; reason='bounded_structural_support'
  elif evidence>=.6 and scope>=.6 and coverage>=.55 and repro>=.5 and det>=.5: outcome='sandbox_change_probable'; reason='probable_structural_support'
  semantic=_digest(session_id,outcome,evidence,scope,coverage,repro,det)
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,**deepcopy(prior['result']),'idempotent':True}
   now=self.clock(); aid=f'sandbox_change-arbitration-{semantic[:24]}'; record={'arbitration_id':aid,'session_id':session_id,'candidate_id':row.get('candidate_id'),'eligibility_ids':row.get('eligibility_ids',[]),'deficiency_candidate_ids':row.get('deficiency_candidate_ids',[]),'change_categories':row.get('change_categories',[]),'component_ids':row.get('component_ids',[]),'project_digests':row.get('project_digests',[]),'scope_digests':row.get('scope_digests',[]),'evidence_ids':row.get('evidence_ids',[]),'evidence_support':evidence,'scope_support':scope,'containment_support':coverage,'reversibility_support':repro,'isolation_support':det,'outcome':outcome,'reason':reason,'structural_digest':_digest(semantic,reason),'created_at':now,'patch_text_digest':'','sandbox_id':'','sandbox_change_id':'','approval_id':'','authorization_id':'','execution_id':'','promotion_id':'','certification_id':''}; s['outcomes'].append(record); result={'status':'sandbox_change_arbitrated','arbitration_id':aid,'outcome':outcome,'reason':reason}; s['processed_events'].append({'event_id':_clean(event_id,180),'occurred_at':now,'result':deepcopy(result),'content_free':True}); s['revision']+=1; s['updated_at']=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {'ok':True,**result,'idempotent':False,'provider_contacted':False,'external_action_executed':False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s['outcomes']: counts[x.get('outcome')]=counts.get(x.get('outcome'),0)+1
  return {'ok':True,'contract_version':CONTRACT_VERSION,'outcome_count':len(s['outcomes']),'outcome_counts':counts,'recognized_outcomes':sorted(OUTCOMES),'recent_outcomes':deepcopy(s['outcomes'][-24:]),'authority_boundary':deepcopy(s['authority_boundary']),'patch_text_exposed':False,'raw_source_exposed':False,'evidence_text_exposed':False,'hidden_reasoning_exposed':False,'provider_contacted':False,'external_action_executed':False}
def build_sandbox_change_arbitration_inspection(runtime_root=None): return SandboxChangeArbitrationStore(runtime_root).inspection_summary()
