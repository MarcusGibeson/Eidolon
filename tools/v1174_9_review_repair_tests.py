from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "conscious_agent"))

from bounded_experiential_lessons import validate_prior_lesson_receipts
from memory_experiential_learning_alpha import validate_prior_memory_experiential_learning_alpha_receipts
from immediate_memory_learning import build_immediate_memory_learning, validate_prior_learning_receipts
from response_intent_selection import build_response_intent_selection
from conversation_runtime import _bound_unverified_action_claim


def require(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


ordinary_history = [{
    "id": "conversation_fixture",
    "user_message": "hello",
    "assistant_response": "Hi.",
    "completion_state": "completed",
    "success": True,
}]
learning_history = validate_prior_learning_receipts(ordinary_history)
lesson_history = validate_prior_lesson_receipts(ordinary_history)
alpha_history = validate_prior_memory_experiential_learning_alpha_receipts(ordinary_history)
require(learning_history["tampered_receipt_count"] == 0, "ordinary history triggered learning tamper recovery")
require(learning_history["continuity_disposition"] == "use_current_turn_only", "ordinary learning continuity degraded")
require(lesson_history["tampered_receipt_count"] == 0, "ordinary history triggered lesson tamper recovery")
require(not lesson_history["policy_recovered"], "ordinary lesson continuity degraded")
require(not alpha_history["recovery_required"], "ordinary history triggered alpha recovery")

malformed_learning = validate_prior_learning_receipts([{"immediate_memory_learning_commit_handoff": "invalid"}])
malformed_lesson = validate_prior_lesson_receipts([{"bounded_experiential_lesson_review_handoff": "invalid"}])
require(malformed_learning["tampered_receipt_count"] == 1, "malformed learning receipt was ignored")
require(malformed_lesson["tampered_receipt_count"] == 1, "malformed lesson receipt was ignored")

learning = build_immediate_memory_learning(
    "Stop calling me Daddy",
    [],
    protected_operator_constraints=(
        "preserve_historical_truth", "no_unconfirmed_memory_mutation", "current_message_precedence",
    ),
    prior_learning_receipts=ordinary_history,
)
require(learning["policy"]["candidate_type"] == "preference_change", "direct nickname rejection was not learned")
require(learning["policy"]["current_turn_precedence"], "direct preference did not receive current-turn precedence")

correction_intent = build_response_intent_selection(
    "Stop calling me Daddy", reasoning_state={}, conversation_history=ordinary_history,
)
require(correction_intent["selected_intent"] == "correction", "direct nickname rejection was not classified as correction")

action_intent = build_response_intent_selection(
    "Do a system maintenance check", reasoning_state={}, conversation_history=ordinary_history,
)
require(action_intent["evidence"]["action_intent_present"], "imperative maintenance request was not action intent")
require(action_intent["construction_directives"]["execution_claims_forbidden"], "execution claims were not forbidden")
require("never claim an action ran" in action_intent["prompt_section"], "action receipt boundary missing from prompt")
bounded_claim = _bound_unverified_action_claim("Certainly. Let's proceed with a maintenance check.", action_intent)
require("have not executed it" in bounded_claim, "model execution claim was not bounded")

question = build_response_intent_selection(
    "Do you like the name Eidolon?", reasoning_state={}, conversation_history=ordinary_history,
)
require(not question["evidence"]["action_intent_present"], "ordinary do-question became action intent")

runtime_source = (ROOT / "conscious_agent" / "conversation_runtime.py").read_text(encoding="utf-8")
planning_source = (ROOT / "conscious_agent" / "hierarchical_planning_runtime.py").read_text(encoding="utf-8")
require(runtime_source.count("queue_turn_completion_safely(") == 2, "both runtime paths must queue optional cognition")
require('include_cognitive_context=False' in runtime_source, "stream result still emits full cognitive evidence")
require('"reproduce_reliability_failure"' in planning_source, "planning remains generic")

report = {
    "ok": True,
    "suite": "v1174.9-review-repair",
    "ordinary_history_false_recovery_repaired": True,
    "direct_preference_learning_repaired": True,
    "imperative_action_intent_repaired": True,
    "unsupported_execution_claims_blocked": True,
    "post_turn_cognition_queued": True,
    "stream_payload_compacted": True,
    "planning_milestones_specialized": True,
}
print(json.dumps(report, sort_keys=True))
