from conscious_agent.bounded_experiential_lessons import (
    build_bounded_experiential_lesson,
    build_lesson_review_boundary_handoff,
    validate_prior_lesson_receipts,
    verify_lesson_review_boundary_handoff,
)
from conscious_agent.immediate_memory_learning import build_immediate_memory_learning

LC=("preserve_historical_truth","no_unconfirmed_memory_mutation","current_message_precedence")
BC=("no_uncontrolled_self_training","review_before_durable_lesson","preserve_historical_truth")

def correction_projection():
    return build_immediate_memory_learning(
        "Correction: my preferred editor is Helix now",
        [{"preference_key":"preferred_editor","value":"Vim"}],
        protected_operator_constraints=LC,
    )

def lesson(prior=()):
    return build_bounded_experiential_lesson(
        "Correction: my preferred editor is Helix now",
        correction_projection(),
        protected_operator_constraints=BC,
        prior_lesson_receipts=prior,
    )

def test_1168_3_review_handoff_requires_provider_and_memory_commit():
    candidate=lesson()["candidate"]
    assert build_lesson_review_boundary_handoff(candidate, provider_completed=False, assistant_memory_committed=True)["eligible_for_operator_review"] is False
    assert build_lesson_review_boundary_handoff(candidate, provider_completed=True, assistant_memory_committed=False)["eligible_for_operator_review"] is False
    good=build_lesson_review_boundary_handoff(candidate, provider_completed=True, assistant_memory_committed=True)
    assert good["eligible_for_operator_review"] is True
    assert good["durable_commit_permitted"] is False
    assert good["model_training_performed"] is False
    assert verify_lesson_review_boundary_handoff(good)

def test_1168_3_no_candidate_never_becomes_review_eligible():
    handoff=build_lesson_review_boundary_handoff(None, provider_completed=True, assistant_memory_committed=True)
    assert handoff["eligible_for_operator_review"] is False
    assert handoff["lesson_candidate_present"] is False

def test_1168_4_verified_prior_receipt_resumes_structural_context():
    handoff=build_lesson_review_boundary_handoff(lesson()["candidate"], provider_completed=True, assistant_memory_committed=True)
    out=lesson([{"bounded_experiential_lesson_review_handoff": handoff}])
    assert out["policy"]["continuity_disposition"] == "resume_verified_lesson_context"
    assert out["policy"]["verified_prior_lesson_receipts"] == 1

def test_1168_4_replay_does_not_amplify_receipts():
    handoff=build_lesson_review_boundary_handoff(lesson()["candidate"], provider_completed=True, assistant_memory_committed=True)
    prior=validate_prior_lesson_receipts([handoff, handoff])
    assert prior["verified_receipt_count"] == 1
    assert prior["replayed_receipt_count"] == 1

def test_1168_4_tampered_receipt_forces_recovery():
    handoff=build_lesson_review_boundary_handoff(lesson()["candidate"], provider_completed=True, assistant_memory_committed=True)
    handoff=dict(handoff); handoff["model_training_performed"] = True
    out=lesson([handoff])
    assert out["policy"]["policy_recovered"] is True
    assert out["policy"]["continuity_disposition"] == "literal_request_only_recovery"
    assert out["candidate"] is None

def test_1168_4_conflicting_receipts_force_recovery():
    a=build_lesson_review_boundary_handoff(lesson()["candidate"], provider_completed=True, assistant_memory_committed=True)
    other=dict(lesson()["candidate"]); other["lesson_type"]="failure_avoidance_lesson"; other["source_kind"]="bounded_failure"
    b=build_lesson_review_boundary_handoff(other, provider_completed=True, assistant_memory_committed=True)
    out=lesson([a,b])
    assert out["policy"]["policy_recovered"] is True
    assert out["policy"]["conflicting_prior_lesson_receipts"] is True

def test_1168_5_receipts_are_content_free_and_authority_free():
    handoff=build_lesson_review_boundary_handoff(lesson()["candidate"], provider_completed=True, assistant_memory_committed=True)
    dumped=str(handoff).lower()
    assert "helix" not in dumped and "vim" not in dumped
    assert handoff["authority"] == "none"
    assert handoff["self_training_permitted"] is False
    assert handoff["memory_mutation_performed"] is False

def test_1168_5_runtime_has_shared_streaming_and_nonstreaming_handoff():
    source=open("conscious_agent/conversation_runtime.py",encoding="utf-8").read()
    assert source.count("build_lesson_review_boundary_handoff(") == 2
    assert source.count('result.cognitive_context["bounded_experiential_lesson_review_handoff"]') == 2
    assert source.count("prior_lesson_receipts=session_history") == 2
