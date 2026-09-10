from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "conscious_agent"))
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

from isolated_coding_execution_foundations import (
    AUTHORITY_STATE,
    cancel_coding_work_request,
    create_or_restore_coding_work_plan,
    create_or_restore_coding_work_request,
    inspect_coding_project,
    load_coding_project_inspection,
    load_coding_work_plan,
    load_coding_work_request,
    materialize_or_restore_isolated_coding_workspace,
)
from isolated_coding_execution import (
    EXECUTION_AUTHORITY,
    _apply_attempt,
    _execution_path,
    _load_or_generate_attempt,
    _seal,
    _workspace_root_from_record,
    authorize_and_run_isolated_coding_execution,
    load_isolated_coding_execution,
    prepare_isolated_coding_execution,
    process_isolated_coding_execution_control,
)
from isolated_coding_execution_reliability import (
    build_isolated_coding_operator_handoff,
    inspect_isolated_coding_execution_health,
)
from ordinary_chat_development_campaign import _atomic_json, _read_json, _store_root

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
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def source_signature() -> str:
    digest = hashlib.sha256()
    ignored = {".git", "data", "__pycache__", ".pytest_cache", ".venv", "venv"}
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or any(part in ignored for part in path.parts) or path.suffix in {".pyc", ".pyo"}:
            continue
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


SOURCE_BEFORE = source_signature()


def make_project(base: Path, *, two_sources: bool = False) -> Path:
    project = base / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text('[project]\nname="calculator"\nversion="0.1.0"\n', encoding="utf-8")
    (project / "main.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    if two_sources:
        (project / "helper.py").write_text("VALUE = 1\n", encoding="utf-8")
    (project / "tests").mkdir()
    (project / "tests" / "test_main.py").write_text(
        "import unittest\n"
        "from main import add, subtract\n\n"
        "class CalculatorTests(unittest.TestCase):\n"
        "    def test_add(self): self.assertEqual(add(2, 3), 5)\n"
        "    def test_subtract(self): self.assertEqual(subtract(7, 2), 5)\n\n"
        "if __name__ == '__main__': unittest.main()\n",
        encoding="utf-8",
    )
    (project / ".env").write_text("SECRET=DO_NOT_COPY\n", encoding="utf-8")
    return project


def prepare(project: Path, runtime: Path) -> tuple[dict, dict]:
    request = create_or_restore_coding_work_request(
        user_objective="Add subtraction while preserving addition.",
        target_project=project,
        requirements=["Add subtract(a, b).", "Preserve add(a, b)."],
        acceptance_criteria=["subtract(7,2) is 5", "add(2,3) is 5"],
        constraints=["Keep the existing project layout."],
        prohibited_actions=["Do not install dependencies."],
        expected_artifacts=["Reviewable isolated diff", "Passing bounded verification"],
        verification=["Compile Python", "Run project tests"],
        runtime_root=runtime,
    )
    require(request["ok"], "request_ready")
    inspection = inspect_coding_project(request["request_id"], runtime_root=runtime)
    require(inspection["ok"], "inspection_ready")
    require(create_or_restore_coding_work_plan(request["request_id"], runtime_root=runtime)["ok"], "plan_ready")
    workspace = materialize_or_restore_isolated_coding_workspace(request["request_id"], runtime_root=runtime)
    require(workspace["ok"], "workspace_ready")
    prepared = prepare_isolated_coding_execution(request["request_id"], runtime_root=runtime)
    require(prepared["ok"], "execution_prepared")
    return request, prepared


class CorrectProvider:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def __call__(self, prompt: str) -> str:
        payload = json.loads(prompt)
        self.calls.append(payload)
        authority = payload["authority"]
        return json.dumps({
            "authority": {
                "request_id": authority["request_id"],
                "execution_digest": authority["execution_digest"],
                "attempt": authority["attempt"],
            },
            "files": [{
                "path": "main.py",
                "operation": "modify",
                "content": "def add(a, b):\n    return a + b\n\ndef subtract(a, b):\n    return a - b\n",
            }],
        })


# Windows-portable path semantics: case-insensitive collisions and reserved names
# are rejected before any workspace is constructed.
with tempfile.TemporaryDirectory(prefix="eid-v1254-6-8-casefold-") as directory:
    base = Path(directory)
    runtime = base / "runtime"
    project = base / "project"
    project.mkdir()
    (project / "main.py").write_text("VALUE = 1\n", encoding="utf-8")
    (project / "MAIN.py").write_text("VALUE = 2\n", encoding="utf-8")
    request = create_or_restore_coding_work_request(user_objective="Inspect safely", target_project=project, runtime_root=runtime)
    try:
        # Supply directory entries explicitly: case-insensitive Windows cannot
        # physically hold this adversarial pair, but the scanner must reject it.
        entries = [SimpleNamespace(name=name, path=str(project / name),
                    is_dir=lambda **kw: False, is_file=lambda **kw: True)
                   for name in ("main.py", "MAIN.py")]
        scandir = os.scandir
        with patch("isolated_coding_execution_foundations.os.scandir",
                   side_effect=lambda p: entries if Path(p) == project else scandir(p)):
            inspect_coding_project(request["request_id"], runtime_root=runtime)
    except ValueError as exc:
        require(str(exc) == "project_casefold_path_collision", "windows_casefold_collision_rejected")
    else:
        raise AssertionError("windows_casefold_collision_rejected")

with tempfile.TemporaryDirectory(prefix="eid-v1254-6-8-reserved-") as directory:
    base = Path(directory)
    runtime = base / "runtime"
    project = base / "project"
    project.mkdir()
    request = create_or_restore_coding_work_request(user_objective="Inspect safely", target_project=project, runtime_root=runtime)
    try:
        entry = SimpleNamespace(name="NUL.txt", path=str(project / "NUL.txt"))
        scandir = os.scandir
        with patch("isolated_coding_execution_foundations.os.scandir",
                   side_effect=lambda p: [entry] if Path(p) == project else scandir(p)):
            inspect_coding_project(request["request_id"], runtime_root=runtime)
    except ValueError as exc:
        require(str(exc) == "windows_reserved_project_path", "windows_reserved_name_rejected")
    else:
        raise AssertionError("windows_reserved_name_rejected")

# Long but valid relative paths are not arbitrarily truncated at legacy MAX_PATH.
with tempfile.TemporaryDirectory(prefix="eid-v1254-6-8-long-") as directory:
    base = Path(directory)
    runtime = base / "runtime"
    project = base / "project"
    cursor = project
    for index in range(10):
        cursor = cursor / (f"segment_{index}_" + "x" * 18)
    cursor.mkdir(parents=True)
    target = cursor / "module.py"
    target.write_text("VALUE = 1\n", encoding="utf-8")
    relative = target.relative_to(project).as_posix()
    require(len(relative) > 260, "long_relative_path_fixture_exceeds_legacy_max_path")
    request = create_or_restore_coding_work_request(user_objective="Inspect long path", target_project=project, runtime_root=runtime)
    inspection = inspect_coding_project(request["request_id"], runtime_root=runtime)
    require(inspection["ok"] and relative in [row["relative_path"] for row in inspection["inventory"]], "long_portable_path_inspected_without_truncation")

# Materialized workspaces fail closed if private material or a link appears later.
with tempfile.TemporaryDirectory(prefix="eid-v1254-6-8-private-") as directory:
    base = Path(directory)
    runtime = base / "runtime"
    project = make_project(base)
    request, prepared = prepare(project, runtime)
    workspace = _read_json(_store_root(runtime) / "coding_workspace_records" / f"{request['request_id']}.json")
    workspace_root = _workspace_root_from_record(workspace)
    (workspace_root / ".env").write_text("SECRET=INJECTED\n", encoding="utf-8")
    blocked = prepare_isolated_coding_execution(request["request_id"], runtime_root=runtime)
    require(blocked["status"] == "isolated_coding_execution_workspace_changed", "post_materialization_private_file_blocks_execution")

with tempfile.TemporaryDirectory(prefix="eid-v1254-6-8-link-") as directory:
    base = Path(directory)
    runtime = base / "runtime"
    project = make_project(base)
    request, prepared = prepare(project, runtime)
    workspace = _read_json(_store_root(runtime) / "coding_workspace_records" / f"{request['request_id']}.json")
    workspace_root = _workspace_root_from_record(workspace)
    outside = base / "outside.py"
    outside.write_text("SECRET_OUTSIDE = 1\n", encoding="utf-8")
    try:
        os.symlink(outside, workspace_root / "linked.py")
    except (OSError, NotImplementedError):
        # The deterministic Windows reparse contract is covered by the shared
        # link-like helper; native junction creation belongs in Desktop review.
        require(True, "link_fixture_unavailable_native_review_required")
    else:
        blocked = prepare_isolated_coding_execution(request["request_id"], runtime_root=runtime)
        require(blocked["status"] == "isolated_coding_execution_workspace_changed", "post_materialization_link_blocks_execution")

# A provider cannot make a failing implementation pass by editing project-owned tests.
with tempfile.TemporaryDirectory(prefix="eid-v1254-6-8-tests-") as directory:
    base = Path(directory)
    runtime = base / "runtime"
    project = make_project(base)
    selected_before = tree_signature(project)
    request, prepared = prepare(project, runtime)
    calls: list[dict] = []

    def test_tampering_provider(prompt: str) -> str:
        payload = json.loads(prompt)
        calls.append(payload)
        authority = payload["authority"]
        return json.dumps({
            "authority": {"request_id": authority["request_id"], "execution_digest": authority["execution_digest"], "attempt": authority["attempt"]},
            "files": [{"path": "tests/test_main.py", "operation": "modify", "content": "# tests removed\n"}],
        })

    result = authorize_and_run_isolated_coding_execution(
        request["request_id"], expected_execution_digest=prepared["execution_digest"],
        authorization_phrase=prepared["authorization_phrase"], runtime_root=runtime,
        provider_generate=test_tampering_provider, python_executable=sys.executable,
    )
    require(result["status"] == "isolated_coding_generation_rejected", "existing_project_test_modification_rejected")
    require(len(calls) == 1, "test_tampering_provider_bounded_to_one_rejected_attempt")
    require(tree_signature(project) == selected_before, "test_tampering_never_modifies_selected_project")

# Preflight every change before writing any of them, so a conflict in a later
# file cannot leave an earlier file partially applied.
with tempfile.TemporaryDirectory(prefix="eid-v1254-6-8-atomic-") as directory:
    base = Path(directory)
    runtime = base / "runtime"
    project = make_project(base, two_sources=True)
    request, prepared = prepare(project, runtime)
    workspace_record = _read_json(_store_root(runtime) / "coding_workspace_records" / f"{request['request_id']}.json")
    workspace_root = _workspace_root_from_record(workspace_record)
    req = load_coding_work_request(request["request_id"], runtime_root=runtime)
    plan = load_coding_work_plan(request["request_id"], runtime_root=runtime)
    inspection = load_coding_project_inspection(request["request_id"], runtime_root=runtime)

    def two_file_provider(prompt: str) -> str:
        payload = json.loads(prompt)
        authority = payload["authority"]
        return json.dumps({
            "authority": {"request_id": authority["request_id"], "execution_digest": authority["execution_digest"], "attempt": authority["attempt"]},
            "files": [
                {"path": "main.py", "operation": "modify", "content": "def add(a, b):\n    return a + b\n\ndef subtract(a, b):\n    return a - b\n"},
                {"path": "helper.py", "operation": "modify", "content": "VALUE = 2\n"},
            ],
        })

    attempt = _load_or_generate_attempt(
        request=req, plan=plan, inspection=inspection, root=workspace_root,
        execution_digest=prepared["execution_digest"], attempt_number=1,
        previous_outcome=None, runtime_root=runtime, provider_generate=two_file_provider,
    )
    require(attempt.get("attempt_record_digest"), "two_file_attempt_sealed_before_apply")
    main_before = (workspace_root / "main.py").read_text(encoding="utf-8")
    (workspace_root / "helper.py").write_text("VALUE = 99\n", encoding="utf-8")
    blocked = _apply_attempt(attempt, runtime_root=runtime)
    require(blocked["status"] == "isolated_coding_workspace_apply_blocked", "late_file_conflict_blocks_entire_apply")
    require((workspace_root / "main.py").read_text(encoding="utf-8") == main_before, "preflight_prevents_partial_first_file_write")

# Crash/restart recovery restores a sealed generation attempt and does not make
# a duplicate provider call after an expired execution lease.
with tempfile.TemporaryDirectory(prefix="eid-v1254-6-8-recover-") as directory:
    base = Path(directory)
    runtime = base / "runtime"
    project = make_project(base)
    selected_before = tree_signature(project)
    request, prepared = prepare(project, runtime)
    workspace_record = _read_json(_store_root(runtime) / "coding_workspace_records" / f"{request['request_id']}.json")
    workspace_root = _workspace_root_from_record(workspace_record)
    req = load_coding_work_request(request["request_id"], runtime_root=runtime)
    plan = load_coding_work_plan(request["request_id"], runtime_root=runtime)
    inspection = load_coding_project_inspection(request["request_id"], runtime_root=runtime)
    provider = CorrectProvider()
    attempt = _load_or_generate_attempt(
        request=req, plan=plan, inspection=inspection, root=workspace_root,
        execution_digest=prepared["execution_digest"], attempt_number=1,
        previous_outcome=None, runtime_root=runtime, provider_generate=provider,
    )
    require(attempt.get("attempt_record_digest") and len(provider.calls) == 1, "precrash_generation_attempt_durably_sealed")
    execution = _read_json(_execution_path(request["request_id"], runtime))
    execution.update({
        "phase": "running", "status": "isolated_coding_execution_running",
        "lease_token": "expired-fixture-lease", "lease_expires_unix": 0.0,
        "execution_authority_consumed": True, "recovery_count": 0, **EXECUTION_AUTHORITY,
    })
    _atomic_json(_execution_path(request["request_id"], runtime), _seal(execution, "execution_record_digest"))
    health_before = inspect_isolated_coding_execution_health(request["request_id"], runtime_root=runtime)
    require(health_before["lease_expired"] and health_before["recovery_disposition"] == "same_exact_authorization_may_recover", "expired_lease_reports_bounded_recovery")
    require(health_before["application_authority_denied"], "running_recovery_keeps_application_authority_denied")
    recovered = authorize_and_run_isolated_coding_execution(
        request["request_id"], expected_execution_digest=prepared["execution_digest"],
        authorization_phrase=prepared["authorization_phrase"], runtime_root=runtime,
        provider_generate=provider, python_executable=sys.executable,
    )
    require(recovered["ok"] and recovered["operation_status"] == "recovered", "expired_execution_lease_recovers")
    require(recovered["recovery_count"] == 1, "recovery_count_recorded")
    require(len(provider.calls) == 1, "recovery_reuses_sealed_attempt_without_duplicate_provider_call")
    require(tree_signature(project) == selected_before, "recovery_never_modifies_selected_project")
    health_after = inspect_isolated_coding_execution_health(request["request_id"], runtime_root=runtime)
    require(health_after["ok"] and health_after["phase"] == "sealed", "completed_execution_health_is_clean")
    require(health_after["attempt_valid_count"] == 1 and health_after["review_valid"], "health_validates_attempt_and_review_digests")
    require(health_after["recovery_disposition"] == "terminal_review_available", "completed_execution_is_terminal_review_state")
    require(health_after["authority_denied"] and health_after["application_authority_denied"], "sealed_execution_returns_to_denied_authority")
    handoff = build_isolated_coding_operator_handoff(request["request_id"], runtime_root=runtime, include_diff=True)
    require(handoff["ok"] and handoff["status"] == "isolated_coding_operator_handoff_ready", "operator_handoff_ready")
    require("subtract" in handoff["review"]["diff"], "operator_handoff_contains_reviewable_diff")
    require(handoff["next_authority_stage"] == "v1255-controlled-application-and-rollback", "handoff_names_later_application_stage")
    require(not handoff["source_application_authorized"] and not handoff["release_authorized"], "handoff_grants_no_apply_or_release_authority")
    control = process_isolated_coding_execution_control(f"Review isolated coding request {request['request_id']}.", runtime_root=runtime)
    require(control["active"] and control["event"] == "isolated_coding_operator_handoff_ready", "ordinary_chat_exact_review_control_available")
    require("subtract" in control["operator_review"]["review"]["diff"], "ordinary_chat_review_returns_operator_diff")

# Cancellation cleans the disposable workspace and blocks later execution without
# contacting the provider.
with tempfile.TemporaryDirectory(prefix="eid-v1254-6-8-cancel-") as directory:
    base = Path(directory)
    runtime = base / "runtime"
    project = make_project(base)
    selected_before = tree_signature(project)
    request, prepared = prepare(project, runtime)
    workspace_record = _read_json(_store_root(runtime) / "coding_workspace_records" / f"{request['request_id']}.json")
    workspace_path = Path(workspace_record["workspace_path"])
    require(workspace_path.exists(), "cancellation_fixture_workspace_exists")
    cancelled = cancel_coding_work_request(request["request_id"], runtime_root=runtime)
    require(cancelled["ok"] and cancelled["workspace_cleaned"], "cancellation_cleans_workspace")
    require(not workspace_path.exists(), "cancelled_workspace_removed_deterministically")
    provider = CorrectProvider()
    blocked = authorize_and_run_isolated_coding_execution(
        request["request_id"], expected_execution_digest=prepared["execution_digest"],
        authorization_phrase=prepared["authorization_phrase"], runtime_root=runtime,
        provider_generate=provider, python_executable=sys.executable,
    )
    require(blocked["status"] == "isolated_coding_execution_cancelled", "cancelled_request_cannot_execute")
    require(len(provider.calls) == 0, "cancelled_request_never_contacts_provider")
    require(tree_signature(project) == selected_before, "cancellation_never_modifies_selected_project")

# If selected source changes during provider generation, the candidate stops
# before applying generated changes into the disposable workspace.
with tempfile.TemporaryDirectory(prefix="eid-v1254-6-8-race-") as directory:
    base = Path(directory)
    runtime = base / "runtime"
    project = make_project(base)
    request, prepared = prepare(project, runtime)
    workspace_record = _read_json(_store_root(runtime) / "coding_workspace_records" / f"{request['request_id']}.json")
    workspace_root = Path(workspace_record["workspace_path"])
    workspace_before = (workspace_root / "main.py").read_text(encoding="utf-8")
    calls: list[dict] = []

    def source_changing_provider(prompt: str) -> str:
        payload = json.loads(prompt)
        calls.append(payload)
        (project / "main.py").write_text("# operator changed selected source concurrently\n", encoding="utf-8")
        authority = payload["authority"]
        return json.dumps({
            "authority": {"request_id": authority["request_id"], "execution_digest": authority["execution_digest"], "attempt": authority["attempt"]},
            "files": [{"path": "main.py", "operation": "modify", "content": "def add(a, b):\n    return a + b\n\ndef subtract(a, b):\n    return a - b\n"}],
        })

    raced = authorize_and_run_isolated_coding_execution(
        request["request_id"], expected_execution_digest=prepared["execution_digest"],
        authorization_phrase=prepared["authorization_phrase"], runtime_root=runtime,
        provider_generate=source_changing_provider, python_executable=sys.executable,
    )
    require(raced["status"] == "stale_source_detected", "source_change_after_generation_blocks_workspace_apply")
    require(len(calls) == 1, "race_fixture_contacts_provider_once_before_stale_detection")
    require((workspace_root / "main.py").read_text(encoding="utf-8") == workspace_before, "stale_race_leaves_workspace_candidate_unapplied")

for key, expected in AUTHORITY_STATE.items():
    require(expected is False, f"foundation_authority_contract_{key}_remains_denied")
require(source_signature() == SOURCE_BEFORE, "eidolon_source_immutable_during_bundle_c_suite")

report = {
    "ok": True,
    "suite": "v1254.6-v1254.8-isolated-coding-execution-reliability",
    "passed": len(CHECKS),
    "failed": 0,
    "checks": CHECKS,
    "native_provider_contacted": False,
    "selected_project_application_authorized": False,
    "release_authorized": False,
    "independent_authority_granted": False,
    "native_windows_junction_validation": "desktop_review_required",
}
print(json.dumps(report, indent=2, sort_keys=True))
