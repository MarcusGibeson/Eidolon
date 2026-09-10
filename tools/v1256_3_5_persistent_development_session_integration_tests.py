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

from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from persistent_development_sessions import load_persistent_development_session_events
from persistent_development_sessions_foundations import load_persistent_development_session
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


class RepairingProvider:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def __call__(self, prompt: str) -> str:
        payload = json.loads(prompt)
        self.calls.append(payload)
        authority = payload["authority"]
        attempt = int(authority["attempt"])
        subtract = "return a + b" if attempt == 1 else "return a - b"
        return json.dumps({
            "authority": {
                "request_id": authority["request_id"],
                "execution_digest": authority["execution_digest"],
                "attempt": attempt,
            },
            "files": [{
                "path": "main.py",
                "operation": "modify",
                "content": f"def add(a, b):\n    return a + b\n\ndef subtract(a, b):\n    {subtract}\n",
            }],
        })


SOURCE_BEFORE = source_signature()

with tempfile.TemporaryDirectory(prefix="eid-v1256-3-5-") as directory:
    base = Path(directory)
    runtime = base / "runtime"
    project = make_project(base)
    project_before = tree_signature(project)
    original_main = (project / "main.py").read_text(encoding="utf-8")
    projection = {
        "grounding": {"grounding_status": "matched", "capability_id": "software_development"},
        "intent": {"category": "action_request"},
    }

    created = process_ordinary_chat_development_turn(
        "Add subtraction to this calculator while preserving addition.",
        action_projection=projection,
        session_id="v1256-chat",
        project_state={"id": "calculator", "name": "Calculator", "path": str(project)},
        runtime_root=runtime,
    )
    require(created["active"] and created["event"] == "proposal_created", "ordinary_chat_request_creates_proposal")
    proposal = created["proposal"]
    approved = process_ordinary_chat_development_turn(
        f"Approve development proposal {proposal['proposal_id']} revision {proposal['revision']}.",
        runtime_root=runtime,
        python_executable=sys.executable,
    )
    require(approved["event"] == "approval_consumed", "proposal_approval_consumed")
    persistent = approved.get("persistent_development_session") or {}
    request_id = str(approved.get("isolated_coding_request_id") or "")
    session_id = str(persistent.get("session_id") or "")
    require(request_id.startswith("devc_") and session_id.startswith("devs_"), "approval_creates_persistent_session_for_isolated_request")
    require(persistent["phase"] == "execution_authorization_required", "approval_session_waits_for_separate_execution_authority")
    require(persistent["provider_contact_authorized"] is False and persistent["automatic_resume_authorized"] is False, "persistent_session_does_not_inherit_proposal_authority")

    resume = process_ordinary_chat_development_turn(f"Resume development session {session_id}.", runtime_root=runtime)
    require(resume["active"] and resume["event"] == "persistent_development_session_resumed", "ordinary_chat_resume_control_active")
    require(resume["next_control"]["kind"] == "isolated_execution", "resume_surfaces_existing_execution_control")
    require(resume["next_control"]["authorization_phrase"].startswith("Authorize isolated coding execution"), "resume_surfaces_exact_existing_execution_phrase")
    require(resume["provider_contacted"] is False and resume["commands_executed"] is False, "resume_itself_executes_nothing")

    provider = RepairingProvider()
    execution = process_ordinary_chat_development_turn(
        resume["next_control"]["authorization_phrase"],
        runtime_root=runtime,
        provider_generate=provider,
        python_executable=sys.executable,
    )
    require(execution["active"] and execution["event"] == "isolated_coding_execution_completed", "ordinary_chat_execution_completes")
    require(len(provider.calls) == 2, "one_failed_attempt_then_one_repair_provider_call")
    persistent = execution.get("persistent_development_session") or {}
    require(persistent["phase"] == "review_ready" and persistent["attempt_count"] == 2, "session_refreshes_to_review_ready_with_attempts")
    require(persistent["verification_evidence_preserved"], "session_preserves_test_evidence")
    require([row["passed"] for row in persistent["attempt_evidence"]] == [False, True], "failed_and_passing_attempts_survive_in_order")
    require(tree_signature(project) == project_before, "isolated_execution_still_does_not_modify_selected_project")

    events_before_restart = load_persistent_development_session_events(session_id, runtime_root=runtime)
    require(len(events_before_restart) >= 2, "progress_events_persisted")
    require(all(row["content_minimized"] and not row["private_content_included"] for row in events_before_restart), "progress_events_content_minimized")

    # Restart in a clean process and resume without supplying any provider. It
    # must restore evidence rather than repeating either provider attempt.
    script = (
        "import json,sys;"
        f"sys.path.insert(0,{str(ROOT / 'conscious_agent')!r});"
        "from persistent_development_sessions import resume_persistent_development_session;"
        f"r=resume_persistent_development_session({session_id!r},runtime_root={str(runtime)!r});"
        "print(json.dumps({'phase':r.get('persistent_session',{}).get('phase'),'attempt_count':r.get('persistent_session',{}).get('attempt_count'),'next_kind':r.get('next_control',{}).get('kind'),'provider':r.get('provider_contacted')}))"
    )
    restarted = subprocess.run([sys.executable, "-I", "-B", "-c", script], cwd=ROOT, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, text=True, capture_output=True, timeout=30)
    require(restarted.returncode == 0, "clean_process_resume_runs")
    restarted_row = json.loads(restarted.stdout.strip())
    require(restarted_row == {"phase": "review_ready", "attempt_count": 2, "next_kind": "none", "provider": False}, "clean_process_resume_restores_evidence_without_reexecution")
    require(len(provider.calls) == 2, "restart_resume_does_not_recontact_provider")

    # Prepare application through the real ordinary-chat v1255 seam. The same
    # persistent session advances and exposes the already-prepared exact packet.
    prepared_application = process_ordinary_chat_development_turn(
        f"Prepare controlled application for request {request_id}.",
        runtime_root=runtime,
        python_executable=sys.executable,
    )
    require(prepared_application["event"] == "controlled_application_authorization_required", "controlled_application_prepared")
    persistent = prepared_application.get("persistent_development_session") or {}
    require(persistent["session_id"] == session_id and persistent["phase"] == "application_authorization_required", "same_session_tracks_application_preparation")

    app_resume = process_ordinary_chat_development_turn(f"Resume development session {session_id}.", runtime_root=runtime)
    require(app_resume["next_control"]["kind"] == "controlled_application", "resume_surfaces_existing_application_packet")
    apply_phrase = app_resume["next_control"]["authorization_phrase"]
    require(apply_phrase.startswith("Authorize controlled application"), "exact_application_phrase_restored_after_restart")

    applied = process_ordinary_chat_development_turn(apply_phrase, runtime_root=runtime, python_executable=sys.executable)
    require(applied["event"] in {"controlled_application_completed", "controlled_application_completed_recovered"}, "controlled_application_completes")
    persistent = applied.get("persistent_development_session") or {}
    require(persistent["phase"] == "completed" and "controlled_application_completed" in persistent["completed_work"], "session_records_completed_application")
    require("def subtract" in (project / "main.py").read_text(encoding="utf-8"), "selected_project_receives_reviewed_candidate_once")
    require(len(provider.calls) == 2, "application_does_not_recontact_provider")

    event_count_after_apply = len(load_persistent_development_session_events(session_id, runtime_root=runtime))
    replay = process_ordinary_chat_development_turn(apply_phrase, runtime_root=runtime, python_executable=sys.executable)
    require(replay["event"] in {"controlled_application_completed", "controlled_application_completed_recovered"}, "duplicate_application_control_restores_terminal_result")
    require(len(provider.calls) == 2, "duplicate_application_control_never_recontacts_provider")
    require(len(load_persistent_development_session_events(session_id, runtime_root=runtime)) == event_count_after_apply, "duplicate_terminal_observation_does_not_duplicate_progress_event")

    prepared_rollback = process_ordinary_chat_development_turn(f"Prepare controlled rollback for request {request_id}.", runtime_root=runtime)
    require(prepared_rollback["event"] == "controlled_rollback_authorization_required", "controlled_rollback_prepared")
    require(prepared_rollback["persistent_development_session"]["phase"] == "rollback_authorization_required", "session_tracks_pending_rollback")
    rollback_resume = process_ordinary_chat_development_turn(f"Resume development session {session_id}.", runtime_root=runtime)
    require(rollback_resume["next_control"]["kind"] == "controlled_rollback", "resume_surfaces_separate_rollback_authorization")
    rollback_phrase = rollback_resume["next_control"]["authorization_phrase"]
    rolled_back = process_ordinary_chat_development_turn(rollback_phrase, runtime_root=runtime)
    require(rolled_back["event"] in {"controlled_rollback_completed", "controlled_rollback_completed_recovered"}, "controlled_rollback_completes")
    persistent = rolled_back.get("persistent_development_session") or {}
    require(persistent["phase"] == "rolled_back" and "controlled_rollback_completed" in persistent["completed_work"], "session_records_rollback_completion")
    require((project / "main.py").read_text(encoding="utf-8") == original_main, "rollback_restores_pre_apply_content")
    require(len(provider.calls) == 2, "rollback_never_recontacts_provider")

    final = load_persistent_development_session(session_id, runtime_root=runtime)
    require(final["generation"] >= 5 and final["phase"] == "rolled_back", "multi_stage_session_generation_persists")
    final_events = load_persistent_development_session_events(session_id, runtime_root=runtime)
    require(all(int(row["sequence"]) == index + 1 for index, row in enumerate(final_events)), "progress_event_sequence_contiguous")
    require(all((not index) or row["prior_event_digest"] == final_events[index - 1]["event_digest"] for index, row in enumerate(final_events)), "progress_event_digest_chain_intact")

require(source_signature() == SOURCE_BEFORE, "integration_suite_preserves_eidolon_source")

print(json.dumps({
    "ok": True,
    "suite": "v1256.3-v1256.5-persistent-development-session-integration",
    "passed": len(CHECKS),
    "failed": 0,
    "checks": CHECKS,
    "provider_calls": 2,
    "restart_reexecution": False,
    "duplicate_execution_authorized": False,
    "release_authorized": False,
}, indent=2, sort_keys=True))
