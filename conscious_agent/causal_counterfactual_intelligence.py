from __future__ import annotations

"""Era 3 causal and counterfactual reasoning.

This is a read-only reasoning/evidence layer.  It composes the older v1281
causal diagnostic contract, adds explicit confounders, competing predictions,
counterfactual interventions, and restart-safe evidence updates, but never runs
a probe or converts a hypothesis into fact merely because it scores highest.
"""

from datetime import datetime, timezone
import math
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from ordinary_chat_development_campaign import _atomic_json, _digest, _read_json, _store_root
from metadata_mutation_coordination import metadata_mutation_lock
from causal_diagnostic_reasoning_foundations import (
    build_causal_hypothesis,
    build_causal_diagnostic_model,
    apply_probe_outcome,
)

CONTRACT_VERSION = "v1750.9"
SCHEMA_VERSION = "1"
MAX_HYPOTHESES = 8
MAX_PROBES = 16
MAX_OBSERVATIONS = 64
MAX_CONFOUNDERS = 16

AUTHORITY_FLAGS = {
    "causal_reasoning_authorized": True,
    "counterfactual_reasoning_authorized": True,
    "probe_execution_authorized": False,
    "test_execution_authorized": False,
    "provider_contact_authorized": False,
    "project_mutation_authorized": False,
    "source_mutation_authorized": False,
    "repair_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "standing_authority_granted": False,
}

_SAFE = re.compile(r"[^a-z0-9_.:-]+")
_SHOW = re.compile(r"^(?:show|inspect) causal case (?P<id>causal_[a-f0-9]{24})[.!?]*$", re.I)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _code(value: Any, fallback: str = "unknown") -> str:
    text = str(value or "").strip().lower().replace(" ", "_")
    text = _SAFE.sub("_", text).strip("_")[:128]
    return text or fallback


def _clamp(value: Any, default: float = 0.5) -> float:
    try:
        return round(max(0.01, min(0.99, float(value))), 4)
    except (TypeError, ValueError):
        return default


def _path(case_id: str, runtime_root: str | Path | None = None) -> Path:
    return _store_root(runtime_root) / "causal_cases" / f"{case_id}.json"


def _serialized_case_mutation(function):
    def wrapped(case_id: str, *args: Any, **kwargs: Any):
        with metadata_mutation_lock(_path(case_id, kwargs.get("runtime_root"))):
            return function(case_id, *args, **kwargs)
    return wrapped


def _normalize_hypothesis(row: Mapping[str, Any], index: int) -> dict[str, Any]:
    code = _code(row.get("hypothesis_code") or row.get("id") or f"hypothesis_{index+1}")
    predictions = []
    raw_predictions = row.get("predictions") or {}
    if isinstance(raw_predictions, Mapping):
        iterable = raw_predictions.items()
    else:
        iterable = []
        for item in raw_predictions if isinstance(raw_predictions, Sequence) and not isinstance(raw_predictions, (str, bytes)) else []:
            if isinstance(item, Mapping):
                iterable.append((item.get("probe_code"), item.get("expected_outcome")))
    for probe, outcome in iterable:
        p, o = _code(probe, ""), _code(outcome, "")
        if p and o and not any(x["probe_code"] == p for x in predictions):
            predictions.append({"probe_code": p, "expected_outcome": o})
        if len(predictions) >= MAX_PROBES:
            break
    confounders = []
    for c in row.get("confounders") or []:
        code_c = _code(c, "")
        if code_c and code_c not in confounders:
            confounders.append(code_c)
        if len(confounders) >= MAX_CONFOUNDERS:
            break
    return {
        "hypothesis_code": code,
        "proposition_private": " ".join(str(row.get("proposition") or code).split())[:400],
        "prior_confidence": _clamp(row.get("prior_confidence"), 0.5),
        "posterior_confidence": _clamp(row.get("prior_confidence"), 0.5),
        "predictions": predictions,
        "confounders": confounders,
        "support_count": 0,
        "contradiction_count": 0,
        "causal_status": "unresolved",
        "root_cause_proven": False,
    }


def _discrimination(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    hypotheses = list(record.get("hypotheses") or [])
    probe_codes = sorted({p["probe_code"] for h in hypotheses for p in h.get("predictions") or []})
    rows = []
    for probe in probe_codes:
        predictions = {}
        missing = 0
        for h in hypotheses:
            found = next((p["expected_outcome"] for p in h.get("predictions") or [] if p["probe_code"] == probe), None)
            if found is None:
                missing += 1
            else:
                predictions[h["hypothesis_code"]] = found
        groups = len(set(predictions.values()))
        coverage = len(predictions) / max(1, len(hypotheses))
        # Maximum when all hypotheses participate and split across outcomes.
        discrimination = round(coverage * (groups - 1) / max(1, len(hypotheses) - 1), 4)
        rows.append({
            "probe_code": probe,
            "hypothesis_coverage": len(predictions),
            "missing_prediction_count": missing,
            "distinct_predicted_outcomes": groups,
            "discrimination_score": discrimination,
            "predictions": predictions,
            "probe_executed": False,
        })
    rows.sort(key=lambda r: (-r["discrimination_score"], r["missing_prediction_count"], r["probe_code"]))
    return rows


def _public(record: Mapping[str, Any]) -> dict[str, Any]:
    hypotheses = []
    for h in record.get("hypotheses") or []:
        hypotheses.append({
            "hypothesis_code": h.get("hypothesis_code"),
            "prior_confidence": h.get("prior_confidence"),
            "posterior_confidence": h.get("posterior_confidence"),
            "predictions": h.get("predictions") or [],
            "confounders": h.get("confounders") or [],
            "support_count": int(h.get("support_count") or 0),
            "contradiction_count": int(h.get("contradiction_count") or 0),
            "causal_status": h.get("causal_status"),
            "root_cause_proven": False,
        })
    result = {
        "ok": True,
        "status": record.get("status", "causal_case_ready"),
        "contract_version": CONTRACT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "causal_case_id": record.get("causal_case_id"),
        "revision": int(record.get("revision") or 0),
        "observation_digest": record.get("observation_digest"),
        "hypotheses": hypotheses,
        "hypothesis_count": len(hypotheses),
        "discriminating_probes": _discrimination(record),
        "observation_count": len(record.get("observations") or []),
        "evidence_digest_count": len({o.get("evidence_digest") for o in record.get("observations") or [] if o.get("evidence_digest")}),
        "best_hypothesis_code": max(hypotheses, key=lambda h: h["posterior_confidence"])["hypothesis_code"] if hypotheses else None,
        "root_cause_proven": False,
        "misleading_log_resistant": True,
        "correlation_is_not_causation": True,
        "private_observation_text_exposed": False,
        "private_hypothesis_text_exposed": False,
        "raw_evidence_exposed": False,
        "created_at": record.get("created_at"),
        "updated_at": record.get("updated_at"),
        **AUTHORITY_FLAGS,
    }
    result["causal_case_digest"] = _digest({k: v for k, v in result.items() if k != "causal_case_digest"})
    return result


def create_causal_case(
    observation: str,
    hypotheses: Sequence[Mapping[str, Any]],
    *,
    evidence_provenance: Sequence[str] = (),
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    text = " ".join(str(observation or "").split())[:1000]
    rows = [_normalize_hypothesis(h, i) for i, h in enumerate(hypotheses[:MAX_HYPOTHESES]) if isinstance(h, Mapping)]
    if not text or len(rows) < 2:
        return {"ok": False, "status": "observation_and_two_hypotheses_required", **AUTHORITY_FLAGS}
    codes = [h["hypothesis_code"] for h in rows]
    if len(set(codes)) != len(codes):
        return {"ok": False, "status": "duplicate_hypothesis_code", **AUTHORITY_FLAGS}
    case_key = _digest({"observation": text, "hypotheses": [{"code": h["hypothesis_code"], "predictions": h["predictions"]} for h in rows]})
    case_id = f"causal_{case_key[:24]}"
    existing = _read_json(_path(case_id, runtime_root))
    if existing:
        result = _public(existing); result["status"] = "causal_case_current"; return result
    now = _now()
    record = {
        "status": "causal_case_ready",
        "causal_case_id": case_id,
        "revision": 1,
        "observation_private": text,
        "observation_digest": _digest(text),
        "evidence_provenance_codes": [_code(x) for x in list(evidence_provenance)[:16]],
        "hypotheses": rows,
        "observations": [],
        "created_at": now,
        "updated_at": now,
    }
    record["private_record_digest"] = _digest({k: v for k, v in record.items() if k != "private_record_digest"})
    _atomic_json(_path(case_id, runtime_root), record)
    return _public(record)


def inspect_causal_case(case_id: str, *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    record = _read_json(_path(case_id, runtime_root))
    if not record:
        return {"ok": False, "status": "causal_case_not_found", "causal_case_id": case_id, **AUTHORITY_FLAGS}
    return _public(record)


@_serialized_case_mutation
def record_probe_observation(
    case_id: str,
    expected_digest: str,
    *,
    probe_code: str,
    observed_outcome: str,
    evidence_digest: str,
    evidence_quality: float = 0.8,
    independence: float = 0.8,
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    path = _path(case_id, runtime_root); record = _read_json(path)
    if not record:
        return {"ok": False, "status": "causal_case_not_found", **AUTHORITY_FLAGS}
    current = _public(record)["causal_case_digest"]
    if expected_digest != current:
        return {"ok": False, "status": "stale_causal_case_digest", "current_digest": current, **AUTHORITY_FLAGS}
    probe = _code(probe_code); outcome = _code(observed_outcome)
    ev = str(evidence_digest or "").lower()
    if not re.fullmatch(r"[a-f0-9]{64}", ev):
        return {"ok": False, "status": "evidence_digest_required", **AUTHORITY_FLAGS}
    observation_key = _digest({"probe": probe, "outcome": outcome, "evidence": ev})
    if any(o.get("observation_key") == observation_key for o in record.get("observations") or []):
        result = _public(record); result["status"] = "causal_observation_replay"; return result
    quality = _clamp(evidence_quality, 0.8); independent = _clamp(independence, 0.8)
    weight = round(0.5 * quality + 0.5 * independent, 4)
    for h in record.get("hypotheses") or []:
        prediction = next((p["expected_outcome"] for p in h.get("predictions") or [] if p["probe_code"] == probe), None)
        prior = _clamp(h.get("posterior_confidence"), 0.5)
        if prediction is None:
            continue
        if prediction == outcome:
            # bounded odds update; strong but never proof
            odds = prior / (1 - prior)
            likelihood = 1.0 + 2.0 * weight
            posterior = odds * likelihood / (1 + odds * likelihood)
            h["support_count"] = int(h.get("support_count") or 0) + 1
            h["causal_status"] = "supported"
        else:
            odds = prior / (1 - prior)
            likelihood = max(0.2, 1.0 - 0.75 * weight)
            posterior = odds * likelihood / (1 + odds * likelihood)
            h["contradiction_count"] = int(h.get("contradiction_count") or 0) + 1
            h["causal_status"] = "challenged"
        h["posterior_confidence"] = round(max(0.01, min(0.99, posterior)), 4)
        h["root_cause_proven"] = False
    record.setdefault("observations", []).append({
        "observation_key": observation_key, "probe_code": probe, "observed_outcome": outcome,
        "evidence_digest": ev, "evidence_quality": quality, "independence": independent,
        "recorded_at": _now(),
    })
    record["observations"] = record["observations"][-MAX_OBSERVATIONS:]
    record["revision"] = int(record.get("revision") or 1) + 1; record["updated_at"] = _now()
    record["private_record_digest"] = _digest({k: v for k, v in record.items() if k != "private_record_digest"})
    _atomic_json(path, record)
    result = _public(record); result["status"] = "causal_observation_recorded"; return result


def counterfactual_analysis(case_id: str, expected_digest: str, *, intervention_code: str, assumed_outcome: str, runtime_root: str | Path | None = None) -> dict[str, Any]:
    record = _read_json(_path(case_id, runtime_root))
    if not record:
        return {"ok": False, "status": "causal_case_not_found", **AUTHORITY_FLAGS}
    current = _public(record)["causal_case_digest"]
    if expected_digest != current:
        return {"ok": False, "status": "stale_causal_case_digest", "current_digest": current, **AUTHORITY_FLAGS}
    probe = _code(intervention_code); outcome = _code(assumed_outcome)
    rows = []
    for h in record.get("hypotheses") or []:
        prediction = next((p["expected_outcome"] for p in h.get("predictions") or [] if p["probe_code"] == probe), None)
        if prediction is None:
            compatibility = "unknown"
        elif prediction == outcome:
            compatibility = "compatible"
        else:
            compatibility = "incompatible"
        rows.append({
            "hypothesis_code": h.get("hypothesis_code"),
            "predicted_outcome": prediction or "unknown",
            "assumed_outcome": outcome,
            "compatibility": compatibility,
            "current_confidence": h.get("posterior_confidence"),
            "causal_claim_created": False,
        })
    return {
        "ok": True,
        "status": "counterfactual_analysis_ready",
        "causal_case_id": case_id,
        "causal_case_digest": current,
        "intervention_code": probe,
        "assumed_outcome": outcome,
        "comparisons": rows,
        "counterfactual_is_not_observed_evidence": True,
        "root_cause_proven": False,
        "probe_executed": False,
        **AUTHORITY_FLAGS,
    }


def legacy_v1281_projection(case_id: str, *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    """Compose the older causal owner for compatibility/evidence lineage."""
    record = _read_json(_path(case_id, runtime_root))
    if not record:
        return {"ok": False, "status": "causal_case_not_found", **AUTHORITY_FLAGS}
    legacy_h = []
    for h in record.get("hypotheses") or []:
        pred = (h.get("predictions") or [{}])[0] if h.get("predictions") else {}
        legacy_h.append(build_causal_hypothesis(
            hypothesis_code=h.get("hypothesis_code"), cause_class="era3_candidate",
            symptom_codes=["observed_problem"], supporting_evidence=[], contradicting_evidence=[],
            probe_code=pred.get("probe_code") or "no_probe",
            expected_if_true=pred.get("expected_outcome") or "unknown",
            expected_if_false="alternative_outcome", confidence="medium",
        ))
    return build_causal_diagnostic_model(symptom_codes=["observed_problem"], hypotheses=legacy_h, evidence_codes=record.get("evidence_provenance_codes") or [])


def process_causal_reasoning_control(user_text: str, *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    text = str(user_text or "").strip(); lowered = text.lower()
    if "causal case" in lowered and any(x in lowered for x in (" and install", " and execute", " and repair", " and run")):
        return {"active": True, "ok": False, "status": "read_only_scope_expansion_rejected", **AUTHORITY_FLAGS}
    match = _SHOW.fullmatch(text)
    if match:
        return {"active": True, **inspect_causal_case(match.group("id").lower(), runtime_root=runtime_root)}
    if lowered in {"show causal reasoning requirements", "inspect causal reasoning requirements"}:
        return {"active": True, "ok": True, "status": "causal_reasoning_requirements", "requirements": [
            "at_least_two_competing_hypotheses", "predicted_observations", "disconfirming_evidence", "confounders",
            "discriminating_probe_before_root_cause_claim", "counterfactuals_are_not_observations",
        ], "root_cause_proven": False, **AUTHORITY_FLAGS}
    return {"active": False}


__all__ = [
    "CONTRACT_VERSION", "SCHEMA_VERSION", "AUTHORITY_FLAGS", "create_causal_case", "inspect_causal_case",
    "record_probe_observation", "counterfactual_analysis", "legacy_v1281_projection", "process_causal_reasoning_control",
]
