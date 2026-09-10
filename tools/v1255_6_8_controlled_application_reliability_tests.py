from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "conscious_agent"))
sys.path.insert(0, str(ROOT / "tools"))
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

from ordinary_chat_development_campaign import _atomic_json
from controlled_application_rollback_foundations import (
    DENIED_AUTHORITY,
    inspect_controlled_application_conflicts,
    prepare_controlled_application,
)
from controlled_application_rollback import (
    _authorization_path,
    _backup_manifest_path,
    _capture_backup,
    _execution_authority,
    _execution_path,
    _prepare_execution_record,
    _sealed,
    _workspace_candidate_bytes,
    _write_candidate_file,
    authorize_and_apply_controlled_candidate,
    authorize_and_rollback_controlled_candidate,
    prepare_controlled_rollback,
)
from controlled_application_rollback_reliability import (
    build_controlled_application_operator_handoff,
    inspect_controlled_application_health,
)
from isolated_coding_execution_foundations import (
    _request_path,
    _sealed as seal_foundation,
    load_coding_work_request,
)
from v1255_test_support import CandidateProvider, make_project, prepare_fast_v1254_candidate

CHECKS: list[str] = []


def require(value: object, label: str) -> None:
    if not value:
        raise AssertionError(label)
    CHECKS.append(label)


def source_signature() -> str:
    digest = hashlib.sha256()
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.is_symlink() or any(part in {"data", "__pycache__", ".git", ".pytest_cache", ".venv", "venv"} for part in path.parts):
            continue
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


SOURCE_BEFORE = source_signature()

# Verification failure automatically restores only the affected scope.
with tempfile.TemporaryDirectory(prefix="eid-v1255-verification-rollback-") as td:
    base = Path(td); runtime = base / "runtime"; project = make_project(base)
    original_main = (project / "main.py").read_bytes()
    request, _, _ = prepare_fast_v1254_candidate(project, runtime)
    packet = prepare_controlled_application(request["request_id"], runtime_root=runtime)
    failing_tests = (project / "tests" / "test_main.py").read_text().replace("self.assertEqual(subtract(7, 2), 5)", "self.assertEqual(subtract(7, 2), 999)")
    (project / "tests" / "test_main.py").write_text(failing_tests, encoding="utf-8")
    result = authorize_and_apply_controlled_candidate(request["request_id"], expected_application_digest=packet["application_digest"], authorization_phrase=packet["authorization_phrase"], runtime_root=runtime, python_executable=sys.executable)
    require(not result["ok"] and result["status"] == "controlled_application_verification_failed_rolled_back", "failed_live_verification_rolls_back")
    require((project / "main.py").read_bytes() == original_main, "verification_failure_restores_affected_file")
    require("999" in (project / "tests" / "test_main.py").read_text(), "verification_failure_preserves_unrelated_operator_test_edit")
    require(result["rollback_executed"] and result["rollback_verified"], "automatic_failure_rollback_verified")

# Candidate workspace tampering after packet preparation fails before authorization
# consumption or selected-project backup capture.
with tempfile.TemporaryDirectory(prefix="eid-v1255-workspace-tamper-") as td:
    base = Path(td); runtime = base / "runtime"; project = make_project(base)
    request, _, _ = prepare_fast_v1254_candidate(project, runtime)
    packet = prepare_controlled_application(request["request_id"], runtime_root=runtime)
    workspace_record = json.loads((runtime / "development_campaigns" / "coding_workspace_records" / f"{request['request_id']}.json").read_text())
    workspace_root = Path(workspace_record["workspace_path"])
    (workspace_root / "main.py").write_text("def add(a,b): return -1\n", encoding="utf-8")
    blocked = authorize_and_apply_controlled_candidate(request["request_id"], expected_application_digest=packet["application_digest"], authorization_phrase=packet["authorization_phrase"], runtime_root=runtime, python_executable=sys.executable)
    require(blocked["status"] == "candidate_workspace_integrity_changed", "candidate_workspace_tamper_detected")
    require(not _authorization_path(request["request_id"], runtime).exists(), "candidate_tamper_does_not_consume_authorization")
    require(not _backup_manifest_path(request["request_id"], runtime).exists(), "candidate_tamper_does_not_capture_backup")

# Expired interrupted application with a known partial state recovers under the
# same exact authorization without provider contact or duplicate authorization.
with tempfile.TemporaryDirectory(prefix="eid-v1255-apply-recovery-") as td:
    base = Path(td); runtime = base / "runtime"; project = make_project(base)
    request, _, provider = prepare_fast_v1254_candidate(project, runtime, provider=CandidateProvider(create_extra=True))
    packet = prepare_controlled_application(request["request_id"], runtime_root=runtime)
    execution = _prepare_execution_record(packet, runtime_root=runtime)
    backup = _capture_backup(request["request_id"], packet, project, runtime_root=runtime)
    running = dict(execution)
    running.update({"status": "controlled_application_running", "phase": "running", "lease_token": "expired-fixture", "lease_expires_unix": time.time() - 10, "authorization_consumed": True, **_execution_authority()})
    running = _sealed(running, "execution_record_digest")
    _atomic_json(_execution_path(request["request_id"], runtime), running)
    # Simulate one completed write from the interrupted transaction.
    main_change = next(row for row in packet["changes"] if row["relative_path"] == "main.py")
    _write_candidate_file(project / "main.py", _workspace_candidate_bytes(request["request_id"], main_change, runtime_root=runtime))
    recovered = authorize_and_apply_controlled_candidate(request["request_id"], expected_application_digest=packet["application_digest"], authorization_phrase=packet["authorization_phrase"], runtime_root=runtime, python_executable=sys.executable)
    require(recovered["ok"] and recovered["status"] == "controlled_application_completed_recovered", "expired_partial_apply_recovers")
    require(recovered["recovery_count"] == 1 and recovered["authorization_consumption_count"] == 1, "apply_recovery_reuses_one_authorization")
    require((project / "helper.py").is_file() and "subtract" in (project / "main.py").read_text(), "apply_recovery_completes_candidate")
    require(provider.calls == 1, "apply_recovery_never_recontacts_provider")
    health = inspect_controlled_application_health(request["request_id"], runtime_root=runtime)
    require(health["target_state"] == "candidate" and health["backup_valid"], "recovered_application_health_candidate_and_backup_valid")

# Concurrent duplicate exact apply requests converge on one sealed result.
with tempfile.TemporaryDirectory(prefix="eid-v1255-concurrent-") as td:
    base = Path(td); runtime = base / "runtime"; project = make_project(base)
    request, _, _ = prepare_fast_v1254_candidate(project, runtime)
    packet = prepare_controlled_application(request["request_id"], runtime_root=runtime)
    barrier = threading.Barrier(4); outputs: list[dict] = []; lock = threading.Lock()
    def worker() -> None:
        barrier.wait()
        row = authorize_and_apply_controlled_candidate(request["request_id"], expected_application_digest=packet["application_digest"], authorization_phrase=packet["authorization_phrase"], runtime_root=runtime, python_executable=sys.executable)
        with lock: outputs.append(row)
    threads = [threading.Thread(target=worker) for _ in range(4)]
    [thread.start() for thread in threads]; [thread.join(40) for thread in threads]
    require(len(outputs) == 4, "concurrent_apply_duplicates_return_bounded_results")
    require(sum(bool(row.get("ok")) for row in outputs) == 1, "concurrent_apply_single_mutating_creator")
    require(sum(row.get("status") == "controlled_application_in_progress" for row in outputs) == 3, "concurrent_apply_duplicates_fail_closed_while_active")
    created = next(row for row in outputs if row.get("ok"))
    require(created.get("operation_status") == "created", "concurrent_apply_single_creator")
    replay = authorize_and_apply_controlled_candidate(request["request_id"], expected_application_digest=packet["application_digest"], authorization_phrase=packet["authorization_phrase"], runtime_root=runtime, python_executable=sys.executable)
    require(replay.get("operation_status") == "restored" and replay.get("application_result_digest") == created.get("application_result_digest"), "concurrent_apply_late_duplicate_restores_sealed_result")
    auth = json.loads(_authorization_path(request["request_id"], runtime).read_text())
    require(auth["consumption_count"] == 1, "concurrent_apply_single_authorization_consumption")

# Windows casefold collision on a candidate-created path blocks the packet even
# on a case-sensitive development host.
with tempfile.TemporaryDirectory(prefix="eid-v1255-casefold-") as td:
    base = Path(td); runtime = base / "runtime"; project = make_project(base)
    request, _, _ = prepare_fast_v1254_candidate(project, runtime, provider=CandidateProvider(create_extra=True))
    (project / "Helper.py").write_text("# operator file with Windows-colliding spelling\n", encoding="utf-8")
    conflict = inspect_controlled_application_conflicts(request["request_id"], runtime_root=runtime)
    require(not conflict["ok"] and conflict["windows_casefold_conflict_count"] == 1, "windows_casefold_collision_detected")
    blocked = prepare_controlled_application(request["request_id"], runtime_root=runtime)
    require(not blocked["ok"], "windows_casefold_collision_blocks_application_packet")

# Symlink/link substitution on an affected path is a containment conflict.
if hasattr(os, "symlink"):
    with tempfile.TemporaryDirectory(prefix="eid-v1255-link-") as td:
        base = Path(td); runtime = base / "runtime"; project = make_project(base)
        request, _, _ = prepare_fast_v1254_candidate(project, runtime)
        packet = prepare_controlled_application(request["request_id"], runtime_root=runtime)
        outside = base / "outside.py"; outside.write_text("OUTSIDE=True\n", encoding="utf-8")
        (project / "main.py").unlink()
        try:
            os.symlink(outside, project / "main.py")
        except OSError:
            pass
        if (project / "main.py").is_symlink():
            blocked = authorize_and_apply_controlled_candidate(request["request_id"], expected_application_digest=packet["application_digest"], authorization_phrase=packet["authorization_phrase"], runtime_root=runtime, python_executable=sys.executable)
            require(not blocked["ok"], "affected_symlink_substitution_blocks_apply")
            require(outside.read_text() == "OUTSIDE=True\n", "symlink_outside_target_untouched")

# Request cancellation after packet preparation blocks before authorization use.
with tempfile.TemporaryDirectory(prefix="eid-v1255-cancel-before-apply-") as td:
    base = Path(td); runtime = base / "runtime"; project = make_project(base)
    request, _, _ = prepare_fast_v1254_candidate(project, runtime)
    packet = prepare_controlled_application(request["request_id"], runtime_root=runtime)
    row = load_coding_work_request(request["request_id"], runtime_root=runtime); row["cancelled"] = True; row["lifecycle_state"] = "cancelled"; row = seal_foundation(row, "record_digest")
    _atomic_json(_request_path(request["request_id"], runtime), row)
    blocked = authorize_and_apply_controlled_candidate(request["request_id"], expected_application_digest=packet["application_digest"], authorization_phrase=packet["authorization_phrase"], runtime_root=runtime, python_executable=sys.executable)
    require(blocked["status"] == "coding_work_request_cancelled", "cancel_after_packet_blocks_apply")
    require(not _authorization_path(request["request_id"], runtime).exists(), "cancelled_apply_does_not_consume_authorization")

# Rollback refuses to overwrite a user edit made to an applied path.
with tempfile.TemporaryDirectory(prefix="eid-v1255-rollback-conflict-") as td:
    base = Path(td); runtime = base / "runtime"; project = make_project(base)
    request, _, _ = prepare_fast_v1254_candidate(project, runtime)
    packet = prepare_controlled_application(request["request_id"], runtime_root=runtime)
    applied = authorize_and_apply_controlled_candidate(request["request_id"], expected_application_digest=packet["application_digest"], authorization_phrase=packet["authorization_phrase"], runtime_root=runtime, python_executable=sys.executable)
    require(applied["ok"], "rollback_conflict_fixture_applied")
    (project / "main.py").write_text("# operator edit after apply\ndef add(a,b): return 7\n", encoding="utf-8")
    blocked = prepare_controlled_rollback(request["request_id"], runtime_root=runtime)
    require(blocked["status"] == "controlled_rollback_conflict_detected", "rollback_preserves_post_apply_user_edit")
    require("operator edit" in (project / "main.py").read_text(), "rollback_conflict_does_not_mutate_user_edit")

# Tampered private backup prevents rollback preparation.
with tempfile.TemporaryDirectory(prefix="eid-v1255-backup-tamper-") as td:
    base = Path(td); runtime = base / "runtime"; project = make_project(base)
    request, _, _ = prepare_fast_v1254_candidate(project, runtime)
    packet = prepare_controlled_application(request["request_id"], runtime_root=runtime)
    applied = authorize_and_apply_controlled_candidate(request["request_id"], expected_application_digest=packet["application_digest"], authorization_phrase=packet["authorization_phrase"], runtime_root=runtime, python_executable=sys.executable)
    require(applied["ok"], "backup_tamper_fixture_applied")
    path = _backup_manifest_path(request["request_id"], runtime); raw = json.loads(path.read_text()); raw["entries"][0]["content_b64"] = base64.b64encode(b"tampered").decode(); path.write_text(json.dumps(raw), encoding="utf-8")
    blocked = prepare_controlled_rollback(request["request_id"], runtime_root=runtime)
    require(blocked["status"] == "controlled_rollback_backup_invalid", "tampered_backup_blocks_rollback")

# Interrupted rollback from known candidate/baseline partial state completes under
# the same exact rollback authorization.
with tempfile.TemporaryDirectory(prefix="eid-v1255-rollback-recovery-") as td:
    base = Path(td); runtime = base / "runtime"; project = make_project(base)
    original_main = (project / "main.py").read_bytes()
    request, _, _ = prepare_fast_v1254_candidate(project, runtime, provider=CandidateProvider(create_extra=True))
    packet = prepare_controlled_application(request["request_id"], runtime_root=runtime)
    applied = authorize_and_apply_controlled_candidate(request["request_id"], expected_application_digest=packet["application_digest"], authorization_phrase=packet["authorization_phrase"], runtime_root=runtime, python_executable=sys.executable)
    require(applied["ok"], "rollback_recovery_fixture_applied")
    rollback = prepare_controlled_rollback(request["request_id"], runtime_root=runtime)
    # Simulate a crash after restoring only main.py from the private backup.
    backup = json.loads(_backup_manifest_path(request["request_id"], runtime).read_text())
    main_backup = next(row for row in backup["entries"] if row["relative_path"] == "main.py")
    _write_candidate_file(project / "main.py", base64.b64decode(main_backup["content_b64"]))
    require((project / "helper.py").is_file() and (project / "main.py").read_bytes() == original_main, "partial_rollback_fixture_mixed_known_state")
    recovered = authorize_and_rollback_controlled_candidate(request["request_id"], expected_rollback_digest=rollback["rollback_digest"], authorization_phrase=rollback["authorization_phrase"], runtime_root=runtime)
    require(recovered["ok"] and recovered["status"] == "controlled_rollback_completed", "partial_rollback_recovered")
    require(not (project / "helper.py").exists() and (project / "main.py").read_bytes() == original_main, "rollback_recovery_restores_full_backup")

# Read-only health and handoff expose no paths, backups, provider payloads, or authority.
with tempfile.TemporaryDirectory(prefix="eid-v1255-handoff-") as td:
    base = Path(td); runtime = base / "runtime"; project = make_project(base)
    request, _, _ = prepare_fast_v1254_candidate(project, runtime)
    packet = prepare_controlled_application(request["request_id"], runtime_root=runtime)
    applied = authorize_and_apply_controlled_candidate(request["request_id"], expected_application_digest=packet["application_digest"], authorization_phrase=packet["authorization_phrase"], runtime_root=runtime, python_executable=sys.executable)
    health = inspect_controlled_application_health(request["request_id"], runtime_root=runtime)
    require(health["read_only"] and health["target_state"] == "candidate", "application_health_read_only_candidate_state")
    handoff = build_controlled_application_operator_handoff(request["request_id"], runtime_root=runtime)
    encoded = json.dumps(handoff)
    require(handoff["status"] == "controlled_application_operator_handoff_ready", "operator_handoff_ready")
    require(str(project) not in encoded and "content_b64" not in encoded and "fixture-private" not in encoded, "operator_handoff_content_minimized")
    for key, expected in DENIED_AUTHORITY.items():
        require(handoff.get(key) is expected, f"handoff_{key}_denied")

require(SOURCE_BEFORE == source_signature(), "eidolon_source_immutable_during_reliability_tests")
print(json.dumps({"ok": True, "version": "1255.8", "checks": len(CHECKS), "passed": len(CHECKS), "verification_failure_rollback": True, "expired_apply_recovery": True, "interrupted_rollback_recovery": True, "windows_casefold_hardening": True, "concurrent_exactly_once": True, "authority_granted": False}, sort_keys=True))
