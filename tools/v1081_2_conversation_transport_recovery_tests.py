from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import threading
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

import dashboard_chat_console as console
import post_review_development_verify as isolated_verify
import release_metadata


class Failure(AssertionError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Failure(message)


def source() -> str:
    return (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")


def rendered_script() -> str:
    html = console.render_realtime_chat_panel(None, compact=True)
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


def run_node(body: str) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="eidolon-v1081-2-node-") as raw:
        path = Path(raw) / "transport.js"
        path.write_text(body, encoding="utf-8")
        try:
            result = subprocess.run(["node", str(path)], capture_output=True, text=True, timeout=30)
        except FileNotFoundError:
            return {"skipped": True}
        require(result.returncode == 0, f"node transport fixture failed: {result.stderr.strip()}")
        return json.loads(result.stdout)


def sse_helpers() -> str:
    script = rendered_script()
    start = script.index("function splitSseFrames")
    end = script.index("function transportDelay", start)
    return script[start:end]


def test_runtime_metadata_is_v1081_2_or_newer() -> None:
    version = tuple(int(part) for part in release_metadata.RUNTIME_VERSION.split("."))
    require(version >= (1081, 2), "runtime metadata predates v1081.2")
    require(release_metadata.RUNTIME_VERSION_TAG == f"v{release_metadata.RUNTIME_VERSION}", "runtime tag and version disagree")
    history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
    require("v1081.2 Conversation Transport and Recovery Soak" in history, "v1081.2 historical evidence is missing")


def test_fragmented_crlf_and_lf_sse_frames_parse_in_order() -> None:
    payload = run_node(sse_helpers() + r"""
let buffer = '';
const chunks = [
  'event: accepted\r',
  '\ndata: {"operation_id":"one"}\r\n\r',
  '\nevent: delta\ndata: {"text":"hel"}\n\n',
  'event: delta\r\ndata: {"text":"lo"}\r\n\r\n',
  'event: done\ndata: {"result":{"success":true}}'
];
const events = [];
chunks.forEach(function(chunk, index) {
  const framed = splitSseFrames(buffer + chunk, index === chunks.length - 1);
  buffer = framed.remainder;
  framed.frames.forEach(function(frame) { events.push(parseSseFrame(frame)); });
});
console.log(JSON.stringify({events:events, remainder:buffer}));
""")
    if payload.get("skipped"):
        return
    events = payload.get("events")
    require(isinstance(events, list) and [item.get("type") for item in events] == ["accepted", "delta", "delta", "done"], "fragmented frames changed event order")
    require(payload.get("remainder") == "", "fragmented parser left a remainder")


def test_multiline_data_is_joined_without_trimming_content() -> None:
    payload = run_node(sse_helpers() + r"""
const frame = parseSseFrame('event: message\ndata: first line  \ndata:  second line');
console.log(JSON.stringify(frame));
""")
    if payload.get("skipped"):
        return
    require(payload.get("type") == "message", "multiline fixture changed event type")
    require(payload.get("data") == "first line  \n second line", "multiline data was concatenated or trimmed")


def test_final_packet_without_blank_delimiter_is_flushed_once() -> None:
    payload = run_node(sse_helpers() + r"""
const framed = splitSseFrames('event: done\ndata: {"ok":true}', true);
console.log(JSON.stringify({count:framed.frames.length, parsed:parseSseFrame(framed.frames[0]), remainder:framed.remainder}));
""")
    if payload.get("skipped"):
        return
    require(payload.get("count") == 1 and payload.get("remainder") == "", "final packet was not flushed exactly once")
    require((payload.get("parsed") or {}).get("type") == "done", "final packet lost its event type")


def test_stream_acceptance_request_has_bounded_header_wait() -> None:
    text = source()
    start = text.index("response = await boundedControlFetch('/api/dashboard-chat/stream'")
    end = text.index("if (!response.ok || !response.body)", start)
    block = text[start:end]
    require("}}, 12000);" in block, "initial stream acceptance has no twelve-second bound")
    require("streamStartTimedOut = true" in block, "stream acceptance timeout is not distinguished from cancellation")


def test_transport_silence_starts_read_only_reconciliation() -> None:
    text = source()
    start = text.index("function armTransportWatchdog")
    end = text.index("function noteTransportActivity", start)
    block = text[start:end]
    for token in ("markReplyForReconciliation", "pollOperation(operationIdForTurn", "resolveAcceptanceOutcome", "No retry or duplicate submission occurred"):
        require(token in block, f"transport watchdog omitted {token}")
    require("/api/dashboard-chat/stream" not in block, "transport silence can replay the provider request")
    require("execute" not in block.lower(), "transport silence can execute an action")


def test_keepalive_and_every_complete_frame_refresh_the_watchdog() -> None:
    text = source()
    consume_start = text.index("function consume(raw, flushFinal)")
    consume_end = text.index("let payload = {{}};", consume_start)
    block = text[consume_start:consume_end]
    require("noteTransportActivity();" in block, "complete SSE frames do not refresh transport activity")
    require(block.index("noteTransportActivity();") < block.index("if (!data) continue;"), "data-free keepalive frames cannot refresh the watchdog")


def test_acceptance_resolution_is_bounded_retried_and_tri_state() -> None:
    text = source()
    start = text.index("async function resolveAcceptanceOutcome")
    end = text.index("async function resolveAcceptanceByKey", start)
    block = text[start:end]
    for token in ("Math.min(4", "boundedControlFetch", "3500", "transportDelay", "'accepted'", "'not_found'", "'unavailable'"):
        require(token in block, f"acceptance resolution omitted {token}")


def test_active_session_and_session_cue_recovery_are_bounded() -> None:
    text = source()
    reconcile = text[text.index("async function reconcileActiveSessionSnapshot"):text.index("const stateCopy", text.index("async function reconcileActiveSessionSnapshot"))]
    require("boundedControlFetch('/api/dashboard-chat/active-session'" in reconcile and "8000" in reconcile, "active-session recovery remains unbounded")
    cue = text[text.index("async function refreshSessionCue"):text.index("async function switchConversationSession", text.index("async function refreshSessionCue"))]
    require("boundedControlFetch('/api/dashboard-chat/operation?session_id='" in cue and "5000" in cue, "session-cue recovery remains unbounded")


def test_cancellation_transport_is_bounded_and_never_replayed() -> None:
    text = source()
    start = text.index("cancelButton.addEventListener")
    end = text.index("}})();", start)
    block = text[start:end]
    require("boundedControlFetch('/api/dashboard-chat/cancel'" in block and "}}, 7000);" in block, "cancellation request remains unbounded")
    require("pollOperation(operationToCancel);" in block, "uncertain cancellation does not reconcile the exact operation")
    require("/api/dashboard-chat/stream" not in block, "cancellation recovery can replay a turn")


def test_sleep_wake_back_focus_and_online_paths_reconcile() -> None:
    text = source()
    for token in ("'bfcache-return'", "'sleep-resume'", "'offline-recovery'", "'focus-recovery'"):
        require(token in text, f"browser recovery path omitted {token}")
    require("window.addEventListener('focus'" in text, "window focus recovery is missing")


def test_operation_polling_remains_bounded_and_read_only() -> None:
    text = source()
    start = text.index("async function pollOperation")
    end = text.index("function setDraftStatus", start)
    block = text[start:end]
    for token in ("boundedControlFetch", "if (nextFailures >= 18)", "Math.min(15000"):
        require(token in block, f"operation polling omitted {token}")
    require("/cancel" not in block and "/stream" not in block and "execute" not in block.lower(), "operation polling can mutate or replay")


def test_backend_subscription_emits_keepalive_while_running() -> None:
    operation_id = "conversation_20260719T120000_abcdef123456"
    job = console._DashboardOperationJob(operation_id=operation_id, session_id="fixture-session", turn_id="fixture-turn")
    with console._DASHBOARD_OPERATION_LOCK:
        console._DASHBOARD_OPERATION_JOBS[operation_id] = job
    stream = console.subscribe_dashboard_chat_operation(operation_id)
    started = time.monotonic()
    try:
        event = next(stream)
        require(event.get("event") == "keepalive", f"running subscription emitted {event.get('event')}")
        require(time.monotonic() - started < 2.0, "keepalive exceeded the bounded wait")
    finally:
        job.finish()
        stream.close()
        with console._DASHBOARD_OPERATION_LOCK:
            console._DASHBOARD_OPERATION_JOBS.pop(operation_id, None)


def test_backend_delayed_terminal_events_preserve_order() -> None:
    operation_id = "conversation_20260719T120001_abcdef123457"
    job = console._DashboardOperationJob(operation_id=operation_id, session_id="fixture-session", turn_id="fixture-turn")
    with console._DASHBOARD_OPERATION_LOCK:
        console._DASHBOARD_OPERATION_JOBS[operation_id] = job

    def producer() -> None:
        time.sleep(0.05)
        job.append({"event": "delta", "text": "one"})
        time.sleep(0.05)
        job.append({"event": "conversation_complete", "result": {"success": True}})
        time.sleep(0.05)
        job.append({"event": "done", "result": {"success": True}})
        job.finish()

    thread = threading.Thread(target=producer, daemon=True)
    thread.start()
    stream = console.subscribe_dashboard_chat_operation(operation_id)
    try:
        events = [item.get("event") for item in stream if item.get("event") != "keepalive"]
        require(events == ["delta", "conversation_complete", "done"], f"delayed terminal ordering changed: {events}")
    finally:
        thread.join(timeout=2)
        with console._DASHBOARD_OPERATION_LOCK:
            console._DASHBOARD_OPERATION_JOBS.pop(operation_id, None)


def test_rendered_javascript_syntax() -> None:
    with tempfile.TemporaryDirectory(prefix="eidolon-v1081-2-js-") as raw:
        path = Path(raw) / "rendered.js"
        path.write_text(rendered_script(), encoding="utf-8")
        try:
            result = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True, timeout=30)
        except FileNotFoundError:
            return
        require(result.returncode == 0, f"rendered JavaScript syntax failed: {result.stderr.strip()}")


def test_core_profile_advances_to_v1081_2() -> None:
    selected = {spec.name for spec in isolated_verify.select_suites("core")}
    required = {
        "v1081.2-conversation-transport-recovery",
        "v1081.1-daily-use-baseline-soak",
        "v1081.0-consolidated-baseline",
        "provider-neutral-conversation",
        "conversation-runtime-critical-path",
    }
    require(required.issubset(selected), f"core profile omitted required suites: {sorted(required - selected)}")


def test_current_docs_metadata_and_release_registration_align() -> None:
    current = release_metadata.RUNTIME_VERSION_TAG
    for relative in (
        "README.md", "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "archive/docs/legacy_dependencies/roadmaps/README_DESKTOP_ALPHA.md",
        "data/settings.json", "data/workspaces/active_project.json", "data/workspaces/projects.json",
    ):
        require(current in (ROOT / relative).read_text(encoding="utf-8"), f"{relative} omits {current}")
    verify = (TOOLS / "release_verify.py").read_text(encoding="utf-8")
    require(verify.count('"conversation-transport-recovery-fixtures"') == 1, "v1081.2 release stage is not registered exactly once")
    require(verify.count('"tools/v1081_2_conversation_transport_recovery_tests.py"') == 1, "v1081.2 suite path is not registered exactly once")


def test_source_tree_remains_source_only() -> None:
    require(not (ROOT / "data" / "projects.json").exists(), "source tree contains data/projects.json")
    forbidden = (
        "data/chat_actions", "data/conversation_sessions", "data/dashboard_chat", "data/approvals",
        "data/notifications", "data/tasks.json", "data/memories.json", ".venv", "__pycache__",
    )
    paths = [
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix.lower() not in {".pyc", ".pyo"}
    ]
    for token in forbidden:
        require(not any(token in path for path in paths), f"source tree contains forbidden runtime token: {token}")


TESTS: tuple[tuple[str, Callable[[], None]], ...] = (
    ("runtime_metadata_is_v1081_2_or_newer", test_runtime_metadata_is_v1081_2_or_newer),
    ("fragmented_crlf_and_lf_sse_frames_parse_in_order", test_fragmented_crlf_and_lf_sse_frames_parse_in_order),
    ("multiline_data_is_joined_without_trimming_content", test_multiline_data_is_joined_without_trimming_content),
    ("final_packet_without_blank_delimiter_is_flushed_once", test_final_packet_without_blank_delimiter_is_flushed_once),
    ("stream_acceptance_request_has_bounded_header_wait", test_stream_acceptance_request_has_bounded_header_wait),
    ("transport_silence_starts_read_only_reconciliation", test_transport_silence_starts_read_only_reconciliation),
    ("keepalive_and_every_complete_frame_refresh_the_watchdog", test_keepalive_and_every_complete_frame_refresh_the_watchdog),
    ("acceptance_resolution_is_bounded_retried_and_tri_state", test_acceptance_resolution_is_bounded_retried_and_tri_state),
    ("active_session_and_session_cue_recovery_are_bounded", test_active_session_and_session_cue_recovery_are_bounded),
    ("cancellation_transport_is_bounded_and_never_replayed", test_cancellation_transport_is_bounded_and_never_replayed),
    ("sleep_wake_back_focus_and_online_paths_reconcile", test_sleep_wake_back_focus_and_online_paths_reconcile),
    ("operation_polling_remains_bounded_and_read_only", test_operation_polling_remains_bounded_and_read_only),
    ("backend_subscription_emits_keepalive_while_running", test_backend_subscription_emits_keepalive_while_running),
    ("backend_delayed_terminal_events_preserve_order", test_backend_delayed_terminal_events_preserve_order),
    ("rendered_javascript_syntax", test_rendered_javascript_syntax),
    ("core_profile_advances_to_v1081_2", test_core_profile_advances_to_v1081_2),
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
        "suite": "v1081.2-conversation-transport-and-recovery-soak",
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
