from __future__ import annotations

import argparse
import json
import subprocess
import sys
sys.dont_write_bytecode = True
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))

import approval_manager
import attention_center
import chat_action_router
import command_runner
import conversation_sessions as sessions
import dashboard_chat_console as dashboard_chat
import notification_manager
import release_metadata
import task_queue


class Failure(AssertionError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Failure(message)


@contextmanager
def patched(module: Any, **values: Any):
    originals = {key: getattr(module, key) for key in values}
    for key, value in values.items():
        setattr(module, key, value)
    try:
        yield
    finally:
        for key, value in originals.items():
            setattr(module, key, value)


@contextmanager
def isolated_conversations():
    with tempfile.TemporaryDirectory(prefix="eidolon-v1080-7-conversations-") as raw:
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
        sessions.LEGACY_DASHBOARD_CHAT_DIR = root / "legacy"
        sessions.LEGACY_DASHBOARD_CHAT_IMPORT_FILE = sessions.CONVERSATION_SESSIONS_DIR / "legacy_import.json"
        sessions.clear_conversation_search_cache()
        try:
            yield root
        finally:
            sessions.clear_conversation_search_cache()
            for key, value in originals.items():
                setattr(sessions, key, value)


def _empty_sources() -> dict[str, Any]:
    return {
        "list_notifications": lambda **_kwargs: [],
        "list_approvals": lambda **_kwargs: [],
        "list_tasks": lambda **_kwargs: [],
        "list_chat_actions": lambda **_kwargs: [],
        "get_active_project": lambda: {},
        "build_action_portal_state": lambda *_args, **_kwargs: {},
    }


def test_read_only_builder_does_not_create_runtime_storage() -> None:
    with tempfile.TemporaryDirectory(prefix="eidolon-v1080-7-read-only-") as raw:
        root = Path(raw)
        notification_dir = root / "notifications"
        approval_dir = root / "approvals"
        tasks_file = root / "tasks.json"
        action_dir = root / "chat_actions"
        with patched(notification_manager, NOTIFICATIONS_DIR=notification_dir), patched(
            approval_manager, APPROVALS_DIR=approval_dir, APPROVALS_README=approval_dir / "README.md"
        ), patched(task_queue, TASKS_FILE=tasks_file), patched(chat_action_router, CHAT_ACTIONS_DIR=action_dir):
            report = attention_center.build_attention_center()
        require(report["read_only"] and report["mutations_performed"] is False, "read-only boundary metadata drifted")
        require(not notification_dir.exists(), "attention read created notification storage")
        require(not approval_dir.exists(), "attention read created approval storage")
        require(not tasks_file.exists(), "attention read created tasks.json")
        require(not action_dir.exists(), "attention read created chat-action storage")


def test_redaction_excludes_commands_results_metadata_paths_and_notes() -> None:
    sources = _empty_sources()
    sources.update({
        "list_notifications": lambda **_kwargs: [{
            "id": "note_1", "status": "unread", "severity": "warning", "title": "Safe notice",
            "message": "Review is needed.", "metadata": {"credential": "NOTIFICATION_SECRET"},
            "recommended_command": "SECRET_NOTIFICATION_COMMAND", "created_at": "2026-07-18T10:00:00",
        }],
        "list_approvals": lambda **_kwargs: [{
            "id": "approval_1", "status": "pending", "summary": "Review protected work",
            "action_type": "run_command", "risk_level": "high", "command": "SECRET_APPROVAL_COMMAND",
            "metadata": {"receipt": "SECRET_APPROVAL_RECEIPT"}, "created_at": "2026-07-18T11:00:00",
        }],
        "list_tasks": lambda **_kwargs: [{
            "id": "task_1", "title": "Repair bounded issue", "status": "blocked", "priority": "high",
            "command": "SECRET_TASK_COMMAND", "result": "SECRET_TASK_OUTPUT", "metadata": {"private": "SECRET_TASK_META"},
            "blockers": ["Needs operator decision"], "created_at": "2026-07-18T12:00:00",
        }],
        "list_chat_actions": lambda **_kwargs: [{
            "id": "action_1", "title": "Run diagnostics", "status": "failed", "summary": "Diagnostics failed safely.",
            "command": "SECRET_ACTION_COMMAND", "user_request": "SECRET_USER_PROMPT",
            "result": {"stdout": "SECRET_RAW_OUTPUT", "credential": "SECRET_ACTION_CREDENTIAL"},
            "created_at": "2026-07-18T13:00:00",
        }],
        "get_active_project": lambda: {
            "name": "Eidolon", "status": "active", "path": "C:/SECRET/PROJECT/PATH",
            "next_steps": ["Review the attention center"], "known_issues": [], "notes": ["SECRET_PROJECT_NOTE"],
        },
        "build_action_portal_state": lambda *_args, **_kwargs: {"status": "failed", "summary": "Diagnostics failed safely."},
    })
    with patched(attention_center, **sources):
        report = attention_center.build_attention_center()
    encoded = json.dumps(report)
    for secret in (
        "NOTIFICATION_SECRET", "SECRET_NOTIFICATION_COMMAND", "SECRET_APPROVAL_COMMAND", "SECRET_APPROVAL_RECEIPT",
        "SECRET_TASK_COMMAND", "SECRET_TASK_OUTPUT", "SECRET_TASK_META", "SECRET_ACTION_COMMAND", "SECRET_USER_PROMPT",
        "SECRET_RAW_OUTPUT", "SECRET_ACTION_CREDENTIAL", "C:/SECRET/PROJECT/PATH", "SECRET_PROJECT_NOTE",
    ):
        require(secret not in encoded, f"redacted attention payload leaked {secret}")
    require(report["privacy"]["raw_command_output_included"] is False, "privacy declaration drifted")


def test_priority_counts_and_operator_attention_are_deterministic() -> None:
    sources = _empty_sources()
    sources.update({
        "list_approvals": lambda **_kwargs: [{"id": "approval", "status": "pending", "summary": "Approve patch", "action_type": "apply_patch", "risk_level": "high", "created_at": "2026-07-18T12:00:00"}],
        "list_tasks": lambda **_kwargs: [
            {"id": "task_blocked", "title": "Blocked task", "status": "blocked", "priority": "medium", "blockers": ["Operator input"], "created_at": "2026-07-18T11:00:00"},
            {"id": "task_active", "title": "Active task", "status": "active", "priority": "low", "created_at": "2026-07-18T13:00:00"},
        ],
        "list_notifications": lambda **_kwargs: [{"id": "note", "status": "unread", "severity": "warning", "title": "Warning", "message": "Needs review", "created_at": "2026-07-18T14:00:00"}],
    })
    with patched(attention_center, **sources):
        report = attention_center.build_attention_center()
    require(report["counts"]["pending_approvals"] == 1, "approval count drifted")
    require(report["counts"]["blocked_tasks"] == 1 and report["counts"]["open_tasks"] == 2, "task counts drifted")
    require(report["counts"]["total_attention"] == 3, f"operator attention count drifted: {report['counts']}")
    require(report["items"][0]["id"] == "task_blocked", "highest-severity operator item did not retain deterministic priority")


def test_recent_completed_action_is_visible_without_becoming_attention() -> None:
    sources = _empty_sources()
    sources.update({
        "list_chat_actions": lambda **_kwargs: [{"id": "action_done", "title": "Diagnostics", "status": "executed", "summary": "Completed safely", "created_at": "2026-07-18T14:00:00", "result": {"ok": True}}],
        "build_action_portal_state": lambda *_args, **_kwargs: {"status": "completed", "summary": "Completed safely"},
    })
    with patched(attention_center, **sources):
        report = attention_center.build_attention_center()
    require(report["counts"]["action_attention"] == 0, "completed action was misclassified as attention")
    require(report["counts"]["recent_action_results"] == 1, "completed action result disappeared")
    require(report["recent_action_results"][0]["status"] == "completed", "canonical completion state drifted")




def test_awaiting_approval_action_remains_operator_attention() -> None:
    sources = _empty_sources()
    sources.update({
        "list_chat_actions": lambda **_kwargs: [{"id": "action_approval", "title": "Protected change", "status": "approval_created", "summary": "Approval created", "created_at": "2026-07-18T14:00:00", "result": {}}],
        "build_action_portal_state": lambda *_args, **_kwargs: {"status": "awaiting_approval", "summary": "Awaiting explicit operator approval"},
    })
    with patched(attention_center, **sources):
        report = attention_center.build_attention_center()
    action = next(row for row in report["items"] if row["kind"] == "action")
    require(action["status"] == "awaiting_approval", "approval action lost canonical portal state")
    require(action["requires_operator"], "awaiting approval action stopped requiring operator attention")
    require(report["counts"]["action_attention"] == 1, "awaiting approval action disappeared from attention count")


def test_item_and_result_history_are_bounded() -> None:
    sources = _empty_sources()
    sources["list_tasks"] = lambda **_kwargs: [
        {"id": f"task_{index}", "title": f"Task {index}", "status": "planned", "priority": "low", "created_at": f"2026-07-18T10:{index % 60:02d}:00"}
        for index in range(80)
    ]
    with patched(attention_center, **sources):
        report = attention_center.build_attention_center(limit=500)
    require(len(report["items"]) == attention_center.MAX_ATTENTION_ITEMS, "attention item bound drifted")
    require(report["limits"]["items"] == attention_center.MAX_ATTENTION_ITEMS, "reported item bound drifted")


def test_conversation_updates_are_restored_read_only_items() -> None:
    sources = _empty_sources()
    with patched(attention_center, **sources):
        report = attention_center.build_attention_center(conversation_updates=[{
            "session_id": "session_1", "title": "Long conversation", "kind": "needs_recovery",
            "label": "Needs recovery", "updated_at": "2026-07-18T15:00:00",
        }])
    item = next(row for row in report["items"] if row["kind"] == "conversation")
    require(item["related_id"] == "session_1" and item["restored"], "conversation cue lost restored identity")
    require(item["requires_operator"], "recovery cue did not require operator attention")
    require(report["counts"]["conversation_updates"] == 1, "conversation update count drifted")


def test_project_continuity_exposes_next_step_without_path_or_notes() -> None:
    sources = _empty_sources()
    sources["get_active_project"] = lambda: {
        "name": "Eidolon", "status": "active", "path": "C:/private/root",
        "next_steps": ["Continue notification continuity"], "known_issues": ["One bounded issue"],
        "notes": ["private note"], "last_worked_on": "2026-07-18T16:00:00",
    }
    with patched(attention_center, **sources):
        report = attention_center.build_attention_center()
    project = next(row for row in report["items"] if row["kind"] == "project")
    require("Continue notification continuity" in project["summary"], "project next step was omitted")
    require("C:/private/root" not in json.dumps(project) and "private note" not in json.dumps(project), "project private fields leaked")


def test_natural_language_routing_uses_attention_center_and_keeps_watch_distinct() -> None:
    cases = {
        "What needs my attention?": "attention_center",
        "Anything needs attention?": "attention_center",
        "What is waiting for me?": "attention_center",
        "Catch me up on what needs attention": "attention_center",
        "Run a watch check": "watch_once",
        "Check watch": "watch_once",
    }
    for message, expected in cases.items():
        action = chat_action_router.propose_chat_action(message, save=False)
        require(action.get("intent") == expected, f"{message!r} routed to {action.get('intent')} instead of {expected}")
    attention = chat_action_router.propose_chat_action("What needs my attention?", save=False)
    require(attention.get("command") == "python conscious_agent/main.py --attention-center", "attention command drifted")


def test_casual_attention_language_does_not_become_command() -> None:
    action = chat_action_router.propose_chat_action("I need your attention because I feel ignored.", save=False)
    require(action.get("intent") == "conversation_only", f"emotional conversation became command: {action.get('intent')}")


def test_attention_command_is_allowlisted_and_shell_remains_blocked() -> None:
    valid = command_runner.validate_command("python conscious_agent/main.py --attention-center")
    require(valid.ok, f"attention command was not allowlisted: {valid.reason}")
    invalid = command_runner.validate_command("python conscious_agent/main.py --attention-center ; whoami")
    require(not invalid.ok, "shell chaining became available through attention center")


def test_cli_json_is_read_only_and_machine_readable() -> None:
    forbidden = [ROOT / "data" / "notifications", ROOT / "data" / "approvals", ROOT / "data" / "tasks.json"]
    require(not any(path.exists() for path in forbidden), "test source began with runtime attention storage")
    result = subprocess.run(
        [sys.executable, "conscious_agent/main.py", "--attention-center", "--readiness-json"],
        cwd=ROOT, capture_output=True, text=True, timeout=60,
        env={**__import__("os").environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    require(result.returncode == 0, f"attention CLI failed: {result.stderr.strip()}")
    payload = json.loads(result.stdout)
    require(payload["read_only"] and payload["redacted"] and payload["mutations_performed"] is False, "CLI boundary metadata drifted")
    require(not any(path.exists() for path in forbidden), "attention CLI created runtime storage")


def test_dashboard_payload_collects_only_visible_conversation_cues() -> None:
    captured: dict[str, Any] = {}
    def fake_builder(**kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return {"ok": True, "counts": {}, "items": [], "recent_action_results": []}
    with patched(
        dashboard_chat,
        dashboard_chat_session_catalog_state=lambda **_kwargs: [
            {"id": "session_a", "title": "A", "updated_at": "2026-07-18T10:00:00"},
            {"id": "session_b", "title": "B", "updated_at": "2026-07-18T11:00:00"},
        ],
        dashboard_session_operation_cue=lambda session_id: {"kind": "reply_ready", "label": "Reply ready", "public_state": "completed"} if session_id == "session_b" else None,
        build_attention_center=fake_builder,
    ):
        payload = dashboard_chat.dashboard_chat_attention_center_payload()
    require(payload["ok"], "dashboard attention payload failed")
    updates = list(captured.get("conversation_updates") or [])
    require(len(updates) == 1 and updates[0]["session_id"] == "session_b", f"dashboard cue collection drifted: {updates}")
    require("acknowledgement_token" not in json.dumps(updates), "read-only attention payload included acknowledgement authority")


def _static_attention_report() -> dict[str, Any]:
    return {
        "ok": True,
        "counts": {"total_attention": 2, "pending_approvals": 1, "unread_notifications": 1, "open_tasks": 2, "conversation_updates": 1, "action_attention": 1},
        "items": [
            {"kind": "approval", "status": "pending", "title": "Approve work", "summary": "apply patch · risk high", "href": "/approvals", "requires_operator": True},
            {"kind": "conversation", "status": "reply_ready", "title": "Daily chat", "summary": "Reply ready", "href": "/chat-console", "requires_operator": False},
        ],
        "recent_action_results": [],
    }


def test_rendered_attention_center_has_read_only_controls_and_narrow_layout() -> None:
    with isolated_conversations(), patched(dashboard_chat, dashboard_chat_attention_center_payload=_static_attention_report):
        sessions.create_conversation_session("Attention UI", select_session=True)
        html = dashboard_chat.render_realtime_chat_panel(None, compact=True)
    for token in (
        "id='chat-attention-center'", "id='attention-center-list'", "id='attention-center-refresh'",
        "Read-only and redacted", "/api/dashboard-chat/attention-center", "chat-attention-center",
        "attention-center-item", "window.setInterval", f"data-chat-version='{release_metadata.RUNTIME_VERSION_TAG}-",
    ):
        require(token in html, f"rendered attention center omitted {token}")
    require("mark-notification-read" not in html and "approve_approval" not in html, "attention center gained hidden mutation controls")


def test_rendered_javascript_syntax() -> None:
    with isolated_conversations(), patched(dashboard_chat, dashboard_chat_attention_center_payload=_static_attention_report):
        sessions.create_conversation_session("Attention JavaScript", select_session=True)
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
    with tempfile.TemporaryDirectory(prefix="eidolon-v1080-7-js-") as raw:
        path = Path(raw) / "rendered.js"
        path.write_text("\n".join(scripts), encoding="utf-8")
        try:
            result = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True, timeout=30)
        except FileNotFoundError:
            return
        require(result.returncode == 0, f"rendered JavaScript syntax failed: {result.stderr.strip()}")


def test_dashboard_and_api_attention_routes_are_get_only() -> None:
    dashboard_source = (AGENT / "dashboard.py").read_text(encoding="utf-8")
    api_source = (AGENT / "api_server.py").read_text(encoding="utf-8")
    require('path == "/api/dashboard-chat/attention-center"' in dashboard_source, "dashboard attention GET endpoint missing")
    require('parts == ["attention-center"]' in api_source, "general attention GET endpoint missing")
    require('parsed.path == "/api/dashboard-chat/attention-center"' not in dashboard_source, "attention center was added as a POST mutation")
    require("build_attention_center()" in api_source, "API attention route is not wired to the redacted builder")


def test_attention_module_has_no_mutation_or_embedding_dependencies() -> None:
    source = (AGENT / "attention_center.py").read_text(encoding="utf-8")
    for token in ("store_memory", "save_notification", "approve_approval", "update_task", "execute_chat_action", "semantic", "embedding"):
        require(token not in source, f"attention center acquired forbidden mutation/vector dependency: {token}")
    require("create_if_missing=False" in source, "attention center stopped using non-creating readers")


def test_current_metadata_docs_and_release_registration_are_aligned() -> None:
    version_parts = tuple(int(part) for part in release_metadata.RUNTIME_VERSION.split("."))
    require(version_parts >= (1080, 7), "runtime metadata regressed below v1080.7")
    require("v1080.7 Notification Center and Task/Project Continuity" in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8"), "v1080.7 historical milestone disappeared")
    for relative in ("data/settings.json", "data/workspaces/active_project.json", "data/workspaces/projects.json"):
        require(release_metadata.RUNTIME_VERSION in (ROOT / relative).read_text(encoding="utf-8"), f"{relative} is not aligned to current runtime version")
    current_tag = f"v{release_metadata.RUNTIME_VERSION}"
    for relative in ("README.md", "README_NEXT_STEPS.md"):
        require(current_tag in (ROOT / relative).read_text(encoding="utf-8"), f"{relative} omits the current runtime tag")
    require("v1080.7" in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8"), "release history omits v1080.7")
    verify = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
    require(verify.count('"notification-task-project-continuity-fixtures"') == 1, "v1080.7 stage is not registered exactly once")
    require(verify.count('"tools/v1080_7_notification_task_project_continuity_tests.py"') == 1, "v1080.7 suite path is not registered exactly once")


def test_source_tree_remains_source_only() -> None:
    require(not (ROOT / "data" / "projects.json").exists(), "source tree contains data/projects.json")
    forbidden = (
        "data/chat_actions", "data/conversation_sessions", "data/approvals", "data/notifications",
        "data/tasks.json", "data/memories.json", ".venv", "__pycache__",
    )
    paths = [path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if path.is_file()]
    for token in forbidden:
        require(not any(token in path for path in paths), f"source tree contains forbidden runtime token: {token}")


TESTS: tuple[tuple[str, Callable[[], None]], ...] = (
    ("read_only_builder_does_not_create_runtime_storage", test_read_only_builder_does_not_create_runtime_storage),
    ("redaction_excludes_commands_results_metadata_paths_and_notes", test_redaction_excludes_commands_results_metadata_paths_and_notes),
    ("priority_counts_and_operator_attention_are_deterministic", test_priority_counts_and_operator_attention_are_deterministic),
    ("recent_completed_action_is_visible_without_becoming_attention", test_recent_completed_action_is_visible_without_becoming_attention),
    ("awaiting_approval_action_remains_operator_attention", test_awaiting_approval_action_remains_operator_attention),
    ("item_and_result_history_are_bounded", test_item_and_result_history_are_bounded),
    ("conversation_updates_are_restored_read_only_items", test_conversation_updates_are_restored_read_only_items),
    ("project_continuity_exposes_next_step_without_path_or_notes", test_project_continuity_exposes_next_step_without_path_or_notes),
    ("natural_language_routing_uses_attention_center_and_keeps_watch_distinct", test_natural_language_routing_uses_attention_center_and_keeps_watch_distinct),
    ("casual_attention_language_does_not_become_command", test_casual_attention_language_does_not_become_command),
    ("attention_command_is_allowlisted_and_shell_remains_blocked", test_attention_command_is_allowlisted_and_shell_remains_blocked),
    ("cli_json_is_read_only_and_machine_readable", test_cli_json_is_read_only_and_machine_readable),
    ("dashboard_payload_collects_only_visible_conversation_cues", test_dashboard_payload_collects_only_visible_conversation_cues),
    ("rendered_attention_center_has_read_only_controls_and_narrow_layout", test_rendered_attention_center_has_read_only_controls_and_narrow_layout),
    ("rendered_javascript_syntax", test_rendered_javascript_syntax),
    ("dashboard_and_api_attention_routes_are_get_only", test_dashboard_and_api_attention_routes_are_get_only),
    ("attention_module_has_no_mutation_or_embedding_dependencies", test_attention_module_has_no_mutation_or_embedding_dependencies),
    ("current_metadata_docs_and_release_registration_are_aligned", test_current_metadata_docs_and_release_registration_are_aligned),
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
        "suite": "v1080.7-notification-task-project-continuity",
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
