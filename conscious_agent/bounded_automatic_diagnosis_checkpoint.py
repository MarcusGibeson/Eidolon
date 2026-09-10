from __future__ import annotations

"""Strictly read-only v1213.9 bounded automatic diagnosis checkpoint."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from bounded_automatic_diagnosis import AUTHORITY_FLAGS, CONTRACT_VERSION as RETAINED_CONTRACT_VERSION, DIAGNOSABLE_OUTCOMES, NON_DIAGNOSABLE_OUTCOMES, _diagnose_evidence, public_bounded_automatic_diagnosis
from checkpoint_registry import inspect_checkpoint_registry

CONTRACT_VERSION = "v1213.9"
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


def _synthetic_evidence(outcome: str) -> dict[str, Any]:
    row = {
        "proposal_id": "devc_" + "1" * 24,
        "proposal_revision": 1,
        "proposal_revision_digest": "2" * 64,
        "attempt_number": 2,
        "attempt_digest": "3" * 64,
        "continuation_result_digest": "4" * 64,
        "parent_loop_result_digest": "5" * 64,
        "continuation_loop_result_digest": "6" * 64,
        "lineage_digest": "7" * 64,
        "outcome_status": outcome,
        "completed_stage": "build" if "build_blocked" in outcome else ("internal" if "internal_error" in outcome else "test"),
        "project_kind": "new_python_cli_project",
        "selected_adapter_id": "python",
        "observed_provider_contacted": True,
        "observed_tests_executed": "tests_failed" in outcome,
        "observed_test_passed": False if "tests_failed" in outcome else None,
        "observed_cleanup_confirmed": True,
        "content_free": True,
        "raw_output_included": False,
        "private_path_included": False,
    }
    row["evidence_digest"] = _digest(row)
    return row


def _synthetic_projection(outcome: str) -> dict[str, Any]:
    evidence = _synthetic_evidence(outcome)
    candidates = _diagnose_evidence(evidence)
    row = {
        "ok": True,
        "schema_version": "1",
        "contract_version": RETAINED_CONTRACT_VERSION,
        "status": "bounded_automatic_diagnosis_completed",
        "proposal_id": evidence["proposal_id"],
        "proposal_revision": 1,
        "proposal_revision_digest": evidence["proposal_revision_digest"],
        "attempt_number": 2,
        "attempt_digest": evidence["attempt_digest"],
        "continuation_result_digest": evidence["continuation_result_digest"],
        "continuation_loop_result_digest": evidence["continuation_loop_result_digest"],
        "lineage_digest": evidence["lineage_digest"],
        "outcome_status": outcome,
        "evidence_digest": evidence["evidence_digest"],
        "diagnosis_digest": _digest({"outcome": outcome, "evidence_digest": evidence["evidence_digest"]}),
        "diagnosis_posture": "diagnosis_candidates_require_operator_review",
        "diagnosis_candidates": candidates,
        "diagnosis_count": len(candidates),
        "suggested_next_step": "operator_review_before_repair_proposal",
        "diagnosis_performed": True,
        "automatic_diagnosis": True,
        "diagnosis_authorized": True,
        "operator_authorized_diagnosis": False,
        "root_cause_proven": False,
        "operator_review_required": True,
        "provider_contacted": False,
        "tests_executed": False,
        "project_modified": False,
        "selected_project_modified": False,
        "source_modified": False,
        "patch_created": False,
        "repair_created": False,
        "runtime_records_external": True,
        **AUTHORITY_FLAGS,
        "diagnosis_authorized": True,
    }
    row["diagnosis_result_digest"] = _digest(row)
    return public_bounded_automatic_diagnosis(row)


def build_bounded_automatic_diagnosis_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    runtime = Path(runtime_root) if runtime_root is not None else None
    runtime_existed = runtime.exists() if runtime is not None else False
    before, count = _tree_signature(source)
    checks: list[bool] = []
    check = lambda value: checks.append(bool(value))

    projections = {status: _synthetic_projection(status) for status in DIAGNOSABLE_OUTCOMES}
    for status, template in DIAGNOSABLE_OUTCOMES.items():
        row = projections[status]
        check(row.get("ok") is True)
        check(row.get("status") == "bounded_automatic_diagnosis_completed")
        check(row.get("outcome_status") == status)
        check(row.get("diagnosis_count") == 1)
        check(row.get("diagnosis_candidates", [{}])[0].get("diagnosis_code") == template["diagnosis_code"])
        check(row.get("diagnosis_candidates", [{}])[0].get("confidence") == "high_observation_low_root_cause")
        check(len(row.get("diagnosis_candidates", [{}])[0].get("unknowns") or []) == 2)
        check(row.get("diagnosis_performed") is True)
        check(row.get("automatic_diagnosis") is True)
        check(row.get("diagnosis_authorized") is True)
        check(row.get("operator_authorized_diagnosis") is False)
        check(row.get("root_cause_proven") is False)
        check(row.get("operator_review_required") is True)
        check(row.get("provider_contacted") is False)
        check(row.get("tests_executed") is False)
        check(row.get("repair_authorized") is False)
        check(row.get("retest_authorized") is False)
        check(row.get("apply_authorized") is False)
        check(row.get("release_authorized") is False)
        check(row.get("authority_granted") is False)
        check(row.get("content_free") is True)
        check(row.get("private_path_exposed") is False)
        check(row.get("private_content_exposed") is False)

    check(len(NON_DIAGNOSABLE_OUTCOMES) == 1)
    check("conversational_build_test_continuation_completed" in NON_DIAGNOSABLE_OUTCOMES)
    check(RETAINED_CONTRACT_VERSION == "v1213.8")
    check(all(value is False for value in AUTHORITY_FLAGS.values()))
    module_source = (source / "conscious_agent" / "bounded_automatic_diagnosis.py").read_text(encoding="utf-8")
    ordinary_source = (source / "conscious_agent" / "ordinary_chat_development_campaign.py").read_text(encoding="utf-8")
    check("load_conversational_build_test_continuation" in module_source)
    check("attach_bounded_automatic_diagnosis" in ordinary_source)
    check("provider_generate" not in module_source)
    check("subprocess" not in module_source)
    check('repair_authorized": True' not in module_source)
    check('retest_authorized": True' not in module_source)
    check('apply_authorized": True' not in module_source)
    check('release_authorized": True' not in module_source)
    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == "bounded-automatic-diagnosis-checkpoint"), None)
    check(descriptor is not None)
    check((descriptor or {}).get("contract_version") == CONTRACT_VERSION)
    check((descriptor or {}).get("read_only") is True)
    check((descriptor or {}).get("post_available") is False)
    after, after_count = _tree_signature(source)
    check(after == before and after_count == count)
    check(runtime is None or runtime.exists() == runtime_existed)

    summary = {
        "diagnosable_outcome_count": len(DIAGNOSABLE_OUTCOMES),
        "successful_outcome_excluded": True,
        "exact_continuation_binding_required": True,
        "content_free_evidence_required": True,
        "ordinary_chat_attachment_present": True,
        "provider_free_diagnosis": True,
        "test_free_diagnosis": True,
        "automatic_diagnosis_contract": True,
        "root_cause_proven": False,
        "operator_review_required": True,
        "durable_replay_and_recovery": True,
        "privacy_preserved": True,
        "repair_authorized": False,
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
        "diagnosis_runtime_executed": False,
        "runtime_probed": False,
        "runtime_data_read": False,
        "runtime_mutated": False,
        "source_modified": False,
        "project_modified": False,
        "dependencies_installed": False,
        "automatic_diagnosis_contract": True,
        "automatic_diagnosis_executed": False,
        "root_cause_proven": False,
        "automatic_repair": False,
        "retest_authorized": False,
        "repair_authorized": False,
        "apply_authorized": False,
        "release_authorized": False,
        "authority_granted": False,
        "global_profile_pass_claimed": False,
        "source_signature_before": before,
        "source_signature_after": after,
        "source_file_count": count,
        "limitations": [
            "The checkpoint evaluates synthetic content-free diagnosis evidence and reads no private runtime records.",
            "Operational diagnosis classifies lifecycle observations only and never proves root cause.",
            "Every diagnosis requires operator review before a repair proposal may be prepared.",
            "Retest, repair, selected-project apply, installation, promotion, release, and model management remain unavailable.",
        ],
    }
    report["structural_digest"] = _digest({key: value for key, value in report.items() if key != "structural_digest"})
    return report
