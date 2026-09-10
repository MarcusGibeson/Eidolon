from pathlib import Path
from tempfile import TemporaryDirectory
from conscious_agent.prospective_planning_signals import ProspectivePlanningSignalStore

def main():
    with TemporaryDirectory() as directory:
        store = ProspectivePlanningSignalStore(Path(directory))
        active = store.register(
            "event-active", origin_ids=["goal-outcome-1"], source_categories=["accepted_goal_outcome"],
            goal_ids=["goal-1"], purpose_category="project_path", evidence_ids=["evidence-1"],
            importance=.8, expected_value=.75, alternative_ids=["alt-1"], counterfactual_ids=["cf-1"],
            stop_condition_ids=["stop-1"], scope_digest="a" * 64,
        )
        assert active["ok"] and active["result"]["state"] == "active"
        suppressed = store.register(
            "event-suppressed", origin_ids=["goal-outcome-2"], source_categories=["accepted_goal_outcome"],
            goal_ids=["goal-2"], purpose_category="project_path", evidence_ids=["evidence-2"],
            importance=.1, urgency=.95, expected_value=.1,
        )
        assert suppressed["result"]["state"] == "suppressed"
        review = store.register(
            "event-review", origin_ids=["goal-outcome-3"], source_categories=["accepted_goal_outcome"],
            goal_ids=["goal-3"], purpose_category="risk_mitigation", evidence_ids=["evidence-3"],
            risk=.97, reversibility=.05,
        )
        assert review["result"]["state"] == "requires_operator_review"
        assert store.register(
            "event-active", origin_ids=["goal-outcome-1"], source_categories=["accepted_goal_outcome"],
            goal_ids=["goal-1"], purpose_category="project_path", evidence_ids=["evidence-1"],
        )["idempotent"]
        inspection = store.inspection_summary()
        assert inspection["signal_count"] == 3
        assert not any(inspection["authority_boundary"].values())
        assert not inspection["plan_text_exposed"] and not inspection["provider_contacted"]
    print("v1134.0 prospective planning signals: 8/8 passed")

if __name__ == "__main__":
    main()
