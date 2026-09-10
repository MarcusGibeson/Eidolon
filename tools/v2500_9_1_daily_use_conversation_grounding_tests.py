from __future__ import annotations

"""Focused v2500.9.1 daily-use conversation grounding checkpoint."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for value in (str(ROOT), str(AGENT)):
    if value not in sys.path:
        sys.path.insert(0, value)

from active_conversation_facts import resolve_active_conversation_facts
from conversation_target_continuity import (
    build_conversation_target_projection,
    enforce_conversation_target_output,
)
from natural_conversation_quality_runtime import build_natural_conversation_quality_runtime_profile
from release_authority import (
    AUTHORITY_FLAGS,
    CHECKPOINT_HISTORY,
    CODEX_REVIEW_STATE,
    PREVIOUS_WORKING_SOURCE_VERSION,
    WORKING_SOURCE_VERSION,
)


checks: list[str] = []


def require(condition: bool, name: str, details: object = "") -> None:
    if not condition:
        raise AssertionError(f"{name}: {details}")
    checks.append(name)


history = (
    {
        "user_message": (
            "Earlier I said I was worn out but proud of reaching a milestone. "
            "We got distracted by repeated coding failures. What did that sound like to you?"
        ),
        "assistant_response": "You sounded proud, exhausted, and frustrated.",
    },
)
message = "Be specific to today, not general advice. Why does that matter to me right now?"
quality = build_natural_conversation_quality_runtime_profile(message, history, emotional=True)
guidance = " ".join(quality.prompt_lines()).casefold()
require(quality.present_stakes_grounding_required, "present_stakes_profile_activates")
require("attributable current circumstance" in guidance, "present_stakes_prompt_requires_evidence")
require("do not substitute generic advice" in guidance, "present_stakes_prompt_rejects_generic_advice")

projection = build_conversation_target_projection(message, history)
generic = (
    "Reflecting on your feelings can help you understand how you are handling success and setbacks. "
    "This awareness may help you approach future problems with a clearer mindset."
)
grounded, diagnostics = enforce_conversation_target_output(
    generic,
    projection,
    history,
    casual_fast_path=True,
)
require(diagnostics["present_stakes_grounding_applied"] is True, "generic_present_stakes_answer_is_repaired")
require("you were worn out but proud" in grounded.casefold(), "repair_shifts_user_evidence_to_companion_voice")
require("we got distracted" in grounded.casefold(), "repair_retains_shared_current_circumstance")
require("not coach you through it" in grounded.casefold(), "repair_explains_relational_stake")
require(all(term not in grounded.casefold() for term in ("reflecting on", "this awareness", "clearer mindset")), "repair_removes_generic_self_help")
serialized_diagnostics = json.dumps(diagnostics, sort_keys=True).casefold()
require(all(term not in serialized_diagnostics for term in ("worn out", "coding failures", "milestone")), "public_diagnostics_are_content_free")
require(diagnostics["provider_request_added"] is False, "repair_adds_no_provider_request")
require(diagnostics["authority_granted"] is False, "repair_grants_no_authority")

good = "It matters because today you needed me to understand the cost of that milestone, and changing subjects missed that moment."
unchanged, unchanged_diagnostics = enforce_conversation_target_output(
    good,
    projection,
    history,
    casual_fast_path=True,
)
require(unchanged == good, "already_grounded_provider_answer_is_preserved")
require(unchanged_diagnostics["present_stakes_grounding_applied"] is False, "good_answer_does_not_trigger_repair")

current_family = WORKING_SOURCE_VERSION.split(".", 1)[0]
overview = resolve_active_conversation_facts(
    f"We finally made it to {current_family}. I bet you're feeling pretty smart now, aren't you?",
    (),
)
require(overview.state == "grounded_current_milestone_reflection", "current_milestone_banter_is_grounded")
require(overview.response.startswith("Maybe a little."), "current_milestone_preserves_playful_tone")
require("bounded multi-step session" in overview.response and "signed evidence" in overview.response, "milestone_overview_names_verified_capabilities")

proudest = resolve_active_conversation_facts(
    f"What part of reaching v{current_family} are you personally proudest of, and why that part?",
    (),
)
require(proudest.fact_kind == "current_milestone_proudest_capability", "proudest_follow_up_has_distinct_intent")
require("proudest that I can now coordinate a bounded research objective" in proudest.response, "proudest_follow_up_selects_one_capability")
require("final authority remains with you" in proudest.response, "proudest_follow_up_explains_significance")

limitation = resolve_active_conversation_facts(f"What part of v{current_family} still limits you or frustrates you most?", ())
require(limitation.fact_kind == "current_milestone_limitation", "limitation_follow_up_has_distinct_intent")
require("largest remaining limitation" in limitation.response and "live-trial reliability" in limitation.response and "sustained operator-run trials" in limitation.response, "limitation_follow_up_names_current_reliability_gap")

significance = resolve_active_conversation_facts(f"Why does v{current_family} matter to our development relationship?", ())
require(significance.fact_kind == "current_milestone_significance", "significance_follow_up_has_distinct_intent")
require("meaningfully two-sided" in significance.response, "significance_follow_up_answers_relationship_question")

older = resolve_active_conversation_facts("We made it to v2400. I bet you're feeling smart now.", ())
require(older.state != "grounded_current_milestone_reflection", "historical_version_does_not_masquerade_as_current")

require(tuple(map(int, WORKING_SOURCE_VERSION.split("."))) >= (2500, 9, 1), "checkpoint_remains_in_current_lineage")
require("2500.9.1" in {WORKING_SOURCE_VERSION, PREVIOUS_WORKING_SOURCE_VERSION} or tuple(map(int, WORKING_SOURCE_VERSION.split("."))) > (2500, 9, 1), "previous_checkpoint_preserved")
require(any(version == "2500.9.1" and title == "Daily-Use Conversation Grounding Checkpoint" for version, title in CHECKPOINT_HISTORY), "milestone_is_retained")
require(bool(CODEX_REVIEW_STATE) and "checkpoint_candidate" in CODEX_REVIEW_STATE, "review_state_preserves_operator_review_boundary")
require(not any(AUTHORITY_FLAGS.values()), "checkpoint_grants_no_authority")

verifier = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(verifier.count("v2500_9_1_daily_use_conversation_grounding_tests.py") == 1, "checkpoint_suite_registered_once")

print(json.dumps({
    "suite": "v2500.9.1-daily-use-conversation-grounding",
    "ok": True,
    "passed": len(checks),
    "failed": 0,
    "checks": checks,
    "provider_contacted": False,
    "source_mutated": False,
    "authority_granted": False,
}, sort_keys=True))
