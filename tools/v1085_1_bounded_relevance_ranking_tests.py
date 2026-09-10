from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
sys.path.insert(0, str(AGENT))

from context_relevance_ranking import rank_context_records, ranking_public_summary
from conversation_context import _memory_candidates, build_conversation_prompt


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


def records() -> list[dict]:
    return [
        {"id": "older", "type": "fact", "content": "Tomato garden spacing uses wide rows.", "importance": "medium", "state": "active"},
        {"id": "curated", "type": "preference", "content": "Marcus prefers practical tomato garden guidance.", "importance": "high", "state": "active", "operator_curated": True, "retention_confirmed": True},
        {"id": "recent", "type": "fact", "content": "Printer toner was replaced yesterday.", "importance": "low", "state": "active"},
    ]


def test_lexical_relevance_outranks_unrelated_recency() -> None:
    ranked = rank_context_records(records(), "tomato garden spacing")
    require(ranked[0][0]["id"] in {"older", "curated"}, "unrelated recent record outranked lexical matches")
    require(ranked[0][1].lexical_score > 0, "top record lacks lexical evidence")


def test_recency_breaks_otherwise_equal_candidates() -> None:
    rows = [
        {"id": "old", "type": "fact", "content": "same topic detail", "state": "active"},
        {"id": "new", "type": "fact", "content": "same topic detail", "state": "active"},
    ]
    ranked = rank_context_records(rows, "same topic")
    require(ranked[0][0]["id"] == "new", "recency did not break an equal relevance tie")
    require(ranked[0][1].recency_score > ranked[1][1].recency_score, "recency component not recorded")


def test_operator_curation_relationship_and_status_are_scored() -> None:
    ranked = rank_context_records(records(), "practical guidance")
    evidence = next(item for row, item in ranked if row["id"] == "curated")
    require(evidence.operator_curation_score == 4, "operator curation signal wrong")
    require(evidence.relationship_relevant and evidence.relationship_score == 2, "relationship relevance missing")
    require(evidence.status_score == 2, "active status missing")
    require(evidence.importance_score == 4, "importance signal missing")


def test_ineligible_status_is_not_ranked() -> None:
    rows = records() + [{"id": "deleted", "type": "preference", "content": "tomato garden secret", "state": "deleted", "importance": "high"}]
    ranked = rank_context_records(rows, "tomato garden")
    require("deleted" not in [row["id"] for row, _evidence in ranked], "deleted context was ranked")


def test_ranking_is_deterministic_bounded_and_content_free() -> None:
    first = rank_context_records(records(), "tomato garden spacing")
    second = rank_context_records(json.loads(json.dumps(records())), "tomato garden spacing")
    first_summary = ranking_public_summary(first)
    second_summary = ranking_public_summary(second)
    require(first_summary == second_summary, "equivalent ranking inputs changed evidence")
    require(len(first_summary["evidence"]) <= 12, "public ranking evidence is unbounded")
    rendered = json.dumps(first_summary).lower()
    for private in ("tomato garden spacing", "printer toner", "marcus prefers"):
        require(private not in rendered, f"ranking summary leaked content: {private}")
    require(first_summary["content_free"] and not first_summary["provider_invoked"], "ranking boundaries wrong")


def test_correction_suppression_remains_authoritative() -> None:
    stale = "Marcus lives in Dayton."
    corrected = "Marcus lives in Columbus."
    rows = [
        {"type": "personal_fact", "content": stale, "importance": "high"},
        {"type": "personal_fact", "content": corrected, "importance": "high", "superseded_content_digests": [__import__("hashlib").sha256(stale.encode()).hexdigest()]},
    ]
    candidates = _memory_candidates(rows, "Where does Marcus live?")
    texts = [row.get("content") for row, _important in candidates]
    require(corrected in texts and stale not in texts, "ranking reintroduced superseded content")


def test_prompt_metrics_report_ranking_without_provider_contact() -> None:
    packet = build_conversation_prompt(
        user_message="Explain tomato garden spacing.", self_model={"name": "Eidolon"}, desires={},
        memories=records(), project_context="", goal_context="", task_context="", conversation_history=[],
        context_size=4096, max_tokens=256,
    )
    metrics = packet.metrics
    require(metrics.context_ranked_candidate_count == 3, "ranked candidate count wrong")
    require(metrics.context_top_rank_score > 0 and metrics.context_ranked_lexical_matches >= 1, "ranking metrics missing")
    require(metrics.context_ranked_operator_curated >= 1, "operator-curated metric missing")
    require(not metrics.context_ranking_provider_invoked, "ranking claimed provider contact")


TESTS = [
    ("lexical_relevance_outranks_unrelated_recency", test_lexical_relevance_outranks_unrelated_recency),
    ("recency_breaks_otherwise_equal_candidates", test_recency_breaks_otherwise_equal_candidates),
    ("operator_curation_relationship_and_status_are_scored", test_operator_curation_relationship_and_status_are_scored),
    ("ineligible_status_is_not_ranked", test_ineligible_status_is_not_ranked),
    ("ranking_is_deterministic_bounded_and_content_free", test_ranking_is_deterministic_bounded_and_content_free),
    ("correction_suppression_remains_authoritative", test_correction_suppression_remains_authoritative),
    ("prompt_metrics_report_ranking_without_provider_contact", test_prompt_metrics_report_ranking_without_provider_contact),
]


def main() -> int:
    argparse.ArgumentParser().add_argument("--json", action="store_true")
    checks, passed = [], 0
    for name, fn in TESTS:
        try:
            fn()
        except Exception as error:
            checks.append({"name": name, "status": "fail", "message": f"{type(error).__name__}: {error}"})
        else:
            passed += 1
            checks.append({"name": name, "status": "pass", "message": ""})
    report = {"suite": "v1085.1-bounded-relevance-ranking", "ok": passed == len(TESTS), "status": "pass" if passed == len(TESTS) else "fail", "passed": passed, "total": len(TESTS), "checks": checks}
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
