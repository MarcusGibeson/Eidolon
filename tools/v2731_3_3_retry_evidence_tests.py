from __future__ import annotations

"""A repair retry changes how the answer is serialized, not what evidence it may use.

When the first synthesis reply was not valid JSON, the repair retry re-offered
one passage per source: the first that fit a smaller character limit. A finding
whose only support sat in passage 2 or 3 lost that support because of a
misplaced brace, and grounding then refused the claim for want of evidence the
model had been shown a moment earlier.

The retry now re-offers each source's whole option set - the same passages, ids
and indexes as the first attempt. Nothing else about the retry changes: its
wording, its single attempt, its output limit and temperature. The retry is
still reported as a retry, and grounding still accepts only passages from the
offered set.
"""

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
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2731-3-3-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

from governed_public_web_research_adapter import GovernedPublicWebResearchAdapter
import research_claim_assessment as rca
from research_claim_assessment import grounded_supporting_citation_ids


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


CLAIM = "Loss detection halves the congestion window."
SUPPORT = "Loss detection halves the congestion window immediately after a timeout."
FILLER = ["The congestion control process has several parts studied by engineers.",
          "Researchers continue to publish new variants of the algorithm every year."]
FIRST = "UNTRUSTED PUBLIC DOCUMENTS:\n"
RETRY = "UNTRUSTED COMPACT PUBLIC DOCUMENTS:\n"


def document(cid: str, sentences: list[str]) -> dict:
    return {"citation_id": cid, "title": f"Source {cid}", "excerpt": " ".join(sentences), "unverified_study_context": "",
            "publisher_claimed_dates": [], "attribution_urls": [], "public_url": f"https://{cid}-example.org/tcp",
            "source_kind": "unknown", "query_terms": ["tcp"], "candidate_name": "", "candidate_digest": "",
            "evidence_dimension": ""}


class Model:
    """Breaks its first reply; on the retry, cites a passage stating the claim wherever one is offered."""

    def __init__(self, extra_rows=()) -> None:
        self.prompts: list[str] = []
        self.extra_rows = list(extra_rows)

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if len(self.prompts) == 1:
            return '{"findings": [ not valid'
        docs = json.loads(prompt.split(RETRY, 1)[1])
        rows = []
        for d in docs:
            hit = next((p for p in d["passages"] if "halves" in p["text"]), None)
            rows.append({"citation_id": d["citation_id"], "claim": CLAIM, "evidence_kind": "unknown",
                         "passage_index": (hit or d["passages"][0])["passage_index"],
                         "assessment": "supports" if hit else "unclear"})
        return json.dumps({"findings": [{"title": "Loss", "summary": CLAIM, "citation_ids": [docs[0]["citation_id"]],
                                         "uncertainties": ["u"]}], "limitations": ["l"],
                           "source_assessments": rows + self.extra_rows})


QUESTION = {"subquestions": [{"question": "How does TCP congestion control work"}]}
DEMAND = {"objective_shape": "single_candidate_dimension",
          "subquestions": [{"question": "What evidence shows demand for TCP tuning tools", "evidence_dimension": "demand"}]}


def run(position: int, extra_rows=(), decomposition=QUESTION):
    witness = list(FILLER)
    witness.insert(position - 1, SUPPORT)
    docs = {"web-1": document("web-1", witness),
            "web-2": document("web-2", FILLER + ["A third general sentence about networks and traffic appears."])}
    calls: list[dict] = []
    original = rca.assess_source_claims

    def recording(payload, **kwargs):
        calls.append(kwargs)
        return original(payload, **kwargs)

    rca.assess_source_claims = recording
    try:
        model = Model(extra_rows)
        adapter = GovernedPublicWebResearchAdapter(synthesizer=model)
        adapter._transient_documents.update(docs)
        adapter.set_synthesis_time_budget(600)
        result = adapter.synthesize(decomposition=decomposition,
                                    citations=[{"citation_id": cid, "quality_score": 0.5} for cid in docs])
    finally:
        rca.assess_source_claims = original
    return model, calls, result


# --- the retry re-offers the first attempt's options, nothing more and nothing less ---

model, calls, result = run(2)
first = json.loads(model.prompts[0].split(FIRST, 1)[1])
retry = json.loads(model.prompts[1].split(RETRY, 1)[1])
sets = calls[0]["option_sets"]
require(len(model.prompts) == 2 and model.prompts[1].startswith("You are repairing the structure"),
        "the_malformed_reply_triggers_the_unchanged_repair_retry")
require([d["citation_id"] for d in retry] == [d["citation_id"] for d in first],
        "every_source_offered_first_is_offered_again_and_no_other")
require(all(r["passages"] == f["passages"] == sets[f["citation_id"]].passages() for r, f in zip(retry, first)),
        "the_retry_shows_the_same_set_with_the_same_ids_text_order_and_indexes")
require(result["status"] == "research_synthesis_generated_after_retry" and result["generation_retry_used"] is True
        and result["provider_request_count"] == 2, "the_retry_is_still_reported_as_a_retry")

# --- the causal witness: support that exists only in passage 2 or 3 --------------------

for position in (2, 3):
    model, calls, result = run(position)
    retry = json.loads(model.prompts[1].split(RETRY, 1)[1])
    offered = next(p for d in retry if d["citation_id"] == "web-1" for p in d["passages"] if "halves" in p["text"])
    require(offered["passage_index"] == position, f"the_supporting_passage_is_passage_{position}_on_the_retry")
    rows = result["source_assessment_summary"]["assessments"]
    require(grounded_supporting_citation_ids(rows, CLAIM) == ["web-1"]
            and any(r["passage_digest"] == hashlib.sha256(SUPPORT.encode()).hexdigest() for r in rows),
            f"support_found_only_in_passage_{position}_is_grounded_after_a_retry")

# --- grounding still accepts only passages from the offered set ------------------------

model, calls, result = run(2, extra_rows=[
    {"citation_id": "web-1", "claim": CLAIM, "passage_index": 4, "assessment": "supports", "evidence_kind": "unknown"},
    {"citation_id": "web-1", "claim": CLAIM, "passage_id": "f" * 16, "assessment": "supports", "evidence_kind": "unknown"},
])
summary = result["source_assessment_summary"]
require(summary["rejected_assessment_counts"].get("unobserved_passage_index") == 1
        and summary["selector_diagnostics"].get("above_source_range") == 1,
        "a_retry_selection_beyond_the_set_is_refused")
require(summary["rejected_assessment_counts"].get("unobserved_passage_id") == 1,
        "a_passage_id_outside_the_set_is_refused")
texts = {hashlib.sha256(p["text"].encode()).hexdigest() for s in calls[0]["option_sets"].values() for p in s.passages()}
require(all(r["passage_digest"] in texts for r in summary["assessments"]),
        "every_accepted_assessment_cites_a_passage_from_the_offered_set")

# --- demand keeps the one-passage retry until demand migrates on its own terms ---------

model, calls, result = run(2, decomposition=DEMAND)
retry = json.loads(model.prompts[1].split(RETRY, 1)[1])
require(len(model.prompts) == 2 and all(len(d["passages"]) <= 1 for d in retry),
        "a_demand_retry_still_offers_one_passage_per_source")
require(not any("halves" in p["text"] for d in retry for p in d["passages"])
        and not grounded_supporting_citation_ids(result["source_assessment_summary"]["assessments"], CLAIM),
        "so_demand_retry_behaviour_is_unchanged_by_this_step")

print(json.dumps({"suite": "v2731.3.3-retry-evidence", "passed": len(CHECKS), "total": len(CHECKS),
                  "ok": True, "checks": CHECKS}))
