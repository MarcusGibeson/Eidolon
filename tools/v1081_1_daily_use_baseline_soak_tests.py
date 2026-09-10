from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Callable

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
TOOLS = ROOT / "tools"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import chat_action_router as router
import conversation_quality
import dashboard_chat_console as console
import post_review_development_verify as isolated_verify
import release_metadata


class Failure(AssertionError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Failure(message)


def dashboard_source() -> str:
    return (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")


def rendered_panel() -> str:
    return console.render_realtime_chat_panel(None, compact=True)


def rendered_script() -> str:
    html = rendered_panel()
    scripts: list[str] = []
    cursor = 0
    while True:
        start = html.find("<script>", cursor)
        if start < 0:
            break
        end = html.find("</script>", start)
        require(end >= 0, "rendered script tag is unclosed")
        scripts.append(html[start + 8:end])
        cursor = end + 9
    require(scripts, "rendered panel contains no JavaScript")
    return "\n".join(scripts)


def test_runtime_metadata_is_v1081_1() -> None:
    version = tuple(int(part) for part in release_metadata.RUNTIME_VERSION.split("."))
    require(version >= (1081, 1), "runtime metadata regressed below v1081.1")
    require("# v1081.1 Daily-Use Baseline Soak" in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8"), "v1081.1 historical evidence is missing")


def test_established_self_development_phrase_reaches_real_pipeline() -> None:
    phrase = "What should be the next thing we work on you for?"
    profile = conversation_quality.classify_conversation_quality(phrase)
    require(profile.should_analyze_action, "established self-development phrase is blocked before the router")
    action = router.propose_chat_action(phrase, save=False)
    require(action.get("intent") == "self_development_cycle", f"established phrase routed to {action.get('intent')}")

    original_history = console.conversation_history_for_prompt
    original_propose = console.propose_chat_action
    calls: list[str] = []
    try:
        console.conversation_history_for_prompt = lambda *_args, **_kwargs: []
        console.propose_chat_action = lambda message, **_kwargs: calls.append(message) or {"intent": "self_development_cycle"}
        result = console._propose_explicit_chat_action(phrase, "fixture-session", operation_id="fixture-operation")
    finally:
        console.conversation_history_for_prompt = original_history
        console.propose_chat_action = original_propose
    require(result and result.get("intent") == "self_development_cycle", "dashboard pipeline still drops the established phrase")
    require(calls == [phrase], "dashboard pipeline did not invoke the action router exactly once")


def test_common_and_mixed_self_development_wording_routes() -> None:
    phrases = (
        "What should we work on next for you?",
        "What should we work on next for Eidolon?",
        "I feel better now, and also what should we work on next for you?",
    )
    for phrase in phrases:
        require(conversation_quality.should_analyze_chat_action(phrase), f"ordinary self-development wording was not analyzed: {phrase}")
        action = router.propose_chat_action(phrase, save=False)
        require(action.get("intent") == "self_development_cycle", f"ordinary wording routed to {action.get('intent')}: {phrase}")


def test_self_development_routing_resists_casual_planning() -> None:
    phrases = (
        "I wonder what we should work on next in the garden.",
        "What should I work on next for my dog grooming portfolio?",
        "You helped me figure out what to work on next yesterday.",
    )
    for phrase in phrases:
        require(not conversation_quality.should_analyze_chat_action(phrase), f"casual planning became an operator action: {phrase}")
        require(router.propose_chat_action(phrase, save=False).get("intent") == "conversation_only", f"casual planning routed as an action: {phrase}")


def test_action_analysis_still_precedes_provider_generation() -> None:
    source = dashboard_source()
    stream_start = source.index("def stream_dashboard_chat_turn")
    action_index = source.index("_propose_explicit_chat_action", stream_start)
    provider_index = source.index("for item in stream_conversation_turn", stream_start)
    require(action_index < provider_index, "explicit action analysis moved behind provider generation")


def test_coordination_requests_are_bounded() -> None:
    source = dashboard_source()
    require("async function boundedControlFetch" in source, "bounded browser control fetch helper is missing")
    post_start = source.index("async function postCoordination")
    post_end = source.index("async function activateCurrentBrowserTab", post_start)
    block = source[post_start:post_end]
    require("boundedControlFetch('/api/dashboard-chat/coordination'" in block, "tab coordination still uses an unbounded fetch")
    require("}}, 5000);" in block, "tab coordination timeout is not five seconds")
    require("composerSubmissionPending = false;" in source[source.index("if (!await confirmConversationControl())"):], "failed coordination does not release the composer latch")


def test_sse_parser_flushes_a_final_packet_without_blank_delimiter() -> None:
    source = dashboard_source()
    require("function consume(raw, flushFinal)" in source, "SSE parser has no final-flush mode")
    require("function splitSseFrames(rawBuffer, flushFinal)" in source, "SSE frame splitter is missing")
    require("if (flushFinal && source.trim())" in source, "SSE parser drops a trailing complete packet")
    require("consume(decoder.decode(), true);" in source, "stream EOF does not flush the final decoder packet")


def test_clean_eof_reconciles_an_accepted_turn_without_replay() -> None:
    source = dashboard_source()
    flush = source.index("consume(decoder.decode(), true);")
    start = source.index("if (!terminalEventSeen)", flush)
    end = source.index("}} catch (error)", start)
    block = source[start:end]
    for token in (
        "acceptedByRuntime && operationIdForTurn",
        "markReplyForReconciliation(reply, operationIdForTurn)",
        "pollOperation(operationIdForTurn",
        "Nothing was resubmitted",
    ):
        require(token in block, f"clean EOF reconciliation omitted {token}")
    require("fetch('/api/dashboard-chat/stream'" not in block, "clean EOF reconciliation can replay the provider request")


def test_clean_eof_restores_only_an_unaccepted_draft() -> None:
    source = dashboard_source()
    flush = source.index("consume(decoder.decode(), true);")
    start = source.index("if (!terminalEventSeen)", flush)
    end = source.index("}} catch (error)", start)
    block = source[start:end]
    require(
        "resolveAcceptanceByKey(turnSessionId, acceptanceKey)" in block
        or "resolveAcceptanceOutcome(turnSessionId, acceptanceKey, 3)" in block,
        "clean EOF does not resolve uncertain acceptance",
    )
    require("outcome.state === 'not_found'" in block, "clean EOF does not distinguish proven non-acceptance from unavailable status")
    require("restoreUnacceptedDraft(turnSessionId, turnDraftKey, message, turnGeneration)" in block, "unaccepted clean EOF does not restore the draft")
    require("The stream ended before the turn was accepted" in block, "unaccepted clean EOF presentation is missing")


def test_terminal_done_suppresses_clean_eof_recovery() -> None:
    source = dashboard_source()
    done_start = source.index("else if (type === 'done')")
    done_end = source.index("else if (type === 'replace')", done_start)
    require("terminalEventSeen = true;" in source[done_start:done_end], "done events do not suppress clean-EOF recovery")


def test_operation_status_polling_is_bounded_and_backed_off() -> None:
    source = dashboard_source()
    start = source.index("async function pollOperation")
    end = source.index("function setDraftStatus", start)
    block = source[start:end]
    for token in (
        "boundedControlFetch(url, {{ cache:'no-store' }}, 5000)",
        "if (nextFailures >= 18)",
        "Math.min(15000",
        "reconciliation paused after repeated unavailable status checks",
    ):
        require(token in block, f"bounded operation polling omitted {token}")
    require("execute" not in block.lower(), "status polling can execute or retry an action")


def test_dashboard_turn_save_uses_unique_atomic_temporary_files() -> None:
    source = dashboard_source()
    start = source.index("def save_dashboard_chat_turn")
    end = source.index("def _load_json_file", start)
    block = source[start:end]
    for token in ("os.getpid()", "threading.get_ident()", "uuid.uuid4().hex", "os.replace(temporary, path)", "temporary.unlink(missing_ok=True)"):
        require(token in block, f"dashboard turn persistence omitted {token}")
    require('with_suffix(".json.tmp")' not in block, "dashboard turns still share one cross-process temporary filename")


def test_dashboard_turn_cross_process_save_race_does_not_crash() -> None:
    worker = TOOLS / "dashboard_chat_turn_save_race_worker.py"
    with tempfile.TemporaryDirectory(prefix="eidolon-v1081-1-turn-race-") as raw:
        root = Path(raw)
        store = root / "store"
        barrier = root / "barrier"
        barrier.mkdir()
        processes: list[subprocess.Popen[str]] = []
        for writer in ("dashboard", "cli"):
            processes.append(subprocess.Popen(
                [sys.executable, str(worker), "--store", str(store), "--barrier", str(barrier), "--writer", writer],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            ))
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and not all((barrier / f"ready-{writer}").exists() for writer in ("dashboard", "cli")):
            time.sleep(0.02)
        require(all((barrier / f"ready-{writer}").exists() for writer in ("dashboard", "cli")), "subprocess writers did not reach the race barrier")
        (barrier / "release").write_text("go", encoding="utf-8")
        outputs = [process.communicate(timeout=20) for process in processes]
        for process, (stdout, stderr) in zip(processes, outputs):
            require(process.returncode == 0, f"cross-process save crashed: {stderr or stdout}")
            require(json.loads(stdout).get("ok") is True, "cross-process save worker did not report success")
        stored = json.loads((store / "dash_chat_cross_process_same_turn.json").read_text(encoding="utf-8"))
        require(stored.get("writer") in {"dashboard", "cli"}, "cross-process race left invalid JSON")
        require(not list(store.glob("*.tmp")) and not list(store.glob(".*.tmp")), "cross-process save left temporary files")


def test_isolated_worker_has_bounded_orphan_grace() -> None:
    verifier = (TOOLS / "post_review_development_verify.py").read_text(encoding="utf-8")
    worker = (TOOLS / "isolated_suite_worker.py").read_text(encoding="utf-8")
    require('"--handoff-grace", "15"' in verifier, "verifier does not bound orphan-worker grace")
    require('parser.add_argument("--handoff-grace"' in worker, "worker has no handoff-grace control")
    require("min(float(args.handoff_grace), 60.0)" in worker, "worker handoff grace is not bounded")


def test_core_profile_advances_to_v1081_1() -> None:
    selected = {spec.name for spec in isolated_verify.select_suites("core")}
    required = {
        "v1081.1-daily-use-baseline-soak",
        "v1081.0-consolidated-baseline",
        "provider-neutral-conversation",
        "conversation-runtime-critical-path",
    }
    require(required.issubset(selected), f"core profile omitted retained v1081.1 evidence: {sorted(required - selected)}")


def test_rendered_javascript_syntax() -> None:
    with tempfile.TemporaryDirectory(prefix="eidolon-v1081-1-js-") as raw:
        path = Path(raw) / "rendered.js"
        path.write_text(rendered_script(), encoding="utf-8")
        try:
            result = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True, timeout=30)
        except FileNotFoundError:
            return
        require(result.returncode == 0, f"rendered JavaScript syntax failed: {result.stderr.strip()}")


def test_current_docs_metadata_and_release_registration_align() -> None:
    current = release_metadata.RUNTIME_VERSION_TAG
    for relative in (
        "README.md", "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "archive/docs/legacy_dependencies/roadmaps/README_DESKTOP_ALPHA.md",
        "data/settings.json", "data/workspaces/active_project.json", "data/workspaces/projects.json",
    ):
        require(current in (ROOT / relative).read_text(encoding="utf-8"), f"{relative} omits {current}")
    verify = (TOOLS / "release_verify.py").read_text(encoding="utf-8")
    require(verify.count('"daily-use-baseline-soak-fixtures"') == 1, "v1081.1 release stage is not registered exactly once")
    require(verify.count('"tools/v1081_1_daily_use_baseline_soak_tests.py"') == 1, "v1081.1 suite path is not registered exactly once")


def test_source_tree_remains_source_only() -> None:
    require(not (ROOT / "data" / "projects.json").exists(), "source tree contains data/projects.json")
    forbidden = (
        "data/chat_actions", "data/conversation_sessions", "data/dashboard_chat", "data/approvals",
        "data/notifications", "data/tasks.json", "data/memories.json", ".venv", "__pycache__",
    )
    paths = [
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}
    ]
    for token in forbidden:
        require(not any(token in path for path in paths), f"source tree contains forbidden runtime token: {token}")


TESTS: tuple[tuple[str, Callable[[], None]], ...] = (
    ("runtime_metadata_is_v1081_1", test_runtime_metadata_is_v1081_1),
    ("established_self_development_phrase_reaches_real_pipeline", test_established_self_development_phrase_reaches_real_pipeline),
    ("common_and_mixed_self_development_wording_routes", test_common_and_mixed_self_development_wording_routes),
    ("self_development_routing_resists_casual_planning", test_self_development_routing_resists_casual_planning),
    ("action_analysis_still_precedes_provider_generation", test_action_analysis_still_precedes_provider_generation),
    ("coordination_requests_are_bounded", test_coordination_requests_are_bounded),
    ("sse_parser_flushes_a_final_packet_without_blank_delimiter", test_sse_parser_flushes_a_final_packet_without_blank_delimiter),
    ("clean_eof_reconciles_an_accepted_turn_without_replay", test_clean_eof_reconciles_an_accepted_turn_without_replay),
    ("clean_eof_restores_only_an_unaccepted_draft", test_clean_eof_restores_only_an_unaccepted_draft),
    ("terminal_done_suppresses_clean_eof_recovery", test_terminal_done_suppresses_clean_eof_recovery),
    ("operation_status_polling_is_bounded_and_backed_off", test_operation_status_polling_is_bounded_and_backed_off),
    ("dashboard_turn_save_uses_unique_atomic_temporary_files", test_dashboard_turn_save_uses_unique_atomic_temporary_files),
    ("dashboard_turn_cross_process_save_race_does_not_crash", test_dashboard_turn_cross_process_save_race_does_not_crash),
    ("isolated_worker_has_bounded_orphan_grace", test_isolated_worker_has_bounded_orphan_grace),
    ("core_profile_advances_to_v1081_1", test_core_profile_advances_to_v1081_1),
    ("rendered_javascript_syntax", test_rendered_javascript_syntax),
    ("current_docs_metadata_and_release_registration_align", test_current_docs_metadata_and_release_registration_align),
    ("source_tree_remains_source_only", test_source_tree_remains_source_only),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.parse_args()
    checks: list[dict[str, str]] = []
    passed = 0
    for name, test in TESTS:
        try:
            test()
        except Exception as error:
            checks.append({"name": name, "status": "fail", "message": f"{type(error).__name__}: {error}"})
        else:
            passed += 1
            checks.append({"name": name, "status": "pass", "message": ""})
    report = {
        "suite": "v1081.1-daily-use-baseline-soak-and-concrete-defect-repair",
        "ok": passed == len(TESTS),
        "status": "pass" if passed == len(TESTS) else "fail",
        "passed": passed,
        "total": len(TESTS),
        "checks": checks,
        "native_provider_contacted": False,
        "model_management_performed": False,
        "runtime_state_mutated": False,
        "release_authorized": False,
    }
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
