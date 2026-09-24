from __future__ import annotations

"""Dual-contract scoring for G-ROUTE2.

Every JSON-profile output is scored twice from the same bytes: once under the raw
transport contract G-ROUTE1 used, and once under the normalized contract. Formatting
and reasoning effects therefore stay separable within a single sample, with no
cross-run sampling noise. Qualification is decided under the normalized contract;
the raw matrix is reported beside it.

Gold is used here and only here. The routing policy never sees it.
"""

from collections import Counter, defaultdict
import statistics
from typing import Any, Iterable, Mapping, Sequence

from g_route1_contract import MODEL_TIERS, RISK_CLASSES, TASK_CLASSES
from g_route1_operational import validate_operational
from g_route1_validators import validate_fixture_output
from g_route2_contract import EXPECTED_CALLS, EXPECTED_REPEATS, TIER_ORDER, load_thresholds
from g_route2_normalization import ACCEPTED_OUTCOMES, JSON_PROFILES, OUTCOMES, normalize
from g_route2_policy import evaluate as evaluate_policy, simulate

CONTRACT_VERSION = "g-route2.scorer.v1"


def _ratio(count: int, total: int) -> dict[str, Any]:
    return {"count": count, "of": total, "rate": round(count / total, 6) if total else None}


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * percentile))))
    return round(ordered[index], 6)


def evaluate_output(
    fixture: Mapping[str, Any], gold: Mapping[str, Any], raw_output: Any, *,
    execution_evidence: Mapping[str, Any] | None = None,
    routing_table: Mapping[str, Sequence[str]] | None = None,
    model_tier: str = "", repeat_disagreement_observed: bool = False,
) -> dict[str, Any]:
    """Produce normalization, both contract results, and the three routing verdicts."""
    profile = str(fixture["validator_profile"])
    record = normalize(raw_output, validator_profile=profile)
    raw_operational = validate_operational(fixture, raw_output, execution_evidence=execution_evidence)
    raw_semantic = validate_fixture_output(fixture, gold, raw_output, execution_evidence=execution_evidence)
    normalized_operational = validate_operational(fixture, record["payload"], execution_evidence=execution_evidence)
    normalized_semantic = validate_fixture_output(fixture, gold, record["payload"],
                                                  execution_evidence=execution_evidence)
    policy = evaluate_policy(
        fixture=fixture, normalization=record, operational=normalized_operational,
        routing_table=routing_table, model_tier=model_tier,
        execution_evidence=execution_evidence,
        repeat_disagreement_observed=repeat_disagreement_observed,
    )
    return {
        "normalization": record,
        "raw_contract": {
            "operational_validation": raw_operational, "semantic_evaluation": raw_semantic,
            "false_clean": bool(raw_operational["accepted"] and not raw_semantic["hard_gate_pass"]),
        },
        "normalized_contract": {
            "operational_validation": normalized_operational, "semantic_evaluation": normalized_semantic,
            "false_clean": bool(normalized_operational["accepted"] and not normalized_semantic["hard_gate_pass"]),
        },
        "policy": policy,
    }


def _contract(row: Mapping[str, Any], contract: str) -> Mapping[str, Any]:
    return row[contract + "_contract"]


def _cell(records: list[Mapping[str, Any]], thresholds: Mapping[str, Any], contract: str) -> dict[str, Any]:
    expected = int(thresholds["expected_observations_per_cell"])
    rows = [_contract(row, contract) for row in records]
    operational = sum(bool(row["operational_validation"]["accepted"]) for row in rows)
    semantic = sum(bool(row["semantic_evaluation"]["hard_gate_pass"]) for row in rows)
    structural = sum(bool(row["operational_validation"]["structural_valid"]) for row in rows)
    false_clean = sum(bool(row["false_clean"]) for row in rows)
    infrastructure = sum(bool(row.get("infrastructure_failure")) for row in records)
    complete = len(records) == expected and len({row["repeat"] for row in records}) == expected
    qualified = (
        complete and infrastructure == 0 and operational == expected and semantic == expected
        and false_clean == 0 and all(row.get("returned_model") == row.get("model") for row in records)
    )
    latencies = [float(row.get("latency_seconds") or 0.0) for row in records if row.get("provider_contacted")]
    token_rates = [float(row["tokens_per_second"]) for row in records if row.get("tokens_per_second") is not None]
    return {
        "observations": len(records), "expected_observations": expected, "complete": complete,
        "qualified": qualified,
        "operational_acceptance": _ratio(operational, len(records)),
        "semantic_correctness": _ratio(semantic, len(records)),
        "structural_validity": _ratio(structural, len(records)),
        "false_clean_errors": false_clean,
        "infrastructure_failures": infrastructure,
        "validator_detected_failures": sum(not row["operational_validation"]["accepted"] for row in rows),
        "validator_missed_semantic_failures": false_clean,
        "normalization_rate": _ratio(sum(bool(row["normalization"]["normalized"]) for row in records),
                                     len(records)),
        "repeat_consistency": len({(
            bool(row["operational_validation"]["accepted"]),
            bool(row["semantic_evaluation"]["hard_gate_pass"]),
        ) for row in rows}) <= 1 if complete else False,
        "latency_seconds": {
            "median": round(statistics.median(latencies), 6) if latencies else None,
            "p95": _percentile(latencies, 0.95)},
        "tokens_per_second": {
            "median": round(statistics.median(token_rates), 6) if token_rates else None,
            "p95": _percentile(token_rates, 0.95)},
    }


def matrix(records: Iterable[Mapping[str, Any]], thresholds: Mapping[str, Any], contract: str) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in records:
        grouped[(str(row["task_class"]), str(row["risk_class"]), str(row["model_tier"]))].append(row)
    rows = []
    for task in TASK_CLASSES:
        for risk in RISK_CLASSES:
            for tier in MODEL_TIERS:
                rows.append({"task_class": task, "risk_class": risk, "model_tier": tier,
                             "contract": contract,
                             **_cell(grouped.get((task, risk, tier), []), thresholds, contract)})
    return rows


def routing_table(qualification_matrix: Iterable[Mapping[str, Any]]) -> dict[str, list[str]]:
    table: dict[str, list[str]] = {}
    for row in qualification_matrix:
        key = str(row["task_class"]) + "|" + str(row["risk_class"])
        table.setdefault(key, [])
        if row["qualified"]:
            table[key].append(str(row["model_tier"]))
    return {key: [tier for tier in TIER_ORDER if tier in value] for key, value in table.items()}


def selection(qualification_matrix: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    table = routing_table(qualification_matrix)
    rows = []
    for task in TASK_CLASSES:
        for risk in RISK_CLASSES:
            tiers = table.get(task + "|" + risk, [])
            rows.append({
                "task_class": task, "risk_class": risk, "qualified_tiers": tiers,
                "cheapest_qualified": tiers[0] if tiers and risk != "R4" else None,
                "outcome": "evidence_only" if risk == "R4" else (
                    f"use_{tiers[0]}" if tiers else "no_qualified_model"),
            })
    return rows


def escalation(records: Iterable[Mapping[str, Any]], *, mode: str = "table_free") -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int], list[Mapping[str, Any]]] = defaultdict(list)
    for row in records:
        grouped[(str(row["fixture_id"]), int(row["repeat"]))].append(row)
    rows = []
    for (fixture_id, repeat), units in sorted(grouped.items()):
        result = simulate(units, mode=mode)
        stopped_tier = result["final_simulated_tier"] if result["stopped"] else None
        stopped_row = next((row for row in units if row["model_tier"] == stopped_tier), None)
        semantically_correct = bool(
            stopped_row and _contract(stopped_row, "normalized")["semantic_evaluation"]["hard_gate_pass"]
        ) if stopped_row else None
        rows.append({
            "fixture_id": fixture_id, "repeat": repeat, "initial_tier": TIER_ORDER[0], **result,
            "stop_was_semantically_correct": semantically_correct,
            "unsafe_early_stop": bool(stopped_row is not None and semantically_correct is False),
            "stop_required_normalization": bool(
                stopped_row and stopped_row["normalization"]["normalized"]),
        })
    return rows


def score(records: list[Mapping[str, Any]], *, thresholds: Mapping[str, Any] | None = None) -> dict[str, Any]:
    limits = dict(thresholds or load_thresholds())
    gates = limits["gates"]
    call_ids = [str(row.get("call_id") or "") for row in records]
    complete_run = len(records) == EXPECTED_CALLS and len(set(call_ids)) == EXPECTED_CALLS

    normalized_matrix = matrix(records, limits, "normalized")
    raw_matrix = matrix(records, limits, "raw")
    table = routing_table(normalized_matrix)

    table_free = escalation(records, mode="table_free")
    stops = [row for row in table_free if row["stopped"]]
    unsafe = [row for row in table_free if row["unsafe_early_stop"]]
    useful = [row for row in stops if row["stop_was_semantically_correct"]]
    unsafe_from_normalization = [row for row in unsafe if row["stop_required_normalization"]]

    outcome_counts = Counter(str(row["normalization"]["outcome"]) for row in records)
    json_rows = [row for row in records
                 if str(row.get("prompt_profile") or row.get("validator_profile") or "") in JSON_PROFILES]

    def totals(contract: str) -> dict[str, Any]:
        rows = [_contract(row, contract) for row in records]
        return {
            "structural_validity": _ratio(sum(r["operational_validation"]["structural_valid"] for r in rows), len(rows)),
            "operational_acceptance": _ratio(sum(r["operational_validation"]["accepted"] for r in rows), len(rows)),
            "semantic_correctness": _ratio(sum(r["semantic_evaluation"]["hard_gate_pass"] for r in rows), len(rows)),
            "false_clean": sum(r["false_clean"] for r in rows),
            "validator_detected_semantic_failures": sum(not r["operational_validation"]["accepted"] for r in rows),
            "validator_missed_semantic_failures": sum(r["false_clean"] for r in rows),
            "qualified_cells": sum(c["qualified"] for c in (normalized_matrix if contract == "normalized" else raw_matrix)),
        }

    efficiency = {}
    for tier in TIER_ORDER:
        rows = [row for row in records if row["model_tier"] == tier]
        latencies = [float(row.get("latency_seconds") or 0.0) for row in rows]
        rates = [float(row["tokens_per_second"]) for row in rows if row.get("tokens_per_second") is not None]
        efficiency[tier] = {
            "calls": len(rows),
            "total_latency_seconds": round(sum(latencies), 6),
            "latency_median": round(statistics.median(latencies), 6) if latencies else None,
            "latency_p95": _percentile(latencies, 0.95),
            "prompt_tokens": sum(int((row.get("provider_metrics") or {}).get("prompt_eval_count") or 0) for row in rows),
            "output_tokens": sum(int((row.get("provider_metrics") or {}).get("eval_count") or 0) for row in rows),
            "tokens_per_second_median": round(statistics.median(rates), 6) if rates else None,
        }

    gate_results = {
        "infrastructure_crashes_from_model_output": {
            "observed": sum(1 for row in records if str(row.get("infrastructure_failure") or "").startswith("frozen_evaluator")),
            "allowed": gates["infrastructure_crashes_from_model_output_allowed"]},
        "unsafe_terminal_acceptance_from_normalization": {
            "observed": len(unsafe_from_normalization),
            "allowed": gates["unsafe_terminal_acceptance_attributable_solely_to_normalization_allowed"]},
        "normalization_changed_semantic_values": {
            "observed": sum(1 for row in records if row["normalization"].get("semantic_values_changed")),
            "allowed": 0},
        "unsafe_early_stop_rate_of_stops": {
            "observed": round(len(unsafe) / len(stops), 6) if stops else 0.0,
            "max": gates["max_unsafe_early_stop_rate_of_stops"]},
        "useful_admission_rate_of_fixture_repeats": {
            "observed": round(len(useful) / len(table_free), 6) if table_free else 0.0,
            "min": gates["min_useful_admission_rate_of_fixture_repeats"]},
        "every_qualified_cell_complete": {
            "observed": all(cell["complete"] for cell in normalized_matrix if cell["qualified"]), "required": True},
        "no_vacuous_pass": {
            "observed": not any(cell["qualified"] and cell["observations"] == 0 for cell in normalized_matrix),
            "required": True},
    }
    gates_passed = (
        gate_results["infrastructure_crashes_from_model_output"]["observed"] == 0
        and gate_results["unsafe_terminal_acceptance_from_normalization"]["observed"] == 0
        and gate_results["normalization_changed_semantic_values"]["observed"] == 0
        and gate_results["unsafe_early_stop_rate_of_stops"]["observed"] <= gates["max_unsafe_early_stop_rate_of_stops"]
        and gate_results["useful_admission_rate_of_fixture_repeats"]["observed"] >= gates["min_useful_admission_rate_of_fixture_repeats"]
        and gate_results["every_qualified_cell_complete"]["observed"]
        and gate_results["no_vacuous_pass"]["observed"]
    )

    report = {
        "contract_version": CONTRACT_VERSION,
        "units": {"fixtures": 24, "task_classes": 6, "risk_classes": 4, "model_tiers": 3,
                  "repeats_per_cell": EXPECTED_REPEATS, "qualification_cells": 72,
                  "scheduled_calls": EXPECTED_CALLS, "observed_calls": len(records),
                  "json_profile_calls": len(json_rows), "ambiguity_diagnostics": 0},
        "complete": complete_run and all(cell["complete"] for cell in normalized_matrix),
        "qualification_contract": "normalized",
        "qualification_matrix": normalized_matrix,
        "raw_contract_matrix": raw_matrix,
        "selection_matrix": selection(normalized_matrix),
        "routing_table": table,
        "routing_table_is_in_sample": True,
        "normalization": {
            "outcome_counts": {outcome: outcome_counts.get(outcome, 0) for outcome in OUTCOMES},
            "normalization_rate": _ratio(sum(1 for row in records if row["normalization"]["normalized"]), len(records)),
            "accepted_outcomes": list(ACCEPTED_OUTCOMES),
            "by_tier": {tier: sum(1 for row in records
                                  if row["model_tier"] == tier and row["normalization"]["normalized"])
                        for tier in TIER_ORDER},
        },
        "raw_contract_totals": totals("raw"),
        "normalized_contract_totals": totals("normalized"),
        "escalation_table_free": table_free,
        "escalation_summary": {
            "mode": "table_free",
            "final_tier_counts": dict(Counter(row["final_simulated_tier"] for row in table_free)),
            "stops": len(stops),
            "useful_admission": len(useful),
            "unsafe_early_stops": len(unsafe),
            "unsafe_early_stops_requiring_normalization": len(unsafe_from_normalization),
            "escalation_frequency": _ratio(len(table_free) - len(stops), len(table_free)),
            "no_qualified_model_rate": _ratio(
                sum(1 for row in table_free if row["final_simulated_tier"] == "no_qualified_model"), len(table_free)),
            "trigger_counts": dict(Counter(
                trigger for row in records for trigger in row["policy"]["triggers"])),
        },
        "efficiency": efficiency,
        "gates": gate_results,
        "gates_passed": gates_passed,
        "overall_leaderboard": None,
        "production_routing_invoked": False,
        "belief_effects": "none",
    }
    report["valid_completed_report"] = bool(report["complete"])
    return report


__all__ = ["CONTRACT_VERSION", "evaluate_output", "matrix", "routing_table", "selection",
           "escalation", "score"]
