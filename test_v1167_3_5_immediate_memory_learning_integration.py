from conscious_agent.immediate_memory_learning import (
    build_immediate_memory_learning, build_learning_commit_boundary_handoff,
    verify_learning_commit_boundary_handoff, validate_prior_learning_receipts,
)
C=("preserve_historical_truth","no_unconfirmed_memory_mutation","current_message_precedence")

def candidate(msg="From now on, I prefer concise replies."):
    return build_immediate_memory_learning(msg,[{"preference_key":"reply_style"}],C)["candidate"]

def test_durable_candidate_waits_for_existing_commit_boundary():
    h=build_learning_commit_boundary_handoff(candidate(),provider_completed=False,assistant_memory_committed=False)
    assert h["eligible_for_existing_commit_review"] is False
    assert h["automatic_commit_permitted"] is False

def test_completed_turn_can_stage_review_without_mutation():
    h=build_learning_commit_boundary_handoff(candidate(),provider_completed=True,assistant_memory_committed=True)
    assert h["eligible_for_existing_commit_review"] is True
    assert h["memory_mutation_performed"] is False
    assert verify_learning_commit_boundary_handoff(h)

def test_temporary_preference_never_becomes_durable_handoff():
    c=build_immediate_memory_learning("For now, please use short answers.",[{"preference_key":"reply_style"}],C)["candidate"]
    h=build_learning_commit_boundary_handoff(c,provider_completed=True,assistant_memory_committed=True)
    assert h["eligible_for_existing_commit_review"] is False

def test_retraction_preserves_history_at_handoff():
    c=build_immediate_memory_learning("I take that back.",[{"fact_key":"claim"}],C)["candidate"]
    h=build_learning_commit_boundary_handoff(c,provider_completed=True,assistant_memory_committed=True)
    assert h["historical_truth_preserved"] is True
    assert h["automatic_commit_permitted"] is False

def test_verified_prior_receipt_supports_cross_turn_continuity():
    h=build_learning_commit_boundary_handoff(candidate(),provider_completed=True,assistant_memory_committed=True)
    p=build_immediate_memory_learning("Continue.",[],C,[h])
    assert p["policy"]["continuity_disposition"]=="resume_verified_learning_context"
    assert p["policy"]["verified_prior_learning_receipts"]==1

def test_replayed_receipt_does_not_amplify_continuity():
    h=build_learning_commit_boundary_handoff(candidate(),provider_completed=True,assistant_memory_committed=True)
    r=validate_prior_learning_receipts([h,h])
    assert r["verified_receipt_count"]==1 and r["replayed_receipt_count"]==1

def test_tampered_receipt_is_rejected():
    h=build_learning_commit_boundary_handoff(candidate(),provider_completed=True,assistant_memory_committed=True)
    h=dict(h); h["candidate_type"]="retraction"
    r=validate_prior_learning_receipts([h])
    assert r["verified_receipt_count"]==0

def test_streaming_and_non_streaming_stage_same_handoff():
    s=open("conscious_agent/conversation_runtime.py",encoding="utf-8").read()
    assert s.count("build_learning_commit_boundary_handoff(")==2
    assert s.count('immediate_memory_learning_commit_handoff')==2
    assert s.count("prior_learning_receipts=session_history")==2
