from __future__ import annotations

"""Focused deterministic regressions for the v1489 Trial 3 repair.

All fixture text is synthetic. Runtime data is redirected outside the source tree
before Eidolon modules are imported. Public assertions inspect only content-free
projections.
"""

import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "conscious_agent"))

_RUNTIME_DIR = tempfile.TemporaryDirectory(prefix="eidolon-v1489-trial3-", ignore_cleanup_errors=True)
os.environ["EIDOLON_DATA_DIR"] = _RUNTIME_DIR.name
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

from immediate_conversation_grounding import build_immediate_conversation_grounding
from historical_memory_truth import build_historical_memory_truth
from conversation_context import build_conversation_prompt
from conversation_sessions import append_conversation_turn, create_conversation_session, load_conversation_session
from memory import store_memory
import conversation_runtime
import dashboard_chat_console as dashboard


RESULTS: list[tuple[str, bool, str]] = []


def require(name: str, condition: bool, detail: object = "") -> None:
    RESULTS.append((name, bool(condition), str(detail)[:700]))
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


def _compound_message() -> str:
    return (
        "Correction: the route was North Gate, not South Gate. "
        "The device was Helios, not Atlas. "
        "Tell me exactly what I just corrected. "
        "Then explain what you should have said when no supporting memory existed."
    )


def test_state_machine_current_correction_plus_recall() -> None:
    message = (
        "Correction: the route was North Gate, not South Gate. "
        "The device was Helios, not Atlas. Tell me exactly what I just corrected."
    )
    profile = build_immediate_conversation_grounding(
        message,
        [{"user_message": "What difficulties do you remember?", "assistant_response": "I am not sure."}],
        [],
    )
    require("state-current-correction-recall", profile.grounding_state == "current_correction_plus_recall", profile.public_summary())
    require("current-correction-selected-before-previous", profile.current_message_correction and not profile.protected_recent_user_turn, profile.public_summary())
    require("current-correction-named-route", "North Gate" in profile.evidence_text and "South Gate" in profile.evidence_text, profile.evidence_text)
    require("current-correction-named-device", "Helios" in profile.evidence_text and "Atlas" in profile.evidence_text, profile.evidence_text)
    require("current-correction-negations-preserved", profile.evidence_text.count("not") == 2, profile.evidence_text)
    require("current-correction-recall-clause-excluded", "Tell me exactly" not in profile.evidence_text, profile.evidence_text)
    require("current-correction-previous-question-excluded", "What difficulties" not in profile.evidence_text, profile.evidence_text)
    require("current-correction-provider-free-answer", profile.deterministic_response() == profile.evidence_text, profile.deterministic_response())


def test_state_machine_current_correction_plus_recall_plus_explanation() -> None:
    profile = build_immediate_conversation_grounding(
        _compound_message(),
        [{"user_message": "What difficulties do you remember?", "assistant_response": "I am not sure."}],
        [],
    )
    response = profile.deterministic_response()
    require("state-current-correction-compound", profile.grounding_state == "current_correction_plus_recall_plus_explanation", profile.public_summary())
    require("compound-second-clause-detected", profile.compound_explanation_requested, profile.public_summary())
    require("compound-correction-once", response.count("North Gate") == 1 and response.count("Helios") == 1, response)
    require("compound-explanation-present-once", response.count("no supporting memory exists") == 1, response)
    require("compound-uncertainty-rule", "don't have an attributable record" in response and "not invent" in response, response)
    require("compound-does-not-echo-prior-question", "What difficulties do you remember" not in response, response)


def test_state_machine_previous_turn_recall() -> None:
    prior = "Correction: the synthetic badge was amber, not violet."
    profile = build_immediate_conversation_grounding(
        "Tell me exactly what I just corrected.",
        [{"user_message": prior, "assistant_response": "Understood."}],
        [],
    )
    require("state-previous-turn-recall", profile.grounding_state == "previous_turn_recall", profile.public_summary())
    require("previous-turn-still-exact", profile.deterministic_response() == prior, profile.deterministic_response())
    require("previous-turn-source-offset", profile.source_turn_offset == 0, profile.public_summary())


def test_prompt_current_message_precedence_and_public_privacy() -> None:
    p = packet(
        _compound_message(),
        [{"user_message": "What difficulties do you remember?", "assistant_response": "I am not sure."}],
    )
    require("prompt-current-correction-heading", "CURRENT USER CORRECTION EVIDENCE" in p.prompt)
    require("prompt-current-correction-before-latest", p.prompt.index("CURRENT USER CORRECTION EVIDENCE") < p.prompt.index("LATEST USER MESSAGE"))
    require("prompt-current-grounding-state", p.metrics.immediate_grounding_state == "current_correction_plus_recall_plus_explanation", p.metrics.to_dict())
    require("prompt-current-correction-protected", p.metrics.current_message_correction_protected, p.metrics.to_dict())
    require("prompt-compound-explanation-recorded", p.metrics.compound_grounding_explanation_requested, p.metrics.to_dict())
    require("prompt-casual-budget-still-bounded", p.metrics.fast_path_bound_passed and p.metrics.estimated_prompt_tokens <= 900, p.metrics.estimated_prompt_tokens)
    public = str(p.metrics.to_dict())
    for private_term in ("North Gate", "South Gate", "Helios", "Atlas"):
        require(f"public-metrics-hide-{private_term.lower().replace(' ', '-')}", private_term not in public, public)


def test_runtime_compound_streaming_nonstreaming_zero_provider() -> None:
    class ProviderMustNotRun:
        calls = 0
        def __init__(self, *args, **kwargs):
            type(self).calls += 1
            raise AssertionError("provider must be bypassed for fully attributable current-message grounding")

    original = conversation_runtime.LocalModelClient
    conversation_runtime.LocalModelClient = ProviderMustNotRun
    try:
        previous_question = "What difficulties do you remember from our synthetic history?"
        session = create_conversation_session(title="Trial 3 compound nonstream", select_session=False)
        append_conversation_turn(
            session["id"], turn_id="trial3_prev_nonstream", user_message=previous_question,
            assistant_response="I do not have enough evidence.", completion_state="completed", success=True,
            source="v1489_trial3_fixture", select_session=False,
        )
        nonstream = conversation_runtime.run_conversation_turn(
            _compound_message(), use_ai=True, session_id=session["id"], select_session_on_record=False,
        )
        require("compound-nonstream-success", nonstream.success, nonstream.to_dict())
        require("compound-nonstream-provider-zero", nonstream.provider_request_count == 0, nonstream.provider_request_count)
        require("compound-nonstream-grounded-state", nonstream.completion_state == "grounded_immediate_context", nonstream.completion_state)
        require("compound-nonstream-current-facts", "North Gate" in nonstream.response and "Helios" in nonstream.response, nonstream.response)
        require("compound-nonstream-prior-question-not-echoed", previous_question not in nonstream.response, nonstream.response)
        require("compound-nonstream-explanation", "not invent" in nonstream.response and "attributable record" in nonstream.response, nonstream.response)
        require("compound-nonstream-each-clause-once", nonstream.response.count("North Gate") == 1 and nonstream.response.count("no supporting memory exists") == 1, nonstream.response)
        persisted = load_conversation_session(session["id"], include_turns=True) or {}
        matching = [row for row in persisted.get("turns", []) if row.get("id") == nonstream.operation_id]
        require("compound-nonstream-one-committed-turn", len(matching) == 1, len(matching))

        stream_session = create_conversation_session(title="Trial 3 compound stream", select_session=False)
        append_conversation_turn(
            stream_session["id"], turn_id="trial3_prev_stream", user_message=previous_question,
            assistant_response="I do not have enough evidence.", completion_state="completed", success=True,
            source="v1489_trial3_fixture", select_session=False,
        )
        events = list(conversation_runtime.stream_conversation_turn(
            _compound_message(), use_ai=True, session_id=stream_session["id"], select_session_on_record=False,
            operation_id="conversation_20260812T190000_trial3compound01",
        ))
        done = next(item["result"] for item in events if item.get("event") == "done")
        require("compound-stream-provider-zero", done.get("provider_request_count") == 0, done)
        require("compound-stream-parity", done.get("response") == nonstream.response, (done.get("response"), nonstream.response))
        require("compound-stream-no-provider-event", not any(item.get("event") == "provider_request" for item in events), events)
        require("compound-stream-one-visible-replacement", sum(1 for item in events if item.get("event") == "replace") == 1, events)
        stream_persisted = load_conversation_session(stream_session["id"], include_turns=True) or {}
        stream_matching = [row for row in stream_persisted.get("turns", []) if row.get("id") == done.get("operation_id")]
        require("compound-stream-one-committed-turn", len(stream_matching) == 1, len(stream_matching))
        require("compound-provider-never-instantiated", ProviderMustNotRun.calls == 0, ProviderMustNotRun.calls)
    finally:
        conversation_runtime.LocalModelClient = original


def test_historical_state_machine_and_provenance() -> None:
    query = "What difficulties have we had with reminder planning and prioritization, and what evidence supports that?"
    unsupported = build_historical_memory_truth(query, [])
    require("state-unsupported-history", unsupported.state == "unsupported_historical_memory", unsupported.public_summary())
    require("unsupported-history-uncertain", unsupported.uncertainty_required and not unsupported.attributable_evidence_available, unsupported.public_summary())
    broad_wording = build_historical_memory_truth(
        "What difficulties had occurred around synthetic scheduling, and what evidence supported that?", []
    )
    require("historical-broad-past-wording-detected", broad_wording.query_detected and broad_wording.state == "unsupported_historical_memory", broad_wording.public_summary())

    assistant = build_historical_memory_truth(query, [{
        "id": "assistant-capability-1", "type": "fact", "source": "synthetic_assistant",
        "content": "I can help with reminder planning and prioritization whenever you want.",
        "provenance": {"origin": "generated_turn"},
    }])
    require("state-assistant-authored-non-evidence", assistant.state == "assistant_authored_non_evidence", assistant.public_summary())
    require("assistant-capability-not-user-history", not assistant.attributable_evidence_available and assistant.assistant_authored_candidate_count == 1, assistant.public_summary())

    weak = build_historical_memory_truth(query, [{
        "id": "user-weak-1", "type": "user_fact", "source": "operator_fixture", "operator_explicit": True,
        "content": "We talked about planning meals once.", "provenance": {"origin": "operator_explicit"},
    }])
    require("weak-overlap-not-history", weak.state == "unsupported_historical_memory" and weak.weak_match_rejected_count == 1, weak.public_summary())

    nonassertive = build_historical_memory_truth(query, [{
        "id": "user-question-1", "type": "conversation_user", "source": "conversation_session",
        "content": "What difficulties have we had with reminder planning and prioritization?",
        "conversation_session_id": "fixture-session",
    }])
    require("user-question-not-event-evidence", nonassertive.state == "unsupported_historical_memory" and nonassertive.user_nonassertive_candidate_count == 1, nonassertive.public_summary())

    supported_query = "What difficulties have we had with the garden renovation schedule, and what evidence supports that?"
    supported = build_historical_memory_truth(supported_query, [{
        "id": "user-supported-1", "type": "user_fact", "source": "operator_fixture", "operator_explicit": True,
        "content": "We had trouble with the garden renovation schedule and missed the tile delivery window.",
        "provenance": {"origin": "operator_explicit"},
    }])
    require("state-supported-user-history", supported.state == "supported_user_authored_memory", supported.public_summary())
    require("supported-user-history-attributable", supported.attributable_evidence_available and supported.user_authored_evidence_count == 1, supported.public_summary())
    require("supported-user-history-human-attribution", "Evidence: user-authored attributable record." in supported.deterministic_response(), supported.deterministic_response())

    conflict = build_historical_memory_truth("What did we decide about the cedar workshop schedule, and what evidence supports that?", [
        {"id": "conflict-1", "type": "user_fact", "source": "operator_fixture", "operator_explicit": True,
         "fact_key": "cedar_schedule", "content": "The cedar workshop schedule was moved to Friday morning.", "provenance": {"origin": "operator_explicit"}},
        {"id": "conflict-2", "type": "user_fact", "source": "operator_fixture", "operator_explicit": True,
         "fact_key": "cedar_schedule", "content": "The cedar workshop schedule stayed on Monday afternoon.", "provenance": {"origin": "operator_explicit"}},
    ])
    require("state-conflicting-memory", conflict.state == "conflicting_memory_evidence" and conflict.conflicting_evidence_count >= 1, conflict.public_summary())
    require("conflicting-memory-fails-closed", conflict.uncertainty_required and not conflict.attributable_evidence_available, conflict.public_summary())

    malformed = build_historical_memory_truth("What did we decide about the cobalt archive label, and what evidence supports that?", [{
        "type": "user_fact", "content": "The cobalt archive label was changed to Delta Seven."
    }])
    require("state-malformed-memory", malformed.state == "malformed_or_unattributed_memory", malformed.public_summary())
    require("malformed-memory-fails-closed", malformed.uncertainty_required and malformed.malformed_or_unattributed_count == 1, malformed.public_summary())

    for profile, label in ((unsupported, "unsupported"), (assistant, "assistant"), (weak, "weak"), (nonassertive, "nonassertive"), (supported, "supported"), (conflict, "conflict"), (malformed, "malformed")):
        public = str(profile.public_summary())
        for private_term in ("reminder", "garden", "cedar", "cobalt", "Delta Seven"):
            require(f"{label}-public-diagnostics-redacted-{private_term.lower().replace(' ', '-')}", private_term not in public, public)


def test_runtime_historical_truth_without_provider_narrative() -> None:
    class ProviderMustNotRun:
        calls = 0
        def __init__(self, *args, **kwargs):
            type(self).calls += 1
            raise AssertionError("historical truth boundary should answer attributable/unsupported cases without provider narrative")

    store_memory({
        "id": "trial3_assistant_capability", "type": "fact", "source": "synthetic_assistant",
        "content": "I can help with reminder planning and prioritization whenever you want.",
        "provenance": {"origin": "generated_turn"}, "use_in_conversation": True,
    }, vectorize=False)
    store_memory({
        "id": "trial3_user_supported", "type": "user_fact", "source": "operator_fixture", "operator_explicit": True,
        "content": "We had trouble with the garden renovation schedule and missed the tile delivery window.",
        "provenance": {"origin": "operator_explicit"}, "use_in_conversation": True,
    }, vectorize=False)
    store_memory({
        "id": "trial3_conflict_a", "type": "user_fact", "source": "operator_fixture", "operator_explicit": True,
        "fact_key": "obsidian_schedule", "content": "The obsidian workshop schedule moved to Thursday morning.",
        "provenance": {"origin": "operator_explicit"}, "use_in_conversation": True,
    }, vectorize=False)
    store_memory({
        "id": "trial3_conflict_b", "type": "user_fact", "source": "operator_fixture", "operator_explicit": True,
        "fact_key": "obsidian_schedule", "content": "The obsidian workshop schedule stayed on Tuesday evening.",
        "provenance": {"origin": "operator_explicit"}, "use_in_conversation": True,
    }, vectorize=False)

    original = conversation_runtime.LocalModelClient
    conversation_runtime.LocalModelClient = ProviderMustNotRun
    try:
        unsupported_session = create_conversation_session(title="Trial 3 unsupported history", select_session=False)
        unsupported = conversation_runtime.run_conversation_turn(
            "What difficulties have we had with time management and overlapping shifts, and what evidence supports that?",
            use_ai=True, session_id=unsupported_session["id"], select_session_on_record=False,
        )
        require("runtime-unsupported-history-provider-zero", unsupported.provider_request_count == 0, unsupported.provider_request_count)
        require("runtime-unsupported-history-uncertainty", "don't have an attributable memory record" in unsupported.response, unsupported.response)
        require("runtime-unsupported-history-no-narrative", "time management" not in unsupported.response.lower() and "overlapping shifts" not in unsupported.response.lower(), unsupported.response)

        assistant_session = create_conversation_session(title="Trial 3 assistant non evidence", select_session=False)
        assistant = conversation_runtime.run_conversation_turn(
            "What difficulties have we had with reminder planning and prioritization, and what evidence supports that?",
            use_ai=True, session_id=assistant_session["id"], select_session_on_record=False,
        )
        require("runtime-assistant-history-provider-zero", assistant.provider_request_count == 0, assistant.provider_request_count)
        require("runtime-assistant-history-rejected-as-user-evidence", "assistant-authored material" in assistant.response, assistant.response)
        require("runtime-assistant-history-no-event-invention", "we struggled" not in assistant.response.lower() and "we had trouble" not in assistant.response.lower(), assistant.response)

        supported_session = create_conversation_session(title="Trial 3 supported history", select_session=False)
        supported = conversation_runtime.run_conversation_turn(
            "What difficulties have we had with the garden renovation schedule, and what evidence supports that?",
            use_ai=True, session_id=supported_session["id"], select_session_on_record=False,
        )
        require("runtime-supported-history-provider-zero", supported.provider_request_count == 0, supported.provider_request_count)
        require("runtime-supported-history-bounded", "missed the tile delivery window" in supported.response, supported.response)
        require("runtime-supported-history-attributed", "user-authored attributable record" in supported.response, supported.response)

        conflict_session = create_conversation_session(title="Trial 3 conflict history", select_session=False)
        conflict = conversation_runtime.run_conversation_turn(
            "What did we decide about the obsidian workshop schedule, and what evidence supports that?",
            use_ai=True, session_id=conflict_session["id"], select_session_on_record=False,
        )
        require("runtime-conflict-history-provider-zero", conflict.provider_request_count == 0, conflict.provider_request_count)
        require("runtime-conflict-history-fails-closed", "conflicting attributable records" in conflict.response, conflict.response)
        require("runtime-conflict-public-state", conflict.context.get("historical_memory_evidence_state") == "conflicting_memory_evidence", conflict.context)
        require("runtime-conflict-public-count", int(conflict.context.get("historical_conflict_count") or 0) >= 1, conflict.context)

        require("runtime-history-provider-never-instantiated", ProviderMustNotRun.calls == 0, ProviderMustNotRun.calls)
        public = str(supported.cognitive_context.get("immediate_conversation_grounding") or {})
        require("runtime-public-grounding-no-memory-text", "tile delivery" not in public and "garden renovation" not in public, public)
    finally:
        conversation_runtime.LocalModelClient = original


def test_dashboard_compound_reconnect_exactly_once() -> None:
    session = create_conversation_session(title="Trial 3 dashboard compound", select_session=False)
    append_conversation_turn(
        session["id"], turn_id="trial3_dashboard_prev", user_message="What did we discuss last time?",
        assistant_response="I am not sure.", completion_state="completed", success=True,
        source="v1489_trial3_fixture", select_session=False,
    )
    op = "conversation_20260812T190000_trial3dashreplay01"
    first = list(dashboard.stream_dashboard_chat_turn(_compound_message(), use_ai=True, session_id=session["id"], operation_id=op))
    second = list(dashboard.stream_dashboard_chat_turn(_compound_message(), use_ai=True, session_id=session["id"], operation_id=op))
    done1 = next(item["turn"] for item in first if item.get("event") == "done")
    done2 = next(item["turn"] for item in second if item.get("event") == "done")
    require("dashboard-compound-same-operation", done1.get("conversation_runtime", {}).get("operation_id") == done2.get("conversation_runtime", {}).get("operation_id") == op, (done1.get("conversation_runtime", {}).get("operation_id"), done2.get("conversation_runtime", {}).get("operation_id")))
    require("dashboard-compound-same-response", done1.get("eidolon_response") == done2.get("eidolon_response"), (done1.get("eidolon_response"), done2.get("eidolon_response")))
    require("dashboard-compound-provider-zero", done1.get("conversation_runtime", {}).get("provider_request_count") == 0, done1.get("conversation_runtime"))
    persisted = load_conversation_session(session["id"], include_turns=True) or {}
    matching = [row for row in persisted.get("turns", []) if row.get("id") == op]
    require("dashboard-compound-reconnect-one-turn", len(matching) == 1, len(matching))


def test_existing_command_receipt_boundary_unchanged() -> None:
    command = "Before we continue, run a read-only system maintenance check and summarize anything that needs my attention."
    original_stream = dashboard.stream_conversation_turn
    dashboard.stream_conversation_turn = lambda *a, **k: (_ for _ in ()).throw(AssertionError("provider must not run for governed maintenance action"))
    try:
        events = list(dashboard.stream_dashboard_chat_turn(
            command, use_ai=True, operation_id="conversation_20260812T190000_trial3maintenance01",
        ))
        turn = next(item["turn"] for item in events if item.get("event") == "done")
        receipt = turn.get("execution_receipt") or {}
        require("trial3-maintenance-provider-zero", turn.get("conversation_runtime", {}).get("provider_request_count") == 0, turn.get("conversation_runtime"))
        require("trial3-maintenance-authoritative-receipt", receipt.get("authoritative") is True, receipt)
        require("trial3-maintenance-success-receipt-bound", receipt.get("succeeded") is True and "receipt confirms successful completion" in str(turn.get("eidolon_response") or ""), turn)
    finally:
        dashboard.stream_conversation_turn = original_stream


def main() -> None:
    tests = [
        test_state_machine_current_correction_plus_recall,
        test_state_machine_current_correction_plus_recall_plus_explanation,
        test_state_machine_previous_turn_recall,
        test_prompt_current_message_precedence_and_public_privacy,
        test_runtime_compound_streaming_nonstreaming_zero_provider,
        test_historical_state_machine_and_provenance,
        test_runtime_historical_truth_without_provider_narrative,
        test_dashboard_compound_reconnect_exactly_once,
        test_existing_command_receipt_boundary_unchanged,
    ]
    try:
        for test in tests:
            test()
    finally:
        _RUNTIME_DIR.cleanup()
    print(f"v1489 Trial 3 compound grounding/memory-truth repair: {len(RESULTS)}/{len(RESULTS)} checks passed")
    for name, ok, _detail in RESULTS:
        print(f"  {'PASS' if ok else 'FAIL'} {name}")


if __name__ == "__main__":
    main()
