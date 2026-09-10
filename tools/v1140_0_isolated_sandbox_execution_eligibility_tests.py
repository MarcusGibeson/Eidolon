from pathlib import Path
import tempfile
ROOT=Path(__file__).resolve().parents[1]
from conscious_agent.isolated_sandbox_execution_eligibility import IsolatedSandboxExecutionEligibilityStore
def seed_outcome(r):
 from conscious_agent.json_storage import write_json_atomic
 p=r/"sandbox_change_arbitration.json"
 write_json_atomic(p,{"schema_version":"1","contract_version":"v1139.4","outcomes":[{"arbitration_id":"arb-1","session_id":"sess-1","candidate_id":"change-cand-1","eligibility_ids":["change-elig-1"],"deficiency_candidate_ids":["def-1"],"change_categories":["source_repair"],"component_ids":["component.alpha"],"project_digests":["p"*64],"scope_digests":["s"*64],"evidence_ids":["e-1"],"outcome":"sandbox_change_supported"}],"processed_events":[],"revision":1,"updated_at":"","authority_boundary":{}},expected_type=dict,sort_keys=True)

checks=[]
def check(n,v): checks.append((n,bool(v))); print(("PASS" if v else "FAIL"),n)
with tempfile.TemporaryDirectory() as td:
 r=Path(td)/"cognition"; r.mkdir(parents=True); seed_outcome(r); s=IsolatedSandboxExecutionEligibilityStore(r)
 a=s.register("evt-1",arbitration_id="arb-1",execution_modes=["materialize_isolated_workspace","apply_candidate_change"],isolation_profile_id="strict-local",workspace_manifest_digest="m"*64,resource_budget_id="budget-1",command_profile_id="python-safe",operator_review_required=False,containment_confidence=.9,reversibility=.8)
 check("eligible",a["state"]=="eligible"); check("idempotent",s.register("evt-1",arbitration_id="arb-1",execution_modes=["materialize_isolated_workspace","apply_candidate_change"],isolation_profile_id="strict-local",workspace_manifest_digest="m"*64)["idempotent"]); row=s.snapshot()["eligibility_records"][0]; check("exact lineage",row["sandbox_change_arbitration_id"]=="arb-1" and row["sandbox_change_candidate_id"]=="change-cand-1"); check("content free",not row["sandbox_id"] and not row["patch_digest"]); check("authority inert",not any(s.inspection_summary()["authority_boundary"].values())); check("no execution",not s.inspection_summary()["commands_executed"] and not s.inspection_summary()["tests_executed"])
assert all(v for _,v in checks); print(f"RESULT {sum(v for _,v in checks)}/{len(checks)}")
