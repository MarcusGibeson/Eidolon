from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile

from conscious_agent.json_storage import write_json_atomic
from conscious_agent.repair_implementation_eligibility import RepairImplementationEligibilityStore


def seed(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    write_json_atomic(root / "isolated_sandbox_execution_arbitration.json", {
        "schema_version": "1", "contract_version": "v1140.4", "processed_events": [], "revision": 1, "updated_at": "", "authority_boundary": {},
        "outcomes": [{
            "arbitration_id": "ix-arb-1", "session_id": "ix-session-1", "candidate_id": "ix-candidate-1", "eligibility_ids": ["ix-elig-1"],
            "deficiency_candidate_ids": ["def-1"], "execution_modes": ["materialize_isolated_workspace", "apply_candidate_change"],
            "component_ids": ["component.alpha"], "project_digests": ["p" * 64], "scope_digests": ["s" * 64],
            "outcome": "isolated_sandbox_execution_supported"
        }]
    }, expected_type=dict, sort_keys=True)
    write_json_atomic(root / "isolated_sandbox_execution_deliberation_sessions.json", {
        "schema_version": "1", "contract_version": "v1140.3", "processed_events": [], "revision": 1, "updated_at": "", "authority_boundary": {},
        "sessions": [{"session_id": "ix-session-1", "candidate_id": "ix-candidate-1", "eligibility_ids": ["ix-elig-1"], "state": "open"}]
    }, expected_type=dict, sort_keys=True)
    write_json_atomic(root / "isolated_sandbox_execution_candidates.json", {
        "schema_version": "1", "contract_version": "v1140.1", "processed_events": [], "revision": 1, "updated_at": "", "authority_boundary": {},
        "candidates": [{
            "candidate_id": "ix-candidate-1", "eligibility_ids": ["ix-elig-1"], "sandbox_change_arbitration_ids": ["sc-arb-1"],
            "sandbox_change_candidate_ids": ["sc-candidate-1"], "sandbox_change_eligibility_ids": ["sc-elig-1"], "deficiency_candidate_ids": ["def-1"],
            "component_ids": ["component.alpha"], "project_digests": ["p" * 64], "scope_digests": ["s" * 64],
            "execution_modes": ["materialize_isolated_workspace", "apply_candidate_change"], "isolation_profile_ids": ["isolation.strict"],
            "workspace_manifest_digests": ["w" * 64], "resource_budget_ids": ["budget.small"], "command_profile_ids": ["commands.repair"],
            "prerequisite_ids": [], "state": "active"
        }]
    }, expected_type=dict, sort_keys=True)
    write_json_atomic(root / "isolated_sandbox_execution_eligibility.json", {
        "schema_version": "1", "contract_version": "v1140.0", "processed_events": [], "revision": 1, "updated_at": "", "authority_boundary": {},
        "eligibility_records": [{
            "eligibility_id": "ix-elig-1", "sandbox_change_arbitration_id": "sc-arb-1", "sandbox_change_candidate_id": "sc-candidate-1",
            "sandbox_change_eligibility_ids": ["sc-elig-1"], "deficiency_candidate_ids": ["def-1"], "execution_modes": ["materialize_isolated_workspace", "apply_candidate_change"],
            "component_ids": ["component.alpha"], "isolation_profile_id": "isolation.strict", "workspace_manifest_digest": "w" * 64,
            "resource_budget_id": "budget.small", "command_profile_id": "commands.repair", "prerequisite_ids": [], "state": "eligible"
        }]
    }, expected_type=dict, sort_keys=True)
    write_json_atomic(root / "sandbox_change_candidates.json", {
        "schema_version": "1", "contract_version": "v1139.1", "processed_events": [], "revision": 1, "updated_at": "", "authority_boundary": {},
        "candidates": [{
            "candidate_id": "sc-candidate-1", "eligibility_ids": ["sc-elig-1"], "arbitration_ids": ["tp-arb-1"],
            "test_plan_candidate_ids": ["tp-candidate-1"], "test_plan_eligibility_ids": ["tp-elig-1"],
            "specification_candidate_ids": ["spec-candidate-1"], "proposal_candidate_ids": ["proposal-candidate-1"],
            "deficiency_candidate_ids": ["def-1"], "component_ids": ["component.alpha"], "path_digests": ["d" * 64],
            "operation_categories": ["replace_bounded_component"], "state": "active"
        }]
    }, expected_type=dict, sort_keys=True)


checks = []
def check(name, value):
    checks.append((name, bool(value)))
    print(("PASS" if value else "FAIL"), name)


with tempfile.TemporaryDirectory() as td:
    root = Path(td) / "cognition"
    seed(root)
    store = RepairImplementationEligibilityStore(root)
    lineage = store.resolve_lineage("ix-arb-1")
    expiry = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat().replace("+00:00", "Z")
    approval = {"id": "approval-1", "status": "approved", "reviewed_artifact_set_digest": lineage["reviewed_artifact_set_digest"], "expires_at": expiry}
    authorization = {"id": "authorization-1", "status": "authorized", "approval_id": "approval-1", "reviewed_artifact_set_digest": lineage["reviewed_artifact_set_digest"], "expires_at": expiry}

    waiting = store.register("event-wait", arbitration_id="ix-arb-1", approval_record=approval, authorization_record=None, operator_review_required=False)
    check("authorization separated", waiting["state"] == "awaiting_authorization")

    registered = store.register("event-valid", arbitration_id="ix-arb-1", approval_record=approval, authorization_record=authorization, operator_review_required=False, tab_session_id="tab-a")
    row = next(item for item in store.snapshot()["eligibility_records"] if item["eligibility_id"] == registered["eligibility_id"])
    check("eligible", registered["state"] == "eligible")
    check("exact v1140 lineage", row["v1140_arbitration_id"] == "ix-arb-1" and row["v1140_deliberation_session_id"] == "ix-session-1")
    check("exact upstream lineage", row["test_plan_candidate_ids"] == ["tp-candidate-1"] and row["specification_candidate_ids"] == ["spec-candidate-1"] and row["proposal_candidate_ids"] == ["proposal-candidate-1"])
    check("artifact binding", row["approval_binding_valid"] and row["authorization_binding_valid"] and row["reviewed_artifact_set_digest"] == lineage["reviewed_artifact_set_digest"])
    check("bounded authority", row["bounded_valid_until"] and not row["sandbox_id"] and not row["patch_digest"])
    duplicate = store.register("event-duplicate", arbitration_id="ix-arb-1", approval_record=approval, authorization_record=authorization, operator_review_required=False, tab_session_id="tab-b")
    check("cross-tab duplicate", duplicate["eligibility_id"] == registered["eligibility_id"] and duplicate["status"].endswith("reused"))
    mismatched = dict(authorization); mismatched["reviewed_artifact_set_digest"] = "0" * 64
    suppressed = store.register("event-mismatch", arbitration_id="ix-arb-1", approval_record=approval, authorization_record=mismatched, operator_review_required=False)
    check("mismatch fails closed", suppressed["state"] == "suppressed")
    stale = store.register("event-stale", arbitration_id="ix-arb-1", approval_record=approval, authorization_record=authorization, operator_review_required=False, worker_generation=1, current_generation=2, contradiction_ids=["worker-generation-drift"])
    check("stale worker suppressed", stale["state"] == "suppressed")
    check("authority inert", not any(store.inspection_summary()["authority_boundary"].values()))

assert all(value for _, value in checks)
print(f"RESULT {sum(value for _, value in checks)}/{len(checks)}")
