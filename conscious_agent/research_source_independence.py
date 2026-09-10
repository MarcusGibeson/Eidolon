from __future__ import annotations

"""v2503.4 deterministic public-source identity and evidence-lineage reasoning.

This module performs no network/provider work. It converts already-public citation
metadata into content-free digests and conservative lineage clusters. Ambiguous
similarity never silently merges citations, and repeated/derivative citations never
become independent confirmation merely because they are numerous.
"""

import hashlib
import json
import posixpath
import re
from typing import Any, Iterable, Mapping
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

CONTRACT_VERSION = "v2503.4"

_DENIED = {
    "network_contacted": False,
    "provider_contacted": False,
    "write_method_used": False,
    "private_network_allowed": False,
    "credentials_allowed": False,
    "uploads_allowed": False,
    "source_modified": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "release_authorized": False,
    "standing_research_authority_granted": False,
    "authority_expanded": False,
}

_TRACKING_EXACT = {
    "gclid", "dclid", "fbclid", "msclkid", "mc_cid", "mc_eid", "igshid",
    "ref_src", "ref_url", "spm", "vero_conv", "vero_id", "wickedid",
}
_TRACKING_PREFIXES = ("utm_", "pk_", "ga_", "hsa_", "oly_")
_HOST_DECORATORS = {"www", "m", "amp", "mobile"}
_MULTI_LABEL_SUFFIXES = {
    "co.uk", "org.uk", "ac.uk", "gov.uk", "com.au", "net.au", "org.au",
    "co.jp", "co.nz", "com.br", "com.mx", "co.in", "com.sg", "com.tr",
}
_MALFORMED_URL = re.compile(r"[\s\\<>\[\]{}\"']|%(?:0[0-9a-f]|7f)", re.I)
_PROMOTIONAL_PATH = re.compile(
    r"(?:^|[-_/])(?:best|top|guide|how-to|ideas?|opportunities|profitable|comparison|reviews?)(?:[-_/]|$)",
    re.I,
)
_DEFINITION_SOURCE = re.compile(
    r"(?:^|[./_-])(?:dictionary|definition|definitions|meaning|supply-and-demand)(?:[./_-]|$)",
    re.I,
)


def _clean(value: object, limit: int = 2048) -> str:
    return " ".join(str(value or "").split()).strip()[:limit]


def _digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _hex64(value: object) -> str:
    text = str(value or "").strip().lower()
    return text if re.fullmatch(r"[0-9a-f]{64}", text) else ""


def canonicalize_public_url(value: object) -> str:
    """Normalize harmless public URL variation without broad semantic merging."""
    raw = str(value or "").strip()
    if not raw or len(raw) > 4096 or _MALFORMED_URL.search(raw):
        return ""
    try:
        parsed = urlsplit(raw)
    except Exception:
        return ""
    scheme = parsed.scheme.casefold()
    if scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        return ""
    host = parsed.hostname.casefold().rstrip(".")
    try:
        port = parsed.port
    except ValueError:
        return ""
    default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    netloc = host if port is None or default_port else f"{host}:{port}"
    raw_path = parsed.path or "/"
    normalized = posixpath.normpath(raw_path)
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    if raw_path.endswith("/") and normalized != "/" and not normalized.endswith("/"):
        normalized += "/"
    pairs: list[tuple[str, str]] = []
    for key, item in parse_qsl(parsed.query, keep_blank_values=True):
        lower = key.casefold()
        if lower in _TRACKING_EXACT or lower.startswith(_TRACKING_PREFIXES):
            continue
        pairs.append((key, item))
    pairs.sort(key=lambda pair: (pair[0].casefold(), pair[0], pair[1]))
    query = urlencode(pairs, doseq=True)
    return urlunsplit((scheme, netloc, normalized, query, ""))


def source_evidence_role(citation: Mapping[str, Any] | None) -> dict[str, Any]:
    """Classify what a public source can support without inflating its claims."""
    row = dict(citation or {})
    public_url = canonicalize_public_url(row.get("canonical_url") or row.get("public_url"))
    if not public_url:
        return {
            "valid_public_url": False,
            "evidence_role": "invalid_public_url",
            "source_quality_tier": "inadmissible",
            "quality_cap": 0.0,
            "supportable_dimensions": [],
            "promotional_or_listicle": False,
        }

    parsed = urlsplit(public_url)
    host = (parsed.hostname or "").casefold()
    path = (parsed.path or "/").casefold()
    kind = _clean(row.get("source_kind"), 60).casefold() or "unknown"
    dimensions = ["demand", "competition", "implementation_dependencies", "free_tier_feasibility"]
    # A publishing directory is not a finding about the article's evidence.
    promotional = bool(_PROMOTIONAL_PATH.search(path))
    definition_source = bool(_DEFINITION_SOURCE.search(host + path))
    if definition_source:
        return {
            "valid_public_url": True,
            "evidence_role": "generic_definition",
            "source_quality_tier": "inadmissible",
            "quality_cap": 0.0,
            "supportable_dimensions": [],
            "promotional_or_listicle": False,
        }

    if host in {"github.com", "www.github.com"} and re.search(r"/(?:issues|discussions)/", path):
        role, tier, cap, supported = "community_experience", "community", 0.55, dimensions[:2]
    elif host in {"github.com", "www.github.com"}:
        role, tier, cap, supported = "implementation_precedent", "primary", 0.80, ["implementation_dependencies"]
    elif re.search(r"(?:^|/)(?:pricing|plans?|limits?|quotas?|free-tier)(?:/|$|[-_])", path):
        role, tier, cap, supported = "pricing_or_free_tier", "primary", 0.90, ["competition", "free_tier_feasibility"]
    elif re.search(r"(?:^|/)(?:docs?|developer|api|reference|support)(?:/|$|[-_])", path):
        role, tier, cap, supported = "implementation_documentation", "primary", 0.90, ["implementation_dependencies"]
    elif kind == "primary_data" or host.endswith((".gov", ".edu")):
        role, tier, cap, supported = "direct_measurement", "primary", 0.95, dimensions
    elif kind == "primary_official":
        role, tier, cap, supported = "first_party_product_claim", "primary", 0.85, ["competition", "implementation_dependencies"]
    elif kind in {"reputable_secondary", "secondary_analysis"}:
        role, tier, cap, supported = "independent_analysis", "secondary", 0.78, dimensions
    elif kind == "specialist_secondary":
        role, tier, cap, supported = "specialist_analysis", "secondary", 0.72, dimensions
    elif kind == "community_experience":
        role, tier, cap, supported = "community_experience", "community", 0.55, dimensions[:2]
    else:
        role, tier, cap, supported = "unclassified_public_source", "unknown", 0.30, []

    if promotional and role not in {"direct_measurement", "pricing_or_free_tier", "implementation_documentation"}:
        role, tier, cap = "promotional_summary", "promotional", min(cap, 0.45)
        supported = []
    return {
        "valid_public_url": True,
        "evidence_role": role,
        "source_quality_tier": tier,
        "quality_cap": round(cap, 4),
        "supportable_dimensions": list(supported),
        "promotional_or_listicle": promotional,
    }


def _publisher_key(host: str, supplied: object = "") -> str:
    explicit = _clean(supplied, 255).casefold()
    if explicit:
        return re.sub(r"\s+", " ", explicit)
    labels = [part for part in host.casefold().strip(".").split(".") if part]
    while len(labels) > 2 and labels[0] in _HOST_DECORATORS:
        labels.pop(0)
    if len(labels) <= 2:
        return ".".join(labels)
    tail2 = ".".join(labels[-2:])
    if tail2 in _MULTI_LABEL_SUFFIXES and len(labels) >= 3:
        return ".".join(labels[-3:])
    return tail2


def source_identity(citation: Mapping[str, Any] | None) -> dict[str, Any]:
    row = dict(citation or {})
    public_url = canonicalize_public_url(row.get("canonical_url") or row.get("public_url"))
    try:
        host = (urlsplit(public_url).hostname or "").casefold() if public_url else _clean(row.get("host"), 255).casefold()
    except Exception:
        host = _clean(row.get("host"), 255).casefold()
    publisher_key = _publisher_key(host, row.get("publisher") or row.get("publisher_id"))
    canonical_page_digest = _digest({"canonical_public_url": public_url}) if public_url else ""
    host_digest = _digest({"host": host}) if host else ""
    publisher_digest = _digest({"publisher": publisher_key}) if publisher_key else ""
    source_digest = _hex64(row.get("source_digest"))
    explicit_origin_digest = (
        _hex64(row.get("lineage_origin_digest"))
        or _hex64(row.get("mirror_of_source_digest"))
        or _hex64(row.get("syndicated_from_source_digest"))
        or _hex64(row.get("attribution_source_digest"))
    )
    explicit_similarity_digest = _hex64(row.get("content_similarity_digest"))
    evidence_digest = _hex64(row.get("evidence_digest"))
    similarity_digest = explicit_similarity_digest or evidence_digest
    similarity_confidence = _clean(row.get("content_similarity_confidence"), 24).casefold()
    if evidence_digest and not explicit_similarity_digest:
        similarity_confidence = "exact"
    if similarity_confidence not in {"exact", "high", "ambiguous", "low", "unknown"}:
        similarity_confidence = "unknown"
    attribution_digest = _hex64(row.get("attribution_digest"))
    if canonical_page_digest:
        source_identity_digest = _digest({
            "canonical_page_digest": canonical_page_digest,
            "publisher_digest": publisher_digest,
        })
    elif source_digest:
        source_identity_digest = _digest({
            "source_digest": source_digest,
            "publisher_digest": publisher_digest,
        })
    else:
        source_identity_digest = _digest({
            "host_digest": host_digest,
            "publisher_digest": publisher_digest,
        })
    source_kind = _clean(row.get("source_kind"), 60).casefold() or "unknown"
    authoritative = source_kind in {"primary_official", "primary_data"}
    evidence_role = source_evidence_role(row)
    return {
        "contract_version": CONTRACT_VERSION,
        "citation_id": _clean(row.get("citation_id"), 80),
        "source_identity_digest": source_identity_digest,
        "canonical_page_digest": canonical_page_digest,
        "host_digest": host_digest,
        "publisher_digest": publisher_digest,
        "source_digest": source_digest,
        "explicit_origin_digest": explicit_origin_digest,
        "attribution_digest": attribution_digest,
        "content_similarity_digest": similarity_digest,
        "content_similarity_confidence": similarity_confidence,
        "authoritative_source": authoritative,
        **evidence_role,
        "raw_content_persisted": False,
        **_DENIED,
    }


def cluster_evidence_lineages(citations: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Cluster likely shared claim lineages using conservative deterministic signals."""
    rows = [dict(row or {}) for row in list(citations)[:256] if isinstance(row, Mapping)]
    identities = [source_identity(row) for row in rows]
    clusters: list[dict[str, Any]] = []
    cluster_by_key: dict[tuple[str, str], int] = {}
    citation_rows: list[dict[str, Any]] = []

    # Ambiguous similarity groups are deliberately not merged and are excluded
    # from confirmed-independence counts until stronger evidence exists.
    ambiguous_similarity_counts: dict[str, int] = {}
    for identity in identities:
        sim = identity.get("content_similarity_digest")
        if sim and identity.get("content_similarity_confidence") == "ambiguous":
            ambiguous_similarity_counts[str(sim)] = ambiguous_similarity_counts.get(str(sim), 0) + 1

    for identity in identities:
        origin = str(identity.get("explicit_origin_digest") or "")
        canonical = str(identity.get("canonical_page_digest") or "")
        source_digest = str(identity.get("source_digest") or "")
        similarity = str(identity.get("content_similarity_digest") or "")
        sim_conf = str(identity.get("content_similarity_confidence") or "unknown")
        attribution = str(identity.get("attribution_digest") or "")
        publisher = str(identity.get("publisher_digest") or "")

        uncertain = bool(similarity and sim_conf == "ambiguous" and ambiguous_similarity_counts.get(similarity, 0) > 1)
        reason = "distinct_source_identity"
        key: tuple[str, str]
        if origin:
            key, reason = ("origin", origin), "explicit_origin"
        elif canonical:
            key, reason = ("canonical_page", canonical), "canonical_page"
        elif source_digest:
            key, reason = ("source_digest", source_digest), "source_digest"
        else:
            key = ("identity", str(identity.get("source_identity_digest") or ""))
        if similarity and sim_conf in {"exact", "high"}:
            key, reason = ("content_similarity", similarity), "high_confidence_similarity"
        elif attribution and publisher:
            key, reason = ("publisher_attribution", _digest([publisher, attribution])), "publisher_attribution"

        if uncertain:
            # Preserve each ambiguous item as its own unresolved lineage rather
            # than silently merging or claiming independence.
            key = ("ambiguous", _digest([identity.get("citation_id"), identity.get("source_identity_digest")]))
            reason = "ambiguous_similarity_unmerged"

        if key in cluster_by_key:
            cluster_index = cluster_by_key[key]
            clusters[cluster_index]["citation_ids"].append(identity.get("citation_id"))
            clusters[cluster_index]["repetition_count"] += 1
            clusters[cluster_index]["authoritative_source"] = bool(
                clusters[cluster_index]["authoritative_source"] or identity.get("authoritative_source")
            )
        else:
            cluster_index = len(clusters)
            cluster_by_key[key] = cluster_index
            cluster_digest = _digest({"key_type": key[0], "key_digest": key[1]})
            clusters.append({
                "lineage_digest": cluster_digest,
                "citation_ids": [identity.get("citation_id")],
                "repetition_count": 1,
                "lineage_reason": reason,
                "independence_state": "uncertain" if uncertain else "independent",
                "authoritative_source": bool(identity.get("authoritative_source")),
            })
        citation_rows.append({
            **identity,
            "lineage_digest": clusters[cluster_index]["lineage_digest"],
            "lineage_reason": reason,
            "independence_state": "uncertain" if uncertain else "independent",
        })

    # A lineage with >1 citations is repetition/derivation by definition. It is
    # still one independent confirmation, never N confirmations.
    independent = [row for row in clusters if row.get("independence_state") == "independent"]
    uncertain = [row for row in clusters if row.get("independence_state") == "uncertain"]
    unique_sources = {str(row.get("source_identity_digest") or "") for row in identities if row.get("source_identity_digest")}
    primary_lineages = sum(1 for row in independent if row.get("authoritative_source"))
    result = {
        "ok": True,
        "status": "evidence_lineages_clustered",
        "contract_version": CONTRACT_VERSION,
        "citations": citation_rows,
        "lineages": clusters,
        "observed_citation_count": len(rows),
        "unique_source_identity_count": len(unique_sources),
        "independent_lineage_count": len(independent),
        "uncertain_lineage_count": len(uncertain),
        "repeated_or_derivative_citation_count": max(0, len(rows) - len(clusters)),
        "primary_or_authoritative_lineage_count": primary_lineages,
        "citation_volume_increases_confidence": False,
        "ambiguous_lineage_silently_merged": False,
        "raw_content_persisted": False,
        **_DENIED,
    }
    result["lineage_digest"] = _digest([
        {
            "lineage_digest": row["lineage_digest"],
            "repetition_count": row["repetition_count"],
            "independence_state": row["independence_state"],
            "authoritative_source": row["authoritative_source"],
        }
        for row in clusters
    ])
    return result


def independence_summary(citations: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    clustered = cluster_evidence_lineages(citations)
    return {
        "observed_citation_count": int(clustered.get("observed_citation_count") or 0),
        "unique_source_identity_count": int(clustered.get("unique_source_identity_count") or 0),
        "independent_lineage_count": int(clustered.get("independent_lineage_count") or 0),
        "uncertain_lineage_count": int(clustered.get("uncertain_lineage_count") or 0),
        "repeated_or_derivative_citation_count": int(clustered.get("repeated_or_derivative_citation_count") or 0),
        "primary_or_authoritative_lineage_count": int(clustered.get("primary_or_authoritative_lineage_count") or 0),
        "lineage_digest": str(clustered.get("lineage_digest") or ""),
        "citation_volume_increases_confidence": False,
    }


__all__ = [
    "CONTRACT_VERSION",
    "canonicalize_public_url",
    "source_evidence_role",
    "source_identity",
    "cluster_evidence_lineages",
    "independence_summary",
]
