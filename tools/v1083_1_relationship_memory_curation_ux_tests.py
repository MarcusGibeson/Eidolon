from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
TOOLS = ROOT / "tools"
sys.path.insert(0, str(AGENT))

import conversation_operations as operations
import dashboard
import dashboard_chat_console
import memory
import memory_commit_attribution as attribution
import post_review_development_verify as isolated_verify
import relationship_memory_curation as curation


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


class isolated_memory:
    def __enter__(self):
        self.temp = tempfile.TemporaryDirectory(prefix="eidolon-v1083-1-")
        root = Path(self.temp.name)
        self.original = (
            memory.MEMORY_FILE,
            memory.THOUGHT_LOG_FILE,
            operations.CONVERSATION_OPERATION_DIR,
            operations.CONVERSATION_OPERATION_ACKNOWLEDGEMENT_DIR,
        )
        memory.MEMORY_FILE = root / "memories.json"
        memory.THOUGHT_LOG_FILE = root / "thoughts.log"
        operations.CONVERSATION_OPERATION_DIR = root / "operations"
        operations.CONVERSATION_OPERATION_ACKNOWLEDGEMENT_DIR = root / "acknowledgements"
        return root

    def __exit__(self, *_args):
        (
            memory.MEMORY_FILE,
            memory.THOUGHT_LOG_FILE,
            operations.CONVERSATION_OPERATION_DIR,
            operations.CONVERSATION_OPERATION_ACKNOWLEDGEMENT_DIR,
        ) = self.original
        self.temp.cleanup()


def test_operator_created_memory_exposes_content_free_provenance() -> None:
    with isolated_memory():
        result = curation.create_relationship_memory("preference", "Marcus prefers quiet mornings.", source="operator_relationship_curation_fixture")
        record = result["record"]
        provenance = record["provenance"]
        require(provenance["origin"] == "operator_explicit", "operator provenance missing")
        require(provenance["operator_explicit"], "operator explicit flag missing")
        require(not provenance["provider_invoked"] and not provenance["transcript_inferred"], "operator curation claimed inference")
        require("Marcus prefers quiet mornings" not in json.dumps(provenance), "content leaked into provenance")


def test_generated_turn_provenance_is_visible_without_prompt_or_response() -> None:
    with isolated_memory():
        operation_id = "conversation_20260720T130000_aaaaaaaaaaaa"
        session_id = "conversation_session_20260720T130000_bbbbbbbbbb"
        operations.create_operation_marker(operation_id, session_id, acceptance_key="chat_accept_cccccccccccccccccccccccccccccccc")
        evidence = attribution.build_memory_commit_attribution(
            role="assistant", operation_id=operation_id, session_id=session_id, turn_id=operation_id,
            source="fixture_generated", content="Private generated content", completion_state="completed",
            provider_generation_completed=True, operation_completion_claimed=True,
        )
        memory.store_memory({
            "id": "relationship-generated-fixture",
            "type": "important_moment",
            "content": "Operator-approved summary of a shared moment.",
            "source": "generated_memory_candidate_fixture",
            "status": "active",
            "relationship_eligible": True,
            "use_in_conversation": True,
            "memory_commit_attribution": evidence,
        }, vectorize=False)
        record = curation.list_relationship_memory_curation_records()[0]
        provenance = record["provenance"]
        require(provenance["origin"] == "generated_turn", "generated origin missing")
        require(provenance["conversation_session_id"] == session_id, "session provenance missing")
        require(provenance["conversation_turn_id"] == operation_id, "turn provenance missing")
        serialized = json.dumps(provenance)
        require("Private generated content" not in serialized, "generated response leaked")
        require("Private generated content" not in serialized, "generated content leaked")
        require(provenance.get("contains_prompt") is False and provenance.get("contains_response") is False, "content-free flags wrong")


def test_retain_is_explicit_bounded_and_idempotent() -> None:
    with isolated_memory():
        created = curation.create_relationship_memory("relationship", "Marcus values direct, honest conversation.")
        key = created["record"]["record_key"]
        retained = curation.update_relationship_memory(key, "retain", source="fixture_operator")
        repeated = curation.update_relationship_memory(key, "retain", source="fixture_operator")
        require(retained["changed"] and retained["record"]["retention_confirmed"], "retention not recorded")
        require(not repeated["changed"], "repeat retain duplicated review history")
        stored = memory.load_memories()[0]
        require([event["action"] for event in stored["curation_history"]] == ["create", "retain"], "retention history wrong")


def test_correction_replaces_only_curated_content_and_preserves_digest_history() -> None:
    with isolated_memory():
        created = curation.create_relationship_memory("personal_fact", "Marcus prefers the old wording.", importance="low")
        key = created["record"]["record_key"]
        result = curation.correct_relationship_memory(key, "Marcus prefers the corrected wording.", importance="high", source="fixture_operator")
        require(result["changed"] and result["raw_conversation_history_changed"] is False, "correction boundary wrong")
        stored = memory.load_memories()[0]
        require(stored["content"] == "Marcus prefers the corrected wording.", "corrected content not stored")
        require(stored["importance"] == "high", "corrected importance not stored")
        event = stored["curation_history"][-1]
        require(event["action"] == "correct", "correction history missing")
        serialized_event = json.dumps(event)
        require("old wording" not in serialized_event and "corrected wording" not in serialized_event, "content copied into audit history")
        require(event["details"]["previous_content_digest"] != event["details"]["new_content_digest"], "content digests did not change")
        require(not stored.get("retention_confirmed"), "correction retained stale review confirmation")


def test_retracted_memory_must_be_restored_before_correction_or_retention() -> None:
    with isolated_memory():
        created = curation.create_relationship_memory("commitment", "A retracted fixture.")
        key = created["record"]["record_key"]
        curation.update_relationship_memory(key, "retract")
        for action in ("retain",):
            try:
                curation.update_relationship_memory(key, action)
                raise AssertionError("retracted memory unexpectedly retained")
            except curation.RelationshipMemoryCurationError:
                pass
        try:
            curation.correct_relationship_memory(key, "Should not apply")
            raise AssertionError("retracted memory unexpectedly corrected")
        except curation.RelationshipMemoryCurationError:
            pass


def test_dashboard_exposes_review_correction_retention_and_provenance() -> None:
    with isolated_memory():
        created = curation.create_relationship_memory("nickname", "Marc")
        html = dashboard_chat_console.render_realtime_chat_panel(None)
        for token in ("dashboard_relationship_memory_correct", "Save correction", "Retain", "Provenance:", "Content-free evidence only"):
            require(token in html, f"dashboard curation control missing: {token}")
        require("receipt_path" not in html and "timings_ms" not in html, "private receipt details exposed")
        dashboard.DashboardState.error = ""
        dashboard.handle_action({
            "action": ["dashboard_relationship_memory_correct"],
            "record_key": [created["record"]["record_key"]],
            "content": ["Marcus"],
            "importance": ["medium"],
        })
        require(dashboard.DashboardState.error == "", "dashboard correction failed")
        require(curation.list_relationship_memory_curation_records()[0]["content"] == "Marcus", "dashboard correction did not use service")


def test_read_views_remain_pure_and_registration_is_exactly_once() -> None:
    with isolated_memory() as root:
        curation.create_relationship_memory("preference", "Pure read fixture")
        before = memory.MEMORY_FILE.read_bytes()
        curation.relationship_memory_curation_summary()
        curation.list_relationship_memory_curation_records()
        require(memory.MEMORY_FILE.read_bytes() == before, "curation GET mutated memory")
    core = [suite.name for suite in isolated_verify.select_suites("core")]
    full = [suite.name for suite in isolated_verify.select_suites("full")]
    require(core.count("v1083.1-relationship-memory-curation-ux") == 1, "core registration wrong")
    require(full.count("v1083.1-relationship-memory-curation-ux") == 1, "full registration wrong")
    release_source = (TOOLS / "release_verify.py").read_text(encoding="utf-8")
    require(release_source.count("v1083_1_relationship_memory_curation_ux_tests.py") == 1, "release registration wrong")


TESTS = [
    ("operator_created_memory_exposes_content_free_provenance", test_operator_created_memory_exposes_content_free_provenance),
    ("generated_turn_provenance_is_visible_without_prompt_or_response", test_generated_turn_provenance_is_visible_without_prompt_or_response),
    ("retain_is_explicit_bounded_and_idempotent", test_retain_is_explicit_bounded_and_idempotent),
    ("correction_replaces_only_curated_content_and_preserves_digest_history", test_correction_replaces_only_curated_content_and_preserves_digest_history),
    ("retracted_memory_must_be_restored_before_correction_or_retention", test_retracted_memory_must_be_restored_before_correction_or_retention),
    ("dashboard_exposes_review_correction_retention_and_provenance", test_dashboard_exposes_review_correction_retention_and_provenance),
    ("read_views_remain_pure_and_registration_is_exactly_once", test_read_views_remain_pure_and_registration_is_exactly_once),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.parse_args()
    checks = []
    for name, function in TESTS:
        try:
            function()
        except Exception as error:
            checks.append({"name": name, "status": "fail", "message": f"{type(error).__name__}: {error}"})
        else:
            checks.append({"name": name, "status": "pass", "message": ""})
    passed = sum(check["status"] == "pass" for check in checks)
    report = {"suite": "v1083.1-relationship-memory-curation-ux", "ok": passed == len(checks), "status": "pass" if passed == len(checks) else "fail", "passed": passed, "total": len(checks), "checks": checks}
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
