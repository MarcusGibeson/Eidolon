from __future__ import annotations

"""Does a finding supply the relation its question asked for? Measured, not enforced.

answers_objective catches a finding that admits it could not answer. It cannot
see one that answers something easier than what was asked. None of fifteen
stored how-question findings was a complete mechanism: "how do mRNA vaccines
produce an immune response" came back as "mRNA vaccines induce immune
responses" - on topic, supported, and a restatement of the question.

Whether a finding explains a mechanism is semantic. In a 55-case benchmark over
every stored finding plus controls, a deterministic answer-form check agreed with
hand labels on 15 of 20 how-question cases, failing exactly the agent-only and
acronym cases; a separate model judge agreed on 18 (19 once one inconsistent
hand label was corrected). Asked to infer the question type itself, the judge
read "task cancellation behaviour" as a mechanism question - so the relation is
now decided deterministically from the objective and handed to the judge.

    objective -> requested_relation (deterministic) -> synthesis -> answer judge
    (separate call, fixed level) -> answer_quality_codes (deterministic) -> receipt

"What were the causes of X" is answered by the causes. "Why did X happen" needs
the explanation that connects them. A configuration question needs actionable
settings, not a definition of the tool. Descriptive questions get no invented
depth requirement. Nothing here changes admission.
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
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2731-2-7-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

import governed_public_web_research_adapter as adapter_module
from bounded_autonomous_web_research import BoundedResearchSessionStore, _evaluate_evidence_policy
from bounded_research_history import sanitize_report
from research_claim_assessment import assess_source_claims
from research_evidence_policy import (
    DEPTH_REQUESTING_RELATIONS,
    REQUESTED_RELATIONS,
    requested_relation,
)
from research_source_classification import classify_source_kind
from research_web_intelligence_v2100 import NATIVE_RECEIPT_CONTRACT_VERSION


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


def digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


# --- the relation an objective asks for, decided deterministically ---------------

EXPECTED = {
    "Research how mRNA vaccines produce an immune response": "mechanism",
    "Research how ocean tides are generated": "mechanism",
    "Research how GPS works": "mechanism",
    "Research why the 1929 stock market crash happened": "explanation",
    "Research why the Titanic sank": "explanation",
    "Research the causes of the 1929 stock market crash": "causes",
    "Research what caused the Great Fire of London": "causes",
    "Research the difference between TCP and UDP": "comparison",
    "Research Stripe payment processing fee structure": "amount",
    "Research how much AWS S3 storage costs": "amount",
    "Research the current state of EU AI Act enforcement": "state",
    "Research PostgreSQL connection pooling configuration": "configuration",
    "Research how to configure PgBouncer transaction pooling": "configuration",
    "Research Python asyncio task cancellation behavior": "descriptive",
    "Research creator sponsorship payment delays demand.": "descriptive",
    "how ocean tides are generated": "mechanism",
}
wrong = {objective: requested_relation(objective) for objective, code in EXPECTED.items()
         if requested_relation(objective) != code}
require(not wrong, f"every_objective_gets_the_relation_it_asks_for{'' if not wrong else ':' + json.dumps(wrong)}")
require(requested_relation("") == "", "an_empty_objective_asks_for_nothing")
require(requested_relation("Research why the 1929 crash happened") != requested_relation(
    "Research the causes of the 1929 crash"), "why_and_causes_of_are_different_relations")
require(DEPTH_REQUESTING_RELATIONS == {"mechanism", "explanation"},
        "only_mechanism_and_explanation_request_depth")
require(set(EXPECTED.values()) == set(REQUESTED_RELATIONS), "every_relation_is_exercised")

# --- the judged level becomes three fields, through the live wrapper --------------


def live_row(cid: str, url: str) -> dict:
    return {"citation_id": cid, "public_url": url, "host": url.split("/")[2], "source_kind": classify_source_kind(url),
            "freshness": "fresh", "quality_score": 0.5, "relevance_score": 1.0, "source_digest": "",
            "candidate_digest": "", "evidence_dimension": "", "stance": "unknown", "evidence_producer_signal": "none",
            "source_identity_digest": "", "canonical_page_digest": "", "explicit_origin_digest": "",
            "publisher_digest": hashlib.sha256(url.split("/")[2].encode()).hexdigest(),
            "attribution_digest": "", "content_similarity_digest": "", "content_similarity_confidence": ""}


ROWS = [live_row("web-1", "https://tidesnotes.org/how-tides-work"),
        live_row("web-2", "https://oceanprimer.net/tides")]
CLAIM = "The Moon and Sun's gravity generate ocean tides."


def evaluate(objective: str, level: str | None) -> dict:
    finding = {"title": "Tides", "summary": CLAIM, "citation_ids": ["web-1", "web-2"],
               "uncertainties": ["Bounded evidence."]}
    payload = {"findings": [finding], "source_assessments": [
        {"citation_id": cid, "claim": CLAIM, "passage_index": 1, "assessment": "supports", "evidence_kind": "unknown"}
        for cid in ("web-1", "web-2")]}
    summary = assess_source_claims(payload, documents=[
        {"citation_id": "web-1", "excerpt": "The gravity of the Moon and the Sun raises the tides in the oceans."},
        {"citation_id": "web-2", "excerpt": "Ocean tides are produced by the gravitational pull of the Moon and Sun."},
    ], citations=ROWS)
    result = _evaluate_evidence_policy(payload={"findings": [finding]}, citations=ROWS, assessment_summary=summary,
                                       currency_requirement="reference", objective=objective,
                                       answer_quality_level=level)
    require(result.get("policy_code"), "the_wrapper_returned_a_real_evaluation")
    CHECKS.pop()
    return result


def fields(result: dict) -> tuple:
    return (result["answers_topic"], result["answers_requested_relation"], result["answers_requested_depth"])


HOW = "Research how ocean tides are generated"
WHY = "Research why the 1929 stock market crash happened"
CAUSES = "Research the causes of the 1929 stock market crash"
CONFIG = "Research PostgreSQL connection pooling configuration"
DESCRIBE = "Research Python asyncio task cancellation behavior"

require(fields(evaluate(HOW, "off_topic")) == ("no", "not_satisfied", "not_satisfied"), "off_topic_answers_nothing")
require(fields(evaluate(HOW, "topic_only")) == ("yes", "not_satisfied", "not_satisfied"),
        "a_how_restatement_is_on_topic_but_answers_neither_relation_nor_depth")
require(fields(evaluate(HOW, "partial")) == ("yes", "satisfied", "not_satisfied"),
        "an_agent_only_how_answer_answers_the_relation_but_not_the_depth")
require(fields(evaluate(HOW, "complete")) == ("yes", "satisfied", "satisfied"),
        "a_how_answer_with_intermediate_steps_satisfies_the_depth")
require(fields(evaluate(WHY, "partial")) == ("yes", "satisfied", "not_satisfied"),
        "a_why_answer_that_names_causes_without_the_explanation_lacks_depth")
require(fields(evaluate(WHY, "complete"))[2] == "satisfied", "a_why_answer_with_the_explanation_satisfies_the_depth")
require(fields(evaluate(CAUSES, "complete")) == ("yes", "satisfied", "not_requested"),
        "a_causes_of_question_is_fully_answered_by_the_causes")
require(fields(evaluate(CAUSES, "topic_only")) == ("yes", "not_satisfied", "not_requested"),
        "a_causes_of_question_answered_with_a_trading_volume_is_not_answered")
require(fields(evaluate(CONFIG, "topic_only")) == ("yes", "not_satisfied", "not_requested"),
        "defining_the_tool_does_not_answer_a_configuration_question")
require(fields(evaluate(CONFIG, "partial"))[1] == "partial", "naming_the_setting_without_how_is_partial")
require(fields(evaluate(CONFIG, "complete"))[1] == "satisfied", "actionable_settings_answer_a_configuration_question")
require(fields(evaluate(DESCRIBE, "complete")) == ("yes", "satisfied", "not_requested"),
        "a_descriptive_question_gets_no_invented_depth_requirement")

judged = evaluate(HOW, "partial")
require(judged["answer_quality_judged"] is True and judged["answer_quality_level"] == "partial"
        and judged["requested_relation"] == "mechanism", "a_judged_run_says_it_was_judged_and_what_was_asked")
unjudged = evaluate(HOW, None)
require(unjudged["answer_quality_judged"] is False and fields(unjudged) == ("", "", "")
        and unjudged["requested_relation"] == "mechanism",
        "an_unjudged_run_is_visibly_unjudged_not_a_quiet_pass_or_fail")
require(evaluate(HOW, "excellent")["answer_quality_judged"] is False, "an_out_of_vocabulary_level_is_unjudged")

# Measurement only: the verdict is identical whatever the judge said.
ADMISSION_KEYS = ("would_admit", "finding_condition_failures", "citation_condition_failures",
                  "independent_publisher_count", "required_publisher_count", "supporting_authority_tier")
baseline = {key: unjudged[key] for key in ADMISSION_KEYS}
for level in ("off_topic", "topic_only", "partial", "complete"):
    for objective in (HOW, WHY, CAUSES, CONFIG, DESCRIBE):
        result = evaluate(objective, level)
        require({key: result[key] for key in ADMISSION_KEYS} == {key: evaluate(objective, None)[key]
                                                                for key in ADMISSION_KEYS},
                "the_judge_never_changes_the_verdict")
        CHECKS.pop()
CHECKS.append("no_answer_level_changes_admission_for_any_relation")

# --- the adapter's judge: a separate call, given the relation, returning a code ---

captured: list[str] = []


def fake_judge(reply: str):
    def judge(prompt: str) -> str:
        captured.append(prompt)
        return reply
    return judge


adapter = adapter_module.GovernedPublicWebResearchAdapter()
adapter.answer_judge = fake_judge('{"answer":"partial"}')
graded = adapter.judge_answer_quality(objective=HOW, finding=CLAIM, requested_relation="mechanism")
require(graded == {"ok": True, "status": "answer_quality_judged", "answer_level": "partial",
                   "provider_contacted": True}, "the_judge_returns_one_fixed_level")
require("The question asks for how something works or comes about" in captured[-1]
        and "intermediate steps" in captured[-1], "the_judge_is_told_the_relation_rather_than_inferring_it")
require("Moon" not in json.dumps(graded), "the_judge_result_carries_no_finding_text")

adapter.judge_answer_quality(objective=CAUSES, finding=CLAIM, requested_relation="causes")
require("an explanation is not required" in captured[-1], "a_causes_judge_does_not_demand_an_explanation")
adapter.judge_answer_quality(objective=WHY, finding=CLAIM, requested_relation="explanation")
require("explains how the causes produced the outcome" in captured[-1], "a_why_judge_demands_the_explanation")
adapter.judge_answer_quality(objective=CONFIG, finding=CLAIM, requested_relation="configuration")
require("actionable settings" in captured[-1], "a_configuration_judge_demands_actionable_settings")

calls_before = len(captured)
require(adapter.judge_answer_quality(objective=HOW, finding=CLAIM, requested_relation="astrology")["status"]
        == "answer_quality_not_judgeable" and len(captured) == calls_before,
        "an_unknown_relation_is_not_judged_and_costs_no_call")
adapter.answer_judge = fake_judge("I think it is quite good")
require(adapter.judge_answer_quality(objective=HOW, finding=CLAIM, requested_relation="mechanism")["status"]
        == "answer_quality_judge_invalid", "an_unparseable_judgement_is_invalid_not_a_level")


def exploding(prompt: str) -> str:
    raise RuntimeError("provider down")


adapter.answer_judge = exploding
require(adapter.judge_answer_quality(objective=HOW, finding=CLAIM, requested_relation="mechanism")["status"]
        == "answer_quality_judge_failed", "a_failing_judge_is_a_status_not_an_exception")

synth_calls: list[str] = []
fixture_synth = adapter_module.GovernedPublicWebResearchAdapter(synthesizer=lambda prompt: synth_calls.append(prompt) or "{}")
require(fixture_synth.judge_answer_quality(objective=HOW, finding=CLAIM, requested_relation="mechanism")["status"]
        == "answer_quality_judge_unavailable" and not synth_calls,
        "a_fixture_synthesizer_is_never_reused_as_the_judge")

# --- end to end: the judge runs inside the real research run -----------------------

BUDGET = {"max_queries": 3, "max_candidates": 8, "max_observed_pages": 5, "max_total_bytes": 65_536,
          "max_elapsed_seconds": 120, "max_source_failures": 3}
URLS = ["https://tidesnotes.org/how-tides-work", "https://oceanprimer.net/tides"]
EXCERPTS = {URLS[0]: "The gravity of the Moon and the Sun raises the tides in the oceans.",
            URLS[1]: "Ocean tides are produced by the gravitational pull of the Moon and Sun."}


class TidesAdapter:
    """Two readable sources and one supported, agent-only finding."""

    def __init__(self) -> None:
        self.search_calls = 0
        self.urls: dict[str, str] = {}

    def describe(self) -> dict[str, object]:
        return {"adapter_code": "v2731.2.7-answer-quality-fixture", "read_only": True,
                "allowed_methods": ["GET", "HEAD"], "search_supported": True,
                "private_network_allowed": False, "redirect_revalidation_required": True,
                "credentials_allowed": False, "cookies_allowed": False, "uploads_allowed": False,
                "side_effects_allowed": False, "max_bytes_enforced": True, "timeout_enforced": True}

    def search(self, query: str, *, limit: int, timeout_seconds: float) -> list[dict[str, object]]:
        self.search_calls += 1
        if self.search_calls > 1:
            return []
        return [{"url": url, "source_kind": "unknown", "fetched_at": "2026-09-10T00:00:00+00:00"} for url in URLS]

    def observe(self, candidate: dict[str, object], *, plan: dict[str, object], max_bytes: int,
                timeout_seconds: float) -> dict[str, object]:
        url = str(candidate.get("public_url") or candidate.get("url") or "")
        cid = "web-" + hashlib.sha256(url.encode()).hexdigest()[:16]
        self.urls[cid] = url
        row = {
            "contract_version": NATIVE_RECEIPT_CONTRACT_VERSION, "receipt_kind": "source_observation",
            "authoritative": True, "terminal": True,
            "operation_digest": digest({"operation": cid}), "terminal_result_digest": digest({"terminal": cid}),
            "source_observed": True, "plan_digest": plan["plan_digest"],
            "source_candidate_digest": candidate["source_candidate_digest"],
            "claim_code": candidate.get("subquestion_id", "rq1"), "stance": "unknown",
            "evidence_digest": digest({"evidence": cid}), "citation_id": cid,
            "source_kind": candidate.get("source_kind", "unknown"), "quality_score": 0.5,
            "freshness_known": True, "fresh_enough": True, "relevance_score": 0.85,
            "observed_bytes": min(512, max_bytes), "public_url": url, "evidence_producer_signal": "none",
        }
        row["receipt_digest"] = digest(row)
        return row

    def synthesize(self, *, decomposition, citations, **kwargs) -> dict[str, object]:
        rows = [dict(row) for row in citations]
        ids = [str(row["citation_id"]) for row in rows]
        finding = {"title": "Tides", "summary": CLAIM, "citation_ids": ids[:1],
                   "uncertainties": ["The excerpts name the forces, not the process."]}
        assessed = {"findings": [finding], "source_assessments": [
            {"citation_id": cid, "claim": CLAIM, "passage_index": 1, "assessment": "supports",
             "evidence_kind": "unknown"} for cid in ids]}
        summary = assess_source_claims(assessed, documents=[{"citation_id": cid, "excerpt": EXCERPTS[self.urls[cid]]}
                                                            for cid in ids], citations=rows)
        return {"ok": True, "status": "research_synthesis_ready",
                "payload": {"findings": [finding], "limitations": ["Fixture evidence only."]},
                "source_assessment_summary": summary, "provider_contacted": False, "provider_request_count": 0}


class JudgedTidesAdapter(TidesAdapter):
    def __init__(self) -> None:
        super().__init__()
        self.judge_calls: list[dict[str, str]] = []

    def judge_answer_quality(self, *, objective: str, finding: str, requested_relation: str) -> dict[str, object]:
        self.judge_calls.append({"objective": objective, "finding": finding, "requested_relation": requested_relation})
        return {"ok": True, "status": "answer_quality_judged", "answer_level": "partial", "provider_contacted": True}


def run(adapter, label: str) -> dict:
    store = BoundedResearchSessionStore(RUNTIME / label)
    created = store.create_session(f"create-{label}", objective=HOW, budget=BUDGET)
    require(created["ok"], f"{label}_session_created")
    session = created["result"]
    authorized = store.authorize_session(f"authorize-{label}", session_id=session["session_id"],
                                         session_digest=session["session_digest"], public_query_confirmed=True)
    require(authorized["ok"], f"{label}_session_authorized")
    executed = store.execute_session(f"execute-{label}", session_id=session["session_id"],
                                     authorization_digest=authorized["result"]["authorization_digest"],
                                     adapter=adapter)
    require(executed["ok"], f"{label}_session_completes")
    return executed["result"]["report"]


judged_adapter = JudgedTidesAdapter()
report = run(judged_adapter, "judged")
require(len(judged_adapter.judge_calls) == 1, "the_research_run_called_the_judge_once")
require(judged_adapter.judge_calls[0]["finding"] == CLAIM and judged_adapter.judge_calls[0]["requested_relation"]
        == "mechanism", "the_judge_was_given_the_finding_and_the_deterministic_relation")
policy = report.get("evidence_policy_evaluation") or {}
require(policy.get("answer_quality_status") == "answer_quality_judged" and policy.get("answer_quality_judged") is True,
        "the_receipt_proves_the_judge_ran")
require(policy.get("requested_relation") == "mechanism" and policy.get("answer_quality_level") == "partial",
        "the_receipt_names_what_was_asked_and_what_the_judge_found")
require((policy.get("answers_topic"), policy.get("answers_requested_relation"), policy.get("answers_requested_depth"))
        == ("yes", "satisfied", "not_satisfied"), "tides_is_on_topic_names_the_agent_and_lacks_the_mechanism")
persisted = sanitize_report(report)["evidence_policy_evaluation"]
require(persisted["answers_requested_depth"] == "not_satisfied" and persisted["answer_quality_judged"] is True
        and persisted["requested_relation"] == "mechanism", "the_answer_quality_fields_survive_persistence")

control = run(TidesAdapter(), "control")
control_policy = control.get("evidence_policy_evaluation") or {}
require(control_policy.get("answer_quality_status") == "answer_quality_judge_unavailable"
        and control_policy.get("answer_quality_judged") is False and control_policy.get("answers_topic") == "",
        "an_adapter_without_a_judge_is_reported_as_unjudged")
require({key: control_policy.get(key) for key in ADMISSION_KEYS} == {key: policy.get(key) for key in ADMISSION_KEYS},
        "the_run_admits_exactly_as_it_would_without_the_judge")

print(json.dumps({"suite": "v2731.2.7-answer-quality-measurement", "passed": len(CHECKS),
                  "total": len(CHECKS), "ok": True, "checks": CHECKS}))
