from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "conscious_agent"))
sys.path.insert(0, str(ROOT / "tools"))
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

from controlled_application_rollback_foundations import prepare_controlled_application
from controlled_application_rollback import (
    authorize_and_apply_controlled_candidate,
    authorize_and_rollback_controlled_candidate,
    load_controlled_application_execution,
    load_controlled_rollback_result,
    prepare_controlled_rollback,
    process_controlled_application_rollback_control,
    public_controlled_application_result,
    public_controlled_rollback,
)
from v1255_test_support import CandidateProvider, make_project, prepare_v1254_candidate, tree_signature

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

# Exact application preserves unrelated user changes, verifies the live project,
# prepares an external rollback backup, and supports exact rollback.
with tempfile.TemporaryDirectory(prefix="eid-v1255-3-5-") as td:
    base = Path(td); runtime = base / "runtime"; project = make_project(base)
    original_main = (project / "main.py").read_bytes()
    original_private = (project / ".env").read_bytes()
    request, _, provider = prepare_v1254_candidate(project, runtime)
    (project / "README.md").write_text("# Calculator\noperator edit after review\n", encoding="utf-8")
    unrelated_after = (project / "README.md").read_bytes()
    packet = prepare_controlled_application(request["request_id"], runtime_root=runtime)
    require(packet["ok"] and packet["unrelated_source_changes_allowed"], "application_packet_allows_unrelated_operator_change")

    wrong = authorize_and_apply_controlled_candidate(
        request["request_id"], expected_application_digest=packet["application_digest"],
        authorization_phrase="apply it", runtime_root=runtime, python_executable=sys.executable,
    )
    require(wrong["status"] == "controlled_application_exact_authorization_required", "approximate_apply_authorization_rejected")
    require((project / "main.py").read_bytes() == original_main, "wrong_authorization_does_not_mutate_project")
    backup_path = runtime / "development_campaigns" / "controlled_application_backups" / f"{request['request_id']}.json"
    require(not backup_path.exists(), "wrong_authorization_does_not_capture_private_backup")

    applied = authorize_and_apply_controlled_candidate(
        request["request_id"], expected_application_digest=packet["application_digest"],
        authorization_phrase=packet["authorization_phrase"], runtime_root=runtime, python_executable=sys.executable,
    )
    require(applied["ok"] and applied["status"] == "controlled_application_completed", "controlled_application_completed")
    require(applied["applied_count"] == 1 and applied["authorization_consumption_count"] == 1, "single_application_authorization_consumed")
    require(applied["backup_prepared"] and backup_path.is_file(), "private_backup_persisted_before_write")
    require(applied["verification_passed"] and applied["tests_executed"], "post_apply_live_verification_passed")
    require("subtract" in (project / "main.py").read_text(encoding="utf-8"), "candidate_installed_in_selected_project")
    require((project / "README.md").read_bytes() == unrelated_after, "unrelated_operator_edit_preserved")
    require((project / ".env").read_bytes() == original_private, "private_runtime_file_untouched")
    require(provider.calls == 1, "application_does_not_recontact_provider")
    backup_text = backup_path.read_text(encoding="utf-8")
    require("content_b64" in backup_text and str(project) not in backup_text, "backup_contains_bytes_without_selected_project_path")

    sealed = load_controlled_application_execution(request["request_id"], runtime_root=runtime)
    require(sealed["phase"] == "sealed" and sealed["authorization_consumed"], "application_execution_sealed")
    require(sealed["application_execution_authorized"] is False and sealed["release_authorized"] is False, "sealed_application_authority_denied")
    public = public_controlled_application_result(applied)
    require(public["selected_project_modified"] and public["rollback_available"], "public_application_reports_applied_state")
    require(str(project) not in json.dumps(public) and "content_b64" not in json.dumps(public), "public_application_hides_path_and_backup")

    replay = authorize_and_apply_controlled_candidate(
        request["request_id"], expected_application_digest=packet["application_digest"],
        authorization_phrase=packet["authorization_phrase"], runtime_root=runtime, python_executable=sys.executable,
    )
    require(replay["operation_status"] == "restored" and replay["application_result_digest"] == applied["application_result_digest"], "apply_replay_idempotent")
    require(provider.calls == 1, "apply_replay_no_provider_contact")

    rollback = prepare_controlled_rollback(request["request_id"], runtime_root=runtime)
    require(rollback["ok"] and rollback["status"] == "controlled_rollback_authorization_required", "rollback_packet_prepared")
    require(rollback["authorization_phrase"].startswith("Authorize controlled rollback for request "), "exact_rollback_phrase_emitted")
    require("subtract" in (project / "main.py").read_text(), "prepare_rollback_does_not_change_applied_project")
    wrong_rollback = authorize_and_rollback_controlled_candidate(
        request["request_id"], expected_rollback_digest=rollback["rollback_digest"], authorization_phrase="rollback", runtime_root=runtime,
    )
    require(wrong_rollback["status"] == "controlled_rollback_exact_authorization_required", "approximate_rollback_authorization_rejected")
    require("subtract" in (project / "main.py").read_text(), "wrong_rollback_authorization_preserves_applied_state")
    rolled = authorize_and_rollback_controlled_candidate(
        request["request_id"], expected_rollback_digest=rollback["rollback_digest"], authorization_phrase=rollback["authorization_phrase"], runtime_root=runtime,
    )
    require(rolled["ok"] and rolled["status"] == "controlled_rollback_completed", "controlled_rollback_completed")
    require((project / "main.py").read_bytes() == original_main, "rollback_restores_original_affected_file")
    require((project / "README.md").read_bytes() == unrelated_after, "rollback_preserves_unrelated_operator_edit")
    require((project / ".env").read_bytes() == original_private, "rollback_preserves_private_runtime_file")
    require(rolled["authorization_consumption_count"] == 1 and rolled["rollback_verified"], "rollback_exactly_once_and_verified")
    public_rb = public_controlled_rollback(rolled)
    require(str(project) not in json.dumps(public_rb) and public_rb["backup_content_exposed"] is False, "public_rollback_privacy_safe")
    rb_replay = authorize_and_rollback_controlled_candidate(
        request["request_id"], expected_rollback_digest=rollback["rollback_digest"], authorization_phrase=rollback["authorization_phrase"], runtime_root=runtime,
    )
    require(rb_replay["operation_status"] == "restored" and rb_replay["rollback_result_digest"] == rolled["rollback_result_digest"], "rollback_replay_idempotent")

# Conflicting same-path edit after packet preparation blocks before authorization
# consumption and before private backup capture.
with tempfile.TemporaryDirectory(prefix="eid-v1255-stale-between-") as td:
    base = Path(td); runtime = base / "runtime"; project = make_project(base)
    request, _, _ = prepare_v1254_candidate(project, runtime)
    packet = prepare_controlled_application(request["request_id"], runtime_root=runtime)
    (project / "main.py").write_text("def add(a,b): return 999\n", encoding="utf-8")
    blocked = authorize_and_apply_controlled_candidate(
        request["request_id"], expected_application_digest=packet["application_digest"], authorization_phrase=packet["authorization_phrase"], runtime_root=runtime, python_executable=sys.executable,
    )
    require(blocked["status"] == "controlled_application_conflict_detected", "same_path_change_after_packet_blocks_apply")
    require(not (runtime / "development_campaigns" / "controlled_application_authorizations" / f"{request['request_id']}.json").exists(), "conflict_does_not_consume_apply_authorization")
    require(not (runtime / "development_campaigns" / "controlled_application_backups" / f"{request['request_id']}.json").exists(), "conflict_does_not_capture_backup")

# Create and delete candidate operations apply and roll back exactly.
with tempfile.TemporaryDirectory(prefix="eid-v1255-create-delete-apply-") as td:
    base = Path(td); runtime = base / "runtime"; project = make_project(base)
    original_readme = (project / "README.md").read_bytes()
    request, _, _ = prepare_v1254_candidate(project, runtime, provider=CandidateProvider(create_extra=True, delete_readme=True))
    packet = prepare_controlled_application(request["request_id"], runtime_root=runtime)
    applied = authorize_and_apply_controlled_candidate(request["request_id"], expected_application_digest=packet["application_digest"], authorization_phrase=packet["authorization_phrase"], runtime_root=runtime, python_executable=sys.executable)
    require(applied["ok"] and (project / "helper.py").is_file() and not (project / "README.md").exists(), "create_modify_delete_apply_exact")
    rollback = prepare_controlled_rollback(request["request_id"], runtime_root=runtime)
    rolled = authorize_and_rollback_controlled_candidate(request["request_id"], expected_rollback_digest=rollback["rollback_digest"], authorization_phrase=rollback["authorization_phrase"], runtime_root=runtime)
    require(rolled["ok"] and not (project / "helper.py").exists(), "rollback_removes_created_file")
    require((project / "README.md").read_bytes() == original_readme, "rollback_restores_deleted_file")

# Ordinary conversation control requires the explicit preparation and exact
# authorization phrases; discussion-like text remains inactive.
with tempfile.TemporaryDirectory(prefix="eid-v1255-conversation-") as td:
    base = Path(td); runtime = base / "runtime"; project = make_project(base)
    request, _, _ = prepare_v1254_candidate(project, runtime)
    inactive = process_controlled_application_rollback_control("It would be nice to apply this someday.", runtime_root=runtime)
    require(inactive["active"] is False, "casual_application_discussion_inactive")
    prepared = process_controlled_application_rollback_control(f"Prepare controlled application for request {request['request_id']}.", runtime_root=runtime)
    require(prepared["active"] and prepared["event"] == "controlled_application_authorization_required", "conversation_prepare_application_active")
    phrase = prepared["controlled_application"]["authorization_phrase"]
    applied = process_controlled_application_rollback_control(phrase, runtime_root=runtime, python_executable=sys.executable)
    require(applied["active"] and applied["event"] == "controlled_application_completed", "conversation_exact_apply_active")
    rbprep = process_controlled_application_rollback_control(f"Prepare controlled rollback for request {request['request_id']}.", runtime_root=runtime)
    require(rbprep["active"] and rbprep["event"] == "controlled_rollback_authorization_required", "conversation_prepare_rollback_active")
    rb = process_controlled_application_rollback_control(rbprep["controlled_rollback"]["authorization_phrase"], runtime_root=runtime)
    require(rb["active"] and rb["event"] == "controlled_rollback_completed", "conversation_exact_rollback_active")

require(SOURCE_BEFORE == source_signature(), "eidolon_source_immutable_during_integration_tests")
print(json.dumps({"ok": True, "version": "1255.5", "checks": len(CHECKS), "passed": len(CHECKS), "transactional_apply": True, "post_apply_verification": True, "separate_exact_rollback": True, "unrelated_user_changes_preserved": True, "authority_granted": False}, sort_keys=True))
