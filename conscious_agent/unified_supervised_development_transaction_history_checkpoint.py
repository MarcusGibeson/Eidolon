from __future__ import annotations

"""Strictly read-only v1221.9 unified supervised-development history checkpoint."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from checkpoint_registry import inspect_checkpoint_registry
from unified_supervised_development_transaction_history import AUTHORITY_FLAGS, CONTRACT_VERSION as RETAINED_CONTRACT_VERSION, MAX_PAGE_SIZE, STAGE_SPECS, public_unified_supervised_development_transaction_history

CONTRACT_VERSION = "v1221.9"


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _tree_signature(root: Path) -> tuple[str, int]:
    rows = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        rows.append((path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()))
    return _digest(rows), len(rows)


def _synthetic_event(sequence: int, stage: str, status: str, decision: str = "") -> dict[str, Any]:
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
        "authority_consumed": stage in {"approval", "apply-authorization", "rollback-authorization"},
        "operator_decision": decision,
        "decision_state": "rollback_result_accepted" if decision == "accept-rollback-result" else "",
        "event_identity_digest": hashlib.sha256(f"identity-{sequence}".encode()).hexdigest(),
        "sequence": sequence,
    }
    row["transaction_event_digest"] = _digest(row)
    return row


def build_unified_supervised_development_transaction_history_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    runtime = Path(runtime_root) if runtime_root is not None else None
    runtime_existed = runtime.exists() if runtime is not None else False
    before, count = _tree_signature(source)
    checks: list[bool] = []
    check = lambda value: checks.append(bool(value))

    stages = ["campaign-event", "approval", "grounded-planning", "build-test", "automatic-diagnosis",
              "repair-execution", "apply-execution", "rollback-execution", "rollback-result-decision"]
    events = [
        _synthetic_event(index, stage, f"{stage}-recorded", "accept-rollback-result" if stage == "rollback-result-decision" else "")
        for index, stage in enumerate(stages, start=1)
    ]
    source_set_digest = _digest([
        {"stage": event["stage"], "canonical_record_digest": event["canonical_record_digest"]}
        for event in events
    ])
    binding = {
        "contract_version": RETAINED_CONTRACT_VERSION,
        "proposal_id": "devc_0123456789abcdef01234567",
        "proposal_revision": 1,
        "generation": 1,
        "previous_history_digest": "",
        "source_set_digest": source_set_digest,
        "event_count": len(events),
        "current_state": "rollback_result_accepted",
        "terminal": True,
    }
    record = {
        "ok": True,
        "status": "unified_supervised_development_transaction_history_ready",
        **binding,
        "history_digest": _digest(binding),
        "events": events,
        "coverage": {
            "observed_stages": stages,
            "observed_stage_count": len(stages),
            "first_observed_stage": stages[0],
            "last_observed_stage": stages[-1],
            "missing_intermediate_stages": [],
            "gap_count": 0,
        },
        "stage_count": len(stages),
        "gap_count": 0,
        "history_is_derivative": True,
        "authoritative_receipts_preserved": True,
        "read_only_inspection": True,
        "runtime_records_external": True,
        "provider_contacted": False,
        "tests_executed": False,
        "repair_executed": False,
        "apply_executed": False,
        "rollback_executed": False,
        "project_modified": False,
        "selected_project_modified": False,
        "source_modified": False,
        **AUTHORITY_FLAGS,
    }
    public = public_unified_supervised_development_transaction_history(record, page=1, page_size=5)
    check(public.get("ok") is True)
    check(public.get("content_free") is True)
    check(public.get("event_count") == len(events))
    check(public.get("page_event_count") == 5)
    check(public.get("has_next_page") is True)
    check(public.get("current_state") == "rollback_result_accepted")
    check(public.get("terminal") is True)
    check(public.get("history_is_derivative") is True)
    check(public.get("authoritative_receipts_preserved") is True)
    for event in public.get("events") or []:
        check(len(event.get("artifact_digest") or "") == 64)
        check(len(event.get("canonical_record_digest") or "") == 64)
        check(len(event.get("transaction_event_digest") or "") == 64)
        check("path" not in json.dumps(event).lower())
    for key in (
        "private_request_exposed", "private_path_exposed", "private_content_exposed",
        "raw_provider_output_exposed", "raw_test_output_exposed", "rollback_content_exposed",
    ):
        check(public.get(key) is False)
    for key in AUTHORITY_FLAGS:
        check(public.get(key) is False)
    for key in (
        "provider_contacted", "tests_executed", "repair_executed", "apply_executed",
        "rollback_executed", "project_modified", "source_modified",
    ):
        check(public.get(key) is False)

    ordinary = (source / "conscious_agent" / "ordinary_chat_development_campaign.py").read_text(encoding="utf-8")
    module = (source / "conscious_agent" / "unified_supervised_development_transaction_history.py").read_text(encoding="utf-8")
    check("process_unified_supervised_development_transaction_history_control" in ordinary)
    check("attach_unified_supervised_development_transaction_history" in ordinary)
    check("LocalModelClient" not in module)
    check("MAX_PAGE_SIZE = 50" in module)
    check(len(STAGE_SPECS) >= 20)
    check(RETAINED_CONTRACT_VERSION == "v1221.8")

    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == "unified-supervised-development-transaction-history-checkpoint"), None)
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
            "stage_spec_count": len(STAGE_SPECS),
            "synthetic_event_count": len(events),
            "maximum_page_size": MAX_PAGE_SIZE,
            "history_is_derivative": True,
            "authoritative_receipts_preserved": True,
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
            "The checkpoint evaluates synthetic content-free history and reads no runtime records.",
            "A transaction history is a derivative index; original receipts remain authoritative.",
            "History inspection cannot contact providers, run tests, repair, apply, roll back, install, promote, release, or grant authority.",
        ],
    }
    report["structural_digest"] = _digest({key: value for key, value in report.items() if key != "structural_digest"})
    return report
