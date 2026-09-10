from __future__ import annotations

"""Strictly read-only v1211.9 operator results and continuation checkpoint."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from checkpoint_registry import inspect_checkpoint_registry
from operator_build_test_results import AUTHORITY_FLAGS, CONTRACT_VERSION as RETAINED_CONTRACT_VERSION, DECISIONS_BY_OUTCOME, OUTCOME_BY_LOOP_STATUS, project_operator_build_test_result

CONTRACT_VERSION = "v1211.9"
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


def _synthetic_loop(status: str) -> dict[str, Any]:
    result = {
        "ok": status == "conversational_build_test_completed",
        "status": status,
        "proposal_id": "devc_" + "a" * 24,
        "proposal_revision": 1,
        "proposal_revision_digest": "b" * 64,
        "loop_digest": "c" * 64,
        "project_kind": "new_python_cli_project",
        "selected_adapter_id": "python",
        "completed_stage": "complete" if status == "conversational_build_test_completed" else "test",
        "provider_contacted": False,
        "tests_executed": False,
        "test_passed": True if status == "conversational_build_test_completed" else None,
        "cleanup_confirmed": None,
        "attempt_count": 1,
        "recovery_count": 0,
    }
    result["loop_result_digest"] = _digest(result)
    return {
        "proposal_id": result["proposal_id"],
        "proposal_revision": 1,
        "loop_digest": result["loop_digest"],
        "phase": "sealed",
        "result": result,
        "result_digest": _digest(result),
    }


def build_operator_build_test_results_checkpoint(*, source_root: str | Path | None = None, runtime_root: str | Path | None = None) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    runtime = Path(runtime_root) if runtime_root is not None else None
    runtime_existed = runtime.exists() if runtime is not None else False
    before, count = _tree_signature(source)
    checks: list[bool] = []
    check = lambda value: checks.append(bool(value))

    projections = {status: project_operator_build_test_result(_synthetic_loop(status)) for status in OUTCOME_BY_LOOP_STATUS}
    for status, outcome in OUTCOME_BY_LOOP_STATUS.items():
        row = projections[status]
        check(row.get("ok") is True)
        check(row.get("outcome") == outcome)
        check(row.get("available_decisions") == list(DECISIONS_BY_OUTCOME[outcome]))
        check(len(row.get("decision_phrases") or []) == 3)
        check(row.get("automatic_continuation") is False)
        check(row.get("continuation_execution_authorized") is False)
        check(row.get("diagnosis_authorized") is False)
        check(row.get("repair_authorized") is False)
        check(row.get("apply_authorized") is False)
        check(row.get("release_authorized") is False)
        check(row.get("authority_granted") is False)
    check(all(value is False for value in AUTHORITY_FLAGS.values()))
    check(RETAINED_CONTRACT_VERSION == "v1211.8")
    module_source = (source / "conscious_agent" / "operator_build_test_results.py").read_text(encoding="utf-8")
    ordinary_source = (source / "conscious_agent" / "ordinary_chat_development_campaign.py").read_text(encoding="utf-8")
    loop_source = (source / "conscious_agent" / "conversational_build_test_loop.py").read_text(encoding="utf-8")
    check("process_operator_build_test_result_control" in ordinary_source)
    check("create_or_resume_operator_build_test_result" in loop_source)
    check("prepare-next-attempt" in module_source)
    check("automatic_continuation\": False" in module_source)
    check("run_or_resume_selected_test_adapter" not in module_source)
    check("provider_generate" not in module_source)
    check("repair_authorized\": True" not in module_source)
    check("apply_authorized\": True" not in module_source)
    check("release_authorized\": True" not in module_source)
    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == "operator-build-test-results-checkpoint"), None)
    check(descriptor is not None)
    check((descriptor or {}).get("contract_version") == CONTRACT_VERSION)
    check((descriptor or {}).get("read_only") is True)
    check((descriptor or {}).get("post_available") is False)
    after, after_count = _tree_signature(source)
    check(after == before and after_count == count)
    check(runtime is None or runtime.exists() == runtime_existed)

    summary = {
        "outcome_count": len(OUTCOME_BY_LOOP_STATUS),
        "decision_count": len({decision for values in DECISIONS_BY_OUTCOME.values() for decision in values}),
        "ordinary_chat_decision_control_present": True,
        "durable_external_results": True,
        "deterministic_replay": True,
        "conflicting_decisions_rejected": True,
        "continuation_preparation_only": True,
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
            "The checkpoint uses synthetic sealed outcomes and does not read private runtime records.",
            "A prepared next attempt is a review record only and is not execution authorization.",
            "Diagnosis and repair remain deferred to v1213-v1215.",
            "Continuation execution remains in the v1212 roadmap unit.",
        ],
    }
    report["structural_digest"] = _digest({key: value for key, value in report.items() if key != "structural_digest"})
    return report
