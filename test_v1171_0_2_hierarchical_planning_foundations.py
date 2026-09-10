from copy import deepcopy
from conscious_agent.internally_generated_goal_runtime import build_internally_generated_goal_candidate, build_internally_generated_goal_candidate_review_projection, build_internally_generated_goal_candidate_reliability
from conscious_agent.hierarchical_planning_runtime import build_hierarchical_planning_projection, build_hierarchical_planning_review_handoff, verify_hierarchical_planning_review_handoff, validate_prior_hierarchical_planning_receipts


def _goal(message="The Eidolon project tests are still failing again."):
    alpha={"policy":{"memory_selection_posture":"literal_current_request_only_recovery","policy_recovered":False},"evidence":{},"diagnostics":{},"selected_memory_records":[],"prompt_section":""}
    # Use a minimal verified-looking goal fixture by calling the retained builder with its recovery-safe alpha seam.
    g=build_internally_generated_goal_candidate(message, alpha, protected_operator_constraints=("literal_current_request_precedence","no_goal_activation","no_plan_creation","no_tool_routing","no_action_execution","operator_review_required"))
    review=build_internally_generated_goal_candidate_review_projection(g)
    reliability=build_internally_generated_goal_candidate_reliability(g, review)
    return g,reliability


def _valid_goal():
    g,r=_goal()
    if not g.get("candidate"):
        # deterministic structural fixture, matching the public v1170 contract
        g={"policy":{"candidate_available":True,"operator_review_required":True,"goal_activation_permitted":False,"plan_creation_permitted":False},"candidate":{"candidate_type":"reliability_improvement","scope_band":"system"},"evidence":{"candidate_evidence_count":2}}
        r={"reliability_posture":"goal_candidate_context_reliable","candidate_available":True}
    return g,r


def test_1171_0_content_free_hierarchy_contract():
    g,r=_valid_goal(); p=build_hierarchical_planning_projection(g,r)
    assert p["hierarchy"]["plan_candidate_available"]
    assert p["hierarchy"]["milestone_count"] >= 2
    assert p["hierarchy"]["dependency_count"] == 2
    assert p["hierarchy"]["stopping_condition_count"] == 3
    assert p["policy"]["content_free"] is True
    assert "tests are" not in str(p).lower()


def test_1171_0_no_goal_candidate_means_no_plan_candidate():
    p=build_hierarchical_planning_projection({}, {})
    assert not p["hierarchy"]["plan_candidate_available"]
    assert p["policy"]["planning_posture"] == "literal_current_request_only_recovery"


def test_1171_0_missing_constraints_fail_closed():
    g,r=_valid_goal(); p=build_hierarchical_planning_projection(g,r,protected_operator_constraints=("literal_current_request_precedence",))
    assert p["policy"]["policy_recovered"]
    assert p["hierarchy"]["milestone_count"] == 0


def test_1171_1_authority_is_denied_everywhere():
    g,r=_valid_goal(); p=build_hierarchical_planning_projection(g,r)
    for key in ("goal_activation_permitted","plan_activation_permitted","tool_routing_permitted","action_execution_permitted","source_editing_permitted","autonomous_work_permitted","provider_contact_permitted","plan_persistence_permitted"):
        assert p["policy"][key] is False
    assert p["hierarchy"]["plan_activated"] is False


def test_1171_1_replay_does_not_amplify_continuity():
    g,r=_valid_goal(); p=build_hierarchical_planning_projection(g,r)
    h=build_hierarchical_planning_review_handoff(p,provider_completed=True,assistant_memory_committed=True)
    rows=[{"hierarchical_planning_review_handoff":h},{"hierarchical_planning_review_handoff":h}]
    s=validate_prior_hierarchical_planning_receipts(rows)
    assert s["verified_receipt_count"] == 1 and s["replayed_receipt_count"] == 1


def test_1171_1_tamper_fails_closed():
    g,r=_valid_goal(); p=build_hierarchical_planning_projection(g,r)
    h=build_hierarchical_planning_review_handoff(p,provider_completed=True,assistant_memory_committed=True)
    h["milestone_count"] += 1
    assert not verify_hierarchical_planning_review_handoff(h)
    q=build_hierarchical_planning_projection(g,r,prior_planning_receipts=[{"hierarchical_planning_review_handoff":h}])
    assert q["policy"]["policy_recovered"] and q["hierarchy"]["milestone_count"] == 0


def test_1171_1_conflicting_receipts_fail_closed():
    g,r=_valid_goal(); p=build_hierarchical_planning_projection(g,r)
    a=build_hierarchical_planning_review_handoff(p,provider_completed=True,assistant_memory_committed=True)
    b=deepcopy(a); b["candidate_type"]="capability_improvement"; b.pop("receipt_digest");
    import hashlib,json; b["receipt_digest"]=hashlib.sha256(json.dumps(b,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
    q=build_hierarchical_planning_projection(g,r,prior_planning_receipts=[{"hierarchical_planning_review_handoff":a},{"hierarchical_planning_review_handoff":b}])
    assert q["policy"]["policy_recovered"]


def test_1171_2_handoff_requires_provider_and_memory_commit():
    g,r=_valid_goal(); p=build_hierarchical_planning_projection(g,r)
    a=build_hierarchical_planning_review_handoff(p,provider_completed=True,assistant_memory_committed=False)
    b=build_hierarchical_planning_review_handoff(p,provider_completed=True,assistant_memory_committed=True)
    assert verify_hierarchical_planning_review_handoff(a) and verify_hierarchical_planning_review_handoff(b)
    assert not a["eligible_for_review_continuity"] and b["eligible_for_review_continuity"]
    assert not b["plan_activated"] and not b["action_executed"]


def test_1171_2_oversized_prior_receipt_fails_closed():
    g,r=_valid_goal(); q=build_hierarchical_planning_projection(g,r,prior_planning_receipts=[{"hierarchical_planning_review_handoff":{"x":"z"*70000}}])
    assert q["policy"]["policy_recovered"]
