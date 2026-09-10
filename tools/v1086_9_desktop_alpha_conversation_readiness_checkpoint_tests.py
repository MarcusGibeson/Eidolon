from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
TOOLS = ROOT / "tools"
sys.path[:0] = [str(AGENT), str(TOOLS)]

import api_server
import dashboard_chat_console
import conversation_readiness_checkpoint as checkpoint
import post_review_development_verify as isolated_verify
import release_metadata


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


def build() -> dict:
    return checkpoint.build_conversation_readiness_checkpoint()


def area(report: dict, name: str) -> dict:
    return next(row for row in report["areas"] if row["name"] == name)


def source_snapshot() -> dict[str, str]:
    return {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in ROOT.rglob("*")
        if path.is_file() and not any(part in {"__pycache__", ".git", ".venv", "venv"} for part in path.parts)
    }


def test_release_metadata_and_docs_close_v1086_arc() -> None:
    version = tuple(int(part) for part in release_metadata.RUNTIME_VERSION.split("."))
    require(version >= (1086, 9), "runtime predates v1086.9")
    require(release_metadata.RUNTIME_VERSION_TAG == f"v{release_metadata.RUNTIME_VERSION}", "runtime tag is inconsistent")
    history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
    require("# v1086.9 Desktop Alpha Conversation Readiness Checkpoint" in history, "release history entry missing")


def test_checkpoint_has_exact_bounded_area_set() -> None:
    report = build()
    expected = {
        "everyday_consecutive_use", "restart_and_session_resumption", "provider_outage_and_return",
        "interruption_and_steering", "retry_regeneration_and_resend", "message_editing_and_branching",
        "per_conversation_response_preferences", "temporary_instruction_scope", "pinned_working_context",
        "offline_queued_operator_intent", "offline_local_surfaces", "large_history_and_layout",
        "multi_tab_exactly_once_and_immutability", "relationship_memory_and_personality",
        "operator_authority_and_privacy",
    }
    require(report["area_count"] == checkpoint.CHECKPOINT_AREA_COUNT == 15, "checkpoint area count changed")
    require({row["name"] for row in report["areas"]} == expected, "checkpoint areas changed")
    require(report["ready_area_count"] == 15 and report["checkpoint_status"] == "ready_for_operator_evaluation", "checkpoint is not ready")


def test_everyday_long_session_bounds_remain_complete_turn_windows() -> None:
    metrics = area(build(), "everyday_consecutive_use")["metrics"]
    require(metrics["long_session_threshold"] == 120, "long-session threshold changed")
    require(metrics["initial_render_window"] == 80, "initial render bound changed")
    require(metrics["earlier_history_window_limit"] == 120, "earlier-history bound changed")
    require(metrics["whole_turn_windows"] and metrics["draft_preserved"], "daily-use preservation weakened")


def test_restart_and_resumption_digest_is_deterministic_and_read_only() -> None:
    before = source_snapshot()
    first = build()
    second = build()
    after = source_snapshot()
    require(first["contract_digest"] == second["contract_digest"], "checkpoint digest changed across reload-equivalent builds")
    require(first["areas_digest"] == second["areas_digest"], "area digest changed across reload-equivalent builds")
    require(before == after, "checkpoint mutated source tree")
    metrics = area(first, "restart_and_session_resumption")["metrics"]
    require(metrics["session_selection_persisted"] and metrics["drafts_persisted"] and metrics["controls_persisted"], "restart state missing")
    require(not metrics["current_turn_instruction_persisted"] and not metrics["writes_state"], "current-turn scope or checkpoint wrote state")


def test_provider_outage_and_return_never_replay_or_auto_execute() -> None:
    metrics = area(build(), "provider_outage_and_return")["metrics"]
    require(metrics["outage_state"] == "local_surfaces_only" and metrics["returned_state"] == "online", "outage/return states wrong")
    require(not metrics["generation_offline"] and metrics["generation_returned"], "provider capability transition wrong")
    require(not metrics["automatic_request_replay"], "accepted request replay enabled")
    require(not metrics["automatic_execution_after_return"] and not metrics["automatic_resend"], "queued intent auto-executes")


def test_interruption_is_cancellation_first_and_blocks_partial_memory() -> None:
    evidence = area(build(), "interruption_and_steering")
    metrics = evidence["metrics"]
    require(evidence["reason"] == "explicit_cancel_then_fresh_send", "steering reason changed")
    require(metrics["cancellation_first"] and metrics["steering_allowed"], "steering plan is not cancellation-first")
    require(metrics["fresh_acceptance_identity_required"], "fresh acceptance is not required")
    require(not metrics["accepted_request_replay"] and not metrics["redirect_written"], "accepted request was mutated or replayed")
    require(not metrics["cancelled_memory_commit_allowed"] and not metrics["failed_memory_commit_allowed"], "failed/cancelled memory commit enabled")
    require(not metrics["partial_response_committed"], "partial response was committed")


def test_failed_retry_regeneration_and_resend_keep_distinct_identities() -> None:
    metrics = area(build(), "retry_regeneration_and_resend")["metrics"]
    require(metrics["action_types"] == ["failed_retry", "regenerate_completed_response", "explicit_resend"], "action types changed")
    require(metrics["failed_retry_reuses_acceptance"], "failed retry lost accepted identity")
    require(metrics["regeneration_reuses_user_memory"], "regeneration user-memory identity changed")
    require(metrics["resend_creates_new_user_turn"], "resend no longer creates a new turn")
    require(not metrics["automatic_retry"] and not metrics["automatic_regeneration"] and not metrics["automatic_resend"], "automatic turn action enabled")


def test_message_editing_preserves_original_and_does_not_send() -> None:
    metrics = area(build(), "message_editing_and_branching")["metrics"]
    require(metrics["branch_allowed"], "explicit branch plan blocked")
    require(metrics["original_session_preserved"] and metrics["original_turn_preserved"], "source conversation not preserved")
    require(not metrics["raw_transcript_rewritten"], "raw transcript rewrite enabled")
    require(not metrics["provider_invoked"] and not metrics["message_submitted"] and not metrics["automatic_branch_creation"], "branch plan has side effects")


def test_response_preferences_are_session_local_with_current_turn_override() -> None:
    metrics = area(build(), "per_conversation_response_preferences")["metrics"]
    require(metrics["mode"] == "detailed" and metrics["format"] == "steps", "preference probe changed")
    require(metrics["session_local"] and metrics["current_turn_override_allowed"], "preference scope weakened")
    require(not metrics["mutates_global_personality"], "preference mutates personality")
    require(metrics["override_changes_effective_guidance"], "current-turn override is not reflected")
    require(len(metrics["stored_instruction_digest"]) == 64 and len(metrics["turn_override_digest"]) == 64, "preference digest missing")


def test_temporary_instruction_scopes_cover_turn_topic_session_and_clear() -> None:
    metrics = area(build(), "temporary_instruction_scope")["metrics"]
    require(metrics["scope_count"] == 4, "temporary instruction scope count changed")
    require(metrics["current_turn_active"] and metrics["current_turn_only"] and not metrics["current_turn_persisted"], "current-turn scope wrong")
    require(metrics["current_topic_active"] and not metrics["topic_shift_active"], "topic scope did not deactivate")
    require(metrics["topic_shift_reason"] == "topic_changed", "topic-shift reason changed")
    require(metrics["current_session_active"] and metrics["until_cleared_active"], "persisted scopes inactive")
    require(not metrics["mutates_personality"] and not metrics["grants_protected_authority"] and not metrics["provider_invoked"], "temporary scope escalated")


def test_pins_are_bounded_scoped_expiring_revision_guarded_and_budgeted() -> None:
    metrics = area(build(), "pinned_working_context")["metrics"]
    require(metrics["record_count"] == metrics["maximum_items"] == 8, "pin count bound changed")
    require(metrics["maximum_item_chars"] == 1200 and metrics["prompt_budget_chars"] == 4800, "pin size budget changed")
    require(metrics["topic_active_before_shift"] and not metrics["topic_active_after_shift"], "topic pin scope failed")
    require(metrics["expired_count"] == 1, "expired pin not excluded")
    require(metrics["admitted_chars"] <= metrics["prompt_budget_chars"], "pin prompt budget exceeded")
    require(metrics["all_revisions_positive"] and metrics["stale_revision_rejected"], "pin revisions unguarded")
    require(not metrics["mutates_personality"] and not metrics["grants_protected_authority"] and not metrics["provider_invoked"], "pin escalated")


def test_offline_intent_is_content_free_pending_operator_review() -> None:
    evidence = area(build(), "offline_queued_operator_intent")
    metrics = evidence["metrics"]
    require(metrics["intent_state"] == "ready" and evidence["reason"] == "explicit_review_required", "offline intent state wrong")
    require(metrics["explicit_confirmation_required"], "offline intent lost confirmation")
    require(not metrics["automatic_execution"] and not metrics["automatic_resend"], "offline intent auto-executes")
    require(not metrics["provider_invoked"] and not metrics["writes_state"], "offline evidence has side effects")
    require(len(metrics["intent_digest"]) == 64, "offline intent digest missing")


def test_offline_local_surfaces_remain_available_without_provider() -> None:
    metrics = area(build(), "offline_local_surfaces")["metrics"]
    for key in ("draft_preserved", "navigation_preserved", "search_preserved", "memory_browse_preserved", "context_inspection_preserved", "branching_preserved"):
        require(metrics[key] is True, f"{key} is unavailable offline")
    require(not metrics["provider_invoked"], "offline surfaces invoked provider")


def test_large_history_scroll_jump_and_narrow_layout_contracts_remain() -> None:
    metrics = area(build(), "large_history_and_layout")["metrics"]
    require(metrics["initial_render_window"] == 80 and metrics["earlier_history_window_limit"] == 120, "history bounds changed")
    require(metrics["whole_turn_windows"] and metrics["scroll_anchor_preserved_on_prepend"] and metrics["jump_to_latest_preserved"], "scroll contract weakened")
    require(metrics["narrow_layout_contained"] and not metrics["full_transcript_embedded"], "layout or transcript boundary weakened")
    render = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
    styles = (AGENT / "dashboard_chat_styles.py").read_text(encoding="utf-8")
    require("@media (max-width:620px)" in styles and "grid-template-columns:1fr" in styles, "narrow layout CSS missing")
    require("Load earlier messages" in render and "chat-jump-latest" in render, "history navigation controls missing")


def test_multi_tab_exactly_once_claims_and_source_immutability_remain() -> None:
    metrics = area(build(), "multi_tab_exactly_once_and_immutability")["metrics"]
    require(metrics["stale_revision_rejected"] and metrics["mutation_claim_required"] and metrics["cross_process_lease_required"], "multi-tab guard weakened")
    require(not metrics["accepted_operation_replayed"] and metrics["exactly_once_completion_claim"], "exactly-once guard weakened")
    require(not metrics["source_tree_mutation_required"], "checkpoint requires source mutation")


def test_relationship_corrections_curation_deletion_mood_personality_and_affection_remain_bounded() -> None:
    metrics = area(build(), "relationship_memory_and_personality")["metrics"]
    require(metrics["correction_state"] in {"ready", "review_required"}, "correction state missing")
    require(metrics["curation_state"] in {"clear", "review_required"}, "curation state missing")
    require(metrics["retraction_deletion_state"] == "ready", "retraction/deletion state wrong")
    require(metrics["mood_state"] == "bounded" and metrics["important_moment_state"] == "ready", "emotional continuity state wrong")
    require(metrics["personality_state"] == "stable", "personality state wrong")
    require(metrics["affection_inflation_state"] == "blocked", "affection inflation guard weakened")
    require(not metrics["provider_invoked"] and not metrics["writes_state"], "continuity checkpoint has side effects")
    require(not metrics["raw_transcript_rewritten"] and not metrics["memory_content_returned"], "continuity leaked or rewrote content")


def test_operator_authority_cannot_escalate() -> None:
    metrics = area(build(), "operator_authority_and_privacy")["metrics"]
    for key in ("provider_invoked", "model_management", "provider_switching", "generation_settings_changed", "approval_granted", "rollback_authorized", "installation_performed", "promotion_performed", "release_certified", "hidden_reasoning_returned", "private_content_returned", "writes_state"):
        require(metrics[key] is False, f"protected authority escalated: {key}")


def test_checkpoint_is_content_free_and_redacted() -> None:
    report = build()
    require(report["read_only"] and report["content_free"] and report["redacted"], "checkpoint public flags wrong")
    require(not report["provider_invoked"] and not report["embedding_provider_invoked"] and not report["writes_state"], "checkpoint has side effects")
    require(not checkpoint.conversation_readiness_checkpoint_contains_private_fields(report), "checkpoint exposes private fields")
    serialized = json.dumps(report, sort_keys=True).lower()
    for forbidden in ("private current turn instruction", "private pinned working context", "private edited user message", "private redirect text"):
        require(forbidden not in serialized, f"private probe text leaked: {forbidden}")


def test_get_only_api_route_is_registered_and_content_free() -> None:
    status, payload = api_server.handle_api_get("/api/conversation/readiness-checkpoint", {})
    require(status == 200 and payload.get("ok"), "checkpoint GET route failed")
    require(payload["data"]["type"] == "desktop_alpha_conversation_readiness_checkpoint", "wrong checkpoint payload")
    require(not checkpoint.conversation_readiness_checkpoint_contains_private_fields(payload["data"]), "API checkpoint leaked private fields")
    source = (AGENT / "api_server.py").read_text(encoding="utf-8")
    require('if parts == ["conversation", "readiness-checkpoint"]' in source, "GET route missing")
    post_section = source[source.index("def handle_api_post"):]
    require('parts == ["conversation", "readiness-checkpoint"]' not in post_section, "checkpoint mutation route exists")


def test_javascript_syntax_and_narrow_layout_compile() -> None:
    dashboard = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
    styles = (AGENT / "dashboard_chat_styles.py").read_text(encoding="utf-8")
    require("@media (max-width:620px)" in styles, "narrow-layout media query missing")
    require("chat-working-context-editor" in dashboard and "chat-offline-intent-editor" in dashboard, "conversation controls missing")
    node = shutil.which("node")
    if node:
        html = dashboard_chat_console.render_realtime_chat_panel(None, compact=True)
        with tempfile.TemporaryDirectory(prefix="eidolon-v1086-9-js-") as raw:
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


def test_source_only_privacy_and_archive_boundaries() -> None:
    forbidden_names = {"projects.json", "memories.json", "tasks.json"}
    violations = []
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT).as_posix()
        if any(part in {".git", ".venv", "venv", "__pycache__"} for part in path.parts):
            violations.append(rel)
        if path.is_file() and (path.suffix.lower() in {".pyc", ".zip"}):
            violations.append(rel)
        if path.is_file() and path.name in forbidden_names and rel not in {"data/workspaces/projects.json"}:
            violations.append(rel)
        if rel.startswith("data/approvals/") or rel.startswith("data/autonomy/") or rel.startswith("data/conversations/"):
            violations.append(rel)
    require(not violations, f"source-only privacy violations: {violations[:8]}")


def test_suite_registration_is_exact_once() -> None:
    names = [spec.name for spec in isolated_verify.SUITES]
    require(names.count("v1086.9-desktop-alpha-conversation-readiness-checkpoint") == 1, "suite registration not exact")
    require(names.index("v1086.9-desktop-alpha-conversation-readiness-checkpoint") < names.index("v1086.8-long-session-performance-ux-hardening"), "suite order wrong")


TESTS = [(name.removeprefix("test_"), fn) for name, fn in list(globals().items()) if name.startswith("test_")]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.parse_args()
    checks = []
    passed = 0
    for name, fn in TESTS:
        try:
            fn()
        except Exception as error:
            checks.append({"name": name, "status": "fail", "message": f"{type(error).__name__}: {error}"})
        else:
            passed += 1
            checks.append({"name": name, "status": "pass", "message": ""})
    report = {
        "suite": "v1086.9-desktop-alpha-conversation-readiness-checkpoint",
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
