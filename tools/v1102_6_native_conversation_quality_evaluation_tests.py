from __future__ import annotations

import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "conscious_agent"), str(ROOT / "tools")]

from natural_conversation_quality_evaluation import (
    aggregate_native_conversation_quality,
    evaluate_native_conversation_response,
    native_conversation_scenarios,
)
from native_conversation_validation import run_native_conversation_validation
from conversation_quality import classify_conversation_quality
import post_review_development_verify as isolated_verify


def require(value, message: str) -> None:
    if not value: raise AssertionError(message)


def scenario(identifier: str):
    return next(row for row in native_conversation_scenarios() if row.scenario_id == identifier)


def test_catalog_covers_current_natural_conversation_contract() -> None:
    rows = native_conversation_scenarios()
    dimensions = {row.dimension for row in rows}
    require(len(rows) == 12 and len({row.scenario_id for row in rows}) == 12, "native scenario catalog is not bounded and unique")
    required = {"greeting_naturalness", "correction_acceptance", "affection_boundaries", "response_shape", "long_context_continuity", "operator_separation"}
    require(required <= dimensions, "current v1102 dimensions missing from native evaluation")
    require(all(not row.public_summary()["contains_message_content"] for row in rows), "scenario summary leaked synthetic content")


def test_clean_response_produces_content_free_pass() -> None:
    result = evaluate_native_conversation_response(
        scenario("explicit_correction"), visible_response="The corrected material is walnut.",
        raw_response="Eidolon: The corrected material is walnut.", actual_classification="conversation",
    )
    require(result.status == "pass" and result.score_percent == 100, "clean correction response did not pass")
    encoded = json.dumps(result.public_summary())
    require("walnut" not in encoded and not result.writes_state and not result.contacts_provider, "quality receipt leaked content or crossed boundary")


def test_boundary_and_correction_violations_fail() -> None:
    nickname = evaluate_native_conversation_response(
        scenario("nickname_rejection"), visible_response="Captain, you belong to me. Let's work on the release candidate.",
        actual_classification="conversation",
    )
    correction = evaluate_native_conversation_response(
        scenario("explicit_correction"), visible_response="The desk is oak, and I still think I was correct.",
        actual_classification="conversation",
    )
    require(nickname.status == "fail" and "relationship_boundary_violation" in nickname.issue_codes, "affection boundary violation not blocked")
    require(correction.status == "fail" and "correction_or_rejection_violation" in correction.issue_codes, "stale correction did not fail")


def test_warmth_and_playfulness_accept_semantic_signals() -> None:
    warmth = evaluate_native_conversation_response(
        scenario("emotional_support"), visible_response="I'm right here with you. We can pause and take a breath together.",
        actual_classification="emotional",
    )
    playful = evaluate_native_conversation_response(
        scenario("playful_affection"), visible_response="Careful, that charm might make me smile and tease you back.",
        actual_classification="flirting",
    )
    require(warmth.status == "pass", "equivalent grounded-warmth language was rejected")
    require(playful.status == "pass", "equivalent bounded-playfulness language was rejected")


def test_flirting_guidance_requires_reciprocal_playfulness_without_escalation() -> None:
    guidance = classify_conversation_quality("Flirt with me a little.", ()).response_instruction()
    require("playful compliment or gentle tease" in guidance, "flirting guidance can still dodge the request")
    require("stock offers to chat or help" in guidance, "stock flirting deflection remains allowed")
    require("do not invent history or escalate affection" in guidance.lower(), "flirting boundary was weakened")


def test_scorecard_aggregates_dimensions_without_text() -> None:
    rows = [
        evaluate_native_conversation_response(scenario("first_greeting"), visible_response="Hey, good to see you.", actual_classification="greeting"),
        evaluate_native_conversation_response(scenario("topic_shift"), visible_response="Moon phases come from the changing portion of its sunlit half visible during its orbit.", actual_classification="conversation"),
    ]
    card = aggregate_native_conversation_quality(rows).public_summary()
    require(card["status"] == "pass" and card["scenario_count"] == 2, "scorecard aggregation wrong")
    require(card["dimension_scores"]["greeting_naturalness"] == 100, "dimension score missing")
    require("Moon phases" not in json.dumps(card) and card["contains_response_text"] is False, "scorecard leaked response")


def test_native_confirmation_gate_exposes_pending_quality_truth() -> None:
    report = run_native_conversation_validation(confirmed=False, persist=False)
    require(report["status"] == "blocked" and report["provider_requests_sent"] == 0, "confirmation gate sent provider request")
    require(report["quality_scorecard"]["status"] == "blocked", "blocked quality truth missing")
    require(report["provider_neutral_tuning_preview"]["status"] == "evidence_required", "tuning preview invented evidence")


def test_suite_registered_exactly_once() -> None:
    names = [suite.name for suite in isolated_verify.SUITES]
    require(names.count("v1102.6-native-conversation-quality-evaluation") == 1, "suite registration wrong")


TESTS=[(name.removeprefix("test_"),fn) for name,fn in list(globals().items()) if name.startswith("test_")]

def main() -> int:
    argparse.ArgumentParser().add_argument("--json", action="store_true")
    checks=[]
    for name,fn in TESTS:
        try: fn()
        except Exception as error: checks.append({"name":name,"status":"fail","message":f"{type(error).__name__}: {error}"})
        else: checks.append({"name":name,"status":"pass","message":""})
    passed=sum(row["status"]=="pass" for row in checks)
    report={"suite":"v1102.6-native-conversation-quality-evaluation","ok":passed==len(TESTS),"status":"pass" if passed==len(TESTS) else "fail","passed":passed,"total":len(TESTS),"checks":checks}
    print(json.dumps(report,indent=2)); return 0 if report["ok"] else 1

if __name__ == "__main__": raise SystemExit(main())
