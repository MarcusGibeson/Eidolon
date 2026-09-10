from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
TOOLS = ROOT / "tools"
sys.path.insert(0, str(AGENT))

import conversation_operations as operations
import conversation_runtime as runtime
import conversation_sessions as sessions
import memory
import memory_commit_attribution as attribution
import post_review_development_verify as isolated_verify
from local_model import LocalModelConfig


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


class isolated_runtime:
    def __enter__(self):
        self.temp = tempfile.TemporaryDirectory(prefix="eidolon-v1083-0-")
        root = Path(self.temp.name)
        self.original = (
            memory.MEMORY_FILE,
            memory.THOUGHT_LOG_FILE,
            operations.CONVERSATION_OPERATION_DIR,
            operations.CONVERSATION_OPERATION_ACKNOWLEDGEMENT_DIR,
            sessions.CONVERSATION_SESSIONS_DIR,
            sessions.ACTIVE_SESSION_FILE,
        )
        memory.MEMORY_FILE = root / "memories.json"
        memory.THOUGHT_LOG_FILE = root / "thoughts.log"
        operations.CONVERSATION_OPERATION_DIR = root / "operations"
        operations.CONVERSATION_OPERATION_ACKNOWLEDGEMENT_DIR = root / "acknowledgements"
        sessions.CONVERSATION_SESSIONS_DIR = root / "sessions"
        sessions.ACTIVE_SESSION_FILE = root / "sessions" / "active_session.json"
        return root

    def __exit__(self, *_args):
        (
            memory.MEMORY_FILE,
            memory.THOUGHT_LOG_FILE,
            operations.CONVERSATION_OPERATION_DIR,
            operations.CONVERSATION_OPERATION_ACKNOWLEDGEMENT_DIR,
            sessions.CONVERSATION_SESSIONS_DIR,
            sessions.ACTIVE_SESSION_FILE,
        ) = self.original
        self.temp.cleanup()


def identities():
    return (
        "conversation_20260720T120000_aaaaaaaaaaaa",
        "conversation_session_20260720T120000_bbbbbbbbbb",
        "chat_accept_cccccccccccccccccccccccccccccccc",
    )


def test_completed_generated_turn_gets_exact_content_free_attribution() -> None:
    with isolated_runtime():
        operation_id, session_id, acceptance_key = identities()
        operations.create_operation_marker(operation_id, session_id, acceptance_key=acceptance_key)
        record = attribution.build_memory_commit_attribution(
            role="assistant",
            operation_id=operation_id,
            session_id=session_id,
            turn_id=operation_id,
            source="fixture",
            content="Generated fixture response.",
            completion_state="completed",
            provider_generation_completed=True,
            operation_completion_claimed=True,
        )
        validated = attribution.validate_memory_commit_attribution(record, require_assistant_eligible=True)
        require(validated["conversation_operation_id"] == operation_id, "operation identity lost")
        require(validated["conversation_session_id"] == session_id, "session identity lost")
        require(validated["conversation_turn_id"] == operation_id, "turn identity lost")
        require(validated["eligibility_decision"]["eligible"], "completed generated turn was not eligible")
        serialized = json.dumps(validated)
        require(acceptance_key not in serialized, "raw acceptance key leaked")
        require("Generated fixture response" not in serialized, "response content leaked into attribution")
        require(validated["acceptance_identity_digest"], "acceptance identity digest missing")


def test_cancelled_failed_partial_synthetic_and_missing_responses_are_ineligible() -> None:
    scenarios = (
        {"completion_state": "cancelled", "provider_generation_completed": True, "operation_completion_claimed": False},
        {"completion_state": "failed", "provider_generation_completed": False, "operation_completion_claimed": False},
        {"completion_state": "completed", "provider_generation_completed": True, "operation_completion_claimed": True, "partial_response": True},
        {"completion_state": "completed", "provider_generation_completed": True, "operation_completion_claimed": True, "synthetic_response": True},
    )
    for scenario in scenarios:
        decision = attribution.assistant_commit_eligibility(response="partial", **scenario)
        require(not decision["eligible"], f"ineligible scenario passed: {scenario}")
    missing = attribution.assistant_commit_eligibility(
        response="", completion_state="completed", provider_generation_completed=True, operation_completion_claimed=True,
    )
    require(not missing["eligible"], "missing response was eligible")


def test_runtime_store_rejects_unattributed_assistant_and_persists_valid_candidate() -> None:
    with isolated_runtime():
        operation_id, session_id, acceptance_key = identities()
        operations.create_operation_marker(operation_id, session_id, acceptance_key=acceptance_key)
        saved = runtime._store_assistant_memory(
            operation_id,
            "Completed generated response.",
            "fixture_runtime",
            LocalModelConfig(),
            session_id,
        )
        records = memory.load_memories()
        require(len(records) == 1 and records[0] == saved, "assistant memory not stored exactly once")
        require(saved["id"] == saved["memory_candidate_id"], "candidate identity is not durable memory identity")
        require(saved["conversation_turn_id"] == operation_id, "memory not bound to exact generated turn")
        attribution.validate_memory_commit_attribution(saved["memory_commit_attribution"], require_assistant_eligible=True)


def test_user_memory_has_distinct_non_assistant_attribution() -> None:
    with isolated_runtime():
        operation_id, session_id, acceptance_key = identities()
        operations.create_operation_marker(operation_id, session_id, acceptance_key=acceptance_key)
        saved = runtime._store_user_memory(operation_id, "User fixture", "fixture_runtime", session_id)
        evidence = saved["memory_commit_attribution"]
        require(evidence["role"] == "user", "user attribution role wrong")
        require(evidence["eligibility_decision"]["decision"] == "not_applicable", "user input claimed assistant eligibility")
        require(not evidence["completion_evidence"]["provider_generation_completed"], "user input claimed provider generation")


def test_session_turn_carries_only_candidate_id_links() -> None:
    with isolated_runtime():
        session = sessions.create_conversation_session("Attribution links")
        turn = sessions.append_conversation_turn(
            session["id"],
            turn_id="turn-attribution",
            user_message="hello",
            assistant_response="response",
            completion_state="completed",
            success=True,
            user_memory_stored=True,
            assistant_memory_stored=True,
            user_memory_attribution_id="memory_candidate_user",
            assistant_memory_attribution_id="memory_candidate_assistant",
        )
        require(turn["memory_commit_attribution_schema_version"] == "1", "turn attribution schema missing")
        require(turn["assistant_memory_attribution_id"] == "memory_candidate_assistant", "assistant candidate link missing")
        require("memory_commit_attribution" not in turn, "full attribution copied into transcript")


def test_registration_and_source_only_privacy() -> None:
    core = [suite.name for suite in isolated_verify.select_suites("core")]
    full = [suite.name for suite in isolated_verify.select_suites("full")]
    require(core.count("v1083.0-memory-commit-attribution") == 1, "core registration wrong")
    require(full.count("v1083.0-memory-commit-attribution") == 1, "full registration wrong")
    source = (TOOLS / "release_verify.py").read_text(encoding="utf-8")
    require(source.count("v1083_0_memory_commit_attribution_tests.py") == 1, "release registration wrong")
    forbidden = ("data/memories.json", "data/conversation_runtime/", "data/conversation_sessions/")
    files = [path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if path.is_file() and "__pycache__" not in path.parts]
    require(not [name for name in files if any(name == item or name.startswith(item) for item in forbidden)], "private runtime state present")


TESTS = [
    ("completed_generated_turn_gets_exact_content_free_attribution", test_completed_generated_turn_gets_exact_content_free_attribution),
    ("cancelled_failed_partial_synthetic_and_missing_responses_are_ineligible", test_cancelled_failed_partial_synthetic_and_missing_responses_are_ineligible),
    ("runtime_store_rejects_unattributed_assistant_and_persists_valid_candidate", test_runtime_store_rejects_unattributed_assistant_and_persists_valid_candidate),
    ("user_memory_has_distinct_non_assistant_attribution", test_user_memory_has_distinct_non_assistant_attribution),
    ("session_turn_carries_only_candidate_id_links", test_session_turn_carries_only_candidate_id_links),
    ("registration_and_source_only_privacy", test_registration_and_source_only_privacy),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.parse_args()
    checks = []
    for name, function in TESTS:
        try:
            function()
        except Exception as error:
            checks.append({"name": name, "status": "fail", "message": f"{type(error).__name__}: {error}"})
        else:
            checks.append({"name": name, "status": "pass", "message": ""})
    passed = sum(check["status"] == "pass" for check in checks)
    report = {"suite": "v1083.0-memory-commit-attribution", "ok": passed == len(checks), "status": "pass" if passed == len(checks) else "fail", "passed": passed, "total": len(checks), "checks": checks}
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
