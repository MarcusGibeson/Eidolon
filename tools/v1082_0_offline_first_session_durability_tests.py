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
import conversation_offline_durability as durability
import conversation_sessions as sessions
import dashboard_chat_console
import post_review_development_verify as isolated_verify
import release_metadata


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


class IsolatedConversationStorage:
    def __init__(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="eidolon-v1082-0-")
        root = Path(self.temp.name) / "conversation_sessions"
        self.original = (
            sessions.CONVERSATION_SESSIONS_DIR,
            sessions.ACTIVE_SESSION_FILE,
            sessions.CONVERSATION_DRAFTS_DIR,
            sessions.CONVERSATION_DRAFT_CONFLICTS_DIR,
            navigation.CONVERSATION_PRESENTATION_DIR,
            navigation.CONVERSATION_NAVIGATION_CLIENTS_DIR,
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
            sessions.CONVERSATION_SESSIONS_DIR,
            sessions.ACTIVE_SESSION_FILE,
            sessions.CONVERSATION_DRAFTS_DIR,
            sessions.CONVERSATION_DRAFT_CONFLICTS_DIR,
            navigation.CONVERSATION_PRESENTATION_DIR,
            navigation.CONVERSATION_NAVIGATION_CLIENTS_DIR,
            navigation.CONVERSATION_LIFECYCLE_REQUESTS_DIR,
        ) = self.original
        self.temp.cleanup()


def test_release_metadata_records_bundle_progression() -> None:
    require(tuple(map(int, release_metadata.RUNTIME_VERSION.split("."))) >= (1082, 2), "runtime regressed below offline-session bundle")
    require(tuple(map(int, release_metadata.PREVIOUS_RUNTIME_VERSION.split("."))) >= (1082, 1), "v1082.1 lineage missing")
    history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
    require("# v1082.0 Offline-First Session Durability" in history, "v1082.0 historical milestone missing")
    require(tuple(map(int, release_metadata.NEXT_RECOMMENDED_ARC.split()[0].removeprefix("v").split("."))) >= (1082, 3), "next arc mismatch")


def test_local_capabilities_survive_generation_unavailability() -> None:
    runtime = IsolatedConversationStorage()
    try:
        session = sessions.create_conversation_session("Offline continuity")
        sessions.save_conversation_draft(session["id"], "private draft", editor_id="tab-a")
        state = durability.offline_session_durability_state(session["id"])
        capabilities = state["capabilities"]
        for key in ("conversation_history", "conversation_selection", "draft_editing", "conversation_search", "archive_browsing", "archive_restore", "reading_position", "attention_center", "memory_curation", "settings_inspection"):
            require(capabilities.get(key) is True, f"local capability disabled: {key}")
        require(capabilities["provider_generation"] is False, "offline state claimed generation")
        require(capabilities["automatic_request_replay"] is False, "offline state enabled replay")
    finally:
        runtime.close()


def test_offline_state_is_content_free() -> None:
    runtime = IsolatedConversationStorage()
    try:
        session = sessions.create_conversation_session("Private title")
        sessions.save_conversation_draft(session["id"], "very private draft", editor_id="tab-a")
        state = durability.offline_session_durability_state(session["id"])
        require(durability.offline_session_state_contains_private_fields(state) is False, "durability state contains private fields")
        serialized = json.dumps(state)
        require("very private draft" not in serialized and "Private title" not in serialized, "durability state leaked content")
        require(state["content_free"] is True and state["provider_dependency"] == "none_for_local_surfaces", "content-free contract missing")
    finally:
        runtime.close()


def test_browser_restart_metadata_is_bounded() -> None:
    source = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
    require("eidolon.chat.offline-continuity.v1" in source, "browser continuity metadata key missing")
    require("content_free:true" in source, "browser continuity metadata not marked content-free")
    require("draft_revision" in source and "unread_turn_count" in source, "bounded continuity metadata incomplete")
    require("transcript_html" not in source[source.find("eidolon.chat.offline-continuity.v1"):source.find("eidolon.chat.offline-continuity.v1") + 1000], "browser continuity cache stores transcript")


def test_snapshot_exposes_provider_independent_state() -> None:
    source = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
    require('"offline_session": offline_session_durability_state' in source, "session snapshot omits offline durability")
    require("applyOfflineSessionDurability(snapshot.offline_session || null)" in source, "restored snapshot ignores durability state")
    require("applyOfflineSessionDurability(initialOfflineSession)" in source, "initial render ignores durability state")


def test_offline_ui_is_not_model_output() -> None:
    source = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
    require("chat-offline-session-durability" in source, "offline continuity surface missing")
    require("No provider response is fabricated" in source, "truthful offline wording missing")
    require("data-provider-dependency='none_for_local_surfaces'" in source, "provider-independent boundary missing")


def test_search_archive_and_selection_remain_local() -> None:
    session_source = (AGENT / "conversation_sessions.py").read_text(encoding="utf-8")
    navigation_source = (AGENT / "conversation_navigation.py").read_text(encoding="utf-8")
    for forbidden in ("LocalModelClient", "provider_readiness", "generate(", "stream_generate"):
        require(forbidden not in session_source, f"session storage depends on provider: {forbidden}")
        require(forbidden not in navigation_source, f"navigation depends on provider: {forbidden}")
    require("conversation_session_catalog_page" in session_source, "local search missing")
    require("archive_conversation_session" in navigation_source and "restore_conversation_session" in navigation_source, "local archive lifecycle missing")


def test_rendered_javascript_syntax() -> None:
    html = dashboard_chat_console.render_realtime_chat_panel(None, compact=True)
    require("chat-offline-session-durability" in html, "offline durability cue not rendered")
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
    node = shutil.which("node")
    if not node:
        return
    with tempfile.TemporaryDirectory(prefix="eidolon-v1082-0-js-") as raw:
        for index, script in enumerate(scripts):
            path = Path(raw) / f"script-{index}.js"
            path.write_text(script, encoding="utf-8")
            result = subprocess.run([node, "--check", str(path)], capture_output=True, text=True, timeout=30)
            require(result.returncode == 0, result.stderr or "rendered JavaScript syntax failed")


def test_profile_and_release_registration() -> None:
    core = {suite.name for suite in isolated_verify.select_suites("core")}
    require("v1082.0-offline-first-session-durability" in core, "v1082.0 absent from core profile")
    source = (TOOLS / "release_verify.py").read_text(encoding="utf-8")
    require(source.count("tools/v1082_0_offline_first_session_durability_tests.py") == 1, "v1082.0 release registration wrong")


def test_source_only_privacy() -> None:
    forbidden = (
        "data/projects.json", "data/conversation_sessions", "data/conversation_runtime",
        "data/dashboard_chat", "data/approvals", "data/tasks.json", "data/memories.json", ".venv",
    )
    files = [
        path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}
    ]
    for token in forbidden:
        require(not any(token in item for item in files), f"forbidden runtime path {token}")


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
    report = {"suite": "v1082.0-offline-first-session-durability", "ok": passed == len(TESTS), "status": "pass" if passed == len(TESTS) else "fail", "passed": passed, "total": len(TESTS), "checks": checks}
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
