from __future__ import annotations

"""Era 3 metacognition, confidence calibration, and self-correction.

The contract exposes bounded diagnostics about reasoning quality, not private
chain-of-thought.  It distinguishes evidence classes, calibrates confidence,
flags stale context/fixation/circular plans/unsupported certainty, preserves
failed tactics, and recommends epistemic actions without executing them.
"""

from datetime import datetime, timezone
import math
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from ordinary_chat_development_campaign import _atomic_json, _digest, _read_json, _store_root
from metadata_mutation_coordination import metadata_mutation_lock
from cognitive_architecture_beta import assess_metacognition

CONTRACT_VERSION = "v1799.9"
SCHEMA_VERSION = "1"
MAX_CLAIMS = 64
MAX_EVENTS = 128
MAX_TACTICS = 32

EPISTEMIC_STATES = {"known", "measured", "remembered", "inferred", "assumed", "unknown"}
AUTHORITY_FLAGS = {
    "metacognitive_review_authorized": True,
    "confidence_calibration_authorized": True,
    "reasoning_self_correction_authorized": True,
    "execution_authorized": False,
    "provider_contact_authorized": False,
    "external_research_authorized": False,
    "project_mutation_authorized": False,
    "source_mutation_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "standing_authority_granted": False,
}

_SHOW = re.compile(r"^(?:show|inspect) epistemic session (?P<id>epistemic_[a-f0-9]{24})[.!?]*$", re.I)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _clamp(value: Any, default: float = 0.5) -> float:
    try:
        return round(max(0.0, min(1.0, float(value))), 4)
    except (TypeError, ValueError):
        return default


def _code(value: Any) -> str:
    text = re.sub(r"[^a-z0-9_.:-]+", "_", str(value or "").strip().lower()).strip("_")[:128]
    return text or "unknown"


def _path(session_id: str, runtime_root: str | Path | None = None) -> Path:
    return _store_root(runtime_root) / "epistemic_sessions" / f"{session_id}.json"


def _serialized_session_mutation(function):
    def wrapped(session_id: str, *args: Any, **kwargs: Any):
        with metadata_mutation_lock(_path(session_id, kwargs.get("runtime_root"))):
            return function(session_id, *args, **kwargs)
    return wrapped


def classify_epistemic_state(claim: Mapping[str, Any]) -> str:
    explicit = str(claim.get("epistemic_state") or "").lower()
    if explicit in EPISTEMIC_STATES:
        return explicit
    source = str(claim.get("source_kind") or "").lower()
    evidence_count = max(0, int(claim.get("evidence_count") or 0))
    direct = bool(claim.get("direct_observation"))
    if source in {"measurement", "benchmark", "test_result", "instrument"} or direct and evidence_count:
        return "measured"
    if source in {"operator_statement", "authoritative_record", "verified_document"} and evidence_count:
        return "known"
    if source in {"memory", "durable_memory", "episodic_memory"}:
        return "remembered"
    if source in {"inference", "reasoning", "causal_model"} or evidence_count:
        return "inferred"
    if source in {"assumption", "default", "heuristic"}:
        return "assumed"
    return "unknown"


def calibrate_claim(claim: Mapping[str, Any]) -> dict[str, Any]:
    state = classify_epistemic_state(claim)
    quality = _clamp(claim.get("evidence_quality"), 0.5)
    independence = _clamp(claim.get("independence"), 0.5)
    freshness = _clamp(claim.get("freshness"), 0.5)
    contradiction = _clamp(claim.get("contradiction_pressure"), 0.0)
    count = max(0, min(20, int(claim.get("evidence_count") or 0)))
    count_factor = min(1.0, math.log2(count + 1) / 3.0)
    base = {
        "known": 0.78, "measured": 0.82, "remembered": 0.62,
        "inferred": 0.56, "assumed": 0.35, "unknown": 0.15,
    }[state]
    calibrated = base + 0.12 * quality + 0.08 * independence + 0.08 * freshness + 0.08 * count_factor - 0.30 * contradiction
    calibrated = round(max(0.01, min(0.99, calibrated)), 4)
    asserted = _clamp(claim.get("asserted_confidence"), calibrated)
    return {
        "claim_code": _code(claim.get("claim_code") or claim.get("id")),
        "epistemic_state": state,
        "calibrated_confidence": calibrated,
        "asserted_confidence": asserted,
        "overconfidence_gap": round(max(0.0, asserted - calibrated), 4),
        "underconfidence_gap": round(max(0.0, calibrated - asserted), 4),
        "evidence_count": count,
        "evidence_quality": quality,
        "independence": independence,
        "freshness": freshness,
        "contradiction_pressure": contradiction,
        "unsupported_certainty": asserted - calibrated >= 0.20,
        "claim_text_exposed": False,
    }


def score_calibration(predictions: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = []
    for p in predictions[:200]:
        confidence = _clamp(p.get("confidence"), 0.5)
        outcome = 1.0 if bool(p.get("outcome")) else 0.0
        rows.append((confidence, outcome))
    if not rows:
        return {"ok": False, "status": "calibration_outcomes_required"}
    brier = sum((c - o) ** 2 for c, o in rows) / len(rows)
    bins = []
    for lower in (0.0, 0.2, 0.4, 0.6, 0.8):
        group = [(c, o) for c, o in rows if lower <= c < lower + 0.2 or (lower == 0.8 and c == 1.0)]
        if group:
            bins.append({
                "range": [lower, round(lower + 0.2, 1)], "count": len(group),
                "mean_confidence": round(sum(c for c, _ in group) / len(group), 4),
                "observed_frequency": round(sum(o for _, o in group) / len(group), 4),
            })
    return {"ok": True, "status": "calibration_scored", "prediction_count": len(rows), "brier_score": round(brier, 6), "bins": bins, "lower_brier_is_better": True}


def _cycle_detected(steps: Sequence[Mapping[str, Any]]) -> bool:
    graph: dict[str, list[str]] = {}
    for i, raw in enumerate(steps[:64]):
        code = _code(raw.get("step_code") or raw.get("id") or f"step_{i+1}")
        graph[code] = [_code(x) for x in list(raw.get("depends_on") or [])[:16]]
    visiting: set[str] = set(); visited: set[str] = set()
    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for dep in graph.get(node, []):
            if dep in graph and visit(dep):
                return True
        visiting.remove(node); visited.add(node); return False
    return any(visit(n) for n in graph)


def assess_reasoning_health(
    *, claims: Sequence[Mapping[str, Any]] = (), plan_steps: Sequence[Mapping[str, Any]] = (),
    tactic_history: Sequence[Mapping[str, Any]] = (), context_freshness: float = 1.0,
    response_signatures: Sequence[str] = (), uncertainty: float = 0.5,
) -> dict[str, Any]:
    calibrated = [calibrate_claim(c) for c in claims[:MAX_CLAIMS]]
    unsupported = [c for c in calibrated if c["unsupported_certainty"]]
    circular = _cycle_detected(plan_steps)
    failures: dict[str, int] = {}
    recent = list(tactic_history)[-MAX_TACTICS:]
    for t in recent:
        if str(t.get("outcome") or "").lower() in {"failed", "failure", "contradicted", "no_progress"}:
            code = _code(t.get("tactic_code")); failures[code] = failures.get(code, 0) + 1
    repeated_failed = sorted(code for code, count in failures.items() if count >= 2)
    signatures = [_code(s) for s in response_signatures[-8:]]
    collapse = len(signatures) >= 4 and len(set(signatures[-4:])) == 1
    stale = _clamp(context_freshness, 1.0) < 0.35
    high_uncertainty = _clamp(uncertainty, 0.5) >= 0.7
    issue_codes = []
    if unsupported: issue_codes.append("unsupported_certainty")
    if circular: issue_codes.append("circular_plan")
    if repeated_failed: issue_codes.append("repeated_failed_tactic")
    if stale: issue_codes.append("stale_context")
    if collapse: issue_codes.append("answer_pattern_collapse")
    if high_uncertainty: issue_codes.append("high_uncertainty")
    if circular or repeated_failed or collapse:
        action = "change_strategy"
    elif unsupported or stale:
        action = "seek_better_evidence"
    elif high_uncertainty:
        action = "deepen_reasoning"
    else:
        action = "proceed_bounded"
    return {
        "ok": True, "status": "reasoning_health_ready", "contract_version": CONTRACT_VERSION,
        "calibrated_claims": calibrated, "issue_codes": issue_codes,
        "unsupported_certainty_count": len(unsupported), "circular_plan_detected": circular,
        "repeated_failed_tactic_codes": repeated_failed, "stale_context_detected": stale,
        "answer_pattern_collapse_detected": collapse, "high_uncertainty": high_uncertainty,
        "recommended_epistemic_action": action,
        "private_chain_of_thought_exposed": False, "raw_claim_text_exposed": False,
        "action_executed": False, **AUTHORITY_FLAGS,
    }


def create_epistemic_session(
    subject_code: str, *, claims: Sequence[Mapping[str, Any]] = (), plan_steps: Sequence[Mapping[str, Any]] = (),
    context_freshness: float = 1.0, uncertainty: float = 0.5, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    subject = _code(subject_code)
    key = _digest({"subject": subject, "claims": [calibrate_claim(c)["claim_code"] for c in claims[:MAX_CLAIMS]]})
    session_id = f"epistemic_{key[:24]}"; path = _path(session_id, runtime_root)
    existing = _read_json(path)
    if existing:
        result = inspect_epistemic_session(session_id, runtime_root=runtime_root); result["status"] = "epistemic_session_current"; return result
    now = _now()
    record = {
        "status": "epistemic_session_ready", "epistemic_session_id": session_id, "revision": 1,
        "subject_code": subject, "claims_private": [dict(c) for c in claims[:MAX_CLAIMS]],
        "plan_steps_private": [dict(s) for s in plan_steps[:64]], "context_freshness": _clamp(context_freshness, 1.0),
        "uncertainty": _clamp(uncertainty, 0.5), "tactic_history": [], "response_signatures": [], "events": [],
        "created_at": now, "updated_at": now,
    }
    record["private_record_digest"] = _digest({k: v for k, v in record.items() if k != "private_record_digest"})
    _atomic_json(path, record); return inspect_epistemic_session(session_id, runtime_root=runtime_root)


def inspect_epistemic_session(session_id: str, *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    record = _read_json(_path(session_id, runtime_root))
    if not record:
        return {"ok": False, "status": "epistemic_session_not_found", "epistemic_session_id": session_id, **AUTHORITY_FLAGS}
    health = assess_reasoning_health(
        claims=record.get("claims_private") or [], plan_steps=record.get("plan_steps_private") or [],
        tactic_history=record.get("tactic_history") or [], context_freshness=record.get("context_freshness"),
        response_signatures=record.get("response_signatures") or [], uncertainty=record.get("uncertainty"),
    )
    result = {
        **health, "status": record.get("status", "epistemic_session_ready"),
        "epistemic_session_id": session_id, "revision": int(record.get("revision") or 0),
        "subject_code": record.get("subject_code"), "event_count": len(record.get("events") or []),
        "tactic_count": len(record.get("tactic_history") or []),
        "private_claim_records_exposed": False, "private_plan_steps_exposed": False,
        "created_at": record.get("created_at"), "updated_at": record.get("updated_at"),
    }
    result["epistemic_session_digest"] = _digest({k: v for k, v in result.items() if k != "epistemic_session_digest"})
    return result


@_serialized_session_mutation
def record_reasoning_outcome(
    session_id: str, expected_digest: str, *, tactic_code: str, outcome: str,
    evidence_digest: str = "", response_signature: str = "", context_freshness: float | None = None,
    uncertainty: float | None = None, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    path = _path(session_id, runtime_root); record = _read_json(path)
    if not record:
        return {"ok": False, "status": "epistemic_session_not_found", **AUTHORITY_FLAGS}
    current = inspect_epistemic_session(session_id, runtime_root=runtime_root)["epistemic_session_digest"]
    if expected_digest != current:
        return {"ok": False, "status": "stale_epistemic_session_digest", "current_digest": current, **AUTHORITY_FLAGS}
    tactic = _code(tactic_code); result_code = _code(outcome)
    ev = str(evidence_digest or "").lower()
    if ev and not re.fullmatch(r"[a-f0-9]{64}", ev):
        return {"ok": False, "status": "invalid_evidence_digest", **AUTHORITY_FLAGS}
    event_key = _digest({"tactic": tactic, "outcome": result_code, "evidence": ev, "signature": _code(response_signature)})
    if any(e.get("event_key") == event_key for e in record.get("events") or []):
        result = inspect_epistemic_session(session_id, runtime_root=runtime_root); result["status"] = "reasoning_outcome_replay"; return result
    record.setdefault("tactic_history", []).append({"tactic_code": tactic, "outcome": result_code, "evidence_digest": ev, "at": _now()})
    record["tactic_history"] = record["tactic_history"][-MAX_TACTICS:]
    if response_signature:
        record.setdefault("response_signatures", []).append(_code(response_signature)); record["response_signatures"] = record["response_signatures"][-16:]
    if context_freshness is not None: record["context_freshness"] = _clamp(context_freshness, 1.0)
    if uncertainty is not None: record["uncertainty"] = _clamp(uncertainty, 0.5)
    record.setdefault("events", []).append({"event_key": event_key, "event_kind": "reasoning_outcome", "tactic_code": tactic, "outcome": result_code, "evidence_digest": ev, "at": _now()})
    record["events"] = record["events"][-MAX_EVENTS:]
    record["revision"] = int(record.get("revision") or 1) + 1; record["updated_at"] = _now()
    record["private_record_digest"] = _digest({k: v for k, v in record.items() if k != "private_record_digest"})
    _atomic_json(path, record)
    result = inspect_epistemic_session(session_id, runtime_root=runtime_root); result["status"] = "reasoning_outcome_recorded"; return result


def legacy_metacognition_projection(session_id: str, *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    row = inspect_epistemic_session(session_id, runtime_root=runtime_root)
    if not row.get("ok"):
        return row
    evidence_completeness = 1.0 - min(1.0, row.get("unsupported_certainty_count", 0) / max(1, len(row.get("calibrated_claims") or [])))
    return assess_metacognition({
        "uncertainty": 1.0 if row.get("high_uncertainty") else 0.35,
        "evidence_completeness": evidence_completeness,
        "novelty": 0.5,
        "pattern_match_reliance": 0.9 if row.get("answer_pattern_collapse_detected") else 0.35,
        "stakes": 0.7 if row.get("issue_codes") else 0.3,
    }, version="1799.9")


def process_epistemic_self_correction_control(user_text: str, *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    text = str(user_text or "").strip(); lowered = text.lower()
    if "epistemic session" in lowered and any(x in lowered for x in (" and execute", " and install", " and act", " and promote")):
        return {"active": True, "ok": False, "status": "metacognitive_scope_expansion_rejected", **AUTHORITY_FLAGS}
    match = _SHOW.fullmatch(text)
    if match:
        return {"active": True, **inspect_epistemic_session(match.group("id").lower(), runtime_root=runtime_root)}
    if lowered in {"show metacognitive requirements", "inspect metacognitive requirements", "show epistemic control requirements"}:
        return {"active": True, "ok": True, "status": "metacognitive_requirements", "requirements": [
            "known_inferred_assumed_measured_remembered_unknown_separated", "confidence_calibrated_to_evidence",
            "unsupported_certainty_detected", "circular_plan_detected", "failed_tactic_nonrepetition",
            "stale_context_detected", "answer_pattern_collapse_detected", "private_chain_of_thought_never_exposed",
        ], **AUTHORITY_FLAGS}
    return {"active": False}


__all__ = [
    "CONTRACT_VERSION", "SCHEMA_VERSION", "EPISTEMIC_STATES", "AUTHORITY_FLAGS", "classify_epistemic_state",
    "calibrate_claim", "score_calibration", "assess_reasoning_health", "create_epistemic_session",
    "inspect_epistemic_session", "record_reasoning_outcome", "legacy_metacognition_projection",
    "process_epistemic_self_correction_control",
]
