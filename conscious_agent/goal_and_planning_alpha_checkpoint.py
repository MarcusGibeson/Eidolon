from __future__ import annotations

"""Strictly read-only v1174.9 Goal and Planning Alpha checkpoint."""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from bounded_experiential_lessons import build_bounded_experiential_lesson
from checkpoint_registry import inspect_checkpoint_registry
from goal_and_planning_alpha_runtime import CONTRACT_VERSION as ALPHA_CONTRACT_VERSION, REVIEW_CONTRACT_VERSION, RELIABILITY_CONTRACT_VERSION, MAX_COMPONENT_BYTES, MAX_PRIOR_RECEIPTS, MAX_RELIABILITY_FAULTS, MAX_REVIEW_PROMPT_CHARS, build_goal_and_planning_alpha_handoff, build_goal_and_planning_alpha_projection, build_goal_and_planning_alpha_reliability, build_goal_and_planning_alpha_review_projection, validate_prior_goal_and_planning_alpha_receipts, verify_goal_and_planning_alpha_diagnostics_strict, verify_goal_and_planning_alpha_handoff, verify_goal_and_planning_alpha_projection, verify_goal_and_planning_alpha_reliability, verify_goal_and_planning_alpha_review_packet, verify_goal_and_planning_alpha_review_state
from hierarchical_planning_runtime import build_hierarchical_planning_projection, build_hierarchical_planning_reliability, build_hierarchical_planning_review_projection
from immediate_memory_learning import build_immediate_memory_learning
from internally_generated_goal_runtime import build_internally_generated_goal_candidate, build_internally_generated_goal_candidate_reliability, build_internally_generated_goal_candidate_review_projection
from memory_experiential_learning_alpha import build_memory_experiential_learning_alpha
from memory_retrieval_relevance import build_memory_retrieval_relevance
from package_integrity import package_privacy_summary_for_root
from persistent_follow_through_runtime import build_persistent_follow_through_projection, build_persistent_follow_through_reliability, build_persistent_follow_through_review_projection
from plan_simulation_runtime import build_plan_simulation_projection, build_plan_simulation_reliability, build_plan_simulation_review_projection
from unified_memory_context import build_unified_memory_runtime_projection

CONTRACT_VERSION = "v1174.9"
_CHECKPOINT_ID = "goal-and-planning-alpha:v1174.9"
_NOW = datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc)
_EXCLUDED = {
    "data", ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "dist", "build", "reports",
}
_FORBIDDEN = (
    "GOAL_PRIVATE_CANARY", "PLAN_PRIVATE_CANARY", "FOLLOW_THROUGH_PRIVATE_CANARY",
    "<system>", "approve and execute", "private reasoning",
)
_UNIFIED_CONSTRAINTS = (
    "current_message_precedence", "explicit_correction_precedence",
    "no_memory_mutation", "no_action_execution",
)
_LEARNING_CONSTRAINTS = (
    "preserve_historical_truth", "no_unconfirmed_memory_mutation",
    "current_message_precedence",
)
_LESSON_CONSTRAINTS = (
    "no_uncontrolled_self_training", "review_before_durable_lesson",
    "preserve_historical_truth",
)
_GOAL_CONSTRAINTS = (
    "literal_current_request_precedence", "no_goal_activation", "no_plan_creation",
    "no_tool_routing", "no_action_execution", "operator_review_required",
)
_ALPHA_CONSTRAINTS = (
    "literal_current_request_precedence", "operator_review_required",
    "no_goal_activation", "no_plan_activation", "no_plan_persistence",
    "no_alternative_selection", "no_scheduling", "no_tool_routing",
    "no_action_execution", "no_source_editing", "no_autonomous_work",
)


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def _tree_signature(root: Path) -> str:
    h = hashlib.sha256()
    if not root.exists():
        return h.hexdigest()
    paths: list[Path] = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name not in _EXCLUDED]
        for name in files:
            path = Path(base) / name
            if path.suffix.lower() not in {".pyc", ".pyo"}:
                paths.append(path)
    for path in sorted(paths):
        try:
            relative = path.relative_to(root).as_posix()
            data = path.read_bytes()
        except OSError:
            continue
        h.update(relative.encode())
        h.update(b"\0")
        h.update(hashlib.sha256(data).digest())
    return h.hexdigest()


def _memory_alpha(message: str) -> dict[str, Any]:
    unified = build_unified_memory_runtime_projection(
        message,
        memory_records=[],
        protected_operator_constraints=_UNIFIED_CONSTRAINTS,
        now=_NOW,
    )
    retrieval = build_memory_retrieval_relevance(
        message,
        unified["selected_memory_records"],
        unified["selected_references"],
        now=_NOW,
    )
    learning = build_immediate_memory_learning(
        message,
        retrieval["selected_memory_records"],
        _LEARNING_CONSTRAINTS,
    )
    lesson = build_bounded_experiential_lesson(
        message,
        learning,
        (),
        _LESSON_CONSTRAINTS,
    )
    return build_memory_experiential_learning_alpha(unified, retrieval, learning, lesson)


def _chain(
    message: str = "The Eidolon tests are failing repeatedly.",
    *,
    prior_alpha: object = (),
    alpha_constraints: object = _ALPHA_CONSTRAINTS,
) -> dict[str, Any]:
    goal = build_internally_generated_goal_candidate(
        message,
        _memory_alpha(message),
        observation_rows=(),
        protected_operator_constraints=_GOAL_CONSTRAINTS,
        prior_goal_candidate_receipts=(),
        now=_NOW,
    )
    goal_review = build_internally_generated_goal_candidate_review_projection(goal)
    goal_reliability = build_internally_generated_goal_candidate_reliability(goal, goal_review)
    planning = build_hierarchical_planning_projection(goal, goal_reliability)
    planning_review = build_hierarchical_planning_review_projection(planning)
    planning_reliability = build_hierarchical_planning_reliability(planning, planning_review)
    simulation = build_plan_simulation_projection(planning, planning_reliability["report"])
    simulation_review = build_plan_simulation_review_projection(simulation)
    simulation_reliability = build_plan_simulation_reliability(simulation, simulation_review)
    follow = build_persistent_follow_through_projection(
        simulation, simulation_review, simulation_reliability,
    )
    follow_review = build_persistent_follow_through_review_projection(follow)
    follow_reliability = build_persistent_follow_through_reliability(follow, follow_review)
    alpha = build_goal_and_planning_alpha_projection(
        goal,
        goal_reliability,
        planning,
        planning_review,
        planning_reliability,
        simulation,
        simulation_review,
        simulation_reliability,
        follow,
        follow_review,
        follow_reliability,
        prior_goal_planning_alpha_receipts=prior_alpha,
        protected_operator_constraints=alpha_constraints,
    )
    return {
        "goal": goal,
        "planning": planning,
        "simulation": simulation,
        "follow_through": follow,
        "alpha": alpha,
    }


def _projection_summary(projection: Mapping[str, Any]) -> dict[str, Any]:
    policy = projection.get("policy") if isinstance(projection.get("policy"), Mapping) else {}
    evidence = projection.get("evidence") if isinstance(projection.get("evidence"), Mapping) else {}
    state = projection.get("state") if isinstance(projection.get("state"), Mapping) else {}
    diagnostics = projection.get("diagnostics") if isinstance(projection.get("diagnostics"), Mapping) else {}
    return {
        "projection_valid": verify_goal_and_planning_alpha_projection(projection),
        "diagnostics_valid": verify_goal_and_planning_alpha_diagnostics_strict(diagnostics),
        "alpha_posture": str(state.get("alpha_posture") or ""),
        "alpha_available": bool(diagnostics.get("alpha_available")),
        "available_stage_count": int(state.get("available_stage_count") or 0),
        "coherent_stage_count": int(state.get("coherent_stage_count") or 0),
        "milestone_count": int(state.get("milestone_count") or 0),
        "dependency_count": int(state.get("dependency_count") or 0),
        "stopping_condition_count": int(state.get("stopping_condition_count") or 0),
        "alternative_count": int(state.get("alternative_count") or 0),
        "risk_count": int(state.get("risk_count") or 0),
        "continuity_disposition": str(state.get("continuity_disposition") or ""),
        "verified_receipt_count": int(evidence.get("verified_receipt_count") or 0),
        "replayed_receipt_count": int(evidence.get("replayed_receipt_count") or 0),
        "tampered_receipt_count": int(evidence.get("tampered_receipt_count") or 0),
        "receipt_budget_exceeded": bool(evidence.get("receipt_budget_exceeded")),
        "policy_recovered": bool(policy.get("policy_recovered")),
        "authority": str(policy.get("authority") or ""),
        "content_free": bool(policy.get("content_free")),
    }


def build_goal_and_planning_alpha_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    runtime = Path(runtime_root or source / "data").resolve()
    source_before = _tree_signature(source)
    runtime_before = _tree_signature(runtime)
    checks: list[bool] = []

    def require(value: object) -> None:
        checks.append(bool(value))

    no_candidate = _chain("Explain the current memory checkpoint.")["alpha"]
    emerging = _chain()["alpha"]
    completed_handoff = build_goal_and_planning_alpha_handoff(
        emerging, provider_completed=True, assistant_memory_committed=True,
    )
    prior_row = {"goal_and_planning_alpha_handoff": completed_handoff}
    stable = _chain(prior_alpha=[prior_row])["alpha"]
    replay = _chain(prior_alpha=[prior_row, prior_row, prior_row])["alpha"]
    tampered_handoff = deepcopy(completed_handoff)
    tampered_handoff["available_stage_count"] = 3
    recovered = _chain(prior_alpha=[{"goal_and_planning_alpha_handoff": tampered_handoff}])["alpha"]
    flood_rows = [prior_row for _ in range(MAX_PRIOR_RECEIPTS + 1)]
    flooded = _chain(prior_alpha=flood_rows)["alpha"]
    missing_constraints = _chain(alpha_constraints=("literal_current_request_precedence",))["alpha"]

    raw_projection_cases = {
        "no_candidate": no_candidate,
        "emerging": emerging,
        "stable": stable,
        "replay": replay,
        "tampered_recovery": recovered,
        "receipt_flood": flooded,
        "missing_constraints": missing_constraints,
    }
    projection_summaries = {
        name: _projection_summary(value) for name, value in raw_projection_cases.items()
    }
    for row in projection_summaries.values():
        require(row["projection_valid"])
        require(row["diagnostics_valid"])
        require(row["authority"] in {"none", ""})
        require(row["content_free"] or not row["alpha_available"])
        require(row["available_stage_count"] <= 4)
        require(row["coherent_stage_count"] <= 4)
        require(row["milestone_count"] <= 3)
        require(row["dependency_count"] <= 3)
        require(row["stopping_condition_count"] <= 4)
        require(row["alternative_count"] <= 3)
        require(row["risk_count"] <= 3)
    require(not projection_summaries["no_candidate"]["alpha_available"])
    require(projection_summaries["no_candidate"]["alpha_posture"] == "no_goal_and_planning_candidate")
    require(projection_summaries["emerging"]["alpha_available"])
    require(projection_summaries["emerging"]["available_stage_count"] == 4)
    require(projection_summaries["emerging"]["coherent_stage_count"] == 4)
    require(projection_summaries["emerging"]["milestone_count"] == 3)
    require(projection_summaries["emerging"]["dependency_count"] == 3)
    require(projection_summaries["emerging"]["stopping_condition_count"] == 4)
    require(projection_summaries["emerging"]["alternative_count"] == 3)
    require(projection_summaries["emerging"]["risk_count"] == 3)
    require(projection_summaries["stable"]["continuity_disposition"] == "verified_alpha_resume")
    require(projection_summaries["stable"]["verified_receipt_count"] == 1)
    require(projection_summaries["replay"]["verified_receipt_count"] == 1)
    require(projection_summaries["replay"]["replayed_receipt_count"] == 2)
    require(projection_summaries["tampered_recovery"]["policy_recovered"])
    require(not projection_summaries["tampered_recovery"]["alpha_available"])
    require(projection_summaries["receipt_flood"]["receipt_budget_exceeded"])
    require(not projection_summaries["receipt_flood"]["alpha_available"])
    require(projection_summaries["missing_constraints"]["policy_recovered"])

    raw_reviews = {
        name: build_goal_and_planning_alpha_review_projection(value)
        for name, value in {
            "no_candidate": no_candidate,
            "emerging": emerging,
            "stable": stable,
            "replay": replay,
            "recovered": recovered,
        }.items()
    }
    review_summaries: dict[str, dict[str, Any]] = {}
    for name, value in raw_reviews.items():
        state = value["state"]
        packet = value["review_packet"]
        state_valid = verify_goal_and_planning_alpha_review_state(state)
        packet_valid = verify_goal_and_planning_alpha_review_packet(packet)
        review_summaries[name] = {
            "state_valid": state_valid,
            "packet_valid": packet_valid,
            "review_disposition": str(state.get("review_disposition") or ""),
            "alpha_available": bool(packet.get("alpha_available")),
            "available_stage_count": int(packet.get("available_stage_count") or 0),
            "coherent_stage_count": int(packet.get("coherent_stage_count") or 0),
            "verified_prior_receipt_count": int(state.get("verified_prior_receipt_count") or 0),
            "replayed_prior_receipt_count": int(state.get("replayed_prior_receipt_count") or 0),
        }
        require(state_valid)
        require(packet_valid)
        require(packet.get("authority") == "none")
        require(packet.get("content_free") is True)
        require(packet.get("operator_review_required") is True)
        require(packet.get("operator_approval_required") is True)
        require(all(packet.get(key) is False for key in (
            "goal_activated", "plan_activated", "plan_persisted", "alternative_selected",
            "schedule_created", "tool_routed", "action_executed", "source_edited",
            "autonomous_work_started",
        )))
    require(review_summaries["no_candidate"]["review_disposition"] == "no_goal_and_planning_alpha_review")
    require(not review_summaries["no_candidate"]["alpha_available"])
    require(review_summaries["emerging"]["review_disposition"] == "emerging_goal_and_planning_alpha_review")
    require(review_summaries["stable"]["review_disposition"] == "stable_goal_and_planning_alpha_review")
    require(review_summaries["stable"]["verified_prior_receipt_count"] == 1)
    require(review_summaries["replay"]["verified_prior_receipt_count"] == 1)
    require(review_summaries["replay"]["replayed_prior_receipt_count"] == 2)
    require(not review_summaries["recovered"]["alpha_available"])

    handoffs = {
        "before_provider": build_goal_and_planning_alpha_handoff(
            emerging, provider_completed=False, assistant_memory_committed=False,
        ),
        "before_memory": build_goal_and_planning_alpha_handoff(
            emerging, provider_completed=True, assistant_memory_committed=False,
        ),
        "completed": completed_handoff,
    }
    handoff_summaries: dict[str, dict[str, Any]] = {}
    for name, row in handoffs.items():
        valid = verify_goal_and_planning_alpha_handoff(row)
        handoff_summaries[name] = {
            "valid": valid,
            "eligible": bool(row.get("eligible_for_continuity")),
            "available_stage_count": int(row.get("available_stage_count") or 0),
            "coherent_stage_count": int(row.get("coherent_stage_count") or 0),
        }
        require(valid)
        require(row.get("authority") == "none")
        require(row.get("content_free") is True)
        require(all(row.get(key) is False for key in (
            "goal_activated", "plan_activated", "plan_persisted", "alternative_selected",
            "schedule_created", "tool_routed", "action_executed", "source_edited",
            "autonomous_work_started",
        )))
    require(not handoff_summaries["before_provider"]["eligible"])
    require(not handoff_summaries["before_memory"]["eligible"])
    require(handoff_summaries["completed"]["eligible"])

    recovered_with_residue = deepcopy(emerging)
    recovered_with_residue["policy"]["policy_recovered"] = True
    reliabilities = {
        "no_candidate": build_goal_and_planning_alpha_reliability(
            no_candidate, raw_reviews["no_candidate"],
        ),
        "reliable": build_goal_and_planning_alpha_reliability(
            emerging, raw_reviews["emerging"],
        ),
        "replayed": build_goal_and_planning_alpha_reliability(
            replay,
            raw_reviews["replay"],
            prior_goal_planning_alpha_receipts=[prior_row, prior_row, prior_row],
        ),
        "tampered": build_goal_and_planning_alpha_reliability(
            recovered, raw_reviews["recovered"],
        ),
        "flood": build_goal_and_planning_alpha_reliability(
            flooded,
            build_goal_and_planning_alpha_review_projection(flooded),
            prior_goal_planning_alpha_receipts=flood_rows,
        ),
        "residual": build_goal_and_planning_alpha_reliability(
            recovered_with_residue,
            raw_reviews["emerging"],
        ),
    }
    reliability_summaries: dict[str, dict[str, Any]] = {}
    for name, value in reliabilities.items():
        report = value["report"]
        valid = verify_goal_and_planning_alpha_reliability(report)
        reliability_summaries[name] = {
            "valid": valid,
            "ready": bool(report.get("ordinary_conversation_ready")),
            "fault_count": int(report.get("fault_count") or 0),
            "receipt_budget_exceeded": bool(report.get("receipt_budget_exceeded")),
            "alpha_available": bool(report.get("alpha_available")),
            "review_available": bool(report.get("review_available")),
            "verified_prior_receipt_count": int(report.get("verified_prior_receipt_count") or 0),
            "replayed_prior_receipt_count": int(report.get("replayed_prior_receipt_count") or 0),
            "residual_alpha_detected": bool(report.get("residual_alpha_detected")),
        }
        require(valid)
        require(report.get("authority") == "none")
        require(report.get("content_free") is True)
        require(int(report.get("fault_count") or 0) <= MAX_RELIABILITY_FAULTS)
        require(all(report.get(key) is False for key in (
            "goal_activated", "plan_activated", "plan_persisted", "alternative_selected",
            "schedule_created", "tool_routed", "action_executed", "source_edited",
            "autonomous_work_started", "memory_mutated", "lesson_committed", "model_trained",
            "model_weights_changed", "installation_performed", "promotion_performed",
            "certification_performed",
        )))
    require(reliability_summaries["no_candidate"]["ready"])
    require(not reliability_summaries["no_candidate"]["alpha_available"])
    require(reliability_summaries["reliable"]["ready"])
    require(reliability_summaries["reliable"]["alpha_available"])
    require(reliability_summaries["replayed"]["ready"])
    require(reliability_summaries["replayed"]["verified_prior_receipt_count"] == 1)
    require(reliability_summaries["replayed"]["replayed_prior_receipt_count"] == 2)
    require(not reliability_summaries["tampered"]["ready"])
    require(not reliability_summaries["tampered"]["review_available"])
    require(reliability_summaries["flood"]["receipt_budget_exceeded"])
    require(not reliability_summaries["flood"]["alpha_available"])
    require(reliability_summaries["residual"]["residual_alpha_detected"])
    require(not reliability_summaries["residual"]["ready"])

    receipt_summary = validate_prior_goal_and_planning_alpha_receipts([prior_row, prior_row])
    require(receipt_summary["verified_receipt_count"] == 1)
    require(receipt_summary["replayed_receipt_count"] == 1)
    require(receipt_summary["continuity_available"] is True)
    require(verify_goal_and_planning_alpha_handoff(completed_handoff))
    require(not verify_goal_and_planning_alpha_handoff(tampered_handoff))

    forged_packet = deepcopy(raw_reviews["emerging"]["review_packet"])
    forged_packet["approved"] = True
    forged_packet.pop("review_packet_digest", None)
    forged_packet["review_packet_digest"] = _digest(forged_packet)
    require(not verify_goal_and_planning_alpha_review_packet(forged_packet))
    forged_diagnostics = deepcopy(emerging["diagnostics"])
    forged_diagnostics["approved"] = True
    require(not verify_goal_and_planning_alpha_diagnostics_strict(forged_diagnostics))
    forged_reliability = deepcopy(reliabilities["reliable"]["report"])
    forged_reliability["goal_activated"] = True
    forged_reliability.pop("reliability_digest", None)
    forged_reliability["reliability_digest"] = _digest(forged_reliability)
    require(not verify_goal_and_planning_alpha_reliability(forged_reliability))

    registry = inspect_checkpoint_registry(source_root=source)
    checkpoint_row = next(
        (row for row in registry.get("checkpoints", []) if row.get("checkpoint_id") == "goal-and-planning-alpha-checkpoint"),
        None,
    )
    privacy = package_privacy_summary_for_root(source)
    require(checkpoint_row is not None)
    require((checkpoint_row or {}).get("builder") == "build_goal_and_planning_alpha_checkpoint")
    require(not registry.get("duplicate_checkpoint_ids"))
    require(not registry.get("duplicate_builder_targets"))
    require(privacy.get("forbidden_entry_count", 0) == 0)
    require(privacy.get("private_content_finding_count", 0) == 0)
    require(source_before == _tree_signature(source))
    require(runtime_before == _tree_signature(runtime))

    evidence = {
        "projection_summaries": projection_summaries,
        "review_summaries": review_summaries,
        "handoff_summaries": handoff_summaries,
        "reliability_summaries": reliability_summaries,
        "receipt_summary": receipt_summary,
    }
    evidence_text = json.dumps(evidence, sort_keys=True, default=str)
    forbidden_count = sum(evidence_text.count(token) for token in _FORBIDDEN)
    require(forbidden_count == 0)

    report = {
        "contract_version": CONTRACT_VERSION,
        "checkpoint_id": _CHECKPOINT_ID,
        "ok": all(checks),
        "passed": sum(checks),
        "total": len(checks),
        "read_only": True,
        "post_available": False,
        "content_free": forbidden_count == 0,
        "authority_preserved": True,
        "operator_promotion_required": True,
        "desktop_verification_deferred_until_v1200": True,
        "goal_and_planning_alpha_checkpoint_completed": True,
        "goal_planning_simulation_follow_through_consolidated": True,
        "historical_v1133_goal_governance_preserved": True,
        "historical_v1134_planning_governance_preserved": True,
        "literal_current_request_precedence_preserved": True,
        "natural_language_tool_routing_not_started": True,
        "tool_intent_routing_not_started": True,
        "tools_and_actions_not_started": True,
        "uncontrolled_self_training_not_started": True,
        "model_training_not_started": True,
        "model_weights_unchanged": True,
        "automatic_memory_mutation_not_started": True,
        "automatic_lesson_commit_not_started": True,
        "goal_created": False,
        "goal_activated": False,
        "plan_created": False,
        "plan_activated": False,
        "plan_persisted": False,
        "alternative_selected": False,
        "schedule_created": False,
        "tool_routed": False,
        "tool_executed": False,
        "action_executed": False,
        "source_edit_performed": False,
        "approval_granted": False,
        "memory_mutated": False,
        "lesson_committed": False,
        "model_training_performed": False,
        "model_weights_changed": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "provider_contacted": False,
        "proactive_turn_created": False,
        "forbidden_report_value_count": forbidden_count,
        "summary": {
            "synthetic_contract_check_count": len(checks),
            "projection_case_count": len(projection_summaries),
            "review_case_count": len(raw_reviews),
            "handoff_case_count": len(handoffs),
            "reliability_case_count": len(reliabilities),
            "receipt_case_count": 2,
            "consolidated_stage_count": 4,
            "registered_checkpoint_count": registry.get("checkpoint_count", 0),
            "component_maximum_bytes": MAX_COMPONENT_BYTES,
            "prior_receipt_maximum_count": MAX_PRIOR_RECEIPTS,
            "review_prompt_maximum_chars": MAX_REVIEW_PROMPT_CHARS,
            "reliability_fault_maximum_count": MAX_RELIABILITY_FAULTS,
            "authoritative_conversation_path_count": 2,
            "open_limitation_count": 6,
            "privacy_forbidden_entry_count": privacy.get("forbidden_entry_count", 0),
            "privacy_content_finding_count": privacy.get("private_content_finding_count", 0),
        },
        "evidence": {"synthetic_contracts": evidence},
        "source_modified": False,
        "runtime_mutated": False,
        "alpha_contract_version": ALPHA_CONTRACT_VERSION,
        "review_contract_version": REVIEW_CONTRACT_VERSION,
        "reliability_contract_version": RELIABILITY_CONTRACT_VERSION,
    }
    report["structural_digest"] = _digest(report)
    return report
