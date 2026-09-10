from copy import deepcopy

from conscious_agent.hierarchical_planning_runtime import (
    build_hierarchical_planning_projection,
    build_hierarchical_planning_review_handoff,
    build_hierarchical_planning_review_projection,
    verify_hierarchical_planning_review_packet,
    verify_hierarchical_planning_review_state,
)


def _goal(candidate_type="reliability_improvement", evidence_count=2):
    projection = {
        "policy": {
            "candidate_available": True,
            "operator_review_required": True,
            "goal_activation_permitted": False,
            "plan_creation_permitted": False,
        },
        "candidate": {"candidate_type": candidate_type, "scope_band": "system"},
        "evidence": {"candidate_evidence_count": evidence_count},
    }
    reliability = {
        "reliability_posture": "goal_candidate_context_reliable",
        "candidate_available": True,
    }
    return projection, reliability


def _projection(*, prior=()):
    goal, reliability = _goal()
    return build_hierarchical_planning_projection(
        goal, reliability, prior_planning_receipts=prior,
    )


def test_1171_3_emerging_review_is_structurally_coherent():
    review = build_hierarchical_planning_review_projection(_projection())
    state = review["state"]
    packet = review["review_packet"]
    assert state["review_disposition"] == "emerging_plan_review"
    assert state["milestone_readiness_band"] == "structured_for_review"
    assert state["dependency_disposition"] == "operator_and_evidence_pending"
    assert state["stopping_posture"] == "bounded_and_explicit"
    assert verify_hierarchical_planning_review_state(state)
    assert verify_hierarchical_planning_review_packet(packet)


def test_1171_3_verified_same_candidate_continuity_becomes_stable():
    current = _projection()
    handoff = build_hierarchical_planning_review_handoff(
        current, provider_completed=True, assistant_memory_committed=True,
    )
    resumed = _projection(prior=[{"hierarchical_planning_review_handoff": handoff}])
    review = build_hierarchical_planning_review_projection(resumed)
    assert review["state"]["review_disposition"] == "stable_plan_review"
    assert review["state"]["continuity_disposition"] == "verified_same_candidate_continuity"
    assert review["state"]["verified_prior_receipt_count"] == 1


def test_1171_3_replay_does_not_increase_verified_continuity():
    current = _projection()
    handoff = build_hierarchical_planning_review_handoff(
        current, provider_completed=True, assistant_memory_committed=True,
    )
    resumed = _projection(prior=[
        {"hierarchical_planning_review_handoff": handoff},
        {"hierarchical_planning_review_handoff": handoff},
    ])
    review = build_hierarchical_planning_review_projection(resumed)
    assert review["state"]["verified_prior_receipt_count"] == 1
    assert review["state"]["replayed_prior_receipt_count"] == 1


def test_1171_3_recovered_projection_has_no_review_candidate():
    goal, reliability = _goal()
    recovered = build_hierarchical_planning_projection(
        goal, reliability,
        protected_operator_constraints=("literal_current_request_precedence",),
    )
    review = build_hierarchical_planning_review_projection(recovered)
    assert review["state"]["review_disposition"] == "literal_current_request_only_recovery"
    assert not review["review_packet"]["plan_candidate_available"]
    assert review["review_packet"]["milestone_categories"] == []


def test_1171_4_operator_packet_is_content_free_and_authority_free():
    packet = build_hierarchical_planning_review_projection(_projection())["review_packet"]
    assert packet["content_free"] is True
    assert packet["authority"] == "none"
    assert packet["operator_review_required"] is True
    assert packet["operator_approval_required"] is True
    assert all(packet[key] is False for key in (
        "plan_activated", "plan_persisted", "schedule_created", "tool_routed",
        "action_executed", "source_edited", "autonomous_work_started",
    ))
    text = str(packet).lower()
    assert "tests are still failing" not in text
    assert "private reasoning" not in text


def test_1171_4_unknown_packet_field_is_rejected_even_with_recomputed_digest():
    packet = deepcopy(build_hierarchical_planning_review_projection(_projection())["review_packet"])
    packet["approved"] = True
    packet.pop("review_packet_digest")
    from conscious_agent.hierarchical_planning_runtime import _digest
    packet["review_packet_digest"] = _digest(packet)
    assert not verify_hierarchical_planning_review_packet(packet)


def test_1171_4_count_category_mismatch_recovers():
    projection = _projection()
    projection["hierarchy"]["milestone_count"] += 1
    from conscious_agent.hierarchical_planning_runtime import _digest
    projection["hierarchy"]["integrity_digest"] = _digest({
        k: v for k, v in projection["hierarchy"].items() if k != "integrity_digest"
    })
    projection["diagnostics"]["integrity_digest"] = _digest({
        "policy": projection["policy"], "evidence": projection["evidence"], "hierarchy": projection["hierarchy"]
    })
    review = build_hierarchical_planning_review_projection(projection)
    assert review["state"]["review_disposition"] == "literal_current_request_only_recovery"
    assert not review["review_packet"]["plan_candidate_available"]


def test_1171_5_prompt_is_bounded_structural_and_nonexecuting():
    review = build_hierarchical_planning_review_projection(_projection())
    prompt = review["prompt_section"]
    assert len(prompt) <= 2048
    assert 'authority="none"' in prompt
    assert '"plan_activated":false' in prompt
    assert '"plan_persisted":false' in prompt
    assert '"tool_routed":false' in prompt
    assert '"action_executed":false' in prompt


def test_1171_5_review_verifiers_reject_tampering():
    review = build_hierarchical_planning_review_projection(_projection())
    state = deepcopy(review["state"])
    packet = deepcopy(review["review_packet"])
    state["plan_activated"] = True
    packet["tool_routed"] = True
    assert not verify_hierarchical_planning_review_state(state)
    assert not verify_hierarchical_planning_review_packet(packet)
