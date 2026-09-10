from __future__ import annotations

"""Integrated Era 3 reasoning checkpoint.

Composes problem framing, causal discrimination, long-horizon planning, and
metacognitive review into one bounded public projection.  The integration owns
no evidence store and no executor; each subsystem remains authoritative for its
own runtime record.
"""

from pathlib import Path
from typing import Any, Mapping, Sequence

from ordinary_chat_development_campaign import _digest
from problem_framing_intelligence import build_problem_frame, judge_clarification
from causal_counterfactual_intelligence import create_causal_case
from long_horizon_planning_intelligence import create_long_horizon_plan
from epistemic_self_correction import create_epistemic_session

CONTRACT_VERSION = "v1799.9"
AUTHORITY_FLAGS = {
    "reasoning_integration_authorized": True,
    "execution_authorized": False,
    "provider_contact_authorized": False,
    "external_research_authorized": False,
    "project_mutation_authorized": False,
    "source_mutation_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "standing_authority_granted": False,
}


def build_integrated_reasoning_case(
    request_text: str,
    *,
    project_evidence: Mapping[str, Any] | None = None,
    hypotheses: Sequence[Mapping[str, Any]] = (),
    milestones: Sequence[Mapping[str, Any]] = (),
    claims: Sequence[Mapping[str, Any]] = (),
    plan_steps_for_meta: Sequence[Mapping[str, Any]] = (),
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    frame = build_problem_frame(request_text, project_evidence=project_evidence, source_kind="era3_integrated_case", runtime_root=runtime_root)
    if not frame.get("ok"):
        return {"ok": False, "status": "problem_frame_blocked", "problem_framing": frame, **AUTHORITY_FLAGS}
    judgment = judge_clarification(str(frame["problem_frame_id"]), str(frame["problem_frame_digest"]), runtime_root=runtime_root)
    causal = None
    if len(hypotheses) >= 2:
        causal = create_causal_case(request_text, hypotheses, evidence_provenance=["problem_frame"], runtime_root=runtime_root)
    plan = None
    if milestones:
        plan = create_long_horizon_plan(
            request_text, milestones,
            acceptance_codes=[str(i.get("item_id") or "") for i in frame.get("acceptance_criteria") or []],
            stop_condition_codes=["operator_stop", "authority_boundary", "unsafe_state"],
            resource_codes=["bounded_time", "bounded_context"],
            runtime_root=runtime_root,
        )
    epistemic = create_epistemic_session(
        "era3_integrated_reasoning", claims=claims, plan_steps=plan_steps_for_meta,
        context_freshness=1.0, uncertainty=0.7 if frame.get("unknowns") else 0.35, runtime_root=runtime_root,
    )
    if judgment.get("judgment") in {"ask", "stop"}:
        next_move = "clarify_or_stop"
    elif epistemic.get("recommended_epistemic_action") in {"change_strategy", "seek_better_evidence", "deepen_reasoning"}:
        next_move = "self_correct_before_commitment"
    elif causal and (causal.get("discriminating_probes") or []) and causal["discriminating_probes"][0].get("discrimination_score", 0) > 0:
        next_move = "gather_discriminating_evidence"
    elif plan and plan.get("ok"):
        next_move = "review_bounded_plan"
    else:
        next_move = "proceed_bounded_without_execution"
    result = {
        "ok": True,
        "status": "era3_integrated_reasoning_ready",
        "contract_version": CONTRACT_VERSION,
        "problem_framing": {
            "problem_frame_id": frame.get("problem_frame_id"), "problem_frame_digest": frame.get("problem_frame_digest"),
            "counts": frame.get("counts"), "clarification_judgment": judgment.get("judgment"), "reason_code": judgment.get("reason_code"),
        },
        "causal_reasoning": None if not causal else {
            "causal_case_id": causal.get("causal_case_id"), "causal_case_digest": causal.get("causal_case_digest"),
            "hypothesis_count": causal.get("hypothesis_count"), "discriminating_probe_count": len(causal.get("discriminating_probes") or []),
            "root_cause_proven": False,
        },
        "long_horizon_plan": None if not plan else {
            "plan_id": plan.get("plan_id"), "plan_digest": plan.get("plan_digest"), "milestone_count": plan.get("milestone_count"),
            "original_objective_preserved": plan.get("original_objective_preserved"),
        },
        "metacognition": {
            "epistemic_session_id": epistemic.get("epistemic_session_id"), "epistemic_session_digest": epistemic.get("epistemic_session_digest"),
            "issue_codes": epistemic.get("issue_codes") or [], "recommended_epistemic_action": epistemic.get("recommended_epistemic_action"),
        },
        "next_reasoning_move": next_move,
        "private_chain_of_thought_exposed": False,
        "raw_request_exposed": False,
        "decision_created": False,
        "action_executed": False,
        **AUTHORITY_FLAGS,
    }
    result["integrated_reasoning_digest"] = _digest({k: v for k, v in result.items() if k != "integrated_reasoning_digest"})
    return result


__all__ = ["CONTRACT_VERSION", "AUTHORITY_FLAGS", "build_integrated_reasoning_case"]
