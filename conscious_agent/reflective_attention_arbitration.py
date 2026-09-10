from __future__ import annotations
"""v1123.4 deterministic comparison for bounded attention review; never selects attention."""
from copy import deepcopy
from reflective_attention_deliberation import ReflectiveAttentionDeliberationStore, CONTRACT_VERSION as SESSION_VERSION
CONTRACT_VERSION="v1123.4"
class ReflectiveAttentionArbitrator:
 def __init__(self,runtime_root=None): self.sessions=ReflectiveAttentionDeliberationStore(runtime_root)
 def arbitrate(self,event_id:str,*,session_id:str,relevance:float=.5,importance:float=.5,urgency:float=.5,uncertainty:float=.5,persistence:float=.5,overlap_strength:float=.0,cognitive_load:float=.5,recovery_constraint:float=.0,operator_review_required:bool=False,force_unresolved:bool=False):
  clamp=lambda x:round(max(0.0,min(float(x),1.0)),4); relevance=clamp(relevance); importance=clamp(importance); urgency=clamp(urgency); uncertainty=clamp(uncertainty); persistence=clamp(persistence); overlap=clamp(overlap_strength); load=clamp(cognitive_load); recovery=clamp(recovery_constraint)
  row=next((x for x in self.sessions.snapshot().get("sessions",[]) if x.get("session_id")==session_id),None)
  if not row: raise ValueError("session required")
  if operator_review_required or row.get("operator_review_required"): outcome="requires_operator_review"; reason="operator_review_boundary"
  elif force_unresolved or uncertainty>.82: outcome="unresolved"; reason="uncertain_salience_support"
  elif recovery>=.7 or (load>=.82 and row.get("recovery_compatibility",0)<.5): outcome="defer_for_recovery"; reason="recovery_or_load_constraint"
  elif overlap>=.75 or row.get("semantic_overlap"): outcome="merge_overlap"; reason="semantic_attention_overlap"
  elif importance>=.7 and relevance>=.6 and persistence>=.55 and uncertainty<=.55: outcome="prioritize_for_bounded_attention"; reason="durable_salience_support"
  elif importance<.3 and relevance<.3 and urgency<.4: outcome="deliberate_non_selection"; reason="insufficient_structural_support"
  else: outcome="retain_for_review"; reason="bounded_review_retained_without_attention_selection"
  result=self.sessions.record_outcome(event_id,session_id=session_id,outcome=outcome,reason_code=reason)
  result["arbitration"]={"contract_version":CONTRACT_VERSION,"outcome":outcome,"reason":reason,"scores":{"relevance":relevance,"importance":importance,"urgency":urgency,"uncertainty":uncertainty,"persistence":persistence,"overlap_strength":overlap,"cognitive_load":load,"recovery_constraint":recovery},"attention_selected":False,"reflection_created":False,"intention_created":False,"initiative_created":False,"message_sent":False,"notification_created":False,"proposal_created":False,"approval_granted":False,"authorization_granted":False,"external_action_executed":False,"provider_contacted":False,"browsing_performed":False}
  return result
 def inspection_summary(self):
  base=self.sessions.inspection_summary(); return {"ok":True,"contract_version":CONTRACT_VERSION,"session_contract_version":SESSION_VERSION,"outcome_counts":base.get("outcome_counts",{}),"recent_sessions":base.get("recent_sessions",[]),"authority_boundary":deepcopy(base.get("authority_boundary",{})),"attention_selected":False,"reflection_created":False,"intention_created":False,"initiative_created":False,"message_sent":False,"notification_created":False,"proposal_created":False,"approval_granted":False,"authorization_granted":False,"external_action_executed":False,"provider_contacted":False,"browsing_performed":False,"hidden_reasoning_exposed":False,"runtime_mutated":False}
def build_reflective_attention_arbitration_inspection(runtime_root=None): return ReflectiveAttentionArbitrator(runtime_root).inspection_summary()
