from __future__ import annotations

"""Conversation-facing controls for bounded, read-only research sessions.

This module translates exact operator phrases into the existing v2501.9
research lifecycle. It does not add a second authority model: creation remains
provider-free, one exact confirmation authorizes the whole GET/HEAD-only
session, and execution remains exactly-once inside the research store.
"""

import hashlib
import ipaddress
import json
import math
import re
from typing import Any, Mapping
from urllib.parse import urlsplit

try:
    from bounded_autonomous_web_research import BoundedResearchSessionStore
    from governed_public_web_research_adapter import GovernedPublicWebResearchAdapter
except ImportError:
    from bounded_autonomous_web_research import BoundedResearchSessionStore
    from governed_public_web_research_adapter import GovernedPublicWebResearchAdapter


CONTRACT_VERSION = "v2503.3"
RESEARCH_FUNCTIONS = frozenset({
    "research_session_create",
    "research_session_authorize_execute",
    "research_session_cancel",
    "research_session_status",
    "research_history_list",
    "research_sessions_compare",
    "research_report_export",
})

_CREATE = re.compile(
    r"^(?:please\s+)?research\s+(.+?)"
    r"(?:\s+and\s+(?:come\s+back|return)\s+with\s+(?:a\s+)?(?:cited\s+)?(?:report|evidence))?\s*[.!?]*$",
    re.I,
)
_AUTHORIZE = re.compile(
    r"^Authorize research session (research-[0-9a-f]{24}) digest ([0-9a-f]{64})\.?$",
    re.I,
)
_CANCEL = re.compile(
    r"^Cancel research session (research-[0-9a-f]{24}) digest ([0-9a-f]{64})\.?$",
    re.I,
)
_STATUS = re.compile(
    r"^(?:Show|Inspect|Check)(?: the)? research status(?: for session (research-[0-9a-f]{24}))?\.?$",
    re.I,
)
_HISTORY = re.compile(
    r"^(?:Show|Inspect|List)(?: the)? research history\.?$",
    re.I,
)
_COMPARE = re.compile(
    r"^Compare research sessions (research-[0-9a-f]{24}) digest ([0-9a-f]{64}) and (research-[0-9a-f]{24}) digest ([0-9a-f]{64})\.?$",
    re.I,
)
_EXPORT = re.compile(
    r"^Export research session (research-[0-9a-f]{24}) digest ([0-9a-f]{64}) as Markdown\.?$",
    re.I,
)
_REQUESTED_SIDE_EFFECT = re.compile(
    r"\b(?:and|then)\s+(?:post|publish|upload|message|email|buy|purchase|order|create\s+(?:an?\s+)?account|log\s*in|sign\s*in)\b",
    re.I,
)


def parse_conversational_research_request(message: str) -> dict[str, Any] | None:
    """Recognize only explicit research controls; casual mentions stay conversational."""
    request = " ".join(str(message or "").split()).strip()
    match = _AUTHORIZE.fullmatch(request)
    if match:
        return {
            "intent": "bounded_research_authorize_execute",
            "function_name": "research_session_authorize_execute",
            "function_args": {"session_id": match.group(1).lower(), "session_digest": match.group(2).lower()},
        }
    match = _CANCEL.fullmatch(request)
    if match:
        return {
            "intent": "bounded_research_cancel",
            "function_name": "research_session_cancel",
            "function_args": {"session_id": match.group(1).lower(), "session_digest": match.group(2).lower()},
        }
    match = _HISTORY.fullmatch(request)
    if match:
        return {
            "intent": "bounded_research_history",
            "function_name": "research_history_list",
            "function_args": {},
        }
    match = _COMPARE.fullmatch(request)
    if match:
        return {
            "intent": "bounded_research_compare",
            "function_name": "research_sessions_compare",
            "function_args": {
                "left_session_id": match.group(1).lower(),
                "left_session_digest": match.group(2).lower(),
                "right_session_id": match.group(3).lower(),
                "right_session_digest": match.group(4).lower(),
            },
        }
    match = _EXPORT.fullmatch(request)
    if match:
        return {
            "intent": "bounded_research_export",
            "function_name": "research_report_export",
            "function_args": {"session_id": match.group(1).lower(), "session_digest": match.group(2).lower()},
        }
    match = _STATUS.fullmatch(request)
    if match:
        return {
            "intent": "bounded_research_status",
            "function_name": "research_session_status",
            "function_args": {"session_id": str(match.group(1) or "").lower()},
        }
    match = _CREATE.fullmatch(request)
    if not match:
        return None
    objective = str(match.group(1) or "").strip(" .!?")
    if not objective:
        return None
    if _REQUESTED_SIDE_EFFECT.search(objective):
        return {
            "intent": "bounded_research_side_effect_blocked",
            "function_name": "",
            "function_args": {},
            "blocked": True,
        }
    return {
        "intent": "bounded_research_create",
        "function_name": "research_session_create",
        "function_args": {"objective": objective},
    }


def _authorization_phrase(session: Mapping[str, Any]) -> str:
    return (
        f"Authorize research session {session.get('session_id')} "
        f"digest {session.get('session_digest')}."
    )


def _public_session_fields(session: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {
        "session_id", "session_digest", "state", "progress_stage", "progress_percent",
        "budget", "budget_remaining", "query_count", "candidate_count", "observed_page_count",
        "observed_bytes", "evidence_count", "claim_count", "contradiction_count",
        "citation_count", "report_digest", "stop_reason", "failure_code", "source_failure_count",
    }
    return {key: session.get(key) for key in allowed if key in session}


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


def _bounded_score(value: object) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    if not math.isfinite(score):
        return 0.0
    return round(max(0.0, min(1.0, score)), 4)


def _bounded_count(value: object) -> int:
    try:
        return max(0, min(1_000_000, int(value)))
    except (TypeError, ValueError, OverflowError):
        return 0


def _score_band(value: object) -> str:
    score = _bounded_score(value)
    if score >= 0.75:
        return "high"
    if score >= 0.5:
        return "medium"
    if score > 0:
        return "low"
    return "unknown"


def _safe_public_url(value: object) -> tuple[str, str]:
    raw = str(value or "").strip()[:2048]
    try:
        parsed = urlsplit(raw)
    except Exception:
        return "", ""
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        return "", ""
    host = parsed.hostname.casefold().rstrip(".")[:255]
    return f"{parsed.scheme}://{host}{parsed.path or '/'}", host


def conversational_research_review(action: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Project one completed report into a bounded, privacy-safe evidence review."""
    action = action or {}
    if str(action.get("function_name") or "") != "research_session_authorize_execute":
        return None
    if str(action.get("status") or "").casefold() != "completed":
        return None
    result = action.get("result") if isinstance(action.get("result"), Mapping) else {}
    if not result.get("ok", True):
        return None
    report = result.get("report") if isinstance(result.get("report"), Mapping) else {}
    report_digest = str(report.get("report_digest") or "").casefold()
    if not re.fullmatch(r"[0-9a-f]{64}", report_digest):
        return None
    if str(result.get("report_digest") or "").casefold() != report_digest:
        return None
    digest_payload = {key: value for key, value in report.items() if key != "report_digest"}
    if _digest(digest_payload) != report_digest:
        return None

    citations: list[dict[str, Any]] = []
    quality_counts = {"high": 0, "medium": 0, "low": 0, "unknown": 0}
    freshness_counts = {"fresh": 0, "stale": 0, "unknown": 0}
    seen: set[str] = set()
    for raw in list(report.get("citations") or [])[:32]:
        if not isinstance(raw, Mapping):
            continue
        citation_id = str(raw.get("citation_id") or "").strip()[:80]
        if not citation_id or citation_id in seen:
            continue
        seen.add(citation_id)
        public_url, derived_host = _safe_public_url(raw.get("public_url"))
        if not public_url:
            continue
        quality_score = _bounded_score(raw.get("quality_score"))
        relevance_score = _bounded_score(raw.get("relevance_score"))
        quality = _score_band(quality_score)
        freshness = str(raw.get("freshness") or "unknown").casefold()
        freshness = freshness if freshness in freshness_counts else "unknown"
        source_kind = str(raw.get("source_kind") or "unknown").casefold()
        source_kind = source_kind if re.fullmatch(r"[a-z][a-z0-9_-]{0,59}", source_kind) else "unknown"
        source_digest = str(raw.get("source_digest") or "").casefold()
        source_digest = source_digest if re.fullmatch(r"[0-9a-f]{64}", source_digest) else ""
        quality_counts[quality] += 1
        freshness_counts[freshness] += 1
        citations.append({
            "citation_id": citation_id,
            "public_url": public_url,
            "host": derived_host,
            "source_kind": source_kind,
            "quality": quality,
            "quality_score": quality_score,
            "relevance_score": relevance_score,
            "freshness": freshness,
            "source_digest": source_digest,
            "source_identity_digest": str(raw.get("source_identity_digest") or "")[:64].casefold(),
            "canonical_page_digest": str(raw.get("canonical_page_digest") or "")[:64].casefold(),
            "publisher_digest": str(raw.get("publisher_digest") or "")[:64].casefold(),
            "lineage_digest": str(raw.get("lineage_digest") or "")[:64].casefold(),
            "independence_state": str(raw.get("independence_state") or "independent")[:24].casefold(),
            "authoritative_source": bool(raw.get("authoritative_source")),
        })
        if len(citations) >= 12:
            break

    claims: list[dict[str, Any]] = []
    allowed_states = {"supported", "refuted", "conflicted", "insufficient_current_evidence"}
    for raw in list(report.get("claim_assessments") or [])[:16]:
        if not isinstance(raw, Mapping):
            continue
        state = str(raw.get("support_state") or "insufficient_current_evidence").casefold()
        state = state if state in allowed_states else "insufficient_current_evidence"
        claims.append({
            "claim_code": str(raw.get("claim_code") or "")[:120],
            "state": state,
            "independent_source_count": _bounded_count(raw.get("independent_source_count")),
            "independent_lineage_count": _bounded_count(raw.get("independent_lineage_count") or raw.get("independent_source_count")),
            "unique_source_identity_count": _bounded_count(raw.get("unique_source_identity_count")),
            "uncertain_lineage_count": _bounded_count(raw.get("uncertain_lineage_count")),
            "repeated_or_derivative_citation_count": _bounded_count(raw.get("repeated_or_derivative_citation_count") or raw.get("duplicate_evidence_count")),
            "independent_evidence_count": _bounded_count(raw.get("independent_evidence_count")),
            "duplicate_evidence_count": _bounded_count(raw.get("duplicate_evidence_count")),
            "quality": _score_band(raw.get("max_quality")),
            "relevance": _score_band(raw.get("max_relevance")),
            "citation_ids": list(dict.fromkeys(
                str(value)[:80]
                for key in ("supporting_citations", "refuting_citations", "incomplete_citations", "stale_citations")
                for value in list(raw.get(key) or [])
                if str(value).strip()
            ))[:12],
        })

    review = {
        "contract_version": CONTRACT_VERSION,
        "status": str(report.get("status") or "research_report_ready")[:80],
        "report_digest": report_digest,
        "citation_count": _bounded_count(report.get("citation_count") or len(citations)),
        "displayed_citation_count": len(citations),
        "verified_count": len(list(report.get("verified_findings") or [])),
        "inference_count": len(list(report.get("reasonable_inferences") or [])),
        "disagreement_count": len(list(report.get("unresolved_disagreements") or [])),
        "missing_evidence_count": len(list(report.get("missing_evidence") or [])),
        "source_failure_count": _bounded_count(report.get("source_failure_count")),
        "repeated_source_citation_count": _bounded_count(report.get("repeated_source_citation_count")),
        "repeated_or_derivative_citation_count": _bounded_count(report.get("repeated_or_derivative_citation_count")),
        "independent_lineage_count": _bounded_count(report.get("independent_lineage_count")),
        "uncertain_lineage_count": _bounded_count(report.get("uncertain_lineage_count")),
        "source_independence_summary": dict(report.get("source_independence_summary") or {}),
        "recommendation_confidence_threshold": str(report.get("recommendation_confidence_threshold") or "moderate-confidence")[:40],
        "strongest_opportunity_admitted": bool(report.get("strongest_opportunity_admitted")),
        "recommendation_confidence_assessments": [dict(row) for row in list(report.get("recommendation_confidence_assessments") or [])[:8] if isinstance(row, Mapping)],
        "candidate_evidence_matrix": [dict(row) for row in list(report.get("candidate_evidence_matrix") or [])[:8] if isinstance(row, Mapping)],
        "all_material_conclusions_evidence_bound_or_labeled_inference": bool(report.get("all_material_conclusions_evidence_bound_or_labeled_inference", True)),
        "minority_and_contradictory_evidence_preserved": bool(report.get("minority_and_contradictory_evidence_preserved", True)),
        "quality_counts": quality_counts,
        "freshness_counts": freshness_counts,
        "citations": citations,
        "claims": claims,
        "generated_prose_is_evidence": False,
        "raw_page_content_exposed": False,
        "raw_query_text_exposed": False,
        "private_objective_exposed": False,
        "review_network_contacted": False,
        "review_runtime_mutated": False,
        "installation_authorized": False,
        "promotion_authorized": False,
        "authority_expanded": False,
    }
    review["review_digest"] = _digest(review)
    return review


def conversational_research_history(action: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Project a persisted content-free history catalog from an executed history action."""
    action = action or {}
    if str(action.get("function_name") or "") != "research_history_list":
        return None
    if str(action.get("status") or "").casefold() not in {"completed", "executed"}:
        return None
    result = action.get("result") if isinstance(action.get("result"), Mapping) else {}
    history = result.get("history") if isinstance(result.get("history"), Mapping) else {}
    rows = [dict(row) for row in list(history.get("sessions") or [])[:64] if isinstance(row, Mapping)]
    return {
        "contract_version": CONTRACT_VERSION,
        "history_count": len(rows),
        "sessions": rows,
        "missing_records": [dict(row) for row in list(history.get("missing_records") or [])[:32] if isinstance(row, Mapping)],
        "store_revision": _bounded_count(history.get("store_revision")),
        "integrity_ok": bool(history.get("ok")),
        "network_contacted": False,
        "private_objective_exposed": False,
        "raw_query_text_exposed": False,
        "raw_page_content_exposed": False,
        "authority_expanded": False,
    }


def conversational_research_comparison(action: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Project one persisted content-free comparison result."""
    action = action or {}
    if str(action.get("function_name") or "") != "research_sessions_compare":
        return None
    if str(action.get("status") or "").casefold() not in {"completed", "executed"}:
        return None
    result = action.get("result") if isinstance(action.get("result"), Mapping) else {}
    comparison = result.get("comparison") if isinstance(result.get("comparison"), Mapping) else {}
    if not comparison:
        return None
    allowed = {
        "status", "left_session_id", "right_session_id", "left_session_digest", "right_session_digest",
        "left_report_digest", "right_report_digest", "added_claim_codes", "removed_claim_codes",
        "changed_claims", "added_citation_ids", "removed_citation_ids", "changed_citation_ids",
        "stale_claim_codes", "contradictory_claim_codes", "duplicated_claim_codes",
        "unsupported_claim_codes", "source_independence_preserved", "automatic_winner_declared",
        "changed_recommendation_confidence", "left_source_independence_summary", "right_source_independence_summary",
        "left_candidate_matrix_digest", "right_candidate_matrix_digest", "comparison_reason", "comparison_digest"
    }
    projected = {key: comparison.get(key) for key in allowed if key in comparison}
    projected.update({
        "contract_version": CONTRACT_VERSION, "network_contacted": False, "private_objective_exposed": False,
        "raw_query_text_exposed": False, "raw_page_content_exposed": False, "authority_expanded": False,
    })
    return projected


def conversational_research_export(action: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Project one explicit local export receipt without exposing its private runtime path."""
    action = action or {}
    if str(action.get("function_name") or "") != "research_report_export":
        return None
    if str(action.get("status") or "").casefold() not in {"completed", "executed"}:
        return None
    result = action.get("result") if isinstance(action.get("result"), Mapping) else {}
    receipt = result.get("export") if isinstance(result.get("export"), Mapping) else {}
    if not receipt:
        return None
    return {
        "contract_version": CONTRACT_VERSION,
        "session_id": str(receipt.get("session_id") or "")[:120],
        "session_digest": str(receipt.get("session_digest") or "")[:64].casefold(),
        "report_digest": str(receipt.get("report_digest") or "")[:64].casefold(),
        "export_schema_version": str(receipt.get("export_schema_version") or "")[:24],
        "export_digest": str(receipt.get("export_digest") or "")[:64].casefold(),
        "export_byte_count": _bounded_count(receipt.get("export_byte_count")),
        "file_name": str(receipt.get("file_name") or "")[:180],
        "local_runtime_export": bool(receipt.get("local_runtime_export")),
        "uploaded": False, "transmitted": False, "private_path_exposed": False,
        "network_contacted": False, "private_objective_exposed": False, "raw_query_text_exposed": False,
        "raw_page_content_exposed": False, "authority_expanded": False,
    }


def conversational_research_progress(
    action: Mapping[str, Any] | None,
    *,
    store: BoundedResearchSessionStore | None = None,
) -> dict[str, Any] | None:
    """Project live, content-free progress for one exact research execution action."""
    action = action or {}
    if str(action.get("function_name") or "") != "research_session_authorize_execute":
        return None
    args = action.get("function_args") if isinstance(action.get("function_args"), Mapping) else {}
    session_id = str(args.get("session_id") or "")
    session_digest = str(args.get("session_digest") or "")
    if not session_id or not session_digest:
        return None
    inspected = (store or BoundedResearchSessionStore()).inspect_session(
        session_id,
        session_digest=session_digest,
    )
    if not inspected.get("ok"):
        return None
    session = _public_session_fields(dict(inspected.get("session") or {}))
    state = str(session.get("state") or "unknown")
    return session | {
        "store_revision": max(0, int(inspected.get("store_revision") or 0)),
        "cancellable": state in {"awaiting_session_authorization", "authorized", "running"},
        "terminal": state in {"completed", "failed", "cancelled"},
        "reconnect_policy": "rehydrate_same_session_without_replay",
        "restart_policy": "fail_closed_without_external_request_replay",
        "content_free": True,
    }


def cancel_research_for_conversation_operation(
    action: Mapping[str, Any] | None,
    *,
    event_id: str,
    store: BoundedResearchSessionStore | None = None,
) -> dict[str, Any] | None:
    """Cancel only the exact research session bound to a running conversation action."""
    action = action or {}
    if str(action.get("function_name") or "") != "research_session_authorize_execute":
        return None
    args = action.get("function_args") if isinstance(action.get("function_args"), Mapping) else {}
    session_id = str(args.get("session_id") or "")
    session_digest = str(args.get("session_digest") or "")
    if not session_id or not session_digest:
        return {"ok": False, "status": "exact_research_session_required", "network_contacted": False}
    return execute_conversational_research_action(
        "research_session_cancel",
        {"session_id": session_id, "session_digest": session_digest},
        event_id=event_id,
        store=store,
    )


def _source_assessment_review_lines(report: Mapping[str, Any]) -> list[str]:
    """Explain bounded assessment receipts without upgrading model judgments."""
    from research_source_independence import source_evidence_role
    summary = report.get("source_assessment_summary")
    if not isinstance(summary, Mapping):
        return []
    sources = {str(row.get("citation_id") or ""): row
               for row in list(report.get("citations") or [])[:64] if isinstance(row, Mapping)}
    kinds = {"survey_result": "survey material", "customer_experience": "customer experience",
             "usage_measurement": "usage measurement", "vendor_offering": "vendor offering",
             "unknown": "unclassified material"}
    stances = {"supports": "marked support, not independently verified",
               "refutes": "marked contradiction, not independently verified",
               "unclear": "did not establish the proposed claim"}
    lines = []
    seen = set()
    for row in list(summary.get("assessments") or [])[:32]:
        if not isinstance(row, Mapping) or not row.get("textual_provenance_verified"):
            continue
        cid = str(row.get("citation_id") or "")
        source = sources.get(cid)
        if not source or cid in seen or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", cid):
            continue
        public_url, host = _safe_public_url(source.get("public_url"))
        try:
            public_host = ipaddress.ip_address(host).is_global
        except ValueError:
            public_host = bool(host and "." in host and not host.endswith((".local", ".localhost")))
        if (not public_url or not public_host
                or source_evidence_role(source)["evidence_role"] == "invalid_public_url"):
            continue
        stance = stances.get(row.get("model_assessment"))
        if not stance:
            continue
        seen.add(cid)
        freshness = source.get("freshness")
        currency = "recorded as stale" if freshness == "stale" else (
            "currentness recorded" if freshness == "fresh" else "currentness unverified")
        from datetime import date
        reported_dates = []
        for value in (summary.get("source_reported_publication_dates") or {}).get(cid, [])[:2]:
            try:
                reported_dates.append(date.fromisoformat(str(value)).isoformat())
            except ValueError:
                continue
        if reported_dates:
            currency = "source-reported publication date: " + ", ".join(reported_dates) + "; " + currency
        lines.append(f"- [{cid}] Model classification: {kinds.get(row.get('model_evidence_kind'), kinds['unknown'])}; "
                     f"{stance}; {currency}.")
        if len(lines) == 6:
            break
    if not lines:
        return []
    return ["", "Source assessment review (model judgments, not verified findings):", *lines,
            "Still required: verify the claim against the source, its date, and independent origin. "
            "Related market activity alone does not establish demand for the proposed product."]


def _research_report_message(session: Mapping[str, Any], report: Mapping[str, Any]) -> str:
    session_id = str(session.get("session_id") or "the bounded session")
    answer = str(report.get("rendered_answer") or "").strip()
    citations = [dict(row) for row in report.get("citations", []) if isinstance(row, Mapping)][:12]
    report_ready = str(report.get("status") or "") == "research_report_ready"
    if report_ready:
        lines = [f"I completed bounded read-only research session {session_id}."]
    else:
        lines = [
            f"I completed bounded collection for research session {session_id}, but I did not produce a trustworthy answer to the requested objective."
        ]
        synthesis_status = str(report.get("synthesis_status") or "")
        if synthesis_status in {"research_synthesis_generation_invalid", "research_synthesis_generation_failed"}:
            lines.append("The configured model did not return a valid structured synthesis, so no recommendation should be inferred from the sources below.")
    if answer:
        lines.extend(["", answer])
    elif not report_ready:
        for limitation in list(report.get("limitations") or [])[:4]:
            lines.append(str(limitation)[:600])
    assessments = report.get("source_assessment_summary") or {}
    stop_labels = {"adapter_execution_failed_safely": "execution failed safely", "source_failure_budget_reached": "source-failure limit reached",
                   "time_budget_reached": "time limit reached", "page_budget_reached": "page limit reached",
                   "byte_budget_reached": "download limit reached", "planned_collection_finished": "planned collection finished",
                   "no_search_results": "the search returned no results",
                   "search_results_unavailable": "the search engine did not return a results page",
                   "no_readable_source_observed": "no source found could be read"}
    if report.get("collection_stop_reason") in stop_labels:
        lines.append("Collection stopped: " + stop_labels[report["collection_stop_reason"]] + ".")
    from research_failure_receipts import sanitize_failures
    for failure in sanitize_failures(report.get("source_failure_receipts"))[:8]:
        target = failure['public_url'] or ('source ' + failure['source_candidate_digest'][:12])
        lines.append("Source fetch failed: " + target + " (" + failure['reason'].replace('_', ' ') + ").")
    unreadable = _bounded_count(report.get("readable_content_failure_count"))
    pdf_failures = _bounded_count(report.get("pdf_extraction_failure_count"))
    if pdf_failures:
        lines.append(f"PDF extraction gaps: {pdf_failures} document(s) could not be read within the text-extraction limits. "
                     "Encrypted and scanned-only PDFs are not treated as evidence; no OCR was performed.")
    if unreadable:
        lines.append(f"Readable-content gaps: {unreadable} fetched page(s) contained too little visible text "
                     "for demand assessment. They were not counted as evidence; this does not establish absent demand.")
    if str(report.get("synthesis_status") or "") == "research_model_assessed_inference":
        lines.append("Automatic assessment used source-bound passages; no native observation was upgraded to verified support.")
    elif isinstance(assessments, Mapping) and assessments.get("grounded_assessment_count"):
        lines.append(
            f"Exact source passages matched: {int(assessments['grounded_assessment_count'])}. "
            "These model assessments do not establish independent support for the conclusions."
        )
        if assessments.get("admission_blockers"):
            lines.append("Evidence assessment is incomplete: source classification, freshness and claim support "
                         "have not all been verified. This is not a finding that customer demand is absent.")
    elif isinstance(assessments, Mapping) and assessments.get("rejected_assessment_counts"):
        reasons = assessments["rejected_assessment_counts"]
        if isinstance(reasons, Mapping):
            lines.append("Source assessment gaps: " + "; ".join(
                str(reason).replace("_", " ")[:80] for reason in list(reasons)[:4]
            ) + ".")
    if not report_ready:
        lines.extend(_source_assessment_review_lines(report))
    if citations:
        lines.extend(["", "Sources:"])
        for row in citations:
            citation_id = str(row.get("citation_id") or "source")[:80]
            public_url = str(row.get("public_url") or "")[:2048]
            if public_url:
                lines.append(f"- [{citation_id}] {public_url}")
    disagreements = len(list(report.get("unresolved_disagreements") or []))
    missing = len(list(report.get("missing_evidence") or []))
    if disagreements or missing:
        lines.extend(["", f"Uncertainty retained: {disagreements} unresolved disagreement(s), {missing} evidence gap(s)."])
    lines.append("No posting, account, purchase, upload, message, credential use, or write request was allowed.")
    return "\n".join(lines)


def execute_conversational_research_action(
    function_name: str,
    function_args: Mapping[str, Any] | None,
    *,
    event_id: str,
    dry_run: bool = False,
    store: BoundedResearchSessionStore | None = None,
    adapter_factory: Any = None,
) -> dict[str, Any]:
    """Run one conversation action against the authoritative research store."""
    name = str(function_name or "")
    args = dict(function_args or {})
    if name not in RESEARCH_FUNCTIONS:
        return {"ok": False, "status": "unsupported_conversational_research_function", "message": "Unsupported research control."}
    if dry_run:
        return {
            "ok": True,
            "status": "research_conversation_dry_run_passed",
            "message": "Dry run passed. The exact bounded research transition was validated without web contact or runtime mutation.",
            "network_contacted": False,
            "runtime_mutated": False,
        }

    coordinator = store or BoundedResearchSessionStore()
    if name == "research_history_list":
        history = coordinator.history_catalog(limit=64)
        rows = list(history.get("sessions") or [])
        lines = [f"Research history: {len(rows)} terminal session(s)."]
        for row in rows[:10]:
            lines.append(
                f"- {row.get('session_id')}: {row.get('terminal_status')}; "
                f"{row.get('evidence_count', 0)} evidence item(s), {row.get('citation_count', 0)} citation(s); "
                f"integrity={row.get('integrity_status', 'unknown')}."
            )
        if history.get("missing_records"):
            lines.append(
                f"Integrity warning: {len(history.get('missing_records') or [])} terminal session(s) lack a history record; "
                "nothing was repaired silently."
            )
        return {
            "ok": True,
            "status": "bounded_research_history_ready",
            "message": "\n".join(lines),
            "history": history,
            "network_contacted": False,
            "private_objective_exposed": False,
            "raw_query_text_exposed": False,
            "raw_page_content_exposed": False,
        }

    if name == "research_sessions_compare":
        comparison = coordinator.compare_sessions(
            left_session_id=str(args.get("left_session_id") or ""),
            left_session_digest=str(args.get("left_session_digest") or ""),
            right_session_id=str(args.get("right_session_id") or ""),
            right_session_digest=str(args.get("right_session_digest") or ""),
        )
        if not comparison.get("ok"):
            return {
                "ok": False, "status": str(comparison.get("status") or "research_sessions_not_meaningfully_comparable"),
                "message": str(comparison.get("comparison_reason") or "Those exact completed sessions cannot be meaningfully compared."),
                "comparison": comparison, "network_contacted": False,
            }
        changed = len(list(comparison.get("changed_claims") or []))
        return {
            "ok": True, "status": "research_sessions_compared",
            "message": (
                f"Compared {comparison.get('left_session_id')} with {comparison.get('right_session_id')} without web contact. "
                f"Evidence structure changed in {changed} shared claim(s); added={len(list(comparison.get('added_claim_codes') or []))}, "
                f"removed={len(list(comparison.get('removed_claim_codes') or []))}, contradictory={len(list(comparison.get('contradictory_claim_codes') or []))}. "
                "No automatic winner was declared."
            ),
            "comparison": comparison, "network_contacted": False,
            "private_objective_exposed": False, "raw_query_text_exposed": False, "raw_page_content_exposed": False,
        }

    if name == "research_report_export":
        exported = coordinator.export_report_markdown(
            f"{event_id}:export",
            session_id=str(args.get("session_id") or ""),
            session_digest=str(args.get("session_digest") or ""),
        )
        receipt = dict(exported.get("result") or {})
        if not exported.get("ok"):
            return {
                "ok": False, "status": str(exported.get("status") or "research_report_export_failed"),
                "message": "The exact completed report could not be exported. Nothing was uploaded or transmitted.",
                "network_contacted": False, "uploaded": False, "transmitted": False,
            }
        return {
            "ok": True, "status": "bounded_research_report_exported",
            "message": (f"Saved the digest-bound Markdown export as {receipt.get('file_name')} in Eidolon's local runtime export area. "
                        "Nothing was uploaded or transmitted, and no private filesystem path is exposed here."),
            "export": receipt, "network_contacted": False, "uploaded": False, "transmitted": False,
            "private_objective_exposed": False, "raw_query_text_exposed": False, "raw_page_content_exposed": False,
        }

    if name == "research_session_create":
        outcome = coordinator.create_session(
            f"{event_id}:create",
            objective=str(args.get("objective") or ""),
            budget={
                "max_queries": 20,
                "max_candidates": 32,
                "max_observed_pages": 28,
                "max_total_bytes": 4 * 1024 * 1024,
                "max_elapsed_seconds": 600,
                "max_source_failures": 12,
            },
        )
        session = dict(outcome.get("result") or {})
        if not outcome.get("ok"):
            return {
                "ok": False,
                "status": str(outcome.get("status") or "research_session_create_failed"),
                "message": "I could not prepare that bounded research session. No web request ran.",
                "network_contacted": False,
            }
        phrase = _authorization_phrase(session)
        return {
            "ok": True,
            "status": str(outcome.get("status") or "research_session_created"),
            "message": (
                f"I prepared bounded read-only research session {session.get('session_id')}. No web request has run. "
                "One exact confirmation authorizes the whole GET/HEAD-only session; individual pages need no further approval. "
                f"Say exactly: {phrase}"
            ),
            "session": _public_session_fields(session),
            "authorization_phrase": phrase,
            "network_contacted": False,
            "per_page_approval_required": False,
        }

    session_id = str(args.get("session_id") or "")
    session_digest = str(args.get("session_digest") or "")
    if name == "research_session_authorize_execute":
        authorized = coordinator.authorize_session(
            f"{event_id}:authorize",
            session_id=session_id,
            session_digest=session_digest,
            public_query_confirmed=True,
        )
        if not authorized.get("ok"):
            return {
                "ok": False,
                "status": str(authorized.get("status") or "research_session_authorization_failed"),
                "message": "The exact research session could not be authorized. No web request ran.",
                "network_contacted": False,
            }
        authorization = str(dict(authorized.get("result") or {}).get("authorization_digest") or "")
        factory = adapter_factory or GovernedPublicWebResearchAdapter
        executed = coordinator.execute_session(
            f"{event_id}:execute",
            session_id=session_id,
            authorization_digest=authorization,
            adapter=factory(),
        )
        result = dict(executed.get("result") or {})
        session = dict(result.get("session") or {})
        report = dict(result.get("report") or {})
        if str(executed.get("status") or "") == "bounded_research_cancelled":
            return {
                "ok": True,
                "status": "bounded_research_cancelled",
                "message": (
                    f"I cancelled bounded research session {session_id}. The request already in flight was allowed to finish, "
                    "but no additional source request started and no partial report was presented as complete."
                ),
                "session": _public_session_fields(session),
                "report_digest": str(report.get("report_digest") or ""),
                "network_contacted": True,
                "per_page_approval_required": False,
            }
        if not executed.get("ok"):
            return {
                "ok": False,
                "status": str(executed.get("status") or "bounded_research_failed_safely"),
                "message": "The bounded research session stopped safely and did not produce a successful cited conclusion.",
                "session": _public_session_fields(session),
                "report_digest": str(report.get("report_digest") or ""),
                "network_contacted": True,
            }
        return {
            "ok": True,
            "status": str(executed.get("status") or "bounded_research_completed"),
            "message": _research_report_message(session, report),
            "session": _public_session_fields(session),
            "report": report,
            "report_digest": str(report.get("report_digest") or ""),
            "citation_count": int(report.get("citation_count") or 0),
            "network_contacted": True,
            "per_page_approval_required": False,
        }

    if name == "research_session_cancel":
        cancelled = coordinator.cancel_session(
            f"{event_id}:cancel",
            session_id=session_id,
            session_digest=session_digest,
        )
        session = dict(cancelled.get("result") or {})
        return {
            "ok": bool(cancelled.get("ok")),
            "status": str(cancelled.get("status") or "research_session_cancel_failed"),
            "message": (
                f"I cancelled research session {session_id}; no further source requests will start."
                if cancelled.get("ok")
                else "That exact research session could not be cancelled; its state was left unchanged."
            ),
            "session": _public_session_fields(session),
            "network_contacted": False,
        }

    inspected = coordinator.inspection_summary()
    sessions = [dict(row) for row in inspected.get("sessions", []) if isinstance(row, Mapping)]
    if session_id:
        sessions = [row for row in sessions if str(row.get("session_id") or "") == session_id]
    sessions = sessions[-5:]
    if not sessions:
        message = "No matching bounded research session was found."
    else:
        lines = ["Bounded research session status:"]
        for row in sessions:
            lines.append(
                f"- {row.get('session_id')}: {row.get('state')} at {row.get('progress_percent', 0)}% "
                f"({row.get('progress_stage')}); {row.get('evidence_count', 0)} evidence item(s)."
            )
        message = "\n".join(lines)
    return {
        "ok": True,
        "status": "bounded_research_status_ready",
        "message": message,
        "sessions": [_public_session_fields(row) for row in sessions],
        "network_contacted": False,
    }


__all__ = [
    "CONTRACT_VERSION",
    "RESEARCH_FUNCTIONS",
    "parse_conversational_research_request",
    "execute_conversational_research_action",
    "conversational_research_progress",
    "conversational_research_review",
    "conversational_research_history",
    "conversational_research_comparison",
    "conversational_research_export",
    "cancel_research_for_conversation_operation",
]
