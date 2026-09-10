from __future__ import annotations

"""Deterministic v1079.5 provider-readiness and offline-recovery fixtures.

The suite uses isolated/restored runtime data and simulated provider failures. It
never contacts a native provider, manages model files, switches provider profiles,
grants approvals, authorizes a release, or expands autonomy.
"""

import argparse
import json
import os
import shutil
import sys
import tempfile
import traceback
import re
import threading
import urllib.request
from copy import deepcopy
from html.parser import HTMLParser
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
sys.path.insert(0, str(AGENT))
EXTERNAL_DATA_DIR = Path(os.environ.get("EIDOLON_DATA_DIR") or (ROOT / "data")).resolve()


class _DisclosureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.details_depth = 0
        self.outside_details: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "details":
            self.details_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "details" and self.details_depth:
            self.details_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.details_depth:
            self.outside_details.append(data)


class _TitleAttributeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(); self.has_title = False
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if any(str(name).lower() == "title" for name, _value in attrs): self.has_title = True


def _snapshot_tree(root: Path) -> Path:
    backup = Path(tempfile.mkdtemp(prefix="eidolon-v1079-5-provider-recovery-backup-"))
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
    import dashboard
    import dashboard_chat_console
    import dashboard_local_model
    from conversation_experience import (
        normalize_failure_category,
        redacted_turn_diagnostics,
        turn_experience_state,
    )
    from conversation_recovery import ConversationRecoveryError, recovery_state, retry_failed_conversation_turn
    from conversation_operations import create_operation_marker, finalize_operation_marker, new_conversation_operation_id
    from conversation_sessions import (
        append_conversation_turn,
        conversation_history_for_prompt,
        conversation_session_turns,
        create_conversation_session,
        load_conversation_draft,
        load_conversation_session,
        save_conversation_draft,
        select_conversation_session,
        session_contains_private_receipt_fields,
    )
    from dashboard_chat_console import render_realtime_chat_panel
    from local_model import UnavailableServiceError
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
    modules["SELF_FILE"].write_text(
        json.dumps({"name": "Eidolon", "mood": "steady", "active_goals": []}), encoding="utf-8"
    )
    modules["DESIRES_FILE"].write_text(json.dumps({"connection": 0.8}), encoding="utf-8")
    modules["MEMORY_FILE"].write_text("[]", encoding="utf-8")
    settings = deepcopy(modules["DEFAULT_SETTINGS"])
    settings.update({
        "local_model_provider": "ollama",
        "local_model": "provider-recovery-fixture-model",
        "local_model_endpoint": "http://localhost:11434",
        "ai_chat_enabled": True,
    })
    modules["save_settings"](settings)


def _run_check(name: str, function: Callable[[], None]) -> dict[str, Any]:
    try:
        function()
        return {"name": name, "status": "pass"}
    except Exception as error:
        return {"name": name, "status": "fail", "error": f"{type(error).__name__}: {error}", "traceback": traceback.format_exc()}


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

        def required_states_are_distinct_and_calm() -> None:
            cases = {
                "ai_disabled": ("offline", "Local generation is off"),
                "unavailable_service": ("offline", "Eidolon cannot reach the local service"),
                "missing_model": ("offline", "The selected model is unavailable"),
                "invalid_configuration": ("attention", "Local generation needs attention"),
                "timeout": ("attention", "Eidolon took too long"),
                "interrupted_stream": ("disconnected", "The reply was interrupted"),
                "cancelled": ("cancelled", "Cancelled safely"),
            }
            for category, expected in cases.items():
                view = modules["turn_experience_state"]({
                    "success": False, "completion_state": "cancelled" if category == "cancelled" else "failed",
                    "failure_category": category, "user_message": "fixture",
                })
                assert (view.state, view.label) == expected
                assert "stack" not in view.detail.lower() and "trace" not in view.detail.lower()
            recovered = modules["turn_experience_state"]({
                "success": True, "completion_state": "completed", "recovery_of": "source-turn",
            })
            assert recovered.state == "recovered" and recovered.label == "Recovered successfully"
        checks.append(_run_check("all_required_provider_offline_cancel_and_recovery_states_are_distinct", required_states_are_distinct_and_calm))

        def historical_aliases_map_to_current_contract() -> None:
            expected = {
                "provider_unavailable": "unavailable_service",
                "provider_disconnect": "interrupted_stream",
                "model_unavailable": "missing_model",
                "empty_output": "empty_response",
                "memory_write_failed": "memory_write_failure",
            }
            for old, new in expected.items():
                assert modules["normalize_failure_category"](old) == new
        checks.append(_run_check("historical_failure_aliases_render_through_one_current_contract", historical_aliases_map_to_current_contract))

        def persisted_diagnostics_are_bounded_and_redacted() -> None:
            session = modules["create_conversation_session"]("Diagnostic privacy", source="fixture")
            turn_id = modules["new_conversation_operation_id"]()
            modules["create_operation_marker"](
                turn_id, session["id"], acceptance_key="fixture_diagnostic_acceptance", streaming=True,
            )
            modules["append_conversation_turn"](
                session["id"], turn_id=turn_id, user_message="Please answer",
                assistant_response="raw provider wording must not lead", completion_state="failed", success=False,
                failure_category="unavailable_service", provider="ollama", model="fixture-model",
                diagnostic={
                    "code": "unavailable_service", "provider": "ollama", "model": "fixture-model",
                    "endpoint": "http://operator:secret@localhost:11434/api/generate?token=hunter2#private",
                    "retryable": True, "status_code": 503,
                    "details": {"failure_kind": "connection", "exception_type": "ConnectError", "raw_body": "PRIVATE PROMPT"},
                    "raw_response": "PRIVATE RESPONSE", "traceback": "SECRET TRACE",
                },
            )
            modules["finalize_operation_marker"](
                turn_id, completion_state="failed", success=False,
                failure_category="unavailable_service", final_session_turn_recorded=True,
            )
            stored = modules["conversation_session_turns"](session["id"])[0]
            diagnostic = stored["diagnostic"]
            encoded = json.dumps(diagnostic)
            assert diagnostic["endpoint"] == "http://localhost:11434/api/generate"
            assert diagnostic["technical_category"] == "unavailable_service"
            assert diagnostic["status_code"] == 503 and diagnostic["retryable"] is True
            for forbidden in ("secret", "hunter2", "PRIVATE", "TRACE", "raw_body", "raw_response"):
                assert forbidden not in encoded
            assert modules["session_contains_private_receipt_fields"](
                modules["load_conversation_session"](session["id"], include_turns=True)
            ) is False
            state["diagnostic_session"] = session
            state["diagnostic_turn_id"] = turn_id
        checks.append(_run_check("session_turn_diagnostics_whitelist_endpoint_and_evidence_without_secrets", persisted_diagnostics_are_bounded_and_redacted))

        def ordinary_chat_hides_provider_details_until_disclosure() -> None:
            session = state["diagnostic_session"]
            modules["select_conversation_session"](session["id"])
            html = modules["render_realtime_chat_panel"](None)
            parser = _DisclosureParser()
            parser.feed(html)
            outside = " ".join(parser.outside_details)
            assert "Eidolon cannot reach the local service" in outside
            assert "raw provider wording must not lead" not in html
            assert "fixture-model" not in outside
            assert "http://localhost:11434/api/generate" not in outside
            assert "chat-provider-pill" not in html
            assert "Technical details" in html
            assert "Open provider settings" in html
            state["failed_html"] = html
        checks.append(_run_check("provider_model_endpoint_and_category_remain_inside_progressive_disclosure", ordinary_chat_hides_provider_details_until_disclosure))

        def recovery_choices_are_explicit_and_nonduplicating() -> None:
            html = state["failed_html"]
            turn_id = state["diagnostic_turn_id"]
            assert html.count("name='turn_id' value='" + turn_id + "'") == 1
            assert html.count("Run explicit linked recovery") >= 1
            assert html.count("data-turn-id='" + turn_id + "'") == 1
            assert "name='recovery_token'" in html
            assert "Open provider settings" in html
            assert "Continue without local generation" in html
            assert "automatic retry" in html.lower() or "no automatic retry" in html.lower()
            assert "dashboard_chat_turn_regenerate" not in html
        checks.append(_run_check("failed_turn_exposes_one_retry_settings_and_offline_choice_without_regenerate", recovery_choices_are_explicit_and_nonduplicating))

        def deliberate_offline_mode_does_not_offer_retry() -> None:
            session = modules["create_conversation_session"]("Offline organization", source="fixture")
            modules["append_conversation_turn"](
                session["id"], turn_id="offline-source", user_message="Store this locally",
                assistant_response="Local generation is disabled.", completion_state="ai_disabled", success=False,
                failure_category="ai_disabled", provider="ollama", model="fixture-model",
            )
            modules["select_conversation_session"](session["id"])
            html = modules["render_realtime_chat_panel"](None)
            turn_segment = html[html.index("offline-source") if "offline-source" in html else 0:]
            assert "Local generation is off" in html
            assert "Continue without local generation" in html
            assert "name='turn_id' value='offline-source'" not in html
            assert "Open provider settings" not in turn_segment.split("<details class='chat-diagnostics-drawer'", 1)[0]
        checks.append(_run_check("deliberate_local_generation_off_is_not_misrepresented_as_provider_failure", deliberate_offline_mode_does_not_offer_retry))

        def runtime_failure_records_safe_diagnostic_once() -> None:
            session = modules["create_conversation_session"]("Runtime failure", source="fixture")
            runtime = modules["conversation_runtime"]

            class FailingClient:
                last_retry_count = 0
                def __init__(self, config: Any, cancel_event: Any = None) -> None:
                    self.config = config
                def generate(self, prompt: str) -> str:
                    raise modules["UnavailableServiceError"](
                        "provider body included private prompt", provider=self.config.provider,
                        endpoint=self.config.endpoint, model=self.config.model, retryable=True,
                        details={"failure_kind": "connection", "exception_type": "ConnectionError", "raw_body": prompt},
                    )
                def cancel(self) -> None: return None
                def close(self) -> None: return None

            operation_id = modules["new_conversation_operation_id"]()
            modules["create_operation_marker"](
                operation_id, session["id"], acceptance_key="fixture_runtime_acceptance", streaming=False,
            )
            original = runtime.LocalModelClient
            runtime.LocalModelClient = FailingClient
            try:
                result = runtime.run_conversation_turn(
                    "One accepted failure", session_id=session["id"], source="fixture", operation_id=operation_id,
                )
            finally:
                runtime.LocalModelClient = original
            modules["finalize_operation_marker"](
                operation_id, completion_state=result.completion_state, success=result.success,
                failure_category=result.failure_category, final_session_turn_recorded=result.session_turn_recorded,
            )
            turns = modules["conversation_session_turns"](session["id"])
            assert result.success is False and result.failure_category == "unavailable_service"
            assert len([turn for turn in turns if turn.get("id") == result.operation_id]) == 1
            diagnostic = modules["redacted_turn_diagnostics"](turns[-1])
            assert diagnostic["technical_category"] == "unavailable_service"
            assert diagnostic["endpoint"] == "http://localhost:11434"
            assert "private prompt" not in json.dumps(turns[-1])
            assert modules["conversation_history_for_prompt"](session["id"]) == []
            state["runtime_failure"] = (session, result)
        checks.append(_run_check("runtime_provider_failure_persists_one_redacted_turn_and_no_prompt_history", runtime_failure_records_safe_diagnostic_once))

        def successful_retry_is_linked_committed_and_blocked_from_duplicate() -> None:
            session, failed = state["runtime_failure"]
            runtime = modules["conversation_runtime"]
            def stable_memories():
                import time
                previous = deepcopy(modules["load_memories"]())
                for _ in range(20):
                    time.sleep(0.025)
                    current = deepcopy(modules["load_memories"]())
                    if current == previous:
                        return current
                    previous = current
                return previous

            class RecoveryClient:
                last_retry_count = 0
                def __init__(self, config: Any, cancel_event: Any = None) -> None: self.config = config
                def generate(self, prompt: str) -> str: return "Recovered response"
                def cancel(self) -> None: return None
                def close(self) -> None: return None

            recovery = modules["recovery_state"](session["id"], failed.operation_id)
            assert recovery["acceptance_proven"] is True and recovery["recovery_cue_token"]
            original = runtime.LocalModelClient
            runtime.LocalModelClient = RecoveryClient
            try:
                recovered = modules["retry_failed_conversation_turn"](
                    session["id"], failed.operation_id, source="fixture_recovery",
                    expected_recovery_cue=recovery["recovery_cue_token"],
                )
            finally:
                runtime.LocalModelClient = original
            assert recovered.success and recovered.recovery_of == failed.operation_id
            before_turns = deepcopy(modules["conversation_session_turns"](session["id"]))
            before_memories = stable_memories()
            try:
                modules["retry_failed_conversation_turn"](session["id"], failed.operation_id)
                raise AssertionError("duplicate recovery unexpectedly ran")
            except modules["ConversationRecoveryError"]:
                pass
            assert modules["conversation_session_turns"](session["id"]) == before_turns
            assert stable_memories() == before_memories
            history = modules["conversation_history_for_prompt"](session["id"])
            assert len(history) == 1 and history[0]["assistant_response"].endswith("Recovered response")
            modules["select_conversation_session"](session["id"])
            html = modules["render_realtime_chat_panel"](None)
            assert "Recovered successfully" in html
            source_start = html.index("Recovered successfully in a later linked turn")
            assert "name='turn_id' value='" + failed.operation_id + "'" not in html[source_start:]
        checks.append(_run_check("successful_recovery_commits_once_reuses_memory_and_blocks_duplicate_replay", successful_retry_is_linked_committed_and_blocked_from_duplicate))

        def live_stream_contract_uses_calm_copy_and_idempotent_action_rows() -> None:
            html = state["failed_html"]
            assert "const failureCopy" in html and "applyFailurePresentation" in html
            assert "appendRecoveryActions(result)" in html
            assert "if (existingRow) existingRow.remove();" in html
            assert "recovery.recovery_cue_token" in html
            assert "Refresh recovery state" in html
            assert "payload.message || 'The failed turn" not in html
            assert "providerPill" not in html
            assert "if (!turnIsCurrent || reply.dataset.failureCategory) continue;" in html
        checks.append(_run_check("live_stream_failures_share_calm_contract_and_create_actions_once", live_stream_contract_uses_calm_copy_and_idempotent_action_rows))

        def settings_round_trip_preserves_selected_session_and_draft() -> None:
            session = modules["create_conversation_session"]("Settings round trip", source="fixture")
            modules["select_conversation_session"](session["id"])
            modules["save_conversation_draft"](session["id"], "Keep this exact draft", source="fixture")
            before_session = modules["load_conversation_session"](session["id"], include_turns=True)
            before_draft = modules["load_conversation_draft"](session["id"])
            local_page = modules["dashboard_local_model"]
            original_status = local_page.local_model_status
            original_payload = local_page.configuration_payload
            local_page.local_model_status = lambda: {
                "provider": "ollama", "status": "unavailable", "endpoint": "http://localhost:11434",
                "service_available": False, "embedding_service_available": False,
                "configured_model": "provider-recovery-fixture-model", "model_available": False,
                "configured_embed_model": "fixture-embed", "embed_model_available": False,
                "generation": {}, "models": [], "embedding_models": [],
            }
            local_page.configuration_payload = lambda: {
                "values": modules["load_settings"](), "provider_profiles": {}, "effective_embedding_endpoint": "",
            }
            try:
                html = local_page.render_local_model_status(
                    safe=lambda value: str(value),
                    card=lambda title, body: f"<section><h2>{title}</h2>{body}</section>",
                    layout=lambda path, body: body,
                    return_to_chat=True,
                )
            finally:
                local_page.local_model_status = original_status
                local_page.configuration_payload = original_payload
            assert "Return to Eidolon" in html and "private draft were left unchanged" in html
            assert modules["load_conversation_session"](session["id"], include_turns=True) == before_session
            assert modules["load_conversation_draft"](session["id"]) == before_draft
            chat_html = modules["render_realtime_chat_panel"](None)
            assert "await persistDraft({ sessionId:targetSessionId" in chat_html
            assert "await persistPresentation({ sessionId:targetSessionId" in chat_html
            assert "window.location.assign(link.href)" in chat_html
        checks.append(_run_check("opening_and_returning_from_provider_settings_preserves_session_and_draft", settings_round_trip_preserves_selected_session_and_draft))

        def provider_settings_return_query_is_wired_without_mutation() -> None:
            session = modules["create_conversation_session"]("Settings HTTP return", source="fixture")
            modules["select_conversation_session"](session["id"])
            modules["save_conversation_draft"](session["id"], "Unsaved before settings route", source="fixture")
            before_session = modules["load_conversation_session"](session["id"], include_turns=True)
            before_draft = modules["load_conversation_draft"](session["id"])
            dashboard_module = modules["dashboard"]
            original_renderer = dashboard_module.render_local_model_status
            observed: list[bool] = []

            def bounded_renderer(*, return_to_chat: bool = False) -> str:
                observed.append(return_to_chat)
                return "<html><body>RETURN_TO_CHAT_TRUE</body></html>"

            dashboard_module.render_local_model_status = bounded_renderer
            server = ThreadingHTTPServer(("127.0.0.1", 0), dashboard_module.EidolonDashboardHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f"http://127.0.0.1:{server.server_address[1]}/local-model?return_to=chat"
                with urllib.request.urlopen(url, timeout=5) as response:
                    body = response.read().decode("utf-8")
                    assert response.status == 200
                assert "RETURN_TO_CHAT_TRUE" in body
                assert observed == [True]
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)
                dashboard_module.render_local_model_status = original_renderer
            assert modules["load_conversation_session"](session["id"], include_turns=True) == before_session
            assert modules["load_conversation_draft"](session["id"]) == before_draft
        checks.append(_run_check("provider_settings_return_query_reaches_renderer_without_session_or_draft_mutation", provider_settings_return_query_is_wired_without_mutation))

        def privacy_and_governance_boundaries_remain_explicit() -> None:
            html = state["failed_html"]
            lowered = html.lower()
            for forbidden in ("receipt_path", "raw_events", "raw_response", "response_body", "traceback", "secret@"):
                assert forbidden not in lowered
            assert "nothing was switched or installed" in lowered
            assert "does not retry or duplicate" in lowered
            assert "install, pull, replace, or delete" not in lowered
            assert "dashboard_chat_turn_regenerate" not in lowered
            title_parser = _TitleAttributeParser(); title_parser.feed(html)
            assert not title_parser.has_title
        checks.append(_run_check("provider_recovery_adds_no_secret_exposure_fallback_model_management_or_native_tooltips", privacy_and_governance_boundaries_remain_explicit))

        def preview_remains_write_free() -> None:
            before = {
                str(path.relative_to(EXTERNAL_DATA_DIR)): path.read_bytes()
                for path in EXTERNAL_DATA_DIR.rglob("*") if path.is_file()
            }
            modules["render_realtime_chat_panel"](None)
            after = {
                str(path.relative_to(EXTERNAL_DATA_DIR)): path.read_bytes()
                for path in EXTERNAL_DATA_DIR.rglob("*") if path.is_file()
            }
            assert before == after
        checks.append(_run_check("provider_recovery_chat_and_settings_preview_remain_side_effect_free", preview_remains_write_free))
    finally:
        try:
            _restore_tree(EXTERNAL_DATA_DIR, backup)
            restored = True
        except Exception as error:
            restore_error = f"{type(error).__name__}: {error}"

    passed = sum(1 for check in checks if check["status"] == "pass")
    ok = passed == len(checks) and restored
    result = {
        "suite": "provider-readiness-offline-recovery-v1079.5",
        "ok": ok,
        "status": "pass" if ok else "fail",
        "passed": passed,
        "total": len(checks),
        "runtime_data_restored": restored,
        "restore_error": restore_error,
        "checks": checks,
        "evidence_classification": "deterministic simulated-provider fixture",
        "native_provider_evidence": False,
        "model_management_performed": False,
        "provider_or_model_switched": False,
        "release_authorized": False,
        "autonomy_expanded": False,
    }
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{result['status']}: {passed}/{len(checks)}")
        for check in checks:
            print(f"- {check['status']}: {check['name']}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
