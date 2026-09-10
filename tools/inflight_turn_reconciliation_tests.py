from __future__ import annotations

"""Deterministic v1079.5 in-flight turn reconciliation and leave-safety fixtures.

The suite uses an external/restored runtime data root and a simulated conversation
stream. It never contacts a provider, installs or changes a model, grants approval,
authorizes a release, or enables autonomous action.
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import threading
import time
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
    backup = Path(tempfile.mkdtemp(prefix="eidolon-v1079-5-inflight-backup-"))
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
        create_operation_marker,
        finalize_operation_marker,
        load_operation_marker,
        new_conversation_operation_id,
        operation_marker_contains_private_fields,
    )
    from conversation_sessions import (
        append_conversation_turn,
        conversation_history_for_prompt,
        conversation_session_turns,
        create_conversation_session,
        get_active_conversation_session,
        load_conversation_draft,
        save_conversation_draft,
        select_conversation_session,
    )
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
    EXTERNAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    modules["SELF_FILE"].write_text(json.dumps({"name": "Eidolon", "mood": "steady", "active_goals": []}), encoding="utf-8")
    modules["DESIRES_FILE"].write_text(json.dumps({"connection": 0.8}), encoding="utf-8")
    modules["MEMORY_FILE"].write_text("[]", encoding="utf-8")
    settings = deepcopy(modules["DEFAULT_SETTINGS"])
    settings.update({
        "local_model_provider": "ollama",
        "local_model": "inflight-fixture-model",
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


def _wait_for_terminal(console: Any, operation_id: str, timeout: float = 3.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    latest: dict[str, Any] = {}
    while time.monotonic() < deadline:
        latest = console.dashboard_chat_operation_status(operation_id=operation_id)
        marker = latest.get("operation") or {}
        if marker.get("public_state") != "running":
            return latest
        time.sleep(0.02)
    raise AssertionError(f"operation did not become terminal: {operation_id} {latest}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    backup = _snapshot_tree(EXTERNAL_DATA_DIR)
    source_before = _source_snapshot()
    checks: list[dict[str, Any]] = []
    restored = False
    restore_error = ""
    original_stream = None
    try:
        if EXTERNAL_DATA_DIR.exists():
            shutil.rmtree(EXTERNAL_DATA_DIR)
        modules = _load_modules()
        _seed_runtime(modules)
        console = modules["dashboard_chat_console"]
        operations = modules["conversation_operations"]
        original_stream = console.stream_dashboard_chat_turn
        state: dict[str, Any] = {
            "invocations": {},
            "release_late": threading.Event(),
            "release_cancel": threading.Event(),
            "release_switch": threading.Event(),
            "cancel_observed": threading.Event(),
        }

        def fake_stream(
            message: str,
            *,
            use_ai: bool = True,
            cancel_event: threading.Event | None = None,
            session_id: str = "",
            operation_id: str = "",
            draft_already_cleared: bool = False,
        ):
            state["invocations"][operation_id] = state["invocations"].get(operation_id, 0) + 1
            yield {
                "event": "meta", "operation_id": operation_id, "session_id": session_id,
                "provider": "fixture", "model": "fixture-model", "streaming": True,
            }
            completion_state = "completed"
            success = True
            failure_category = ""
            response = "Eidolon: completed once"
            if message == "late-complete":
                state["release_late"].wait(3)
            elif message == "switch-late":
                state["release_switch"].wait(3)
            elif message == "cancel-me":
                while not (cancel_event and cancel_event.is_set()):
                    time.sleep(0.01)
                state["cancel_observed"].set()
                state["release_cancel"].wait(3)
                completion_state = "cancelled"
                success = False
                failure_category = "cancelled"
                response = "Cancelled safely."
            elif message == "fail-me":
                completion_state = "failed"
                success = False
                failure_category = "timeout"
                response = "The turn stopped safely."
            elif message == "duplicate-done":
                response = "Eidolon: duplicate delivery remained one turn"
            modules["append_conversation_turn"](
                session_id,
                turn_id=operation_id,
                user_message=message,
                assistant_response=response,
                completion_state=completion_state,
                success=success,
                failure_category=failure_category,
                provider="fixture",
                model="fixture-model",
                streaming=True,
                diagnostic={"code": failure_category, "provider": "fixture", "model": "fixture-model", "redacted": True}
                if not success else None,
                select_session=False,
            )
            result = {
                "operation_id": operation_id,
                "session_id": session_id,
                "success": success,
                "completion_state": completion_state,
                "failure_category": failure_category,
                "session_turn_recorded": True,
                "provider": "fixture",
                "model": "fixture-model",
            }
            turn = {"id": f"dashboard-{operation_id}", "conversation_runtime": result}
            yield {"event": "done", "operation_id": operation_id, "turn": turn}
            if message == "duplicate-done":
                yield {"event": "done", "operation_id": operation_id, "turn": turn}

        console.stream_dashboard_chat_turn = fake_stream

        def marker_is_bounded_public_and_text_free() -> None:
            session = modules["create_conversation_session"]("Marker privacy", source="fixture")
            operation_id = modules["new_conversation_operation_id"]()
            marker = modules["create_operation_marker"](
                operation_id, session["id"], acceptance_key="fixture-acceptance-key"
            )
            assert marker["public_state"] == "running" and marker["redacted"] is True
            assert modules["operation_marker_contains_private_fields"](marker) is False
            encoded = json.dumps(marker).lower()
            for forbidden in ("user_message", "assistant_response", "prompt", "partial_tokens", "receipt_path", "traceback"):
                assert forbidden not in encoded
            marker_path = operations.CONVERSATION_OPERATION_DIR / f"{operation_id}.json"
            assert marker_path.exists() and modules["operation_marker_contains_private_fields"](json.loads(marker_path.read_text())) is False
            try:
                modules["create_operation_marker"](
                    modules["new_conversation_operation_id"](), session["id"], acceptance_key="message text must not persist"
                )
            except ValueError:
                pass
            else:
                raise AssertionError("free-form acceptance keys must fail closed")
            state["privacy_session"] = session
        checks.append(_run_check("accepted_operation_marker_is_atomic_bounded_and_contains_no_private_turn_content", marker_is_bounded_public_and_text_free))

        def duplicate_marker_and_terminal_packets_are_idempotent() -> None:
            session = state["privacy_session"]
            operation_id = modules["new_conversation_operation_id"]()
            first = modules["create_operation_marker"](operation_id, session["id"], acceptance_key="same-key")
            second = modules["create_operation_marker"](operation_id, session["id"], acceptance_key="different-key")
            assert first == second
            completed = modules["finalize_operation_marker"](
                operation_id, completion_state="completed", success=True, final_session_turn_recorded=True
            )
            duplicate = modules["finalize_operation_marker"](
                operation_id, completion_state="failed", success=False, failure_category="timeout"
            )
            assert completed["public_state"] == "completed"
            assert duplicate["public_state"] == "completed" and duplicate["failure_category"] == ""
        checks.append(_run_check("duplicate_marker_creation_and_completion_delivery_cannot_overwrite_terminal_truth", duplicate_marker_and_terminal_packets_are_idempotent))

        def refresh_during_active_turn_does_not_resubmit() -> None:
            session = modules["create_conversation_session"]("Refresh active", source="fixture")
            modules["save_conversation_draft"](session["id"], "late-complete", source="fixture")
            barrier = threading.Barrier(3)
            accepted_rows: list[dict[str, Any]] = []
            errors: list[BaseException] = []

            def accept_once() -> None:
                try:
                    barrier.wait(timeout=2)
                    accepted_rows.append(console.start_dashboard_chat_operation(
                        "late-complete", session_id=session["id"], acceptance_key="refresh-key"
                    ))
                except BaseException as error:
                    errors.append(error)

            threads = [threading.Thread(target=accept_once) for _ in range(2)]
            for thread in threads:
                thread.start()
            barrier.wait(timeout=2)
            for thread in threads:
                thread.join(timeout=3)
            assert not errors and len(accepted_rows) == 2
            operation_ids = {row["operation"]["operation_id"] for row in accepted_rows}
            assert len(operation_ids) == 1
            operation_id = next(iter(operation_ids))
            assert sorted(bool(row["duplicate_acceptance"]) for row in accepted_rows) == [False, True]
            deadline = time.monotonic() + 2
            while state["invocations"].get(operation_id) != 1 and time.monotonic() < deadline:
                time.sleep(0.01)
            assert state["invocations"].get(operation_id) == 1
            status_a = console.dashboard_chat_operation_status(operation_id=operation_id)
            status_b = console.dashboard_chat_operation_status(operation_id=operation_id)
            by_key = console.dashboard_chat_operation_status(session_id=session["id"], acceptance_key="refresh-key")
            assert status_a["operation"]["public_state"] == status_b["operation"]["public_state"] == "running"
            assert by_key["operation"]["operation_id"] == operation_id
            assert modules["load_conversation_draft"](session["id"])["content"] == ""
            state["late_session"] = session
            state["late_operation"] = operation_id
        checks.append(_run_check("refresh_and_duplicate_acceptance_reconcile_one_running_operation_without_provider_replay", refresh_during_active_turn_does_not_resubmit))

        def disconnected_viewer_allows_late_completion_once() -> None:
            operation_id = state["late_operation"]
            session = state["late_session"]
            console.detach_dashboard_chat_operation(operation_id)
            running = console.dashboard_chat_operation_status(operation_id=operation_id)
            assert running["operation"]["public_state"] == "running"
            assert running["operation"]["client_disconnected"] is True
            state["release_late"].set()
            terminal = _wait_for_terminal(console, operation_id)
            acknowledged = console.dashboard_chat_operation_status(operation_id=operation_id)
            marker = acknowledged["operation"]
            assert marker["public_state"] == "completed"
            assert marker["client_disconnected"] is True and marker["reconciled_late"] is True
            assert marker["final_session_turn_recorded"] is True
            turns = modules["conversation_session_turns"](session["id"])
            assert [turn["id"] for turn in turns].count(operation_id) == 1
            assert terminal["session_turn"]["assistant_response"] == "Eidolon: completed once"
            assert state["invocations"].get(operation_id) == 1
        checks.append(_run_check("browser_detach_never_cancels_and_late_completion_attaches_exactly_once", disconnected_viewer_allows_late_completion_once))

        def duplicate_status_polling_never_duplicates_turn_or_memory() -> None:
            operation_id = state["late_operation"]
            session = state["late_session"]
            before_turns = len(modules["conversation_session_turns"](session["id"]))
            before_memories = len(modules["load_memories"]())
            marker_path = operations.CONVERSATION_OPERATION_DIR / f"{operation_id}.json"
            marker_before = marker_path.read_bytes()
            for _ in range(6):
                payload = console.dashboard_chat_operation_status(operation_id=operation_id)
                assert payload["operation"]["public_state"] == "completed"
            assert marker_path.read_bytes() == marker_before
            assert len(modules["conversation_session_turns"](session["id"])) == before_turns
            assert len(modules["load_memories"]()) == before_memories
        checks.append(_run_check("repeated_reconciliation_polling_is_read_only_and_nonduplicating", duplicate_status_polling_never_duplicates_turn_or_memory))

        def newer_draft_and_other_session_draft_survive_late_completion() -> None:
            first = modules["create_conversation_session"]("Draft A", source="fixture")
            second = modules["create_conversation_session"]("Draft B", source="fixture")
            modules["save_conversation_draft"](first["id"], "accepted text", source="fixture")
            modules["save_conversation_draft"](second["id"], "unrelated draft", source="fixture")
            accepted = console.start_dashboard_chat_operation("duplicate-done", session_id=first["id"], acceptance_key="draft-key")
            operation_id = accepted["operation"]["operation_id"]
            modules["save_conversation_draft"](first["id"], "newer message typed while responding", source="fixture")
            _wait_for_terminal(console, operation_id)
            assert modules["load_conversation_draft"](first["id"])["content"] == "newer message typed while responding"
            assert modules["load_conversation_draft"](second["id"])["content"] == "unrelated draft"
            assert len([turn for turn in modules["conversation_session_turns"](first["id"]) if turn["id"] == operation_id]) == 1
            assert state["invocations"].get(operation_id) == 1
        checks.append(_run_check("accepted_tombstone_never_clears_a_newer_draft_or_another_sessions_draft", newer_draft_and_other_session_draft_survive_late_completion))

        def failure_reconciles_without_prompt_or_memory_promotion() -> None:
            session = modules["create_conversation_session"]("Failure return", source="fixture")
            before_memories = len(modules["load_memories"]())
            accepted = console.start_dashboard_chat_operation("fail-me", session_id=session["id"], acceptance_key="failure-key")
            operation_id = accepted["operation"]["operation_id"]
            terminal = _wait_for_terminal(console, operation_id)
            assert terminal["operation"]["public_state"] == "failed"
            assert terminal["operation"]["failure_category"] == "timeout"
            assert terminal["session_turn"]["success"] is False
            assert modules["conversation_history_for_prompt"](session["id"]) == []
            assert len(modules["load_memories"]()) == before_memories
        checks.append(_run_check("failed_late_result_remains_visible_but_excluded_from_prompt_history_and_memory", failure_reconciles_without_prompt_or_memory_promotion))

        def repeated_cancellation_is_exact_and_idempotent() -> None:
            session = modules["create_conversation_session"]("Cancel return", source="fixture")
            accepted = console.start_dashboard_chat_operation("cancel-me", session_id=session["id"], acceptance_key="cancel-key")
            operation_id = accepted["operation"]["operation_id"]
            first = console.cancel_dashboard_chat_operation(operation_id)
            assert first["ok"] is True and first["status"] == "cancellation_requested"
            assert state["cancel_observed"].wait(2)
            second = console.cancel_dashboard_chat_operation(operation_id)
            assert second["ok"] is True and second["duplicate_request"] is True
            state["release_cancel"].set()
            terminal = _wait_for_terminal(console, operation_id)
            assert terminal["operation"]["public_state"] == "cancelled"
            assert terminal["operation"]["cancellation_requested"] is True
            assert modules["conversation_history_for_prompt"](session["id"]) == []
            assert len([turn for turn in modules["conversation_session_turns"](session["id"]) if turn["id"] == operation_id]) == 1
        checks.append(_run_check("repeated_cancel_targets_one_exact_operation_and_commits_one_cancelled_turn", repeated_cancellation_is_exact_and_idempotent))

        def completed_response_wins_over_late_cancellation() -> None:
            session = modules["create_conversation_session"]("Completion wins", source="fixture")
            accepted = console.start_dashboard_chat_operation("complete-first", session_id=session["id"], acceptance_key="completion-key")
            operation_id = accepted["operation"]["operation_id"]
            terminal = _wait_for_terminal(console, operation_id)
            assert terminal["operation"]["public_state"] == "completed"
            cancelled = console.cancel_dashboard_chat_operation(operation_id)
            assert cancelled["ok"] is False and cancelled["status"] == "completed"
            assert console.dashboard_chat_operation_status(operation_id=operation_id)["operation"]["public_state"] == "completed"
        checks.append(_run_check("completed_response_remains_completed_when_cancellation_arrives_too_late", completed_response_wins_over_late_cancellation))

        def process_restart_orphan_becomes_uncertain_not_cancelled() -> None:
            session = modules["create_conversation_session"]("Orphan", source="fixture")
            operation_id = modules["new_conversation_operation_id"]()
            modules["create_operation_marker"](operation_id, session["id"], acceptance_key="orphan-key")
            status = console.dashboard_chat_operation_status(operation_id=operation_id)
            assert status["operation"]["public_state"] == "uncertain"
            assert status["operation"]["failure_category"] == "runtime_status_unknown_after_restart"
            assert status["operation"]["cancellation_requested"] is False
            assert status["session_turn"] is None
        checks.append(_run_check("orphaned_running_marker_after_restart_becomes_uncertain_without_fake_cancellation", process_restart_orphan_becomes_uncertain_not_cancelled))

        def late_completion_does_not_steal_newer_session_selection() -> None:
            first = modules["create_conversation_session"]("Running session", source="fixture")
            second = modules["create_conversation_session"]("Newly selected session", source="fixture")
            modules["select_conversation_session"](first["id"])
            accepted = console.start_dashboard_chat_operation("switch-late", session_id=first["id"], acceptance_key="switch-key")
            operation_id = accepted["operation"]["operation_id"]
            modules["select_conversation_session"](second["id"])
            state["release_switch"].set()
            terminal = _wait_for_terminal(console, operation_id)
            assert terminal["operation"]["public_state"] == "completed"
            assert terminal["session_turn"]["id"] == operation_id
            active = modules["get_active_conversation_session"](create_if_missing=False) or {}
            assert active.get("id") == second["id"]
            assert len([turn for turn in modules["conversation_session_turns"](first["id"]) if turn["id"] == operation_id]) == 1
            assert modules["conversation_session_turns"](second["id"]) == []
        checks.append(_run_check("late_completion_updates_its_own_session_without_stealing_a_newer_selection", late_completion_does_not_steal_newer_session_selection))

        def session_selection_and_provider_settings_contract_remain_unchanged() -> None:
            session = modules["create_conversation_session"]("Selection", source="fixture")
            modules["select_conversation_session"](session["id"])
            modules["save_conversation_draft"](session["id"], "provider settings draft", source="fixture")
            html = console.render_realtime_chat_panel(None)
            assert "/local-model?return_to=chat#local-model-config-form" in html
            assert "await persistDraft({ sessionId:targetSessionId" in html
            assert "await persistPresentation({ sessionId:targetSessionId" in html
            assert modules["load_conversation_draft"](session["id"])["content"] == "provider settings draft"
        checks.append(_run_check("provider_settings_navigation_still_preserves_selected_session_and_private_draft", session_selection_and_provider_settings_contract_remain_unchanged))

        def ordinary_chat_uses_calm_states_and_progressive_reconciliation_details() -> None:
            session = modules["create_conversation_session"]("Disclosure", source="fixture")
            modules["select_conversation_session"](session["id"])
            operation_id = modules["new_conversation_operation_id"]()
            modules["create_operation_marker"](operation_id, session["id"], acceptance_key="disclosure-key")
            # Treat the marker as active for the render so it is not orphan-reclassified.
            dummy = console._DashboardOperationJob(operation_id=operation_id, session_id=session["id"], turn_id="fixture")
            with console._DASHBOARD_OPERATION_LOCK:
                console._DASHBOARD_OPERATION_JOBS[operation_id] = dummy
            try:
                html = console.render_realtime_chat_panel(None)
            finally:
                dummy.done = True
                console._discard_dashboard_operation_job(operation_id)
            dashboard_source = (AGENT / "dashboard.py").read_text(encoding="utf-8")
            assert "Eidolon is still responding. Refreshing will not submit it again." in html
            assert "The reply completed while you were away and was attached once." in html
            assert "The connection ended before completion could be confirmed." in html
            assert "Reconciliation details" in html
            assert "This marker contains no message text" in html
            assert "boundedControlFetch('/api/dashboard-chat/stream'" in html
            assert "pollOperation(initialOperation.operation_id)" in html
            assert "async function activateCurrentBrowserTab()" in html
            assert "postCoordination('activate')" in html
            assert 'elif action == "activate":' in dashboard_source
            assert "force=True" in dashboard_source
            assert "reply.textContent = 'Thinking...'" in html
            assert "if (!existingReply || existingReply.dataset.reconciliationPending !== 'true') return;" not in html
            assert "body: JSON.stringify(Object.assign({" in html and "message: message" in html
            assert html.count("boundedControlFetch('/api/dashboard-chat/stream'") == 1
        checks.append(_run_check("ordinary_chat_has_calm_running_late_complete_uncertain_states_with_details_disclosed", ordinary_chat_uses_calm_states_and_progressive_reconciliation_details))

        def http_status_endpoint_returns_marker_plus_persisted_turn_not_receipt() -> None:
            session = modules["create_conversation_session"]("HTTP status", source="fixture")
            accepted = console.start_dashboard_chat_operation("complete-first", session_id=session["id"], acceptance_key="http-key")
            operation_id = accepted["operation"]["operation_id"]
            _wait_for_terminal(console, operation_id)
            server = ThreadingHTTPServer(("127.0.0.1", 0), modules["dashboard"].EidolonDashboardHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f"http://127.0.0.1:{server.server_port}/api/dashboard-chat/operation?operation_id={operation_id}"
                with urllib.request.urlopen(url, timeout=4) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                assert payload["ok"] is True and payload["operation"]["public_state"] == "completed"
                assert payload["session_turn"]["id"] == operation_id
                encoded_marker = json.dumps(payload["operation"]).lower()
                assert "user_message" not in encoded_marker and "assistant_response" not in encoded_marker
                assert "receipt" not in encoded_marker and "traceback" not in encoded_marker
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)
        checks.append(_run_check("localhost_status_endpoint_reconciles_from_marker_and_session_turn_without_receipts", http_status_endpoint_returns_marker_plus_persisted_turn_not_receipt))

        def package_inventory_excludes_runtime_operations_and_private_state() -> None:
            from package_integrity import iter_source_tree_entries
            entries = list(iter_source_tree_entries(ROOT))
            forbidden = (
                "data/conversation_runtime/operations/", "data/conversation_sessions/",
                "data/dashboard_chat/", "data/memories.json", "data/projects.json",
            )
            assert not any(any(entry.startswith(prefix) for prefix in forbidden) for entry in entries)
            assert not any(entry.endswith((".zip", ".pyc")) or "/__pycache__/" in entry for entry in entries)
        checks.append(_run_check("source_package_inventory_excludes_operation_markers_sessions_drafts_and_private_runtime_state", package_inventory_excludes_runtime_operations_and_private_state))

        def governance_and_no_automatic_replay_tokens_remain_explicit() -> None:
            source = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
            dashboard_source = (AGENT / "dashboard.py").read_text(encoding="utf-8")
            runtime = (AGENT / "conversation_runtime.py").read_text(encoding="utf-8")
            assert "viewer connection lifetime" not in source  # implementation is behavior, not a fake slogan
            assert "No automatic retry or duplicate submission occurred." in source
            assert "Nothing was resubmitted or silently cancelled." in source
            operation_source = (AGENT / "conversation_operations.py").read_text(encoding="utf-8").lower()
            assert "install models" not in operation_source and "provider payloads" in operation_source
            stream_block = dashboard_source.split('if parsed.path == "/api/dashboard-chat/stream":', 1)[1].split('if parsed.path == "/api"', 1)[0]
            assert "detach_dashboard_chat_operation(operation_id)" in stream_block
            assert "cancel_event.set()" not in stream_block
            assert "fallback_used: bool = False" in runtime
            assert '"model_management_performed": False' in runtime
        checks.append(_run_check("no_auto_retry_fallback_model_management_or_governance_expansion_was_added", governance_and_no_automatic_replay_tokens_remain_explicit))

    finally:
        if original_stream is not None:
            try:
                modules["dashboard_chat_console"].stream_dashboard_chat_turn = original_stream
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
        "suite": "inflight_turn_reconciliation_and_leave_safety",
        "ok": passed == len(checks),
        "passed": passed,
        "total": len(checks),
        "checks": checks,
        "native_provider_contacted": False,
        "model_management_performed": False,
        "automatic_replay_performed": False,
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
