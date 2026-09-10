from pathlib import Path
import json

from conscious_agent.conversation_policy_state import (
    build_conversation_policy_state,
    stage_conversation_policy_state,
    complete_conversation_policy_state,
)


def _policy(intent="direct_answer", warmth="neutral"):
    return build_conversation_policy_state(
        {"selected_intent": intent, "confidence": "high", "selection_digest": "a" * 64},
        {"context_application": "implicit", "warmth": warmth, "policy_digest": "b" * 64},
        {"output_disposition": "answer_only", "question_scope": "none", "max_follow_up_questions": 0,
         "explicit_silence_verified": False, "policy_digest": "c" * 64},
    )


def test_v1159_6_duplicate_completion_is_idempotent(monkeypatch, tmp_path):
    monkeypatch.setenv("EIDOLON_DATA_DIR", str(tmp_path))
    stage_conversation_policy_state(_policy(), operation_id="op-1", session_id="s-1")
    first = complete_conversation_policy_state(operation_id="op-1", session_id="s-1", now_epoch=100)
    second = complete_conversation_policy_state(operation_id="op-1", session_id="s-1", now_epoch=101)
    assert first["completed"] is True and first["duplicate_completion"] is False
    assert second["completed"] is True and second["duplicate_completion"] is True
    assert second["record_identity"] == first["record_identity"]


def test_v1159_6_cross_session_duplicate_fails_closed(monkeypatch, tmp_path):
    monkeypatch.setenv("EIDOLON_DATA_DIR", str(tmp_path))
    stage_conversation_policy_state(_policy(), operation_id="op-1", session_id="s-1")
    complete_conversation_policy_state(operation_id="op-1", session_id="s-1")
    result = complete_conversation_policy_state(operation_id="op-1", session_id="s-2")
    assert result["completed"] is False
    assert result["completion_failure"] == "operation_session_mismatch"


def test_v1159_6_stale_pending_is_not_promoted(monkeypatch, tmp_path):
    monkeypatch.setenv("EIDOLON_DATA_DIR", str(tmp_path))
    stage_conversation_policy_state(_policy(), operation_id="op-1", session_id="s-1")
    path = tmp_path / "conversation_policy_state/pending/op-1.json"
    record = json.loads(path.read_text())
    record["staged_at_epoch"] = 1
    path.write_text(json.dumps(record, sort_keys=True, indent=2))
    before = path.read_bytes()
    result = complete_conversation_policy_state(operation_id="op-1", session_id="s-1", now_epoch=90002)
    assert result["completed"] is False and result["completion_failure"] == "stale_pending"
    assert path.read_bytes() == before


def test_v1159_7_tampered_transition_metadata_fails_closed(monkeypatch, tmp_path):
    monkeypatch.setenv("EIDOLON_DATA_DIR", str(tmp_path))
    stage_conversation_policy_state(_policy(), operation_id="op-1", session_id="s-1")
    complete_conversation_policy_state(operation_id="op-1", session_id="s-1")
    completed = tmp_path / "conversation_policy_state/completed/s-1.json"
    record = json.loads(completed.read_text())
    record["transition_digest"] = "0" * 64
    completed.write_text(json.dumps(record, sort_keys=True, indent=2))
    stage_conversation_policy_state(_policy(warmth="warm"), operation_id="op-2", session_id="s-1")
    result = complete_conversation_policy_state(operation_id="op-2", session_id="s-1")
    assert result["completed"] is False
    assert result["completion_failure"] == "invalid_previous_completed"


def test_v1159_7_oversized_projection_is_bounded(monkeypatch, tmp_path):
    monkeypatch.setenv("EIDOLON_DATA_DIR", str(tmp_path))
    policy = _policy()
    policy["warmth"] = "W" * 10000
    policy["response_intent_digest"] = "x" * 10000
    stage_conversation_policy_state(policy, operation_id="op-1", session_id="s-1")
    record = json.loads((tmp_path / "conversation_policy_state/pending/op-1.json").read_text())
    assert len(record["projection"]["warmth"]) <= 64
    assert len(record["projection"]["response_intent_digest"]) <= 64
    assert len(json.dumps(record)) < 7000


def test_v1159_8_authority_fields_are_reconstructed(monkeypatch, tmp_path):
    monkeypatch.setenv("EIDOLON_DATA_DIR", str(tmp_path))
    policy = _policy("governed_approval_request")
    policy.update({"approval_granted": True, "authorization_granted": True, "execution_permitted": True,
                   "may_initiate_new_turn": True, "provider_contacted_for_policy": True})
    stage_conversation_policy_state(policy, operation_id="op-1", session_id="s-1")
    record = json.loads((tmp_path / "conversation_policy_state/pending/op-1.json").read_text())
    projection = record["projection"]
    assert projection["approval_granted"] is False
    assert projection["authorization_granted"] is False
    assert projection["execution_permitted"] is False
    assert projection["may_initiate_new_turn"] is False
    assert projection["provider_contacted_for_policy"] is False


def test_v1159_8_runtime_still_uses_shared_lifecycle_seams():
    source = Path("conscious_agent/conversation_runtime.py").read_text()
    assert source.count("stage_conversation_policy_state(") == 2
    assert source.count("complete_conversation_policy_state(") == 2
    assert source.count('conversation_policy["prompt_section"]') == 2
