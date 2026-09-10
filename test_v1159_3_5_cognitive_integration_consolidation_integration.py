from pathlib import Path
import json

from conscious_agent.conversation_policy_state import (
    build_conversation_policy_state,
    stage_conversation_policy_state,
    complete_conversation_policy_state,
)


def _policy(intent="direct_answer", warmth="neutral", disposition="answer_only"):
    return build_conversation_policy_state(
        {"selected_intent": intent, "confidence": "high", "selection_digest": "a" * 64},
        {"context_application": "implicit", "warmth": warmth, "policy_digest": "b" * 64},
        {"output_disposition": disposition, "question_scope": "none", "max_follow_up_questions": 0,
         "explicit_silence_verified": disposition == "intentional_silence", "policy_digest": "c" * 64},
    )


def test_v1159_3_stages_content_free_pending_record(monkeypatch, tmp_path):
    monkeypatch.setenv("EIDOLON_DATA_DIR", str(tmp_path))
    result = stage_conversation_policy_state(_policy(), operation_id="op-1", session_id="session-1")
    assert result["pending_persisted"] is True
    assert result["completed"] is False
    record = json.loads((tmp_path / "conversation_policy_state/pending/op-1.json").read_text())
    assert record["contains_content"] is False
    assert "prompt_section" not in record["projection"]
    assert record["approval_granted"] is False


def test_v1159_4_completion_records_initial_and_changed_transition(monkeypatch, tmp_path):
    monkeypatch.setenv("EIDOLON_DATA_DIR", str(tmp_path))
    stage_conversation_policy_state(_policy(), operation_id="op-1", session_id="session-1")
    first = complete_conversation_policy_state(operation_id="op-1", session_id="session-1")
    assert first["completed"] is True and first["transition_kind"] == "initial"
    stage_conversation_policy_state(_policy(intent="explanation", warmth="warm"), operation_id="op-2", session_id="session-1")
    second = complete_conversation_policy_state(operation_id="op-2", session_id="session-1")
    assert second["completed"] is True and second["transition_kind"] == "changed"
    assert "selected_intent" in second["changed_fields"]
    assert "warmth" in second["changed_fields"]
    assert second["contains_content"] is False


def test_v1159_4_stable_transition_is_explicit(monkeypatch, tmp_path):
    monkeypatch.setenv("EIDOLON_DATA_DIR", str(tmp_path))
    stage_conversation_policy_state(_policy(), operation_id="op-1", session_id="session-1")
    complete_conversation_policy_state(operation_id="op-1", session_id="session-1")
    stage_conversation_policy_state(_policy(), operation_id="op-2", session_id="session-1")
    result = complete_conversation_policy_state(operation_id="op-2", session_id="session-1")
    assert result["transition_kind"] == "stable"
    assert result["changed_fields"] == []


def test_v1159_5_invalid_pending_fails_closed_without_rewrite(monkeypatch, tmp_path):
    monkeypatch.setenv("EIDOLON_DATA_DIR", str(tmp_path))
    path = tmp_path / "conversation_policy_state/pending/op-1.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"record_identity":"tampered","projection":{}}')
    before = path.read_bytes()
    result = complete_conversation_policy_state(operation_id="op-1", session_id="session-1")
    assert result["completed"] is False
    assert result["completion_failure"] == "missing_or_invalid_pending"
    assert path.read_bytes() == before


def test_v1159_5_runtime_uses_shared_stage_and_completion_seams():
    source = Path("conscious_agent/conversation_runtime.py").read_text()
    assert source.count("stage_conversation_policy_state(") == 2
    assert source.count("complete_conversation_policy_state(") == 2
    assert source.count('result.cognitive_context["conversation_policy_continuity"]') == 4
    assert source.count('conversation_policy["prompt_section"]') == 2


def test_v1159_5_records_remain_non_authorizing(monkeypatch, tmp_path):
    monkeypatch.setenv("EIDOLON_DATA_DIR", str(tmp_path))
    stage_conversation_policy_state(_policy("governed_approval_request"), operation_id="op-1", session_id="session-1")
    result = complete_conversation_policy_state(operation_id="op-1", session_id="session-1")
    assert result["approval_granted"] is False
    assert result["authorization_granted"] is False
    assert result["execution_permitted"] is False
