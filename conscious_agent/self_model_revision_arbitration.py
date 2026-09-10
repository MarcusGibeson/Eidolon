from __future__ import annotations
"""v1120.4 deterministic bounded arbitration among identity and self-model revision responses."""
from copy import deepcopy
from self_model_revision_deliberation import SelfModelRevisionDeliberationStore, CONTRACT_VERSION as SESSION_VERSION
CONTRACT_VERSION="v1120.4"
class SelfModelRevisionArbitrator:
 def __init__(self,runtime_root=None): self.sessions=SelfModelRevisionDeliberationStore(runtime_root)
 def arbitrate(self,event_id:str,*,session_id:str,support_strength:float=.5,contradiction_strength:float=.0,temporal_scope_mismatch:float=.0,persistence_mismatch:float=.0,confidence_mismatch:float=.0,evidence_quality:float=.5,uncertainty:float=.5,replacement_supported:bool=False,temporary_state_supported:bool=False,operator_review_required:bool=False,force_unresolved:bool=False):
  clamp=lambda x:max(0.0,min(float(x),1.0)); support=clamp(support_strength); contradiction=clamp(contradiction_strength); temporal=clamp(temporal_scope_mismatch); persistence=clamp(persistence_mismatch); mismatch=clamp(confidence_mismatch); quality=clamp(evidence_quality); uncertainty=clamp(uncertainty)
  row=next((x for x in self.sessions.snapshot().get("sessions",[]) if x.get("session_id")==session_id),None)
  if not row: raise ValueError("session required")
  if operator_review_required or row.get("operator_review_required"): outcome="requires_operator_review"; reason="operator_review_boundary"
  elif force_unresolved or quality<.35 or uncertainty>.82: outcome="unresolved"; reason="insufficient_or_uncertain_support"
  elif temporary_state_supported and max(temporal,persistence)>.72 and quality>=.6: outcome="reclassify_temporary_state"; reason="temporary_state_scope_supported"
  elif replacement_supported and contradiction>.72 and quality>=.68: outcome="replace_candidate"; reason="supported_replacement_candidate"
  elif contradiction>.82 and quality>=.65: outcome="suspend"; reason="strong_supported_contradiction"
  elif mismatch>.7 or (contradiction>.55 and support<.45): outcome="weaken"; reason="confidence_exceeds_structural_support"
  elif max(contradiction,temporal,persistence,mismatch)<.3 and support>=.55: outcome="retain"; reason="claim_support_remains_coherent"
  else: outcome="deliberate_no_revision"; reason="bounded_non_revision_preserved"
  result=self.sessions.record_outcome(event_id,session_id=session_id,outcome=outcome,reason_code=reason)
  result["arbitration"]={"contract_version":CONTRACT_VERSION,"outcome":outcome,"reason":reason,"scores":{"support":support,"contradiction":contradiction,"temporal_scope_mismatch":temporal,"persistence_mismatch":persistence,"confidence_mismatch":mismatch,"evidence_quality":quality,"uncertainty":uncertainty},"identity_revised":False,"self_model_revised":False,"temporary_state_promoted":False,"proposal_created":False,"approval_granted":False,"authorization_granted":False,"external_action_executed":False}
  return result
 def inspection_summary(self):
  base=self.sessions.inspection_summary(); return {"ok":True,"contract_version":CONTRACT_VERSION,"session_contract_version":SESSION_VERSION,"outcome_counts":base.get("outcome_counts",{}),"recent_sessions":base.get("recent_sessions",[]),"authority_boundary":deepcopy(base.get("authority_boundary",{})),"identity_revised":False,"self_model_revised":False,"temporary_state_promoted":False,"decision_committed":False,"proposal_created":False,"approval_granted":False,"authorization_granted":False,"external_action_executed":False,"hidden_reasoning_exposed":False,"runtime_mutated":False}
def build_self_model_revision_arbitration_inspection(runtime_root=None): return SelfModelRevisionArbitrator(runtime_root).inspection_summary()
