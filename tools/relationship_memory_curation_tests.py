from __future__ import annotations

"""Deterministic v1079.4 operator-controlled continuity-memory curation fixtures."""

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
sys.path.insert(0, str(AGENT))
EXTERNAL_DATA_DIR = Path(os.environ.get("EIDOLON_DATA_DIR") or (ROOT / "data")).resolve()


def _snapshot_tree(root: Path) -> Path:
    backup = Path(tempfile.mkdtemp(prefix="eidolon-relationship-curation-backup-"))
    if root.exists():
        shutil.copytree(root, backup / "data", dirs_exist_ok=True)
    return backup


def _restore_tree(root: Path, backup: Path) -> None:
    if root.exists():
        shutil.rmtree(root)
    saved = backup / "data"
    if saved.exists():
        shutil.copytree(saved, root)
    shutil.rmtree(backup, ignore_errors=True)


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        return digest.hexdigest()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _seed_memories() -> list[dict[str, Any]]:
    return [
        {
            "type": "preference",
            "content": "Marcus prefers concise technical answers.",
            "importance": "high",
            "created_at": "2026-01-01T00:00:00",
        },
        {
            "type": "nickname",
            "content": "Restricted nickname should remain hidden from curation controls.",
            "privacy": "restricted",
        },
        {
            "type": "conversation_user",
            "content": "Call me TranscriptName from now on.",
        },
    ]


def _load_modules() -> dict[str, Any]:
    import dashboard
    from dashboard_chat_console import render_realtime_chat_panel
    from memory import load_memories, mutate_memories, store_memory
    from paths import MEMORY_FILE, SELF_FILE
    from relationship_continuity import build_relationship_continuity_snapshot
    from relationship_memory_curation import (
        CURATABLE_RELATIONSHIP_TYPES,
        RelationshipMemoryCurationError,
        create_relationship_memory,
        delete_retracted_relationship_memory,
        list_relationship_memory_curation_records,
        relationship_memory_curation_summary,
        update_relationship_memory,
    )
    return locals()


def _seed_runtime(modules: dict[str, Any]) -> None:
    EXTERNAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    modules["MEMORY_FILE"].parent.mkdir(parents=True, exist_ok=True)
    modules["MEMORY_FILE"].write_text(json.dumps(_seed_memories(), indent=2), encoding="utf-8")
    modules["SELF_FILE"].write_text(
        json.dumps({"name": "Eidolon", "active_goals": [], "current_state": {"mood_label": "steady"}}, indent=2),
        encoding="utf-8",
    )


def _run_check(name: str, function: Callable[[], None]) -> dict[str, Any]:
    try:
        function()
        return {"name": name, "status": "pass"}
    except Exception as error:
        return {"name": name, "status": "fail", "error": f"{type(error).__name__}: {error}"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    backup = _snapshot_tree(EXTERNAL_DATA_DIR)
    checks: list[dict[str, Any]] = []
    restored = False
    restore_error = ""
    state: dict[str, Any] = {}
    try:
        if EXTERNAL_DATA_DIR.exists():
            shutil.rmtree(EXTERNAL_DATA_DIR)
        modules = _load_modules()
        _seed_runtime(modules)

        def explicit_create_writes_one_safe_memory() -> None:
            before = modules["load_memories"]()
            result = modules["create_relationship_memory"](
                "nickname",
                "Marcus prefers to be called Marc in casual conversation.",
                importance="high",
                source="fixture_operator",
            )
            after = modules["load_memories"]()
            assert result["ok"] and result["created"] and result["changed"]
            assert len(after) == len(before) + 1
            memory = after[-1]
            assert memory["type"] == "nickname"
            assert memory["relationship_eligible"] is True
            assert memory["use_in_conversation"] is True
            assert memory["status"] == "active"
            assert memory["source"] == "fixture_operator"
            event = memory["curation_history"][-1]
            assert event["operator_explicit"] is True
            assert event["provider_invoked"] is False
            assert event["transcript_inferred"] is False
            assert event["personality_mutated"] is False
            state["record_key"] = result["record"]["record_key"]
            state["content"] = memory["content"]
        checks.append(_run_check("explicit_create_adds_one_operator_authored_memory_without_provider_or_transcript_inference", explicit_create_writes_one_safe_memory))

        def duplicate_create_is_idempotent() -> None:
            before = modules["load_memories"]()
            before_digest = _tree_digest(EXTERNAL_DATA_DIR)
            result = modules["create_relationship_memory"](
                "nickname",
                "  Marcus prefers to be called Marc in casual conversation.  ",
                importance="critical",
            )
            after = modules["load_memories"]()
            assert result["status"] == "duplicate"
            assert result["created"] is False and result["changed"] is False
            assert after == before
            assert _tree_digest(EXTERNAL_DATA_DIR) == before_digest
        checks.append(_run_check("equivalent_active_memory_is_not_duplicated_by_repeat_form_submission", duplicate_create_is_idempotent))

        def shared_transaction_prevents_concurrent_lost_updates() -> None:
            before = len(modules["load_memories"]())
            entered = threading.Event()
            release = threading.Event()
            errors: list[str] = []

            def hold_transaction(memories: list[dict[str, Any]]) -> None:
                memories.append({"type": "transaction_marker", "content": "shared-lock-holder"})
                entered.set()
                if not release.wait(timeout=5):
                    raise TimeoutError("shared transaction fixture release timed out")

            def run(target: Callable[[], Any]) -> None:
                try:
                    target()
                except Exception as error:
                    errors.append(f"{type(error).__name__}: {error}")

            holder = threading.Thread(target=lambda: run(lambda: modules["mutate_memories"](hold_transaction)))
            ordinary = threading.Thread(target=lambda: run(lambda: modules["store_memory"]({
                "type": "conversation_user",
                "content": "simultaneous ordinary memory",
            })))
            curated = threading.Thread(target=lambda: run(lambda: modules["create_relationship_memory"](
                "preference",
                "Marcus prefers memory writes that cannot overwrite one another.",
                source="concurrent_fixture_operator",
            )))
            import vector_memory
            original_vector_write = vector_memory.add_memory_vector
            vector_memory.add_memory_vector = lambda _memory: ""
            try:
                holder.start()
                assert entered.wait(timeout=5)
                ordinary.start()
                curated.start()
                time.sleep(0.1)
                release.set()
                for thread in (holder, ordinary, curated):
                    thread.join(timeout=5)
                    assert not thread.is_alive()
            finally:
                vector_memory.add_memory_vector = original_vector_write
            assert not errors, errors
            after = modules["load_memories"]()
            assert len(after) == before + 3
            contents = {str(memory.get("content") or "") for memory in after}
            assert "shared-lock-holder" in contents
            assert "simultaneous ordinary memory" in contents
            assert "Marcus prefers memory writes that cannot overwrite one another." in contents

        checks.append(_run_check("ordinary_and_curated_memory_writes_share_one_atomic_transaction_lock", shared_transaction_prevents_concurrent_lost_updates))

        def invalid_create_is_blocked_without_writes() -> None:
            before_digest = _tree_digest(EXTERNAL_DATA_DIR)
            for memory_type, content in [("conversation_user", "No"), ("nickname", "   ")]:
                try:
                    modules["create_relationship_memory"](memory_type, content)
                    raise AssertionError("invalid memory unexpectedly created")
                except modules["RelationshipMemoryCurationError"]:
                    pass
            assert _tree_digest(EXTERNAL_DATA_DIR) == before_digest
        checks.append(_run_check("unsupported_or_blank_memory_is_blocked_without_runtime_mutation", invalid_create_is_blocked_without_writes))

        def read_views_are_pure_and_hide_restricted_rows() -> None:
            before = _tree_digest(EXTERNAL_DATA_DIR)
            rows = modules["list_relationship_memory_curation_records"]()
            summary = modules["relationship_memory_curation_summary"]()
            after = _tree_digest(EXTERNAL_DATA_DIR)
            raw = json.dumps(rows)
            assert before == after
            assert summary["writes_on_read"] is False
            assert "Restricted nickname" not in raw
            assert "TranscriptName" not in raw
            assert any(row["content"] == state["content"] for row in rows)
        checks.append(_run_check("curation_listing_is_side_effect_free_and_excludes_restricted_or_transcript_rows", read_views_are_pure_and_hide_restricted_rows))

        def disable_preserves_history_and_excludes_prompt_cue() -> None:
            result = modules["update_relationship_memory"](state["record_key"], "disable", source="fixture_operator")
            assert result["changed"] and result["status"] == "disabled"
            memories = modules["load_memories"]()
            memory = next(row for row in memories if row.get("content") == state["content"])
            assert memory["content"] == state["content"]
            assert memory["relationship_eligible"] is False
            assert memory["use_in_conversation"] is False
            assert [event["action"] for event in memory["curation_history"]][-2:] == ["create", "disable"]
            snapshot = modules["build_relationship_continuity_snapshot"](memories, {"current_state": {}}, user_message="Marc")
            assert state["content"] not in snapshot.to_prompt_block()
        checks.append(_run_check("disable_preserves_record_and_audit_history_but_excludes_future_prompt_continuity", disable_preserves_history_and_excludes_prompt_cue))

        def repeated_disable_is_idempotent() -> None:
            before = modules["load_memories"]()
            result = modules["update_relationship_memory"](state["record_key"], "disable")
            after = modules["load_memories"]()
            assert result["changed"] is False
            assert after == before
        checks.append(_run_check("repeat_disable_does_not_duplicate_curation_history", repeated_disable_is_idempotent))

        def restore_reincludes_cue() -> None:
            result = modules["update_relationship_memory"](state["record_key"], "restore")
            assert result["changed"] and result["status"] == "active"
            memories = modules["load_memories"]()
            snapshot = modules["build_relationship_continuity_snapshot"](memories, {"current_state": {}}, user_message="Marc")
            assert state["content"] in snapshot.to_prompt_block()
        checks.append(_run_check("explicit_restore_reenables_the_same_memory_without_creating_a_copy", restore_reincludes_cue))

        def retract_and_restore_never_delete_memory() -> None:
            count_before = len(modules["load_memories"]())
            retracted = modules["update_relationship_memory"](state["record_key"], "retract")
            assert retracted["status"] == "retracted"
            memories = modules["load_memories"]()
            assert len(memories) == count_before
            memory = next(row for row in memories if row.get("content") == state["content"])
            assert memory["status"] == "retracted"
            assert state["content"] not in modules["build_relationship_continuity_snapshot"](memories, {"current_state": {}}, user_message="Marc").to_prompt_block()
            restored_result = modules["update_relationship_memory"](state["record_key"], "restore")
            assert restored_result["status"] == "active"
            assert len(modules["load_memories"]()) == count_before
        checks.append(_run_check("retract_and_restore_are_explicit_reversible_state_changes_not_deletion", retract_and_restore_never_delete_memory))

        def confirmed_delete_removes_only_retracted_content() -> None:
            created = modules["create_relationship_memory"](
                "preference",
                "Delete this dedicated continuity-memory fixture after retraction.",
                source="fixture_operator",
            )
            record_key = created["record"]["record_key"]
            before_active = modules["load_memories"]()
            for confirmation in ("DELETE", "delete"):
                try:
                    modules["delete_retracted_relationship_memory"](record_key, confirmation)
                    raise AssertionError("active or incorrectly confirmed memory unexpectedly deleted")
                except modules["RelationshipMemoryCurationError"]:
                    pass
            assert modules["load_memories"]() == before_active
            modules["update_relationship_memory"](record_key, "retract")
            html = modules["render_realtime_chat_panel"](None)
            assert "dashboard_relationship_memory_delete" in html
            assert "Type DELETE" in html and "Delete permanently" in html

            import vector_memory
            original_delete = vector_memory.delete_memory_vector_verified
            deleted_ids: list[str] = []
            vector_memory.delete_memory_vector_verified = lambda memory_id: (
                deleted_ids.append(str(memory_id))
                or {
                    "cleanup_complete": True,
                    "deletion_attempted": True,
                    "verification_status": "verified_absent",
                    "verified_absent": True,
                    "semantic_store_available": True,
                    "provider_invoked": False,
                    "content_free": True,
                }
            )
            try:
                result = modules["delete_retracted_relationship_memory"](record_key, "DELETE", source="fixture_operator")
            finally:
                vector_memory.delete_memory_vector_verified = original_delete
            memories = modules["load_memories"]()
            serialized = json.dumps(memories)
            assert result["status"] == "deleted" and result["content_removed"] is True
            assert "Delete this dedicated continuity-memory fixture" not in serialized
            assert record_key not in {row["record_key"] for row in modules["list_relationship_memory_curation_records"]()}
            tombstone = next(row for row in memories if row.get("type") == "relationship_memory_deletion_tombstone")
            assert tombstone["content_removed"] is True and "content" not in tombstone
            assert deleted_ids == [created["record"]["id"]]
        checks.append(_run_check("confirmed_permanent_delete_requires_retraction_removes_content_and_retains_only_tombstone", confirmed_delete_removes_only_retracted_content))

        def stale_legacy_key_is_rejected() -> None:
            rows = modules["list_relationship_memory_curation_records"]()
            legacy = next(row for row in rows if row["record_key"].startswith("legacy:"))
            bad_key = legacy["record_key"][:-1] + ("0" if legacy["record_key"][-1] != "0" else "1")
            before = _tree_digest(EXTERNAL_DATA_DIR)
            try:
                modules["update_relationship_memory"](bad_key, "disable")
                raise AssertionError("stale legacy key unexpectedly mutated memory")
            except modules["RelationshipMemoryCurationError"]:
                pass
            assert _tree_digest(EXTERNAL_DATA_DIR) == before
        checks.append(_run_check("stale_or_mismatched_legacy_record_key_cannot_mutate_a_different_memory", stale_legacy_key_is_rejected))

        def dashboard_get_is_pure_and_exposes_explicit_controls() -> None:
            session_dir = EXTERNAL_DATA_DIR / "conversation_sessions"
            before = _tree_digest(EXTERNAL_DATA_DIR)
            html = modules["render_realtime_chat_panel"](None)
            after = _tree_digest(EXTERNAL_DATA_DIR)
            assert before == after
            assert not session_dir.exists()
            assert "Manage continuity memories" in html
            assert "dashboard_relationship_memory_create" in html
            assert "dashboard_relationship_memory_update" in html
            assert "Add continuity memory" in html
            assert "Session transcripts are never mined" in html
            assert "receipt_path" not in html and "timings_ms" not in html
        checks.append(_run_check("dashboard_get_renders_create_disable_restore_retract_controls_without_writing_runtime_state", dashboard_get_is_pure_and_exposes_explicit_controls))

        def dashboard_post_actions_use_curation_service() -> None:
            before_count = len(modules["load_memories"]())
            modules["dashboard"].DashboardState.error = ""
            modules["dashboard"].handle_action({
                "action": ["dashboard_relationship_memory_create"],
                "memory_type": ["important_moment"],
                "content": ["Marcus and Eidolon completed the relationship-memory curation checkpoint."],
                "importance": ["high"],
            })
            assert modules["dashboard"].DashboardState.error == ""
            assert len(modules["load_memories"]()) == before_count + 1
            row = next(
                item for item in modules["list_relationship_memory_curation_records"]()
                if item["content"].startswith("Marcus and Eidolon completed")
            )
            modules["dashboard"].handle_action({
                "action": ["dashboard_relationship_memory_update"],
                "record_key": [row["record_key"]],
                "curation_action": ["disable"],
            })
            updated = next(item for item in modules["list_relationship_memory_curation_records"]() if item["record_key"] == row["record_key"])
            assert updated["state"] == "disabled"
        checks.append(_run_check("dashboard_post_routes_apply_only_explicit_operator_curation_actions", dashboard_post_actions_use_curation_service))

        def summary_is_governance_neutral() -> None:
            summary = modules["relationship_memory_curation_summary"]()
            assert summary["transcript_inference"] is False
            assert summary["provider_invocation"] is False
            assert summary["personality_mutation"] is False
            assert summary["deletes_memories"] is True
            assert summary["deletes_memories_without_confirmation"] is False
            assert summary["confirmed_permanent_deletion_supported"] is True
            assert summary["permanent_deletion_requires_retracted_state"] is True
            assert summary["permanent_deletion_requires_exact_confirmation"] is True
            assert set(modules["CURATABLE_RELATIONSHIP_TYPES"]) == {
                "nickname", "preference", "relationship", "important_moment", "commitment", "personal_fact", "user_mood"
            }
        checks.append(_run_check("curation_summary_preserves_provider_personality_autonomy_and_deletion_boundaries", summary_is_governance_neutral))

    finally:
        try:
            _restore_tree(EXTERNAL_DATA_DIR, backup)
            restored = True
        except Exception as error:
            restore_error = f"{type(error).__name__}: {error}"

    failed = [check for check in checks if check["status"] != "pass"]
    report = {
        "ok": not failed and restored,
        "status": "pass" if not failed and restored else "blocked",
        "suite": "v1079.4-relationship-memory-curation",
        "evidence_kind": "deterministic_fixture",
        "native_provider_evidence": False,
        "passed": len(checks) - len(failed),
        "total": len(checks),
        "checks": checks,
        "runtime_data_restored": restored,
        "runtime_data_restore_error": restore_error or None,
        "governance": {
            "operator_explicit_writes_only": True,
            "infers_from_transcripts": False,
            "invokes_provider": False,
            "mutates_personality": False,
            "deletes_memories": True,
            "deletes_memories_without_confirmation": False,
            "deletes_only_retracted_memories_with_exact_confirmation": True,
            "changes_provider_or_model": False,
            "performs_autonomous_actions": False,
        },
    }
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"{report['status']}: {report['passed']}/{report['total']}")
        for check in checks:
            suffix = f" - {check['error']}" if check.get("error") else ""
            print(f"- {check['status']}: {check['name']}{suffix}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
