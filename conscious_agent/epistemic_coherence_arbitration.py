from __future__ import annotations
"""v1119.4 deterministic bounded arbitration among epistemic-coherence responses."""
from copy import deepcopy
from epistemic_coherence_deliberation import EpistemicCoherenceDeliberationStore, CONTRACT_VERSION as SESSION_VERSION
CONTRACT_VERSION="v1119.4"
class EpistemicCoherenceArbitrator:
 def __init__(self,runtime_root=None): self.sessions=EpistemicCoherenceDeliberationStore(runtime_root)
 def arbitrate(self,event_id:str,*,session_id:str,contradiction_strength:float=.5,duplication_strength:float=.0,dependency_staleness:float=.0,confidence_mismatch:float=.0,evidence_quality:float=.5,uncertainty:float=.5,replacement_supported:bool=False,operator_review_required:bool=False,force_unresolved:bool=False):
  clamp=lambda x:max(0.0,min(float(x),1.0)); contradiction=clamp(contradiction_strength); duplication=clamp(duplication_strength); stale=clamp(dependency_staleness); mismatch=clamp(confidence_mismatch); quality=clamp(evidence_quality); uncertainty=clamp(uncertainty)
  row=next((x for x in self.sessions.snapshot().get("sessions",[]) if x.get("session_id")==session_id),None)
  if not row: raise ValueError("session required")
  if operator_review_required or row.get("operator_review_required"): outcome="requires_operator_review"; reason="operator_review_boundary"
  elif force_unresolved or quality<.35 or uncertainty>.82: outcome="unresolved"; reason="insufficient_or_uncertain_evidence"
  elif duplication>.82 and contradiction<.35: outcome="merge_candidate"; reason="strong_structural_duplication"
  elif stale>.78 and replacement_supported and quality>=.65: outcome="replace_dependency"; reason="stale_dependency_with_supported_replacement"
  elif contradiction>.8 and quality>=.65: outcome="suspend_claim"; reason="strong_supported_contradiction"
  elif mismatch>.72 and contradiction>.55: outcome="weaken_claim"; reason="confidence_exceeds_coherence_support"
  elif max(contradiction,duplication,stale,mismatch)<.35: outcome="deliberate_no_repair"; reason="low_coherence_risk"
  elif quality<.55 or uncertainty>.65: outcome="request_more_evidence"; reason="additional_evidence_warranted"
  else: outcome="retain_separation"; reason="bounded_separation_preserved"
  result=self.sessions.record_outcome(event_id,session_id=session_id,outcome=outcome,reason_code=reason)
  result["arbitration"]={"contract_version":CONTRACT_VERSION,"outcome":outcome,"reason":reason,"scores":{"contradiction":contradiction,"duplication":duplication,"dependency_staleness":stale,"confidence_mismatch":mismatch,"evidence_quality":quality,"uncertainty":uncertainty},"records_repaired":False,"proposal_created":False,"approval_granted":False,"authorization_granted":False,"external_action_executed":False}
  return result
 def inspection_summary(self):
  base=self.sessions.inspection_summary(); return {"ok":True,"contract_version":CONTRACT_VERSION,"session_contract_version":SESSION_VERSION,"outcome_counts":base.get("outcome_counts",{}),"recent_sessions":base.get("recent_sessions",[]),"authority_boundary":deepcopy(base.get("authority_boundary",{})),"records_repaired":False,"decision_committed":False,"proposal_created":False,"approval_granted":False,"authorization_granted":False,"external_action_executed":False,"hidden_reasoning_exposed":False,"runtime_mutated":False}
def build_epistemic_coherence_arbitration_inspection(runtime_root=None): return EpistemicCoherenceArbitrator(runtime_root).inspection_summary()
