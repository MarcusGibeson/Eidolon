from pathlib import Path
import json,tempfile
from conscious_agent.test_plan_outcome_lineage import TestPlanOutcomeLineageStore
from conscious_agent.test_plan_reliability_review import TestPlanReliabilityReviewStore

def main():
 with tempfile.TemporaryDirectory() as td:
  r=Path(td)/"cognition";r.mkdir(parents=True)
  (r/"test_plan_arbitration.json").write_text(json.dumps({"outcomes":[{"arbitration_id":"a1","candidate_id":"c1","eligibility_ids":["e1"],"deficiency_candidate_ids":["d1"],"test_plan_categories":["regression_test_plan"],"component_ids":["component:x"],"project_digests":["p"],"scope_digests":["s"],"evidence_ids":["ev"],"outcome":"test_plan_supported"}]}))
  lid=TestPlanOutcomeLineageStore(r).record("l",arbitration_id="a1")["lineage_id"]; store=TestPlanReliabilityReviewStore(r)
  assert store.review("r1",lineage_id=lid,false_positive_count=2)["finding"]=="repeated_false_positive"
  assert store.review("r2",lineage_id=lid,missed_signal_count=2)["finding"]=="possible_missed_test_plan"
  assert store.review("r3",lineage_id=lid,coverage_drift=True)["finding"]=="coverage_drift"
  assert store.review("r4",lineage_id=lid,flaky_plan_count=2)["finding"]=="flaky_plan_pattern"
  summary=store.inspection_summary(); assert not any(summary["authority_boundary"].values()) and not summary["test_plan_text_exposed"]
 print("v1138.7 test plan reliability review: 5/5 passed")
if __name__=="__main__": main()
