from __future__ import annotations

"""Focused deterministic regressions for the v1489 Trial 2 repair.

Fixtures are synthetic.  Runtime data is redirected outside the source tree before
Eidolon modules are imported.
"""

import os
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "conscious_agent"))

_RUNTIME_DIR = tempfile.TemporaryDirectory(prefix="eidolon-v1489-trial2-", ignore_cleanup_errors=True)
os.environ["EIDOLON_DATA_DIR"] = _RUNTIME_DIR.name
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

from conversation_context import build_conversation_prompt
from conversation_quality import classify_conversation_quality
from natural_language_action_routing import classify_natural_language_intent
from chat_action_router import load_chat_action, propose_chat_action
from execution_claim_guard import (
    build_execution_truth_receipt,
    public_execution_receipt,
    receipt_allows_success_claim,
    render_receipt_bound_action_response,
    validate_execution_truth_receipt,
)
import dashboard_chat_console as dashboard
import conversation_runtime
from conversation_sessions import append_conversation_turn, create_conversation_session


RESULTS: list[tuple[str, bool, str]] = []


def require(name: str, condition: bool, detail: object = "") -> None:
    RESULTS.append((name, bool(condition), str(detail)[:500]))
    if not condition:
        raise AssertionError(f"{name}: {detail}")


def packet(message: str, history=(), memories=()):
    return build_conversation_prompt(
        user_message=message,
        self_model={"name": "Eidolon"},
        desires={},
        memories=list(memories),
        project_context="",
        goal_context="",
        task_context="",
        conversation_history=list(history),
        context_size=8192,
        max_tokens=512,
    )


def test_immediate_correction_grounding() -> None:
    correction = (
        "Correction: the clinician diagnosed contact dermatitis, and I said Allegra might have contributed. "
        "Please don't pretend to remember details when you're uncertain."
    )
    p = packet(
        "What did I just correct you about? Repeat my correction exactly.",
        [{"user_message": correction, "assistant_response": "Understood."}],
    )
    require("correction-contact-dermatitis-preserved", "contact dermatitis" in p.prompt)
    require("correction-allegra-preserved", "Allegra" in p.prompt)
    require("correction-user-evidence-labeled", "IMMEDIATE USER FACT EVIDENCE" in p.prompt)
    require("correction-system-user-boundary", "not to system, identity, personality, policy" in p.prompt)
    require("correction-exact-repeat-guidance", "preserve the evidence wording" in p.prompt)
    require("correction-fast-budget", p.metrics.estimated_prompt_tokens <= 900, p.metrics.estimated_prompt_tokens)
    require("correction-content-free-metrics", p.metrics.prompt_metrics_content_free)


def test_missing_historical_memory_uncertainty() -> None:
    p = packet("Do you remember what I told you last winter about the old brass lamp?")
    require("missing-memory-grounding-present", p.metrics.historical_memory_query)
    require("missing-memory-no-attributable-record", not p.metrics.attributable_historical_memory_available)
    require("missing-memory-uncertainty-guidance", "No attributable historical memory evidence is available" in p.prompt)
    require("missing-memory-no-invention-guidance", "instead of constructing a plausible memory" in p.prompt)

    unrelated = [{
        "id": "synthetic_unrelated_memory",
        "type": "conversation_user",
        "source": "synthetic_fixture",
        "content": "Synthetic correction labels included contact dermatitis and Allegra.",
    }]
    collision = packet("Do you remember the synthetic cobalt lighthouse detail from long ago?", memories=unrelated)
    require("generic-overlap-is-not-attributable", not collision.metrics.attributable_historical_memory_available)
    focused = packet("Do you remember Allegra?", memories=unrelated)
    require("focused-distinctive-term-remains-attributable", focused.metrics.attributable_historical_memory_available)


def test_runtime_grounding_streaming_nonstreaming_and_missing_memory() -> None:
    class ProviderMustNotRun:
        calls = 0
        def __init__(self, *args, **kwargs):
            type(self).calls += 1
            raise AssertionError("provider must be bypassed for fully attributable immediate grounding")

    original = conversation_runtime.LocalModelClient
    conversation_runtime.LocalModelClient = ProviderMustNotRun
    session = create_conversation_session(title="Trial 2 grounding fixture", select_session=False)
    correction = (
        "Correction: the clinician diagnosed contact dermatitis, and I said Allegra might have contributed. "
        "Please don't pretend to remember details when you're uncertain."
    )
    append_conversation_turn(
        session["id"], turn_id="fixture_correction_001", user_message=correction,
        assistant_response="Understood.", completion_state="completed", success=True,
        source="v1489_trial2_fixture", select_session=False,
    )
    try:
        nonstream = conversation_runtime.run_conversation_turn(
            "What did I just correct you about? Repeat my correction exactly.",
            use_ai=True, session_id=session["id"], select_session_on_record=False,
        )
        require("runtime-grounded-nonstream-success", nonstream.success, nonstream.to_dict())
        require("runtime-grounded-nonstream-exact", nonstream.response == correction, nonstream.response)
        require("runtime-grounded-nonstream-no-provider", nonstream.provider_request_count == 0, nonstream.provider_request_count)

        exact_phrase_session = create_conversation_session(title="Trial 2 exact wording fixture", select_session=False)
        append_conversation_turn(
            exact_phrase_session["id"], turn_id="fixture_correction_exact_001", user_message=correction,
            assistant_response="Understood.", completion_state="completed", success=True,
            source="v1489_trial2_fixture", select_session=False,
        )
        exact_phrase = conversation_runtime.run_conversation_turn(
            "Tell me exactly what I just corrected.",
            use_ai=True, session_id=exact_phrase_session["id"], select_session_on_record=False,
        )
        require("runtime-real-trial-wording-exact", exact_phrase.response == correction, exact_phrase.response)
        require("runtime-real-trial-wording-no-provider", exact_phrase.provider_request_count == 0, exact_phrase.provider_request_count)

        # Create a fresh session so the streaming path sees the same immediately prior correction.
        stream_session = create_conversation_session(title="Trial 2 stream grounding fixture", select_session=False)
        append_conversation_turn(
            stream_session["id"], turn_id="fixture_correction_002", user_message=correction,
            assistant_response="Understood.", completion_state="completed", success=True,
            source="v1489_trial2_fixture", select_session=False,
        )
        events = list(conversation_runtime.stream_conversation_turn(
            "What did I just correct you about? Repeat my correction exactly.",
            use_ai=True, session_id=stream_session["id"], select_session_on_record=False,
            operation_id="conversation_20260812T000000_trial2ground01",
        ))
        done = next(item["result"] for item in events if item.get("event") == "done")
        require("runtime-grounded-stream-exact", done.get("response") == correction, done)
        require("runtime-grounded-stream-no-provider", done.get("provider_request_count") == 0, done.get("provider_request_count"))
        require("runtime-grounded-stream-no-provider-event", not any(item.get("event") == "provider_request" for item in events), events)

        missing_session = create_conversation_session(title="Trial 2 missing memory fixture", select_session=False)
        missing = conversation_runtime.run_conversation_turn(
            "Do you remember what I told you last winter about the old brass lamp?",
            use_ai=True, session_id=missing_session["id"], select_session_on_record=False,
        )
        require("runtime-missing-memory-uncertain", "don't have an attributable memory record" in missing.response, missing.response)
        require("runtime-missing-memory-no-provider", missing.provider_request_count == 0, missing.provider_request_count)
        require("runtime-grounding-provider-never-instantiated", ProviderMustNotRun.calls == 0, ProviderMustNotRun.calls)
    finally:
        conversation_runtime.LocalModelClient = original


def test_command_classification_and_hypothetical_boundary() -> None:
    command = "Before we continue, run a read-only system maintenance check and summarize anything that needs my attention."
    quality = classify_conversation_quality(command, [])
    intent = classify_natural_language_intent(command)
    action = propose_chat_action(command, save=False)
    require("maintenance-explicit-operator", quality.explicit_operator_request and quality.should_analyze_action, quality)
    require("maintenance-action-before-casual", intent.get("category") == "action_request", intent)
    require("maintenance-routes-governed", action.get("intent") == "maintenance_scan" and action.get("execution_mode") == "direct_command", action)

    hypothetical = "It would be nice if you could check my computer someday."
    h_quality = classify_conversation_quality(hypothetical, [])
    h_intent = classify_natural_language_intent(hypothetical)
    require("hypothetical-not-operator", not h_quality.should_analyze_action, h_quality)
    require("hypothetical-not-execution", not h_intent.get("action_intent_present"), h_intent)


def _synthetic_action(status: str, *, result_ok: bool = False, suffix: str = "x") -> dict:
    action = {
        "id": f"chat_action_fixture_{suffix}",
        "intent": "run_diagnostics",
        "execution_mode": "direct_command",
        "risk_level": "low",
        "status": status,
        "execution_attempt": 1 if status not in {"proposed", "blocked"} else 0,
        "active_attempt_id": "",
        "result_summary_status": status if status not in {"proposed", "blocked"} else "",
        "events": [{"event": "fixture"}] if status not in {"proposed"} else [],
    }
    if status not in {"proposed", "blocked"}:
        action["result"] = {"ok": bool(result_ok)}
    return action


def test_receipt_bound_execution_truth() -> None:
    success = _synthetic_action("executed", result_ok=True, suffix="success")
    receipt = build_execution_truth_receipt(success)
    valid, reason = validate_execution_truth_receipt(receipt, success)
    response = render_receipt_bound_action_response(success, receipt, verified_output="Overall status: PASS")
    require("valid-receipt-validates", valid, reason)
    require("success-requires-valid-receipt", receipt_allows_success_claim(receipt, success), receipt)
    require("success-response-bound-to-action-id", success["id"] in response, response)
    require("success-response-says-verified", "receipt confirms successful completion" in response, response)

    missing_response = render_receipt_bound_action_response(success, {})
    require("missing-receipt-no-success", "cannot claim it ran" in missing_response.lower(), missing_response)

    for index, status in enumerate(("blocked", "failed", "cancelled", "timed_out", "proposed")):
        row = _synthetic_action(status, result_ok=False, suffix=str(index))
        row_receipt = build_execution_truth_receipt(row)
        row_response = render_receipt_bound_action_response(row, row_receipt)
        require(f"{status}-receipt-no-success", not receipt_allows_success_claim(row_receipt, row), row_response)
        require(f"{status}-response-no-success-language", "successfully" not in row_response.lower(), row_response)

    tampered = dict(receipt)
    tampered["status"] = "failed"
    valid, reason = validate_execution_truth_receipt(tampered, success)
    require("tampered-receipt-rejected", not valid and "digest" in reason, reason)
    tampered_response = render_receipt_bound_action_response(success, tampered)
    require("tampered-receipt-no-success", "cannot claim it ran" in tampered_response.lower(), tampered_response)

    public = public_execution_receipt(receipt)
    forbidden = {"output", "stdout", "stderr", "prompt", "conversation", "memory", "payload", "path", "secret", "credential", "command"}
    require("receipt-public-content-free", not any(key in forbidden for key in public), public)
    require("receipt-no-raw-output", public.get("raw_output_included") is False, public)


def _collect_stream(message: str, operation_id: str):
    return list(dashboard.stream_dashboard_chat_turn(
        message,
        use_ai=True,
        session_id="",
        operation_id=operation_id,
    ))


def test_dashboard_streaming_nonstreaming_and_exactly_once() -> None:
    command = "Before we continue, run a read-only system maintenance check and summarize anything that needs my attention."

    original_stream = dashboard.stream_conversation_turn
    original_run = dashboard.run_conversation_turn
    dashboard.stream_conversation_turn = lambda *a, **k: (_ for _ in ()).throw(AssertionError("provider stream must not run for governed action"))
    dashboard.run_conversation_turn = lambda *a, **k: (_ for _ in ()).throw(AssertionError("provider generation must not run for governed action"))
    try:
        op = "conversation_20260812T000000_trial2route001"
        first = _collect_stream(command, op)
        second = _collect_stream(command, op)
        done1 = next(item["turn"] for item in first if item.get("event") == "done")
        done2 = next(item["turn"] for item in second if item.get("event") == "done")
        require("stream-provider-request-zero", done1["conversation_runtime"].get("provider_request_count") == 0, done1["conversation_runtime"])
        require("stream-real-receipt", bool(done1.get("execution_receipt", {}).get("authoritative")), done1.get("execution_receipt"))
        require("stream-success-only-with-receipt", done1.get("execution_receipt", {}).get("succeeded") is True, done1.get("execution_receipt"))
        require("stream-no-provider-event", not any(item.get("event") == "provider_request" for item in first), first)
        require("stream-visible-receipt-summary", any(item.get("event") == "delta" and "receipt confirms successful completion" in str(item.get("text") or "") for item in first), first)
        require("reconnect-same-action-id", done1.get("action_id") == done2.get("action_id"), (done1.get("action_id"), done2.get("action_id")))
        persisted = load_chat_action(str(done1.get("action_id") or "")) or {}
        require("reconnect-one-execution-attempt", int(persisted.get("execution_attempt") or 0) == 1, persisted.get("execution_attempt"))
        second_execution = done2.get("action_execution") or {}
        require("reconnect-replays-receipt", bool(second_execution.get("replayed")), second_execution)

        nonstream = dashboard.create_dashboard_chat_turn(command, use_ai=True)
        require("nonstream-provider-request-zero", nonstream["conversation_runtime"].get("provider_request_count") == 0, nonstream["conversation_runtime"])
        require("nonstream-real-receipt", bool(nonstream.get("execution_receipt", {}).get("authoritative")), nonstream.get("execution_receipt"))
        require("stream-nonstream-truth-parity", "receipt confirms successful completion" in nonstream.get("eidolon_response", ""), nonstream.get("eidolon_response"))
        require("successful-action-turn-metadata", nonstream.get("completion_state") == "completed" and nonstream.get("conversation_runtime", {}).get("success") is True, nonstream)
    finally:
        dashboard.stream_conversation_turn = original_stream
        dashboard.run_conversation_turn = original_run


def test_blocked_action_metadata_remains_blocked() -> None:
    original = dashboard._propose_explicit_chat_action
    dashboard._propose_explicit_chat_action = lambda *args, **kwargs: {
        "id": "", "status": "blocked", "intent": "unsupported_command",
        "execution_mode": "blocked", "risk_level": "unknown", "summary": "synthetic",
    }
    try:
        session = create_conversation_session(title="Blocked metadata fixture", select_session=False)
        nonstream = dashboard.create_dashboard_chat_turn(
            "Run an unsupported synthetic check", use_ai=True, session_id=session["id"],
        )
        require("blocked-nonstream-not-success", nonstream.get("conversation_runtime", {}).get("success") is False, nonstream)
        require("blocked-nonstream-state", nonstream.get("completion_state") == "blocked", nonstream)
        events = list(dashboard.stream_dashboard_chat_turn(
            "Run an unsupported synthetic check", use_ai=True, session_id=session["id"],
            operation_id="conversation_20260812T000000_trial2blocked1",
        ))
        complete = next(item["result"] for item in events if item.get("event") == "conversation_complete")
        turn = next(item["turn"] for item in events if item.get("event") == "done")
        require("blocked-stream-not-success", complete.get("success") is False, complete)
        require("blocked-stream-state", turn.get("completion_state") == "blocked", turn)
        require("blocked-stream-no-provider", turn.get("conversation_runtime", {}).get("provider_request_count") == 0, turn)
    finally:
        dashboard._propose_explicit_chat_action = original


def test_source_does_not_log_private_receipt_material() -> None:
    source = Path("conscious_agent/execution_claim_guard.py").read_text(encoding="utf-8")
    require("guard-declares-content-free", '"content_free": True' in source)
    require("guard-declares-no-raw-output", '"raw_output_included": False' in source)
    require("guard-has-digest-validation", "receipt_digest_invalid" in source and "action_state_tampered" in source)


def main() -> None:
    tests = [
        test_immediate_correction_grounding,
        test_missing_historical_memory_uncertainty,
        test_runtime_grounding_streaming_nonstreaming_and_missing_memory,
        test_command_classification_and_hypothetical_boundary,
        test_receipt_bound_execution_truth,
        test_dashboard_streaming_nonstreaming_and_exactly_once,
        test_blocked_action_metadata_remains_blocked,
        test_source_does_not_log_private_receipt_material,
    ]
    try:
        for test in tests:
            test()
    finally:
        _RUNTIME_DIR.cleanup()
    print(f"v1489 Trial 2 grounding/command-routing repair: {len(RESULTS)}/{len(RESULTS)} checks passed")
    for name, ok, _detail in RESULTS:
        print(f"  {'PASS' if ok else 'FAIL'} {name}")


if __name__ == "__main__":
    main()
