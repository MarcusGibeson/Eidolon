from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
TOOLS = ROOT / "tools"
sys.path.insert(0, str(AGENT))
sys.path.insert(0, str(TOOLS))

import post_review_development_verify as isolated_verify
import release_metadata
from conversation_context import build_conversation_prompt
from conversation_quality import classify_conversation_quality


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


def history() -> list[dict[str, str]]:
    return [
        {"user_message": "I am planning a vegetable garden with tomatoes and basil.", "assistant_response": "Use a sunny, well-drained bed."},
        {"user_message": "My printer is showing an error code.", "assistant_response": "What error code is displayed?"},
    ]


def test_continuation_uses_latest_thread() -> None:
    transition = classify_conversation_quality("It displays error code E42.", history()).topic_transition
    require(transition.transition_kind == "continuation" and transition.matched_turn_offset == 0, "latest thread continuation missed")


def test_explicit_topic_shift_drops_prior_topic() -> None:
    transition = classify_conversation_quality("New topic: what is a good soup recipe?", history()).topic_transition
    require(transition.transition_kind == "topic_shift" and transition.explicit_transition_cue, "explicit topic shift missed")
    require(transition.matched_turn_offset is None, "topic shift retained old match")


def test_older_topic_resumption_is_distinct() -> None:
    transition = classify_conversation_quality("How much sun do the tomatoes need?", history()).topic_transition
    require(transition.transition_kind == "resumption", "older topic resumption missed")
    require(transition.matched_turn_offset == 1 and transition.best_earlier_overlap_percent >= 30, "older match evidence wrong")


def test_interruption_preserves_prior_thread_without_callback() -> None:
    quality = classify_conversation_quality("Quick question before we continue: what time is it?", history())
    require(quality.topic_transition.transition_kind == "interruption", "side-question interruption missed")
    require(quality.topic_transition.preserves_prior_thread, "interruption did not preserve prior thread")
    require(quality.callbacks.selected_count == 0, "interruption forced prior-topic callback")


def test_explicit_return_is_separate_from_resumption() -> None:
    transition = classify_conversation_quality("Back to the vegetable garden, how far apart should tomatoes be?", history()).topic_transition
    require(transition.transition_kind == "return" and transition.explicit_transition_cue, "explicit return missed")
    require(transition.matched_turn_offset == 1, "return matched wrong topic")


def test_prompt_and_memory_query_follow_resumed_topic() -> None:
    quality = classify_conversation_quality("How much sun do the tomatoes need?", history())
    require("vegetable garden" in quality.memory_query and "printer" not in quality.memory_query, "resumed memory query used wrong thread")
    packet = build_conversation_prompt(
        user_message="How much sun do the tomatoes need?", self_model={"name": "Eidolon"}, desires={}, memories=[], project_context="", goal_context="", task_context="",
        conversation_history=history(), context_size=4096, max_tokens=256,
    )
    require("TOPIC TRANSITION QUALITY" in packet.prompt and "Resume the matching earlier topic" in packet.prompt, "transition guidance missing")
    require(packet.metrics.conversation_topic_transition == "resumption", "transition metric missing")
    require(packet.metrics.conversation_topic_match_offset == 1, "topic offset metric wrong")


def test_registration_metadata_javascript_layout_and_privacy() -> None:
    require(tuple(map(int, release_metadata.RUNTIME_VERSION.split("."))) >= (1084, 5), "runtime regressed before v1084.5")
    require(release_metadata.RUNTIME_MILESTONE.startswith(f"v{release_metadata.RUNTIME_VERSION}"), "current milestone is not aligned to runtime metadata")
    history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
    require("# v1084.5 Conversation Quality Bundle B" in history, "v1084.5 historical milestone disappeared")
    next_token = release_metadata.NEXT_RECOMMENDED_ARC.split()[0].lstrip("v")
    next_version = tuple(int(part) for part in next_token.split(".")[:2])
    require(next_version >= (1084, 6), "next objective regressed before the remaining conversation-quality arc")
    core = [suite.name for suite in isolated_verify.select_suites("core")]
    full = [suite.name for suite in isolated_verify.select_suites("full")]
    names = (
        "v1084.3-unresolved-thread-continuity",
        "v1084.4-natural-conversational-callbacks",
        "v1084.5-topic-transition-quality",
    )
    for name in names:
        require(core.count(name) == 1 and full.count(name) == 1, f"registration wrong for {name}")
    release_source = (TOOLS / "release_verify.py").read_text(encoding="utf-8")
    for script in (
        "v1084_3_unresolved_thread_continuity_tests.py",
        "v1084_4_natural_conversational_callbacks_tests.py",
        "v1084_5_topic_transition_quality_tests.py",
    ):
        require(release_source.count(script) == 1, f"release registration wrong for {script}")

    responsive_source = (AGENT / "dashboard_first_use.py").read_text(encoding="utf-8").replace(" ", "")
    require(
        "@media(max-width:820px)" in responsive_source and "@media(max-width:560px)" in responsive_source,
        "active first-use narrow-layout contract missing",
    )
    import dashboard_chat_console
    html = dashboard_chat_console.render_realtime_chat_panel(None, compact=True)
    node = shutil.which("node")
    if node:
        with tempfile.TemporaryDirectory(prefix="eidolon-v1084-5-js-") as raw:
            cursor = 0
            index = 0
            while True:
                start = html.find("<script>", cursor)
                if start < 0:
                    break
                end = html.find("</script>", start)
                require(end >= 0, "unclosed rendered script")
                path = Path(raw) / f"script-{index}.js"
                path.write_text(html[start + 8:end], encoding="utf-8")
                result = subprocess.run([node, "--check", str(path)], capture_output=True, text=True, timeout=30)
                require(result.returncode == 0, result.stderr or "rendered JavaScript failed syntax validation")
                cursor = end + 9
                index += 1

    forbidden = ("data/projects.json", "data/tasks.json", "data/memories.json", "data/approvals/", "data/conversation_runtime/")
    files = [path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if path.is_file() and "__pycache__" not in path.parts]
    require(not [name for name in files if any(name == item or name.startswith(item) for item in forbidden)], "private runtime state present")


TESTS = [
    ("continuation_uses_latest_thread", test_continuation_uses_latest_thread),
    ("explicit_topic_shift_drops_prior_topic", test_explicit_topic_shift_drops_prior_topic),
    ("older_topic_resumption_is_distinct", test_older_topic_resumption_is_distinct),
    ("interruption_preserves_prior_thread_without_callback", test_interruption_preserves_prior_thread_without_callback),
    ("explicit_return_is_separate_from_resumption", test_explicit_return_is_separate_from_resumption),
    ("prompt_and_memory_query_follow_resumed_topic", test_prompt_and_memory_query_follow_resumed_topic),
    ("registration_metadata_javascript_layout_and_privacy", test_registration_metadata_javascript_layout_and_privacy),
]


def main() -> int:
    argparse.ArgumentParser().add_argument("--json", action="store_true")
    checks = []
    passed = 0
    for name, fn in TESTS:
        try:
            fn()
        except Exception as error:
            checks.append({"name": name, "status": "fail", "message": f"{type(error).__name__}: {error}"})
        else:
            passed += 1
            checks.append({"name": name, "status": "pass", "message": ""})
    report = {"suite": "v1084.5-topic-transition-quality", "ok": passed == len(TESTS), "status": "pass" if passed == len(TESTS) else "fail", "passed": passed, "total": len(TESTS), "checks": checks}
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
