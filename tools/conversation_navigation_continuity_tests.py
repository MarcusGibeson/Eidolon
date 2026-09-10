from __future__ import annotations

"""Deterministic v1079.5 conversation navigation and composer continuity fixtures.

The suite uses isolated/restored runtime data. It never contacts a provider, retries
or replays generation, changes model configuration, grants approval, authorizes a
release, mines transcripts, promotes memory, or expands autonomy.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.request
import uuid
from copy import deepcopy
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
sys.path.insert(0, str(AGENT))
EXTERNAL_DATA_DIR = Path(os.environ.get("EIDOLON_DATA_DIR") or (Path(tempfile.gettempdir()) / "eidolon-navigation-continuity-fixture-data")).resolve()
os.environ["EIDOLON_DATA_DIR"] = str(EXTERNAL_DATA_DIR)


def _snapshot_tree(root: Path) -> Path:
    backup = Path(tempfile.mkdtemp(prefix="eidolon-v1079-5-navigation-backup-"))
    if root.exists():
        shutil.copytree(root, backup / "data", dirs_exist_ok=True)
    return backup


def _restore_tree(root: Path, backup: Path) -> None:
    if root.exists():
        shutil.rmtree(root)
    saved = backup / "data"
    if saved.exists():
        shutil.copytree(saved, root)
    shutil.rmtree(backup, ignore_errors=True)


def _source_snapshot() -> dict[str, str]:
    result: dict[str, str] = {}
    for path in ROOT.rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        relative = path.relative_to(ROOT).as_posix()
        if relative.startswith(("data/conversation_sessions/", "data/conversation_runtime/", "data/dashboard_chat/")):
            continue
        result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _load_modules() -> dict[str, Any]:
    import conversation_navigation
    import conversation_operations
    import dashboard
    import dashboard_chat_console
    from conversation_navigation import (
        CONVERSATION_NAVIGATION_CLIENTS_DIR,
        CONVERSATION_PRESENTATION_DIR,
        load_conversation_presentation_state,
        presentation_state_contains_private_fields,
        save_conversation_presentation_state,
        switch_conversation_session,
    )
    from conversation_operations import (
        create_operation_marker,
        finalize_operation_marker,
        load_operation_marker,
        mark_operation_client_disconnected,
        new_conversation_operation_id,
    )
    from conversation_sessions import (
        append_conversation_turn,
        clear_conversation_draft,
        conversation_history_for_prompt,
        conversation_session_turns,
        create_conversation_session,
        get_active_conversation_session,
        load_conversation_draft,
        save_conversation_draft,
        select_conversation_session,
    )
    from memory import load_memories
    from package_integrity import forbidden_runtime_path_matches
    from paths import DESIRES_FILE, MEMORY_FILE, SELF_FILE
    from settings_manager import DEFAULT_SETTINGS, save_settings

    try:
        import vector_memory
        vector_memory.add_memory_vector = lambda _memory: None
    except Exception:
        pass
    return locals()


def _seed_runtime(modules: dict[str, Any]) -> None:
    EXTERNAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    modules["SELF_FILE"].write_text(
        json.dumps({"name": "Eidolon", "mood": "steady", "energy": 0.7, "focus": "conversation", "active_goals": []}),
        encoding="utf-8",
    )
    modules["DESIRES_FILE"].write_text(json.dumps({"connection": 0.8}), encoding="utf-8")
    modules["MEMORY_FILE"].write_text(
        json.dumps([{"id": "memory_fixture", "type": "relationship_fact", "content": "Explicit fixture memory", "importance": "medium"}]),
        encoding="utf-8",
    )
    settings = deepcopy(modules["DEFAULT_SETTINGS"])
    settings.update({
        "local_model_provider": "ollama",
        "local_model": "navigation-fixture-model",
        "local_model_endpoint": "http://localhost:11434",
        "ai_chat_enabled": True,
    })
    modules["save_settings"](settings)


def _run_check(name: str, function: Callable[[], None]) -> dict[str, Any]:
    try:
        function()
        return {"name": name, "status": "pass"}
    except Exception as error:
        return {"name": name, "status": "fail", "error": f"{type(error).__name__}: {error}"}


def _json_post(url: str, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    backup = _snapshot_tree(EXTERNAL_DATA_DIR)
    source_before = _source_snapshot()
    checks: list[dict[str, Any]] = []
    restored = False
    restore_error = ""
    server: ThreadingHTTPServer | None = None
    server_thread: threading.Thread | None = None
    modules: dict[str, Any] = {}
    try:
        if EXTERNAL_DATA_DIR.exists():
            shutil.rmtree(EXTERNAL_DATA_DIR)
        modules = _load_modules()
        _seed_runtime(modules)
        console = modules["dashboard_chat_console"]

        a = modules["create_conversation_session"]("Conversation A", source="navigation_fixture")
        b = modules["create_conversation_session"]("Conversation B", source="navigation_fixture")
        c = modules["create_conversation_session"]("Conversation C", source="navigation_fixture")
        modules["save_conversation_draft"](a["id"], "draft A", client_updated_at="2099-01-01T12:00:00.000Z")
        modules["save_conversation_draft"](b["id"], "draft B", client_updated_at="2099-01-01T12:00:01.000Z")
        modules["save_conversation_draft"](c["id"], "", client_updated_at="2099-01-01T12:00:02.000Z")
        modules["append_conversation_turn"](
            a["id"], turn_id="turn_a", user_message="A user", assistant_response="A assistant",
            completion_state="completed", success=True, select_session=False,
        )
        modules["append_conversation_turn"](
            b["id"], turn_id="turn_b", user_message="B user", assistant_response="B assistant",
            completion_state="completed", success=True, select_session=False,
        )
        modules["select_conversation_session"](a["id"])

        def presentation_state_is_atomic_content_free_and_bounded() -> None:
            result = modules["save_conversation_presentation_state"](
                a["id"], follow_latest=False, scroll_from_bottom_px=9_999_999,
                composer_intentionally_empty=False, client_updated_at="2099-01-01T12:01:00.000Z",
            )
            loaded = modules["load_conversation_presentation_state"](a["id"])
            assert result["changed"] is True
            assert loaded["follow_latest"] is False
            assert loaded["scroll_from_bottom_px"] == 1_000_000
            assert loaded["composer_intentionally_empty"] is False
            assert loaded["content_free"] is True and loaded["local_private"] is True
            assert modules["presentation_state_contains_private_fields"](loaded) is False
            encoded = json.dumps(loaded).lower()
            for forbidden in ("draft a", "a user", "a assistant", "provider", "model", "operation_id", "receipt"):
                assert forbidden not in encoded
            try:
                modules["save_conversation_presentation_state"](
                    a["id"], follow_latest=True, scroll_from_bottom_px=0,
                    composer_intentionally_empty=True, client_updated_at="draft text disguised as a timestamp",
                )
            except ValueError as error:
                assert "timestamp" in str(error).lower()
            else:
                raise AssertionError("Free-form presentation timestamps must be rejected.")
        checks.append(_run_check("presentation_state_is_atomic_private_content_free_and_bounded", presentation_state_is_atomic_content_free_and_bounded))

        def source_draft_and_presentation_save_before_exact_target_selection() -> None:
            client = str(uuid.uuid4())
            result = modules["switch_conversation_session"](
                source_session_id=a["id"], target_session_id=b["id"], navigation_client_id=client,
                selection_generation=1, source_draft_content="A switched draft",
                source_draft_updated_at="2099-01-01T12:02:00.000Z",
                source_follow_latest=False, source_scroll_from_bottom_px=144,
                source_composer_intentionally_empty=False,
                source_presentation_updated_at="2099-01-01T12:02:00.000Z",
            )
            assert result["status"] == "selected" and result["selected_session_id"] == b["id"]
            assert modules["load_conversation_draft"](a["id"])["content"] == "A switched draft"
            presentation = modules["load_conversation_presentation_state"](a["id"])
            assert presentation["follow_latest"] is False and presentation["scroll_from_bottom_px"] == 144
            assert modules["get_active_conversation_session"]()["id"] == b["id"]
        checks.append(_run_check("source_draft_and_presentation_are_saved_before_exact_target_selection", source_draft_and_presentation_save_before_exact_target_selection))

        def target_snapshot_restores_only_target_content() -> None:
            snapshot = console.dashboard_chat_session_snapshot(b["id"])
            assert snapshot["session"]["id"] == b["id"]
            assert snapshot["draft"]["content"] == "draft B"
            assert "B user" in snapshot["transcript_html"] and "B assistant" in snapshot["transcript_html"]
            assert "A user" not in snapshot["transcript_html"] and "A switched draft" not in snapshot["transcript_html"]
            assert snapshot["presentation"]["session_id"] == b["id"]
        checks.append(_run_check("target_snapshot_restores_only_target_draft_transcript_and_state", target_snapshot_restores_only_target_content))

        def empty_draft_is_isolated_and_explicitly_representable() -> None:
            modules["save_conversation_presentation_state"](
                c["id"], follow_latest=True, scroll_from_bottom_px=0,
                composer_intentionally_empty=True, client_updated_at="2099-01-01T12:03:00.000Z",
            )
            snapshot = console.dashboard_chat_session_snapshot(c["id"])
            assert snapshot["draft"]["content"] == ""
            assert snapshot["presentation"]["composer_intentionally_empty"] is True
            assert modules["load_conversation_draft"](b["id"])["content"] == "draft B"
        checks.append(_run_check("intentionally_empty_composer_state_remains_isolated_per_session", empty_draft_is_isolated_and_explicitly_representable))

        def rapid_a_b_a_rejects_late_b_selection() -> None:
            modules["select_conversation_session"](a["id"])
            client = str(uuid.uuid4())
            first = modules["switch_conversation_session"](
                source_session_id=a["id"], target_session_id=b["id"], navigation_client_id=client,
                selection_generation=1, source_draft_content="A first", source_draft_updated_at="2099-01-01T12:04:00.000Z",
                source_follow_latest=True, source_scroll_from_bottom_px=0, source_composer_intentionally_empty=False,
                source_presentation_updated_at="2099-01-01T12:04:00.000Z",
            )
            second = modules["switch_conversation_session"](
                source_session_id=b["id"], target_session_id=a["id"], navigation_client_id=client,
                selection_generation=2, source_draft_content="B first", source_draft_updated_at="2099-01-01T12:04:01.000Z",
                source_follow_latest=True, source_scroll_from_bottom_px=0, source_composer_intentionally_empty=False,
                source_presentation_updated_at="2099-01-01T12:04:01.000Z",
            )
            late = modules["switch_conversation_session"](
                source_session_id=a["id"], target_session_id=b["id"], navigation_client_id=client,
                selection_generation=1, source_draft_content="A stale", source_draft_updated_at="2099-01-01T12:03:59.000Z",
                source_follow_latest=False, source_scroll_from_bottom_px=999, source_composer_intentionally_empty=False,
                source_presentation_updated_at="2099-01-01T12:03:59.000Z",
            )
            assert first["status"] == "selected" and second["status"] == "selected"
            assert late["stale_selection_ignored"] is True
            assert modules["get_active_conversation_session"]()["id"] == a["id"]
            assert modules["load_conversation_draft"](a["id"])["content"] == "A first"
        checks.append(_run_check("rapid_a_to_b_to_a_switching_rejects_late_selection_and_draft_activity", rapid_a_b_a_rejects_late_b_selection))

        def rapid_a_b_c_out_of_order_stays_on_c() -> None:
            modules["select_conversation_session"](a["id"])
            client = str(uuid.uuid4())
            newer = modules["switch_conversation_session"](
                source_session_id=a["id"], target_session_id=c["id"], navigation_client_id=client,
                selection_generation=2, source_draft_content="A newest", source_draft_updated_at="2099-01-01T12:05:02.000Z",
                source_follow_latest=True, source_scroll_from_bottom_px=0, source_composer_intentionally_empty=False,
                source_presentation_updated_at="2099-01-01T12:05:02.000Z",
            )
            older = modules["switch_conversation_session"](
                source_session_id=a["id"], target_session_id=b["id"], navigation_client_id=client,
                selection_generation=1, source_draft_content="A older", source_draft_updated_at="2099-01-01T12:05:01.000Z",
                source_follow_latest=False, source_scroll_from_bottom_px=800, source_composer_intentionally_empty=False,
                source_presentation_updated_at="2099-01-01T12:05:01.000Z",
            )
            assert newer["selected_session_id"] == c["id"]
            assert older["stale_selection_ignored"] is True
            assert modules["get_active_conversation_session"]()["id"] == c["id"]
        checks.append(_run_check("rapid_a_to_b_to_c_out_of_order_delivery_keeps_newest_target", rapid_a_b_c_out_of_order_stays_on_c))

        def same_content_save_advances_ordering_barrier() -> None:
            modules["save_conversation_draft"](b["id"], "ordering", client_updated_at="2099-01-01T12:06:00.000Z")
            fresh = modules["save_conversation_draft"](b["id"], "ordering", client_updated_at="2099-01-01T12:06:02.000Z")
            stale = modules["save_conversation_draft"](b["id"], "stale overwrite", client_updated_at="2099-01-01T12:06:01.000Z")
            assert fresh["changed"] is False
            assert stale["stale_update_ignored"] is True
            assert modules["load_conversation_draft"](b["id"])["content"] == "ordering"
        checks.append(_run_check("same_content_draft_save_advances_stale_response_ordering_barrier", same_content_save_advances_ordering_barrier))

        def same_presentation_save_advances_ordering_barrier() -> None:
            modules["save_conversation_presentation_state"](
                b["id"], follow_latest=True, scroll_from_bottom_px=0, composer_intentionally_empty=False,
                client_updated_at="2099-01-01T12:07:00.000Z",
            )
            fresh = modules["save_conversation_presentation_state"](
                b["id"], follow_latest=True, scroll_from_bottom_px=0, composer_intentionally_empty=False,
                client_updated_at="2099-01-01T12:07:02.000Z",
            )
            stale = modules["save_conversation_presentation_state"](
                b["id"], follow_latest=False, scroll_from_bottom_px=321, composer_intentionally_empty=True,
                client_updated_at="2099-01-01T12:07:01.000Z",
            )
            assert fresh["changed"] is False and stale["stale_update_ignored"] is True
            current = modules["load_conversation_presentation_state"](b["id"])
            assert current["follow_latest"] is True and current["scroll_from_bottom_px"] == 0
        checks.append(_run_check("same_presentation_save_advances_stale_response_ordering_barrier", same_presentation_save_advances_ordering_barrier))

        def accepted_tombstone_and_newer_draft_ordering_remains_safe() -> None:
            modules["save_conversation_draft"](a["id"], "message being sent", client_updated_at="2099-01-01T12:08:00.000Z")
            tombstone = modules["clear_conversation_draft"](a["id"], source="navigation_fixture_acceptance")
            newer = modules["save_conversation_draft"](a["id"], "newer unsent draft", client_updated_at="2100-01-01T00:00:00.000Z")
            stale = modules["save_conversation_draft"](a["id"], "message being sent", client_updated_at="2099-01-01T12:08:00.000Z")
            assert tombstone["has_draft"] is False and newer["has_draft"] is True
            assert stale["stale_update_ignored"] is True
            assert modules["load_conversation_draft"](a["id"])["content"] == "newer unsent draft"
        checks.append(_run_check("delayed_acceptance_tombstone_never_clears_or_restores_wrong_draft", accepted_tombstone_and_newer_draft_ordering_remains_safe))

        def browser_contract_binds_every_async_result_to_selection_generation() -> None:
            modules["select_conversation_session"](a["id"])
            html = console.render_realtime_chat_panel(None)
            required = (
                "nextSelectionGeneration()", "generation !== selectionRequestToken", "isCurrentSelection(turnSessionId, turnGeneration)",
                "/api/dashboard-chat/session-switch", "source_draft_content", "source_presentation_updated_at",
                "eidolon.chat.presentation.v2.", "eidolon.chat.navigation.v1", "clearAcceptedDraft(turnSessionId",
                "restoreUnacceptedDraft(turnSessionId, turnDraftKey, message, turnGeneration)",
                "Your newer draft was preserved instead of being overwritten.",
            )
            for token in required:
                assert token in html
            assert "sessionBox.value = payload.session_id" not in html
            assert "if (activeController) activeController.abort();" not in html
        checks.append(_run_check("browser_navigation_contract_rejects_stale_session_load_save_and_acceptance_results", browser_contract_binds_every_async_result_to_selection_generation))

        def running_operation_survives_switch_and_reconciles_on_return() -> None:
            modules["select_conversation_session"](a["id"])
            operation_id = modules["new_conversation_operation_id"]()
            modules["create_operation_marker"](operation_id, a["id"], acceptance_key="navigation-running-key")
            job = console._DashboardOperationJob(operation_id=operation_id, session_id=a["id"], turn_id=operation_id)
            with console._DASHBOARD_OPERATION_LOCK:
                console._DASHBOARD_OPERATION_JOBS[operation_id] = job
            try:
                client = str(uuid.uuid4())
                modules["switch_conversation_session"](
                    source_session_id=a["id"], target_session_id=b["id"], navigation_client_id=client,
                    selection_generation=1, source_draft_content="leave while running",
                    source_draft_updated_at="2099-01-01T12:09:00.000Z", source_follow_latest=True,
                    source_scroll_from_bottom_px=0, source_composer_intentionally_empty=False,
                    source_presentation_updated_at="2099-01-01T12:09:00.000Z",
                )
                marker = modules["load_operation_marker"](operation_id)
                assert marker["public_state"] == "running" and marker["cancellation_requested"] is False
                assert modules["get_active_conversation_session"]()["id"] == b["id"]
                snapshot = console.dashboard_chat_session_snapshot(a["id"])
                assert snapshot["operation_status"]["operation"]["operation_id"] == operation_id
                assert snapshot["operation_status"]["session_cue"]["label"] == "Still responding"
            finally:
                job.done = True
                console._discard_dashboard_operation_job(operation_id)
        checks.append(_run_check("switching_away_never_cancels_running_operation_and_switching_back_reconciles_same_id", running_operation_survives_switch_and_reconciles_on_return))

        def late_completion_attaches_once_without_stealing_selection() -> None:
            modules["select_conversation_session"](b["id"])
            operation_id = modules["new_conversation_operation_id"]()
            modules["create_operation_marker"](operation_id, a["id"], acceptance_key="navigation-late-key")
            modules["mark_operation_client_disconnected"](operation_id)
            modules["append_conversation_turn"](
                a["id"], turn_id=operation_id, user_message="late user", assistant_response="late assistant",
                completion_state="completed", success=True, select_session=False,
            )
            modules["append_conversation_turn"](
                a["id"], turn_id=operation_id, user_message="duplicate", assistant_response="duplicate",
                completion_state="completed", success=True, select_session=False,
            )
            modules["finalize_operation_marker"](
                operation_id, completion_state="completed", success=True, final_session_turn_recorded=True,
            )
            modules["finalize_operation_marker"](
                operation_id, completion_state="failed", success=False, failure_category="late_packet",
                final_session_turn_recorded=True,
            )
            assert modules["get_active_conversation_session"]()["id"] == b["id"]
            matching = [turn for turn in modules["conversation_session_turns"](a["id"]) if turn["id"] == operation_id]
            assert len(matching) == 1 and matching[0]["assistant_response"] == "late assistant"
            snapshot = console.dashboard_chat_session_snapshot(a["id"])
            assert snapshot["transcript_html"].count("late assistant") == 1
            assert snapshot["operation_status"]["session_cue"]["label"] == "Reply ready"
        checks.append(_run_check("late_completion_after_switch_attaches_once_without_stealing_active_selection", late_completion_attaches_once_without_stealing_selection))

        def transcript_operation_and_draft_state_are_isolated() -> None:
            a_snapshot = console.dashboard_chat_session_snapshot(a["id"])
            b_snapshot = console.dashboard_chat_session_snapshot(b["id"])
            assert "A assistant" in a_snapshot["transcript_html"] and "B assistant" not in a_snapshot["transcript_html"]
            assert "B assistant" in b_snapshot["transcript_html"] and "A assistant" not in b_snapshot["transcript_html"]
            assert a_snapshot["draft"]["content"] != b_snapshot["draft"]["content"]
            if a_snapshot["operation_status"].get("operation"):
                assert a_snapshot["operation_status"]["operation"]["session_id"] == a["id"]
        checks.append(_run_check("transcript_draft_and_operation_cues_never_cross_session_boundaries", transcript_operation_and_draft_state_are_isolated))

        def ordinary_open_is_distinct_from_open_and_mark_seen() -> None:
            modules["select_conversation_session"](b["id"])
            operation_id = modules["new_conversation_operation_id"]()
            modules["create_operation_marker"](operation_id, c["id"], acceptance_key="navigation-cue-key")
            modules["finalize_operation_marker"](operation_id, completion_state="failed", success=False, failure_category="timeout")
            html = console.render_realtime_chat_panel(None)
            assert "data-chat-session-open" in html
            assert "data-chat-session-open-seen" in html
            assert "<button type='submit'>Open</button>" in html
            assert "Open and mark seen" in html
            assert "dashboard_chat_session_select_and_acknowledge" in html
            normal_action = html.split("data-chat-session-open>", 1)[1].split("</form>", 1)[0]
            assert "acknowledgement_token" not in normal_action
        checks.append(_run_check("ordinary_open_and_explicit_open_and_mark_seen_are_separate_actions", ordinary_open_is_distinct_from_open_and_mark_seen))

        def provider_settings_departure_preserves_draft_presentation_and_session() -> None:
            modules["select_conversation_session"](a["id"])
            before = modules["get_active_conversation_session"]()["id"]
            html = console.render_realtime_chat_panel(None)
            assert "/local-model?return_to=chat#local-model-config-form" in html
            assert "await persistDraft({ sessionId:targetSessionId" in html
            assert "await persistPresentation({ sessionId:targetSessionId" in html
            assert modules["get_active_conversation_session"]()["id"] == before
        checks.append(_run_check("provider_settings_departure_and_return_preserve_selected_session_draft_and_presentation", provider_settings_departure_preserves_draft_presentation_and_session))

        def passive_snapshot_and_switching_do_not_mutate_continuity() -> None:
            modules["select_conversation_session"](a["id"])
            before_memory = modules["MEMORY_FILE"].read_bytes()
            before_self = modules["SELF_FILE"].read_bytes()
            before_desires = modules["DESIRES_FILE"].read_bytes()
            before_history = modules["conversation_history_for_prompt"](a["id"])
            before_turns = modules["conversation_session_turns"](a["id"])
            console.dashboard_chat_session_snapshot(a["id"])
            client = str(uuid.uuid4())
            modules["switch_conversation_session"](
                source_session_id=a["id"], target_session_id=b["id"], navigation_client_id=client,
                selection_generation=1, source_draft_content="continuity neutral",
                source_draft_updated_at="2099-01-01T12:10:00.000Z", source_follow_latest=True,
                source_scroll_from_bottom_px=0, source_composer_intentionally_empty=False,
                source_presentation_updated_at="2099-01-01T12:10:00.000Z",
            )
            assert modules["MEMORY_FILE"].read_bytes() == before_memory
            assert modules["SELF_FILE"].read_bytes() == before_self
            assert modules["DESIRES_FILE"].read_bytes() == before_desires
            assert modules["conversation_history_for_prompt"](a["id"]) == before_history
            assert modules["conversation_session_turns"](a["id"]) == before_turns
        checks.append(_run_check("navigation_and_passive_snapshot_do_not_mutate_prompt_memory_relationship_mood_or_moments", passive_snapshot_and_switching_do_not_mutate_continuity))

        def get_snapshot_is_side_effect_free_and_post_switch_is_bounded() -> None:
            server = ThreadingHTTPServer(("127.0.0.1", 0), modules["dashboard"].EidolonDashboardHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            pointer = EXTERNAL_DATA_DIR / "conversation_sessions" / "active_session.json"
            before_pointer = pointer.read_bytes()
            before_memory = modules["MEMORY_FILE"].read_bytes()
            try:
                with urllib.request.urlopen(base + "/api/dashboard-chat/session?session_id=" + a["id"], timeout=5) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                assert payload["ok"] is True and payload["session"]["id"] == a["id"]
                assert pointer.read_bytes() == before_pointer and modules["MEMORY_FILE"].read_bytes() == before_memory
                status, switched = _json_post(base + "/api/dashboard-chat/session-switch", {
                    "source_session_id": b["id"], "target_session_id": c["id"],
                    "navigation_client_id": str(uuid.uuid4()), "selection_generation": 1,
                    "source_draft_content": "HTTP source", "source_draft_updated_at": "2099-01-01T12:11:00.000Z",
                    "source_follow_latest": False, "source_scroll_from_bottom_px": 77,
                    "source_composer_intentionally_empty": False,
                    "source_presentation_updated_at": "2099-01-01T12:11:00.000Z",
                })
                assert status == 200 and switched["snapshot"]["session"]["id"] == c["id"]
                assert modules["load_conversation_draft"](b["id"])["content"] == "HTTP source"
                assert "source_draft_content" not in json.dumps(switched["snapshot"])
            finally:
                server.shutdown(); server.server_close(); thread.join(timeout=3)
        checks.append(_run_check("get_snapshot_is_read_only_while_post_switch_saves_source_then_selects_target", get_snapshot_is_side_effect_free_and_post_switch_is_bounded))

        def rendered_javascript_is_valid_and_contains_no_implicit_governance() -> None:
            modules["select_conversation_session"](a["id"])
            html = console.render_realtime_chat_panel(None)
            script = html[html.rfind("<script>") + len("<script>"):html.rfind("</script>")]
            script_path = Path(tempfile.mkdtemp(prefix="eidolon-nav-js-")) / "chat.js"
            script_path.write_text(script, encoding="utf-8")
            try:
                completed = subprocess.run(["node", "--check", str(script_path)], capture_output=True, text=True, timeout=20)
                assert completed.returncode == 0, completed.stderr
            finally:
                shutil.rmtree(script_path.parent, ignore_errors=True)
            lowered = script.lower()
            for forbidden in ("ollama pull", "install model", "delete model", "automatic fallback", "grant approval", "authorize release"):
                assert forbidden not in lowered
        checks.append(_run_check("rendered_navigation_javascript_is_valid_and_adds_no_provider_model_or_governance_authority", rendered_javascript_is_valid_and_contains_no_implicit_governance))

        def package_rules_exclude_all_navigation_runtime_records() -> None:
            candidates = [
                "data/projects.json",
                "data/conversation_sessions/conversation_session_fixture.json",
                "data/conversation_sessions/drafts/conversation_session_fixture.json",
                "data/conversation_sessions/presentation/conversation_session_fixture.json",
                "data/conversation_sessions/navigation_clients/client.json",
                "data/conversation_sessions/operations/operation.json",
                "data/conversation_sessions/operation_acknowledgements/ack.json",
                "data/memories.json",
                "data/dashboard_chat/turn.json",
                "reports/private.json",
                "nested.zip",
            ]
            forbidden = modules["forbidden_runtime_path_matches"](candidates)
            for candidate in candidates[:-2]:
                assert candidate in forbidden
            assert modules["CONVERSATION_PRESENTATION_DIR"].is_relative_to(EXTERNAL_DATA_DIR / "conversation_sessions")
            assert modules["CONVERSATION_NAVIGATION_CLIENTS_DIR"].is_relative_to(EXTERNAL_DATA_DIR / "conversation_sessions")
        checks.append(_run_check("source_only_package_rules_exclude_drafts_operations_acknowledgements_and_presentation_records", package_rules_exclude_all_navigation_runtime_records))

        def source_tree_and_runtime_restore_contract() -> None:
            assert _source_snapshot() == source_before
        checks.append(_run_check("source_tree_remains_immutable_during_isolated_runtime_fixtures", source_tree_and_runtime_restore_contract))

    finally:
        try:
            _restore_tree(EXTERNAL_DATA_DIR, backup)
            restored = True
        except Exception as error:
            restore_error = f"{type(error).__name__}: {error}"

    failed = [check for check in checks if check["status"] != "pass"]
    report = {
        "ok": not failed and restored,
        "status": "pass" if not failed and restored else "blocked",
        "suite": "conversation_navigation_and_composer_continuity",
        "version": "1079.5",
        "evidence_kind": "deterministic_fixture",
        "native_provider_contacted": False,
        "automatic_retry_performed": False,
        "model_management_performed": False,
        "passed": len(checks) - len(failed),
        "total": len(checks),
        "checks": checks,
        "runtime_data_restored": restored,
        "runtime_data_restore_error": restore_error or None,
    }
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"{report['status']}: {report['passed']}/{report['total']}")
        for check in checks:
            suffix = f" - {check['error']}" if check.get("error") else ""
            print(f"- {check['status']}: {check['name']}{suffix}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
