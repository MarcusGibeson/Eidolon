from __future__ import annotations

import argparse
import copy
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

import api_server
import conversation_quality_checkpoint as checkpoint
import post_review_development_verify as isolated_verify
import release_metadata


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


def fixture_history(count: int = 60) -> list[dict]:
    rows = []
    for index in range(count):
        rows.append({
            "turn_id": f"turn-{index}",
            "user_message": f"private user thread {index}",
            "assistant_response": (
                "I will help with the deployment blocker next. Which certificate is failing?"
                if index == count - 1 else f"private assistant reply {index}"
            ),
            "continuity_lane": "ordinary" if index % 3 else "operator",
        })
    return rows


def fixture_provider() -> dict:
    return {
        "type": "provider_recovery_evidence",
        "schema_version": "1",
        "checked_at": "2026-07-20T20:00:00Z",
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


def build() -> dict:
    return checkpoint.build_conversation_quality_checkpoint(
        "private-session-id",
        history=fixture_history(),
        provider_evidence=fixture_provider(),
    )


def area(report: dict, name: str) -> dict:
    return next(row for row in report["areas"] if row["name"] == name)


def test_release_metadata_closes_v1084_arc() -> None:
    current = tuple(map(int, release_metadata.RUNTIME_VERSION.split(".")))
    require(current >= (1084, 9), "runtime regressed before v1084.9")
    require(release_metadata.RUNTIME_VERSION_TAG == f"v{release_metadata.RUNTIME_VERSION}", "runtime version tag inconsistent")
    require(release_metadata.PREVIOUS_RUNTIME_VERSION != release_metadata.RUNTIME_VERSION, "previous runtime version cannot equal current")
    next_token = release_metadata.NEXT_RECOMMENDED_ARC.split()[0].lstrip("v")
    require(tuple(map(int, next_token.split(".")[:2])) >= (1085, 0), "next arc regressed before v1085.0")
    history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
    require("# v1084.9 Conversation Quality Checkpoint" in history, "release history entry missing")


def test_long_session_relevance_is_bounded_and_restart_stable() -> None:
    first = build()
    second = checkpoint.build_conversation_quality_checkpoint(
        "private-session-id",
        history=json.loads(json.dumps(fixture_history())),
        provider_evidence=copy.deepcopy(fixture_provider()),
    )
    relevance = area(first, "long_session_relevance")
    require(relevance["metrics"]["history_rows_available"] == 48, "checkpoint history window is not bounded")
    require(relevance["metrics"]["history_rows_considered"] <= 8, "quality signal history window exceeded")
    require(first["contract_digest"] == second["contract_digest"], "restart changed checkpoint digest")
    require(area(first, "restart_continuity")["metrics"]["writes_state"] is False, "restart evidence writes state")


def test_intent_response_shape_and_relevance_contracts() -> None:
    report = build()
    shape = area(report, "intent_and_response_shape")
    relevance = area(report, "long_session_relevance")
    require(shape["state"] == "ready", "intent/response shape checkpoint not ready")
    require(shape["metrics"]["brief_probe"] == "brief", "brief response probe failed")
    require(shape["metrics"]["deep_probe"] == "deep", "deep response probe failed")
    require(shape["metrics"]["mutates_personality"] is False, "response shape mutates personality")
    require(relevance["metrics"]["raw_history_returned"] is False, "relevance evidence returns raw history")


def test_unresolved_threads_and_callbacks_remain_bounded() -> None:
    evidence = area(build(), "unresolved_threads_and_callbacks")
    require(evidence["metrics"]["probe_unresolved_items"] >= 1, "unresolved-thread probe found no evidence")
    require(evidence["metrics"]["probe_matching_items"] >= 1, "unresolved thread was not matched")
    require(evidence["metrics"]["probe_callbacks_selected"] <= 2, "callback selection exceeded bound")
    require(evidence["metrics"]["automatic_obligation_creation"] is False, "unresolved signal became obligation")


def test_topic_changes_resumptions_and_interruptions_are_distinct() -> None:
    transitions = area(build(), "topic_transitions")["metrics"]["probe_transitions"]
    require(transitions["topic_shift"] == "topic_shift", "topic shift was not separated")
    require(transitions["resumption"] in {"resumption", "return"}, "resumption was not recognized")
    require(transitions["interruption"] == "interruption", "interruption was not recognized")
    evidence = area(build(), "topic_transitions")
    require(not evidence["metrics"]["unrelated_sessions_merged"], "unrelated sessions were merged")
    require(not evidence["metrics"]["interrupted_thread_forced"], "interrupted thread was forced")


def test_correction_handling_is_explicit_once_and_non_rewriting() -> None:
    correction = area(build(), "correction_handling")
    require(correction["metrics"]["explicit_probe"], "explicit correction was not recognized")
    require(correction["metrics"]["acknowledge_once"], "correction is not acknowledged once")
    require(correction["metrics"]["stale_claim_suppression"], "stale claim suppression missing")
    require(not correction["metrics"]["ambiguous_ordinary_inferred"], "ordinary ambiguity inferred as correction")
    require(not correction["metrics"]["raw_transcript_rewritten"], "correction rewrote transcript")


def test_personality_expression_and_affection_boundaries_hold() -> None:
    expression = area(build(), "personality_expression")
    require(expression["state"] == "stable", "personality expression is not stable")
    require(expression["metrics"]["emotional_mode"] == "warm_grounded", "emotional expression mode wrong")
    require(expression["metrics"]["operator_mode"] == "supervised_direct", "operator expression mode wrong")
    require(expression["metrics"]["affection_inflation_signals"] >= 1, "affection inflation probe missed")
    for key in ("affection_escalation_allowed", "exclusivity_allowed", "dependence_encouragement_allowed", "identity_mutation", "hidden_trait_inference"):
        require(expression["metrics"][key] is False, f"boundary weakened: {key}")


def test_diagnostics_are_bounded_content_free_and_json_safe() -> None:
    report = build()
    diagnostics = area(report, "quality_diagnostics")
    require(diagnostics["state"] == "content_free", "diagnostics are not content-free")
    require(diagnostics["metrics"]["decision_code_count"] <= 24, "diagnostic codes exceed bound")
    require(diagnostics["metrics"]["forbidden_private_fields"] is False, "diagnostics contain forbidden fields")
    require(diagnostics["metrics"]["hidden_reasoning_exposed"] is False, "hidden reasoning exposed")
    json.dumps(report, sort_keys=True)


def test_provider_outage_never_replays_resends_or_switches() -> None:
    provider = area(build(), "provider_outage")
    require(provider["state"] == "temporarily_unavailable", "provider outage state wrong")
    require(not provider["metrics"]["generation_available"], "unavailable generation reported ready")
    require(not provider["metrics"]["automatic_generation_replay"], "automatic generation replay enabled")
    require(not provider["metrics"]["automatic_resend"], "automatic resend enabled")
    require(not provider["metrics"]["provider_switching"], "provider switching enabled")


def test_failed_and_cancelled_generation_cannot_commit_memory() -> None:
    turns = area(build(), "failed_and_cancelled_generation")
    require(turns["metrics"]["cancelled_state"] == "accepted_cancelled", "cancelled state wrong")
    require(turns["metrics"]["failed_state"] == "accepted_failed", "failed state wrong")
    require(not turns["metrics"]["cancelled_memory_commit_allowed"], "cancelled turn can commit memory")
    require(not turns["metrics"]["failed_memory_commit_allowed"], "failed turn can commit memory")
    require(not turns["metrics"]["synthetic_assistant_output"], "synthetic output fabricated")


def test_checkpoint_is_read_only_content_free_and_private() -> None:
    report = build()
    rendered = json.dumps(report, sort_keys=True)
    for secret in ("private user thread", "private assistant reply", "certificate is failing"):
        require(secret not in rendered, f"checkpoint leaked private text: {secret}")
    require(report["checkpoint_status"] == "conversation_quality_contracts_ready", "checkpoint status wrong")
    require(report["release_certified"] is False and report["verification_required"] is True, "checkpoint claims release authority")
    require(report["read_only"] and report["redacted"] and report["content_free"], "privacy flags missing")
    require(not checkpoint.conversation_quality_checkpoint_contains_private_fields(report), "checkpoint has forbidden private fields")
    require(all(value is False for value in report["boundaries"].values()), "checkpoint weakened a safety boundary")


def test_get_only_route_registration_javascript_layout_and_source_privacy() -> None:
    old_history = checkpoint._history_for_session
    old_provider = checkpoint.provider_resume_cue
    checkpoint._history_for_session = lambda _session_id: fixture_history()
    checkpoint.provider_resume_cue = lambda _evidence=None: fixture_provider()
    try:
        status, payload = api_server.handle_api_get(
            "/api/conversation/conversation-quality-checkpoint",
            {"session_id": ["private-session-id"]},
        )
    finally:
        checkpoint._history_for_session = old_history
        checkpoint.provider_resume_cue = old_provider
    data = payload.get("data") if isinstance(payload, dict) else None
    require(status == 200 and isinstance(data, dict), "checkpoint GET route failed")
    require(data["read_only"] and data["content_free"], "GET output is not content-free")
    index = json.dumps(api_server._api_index())
    require("GET /api/conversation/conversation-quality-checkpoint" in index, "GET route missing")
    require("POST /api/conversation/conversation-quality-checkpoint" not in index, "POST route exposed")

    core = [suite.name for suite in isolated_verify.select_suites("core")]
    full = [suite.name for suite in isolated_verify.select_suites("full")]
    require(core.count("v1084.9-conversation-quality-checkpoint") == 1, "core registration wrong")
    require(full.count("v1084.9-conversation-quality-checkpoint") == 1, "full registration wrong")
    release_source = (TOOLS / "release_verify.py").read_text(encoding="utf-8")
    require(release_source.count("v1084_9_conversation_quality_checkpoint_tests.py") == 1, "release registration wrong")

    responsive_source = (AGENT / "dashboard_first_use.py").read_text(encoding="utf-8").replace(" ", "")
    require(
        "@media(max-width:820px)" in responsive_source and "@media(max-width:560px)" in responsive_source,
        "active first-use narrow-layout contract missing",
    )
    import dashboard_chat_console
    html = dashboard_chat_console.render_realtime_chat_panel(None, compact=True)
    node = shutil.which("node")
    if node:
        with tempfile.TemporaryDirectory(prefix="eidolon-v1084-9-js-") as raw:
            cursor, index_value = 0, 0
            while True:
                start = html.find("<script>", cursor)
                if start < 0:
                    break
                end = html.find("</script>", start)
                require(end >= 0, "unclosed rendered script")
                path = Path(raw) / f"script-{index_value}.js"
                path.write_text(html[start + 8:end], encoding="utf-8")
                result = subprocess.run([node, "--check", str(path)], capture_output=True, text=True, timeout=30)
                require(result.returncode == 0, result.stderr or "rendered JavaScript failed syntax validation")
                cursor, index_value = end + 9, index_value + 1

    forbidden = (
        "data/projects.json", "data/tasks.json", "data/memories.json", "data/approvals/",
        "data/conversation_runtime/", "data/conversation_sessions/", "data/provider_recovery/",
    )
    files = [path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if path.is_file() and "__pycache__" not in path.parts]
    require(not [name for name in files if any(name == item or name.startswith(item) for item in forbidden)], "private runtime state present")
    require(not any(name.endswith(".zip") for name in files), "nested source ZIP present")


TESTS = [
    ("release_metadata_closes_v1084_arc", test_release_metadata_closes_v1084_arc),
    ("long_session_relevance_is_bounded_and_restart_stable", test_long_session_relevance_is_bounded_and_restart_stable),
    ("intent_response_shape_and_relevance_contracts", test_intent_response_shape_and_relevance_contracts),
    ("unresolved_threads_and_callbacks_remain_bounded", test_unresolved_threads_and_callbacks_remain_bounded),
    ("topic_changes_resumptions_and_interruptions_are_distinct", test_topic_changes_resumptions_and_interruptions_are_distinct),
    ("correction_handling_is_explicit_once_and_non_rewriting", test_correction_handling_is_explicit_once_and_non_rewriting),
    ("personality_expression_and_affection_boundaries_hold", test_personality_expression_and_affection_boundaries_hold),
    ("diagnostics_are_bounded_content_free_and_json_safe", test_diagnostics_are_bounded_content_free_and_json_safe),
    ("provider_outage_never_replays_resends_or_switches", test_provider_outage_never_replays_resends_or_switches),
    ("failed_and_cancelled_generation_cannot_commit_memory", test_failed_and_cancelled_generation_cannot_commit_memory),
    ("checkpoint_is_read_only_content_free_and_private", test_checkpoint_is_read_only_content_free_and_private),
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
        "suite": "v1084.9-conversation-quality-checkpoint",
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
