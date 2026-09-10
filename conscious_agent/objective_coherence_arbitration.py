from __future__ import annotations
"""v1121.4 deterministic bounded arbitration among goal-coherence responses."""
from copy import deepcopy
from objective_coherence_deliberation import ObjectiveCoherenceDeliberationStore, CONTRACT_VERSION as SESSION_VERSION
CONTRACT_VERSION="v1121.4"
class ObjectiveCoherenceArbitrator:
 def __init__(self,runtime_root=None): self.sessions=ObjectiveCoherenceDeliberationStore(runtime_root)
 def arbitrate(self,event_id:str,*,session_id:str,objective_conflict:float=.0,dependency_conflict:float=.0,priority_mismatch:float=.0,milestone_infeasibility:float=.0,drift_strength:float=.0,abandonment_ambiguity:float=.0,evidence_quality:float=.5,uncertainty:float=.5,operator_review_required:bool=False,force_unresolved:bool=False):
  clamp=lambda x:max(0.0,min(float(x),1.0)); oc=clamp(objective_conflict); dc=clamp(dependency_conflict); pm=clamp(priority_mismatch); mi=clamp(milestone_infeasibility); drift=clamp(drift_strength); aa=clamp(abandonment_ambiguity); quality=clamp(evidence_quality); uncertainty=clamp(uncertainty)
  row=next((x for x in self.sessions.snapshot().get("sessions",[]) if x.get("session_id")==session_id),None)
  if not row: raise ValueError("session required")
  if operator_review_required or row.get("operator_review_required"): outcome="requires_operator_review"; reason="operator_review_boundary"
  elif force_unresolved or quality<.35 or uncertainty>.82: outcome="unresolved"; reason="insufficient_or_uncertain_support"
  elif aa>.72 and quality>=.6: outcome="clarify_abandonment"; reason="abandonment_state_requires_clarification"
  elif dc>.72 and quality>=.65: outcome="dependency_repair_candidate"; reason="dependency_conflict_dominant"
  elif mi>.72 and quality>=.65: outcome="milestone_revision_candidate"; reason="milestone_feasibility_mismatch"
  elif max(pm,oc,drift)>.7 and quality>=.65: outcome="reprioritization_candidate"; reason="priority_or_objective_coherence_mismatch"
  elif max(oc,dc,pm,mi,drift,aa)<.3: outcome="retain"; reason="objective_structure_remains_coherent"
  else: outcome="deliberate_no_repair"; reason="bounded_non_repair_preserved"
  result=self.sessions.record_outcome(event_id,session_id=session_id,outcome=outcome,reason_code=reason)
  result["arbitration"]={"contract_version":CONTRACT_VERSION,"outcome":outcome,"reason":reason,"scores":{"objective_conflict":oc,"dependency_conflict":dc,"priority_mismatch":pm,"milestone_infeasibility":mi,"drift_strength":drift,"abandonment_ambiguity":aa,"evidence_quality":quality,"uncertainty":uncertainty},"objectives_reprioritized":False,"objective_abandoned":False,"dependency_modified":False,"milestone_modified":False,"proposal_created":False,"approval_granted":False,"authorization_granted":False,"external_action_executed":False}
  return result
 def inspection_summary(self):
  base=self.sessions.inspection_summary(); return {"ok":True,"contract_version":CONTRACT_VERSION,"session_contract_version":SESSION_VERSION,"outcome_counts":base.get("outcome_counts",{}),"recent_sessions":base.get("recent_sessions",[]),"authority_boundary":deepcopy(base.get("authority_boundary",{})),"objectives_reprioritized":False,"objective_abandoned":False,"dependency_modified":False,"milestone_modified":False,"decision_committed":False,"proposal_created":False,"approval_granted":False,"authorization_granted":False,"external_action_executed":False,"hidden_reasoning_exposed":False,"runtime_mutated":False}
def build_objective_coherence_arbitration_inspection(runtime_root=None): return ObjectiveCoherenceArbitrator(runtime_root).inspection_summary()
