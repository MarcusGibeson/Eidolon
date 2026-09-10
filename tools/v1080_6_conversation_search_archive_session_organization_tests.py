from __future__ import annotations

import argparse
import json
import subprocess
import sys
sys.dont_write_bytecode = True
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))

import conversation_sessions as sessions
import dashboard_chat_console as dashboard_chat
import release_metadata


class Failure(AssertionError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Failure(message)


@contextmanager
def isolated_runtime():
    with tempfile.TemporaryDirectory(prefix="eidolon-v1080-6-catalog-") as raw:
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
        sessions.LEGACY_DASHBOARD_CHAT_IMPORT_FILE = sessions.CONVERSATION_SESSIONS_DIR / "legacy_import.json"
        sessions.clear_conversation_search_cache()
        try:
            yield root
        finally:
            sessions.clear_conversation_search_cache()
            for key, value in originals.items():
                setattr(sessions, key, value)


def _turn(session_id: str, turn_id: str, user: str, assistant: str, *, success: bool = True, created_at: str = "") -> None:
    sessions.append_conversation_turn(
        session_id,
        turn_id=turn_id,
        user_message=user,
        assistant_response=assistant,
        completion_state="completed" if success else "failed",
        success=success,
        provider="test",
        model="test",
        created_at=created_at,
        select_session=False,
        allow_default_title_update=False,
    )


def _set_session_times(session_id: str, *, created_at: str, updated_at: str) -> None:
    value = sessions.load_conversation_session(session_id, include_turns=True) or {}
    value["created_at"] = created_at
    value["updated_at"] = updated_at
    value["last_turn_at"] = updated_at
    sessions._atomic_write(sessions._session_path(session_id), value)


def test_ranked_private_search_matches_title_and_completed_text() -> None:
    with isolated_runtime():
        title_hit = sessions.create_conversation_session("Project Orion planning", select_session=False)
        body_hit = sessions.create_conversation_session("General notes", select_session=False)
        _turn(body_hit["id"], "turn_body", "We should review Project Orion tomorrow.", "I can help organize that plan.")
        page = sessions.conversation_session_catalog_page("project orion", include_archived=True, limit=10)
        ids = [item["id"] for item in page["items"]]
        require(ids[:2] == [title_hit["id"], body_hit["id"]], f"search ranking drifted: {ids}")
        require(page["items"][0]["match_source"] == "title", "title result lost its source")
        require(page["items"][1]["match_source"] == "completed_turn", "completed turn result lost its source")
        require(page["receipts_included"] is False and page["private_local_search"] is True, "search boundary metadata drifted")


def test_search_excludes_failed_turns_and_action_receipt_text() -> None:
    with isolated_runtime():
        session = sessions.create_conversation_session("Boundaries", select_session=False)
        _turn(session["id"], "failed", "FAILED-ONLY-SECRET", "failed response", success=False)
        _turn(session["id"], "completed", "Normal conversation", "Ordinary answer")
        value = sessions.load_conversation_session(session["id"], include_turns=True) or {}
        value["turns"][-1]["operator_action"] = {"command": "ACTION-ONLY-SECRET", "raw_output": "PRIVATE"}
        sessions._atomic_write(sessions._session_path(session["id"]), value)
        sessions.clear_conversation_search_cache()
        require(sessions.conversation_session_catalog_page("FAILED-ONLY-SECRET")["total"] == 0, "failed turn entered search")
        require(sessions.conversation_session_catalog_page("ACTION-ONLY-SECRET")["total"] == 0, "action receipt entered search")


def test_search_normalizes_polite_multiword_queries_without_broad_or_matching() -> None:
    with isolated_runtime():
        match = sessions.create_conversation_session("Maintenance and settings", select_session=False)
        partial = sessions.create_conversation_session("Maintenance only", select_session=False)
        page = sessions.conversation_session_catalog_page("  MAINTENANCE   settings ", limit=10)
        require([item["id"] for item in page["items"]] == [match["id"]], "multiword search did not require all terms")
        require(partial["id"] not in [item["id"] for item in page["items"]], "search broadened into OR matching")


def test_large_catalog_pagination_is_stable_and_nonduplicating() -> None:
    with isolated_runtime():
        for index in range(67):
            session = sessions.create_conversation_session(f"Conversation {index:02d}", select_session=False)
            _set_session_times(
                session["id"],
                created_at=f"2026-05-{(index % 28) + 1:02d}T10:00:00Z",
                updated_at=f"2026-07-{(index % 18) + 1:02d}T10:{index % 60:02d}:00Z",
            )
        pages = [sessions.conversation_session_catalog_page("", offset=offset, limit=20) for offset in (0, 20, 40, 60)]
        ids = [item["id"] for page in pages for item in page["items"]]
        require(len(ids) == 67 and len(set(ids)) == 67, "pagination duplicated or omitted conversations")
        require(pages[0]["has_previous"] is False and pages[-1]["has_next"] is False, "pagination boundaries drifted")
        clamped = sessions.conversation_session_catalog_page("", offset=9999, limit=20)
        require(clamped["offset"] == 60 and clamped["shown"] == 7, "out-of-range offset was not clamped to the last page")


def test_duplicate_titles_receive_stable_disambiguated_labels() -> None:
    with isolated_runtime():
        first = sessions.create_conversation_session("Daily notes", select_session=False)
        second = sessions.create_conversation_session("Daily notes", select_session=False)
        _set_session_times(first["id"], created_at="2026-07-01T10:00:00Z", updated_at="2026-07-02T10:00:00Z")
        _set_session_times(second["id"], created_at="2026-07-03T10:00:00Z", updated_at="2026-07-04T10:00:00Z")
        items = sessions.conversation_session_catalog_page("daily notes", limit=10)["items"]
        require(len(items) == 2 and all(item["duplicate_title"] for item in items), "duplicate titles were not marked")
        labels = [item["display_title"] for item in items]
        require(len(set(labels)) == 2 and all("Daily notes · Jul" in label for label in labels), f"duplicate labels are not distinct: {labels}")
        sessions.archive_conversation_session(first["id"])
        active_only = sessions.conversation_session_catalog_page("daily notes", include_archived=False, limit=10)["items"]
        require(len(active_only) == 1 and active_only[0]["duplicate_title"], "duplicate label changed when its counterpart was archived")


def test_recency_groups_are_deterministic() -> None:
    now = datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc)
    require(sessions.conversation_session_group_label("2026-07-18T01:00:00Z", now=now) == "Today", "today grouping failed")
    require(sessions.conversation_session_group_label("2026-07-17T01:00:00Z", now=now) == "Yesterday", "yesterday grouping failed")
    require(sessions.conversation_session_group_label("2026-07-13T01:00:00Z", now=now) == "Previous 7 days", "week grouping failed")
    require(sessions.conversation_session_group_label("2026-06-30T01:00:00Z", now=now) == "Previous 30 days", "month-window grouping failed")
    require(sessions.conversation_session_group_label("2026-05-01T01:00:00Z", now=now) == "May 2026", "historical month grouping failed")


def test_archive_restore_search_visibility_and_history_preservation() -> None:
    with isolated_runtime():
        session = sessions.create_conversation_session("Archive target", select_session=False)
        _turn(session["id"], "turn", "Remember this searchable phrase", "It remains private local history.")
        sessions.archive_conversation_session(session["id"])
        require(sessions.conversation_session_catalog_page("searchable phrase", include_archived=False)["total"] == 0, "archived session appeared without opt-in")
        archived = sessions.conversation_session_catalog_page("searchable phrase", include_archived=True)
        require(archived["total"] == 1 and archived["items"][0]["status"] == "archived", "archived search result was unavailable")
        sessions.restore_conversation_session(session["id"])
        restored = sessions.conversation_session_catalog_page("searchable phrase", include_archived=False)
        require(restored["total"] == 1, "restored conversation did not return to active search")
        require(sessions.load_conversation_session(session["id"], include_turns=True)["turn_count"] == 1, "archive/restore altered history")


def test_archived_draft_is_preserved_but_cannot_be_mutated_until_restore() -> None:
    with isolated_runtime():
        session = sessions.create_conversation_session("Draft archive", select_session=False)
        sessions.save_conversation_draft(session["id"], "private unsent draft")
        sessions.archive_conversation_session(session["id"])
        try:
            sessions.save_conversation_draft(session["id"], "changed while archived")
        except ValueError:
            pass
        else:
            raise Failure("archived draft mutation was allowed")
        require(sessions.load_conversation_draft(session["id"])["content"] == "private unsent draft", "archive discarded the draft")
        sessions.restore_conversation_session(session["id"])
        sessions.save_conversation_draft(session["id"], "restored draft")
        require(sessions.load_conversation_draft(session["id"])["content"] == "restored draft", "restored draft could not be edited")


def test_search_cache_invalidates_after_rename_and_new_turn() -> None:
    with isolated_runtime():
        session = sessions.create_conversation_session("Original title", select_session=False)
        require(sessions.conversation_session_catalog_page("original title")["total"] == 1, "initial title was not searchable")
        sessions.rename_conversation_session(session["id"], "Renamed conversation")
        require(sessions.conversation_session_catalog_page("renamed conversation")["total"] == 1, "cache did not observe rename")
        _turn(session["id"], "new-turn", "A newly indexed lighthouse phrase", "Acknowledged.")
        require(sessions.conversation_session_catalog_page("lighthouse phrase")["total"] == 1, "cache did not observe appended turn")


def test_catalog_bounds_query_and_page_size() -> None:
    with isolated_runtime():
        sessions.create_conversation_session("Bounded", select_session=False)
        page = sessions.conversation_session_catalog_page("", limit=9999)
        require(page["limit"] == sessions.MAX_CONVERSATION_SEARCH_LIMIT, "catalog limit was not bounded")
        try:
            sessions.conversation_session_catalog_page("x" * (sessions.MAX_CONVERSATION_SEARCH_QUERY_CHARS + 1))
        except ValueError:
            pass
        else:
            raise Failure("oversized search query was accepted")


def test_dashboard_catalog_state_and_page_are_bounded_and_receipt_free() -> None:
    with isolated_runtime():
        session = sessions.create_conversation_session("Dashboard catalog", select_session=True)
        _turn(session["id"], "turn", "Find the orchard", "The orchard is here.")
        state = dashboard_chat.dashboard_chat_session_catalog_state(include_archived=True)
        page = dashboard_chat.dashboard_chat_session_catalog_page(query="orchard", include_archived=True, offset=0, limit=30)
        serialized = json.dumps({"state": state, "page": page})
        require(state and state[0]["display_title"], "dashboard selector metadata omitted display title")
        require(page["total"] == 1 and page["items"][0]["match_source"] == "completed_turn", "dashboard search page drifted")
        for forbidden in ("operator_action", "raw_output", "receipt_path", "provider_payload", "credentials"):
            require(forbidden not in serialized, f"dashboard catalog exposed {forbidden}")


def test_rendered_organizer_has_private_search_grouping_and_pagination() -> None:
    with isolated_runtime():
        session = sessions.create_conversation_session("Rendered catalog", select_session=True)
        _turn(session["id"], "turn", "Searchable rendering", "Visible result")
        html = dashboard_chat.render_realtime_chat_panel(None, compact=True, session_query="rendering", include_archived=True)
        for token in (
            "conversation-catalog-search-form",
            "conversation-catalog-previous",
            "conversation-catalog-next",
            "conversation-session-group",
            "/api/dashboard-chat/session-catalog?",
            "function refreshConversationOrganizer",
        ):
            require(token in html, f"rendered organizer omitted {token}")
        require(f"data-chat-version='v{release_metadata.RUNTIME_VERSION}" in html, "rendered organizer is not aligned to the current runtime")
        require("Search excludes failed turns and runtime receipts" in html, "search boundary copy drifted")


def test_rendered_javascript_syntax() -> None:
    with isolated_runtime():
        session = sessions.create_conversation_session("JavaScript", select_session=True)
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
    with tempfile.TemporaryDirectory(prefix="eidolon-v1080-6-js-") as raw:
        path = Path(raw) / "rendered.js"
        path.write_text("\n".join(scripts), encoding="utf-8")
        try:
            result = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True, timeout=30)
        except FileNotFoundError:
            return
        require(result.returncode == 0, f"rendered JavaScript syntax failed: {result.stderr.strip()}")


def test_catalog_endpoint_is_read_only_and_release_stage_is_registered_once() -> None:
    dashboard_source = (AGENT / "dashboard.py").read_text(encoding="utf-8")
    require('path == "/api/dashboard-chat/session-catalog"' in dashboard_source, "read-only catalog endpoint is missing")
    require('if parsed.path == "/api/dashboard-chat/session-catalog"' not in dashboard_source, "catalog was accidentally added as a POST mutation")
    verify_source = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
    require(verify_source.count('"conversation-search-archive-session-organization-fixtures"') == 1, "v1080.6 release stage is not registered exactly once")
    require(verify_source.count('"tools/v1080_6_conversation_search_archive_session_organization_tests.py"') == 1, "v1080.6 suite path is not registered exactly once")


def test_current_metadata_and_docs_are_aligned() -> None:
    current = tuple(int(part) for part in release_metadata.RUNTIME_VERSION.split("."))
    require(current >= (1080, 6), "runtime metadata predates v1080.6")
    history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
    require("# v1080.6 Conversation Search, Archive, and Session Organization" in history, "v1080.6 historical milestone disappeared")
    for relative in ("data/settings.json", "data/workspaces/active_project.json", "data/workspaces/projects.json"):
        require(release_metadata.RUNTIME_VERSION in (ROOT / relative).read_text(encoding="utf-8"), f"{relative} is not aligned to the current runtime")
    current_tag = f"v{release_metadata.RUNTIME_VERSION}"
    for relative in ("README.md", "README_NEXT_STEPS.md"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        require(current_tag in text, f"{relative} omits the current runtime tag")
    require("v1080.6" in history, "release history omits retained v1080.6 evidence")


def test_source_tree_remains_source_only() -> None:
    require(not (ROOT / "data" / "projects.json").exists(), "source tree contains data/projects.json")
    forbidden = ("data/chat_actions", "data/conversation_sessions", "data/approvals", "data/memories.json", ".venv", "__pycache__")
    paths = [path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if path.is_file()]
    for token in forbidden:
        require(not any(token in path for path in paths), f"source tree contains forbidden runtime token: {token}")


TESTS: tuple[tuple[str, Callable[[], None]], ...] = (
    ("ranked_private_search_matches_title_and_completed_text", test_ranked_private_search_matches_title_and_completed_text),
    ("search_excludes_failed_turns_and_action_receipt_text", test_search_excludes_failed_turns_and_action_receipt_text),
    ("search_normalizes_polite_multiword_queries_without_broad_or_matching", test_search_normalizes_polite_multiword_queries_without_broad_or_matching),
    ("large_catalog_pagination_is_stable_and_nonduplicating", test_large_catalog_pagination_is_stable_and_nonduplicating),
    ("duplicate_titles_receive_stable_disambiguated_labels", test_duplicate_titles_receive_stable_disambiguated_labels),
    ("recency_groups_are_deterministic", test_recency_groups_are_deterministic),
    ("archive_restore_search_visibility_and_history_preservation", test_archive_restore_search_visibility_and_history_preservation),
    ("archived_draft_is_preserved_but_cannot_be_mutated_until_restore", test_archived_draft_is_preserved_but_cannot_be_mutated_until_restore),
    ("search_cache_invalidates_after_rename_and_new_turn", test_search_cache_invalidates_after_rename_and_new_turn),
    ("catalog_bounds_query_and_page_size", test_catalog_bounds_query_and_page_size),
    ("dashboard_catalog_state_and_page_are_bounded_and_receipt_free", test_dashboard_catalog_state_and_page_are_bounded_and_receipt_free),
    ("rendered_organizer_has_private_search_grouping_and_pagination", test_rendered_organizer_has_private_search_grouping_and_pagination),
    ("rendered_javascript_syntax", test_rendered_javascript_syntax),
    ("catalog_endpoint_is_read_only_and_release_stage_is_registered_once", test_catalog_endpoint_is_read_only_and_release_stage_is_registered_once),
    ("current_metadata_and_docs_are_aligned", test_current_metadata_and_docs_are_aligned),
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
        "suite": "v1080.6-conversation-search-archive-session-organization",
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
