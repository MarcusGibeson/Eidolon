from __future__ import annotations

"""Deterministic v1079.5 daily companion resume and draft-continuity fixtures.

The suite uses an isolated EIDOLON_DATA_DIR. It does not contact native providers,
install or remove models, execute actions, grant approvals, or expose private text
outside the temporary fixture tree.
"""

import argparse
import importlib
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

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
sys.path.insert(0, str(AGENT))
EXTERNAL_DATA_DIR = Path(os.environ.get("EIDOLON_DATA_DIR") or (ROOT / "data")).resolve()


def _snapshot_tree(root: Path) -> Path:
    backup = Path(tempfile.mkdtemp(prefix="eidolon-v1079-5-daily-companion-backup-"))
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
    from dashboard import EidolonDashboardHandler
    from conversation_sessions import (
        append_conversation_turn,
        clear_conversation_draft,
        conversation_history_for_prompt,
        conversation_session_turns,
        create_conversation_session,
        get_active_conversation_session,
        load_conversation_draft,
        load_conversation_session,
        save_conversation_draft,
        select_conversation_session,
    )
    from dashboard_chat_console import render_realtime_chat_panel, stream_dashboard_chat_turn
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
        json.dumps({"name": "Eidolon", "mood": "steady", "active_goals": []}),
        encoding="utf-8",
    )
    modules["DESIRES_FILE"].write_text(json.dumps({"connection": 0.8}), encoding="utf-8")
    modules["MEMORY_FILE"].write_text("[]", encoding="utf-8")
    settings = deepcopy(modules["DEFAULT_SETTINGS"])
    settings["local_model_provider"] = "ollama"
    settings["local_model"] = "daily-companion-fixture-model"
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
        state: dict[str, Any] = {}

        def preview_remains_write_free() -> None:
            session_root = EXTERNAL_DATA_DIR / "conversation_sessions"
            html = modules["render_realtime_chat_panel"](None)
            assert "Drafts save per conversation" in html
            assert not session_root.exists()
        checks.append(_run_check("dashboard_preview_does_not_create_session_or_draft_runtime_data", preview_remains_write_free))

        def selected_session_survives_restart() -> None:
            first = modules["create_conversation_session"]("Morning check-in", source="fixture")
            second = modules["create_conversation_session"]("Project conversation", source="fixture")
            modules["select_conversation_session"](first["id"])
            reloaded = importlib.reload(modules["conversation_sessions"])
            resumed = reloaded.get_active_conversation_session(create_if_missing=False)
            assert resumed and resumed["id"] == first["id"]
            pointer = json.loads((EXTERNAL_DATA_DIR / "conversation_sessions" / "active_session.json").read_text(encoding="utf-8"))
            assert pointer["session_id"] == first["id"]
            state.update({"first": first, "second": second, "sessions_module": reloaded})
        checks.append(_run_check("last_selected_conversation_resumes_after_module_restart", selected_session_survives_restart))

        def latest_conversed_session_becomes_active_once() -> None:
            second = state["second"]
            modules["append_conversation_turn"](
                second["id"],
                turn_id="daily-companion-active-turn",
                user_message="Continue this project thread",
                assistant_response="Continuing here.",
                completion_state="completed",
                success=True,
            )
            reloaded = importlib.reload(state["sessions_module"])
            assert reloaded.get_active_conversation_session(create_if_missing=False)["id"] == second["id"]
            matching = [
                turn for turn in reloaded.conversation_session_turns(second["id"])
                if turn.get("id") == "daily-companion-active-turn"
            ]
            assert len(matching) == 1
        checks.append(_run_check("last_conversed_session_becomes_persisted_active_session_without_duplicate_turn", latest_conversed_session_becomes_active_once))

        def drafts_are_private_separate_and_restart_safe() -> None:
            first = state["first"]
            second = state["second"]
            modules["save_conversation_draft"](first["id"], "Call the vet tomorrow", source="fixture")
            modules["save_conversation_draft"](second["id"], "Finish the provider notes", source="fixture")
            modules["select_conversation_session"](first["id"])
            html = modules["render_realtime_chat_panel"](None)
            assert "Call the vet tomorrow" in html
            assert "Finish the provider notes" not in html
            reloaded = importlib.reload(state["sessions_module"])
            assert reloaded.load_conversation_draft(first["id"])["content"] == "Call the vet tomorrow"
            assert reloaded.load_conversation_draft(second["id"])["content"] == "Finish the provider notes"
            session = modules["load_conversation_session"](first["id"], include_turns=True)
            assert "draft" not in session and "content" not in session
        checks.append(_run_check("drafts_persist_privately_and_independently_for_each_conversation", drafts_are_private_separate_and_restart_safe))

        def duplicate_saves_are_idempotent() -> None:
            first = state["first"]
            changed = modules["save_conversation_draft"](first["id"], "A different draft", source="fixture")
            unchanged = modules["save_conversation_draft"](first["id"], "A different draft", source="fixture")
            assert changed["changed"] is True
            assert unchanged["changed"] is False
            draft_files = list((EXTERNAL_DATA_DIR / "conversation_sessions" / "drafts").glob(f"{first['id']}*.json"))
            assert len(draft_files) == 1
        checks.append(_run_check("identical_draft_save_is_idempotent_and_creates_one_record", duplicate_saves_are_idempotent))

        def stale_browser_save_cannot_resurrect_accepted_text() -> None:
            first = state["first"]
            saved = modules["save_conversation_draft"](first["id"], "Send this once", source="fixture")
            cleared = modules["clear_conversation_draft"](first["id"], source="fixture_acceptance")
            stale = modules["save_conversation_draft"](
                first["id"],
                "Send this once",
                source="late_browser_request",
                client_updated_at=saved["updated_at"],
            )
            assert cleared["has_draft"] is False
            assert stale["stale_update_ignored"] is True
            assert modules["load_conversation_draft"](first["id"])["content"] == ""
        checks.append(_run_check("accepted_message_tombstone_blocks_late_stale_draft_resurrection", stale_browser_save_cannot_resurrect_accepted_text))

        def stream_acceptance_clears_draft_and_records_one_failed_turn() -> None:
            second = state["second"]
            modules["save_conversation_draft"](second["id"], "One offline message", source="fixture")
            events = list(modules["stream_dashboard_chat_turn"](
                "One offline message",
                use_ai=False,
                session_id=second["id"],
            ))
            assert events and events[0]["event"] == "meta"
            assert modules["load_conversation_draft"](second["id"])["content"] == ""
            matching = [
                turn for turn in modules["conversation_session_turns"](second["id"])
                if turn.get("user_message") == "One offline message"
            ]
            assert len(matching) == 1
            assert matching[0]["success"] is False
            assert all(
                row["user_message"] != "One offline message"
                for row in modules["conversation_history_for_prompt"](second["id"])
            )
        checks.append(_run_check("runtime_acceptance_clears_draft_once_and_failed_turn_stays_out_of_prompt_history", stream_acceptance_clears_draft_and_records_one_failed_turn))

        def browser_crash_buffer_and_server_sync_are_visible() -> None:
            modules["select_conversation_session"](state["first"]["id"])
            html = modules["render_realtime_chat_panel"](None)
            assert "eidolon.chat.draft.v3." in html
            assert "window.localStorage.getItem(key)" in html
            assert "/api/dashboard-chat/draft" in html
            assert "client_updated_at" in html
            assert "data-server-draft-updated-at" in html
            assert "stale browser" not in html.lower()
            assert "eidolon.chat.navigation.v1" in html
            assert "window.sessionStorage.getItem(navigationStorageKey)" in html
            assert "window.sessionStorage.getItem(key)" not in html
            assert "Message accepted; draft cleared" in html
        checks.append(_run_check("browser_crash_buffer_syncs_with_private_server_draft_without_session_storage", browser_crash_buffer_and_server_sync_are_visible))

        def private_draft_http_endpoint_is_bounded_and_content_free() -> None:
            first = state["first"]
            server = ThreadingHTTPServer(("127.0.0.1", 0), modules["EidolonDashboardHandler"])
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            url = f"http://127.0.0.1:{server.server_address[1]}/api/dashboard-chat/draft"

            def post(content: str) -> tuple[int, dict[str, Any]]:
                request = urllib.request.Request(
                    url,
                    data=json.dumps({
                        "session_id": first["id"],
                        "content": content,
                        "client_updated_at": "2099-01-01T00:00:00.000Z" if content == "HTTP draft" else "",
                    }).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    return response.status, json.loads(response.read().decode("utf-8"))

            try:
                status, payload = post("HTTP draft")
                assert status == 200 and payload["ok"] is True
                assert payload["session_id"] == first["id"]
                assert "content" not in payload
                assert modules["load_conversation_draft"](first["id"])["content"] == "HTTP draft"
                try:
                    post("x" * 20_001)
                except urllib.error.HTTPError as error:
                    assert error.code == 400
                    blocked = json.loads(error.read().decode("utf-8"))
                    assert blocked["ok"] is False
                    assert "20000" in blocked["error"]
                else:
                    raise AssertionError("Oversized draft endpoint request was not rejected.")
            finally:
                server.shutdown()
                thread.join(timeout=5)
                server.server_close()
        checks.append(_run_check("private_draft_http_endpoint_saves_metadata_only_and_rejects_oversized_content", private_draft_http_endpoint_is_bounded_and_content_free))

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
        "suite": "v1079.5-daily-companion-resume-and-draft-continuity",
        "evidence_kind": "deterministic_fixture",
        "native_provider_evidence": False,
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
