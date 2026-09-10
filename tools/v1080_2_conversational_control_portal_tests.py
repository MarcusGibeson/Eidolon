from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))

import chat_action_router as router
import command_runner
import conversation_sessions as sessions
import dashboard_chat_console as dashboard_chat
from command_runner import CommandRunResult
from conversation_action_portal import (
    action_context_summary,
    build_action_portal_state,
    sanitize_action_portal_state,
)
from conversation_quality import classify_conversation_quality


class Failure(AssertionError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Failure(message)


@contextmanager
def isolated_action_store():
    with tempfile.TemporaryDirectory(prefix="eidolon-v1080-2-actions-") as raw:
        root = Path(raw)
        old_dir = router.CHAT_ACTIONS_DIR
        old_readme = router.CHAT_ACTIONS_README
        old_store = router.store_memory
        old_run = router.run_approved_command
        old_suggest = router.suggest_patch
        old_approval = router.create_approval
        router.CHAT_ACTIONS_DIR = root / "chat_actions"
        router.CHAT_ACTIONS_README = router.CHAT_ACTIONS_DIR / "README.md"
        router.store_memory = lambda *_args, **_kwargs: None
        try:
            yield root
        finally:
            router.CHAT_ACTIONS_DIR = old_dir
            router.CHAT_ACTIONS_README = old_readme
            router.store_memory = old_store
            router.run_approved_command = old_run
            router.suggest_patch = old_suggest
            router.create_approval = old_approval


@contextmanager
def isolated_session_store():
    with tempfile.TemporaryDirectory(prefix="eidolon-v1080-2-sessions-") as raw:
        root = Path(raw)
        originals = {
            "CONVERSATION_SESSIONS_DIR": sessions.CONVERSATION_SESSIONS_DIR,
            "ACTIVE_SESSION_FILE": sessions.ACTIVE_SESSION_FILE,
            "CONVERSATION_DRAFTS_DIR": sessions.CONVERSATION_DRAFTS_DIR,
            "LEGACY_DASHBOARD_CHAT_DIR": sessions.LEGACY_DASHBOARD_CHAT_DIR,
            "LEGACY_DASHBOARD_CHAT_IMPORT_FILE": sessions.LEGACY_DASHBOARD_CHAT_IMPORT_FILE,
        }
        sessions.CONVERSATION_SESSIONS_DIR = root / "conversation_sessions"
        sessions.ACTIVE_SESSION_FILE = sessions.CONVERSATION_SESSIONS_DIR / "active_session.json"
        sessions.CONVERSATION_DRAFTS_DIR = sessions.CONVERSATION_SESSIONS_DIR / "drafts"
        sessions.LEGACY_DASHBOARD_CHAT_DIR = root / "legacy_dashboard_chat"
        sessions.LEGACY_DASHBOARD_CHAT_IMPORT_FILE = sessions.CONVERSATION_SESSIONS_DIR / "legacy_dashboard_chat_import.json"
        try:
            yield root
        finally:
            for key, value in originals.items():
                setattr(sessions, key, value)


def test_routing_matrix() -> None:
    cases = {
        "Please run diagnostics.": "run_diagnostics",
        "Could you do a maintainence scan please?": "maintenance_scan",
        "How is your system health?": "run_diagnostics",
        "Please check settings health.": "settings_health",
        "What's waiting for approval?": "approval_inbox",
        "Where are we on the tasks?": "task_status",
        "Where are we on the project?": "project_status",
        "How is your memory?": "memory_status",
        "Any notifications for me?": "notifications",
        "What should be the next thing we work on you for?": "self_development_cycle",
        "What can you do?": "supervised_capabilities",
    }
    with isolated_action_store():
        for phrase, expected in cases.items():
            actual = router.propose_chat_action(phrase, save=False)
            require(actual.get("intent") == expected, f"{phrase!r} routed to {actual.get('intent')!r}, expected {expected!r}")


def test_false_positive_resistance() -> None:
    phrases = (
        "I hope everything is working out with your friend.",
        "My bicycle needs maintenance before winter.",
        "The project in that novel was strange.",
        "Your memory of that movie made me laugh.",
        "I got an approval notification from my bank.",
        "What model of car do you like?",
    )
    with isolated_action_store():
        for phrase in phrases:
            profile = classify_conversation_quality(phrase)
            action = router.propose_chat_action(phrase, save=False)
            require(not profile.should_analyze_action, f"casual phrase was classified as an operator action: {phrase}")
            require(action.get("intent") == "conversation_only", f"casual phrase routed to {action.get('intent')}: {phrase}")


def test_capability_truthfulness() -> None:
    text = router.supervised_capability_summary().lower()
    for phrase in ("diagnostics", "maintenance", "approval", "task", "project", "memory", "notifications", "self-development"):
        require(phrase in text, f"capability summary omitted {phrase}")
    with isolated_action_store():
        action = router.propose_chat_action("What supervised actions can you handle?", save=False)
    combined = (str(action.get("summary")) + " " + str(action.get("explanation"))).lower()
    require("unrestricted shell" in combined, "capability response omitted shell boundary")
    require("model management" in combined and "provider switching" in combined, "capability response omitted provider/model boundary")
    require(action.get("status") == "info", "capability action should be informational")
    portal = build_action_portal_state(action)
    require(portal and portal.get("status") == "completed", "informational capability card should rehydrate as completed, not blocked")


def test_deduplicated_proposal() -> None:
    with isolated_action_store():
        first = router.propose_chat_action("Run diagnostics", save=True, deduplication_key="conversation_20260718T120000_abcdef123456")
        second = router.propose_chat_action("Run diagnostics", save=True, deduplication_key="conversation_20260718T120000_abcdef123456")
        require(first.get("id") == second.get("id"), "duplicate operation created a second proposal")
        records = list(router.CHAT_ACTIONS_DIR.glob("*.json"))
        require(len(records) == 1, f"expected one persisted proposal, found {len(records)}")


def test_concurrent_exactly_once_execution() -> None:
    with isolated_action_store():
        action = router.propose_chat_action("Run diagnostics", save=True, deduplication_key="conversation_20260718T120001_abcdef123456")
        entered = threading.Event()
        release = threading.Event()
        calls: list[int | None] = []

        def fake_run(command: str, dry_run: bool = False, timeout_seconds: int | None = None) -> CommandRunResult:
            calls.append(timeout_seconds)
            entered.set()
            require(release.wait(3), "test execution barrier timed out")
            return CommandRunResult(True, command, ["python"], return_code=0, stdout="PRIVATE RAW OUTPUT", message="Diagnostics completed.")

        router.run_approved_command = fake_run
        results: list[object] = []
        thread = threading.Thread(target=lambda: results.append(router.execute_chat_action(action["id"], timeout_seconds=180)))
        thread.start()
        require(entered.wait(2), "first execution never entered runner")
        duplicate = router.execute_chat_action(action["id"], timeout_seconds=180)
        release.set()
        thread.join(3)
        require(not thread.is_alive(), "first execution did not finish")
        require(len(calls) == 1, f"runner called {len(calls)} times during duplicate delivery")
        require(duplicate.replayed and duplicate.status == "running", "duplicate while running did not return a non-executing replay")
        replay = router.execute_chat_action(action["id"], timeout_seconds=180)
        require(replay.replayed and replay.ok, "terminal duplicate did not replay persisted completion")
        require(len(calls) == 1, "terminal replay executed the command again")
        require(calls == [180], f"chat timeout was not forwarded exactly: {calls}")


def test_timeout_and_safe_retry() -> None:
    with isolated_action_store():
        action = router.propose_chat_action("Run diagnostics", save=True, deduplication_key="conversation_20260718T120002_abcdef123456")
        calls = 0

        def fake_run(command: str, dry_run: bool = False, timeout_seconds: int | None = None) -> CommandRunResult:
            nonlocal calls
            calls += 1
            if calls == 1:
                return CommandRunResult(False, command, ["python"], error="Command timed out after 180 seconds.")
            return CommandRunResult(True, command, ["python"], return_code=0, message="Diagnostics completed after retry.")

        router.run_approved_command = fake_run
        first = router.execute_chat_action(action["id"], timeout_seconds=180)
        persisted = router.load_chat_action(action["id"])
        portal = build_action_portal_state(persisted, persisted.get("result") if persisted else None)
        require(first.status == "timed_out", f"timeout stored as {first.status}")
        require(portal and portal.get("retry_allowed"), "safe timed-out action did not offer explicit retry")
        duplicate_failure = router.execute_chat_action(action["id"], timeout_seconds=180)
        require(duplicate_failure.replayed and calls == 1, "duplicate delivery retried a timed-out action without explicit permission")
        second = router.execute_chat_action(action["id"], timeout_seconds=180, retry=True)
        third = router.execute_chat_action(action["id"], timeout_seconds=180)
        require(second.ok and second.status == "executed", "explicit timeout retry did not complete")
        require(third.replayed and calls == 2, "completed retry replayed the command")


def test_running_portal_is_redacted() -> None:
    action = {
        "id": "chat_action_test",
        "intent": "run_diagnostics",
        "title": "Run diagnostics",
        "summary": "Run a bounded diagnostic report.",
        "execution_mode": "direct_command",
        "risk_level": "low",
        "status": "running",
        "command": "python secret.py --token hunter2",
        "user_request": "private request",
    }
    portal = build_action_portal_state(action)
    encoded = json.dumps(portal, sort_keys=True)
    require(portal and portal.get("status") == "running", "running state not normalized")
    require("no terminal result" in str(portal.get("message")).lower(), "running state did not explain missing terminal evidence")
    for secret in ("secret.py", "hunter2", "private request"):
        require(secret not in encoded, f"portal leaked {secret}")
    require("command" not in portal and "user_request" not in portal, "portal retained raw command/request fields")


def test_session_rehydration_and_context_redaction() -> None:
    with isolated_action_store(), isolated_session_store():
        session = sessions.create_conversation_session("Portal test", select_session=False)
        turn_id = "conversation_20260718T120003_abcdef123456"
        sessions.append_conversation_turn(
            session["id"], turn_id=turn_id, user_message="Run diagnostics", assistant_response="I will check it.",
            completion_state="completed", success=True, provider="test", model="test", select_session=False,
        )
        action = router.propose_chat_action("Run diagnostics", save=True, deduplication_key=turn_id)
        action["status"] = "executed"
        action["result"] = {"ok": True, "message": "Diagnostics completed.", "stdout": "RAW PRIVATE OUTPUT", "command": "private command"}
        router.save_chat_action(action)
        portal = build_action_portal_state(action, action["result"])
        sessions.update_conversation_turn_action(session["id"], turn_id, portal)
        history = sessions.conversation_history_for_prompt(session["id"])
        require(len(history) == 1 and "action_status_summary" in history[0], "persisted action status missing from prompt history")
        encoded = json.dumps(history)
        require("completed" in encoded.lower(), "completion state missing from concise context")
        require("RAW PRIVATE OUTPUT" not in encoded and "private command" not in encoded, "prompt history leaked raw action evidence")
        require("Persisted evidence exists" in history[0]["action_status_summary"], "context did not anchor claims to persisted evidence")
        turn = sessions.conversation_session_turns(session["id"])[0]
        html = dashboard_chat._render_action_portal_card(session["id"], turn)
        require("Rehydrated from redacted persisted state" in html, "reload card did not identify persisted rehydration")
        require("RAW PRIVATE OUTPUT" not in html and "private command" not in html, "rehydrated HTML leaked raw evidence")


def test_fallback_rehydration_without_session_snapshot() -> None:
    with isolated_action_store(), isolated_session_store():
        session = sessions.create_conversation_session("Fallback test", select_session=False)
        turn_id = "conversation_20260718T120004_abcdef123456"
        sessions.append_conversation_turn(
            session["id"], turn_id=turn_id, user_message="Check settings health", assistant_response="I will check the configured health.",
            completion_state="completed", success=True, provider="test", model="test", select_session=False,
        )
        action = router.propose_chat_action("Check settings health", save=True, deduplication_key=turn_id)
        action["status"] = "failed"
        action["result"] = {"ok": False, "error": "Health check failed safely.", "stderr": "PRIVATE"}
        router.save_chat_action(action)
        history = sessions.conversation_history_for_prompt(session["id"])
        require("failed" in history[0].get("action_status_summary", "").lower(), "governed-action fallback did not rehydrate failed status")
        require("PRIVATE" not in json.dumps(history), "fallback leaked raw output")


def test_stale_proposal_cannot_overwrite_completion() -> None:
    with isolated_session_store():
        session = sessions.create_conversation_session("Stale state", select_session=False)
        turn_id = "conversation_20260718T120005_abcdef123456"
        sessions.append_conversation_turn(
            session["id"], turn_id=turn_id, user_message="Run diagnostics", assistant_response="Done.",
            completion_state="completed", success=True, select_session=False,
        )
        base = {"id": "chat_action_stale", "intent": "run_diagnostics", "title": "Run diagnostics", "summary": "Check.", "execution_mode": "direct_command", "risk_level": "low"}
        completed = build_action_portal_state({**base, "status": "executed"}, {"ok": True, "status": "executed", "message": "Completed."})
        proposed = build_action_portal_state({**base, "status": "proposed"})
        sessions.update_conversation_turn_action(session["id"], turn_id, completed)
        sessions.update_conversation_turn_action(session["id"], turn_id, proposed)
        stored = sessions.conversation_session_turns(session["id"])[0]["operator_action"]
        require(stored.get("status") == "completed", "stale proposal replaced terminal completion")


def test_operation_status_exposes_only_redacted_portal() -> None:
    with isolated_action_store():
        operation_id = "conversation_20260718T120006_abcdef123456"
        action = router.propose_chat_action("Run diagnostics", save=True, deduplication_key=operation_id)
        action["status"] = "running"
        action["command"] = "python private.py --secret"
        router.save_chat_action(action)
        portal = dashboard_chat._action_portal_for_operation(operation_id)
        encoded = json.dumps(portal)
        require(portal and portal.get("status") == "running", "operation reconciliation omitted running proposal")
        require("private.py" not in encoded and "--secret" not in encoded, "operation status leaked command content")


def test_modification_and_approval_boundaries() -> None:
    with isolated_action_store():
        patch = router.propose_chat_action("Suggest improvement for conscious_agent/memory.py", save=False)
        apply_patch = router.propose_chat_action("Apply the latest patch", save=False)
        model = router.propose_chat_action("Install a new model", save=False)
        shell = router.propose_chat_action("Execute shell command whoami", save=False)
        require(patch.get("execution_mode") == router.DIRECT_FUNCTION, "patch proposal was not kept proposal-only")
        require(apply_patch.get("execution_mode") == router.APPROVAL, "patch application bypassed approval")
        require(model.get("execution_mode") == router.BLOCKED and model.get("intent") == "blocked_model_provider_management", "model management was not explicitly blocked")
        require(shell.get("execution_mode") == router.BLOCKED and shell.get("intent") == "blocked_unrestricted_shell", "arbitrary shell request was not explicitly blocked")
        require(dashboard_chat._execute_explicit_safe_chat_action(patch) is None, "dashboard auto-executed a modification proposal")
        require(dashboard_chat._execute_explicit_safe_chat_action(apply_patch) is None, "dashboard auto-executed approval work")
        persisted_block = router.propose_chat_action("Install a new model", save=True, save_unknown=False, deduplication_key="conversation_20260718T120007_abcdef123456")
        require(persisted_block.get("intent") == "blocked_model_provider_management", "blocked model request disappeared from the visible portal path")
        require(len(list(router.CHAT_ACTIONS_DIR.glob("*.json"))) == 1, "blocked governed request was not persisted exactly once")


def test_python_uses_active_interpreter() -> None:
    args = command_runner._execution_args(["python", "conscious_agent/main.py", "--status"])
    require(args and Path(args[0]).resolve() == Path(sys.executable).resolve(), "approved Python command did not use active interpreter")


def test_receipts_do_not_vectorize_synchronously() -> None:
    source = (AGENT / "chat_action_router.py").read_text(encoding="utf-8")
    start = source.index("def _store_execution_memory")
    body = source[start: source.index("\ndef ", start + 5)]
    require("vectorize=False" in body, "execution receipt may invoke synchronous embeddings")
    proposal = source[source.index("if save and persistable_intent"):source.index("return action", source.index("if save and persistable_intent"))]
    require("vectorize=False" in proposal, "proposal receipt may invoke synchronous embeddings")


def test_conversation_critical_path_ordering() -> None:
    source = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8") + (AGENT / "dashboard_chat_styles.py").read_text(encoding="utf-8")
    stream_start = source.index("def stream_dashboard_chat_turn")
    block = source[stream_start:source.index("def dashboard_chat_turn_text", stream_start)]
    proposal = block.index("_propose_explicit_chat_action")
    provider = block.index("stream_conversation_turn")
    completion = block.index('"event": "conversation_complete"')
    execution = block.index("_execute_explicit_safe_chat_action")
    require(proposal < provider, "explicit action analysis no longer precedes provider start")
    require(completion < execution, "safe action execution moved before visible conversational completion")


def test_rendered_portal_layout_and_javascript() -> None:
    source = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8") + (AGENT / "dashboard_chat_styles.py").read_text(encoding="utf-8")
    for token in ("max-width:100%", "min-width:0", "overflow-wrap:anywhere", "applyPersistedActionPortal", "initialActionPortal"):
        require(token in source, f"rendering source omitted {token}")
    html = dashboard_chat.render_realtime_chat_panel(None, compact=True)
    scripts = []
    cursor = 0
    while True:
        start = html.find("<script>", cursor)
        if start < 0:
            break
        end = html.find("</script>", start)
        require(end >= 0, "rendered script tag was not closed")
        scripts.append(html[start + len("<script>"):end])
        cursor = end + len("</script>")
    require(scripts, "no rendered JavaScript found")
    with tempfile.TemporaryDirectory(prefix="eidolon-v1080-2-js-") as raw:
        js = Path(raw) / "rendered.js"
        js.write_text("\n".join(scripts), encoding="utf-8")
        try:
            result = subprocess.run(["node", "--check", str(js)], capture_output=True, text=True, timeout=30)
        except FileNotFoundError:
            return
        require(result.returncode == 0, f"rendered JavaScript syntax failed: {result.stderr.strip()}")


def test_current_metadata_and_docs_are_aligned() -> None:
    import release_metadata
    version = str(release_metadata.RUNTIME_VERSION)
    milestone = str(release_metadata.RUNTIME_MILESTONE)
    require(version and milestone.startswith(f"v{version} "), "runtime metadata is internally inconsistent")
    for relative in ("data/settings.json", "data/workspaces/active_project.json", "data/workspaces/projects.json"):
        data = json.loads((ROOT / relative).read_text(encoding="utf-8"))
        require(version in json.dumps(data), f"{relative} did not advance to the current runtime version")
    rendered = dashboard_chat.render_realtime_chat_panel(None, compact=True)
    require(f"data-chat-version='v{version}-" in rendered, "dashboard chat metadata is stale")
    for relative in ("README.md", "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        require(milestone in text, f"{relative} omitted current milestone")

def test_private_receipt_guard_covers_portal() -> None:
    value = {"turns": [{"operator_action": sanitize_action_portal_state({
        "action_id": "chat_action_test", "intent": "diagnostics", "title": "Diagnostics", "summary": "Bounded summary",
        "execution_mode": "direct_command", "risk_level": "low", "status": "completed", "message": "Completed.",
    })}]}
    require(not sessions.session_contains_private_receipt_fields(value), "bounded portal was mistaken for a private receipt")
    value["turns"][0]["operator_action"]["prompt"] = "private"
    require(sessions.session_contains_private_receipt_fields(value), "private prompt field was not rejected")


TESTS: tuple[tuple[str, Callable[[], None]], ...] = (
    ("routing_matrix", test_routing_matrix),
    ("false_positive_resistance", test_false_positive_resistance),
    ("capability_truthfulness", test_capability_truthfulness),
    ("deduplicated_proposal", test_deduplicated_proposal),
    ("concurrent_exactly_once_execution", test_concurrent_exactly_once_execution),
    ("timeout_and_safe_retry", test_timeout_and_safe_retry),
    ("running_portal_is_redacted", test_running_portal_is_redacted),
    ("session_rehydration_and_context_redaction", test_session_rehydration_and_context_redaction),
    ("fallback_rehydration_without_session_snapshot", test_fallback_rehydration_without_session_snapshot),
    ("stale_proposal_cannot_overwrite_completion", test_stale_proposal_cannot_overwrite_completion),
    ("operation_status_exposes_only_redacted_portal", test_operation_status_exposes_only_redacted_portal),
    ("modification_and_approval_boundaries", test_modification_and_approval_boundaries),
    ("python_uses_active_interpreter", test_python_uses_active_interpreter),
    ("receipts_do_not_vectorize_synchronously", test_receipts_do_not_vectorize_synchronously),
    ("conversation_critical_path_ordering", test_conversation_critical_path_ordering),
    ("rendered_portal_layout_and_javascript", test_rendered_portal_layout_and_javascript),
    ("current_metadata_and_docs_are_aligned", test_current_metadata_and_docs_are_aligned),
    ("private_receipt_guard_covers_portal", test_private_receipt_guard_covers_portal),
)


def main() -> int:
    passed = 0
    rows = []
    for name, test in TESTS:
        try:
            test()
        except Exception as error:
            rows.append({"name": name, "status": "fail", "message": f"{type(error).__name__}: {error}"})
        else:
            passed += 1
            rows.append({"name": name, "status": "pass", "message": ""})
    report = {
        "suite": "v1080.2-conversational-control-portal",
        "passed": passed,
        "total": len(TESTS),
        "status": "pass" if passed == len(TESTS) else "fail",
        "checks": rows,
    }
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
