from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile

from conscious_agent.json_storage import write_json_atomic
from conscious_agent.sandbox_repair_work_orders import SandboxRepairWorkOrderStore, STATES


checks = []
def check(name, value):
    checks.append((name, bool(value)))
    print(("PASS" if value else "FAIL"), name)


with tempfile.TemporaryDirectory() as td:
    root = Path(td) / "cognition"
    root.mkdir(parents=True)
    expiry = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat().replace("+00:00", "Z")
    write_json_atomic(root / "repair_implementation_eligibility.json", {
        "schema_version": "1", "contract_version": "v1141.0", "processed_events": [], "revision": 1, "updated_at": "", "authority_boundary": {},
        "eligibility_records": [{
            "eligibility_id": "repair-elig-1", "state": "eligible", "validity_state": "bounded_valid", "bounded_valid_until": expiry,
            "reviewed_artifact_set_digest": "a" * 64, "approval_id": "approval-1", "authorization_id": "authorization-1",
            "approval_artifact_set_digest": "a" * 64, "authorization_artifact_set_digest": "a" * 64,
            "v1140_arbitration_id": "ix-arb-1", "v1140_deliberation_session_id": "ix-session-1", "v1140_candidate_id": "ix-candidate-1", "v1140_eligibility_ids": ["ix-elig-1"],
            "sandbox_change_arbitration_ids": ["sc-arb-1"], "sandbox_change_candidate_ids": ["sc-candidate-1"], "sandbox_change_eligibility_ids": ["sc-elig-1"],
            "test_plan_candidate_ids": ["tp-1"], "test_plan_eligibility_ids": ["tp-e-1"], "specification_candidate_ids": ["spec-1"], "proposal_candidate_ids": ["proposal-1"], "deficiency_candidate_ids": ["def-1"],
            "allowed_operation_categories": ["replace_bounded_component"], "allowed_execution_modes": ["materialize_isolated_workspace", "apply_candidate_change"],
            "component_ids": ["component.alpha"], "path_digests": ["d" * 64], "workspace_manifest_digests": ["w" * 64],
            "isolation_profile_ids": ["isolation.strict"], "command_profile_ids": ["commands.repair"], "resource_budget_ids": ["budget.small"],
            "containment_requirements": ["os_enforced_isolation"], "reversibility_requirements": ["discardable_workspace"],
            "recovery_requirements": ["restart_reconciliation"], "rollback_requirements": ["discard_candidate_workspace"], "prerequisite_ids": []
        }]
    }, expected_type=dict, sort_keys=True)
    store = SandboxRepairWorkOrderStore(root)
    result = store.register("event-1", eligibility_id="repair-elig-1", test_profile_id="tests.focused", time_budget_seconds=900, owner_id="operator", tab_session_id="tab-a")
    row = store.snapshot()["work_orders"][0]
    check("ready", result["state"] == "ready_for_operator_confirmed_materialization")
    check("exact binding", row["reviewed_artifact_set_digest"] == row["approval_artifact_set_digest"] == row["authorization_artifact_set_digest"])
    check("upstream lineage", row["v1140_arbitration_id"] == "ix-arb-1" and row["test_plan_candidate_ids"] == ["tp-1"] and row["deficiency_candidate_ids"] == ["def-1"])
    check("immutable bounds", row["immutable_authorized_bounds"] and row["authorized_bounds_match"] and row["command_profile_ids"] == ["commands.repair"])
    check("bounded token identifier", row["execution_token_id"].startswith("repair-execution-token-") and not row["execution_token_activated"] and not row["execution_token_grants_authority"])
    check("no materialization", not row["sandbox_id"] and not row["workspace_id"] and not row["patch_digest"])
    duplicate = store.register("event-2", eligibility_id="repair-elig-1", test_profile_id="tests.focused", time_budget_seconds=900, owner_id="operator", tab_session_id="tab-b")
    check("cross-tab duplicate", duplicate["work_order_id"] == result["work_order_id"] and duplicate["status"].endswith("reused"))
    broadened = store.register("event-3", eligibility_id="repair-elig-1", test_profile_id="tests.focused", time_budget_seconds=900, requested_operation_categories=["replace_bounded_component", "install_release"])
    check("scope broadening suppressed", broadened["state"] == "suppressed")
    claimed = store.register("event-4", eligibility_id="repair-elig-1", test_profile_id="tests.focused.claimed", time_budget_seconds=900, worker_claim_id="claim-1", preexisting_claim=True)
    check("preexisting claim only", claimed["state"] == "claimed" and not store.snapshot()["work_orders"][-1]["claim_created_by_work_order"])
    check("recognized lifecycle", {"active", "suppressed", "deferred", "awaiting_prerequisite", "awaiting_approval", "awaiting_authorization", "ready_for_operator_confirmed_materialization", "claimed", "expired", "superseded", "retracted", "retired"} <= STATES)
    check("authority inert", not any(store.inspection_summary()["authority_boundary"].values()))

assert all(value for _, value in checks)
print(f"RESULT {sum(value for _, value in checks)}/{len(checks)}")
