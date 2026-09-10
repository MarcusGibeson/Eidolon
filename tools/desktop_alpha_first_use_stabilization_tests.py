from __future__ import annotations

"""Deterministic v1080.1 first-use conversation and dashboard regressions."""

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Any, Callable

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
EXTERNAL_DATA_DIR = Path(
    os.environ.get("EIDOLON_DATA_DIR")
    or (Path(tempfile.gettempdir()) / "eidolon-v1080-1-first-use-data")
).resolve()
os.environ["EIDOLON_DATA_DIR"] = str(EXTERNAL_DATA_DIR)
sys.path.insert(0, str(AGENT))


def _snapshot() -> dict[str, str]:
    return {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in ROOT.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    }


def _check(name: str, callback: Callable[[], None]) -> dict[str, Any]:
    try:
        callback()
        return {"name": name, "status": "pass"}
    except Exception as error:
        return {
            "name": name,
            "status": "fail",
            "error": f"{type(error).__name__}: {error}",
            "traceback": traceback.format_exc(),
        }


def _prepare_runtime() -> Path:
    backup = Path(tempfile.mkdtemp(prefix="eidolon-v1080-1-first-use-backup-"))
    if EXTERNAL_DATA_DIR.exists():
        shutil.copytree(EXTERNAL_DATA_DIR, backup / "data")
        shutil.rmtree(EXTERNAL_DATA_DIR)
    EXTERNAL_DATA_DIR.mkdir(parents=True)
    shutil.copy2(ROOT / "data" / "settings.json", EXTERNAL_DATA_DIR / "settings.json")
    (EXTERNAL_DATA_DIR / "memories.json").write_text("[]\n", encoding="utf-8")
    (EXTERNAL_DATA_DIR / "self_model.json").write_text(
        json.dumps({"name": "Eidolon", "active_goals": []}), encoding="utf-8"
    )
    (EXTERNAL_DATA_DIR / "desires.json").write_text(
        json.dumps({"values": ["care", "curiosity"]}), encoding="utf-8"
    )
    return backup


def _restore_runtime(backup: Path) -> None:
    shutil.rmtree(EXTERNAL_DATA_DIR, ignore_errors=True)
    if (backup / "data").exists():
        shutil.copytree(backup / "data", EXTERNAL_DATA_DIR)
    shutil.rmtree(backup, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    source_before = _snapshot()
    backup = _prepare_runtime()
    checks: list[dict[str, Any]] = []

    try:
        import conversation_context
        import conversation_quality
        import conversation_runtime
        import dashboard_chat_console
        import dashboard_local_model

        def reported_conversation_remains_conversational() -> None:
            samples = (
                "hey Eid whats up?",
                "Nah right now we'll chill. I Love you",
                "Whats your name?",
                "Do you like the name Eidolon?",
                "What if we changed your name? Can you think of a better one?",
                "What about GLaDOS?",
                "Well, you're my AI. And I love the Portal series and think it'll be cool.",
                "I love jumping through and the change in momentum when you travel through a portal",
            )
            profiles = [conversation_quality.classify_conversation_quality(sample) for sample in samples]
            assert all(not profile.explicit_operator_request for profile in profiles)
            assert all(not profile.should_include_operational_context for profile in profiles)
            assert profiles[1].emotional and profiles[1].flirting
            assert any("conversational_question" in profile.reasons for profile in profiles[2:6])

        checks.append(_check("reported_chat_sequence_stays_in_ordinary_conversation", reported_conversation_remains_conversational))

        def stale_project_coaching_is_not_reinjected() -> None:
            history = [
                {
                    "user_message": "hey Eid whats up?",
                    "assistant_response": "Eidolon: We are making progress on v1078.9 Fresh-Install and Local-Model Integration Validation. Run --project-tree next.",
                },
                {
                    "user_message": "I love the Portal series",
                    "assistant_response": "The momentum shift is one of the cleverest parts of Portal.",
                },
            ]
            packet = conversation_context.build_conversation_prompt(
                user_message="What about the name GLaDOS?",
                self_model={"name": "Eidolon", "active_goals": ["ship v1078.9"]},
                desires={"values": ["care"]},
                memories=[
                    {"type": "task", "content": "Resume v1078.9 validation and run --project-tree", "importance": "high"},
                    {"type": "preference", "content": "Marcus loves the Portal series", "importance": "high"},
                ],
                project_context="v1078.9 Fresh-Install and Local-Model Integration Validation",
                goal_context="Finish the old release candidate",
                task_context="Run --project-tree",
                conversation_history=history,
                context_size=8192,
                max_tokens=350,
            )
            prompt = packet.prompt
            assert "Your runtime is v1080.1" in prompt
            assert "Marcus loves the Portal series" in prompt
            assert "momentum shift" in prompt
            assert "v1078.9" not in prompt
            assert "--project-tree" not in prompt
            assert "ACTIVE PROJECT CONTEXT" not in prompt
            assert packet.metrics.history_turns_included == 1

        checks.append(_check("ordinary_prompt_excludes_stale_project_turns_and_operational_memories", stale_project_coaching_is_not_reinjected))

        def ordinary_history_is_bounded_but_operator_context_survives() -> None:
            history = [
                {"user_message": f"casual {index}", "assistant_response": f"reply {index}"}
                for index in range(10)
            ]
            ordinary = conversation_context.build_conversation_prompt(
                user_message="What do you think?",
                self_model={"name": "Eidolon"}, desires={}, memories=[],
                project_context="Current project context", goal_context="Current goal", task_context="Current task",
                conversation_history=history, context_size=8192, max_tokens=350,
            )
            assert ordinary.metrics.history_turns_included == 6
            assert "casual 3" not in ordinary.prompt and "casual 4" in ordinary.prompt
            operator = conversation_context.build_conversation_prompt(
                user_message="Review the current project and run diagnostics",
                self_model={"name": "Eidolon"}, desires={}, memories=[],
                project_context="Current project context", goal_context="Current goal", task_context="Current task",
                conversation_history=history, context_size=8192, max_tokens=350,
            )
            for label in ("ACTIVE PROJECT CONTEXT", "STRUCTURED GOAL CONTEXT", "TASK QUEUE CONTEXT"):
                assert label in operator.prompt

        checks.append(_check("ordinary_history_is_bounded_while_explicit_operator_context_remains", ordinary_history_is_bounded_but_operator_context_survives))

        def response_prefixes_are_removed_once_for_complete_and_streamed_text() -> None:
            assert conversation_runtime._clean_assistant_response("Eidolon: Hello Marcus") == "Hello Marcus"
            assert conversation_runtime._clean_assistant_response("Assistant: Eidolon: Hello Marcus") == "Hello Marcus"
            cleaner = conversation_runtime._AssistantStreamCleaner("Eidolon")
            visible = "".join(cleaner.feed(part) for part in ("Eido", "lon: ", "I like that name.")) + cleaner.finish()
            assert visible == "I like that name."

        checks.append(_check("provider_role_prefixes_do_not_appear_inside_chat_bubbles", response_prefixes_are_removed_once_for_complete_and_streamed_text))

        def overview_composer_is_bounded_and_sticky() -> None:
            source = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
            html = dashboard_chat_console.render_realtime_chat_panel(None, compact=True)
            assert "realtime-chat-shell compact" in html
            assert "data-chat-version='v1080.1-desktop-alpha-stabilization'" in html
            assert ".realtime-chat-shell.compact .realtime-chat-log" in source
            assert "height:clamp(180px,32dvh,300px)" in source
            assert ".realtime-chat-shell.compact .realtime-chat-form { display:grid; grid-template-columns:minmax(0,1fr); position:sticky" in source
            assert ".realtime-chat-shell.compact .chat-composer-label { display:block; width:100%; min-width:0; }" in source
            assert ".realtime-chat-shell.compact .realtime-chat-form textarea { display:block; width:100%; min-width:0; }" in source
            assert ".realtime-chat-shell.compact .chat-composer-actions { display:grid; grid-template-columns:repeat(2,minmax(0,1fr));" in source
            assert ".realtime-chat-shell.compact .chat-draft-status { grid-column:1 / -1;" in source
            full = dashboard_chat_console.render_realtime_chat_panel(None, compact=False)
            assert "realtime-chat-shell compact" not in full

        checks.append(_check("overview_chat_keeps_a_visible_compact_composer_without_shrinking_chat_console", overview_composer_is_bounded_and_sticky))

        def provider_models_have_described_choices_and_custom_entry() -> None:
            dashboard_local_model.local_model_status = lambda: {
                "models": ["qwen2.5:7b", "custom-generation"],
                "embedding_models": ["nomic-embed-text"],
                "generation": {}, "error": {}, "embedding_error": {},
            }
            dashboard_local_model.configuration_payload = lambda: {
                "values": {
                    "local_model_provider": "ollama",
                    "local_model": "qwen2.5:7b",
                    "embed_model": "nomic-embed-text",
                },
                "provider_profiles": {},
            }
            html = dashboard_local_model.render_local_model_status(
                safe=lambda value: str(value),
                card=lambda title, body: f"<section><h2>{title}</h2>{body}</section>",
                layout=lambda title, body: f"<main><h1>{title}</h1>{body}</main>",
            )
            assert "list='lm-local_model-choices'" in html
            assert "list='lm-embed_model-choices'" in html
            assert "value='qwen2.5:7b'" in html and "7B generation model" in html
            assert "value='nomic-embed-text'" in html and "semantic search and memory retrieval" in html
            assert "Provider-reported embedding candidate" in dashboard_local_model._model_description(
                "qwen2.5:7b", purpose="embedding"
            )
            assert "enter an exact custom identifier" in html.lower()

        checks.append(_check("model_fields_offer_described_provider_choices_and_allow_custom_ids", provider_models_have_described_choices_and_custom_entry))
    finally:
        _restore_runtime(backup)

    checks.append({
        "name": "source_tree_remains_immutable",
        "status": "pass" if _snapshot() == source_before else "fail",
    })
    passed = sum(item.get("status") == "pass" for item in checks)
    report = {
        "suite": "v1080.1-desktop-alpha-first-use-stabilization",
        "status": "pass" if passed == len(checks) else "fail",
        "ok": passed == len(checks),
        "passed": passed,
        "total": len(checks),
        "checks": checks,
        "native_provider_contacted": False,
        "model_management_performed": False,
        "operator_promotion_performed": False,
    }
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else f"{report['suite']}: {passed}/{len(checks)} passed")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
