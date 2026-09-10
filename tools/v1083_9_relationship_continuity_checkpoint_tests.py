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
import post_review_development_verify as isolated_verify
import relationship_continuity_checkpoint as checkpoint
import release_metadata


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


def fixture_memories() -> list[dict]:
    return [
        {
            "id": "preference-old",
            "type": "preference",
            "content": "Marcus likes black coffee",
            "status": "active",
            "relationship_eligible": True,
            "use_in_conversation": True,
            "created_at": "2026-07-01T00:00:00Z",
        },
        {
            "id": "preference-new",
            "type": "preference",
            "content": "Marcus likes black coffee",
            "status": "active",
            "relationship_eligible": True,
            "use_in_conversation": True,
            "created_at": "2026-07-02T00:00:00Z",
            "correction_lineage": [{
                "operator_explicit": True,
                "previous_content": "Marcus preferred tea",
                "previous_content_digest": "a" * 64,
                "replacement_content_digest": "b" * 64,
                "provider_invoked": False,
                "raw_transcript_rewritten": False,
            }],
            "superseded_content_digests": ["a" * 64],
        },
        {
            "id": "preference-contradiction",
            "type": "preference",
            "content": "Marcus does not like black coffee",
            "status": "active",
            "relationship_eligible": True,
            "use_in_conversation": True,
            "created_at": "2026-07-03T00:00:00Z",
        },
        {
            "id": "mood-current",
            "type": "user_mood",
            "content": "The user explicitly said they feel hopeful today",
            "status": "active",
            "relationship_eligible": True,
            "use_in_conversation": True,
            "temporal_state": "current",
        },
        {
            "id": "mood-cleared",
            "type": "user_mood",
            "content": "The user previously felt discouraged",
            "status": "active",
            "relationship_eligible": True,
            "use_in_conversation": True,
            "temporal_state": "cleared",
        },
        {
            "id": "moment-open",
            "type": "important_moment",
            "content": "A privately worded important moment",
            "status": "active",
            "relationship_eligible": True,
            "use_in_conversation": True,
            "temporal_state": "open",
            "operator_explicit": True,
            "retention_confirmed": True,
            "source": "operator_relationship_curation_dashboard",
        },
        {
            "id": "retracted",
            "type": "personal_fact",
            "content": "Retracted private fact",
            "status": "retracted",
            "relationship_eligible": False,
            "use_in_conversation": False,
        },
        {
            "id": "relationship_memory_deletion_deadbeef",
            "type": "relationship_memory_deletion_tombstone",
            "status": "deleted",
            "deleted_record_key_digest": "c" * 64,
            "content_removed": True,
            "vector_cleanup": {
                "cleanup_complete": True,
                "verified_absent": True,
                "content_free": True,
                "provider_invoked": False,
            },
        },
    ]


def fixture_history(count: int = 40) -> list[dict]:
    return [
        {
            "turn_id": f"turn-{index}",
            "user_message": f"private user line {index}",
            "assistant_response": f"Grounded assistant reply {index}",
            "continuity_lane": "ordinary" if index % 2 == 0 else "relational",
        }
        for index in range(count)
    ]


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
    return checkpoint.build_relationship_continuity_checkpoint(
        "session-private-id",
        memories=fixture_memories(),
        history=fixture_history(),
        provider_evidence=fixture_provider(),
        interaction_lane="relational",
    )


def area(report: dict, name: str) -> dict:
    return next(row for row in report["areas"] if row["name"] == name)


def test_release_metadata_closes_v1083_arc() -> None:
    parts = tuple(int(part) for part in release_metadata.RUNTIME_VERSION.split("."))
    require(parts >= (1083, 9), "runtime predates the v1083.9 checkpoint")
    require(release_metadata.RUNTIME_VERSION_TAG == f"v{release_metadata.RUNTIME_VERSION}", "runtime version tag is inconsistent")
    history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
    require("# v1083.9 Relationship Continuity Checkpoint" in history, "release history entry missing")
    require("404/404 across 32 suites" in history and "669/669 across 49 suites" in history, "v1083.9 verification evidence missing")


def test_long_session_is_bounded_and_restart_digest_is_idempotent() -> None:
    first = build()
    reloaded_memories = json.loads(json.dumps(fixture_memories()))
    reloaded_history = json.loads(json.dumps(fixture_history()))
    second = checkpoint.build_relationship_continuity_checkpoint(
        "session-private-id",
        memories=reloaded_memories,
        history=reloaded_history,
        provider_evidence=copy.deepcopy(fixture_provider()),
        interaction_lane="relational",
    )
    personality = area(first, "long_session_personality")
    require(personality["metrics"]["history_rows_considered"] == 12, "long history was not bounded")
    require(first["contract_digest"] == second["contract_digest"], "restart changed deterministic checkpoint digest")
    require(area(first, "restart_continuity")["metrics"]["writes_state"] is False, "restart evidence writes state")


def test_corrections_and_conflicts_remain_explicit() -> None:
    report = build()
    corrections = area(report, "correction_propagation")
    conflicts = area(report, "memory_conflicts")
    require(corrections["state"] == "ready", "correction lineage is not complete")
    require(corrections["metrics"]["corrected_records"] == 1, "corrected record count wrong")
    require(corrections["metrics"]["raw_transcripts_rewritten"] is False, "correction rewrote transcript")
    kinds = conflicts["metrics"]["kinds"]
    require(kinds.get("exact_duplicate", 0) >= 1, "exact duplicate not represented")
    require(kinds.get("contradiction", 0) >= 1, "contradiction not represented separately")
    require(conflicts["metrics"]["automatic_mutation"] is False, "conflict classification mutates automatically")


def test_retraction_and_deletion_integrity_is_content_free() -> None:
    report = build()
    deletion = area(report, "retraction_and_deletion")
    require(deletion["state"] == "ready", "deletion integrity is not ready")
    require(deletion["metrics"]["retracted_records"] == 1, "retracted count wrong")
    require(deletion["metrics"]["deletion_tombstones"] == 1, "tombstone count wrong")
    require(deletion["metrics"]["content_free_tombstones"], "tombstone is not content-free")


def test_mood_moments_and_affection_remain_bounded() -> None:
    report = build()
    mood = area(report, "mood_continuity")
    moments = area(report, "important_moments")
    affection = area(report, "affection_inflation")
    require(mood["metrics"]["current_mood_records"] == 1, "cleared mood accumulated")
    require(mood["metrics"]["old_moods_accumulate"] is False, "old mood accumulation enabled")
    require(moments["metrics"]["open_moment_count"] == 1, "open important moment count wrong")
    require(moments["metrics"]["provenance_states"].get("operator_reviewed_exact_content") == 1, "important-moment provenance missing")
    require(affection["metrics"]["user_led_warmth_allowed"], "user-led warmth unexpectedly blocked")
    require(not affection["metrics"]["affection_escalation_allowed"], "affection inflation enabled")
    require(not affection["metrics"]["relationship_progress_claim_allowed"], "invented relationship progress enabled")


def test_provider_outage_never_replays_or_switches() -> None:
    report = build()
    provider = area(report, "provider_outage")
    require(provider["state"] == "temporarily_unavailable", "provider outage state not preserved")
    require(not provider["metrics"]["generation_available"], "unavailable provider reported ready")
    require(not provider["metrics"]["automatic_generation_replay"], "provider request replay enabled")
    require(not provider["metrics"]["automatic_resend"], "automatic resend enabled")
    require(report["boundaries"]["provider_switching"] is False, "provider switching boundary weakened")
    require(report["boundaries"]["model_management"] is False, "model management boundary weakened")


def test_failed_and_cancelled_generation_cannot_commit_memory() -> None:
    report = build()
    turns = area(report, "failed_and_cancelled_generation")
    require(turns["metrics"]["cancelled_state"] == "accepted_cancelled", "cancelled turn state wrong")
    require(turns["metrics"]["failed_state"] == "accepted_failed", "failed turn state wrong")
    require(not turns["metrics"]["cancelled_memory_commit_allowed"], "cancelled response can commit memory")
    require(not turns["metrics"]["failed_memory_commit_allowed"], "failed response can commit memory")
    require(not turns["metrics"]["synthetic_assistant_output"], "synthetic output fabricated")


def test_checkpoint_is_read_only_content_free_and_private() -> None:
    report = build()
    serialized = json.dumps(report, sort_keys=True)
    for secret in (
        "Marcus likes black coffee", "private user line", "Grounded assistant reply",
        "privately worded important moment", "Retracted private fact",
    ):
        require(secret not in serialized, f"checkpoint leaked private text: {secret}")
    require(report["checkpoint_status"] == "relationship_continuity_contracts_ready", "checkpoint status wrong")
    require(report["release_certified"] is False and report["verification_required"] is True, "checkpoint claims release authority")
    require(report["read_only"] and report["redacted"] and report["content_free"], "read-only privacy flags missing")
    require(not checkpoint.relationship_continuity_checkpoint_contains_private_fields(report), "checkpoint contains forbidden private fields")
    require(all(value is False for value in report["boundaries"].values()), "checkpoint weakened a safety boundary")


def test_api_route_is_get_only_and_redacted() -> None:
    old_memories = checkpoint.load_memories
    old_history = checkpoint._history_for_session
    old_provider = checkpoint.provider_resume_cue
    checkpoint.load_memories = fixture_memories
    checkpoint._history_for_session = lambda _session_id: fixture_history()
    checkpoint.provider_resume_cue = lambda _evidence=None: fixture_provider()
    try:
        status, payload = api_server.handle_api_get(
            "/api/conversation/relationship-continuity-checkpoint",
            {"session_id": ["session-private-id"]},
        )
    finally:
        checkpoint.load_memories = old_memories
        checkpoint._history_for_session = old_history
        checkpoint.provider_resume_cue = old_provider
    data = payload.get("data") if isinstance(payload, dict) else None
    require(status == 200 and isinstance(data, dict), "checkpoint GET route failed")
    require(data["read_only"] and data["content_free"], "API checkpoint is not redacted")
    index = json.dumps(api_server._api_index())
    require("GET /api/conversation/relationship-continuity-checkpoint" in index, "GET route missing from API index")
    require("POST /api/conversation/relationship-continuity-checkpoint" not in index, "mutation route exposed")


def test_rendered_javascript_and_narrow_layout_remain_valid() -> None:
    source = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
    require("@media(max-width:620px)" in source.replace(" ", ""), "narrow layout media query missing")
    for token in ("chat-load-earlier", "chat-jump-latest", "chat-offline-session-durability"):
        require(token in source, f"narrow layout continuity control missing: {token}")
    import dashboard_chat_console
    html = dashboard_chat_console.render_realtime_chat_panel(None, compact=True)
    node = shutil.which("node")
    if not node:
        return
    with tempfile.TemporaryDirectory(prefix="eidolon-v1083-9-js-") as raw:
        cursor = 0
        index = 0
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
            cursor = end + 9
            index += 1


def test_registration_and_release_verification_are_exactly_once() -> None:
    core = [suite.name for suite in isolated_verify.select_suites("core")]
    full = [suite.name for suite in isolated_verify.select_suites("full")]
    require(core.count("v1083.9-relationship-continuity-checkpoint") == 1, "core registration wrong")
    require(full.count("v1083.9-relationship-continuity-checkpoint") == 1, "full registration wrong")
    release_source = (TOOLS / "release_verify.py").read_text(encoding="utf-8")
    require(release_source.count("v1083_9_relationship_continuity_checkpoint_tests.py") == 1, "release registration wrong")


def test_source_only_privacy_and_live_state_absence() -> None:
    forbidden = (
        "data/projects.json", "data/tasks.json", "data/memories.json", "data/provider_recovery/",
        "data/conversation_runtime/", "data/conversation_sessions/", "data/dashboard_chat/",
        "data/chat_actions/", "data/actions/", "data/approvals/", "data/notifications/",
    )
    files = [path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if path.is_file() and "__pycache__" not in path.parts]
    require(not [name for name in files if any(name == item or name.startswith(item) for item in forbidden)], "private runtime data present")
    require(not any(name.endswith(".zip") for name in files), "nested release archive present")


TESTS = [
    ("release_metadata_closes_v1083_arc", test_release_metadata_closes_v1083_arc),
    ("long_session_is_bounded_and_restart_digest_is_idempotent", test_long_session_is_bounded_and_restart_digest_is_idempotent),
    ("corrections_and_conflicts_remain_explicit", test_corrections_and_conflicts_remain_explicit),
    ("retraction_and_deletion_integrity_is_content_free", test_retraction_and_deletion_integrity_is_content_free),
    ("mood_moments_and_affection_remain_bounded", test_mood_moments_and_affection_remain_bounded),
    ("provider_outage_never_replays_or_switches", test_provider_outage_never_replays_or_switches),
    ("failed_and_cancelled_generation_cannot_commit_memory", test_failed_and_cancelled_generation_cannot_commit_memory),
    ("checkpoint_is_read_only_content_free_and_private", test_checkpoint_is_read_only_content_free_and_private),
    ("api_route_is_get_only_and_redacted", test_api_route_is_get_only_and_redacted),
    ("rendered_javascript_and_narrow_layout_remain_valid", test_rendered_javascript_and_narrow_layout_remain_valid),
    ("registration_and_release_verification_are_exactly_once", test_registration_and_release_verification_are_exactly_once),
    ("source_only_privacy_and_live_state_absence", test_source_only_privacy_and_live_state_absence),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.parse_args()
    checks = []
    passed = 0
    for name, function in TESTS:
        try:
            function()
        except Exception as error:
            checks.append({"name": name, "status": "fail", "message": f"{type(error).__name__}: {error}"})
        else:
            passed += 1
            checks.append({"name": name, "status": "pass", "message": ""})
    report = {
        "suite": "v1083.9-relationship-continuity-checkpoint",
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
