# forked from g_route3_validation
from __future__ import annotations

"""Corpus B validation scoring and generalization analysis.

Gold for Corpus B is loaded here, after collection has finished and after the router has
decided every case from gold-blind views. The router's decisions are made first and are
then judged; nothing flows the other way.
"""

from collections import Counter, defaultdict
from typing import Any, Iterable, Mapping

from g_route4_contract import RISK_CLASSES, TASK_CLASSES, TIER_ORDER, load_thresholds, runtime_fixtures
from g_route4_qualification import attach_semantics, failure_rate_upper_bound
from g_route3_routing import (ESCALATION_EXHAUSTED, EVIDENCE_ONLY, NO_QUALIFIED_MODEL, OUTCOMES, STOPPED,
                              qualified_tiers, route, runtime_view)

CONTRACT_VERSION = "g-route4.validation.v1"


def _ratio(count: int, total: int) -> dict[str, Any]:
    return {"count": count, "of": total, "rate": round(count / total, 6) if total else None}


def decide(records: Iterable[Mapping[str, Any]], table: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Gold-blind routing of every Corpus B case. Consumes no semantic field."""
    by_case: dict[str, dict[str, Mapping[str, Any]]] = defaultdict(dict)
    for row in records:
        by_case[row["fixture_id"]][row["model_tier"]] = row
    fixtures = runtime_fixtures("B")
    decisions = []
    for fixture_id in sorted(fixtures):
        views = {tier: runtime_view(row) for tier, row in by_case.get(fixture_id, {}).items()}
        decisions.append(route(fixtures[fixture_id], table, lambda tier, v=views: v.get(tier)))
    return decisions


def score(records: list[Mapping[str, Any]], table: Mapping[str, Any],
          thresholds: Mapping[str, Any] | None = None) -> dict[str, Any]:
    limits = dict(thresholds or load_thresholds())
    gates = limits["gates"]
    decisions = decide(records, table)                 # routing first, gold-blind
    judged = attach_semantics(records, "B")            # then judgment, evaluator side
    truth = {(r["fixture_id"], r["model_tier"]): r for r in judged}

    def correct(fixture_id: str, tier: str) -> bool:
        return bool(truth[(fixture_id, tier)]["semantics"]["normalized_semantic_evaluation"]["hard_gate_pass"])

    cases = len(decisions)
    eligible = [d for d in decisions if d["risk_class"] != "R4"]
    qualified_start = [d for d in eligible if d["qualified_tiers"]]
    stops = [d for d in decisions if d["outcome"] == STOPPED]
    correct_stops = [d for d in stops if correct(d["fixture_id"], d["final_tier"])]
    unsafe_stops = [d for d in stops if not correct(d["fixture_id"], d["final_tier"])]
    escalated = [d for d in decisions if d.get("escalated")]
    escalated_stops = [d for d in stops if d.get("escalated")]
    escalated_correct = [d for d in escalated_stops if correct(d["fixture_id"], d["final_tier"])]
    routed_attempts = [a for d in decisions for a in d["attempts"] if a.get("available")]
    unqualified_terminal = [d for d in stops if d["final_tier"] not in d["qualified_tiers"]]

    qualified_of = {(d["fixture_id"], tier): tier in d["qualified_tiers"] for d in decisions for tier in TIER_ORDER}
    caught_unqualified = surviving_qualified = 0
    for row in judged:
        sem = row["semantics"]
        if not sem["normalized_false_clean"]:
            continue
        if qualified_of[(row["fixture_id"], row["model_tier"])]:
            surviving_qualified += 1
        else:
            caught_unqualified += 1

    unsafe_rate = len(unsafe_stops) / len(stops) if stops else None
    admission_rate = len(correct_stops) / len(qualified_start) if qualified_start else None
    unsafe_evaluable = len(stops) >= gates["min_stops_for_unsafe_gate_to_be_evaluable"]
    admission_evaluable = len(qualified_start) >= gates["min_qualified_start_cases_for_admission_gate_to_be_evaluable"]
    outcome_counts = Counter(d["outcome"] for d in decisions)
    denominators_ok = (cases == 48 and sum(outcome_counts.values()) == cases
                       and set(outcome_counts) <= set(OUTCOMES) and len(judged) == 144)

    gate_results = {
        "unsafe_stop_rate_of_stops": {"observed": round(unsafe_rate, 6) if unsafe_rate is not None else None,
                                      "max": gates["max_unsafe_stop_rate_of_stops"], "evaluable": unsafe_evaluable,
                                      "upper_95": failure_rate_upper_bound(len(unsafe_stops), len(stops)),
                                      "passed": bool(unsafe_evaluable and unsafe_rate is not None
                                                     and unsafe_rate <= gates["max_unsafe_stop_rate_of_stops"])},
        "correct_stop_rate_of_qualified_start_cases": {
            "observed": round(admission_rate, 6) if admission_rate is not None else None,
            "min": gates["min_correct_stop_rate_of_qualified_start_cases"], "evaluable": admission_evaluable,
            "passed": bool(admission_evaluable and admission_rate is not None
                           and admission_rate >= gates["min_correct_stop_rate_of_qualified_start_cases"])},
        "unqualified_tier_terminal_results": {"observed": len(unqualified_terminal), "allowed": 0},
        "denominator_integrity": {"observed": denominators_ok, "required": True},
    }
    integrity_ok = not unqualified_terminal and denominators_ok
    rate_gates = [gate_results["unsafe_stop_rate_of_stops"], gate_results["correct_stop_rate_of_qualified_start_cases"]]
    if not integrity_ok:
        primary = "FAILED_INTEGRITY"
    elif any(gate["evaluable"] and not gate["passed"] for gate in rate_gates):
        primary = "FAIL"            # an evaluable failing gate is a failure, whatever the other gate says
    elif not all(gate["evaluable"] for gate in rate_gates):
        primary = "NOT_TESTABLE"
    else:
        primary = "PASS"

    sec = limits["secondary_escalation"]
    esc_unsafe = len(escalated_stops) - len(escalated_correct)
    if len(escalated_stops) < sec["min_escalated_stops_for_evaluation"]:
        secondary = "NOT_TESTABLE"
    elif (len(escalated_correct) >= sec["success_requires_correct_stops_gained_by_escalation_at_least"]
          and esc_unsafe / len(escalated_stops) <= sec["max_unsafe_rate_of_escalated_stops"]):
        secondary = "PASS"
    else:
        secondary = "FAIL"

    return {
        "contract_version": CONTRACT_VERSION,
        "primary_status": primary, "secondary_status": secondary,
        "table_sha256": table.get("table_sha256"),
        "metrics": {
            "validation_cases": cases, "r4_evidence_only_cases": outcome_counts[EVIDENCE_ONLY],
            "eligible_cases": len(eligible), "qualified_start_cases": len(qualified_start),
            "no_qualified_model_cases": outcome_counts[NO_QUALIFIED_MODEL],
            "escalation_exhausted_cases": outcome_counts[ESCALATION_EXHAUSTED],
            "stops": len(stops), "correct_stops": len(correct_stops), "unsafe_stops": len(unsafe_stops),
            "unsafe_stops_of_stops": _ratio(len(unsafe_stops), len(stops)),
            # Coding acceptance requires the focused tests to pass, so a coding stop cannot be unsafe. These two
            # views keep coding stops from silently diluting the pooled rate; the pooled gate itself is unchanged.
            "unsafe_stops_of_stops_excluding_coding": _ratio(
                sum(d["task_class"] != "coding_generation_repair" for d in unsafe_stops),
                sum(d["task_class"] != "coding_generation_repair" for d in stops)),
            "unsafe_stops_by_task_class": {
                task: _ratio(sum(d["task_class"] == task for d in unsafe_stops), sum(d["task_class"] == task for d in stops))
                for task in sorted({d["task_class"] for d in decisions})},
            "correct_stops_of_qualified_start_cases": _ratio(len(correct_stops), len(qualified_start)),
            "operational_rejection_rate_of_routed_attempts": _ratio(
                sum(not a["output_accepted"] for a in routed_attempts), len(routed_attempts)),
            "trigger_blocks_on_routed_attempts": sum(bool(a.get("triggers")) for a in routed_attempts),
            "escalation_count": len(escalated),
            "successful_escalations": len(escalated_correct),
            "failed_escalations": len(escalated) - len(escalated_correct),
            "final_tier_distribution": dict(Counter(d["final_tier"] or d["outcome"] for d in decisions)),
            "false_clean_stops": len(unsafe_stops),
            "false_clean_outputs_caught_because_tier_unqualified": caught_unqualified,
            "false_clean_outputs_surviving_despite_qualification": surviving_qualified,
            "routing_provider_calls": len(routed_attempts),
            "diagnostic_only_provider_calls": len(judged) - len(routed_attempts),
            "normalized_outputs_among_stops": sum(
                bool(truth[(d["fixture_id"], d["final_tier"])]["normalization"]["normalized"]) for d in stops),
        },
        "gates": gate_results,
        "generalization": generalization(judged, table),
        "decisions": decisions,
        "production_routing_invoked": False, "belief_effects": "none",
    }


def generalization(judged: list[Mapping[str, Any]], table: Mapping[str, Any]) -> dict[str, Any]:
    verdict_of = {(c["task_class"], c["risk_class"], c["model_tier"]): c["verdict"] for c in table["cells"]}
    a_cells = {(c["task_class"], c["risk_class"], c["model_tier"]): c for c in table["cells"]}
    b_rows: dict[tuple[str, str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in judged:
        b_rows[(row["task_class"], row["risk_class"], row["model_tier"])].append(row)
    cells = []
    for task in TASK_CLASSES:
        for risk in RISK_CLASSES:
            for tier in TIER_ORDER:
                rows = b_rows.get((task, risk, tier), [])
                ok = bool(rows) and len(rows) == 2 and all(
                    r["semantics"]["normalized_semantic_evaluation"]["hard_gate_pass"]
                    and r["normalized_operational_validation"]["accepted"]
                    and not r["semantics"]["normalized_false_clean"] for r in rows)
                a = verdict_of.get((task, risk, tier), "insufficient_evidence")
                label = {("qualified", True): "generalized", ("qualified", False): "false_positive_qualification",
                         ("not_qualified", True): "false_negative_qualification",
                         ("not_qualified", False): "consistent_unqualified"}.get((a, ok), "insufficient_on_a")
                b_correct = sum(bool(r["semantics"]["normalized_semantic_evaluation"]["hard_gate_pass"]) for r in rows)
                a_cell = a_cells.get((task, risk, tier), {})
                cells.append({"task_class": task, "risk_class": risk, "model_tier": tier,
                              "corpus_a_verdict": a, "corpus_b_success": ok, "corpus_b_correct": b_correct,
                              "corpus_a_pass_rate": (round(a_cell["semantic_passes"] / a_cell["complete_observations"], 6)
                                                     if a_cell.get("complete_observations") else None),
                              "corpus_b_pass_rate": round(b_correct / len(rows), 6) if rows else None,
                              "label": label})

    def stability(key: str) -> dict[str, Any]:
        out = {}
        for value in sorted({c[key] for c in cells}):
            rows = [c for c in cells if c[key] == value and c["corpus_a_verdict"] != "insufficient_evidence"]
            agree = sum(c["label"] in ("generalized", "consistent_unqualified") for c in rows)
            out[value] = {"agreement": _ratio(agree, len(rows)), "labels": dict(Counter(c["label"] for c in rows))}
        return out

    labels = Counter(c["label"] for c in cells)
    return {"cells": cells, "label_counts": dict(labels),
            "denominator_asymmetry": ("Qualification on A needs 4 of 4 observations; success on B needs 2 of 2. At the "
                                      "same true pass rate p these occur with probability p^4 and p^2, so labels are "
                                      "biased toward false_negative_qualification. Per-observation pass rates for A and "
                                      "B are reported on every cell for that reason."),
            "by_task_class": stability("task_class"), "by_risk_class": stability("risk_class"),
            "by_model_tier": stability("model_tier")}


__all__ = ["CONTRACT_VERSION", "decide", "score", "generalization"]
