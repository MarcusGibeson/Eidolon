from __future__ import annotations

"""Deterministic daily-use consolidation fixtures for v1079.5.7.

The suite exercises the ordinary companion workflow across drafts, navigation,
lifecycle, detached-operation truth, cues, recovery presentation, keyboard/focus
contracts, continuity boundaries, source immutability, and package privacy. It uses
no native provider and restores the external runtime tree exactly.
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
sys.path.insert(0, str(AGENT))
EXTERNAL_DATA_DIR = Path(os.environ.get("EIDOLON_DATA_DIR") or (ROOT / "data")).resolve()


def _snapshot_tree(root: Path) -> Path:
    backup = Path(tempfile.mkdtemp(prefix="eidolon-daily-polish-backup-"))
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


def _tree_bytes(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def _source_snapshot() -> dict[str, str]:
    result: dict[str, str] = {}
    for path in ROOT.rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        relative = path.relative_to(ROOT).as_posix()
        if relative.startswith((
            "data/conversation_sessions/", "data/conversation_runtime/", "data/dashboard_chat/",
            "data/conversation_navigation/",
        )):
            continue
        result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _load_modules() -> dict[str, Any]:
    import dashboard_chat_console
    from conversation_navigation import (
        perform_conversation_lifecycle,
        save_conversation_presentation_state,
        switch_conversation_session,
    )
    from conversation_operations import (
        create_operation_marker,
        finalize_operation_marker,
        mark_operation_client_disconnected,
        new_client_acceptance_key,
        new_conversation_operation_id,
        request_operation_cancellation,
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
    from package_integrity import forbidden_runtime_path_matches, iter_source_tree_entries
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
    modules["SELF_FILE"].write_text(json.dumps({
        "name": "Eidolon", "mood": "steady", "energy": 0.7,
        "focus": "daily companion", "active_goals": [],
    }, indent=2), encoding="utf-8")
    modules["DESIRES_FILE"].write_text(json.dumps({"connection": 0.8}, indent=2), encoding="utf-8")
    modules["MEMORY_FILE"].write_text(json.dumps([
        {"id": "explicit_fixture", "type": "relationship_fact", "content": "Explicit fixture memory", "importance": "medium"}
    ], indent=2), encoding="utf-8")
    settings = deepcopy(modules["DEFAULT_SETTINGS"])
    settings.update({
        "local_model_provider": "ollama",
        "local_model": "daily-polish-fixture-model",
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
        source_scroll_from_bottom_px=88,
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
    try:
        if EXTERNAL_DATA_DIR.exists():
            shutil.rmtree(EXTERNAL_DATA_DIR)
        modules = _load_modules()
        _seed_runtime(modules)
        console = modules["dashboard_chat_console"]

        a = modules["create_conversation_session"]("Morning", source="daily_polish_fixture")
        b = modules["create_conversation_session"]("Project", source="daily_polish_fixture")
        c = modules["create_conversation_session"]("Quiet notes", source="daily_polish_fixture")
        modules["save_conversation_draft"](a["id"], "continue morning draft", client_updated_at="2099-01-01T10:00:00.000Z")
        modules["save_conversation_draft"](b["id"], "project draft", client_updated_at="2099-01-01T10:00:01.000Z")
        modules["save_conversation_presentation_state"](
            a["id"], follow_latest=False, scroll_from_bottom_px=54,
            composer_intentionally_empty=False, client_updated_at="2099-01-01T10:00:00.000Z",
        )
        modules["select_conversation_session"](a["id"])
        state: dict[str, Any] = {}

        def ordinary_surface_is_companion_first() -> None:
            html = console.render_realtime_chat_panel(None)
            state["html"] = html
            assert "chat-primary-conversation-bar" in html
            assert "aria-label='Conversation navigation'" in html
            assert "<button type='button' id='chat-session-open-button' aria-label='Open selected conversation'>Open</button>" in html
            assert "aria-label='Create a new conversation'" in html
            assert "More conversation options" in html
            assert "Generation details" in html and html.index("realtime-chat-log") < html.index("Generation details")
            assert "chat-provider-pill" not in html
        checks.append(_run_check("ordinary_chat_keeps_one_visible_primary_navigation_surface", ordinary_surface_is_companion_first))

        def status_vocabulary_is_consistent_and_redacted() -> None:
            html = state["html"]
            for token in (
                "Ready", "Saving draft", "Switching conversation", "Creating conversation",
                "Still responding", "Needs recovery", "Cancelled safely", "Completion uncertain", "Offline mode",
                "Archiving conversation", "Restoring conversation",
            ):
                assert token in html
            header = html[html.index("companion-status-card"):html.index("chat-primary-conversation-bar")]
            for forbidden in ("operation_id", "acceptance_key", "http://localhost", "traceback", "receipt_path"):
                assert forbidden not in header.lower()
        checks.append(_run_check("companion_status_vocabulary_is_consistent_and_public", status_vocabulary_is_consistent_and_redacted))

        def keyboard_focus_and_duplicate_guards_are_explicit() -> None:
            html = state["html"]
            assert "if (event.key !== 'Enter') return;" in html
            assert "if (event.shiftKey)" in html
            assert "messageBox.addEventListener('beforeinput'" in html
            assert "enterkeyhint='send'" in html
            assert "requestComposerSubmitOnce(event)" in html and "keyboardSubmitLatch" in html
            assert "compositionActive || event.isComposing || event.keyCode === 229" in html
            assert "event.key !== 'Escape'" in html and "closeTemporaryCompanionSurfaces" in html
            escape_block = html[html.index("document.addEventListener('keydown'"):html.index("if (sessionSwitchForm)")]
            assert "cancel" not in escape_block.lower()
            assert "companionActionLocks" in html and "beginCompanionAction" in html
            assert "recovery:" in html and "cancel:" in html and "lifecycle:" in html and "acknowledge:" in html
            assert "focusComposer()" in html
        checks.append(_run_check("keyboard_focus_and_duplicate_action_guards_are_bounded", keyboard_focus_and_duplicate_guards_are_explicit))

        def narrow_layout_has_no_forced_horizontal_controls() -> None:
            styles = console.COMPANION_CHAT_STYLES
            assert "@media (max-width:620px)" in styles
            assert ".chat-primary-conversation-bar form" in styles and "width:100%" in styles
            assert ".chat-composer-actions { display:grid" in styles
            assert "overflow-wrap:anywhere" in styles
            assert "flex-wrap:wrap" in styles
        checks.append(_run_check("compact_layout_wraps_navigation_lifecycle_and_recovery_controls", narrow_layout_has_no_forced_horizontal_controls))

        def resume_existing_draft_and_presentation() -> None:
            snapshot = console.dashboard_chat_session_snapshot(a["id"])
            assert snapshot["draft"]["content"] == "continue morning draft"
            assert snapshot["presentation"]["follow_latest"] is False
            assert snapshot["presentation"]["scroll_from_bottom_px"] == 54
            assert snapshot["session"]["id"] == a["id"]
        checks.append(_run_check("open_and_resume_restores_existing_draft_and_presentation", resume_existing_draft_and_presentation))

        def rapid_switching_preserves_independent_drafts() -> None:
            client = str(uuid.uuid4())
            first = modules["switch_conversation_session"](
                source_session_id=a["id"], target_session_id=b["id"], navigation_client_id=client,
                selection_generation=1, source_draft_content="morning newer", source_draft_updated_at="2099-01-01T11:00:00.000Z",
                source_follow_latest=False, source_scroll_from_bottom_px=21, source_composer_intentionally_empty=False,
                source_presentation_updated_at="2099-01-01T11:00:00.000Z",
            )
            second = modules["switch_conversation_session"](
                source_session_id=b["id"], target_session_id=a["id"], navigation_client_id=client,
                selection_generation=2, source_draft_content="project newer", source_draft_updated_at="2099-01-01T11:00:01.000Z",
                source_follow_latest=True, source_scroll_from_bottom_px=0, source_composer_intentionally_empty=False,
                source_presentation_updated_at="2099-01-01T11:00:01.000Z",
            )
            stale = modules["switch_conversation_session"](
                source_session_id=a["id"], target_session_id=c["id"], navigation_client_id=client,
                selection_generation=1, source_draft_content="stale but session-bound", source_draft_updated_at="2099-01-01T10:30:00.000Z",
                source_follow_latest=True, source_scroll_from_bottom_px=0, source_composer_intentionally_empty=False,
                source_presentation_updated_at="2099-01-01T10:30:00.000Z",
            )
            assert first["selected_session_id"] == b["id"] and second["selected_session_id"] == a["id"]
            assert stale["stale_selection_ignored"] is True
            assert modules["get_active_conversation_session"]()["id"] == a["id"]
            assert modules["load_conversation_draft"](a["id"])["content"] == "morning newer"
            assert modules["load_conversation_draft"](b["id"])["content"] == "project newer"
            state.update({"client": client, "generation": 2})
        checks.append(_run_check("rapid_switching_keeps_exact_session_drafts_and_latest_selection", rapid_switching_preserves_independent_drafts))

        def create_is_exactly_once_and_empty() -> None:
            client = state["client"]
            result = _lifecycle(
                modules, client=client, generation=3, request="daily-create-0001", action="create",
                source=a["id"], draft="morning final", stamp="2099-01-01T11:01:00.000Z",
            )
            duplicate = _lifecycle(
                modules, client=client, generation=3, request="daily-create-0001", action="create",
                source=a["id"], draft="morning final", stamp="2099-01-01T11:01:00.000Z",
            )
            created = result["created_session_id"]
            assert created and duplicate["duplicate_request"] is True and duplicate["created_session_id"] == created
            assert console.dashboard_chat_session_snapshot(created)["draft"]["content"] == ""
            assert len([row for row in modules["list_conversation_sessions"](include_archived=True) if row["id"] == created]) == 1
            state.update({"created": created, "generation": 3})
        checks.append(_run_check("new_conversation_creation_is_exactly_once_and_composer_isolated", create_is_exactly_once_and_empty))

        def send_switch_away_and_late_completion_attach_once() -> None:
            created = state["created"]
            modules["select_conversation_session"](created)
            operation_id = modules["new_conversation_operation_id"]()
            modules["create_operation_marker"](
                operation_id, created, acceptance_key=modules["new_client_acceptance_key"](), streaming=True,
            )
            modules["mark_operation_client_disconnected"](operation_id)
            modules["select_conversation_session"](b["id"])
            modules["append_conversation_turn"](
                created, turn_id=operation_id, user_message="Finish while I am away",
                assistant_response="Completed once while you were elsewhere.", completion_state="completed", success=True,
                provider="ollama", model="daily-polish-fixture-model", streaming=True,
                user_memory_stored=True, assistant_memory_stored=True, select_session=False,
                allow_default_title_update=False,
            )
            modules["append_conversation_turn"](
                created, turn_id=operation_id, user_message="Finish while I am away",
                assistant_response="Duplicate packet must not append.", completion_state="completed", success=True,
                provider="ollama", model="daily-polish-fixture-model", streaming=True,
                select_session=False, allow_default_title_update=False,
            )
            modules["finalize_operation_marker"](
                operation_id, completion_state="completed", success=True,
                final_session_turn_recorded=True,
            )
            assert modules["get_active_conversation_session"]()["id"] == b["id"]
            assert len([turn for turn in modules["conversation_session_turns"](created) if turn["id"] == operation_id]) == 1
            cue = console.dashboard_session_operation_cue(created)
            assert cue and cue["label"] == "Reply ready"
            state["late_operation"] = operation_id
        checks.append(_run_check("accepted_turn_can_finish_away_once_without_stealing_selection", send_switch_away_and_late_completion_attach_once))

        def failed_turn_has_one_explicit_recovery_surface() -> None:
            operation_id = modules["new_conversation_operation_id"]()
            modules["create_operation_marker"](
                operation_id, b["id"], acceptance_key=modules["new_client_acceptance_key"](), streaming=True,
            )
            modules["append_conversation_turn"](
                b["id"], turn_id=operation_id, user_message="Please continue",
                assistant_response="Partial visible reply", completion_state="failed", success=False,
                failure_category="timeout", provider="ollama", model="daily-polish-fixture-model",
                streaming=True, select_session=False,
            )
            modules["finalize_operation_marker"](
                operation_id, completion_state="failed", success=False, failure_category="timeout",
                final_session_turn_recorded=True,
            )
            modules["select_conversation_session"](b["id"])
            html = console.render_realtime_chat_panel(None)
            assert html.split("<script>", 1)[0].count("Run explicit linked recovery") == 1
            assert "Needs recovery" in html
            assert ">Regenerate<" not in html and "dashboard_chat_turn_regenerate" not in html
            assert console.dashboard_session_operation_cue(b["id"])["label"] == "Needs recovery"
            state["failed_operation"] = operation_id
        checks.append(_run_check("failed_turn_has_one_explicit_recovery_path_and_no_regenerate", failed_turn_has_one_explicit_recovery_surface))

        def cancellation_is_exact_and_excluded_from_prompt_history() -> None:
            operation_id = modules["new_conversation_operation_id"]()
            modules["create_operation_marker"](
                operation_id, c["id"], acceptance_key=modules["new_client_acceptance_key"](), streaming=True,
            )
            first = modules["request_operation_cancellation"](operation_id)
            second = modules["request_operation_cancellation"](operation_id)
            modules["append_conversation_turn"](
                c["id"], turn_id=operation_id, user_message="Cancel this",
                assistant_response="Partial reply", completion_state="cancelled", success=False,
                failure_category="cancelled", provider="ollama", model="daily-polish-fixture-model",
                streaming=True, select_session=False,
            )
            modules["finalize_operation_marker"](
                operation_id, completion_state="cancelled", success=False, failure_category="cancelled",
                final_session_turn_recorded=True,
            )
            assert first["cancellation_requested"] is True and second["cancellation_requested"] is True
            assert all(row["user"] != "Cancel this" for row in modules["conversation_history_for_prompt"](c["id"]))
            assert console.dashboard_session_operation_cue(c["id"])["label"] == "Cancelled"
        checks.append(_run_check("cancellation_is_idempotent_visible_and_excluded_from_prompt_history", cancellation_is_exact_and_excluded_from_prompt_history))

        def running_archive_is_refused_but_unrelated_rename_is_safe() -> None:
            operation_id = modules["new_conversation_operation_id"]()
            modules["create_operation_marker"](
                operation_id, a["id"], acceptance_key=modules["new_client_acceptance_key"](), streaming=True,
            )
            client = state["client"]
            blocked = _lifecycle(
                modules, client=client, generation=4, request="daily-archive-block-0001", action="archive",
                source=b["id"], target=a["id"], draft="project newer", stamp="2099-01-01T11:02:00.000Z",
            )
            renamed = _lifecycle(
                modules, client=client, generation=5, request="daily-rename-0001", action="rename",
                source=b["id"], target=b["id"], title="Project renamed", draft="project newer",
                stamp="2099-01-01T11:03:00.000Z",
            )
            assert blocked["blocked"] is True
            assert renamed["changed"] is True
            assert modules["load_conversation_session"](a["id"], include_turns=False)["status"] == "active"
            assert modules["load_conversation_session"](b["id"], include_turns=False)["title"] == "Project renamed"
            modules["finalize_operation_marker"](
                operation_id, completion_state="cancelled", success=False, failure_category="cancelled",
                final_session_turn_recorded=False,
            )
            state["generation"] = 5
        checks.append(_run_check("archive_refuses_exact_running_session_while_unrelated_rename_remains_safe", running_archive_is_refused_but_unrelated_rename_is_safe))

        def archive_restore_and_restore_open_keep_deterministic_selection() -> None:
            client = state["client"]
            modules["select_conversation_session"](b["id"])
            archived = _lifecycle(
                modules, client=client, generation=6, request="daily-archive-0002", action="archive",
                source=b["id"], target=b["id"], draft="project archived draft",
                stamp="2099-01-01T11:04:00.000Z",
            )
            fallback = archived["selected_session_id"]
            assert fallback and fallback != b["id"]
            restored = _lifecycle(
                modules, client=client, generation=7, request="daily-restore-0001", action="restore",
                source=fallback, target=b["id"], draft=modules["load_conversation_draft"](fallback)["content"],
                stamp="2099-01-01T11:05:00.000Z",
            )
            assert restored["selected_session_id"] == fallback
            opened = _lifecycle(
                modules, client=client, generation=8, request="daily-restore-open-0001", action="restore_open",
                source=fallback, target=b["id"], draft=modules["load_conversation_draft"](fallback)["content"],
                stamp="2099-01-01T11:06:00.000Z",
            )
            assert opened["selected_session_id"] == b["id"]
            assert modules["load_conversation_draft"](b["id"])["content"] == "project archived draft"
            state["generation"] = 8
        checks.append(_run_check("archive_fallback_restore_and_restore_open_preserve_drafts_and_selection", archive_restore_and_restore_open_keep_deterministic_selection))

        def provider_settings_departure_is_state_preserving() -> None:
            before_active = modules["get_active_conversation_session"]()["id"]
            before_drafts = {row["id"]: modules["load_conversation_draft"](row["id"])["content"] for row in modules["list_conversation_sessions"](include_archived=True)}
            html = console.render_realtime_chat_panel(None)
            assert "/local-model?return_to=chat#local-model-config-form" in html
            assert "await persistDraft" in html and "await persistPresentation" in html
            after_active = modules["get_active_conversation_session"]()["id"]
            after_drafts = {row["id"]: modules["load_conversation_draft"](row["id"])["content"] for row in modules["list_conversation_sessions"](include_archived=True)}
            assert before_active == after_active and before_drafts == after_drafts
        checks.append(_run_check("provider_settings_departure_and_return_contract_preserves_conversation_state", provider_settings_departure_is_state_preserving))

        def refresh_and_reopen_resume_exact_active_state() -> None:
            active = modules["get_active_conversation_session"]()
            assert active and active["id"] == b["id"]
            snapshot = console.dashboard_chat_session_snapshot(active["id"])
            assert snapshot["session"]["id"] == b["id"]
            assert snapshot["draft"]["content"] == "project archived draft"
            assert snapshot["operation_status"]["operation"]["operation_id"] == state["failed_operation"]
        checks.append(_run_check("refresh_and_reopen_resume_exact_active_draft_and_operation_truth", refresh_and_reopen_resume_exact_active_state))

        def no_duplicate_cross_feature_records_exist() -> None:
            sessions = modules["list_conversation_sessions"](include_archived=True)
            ids = [row["id"] for row in sessions]
            assert len(ids) == len(set(ids))
            for row in sessions:
                turns = modules["conversation_session_turns"](row["id"])
                turn_ids = [turn["id"] for turn in turns]
                assert len(turn_ids) == len(set(turn_ids))
            assert len([turn for turn in modules["conversation_session_turns"](state["created"]) if turn["id"] == state["late_operation"]]) == 1
            html = console.render_realtime_chat_panel(None)
            assert html.count("id='realtime-chat-form'") == 1
            assert html.count("id='chat-session-switch-form'") == 1
            assert html.count("id='chat-session-create-form'") == 1
        checks.append(_run_check("daily_workflow_has_no_duplicate_sessions_turns_or_primary_controls", no_duplicate_cross_feature_records_exist))

        def continuity_and_explicit_memory_are_unchanged_by_navigation_lifecycle() -> None:
            memories = modules["load_memories"]()
            assert len(memories) == 1 and memories[0]["content"] == "Explicit fixture memory"
            self_value = json.loads(modules["SELF_FILE"].read_text(encoding="utf-8"))
            desires = json.loads(modules["DESIRES_FILE"].read_text(encoding="utf-8"))
            assert self_value["mood"] == "steady" and self_value["focus"] == "daily companion"
            assert desires == {"connection": 0.8}
            assert all("relationship_score" not in row and "engagement_score" not in row for row in modules["list_conversation_sessions"](include_archived=True))
        checks.append(_run_check("navigation_and_lifecycle_do_not_mutate_memory_relationship_mood_or_moments", continuity_and_explicit_memory_are_unchanged_by_navigation_lifecycle))

        def render_get_paths_are_side_effect_free() -> None:
            before = _tree_bytes(EXTERNAL_DATA_DIR)
            console.render_realtime_chat_panel(None)
            console.dashboard_chat_session_snapshot(b["id"])
            console.dashboard_chat_operation_status(session_id=b["id"])
            after = _tree_bytes(EXTERNAL_DATA_DIR)
            assert before == after
        checks.append(_run_check("passive_render_snapshot_and_status_gets_are_side_effect_free", render_get_paths_are_side_effect_free))

        def privacy_and_governance_contract_remains_intact() -> None:
            html = console.render_realtime_chat_panel(None).lower()
            ordinary = html[:html.index("generation details")]
            for forbidden in ("receipt_path", "raw_events", "traceback", "authorization_token"):
                assert forbidden not in ordinary
            source = (ROOT / "conscious_agent" / "dashboard_chat_console.py").read_text(encoding="utf-8").lower()
            for forbidden in ("ollama pull", "ollama create", "model install", "autonomous_action_enabled = true"):
                assert forbidden not in source
            entries = list(modules["iter_source_tree_entries"](ROOT))
            assert not modules["forbidden_runtime_path_matches"](entries)
            assert not any(path.endswith(".zip") for path in entries)
            assert not any("conversation_runtime/operations" in path or "conversation_sessions/" in path for path in entries)
        checks.append(_run_check("privacy_governance_and_source_package_exclusions_remain_intact", privacy_and_governance_contract_remains_intact))

    finally:
        try:
            _restore_tree(EXTERNAL_DATA_DIR, backup)
            restored = True
        except Exception as error:
            restore_error = f"{type(error).__name__}: {error}"
        source_after = _source_snapshot()
        checks.append(_run_check("source_tree_is_immutable", lambda: (_ for _ in ()).throw(AssertionError("source tree changed")) if source_before != source_after else None))

    passed = sum(1 for item in checks if item["status"] == "pass")
    result = {
        "suite": "v1079.5.7-daily-companion-polish-consolidation",
        "status": "pass" if passed == len(checks) and restored and not restore_error else "fail",
        "ok": passed == len(checks) and restored and not restore_error,
        "passed": passed,
        "total": len(checks),
        "checks": checks,
        "runtime_data_restored": restored,
        "restore_error": restore_error,
        "native_provider_evidence": False,
        "evidence_classification": "deterministic fixture",
    }
    print(json.dumps(result, indent=2) if args.json else f"{result['status']}: {passed}/{len(checks)}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
