from __future__ import annotations
from research_failure_receipts import sanitize_failures

"""Digest-bound, privacy-minimized history, comparison, and export helpers.

These helpers operate only on the existing bounded research coordinator's
runtime records. They perform no network or provider work and grant no new
authority. Raw objectives, queries, page bodies, credentials, cookies, provider
payloads, and private runtime paths are deliberately absent from all public
projections and export metadata.
"""

from datetime import datetime, timezone
import hashlib
import json
import math
import re
from typing import Any, Iterable, Mapping
from urllib.parse import urlsplit

CONTRACT_VERSION = "v2503.3"
HISTORY_SCHEMA_VERSION = "1"
EXPORT_SCHEMA_VERSION = "1"
MAX_HISTORY_RECORDS = 256
MAX_REPORT_ITEMS = 64

_DENIED = {
    "network_contacted": False,
    "provider_contacted": False,
    "write_method_used": False,
    "private_network_allowed": False,
    "credentials_allowed": False,
    "uploads_allowed": False,
    "source_modified": False,
    "memory_modified": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "release_authorized": False,
    "standing_research_authority_granted": False,
    "authority_expanded": False,
}

_PRIVATE_KEYS = {
    "objective",
    "query",
    "queries",
    "raw_page",
    "raw_page_content",
    "page_body",
    "body",
    "prompt",
    "provider_payload",
    "credentials",
    "credential",
    "cookies",
    "cookie",
    "authorization",
    "authorization_header",
    "filesystem_path",
    "absolute_path",
    "private_memory",
    "memory_text",
}


def _clean(value: object, limit: int = 8000) -> str:
    return " ".join(str(value or "").split()).strip()[:limit]


def _digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _hex64(value: object) -> str:
    text = str(value or "").strip().lower()
    return text if re.fullmatch(r"[0-9a-f]{64}", text) else ""


def _bounded_count(value: object) -> int:
    try:
        return max(0, min(1_000_000, int(value)))
    except (TypeError, ValueError, OverflowError):
        return 0


def _evidence_policy_projection(value: object) -> dict[str, Any]:
    """Project a policy measurement as condition codes and counts only."""
    if not isinstance(value, Mapping) or not value:
        return {}
    return {
        "policy_code": _clean(value.get("policy_code"), 40),
        "evaluated_citation_count": _bounded_count(value.get("evaluated_citation_count")),
        "admissible_citation_count": _bounded_count(value.get("admissible_citation_count")),
        "citation_condition_failures": _count_map(value.get("citation_condition_failures")),
        "authority_states": _count_map(value.get("authority_states")),
        "classification_reasons": _count_map(value.get("classification_reasons")),
        "document_forms": _count_map(value.get("document_forms")),
        "version_signal_count": _bounded_count(value.get("version_signal_count")),
        "finding_condition_failures": [
            code for code in (
                _clean(item, 60) for item in list(value.get("finding_condition_failures") or [])[:12]
            ) if code
        ],
        "would_admit": bool(value.get("would_admit")),
        "enforced": bool(value.get("enforced")),
    }


def _count_map(value: object, limit: int = 24) -> dict[str, int]:
    """Project diagnostic counters as fixed reason codes and counts only.

    Assessment grounding is otherwise invisible in a stored receipt, so a failure
    there cannot be diagnosed after the fact. Reason codes carry no claim text,
    quote, or URL, so counting them keeps the receipt content-free.
    """
    if not isinstance(value, Mapping):
        return {}
    rows: dict[str, int] = {}
    for key, count in list(value.items())[:limit]:
        code = _clean(key, 60)
        if code:
            rows[code] = _bounded_count(count)
    return rows


_DISCOVERY_REJECTION_REASONS = {
    "row_not_object",
    "missing_title",
    "missing_evidence_summary",
    "missing_observed_citations",
    "duplicate_title",
    "missing_required_fields",
    "generic_name",
}


def _sanitize_discovery_diagnostics(value: object) -> dict[str, Any]:
    source = dict(value) if isinstance(value, Mapping) else {}
    raw_reasons = source.get("rejected_opportunity_reason_counts")
    reasons = dict(raw_reasons) if isinstance(raw_reasons, Mapping) else {}
    return {
        "input_opportunity_count": _bounded_count(source.get("input_opportunity_count")),
        "admitted_opportunity_count": _bounded_count(source.get("admitted_opportunity_count")),
        "rejected_opportunity_reason_counts": {
            reason: _bounded_count(reasons.get(reason))
            for reason in sorted(_DISCOVERY_REJECTION_REASONS)
            if _bounded_count(reasons.get(reason))
        },
        "recommendation_admitted": bool(source.get("recommendation_admitted")),
    }


def _bounded_score(value: object) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    if not math.isfinite(score):
        return 0.0
    return round(max(0.0, min(1.0, score)), 4)


def _quality_band(value: object) -> str:
    score = _bounded_score(value)
    if score >= 0.75:
        return "high"
    if score >= 0.5:
        return "medium"
    if score > 0:
        return "low"
    return "unknown"


def _safe_url(value: object) -> tuple[str, str]:
    raw = _clean(value, 2048)
    try:
        parsed = urlsplit(raw)
    except Exception:
        return "", ""
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        return "", ""
    host = parsed.hostname.casefold().rstrip(".")[:255]
    return f"{parsed.scheme}://{host}{parsed.path or '/'}", host


def _iso(value: object) -> str:
    text = _clean(value, 64)
    if not text:
        return ""
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return ""
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def _contains_private_key(value: object) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).casefold() in _PRIVATE_KEYS:
                return True
            if _contains_private_key(item):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_contains_private_key(item) for item in value)
    return False


def sanitize_report(report: Mapping[str, Any] | None) -> dict[str, Any]:
    """Retain only bounded report material needed for review/compare/export."""
    source = dict(report or {})
    _assessment_summary = (
        source.get("source_assessment_summary")
        if isinstance(source.get("source_assessment_summary"), Mapping)
        else {}
    )
    citations: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in list(source.get("citations") or [])[:MAX_REPORT_ITEMS]:
        if not isinstance(raw, Mapping):
            continue
        citation_id = _clean(raw.get("citation_id"), 80)
        if not citation_id or citation_id in seen:
            continue
        public_url, host = _safe_url(raw.get("public_url"))
        if not public_url:
            continue
        seen.add(citation_id)
        freshness = _clean(raw.get("freshness"), 16).casefold()
        if freshness not in {"fresh", "stale", "unknown"}:
            freshness = "unknown"
        source_kind = _clean(raw.get("source_kind"), 60).casefold()
        if not re.fullmatch(r"[a-z][a-z0-9_-]{0,59}", source_kind):
            source_kind = "unknown"
        citations.append({
            "citation_id": citation_id,
            "public_url": public_url,
            "host": host,
            "source_kind": source_kind,
            "freshness": freshness,
            "quality_score": _bounded_score(raw.get("quality_score")),
            "relevance_score": _bounded_score(raw.get("relevance_score")),
            "source_digest": _hex64(raw.get("source_digest")),
            "candidate_digest": _hex64(raw.get("candidate_digest")),
            "evidence_dimension": _clean(raw.get("evidence_dimension"), 60),
            "stance": _clean(raw.get("stance"), 20),
            "source_identity_digest": _hex64(raw.get("source_identity_digest")),
            "canonical_page_digest": _hex64(raw.get("canonical_page_digest")),
            "publisher_digest": _hex64(raw.get("publisher_digest")),
            "lineage_digest": _hex64(raw.get("lineage_digest")),
            "lineage_reason": _clean(raw.get("lineage_reason"), 60),
            "independence_state": _clean(raw.get("independence_state"), 20),
            "authoritative_source": bool(raw.get("authoritative_source")),
        })

    claims: list[dict[str, Any]] = []
    allowed_states = {"supported", "refuted", "conflicted", "insufficient_current_evidence"}
    for raw in list(source.get("claim_assessments") or [])[:MAX_REPORT_ITEMS]:
        if not isinstance(raw, Mapping):
            continue
        state = _clean(raw.get("support_state"), 40).casefold()
        if state not in allowed_states:
            state = "insufficient_current_evidence"
        claims.append({
            "claim_code": _clean(raw.get("claim_code"), 120),
            "support_state": state,
            "supporting_citations": list(dict.fromkeys(_clean(v, 80) for v in list(raw.get("supporting_citations") or []) if _clean(v, 80)))[:16],
            "refuting_citations": list(dict.fromkeys(_clean(v, 80) for v in list(raw.get("refuting_citations") or []) if _clean(v, 80)))[:16],
            "incomplete_citations": list(dict.fromkeys(_clean(v, 80) for v in list(raw.get("incomplete_citations") or []) if _clean(v, 80)))[:16],
            "stale_citations": list(dict.fromkeys(_clean(v, 80) for v in list(raw.get("stale_citations") or []) if _clean(v, 80)))[:16],
            "independent_source_count": _bounded_count(raw.get("independent_source_count")),
            "independent_lineage_count": _bounded_count(raw.get("independent_lineage_count", raw.get("independent_source_count"))),
            "unique_source_identity_count": _bounded_count(raw.get("unique_source_identity_count")),
            "uncertain_lineage_count": _bounded_count(raw.get("uncertain_lineage_count")),
            "independent_evidence_count": _bounded_count(raw.get("independent_evidence_count")),
            "duplicate_evidence_count": _bounded_count(raw.get("duplicate_evidence_count")),
            "repeated_or_derivative_citation_count": _bounded_count(raw.get("repeated_or_derivative_citation_count", raw.get("duplicate_evidence_count"))),
            "primary_or_authoritative_source_count": _bounded_count(raw.get("primary_or_authoritative_source_count")),
            "max_quality": _bounded_score(raw.get("max_quality")),
            "max_relevance": _bounded_score(raw.get("max_relevance")),
            "contradiction_preserved": bool(raw.get("contradiction_preserved")),
        })

    def _finding_rows(key: str, *, disagreement: bool = False) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for raw in list(source.get(key) or [])[:MAX_REPORT_ITEMS]:
            if not isinstance(raw, Mapping):
                continue
            row = {
                "claim_code": _clean(raw.get("claim_code"), 120),
                "finding": _clean(raw.get("finding"), 320),
                "title": _clean(raw.get("title"), 140),
                "candidate_digest": _hex64(raw.get("candidate_digest")),
                "traceable": bool(raw.get("traceable")),
            }
            if disagreement:
                row["supporting_citations"] = list(dict.fromkeys(_clean(v, 80) for v in list(raw.get("supporting_citations") or []) if _clean(v, 80)))[:16]
                row["refuting_citations"] = list(dict.fromkeys(_clean(v, 80) for v in list(raw.get("refuting_citations") or []) if _clean(v, 80)))[:16]
            else:
                row["stance"] = _clean(raw.get("stance"), 24)
                row["citations"] = list(dict.fromkeys(_clean(v, 80) for v in list(raw.get("citations") or []) if _clean(v, 80)))[:16]
                row["evidence_strength"] = _clean(raw.get("evidence_strength"), 16)
                row["independent_lineage_count"] = _bounded_count(raw.get("independent_lineage_count", raw.get("independent_source_count")))
                row["repeated_or_derivative_citation_count"] = _bounded_count(raw.get("repeated_or_derivative_citation_count"))
                if key == "missing_evidence":
                    row["reason"] = _clean(raw.get("reason"), 160)
            rows.append(row)
        return rows

    sanitized = {
        "contract_version": _clean(source.get("contract_version"), 32),
        "session_id": _clean(source.get("session_id"), 120),
        "session_digest": _hex64(source.get("session_digest")),
        "plan_digest": _hex64(source.get("plan_digest")),
        "decomposition_digest": _hex64(source.get("decomposition_digest")),
        "source_strategy_digest": _hex64(source.get("source_strategy_digest")),
        "status": _clean(source.get("status"), 80),
        "claim_assessments": claims,
        "verified_findings": _finding_rows("verified_findings"),
        "reasonable_inferences": _finding_rows("reasonable_inferences"),
        "unresolved_disagreements": _finding_rows("unresolved_disagreements", disagreement=True),
        "missing_evidence": _finding_rows("missing_evidence"),
        "limitations": [_clean(item, 320) for item in list(source.get("limitations") or [])[:16] if _clean(item, 320)],
        "rendered_answer": _clean(source.get("rendered_answer"), 12000),
        "citations": citations,
        "citation_count": len(citations),
        "contradicted_claim_codes": list(dict.fromkeys(_clean(v, 120) for v in list(source.get("contradicted_claim_codes") or []) if _clean(v, 120)))[:32],
        "source_failure_count": _bounded_count(source.get("source_failure_count")),
        "skipped_unreadable_host_count": _bounded_count(source.get("skipped_unreadable_host_count")),
        "readable_content_failure_count": _bounded_count(source.get("readable_content_failure_count")),
        "source_failure_receipts": sanitize_failures(source.get("source_failure_receipts")),
        "collection_stop_reason": source.get("collection_stop_reason") if source.get("collection_stop_reason") in {
            "source_failure_budget_reached", "time_budget_reached", "page_budget_reached",
            "byte_budget_reached", "planned_collection_finished", "adapter_execution_failed_safely"} else "",
        "generated_prose_is_evidence": False,
        "research_intelligence_version": _clean(source.get("research_intelligence_version"), 32),
        "source_independence_version": _clean(source.get("source_independence_version"), 32),
        "requested_result_count": _bounded_count(source.get("requested_result_count")),
        "synthesis_status": _clean(source.get("synthesis_status"), 100),
        "model_assessment_status": _clean(_assessment_summary.get("status"), 80),
        "model_assessment_denial_reason": _clean(source.get("model_assessment_denial_reason"), 80),
        "evidence_policy_evaluation": _evidence_policy_projection(source.get("evidence_policy_evaluation")),
        "grounded_assessment_count": _bounded_count(_assessment_summary.get("grounded_assessment_count")),
        "omitted_passage_source_count": _bounded_count(_assessment_summary.get("omitted_passage_source_count")),
        "assessment_stance_counts": _count_map(_assessment_summary.get("assessment_stance_counts")),
        "assessment_evidence_kind_counts": _count_map(_assessment_summary.get("assessment_evidence_kind_counts")),
        "rejected_assessment_counts": _count_map(_assessment_summary.get("rejected_assessment_counts")),
        "assessment_selector_diagnostics": _count_map(_assessment_summary.get("selector_diagnostics")),
        "assessment_admission_blockers": _count_map(_assessment_summary.get("admission_blockers")),
        "candidate_discovery_synthesis_status": _clean(source.get("candidate_discovery_synthesis_status"), 100),
        "candidate_follow_up_status": _clean(source.get("candidate_follow_up_status"), 100),
        "candidate_follow_up_plan_digest": _hex64(source.get("candidate_follow_up_plan_digest")),
        "candidate_follow_up_query_count": _bounded_count(source.get("candidate_follow_up_query_count")),
        "candidate_follow_up_completed_query_count": _bounded_count(source.get("candidate_follow_up_completed_query_count")),
        "candidate_follow_up_candidate_count": _bounded_count(source.get("candidate_follow_up_candidate_count")),
        "candidate_follow_up_dimensions": [
            value
            for value in (
                _clean(item, 60)
                for item in list(source.get("candidate_follow_up_dimensions") or [])[:4]
            )
            if value in {"demand", "competition", "implementation_dependencies", "free_tier_feasibility"}
        ],
        "candidate_identity_binding_count": _bounded_count(source.get("candidate_identity_binding_count")),
        "candidate_specificity_limited_count": _bounded_count(source.get("candidate_specificity_limited_count")),
        "candidate_identity_binding_required": bool(source.get("candidate_identity_binding_required")),
        "candidate_specific_coverage_required": bool(source.get("candidate_specific_coverage_required")),
        "candidate_specific_coverage_complete": bool(source.get("candidate_specific_coverage_complete")),
        "candidate_research_matrix_complete": bool(source.get("candidate_research_matrix_complete")),
        "candidate_evidence_matrix": [
            {
                "candidate_digest": _hex64(row.get("candidate_digest")),
                "cells": {
                    dimension: {
                        "matrix_state": (
                            _clean(cell.get("matrix_state"), 48)
                            if _clean(cell.get("matrix_state"), 48) in {
                                "supported", "weak", "contradicted",
                                "researched_with_no_credible_evidence", "not_researched",
                            }
                            else "not_researched"
                        ),
                        "evidence_strength": (
                            _clean(cell.get("evidence_strength"), 16)
                            if _clean(cell.get("evidence_strength"), 16) in {"weak", "moderate", "strong"}
                            else "weak"
                        ),
                        "observed_citation_count": _bounded_count(cell.get("observed_citation_count")),
                        "unique_source_identity_count": _bounded_count(cell.get("unique_source_identity_count")),
                        "independent_lineage_count": _bounded_count(cell.get("independent_lineage_count")),
                        "uncertain_lineage_count": _bounded_count(cell.get("uncertain_lineage_count")),
                        "repeated_or_derivative_citation_count": _bounded_count(cell.get("repeated_or_derivative_citation_count")),
                        "primary_or_authoritative_source_count": _bounded_count(cell.get("primary_or_authoritative_source_count")),
                        "fresh_citation_count": _bounded_count(cell.get("fresh_citation_count")),
                        "stale_citation_count": _bounded_count(cell.get("stale_citation_count")),
                        "supporting_evidence_count": _bounded_count(cell.get("supporting_evidence_count")),
                        "refuting_evidence_count": _bounded_count(cell.get("refuting_evidence_count")),
                        "unresolved_evidence_count": _bounded_count(cell.get("unresolved_evidence_count")),
                    }
                    for dimension, cell in dict(row.get("cells") or {}).items()
                    if dimension in {"demand", "competition", "implementation_dependencies", "free_tier_feasibility"}
                    and isinstance(cell, Mapping)
                },
            }
            for row in list(source.get("candidate_evidence_matrix") or [])[:8]
            if isinstance(row, Mapping) and _hex64(row.get("candidate_digest"))
        ],
        "recommendation_confidence_assessments": [
            {
                "candidate_digest": _hex64(row.get("candidate_digest")),
                "title": _clean(row.get("title"), 140),
                "confidence_label": (
                    _clean(row.get("confidence_label"), 32)
                    if _clean(row.get("confidence_label"), 32) in {"unsupported", "tentative", "moderate-confidence", "high-confidence"}
                    else "unsupported"
                ),
                "threshold_label": _clean(row.get("threshold_label"), 32) or "moderate-confidence",
                "threshold_met": bool(row.get("threshold_met")),
                "reasons": [_clean(value, 240) for value in list(row.get("reasons") or [])[:8] if _clean(value, 240)],
                "observed_citation_count": _bounded_count(row.get("observed_citation_count")),
                "unique_source_identity_count": _bounded_count(row.get("unique_source_identity_count")),
                "independent_lineage_count": _bounded_count(row.get("independent_lineage_count")),
                "uncertain_lineage_count": _bounded_count(row.get("uncertain_lineage_count")),
                "repeated_or_derivative_citation_count": _bounded_count(row.get("repeated_or_derivative_citation_count")),
                "primary_or_authoritative_source_count": _bounded_count(row.get("primary_or_authoritative_source_count")),
            }
            for row in list(source.get("recommendation_confidence_assessments") or [])[:8]
            if isinstance(row, Mapping) and _hex64(row.get("candidate_digest"))
        ],
        "recommendation_confidence_threshold": _clean(source.get("recommendation_confidence_threshold"), 32) or "moderate-confidence",
        "strongest_opportunity_admitted": bool(source.get("strongest_opportunity_admitted")),
        "source_independence_summary": {
            "observed_citation_count": _bounded_count((source.get("source_independence_summary") or {}).get("observed_citation_count")) if isinstance(source.get("source_independence_summary"), Mapping) else 0,
            "unique_source_identity_count": _bounded_count((source.get("source_independence_summary") or {}).get("unique_source_identity_count")) if isinstance(source.get("source_independence_summary"), Mapping) else 0,
            "independent_lineage_count": _bounded_count((source.get("source_independence_summary") or {}).get("independent_lineage_count")) if isinstance(source.get("source_independence_summary"), Mapping) else 0,
            "uncertain_lineage_count": _bounded_count((source.get("source_independence_summary") or {}).get("uncertain_lineage_count")) if isinstance(source.get("source_independence_summary"), Mapping) else 0,
            "repeated_or_derivative_citation_count": _bounded_count((source.get("source_independence_summary") or {}).get("repeated_or_derivative_citation_count")) if isinstance(source.get("source_independence_summary"), Mapping) else 0,
            "primary_or_authoritative_lineage_count": _bounded_count((source.get("source_independence_summary") or {}).get("primary_or_authoritative_lineage_count")) if isinstance(source.get("source_independence_summary"), Mapping) else 0,
            "lineage_digest": _hex64((source.get("source_independence_summary") or {}).get("lineage_digest")) if isinstance(source.get("source_independence_summary"), Mapping) else "",
            "citation_volume_increases_confidence": False,
        },
        "recommendation_deterministic_fallback_used": bool(source.get("recommendation_deterministic_fallback_used")),
        "candidate_identity_exposed_in_public_receipt": False,
        "synthesis_provider_contacted": bool(source.get("synthesis_provider_contacted", source.get("provider_contacted", False))),
        "synthesis_provider_request_count": _bounded_count(source.get("synthesis_provider_request_count", source.get("provider_request_count", 0))),
        "candidate_discovery_retry_used": bool(source.get("candidate_discovery_retry_used")),
        "candidate_discovery_semantic_repair_used": bool(source.get("candidate_discovery_semantic_repair_used")),
        "candidate_discovery_initial_validation_diagnostics": _sanitize_discovery_diagnostics(source.get("candidate_discovery_initial_validation_diagnostics")),
        "candidate_discovery_validation_diagnostics": _sanitize_discovery_diagnostics(source.get("candidate_discovery_validation_diagnostics")),
        "final_synthesis_retry_used": bool(source.get("final_synthesis_retry_used")),
        "private_objective_sent_to_provider": False,
        "material_conclusion_traceability": [
            {
                "claim_code": _clean(row.get("claim_code"), 120),
                "classification": _clean(row.get("classification"), 40),
                "citations": list(dict.fromkeys(_clean(v, 80) for v in list(row.get("citations") or []) if _clean(v, 80)))[:16],
                "evidence_bound": bool(row.get("evidence_bound")),
            }
            for row in list(source.get("material_conclusion_traceability") or [])[:MAX_REPORT_ITEMS]
            if isinstance(row, Mapping)
        ],
        "all_material_conclusions_evidence_bound_or_labeled_inference": bool(source.get("all_material_conclusions_evidence_bound_or_labeled_inference", True)),
        "repeated_source_citation_count": _bounded_count(source.get("repeated_source_citation_count")),
        "repeated_or_derivative_citation_count": _bounded_count(source.get("repeated_or_derivative_citation_count")),
        "independent_lineage_count": _bounded_count(source.get("independent_lineage_count")),
        "uncertain_lineage_count": _bounded_count(source.get("uncertain_lineage_count")),
        "repeated_citations_count_as_independent_confirmation": False,
        "minority_and_contradictory_evidence_preserved": bool(source.get("minority_and_contradictory_evidence_preserved", True)),
        "raw_page_content_persisted": False,
        "raw_query_text_exposed": False,
        "private_objective_exposed": False,
        **_DENIED,
    }
    original_digest = _hex64(source.get("report_digest"))
    if original_digest:
        sanitized["report_digest"] = original_digest
    else:
        sanitized["report_digest"] = _digest({k: v for k, v in sanitized.items() if k != "report_digest"})
    return sanitized


def report_structure_digest(report: Mapping[str, Any] | None) -> str:
    sanitized = sanitize_report(report)
    structure = {
        "report_digest": sanitized.get("report_digest"),
        "claims": sanitized.get("claim_assessments"),
        "citations": [
            {
                "citation_id": row.get("citation_id"),
                "host": row.get("host"),
                "source_kind": row.get("source_kind"),
                "freshness": row.get("freshness"),
                "quality_score": row.get("quality_score"),
                "relevance_score": row.get("relevance_score"),
                "source_digest": row.get("source_digest"),
                "source_identity_digest": row.get("source_identity_digest"),
                "publisher_digest": row.get("publisher_digest"),
                "lineage_digest": row.get("lineage_digest"),
                "independence_state": row.get("independence_state"),
            }
            for row in sanitized.get("citations", [])
        ],
        "candidate_evidence_matrix": sanitized.get("candidate_evidence_matrix"),
        "recommendation_confidence_assessments": sanitized.get("recommendation_confidence_assessments"),
        "recommendation_confidence_threshold": sanitized.get("recommendation_confidence_threshold"),
        "source_independence_summary": sanitized.get("source_independence_summary"),
    }
    return _digest(structure)


def build_history_record(session: Mapping[str, Any], report: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Create one content-free terminal history record bound to exact lineage."""
    state = _clean(session.get("state"), 32).casefold()
    failure_code = _clean(session.get("failure_code"), 120)
    terminal_status = "interrupted" if failure_code == "interrupted_execution_not_replayed" else state
    sanitized = sanitize_report(report)
    citations = list(sanitized.get("citations") or [])
    freshness_counts = {"fresh": 0, "stale": 0, "unknown": 0}
    quality_counts = {"high": 0, "medium": 0, "low": 0, "unknown": 0}
    for row in citations:
        freshness = str(row.get("freshness") or "unknown")
        freshness_counts[freshness if freshness in freshness_counts else "unknown"] += 1
        quality_counts[_quality_band(row.get("quality_score"))] += 1
    report_digest = _hex64(session.get("report_digest")) or _hex64(sanitized.get("report_digest"))
    record = {
        "history_schema_version": HISTORY_SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "session_id": _clean(session.get("session_id"), 120),
        "session_digest": _hex64(session.get("session_digest")),
        "plan_digest": _hex64(session.get("plan_digest")),
        "decomposition_digest": _hex64(session.get("decomposition_digest")),
        "source_strategy_digest": _hex64(session.get("source_strategy_digest")),
        "created_at": _iso(session.get("created_at")),
        "authorized_at": _iso(session.get("authorized_at")),
        "started_at": _iso(session.get("started_at")),
        "completed_at": _iso(session.get("completed_at")),
        "terminal_status": terminal_status if terminal_status in {"completed", "cancelled", "failed", "interrupted"} else "failed",
        "report_digest": report_digest,
        "report_structure_digest": report_structure_digest(sanitized) if report_digest else "",
        "evidence_count": _bounded_count(session.get("evidence_count")),
        "claim_count": _bounded_count(session.get("claim_count")),
        "contradiction_count": _bounded_count(session.get("contradiction_count")),
        "citation_count": len(citations),
        "source_failure_count": _bounded_count(session.get("source_failure_count")),
        "freshness_bands": freshness_counts,
        "quality_bands": quality_counts,
        "source_independence_summary": dict(sanitized.get("source_independence_summary") or {}),
        "recommendation_confidence_threshold": _clean(sanitized.get("recommendation_confidence_threshold"), 32) or "moderate-confidence",
        "recommendation_confidence_labels": [
            {
                "candidate_digest": _hex64(row.get("candidate_digest")),
                "confidence_label": _clean(row.get("confidence_label"), 32),
                "threshold_met": bool(row.get("threshold_met")),
            }
            for row in list(sanitized.get("recommendation_confidence_assessments") or [])[:8]
            if isinstance(row, Mapping) and _hex64(row.get("candidate_digest"))
        ],
        "candidate_matrix_digest": _digest(sanitized.get("candidate_evidence_matrix") or []),
        "candidate_matrix_state_counts": {
            state_name: sum(
                1
                for row in list(sanitized.get("candidate_evidence_matrix") or [])
                for cell in dict(row.get("cells") or {}).values()
                if isinstance(cell, Mapping) and cell.get("matrix_state") == state_name
            )
            for state_name in (
                "supported", "weak", "contradicted",
                "researched_with_no_credible_evidence", "not_researched",
            )
        },
        "failure_code_digest": hashlib.sha256(failure_code.encode("utf-8")).hexdigest() if failure_code else "",
        "private_objective_exposed": False,
        "query_text_exposed": False,
        "raw_page_content_exposed": False,
        "credential_material_exposed": False,
        **_DENIED,
    }
    record["history_record_digest"] = _digest(record)
    return record


def validate_history_record(
    record: Mapping[str, Any] | None,
    *,
    session: Mapping[str, Any] | None = None,
    report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    row = dict(record or {})
    supplied_digest = _hex64(row.pop("history_record_digest", ""))
    digest_valid = bool(supplied_digest) and supplied_digest == _digest(row)
    issues: list[str] = []
    if not digest_valid:
        issues.append("history_record_digest_invalid")
    if _contains_private_key(row):
        issues.append("private_history_field_detected")
    source = dict(session or {})
    if source:
        for key in ("session_id", "session_digest", "plan_digest", "decomposition_digest", "source_strategy_digest", "report_digest"):
            expected = _clean(source.get(key), 180).casefold()
            actual = _clean(row.get(key), 180).casefold()
            if expected and actual != expected:
                issues.append(f"history_{key}_stale")
    sanitized = sanitize_report(report) if report else {}
    if sanitized:
        expected_report = _hex64(sanitized.get("report_digest"))
        if expected_report and _hex64(row.get("report_digest")) != expected_report:
            issues.append("history_report_digest_stale")
        if expected_report and _hex64(row.get("report_structure_digest")) != report_structure_digest(sanitized):
            issues.append("history_report_structure_stale")
    return {
        "ok": not issues,
        "status": "research_history_record_valid" if not issues else "research_history_record_invalid",
        "history_record_digest": supplied_digest,
        "digest_valid": digest_valid,
        "issues": sorted(set(issues)),
        "silent_repair_performed": False,
        **_DENIED,
    }


def compare_reports(
    left_record: Mapping[str, Any],
    left_report: Mapping[str, Any],
    right_record: Mapping[str, Any],
    right_report: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare bounded evidence structure without web contact or winner ranking."""
    left = sanitize_report(left_report)
    right = sanitize_report(right_report)
    left_claims = {str(row.get("claim_code") or ""): row for row in left.get("claim_assessments", []) if row.get("claim_code")}
    right_claims = {str(row.get("claim_code") or ""): row for row in right.get("claim_assessments", []) if row.get("claim_code")}
    left_cites = {str(row.get("citation_id") or ""): row for row in left.get("citations", []) if row.get("citation_id")}
    right_cites = {str(row.get("citation_id") or ""): row for row in right.get("citations", []) if row.get("citation_id")}

    added_claims = sorted(set(right_claims) - set(left_claims))
    removed_claims = sorted(set(left_claims) - set(right_claims))
    changed_claims: list[dict[str, Any]] = []
    stale_claims: list[str] = []
    contradictory_claims: list[str] = []
    duplicated_claims: list[str] = []
    unsupported_claims: list[str] = []
    for code in sorted(set(left_claims) & set(right_claims)):
        a, b = left_claims[code], right_claims[code]
        if _digest(a) != _digest(b):
            changed_claims.append({
                "claim_code": code,
                "left_state": a.get("support_state"),
                "right_state": b.get("support_state"),
                "left_independent_source_count": _bounded_count(a.get("independent_source_count")),
                "right_independent_source_count": _bounded_count(b.get("independent_source_count")),
                "left_independent_lineage_count": _bounded_count(a.get("independent_lineage_count", a.get("independent_source_count"))),
                "right_independent_lineage_count": _bounded_count(b.get("independent_lineage_count", b.get("independent_source_count"))),
                "left_duplicate_evidence_count": _bounded_count(a.get("duplicate_evidence_count")),
                "right_duplicate_evidence_count": _bounded_count(b.get("duplicate_evidence_count")),
            })
        if a.get("stale_citations") or b.get("stale_citations"):
            stale_claims.append(code)
        if a.get("support_state") == "conflicted" or b.get("support_state") == "conflicted":
            contradictory_claims.append(code)
        if _bounded_count(a.get("duplicate_evidence_count")) or _bounded_count(b.get("duplicate_evidence_count")):
            duplicated_claims.append(code)
        if a.get("support_state") == "insufficient_current_evidence" or b.get("support_state") == "insufficient_current_evidence":
            unsupported_claims.append(code)

    added_sources = sorted(set(right_cites) - set(left_cites))
    removed_sources = sorted(set(left_cites) - set(right_cites))
    changed_sources = sorted(
        cid for cid in set(left_cites) & set(right_cites)
        if _digest(left_cites[cid]) != _digest(right_cites[cid])
    )
    meaningful = bool(left_claims or right_claims) and bool(left.get("report_digest")) and bool(right.get("report_digest"))
    reason = "" if meaningful else "One or both sessions lack digest-bound evidence summaries."
    left_confidence = {
        _hex64(row.get("candidate_digest")): _clean(row.get("confidence_label"), 32)
        for row in list(left.get("recommendation_confidence_assessments") or [])
        if isinstance(row, Mapping) and _hex64(row.get("candidate_digest"))
    }
    right_confidence = {
        _hex64(row.get("candidate_digest")): _clean(row.get("confidence_label"), 32)
        for row in list(right.get("recommendation_confidence_assessments") or [])
        if isinstance(row, Mapping) and _hex64(row.get("candidate_digest"))
    }
    changed_confidence = [
        {
            "candidate_digest": candidate_digest,
            "left_confidence": left_confidence.get(candidate_digest, "missing"),
            "right_confidence": right_confidence.get(candidate_digest, "missing"),
        }
        for candidate_digest in sorted(set(left_confidence) | set(right_confidence))
        if left_confidence.get(candidate_digest) != right_confidence.get(candidate_digest)
    ]
    result = {
        "ok": meaningful,
        "status": "research_sessions_compared" if meaningful else "research_sessions_not_meaningfully_comparable",
        "contract_version": CONTRACT_VERSION,
        "left_session_id": _clean(left_record.get("session_id"), 120),
        "right_session_id": _clean(right_record.get("session_id"), 120),
        "left_session_digest": _hex64(left_record.get("session_digest")),
        "right_session_digest": _hex64(right_record.get("session_digest")),
        "left_report_digest": _hex64(left.get("report_digest")),
        "right_report_digest": _hex64(right.get("report_digest")),
        "added_claim_codes": added_claims,
        "removed_claim_codes": removed_claims,
        "changed_claims": changed_claims,
        "added_citation_ids": added_sources,
        "removed_citation_ids": removed_sources,
        "changed_citation_ids": changed_sources,
        "stale_claim_codes": sorted(set(stale_claims)),
        "contradictory_claim_codes": sorted(set(contradictory_claims)),
        "duplicated_claim_codes": sorted(set(duplicated_claims)),
        "unsupported_claim_codes": sorted(set(unsupported_claims)),
        "changed_recommendation_confidence": changed_confidence,
        "left_source_independence_summary": dict(left.get("source_independence_summary") or {}),
        "right_source_independence_summary": dict(right.get("source_independence_summary") or {}),
        "left_candidate_matrix_digest": _digest(left.get("candidate_evidence_matrix") or []),
        "right_candidate_matrix_digest": _digest(right.get("candidate_evidence_matrix") or []),
        "source_independence_preserved": True,
        "automatic_winner_declared": False,
        "comparison_reason": reason,
        "private_objective_exposed": False,
        "raw_page_content_exposed": False,
        "raw_query_text_exposed": False,
        **_DENIED,
    }
    result["comparison_digest"] = _digest({k: v for k, v in result.items() if k != "comparison_digest"})
    return result


def _citation_map(report: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {str(row.get("citation_id") or ""): row for row in report.get("citations", []) if isinstance(row, Mapping) and row.get("citation_id")}


def render_markdown_export(session_id: str, report: Mapping[str, Any]) -> dict[str, Any]:
    """Build one local Markdown export payload without writing or transmitting it."""
    sanitized = sanitize_report(report)
    sid = _clean(session_id, 120)
    report_digest = _hex64(sanitized.get("report_digest"))
    if not sid or not report_digest:
        return {"ok": False, "status": "completed_digest_bound_report_required", **_DENIED}
    citations = _citation_map(sanitized)

    lines = [
        "# Eidolon bounded research report",
        "",
        f"- Session ID: `{sid}`",
        f"- Report digest: `{report_digest}`",
        f"- Export schema: `{EXPORT_SCHEMA_VERSION}`",
        "",
    ]
    answer = _clean(sanitized.get("rendered_answer"), 12000)
    if answer:
        lines.extend(["## Synthesis", "", answer, ""])

    confidence_rows = list(sanitized.get("recommendation_confidence_assessments") or [])
    if confidence_rows:
        lines.extend(["## Recommendation confidence", ""])
        lines.append(f"Configured strongest-opportunity threshold: `{sanitized.get('recommendation_confidence_threshold') or 'moderate-confidence'}`")
        lines.append("")
        for row in confidence_rows:
            label = _clean(row.get("title"), 140) or ("candidate " + _hex64(row.get("candidate_digest"))[:12])
            confidence = _clean(row.get("confidence_label"), 32) or "unsupported"
            reasons = "; ".join(_clean(value, 240) for value in list(row.get("reasons") or [])[:4] if _clean(value, 240))
            suffix = f" — {reasons}" if reasons else ""
            lines.append(f"- **{label}**: `{confidence}`{suffix}")
        lines.append("")

    matrix_rows = list(sanitized.get("candidate_evidence_matrix") or [])
    if matrix_rows:
        title_by_digest = {
            _hex64(row.get("candidate_digest")): _clean(row.get("title"), 140)
            for row in confidence_rows
            if _hex64(row.get("candidate_digest"))
        }
        lines.extend(["## Candidate evidence matrix", ""])
        lines.append("| Candidate | Demand | Competition | Implementation dependencies | Free-tier feasibility |")
        lines.append("| --- | --- | --- | --- | --- |")
        for row in matrix_rows:
            candidate_digest = _hex64(row.get("candidate_digest"))
            label = title_by_digest.get(candidate_digest) or ("candidate " + candidate_digest[:12])
            cells = dict(row.get("cells") or {})
            values = []
            for dimension in ("demand", "competition", "implementation_dependencies", "free_tier_feasibility"):
                cell = dict(cells.get(dimension) or {})
                values.append(
                    f"{cell.get('matrix_state') or 'not_researched'} "
                    f"({int(cell.get('independent_lineage_count') or 0)} independent)"
                )
            lines.append("| " + " | ".join([label] + values) + " |")
        lines.append("")

    sections = (
        ("Verified findings", "verified_findings"),
        ("Reasonable inferences", "reasonable_inferences"),
        ("Unresolved disagreement", "unresolved_disagreements"),
        ("Evidence gaps", "missing_evidence"),
    )
    for title, key in sections:
        rows = list(sanitized.get(key) or [])
        if not rows:
            continue
        lines.extend([f"## {title}", ""])
        for row in rows:
            finding = _clean(row.get("finding"), 320) or _clean(row.get("claim_code"), 120) or "Unnamed claim"
            if key == "unresolved_disagreements":
                refs = list(row.get("supporting_citations") or []) + list(row.get("refuting_citations") or [])
            else:
                refs = list(row.get("citations") or [])
            refs = list(dict.fromkeys(str(v) for v in refs if str(v)))
            suffix = f" [{', '.join(refs)}]" if refs else ""
            prefix = "Inference: " if key == "reasonable_inferences" else ""
            reason = f" ({_clean(row.get('reason'), 160)})" if key == "missing_evidence" and row.get("reason") else ""
            lines.append(f"- {prefix}{finding}{reason}{suffix}")
        lines.append("")

    if citations:
        lines.extend(["## Sanitized citations", ""])
        for cid in sorted(citations):
            row = citations[cid]
            lines.append(
                f"- `{cid}`: {row.get('public_url')} | {row.get('source_kind')} | "
                f"freshness={row.get('freshness')} | quality={_quality_band(row.get('quality_score'))} | "
                f"lineage={str(row.get('lineage_digest') or '')[:12]} | independence={row.get('independence_state') or 'unknown'}"
            )
        lines.append("")

    limitations = list(sanitized.get("limitations") or [])
    if limitations:
        lines.extend(["## Material limitations", ""])
        lines.extend(f"- {_clean(item, 320)}" for item in limitations)
        lines.append("")

    lines.extend([
        "## Authority and privacy boundary",
        "",
        "This export is a local, operator-requested projection. It does not upload, post, message, authenticate, purchase, or grant standing research authority.",
        "Raw objectives, search queries, page bodies, credentials, cookies, provider payloads, stack traces, and private filesystem paths are excluded.",
        "",
    ])
    body_without_digest = "\n".join(lines).rstrip() + "\n"
    body_digest = hashlib.sha256(body_without_digest.encode("utf-8")).hexdigest()
    export_digest = _digest({
        "session_id": sid,
        "report_digest": report_digest,
        "export_schema_version": EXPORT_SCHEMA_VERSION,
        "body_digest": body_digest,
    })
    header = f"<!-- export_digest: {export_digest} -->\n"
    markdown = header + body_without_digest
    return {
        "ok": True,
        "status": "bounded_research_markdown_export_ready",
        "contract_version": CONTRACT_VERSION,
        "session_id": sid,
        "report_digest": report_digest,
        "export_schema_version": EXPORT_SCHEMA_VERSION,
        "body_digest": body_digest,
        "export_digest": export_digest,
        "markdown": markdown,
        "byte_count": len(markdown.encode("utf-8")),
        "uploaded": False,
        "transmitted": False,
        "private_fields_excluded": True,
        **_DENIED,
    }


__all__ = [
    "CONTRACT_VERSION",
    "HISTORY_SCHEMA_VERSION",
    "EXPORT_SCHEMA_VERSION",
    "MAX_HISTORY_RECORDS",
    "sanitize_report",
    "report_structure_digest",
    "build_history_record",
    "validate_history_record",
    "compare_reports",
    "render_markdown_export",
]
