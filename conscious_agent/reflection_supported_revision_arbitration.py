from __future__ import annotations
"""v1128.4 deterministic target-specific revision arbitration; outcomes never apply revisions."""
from copy import deepcopy
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from reflection_supported_revision_deliberation_sessions import ReflectionSupportedRevisionDeliberationSessionStore
CONTRACT_VERSION='v1128.4';SCHEMA_VERSION='1'
OUTCOMES={'recommend_belief_revision','recommend_motivation_revision','recommend_goal_revision','recommend_self_model_revision','deliberate_non_application','defer_for_recovery','defer_for_operator_review','await_prerequisite','unresolved'}
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v:Any,n=200): return ' '.join(str(v or '').split())[:n]
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'outcomes':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{'can_apply_revision':False,'can_revise_target':False,'can_approve':False,'can_authorize':False,'can_execute':False}}
class ReflectionSupportedRevisionArbitrationStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root();self.path=self.runtime_root/'reflection_supported_revision_arbitration.json';self.clock=clock or _now;self.sessions=ReflectionSupportedRevisionDeliberationSessionStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self):return deepcopy(self._load())
 def arbitrate(self,event_id:str,*,session_id:str,structural_support:float=.0,uncertainty:float=1.0,deliberate_non_application:bool=False,recovery_ready:bool=True,operator_review_required:bool=False,prerequisites_satisfied:bool=True):
  row=next((x for x in self.sessions.snapshot().get('sessions',[]) if x.get('session_id')==session_id),None)
  if not row:raise ValueError('revision deliberation session required')
  support=max(0.,min(float(structural_support),1.));unc=max(0.,min(float(uncertainty),1.));outcome='unresolved';reason='insufficient_structural_support'
  if deliberate_non_application:outcome='deliberate_non_application';reason='bounded_non_application_selected'
  elif operator_review_required or row.get('pause_reason')=='operator_review_required':outcome='defer_for_operator_review';reason='operator_review_required'
  elif not prerequisites_satisfied or row.get('pause_reason')=='prerequisite_pending':outcome='await_prerequisite';reason='prerequisite_pending'
  elif not recovery_ready or row.get('pause_reason')=='recovery_constraint':outcome='defer_for_recovery';reason='recovery_constraint'
  elif support>=.7 and unc<=.35:
   outcome={'belief':'recommend_belief_revision','motivation':'recommend_motivation_revision','goal':'recommend_goal_revision','self_model':'recommend_self_model_revision'}.get(row.get('target_type'),'unresolved');reason='structural_support_sufficient' if outcome!='unresolved' else 'unsupported_target_type'
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,**deepcopy(prior['result']),'idempotent':True}
   existing=next((x for x in s['outcomes'] if x.get('session_id')==session_id),None)
   if existing:result={'status':'revision_arbitration_outcome_reused','arbitration_id':existing['arbitration_id'],'outcome':existing['outcome']}
   else:
    now=self.clock();aid=f'revision-arbitration-{session_id.rsplit("-",1)[-1]}';s['outcomes'].append({'arbitration_id':aid,'session_id':session_id,'candidate_id':row.get('candidate_id'),'signal_ids':row.get('signal_ids',[]),'target_type':row.get('target_type'),'target_id':row.get('target_id'),'revision_kind':row.get('revision_kind'),'outcome':outcome,'reason_code':reason,'support':support,'uncertainty':unc,'state':'recorded','created_at':now,'history':[{'change':'arbitrated','occurred_at':now,'content_free':True}]});result={'status':'revision_arbitration_recorded','arbitration_id':aid,'outcome':outcome,'reason_code':reason}
   now=self.clock();s['processed_events'].append({'event_id':_clean(event_id,180),'occurred_at':now,'result':deepcopy(result)});s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,**result,'idempotent':False,'target_revised':False,'revision_applied':False,'external_action_executed':False}
 def inspection_summary(self):
  s=self._load();counts={}
  for x in s['outcomes']:counts[x.get('outcome')]=counts.get(x.get('outcome'),0)+1
  return {'ok':True,'contract_version':CONTRACT_VERSION,'outcome_count':len(s['outcomes']),'outcome_counts':counts,'recognized_outcomes':sorted(OUTCOMES),'recent_outcomes':deepcopy(s['outcomes'][-24:]),'authority_boundary':deepcopy(s['authority_boundary']),'raw_content_exposed':False,'hidden_reasoning_exposed':False,'target_revised':False,'revision_applied':False,'external_action_executed':False}
def build_reflection_supported_revision_arbitration_inspection(runtime_root=None):return ReflectionSupportedRevisionArbitrationStore(runtime_root).inspection_summary()
