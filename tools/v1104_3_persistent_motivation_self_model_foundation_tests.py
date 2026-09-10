from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for value in (AGENT, ROOT):
    if str(value) not in os.sys.path:
        os.sys.path.insert(0, str(value))

from persistent_motivation import MotivationStore, motivation_state_contains_forbidden_authority


def require(condition: bool, detail: Any = "requirement failed") -> None:
    if not condition:
        raise AssertionError(detail)


def source_snapshot() -> dict[str, str]:
    return {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(ROOT.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}
    }


def store() -> tuple[MotivationStore, Path]:
    root = Path(tempfile.mkdtemp(prefix="eidolon-v1104-3-")) / "cognition"
    return MotivationStore(root), root


def test_self_model_persists_across_restart_and_provider_switch() -> None:
    first, root = store()
    result = first.initialize_self_model(
        "self-1",
        capabilities=["conversation", "bounded reflection"],
        project_ids=["eidolon-core"],
        provider_id="ollama:qwen",
        evidence_refs=["operator-direction"],
    )
    require(result["result"]["provider_neutral"] is True, result)
    second = MotivationStore(root)
    second.initialize_self_model("self-2", project_ids=["eidolon-core", "other-project"], provider_id="llama.cpp:qwen")
    snapshot = MotivationStore(root).snapshot()
    require(snapshot["identity"]["identity_id"] == "eidolon", snapshot["identity"])
    require(len(snapshot["self_model"]["provider_observations"]) == 2, snapshot["self_model"])
    require(all(item["identity_changed"] is False for item in snapshot["self_model"]["provider_observations"]), snapshot)


def test_enduring_temporary_curiosity_need_concern_preference_and_unresolved_kinds() -> None:
    cognition, _ = store()
    kinds = ["enduring_goal", "temporary_goal", "curiosity", "need", "concern", "preference", "unresolved_subject"]
    for index, kind in enumerate(kinds):
        result = cognition.record_motivation(
            f"event-{index}",
            kind=kind,
            summary=f"summary for {kind}",
            cognitive_state="desire" if kind != "temporary_goal" else "intention",
            origin_type="operator_direction",
            origin_ref=f"ref-{index}",
            urgency=0.1 + index * 0.1,
            confidence=0.8,
        )
        require(result["result"]["created"] is True, result)
    summary = cognition.inspection_summary(item_limit=20)
    require(summary["active_motivation_count"] == 7, summary)
    require({item["kind"] for item in summary["active_motivations"]} == set(kinds), summary)


def test_duplicate_event_and_semantic_duplicate_do_not_duplicate_state() -> None:
    cognition, _ = store()
    first = cognition.record_motivation(
        "same-event",
        kind="curiosity",
        summary="Explore why a test failed",
        cognitive_state="desire",
        origin_type="failure",
        origin_ref="failure-1",
    )
    duplicate_event = cognition.record_motivation(
        "same-event",
        kind="curiosity",
        summary="Explore why a test failed",
        cognitive_state="desire",
        origin_type="failure",
        origin_ref="failure-1",
    )
    semantic_duplicate = cognition.record_motivation(
        "different-event",
        kind="curiosity",
        summary="Explore why a test failed",
        cognitive_state="desire",
        origin_type="reflection",
        origin_ref="reflection-2",
    )
    require(first["result"]["created"] is True, first)
    require(duplicate_event["status"] == "duplicate_event_ignored", duplicate_event)
    require(semantic_duplicate["result"]["status"] == "duplicate_motivation_ignored", semantic_duplicate)
    require(len(cognition.snapshot()["motivations"]) == 1, cognition.snapshot())


def test_motivation_changes_through_evidence_success_and_failure() -> None:
    cognition, _ = store()
    created = cognition.record_motivation(
        "create",
        kind="temporary_goal",
        summary="Finish focused verification",
        cognitive_state="intention",
        origin_type="operator_direction",
        origin_ref="bundle-request",
        urgency=0.6,
        confidence=0.6,
    )
    motivation_id = created["result"]["motivation_id"]
    cognition.update_motivation(
        "failure",
        motivation_id,
        reason_code="test_failed",
        event_type="failure",
        urgency=0.9,
        confidence=0.4,
        authored_conclusion="A focused defect remains and needs another bounded repair.",
        supporting_refs=["test-receipt-1"],
    )
    cognition.update_motivation(
        "success",
        motivation_id,
        reason_code="tests_passed",
        event_type="success",
        urgency=0.0,
        confidence=1.0,
        lifecycle_state="resolved",
        outcome_ref="test-receipt-2",
        authored_conclusion="The bounded verification goal was completed.",
    )
    item = cognition.snapshot()["motivations"][0]
    require(item["lifecycle_state"] == "resolved" and item["confidence"] == 1.0, item)
    require(len(item["update_history"]) == 3, item["update_history"])
    require(any(link["type"] == "affected_by_outcome" for link in item["relationships"]), item)


def test_corrections_and_retractions_remain_accountable_but_inactive() -> None:
    cognition, _ = store()
    created = cognition.record_motivation(
        "create",
        kind="preference",
        summary="Use a particular form of address",
        cognitive_state="desire",
        origin_type="conversation",
        origin_ref="turn-1",
    )
    motivation_id = created["result"]["motivation_id"]
    cognition.retract_motivation("correct", motivation_id, reason_code="relationship_correction", correction_ref="turn-2")
    state = cognition.snapshot()
    item = state["motivations"][0]
    require(item["lifecycle_state"] == "retracted" and item["urgency"] == 0.0, item)
    require(len(item["update_history"]) == 2, item)
    require(cognition.inspection_summary()["active_motivation_count"] == 0, cognition.inspection_summary())
    require(cognition.inspection_summary()["historical_inactive_count"] == 1, cognition.inspection_summary())


def test_motivations_cannot_be_post_hoc_dialogue_justification() -> None:
    cognition, _ = store()
    try:
        cognition.record_motivation(
            "bad",
            kind="curiosity",
            summary="Pretend this motivated an answer",
            origin_type="generated_dialogue",
            origin_ref="turn-9",
            origin_phase="post_generation_justification",
        )
    except ValueError as error:
        require("justify" in str(error), error)
    else:
        raise AssertionError("post-hoc motivation was accepted")
    require(not cognition.path.exists(), "invalid request created a runtime state file")


def test_thought_desire_intention_commitment_proposal_and_authority_are_distinct() -> None:
    cognition, _ = store()
    for index, cognitive_state in enumerate(("thought", "desire", "intention", "commitment", "proposal")):
        cognition.record_motivation(
            f"state-{index}",
            kind="temporary_goal",
            summary=f"State example {cognitive_state}",
            cognitive_state=cognitive_state,
            origin_type="fixture",
            origin_ref=f"state-ref-{index}",
        )
    try:
        cognition.record_motivation(
            "unauthorized",
            kind="temporary_goal",
            summary="Execute a protected action",
            cognitive_state="authorized_action",
            origin_type="reflection",
            origin_ref="reflection-1",
        )
    except PermissionError:
        pass
    else:
        raise AssertionError("internal cognition created authorized action")
    summary = cognition.inspection_summary()
    require(len(summary["cognitive_state_distinctions"]) == 6, summary)
    require(all(row["can_authorize"] is False for row in summary["cognitive_state_distinctions"]), summary)
    require(motivation_state_contains_forbidden_authority(cognition.snapshot()) is False, cognition.snapshot())


def test_relationships_link_memories_commitments_projects_and_outcomes() -> None:
    cognition, _ = store()
    result = cognition.record_motivation(
        "linked",
        kind="concern",
        summary="Preserve rollback safety",
        cognitive_state="commitment",
        origin_type="memory",
        origin_ref="memory-7",
        scope_project_id="eidolon-core",
        relationship_refs=[
            {"type": "derived_from_memory", "target_type": "memory", "target_id": "memory-7"},
            {"type": "linked_commitment", "target_type": "commitment", "target_id": "commitment-2"},
            {"type": "concerns_project", "target_type": "project", "target_id": "eidolon-core"},
        ],
    )
    item = cognition.snapshot()["motivations"][0]
    require(result["result"]["created"] is True, result)
    require(len(item["relationships"]) == 3, item)
    require(item["scope"]["provider_bound"] is False, item)


def test_external_authorization_is_reference_only_and_source_is_immutable() -> None:
    before = source_snapshot()
    cognition, _ = store()
    created = cognition.record_motivation(
        "create",
        kind="temporary_goal",
        summary="Propose a protected patch",
        cognitive_state="proposal",
        origin_type="operator_request",
        origin_ref="turn-4",
    )
    motivation_id = created["result"]["motivation_id"]
    linked = cognition.reference_authorized_action(
        "link-auth",
        motivation_id=motivation_id,
        governed_action_id="action-1",
        authorization_receipt_id="approval-receipt-1",
    )
    require(linked["result"]["internal_authority_granted"] is False, linked)
    item = cognition.snapshot()["motivations"][0]
    require(item["authority"]["authorizes_action"] is False and item["authority"]["executes_action"] is False, item)
    require(before == source_snapshot(), "runtime cognition mutated source")


TESTS = [(name.removeprefix("test_"), function) for name, function in list(globals().items()) if name.startswith("test_")]


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
        "suite": "v1104.3-persistent-motivation-self-model-foundation",
        "ok": passed == len(TESTS),
        "passed": passed,
        "total": len(TESTS),
        "checks": checks,
    }
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
