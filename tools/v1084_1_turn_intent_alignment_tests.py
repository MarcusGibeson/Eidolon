from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
AGENT=ROOT/"conscious_agent"
sys.path.insert(0,str(AGENT))

from chat_action_router import propose_chat_action
from conversation_context import build_conversation_prompt
from conversation_quality import classify_conversation_quality
from conversation_turn_intent import classify_turn_intent


def require(value, message: str) -> None:
    if not value: raise AssertionError(message)


def test_required_intents_are_distinct() -> None:
    cases={
        "Why is the sky blue?":"question",
        "Please summarize this clearly.":"request",
        "I feel overwhelmed today.":"emotional_sharing",
        "Actually, I meant Tuesday, not Thursday.":"correction",
        "Brainstorm several approaches for this.":"brainstorming",
        "That movie was strange.":"casual_remark",
    }
    for text, expected in cases.items():
        profile=classify_conversation_quality(text)
        require(profile.turn_intent.primary_intent==expected, f"{text!r} classified as {profile.turn_intent.primary_intent}")


def test_project_instruction_uses_existing_operator_boundary() -> None:
    text="Review conscious_agent/conversation_context.py and explain a safe improvement."
    profile=classify_conversation_quality(text)
    require(profile.turn_intent.primary_intent=="project_instruction", "explicit project instruction not aligned")
    require(profile.explicit_operator_request and profile.should_analyze_action, "operator action boundary weakened")
    action=propose_chat_action(text,save=False)
    require(action["intent"]=="review_file", "existing governed route changed")


def test_ambiguous_ordinary_language_is_not_a_correction() -> None:
    for text in ("I think Tuesday works.", "Maybe that is different.", "No idea what to eat."):
        intent=classify_turn_intent(text)
        require(not intent.explicit_correction, f"ambiguous ordinary text inferred as correction: {text}")
        require(intent.ambiguous_correction_inferred is False, "classifier claims inferred correction")


def test_emotional_question_keeps_both_signals() -> None:
    profile=classify_conversation_quality("I feel nervous. What should I do?")
    require(profile.turn_intent.primary_intent=="emotional_sharing", "emotional sharing lost priority")
    require("question" in profile.turn_intent.flags and "emotional_sharing" in profile.turn_intent.flags, "secondary intent flags missing")


def test_multiple_questions_are_not_silently_dropped() -> None:
    profile=classify_conversation_quality("What changed? Why did it change? What happens next?")
    require(profile.turn_intent.question_count==3, "question count wrong")
    guidance=profile.response_instruction().lower()
    require("multiple questions" in guidance and "cover each" in guidance, "multi-question guidance missing")


def test_prompt_contains_specific_intent_guidance() -> None:
    packet=build_conversation_prompt(
        user_message="Actually, I meant Tuesday, not Thursday.", self_model={"name":"Eidolon"}, desires={}, memories=[],
        project_context="", goal_context="", task_context="", conversation_history=[], context_size=4096, max_tokens=256,
    )
    require("TURN INTENT ALIGNMENT" in packet.prompt, "intent block missing")
    require("use the corrected meaning" in packet.prompt, "correction guidance missing")
    require(packet.metrics.conversation_turn_intent=="correction", "intent metric missing")


def test_intent_receipt_is_content_free_and_provider_free() -> None:
    intent=classify_turn_intent("Actually, my private answer is Tuesday.")
    summary=intent.public_summary(); serialized=json.dumps(summary)
    require("private answer" not in serialized, "intent receipt leaked message")
    require(summary["writes_state"] is False and summary["contacts_provider"] is False, "intent classifier crossed boundary")


TESTS=[
    ("required_intents_are_distinct",test_required_intents_are_distinct),
    ("project_instruction_uses_existing_operator_boundary",test_project_instruction_uses_existing_operator_boundary),
    ("ambiguous_ordinary_language_is_not_a_correction",test_ambiguous_ordinary_language_is_not_a_correction),
    ("emotional_question_keeps_both_signals",test_emotional_question_keeps_both_signals),
    ("multiple_questions_are_not_silently_dropped",test_multiple_questions_are_not_silently_dropped),
    ("prompt_contains_specific_intent_guidance",test_prompt_contains_specific_intent_guidance),
    ("intent_receipt_is_content_free_and_provider_free",test_intent_receipt_is_content_free_and_provider_free),
]

def main()->int:
    argparse.ArgumentParser().add_argument("--json",action="store_true")
    checks=[]; passed=0
    for name,fn in TESTS:
        try: fn()
        except Exception as error: checks.append({"name":name,"status":"fail","message":f"{type(error).__name__}: {error}"})
        else: passed+=1; checks.append({"name":name,"status":"pass","message":""})
    report={"suite":"v1084.1-turn-intent-alignment","ok":passed==len(TESTS),"status":"pass" if passed==len(TESTS) else "fail","passed":passed,"total":len(TESTS),"checks":checks}
    print(json.dumps(report,indent=2)); return 0 if report["ok"] else 1
if __name__=="__main__": raise SystemExit(main())
