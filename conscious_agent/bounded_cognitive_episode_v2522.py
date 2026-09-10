from __future__ import annotations

"""v2522 provider-free multi-step structural cognitive episodes.

An episode is a bounded sequence of selected cognitive operations and structural
outcome candidates. It is not a transcript and does not execute actions or apply
candidate mutations.
"""

import hashlib, json
from typing import Any, Mapping
from background_structural_cognition_v2505 import derive_structural_background_outcome
from cognitive_operation_arbitration import arbitrate_cognitive_operation
from cognitive_state_delta_v2522 import compare_cognitive_frames

CONTRACT_VERSION = "v2522.5"
MAX_STEPS = 3


def _digest(v: Any) -> str:
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()


def _next_operation(op: str, outcome: Mapping[str, Any], frame: Mapping[str, Any]) -> str | None:
    p = frame.get("projection") if isinstance(frame.get("projection"), Mapping) else {}
    beliefs = p.get("beliefs") if isinstance(p.get("beliefs"), Mapping) else {}
    planning = p.get("planning") if isinstance(p.get("planning"), Mapping) else {}
    conflicts = int(beliefs.get("active_conflict_count") or 0)
    plans = int(planning.get("active_count") or 0)
    if op == "RECONSIDER_BELIEF" and conflicts:
        return "RESOLVE_CONFLICT"
    if op == "REVIEW_GOAL" and plans:
        return "REPLAN"
    if op == "RECALL_MEMORY":
        return "REFLECT"
    if op == "INTEGRATE_EXPERIENCE":
        return "REFLECT"
    if op == "REFLECT" and outcome.get("outcome_type") == "THOUGHT_CONTINUATION":
        return None
    return None


def build_bounded_cognitive_episode(
    frame: Mapping[str, Any], *, previous_frame: Mapping[str, Any] | None = None,
    unfinished_thought_count: int = 0, new_experience: bool = False,
    self_model_evidence: bool = False, max_steps: int = MAX_STEPS,
) -> dict[str, Any]:
    if not isinstance(frame, Mapping) or not frame.get("ok") or not frame.get("frame_digest"):
        raise ValueError("valid cognitive frame required")
    limit = max(1, min(MAX_STEPS, int(max_steps or MAX_STEPS)))
    arbitration = arbitrate_cognitive_operation(frame, unfinished_thought_count=unfinished_thought_count, new_experience=new_experience, self_model_evidence=self_model_evidence)
    op = str(arbitration["selected_operation"])
    steps = []
    visited = set()
    while op and len(steps) < limit and op not in visited:
        visited.add(op)
        outcome = derive_structural_background_outcome(op, frame) if op != "REST" else {
            "ok": True, "operation":"REST", "outcome_type":"NO_DURABLE_CHANGE", "changed_fields":[], "confidence":0.9,
            "reason_code":"deliberate_inactivity", "frame_digest": str(frame["frame_digest"]), "candidate_applied":False,
            "provider_contacted":False,"message_sent":False,"tool_executed":False,"source_mutated":False,"hidden_reasoning_exposed":False,
        }
        steps.append({
            "step": len(steps)+1,
            "operation": op,
            "outcome_type": str(outcome.get("outcome_type") or "NO_DURABLE_CHANGE"),
            "reason_code": str(outcome.get("reason_code") or "")[:120],
            "confidence": round(float(outcome.get("confidence") or 0.0), 4),
            "changed_fields": list(outcome.get("changed_fields") or [])[:8],
        })
        op = _next_operation(op, outcome, frame)
    delta = compare_cognitive_frames(previous_frame, frame)
    row = {
        "ok": True,
        "contract_version": CONTRACT_VERSION,
        "frame_digest": str(frame["frame_digest"]),
        "delta_digest": delta["delta_digest"],
        "meaningful_changes": delta["meaningful_changes"],
        "initial_operation": steps[0]["operation"] if steps else "REST",
        "steps": steps,
        "step_count": len(steps),
        "completed_structurally": True,
        "candidate_outcomes": sorted({s["outcome_type"] for s in steps if s["outcome_type"] != "NO_DURABLE_CHANGE"}),
        "provider_contacted": False,
        "message_sent": False,
        "tool_executed": False,
        "source_mutated": False,
        "candidate_applied": False,
        "hidden_reasoning_exposed": False,
        "raw_reasoning_stored": False,
        "authority_broadened": False,
    }
    row["episode_digest"] = _digest(row)
    return row

__all__ = ["CONTRACT_VERSION", "MAX_STEPS", "build_bounded_cognitive_episode"]
