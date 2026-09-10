from __future__ import annotations

"""Quotable text must not require tidy sentence boundaries.

Passages were only offered for segments of 30-600 characters that fell between
sentence breaks. A page that is one long unbroken paragraph produced none, so it
was dropped from the prompt entirely and the model never assessed it. Those
sources then showed up downstream as unverified source types, and a claim could
not reach two supporting publishers because several sources were never seen.

Provenance is the constraint that matters here: an assessment is only retained
when its quote appears verbatim in the observed excerpt. Every option must
therefore stay an exact slice of that excerpt, which these checks pin down.
"""

import json
import os
import random
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for value in (str(ROOT), str(AGENT)):
    if value not in sys.path:
        sys.path.insert(0, value)
sys.dont_write_bytecode = True
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2730-9-9-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

from research_claim_assessment import (
    PASSAGE_MAX_CHARS,
    PASSAGE_MIN_CHARS,
    PASSAGE_OPTION_LIMIT,
    assess_source_claims,
    passage_options,
)


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


PROSE = (
    "A survey of 1,200 content creators found that 87% were dissatisfied with payment timelines. "
    "Respondents reported waiting an average of 60 days for sponsorship payments to clear. "
    "Nearly half said they had written off at least one brand deal as unrecoverable."
)
UNBROKEN = "Creator sponsorship payment demand " + "with further detail on respondents " * 30
FRAGMENTS = "Creators wait.\nBrands delay.\nInvoices stall.\nPayments slip.\nNobody is happy."

# --- the regression this fixes ------------------------------------------------

require(passage_options("web-1", UNBROKEN), "an_unbroken_paragraph_is_quotable")
require(passage_options("web-1", PROSE), "ordinary_prose_is_still_quotable")
require(len(passage_options("web-1", PROSE)) == 3, "prose_offers_the_full_option_limit")

# --- the provenance contract --------------------------------------------------

CORPUS = [PROSE, UNBROKEN, FRAGMENTS, "", "   ", "\n\n\n", "Short.", "x" * 2000,
          "One sentence that is comfortably long enough to stand on its own as evidence."]
random.seed(20260910)
alphabet = "abcdefghij ....!!\n\n  ?"
for _ in range(400):
    CORPUS.append("".join(random.choice(alphabet) for _ in range(random.randint(0, 900))))

verbatim = bounded = capped = deterministic = True
for text in CORPUS:
    options = passage_options("web-fuzz", text)
    if len(options) > PASSAGE_OPTION_LIMIT:
        capped = False
    for option in options:
        if option["text"] not in text:
            verbatim = False
        if not PASSAGE_MIN_CHARS <= len(option["text"]) <= PASSAGE_MAX_CHARS:
            bounded = False
    if passage_options("web-fuzz", text) != options:
        deterministic = False

require(verbatim, "every_offered_passage_is_verbatim_observed_text")
require(bounded, "every_offered_passage_respects_the_length_bounds")
require(capped, "the_option_limit_is_never_exceeded")
require(deterministic, "passage_extraction_is_deterministic")

# Grounding recomputes the options, so identical input must yield identical ids.
require(
    [row["passage_id"] for row in passage_options("web-1", PROSE)]
    == [row["passage_id"] for row in passage_options("web-1", PROSE)],
    "passage_ids_are_stable_across_calls",
)
require(
    passage_options("web-1", PROSE)[0]["passage_id"] != passage_options("web-2", PROSE)[0]["passage_id"],
    "passage_ids_stay_bound_to_their_source",
)

# Long runs are cut at whitespace rather than through a word.
for option in passage_options("web-1", UNBROKEN):
    tail = UNBROKEN[UNBROKEN.index(option["text"]) + len(option["text"]):]
    require(not tail or tail[0].isspace() or option["text"][-1].isspace(), "long_runs_are_cut_at_whitespace")
    CHECKS.pop()
CHECKS.append("long_runs_are_cut_at_whitespace")

require(passage_options("web-1", "") == [], "empty_text_offers_nothing")
require(passage_options("web-1", "Short.") == [], "text_below_the_minimum_offers_nothing")

# --- end to end: an offered passage survives grounding ------------------------

def ground(text: str, passage_index: int = 1) -> dict:
    documents = [{"citation_id": "web-1", "excerpt": text}]
    citations = [{"citation_id": "web-1", "public_url": "https://example.org/study",
                  "source_kind": "reputable_secondary", "freshness": "fresh", "relevance_score": 1.0}]
    payload = {"source_assessments": [{
        "citation_id": "web-1", "claim": "Creators report sponsorship payment delays.",
        "passage_index": passage_index, "assessment": "supports",
        "dimension": "demand", "evidence_kind": "survey_result",
    }]}
    return assess_source_claims(payload, documents=documents, citations=citations, required_dimension="demand")


for label, text in (("prose", PROSE), ("unbroken", UNBROKEN)):
    result = ground(text)
    require(result["status"] == "source_assessments_grounded", f"an_offered_passage_grounds_for_{label}")
    require(result["grounded_assessment_count"] == 1, f"exactly_one_assessment_is_retained_for_{label}")
    require(not result["rejected_assessment_counts"], f"nothing_is_rejected_for_{label}")

# An index outside the offered range is still refused.
out_of_range = ground(PROSE, passage_index=99)
require(out_of_range["grounded_assessment_count"] == 0, "an_unoffered_passage_index_is_refused")
require(
    out_of_range["rejected_assessment_counts"].get("unobserved_passage_index") == 1,
    "an_unoffered_passage_index_is_recorded_as_such",
)

print(json.dumps({"suite": "v2730.9.9-passage-extraction", "passed": len(CHECKS), "total": len(CHECKS), "ok": True, "checks": CHECKS}))
