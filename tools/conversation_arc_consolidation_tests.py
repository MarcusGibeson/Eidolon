from __future__ import annotations

"""Deterministic cross-feature consolidation fixtures for the v1079.4 conversation arc.

The suite exercises the completed session, relationship, temporal, recovery,
experience, provider-profile, memory-commit, receipt-redaction, and governance
layers together. It uses a simulated provider client only and restores the
external runtime tree exactly.
"""

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
    backup = Path(tempfile.mkdtemp(prefix="eidolon-conversation-arc-backup-"))
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
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def _load_modules() -> dict[str, Any]:
    import conversation_runtime
    from conversation_experience import build_conversation_experience_state
    from conversation_recovery import retry_failed_conversation_turn
    from conversation_sessions import (
        archive_conversation_session,
        conversation_history_for_prompt,
        conversation_session_turns,
        create_conversation_session,
        load_conversation_session,
        rename_conversation_session,
        restore_conversation_session,
        search_conversation_sessions,
        select_conversation_session,
        session_contains_private_receipt_fields,
    )
    from dashboard import render_chat_console
    from local_model import LocalModelTimeoutError
    from local_model_configuration import save_local_model_configuration
    from memory import load_memories
    from paths import DESIRES_FILE, MEMORY_FILE, SELF_FILE
    from relationship_memory_curation import create_relationship_memory, update_relationship_memory
    from settings_manager import DEFAULT_SETTINGS, load_settings, save_settings

    try:
        import vector_memory
        vector_memory.add_memory_vector = lambda _memory: None
    except Exception:
        pass
    return locals()


class SimulatedConversationClient:
    mode = "success"
    output = "I remember our ongoing thread and can continue naturally."
    prompts: list[str] = []
    configs: list[dict[str, str]] = []

    def __init__(self, config: Any, cancel_event: Any = None) -> None:
        self.config = config
        self.cancel_event = cancel_event
        self.last_retry_count = 0
        self.__class__.configs.append({"provider": config.provider, "model": config.model})

    def generate(self, prompt: str) -> str:
        self.__class__.prompts.append(prompt)
        if self.__class__.mode == "timeout":
            raise LocalModelTimeoutError(
                "simulated provider-controlled timeout detail",
                provider=self.config.provider,
                endpoint=self.config.endpoint,
                model=self.config.model,
                retryable=True,
                details={"failure_kind": "simulated_timeout"},
            )
        return self.__class__.output

    def cancel(self) -> None:
        if self.cancel_event is not None:
            self.cancel_event.set()

    def close(self) -> None:
        return None


# Imported lazily by _load_modules; bound here for the simulated client method.
LocalModelTimeoutError: Any = RuntimeError


def _seed_runtime(modules: dict[str, Any]) -> None:
    EXTERNAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    modules["SELF_FILE"].write_text(json.dumps({
        "name": "Eidolon",
        "current_state": {"mood_label": "warm", "energy": 0.62, "focus": 0.71},
        "active_goals": [],
    }, indent=2), encoding="utf-8")
    modules["DESIRES_FILE"].write_text(json.dumps({"connection": 0.8}, indent=2), encoding="utf-8")
    modules["MEMORY_FILE"].write_text("[]", encoding="utf-8")
    settings = deepcopy(modules["DEFAULT_SETTINGS"])
    settings["local_model_provider"] = "ollama"
    settings["local_model"] = "consolidation-ollama-model"
    settings["local_model_retry_limit"] = 0
    settings["ai_chat_enabled"] = True
    profiles = deepcopy(settings.get("local_model_provider_profiles") or {})
    profiles["ollama"]["local_model"] = "consolidation-ollama-model"
    profiles["llama_cpp"]["local_model"] = "consolidation-llama-model"
    settings["local_model_provider_profiles"] = profiles
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
    original_client: Any = None
    try:
        if EXTERNAL_DATA_DIR.exists():
            shutil.rmtree(EXTERNAL_DATA_DIR)
        modules = _load_modules()
        global LocalModelTimeoutError
        LocalModelTimeoutError = modules["LocalModelTimeoutError"]
        _seed_runtime(modules)
        original_client = modules["conversation_runtime"].LocalModelClient
        modules["conversation_runtime"].LocalModelClient = SimulatedConversationClient
        SimulatedConversationClient.mode = "success"
        SimulatedConversationClient.prompts.clear()
        SimulatedConversationClient.configs.clear()
        state: dict[str, Any] = {}

        def dashboard_preview_is_write_free() -> None:
            before = _tree_bytes(EXTERNAL_DATA_DIR)
            html = modules["render_chat_console"]()
            after = _tree_bytes(EXTERNAL_DATA_DIR)
            assert before == after
            assert "Eidolon" in html
            assert "conversation_runtime/receipts" not in html
        checks.append(_run_check("dashboard_preview_is_write_free_before_any_session_exists", dashboard_preview_is_write_free))

        def explicit_continuity_memories_are_deduplicated() -> None:
            nickname = modules["create_relationship_memory"]("nickname", "Marcus prefers Eidolon to call him Marcus.", importance="high")
            duplicate = modules["create_relationship_memory"]("nickname", "Marcus prefers Eidolon to call him Marcus.", importance="high")
            preference = modules["create_relationship_memory"]("preference", "Marcus prefers direct practical answers.", importance="high")
            mood = modules["create_relationship_memory"]("user_mood", "Marcus explicitly feels focused and optimistic today.", importance="high")
            moment = modules["create_relationship_memory"]("important_moment", "Marcus and Eidolon are completing the v1079.4 conversation arc.", importance="high")
            assert nickname["created"] is True and duplicate["created"] is False
            assert preference["created"] is True and mood["created"] is True and moment["created"] is True
            state.update({"mood_key": mood["record"]["record_key"], "moment_key": moment["record"]["record_key"]})
        checks.append(_run_check("explicit_relationship_mood_and_moment_memories_are_created_once", explicit_continuity_memories_are_deduplicated))

        def first_turn_combines_all_continuity_layers() -> None:
            session = modules["create_conversation_session"]("Release reflection", source="consolidation_fixture")
            modules["select_conversation_session"](session["id"])
            result = modules["conversation_runtime"].run_conversation_turn(
                "How are we doing with the v1079.4 conversation arc?",
                source="consolidation_fixture",
                session_id=session["id"],
            )
            assert result.success is True and result.session_id == session["id"]
            assert result.user_memory_stored is True and result.assistant_memory_stored is True
            prompt = SimulatedConversationClient.prompts[-1]
            assert "Marcus prefers Eidolon to call him Marcus" in prompt
            assert "direct practical answers" in prompt
            assert "focused and optimistic today" in prompt
            assert "completing the v1079.4 conversation arc" in prompt
            assert "SYSTEM CONTRACT" in prompt and "LATEST USER MESSAGE" in prompt
            state.update({"session_id": session["id"], "first_result": result})
        checks.append(_run_check("first_turn_combines_session_relationship_mood_and_moment_context", first_turn_combines_all_continuity_layers))

        def provider_switch_preserves_session_and_profiles() -> None:
            modules["save_local_model_configuration"]({"local_model_provider": "llama_cpp"})
            settings = modules["load_settings"]()
            assert settings["local_model_provider"] == "llama_cpp"
            assert settings["local_model"] == "consolidation-llama-model"
            assert settings["local_model_provider_profiles"]["ollama"]["local_model"] == "consolidation-ollama-model"
            result = modules["conversation_runtime"].run_conversation_turn(
                "Continue from what we just discussed.",
                source="consolidation_fixture",
                session_id=state["session_id"],
            )
            assert result.success is True and result.session_id == state["session_id"]
            assert result.provider == "llama_cpp" and result.model == "consolidation-llama-model"
            prompt = SimulatedConversationClient.prompts[-1]
            assert "How are we doing with the v1079.4 conversation arc?" in prompt
            assert "I remember our ongoing thread" in prompt
            state["second_result"] = result
        checks.append(_run_check("provider_switch_preserves_profiles_session_and_completed_history", provider_switch_preserves_session_and_profiles))

        def failed_turn_stays_visible_but_out_of_prompt_history() -> None:
            SimulatedConversationClient.mode = "timeout"
            failed = modules["conversation_runtime"].run_conversation_turn(
                "Retry this exact thought safely if the provider times out.",
                source="consolidation_fixture",
                session_id=state["session_id"],
            )
            SimulatedConversationClient.mode = "success"
            assert failed.success is False and failed.failure_category == "timeout"
            assert failed.user_memory_stored is True and failed.assistant_memory_stored is False
            turns = modules["conversation_session_turns"](state["session_id"])
            assert turns[-1]["id"] == failed.operation_id and turns[-1]["success"] is False
            history = modules["conversation_history_for_prompt"](state["session_id"], limit=8)
            assert all("Retry this exact thought" not in row["user_message"] for row in history)
            state["failed_result"] = failed
        checks.append(_run_check("failed_turn_is_visible_but_excluded_from_future_prompt_history", failed_turn_stays_visible_but_out_of_prompt_history))

        def recovery_reuses_user_memory_and_commits_once() -> None:
            recovered = modules["retry_failed_conversation_turn"](
                state["session_id"], state["failed_result"].operation_id,
                source="consolidation_fixture_recovery",
            )
            assert recovered.success is True
            assert recovered.user_memory_stored is False and recovered.user_memory_reused is True
            assert recovered.assistant_memory_stored is True
            memories = modules["load_memories"]()
            original_users = [m for m in memories if m.get("type") == "conversation_user" and m.get("conversation_operation_id") == state["failed_result"].operation_id]
            recovery_users = [m for m in memories if m.get("type") == "conversation_user" and m.get("conversation_operation_id") == recovered.operation_id]
            recovery_assistants = [m for m in memories if m.get("type") == "conversation_eidolon" and m.get("conversation_operation_id") == recovered.operation_id]
            assert len(original_users) == 1 and recovery_users == [] and len(recovery_assistants) == 1
            history = modules["conversation_history_for_prompt"](state["session_id"], limit=8)
            assert sum("Retry this exact thought" in row["user_message"] for row in history) == 1
            state["recovered_result"] = recovered
        checks.append(_run_check("failed_turn_recovery_reuses_user_memory_and_commits_one_assistant_reply", recovery_reuses_user_memory_and_commits_once))

        def duplicate_recovery_is_blocked() -> None:
            try:
                modules["retry_failed_conversation_turn"](
                    state["session_id"], state["failed_result"].operation_id,
                    source="consolidation_fixture_recovery",
                )
                raise AssertionError("duplicate recovery unexpectedly succeeded")
            except Exception as error:
                assert "already has a successful recovery" in str(error)
        checks.append(_run_check("successful_recovery_cannot_be_submitted_twice", duplicate_recovery_is_blocked))

        def temporal_curation_changes_future_prompt_only() -> None:
            modules["update_relationship_memory"](state["moment_key"], "resolve")
            modules["update_relationship_memory"](state["mood_key"], "clear")
            result = modules["conversation_runtime"].run_conversation_turn(
                "Give me a direct update without forcing old emotional context.",
                source="consolidation_fixture",
                session_id=state["session_id"],
            )
            assert result.success is True
            prompt = SimulatedConversationClient.prompts[-1]
            assert "focused and optimistic today" not in prompt
            assert "completing the v1079.4 conversation arc" not in prompt
            assert "direct practical answers" in prompt
            memories = modules["load_memories"]()
            assert any(m.get("mood_state") == "cleared" for m in memories if m.get("type") == "user_mood")
            assert any(m.get("moment_state") == "resolved" for m in memories if m.get("type") == "important_moment")
        checks.append(_run_check("cleared_mood_and_resolved_moment_leave_prompt_but_remain_audited_history", temporal_curation_changes_future_prompt_only))

        def receipts_are_redacted_and_content_free() -> None:
            for result in (state["first_result"], state["second_result"], state["failed_result"], state["recovered_result"]):
                receipt = json.loads(Path(result.receipt_path).read_text(encoding="utf-8"))
                raw = json.dumps(receipt, sort_keys=True)
                assert receipt["redacted"] is True
                assert receipt["conversation_session_id"] == state["session_id"]
                assert receipt["contains_prompts"] is False and receipt["contains_generated_responses"] is False
                assert "focused and optimistic today" not in raw
                assert "Retry this exact thought safely" not in raw
                assert "I remember our ongoing thread" not in raw
                assert receipt["governance"]["release_authorized"] is False
                assert receipt["governance"]["autonomous_action_performed"] is False
        checks.append(_run_check("runtime_receipts_preserve_metrics_without_private_conversation_content", receipts_are_redacted_and_content_free))

        def session_files_do_not_embed_receipts() -> None:
            session = modules["load_conversation_session"](state["session_id"], include_turns=True)
            assert session is not None
            assert modules["session_contains_private_receipt_fields"](session) is False
            raw = json.dumps(session, sort_keys=True)
            assert "receipt_path" not in raw and "context_budget" not in raw and "timings_ms" not in raw
        checks.append(_run_check("session_history_contains_no_private_runtime_receipt_fields", session_files_do_not_embed_receipts))

        def organization_preserves_history_and_search_scope() -> None:
            renamed = modules["rename_conversation_session"](state["session_id"], "Consolidated daily conversation")
            assert renamed["title"] == "Consolidated daily conversation"
            assert [item["id"] for item in modules["search_conversation_sessions"]("consolidated daily")] == [state["session_id"]]
            modules["archive_conversation_session"](state["session_id"])
            assert modules["search_conversation_sessions"]("consolidated daily", include_archived=False) == []
            archived = modules["search_conversation_sessions"]("consolidated daily", include_archived=True)
            assert [item["id"] for item in archived] == [state["session_id"]]
            restored = modules["restore_conversation_session"](state["session_id"])
            assert restored["status"] == "active"
            assert modules["select_conversation_session"](state["session_id"])["id"] == state["session_id"]
            assert len(modules["conversation_session_turns"](state["session_id"])) >= 5
        checks.append(_run_check("rename_archive_restore_and_search_preserve_complete_private_history", organization_preserves_history_and_search_scope))

        def experience_state_is_calm_and_governance_neutral() -> None:
            session = modules["load_conversation_session"](state["session_id"], include_turns=True)
            latest = session["turns"][-1]
            settings = modules["load_settings"]()
            experience = modules["build_conversation_experience_state"](
                active_session=session,
                latest_turn=latest,
                settings=settings,
                continuity_summary={"cue_count": 1, "mood_label": "warm"},
            ).public_dict()
            assert experience["state"] == "ready"
            assert experience["session_title"] == "Consolidated daily conversation"
            assert experience["provider_label"] == "llama.cpp"
            raw = json.dumps(experience)
            assert "localhost" not in raw and "receipt" not in raw and "approval" not in raw
        checks.append(_run_check("companion_experience_state_is_redacted_and_does_not_grant_authority", experience_state_is_calm_and_governance_neutral))

        def full_release_smoke_graph_has_single_owners() -> None:
            import release_verify
            steps = release_verify.FULL_RELEASE_SMOKE_STEPS
            labels = [label for label, _args, _timeout in steps]
            assert labels == ["release", "install-release", "install-regression-recent"]
            release_args = next(args for label, args, _timeout in steps if label == "release")
            install_args = next(args for label, args, _timeout in steps if label == "install-release")
            assert release_args == ("--tier", "release")
            assert "--tier" not in install_args or "readiness" not in install_args
            skips = {install_args[index + 1] for index, value in enumerate(install_args[:-1]) if value == "--skip-check"}
            assert skips == {
                "code-patch-release",
                "release-pipeline",
                "approval-release-workflow",
                *release_verify.SUPERSEDED_INSTALL_RELEASE_CHECKS,
            }
        checks.append(_run_check("full_release_smoke_graph_deduplicates_outer_owned_checks", full_release_smoke_graph_has_single_owners))

        def historical_pilot_execution_is_bounded_and_ordered() -> None:
            import smoke_registry_pilot
            original_runner = smoke_registry_pilot._run_smoke_check_subprocess
            original_cache = dict(smoke_registry_pilot._PILOT_EXECUTION_CACHE)
            smoke_registry_pilot._PILOT_EXECUTION_CACHE.clear()
            try:
                smoke_registry_pilot._run_smoke_check_subprocess = lambda _root, _name, timeout_seconds=90.0: {
                    "passed": True, "status": "pass", "returncode": 0, "elapsed_seconds": 0.001,
                    "error": "", "stdout_excerpt": "deterministic fixture",
                }
                rows = smoke_registry_pilot.execute_pilot_smoke_checks(ROOT)
                expected = [row["smoke_name"] for row in smoke_registry_pilot.build_pilot_registry_rows()]
                assert [row["smoke_name"] for row in rows] == expected
                assert len(rows) == 5 and all(row["passed"] is True for row in rows)
                assert all(row["bounded_parallel_execution"] is True for row in rows)
                assert all(row["parallel_worker_limit"] == 3 for row in rows)
                assert all(row["subprocess_timeout_enforced"] is True for row in rows)
            finally:
                smoke_registry_pilot._run_smoke_check_subprocess = original_runner
                smoke_registry_pilot._PILOT_EXECUTION_CACHE.clear()
                smoke_registry_pilot._PILOT_EXECUTION_CACHE.update(original_cache)
        checks.append(_run_check("historical_pilot_execution_is_bounded_and_registry_ordered", historical_pilot_execution_is_bounded_and_ordered))

    finally:
        if original_client is not None:
            try:
                modules["conversation_runtime"].LocalModelClient = original_client
            except Exception:
                pass
        try:
            _restore_tree(EXTERNAL_DATA_DIR, backup)
            restored = True
        except Exception as error:
            restore_error = f"{type(error).__name__}: {error}"

    passed = sum(1 for check in checks if check.get("status") == "pass")
    total = len(checks)
    ok = passed == total and restored
    report = {
        "ok": ok,
        "status": "pass" if ok else "blocked",
        "suite": "v1079.4-conversation-arc-consolidation",
        "evidence_kind": "deterministic_fixture",
        "native_provider_evidence": False,
        "passed": passed,
        "total": total,
        "checks": checks,
        "runtime_data_restored": restored,
        "restore_error": restore_error,
        "simulated_provider_only": True,
        "governance": {
            "provider_selection_operator_controlled": True,
            "model_management_performed": False,
            "approval_granted": False,
            "release_authorized": False,
            "autonomy_expanded": False,
        },
    }
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else f"conversation arc consolidation: {passed}/{total}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
