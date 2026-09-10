from __future__ import annotations

"""Exact staged installation apply with external transaction evidence.

The module mutates only the exact registered target bound by the active staged
plan. Candidate, transaction, backup and receipt records remain beneath an
external runtime root. Promotion and certification are intentionally absent.
"""

from collections import Counter
import json
import os
from pathlib import Path, PurePosixPath
import secrets
import shutil
from typing import Any, Iterable, Mapping

try:
    from process_ownership import current_process_start_identity, process_is_alive
    from release_candidate_identity import atomic_json, build_source_manifest, digest_payload, read_json, runtime_data_root, sha256_file, utc_now
    from release_installation_plan import _plan_binding, plan_directory, protected_policy_sha256
    from release_installation_preview import _protected, _safe_relative, _target_inventory
    from release_installation_staging import _stage_binding, _verify_affected_candidate_files, installation_staging_status, staging_directory
except ImportError:
    from process_ownership import current_process_start_identity, process_is_alive
    from release_candidate_identity import atomic_json, build_source_manifest, digest_payload, read_json, runtime_data_root, sha256_file, utc_now
    from release_installation_plan import _plan_binding, plan_directory, protected_policy_sha256
    from release_installation_preview import _protected, _safe_relative, _target_inventory
    from release_installation_staging import _stage_binding, _verify_affected_candidate_files, installation_staging_status, staging_directory

INSTALLATION_TRANSACTION_CONTRACT_VERSION = "1"
INSTALLATION_TRANSACTION_SCHEMA = "eidolon-installation-transaction-v1"
INSTALLATION_TRANSACTION_DIRECTORY = "release_installation_transactions"
INSTALLATION_APPLY_CONFIRMATION = "APPLY EXACT STAGED INSTALLATION"
INSTALLATION_APPLY_ACTION = "apply_exact_staged_installation_transactionally"
ALLOWED_MUTATION_KINDS = {"add", "replace", "remove"}


def transaction_directory(runtime_root: str | Path | None = None) -> Path:
    return runtime_data_root(runtime_root) / INSTALLATION_TRANSACTION_DIRECTORY


def _kind_counts(rows: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    for row in rows or []:
        counts[str(row.get("kind") or "unknown")] += max(1, int(row.get("count") or 1))
    return [{"kind": key, "count": counts[key]} for key in sorted(counts)]


def _token_digest(token: str) -> str:
    return digest_payload({"contract": "eidolon-installation-apply-token-file-v1", "token": token})


def _load_active_stage(runtime_root: str | Path | None) -> tuple[dict[str, Any], dict[str, Any]]:
    directory = staging_directory(runtime_root)
    pointer = read_json(directory / "active_stage.json")
    stage_id = str(pointer.get("stage_id") or "")
    return pointer, read_json(directory / "records" / f"{stage_id}.json") if stage_id else {}


def _load_plan(runtime_root: str | Path | None, plan_id: str) -> dict[str, Any]:
    return read_json(plan_directory(runtime_root) / "records" / f"{plan_id}.json") if plan_id else {}


def _transaction_identity(record: Mapping[str, Any]) -> str:
    return digest_payload({
        "contract": "eidolon-installation-transaction-identity-v1",
        "transaction_id": str(record.get("transaction_id") or ""),
        "generation": int(record.get("generation") or 0),
        "action": str(record.get("action") or ""),
        "stage_id": str(record.get("stage_id") or ""),
        "stage_generation": int(record.get("stage_generation") or 0),
        "stage_binding_sha256": str(record.get("stage_binding_sha256") or ""),
        "staging_record_sha256": str(record.get("staging_record_sha256") or ""),
        "plan_id": str(record.get("plan_id") or ""),
        "plan_binding_sha256": str(record.get("plan_binding_sha256") or ""),
        "candidate_id": str(record.get("candidate_id") or ""),
        "archive_sha256": str(record.get("archive_sha256") or ""),
        "source_manifest_sha256": str(record.get("source_manifest_sha256") or ""),
        "archive_manifest_sha256": str(record.get("archive_manifest_sha256") or ""),
        "target_project_id": str(record.get("target_project_id") or ""),
        "target_identity_sha256": str(record.get("target_identity_sha256") or ""),
        "target_pre_apply_inventory_sha256": str(record.get("target_pre_apply_inventory_sha256") or ""),
        "effects_sha256": str(record.get("effects_sha256") or ""),
        "protected_policy_sha256": str(record.get("protected_policy_sha256") or ""),
        "backup_plan_sha256": str(record.get("backup_plan_sha256") or ""),
        "rollback_plan_sha256": str(record.get("rollback_plan_sha256") or ""),
        "authorization_binding_sha256": str(record.get("authorization_binding_sha256") or ""),
    })


def _state_digest(record: Mapping[str, Any]) -> str:
    return digest_payload({
        "contract": "eidolon-installation-transaction-state-v1",
        "transaction_identity_sha256": str(record.get("transaction_identity_sha256") or ""),
        "state": str(record.get("state") or ""),
        "event_sequence": int(record.get("event_sequence") or 0),
        "backups_completed": list(record.get("backups_completed") or []),
        "effects_completed": list(record.get("effects_completed") or []),
        "rollback_completed": list(record.get("rollback_completed") or []),
        "target_current_inventory_sha256": str(record.get("target_current_inventory_sha256") or ""),
        "installed_receipt_sha256": str(record.get("installed_receipt_sha256") or ""),
        "rollback_state": str(record.get("rollback_state") or ""),
    })


def _public(record: Mapping[str, Any] | None) -> dict[str, Any]:
    row = dict(record or {})
    contradictions = _kind_counts(row.get("contradictions") if isinstance(row.get("contradictions"), list) else [])
    return {
        "ok": bool(row.get("ok")) and not contradictions,
        "status": str(row.get("status") or row.get("state") or "not_applied"),
        "contract_version": INSTALLATION_TRANSACTION_CONTRACT_VERSION,
        "transaction_present": bool(row),
        "transaction_id": str(row.get("transaction_id") or ""),
        "transaction_identity_sha256": str(row.get("transaction_identity_sha256") or ""),
        "transaction_state_sha256": str(row.get("transaction_state_sha256") or ""),
        "generation": int(row.get("generation") or 0),
        "stage_id": str(row.get("stage_id") or ""),
        "stage_generation": int(row.get("stage_generation") or 0),
        "plan_id": str(row.get("plan_id") or ""),
        "candidate_id": str(row.get("candidate_id") or ""),
        "packaged_version": str(row.get("packaged_version") or ""),
        "archive_sha256": str(row.get("archive_sha256") or ""),
        "source_manifest_sha256": str(row.get("source_manifest_sha256") or ""),
        "archive_manifest_sha256": str(row.get("archive_manifest_sha256") or ""),
        "target_project_id": str(row.get("target_project_id") or ""),
        "target_pre_apply_inventory_sha256": str(row.get("target_pre_apply_inventory_sha256") or ""),
        "target_current_inventory_sha256": str(row.get("target_current_inventory_sha256") or ""),
        "effects_sha256": str(row.get("effects_sha256") or ""),
        "backup_plan_sha256": str(row.get("backup_plan_sha256") or ""),
        "rollback_plan_sha256": str(row.get("rollback_plan_sha256") or ""),
        "backup_count": len(row.get("backups_completed") or []),
        "completed_effect_count": len(row.get("effects_completed") or []),
        "total_effect_count": int(row.get("total_effect_count") or 0),
        "contradictions": contradictions,
        "contradiction_count": sum(int(item["count"]) for item in contradictions),
        "literal_confirmation_required": INSTALLATION_APPLY_CONFIRMATION,
        "backups_verified_before_mutation": bool(row.get("backups_verified_before_mutation")),
        "target_revalidated": bool(row.get("target_revalidated")),
        "stage_revalidated": bool(row.get("stage_revalidated")),
        "plan_revalidated": bool(row.get("plan_revalidated")),
        "disk_space_revalidated": bool(row.get("disk_space_revalidated")),
        "append_only_events": True,
        "paths_suppressed": True,
        "records_external": True,
        "content_free": True,
        "project_registry_changed": False,
        "installed": str(row.get("state") or "") == "installed_unpromoted",
        "promoted": False,
        "certified": False,
        "provider_contacted": False,
    }


def _authorization_binding(record: Mapping[str, Any]) -> str:
    return digest_payload({
        "contract": "eidolon-installation-apply-authorization-v1",
        "token_id": str(record.get("token_id") or ""),
        "action": str(record.get("action") or ""),
        "stage_id": str(record.get("stage_id") or ""),
        "stage_generation": int(record.get("stage_generation") or 0),
        "stage_binding_sha256": str(record.get("stage_binding_sha256") or ""),
        "staging_record_sha256": str(record.get("staging_record_sha256") or ""),
        "plan_id": str(record.get("plan_id") or ""),
        "plan_binding_sha256": str(record.get("plan_binding_sha256") or ""),
        "candidate_id": str(record.get("candidate_id") or ""),
        "archive_sha256": str(record.get("archive_sha256") or ""),
        "source_manifest_sha256": str(record.get("source_manifest_sha256") or ""),
        "archive_manifest_sha256": str(record.get("archive_manifest_sha256") or ""),
        "target_project_id": str(record.get("target_project_id") or ""),
        "target_identity_sha256": str(record.get("target_identity_sha256") or ""),
        "target_pre_apply_inventory_sha256": str(record.get("target_pre_apply_inventory_sha256") or ""),
        "effects_sha256": str(record.get("effects_sha256") or ""),
        "protected_policy_sha256": str(record.get("protected_policy_sha256") or ""),
        "backup_plan_sha256": str(record.get("backup_plan_sha256") or ""),
        "rollback_plan_sha256": str(record.get("rollback_plan_sha256") or ""),
        "nonce": str(record.get("nonce") or ""),
    })


def _stage_record_digest(record: Mapping[str, Any]) -> str:
    material = dict(record)
    material.pop("contradictions", None)
    return digest_payload({"schema": "eidolon-private-staging-record-digest-v1", "record": material})


def _used(runtime_root: str | Path | None, token: str) -> bool:
    return (transaction_directory(runtime_root) / "used" / f"{_token_digest(token)}.json").is_file()


def _mark_used(runtime_root: str | Path | None, token: str, status: str, transaction_id: str = "") -> None:
    atomic_json(transaction_directory(runtime_root) / "used" / f"{_token_digest(token)}.json", {
        "schema": "eidolon-installation-apply-token-use-v1", "status": status,
        "transaction_id": transaction_id, "used_at": utc_now(), "content_free": True,
    })


def _authorization(runtime_root: str | Path | None, token: str) -> dict[str, Any]:
    return read_json(transaction_directory(runtime_root) / "authorizations" / f"{_token_digest(token)}.json")


def preview_installation_apply_authorization(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    stage_status = installation_staging_status(runtime_root=runtime_root)
    pointer, stage = _load_active_stage(runtime_root)
    contradictions: list[dict[str, Any]] = []
    if not stage_status.get("ok") or not stage:
        contradictions.append({"kind": "coherent_external_stage_required"})
    if stage and str(stage.get("stage_binding_sha256") or "") != _stage_binding(stage):
        contradictions.append({"kind": "stage_binding_mismatch"})
    plan = _load_plan(runtime_root, str(stage.get("plan_id") or "")) if stage else {}
    if stage and (not plan or str(plan.get("plan_binding_sha256") or "") != _plan_binding(plan)):
        contradictions.append({"kind": "installation_plan_missing_or_mismatched"})
    if contradictions:
        return {**_public({"status": "coherent_stage_required", "contradictions": contradictions}), "authorization_token": ""}
    nonce = secrets.token_hex(24)
    token_id = f"installation-apply-auth-{secrets.token_hex(12)}"
    stage_generation = int(stage.get("stage_generation") or pointer.get("stage_generation") or 1)
    record = {
        "schema": "eidolon-installation-apply-authorization-v1",
        "token_id": token_id,
        "created_at": utc_now(),
        "action": INSTALLATION_APPLY_ACTION,
        "stage_id": str(stage.get("stage_id") or ""),
        "stage_generation": stage_generation,
        "stage_binding_sha256": str(stage.get("stage_binding_sha256") or ""),
        "staging_record_sha256": _stage_record_digest(stage),
        "plan_id": str(stage.get("plan_id") or ""),
        "plan_binding_sha256": str(stage.get("plan_binding_sha256") or ""),
        "candidate_id": str(stage.get("candidate_id") or ""),
        "archive_sha256": str(stage.get("archive_sha256") or ""),
        "source_manifest_sha256": str(stage.get("source_manifest_sha256") or ""),
        "archive_manifest_sha256": str(stage.get("archive_manifest_sha256") or plan.get("archive_manifest_sha256") or ""),
        "target_project_id": str(stage.get("target_project_id") or ""),
        "target_identity_sha256": str(stage.get("target_identity_sha256") or plan.get("target_identity_sha256") or ""),
        "target_pre_apply_inventory_sha256": str(stage.get("target_inventory_sha256") or ""),
        "effects_sha256": str(stage.get("effects_sha256") or ""),
        "protected_policy_sha256": str(stage.get("protected_policy_sha256") or plan.get("protected_policy_sha256") or ""),
        "backup_plan_sha256": str(stage.get("backup_plan_sha256") or ""),
        "rollback_plan_sha256": str(stage.get("rollback_plan_sha256") or ""),
        "literal_confirmation": INSTALLATION_APPLY_CONFIRMATION,
        "nonce": nonce,
        "content_free": True,
    }
    record["authorization_binding_sha256"] = _authorization_binding(record)
    token = f"{token_id}.{record['authorization_binding_sha256']}.{nonce}"
    atomic_json(transaction_directory(runtime_root) / "authorizations" / f"{_token_digest(token)}.json", record)
    return {
        "ok": True, "status": "apply_authorization_preview", "authorization_token": token,
        "authorization_binding_sha256": record["authorization_binding_sha256"],
        "stage_id": record["stage_id"], "stage_generation": stage_generation,
        "plan_id": record["plan_id"], "candidate_id": record["candidate_id"],
        "target_project_id": record["target_project_id"], "action": INSTALLATION_APPLY_ACTION,
        "literal_confirmation": INSTALLATION_APPLY_CONFIRMATION,
        "paths_suppressed": True, "records_external": True, "content_free": True,
        "promoted": False, "certified": False,
    }


def _append_event(runtime_root: str | Path | None, transaction_id: str, record: dict[str, Any], event: Mapping[str, Any]) -> None:
    record["event_sequence"] = int(record.get("event_sequence") or 0) + 1
    row = {"schema": "eidolon-installation-transaction-event-v1", "sequence": record["event_sequence"], "at": utc_now(), **dict(event)}
    path = transaction_directory(runtime_root) / "events" / f"{transaction_id}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
        handle.flush(); os.fsync(handle.fileno())


def _save_transaction(runtime_root: str | Path | None, record: dict[str, Any]) -> None:
    record["transaction_state_sha256"] = _state_digest(record)
    atomic_json(transaction_directory(runtime_root) / "records" / f"{record['transaction_id']}.json", record)
    atomic_json(transaction_directory(runtime_root) / "active_transaction.json", {
        "schema": INSTALLATION_TRANSACTION_SCHEMA,
        "transaction_id": record["transaction_id"], "generation": record["generation"],
        "transaction_identity_sha256": record["transaction_identity_sha256"],
        "transaction_state_sha256": record["transaction_state_sha256"],
        "target_project_id": record["target_project_id"], "content_free": True,
    })


def _safe_target_path(root: Path, relative: str, *, create_parents: bool = False) -> Path:
    rel = _safe_relative(relative)
    if not rel or _protected(rel):
        raise ValueError("protected_or_invalid_target_path")
    root = root.resolve()
    if root.is_symlink() or not root.is_dir():
        raise ValueError("target_root_invalid")
    path = root.joinpath(*PurePosixPath(rel).parts)
    current = root
    for part in PurePosixPath(rel).parts[:-1]:
        current = current / part
        if current.exists() and current.is_symlink():
            raise ValueError("target_parent_symlink")
    if create_parents:
        path.parent.mkdir(parents=True, exist_ok=True)
        current = root
        for part in PurePosixPath(rel).parts[:-1]:
            current = current / part
            if current.is_symlink():
                raise ValueError("target_parent_symlink")
    return path


def _atomic_copy(source: Path, target: Path, transaction_id: str) -> None:
    data = source.read_bytes()
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.parent / f".{target.name}.{transaction_id}.{os.getpid()}.{secrets.token_hex(5)}.tmp"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(temp, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data); handle.flush(); os.fsync(handle.fileno())
        os.replace(temp, target)
    finally:
        try: temp.unlink()
        except FileNotFoundError: pass


def _verify_file(path: Path, expected_sha: str) -> bool:
    return bool(expected_sha and path.is_file() and not path.is_symlink() and sha256_file(path) == expected_sha)


def _read_stage_plans(stage: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    root = Path(str(stage.get("stage_root_path") or ""))
    return read_json(root / "backup_plan.json"), read_json(root / "rollback_plan.json")


def _revalidate_before_apply(runtime_root: str | Path | None, auth: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    contradictions: list[dict[str, Any]] = []
    stage_status = installation_staging_status(runtime_root=runtime_root)
    pointer, stage = _load_active_stage(runtime_root)
    plan = _load_plan(runtime_root, str(stage.get("plan_id") or "")) if stage else {}
    if not stage_status.get("ok") or not stage:
        contradictions.append({"kind": "installation_stage_stale"})
    if stage and str(stage.get("stage_binding_sha256") or "") != _stage_binding(stage):
        contradictions.append({"kind": "stage_binding_mismatch"})
    if plan and str(plan.get("plan_binding_sha256") or "") != _plan_binding(plan):
        contradictions.append({"kind": "plan_binding_mismatch"})
    bound = (
        "stage_id", "stage_binding_sha256", "plan_id", "plan_binding_sha256", "candidate_id",
        "archive_sha256", "source_manifest_sha256", "target_project_id", "effects_sha256",
        "backup_plan_sha256", "rollback_plan_sha256",
    )
    for field in bound:
        if str(auth.get(field) or "") != str(stage.get(field) or ""):
            contradictions.append({"kind": f"apply_authorization_{field}_mismatch"})
    if int(auth.get("stage_generation") or 0) != int(stage.get("stage_generation") or pointer.get("stage_generation") or 0):
        contradictions.append({"kind": "apply_authorization_stage_generation_mismatch"})
    if str(auth.get("staging_record_sha256") or "") != _stage_record_digest(stage):
        contradictions.append({"kind": "staging_record_changed"})
    if str(auth.get("archive_manifest_sha256") or "") != str(stage.get("archive_manifest_sha256") or plan.get("archive_manifest_sha256") or ""):
        contradictions.append({"kind": "archive_manifest_changed"})
    if str(auth.get("target_identity_sha256") or "") != str(stage.get("target_identity_sha256") or plan.get("target_identity_sha256") or ""):
        contradictions.append({"kind": "target_identity_changed"})
    if str(auth.get("protected_policy_sha256") or "") != protected_policy_sha256():
        contradictions.append({"kind": "protected_policy_changed"})
    candidate_root = Path(str(stage.get("candidate_stage_root_path") or ""))
    if not _verify_affected_candidate_files(candidate_root, stage, plan):
        contradictions.append({"kind": "staged_candidate_changed"})
    manifest = {"entries": []}
    backup_plan, rollback_plan = _read_stage_plans(stage)
    if digest_payload(backup_plan) != str(stage.get("backup_plan_sha256") or ""):
        contradictions.append({"kind": "backup_plan_changed"})
    if digest_payload(rollback_plan) != str(stage.get("rollback_plan_sha256") or ""):
        contradictions.append({"kind": "rollback_plan_changed"})
    target_root = Path(str(stage.get("target_root_path") or ""))
    inventory = _target_inventory(target_root) if str(stage.get("target_root_path") or "") else {"ok": False, "digest": "", "entries": []}
    if not inventory.get("ok") or str(inventory.get("digest") or "") != str(stage.get("target_inventory_sha256") or ""):
        contradictions.append({"kind": "target_changed_after_staging"})
    effects = list(plan.get("effects") or []) if isinstance(plan.get("effects"), list) else []
    if digest_payload({"schema": "eidolon-installation-effects-v1", "effects": effects}) != str(stage.get("effects_sha256") or ""):
        contradictions.append({"kind": "installation_effects_changed"})
    for effect in effects:
        kind = str(effect.get("kind") or "")
        path = str(effect.get("path") or "")
        if kind in ALLOWED_MUTATION_KINDS and (_protected(path) or not _safe_relative(path)):
            contradictions.append({"kind": "protected_mutation_effect"})
    needed = sum(int(row.get("candidate_size") or row.get("package_size") or 0) for row in effects if str(row.get("kind") or "") in {"add", "replace"})
    needed += sum(int(row.get("size") or 0) for row in inventory.get("entries", []) if str(row.get("path") or "") in {str(e.get("path") or "") for e in effects if str(e.get("kind") or "") in {"replace", "remove"}})
    try:
        free = shutil.disk_usage(target_root).free
    except OSError:
        free = 0
    if free < needed + 1024 * 1024:
        contradictions.append({"kind": "insufficient_disk_space"})
    return stage, plan, contradictions, {"manifest": manifest, "backup_plan": backup_plan, "rollback_plan": rollback_plan, "target_inventory": inventory, "disk_free": free, "disk_needed": needed}


def _create_record(runtime_root: str | Path | None, auth: Mapping[str, Any], stage: Mapping[str, Any], plan: Mapping[str, Any], details: Mapping[str, Any]) -> dict[str, Any]:
    directory = transaction_directory(runtime_root)
    pointer = read_json(directory / "active_transaction.json")
    generation = int(pointer.get("generation") or 0) + 1
    transaction_id = f"installation-transaction-{digest_payload({'stage': stage.get('stage_binding_sha256'), 'auth': auth.get('authorization_binding_sha256'), 'generation': generation})[:24]}"
    record = {
        "schema": INSTALLATION_TRANSACTION_SCHEMA, "contract_version": INSTALLATION_TRANSACTION_CONTRACT_VERSION,
        "transaction_id": transaction_id, "generation": generation, "created_at": utc_now(),
        "action": INSTALLATION_APPLY_ACTION, "state": "applying", "status": "applying", "ok": True,
        "stage_id": str(stage.get("stage_id") or ""), "stage_generation": int(stage.get("stage_generation") or 0),
        "stage_binding_sha256": str(stage.get("stage_binding_sha256") or ""), "staging_record_sha256": _stage_record_digest(stage),
        "plan_id": str(stage.get("plan_id") or ""), "plan_binding_sha256": str(stage.get("plan_binding_sha256") or ""),
        "authorization_binding_sha256": str(auth.get("authorization_binding_sha256") or ""),
        "candidate_id": str(stage.get("candidate_id") or ""), "packaged_version": str(stage.get("packaged_version") or ""),
        "archive_sha256": str(stage.get("archive_sha256") or ""), "source_manifest_sha256": str(stage.get("source_manifest_sha256") or ""),
        "archive_manifest_sha256": str(stage.get("archive_manifest_sha256") or plan.get("archive_manifest_sha256") or ""),
        "target_project_id": str(stage.get("target_project_id") or ""), "target_identity_sha256": str(stage.get("target_identity_sha256") or plan.get("target_identity_sha256") or ""),
        "target_pre_apply_inventory_sha256": str(stage.get("target_inventory_sha256") or ""), "target_current_inventory_sha256": str(stage.get("target_inventory_sha256") or ""),
        "effects_sha256": str(stage.get("effects_sha256") or ""), "protected_policy_sha256": str(stage.get("protected_policy_sha256") or plan.get("protected_policy_sha256") or ""),
        "backup_plan_sha256": str(stage.get("backup_plan_sha256") or ""), "rollback_plan_sha256": str(stage.get("rollback_plan_sha256") or ""),
        "stage_root_path": str(stage.get("stage_root_path") or ""), "candidate_stage_root_path": str(stage.get("candidate_stage_root_path") or ""),
        "target_root_path": str(stage.get("target_root_path") or ""), "backup_root_path": str(directory / "backups" / transaction_id),
        "effects": list(plan.get("effects") or []), "total_effect_count": sum(1 for row in plan.get("effects", []) if str(row.get("kind") or "") in ALLOWED_MUTATION_KINDS),
        "backups_completed": [], "effects_completed": [], "event_sequence": 0,
        "owner_pid": os.getpid(), "owner_start_identity": current_process_start_identity(), "owner_nonce": secrets.token_hex(24),
        "owner_released": False, "backups_verified_before_mutation": False, "target_revalidated": True,
        "stage_revalidated": True, "plan_revalidated": True, "disk_space_revalidated": True,
        "disk_free_before_apply": int(details.get("disk_free") or 0), "disk_required_estimate": int(details.get("disk_needed") or 0),
        "contradictions": [], "promoted": False, "certified": False, "content_free": True,
    }
    record["transaction_identity_sha256"] = _transaction_identity(record)
    _append_event(runtime_root, transaction_id, record, {"kind": "transaction_started", "state": "applying"})
    _save_transaction(runtime_root, record)
    return record


def _backup_all(runtime_root: str | Path | None, record: dict[str, Any], *, interrupt_at: str = "") -> bool:
    target_root = Path(record["target_root_path"])
    backup_root = Path(record["backup_root_path"])
    completed = set(str(x) for x in record.get("backups_completed") or [])
    if interrupt_at == "before_backup":
        record["state"] = record["status"] = "interrupted"; record["owner_released"] = True
        _append_event(runtime_root, record["transaction_id"], record, {"kind": "interrupted_before_backup"}); _save_transaction(runtime_root, record); return False
    for effect in record.get("effects", []):
        path = str(effect.get("path") or ""); kind = str(effect.get("kind") or "")
        if kind not in {"replace", "remove"} or path in completed:
            continue
        source = _safe_target_path(target_root, path)
        expected = str(effect.get("target_sha256") or "")
        if not _verify_file(source, expected):
            raise RuntimeError(f"target_changed_before_backup:{path}")
        destination = backup_root.joinpath(*PurePosixPath(_safe_relative(path)).parts)
        _atomic_copy(source, destination, record["transaction_id"])
        if not _verify_file(destination, expected):
            raise RuntimeError(f"backup_verification_failed:{path}")
        record.setdefault("backups_completed", []).append(path)
        _append_event(runtime_root, record["transaction_id"], record, {"kind": "backup_verified", "path": path, "sha256": expected})
        _save_transaction(runtime_root, record)
    record["backups_verified_before_mutation"] = True
    _append_event(runtime_root, record["transaction_id"], record, {"kind": "all_backups_verified"}); _save_transaction(runtime_root, record)
    if interrupt_at == "after_backup":
        record["state"] = record["status"] = "interrupted"; record["owner_released"] = True
        _append_event(runtime_root, record["transaction_id"], record, {"kind": "interrupted_after_backup"}); _save_transaction(runtime_root, record); return False
    return True


def _effect_post_matches(target_root: Path, effect: Mapping[str, Any]) -> bool:
    path = _safe_target_path(target_root, str(effect.get("path") or ""))
    kind = str(effect.get("kind") or "")
    if kind == "remove": return not path.exists()
    return _verify_file(path, str(effect.get("candidate_sha256") or ""))


def _apply_remaining(runtime_root: str | Path | None, record: dict[str, Any], *, interrupt_at: str = "") -> bool:
    target_root = Path(record["target_root_path"]); candidate_root = Path(record["candidate_stage_root_path"])
    completed = set(str(x) for x in record.get("effects_completed") or [])
    index = 0
    for effect in record.get("effects", []):
        path = str(effect.get("path") or ""); kind = str(effect.get("kind") or "")
        if kind not in ALLOWED_MUTATION_KINDS: continue
        index += 1
        if path in completed:
            if not _effect_post_matches(target_root, effect): raise RuntimeError(f"completed_effect_changed:{path}")
            continue
        target = _safe_target_path(target_root, path, create_parents=kind in {"add", "replace"})
        pre_sha = str(effect.get("target_sha256") or "")
        if kind == "add":
            if target.exists(): raise RuntimeError(f"add_target_now_exists:{path}")
            source = _safe_target_path(candidate_root, path)
            if not _verify_file(source, str(effect.get("candidate_sha256") or "")): raise RuntimeError(f"candidate_file_changed:{path}")
            _atomic_copy(source, target, record["transaction_id"])
        elif kind == "replace":
            if not _verify_file(target, pre_sha): raise RuntimeError(f"replace_target_changed:{path}")
            source = _safe_target_path(candidate_root, path)
            if not _verify_file(source, str(effect.get("candidate_sha256") or "")): raise RuntimeError(f"candidate_file_changed:{path}")
            _atomic_copy(source, target, record["transaction_id"])
        else:
            if not _verify_file(target, pre_sha): raise RuntimeError(f"remove_target_changed:{path}")
            target.unlink()
        if not _effect_post_matches(target_root, effect): raise RuntimeError(f"effect_post_verification_failed:{path}")
        record.setdefault("effects_completed", []).append(path)
        _append_event(runtime_root, record["transaction_id"], record, {"kind": "effect_applied", "path": path, "action": kind, "before_sha256": pre_sha, "after_sha256": str(effect.get("candidate_sha256") or "")})
        inventory = _target_inventory(target_root); record["target_current_inventory_sha256"] = str(inventory.get("digest") or "")
        _save_transaction(runtime_root, record)
        if interrupt_at == f"after_effect:{index}":
            record["state"] = record["status"] = "interrupted"; record["owner_released"] = True
            _append_event(runtime_root, record["transaction_id"], record, {"kind": "interrupted_after_effect", "effect_index": index}); _save_transaction(runtime_root, record); return False
    if interrupt_at == "after_mutation_before_finalize":
        record["state"] = record["status"] = "interrupted"; record["owner_released"] = True
        _append_event(runtime_root, record["transaction_id"], record, {"kind": "interrupted_after_mutation_before_finalize"}); _save_transaction(runtime_root, record); return False
    return True


def _finalize_installation(runtime_root: str | Path | None, record: dict[str, Any]) -> dict[str, Any]:
    inventory = _target_inventory(Path(record["target_root_path"]))
    if not inventory.get("ok"):
        raise RuntimeError("target_inventory_failed_after_apply")
    record["target_current_inventory_sha256"] = str(inventory.get("digest") or "")
    receipt = {
        "schema": "eidolon-installed-state-receipt-v1", "transaction_id": record["transaction_id"],
        "transaction_identity_sha256": record["transaction_identity_sha256"], "candidate_id": record["candidate_id"],
        "packaged_version": record["packaged_version"], "archive_sha256": record["archive_sha256"],
        "source_manifest_sha256": record["source_manifest_sha256"], "archive_manifest_sha256": record["archive_manifest_sha256"],
        "target_project_id": record["target_project_id"], "target_inventory_sha256": record["target_current_inventory_sha256"],
        "effects_sha256": record["effects_sha256"], "installed_at": utc_now(), "state": "installed_unpromoted",
        "promoted": False, "certified": False, "content_free": True,
    }
    receipt["receipt_sha256"] = digest_payload(receipt)
    atomic_json(transaction_directory(runtime_root) / "installed_receipts" / f"{record['transaction_id']}.json", receipt)
    atomic_json(transaction_directory(runtime_root) / "active_installed_receipt.json", {
        "schema": "eidolon-installed-state-receipt-v1", "transaction_id": record["transaction_id"],
        "receipt_sha256": receipt["receipt_sha256"], "target_project_id": record["target_project_id"], "content_free": True,
    })
    record["installed_receipt_sha256"] = receipt["receipt_sha256"]
    record["state"] = record["status"] = "installed_unpromoted"; record["owner_released"] = True; record["completed_at"] = utc_now()
    _append_event(runtime_root, record["transaction_id"], record, {"kind": "transaction_finalized", "state": "installed_unpromoted", "receipt_sha256": receipt["receipt_sha256"]})
    _save_transaction(runtime_root, record)
    return record


def apply_authorized_installation(
    authorization_token: str, *, confirm: str, runtime_root: str | Path | None = None,
    _interrupt_at: str = "",
) -> dict[str, Any]:
    token = authorization_token if isinstance(authorization_token, str) else ""
    if not token or not isinstance(confirm, str) or confirm != INSTALLATION_APPLY_CONFIRMATION:
        return _public({"status": "literal_confirmation_required", "contradictions": [{"kind": "literal_confirmation_required"}]})
    if _used(runtime_root, token):
        return _public({"status": "authorization_reused", "contradictions": [{"kind": "authorization_reused"}]})
    auth = _authorization(runtime_root, token)
    if not auth or str(auth.get("authorization_binding_sha256") or "") != _authorization_binding(auth):
        return _public({"status": "authorization_missing_or_malformed", "contradictions": [{"kind": "authorization_missing_or_malformed"}]})
    parts = token.split(".")
    if len(parts) != 3 or parts != [str(auth.get("token_id") or ""), str(auth.get("authorization_binding_sha256") or ""), str(auth.get("nonce") or "")]:
        return _public({"status": "authorization_token_mismatch", "contradictions": [{"kind": "authorization_token_mismatch"}]})
    if str(auth.get("action") or "") != INSTALLATION_APPLY_ACTION:
        return _public({"status": "authorization_action_mismatch", "contradictions": [{"kind": "authorization_action_mismatch"}]})
    stage, plan, contradictions, details = _revalidate_before_apply(runtime_root, auth)
    if contradictions:
        return _public({"status": "authorization_stale_or_mismatched", "contradictions": contradictions})
    record = _create_record(runtime_root, auth, stage, plan, details)
    _mark_used(runtime_root, token, "transaction_started", record["transaction_id"])
    try:
        if not _backup_all(runtime_root, record, interrupt_at=_interrupt_at): return _public(record)
        if not _apply_remaining(runtime_root, record, interrupt_at=_interrupt_at): return _public(record)
        return _public(_finalize_installation(runtime_root, record))
    except Exception as exc:
        record["state"] = record["status"] = "uncertain" if record.get("effects_completed") else "interrupted"
        record["owner_released"] = True
        record.setdefault("contradictions", []).append({"kind": str(exc).split(":", 1)[0] or "installation_apply_failed"})
        _append_event(runtime_root, record["transaction_id"], record, {"kind": "transaction_failed", "failure_kind": str(exc).split(":", 1)[0]})
        try: _save_transaction(runtime_root, record)
        except Exception: pass
        return _public(record)


def active_transaction_private(runtime_root: str | Path | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    directory = transaction_directory(runtime_root)
    pointer = read_json(directory / "active_transaction.json")
    transaction_id = str(pointer.get("transaction_id") or "")
    return pointer, read_json(directory / "records" / f"{transaction_id}.json") if transaction_id else {}


def installation_transaction_status(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    pointer, record = active_transaction_private(runtime_root)
    if not record:
        return _public({})
    contradictions = list(record.get("contradictions") or [])
    if str(pointer.get("transaction_identity_sha256") or "") != str(record.get("transaction_identity_sha256") or ""):
        contradictions.append({"kind": "transaction_pointer_identity_mismatch"})
    if str(record.get("transaction_identity_sha256") or "") != _transaction_identity(record):
        contradictions.append({"kind": "transaction_identity_mismatch"})
    if str(record.get("transaction_state_sha256") or "") != _state_digest(record):
        contradictions.append({"kind": "transaction_state_mismatch"})
    if str(pointer.get("transaction_state_sha256") or "") != str(record.get("transaction_state_sha256") or ""):
        contradictions.append({"kind": "transaction_pointer_state_mismatch"})
    current = dict(record); current["contradictions"] = contradictions; current["ok"] = not contradictions
    if contradictions and current.get("state") not in {"rolled_back"}:
        current["status"] = "uncertain"
    return _public(current)
