# forked from g_route3_validation
from __future__ import annotations

"""Phase B′ validation scoring (design "Gates (frozen before contact)", "P2", "E1", "Descriptive reporting",
"Generalization", "Scoring shapes in the fork").

Gold for B′ is loaded here, after collection has finished and after the router has decided every case from gold-blind
views. The router's decisions are made first and are then judged; nothing flows the other way. Routing itself is the
imported-unchanged routing module.

Design changes from the forked module:
- Two gates with three outcomes each, decided by the exact one-sided Clopper-Pearson bound forms at alpha = 0.05,
  evaluated in exact rational arithmetic (never by comparing rounded bounds), with the frozen floors (76 stops,
  30 qualified-start cases, 10 for the observed-rate FAIL). Every result reports k, n and both bounds.
- Primary status: FAILED_INTEGRITY, then FAIL, then NOT_TESTABLE, then PASS.
- Integrity denominators: 915 judged calls; 300 eligible and 5 R4 cases decided; the D9 per-cell composition.
- The secondary escalation verdict and the "excluding coding" metric are removed; E1 is descriptive.
- P2, the equal-weight class rate, the family cluster bound, per-family and per-cell breakdowns, research metrics and
  generalization (a two-sided exact 95% interval, no labels) are descriptive and never gating.
"""

from collections import Counter, defaultdict
from fractions import Fraction
import math
from typing import Any, Iterable, Mapping

import g_route1_validators as G1V
from g_route4_contract import (B_CELL_SIZES, EXPECTED_CALLS, RISK_CLASSES, TASK_CLASSES, TIER_ORDER,
                               indexed_fixture_gold, load_thresholds, runtime_fixtures)
from g_route4_qualification import attach_semantics, failure_rate_upper_bound
from g_route3_routing import (ESCALATION_EXHAUSTED, EVIDENCE_ONLY, NO_QUALIFIED_MODEL, OUTCOMES, STOPPED,
                              route, runtime_view)

CONTRACT_VERSION = "g-route4.validation.v1"
PASS, FAIL_SHOWN_WORSE, FAIL_NOT_SHOWN, NOT_TESTABLE = "PASS", "FAIL (shown worse)", "FAIL (not shown)", "NOT_TESTABLE"
# Element-shape failure (the research diagnosis's T7): an element of the wrong type or container, as the frozen
# research normalizer reports it.
ELEMENT_SHAPE_REASONS = ("research_schema_mismatch", "claims_not_list", "claim_schema_mismatch",
                         "citation_element_type_mismatch", "lineage_element_type_mismatch", "uncertainties_not_list",
                         "uncertainty_element_type_mismatch")


def _ratio(count: int, total: int) -> dict[str, Any]:
    return {"count": count, "of": total, "rate": round(count / total, 6) if total else None}


# ---------------------------------------------------------------- exact binomial forms (design "Bounds")
def _binom_cdf(k: int, n: int, p: Fraction) -> Fraction:
    """P(X <= k | n, p), exact."""
    if k < 0:
        return Fraction(0)
    return sum((Fraction(math.comb(n, i)) * p ** i * (1 - p) ** (n - i) for i in range(min(k, n) + 1)), Fraction(0))


def _binom_sf(k: int, n: int, p: Fraction) -> Fraction:
    """P(X >= k | n, p), exact."""
    return 1 - _binom_cdf(k - 1, n, p)


def upper_bound_at_most(k: int, n: int, p0: Fraction, alpha: Fraction) -> bool:
    """One-sided upper bound <= p0  <=>  P(X <= k | n, p0) <= alpha."""
    return n > 0 and _binom_cdf(k, n, p0) <= alpha


def lower_bound_above(k: int, n: int, p0: Fraction, alpha: Fraction) -> bool:
    """One-sided lower bound > p0  <=>  P(X >= k | n, p0) < alpha."""
    return n > 0 and _binom_sf(k, n, p0) < alpha


def lower_bound_at_least(x: int, n: int, p0: Fraction, alpha: Fraction) -> bool:
    """One-sided lower bound >= p0  <=>  P(X >= x | n, p0) <= alpha."""
    return n > 0 and _binom_sf(x, n, p0) <= alpha


def upper_bound_below(x: int, n: int, p0: Fraction, alpha: Fraction) -> bool:
    """One-sided upper bound < p0  <=>  P(X <= x | n, p0) < alpha."""
    return n > 0 and _binom_cdf(x, n, p0) < alpha


def lower_bound(k: int, n: int, confidence: float = 0.95) -> float | None:
    """One-sided exact (Clopper-Pearson) lower bound on a binomial rate, reported numerically."""
    if n <= 0:
        return None
    if k <= 0:
        return 0.0
    alpha = 1.0 - confidence

    def sf(p: float) -> float:
        return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))

    low, high = 0.0, 1.0
    for _ in range(80):
        mid = (low + high) / 2
        if sf(mid) < alpha:
            low = mid
        else:
            high = mid
    return round(low, 6)


def upper_bound(k: int, n: int, confidence: float = 0.95) -> float | None:
    """One-sided exact (Clopper-Pearson) upper bound, reported numerically."""
    return failure_rate_upper_bound(k, n, confidence)


def two_sided_interval(k: int, n: int) -> dict[str, Any]:
    """Two-sided exact 95% Clopper-Pearson interval (descriptive)."""
    return {"k": k, "n": n, "lower_95_two_sided": lower_bound(k, n, 0.975),
            "upper_95_two_sided": upper_bound(k, n, 0.975)}


def unsafe_stop_outcome(k: int, n: int, gates: Mapping[str, Any]) -> str:
    """n = stops, k = unsafe stops. The frozen three-way table (the outcome only)."""
    p0, alpha = Fraction(str(gates["max_unsafe_stop_rate_of_stops"])), Fraction(str(gates["alpha"]))
    floor, observed_floor = gates["min_stops_for_unsafe_gate_pass"], gates["min_n_for_observed_rate_fail"]
    if lower_bound_above(k, n, p0, alpha):
        return FAIL_SHOWN_WORSE
    if n >= floor and upper_bound_at_most(k, n, p0, alpha):
        return PASS
    if (n >= floor and not upper_bound_at_most(k, n, p0, alpha)) or (n >= observed_floor and Fraction(k, n) > p0):
        return FAIL_NOT_SHOWN
    return NOT_TESTABLE


def correct_stop_outcome(x: int, n: int, gates: Mapping[str, Any]) -> str:
    """n = qualified-start cases, x = correct stops. The frozen three-way table (the outcome only)."""
    p0, alpha = Fraction(str(gates["min_correct_stop_rate_of_qualified_start_cases"])), Fraction(str(gates["alpha"]))
    floor, observed_floor = gates["min_qualified_start_cases_for_correct_gate_pass"], gates["min_n_for_observed_rate_fail"]
    if upper_bound_below(x, n, p0, alpha):
        return FAIL_SHOWN_WORSE
    if n >= floor and lower_bound_at_least(x, n, p0, alpha):
        return PASS
    if (n >= floor and not lower_bound_at_least(x, n, p0, alpha)) or (n >= observed_floor and Fraction(x, n) < p0):
        return FAIL_NOT_SHOWN
    return NOT_TESTABLE


def unsafe_stop_gate(k: int, n: int, gates: Mapping[str, Any]) -> dict[str, Any]:
    """The unsafe-stop gate result: its outcome, with k, n and both reported bounds."""
    return {"outcome": unsafe_stop_outcome(k, n, gates), "k": k, "n": n, "observed": round(k / n, 6) if n else None,
            "lower_95": lower_bound(k, n), "upper_95": upper_bound(k, n),
            "bound": str(Fraction(str(gates["max_unsafe_stop_rate_of_stops"]))),
            "floor": gates["min_stops_for_unsafe_gate_pass"]}


def correct_stop_gate(x: int, n: int, gates: Mapping[str, Any]) -> dict[str, Any]:
    """The correct-stop gate result: its outcome, with k, n and both reported bounds."""
    return {"outcome": correct_stop_outcome(x, n, gates), "k": x, "n": n, "observed": round(x / n, 6) if n else None,
            "lower_95": lower_bound(x, n), "upper_95": upper_bound(x, n),
            "bound": str(Fraction(str(gates["min_correct_stop_rate_of_qualified_start_cases"]))),
            "floor": gates["min_qualified_start_cases_for_correct_gate_pass"]}


# ---------------------------------------------------------------- routing, research metrics and scoring
def decide(records: Iterable[Mapping[str, Any]], table: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Gold-blind routing of every B′ case. Consumes no semantic field."""
    by_case: dict[str, dict[str, Mapping[str, Any]]] = defaultdict(dict)
    for row in records:
        by_case[row["fixture_id"]][row["model_tier"]] = row
    fixtures = runtime_fixtures("B")
    decisions = []
    for fixture_id in sorted(fixtures):
        views = {tier: runtime_view(row) for tier, row in by_case.get(fixture_id, {}).items()}
        decisions.append(route(fixtures[fixture_id], table, lambda tier, v=views: v.get(tier)))
    return decisions


def research_metrics(judged: Iterable[Mapping[str, Any]], gold_of: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Descriptive, over every research output of every tier (design "Descriptive reporting"): claim-level agreement
    (a claim's status, citations and lineages all equal gold), uncertainty-code agreement (exact set equality with gold)
    and element-shape failures (a count). Parsing and normalization are the frozen validator's own."""
    claims = claims_agree = outputs = codes_agree = shape_failures = 0
    for row in judged:
        if row["task_class"] != "grounded_research_synthesis":
            continue
        outputs += 1
        want_reasons: list[str] = []
        want = G1V._normalize_research(dict(gold_of[row["fixture_id"]]["expected"]), want_reasons)
        claims += len(want["claims"])
        value, parse_reasons = G1V._parse_object(row["normalization"]["payload"])
        if value is None:
            continue
        reasons: list[str] = []
        got = G1V._normalize_research(value, reasons)
        if any(r.split(":")[0] in ELEMENT_SHAPE_REASONS for r in reasons):
            shape_failures += 1
        got_claims = {c["claim_id"]: c for c in got["claims"]}
        claims_agree += sum(got_claims.get(c["claim_id"]) == c for c in want["claims"])
        codes_agree += set(got["uncertainties"]) == set(want["uncertainties"])
    return {"research_outputs": outputs, "claim_level_agreement": _ratio(claims_agree, claims),
            "uncertainty_code_agreement": _ratio(codes_agree, outputs), "element_shape_failures": shape_failures,
            "element_shape_definition": list(ELEMENT_SHAPE_REASONS)}


def score(records: list[Mapping[str, Any]], table: Mapping[str, Any], thresholds: Mapping[str, Any] | None = None,
          families: Mapping[str, str] | None = None) -> dict[str, Any]:
    limits = dict(thresholds or load_thresholds())
    gates = limits["gates"]
    decisions = decide(records, table)                 # routing first, gold-blind
    judged = attach_semantics(records, "B")            # then judgment, evaluator side
    truth = {(r["fixture_id"], r["model_tier"]): r for r in judged}

    def correct(fixture_id: str, tier: str) -> bool:
        return bool(truth[(fixture_id, tier)]["semantics"]["normalized_semantic_evaluation"]["hard_gate_pass"])

    cases = len(decisions)
    eligible = [d for d in decisions if d["risk_class"] != "R4"]
    r4 = [d for d in decisions if d["risk_class"] == "R4"]
    qualified_start = [d for d in eligible if d["qualified_tiers"]]
    stops = [d for d in decisions if d["outcome"] == STOPPED]
    correct_stops = [d for d in stops if correct(d["fixture_id"], d["final_tier"])]
    unsafe_stops = [d for d in stops if not correct(d["fixture_id"], d["final_tier"])]
    qualified_start_correct = [d for d in qualified_start
                               if d["outcome"] == STOPPED and correct(d["fixture_id"], d["final_tier"])]
    escalated = [d for d in decisions if d.get("escalated")]
    escalated_stops = [d for d in stops if d.get("escalated")]
    escalated_correct = [d for d in escalated_stops if correct(d["fixture_id"], d["final_tier"])]
    routed_attempts = [a for d in decisions for a in d["attempts"] if a.get("available")]
    unqualified_terminal = [d for d in stops if d["final_tier"] not in d["qualified_tiers"]]

    qualified_of = {(d["fixture_id"], tier): tier in d["qualified_tiers"] for d in decisions for tier in TIER_ORDER}
    caught_unqualified = surviving_qualified = 0
    for row in judged:
        if not row["semantics"]["normalized_false_clean"]:
            continue
        if qualified_of[(row["fixture_id"], row["model_tier"])]:
            surviving_qualified += 1
        else:
            caught_unqualified += 1

    outcome_counts = Counter(d["outcome"] for d in decisions)
    composition = Counter((d["task_class"], d["risk_class"]) for d in decisions)
    denominators = {"judged_calls": len(judged), "cases": cases, "eligible_cases": len(eligible), "r4_cases": len(r4),
                    "d9_composition_matches": dict(composition) == dict(B_CELL_SIZES),
                    "outcomes_known": set(outcome_counts) <= set(OUTCOMES),
                    "r4_decided_evidence_only": outcome_counts[EVIDENCE_ONLY] == len(r4)}
    denominators_ok = (len(judged) == EXPECTED_CALLS["B"] and cases == sum(B_CELL_SIZES.values())
                       and len(eligible) == 300 and len(r4) == 5 and sum(outcome_counts.values()) == cases
                       and denominators["d9_composition_matches"] and denominators["outcomes_known"]
                       and denominators["r4_decided_evidence_only"])

    unsafe_gate = unsafe_stop_gate(len(unsafe_stops), len(stops), gates)
    correct_gate = correct_stop_gate(len(qualified_start_correct), len(qualified_start), gates)
    integrity = {"denominator_integrity": {"observed": denominators_ok, "required": True, "detail": denominators},
                 "unqualified_tier_terminal_results": {"observed": len(unqualified_terminal),
                                                        "allowed": gates["unqualified_tier_terminal_results_allowed"]}}
    integrity_ok = denominators_ok and len(unqualified_terminal) <= gates["unqualified_tier_terminal_results_allowed"]
    outcomes = (unsafe_gate["outcome"], correct_gate["outcome"])
    if not integrity_ok:
        primary = "FAILED_INTEGRITY"
    elif any(o in (FAIL_SHOWN_WORSE, FAIL_NOT_SHOWN) for o in outcomes):
        primary = "FAIL"
    elif NOT_TESTABLE in outcomes:
        primary = "NOT_TESTABLE"
    else:
        primary = "PASS"

    # P2 (descriptive): the conversation stratum
    conversation_stops = [d for d in stops if d["task_class"] == "ordinary_conversation"]
    conversation_unsafe = [d for d in conversation_stops if not correct(d["fixture_id"], d["final_tier"])]
    small_conversation = [r for r in judged if r["task_class"] == "ordinary_conversation" and r["risk_class"] != "R4"
                          and r["model_tier"] == "small"]
    small_failures = sum(not r["semantics"]["normalized_semantic_evaluation"]["hard_gate_pass"]
                         for r in small_conversation)
    p2 = {"conversation_unsafe_stops": two_sided_interval(len(conversation_unsafe), len(conversation_stops)),
          "conversation_unsafe_stops_small_tier": two_sided_interval(
              sum(d["final_tier"] == "small" for d in conversation_unsafe),
              sum(d["final_tier"] == "small" for d in conversation_stops)),
          "small_tier_conversation_semantic_failures_all_eligible_cases": two_sided_interval(
              small_failures, len(small_conversation))}
    # E1 (pilot, descriptive; no verdict)
    e1 = {"escalations": len(escalated), "escalated_stops": two_sided_interval(len(escalated_stops), len(escalated)),
          "correct_among_escalated_stops": two_sided_interval(len(escalated_correct), len(escalated_stops)),
          "unsafe_among_escalated_stops": two_sided_interval(len(escalated_stops) - len(escalated_correct),
                                                             len(escalated_stops)),
          "verdict": None}
    # descriptive, never gating
    by_class = {task: _ratio(sum(d["task_class"] == task for d in unsafe_stops), sum(d["task_class"] == task for d in stops))
                for task in TASK_CLASSES}
    with_stops = [v["rate"] for v in by_class.values() if v["of"]]
    families = dict(families or {})
    family_stops = Counter(families.get(d["fixture_id"]) for d in stops)
    family_unsafe = Counter(families.get(d["fixture_id"]) for d in unsafe_stops)
    families_with_stops = sorted(f for f in family_stops if f is not None)
    families_with_unsafe = [f for f in families_with_stops if family_unsafe.get(f)]
    cell_breakdown = {f"{t}|{r}": _ratio(sum((d["task_class"], d["risk_class"]) == (t, r) for d in unsafe_stops),
                                         sum((d["task_class"], d["risk_class"]) == (t, r) for d in stops))
                      for t in TASK_CLASSES for r in RISK_CLASSES}
    gold_b = {fid: gold for fid, (_, gold) in indexed_fixture_gold("B").items()}
    return {
        "contract_version": CONTRACT_VERSION,
        "primary_status": primary,
        "table_sha256": table.get("table_sha256"),
        "gates": {"unsafe_stop_rate_of_stops": unsafe_gate, "correct_stop_rate_of_qualified_start_cases": correct_gate,
                  **integrity},
        "metrics": {
            "validation_cases": cases, "r4_evidence_only_cases": outcome_counts[EVIDENCE_ONLY],
            "eligible_cases": len(eligible), "qualified_start_cases": len(qualified_start),
            "no_qualified_model_cases": outcome_counts[NO_QUALIFIED_MODEL],
            "escalation_exhausted_cases": outcome_counts[ESCALATION_EXHAUSTED],
            "stops": len(stops), "correct_stops": len(correct_stops), "unsafe_stops": len(unsafe_stops),
            "correct_stops_of_qualified_start_cases": _ratio(len(qualified_start_correct), len(qualified_start)),
            "operational_rejection_rate_of_routed_attempts": _ratio(
                sum(not a["output_accepted"] for a in routed_attempts), len(routed_attempts)),
            "trigger_blocks_on_routed_attempts": sum(bool(a.get("triggers")) for a in routed_attempts),
            "final_tier_distribution": dict(Counter(d["final_tier"] or d["outcome"] for d in decisions)),
            "false_clean_stops": len(unsafe_stops),
            "false_clean_outputs_caught_because_tier_unqualified": caught_unqualified,
            "false_clean_outputs_surviving_despite_qualification": surviving_qualified,
            "routing_provider_calls": len(routed_attempts),
            "diagnostic_only_provider_calls": len(judged) - len(routed_attempts),
            "normalized_outputs_among_stops": sum(
                bool(truth[(d["fixture_id"], d["final_tier"])]["normalization"]["normalized"]) for d in stops),
        },
        "p2_descriptive": p2,
        "e1_pilot_descriptive": e1,
        "descriptive_never_gating": {
            "unsafe_stops_by_task_class": by_class,
            "equal_weight_by_class_unsafe_rate": round(sum(with_stops) / len(with_stops), 6) if with_stops else None,
            "equal_weight_by_class_note": "over classes with at least one stop; no bound",
            "unsafe_stops_by_family": {f: _ratio(family_unsafe.get(f, 0), family_stops[f]) for f in families_with_stops},
            "unsafe_stops_by_cell": cell_breakdown,
            "cluster_bound": {"label": "P(a template family has at least one unsafe stop)",
                              "families_with_an_unsafe_stop": len(families_with_unsafe),
                              "families_with_a_stop": len(families_with_stops),
                              "upper_95": upper_bound(len(families_with_unsafe), len(families_with_stops))},
            "research_metrics_b": research_metrics(judged, gold_b),
        },
        "generalization": generalization(judged, table),
        "decisions": decisions,
        "production_routing_invoked": False, "belief_effects": "none",
    }


def generalization(judged: list[Mapping[str, Any]], table: Mapping[str, Any]) -> dict[str, Any]:
    """Descriptive: for each tier and each eligible B′ cell, the semantic hard-gate pass rate with a two-sided exact
    95% Clopper-Pearson interval, beside the A′ verdict and the A′ pass rate on the same basis. No labels."""
    a_cells = {(c["task_class"], c["risk_class"], c["model_tier"]): c for c in table["cells"]}
    b_rows: dict[tuple[str, str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in judged:
        b_rows[(row["task_class"], row["risk_class"], row["model_tier"])].append(row)
    cells = []
    for task in TASK_CLASSES:
        for risk in RISK_CLASSES:
            if risk == "R4":
                continue
            for tier in TIER_ORDER:
                rows = b_rows.get((task, risk, tier), [])
                b_pass = sum(bool(r["semantics"]["normalized_semantic_evaluation"]["hard_gate_pass"]) for r in rows)
                a_cell = a_cells.get((task, risk, tier), {})
                cells.append({"task_class": task, "risk_class": risk, "model_tier": tier,
                              "a_verdict": a_cell.get("verdict", "insufficient_evidence"),
                              "a_pass_rate": (round(a_cell["semantic_passes"] / a_cell["complete_observations"], 6)
                                              if a_cell.get("complete_observations") else None),
                              "b_semantic_pass": two_sided_interval(b_pass, len(rows)),
                              "b_pass_rate": round(b_pass / len(rows), 6) if rows else None})
    return {"cells": cells, "basis": "semantic hard-gate pass rate, per tier and eligible B′ cell",
            "labels": "none (the prior experiment's generalization labels are not used)"}


__all__ = ["CONTRACT_VERSION", "PASS", "FAIL_SHOWN_WORSE", "FAIL_NOT_SHOWN", "NOT_TESTABLE", "decide", "score",
           "generalization", "research_metrics", "unsafe_stop_gate", "correct_stop_gate", "unsafe_stop_outcome",
           "correct_stop_outcome", "upper_bound_at_most",
           "lower_bound_above", "lower_bound_at_least", "upper_bound_below", "lower_bound", "upper_bound",
           "two_sided_interval"]
