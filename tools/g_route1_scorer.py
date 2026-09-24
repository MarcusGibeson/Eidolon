from __future__ import annotations

"""Deterministic qualification matrix and routing simulation for G-ROUTE1."""

from collections import defaultdict
import statistics
from typing import Any, Iterable, Mapping

from g_route1_contract import MODEL_TIERS, RISK_CLASSES, TASK_CLASSES
from g_route1_execution_contract import EXPECTED_CALLS, EXPECTED_REPEATS, TIER_ORDER, build_schedule, load_thresholds


CONTRACT_VERSION = "g-route1.scorer.v1"


def _ratio(count: int, total: int) -> dict[str, Any]:
    return {"count": count, "of": total, "rate": round(count / total, 6) if total else None}


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * percentile))))
    return round(ordered[index], 6)


def _cell(records: list[Mapping[str, Any]], thresholds: Mapping[str, Any]) -> dict[str, Any]:
    expected = int(thresholds["expected_observations_per_cell"])
    operational = sum(bool(row["operational_validation"]["accepted"]) for row in records)
    semantic = sum(bool(row["semantic_evaluation"]["hard_gate_pass"]) for row in records)
    false_clean = sum(bool(row.get("false_clean")) for row in records)
    infrastructure = sum(bool(row.get("infrastructure_failure")) for row in records)
    structural = sum(bool(row["operational_validation"]["structural_valid"]) for row in records)
    grounding_rows = [row["operational_validation"].get("grounding_valid") for row in records]
    grounding = [value for value in grounding_rows if value is not None]
    latencies = [float(row.get("latency_seconds") or 0.0) for row in records if row.get("provider_contacted")]
    token_rates = [float(row.get("tokens_per_second")) for row in records if row.get("tokens_per_second") is not None]
    complete = len(records) == expected and len({row["repeat"] for row in records}) == expected
    qualified = (
        complete and infrastructure == 0 and operational == expected and semantic == expected
        and false_clean == 0 and all(row.get("returned_model") == row.get("model") for row in records)
    )
    return {
        "observations": len(records), "expected_observations": expected, "complete": complete,
        "qualified": qualified, "operational_acceptance": _ratio(operational, len(records)),
        "semantic_correctness": _ratio(semantic, len(records)),
        "structural_validity": _ratio(structural, len(records)),
        "false_clean_errors": false_clean, "infrastructure_failures": infrastructure,
        "validator_detected_failures": sum(not row["operational_validation"]["accepted"] for row in records),
        "validator_missed_semantic_failures": false_clean,
        "grounding_accuracy": _ratio(sum(bool(value) for value in grounding), len(grounding)),
        "repeat_consistency": len({(
            bool(row["operational_validation"]["accepted"]),
            bool(row["semantic_evaluation"]["hard_gate_pass"]),
        ) for row in records}) <= 1 if complete else False,
        "latency_seconds": {
            "median": round(statistics.median(latencies), 6) if latencies else None,
            "p95": _percentile(latencies, 0.95),
        },
        "tokens_per_second": {
            "median": round(statistics.median(token_rates), 6) if token_rates else None,
            "p95": _percentile(token_rates, 0.95),
        },
    }


def simulate_escalation(records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int], dict[str, Mapping[str, Any]]] = defaultdict(dict)
    for row in records:
        grouped[(str(row["fixture_id"]), int(row["repeat"]))][str(row["model_tier"])] = row
    output = []
    for (fixture_id, repeat), tiers in sorted(grouped.items()):
        attempts = []
        final = None
        false_clean_prevented_escalation = False
        for index, tier in enumerate(TIER_ORDER):
            row = tiers.get(tier)
            if row is None:
                attempts.append({"tier": tier, "available": False, "accepted": False, "reason": "missing_observation"})
                continue
            accepted = bool(row["operational_validation"]["accepted"])
            false_clean = bool(row.get("false_clean"))
            attempts.append({
                "tier": tier, "available": True, "accepted": accepted,
                "semantic_correct": bool(row["semantic_evaluation"]["hard_gate_pass"]),
                "false_clean": false_clean,
                "escalation_triggered": not accepted,
                "next_tier": TIER_ORDER[index + 1] if not accepted and index + 1 < len(TIER_ORDER) else None,
                "reason": "operational_accept" if accepted else "operational_rejection",
            })
            if accepted:
                final = tier
                false_clean_prevented_escalation = false_clean
                break
        output.append({
            "fixture_id": fixture_id, "repeat": repeat, "initial_tier": "small",
            "attempts": attempts, "final_simulated_tier": final or "no_qualified_model",
            "false_clean_prevented_escalation": false_clean_prevented_escalation,
            "production_routing_invoked": False,
        })
    return output


def score(records: list[Mapping[str, Any]]) -> dict[str, Any]:
    thresholds = load_thresholds()
    call_ids = [str(row.get("call_id") or "") for row in records]
    expected = {row.call_id: row for row in build_schedule()}
    bindings_valid = True
    for row in records:
        scheduled = expected.get(str(row.get("call_id") or ""))
        if scheduled is None or any(
            row.get(field) != getattr(scheduled, field)
            for field in ("fixture_id", "task_class", "risk_class", "model_tier", "model", "repeat")
        ):
            bindings_valid = False
    complete = (
        len(records) == EXPECTED_CALLS and len(set(call_ids)) == EXPECTED_CALLS
        and set(call_ids) == set(expected) and bindings_valid
    )
    grouped: dict[tuple[str, str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in records:
        grouped[(str(row["task_class"]), str(row["risk_class"]), str(row["model_tier"]))].append(row)
    matrix = []
    for task in TASK_CLASSES:
        for risk in RISK_CLASSES:
            for tier in MODEL_TIERS:
                rows = grouped.get((task, risk, tier), [])
                cell = _cell(rows, thresholds)
                matrix.append({"task_class": task, "risk_class": risk, "model_tier": tier, **cell})
    qualified = {(row["task_class"], row["risk_class"]): [] for row in matrix}
    for row in matrix:
        if row["qualified"]:
            qualified[(row["task_class"], row["risk_class"])].append(row["model_tier"])
    selections = []
    for task in TASK_CLASSES:
        for risk in RISK_CLASSES:
            tiers = [tier for tier in TIER_ORDER if tier in qualified[(task, risk)]]
            selections.append({
                "task_class": task, "risk_class": risk, "qualified_tiers": tiers,
                "cheapest_qualified": tiers[0] if tiers and risk != "R4" else None,
                "outcome": "evidence_only" if risk == "R4" else (f"use_{tiers[0]}" if tiers else "no_qualified_model"),
            })
    false_clean = [row["call_id"] for row in records if row.get("false_clean")]
    report = {
        "contract_version": CONTRACT_VERSION,
        "units": {
            "fixtures": 24, "task_classes": 6, "risk_classes": 4, "model_tiers": 3,
            "repeats_per_cell": EXPECTED_REPEATS, "qualification_cells": 72,
            "scheduled_calls": EXPECTED_CALLS, "observed_calls": len(records),
            "ambiguity_diagnostics": 0,
        },
        "complete": complete and all(row["complete"] for row in matrix),
        "qualification_matrix": matrix,
        "selection_matrix": selections,
        "escalation_simulation": simulate_escalation(records),
        "global_diagnostics": {
            "false_clean_errors": {"count": len(false_clean), "call_ids": false_clean},
            "provider_runtime_failures": sum(bool(row.get("infrastructure_failure")) for row in records),
            "provider_calls": sum(bool(row.get("provider_contacted")) for row in records),
            "prompt_tokens": sum(int((row.get("provider_metrics") or {}).get("prompt_eval_count") or 0) for row in records),
            "output_tokens": sum(int((row.get("provider_metrics") or {}).get("eval_count") or 0) for row in records),
            "ambiguity_handling": {"count": 0, "included_in_crisp_denominator": False},
        },
        "overall_leaderboard": None,
        "production_routing_invoked": False,
        "belief_effects": "none",
    }
    report["valid_completed_report"] = bool(report["complete"])
    return report


__all__ = ["CONTRACT_VERSION", "score", "simulate_escalation"]
