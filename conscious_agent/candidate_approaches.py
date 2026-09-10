from __future__ import annotations
"""v1321 candidate-approach generation for bounded deliberative planning.

The planner receives an already content-minimized goal contract and current
project-understanding evidence.  It creates more than one viable approach only
when a real tradeoff is present.  Reversible routine decisions collapse to one
bounded default rather than manufacturing ceremony.  This module is advisory:
it does not select tools, execute tests, mutate projects, consume approvals, or
grant authority.
"""
from pathlib import Path
from typing import Any, Iterable, Mapping

from cognitive_coding_foundations import DENIED_AUTHORITY, digest
from goal_representation import validate_goal
from project_evidence_store import atomic_json, evidence_root, read_json, seal, valid

CONTRACT_VERSION = "v1321.8"
MAX_APPROACHES = 5
RISK_LEVELS = ("low", "medium", "high", "protected")

PLANNING_DENIED_AUTHORITY = {
    **DENIED_AUTHORITY,
    "approach_selection_authorized": False,
    "planning_execution_authorized": False,
    "approval_consumed": False,
    "independent_authority_granted": False,
}


def _record_path(approach_set_id: str, runtime_root=None) -> Path:
    return evidence_root("candidate_approaches", runtime_root) / "records" / f"{approach_set_id}.json"


def _norm_context(raw: Mapping[str, Any] | None) -> dict[str, Any]:
    value = dict(raw or {})
    risk = str(value.get("risk_level") or "low").strip().lower()
    if risk not in RISK_LEVELS:
        risk = "medium"
    reversible = bool(value.get("reversible", True))
    consequential = bool(value.get("consequential", False))
    blast_radius = max(0, min(100, int(value.get("blast_radius", 10))))
    return {
        "risk_level": risk,
        "reversible": reversible,
        "consequential": consequential,
        "blast_radius": blast_radius,
        "compatibility_sensitive": bool(value.get("compatibility_sensitive", False)),
        "performance_sensitive": bool(value.get("performance_sensitive", False)),
        "privacy_sensitive": bool(value.get("privacy_sensitive", False)),
        "tradeoffs_matter_hint": bool(value.get("tradeoffs_matter", False)),
    }


def _tradeoffs_matter(context: Mapping[str, Any], explicit_count: int) -> bool:
    return bool(
        explicit_count >= 2
        or context.get("tradeoffs_matter_hint")
        or context.get("consequential")
        or not context.get("reversible")
        or context.get("risk_level") in {"high", "protected"}
        or int(context.get("blast_radius") or 0) >= 35
        or context.get("compatibility_sensitive")
        or context.get("performance_sensitive")
        or context.get("privacy_sensitive")
    )


def _approach(code: str, *, strategy: str, context: Mapping[str, Any], source: str, notes: Iterable[str] = ()) -> dict[str, Any]:
    code = str(code or "").strip().lower().replace(" ", "_")[:80]
    if not code:
        raise ValueError("approach_code_required")
    note_digests = sorted({digest(str(x)) for x in notes if str(x).strip()})[:16]
    row = {
        "approach_code": code,
        "strategy": str(strategy or code)[:80],
        "source": source,
        "risk_level": context["risk_level"],
        "reversible": bool(context["reversible"]),
        "blast_radius": int(context["blast_radius"]),
        "compatibility_sensitive": bool(context["compatibility_sensitive"]),
        "performance_sensitive": bool(context["performance_sensitive"]),
        "privacy_sensitive": bool(context["privacy_sensitive"]),
        "note_digests": note_digests,
        "viable": True,
        "executed": False,
        "content_free": True,
        **PLANNING_DENIED_AUTHORITY,
    }
    row["approach_id"] = "approach_" + digest(row)[:20]
    row["approach_digest"] = digest(row)
    return row


def _explicit_approaches(options: Iterable[Mapping[str, Any]], context: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in list(options)[:MAX_APPROACHES]:
        code = str(raw.get("code") or raw.get("approach_code") or "").strip().lower().replace(" ", "_")[:80]
        if not code or code in seen:
            continue
        seen.add(code)
        if raw.get("viable") is False:
            continue
        rows.append(
            _approach(
                code,
                strategy=str(raw.get("strategy") or code),
                context=context,
                source="explicit_candidate",
                notes=raw.get("notes") or (),
            )
        )
    return rows


def build_candidate_approaches(
    goal: Mapping[str, Any],
    project_understanding: Mapping[str, Any],
    *,
    decision_context: Mapping[str, Any] | None = None,
    explicit_options: Iterable[Mapping[str, Any]] = (),
    runtime_root=None,
) -> dict[str, Any]:
    """Build and persist a content-minimized approach set.

    ``project_understanding`` may be a public v1320 projection; only its digests
    and consistency/freshness signals are retained.  Raw goal text is never
    required because v1303 already represents it as digests.
    """
    if not validate_goal(goal).get("ok"):
        raise ValueError("valid_goal_required")
    manifest = str(project_understanding.get("source_manifest_digest") or "")
    workspace = str(project_understanding.get("workspace_digest") or "")
    if not manifest or not workspace:
        raise ValueError("project_understanding_required")
    if project_understanding.get("manifest_consistent") is False:
        raise ValueError("project_understanding_conflicted")

    context = _norm_context(decision_context)
    supplied = list(explicit_options)[:MAX_APPROACHES]
    tradeoffs = _tradeoffs_matter(context, len(supplied))
    collapsed = not tradeoffs and context["reversible"] and context["risk_level"] == "low"

    candidates = _explicit_approaches(supplied, context)
    if not candidates:
        if collapsed:
            candidates = [
                _approach(
                    "routine_reversible_choice",
                    strategy="smallest_convention_preserving_change",
                    context=context,
                    source="deterministic_routine_default",
                )
            ]
        else:
            candidates = [
                _approach("minimal_targeted_change", strategy="smallest_supported_surface", context=context, source="deterministic_planner"),
                _approach("existing_pattern_extension", strategy="extend_verified_repository_pattern", context=context, source="deterministic_planner"),
                _approach("boundary_refactor", strategy="repair_or_improve_ownership_boundary", context=context, source="deterministic_planner"),
            ]

    if tradeoffs and len(candidates) < 2:
        # An explicitly supplied singleton is not enough to prove that a
        # consequential decision has alternatives. Add a conservative fallback.
        existing = {row["approach_code"] for row in candidates}
        fallback = "minimal_targeted_change" if "minimal_targeted_change" not in existing else "existing_pattern_extension"
        candidates.append(_approach(fallback, strategy="conservative_fallback", context=context, source="deterministic_planner"))

    key_payload = {
        "goal_digest": goal.get("goal_digest"),
        "workspace_digest": workspace,
        "source_manifest_digest": manifest,
        "context": context,
        "candidate_digests": [row["approach_digest"] for row in candidates],
    }
    approach_set_id = "approaches_" + digest(key_payload)[:24]
    selected = candidates[0]["approach_id"] if collapsed and len(candidates) == 1 else ""
    row = seal(
        {
            "contract_version": CONTRACT_VERSION,
            "approach_set_id": approach_set_id,
            "goal_id": goal.get("goal_id"),
            "goal_digest": goal.get("goal_digest"),
            "workspace_digest": workspace,
            "source_manifest_digest": manifest,
            "decision_context_digest": digest(context),
            "tradeoffs_matter": tradeoffs,
            "collapsed_trivial_choice": collapsed,
            "approaches": candidates,
            "approach_count": len(candidates),
            "selected_approach_id": selected,
            "selection_deferred": not bool(selected),
            "raw_goal_content_persisted": False,
            "source_modified": False,
            "tests_executed": False,
            "action_executed": False,
            **PLANNING_DENIED_AUTHORITY,
        }
    )
    atomic_json(_record_path(approach_set_id, runtime_root), row)
    return {
        "ok": True,
        "status": "routine_choice_collapsed" if collapsed else "candidate_approaches_ready",
        "candidate_approaches": public_candidate_approaches(row),
        "action_executed": False,
        **PLANNING_DENIED_AUTHORITY,
    }


def public_candidate_approaches(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "approach_set_id": row.get("approach_set_id"),
        "goal_id": row.get("goal_id"),
        "goal_digest": row.get("goal_digest"),
        "workspace_digest": row.get("workspace_digest"),
        "source_manifest_digest": row.get("source_manifest_digest"),
        "tradeoffs_matter": bool(row.get("tradeoffs_matter")),
        "collapsed_trivial_choice": bool(row.get("collapsed_trivial_choice")),
        "approach_count": int(row.get("approach_count") or 0),
        "approaches": [
            {
                "approach_id": item.get("approach_id"),
                "approach_code": item.get("approach_code"),
                "strategy": item.get("strategy"),
                "risk_level": item.get("risk_level"),
                "reversible": bool(item.get("reversible")),
                "viable": bool(item.get("viable")),
                "executed": False,
            }
            for item in row.get("approaches") or []
        ],
        "selected_approach_id": row.get("selected_approach_id") or "",
        "selection_deferred": bool(row.get("selection_deferred")),
        "raw_goal_content_persisted": False,
        "read_only": True,
        "source_modified": False,
        "tests_executed": False,
        "action_executed": False,
        **PLANNING_DENIED_AUTHORITY,
    }


def load_candidate_approaches(approach_set_id: str, *, runtime_root=None, include_private: bool = False) -> dict[str, Any]:
    row = read_json(_record_path(str(approach_set_id), runtime_root))
    if not row or not valid(row):
        return {}
    return row if include_private else public_candidate_approaches(row)


def assess_candidate_approach_freshness(
    approach_set_id: str,
    project_understanding: Mapping[str, Any],
    *,
    runtime_root=None,
) -> dict[str, Any]:
    row = load_candidate_approaches(approach_set_id, runtime_root=runtime_root, include_private=True)
    if not row:
        return {"ok": False, "status": "missing_or_tampered", "current": False, "action_executed": False, **PLANNING_DENIED_AUTHORITY}
    same = (
        row.get("workspace_digest") == project_understanding.get("workspace_digest")
        and row.get("source_manifest_digest") == project_understanding.get("source_manifest_digest")
        and project_understanding.get("manifest_consistent") is not False
    )
    return {
        "ok": True,
        "status": "current" if same else "stale",
        "current": same,
        "action_executed": False,
        **PLANNING_DENIED_AUTHORITY,
    }


def process_candidate_approaches_control(
    text: str,
    *,
    project_root=None,
    project_understanding: Mapping[str, Any] | None = None,
    goal: Mapping[str, Any] | None = None,
    decision_context: Mapping[str, Any] | None = None,
    runtime_root=None,
) -> dict[str, Any]:
    if str(text or "").strip().lower() not in {"show candidate approaches", "inspect candidate approaches"}:
        return {"active": False}
    if not goal:
        return {"active": True, "ok": False, "status": "planning_goal_required", "action_executed": False, **PLANNING_DENIED_AUTHORITY}
    if project_understanding is None:
        if not project_root:
            return {"active": True, "ok": False, "status": "project_root_required", "action_executed": False, **PLANNING_DENIED_AUTHORITY}
        from project_understanding_checkpoint import build_project_understanding_checkpoint
        project_understanding = build_project_understanding_checkpoint(project_root, runtime_root=runtime_root)["project_understanding"]
    return {
        "active": True,
        **build_candidate_approaches(goal, project_understanding, decision_context=decision_context, runtime_root=runtime_root),
    }


__all__ = [
    "CONTRACT_VERSION",
    "MAX_APPROACHES",
    "PLANNING_DENIED_AUTHORITY",
    "build_candidate_approaches",
    "public_candidate_approaches",
    "load_candidate_approaches",
    "assess_candidate_approach_freshness",
    "process_candidate_approaches_control",
]
