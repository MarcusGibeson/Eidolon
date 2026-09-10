from __future__ import annotations
import copy, hashlib, json
from conscious_agent.plan_simulation_runtime import (
    build_plan_simulation_projection, build_plan_simulation_review_handoff,
    build_plan_simulation_review_projection, build_plan_simulation_reliability,
    verify_plan_simulation_diagnostics_strict, verify_plan_simulation_reliability,
)

def projection(prior=()):
    p={"hierarchy":{"plan_candidate_available":True,"milestone_count":3,"dependency_count":2,"stopping_condition_count":3},"policy":{"operator_review_required":True,"plan_activation_permitted":False,"action_execution_permitted":False}}
    r={"reliability_posture":"hierarchical_planning_context_reliable","ordinary_conversation_ready":True,"plan_candidate_available":True}
    return build_plan_simulation_projection(p,r,prior_simulation_receipts=prior)

def reliability(value=None, prior=()):
    value=value or projection(prior)
    review=build_plan_simulation_review_projection(value)
    return build_plan_simulation_reliability(value,review,prior_simulation_receipts=prior)

def test_clean_reliability_is_available_and_content_free():
    out=reliability(); report=out["report"]
    assert report["reliability_posture"]=="plan_simulation_context_reliable"
    assert report["simulation_available"] is True and verify_plan_simulation_reliability(report)
    assert len(out["prompt_section"]) < 2048

def test_digest_valid_unknown_diagnostic_field_is_rejected():
    value=projection(); d=copy.deepcopy(value["diagnostics"]); d["approved"]=True
    assert not verify_plan_simulation_diagnostics_strict(d)

def test_receipt_budget_flood_fails_closed():
    first=projection(); receipt=build_plan_simulation_review_handoff(first,provider_completed=True,assistant_memory_committed=True)
    rows=[{"plan_simulation_review_handoff":receipt} for _ in range(65)]
    report=reliability(projection(rows),rows)["report"]
    assert report["ordinary_conversation_ready"] is False and report["receipt_budget_exceeded"] is True

def test_replay_does_not_amplify_verified_count():
    first=projection(); receipt=build_plan_simulation_review_handoff(first,provider_completed=True,assistant_memory_committed=True)
    rows=[{"plan_simulation_review_handoff":receipt}]*2
    report=reliability(projection(rows),rows)["report"]
    assert report["verified_prior_receipt_count"] == 1
    assert report["replayed_prior_receipt_count"] == 1

def test_tampered_receipt_fails_closed():
    first=projection(); receipt=build_plan_simulation_review_handoff(first,provider_completed=True,assistant_memory_committed=True)
    receipt["alternative_selected"]=True
    rows=[{"plan_simulation_review_handoff":receipt}]
    report=reliability(projection(rows),rows)["report"]
    assert report["ordinary_conversation_ready"] is False
    assert report["simulation_available"] is False

def test_recovered_projection_with_residue_is_detected():
    value=projection(); value["policy"]["policy_recovered"]=True
    value["diagnostics"]["recovered"]=True
    value["diagnostics"]["integrity_digest"] = hashlib.sha256(json.dumps({"policy":value["policy"],"evidence":value["evidence"],"comparison":value["comparison"]},sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
    report=reliability(value)["report"]
    assert report["residual_simulation_detected"] is True
    assert report["review_available"] is False

def test_forged_authority_in_reliability_is_rejected():
    report=copy.deepcopy(reliability()["report"]); report["alternative_selected"]=True
    report.pop("reliability_digest")
    report["reliability_digest"]=hashlib.sha256(json.dumps(report,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
    assert not verify_plan_simulation_reliability(report)

def test_shared_streaming_and_non_streaming_integration():
    source=open("conscious_agent/conversation_runtime.py",encoding="utf-8").read()
    assert source.count("build_plan_simulation_reliability(") == 2
    assert source.count('result.cognitive_context["plan_simulation_reliability"]') == 2
    assert source.count('plan_simulation_reliability["prompt_section"]') == 2

def test_no_v1173_or_execution_authority_added():
    source=open("conscious_agent/plan_simulation_runtime.py",encoding="utf-8").read().lower()
    assert "persistent_follow_through" not in source
    assert "execute_plan(" not in source
