from __future__ import annotations

"""Focused deterministic fixtures for the unpromoted v1489 conversation repair.

Fixtures use synthetic conversation wording only. Provider behavior is simulated,
and runtime state is redirected outside the source tree before Eidolon imports.
"""

import argparse
import inspect
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v1489-conversation-repair-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True
sys.path.insert(0, str(AGENT))

import conversation_runtime
import desktop_shell
from conversation_context import build_conversation_prompt, estimate_tokens
from conversation_quality import classify_conversation_quality
from conversation_sessions import append_conversation_turn, conversation_session_turns, create_conversation_session
from natural_follow_up_policy import (
    NaturalFollowUpStreamGate,
    build_natural_follow_up_runtime_projection,
    enforce_natural_follow_up_output,
)
from response_time_runtime import build_compact_cognitive_projection


def require(value: object, detail: object = "") -> None:
    if not value:
        raise AssertionError(detail or "requirement failed")


def test_meaningful_first_conversation_guidance() -> None:
    quality = classify_conversation_quality("It matters to me that this is our first important conversation.", [])
    guide = quality.response_instruction()
    require(quality.meaningful_moment, quality.receipt_metrics())
    require(quality.meaningful_moment_kind == "first_or_important_conversation", quality.receipt_metrics())
    require("Acknowledge that significance directly" in guide, guide)
    require("do not force a question" in guide, guide)


def test_excitement_and_appreciation_are_specific() -> None:
    quality = classify_conversation_quality("I'm genuinely thrilled you're here, and I appreciate this exchange.", [])
    guide = quality.response_instruction()
    require(quality.meaningful_moment_kind == "appreciation_or_excitement", quality.receipt_metrics())
    require("specific excitement or appreciation" in guide, guide)
    require("generic offer to help" in guide, guide)


def test_relationship_reflection_after_difficulty() -> None:
    history = [{"user_message": "Yesterday was a rough day and I was overwhelmed.", "assistant_response": "That sounds draining."}]
    quality = classify_conversation_quality("Talking with you about it feels significant to me.", history)
    require(quality.meaningful_moment_kind == "relationship_reflection_after_difficulty", quality.receipt_metrics())
    require("without inventing memory, intimacy, or consciousness claims" in quality.response_instruction())


def test_multiturn_active_subject_is_preserved() -> None:
    history = [{
        "user_message": "I spent the evening restoring an old radio.",
        "assistant_response": "Getting the old mechanism moving again sounds satisfying.",
        "completion_state": "completed",
        "success": True,
    }]
    packet = build_conversation_prompt(
        user_message="The tuning knob finally turns smoothly now.",
        self_model={"name": "Eidolon"}, desires={}, memories=[],
        project_context="OPERATIONAL_CANARY_PROJECT", goal_context="OPERATIONAL_CANARY_GOAL", task_context="OPERATIONAL_CANARY_TASK",
        conversation_history=history, context_size=8192, max_tokens=256,
    )
    require("old radio" in packet.prompt.lower(), packet.prompt[-2500:])
    require(packet.metrics.conversation_topic_transition == "continuation", packet.metrics.to_dict())
    require("OPERATIONAL_CANARY" not in packet.prompt, "casual prompt acquired operator context")


def test_repetition_suppression_is_model_readable() -> None:
    canonical = {"selected_intent": "direct_answer", "intentional_silence_verified": False}
    discourse = {"discourse_relation": "continue", "address_explicit_correction": False}
    continuity = {
        "continuity_relation": "continue_thread",
        "continuity_confidence": "high",
        "consume_prior_question": True,
        "avoid_reasking_answered_question": False,
        "close_without_reopening": False,
    }
    history = [
        {"role": "assistant", "text": "I understand. Let me know if you need anything else."},
        {"role": "assistant", "text": "I understand. Let me know if you want to talk more."},
    ]
    projection = build_natural_follow_up_runtime_projection(
        "That part is better now.", canonical, discourse, continuity, conversation_history=history,
    )
    prompt = projection["prompt_section"]
    require(projection["diagnostics"]["optional_follow_up_suppressed"] is True, projection["diagnostics"])
    require("NATURAL FOLLOW-UP CONTRACT" in prompt, prompt)
    require("generic help/closing offer" in prompt, prompt)
    require("re-asked question" in prompt, prompt)
    require("QUESTION BOUNDARY: Ask no question" in prompt, prompt)


def test_casual_projection_omits_redundant_heavy_blocks() -> None:
    follow = {"prompt_section": "NATURAL FOLLOW-UP CONTRACT\nAnswer the current message.\nDo not end with a generic offer to help."}
    prompt, diagnostics = build_compact_cognitive_projection(
        "The little repair finally worked.",
        action_projection={}, development_campaign={}, cognitive={"prompt_section": "COGNITION_CANARY"},
        conversation_policy={"prompt_section": "CONVERSATION POLICY"},
        conversation_discourse={"prompt_section": "DISCOURSE POLICY"},
        memory_retrieval={"prompt_section": "MEMORY POLICY"}, natural_continuity={"prompt_section": "CONTINUITY POLICY"},
        natural_follow_up=follow, governed_speech={"prompt_section": "SPEECH_CANARY"}, daily_companion={"prompt_section": "COMPANION_CANARY"},
    )
    require(diagnostics["ordinary_casual_projection"] is True, diagnostics)
    require("NATURAL FOLLOW-UP CONTRACT" in prompt, prompt)
    require("COGNITION_CANARY" not in prompt and "SPEECH_CANARY" not in prompt and "COMPANION_CANARY" not in prompt, prompt)


def test_stream_and_nonstream_effective_prompts_share_contracts() -> None:
    class FakeClient:
        prompts: list[tuple[str, str]] = []

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.last_retry_count = 0
            self.last_metrics: dict[str, Any] = {}

        def generate(self, prompt: str) -> str:
            type(self).prompts.append(("nonstream", prompt))
            return "That is a meaningful milestone to name directly."

        def stream(self, prompt: str):
            type(self).prompts.append(("stream", prompt))
            yield "I can see why "
            yield "that feels significant."

        def cancel(self) -> None:
            return None

        def close(self) -> None:
            return None

        def __enter__(self):
            return self

        def __exit__(self, *_args: Any) -> None:
            self.close()

    original = conversation_runtime.LocalModelClient
    conversation_runtime.LocalModelClient = FakeClient
    try:
        first = create_conversation_session(title="synthetic first conversation", select_session=False)
        result = conversation_runtime.run_conversation_turn(
            "This feels like an important first conversation.", use_ai=True, session_id=first["id"], select_session_on_record=False,
        )
        require(result.success is True, result.to_dict())
        second = create_conversation_session(title="synthetic appreciation", select_session=False)
        events = list(conversation_runtime.stream_conversation_turn(
            "I'm excited about this exchange and I appreciate it.", use_ai=True, session_id=second["id"], select_session_on_record=False,
        ))
        require(any(event.get("event") == "done" for event in events), events[-5:])
    finally:
        conversation_runtime.LocalModelClient = original

    prompts = dict(FakeClient.prompts)
    require(set(prompts) == {"nonstream", "stream"}, list(prompts))
    for mode, prompt in prompts.items():
        require("CASUAL CONVERSATION CONTRACT" in prompt, mode)
        require("Do not offer generic help or ask a generic intake question" in prompt, mode)
        require("RUNTIME RESPONSE PROJECTION" not in prompt, mode)
        require(estimate_tokens(prompt) <= 900, (mode, estimate_tokens(prompt)))
    require("first or important conversation" in prompts["nonstream"], "first-conversation guidance did not reach provider prompt")
    require("specific excitement or appreciation" in prompts["stream"], "appreciation guidance did not reach stream provider prompt")


def test_casual_fast_path_prompt_budgets_and_sections() -> None:
    fresh = build_conversation_prompt(
        user_message="I found a neat old radio today.", self_model={"name": "Eidolon", "active_goals": ["PROJECT_CANARY"]},
        desires={"analysis": 1.0}, memories=[], project_context="PROJECT_CANARY", goal_context="GOAL_CANARY",
        task_context="TASK_CANARY", conversation_history=[], cognitive_context="COGNITIVE_CANARY ACTION_CANARY CAMPAIGN_CANARY RELEASE_CANARY",
        context_size=8192, max_tokens=128,
    )
    require(fresh.metrics.prompt_lane == "casual_fast", fresh.metrics.to_dict())
    require(fresh.metrics.estimated_prompt_tokens <= 600, fresh.metrics.to_dict())
    require(fresh.metrics.fast_path_bound_passed is True, fresh.metrics.to_dict())
    require(fresh.metrics.prompt_metrics_content_free is True, fresh.metrics.to_dict())
    for canary in ("PROJECT_CANARY", "GOAL_CANARY", "TASK_CANARY", "COGNITIVE_CANARY", "ACTION_CANARY", "CAMPAIGN_CANARY", "RELEASE_CANARY"):
        require(canary not in fresh.prompt, (canary, fresh.prompt))

    history = [{
        "user_message": "I spent the evening restoring an old radio.",
        "assistant_response": "Getting the old mechanism moving again sounds satisfying.",
        "completion_state": "completed", "success": True,
    }]
    continuity = build_conversation_prompt(
        user_message="The tuning knob finally turns smoothly now.", self_model={"name": "Eidolon"}, desires={}, memories=[],
        project_context="PROJECT_CANARY", goal_context="GOAL_CANARY", task_context="TASK_CANARY", conversation_history=history,
        cognitive_context="COGNITIVE_CANARY", context_size=8192, max_tokens=128,
    )
    require(continuity.metrics.estimated_prompt_tokens <= 900, continuity.metrics.to_dict())
    require("I spent the evening restoring an old radio." in continuity.prompt, continuity.prompt)
    require(continuity.prompt.rstrip().endswith("LATEST USER MESSAGE\nThe tuning knob finally turns smoothly now."), continuity.prompt)

    meaningful = build_conversation_prompt(
        user_message="This feels like an important first conversation, and I am excited about it.",
        self_model={"name": "Eidolon"}, desires={}, memories=[], project_context="PROJECT_CANARY", goal_context="GOAL_CANARY",
        task_context="TASK_CANARY", conversation_history=[], context_size=8192, max_tokens=128,
    )
    require(meaningful.metrics.estimated_prompt_tokens <= 900, meaningful.metrics.to_dict())
    require("Acknowledge that significance directly" in meaningful.prompt, meaningful.prompt)


def test_operator_request_keeps_governed_prompt_lane() -> None:
    packet = build_conversation_prompt(
        user_message="Run diagnostics on the supervised conversation service.",
        self_model={"name": "Eidolon", "active_goals": ["OPERATOR_GOAL_CANARY"]}, desires={}, memories=[],
        project_context="OPERATOR_PROJECT_CANARY", goal_context="OPERATOR_GOAL_CONTEXT_CANARY", task_context="OPERATOR_TASK_CANARY",
        conversation_history=[], cognitive_context="OPERATOR_COGNITIVE_CANARY", context_size=8192, max_tokens=128,
    )
    require(packet.metrics.prompt_lane == "governed_operator", packet.metrics.to_dict())
    require("CONVERSATION RESPONSE GUIDANCE" in packet.prompt, packet.prompt)
    require("OPERATOR_PROJECT_CANARY" in packet.prompt, packet.prompt)


def test_repetition_suppression_reaches_stream_and_nonstream_fast_paths() -> None:
    class FakeClient:
        prompts: list[tuple[str, str]] = []
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.last_retry_count = 0
            self.last_metrics: dict[str, Any] = {}
        def generate(self, prompt: str) -> str:
            type(self).prompts.append(("nonstream", prompt)); return "That improvement sounds satisfying."
        def stream(self, prompt: str):
            type(self).prompts.append(("stream", prompt)); yield "That sounds better."
        def cancel(self) -> None: return None
        def close(self) -> None: return None
        def __enter__(self): return self
        def __exit__(self, *_args: Any) -> None: self.close()

    sessions = []
    for label in ("nonstream", "stream"):
        session = create_conversation_session(title=f"synthetic repetition {label}", select_session=False)
        append_conversation_turn(session["id"], turn_id=f"{label}-1", user_message="The latch was sticking.",
                                 assistant_response="I understand. Let me know if you need anything else.", completion_state="completed", success=True, source="test")
        append_conversation_turn(session["id"], turn_id=f"{label}-2", user_message="I cleaned it again.",
                                 assistant_response="I understand. Let me know if you want to talk more.", completion_state="completed", success=True, source="test")
        sessions.append(session)
    original = conversation_runtime.LocalModelClient
    conversation_runtime.LocalModelClient = FakeClient
    try:
        result = conversation_runtime.run_conversation_turn("That part is better now.", use_ai=True, session_id=sessions[0]["id"], select_session_on_record=False)
        require(result.success is True, result.to_dict())
        events = list(conversation_runtime.stream_conversation_turn("That part is better now.", use_ai=True, session_id=sessions[1]["id"], select_session_on_record=False))
        require(any(event.get("event") == "done" for event in events), events[-5:])
    finally:
        conversation_runtime.LocalModelClient = original
    prompts = dict(FakeClient.prompts)
    require(set(prompts) == {"nonstream", "stream"}, list(prompts))
    for mode, prompt in prompts.items():
        require("REPETITION SUPPRESSION" in prompt, (mode, prompt))
        require("generic closing/help offer" in prompt, (mode, prompt))
        require(estimate_tokens(prompt) <= 900, (mode, estimate_tokens(prompt)))


def test_desktop_stream_timing_exposes_first_visible_before_completion() -> None:
    tracker = desktop_shell.DesktopChatStreamTracker(started_clock=100.0)
    tracker.observe({"event": "transport_accepted", "operation_id": "op-synthetic"}, now=100.1)
    tracker.mark_visible(now=100.25)
    tracker.observe({"event": "response_complete"}, now=100.8)
    tracker.observe({"event": "done"}, now=101.0)
    metrics = tracker.timing_metrics()
    require(metrics["send_to_acceptance_ms"] == 99 or metrics["send_to_acceptance_ms"] == 100, metrics)
    require(int(metrics["send_to_first_visible_text_ms"] or 0) < int(metrics["total_completion_ms"] or 0), metrics)
    require(metrics["content_free"] is True, metrics)


def test_desktop_sse_single_request_and_disconnect_no_replay() -> None:
    class Headers(dict):
        def get(self, key: str, default: Any = None) -> Any:
            return super().get(key, default)

    class Response:
        def __init__(self, *, disconnect: bool = False) -> None:
            self.headers = Headers({"X-Eidolon-Operation-Id": "op-fixture", "X-Eidolon-Session-Id": "session-fixture"})
            self.disconnect = disconnect
            self.closed = False

        def __iter__(self):
            yield b'event: accepted\n'
            yield b'data: {"event":"accepted","operation_id":"op-fixture","session_id":"session-fixture"}\n'
            yield b'\n'
            yield b'event: delta\n'
            yield b'data: {"event":"delta","text":"Visible "}\n'
            yield b'\n'
            if self.disconnect:
                raise ConnectionResetError("synthetic disconnect")
            yield b'event: done\n'
            yield b'data: {"event":"done","turn":{"eidolon_response":"Visible reply"}}\n'
            yield b'\n'

        def close(self) -> None:
            self.closed = True

    calls: list[Any] = []
    original = desktop_shell.urllib.request.urlopen
    try:
        response = Response()
        desktop_shell.urllib.request.urlopen = lambda request, timeout=0: (calls.append((request, timeout)) or response)
        client = desktop_shell.LocalApiClient()
        client.refresh_urls = lambda: None
        client.urls["dashboard_api"] = "http://127.0.0.1:9999/api"
        events = list(client.stream_dashboard_chat({"message": "fixture", "use_ai": True, "acceptance_key": "fixture-key"}, timeout=180))
        require(len(calls) == 1, calls)
        require(events[0]["event"] == "transport_accepted", events)
        require(any(item.get("event") == "delta" for item in events), events)
        require(any(item.get("event") == "done" for item in events), events)

        calls.clear()
        response = Response(disconnect=True)
        desktop_shell.urllib.request.urlopen = lambda request, timeout=0: (calls.append((request, timeout)) or response)
        try:
            list(client.stream_dashboard_chat({"message": "fixture", "use_ai": True, "acceptance_key": "fixture-key-2"}, timeout=180))
        except desktop_shell.DesktopApiError as error:
            require(error.payload.get("operation_id") == "op-fixture", error.payload)
            require(error.payload.get("automatic_retry") is False, error.payload)
        else:
            raise AssertionError("disconnect did not surface transport uncertainty")
        require(len(calls) == 1, calls)
    finally:
        desktop_shell.urllib.request.urlopen = original


def test_desktop_acceptance_cancel_close_and_repair_contracts() -> None:
    source = (AGENT / "desktop_shell.py").read_text(encoding="utf-8")
    dashboard_source = (AGENT / "dashboard.py").read_text(encoding="utf-8")
    send_block = source[source.index("    def send_chat()") : source.index("    def restore_from_watcher()")]
    exit_block = source[source.index("    def exit_desktop()") : source.index("    def on_close()")]
    require('"acceptance_key": acceptance_key' in send_block, "desktop send lacks exactly-once identity")
    require('"use_ai": bool(get_setting("ai_chat_enabled", True))' in send_block, "AI-generation repair regressed")
    require("timeout=180" in send_block, "local generation timeout repair regressed")
    require("cancel_dashboard_chat_operation" not in exit_block, "window close became implicit cancellation")
    require("detach_dashboard_chat_operation(operation_id)" in dashboard_source, "viewer disconnect no longer detaches safely")
    require('self.send_header("X-Eidolon-Operation-Id", operation_id)' in dashboard_source, "desktop cannot reconcile accepted stream identity")
    require(desktop_shell._desktop_chat_response({"data": {"eidolon_response": "preferred", "response": "legacy"}}) == "preferred")


def test_ollama_keep_alive_contract_is_preserved() -> None:
    source = (AGENT / "local_model.py").read_text(encoding="utf-8")
    require("ollama_keep_alive_minutes" in source, "keep-alive setting disappeared")
    require('"keep_alive": self._keep_alive()' in source, "Ollama generation no longer sends keep-alive")


def test_source_tree_privacy_boundary() -> None:
    forbidden_parts = {"data", "__pycache__", ".pytest_cache", ".venv", "venv", "env", "logs", "cache", "caches"}
    forbidden_suffixes = {".pyc", ".pyo", ".log"}
    bad: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if any(part.lower() in forbidden_parts for part in rel.parts) or path.suffix.lower() in forbidden_suffixes:
            bad.append(rel.as_posix())
    require(not bad, bad[:25])


def _follow_up_projection_for(
    message: str,
    *,
    history: list[dict[str, Any]] | None = None,
    relation: str = "respond",
    selected_intent: str = "direct_answer",
) -> dict[str, Any]:
    return build_natural_follow_up_runtime_projection(
        message,
        {"selected_intent": selected_intent, "intentional_silence_verified": False},
        {"discourse_relation": relation, "address_explicit_correction": False},
        {
            "continuity_relation": "continue_thread" if history else "fresh_turn",
            "continuity_confidence": "high",
            "consume_prior_question": False,
            "avoid_reasking_answered_question": True,
            "close_without_reopening": False,
        },
        conversation_history=history or [],
    )


def test_sharing_and_closure_cues_force_question_free_policy() -> None:
    for message in (
        "Honestly, I just wanted to share that with you.",
        "That's all.",
        "Just thought you'd like to know.",
        "Anyway, it felt good.",
    ):
        projection = _follow_up_projection_for(message)
        policy = projection["policy"]
        require(policy["sharing_or_closure_cue_present"] is True, (message, policy))
        require(policy["maximum_follow_up_questions"] == 0, (message, policy))
        require(policy["continuation_posture"] == "briefly_acknowledge_and_close", (message, policy))
        require("QUESTION BOUNDARY: Ask no question" in projection["prompt_section"], projection["prompt_section"])


def test_repeated_question_endings_suppress_optional_questions() -> None:
    history = [
        {"role": "assistant", "text": "That sounds satisfying. What part worked best?"},
        {"role": "assistant", "text": "I can see why it mattered. How did that feel?"},
        {"role": "user", "text": "I think I know what I want to do next."},
    ]
    projection = _follow_up_projection_for("What should I do next?", history=history)
    policy = projection["policy"]
    require(policy["repeated_question_ending_behavior"] is True, policy)
    require(policy["recent_question_ending_count"] >= 2, policy)
    require(policy["maximum_follow_up_questions"] == 0, policy)
    require(policy["optional_follow_up_suppressed"] is True, policy)


def test_required_and_user_invited_questions_remain_permitted() -> None:
    clarification = _follow_up_projection_for(
        "Please use the one I mentioned.", relation="clarify", selected_intent="request_clarification",
    )["policy"]
    require(clarification["question_permission"] == "required_clarification", clarification)
    require(clarification["maximum_follow_up_questions"] == 1, clarification)
    kept, diagnostics = enforce_natural_follow_up_output(
        "I need one detail before I can answer accurately. Which one did you mean?",
        clarification, casual_fast_path=True,
    )
    require(kept.endswith("?"), kept)
    require(diagnostics["output_question_units"] == 1, diagnostics)

    invited = _follow_up_projection_for("You can ask me one question about it.")["policy"]
    require(invited["question_permission"] == "user_invited", invited)
    require(invited["maximum_follow_up_questions"] == 1, invited)
    kept, diagnostics = enforce_natural_follow_up_output(
        "I do have one thing I'm curious about. What part surprised you most?",
        invited, casual_fast_path=True,
    )
    require(kept.endswith("?"), kept)
    require(diagnostics["suppressed_question_units"] == 0, diagnostics)


def test_fresh_session_invitation_survives_low_confidence_without_false_invites() -> None:
    canonical = {"selected_intent": "direct_answer", "intentional_silence_verified": False}
    discourse = {"discourse_relation": "respond", "address_explicit_correction": False}
    low_confidence = {
        "continuity_relation": "fresh_turn",
        "continuity_confidence": "low",
        "consume_prior_question": False,
        "avoid_reasking_answered_question": True,
        "close_without_reopening": False,
    }
    invited = build_natural_follow_up_runtime_projection(
        "Ask me one specific question about restoring old radios.",
        canonical, discourse, low_confidence, conversation_history=[],
    )["policy"]
    require(invited["question_permission"] == "user_invited", invited)
    require(invited["maximum_follow_up_questions"] == 1, invited)

    for complaint in (
        "Why did you ask me that?",
        "You always ask me too many questions.",
        "Please never feel like you have to ask me questions.",
        "Don't ask me another question.",
    ):
        policy = build_natural_follow_up_runtime_projection(
            complaint, canonical, discourse, low_confidence, conversation_history=[],
        )["policy"]
        require(policy["question_permission"] == "none", (complaint, policy))
        require(policy["maximum_follow_up_questions"] == 0, (complaint, policy))


def test_fresh_session_runtime_preserves_invited_question_stream_and_nonstream() -> None:
    class FakeClient:
        requests = 0
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.last_retry_count = 0
            self.last_metrics: dict[str, Any] = {}
        def generate(self, _prompt: str) -> str:
            type(self).requests += 1
            return "Sure! Which part of restoring the radio was most satisfying?"
        def stream(self, _prompt: str):
            type(self).requests += 1
            yield "Sure! Which part of restoring "
            yield "the radio was most satisfying?"
        def cancel(self) -> None: return None
        def close(self) -> None: return None
        def __enter__(self): return self
        def __exit__(self, *_args: Any) -> None: self.close()

    original = conversation_runtime.LocalModelClient
    conversation_runtime.LocalModelClient = FakeClient
    try:
        nonstream_session = create_conversation_session(title="fresh invited question", select_session=False)
        result = conversation_runtime.run_conversation_turn(
            "Ask me one specific question about restoring old radios.", use_ai=True,
            session_id=nonstream_session["id"], select_session_on_record=False,
        )
        require(result.response.endswith("?"), result.to_dict())
        enforcement = result.cognitive_context.get("natural_follow_up_output_enforcement") or {}
        require(enforcement.get("maximum_follow_up_questions") == 1, enforcement)
        require(enforcement.get("suppressed_question_units") == 0, enforcement)

        stream_session = create_conversation_session(title="fresh invited question stream", select_session=False)
        events = list(conversation_runtime.stream_conversation_turn(
            "Ask me one question about the radio.", use_ai=True,
            session_id=stream_session["id"], select_session_on_record=False,
        ))
        visible = "".join(str(event.get("text") or "") for event in events if event.get("event") == "delta")
        require(visible.endswith("?"), events)
        require(not any(event.get("event") == "replace" for event in events), events)
        require(sum(event.get("event") == "provider_request" for event in events) == 1, events)
        require(len(conversation_session_turns(stream_session["id"])) == 1, conversation_session_turns(stream_session["id"]))
        require(FakeClient.requests == 2, FakeClient.requests)
    finally:
        conversation_runtime.LocalModelClient = original


def test_stream_gate_never_retracts_visible_question() -> None:
    policy = _follow_up_projection_for("I just wanted to share that.")["policy"]
    gate = NaturalFollowUpStreamGate(policy, casual_fast_path=True)
    visible = []
    for chunk in ("That makes sense", ". I can see why ", "it mattered. What happened ", "next?"):
        piece = gate.feed(chunk)
        if piece:
            visible.append(piece)
            require("?" not in piece, piece)
    tail = gate.finish()
    if tail:
        visible.append(tail)
    text = "".join(visible).strip()
    require(text == "That makes sense. I can see why it mattered.", text)
    diagnostics = gate.diagnostics()
    require(diagnostics["suppressed_question_units"] == 1, diagnostics)
    require(diagnostics["provider_request_added"] is False, diagnostics)


def test_runtime_question_pressure_enforcement_stream_and_nonstream() -> None:
    class FakeClient:
        requests = 0
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.last_retry_count = 0
            self.last_metrics: dict[str, Any] = {}
        def generate(self, _prompt: str) -> str:
            type(self).requests += 1
            return "That sounds like something you wanted to let land. What else do you want to share?"
        def stream(self, _prompt: str):
            type(self).requests += 1
            yield "That sounds like something you wanted "
            yield "to let land. What else do you want "
            yield "to share?"
        def cancel(self) -> None: return None
        def close(self) -> None: return None
        def __enter__(self): return self
        def __exit__(self, *_args: Any) -> None: self.close()

    original = conversation_runtime.LocalModelClient
    conversation_runtime.LocalModelClient = FakeClient
    try:
        nonstream_session = create_conversation_session(title="question-free share", select_session=False)
        result = conversation_runtime.run_conversation_turn(
            "Honestly, I just wanted to share that with you.", use_ai=True,
            session_id=nonstream_session["id"], select_session_on_record=False,
        )
        require(result.success is True, result.to_dict())
        require("?" not in result.response, result.response)
        require(result.provider_request_count == 1, result.to_dict())
        enforcement = result.cognitive_context.get("natural_follow_up_output_enforcement") or {}
        require(enforcement.get("suppressed_question_units") == 1, enforcement)

        stream_session = create_conversation_session(title="question-free stream", select_session=False)
        events = list(conversation_runtime.stream_conversation_turn(
            "Just thought you'd like to know.", use_ai=True,
            session_id=stream_session["id"], select_session_on_record=False,
        ))
        deltas = "".join(str(e.get("text") or "") for e in events if e.get("event") == "delta")
        require("?" not in deltas, deltas)
        done = next(e for e in events if e.get("event") == "done")
        response = str((done.get("result") or {}).get("response") or "")
        require("?" not in response, done)
        require(not any(e.get("event") == "replace" for e in events), events)
        require(sum(1 for e in events if e.get("event") == "provider_request") == 1, events)
        turns = conversation_session_turns(stream_session["id"])
        require(len(turns) == 1, turns)
        require("?" not in str(turns[0].get("assistant_response") or ""), turns[0])
        require(FakeClient.requests == 2, FakeClient.requests)
    finally:
        conversation_runtime.LocalModelClient = original


def test_several_consecutive_sharing_replies_have_no_question_pressure() -> None:
    class FakeClient:
        requests = 0
        replies = (
            "That has a nice sense of completion to it. What happened next?",
            "I can see why you wanted to mention it. Want to keep going?",
            "That sounds like a good place to leave the thought for now. Anything else?",
        )
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.last_retry_count = 0
            self.last_metrics: dict[str, Any] = {}
        def generate(self, _prompt: str) -> str:
            index = type(self).requests
            type(self).requests += 1
            return type(self).replies[index % len(type(self).replies)]
        def cancel(self) -> None: return None
        def close(self) -> None: return None

    original = conversation_runtime.LocalModelClient
    conversation_runtime.LocalModelClient = FakeClient
    session = create_conversation_session(title="three sharing turns", select_session=False)
    try:
        outputs = []
        for message in ("Anyway, it felt good.", "Just thought you'd like to know.", "That's all."):
            result = conversation_runtime.run_conversation_turn(
                message, use_ai=True, session_id=session["id"], select_session_on_record=False,
            )
            require(result.success is True, result.to_dict())
            outputs.append(result.response)
        require(all("?" not in value for value in outputs), outputs)
        require(FakeClient.requests == 3, FakeClient.requests)
        require(len(set(outputs)) == 3, outputs)
        require(all("shared that with me" not in value.lower() for value in outputs), outputs)
    finally:
        conversation_runtime.LocalModelClient = original


TESTS = [
    ("meaningful_first_conversation_guidance", test_meaningful_first_conversation_guidance),
    ("excitement_and_appreciation_are_specific", test_excitement_and_appreciation_are_specific),
    ("relationship_reflection_after_difficulty", test_relationship_reflection_after_difficulty),
    ("multiturn_active_subject_is_preserved", test_multiturn_active_subject_is_preserved),
    ("repetition_suppression_is_model_readable", test_repetition_suppression_is_model_readable),
    ("sharing_and_closure_cues_force_question_free_policy", test_sharing_and_closure_cues_force_question_free_policy),
    ("repeated_question_endings_suppress_optional_questions", test_repeated_question_endings_suppress_optional_questions),
    ("required_and_user_invited_questions_remain_permitted", test_required_and_user_invited_questions_remain_permitted),
    ("fresh_session_invitation_survives_low_confidence_without_false_invites", test_fresh_session_invitation_survives_low_confidence_without_false_invites),
    ("fresh_session_runtime_preserves_invited_question_stream_and_nonstream", test_fresh_session_runtime_preserves_invited_question_stream_and_nonstream),
    ("stream_gate_never_retracts_visible_question", test_stream_gate_never_retracts_visible_question),
    ("runtime_question_pressure_enforcement_stream_and_nonstream", test_runtime_question_pressure_enforcement_stream_and_nonstream),
    ("several_consecutive_sharing_replies_have_no_question_pressure", test_several_consecutive_sharing_replies_have_no_question_pressure),
    ("casual_projection_omits_redundant_heavy_blocks", test_casual_projection_omits_redundant_heavy_blocks),
    ("stream_and_nonstream_effective_prompts_share_contracts", test_stream_and_nonstream_effective_prompts_share_contracts),
    ("casual_fast_path_prompt_budgets_and_sections", test_casual_fast_path_prompt_budgets_and_sections),
    ("operator_request_keeps_governed_prompt_lane", test_operator_request_keeps_governed_prompt_lane),
    ("repetition_suppression_reaches_stream_and_nonstream_fast_paths", test_repetition_suppression_reaches_stream_and_nonstream_fast_paths),
    ("desktop_stream_timing_exposes_first_visible_before_completion", test_desktop_stream_timing_exposes_first_visible_before_completion),
    ("desktop_sse_single_request_and_disconnect_no_replay", test_desktop_sse_single_request_and_disconnect_no_replay),
    ("desktop_acceptance_cancel_close_and_repair_contracts", test_desktop_acceptance_cancel_close_and_repair_contracts),
    ("ollama_keep_alive_contract_is_preserved", test_ollama_keep_alive_contract_is_preserved),
    ("source_tree_privacy_boundary", test_source_tree_privacy_boundary),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    checks: list[dict[str, Any]] = []
    passed = 0
    try:
        for name, callback in TESTS:
            started = time.monotonic()
            try:
                callback()
            except Exception as error:
                checks.append({"name": name, "status": "fail", "seconds": round(time.monotonic() - started, 4), "message": f"{type(error).__name__}: {error}"})
            else:
                passed += 1
                checks.append({"name": name, "status": "pass", "seconds": round(time.monotonic() - started, 4), "message": ""})
        report = {
            "suite": "v1489-unpromoted-conversation-repair",
            "ok": passed == len(TESTS),
            "status": "pass" if passed == len(TESTS) else "fail",
            "passed": passed,
            "total": len(TESTS),
            "checks": checks,
            "fixture_provider_only": True,
            "private_trial_transcript_used": False,
            "runtime_data_root": "external-temporary",
            "candidate_promoted": False,
        }
        print(json.dumps(report, indent=2) if args.json else f"{'pass' if report['ok'] else 'fail'}: {passed}/{len(TESTS)}")
        return 0 if report["ok"] else 1
    finally:
        shutil.rmtree(RUNTIME, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
