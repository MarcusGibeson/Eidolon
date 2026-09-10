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

import post_review_development_verify as isolated_verify
import release_metadata
from context_relevance_ranking import RankedContextCandidate
from context_salience_balance import balance_ranked_context
from conversation_context import build_conversation_prompt


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


def evidence(index: int, *, recent: int, lexical: int = 0, important: int = 0, curated: int = 0, relationship: bool = False, total: int = 10) -> RankedContextCandidate:
    return RankedContextCandidate(
        source_index=index, source_kind="curated_memory", evidence_digest=f"digest-{index}",
        lexical_score=lexical, recency_score=recent, relationship_score=2 if relationship else 0,
        status_score=2, operator_curation_score=curated, importance_score=important,
        total_score=total, reason_codes=(), relationship_relevant=relationship,
        operator_curated=curated > 0, salient=important >= 4 or curated >= 3,
    )


def test_relevant_older_salience_receives_bounded_reservation() -> None:
    rows = [
        ({"id": "r1"}, evidence(0, recent=4, total=20)),
        ({"id": "r2"}, evidence(1, recent=4, total=19)),
        ({"id": "r3"}, evidence(2, recent=3, total=18)),
        ({"id": "r4"}, evidence(3, recent=3, total=17)),
        ({"id": "older-curated"}, evidence(4, recent=0, lexical=1, important=4, curated=4, relationship=True, total=16)),
    ]
    balanced, proof = balance_ranked_context(rows)
    require(balanced[1][0]["id"] == "older-curated", "older salient context did not receive reserved position")
    require(proof.reservations_applied == 1, "salience reservation not recorded")
    require(proof.reservation_window == 3, "reservation window drifted")


def test_unrelated_older_salience_is_not_forced() -> None:
    rows = [
        ({"id": "recent"}, evidence(0, recent=4, lexical=1, total=20)),
        ({"id": "older-unrelated"}, evidence(1, recent=0, important=4, curated=4, relationship=False, total=10)),
    ]
    balanced, proof = balance_ranked_context(rows)
    require(balanced[0][0]["id"] == "recent", "unrelated older record displaced relevant recent context")
    require(proof.reservations_applied == 0, "unrelated salience was reserved")


def test_prompt_admits_older_curated_memory_before_recent_trivia() -> None:
    memories = [
        {"id": "curated", "type": "preference", "content": "Marcus values calm direct veterinary guidance.", "importance": "high", "state": "active", "operator_curated": True, "retention_confirmed": True},
        *[
            {"id": f"recent-{i}", "type": "fact", "content": f"Recent trivial receipt number {i}.", "importance": "low", "state": "active"}
            for i in range(6)
        ],
    ]
    packet = build_conversation_prompt(
        user_message="Help with calm veterinary guidance.", self_model={"name": "Eidolon"}, desires={},
        memories=memories, project_context="", goal_context="", task_context="", conversation_history=[],
        context_size=1800, max_tokens=256,
    )
    require("Marcus values calm direct veterinary guidance." in packet.prompt, "older curated memory was displaced")
    require(packet.metrics.important_memories_included >= 1, "salient inclusion not recorded")


def test_balancing_is_deterministic_and_non_mutating() -> None:
    original = [
        ({"id": "recent"}, evidence(0, recent=4, total=20)),
        ({"id": "older"}, evidence(1, recent=0, lexical=1, important=4, curated=4, relationship=True, total=10)),
    ]
    snapshot = json.dumps([row for row, _ in original], sort_keys=True)
    first, first_proof = balance_ranked_context(original)
    second, second_proof = balance_ranked_context(list(original))
    require([row[0]["id"] for row in first] == [row[0]["id"] for row in second], "balancing changed across reload-equivalent input")
    require(first_proof == second_proof, "balance evidence changed")
    require(json.dumps([row for row, _ in original], sort_keys=True) == snapshot, "balancer mutated source records")


def test_whole_memory_records_remain_untruncated() -> None:
    content = "A complete curated memory sentence that must remain whole under bounded context admission."
    packet = build_conversation_prompt(
        user_message="Use the complete curated memory sentence.", self_model={"name": "Eidolon"}, desires={},
        memories=[{"type": "preference", "content": content, "importance": "high", "operator_curated": True, "state": "active"}],
        project_context="", goal_context="", task_context="", conversation_history=[],
        context_size=1400, max_tokens=256,
    )
    require(content in packet.prompt, "curated memory was partially truncated")
    require(content[:-8] not in packet.prompt or content in packet.prompt, "partial memory record admitted")


def test_balance_metrics_are_content_free_and_provider_free() -> None:
    packet = build_conversation_prompt(
        user_message="Discuss private veterinary continuity.", self_model={"name": "Eidolon"}, desires={},
        memories=[{"type": "preference", "content": "Private veterinary continuity detail.", "importance": "high", "operator_curated": True, "state": "active"}],
        project_context="", goal_context="", task_context="", conversation_history=[],
        context_size=4096, max_tokens=256,
    )
    metrics = packet.metrics.to_dict()
    rendered = json.dumps(metrics).lower()
    require("private veterinary continuity detail" not in rendered, "salience metrics leaked content")
    require(metrics["context_salient_candidate_count"] >= 1, "salient candidate count missing")
    require(not metrics["context_ranking_provider_invoked"] and not metrics["context_assembly_writes_state"], "balance claimed provider/state mutation")


def test_registration_metadata_javascript_layout_and_source_privacy() -> None:
    current = tuple(int(part) for part in release_metadata.RUNTIME_VERSION.split(".")[:2])
    require(current >= (1085, 2), "runtime regressed before v1085.2")
    require(release_metadata.RUNTIME_MILESTONE.startswith(f"v{release_metadata.RUNTIME_VERSION}"), "current milestone/version mismatch")
    next_token = release_metadata.NEXT_RECOMMENDED_ARC.split()[0].lstrip("v")
    require(tuple(int(part) for part in next_token.split(".")[:2]) >= (1085, 3), "next objective regressed before v1085.3")
    names = (
        "v1085.0-context-assembly-architecture",
        "v1085.1-bounded-relevance-ranking",
        "v1085.2-recency-salience-balance",
    )
    core = [suite.name for suite in isolated_verify.select_suites("core")]
    full = [suite.name for suite in isolated_verify.select_suites("full")]
    for name in names:
        require(core.count(name) == 1 and full.count(name) == 1, f"registration wrong for {name}")
    release_source = (TOOLS / "release_verify.py").read_text(encoding="utf-8")
    for script in (
        "v1085_0_context_assembly_architecture_tests.py",
        "v1085_1_bounded_relevance_ranking_tests.py",
        "v1085_2_recency_salience_balance_tests.py",
    ):
        require(release_source.count(script) == 1, f"release registration wrong for {script}")
    responsive_source = (AGENT / "dashboard_first_use.py").read_text(encoding="utf-8").replace(" ", "")
    require(
        "@media(max-width:820px)" in responsive_source and "@media(max-width:560px)" in responsive_source,
        "active first-use narrow-layout contract missing",
    )
    import dashboard_chat_console
    html = dashboard_chat_console.render_realtime_chat_panel(None, compact=True)
    node = shutil.which("node")
    if node:
        with tempfile.TemporaryDirectory(prefix="eidolon-v1085-2-js-") as raw:
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
    ("relevant_older_salience_receives_bounded_reservation", test_relevant_older_salience_receives_bounded_reservation),
    ("unrelated_older_salience_is_not_forced", test_unrelated_older_salience_is_not_forced),
    ("prompt_admits_older_curated_memory_before_recent_trivia", test_prompt_admits_older_curated_memory_before_recent_trivia),
    ("balancing_is_deterministic_and_non_mutating", test_balancing_is_deterministic_and_non_mutating),
    ("whole_memory_records_remain_untruncated", test_whole_memory_records_remain_untruncated),
    ("balance_metrics_are_content_free_and_provider_free", test_balance_metrics_are_content_free_and_provider_free),
    ("registration_metadata_javascript_layout_and_source_privacy", test_registration_metadata_javascript_layout_and_source_privacy),
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
    report = {"suite": "v1085.2-recency-salience-balance", "ok": passed == len(TESTS), "status": "pass" if passed == len(TESTS) else "fail", "passed": passed, "total": len(TESTS), "checks": checks}
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
