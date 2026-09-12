from __future__ import annotations

"""Synthesis and grounding read one set of passage options, built once.

The adapter offered each source's passage options, and grounding rebuilt them
from the excerpt to check the model's selection. The two lists agreed only
because both callers happened to derive them the same way. Offer a source more
options than the rebuild produces and grounding refuses a passage the model was
actually shown - the passage-index-6 case in the offer-cap experiment.

OptionSet makes that identity structural. It is built once per offered source,
renders the prompt's passages, supplies a retry's subset under the original
indexes, and is what grounding resolves against. A set that is missing, keyed to
another source, or built from different text is refused, never quietly rebuilt.
Nothing else changes: the cap stays at three, and a caller that passes no sets -
the demand planner, harnesses - gets the options it always did.
"""

import dataclasses
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for value in (str(ROOT), str(AGENT)):
    if value not in sys.path:
        sys.path.insert(0, value)
sys.dont_write_bytecode = True
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2731-3-2-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

from governed_public_web_research_adapter import GovernedPublicWebResearchAdapter
import research_claim_assessment as rca
from research_claim_assessment import (
    PASSAGE_OPTION_LIMIT,
    OptionSet,
    assess_source_claims,
    disqualifying_rejections,
    passage_options,
)
import research_evidence_directions


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


CLAIM = "Loss detection halves the congestion window."
SENTENCES = [f"Step {n} of the process is described here in enough words to quote." for n in range(1, 9)]
EXCERPT = " ".join(SENTENCES)


def pid(cid: str, text: str) -> str:
    return hashlib.sha256((cid + "\0" + text).encode()).hexdigest()[:16]


# --- the set --------------------------------------------------------------------

offered = OptionSet.of("web-1", EXCERPT)
require(offered.choices() == passage_options("web-1", EXCERPT),
        "the_set_holds_exactly_the_options_grounding_always_derived")
require(len(offered.options) == PASSAGE_OPTION_LIMIT == 3, "the_offer_cap_is_still_three")
require([p["passage_index"] for p in offered.passages()] == [1, 2, 3]
        and list(offered.passages()[0]) == ["passage_id", "text", "passage_index"],
        "offered_passages_are_numbered_from_one_in_the_prompts_key_order")
require(all(option_id == pid("web-1", text) and text in EXCERPT for option_id, text in offered.options),
        "every_option_is_observed_text_bound_to_its_source")
require(json.loads(json.dumps(offered.passages())) == offered.passages(),
        "the_offered_passages_survive_serialization_unchanged")
try:
    offered.options = ()  # type: ignore[misc]
    frozen = False
except dataclasses.FrozenInstanceError:
    frozen = True
require(frozen, "a_set_cannot_be_altered_once_built")
require(research_evidence_directions.passage_options is rca.passage_options,
        "the_demand_planner_still_reads_the_unchanged_option_function")

# --- synthesis offers the set that grounding resolves against --------------------


class Stub:
    """A model that picks each source's last offered passage; optionally breaks the first reply."""

    def __init__(self, break_first: bool) -> None:
        self.break_first = break_first
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if self.break_first and len(self.prompts) == 1:
            return "not json"
        marker = next(m for m in ("UNTRUSTED COMPACT PUBLIC DOCUMENTS:\n", "UNTRUSTED PUBLIC DOCUMENTS:\n") if m in prompt)
        docs = json.loads(prompt.split(marker, 1)[1])
        return json.dumps({
            "findings": [{"title": "Loss", "summary": CLAIM, "citation_ids": [docs[0]["citation_id"]], "uncertainties": ["u"]}],
            "limitations": ["l"],
            "source_assessments": [{"citation_id": d["citation_id"], "claim": CLAIM, "assessment": "supports",
                                    "passage_index": d["passages"][-1]["passage_index"], "evidence_kind": "unknown"}
                                   for d in docs],
        })


def document(cid: str) -> dict:
    return {"citation_id": cid, "title": f"Source {cid}", "excerpt": EXCERPT, "unverified_study_context": "",
            "publisher_claimed_dates": [], "attribution_urls": [], "public_url": f"https://{cid}-example.org/tcp",
            "source_kind": "unknown", "query_terms": ["tcp"], "candidate_name": "", "candidate_digest": "",
            "evidence_dimension": ""}


def synthesize(break_first: bool):
    grounding_calls: list[dict] = []
    original = rca.assess_source_claims

    def recording(payload, **kwargs):
        grounding_calls.append(kwargs)
        return original(payload, **kwargs)

    rca.assess_source_claims = recording
    try:
        stub = Stub(break_first)
        adapter = GovernedPublicWebResearchAdapter(synthesizer=stub)
        adapter._transient_documents.update({cid: document(cid) for cid in ("web-1", "web-2", "web-3")})
        adapter.set_synthesis_time_budget(600)
        result = adapter.synthesize(decomposition={"subquestions": [{"question": "How does TCP congestion control work"}]},
                                    citations=[{"citation_id": cid, "quality_score": 0.5} for cid in ("web-1", "web-2", "web-3")])
    finally:
        rca.assess_source_claims = original
    return stub, grounding_calls, result


stub, calls, result = synthesize(break_first=False)
require(result["ok"] and len(calls) == 1, "one_grounding_call_after_one_synthesis")
sets = calls[0]["option_sets"]
first_pass = json.loads(stub.prompts[0].split("UNTRUSTED PUBLIC DOCUMENTS:\n", 1)[1])
require(sorted(sets) == sorted(d["citation_id"] for d in first_pass)
        and all(isinstance(s, OptionSet) and s.citation_id == cid for cid, s in sets.items()),
        "grounding_receives_one_set_per_offered_source")
require(all(d["passages"] == sets[d["citation_id"]].passages() for d in first_pass),
        "the_prompt_shows_exactly_the_sets_ids_text_and_order")
grounded_docs = {d["citation_id"]: d for d in calls[0]["documents"]}
require(all(sets[cid].excerpt == grounded_docs[cid]["excerpt"] for cid in sets),
        "each_set_is_bound_to_the_excerpt_grounding_checks_quotes_against")
require(result["source_assessment_summary"]["grounded_assessment_count"] == 3
        and not result["source_assessment_summary"]["rejected_assessment_counts"],
        "the_models_selections_ground_against_the_offered_sets")

stub, calls, result = synthesize(break_first=True)
require(result["ok"] and result["generation_retry_used"] and len(stub.prompts) == 2, "the_repair_retry_ran")
sets = calls[0]["option_sets"]
retry = json.loads(stub.prompts[1].split("UNTRUSTED COMPACT PUBLIC DOCUMENTS:\n", 1)[1])
require(all(passage in sets[d["citation_id"]].passages() for d in retry for passage in d["passages"]),
        "a_retry_reoffers_options_from_the_same_set_under_their_original_indexes")
require(result["source_assessment_summary"]["grounded_assessment_count"] == len(retry)
        and not result["source_assessment_summary"]["rejected_assessment_counts"],
        "a_retry_selection_grounds_against_the_same_set")

# --- the passage-index-6 case -----------------------------------------------------

SIX = OptionSet("web-1", EXCERPT, tuple((pid("web-1", text), text) for text in SENTENCES[:6]))
DOCS = [{"citation_id": "web-1", "excerpt": EXCERPT}]
CITES = [{"citation_id": "web-1"}]


def ground(rows, **kwargs):
    payload = {"source_assessments": [{"citation_id": "web-1", "claim": CLAIM, "assessment": "supports",
                                       "evidence_kind": "unknown", **row} for row in rows]}
    return assess_source_claims(payload, documents=DOCS, citations=CITES, **kwargs)


shared = ground([{"passage_index": 6}], option_sets={"web-1": SIX})
require(shared["grounded_assessment_count"] == 1
        and shared["assessments"][0]["passage_digest"] == hashlib.sha256(SENTENCES[5].encode()).hexdigest(),
        "a_passage_offered_from_a_shared_set_grounds_however_far_down_it_sits")
require(ground([{"passage_id": pid("web-1", SENTENCES[5])}], option_sets={"web-1": SIX})["grounded_assessment_count"] == 1,
        "the_same_passage_selected_by_id_grounds_too")
rebuilt = ground([{"passage_index": 6}])
require(rebuilt["grounded_assessment_count"] == 0
        and rebuilt["selector_diagnostics"] == {"above_source_range": 1},
        "rebuilding_the_options_refuses_it_as_never_offered_the_failure_the_set_removes")

for label, option_sets in (("built_from_different_text", {"web-1": OptionSet.of("web-1", EXCERPT[:-10])}),
                           ("missing", {}),
                           ("keyed_to_another_source", {"web-1": OptionSet.of("web-2", EXCERPT)}),
                           ("not_a_set", {"web-1": passage_options("web-1", EXCERPT)})):
    refused = ground([{"passage_index": 1}, {"passage_id": pid("web-1", SENTENCES[0])}], option_sets=option_sets)
    require(refused["grounded_assessment_count"] == 0
            and refused["rejected_assessment_counts"] == {"option_set_mismatch": 2}
            and disqualifying_rejections(refused["rejected_assessment_counts"]) == {"option_set_mismatch": 2},
            f"a_set_{label}_is_refused_never_rebuilt")

quoted = ground([{"evidence_quote": SENTENCES[0]}], option_sets={})
require(quoted["grounded_assessment_count"] == 1,
        "a_selection_by_quote_is_still_checked_against_the_observed_text_itself")

print(json.dumps({"suite": "v2731.3.2-option-set-identity", "passed": len(CHECKS), "total": len(CHECKS),
                  "ok": True, "checks": CHECKS}))
