from __future__ import annotations

"""The model must be asked to assess every source it was shown.

The synthesis prompt asked for four source assessments regardless of how many
sources were observed. With seven admitted sources, three were never assessed,
and an unassessed source carries no stance, so it can never support a claim or
count toward the two independent publishers a demand finding requires. The cap
was invisible in the receipts, so runs looked like the model judging every
source and finding most of them wanting.

The cap now follows the number of sources actually offered, with the output
budget raised to fit the extra assessments rather than truncating them.
"""

import json
import os
from pathlib import Path
import re
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for value in (str(ROOT), str(AGENT)):
    if value not in sys.path:
        sys.path.insert(0, value)
sys.dont_write_bytecode = True
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2731-0-0-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

from governed_public_web_research_adapter import (
    FINDINGS_SYNTHESIS_MAX_TOKENS,
    FINDINGS_TOKENS_PER_EXTRA_ASSESSMENT,
    MAX_FINDINGS_SYNTHESIS_MAX_TOKENS,
    MAX_SOURCE_ASSESSMENTS,
    GovernedPublicWebResearchAdapter,
)


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


SENTENCE = (
    "A survey of 1,200 content creators found that {n}% were dissatisfied with sponsorship payment timelines. "
    "Respondents reported waiting an average of {n} days for brand payments to clear in that period. "
    "Nearly half said they had written off at least one deal as unrecoverable during the same year."
)

captured: list[dict] = []


def fake_single_request(prompt, *, temperature, max_tokens, timeout_seconds=None):
    """Capture what the synthesis pass actually asks the model for."""
    captured.append({"prompt": prompt, "max_tokens": max_tokens})
    return {"content": json.dumps({
        "findings": [{"title": "Creators report payment delays",
                      "summary": "Creators report sponsorship payment delays.",
                      "citation_ids": ["web-0"], "uncertainties": ["Bounded evidence."]}],
        "limitations": ["Public evidence remains bounded."],
        "source_assessments": [],
    })}


def synthesize_with(document_count: int) -> dict:
    adapter = GovernedPublicWebResearchAdapter()
    citations, documents = [], {}
    for index in range(document_count):
        citation_id = f"web-{index}"
        citations.append({"citation_id": citation_id, "quality_score": 0.82,
                          "source_kind": "reputable_secondary", "public_url": f"https://example{index}.org/study"})
        documents[citation_id] = {
            "citation_id": citation_id, "title": f"Study {index}",
            "excerpt": SENTENCE.format(n=70 + index), "unverified_study_context": "",
            "publisher_claimed_dates": [], "source_kind": "reputable_secondary",
            "query_terms": ["creator", "sponsorship", "payment", "demand"],
            "candidate_name": "", "candidate_digest": "", "evidence_dimension": "demand",
        }
    adapter._transient_documents = documents
    captured.clear()
    adapter.synthesize(
        decomposition={"objective_shape": "single_candidate_dimension", "requested_result_count": 0,
                       "subquestions": [{"subquestion_id": "rq1", "evidence_dimension": "demand"}]},
        citations=citations,
    )
    require(captured, f"synthesis_requested_a_completion_for_{document_count}_documents")
    CHECKS.pop()
    return captured[-1]


def requested_assessments(prompt: str) -> int:
    match = re.search(r"Return at most one finding, (\d+) source assessments", prompt)
    if not match:
        raise AssertionError("assessment_cap_instruction_not_found_in_prompt")
    return int(match.group(1))


import research_claim_assessment  # noqa: E402  (imported for the patch target check)
import governed_public_web_research_adapter as adapter_module  # noqa: E402

adapter_module._single_synthesis_request = fake_single_request

# 1. The cap follows the number of sources actually offered.
for count, expected in ((2, 2), (4, 4), (7, 7)):
    call = synthesize_with(count)
    require(requested_assessments(call["prompt"]) == expected,
            f"a_run_with_{count}_sources_asks_for_{expected}_assessments")

# 2. It stays bounded rather than growing without limit.
large = synthesize_with(12)
require(requested_assessments(large["prompt"]) == MAX_SOURCE_ASSESSMENTS,
        "the_assessment_cap_stays_bounded_for_a_large_corpus")

# 3. The output budget grows with the cap, and stays bounded.
small = synthesize_with(4)
require(small["max_tokens"] == FINDINGS_SYNTHESIS_MAX_TOKENS,
        "a_four_source_run_keeps_the_original_token_budget")
seven = synthesize_with(7)
require(seven["max_tokens"] == FINDINGS_SYNTHESIS_MAX_TOKENS + 3 * FINDINGS_TOKENS_PER_EXTRA_ASSESSMENT,
        "extra_assessments_are_given_extra_output_budget")
require(large["max_tokens"] <= MAX_FINDINGS_SYNTHESIS_MAX_TOKENS,
        "the_token_budget_never_exceeds_its_ceiling")
require(seven["max_tokens"] > small["max_tokens"],
        "a_larger_corpus_is_not_asked_to_fit_the_smaller_budget")

# 4. Every offered source is still named in the prompt, so the model can assess it.
call = synthesize_with(7)
require(all(f"web-{index}" in call["prompt"] for index in range(7)),
        "every_offered_source_appears_in_the_prompt")

print(json.dumps({"suite": "v2731.0.0-source-assessment-cap", "passed": len(CHECKS), "total": len(CHECKS), "ok": True, "checks": CHECKS}))
