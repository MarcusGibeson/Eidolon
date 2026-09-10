from pathlib import Path
import tempfile
from conscious_agent.objective_milestone_decomposition import ObjectiveMilestoneStore
class StubObjectives:
 def snapshot(self):return {"objectives":[{"objective_id":"o1","active_influence":True,"intention_id":"i1","subject_digest":"s1"}]}
def main():
 root=Path(tempfile.mkdtemp())/"cognition";store=ObjectiveMilestoneStore(root);store.objectives=StubObjectives();a=store.decompose("e1",objective_id="o1",milestones=["first","second"]);b=store.decompose("e1",objective_id="o1",milestones=["first","second"]);c=store.decompose("e2",objective_id="o1",milestones=[]);snap=store.snapshot();tests=[a["status"]=="milestones_registered",len(a["result"]["milestone_ids"])==2,b["idempotent"] is True,c["status"]=="deliberate_no_decomposition",all(x["depth"]==1 for x in snap["milestones"]),all(not x["authority_granted"] for x in snap["milestones"]),store.inspection_summary()["contract_version"]=="v1109.3"]
 print(f"v1109.3 objective milestone decomposition: {sum(tests)}/{len(tests)} passed");return 0 if all(tests) else 1
if __name__=='__main__':raise SystemExit(main())
