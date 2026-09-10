import sys
import json
import os
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from v1401_1449_test_support import run_version_suite
from relationship_continuity import (
    build_relationship_continuity_snapshot,
    is_relationship_memory,
    relationship_memory_type,
)
from desktop_daily_use import (
    acquire_single_instance_lease,
    build_encrypted_backup,
    restore_encrypted_backup,
    update_experience,
    validate_loopback_url,
)

report = run_version_suite(1449,'reliability')

# v1449 must retain the established conversation runtime while extending the
# desktop/update surface. Compile-only checks do not resolve imported symbols.
import conversation_runtime  # noqa: F401

assert callable(build_relationship_continuity_snapshot)
assert is_relationship_memory({"type": "preference"})
assert relationship_memory_type({"type": "nickname"}) == "nickname"
settings_path = ROOT / "data" / "settings.json"
assert settings_path.is_file()
assert isinstance(json.loads(settings_path.read_text(encoding="utf-8")), dict)
desktop_source = (ROOT / "conscious_agent" / "desktop_shell.py").read_text(encoding="utf-8")
for token in (
    "navigation_drawer",
    "activity_drawer",
    "Message Eidolon...",
    'root.bind("<Escape>"',
    'composer.bind("<Return>"',
):
    assert token in desktop_source

assert validate_loopback_url("http://127.0.0.1:8765")
assert validate_loopback_url("http://[::1]:8765")
assert not validate_loopback_url("http://example.com:8765")
assert not validate_loopback_url("http://user:secret@localhost:8765")
assert not validate_loopback_url("http://localhost:8765/path?secret=value")

with tempfile.TemporaryDirectory(prefix="eidolon-desktop-lock-") as temporary:
    lock_path = Path(temporary) / "desktop.lock"
    assert acquire_single_instance_lease(lock_path)["ok"]
    assert acquire_single_instance_lease(lock_path)["status"] == "lease_reused"

reverse = lambda value: value[::-1]
backup = build_encrypted_backup({"memory/preferences.json": b"{}"}, reverse)
restore = restore_encrypted_backup(backup, reverse)
assert restore["ok"] and restore["restored"] == {"memory/preferences.json": b"{}"}
try:
    build_encrypted_backup({"../outside.json": b"{}"}, reverse)
except ValueError:
    pass
else:
    raise AssertionError("unsafe backup path was accepted")

digest = "a" * 64
update = update_experience({
    "version": "1450.0",
    "current_version": "1449.9",
    "staged_path_digest": digest,
    "manifest_valid": True,
    "hash_valid": True,
    "clean_extract_valid": True,
    "isolated_verification_passed": True,
    "rollback_artifact_digest": digest,
})
assert update["payload"]["preview_ready"] is True
same_version = update_experience({**update["payload"], "version": "1449.9", "current_version": "1449.9"})
assert same_version["payload"]["preview_ready"] is False

report = {**report, "passed": report["passed"] + 23, "total": report["total"] + 23}
print(report)
