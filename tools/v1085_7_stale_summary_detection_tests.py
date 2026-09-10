from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
TOOLS = ROOT / "tools"
sys.path[:0] = [str(AGENT), str(TOOLS)]

from context_stale_summary_detection import (
    content_digest,
    filter_stale_continuity_summaries,
    stale_summary_evidence_contains_private_fields,
)
from conversation_context import build_conversation_prompt
import post_review_development_verify as verify


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


def test_exact_corrected_digest_suppresses_stale_summary() -> None:
    old = "The office is in Dayton."
    summaries = [
        {"id": "summary-old", "content": old, "content_digest": content_digest(old)},
        {"id": "summary-current", "content": "The office opens at nine."},
    ]
    records = [{"id": "memory-new", "superseded_content_digests": [content_digest(old)]}]
    eligible, evidence = filter_stale_continuity_summaries(summaries, records)
    require([row["id"] for row in eligible] == ["summary-current"], "stale corrected summary remained eligible")
    require(evidence.exact_digest_matches == 1, "exact correction evidence was not counted")


def test_explicit_lineage_and_current_session_evidence_are_honored() -> None:
    summaries = [{"id": "summary-old", "content": "Old fact"}]
    eligible, evidence = filter_stale_continuity_summaries(
        summaries,
        [],
        current_session_records=[{"corrects_summary_id": "summary-old"}],
    )
    require(not eligible, "explicit current-session correction did not suppress summary")
    require(evidence.current_session_conflicts == 1, "current-session conflict not recorded")
    require(evidence.explicit_lineage_matches == 1, "explicit lineage not recorded")


def test_retracted_and_deleted_sources_invalidate_summaries() -> None:
    summaries = [
        {"id": "summary-r", "content": "Retracted source", "source_record_ids": ["record-r"]},
        {"id": "summary-d", "content": "Deleted source", "source_record_ids": ["record-d"]},
    ]
    records = [
        {"id": "record-r", "status": "retracted"},
        {"id": "record-d", "status": "deleted"},
    ]
    eligible, evidence = filter_stale_continuity_summaries(summaries, records)
    require(not eligible, "summary backed by retracted or deleted record remained eligible")
    require(evidence.retracted_conflicts == 1 and evidence.deleted_conflicts == 1, "source states were not separated")


def test_similar_wording_alone_does_not_establish_staleness() -> None:
    eligible, evidence = filter_stale_continuity_summaries(
        [{"id": "summary", "content": "The garden plan is active."}],
        [{"id": "memory", "content": "Our active plan concerns a garden."}],
    )
    require(len(eligible) == 1 and evidence.stale_count == 0, "ambiguous similarity inferred a correction")


def test_prompt_assembly_uses_fresh_summary_and_excludes_stale_one() -> None:
    old = "The Atlas office is in Dayton."
    packet = build_conversation_prompt(
        user_message="Where is the Atlas office and when does it open?",
        self_model={"name": "Eidolon"},
        desires={},
        memories=[
            {
                "id": "corrected-memory",
                "type": "fact",
                "content": "The Atlas office is in Columbus.",
                "importance": "high",
                "superseded_content_digests": [content_digest(old)],
            }
        ],
        continuity_summaries=[
            {"id": "old-summary", "content": old, "content_digest": content_digest(old), "importance": "high"},
            {"id": "fresh-summary", "content": "The Atlas office opens at nine.", "importance": "high"},
        ],
        project_context="",
        goal_context="",
        task_context="",
        conversation_history=[],
        context_size=8192,
        max_tokens=256,
    )
    require(old not in packet.prompt, "stale summary re-entered prompt context")
    require("The Atlas office opens at nine" in packet.prompt, "eligible fresh summary was not available")
    require(packet.metrics.context_stale_summaries_suppressed == 1, "stale-summary metric is wrong")


def test_evidence_is_content_free_provider_free_and_read_only() -> None:
    old = "Private obsolete summary"
    _eligible, evidence = filter_stale_continuity_summaries(
        [{"id": "summary", "content": old}],
        [{"superseded_content_digests": [content_digest(old)]}],
    )
    summary = evidence.public_summary()
    require(not stale_summary_evidence_contains_private_fields(summary), "stale-summary evidence leaked content")
    require(not evidence.provider_invoked and not evidence.writes_state, "detector invoked provider or wrote state")
    require(not evidence.rewrites_summary, "detector rewrote stored summary")


def test_suite_registration_is_exact() -> None:
    names = [suite.name for suite in verify.select_suites("core")]
    require(names.count("v1085.7-stale-summary-detection") == 1, "suite registration is not exact")


TESTS = [
    ("exact_corrected_digest_suppresses_stale_summary", test_exact_corrected_digest_suppresses_stale_summary),
    ("explicit_lineage_and_current_session_evidence_are_honored", test_explicit_lineage_and_current_session_evidence_are_honored),
    ("retracted_and_deleted_sources_invalidate_summaries", test_retracted_and_deleted_sources_invalidate_summaries),
    ("similar_wording_alone_does_not_establish_staleness", test_similar_wording_alone_does_not_establish_staleness),
    ("prompt_assembly_uses_fresh_summary_and_excludes_stale_one", test_prompt_assembly_uses_fresh_summary_and_excludes_stale_one),
    ("evidence_is_content_free_provider_free_and_read_only", test_evidence_is_content_free_provider_free_and_read_only),
    ("suite_registration_is_exact", test_suite_registration_is_exact),
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
    report = {
        "suite": "v1085.7-stale-summary-detection",
        "ok": passed == len(TESTS),
        "status": "pass" if passed == len(TESTS) else "fail",
        "passed": passed,
        "total": len(TESTS),
        "checks": checks,
    }
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
