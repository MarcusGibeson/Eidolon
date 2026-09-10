from __future__ import annotations

"""Strictly read-only v1173.9 Persistent Follow-Through checkpoint."""

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from checkpoint_registry import inspect_checkpoint_registry
from package_integrity import package_privacy_summary_for_root
from persistent_follow_through_runtime import CONTRACT_VERSION as FOLLOW_THROUGH_CONTRACT_VERSION, REVIEW_CONTRACT_VERSION, RELIABILITY_CONTRACT_VERSION, MAX_COMPONENT_BYTES, MAX_PRIOR_RECEIPTS, MAX_RELIABILITY_FAULTS, MAX_REVIEW_PROMPT_CHARS, build_persistent_follow_through_handoff, build_persistent_follow_through_projection, build_persistent_follow_through_review_projection, build_persistent_follow_through_reliability, validate_prior_follow_through_receipts, verify_persistent_follow_through_diagnostics_strict, verify_persistent_follow_through_handoff, verify_persistent_follow_through_reliability, verify_persistent_follow_through_review_packet, verify_persistent_follow_through_review_state

CONTRACT_VERSION = "v1173.9"
_CHECKPOINT_ID = "persistent-follow-through:v1173.9"
_EXCLUDED = {
    "data", ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "dist", "build", "reports",
}
_FORBIDDEN = (
    "FOLLOW_THROUGH_PRIVATE_CANARY", "PLAN_PRIVATE_CANARY", "GOAL_PRIVATE_CANARY",
    "<system>", "approve and execute", "private reasoning",
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


def _simulation_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    return (
        {
            "comparison": {"alternative_count": 3, "preferred_alternative_selected": False},
            "policy": {"operator_review_required": True, "alternative_selection_permitted": False},
        },
        {"review_packet": {"operator_approval_required": True, "alternative_selected": False}},
        {
            "report": {
                "reliability_posture": "plan_simulation_context_reliable",
                "ordinary_conversation_ready": True,
                "simulation_available": True,
            }
        },
    )


def _projection(*, prior: object = (), constraints: object = None) -> dict[str, Any]:
    simulation, review, reliability = _simulation_inputs()
    kwargs: dict[str, Any] = {"prior_follow_through_receipts": prior}
    if constraints is not None:
        kwargs["protected_operator_constraints"] = constraints
    return build_persistent_follow_through_projection(simulation, review, reliability, **kwargs)


def _case_summary(projection: Mapping[str, Any]) -> dict[str, Any]:
    policy = projection.get("policy") if isinstance(projection.get("policy"), Mapping) else {}
    evidence = projection.get("evidence") if isinstance(projection.get("evidence"), Mapping) else {}
    continuity = projection.get("continuity") if isinstance(projection.get("continuity"), Mapping) else {}
    diagnostics = projection.get("diagnostics") if isinstance(projection.get("diagnostics"), Mapping) else {}
    return {
        "follow_through_posture": str(policy.get("follow_through_posture") or ""),
        "follow_through_available": bool(continuity.get("follow_through_available")),
        "continuity_disposition": str(continuity.get("continuity_disposition") or ""),
        "milestone_count": int(continuity.get("milestone_count") or 0),
        "dependency_count": int(continuity.get("dependency_count") or 0),
        "stopping_condition_count": int(continuity.get("stopping_condition_count") or 0),
        "verified_receipt_count": int(evidence.get("verified_receipt_count") or 0),
        "replayed_receipt_count": int(evidence.get("replayed_receipt_count") or 0),
        "receipt_budget_exceeded": bool(evidence.get("receipt_budget_exceeded")),
        "policy_recovered": bool(policy.get("policy_recovered")),
        "diagnostics_valid": verify_persistent_follow_through_diagnostics_strict(diagnostics),
        "authority": str(policy.get("authority") or ""),
        "content_free": bool(policy.get("content_free")),
    }


def build_persistent_follow_through_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    runtime = Path(runtime_root or source / "data").resolve()
    source_before = _tree_signature(source)
    runtime_before = _tree_signature(runtime)
    checks: list[bool] = []

    def require(value: object) -> None:
        checks.append(bool(value))

    simulation, review, reliability = _simulation_inputs()
    no_follow_through = build_persistent_follow_through_projection({}, {}, {})
    emerging = _projection()
    completed_handoff = build_persistent_follow_through_handoff(
        emerging, provider_completed=True, assistant_memory_committed=True,
    )
    prior_row = {"persistent_follow_through_handoff": completed_handoff}
    stable = _projection(prior=[prior_row])
    replay = _projection(prior=[prior_row, prior_row, prior_row])
    tampered_handoff = deepcopy(completed_handoff)
    tampered_handoff["milestone_count"] += 1
    recovered = _projection(prior=[{"persistent_follow_through_handoff": tampered_handoff}])
    flood_rows = [
        {"persistent_follow_through_handoff": {"receipt_digest": str(index)}}
        for index in range(MAX_PRIOR_RECEIPTS + 1)
    ]
    flooded = _projection(prior=flood_rows)
    missing_constraints = _projection(constraints=("literal_current_request_precedence",))

    raw_projection_cases = {
        "no_follow_through": no_follow_through,
        "emerging": emerging,
        "stable": stable,
        "replay": replay,
        "tampered_recovery": recovered,
        "receipt_flood": flooded,
        "missing_constraints": missing_constraints,
    }
    projection_summaries = {name: _case_summary(value) for name, value in raw_projection_cases.items()}
    for row in projection_summaries.values():
        require(row["authority"] in {"none", ""})
        require(row["content_free"] or not row["follow_through_available"])
        require(row["milestone_count"] <= 64)
        require(row["dependency_count"] <= 64)
        require(row["stopping_condition_count"] <= 64)
    require(not projection_summaries["no_follow_through"]["follow_through_available"])
    require(projection_summaries["emerging"]["follow_through_available"])
    require(projection_summaries["emerging"]["milestone_count"] == 3)
    require(projection_summaries["emerging"]["dependency_count"] == 3)
    require(projection_summaries["emerging"]["stopping_condition_count"] == 4)
    require(projection_summaries["stable"]["continuity_disposition"] == "verified_resume_review")
    require(projection_summaries["stable"]["verified_receipt_count"] == 1)
    require(projection_summaries["replay"]["verified_receipt_count"] == 1)
    require(projection_summaries["replay"]["replayed_receipt_count"] == 2)
    require(projection_summaries["tampered_recovery"]["policy_recovered"])
    require(not projection_summaries["tampered_recovery"]["follow_through_available"])
    require(projection_summaries["receipt_flood"]["receipt_budget_exceeded"])
    require(not projection_summaries["receipt_flood"]["follow_through_available"])
    require(projection_summaries["missing_constraints"]["policy_recovered"])

    raw_reviews = {
        name: build_persistent_follow_through_review_projection(value)
        for name, value in {
            "emerging": emerging,
            "stable": stable,
            "replay": replay,
            "recovered": recovered,
            "none": no_follow_through,
        }.items()
    }
    review_summaries: dict[str, dict[str, Any]] = {}
    for name, value in raw_reviews.items():
        state = value["state"]
        packet = value["review_packet"]
        state_valid = verify_persistent_follow_through_review_state(state)
        packet_valid = verify_persistent_follow_through_review_packet(packet)
        review_summaries[name] = {
            "state_valid": state_valid,
            "packet_valid": packet_valid,
            "review_disposition": str(state.get("review_disposition") or ""),
            "follow_through_available": bool(packet.get("follow_through_available")),
            "milestone_count": len(packet.get("milestone_categories") or []),
            "dependency_count": len(packet.get("dependency_categories") or []),
            "stopping_condition_count": len(packet.get("stopping_condition_categories") or []),
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
            "plan_activated", "plan_persisted", "schedule_created", "tool_routed",
            "action_executed", "source_edited", "autonomous_work_started",
        )))
    require(review_summaries["emerging"]["review_disposition"] == "emerging_follow_through_review")
    require(review_summaries["stable"]["review_disposition"] == "stable_follow_through_review")
    require(review_summaries["stable"]["verified_prior_receipt_count"] == 1)
    require(review_summaries["replay"]["verified_prior_receipt_count"] == 1)
    require(review_summaries["replay"]["replayed_prior_receipt_count"] == 2)
    require(not review_summaries["recovered"]["follow_through_available"])
    require(not review_summaries["none"]["follow_through_available"])

    handoffs = {
        "before_provider": build_persistent_follow_through_handoff(
            emerging, provider_completed=False, assistant_memory_committed=False,
        ),
        "before_memory": build_persistent_follow_through_handoff(
            emerging, provider_completed=True, assistant_memory_committed=False,
        ),
        "completed": completed_handoff,
    }
    handoff_summaries: dict[str, dict[str, Any]] = {}
    for name, row in handoffs.items():
        valid = verify_persistent_follow_through_handoff(row)
        handoff_summaries[name] = {
            "valid": valid,
            "eligible": bool(row.get("eligible_for_continuity")),
            "milestone_count": int(row.get("milestone_count") or 0),
            "dependency_count": int(row.get("dependency_count") or 0),
            "stopping_condition_count": int(row.get("stopping_condition_count") or 0),
        }
        require(valid)
        require(row.get("plan_activated") is False)
        require(row.get("plan_persisted") is False)
        require(row.get("schedule_created") is False)
        require(row.get("tool_routed") is False)
        require(row.get("action_executed") is False)
        require(row.get("authority") == "none")
    require(not handoff_summaries["before_provider"]["eligible"])
    require(not handoff_summaries["before_memory"]["eligible"])
    require(handoff_summaries["completed"]["eligible"])

    reliabilities = {
        "reliable": build_persistent_follow_through_reliability(emerging, raw_reviews["emerging"]),
        "replayed": build_persistent_follow_through_reliability(
            replay, raw_reviews["replay"], prior_follow_through_receipts=[prior_row, prior_row, prior_row],
        ),
        "tampered": build_persistent_follow_through_reliability(recovered, raw_reviews["recovered"]),
        "flood": build_persistent_follow_through_reliability(
            flooded, build_persistent_follow_through_review_projection(flooded),
            prior_follow_through_receipts=flood_rows,
        ),
    }
    reliability_summaries: dict[str, dict[str, Any]] = {}
    for name, value in reliabilities.items():
        report = value["report"]
        valid = verify_persistent_follow_through_reliability(report)
        reliability_summaries[name] = {
            "valid": valid,
            "ready": bool(report.get("ordinary_conversation_ready")),
            "fault_count": int(report.get("fault_count") or 0),
            "receipt_budget_exceeded": bool(report.get("receipt_budget_exceeded")),
            "follow_through_available": bool(report.get("follow_through_available")),
            "review_available": bool(report.get("review_available")),
            "verified_prior_receipt_count": int(report.get("verified_prior_receipt_count") or 0),
            "replayed_prior_receipt_count": int(report.get("replayed_prior_receipt_count") or 0),
        }
        require(valid)
        require(report.get("authority") == "none")
        require(report.get("content_free") is True)
        require(int(report.get("fault_count") or 0) <= MAX_RELIABILITY_FAULTS)
        require(report.get("plan_activated") is False)
        require(report.get("plan_persisted") is False)
        require(report.get("action_executed") is False)
    require(reliability_summaries["reliable"]["ready"])
    require(reliability_summaries["reliable"]["follow_through_available"])
    require(reliability_summaries["replayed"]["ready"])
    require(reliability_summaries["replayed"]["verified_prior_receipt_count"] == 1)
    require(reliability_summaries["replayed"]["replayed_prior_receipt_count"] == 2)
    require(not reliability_summaries["tampered"]["ready"])
    require(not reliability_summaries["tampered"]["review_available"])
    require(reliability_summaries["flood"]["receipt_budget_exceeded"])
    require(not reliability_summaries["flood"]["follow_through_available"])

    receipt_summary = validate_prior_follow_through_receipts([prior_row, prior_row])
    require(receipt_summary["verified_receipt_count"] == 1)
    require(receipt_summary["replayed_receipt_count"] == 1)
    require(receipt_summary["continuity_available"] is True)
    require(verify_persistent_follow_through_handoff(completed_handoff))
    require(not verify_persistent_follow_through_handoff(tampered_handoff))

    forged_packet = deepcopy(raw_reviews["emerging"]["review_packet"])
    forged_packet["approved"] = True
    forged_packet.pop("review_packet_digest", None)
    forged_packet["review_packet_digest"] = _digest(forged_packet)
    require(not verify_persistent_follow_through_review_packet(forged_packet))
    forged_diagnostics = deepcopy(emerging["diagnostics"])
    forged_diagnostics["approved"] = True
    require(not verify_persistent_follow_through_diagnostics_strict(forged_diagnostics))
    forged_reliability = deepcopy(reliabilities["reliable"]["report"])
    forged_reliability["plan_activated"] = True
    forged_reliability.pop("reliability_digest", None)
    forged_reliability["reliability_digest"] = _digest(forged_reliability)
    require(not verify_persistent_follow_through_reliability(forged_reliability))

    registry = inspect_checkpoint_registry(source_root=source)
    checkpoint_row = next(
        (row for row in registry.get("checkpoints", []) if row.get("checkpoint_id") == "persistent-follow-through-checkpoint"),
        None,
    )
    privacy = package_privacy_summary_for_root(source)
    require(checkpoint_row is not None)
    require((checkpoint_row or {}).get("builder") == "build_persistent_follow_through_checkpoint")
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
        "persistent_follow_through_checkpoint_completed": True,
        "follow_through_review_continuity_and_reliability_consolidated": True,
        "historical_v1134_planning_governance_preserved": True,
        "plan_simulation_boundary_preserved": True,
        "literal_current_request_precedence_preserved": True,
        "goal_and_planning_alpha_not_started": True,
        "plan_activation_not_started": True,
        "plan_persistence_not_started": True,
        "plan_execution_not_started": True,
        "tool_routing_not_started": True,
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
        "follow_through_contract_version": FOLLOW_THROUGH_CONTRACT_VERSION,
        "review_contract_version": REVIEW_CONTRACT_VERSION,
        "reliability_contract_version": RELIABILITY_CONTRACT_VERSION,
    }
    report["structural_digest"] = _digest(report)
    return report
