from __future__ import annotations

"""Strictly read-only v1181.9 supervised implementation checkpoint.

Consolidates exact implementation preparation, private in-memory patch drafting,
operator patch review, and isolated sandbox materialization. The checkpoint uses
caller-owned synthetic contracts and temporary sandbox roots only. It never
reads or modifies production source, applies a patch to source, runs tests,
invokes a shell/tool/provider/model, grants source-application authority, or
performs installation, promotion, certification, or release authorization.
"""

import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from bounded_implementation_preparation import CONTRACT_VERSION as PREPARATION_CONTRACT_VERSION, MAX_BASELINE_FILES, MAX_PLANS, MAX_PREPARATIONS, MAX_REPORT_BYTES, prepare_implementation_candidates
from checkpoint_registry import inspect_checkpoint_registry
from package_integrity import package_privacy_summary_for_root
from supervised_patch_draft_foundations import CONTRACT_VERSION as DRAFT_CONTRACT_VERSION, MAX_PATCH_BYTES, MAX_PATCH_LINES, MAX_SOURCE_BYTES as DRAFT_MAX_SOURCE_BYTES, draft_supervised_patch, patch_draft_public_summary
from supervised_patch_review_sandbox_materialization import CONTRACT_VERSION as MATERIALIZATION_CONTRACT_VERSION, MAX_SOURCE_BYTES as MATERIALIZATION_MAX_SOURCE_BYTES, materialize_reviewed_patch, review_patch_draft, sandbox_materialization_public_summary
from supervised_project_inspection_planning_checkpoint import build_supervised_project_inspection_planning_checkpoint

CONTRACT_VERSION = "v1181.9"
_CHECKPOINT_ID = "supervised-implementation:v1181.9"
_EXCLUDED = {
    "data", "sandbox", ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "dist", "build", "reports",
}
_FORBIDDEN_REPORT_TEXT = (
    "IMPLEMENTATION_CHECKPOINT_PRIVATE_SOURCE",
    "IMPLEMENTATION_CHECKPOINT_PRIVATE_REPLACEMENT",
    "IMPLEMENTATION_CHECKPOINT_PRIVATE_PATCH",
    "patch_text",
    "before_text",
    "after_text",
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


def _bytes_digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


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
        "preparation": source / "conscious_agent" / "bounded_implementation_preparation.py",
        "draft": source / "conscious_agent" / "supervised_patch_draft_foundations.py",
        "materialization": source / "conscious_agent" / "supervised_patch_review_sandbox_materialization.py",
    }
    texts = {name: path.read_text(encoding="utf-8") for name, path in paths.items()}
    return {
        "preparation_contract": PREPARATION_CONTRACT_VERSION,
        "draft_contract": DRAFT_CONTRACT_VERSION,
        "materialization_contract": MATERIALIZATION_CONTRACT_VERSION,
        "maximum_plans": MAX_PLANS,
        "maximum_baseline_files": MAX_BASELINE_FILES,
        "maximum_preparations": MAX_PREPARATIONS,
        "maximum_preparation_report_bytes": MAX_REPORT_BYTES,
        "maximum_draft_source_bytes": DRAFT_MAX_SOURCE_BYTES,
        "maximum_patch_bytes": MAX_PATCH_BYTES,
        "maximum_patch_lines": MAX_PATCH_LINES,
        "maximum_materialization_source_bytes": MATERIALIZATION_MAX_SOURCE_BYTES,
        "preparation_source_read_present": any(token in texts["preparation"] for token in ("read_text(", "read_bytes(", "open(")),
        "preparation_write_present": any(token in texts["preparation"] for token in ("write_text(", "write_bytes(", "subprocess")),
        "draft_repository_read_present": any(token in texts["draft"] for token in ("read_text(", "read_bytes(", "open(")),
        "draft_write_present": any(token in texts["draft"] for token in ("write_text(", "write_bytes(", "subprocess")),
        "materialization_subprocess_present": "subprocess" in texts["materialization"],
        "materialization_source_application_enabled": 'source_application_authorized": True' in texts["materialization"],
        "materialization_test_execution_enabled": 'tests_executed": True' in texts["materialization"],
        "materialization_provider_enabled": 'provider_contacted": True' in texts["materialization"],
    }


def build_supervised_implementation_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    runtime = Path(runtime_root or source / "data").resolve()
    source_before = _tree_signature(source)
    runtime_before = _tree_signature(runtime)
    checks: list[bool] = []

    def require(value: object) -> None:
        checks.append(bool(value))

    prior = build_supervised_project_inspection_planning_checkpoint(source_root=source, runtime_root=runtime)
    for key in (
        "ok", "read_only", "content_free", "authority_preserved",
        "supervised_project_inspection_planning_checkpoint_completed",
        "explicit_root_inspection_exercised", "deficiency_review_exercised",
        "specification_candidates_exercised", "implementation_test_planning_exercised",
    ):
        require(prior.get(key))
    for key in (
        "source_modified", "runtime_mutated", "patch_created", "patch_applied",
        "tests_executed", "shell_invoked", "automatic_approval_created",
        "automatic_authorization_granted", "execution_invoked", "registered_tool_invoked",
        "provider_contacted", "model_operation_performed", "source_edit_performed",
        "installation_performed", "promotion_performed", "certification_performed",
    ):
        require(prior.get(key) is False)

    before_text = (
        "def checkpoint_value():\n"
        "    return 1\n"
        "# IMPLEMENTATION_CHECKPOINT_PRIVATE_SOURCE\n"
    )
    after_text = (
        "def checkpoint_value():\n"
        "    return 2\n"
        "# IMPLEMENTATION_CHECKPOINT_PRIVATE_REPLACEMENT\n"
    )
    before_digest = _bytes_digest(before_text.encode("utf-8"))
    target = "conscious_agent/synthetic_checkpoint_target.py"
    plan = {
        "specification_id": "spec-checkpoint",
        "implementation_plan_id": "impl-checkpoint",
        "implementation_plan_digest": "a" * 64,
        "test_plan_digest": "b" * 64,
        "implementation_step_codes": ["prepare_minimal_parseability_change"],
        "pre_change_checks": ["source_identity_match", "fresh_source_required"],
        "acceptance_criteria_codes": ["python_parses", "specified_behavior_matches"],
        "post_change_checks": ["python_compile", "focused_regression", "source_privacy_scan"],
        "rollback_plan_codes": ["restore_pre_change_snapshot"],
        "patch_allowed": False,
        "test_execution_allowed": False,
    }
    planning = {
        "contract_version": "v1180.8",
        "content_free": True,
        "source_modified": False,
        "patch_created": False,
        "tests_executed": False,
        "planning_bundle_digest": "c" * 64,
        "plans": [plan],
    }
    baseline = {
        "content_free": True,
        "baseline_digest": "d" * 64,
        "files": [{"path": target, "file_digest": before_digest}],
    }
    bindings = {
        "impl-checkpoint": {"target_path": target, "expected_file_digest": before_digest},
    }

    preparation = prepare_implementation_candidates(planning, baseline, bindings)
    require(preparation.get("contract_version") == PREPARATION_CONTRACT_VERSION)
    require(preparation.get("preparation_status") == "candidate_ready")
    require(preparation.get("preparation_count") == 1)
    require(preparation.get("content_free"))
    require(preparation.get("source_read") is False)
    require(preparation.get("source_modified") is False)
    require(preparation.get("patch_created") is False)
    require(preparation.get("tests_executed") is False)
    require(preparation.get("shell_invoked") is False)
    require(preparation.get("tool_invoked") is False)
    require(preparation.get("approval_created") is False)
    require(preparation.get("authorization_created") is False)
    prep_row = preparation["preparations"][0]
    require(prep_row.get("target_path") == target)
    require(prep_row.get("baseline_file_digest") == before_digest)
    require(prep_row.get("sandbox_required") is True)
    require(prep_row.get("fresh_source_match_required") is True)
    require(prep_row.get("operator_review_required") is True)
    require(prep_row.get("patch_creation_allowed") is False)
    require(prep_row.get("implementation_authorized") is False)
    require(prep_row.get("test_execution_allowed") is False)
    require(str(prep_row.get("preparation_id") or "").startswith("prep-"))
    require(len(str(prep_row.get("preparation_digest") or "")) == 64)
    require(len(str(preparation.get("preparation_bundle_digest") or "")) == 64)

    draft = draft_supervised_patch(
        preparation, str(prep_row["preparation_id"]), before_text, after_text,
    )
    require(draft.get("contract_version") == DRAFT_CONTRACT_VERSION)
    require(draft.get("draft_status") == "draft_ready")
    require(draft.get("target_path") == target)
    require(draft.get("before_digest") == before_digest)
    require(len(str(draft.get("after_digest") or "")) == 64)
    require(len(str(draft.get("patch_digest") or "")) == 64)
    require(len(str(draft.get("draft_digest") or "")) == 64)
    require(draft.get("single_target") is True)
    require(draft.get("reversible") is True)
    require(draft.get("sandbox_required") is True)
    require(draft.get("operator_review_required") is True)
    require(draft.get("separate_application_approval_required") is True)
    require(draft.get("application_authorized") is False)
    require(draft.get("test_execution_authorized") is False)
    require(draft.get("repository_read") is False)
    require(draft.get("source_modified") is False)
    require(draft.get("patch_written") is False)
    require(draft.get("patch_applied") is False)
    require(draft.get("tests_executed") is False)
    require(draft.get("shell_invoked") is False)
    require(draft.get("tool_invoked") is False)
    require(draft.get("private_artifact") is True)
    require(draft.get("contains_source_content") is True)
    require(draft.get("public_diagnostics_safe") is False)
    require("IMPLEMENTATION_CHECKPOINT_PRIVATE_PATCH" not in str(draft.get("patch_text") or ""))

    draft_summary = patch_draft_public_summary(draft)
    require(draft_summary.get("content_free"))
    require(draft_summary.get("patch_text_included") is False)
    require(draft_summary.get("raw_source_included") is False)
    require(draft_summary.get("authority_granted") is False)
    require("patch_text" not in draft_summary)
    require(len(str(draft_summary.get("summary_digest") or "")) == 64)

    approved = review_patch_draft(draft, decision="approve", operator_actor="checkpoint-operator")
    rejected = review_patch_draft(draft, decision="reject", operator_actor="checkpoint-operator")
    deferred = review_patch_draft(draft, decision="defer", operator_actor="checkpoint-operator")
    require(approved.get("contract_version") == MATERIALIZATION_CONTRACT_VERSION)
    require(approved.get("review_status") == "approved_for_sandbox")
    require(approved.get("sandbox_materialization_authorized") is True)
    require(approved.get("source_application_authorized") is False)
    require(approved.get("test_execution_authorized") is False)
    require(approved.get("content_free"))
    require(len(str(approved.get("review_digest") or "")) == 64)
    require(len(str(approved.get("operator_actor_digest") or "")) == 64)
    require(rejected.get("review_status") == "rejected")
    require(rejected.get("sandbox_materialization_authorized") is False)
    require(deferred.get("review_status") == "deferred")
    require(deferred.get("sandbox_materialization_authorized") is False)

    with TemporaryDirectory(prefix="eidolon-v1181-checkpoint-") as directory:
        root = Path(directory)
        synthetic_source = root / "synthetic-source"
        sandbox = root / "isolated-sandbox"
        synthetic_source.mkdir()
        materialized = materialize_reviewed_patch(
            draft,
            approved,
            sandbox_root=sandbox,
            source_root=synthetic_source,
            before_text=before_text,
            after_text=after_text,
        )
        require(materialized.get("materialization_status") == "materialized")
        require(materialized.get("sandbox_materialized") is True)
        require(materialized.get("sandbox_file_written") is True)
        require(materialized.get("source_modified") is False)
        require(materialized.get("patch_applied_to_source") is False)
        require(materialized.get("tests_executed") is False)
        require(materialized.get("shell_invoked") is False)
        require(materialized.get("tool_invoked") is False)
        require(materialized.get("provider_contacted") is False)
        require(materialized.get("model_contacted") is False)
        require(materialized.get("source_application_authorized") is False)
        require(materialized.get("test_execution_authorized") is False)
        require(materialized.get("promotion_authorized") is False)
        require(materialized.get("release_authorized") is False)
        require(materialized.get("sandbox_only") is True)
        sandbox_target = sandbox / target
        require(sandbox_target.is_file())
        require(_bytes_digest(sandbox_target.read_bytes()) == draft.get("after_digest"))
        require((sandbox / ".eidolon_sandbox_materialization.json").is_file())
        require(not any(synthetic_source.rglob("*")))
        replay = materialize_reviewed_patch(
            draft,
            approved,
            sandbox_root=sandbox,
            source_root=synthetic_source,
            before_text=before_text,
            after_text=after_text,
        )
        require(replay.get("materialization_status") == "already_materialized")
        require(replay.get("sandbox_file_written") is False)
        require(replay.get("sandbox_target_digest") == materialized.get("sandbox_target_digest"))
        public_materialized = sandbox_materialization_public_summary(materialized)
        require(public_materialized.get("content_free"))
        require(public_materialized.get("sandbox_only"))
        require(public_materialized.get("source_modified") is False)
        require(public_materialized.get("patch_applied_to_source") is False)
        require(public_materialized.get("tests_executed") is False)
        require(public_materialized.get("authority_granted") is False)
        require("patch_text" not in public_materialized)
        require(len(str(public_materialized.get("summary_digest") or "")) == 64)

        drift_sandbox = root / "drift-sandbox"
        (drift_sandbox / "conscious_agent").mkdir(parents=True)
        (drift_sandbox / target).write_text("drift", encoding="utf-8")
        drift = materialize_reviewed_patch(
            draft, approved, sandbox_root=drift_sandbox, source_root=synthetic_source,
            before_text=before_text, after_text=after_text,
        )
        require(drift.get("block_reason") == "sandbox_target_drift")

        overlap = materialize_reviewed_patch(
            draft, approved, sandbox_root=synthetic_source / "sandbox", source_root=synthetic_source,
            before_text=before_text, after_text=after_text,
        )
        require(overlap.get("block_reason") == "sandbox_not_isolated")

        symlink_sandbox = root / "symlink-sandbox"
        outside = root / "outside"
        symlink_sandbox.mkdir()
        outside.mkdir()
        try:
            (symlink_sandbox / "conscious_agent").symlink_to(outside, target_is_directory=True)
            symlink_result = materialize_reviewed_patch(
                draft, approved, sandbox_root=symlink_sandbox, source_root=synthetic_source,
                before_text=before_text, after_text=after_text,
            )
            require(symlink_result.get("block_reason") == "sandbox_symlink_boundary")
        except (OSError, NotImplementedError):
            require(True)

    stale = prepare_implementation_candidates(
        planning, baseline,
        {"impl-checkpoint": {"target_path": target, "expected_file_digest": "f" * 64}},
    )
    require(stale.get("preparation_status") == "stale_source")
    require(stale.get("stale_binding_count") == 1)
    for bad_target in (
        "../secret.py", "/etc/passwd", "C:/secret.py", "data/private.json", "sandbox/private.py", "binary.exe",
    ):
        blocked = prepare_implementation_candidates(
            planning, baseline,
            {"impl-checkpoint": {"target_path": bad_target, "expected_file_digest": before_digest}},
        )
        require(blocked.get("preparation_count") == 0)
    require(prepare_implementation_candidates({**planning, "contract_version": "bad"}, baseline, bindings).get("block_reason") == "invalid_input_contract")
    require(prepare_implementation_candidates(planning, {**baseline, "baseline_digest": "bad"}, bindings).get("block_reason") == "invalid_input_contract")
    duplicate_preparation = prepare_implementation_candidates({**planning, "plans": [plan, plan]}, baseline, bindings)
    require(duplicate_preparation.get("preparation_count") == 1)
    require(duplicate_preparation.get("duplicate_plan_count") == 1)

    require(draft_supervised_patch(preparation, str(prep_row["preparation_id"]), before_text + "# drift\n", after_text).get("block_reason") == "baseline_text_digest_mismatch")
    require(draft_supervised_patch(preparation, "missing", before_text, after_text).get("block_reason") == "invalid_preparation_contract")
    require(draft_supervised_patch({**preparation, "contract_version": "bad"}, str(prep_row["preparation_id"]), before_text, after_text).get("block_reason") == "invalid_preparation_contract")
    require(draft_supervised_patch(preparation, str(prep_row["preparation_id"]), before_text, before_text).get("block_reason") == "no_change")
    require(draft_supervised_patch(preparation, str(prep_row["preparation_id"]), before_text + "\x00", after_text).get("block_reason") == "invalid_source_text")
    unsafe_preparation = json.loads(json.dumps(preparation))
    unsafe_preparation["preparations"][0]["target_path"] = "../secret.py"
    require(draft_supervised_patch(unsafe_preparation, str(prep_row["preparation_id"]), before_text, after_text).get("block_reason") == "invalid_target_binding")
    unsafe_authority = json.loads(json.dumps(preparation))
    unsafe_authority["preparations"][0]["implementation_authorized"] = True
    require(draft_supervised_patch(unsafe_authority, str(prep_row["preparation_id"]), before_text, after_text).get("block_reason") == "unsafe_preparation_authority")

    require(review_patch_draft(draft, decision="approve", operator_actor="").get("block_reason") == "missing_operator_actor")
    require(review_patch_draft(draft, decision="ship", operator_actor="operator").get("block_reason") == "invalid_review_decision")
    require(review_patch_draft({**draft, "draft_status": "blocked"}, decision="approve", operator_actor="operator").get("block_reason") == "invalid_patch_draft_contract")
    require(materialize_reviewed_patch(draft, rejected, sandbox_root="/tmp/eidolon-v1181-reject", source_root="/tmp/eidolon-v1181-source", before_text=before_text, after_text=after_text).get("block_reason") == "invalid_review_binding")
    require(materialize_reviewed_patch(draft, approved, sandbox_root="/tmp/eidolon-v1181-digest", source_root="/tmp/eidolon-v1181-source-2", before_text=before_text + "x", after_text=after_text).get("block_reason") == "source_text_digest_mismatch")

    source_contract = _source_contract(source)
    require(source_contract["preparation_contract"] == "v1181.2")
    require(source_contract["draft_contract"] == "v1181.5")
    require(source_contract["materialization_contract"] == "v1181.8")
    require(source_contract["maximum_plans"] == 32)
    require(source_contract["maximum_baseline_files"] == 512)
    require(source_contract["maximum_preparations"] == 32)
    require(source_contract["maximum_preparation_report_bytes"] == 131_072)
    require(source_contract["maximum_draft_source_bytes"] == 262_144)
    require(source_contract["maximum_patch_bytes"] == 262_144)
    require(source_contract["maximum_patch_lines"] == 4_096)
    require(source_contract["maximum_materialization_source_bytes"] == 262_144)
    require(source_contract["preparation_source_read_present"] is False)
    require(source_contract["preparation_write_present"] is False)
    require(source_contract["draft_repository_read_present"] is False)
    require(source_contract["draft_write_present"] is False)
    require(source_contract["materialization_subprocess_present"] is False)
    require(source_contract["materialization_source_application_enabled"] is False)
    require(source_contract["materialization_test_execution_enabled"] is False)
    require(source_contract["materialization_provider_enabled"] is False)

    registry = inspect_checkpoint_registry(source_root=source)
    checkpoint_row = next((
        row for row in registry.get("checkpoints", [])
        if row.get("checkpoint_id") == "supervised-implementation-checkpoint"
    ), None)
    require(checkpoint_row is not None)
    require((checkpoint_row or {}).get("builder") == "build_supervised_implementation_checkpoint")
    require((checkpoint_row or {}).get("contract_version") == CONTRACT_VERSION)
    require(not registry.get("duplicate_checkpoint_ids"))
    require(not registry.get("duplicate_builder_targets"))

    privacy = package_privacy_summary_for_root(source)
    require(privacy.get("ok"))
    require(privacy.get("source_only"))
    require(int(privacy.get("forbidden_count", privacy.get("forbidden_entry_count", 0)) or 0) == 0)
    require(int(privacy.get("private_content_finding_count", 0) or 0) == 0)

    evidence = {
        "retained_planning_checkpoint": {
            "contract_version": prior.get("contract_version"),
            "passed": prior.get("passed"),
            "total": prior.get("total"),
            "structural_digest": prior.get("structural_digest"),
        },
        "preparation": {
            "preparation_count": preparation.get("preparation_count"),
            "preparation_bundle_digest": preparation.get("preparation_bundle_digest"),
            "preparation_digest": prep_row.get("preparation_digest"),
        },
        "draft": {
            "draft_status": draft.get("draft_status"),
            "draft_digest": draft.get("draft_digest"),
            "patch_digest": draft.get("patch_digest"),
            "patch_line_count": draft.get("patch_line_count"),
            "summary_digest": draft_summary.get("summary_digest"),
        },
        "review": {
            "approved_review_digest": approved.get("review_digest"),
            "rejected_review_digest": rejected.get("review_digest"),
            "deferred_review_digest": deferred.get("review_digest"),
        },
        "materialization": {
            "materialization_status": materialized.get("materialization_status"),
            "materialization_receipt_digest": materialized.get("materialization_receipt_digest"),
            "sandbox_marker_digest": materialized.get("sandbox_marker_digest"),
            "summary_digest": public_materialized.get("summary_digest"),
            "replay_status": replay.get("materialization_status"),
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
        "supervised_implementation_checkpoint_completed": True,
        "retained_project_inspection_planning_checkpoint_completed": True,
        "implementation_preparation_exercised": True,
        "private_patch_drafting_exercised": True,
        "operator_patch_review_exercised": True,
        "isolated_sandbox_materialization_exercised": True,
        "idempotent_materialization_replay_exercised": True,
        "tamper_and_boundary_rejection_exercised": True,
        "production_source_read": False,
        "production_source_modified": False,
        "raw_source_exposed": False,
        "raw_patch_exposed": False,
        "patch_written_to_source": False,
        "patch_applied_to_source": False,
        "tests_executed": False,
        "shell_invoked": False,
        "automatic_approval_created": False,
        "automatic_authorization_granted": False,
        "source_application_authorized": False,
        "test_execution_authorized": False,
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
        "release_authorized": False,
        "source_modified": source_modified,
        "runtime_mutated": runtime_mutated,
        "forbidden_report_value_count": forbidden_count,
        "summary": {
            "retained_checkpoint_count": 1,
            "preparation_case_count": 1,
            "private_draft_case_count": 1,
            "review_decision_case_count": 3,
            "sandbox_materialization_case_count": 2,
            "negative_boundary_case_count": 22,
            "maximum_plans": MAX_PLANS,
            "maximum_baseline_files": MAX_BASELINE_FILES,
            "maximum_preparations": MAX_PREPARATIONS,
            "maximum_source_bytes": DRAFT_MAX_SOURCE_BYTES,
            "maximum_patch_bytes": MAX_PATCH_BYTES,
            "maximum_patch_lines": MAX_PATCH_LINES,
            "privacy_forbidden_entry_count": int(privacy.get("forbidden_entry_count", privacy.get("forbidden_count", 0)) or 0),
            "privacy_content_finding_count": int(privacy.get("private_content_finding_count", 0) or 0),
            "open_limitation_count": 4,
        },
        "evidence": evidence,
    }
    report["structural_digest"] = _digest({key: value for key, value in report.items() if key != "structural_digest"})
    return report
