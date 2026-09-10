from __future__ import annotations

"""Deterministic v1079.5 daily re-entry and unfinished-conversation cue fixtures.

The suite uses isolated/restored runtime data and synthetic operation markers. It
never contacts a provider, retries generation, changes a model, grants approval,
authorizes a release, or expands autonomy.
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from copy import deepcopy
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
sys.path.insert(0, str(AGENT))
EXTERNAL_DATA_DIR = Path(os.environ.get("EIDOLON_DATA_DIR") or (ROOT / "data")).resolve()


def _snapshot_tree(root: Path) -> Path:
    backup = Path(tempfile.mkdtemp(prefix="eidolon-v1079-5-reentry-backup-"))
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
    import conversation_operations
    import dashboard
    import dashboard_chat_console
    from conversation_operations import (
        CONVERSATION_OPERATION_ACKNOWLEDGEMENT_DIR,
        CONVERSATION_OPERATION_DIR,
        create_operation_marker,
        finalize_operation_marker,
        load_operation_acknowledgement,
        load_operation_marker,
        mark_operation_client_disconnected,
        new_conversation_operation_id,
        operation_marker_contains_private_fields,
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
        json.dumps([
            {"id": "memory_fixture", "type": "relationship_fact", "content": "Explicit fixture memory", "importance": "medium"}
        ]),
        encoding="utf-8",
    )
    settings = deepcopy(modules["DEFAULT_SETTINGS"])
    settings.update({
        "local_model_provider": "ollama",
        "local_model": "reentry-fixture-model",
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


def _read_tree_bytes(paths: list[Path]) -> dict[str, bytes | None]:
    return {str(path): path.read_bytes() if path.exists() else None for path in paths}


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
        operations = modules["conversation_operations"]
        state: dict[str, Any] = {"acceptance_counter": 0, "active_jobs": []}

        def make_operation(
            session_id: str,
            state_name: str,
            *,
            accepted_at: str,
            disconnected: bool = False,
            final_turn: bool = False,
            failure_category: str = "",
            active_running: bool = False,
        ) -> dict[str, Any]:
            state["acceptance_counter"] += 1
            operation_id = modules["new_conversation_operation_id"]()
            marker = modules["create_operation_marker"](
                operation_id,
                session_id,
                accepted_at=accepted_at,
                acceptance_key=f"cue-fixture-{state['acceptance_counter']:08d}",
            )
            if disconnected:
                marker = modules["mark_operation_client_disconnected"](operation_id) or marker
            if state_name != "running":
                marker = modules["finalize_operation_marker"](
                    operation_id,
                    completion_state=state_name,
                    success=state_name == "completed",
                    failure_category=failure_category,
                    final_session_turn_recorded=final_turn,
                ) or marker
            elif active_running:
                job = console._DashboardOperationJob(operation_id=operation_id, session_id=session_id, turn_id=operation_id)
                console._DASHBOARD_OPERATION_JOBS[operation_id] = job
                state["active_jobs"].append(operation_id)
            return marker

        def compact_public_cues_are_bounded_and_one_per_session() -> None:
            session = modules["create_conversation_session"]("Bounded cue", source="fixture")
            marker = make_operation(session["id"], "failed", accepted_at="2026-07-16T12:00:00.000Z", failure_category="timeout")
            status = console.dashboard_chat_operation_status(session_id=session["id"])
            cue = status["session_cue"]
            assert cue == {
                "kind": "needs_recovery",
                "label": "Needs recovery",
                "public_state": "failed",
                "acknowledgeable": True,
            }
            encoded = json.dumps(cue).lower()
            for forbidden in (marker["operation_id"].lower(), "acceptance", "provider", "model", "endpoint", "timestamp", "timeout"):
                assert forbidden not in encoded
            assert modules["operation_marker_contains_private_fields"](cue) is False
            state["bounded_session"] = session
            state["bounded_marker"] = marker
        checks.append(_run_check("one_compact_bounded_public_cue_is_derived_per_session", compact_public_cues_are_bounded_and_one_per_session))

        def running_refresh_cue_is_truthful_and_not_acknowledgeable() -> None:
            session = modules["create_conversation_session"]("Running cue", source="fixture")
            marker = make_operation(session["id"], "running", accepted_at="2026-07-16T12:01:00.000Z", active_running=True)
            first = console.dashboard_chat_operation_status(session_id=session["id"])
            second = console.dashboard_chat_operation_status(session_id=session["id"])
            assert first["session_cue"] == second["session_cue"]
            assert first["session_cue"]["label"] == "Still responding"
            assert first["session_cue"]["acknowledgeable"] is False
            rejected = console.acknowledge_dashboard_session_operation_cue(session["id"], operation_id=marker["operation_id"])
            assert rejected["status"] == "not_acknowledgeable"
            assert modules["load_operation_acknowledgement"](marker["operation_id"]) is None
            assert modules["load_operation_marker"](marker["operation_id"])["public_state"] == "running"
            state["running_session"] = session
        checks.append(_run_check("refresh_preserves_one_still_responding_cue_without_acknowledging_or_cancelling", running_refresh_cue_is_truthful_and_not_acknowledgeable))

        def completion_cue_requires_late_or_detached_completion() -> None:
            normal = modules["create_conversation_session"]("Normal complete", source="fixture")
            late = modules["create_conversation_session"]("Late complete", source="fixture")
            make_operation(normal["id"], "completed", accepted_at="2026-07-16T12:02:00.000Z", final_turn=True)
            late_marker = make_operation(late["id"], "completed", accepted_at="2026-07-16T12:03:00.000Z", disconnected=True, final_turn=True)
            assert console.dashboard_session_operation_cue(normal["id"]) is None
            cue = console.dashboard_session_operation_cue(late["id"])
            assert cue and cue["kind"] == "reply_ready" and cue["label"] == "Reply ready"
            assert modules["load_operation_marker"](late_marker["operation_id"])["reconciled_late"] is True
            state["late_session"] = late
            state["late_marker"] = late_marker
        checks.append(_run_check("reply_ready_is_reserved_for_completed_while_away_operations", completion_cue_requires_late_or_detached_completion))

        def failed_cancelled_and_uncertain_cues_are_distinct() -> None:
            failed = modules["create_conversation_session"]("Failed cue", source="fixture")
            cancelled = modules["create_conversation_session"]("Cancelled cue", source="fixture")
            uncertain = modules["create_conversation_session"]("Uncertain cue", source="fixture")
            make_operation(failed["id"], "failed", accepted_at="2026-07-16T12:04:00.000Z", failure_category="provider_unavailable")
            make_operation(cancelled["id"], "cancelled", accepted_at="2026-07-16T12:05:00.000Z", failure_category="cancelled")
            uncertain_marker = make_operation(uncertain["id"], "running", accepted_at="2026-07-16T12:06:00.000Z")
            assert console.dashboard_session_operation_cue(failed["id"])["kind"] == "needs_recovery"
            assert console.dashboard_session_operation_cue(cancelled["id"])["kind"] == "cancelled"
            uncertain_cue = console.dashboard_session_operation_cue(uncertain["id"])
            assert uncertain_cue["kind"] == "completion_uncertain"
            assert modules["load_operation_marker"](uncertain_marker["operation_id"])["public_state"] == "running"
            state.update({"failed_session": failed, "cancelled_session": cancelled, "uncertain_session": uncertain})
        checks.append(_run_check("failed_cancelled_and_restart_uncertain_states_have_distinct_calm_cues", failed_cancelled_and_uncertain_cues_are_distinct))

        def newest_operation_precedence_is_deterministic() -> None:
            session = modules["create_conversation_session"]("Newest wins", source="fixture")
            old = make_operation(session["id"], "failed", accepted_at="2026-07-16T12:07:00.000Z", failure_category="timeout")
            newer = make_operation(session["id"], "running", accepted_at="2026-07-16T12:08:00.000Z", active_running=True)
            status = console.dashboard_chat_operation_status(session_id=session["id"])
            assert status["operation"]["operation_id"] == newer["operation_id"]
            assert status["session_cue"]["kind"] == "still_responding"
            token = console.dashboard_session_operation_cue(session["id"], include_token=True)["acknowledgement_token"]
            rejected = console.acknowledge_dashboard_session_operation_cue(session["id"], acknowledgement_token=token)
            assert rejected["status"] == "not_acknowledgeable"
            assert modules["load_operation_acknowledgement"](old["operation_id"]) is None
        checks.append(_run_check("newest_operation_precedence_prevents_older_cues_from_overwriting_newer_truth", newest_operation_precedence_is_deterministic))

        def multi_session_cues_are_isolated() -> None:
            labels = {
                state["running_session"]["id"]: "Still responding",
                state["late_session"]["id"]: "Reply ready",
                state["failed_session"]["id"]: "Needs recovery",
                state["cancelled_session"]["id"]: "Cancelled",
                state["uncertain_session"]["id"]: "Completion uncertain",
            }
            for session_id, label in labels.items():
                assert console.dashboard_session_operation_cue(session_id)["label"] == label
            assert len(set(labels)) == len(labels)
        checks.append(_run_check("session_cues_are_isolated_across_named_conversations", multi_session_cues_are_isolated))

        def repeated_render_and_polling_do_not_duplicate_rows() -> None:
            modules["select_conversation_session"](state["running_session"]["id"])
            first = console.render_realtime_chat_panel(None)
            second = console.render_realtime_chat_panel(None)
            for session_id in (
                state["running_session"]["id"], state["late_session"]["id"],
                state["failed_session"]["id"], state["cancelled_session"]["id"], state["uncertain_session"]["id"],
            ):
                marker = f"data-session-cue-session-id='{session_id}'"
                assert first.count(marker) == 1
                assert second.count(marker) == 1
            source = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
            assert "removeSessionCue(sessionId);" in source
            assert "querySelectorAll('[data-session-cue-session-id]')" in source
            assert "reentryList.appendChild(row);" in source
        checks.append(_run_check("repeated_refresh_and_status_polling_replace_one_cue_instead_of_appending_duplicates", repeated_render_and_polling_do_not_duplicate_rows))

        def explicit_acknowledgement_is_atomic_idempotent_and_preserves_marker_truth() -> None:
            session = state["late_session"]
            marker = state["late_marker"]
            marker_path = modules["CONVERSATION_OPERATION_DIR"] / f"{marker['operation_id']}.json"
            marker_before = marker_path.read_bytes()
            cue = console.dashboard_session_operation_cue(session["id"], include_token=True)
            first = console.acknowledge_dashboard_session_operation_cue(
                session["id"], acknowledgement_token=cue["acknowledgement_token"]
            )
            second = console.acknowledge_dashboard_session_operation_cue(
                session["id"], operation_id=marker["operation_id"]
            )
            assert first["ok"] and first["changed"] is True
            assert second["ok"] and second["status"] == "already_acknowledged" and second["changed"] is False
            assert marker_path.read_bytes() == marker_before
            acknowledgement = modules["load_operation_acknowledgement"](marker["operation_id"])
            assert acknowledgement["acknowledged_public_state"] == "completed"
            assert console.dashboard_session_operation_cue(session["id"]) is None
            assert modules["operation_marker_contains_private_fields"](acknowledgement) is False
        checks.append(_run_check("explicit_post_style_acknowledgement_is_atomic_idempotent_and_never_mutates_operation_truth", explicit_acknowledgement_is_atomic_idempotent_and_preserves_marker_truth))

        def get_status_and_render_are_side_effect_free() -> None:
            session = state["failed_session"]
            marker = console.dashboard_chat_operation_status(session_id=session["id"])["operation"]
            ack_path = modules["CONVERSATION_OPERATION_ACKNOWLEDGEMENT_DIR"] / f"{marker['operation_id']}.json"
            assert not ack_path.exists()
            before = _read_tree_bytes([
                modules["MEMORY_FILE"], modules["SELF_FILE"], modules["DESIRES_FILE"],
                operations.CONVERSATION_OPERATION_DIR / f"{marker['operation_id']}.json",
            ])
            server = ThreadingHTTPServer(("127.0.0.1", 0), modules["dashboard"].EidolonDashboardHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f"http://127.0.0.1:{server.server_port}/api/dashboard-chat/operation?session_id={session['id']}"
                with urllib.request.urlopen(url, timeout=5) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                assert payload["ok"] and payload["session_cue"]["kind"] == "needs_recovery"
                with urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/chat-console", timeout=5) as response:
                    assert response.status == 200
            finally:
                server.shutdown(); server.server_close(); thread.join(timeout=3)
            after = _read_tree_bytes(list(map(Path, before.keys())))
            assert before == after and not ack_path.exists()
        checks.append(_run_check("get_status_and_dashboard_rendering_are_read_only_and_cannot_acknowledge_cues", get_status_and_render_are_side_effect_free))

        def acknowledgement_is_scoped_to_exact_session_and_latest_operation() -> None:
            first_session = state["failed_session"]
            second_session = state["cancelled_session"]
            first_cue = console.dashboard_session_operation_cue(first_session["id"], include_token=True)
            wrong_session = console.acknowledge_dashboard_session_operation_cue(
                second_session["id"], acknowledgement_token=first_cue["acknowledgement_token"]
            )
            assert wrong_session["status"] == "stale"
            first_marker = console.dashboard_chat_operation_status(session_id=first_session["id"])["operation"]
            wrong_operation = console.acknowledge_dashboard_session_operation_cue(
                first_session["id"], operation_id=state["late_marker"]["operation_id"]
            )
            assert wrong_operation["status"] == "stale"
            assert modules["load_operation_acknowledgement"](first_marker["operation_id"]) is None
            assert console.dashboard_session_operation_cue(second_session["id"])["kind"] == "cancelled"
        checks.append(_run_check("acknowledgement_tokens_and_operation_ids_fail_closed_across_sessions_and_newer_operations", acknowledgement_is_scoped_to_exact_session_and_latest_operation))

        def acknowledgement_preserves_transcript_prompt_memory_relationship_mood_and_moments() -> None:
            session = state["failed_session"]
            marker = console.dashboard_chat_operation_status(session_id=session["id"])["operation"]
            modules["append_conversation_turn"](
                session["id"], turn_id=marker["operation_id"], user_message="failed private text",
                assistant_response="partial private text", completion_state="failed", success=False,
                failure_category="provider_unavailable", provider="fixture", model="fixture-model", select_session=False,
            )
            paths = [
                modules["MEMORY_FILE"], modules["SELF_FILE"], modules["DESIRES_FILE"],
                EXTERNAL_DATA_DIR / "conversation_sessions" / f"{session['id']}.json",
            ]
            before = _read_tree_bytes(paths)
            history_before = modules["conversation_history_for_prompt"](session["id"])
            memories_before = modules["load_memories"](limit=100)
            cue = console.dashboard_session_operation_cue(session["id"], include_token=True)
            result = console.acknowledge_dashboard_session_operation_cue(
                session["id"], acknowledgement_token=cue["acknowledgement_token"]
            )
            assert result["ok"]
            assert _read_tree_bytes(paths) == before
            assert modules["conversation_history_for_prompt"](session["id"]) == history_before == []
            assert modules["load_memories"](limit=100) == memories_before
            turn = modules["conversation_session_turns"](session["id"])[-1]
            assert turn["success"] is False and turn["completion_state"] == "failed"
        checks.append(_run_check("acknowledgement_cannot_mutate_transcript_prompt_history_memory_relationship_mood_or_important_moment_state", acknowledgement_preserves_transcript_prompt_memory_relationship_mood_and_moments))

        def drafts_tombstones_and_active_selection_are_preserved() -> None:
            cancelled = state["cancelled_session"]
            unrelated = modules["create_conversation_session"]("Unrelated draft", source="fixture")
            modules["save_conversation_draft"](cancelled["id"], "cancelled session draft", source="fixture")
            modules["save_conversation_draft"](unrelated["id"], "unrelated draft", source="fixture")
            tombstone_session = modules["create_conversation_session"]("Tombstone", source="fixture")
            modules["save_conversation_draft"](tombstone_session["id"], "accepted message", source="fixture")
            tombstone = modules["clear_conversation_draft"](tombstone_session["id"], source="fixture_acceptance")
            modules["select_conversation_session"](unrelated["id"])
            active_before = modules["get_active_conversation_session"](create_if_missing=False)["id"]
            cue = console.dashboard_session_operation_cue(cancelled["id"], include_token=True)
            result = console.acknowledge_dashboard_session_operation_cue(
                cancelled["id"], acknowledgement_token=cue["acknowledgement_token"]
            )
            assert result["ok"]
            assert modules["load_conversation_draft"](cancelled["id"])["content"] == "cancelled session draft"
            assert modules["load_conversation_draft"](unrelated["id"])["content"] == "unrelated draft"
            tombstone_after = modules["load_conversation_draft"](tombstone_session["id"])
            assert tombstone_after["content"] == "" and tombstone_after["cleared_at"] == tombstone["cleared_at"]
            assert modules["get_active_conversation_session"](create_if_missing=False)["id"] == active_before
        checks.append(_run_check("cue_acknowledgement_preserves_every_session_draft_tombstone_and_active_selection", drafts_tombstones_and_active_selection_are_preserved))

        def late_completion_after_switch_keeps_selection_and_updates_only_origin_cue() -> None:
            origin = modules["create_conversation_session"]("Origin late", source="fixture")
            selected = modules["create_conversation_session"]("Selected elsewhere", source="fixture")
            marker = make_operation(origin["id"], "running", accepted_at="2026-07-16T12:20:00.000Z", active_running=True)
            modules["select_conversation_session"](selected["id"])
            modules["mark_operation_client_disconnected"](marker["operation_id"])
            modules["append_conversation_turn"](
                origin["id"], turn_id=marker["operation_id"], user_message="late origin", assistant_response="late reply",
                completion_state="completed", success=True, provider="fixture", model="fixture-model", select_session=False,
            )
            modules["finalize_operation_marker"](
                marker["operation_id"], completion_state="completed", success=True, final_session_turn_recorded=True
            )
            console._DASHBOARD_OPERATION_JOBS[marker["operation_id"]].done = True
            assert modules["get_active_conversation_session"](create_if_missing=False)["id"] == selected["id"]
            assert console.dashboard_session_operation_cue(origin["id"])["kind"] == "reply_ready"
            assert console.dashboard_session_operation_cue(selected["id"]) is None
            assert len([turn for turn in modules["conversation_session_turns"](origin["id"]) if turn["id"] == marker["operation_id"]]) == 1
        checks.append(_run_check("late_completion_after_session_switch_updates_origin_once_without_stealing_selection", late_completion_after_switch_keeps_selection_and_updates_only_origin_cue))

        def rendered_session_cue_surface_is_redacted_and_progressive() -> None:
            modules["select_conversation_session"](state["uncertain_session"]["id"])
            html = console.render_realtime_chat_panel(None)
            start = html.index("<section class='conversation-reentry-panel'")
            end = html.index("</section>", start) + len("</section>")
            panel = html[start:end]
            assert "Still responding" in panel and "Completion uncertain" in panel
            assert "data-session-operation-cue" in panel
            for forbidden in (
                "conversation_2026", "cue-fixture-", "reentry-fixture-model", "ollama", "localhost:11434",
                "runtime_status_unknown_after_restart", "accepted_at", "completed_at", "failure_category",
                "provider", "model", "endpoint", "traceback", "receipt", "partial private text",
            ):
                assert forbidden not in panel
            assert "Reconciliation details" in html and "Generation details" in html
        checks.append(_run_check("session_list_cues_show_only_calm_labels_while_technical_evidence_stays_progressively_disclosed", rendered_session_cue_surface_is_redacted_and_progressive))

        def explicit_post_endpoint_acknowledges_exact_operation_only() -> None:
            session = modules["create_conversation_session"]("HTTP acknowledge", source="fixture")
            marker = make_operation(session["id"], "failed", accepted_at="2026-07-16T12:30:00.000Z", failure_category="timeout")
            server = ThreadingHTTPServer(("127.0.0.1", 0), modules["dashboard"].EidolonDashboardHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                body = json.dumps({"session_id": session["id"], "operation_id": marker["operation_id"]}).encode("utf-8")
                request = urllib.request.Request(
                    f"http://127.0.0.1:{server.server_port}/api/dashboard-chat/operation-acknowledge",
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                assert payload["ok"] and payload["status"] == "acknowledged"
                with urllib.request.urlopen(request, timeout=5) as response:
                    duplicate = json.loads(response.read().decode("utf-8"))
                assert duplicate["ok"] and duplicate["status"] == "already_acknowledged"
                assert console.dashboard_session_operation_cue(session["id"]) is None
            finally:
                server.shutdown(); server.server_close(); thread.join(timeout=3)
        checks.append(_run_check("explicit_post_endpoint_acknowledges_one_exact_operation_and_repeated_posts_are_idempotent", explicit_post_endpoint_acknowledges_exact_operation_only))

        def source_package_rules_exclude_markers_and_acknowledgements() -> None:
            samples = [
                "Eidolon/data/conversation_runtime/operations/conversation_fixture.json",
                "Eidolon/data/conversation_runtime/operation_acknowledgements/conversation_fixture.json",
                "Eidolon/data/conversation_sessions/conversation_fixture.json",
                "Eidolon/data/conversation_sessions/drafts/conversation_fixture.json",
                "Eidolon/data/projects.json",
            ]
            matches = modules["forbidden_runtime_path_matches"](samples)
            assert set(matches) == set(samples)
            source = (AGENT / "package_integrity.py").read_text(encoding="utf-8")
            assert "data/settings.json" in source and "data/workspaces/projects.json" in source
        checks.append(_run_check("source_only_privacy_rules_exclude_operation_markers_acknowledgements_sessions_drafts_and_runtime_projects", source_package_rules_exclude_markers_and_acknowledgements))

        def governance_and_continuity_boundaries_remain_explicit() -> None:
            source = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
            operations_source = (AGENT / "conversation_operations.py").read_text(encoding="utf-8")
            runtime_source = (AGENT / "conversation_runtime.py").read_text(encoding="utf-8")
            assert "GET/render paths never call this" in source
            assert "Only terminal conversation cues may be acknowledged" in operations_source
            assert "local_private" in operations_source and "redacted" in operations_source
            assert "fallback_used: bool = False" in runtime_source
            assert '"model_management_performed": False' in runtime_source
            for token in ("install_model", "pull_model", "delete_model", "authorize_release", "grant_approval"):
                assert token not in operations_source
        checks.append(_run_check("cue_work_adds_no_fallback_model_management_memory_promotion_approval_release_or_autonomy_authority", governance_and_continuity_boundaries_remain_explicit))

    finally:
        try:
            if modules:
                console = modules.get("dashboard_chat_console")
                if console:
                    for operation_id in state.get("active_jobs", []) if 'state' in locals() else []:
                        console._DASHBOARD_OPERATION_JOBS.pop(operation_id, None)
        except Exception:
            pass
        try:
            _restore_tree(EXTERNAL_DATA_DIR, backup)
            restored = True
        except Exception as error:
            restore_error = f"{type(error).__name__}: {error}"

    source_after = _source_snapshot()
    checks.append({
        "name": "runtime_fixture_restoration_and_source_tree_immutability",
        "status": "pass" if restored and source_before == source_after else "fail",
        **({} if restored and source_before == source_after else {
            "error": restore_error or "source tree changed during isolated fixture execution"
        }),
    })
    passed = sum(check.get("status") == "pass" for check in checks)
    report = {
        "version": "1079.5",
        "suite": "daily_reentry_and_unfinished_conversation_cues",
        "ok": passed == len(checks),
        "passed": passed,
        "total": len(checks),
        "checks": checks,
        "native_provider_contacted": False,
        "model_management_performed": False,
        "automatic_retry_performed": False,
        "full_verification_run": False,
        "runtime_data_restored": restored,
    }
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for check in checks:
            print(f"{check['status'].upper()}: {check['name']}" + (f" - {check.get('error')}" if check.get("error") else ""))
        print(f"{passed}/{len(checks)} checks passed")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
