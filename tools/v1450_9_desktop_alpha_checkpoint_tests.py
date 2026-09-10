from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from desktop_daily_use import (  # noqa: E402
    WindowsDpapiAdapter,
    acquire_single_instance_lease,
    build_encrypted_backup,
    restore_encrypted_backup,
    update_experience,
    validate_loopback_url,
)
from release_authority import (  # noqa: E402
    AUTHORITY_FLAGS,
    CHECKPOINT_HISTORY,
    PREVIOUS_WORKING_SOURCE_VERSION,
    WORKING_SOURCE_VERSION,
)
from relationship_continuity import build_relationship_continuity_snapshot  # noqa: E402
import release_packaging  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    checks: list[dict[str, str]] = []

    def check(name: str, condition: object) -> None:
        if not condition:
            raise AssertionError(name)
        checks.append({"name": name, "status": "pass"})

    def version_key(value: str) -> tuple[int, ...]:
        return tuple(int(part) for part in str(value).split("."))

    check("working_version", version_key(WORKING_SOURCE_VERSION) >= version_key("1450.9"))
    check(
        "previous_version",
        version_key(PREVIOUS_WORKING_SOURCE_VERSION) >= version_key("1449.9")
        and version_key(PREVIOUS_WORKING_SOURCE_VERSION) < version_key(WORKING_SOURCE_VERSION),
    )
    check("checkpoint_history", ("1450.9", "Desktop Alpha Checkpoint") in CHECKPOINT_HISTORY)

    shell_path = ROOT / "conscious_agent" / "desktop_shell.py"
    shell_source = shell_path.read_text(encoding="utf-8")
    ast.parse(shell_source, filename=str(shell_path))
    for token in (
        "navigation_drawer",
        "activity_drawer",
        "Message Eidolon...",
        'composer.bind("<Return>"',
        'root.bind("<Escape>"',
        "theme_scrollbar",
        'colors["cyan"]',
        'colors["amber"]',
    ):
        check(f"desktop_token:{token}", token in shell_source)

    check("loopback_ipv4", validate_loopback_url("http://127.0.0.1:8765"))
    check("loopback_ipv6", validate_loopback_url("http://[::1]:8765"))
    check("remote_endpoint_denied", not validate_loopback_url("http://example.com:8765"))
    check("credential_url_denied", not validate_loopback_url("http://user:secret@localhost:8765"))

    with tempfile.TemporaryDirectory(prefix="eidolon-v1450-lock-") as temporary:
        lock_path = Path(temporary) / "desktop.lock"
        check("single_instance_acquired", acquire_single_instance_lease(lock_path)["ok"])
        check("single_instance_reused", acquire_single_instance_lease(lock_path)["status"] == "lease_reused")

    reverse = lambda value: value[::-1]
    backup = build_encrypted_backup({"memory/preferences.json": b"{}"}, reverse)
    restored = restore_encrypted_backup(backup, reverse)
    check("backup_restore_preview", restored["ok"] and restored["restored"] == {"memory/preferences.json": b"{}"})
    try:
        build_encrypted_backup({"../outside.json": b"{}"}, reverse)
    except ValueError:
        checks.append({"name": "backup_traversal_denied", "status": "pass"})
    else:
        raise AssertionError("backup_traversal_denied")

    if os.name == "nt":
        plaintext = b"eidolon-v1450-dpapi-roundtrip"
        encrypted = WindowsDpapiAdapter.encrypt(plaintext)
        check("windows_dpapi_encrypted", encrypted != plaintext)
        check("windows_dpapi_roundtrip", WindowsDpapiAdapter.decrypt(encrypted) == plaintext)

    digest = hashlib.sha256(b"candidate").hexdigest()
    update = update_experience({
        "version": "1451.0",
        "current_version": WORKING_SOURCE_VERSION,
        "staged_path_digest": digest,
        "manifest_valid": True,
        "hash_valid": True,
        "clean_extract_valid": True,
        "isolated_verification_passed": True,
        "rollback_artifact_digest": digest,
    })
    check("update_preview_exact", update["payload"]["preview_ready"] is True)
    check("relationship_runtime_restored", callable(build_relationship_continuity_snapshot))

    runtime_root = Path(os.environ["EIDOLON_DATA_DIR"]).expanduser().resolve()
    check("runtime_external", runtime_root != (ROOT / "data").resolve() and ROOT not in runtime_root.parents)
    settings = json.loads((runtime_root / "settings.json").read_text(encoding="utf-8"))
    check("settings_schema_present", bool(str(settings.get("settings_version") or "").strip()))
    check("workspace_runtime_excluded", not (ROOT / "data" / "workspaces" / "active_project.json").exists())
    check("projects_runtime_excluded", not (ROOT / "data" / "projects.json").exists())
    with tempfile.TemporaryDirectory(prefix="eidolon-v1450-package-runtime-") as package_runtime:
        release_packaging.DATA_DIR = Path(package_runtime)
        (release_packaging.DATA_DIR / "settings.json").write_text(
            json.dumps({"settings_version": WORKING_SOURCE_VERSION, "last_updated_for": f"v{WORKING_SOURCE_VERSION}"}),
            encoding="utf-8",
        )
        manifest = release_packaging.build_release_manifest_integrity(
            package_name=f"Eidolon_v{WORKING_SOURCE_VERSION.replace('.', '_')}_source_only.zip",
            save=False,
        )
    check("source_only_manifest_without_private_workspace", manifest.get("ok") is True)
    check("validation_record", (ROOT / "archive/docs/legacy_dependencies/validation/V1450_9_DESKTOP_ALPHA_VALIDATION.md").is_file())
    for name in ("README.md", "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "archive/docs/legacy_dependencies/roadmaps/README_V1500_ROADMAP.md"):
        check(f"docs_current:{name}", "v1450.9" in (ROOT / name).read_text(encoding="utf-8"))

    verify_source = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
    check("release_stage_registered", verify_source.count('"v1450.9-desktop-alpha-checkpoint"') == 2)
    check("authority_remains_denied", all(value is False for value in AUTHORITY_FLAGS.values()))

    report = {
        "suite": "v1450.9-desktop-alpha-checkpoint",
        "ok": True,
        "status": "pass",
        "passed": len(checks),
        "total": len(checks),
        "checks": checks,
        "native_windows_dpapi_tested": os.name == "nt",
        "provider_contacted": False,
        "model_management_performed": False,
        "release_authorized": False,
        "multi_day_soak_claimed": False,
    }
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"pass: {len(checks)}/{len(checks)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
