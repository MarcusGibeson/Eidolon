from __future__ import annotations

"""Strictly read-only v1172.9 Plan Simulation checkpoint."""

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from checkpoint_registry import inspect_checkpoint_registry
from package_integrity import package_privacy_summary_for_root
from plan_simulation_runtime import CONTRACT_VERSION as SIMULATION_CONTRACT_VERSION, REVIEW_CONTRACT_VERSION, RELIABILITY_CONTRACT_VERSION, MAX_ALTERNATIVES, MAX_COMPONENT_BYTES, MAX_PRIOR_RECEIPTS, MAX_RELIABILITY_FAULTS, MAX_REVIEW_PROMPT_CHARS, build_plan_simulation_projection, build_plan_simulation_review_handoff, build_plan_simulation_review_projection, build_plan_simulation_reliability, validate_prior_plan_simulation_receipts, verify_plan_simulation_diagnostics_strict, verify_plan_simulation_reliability, verify_plan_simulation_review_handoff, verify_plan_simulation_review_packet, verify_plan_simulation_review_state

CONTRACT_VERSION = "v1172.9"
_CHECKPOINT_ID = "plan-simulation:v1172.9"
_EXCLUDED = {
    "data", ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "dist", "build", "reports",
}
_FORBIDDEN = (
    "SIMULATION_PRIVATE_CANARY", "PLAN_PRIVATE_CANARY", "GOAL_PRIVATE_CANARY",
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


def _planning_inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    return (
        {
            "hierarchy": {
                "plan_candidate_available": True,
                "milestone_count": 3,
                "dependency_count": 2,
                "stopping_condition_count": 3,
            },
            "policy": {
                "operator_review_required": True,
                "plan_activation_permitted": False,
                "action_execution_permitted": False,
            },
        },
        {
            "reliability_posture": "hierarchical_planning_context_reliable",
            "ordinary_conversation_ready": True,
            "plan_candidate_available": True,
        },
    )


def _projection(*, prior: object = (), constraints: object = None) -> dict[str, Any]:
    planning, reliability = _planning_inputs()
    kwargs: dict[str, Any] = {"prior_simulation_receipts": prior}
    if constraints is not None:
        kwargs["protected_operator_constraints"] = constraints
    return build_plan_simulation_projection(planning, reliability, **kwargs)


def _case_summary(projection: Mapping[str, Any]) -> dict[str, Any]:
    policy = projection.get("policy") if isinstance(projection.get("policy"), Mapping) else {}
    comparison = projection.get("comparison") if isinstance(projection.get("comparison"), Mapping) else {}
    diagnostics = projection.get("diagnostics") if isinstance(projection.get("diagnostics"), Mapping) else {}
    return {
        "simulation_posture": str(policy.get("simulation_posture") or ""),
        "simulation_available": bool(diagnostics.get("simulation_available")),
        "alternative_count": int(comparison.get("alternative_count") or 0),
        "risk_count": int(comparison.get("risk_category_count") or 0),
        "alternative_classes": [
            str(row.get("alternative_class") or "none")
            for row in list(comparison.get("alternatives") or [])
            if isinstance(row, Mapping)
        ],
        "risk_categories": [str(item) for item in list(comparison.get("risk_categories") or [])],
        "preferred_alternative_selected": bool(comparison.get("preferred_alternative_selected")),
        "policy_recovered": bool(policy.get("policy_recovered")),
        "diagnostics_valid": verify_plan_simulation_diagnostics_strict(diagnostics),
        "authority": str(policy.get("authority") or ""),
        "content_free": bool(policy.get("content_free")),
    }


def build_plan_simulation_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    runtime = Path(runtime_root or source / "data").resolve()
    source_before = _tree_signature(source)
    runtime_before = _tree_signature(runtime)
    checks: list[bool] = []

    def require(value: object) -> None:
        checks.append(bool(value))

    no_simulation = build_plan_simulation_projection({}, {})
    emerging = _projection()
    completed_handoff = build_plan_simulation_review_handoff(
        emerging, provider_completed=True, assistant_memory_committed=True,
    )
    prior_row = {"plan_simulation_review_handoff": completed_handoff}
    stable = _projection(prior=[prior_row])
    replay = _projection(prior=[prior_row, prior_row, prior_row])
    tampered_handoff = deepcopy(completed_handoff)
    tampered_handoff["alternative_count"] += 1
    recovered = _projection(prior=[{"plan_simulation_review_handoff": tampered_handoff}])
    flood_rows = [
        {"plan_simulation_review_handoff": {"receipt_digest": str(index)}}
        for index in range(MAX_PRIOR_RECEIPTS + 1)
    ]
    flooded = _projection(prior=flood_rows)
    missing_constraints = _projection(constraints=("literal_current_request_precedence",))

    raw_projection_cases = {
        "no_simulation": no_simulation,
        "emerging": emerging,
        "stable": stable,
        "replay": replay,
        "tampered_recovery": recovered,
        "receipt_flood": flooded,
        "missing_constraints": missing_constraints,
    }
    projection_summaries = {
        name: _case_summary(value) for name, value in raw_projection_cases.items()
    }
    for row in projection_summaries.values():
        require(row["authority"] in {"none", ""})
        require(row["content_free"] or not row["simulation_available"])
        require(row["alternative_count"] <= MAX_ALTERNATIVES)
        require(row["risk_count"] <= 64)
        require(row["preferred_alternative_selected"] is False)
    require(not projection_summaries["no_simulation"]["simulation_available"])
    require(projection_summaries["emerging"]["simulation_available"])
    require(projection_summaries["emerging"]["alternative_count"] == 3)
    require(projection_summaries["emerging"]["risk_count"] == 3)
    require(projection_summaries["stable"]["simulation_available"])
    require(projection_summaries["tampered_recovery"]["policy_recovered"])
    require(not projection_summaries["tampered_recovery"]["simulation_available"])
    require(projection_summaries["receipt_flood"]["policy_recovered"])
    require(not projection_summaries["receipt_flood"]["simulation_available"])
    require(projection_summaries["missing_constraints"]["policy_recovered"])

    raw_reviews = {
        name: build_plan_simulation_review_projection(value)
        for name, value in {
            "emerging": emerging,
            "stable": stable,
            "replay": replay,
            "recovered": recovered,
            "none": no_simulation,
        }.items()
    }
    review_summaries: dict[str, dict[str, Any]] = {}
    for name, value in raw_reviews.items():
        state = value["state"]
        packet = value["review_packet"]
        state_valid = verify_plan_simulation_review_state(state)
        packet_valid = verify_plan_simulation_review_packet(packet)
        review_summaries[name] = {
            "state_valid": state_valid,
            "packet_valid": packet_valid,
            "review_disposition": str(state.get("review_disposition") or ""),
            "simulation_available": bool(packet.get("simulation_available")),
            "alternative_classes": list(packet.get("alternative_classes") or []),
            "risk_categories": list(packet.get("risk_categories") or []),
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
            "alternative_selected", "plan_activated", "plan_persisted", "schedule_created",
            "tool_routed", "action_executed", "source_edited", "autonomous_work_started",
        )))
    require(review_summaries["emerging"]["review_disposition"] == "emerging_simulation_review")
    require(review_summaries["stable"]["review_disposition"] == "stable_simulation_review")
    require(review_summaries["stable"]["verified_prior_receipt_count"] == 1)
    require(review_summaries["replay"]["verified_prior_receipt_count"] == 1)
    require(review_summaries["replay"]["replayed_prior_receipt_count"] == 2)
    require(not review_summaries["recovered"]["simulation_available"])
    require(not review_summaries["none"]["simulation_available"])

    handoffs = {
        "before_provider": build_plan_simulation_review_handoff(
            emerging, provider_completed=False, assistant_memory_committed=False,
        ),
        "before_memory": build_plan_simulation_review_handoff(
            emerging, provider_completed=True, assistant_memory_committed=False,
        ),
        "completed": completed_handoff,
    }
    handoff_summaries: dict[str, dict[str, Any]] = {}
    for name, row in handoffs.items():
        valid = verify_plan_simulation_review_handoff(row)
        handoff_summaries[name] = {
            "valid": valid,
            "eligible": bool(row.get("eligible_for_review_continuity")),
            "alternative_count": int(row.get("alternative_count") or 0),
            "risk_count": int(row.get("risk_count") or 0),
        }
        require(valid)
        require(row.get("alternative_selected") is False)
        require(row.get("plan_activated") is False)
        require(row.get("action_executed") is False)
        require(row.get("authority") == "none")
    require(not handoff_summaries["before_provider"]["eligible"])
    require(not handoff_summaries["before_memory"]["eligible"])
    require(handoff_summaries["completed"]["eligible"])

    reliabilities = {
        "reliable": build_plan_simulation_reliability(emerging, raw_reviews["emerging"]),
        "replayed": build_plan_simulation_reliability(
            replay, raw_reviews["replay"], prior_simulation_receipts=[prior_row, prior_row, prior_row],
        ),
        "tampered": build_plan_simulation_reliability(recovered, raw_reviews["recovered"]),
        "flood": build_plan_simulation_reliability(
            flooded, build_plan_simulation_review_projection(flooded), prior_simulation_receipts=flood_rows,
        ),
    }
    reliability_summaries: dict[str, dict[str, Any]] = {}
    for name, value in reliabilities.items():
        report = value["report"]
        valid = verify_plan_simulation_reliability(report)
        reliability_summaries[name] = {
            "valid": valid,
            "ready": bool(report.get("ordinary_conversation_ready")),
            "fault_count": int(report.get("fault_count") or 0),
            "receipt_budget_exceeded": bool(report.get("receipt_budget_exceeded")),
            "simulation_available": bool(report.get("simulation_available")),
            "review_available": bool(report.get("review_available")),
            "verified_prior_receipt_count": int(report.get("verified_prior_receipt_count") or 0),
            "replayed_prior_receipt_count": int(report.get("replayed_prior_receipt_count") or 0),
        }
        require(valid)
        require(report.get("authority") == "none")
        require(report.get("content_free") is True)
        require(int(report.get("fault_count") or 0) <= MAX_RELIABILITY_FAULTS)
        require(report.get("alternative_selected") is False)
        require(report.get("plan_activated") is False)
        require(report.get("action_executed") is False)
    require(reliability_summaries["reliable"]["ready"])
    require(reliability_summaries["reliable"]["simulation_available"])
    require(reliability_summaries["replayed"]["ready"])
    require(reliability_summaries["replayed"]["verified_prior_receipt_count"] == 1)
    require(reliability_summaries["replayed"]["replayed_prior_receipt_count"] == 2)
    require(not reliability_summaries["tampered"]["ready"])
    require(not reliability_summaries["tampered"]["review_available"])
    require(reliability_summaries["flood"]["receipt_budget_exceeded"])
    require(not reliability_summaries["flood"]["simulation_available"])

    receipt_summary = validate_prior_plan_simulation_receipts([prior_row, prior_row])
    require(receipt_summary["verified_receipt_count"] == 1)
    require(receipt_summary["replayed_receipt_count"] == 1)
    require(receipt_summary["continuity_available"] is True)
    require(verify_plan_simulation_review_handoff(completed_handoff))
    require(not verify_plan_simulation_review_handoff(tampered_handoff))

    forged_packet = deepcopy(raw_reviews["emerging"]["review_packet"])
    forged_packet["approved"] = True
    forged_packet.pop("review_packet_digest", None)
    forged_packet["review_packet_digest"] = _digest(forged_packet)
    require(not verify_plan_simulation_review_packet(forged_packet))
    forged_diagnostics = deepcopy(emerging["diagnostics"])
    forged_diagnostics["approved"] = True
    require(not verify_plan_simulation_diagnostics_strict(forged_diagnostics))
    forged_reliability = deepcopy(reliabilities["reliable"]["report"])
    forged_reliability["alternative_selected"] = True
    forged_reliability.pop("reliability_digest", None)
    forged_reliability["reliability_digest"] = _digest(forged_reliability)
    require(not verify_plan_simulation_reliability(forged_reliability))

    registry = inspect_checkpoint_registry(source_root=source)
    checkpoint_row = next(
        (row for row in registry.get("checkpoints", []) if row.get("checkpoint_id") == "plan-simulation-checkpoint"),
        None,
    )
    privacy = package_privacy_summary_for_root(source)
    require(checkpoint_row is not None)
    require((checkpoint_row or {}).get("builder") == "build_plan_simulation_checkpoint")
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
        "plan_simulation_checkpoint_completed": True,
        "simulation_review_continuity_and_reliability_consolidated": True,
        "historical_v1134_planning_governance_preserved": True,
        "hierarchical_planning_boundary_preserved": True,
        "literal_current_request_precedence_preserved": True,
        "alternative_selection_not_started": True,
        "plan_activation_not_started": True,
        "plan_persistence_not_started": True,
        "plan_execution_not_started": True,
        "persistent_follow_through_not_started": True,
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
            "alternative_maximum_count": MAX_ALTERNATIVES,
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
        "simulation_contract_version": SIMULATION_CONTRACT_VERSION,
        "review_contract_version": REVIEW_CONTRACT_VERSION,
        "reliability_contract_version": RELIABILITY_CONTRACT_VERSION,
    }
    report["structural_digest"] = _digest(report)
    return report
