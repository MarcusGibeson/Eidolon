from __future__ import annotations
"""v1122.4 deterministic bounded arbitration among motivational-drive responses."""
from copy import deepcopy
from motivational_drive_deliberation import MotivationalDriveDeliberationStore, CONTRACT_VERSION as SESSION_VERSION
CONTRACT_VERSION="v1122.4"
class MotivationalDriveArbitrator:
 def __init__(self,runtime_root=None): self.sessions=MotivationalDriveDeliberationStore(runtime_root)
 def arbitrate(self,event_id:str,*,session_id:str,durable_drive_strength:float=.5,transient_urgency:float=.5,importance:float=.5,uncertainty:float=.5,false_urgency_risk:float=.5,overlap_strength:float=.0,recovery_constraint:float=.0,operator_review_required:bool=False,force_unresolved:bool=False):
  clamp=lambda x:max(0.0,min(float(x),1.0)); durable=clamp(durable_drive_strength); transient=clamp(transient_urgency); importance=clamp(importance); uncertainty=clamp(uncertainty); false_risk=clamp(false_urgency_risk); overlap=clamp(overlap_strength); recovery=clamp(recovery_constraint)
  row=next((x for x in self.sessions.snapshot().get("sessions",[]) if x.get("session_id")==session_id),None)
  if not row: raise ValueError("session required")
  if operator_review_required or row.get("operator_review_required"): outcome="requires_operator_review"; reason="operator_review_boundary"
  elif force_unresolved or uncertainty>.82: outcome="unresolved"; reason="uncertain_drive_support"
  elif false_risk>=.65 and transient>durable: outcome="decay_transient_urgency"; reason="false_urgency_restraint"
  elif recovery>=.7: outcome="defer_drive"; reason="recovery_constraint"
  elif overlap>=.75: outcome="merge_overlapping_drive"; reason="semantic_drive_overlap"
  elif durable>=.72 and importance>=.6 and uncertainty<=.55: outcome="prioritize_for_bounded_review"; reason="durable_drive_support"
  elif durable<.3 and transient<.3: outcome="deliberate_non_selection"; reason="insufficient_motivational_pressure"
  else: outcome="retain_drive"; reason="bounded_drive_retained_without_attention_selection"
  result=self.sessions.record_outcome(event_id,session_id=session_id,outcome=outcome,reason_code=reason)
  result["arbitration"]={"contract_version":CONTRACT_VERSION,"outcome":outcome,"reason":reason,"scores":{"durable_drive_strength":durable,"transient_urgency":transient,"importance":importance,"uncertainty":uncertainty,"false_urgency_risk":false_risk,"overlap_strength":overlap,"recovery_constraint":recovery},"attention_selected":False,"initiative_created":False,"message_sent":False,"notification_created":False,"proposal_created":False,"approval_granted":False,"authorization_granted":False,"external_action_executed":False,"provider_contacted":False,"browsing_performed":False}
  return result
 def inspection_summary(self):
  base=self.sessions.inspection_summary(); return {"ok":True,"contract_version":CONTRACT_VERSION,"session_contract_version":SESSION_VERSION,"outcome_counts":base.get("outcome_counts",{}),"recent_sessions":base.get("recent_sessions",[]),"authority_boundary":deepcopy(base.get("authority_boundary",{})),"attention_selected":False,"initiative_created":False,"message_sent":False,"notification_created":False,"proposal_created":False,"approval_granted":False,"authorization_granted":False,"external_action_executed":False,"provider_contacted":False,"browsing_performed":False,"hidden_reasoning_exposed":False,"runtime_mutated":False}
def build_motivational_drive_arbitration_inspection(runtime_root=None): return MotivationalDriveArbitrator(runtime_root).inspection_summary()
