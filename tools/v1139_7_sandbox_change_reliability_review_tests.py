from pathlib import Path
import json,tempfile
from conscious_agent.sandbox_change_outcome_lineage import SandboxChangeOutcomeLineageStore
from conscious_agent.sandbox_change_reliability_review import SandboxChangeReliabilityReviewStore
def main():
 with tempfile.TemporaryDirectory() as td:
  root=Path(td)/"cognition";root.mkdir(parents=True)
  (root/"sandbox_change_arbitration.json").write_text(json.dumps({"outcomes":[{"arbitration_id":"a1","candidate_id":"c1","eligibility_ids":["e1"],"deficiency_candidate_ids":["d1"],"change_categories":["bounded_source_change"],"component_ids":["component:x"],"project_digests":["p"],"scope_digests":["s"],"evidence_ids":["ev"],"outcome":"sandbox_change_supported"}]}))
  lid=SandboxChangeOutcomeLineageStore(root).record("l",arbitration_id="a1")["lineage_id"]; store=SandboxChangeReliabilityReviewStore(root)
  assert store.review("r1",lineage_id=lid,false_positive_count=2)["finding"]=="repeated_false_positive"
  assert store.review("r2",lineage_id=lid,missed_signal_count=2)["finding"]=="possible_missed_sandbox_change"
  assert store.review("r3",lineage_id=lid,containment_drift=True)["finding"]=="containment_drift"
  assert store.review("r4",lineage_id=lid,isolation_drift=True)["finding"]=="isolation_drift"
  assert store.review("r5",lineage_id=lid,resource_budget_drift=True)["finding"]=="resource_budget_drift"
  summary=store.inspection_summary(); assert not any(summary["authority_boundary"].values()) and not summary["patch_text_exposed"]
 print("v1139.7 sandbox change reliability review: 5/5 passed")
if __name__=="__main__": main()
