from __future__ import annotations

import importlib
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def write_bom(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\xef\xbb\xbf" + json.dumps(value, indent=2).encode("utf-8"))


def test_preview_is_content_free_and_non_mutating() -> None:
    from metadata_migration import preview_metadata_migration
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "settings.json"
        write_bom(target, {"safe_mode": "strict"})
        before = target.read_bytes()
        preview = preview_metadata_migration("settings", "settings.json", data_dir=root)
        require(preview["ok"] and preview["status"] == "migration_available", "migration preview failed")
        require(len(preview["preview_token"]) == 64, "preview token is not digest-bound")
        require(preview["detected_encoding"] == "utf-8-bom", "encoding was not bound")
        require(preview["root_type"] == "dict" and preview["expected_root_type"] == "dict", "root shape was not bound")
        require(preview["canonical_sha256"] and preview["content_sha256"] != preview["canonical_sha256"], "canonical output was not bound")
        require(preview["payload_returned"] is False and preview["absolute_path_returned"] is False, "preview leaked private content")
        require(target.read_bytes() == before, "preview mutated source")


def test_apply_requires_exact_confirmation_and_creates_verified_private_backup() -> None:
    from metadata_migration import apply_metadata_migration, preview_metadata_migration
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "settings.json"
        write_bom(target, {"safe_mode": "strict", "value": "☃"})
        preview = preview_metadata_migration("settings", "settings.json", data_dir=root)
        denied = apply_metadata_migration("settings", "settings.json", preview_token=preview["preview_token"], operator_confirmed=False, data_dir=root)
        require(denied["status"] == "confirmation_required" and target.read_bytes().startswith(b"\xef\xbb\xbf"), "unconfirmed migration wrote source")
        applied = apply_metadata_migration("settings", "settings.json", preview_token=preview["preview_token"], operator_confirmed=True, data_dir=root)
        require(applied["ok"] and applied["status"] == "migrated", "confirmed migration failed")
        require(applied["backup_created"] and applied["backup_verified"], "verified backup missing")
        require(not target.read_bytes().startswith(b"\xef\xbb\xbf"), "BOM remained after migration")
        backups = list((root / "metadata_migration_backups" / "settings").glob("*.bak"))
        require(len(backups) == 1 and backups[0].read_bytes().startswith(b"\xef\xbb\xbf"), "private backup does not preserve original")


def test_stale_preview_is_rejected() -> None:
    from metadata_migration import apply_metadata_migration, preview_metadata_migration
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "tasks.json"
        write_bom(target, {"version": 2, "tasks": []})
        preview = preview_metadata_migration("tasks", "tasks.json", data_dir=root)
        write_bom(target, {"version": 3, "tasks": []})
        current = target.read_bytes()
        result = apply_metadata_migration("tasks", "tasks.json", preview_token=preview["preview_token"], operator_confirmed=True, data_dir=root)
        require(result["status"] == "stale_or_mismatched_preview", "stale preview was accepted")
        require(target.read_bytes() == current, "stale preview changed source")
        require(not (root / "metadata_migration_backups").exists(), "stale preview created backup")


def test_invalid_json_and_shape_are_never_replaced() -> None:
    from metadata_migration import apply_metadata_migration, preview_metadata_migration
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        invalid = root / "settings.json"
        invalid.write_bytes(b"\xef\xbb\xbf{broken")
        before = invalid.read_bytes()
        preview = preview_metadata_migration("settings", "settings.json", data_dir=root)
        require(preview["status"] == "invalid_json" and not preview["ok"], "invalid JSON preview was not blocked")
        result = apply_metadata_migration("settings", "settings.json", preview_token="x" * 64, operator_confirmed=True, data_dir=root)
        require(not result["ok"] and invalid.read_bytes() == before, "invalid JSON was replaced")
        wrong = root / "tasks.json"
        write_bom(wrong, [1, 2, 3])
        wrong_before = wrong.read_bytes()
        preview_wrong = preview_metadata_migration("tasks", "tasks.json", data_dir=root)
        require(preview_wrong["status"] == "invalid_root_shape", "wrong root shape was not blocked")
        require(wrong.read_bytes() == wrong_before, "wrong-root file was modified")


def test_operator_projects_registry_requires_dedicated_confirmation() -> None:
    from metadata_migration import apply_metadata_migration, preview_metadata_migration
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "projects.json"
        write_bom(target, {"active_project_id": "eidolon", "projects": []})
        preview = preview_metadata_migration("projects", "projects.json", data_dir=root)
        blocked = apply_metadata_migration("projects", "projects.json", preview_token=preview["preview_token"], operator_confirmed=True, data_dir=root)
        require(blocked["status"] == "operator_registry_confirmation_required", "operator registry did not require dedicated confirmation")
        require(target.read_bytes().startswith(b"\xef\xbb\xbf"), "operator registry changed without dedicated confirmation")
        applied = apply_metadata_migration("projects", "projects.json", preview_token=preview["preview_token"], operator_confirmed=True, operator_registry_confirmed=True, data_dir=root)
        require(applied["ok"] and applied["status"] == "migrated", "dedicated operator registry confirmation failed")


def test_write_interruption_restores_original() -> None:
    storage = importlib.import_module("json_storage")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "settings.json"
        write_bom(target, {"safe_mode": "strict"})
        original = target.read_bytes()
        preview = storage.preview_json_migration(target, expected_type=dict)
        original_writer = storage.write_json_atomic
        storage.write_json_atomic = lambda *args, **kwargs: (_ for _ in ()).throw(OSError("simulated interruption"))
        try:
            result = storage.apply_json_migration(target, preview_token=preview["preview_token"], operator_confirmed=True, expected_type=dict, backup_dir=root / "private_backups")
        finally:
            storage.write_json_atomic = original_writer
        require(result["status"] == "write_failed", "interruption was not reported")
        require(target.read_bytes() == original, "interrupted migration did not preserve original")


def test_path_and_store_family_boundaries() -> None:
    from metadata_migration import MetadataMigrationError, preview_metadata_migration
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        for store_id, relative in [("settings", "../settings.json"), ("tasks", "settings.json"), ("unknown", "x.json")]:
            try:
                preview_metadata_migration(store_id, relative, data_dir=root)
            except MetadataMigrationError:
                pass
            else:
                raise AssertionError(f"unsafe migration target accepted: {store_id} {relative}")


def test_already_canonical_is_noop() -> None:
    from metadata_migration import apply_metadata_migration, preview_metadata_migration
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "settings.json"
        target.write_text('{"safe_mode": "strict"}\n', encoding="utf-8")
        before = target.read_bytes()
        preview = preview_metadata_migration("settings", "settings.json", data_dir=root)
        require(preview["status"] == "already_canonical", "canonical file was not recognized")
        result = apply_metadata_migration("settings", "settings.json", preview_token=preview["preview_token"], operator_confirmed=True, data_dir=root)
        require(result["ok"] and result["status"] == "already_canonical", "canonical no-op failed")
        require(target.read_bytes() == before, "canonical no-op rewrote file")
        require(not (root / "metadata_migration_backups").exists(), "canonical no-op created backup")


def test_release_metadata_and_docs() -> None:
    release = (AGENT / "release_metadata.py").read_text(encoding="utf-8")
    import re
    match = re.search(r'RUNTIME_VERSION = "(\d+)\.(\d+)"', release)
    require(bool(match) and tuple(map(int, match.groups())) >= (1093, 2), "runtime version regressed")
    require("v1093.2" in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8"), "history missing v1093.2")
    require("v1093.3" in (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8"), "next bundle missing")
    require("v1150" in (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8"), "Codex schedule missing")


def main() -> int:
    tests = [
        test_preview_is_content_free_and_non_mutating,
        test_apply_requires_exact_confirmation_and_creates_verified_private_backup,
        test_stale_preview_is_rejected,
        test_invalid_json_and_shape_are_never_replaced,
        test_operator_projects_registry_requires_dedicated_confirmation,
        test_write_interruption_restores_original,
        test_path_and_store_family_boundaries,
        test_already_canonical_is_noop,
        test_release_metadata_and_docs,
    ]
    failures: list[str] = []
    passed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as error:
            failures.append(f"{test.__name__}: {type(error).__name__}: {error}")
    report = {"version": "1093.2", "suite": "previewed-backup-bound-metadata-migration", "passed": passed, "total": len(tests), "ok": passed == len(tests), "failures": failures}
    print(json.dumps(report, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
