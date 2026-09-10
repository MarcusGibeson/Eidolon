from pathlib import Path
from tempfile import TemporaryDirectory
from conscious_agent.prospective_planning_signals import ProspectivePlanningSignalStore
from conscious_agent.prospective_planning_candidates import ProspectivePlanningCandidateStore

def main():
    with TemporaryDirectory() as directory:
        root = Path(directory)
        signals = ProspectivePlanningSignalStore(root)
        candidates = ProspectivePlanningCandidateStore(root)
        signal_id = signals.register(
            "signal-1", origin_ids=["goal-outcome-1"], source_categories=["accepted_goal_outcome"],
            goal_ids=["goal-1"], purpose_category="deliberate_no_action_review", evidence_ids=["evidence-1"],
            risk=.85, alternative_ids=["alt-1", "alt-2"], counterfactual_ids=["cf-1"], stop_condition_ids=["stop-1"],
        )["result"]["signal_id"]
        active = candidates.register("candidate-1", signal_ids=[signal_id], scope_digest="b" * 64, semantic_overlap_key="scope-1")
        assert active["result"]["state"] == "active"
        assert candidates.register("candidate-1", signal_ids=[signal_id])["idempotent"]
        waiting = candidates.register("candidate-2", signal_ids=[signal_id], timing_window_id="window-1", semantic_overlap_key="scope-2")
        assert waiting["result"]["state"] == "awaiting_timing_window"
        inspection = candidates.inspection_summary()
        assert inspection["candidate_count"] == 2
        assert inspection["recent_candidates"][0]["deliberate_no_action_eligible"]
        assert inspection["recent_candidates"][0]["alternative_ids"] == ["alt-1", "alt-2"]
        assert not any(inspection["authority_boundary"].values()) and not inspection["plan_text_exposed"]
    print("v1134.1 prospective planning candidates: 7/7 passed")

if __name__ == "__main__":
    main()
