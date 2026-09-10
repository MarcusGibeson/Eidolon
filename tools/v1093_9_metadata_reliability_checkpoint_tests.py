from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def seed(path: Path, value: object, *, bom: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, ensure_ascii=False) + "\n").encode("utf-8")
    path.write_bytes((b"\xef\xbb\xbf" if bom else b"") + payload)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_inventory_is_authoritative_and_content_free() -> None:
    from metadata_store_inventory import inspect_mutable_json_stores, list_mutable_json_stores

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        seed(root / "settings.json", {"mode": "strict"}, bom=True)
        stores = list_mutable_json_stores()
        result = inspect_mutable_json_stores(data_dir=root)
        encoded = json.dumps(result)
        require(len(stores) >= 22 and result["store_count"] == len(stores), "mutable-store inventory incomplete")
        require(result["payload_returned"] is False, "inventory claims payload exposure")
        require(str(root) not in encoded and "strict" not in encoded, "inventory leaked path or payload")
        require(any(row["store_id"] == "settings" and row["bom_file_count"] == 1 for row in result["stores"]), "BOM settings not inventoried")


def test_bom_invalid_and_wrong_root_reads_do_not_mutate() -> None:
    from json_storage import load_json_file

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        bom = root / "settings.json"
        invalid = root / "tasks.json"
        wrong = root / "approvals.json"
        seed(bom, {"name": "Eidolon"}, bom=True)
        invalid.write_bytes(b"{broken")
        seed(wrong, ["wrong-root"])
        before = {path: path.read_bytes() for path in (bom, invalid, wrong)}
        require(load_json_file(bom, {}, expected_type=dict)["name"] == "Eidolon", "BOM read failed")
        require(load_json_file(invalid, {"safe": True}, expected_type=dict) == {"safe": True}, "invalid fallback failed")
        require(load_json_file(wrong, {"safe": True}, expected_type=dict) == {"safe": True}, "wrong-root fallback failed")
        require(all(path.read_bytes() == payload for path, payload in before.items()), "read path rewrote source metadata")


def test_canonical_atomic_save_preserves_prior_on_invalid_shape() -> None:
    from json_storage import JsonStorageError, write_json_atomic

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        os.environ["EIDOLON_METADATA_LOCK_DIR"] = str(root / "locks")
        target = root / "settings.json"
        seed(target, {"before": True}, bom=True)
        write_json_atomic(target, {"message": "héllo", "value": 2}, expected_type=dict, sort_keys=True)
        raw = target.read_bytes()
        require(not raw.startswith(b"\xef\xbb\xbf") and raw.endswith(b"\n"), "save is not canonical BOM-free UTF-8")
        require(json.loads(raw.decode("utf-8"))["message"] == "héllo", "Unicode was not preserved")
        stable = raw
        try:
            write_json_atomic(target, ["wrong"], expected_type=dict)
        except JsonStorageError:
            pass
        else:
            raise AssertionError("wrong-root save was accepted")
        require(target.read_bytes() == stable, "invalid save replaced prior valid metadata")
        require(not list(root.glob(".settings.json.*.tmp")), "temporary file leaked after save")


def test_governed_preview_requires_literal_and_registry_confirmation() -> None:
    from metadata_migration_capability import apply_metadata_migration_capability, preview_metadata_migration_capability

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        os.environ["EIDOLON_METADATA_LOCK_DIR"] = str(root / "locks")
        settings = root / "settings.json"
        projects = root / "projects.json"
        seed(settings, {"mode": "safe"}, bom=True)
        seed(projects, {"active_project_id": "eidolon", "projects": []}, bom=True)
        preview = preview_metadata_migration_capability("settings", "settings.json", data_dir=root)
        denied = apply_metadata_migration_capability(
            "settings", "settings.json", preview_token=preview["preview_token"], operator_confirmed="true", data_dir=root
        )
        require(not denied["ok"] and settings.read_bytes().startswith(b"\xef\xbb\xbf"), "string confirmation was accepted")
        applied = apply_metadata_migration_capability(
            "settings", "settings.json", preview_token=preview["preview_token"], operator_confirmed=True, data_dir=root
        )
        require(applied["ok"] and applied["source_mutated"] and not settings.read_bytes().startswith(b"\xef\xbb\xbf"), "confirmed settings migration failed")
        project_preview = preview_metadata_migration_capability("projects", "projects.json", data_dir=root)
        project_denied = apply_metadata_migration_capability(
            "projects", "projects.json", preview_token=project_preview["preview_token"], operator_confirmed=True, data_dir=root
        )
        require(project_denied["status"] == "operator_registry_confirmation_required", "projects registry lacked dedicated confirmation")
        require(projects.read_bytes().startswith(b"\xef\xbb\xbf"), "projects registry changed without dedicated confirmation")


def test_competing_write_invalidates_preview() -> None:
    from json_storage import write_json_atomic
    from metadata_migration import apply_metadata_migration, preview_metadata_migration

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        os.environ["EIDOLON_METADATA_LOCK_DIR"] = str(root / "locks")
        target = root / "settings.json"
        seed(target, {"value": 1}, bom=True)
        preview = preview_metadata_migration("settings", "settings.json", data_dir=root)
        write_json_atomic(target, {"value": 2}, expected_type=dict)
        result = apply_metadata_migration(
            "settings", "settings.json", preview_token=preview["preview_token"], operator_confirmed=True, data_dir=root
        )
        require(result["status"] == "stale_or_mismatched_preview" and json.loads(target.read_text())["value"] == 2, "competing write did not stale preview")


def test_live_owner_preserved_and_dead_exact_owner_reclaimable() -> None:
    from metadata_mutation_coordination import inspect_metadata_lock, metadata_lock_path, metadata_mutation_lock

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "settings.json"
        seed(target, {"value": 1})
        os.environ["EIDOLON_METADATA_LOCK_DIR"] = str(root / "locks")
        with metadata_mutation_lock(target):
            live = inspect_metadata_lock(target)
            require(live["owner_active"] and not live["safe_cleanup"], "live owner was treated as reclaimable")
        lock = metadata_lock_path(target)
        lock.parent.mkdir(parents=True, exist_ok=True)
        target_digest = hashlib.sha256(str(target.resolve()).encode("utf-8")).hexdigest()
        lock.write_text(json.dumps({"pid": 99999999, "owner_token": "a" * 32, "target_digest": target_digest}), encoding="utf-8")
        dead = inspect_metadata_lock(target)
        require(dead["owner_abandoned"] and dead["safe_cleanup"], "dead exact owner was not reclaimable")


def test_unbound_temporary_requires_operator_review() -> None:
    from metadata_artifact_reconciliation import inspect_orphaned_metadata_artifacts, reconcile_orphaned_metadata_artifacts

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        os.environ["EIDOLON_METADATA_LOCK_DIR"] = str(root / "locks")
        temporary = root / ".settings.json.transaction-7-orphan.tmp"
        seed(temporary, {"plausible": True})
        state = inspect_orphaned_metadata_artifacts(data_dir=root)
        row = next(row for row in state["rows"] if row["artifact_type"] == "temporary_file")
        require(row["status"] == "operator_review" and not row["safe_cleanup"], "unbound temporary was advertised as recoverable")
        reconcile_orphaned_metadata_artifacts(operator_confirmed=True, data_dir=root)
        require(temporary.exists(), "unbound temporary was deleted")


def test_duplicate_verified_backup_cleanup_matches_advertised_control() -> None:
    from metadata_artifact_reconciliation import inspect_orphaned_metadata_artifacts, reconcile_orphaned_metadata_artifacts

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "settings.json"
        backup = root / "metadata_migration_backups" / "settings" / "settings.json.pre-utf8-migration-duplicate.bak"
        seed(target, {"value": 1})
        backup.parent.mkdir(parents=True, exist_ok=True)
        backup.write_bytes(target.read_bytes())
        state = inspect_orphaned_metadata_artifacts(data_dir=root)
        row = next(row for row in state["rows"] if row["artifact_type"] == "migration_backup")
        require(row["status"] == "safe_cleanup" and state["safe_cleanup_available"], "duplicate backup not advertised as safe cleanup")
        denied = reconcile_orphaned_metadata_artifacts(operator_confirmed=False, data_dir=root)
        require(denied["status"] == "confirmation_required" and backup.exists(), "unconfirmed duplicate backup cleanup mutated")
        done = reconcile_orphaned_metadata_artifacts(operator_confirmed=True, data_dir=root)
        require(done["removed"] == 1 and not backup.exists(), "confirmed cleanup did not remove advertised duplicate backup")


def test_tampered_recovery_record_fails_closed() -> None:
    from metadata_migration_recovery import begin_migration_recovery, recover_pending_metadata_migrations, update_migration_recovery

    with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as outside_td:
        root = Path(td)
        target = root / "settings.json"
        outside = Path(outside_td) / "outside.json"
        seed(target, {"value": 1})
        seed(outside, {"outside": True})
        record = begin_migration_recovery(
            target,
            original_sha256=digest(target),
            canonical_sha256="b" * 64,
            expected_root_type="dict",
            data_dir=root,
        )
        update_migration_recovery(record, stage="replacement_started", data_dir=root)
        record_path = root / "metadata_migration_state" / f"{record['operation_id']}.json"
        tampered = json.loads(record_path.read_text(encoding="utf-8"))
        tampered["target_path"] = str(outside)
        record_path.write_text(json.dumps(tampered), encoding="utf-8")
        before = outside.read_bytes()
        result = recover_pending_metadata_migrations(operator_confirmed=True, data_dir=root)
        require(result["uncertain"] == 1 and result["results"][0]["status"] == "unsafe_private_record", "tampered recovery record did not fail closed")
        require(outside.read_bytes() == before, "tampered recovery record touched external target")


def test_daily_state_and_dashboard_are_content_free_and_provider_free() -> None:
    from metadata_recovery_state import build_metadata_recovery_state

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        seed(root / "settings.json", {"secret": "PRIVATE_PAYLOAD"})
        os.environ["EIDOLON_METADATA_LOCK_DIR"] = str(root / "locks")
        state = build_metadata_recovery_state(data_dir=root)
        encoded = json.dumps(state)
        require(state["controls"]["ordinary_conversation_available"] and state["provider_contacted"] is False, "daily recovery state blocks chat or contacts provider")
        require(str(root) not in encoded and "PRIVATE_PAYLOAD" not in encoded, "daily recovery state leaked content")
    dashboard = (AGENT / "dashboard.py").read_text(encoding="utf-8")
    console = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
    do_post = dashboard.index("    def do_POST")
    require(dashboard.index('if path == "/api/metadata-recovery-state"') < do_post, "status route is not read-only GET")
    require(dashboard.index('if parsed.path == "/api/metadata-recovery/reconcile"') > do_post, "cleanup route is not POST")
    require("window.setTimeout(refreshMetadataRecoveryState, 0)" in console, "recovery panel is not asynchronously initialized")


def test_source_tree_excludes_private_runtime_artifacts() -> None:
    forbidden_names = {"projects.json", "tasks.json", "memories.json", "approvals"}
    violations: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT).as_posix()
        if relative == "data/projects.json":
            violations.append(relative)
        if "/__pycache__/" in f"/{relative}" or relative.endswith((".pyc", ".pyo")):
            violations.append(relative)
        if "metadata_migration_backups" in relative or "metadata_mutation_locks" in relative or "metadata_migration_recovery" in relative:
            # Module and test names are allowed; only runtime directories beneath data are forbidden.
            if relative.startswith("data/"):
                violations.append(relative)
        if relative == "data/projects.json" or relative in {"data/tasks.json", "data/memories.json"} or relative.startswith("data/approvals/"):
            violations.append(relative)
    require(not violations, f"private runtime artifacts found: {violations[:5]}")


def test_release_metadata_history_and_registration() -> None:
    from release_metadata import RUNTIME_VERSION
    require(tuple(map(int, RUNTIME_VERSION.split("."))) >= (1093, 9), "runtime version regressed below v1093.9")
    from release_history import parse_release_history_file
    parsed_history = parse_release_history_file(ROOT / "README_RELEASE_HISTORY.md")
    require(parsed_history.get("ok"), parsed_history)
    require(sum(1 for row in parsed_history.get("public_entries") or [] if row.get("version") == "1093.9" and not row.get("range_end")) == 1, "checkpoint history duplicated or missing")
    require(parsed_history.get("duplicate_version_count") == 0 and parsed_history.get("ordering_violation_count") == 0, parsed_history)
    next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
    require("v1150" in next_steps, "Codex schedule missing")
    registry = (ROOT / "tools" / "post_review_development_verify.py").read_text(encoding="utf-8")
    checkpoint = 'SuiteSpec("v1093.9-metadata-reliability-checkpoint", "tools/v1093_9_metadata_reliability_checkpoint_tests.py", arguments=(), profiles=("core", "full"))'
    require(checkpoint in registry, "checkpoint suite not registered")
    require(registry.index("v1093.9-metadata-reliability-checkpoint") < registry.index("v1093.8-daily-use-metadata-recovery-hardening"), "checkpoint suite is not first")


def main() -> int:
    tests = [
        test_inventory_is_authoritative_and_content_free,
        test_bom_invalid_and_wrong_root_reads_do_not_mutate,
        test_canonical_atomic_save_preserves_prior_on_invalid_shape,
        test_governed_preview_requires_literal_and_registry_confirmation,
        test_competing_write_invalidates_preview,
        test_live_owner_preserved_and_dead_exact_owner_reclaimable,
        test_unbound_temporary_requires_operator_review,
        test_duplicate_verified_backup_cleanup_matches_advertised_control,
        test_tampered_recovery_record_fails_closed,
        test_daily_state_and_dashboard_are_content_free_and_provider_free,
        test_source_tree_excludes_private_runtime_artifacts,
        test_release_metadata_history_and_registration,
    ]
    failures: list[str] = []
    passed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as error:
            failures.append(f"{test.__name__}: {type(error).__name__}: {error}")
    report = {
        "version": "1093.9",
        "suite": "metadata-reliability-checkpoint",
        "passed": passed,
        "total": len(tests),
        "ok": passed == len(tests),
        "failures": failures,
    }
    print(json.dumps(report, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
