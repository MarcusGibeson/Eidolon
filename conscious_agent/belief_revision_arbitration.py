from __future__ import annotations
"""v1118.4 deterministic bounded arbitration among belief revision outcomes."""
from copy import deepcopy
from belief_revision_deliberation import BeliefRevisionDeliberationStore, CONTRACT_VERSION as SESSION_VERSION
CONTRACT_VERSION="v1118.4"
class BeliefRevisionArbitrator:
 def __init__(self,runtime_root=None): self.sessions=BeliefRevisionDeliberationStore(runtime_root)
 def arbitrate(self,event_id:str,*,session_id:str,support_strength:float=.5,contradiction_strength:float=.5,evidence_quality:float=.5,uncertainty:float=.5,replacement_supported:bool=False,operator_review_required:bool=False,force_unresolved:bool=False):
  clamp=lambda x:max(0.0,min(float(x),1.0)); support=clamp(support_strength); contradiction=clamp(contradiction_strength); quality=clamp(evidence_quality); uncertainty=clamp(uncertainty)
  row=next((x for x in self.sessions.snapshot().get("sessions",[]) if x.get("session_id")==session_id),None)
  if not row: raise ValueError("session required")
  if operator_review_required or row.get("operator_review_required"): outcome="requires_operator_review"; reason="operator_review_boundary"
  elif force_unresolved or quality<.35 or uncertainty>.8: outcome="unresolved"; reason="insufficient_or_uncertain_evidence"
  elif contradiction>.78 and replacement_supported and quality>=.65: outcome="replace"; reason="strong_supported_replacement"
  elif contradiction>.72: outcome="suspend"; reason="strong_contradiction"
  elif contradiction-support>.22: outcome="weaken"; reason="contradiction_outweighs_support"
  elif support-contradiction>.28 and quality>=.65: outcome="strengthen"; reason="support_outweighs_contradiction"
  elif abs(support-contradiction)<.08: outcome="deliberate_no_revision"; reason="balanced_evidence"
  else: outcome="retain"; reason="bounded_retention"
  result=self.sessions.record_outcome(event_id,session_id=session_id,outcome=outcome,reason_code=reason)
  result["arbitration"]={"contract_version":CONTRACT_VERSION,"outcome":outcome,"reason":reason,"scores":{"support":support,"contradiction":contradiction,"evidence_quality":quality,"uncertainty":uncertainty},"belief_revised":False,"proposal_created":False,"approval_granted":False,"authorization_granted":False,"external_action_executed":False}
  return result
 def inspection_summary(self):
  base=self.sessions.inspection_summary(); return {"ok":True,"contract_version":CONTRACT_VERSION,"session_contract_version":SESSION_VERSION,"outcome_counts":base.get("outcome_counts",{}),"recent_sessions":base.get("recent_sessions",[]),"authority_boundary":deepcopy(base.get("authority_boundary",{})),"belief_revised":False,"decision_committed":False,"proposal_created":False,"approval_granted":False,"authorization_granted":False,"external_action_executed":False,"hidden_reasoning_exposed":False,"runtime_mutated":False}
def build_belief_revision_arbitration_inspection(runtime_root=None): return BeliefRevisionArbitrator(runtime_root).inspection_summary()
