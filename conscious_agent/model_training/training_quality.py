from __future__ import annotations

"""Deterministic quality assessment for sanitized training candidates."""

from typing import Any, Mapping

CONTRACT_VERSION = "v2503.4.28.2"


def assess_training_record_quality(record: Mapping[str, Any]) -> dict[str, Any]:
    sanitized = bool(record.get("sanitized") is True)
    validation_passed = bool(record.get("validation_passed") is True)
    has_correction = bool(record.get("has_correction") is True)
    validation = record.get("validation") if isinstance(record.get("validation"), Mapping) else {}
    deterministic = bool(validation.get("deterministic") is True or validation.get("tests_passed") is True or validation.get("validator") is not None)
    provenance = record.get("provenance") if isinstance(record.get("provenance"), Mapping) else {}
    operator_reviewed = bool(provenance.get("operator_approved") is True or provenance.get("operator_reviewed") is True)
    failure_code = str(record.get("failure_code") or "")
    provenance = record.get("provenance") if isinstance(record.get("provenance"), Mapping) else provenance
    difficulty = max(1, min(5, int(provenance.get("difficulty", 2 if has_correction else 1) or 1)))
    novelty = max(0, min(10, int(provenance.get("novelty_score", 5) or 0)))

    score = 0
    reasons: list[str] = []
    if sanitized:
        score += 25; reasons.append("sanitized")
    if validation_passed:
        score += 30; reasons.append("validated_success")
    if deterministic:
        score += 25; reasons.append("deterministic_evidence")
    if has_correction:
        score += 10; reasons.append("correction_pair_available")
    if operator_reviewed:
        score += 10; reasons.append("operator_reviewed")
    score += min(10, max(0, (difficulty - 1) * 2)); reasons.append(f"difficulty_{difficulty}")
    score += min(5, novelty // 2); reasons.append("novelty_weighted")
    if not validation_passed:
        score = min(score, 35); reasons.append("unverified_chosen_output_rejected")
    if not sanitized:
        score = 0; reasons.append("unsanitized_rejected")

    eligible = bool(sanitized and validation_passed and score >= 70)
    return {
        "contract_version": CONTRACT_VERSION,
        "record_id": str(record.get("record_id") or ""),
        "quality_score": max(0, min(score, 100)),
        "quality_band": "high" if score >= 90 else "moderate" if score >= 70 else "low",
        "eligible_for_operator_approval": eligible,
        "reasons": reasons,
        "failure_code": failure_code[:120],
        "difficulty": difficulty,
        "novelty_score": novelty,
        "automatic_approval": False,
        "model_training_authorized": False,
        "model_promotion_authorized": False,
    }
