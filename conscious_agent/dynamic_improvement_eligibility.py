from __future__ import annotations

"""v1490.3-v1490.9 deterministic eligibility hardening for dynamic discovery.

This layer can narrow and describe discovery evidence, but it cannot rank,
select, persist a proposal, prepare a workspace, contact a provider, or grant
execution/install/release authority.
"""

from collections import Counter
import hashlib
import json
from typing import Any, Iterable, Mapping

CONTRACT_VERSION = "v1490.9"
MIN_TEST_FILES = 1
MAX_DEPENDENCIES = 36
MIN_CONFIDENCE = 0.58


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _candidate_symbols(row: Mapping[str, Any]) -> set[tuple[str, str]]:
    module = str(row.get("source_module") or "")
    return {(module, str(name)) for name in row.get("source_symbols") or () if str(name)}


def _confidence_components(row: Mapping[str, Any]) -> dict[str, float]:
    refs = max(0, int(row.get("test_reference_file_count") or row.get("existing_test_reference_file_count") or 0))
    deps = max(0, int(row.get("estimated_dependency_count") or 0))
    symbols = max(1, len(row.get("source_symbols") or ()))
    spans = row.get("symbol_spans") or ()
    span_total = sum(max(1, int(span[2]) - int(span[1]) + 1) for span in spans if len(span) >= 3)
    reversibility = str(row.get("reversibility_classification") or "").casefold()
    return {
        "testability": round(min(1.0, refs / 3.0), 4),
        "dependency_headroom": round(max(0.0, 1.0 - deps / max(1.0, float(MAX_DEPENDENCIES))), 4),
        "cohesion": round(max(0.0, 1.0 - max(0, span_total - symbols * 35) / 280.0), 4),
        "reversibility": 1.0 if ("high" in reversibility or "reversible" in reversibility or "bounded_new_module" in reversibility) else 0.6 if "medium" in reversibility else 0.25,
        "discovery_eligible": 1.0 if bool(row.get("eligible_for_later_planning")) else 0.0,
    }


def _confidence(components: Mapping[str, float]) -> float:
    weights = {"testability": .30, "dependency_headroom": .20, "cohesion": .15, "reversibility": .20, "discovery_eligible": .15}
    return round(sum(float(components.get(key, 0.0)) * weight for key, weight in weights.items()), 4)


def harden_dynamic_discovery(
    discovery: Mapping[str, Any],
    *,
    completed_lineages: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Return deterministic eligibility decisions without choosing among them."""
    candidates = [dict(row or {}) for row in discovery.get("candidates") or ()]
    completed = [dict(row or {}) for row in completed_lineages]
    completed_destinations = {str(row.get("destination_module") or row.get("proposed_destination_module") or "").casefold() for row in completed}
    completed_evidence = {str(row.get("evidence_digest") or "") for row in completed if row.get("evidence_digest")}

    symbol_counts: Counter[tuple[str, str]] = Counter()
    destination_groups: dict[str, list[str]] = {}
    exact_symbol_groups: dict[tuple[tuple[str, str], ...], list[str]] = {}
    for row in candidates:
        cid = str(row.get("candidate_id") or "")
        symbols = _candidate_symbols(row)
        symbol_counts.update(symbols)
        destination_groups.setdefault(str(row.get("proposed_destination_module") or "").casefold(), []).append(cid)
        exact_symbol_groups.setdefault(tuple(sorted(symbols)), []).append(cid)

    decisions: list[dict[str, Any]] = []
    for row in candidates:
        candidate_id = str(row.get("candidate_id") or "")
        destination = str(row.get("proposed_destination_module") or "")
        source_symbols = sorted(str(x) for x in row.get("source_symbols") or () if str(x))
        rejection_codes: list[str] = []
        if not candidate_id or not str(row.get("evidence_digest") or "") or not destination or not source_symbols:
            rejection_codes.append("incomplete_candidate_evidence")
        if not bool(row.get("eligible_for_later_planning")):
            rejection_codes.append("discovery_marked_ineligible")
        if bool(row.get("protected_authority_boundary")) or "protected_authority_boundary" in set(row.get("rejection_codes") or ()):
            rejection_codes.append("protected_authority_boundary")
        if int(row.get("estimated_dependency_count") or 0) > MAX_DEPENDENCIES:
            rejection_codes.append("dependency_closure_excessive")
        if int(row.get("test_reference_file_count") or row.get("existing_test_reference_file_count") or 0) < MIN_TEST_FILES:
            rejection_codes.append("insufficient_attributable_test_evidence")
        symbols_for_row = _candidate_symbols(row)
        overlap_candidate_ids = sorted({
            str(other.get("candidate_id") or "")
            for other in candidates
            if str(other.get("candidate_id") or "") != candidate_id and symbols_for_row.intersection(_candidate_symbols(other))
        })
        exact_group = sorted(exact_symbol_groups.get(tuple(sorted(symbols_for_row)), []))
        destination_group = sorted(destination_groups.get(destination.casefold(), []))
        # Exact duplicates and duplicate destinations are canonicalized deterministically;
        # partial overlaps remain eligible for v1491 comparison instead of erasing every
        # candidate in a dense sliding-family discovery surface.
        if len(exact_group) > 1 and candidate_id != exact_group[0]:
            rejection_codes.append("exact_overlap_duplicate")
        if len(destination_group) > 1 and candidate_id != destination_group[0]:
            rejection_codes.append("duplicate_destination_in_discovery")
        if destination.casefold() in completed_destinations or str(row.get("evidence_digest") or "") in completed_evidence:
            rejection_codes.append("completed_lineage_duplicate")
        components = _confidence_components(row)
        confidence = _confidence(components)
        uncertainty = "low" if confidence >= .78 else "medium" if confidence >= MIN_CONFIDENCE else "high"
        if confidence < MIN_CONFIDENCE:
            rejection_codes.append("confidence_below_planning_floor")
        rejection_codes = sorted(set(rejection_codes))
        eligible = not rejection_codes
        decision = {
            "candidate_id": candidate_id,
            "evidence_digest": str(row.get("evidence_digest") or ""),
            "source_module": str(row.get("source_module") or ""),
            "source_symbols": source_symbols,
            "proposed_destination_module": destination,
            "estimated_dependency_count": int(row.get("estimated_dependency_count") or 0),
            "test_reference_file_count": int(row.get("test_reference_file_count") or row.get("existing_test_reference_file_count") or 0),
            "reversibility_classification": str(row.get("reversibility_classification") or ""),
            "confidence": confidence,
            "confidence_components": components,
            "uncertainty": uncertainty,
            "overlap_candidate_ids": overlap_candidate_ids,
            "overlap_requires_quality_resolution": bool(overlap_candidate_ids),
            "eligible_for_quality_comparison": eligible,
            "rejection_codes": rejection_codes,
            "content_free": True,
        }
        decision["eligibility_digest"] = _digest(decision)
        decisions.append(decision)

    decisions.sort(key=lambda row: (row["source_module"], row["source_symbols"], row["candidate_id"]))
    eligible = [row for row in decisions if row["eligible_for_quality_comparison"]]
    rejected = [row for row in decisions if not row["eligible_for_quality_comparison"]]
    result = {
        "contract_version": CONTRACT_VERSION,
        "discovery_digest": str(discovery.get("discovery_digest") or ""),
        "candidate_count": len(decisions),
        "eligible_count": len(eligible),
        "rejected_count": len(rejected),
        "decisions": decisions,
        "eligible_candidates": eligible,
        "rejected_candidates": rejected,
        "selection_made": False,
        "ranking_performed": False,
        "proposal_created": False,
        "workspace_prepared": False,
        "provider_contacted": False,
        "source_modified": False,
        "authority_granted": False,
        "content_free": True,
    }
    result["hardening_digest"] = _digest({k: v for k, v in result.items() if k != "decisions"} | {"decision_digests": [x["eligibility_digest"] for x in decisions]})
    return result


__all__ = ["CONTRACT_VERSION", "harden_dynamic_discovery"]
