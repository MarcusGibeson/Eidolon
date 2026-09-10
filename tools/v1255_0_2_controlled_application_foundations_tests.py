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

from controlled_application_rollback_foundations import (
    CONTRACT_VERSION,
    DENIED_AUTHORITY,
    build_private_backup_manifest,
    inspect_controlled_application_conflicts,
    load_controlled_application,
    load_controlled_application_backup_scope,
    prepare_controlled_application,
    public_controlled_application,
    validate_private_backup_manifest,
)
from isolated_coding_execution_foundations import load_coding_work_request
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

# Baseline packet is immutable, content minimized, and grants no authority.
with tempfile.TemporaryDirectory(prefix="eid-v1255-0-2-") as td:
    base = Path(td); runtime = base / "runtime"; project = make_project(base)
    selected_before = tree_signature(project)
    request, result, provider = prepare_v1254_candidate(project, runtime)
    require(provider.calls == 1 and result["test_passed"], "passing_v1254_candidate_ready")
    conflict = inspect_controlled_application_conflicts(request["request_id"], runtime_root=runtime)
    require(conflict["ok"] and conflict["status"] == "controlled_application_paths_clear", "changed_paths_clear")
    require(conflict["conflict_count"] == 0 and conflict["source_manifest_changed"] is False, "baseline_manifest_fresh")
    packet = prepare_controlled_application(request["request_id"], runtime_root=runtime)
    require(packet["ok"] and packet["status"] == "controlled_application_authorization_required", "application_packet_prepared")
    require(packet["contract_version"] == CONTRACT_VERSION == "v1255.2", "foundation_contract_version")
    require(packet["change_count"] == 1 and packet["changes"][0]["relative_path"] == "main.py", "candidate_scope_exact")
    require(packet["changes"][0]["operation"] == "modify", "candidate_operation_classified")
    require(packet["authorization_phrase"].startswith("Authorize controlled application for request "), "exact_application_phrase_emitted")
    require(packet["backup_required_before_first_write"] and packet["rollback_required_on_partial_failure"], "backup_and_failure_rollback_required")
    require(packet["rollback_requires_separate_authorization_after_success"], "successful_rollback_separate_authority")
    require(tree_signature(project) == selected_before, "preparation_does_not_modify_selected_project")
    for key, expected in DENIED_AUTHORITY.items():
        require(packet.get(key) is expected, f"prepared_{key}_denied")
    restored = prepare_controlled_application(request["request_id"], runtime_root=runtime)
    require(restored["operation_status"] == "restored" and restored["application_digest"] == packet["application_digest"], "application_packet_idempotent")
    require(load_controlled_application(request["request_id"], runtime_root=runtime)["application_digest"] == packet["application_digest"], "application_packet_reload_valid")
    scope = load_controlled_application_backup_scope(request["request_id"], runtime_root=runtime)
    require(scope["entry_count"] == 1 and scope["private_contents_captured"] is False, "backup_scope_prepared_without_private_capture")
    pub = public_controlled_application(packet)
    encoded = json.dumps(pub)
    require(str(project) not in encoded and "fixture-private" not in encoded, "public_packet_hides_private_path_and_content")
    require(pub["backup_content_exposed"] is False and pub["private_project_path_exposed"] is False, "public_packet_privacy_flags")

# Unrelated operator edits are preserved as drift, not misclassified as a conflict.
with tempfile.TemporaryDirectory(prefix="eid-v1255-unrelated-") as td:
    base = Path(td); runtime = base / "runtime"; project = make_project(base)
    request, _, _ = prepare_v1254_candidate(project, runtime)
    (project / "README.md").write_text("# Calculator\noperator changed unrelated notes\n", encoding="utf-8")
    state = inspect_controlled_application_conflicts(request["request_id"], runtime_root=runtime)
    require(state["ok"] and state["source_manifest_changed"], "unrelated_source_drift_detected")
    require(state["unrelated_source_changes_allowed"], "unrelated_source_drift_allowed")
    require(state["conflict_count"] == 0, "unrelated_edit_not_conflict")
    packet = prepare_controlled_application(request["request_id"], runtime_root=runtime)
    require(packet["ok"] and packet["unrelated_source_changes_allowed"], "packet_preserves_unrelated_edit")

# Same-path operator edit fails closed.
with tempfile.TemporaryDirectory(prefix="eid-v1255-conflict-") as td:
    base = Path(td); runtime = base / "runtime"; project = make_project(base)
    request, _, _ = prepare_v1254_candidate(project, runtime)
    (project / "main.py").write_text("# operator edit\ndef add(a,b): return 100\n", encoding="utf-8")
    state = inspect_controlled_application_conflicts(request["request_id"], runtime_root=runtime)
    require(not state["ok"] and state["conflict_count"] == 1, "same_path_conflict_detected")
    blocked = prepare_controlled_application(request["request_id"], runtime_root=runtime)
    require(blocked["ok"] is False and blocked["status"] == "controlled_application_conflict_detected", "same_path_conflict_blocks_packet")

# Create and delete operations are represented against the sealed baseline.
with tempfile.TemporaryDirectory(prefix="eid-v1255-create-delete-") as td:
    base = Path(td); runtime = base / "runtime"; project = make_project(base)
    provider = CandidateProvider(create_extra=True, delete_readme=True)
    request, _, _ = prepare_v1254_candidate(project, runtime, provider=provider)
    packet = prepare_controlled_application(request["request_id"], runtime_root=runtime)
    operations = {row["relative_path"]: row["operation"] for row in packet["changes"]}
    require(operations == {"README.md": "delete", "helper.py": "create", "main.py": "modify"}, "create_modify_delete_scope_classified")
    create = next(row for row in packet["changes"] if row["relative_path"] == "helper.py")
    delete = next(row for row in packet["changes"] if row["relative_path"] == "README.md")
    require(create["baseline_existed"] is False and bool(create["candidate_content_digest"]), "create_baseline_absent")
    require(delete["baseline_existed"] is True and delete["candidate_content_digest"] == "", "delete_candidate_absent")

# Backup helper is private, exact, bounded, and tamper evident, but not persisted by preparation.
with tempfile.TemporaryDirectory(prefix="eid-v1255-backup-") as td:
    base = Path(td); runtime = base / "runtime"; project = make_project(base)
    request, _, _ = prepare_v1254_candidate(project, runtime)
    packet = prepare_controlled_application(request["request_id"], runtime_root=runtime)
    backup = build_private_backup_manifest(request["request_id"], packet, project)
    require(validate_private_backup_manifest(backup, expected_application_digest=packet["application_digest"]), "private_backup_manifest_valid")
    require(backup["entry_count"] == 1 and backup["entries"][0]["content_b64"], "private_backup_contains_exact_preapply_bytes")
    tampered = json.loads(json.dumps(backup)); tampered["entries"][0]["content_b64"] = "AAAA"
    require(not validate_private_backup_manifest(tampered, expected_application_digest=packet["application_digest"]), "tampered_private_backup_rejected")
    require(not (runtime / "development_campaigns" / "controlled_application_backups" / f"{request['request_id']}.json").exists(), "preparation_does_not_capture_private_backup")

# Cancelled requests cannot graduate into application packets.
with tempfile.TemporaryDirectory(prefix="eid-v1255-cancel-") as td:
    base = Path(td); runtime = base / "runtime"; project = make_project(base)
    request, _, _ = prepare_v1254_candidate(project, runtime)
    from isolated_coding_execution_foundations import _request_path, _sealed, _atomic_json
    row = load_coding_work_request(request["request_id"], runtime_root=runtime)
    row["cancelled"] = True; row["lifecycle_state"] = "cancelled"
    row = _sealed(row, "record_digest"); _atomic_json(_request_path(request["request_id"], runtime), row)
    blocked = prepare_controlled_application(request["request_id"], runtime_root=runtime)
    require(blocked["ok"] is False and blocked["status"] == "coding_work_request_cancelled", "cancelled_request_blocks_application")

require(SOURCE_BEFORE == source_signature(), "eidolon_source_immutable_during_foundation_tests")
print(json.dumps({"ok": True, "version": "1255.2", "checks": len(CHECKS), "passed": len(CHECKS), "controlled_application_preparation": True, "selective_conflict_detection": True, "private_backup_capture_deferred": True, "authority_granted": False}, sort_keys=True))
