from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
TOOLS = ROOT / "tools"
sys.path.insert(0, str(AGENT))

import conversation_navigation as navigation
import conversation_sessions as sessions
import dashboard_chat_console
import post_review_development_verify as isolated_verify


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


class IsolatedConversationStorage:
    def __init__(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="eidolon-v1082-1-")
        root = Path(self.temp.name) / "conversation_sessions"
        self.original = (
            sessions.CONVERSATION_SESSIONS_DIR, sessions.ACTIVE_SESSION_FILE,
            sessions.CONVERSATION_DRAFTS_DIR, sessions.CONVERSATION_DRAFT_CONFLICTS_DIR,
            navigation.CONVERSATION_PRESENTATION_DIR, navigation.CONVERSATION_NAVIGATION_CLIENTS_DIR,
            navigation.CONVERSATION_LIFECYCLE_REQUESTS_DIR,
        )
        sessions.CONVERSATION_SESSIONS_DIR = root
        sessions.ACTIVE_SESSION_FILE = root / "active_session.json"
        sessions.CONVERSATION_DRAFTS_DIR = root / "drafts"
        sessions.CONVERSATION_DRAFT_CONFLICTS_DIR = root / "draft_conflicts"
        navigation.CONVERSATION_PRESENTATION_DIR = root / "presentation"
        navigation.CONVERSATION_NAVIGATION_CLIENTS_DIR = root / "navigation_clients"
        navigation.CONVERSATION_LIFECYCLE_REQUESTS_DIR = root / "lifecycle_requests"

    def close(self) -> None:
        (
            sessions.CONVERSATION_SESSIONS_DIR, sessions.ACTIVE_SESSION_FILE,
            sessions.CONVERSATION_DRAFTS_DIR, sessions.CONVERSATION_DRAFT_CONFLICTS_DIR,
            navigation.CONVERSATION_PRESENTATION_DIR, navigation.CONVERSATION_NAVIGATION_CLIENTS_DIR,
            navigation.CONVERSATION_LIFECYCLE_REQUESTS_DIR,
        ) = self.original
        self.temp.cleanup()


def create_session() -> tuple[IsolatedConversationStorage, str]:
    runtime = IsolatedConversationStorage()
    session = sessions.create_conversation_session("Draft conflict")
    return runtime, session["id"]


def test_draft_revision_and_digest_advance() -> None:
    runtime, session_id = create_session()
    try:
        first = sessions.save_conversation_draft(session_id, "one", base_revision=0, editor_id="tab-a")
        second = sessions.save_conversation_draft(session_id, "two", base_revision=1, editor_id="tab-a")
        require(first["revision"] == 1 and second["revision"] == 2, "draft revision did not advance")
        require(len(second["content_digest"]) == 64 and second["content_digest"] != first["content_digest"], "draft digest missing")
    finally:
        runtime.close()


def test_divergent_stale_edit_preserves_both_versions() -> None:
    runtime, session_id = create_session()
    try:
        saved = sessions.save_conversation_draft(session_id, "saved version", base_revision=0, editor_id="tab-a")
        conflict = sessions.save_conversation_draft(session_id, "other tab version", base_revision=0, editor_id="tab-b")
        current = sessions.load_conversation_draft(session_id)
        require(conflict["draft_conflict"] is True, "divergent stale edit was not identified")
        require(current["content"] == "saved version" and current["revision"] == saved["revision"], "canonical draft was silently overwritten")
        require(conflict["conflict"]["current_content"] == "saved version", "current version not preserved")
        require(conflict["conflict"]["incoming_content"] == "other tab version", "incoming version not preserved")
        stored = sessions.load_conversation_draft_conflict(session_id, conflict["conflict"]["conflict_id"])
        require(stored and stored["incoming_content"] == "other tab version", "conflict record missing")
    finally:
        runtime.close()


def test_identical_stale_edit_is_idempotent() -> None:
    runtime, session_id = create_session()
    try:
        sessions.save_conversation_draft(session_id, "same", base_revision=0, editor_id="tab-a")
        duplicate = sessions.save_conversation_draft(session_id, "same", base_revision=0, editor_id="tab-b")
        require(duplicate["draft_conflict"] is False, "identical stale edit created false conflict")
        require(duplicate["revision"] == 1, "identical stale edit advanced revision")
    finally:
        runtime.close()


def test_explicit_keep_current_resolution() -> None:
    runtime, session_id = create_session()
    try:
        sessions.save_conversation_draft(session_id, "current", base_revision=0, editor_id="tab-a")
        conflict = sessions.save_conversation_draft(session_id, "incoming", base_revision=0, editor_id="tab-b")
        result = sessions.resolve_conversation_draft_conflict(
            session_id, conflict["conflict"]["conflict_id"], choice="current", expected_revision=1, editor_id="tab-a",
        )
        require(result["resolution"] == "current", "current resolution not recorded")
        require(result["draft"]["content"] == "current" and result["draft"]["revision"] == 1, "current resolution changed draft")
    finally:
        runtime.close()


def test_explicit_use_incoming_resolution() -> None:
    runtime, session_id = create_session()
    try:
        sessions.save_conversation_draft(session_id, "current", base_revision=0, editor_id="tab-a")
        conflict = sessions.save_conversation_draft(session_id, "incoming", base_revision=0, editor_id="tab-b")
        result = sessions.resolve_conversation_draft_conflict(
            session_id, conflict["conflict"]["conflict_id"], choice="incoming", expected_revision=1, editor_id="tab-b",
        )
        require(result["resolution"] == "incoming", "incoming resolution not recorded")
        require(result["draft"]["content"] == "incoming" and result["draft"]["revision"] == 2, "incoming resolution did not advance canonical draft")
    finally:
        runtime.close()


def test_resolution_rejects_changed_canonical_revision() -> None:
    runtime, session_id = create_session()
    try:
        sessions.save_conversation_draft(session_id, "current", base_revision=0, editor_id="tab-a")
        conflict = sessions.save_conversation_draft(session_id, "incoming", base_revision=0, editor_id="tab-b")
        sessions.save_conversation_draft(session_id, "newer", base_revision=1, editor_id="tab-a")
        try:
            sessions.resolve_conversation_draft_conflict(
                session_id, conflict["conflict"]["conflict_id"], choice="incoming", expected_revision=1, editor_id="tab-b",
            )
        except ValueError as error:
            require("changed after the conflict" in str(error), "wrong stale resolution error")
        else:
            raise AssertionError("stale conflict resolution was accepted")
    finally:
        runtime.close()


def test_acceptance_clear_advances_revision() -> None:
    runtime, session_id = create_session()
    try:
        saved = sessions.save_conversation_draft(session_id, "send me", base_revision=0, editor_id="tab-a")
        cleared = sessions.clear_conversation_draft(session_id)
        require(cleared["revision"] == saved["revision"] + 1, "accepted clear did not advance revision")
        require(cleared["content"] == "" and len(cleared["content_digest"]) == 64, "clear tombstone incomplete")
    finally:
        runtime.close()


def test_dashboard_api_wires_conflict_contract() -> None:
    source = (AGENT / "dashboard.py").read_text(encoding="utf-8")
    require('parsed.path == "/api/dashboard-chat/draft-conflict-resolve"' in source, "conflict resolution endpoint missing")
    require("base_revision=(int(body.get" in source and "editor_id=str(body.get" in source, "draft save drops revision or editor")
    require("resolve_conversation_draft_conflict" in source, "server resolution helper not called")


def test_ui_requires_explicit_choice_and_blocks_send() -> None:
    source = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
    require("Two tabs edited this draft" in source, "conflict presentation missing")
    require("Keep saved draft" in source and "Use this tab’s draft" in source, "explicit resolution choices missing")
    require("if (activeDraftConflict)" in source and "No text was submitted" in source, "unresolved conflict does not block send")
    require("automatic choice was made" in source, "no-automatic-resolution wording missing")


def test_browser_draft_storage_tracks_base_revision() -> None:
    source = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
    require("eidolon.chat.draft.v3." in source, "revision-aware browser draft key missing")
    require("base_revision" in source and "draftEditorId()" in source, "browser draft revision/editor missing")
    require("draft_conflict" in source and "showDraftConflict" in source, "browser ignores server conflict")


def test_rendered_javascript_syntax() -> None:
    html = dashboard_chat_console.render_realtime_chat_panel(None, compact=True)
    require("chat-draft-conflict" in html, "conflict controls not rendered")
    node = shutil.which("node")
    if not node:
        return
    scripts = []
    cursor = 0
    while True:
        start = html.find("<script>", cursor)
        if start < 0:
            break
        end = html.find("</script>", start)
        require(end >= 0, "unclosed script")
        scripts.append(html[start + len("<script>"):end])
        cursor = end + len("</script>")
    with tempfile.TemporaryDirectory(prefix="eidolon-v1082-1-js-") as raw:
        for index, script in enumerate(scripts):
            path = Path(raw) / f"script-{index}.js"
            path.write_text(script, encoding="utf-8")
            result = subprocess.run([node, "--check", str(path)], capture_output=True, text=True, timeout=30)
            require(result.returncode == 0, result.stderr or "rendered JavaScript syntax failed")


def test_profile_and_release_registration() -> None:
    core = {suite.name for suite in isolated_verify.select_suites("core")}
    require("v1082.1-cross-tab-draft-conflict" in core, "v1082.1 absent from core profile")
    source = (TOOLS / "release_verify.py").read_text(encoding="utf-8")
    require(source.count("tools/v1082_1_cross_tab_draft_conflict_tests.py") == 1, "v1082.1 release registration wrong")


def test_source_only_privacy() -> None:
    require(not (ROOT / "data/conversation_sessions").exists(), "private conversation runtime present")
    require(not (ROOT / "data/projects.json").exists(), "private active-project pointer present")
    require("draft_conflicts" not in {path.name for path in (ROOT / "data").glob("*") if path.exists()}, "draft conflict runtime packaged")


TESTS: tuple[tuple[str, Callable[[], None]], ...] = tuple(
    (name[5:], value) for name, value in sorted(globals().items()) if name.startswith("test_") and callable(value)
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.parse_args()
    checks = []
    passed = 0
    for name, function in TESTS:
        try:
            function()
        except Exception as error:
            checks.append({"name": name, "status": "fail", "message": f"{type(error).__name__}: {error}"})
        else:
            passed += 1
            checks.append({"name": name, "status": "pass", "message": ""})
    report = {"suite": "v1082.1-cross-tab-draft-conflict", "ok": passed == len(TESTS), "status": "pass" if passed == len(TESTS) else "fail", "passed": passed, "total": len(TESTS), "checks": checks}
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
