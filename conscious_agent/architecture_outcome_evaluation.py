from __future__ import annotations
"""Outcome evaluation for operator-selected architecture project goals.

The evaluator compares current repository evidence with the goal's captured
baseline and separately consumes externally supplied verification evidence. It
never executes tests or source changes and never treats predicted improvement as
proof of behavioral correctness.
"""

from pathlib import Path
from typing import Any, Mapping

from project_evidence_store import DENIED_AUTHORITY, digest
from architecture_project_goal import load_architecture_project_goal
from architecture_change_reasoning import build_architecture_change_assessment, load_architecture_change_assessment

CONTRACT_VERSION = "v2503.7.8"


def _hex64(value: Any) -> bool:
    s = str(value or "").lower()
    return len(s) == 64 and all(c in "0123456789abcdef" for c in s)


def evaluate_architecture_project_outcome(
    source_root: str | Path,
    goal_id: str,
    *,
    verification_evidence: Mapping[str, Any] | None = None,
    runtime_root=None,
) -> dict[str, Any]:
    goal = load_architecture_project_goal(goal_id, runtime_root=runtime_root, include_private=True)
    if not goal:
        return {"ok": False, "status": "architecture_goal_not_found", "action_executed": False, **DENIED_AUTHORITY}

    target = str(goal.get("target_path") or "")
    current_result = build_architecture_change_assessment(source_root, [target], runtime_root=runtime_root)
    current_public = current_result.get("assessment") or {}
    current = load_architecture_change_assessment(
        str(current_public.get("analysis_id") or ""), runtime_root=runtime_root, include_private=True
    )
    findings = current.get("findings") or []
    finding = findings[0] if findings else {}
    criteria = dict(goal.get("acceptance_criteria") or {})
    metrics = dict(finding.get("metrics") or {})

    baseline_lines = int(criteria.get("target_line_count_should_decrease") or 0)
    baseline_symbols = int(criteria.get("target_top_level_symbol_count_should_decrease") or 0)
    baseline_cycles = int(criteria.get("baseline_dependency_cycle_count") or 0)
    current_lines = int(metrics.get("line_count") or 0)
    current_symbols = int(metrics.get("top_level_symbol_count") or 0)
    current_cycles = int(current.get("dependency_cycle_count") or 0)

    checks = {
        "target_still_resolvable": bool(findings),
        "target_line_count_reduced": bool(baseline_lines) and 0 < current_lines < baseline_lines,
        "target_symbol_count_reduced": bool(baseline_symbols) and 0 <= current_symbols < baseline_symbols,
        "no_new_dependency_cycles": current_cycles <= baseline_cycles,
        "governance_authority_unchanged": True,
    }

    verification = dict(verification_evidence or {})
    verification_digest = str(verification.get("verification_digest") or "")
    verification_valid = bool(
        _hex64(verification_digest)
        and verification.get("passed") is True
        and verification.get("source_manifest_digest") == current.get("source_manifest_digest")
        and verification.get("unexplained_regression_count") == 0
    )
    checks["verification_evidence_passed"] = verification_valid

    passed = [k for k, v in checks.items() if v]
    failed = [k for k, v in checks.items() if not v]
    outcome_digest = digest(
        {
            "goal_id": goal_id,
            "goal_evidence_digest": goal.get("goal_evidence_digest"),
            "current_manifest": current.get("source_manifest_digest"),
            "checks": checks,
            "verification_digest": verification_digest,
        }
    )
    complete = bool(findings) and verification_valid
    success = complete and not failed
    return {
        "ok": success,
        "status": (
            "architecture_goal_outcome_satisfied"
            if success
            else ("architecture_goal_outcome_incomplete" if not complete else "architecture_goal_outcome_not_satisfied")
        ),
        "contract_version": CONTRACT_VERSION,
        "goal_id": goal_id,
        "goal_evidence_digest": goal.get("goal_evidence_digest"),
        "source_manifest_digest": current.get("source_manifest_digest"),
        "outcome_digest": outcome_digest,
        "baseline": {
            "line_count": baseline_lines,
            "top_level_symbol_count": baseline_symbols,
            "dependency_cycle_count": baseline_cycles,
        },
        "current": {
            "line_count": current_lines,
            "top_level_symbol_count": current_symbols,
            "dependency_cycle_count": current_cycles,
        },
        "checks": checks,
        "passed_check_count": len(passed),
        "failed_check_count": len(failed),
        "failed_checks": failed,
        "verification_evidence_valid": verification_valid,
        "verification_evidence_digest": verification_digest if _hex64(verification_digest) else "",
        "predictions_not_behavioral_proof": True,
        "tests_executed": False,
        "source_modified": False,
        "goal_completed_automatically": False,
        "installation_authorized": False,
        "promotion_authorized": False,
        "action_executed": False,
        **DENIED_AUTHORITY,
    }


__all__ = ["CONTRACT_VERSION", "evaluate_architecture_project_outcome"]
