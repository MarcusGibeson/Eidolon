import hashlib
import json

from conscious_agent.unified_memory_context import build_unified_memory_runtime_projection
from conscious_agent.memory_retrieval_relevance import build_memory_retrieval_relevance
from conscious_agent.immediate_memory_learning import (
    build_immediate_memory_learning,
    build_learning_commit_boundary_handoff,
)
from conscious_agent.bounded_experiential_lessons import (
    build_bounded_experiential_lesson,
    build_lesson_review_boundary_handoff,
)
from conscious_agent.memory_experiential_learning_alpha import (
    MAX_PRIOR_ALPHA_RECEIPTS,
    audit_memory_experiential_learning_alpha,
    build_memory_experiential_learning_alpha,
    build_memory_experiential_learning_alpha_handoff,
    build_memory_experiential_learning_alpha_reliability,
    validate_prior_memory_experiential_learning_alpha_receipts,
    verify_memory_experiential_learning_alpha_audit,
    verify_memory_experiential_learning_alpha_handoff,
    verify_memory_experiential_learning_alpha_reliability,
)


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def completed_projection(prior=()):
    message = "Correction: my preferred editor is Helix now"
    memories = [{
        "memory_domain": "semantic", "preference_key": "preferred_editor", "value": "Vim",
        "content": "Vim", "confidence": 0.8, "created_at": "2026-01-01T00:00:00Z",
    }]
    unified = build_unified_memory_runtime_projection(
        message, memory_records=memories,
        protected_operator_constraints=(
            "current_message_precedence", "explicit_correction_precedence",
            "no_memory_mutation", "no_action_execution",
        ),
    )
    retrieval = build_memory_retrieval_relevance(
        message, unified["selected_memory_records"], unified.get("selected_references")
    )
    learning = build_immediate_memory_learning(
        message, retrieval["selected_memory_records"],
        protected_operator_constraints=(
            "preserve_historical_truth", "no_unconfirmed_memory_mutation", "current_message_precedence",
        ),
    )
    lesson = build_bounded_experiential_lesson(
        message, learning,
        protected_operator_constraints=(
            "no_uncontrolled_self_training", "review_before_durable_lesson", "preserve_historical_truth",
        ),
    )
    learning_handoff = build_learning_commit_boundary_handoff(
        learning.get("candidate"), provider_completed=True, assistant_memory_committed=True
    )
    lesson_handoff = build_lesson_review_boundary_handoff(
        lesson.get("candidate"), provider_completed=True, assistant_memory_committed=True
    )
    return build_memory_experiential_learning_alpha(
        unified, retrieval, learning, lesson,
        learning_commit_handoff=learning_handoff,
        lesson_review_handoff=lesson_handoff,
        prior_alpha_receipts=prior,
    )


def completed_artifacts(prior=()):
    projection = completed_projection(prior)
    handoff = build_memory_experiential_learning_alpha_handoff(
        projection, provider_completed=True, assistant_memory_committed=True
    )
    audit = audit_memory_experiential_learning_alpha(projection, handoff)
    reliability = build_memory_experiential_learning_alpha_reliability(
        projection, handoff, audit, prior_alpha_receipts=prior
    )
    return projection, handoff, audit, reliability


def test_1169_6_handoff_rejects_digest_valid_unknown_fields():
    _, handoff, _, _ = completed_artifacts()
    forged = dict(handoff)
    forged["training_authority"] = "none"
    forged.pop("receipt_digest")
    forged["receipt_digest"] = _digest(forged)
    assert verify_memory_experiential_learning_alpha_handoff(forged) is False


def test_1169_6_handoff_rejects_impossible_counts_and_contracts():
    _, handoff, _, _ = completed_artifacts()
    for field, value in (("selected_count", -1), ("selected_count", 999), ("contract_version", "9999.9")):
        forged = dict(handoff)
        forged[field] = value
        forged.pop("receipt_digest")
        forged["receipt_digest"] = _digest(forged)
        assert verify_memory_experiential_learning_alpha_handoff(forged) is False


def test_1169_6_audit_rejects_extra_fields_and_incoherent_counts():
    _, _, audit, _ = completed_artifacts()
    forged = dict(audit)
    forged["approval"] = False
    forged.pop("audit_digest")
    forged["audit_digest"] = _digest(forged)
    assert verify_memory_experiential_learning_alpha_audit(forged) is False

    forged = dict(audit)
    forged["compliant"] = True
    forged["violation_count"] = 1
    forged.pop("audit_digest")
    forged["audit_digest"] = _digest(forged)
    assert verify_memory_experiential_learning_alpha_audit(forged) is False


def test_1169_7_prior_receipt_flood_is_bounded_and_fails_closed():
    _, handoff, _, _ = completed_artifacts()
    state = validate_prior_memory_experiential_learning_alpha_receipts(
        [handoff] * (MAX_PRIOR_ALPHA_RECEIPTS + 9)
    )
    assert state["verified_receipt_count"] == 1
    assert state["replayed_receipt_count"] == MAX_PRIOR_ALPHA_RECEIPTS - 1
    assert state["ignored_receipt_count"] == 9
    assert state["receipt_budget_exceeded"] is True
    assert state["recovery_required"] is True


def test_1169_7_oversized_and_malformed_prior_receipts_fail_closed():
    _, handoff, _, _ = completed_artifacts()
    oversized = dict(handoff)
    oversized["receipt_digest"] = "x" * 20000
    state = validate_prior_memory_experiential_learning_alpha_receipts([None, oversized])
    assert state["malformed_receipt_count"] == 1
    assert state["oversized_receipt_count"] == 1
    assert state["verified_receipt_count"] == 0
    assert state["recovery_required"] is True


def test_1169_7_reliability_fails_closed_on_tampered_handoff():
    projection, handoff, audit, _ = completed_artifacts()
    tampered = dict(handoff)
    tampered["model_training_performed"] = True
    report = build_memory_experiential_learning_alpha_reliability(projection, tampered, audit)
    assert report["ordinary_conversation_ready"] is False
    assert report["reliability_posture"] == "literal_current_request_only_recovery"
    assert report["selected_count"] == 0
    assert report["learning_candidate_available"] is False
    assert report["lesson_candidate_available"] is False
    assert verify_memory_experiential_learning_alpha_reliability(report)


def test_1169_7_recovered_projection_cannot_report_residual_context():
    projection, handoff, audit, _ = completed_artifacts()
    damaged = dict(projection)
    damaged["policy"] = dict(projection["policy"])
    damaged["policy"]["policy_recovered"] = True
    damaged["selected_memory_records"] = [{"content": "must not survive"}]
    report = build_memory_experiential_learning_alpha_reliability(damaged, handoff, audit)
    assert report["recovered_projection"] is True
    assert report["residual_state_detected"] is True
    assert report["ordinary_conversation_ready"] is False
    assert report["selected_count"] == 0


def test_1169_8_reliability_report_is_content_free_and_authority_free():
    _, _, _, report = completed_artifacts()
    assert report["ordinary_conversation_ready"] is True
    assert report["fault_count"] == 0
    assert verify_memory_experiential_learning_alpha_reliability(report)
    dumped = json.dumps(report, sort_keys=True).lower()
    assert "helix" not in dumped and "vim" not in dumped
    assert report["authority"] == "none"
    assert report["memory_mutation_performed"] is False
    assert report["lesson_commit_performed"] is False
    assert report["model_training_performed"] is False


def test_1169_8_reliability_rejects_digest_valid_authority_field():
    _, _, _, report = completed_artifacts()
    forged = dict(report)
    forged["authority"] = "operator"
    forged.pop("reliability_digest")
    forged["reliability_digest"] = _digest(forged)
    assert verify_memory_experiential_learning_alpha_reliability(forged) is False


def test_1169_8_streaming_and_nonstreaming_share_reliability_projection():
    source = open("conscious_agent/conversation_runtime.py", encoding="utf-8").read()
    assert source.count("build_memory_experiential_learning_alpha_reliability(") == 2
    assert source.count('result.cognitive_context["memory_experiential_learning_alpha_reliability"]') == 2
    assert source.count("alpha_prior_receipts = session_history") == 2


def test_1169_8_source_contains_no_goal_plan_tool_or_training_activation():
    source = open("conscious_agent/memory_experiential_learning_alpha.py", encoding="utf-8").read().lower()
    assert '"model_training_performed": false' in source
    assert '"memory_mutation_performed": false' in source
    assert '"lesson_commit_performed": false' in source
    assert "execute_tool(" not in source
    assert "create_goal(" not in source
    assert "create_plan(" not in source
