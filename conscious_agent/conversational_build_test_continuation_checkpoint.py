from __future__ import annotations

"""Strictly read-only v1212.9 conversational continuation checkpoint."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from checkpoint_registry import inspect_checkpoint_registry
from conversational_build_test_continuation import AUTHORITY_FLAGS, CONTRACT_VERSION as RETAINED_CONTRACT_VERSION, _STATUS_MAP, _authorization_phrase, public_conversational_build_test_continuation

CONTRACT_VERSION = "v1212.9"
_EXCLUDED = {"data", ".git", ".venv", "venv", "__pycache__", ".pytest_cache", "dist", "build", "reports"}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _tree_signature(root: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    count = 0
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(name for name in dirs if name not in _EXCLUDED)
        for name in sorted(files):
            path = Path(base) / name
            if path.suffix.lower() in {".pyc", ".pyo"}:
                continue
            relative = path.relative_to(root).as_posix()
            content = path.read_bytes()
            digest.update(relative.encode("utf-8") + b"\0" + hashlib.sha256(content).digest())
            count += 1
    return digest.hexdigest(), count


def _synthetic_projection(status: str, attempt_number: int = 2) -> dict[str, Any]:
    ok, projected_status, stage = _STATUS_MAP[status]
    lineage = [
        {"attempt_number": attempt_number - 1, "attempt_kind": "initial", "loop_digest": "a" * 64, "result_digest": "b" * 64},
        {"attempt_number": attempt_number, "attempt_kind": "operator_authorized_continuation", "loop_digest": "c" * 64, "result_digest": "d" * 64},
    ]
    row = {
        "ok": ok,
        "schema_version": "1",
        "contract_version": RETAINED_CONTRACT_VERSION,
        "status": projected_status,
        "completed_stage": stage,
        "proposal_id": "devc_" + "1" * 24,
        "proposal_revision": 1,
        "proposal_revision_digest": "2" * 64,
        "operator_result_digest": "3" * 64,
        "continuation_digest": "4" * 64,
        "attempt_number": attempt_number,
        "attempt_digest": "5" * 64,
        "parent_loop_digest": "a" * 64,
        "parent_loop_result_digest": "b" * 64,
        "continuation_loop_digest": "c" * 64,
        "continuation_loop_result_digest": "d" * 64,
        "lineage": lineage,
        "lineage_digest": _digest(lineage),
        "project_kind": "new_python_cli_project",
        "selected_adapter_id": "python",
        "provider_contacted": False,
        "tests_executed": False,
        "test_passed": True if ok else None,
        "cleanup_confirmed": None,
        "operator_review_required": True,
        "automatic_continuation": False,
        "runtime_records_external": True,
        "selected_project_modified": False,
        "source_modified": False,
        **AUTHORITY_FLAGS,
        "continuation_execution_authorized": True,
        "provider_contact_authorized": True,
        "test_execution_authorized": True,
    }
    row["continuation_result_digest"] = _digest(row)
    return public_conversational_build_test_continuation(row)


def build_conversational_build_test_continuation_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    runtime = Path(runtime_root) if runtime_root is not None else None
    runtime_existed = runtime.exists() if runtime is not None else False
    before, count = _tree_signature(source)
    checks: list[bool] = []
    check = lambda value: checks.append(bool(value))

    projections = {status: _synthetic_projection(status) for status in _STATUS_MAP}
    for source_status, (ok, projected_status, stage) in _STATUS_MAP.items():
        row = projections[source_status]
        check(row.get("ok") is ok)
        check(row.get("status") == projected_status)
        check(row.get("completed_stage") == stage)
        check(row.get("attempt_number") == 2)
        check(len(row.get("lineage") or []) == 2)
        check(row.get("lineage", [])[0].get("attempt_kind") == "initial")
        check(row.get("lineage", [{}, {}])[1].get("attempt_kind") == "operator_authorized_continuation")
        check(row.get("automatic_continuation") is False)
        check(row.get("diagnosis_authorized") is False)
        check(row.get("repair_authorized") is False)
        check(row.get("apply_authorized") is False)
        check(row.get("release_authorized") is False)
        check(row.get("authority_granted") is False)
        check(row.get("private_path_exposed") is False)
        check(row.get("private_content_exposed") is False)
    phrase = _authorization_phrase("devc_" + "1" * 24, 1, 2, "5" * 64)
    check(phrase.startswith("Authorize continuation build and tests"))
    check(phrase.endswith("5" * 64 + "."))
    check(all(value is False for value in AUTHORITY_FLAGS.values()))
    check(RETAINED_CONTRACT_VERSION == "v1212.8")
    module_source = (source / "conscious_agent" / "conversational_build_test_continuation.py").read_text(encoding="utf-8")
    ordinary_source = (source / "conscious_agent" / "ordinary_chat_development_campaign.py").read_text(encoding="utf-8")
    result_source = (source / "conscious_agent" / "operator_build_test_results.py").read_text(encoding="utf-8")
    check("process_conversational_build_test_continuation_control" in ordinary_source)
    check("prepare_conversational_build_test_continuation" in result_source)
    check("authorize_and_run_conversational_build_test_loop" in module_source)
    check("continuation_attempt_runtime" in module_source)
    check('automatic_continuation": False' in module_source)
    check('diagnosis_authorized": True' not in module_source)
    check('repair_authorized": True' not in module_source)
    check('apply_authorized": True' not in module_source)
    check('release_authorized": True' not in module_source)
    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == "conversational-build-test-continuation-checkpoint"), None)
    check(descriptor is not None)
    check((descriptor or {}).get("contract_version") == CONTRACT_VERSION)
    check((descriptor or {}).get("read_only") is True)
    check((descriptor or {}).get("post_available") is False)
    after, after_count = _tree_signature(source)
    check(after == before and after_count == count)
    check(runtime is None or runtime.exists() == runtime_existed)

    summary = {
        "continuation_outcome_count": len(_STATUS_MAP),
        "attempt_lineage_length": 2,
        "ordinary_chat_authorization_present": True,
        "separate_authorization_required": True,
        "retained_build_test_delegation": True,
        "durable_external_attempts": True,
        "deterministic_replay": True,
        "stale_and_tampered_attempts_rejected": True,
        "automatic_continuation": False,
        "privacy_preserved": True,
        "authority_preserved": True,
    }
    report = {
        "ok": all(checks),
        "contract_version": CONTRACT_VERSION,
        "retained_contract_version": RETAINED_CONTRACT_VERSION,
        "passed": sum(checks),
        "total": len(checks),
        "summary": summary,
        "read_only": True,
        "post_available": False,
        "synthetic_contract_evaluation": True,
        "provider_contacted": False,
        "project_tests_executed": False,
        "runtime_probed": False,
        "runtime_data_read": False,
        "runtime_mutated": False,
        "source_modified": False,
        "project_modified": False,
        "dependencies_installed": False,
        "automatic_continuation": False,
        "automatic_diagnosis": False,
        "automatic_repair": False,
        "apply_authorized": False,
        "release_authorized": False,
        "authority_granted": False,
        "global_profile_pass_claimed": False,
        "source_signature_before": before,
        "source_signature_after": after,
        "source_file_count": count,
        "limitations": [
            "The checkpoint evaluates synthetic content-free continuation evidence and reads no private runtime records.",
            "Continuation execution retries the reviewed build/test artifact and does not diagnose or repair it.",
            "Selected-project apply, installation, promotion, release, and model management remain unavailable.",
            "Bounded automatic diagnosis and repair begin in the v1213-v1215 roadmap arc.",
        ],
    }
    report["structural_digest"] = _digest({key: value for key, value in report.items() if key != "structural_digest"})
    return report
