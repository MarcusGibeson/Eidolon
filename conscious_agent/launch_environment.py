from __future__ import annotations

"""Ordinary-launch external runtime selection and v1150.1 migration handling."""

import os
from pathlib import Path
import platform
from typing import Any, Mapping, MutableMapping

LAUNCH_ENVIRONMENT_SCHEMA_VERSION = "2"
RUNTIME_ENVIRONMENT_VARIABLE = "EIDOLON_DATA_DIR"
WINDOWS_RUNTIME_TEMPLATE = r"%LOCALAPPDATA%\Eidolon\runtime"
POSIX_RUNTIME_TEMPLATE = "${XDG_DATA_HOME:-$HOME/.local/share}/eidolon/runtime"


def _resolved(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
    except ValueError:
        return False
    return True


def default_external_runtime_root(
    *,
    environment: Mapping[str, str] | None = None,
    platform_name: str | None = None,
    home: str | Path | None = None,
) -> Path:
    env = environment if environment is not None else os.environ
    system = str(platform_name or platform.system()).strip().lower()
    home_path = _resolved(home or env.get("USERPROFILE") or env.get("HOME") or Path.home())
    if system == "windows":
        local_app_data = str(env.get("LOCALAPPDATA") or "").strip()
        base = _resolved(local_app_data) if local_app_data else home_path / "AppData" / "Local"
        return (base / "Eidolon" / "runtime").resolve()
    xdg_data_home = str(env.get("XDG_DATA_HOME") or "").strip()
    base = _resolved(xdg_data_home) if xdg_data_home else home_path / ".local" / "share"
    return (base / "eidolon" / "runtime").resolve()


def runtime_location_status(
    source_root: str | Path,
    *,
    environment: Mapping[str, str] | None = None,
    platform_name: str | None = None,
    include_paths: bool = False,
    inspect_runtime_inventory: bool = True,
) -> dict[str, Any]:
    """Describe ordinary-launch placement and migration need without mutation."""

    env = environment if environment is not None else os.environ
    source = _resolved(source_root)
    source_data = (source / "data").resolve()
    explicit = str(env.get(RUNTIME_ENVIRONMENT_VARIABLE) or "").strip()
    default_root = default_external_runtime_root(
        environment=env,
        platform_name=platform_name,
        home=env.get("USERPROFILE") or env.get("HOME") or None,
    )
    active_root = _resolved(explicit) if explicit else default_root
    external = not _is_within(active_root, source)
    source_local = _is_within(active_root, source)
    if inspect_runtime_inventory:
        try:
            from runtime_data_migration import preview_runtime_data_migration
        except ImportError:
            from runtime_data_migration import preview_runtime_data_migration
        migration = preview_runtime_data_migration(source_data, active_root, include_paths=False)
    else:
        def has_entries(path: Path) -> bool:
            try:
                return path.is_dir() and next(path.iterdir(), None) is not None
            except OSError:
                return False
        source_has_entries = has_entries(source_data)
        target_has_entries = has_entries(active_root)
        if source_local:
            migration_status = "same_runtime_location"
        elif target_has_entries:
            migration_status = "external_runtime_already_populated"
        elif source_has_entries:
            migration_status = "migration_inventory_deferred"
        else:
            migration_status = "no_legacy_runtime_data"
        migration = {
            "status": migration_status,
            "legacy_file_count": None,
            "migration_needed": migration_status == "migration_inventory_deferred",
            "interrupted_migration_detected": False,
        }
    status = "external_runtime_active" if external else "source_local_runtime"
    recommended = "none"
    if source_local:
        recommended = "choose_external_runtime"
    elif migration["status"] in {"ready", "interrupted_migration_detected", "interrupted_migration_finalization_detected"}:
        recommended = "ordinary_launch_will_copy_and_verify_legacy_runtime"
    elif migration["status"] in {"incompatible_runtime_layout", "legacy_runtime_contains_symlinks"}:
        recommended = "review_blocking_migration_condition"
    result: dict[str, Any] = {
        "schema_version": LAUNCH_ENVIRONMENT_SCHEMA_VERSION,
        "ok": external and migration["status"] not in {"incompatible_runtime_layout", "legacy_runtime_contains_symlinks"},
        "status": status,
        "runtime_origin": "explicit_override" if explicit else "ordinary_launch_default",
        "runtime_external": external,
        "runtime_source_local": source_local,
        "explicit_override": bool(explicit),
        "explicit_external_override": bool(explicit and external),
        "default_external_runtime_available": True,
        "source_data_directory_present": source_data.exists(),
        "legacy_runtime_file_count": migration["legacy_file_count"],
        "migration_preview_status": migration["status"],
        "migration_inventory_performed": bool(inspect_runtime_inventory),
        "migration_needed": migration["migration_needed"],
        "interrupted_migration_detected": migration["interrupted_migration_detected"],
        "recommended_action": recommended,
        "automatic_migration": False,
        "runtime_mutation_performed": False,
        "source_mutation_performed": False,
        "private_paths_included": bool(include_paths),
        "content_free": not bool(include_paths),
    }
    if include_paths:
        result.update({
            "source_root": str(source),
            "source_data_root": str(source_data),
            "active_runtime_root": str(active_root),
            "default_external_runtime_root": str(default_root),
        })
    return result


def build_runtime_migration_guidance(
    source_root: str | Path,
    *,
    environment: Mapping[str, str] | None = None,
    platform_name: str | None = None,
    include_paths: bool = False,
    inspect_runtime_inventory: bool = True,
) -> dict[str, Any]:
    location = runtime_location_status(
        source_root,
        environment=environment,
        platform_name=platform_name,
        include_paths=include_paths,
        inspect_runtime_inventory=inspect_runtime_inventory,
    )
    migration_status = str(location.get("migration_preview_status") or "")
    if location["runtime_source_local"]:
        headline = "Runtime data is explicitly configured inside the source tree."
        summary = "Ordinary launch preserves explicit configuration but will not migrate or overwrite it."
    elif migration_status in {"ready", "interrupted_migration_detected", "interrupted_migration_finalization_detected"}:
        headline = "Legacy source-local runtime data is ready for safe migration."
        summary = "Ordinary launch will stage, verify, and atomically copy it to the external runtime while leaving the legacy copy untouched."
    elif migration_status == "external_runtime_already_populated":
        headline = "An external runtime already exists."
        summary = "Ordinary launch will preserve it and will not merge source-local files into it."
    elif migration_status in {"incompatible_runtime_layout", "legacy_runtime_contains_symlinks"}:
        headline = "Runtime migration requires operator review."
        summary = "Ordinary launch will block rather than start against an empty or incompatible runtime."
    else:
        headline = "Runtime data is external to the source tree."
        summary = "Fresh source-only extraction will start with an external runtime and no bundled private state."
    return {
        **location,
        "headline": headline,
        "summary": summary,
        "migration_steps": [
            "Close every Eidolon dashboard process before migrating runtime data.",
            "Keep the legacy runtime intact until the external copy is verified in ordinary use.",
            "Do not merge a populated external runtime with a different legacy runtime.",
            "Review incompatible layout or symlink findings before launching.",
        ],
        "commands": {
            "windows_ordinary_launch": r".\run_eidolon.ps1",
            "windows_explicit_runtime": rf'$env:{RUNTIME_ENVIRONMENT_VARIABLE}="{WINDOWS_RUNTIME_TEMPLATE}"; .\run_eidolon.ps1',
            "posix_ordinary_launch": "./run_eidolon.sh",
            "posix_explicit_runtime": f'export {RUNTIME_ENVIRONMENT_VARIABLE}="{POSIX_RUNTIME_TEMPLATE}"; ./run_eidolon.sh',
            "inspect_redacted": "python eidolon.py runtime-guide --json",
            "inspect_local_paths": "python eidolon.py runtime-guide --show-paths",
        },
        "accepted_message_replayed": False,
        "provider_request_repeated": False,
        "models_changed": False,
    }


def prepare_ordinary_launch_environment(
    source_root: str | Path,
    *,
    environment: MutableMapping[str, str] | None = None,
    platform_name: str | None = None,
    create_runtime: bool = True,
    seed_source_defaults: bool = True,
) -> dict[str, Any]:
    """Prepare one external runtime, preserving existing and legacy user data.

    With no explicit override, legacy ``source/data`` is copied only when the
    external target is absent or empty. The migration is copy-only, verified,
    recoverable, and never deletes the legacy source. A populated external
    runtime always wins and is never merged or overwritten.
    """

    env = environment if environment is not None else os.environ
    source = _resolved(source_root)
    source_data = (source / "data").resolve()
    explicit = str(env.get(RUNTIME_ENVIRONMENT_VARIABLE) or "").strip()
    selected = _resolved(explicit) if explicit else default_external_runtime_root(
        environment=env,
        platform_name=platform_name,
        home=env.get("USERPROFILE") or env.get("HOME") or None,
    )
    if not explicit:
        env[RUNTIME_ENVIRONMENT_VARIABLE] = str(selected)
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    env.setdefault("PYTHONUNBUFFERED", "1")
    external = not _is_within(selected, source)
    created = False
    seeded_files = 0
    migration: dict[str, Any] = {
        "status": "explicit_override_preserved" if explicit else "not_checked",
        "migration_performed": False,
        "recovered_interrupted_migration": False,
        "legacy_file_count": 0,
        "installed_file_count": 0,
        "legacy_source_modified": False,
        "legacy_source_deleted": False,
        "private_payload_returned": False,
    }
    migration_blocking = False

    if create_runtime and external and not explicit:
        try:
            from runtime_data_migration import preview_runtime_data_migration, migrate_runtime_data
        except ImportError:
            from runtime_data_migration import preview_runtime_data_migration, migrate_runtime_data
        migration_journal = selected.parent / f".{selected.name}.eidolon-runtime-migration.json"
        external_populated = selected.exists() and any(path.is_file() for path in selected.rglob("*"))
        if external_populated and not migration_journal.is_file():
            preview = {
                "status": "external_runtime_already_populated",
                "ok": True,
                "migration_needed": False,
                "migration_performed": False,
                "legacy_file_count": 0,
                "installed_file_count": 0,
                "legacy_source_modified": False,
                "legacy_source_deleted": False,
                "external_runtime_overwritten": False,
            }
        else:
            preview = preview_runtime_data_migration(source_data, selected)
        migration = dict(preview)
        if preview["status"] == "external_runtime_already_populated":
            migration["status"] = "existing_external_runtime_preserved"
        elif preview["status"] in {"ready", "interrupted_migration_detected", "interrupted_migration_finalization_detected"}:
            migration = migrate_runtime_data(
                source_data,
                selected,
                operator_confirmed=True,
                automatic=True,
            )
            migration_blocking = not migration.get("ok")
        elif preview["status"] in {"incompatible_runtime_layout", "legacy_runtime_contains_symlinks"}:
            migration_blocking = True
        elif preview["status"] == "no_legacy_runtime_data":
            existed = selected.exists()
            selected.mkdir(parents=True, exist_ok=True)
            created = not existed
    elif create_runtime:
        existed = selected.exists()
        selected.mkdir(parents=True, exist_ok=True)
        created = not existed

    if create_runtime and external and not migration_blocking and not selected.exists():
        selected.mkdir(parents=True, exist_ok=True)
        created = True

    if (
        create_runtime
        and seed_source_defaults
        and external
        and not migration_blocking
        and selected.exists()
        and not any(path.is_file() for path in selected.rglob("*"))
    ):
        try:
            from package_integrity import SOURCE_DATA_ALLOWLIST, source_package_bytes
        except ImportError:
            from package_integrity import SOURCE_DATA_ALLOWLIST, source_package_bytes
        for relative in SOURCE_DATA_ALLOWLIST:
            source_path = source / relative
            if not source_path.is_file():
                continue
            target = selected / Path(relative).relative_to("data")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source_package_bytes(source, relative))
            seeded_files += 1

    status = "external_runtime_ready"
    if not external:
        status = "source_local_override_preserved"
    elif migration_blocking:
        status = "runtime_migration_blocked"
    elif migration.get("migration_performed"):
        status = "external_runtime_migrated"
    elif migration.get("migration_finalization_performed"):
        status = "external_runtime_migration_recovered"
    elif migration.get("status") == "existing_external_runtime_preserved":
        status = "existing_external_runtime_preserved"
    return {
        "schema_version": LAUNCH_ENVIRONMENT_SCHEMA_VERSION,
        "ok": external and not migration_blocking,
        "status": status,
        "runtime_origin": "explicit_override" if explicit else "ordinary_launch_default",
        "runtime_external": external,
        "explicit_override_preserved": bool(explicit),
        "runtime_directory_created": created,
        "source_safe_defaults_seeded": seeded_files,
        "migration_status": migration.get("status", ""),
        "migration_blocking": migration_blocking,
        "legacy_runtime_file_count": int(migration.get("legacy_file_count") or 0),
        "migrated_runtime_file_count": int(migration.get("installed_file_count") or 0),
        "automatic_migration": bool(migration.get("migration_performed") or migration.get("migration_finalization_performed")),
        "interrupted_migration_recovered": bool(migration.get("recovered_interrupted_migration")),
        "source_data_copied": bool(migration.get("migration_performed")),
        "source_runtime_data_copied": bool(migration.get("migration_performed")),
        "private_runtime_data_copied": bool(migration.get("migration_performed")),
        "source_data_deleted": bool(migration.get("legacy_source_deleted")),
        "source_data_modified": bool(migration.get("legacy_source_modified")),
        "external_runtime_overwritten": bool(migration.get("external_runtime_overwritten")),
        "accepted_message_replayed": False,
        "provider_request_repeated": False,
        "private_payload_returned": False,
        "private_paths_included": False,
        "content_free": True,
    }
