from __future__ import annotations

import concurrent.futures
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

from ordinary_chat_development_campaign import _atomic_json, _digest, _store_root
from isolated_coding_execution_foundations import (
    create_or_restore_coding_work_plan,
    create_or_restore_coding_work_request,
    inspect_coding_project,
    materialize_or_restore_isolated_coding_workspace,
)
from isolated_coding_execution import _execution_path, _seal as seal_execution, prepare_isolated_coding_execution
from persistent_development_sessions import (
    load_persistent_development_session_events,
    process_persistent_development_session_control,
    resume_persistent_development_session,
)
from persistent_development_sessions_foundations import (
    create_or_restore_persistent_development_session,
    load_persistent_development_session,
    public_persistent_development_session,
    refresh_persistent_development_session,
)
from persistent_development_sessions_reliability import (
    build_persistent_development_session_handoff,
    inspect_persistent_development_session_health,
    recover_persistent_development_session,
    resume_persistent_development_session_reliably,
)
from v1255_test_support import CandidateProvider, make_project, prepare_fast_v1254_candidate, tree_signature

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
        constraints=["Keep current layout."],
        prohibited_actions=["Do not install dependencies."],
        expected_artifacts=["Reviewable diff", "Passing tests"],
        verification=["Compile Python", "Run project tests"],
        runtime_root=runtime,
    )
    assert inspect_coding_project(request["request_id"], runtime_root=runtime)["ok"]
    assert create_or_restore_coding_work_plan(request["request_id"], runtime_root=runtime)["ok"]
    assert materialize_or_restore_isolated_coding_workspace(request["request_id"], runtime_root=runtime)["ok"]
    return request


SOURCE_BEFORE = source_signature()

# Stale source after a prepared execution is surfaced by the session before any
# provider call or authority replay.
with tempfile.TemporaryDirectory(prefix="eid-v1256-6-8-stale-") as directory:
    base = Path(directory)
    runtime = base / "runtime"
    project = make_project(base)
    request = prepare_foundation(project, runtime)
    prepared = prepare_isolated_coding_execution(request["request_id"], runtime_root=runtime)
    session = create_or_restore_persistent_development_session(request["request_id"], runtime_root=runtime)
    (project / "main.py").write_text("VALUE = 'operator edit after review'\n", encoding="utf-8")
    resumed = resume_persistent_development_session_reliably(session["session_id"], runtime_root=runtime)
    public = resumed["persistent_session"]
    require(public["phase"] == "blocked" and "stale_source_detected" in public["blockers"], "stale_source_becomes_persistent_blocker")
    require(public["next_action"] == "operator_reconcile_source", "stale_source_requires_operator_reconciliation")
    require(resumed["next_control"]["kind"] == "none", "stale_source_does_not_surface_execution_authorization")
    require(resumed["provider_contacted"] is False and resumed["automatic_resume_authorized"] is False, "stale_resume_executes_nothing")

# Expired v1254 execution lease is recoverable using the same already-bound
# authorization, but the persistent layer does not consume it by itself.
with tempfile.TemporaryDirectory(prefix="eid-v1256-6-8-lease-") as directory:
    base = Path(directory)
    runtime = base / "runtime"
    project = make_project(base)
    request = prepare_foundation(project, runtime)
    prepared = prepare_isolated_coding_execution(request["request_id"], runtime_root=runtime)
    session = create_or_restore_persistent_development_session(request["request_id"], runtime_root=runtime)
    execution_path = _execution_path(request["request_id"], runtime)
    execution = json.loads(execution_path.read_text(encoding="utf-8"))
    execution.update({
        "status": "isolated_coding_execution_running",
        "phase": "running",
        "lease_token": "expired-fixture",
        "lease_expires_unix": time.time() - 30,
        "execution_authority_consumed": True,
    })
    execution = seal_execution(execution, "execution_record_digest")
    _atomic_json(execution_path, execution)
    resumed = resume_persistent_development_session_reliably(session["session_id"], runtime_root=runtime)
    require(resumed["persistent_session"]["phase"] == "execution_recovery_required", "expired_execution_lease_detected")
    require(resumed["next_control"]["kind"] == "isolated_execution_recovery", "expired_execution_projects_recovery_control")
    require(resumed["next_control"]["authorization_phrase"] == prepared["authorization_phrase"], "recovery_uses_original_exact_authorization")
    require(resumed["provider_contacted"] is False and resumed["duplicate_execution_authorized"] is False, "lease_recovery_projection_does_not_execute")

# Corrupt session projection is reconstructed from the authoritative v1254
# lineage and quarantined without exposing its contents.
with tempfile.TemporaryDirectory(prefix="eid-v1256-6-8-corrupt-session-") as directory:
    base = Path(directory)
    runtime = base / "runtime"
    project = make_project(base)
    request, _, _ = prepare_fast_v1254_candidate(project, runtime, provider=CandidateProvider())
    session = create_or_restore_persistent_development_session(request["request_id"], runtime_root=runtime)
    session_path = _store_root(runtime) / "persistent_development_sessions" / f"{request['request_id']}.json"
    raw = json.loads(session_path.read_text(encoding="utf-8"))
    raw["phase"] = "forged_complete"
    session_path.write_text(json.dumps(raw), encoding="utf-8")
    health = inspect_persistent_development_session_health(session["session_id"], runtime_root=runtime)
    require(not health["ok"] and health["recoverable"] and not health["session_valid"], "corrupt_session_health_detected_and_recoverable")
    recovered = recover_persistent_development_session(session["session_id"], runtime_root=runtime)
    require(recovered["ok"] and recovered["status"] == "persistent_session_recovered", "corrupt_session_projection_recovered")
    require(recovered["quarantined_record_count"] == 1, "corrupt_session_projection_quarantined")
    require(recovered["persistent_session"]["phase"] == "review_ready", "recovery_reconstructs_phase_from_authoritative_lineage")
    require(recovered["provider_contacted"] is False and recovered["selected_project_modified"] is False, "metadata_recovery_has_no_execution_or_project_side_effect")
    quarantine = _store_root(runtime) / "persistent_development_session_quarantine" / session["session_id"]
    require(any(quarantine.glob("session-*.json")), "corrupt_session_quarantine_receipt_exists")
    require(inspect_persistent_development_session_health(session["session_id"], runtime_root=runtime)["ok"], "health_green_after_session_recovery")

# Corrupt index is recoverable from a valid session projection.
with tempfile.TemporaryDirectory(prefix="eid-v1256-6-8-corrupt-index-") as directory:
    base = Path(directory)
    runtime = base / "runtime"
    project = make_project(base)
    request = prepare_foundation(project, runtime)
    session = create_or_restore_persistent_development_session(request["request_id"], runtime_root=runtime)
    index_path = _store_root(runtime) / "persistent_development_session_indexes" / f"{session['session_id']}.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["request_id"] = "devc_" + "0" * 24
    index_path.write_text(json.dumps(index), encoding="utf-8")
    health = inspect_persistent_development_session_health(session["session_id"], runtime_root=runtime)
    require(not health["ok"] and health["recoverable"] and not health["index_valid"], "corrupt_index_detected_and_recoverable")
    recovered = recover_persistent_development_session(session["session_id"], runtime_root=runtime)
    require(recovered["ok"] and recovered["health"]["index_valid"], "corrupt_index_rebuilt_from_valid_session")
    require(load_persistent_development_session(session["session_id"], runtime_root=runtime)["request_id"] == request["request_id"], "rebuilt_index_points_to_original_request")

# Event-chain corruption is quarantined; execution/test evidence stays in the
# authoritative lineage and the rebuilt chain starts with an explicit recovery event.
with tempfile.TemporaryDirectory(prefix="eid-v1256-6-8-corrupt-events-") as directory:
    base = Path(directory)
    runtime = base / "runtime"
    project = make_project(base)
    request = prepare_foundation(project, runtime)
    session = create_or_restore_persistent_development_session(request["request_id"], runtime_root=runtime)
    first = resume_persistent_development_session(session["session_id"], runtime_root=runtime)
    require(first["progress_event"]["sequence"] == 1, "initial_progress_event_created")
    event_path = _store_root(runtime) / "persistent_development_session_events" / session["session_id"] / "event-000001.json"
    event = json.loads(event_path.read_text(encoding="utf-8"))
    event["phase"] = "tampered"
    event_path.write_text(json.dumps(event), encoding="utf-8")
    health = inspect_persistent_development_session_health(session["session_id"], runtime_root=runtime)
    require(not health["event_chain_valid"] and health["recoverable"], "event_chain_corruption_detected")
    recovered = recover_persistent_development_session(session["session_id"], runtime_root=runtime)
    require(recovered["ok"] and recovered["quarantined_record_count"] == 1, "corrupt_event_chain_quarantined_and_rebuilt")
    events = load_persistent_development_session_events(session["session_id"], runtime_root=runtime)
    require(len(events) == 1 and events[0]["event_type"] == "session_recovered_from_authoritative_lineage", "recovered_event_chain_starts_with_explicit_recovery_receipt")
    require(inspect_persistent_development_session_health(session["session_id"], runtime_root=runtime)["ok"], "event_chain_health_green_after_recovery")

# Concurrent resumes converge on one state/event identity rather than creating
# duplicate continuation receipts or work.
with tempfile.TemporaryDirectory(prefix="eid-v1256-6-8-concurrency-") as directory:
    base = Path(directory)
    runtime = base / "runtime"
    project = make_project(base)
    request = prepare_foundation(project, runtime)
    session = create_or_restore_persistent_development_session(request["request_id"], runtime_root=runtime)
    before = len(load_persistent_development_session_events(session["session_id"], runtime_root=runtime))
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(resume_persistent_development_session_reliably, session["session_id"], runtime_root=runtime) for _ in range(8)]
        rows = [future.result(timeout=30) for future in futures]
    require(all(row["event"] == "persistent_development_session_resumed" for row in rows), "concurrent_resumes_all_restore_same_session")
    digests = {row["persistent_session"]["session_id"] for row in rows}
    require(digests == {session["session_id"]}, "concurrent_resumes_keep_single_session_identity")
    after_events = load_persistent_development_session_events(session["session_id"], runtime_root=runtime)
    require(len(after_events) == before + 1, "concurrent_identical_resume_event_deduplicated")
    require(all(row["provider_contacted"] is False and row["duplicate_execution_authorized"] is False for row in rows), "concurrent_resume_never_executes_or_duplicates_work")

# Long Windows-like runtime paths remain safe because session storage uses only
# bounded request/session identifiers, never selected-project paths as filenames.
with tempfile.TemporaryDirectory(prefix="eid-v1256-6-8-longpath-") as directory:
    base = Path(directory)
    deep = base
    for index in range(8):
        deep = deep / (f"segment-{index}-" + "x" * 24)
    runtime = deep / "runtime"
    project = make_project(base)
    request = prepare_foundation(project, runtime)
    session = create_or_restore_persistent_development_session(request["request_id"], runtime_root=runtime)
    resumed = resume_persistent_development_session_reliably(session["session_id"], runtime_root=runtime)
    require(resumed["active"] and resumed["persistent_session"]["restart_safe"], "long_runtime_path_session_resume_succeeds")
    require(str(project) not in json.dumps(resumed), "long_path_public_result_does_not_expose_project_path")

# Handoff is bounded/content-minimized and carries no authority.
with tempfile.TemporaryDirectory(prefix="eid-v1256-6-8-handoff-") as directory:
    base = Path(directory)
    runtime = base / "runtime"
    project = make_project(base)
    project_before = tree_signature(project)
    request = prepare_foundation(project, runtime)
    session = create_or_restore_persistent_development_session(request["request_id"], runtime_root=runtime)
    handoff = build_persistent_development_session_handoff(session["session_id"], runtime_root=runtime)
    require(handoff["ok"] and handoff["status"] == "persistent_development_session_handoff_ready", "bounded_handoff_ready")
    require(handoff["requirements_preserved"] and handoff["plan_preserved"], "handoff_reports_required_continuity")
    require(handoff["private_content_exposed"] is False and str(project) not in json.dumps(handoff), "handoff_content_minimized_and_path_safe")
    require(handoff["automatic_resume_authorized"] is False and handoff["release_authorized"] is False, "handoff_grants_no_resume_or_release_authority")
    require(tree_signature(project) == project_before, "health_and_handoff_preserve_selected_project")

# Malformed control identifiers remain inert/fail closed.
invalid = process_persistent_development_session_control("Resume development session ../../secrets.", runtime_root=Path(tempfile.gettempdir()) / "eid-v1256-invalid")
require(invalid["active"] is False, "path_traversal_like_session_control_inert")

require(source_signature() == SOURCE_BEFORE, "reliability_suite_preserves_eidolon_source")

print(json.dumps({
    "ok": True,
    "suite": "v1256.6-v1256.8-persistent-development-session-reliability",
    "passed": len(CHECKS),
    "failed": 0,
    "checks": CHECKS,
    "provider_contacted": False,
    "automatic_resume_authorized": False,
    "duplicate_execution_authorized": False,
    "release_authorized": False,
}, indent=2, sort_keys=True))
