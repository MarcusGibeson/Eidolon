from __future__ import annotations

import argparse, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"conscious_agent"),str(ROOT/"tools")]

from provider_neutral_conversation_tuning import build_provider_neutral_tuning_plan
import post_review_development_verify as isolated_verify


def require(value,message:str)->None:
    if not value: raise AssertionError(message)


def card(status="partial", issues=None, scenarios=12):
    return {"status":status,"scenario_count":scenarios,"issue_counts":issues or {}}


def test_issue_counts_produce_bounded_ranked_recommendations() -> None:
    plan=build_provider_neutral_tuning_plan(card(issues={"response_shape_mismatch":4,"required_continuity_signal_missing":2,"identity_continuity_risk":1}))
    require(plan.status=="operator_review_recommended" and plan.operator_review_required,"review plan not produced")
    require(plan.recommendation_codes[0]=="response_shape" and len(plan.recommendation_codes)<=6,"recommendations not ranked or bounded")


def test_plan_is_provider_neutral_for_equivalent_evidence() -> None:
    base=card(issues={"stock_response_hygiene_risk":2})
    ollama=build_provider_neutral_tuning_plan({**base,"provider":"ollama","model":"one"})
    llama=build_provider_neutral_tuning_plan({**base,"provider":"llama_cpp","model":"two"})
    require(ollama==llama,"provider identity changed tuning plan")
    encoded=json.dumps(ollama.public_summary())
    require("ollama" not in encoded and "llama" not in encoded,"provider-specific data leaked into plan")


def test_clean_scorecard_recommends_no_change() -> None:
    plan=build_provider_neutral_tuning_plan(card(status="pass",issues={}))
    require(plan.status=="no_change_recommended" and not plan.operator_review_required,"clean evidence invented tuning")


def test_missing_or_unavailable_evidence_stays_pending() -> None:
    missing=build_provider_neutral_tuning_plan(None)
    unavailable=build_provider_neutral_tuning_plan(card(status="unavailable",scenarios=0))
    require(missing.status=="evidence_required" and unavailable.status=="evidence_required","missing evidence produced false tuning truth")


def test_plan_cannot_mutate_provider_model_personality_or_state() -> None:
    plan=build_provider_neutral_tuning_plan(card(issues={"relationship_boundary_violation":1})).public_summary()
    require(plan["automatic_application_allowed"] is False,"automatic application allowed")
    require(not plan["provider_configuration_changed"] and not plan["model_configuration_changed"],"provider/model configuration changed")
    require(not plan["prompt_policy_changed"] and not plan["writes_state"] and not plan["mutates_personality"],"preview mutated runtime policy")
    require(plan["contains_message_content"] is False and plan["contains_response_text"] is False,"content leaked")


def test_suite_registered_exactly_once() -> None:
    names=[suite.name for suite in isolated_verify.SUITES]
    require(names.count("v1102.7-provider-neutral-conversation-tuning")==1,"suite registration wrong")


TESTS=[(n.removeprefix("test_"),f) for n,f in list(globals().items()) if n.startswith("test_")]
def main()->int:
    argparse.ArgumentParser().add_argument("--json",action="store_true")
    checks=[]
    for n,f in TESTS:
        try:f()
        except Exception as e:checks.append({"name":n,"status":"fail","message":f"{type(e).__name__}: {e}"})
        else:checks.append({"name":n,"status":"pass","message":""})
    passed=sum(r["status"]=="pass" for r in checks); report={"suite":"v1102.7-provider-neutral-conversation-tuning","ok":passed==len(TESTS),"status":"pass" if passed==len(TESTS) else "fail","passed":passed,"total":len(TESTS),"checks":checks}
    print(json.dumps(report,indent=2));return 0 if report["ok"] else 1
if __name__=="__main__":raise SystemExit(main())
