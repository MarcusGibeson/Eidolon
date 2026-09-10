from __future__ import annotations

import hashlib
import importlib
import json
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "conscious_agent"))
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

from isolated_coding_execution_foundations import (
    AUTHORITY_STATE,
    PREPARATION_CAPABILITIES,
    _is_link_like,
    _safe_relative,
    cancel_coding_work_request,
    check_coding_source_freshness,
    create_or_restore_coding_work_plan,
    create_or_restore_coding_work_request,
    inspect_coding_project,
    load_coding_work_request,
    materialize_or_restore_isolated_coding_workspace,
    public_coding_project_inspection,
    public_coding_work_plan,
    public_coding_work_request,
    public_isolated_coding_workspace,
)

CHECKS: list[str] = []


def require(value: object, label: str) -> None:
    if not value:
        raise AssertionError(label)
    CHECKS.append(label)


def tree_signature(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def assert_authority_denied(record: dict, prefix: str) -> None:
    for key, expected in AUTHORITY_STATE.items():
        require(record.get(key) is expected, f"{prefix}_{key}_denied")


def source_signature() -> str:
    digest = hashlib.sha256()
    ignored = {".git", "data", "__pycache__", ".pytest_cache", ".venv", "venv"}
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or any(part in ignored for part in path.parts) or path.suffix in {".pyc", ".pyo"}:
            continue
        digest.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


SOURCE_BEFORE = source_signature()


with tempfile.TemporaryDirectory(prefix="eid-v1254-0-2-") as directory:
    base = Path(directory)
    project = base / "project"
    runtime = base / "runtime"
    external = base / "external"
    project.mkdir()
    external.mkdir()
    (project / "pyproject.toml").write_text('[project]\nname="fixture"\nversion="0.1.0"\n', encoding="utf-8")
    (project / "main.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (project / "tests").mkdir()
    (project / "tests" / "test_main.py").write_text("from main import add\n\ndef test_add(): assert add(2,3)==5\n", encoding="utf-8")
    (project / ".env").write_text("SECRET=DO_NOT_COPY\n", encoding="utf-8")
    (project / "data").mkdir()
    (project / "data" / "projects.json").write_text('{"private":true}\n', encoding="utf-8")
    (project / "conversations").mkdir()
    (project / "conversations" / "session.json").write_text('{"message":"private"}\n', encoding="utf-8")
    (external / "outside.py").write_text("OUTSIDE = True\n", encoding="utf-8")
    symlink_created = False
    try:
        (project / "linked-outside").symlink_to(external, target_is_directory=True)
        symlink_created = True
    except (OSError, NotImplementedError):
        pass

    before = tree_signature(project)
    request = create_or_restore_coding_work_request(
        user_objective="Add subtraction while preserving addition.",
        target_project=project,
        requirements=["Add a subtract(a, b) function in the calculator source."],
        acceptance_criteria=["Addition still works.", "Subtraction returns the arithmetic difference."],
        constraints=["Use the existing Python project layout."],
        prohibited_actions=["Do not install dependencies."],
        ambiguities=["No CLI behavior is requested."],
        assumptions=["main.py is the intended calculator module."],
        expected_artifacts=["Updated isolated main.py", "Focused test evidence", "Reviewable diff"],
        verification=["Compile Python", "Run focused calculator tests"],
        runtime_root=runtime,
    )
    require(request["ok"] and request["status"] == "coding_work_request_ready", "request_contract_ready")
    require(request["user_objective"].startswith("Add subtraction"), "request_objective_recorded")
    require(request["target"]["path_digest"] and request["target"]["private_path"] == str(project.resolve()), "request_target_recorded")
    require(len(request["requirements"]) == 1 and len(request["acceptance_criteria"]) == 2, "request_requirements_acceptance_recorded")
    require(request["constraints"] and len(request["prohibited_actions"]) >= 4, "request_constraints_prohibitions_recorded")
    require(request["ambiguities"] and request["assumptions"], "request_ambiguity_assumption_recorded")
    require(request["expected_artifacts"] and request["verification"], "request_artifacts_verification_recorded")
    assert_authority_denied(request, "request")
    require(all(PREPARATION_CAPABILITIES.values()), "preparation_capabilities_explicitly_enabled")
    require(request["preparation_capabilities"] == PREPARATION_CAPABILITIES, "request_separates_preparation_from_authority")
    public_request = public_coding_work_request(request)
    require(public_request["private_path_exposed"] is False and public_request["request_text_exposed"] is False, "request_public_projection_private_safe")

    duplicate = create_or_restore_coding_work_request(
        user_objective="Add subtraction while preserving addition.",
        target_project=project,
        requirements=["Add a subtract(a, b) function in the calculator source."],
        acceptance_criteria=["Addition still works.", "Subtraction returns the arithmetic difference."],
        constraints=["Use the existing Python project layout."],
        prohibited_actions=["Do not install dependencies."],
        ambiguities=["No CLI behavior is requested."],
        assumptions=["main.py is the intended calculator module."],
        expected_artifacts=["Updated isolated main.py", "Focused test evidence", "Reviewable diff"],
        verification=["Compile Python", "Run focused calculator tests"],
        runtime_root=runtime,
    )
    require(duplicate["operation_status"] == "restored", "duplicate_request_idempotent_restore")
    require(duplicate["request_id"] == request["request_id"] and duplicate["request_digest"] == request["request_digest"], "duplicate_request_same_identity")

    inspection = inspect_coding_project(request["request_id"], runtime_root=runtime)
    require(inspection["ok"] and inspection["project_type"] == "python_project", "project_type_identified")
    paths = {row["relative_path"] for row in inspection["inventory"]}
    require({"pyproject.toml", "main.py", "tests/test_main.py"}.issubset(paths), "relevant_source_inventory_present")
    require(".env" not in paths and "data/projects.json" not in paths and "conversations/session.json" not in paths, "private_runtime_data_excluded")
    if symlink_created:
        require("linked-outside/outside.py" not in paths and inspection["link_or_boundary_rejection_count"] >= 1, "symlink_escape_not_scanned")
    public_inspection = public_coding_project_inspection(inspection)
    require(public_inspection["raw_paths_exposed"] is False and public_inspection["private_path_exposed"] is False, "inspection_projection_content_minimized")
    require(len(public_inspection["file_path_digests"]) == inspection["file_count"], "inspection_projection_structural_evidence")
    assert_authority_denied(public_inspection, "inspection")

    try:
        _safe_relative("../outside.py")
        raise AssertionError("path traversal was accepted")
    except ValueError:
        CHECKS.append("path_traversal_rejected")
    try:
        _safe_relative("data/projects.json")
        raise AssertionError("private data relative path was accepted")
    except ValueError:
        CHECKS.append("private_relative_path_rejected")

    fake_stat = SimpleNamespace(st_file_attributes=0x400)
    with patch("isolated_coding_execution_foundations.Path.is_symlink", return_value=False), patch("isolated_coding_execution_foundations.os.lstat", return_value=fake_stat):
        require(_is_link_like(Path("junction-probe")) is True, "windows_junction_reparse_point_rejected")

    plan = create_or_restore_coding_work_plan(request["request_id"], runtime_root=runtime)
    require(plan["ok"] and plan["status"] == "coding_work_plan_ready", "bounded_plan_ready")
    require(plan["requirement_file_links"] and plan["implementation_steps"], "plan_connects_requirements_files_steps")
    require(plan["verification_plan"] == request["verification"], "plan_connects_verification")
    require(plan["assumptions"] and plan["ambiguities"], "plan_records_assumptions_uncertainty")
    require(plan["completion_conditions"] and plan["blocker_conditions"], "plan_completion_blockers_defined")
    require(plan["plan_grants_execution_authority"] is False and plan["plan_grants_application_authority"] is False, "plan_cannot_grant_authority")
    assert_authority_denied(plan, "plan")
    assert_authority_denied(public_coding_work_plan(plan), "public_plan")

    workspace = materialize_or_restore_isolated_coding_workspace(request["request_id"], runtime_root=runtime)
    require(workspace["ok"] and workspace["status"] == "isolated_coding_workspace_ready", "isolated_workspace_materialized")
    workspace_path = Path(workspace["workspace_path"])
    require(workspace_path.is_dir() and runtime.resolve() in workspace_path.resolve().parents, "workspace_external_to_selected_project")
    require(tree_signature(project) == before, "selected_project_immutable_during_workspace_creation")
    workspace_paths = {row["relative_path"] for row in workspace["files"]}
    require(workspace_paths == paths, "workspace_matches_inspected_inventory")
    require(not (workspace_path / ".env").exists() and not (workspace_path / "data").exists() and not (workspace_path / "conversations").exists(), "workspace_private_data_absent")
    require(workspace["source_manifest_digest"] == inspection["source_manifest_digest"], "source_workspace_manifest_bound")
    require(workspace["reviewable_result_only"] and workspace["cleanup_supported"], "workspace_reviewable_disposable_result")
    assert_authority_denied(workspace, "workspace")
    assert_authority_denied(public_isolated_coding_workspace(workspace), "public_workspace")

    workspace_again = materialize_or_restore_isolated_coding_workspace(request["request_id"], runtime_root=runtime)
    require(workspace_again["operation_status"] == "restored" and workspace_again["workspace_record_digest"] == workspace["workspace_record_digest"], "workspace_idempotent_restore")

    # Restart-safe restoration is file-backed, not process-memory-backed.
    import isolated_coding_execution_foundations as foundations
    importlib.reload(foundations)
    restored_after_reload = foundations.load_coding_work_request(request["request_id"], runtime_root=runtime)
    require(restored_after_reload.get("request_digest") == request["request_digest"], "restart_safe_request_restoration")

    cancelled = foundations.cancel_coding_work_request(request["request_id"], runtime_root=runtime)
    require(cancelled["ok"] and cancelled["workspace_cleaned"], "cancellation_cleanup_succeeds")
    require(not workspace_path.exists(), "cancellation_removes_disposable_workspace")
    cancelled_request = foundations.load_coding_work_request(request["request_id"], runtime_root=runtime)
    require(cancelled_request["cancelled"] and cancelled_request["lifecycle_state"] == "cancelled", "cancellation_state_persisted")
    blocked_after_cancel = foundations.materialize_or_restore_isolated_coding_workspace(request["request_id"], runtime_root=runtime)
    require(blocked_after_cancel["status"] == "coding_work_request_cancelled", "cancelled_request_cannot_rematerialize")

    # Separate fixture proves staleness blocks planning/workspace preparation.
    stale_project = base / "stale-project"
    stale_project.mkdir()
    (stale_project / "main.py").write_text("VALUE = 1\n", encoding="utf-8")
    stale_request = foundations.create_or_restore_coding_work_request(
        user_objective="Change VALUE to 2.", target_project=stale_project,
        requirements=["Change VALUE to 2."], acceptance_criteria=["VALUE equals 2."],
        runtime_root=runtime,
    )
    stale_inspection = foundations.inspect_coding_project(stale_request["request_id"], runtime_root=runtime)
    require(stale_inspection["ok"], "stale_fixture_inspected")
    (stale_project / "main.py").write_text("VALUE = 99\n", encoding="utf-8")
    freshness = foundations.check_coding_source_freshness(stale_request["request_id"], runtime_root=runtime)
    require(not freshness["ok"] and freshness["status"] == "stale_source_detected" and freshness["stale_source"], "stale_source_detected")
    stale_plan = foundations.create_or_restore_coding_work_plan(stale_request["request_id"], runtime_root=runtime)
    require(stale_plan["status"] == "stale_source_detected", "stale_source_blocks_plan")

    require(tree_signature(project) == before, "selected_project_immutable_after_full_flow")

from release_authority import AUTHORITATIVE_BASELINE_ARCHIVE_SHA256, PREVIOUS_WORKING_SOURCE_VERSION, WORKING_SOURCE_VERSION, validate_release_authority
from checkpoint_registry import lookup_checkpoint
require(tuple(int(part) for part in WORKING_SOURCE_VERSION.split(".")) >= (1254, 2) and PREVIOUS_WORKING_SOURCE_VERSION, "release_metadata_at_or_beyond_bundle_a")
require(AUTHORITATIVE_BASELINE_ARCHIVE_SHA256 == "23672742f8fa121e50937c0833cf4066f146f0d0dc46056640ce4e0831b3b19f", "authoritative_baseline_hash_recorded")
require(validate_release_authority(source_root=ROOT)["ok"], "release_authority_consistent")
for version in ("1254.0", "1254.1", "1254.2"):
    row = lookup_checkpoint(version)
    require(row is not None and row.test_selector == "tools/v1254_0_2_isolated_coding_execution_foundations_tests.py", f"checkpoint_{version}_registered")
next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
require(f"Current source: v{WORKING_SOURCE_VERSION}" in next_steps and "v1255" in next_steps, "next_steps_current_and_bounded")
require(all(f"## v{version}" in history for version in ("1254.0", "1254.1", "1254.2")), "release_history_bundle_complete")
require(source_signature() == SOURCE_BEFORE, "eidolon_source_immutable_during_focused_suite")

report = {
    "ok": True,
    "suite": "v1254.0-v1254.2-isolated-coding-execution-foundations",
    "passed": len(CHECKS),
    "total": len(CHECKS),
    "checks": CHECKS,
    "provider_contacted": False,
    "commands_executed_by_product": False,
    "tests_executed_by_product": False,
    "selected_project_modified": False,
    "source_application_authorized": False,
    "release_authorized": False,
    "independent_authority_granted": False,
}
print(json.dumps(report, indent=2 if "--json" in sys.argv else None, sort_keys=True))
