from __future__ import annotations

"""Deterministic v1079.4 session organization and failed-turn recovery fixtures."""

import argparse
import json
import os
import shutil
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
sys.path.insert(0, str(AGENT))
EXTERNAL_DATA_DIR = Path(os.environ.get("EIDOLON_DATA_DIR") or (ROOT / "data")).resolve()


def _snapshot_tree(root: Path) -> Path:
    backup = Path(tempfile.mkdtemp(prefix="eidolon-session-organization-backup-"))
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


def _load_modules() -> dict[str, Any]:
    import conversation_runtime
    import dashboard_chat_console
    from conversation_operations import create_operation_marker, finalize_operation_marker, new_conversation_operation_id
    from conversation_recovery import (
        ConversationRecoveryError,
        recovery_state,
        retry_failed_conversation_turn,
    )
    from conversation_sessions import (
        ACTIVE_SESSION_FILE,
        append_conversation_turn,
        archive_conversation_session,
        conversation_history_for_prompt,
        conversation_session_turns,
        create_conversation_session,
        list_conversation_sessions,
        load_conversation_session,
        rename_conversation_session,
        restore_conversation_session,
        search_conversation_sessions,
        select_conversation_session,
    )
    from dashboard import handle_action, render_chat_console
    from dashboard_chat_console import render_realtime_chat_panel, retry_dashboard_chat_turn
    from memory import load_memories, store_memory
    from paths import DESIRES_FILE, MEMORY_FILE, SELF_FILE
    from settings_manager import DEFAULT_SETTINGS, load_settings, save_settings

    try:
        import vector_memory
        vector_memory.add_memory_vector = lambda _memory: None
    except Exception:
        pass
    return locals()


def _seed_runtime(modules: dict[str, Any]) -> None:
    EXTERNAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    modules["SELF_FILE"].write_text(json.dumps({"name": "Eidolon", "active_goals": []}), encoding="utf-8")
    modules["DESIRES_FILE"].write_text(json.dumps({"connection": 0.8}), encoding="utf-8")
    modules["MEMORY_FILE"].write_text("[]", encoding="utf-8")
    settings = deepcopy(modules["DEFAULT_SETTINGS"])
    settings["local_model_provider"] = "ollama"
    settings["local_model"] = "organization-fixture-model"
    settings["ai_chat_enabled"] = True
    modules["save_settings"](settings)


def _run_check(name: str, function: Callable[[], None]) -> dict[str, Any]:
    try:
        function()
        return {"name": name, "status": "pass"}
    except Exception as error:
        return {"name": name, "status": "fail", "error": f"{type(error).__name__}: {error}"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    backup = _snapshot_tree(EXTERNAL_DATA_DIR)
    checks: list[dict[str, Any]] = []
    restored = False
    restore_error = ""
    try:
        if EXTERNAL_DATA_DIR.exists():
            shutil.rmtree(EXTERNAL_DATA_DIR)
        modules = _load_modules()
        _seed_runtime(modules)

        create = modules["create_conversation_session"]
        append = modules["append_conversation_turn"]
        turns = modules["conversation_session_turns"]
        load = modules["load_conversation_session"]
        state: dict[str, Any] = {}

        def append_accepted_failed_turn(
            session_id: str, *, user_message: str, assistant_response: str, failure_category: str,
            acceptance_key: str, user_memory_stored: bool = False,
        ) -> str:
            operation_id = modules["new_conversation_operation_id"]()
            modules["create_operation_marker"](
                operation_id, session_id, acceptance_key=acceptance_key, streaming=True,
            )
            append(
                session_id, turn_id=operation_id, user_message=user_message,
                assistant_response=assistant_response, completion_state="failed", success=False,
                failure_category=failure_category, user_memory_stored=user_memory_stored,
            )
            modules["finalize_operation_marker"](
                operation_id, completion_state="failed", success=False, failure_category=failure_category,
                final_session_turn_recorded=True,
            )
            return operation_id

        def rename_preserves_identity_and_history() -> None:
            session = create("Original title", source="fixture")
            append(session["id"], turn_id="rename-turn", user_message="hello", assistant_response="Eidolon: hi", completion_state="completed", success=True, provider="ollama", model="one")
            renamed = modules["rename_conversation_session"](session["id"], "Daily continuity")
            loaded = load(session["id"], include_turns=True)
            assert renamed["id"] == session["id"]
            assert loaded["title"] == "Daily continuity"
            assert loaded["turns"][0]["provider"] == "ollama"
            assert loaded["turn_count"] == 1
            state["organized"] = loaded
        checks.append(_run_check("rename_preserves_session_id_history_and_provider_metadata", rename_preserves_identity_and_history))

        def blank_rename_fails_without_mutation() -> None:
            session_id = state["organized"]["id"]
            before = load(session_id, include_turns=True)
            try:
                modules["rename_conversation_session"](session_id, "   ")
                raise AssertionError("blank rename unexpectedly succeeded")
            except ValueError:
                pass
            assert load(session_id, include_turns=True) == before
        checks.append(_run_check("blank_rename_fails_closed_without_mutation", blank_rename_fails_without_mutation))

        def archive_restore_preserves_private_history() -> None:
            session_id = state["organized"]["id"]
            modules["select_conversation_session"](session_id)
            archived = modules["archive_conversation_session"](session_id)
            assert archived["status"] == "archived"
            assert not modules["ACTIVE_SESSION_FILE"].exists()
            assert session_id not in {item["id"] for item in modules["list_conversation_sessions"]()}
            assert session_id in {item["id"] for item in modules["list_conversation_sessions"](include_archived=True)}
            try:
                modules["select_conversation_session"](session_id)
                raise AssertionError("archived session unexpectedly selected")
            except ValueError:
                pass
            restored_session = modules["restore_conversation_session"](session_id)
            assert restored_session["status"] == "active"
            assert len(turns(session_id)) == 1
            assert modules["select_conversation_session"](session_id)["id"] == session_id
        checks.append(_run_check("archive_restore_never_deletes_history_or_selects_archived_session", archive_restore_preserves_private_history))

        def local_search_is_bounded_to_titles_and_completed_turns() -> None:
            first = state["organized"]["id"]
            second = create("Project planning", source="fixture")
            append(second["id"], turn_id="search-ok", user_message="Discuss the lantern launch", assistant_response="Eidolon: Lantern notes saved.", completion_state="completed", success=True)
            append(second["id"], turn_id="search-failed", user_message="secret timeout phrase", assistant_response="timeout", completion_state="failed", success=False, failure_category="timeout")
            assert [item["id"] for item in modules["search_conversation_sessions"]("daily continuity")] == [first]
            assert [item["id"] for item in modules["search_conversation_sessions"]("lantern launch")] == [second["id"]]
            assert modules["search_conversation_sessions"]("secret timeout phrase") == []
            raw = json.dumps(modules["search_conversation_sessions"]("lantern"), sort_keys=True).lower()
            assert "timings_ms" not in raw and "receipt_path" not in raw and "raw_events" not in raw
            state["search_session"] = second
        checks.append(_run_check("local_search_uses_titles_and_completed_text_but_not_failed_turns_or_receipts", local_search_is_bounded_to_titles_and_completed_turns))

        def dashboard_get_search_is_write_free() -> None:
            before = {
                str(path.relative_to(EXTERNAL_DATA_DIR)): path.read_bytes()
                for path in EXTERNAL_DATA_DIR.rglob("*") if path.is_file()
            }
            html = modules["render_chat_console"](session_query="lantern", include_archived=True)
            after = {
                str(path.relative_to(EXTERNAL_DATA_DIR)): path.read_bytes()
                for path in EXTERNAL_DATA_DIR.rglob("*") if path.is_file()
            }
            assert before == after
            assert "Find and organize conversations" in html
            assert "dashboard_chat_session_rename" in html
            assert "dashboard_chat_session_archive" in html
            assert "dashboard_chat_session_restore" not in html
            assert "conversation_runtime/receipts" not in html
        checks.append(_run_check("dashboard_search_and_organization_preview_is_side_effect_free", dashboard_get_search_is_write_free))

        def dashboard_post_actions_route_through_session_service() -> None:
            session = state["search_session"]
            modules["handle_action"]({"action": ["dashboard_chat_session_rename"], "session_id": [session["id"]], "title": ["Renamed in dashboard"]})
            assert load(session["id"], include_turns=False)["title"] == "Renamed in dashboard"
            modules["handle_action"]({"action": ["dashboard_chat_session_archive"], "session_id": [session["id"]]})
            assert load(session["id"], include_turns=False)["status"] == "archived"
            modules["handle_action"]({"action": ["dashboard_chat_session_restore"], "session_id": [session["id"]]})
            assert load(session["id"], include_turns=False)["status"] == "active"
        checks.append(_run_check("dashboard_post_actions_rename_archive_and_restore_explicitly", dashboard_post_actions_route_through_session_service))

        def failed_retry_reuses_existing_user_memory_once() -> None:
            session = create("Recovery", source="fixture")
            source_id = append_accepted_failed_turn(
                session["id"], user_message="Please continue safely", assistant_response="Timed out safely.",
                failure_category="timeout", acceptance_key="organization_failed_acceptance", user_memory_stored=True,
            )
            modules["store_memory"]({"type": "conversation_user", "content": "Please continue safely", "conversation_operation_id": source_id, "conversation_session_id": session["id"], "completion_state": "received"})
            runtime = modules["conversation_runtime"]
            prompts: list[str] = []

            class FakeClient:
                last_retry_count = 0
                def __init__(self, config: Any, cancel_event: Any = None) -> None:
                    self.config = config
                def generate(self, prompt: str) -> str:
                    prompts.append(prompt)
                    return "recovered response"
                def cancel(self) -> None: return None
                def close(self) -> None: return None

            original = runtime.LocalModelClient
            runtime.LocalModelClient = FakeClient
            try:
                recovery = modules["recovery_state"](session["id"], source_id)
                result = modules["retry_failed_conversation_turn"](
                    session["id"], source_id, use_ai=True, source="fixture_recovery",
                    expected_recovery_cue=recovery["recovery_cue_token"],
                )
            finally:
                runtime.LocalModelClient = original
            assert result.success and result.user_memory_reused and not result.user_memory_stored
            assert result.recovery_of == source_id and result.recovery_kind == "failed_turn_retry"
            session_turns = turns(session["id"])
            assert len(session_turns) == 2
            assert session_turns[-1]["recovery_of"] == source_id
            assert session_turns[-1]["assistant_memory_stored"] is True
            memories = modules["load_memories"]()
            user_rows = [item for item in memories if item.get("type") == "conversation_user" and item.get("content") == "Please continue safely"]
            assistant_rows = [item for item in memories if item.get("type") == "conversation_eidolon" and item.get("conversation_session_id") == session["id"]]
            assert len(user_rows) == 1 and len(assistant_rows) == 1
            assert modules["conversation_history_for_prompt"](session["id"])[-1]["assistant_response"].endswith("recovered response")
            state["recovery"] = (session, result, source_id)
        checks.append(_run_check("failed_retry_reuses_user_memory_and_commits_one_linked_assistant_turn", failed_retry_reuses_existing_user_memory_once))

        def missing_original_user_memory_is_created_once() -> None:
            session = create("Configuration recovery", source="fixture")
            source_id = append_accepted_failed_turn(
                session["id"], user_message="Retry after configuration repair", assistant_response="Invalid configuration.",
                failure_category="invalid_configuration", acceptance_key="organization_config_acceptance",
            )
            runtime = modules["conversation_runtime"]

            class FakeClient:
                last_retry_count = 0
                def __init__(self, config: Any, cancel_event: Any = None) -> None: self.config = config
                def generate(self, prompt: str) -> str: return "configuration recovered"
                def cancel(self) -> None: return None
                def close(self) -> None: return None

            original = runtime.LocalModelClient
            runtime.LocalModelClient = FakeClient
            try:
                recovery = modules["recovery_state"](session["id"], source_id)
                result = modules["retry_failed_conversation_turn"](
                    session["id"], source_id, expected_recovery_cue=recovery["recovery_cue_token"],
                )
            finally:
                runtime.LocalModelClient = original
            assert result.success and result.user_memory_stored and not result.user_memory_reused
            rows = [item for item in modules["load_memories"]() if item.get("type") == "conversation_user" and item.get("content") == "Retry after configuration repair"]
            assert len(rows) == 1 and rows[0].get("recovery_of") == source_id
        checks.append(_run_check("retry_creates_missing_original_user_memory_exactly_once", missing_original_user_memory_is_created_once))

        def duplicate_successful_recovery_is_blocked_without_writes() -> None:
            session, _result, source_id = state["recovery"]
            before_memories = deepcopy(modules["load_memories"]())
            before_turns = deepcopy(turns(session["id"]))
            try:
                modules["retry_failed_conversation_turn"](session["id"], source_id)
                raise AssertionError("duplicate successful retry unexpectedly ran")
            except modules["ConversationRecoveryError"]:
                pass
            assert modules["load_memories"]() == before_memories
            assert turns(session["id"]) == before_turns
            assert modules["recovery_state"](session["id"], source_id)["successful_recovery_turn_id"]
        checks.append(_run_check("repeat_retry_after_success_is_blocked_without_memory_or_turn_duplication", duplicate_successful_recovery_is_blocked_without_writes))

        def completed_turn_regeneration_is_blocked() -> None:
            session = create("Completed", source="fixture")
            append(session["id"], turn_id="completed-source", user_message="done", assistant_response="Eidolon: done", completion_state="completed", success=True, user_memory_stored=True, assistant_memory_stored=True)
            before = deepcopy(turns(session["id"]))
            try:
                modules["retry_failed_conversation_turn"](session["id"], "completed-source")
                raise AssertionError("completed turn was regenerated")
            except modules["ConversationRecoveryError"]:
                pass
            assert turns(session["id"]) == before
            assert modules["recovery_state"](session["id"], "completed-source")["completed_turn_replay_blocked"] is True
        checks.append(_run_check("completed_turn_regeneration_is_blocked_until_memory_supersession_exists", completed_turn_regeneration_is_blocked))

        def recovery_uses_current_provider_without_switch_or_fallback() -> None:
            session = create("Provider recovery", source="fixture")
            source_id = append_accepted_failed_turn(
                session["id"], user_message="recover on selected provider", assistant_response="offline",
                failure_category="unavailable_service", acceptance_key="organization_provider_acceptance",
            )
            settings = deepcopy(modules["DEFAULT_SETTINGS"])
            settings["local_model_provider"] = "llama_cpp"
            settings["local_model"] = "llama-recovery-model"
            settings["local_model_endpoint"] = "http://127.0.0.1:8080"
            settings["local_model_provider_profiles"]["llama_cpp"]["local_model"] = "llama-recovery-model"
            modules["save_settings"](settings)
            before_settings = deepcopy(modules["load_settings"]())
            runtime = modules["conversation_runtime"]

            class FakeClient:
                last_retry_count = 0
                def __init__(self, config: Any, cancel_event: Any = None) -> None: self.config = config
                def generate(self, prompt: str) -> str: return "llama recovery"
                def cancel(self) -> None: return None
                def close(self) -> None: return None

            original = runtime.LocalModelClient
            runtime.LocalModelClient = FakeClient
            try:
                recovery = modules["recovery_state"](session["id"], source_id)
                result = modules["retry_failed_conversation_turn"](
                    session["id"], source_id, expected_recovery_cue=recovery["recovery_cue_token"],
                )
            finally:
                runtime.LocalModelClient = original
            assert result.success and result.provider == "llama_cpp" and result.model == "llama-recovery-model"
            assert result.fallback_configured is False and result.fallback_used is False
            assert modules["load_settings"]() == before_settings
            assert load(session["id"], include_turns=False)["last_provider"] == "llama_cpp"
            _seed_runtime(modules)
        checks.append(_run_check("recovery_uses_current_explicit_provider_without_fallback_or_profile_mutation", recovery_uses_current_provider_without_switch_or_fallback))

        def dashboard_retry_control_is_visible_and_idempotent() -> None:
            session = create("Dashboard retry", source="fixture")
            source_id = append_accepted_failed_turn(
                session["id"], user_message="dashboard retry message", assistant_response="Disconnected safely.",
                failure_category="interrupted_stream", acceptance_key="organization_dashboard_acceptance",
            )
            modules["select_conversation_session"](session["id"])
            html = modules["render_realtime_chat_panel"](None)
            assert "Run explicit linked recovery" in html
            assert "dashboard_chat_turn_retry" in html
            assert "name='recovery_token'" in html
            assert "dashboard_chat_turn_regenerate" not in html
        checks.append(_run_check("dashboard_exposes_failed_retry_but_not_unsafe_completed_regeneration", dashboard_retry_control_is_visible_and_idempotent))

        def dashboard_retry_records_linked_turn_without_reproposing_action() -> None:
            session = create("Dashboard action retry", source="fixture")
            source_id = append_accepted_failed_turn(
                session["id"], user_message="retry from dashboard action", assistant_response="timeout",
                failure_category="timeout", acceptance_key="organization_action_acceptance",
            )
            recovery_token = modules["recovery_state"](session["id"], source_id)["recovery_cue_token"]
            runtime = modules["conversation_runtime"]
            dashboard = modules["dashboard_chat_console"]

            class FakeClient:
                last_retry_count = 0
                def __init__(self, config: Any, cancel_event: Any = None) -> None: self.config = config
                def generate(self, prompt: str) -> str: return "dashboard recovered"
                def cancel(self) -> None: return None
                def close(self) -> None: return None

            original_client = runtime.LocalModelClient
            original_propose = dashboard.propose_chat_action
            original_should_analyze = dashboard.should_analyze_chat_action
            original_side_effects = dashboard._save_post_response_side_effects
            runtime.LocalModelClient = FakeClient
            dashboard.should_analyze_chat_action = lambda *_args, **_kwargs: True
            dashboard.propose_chat_action = lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("provider retry must not propose a new operator action"))
            dashboard._save_post_response_side_effects = lambda *_args, **_kwargs: ""
            try:
                modules["handle_action"]({
                    "action": ["dashboard_chat_turn_retry"],
                    "session_id": [session["id"]],
                    "turn_id": [source_id],
                    "recovery_token": [recovery_token],
                    "use_ai": ["true"],
                })
            finally:
                runtime.LocalModelClient = original_client
                dashboard.propose_chat_action = original_propose
                dashboard.should_analyze_chat_action = original_should_analyze
                dashboard._save_post_response_side_effects = original_side_effects
            linked = [item for item in turns(session["id"]) if item.get("recovery_of") == source_id]
            assert len(linked) == 1 and linked[0]["success"] is True
            dashboard_rows = [item for item in dashboard.list_dashboard_chat_turns(session["id"]) if item.get("recovery_of") == source_id]
            assert len(dashboard_rows) == 1
            assert dashboard_rows[0]["action_id"] == "" and dashboard_rows[0]["action"] is None
        checks.append(_run_check("dashboard_retry_post_records_one_linked_runtime_turn_without_reproposing_action", dashboard_retry_records_linked_turn_without_reproposing_action))

        def no_delete_or_autonomy_surface_added() -> None:
            source = (AGENT / "conversation_recovery.py").read_text(encoding="utf-8")
            panel = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
            assert "delete_conversation_session" not in source + panel
            assert "install_model(" not in source
            assert "autonomous_action" not in source
            assert "dashboard_chat_session_delete" not in panel
        checks.append(_run_check("organization_and_recovery_add_no_delete_model_management_or_autonomy_surface", no_delete_or_autonomy_surface_added))

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
        "suite": "v1079.4-conversation-session-organization-and-recovery",
        "evidence_kind": "deterministic_fixture",
        "native_provider_evidence": False,
        "passed": len(checks) - len(failed),
        "total": len(checks),
        "checks": checks,
        "runtime_data_restored": restored,
        "runtime_data_restore_error": restore_error or None,
        "governance": {
            "completed_turn_regeneration_enabled": False,
            "session_deletion_enabled": False,
            "provider_fallback_enabled": False,
            "model_management_performed": False,
            "autonomy_expanded": False,
        },
    }
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"{report['status']}: {report['passed']}/{report['total']}")
        for check in checks:
            print(f"- {check['status']}: {check['name']}{' - ' + check.get('error','') if check.get('error') else ''}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
