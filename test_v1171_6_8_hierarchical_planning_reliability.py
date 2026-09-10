from copy import deepcopy
from conscious_agent.hierarchical_planning_runtime import (
    _digest, build_hierarchical_planning_projection, build_hierarchical_planning_review_handoff,
    build_hierarchical_planning_review_projection, build_hierarchical_planning_reliability,
    verify_hierarchical_planning_diagnostics_strict, verify_hierarchical_planning_reliability,
)

def _base(prior=()):
    goal={"policy":{"candidate_available":True,"operator_review_required":True,"goal_activation_permitted":False,"plan_creation_permitted":False},"candidate":{"candidate_type":"reliability_improvement","scope_band":"system"},"evidence":{"candidate_evidence_count":2}}
    rel={"reliability_posture":"goal_candidate_context_reliable","candidate_available":True}
    p=build_hierarchical_planning_projection(goal,rel,prior_planning_receipts=prior)
    return p, build_hierarchical_planning_review_projection(p)

def test_1171_6_clean_reliability_is_ready_and_content_free():
    p,r=_base(); out=build_hierarchical_planning_reliability(p,r)
    assert out["report"]["ordinary_conversation_ready"] is True
    assert verify_hierarchical_planning_reliability(out["report"])
    assert "private reasoning" not in str(out).lower()

def test_1171_6_digest_valid_unknown_diagnostic_field_is_rejected():
    p,r=_base(); p=deepcopy(p); p["diagnostics"]["approved"]=True
    p["diagnostics"]["integrity_digest"]=_digest({"policy":p["policy"],"evidence":p["evidence"],"hierarchy":p["hierarchy"]})
    assert not verify_hierarchical_planning_diagnostics_strict(p["diagnostics"])
    assert build_hierarchical_planning_reliability(p,r)["report"]["ordinary_conversation_ready"] is False

def test_1171_7_receipt_flood_fails_closed():
    p,r=_base(); hand=build_hierarchical_planning_review_handoff(p,provider_completed=True,assistant_memory_committed=True)
    rows=[{"hierarchical_planning_review_handoff":dict(hand,receipt_digest=str(i).zfill(64))} for i in range(65)]
    out=build_hierarchical_planning_reliability(p,r,prior_planning_receipts=rows)["report"]
    assert out["receipt_budget_exceeded"] and not out["review_available"]

def test_1171_7_replay_does_not_amplify_verified_count():
    p,r=_base(); hand=build_hierarchical_planning_review_handoff(p,provider_completed=True,assistant_memory_committed=True)
    rows=[{"hierarchical_planning_review_handoff":hand}]*3
    out=build_hierarchical_planning_reliability(p,r,prior_planning_receipts=rows)["report"]
    assert out["verified_prior_receipt_count"]==1 and out["replayed_prior_receipt_count"]==2

def test_1171_7_recovered_state_with_residue_is_suppressed():
    p,r=_base(); p=deepcopy(p); p["policy"]["policy_recovered"]=True
    out=build_hierarchical_planning_reliability(p,r)["report"]
    assert out["residual_plan_detected"] and not out["plan_candidate_available"]

def test_1171_8_reliability_rejects_forged_execution_authority():
    p,r=_base(); report=build_hierarchical_planning_reliability(p,r)["report"]
    report=deepcopy(report); report["plan_activated"]=True; report["reliability_digest"]=_digest({k:v for k,v in report.items() if k!="reliability_digest"})
    assert not verify_hierarchical_planning_reliability(report)

def test_1171_8_prompt_is_bounded_and_nonexecuting():
    p,r=_base(); out=build_hierarchical_planning_reliability(p,r)
    assert len(out["prompt_section"])<2048 and 'authority="none"' in out["prompt_section"]
