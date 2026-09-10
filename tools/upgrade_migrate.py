from __future__ import annotations

"""Reversible migration for retired Eidolon runtime evidence.

Replacement-based upgrades can retain historical sandbox proof files that are no
longer shipped in source-only releases. Mixed or partial evidence must not be
silently trusted. This tool validates the two known ledgers structurally and
cryptographically, then moves only stale/partial proof directories into a
transaction-manifested quarantine. Nothing is deleted.
"""

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))

from release_metadata import RUNTIME_VERSION  # noqa: E402

MIGRATION_ID = "retired-sandbox-evidence-quarantine-v2"
SURFACE_IDS: tuple[str, ...] = (
    "v916-manifest-review-packet-schema",
    "v917-dashboard-surface-preview-generator",
    "v918-cli-api-surface-preview-generator",
    "v919-smoke-surface-preview-generator",
    "v920-generated-preview-parity-report",
)
TARGETS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "sandbox/generated_surface_scaffold_previews",
        "hash_ledger.json",
        tuple(f"{surface_id}.json" for surface_id in SURFACE_IDS),
    ),
    (
        "sandbox/generated_scaffold_wrapper_previews",
        "wrapper_hash_ledger.json",
        tuple(f"{surface_id}.wrapper.json" for surface_id in SURFACE_IDS),
    ),
)
_HEX_DIGITS = frozenset("0123456789abcdef")
_FILE_ATTRIBUTE_REPARSE_POINT = 0x400


def _lstat_payload(path: Path) -> dict[str, int]:
    info = os.lstat(path)
    return {
        "device": int(info.st_dev),
        "inode": int(info.st_ino),
        "mode": int(info.st_mode),
        "size": int(info.st_size),
        "mtime_ns": int(getattr(info, "st_mtime_ns", int(info.st_mtime * 1_000_000_000))),
        "file_attributes": int(getattr(info, "st_file_attributes", 0)),
    }


def _is_indirection(path: Path) -> tuple[bool, str | None]:
    try:
        payload = _lstat_payload(path)
    except OSError as exc:
        return True, f"lstat failed: {type(exc).__name__}: {exc}"
    if stat.S_ISLNK(payload["mode"]):
        return True, "symbolic link"
    if payload["file_attributes"] & _FILE_ATTRIBUTE_REPARSE_POINT:
        return True, "Windows reparse point or junction"
    return False, None


def _lexically_confined(root: Path, path: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _path_chain_errors(root: Path, path: Path) -> list[str]:
    """Reject redirected parents before any path is resolved or followed."""
    errors: list[str] = []
    if not _lexically_confined(root, path):
        return ["path is not lexically confined to the project root"]
    relative = path.relative_to(root)
    current = root
    for part in relative.parts:
        current = current / part
        if not os.path.lexists(current):
            break
        indirect, reason = _is_indirection(current)
        if indirect:
            errors.append(f"filesystem indirection is forbidden at {current.relative_to(root).as_posix()!r}: {reason}")
            break
    return errors


def _directory_fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(json.dumps(_lstat_payload(path), sort_keys=True).encode("utf-8"))
    with os.scandir(path) as entries:
        for entry in sorted(entries, key=lambda item: item.name):
            child = path / entry.name
            digest.update(entry.name.encode("utf-8"))
            digest.update(b"\0")
            payload = _lstat_payload(child)
            digest.update(json.dumps(payload, sort_keys=True).encode("utf-8"))
            if stat.S_ISREG(payload["mode"]) and not (payload["file_attributes"] & _FILE_ATTRIBUTE_REPARSE_POINT):
                try:
                    digest.update(hashlib.sha256(child.read_bytes()).digest())
                except OSError as exc:
                    digest.update(f"unreadable:{type(exc).__name__}:{exc}".encode("utf-8"))
    return digest.hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


SURFACE_REQUIRED_KEYS = frozenset({
    "schema_version", "artifact_type", "surface_id", "source_surface_manifest_id",
    "dashboard_preview", "cli_preview", "api_preview", "smoke_preview",
    "manual_builder", "manual_text_renderer", "authority_level", "activation",
    "parity_anchor", "review_only", "generated_wiring_activated",
    "applies_source_edits", "release_authorized", "autonomy_expanded",
})
WRAPPER_REQUIRED_KEYS = frozenset({
    "schema_version", "artifact_type", "surface_id", "source_artifact_path",
    "manual_builder", "manual_text_renderer", "dashboard_wrapper", "cli_wrapper",
    "api_wrapper", "smoke_wrapper", "rollback_expectation", "protected_manual_status",
    "review_only", "generated_wiring_activated", "applies_source_edits",
    "release_authorized", "autonomy_expanded",
})
TOP_LEVEL_SAFE_FALSE_FIELDS = (
    "generated_wiring_activated", "applies_source_edits", "release_authorized", "autonomy_expanded",
)


def _version_tuple(value: Any) -> tuple[int, ...] | None:
    if not isinstance(value, str) or not value:
        return None
    parts = value.split(".")
    if not all(part.isdigit() for part in parts):
        return None
    return tuple(int(part) for part in parts)


def _validate_exact_object(
    data: dict[str, Any],
    field: str,
    required_keys: frozenset[str],
    errors: list[str],
) -> dict[str, Any] | None:
    nested = data.get(field)
    if not isinstance(nested, dict):
        errors.append(f"{field} must be an object")
        return None
    actual = frozenset(nested)
    missing = sorted(required_keys - actual)
    unexpected = sorted(actual - required_keys)
    if missing:
        errors.append(f"{field} missing schema fields: {missing}")
    if unexpected:
        errors.append(f"{field} has unexpected schema fields: {unexpected}")
    return nested


def _require_nonempty_string(data: dict[str, Any], field: str, errors: list[str], *, prefix: str = "") -> None:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{prefix}{field} must be a non-empty string")


def _validate_wiring_object(
    data: dict[str, Any],
    field: str,
    required_keys: frozenset[str],
    string_fields: tuple[str, ...],
    errors: list[str],
) -> dict[str, Any] | None:
    nested = _validate_exact_object(data, field, required_keys, errors)
    if nested is None:
        return None
    for string_field in string_fields:
        _require_nonempty_string(nested, string_field, errors, prefix=f"{field}.")
    if nested.get("wiring_activated") is not False:
        errors.append(f"{field}.wiring_activated must be false")
    return nested


def _validate_artifact_schema(rel_dir: str, name: str, data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["artifact must be a JSON object"]
    schema_version = data.get("schema_version")
    current = _version_tuple(RUNTIME_VERSION)
    observed = _version_tuple(schema_version)
    if observed is None:
        errors.append("schema_version must be a dotted numeric version")
    elif observed != current:
        relation = "stale" if current is not None and observed < current else "future_or_incompatible"
        errors.append(f"schema_version {schema_version!r} is {relation}; expected {RUNTIME_VERSION!r}")

    if data.get("review_only") is not True:
        errors.append("review_only must be true")
    for field in TOP_LEVEL_SAFE_FALSE_FIELDS:
        if data.get(field) is not False:
            errors.append(f"{field} must be false")

    if rel_dir.endswith("generated_surface_scaffold_previews"):
        expected_keys = SURFACE_REQUIRED_KEYS
        expected_type = "generated_surface_scaffold_preview_review_only"
        surface_id = name.removesuffix(".json")
        if data.get("artifact_type") != expected_type:
            errors.append(f"artifact_type must be {expected_type!r}")
        if data.get("surface_id") != surface_id:
            errors.append("surface_id does not match artifact filename")
        if data.get("source_surface_manifest_id") != surface_id:
            errors.append("source_surface_manifest_id must match surface_id")
        dashboard = _validate_wiring_object(
            data, "dashboard_preview",
            frozenset({"route", "renderer", "style_contract", "hover_contract", "native_title_tooltips_allowed", "wiring_activated"}),
            ("route", "renderer", "style_contract", "hover_contract"), errors,
        )
        if dashboard is not None:
            if dashboard.get("style_contract") != "command-deck/operator-console":
                errors.append("dashboard_preview.style_contract is invalid")
            if dashboard.get("hover_contract") != "data-tip":
                errors.append("dashboard_preview.hover_contract is invalid")
            if dashboard.get("native_title_tooltips_allowed") is not False:
                errors.append("dashboard_preview.native_title_tooltips_allowed must be false")
        _validate_wiring_object(
            data, "cli_preview",
            frozenset({"flag", "builder", "text_renderer", "wiring_activated"}),
            ("flag", "builder", "text_renderer"), errors,
        )
        api = _validate_wiring_object(
            data, "api_preview",
            frozenset({"route", "exposure", "wiring_activated"}),
            ("route", "exposure"), errors,
        )
        if api is not None and api.get("exposure") not in {"preview_only", "not_exposed_review_only"}:
            errors.append("api_preview.exposure is invalid")
        smoke = _validate_wiring_object(
            data, "smoke_preview",
            frozenset({"check", "segment", "expected_version_source", "wiring_activated"}),
            ("check", "segment", "expected_version_source"), errors,
        )
        if smoke is not None and smoke.get("expected_version_source") != "EXPECTED_CURRENT_VERSION":
            errors.append("smoke_preview.expected_version_source must be EXPECTED_CURRENT_VERSION")
        activation_keys = frozenset({
            "generated_preview_authoritative", "generated_wiring_activated",
            "dashboard_wiring_activated", "api_wiring_activated", "cli_wiring_activated",
            "smoke_wiring_activated", "applies_source_edits", "release_authorized",
            "autonomy_expanded", "protected_systems_require_operator_approval",
        })
        activation = _validate_exact_object(data, "activation", activation_keys, errors)
        if activation is not None:
            for field in activation_keys - {"protected_systems_require_operator_approval"}:
                if activation.get(field) is not False:
                    errors.append(f"activation.{field} must be false")
            if activation.get("protected_systems_require_operator_approval") is not True:
                errors.append("activation.protected_systems_require_operator_approval must be true")
        for field in ("manual_builder", "manual_text_renderer", "authority_level", "parity_anchor"):
            _require_nonempty_string(data, field, errors)
        if data.get("authority_level") != "review_only":
            errors.append("authority_level must be review_only")
        if data.get("parity_anchor") != "v930-multi-surface-generated-parity-batch-closure":
            errors.append("parity_anchor is invalid")
    elif rel_dir.endswith("generated_scaffold_wrapper_previews"):
        expected_keys = WRAPPER_REQUIRED_KEYS
        expected_type = "generated_scaffold_compatibility_wrapper_preview_review_only"
        surface_id = name.removesuffix(".wrapper.json")
        if data.get("artifact_type") != expected_type:
            errors.append(f"artifact_type must be {expected_type!r}")
        if data.get("surface_id") != surface_id:
            errors.append("surface_id does not match wrapper filename")
        expected_source = f"sandbox/generated_surface_scaffold_previews/{surface_id}.json"
        if data.get("source_artifact_path") != expected_source:
            errors.append("source_artifact_path does not match the paired scaffold artifact")
        dashboard = _validate_wiring_object(
            data, "dashboard_wrapper",
            frozenset({"manual_route", "wrapper_target", "style_contract", "hover_contract", "native_title_tooltips_allowed", "wiring_activated"}),
            ("manual_route", "wrapper_target", "style_contract", "hover_contract"), errors,
        )
        if dashboard is not None:
            if dashboard.get("style_contract") != "command-deck/operator-console":
                errors.append("dashboard_wrapper.style_contract is invalid")
            if dashboard.get("hover_contract") != "data-tip":
                errors.append("dashboard_wrapper.hover_contract is invalid")
            if dashboard.get("native_title_tooltips_allowed") is not False:
                errors.append("dashboard_wrapper.native_title_tooltips_allowed must be false")
        _validate_wiring_object(
            data, "cli_wrapper",
            frozenset({"manual_flag", "wrapper_target", "builder_target", "text_renderer", "wiring_activated"}),
            ("manual_flag", "wrapper_target", "builder_target", "text_renderer"), errors,
        )
        api = _validate_wiring_object(
            data, "api_wrapper",
            frozenset({"manual_route", "exposure", "wrapper_target", "wiring_activated"}),
            ("manual_route", "exposure", "wrapper_target"), errors,
        )
        if api is not None and api.get("exposure") not in {"preview_only", "not_exposed_review_only"}:
            errors.append("api_wrapper.exposure is invalid")
        smoke = _validate_wiring_object(
            data, "smoke_wrapper",
            frozenset({"manual_check", "wrapper_target", "segment", "expected_version_source", "wiring_activated"}),
            ("manual_check", "wrapper_target", "segment", "expected_version_source"), errors,
        )
        if smoke is not None and smoke.get("expected_version_source") != "EXPECTED_CURRENT_VERSION":
            errors.append("smoke_wrapper.expected_version_source must be EXPECTED_CURRENT_VERSION")
        rollback = _validate_exact_object(
            data, "rollback_expectation",
            frozenset({"manual_code_unchanged", "generated_wrapper_can_be_removed_by_deleting_sandbox_artifact", "live_wiring_rollback_required"}),
            errors,
        )
        if rollback is not None and (
            rollback.get("manual_code_unchanged") is not True
            or rollback.get("generated_wrapper_can_be_removed_by_deleting_sandbox_artifact") is not True
            or rollback.get("live_wiring_rollback_required") is not False
        ):
            errors.append("rollback_expectation is missing safe rollback fields")
        protected = _validate_exact_object(
            data, "protected_manual_status",
            frozenset({"manual_code_replaced", "generated_wrapper_authoritative", "protected_systems_require_operator_approval"}),
            errors,
        )
        if protected is not None and (
            protected.get("manual_code_replaced") is not False
            or protected.get("generated_wrapper_authoritative") is not False
            or protected.get("protected_systems_require_operator_approval") is not True
        ):
            errors.append("protected_manual_status is missing required non-authority fields")
        for field in ("manual_builder", "manual_text_renderer"):
            _require_nonempty_string(data, field, errors)
    else:  # pragma: no cover - TARGETS is closed and statically defined
        return [f"unsupported evidence directory: {rel_dir}"]

    actual_keys = frozenset(data)
    missing_keys = sorted(expected_keys - actual_keys)
    unexpected_keys = sorted(actual_keys - expected_keys)
    if missing_keys:
        errors.append(f"missing schema fields: {missing_keys}")
    if unexpected_keys:
        errors.append(f"unexpected schema fields: {unexpected_keys}")
    return errors


def _directory_inventory(path: Path) -> tuple[set[str], list[str]]:
    names: set[str] = set()
    errors: list[str] = []
    try:
        entries = list(os.scandir(path))
    except OSError as exc:
        return names, [f"directory inventory failed: {type(exc).__name__}: {exc}"]
    for entry in entries:
        child = path / entry.name
        names.add(entry.name)
        try:
            payload = _lstat_payload(child)
        except OSError as exc:
            errors.append(f"entry lstat failed for {entry.name!r}: {type(exc).__name__}: {exc}")
            continue
        if stat.S_ISLNK(payload["mode"]):
            errors.append(f"symlink entries are forbidden: {entry.name!r}")
        elif payload["file_attributes"] & _FILE_ATTRIBUTE_REPARSE_POINT:
            errors.append(f"Windows reparse-point or junction entries are forbidden: {entry.name!r}")
        elif not stat.S_ISREG(payload["mode"]):
            errors.append(f"non-file entries are forbidden: {entry.name!r}")
    return names, errors


def _validated_ledger_entries(
    root: Path,
    rel_dir: str,
    ledger: Any,
    expected_names: tuple[str, ...],
) -> tuple[bool, list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    rows: list[dict[str, Any]] = []
    base = root / rel_dir
    entries = ledger.get("artifacts") if isinstance(ledger, dict) else None
    if not isinstance(entries, list):
        return False, rows, ["ledger artifacts must be a list"]
    if len(entries) != len(expected_names):
        errors.append(f"ledger must contain exactly {len(expected_names)} artifact entries")

    seen_paths: set[str] = set()
    expected_paths = {f"{rel_dir}/{name}" for name in expected_names}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"artifact entry {index} is not an object")
            continue
        if set(entry) != {"path", "sha256"}:
            errors.append(f"artifact entry {index} must contain only path and sha256")
        raw_path = entry.get("path")
        expected_hash = entry.get("sha256")
        if not isinstance(raw_path, str) or not raw_path.strip():
            errors.append(f"artifact entry {index} has no path")
            continue
        normalized = raw_path.replace("\\", "/").strip("/")
        relative = Path(normalized)
        if relative.is_absolute() or ".." in relative.parts:
            errors.append(f"artifact entry {index} path escapes the project: {raw_path!r}")
            continue
        artifact_path = root / relative
        if artifact_path.parent != base or not _lexically_confined(root, artifact_path):
            errors.append(f"artifact entry {index} is outside {rel_dir}: {raw_path!r}")
            continue
        chain_errors = _path_chain_errors(root, artifact_path)
        if chain_errors:
            errors.extend(f"artifact entry {index}: {message}" for message in chain_errors)
            continue
        if normalized not in expected_paths:
            errors.append(f"artifact entry {index} is not an expected retired artifact: {normalized!r}")
            continue
        if normalized in seen_paths:
            errors.append(f"duplicate artifact path in ledger: {normalized!r}")
            continue
        seen_paths.add(normalized)
        if not isinstance(expected_hash, str) or len(expected_hash) != 64 or any(ch not in _HEX_DIGITS for ch in expected_hash.lower()):
            errors.append(f"artifact entry {index} has an invalid sha256")
            continue
        try:
            artifact_identity = _lstat_payload(artifact_path)
        except OSError:
            errors.append(f"artifact entry {index} does not reference a regular file: {normalized!r}")
            continue
        if stat.S_ISLNK(artifact_identity["mode"]) or artifact_identity["file_attributes"] & _FILE_ATTRIBUTE_REPARSE_POINT or not stat.S_ISREG(artifact_identity["mode"]):
            errors.append(f"artifact entry {index} references filesystem indirection or a non-regular file: {normalized!r}")
            continue
        try:
            actual_hash = _sha256(artifact_path)
            artifact_data = _read_json(artifact_path)
        except OSError as exc:
            errors.append(f"artifact entry {index} could not be read: {type(exc).__name__}: {exc}")
            continue
        hash_matches = actual_hash == expected_hash.lower()
        if not hash_matches:
            errors.append(f"artifact entry {index} sha256 mismatch: {normalized!r}")
        schema_errors = _validate_artifact_schema(rel_dir, artifact_path.name, artifact_data)
        errors.extend(f"{artifact_path.name}: {message}" for message in schema_errors)
        rows.append({
            "path": normalized,
            "expected_sha256": expected_hash.lower(),
            "actual_sha256": actual_hash,
            "hash_matches": hash_matches,
            "schema_valid": not schema_errors,
            "schema_errors": schema_errors,
        })

    if seen_paths != expected_paths:
        missing = sorted(expected_paths - seen_paths)
        unexpected = sorted(seen_paths - expected_paths)
        if missing:
            errors.append(f"missing expected ledger paths: {missing}")
        if unexpected:
            errors.append(f"unexpected ledger paths: {unexpected}")

    if isinstance(ledger, dict):
        ledger_version = _version_tuple(ledger.get("schema_version"))
        if ledger_version != _version_tuple(RUNTIME_VERSION):
            errors.append(f"ledger schema_version must equal current runtime {RUNTIME_VERSION}")
        allowed_ledger_keys = {
            "schema_version", "review_only", "generated_wiring_activated",
            "release_authorized", "autonomy_expanded", "artifacts",
        }
        extra_ledger_keys = sorted(set(ledger) - allowed_ledger_keys)
        if extra_ledger_keys:
            errors.append(f"unexpected ledger fields: {extra_ledger_keys}")
    safety_ok = isinstance(ledger, dict) and all((
        ledger.get("review_only") is True,
        ledger.get("generated_wiring_activated") is False,
        ledger.get("release_authorized") is False,
        ledger.get("autonomy_expanded") is False,
    ))
    if not safety_ok:
        errors.append("ledger safety fields are missing or unsafe")
    return not errors, rows, errors


def _inspect_target(root: Path, rel_dir: str, ledger_name: str, expected_names: tuple[str, ...]) -> dict[str, Any]:
    path = root / rel_dir
    chain_errors = _path_chain_errors(root, path)
    if chain_errors:
        return {
            "path": rel_dir,
            "status": "blocked",
            "needs_quarantine": False,
            "error": "; ".join(chain_errors),
            "validation_errors": chain_errors,
        }
    if not os.path.lexists(path):
        return {"path": rel_dir, "status": "absent", "needs_quarantine": False, "json_file_count": 0}
    try:
        target_identity = _lstat_payload(path)
    except OSError as exc:
        return {"path": rel_dir, "status": "blocked", "needs_quarantine": False, "error": f"target lstat failed: {exc}"}
    if stat.S_ISLNK(target_identity["mode"]) or target_identity["file_attributes"] & _FILE_ATTRIBUTE_REPARSE_POINT or not stat.S_ISDIR(target_identity["mode"]):
        return {"path": rel_dir, "status": "blocked", "needs_quarantine": False, "error": "target is filesystem indirection or not a regular directory"}

    physical_names, inventory_errors = _directory_inventory(path)
    fingerprint = _directory_fingerprint(path)
    if not physical_names:
        return {
            "path": rel_dir,
            "status": "quarantine_required",
            "needs_quarantine": True,
            "reason": "empty_retired_evidence_directory",
            "json_file_count": 0,
            "physical_inventory": [],
            "validation_errors": ["empty evidence directory violates exact inventory"],
            "target_identity": target_identity,
            "inspection_fingerprint": fingerprint,
        }
    expected_inventory = {ledger_name, *expected_names}
    missing_physical = sorted(expected_inventory - physical_names)
    unexpected_physical = sorted(physical_names - expected_inventory)
    if missing_physical:
        inventory_errors.append(f"missing physical artifacts: {missing_physical}")
    if unexpected_physical:
        inventory_errors.append(f"unexpected physical artifacts: {unexpected_physical}")

    ledger_path = path / ledger_name
    ledger = _read_json(ledger_path)
    ledger_entries_ok, ledger_rows, ledger_errors = _validated_ledger_entries(root, rel_dir, ledger, expected_names)
    validation_errors = [*inventory_errors, *ledger_errors]
    current_complete = isinstance(ledger, dict) and not validation_errors and ledger_entries_ok
    common = {
        "target_identity": target_identity,
        "inspection_fingerprint": fingerprint,
        "physical_inventory": sorted(physical_names),
    }
    if current_complete:
        return {
            "path": rel_dir,
            "status": "current_complete",
            "needs_quarantine": False,
            "json_file_count": len(physical_names),
            "physical_inventory_validation": "pass",
            "ledger_schema_version": ledger.get("schema_version"),
            "ledger_path_validation": "pass",
            "ledger_hash_validation": "pass",
            "artifact_schema_validation": "pass",
            "artifact_rows": ledger_rows,
            **common,
        }

    schema_versions = sorted({
        str(data.get("schema_version"))
        for item in path.glob("*.json")
        for data in [_read_json(item)]
        if isinstance(data, dict) and data.get("schema_version") is not None
    })
    reason = "missing_or_invalid_ledger" if not isinstance(ledger, dict) else "partial_stale_or_untrusted_retired_evidence"
    return {
        "path": rel_dir,
        "status": "quarantine_required",
        "needs_quarantine": True,
        "reason": reason,
        "json_file_count": len(physical_names),
        "ledger_present": ledger_path.is_file(),
        "ledger_schema_version": ledger.get("schema_version") if isinstance(ledger, dict) else None,
        "expected_inventory": sorted(expected_inventory),
        "validation_errors": validation_errors,
        "ledger_validation_errors": ledger_errors,
        "inventory_validation_errors": inventory_errors,
        "artifact_rows": ledger_rows,
        "observed_schema_versions": schema_versions,
        **common,
    }


def _transaction_manifest(
    *,
    planned: list[dict[str, Any]],
    status: str,
    moved: list[dict[str, Any]] | None = None,
    error: str | None = None,
    rollback_errors: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "migration_id": MIGRATION_ID,
        "runtime_version": RUNTIME_VERSION,
        "updated_at": _now().isoformat(),
        "transaction_status": status,
        "operation": "move_to_quarantine",
        "files_deleted": 0,
        "reversible": True,
        "planned": planned,
        "moved": moved or [],
        "error": error,
        "rollback_errors": rollback_errors or [],
    }


def build_migration_report(
    root: str | Path = ROOT,
    *,
    apply: bool = False,
    _move: Callable[[str, str], Any] = shutil.move,
    _before_apply: Callable[[Path, list[dict[str, Any]]], None] | None = None,
) -> dict[str, Any]:
    project_root = Path(root).resolve()
    inspected = [_inspect_target(project_root, rel_dir, ledger_name, names) for rel_dir, ledger_name, names in TARGETS]
    blocked = [row for row in inspected if row.get("status") == "blocked"]
    candidates = [row for row in inspected if row.get("needs_quarantine") is True]
    moved: list[dict[str, Any]] = []
    quarantine_root: Path | None = None
    transaction_status = "not_started"
    transaction_error: str | None = None
    rollback_errors: list[str] = []

    if apply and candidates and not blocked:
        stamp = _now().strftime("%Y%m%dT%H%M%SZ")
        quarantine_root = project_root / "sandbox" / "retired_evidence_quarantine" / stamp
        suffix = 1
        while quarantine_root.exists():
            quarantine_root = project_root / "sandbox" / "retired_evidence_quarantine" / f"{stamp}_{suffix}"
            suffix += 1
        quarantine_root.mkdir(parents=True, exist_ok=False)
        planned = [
            {
                "source": str(row["path"]),
                "destination": (quarantine_root / str(row["path"]).replace("/", "__")).relative_to(project_root).as_posix(),
                "reason": row.get("reason"),
                "json_file_count": row.get("json_file_count"),
                "target_identity": row.get("target_identity"),
                "inspection_fingerprint": row.get("inspection_fingerprint"),
            }
            for row in candidates
        ]
        manifest_path = quarantine_root / "migration_manifest.json"
        transaction_status = "prepared"
        # The durable plan exists before the first move. If the process is
        # interrupted, operators can see every intended source/destination pair.
        _atomic_write_json(manifest_path, _transaction_manifest(planned=planned, status=transaction_status))
        try:
            if _before_apply is not None:
                _before_apply(project_root, planned)
            for plan in planned:
                source = project_root / str(plan["source"])
                destination = project_root / str(plan["destination"])
                current = _inspect_target(project_root, str(plan["source"]), next(item[1] for item in TARGETS if item[0] == plan["source"]), next(item[2] for item in TARGETS if item[0] == plan["source"]))
                if current.get("needs_quarantine") is not True:
                    raise RuntimeError(f"source changed state after inspection: {plan['source']}")
                if current.get("target_identity") != plan.get("target_identity") or current.get("inspection_fingerprint") != plan.get("inspection_fingerprint"):
                    raise RuntimeError(f"source object changed after inspection: {plan['source']}")
                if destination.exists():
                    raise RuntimeError(f"quarantine destination already exists: {plan['destination']}")
                _move(str(source), str(destination))
                moved.append(dict(plan))
                transaction_status = "moving"
                _atomic_write_json(
                    manifest_path,
                    _transaction_manifest(planned=planned, status=transaction_status, moved=moved),
                )
        except Exception as exc:
            transaction_error = f"{type(exc).__name__}: {exc}"
            for plan in reversed(moved):
                source = project_root / str(plan["source"])
                destination = project_root / str(plan["destination"])
                try:
                    if destination.exists() and not source.exists():
                        _move(str(destination), str(source))
                except Exception as rollback_exc:  # pragma: no cover - exceptional filesystem failure
                    rollback_errors.append(f"{plan['source']}: {type(rollback_exc).__name__}: {rollback_exc}")
            transaction_status = "rollback_failed" if rollback_errors else "rolled_back"
            _atomic_write_json(
                manifest_path,
                _transaction_manifest(
                    planned=planned,
                    status=transaction_status,
                    moved=moved,
                    error=transaction_error,
                    rollback_errors=rollback_errors,
                ),
            )
            if not rollback_errors:
                moved = []
        else:
            transaction_status = "committed"
            _atomic_write_json(
                manifest_path,
                _transaction_manifest(planned=planned, status=transaction_status, moved=moved),
            )

    ok = not blocked and (
        not apply
        or not candidates
        or (transaction_status == "committed" and len(moved) == len(candidates))
    )
    return {
        "version": RUNTIME_VERSION,
        "migration_id": MIGRATION_ID,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "mode": "apply" if apply else "dry_run",
        "targets": inspected,
        "quarantine_required_count": len(candidates),
        "quarantined_count": len(moved) if transaction_status == "committed" else 0,
        "quarantine_root": quarantine_root.relative_to(project_root).as_posix() if quarantine_root else None,
        "transaction_status": transaction_status,
        "transaction_error": transaction_error,
        "rollback_errors": rollback_errors,
        "moved": moved,
        "files_deleted": 0,
        "source_files_modified": 0,
        "reversible": True,
        "operator_review_required": True,
    }


def _print_text(report: dict[str, Any], *, quiet: bool) -> None:
    if quiet and report.get("ok") and report.get("quarantine_required_count") == 0:
        return
    print(f"Eidolon upgrade migration: {report.get('status')} ({report.get('mode')})")
    for row in report.get("targets", []):
        print(f"- {row.get('path')}: {row.get('status')}")
    if report.get("transaction_status") not in (None, "not_started"):
        print(f"Transaction: {report.get('transaction_status')}")
    if report.get("moved") and report.get("transaction_status") == "committed":
        print(f"Quarantined {report.get('quarantined_count')} retired evidence directorie(s) under {report.get('quarantine_root')}.")
    elif report.get("quarantine_required_count") and report.get("mode") == "dry_run":
        print("Run again with --apply to move the retired evidence into reversible quarantine.")
    if report.get("transaction_error"):
        print(f"Migration error: {report.get('transaction_error')}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect or quarantine retired Eidolon sandbox evidence retained by an in-place upgrade.")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--apply", action="store_true", help="Move known partial/stale evidence directories into timestamped quarantine.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    report = build_migration_report(args.root, apply=args.apply)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _print_text(report, quiet=args.quiet)
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
