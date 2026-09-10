from __future__ import annotations

"""Strictly read-only v1223.9 unified work-queue checkpoint."""

import hashlib
import json
from pathlib import Path
from typing import Any

from checkpoint_registry import inspect_checkpoint_registry
from unified_development_work_queue import AUTHORITY_FLAGS, CONTRACT_VERSION as RETAINED_CONTRACT_VERSION, QUEUE_ITEM_ACTIONS, QUEUE_STATES, classify_work_item_state, public_unified_development_work_queue

CONTRACT_VERSION = "v1223.9"


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _tree_signature(root: Path) -> tuple[str, int]:
    rows = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        rows.append((path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()))
    return _digest(rows), len(rows)


def _proposal(state: str = "approved_pending_grounded_specification", consumed: bool = True) -> dict[str, Any]:
    return {"lifecycle_state": state, "approval_consumed": consumed, "approval_required": True}


def _history(stage: str, status: str = "recorded", terminal: bool = False) -> dict[str, Any]:
    return {
        "events": [{"stage": stage, "status": status}],
        "last_observed_stage": stage,
        "current_state": status,
        "terminal": terminal,
    }


def _assessment(classification: str, stage: str, *, inconsistent: bool = False) -> dict[str, Any]:
    return {
        "classification": classification,
        "last_trustworthy_stage": stage,
        "inconsistency_detected": inconsistent,
    }


def build_unified_development_work_queue_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    runtime = Path(runtime_root) if runtime_root is not None else None
    runtime_existed = runtime.exists() if runtime is not None else False
    before, count = _tree_signature(source)
    checks: list[bool] = []
    check = lambda value: checks.append(bool(value))

    resumable = classify_work_item_state(
        _proposal(), _history("grounded-planning", "grounded_plan_ready"),
        _assessment("safely_resumable", "grounded-planning"),
    )
    check(resumable["state"] == "resumable")
    check(resumable["fresh_authority_required"] is True)
    check(resumable["old_authority_reusable"] is False)

    awaiting = classify_work_item_state(
        _proposal("awaiting_approval", False), _history("campaign-event", "proposal_created"),
        _assessment("safely_resumable", "campaign-event"),
    )
    check(awaiting["state"] == "awaiting_approval")
    check(awaiting["pending_operator_decision"] == "proposal_approval")

    blocked = classify_work_item_state(
        _proposal(), _history("approval", "interrupted"),
        _assessment("restart_required", "approval"),
    )
    check(blocked["state"] == "blocked")
    check(blocked["safe_next_step"] == "review_and_begin_fresh_attempt")

    deferred = classify_work_item_state(
        _proposal(), _history("build-test-review"),
        _assessment("review_required", "build-test-review"),
        {"decision": "defer"},
    )
    check(deferred["state"] == "deferred")

    abandoned = classify_work_item_state(
        _proposal(), _history("build-test-review"),
        _assessment("review_required", "build-test-review"),
        {"decision": "close-as-abandoned"},
    )
    check(abandoned["state"] == "abandoned")

    closed = classify_work_item_state(
        _proposal(), _history("rollback-result-decision", terminal=True),
        _assessment("permanently_closed", "rollback-result-decision"),
    )
    check(closed["state"] == "closed")
    check(closed["fresh_authority_required"] is False)

    reopened = classify_work_item_state(
        _proposal(), _history("build-test-review"),
        _assessment("review_required", "build-test-review"),
        {"decision": "defer"}, {"action": "propose-reopen"},
    )
    check(reopened["state"] == "awaiting_approval")
    check(reopened["pending_operator_decision"] == "fresh_reopen_approval")

    synthetic_item = {
        "queue_item_id": "work_0123456789abcdef01234567",
        "proposal_id": "devc_0123456789abcdef01234567",
        "proposal_revision": 1,
        "project_identity_digest": hashlib.sha256(b"project").hexdigest(),
        "project_reference": "project_0123456789abcd",
        "state": "resumable",
        "pending_operator_decision": "resumption_disposition",
        "safe_next_step": "review_and_prepare_fresh_continuation",
        "current_stage": "grounded-planning",
        "resumption_classification": "safely_resumable",
        "fresh_authority_required": True,
        "old_authority_reusable": False,
        "history_generation": 1,
        "history_digest": hashlib.sha256(b"history").hexdigest(),
        "assessment_generation": 1,
        "assessment_digest": hashlib.sha256(b"assessment").hexdigest(),
        "history_event_count": 2,
        "history_gap_count": 0,
        "approval_required": True,
        "approval_consumed": True,
        "duplicate_active_conflict": False,
        "underlying_state": "resumable",
        "queue_item_digest": hashlib.sha256(b"item").hexdigest(),
        "control_generation": 0,
        "control_action": "",
        "focus_phrase": "Focus development work item work_0123456789abcdef01234567 queue " + hashlib.sha256(b"queue").hexdigest() + ".",
        "defer_phrase": "",
        "close_phrase": "",
        "reopen_phrase": "",
    }
    synthetic_project = {
        "project_identity_digest": synthetic_item["project_identity_digest"],
        "project_reference": synthetic_item["project_reference"],
        "work_item_count": 1,
        "open_work_item_count": 1,
        "current_queue_item_id": synthetic_item["queue_item_id"],
        "current_proposal_id": synthetic_item["proposal_id"],
        "current_proposal_revision": 1,
        "project_state": "resumable",
        "pending_operator_decision": "resumption_disposition",
        "safe_next_step": "review_and_prepare_fresh_continuation",
        "duplicate_active_conflict": False,
        "project_state_digest": hashlib.sha256(b"project-state").hexdigest(),
    }
    synthetic = {
        "ok": True,
        "status": "unified_development_work_queue_ready",
        "generation": 1,
        "queue_digest": hashlib.sha256(b"queue").hexdigest(),
        "item_count": 1,
        "project_count": 1,
        "state_counts": {state: int(state == "resumable") for state in QUEUE_STATES},
        "focus_item_id": "",
        "items": [synthetic_item],
        "projects": [synthetic_project],
    }
    public = public_unified_development_work_queue(synthetic)
    check(public["ok"] is True)
    check(public["item_count"] == 1)
    check(public["projects"][0]["project_state"] == "resumable")
    check(public["content_free"] is True)
    for key in AUTHORITY_FLAGS:
        check(public.get(key) is False)
    for key in (
        "provider_contacted", "tests_executed", "continuation_executed", "repair_executed",
        "apply_executed", "rollback_executed", "project_modified", "source_modified",
        "private_request_exposed", "private_path_exposed", "private_content_exposed",
        "project_name_exposed", "raw_provider_output_exposed", "raw_test_output_exposed",
    ):
        check(public.get(key) is False)

    module = (source / "conscious_agent" / "unified_development_work_queue.py").read_text(encoding="utf-8")
    ordinary = (source / "conscious_agent" / "ordinary_chat_development_campaign.py").read_text(encoding="utf-8")
    check("process_unified_development_work_queue_control" in ordinary)
    check("LocalModelClient" not in module)
    check("old_authority_reuse_forbidden" in module)
    check("new_approval_required_before_continuation" in module)
    check(set(QUEUE_STATES) == {"active", "awaiting_approval", "resumable", "blocked", "deferred", "abandoned", "closed"})
    check(set(QUEUE_ITEM_ACTIONS) == {"focus", "defer", "close", "propose-reopen"})
    check(RETAINED_CONTRACT_VERSION == "v1223.8")

    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == "unified-development-work-queue-checkpoint"), None)
    check(descriptor is not None)
    check((descriptor or {}).get("contract_version") == CONTRACT_VERSION)
    check((descriptor or {}).get("read_only") is True)
    check((descriptor or {}).get("post_available") is False)

    after, after_count = _tree_signature(source)
    check(before == after and count == after_count)
    check(runtime is None or runtime.exists() is runtime_existed)

    return {
        "ok": all(checks),
        "status": "unified_development_work_queue_checkpoint_ready" if all(checks) else "unified_development_work_queue_checkpoint_failed",
        "contract_version": CONTRACT_VERSION,
        "read_only": True,
        "runtime_data_read": False,
        "source_modified": False,
        "project_modified": False,
        "authority_granted": False,
        "provider_contacted": False,
        "tests_executed": False,
        "passed": sum(checks),
        "total": len(checks),
        "source_signature_before": before,
        "source_signature_after": after,
        "source_file_count": count,
        "summary": {
            "queue_state_count": len(QUEUE_STATES),
            "queue_item_action_count": len(QUEUE_ITEM_ACTIONS),
            "maximum_queue_items": 500,
            "maximum_page_size": 50,
            "old_authority_reuse_forbidden": True,
            "new_approval_required_before_continuation": True,
            "project_identity_is_digest_only": True,
        },
        "checkpoint_digest": _digest({"checks": checks, "before": before, "count": count}),
    }
