from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

from conscious_agent.runtime_data_migration import (
    preview_runtime_data_migration,
    migrate_runtime_data,
)
from conscious_agent.launch_environment import prepare_ordinary_launch_environment


def digest_tree(root: Path) -> str:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rows.append((path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()


with tempfile.TemporaryDirectory() as temporary:
    base = Path(temporary)
    legacy = base / "legacy" / "data"
    external = base / "external" / "runtime"
    (legacy / "workspaces").mkdir(parents=True)
    (legacy / "conversation_runtime" / "session-a").mkdir(parents=True)
    (legacy / "cognition" / "evidence").mkdir(parents=True)
    (legacy / "workspaces" / "projects.json").write_text('{"projects":[{"id":"private-project"}]}', encoding="utf-8")
    (legacy / "memories.json").write_text('[{"content":"private memory"}]', encoding="utf-8")
    (legacy / "settings.json").write_text('{"provider":"ollama","model":"fixture"}', encoding="utf-8")
    (legacy / "conversation_runtime" / "session-a" / "turns.json").write_text('[{"role":"user","content":"private"}]', encoding="utf-8")
    (legacy / "cognition" / "evidence" / "receipt.json").write_text('{"private":true}', encoding="utf-8")
    before = digest_tree(legacy)

    preview = preview_runtime_data_migration(legacy, external)
    not_confirmed = migrate_runtime_data(legacy, external, operator_confirmed=False)
    migrated = migrate_runtime_data(legacy, external, operator_confirmed=True, automatic=True)
    after = digest_tree(legacy)

    occupied = base / "occupied"
    occupied.mkdir()
    (occupied / "memories.json").write_text("[]", encoding="utf-8")
    blocked = preview_runtime_data_migration(legacy, occupied)

    incompatible = base / "incompatible"
    incompatible.mkdir()
    (incompatible / ".eidolon_runtime_layout.json").write_text('{"layout_version":99}', encoding="utf-8")
    incompatible_target = base / "incompatible-target"
    incompatible_preview = preview_runtime_data_migration(incompatible, incompatible_target)

    interrupted_target = base / "interrupted" / "runtime"
    interrupted_target.parent.mkdir(parents=True)
    journal = interrupted_target.parent / f".{interrupted_target.name}.eidolon-runtime-migration.json"
    journal.write_text(json.dumps({"state":"copying","started_at":"fixture"}), encoding="utf-8")
    recovered = migrate_runtime_data(legacy, interrupted_target, operator_confirmed=True)

    finalized_target = base / "finalized" / "runtime"
    finalized_target.parent.mkdir(parents=True)
    shutil.copytree(legacy, finalized_target)
    finalized_journal = finalized_target.parent / f".{finalized_target.name}.eidolon-runtime-migration.json"
    finalized_journal.write_text(json.dumps({
        "contract_version": "v1150.1",
        "state": "verified",
        "started_at": "fixture",
        "source_inventory_digest": preview["legacy_inventory_digest"],
        "source_file_count": preview["legacy_file_count"],
        "target_name": finalized_target.name,
        "copy_only": True,
    }), encoding="utf-8")
    finalization_preview = preview_runtime_data_migration(legacy, finalized_target)
    finalized = migrate_runtime_data(legacy, finalized_target, operator_confirmed=True)
    finalized_again = preview_runtime_data_migration(legacy, finalized_target)

    launch_source = base / "launch-source"
    launch_data = launch_source / "data"
    launch_data.mkdir(parents=True)
    (launch_data / "memories.json").write_text('[{"content":"launch memory"}]', encoding="utf-8")
    launch_home = base / "launch-home"
    launch_env = {"HOME": str(launch_home), "XDG_DATA_HOME": str(launch_home / "xdg")}
    launch_status = prepare_ordinary_launch_environment(launch_source, environment=launch_env, platform_name="Linux")
    launch_runtime = Path(launch_env["EIDOLON_DATA_DIR"])
    launch_memory_preserved = (launch_runtime / "memories.json").is_file()

    preserved_files = {
        "projects": (external / "workspaces" / "projects.json").is_file(),
        "memories": (external / "memories.json").is_file(),
        "settings": (external / "settings.json").is_file(),
        "conversations": (external / "conversation_runtime" / "session-a" / "turns.json").is_file(),
        "evidence": (external / "cognition" / "evidence" / "receipt.json").is_file(),
    }

checks = [
    preview["status"] == "ready" and preview["migration_needed"],
    not_confirmed["status"] == "operator_confirmation_required" and not external.exists(),
    migrated["ok"] and migrated["status"] == "migration_complete",
    migrated["installed_file_count"] == 5,
    before == after and not migrated["legacy_source_modified"] and not migrated["legacy_source_deleted"],
    preserved_files["projects"],
    preserved_files["memories"],
    preserved_files["settings"],
    preserved_files["conversations"],
    preserved_files["evidence"],
    blocked["status"] == "external_runtime_already_populated" and not blocked["ok"],
    incompatible_preview["status"] == "incompatible_runtime_layout" and not incompatible_preview["ok"],
    recovered["ok"] and recovered["recovered_interrupted_migration"],
    finalization_preview["status"] == "interrupted_migration_finalization_detected",
    finalized["ok"] and finalized["status"] == "migration_recovery_complete",
    finalized["recovered_interrupted_migration"] and finalized["migration_finalization_performed"],
    finalized_again["status"] == "migration_already_complete" and finalized_again["ok"],
    not migrated["private_payload_returned"] and migrated["content_free"],
    launch_status["ok"] and launch_status["automatic_migration"],
    launch_status["status"] == "external_runtime_migrated" and launch_memory_preserved,
]
assert all(checks), {"preview": preview, "migrated": migrated, "blocked": blocked, "incompatible": incompatible_preview, "recovered": recovered}
print(json.dumps({"suite": "v1150.1", "passed": len(checks), "total": len(checks)}))
