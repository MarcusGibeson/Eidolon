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

from ordinary_chat_development_campaign import _atomic_json, _digest, _store_root
from isolated_coding_execution_foundations import (
    cancel_coding_work_request,
    create_or_restore_coding_work_plan,
    create_or_restore_coding_work_request,
    inspect_coding_project,
    load_coding_work_request,
    materialize_or_restore_isolated_coding_workspace,
)
from isolated_coding_execution import prepare_isolated_coding_execution
from persistent_development_sessions_foundations import (
    DENIED_AUTHORITY,
    build_persistent_development_session_snapshot,
    create_or_restore_persistent_development_session,
    load_persistent_development_session,
    public_persistent_development_session,
    refresh_persistent_development_session,
)
from v1255_test_support import make_project, tree_signature

CHECKS: list[str] = []


def require(value: object, label: str) -> None:
    if not value:
        raise AssertionError(label)
    CHECKS.append(label)


def source_signature() -> str:
    digest = hashlib.sha256()
    ignored = {".git", "data", "__pycache__", ".pytest_cache", ".venv", "venv"}
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or any(part in ignored for part in path.parts) or path.suffix in {".pyc", ".pyo"}:
            continue
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def prepare_foundation(project: Path, runtime: Path) -> dict:
    request = create_or_restore_coding_work_request(
        user_objective="Add subtraction while preserving addition.",
        target_project=project,
        requirements=["Add subtract(a, b).", "Preserve add(a, b)."],
        acceptance_criteria=["subtract(7,2) is 5", "add(2,3) is 5"],
        constraints=["Keep the current Python layout."],
        prohibited_actions=["Do not install dependencies."],
        ambiguities=["No UI changes are requested."],
        assumptions=["Existing tests remain authoritative."],
        expected_artifacts=["Reviewable diff", "Passing tests"],
        verification=["Compile Python", "Run project tests"],
        runtime_root=runtime,
    )
    assert request["ok"]
    assert inspect_coding_project(request["request_id"], runtime_root=runtime)["ok"]
    assert create_or_restore_coding_work_plan(request["request_id"], runtime_root=runtime)["ok"]
    assert materialize_or_restore_isolated_coding_workspace(request["request_id"], runtime_root=runtime)["ok"]
    return request


SOURCE_BEFORE = source_signature()

with tempfile.TemporaryDirectory(prefix="eid-v1256-0-2-") as directory:
    base = Path(directory)
    runtime = base / "runtime"
    project = make_project(base)
    project_before = tree_signature(project)
    request = prepare_foundation(project, runtime)
    request_id = request["request_id"]

    session = create_or_restore_persistent_development_session(request_id, runtime_root=runtime)
    require(session["ok"] and session["status"] == "persistent_development_session_ready", "persistent_session_created")
    require(session["session_id"].startswith("devs_") and len(session["session_id"]) == 29, "deterministic_session_id_shape")
    require(session["phase"] == "workspace_ready" and session["next_action"] == "prepare_isolated_execution", "foundation_phase_reconstructed")
    require(session["generation"] == 1 and not session["prior_session_digest"], "first_generation_rooted")
    require(session["snapshot"]["requirements_digest"] and session["snapshot"]["acceptance_criteria_digest"], "requirements_and_acceptance_preserved_by_digest")
    require(session["snapshot"]["artifact_refs"]["plan_digest"], "plan_lineage_preserved")
    require(session["snapshot"]["artifact_refs"]["workspace_digest"], "workspace_lineage_preserved")
    require(session["snapshot"]["private_project_path_stored"] is False and session["snapshot"]["private_content_stored"] is False, "session_snapshot_content_minimized")
    for key, expected in DENIED_AUTHORITY.items():
        require(session.get(key) is expected, f"session_{key}_denied")

    restored = create_or_restore_persistent_development_session(request_id, runtime_root=runtime)
    require(restored["operation_status"] == "restored" and restored["session_id"] == session["session_id"], "duplicate_request_restores_same_session")
    require(restored["session_digest"] == session["session_digest"], "duplicate_request_session_digest_stable")

    loaded = load_persistent_development_session(session["session_id"], runtime_root=runtime)
    require(loaded["session_digest"] == session["session_digest"], "session_load_validates_digest_and_index")
    public = public_persistent_development_session(loaded)
    require(public["requirements_preserved"] and public["plan_preserved"], "public_projection_reports_requirements_and_plan_continuity")
    require(public["private_project_path_exposed"] is False and public["private_content_exposed"] is False, "public_projection_private_safe")
    require("workspace_path" not in json.dumps(public) and str(project) not in json.dumps(public), "public_projection_omits_project_path")

    # Provider-free preparation is enough to advance the durable session. The
    # session surfaces the existing exact authorization requirement but cannot consume it.
    prepared = prepare_isolated_coding_execution(request_id, runtime_root=runtime)
    require(prepared["ok"] and prepared["status"] == "isolated_coding_execution_authorization_required", "isolated_execution_prepared_without_provider")
    refreshed = refresh_persistent_development_session(session["session_id"], runtime_root=runtime)
    require(refreshed["operation_status"] == "updated" and refreshed["generation"] == 2, "session_refresh_records_new_generation")
    require(refreshed["prior_session_digest"] == session["session_digest"], "session_generation_links_prior_digest")
    require(refreshed["phase"] == "execution_authorization_required", "prepared_execution_phase_restored")
    require(refreshed["next_action"] == "authorize_existing_isolated_execution", "resume_points_to_existing_authorization_not_new_execution")
    require(refreshed["automatic_resume_authorized"] is False and refreshed["duplicate_execution_authorized"] is False, "refresh_never_grants_resume_or_duplicate_execution")

    # Deterministic content-minimized attempt/verification evidence fixture.
    attempt = {
        "request_id": request_id,
        "attempt_number": 1,
        "mode": "initial_implementation",
        "status": "isolated_coding_attempt_verified",
        "change_count": 1,
        "verification": {
            "status": "python_tests_failed",
            "tests_executed": True,
            "passed": False,
            "cleanup_confirmed": True,
            "verification_digest": "a" * 64,
        },
        "raw_provider_output_stored": False,
        "raw_test_output_stored": False,
    }
    attempt["attempt_record_digest"] = _digest(attempt)
    _atomic_json(_store_root(runtime) / "isolated_coding_execution_attempts" / request_id / "attempt-1.json", attempt)
    evidence_refresh = refresh_persistent_development_session(session["session_id"], runtime_root=runtime)
    require(evidence_refresh["attempt_count"] == 1, "attempt_count_persisted")
    evidence = evidence_refresh["snapshot"]["attempt_evidence"][0]
    require(evidence["attempt_number"] == 1 and evidence["passed"] is False, "attempt_outcome_preserved")
    require(evidence["verification_digest"] == "a" * 64 and evidence["tests_executed"], "verification_evidence_preserved")
    require("content" not in json.dumps(evidence).lower() and "output" not in json.dumps(evidence).lower(), "attempt_evidence_contains_no_raw_content")

    # A fresh process can restore the same exact session without provider/test work.
    script = (
        "import json,sys;"
        f"sys.path.insert(0,{str(ROOT / 'conscious_agent')!r});"
        "from persistent_development_sessions_foundations import load_persistent_development_session;"
        f"r=load_persistent_development_session({session['session_id']!r},runtime_root={str(runtime)!r});"
        "print(json.dumps({'session_id':r.get('session_id'),'session_digest':r.get('session_digest'),'generation':r.get('generation')}))"
    )
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    restarted = subprocess.run([sys.executable, "-I", "-B", "-c", script], cwd=ROOT, env=env, text=True, capture_output=True, timeout=30)
    require(restarted.returncode == 0, "fresh_process_restart_restore_runs")
    restarted_row = json.loads(restarted.stdout.strip())
    require(restarted_row["session_id"] == session["session_id"] and restarted_row["generation"] == evidence_refresh["generation"], "fresh_process_restores_latest_generation")
    require(restarted_row["session_digest"] == evidence_refresh["session_digest"], "fresh_process_restores_exact_digest")

    # Cancellation state survives refresh and never changes selected source.
    cancelled = cancel_coding_work_request(request_id, runtime_root=runtime)
    require(cancelled["ok"] and cancelled["status"] == "coding_work_request_cancelled", "underlying_request_cancelled")
    cancelled_session = refresh_persistent_development_session(session["session_id"], runtime_root=runtime)
    require(cancelled_session["phase"] == "cancelled" and cancelled_session["next_action"] == "none", "cancelled_state_persisted")
    require(tree_signature(project) == project_before, "session_and_cancellation_preserve_selected_project")
    require(load_coding_work_request(request_id, runtime_root=runtime)["cancelled"] is True, "request_cancellation_durable")

# Corrupt session records fail closed rather than silently reconstructing during Bundle A.
with tempfile.TemporaryDirectory(prefix="eid-v1256-0-2-tamper-") as directory:
    base = Path(directory)
    runtime = base / "runtime"
    project = make_project(base)
    request = prepare_foundation(project, runtime)
    session = create_or_restore_persistent_development_session(request["request_id"], runtime_root=runtime)
    path = _store_root(runtime) / "persistent_development_sessions" / f"{request['request_id']}.json"
    row = json.loads(path.read_text(encoding="utf-8"))
    row["phase"] = "completed"
    path.write_text(json.dumps(row), encoding="utf-8")
    require(load_persistent_development_session(session["session_id"], runtime_root=runtime) == {}, "tampered_session_rejected")

require(source_signature() == SOURCE_BEFORE, "foundation_suite_preserves_source_immutability")

print(json.dumps({
    "ok": True,
    "suite": "v1256.0-v1256.2-persistent-development-session-foundations",
    "passed": len(CHECKS),
    "failed": 0,
    "checks": CHECKS,
    "provider_contacted": False,
    "project_mutation_authorized": False,
    "automatic_resume_authorized": False,
    "duplicate_execution_authorized": False,
}, indent=2, sort_keys=True))
