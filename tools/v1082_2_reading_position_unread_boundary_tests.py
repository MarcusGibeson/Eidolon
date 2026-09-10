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
import release_metadata


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


class IsolatedConversationStorage:
    def __init__(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="eidolon-v1082-2-")
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


def seeded_session(turns: int = 3) -> tuple[IsolatedConversationStorage, str]:
    runtime = IsolatedConversationStorage()
    session = sessions.create_conversation_session("Reading state")
    for index in range(turns):
        sessions.append_conversation_turn(
            session["id"], turn_id=f"turn-{index + 1}", user_message=f"u{index + 1}",
            assistant_response=f"a{index + 1}", completion_state="completed", success=True,
        )
    return runtime, session["id"]


def test_presentation_schema_tracks_anchor_and_boundary() -> None:
    runtime, session_id = seeded_session()
    try:
        value = navigation.save_conversation_presentation_state(
            session_id, follow_latest=False, scroll_from_bottom_px=240,
            view_anchor_turn_id="turn-2", view_anchor_offset_px=18,
            last_seen_turn_id="turn-2", last_seen_turn_count=2,
            composer_intentionally_empty=True,
        )
        require(value["schema_version"] == "2", "presentation schema not advanced")
        require(value["view_anchor_turn_id"] == "turn-2" and value["view_anchor_offset_px"] == 18, "reading anchor missing")
        require(value["last_seen_turn_count"] == 2 and value["unread_turn_count"] == 1, "unread boundary incorrect")
    finally:
        runtime.close()


def test_unread_count_is_derived_after_new_turn() -> None:
    runtime, session_id = seeded_session(2)
    try:
        navigation.save_conversation_presentation_state(
            session_id, follow_latest=False, scroll_from_bottom_px=100,
            last_seen_turn_id="turn-1", last_seen_turn_count=1,
            composer_intentionally_empty=True,
        )
        sessions.append_conversation_turn(
            session_id, turn_id="turn-3", user_message="u3", assistant_response="a3",
            completion_state="completed", success=True,
        )
        loaded = navigation.load_conversation_presentation_state(session_id)
        require(loaded["turn_count"] == 3 and loaded["unread_turn_count"] == 2, "new turn did not advance unread count")
    finally:
        runtime.close()


def test_follow_latest_marks_all_turns_seen() -> None:
    runtime, session_id = seeded_session(4)
    try:
        value = navigation.save_conversation_presentation_state(
            session_id, follow_latest=True, scroll_from_bottom_px=999,
            view_anchor_turn_id="turn-1", view_anchor_offset_px=50,
            last_seen_turn_id="turn-1", last_seen_turn_count=1,
            composer_intentionally_empty=False,
        )
        require(value["unread_turn_count"] == 0 and value["last_seen_turn_count"] == 4, "follow-latest did not mark all seen")
        require(value["last_seen_turn_id"] == "turn-4", "latest turn identity not retained")
        require(value["scroll_from_bottom_px"] == 0 and value["view_anchor_turn_id"] == "", "follow-latest retained stale anchor")
    finally:
        runtime.close()


def test_stale_presentation_update_is_rejected() -> None:
    runtime, session_id = seeded_session(2)
    try:
        first = navigation.save_conversation_presentation_state(
            session_id, follow_latest=False, scroll_from_bottom_px=90,
            last_seen_turn_id="turn-1", last_seen_turn_count=1,
            composer_intentionally_empty=True, client_updated_at="2026-07-19T20:00:00.000Z",
        )
        stale = navigation.save_conversation_presentation_state(
            session_id, follow_latest=True, scroll_from_bottom_px=0,
            last_seen_turn_count=2, composer_intentionally_empty=True,
            client_updated_at="2026-07-19T19:59:59.000Z",
        )
        require(first["changed"] is True, "initial presentation was not saved")
        require(stale["stale_update_ignored"] is True and stale["follow_latest"] is False, "stale presentation overwrote newer state")
    finally:
        runtime.close()


def test_presentation_state_is_content_free() -> None:
    runtime, session_id = seeded_session(1)
    try:
        value = navigation.save_conversation_presentation_state(
            session_id, follow_latest=False, scroll_from_bottom_px=10,
            view_anchor_turn_id="turn-1", view_anchor_offset_px=4,
            last_seen_turn_id="turn-1", last_seen_turn_count=1,
            composer_intentionally_empty=False,
        )
        require(navigation.presentation_state_contains_private_fields(value) is False, "presentation state contains private data")
        require(value["content_free"] is True, "presentation state not marked content-free")
    finally:
        runtime.close()


def test_browser_persists_turn_anchor_and_unread_boundary() -> None:
    source = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
    require("eidolon.chat.presentation.v2." in source, "browser presentation schema missing")
    for token in ("view_anchor_turn_id", "view_anchor_offset_px", "last_seen_turn_id", "last_seen_turn_count", "unread_turn_count"):
        require(token in source, f"browser presentation field missing: {token}")
    require("readingBoundary()" in source and "findTurnAnchor" in source, "turn anchoring logic missing")


def test_jump_latest_announces_unread_count() -> None:
    source = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
    require("jumpLatestButton.dataset.unreadCount" in source, "jump-to-latest unread count missing")
    require("unread turns" in source, "unread accessibility label missing")
    require("data-unread-count" in dashboard_chat_console.COMPANION_CHAT_STYLES, "unread badge style missing")


def test_restored_transcript_has_stable_turn_anchors() -> None:
    source = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
    require(source.count("data-session-turn-id='{_safe(turn.get('id',''))}'") >= 2, "user and assistant turns do not share stable identity")
    require("log.scrollTop += Math.round(before -" in source, "anchor-relative scroll restoration missing")


def test_server_api_accepts_reading_boundary_fields() -> None:
    source = (AGENT / "dashboard.py").read_text(encoding="utf-8")
    for token in ("view_anchor_turn_id", "view_anchor_offset_px", "last_seen_turn_id", "last_seen_turn_count", "unread_turn_count"):
        require(token in source, f"presentation endpoint omits {token}")


def test_narrow_layout_contains_new_controls() -> None:
    styles = dashboard_chat_console.COMPANION_CHAT_STYLES
    require(".chat-draft-conflict-actions > * { flex:1 1 100%;" in styles, "draft conflict controls overflow narrow layout")
    require("overflow-wrap:anywhere" in styles, "bounded continuity text can overflow")


def test_rendered_javascript_syntax() -> None:
    html = dashboard_chat_console.render_realtime_chat_panel(None, compact=True)
    require(f"data-chat-version='{release_metadata.RUNTIME_VERSION_TAG}-{release_metadata.RUNTIME_UI_CONTRACT}'" in html, "rendered UI contract mismatch")
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
    with tempfile.TemporaryDirectory(prefix="eidolon-v1082-2-js-") as raw:
        for index, script in enumerate(scripts):
            path = Path(raw) / f"script-{index}.js"
            path.write_text(script, encoding="utf-8")
            result = subprocess.run([node, "--check", str(path)], capture_output=True, text=True, timeout=30)
            require(result.returncode == 0, result.stderr or "rendered JavaScript syntax failed")


def test_profile_and_release_registration() -> None:
    core = {suite.name for suite in isolated_verify.select_suites("core")}
    require("v1082.2-reading-position-unread-boundary" in core, "v1082.2 absent from core profile")
    source = (TOOLS / "release_verify.py").read_text(encoding="utf-8")
    require(source.count("tools/v1082_2_reading_position_unread_boundary_tests.py") == 1, "v1082.2 release registration wrong")


def test_source_only_privacy() -> None:
    require(not (ROOT / "data/conversation_sessions").exists(), "private session runtime present")
    require(not (ROOT / "data/projects.json").exists(), "private active-project pointer present")
    require(not any(path.suffix in {".pyc", ".pyo"} for path in ROOT.rglob("*") if "__pycache__" not in path.parts), "compiled runtime artifact present")


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
    report = {"suite": "v1082.2-reading-position-unread-boundary", "ok": passed == len(TESTS), "status": "pass" if passed == len(TESTS) else "fail", "passed": passed, "total": len(TESTS), "checks": checks}
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
