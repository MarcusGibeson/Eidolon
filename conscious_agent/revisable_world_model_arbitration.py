from __future__ import annotations
"""v1132.4 deterministic revisable world-model acceptance-versus-deferral arbitration."""
from copy import deepcopy
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from revisable_world_model_deliberation_sessions import RevisableWorldModelDeliberationSessionStore
CONTRACT_VERSION='v1132.4'; SCHEMA_VERSION='1'
OUTCOMES={'relationship_acceptance_recommended','causal_relationship_review_recommended','contradiction_reconciliation_recommended','correction_acceptance_recommended','temporal_relationship_review_recommended','deliberate_non_acceptance','defer_for_recovery','defer_for_focus','defer_for_cognitive_budget','defer_for_operator_review','await_prerequisite','await_contradiction_review','suppress_unsupported_causation','suppress_false_certainty','unresolved'}
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v:Any,n=200): return ' '.join(str(v or '').split())[:n]
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'outcomes':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{'can_apply_revision':False,'can_mutate_belief':False,'can_mutate_memory':False,'can_mutate_goal':False,'can_mutate_identity':False,'can_browse':False,'can_contact_provider':False,'can_execute':False,'can_modify_files':False,'can_send_message':False,'can_approve':False,'can_authorize':False,'can_promote':False,'can_certify':False}}
class RevisableWorldModelArbitrationStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/'revisable_world_model_arbitration.json'; self.clock=clock or _now; self.sessions=RevisableWorldModelDeliberationSessionStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def arbitrate(self,event_id:str,*,session_id:str,evidence_sufficiency:float=0.0,coherence:float=0.0,confidence_match:float=0.0,causal_support:float=0.0,deliberate_non_acceptance:bool=False,recovery_ready:bool=True,focus_available:bool=True,cognitive_budget_available:bool=True,operator_review_ready:bool=False,prerequisites_satisfied:bool=True,contradiction_review_ready:bool=True):
  row=next((x for x in self.sessions.snapshot().get('sessions',[]) if x.get('session_id')==session_id),None)
  if not row: raise ValueError('world-model deliberation session required')
  clamp=lambda x:max(0.,min(float(x),1.)); ev,coh,match,causal=map(clamp,(evidence_sufficiency,coherence,confidence_match,causal_support)); pause=row.get('pause_reason',''); relations=set(row.get('relation_categories',[])); outcome='unresolved'; reason='insufficient_structural_support'
  if deliberate_non_acceptance: outcome='deliberate_non_acceptance'; reason='bounded_non_acceptance_selected'
  elif pause=='operator_review_required' and not operator_review_ready: outcome='defer_for_operator_review'; reason=pause
  elif pause=='prerequisite_pending' or not prerequisites_satisfied: outcome='await_prerequisite'; reason='prerequisite_pending'
  elif pause=='recovery_constraint' or not recovery_ready: outcome='defer_for_recovery'; reason='recovery_constraint'
  elif pause=='focus_constraint' or not focus_available: outcome='defer_for_focus'; reason='focus_constraint'
  elif pause=='cognitive_budget_constraint' or not cognitive_budget_available: outcome='defer_for_cognitive_budget'; reason='cognitive_budget_constraint'
  elif pause=='contradiction_review_pending' or not contradiction_review_ready: outcome='await_contradiction_review'; reason='contradiction_review_pending'
  elif 'may_cause' in relations and causal<.65: outcome='suppress_unsupported_causation'; reason='causal_support_below_threshold'
  elif match<.35 and row.get('confidence',0)>=.7: outcome='suppress_false_certainty'; reason='confidence_mismatch'
  elif ev>=.6 and coh>=.55:
   if row.get('correction') or 'corrects' in relations: outcome='correction_acceptance_recommended'; reason='supported_correction'
   elif 'contradicts' in relations: outcome='contradiction_reconciliation_recommended'; reason='supported_contradiction'
   elif 'may_cause' in relations: outcome='causal_relationship_review_recommended'; reason='bounded_causal_support'
   elif relations & {'precedes','follows','temporally_contextualizes'}: outcome='temporal_relationship_review_recommended'; reason='supported_temporal_relation'
   else: outcome='relationship_acceptance_recommended'; reason='supported_relationship'
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,**deepcopy(prior['result']),'idempotent':True}
   existing=next((x for x in s['outcomes'] if x.get('session_id')==session_id),None)
   if existing: result={'status':'world_model_arbitration_outcome_reused','arbitration_id':existing['arbitration_id'],'outcome':existing['outcome']}
   else:
    now=self.clock(); aid=f'world-model-arbitration-{session_id.rsplit("-",1)[-1]}'; s['outcomes'].append({'arbitration_id':aid,'session_id':session_id,'candidate_id':row.get('candidate_id'),'signal_ids':row.get('signal_ids',[]),'entity_categories':row.get('entity_categories',[]),'relation_categories':row.get('relation_categories',[]),'model_purpose':row.get('model_purpose'),'scope_digest':row.get('scope_digest',''),'evidence_ids':row.get('evidence_ids',[]),'predecessor_candidate_ids':row.get('predecessor_candidate_ids',[]),'correction':row.get('correction',False),'outcome':outcome,'reason_code':reason,'evidence_sufficiency':round(ev,4),'coherence':round(coh,4),'confidence_match':round(match,4),'causal_support':round(causal,4),'state':'recorded','created_at':now,'history':[{'change':'arbitrated','occurred_at':now,'content_free':True}],'world_model_revision_id':'','belief_revision_id':'','memory_revision_id':'','goal_revision_id':'','identity_revision_id':'','message_id':'','approval_id':'','authorization_id':'','action_id':''}); result={'status':'world_model_arbitration_recorded','arbitration_id':aid,'outcome':outcome,'reason_code':reason}
   now=self.clock(); s['processed_events'].append({'event_id':_clean(event_id,180),'occurred_at':now,'result':deepcopy(result)}); s['revision']+=1; s['updated_at']=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {'ok':True,**result,'idempotent':False,'provider_contacted':False,'external_action_executed':False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s['outcomes']: counts[x.get('outcome')]=counts.get(x.get('outcome'),0)+1
  return {'ok':True,'contract_version':CONTRACT_VERSION,'outcome_count':len(s['outcomes']),'outcome_counts':counts,'recognized_outcomes':sorted(OUTCOMES),'recent_outcomes':deepcopy(s['outcomes'][-24:]),'authority_boundary':deepcopy(s['authority_boundary']),'raw_content_exposed':False,'evidence_text_exposed':False,'belief_text_exposed':False,'hidden_reasoning_exposed':False,'provider_contacted':False,'external_action_executed':False}
def build_revisable_world_model_arbitration_inspection(runtime_root=None): return RevisableWorldModelArbitrationStore(runtime_root).inspection_summary()
