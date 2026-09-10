from __future__ import annotations

import argparse
import json
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
from conversation_action_portal import build_action_portal_state, portal_update_is_safe


class Failure(AssertionError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Failure(message)


@contextmanager
def isolated_runtime():
    with tempfile.TemporaryDirectory(prefix="eidolon-v1080-4-consolidation-") as raw:
        root = Path(raw)
        action_originals = {
            "CHAT_ACTIONS_DIR": router.CHAT_ACTIONS_DIR,
            "CHAT_ACTIONS_README": router.CHAT_ACTIONS_README,
            "store_memory": router.store_memory,
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


def _action(status: str, attempt: int, *, mode: str = router.DIRECT_COMMAND, action_id: str = "chat_action_portal") -> dict:
    attempts = []
    if attempt:
        attempts.append({
            "attempt_id": f"{action_id}:attempt:{attempt}",
            "attempt_number": attempt,
            "status": status,
            "result": {"ok": status in {"executed", "completed"}, "message": f"Attempt {attempt} is {status}."},
        })
    return {
        "id": action_id,
        "created_at": "2026-07-18T18:00:00",
        "updated_at": f"2026-07-18T18:0{attempt}:00",
        "intent": "diagnostics",
        "title": "Run diagnostics",
        "summary": "Run the allowlisted diagnostics check.",
        "execution_mode": mode,
        "risk_level": "low",
        "status": status,
        "execution_attempt": attempt,
        "execution_attempts": attempts,
        "result": attempts[-1]["result"] if attempts else {},
    }


def test_retry_running_transition_requires_new_attempt() -> None:
    failed = build_action_portal_state(_action("failed", 1))
    running_new = build_action_portal_state(_action("running", 2))
    running_stale = build_action_portal_state(_action("running", 1))
    require(portal_update_is_safe(failed, running_new), "new retry attempt could not advance failed state to running")
    require(not portal_update_is_safe(failed, running_stale), "same-attempt running state overwrote terminal failure")


def test_older_attempt_cannot_replace_newer_evidence() -> None:
    current = build_action_portal_state(_action("failed", 3))
    stale = build_action_portal_state(_action("completed", 2))
    require(not portal_update_is_safe(current, stale), "older attempt replaced newer terminal evidence")


def test_pending_approval_can_be_cancelled() -> None:
    approval = build_action_portal_state(_action("approval_required", 0, mode=router.APPROVAL))
    cancelled_action = _action("cancelled", 0, mode=router.APPROVAL)
    cancelled_action["result"] = {"ok": True, "message": "Cancelled before approval creation."}
    cancelled = build_action_portal_state(cancelled_action, cancelled_action["result"])
    require(approval and approval.get("status") == "awaiting_approval", "approval proposal did not normalize")
    require(portal_update_is_safe(approval, cancelled), "pending approval could not persist an exact cancellation")


def test_conversation_context_tracks_running_retry() -> None:
    with isolated_runtime():
        session = sessions.create_conversation_session("Retry context", select_session=False)
        operation_id = "conversation_retry_context"
        sessions.append_conversation_turn(
            session["id"], turn_id=operation_id, user_message="Run diagnostics",
            assistant_response="I will run the supervised check.", completion_state="completed", success=True,
            provider="test", model="test", select_session=False,
        )
        failed_action = _action("failed", 1)
        failed_action["deduplication_key"] = operation_id
        failed_action["conversation_session_id"] = session["id"]
        router.save_chat_action(failed_action)
        sessions.update_conversation_turn_action(session["id"], operation_id, build_action_portal_state(failed_action, failed_action["result"]))

        running = _action("running", 2)
        running["deduplication_key"] = operation_id
        running["conversation_session_id"] = session["id"]
        router.save_chat_action(running)
        history = sessions.conversation_history_for_prompt(session["id"])
        summary = history[0].get("action_status_summary", "")
        require("running" in summary.lower(), "conversation context kept stale failed status during retry")
        require("attempt 2" in summary.lower(), "conversation context omitted the active retry attempt")


def test_server_cards_use_one_canonical_contract() -> None:
    with isolated_runtime():
        session = sessions.create_conversation_session("Card contract", select_session=False)
        operation_id = "conversation_card_contract"
        action = _action("failed", 1)
        action["deduplication_key"] = operation_id
        action["conversation_session_id"] = session["id"]
        router.save_chat_action(action)
        turn = sessions.append_conversation_turn(
            session["id"], turn_id=operation_id, user_message="Run diagnostics",
            assistant_response="The supervised check failed safely.", completion_state="completed", success=True,
            provider="test", model="test", select_session=False,
            operator_action=build_action_portal_state(action, action["result"]),
        )
        html = dashboard_chat._render_action_portal_card(session["id"], turn)
        require("class='chat-action-portal chat-inline-action'" in html, "server card omitted canonical live/rehydrated classes")
        require("data-execution-mode='direct_command'" in html and "data-risk-level='low'" in html, "server card omitted lifecycle data")
        require("data-chat-action-retry" in html, "failed low-risk card omitted immediate safe retry")
        require("chat-action-portal-actions" in html, "card controls lack the bounded action container")
        require("data-action-restored='true'" in html, "rehydrated card lacks its persisted-state marker")


def test_completed_reload_revokes_retry_control() -> None:
    with isolated_runtime():
        session = sessions.create_conversation_session("Retry revocation", select_session=False)
        operation_id = "conversation_retry_revocation"
        action = _action("completed", 2)
        action["deduplication_key"] = operation_id
        action["conversation_session_id"] = session["id"]
        router.save_chat_action(action)
        turn = sessions.append_conversation_turn(
            session["id"], turn_id=operation_id, user_message="Retry diagnostics",
            assistant_response="The retry completed.", completion_state="completed", success=True,
            provider="test", model="test", select_session=False,
            operator_action=build_action_portal_state(action, action["result"]),
        )
        html = dashboard_chat._render_action_portal_card(session["id"], turn)
        require("data-chat-action-retry" not in html, "completed rehydrated action retained a stale retry control")
        require("data-action-status='completed'" in html, "completed card did not expose terminal state")


def test_live_card_javascript_uses_canonical_contract() -> None:
    source = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
    require("card.className = 'chat-action-portal chat-inline-action'" in source, "live card still uses the obsolete action-card class")
    require("card.className = 'action-card chat-inline-action'" not in source, "obsolete live action-card contract remains")
    require("ensureActionCardActions(card)" in source, "live card controls are not normalized")
    require("card.dataset.actionStatus = status" in source, "live terminal result does not update card lifecycle data")
    require("approval_created','pending_approval'].includes(raw)" in source, "live approval state is not normalized to awaiting approval")


def test_live_retry_revocation_and_target_refresh_are_explicit() -> None:
    source = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
    require("if (existing) existing.remove();" in source, "persisted reconciliation cannot revoke a stale retry control")
    require("setActionCardRetry(card, Boolean(portal.retry_allowed)" in source, "persisted retry control is not derived from current evidence")
    require("updateLinkedTargetCard(result);" in source, "linked retry result does not refresh its original action card")
    require("result.target_action_id" in source and "result.target_status" in source, "linked target refresh lacks governed identifiers")


def test_rendered_javascript_syntax() -> None:
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
    with tempfile.TemporaryDirectory(prefix="eidolon-v1080-4-js-") as raw:
        path = Path(raw) / "rendered.js"
        path.write_text("\n".join(scripts), encoding="utf-8")
        try:
            result = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True, timeout=30)
        except FileNotFoundError:
            return
        require(result.returncode == 0, f"rendered JavaScript syntax failed: {result.stderr.strip()}")


def test_cross_process_action_claim_is_exactly_once() -> None:
    with isolated_runtime() as root:
        action = router.propose_chat_action(
            "Run diagnostics",
            save=True,
            deduplication_key="v1080_4_cross_process_claim",
        )
        coordination = root / "cross_process_claim"
        coordination.mkdir(parents=True, exist_ok=True)
        go_path = coordination / "go"
        entered_path = coordination / "entered"
        release_path = coordination / "release"
        invocations_path = coordination / "invocations.txt"
        worker_path = ROOT / "tools" / "chat_action_cross_process_claim_worker.py"

        processes: list[subprocess.Popen[str]] = []
        ready_paths: list[Path] = []
        for index in range(2):
            ready_path = coordination / f"ready_{index}"
            ready_paths.append(ready_path)
            processes.append(subprocess.Popen(
                [
                    sys.executable,
                    str(worker_path),
                    "--runtime-root", str(root),
                    "--action-id", str(action["id"]),
                    "--worker-name", f"worker_{index}",
                    "--ready", str(ready_path),
                    "--go", str(go_path),
                    "--entered", str(entered_path),
                    "--release", str(release_path),
                    "--invocations", str(invocations_path),
                ],
                cwd=str(ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            ))

        deadline = time.monotonic() + 10.0
        while not all(path.exists() for path in ready_paths):
            require(time.monotonic() < deadline, "subprocess workers did not reach the claim barrier")
            time.sleep(0.02)
        go_path.write_text("go", encoding="utf-8")

        deadline = time.monotonic() + 10.0
        while not entered_path.exists():
            require(time.monotonic() < deadline, "no subprocess entered the governed runner")
            time.sleep(0.02)

        loser_returned = False
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            if any(process.poll() is not None for process in processes):
                loser_returned = True
                break
            time.sleep(0.02)
        release_path.write_text("release", encoding="utf-8")

        outputs: list[dict] = []
        for process in processes:
            stdout, stderr = process.communicate(timeout=15)
            require(process.returncode == 0, f"claim subprocess crashed: {stderr.strip() or stdout.strip()}")
            lines = [line for line in stdout.splitlines() if line.strip()]
            require(lines, "claim subprocess returned no structured result")
            outputs.append(json.loads(lines[-1]))

        invocation_lines = invocations_path.read_text(encoding="utf-8").splitlines() if invocations_path.exists() else []
        require(loser_returned, "both subprocesses remained in execution instead of one replaying the running claim")
        require(len(invocation_lines) == 1, f"cross-process claim started {len(invocation_lines)} commands")
        require(sum(not bool(item.get("replayed")) for item in outputs) == 1, "cross-process race did not produce exactly one execution owner")
        require(sum(bool(item.get("replayed")) for item in outputs) == 1, "cross-process race did not return one persisted replay")
        persisted = router.load_chat_action(str(action["id"])) or {}
        require(persisted.get("status") == "executed", f"persisted action ended in {persisted.get('status')}")
        require(len(persisted.get("execution_attempts") or []) == 1, "cross-process claim created duplicate execution attempts")
        lock_files = list((router.CHAT_ACTIONS_DIR / ".locks").glob("*.lock"))
        require(not lock_files, f"interprocess locks were not released: {[path.name for path in lock_files]}")


def test_claim_lock_timeout_returns_safe_non_execution() -> None:
    with isolated_runtime():
        action = router.propose_chat_action(
            "Run diagnostics",
            save=True,
            deduplication_key="v1080_4_claim_timeout",
        )
        lock_path = router._chat_action_lock_path(f"action:{action['id']}")
        lock_path.write_text('{"token":"other-process","pid":999999}', encoding="utf-8")
        original_wait = router._CHAT_ACTION_LOCK_WAIT_SECONDS
        original_runner = router.run_approved_command
        calls: list[str] = []
        router._CHAT_ACTION_LOCK_WAIT_SECONDS = 0.1
        router.run_approved_command = lambda command, **_kwargs: calls.append(command)
        try:
            result = router.execute_chat_action(str(action["id"]), timeout_seconds=180)
        finally:
            router._CHAT_ACTION_LOCK_WAIT_SECONDS = original_wait
            router.run_approved_command = original_runner
            lock_path.unlink(missing_ok=True)
        require(result.replayed, "busy interprocess claim was not returned as a non-executing replay")
        require("timed out safely" in result.error.lower(), "busy claim did not report its safe timeout")
        require(not calls, "busy claim reached the command runner")
        persisted = router.load_chat_action(str(action["id"])) or {}
        require(persisted.get("status") == "proposed", "busy claim mutated the persisted proposal")


def test_v1080_3_documented_count_is_reconciled() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
    require("v1080.3" in readme and "22/22" in readme, "README does not record the actual v1080.3 22/22 result")
    require("v1080.3" in history and "22/22" in history, "release history retains the stale v1080.3 count")
    require("v1080.3 daily conversation/operator soak passes 21/21" not in readme, "stale 21/21 claim remains in README")


def test_current_metadata_and_guides_are_aligned() -> None:
    version_tuple = tuple(int(part) for part in release_metadata.RUNTIME_VERSION.split("."))
    require(version_tuple >= (1080, 4), "runtime version regressed below the v1080.4 consolidation baseline")
    current_tag = f"v{release_metadata.RUNTIME_VERSION}"
    require(current_tag in release_metadata.RUNTIME_MILESTONE, "runtime milestone is not aligned with the current version")
    for relative in ("data/settings.json", "data/workspaces/active_project.json", "data/workspaces/projects.json"):
        data = json.loads((ROOT / relative).read_text(encoding="utf-8"))
        require(release_metadata.RUNTIME_VERSION in json.dumps(data), f"{relative} is not aligned with the current runtime version")
    rendered = dashboard_chat.render_realtime_chat_panel(None, compact=True)
    require(f"data-chat-version='{current_tag}-" in rendered, "dashboard chat version metadata is stale")
    for relative in ("README.md", "README_NEXT_STEPS.md", "archive/docs/legacy_dependencies/roadmaps/README_DESKTOP_ALPHA.md"):
        require(current_tag in (ROOT / relative).read_text(encoding="utf-8"), f"{relative} omitted the current version")
    require("v1080.4" in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8"), "release history omitted the v1080.4 consolidation checkpoint")


def test_release_verification_registration_is_exactly_once() -> None:
    source = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
    require(source.count('"desktop-alpha-candidate-consolidation-fixtures"') == 1, "v1080.4 stage is not registered exactly once")
    require(source.count('"tools/v1080_4_desktop_alpha_candidate_consolidation_tests.py"') == 1, "v1080.4 suite path is not registered exactly once")
    require(source.count('"daily-conversation-operator-soak-fixtures"') == 1, "v1080.3 retained stage registration drifted")
    require(source.count('"conversational-control-portal-regression-fixtures"') == 1, "v1080.2 retained stage registration drifted")


def test_source_tree_contains_no_runtime_project_pointer() -> None:
    require(not (ROOT / "data" / "projects.json").exists(), "source candidate contains data/projects.json")
    forbidden = ("conversations", "memories.json", "chat_actions", "approvals", ".venv")
    paths = [path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if path.is_file()]
    for token in forbidden:
        require(not any(token in path for path in paths), f"source tree contains forbidden runtime path token: {token}")


TESTS: tuple[tuple[str, Callable[[], None]], ...] = (
    ("retry_running_transition_requires_new_attempt", test_retry_running_transition_requires_new_attempt),
    ("older_attempt_cannot_replace_newer_evidence", test_older_attempt_cannot_replace_newer_evidence),
    ("pending_approval_can_be_cancelled", test_pending_approval_can_be_cancelled),
    ("conversation_context_tracks_running_retry", test_conversation_context_tracks_running_retry),
    ("server_cards_use_one_canonical_contract", test_server_cards_use_one_canonical_contract),
    ("completed_reload_revokes_retry_control", test_completed_reload_revokes_retry_control),
    ("live_card_javascript_uses_canonical_contract", test_live_card_javascript_uses_canonical_contract),
    ("live_retry_revocation_and_target_refresh_are_explicit", test_live_retry_revocation_and_target_refresh_are_explicit),
    ("rendered_javascript_syntax", test_rendered_javascript_syntax),
    ("cross_process_action_claim_is_exactly_once", test_cross_process_action_claim_is_exactly_once),
    ("claim_lock_timeout_returns_safe_non_execution", test_claim_lock_timeout_returns_safe_non_execution),
    ("v1080_3_documented_count_is_reconciled", test_v1080_3_documented_count_is_reconciled),
    ("current_metadata_and_guides_are_aligned", test_current_metadata_and_guides_are_aligned),
    ("release_verification_registration_is_exactly_once", test_release_verification_registration_is_exactly_once),
    ("source_tree_contains_no_runtime_project_pointer", test_source_tree_contains_no_runtime_project_pointer),
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
        "suite": "v1080.4-desktop-alpha-candidate-consolidation",
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
