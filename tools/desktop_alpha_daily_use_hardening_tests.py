from __future__ import annotations

"""Deterministic v1079.9.1 Desktop Alpha daily-use soak repair fixtures.

The suite uses simulated provider transport only. Runtime files are confined to
EIDOLON_DATA_DIR and the source tree must remain byte-for-byte unchanged.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
sys.path.insert(0, str(AGENT))
EXTERNAL_DATA_DIR = Path(os.environ.get("EIDOLON_DATA_DIR") or (ROOT / "data")).resolve()


def _snapshot() -> dict[str, str]:
    ignored = {"__pycache__", ".pytest_cache"}
    result: dict[str, str] = {}
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in ignored for part in path.parts):
            continue
        result[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _check(name: str, callback: Callable[[], None]) -> dict[str, Any]:
    try:
        callback()
        return {"name": name, "status": "pass"}
    except Exception as error:
        return {"name": name, "status": "fail", "error": f"{type(error).__name__}: {error}"}


def _prepare_runtime() -> None:
    if EXTERNAL_DATA_DIR.exists():
        shutil.rmtree(EXTERNAL_DATA_DIR)
    EXTERNAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    source_settings = ROOT / "data" / "settings.json"
    shutil.copy2(source_settings, EXTERNAL_DATA_DIR / "settings.json")
    (EXTERNAL_DATA_DIR / "memories.json").write_text("[]\n", encoding="utf-8")
    (EXTERNAL_DATA_DIR / "self_model.json").write_text(json.dumps({"name": "Eidolon", "active_goals": []}), encoding="utf-8")
    (EXTERNAL_DATA_DIR / "desires.json").write_text(json.dumps({"values": ["continuity", "care"]}), encoding="utf-8")


def _rendered_javascript(html: str) -> str:
    start = html.index("<script>") + len("<script>")
    end = html.index("</script>", start)
    return html[start:end]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    source_before = _snapshot()
    runtime_backup = Path(tempfile.mkdtemp(prefix="eidolon-v1079-9-runtime-backup-")) / "data"
    if EXTERNAL_DATA_DIR.exists():
        shutil.copytree(EXTERNAL_DATA_DIR, runtime_backup)
    checks: list[dict[str, Any]] = []
    try:
        _prepare_runtime()
        import conversation_runtime
        import dashboard_chat_console
        import vector_memory
        from conversation_sessions import append_conversation_turn, create_conversation_session, load_conversation_session

        vector_memory.add_memory_vector = lambda _memory: None
        source = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
        html = dashboard_chat_console.render_realtime_chat_panel(None)
        javascript = _rendered_javascript(html)

        def stale_turns_cannot_override_foreground_status() -> None:
            assert "let foregroundTurnSequence = 0;" in source
            assert "const turnUiSequence = ++foregroundTurnSequence;" in source
            assert "const foreground = turnUiSequence === foregroundTurnSequence && turnIsCurrent;" in source
            assert "applyOperationStatus(payload, {{ updateStatus:foreground }})" in source
            assert "if (!updateStatus) return;" in source
            assert "pollOperation(operationIdForTurn, {{ uiSequence:turnUiSequence" in source
            assert "appendReconciledTurn(payload.session_turn, marker, {{ updateStatus:updateStatus }})" in source
            assert "applyFailurePresentation(turn.failure_category || turn.completion_state, existingReply, options)" in source
        checks.append(_check("older_consecutive_turns_cannot_overwrite_newer_status_controls_or_latency", stale_turns_cannot_override_foreground_status))

        def failure_state_is_per_reply() -> None:
            assert "reply.dataset.failureCategory" in source
            assert "activeFailureCategory" not in source
            assert "applyFailurePresentation(payload.failure_category, reply, {{ updateStatus:foreground }})" in source
        checks.append(_check("late_failure_from_an_older_turn_cannot_poison_a_newer_reply", failure_state_is_per_reply))

        def uncertain_delivery_reconciles_before_restore() -> None:
            start = source.index("if (!response.ok || !response.body)")
            end = source.index("const reader = response.body.getReader()", start)
            block = source[start:end]
            assert block.index("resolveAcceptanceByKey(turnSessionId, acceptanceKey)") < block.index("restoreUnacceptedDraft")
            assert "Nothing was resubmitted" in block
            assert "clearAcceptedDraft" in block and "pollOperation" in block
            assert "markReplyForReconciliation(reply, operationIdForTurn)" in block
            assert "reply.dataset.reconciliationPending = 'true'" in source
        checks.append(_check("uncertain_initial_delivery_reuses_the_original_acceptance_before_draft_restore", uncertain_delivery_reconciles_before_restore))

        def streaming_is_painted_in_bounded_frames() -> None:
            assert "function queueReplyText(text)" in source
            assert "window.requestAnimationFrame" in source
            assert "window.cancelAnimationFrame" in source
            delta = source[source.index("type === 'delta'"):source.index("type === 'conversation_complete'")]
            assert "queueReplyText(visibleText)" in delta
            assert "reply.textContent += payload.text" not in delta
            for event in ("conversation_complete", "type === 'done'", "type === 'replace'", "type === 'error'"):
                assert event in source
            assert source.count("flushReplyText();") >= 5
        checks.append(_check("long_streams_batch_visible_dom_updates_without_hiding_text", streaming_is_painted_in_bounded_frames))

        def dashboard_first_token_is_visible_text() -> None:
            delta = source[source.index("type === 'delta'"):source.index("type === 'conversation_complete'")]
            assert "visibleText.trim()" in delta
            assert "firstToken.textContent" in delta
        checks.append(_check("dashboard_first_token_clock_ignores_empty_or_whitespace_chunks", dashboard_first_token_is_visible_text))

        def runtime_records_transport_and_visible_timing() -> None:
            original_client = conversation_runtime.LocalModelClient

            class FakeClient:
                last_retry_count = 0
                def __init__(self, *_args: Any, **_kwargs: Any) -> None: pass
                def __enter__(self): return self
                def __exit__(self, *_args: Any) -> None: return None
                def close(self) -> None: return None
                def cancel(self) -> None: return None
                def stream(self, _prompt: str):
                    yield "Eid"
                    time.sleep(0.006)
                    yield "olon:"
                    time.sleep(0.006)
                    yield " A visible reply."

            conversation_runtime.LocalModelClient = FakeClient
            try:
                events = list(conversation_runtime.stream_conversation_turn(
                    "Hello there", use_ai=True, operation_id="conversation_20260717T120000_abcdef123456"
                ))
            finally:
                conversation_runtime.LocalModelClient = original_client
            done = next(item for item in events if item.get("event") == "done")
            timings = done["result"]["timings_ms"]
            assert timings["first_transport_chunk"] is not None
            assert timings["first_visible_token"] is not None
            assert timings["first_token"] == timings["first_visible_token"]
            assert timings["first_visible_token"] >= timings["first_transport_chunk"]
            receipt_path = Path(done["result"]["receipt_path"])
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            encoded = json.dumps(receipt)
            assert "Hello there" not in encoded and "A visible reply" not in encoded and "Eidolon:" not in encoded
            assert receipt["timings_ms"]["first_visible_token"] == timings["first_visible_token"]
        checks.append(_check("runtime_receipt_distinguishes_transport_from_first_visible_token_without_private_text", runtime_records_transport_and_visible_timing))

        def long_session_retention_is_bounded_and_lossless() -> None:
            session = create_conversation_session("Desktop Alpha long session", source="fixture")
            for index in range(200):
                append_conversation_turn(
                    session["id"], turn_id=f"desktop-alpha-{index:03d}",
                    user_message=f"Message {index}", assistant_response=f"Response {index}",
                    completion_state="completed", success=True, provider="fixture", model="fixture",
                )
            loaded = load_conversation_session(session["id"], include_turns=True)
            assert loaded and loaded["turn_count"] == 200
            assert len(loaded["turns"]) == 200
            assert len({turn["id"] for turn in loaded["turns"]}) == 200
            rendered = dashboard_chat_console.render_realtime_chat_panel(None)
            assert "Message 0" in rendered and "Response 199" in rendered
            snapshot = dashboard_chat_console.dashboard_chat_session_snapshot(session["id"])
            assert "Message 0" in snapshot["transcript_html"] and "Response 199" in snapshot["transcript_html"]
            assert snapshot["transcript_html"].count("data-session-turn-id=") == 200
        checks.append(_check("two_hundred_turn_im_session_remains_lossless_and_duplicate_free", long_session_retention_is_bounded_and_lossless))

        def keyboard_focus_accessibility_and_layout_contracts_remain() -> None:
            for token in (
                "messageBox.addEventListener('keydown'", "messageBox.addEventListener('beforeinput'",
                "enterkeyhint='send'", "Shift+Enter adds a new line", "focusComposer()",
                "aria-live='polite'", "chat-jump-latest",
                "pageshow", "visibilitychange", "online", "offline",
            ):
                assert token in html
            assert "@media (max-width:620px)" in source
        checks.append(_check("keyboard_focus_accessibility_history_return_and_narrow_layout_contracts_survive", keyboard_focus_accessibility_and_layout_contracts_remain))

        def no_governance_or_provider_management_expansion() -> None:
            changed = source.lower()
            assert "install model" not in changed
            assert "delete model" not in changed
            assert "switch provider automatically" not in changed
            assert "nothing was resubmitted" in changed
            assert "no second request was submitted automatically" in changed
        checks.append(_check("daily_use_repairs_add_no_model_management_fallback_or_autonomy", no_governance_or_provider_management_expansion))

        def rendered_javascript_parses() -> None:
            node = shutil.which("node")
            if not node:
                compile(javascript, "<dashboard-js-contract>", "exec")  # guaranteed to fail if accidentally treated as Python
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as handle:
                handle.write(javascript)
                path = Path(handle.name)
            try:
                completed = subprocess.run([node, "--check", str(path)], capture_output=True, text=True, timeout=30)
                assert completed.returncode == 0, completed.stderr
            finally:
                path.unlink(missing_ok=True)
        checks.append(_check("rendered_dashboard_javascript_syntax_is_valid", rendered_javascript_parses))

    finally:
        if EXTERNAL_DATA_DIR.exists():
            shutil.rmtree(EXTERNAL_DATA_DIR)
        if runtime_backup.exists():
            shutil.copytree(runtime_backup, EXTERNAL_DATA_DIR)
        shutil.rmtree(runtime_backup.parent, ignore_errors=True)

    checks.append({"name": "source_tree_remains_immutable", "status": "pass" if _snapshot() == source_before else "fail"})
    passed = sum(item.get("status") == "pass" for item in checks)
    report = {
        "suite": "v1079.9.1-desktop-alpha-daily-use-soak-repair",
        "ok": passed == len(checks),
        "status": "pass" if passed == len(checks) else "fail",
        "passed": passed,
        "total": len(checks),
        "checks": checks,
        "evidence_classification": "deterministic fixture",
        "native_provider_evidence": False,
        "operator_promotion_performed": False,
    }
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else f"{report['suite']}: {passed}/{len(checks)} passed")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
