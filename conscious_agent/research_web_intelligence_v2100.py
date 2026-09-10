from __future__ import annotations

"""Era 7 attributable research and governed browser planning.

No network request, browser process, provider call, download, or document parser
is invoked here.  The module plans research, vets source candidates, captures
content-free citation/evidence receipts, and makes contradictions explicit so a
native/browser adapter can later supply real observations under authority.
"""

from datetime import datetime, timezone
import hashlib
import ipaddress
import json
import math
import re
from typing import Any, Iterable, Mapping
from urllib.parse import urlsplit

CONTRACT_VERSION = "v2150.9"
NATIVE_RECEIPT_CONTRACT_VERSION = "era7-native-research-receipt-v1"
SCHEMA_VERSION = "1"
MAX_SUBQUESTIONS = 8
MAX_SOURCES = 32
MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024
ALLOWED_DOWNLOAD_MIME = {
    "text/plain", "text/html", "application/pdf", "application/json",
    "text/csv", "application/xml", "text/xml",
}
SOURCE_QUALITY = {
    "primary_official": 1.0,
    "primary_data": 0.95,
    "reputable_secondary": 0.82,
    "specialist_secondary": 0.76,
    "community_experience": 0.55,
    "unknown": 0.30,
}
# "current" is a news window. Published prices, statutory limits and enforcement
# registers are current subjects that no publisher reissues monthly, so demanding
# evidence from the last thirty days rejected every honest source for them. The
# annual band sits between news and the two-year slow-changing band.
FRESHNESS_DAYS = {"breaking": 1, "current": 30, "quarterly": 90, "versioned": 180, "annual": 365,
                  "slow_changing": 730, "stable": 3650}

_DENIED = {
    "browser_contacted": False,
    "network_contacted": False,
    "provider_contacted": False,
    "download_performed": False,
    "document_opened": False,
    "research_claim_verified": False,
    "tool_executed": False,
    "source_modified": False,
    "memory_modified": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "authority_expanded": False,
}

_SECRET = re.compile(r"(?:\b(?:password|passwd|secret|api[_-]?key|access[_-]?token|bearer)\b\s*[:=]|\bsk-[A-Za-z0-9_-]{12,})", re.I)


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _hex64(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if re.fullmatch(r"[0-9a-f]{64}", text) else ""


def _now(value: datetime | None = None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc)


def _validated_native_receipt(value: Mapping[str, Any], expected_kind: str) -> dict[str, Any] | None:
    row = dict(value or {})
    supplied = _hex64(row.pop("receipt_digest", ""))
    if (
        row.get("contract_version") != NATIVE_RECEIPT_CONTRACT_VERSION
        or row.get("receipt_kind") != expected_kind
        or row.get("authoritative") is not True
        or row.get("terminal") is not True
        or not _hex64(row.get("operation_digest"))
        or not _hex64(row.get("terminal_result_digest"))
        or not supplied
        or supplied != _digest(row)
    ):
        return None
    row["receipt_digest"] = supplied
    return row


def _url_candidate(url: str) -> tuple[bool, str, str, str]:
    raw = str(url or "").strip()
    if not raw or len(raw) > 2048 or _SECRET.search(raw):
        return False, "sensitive_or_invalid_url", "", ""
    try:
        parsed = urlsplit(raw)
    except Exception:
        return False, "malformed_url", "", ""
    if parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username or parsed.password:
        return False, "unsupported_or_credentialed_url", "", ""
    host = parsed.hostname.lower().rstrip(".")
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        return False, "local_target_rejected", "", ""
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None and (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast):
        return False, "private_network_target_rejected", "", ""
    path = parsed.path or "/"
    # Query text is intentionally excluded from public evidence because it may
    # contain private identifiers even when the host itself is public.
    canonical_public = f"{parsed.scheme}://{host}{path}"
    return True, "public_web_candidate", host, canonical_public


def plan_research(
    question: str, *, freshness: str = "current", source_preferences: Iterable[str] = (),
    private_context_present: bool = False, now: datetime | None = None,
) -> dict[str, Any]:
    text = " ".join(str(question or "").split()).strip()
    if not text:
        return {"ok": False, "status": "research_question_required", **_DENIED}
    if len(text) > 8000:
        return {"ok": False, "status": "research_question_too_large", **_DENIED}
    freshness_code = str(freshness or "current").strip().lower()
    if freshness_code not in FRESHNESS_DAYS:
        return {"ok": False, "status": "unknown_freshness_policy", **_DENIED}
    # Deterministic decomposition by explicit question/conjunction boundaries.
    chunks = [p.strip(" .?!") for p in re.split(r"(?:\?|\b(?:and|versus|vs\.?|compared with)\b)", text, flags=re.I) if p.strip(" .?!")]
    if not chunks:
        chunks = [text]
    chunks = chunks[:MAX_SUBQUESTIONS]
    subs = []
    for index, chunk in enumerate(chunks, 1):
        subs.append({
            "subquestion_id": f"rq{index}",
            "question_digest": hashlib.sha256(chunk.encode("utf-8")).hexdigest(),
            "requires_current_evidence": freshness_code in {"breaking", "current", "versioned"},
            "recommended_source_kinds": ["primary_official", "reputable_secondary"] if index == 1 else ["primary_official", "specialist_secondary"],
        })
    prefs = [str(x).strip().lower() for x in source_preferences if str(x).strip().lower() in SOURCE_QUALITY][:8]
    result = {
        "ok": True,
        "status": "research_plan_ready",
        "contract_version": CONTRACT_VERSION,
        "question_digest": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "question_text_persisted": False,
        "subquestions": subs,
        "freshness_policy": freshness_code,
        "max_source_age_days": FRESHNESS_DAYS[freshness_code],
        "preferred_source_kinds": prefs,
        "private_context_present": bool(private_context_present),
        "private_context_may_not_enter_public_query": True,
        "citation_required_for_current_claims": True,
        "contradiction_review_required": True,
        "planned_at": _now(now).isoformat(),
        **_DENIED,
    }
    result["plan_digest"] = _digest({k: v for k, v in result.items() if k != "planned_at"})
    return result


# English month names, spelled out rather than read through strptime's %b, which
# follows the process locale and would silently stop matching on a non-English
# system.
_MONTHS = {
    name: number
    for number, names in enumerate((
        ("jan", "january"), ("feb", "february"), ("mar", "march"), ("apr", "april"),
        ("may",), ("jun", "june"), ("jul", "july"), ("aug", "august"),
        ("sep", "sept", "september"), ("oct", "october"), ("nov", "november"), ("dec", "december"),
    ), 1)
    for name in names
}
_MONTH = r"([A-Za-z]{3,9})\.?"

# Non-ISO shapes scholarly publishers actually emit. Highwire dates look like
# "2021 Aug 23" or "2021/08/23"; a partial date names only a month or a year.
_SCHOLARLY_DATE_SHAPES: tuple[tuple[re.Pattern[str], tuple[str, ...]], ...] = (
    (re.compile(r"^(\d{4})[/.\-](\d{1,2})[/.\-](\d{1,2})$"), ("year", "month", "day")),
    (re.compile(r"^(\d{4})[/.\-](\d{1,2})$"), ("year", "month")),
    (re.compile(r"^(\d{4})$"), ("year",)),
    (re.compile(rf"^(\d{{4}})\s+{_MONTH}(?:\s+(\d{{1,2}}))?$"), ("year", "month_name", "day")),
    (re.compile(rf"^(\d{{1,2}})\s+{_MONTH},?\s+(\d{{4}})$"), ("day", "month_name", "year")),
    (re.compile(rf"^{_MONTH}\s+(\d{{1,2}}),?\s+(\d{{4}})$"), ("month_name", "day", "year")),
    (re.compile(rf"^{_MONTH}\s+(\d{{4}})$"), ("month_name", "year")),
)


def _parse_scholarly_date(text: str) -> datetime | None:
    """Read a non-ISO publication date, resolving a partial date to its start.

    A date that names only a month or a year becomes the first day of that
    period. That can only make a source look older than it is, never fresher, so
    a freshness requirement is never satisfied by the imprecision of a date.
    """
    for pattern, fields in _SCHOLARLY_DATE_SHAPES:
        match = pattern.match(text)
        if not match:
            continue
        parts = dict(zip(fields, match.groups()))
        try:
            year = int(parts["year"])
            if "month_name" in parts:
                month = _MONTHS.get(str(parts["month_name"]).casefold())
                if month is None:
                    return None
            else:
                month = int(parts.get("month") or 1)
            day = int(parts.get("day") or 1)
            if not 1800 <= year <= 2200:
                return None
            return datetime(year, month, day, tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _parse_timestamp(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        parsed = _parse_scholarly_date(text)
        if parsed is None:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def derive_source_freshness(
    *, published_at: str = "", fallback_at: str = "", freshness_policy: str = "current",
    now: datetime | None = None,
) -> dict[str, Any]:
    """Derive age and freshness from a declared publication date.

    An undeclared or unparseable date stays unknown rather than defaulting to
    fresh: a current-evidence claim must not be satisfied by a source that
    never stated when it was published.
    """
    policy = str(freshness_policy or "current").strip().lower()
    if policy not in FRESHNESS_DAYS:
        policy = "current"
    reference_time = _parse_timestamp(published_at) or _parse_timestamp(fallback_at)
    age_days = None
    if reference_time is not None:
        age_days = max(0, int((_now(now) - reference_time).total_seconds() // 86400))
    freshness_known = age_days is not None
    return {
        "age_days": age_days,
        "freshness_known": freshness_known,
        "fresh_enough": bool(freshness_known and age_days <= FRESHNESS_DAYS[policy]) if policy != "stable" else True,
    }


def assess_source_candidate(
    *, url: str, source_kind: str = "unknown", published_at: str = "", fetched_at: str = "",
    freshness_policy: str = "current", plan_digest: str = "",
) -> dict[str, Any]:
    valid, status, host, public_url = _url_candidate(url)
    if not valid:
        return {"ok": False, "status": status, **_DENIED}
    kind = str(source_kind or "unknown").strip().lower()
    if kind not in SOURCE_QUALITY:
        kind = "unknown"
    policy = str(freshness_policy or "current").strip().lower()
    if policy not in FRESHNESS_DAYS:
        policy = "current"
    freshness = derive_source_freshness(
        published_at=published_at, fallback_at=fetched_at, freshness_policy=policy,
    )
    age_days = freshness["age_days"]
    freshness_known = freshness["freshness_known"]
    fresh_enough = freshness["fresh_enough"]
    result = {
        "ok": True,
        "status": "research_source_candidate_assessed",
        "plan_digest": _hex64(plan_digest),
        "host": host,
        "public_url": public_url,
        "url_digest": hashlib.sha256(str(url).encode("utf-8")).hexdigest(),
        "query_fragment_retained": False,
        "source_kind": kind,
        "quality_score": SOURCE_QUALITY[kind],
        "freshness_policy": policy,
        "age_days": age_days,
        "freshness_known": freshness_known,
        "fresh_enough": fresh_enough,
        "browser_contact_required": True,
        "source_observed": False,
        **_DENIED,
    }
    result["source_candidate_digest"] = _digest(result)
    return result


def prepare_browser_research_request(
    *, plan: Mapping[str, Any], source_candidates: Iterable[Mapping[str, Any]], operation_id: str,
) -> dict[str, Any]:
    pd = _hex64(plan.get("plan_digest"))
    if not pd:
        return {"ok": False, "status": "valid_research_plan_required", **_DENIED}
    op = str(operation_id or "").strip()
    if not op:
        return {"ok": False, "status": "operation_identity_required", **_DENIED}
    rows = []
    for raw in list(source_candidates)[:MAX_SOURCES]:
        row = dict(raw or {})
        if row.get("ok") is True and row.get("source_observed") is False and row.get("host"):
            rows.append({
                "source_candidate_digest": str(row.get("source_candidate_digest") or ""),
                "host": str(row.get("host") or "")[:255],
                "public_url": str(row.get("public_url") or "")[:2048],
                "source_kind": str(row.get("source_kind") or "unknown"),
                "fresh_enough": bool(row.get("fresh_enough")),
            })
    request = {
        "contract_version": CONTRACT_VERSION,
        "plan_digest": pd,
        "operation_digest": hashlib.sha256(op.encode("utf-8")).hexdigest(),
        "sources": rows,
        "source_count": len(rows),
        "allowed_schemes": ["https", "http"],
        "private_network_allowed": False,
        "credentials_allowed": False,
        "secret_forwarding_allowed": False,
        "browser_execution_admitted": False,
        "requires_governed_browser_adapter": True,
        "requires_result_receipts": True,
        **_DENIED,
    }
    request["request_digest"] = _digest(request)
    return {"ok": True, "status": "browser_research_request_prepared_not_executed", "request": request, **_DENIED}


def validate_download_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    row = _validated_native_receipt(receipt, "download")
    if row is None:
        return {"ok": False, "status": "download_receipt_rejected", "raw_content_included": False, **_DENIED}
    mime = str(row.get("mime_type") or "").lower()
    try:
        size_value = float(row.get("size_bytes"))
        if not math.isfinite(size_value) or not size_value.is_integer():
            raise ValueError
        size = int(size_value)
    except (TypeError, ValueError, OverflowError):
        return {"ok": False, "status": "download_receipt_rejected", "raw_content_included": False, **_DENIED}
    digest = _hex64(row.get("content_digest"))
    allowed = bool(digest and mime in ALLOWED_DOWNLOAD_MIME and 0 <= size <= MAX_DOWNLOAD_BYTES)
    return {
        "ok": allowed,
        "status": "download_receipt_accepted" if allowed else "download_receipt_rejected",
        "mime_type": mime if mime in ALLOWED_DOWNLOAD_MIME else "",
        "size_bytes": size if size >= 0 else 0,
        "content_digest": digest,
        "raw_content_included": False,
        "extraction_authorized": allowed,
        "network_contacted_by_this_module": False,
        **{k: v for k, v in _DENIED.items() if k != "download_performed"},
        "download_performed": False,
    }


def validate_document_extraction_receipt(download_receipt: Mapping[str, Any], extraction_receipt: Mapping[str, Any]) -> dict[str, Any]:
    """Bind extracted document evidence to one accepted download digest."""
    download = validate_download_receipt(download_receipt)
    row = _validated_native_receipt(extraction_receipt, "document_extraction")
    if row is None:
        return {"ok": False, "status": "authoritative_matching_extraction_receipt_required", "raw_text_included": False, **_DENIED}
    source_digest = _hex64(row.get("source_content_digest"))
    text_digest = _hex64(row.get("extracted_text_digest"))
    structure_digest = _hex64(row.get("structure_digest"))
    try:
        page_count = max(0, min(int(row.get("page_count") or 0), 100000))
    except (TypeError, ValueError, OverflowError):
        page_count = 0
    exact = bool(
        download.get("ok")
        and source_digest
        and source_digest == download.get("content_digest")
        and text_digest
        and page_count >= 1
    )
    if not exact:
        return {"ok": False, "status": "authoritative_matching_extraction_receipt_required", "raw_text_included": False, **_DENIED}
    result = {
        "ok": True, "status": "document_extraction_receipt_accepted",
        "source_content_digest": source_digest, "extracted_text_digest": text_digest,
        "structure_digest": structure_digest, "page_count": page_count,
        "extractor_code": str(row.get("extractor_code") or "unknown")[:80],
        "raw_text_included": False, "source_bytes_included": False,
        "extraction_is_evidence_not_source_truth": True,
        **_DENIED,
    }
    result["extraction_receipt_digest"] = _digest(result)
    return result


def capture_research_evidence(
    *, plan_digest: str, observations: Iterable[Mapping[str, Any]], now: datetime | None = None,
) -> dict[str, Any]:
    pd = _hex64(plan_digest)
    if not pd:
        return {"ok": False, "status": "valid_plan_digest_required", **_DENIED}
    rows = []
    for raw in list(observations)[:MAX_SOURCES]:
        row = _validated_native_receipt(raw, "source_observation")
        if row is None or row.get("source_observed") is not True or _hex64(row.get("plan_digest")) != pd:
            continue
        source_digest = _hex64(row.get("source_candidate_digest")) or _hex64(row.get("source_digest"))
        claim_code = str(row.get("claim_code") or "").strip().lower()[:120]
        stance = str(row.get("stance") or "unknown").strip().lower()
        evidence_digest = _hex64(row.get("evidence_digest"))
        citation_id = str(row.get("citation_id") or "").strip()[:80]
        if not source_digest or not claim_code or stance not in {"supports", "refutes", "mixed", "unknown"} or not evidence_digest or not citation_id:
            continue
        try:
            quality = float(row.get("quality_score") or 0.0)
            if not math.isfinite(quality):
                raise ValueError
        except (TypeError, ValueError, OverflowError):
            continue
        rows.append({
            "source_digest": source_digest,
            "claim_code": claim_code,
            "stance": stance,
            "evidence_digest": evidence_digest,
            "citation_id": citation_id,
            "source_kind": str(row.get("source_kind") or "unknown")[:60],
            "quality_score": max(0.0, min(1.0, quality)),
            "freshness_known": bool(row.get("freshness_known")),
            "fresh_enough": bool(row.get("fresh_enough")),
            "raw_quote_stored": False,
            "authoritative_observation": True,
            "native_receipt_digest": row["receipt_digest"],
            "terminal_result_digest": _hex64(row.get("terminal_result_digest")),
        })
    groups: dict[str, dict[str, int]] = {}
    for row in rows:
        g = groups.setdefault(row["claim_code"], {"supports": 0, "refutes": 0, "mixed": 0, "unknown": 0})
        g[row["stance"]] += 1
    contradictions = sorted(code for code, counts in groups.items() if counts["supports"] and counts["refutes"])
    result = {
        "ok": True,
        "status": "research_evidence_captured",
        "contract_version": CONTRACT_VERSION,
        "plan_digest": pd,
        "evidence": rows,
        "evidence_count": len(rows),
        "claim_stance_counts": groups,
        "contradicted_claim_codes": contradictions,
        "contradiction_review_complete": True,
        "citations": [{"citation_id": r["citation_id"], "source_digest": r["source_digest"], "evidence_digest": r["evidence_digest"]} for r in rows],
        "raw_quotes_persisted": False,
        "captured_at": _now(now).isoformat(),
        **_DENIED,
    }
    result["evidence_bundle_digest"] = _digest({k: v for k, v in result.items() if k != "captured_at"})
    return result


def evaluate_claim_support(evidence_bundle: Mapping[str, Any], claim_code: str, *, current_claim: bool = True) -> dict[str, Any]:
    code = str(claim_code or "").strip().lower()[:120]
    rows = [dict(x) for x in evidence_bundle.get("evidence", []) if isinstance(x, Mapping) and x.get("claim_code") == code]
    supports = [r for r in rows if r.get("stance") == "supports" and (not current_claim or r.get("fresh_enough"))]
    refutes = [r for r in rows if r.get("stance") == "refutes" and (not current_claim or r.get("fresh_enough"))]
    if supports and refutes:
        state = "conflicted"
    elif supports:
        state = "supported"
    elif refutes:
        state = "refuted"
    else:
        state = "insufficient_current_evidence" if current_claim else "insufficient_evidence"
    return {
        "ok": True,
        "status": "research_claim_support_assessed",
        "claim_code": code,
        "support_state": state,
        "supporting_citations": [r["citation_id"] for r in supports],
        "refuting_citations": [r["citation_id"] for r in refutes],
        "citation_required": True,
        "internal_knowledge_is_current_evidence": False,
        "generated_prose_is_evidence": False,
        **_DENIED,
    }


def process_era7_research_control(text: str) -> dict[str, Any]:
    raw = " ".join(str(text or "").split()).strip().lower().rstrip(".!?")
    exact = {"show research and web intelligence contract", "inspect research and web intelligence contract", "show era7 research contract"}
    if raw in exact:
        return {
            "active": True, "ok": True, "status": "era7_research_contract_inspected",
            "contract_version": CONTRACT_VERSION,
            "source_quality_codes": sorted(SOURCE_QUALITY),
            "freshness_policies": dict(FRESHNESS_DAYS),
            "allowed_download_mime": sorted(ALLOWED_DOWNLOAD_MIME),
            "max_download_bytes": MAX_DOWNLOAD_BYTES,
            "governed_browser_required": True,
            "private_network_allowed": False,
            "secret_forwarding_allowed": False,
            **_DENIED,
        }
    if any(raw.startswith(prefix) for prefix in exact):
        return {"active": True, "ok": False, "status": "era7_research_read_only_scope_expansion_rejected", **_DENIED}
    return {"active": False}


__all__ = [
    "CONTRACT_VERSION", "NATIVE_RECEIPT_CONTRACT_VERSION", "SOURCE_QUALITY", "FRESHNESS_DAYS", "plan_research", "assess_source_candidate",
    "derive_source_freshness",
    "prepare_browser_research_request", "validate_download_receipt", "validate_document_extraction_receipt", "capture_research_evidence",
    "evaluate_claim_support", "process_era7_research_control",
]
