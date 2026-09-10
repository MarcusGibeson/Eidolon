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

import dashboard_chat_console
import memory
import post_review_development_verify as isolated_verify
import relationship_memory_curation as curation
from important_moment_provenance import build_important_moment_provenance


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


class isolated_memory:
    def __enter__(self):
        self.temp = tempfile.TemporaryDirectory(prefix="eidolon-v1083-5-")
        root = Path(self.temp.name)
        self.original = (memory.MEMORY_FILE, memory.THOUGHT_LOG_FILE)
        memory.MEMORY_FILE = root / "memories.json"
        memory.THOUGHT_LOG_FILE = root / "thoughts.log"
        return root

    def __exit__(self, *_args):
        memory.MEMORY_FILE, memory.THOUGHT_LOG_FILE = self.original
        self.temp.cleanup()


def test_operator_moment_exposes_pending_review_rationale_without_content() -> None:
    with isolated_memory():
        result = curation.create_relationship_memory("important_moment", "Marcus completed a meaningful milestone.", importance="high")
        provenance = result["record"]["important_moment_provenance"]
        require(provenance["rationale_code"] == "operator_explicit_pending_review", "pending-review rationale wrong")
        require(provenance["review_required"] is True and provenance["operator_explicit"] is True, "review flags wrong")
        serialized = json.dumps(provenance)
        require("meaningful milestone" not in serialized, "moment content leaked into rationale")
        require(provenance["contains_prompt"] is False and provenance["contains_response"] is False, "content-free flags wrong")


def test_retain_confirms_exact_content_and_changes_rationale() -> None:
    with isolated_memory():
        created = curation.create_relationship_memory("important_moment", "A retained milestone.")
        key = created["record"]["record_key"]
        retained = curation.update_relationship_memory(key, "retain")
        provenance = retained["record"]["important_moment_provenance"]
        require(provenance["rationale_code"] == "operator_reviewed_exact_content", "retained rationale wrong")
        require(provenance["retention_confirmed"] is True and provenance["review_required"] is False, "retention evidence wrong")
        require(len(provenance["content_digest"]) == 64, "content digest missing")


def test_correction_resets_retention_without_rewriting_raw_history() -> None:
    with isolated_memory():
        created = curation.create_relationship_memory("important_moment", "Original curated summary.")
        key = created["record"]["record_key"]
        curation.update_relationship_memory(key, "retain")
        corrected = curation.correct_relationship_memory(key, "Corrected curated summary.")
        provenance = corrected["record"]["important_moment_provenance"]
        require(provenance["review_required"] is True, "correction did not require renewed review")
        require(provenance["rationale_code"] == "operator_explicit_pending_review", "correction rationale wrong")
        require(corrected["raw_conversation_history_changed"] is False, "raw history rewrite claimed")
        stored_event = memory.load_memories()[0]["curation_history"][-1]
        require("Original curated summary" not in json.dumps(stored_event) and "Corrected curated summary" not in json.dumps(stored_event), "audit history contains content")


def test_temporal_and_eligibility_actions_update_provenance() -> None:
    with isolated_memory():
        created = curation.create_relationship_memory("important_moment", "Action-state fixture.")
        key = created["record"]["record_key"]
        resolved = curation.update_relationship_memory(key, "resolve")["record"]["important_moment_provenance"]
        require(resolved["temporal_state"] == "resolved" and resolved["eligibility_state"] == "not_currently_used", "resolved state wrong")
        reopened = curation.update_relationship_memory(key, "reopen")["record"]["important_moment_provenance"]
        require(reopened["temporal_state"] == "open" and reopened["eligibility_state"] == "eligible", "reopened state wrong")
        disabled = curation.update_relationship_memory(key, "disable")["record"]["important_moment_provenance"]
        require(disabled["eligibility_state"] == "not_currently_used", "disabled eligibility wrong")


def test_legacy_and_generated_rationales_fail_honestly() -> None:
    legacy = build_important_moment_provenance({"type": "important_moment", "content": "Legacy", "relationship_eligible": True})
    generated = build_important_moment_provenance({
        "type": "important_moment", "content": "Generated summary", "relationship_eligible": True,
        "source": "generated_memory_candidate_fixture",
        "memory_commit_attribution": {
            "schema_version": "1", "attribution_id": "attr", "role": "assistant", "operation_id": "op",
            "conversation_session_id": "session", "conversation_turn_id": "turn", "acceptance_identity_digest": "a"*64,
            "content_digest": "b"*64, "eligibility_decision": "eligible_successful_generated_turn",
            "completion_state": "completed", "provider_generation_completed": True, "operation_completion_claimed": True,
            "eligible_for_durable_commit": True, "source": "fixture", "contains_prompt": False, "contains_response": False,
        },
    })
    require(legacy["rationale_code"] == "legacy_unknown" and legacy["review_required"] is True, "legacy rationale not honest")
    require(generated["rationale_code"] == "generated_turn_attributed", "generated rationale missing")
    require(generated["review_required"] is True and generated["operator_explicit"] is False, "generated review boundary wrong")


def test_dashboard_and_summary_expose_rationale_without_private_receipts() -> None:
    with isolated_memory():
        curation.create_relationship_memory("important_moment", "Dashboard provenance fixture.")
        html = dashboard_chat_console.render_realtime_chat_panel(None)
        require("Why retained:" in html and "This rationale is content-free" in html, "dashboard rationale missing")
        require("receipt_path" not in html and "raw_events" not in html, "private receipt exposed")
        summary = curation.relationship_memory_curation_summary()
        require(summary["important_moment_provenance_visible"] is True, "summary provenance flag missing")
        require(summary["raw_conversation_history_rewrite_supported"] is False, "summary allows history rewrite")


def test_registration_is_exactly_once() -> None:
    core = [suite.name for suite in isolated_verify.select_suites("core")]
    full = [suite.name for suite in isolated_verify.select_suites("full")]
    require(core.count("v1083.5-important-moment-provenance") == 1, "core registration wrong")
    require(full.count("v1083.5-important-moment-provenance") == 1, "full registration wrong")
    source = (TOOLS / "release_verify.py").read_text(encoding="utf-8")
    require(source.count("v1083_5_important_moment_provenance_tests.py") == 1, "release registration wrong")


TESTS = [
    ("operator_moment_exposes_pending_review_rationale_without_content", test_operator_moment_exposes_pending_review_rationale_without_content),
    ("retain_confirms_exact_content_and_changes_rationale", test_retain_confirms_exact_content_and_changes_rationale),
    ("correction_resets_retention_without_rewriting_raw_history", test_correction_resets_retention_without_rewriting_raw_history),
    ("temporal_and_eligibility_actions_update_provenance", test_temporal_and_eligibility_actions_update_provenance),
    ("legacy_and_generated_rationales_fail_honestly", test_legacy_and_generated_rationales_fail_honestly),
    ("dashboard_and_summary_expose_rationale_without_private_receipts", test_dashboard_and_summary_expose_rationale_without_private_receipts),
    ("registration_is_exactly_once", test_registration_is_exactly_once),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.parse_args()
    checks = []
    for name, fn in TESTS:
        try:
            fn()
        except Exception as error:
            checks.append({"name": name, "status": "fail", "message": f"{type(error).__name__}: {error}"})
        else:
            checks.append({"name": name, "status": "pass", "message": ""})
    passed = sum(row["status"] == "pass" for row in checks)
    report = {"suite": "v1083.5-important-moment-provenance", "ok": passed == len(checks), "status": "pass" if passed == len(checks) else "fail", "passed": passed, "total": len(checks), "checks": checks}
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
