from __future__ import annotations

"""v1203.3-v1203.5 Python CLI checkpoint with project-owned tests."""

from pathlib import Path
from typing import Any, Callable, Mapping

from ordinary_chat_development_campaign import _atomic_json, _digest, _proposal_lock, _read_json, _store_root
from python_cli_implementation_foundations import run_or_resume_python_cli_implementation
from project_owned_python_tests import execute_or_resume_project_python_tests

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1203.5"


def _path(proposal_id: str, revision: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "python_cli_test_checkpoints" / proposal_id / f"revision-{int(revision)}.json"


def _valid(record: Mapping[str, Any]) -> bool:
    supplied = str(record.get("checkpoint_digest") or "")
    return bool(supplied and supplied == _digest({k: v for k, v in record.items() if k != "checkpoint_digest"}))


def run_or_resume_python_cli_with_tests(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_revision_digest: str,
    runtime_root=None,
    provider_generate: Callable[[str], str] | None = None,
    python_executable: str | None = None,
) -> dict[str, Any]:
    base = run_or_resume_python_cli_implementation(
        proposal_id,
        expected_revision=expected_revision,
        expected_revision_digest=expected_revision_digest,
        runtime_root=runtime_root,
        provider_generate=provider_generate,
        python_executable=python_executable,
    )
    if not base.get("checkpoint_digest"):
        return {**base, "failed_stage": base.get("failed_stage", "implementation")}
    tests = execute_or_resume_project_python_tests(
        proposal_id,
        expected_revision=expected_revision,
        expected_revision_digest=expected_revision_digest,
        expected_workspace_digest=str(base.get("workspace_digest") or ""),
        runtime_root=runtime_root,
        python_executable=python_executable,
    )
    if not tests.get("test_execution_digest") or tests.get("passed") is not True:
        return {
            "ok": False,
            "status": tests.get("status", "project_tests_failed"),
            "failed_stage": "project_tests",
            "test_execution_digest": tests.get("test_execution_digest", ""),
            "repair_authorized": False,
            "apply_authorized": False,
        }

    with _proposal_lock(proposal_id, runtime_root):
        path = _path(proposal_id, expected_revision, runtime_root)
        existing = _read_json(path)
        if existing:
            bindings_ok = existing.get("proposal_revision_digest") == expected_revision_digest and existing.get("project_test_execution_digest") == tests.get("test_execution_digest")
            return ({**existing, "operation_status": "resumed"} if bindings_ok and _valid(existing) else {"ok": False, "status": "python_cli_test_checkpoint_invalid"})

        stages = list(base.get("stage_receipts") or [])
        row = {
            "sequence": 7,
            "stage": "project_tests",
            "status": "project_owned_python_tests_passed",
            "passed": True,
            "artifact_digest": tests.get("test_execution_digest"),
        }
        row["stage_receipt_digest"] = _digest(row)
        stages.append(row)
        record = {k: v for k, v in base.items() if k not in {"checkpoint_digest", "operation_status", "stage_receipts", "stage_count", "stage_lineage_digest", "status", "contract_version"}}
        record.update({
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "ok": True,
            "status": "python_cli_tests_ready_for_operator_review",
            "stage_receipts": stages,
            "stage_count": 7,
            "stage_lineage_digest": _digest(stages),
            "project_test_execution_digest": tests.get("test_execution_digest"),
            "project_test_summary": {
                "passed": True,
                "test_file_count": int(tests.get("test_file_count") or 0),
                "command_count": int(tests.get("command_count") or 0),
                "passed_result_count": sum(1 for row in tests.get("results") or [] if row.get("passed")),
            },
            "operator_review_required": True,
            "repair_authorized": False,
            "apply_authorized": False,
            "release_authorized": False,
            "authority_granted": False,
        })
        record["checkpoint_digest"] = _digest(record)
        _atomic_json(path, record)
        return {**record, "operation_status": "created"}


def load_python_cli_test_checkpoint(proposal_id: str, revision: int, runtime_root=None) -> dict[str, Any]:
    record = _read_json(_path(proposal_id, revision, runtime_root))
    return record if record and _valid(record) else {}


def public_python_cli_test_checkpoint(record: Mapping[str, Any]) -> dict[str, Any]:
    if not record:
        return {}
    return {
        "ok": bool(record.get("ok")),
        "status": str(record.get("status") or ""),
        "proposal_id": str(record.get("proposal_id") or ""),
        "proposal_revision": int(record.get("proposal_revision") or 0),
        "checkpoint_digest": str(record.get("checkpoint_digest") or ""),
        "stage_count": int(record.get("stage_count") or 0),
        "stage_lineage_digest": str(record.get("stage_lineage_digest") or ""),
        "stage_receipts": list(record.get("stage_receipts") or []),
        "change_summary": dict(record.get("change_summary") or {}),
        "test_summary": dict(record.get("test_summary") or {}),
        "project_test_summary": dict(record.get("project_test_summary") or {}),
        "working_result_available": True,
        "operator_review_required": True,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "raw_output_exposed": False,
        "selected_project_modified": False,
        "source_modified": False,
        "implementation_applied": False,
        "dependencies_installed": False,
        "network_allowed": False,
        "repair_authorized": False,
        "apply_authorized": False,
        "release_authorized": False,
        "authority_granted": False,
    }
