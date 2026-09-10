from __future__ import annotations
"""Deterministic conflict, replacement, and retirement handling for decision commitments."""
from copy import deepcopy
from decision_commitment_lifecycle import DecisionCommitmentStore, _clean, _digest
from json_storage import write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
CONTRACT_VERSION="v1114.5"
class DecisionCommitmentConflictResolver:
 def __init__(self,runtime_root=None,*,clock=None): self.store=DecisionCommitmentStore(runtime_root,clock=clock); self.path=self.store.path; self.clock=self.store.clock
 def resolve(self,event_id:str,*,commitment_ids:list[str],priority:dict[str,float]|None=None,confidence:dict[str,float]|None=None):
  ids=sorted({_clean(x,220) for x in commitment_ids if _clean(x,220)}); priority=priority or {}; confidence=confidence or {}
  if len(ids)<2: raise ValueError("at least two commitment_ids required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self.store._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   rows=[x for x in s["commitments"] if x.get("commitment_id") in ids and x.get("active")]
   if len(rows)<2: result={"status":"conflict_unresolved","reason":"insufficient_active_commitments","winner_id":"","replaced_ids":[]}
   else:
    rows.sort(key=lambda x:(-max(0,min(float(priority.get(x["commitment_id"],.5)),1)),-max(0,min(float(confidence.get(x["commitment_id"],.5)),1)),str(x.get("created_at","")),x["commitment_id"])); winner=rows[0]; now=self.clock(); losers=rows[1:]
    for row in losers:
     row["active"]=False; row["lifecycle"]="replaced"; row["replaced_by_commitment_id"]=winner["commitment_id"]; row["updated_at"]=now; row["history"].append({"outcome":"replaced","reason_code":"deterministic_conflict_resolution","event_digest":_digest(event_id),"occurred_at":now,"content_free":True})
    result={"status":"conflict_resolved","winner_id":winner["commitment_id"],"replaced_ids":[x["commitment_id"] for x in losers],"intention_formed":False,"proposal_created":False,"authority_granted":False}
   now=self.clock(); s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-1024:]; s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  x=self.store.inspection_summary(); x.update({"contract_version":CONTRACT_VERSION,"deterministic":True,"replaced_commitment_count":x["lifecycle_counts"].get("replaced",0),"intention_formed":False,"proposal_created":False,"authority_changed":False}); return x
def build_decision_commitment_conflict_inspection(runtime_root=None): return DecisionCommitmentConflictResolver(runtime_root).inspection_summary()
