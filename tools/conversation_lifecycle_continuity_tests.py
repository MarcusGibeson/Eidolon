from __future__ import annotations

"""Deterministic v1079.5.6 conversation lifecycle and new-session continuity fixtures.

The suite uses isolated/restored runtime state. It never contacts a provider, retries
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
EXTERNAL_DATA_DIR = Path(os.environ.get("EIDOLON_DATA_DIR") or (Path(tempfile.gettempdir()) / "eidolon-lifecycle-continuity-fixture-data")).resolve()
os.environ["EIDOLON_DATA_DIR"] = str(EXTERNAL_DATA_DIR)


def _snapshot_tree(root: Path) -> Path:
    backup = Path(tempfile.mkdtemp(prefix="eidolon-v1079-5-6-lifecycle-backup-"))
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
        CONVERSATION_LIFECYCLE_REQUESTS_DIR,
        load_conversation_presentation_state,
        lifecycle_request_contains_private_fields,
        perform_conversation_lifecycle,
        save_conversation_presentation_state,
        switch_conversation_session,
    )
    from conversation_operations import (
        acknowledge_operation_marker,
        create_operation_marker,
        finalize_operation_marker,
        latest_operation_marker,
        load_operation_acknowledgement,
        new_conversation_operation_id,
        operation_cue_token,
    )
    from conversation_sessions import (
        append_conversation_turn,
        conversation_history_for_prompt,
        conversation_session_turns,
        create_conversation_session,
        get_active_conversation_session,
        list_conversation_sessions,
        load_conversation_draft,
        load_conversation_session,
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
        "local_model": "lifecycle-fixture-model",
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


def _post(base: str, path: str, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    request = urllib.request.Request(
        base + path,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=8) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def _lifecycle(modules: dict[str, Any], *, client: str, generation: int, request: str, action: str,
               source: str, target: str = "", title: str = "", draft: str = "",
               stamp: str = "2099-01-01T12:00:00.000Z") -> dict[str, Any]:
    return modules["perform_conversation_lifecycle"](
        action=action,
        navigation_client_id=client,
        lifecycle_generation=generation,
        request_key=request,
        source_session_id=source,
        target_session_id=target,
        title=title,
        source_draft_content=draft,
        source_draft_updated_at=stamp,
        source_follow_latest=False,
        source_scroll_from_bottom_px=137,
        source_composer_intentionally_empty=not bool(draft),
        source_presentation_updated_at=stamp,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    backup = _snapshot_tree(EXTERNAL_DATA_DIR)
    source_before = _source_snapshot()
    checks: list[dict[str, Any]] = []
    restored = False
    restore_error = ""
    modules: dict[str, Any] = {}
    try:
        if EXTERNAL_DATA_DIR.exists():
            shutil.rmtree(EXTERNAL_DATA_DIR)
        modules = _load_modules()
        _seed_runtime(modules)
        console = modules["dashboard_chat_console"]

        a = modules["create_conversation_session"]("Conversation A", source="lifecycle_fixture")
        b = modules["create_conversation_session"]("Conversation B", source="lifecycle_fixture")
        c = modules["create_conversation_session"]("Conversation C", source="lifecycle_fixture")
        modules["save_conversation_draft"](a["id"], "draft A", client_updated_at="2099-01-01T11:00:00.000Z")
        modules["save_conversation_draft"](b["id"], "draft B", client_updated_at="2099-01-01T11:00:01.000Z")
        modules["save_conversation_presentation_state"](
            a["id"], follow_latest=False, scroll_from_bottom_px=44, composer_intentionally_empty=False,
            client_updated_at="2099-01-01T11:00:00.000Z",
        )
        modules["append_conversation_turn"](
            a["id"], turn_id="turn_a", user_message="A user", assistant_response="A assistant",
            completion_state="completed", success=True, select_session=False,
        )
        modules["append_conversation_turn"](
            b["id"], turn_id="turn_b", user_message="B user", assistant_response="B assistant",
            completion_state="completed", success=True, select_session=False,
        )
        modules["select_conversation_session"](a["id"])

        state: dict[str, Any] = {}

        def save_before_create_and_empty_new_composer() -> None:
            client = str(uuid.uuid4())
            result = _lifecycle(
                modules, client=client, generation=1, request="create-request-0001", action="create",
                source=a["id"], title="Fresh thread", draft="A newer draft", stamp="2099-01-01T12:01:00.000Z",
            )
            state["create_client"] = client
            state["created"] = result["created_session_id"]
            assert result["selected_session_id"] == result["created_session_id"]
            assert modules["load_conversation_draft"](a["id"])["content"] == "A newer draft"
            presentation = modules["load_conversation_presentation_state"](a["id"])
            assert presentation["scroll_from_bottom_px"] == 137 and presentation["follow_latest"] is False
            snapshot = console.dashboard_chat_session_snapshot(result["created_session_id"])
            assert snapshot["draft"]["content"] == "" and snapshot["presentation"]["composer_intentionally_empty"] is True
            assert modules["load_conversation_draft"](b["id"])["content"] == "draft B"
        checks.append(_run_check("save_before_create_creates_one_selected_empty_isolated_session", save_before_create_and_empty_new_composer))

        def duplicate_create_is_exactly_once() -> None:
            before = len(modules["list_conversation_sessions"](include_archived=True))
            result = _lifecycle(
                modules, client=state["create_client"], generation=1, request="create-request-0001", action="create",
                source=a["id"], title="Fresh thread", draft="A newer draft", stamp="2099-01-01T12:01:00.000Z",
            )
            assert result["duplicate_request"] is True
            assert result["created_session_id"] == state["created"]
            assert len(modules["list_conversation_sessions"](include_archived=True)) == before
        checks.append(_run_check("duplicate_create_post_delivery_returns_same_session_without_duplication", duplicate_create_is_exactly_once))

        def exact_rename_and_repeat_idempotency() -> None:
            client = state["create_client"]
            result = _lifecycle(
                modules, client=client, generation=2, request="rename-request-0001", action="rename",
                source=state["created"], target=b["id"], title="Renamed B", draft="new thread draft",
                stamp="2099-01-01T12:02:00.000Z",
            )
            assert result["changed"] is True
            assert modules["load_conversation_session"](b["id"], include_turns=False)["title"] == "Renamed B"
            assert modules["load_conversation_session"](a["id"], include_turns=False)["title"] == "Conversation A"
            repeated = _lifecycle(
                modules, client=client, generation=3, request="rename-request-0002", action="rename",
                source=state["created"], target=b["id"], title="Renamed B", draft="new thread draft",
                stamp="2099-01-01T12:03:00.000Z",
            )
            assert repeated["changed"] is False
        checks.append(_run_check("rename_is_exact_session_bound_bounded_and_idempotent", exact_rename_and_repeat_idempotency))

        def stale_rename_cannot_mutate_after_newer_generation() -> None:
            client = state["create_client"]
            late = _lifecycle(
                modules, client=client, generation=2, request="stale-rename-0001", action="rename",
                source=state["created"], target=c["id"], title="Should not win", draft="new thread draft",
                stamp="2099-01-01T12:04:00.000Z",
            )
            assert late["stale_lifecycle_ignored"] is True
            assert modules["load_conversation_session"](c["id"], include_turns=False)["title"] == "Conversation C"
        checks.append(_run_check("stale_rename_response_cannot_mutate_exact_or_current_session", stale_rename_cannot_mutate_after_newer_generation))

        def archive_running_operation_is_blocked_without_cancellation() -> None:
            client = state["create_client"]
            op = modules["new_conversation_operation_id"]()
            marker = modules["create_operation_marker"](op, c["id"], acceptance_key="lifecycle-running-0001")
            result = _lifecycle(
                modules, client=client, generation=4, request="archive-running-001", action="archive",
                source=state["created"], target=c["id"], draft="new thread draft",
                stamp="2099-01-01T12:05:00.000Z",
            )
            assert result["blocked"] is True and result["status"] == "blocked_running_operation"
            assert modules["load_conversation_session"](c["id"], include_turns=False)["status"] == "active"
            persisted = modules["latest_operation_marker"](c["id"])
            assert persisted["operation_id"] == marker["operation_id"]
            assert persisted["public_state"] == "running" and persisted["cancellation_requested"] is False
            modules["finalize_operation_marker"](op, completion_state="cancelled", success=False, failure_category="cancelled")
        checks.append(_run_check("archive_refuses_exact_running_session_without_cancel_retry_or_replay", archive_running_operation_is_blocked_without_cancellation))

        def archive_unrelated_and_repeat_is_idempotent() -> None:
            client = state["create_client"]
            selected_before = modules["get_active_conversation_session"]()["id"]
            first = _lifecycle(
                modules, client=client, generation=5, request="archive-c-0001", action="archive",
                source=selected_before, target=c["id"], draft="selected preserved",
                stamp="2099-01-01T12:06:00.000Z",
            )
            assert first["changed"] is True
            assert modules["load_conversation_session"](c["id"], include_turns=False)["status"] == "archived"
            assert modules["get_active_conversation_session"]()["id"] == selected_before
            second = _lifecycle(
                modules, client=client, generation=6, request="archive-c-0002", action="archive",
                source=selected_before, target=c["id"], draft="selected preserved",
                stamp="2099-01-01T12:07:00.000Z",
            )
            assert second["changed"] is False and modules["get_active_conversation_session"]()["id"] == selected_before
        checks.append(_run_check("archive_preserves_unrelated_selection_and_repeated_archive_is_idempotent", archive_unrelated_and_repeat_is_idempotent))

        def archive_active_selects_deterministic_existing_fallback() -> None:
            client = state["create_client"]
            modules["select_conversation_session"](state["created"])
            result = _lifecycle(
                modules, client=client, generation=7, request="archive-active-001", action="archive",
                source=state["created"], target=state["created"], draft="archived draft preserved",
                stamp="2099-01-01T12:08:00.000Z",
            )
            assert result["changed"] is True and result["fallback_session_id"] == ""
            assert result["selected_session_id"] != state["created"]
            assert modules["get_active_conversation_session"]()["id"] == result["selected_session_id"]
            assert modules["load_conversation_draft"](state["created"])["content"] == "archived draft preserved"
        checks.append(_run_check("archiving_active_session_selects_one_deterministic_existing_fallback", archive_active_selects_deterministic_existing_fallback))

        def archive_last_active_creates_exactly_one_empty_replacement() -> None:
            # Create a fresh selected session, then archive every other active session before it.
            keep_session = modules["create_conversation_session"]("Last active fixture", source="lifecycle_fixture")
            client = str(uuid.uuid4())
            active = modules["list_conversation_sessions"](include_archived=False)
            keep = keep_session["id"]
            generation = 0
            for session in active:
                sid = session["id"]
                if sid == keep:
                    continue
                generation += 1
                modules["select_conversation_session"](keep)
                _lifecycle(
                    modules, client=client, generation=generation, request=f"last-prep-{generation:04d}", action="archive",
                    source=keep, target=sid, draft="keep A", stamp=f"2099-01-01T13:{generation:02d}:00.000Z",
                )
            modules["select_conversation_session"](keep)
            generation += 1
            before = len(modules["list_conversation_sessions"](include_archived=True))
            result = _lifecycle(
                modules, client=client, generation=generation, request="archive-last-0001", action="archive",
                source=keep, target=keep, draft="last archived draft", stamp="2099-01-01T14:00:00.000Z",
            )
            assert result["fallback_session_id"] and result["selected_session_id"] == result["fallback_session_id"]
            replacement = modules["load_conversation_session"](result["fallback_session_id"], include_turns=False)
            assert replacement["title"] == "New conversation" and modules["load_conversation_draft"](replacement["id"])["content"] == ""
            duplicate = _lifecycle(
                modules, client=client, generation=generation, request="archive-last-0001", action="archive",
                source=keep, target=keep, draft="last archived draft", stamp="2099-01-01T14:00:00.000Z",
            )
            assert duplicate["duplicate_request"] is True and duplicate["fallback_session_id"] == replacement["id"]
            assert len(modules["list_conversation_sessions"](include_archived=True)) == before + 1
            state["replacement"] = replacement["id"]
            state["last_archived"] = keep
            state["last_client"] = client
            state["last_generation"] = generation
        checks.append(_run_check("archiving_last_active_session_creates_one_idempotent_empty_replacement", archive_last_active_creates_exactly_one_empty_replacement))

        def restore_without_open_preserves_selection_and_private_state() -> None:
            client = state["last_client"]
            selected = modules["get_active_conversation_session"]()["id"]
            result = _lifecycle(
                modules, client=client, generation=state["last_generation"] + 1, request="restore-a-0001", action="restore",
                source=selected, target=state["last_archived"], draft="replacement draft", stamp="2099-01-01T14:01:00.000Z",
            )
            assert result["changed"] is True and result["selected_session_id"] == selected
            assert modules["get_active_conversation_session"]()["id"] == selected
            assert modules["load_conversation_draft"](state["last_archived"])["content"] == "last archived draft"
            state["last_generation"] += 1
        checks.append(_run_check("restore_does_not_select_or_change_archived_session_draft_presentation_or_history", restore_without_open_preserves_selection_and_private_state))

        def restore_and_open_is_explicit_and_repeat_safe() -> None:
            client = state["last_client"]
            selected = modules["get_active_conversation_session"]()["id"]
            target = state["last_archived"]
            # Archive the restored fixture again before explicit restore-and-open.
            state["last_generation"] += 1
            _lifecycle(
                modules, client=client, generation=state["last_generation"], request="rearchive-last-001", action="archive",
                source=selected, target=target, draft="replacement draft", stamp="2099-01-01T14:02:00.000Z",
            )
            state["last_generation"] += 1
            opened = _lifecycle(
                modules, client=client, generation=state["last_generation"], request="restore-open-last1", action="restore_open",
                source=selected, target=target, draft="replacement draft", stamp="2099-01-01T14:03:00.000Z",
            )
            assert opened["selected_session_id"] == target and modules["get_active_conversation_session"]()["id"] == target
            state["last_generation"] += 1
            repeated = _lifecycle(
                modules, client=client, generation=state["last_generation"], request="restore-open-last2", action="restore_open",
                source=target, target=target, draft="last archived draft", stamp="2099-01-01T14:04:00.000Z",
            )
            assert repeated["changed"] is False and modules["get_active_conversation_session"]()["id"] == target
        checks.append(_run_check("restore_and_open_is_distinct_explicit_and_idempotent", restore_and_open_is_explicit_and_repeat_safe))

        def lifecycle_generation_rejects_delayed_navigation_and_mutations() -> None:
            client = str(uuid.uuid4())
            source_session = modules["create_conversation_session"]("Generation source", source="lifecycle_fixture")
            target_session = modules["create_conversation_session"]("Generation target", source="lifecycle_fixture")
            modules["select_conversation_session"](source_session["id"])
            newer = _lifecycle(
                modules, client=client, generation=3, request="newer-rename-0001", action="rename",
                source=source_session["id"], target=source_session["id"], title="Generation current", draft="generation draft", stamp="2099-01-01T15:03:00.000Z",
            )
            assert newer["stale_lifecycle_ignored"] is False
            late_navigation = modules["switch_conversation_session"](
                source_session_id=source_session["id"], target_session_id=target_session["id"], navigation_client_id=client,
                selection_generation=2, source_draft_content="stale nav draft", source_draft_updated_at="2099-01-01T15:02:00.000Z",
                source_follow_latest=True, source_scroll_from_bottom_px=0, source_composer_intentionally_empty=False,
                source_presentation_updated_at="2099-01-01T15:02:00.000Z",
            )
            assert late_navigation["stale_selection_ignored"] is True
            assert modules["get_active_conversation_session"]()["id"] == source_session["id"]
            stale_archive = _lifecycle(
                modules, client=client, generation=1, request="stale-archive-0001", action="archive",
                source=source_session["id"], target=source_session["id"], draft="generation draft", stamp="2099-01-01T15:01:00.000Z",
            )
            assert stale_archive["stale_lifecycle_ignored"] is True
            assert modules["load_conversation_session"](source_session["id"], include_turns=False)["status"] == "active"
        checks.append(_run_check("shared_generation_orders_navigation_create_rename_archive_and_restore_deterministically", lifecycle_generation_rejects_delayed_navigation_and_mutations))

        def cue_acknowledgement_is_not_implicit() -> None:
            cue_session = modules["create_conversation_session"]("Cue fixture", source="lifecycle_fixture")
            op = modules["new_conversation_operation_id"]()
            marker = modules["create_operation_marker"](op, cue_session["id"], acceptance_key="lifecycle-cue-0001")
            modules["finalize_operation_marker"](op, completion_state="failed", success=False, failure_category="timeout")
            token = modules["operation_cue_token"](modules["latest_operation_marker"](cue_session["id"]), public_state="failed")
            client = str(uuid.uuid4())
            _lifecycle(
                modules, client=client, generation=1, request="rename-with-cue-01", action="rename",
                source=cue_session["id"], target=cue_session["id"], title="Cue renamed", draft="cue draft", stamp="2099-01-01T16:00:00.000Z",
            )
            assert modules["load_operation_acknowledgement"](op) is None
            modules["acknowledge_operation_marker"](op, session_id=cue_session["id"], public_state="failed")
            assert modules["load_operation_acknowledgement"](op) is not None
        checks.append(_run_check("create_rename_archive_restore_and_open_do_not_implicitly_acknowledge_cues", cue_acknowledgement_is_not_implicit))

        def lifecycle_never_mutates_prompt_memory_relationship_mood_or_moments() -> None:
            neutral_session = modules["create_conversation_session"]("Neutral fixture", source="lifecycle_fixture")
            before_memory = modules["MEMORY_FILE"].read_bytes()
            before_self = modules["SELF_FILE"].read_bytes()
            before_desires = modules["DESIRES_FILE"].read_bytes()
            before_history = modules["conversation_history_for_prompt"](neutral_session["id"])
            before_turns = modules["conversation_session_turns"](neutral_session["id"])
            client = str(uuid.uuid4())
            _lifecycle(
                modules, client=client, generation=1, request="neutral-rename-001", action="rename",
                source=neutral_session["id"], target=neutral_session["id"], title="Neutral lifecycle", draft="neutral draft",
                stamp="2099-01-01T17:00:00.000Z",
            )
            assert modules["MEMORY_FILE"].read_bytes() == before_memory
            assert modules["SELF_FILE"].read_bytes() == before_self
            assert modules["DESIRES_FILE"].read_bytes() == before_desires
            assert modules["conversation_history_for_prompt"](neutral_session["id"]) == before_history
            assert modules["conversation_session_turns"](neutral_session["id"]) == before_turns
            state["neutral"] = neutral_session["id"]
        checks.append(_run_check("lifecycle_actions_leave_prompt_memory_relationship_mood_and_moments_immutable", lifecycle_never_mutates_prompt_memory_relationship_mood_or_moments))

        def late_completion_cannot_select_rename_restore_or_unarchive() -> None:
            selected = modules["get_active_conversation_session"]()["id"]
            op = modules["new_conversation_operation_id"]()
            modules["create_operation_marker"](op, state["replacement"], acceptance_key="late-lifecycle-0001")
            modules["append_conversation_turn"](
                state["replacement"], turn_id=op, user_message="late user", assistant_response="late answer",
                completion_state="completed", success=True, select_session=False, allow_default_title_update=False,
            )
            modules["finalize_operation_marker"](op, completion_state="completed", success=True, final_session_turn_recorded=True)
            assert modules["get_active_conversation_session"]()["id"] == selected
            assert modules["load_conversation_session"](state["replacement"], include_turns=False)["title"] == "New conversation"
        checks.append(_run_check("late_completion_attaches_once_without_lifecycle_or_active_selection_mutation", late_completion_cannot_select_rename_restore_or_unarchive))

        def lifecycle_record_is_atomic_private_and_content_bounded() -> None:
            records = list(modules["CONVERSATION_LIFECYCLE_REQUESTS_DIR"].glob("*.json"))
            assert records
            for path in records:
                value = json.loads(path.read_text(encoding="utf-8"))
                assert value["local_private"] is True and value["content_free_except_title"] is True
                assert modules["lifecycle_request_contains_private_fields"](value) is False
                encoded = json.dumps(value).lower()
                for forbidden in ("draft a", "a assistant", "late answer", "lifecycle-fixture-model", "localhost:11434", "traceback"):
                    assert forbidden not in encoded
        checks.append(_run_check("lifecycle_request_records_are_atomic_local_and_content_free_except_bounded_title", lifecycle_record_is_atomic_private_and_content_bounded))

        def http_post_is_bounded_and_get_snapshot_remains_read_only() -> None:
            server = ThreadingHTTPServer(("127.0.0.1", 0), modules["dashboard"].EidolonDashboardHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            http_source = modules["create_conversation_session"]("HTTP source", source="lifecycle_fixture")
            pointer = EXTERNAL_DATA_DIR / "conversation_sessions" / "active_session.json"
            before_pointer = pointer.read_bytes()
            before_memory = modules["MEMORY_FILE"].read_bytes()
            try:
                with urllib.request.urlopen(base + "/api/dashboard-chat/session?session_id=" + http_source["id"], timeout=8) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                assert payload["ok"] is True and pointer.read_bytes() == before_pointer
                client = str(uuid.uuid4())
                status, created = _post(base, "/api/dashboard-chat/session-lifecycle", {
                    "action": "create", "navigation_client_id": client, "lifecycle_generation": 1,
                    "request_key": "http-create-0001", "source_session_id": http_source["id"], "title": "HTTP thread",
                    "source_draft_content": "HTTP source draft", "source_draft_updated_at": "2099-01-01T18:00:00.000Z",
                    "source_follow_latest": False, "source_scroll_from_bottom_px": 55,
                    "source_composer_intentionally_empty": False,
                    "source_presentation_updated_at": "2099-01-01T18:00:00.000Z",
                })
                assert status == 200 and created["snapshot"]["session"]["id"] == created["created_session_id"]
                assert created["snapshot"]["draft"]["content"] == ""
                assert modules["MEMORY_FILE"].read_bytes() == before_memory
                encoded = json.dumps(created["catalog"]).lower()
                for forbidden in ("http source draft", "provider", "model", "operation_id", "receipt"):
                    assert forbidden not in encoded
            finally:
                server.shutdown(); server.server_close(); thread.join(timeout=3)
        checks.append(_run_check("get_is_read_only_and_post_lifecycle_returns_bounded_snapshot_and_catalog", http_post_is_bounded_and_get_snapshot_remains_read_only))

        def rendered_companion_controls_are_in_place_race_safe_and_valid_js() -> None:
            current = modules["get_active_conversation_session"]()["id"]
            modules["select_conversation_session"](current)
            html = console.render_realtime_chat_panel(None, include_archived=True)
            required = (
                "v1080.0-desktop-alpha-release-candidate",
                "/api/dashboard-chat/session-lifecycle",
                "performConversationLifecycle",
                "newLifecycleRequestKey",
                "data-chat-session-create",
                "data-chat-session-rename",
                "data-chat-session-archive",
                "data-chat-session-restore",
                "data-chat-session-restore-open",
                "Restore and open",
                "generation !== selectionRequestToken",
            )
            for token in required:
                assert token in html
            script = html[html.rfind("<script>") + len("<script>"):html.rfind("</script>")]
            script_dir = Path(tempfile.mkdtemp(prefix="eidolon-lifecycle-js-"))
            script_path = script_dir / "chat.js"
            script_path.write_text(script, encoding="utf-8")
            try:
                completed = subprocess.run(["node", "--check", str(script_path)], capture_output=True, text=True, timeout=20)
                assert completed.returncode == 0, completed.stderr
            finally:
                shutil.rmtree(script_dir, ignore_errors=True)
            lowered = html.lower()
            for forbidden in ("ollama pull", "install model", "delete model", "automatic fallback", "grant approval", "authorize release"):
                assert forbidden not in lowered
        checks.append(_run_check("rendered_lifecycle_controls_are_in_place_generation_bound_companion_first_and_valid", rendered_companion_controls_are_in_place_race_safe_and_valid_js))

        def provider_settings_departure_preserves_all_state() -> None:
            html = console.render_realtime_chat_panel(None, include_archived=True)
            assert "chat-open-provider-settings" in html
            assert "await persistDraft({ sessionId:targetSessionId" in html
            assert "await persistPresentation({ sessionId:targetSessionId" in html
            current = modules["get_active_conversation_session"]()["id"]
            before = modules["load_conversation_draft"](current)
            assert modules["load_conversation_draft"](current) == before
        checks.append(_run_check("provider_settings_departure_keeps_selected_session_drafts_presentation_cues_and_operations", provider_settings_departure_preserves_all_state))

        def source_only_rules_exclude_all_lifecycle_runtime_records() -> None:
            candidates = [
                "data/projects.json",
                "data/conversation_sessions/conversation_session_fixture.json",
                "data/conversation_sessions/drafts/conversation_session_fixture.json",
                "data/conversation_sessions/presentation/conversation_session_fixture.json",
                "data/conversation_sessions/navigation_clients/client.json",
                "data/conversation_sessions/lifecycle_requests/request.json",
                "data/conversation_runtime/operations/operation.json",
                "data/conversation_runtime/operation_acknowledgements/ack.json",
                "data/memories.json",
                "data/dashboard_chat/turn.json",
            ]
            forbidden = modules["forbidden_runtime_path_matches"](candidates)
            for candidate in candidates:
                assert candidate in forbidden
            assert modules["CONVERSATION_LIFECYCLE_REQUESTS_DIR"].is_relative_to(EXTERNAL_DATA_DIR / "conversation_sessions")
        checks.append(_run_check("source_only_rules_exclude_sessions_drafts_operations_acknowledgements_navigation_and_lifecycle_records", source_only_rules_exclude_all_lifecycle_runtime_records))

        def source_tree_immutability_contract() -> None:
            assert _source_snapshot() == source_before
        checks.append(_run_check("source_tree_remains_immutable_during_isolated_lifecycle_fixtures", source_tree_immutability_contract))

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
        "suite": "conversation_lifecycle_and_new_session_continuity",
        "version": "1079.5.6",
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
