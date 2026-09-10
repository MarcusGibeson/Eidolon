from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
TOOLS = ROOT / "tools"


def _bootstrap_external_runtime() -> None:
    if os.environ.get("EIDOLON_DATA_DIR"):
        return
    runtime = Path(tempfile.mkdtemp(prefix="eidolon-v1092-3-runtime-"))
    env = dict(os.environ)
    env["EIDOLON_DATA_DIR"] = str(runtime)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--child"], env=env, text=True, capture_output=True)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    raise SystemExit(result.returncode)


_bootstrap_external_runtime()
sys.path[:0] = [str(AGENT), str(TOOLS)]

from paths import DATA_DIR  # noqa: E402
import project_manager  # noqa: E402
import release_metadata  # noqa: E402
import conversation_operations as operations  # noqa: E402
import conversation_sessions as sessions  # noqa: E402
import project_switching_continuity as continuity  # noqa: E402
from dashboard_chat_console import cancel_dashboard_chat_operation, start_dashboard_chat_operation  # noqa: E402


def require(value: object, message: str) -> None:
    if not value:
        raise AssertionError(message)


def _write_projects() -> None:
    other = DATA_DIR / "other-source"
    other.mkdir(parents=True, exist_ok=True)
    project_manager.PROJECTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    project_manager.PROJECTS_FILE.write_text(json.dumps({
        "active_project_id": "eidolon",
        "active_project": "Eidolon",
        "projects": [
            {"id": "eidolon", "name": "Eidolon", "root": str(ROOT), "working_version": release_metadata.RUNTIME_VERSION, "safe_to_modify": True},
            {"id": "other", "name": "Other Project", "root": str(other), "working_version": "1.0", "safe_to_modify": False},
        ],
    }), encoding="utf-8")


def _switch(selector: str, *, expected_revision: int | None = None, key: str = "") -> dict:
    return project_manager.activate_project(
        selector,
        operator_confirmed=True,
        expected_switch_revision=expected_revision,
        switch_key=key or f"switch-{uuid.uuid4().hex}",
    )


def test_project_scoped_sessions_drafts_navigation_survive_repeated_switches() -> None:
    _write_projects()
    eidolon = sessions.create_conversation_session("Eidolon work")
    sessions.save_conversation_draft(eidolon["id"], "private eidolon draft", base_revision=0, editor_id="eidolon-editor")
    continuity.record_project_navigation("eidolon", selected_session_id=eidolon["id"], view="conversation", scroll_anchor="turn-7")
    first_revision = continuity.project_switch_snapshot()["revision"]
    switched = _switch("other", expected_revision=first_revision, key="switch-project-to-other-0001")
    require(switched["ok"] and switched["project_id"] == "other", "switch to other")
    other = sessions.get_active_conversation_session(create_if_missing=True)
    sessions.save_conversation_draft(other["id"], "private other draft", base_revision=0, editor_id="other-editor")
    continuity.record_project_navigation("other", selected_session_id=other["id"], view="catalog", catalog_cursor="page-2")
    second_revision = continuity.project_switch_snapshot()["revision"]
    require(_switch("eidolon", expected_revision=second_revision, key="switch-project-to-eidolon-0001")["ok"], "switch back")
    restored = sessions.get_active_conversation_session(create_if_missing=False)
    require(restored and restored["id"] == eidolon["id"], "eidolon active session not restored")
    require(sessions.load_conversation_draft(eidolon["id"])["content"] == "private eidolon draft", "eidolon draft lost")
    state = continuity.project_switch_snapshot(project_id="eidolon")
    require(state["project"]["navigation"]["scroll_anchor"] == "turn-7", "navigation lost")
    require(state["project"]["has_draft"] is True, "draft cue lost")


def test_operation_and_turn_are_bound_to_accepting_project_and_session() -> None:
    _write_projects()
    session = sessions.create_conversation_session("Bound operation")
    operation_id = operations.new_conversation_operation_id()
    marker = operations.create_operation_marker(operation_id, session["id"], acceptance_key=operations.new_client_acceptance_key())
    require(marker["project_id"] == "eidolon" and marker["session_id"] == session["id"], "marker binding")
    turn = sessions.append_conversation_turn(
        session["id"], turn_id=operation_id, user_message="test", assistant_response="done",
        completion_state="completed", success=True, select_session=False,
    )
    require(turn["project_id"] == "eidolon", "turn project binding")
    _switch("other", expected_revision=continuity.project_switch_snapshot()["revision"], key="switch-operation-binding-0001")
    persisted = operations.load_operation_marker(operation_id)
    require(persisted and persisted["project_id"] == "eidolon", "operation transferred projects")


def test_old_project_session_cannot_accept_new_turn_after_switch() -> None:
    _write_projects()
    session = sessions.create_conversation_session("Old project session")
    _switch("other", expected_revision=continuity.project_switch_snapshot()["revision"], key="switch-old-session-acceptance-0001")
    try:
        start_dashboard_chat_operation("must be rejected", use_ai=False, session_id=session["id"])
    except ValueError as error:
        require("different active project" in str(error), "wrong rejection")
    else:
        raise AssertionError("old-project session accepted a new turn")


def test_cancellation_requires_exact_operation_project() -> None:
    _write_projects()
    session = sessions.create_conversation_session("Cancellation binding")
    operation_id = operations.new_conversation_operation_id()
    operations.create_operation_marker(operation_id, session["id"], acceptance_key=operations.new_client_acceptance_key())
    rejected = cancel_dashboard_chat_operation(operation_id, project_id="other")
    require(not rejected["ok"] and rejected["status"] == "project_mismatch", "cross-project cancellation accepted")
    require(not operations.load_operation_marker(operation_id)["cancellation_requested"], "rejected cancellation mutated marker")
    accepted = cancel_dashboard_chat_operation(operation_id, project_id="eidolon")
    require(accepted["ok"] and accepted["status"] == "cancellation_requested", "exact cancellation rejected")


def test_stale_project_switch_revision_is_rejected_without_registry_write() -> None:
    _write_projects()
    before = project_manager.PROJECTS_FILE.read_bytes()
    report = _switch("other", expected_revision=99, key="switch-stale-revision-0001")
    require(not report["ok"] and report["status"] == "stale_revision", "stale switch not rejected")
    require(project_manager.PROJECTS_FILE.read_bytes() == before, "stale switch rewrote registry")


def test_switch_key_is_exactly_once() -> None:
    _write_projects()
    revision = continuity.project_switch_snapshot()["revision"]
    first = _switch("other", expected_revision=revision, key="switch-exactly-once-key-0001")
    require(first["ok"] and first["changed"], "first switch")
    after_first = project_manager.PROJECTS_FILE.read_bytes()
    second = _switch("other", expected_revision=revision, key="switch-exactly-once-key-0001")
    require(second["ok"] and not second["changed"] and second["status"] == "already_active", "duplicate switch result")
    require(project_manager.PROJECTS_FILE.read_bytes() == after_first, "duplicate rewrote registry")
    require(continuity.project_switch_snapshot()["revision"] == revision + 1, "duplicate advanced revision")


def test_continuity_records_are_content_free_and_provider_free() -> None:
    _write_projects()
    session = sessions.create_conversation_session("Private")
    sessions.save_conversation_draft(session["id"], "do not expose me", base_revision=0, editor_id="private-editor")
    continuity.capture_project_continuity("eidolon")
    raw = json.loads(continuity.PROJECT_SWITCH_STATE_FILE.read_text(encoding="utf-8"))
    require(not continuity.switching_record_contains_private_fields(raw), "private field in switch state")
    serialized = json.dumps(raw)
    require("do not expose me" not in serialized and "private-editor" not in serialized, "private content leaked")
    snapshot = continuity.project_switch_snapshot(project_id="eidolon")
    require(snapshot["provider_contacted"] is False, "project continuity contacted provider")


def test_release_docs_and_privacy_boundary() -> None:
    require(tuple(int(x) for x in release_metadata.RUNTIME_VERSION.split(".")) >= (1092, 3), "version")
    require(bool(release_metadata.NEXT_RECOMMENDED_ARC), "next arc")
    require(not (ROOT / "data" / "projects.json").exists(), "runtime projects packaged")
    history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
    require("# v1092.3 Project-Switch Conversation Continuity" in history, "history entry")


TESTS = [(name.removeprefix("test_"), fn) for name, fn in list(globals().items()) if name.startswith("test_")]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--child", action="store_true")
    parser.parse_args()
    checks: list[dict[str, str]] = []
    passed = 0
    for name, fn in TESTS:
        try:
            fn()
        except Exception as error:
            checks.append({"name": name, "status": "fail", "message": f"{type(error).__name__}: {error}"})
        else:
            passed += 1
            checks.append({"name": name, "status": "pass", "message": ""})
    report = {
        "suite": "v1092.3-project-switch-conversation-continuity",
        "ok": passed == len(TESTS),
        "status": "pass" if passed == len(TESTS) else "fail",
        "passed": passed,
        "total": len(TESTS),
        "checks": checks,
        "external_runtime": str(DATA_DIR),
    }
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
