from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
sys.dont_write_bytecode = True
import tempfile
import time
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
import release_metadata
from command_runner import CommandRunResult
from conversation_action_portal import build_action_portal_state, running_claim_is_interrupted


class Failure(AssertionError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Failure(message)


@contextmanager
def isolated_runtime():
    with tempfile.TemporaryDirectory(prefix="eidolon-v1080-5-expansion-") as raw:
        root = Path(raw)
        action_originals = {
            "CHAT_ACTIONS_DIR": router.CHAT_ACTIONS_DIR,
            "CHAT_ACTIONS_README": router.CHAT_ACTIONS_README,
            "store_memory": router.store_memory,
            "run_approved_command": router.run_approved_command,
            "_CHAT_ACTION_INTERRUPTED_CLAIM_SECONDS": router._CHAT_ACTION_INTERRUPTED_CLAIM_SECONDS,
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
        }
        router.CHAT_ACTIONS_DIR = root / "chat_actions"
        router.CHAT_ACTIONS_README = router.CHAT_ACTIONS_DIR / "README.md"
        router.store_memory = lambda *_args, **_kwargs: None
        sessions.CONVERSATION_SESSIONS_DIR = root / "conversation_sessions"
        sessions.ACTIVE_SESSION_FILE = sessions.CONVERSATION_SESSIONS_DIR / "active_session.json"
        sessions.CONVERSATION_DRAFTS_DIR = sessions.CONVERSATION_SESSIONS_DIR / "drafts"
        sessions.LEGACY_DASHBOARD_CHAT_DIR = root / "legacy_dashboard_chat"
        sessions.LEGACY_DASHBOARD_CHAT_IMPORT_FILE = sessions.CONVERSATION_SESSIONS_DIR / "legacy_import.json"
        dashboard_chat.DASHBOARD_CHAT_DIR = root / "dashboard_chat"
        dashboard_chat.DASHBOARD_CHAT_README = dashboard_chat.DASHBOARD_CHAT_DIR / "README.md"
        try:
            yield root
        finally:
            for key, value in action_originals.items():
                setattr(router, key, value)
            for key, value in session_originals.items():
                setattr(sessions, key, value)
            for key, value in dashboard_originals.items():
                setattr(dashboard_chat, key, value)


def _attach_action(session_id: str, operation_id: str, request: str, *, status: str = "failed") -> dict:
    sessions.append_conversation_turn(
        session_id,
        turn_id=operation_id,
        user_message=request,
        assistant_response="I routed that through the supervised controls.",
        completion_state="completed",
        success=True,
        provider="test",
        model="test",
        select_session=False,
    )
    action = router.propose_chat_action(
        request,
        save=True,
        deduplication_key=operation_id,
        conversation_session_id=session_id,
    )
    action["status"] = status
    action["result"] = {"ok": status in {"executed", "completed"}, "message": f"Persisted {status} evidence."}
    action["result_summary"] = router._redacted_result_summary(action, status, action["result"])
    action["result_summary_status"] = status
    router.save_chat_action(action)
    portal = build_action_portal_state(action, action["result"])
    sessions.update_conversation_turn_action(session_id, operation_id, portal or {})
    return action


def _simulate_dead_claim(root: Path, action_id: str, claimant: str = "cli") -> dict:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "chat_action_interrupted_claim_worker.py"),
            "--runtime-root", str(root),
            "--action-id", action_id,
            "--claimant", claimant,
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    require(result.returncode == 0, f"interrupted claim worker failed: {result.stderr.strip()}")
    return json.loads(result.stdout.strip())


def test_named_follow_up_selects_correct_recent_action() -> None:
    with isolated_runtime():
        session = sessions.create_conversation_session("Multiple actions", select_session=False)
        diagnostics = _attach_action(session["id"], "op_diagnostics", "Run diagnostics")
        maintenance = _attach_action(session["id"], "op_maintenance", "Run maintenance scan")
        settings = _attach_action(session["id"], "op_settings", "Check settings health", status="executed")
        follow_up = dashboard_chat._propose_explicit_chat_action(
            "Retry the maintenance check again.", session["id"], operation_id="op_retry_maintenance",
        )
        require(follow_up and follow_up.get("target_action_id") == maintenance.get("id"), "named retry selected the wrong recent action")
        require(follow_up.get("execution_mode") == router.ACTION_RETRY, "named retry was not executable through the bounded retry mode")
        require(follow_up.get("target_action_id") not in {diagnostics.get("id"), settings.get("id")}, "named retry crossed action threads")


def test_ambiguous_generic_retry_is_refused_and_deduplicated() -> None:
    with isolated_runtime():
        session = sessions.create_conversation_session("Ambiguous retry", select_session=False)
        _attach_action(session["id"], "op_diag", "Run diagnostics")
        _attach_action(session["id"], "op_maint", "Run maintenance scan")
        first = dashboard_chat._propose_explicit_chat_action("Try that again.", session["id"], operation_id="op_ambiguous")
        second = dashboard_chat._propose_explicit_chat_action("Try that again.", session["id"], operation_id="op_ambiguous")
        require(first and second and first.get("id") == second.get("id"), "ambiguous retry was not deduplicated")
        require(first.get("intent") == "action_follow_up_ambiguous" and first.get("execution_mode") == router.BLOCKED, "ambiguous retry was not visibly refused")
        result = router.execute_chat_action(first["id"], claimant="conversation")
        require(not result.ok and not result.replayed, "ambiguous retry reached an execution path")
        require(all((item.get("execution_attempt") or 0) == 0 for item in router.list_chat_actions()), "ambiguous retry created an execution attempt")


def test_generic_retry_binds_when_only_one_candidate_is_eligible() -> None:
    with isolated_runtime():
        session = sessions.create_conversation_session("One retry candidate", select_session=False)
        failed = _attach_action(session["id"], "op_failed", "Run diagnostics", status="failed")
        _attach_action(session["id"], "op_done", "Run maintenance scan", status="executed")
        follow_up = dashboard_chat._propose_explicit_chat_action("Retry it.", session["id"], operation_id="op_retry_one")
        require(follow_up and follow_up.get("target_action_id") == failed.get("id"), "single eligible retry candidate was not selected")


def test_named_status_follow_up_selects_settings_action() -> None:
    with isolated_runtime():
        session = sessions.create_conversation_session("Named status", select_session=False)
        _attach_action(session["id"], "op_diag_status", "Run diagnostics", status="executed")
        settings = _attach_action(session["id"], "op_settings_status", "Check settings health", status="executed")
        follow_up = dashboard_chat._propose_explicit_chat_action(
            "Show me the settings health status.", session["id"], operation_id="op_settings_followup",
        )
        require(follow_up and follow_up.get("target_action_id") == settings.get("id"), "named status follow-up selected the wrong action")
        require(follow_up.get("execution_mode") == router.INFO, "status follow-up was not read-only")


def test_cross_interface_claim_owner_is_visible_and_nonduplicating() -> None:
    with isolated_runtime():
        action = router.propose_chat_action("Run diagnostics", save=True)
        with router._chat_action_storage_lock(f"action:{action['id']}"):
            claimed = router._claim_execution_attempt(router.load_chat_action(action["id"]) or action, claimant="cli")
        portal = build_action_portal_state(claimed, {}) or {}
        require(portal.get("status") == "running", "live CLI claim was not running")
        require(portal.get("claim_owner_scope") == "cli" and "command line" in str(portal.get("message") or "").lower(), "dashboard-facing portal omitted CLI ownership")
        replay = router.execute_chat_action(action["id"], claimant="dashboard")
        require(replay.replayed and "command line" in replay.message.lower(), "dashboard did not receive a cross-interface ownership replay")
        require(len((router.load_chat_action(action["id"]) or {}).get("execution_attempts") or []) == 1, "cross-interface status check created a duplicate attempt")


def test_process_death_is_presented_as_interrupted_without_implicit_retry() -> None:
    with isolated_runtime() as root:
        action = router.propose_chat_action("Run diagnostics", save=True)
        _simulate_dead_claim(root, action["id"], claimant="cli")
        persisted = router.load_chat_action(action["id"]) or {}
        interrupted, _reason = running_claim_is_interrupted(persisted)
        require(interrupted, "dead claimant was not detected")
        portal = build_action_portal_state(persisted, persisted.get("result") or {}) or {}
        require(portal.get("status") == "interrupted" and portal.get("retry_allowed"), "dead claim did not become a recoverable interrupted portal state")
        calls: list[str] = []
        router.run_approved_command = lambda command, **_kwargs: calls.append(command)
        replay = router.execute_chat_action(action["id"], claimant="dashboard")
        require(replay.replayed and replay.status == "interrupted", "ordinary replay did not persist interrupted evidence")
        require(not calls, "interrupted action retried without explicit retry authority")


def test_explicit_retry_recovers_interrupted_claim_once() -> None:
    with isolated_runtime() as root:
        action = router.propose_chat_action("Run diagnostics", save=True)
        _simulate_dead_claim(root, action["id"], claimant="cli")
        calls = 0

        def fake_run(command: str, **_kwargs) -> CommandRunResult:
            nonlocal calls
            calls += 1
            return CommandRunResult(True, command, [sys.executable], return_code=0, message="Recovered.", stdout="PRIVATE RECOVERY OUTPUT")

        router.run_approved_command = fake_run
        recovered = router.execute_chat_action(action["id"], retry=True, claimant="dashboard")
        replay = router.execute_chat_action(action["id"], retry=True, claimant="api")
        require(recovered.ok and recovered.status == "executed" and replay.replayed, "interrupted retry did not recover exactly once")
        require(calls == 1, f"interrupted retry invoked the runner {calls} times")
        saved = router.load_chat_action(action["id"]) or {}
        attempts = saved.get("execution_attempts") or []
        require([item.get("status") for item in attempts] == ["interrupted", "executed"], "interrupted and recovered attempts were not preserved separately")
        require(attempts[1].get("retry_of_attempt_id") == attempts[0].get("attempt_id"), "recovery attempt was not linked")
        require("PRIVATE RECOVERY OUTPUT" not in json.dumps(attempts), "raw recovery output was duplicated into attempt history")


def test_stale_unverifiable_claim_uses_bounded_recovery_window() -> None:
    with isolated_runtime():
        action = router.propose_chat_action("Run diagnostics", save=True)
        action["status"] = "running"
        action["execution_attempt"] = 1
        action["active_attempt_id"] = f"{action['id']}:attempt:1"
        action["execution_attempts"] = [{
            "attempt_id": action["active_attempt_id"], "attempt_number": 1, "status": "running",
            "started_at": "2026-01-01T00:00:00", "completed_at": "", "retry_of_attempt_id": "",
            "claimant_scope": "api", "result": {},
        }]
        action["claim_owner"] = {
            "scope": "api", "pid": 0, "host": "another-host.invalid",
            "claimed_epoch": time.time() - 600,
        }
        router.save_chat_action(action)
        portal = build_action_portal_state(router.load_chat_action(action["id"]), {}) or {}
        require(portal.get("status") == "interrupted", "expired unverifiable claim remained running forever")


def test_activity_timeline_is_ordered_and_redacted() -> None:
    with isolated_runtime():
        router.run_approved_command = lambda command, **_kwargs: CommandRunResult(
            True, command, [sys.executable], return_code=0, message="Done.", stdout="RAW SECRET OUTPUT",
        )
        action = router.propose_chat_action("Run diagnostics", save=True)
        result = router.execute_chat_action(action["id"], claimant="conversation")
        saved = router.load_chat_action(action["id"]) or {}
        portal = build_action_portal_state(saved, result.__dict__) or {}
        types = [item.get("type") for item in portal.get("activity_timeline") or []]
        require(types == ["proposal_created", "execution_claimed", "attempt_started", "execution_completed"], f"action timeline ordering drifted: {types}")
        require("RAW SECRET OUTPUT" not in json.dumps(portal), "raw command output entered the portal timeline")
        require("RAW SECRET OUTPUT" not in json.dumps(saved.get("action_events") or []), "raw command output entered persisted action events")
        require("RAW SECRET OUTPUT" in json.dumps(saved.get("result") or {}), "governed current result evidence was unexpectedly discarded")


def test_conversation_context_uses_redacted_result_summary_only() -> None:
    with isolated_runtime():
        session = sessions.create_conversation_session("Redacted summary", select_session=False)
        operation_id = "op_redacted_summary"
        sessions.append_conversation_turn(
            session["id"], turn_id=operation_id, user_message="Run diagnostics",
            assistant_response="I completed the supervised check.", completion_state="completed", success=True,
            provider="test", model="test", select_session=False,
        )
        router.run_approved_command = lambda command, **_kwargs: CommandRunResult(
            False, command, [sys.executable], error="PRIVATE ERROR BODY", stderr="PRIVATE STDERR",
        )
        action = router.propose_chat_action(
            "Run diagnostics", save=True, deduplication_key=operation_id, conversation_session_id=session["id"],
        )
        result = router.execute_chat_action(action["id"], claimant="conversation")
        portal = build_action_portal_state(router.load_chat_action(action["id"]), result.__dict__) or {}
        sessions.update_conversation_turn_action(session["id"], operation_id, portal)
        history = sessions.conversation_history_for_prompt(session["id"])
        serialized = json.dumps(history)
        require("PRIVATE ERROR BODY" not in serialized and "PRIVATE STDERR" not in serialized, "raw failure evidence entered conversation context")
        require("failed safely" in serialized.lower() or "failed" in serialized.lower(), "conversation context omitted the concise terminal state")


def test_action_event_history_is_bounded_with_summary() -> None:
    with isolated_runtime():
        action = router.propose_chat_action("Run diagnostics", save=False)
        for index in range(65):
            router._append_action_event(action, "soak_event", "running", f"Redacted event {index}.", attempt_number=index + 1, owner_scope="dashboard")
        router.save_chat_action(action)
        saved = router.load_chat_action(action["id"]) or {}
        require(len(saved.get("action_events") or []) == router._MAX_ACTION_EVENTS, "action event history exceeded its bound")
        summary = saved.get("event_history_summary") or {}
        require(int(summary.get("pruned_event_count") or 0) == 26, f"event compaction count drifted: {summary}")
        portal = build_action_portal_state(saved, {}) or {}
        require(len(portal.get("activity_timeline") or []) <= 12 and int(portal.get("timeline_pruned") or 0) == 26, "portal timeline did not expose bounded compaction evidence")


def test_execution_attempt_history_is_bounded_and_preserves_failure_summary() -> None:
    with isolated_runtime():
        action = router.propose_chat_action("Run diagnostics", save=False)
        attempts = []
        for number in range(1, 21):
            status = "failed" if number in {3, 8} else "executed"
            attempts.append({
                "attempt_id": f"{action['id']}:attempt:{number}", "attempt_number": number, "status": status,
                "started_at": f"2026-07-18T18:{number:02d}:00", "completed_at": f"2026-07-18T18:{number:02d}:01",
                "retry_of_attempt_id": f"{action['id']}:attempt:{number - 1}" if number > 1 else "",
                "claimant_scope": "dashboard", "result": {"ok": status == "executed", "stderr": f"PRIVATE {number}", "message": status},
            })
        action["execution_attempt"] = 20
        action["execution_attempts"] = attempts
        action["status"] = "executed"
        action["result"] = {"ok": True, "stdout": "CURRENT GOVERNED OUTPUT"}
        router.save_chat_action(action)
        saved = router.load_chat_action(action["id"]) or {}
        require(len(saved.get("execution_attempts") or []) == router._MAX_EXECUTION_ATTEMPTS, "execution attempt history exceeded its bound")
        summary = saved.get("execution_history_summary") or {}
        require(int(summary.get("pruned_attempt_count") or 0) == 8, f"attempt compaction count drifted: {summary}")
        require((summary.get("latest_pruned_failure") or {}).get("attempt_number") == 8, "compaction lost the latest pruned failure evidence")
        require("PRIVATE" not in json.dumps(saved.get("execution_attempts") or []), "retained attempt history contains raw output")
        require("CURRENT GOVERNED OUTPUT" in json.dumps(saved.get("result") or {}), "current governed result was removed during compaction")


def test_reload_card_shows_owner_timeline_and_restored_marker() -> None:
    with isolated_runtime():
        session = sessions.create_conversation_session("Restored owner", select_session=False)
        operation_id = "op_restored_owner"
        action = router.propose_chat_action("Run diagnostics", save=True, deduplication_key=operation_id, conversation_session_id=session["id"])
        with router._chat_action_storage_lock(f"action:{action['id']}"):
            claimed = router._claim_execution_attempt(router.load_chat_action(action["id"]) or action, claimant="cli")
        turn = sessions.append_conversation_turn(
            session["id"], turn_id=operation_id, user_message="Run diagnostics",
            assistant_response="It is running through the supervised controls.", completion_state="completed", success=True,
            provider="test", model="test", select_session=False, operator_action=build_action_portal_state(claimed, {}),
        )
        html = dashboard_chat._render_action_portal_card(session["id"], turn)
        require("data-action-timeline" in html and "execution_claimed" not in html, "restored card omitted timeline markup or exposed internal event type directly")
        require("Execution owner: the command line" in html, "restored card omitted cross-interface owner")
        require("data-action-event-restored='true'" in html, "restored timeline omitted its non-executing rehydration event")


def test_rendered_javascript_and_narrow_timeline_layout() -> None:
    source = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8") + (AGENT / "dashboard_chat_styles.py").read_text(encoding="utf-8")
    require("function renderActionTimeline" in source and "details.dataset.actionTimeline" in source, "live cards do not render the persisted activity timeline")
    require(".chat-action-timeline ol { padding-left:18px; }" in source, "narrow layout lacks timeline containment")
    html = dashboard_chat.render_realtime_chat_panel(None, compact=True)
    scripts: list[str] = []
    cursor = 0
    while True:
        start = html.find("<script>", cursor)
        if start < 0:
            break
        end = html.find("</script>", start)
        require(end >= 0, "rendered script tag is unclosed")
        scripts.append(html[start + 8:end])
        cursor = end + 9
    require(scripts, "no rendered JavaScript found")
    with tempfile.TemporaryDirectory(prefix="eidolon-v1080-5-js-") as raw:
        path = Path(raw) / "rendered.js"
        path.write_text("\n".join(scripts), encoding="utf-8")
        try:
            result = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True, timeout=30)
        except FileNotFoundError:
            return
        require(result.returncode == 0, f"rendered JavaScript syntax failed: {result.stderr.strip()}")


def test_current_metadata_and_release_registration_are_aligned() -> None:
    current = tuple(int(part) for part in release_metadata.RUNTIME_VERSION.split("."))
    require(current >= (1080, 5), "runtime metadata predates v1080.5")
    history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
    require("# v1080.5 Desktop Alpha Daily-Use Expansion" in history, "v1080.5 historical milestone disappeared")
    for relative in ("data/settings.json", "data/workspaces/active_project.json", "data/workspaces/projects.json"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        require(release_metadata.RUNTIME_VERSION in text, f"{relative} is not aligned to the current runtime")
    source = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
    require(source.count('"desktop-alpha-daily-use-expansion-fixtures"') == 1, "v1080.5 release stage is not registered exactly once")
    require(source.count('"tools/v1080_5_desktop_alpha_daily_use_expansion_tests.py"') == 1, "v1080.5 suite path is not registered exactly once")
    require(source.count('"desktop-alpha-candidate-consolidation-fixtures"') == 1, "v1080.4 retained stage drifted")


def test_source_tree_remains_source_only() -> None:
    require(not (ROOT / "data" / "projects.json").exists(), "source tree contains data/projects.json")
    forbidden = ("data/chat_actions", "data/conversations", "data/approvals", "data/memories.json", ".venv", "__pycache__")
    paths = [path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if path.is_file()]
    for token in forbidden:
        require(not any(token in path for path in paths), f"source tree contains forbidden runtime token: {token}")


TESTS: tuple[tuple[str, Callable[[], None]], ...] = (
    ("named_follow_up_selects_correct_recent_action", test_named_follow_up_selects_correct_recent_action),
    ("ambiguous_generic_retry_is_refused_and_deduplicated", test_ambiguous_generic_retry_is_refused_and_deduplicated),
    ("generic_retry_binds_when_only_one_candidate_is_eligible", test_generic_retry_binds_when_only_one_candidate_is_eligible),
    ("named_status_follow_up_selects_settings_action", test_named_status_follow_up_selects_settings_action),
    ("cross_interface_claim_owner_is_visible_and_nonduplicating", test_cross_interface_claim_owner_is_visible_and_nonduplicating),
    ("process_death_is_presented_as_interrupted_without_implicit_retry", test_process_death_is_presented_as_interrupted_without_implicit_retry),
    ("explicit_retry_recovers_interrupted_claim_once", test_explicit_retry_recovers_interrupted_claim_once),
    ("stale_unverifiable_claim_uses_bounded_recovery_window", test_stale_unverifiable_claim_uses_bounded_recovery_window),
    ("activity_timeline_is_ordered_and_redacted", test_activity_timeline_is_ordered_and_redacted),
    ("conversation_context_uses_redacted_result_summary_only", test_conversation_context_uses_redacted_result_summary_only),
    ("action_event_history_is_bounded_with_summary", test_action_event_history_is_bounded_with_summary),
    ("execution_attempt_history_is_bounded_and_preserves_failure_summary", test_execution_attempt_history_is_bounded_and_preserves_failure_summary),
    ("reload_card_shows_owner_timeline_and_restored_marker", test_reload_card_shows_owner_timeline_and_restored_marker),
    ("rendered_javascript_and_narrow_timeline_layout", test_rendered_javascript_and_narrow_timeline_layout),
    ("current_metadata_and_release_registration_are_aligned", test_current_metadata_and_release_registration_are_aligned),
    ("source_tree_remains_source_only", test_source_tree_remains_source_only),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.parse_args()
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
        "suite": "v1080.5-desktop-alpha-daily-use-expansion",
        "passed": passed,
        "total": len(TESTS),
        "status": "pass" if passed == len(TESTS) else "fail",
        "checks": checks,
        "native_provider_contacted": False,
        "model_management_performed": False,
        "release_authorized": False,
    }
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
