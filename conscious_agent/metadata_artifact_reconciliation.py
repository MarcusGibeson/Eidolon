from __future__ import annotations

"""Content-free reconciliation of private mutable-metadata artifacts.

This module does not maintain a cleanup ledger. It inspects current private
artifacts, ties them to exact inventoried targets, and permits only narrow
confirmed cleanup when current bytes prove the artifact redundant or the lock
owner is demonstrably abandoned.
"""

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Any

try:
    from json_storage import inspect_json_encoding
    from metadata_migration_recovery import metadata_migration_recovery_status, recovery_state_dir
    from metadata_mutation_coordination import cleanup_abandoned_metadata_lock, inspect_metadata_lock
    from metadata_store_inventory import MUTABLE_JSON_STORES, iter_store_paths
    from paths import DATA_DIR
except ImportError:
    from json_storage import inspect_json_encoding
    from metadata_migration_recovery import metadata_migration_recovery_status, recovery_state_dir
    from metadata_mutation_coordination import cleanup_abandoned_metadata_lock, inspect_metadata_lock
    from metadata_store_inventory import MUTABLE_JSON_STORES, iter_store_paths
    from paths import DATA_DIR


@dataclass(frozen=True)
class KnownTarget:
    store_id: str
    path: Path
    expected_type: type[Any]


def _root(data_dir: Path | None = None) -> Path:
    return Path(data_dir or DATA_DIR).expanduser().resolve()


def _lock_root(data_dir: Path | None = None) -> Path:
    override = os.environ.get("EIDOLON_METADATA_LOCK_DIR")
    return Path(override).expanduser().resolve() if override else _root(data_dir) / "metadata_mutation_locks"


def _digest_path(path: Path) -> str:
    return hashlib.sha256(str(path.expanduser().resolve()).encode("utf-8")).hexdigest()


def _digest_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _known_targets(data_dir: Path | None = None) -> list[KnownTarget]:
    root = _root(data_dir)
    rows: dict[str, KnownTarget] = {}
    for store in MUTABLE_JSON_STORES:
        pattern = store.relative_pattern
        if not any(ch in pattern for ch in "*?["):
            target = (root / pattern).resolve()
            rows[_digest_path(target)] = KnownTarget(store.store_id, target, store.expected_type)
        for target in iter_store_paths(store, data_dir=root):
            resolved = target.resolve()
            rows[_digest_path(resolved)] = KnownTarget(store.store_id, resolved, store.expected_type)
    return sorted(rows.values(), key=lambda row: (row.store_id, row.path.as_posix()))


def _record_rows(data_dir: Path | None = None) -> list[dict[str, Any]]:
    directory = recovery_state_dir(data_dir=data_dir)
    rows: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")) if directory.exists() else []:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            rows.append({"artifact_type": "recovery_record", "status": "operator_review", "safe_cleanup": False, "content_free": True})
            continue
        if not isinstance(value, dict) or value.get("type") != "metadata_migration_recovery":
            rows.append({"artifact_type": "recovery_record", "status": "operator_review", "safe_cleanup": False, "content_free": True})
            continue
        rows.append({
            "artifact_type": "recovery_record",
            "status": "recovery_required",
            "stage": str(value.get("stage") or "unknown"),
            "target_digest": str(value.get("target_digest") or ""),
            "safe_cleanup": False,
            "content_free": True,
        })
    return rows


def inspect_orphaned_metadata_artifacts(*, data_dir: Path | None = None) -> dict[str, Any]:
    root = _root(data_dir)
    targets = _known_targets(root)
    rows: list[dict[str, Any]] = []
    seen_locks: set[Path] = set()
    seen_temporaries: set[Path] = set()
    for target in targets:
        lock = inspect_metadata_lock(target.path)
        if lock.get("lock_exists"):
            try:
                from metadata_mutation_coordination import metadata_lock_path
            except ImportError:
                from metadata_mutation_coordination import metadata_lock_path
            seen_locks.add(metadata_lock_path(target.path).resolve())
            rows.append({
                "artifact_type": "mutation_lock", "store_id": target.store_id,
                "target_digest": lock["target_digest"],
                "status": "busy" if lock.get("owner_active") else ("safe_cleanup" if lock.get("safe_cleanup") else "operator_review"),
                "live_owner": bool(lock.get("owner_active")),
                "safe_cleanup": bool(lock.get("safe_cleanup")),
                "content_free": True,
            })
        patterns = (
            f".{target.path.name}.transaction-*.tmp",
            f".{target.path.name}.recovery-*.tmp",
        )
        for pattern in patterns:
            for artifact in sorted(target.path.parent.glob(pattern)):
                if not artifact.is_file():
                    continue
                seen_temporaries.add(artifact.resolve())
                same_as_target = False
                try:
                    same_as_target = target.path.is_file() and _digest_file(artifact) == _digest_file(target.path)
                except OSError:
                    pass
                state = inspect_json_encoding(artifact, expected_type=target.expected_type)
                # A temporary file without a surviving target is not enough evidence to
                # promote bytes into place. Without a digest-bound recovery record, the
                # intended transaction cannot be proven, so fail closed for operator review.
                status = "safe_cleanup" if same_as_target else "operator_review"
                rows.append({
                    "artifact_type": "temporary_file", "store_id": target.store_id,
                    "target_digest": _digest_path(target.path), "status": status,
                    "valid_json": bool(state.get("valid_json")), "root_shape_valid": bool(state.get("root_shape_valid")),
                    "same_as_target": same_as_target, "safe_cleanup": same_as_target,
                    "content_free": True,
                })

    lock_root = _lock_root(root)
    for artifact in sorted(lock_root.glob("*.lock")) if lock_root.exists() else []:
        if artifact.resolve() in seen_locks:
            continue
        rows.append({
            "artifact_type": "mutation_lock", "store_id": "unknown",
            "target_digest": artifact.stem if len(artifact.stem) == 64 else "",
            "status": "operator_review", "live_owner": False,
            "safe_cleanup": False, "content_free": True,
        })
    for artifact in sorted(root.rglob(".*.tmp")):
        if artifact.resolve() in seen_temporaries:
            continue
        name = artifact.name
        if ".transaction-" not in name and ".recovery-" not in name:
            continue
        rows.append({
            "artifact_type": "temporary_file", "store_id": "unknown",
            "target_digest": "", "status": "operator_review",
            "valid_json": False, "root_shape_valid": False,
            "same_as_target": False, "safe_cleanup": False,
            "content_free": True,
        })

    rows.extend(_record_rows(root))

    backup_root = root / "metadata_migration_backups"
    for store in MUTABLE_JSON_STORES:
        directory = backup_root / store.store_id
        if not directory.exists():
            continue
        targets_by_name: dict[str, list[KnownTarget]] = {}
        for row in targets:
            if row.store_id == store.store_id:
                targets_by_name.setdefault(row.path.name, []).append(row)
        for backup in sorted(directory.glob("*.bak")):
            target_name = backup.name.split(".pre-utf8-migration-", 1)[0]
            matches = targets_by_name.get(target_name) or []
            target = matches[0] if len(matches) == 1 else None
            verified = bool(inspect_json_encoding(backup, expected_type=store.expected_type).get("root_shape_valid"))
            duplicate = False
            if target and target.path.is_file():
                try:
                    duplicate = _digest_file(backup) == _digest_file(target.path)
                except OSError:
                    duplicate = False
            rows.append({
                "artifact_type": "migration_backup", "store_id": store.store_id,
                "target_digest": _digest_path(target.path) if target else "",
                "status": "safe_cleanup" if verified and duplicate else ("verified_backup" if verified and target else "operator_review"),
                "verified": verified, "same_as_target": duplicate,
                "safe_cleanup": bool(verified and duplicate), "content_free": True,
            })

    counts: dict[str, int] = {}
    for row in rows:
        status = str(row.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    overall = "healthy"
    if counts.get("busy"):
        overall = "busy"
    if counts.get("recovery_required"):
        overall = "recovery_required"
    if counts.get("operator_review"):
        overall = "uncertain"
    return {
        "ok": overall not in {"uncertain"},
        "status": overall,
        "artifact_count": len(rows),
        "counts": counts,
        "rows": rows,
        "safe_cleanup_available": bool(counts.get("safe_cleanup")),
        "operator_confirmation_required_for_cleanup": bool(counts.get("safe_cleanup")),
        "payload_returned": False,
        "absolute_path_returned": False,
        "lock_token_returned": False,
        "backup_path_returned": False,
        "content_free": True,
    }


def reconcile_orphaned_metadata_artifacts(*, operator_confirmed: bool, data_dir: Path | None = None) -> dict[str, Any]:
    operator_confirmed = operator_confirmed is True
    before = inspect_orphaned_metadata_artifacts(data_dir=data_dir)
    if not operator_confirmed:
        return {**before, "ok": False, "status": "confirmation_required", "removed": 0, "recovered": 0}
    root = _root(data_dir)
    removed = 0
    targets = _known_targets(root)
    for target in targets:
        lock = inspect_metadata_lock(target.path)
        if lock.get("safe_cleanup"):
            result = cleanup_abandoned_metadata_lock(target.path, operator_confirmed=True)
            removed += int(bool(result.get("removed")))
        for pattern in (f".{target.path.name}.transaction-*.tmp", f".{target.path.name}.recovery-*.tmp"):
            for artifact in sorted(target.path.parent.glob(pattern)):
                try:
                    if target.path.is_file() and _digest_file(artifact) == _digest_file(target.path):
                        artifact.unlink(); removed += 1
                except OSError:
                    pass

    # A verified backup is removable only when it maps to one exact inventoried
    # target and is byte-identical to the current valid target. Ambiguous names,
    # non-identical historical backups, and invalid backups remain untouched.
    backup_root = root / "metadata_migration_backups"
    targets_by_store_and_name: dict[tuple[str, str], list[KnownTarget]] = {}
    for target in targets:
        targets_by_store_and_name.setdefault((target.store_id, target.path.name), []).append(target)
    for store in MUTABLE_JSON_STORES:
        directory = backup_root / store.store_id
        if not directory.exists():
            continue
        for backup in sorted(directory.glob("*.bak")):
            target_name = backup.name.split(".pre-utf8-migration-", 1)[0]
            matches = targets_by_store_and_name.get((store.store_id, target_name)) or []
            if len(matches) != 1:
                continue
            target = matches[0]
            try:
                verified = bool(
                    inspect_json_encoding(backup, expected_type=store.expected_type).get("root_shape_valid")
                )
                if verified and target.path.is_file() and _digest_file(backup) == _digest_file(target.path):
                    backup.unlink()
                    removed += 1
            except OSError:
                pass
    after = inspect_orphaned_metadata_artifacts(data_dir=root)
    status = "safely_recovered" if removed and after.get("status") == "healthy" else after.get("status")
    return {**after, "ok": after.get("status") != "uncertain", "status": status, "removed": removed, "recovered": 0}
