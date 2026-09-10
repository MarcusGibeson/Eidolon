from pathlib import Path
import json,tempfile
from conscious_agent.specification_outcome_lineage import SpecificationOutcomeLineageStore

def main():
 with tempfile.TemporaryDirectory() as td:
  r=Path(td)/"cognition";r.mkdir(parents=True)
  (r/"specification_arbitration.json").write_text(json.dumps({"outcomes":[{"arbitration_id":"a1","candidate_id":"c1","eligibility_ids":["e1"],"deficiency_candidate_ids":["d1"],"specification_categories":["reliability_specification"],"component_ids":["component:x"],"project_digests":["p"],"scope_digests":["s"],"evidence_ids":["ev"],"outcome":"specification_supported"}]}))
  store=SpecificationOutcomeLineageStore(r); out=store.record("l",arbitration_id="a1",predecessor_lineage_ids=["prior"],continuity_context="restart")
  assert out["ok"] and not out["idempotent"]
  assert store.record("l",arbitration_id="a1")["idempotent"]
  row=store.inspection_summary()["recent_lineage"][-1]; assert row["arbitration_id"]=="a1" and row["predecessor_lineage_ids"]==["prior"]
  assert not any(store.inspection_summary()["authority_boundary"].values()) and not store.inspection_summary()["specification_text_exposed"]
 print("v1137.6 specification outcome lineage: 4/4 passed")
if __name__=="__main__": main()
