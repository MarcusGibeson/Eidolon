from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
for path in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

from diagnostic_repair_reasoning_foundations import (
    DENIED_AUTHORITY,
    build_failure_observation,
    create_or_restore_diagnostic_plan,
    form_competing_explanations,
    load_diagnostic_plan,
    public_diagnostic_plan,
)
from isolated_coding_execution_foundations import create_or_restore_coding_work_request
from ordinary_chat_development_campaign import _atomic_json, _digest, _store_root
from v1255_test_support import make_project, tree_signature

CHECKS: list[str] = []


def require(value: object, label: str) -> None:
    if not value:
        raise AssertionError(label)
    CHECKS.append(label)


def source_signature() -> str:
    digest = hashlib.sha256()
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        if "__pycache__" in rel or rel.endswith((".pyc", ".pyo")) or rel.startswith("data/"):
            continue
        digest.update(rel.encode())
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def make_request(project: Path, runtime: Path) -> dict:
    return create_or_restore_coding_work_request(
        user_objective="Add subtraction while preserving addition.",
        target_project=project,
        requirements=["Add subtract(a,b)."],
        acceptance_criteria=["subtract(7,2) is 5"],
        constraints=["Keep current Python layout."],
        prohibited_actions=["No dependency installation."],
        ambiguities=["No UI requested."],
        assumptions=["Existing tests are authoritative."],
        expected_artifacts=["Reviewable diff", "Passing tests"],
        verification=["Run project tests"],
        runtime_root=runtime,
    )


def write_attempt(runtime: Path, request_id: str, attempt_number: int, *, status: str, command_results: list[dict], cleanup: bool = True) -> dict:
    verification = {
        "ok": True,
        "status": status,
        "request_id": request_id,
        "attempt_number": attempt_number,
        "project_type": "python_project",
        "passed": False,
        "tests_executed": True,
        "cleanup_confirmed": cleanup,
        "test_file_count": 2,
        "command_results": command_results,
        "raw_output_exposed": False,
        "private_content_exposed": False,
    }
    verification["verification_digest"] = _digest(verification)
    attempt = {
        "request_id": request_id,
        "attempt_number": attempt_number,
        "status": "isolated_coding_attempt_verified",
        "change_count": 1,
        "change_manifest_digest": _digest({"attempt": attempt_number, "fixture": status}),
        "changes": [{"relative_path_digest": "a" * 64, "operation": "modify", "content_digest": "b" * 64}],
        "verification": verification,
    }
    attempt["attempt_record_digest"] = _digest(attempt)
    _atomic_json(_store_root(runtime) / "isolated_coding_execution_attempts" / request_id / f"attempt-{attempt_number}.json", attempt)
    return attempt


SOURCE_BEFORE = source_signature()
with tempfile.TemporaryDirectory(prefix="eid-v1257-0-2-") as directory:
    base = Path(directory)
    runtime = base / "runtime"
    project = make_project(base)
    project_before = tree_signature(project)
    request = make_request(project, runtime)
    request_id = request["request_id"]

    write_attempt(runtime, request_id, 1, status="python_tests_failed", command_results=[
        {"phase": "syntax", "path_digest": "1" * 64, "passed": True, "exit_class": "zero", "output_digest": "2" * 64, "output_bytes": 0, "cleanup_confirmed": True, "duration_ms": 2},
        {"phase": "tests", "selection_digest": "3" * 64, "passed": False, "exit_class": "nonzero", "output_digest": "4" * 64, "output_bytes": 91, "cleanup_confirmed": True, "duration_ms": 9},
    ])
    observation = build_failure_observation(request_id, 1, runtime_root=runtime)
    require(observation["ok"] and observation["status"] == "diagnostic_failure_observation_ready", "failed_attempt_observation_built")
    require(observation["failed_phase_classes"] == ["tests"] and observation["failed_exit_classes"] == ["nonzero"], "failure_phase_and_exit_class_preserved")
    require(observation["verification_digest"] and observation["observation_digest"], "observation_bound_to_exact_verification")
    require(observation["raw_test_output_stored"] is False and "traceback" not in json.dumps(observation).lower(), "observation_content_minimized")
    require(str(project) not in json.dumps(observation), "project_path_not_exposed")

    hypotheses = form_competing_explanations(observation)
    codes = {row["hypothesis_code"] for row in hypotheses}
    require(len(hypotheses) >= 3, "multiple_competing_explanations_formed")
    require("implementation_behavior_defect" in codes and "preexisting_or_unrelated_test_failure" in codes and "test_environment_or_runner_issue" in codes, "implementation_baseline_environment_alternatives_preserved")
    require(all(row["root_cause_proven"] is False and row["disproof_test"] for row in hypotheses), "hypotheses_are_falsifiable_not_root_cause_claims")

    plan = create_or_restore_diagnostic_plan(request_id, 1, runtime_root=runtime)
    require(plan["ok"] and plan["status"] == "diagnostic_plan_ready", "bounded_diagnostic_plan_created")
    require(plan["hypothesis_count"] >= 3 and plan["diagnostic_probe_count"] >= 2, "plan_connects_hypotheses_to_diagnostics")
    require(any(row["probe_code"] == "individual_test_file_isolation" for row in plan["diagnostic_probes"]), "focused_test_isolation_planned")
    require(plan["completion_condition"] and plan["blocker_condition"], "completion_and_blocker_conditions_defined")
    for key, expected in DENIED_AUTHORITY.items():
        require(plan.get(key) is expected, f"plan_{key}_denied")
    require(plan["raw_test_output_stored"] is False and plan["private_content_stored"] is False, "plan_stores_no_private_or_raw_output")

    restored = create_or_restore_diagnostic_plan(request_id, 1, runtime_root=runtime)
    require(restored["operation_status"] == "restored" and restored["diagnostic_plan_digest"] == plan["diagnostic_plan_digest"], "duplicate_plan_idempotent")
    require(load_diagnostic_plan(request_id, 1, runtime_root=runtime)["diagnostic_plan_digest"] == plan["diagnostic_plan_digest"], "sealed_plan_loads")
    public = public_diagnostic_plan(plan)
    require(public["diagnostic_execution_authorized"] is False and public["repair_authorized"] is False, "public_plan_grants_no_authority")
    require("evidence_basis" not in json.dumps(public), "public_plan_is_content_minimized")

    # Syntax failures produce a different competing explanation set.
    write_attempt(runtime, request_id, 2, status="python_syntax_failed", command_results=[
        {"phase": "syntax", "path_digest": "5" * 64, "passed": False, "exit_class": "nonzero", "output_digest": "6" * 64, "output_bytes": 40, "cleanup_confirmed": True, "duration_ms": 3},
    ])
    syntax_plan = create_or_restore_diagnostic_plan(request_id, 2, runtime_root=runtime)
    syntax_codes = {row["hypothesis_code"] for row in syntax_plan["hypotheses"]}
    require("changed_source_syntax_defect" in syntax_codes and "verification_runtime_anomaly" in syntax_codes, "syntax_failure_has_competing_code_and_environment_explanations")
    require(any(row["probe_code"] == "failed_path_syntax_recheck" for row in syntax_plan["diagnostic_probes"]), "syntax_failure_gets_targeted_recheck")

    # Environment failure is represented honestly rather than mislabeled as code failure.
    write_attempt(runtime, request_id, 3, status="python_runtime_unavailable", command_results=[], cleanup=True)
    env_observation = build_failure_observation(request_id, 3, runtime_root=runtime)
    env_hypotheses = form_competing_explanations(env_observation)
    require(env_observation["environment_blocker_observed"] is True, "environment_blocker_observed")
    require(env_hypotheses[0]["hypothesis_code"] == "verification_environment_unavailable" and env_hypotheses[0]["repairable_in_isolated_workspace"] is False, "environment_blocker_not_claimed_as_code_repair")

    # Restart restores the exact same sealed plan without commands/providers.
    script = (
        "import json,sys;"
        f"sys.path.insert(0,{str(ROOT / 'conscious_agent')!r});"
        "from diagnostic_repair_reasoning_foundations import load_diagnostic_plan;"
        f"r=load_diagnostic_plan({request_id!r},1,runtime_root={str(runtime)!r});"
        "print(json.dumps({'digest':r.get('diagnostic_plan_digest'),'status':r.get('status')}))"
    )
    env = dict(os.environ); env["PYTHONDONTWRITEBYTECODE"] = "1"
    child = subprocess.run([sys.executable, "-I", "-B", "-c", script], cwd=ROOT, env=env, text=True, capture_output=True, timeout=30)
    require(child.returncode == 0 and json.loads(child.stdout)["digest"] == plan["diagnostic_plan_digest"], "restart_restores_exact_diagnostic_plan")

    # Tampered records fail closed.
    path = _store_root(runtime) / "diagnostic_repair_reasoning" / request_id / "attempt-1.json"
    tampered = json.loads(path.read_text(encoding="utf-8")); tampered["hypothesis_count"] = 99
    path.write_text(json.dumps(tampered), encoding="utf-8")
    require(load_diagnostic_plan(request_id, 1, runtime_root=runtime) == {}, "tampered_diagnostic_plan_rejected")
    require(create_or_restore_diagnostic_plan(request_id, 1, runtime_root=runtime)["status"] == "diagnostic_plan_record_invalid", "tampered_duplicate_fails_closed")
    require(tree_signature(project) == project_before, "foundations_never_modify_selected_project")

require(source_signature() == SOURCE_BEFORE, "foundation_suite_preserves_source_immutability")
print(json.dumps({
    "ok": True,
    "suite": "v1257.0-v1257.2-diagnostic-repair-reasoning-foundations",
    "passed": len(CHECKS),
    "failed": 0,
    "checks": CHECKS,
    "provider_contacted": False,
    "commands_executed": False,
    "repair_authorized": False,
    "application_authorized": False,
}, indent=2, sort_keys=True))
