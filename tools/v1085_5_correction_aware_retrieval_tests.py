from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
TOOLS = ROOT / "tools"
sys.path.insert(0, str(AGENT))
sys.path.insert(0, str(TOOLS))

import memory
import post_review_development_verify as isolated_verify
import release_metadata
from context_correction_aware_retrieval import (
    candidate_reintroduces_superseded_fact,
    correction_retrieval_contains_private_fields,
    content_digest,
    filter_correction_aware_records,
)
from conversation_context import _memory_candidates, build_conversation_prompt


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


def corrected_records() -> list[dict]:
    old = "Marcus lives in Toledo."
    return [
        {
            "id": "corrected", "type": "personal_fact", "content": "Marcus lives in Cleveland.", "status": "active",
            "fact_key": "home-city", "correction_lineage": [{"operator_explicit": True, "previous_content": old, "previous_content_digest": content_digest(old), "replacement_content_digest": content_digest("Marcus lives in Cleveland.")}],
            "superseded_content_digests": [content_digest(old)],
        },
        {"id": "exact-stale", "type": "personal_fact", "content": old, "status": "active"},
        {"id": "linked-stale", "type": "personal_fact", "content": "His home city is Toledo.", "status": "active", "fact_key": "home-city"},
        {"id": "similar-unlinked", "type": "personal_fact", "content": "Marcus visited Toledo last year.", "status": "active"},
    ]


def test_exact_superseded_digest_is_suppressed() -> None:
    eligible, evidence = filter_correction_aware_records(corrected_records())
    ids = {row["id"] for row in eligible}
    require("exact-stale" not in ids, "exact superseded content remained eligible")
    require(evidence.exact_digest_suppressed == 1, "exact suppression count wrong")


def test_differently_worded_stale_fact_requires_explicit_link() -> None:
    eligible, evidence = filter_correction_aware_records(corrected_records())
    ids = {row["id"] for row in eligible}
    require("linked-stale" not in ids, "explicitly linked stale wording remained eligible")
    require(evidence.explicit_link_suppressed == 1, "explicit-link suppression count wrong")


def test_lexically_similar_unlinked_record_is_not_inferred_as_correction() -> None:
    eligible, evidence = filter_correction_aware_records(corrected_records())
    ids = {row["id"] for row in eligible}
    require("similar-unlinked" in ids, "ordinary similar record was suppressed without explicit evidence")
    require(evidence.ambiguous_similarity_suppressed == 0 and not evidence.lexical_inference_used, "lexical correction inference was used")


def test_prompt_ranking_uses_corrected_record_and_blocks_stale_variants() -> None:
    candidates = _memory_candidates(corrected_records(), "Where does Marcus live?")
    ids = {row.get("id") for row, _important in candidates}
    require("corrected" in ids, "corrected fact absent from retrieval")
    require("exact-stale" not in ids and "linked-stale" not in ids, "stale facts entered ranked candidates")
    packet = build_conversation_prompt(
        user_message="Where does Marcus live?", self_model={"name": "Eidolon"}, desires={}, memories=corrected_records(),
        project_context="", goal_context="", task_context="", conversation_history=[], context_size=4096, max_tokens=256,
    )
    require("Marcus lives in Cleveland." in packet.prompt, "corrected content absent from prompt")
    require("His home city is Toledo." not in packet.prompt and "Marcus lives in Toledo." not in packet.prompt, "stale corrected content leaked into prompt")
    require(packet.metrics.context_correction_exact_suppressed == 1, "prompt exact suppression metric wrong")
    require(packet.metrics.context_correction_explicit_link_suppressed == 1, "prompt link suppression metric wrong")


def test_memory_search_suppresses_stale_correction_records_offline() -> None:
    with tempfile.TemporaryDirectory(prefix="eidolon-v1085-5-memory-") as raw:
        path = Path(raw) / "memories.json"
        path.write_text(json.dumps(corrected_records()), encoding="utf-8")
        original = memory.MEMORY_FILE
        memory.MEMORY_FILE = path
        try:
            stale = memory.search_memories("toledo", limit=10)
            corrected = memory.search_memories("cleveland", limit=10)
        finally:
            memory.MEMORY_FILE = original
    ids = {row.get("id") for row in stale}
    require("exact-stale" not in ids and "linked-stale" not in ids, "memory search reintroduced stale facts")
    require(any(row.get("id") == "corrected" for row in corrected), "corrected fact absent from memory search")


def test_future_candidate_eligibility_requires_explicit_evidence() -> None:
    rows = corrected_records()
    exact, exact_reason = candidate_reintroduces_superseded_fact({"id": "new-old", "type": "personal_fact", "content": "Marcus lives in Toledo."}, rows)
    ambiguous, ambiguous_reason = candidate_reintroduces_superseded_fact({"id": "new-visit", "type": "personal_fact", "content": "Marcus enjoyed Toledo museums."}, rows)
    require(exact and exact_reason == "exact_superseded_digest", "exact stale candidate was not rejected")
    require(not ambiguous and ambiguous_reason == "no_explicit_supersession_evidence", "ambiguous candidate was rejected without evidence")


def test_registration_metadata_javascript_layout_privacy_and_content_free_evidence() -> None:
    current = tuple(int(part) for part in release_metadata.RUNTIME_VERSION.split("."))
    require(current >= (1085, 5), "runtime regressed before v1085.5")
    history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
    require("v1085.5 Correction-Aware Retrieval" in history, "v1085.5 release evidence missing")
    next_token = release_metadata.NEXT_RECOMMENDED_ARC.split()[0].lstrip("v")
    require(tuple(int(part) for part in next_token.split(".")[:2]) >= (1085, 6), "next objective regressed before v1085.6")
    names = (
        "v1085.3-conversation-topic-segmentation",
        "v1085.4-context-budget-management",
        "v1085.5-correction-aware-retrieval",
    )
    core = [suite.name for suite in isolated_verify.select_suites("core")]
    full = [suite.name for suite in isolated_verify.select_suites("full")]
    for name in names:
        require(core.count(name) == 1 and full.count(name) == 1, f"registration wrong for {name}")
    release_source = (TOOLS / "release_verify.py").read_text(encoding="utf-8")
    for script in (
        "v1085_3_conversation_topic_segmentation_tests.py",
        "v1085_4_context_budget_management_tests.py",
        "v1085_5_correction_aware_retrieval_tests.py",
    ):
        require(release_source.count(script) == 1, f"release registration wrong for {script}")
    _, evidence = filter_correction_aware_records(corrected_records())
    summary = evidence.public_summary()
    require(not correction_retrieval_contains_private_fields(summary), "correction evidence contains private fields")
    require("toledo" not in json.dumps(summary).lower(), "correction evidence leaked content")
    require(not summary["provider_invoked"] and not summary["writes_state"], "correction retrieval contacts provider or writes state")
    responsive_source = (AGENT / "dashboard_first_use.py").read_text(encoding="utf-8").replace(" ", "")
    require(
        "@media(max-width:820px)" in responsive_source and "@media(max-width:560px)" in responsive_source,
        "active first-use narrow-layout contract missing",
    )
    import dashboard_chat_console
    html = dashboard_chat_console.render_realtime_chat_panel(None, compact=True)
    node = shutil.which("node")
    if node:
        with tempfile.TemporaryDirectory(prefix="eidolon-v1085-5-js-") as raw:
            cursor, index = 0, 0
            while True:
                start = html.find("<script>", cursor)
                if start < 0:
                    break
                end = html.find("</script>", start)
                require(end >= 0, "unclosed rendered script")
                path = Path(raw) / f"script-{index}.js"
                path.write_text(html[start + 8:end], encoding="utf-8")
                result = subprocess.run([node, "--check", str(path)], capture_output=True, text=True, timeout=30)
                require(result.returncode == 0, result.stderr or "rendered JavaScript failed syntax validation")
                cursor, index = end + 9, index + 1
    forbidden = ("data/projects.json", "data/tasks.json", "data/memories.json", "data/approvals/", "data/conversation_runtime/")
    files = [path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if path.is_file() and "__pycache__" not in path.parts]
    require(not [name for name in files if any(name == token or name.startswith(token) for token in forbidden)], "private runtime state present")


TESTS = [
    ("exact_superseded_digest_is_suppressed", test_exact_superseded_digest_is_suppressed),
    ("differently_worded_stale_fact_requires_explicit_link", test_differently_worded_stale_fact_requires_explicit_link),
    ("lexically_similar_unlinked_record_is_not_inferred_as_correction", test_lexically_similar_unlinked_record_is_not_inferred_as_correction),
    ("prompt_ranking_uses_corrected_record_and_blocks_stale_variants", test_prompt_ranking_uses_corrected_record_and_blocks_stale_variants),
    ("memory_search_suppresses_stale_correction_records_offline", test_memory_search_suppresses_stale_correction_records_offline),
    ("future_candidate_eligibility_requires_explicit_evidence", test_future_candidate_eligibility_requires_explicit_evidence),
    ("registration_metadata_javascript_layout_privacy_and_content_free_evidence", test_registration_metadata_javascript_layout_privacy_and_content_free_evidence),
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
    report = {"suite": "v1085.5-correction-aware-retrieval", "ok": passed == len(TESTS), "status": "pass" if passed == len(TESTS) else "fail", "passed": passed, "total": len(TESTS), "checks": checks}
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
