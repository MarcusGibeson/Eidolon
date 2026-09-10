from __future__ import annotations

"""v1289.3-v1289.5 product-quality judgment and review-packet bridge."""
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping
from product_quality_judgment_foundations import DENIED_AUTHORITY, DIMENSIONS, assess_quality_dimensions

CONTRACT_VERSION = "v1289.5"


def _digest(v: Any) -> str:
    return sha256(json.dumps(v,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()


def build_product_quality_judgment(evidence: Iterable[Mapping[str, Any]], *, scope_digest: str = "") -> dict[str, Any]:
    assessed = assess_quality_dimensions(evidence)
    states = {d: assessed["dimensions"][d]["state"] for d in DIMENSIONS}
    if any(state == "fail" for state in states.values()):
        disposition = "needs_revision"
    elif any(state in {"unknown", "insufficient"} for state in states.values()):
        disposition = "insufficient_evidence"
    elif any(state == "warn" for state in states.values()):
        disposition = "ready_with_known_gaps"
    else:
        disposition = "operator_ready_candidate"
    deterministic_only = assessed["evidence_count"] > 0 and all(
        row["reason"] == "specialized_evidence_required" or row["fresh_evidence_count"] == 0
        for row in assessed["dimensions"].values()
    )
    result = {
        "contract_version": CONTRACT_VERSION,
        "scope_digest": str(scope_digest or "")[:64],
        "disposition": disposition,
        "dimensions": assessed["dimensions"],
        "dimension_states": states,
        "evidence_count": assessed["evidence_count"],
        "evidence_digest": assessed["evidence_digest"],
        "narrow_test_success_is_product_readiness": False,
        "deterministic_tests_alone_sufficient": False,
        "deterministic_only_evidence_detected": deterministic_only,
        "operator_ready_claimed": disposition == "operator_ready_candidate",
        "release_ready_claimed": False,
        "quality_judgment_is_authorization": False,
        "content_free": True,
        "read_only": True,
        **DENIED_AUTHORITY,
    }
    result["judgment_digest"] = _digest(result)
    return result


def review_packet_quality_evidence(packet: Mapping[str, Any], supplemental_evidence: Iterable[Mapping[str, Any]] = ()) -> list[dict[str, Any]]:
    """Translate existing review evidence conservatively; never invent UX/accessibility passes."""
    scope = str(packet.get("candidate_manifest_digest") or packet.get("changed_files_digest") or "")
    if len(scope) != 64:
        scope = _digest({"review_id": packet.get("review_id"), "changed_file_count": packet.get("changed_file_count")})
    rows: list[dict[str, Any]] = []
    verification = packet.get("verification") if isinstance(packet.get("verification"), Mapping) else {}
    if verification.get("passed") is True:
        result_digest = str(verification.get("result_digest") or "")
        if len(result_digest) != 64:
            result_digest = _digest(verification)
        for dimension in ("coherence", "completeness", "maintainability"):
            rows.append({"dimension":dimension,"evidence_type":"deterministic_test","state":"pass","evidence_digest":result_digest,"scope_digest":scope,"fresh":True})
    for risk in packet.get("risks") or []:
        if not isinstance(risk, Mapping): continue
        severity=str(risk.get("severity") or "").lower(); code=str(risk.get("risk_code") or "")
        if severity in {"high","critical"}:
            dimension="operator_readiness" if "operator" in code or "release" in code else "coherence"
            rows.append({"dimension":dimension,"evidence_type":"requirements_review","state":"warn","evidence_digest":_digest(risk),"scope_digest":scope,"fresh":True,"critical":severity=="critical"})
    for raw in supplemental_evidence:
        row=dict(raw); row.setdefault("scope_digest",scope); rows.append(row)
    return rows


def build_product_quality_from_review_packet(packet: Mapping[str, Any], supplemental_evidence: Iterable[Mapping[str, Any]] = ()) -> dict[str, Any]:
    rows=review_packet_quality_evidence(packet,supplemental_evidence)
    scope=str(packet.get("candidate_manifest_digest") or packet.get("changed_files_digest") or "")
    return build_product_quality_judgment(rows,scope_digest=scope)


def public_product_quality_judgment(judgment: Mapping[str, Any]) -> dict[str, Any]:
    return {k:judgment.get(k) for k in ("contract_version","scope_digest","disposition","dimension_states","evidence_count","evidence_digest","narrow_test_success_is_product_readiness","deterministic_tests_alone_sufficient","operator_ready_claimed","release_ready_claimed","quality_judgment_is_authorization","judgment_digest","content_free","read_only")} | DENIED_AUTHORITY
