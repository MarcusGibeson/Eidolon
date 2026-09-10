from __future__ import annotations

"""Median/p95 regression analysis for v1253.7.

Receipts contain timing/count metrics only. A regression finding is evidence for
operator review, never automatic release or rollback authority.
"""

import hashlib
import json
import math
import statistics
from typing import Any, Iterable, Mapping

from performance_budgets import evaluate_budget

CONTRACT_VERSION = "v1253.7"
RUNTIME_REPAIR_VERSION = "v1253.9.1"


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def summarize_samples(samples: Iterable[float]) -> dict[str, Any]:
    values = sorted(float(value) for value in samples)
    if not values:
        return {"count": 0, "median": None, "p95": None, "minimum": None, "maximum": None}
    p95_index = max(0, min(len(values) - 1, math.ceil(len(values) * 0.95) - 1))
    return {
        "count": len(values),
        "median": round(statistics.median(values), 4),
        "p95": round(values[p95_index], 4),
        "minimum": round(values[0], 4),
        "maximum": round(values[-1], 4),
    }


def compare_metric(
    name: str,
    current_samples: Iterable[float],
    *,
    baseline_samples: Iterable[float] | None = None,
    regression_ratio_max: float = 1.25,
) -> dict[str, Any]:
    current = summarize_samples(current_samples)
    baseline = summarize_samples(baseline_samples or [])
    budget = evaluate_budget(name, current, baseline=baseline if baseline["count"] else None)
    ratio = None
    regression = False
    if current["count"] and baseline["count"] and float(baseline["median"] or 0) > 0:
        ratio = float(current["median"]) / float(baseline["median"])
        regression = ratio > float(regression_ratio_max)
    row = {
        "metric": str(name),
        "current": current,
        "baseline": baseline,
        "median_ratio": round(ratio, 4) if ratio is not None else None,
        "regression_ratio_max": float(regression_ratio_max),
        "material_regression": regression,
        "budget": budget,
        "ok": bool(budget.get("ok")) and not regression,
        "content_free": True,
        "automatic_rollback_authorized": False,
        "release_authorized": False,
    }
    row["receipt_digest"] = _digest(row)
    return row


def build_performance_regression_receipt(metrics: Mapping[str, Iterable[float]], *, baselines: Mapping[str, Iterable[float]] | None = None) -> dict[str, Any]:
    rows = {name: compare_metric(name, samples, baseline_samples=(baselines or {}).get(name)) for name, samples in metrics.items()}
    receipt = {
        "contract_version": CONTRACT_VERSION,
        "ok": all(row["ok"] for row in rows.values()),
        "metrics": rows,
        "median_and_p95_used": True,
        "single_sample_release_gate": False,
        "content_free": True,
        "automatic_rollback_authorized": False,
        "release_authorized": False,
        "independent_authority_granted": False,
    }
    receipt["receipt_digest"] = _digest(receipt)
    return receipt


__all__ = ["CONTRACT_VERSION", "summarize_samples", "compare_metric", "build_performance_regression_receipt"]
