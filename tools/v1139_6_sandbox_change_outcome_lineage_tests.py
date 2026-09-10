from pathlib import Path
import json,tempfile
from conscious_agent.sandbox_change_outcome_lineage import SandboxChangeOutcomeLineageStore
def main():
 with tempfile.TemporaryDirectory() as td:
  root=Path(td)/"cognition";root.mkdir(parents=True)
  (root/"sandbox_change_arbitration.json").write_text(json.dumps({"outcomes":[{"arbitration_id":"a1","candidate_id":"c1","eligibility_ids":["e1"],"deficiency_candidate_ids":["d1"],"change_categories":["bounded_source_change"],"component_ids":["component:x"],"project_digests":["p"],"scope_digests":["s"],"evidence_ids":["ev"],"outcome":"sandbox_change_supported"}]}))
  store=SandboxChangeOutcomeLineageStore(root); out=store.record("l",arbitration_id="a1",predecessor_lineage_ids=["prior"],continuity_context="restart")
  assert out["ok"] and not out["idempotent"]
  assert store.record("l",arbitration_id="a1")["idempotent"]
  row=store.inspection_summary()["recent_lineage"][-1]; assert row["arbitration_id"]=="a1" and row["predecessor_lineage_ids"]==["prior"]
  assert not any(store.inspection_summary()["authority_boundary"].values()) and not store.inspection_summary()["patch_text_exposed"]
 print("v1139.6 sandbox change outcome lineage: 4/4 passed")
if __name__=="__main__": main()
