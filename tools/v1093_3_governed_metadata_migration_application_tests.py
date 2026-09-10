from __future__ import annotations

import json
import os
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
    path.write_bytes(b"\xef\xbb\xbf" + json.dumps(value, ensure_ascii=False).encode("utf-8"))


def test_inventory_is_content_free_and_non_mutating() -> None:
    from metadata_migration_capability import metadata_migration_inventory
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        write_bom(root / "settings.json", {"token": "PRIVATE_VALUE", "safe_mode": "strict"})
        before = (root / "settings.json").read_bytes()
        result = metadata_migration_inventory(data_dir=root)
        require(result["ok"] and result["status"] == "inventory_ready", "inventory unavailable")
        require(result["bulk_migration_supported"] is False, "bulk migration was exposed")
        require(result["payload_returned"] is False and result["absolute_path_returned"] is False, "inventory leaked content")
        require("PRIVATE_VALUE" not in json.dumps(result), "inventory leaked payload")
        require((root / "settings.json").read_bytes() == before, "inventory mutated source")


def test_preview_is_exact_file_and_read_only() -> None:
    from metadata_migration_capability import preview_metadata_migration_capability
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        write_bom(root / "tasks.json", {"version": 2, "tasks": []})
        before = (root / "tasks.json").read_bytes()
        result = preview_metadata_migration_capability("tasks", "tasks.json", data_dir=root)
        require(result["ok"] and result["status"] == "migration_available", "preview unavailable")
        require(result["exact_file_required"] and not result["bulk_migration_supported"], "preview scope widened")
        require(len(result["preview_token"]) == 64, "preview token missing")
        require(result["private_backup_reference_returned"] is False, "backup path leaked")
        require((root / "tasks.json").read_bytes() == before, "preview mutated source")


def test_apply_requires_exact_token_and_confirmation() -> None:
    from metadata_migration_capability import apply_metadata_migration_capability, preview_metadata_migration_capability
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "settings.json"
        write_bom(target, {"safe_mode": "strict"})
        preview = preview_metadata_migration_capability("settings", "settings.json", data_dir=root)
        denied = apply_metadata_migration_capability("settings", "settings.json", preview_token=preview["preview_token"], operator_confirmed=False, data_dir=root)
        require(denied["status"] == "confirmation_required" and target.read_bytes().startswith(b"\xef\xbb\xbf"), "unconfirmed apply wrote source")
        applied = apply_metadata_migration_capability("settings", "settings.json", preview_token=preview["preview_token"], operator_confirmed=True, data_dir=root)
        require(applied["ok"] and applied["status"] == "migrated", "confirmed apply failed")
        require(applied["backup_verified"] and applied["private_backup_reference_returned"] is False, "backup contract invalid")
        require(not target.read_bytes().startswith(b"\xef\xbb\xbf"), "migration did not canonicalize")


def test_operator_registry_requires_dedicated_confirmation() -> None:
    from metadata_migration_capability import apply_metadata_migration_capability, preview_metadata_migration_capability
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        write_bom(root / "projects.json", {"active_project_id": "eidolon", "projects": []})
        preview = preview_metadata_migration_capability("projects", "projects.json", data_dir=root)
        blocked = apply_metadata_migration_capability("projects", "projects.json", preview_token=preview["preview_token"], operator_confirmed=True, data_dir=root)
        require(blocked["status"] == "operator_registry_confirmation_required", "projects registry bypassed dedicated confirmation")


def test_stale_preview_rejected_through_capability() -> None:
    from metadata_migration_capability import apply_metadata_migration_capability, preview_metadata_migration_capability
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target = root / "tasks.json"
        write_bom(target, {"version": 1, "tasks": []})
        preview = preview_metadata_migration_capability("tasks", "tasks.json", data_dir=root)
        write_bom(target, {"version": 2, "tasks": []})
        result = apply_metadata_migration_capability("tasks", "tasks.json", preview_token=preview["preview_token"], operator_confirmed=True, data_dir=root)
        require(result["status"] == "stale_or_mismatched_preview", "stale preview accepted")


def test_dashboard_routes_preserve_get_preview_post_apply() -> None:
    text = (AGENT / "dashboard.py").read_text(encoding="utf-8")
    get_pos = text.index('if path == "/api/metadata-migration/preview"')
    post_pos = text.index('if parsed.path == "/api/metadata-migration/apply"')
    do_post = text.index("    def do_POST")
    require(get_pos < do_post < post_pos, "migration route methods are not separated")
    require('"/api/metadata-migration/inventory"' in text, "inventory route missing")
    require("operator_registry_confirmed" in text[post_pos:post_pos + 1800], "dedicated confirmation missing from POST route")


def test_capability_never_returns_payload_or_absolute_path() -> None:
    from metadata_migration_capability import preview_metadata_migration_capability
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        write_bom(root / "settings.json", {"credential": "SECRET_SHOULD_NOT_RETURN"})
        result = preview_metadata_migration_capability("settings", "settings.json", data_dir=root)
        encoded = json.dumps(result, sort_keys=True)
        require("SECRET_SHOULD_NOT_RETURN" not in encoded and str(root) not in encoded, "capability leaked content or absolute path")
        require(result["content_free"] and result["payload_returned"] is False, "content-free contract missing")



def test_string_false_never_counts_as_confirmation() -> None:
    from metadata_migration_capability import apply_metadata_migration_capability, preview_metadata_migration_capability
    with tempfile.TemporaryDirectory() as td:
        root = Path(td); target = root / "settings.json"
        write_bom(target, {"safe_mode": "strict"})
        preview = preview_metadata_migration_capability("settings", "settings.json", data_dir=root)
        result = apply_metadata_migration_capability("settings", "settings.json", preview_token=preview["preview_token"], operator_confirmed="false", data_dir=root)
        require(result["status"] == "confirmation_required", "string false counted as confirmation")
        require(target.read_bytes().startswith(b"\xef\xbb\xbf"), "string false mutated source")

def test_release_metadata_and_docs() -> None:
    release = (AGENT / "release_metadata.py").read_text(encoding="utf-8")
    import re
    match = re.search(r'RUNTIME_VERSION = "(\d+)\.(\d+)"', release)
    require(bool(match) and tuple(map(int, match.groups())) >= (1093, 3), "runtime version regressed")
    require("v1093.3" in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8"), "history missing v1093.3")
    require("v1093.4" in (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8"), "next version missing")


def main() -> int:
    tests = [
        test_inventory_is_content_free_and_non_mutating,
        test_preview_is_exact_file_and_read_only,
        test_apply_requires_exact_token_and_confirmation,
        test_operator_registry_requires_dedicated_confirmation,
        test_stale_preview_rejected_through_capability,
        test_dashboard_routes_preserve_get_preview_post_apply,
        test_capability_never_returns_payload_or_absolute_path,
        test_string_false_never_counts_as_confirmation,
        test_release_metadata_and_docs,
    ]
    failures=[]; passed=0
    for test in tests:
        try:
            test(); passed += 1
        except Exception as error:
            failures.append(f"{test.__name__}: {type(error).__name__}: {error}")
    report={"version":"1093.3","suite":"governed-metadata-migration-application","passed":passed,"total":len(tests),"ok":passed==len(tests),"failures":failures}
    print(json.dumps(report, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
