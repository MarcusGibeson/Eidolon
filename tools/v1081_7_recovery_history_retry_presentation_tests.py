from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
TOOLS = ROOT / "tools"
sys.path.insert(0, str(AGENT))

import conversation_operations as ops
import conversation_recovery as recovery
import conversation_retry_evidence as retry_evidence
import conversation_sessions as sessions
import dashboard_chat_console
import post_review_development_verify as isolated_verify
import release_metadata


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


class IsolatedRuntime:
    def __init__(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="eidolon-v1081-7-")
        base = Path(self.temp.name)
        ops.CONVERSATION_OPERATION_DIR = base / "operations"
        ops.CONVERSATION_OPERATION_ACKNOWLEDGEMENT_DIR = base / "acknowledgements"
        retry_evidence.CONVERSATION_RETRY_EVIDENCE_DIR = base / "retry_evidence"
        sessions.CONVERSATION_SESSIONS_DIR = base / "conversation_sessions"
        sessions.ACTIVE_SESSION_FILE = sessions.CONVERSATION_SESSIONS_DIR / "active_session.json"
        sessions.CONVERSATION_DRAFTS_DIR = sessions.CONVERSATION_SESSIONS_DIR / "drafts"
        sessions.LEGACY_DASHBOARD_CHAT_DIR = base / "dashboard_chat"
        sessions.LEGACY_DASHBOARD_CHAT_IMPORT_FILE = sessions.CONVERSATION_SESSIONS_DIR / "legacy_dashboard_chat_import.json"
        sessions._SESSION_SEARCH_CACHE.clear()

    def close(self) -> None:
        self.temp.cleanup()


def failed_source(runtime: IsolatedRuntime) -> tuple[str, str]:
    session = sessions.create_conversation_session("Recovery test", source="v1081.7-test")
    session_id = str(session["id"])
    operation_id = "conversation_20260719T120000_123456789abc"
    acceptance_key = "chat_accept_1234567890abcdef"
    ops.create_operation_marker(operation_id, session_id, acceptance_key=acceptance_key)
    ops.finalize_operation_marker(
        operation_id,
        completion_state="unavailable_service",
        success=False,
        failure_category="unavailable_service",
        final_session_turn_recorded=True,
    )
    sessions.append_conversation_turn(
        session_id,
        turn_id=operation_id,
        user_message="private test message",
        assistant_response="",
        completion_state="unavailable_service",
        success=False,
        failure_category="unavailable_service",
        source="v1081.7-test",
        user_memory_stored=True,
        assistant_memory_stored=False,
    )
    return session_id, operation_id


def append_attempt(session_id: str, source_id: str, suffix: str, *, success: bool, state: str, failure: str = "") -> str:
    turn_id = f"conversation_20260719T12010{suffix}_abcdef123456"
    sessions.append_conversation_turn(
        session_id,
        turn_id=turn_id,
        user_message="private test message",
        assistant_response="generated content" if success else "",
        completion_state=state,
        success=success,
        failure_category=failure,
        source="dashboard_chat_recovery",
        user_memory_reused=True,
        assistant_memory_stored=success,
        recovery_of=source_id,
        recovery_kind=recovery.RECOVERY_KIND_FAILED_TURN_RETRY,
    )
    return turn_id


def test_release_metadata() -> None:
    current = tuple(map(int, release_metadata.RUNTIME_VERSION.split(".")))
    previous = tuple(map(int, release_metadata.PREVIOUS_RUNTIME_VERSION.split(".")))
    require(current >= (1081, 7), "runtime metadata predates v1081.7")
    require(previous >= (1081, 6) and previous < current, "v1081.7 lineage missing")
    require("v1081.7" in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8"), "v1081.7 historical milestone disappeared")


def test_recovery_history_is_bounded_and_content_free() -> None:
    runtime = IsolatedRuntime()
    try:
        session_id, source_id = failed_source(runtime)
        append_attempt(session_id, source_id, "1", success=False, state="timeout", failure="timeout")
        append_attempt(session_id, source_id, "2", success=True, state="completed")
        history = recovery.recovery_history(session_id, source_id)
        require(history["attempt_count"] == 2, "attempt count mismatch")
        require(history["recovered"] is True, "successful recovery not detected")
        require(history["latest_recovery_state"] == "completed", "latest state mismatch")
        forbidden = {"user_message", "assistant_response", "prompt", "response", "provider_payload", "credentials"}
        for attempt in history["attempts"]:
            require(not (forbidden & set(attempt)), f"private recovery history fields leaked: {forbidden & set(attempt)}")
    finally:
        runtime.close()


def test_recovery_cue_changes_with_history() -> None:
    runtime = IsolatedRuntime()
    try:
        session_id, source_id = failed_source(runtime)
        before = recovery.recovery_cue_token(session_id, source_id)
        require(len(before) == 64, "initial recovery cue missing")
        append_attempt(session_id, source_id, "1", success=False, state="timeout", failure="timeout")
        after = recovery.recovery_cue_token(session_id, source_id)
        require(len(after) == 64 and after != before, "recovery cue did not change with linked history")
    finally:
        runtime.close()


def test_stale_cue_rejected_before_provider_call() -> None:
    runtime = IsolatedRuntime()
    original = recovery.run_conversation_turn
    calls: list[dict] = []
    try:
        session_id, source_id = failed_source(runtime)
        stale = recovery.recovery_cue_token(session_id, source_id)
        append_attempt(session_id, source_id, "1", success=False, state="timeout", failure="timeout")
        recovery.run_conversation_turn = lambda *args, **kwargs: calls.append(kwargs)  # type: ignore[assignment]
        try:
            recovery.retry_failed_conversation_turn(session_id, source_id, expected_recovery_cue=stale)
        except recovery.ConversationRecoveryError as error:
            require("stale" in str(error).lower(), "stale cue error copy missing")
        else:
            raise AssertionError("stale cue was accepted")
        require(not calls, "provider runtime was called for stale recovery control")
    finally:
        recovery.run_conversation_turn = original
        runtime.close()


def test_current_cue_allows_one_explicit_linked_call() -> None:
    runtime = IsolatedRuntime()
    original = recovery.run_conversation_turn
    calls: list[dict] = []
    sentinel = object()
    try:
        session_id, source_id = failed_source(runtime)
        cue = recovery.recovery_cue_token(session_id, source_id)
        def fake_run(*args, **kwargs):
            calls.append(kwargs)
            return sentinel
        recovery.run_conversation_turn = fake_run  # type: ignore[assignment]
        result = recovery.retry_failed_conversation_turn(session_id, source_id, expected_recovery_cue=cue)
        require(result is sentinel, "current cue did not reach linked recovery")
        require(len(calls) == 1, "linked recovery did not run exactly once")
        require(calls[0].get("recovery_of") == source_id, "linked source operation missing")
    finally:
        recovery.run_conversation_turn = original
        runtime.close()


def test_successful_history_blocks_further_recovery() -> None:
    runtime = IsolatedRuntime()
    try:
        session_id, source_id = failed_source(runtime)
        recovered_id = append_attempt(session_id, source_id, "1", success=True, state="completed")
        state = recovery.recovery_state(session_id, source_id)
        require(state["retryable"] is False, "recovered source still retryable")
        require(state["successful_recovery_turn_id"] == recovered_id, "successful recovery id missing")
        require(state["recovery_attempt_count"] == 1, "recovery attempt count missing")
    finally:
        runtime.close()


def test_operation_status_carries_canonical_recovery_state() -> None:
    runtime = IsolatedRuntime()
    try:
        session_id, source_id = failed_source(runtime)
        payload = dashboard_chat_console.dashboard_chat_operation_status(operation_id=source_id)
        state = payload.get("recovery") or {}
        require(payload.get("ok") is True, "operation status failed")
        require(state.get("turn_id") == source_id, "canonical recovery state missing")
        require(len(str(state.get("recovery_cue_token") or "")) == 64, "status recovery cue missing")
    finally:
        runtime.close()


def test_restored_failure_card_has_history_and_state_token() -> None:
    runtime = IsolatedRuntime()
    try:
        session_id, source_id = failed_source(runtime)
        append_attempt(session_id, source_id, "1", success=False, state="timeout", failure="timeout")
        turn = next(turn for turn in sessions.conversation_session_turns(session_id) if turn.get("id") == source_id)
        turn = dict(turn)
        turn["session_id"] = session_id
        html = dashboard_chat_console._render_turn_recovery_controls(session_id, turn)
        require("Linked recovery history: 1 explicit attempt" in html, "history presentation missing")
        require("name='recovery_token'" in html, "state token missing from restored form")
        require("Run explicit linked recovery" in html, "explicit recovery control missing")
    finally:
        runtime.close()


def test_restored_diagnostics_use_explicit_session_context() -> None:
    runtime = IsolatedRuntime()
    try:
        session = sessions.create_conversation_session("Diagnostic context", source="v1081.7-test")
        session_id = str(session["id"])
        turn_id = "conversation_20260719T121000_abcdef654321"
        sessions.append_conversation_turn(
            session_id, turn_id=turn_id, user_message="private diagnostic fixture", assistant_response="",
            completion_state="failed", success=False, failure_category="unavailable_service",
            source="v1081.7-test", assistant_memory_stored=False,
        )
        turn = sessions.conversation_session_turns(session_id)[0]
        require("session_id" not in turn, "fixture unexpectedly duplicates session id inside the turn")
        html = dashboard_chat_console._render_turn_diagnostics(turn, session_id=session_id)
        require("Acceptance proven" in html and ">False<" in html, "restored diagnostics lost explicit session context")
    finally:
        runtime.close()


def test_dynamic_failure_card_waits_for_verified_state() -> None:
    source = (AGENT / "dashboard_chat_console.py").read_text()
    require("Refresh recovery state" in source, "unverified dynamic card does not require refresh")
    require("recovery.recovery_cue_token" in source, "dynamic recovery token gate missing")
    require("payload.recovery || null" in source, "operation reconciliation does not carry recovery state")


def test_non_acceptance_endpoint_rechecks_server_state() -> None:
    dashboard_source = (AGENT / "dashboard.py").read_text()
    evidence_source = (AGENT / "conversation_retry_evidence.py").read_text()
    require('/api/dashboard-chat/non-acceptance' in dashboard_source, "non-acceptance endpoint missing")
    require("persist_non_acceptance_evidence" in dashboard_source, "endpoint does not use bounded evidence writer")
    require("find_operation_by_acceptance_key" in evidence_source, "server-side accepted-operation recheck missing")


def test_explicit_resend_presentation_has_no_resend_form() -> None:
    source = (AGENT / "dashboard_chat_console.py").read_text()
    start = source.index("function appendExplicitResendPresentation")
    end = source.index("function clearOperationPoll", start)
    block = source[start:end]
    require("Review restored draft" in block, "manual draft review control missing")
    require(
        "fresh_acceptance_identity_required" in block
        or ("source_acceptance_key" in block and "resend_acceptance_key" in block),
        "fresh identity boundary missing",
    )
    require("automaticResend = 'false'" in block, "automatic resend boundary missing")
    require("form.submit" not in block and "method = 'post'" not in block, "resend presentation submits automatically")


def test_dashboard_wrapper_requires_state_token() -> None:
    source = (AGENT / "dashboard_chat_console.py").read_text()
    require("This recovery control has no persisted state token" in source, "tokenless dashboard recovery not blocked")
    dashboard_source = (AGENT / "dashboard.py").read_text()
    require("validate_recovery_cue(session_id, turn_id, recovery_token)" in dashboard_source, "stale validation occurs after coordination claim")


def test_no_automatic_replay_or_settings_mutation() -> None:
    source = (AGENT / "conversation_recovery.py").read_text() + (AGENT / "dashboard_chat_console.py").read_text()
    require("automatic resend" in source.lower() or "automaticResend" in source, "automatic resend boundary copy missing")
    for forbidden in ("install_model", "pull_model", "switch_provider", "save_local_model_configuration"):
        require(forbidden not in (AGENT / "conversation_recovery.py").read_text(), f"recovery module contains forbidden mutation: {forbidden}")


def test_rendered_javascript_syntax() -> None:
    html = dashboard_chat_console.render_realtime_chat_panel(None, compact=True)
    scripts: list[str] = []
    cursor = 0
    while True:
        start = html.find("<script>", cursor)
        if start < 0:
            break
        end = html.find("</script>", start)
        require(end >= 0, "unterminated script")
        scripts.append(html[start + 8:end])
        cursor = end + 9
    with tempfile.TemporaryDirectory(prefix="eidolon-v1081-7-js-") as directory:
        for index, script in enumerate(scripts):
            path = Path(directory) / f"script-{index}.js"
            path.write_text(script)
            result = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True, timeout=30)
            require(result.returncode == 0, result.stderr or "rendered JavaScript syntax failed")


def test_narrow_layout_controls_wrap() -> None:
    styles = dashboard_chat_console.COMPANION_CHAT_STYLES
    require(".chat-recovery-actions > *" in styles and ".chat-explicit-resend-presentation > *" in styles and "flex:1 1 100%; text-align:center;" in styles, "narrow recovery/resend controls do not wrap")
    require("max-width:100%" in styles, "bounded resend presentation width missing")


def test_core_profile_registration() -> None:
    selected = {suite.name for suite in isolated_verify.select_suites("core")}
    require("v1081.7-recovery-history-presentation" in selected, "v1081.7 absent from core profile")
    require("v1081.6-conversation-failure-retry" in selected, "v1081.6 retained suite missing")


def test_release_registration() -> None:
    source = (TOOLS / "release_verify.py").read_text()
    require(source.count("recovery-history-retry-presentation-fixtures") == 1, "release stage count wrong")
    require(source.count("tools/v1081_7_recovery_history_retry_presentation_tests.py") == 1, "suite registration count wrong")


def test_docs_and_workspace_versions() -> None:
    current_tag = release_metadata.RUNTIME_VERSION_TAG
    for relative in (
        "README.md", "README_NEXT_STEPS.md", "archive/docs/legacy_dependencies/roadmaps/README_DESKTOP_ALPHA.md",
        "data/settings.json", "data/workspaces/active_project.json", "data/workspaces/projects.json",
    ):
        require(current_tag in (ROOT / relative).read_text(), f"{relative} missing current version {current_tag}")
    require("v1081.7" in (ROOT / "README_RELEASE_HISTORY.md").read_text(), "v1081.7 release history missing")


def test_source_only_privacy() -> None:
    require(not (ROOT / "data/projects.json").exists(), "data/projects.json present")
    forbidden = (
        "data/conversation_runtime", "data/conversation_sessions", "data/dashboard_chat", "data/approvals",
        "data/tasks.json", "data/memories.json", ".venv",
    )
    paths = [
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}
    ]
    for token in forbidden:
        require(not any(token in path for path in paths), f"forbidden runtime path {token}")


TESTS: tuple[tuple[str, Callable[[], None]], ...] = tuple(
    (name[5:], value) for name, value in sorted(globals().items()) if name.startswith("test_") and callable(value)
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.parse_args()
    checks: list[dict[str, str]] = []
    passed = 0
    for name, function in TESTS:
        try:
            function()
        except Exception as error:
            checks.append({"name": name, "status": "fail", "message": f"{type(error).__name__}: {error}"})
        else:
            passed += 1
            checks.append({"name": name, "status": "pass", "message": ""})
    report = {
        "suite": "v1081.7-conversation-recovery-history-retry-presentation",
        "ok": passed == len(TESTS),
        "status": "pass" if passed == len(TESTS) else "fail",
        "passed": passed,
        "total": len(TESTS),
        "checks": checks,
        "automatic_retry": False,
        "automatic_resend": False,
        "provider_request_replayed": False,
        "release_authorized": False,
    }
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
