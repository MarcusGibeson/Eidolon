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
from conversation_quality_diagnostics import quality_diagnostics_contains_private_fields


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


def packet():
    return build_conversation_prompt(
        user_message="Actually, return to the garden topic and explain tomato spacing briefly.",
        self_model={"name": "Eidolon"}, desires={},
        memories=[{"type": "fact", "content": "Tomatoes need room between plants.", "importance": 4}],
        project_context="", goal_context="", task_context="",
        conversation_history=[
            {"user_message": "I am planning a tomato garden.", "assistant_response": "Use a sunny bed.", "continuity_lane": "ordinary"},
            {"user_message": "My printer is broken.", "assistant_response": "Check the error code.", "continuity_lane": "ordinary"},
        ],
        context_size=4096, max_tokens=256,
    )


def test_diagnostics_explain_actual_context_decisions() -> None:
    diagnostics = packet().metrics.conversation_quality_diagnostics
    require(diagnostics["operator_visible"] and diagnostics["read_only"] and diagnostics["content_free"], "diagnostic visibility/boundaries wrong")
    require(diagnostics["intent"]["primary"] == "correction", "intent decision missing")
    require(diagnostics["continuity"]["topic_transition"] in {"return", "resumption"}, "transition decision missing")
    require(diagnostics["context_budget"]["within_budget"], "budget decision wrong")
    require("session_history" in diagnostics["section_decisions"]["included"], "actual included section missing")


def test_diagnostics_do_not_expose_private_content_or_hidden_reasoning() -> None:
    diagnostics = packet().metrics.conversation_quality_diagnostics
    rendered = json.dumps(diagnostics).lower()
    for private in ("tomato spacing", "printer is broken", "sunny bed", "tomatoes need room"):
        require(private not in rendered, f"diagnostic exposed private content: {private}")
    require(not quality_diagnostics_contains_private_fields(diagnostics), "diagnostic contains forbidden private fields")
    boundaries = diagnostics["boundaries"]
    require(not boundaries["hidden_chain_of_thought_exposed"] and not boundaries["prompt_text_exposed"], "hidden reasoning or prompt exposed")


def test_diagnostics_are_bounded_and_structured() -> None:
    diagnostics = packet().metrics.conversation_quality_diagnostics
    require(len(diagnostics["decision_codes"]) <= 24, "decision codes unbounded")
    require(len(diagnostics["section_decisions"]["included"]) <= 24, "included section names unbounded")
    require(len(diagnostics["section_decisions"]["omitted"]) <= 24, "omitted section names unbounded")
    require(set(diagnostics) == {"type", "schema_version", "operator_visible", "read_only", "redacted", "content_free", "decision_codes", "intent", "response_shape", "continuity", "correction", "personality_expression", "context_budget", "section_decisions", "boundaries"}, "diagnostic schema drifted")


def test_diagnostics_are_deterministic_across_reload_equivalent_inputs() -> None:
    first = packet().metrics.conversation_quality_diagnostics
    second = packet().metrics.conversation_quality_diagnostics
    require(first == second, "reload-equivalent diagnostics changed")


def test_diagnostics_do_not_contact_provider_or_write_state() -> None:
    boundaries = packet().metrics.conversation_quality_diagnostics["boundaries"]
    require(not boundaries["provider_invoked"] and not boundaries["writes_state"], "diagnostics contacted provider or wrote state")
    require(not boundaries["mutates_personality"] and not boundaries["rewrites_transcript"], "diagnostics mutated protected state")


def test_runtime_context_metrics_remain_json_safe() -> None:
    metrics = packet().metrics.to_dict()
    encoded = json.dumps(metrics, sort_keys=True)
    decoded = json.loads(encoded)
    require(decoded["conversation_quality_diagnostics"]["type"] == "conversation_quality_diagnostics", "diagnostics missing from runtime context metrics")
    require(decoded["conversation_correction_kind"] != "none", "correction metrics absent")
    require(decoded["conversation_personality_expression_mode"] == "receptive_direct", "expression metrics absent")


def test_registration_metadata_javascript_layout_and_package_privacy() -> None:
    require(tuple(map(int, release_metadata.RUNTIME_VERSION.split("."))) >= (1084, 8), "runtime regressed before v1084.8")
    require(release_metadata.PREVIOUS_RUNTIME_VERSION != release_metadata.RUNTIME_VERSION, "previous runtime version cannot equal current")
    next_token = release_metadata.NEXT_RECOMMENDED_ARC.split()[0].lstrip("v")
    next_version = tuple(int(part) for part in next_token.split(".")[:2])
    require(next_version >= (1084, 9), "next objective regressed before the v1084.9 checkpoint")
    names = (
        "v1084.6-conversational-correction-handling",
        "v1084.7-personality-expression-stability",
        "v1084.8-conversation-quality-diagnostics",
    )
    core = [suite.name for suite in isolated_verify.select_suites("core")]
    full = [suite.name for suite in isolated_verify.select_suites("full")]
    for name in names:
        require(core.count(name) == 1 and full.count(name) == 1, f"registration wrong for {name}")
    release_source = (TOOLS / "release_verify.py").read_text(encoding="utf-8")
    for script in (
        "v1084_6_conversational_correction_handling_tests.py",
        "v1084_7_personality_expression_stability_tests.py",
        "v1084_8_conversation_quality_diagnostics_tests.py",
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
        with tempfile.TemporaryDirectory(prefix="eidolon-v1084-8-js-") as raw:
            cursor, index = 0, 0
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
                cursor, index = end + 9, index + 1

    forbidden = ("data/projects.json", "data/tasks.json", "data/memories.json", "data/approvals/", "data/conversation_runtime/")
    files = [path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if path.is_file() and "__pycache__" not in path.parts]
    require(not [name for name in files if any(name == item or name.startswith(item) for item in forbidden)], "private runtime state present")


TESTS = [
    ("diagnostics_explain_actual_context_decisions", test_diagnostics_explain_actual_context_decisions),
    ("diagnostics_do_not_expose_private_content_or_hidden_reasoning", test_diagnostics_do_not_expose_private_content_or_hidden_reasoning),
    ("diagnostics_are_bounded_and_structured", test_diagnostics_are_bounded_and_structured),
    ("diagnostics_are_deterministic_across_reload_equivalent_inputs", test_diagnostics_are_deterministic_across_reload_equivalent_inputs),
    ("diagnostics_do_not_contact_provider_or_write_state", test_diagnostics_do_not_contact_provider_or_write_state),
    ("runtime_context_metrics_remain_json_safe", test_runtime_context_metrics_remain_json_safe),
    ("registration_metadata_javascript_layout_and_package_privacy", test_registration_metadata_javascript_layout_and_package_privacy),
]


def main() -> int:
    argparse.ArgumentParser().add_argument("--json", action="store_true")
    checks, passed = [], 0
    for name, fn in TESTS:
        try:
            fn()
        except Exception as error:
            checks.append({"name": name, "status": "fail", "message": f"{type(error).__name__}: {error}"})
        else:
            passed += 1
            checks.append({"name": name, "status": "pass", "message": ""})
    report = {"suite": "v1084.8-conversation-quality-diagnostics", "ok": passed == len(TESTS), "status": "pass" if passed == len(TESTS) else "fail", "passed": passed, "total": len(TESTS), "checks": checks}
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
