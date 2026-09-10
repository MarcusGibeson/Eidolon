from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
TOOLS = ROOT / "tools"
sys.path.insert(0, str(AGENT))

import api_server
import conversation_lifecycle_recovery as lifecycle
import conversation_navigation as navigation
import conversation_sessions as sessions
import conversation_turn_presentation as turn_presentation
import daily_use_stability_checkpoint as checkpoint
import post_review_development_verify as isolated_verify
import provider_recovery_evidence as provider_evidence
import release_metadata


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


@contextmanager
def isolated_runtime():
    with tempfile.TemporaryDirectory(prefix="eidolon-v1082-9-") as raw:
        root = Path(raw)
        session_root = root / "conversation_sessions"
        provider_root = root / "provider_recovery"
        original = (
            sessions.CONVERSATION_SESSIONS_DIR,
            sessions.ACTIVE_SESSION_FILE,
            sessions.CONVERSATION_DRAFTS_DIR,
            sessions.CONVERSATION_DRAFT_CONFLICTS_DIR,
            navigation.CONVERSATION_PRESENTATION_DIR,
            navigation.CONVERSATION_NAVIGATION_CLIENTS_DIR,
            navigation.CONVERSATION_LIFECYCLE_REQUESTS_DIR,
            provider_evidence.PROVIDER_RECOVERY_DIR,
            provider_evidence.LATEST_PROVIDER_RECOVERY_FILE,
        )
        sessions.CONVERSATION_SESSIONS_DIR = session_root
        sessions.ACTIVE_SESSION_FILE = session_root / "active_session.json"
        sessions.CONVERSATION_DRAFTS_DIR = session_root / "drafts"
        sessions.CONVERSATION_DRAFT_CONFLICTS_DIR = session_root / "draft_conflicts"
        navigation.CONVERSATION_PRESENTATION_DIR = session_root / "presentation"
        navigation.CONVERSATION_NAVIGATION_CLIENTS_DIR = session_root / "navigation_clients"
        navigation.CONVERSATION_LIFECYCLE_REQUESTS_DIR = session_root / "lifecycle_requests"
        provider_evidence.PROVIDER_RECOVERY_DIR = provider_root
        provider_evidence.LATEST_PROVIDER_RECOVERY_FILE = provider_root / "latest_readiness.json"
        sessions.clear_conversation_search_cache()
        try:
            yield root
        finally:
            (
                sessions.CONVERSATION_SESSIONS_DIR,
                sessions.ACTIVE_SESSION_FILE,
                sessions.CONVERSATION_DRAFTS_DIR,
                sessions.CONVERSATION_DRAFT_CONFLICTS_DIR,
                navigation.CONVERSATION_PRESENTATION_DIR,
                navigation.CONVERSATION_NAVIGATION_CLIENTS_DIR,
                navigation.CONVERSATION_LIFECYCLE_REQUESTS_DIR,
                provider_evidence.PROVIDER_RECOVERY_DIR,
                provider_evidence.LATEST_PROVIDER_RECOVERY_FILE,
            ) = original
            sessions.clear_conversation_search_cache()


def append_turn(session_id: str, number: int, *, state: str = "completed", success: bool = True) -> dict:
    return sessions.append_conversation_turn(
        session_id,
        turn_id=f"turn-{number:04d}",
        user_message=f"operator message {number}",
        assistant_response=f"assistant response {number}" if success else "",
        completion_state=state,
        success=success,
        provider="fixture",
        model="fixture-model",
        streaming=True,
        assistant_memory_stored=bool(success),
        select_session=False,
    )


def test_release_metadata_closes_v1082_arc() -> None:
    current = tuple(int(part) for part in release_metadata.RUNTIME_VERSION.split("."))
    require(current >= (1082, 9), "runtime predates the v1082.9 checkpoint")
    history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
    require("# v1082.9 Daily-Use Stability Checkpoint" in history, "v1082.9 checkpoint history missing")
    require("332/332 across 22 core suites" in history, "v1082.9 core evidence missing")
    require("597/597 across 39 full suites" in history, "v1082.9 full evidence missing")


def test_rapid_consecutive_turns_are_idempotent() -> None:
    with isolated_runtime():
        session = sessions.create_conversation_session("Rapid consecutive turns")
        first = append_turn(session["id"], 1)
        duplicate = append_turn(session["id"], 1)
        append_turn(session["id"], 2)
        stored = sessions.load_conversation_session(session["id"], include_turns=True)
        require(first == duplicate, "duplicate turn identity changed persisted result")
        require(stored and stored["turn_count"] == 2, "duplicate turn was appended twice")


def test_cancelled_and_failed_turn_memory_boundaries() -> None:
    cancelled = turn_presentation.build_turn_presentation(
        {"operation_id": "accepted-cancelled", "accepted_at": "persisted", "public_state": "cancelled"},
        turn={"success": False, "completion_state": "cancelled"},
    )
    failed = turn_presentation.build_turn_presentation(
        {"operation_id": "accepted-failed", "accepted_at": "persisted", "public_state": "failed"},
        turn={"success": False, "completion_state": "failed"},
    )
    require(not cancelled["memory_commit_allowed"], "cancelled turn can commit assistant memory")
    require(not failed["memory_commit_allowed"], "failed turn can commit assistant memory")
    require(not cancelled["automatic_resend"] and not failed["automatic_retry"], "failure path became automatic")


def test_draft_conflict_is_preserved_and_explicitly_resolved() -> None:
    with isolated_runtime():
        session = sessions.create_conversation_session("Draft conflict")
        saved = sessions.save_conversation_draft(session["id"], "tab a", base_revision=0, editor_id="tab-a")
        conflict = sessions.save_conversation_draft(session["id"], "tab b", base_revision=0, editor_id="tab-b")
        require(saved["revision"] == 1 and conflict["draft_conflict"], "divergent edit was silently overwritten")
        conflict_id = conflict["conflict"]["conflict_id"]
        resolved = sessions.resolve_conversation_draft_conflict(
            session["id"], conflict_id, choice="incoming", expected_revision=1, editor_id="tab-b",
        )
        require(resolved["draft"]["content"] == "tab b", "explicit incoming resolution was not applied")
        require(resolved["draft"]["revision"] == 2, "draft revision did not advance after resolution")


def test_reading_state_and_large_history_windows_remain_consistent() -> None:
    with isolated_runtime():
        session = sessions.create_conversation_session("Long history")
        for number in range(1, 161):
            append_turn(session["id"], number)
        presentation = navigation.save_conversation_presentation_state(
            session["id"], follow_latest=False, scroll_from_bottom_px=420,
            composer_intentionally_empty=False, view_anchor_turn_id="turn-0100",
            view_anchor_offset_px=12, last_seen_turn_id="turn-0100", last_seen_turn_count=100,
        )
        recent = sessions.conversation_session_turn_window(session["id"], limit=60)
        earlier = sessions.conversation_session_turn_window(
            session["id"], before_turn_id=recent["oldest_turn_id"], limit=60,
        )
        require(presentation["unread_turn_count"] == 60, "unread boundary drifted")
        require(recent["shown"] == 60 and earlier["shown"] == 60, "bounded transcript windows are wrong")
        recent_ids = {turn["id"] for turn in recent["turns"]}
        earlier_ids = {turn["id"] for turn in earlier["turns"]}
        require(not recent_ids.intersection(earlier_ids), "history windows overlap")


def test_search_archive_restore_snapshot_is_consistent() -> None:
    with isolated_runtime():
        session = sessions.create_conversation_session("Search archive continuity")
        append_turn(session["id"], 1)
        before = sessions.conversation_session_catalog_page("search archive", include_archived=True)
        sessions.archive_conversation_session(session["id"])
        archived = sessions.conversation_session_catalog_page("search archive", include_archived=True)
        sessions.restore_conversation_session(session["id"])
        restored = sessions.conversation_session_catalog_page("search archive", include_archived=False)
        require(before["snapshot_consistent"] and archived["snapshot_consistent"] and restored["snapshot_consistent"], "catalog snapshot not consistent")
        require(before["catalog_revision"] != archived["catalog_revision"], "archive did not change catalog revision")
        require(restored["total"] == 1 and restored["items"][0]["status"] == "active", "restored session missing")


def test_lifecycle_recovery_never_replays_generation() -> None:
    for reason in ("history-return", "bfcache-return", "sleep-resume", "focus-recovery", "offline-recovery"):
        visible = lifecycle.lifecycle_recovery_plan(reason, hidden=False, online=True, owns_control=False, active_operation_id="accepted-operation")
        hidden = lifecycle.lifecycle_recovery_plan(reason, hidden=True, online=True, owns_control=False, active_operation_id="accepted-operation")
        require(visible["reconcile_session"] and visible["resume_operation_poll"], f"visible {reason} did not reconcile")
        require(not hidden["reconcile_session"] and not hidden["resume_operation_poll"], f"hidden {reason} started foreground work")
        for value in (visible, hidden):
            require(not value["automatic_generation_retry"] and not value["automatic_resend"], "lifecycle recovery became automatic")
            require(not value["provider_request_replayed"], "lifecycle recovery replays provider request")


def test_provider_outage_and_verified_return_remain_explicit() -> None:
    with isolated_runtime():
        digest = "a" * 64
        unavailable_report = {
            "availability": {"state": "temporarily_unavailable", "observed_state": "temporarily_unavailable", "generation_available": False, "embedding_available": False},
            "configuration_digest": digest,
            "evidence_receipt": {"receipt_type": "provider_readiness", "timestamp": "2026-07-20T00:00:00Z", "configuration_digest": digest},
        }
        ready_report = {
            "availability": {"state": "ready", "observed_state": "ready", "generation_available": True, "embedding_available": True},
            "configuration_digest": digest,
            "evidence_receipt": {"receipt_type": "provider_readiness", "timestamp": "2026-07-20T00:01:00Z", "configuration_digest": digest},
        }
        first = provider_evidence.persist_provider_recovery_evidence(unavailable_report, configured_configuration_digest=digest)
        second = provider_evidence.persist_provider_recovery_evidence(ready_report, configured_configuration_digest=digest)
        require(first["observed_state"] == "temporarily_unavailable", "unavailable evidence wrong")
        require(second["recovery_proven"] and second["recovered"], "verified provider return was not proven")
        require(not second["automatic_generation_replay"] and not second["automatic_resend"], "provider return became automatic")


def test_checkpoint_is_read_only_content_free_and_truthful() -> None:
    with isolated_runtime():
        session = sessions.create_conversation_session("Checkpoint session")
        sessions.save_conversation_draft(session["id"], "private text that must not appear", editor_id="tab-a")
        report = checkpoint.build_daily_use_stability_checkpoint(session["id"])
        serialized = json.dumps(report, sort_keys=True)
        require(report["checkpoint_status"] == "runtime_contracts_ready", "checkpoint contract status wrong")
        require(report["release_certified"] is False and report["verification_required"] is True, "runtime checkpoint pretends to certify release")
        require(report["read_only"] and report["content_free"] and report["redacted"], "checkpoint boundaries missing")
        require("private text" not in serialized, "checkpoint leaked draft content")
        require(not checkpoint.daily_use_checkpoint_contains_private_fields(report), "checkpoint contains forbidden private fields")
        require(all(value is False for value in report["boundaries"].values()), "checkpoint weakened a safety boundary")


def test_api_route_exposes_only_read_only_checkpoint() -> None:
    with isolated_runtime():
        session = sessions.create_conversation_session("API checkpoint")
        status, payload = api_server.handle_api_get(
            "/api/conversation/daily-use-stability-checkpoint", {"session_id": [session["id"]]},
        )
        data = payload.get("data") if isinstance(payload, dict) else None
        require(status == 200 and isinstance(data, dict), "checkpoint API route failed")
        require(data["session_id"] == session["id"] and data["read_only"], "checkpoint API returned wrong state")
        require("POST /api/conversation/daily-use-stability-checkpoint" not in json.dumps(api_server._api_index()), "checkpoint unexpectedly exposes a mutation route")


def test_browser_contracts_remain_wired_and_javascript_parses() -> None:
    source = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
    for token in (
        "catalogRefreshSequence", "history.state", "pageshow", "Load earlier messages",
        "draft_conflict", "applyTurnPresentation", "recoverConversationLifecycle",
    ):
        require(token in source, f"daily-use browser contract missing: {token}")
    import dashboard_chat_console
    html = dashboard_chat_console.render_realtime_chat_panel(None, compact=True)
    node = shutil.which("node")
    if not node:
        return
    with tempfile.TemporaryDirectory(prefix="eidolon-v1082-9-js-") as raw:
        cursor = 0
        index = 0
        while True:
            start = html.find("<script>", cursor)
            if start < 0:
                break
            end = html.find("</script>", start)
            require(end >= 0, "unclosed rendered script")
            path = Path(raw) / f"script-{index}.js"
            path.write_text(html[start + 8:end], encoding="utf-8")
            result = subprocess.run([node, "--check", str(path)], capture_output=True, text=True, timeout=30)
            require(result.returncode == 0, result.stderr or "rendered JavaScript failed syntax validation")
            cursor = end + 9
            index += 1


def test_narrow_layout_contains_daily_use_controls() -> None:
    console_source = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
    style_source = (AGENT / "dashboard_chat_styles.py").read_text(encoding="utf-8")
    require("@media(max-width:620px)" in style_source.replace(" ", ""), "narrow layout media query missing")
    combined = console_source + "\n" + style_source
    for token in ("chat-draft-conflict", "chat-load-earlier", "chat-jump-latest", "chat-offline-session-durability"):
        require(token in combined, f"narrow-layout control missing: {token}")


def test_registration_and_release_verification_are_exactly_once() -> None:
    core = [suite.name for suite in isolated_verify.select_suites("core")]
    full = [suite.name for suite in isolated_verify.select_suites("full")]
    require(core.count("v1082.9-daily-use-stability-checkpoint") == 1, "core registration wrong")
    require(full.count("v1082.9-daily-use-stability-checkpoint") == 1, "full registration wrong")
    release_source = (TOOLS / "release_verify.py").read_text(encoding="utf-8")
    require(release_source.count("v1082_9_daily_use_stability_checkpoint_tests.py") == 1, "release registration wrong")


def test_source_only_privacy_and_live_state_absence() -> None:
    forbidden = (
        "data/projects.json", "data/tasks.json", "data/memories.json", "data/provider_recovery/",
        "data/conversation_runtime/", "data/conversation_sessions/", "data/dashboard_chat/",
        "data/chat_actions/", "data/actions/", "data/approvals/", "data/notifications/",
    )
    files = [path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if path.is_file() and "__pycache__" not in path.parts]
    require(not [name for name in files if any(name == item or name.startswith(item) for item in forbidden)], "private runtime data present")
    require(not any(name.endswith(".zip") for name in files), "nested release archive present")


TESTS = [
    ("release_metadata_closes_v1082_arc", test_release_metadata_closes_v1082_arc),
    ("rapid_consecutive_turns_are_idempotent", test_rapid_consecutive_turns_are_idempotent),
    ("cancelled_and_failed_turn_memory_boundaries", test_cancelled_and_failed_turn_memory_boundaries),
    ("draft_conflict_is_preserved_and_explicitly_resolved", test_draft_conflict_is_preserved_and_explicitly_resolved),
    ("reading_state_and_large_history_windows_remain_consistent", test_reading_state_and_large_history_windows_remain_consistent),
    ("search_archive_restore_snapshot_is_consistent", test_search_archive_restore_snapshot_is_consistent),
    ("lifecycle_recovery_never_replays_generation", test_lifecycle_recovery_never_replays_generation),
    ("provider_outage_and_verified_return_remain_explicit", test_provider_outage_and_verified_return_remain_explicit),
    ("checkpoint_is_read_only_content_free_and_truthful", test_checkpoint_is_read_only_content_free_and_truthful),
    ("api_route_exposes_only_read_only_checkpoint", test_api_route_exposes_only_read_only_checkpoint),
    ("browser_contracts_remain_wired_and_javascript_parses", test_browser_contracts_remain_wired_and_javascript_parses),
    ("narrow_layout_contains_daily_use_controls", test_narrow_layout_contains_daily_use_controls),
    ("registration_and_release_verification_are_exactly_once", test_registration_and_release_verification_are_exactly_once),
    ("source_only_privacy_and_live_state_absence", test_source_only_privacy_and_live_state_absence),
]


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
    report = {
        "suite": "v1082.9-daily-use-stability-checkpoint",
        "ok": passed == len(TESTS),
        "status": "pass" if passed == len(TESTS) else "fail",
        "passed": passed,
        "total": len(TESTS),
        "checks": checks,
    }
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
