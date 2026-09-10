from __future__ import annotations

"""Deterministic v1079.7.0 conversational responsiveness and companion-quality fixtures.

The suite contacts no provider and performs no model management, approval, release,
rollback, source mutation, or autonomous action. Runtime writes are isolated and
restored after the checks.
"""

import argparse
import gc
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
EXTERNAL_DATA_DIR = Path(
    os.environ.get("EIDOLON_DATA_DIR")
    or (Path(tempfile.gettempdir()) / "eidolon-v1079-7-conversation-quality-data")
).resolve()
os.environ["EIDOLON_DATA_DIR"] = str(EXTERNAL_DATA_DIR)
sys.path.insert(0, str(AGENT))


def _source_snapshot() -> dict[str, str]:
    return {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in ROOT.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    }


def _backup_runtime() -> Path:
    backup = Path(tempfile.mkdtemp(prefix="eidolon-v1079-7-quality-backup-"))
    if EXTERNAL_DATA_DIR.exists():
        shutil.copytree(EXTERNAL_DATA_DIR, backup / "data", dirs_exist_ok=True)
        shutil.rmtree(EXTERNAL_DATA_DIR)
    EXTERNAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return backup


def _restore_runtime(backup: Path) -> None:
    try:
        from chromadb.api.client import SharedSystemClient
        SharedSystemClient.clear_system_cache()
    except (ImportError, AttributeError):
        pass
    gc.collect()
    shutil.rmtree(EXTERNAL_DATA_DIR, ignore_errors=True)
    saved = backup / "data"
    if saved.exists():
        shutil.copytree(saved, EXTERNAL_DATA_DIR)
    shutil.rmtree(backup, ignore_errors=True)


def _check(name: str, function: Callable[[], None]) -> dict[str, Any]:
    try:
        function()
        return {"name": name, "status": "pass"}
    except Exception as error:
        return {
            "name": name,
            "status": "fail",
            "error": f"{type(error).__name__}: {error}",
            "traceback": traceback.format_exc(),
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    source_before = _source_snapshot()
    backup = _backup_runtime()
    checks: list[dict[str, Any]] = []
    restore_error = ""
    try:
        import chat_action_router as router
        import command_runner
        import conversation_runtime as runtime
        import dashboard_chat_console as console
        from conversation_context import build_conversation_prompt
        from conversation_quality import (
            classify_conversation_quality,
            filter_general_conversation_memories,
            general_memory_is_conversation_eligible,
            should_analyze_chat_action,
        )
        from conversation_sessions import create_conversation_session
        from paths import DESIRES_FILE, MEMORY_FILE, SELF_FILE
        from settings_manager import DEFAULT_SETTINGS, save_settings

        EXTERNAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
        SELF_FILE.write_text(json.dumps({"name": "Eidolon", "mood": "steady", "active_goals": ["Ship a build"]}), encoding="utf-8")
        DESIRES_FILE.write_text(json.dumps({"connection": 0.8, "clarity": 0.9}), encoding="utf-8")
        MEMORY_FILE.write_text("[]", encoding="utf-8")
        settings = deepcopy(DEFAULT_SETTINGS)
        settings["ai_chat_enabled"] = False
        save_settings(settings)

        def greetings_emotion_flirting_are_conversation() -> None:
            cases = {
                "Hello": "greeting",
                "I feel lonely tonight": "emotional",
                "You are cute": "flirting",
                "What do you think about that?": "conversation",
            }
            for message, expected in cases.items():
                profile = classify_conversation_quality(message)
                assert profile.kind == expected, (message, profile)
                assert profile.should_analyze_action is False
                assert should_analyze_chat_action(message) is False

        checks.append(_check("greetings_emotion_flirting_and_casual_questions_stay_conversational", greetings_emotion_flirting_are_conversation))

        def ambiguous_work_words_do_not_become_commands() -> None:
            messages = (
                "I have a plan for dinner.",
                "Can you fix my mood?",
                "That review hurt today.",
                "What model of car do you like?",
                "What should I do next with this feeling?",
            )
            for message in messages:
                assert not should_analyze_chat_action(message), message
                action = router.propose_chat_action(message, save=False)
                assert action["intent"] == "conversation_only", (message, action)

        checks.append(_check("ambiguous_plan_fix_review_model_and_next_language_does_not_trigger_actions", ambiguous_work_words_do_not_become_commands))

        def explicit_operator_requests_remain_bounded() -> None:
            expected = {
                "Run diagnostics": "run_diagnostics",
                "Do a system maintainence check": "maintenance_scan",
                "Check approvals": "approval_inbox",
                "Run watch": "watch_once",
                "Check memory status": "memory_status",
                "Check tasks": "task_status",
                "Suggest improvement for conscious_agent/memory.py": "suggest_patch",
                "Review conscious_agent/memory.py": "review_file",
                "Install model llama3": "blocked_model_provider_management",
            }
            for message, intent in expected.items():
                profile = classify_conversation_quality(message)
                assert profile.explicit_operator_request and profile.should_analyze_action, message
                action = router.propose_chat_action(message, save=False)
                assert action["intent"] == intent, (message, action)
                assert action.get("execution_mode") in {router.DIRECT_COMMAND, router.DIRECT_FUNCTION, router.BLOCKED, router.APPROVAL, router.INFO}

        checks.append(_check("explicit_operator_requests_keep_existing_governed_routes", explicit_operator_requests_remain_bounded))

        def short_followups_keep_recent_thread() -> None:
            history = [{
                "user_message": "I am nervous about tomorrow's meeting.",
                "assistant_response": "That makes sense. The uncertainty is probably the hardest part.",
            }]
            for message in ("yes", "why?", "tell me more", "what do you think?"):
                profile = classify_conversation_quality(message, history)
                assert profile.short_follow_up and profile.recent_thread_available
                assert "tomorrow's meeting" in profile.memory_query
                assert profile.should_analyze_action is False

        checks.append(_check("short_followups_resolve_against_recent_completed_context", short_followups_keep_recent_thread))

        def ordinary_prompt_is_companion_first() -> None:
            history = [{"user_message": "I am nervous about tomorrow.", "assistant_response": "We can stay with that for a moment."}]
            packet = build_conversation_prompt(
                user_message="why?",
                self_model={"name": "Eidolon", "active_goals": ["PROJECT GOAL MUST STAY OUT"]},
                desires={"connection": 0.8},
                memories=[{"type": "preference", "content": "Marcus prefers direct, practical answers.", "importance": "high"}],
                project_context="PROJECT STATUS MUST STAY OUT",
                goal_context="GOAL STATUS MUST STAY OUT",
                task_context="TASK STATUS MUST STAY OUT",
                conversation_history=history,
                context_size=4096,
                max_tokens=256,
            )
            prompt = packet.prompt
            assert "CASUAL CONVERSATION CONTRACT" in prompt
            assert "This is a short follow-up" in prompt
            assert "RECENT SESSION TURN" in prompt and "nervous about tomorrow" in prompt
            for forbidden in ("PROJECT STATUS MUST STAY OUT", "GOAL STATUS MUST STAY OUT", "TASK STATUS MUST STAY OUT", "PROJECT GOAL MUST STAY OUT"):
                assert forbidden not in prompt
            assert "Marcus prefers direct, practical answers." in prompt

        checks.append(_check("ordinary_prompt_uses_thread_and_memory_without_project_status_noise", ordinary_prompt_is_companion_first))

        def operator_prompt_admits_only_needed_operational_context() -> None:
            packet = build_conversation_prompt(
                user_message="Run diagnostics",
                self_model={"name": "Eidolon", "active_goals": ["CURRENT OPERATOR GOAL"]},
                desires={"clarity": 0.9},
                memories=[],
                project_context="ACTIVE PROJECT CONTEXT FIXTURE",
                goal_context="STRUCTURED GOAL CONTEXT FIXTURE",
                task_context="TASK QUEUE CONTEXT FIXTURE",
                conversation_history=[],
                context_size=4096,
                max_tokens=256,
            )
            prompt = packet.prompt
            assert "CURRENT OPERATOR GOAL" in prompt
            assert "ACTIVE PROJECT CONTEXT FIXTURE" in prompt
            assert "STRUCTURED GOAL CONTEXT FIXTURE" in prompt
            assert "TASK QUEUE CONTEXT FIXTURE" in prompt
            assert "explicit operator request" in prompt

        checks.append(_check("operational_context_is_admitted_only_for_explicit_operator_threads", operator_prompt_admits_only_needed_operational_context))

        def memory_filtering_is_private_and_nonrepetitive() -> None:
            memories = [
                {"type": "preference", "content": "Marcus prefers concise explanations."},
                {"type": "reflection", "content": "Internal reflection."},
                {"type": "chat_action_proposed", "content": "Internal action receipt."},
                {"type": "memory", "content": "Secret material", "privacy": "secret"},
                {"type": "memory", "content": "Resolved material", "status": "resolved"},
                {"type": "memory", "content": "Explicitly disabled", "use_in_conversation": False},
            ]
            eligible = filter_general_conversation_memories(memories)
            assert [item["content"] for item in eligible] == ["Marcus prefers concise explanations."]
            assert general_memory_is_conversation_eligible(memories[0]) is True
            for item in memories[1:]:
                assert general_memory_is_conversation_eligible(item) is False
            packet = build_conversation_prompt(
                user_message="tell me more",
                self_model={"name": "Eidolon"}, desires={}, memories=memories,
                project_context="", goal_context="", task_context="",
                conversation_history=[{"user_message": "Marcus prefers concise explanations.", "assistant_response": "I will keep this focused."}],
                context_size=2048, max_tokens=192,
            )
            assert packet.prompt.count("Marcus prefers concise explanations.") == 1
            assert "Internal reflection" not in packet.prompt and "Secret material" not in packet.prompt

        checks.append(_check("eligible_long_term_memory_is_filtered_and_not_repeated_from_recent_history", memory_filtering_is_private_and_nonrepetitive))

        def response_cleanup_and_offline_copy_are_human_facing() -> None:
            assert runtime._clean_assistant_response("Eidolon: Hello there.") == "Hello there."
            assert runtime._clean_assistant_response("Assistant: Eidolon: Hello there.") == "Hello there."
            assert runtime._clean_assistant_response("A label: should remain") == "A label: should remain"
            cleaner = runtime._AssistantStreamCleaner("Eidolon")
            assert cleaner.feed("Assis") == ""
            assert cleaner.feed("tant: Eido") == ""
            assert cleaner.feed("lon: Hello ") == "Hello "
            assert cleaner.feed("there.") == "there."
            assert cleaner.finish() == ""
            ordinary = runtime._AssistantStreamCleaner("Eidolon")
            assert ordinary.feed("A natural reply.") == "A natural reply."
            runtime_text = (AGENT / "conversation_runtime.py").read_text(encoding="utf-8")
            assert "Your message was saved. Local generation is off" in runtime_text
            assert "no provider was contacted and no fallback was used" in runtime_text

        checks.append(_check("provider_labels_are_removed_and_offline_copy_preserves_no_fallback_truth", response_cleanup_and_offline_copy_are_human_facing))

        def ordinary_stream_finishes_before_optional_bookkeeping() -> None:
            session = create_conversation_session("Conversation fixture", source="v1079_7_fixture")
            original_stream = console.stream_conversation_turn
            original_propose = console.propose_chat_action
            original_side_effects = console._save_post_response_side_effects
            proposal_calls: list[dict[str, Any]] = []

            def fake_stream(*_args: Any, **_kwargs: Any):
                yield {"event": "meta", "operation_id": "conversation_quality_stream_001", "session_id": session["id"], "provider": "fixture", "model": "fixture"}
                yield {"event": "delta", "operation_id": "conversation_quality_stream_001", "text": "A natural reply."}
                yield {"event": "response_complete", "operation_id": "conversation_quality_stream_001"}
                yield {"event": "done", "operation_id": "conversation_quality_stream_001", "result": {
                    "operation_id": "conversation_quality_stream_001", "success": True, "completion_state": "completed",
                    "display_message": "A natural reply.", "response": "A natural reply.", "failure_category": "",
                    "provider": "fixture", "model": "fixture", "timings_ms": {"first_token": 1, "provider": 2},
                    "recovery_of": "", "recovery_kind": "",
                }}

            def fake_propose(request: str, save: bool = True, **kwargs: Any) -> dict[str, Any]:
                proposal_calls.append({"request": request, "save": save, **kwargs})
                return {"id": "unexpected", "intent": "diagnostics"}

            console.stream_conversation_turn = fake_stream
            console.propose_chat_action = fake_propose
            console._save_post_response_side_effects = lambda *_args, **_kwargs: ""
            try:
                events = list(console.stream_dashboard_chat_turn("Just talking normally", session_id=session["id"], operation_id="conversation_quality_stream_001"))
            finally:
                console.stream_conversation_turn = original_stream
                console.propose_chat_action = original_propose
                console._save_post_response_side_effects = original_side_effects
            names = [str(item.get("event") or "") for item in events]
            complete = names.index("conversation_complete")
            conversation_only = next(i for i, item in enumerate(events) if item.get("event") == "status" and item.get("stage") == "conversation_only")
            assert complete < conversation_only < names.index("done")
            assert proposal_calls == []
            assert not any(item.get("event") == "action" for item in events)

        checks.append(_check("ordinary_stream_releases_conversation_before_skipping_action_analysis", ordinary_stream_finishes_before_optional_bookkeeping))

        def explicit_action_analysis_is_deduplicated_by_operation() -> None:
            shutil.rmtree(router.CHAT_ACTIONS_DIR, ignore_errors=True)
            key = "conversation_quality_action_001"
            first = router.propose_chat_action("Run diagnostics", save=True, save_unknown=False, deduplication_key=key)
            second = router.propose_chat_action("Run diagnostics", save=True, save_unknown=False, deduplication_key=key)
            assert first["id"] == second["id"] and first["deduplication_key"] == key
            records = [item for item in router.list_chat_actions(include_closed=True) if item.get("deduplication_key") == key]
            assert len(records) == 1

        checks.append(_check("explicit_action_analysis_persists_exactly_once_per_conversation_operation", explicit_action_analysis_is_deduplicated_by_operation))

        def explicit_safe_action_is_visible_and_runs_once() -> None:
            session = create_conversation_session("Action bridge fixture", select_session=False)
            original_stream = console.stream_conversation_turn
            original_propose = console.propose_chat_action
            original_execute = console._execute_explicit_safe_chat_action
            original_side_effects = console._save_post_response_side_effects
            executions: list[str] = []

            def fake_stream(*_args: Any, **_kwargs: Any):
                yield {"event": "meta", "operation_id": "conversation_action_bridge_001", "provider": "fixture", "model": "fixture"}
                yield {"event": "delta", "text": "I can route that through the supervised system action."}
                yield {"event": "done", "result": {
                    "operation_id": "conversation_action_bridge_001", "success": True, "completion_state": "completed",
                    "display_message": "I can route that through the supervised system action.", "timings_ms": {"provider": 1},
                }}

            def fake_propose(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
                return {
                    "id": "chat_action_action_bridge_001", "status": "proposed", "intent": "maintenance_scan",
                    "title": "Run maintenance scan", "summary": "Run the allowlisted maintenance check.",
                    "execution_mode": "direct_command", "risk_level": "low",
                }

            def fake_execute(action: dict[str, Any] | None) -> dict[str, Any]:
                executions.append(str((action or {}).get("id") or ""))
                return {"ok": True, "action_id": executions[-1], "status": "executed", "message": "Maintenance scan completed.", "output": "fixture clean", "output_truncated": False}

            console.stream_conversation_turn = fake_stream
            console.propose_chat_action = fake_propose
            console._execute_explicit_safe_chat_action = fake_execute
            console._save_post_response_side_effects = lambda *_args, **_kwargs: ""
            try:
                events = list(console.stream_dashboard_chat_turn(
                    "Do a system maintainence check", session_id=session["id"], operation_id="conversation_action_bridge_001"
                ))
            finally:
                console.stream_conversation_turn = original_stream
                console.propose_chat_action = original_propose
                console._execute_explicit_safe_chat_action = original_execute
                console._save_post_response_side_effects = original_side_effects
            names = [str(item.get("event") or "") for item in events]
            assert names.count("action") == 1 and names.count("action_result") == 1
            assert "meta" not in names and "provider_request" not in names
            assert names.index("action") < names.index("action_result") < names.index("delta") < names.index("conversation_complete") < names.index("done")
            assert executions == ["chat_action_action_bridge_001"]
            final_turn = next(item["turn"] for item in events if item.get("event") == "done")
            assert final_turn["action_execution"]["ok"] is True
            assert final_turn["conversation_runtime"]["provider_request_count"] == 0
            assert final_turn["conversation_runtime"]["operator_routed_before_provider"] is True
        checks.append(_check("explicit_allowlisted_chat_action_is_visible_and_executes_once_before_generation", explicit_safe_action_is_visible_and_runs_once))

        def approved_python_actions_use_active_interpreter() -> None:
            validation = command_runner.validate_command(
                "python conscious_agent/main.py --maintenance-scan --no-ai-maintenance"
            )
            assert validation.ok is True
            execution_args = command_runner._execution_args(validation.args)
            assert execution_args[0] == sys.executable
            assert execution_args[1:] == validation.args[1:]

        checks.append(_check("approved_python_actions_execute_with_active_virtual_environment_interpreter", approved_python_actions_use_active_interpreter))

        def reflection_bookkeeping_is_once_and_prompt_ineligible() -> None:
            originals = {
                "load_memories": console.load_memories,
                "load_self_model": console.load_self_model,
                "load_desires": console.load_desires,
                "generate_inner_thought": console.generate_inner_thought,
                "reflect_on_thought": console.reflect_on_thought,
                "store_memory_batch": console.store_memory_batch,
            }
            stored: list[dict[str, Any]] = []
            console.load_memories = lambda limit=None: list(stored)
            console.load_self_model = lambda: {"name": "Eidolon"}
            console.load_desires = lambda: {"clarity": 1.0}
            console.generate_inner_thought = lambda **_kwargs: {"type": "thought", "content": "Internal thought"}
            console.reflect_on_thought = lambda *_args, **_kwargs: {"type": "reflection", "content": "Internal reflection"}
            console.store_memory_batch = lambda items: stored.extend(dict(item) for item in items)
            try:
                assert console._save_post_response_side_effects("conversation_quality_side_effect_001", "hello", "reply", None) == ""
                assert console._save_post_response_side_effects("conversation_quality_side_effect_001", "hello", "reply", None) == ""
                stored.clear()
                stored.append({
                    "type": "thought",
                    "content": "Previously committed thought",
                    "conversation_side_effect_id": "conversation_quality_side_effect_002",
                    "conversation_side_effect_phase": "thought",
                    "use_in_conversation": False,
                })
                assert console._save_post_response_side_effects("conversation_quality_side_effect_002", "hello", "reply", None) == ""
            finally:
                for name, value in originals.items():
                    setattr(console, name, value)
            assert len(stored) == 2
            assert all(item.get("conversation_side_effect_id") == "conversation_quality_side_effect_002" for item in stored)
            assert {item.get("conversation_side_effect_phase") for item in stored} == {"thought", "reflection"}
            assert all(item.get("use_in_conversation") is False for item in stored)

        checks.append(_check("optional_reflection_bookkeeping_is_exactly_once_and_excluded_from_prompt_recall", reflection_bookkeeping_is_once_and_prompt_ineligible))

        def rendered_javascript_and_responsive_contracts() -> None:
            html = console.render_realtime_chat_panel(None, include_archived=True)
            scripts = re.findall(r"<script>(.*?)</script>", html, flags=re.DOTALL)
            assert scripts
            node = shutil.which("node")
            if node:
                temporary = Path(tempfile.mkdtemp(prefix="eidolon-v1079-7-quality-js-")) / "chat.js"
                temporary.write_text("\n".join(scripts), encoding="utf-8")
                completed = subprocess.run([node, "--check", str(temporary)], capture_output=True, text=True, timeout=20)
                shutil.rmtree(temporary.parent, ignore_errors=True)
                assert completed.returncode == 0, completed.stderr or completed.stdout
            style_source = (AGENT / "dashboard_chat_styles.py").read_text(encoding="utf-8")
            assert "@media (max-width:620px)" in style_source
            assert ".chat-composer-actions { display:grid; grid-template-columns:1fr 1fr" in style_source
            assert "Enter sends; Shift+Enter adds a new line." in html
            assert "event.isComposing" in html and "settleTerminalControls(operationIdForTurn)" in html
            assert "Reply saved. You can keep talking." in html
            assert "type === 'action'" in html and "type === 'action_result'" in html
            assert "appendChatActionCard" in html and "applyChatActionResult" in html
            lowered = html.lower()
            for forbidden in ("ollama pull", "install model", "delete model", "automatic fallback", "grant approval", "authorize release"):
                assert forbidden not in lowered

        checks.append(_check("rendered_javascript_stream_controls_and_responsive_layouts_remain_valid", rendered_javascript_and_responsive_contracts))

        def verifier_registration_and_governance_are_bounded() -> None:
            verifier = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
            filename = "tools/conversational_responsiveness_companion_quality_tests.py"
            assert verifier.count(filename) == 1
            quality_text = (AGENT / "conversation_quality.py").read_text(encoding="utf-8").lower()
            runtime_text = (AGENT / "conversation_runtime.py").read_text(encoding="utf-8").lower()
            for forbidden in ("ollama pull", "ollama rm", "automatic provider switch", "release_authorized = true", "autonomy_expanded = true"):
                assert forbidden not in quality_text and forbidden not in runtime_text

        checks.append(_check("quality_suite_is_registered_once_without_model_provider_or_governance_authority", verifier_registration_and_governance_are_bounded))
    finally:
        try:
            _restore_runtime(backup)
        except Exception as error:
            restore_error = f"{type(error).__name__}: {error}"

    source_after = _source_snapshot()
    source_tree_unchanged = source_before == source_after

    passed = sum(1 for check in checks if check["status"] == "pass")
    total = len(checks)
    ok = passed == total and not restore_error and source_tree_unchanged
    report = {
        "suite": "v1079.7.0-conversational-responsiveness-and-companion-quality",
        "status": "pass" if ok else "fail",
        "ok": ok,
        "passed": passed,
        "total": total,
        "checks": checks,
        "runtime_data_restored": not restore_error,
        "source_tree_unchanged": source_tree_unchanged,
        "restore_error": restore_error,
        "native_provider_contacted": False,
        "model_management_performed": False,
        "provider_changed": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "evidence_classification": "deterministic fixture",
    }
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"{report['suite']}: {report['status']} ({passed}/{total})")
        for check in checks:
            print(f"[{check['status'].upper()}] {check['name']}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
