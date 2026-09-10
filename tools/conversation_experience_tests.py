from __future__ import annotations

"""Deterministic companion-first conversation experience fixtures through v1079.5."""

import argparse
import gc
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
    backup = Path(tempfile.mkdtemp(prefix="eidolon-conversation-experience-backup-"))
    if root.exists():
        shutil.copytree(root, backup / "data", dirs_exist_ok=True)
    return backup


def _restore_tree(root: Path, backup: Path) -> None:
    try:
        from chromadb.api.client import SharedSystemClient
        SharedSystemClient.clear_system_cache()
    except (ImportError, AttributeError):
        pass
    gc.collect()
    if root.exists():
        shutil.rmtree(root)
    saved = backup / "data"
    if saved.exists():
        shutil.copytree(saved, root)
    shutil.rmtree(backup, ignore_errors=True)


def _load_modules() -> dict[str, Any]:
    import dashboard_chat_console as dashboard_console
    from conversation_experience import (
        build_conversation_experience_state,
        presentation_for_turn,
        provider_display_name,
    )
    from conversation_operations import create_operation_marker, finalize_operation_marker, new_conversation_operation_id
    from conversation_sessions import (
        append_conversation_turn,
        create_conversation_session,
        load_conversation_session,
        migrate_legacy_dashboard_chat_turns,
    )
    from dashboard_chat_console import render_realtime_chat_panel, stream_dashboard_chat_turn
    from paths import DESIRES_FILE, MEMORY_FILE, SELF_FILE
    from settings_manager import DEFAULT_SETTINGS, save_settings

    return locals()


def _seed_runtime(modules: dict[str, Any]) -> None:
    EXTERNAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    modules["SELF_FILE"].write_text(
        json.dumps({"name": "Eidolon", "mood": "steady", "energy": 0.7, "focus": "conversation"}),
        encoding="utf-8",
    )
    modules["DESIRES_FILE"].write_text(json.dumps({"connection": 0.8}), encoding="utf-8")
    modules["MEMORY_FILE"].write_text(
        json.dumps([
            {
                "id": "experience-memory-1",
                "type": "preference",
                "content": "Marcus prefers calm direct explanations.",
                "importance": "high",
                "status": "active",
                "source": "operator",
            }
        ]),
        encoding="utf-8",
    )
    settings = deepcopy(modules["DEFAULT_SETTINGS"])
    settings["local_model_provider"] = "ollama"
    settings["local_model"] = "experience-fixture-model"
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

        def calm_state_mapping_is_deterministic() -> None:
            assert modules["presentation_for_turn"](None) == (
                "ready", "Ready to talk", "Start a new conversation or continue where you left off."
            )
            assert modules["presentation_for_turn"]({"success": True, "completion_state": "completed"})[1] == "Ready to continue"
            timeout = modules["presentation_for_turn"]({"success": False, "completion_state": "failed", "failure_category": "timeout"})
            assert timeout[0] == "attention" and timeout[1] == "Eidolon took too long"
            assert "raw" not in " ".join(timeout).lower()
        checks.append(_run_check("calm_runtime_state_mapping_is_deterministic_and_redacted", calm_state_mapping_is_deterministic))

        def provider_labels_are_bounded() -> None:
            assert modules["provider_display_name"]("ollama") == "Ollama"
            assert modules["provider_display_name"]("llama_cpp") == "llama.cpp"
            assert len(modules["provider_display_name"]("x" * 200)) <= 32
        checks.append(_run_check("provider_labels_are_human_readable_and_bounded", provider_labels_are_bounded))

        def offline_state_is_explicit() -> None:
            result = modules["build_conversation_experience_state"](
                active_session={"title": "Daily check-in"}, latest_turn=None,
                settings={"local_model_provider": "ollama", "local_model": "model", "ai_chat_enabled": False},
                continuity_summary={"cue_count": 1, "mood_label": "steady"},
            ).public_dict()
            assert result["state"] == "offline"
            assert result["label"] == "Offline mode"
            assert result["session_title"] == "Daily check-in"
        checks.append(_run_check("offline_mode_is_visible_without_contacting_a_provider", offline_state_is_explicit))

        def companion_header_and_progressive_disclosure_render() -> None:
            session = modules["create_conversation_session"]("Evening conversation", source="fixture")
            modules["append_conversation_turn"](
                session["id"], turn_id="experience-complete", user_message="How was your day?",
                assistant_response="I am here with you.", completion_state="completed", success=True,
                provider="ollama", model="experience-fixture-model",
            )
            html = modules["render_realtime_chat_panel"](None)
            state["html"] = html
            assert "Conversation with Eidolon" in html
            assert "companion-status-card" in html
            assert ">Ready<" in html
            assert "chat-provider-pill" not in html
            assert "chat-mode-pill" in html and "Private local conversation" in html
            assert "Ollama" in html and html.index("Ollama") > html.index("Generation details")
            assert "<details class='chat-tools-drawer'" in html
            assert "<details class='chat-diagnostics-drawer'" in html
            assert "Generation details" in html
            assert html.index("realtime-chat-log") < html.index("Generation details")
        checks.append(_run_check("companion_header_keeps_tools_and_diagnostics_progressively_disclosed", companion_header_and_progressive_disclosure_render))

        def draft_is_scoped_to_session() -> None:
            html = state["html"]
            assert "eidolon.chat.draft.v3." in html
            assert "window.localStorage.getItem(key)" in html
            assert "window.localStorage.setItem(key" in html
            assert "/api/dashboard-chat/draft" in html
            assert "data-server-draft-updated-at" in html
            assert "data-server-draft-revision" in html
            assert "chat-draft-conflict" in html
            assert "eidolon.chat.navigation.v1" in html
            assert "window.sessionStorage.getItem(navigationStorageKey)" in html
            assert "window.sessionStorage.getItem(key)" not in html
        checks.append(_run_check("unsent_draft_is_preserved_per_conversation_session", draft_is_scoped_to_session))

        def draft_clears_only_after_runtime_acceptance() -> None:
            html = state["html"]
            source = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
            submit_start = source.index("form.addEventListener('submit'")
            accepted_start = source.index("if (type === 'accepted')", submit_start)
            meta_start = source.index("type === 'meta'", accepted_start)
            preaccepted = source[submit_start:accepted_start]
            if "clearAcceptedDraft(turnSessionId" in preaccepted:
                assert preaccepted.index("resolveAcceptanceOutcome(turnSessionId, acceptanceKey") < preaccepted.index("clearAcceptedDraft(turnSessionId")
                assert "outcome.state === 'accepted'" in preaccepted
            accepted_branch = source[accepted_start:meta_start]
            assert "acceptedByRuntime = true;" in accepted_branch
            assert "clearAcceptedDraft(turnSessionId, turnDraftKey, turnGeneration);" in accepted_branch
            assert "draftClearedOperationId !== operationIdForTurn" in source[accepted_start:]
            assert "resolveAcceptanceOutcome" in html
            assert "messageBox.value = submittedMessage;" in html
            assert "Your newer draft was preserved instead of being overwritten." in html
            assert "Your draft was restored" in html
        checks.append(_run_check("draft_clears_only_after_runtime_acceptance_and_restores_on_early_failure", draft_clears_only_after_runtime_acceptance))

        def enter_sends_shift_enter_preserves_newline() -> None:
            html = state["html"]
            assert "if (event.key !== 'Enter') return;" in html
            assert "if (event.shiftKey)" in html
            assert "messageBox.addEventListener('beforeinput'" in html
            assert "insertLineBreak" in html and "insertParagraph" in html
            assert "enterkeyhint='send'" in html
            assert "form.requestSubmit()" in html
            assert "Shift+Enter adds a new line" in html
        checks.append(_run_check("desktop_and_mobile_enter_send_while_shift_enter_preserves_multiline_composition", enter_sends_shift_enter_preserves_newline))

        def scroll_does_not_yank_reader() -> None:
            html = state["html"]
            assert "function isFollowingConversation()" in html
            assert "< 72" in html
            assert "if (follow) scrollConversation(true)" in html
            assert "log.scrollTop = log.scrollHeight" in html
            assert "chat-jump-latest" in html
            assert "updateJumpLatestButton" in html
        checks.append(_run_check("streaming_auto_scroll_preserves_reading_position_and_offers_latest_control", scroll_does_not_yank_reader))

        def conversation_completion_releases_chat_before_optional_action_work() -> None:
            console = modules["dashboard_console"]
            original_stream = console.stream_conversation_turn
            original_propose = console.propose_chat_action
            proposal_calls: list[dict[str, Any]] = []

            def fake_stream(*_args: Any, **kwargs: Any):
                operation_id = str(kwargs.get("operation_id") or "im-operation")
                yield {"event": "meta", "operation_id": operation_id, "provider": "fixture", "model": "fixture"}
                yield {"event": "delta", "text": "A completed conversational reply."}
                yield {
                    "event": "done",
                    "result": {
                        "success": True,
                        "completion_state": "completed",
                        "display_message": "A completed conversational reply.",
                        "failure_category": "",
                        "provider": "fixture",
                        "model": "fixture",
                        "timings_ms": {"first_token": 1, "provider": 2},
                        "recovery_of": "",
                        "recovery_kind": "",
                    },
                }

            def fake_propose(request: str, save: bool = True, **kwargs: Any) -> dict[str, Any]:
                proposal_calls.append({"request": request, "save": save, **kwargs})
                return {"id": "", "intent": "unknown_request", "status": "blocked"}

            console.stream_conversation_turn = fake_stream
            console.propose_chat_action = fake_propose
            try:
                events = list(modules["stream_dashboard_chat_turn"](
                    "Just talking normally", use_ai=True, operation_id="im-operation"
                ))
            finally:
                console.stream_conversation_turn = original_stream
                console.propose_chat_action = original_propose

            names = [str(item.get("event") or "") for item in events]
            complete_index = names.index("conversation_complete")
            conversation_only_index = next(
                index for index, item in enumerate(events)
                if item.get("event") == "status" and item.get("stage") == "conversation_only"
            )
            assert complete_index < conversation_only_index < names.index("done")
            assert not any(item.get("event") == "action" for item in events)
            assert proposal_calls == []
            html = state["html"]
            complete_branch = html[html.index("type === 'conversation_complete'"):html.index("type === 'status'")]
            assert "settleTerminalControls(operationIdForTurn)" in complete_branch
            assert "Reply saved. You can keep talking." in complete_branch
        checks.append(_run_check("completed_reply_releases_composer_before_optional_action_processing", conversation_completion_releases_chat_before_optional_action_work))

        def transcript_keeps_more_than_thirty_turns() -> None:
            session = modules["create_conversation_session"]("Long conversation", source="fixture")
            for index in range(1, 36):
                modules["append_conversation_turn"](
                    session["id"],
                    turn_id=f"long-conversation-{index}",
                    user_message=f"Retained message {index}",
                    assistant_response=f"Retained response {index}",
                    completion_state="completed",
                    success=True,
                    provider="fixture",
                    model="fixture",
                )
            html = modules["render_realtime_chat_panel"](None)
            assert "Retained message 1" in html and "Retained response 1" in html
            assert "Retained message 35" in html and "Retained response 35" in html
        checks.append(_run_check("active_transcript_retains_more_than_thirty_completed_turns", transcript_keeps_more_than_thirty_turns))

        def runtime_states_are_visible_but_calm() -> None:
            html = state["html"]
            for token in ("Still responding", "Saving draft", "Switching conversation", "Creating conversation", "Cancelling safely", "Completion uncertain"):
                assert token in html
            assert "thinking-pulse" not in html
            assert "saved to conversation" not in html
        checks.append(_run_check("generation_cancellation_and_recovery_states_use_companion_first_language", runtime_states_are_visible_but_calm))

        def failed_turn_remains_honest_and_retryable() -> None:
            session = modules["create_conversation_session"]("Recovery view", source="fixture")
            turn_id = modules["new_conversation_operation_id"]()
            modules["create_operation_marker"](
                turn_id, session["id"], acceptance_key="experience_failed_acceptance", streaming=True,
            )
            modules["append_conversation_turn"](
                session["id"], turn_id=turn_id, user_message="Please answer",
                assistant_response="The connection ended.", completion_state="failed", success=False,
                failure_category="provider_disconnect", provider="ollama", model="experience-fixture-model",
            )
            modules["finalize_operation_marker"](
                turn_id, completion_state="failed", success=False, failure_category="provider_disconnect",
                final_session_turn_recorded=True,
            )
            html = modules["render_realtime_chat_panel"](None)
            assert "Not added to memory or future continuity." in html
            assert "dashboard_chat_turn_retry" in html
            assert "Run explicit linked recovery" in html
            assert "name='recovery_token'" in html
            assert "dashboard_chat_turn_regenerate" not in html
            assert ">Regenerate<" not in html
        checks.append(_run_check("failed_turns_remain_visible_retryable_and_excluded_from_continuity", failed_turn_remains_honest_and_retryable))

        def dashboard_preview_is_write_free() -> None:
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
        checks.append(_run_check("companion_chat_preview_remains_side_effect_free", dashboard_preview_is_write_free))

        def diagnostics_are_disclosed_without_receipts_or_secrets() -> None:
            html = state["html"]
            lowered = html.lower()
            assert "runtime receipts" in lowered and "remain private" in lowered
            assert "receipt_path" not in lowered
            assert "raw_events" not in lowered
            assert "authorization" not in lowered
            assert "http://localhost:11434" in html
            assert html.index("http://localhost:11434") > html.index("Generation details")
            assert "credentials, and stack traces remain private" in lowered
        checks.append(_run_check("generation_details_disclose_bounded_endpoint_without_receipts_or_secrets", diagnostics_are_disclosed_without_receipts_or_secrets))

        def governance_boundaries_remain_explicit() -> None:
            html = state["html"].lower()
            assert "partial output is not committed to memory" in html
            assert "provider changes keep this conversation selected" in html
            assert "silent fallback" not in html
            assert "install model" not in html and "delete model" not in html
            assert "autonomous" not in html
            assert " title=" not in html
        checks.append(_run_check("polish_adds_no_model_management_fallback_autonomy_or_native_tooltips", governance_boundaries_remain_explicit))

        def legacy_dashboard_history_import_is_lossless_and_idempotent() -> None:
            legacy_dir = EXTERNAL_DATA_DIR / "dashboard_chat"
            if legacy_dir.exists():
                shutil.rmtree(legacy_dir)
            legacy_dir.mkdir(parents=True, exist_ok=True)
            original_payloads: dict[str, bytes] = {}
            for index, stamp in enumerate(("2026-06-18T21:52:17", "2026-06-18T21:53:04"), start=1):
                payload = {
                    "id": f"dash_chat_legacy_fixture_{index}",
                    "type": "dashboard_chat_turn",
                    "created_at": stamp,
                    "user_message": f"Private legacy message {index}",
                    "eidolon_response": f"Private legacy response {index}",
                    "use_ai": True,
                    "error": "",
                }
                path = legacy_dir / f"legacy_fixture_{index}.json"
                path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                original_payloads[path.name] = path.read_bytes()
            first = modules["migrate_legacy_dashboard_chat_turns"]()
            second = modules["migrate_legacy_dashboard_chat_turns"]()
            session = modules["load_conversation_session"](first["session_id"], include_turns=True)
            assert first["status"] == "imported" and first["imported_turn_count"] == 2, first
            assert second["status"] == "current" and second["imported_turn_count"] == 0, second
            assert session and session["turn_count"] == 2 and session["completed_turn_count"] == 2, session
            assert len({turn["id"] for turn in session["turns"]}) == 2, session["turns"]
            preserved_payloads = {path.name: path.read_bytes() for path in legacy_dir.glob("*.json")}
            assert preserved_payloads == original_payloads, sorted(preserved_payloads)
            marker_text = (EXTERNAL_DATA_DIR / "conversation_sessions" / "legacy_dashboard_chat_import.json").read_text(encoding="utf-8")
            assert "Private legacy message" not in marker_text and "Private legacy response" not in marker_text, marker_text
        checks.append(_run_check("legacy_dashboard_history_import_is_lossless_private_and_idempotent", legacy_dashboard_history_import_is_lossless_and_idempotent))
    finally:
        try:
            _restore_tree(EXTERNAL_DATA_DIR, backup)
            restored = True
        except Exception as error:
            restore_error = f"{type(error).__name__}: {error}"

    passed = sum(1 for check in checks if check["status"] == "pass")
    suite_ok = passed == len(checks) and restored
    result = {
        "suite": "conversation-experience-polish-through-v1079.5",
        "ok": suite_ok,
        "status": "pass" if suite_ok else "fail",
        "passed": passed,
        "total": len(checks),
        "runtime_data_restored": restored,
        "restore_error": restore_error,
        "checks": checks,
        "evidence_classification": "deterministic fixture",
        "native_provider_evidence": False,
    }
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{result['status']}: {passed}/{len(checks)}")
        for check in checks:
            print(f"- {check['status']}: {check['name']}")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
