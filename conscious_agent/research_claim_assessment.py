"""Bind model source assessments to transient observed text without promoting them."""
from __future__ import annotations

import hashlib
import re
from collections import Counter
from collections.abc import Mapping

from research_source_independence import independence_summary, source_evidence_role, source_identity


def digest_of_claim(claim: object) -> str:
    """The digest that binds a source assessment to one exact claim.

    Assessments are grounded per claim, and the model is told each assessed claim
    must equal the finding summary. Everything that asks "did this source support
    this finding" compares against this digest, so it has one definition.
    """
    return hashlib.sha256(str(claim if claim is not None else "").encode()).hexdigest()


_TRAILING_PUNCTUATION = re.compile(r"[\s.!?;:,]+$")


def normalized_claim_text(claim: object) -> str:
    """A claim with case, whitespace and trailing punctuation made irrelevant.

    Only those three. Anything else - a unit, a figure, a word - is part of the
    proposition, so "$0.30" and "30 cents" stay different claims.
    """
    collapsed = " ".join(str(claim if claim is not None else "").split()).casefold()
    return _TRAILING_PUNCTUATION.sub("", collapsed)


def digest_of_normalized_claim(claim: object) -> str:
    """A content-free digest of the normalized claim, for measurement only.

    Admission still keys on digest_of_claim. This exists so a receipt can say
    whether an assessment made for "other wording" differed only cosmetically -
    in which case the identity test is too literal - or changed the proposition,
    in which case it is right and the prompt is the thing to fix.
    """
    return hashlib.sha256(normalized_claim_text(claim).encode()).hexdigest()


def grounded_supporting_citation_ids(
    assessments: object,
    claim: object,
    offered_ids: object = None,
) -> list[str]:
    """Citations the model tied, through an observed passage, to supporting exactly this claim.

    An assessment only reaches this list after grounding has verified that its
    passage was offered and appears literally in the observed excerpt. The support
    judgement itself remains the model's: grounding verifies provenance, not
    meaning. An assessment made for a different claim never counts, however
    favourable.
    """
    digest = digest_of_claim(claim)
    allowed = None if offered_ids is None else {str(item) for item in offered_ids}  # type: ignore[union-attr]
    ids: list[str] = []
    for row in assessments if isinstance(assessments, list) else []:
        if not isinstance(row, Mapping):
            continue
        if row.get("model_assessment") != "supports" or row.get("claim_digest") != digest:
            continue
        if row.get("textual_provenance_verified") is not True:
            continue
        cid = str(row.get("citation_id") or "")
        if cid and (allowed is None or cid in allowed) and cid not in ids:
            ids.append(cid)
    return ids


PASSAGE_MIN_CHARS = 30
PASSAGE_MAX_CHARS = 600
PASSAGE_OPTION_LIMIT = 3
_SEGMENT_BREAK = re.compile(r"(?<=[.!?])\s+|\n+")


def _segment_spans(text):
    """Offsets of sentence-like segments, separators excluded."""
    spans, cursor = [], 0
    for match in _SEGMENT_BREAK.finditer(text):
        if match.start() > cursor:
            spans.append((cursor, match.start()))
        cursor = match.end()
    if len(text) > cursor:
        spans.append((cursor, len(text)))
    return spans


def _bounded_chunks(text, start, end):
    """Cut an overlong run into pieces at whitespace, never mid-word."""
    spans, cursor = [], start
    while end - cursor > PASSAGE_MAX_CHARS:
        window = text.rfind(" ", cursor + PASSAGE_MIN_CHARS, cursor + PASSAGE_MAX_CHARS)
        stop = window if window > cursor else cursor + PASSAGE_MAX_CHARS
        spans.append((cursor, stop))
        cursor = stop + 1 if text[stop:stop + 1] == " " else stop
    if end - cursor >= PASSAGE_MIN_CHARS:
        spans.append((cursor, end))
    return spans


def passage_options(citation_id, excerpt):
    """Offer bounded exact spans; IDs remain bound to both text and source.

    Every option is a slice of the excerpt by offset, so a passage is always
    verbatim observed text. Text that does not fall into neat sentences is
    still quotable: an overlong run is cut at whitespace and consecutive short
    fragments are joined across their original separators. Requiring tidy
    sentence boundaries silently discarded whole sources before the model could
    assess them.
    """
    text = str(excerpt or "")
    options, open_start = [], None
    for start, end in _segment_spans(text):
        if open_start is None:
            open_start = start
        if end - open_start > PASSAGE_MAX_CHARS:
            chunks = _bounded_chunks(text, open_start, end)
            open_start = None
        elif end - open_start >= PASSAGE_MIN_CHARS:
            chunks = [(open_start, end)]
            open_start = None
        else:
            continue  # too short alone; keep accumulating across separators
        for chunk_start, chunk_end in chunks:
            span = text[chunk_start:chunk_end]
            options.append({
                "passage_id": hashlib.sha256((citation_id + "\0" + span).encode()).hexdigest()[:16],
                "text": span,
            })
            if len(options) == PASSAGE_OPTION_LIMIT:
                return options
    return options


def assess_source_claims(payload, *, documents, citations, required_dimension=""):
    """Retain content-free assessments only when their exact passage was observed.

    Matching a passage establishes textual provenance, not entailment. Model stance
    remains advisory and cannot replace a native supporting-observation receipt.
    """
    source_index = {row.get("citation_id"): row for row in citations if isinstance(row, Mapping)}
    document_index = {row.get("citation_id"): row for row in documents if isinstance(row, Mapping)}
    supplied = payload.get("source_assessments", []) if isinstance(payload, Mapping) else []
    if not isinstance(supplied, list):
        supplied = []
    accepted, rejected, seen = [], Counter(), set()
    selector_diagnostics = Counter()
    for row in supplied[:32]:
        if not isinstance(row, Mapping):
            rejected["invalid_row"] += 1
            continue
        cid = row.get("citation_id")
        if not isinstance(cid, str) or cid not in source_index or cid not in document_index:
            rejected["unobserved_citation"] += 1
            continue
        quote, claim = row.get("evidence_quote"), row.get("claim")
        stance = row.get("assessment")
        excerpt = str(document_index[cid].get("excerpt") or "")
        if "passage_index" in row:
            choices = passage_options(cid, excerpt)
            position = row["passage_index"]
            if type(position) is not int or not 1 <= position <= len(choices):
                rejected["unobserved_passage_index"] += 1
                reason = ("no_offered_passages" if not choices else
                          "wrong_type" if type(position) is not int else
                          "below_one" if position < 1 else "above_source_range")
                selector_diagnostics[reason] += 1
                continue
            selected = choices[position - 1]
            if "passage_id" in row and row["passage_id"] != selected["passage_id"]:
                rejected["passage_selector_conflict"] += 1
                continue
            row = {**row, "passage_id": selected["passage_id"]}
        if "passage_id" in row:
            options = {item["passage_id"]: item["text"] for item in passage_options(cid, excerpt)}
            pid = row["passage_id"]
            if not isinstance(pid, str) or pid not in options:
                rejected["unobserved_passage_id"] += 1
                continue
            if quote is not None and quote != options[pid]:
                rejected["passage_quote_mismatch"] += 1
                continue
            quote = options[pid]
        if not isinstance(quote, str) or not 30 <= len(quote) <= 600:
            rejected["passage_missing_or_out_of_bounds"] += 1
            continue
        if not isinstance(claim, str) or not 1 <= len(claim) <= 700:
            rejected["claim_missing_or_out_of_bounds"] += 1
            continue
        if stance not in ("supports", "refutes", "unclear"):
            rejected["invalid_stance"] += 1
            continue
        if quote not in excerpt:
            rejected["passage_not_observed"] += 1
            continue
        key = (cid, quote, claim, stance)
        if key in seen:
            rejected["duplicate_assessment"] += 1
            continue
        seen.add(key)
        role = source_evidence_role(source_index[cid])
        accepted.append({
            "citation_id": cid,
            "claim_digest": digest_of_claim(claim),
            "normalized_claim_digest": digest_of_normalized_claim(claim),
            "passage_digest": hashlib.sha256(quote.encode()).hexdigest(),
            "observed_excerpt_digest": hashlib.sha256(excerpt.encode()).hexdigest(),
            "model_assessment": stance,
            "model_evidence_kind": row.get("evidence_kind") if row.get("evidence_kind") in {
                "customer_experience", "survey_result", "usage_measurement", "vendor_offering", "unknown"
            } else "unknown",
            "assessed_dimension": row.get("dimension", required_dimension) if row.get("dimension", required_dimension) in {
                "demand", "competition", "implementation_dependencies", "free_tier_feasibility"
            } else "",
            "evidence_role": role["evidence_role"],
            "supportable_dimensions": role["supportable_dimensions"],
            "textual_provenance_verified": True,
            "semantic_support_verified": False,
        })
    used = {row["citation_id"] for row in accepted}
    blockers = Counter()
    for cid in sorted(used):
        source = source_index[cid]
        if source.get("source_kind", "unknown") == "unknown":
            blockers["source_type_unverified"] += 1
        if source.get("freshness", "unknown") == "unknown":
            blockers["source_freshness_unverified"] += 1
    if accepted:
        blockers["claim_support_not_verified"] = len(accepted)
    return {
        "status": "source_assessments_grounded" if accepted else "source_assessments_unavailable",
        "assessments": accepted,
        "grounded_assessment_count": len(accepted),
        # Fixed-vocabulary tallies. Admission turns on stance and evidence kind, so
        # without these a refusal is indistinguishable from a model that never ran.
        "assessment_stance_counts": dict(Counter(row["model_assessment"] for row in accepted)),
        "assessment_evidence_kind_counts": dict(Counter(row["model_evidence_kind"] for row in accepted)),
        "rejected_assessment_counts": dict(rejected),
        "selector_diagnostics": dict(selector_diagnostics),
        "admission_blockers": dict(blockers),
        "source_independence": independence_summary([source_index[cid] for cid in sorted(used)]),
        "model_judgment_is_evidence": False,
        "raw_quote_persisted": False,
        "raw_page_content_persisted": False,
        "authority_expanded": False,
    }


# A rejection disqualifies the whole inference when it means the response claimed
# provenance it does not have: citing a source it was never shown, selecting a
# passage that was not offered, or quoting text absent from the observed excerpt.
# A duplicate is not that. It is the same grounded assessment stated twice, and
# grounding has already dropped the repeat, so refusing the finding over it
# discards good evidence because the model was repetitive. Any reason not listed
# here is treated as disqualifying, so a new rejection code fails closed.
BENIGN_ASSESSMENT_REJECTIONS = frozenset({"duplicate_assessment"})


def disqualifying_rejections(rejected_counts):
    """Rejection reasons serious enough to refuse a model-assessed inference."""
    if not isinstance(rejected_counts, Mapping):
        return {}
    disqualifying = {}
    for reason, count in rejected_counts.items():
        try:
            total = int(count)
        except (TypeError, ValueError):
            total = 1
        if total > 0 and str(reason) not in BENIGN_ASSESSMENT_REJECTIONS:
            disqualifying[str(reason)] = total
    return disqualifying


def _not_admitted(reason):
    """Refuse a model-assessed inference, naming which rule refused it.

    A bare refusal made every denial look alike in the receipt, so a run blocked
    by one stale citation was indistinguishable from one lacking evidence
    entirely. The reason is a fixed code, carrying no claim text or URL.
    """
    return {"ok": False, "status": "model_assessment_not_admitted", "denial_reason": reason}


def model_assessed_conclusion(payload, *, assessment_summary, citations, dimension):
    """Admit a tentative demand inference, never a verified observation or winner.

    The model evaluates meaning and evidence kind. Deterministic checks bind that
    judgment to the exact finding, observed passages, and distinct source lineages.
    """
    if dimension != "demand" or not isinstance(payload, Mapping) or not isinstance(assessment_summary, Mapping):
        return _not_admitted("not_a_demand_dimension")
    findings = payload.get("findings")
    if not isinstance(findings, list) or len(findings) != 1 or not isinstance(findings[0], Mapping):
        return _not_admitted("finding_not_singular")
    finding = findings[0]
    if not isinstance(finding.get("title"), str) or not finding["title"].strip():
        return _not_admitted("finding_missing_title")
    claim = finding.get("summary")
    ids = finding.get("citation_ids")
    if not isinstance(claim, str) or not 1 <= len(claim) <= 700 or not isinstance(ids, list):
        return _not_admitted("finding_claim_or_citations_invalid")
    if not all(isinstance(cid, str) for cid in ids):
        return _not_admitted("citation_ids_not_strings")
    index = {row.get("citation_id"): row for row in citations if isinstance(row, Mapping)}
    if not ids or any(cid not in index for cid in ids):
        return _not_admitted("cited_citation_not_observed")
    claim_digest = hashlib.sha256(claim.encode()).hexdigest()
    if disqualifying_rejections(assessment_summary.get("rejected_assessment_counts")):
        return _not_admitted("grounding_rejected_some_assessments")
    if any(row.get("stance") in {"refutes", "mixed"} for row in index.values()):
        return _not_admitted("observed_citation_stance_conflicts")
    all_assessments = assessment_summary.get("assessments", [])
    if not isinstance(all_assessments, list):
        return _not_admitted("assessments_malformed")
    if any(not isinstance(row, Mapping) or row.get("claim_digest") != claim_digest
           or row.get("assessed_dimension") != dimension for row in all_assessments):
        return _not_admitted("assessment_claim_or_dimension_mismatch")
    rows = [row for row in assessment_summary.get("assessments", [])
            if isinstance(row, Mapping) and row.get("claim_digest") == claim_digest
            and row.get("assessed_dimension") == dimension]
    # Consider adverse assessments even when the model omitted them from its finding.
    if any(row.get("model_assessment") == "refutes"
           or (row.get("citation_id") in ids and row.get("model_assessment") != "supports")
           for row in rows):
        return _not_admitted("cited_source_not_assessed_as_supporting")
    eligible = {}
    set_aside_stale: list[str] = []
    for row in rows:
        cid = row.get("citation_id")
        if cid not in ids or not row.get("textual_provenance_verified"):
            continue
        if not re.fullmatch(r"[0-9a-f]{64}", str(row.get("passage_digest") or "")):
            return _not_admitted("passage_digest_invalid")
        role = source_evidence_role(index[cid])
        if role["evidence_role"] in {
            "invalid_public_url", "generic_definition", "promotional_summary",
            "first_party_product_claim", "implementation_precedent",
            "implementation_documentation", "pricing_or_free_tier",
        }:
            continue
        if row.get("model_evidence_kind") not in {"customer_experience", "survey_result", "usage_measurement"}:
            continue
        relevance = index[cid].get("relevance_score")
        if not isinstance(relevance, (int, float)) or not 0.5 <= relevance <= 1.0:
            continue
        if index[cid].get("stance") in {"refutes", "mixed"}:
            # A cited source that argues against the claim is a contradiction, not
            # a weak citation, and still refuses the finding outright.
            return _not_admitted("cited_source_conflicting")
        if index[cid].get("freshness") == "stale":
            # An out-of-date source is not bad faith, it is evidence that must not
            # count. Set it aside as ineligible rather than refusing a finding whose
            # remaining citations do qualify; the two fresh independent publishers
            # required below are unchanged, and the exclusion is recorded.
            set_aside_stale.append(cid)
            continue
        # Identical selected passages remain one lineage even across different hosts.
        eligible[cid] = {**index[cid], "content_similarity_digest": row["passage_digest"],
                         "content_similarity_confidence": "exact"}
    if set(eligible) | set(set_aside_stale) != set(ids):
        return _not_admitted("cited_source_ineligible")
    if not eligible:
        return _not_admitted("no_eligible_cited_source")
    publishers = {source_identity(index[cid])["publisher_digest"] for cid in eligible}
    if "" in publishers or len(publishers) < 2:
        return _not_admitted("insufficient_distinct_publishers")
    original_lineage = independence_summary([index[cid] for cid in eligible])
    groups = {cid: {cid} for cid in index}
    for pair in assessment_summary.get("observed_attribution_relationships", []):
        if not isinstance(pair, list) or len(pair) != 2 or any(cid not in groups for cid in pair):
            return _not_admitted("attribution_relationships_malformed")
        merged = groups[pair[0]] | groups[pair[1]]
        for cid in merged:
            groups[cid] = merged
    if len({tuple(sorted(groups[cid])) for cid in eligible}) < 2:
        return _not_admitted("insufficient_independent_groups")
    if original_lineage["independent_lineage_count"] < 2 or original_lineage["uncertain_lineage_count"]:
        return _not_admitted("insufficient_independent_lineage")
    lineage = independence_summary(eligible.values())
    if lineage["independent_lineage_count"] < 2 or lineage["uncertain_lineage_count"]:
        return _not_admitted("insufficient_eligible_lineage")
    limitations = [
        "Claim support and evidence type were assessed by the model, not independently verified. "
        "Different source lineages do not prove the sources are factually correct.",
        "Freshness is not established by this assessment; it does not verify current demand or willingness to pay.",
    ]
    if any(row.get("model_assessment") == "unclear" for row in rows):
        limitations.append("Additional assessed sources did not establish this claim and were not counted as support.")
    if set_aside_stale:
        limitations.append(
            f"{len(set_aside_stale)} cited source(s) were out of date and were set aside; "
            "they did not count toward the independent support for this claim."
        )
    inferred = {"finding": claim, "citations": list(eligible), "classification": "model_assessed_inference",
                "confidence": "tentative", "semantic_support_verified": False,
                "set_aside_stale_citations": sorted(set_aside_stale),
                "independent_source_count": min(lineage["independent_lineage_count"],
                                                original_lineage["independent_lineage_count"], len(publishers))}
    return {"ok": True, "status": "research_model_assessed_inference", "verified_findings": [],
            "reasonable_inferences": [inferred], "unresolved_disagreements": [],
            "missing_evidence": [{"finding": "Current demand and willingness to pay remain unverified"}],
            "limitations": limitations, "citations": [dict(index[cid]) for cid in eligible], "citation_count": len(eligible),
            "rendered_answer": "Model-assessed inference (tentative; not verified fact):\n\n" + claim
                + " [" + ", ".join(eligible) + "]\n\n" + " ".join(limitations),
            "strongest_opportunity_admitted": False, "generated_prose_is_evidence": False}
