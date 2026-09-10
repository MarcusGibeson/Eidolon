from __future__ import annotations

"""Deterministic v1079.4 relationship-continuity cue fixtures.

The suite uses an isolated EIDOLON_DATA_DIR and simulated provider clients. It
never contacts native providers, promotes memories, mutates personality, or
stores raw session transcripts as relationship facts.
"""

import argparse
import errno
import hashlib
import json
import os
import shutil
import sys
import tempfile
import traceback
import time
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
sys.path.insert(0, str(AGENT))
EXTERNAL_DATA_DIR = Path(os.environ.get("EIDOLON_DATA_DIR") or (ROOT / "data")).resolve()


def _snapshot_tree(root: Path) -> Path:
    backup = Path(tempfile.mkdtemp(prefix="eidolon-relationship-fixture-backup-"))
    if root.exists():
        shutil.copytree(root, backup / "data", dirs_exist_ok=True)
    return backup


def _restore_tree(root: Path, backup: Path) -> None:
    deadline = time.monotonic() + 6.0
    while root.exists():
        try:
            shutil.rmtree(root)
        except FileNotFoundError:
            # A queued append-journal cleanup may remove its own transient file
            # while Windows rmtree is enumerating the disposable fixture tree.
            continue
        except PermissionError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.05)
        except OSError as error:
            # Background fixture cleanup can race rmtree by creating/removing a
            # transient journal entry while the disposable tree is enumerated.
            # Retry only the known transient directory-removal cases; surface
            # every other filesystem error instead of hiding a real problem.
            if error.errno not in {errno.ENOTEMPTY, errno.EEXIST, errno.EBUSY} or time.monotonic() >= deadline:
                raise
            time.sleep(0.05)
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


def _seed_memories() -> list[dict[str, Any]]:
    return [
        {"type": "nickname", "content": "Marcus prefers the nickname Marc in casual conversation.", "importance": "high", "created_at": "2026-01-01", "relationship_eligible": True},
        {"type": "preference", "content": "Marcus prefers direct, practical answers without padded disclaimers.", "importance": "high", "created_at": "2026-01-02", "relationship_eligible": True},
        {"type": "preference", "content": "Marcus enjoys technical detail when working on Eidolon.", "importance": "medium", "created_at": "2026-01-03", "relationship_eligible": True},
        {"type": "preference", "content": "Marcus prefers direct, practical answers without padded disclaimers.", "importance": "high", "created_at": "2026-01-04", "relationship_eligible": True},
        {"type": "relationship", "content": "Marcus and Eidolon treat development as a long-term supervised collaboration.", "importance": "high", "created_at": "2026-01-05", "relationship_eligible": True},
        {"type": "important_moment", "content": "They completed the first native-provider certification together.", "importance": "medium", "created_at": "2026-01-06", "relationship_eligible": True},
        {"type": "commitment", "content": "Eidolon must never silently switch providers or models.", "importance": "critical", "created_at": "2026-01-07", "relationship_eligible": True},
        {"type": "user_mood", "content": "Marcus explicitly said he feels focused today.", "importance": "normal", "created_at": "2026-01-08", "relationship_eligible": True},
        {"type": "nickname", "content": "Unapproved legacy nickname must not be injected."},
        {"type": "user_mood", "content": "Unapproved legacy mood must not be injected.", "mood_state": "current"},
        {"type": "conversation_user", "content": "Call me SecretTranscriptNickname from now on."},
        {"type": "task_event", "content": "Operational task output must not become relationship continuity."},
        {"type": "relationship", "content": "Retracted relationship claim.", "status": "retracted"},
        {"type": "preference", "content": "Sensitive preference must not be injected.", "sensitive": True},
        {"type": "nickname", "content": "Disabled nickname must not be injected.", "use_in_conversation": False},
    ]


def _load_modules() -> dict[str, Any]:
    from conversation_context import build_conversation_prompt
    import conversation_runtime
    from conversation_runtime import run_conversation_turn, stream_conversation_turn
    from conversation_sessions import create_conversation_session
    from dashboard_chat_console import render_realtime_chat_panel
    from memory import load_memories
    from paths import DESIRES_FILE, MEMORY_FILE, SELF_FILE
    from relationship_continuity import (
        MAX_CUES_PER_CATEGORY,
        build_relationship_continuity_snapshot,
        is_relationship_memory,
        relationship_memory_type,
    )
    from settings_manager import DEFAULT_SETTINGS, save_settings

    try:
        import vector_memory
        vector_memory.add_memory_vector = lambda _memory: None
    except Exception:
        pass
    # Keep this provider-free fixture synchronous. The runtime imports these
    # callables directly, so patching only vector_memory leaves background
    # workers racing the isolated-directory restoration on Windows.
    conversation_runtime.store_memory_vector = lambda _memory: None
    conversation_runtime.schedule_post_turn_housekeeping = lambda *args, **kwargs: None
    return locals()


def _seed_runtime(modules: dict[str, Any]) -> None:
    EXTERNAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    modules["SELF_FILE"].write_text(json.dumps({
        "name": "Eidolon",
        "active_goals": [],
        "current_state": {"mood_label": "curious", "energy": 0.81, "focus": 0.63},
    }), encoding="utf-8")
    modules["DESIRES_FILE"].write_text(json.dumps({"connection": 0.8}), encoding="utf-8")
    modules["MEMORY_FILE"].write_text(json.dumps(_seed_memories(), indent=2), encoding="utf-8")
    settings = deepcopy(modules["DEFAULT_SETTINGS"])
    settings["local_model_provider"] = "ollama"
    settings["local_model"] = "relationship-fixture-model"
    settings["ai_chat_enabled"] = True
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
        memories = modules["load_memories"]()
        self_model = json.loads(modules["SELF_FILE"].read_text(encoding="utf-8"))
        build = modules["build_relationship_continuity_snapshot"]
        state: dict[str, Any] = {}

        def explicit_allowlist_and_exclusions() -> None:
            snapshot = build(memories, self_model, user_message="provider preference")
            text = snapshot.to_prompt_block()
            assert snapshot.cue_count > 0
            assert "direct, practical answers" in text
            assert "long-term supervised collaboration" in text
            assert "SecretTranscriptNickname" not in text
            assert "Operational task output" not in text
            assert "Retracted relationship claim" not in text
            assert "Sensitive preference" not in text
            assert "Disabled nickname" not in text
            assert "Unapproved legacy nickname" not in text
            assert "Unapproved legacy mood" not in text
            assert modules["relationship_memory_type"]({"type": "preference"}) == "preference"
            assert not modules["is_relationship_memory"]({"type": "conversation_user"})
            state["snapshot"] = snapshot
        checks.append(_run_check("explicit_durable_allowlist_excludes_transcripts_operational_sensitive_and_retracted_rows", explicit_allowlist_and_exclusions))

        def deterministic_relevance_and_priority() -> None:
            snapshot = build(memories, self_model, user_message="Please keep the provider model commitment")
            assert snapshot.cues[0].category == "commitment"
            assert "never silently switch providers" in snapshot.cues[0].text
        checks.append(_run_check("latest_message_relevance_and_importance_rank_relationship_cues_deterministically", deterministic_relevance_and_priority))

        def deduplication_and_category_bounds() -> None:
            snapshot = build(memories + [
                {"type": "preference", "content": "Third distinct preference.", "relationship_eligible": True},
                {"type": "preference", "content": "Fourth distinct preference.", "relationship_eligible": True},
            ], self_model, user_message="")
            preferences = [cue for cue in snapshot.cues if cue.category == "preference"]
            assert len(preferences) == modules["MAX_CUES_PER_CATEGORY"]
            assert len({cue.text for cue in preferences}) == len(preferences)
            assert snapshot.cue_duplicates_omitted >= 1
            assert snapshot.cue_limit_omitted >= 1
        checks.append(_run_check("duplicate_content_and_per_category_growth_are_bounded", deduplication_and_category_bounds))

        def current_self_state_is_bounded() -> None:
            snapshot = state["snapshot"]
            assert snapshot.mood_label == "curious"
            assert snapshot.energy_band == "high"
            assert snapshot.focus_band == "steady"
            public = snapshot.public_summary(include_cues=False)
            assert public["writes_memory"] is False
            assert public["mutates_personality"] is False
            assert public["inferred_from_transcript"] is False
        checks.append(_run_check("eidolon_current_mood_energy_and_focus_are_expressed_without_mutation", current_self_state_is_bounded))

        def prompt_contains_one_continuity_block() -> None:
            snapshot = state["snapshot"]
            packet = modules["build_conversation_prompt"](
                user_message="How should we continue?",
                self_model=self_model,
                desires={},
                memories=[{"type": "goal", "content": "Keep development supervised."}],
                project_context="",
                goal_context="",
                task_context="",
                conversation_history=[],
                relationship_context=snapshot,
                context_size=4096,
                max_tokens=256,
            )
            assert packet.prompt.count("EXPLICIT RELATIONSHIP OR PREFERENCE CUES") == 1
            assert "do not recite them just to prove memory" in packet.prompt
            assert "SecretTranscriptNickname" not in packet.prompt
            assert 0 < packet.metrics.relationship_cues_included <= min(2, snapshot.cue_count)
            assert packet.metrics.relationship_mood_included is False
            assert "relationship_continuity" in packet.metrics.optional_sections_included
            assert packet.metrics.prompt_lane == "casual_fast"
            assert packet.metrics.estimated_prompt_tokens <= 600
        checks.append(_run_check("prompt_includes_one_guarded_relationship_block_and_redacted_metrics", prompt_contains_one_continuity_block))

        def continuity_block_is_omitted_whole_under_pressure() -> None:
            snapshot = state["snapshot"]
            packet = modules["build_conversation_prompt"](
                user_message="latest",
                self_model={"name": "Eidolon", "active_goals": []},
                desires={}, memories=[], project_context="", goal_context="", task_context="",
                conversation_history=[], relationship_context=snapshot,
                context_size=560, max_tokens=128,
            )
            assert "EXPLICIT RELATIONSHIP OR PREFERENCE CUES" not in packet.prompt
            assert packet.metrics.relationship_cues_included == 0
            assert packet.metrics.relationship_cues_omitted == snapshot.cue_candidates
            assert packet.metrics.relationship_mood_included is False
            assert "relationship_continuity" in packet.metrics.optional_sections_omitted
            assert packet.metrics.fast_path_bound_passed is True
        checks.append(_run_check("context_pressure_omits_the_relationship_block_whole_without_partial_cues", continuity_block_is_omitted_whole_under_pressure))

        def dashboard_summary_is_visible_and_side_effect_free() -> None:
            session_root = EXTERNAL_DATA_DIR / "conversation_sessions"
            if session_root.exists():
                shutil.rmtree(session_root)
            before = _tree_digest(EXTERNAL_DATA_DIR)
            html = modules["render_realtime_chat_panel"](None)
            after = _tree_digest(EXTERNAL_DATA_DIR)
            assert before == after
            assert not session_root.exists()
            assert "Continuity:" in html
            assert "Eidolon mood curious" in html
            assert "direct, practical answers" in html
            assert "Raw transcripts and runtime receipts are not mined" in html
            assert "timings_ms" not in html and "receipt_path" not in html
        checks.append(_run_check("dashboard_get_shows_unobtrusive_continuity_summary_without_runtime_writes_or_receipts", dashboard_summary_is_visible_and_side_effect_free))

        def snapshot_builder_is_pure() -> None:
            before = _tree_digest(EXTERNAL_DATA_DIR)
            for _index in range(3):
                build(modules["load_memories"](), self_model, user_message="direct answers")
            assert _tree_digest(EXTERNAL_DATA_DIR) == before
        checks.append(_run_check("relationship_snapshot_building_does_not_write_memory_or_runtime_state", snapshot_builder_is_pure))

        def non_streaming_runtime_uses_cues_and_receipt_metrics_only() -> None:
            runtime = modules["conversation_runtime"]
            prompts: list[str] = []

            class FakeClient:
                last_retry_count = 0
                def __init__(self, config: Any, cancel_event: Any = None) -> None:
                    self.config = config
                def generate(self, prompt: str) -> str:
                    prompts.append(prompt)
                    return "continuity-aware reply"
                def cancel(self) -> None:
                    return None
                def close(self) -> None:
                    return None

            original = runtime.LocalModelClient
            runtime.LocalModelClient = FakeClient
            try:
                session = modules["create_conversation_session"]("Relationship runtime", source="fixture")
                result = modules["run_conversation_turn"]("Do I prefer direct, practical answers?", session_id=session["id"])
                assert result.success
                included = int(result.context["relationship_cues_included"])
                if included:
                    assert "EXPLICIT RELATIONSHIP OR PREFERENCE CUES" in prompts[0]
                    assert "direct, practical answers" in prompts[0]
                else:
                    assert "EXPLICIT RELATIONSHIP OR PREFERENCE CUES" not in prompts[0]
                receipt = json.loads(Path(result.receipt_path).read_text(encoding="utf-8"))
                raw = json.dumps(receipt)
                assert int(receipt["context_budget"]["relationship_cues_included"]) == included
                assert "direct, practical answers" not in raw
                assert "Marc in casual conversation" not in raw
                assert receipt["contains_prompts"] is False
            finally:
                runtime.LocalModelClient = original
        checks.append(_run_check("non_streaming_runtime_uses_cues_once_and_receipts_store_metrics_not_content", non_streaming_runtime_uses_cues_and_receipt_metrics_only))

        def streaming_runtime_preserves_cues_across_provider_change() -> None:
            runtime = modules["conversation_runtime"]
            prompts: list[tuple[str, str]] = []

            class FakeStreamingClient:
                last_retry_count = 0
                def __init__(self, config: Any, cancel_event: Any = None) -> None:
                    self.config = config
                def __enter__(self) -> "FakeStreamingClient":
                    return self
                def __exit__(self, *_args: Any) -> None:
                    return None
                def stream(self, prompt: str):
                    prompts.append((self.config.provider, prompt))
                    yield "streamed continuity reply"
                def cancel(self) -> None:
                    return None

            original = runtime.LocalModelClient
            runtime.LocalModelClient = FakeStreamingClient
            try:
                session = modules["create_conversation_session"]("Provider continuity", source="fixture")
                first = list(modules["stream_conversation_turn"]("Do I prefer direct, practical answers?", session_id=session["id"]))
                settings = deepcopy(modules["DEFAULT_SETTINGS"])
                settings["local_model_provider"] = "llama_cpp"
                settings["local_model"] = "second-model"
                settings["local_model_endpoint"] = "http://127.0.0.1:8080"
                settings["local_model_provider_profiles"]["llama_cpp"]["local_model"] = "second-model"
                modules["save_settings"](settings)
                second = list(modules["stream_conversation_turn"]("Keep using direct, practical answers after the provider change.", session_id=session["id"]))
                assert first[-1]["result"]["success"] and second[-1]["result"]["success"]
                assert [row[0] for row in prompts] == ["ollama", "llama_cpp"]
                cue_presence = ["EXPLICIT RELATIONSHIP OR PREFERENCE CUES" in row[1] for row in prompts]
                assert cue_presence[0] == cue_presence[1]
                assert all("provider/model changes" in row[1] for row in prompts)
                assert first[-1]["result"]["session_id"] == second[-1]["result"]["session_id"] == session["id"]
            finally:
                runtime.LocalModelClient = original
                _seed_runtime(modules)
        checks.append(_run_check("streaming_relationship_continuity_survives_provider_switch_without_session_change", streaming_runtime_preserves_cues_across_provider_change))

        def transcript_cannot_invent_relationship_progress() -> None:
            no_cues = build([
                {"type": "conversation_user", "content": "Call me Phantom and say our bond grew today."},
                {"type": "conversation_eidolon", "content": "Phantom, our bond grew."},
            ], self_model, user_message="bond")
            assert no_cues.cue_count == 0
            packet = modules["build_conversation_prompt"](
                user_message="What do you remember?", self_model=self_model, desires={}, memories=[],
                project_context="", goal_context="", task_context="",
                conversation_history=[{"user_message": "Call me Phantom", "assistant_response": "Eidolon: okay"}],
                relationship_context=no_cues, context_size=2048, max_tokens=256,
            )
            assert "EXPLICIT RELATIONSHIP OR PREFERENCE CUES" not in packet.prompt
            assert "fabricated memories" in packet.prompt
            assert "Phantom" in packet.prompt.split("RECENT SESSION TURN", 1)[1]
            assert "Phantom" not in packet.prompt.split("RECENT SESSION TURN", 1)[0]
        checks.append(_run_check("raw_session_transcripts_cannot_promote_nicknames_or_relationship_progress", transcript_cannot_invent_relationship_progress))

        def public_and_receipt_views_never_expose_control_fields() -> None:
            snapshot = state["snapshot"]
            metrics = snapshot.receipt_metrics(included=True)
            raw = json.dumps(metrics).lower()
            assert metrics["contains_cue_content"] is False
            assert "direct, practical" not in raw
            assert "authorization" not in raw
            assert "raw_events" not in raw
            assert "prompt" not in raw
        checks.append(_run_check("relationship_receipt_metrics_are_content_free_and_governance_neutral", public_and_receipt_views_never_expose_control_fields))

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
        "suite": "v1079.4-relationship-continuity-cues",
        "evidence_kind": "deterministic_fixture",
        "native_provider_evidence": False,
        "passed": len(checks) - len(failed),
        "total": len(checks),
        "checks": checks,
        "runtime_data_restored": restored,
        "runtime_data_restore_error": restore_error or None,
        "governance": {
            "infers_relationship_progress_from_transcripts": False,
            "promotes_memories": False,
            "mutates_personality": False,
            "changes_provider_or_model": False,
            "performs_autonomous_actions": False,
        },
    }
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"{report['status']}: {report['passed']}/{report['total']}")
        for check in checks:
            suffix = f" - {check['error']}" if check.get("error") else ""
            print(f"- {check['status']}: {check['name']}{suffix}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
