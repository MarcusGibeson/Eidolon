from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))

import chat_action_router as router
import conversation_sessions as sessions
import dashboard_chat_console as dashboard_chat
from command_runner import CommandRunResult
from conversation_action_portal import build_action_portal_state, portal_update_is_safe
from conversation_quality import classify_conversation_quality


class Failure(AssertionError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Failure(message)


@contextmanager
def isolated_runtime():
    with tempfile.TemporaryDirectory(prefix="eidolon-v1080-3-soak-") as raw:
        root = Path(raw)
        action_originals = {
            "CHAT_ACTIONS_DIR": router.CHAT_ACTIONS_DIR,
            "CHAT_ACTIONS_README": router.CHAT_ACTIONS_README,
            "store_memory": router.store_memory,
            "run_approved_command": router.run_approved_command,
            "create_approval": router.create_approval,
            "suggest_patch": router.suggest_patch,
        }
        session_originals = {
            "CONVERSATION_SESSIONS_DIR": sessions.CONVERSATION_SESSIONS_DIR,
            "ACTIVE_SESSION_FILE": sessions.ACTIVE_SESSION_FILE,
            "CONVERSATION_DRAFTS_DIR": sessions.CONVERSATION_DRAFTS_DIR,
            "LEGACY_DASHBOARD_CHAT_DIR": sessions.LEGACY_DASHBOARD_CHAT_DIR,
            "LEGACY_DASHBOARD_CHAT_IMPORT_FILE": sessions.LEGACY_DASHBOARD_CHAT_IMPORT_FILE,
        }
        dashboard_originals = {
            "DASHBOARD_CHAT_DIR": dashboard_chat.DASHBOARD_CHAT_DIR,
            "DASHBOARD_CHAT_README": dashboard_chat.DASHBOARD_CHAT_README,
            "stream_conversation_turn": dashboard_chat.stream_conversation_turn,
            "run_conversation_turn": dashboard_chat.run_conversation_turn,
            "_save_post_response_side_effects": dashboard_chat._save_post_response_side_effects,
        }
        router.CHAT_ACTIONS_DIR = root / "chat_actions"
        router.CHAT_ACTIONS_README = router.CHAT_ACTIONS_DIR / "README.md"
        router.store_memory = lambda *_args, **_kwargs: None
        sessions.CONVERSATION_SESSIONS_DIR = root / "conversation_sessions"
        sessions.ACTIVE_SESSION_FILE = sessions.CONVERSATION_SESSIONS_DIR / "active_session.json"
        sessions.CONVERSATION_DRAFTS_DIR = sessions.CONVERSATION_SESSIONS_DIR / "drafts"
        sessions.LEGACY_DASHBOARD_CHAT_DIR = root / "legacy_dashboard_chat"
        sessions.LEGACY_DASHBOARD_CHAT_IMPORT_FILE = sessions.CONVERSATION_SESSIONS_DIR / "legacy_dashboard_chat_import.json"
        dashboard_chat.DASHBOARD_CHAT_DIR = root / "dashboard_chat"
        dashboard_chat.DASHBOARD_CHAT_README = dashboard_chat.DASHBOARD_CHAT_DIR / "README.md"
        dashboard_chat._save_post_response_side_effects = lambda *_args, **_kwargs: ""
        try:
            yield root
        finally:
            for key, value in action_originals.items():
                setattr(router, key, value)
            for key, value in session_originals.items():
                setattr(sessions, key, value)
            for key, value in dashboard_originals.items():
                setattr(dashboard_chat, key, value)


def _session_with_action(*, status: str = "proposed", result: dict | None = None, mode: str = router.DIRECT_COMMAND):
    session = sessions.create_conversation_session("Action thread", select_session=False)
    operation_id = "conversation_20260718T230000_abcdef123456"
    sessions.append_conversation_turn(
        session["id"],
        turn_id=operation_id,
        user_message="Run diagnostics",
        assistant_response="I will route that through the supervised controls.",
        completion_state="completed",
        success=True,
        provider="test",
        model="test",
        select_session=False,
    )
    action = router.propose_chat_action("Run diagnostics", save=True, deduplication_key=operation_id)
    action["execution_mode"] = mode
    action["status"] = status
    action["result"] = dict(result or {})
    router.save_chat_action(action)
    portal = build_action_portal_state(action, action["result"])
    if portal:
        sessions.update_conversation_turn_action(session["id"], operation_id, portal)
    return session, operation_id, action


def test_follow_up_phrase_matrix() -> None:
    cases = {
        "Did that finish?": "status",
        "What happened with it?": "status",
        "Why did that fail?": "status",
        "Try that again.": "retry",
        "Please retry it.": "retry",
        "Don't run that yet.": "cancel",
        "Hold it for now.": "cancel",
        "Approve that.": "approval",
    }
    for phrase, expected in cases.items():
        require(router.classify_chat_action_follow_up(phrase) == expected, f"{phrase!r} did not classify as {expected}")


def test_follow_up_false_positive_resistance() -> None:
    phrases = (
        "What happened in the movie?",
        "Try that restaurant again sometime.",
        "Don't run that red light.",
        "Approve that design choice in your opinion?",
        "It finished raining.",
    )
    for phrase in phrases:
        require(not router.classify_chat_action_follow_up(phrase), f"casual phrase became action control: {phrase}")


def test_recent_session_binding_and_stale_refusal() -> None:
    with isolated_runtime():
        session, _operation_id, action = _session_with_action()
        resolved = dashboard_chat._latest_governed_action_for_session(session["id"])
        require(resolved and resolved.get("id") == action.get("id"), "recent session action was not resolved")
        for index in range(5):
            sessions.append_conversation_turn(
                session["id"],
                turn_id=f"ordinary_{index}",
                user_message=f"Ordinary message {index}",
                assistant_response=f"Ordinary reply {index}",
                completion_state="completed",
                success=True,
                select_session=False,
            )
        require(dashboard_chat._latest_governed_action_for_session(session["id"]) is None, "stale action leaked past bounded follow-up window")
        require(dashboard_chat._propose_explicit_chat_action("What happened?", session["id"], operation_id="followup_none") is None, "unbound status phrase created a global action")


def test_inflight_action_binding_is_session_scoped() -> None:
    with isolated_runtime():
        first = sessions.create_conversation_session("First", select_session=False)
        second = sessions.create_conversation_session("Second", select_session=False)
        action_first = router.propose_chat_action(
            "Run diagnostics", save=True, deduplication_key="inflight_first", conversation_session_id=first["id"],
        )
        router.propose_chat_action(
            "Check settings health", save=True, deduplication_key="inflight_second", conversation_session_id=second["id"],
        )
        resolved = dashboard_chat._latest_governed_action_for_session(first["id"])
        require(resolved and resolved.get("id") == action_first.get("id"), "in-flight follow-up crossed conversation sessions")
        follow_up = dashboard_chat._propose_explicit_chat_action("Is it still running?", first["id"], operation_id="inflight_followup")
        require(follow_up and follow_up.get("target_action_id") == action_first.get("id"), "in-flight status follow-up did not bind to the session action")


def test_follow_up_provider_guidance_forbids_false_completion() -> None:
    history = [{"user_message": "Run diagnostics", "assistant_response": "I routed that through the visible controls."}]
    profile = classify_conversation_quality("Approve that.", history)
    require(profile.explicit_operator_request and profile.short_follow_up, "approval follow-up was not recognized as a protected operator continuation")
    guidance = profile.response_instruction().lower()
    require("do not claim" in guidance and "approval" in guidance, "provider guidance permits false approval or completion claims")


def test_status_follow_up_is_read_only_and_deduplicated() -> None:
    with isolated_runtime():
        _session, _operation_id, target = _session_with_action(status="executed", result={"ok": True, "message": "Diagnostics completed.", "stdout": "PRIVATE"})
        first = router.propose_chat_action_follow_up("Did that finish?", target, save=True, deduplication_key="followup_status")
        second = router.propose_chat_action_follow_up("Did that finish?", target, save=True, deduplication_key="followup_status")
        require(first and second and first["id"] == second["id"], "duplicate status follow-up created two cards")
        require(first.get("execution_mode") == router.INFO, "status follow-up was executable")
        result = router.execute_chat_action(first["id"])
        require(result.ok and result.status == "info", "read-only status card did not replay safely")
        require(router.load_chat_action(target["id"])["status"] == "executed", "status follow-up mutated target action")
        require("PRIVATE" not in json.dumps(first), "status follow-up copied raw output")


def test_retry_preserves_attempt_chain_and_exactly_once() -> None:
    with isolated_runtime():
        calls = 0

        def fake_run(command: str, dry_run: bool = False, timeout_seconds: int | None = None) -> CommandRunResult:
            nonlocal calls
            calls += 1
            if calls == 1:
                return CommandRunResult(False, command, [sys.executable], error="Command timed out after 180 seconds.", stderr="FIRST PRIVATE")
            return CommandRunResult(True, command, [sys.executable], return_code=0, message="Diagnostics completed after retry.", stdout="SECOND PRIVATE")

        router.run_approved_command = fake_run
        action = router.propose_chat_action("Run diagnostics", save=True, deduplication_key="original_retry")
        first = router.execute_chat_action(action["id"], timeout_seconds=180)
        require(first.status == "timed_out", "initial timeout was not persisted")
        follow_up = router.propose_chat_action_follow_up("Try that again.", router.load_chat_action(action["id"]), save=True, deduplication_key="retry_control")
        require(follow_up and follow_up.get("execution_mode") == router.ACTION_RETRY, "safe retry follow-up was not created")
        second = router.execute_chat_action(follow_up["id"], timeout_seconds=180)
        replay = router.execute_chat_action(follow_up["id"], timeout_seconds=180)
        require(second.ok and replay.replayed, "retry control did not finish and replay exactly once")
        require(calls == 2, f"runner executed {calls} times instead of initial plus one retry")
        target = router.load_chat_action(action["id"])
        attempts = target.get("execution_attempts") or []
        require(len(attempts) == 2, f"expected two preserved attempts, found {len(attempts)}")
        require(attempts[0].get("status") == "timed_out" and (attempts[0].get("result") or {}).get("redacted"), "original timeout evidence was overwritten")
        require(attempts[1].get("status") == "executed" and (attempts[1].get("result") or {}).get("redacted"), "retry evidence was not preserved separately")
        require("FIRST PRIVATE" not in json.dumps(attempts) and "SECOND PRIVATE" not in json.dumps(attempts), "attempt chain duplicated raw command output")
        require(attempts[1].get("retry_of_attempt_id") == attempts[0].get("attempt_id"), "retry was not linked to the original attempt")


def test_concurrent_retry_delivery_starts_one_attempt() -> None:
    with isolated_runtime():
        calls = 0
        entered = threading.Event()
        release = threading.Event()

        def fake_run(command: str, dry_run: bool = False, timeout_seconds: int | None = None) -> CommandRunResult:
            nonlocal calls
            calls += 1
            if calls == 1:
                return CommandRunResult(False, command, [sys.executable], error="Command timed out after 180 seconds.")
            entered.set()
            require(release.wait(3), "retry runner barrier timed out")
            return CommandRunResult(True, command, [sys.executable], return_code=0, message="Recovered.")

        router.run_approved_command = fake_run
        target = router.propose_chat_action("Run diagnostics", save=True, deduplication_key="concurrent_target")
        router.execute_chat_action(target["id"], timeout_seconds=180)
        control = router.propose_chat_action_follow_up("Retry it.", router.load_chat_action(target["id"]), save=True, deduplication_key="concurrent_control")
        results: list = []
        thread = threading.Thread(target=lambda: results.append(router.execute_chat_action(control["id"], timeout_seconds=180)))
        thread.start()
        require(entered.wait(2), "retry attempt did not start")
        duplicate = router.execute_chat_action(control["id"], timeout_seconds=180)
        release.set()
        thread.join(3)
        require(not thread.is_alive(), "retry attempt did not finish")
        require(duplicate.replayed and duplicate.status == "running", "concurrent duplicate did not replay running state")
        require(calls == 2, "concurrent retry delivery started duplicate commands")


def test_pending_cancel_prevents_later_execution() -> None:
    with isolated_runtime():
        calls = 0

        def fake_run(*_args, **_kwargs):
            nonlocal calls
            calls += 1
            return CommandRunResult(True, "", [sys.executable], return_code=0, message="should not run")

        router.run_approved_command = fake_run
        target = router.propose_chat_action("Run diagnostics", save=True, deduplication_key="cancel_target")
        control = router.propose_chat_action_follow_up("Don't run that yet.", target, save=True, deduplication_key="cancel_control")
        require(control and control.get("execution_mode") == router.ACTION_CANCEL, "pending cancellation control was not created")
        result = router.execute_chat_action(control["id"])
        require(result.ok, "pending cancellation control failed")
        persisted = router.load_chat_action(target["id"])
        require(persisted.get("status") == "cancelled", "target was not atomically cancelled")
        later = router.execute_chat_action(target["id"])
        require(not later.ok and calls == 0, "cancelled target executed later")
        portal = build_action_portal_state(persisted, persisted.get("result"))
        require(portal and portal.get("status") == "cancelled", "cancelled state did not rehydrate")


def test_running_or_terminal_cancel_is_not_faked() -> None:
    with isolated_runtime():
        _session, _operation_id, running = _session_with_action(status="running")
        control = router.propose_chat_action_follow_up("Cancel it.", running, save=False)
        require(control and control.get("execution_mode") == router.BLOCKED, "running cancellation was presented as successful")
        require("already running" in str(control.get("summary")).lower(), "running cancellation did not explain the boundary")
        running["status"] = "executed"
        running["result"] = {"ok": True, "message": "Completed."}
        terminal = router.propose_chat_action_follow_up("Stop that.", running, save=False)
        require(terminal and terminal.get("execution_mode") == router.BLOCKED, "terminal action was cancellable")
        running["status"] = "approval_created"
        running["approval_id"] = "approval_pending"
        approval_created = router.propose_chat_action_follow_up("Cancel it.", running, save=False)
        require(approval_created and approval_created.get("execution_mode") == router.BLOCKED, "created approval was presented as cancellable")


def test_approval_follow_up_never_grants_approval() -> None:
    with isolated_runtime():
        calls = 0

        def fake_approval(**_kwargs):
            nonlocal calls
            calls += 1
            return {"id": "approval_private", "status": "pending"}

        router.create_approval = fake_approval
        target = router.propose_chat_action("Apply the latest patch", save=True, deduplication_key="approval_target")
        follow_up = router.propose_chat_action_follow_up("Approve that.", target, save=True, deduplication_key="approval_followup")
        require(follow_up and follow_up.get("execution_mode") == router.INFO, "approval follow-up became an approval mutation")
        router.execute_chat_action(follow_up["id"])
        require(calls == 0, "conversational approval follow-up created or granted approval")
        require(router.load_chat_action(target["id"])["status"] == "proposed", "approval target changed without card execution")


def test_context_reconciles_retry_without_raw_output() -> None:
    with isolated_runtime():
        session, operation_id, target = _session_with_action(status="timed_out", result={"ok": False, "error": "Timed out.", "stderr": "OLD PRIVATE"})
        target["execution_attempt"] = 1
        target["execution_attempts"] = [{
            "attempt_id": f"{target['id']}:attempt:1",
            "attempt_number": 1,
            "status": "timed_out",
            "started_at": "2026-07-18T23:00:00",
            "completed_at": "2026-07-18T23:03:00",
            "retry_of_attempt_id": "",
            "result": dict(target["result"]),
        }]
        router.save_chat_action(target)
        stale = build_action_portal_state(target, target["result"])
        sessions.update_conversation_turn_action(session["id"], operation_id, stale)

        router.run_approved_command = lambda *_args, **_kwargs: CommandRunResult(True, "", [sys.executable], return_code=0, message="Recovered.", stdout="NEW PRIVATE")
        router.execute_chat_action(target["id"], retry=True, timeout_seconds=180)
        history = sessions.conversation_history_for_prompt(session["id"])
        summary = history[0].get("action_status_summary", "")
        require("completed" in summary.lower(), "prompt context kept stale timeout after retry")
        require("attempt 2" in summary.lower() and "earlier attempt" in summary.lower(), "prompt context omitted preserved attempt lineage")
        require("OLD PRIVATE" not in json.dumps(history) and "NEW PRIVATE" not in json.dumps(history), "prompt context leaked attempt output")


def test_card_rehydrates_latest_attempt_and_preserves_privacy() -> None:
    with isolated_runtime():
        session, operation_id, target = _session_with_action(status="executed", result={"ok": True, "message": "Recovered.", "stdout": "PRIVATE OUTPUT"})
        target["execution_attempt"] = 2
        target["execution_attempts"] = [
            {"attempt_id": "a1", "attempt_number": 1, "status": "timed_out", "result": {"stderr": "OLD PRIVATE"}},
            {"attempt_id": "a2", "attempt_number": 2, "status": "executed", "result": dict(target["result"]), "retry_of_attempt_id": "a1"},
        ]
        router.save_chat_action(target)
        turn = sessions.conversation_session_turns(session["id"])[0]
        html = dashboard_chat._render_action_portal_card(session["id"], turn)
        require("Latest execution attempt: 2" in html and "Earlier preserved attempts: 1" in html, "rehydrated card omitted attempt lineage")
        require("PRIVATE OUTPUT" not in html and "OLD PRIVATE" not in html, "rehydrated card leaked raw attempt evidence")
        require("Viewing this card never executes" in html, "rehydrated card omitted non-execution boundary")


def test_cancelled_state_rejects_stale_overwrite() -> None:
    base = {"id": "cancelled_test", "title": "Pending check", "summary": "Check.", "execution_mode": router.DIRECT_COMMAND, "risk_level": "low"}
    cancelled = build_action_portal_state({**base, "status": "cancelled"}, {"ok": True, "message": "Cancelled."})
    proposed = build_action_portal_state({**base, "status": "proposed"})
    require(cancelled and proposed and not portal_update_is_safe(cancelled, proposed), "stale proposal can overwrite cancellation")


def test_capability_summary_is_registry_derived() -> None:
    summary = router.supervised_capability_summary()
    for item in router.SUPERVISED_CAPABILITY_REGISTRY:
        require(item["label"] in summary, f"capability registry item missing from summary: {item['id']}")
    require("Currently registered" in summary and "unrestricted shell" in summary, "capability summary omitted current-state or boundary language")


def test_long_session_history_remains_bounded_and_clean() -> None:
    with isolated_runtime():
        session = sessions.create_conversation_session("Long soak", select_session=False)
        for index in range(80):
            sessions.append_conversation_turn(
                session["id"],
                turn_id=f"long_{index:03d}",
                user_message=f"Conversation message {index}",
                assistant_response=f"Conversation reply {index}",
                completion_state="completed",
                success=True,
                provider="test",
                model="test",
                select_session=False,
            )
        history = sessions.conversation_history_for_prompt(session["id"], limit=8)
        require(len(history) == 8, f"long-session prompt history was not bounded: {len(history)}")
        require(history[0]["user_message"] == "Conversation message 72", "long-session prompt history selected the wrong boundary")
        require("operator_action" not in json.dumps(history), "prompt history exposed portal structure instead of summary")


def test_stream_event_ordering_for_direct_action() -> None:
    with isolated_runtime():
        session = sessions.create_conversation_session("Ordering", select_session=False)
        operation_id = "conversation_stream_order_abcdef123456"

        def fake_stream(message: str, **kwargs):
            sessions.append_conversation_turn(
                session["id"], turn_id=operation_id, user_message=message, assistant_response="Provider reply.",
                completion_state="completed", success=True, provider="test", model="test", select_session=False,
            )
            yield {"event": "meta", "operation_id": operation_id}
            yield {"event": "delta", "text": "Provider reply."}
            yield {"event": "done", "result": {
                "success": True, "completion_state": "completed", "display_message": "Provider reply.",
                "failure_category": "", "timings_ms": {"first_token": 1, "provider": 2},
                "operation_id": operation_id, "provider": "test", "model": "test",
            }}

        dashboard_chat.stream_conversation_turn = fake_stream
        router.run_approved_command = lambda *_args, **_kwargs: CommandRunResult(True, "", [sys.executable], return_code=0, message="Diagnostics completed.")
        events = list(dashboard_chat.stream_dashboard_chat_turn(
            "Run diagnostics", use_ai=True, session_id=session["id"], operation_id=operation_id, draft_already_cleared=True,
        ))
        names = [item.get("event") for item in events]
        require(names.index("action") < names.index("delta"), "action proposal was not visible before provider delta")
        require(names.index("conversation_complete") < names.index("action_result"), "direct action executed before conversational completion")
        require(names.count("action_result") == 1 and names.count("done") == 1, "stream emitted duplicate action result or completion")


def test_pending_hold_applies_before_provider_start() -> None:
    with isolated_runtime():
        session, _operation_id, target = _session_with_action(status="proposed")
        followup_operation = "conversation_hold_order_abcdef123456"
        observed_statuses: list[str] = []

        def fake_stream(message: str, **kwargs):
            observed_statuses.append(str(router.load_chat_action(target["id"]).get("status")))
            sessions.append_conversation_turn(
                session["id"], turn_id=followup_operation, user_message=message, assistant_response="I left it pending no longer.",
                completion_state="completed", success=True, provider="test", model="test", select_session=False,
            )
            yield {"event": "delta", "text": "I left it pending no longer."}
            yield {"event": "done", "result": {
                "success": True, "completion_state": "completed", "display_message": "I left it pending no longer.",
                "failure_category": "", "timings_ms": {}, "operation_id": followup_operation,
                "provider": "test", "model": "test",
            }}

        dashboard_chat.stream_conversation_turn = fake_stream
        events = list(dashboard_chat.stream_dashboard_chat_turn(
            "Don't run that yet.", use_ai=True, session_id=session["id"], operation_id=followup_operation, draft_already_cleared=True,
        ))
        names = [item.get("event") for item in events]
        require(observed_statuses == ["cancelled"], f"provider started before pending hold was persisted: {observed_statuses}")
        require(names.index("action_result") < names.index("delta"), "pending hold result was not visible before provider response")
        require(router.load_chat_action(target["id"])["status"] == "cancelled", "pending target escaped pre-provider hold")


def test_rendered_javascript_and_narrow_portal_layout() -> None:
    source = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8") + (AGENT / "dashboard_chat_styles.py").read_text(encoding="utf-8")
    for token in ("max-width:100%", "min-width:0", "overflow-wrap:anywhere", "Earlier preserved attempts"):
        require(token in source, f"dashboard source omitted {token}")
    html = dashboard_chat.render_realtime_chat_panel(None, compact=True)
    scripts: list[str] = []
    cursor = 0
    while True:
        start = html.find("<script>", cursor)
        if start < 0:
            break
        end = html.find("</script>", start)
        require(end >= 0, "rendered script tag was not closed")
        scripts.append(html[start + 8:end])
        cursor = end + 9
    require(scripts, "no rendered JavaScript found")
    with tempfile.TemporaryDirectory(prefix="eidolon-v1080-3-js-") as raw:
        path = Path(raw) / "rendered.js"
        path.write_text("\n".join(scripts), encoding="utf-8")
        try:
            result = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True, timeout=30)
        except FileNotFoundError:
            return
        require(result.returncode == 0, f"rendered JavaScript syntax failed: {result.stderr.strip()}")


def test_operational_receipts_remain_nonvectorized() -> None:
    source = (AGENT / "chat_action_router.py").read_text(encoding="utf-8")
    require(source.count("vectorize=False") >= 3, "new follow-up or execution receipts may synchronously vectorize")
    follow_up_start = source.index("def propose_chat_action_follow_up")
    follow_up_end = source.index("\ndef propose_chat_action(", follow_up_start)
    require("vectorize=False" in source[follow_up_start:follow_up_end], "follow-up receipt invokes synchronous embeddings")


def test_chat_surfaces_forward_bounded_timeout() -> None:
    dashboard_source = (AGENT / "dashboard.py").read_text(encoding="utf-8")
    api_source = (AGENT / "api_server.py").read_text(encoding="utf-8")
    console_source = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
    require("timeout_seconds=180 if not dry_run else None" in dashboard_source, "dashboard chat-action execution lost the 180-second ceiling")
    require("timeout_seconds=180 if not dry_run else None" in api_source, "chat-action API execution lost the 180-second ceiling")
    require("timeout_seconds=180" in console_source, "conversation-launched action execution lost the 180-second ceiling")


def test_release_verification_registration_is_exactly_once() -> None:
    source = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
    require(source.count('"daily-conversation-operator-soak-fixtures"') == 1, "v1080.3 soak stage is not registered exactly once")
    require(source.count('"tools/v1080_3_daily_conversation_operator_soak_tests.py"') == 1, "v1080.3 soak suite path is not registered exactly once")
    require(source.count('"conversational-control-portal-regression-fixtures"') == 1, "v1080.2 portal regression stage is not registered exactly once")
    require(source.count('"tools/v1080_2_conversational_control_portal_tests.py"') == 1, "v1080.2 portal suite path is not registered exactly once")


TESTS: tuple[tuple[str, Callable[[], None]], ...] = (
    ("follow_up_phrase_matrix", test_follow_up_phrase_matrix),
    ("follow_up_false_positive_resistance", test_follow_up_false_positive_resistance),
    ("recent_session_binding_and_stale_refusal", test_recent_session_binding_and_stale_refusal),
    ("inflight_action_binding_is_session_scoped", test_inflight_action_binding_is_session_scoped),
    ("follow_up_provider_guidance_forbids_false_completion", test_follow_up_provider_guidance_forbids_false_completion),
    ("status_follow_up_is_read_only_and_deduplicated", test_status_follow_up_is_read_only_and_deduplicated),
    ("retry_preserves_attempt_chain_and_exactly_once", test_retry_preserves_attempt_chain_and_exactly_once),
    ("concurrent_retry_delivery_starts_one_attempt", test_concurrent_retry_delivery_starts_one_attempt),
    ("pending_cancel_prevents_later_execution", test_pending_cancel_prevents_later_execution),
    ("running_or_terminal_cancel_is_not_faked", test_running_or_terminal_cancel_is_not_faked),
    ("approval_follow_up_never_grants_approval", test_approval_follow_up_never_grants_approval),
    ("context_reconciles_retry_without_raw_output", test_context_reconciles_retry_without_raw_output),
    ("card_rehydrates_latest_attempt_and_preserves_privacy", test_card_rehydrates_latest_attempt_and_preserves_privacy),
    ("cancelled_state_rejects_stale_overwrite", test_cancelled_state_rejects_stale_overwrite),
    ("capability_summary_is_registry_derived", test_capability_summary_is_registry_derived),
    ("long_session_history_remains_bounded_and_clean", test_long_session_history_remains_bounded_and_clean),
    ("stream_event_ordering_for_direct_action", test_stream_event_ordering_for_direct_action),
    ("pending_hold_applies_before_provider_start", test_pending_hold_applies_before_provider_start),
    ("rendered_javascript_and_narrow_portal_layout", test_rendered_javascript_and_narrow_portal_layout),
    ("operational_receipts_remain_nonvectorized", test_operational_receipts_remain_nonvectorized),
    ("chat_surfaces_forward_bounded_timeout", test_chat_surfaces_forward_bounded_timeout),
    ("release_verification_registration_is_exactly_once", test_release_verification_registration_is_exactly_once),
)


def main() -> int:
    checks: list[dict[str, str]] = []
    passed = 0
    for name, test in TESTS:
        try:
            test()
        except Exception as error:
            checks.append({"name": name, "status": "fail", "message": f"{type(error).__name__}: {error}"})
        else:
            passed += 1
            checks.append({"name": name, "status": "pass", "message": ""})
    report = {
        "suite": "v1080.3-daily-conversation-operator-soak",
        "passed": passed,
        "total": len(TESTS),
        "status": "pass" if passed == len(TESTS) else "fail",
        "checks": checks,
    }
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
