from __future__ import annotations

"""Deterministic v1079.4 conversation-session continuity fixtures.

The suite uses only an isolated EIDOLON_DATA_DIR. It does not contact native
providers, install models, execute actions, or expose private runtime receipts.
"""

import argparse
import json
import os
import shutil
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
sys.path.insert(0, str(AGENT))
EXTERNAL_DATA_DIR = Path(os.environ.get("EIDOLON_DATA_DIR") or (ROOT / "data")).resolve()


def _snapshot_tree(root: Path) -> Path:
    backup = Path(tempfile.mkdtemp(prefix="eidolon-session-fixture-backup-"))
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
    import conversation_sessions
    from conversation_context import build_conversation_prompt
    from conversation_runtime import run_conversation_turn
    import conversation_runtime
    from conversation_sessions import (
        append_conversation_turn,
        conversation_history_for_prompt,
        conversation_session_turns,
        create_conversation_session,
        get_active_conversation_session,
        list_conversation_sessions,
        load_conversation_session,
        select_conversation_session,
        session_contains_private_receipt_fields,
    )
    from dashboard_chat_console import list_dashboard_chat_turns, render_realtime_chat_panel, save_dashboard_chat_turn
    from memory import load_memories
    from paths import DESIRES_FILE, MEMORY_FILE, SELF_FILE
    from settings_manager import DEFAULT_SETTINGS, save_settings

    try:
        import vector_memory
        vector_memory.add_memory_vector = lambda _memory: None
    except Exception:
        pass

    return locals()


def _seed_runtime(modules: dict[str, Any]) -> None:
    data_dir = EXTERNAL_DATA_DIR
    data_dir.mkdir(parents=True, exist_ok=True)
    modules["SELF_FILE"].write_text(json.dumps({"name": "Eidolon", "active_goals": []}), encoding="utf-8")
    modules["DESIRES_FILE"].write_text(json.dumps({"connection": 0.8}), encoding="utf-8")
    modules["MEMORY_FILE"].write_text(json.dumps([
        {"type": "preference", "content": "Marcus prefers direct, practical answers.", "importance": "high"},
        {"type": "conversation_user", "content": "old global transcript should not be injected"},
    ]), encoding="utf-8")
    settings = deepcopy(modules["DEFAULT_SETTINGS"])
    settings["local_model_provider"] = "ollama"
    settings["local_model"] = "session-fixture-model"
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
        select = modules["select_conversation_session"]
        active = modules["get_active_conversation_session"]
        list_sessions = modules["list_conversation_sessions"]
        load_session = modules["load_conversation_session"]
        append_turn = modules["append_conversation_turn"]
        turns = modules["conversation_session_turns"]
        history = modules["conversation_history_for_prompt"]

        state: dict[str, Any] = {}

        def dashboard_preview_is_side_effect_free() -> None:
            session_root = EXTERNAL_DATA_DIR / "conversation_sessions"
            if session_root.exists():
                shutil.rmtree(session_root)
            html = modules["render_realtime_chat_panel"](None)
            assert "New conversation" in html
            assert not session_root.exists()
        checks.append(_run_check("dashboard_get_preview_does_not_create_session_runtime_data", dashboard_preview_is_side_effect_free))

        def concurrent_atomic_writes_do_not_share_a_windows_temp_file() -> None:
            target = EXTERNAL_DATA_DIR / "conversation_sessions" / "atomic-write-race.json"
            values = [{"writer": index} for index in range(12)]
            with ThreadPoolExecutor(max_workers=6) as pool:
                list(pool.map(lambda value: modules["conversation_sessions"]._atomic_write(target, value), values))
            saved = json.loads(target.read_text(encoding="utf-8"))
            assert saved in values
            assert not list(target.parent.glob(f".{target.name}.*.tmp"))
        checks.append(_run_check("concurrent_atomic_writes_use_unique_windows_temp_files", concurrent_atomic_writes_do_not_share_a_windows_temp_file))

        def creation_selection_resume() -> None:
            first = create("Daily conversation", source="fixture")
            second = create("Project thoughts", source="fixture")
            assert active()["id"] == second["id"]
            selected = select(first["id"])
            assert selected["id"] == first["id"]
            assert active()["id"] == first["id"]
            assert {item["id"] for item in list_sessions()} == {first["id"], second["id"]}
            state["first"] = first
            state["second"] = second
        checks.append(_run_check("session_creation_selection_and_resumption", creation_selection_resume))

        def automatic_title_and_idempotency() -> None:
            session = create(source="fixture")
            append_turn(session["id"], turn_id="turn-1", user_message="Remember our morning routine", assistant_response="Eidolon: I remember.", completion_state="completed", success=True, provider="ollama", model="one")
            append_turn(session["id"], turn_id="turn-1", user_message="duplicate", assistant_response="duplicate", completion_state="completed", success=True)
            loaded = load_session(session["id"], include_turns=True)
            assert loaded["title"] == "Remember our morning routine"
            assert loaded["turn_count"] == 1
            state["continuity"] = loaded
        checks.append(_run_check("first_turn_titles_session_and_turn_append_is_idempotent", automatic_title_and_idempotency))

        def failed_turns_excluded() -> None:
            session_id = state["continuity"]["id"]
            append_turn(session_id, turn_id="turn-2", user_message="This times out", assistant_response="Timed out safely.", completion_state="failed", success=False, failure_category="timeout", provider="ollama", model="one")
            append_turn(session_id, turn_id="turn-3", user_message="Continue successfully", assistant_response="Eidolon: Continuing.", completion_state="completed", success=True, provider="llama_cpp", model="two")
            prompt_rows = history(session_id, limit=8)
            assert [row["user_message"] for row in prompt_rows] == ["Remember our morning routine", "Continue successfully"]
            assert all("times out" not in row["user_message"].lower() for row in prompt_rows)
            assert len(turns(session_id)) == 3
        checks.append(_run_check("failed_and_partial_turns_visible_but_excluded_from_prompt_history", failed_turns_excluded))

        def provider_switch_keeps_session() -> None:
            session_id = state["continuity"]["id"]
            loaded = load_session(session_id, include_turns=True)
            assert loaded["last_provider"] == "llama_cpp"
            assert loaded["turns"][0]["provider"] == "ollama"
            assert loaded["turns"][-1]["provider"] == "llama_cpp"
            assert active()["id"] == session_id
        checks.append(_run_check("provider_switch_preserves_same_session_and_transcript", provider_switch_keeps_session))

        def prompt_history_order_and_metrics() -> None:
            packet = modules["build_conversation_prompt"](
                user_message="What happened next?",
                self_model={"name": "Eidolon", "active_goals": []},
                desires={},
                memories=[{"type": "preference", "content": "Marcus likes continuity.", "importance": "high"}],
                project_context="",
                goal_context="",
                task_context="",
                conversation_history=history(state["continuity"]["id"]),
                context_size=4096,
                max_tokens=256,
            )
            assert packet.prompt.index("Remember our morning routine") < packet.prompt.index("Continue successfully")
            assert "This times out" not in packet.prompt
            assert packet.metrics.history_turn_candidates == 2
            assert packet.metrics.history_turns_included == 2
        checks.append(_run_check("context_builder_admits_complete_history_chronologically", prompt_history_order_and_metrics))

        def bounded_history_omission() -> None:
            session = create("Long session", source="fixture")
            for index in range(10):
                append_turn(session["id"], turn_id=f"long-{index}", user_message=f"User {index} " + "u" * 200, assistant_response=f"Eidolon: Reply {index} " + "r" * 200, completion_state="completed", success=True)
            packet = modules["build_conversation_prompt"](
                user_message="latest",
                self_model={"name": "Eidolon", "active_goals": []},
                desires={}, memories=[], project_context="", goal_context="", task_context="",
                conversation_history=history(session["id"], limit=10), context_size=900, max_tokens=200,
            )
            assert 0 < packet.metrics.history_turns_included < 10
            assert packet.metrics.history_turns_omitted > 0
            assert "User 9" in packet.prompt
        checks.append(_run_check("oversized_session_history_reduces_to_newest_complete_suffix", bounded_history_omission))

        def no_receipt_fields() -> None:
            loaded = load_session(state["continuity"]["id"], include_turns=True)
            assert not modules["session_contains_private_receipt_fields"](loaded)
            raw = json.dumps(loaded).lower()
            assert "timings_ms" not in raw and "receipt_path" not in raw and "raw_events" not in raw
        checks.append(_run_check("session_history_does_not_embed_private_runtime_receipts", no_receipt_fields))

        def dashboard_panel_session_experience() -> None:
            select(state["continuity"]["id"])
            html = modules["render_realtime_chat_panel"](None)
            assert "New conversation" in html and "Open selected conversation" in html
            assert "Remember our morning routine" in html
            assert "Continue successfully" in html
            assert "conversation_runtime/receipts" not in html
            assert "context_budget" not in html
            assert "session_id: turnSessionId" in html
        checks.append(_run_check("dashboard_renders_selected_transcript_without_receipt_details", dashboard_panel_session_experience))

        def dashboard_turn_filtering() -> None:
            first = state["first"]["id"]
            second = state["second"]["id"]
            modules["save_dashboard_chat_turn"]({"id": "dash-a", "created_at": "2026-01-01", "session_id": first, "user_message": "a"})
            modules["save_dashboard_chat_turn"]({"id": "dash-b", "created_at": "2026-01-02", "session_id": second, "user_message": "b"})
            assert [row["id"] for row in modules["list_dashboard_chat_turns"](first)] == ["dash-a"]
            assert [row["id"] for row in modules["list_dashboard_chat_turns"](second)] == ["dash-b"]
        checks.append(_run_check("dashboard_history_filters_by_selected_session", dashboard_turn_filtering))

        def api_chat_respects_explicit_session() -> None:
            from api_server import handle_api_get, handle_api_post

            session = create("API continuity", source="fixture")
            status, payload = handle_api_post("/api/dashboard-chat", {
                "message": "API session message",
                "use_ai": False,
                "session_id": session["id"],
            })
            assert status == 201
            assert payload["data"]["session_id"] == session["id"]
            status, payload = handle_api_get("/api/dashboard-chat", {"session_id": [session["id"]]})
            assert status == 200
            assert len(payload["data"]) == 1
            assert payload["data"][0]["session_id"] == session["id"]
        checks.append(_run_check("dashboard_chat_api_preserves_and_filters_explicit_session", api_chat_respects_explicit_session))

        def runtime_continuity_and_memory_tags() -> None:
            runtime = modules["conversation_runtime"]
            prompts: list[str] = []
            providers = ["ollama", "llama_cpp"]

            class FakeClient:
                last_retry_count = 0
                def __init__(self, config: Any, cancel_event: Any = None) -> None:
                    self.config = config
                def generate(self, prompt: str) -> str:
                    prompts.append(prompt)
                    return f"reply from {providers[len(prompts)-1]}"
                def cancel(self) -> None:
                    return None
                def close(self) -> None:
                    return None

            original_client = runtime.LocalModelClient
            runtime.LocalModelClient = FakeClient
            try:
                session = create("Runtime continuity", source="fixture")
                first = modules["run_conversation_turn"]("First runtime turn", session_id=session["id"])
                settings = deepcopy(modules["DEFAULT_SETTINGS"])
                settings["local_model_provider"] = "llama_cpp"
                settings["local_model"] = "second-model"
                settings["local_model_endpoint"] = "http://127.0.0.1:8080"
                settings["local_model_provider_profiles"]["llama_cpp"]["local_model"] = "second-model"
                modules["save_settings"](settings)
                second = modules["run_conversation_turn"]("Second runtime turn", session_id=session["id"])
                assert first.success and second.success
                assert first.session_id == second.session_id == session["id"]
                assert first.session_turn_recorded and second.session_turn_recorded
                assert "First runtime turn" in prompts[1] and "reply from ollama" in prompts[1]
                memories = modules["load_memories"]()
                conversation_memories = [
                    row for row in memories
                    if row.get("type") in {"conversation_user", "conversation_eidolon"}
                    and row.get("conversation_session_id") == session["id"]
                ]
                assert len(conversation_memories) == 4
                assert "old global transcript should not be injected" not in prompts[0]
            finally:
                runtime.LocalModelClient = original_client
        checks.append(_run_check("runtime_resumes_session_across_provider_switch_and_tags_memories", runtime_continuity_and_memory_tags))

        def invalid_configuration_is_visible_but_not_reused_as_context() -> None:
            settings = deepcopy(modules["DEFAULT_SETTINGS"])
            settings["local_model_endpoint"] = "not-a-url"
            modules["save_settings"](settings)
            session = create("Recovery state", source="fixture")
            result = modules["run_conversation_turn"]("Can you hear me?", session_id=session["id"])
            assert not result.success
            assert result.failure_category == "invalid_configuration"
            assert result.session_turn_recorded
            saved_turns = turns(session["id"])
            assert len(saved_turns) == 1
            assert saved_turns[0]["failure_category"] == "invalid_configuration"
            assert history(session["id"], limit=8) == []
            _seed_runtime(modules)
        checks.append(_run_check("invalid_configuration_failure_is_visible_but_excluded_from_future_context", invalid_configuration_is_visible_but_not_reused_as_context))

        def no_duplicate_session_turn_on_record_replay() -> None:
            session = create("Replay guard", source="fixture")
            kwargs = dict(turn_id="same-operation", user_message="hello", assistant_response="Eidolon: hi", completion_state="completed", success=True)
            append_turn(session["id"], **kwargs)
            append_turn(session["id"], **kwargs)
            assert len(turns(session["id"])) == 1
        checks.append(_run_check("operation_id_prevents_duplicate_session_turns", no_duplicate_session_turn_on_record_replay))

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
        "suite": "v1079.4-conversation-session-continuity",
        "evidence_kind": "deterministic_fixture",
        "native_provider_evidence": False,
        "passed": len(checks) - len(failed),
        "total": len(checks),
        "checks": checks,
        "runtime_data_restored": restored,
        "runtime_data_restore_error": restore_error or None,
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
