from __future__ import annotations
"""v1124.4 deterministic reflective-focus arbitration."""
from copy import deepcopy
from reflective_focus_deliberation import ReflectiveFocusDeliberationStore, CONTRACT_VERSION as SESSION_VERSION
CONTRACT_VERSION="v1124.4"
class ReflectiveFocusArbitrator:
 def __init__(self,runtime_root=None): self.sessions=ReflectiveFocusDeliberationStore(runtime_root)
 def arbitrate(self,event_id:str,*,session_id:str,importance:float=.5,relevance:float=.5,uncertainty:float=.5,focus_load:float=.5,recovery_constraint:float=.0,overlap_strength:float=.0,operator_review_required:bool=False,force_unresolved:bool=False):
  clamp=lambda x:round(max(0.0,min(float(x),1.0)),4); importance=clamp(importance); relevance=clamp(relevance); uncertainty=clamp(uncertainty); load=clamp(focus_load); recovery=clamp(recovery_constraint); overlap=clamp(overlap_strength)
  row=next((x for x in self.sessions.snapshot().get("sessions",[]) if x.get("session_id")==session_id),None)
  if not row: raise ValueError("focus session required")
  if operator_review_required or row.get("operator_review_required"): outcome="defer_for_operator_review"; reason="operator_review_boundary"
  elif force_unresolved or uncertainty>.82: outcome="unresolved"; reason="focus_support_uncertain"
  elif recovery>=.7 or load>=.85 or not row.get("recovery_compatible",True): outcome="suspend_for_recovery"; reason="recovery_or_focus_load_constraint"
  elif overlap>=.75 or row.get("overlap_attention_ids"): outcome="resolve_overlap"; reason="selected_attention_overlap"
  elif importance>=.62 and relevance>=.58 and uncertainty<=.58: outcome="continue_bounded_focus"; reason="bounded_focus_support"
  else: outcome="disengage_deliberately"; reason="insufficient_continuation_support"
  result=self.sessions.record_outcome(event_id,session_id=session_id,outcome=outcome,reason_code=reason); result["arbitration"]={"contract_version":CONTRACT_VERSION,"outcome":outcome,"reason":reason,"scores":{"importance":importance,"relevance":relevance,"uncertainty":uncertainty,"focus_load":load,"recovery_constraint":recovery,"overlap_strength":overlap},"reflection_created":False,"intention_created":False,"initiative_created":False,"message_sent":False,"notification_created":False,"external_action_executed":False}; return result
 def inspection_summary(self):
  base=self.sessions.inspection_summary(); return {"ok":True,"contract_version":CONTRACT_VERSION,"session_contract_version":SESSION_VERSION,"session_count":base.get("session_count",0),"outcome_counts":base.get("outcome_counts",{}),"recent_sessions":base.get("recent_sessions",[]),"authority_boundary":deepcopy(base.get("authority_boundary",{})),"reflection_created":False,"intention_created":False,"initiative_created":False,"message_sent":False,"notification_created":False,"provider_contacted":False,"browsing_performed":False,"external_action_executed":False,"hidden_reasoning_exposed":False,"runtime_mutated":False}
def build_reflective_focus_arbitration_inspection(runtime_root=None): return ReflectiveFocusArbitrator(runtime_root).inspection_summary()
