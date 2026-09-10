from __future__ import annotations

"""Strictly read-only v1222.9 transaction-resumption checkpoint."""

import hashlib
import json
from pathlib import Path
from typing import Any

from checkpoint_registry import inspect_checkpoint_registry
from transaction_resumption_abandoned_work_reconciliation import ASSESSMENT_CLASSES, AUTHORITY_FLAGS, CONTRACT_VERSION as RETAINED_CONTRACT_VERSION, RESUMPTION_DECISIONS, classify_transaction_history, public_transaction_resumption

CONTRACT_VERSION = "v1222.9"


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _tree_signature(root: Path) -> tuple[str, int]:
    rows = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        rows.append((path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()))
    return _digest(rows), len(rows)


def _event(sequence: int, stage: str, status: str, *, consumed: bool = False, decision: str = "") -> dict[str, Any]:
    row = {
        "stage": stage,
        "stage_rank": sequence - 1,
        "source_index": 1,
        "status_field": "status",
        "status": status,
        "recorded_at": "",
        "artifact_digest_field": "synthetic_digest",
        "artifact_digest": hashlib.sha256(f"artifact-{sequence}".encode()).hexdigest(),
        "canonical_record_digest": hashlib.sha256(f"record-{sequence}".encode()).hexdigest(),
        "counts": {},
        "authority_consumed": consumed,
        "operator_decision": decision,
        "decision_state": "",
        "event_identity_digest": hashlib.sha256(f"identity-{sequence}".encode()).hexdigest(),
        "sequence": sequence,
    }
    row["transaction_event_digest"] = _digest(row)
    return row


def _history(events: list[dict[str, Any]], *, gaps: int = 0, terminal: bool = False) -> dict[str, Any]:
    return {
        "ok": True,
        "proposal_id": "devc_0123456789abcdef01234567",
        "proposal_revision": 1,
        "generation": 1,
        "history_digest": hashlib.sha256(b"history").hexdigest(),
        "source_set_digest": hashlib.sha256(b"sources").hexdigest(),
        "events": events,
        "event_count": len(events),
        "stage_count": len({row["stage"] for row in events}),
        "gap_count": gaps,
        "terminal": terminal,
        "current_state": str(events[-1].get("status") if events else ""),
    }


def build_transaction_resumption_abandoned_work_reconciliation_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    runtime = Path(runtime_root) if runtime_root is not None else None
    runtime_existed = runtime.exists() if runtime is not None else False
    before, count = _tree_signature(source)
    checks: list[bool] = []
    check = lambda value: checks.append(bool(value))

    safe = classify_transaction_history(_history([
        _event(1, "campaign-event", "proposal_recorded"),
        _event(2, "grounded-planning", "grounded_plan_ready"),
    ]))
    check(safe["classification"] == "safely_resumable")
    check("resume-planning" in safe["eligible_decisions"])
    check(safe["unfinished_work_detected"] is True)

    restart = classify_transaction_history(_history([
        _event(1, "campaign-event", "proposal_recorded"),
        _event(2, "approval", "interrupted", consumed=True),
    ]))
    check(restart["classification"] == "restart_required")
    check("begin-fresh-attempt" in restart["eligible_decisions"])
    check(restart["consumed_authority_event_count"] == 1)

    review = classify_transaction_history(_history([
        _event(1, "campaign-event", "proposal_recorded"),
        _event(2, "build-test-review", "review_required"),
    ]))
    check(review["classification"] == "review_required")
    check("defer" in review["eligible_decisions"])

    inconsistent = classify_transaction_history(_history([
        _event(1, "campaign-event", "proposal_recorded"),
        _event(2, "repair-execution", "recorded"),
    ], gaps=2))
    check(inconsistent["classification"] == "review_required")
    check(inconsistent["inconsistency_detected"] is True)
    check("investigate-inconsistency" in inconsistent["eligible_decisions"])

    closed = classify_transaction_history(_history([
        _event(1, "campaign-event", "proposal_recorded"),
        _event(2, "rollback-result-decision", "recorded", decision="accept-rollback-result"),
    ], terminal=True))
    check(closed["classification"] == "permanently_closed")
    check(closed["eligible_decisions"] == [])
    check(closed["unfinished_work_detected"] is False)

    assessment = {
        "ok": True,
        "status": "transaction_resumption_assessment_ready",
        "schema_version": "1",
        "contract_version": RETAINED_CONTRACT_VERSION,
        "proposal_id": "devc_0123456789abcdef01234567",
        "proposal_revision": 1,
        "assessment_generation": 1,
        "history_generation": 1,
        "history_digest": hashlib.sha256(b"history").hexdigest(),
        "history_source_set_digest": hashlib.sha256(b"sources").hexdigest(),
        "classification": safe["classification"],
        "last_trustworthy_stage": safe["last_trustworthy_stage"],
        "safe_resumption_boundary": safe["safe_resumption_boundary"],
        "reason_codes": safe["reason_codes"],
        "eligible_decisions": safe["eligible_decisions"],
        "assessment_digest": hashlib.sha256(b"assessment").hexdigest(),
        "decision_phrases": [],
        "history_event_count": 2,
        "history_stage_count": 2,
        "history_gap_count": 0,
        "history_current_state": "grounded_plan_ready",
        "history_terminal": False,
        "consumed_authority_event_count": 0,
        "inconsistency_detected": False,
        "unfinished_work_detected": True,
        "content_free": True,
        "operator_review_required": True,
        "runtime_records_external": True,
        "history_is_derivative": True,
        "authoritative_receipts_preserved": True,
        "old_authority_reuse_forbidden": True,
        "new_approval_required_before_continuation": True,
        "provider_contacted": False,
        "tests_executed": False,
        "continuation_executed": False,
        "repair_executed": False,
        "apply_executed": False,
        "rollback_executed": False,
        "project_modified": False,
        "selected_project_modified": False,
        "source_modified": False,
        **AUTHORITY_FLAGS,
    }
    public = public_transaction_resumption(assessment)
    check(public.get("ok") is True)
    check(public.get("content_free") is True)
    check(public.get("classification") == "safely_resumable")
    check(public.get("old_authority_reuse_forbidden") is True)
    check(public.get("new_approval_required_before_continuation") is True)
    for key in AUTHORITY_FLAGS:
        check(public.get(key) is False)
    for key in (
        "provider_contacted", "tests_executed", "continuation_executed", "repair_executed",
        "apply_executed", "rollback_executed", "project_modified", "source_modified",
        "private_request_exposed", "private_path_exposed", "private_content_exposed",
        "raw_provider_output_exposed", "raw_test_output_exposed",
    ):
        check(public.get(key) is False)

    ordinary = (source / "conscious_agent" / "ordinary_chat_development_campaign.py").read_text(encoding="utf-8")
    module = (source / "conscious_agent" / "transaction_resumption_abandoned_work_reconciliation.py").read_text(encoding="utf-8")
    check("process_transaction_resumption_control" in ordinary)
    check("LocalModelClient" not in module)
    check("old_authority_reuse_forbidden" in module)
    check("new_approval_required_before_continuation" in module)
    check(set(ASSESSMENT_CLASSES) == {"safely_resumable", "restart_required", "review_required", "permanently_closed"})
    check(len(RESUMPTION_DECISIONS) == 5)
    check(RETAINED_CONTRACT_VERSION == "v1222.8")

    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == "transaction-resumption-abandoned-work-reconciliation-checkpoint"), None)
    check(descriptor is not None)
    check((descriptor or {}).get("contract_version") == CONTRACT_VERSION)
    check((descriptor or {}).get("read_only") is True)
    check((descriptor or {}).get("post_available") is False)

    after, after_count = _tree_signature(source)
    check(before == after and count == after_count)
    check(runtime is None or runtime.exists() == runtime_existed)

    report = {
        "ok": all(checks),
        "contract_version": CONTRACT_VERSION,
        "retained_contract_version": RETAINED_CONTRACT_VERSION,
        "passed": sum(checks),
        "total": len(checks),
        "summary": {
            "assessment_class_count": len(ASSESSMENT_CLASSES),
            "operator_decision_count": len(RESUMPTION_DECISIONS),
            "old_authority_reuse_forbidden": True,
            "new_approval_required_before_continuation": True,
            "checkpoint_project_modified": False,
        },
        "read_only": True,
        "post_available": False,
        "synthetic_contract_evaluation": True,
        "runtime_data_read": False,
        "runtime_mutated": False,
        "source_modified": False,
        "provider_contacted": False,
        "project_tests_executed": False,
        "continuation_executed": False,
        "repair_executed": False,
        "apply_executed": False,
        "rollback_executed": False,
        "project_modified": False,
        "dependencies_installed": False,
        "release_authorized": False,
        "authority_granted": False,
        "global_profile_pass_claimed": False,
        "source_signature_before": before,
        "source_signature_after": after,
        "source_file_count": count,
        "limitations": [
            "The checkpoint evaluates synthetic content-free histories and reads no runtime records.",
            "Resumption assessments are derivative; original receipts remain authoritative.",
            "A continuation proposal requires fresh approval and cannot execute continuation work.",
        ],
    }
    report["structural_digest"] = _digest({key: value for key, value in report.items() if key != "structural_digest"})
    return report
