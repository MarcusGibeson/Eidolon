from __future__ import annotations

"""Gold-blind router simulation for Corpus B.

The router sees only a whitelisted runtime view of each model output, the model-facing
fixture, and the frozen qualification table. It never imports a gold loader, never
receives a semantic label, and never sends work to a tier the table has not qualified.
"""

from typing import Any, Callable, Mapping, Sequence

from g_route3_triggers import TRIGGERS, triggers_for as _payload_triggers

CONTRACT_VERSION = "g-route3.routing.v1"
TIER_ORDER = ("small", "mid", "large")
STOPPED, NO_QUALIFIED_MODEL, EVIDENCE_ONLY, ESCALATION_EXHAUSTED = (
    "stopped", "no_qualified_model", "evidence_only", "escalation_exhausted")
OUTCOMES = (STOPPED, NO_QUALIFIED_MODEL, EVIDENCE_ONLY, ESCALATION_EXHAUSTED)
RUNTIME_VIEW_KEYS = frozenset({
    "fixture_id", "task_class", "risk_class", "model_tier", "normalization",
    "normalized_operational_validation", "infrastructure_failure", "coding_execution_evidence",
})
FORBIDDEN_VIEW_KEYS = frozenset({"semantics", "gold", "expected", "gold_linkage", "reference_output"})


def runtime_view(record: Mapping[str, Any]) -> dict[str, Any]:
    """Project a persisted record onto what a live router could legitimately know."""
    view = {key: record[key] for key in RUNTIME_VIEW_KEYS if key in record}
    normalization = dict(view.get("normalization") or {})
    view["normalization"] = {key: normalization.get(key) for key in ("outcome", "normalized", "payload")}
    return view


def assert_gold_blind(view: Mapping[str, Any]) -> None:
    leaked = FORBIDDEN_VIEW_KEYS & set(view)
    if leaked or set(view) - RUNTIME_VIEW_KEYS:
        raise ValueError("gold_leakage_into_routing:" + ",".join(sorted(leaked | (set(view) - RUNTIME_VIEW_KEYS))))


def qualified_tiers(table: Mapping[str, Any], task_class: str, risk_class: str) -> list[str]:
    tiers = list((table.get("routing_lookup") or {}).get(f"{task_class}|{risk_class}", []))
    return [tier for tier in TIER_ORDER if tier in tiers]


def triggers_for(fixture: Mapping[str, Any], view: Mapping[str, Any]) -> list[str]:
    return _payload_triggers(fixture, (view.get("normalization") or {}).get("payload"))


def verdicts(fixture: Mapping[str, Any], view: Mapping[str, Any], table: Mapping[str, Any]) -> dict[str, Any]:
    """The three separate verdicts for one tier's output. They are never merged."""
    assert_gold_blind(view)
    tier = str(view["model_tier"])
    accepted = bool((view.get("normalized_operational_validation") or {}).get("accepted")) \
        and not view.get("infrastructure_failure")
    qualified = tier in qualified_tiers(table, str(fixture["task_class"]), str(fixture["consequence_risk"]))
    fired = triggers_for(fixture, view) if accepted else []
    evidence_only = str(fixture["consequence_risk"]) == "R4"
    return {
        "model_tier": tier,
        "output_accepted": accepted,
        "model_cell_qualified": qualified,
        "triggers": fired,
        "safe_to_stop_escalation": bool(accepted and qualified and not fired and not evidence_only),
    }


def route(fixture: Mapping[str, Any], table: Mapping[str, Any],
          observe: Callable[[str], Mapping[str, Any] | None]) -> dict[str, Any]:
    """Route one validation case. `observe(tier)` is only ever called for qualified tiers."""
    task, risk = str(fixture["task_class"]), str(fixture["consequence_risk"])
    tiers = qualified_tiers(table, task, risk)
    base = {"fixture_id": fixture["fixture_id"], "task_class": task, "risk_class": risk,
            "qualified_tiers": tiers, "start_tier": tiers[0] if tiers and risk != "R4" else None,
            "uses_gold": False, "production_routing_invoked": False}
    if risk == "R4":
        return {**base, "outcome": EVIDENCE_ONLY, "final_tier": None, "attempts": [], "tiers_contacted": []}
    if not tiers:
        return {**base, "outcome": NO_QUALIFIED_MODEL, "final_tier": None, "attempts": [], "tiers_contacted": []}
    attempts = []
    for index, tier in enumerate(tiers):
        view = observe(tier)
        if view is None:
            attempts.append({"model_tier": tier, "available": False, "output_accepted": False,
                             "model_cell_qualified": True, "triggers": [], "safe_to_stop_escalation": False,
                             "next_tier": tiers[index + 1] if index + 1 < len(tiers) else None})
            continue
        view = runtime_view(view)
        verdict = verdicts(fixture, view, table)
        verdict["available"] = True
        verdict["next_tier"] = None if verdict["safe_to_stop_escalation"] else (
            tiers[index + 1] if index + 1 < len(tiers) else None)
        attempts.append(verdict)
        if verdict["safe_to_stop_escalation"]:
            return {**base, "outcome": STOPPED, "final_tier": tier, "attempts": attempts,
                    "tiers_contacted": [a["model_tier"] for a in attempts],
                    "escalated": index > 0}
    return {**base, "outcome": ESCALATION_EXHAUSTED, "final_tier": None, "attempts": attempts,
            "tiers_contacted": [a["model_tier"] for a in attempts], "escalated": len(attempts) > 1}


__all__ = ["CONTRACT_VERSION", "TIER_ORDER", "OUTCOMES", "TRIGGERS", "STOPPED", "NO_QUALIFIED_MODEL",
           "EVIDENCE_ONLY", "ESCALATION_EXHAUSTED", "RUNTIME_VIEW_KEYS", "FORBIDDEN_VIEW_KEYS",
           "runtime_view", "assert_gold_blind", "qualified_tiers", "triggers_for", "verdicts", "route"]
