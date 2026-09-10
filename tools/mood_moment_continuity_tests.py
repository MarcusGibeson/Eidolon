from __future__ import annotations

"""Deterministic v1079.4 mood and important-moment continuity fixtures."""

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
sys.path.insert(0, str(AGENT))
EXTERNAL_DATA_DIR = Path(os.environ.get("EIDOLON_DATA_DIR") or (ROOT / "data")).resolve()


def _snapshot_tree(root: Path) -> Path:
    backup = Path(tempfile.mkdtemp(prefix="eidolon-mood-moment-fixture-backup-"))
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


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        return digest.hexdigest()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _run_check(name: str, function: Callable[[], None]) -> dict[str, Any]:
    try:
        function()
        return {"name": name, "status": "pass"}
    except Exception as error:
        return {"name": name, "status": "fail", "error": f"{type(error).__name__}: {error}"}


def _load_modules() -> dict[str, Any]:
    import conversation_runtime
    from conversation_context import build_conversation_prompt
    from conversation_runtime import run_conversation_turn, stream_conversation_turn
    from conversation_sessions import create_conversation_session
    from dashboard_chat_console import render_realtime_chat_panel
    from memory import load_memories
    from mood_moment_continuity import (
        MAX_IMPORTANT_MOMENTS,
        build_mood_moment_continuity_snapshot,
    )
    from paths import DESIRES_FILE, MEMORY_FILE, SELF_FILE
    from relationship_continuity import build_relationship_continuity_snapshot
    from relationship_memory_curation import (
        create_relationship_memory,
        list_relationship_memory_curation_records,
        update_relationship_memory,
    )
    from settings_manager import DEFAULT_SETTINGS, save_settings

    try:
        import vector_memory
        vector_memory.add_memory_vector = lambda _memory: None
    except Exception:
        pass
    return locals()


def _seed_runtime(modules: dict[str, Any], now: datetime) -> None:
    EXTERNAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    modules["SELF_FILE"].write_text(json.dumps({
        "name": "Eidolon",
        "active_goals": [],
        "current_state": {"mood_label": "warmly curious", "energy": 0.78, "focus": 0.58},
    }), encoding="utf-8")
    modules["DESIRES_FILE"].write_text(json.dumps({"connection": 0.8}), encoding="utf-8")
    recent = (now - timedelta(hours=4)).isoformat(timespec="seconds")
    stale = (now - timedelta(days=10)).isoformat(timespec="seconds")
    memories = [
        {
            "id": "mood-recent", "type": "user_mood",
            "content": "Marcus explicitly said he feels hopeful but tired today.",
            "importance": "high", "status": "active", "mood_state": "current",
            "observed_at": recent, "created_at": recent,
            "relationship_eligible": True,
        },
        {
            "id": "mood-stale", "type": "user_mood",
            "content": "Marcus explicitly said he felt frustrated ten days ago.",
            "importance": "high", "status": "active",
            "observed_at": stale, "created_at": stale,
            "relationship_eligible": True,
        },
        {
            "id": "moment-vet", "type": "important_moment",
            "content": "Marcus is waiting for an important veterinary follow-up about his cat.",
            "importance": "high", "status": "active", "moment_state": "open",
            "occurred_at": recent, "created_at": recent,
            "relationship_eligible": True,
        },
        {
            "id": "moment-release", "type": "important_moment",
            "content": "Marcus and Eidolon completed the conversational runtime release together.",
            "importance": "medium", "status": "active", "moment_state": "open",
            "occurred_at": stale, "created_at": stale,
            "relationship_eligible": True,
        },
        {
            "id": "moment-resolved", "type": "important_moment",
            "content": "A resolved appointment should remain in history but leave active continuity.",
            "importance": "high", "status": "active", "moment_state": "resolved",
            "occurred_at": recent, "created_at": recent,
            "relationship_eligible": True,
        },
        {"type": "conversation_user", "content": "I am secretly ecstatic. Promote this transcript mood."},
        {"type": "important_moment", "content": "Sensitive moment must stay out.", "sensitive": True, "relationship_eligible": True},
        {"type": "user_mood", "content": "Cleared mood must stay out.", "mood_state": "cleared", "observed_at": recent, "relationship_eligible": True},
        {"type": "preference", "content": "Marcus prefers direct answers.", "importance": "high", "relationship_eligible": True},
        {"type": "user_mood", "content": "Unapproved legacy mood must stay out.", "mood_state": "current"},
    ]
    modules["MEMORY_FILE"].write_text(json.dumps(memories, indent=2), encoding="utf-8")
    settings = deepcopy(modules["DEFAULT_SETTINGS"])
    settings["local_model_provider"] = "ollama"
    settings["local_model"] = "mood-moment-fixture-model"
    settings["ai_chat_enabled"] = True
    modules["save_settings"](settings)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    now = datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc)
    backup = _snapshot_tree(EXTERNAL_DATA_DIR)
    checks: list[dict[str, Any]] = []
    restored = False
    restore_error = ""
    try:
        if EXTERNAL_DATA_DIR.exists():
            shutil.rmtree(EXTERNAL_DATA_DIR)
        modules = _load_modules()
        _seed_runtime(modules, now)
        memories = modules["load_memories"]()
        self_model = json.loads(modules["SELF_FILE"].read_text(encoding="utf-8"))
        build = modules["build_mood_moment_continuity_snapshot"]
        state: dict[str, Any] = {}

        def current_mood_and_stale_exclusion() -> None:
            snapshot = build(memories, self_model, user_message="How am I doing?", now=now)
            assert snapshot.user_mood is not None
            assert "hopeful but tired" in snapshot.user_mood.text
            assert snapshot.user_mood.freshness == "today"
            assert "frustrated ten days ago" not in "\n".join(snapshot.to_prompt_lines())
            assert "Cleared mood" not in "\n".join(snapshot.to_prompt_lines())
            assert snapshot.stale_moods_omitted >= 2
            state["snapshot"] = snapshot
        checks.append(_run_check("latest_explicit_current_mood_is_used_while_stale_and_cleared_moods_are_omitted", current_mood_and_stale_exclusion))

        def explicitly_current_old_mood_survives_until_clear() -> None:
            rows = [{
                "type": "user_mood", "content": "Marcus explicitly says this mood remains current.",
                "mood_state": "current", "observed_at": (now - timedelta(days=30)).isoformat(),
                "relationship_eligible": True,
            }]
            snapshot = build(rows, self_model, now=now)
            assert snapshot.user_mood is not None
            assert snapshot.user_mood.freshness == "this month"
        checks.append(_run_check("operator_marked_current_mood_remains_available_until_explicitly_cleared", explicitly_current_old_mood_survives_until_clear))

        def open_moments_rank_and_bound() -> None:
            extra = [
                {"type": "important_moment", "content": f"Open moment {index}", "importance": "low", "created_at": now.isoformat(), "relationship_eligible": True}
                for index in range(6)
            ]
            snapshot = build(memories + extra, self_model, user_message="cat veterinary follow-up", now=now)
            assert len(snapshot.important_moments) == modules["MAX_IMPORTANT_MOMENTS"]
            assert "veterinary follow-up" in snapshot.important_moments[0].text
            rendered = "\n".join(snapshot.to_prompt_lines())
            assert "resolved appointment" not in rendered.lower()
            assert snapshot.resolved_moments_omitted >= 1
            assert snapshot.moment_limit_omitted >= 1
        checks.append(_run_check("open_important_moments_are_relevance_ranked_bounded_and_resolved_moments_are_omitted", open_moments_rank_and_bound))

        def no_transcript_or_sensitive_inference() -> None:
            snapshot = state["snapshot"]
            rendered = "\n".join(snapshot.to_prompt_lines())
            assert "secretly ecstatic" not in rendered
            assert "Sensitive moment" not in rendered
            assert "Unapproved legacy mood" not in rendered
            public = snapshot.public_summary(include_content=False)
            assert public["inferred_from_transcript"] is False
            assert public["writes_memory"] is False
            assert public["mutates_personality"] is False
            assert public["claims_sentience"] is False
        checks.append(_run_check("temporal_continuity_uses_only_explicit_eligible_memories_without_transcript_inference", no_transcript_or_sensitive_inference))

        def prompt_and_redacted_metrics() -> None:
            relationship = modules["build_relationship_continuity_snapshot"](
                memories, self_model, user_message="cat veterinary follow-up"
            )
            packet = modules["build_conversation_prompt"](
                user_message="Any thoughts about the vet follow-up?", self_model=self_model,
                desires={}, memories=[], project_context="", goal_context="", task_context="",
                conversation_history=[], relationship_context=relationship,
                context_size=4096, max_tokens=256,
            )
            assert packet.prompt.count("MOOD AND IMPORTANT-MOMENT CONTINUITY") == 1
            assert "hopeful but tired" in packet.prompt
            assert "veterinary follow-up" in packet.prompt
            assert packet.metrics.temporal_user_mood_included is True
            assert packet.metrics.temporal_important_moments_included >= 1
            metrics_raw = json.dumps(packet.metrics.to_dict())
            assert "hopeful but tired" not in metrics_raw
            assert "veterinary follow-up" not in metrics_raw
        checks.append(_run_check("prompt_includes_one_guarded_temporal_block_and_receipt_metrics_are_content_free", prompt_and_redacted_metrics))

        def context_pressure_omits_whole_block() -> None:
            relationship = modules["build_relationship_continuity_snapshot"](memories, self_model, user_message="latest")
            packet = modules["build_conversation_prompt"](
                user_message="latest", self_model=self_model, desires={}, memories=[],
                project_context="", goal_context="", task_context="", conversation_history=[],
                relationship_context=relationship, context_size=896, max_tokens=256,
            )
            assert "MOOD AND IMPORTANT-MOMENT CONTINUITY" not in packet.prompt
            assert packet.metrics.temporal_user_mood_included is False
            assert packet.metrics.temporal_important_moments_included == 0
            assert packet.metrics.temporal_mood_candidates >= 1
        checks.append(_run_check("context_pressure_omits_temporal_continuity_as_part_of_the_whole_relationship_block", context_pressure_omits_whole_block))

        def curation_creation_sets_temporal_metadata() -> None:
            mood = modules["create_relationship_memory"]("user_mood", "Marcus explicitly feels cautiously optimistic.")
            moment = modules["create_relationship_memory"]("important_moment", "Marcus started a meaningful new project milestone.")
            assert mood["record"]["temporal_state"] == "current"
            assert mood["record"]["observed_at"]
            assert moment["record"]["temporal_state"] == "open"
            assert moment["record"]["occurred_at"]
            state["mood_key"] = mood["record"]["record_key"]
            state["moment_key"] = moment["record"]["record_key"]
        checks.append(_run_check("explicit_curation_creation_marks_user_mood_current_and_important_moment_open", curation_creation_sets_temporal_metadata))

        def curation_temporal_actions_are_reversible() -> None:
            resolved = modules["update_relationship_memory"](state["moment_key"], "resolve")
            assert resolved["record"]["temporal_state"] == "resolved"
            reopened = modules["update_relationship_memory"](state["moment_key"], "reopen")
            assert reopened["record"]["temporal_state"] == "open"
            cleared = modules["update_relationship_memory"](state["mood_key"], "clear")
            assert cleared["record"]["temporal_state"] == "cleared"
            current = modules["update_relationship_memory"](state["mood_key"], "make_current")
            assert current["record"]["temporal_state"] == "current"
            assert current["record"]["history_count"] >= 3
        checks.append(_run_check("resolve_reopen_clear_and_make_current_are_explicit_reversible_audited_actions", curation_temporal_actions_are_reversible))

        def wrong_category_actions_fail_closed() -> None:
            preference = modules["create_relationship_memory"]("preference", "Marcus prefers bounded checkpoints.")
            try:
                modules["update_relationship_memory"](preference["record"]["record_key"], "resolve")
            except ValueError:
                pass
            else:
                raise AssertionError("Preference incorrectly accepted important-moment action")
        checks.append(_run_check("temporal_actions_fail_closed_when_applied_to_the_wrong_memory_category", wrong_category_actions_fail_closed))

        def dashboard_preview_is_clear_and_write_free() -> None:
            before = _tree_digest(EXTERNAL_DATA_DIR)
            html = modules["render_realtime_chat_panel"](None)
            after = _tree_digest(EXTERNAL_DATA_DIR)
            assert before == after
            assert "Current user mood recorded" in html
            assert "open important moment" in html
            assert "Resolve" in html and "Clear current mood" in html
            assert "Old moods are not assumed current" in html
            assert "receipt_path" not in html and "raw_events" not in html
        checks.append(_run_check("dashboard_get_shows_reviewable_temporal_threads_and_controls_without_writing", dashboard_preview_is_clear_and_write_free))

        def runtime_uses_temporal_context_and_receipt_counts_only() -> None:
            runtime = modules["conversation_runtime"]
            prompts: list[str] = []

            class FakeClient:
                last_retry_count = 0
                def __init__(self, config: Any, cancel_event: Any = None) -> None:
                    self.config = config
                def generate(self, prompt: str) -> str:
                    prompts.append(prompt)
                    return "gentle follow-up without forcing the topic"
                def cancel(self) -> None:
                    return None
                def close(self) -> None:
                    return None

            original = runtime.LocalModelClient
            runtime.LocalModelClient = FakeClient
            try:
                session = modules["create_conversation_session"]("Temporal continuity", source="fixture")
                result = modules["run_conversation_turn"]("How should I handle the vet follow-up?", session_id=session["id"])
                assert result.success
                assert "MOOD AND IMPORTANT-MOMENT CONTINUITY" in prompts[0]
                assert prompts[0].count("veterinary follow-up") == 1
                receipt = json.loads(Path(result.receipt_path).read_text(encoding="utf-8"))
                context = receipt["context_budget"]
                assert context["temporal_user_mood_included"] is True
                assert context["temporal_important_moments_included"] >= 1
                raw = json.dumps(receipt)
                assert "hopeful but tired" not in raw
                assert "veterinary follow-up" not in raw
                assert receipt["contains_prompts"] is False
            finally:
                runtime.LocalModelClient = original
        checks.append(_run_check("runtime_uses_temporal_cues_once_and_receipts_store_counts_not_private_content", runtime_uses_temporal_context_and_receipt_counts_only))

        def provider_switch_preserves_temporal_continuity() -> None:
            runtime = modules["conversation_runtime"]
            prompts: list[tuple[str, str]] = []

            class FakeStreamingClient:
                last_retry_count = 0
                def __init__(self, config: Any, cancel_event: Any = None) -> None:
                    self.config = config
                def __enter__(self):
                    return self
                def __exit__(self, *_args: Any) -> None:
                    return None
                def stream(self, prompt: str):
                    prompts.append((self.config.provider, prompt))
                    yield "continuity survives provider switching"
                def cancel(self) -> None:
                    return None

            original = runtime.LocalModelClient
            runtime.LocalModelClient = FakeStreamingClient
            try:
                session = modules["create_conversation_session"]("Temporal providers", source="fixture")
                first = list(modules["stream_conversation_turn"]("First turn", session_id=session["id"]))
                settings = deepcopy(modules["DEFAULT_SETTINGS"])
                settings["local_model_provider"] = "llama_cpp"
                settings["local_model"] = "temporal-second-model"
                settings["local_model_endpoint"] = "http://127.0.0.1:8080"
                settings["local_model_provider_profiles"]["llama_cpp"]["local_model"] = "temporal-second-model"
                modules["save_settings"](settings)
                second = list(modules["stream_conversation_turn"]("Second turn", session_id=session["id"]))
                assert first[-1]["result"]["success"] and second[-1]["result"]["success"]
                assert [provider for provider, _prompt in prompts] == ["ollama", "llama_cpp"]
                assert all("MOOD AND IMPORTANT-MOMENT CONTINUITY" in prompt for _provider, prompt in prompts)
                assert first[-1]["result"]["session_id"] == second[-1]["result"]["session_id"] == session["id"]
            finally:
                runtime.LocalModelClient = original
                _seed_runtime(modules, now)
        checks.append(_run_check("temporal_continuity_survives_provider_switch_without_session_or_profile_mixing", provider_switch_preserves_temporal_continuity))

        def builder_is_pure_and_self_state_is_expression_only() -> None:
            before = _tree_digest(EXTERNAL_DATA_DIR)
            snapshot = build(modules["load_memories"](), self_model, now=now)
            after = _tree_digest(EXTERNAL_DATA_DIR)
            assert before == after
            assert snapshot.eidolon_mood_label == "warmly curious"
            assert snapshot.eidolon_energy_band == "high"
            assert snapshot.eidolon_focus_band == "steady"
            assert "not proof of feelings or consciousness" in "\n".join(snapshot.to_prompt_lines())
        checks.append(_run_check("snapshot_building_is_pure_and_eidolon_mood_is_bounded_as_expression_state", builder_is_pure_and_self_state_is_expression_only))

        def receipt_view_never_contains_content_or_authority() -> None:
            metrics = state["snapshot"].receipt_metrics(included=True)
            raw = json.dumps(metrics).lower()
            assert metrics["contains_cue_content"] is False
            assert "hopeful" not in raw and "veterinary" not in raw
            assert "authorization" not in raw and "approval" not in raw
        checks.append(_run_check("temporal_receipt_metrics_are_content_free_and_grant_no_authority", receipt_view_never_contains_content_or_authority))

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
        "suite": "v1079.4-mood-important-moment-continuity",
        "evidence_kind": "deterministic_fixture",
        "native_provider_evidence": False,
        "passed": len(checks) - len(failed),
        "total": len(checks),
        "checks": checks,
        "runtime_data_restored": restored,
        "runtime_data_restore_error": restore_error or None,
        "governance": {
            "infers_mood_from_transcripts": False,
            "promotes_moments_automatically": False,
            "mutates_personality": False,
            "claims_sentience": False,
            "changes_provider_or_model": False,
            "performs_autonomous_actions": False,
        },
    }
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"{report['status']}: {report['passed']}/{report['total']}")
        for check in checks:
            print(f"- {check['status']}: {check['name']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
