from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
for path in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

from diagnostic_repair_reasoning import (
    _operation_path,
    _seal_operation,
    run_focused_diagnostics,
)
from diagnostic_repair_reasoning_foundations import load_diagnostic_result
from diagnostic_repair_reasoning_reliability import (
    build_diagnostic_repair_operator_handoff,
    inspect_diagnostic_repair_health,
)
from isolated_coding_execution import (
    EXECUTION_AUTHORITY,
    _execution_path,
    _seal as seal_execution,
    authorize_and_run_isolated_coding_execution,
    prepare_isolated_coding_execution,
)
from isolated_coding_execution_foundations import (
    cancel_coding_work_request,
    create_or_restore_coding_work_plan,
    create_or_restore_coding_work_request,
    inspect_coding_project,
    materialize_or_restore_isolated_coding_workspace,
)
from ordinary_chat_development_campaign import _atomic_json, _digest, _read_json, _store_root
from v1255_test_support import make_project, tree_signature

CHECKS: list[str] = []


def require(value: object, label: str) -> None:
    if not value:
        raise AssertionError(label)
    CHECKS.append(label)


def source_signature() -> str:
    rows = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        if "__pycache__" in rel or rel.endswith((".pyc", ".pyo")) or rel.startswith("data/"):
            continue
        rows.append((rel, hashlib.sha256(path.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()


def prepare(project: Path, runtime: Path) -> tuple[dict, dict]:
    request = create_or_restore_coding_work_request(
        user_objective="Add subtraction while preserving addition.", target_project=project,
        requirements=["Add subtract(a,b)."], acceptance_criteria=["subtract(7,2) is 5"],
        constraints=["Keep layout."], prohibited_actions=["No dependency installation."],
        expected_artifacts=["Reviewable diff", "Passing tests"], verification=["Run project tests"],
        runtime_root=runtime,
    )
    assert inspect_coding_project(request["request_id"], runtime_root=runtime)["ok"]
    assert create_or_restore_coding_work_plan(request["request_id"], runtime_root=runtime)["ok"]
    workspace = materialize_or_restore_isolated_coding_workspace(request["request_id"], runtime_root=runtime)
    assert workspace["ok"]
    prepared = prepare_isolated_coding_execution(request["request_id"], runtime_root=runtime)
    assert prepared["ok"]
    return request, prepared


def activate_failed_fixture(project: Path, runtime: Path) -> tuple[dict, dict]:
    request, prepared = prepare(project, runtime)
    request_id = request["request_id"]
    execution_path = _execution_path(request_id, runtime)
    execution = _read_json(execution_path)
    running = dict(execution)
    running.update({
        "phase": "running", "status": "isolated_coding_execution_running",
        "lease_token": "fixture-lease", "lease_expires_unix": time.time() + 600,
        "execution_authority_consumed": True, **EXECUTION_AUTHORITY,
    })
    _atomic_json(execution_path, seal_execution(running, "execution_record_digest"))
    workspace_record = _read_json(_store_root(runtime) / "coding_workspace_records" / f"{request_id}.json")
    workspace = Path(workspace_record["workspace_path"])
    wrong = "def add(a, b):\n    return a + b\n\ndef subtract(a, b):\n    return a + b\n"
    (workspace / "main.py").write_text(wrong, encoding="utf-8")
    verification = {
        "ok": True, "status": "python_tests_failed", "request_id": request_id, "attempt_number": 1,
        "project_type": "python_project", "passed": False, "tests_executed": True, "cleanup_confirmed": True,
        "test_file_count": 1,
        "command_results": [
            {"phase": "syntax", "path_digest": "a" * 64, "passed": True, "exit_class": "zero", "output_digest": "b" * 64, "output_bytes": 0, "cleanup_confirmed": True, "duration_ms": 1},
            {"phase": "tests", "selection_digest": "c" * 64, "passed": False, "exit_class": "nonzero", "output_digest": "d" * 64, "output_bytes": 20, "cleanup_confirmed": True, "duration_ms": 3},
        ],
    }
    verification["verification_digest"] = _digest(verification)
    attempt = {
        "request_id": request_id, "execution_digest": prepared["execution_digest"], "attempt_number": 1,
        "status": "isolated_coding_attempt_verified", "change_count": 1,
        "change_manifest_digest": _digest([{"path": "main.py", "content": hashlib.sha256(wrong.encode()).hexdigest()}]),
        "changes": [{
            "relative_path": "main.py", "relative_path_digest": hashlib.sha256(b"main.py").hexdigest(),
            "operation": "modify", "content_digest": hashlib.sha256(wrong.encode()).hexdigest(),
        }],
        "verification": verification,
    }
    attempt["attempt_record_digest"] = _digest(attempt)
    _atomic_json(_store_root(runtime) / "isolated_coding_execution_attempts" / request_id / "attempt-1.json", attempt)
    return request, prepared


class RepeatingWrongProvider:
    def __init__(self) -> None:
        self.calls = 0
    def __call__(self, prompt: str) -> str:
        payload = json.loads(prompt); self.calls += 1; a = payload["authority"]
        body = "def add(a, b):\n    return a + b\n\ndef subtract(a, b):\n    return a + b\n"
        return json.dumps({"authority": {"request_id": a["request_id"], "execution_digest": a["execution_digest"], "attempt": a["attempt"]}, "files": [{"path": "main.py", "operation": "modify", "content": body}]})


SOURCE_BEFORE = source_signature()
# Repeated identical repair approaches stop before a third provider call.
with tempfile.TemporaryDirectory(prefix="eid-v1257-6-8-repeat-") as directory:
    base = Path(directory); runtime = base / "runtime"; project = make_project(base); before = tree_signature(project)
    request, prepared = prepare(project, runtime); provider = RepeatingWrongProvider()
    result = authorize_and_run_isolated_coding_execution(
        request["request_id"], expected_execution_digest=prepared["execution_digest"], authorization_phrase=prepared["authorization_phrase"],
        runtime_root=runtime, provider_generate=provider, python_executable=sys.executable,
    )
    require(result["ok"] is False and "blocked_repeated_failed_repair" in result["status"], "repeated_failed_repair_becomes_terminal_blocker")
    require(provider.calls == 2 and result["attempt_count"] == 2, "repeated_strategy_stops_before_third_provider_call")
    require(result["diagnostic_cycle_count"] == 2, "both_failed_attempts_have_diagnostic_cycles")
    second = load_diagnostic_result(request["request_id"], 2, runtime_root=runtime)
    require(second["repeated_failed_repair"] is True and second["repair_supported"] is False, "second_diagnosis_marks_repeated_strategy")
    require(tree_signature(project) == before, "repeated_repair_block_preserves_selected_project")
    health = inspect_diagnostic_repair_health(request["request_id"], runtime_root=runtime)
    require(health["ok"] and health["failed_attempt_count"] == 2 and health["diagnostic_count"] == 2, "health_inspection_validates_complete_diagnostic_chain")
    require(any("repeated_failed_repair" in warning for warning in health["warnings"]), "health_surfaces_repeated_repair_warning")
    handoff = build_diagnostic_repair_operator_handoff(request["request_id"], runtime_root=runtime)
    require(handoff["ok"] and handoff["diagnostic_cycle_count"] == 2, "operator_handoff_preserves_bounded_diagnostic_history")
    require(handoff["read_only"] and handoff["provider_contacted_by_handoff"] is False and handoff["tests_executed_by_handoff"] is False, "handoff_is_read_only")

# Active operation blocks a duplicate diagnostic command campaign.
with tempfile.TemporaryDirectory(prefix="eid-v1257-6-8-live-") as directory:
    base = Path(directory); runtime = base / "runtime"; project = make_project(base); before = tree_signature(project)
    request, prepared = activate_failed_fixture(project, runtime); request_id = request["request_id"]
    # Build the provider-free plan before placing the synthetic live lease.
    from diagnostic_repair_reasoning_foundations import create_or_restore_diagnostic_plan
    assert create_or_restore_diagnostic_plan(request_id, 1, runtime_root=runtime)["ok"]
    operation = {
        "ok": True, "schema_version": "1", "contract_version": "v1257.5", "status": "diagnostic_operation_running", "phase": "running",
        "request_id": request_id, "attempt_number": 1, "expected_execution_digest": prepared["execution_digest"],
        "lease_token": "other-worker", "lease_expires_unix": time.time() + 300, "recovery_count": 0,
        "provider_contacted": False, "selected_project_modified": False, "source_modified": False,
    }
    _atomic_json(_operation_path(request_id, 1, runtime), _seal_operation(operation))
    duplicate = run_focused_diagnostics(request_id, 1, expected_execution_digest=prepared["execution_digest"], runtime_root=runtime, python_executable=sys.executable)
    require(duplicate["status"] == "diagnostic_operation_in_progress", "live_diagnostic_lease_blocks_duplicate_commands")
    require(not load_diagnostic_result(request_id, 1, runtime_root=runtime), "live_duplicate_does_not_forge_result")
    require(tree_signature(project) == before, "live_duplicate_preserves_selected_project")

# Expired diagnostic operation recovers under one new lease and seals one result.
with tempfile.TemporaryDirectory(prefix="eid-v1257-6-8-expired-") as directory:
    base = Path(directory); runtime = base / "runtime"; project = make_project(base); before = tree_signature(project)
    request, prepared = activate_failed_fixture(project, runtime); request_id = request["request_id"]
    operation = {
        "ok": True, "schema_version": "1", "contract_version": "v1257.5", "status": "diagnostic_operation_running", "phase": "running",
        "request_id": request_id, "attempt_number": 1, "expected_execution_digest": prepared["execution_digest"],
        "lease_token": "crashed-worker", "lease_expires_unix": time.time() - 5, "recovery_count": 0,
        "provider_contacted": False, "selected_project_modified": False, "source_modified": False,
    }
    _atomic_json(_operation_path(request_id, 1, runtime), _seal_operation(operation))
    recovered = run_focused_diagnostics(request_id, 1, expected_execution_digest=prepared["execution_digest"], runtime_root=runtime, python_executable=sys.executable)
    require(recovered["ok"] and recovered["operation_status"] == "recovered", "expired_diagnostic_operation_recovers")
    require(recovered["operation_recovery_count"] == 1, "diagnostic_recovery_count_recorded")
    replay = run_focused_diagnostics(request_id, 1, expected_execution_digest=prepared["execution_digest"], runtime_root=runtime, python_executable=sys.executable)
    require(replay["operation_status"] == "restored" and replay["diagnostic_result_digest"] == recovered["diagnostic_result_digest"], "recovered_diagnosis_replays_without_commands")
    require(tree_signature(project) == before, "expired_recovery_preserves_selected_project")

# Stale source and cancellation block before starting diagnostic operations.
with tempfile.TemporaryDirectory(prefix="eid-v1257-6-8-stale-") as directory:
    base = Path(directory); runtime = base / "runtime"; project = make_project(base)
    request, prepared = activate_failed_fixture(project, runtime); request_id = request["request_id"]
    (project / "README.md").write_text("operator changed source\n", encoding="utf-8")
    stale = run_focused_diagnostics(request_id, 1, expected_execution_digest=prepared["execution_digest"], runtime_root=runtime, python_executable=sys.executable)
    require(stale["status"] == "diagnostic_stale_source_detected", "stale_source_blocks_diagnostics_before_commands")
    require(not _operation_path(request_id, 1, runtime).exists(), "stale_source_creates_no_diagnostic_lease")

with tempfile.TemporaryDirectory(prefix="eid-v1257-6-8-cancel-") as directory:
    base = Path(directory); runtime = base / "runtime"; project = make_project(base); before = tree_signature(project)
    request, prepared = activate_failed_fixture(project, runtime); request_id = request["request_id"]
    cancel_coding_work_request(request_id, runtime_root=runtime)
    cancelled = run_focused_diagnostics(request_id, 1, expected_execution_digest=prepared["execution_digest"], runtime_root=runtime, python_executable=sys.executable)
    require(cancelled["status"] == "diagnostic_request_cancelled_or_missing", "cancellation_blocks_diagnostic_execution")
    require(not _operation_path(request_id, 1, runtime).exists(), "cancelled_request_creates_no_diagnostic_lease")
    require(tree_signature(project) == before, "cancelled_diagnostics_preserve_selected_project")

# Tampered result is rejected before any recovery work, even when an execution remains live.
with tempfile.TemporaryDirectory(prefix="eid-v1257-6-8-tamper-") as directory:
    base = Path(directory); runtime = base / "runtime"; project = make_project(base); before = tree_signature(project)
    request, prepared = activate_failed_fixture(project, runtime); request_id = request["request_id"]
    good = run_focused_diagnostics(request_id, 1, expected_execution_digest=prepared["execution_digest"], runtime_root=runtime, python_executable=sys.executable)
    require(good["ok"], "diagnostic_result_created_before_tamper")
    result_path = _store_root(runtime) / "diagnostic_repair_results" / request_id / "attempt-1.json"
    tampered = json.loads(result_path.read_text(encoding="utf-8")); tampered["preferred_hypothesis_code"] = "forged_root_cause"
    result_path.write_text(json.dumps(tampered), encoding="utf-8")
    blocked = run_focused_diagnostics(request_id, 1, expected_execution_digest=prepared["execution_digest"], runtime_root=runtime, python_executable=sys.executable)
    require(blocked["status"] == "diagnostic_result_record_invalid", "tampered_diagnostic_result_fails_closed_before_rerun")
    health = inspect_diagnostic_repair_health(request_id, runtime_root=runtime)
    require(health["ok"] is False and any("diagnostic_result_1" in error for error in health["errors"]), "health_reports_tampered_diagnostic_result")
    require(tree_signature(project) == before, "tamper_handling_preserves_selected_project")

# Deep runtime roots remain functional without leaking their path through public evidence.
with tempfile.TemporaryDirectory(prefix="eid-v1257-6-8-long-") as directory:
    base = Path(directory); runtime = base
    for index in range(12): runtime = runtime / ("runtime_segment_" + str(index).zfill(2) + "_" + "x" * 12)
    project = make_project(base); before = tree_signature(project)
    request, prepared = activate_failed_fixture(project, runtime)
    result = run_focused_diagnostics(request["request_id"], 1, expected_execution_digest=prepared["execution_digest"], runtime_root=runtime, python_executable=sys.executable)
    require(result["ok"] and result["diagnostic_result_digest"], "long_runtime_path_diagnostics_complete")
    public = build_diagnostic_repair_operator_handoff(request["request_id"], runtime_root=runtime)
    require(str(runtime) not in json.dumps(public) and str(project) not in json.dumps(public), "operator_handoff_exposes_no_runtime_or_project_paths")
    require(tree_signature(project) == before, "long_path_diagnostics_preserve_selected_project")

require(source_signature() == SOURCE_BEFORE, "reliability_suite_preserves_source_immutability")
print(json.dumps({
    "ok": True,
    "suite": "v1257.6-v1257.8-diagnostic-repair-reasoning-reliability",
    "passed": len(CHECKS), "failed": 0, "checks": CHECKS,
    "provider_repair_repetition_stopped": True,
    "native_windows_cross_process_validation": "desktop_review_required",
    "selected_project_modified": False,
}, indent=2, sort_keys=True))
