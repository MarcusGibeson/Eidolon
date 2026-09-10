from pathlib import Path
import tempfile
from conscious_agent.objective_progress_evidence import ObjectiveProgressLedger
class StubObjectives:
 def snapshot(self):return {"objectives":[{"objective_id":"o1"}]}
class StubMilestones:
 def snapshot(self):return {"milestones":[{"milestone_id":"m1","objective_id":"o1"}]}
def main():
 root=Path(tempfile.mkdtemp())/"cognition";s=ObjectiveProgressLedger(root);s.objectives=StubObjectives();s.milestones=StubMilestones();a=s.record("e1",objective_id="o1",milestone_id="m1",evidence_type="explicit_user_update",evidence_id="u1",claimed_state="partial");b=s.record("e2",objective_id="o1",milestone_id="m1",evidence_type="explicit_user_update",evidence_id="u1",claimed_state="partial");c=s.record("e3",objective_id="o1",evidence_type="bounded_reflection",evidence_id="r1",claimed_state="completed");d=s.record("e4",objective_id="o1",evidence_type="bounded_reflection",evidence_id="r2",claimed_state="completed",criteria_satisfied=["criterion"]);i=s.inspection_summary();tests=[a["status"]=="progress_recorded",b["status"]=="duplicate_evidence_ignored",c["result"]["reason"]=="completion_evidence_insufficient",d["status"]=="progress_recorded",i["evidence_count"]==2,i["completed_claim_count"]==1,i["contract_version"]=="v1109.4",not any(i["authority_boundary"].values())]
 print(f"v1109.4 objective progress evidence: {sum(tests)}/{len(tests)} passed");return 0 if all(tests) else 1
if __name__=='__main__':raise SystemExit(main())
