from __future__ import annotations

"""Focused v1500.8 conversational target and repetition checks."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for value in (str(ROOT), str(AGENT)):
    if value not in sys.path:
        sys.path.insert(0, value)

from conversation_target_continuity import (
    build_conversation_target_projection,
    enforce_conversation_target_output,
)

passed = failed = 0


def check(name: str, condition: bool, details: object = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print("PASS", name)
    else:
        failed += 1
        print("FAIL", name, details)


history = [{
    "user_message": "We reached the milestone and I want to rest.",
    "assistant_response": "Taking time to rest is well deserved before starting more work.",
}]

question = build_conversation_target_projection("How do you feel about your progress?", history)
check("newest direct question is primary", question["policy"]["target_kind"] == "current_question", question)
check("target prompt explicitly rejects older request", "Do not answer an older request" in question["prompt_section"])

follow_up = build_conversation_target_projection("Why?", history)
check("short why resolves latest completed pair", follow_up["policy"]["target_kind"] == "short_follow_up", follow_up)
check("short follow-up records completed pair", follow_up["policy"]["latest_completed_pair_available"] is True)

correction = build_conversation_target_projection("No, you seem stuck on my first message.", history)
check("correction outranks previous topic", correction["policy"]["target_kind"] == "current_correction", correction)

shift = build_conversation_target_projection("New topic: tell me about your memory system.", history)
check("explicit shift resets target", shift["policy"]["target_kind"] == "explicit_topic_shift", shift)

failed_history = history + [{
    "user_message": "Explain further.",
    "assistant_response": "This partial answer must not become continuity evidence.",
    "success": False,
    "completion_state": "cancelled",
}]
failed_projection = build_conversation_target_projection("How so?", failed_history)
check("cancelled turn is excluded from completed-pair count", failed_projection["policy"]["history_pairs_considered"] == 1, failed_projection)

duplicate, duplicate_diag = enforce_conversation_target_output(
    "Taking time to rest is well deserved before starting more work.",
    question, history, casual_fast_path=True,
)
check("whole repeated answer is replaced", duplicate_diag["whole_response_replaced"] is True, duplicate_diag)
check("replacement identifies missed newest question", "latest question" in duplicate, duplicate)

near_duplicate, near_diag = enforce_conversation_target_output(
    "Taking some time to rest is well deserved before beginning more work.",
    question, history, casual_fast_path=True,
)
check("near duplicate is resisted", near_diag["applied"] is True, near_diag)

partial_history = [{
    "user_message": "What changed?",
    "assistant_response": "The memory graph is more consistent. It now preserves corrected roles.",
}]
partial, partial_diag = enforce_conversation_target_output(
    "The memory graph is more consistent. It also resolves family aliases.",
    question, partial_history, casual_fast_path=True,
)
check("duplicate sentence is removed", partial_diag["duplicate_sentences_removed"] == 1, partial_diag)
check("novel sentence remains", partial == "It also resolves family aliases.", partial)

fresh, fresh_diag = enforce_conversation_target_output(
    "I can inspect my source and prepare bounded proposals now.",
    question, history, casual_fast_path=True,
)
check("substantively new response remains unchanged", fresh.startswith("I can inspect"), fresh)
check("new response does not trigger gate", fresh_diag["applied"] is False, fresh_diag)

governed, governed_diag = enforce_conversation_target_output(
    history[0]["assistant_response"], question, history, casual_fast_path=False,
)
check("non-casual governed lane remains unchanged", governed == history[0]["assistant_response"], governed)
check("governed lane does not apply repetition gate", governed_diag["applied"] is False, governed_diag)

serialized = json.dumps({"projection": question["policy"], "diagnostics": duplicate_diag}, sort_keys=True)
check("public evidence contains no transcript text", all(token not in serialized for token in ("milestone", "progress", "Taking time")), serialized)
check("target control adds no provider request", duplicate_diag["provider_request_added"] is False)
check("target control grants no authority", question["policy"]["authority_granted"] is False)

runtime = (AGENT / "conversation_runtime.py").read_text(encoding="utf-8")
check("target projection integrated in both runtime paths", runtime.count("build_conversation_target_projection(message, session_history)") == 2)
check("output enforcement integrated in both runtime paths", runtime.count("enforce_conversation_target_output(") == 2)

verifier = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
check("v1500.8 suite registered exactly once", verifier.count("v1500_8_conversation_target_continuity_tests.py") == 1)

print({
    "ok": failed == 0,
    "passed": passed,
    "failed": failed,
    "suite": "v1500.8-conversation-target-continuity",
    "provider_contacted": False,
    "source_mutated": False,
    "authority_granted": False,
    "content_free_public_evidence": True,
})
if failed:
    raise SystemExit(1)
