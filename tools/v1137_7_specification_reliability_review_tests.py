from pathlib import Path
import json,tempfile
from conscious_agent.specification_outcome_lineage import SpecificationOutcomeLineageStore
from conscious_agent.specification_reliability_review import SpecificationReliabilityReviewStore

def main():
 with tempfile.TemporaryDirectory() as td:
  r=Path(td)/"cognition";r.mkdir(parents=True)
  (r/"specification_arbitration.json").write_text(json.dumps({"outcomes":[{"arbitration_id":"a1","candidate_id":"c1","eligibility_ids":["e1"],"deficiency_candidate_ids":["d1"],"specification_categories":["reliability_specification"],"component_ids":["component:x"],"project_digests":["p"],"scope_digests":["s"],"evidence_ids":["ev"],"outcome":"specification_supported"}]}))
  lid=SpecificationOutcomeLineageStore(r).record("l",arbitration_id="a1")["lineage_id"]; store=SpecificationReliabilityReviewStore(r)
  assert store.review("r1",lineage_id=lid,false_positive_count=2)["finding"]=="repeated_false_positive"
  assert store.review("r2",lineage_id=lid,missed_signal_count=2)["finding"]=="possible_missed_specification"
  assert store.review("r3",lineage_id=lid,scope_drift=True)["finding"]=="scope_drift"
  summary=store.inspection_summary(); assert not any(summary["authority_boundary"].values()) and not summary["specification_text_exposed"]
 print("v1137.7 specification reliability review: 4/4 passed")
if __name__=="__main__": main()
