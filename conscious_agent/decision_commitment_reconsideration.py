from __future__ import annotations
"""Deterministic reconsideration, decay, expiry, and resumption for decision commitments."""
from copy import deepcopy
from decision_commitment_lifecycle import DecisionCommitmentStore, _clean, _digest
CONTRACT_VERSION="v1114.4"
class DecisionCommitmentReconsideration:
 def __init__(self,runtime_root=None,*,clock=None): self.store=DecisionCommitmentStore(runtime_root,clock=clock)
 def reconsider(self,event_id:str,*,commitment_id:str,evidence_support:float=.5,conflict_score:float=0.0,stale:bool=False,expired:bool=False):
  support=max(0.0,min(float(evidence_support),1.0)); conflict=max(0.0,min(float(conflict_score),1.0))
  if expired: outcome="expired"; reason="expiry_due"
  elif conflict>=.75: outcome="suspended"; reason="material_conflict"
  elif stale and support<.5: outcome="retired"; reason="stale_and_unsupported"
  elif support>=.6 and conflict<.5: outcome="active"; reason="bounded_reaffirmation"
  else: outcome="suspended"; reason="uncertain_reconsideration"
  return self.store.transition(event_id,commitment_id=commitment_id,outcome=outcome,reason_code=reason)
 def inspection_summary(self):
  x=self.store.inspection_summary(); x.update({"contract_version":CONTRACT_VERSION,"deterministic":True,"latest_event_not_automatic_winner":True,"missing_feedback_is_positive":False,"authority_changed":False}); return x
def build_decision_commitment_reconsideration_inspection(runtime_root=None): return DecisionCommitmentReconsideration(runtime_root).inspection_summary()
