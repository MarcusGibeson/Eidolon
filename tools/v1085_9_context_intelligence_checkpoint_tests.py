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
sys.path[:0] = [str(AGENT), str(TOOLS)]

import api_server
import context_intelligence_checkpoint as checkpoint
import dashboard_chat_console
import post_review_development_verify as isolated_verify
import release_metadata


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


def fixture_provider() -> dict:
    return {
        "type": "provider_recovery_evidence",
        "schema_version": "1",
        "checked_at": "2026-07-21T00:00:00Z",
        "state": "temporarily_unavailable",
        "observed_state": "temporarily_unavailable",
        "generation_available": False,
        "embedding_available": False,
        "configured_values_match": True,
        "settings_scope": "configured",
        "configuration_digest": "d" * 64,
        "trigger": "explicit_operator",
        "recovery_proven": False,
        "automatic_generation_replay": False,
        "automatic_resend": False,
        "redacted": True,
    }


def private_history() -> list[dict]:
    return [
        {
            "user_message": f"private user context {index}",
            "assistant_response": f"private assistant context {index}",
            "completion_state": "completed",
            "success": True,
        }
        for index in range(30)
    ]


def build() -> dict:
    return checkpoint.build_context_intelligence_checkpoint(
        "private-session-id",
        history=private_history(),
        memories=[
            {
                "id": "private-memory-id",
                "type": "fact",
                "content": "private memory content must never appear",
                "importance": "high",
            }
        ],
        continuity_rows=[
            {
                "id": "private-continuity-id",
                "content": "private continuity text must never appear",
            }
        ],
        cross_session_sessions=[
            {
                "id": "private-other-session",
                "title": "private other session title",
                "status": "active",
                "turns": [
                    {
                        "user_message": "private linked user text",
                        "assistant_response": "private linked assistant text",
                        "completion_state": "completed",
                        "success": True,
                    }
                ],
            }
        ],
        provider_evidence=fixture_provider(),
    )


def area(report: dict, name: str) -> dict:
    return next(row for row in report["areas"] if row["name"] == name)


def test_release_metadata_closes_v1085_arc() -> None:
    current = tuple(int(part) for part in release_metadata.RUNTIME_VERSION.split("."))
    require(current >= (1085, 9), "runtime regressed before v1085.9")
    require(release_metadata.RUNTIME_VERSION_TAG == f"v{release_metadata.RUNTIME_VERSION}", "runtime tag is inconsistent")
    require(release_metadata.RUNTIME_MILESTONE.startswith(release_metadata.RUNTIME_VERSION_TAG), "current milestone is inconsistent")
    history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
    require("# v1085.9 Context Intelligence Checkpoint" in history, "release history entry missing")


def test_lane_architecture_ranking_and_salience_remain_bounded() -> None:
    report = build()
    lanes = area(report, "context_lanes")
    ranking = area(report, "ranking_and_salience")
    require(lanes["state"] == "ready", "context lanes are not ready")
    require(lanes["metrics"]["lane_order"] == [
        "current_turn", "correction_evidence", "active_thread", "recent_conversation",
        "mood", "important_moments", "curated_memory",
    ], "lane order changed")
    require(lanes["metrics"]["current_turn_protected"], "current turn is not protected")
    require(lanes["metrics"]["correction_evidence_precedes_ranked_context"], "correction evidence does not precede ranking")
    require(ranking["metrics"]["candidate_count"] <= 64, "ranking candidate bound exceeded")
    require(not ranking["metrics"]["provider_invoked"], "ranking invoked a provider")


def test_large_history_topic_segmentation_is_bounded() -> None:
    evidence = area(build(), "large_history_and_topics")
    metrics = evidence["metrics"]
    require(metrics["supplied_history_rows"] > 12, "large-history probe is not large")
    require(metrics["maximum_topic_history_rows"] == 32, "topic-history bound changed")
    require(metrics["segment_count"] >= 2, "multiple topics were not separated")
    require(metrics["unrelated_turns_excluded"] >= 1, "unrelated turns were not excluded")
    require(not metrics["partial_turn_admission_allowed"], "partial turn admission was enabled")


def test_cross_session_linking_is_explicit_bounded_and_non_merging() -> None:
    evidence = area(build(), "cross_session_threads")
    metrics = evidence["metrics"]
    require(evidence["state"] == "ready", "related session was not linked")
    require(metrics["candidate_sessions"] == 2, "candidate-session count is wrong")
    require(metrics["linked_sessions"] == 1 and metrics["linked_turns"] == 1, "bounded related-session link is wrong")
    require(metrics["turns_included"] == 1, "linked turn was not admitted")
    require(not metrics["merges_sessions"] and not metrics["rewrites_history"], "session authority was weakened")
    require(not metrics["failed_or_partial_turns_eligible"], "failed or partial linked turns became eligible")


def test_corrections_suppress_stale_exact_content_not_ambiguous_similarity() -> None:
    evidence = area(build(), "correction_aware_retrieval")
    metrics = evidence["metrics"]
    require(metrics["correction_records"] >= 1, "explicit correction evidence missing")
    require(metrics["exact_suppressed"] >= 1, "stale exact record was not suppressed")
    require(metrics["ambiguous_similarity_suppressed"] == 0, "similar wording was treated as correction evidence")
    require(metrics["current_record_eligible"], "corrected current record was removed")
    require(not metrics["stale_record_eligible"], "stale corrected record remained eligible")
    require(metrics["similar_unlinked_record_eligible"], "unlinked similar record was incorrectly suppressed")
    require(not metrics["rewrites_transcript"], "correction retrieval rewrote transcript")


def test_retracted_deleted_and_stale_continuity_records_remain_excluded() -> None:
    correction = area(build(), "correction_aware_retrieval")["metrics"]
    continuity = area(build(), "continuity_record_staleness")["metrics"]
    require(not correction["retracted_record_eligible"], "retracted record remained eligible")
    require(not correction["deleted_record_eligible"], "deleted record remained eligible")
    require(continuity["detected"] >= 3, "stale continuity records were not detected")
    require(continuity["retracted_conflicts"] >= 1, "retracted continuity source was not detected")
    require(continuity["deleted_conflicts"] >= 1, "deleted continuity source was not detected")
    require(not continuity["old_location_eligible"], "corrected continuity record remained eligible")
    require(continuity["fresh_hours_eligible"], "fresh continuity record was removed")
    require(not continuity["rewrites_stored_record"], "continuity detector rewrote stored data")


def test_context_budget_has_explicit_omission_evidence_and_whole_records() -> None:
    evidence = area(build(), "budget_management")
    metrics = evidence["metrics"]
    require(evidence["state"] == "ready", "budget management is not ready")
    require(metrics["allocated_tokens"] and metrics["used_tokens"], "lane budget evidence missing")
    require(sum(metrics["omissions_by_lane"].values()) >= 1, "budget probe produced no bounded omissions")
    require(metrics["omission_reasons"].get("lane_budget_exhausted", 0) >= 1, "lane exhaustion reason missing")
    require(not metrics["silent_truncation_allowed"], "silent truncation was enabled")
    require(not metrics["partial_record_admission_allowed"], "partial record admission was enabled")


def test_inspection_console_is_read_only_offline_and_content_free() -> None:
    evidence = area(build(), "inspection_console")
    metrics = evidence["metrics"]
    require(evidence["state"] == "content_free", "inspection console is not content-free")
    require(metrics["offline_available"] and metrics["read_only"], "inspection console is not offline/read-only")
    require(not metrics["provider_invoked"] and not metrics["writes_state"], "inspection console invoked provider or wrote state")
    require(not metrics["contains_context_content"], "inspection console exposes context content")
    require(not metrics["contains_hidden_reasoning"], "inspection console exposes hidden reasoning")
    require(not metrics["private_fields_detected"], "inspection console contains forbidden private fields")


def test_provider_outage_preserves_offline_context_without_replay() -> None:
    evidence = area(build(), "offline_and_provider_outage")
    metrics = evidence["metrics"]
    require(evidence["state"] == "temporarily_unavailable", "provider outage state is wrong")
    require(metrics["offline_context_available"], "offline context became unavailable")
    require(not metrics["generation_available"] and not metrics["embedding_available"], "unavailable provider was reported ready")
    require(not metrics["automatic_generation_replay"], "automatic generation replay was enabled")
    require(not metrics["automatic_resend"], "automatic resend was enabled")
    require(not metrics["provider_switching"] and not metrics["model_management"], "provider or model control boundary weakened")


def test_deterministic_assembly_and_restart_contract_are_stable() -> None:
    first = build()
    second = build()
    evidence = area(first, "deterministic_assembly")
    require(evidence["state"] == "stable", "assembly is not deterministic")
    require(evidence["metrics"]["deterministic"] and evidence["metrics"]["restart_stable"], "restart contract is unstable")
    require(first["contract_digest"] == second["contract_digest"], "contract digest changed for equivalent inputs")
    require(evidence["metrics"]["assembly_digest"] == area(second, "deterministic_assembly")["metrics"]["assembly_digest"], "assembly digest changed")
    require(not evidence["metrics"]["provider_invoked"] and not evidence["metrics"]["writes_state"], "deterministic probe invoked provider or wrote state")


def test_checkpoint_is_private_read_only_and_has_no_release_authority() -> None:
    report = build()
    rendered = json.dumps(report, sort_keys=True)
    for secret in (
        "private user context", "private assistant context", "private memory content",
        "private continuity text", "private linked user text", "private-session-id",
    ):
        require(secret not in rendered, f"checkpoint leaked private value: {secret}")
    require(report["checkpoint_status"] == "context_intelligence_contracts_ready", "checkpoint status is wrong")
    require(report["read_only"] and report["content_free"] and report["offline_available"], "checkpoint boundary flags missing")
    require(not report["provider_invoked"] and not report["writes_state"], "checkpoint invoked provider or wrote state")
    require(not report["release_certified"] and report["verification_required"], "checkpoint claimed release authority")
    require(not checkpoint.context_intelligence_checkpoint_contains_private_fields(report), "checkpoint contains forbidden private fields")
    require(all(value is False for value in report["boundaries"].values()), "checkpoint weakened a safety boundary")


def test_get_only_route_registration_javascript_layout_and_source_privacy() -> None:
    old = api_server.build_context_intelligence_checkpoint
    api_server.build_context_intelligence_checkpoint = lambda session_id="": build()
    try:
        status, payload = api_server.handle_api_get(
            "/api/conversation/context-intelligence-checkpoint",
            {"session_id": ["private-session-id"]},
        )
    finally:
        api_server.build_context_intelligence_checkpoint = old
    data = payload.get("data") if isinstance(payload, dict) else None
    require(status == 200 and isinstance(data, dict), "checkpoint GET route failed")
    require(data["read_only"] and data["content_free"], "GET output is not content-free")
    index = json.dumps(api_server._api_index())
    require("GET /api/conversation/context-intelligence-checkpoint" in index, "GET route missing")
    require("POST /api/conversation/context-intelligence-checkpoint" not in index, "POST route exposed")

    names = [suite.name for suite in isolated_verify.SUITES]
    anchor = names.index("v1085.9-context-intelligence-checkpoint")
    historical = isolated_verify.SUITES[anchor:]
    core = [suite.name for suite in historical if "core" in suite.profiles]
    full = [suite.name for suite in historical if "full" in suite.profiles]
    require(core.count("v1085.9-context-intelligence-checkpoint") == 1, "core registration wrong")
    require(full.count("v1085.9-context-intelligence-checkpoint") == 1, "full registration wrong")
    require(len(core) <= 102, "historical core profile exceeded its bounded ceiling")
    release_source = (TOOLS / "release_verify.py").read_text(encoding="utf-8")
    require(release_source.count("v1085_9_context_intelligence_checkpoint_tests.py") == 1, "release registration wrong")

    responsive_source = (AGENT / "dashboard_first_use.py").read_text(encoding="utf-8").replace(" ", "")
    require(
        "@media(max-width:820px)" in responsive_source and "@media(max-width:560px)" in responsive_source,
        "active first-use narrow-layout contract missing",
    )
    html = dashboard_chat_console.render_realtime_chat_panel(None, compact=True)
    node = shutil.which("node")
    if node:
        with tempfile.TemporaryDirectory(prefix="eidolon-v1085-9-js-") as raw:
            cursor, script_index = 0, 0
            while True:
                start = html.find("<script>", cursor)
                if start < 0:
                    break
                end = html.find("</script>", start)
                require(end >= 0, "unclosed rendered script")
                script = Path(raw) / f"script-{script_index}.js"
                script.write_text(html[start + 8:end], encoding="utf-8")
                result = subprocess.run([node, "--check", str(script)], capture_output=True, text=True, timeout=30)
                require(result.returncode == 0, result.stderr or "rendered JavaScript syntax failed")
                cursor, script_index = end + 9, script_index + 1

    forbidden = (
        "data/projects.json", "data/tasks.json", "data/memories.json", "data/approvals/",
        "data/conversation_runtime/", "data/conversation_sessions/", "data/provider_recovery/",
        "data/dashboard_chat/", "data/chat_actions/",
    )
    files = [
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix.lower() not in {".pyc", ".pyo"}
    ]
    require(not [name for name in files if any(name == item or name.startswith(item) for item in forbidden)], "private runtime state present")
    require(not any(name.endswith(".zip") for name in files), "nested source ZIP present")


TESTS = [
    ("release_metadata_closes_v1085_arc", test_release_metadata_closes_v1085_arc),
    ("lane_architecture_ranking_and_salience_remain_bounded", test_lane_architecture_ranking_and_salience_remain_bounded),
    ("large_history_topic_segmentation_is_bounded", test_large_history_topic_segmentation_is_bounded),
    ("cross_session_linking_is_explicit_bounded_and_non_merging", test_cross_session_linking_is_explicit_bounded_and_non_merging),
    ("corrections_suppress_stale_exact_content_not_ambiguous_similarity", test_corrections_suppress_stale_exact_content_not_ambiguous_similarity),
    ("retracted_deleted_and_stale_continuity_records_remain_excluded", test_retracted_deleted_and_stale_continuity_records_remain_excluded),
    ("context_budget_has_explicit_omission_evidence_and_whole_records", test_context_budget_has_explicit_omission_evidence_and_whole_records),
    ("inspection_console_is_read_only_offline_and_content_free", test_inspection_console_is_read_only_offline_and_content_free),
    ("provider_outage_preserves_offline_context_without_replay", test_provider_outage_preserves_offline_context_without_replay),
    ("deterministic_assembly_and_restart_contract_are_stable", test_deterministic_assembly_and_restart_contract_are_stable),
    ("checkpoint_is_private_read_only_and_has_no_release_authority", test_checkpoint_is_private_read_only_and_has_no_release_authority),
    ("get_only_route_registration_javascript_layout_and_source_privacy", test_get_only_route_registration_javascript_layout_and_source_privacy),
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
        "suite": "v1085.9-context-intelligence-checkpoint",
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
