from __future__ import annotations

"""Strictly read-only v1180.9 project-inspection and planning checkpoint.

Consolidates explicit-root project inspection, operator deficiency review,
content-free structural specification, and bounded implementation/test planning.
The checkpoint uses a temporary synthetic project only. It never discovers a
private project registry, creates or applies a patch, runs tests, invokes a
shell/tool/provider/model, grants authority, or mutates source or production
runtime state.
"""

import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from checkpoint_registry import inspect_checkpoint_registry
from natural_language_action_checkpoint import build_natural_language_action_checkpoint
from package_integrity import package_privacy_summary_for_root
from supervised_deficiency_specification import CONTRACT_VERSION as SPECIFICATION_CONTRACT_VERSION, MAX_REVIEW_ROWS, MAX_SPECIFICATIONS, build_specification_candidates, review_deficiency_candidates, specification_foundation_prompt
from supervised_implementation_test_planning import CONTRACT_VERSION as PLANNING_CONTRACT_VERSION, MAX_PLAN_ROWS, build_implementation_and_test_plans, implementation_test_planning_prompt
from supervised_project_inspection import CONTRACT_VERSION as INSPECTION_CONTRACT_VERSION, MAX_CANDIDATES, MAX_FILES, MAX_FILE_BYTES, MAX_PUBLIC_FILES, MAX_TOTAL_BYTES, inspect_project_source, project_inspection_prompt

CONTRACT_VERSION = "v1180.9"
_CHECKPOINT_ID = "supervised-project-inspection-planning:v1180.9"
_EXCLUDED = {
    "data", "sandbox", ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "dist", "build", "reports",
}
_FORBIDDEN_REPORT_TEXT = (
    "PROJECT_CHECKPOINT_PRIVATE_SOURCE",
    "PROJECT_CHECKPOINT_PRIVATE_SECRET",
    "PROJECT_CHECKPOINT_PRIVATE_OUTPUT",
    "raw_source_text",
    "raw_patch_text",
    "raw_shell_command",
    "chain_of_thought",
    "private reasoning payload",
)


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _tree_signature(root: Path) -> str:
    h = hashlib.sha256()
    if not root.exists():
        return h.hexdigest()
    paths: list[Path] = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name not in _EXCLUDED]
        for name in files:
            path = Path(base) / name
            if path.suffix.lower() not in {".pyc", ".pyo"}:
                paths.append(path)
    for path in sorted(paths):
        try:
            relative = path.relative_to(root).as_posix()
            data = path.read_bytes()
        except OSError:
            continue
        h.update(relative.encode("utf-8"))
        h.update(b"\0")
        h.update(hashlib.sha256(data).digest())
    return h.hexdigest()


def _source_contract(source: Path) -> dict[str, Any]:
    paths = {
        "inspection": source / "conscious_agent" / "supervised_project_inspection.py",
        "specification": source / "conscious_agent" / "supervised_deficiency_specification.py",
        "planning": source / "conscious_agent" / "supervised_implementation_test_planning.py",
    }
    texts = {name: path.read_text(encoding="utf-8") for name, path in paths.items()}
    return {
        "inspection_contract": INSPECTION_CONTRACT_VERSION,
        "specification_contract": SPECIFICATION_CONTRACT_VERSION,
        "planning_contract": PLANNING_CONTRACT_VERSION,
        "maximum_files": MAX_FILES,
        "maximum_file_bytes": MAX_FILE_BYTES,
        "maximum_total_bytes": MAX_TOTAL_BYTES,
        "maximum_public_files": MAX_PUBLIC_FILES,
        "maximum_candidates": MAX_CANDIDATES,
        "maximum_review_rows": MAX_REVIEW_ROWS,
        "maximum_specifications": MAX_SPECIFICATIONS,
        "maximum_plan_rows": MAX_PLAN_ROWS,
        "inspection_write_present": any(token in texts["inspection"] for token in ("write_text(", "write_bytes(", "subprocess")),
        "specification_source_read_present": any(token in texts["specification"] for token in ("read_text(", "read_bytes(", "open(")),
        "specification_write_present": any(token in texts["specification"] for token in ("write_text(", "write_bytes(", "subprocess")),
        "planning_source_read_present": any(token in texts["planning"] for token in ("read_text(", "read_bytes(", "open(")),
        "planning_write_present": any(token in texts["planning"] for token in ("write_text(", "write_bytes(", "subprocess")),
        "planning_shell_present": "shell_invoked\": True" in texts["planning"] or "subprocess" in texts["planning"],
    }


def build_supervised_project_inspection_planning_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    runtime = Path(runtime_root or source / "data").resolve()
    source_before = _tree_signature(source)
    runtime_before = _tree_signature(runtime)
    checks: list[bool] = []

    def require(value: object) -> None:
        checks.append(bool(value))

    prior = build_natural_language_action_checkpoint(source_root=source, runtime_root=runtime)
    for key in (
        "ok", "read_only", "content_free", "authority_preserved",
        "natural_language_action_checkpoint_completed",
        "intent_through_follow_through_consolidated",
        "complete_action_loop_reliability_exercised",
    ):
        require(prior.get(key))
    for key in (
        "source_modified", "runtime_mutated", "registered_tool_invoked",
        "provider_contacted", "execution_invoked", "source_edit_performed",
        "installation_performed", "promotion_performed", "certification_performed",
    ):
        require(prior.get(key) is False)

    with TemporaryDirectory(prefix="eidolon-v1180-checkpoint-") as directory:
        project = Path(directory) / "project"
        (project / "pkg").mkdir(parents=True)
        (project / "docs").mkdir()
        (project / "data").mkdir()
        (project / "sandbox").mkdir()
        (project / "pkg" / "good.py").write_text(
            "def healthy():\n    return 1\n# TODO reviewed maintenance\n",
            encoding="utf-8",
        )
        (project / "pkg" / "bad.py").write_text("def broken(:\n    pass\n", encoding="utf-8")
        (project / "pkg" / "large.py").write_text("\n".join("x = 1" for _ in range(1201)) + "\n", encoding="utf-8")
        (project / "docs" / "README.md").write_text("Synthetic bounded project.\n", encoding="utf-8")
        (project / "oversized.txt").write_bytes(b"x" * (MAX_FILE_BYTES + 1))
        (project / "data" / "private.json").write_text(
            '{"secret":"PROJECT_CHECKPOINT_PRIVATE_SECRET"}', encoding="utf-8",
        )
        (project / "sandbox" / "private.txt").write_text(
            "PROJECT_CHECKPOINT_PRIVATE_OUTPUT", encoding="utf-8",
        )

        inspection = inspect_project_source(project)
        require(inspection.get("inspection_status") == "review_required")
        require(inspection.get("contract_version") == INSPECTION_CONTRACT_VERSION)
        require(inspection.get("file_count") == 5)
        require(inspection.get("public_file_count") == 5)
        require(inspection.get("deficiency_candidate_count") == 4)
        require(inspection.get("operator_review_required"))
        require(inspection.get("content_free"))
        require(inspection.get("raw_source_exposed") is False)
        require(inspection.get("project_registry_discovered") is False)
        require(inspection.get("source_modified") is False)
        require(inspection.get("specification_created") is False)
        require(inspection.get("patch_created") is False)
        require(inspection.get("approval_created") is False)
        require(inspection.get("execution_invoked") is False)
        require(len(str(inspection.get("scope_digest") or "")) == 64)
        require(len(str(inspection.get("inspection_digest") or "")) == 64)
        categories = {row.get("category") for row in inspection.get("deficiency_candidates", [])}
        require(categories == {"python_syntax_error", "maintenance_marker", "large_module", "oversized_file"})
        for row in inspection.get("deficiency_candidates", []):
            require(str(row.get("candidate_id") or "").startswith("def-"))
            require(len(str(row.get("evidence_digest") or "")) == 64)
            require(row.get("operator_review_required") is True)
            require(row.get("specification_created") is False)
            require(row.get("patch_created") is False)
            require(row.get("source_modified") is False)
        encoded_inspection = json.dumps(inspection, sort_keys=True, separators=(",", ":"))
        require("PROJECT_CHECKPOINT_PRIVATE_SECRET" not in encoded_inspection)
        require("PROJECT_CHECKPOINT_PRIVATE_OUTPUT" not in encoded_inspection)
        require("data/private.json" not in encoded_inspection)
        require("sandbox/private.txt" not in encoded_inspection)

        by_category = {row["category"]: row for row in inspection["deficiency_candidates"]}
        decisions = {
            by_category["python_syntax_error"]["candidate_id"]: "confirm",
            by_category["large_module"]["candidate_id"]: "confirm",
            by_category["maintenance_marker"]["candidate_id"]: "reject",
            by_category["oversized_file"]["candidate_id"]: "defer",
        }
        review = review_deficiency_candidates(inspection, decisions)
        require(review.get("review_status") == "reviewed")
        require(review.get("contract_version") == SPECIFICATION_CONTRACT_VERSION)
        require(review.get("review_row_count") == 4)
        require(review.get("confirmed_count") == 2)
        require(review.get("rejected_count") == 1)
        require(review.get("deferred_count") == 1)
        require(review.get("pending_count") == 0)
        require(review.get("content_free"))
        require(review.get("source_read") is False)
        require(review.get("project_registry_discovered") is False)
        require(review.get("source_modified") is False)
        require(review.get("patch_created") is False)
        require(review.get("approval_created") is False)
        require(review.get("authorization_created") is False)
        require(review.get("execution_invoked") is False)
        require(len(str(review.get("review_digest") or "")) == 64)
        for row in review.get("review_rows", []):
            require(len(str(row.get("decision_digest") or "")) == 64)
            require(row.get("decision") in {"confirm", "reject", "defer", "pending"})
            require(row.get("deficiency_confirmed") == (row.get("decision") == "confirm"))
            require(row.get("specification_eligible") == (row.get("decision") == "confirm"))

        specifications = build_specification_candidates(review)
        require(specifications.get("specification_status") == "candidate_ready")
        require(specifications.get("specification_count") == 2)
        require(specifications.get("contract_version") == SPECIFICATION_CONTRACT_VERSION)
        require(specifications.get("content_free"))
        require(specifications.get("implementation_allowed") is False)
        require(specifications.get("test_execution_allowed") is False)
        require(specifications.get("source_modified") is False)
        require(specifications.get("patch_created") is False)
        require(specifications.get("execution_invoked") is False)
        require(len(str(specifications.get("specification_bundle_digest") or "")) == 64)
        for spec in specifications.get("specifications", []):
            require(str(spec.get("specification_id") or "").startswith("spec-"))
            require(len(str(spec.get("specification_digest") or "")) == 64)
            require(len(str(spec.get("decision_digest") or "")) == 64)
            require(len(str(spec.get("evidence_digest") or "")) == 64)
            require(bool(spec.get("objective_codes")))
            require(bool(spec.get("acceptance_criteria_codes")))
            require(bool(spec.get("test_intent_codes")))
            require(spec.get("reversibility_required") is True)
            require(spec.get("operator_approval_required") is True)
            require(spec.get("implementation_allowed") is False)

        plans = build_implementation_and_test_plans(specifications)
        require(plans.get("planning_status") == "candidate_ready")
        require(plans.get("plan_count") == 2)
        require(plans.get("contract_version") == PLANNING_CONTRACT_VERSION)
        require(plans.get("content_free"))
        require(plans.get("operator_review_required"))
        require(plans.get("source_read") is False)
        require(plans.get("source_modified") is False)
        require(plans.get("patch_created") is False)
        require(plans.get("tests_executed") is False)
        require(plans.get("approval_created") is False)
        require(plans.get("authorization_created") is False)
        require(plans.get("execution_invoked") is False)
        require(plans.get("tool_invoked") is False)
        require(plans.get("provider_contacted") is False)
        require(plans.get("model_contacted") is False)
        require(plans.get("shell_invoked") is False)
        require(plans.get("implementation_allowed") is False)
        require(plans.get("test_execution_allowed") is False)
        require(len(str(plans.get("planning_bundle_digest") or "")) == 64)
        for plan in plans.get("plans", []):
            require(str(plan.get("implementation_plan_id") or "").startswith("impl-"))
            require(len(str(plan.get("implementation_plan_digest") or "")) == 64)
            require(len(str(plan.get("test_plan_digest") or "")) == 64)
            require(bool(plan.get("implementation_step_codes")))
            require("minimal_bounded_change" in plan.get("implementation_constraints", []))
            require("preserve_privacy_boundary" in plan.get("implementation_constraints", []))
            require("operator_review_before_patch" in plan.get("implementation_constraints", []))
            require("rollback_required" in plan.get("implementation_constraints", []))
            require("source_identity_match" in plan.get("pre_change_checks", []))
            require("specification_digest_match" in plan.get("pre_change_checks", []))
            require("clean_sandbox_required" in plan.get("pre_change_checks", []))
            require("focused_regression" in plan.get("post_change_checks", []))
            require("source_privacy_scan" in plan.get("post_change_checks", []))
            require(plan.get("rollback_plan_codes") == ["restore_pre_change_snapshot", "rerun_focused_regression"])
            require(plan.get("patch_allowed") is False)
            require(plan.get("test_execution_allowed") is False)
            require(plan.get("implementation_authorized") is False)

        scoped = inspect_project_source(project, scope=["pkg/good.py"])
        require(scoped.get("file_count") == 1)
        require((scoped.get("files") or [{}])[0].get("path") == "pkg/good.py")
        require(scoped.get("rejected_scope_count") == 0)
        traversal = inspect_project_source(
            project, scope=["../secret", "/etc/passwd", "C:/Windows", "data/private.json", "sandbox/private.txt"],
        )
        require(traversal.get("file_count") == 0)
        require(int(traversal.get("rejected_scope_count") or 0) >= 5)
        require(traversal.get("source_modified") is False)
        require(inspect_project_source(project / "missing").get("block_reason") == "source_root_unavailable")

        many = project / "many"
        many.mkdir()
        for index in range(20):
            (many / f"f{index}.py").write_text("x = 1\n", encoding="utf-8")
        bounded = inspect_project_source(project, scope=["many"], max_files=5)
        require(bounded.get("file_count") == 5)
        require(bounded.get("input_truncated"))
        require(int(bounded.get("public_file_count") or 0) <= MAX_PUBLIC_FILES)
        require(int(bounded.get("deficiency_candidate_count") or 0) <= MAX_CANDIDATES)

        pending_review = review_deficiency_candidates(inspection, {})
        require(pending_review.get("review_status") == "review_required")
        require(pending_review.get("pending_count") == 4)
        require(build_specification_candidates(pending_review).get("specification_count") == 0)
        require(review_deficiency_candidates({"contract_version": "wrong"}, {}).get("block_reason") == "invalid_inspection_contract")
        tampered_review = dict(review)
        tampered_review["review_digest"] = "bad"
        require(build_specification_candidates(tampered_review).get("block_reason") == "invalid_review_contract")
        tampered_specs = json.loads(json.dumps(specifications))
        tampered_specs["specifications"][0]["category"] = "maintenance_marker"
        tampered_plan = build_implementation_and_test_plans(tampered_specs)
        require(tampered_plan.get("invalid_specification_count") == 1)
        require(tampered_plan.get("plan_count") == 1)
        duplicate_specs = json.loads(json.dumps(specifications))
        duplicate_specs["specifications"] *= 4
        duplicate_plan = build_implementation_and_test_plans(duplicate_specs)
        require(duplicate_plan.get("plan_count") == 2)
        require(int(duplicate_plan.get("invalid_specification_count") or 0) == 6)
        require(build_implementation_and_test_plans({"contract_version": "wrong"}).get("block_reason") == "invalid_specification_bundle")

        require("candidates, not proven defects" in project_inspection_prompt(inspection))
        require("not patch instructions" in specification_foundation_prompt(specifications))
        require("not patches or executable test commands" in implementation_test_planning_prompt(plans))

    source_contract = _source_contract(source)
    require(source_contract["inspection_contract"] == "v1180.2")
    require(source_contract["specification_contract"] == "v1180.5")
    require(source_contract["planning_contract"] == "v1180.8")
    require(source_contract["maximum_files"] == 512)
    require(source_contract["maximum_file_bytes"] == 512_000)
    require(source_contract["maximum_total_bytes"] == 8_000_000)
    require(source_contract["maximum_public_files"] == 128)
    require(source_contract["maximum_candidates"] == 64)
    require(source_contract["maximum_review_rows"] == 64)
    require(source_contract["maximum_specifications"] == 32)
    require(source_contract["maximum_plan_rows"] == 32)
    require(source_contract["inspection_write_present"] is False)
    require(source_contract["specification_source_read_present"] is False)
    require(source_contract["specification_write_present"] is False)
    require(source_contract["planning_source_read_present"] is False)
    require(source_contract["planning_write_present"] is False)
    require(source_contract["planning_shell_present"] is False)

    registry = inspect_checkpoint_registry(source_root=source)
    checkpoint_row = next((
        row for row in registry.get("checkpoints", [])
        if row.get("checkpoint_id") == "supervised-project-inspection-planning-checkpoint"
    ), None)
    require(checkpoint_row is not None)
    require((checkpoint_row or {}).get("builder") == "build_supervised_project_inspection_planning_checkpoint")
    require((checkpoint_row or {}).get("contract_version") == CONTRACT_VERSION)
    require(not registry.get("duplicate_checkpoint_ids"))
    require(not registry.get("duplicate_builder_targets"))

    privacy = package_privacy_summary_for_root(source)
    require(privacy.get("ok"))
    require(privacy.get("source_only"))
    require(int(privacy.get("forbidden_count", privacy.get("forbidden_entry_count", 0)) or 0) == 0)
    require(int(privacy.get("private_content_finding_count", 0) or 0) == 0)

    evidence = {
        "retained_action_checkpoint": {
            "contract_version": prior.get("contract_version"),
            "passed": prior.get("passed"),
            "total": prior.get("total"),
            "structural_digest": prior.get("structural_digest"),
        },
        "inspection": {
            "contract_version": inspection.get("contract_version"),
            "file_count": inspection.get("file_count"),
            "candidate_count": inspection.get("deficiency_candidate_count"),
            "inspection_digest": inspection.get("inspection_digest"),
            "scope_digest": inspection.get("scope_digest"),
        },
        "review": {
            "confirmed_count": review.get("confirmed_count"),
            "rejected_count": review.get("rejected_count"),
            "deferred_count": review.get("deferred_count"),
            "review_digest": review.get("review_digest"),
        },
        "specification": {
            "specification_count": specifications.get("specification_count"),
            "specification_bundle_digest": specifications.get("specification_bundle_digest"),
        },
        "planning": {
            "plan_count": plans.get("plan_count"),
            "planning_bundle_digest": plans.get("planning_bundle_digest"),
        },
        "source_contract": source_contract,
        "privacy": {
            "entry_count": privacy.get("entry_count"),
            "forbidden_entry_count": privacy.get("forbidden_entry_count", privacy.get("forbidden_count", 0)),
            "private_content_finding_count": privacy.get("private_content_finding_count", 0),
        },
    }
    evidence_text = json.dumps(evidence, sort_keys=True, separators=(",", ":"))
    forbidden_count = sum(1 for value in _FORBIDDEN_REPORT_TEXT if value in evidence_text)
    require(forbidden_count == 0)

    source_modified = source_before != _tree_signature(source)
    runtime_mutated = runtime_before != _tree_signature(runtime)
    require(source_modified is False)
    require(runtime_mutated is False)

    report: dict[str, Any] = {
        "schema_version": "1",
        "contract_version": CONTRACT_VERSION,
        "checkpoint_id": _CHECKPOINT_ID,
        "status": "ready" if all(checks) else "review_required",
        "ok": all(checks),
        "passed": sum(checks),
        "total": len(checks),
        "read_only": True,
        "post_available": False,
        "content_free": True,
        "authority_preserved": True,
        "operator_promotion_required": True,
        "desktop_verification_deferred_until_v1200": True,
        "supervised_project_inspection_planning_checkpoint_completed": True,
        "explicit_root_inspection_exercised": True,
        "scope_privacy_boundaries_exercised": True,
        "deficiency_review_exercised": True,
        "specification_candidates_exercised": True,
        "implementation_test_planning_exercised": True,
        "tamper_and_replay_rejection_exercised": True,
        "bounded_limits_exercised": True,
        "private_project_registry_discovered": False,
        "raw_source_exposed": False,
        "raw_evidence_exposed": False,
        "raw_patch_created": False,
        "specification_automatically_confirmed": False,
        "patch_created": False,
        "patch_applied": False,
        "tests_executed": False,
        "shell_invoked": False,
        "automatic_approval_created": False,
        "automatic_authorization_granted": False,
        "execution_invoked": False,
        "registered_tool_invoked": False,
        "provider_contacted": False,
        "model_operation_performed": False,
        "source_edit_performed": False,
        "production_runtime_mutated": False,
        "memory_mutated": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "source_modified": source_modified,
        "runtime_mutated": runtime_mutated,
        "forbidden_report_value_count": forbidden_count,
        "summary": {
            "retained_checkpoint_count": 1,
            "inspected_file_case_count": int(inspection.get("file_count") or 0),
            "deficiency_candidate_case_count": int(inspection.get("deficiency_candidate_count") or 0),
            "review_decision_case_count": int(review.get("review_row_count") or 0),
            "confirmed_deficiency_case_count": int(review.get("confirmed_count") or 0),
            "specification_case_count": int(specifications.get("specification_count") or 0),
            "implementation_plan_case_count": int(plans.get("plan_count") or 0),
            "scope_boundary_case_count": 5,
            "tamper_rejection_case_count": 6,
            "maximum_files": MAX_FILES,
            "maximum_file_bytes": MAX_FILE_BYTES,
            "maximum_total_bytes": MAX_TOTAL_BYTES,
            "maximum_public_files": MAX_PUBLIC_FILES,
            "maximum_candidates": MAX_CANDIDATES,
            "maximum_review_rows": MAX_REVIEW_ROWS,
            "maximum_specifications": MAX_SPECIFICATIONS,
            "maximum_plan_rows": MAX_PLAN_ROWS,
            "privacy_forbidden_entry_count": int(privacy.get("forbidden_entry_count", privacy.get("forbidden_count", 0)) or 0),
            "privacy_content_finding_count": int(privacy.get("private_content_finding_count", 0) or 0),
            "open_limitation_count": 4,
        },
        "evidence": evidence,
    }
    report["structural_digest"] = _digest({key: value for key, value in report.items() if key != "structural_digest"})
    return report
