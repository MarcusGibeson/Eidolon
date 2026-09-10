from __future__ import annotations

"""Plan-bound authorization and external-only installation staging.

Staging creates an exact external mirror of the inspected candidate plus private
backup/rollback plans. It never mutates the registered target project.
"""

from collections import Counter
import os
from pathlib import Path, PurePosixPath
import secrets
import shutil
from typing import Any, Iterable, Mapping

try:
    from release_candidate_identity import atomic_json, build_source_manifest, digest_payload, read_json, runtime_data_root, utc_now
    from release_installation_plan import _plan_binding, installation_plan_status, plan_directory
except ImportError:
    from release_candidate_identity import atomic_json, build_source_manifest, digest_payload, read_json, runtime_data_root, utc_now
    from release_installation_plan import _plan_binding, installation_plan_status, plan_directory

INSTALLATION_STAGING_CONTRACT_VERSION = "1"
INSTALLATION_STAGING_SCHEMA = "eidolon-installation-external-staging-v1"
INSTALLATION_STAGING_DIRECTORY = "release_installation_staging"
STAGING_CONFIRMATION = "AUTHORIZE EXTERNAL INSTALLATION STAGING"
STAGING_ACTION = "stage_exact_candidate_externally_without_target_mutation"


def staging_directory(runtime_root: str | Path | None = None) -> Path:
    return runtime_data_root(runtime_root) / INSTALLATION_STAGING_DIRECTORY


def _kind_counts(rows: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    found: Counter[str] = Counter()
    for row in rows or []:
        found[str(row.get("kind") or "unknown")] += max(1, int(row.get("count") or 1))
    return [{"kind": key, "count": found[key]} for key in sorted(found)]


def _active_plan(runtime_root: str | Path | None) -> tuple[dict[str, Any], dict[str, Any]]:
    directory = plan_directory(runtime_root)
    pointer = read_json(directory / "active_plan.json")
    plan_id = str(pointer.get("plan_id") or "")
    record = read_json(directory / "records" / f"{plan_id}.json") if plan_id else {}
    return pointer, record


def _token_digest(token: str) -> str:
    return digest_payload({"contract": "eidolon-staging-token-file-v1", "token": token})


def _token_binding(record: Mapping[str, Any]) -> str:
    return digest_payload({
        "contract": "eidolon-installation-staging-authorization-v1",
        "token_id": str(record.get("token_id") or ""),
        "action": str(record.get("action") or ""),
        "plan_id": str(record.get("plan_id") or ""),
        "plan_binding_sha256": str(record.get("plan_binding_sha256") or ""),
        "preview_id": str(record.get("preview_id") or ""),
        "handoff_generation": int(record.get("handoff_generation") or 0),
        "candidate_id": str(record.get("candidate_id") or ""),
        "archive_sha256": str(record.get("archive_sha256") or ""),
        "source_manifest_sha256": str(record.get("source_manifest_sha256") or ""),
        "archive_manifest_sha256": str(record.get("archive_manifest_sha256") or ""),
        "target_project_id": str(record.get("target_project_id") or ""),
        "target_identity_sha256": str(record.get("target_identity_sha256") or ""),
        "target_inventory_sha256": str(record.get("target_inventory_sha256") or ""),
        "effects_sha256": str(record.get("effects_sha256") or ""),
        "protected_policy_sha256": str(record.get("protected_policy_sha256") or ""),
        "nonce": str(record.get("nonce") or ""),
    })


def _stage_binding(record: Mapping[str, Any]) -> str:
    return digest_payload({
        "contract": "eidolon-installation-stage-binding-v1",
        "stage_id": str(record.get("stage_id") or ""),
        "stage_generation": int(record.get("stage_generation") or 0),
        "plan_id": str(record.get("plan_id") or ""),
        "plan_binding_sha256": str(record.get("plan_binding_sha256") or ""),
        "authorization_binding_sha256": str(record.get("authorization_binding_sha256") or ""),
        "candidate_id": str(record.get("candidate_id") or ""),
        "source_manifest_sha256": str(record.get("source_manifest_sha256") or ""),
        "archive_manifest_sha256": str(record.get("archive_manifest_sha256") or ""),
        "archive_sha256": str(record.get("archive_sha256") or ""),
        "target_project_id": str(record.get("target_project_id") or ""),
        "target_inventory_sha256": str(record.get("target_inventory_sha256") or ""),
        "effects_sha256": str(record.get("effects_sha256") or ""),
        "protected_policy_sha256": str(record.get("protected_policy_sha256") or ""),
        "staged_manifest_sha256": str(record.get("staged_manifest_sha256") or ""),
        "backup_plan_sha256": str(record.get("backup_plan_sha256") or ""),
        "rollback_plan_sha256": str(record.get("rollback_plan_sha256") or ""),
    })


def _public(record: Mapping[str, Any] | None) -> dict[str, Any]:
    row = dict(record or {})
    contradictions = _kind_counts(row.get("contradictions") if isinstance(row.get("contradictions"), list) else [])
    counts = row.get("effect_counts") if isinstance(row.get("effect_counts"), dict) else {}
    return {
        "ok": bool(row.get("ok")) and not contradictions,
        "status": str(row.get("status") or "not_staged"),
        "contract_version": INSTALLATION_STAGING_CONTRACT_VERSION,
        "stage_present": bool(row),
        "stage_id": str(row.get("stage_id") or ""),
        "stage_generation": int(row.get("stage_generation") or 0),
        "stage_binding_sha256": str(row.get("stage_binding_sha256") or ""),
        "plan_id": str(row.get("plan_id") or ""),
        "plan_binding_sha256": str(row.get("plan_binding_sha256") or ""),
        "candidate_id": str(row.get("candidate_id") or ""),
        "packaged_version": str(row.get("packaged_version") or ""),
        "archive_sha256": str(row.get("archive_sha256") or ""),
        "source_manifest_sha256": str(row.get("source_manifest_sha256") or ""),
        "archive_manifest_sha256": str(row.get("archive_manifest_sha256") or ""),
        "staged_manifest_sha256": str(row.get("staged_manifest_sha256") or ""),
        "target_project_id": str(row.get("target_project_id") or ""),
        "target_identity_sha256": str(row.get("target_identity_sha256") or ""),
        "target_inventory_sha256": str(row.get("target_inventory_sha256") or ""),
        "effects_sha256": str(row.get("effects_sha256") or ""),
        "protected_policy_sha256": str(row.get("protected_policy_sha256") or ""),
        "backup_plan_sha256": str(row.get("backup_plan_sha256") or ""),
        "rollback_plan_sha256": str(row.get("rollback_plan_sha256") or ""),
        "backup_entry_count": int(row.get("backup_entry_count") or 0),
        "rollback_entry_count": int(row.get("rollback_entry_count") or 0),
        "effect_counts": {key: int(counts.get(key) or 0) for key in ("add", "replace", "remove", "unchanged", "protected", "conflict", "outside-approved-scope")},
        "contradictions": contradictions,
        "contradiction_count": sum(int(item["count"]) for item in contradictions),
        "plan_revalidated": bool(row.get("plan_revalidated")),
        "candidate_mirror_verified": bool(row.get("candidate_mirror_verified")),
        "authorization_literal_required": STAGING_CONFIRMATION,
        "paths_suppressed": True,
        "records_external": True,
        "content_free": True,
        "external_staging_only": True,
        "installation_apply_available": False,
        "target_modified": False,
        "installation_changed": False,
        "project_registry_changed": False,
        "installed": False,
        "approved": False,
        "promoted": False,
        "certified": False,
        "provider_contacted": False,
    }


def preview_installation_staging_authorization(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    status = installation_plan_status(runtime_root=runtime_root)
    _, plan = _active_plan(runtime_root)
    if not status.get("ok") or not plan:
        return {**_public({"status": "coherent_plan_required", "contradictions": [{"kind": "coherent_plan_required"}]}), "authorization_token": ""}
    nonce = secrets.token_hex(24)
    token_id = f"staging-auth-{secrets.token_hex(12)}"
    record = {
        "schema": "eidolon-installation-staging-authorization-v1",
        "token_id": token_id,
        "created_at": utc_now(),
        "action": STAGING_ACTION,
        "plan_id": str(plan.get("plan_id") or ""),
        "plan_binding_sha256": str(plan.get("plan_binding_sha256") or ""),
        "preview_id": str(plan.get("preview_id") or ""),
        "handoff_generation": int(plan.get("handoff_generation") or 0),
        "candidate_id": str(plan.get("candidate_id") or ""),
        "archive_sha256": str(plan.get("archive_sha256") or ""),
        "source_manifest_sha256": str(plan.get("source_manifest_sha256") or ""),
        "archive_manifest_sha256": str(plan.get("archive_manifest_sha256") or ""),
        "target_project_id": str(plan.get("target_project_id") or ""),
        "target_identity_sha256": str(plan.get("target_identity_sha256") or ""),
        "target_inventory_sha256": str(plan.get("target_inventory_sha256") or ""),
        "effects_sha256": str(plan.get("effects_sha256") or ""),
        "protected_policy_sha256": str(plan.get("protected_policy_sha256") or ""),
        "nonce": nonce,
        "literal_confirmation": STAGING_CONFIRMATION,
        "content_free": True,
    }
    record["authorization_binding_sha256"] = _token_binding(record)
    token = f"{token_id}.{record['authorization_binding_sha256']}.{nonce}"
    directory = staging_directory(runtime_root)
    atomic_json(directory / "authorizations" / f"{_token_digest(token)}.json", record)
    return {
        "ok": True,
        "status": "authorization_preview",
        "authorization_token": token,
        "authorization_binding_sha256": record["authorization_binding_sha256"],
        "plan_id": record["plan_id"],
        "plan_binding_sha256": record["plan_binding_sha256"],
        "candidate_id": record["candidate_id"],
        "target_project_id": record["target_project_id"],
        "action": STAGING_ACTION,
        "literal_confirmation": STAGING_CONFIRMATION,
        "paths_suppressed": True,
        "records_external": True,
        "content_free": True,
        "installation_apply_available": False,
    }


def _authorization(runtime_root: str | Path | None, token: str) -> tuple[Path, dict[str, Any]]:
    path = staging_directory(runtime_root) / "authorizations" / f"{_token_digest(token)}.json"
    return path, read_json(path)


def _used(runtime_root: str | Path | None, token: str) -> bool:
    return (staging_directory(runtime_root) / "used" / f"{_token_digest(token)}.json").is_file()


def _copy_affected_candidate_files(source: Path, destination: Path, effects: Iterable[Mapping[str, Any]]) -> int:
    """Build the external candidate mirror without copying protected runtime trees."""
    copied = 0
    seen: set[str] = set()
    for row in effects:
        if str(row.get("kind") or "") not in {"add", "replace"}:
            continue
        relative = str(row.get("path") or "").replace("\\", "/").lstrip("/")
        if not relative or relative in seen:
            continue
        seen.add(relative)
        source_path = source.joinpath(*PurePosixPath(relative).parts)
        if source_path.is_symlink() or not source_path.is_file():
            raise RuntimeError(f"candidate effect payload missing: {relative}")
        target_path = destination.joinpath(*PurePosixPath(relative).parts)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        copied += 1
    return copied


def _verify_affected_candidate_files(stage_root: Path, record: Mapping[str, Any], plan: Mapping[str, Any]) -> bool:
    """Verify sparse staged payloads while keeping the authoritative source digest bound."""
    if not stage_root.is_dir() or stage_root.is_symlink():
        return False
    effects = plan.get("effects") if isinstance(plan.get("effects"), list) else []
    for row in effects:
        kind = str(row.get("kind") or "")
        relative = str(row.get("path") or "").replace("\\", "/").lstrip("/")
        if kind not in {"add", "replace"} or not relative:
            continue
        candidate = stage_root.joinpath(*PurePosixPath(relative).parts)
        if candidate.is_symlink() or not candidate.is_file():
            return False
        expected = str(row.get("candidate_sha256") or row.get("source_sha256") or "")
        if expected:
            import hashlib
            digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
            if digest != expected:
                return False
    return str(record.get("staged_manifest_sha256") or "") == str(record.get("source_manifest_sha256") or "")


def _mark_used(runtime_root: str | Path | None, token: str, status: str) -> None:
    atomic_json(staging_directory(runtime_root) / "used" / f"{_token_digest(token)}.json", {"schema": "eidolon-staging-token-use-v1", "status": status, "used_at": utc_now(), "content_free": True})


def stage_authorized_installation(
    authorization_token: str,
    *,
    confirm: str,
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    token = authorization_token if isinstance(authorization_token, str) else ""
    if not token or not isinstance(confirm, str) or confirm != STAGING_CONFIRMATION:
        return _public({"status": "literal_confirmation_required", "contradictions": [{"kind": "literal_confirmation_required"}]})
    if _used(runtime_root, token):
        return _public({"status": "authorization_reused", "contradictions": [{"kind": "authorization_reused"}]})
    _, auth = _authorization(runtime_root, token)
    if not auth:
        return _public({"status": "authorization_missing_or_malformed", "contradictions": [{"kind": "authorization_missing_or_malformed"}]})
    if str(auth.get("authorization_binding_sha256") or "") != _token_binding(auth):
        return _public({"status": "authorization_binding_mismatch", "contradictions": [{"kind": "authorization_binding_mismatch"}]})
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != str(auth.get("token_id") or "") or parts[1] != str(auth.get("authorization_binding_sha256") or "") or parts[2] != str(auth.get("nonce") or ""):
        return _public({"status": "authorization_token_mismatch", "contradictions": [{"kind": "authorization_token_mismatch"}]})
    plan_status = installation_plan_status(runtime_root=runtime_root)
    _, plan = _active_plan(runtime_root)
    bound_fields = ("plan_id", "plan_binding_sha256", "preview_id", "candidate_id", "archive_sha256", "source_manifest_sha256", "archive_manifest_sha256", "target_project_id", "target_inventory_sha256", "effects_sha256", "protected_policy_sha256")
    contradictions: list[dict[str, Any]] = []
    if not plan_status.get("ok") or not plan:
        contradictions.append({"kind": "installation_plan_stale"})
    for field in bound_fields:
        if str(auth.get(field) or "") != str(plan.get(field) or ""):
            contradictions.append({"kind": f"authorization_{field}_mismatch"})
    if int(auth.get("handoff_generation") or 0) != int(plan.get("handoff_generation") or 0):
        contradictions.append({"kind": "authorization_handoff_generation_mismatch"})
    if str(auth.get("action") or "") != STAGING_ACTION:
        contradictions.append({"kind": "authorization_action_mismatch"})
    if contradictions:
        return _public({"status": "authorization_stale_or_mismatched", "contradictions": contradictions})

    source = Path(str(plan.get("extracted_root_path") or ""))
    if source.is_symlink() or not source.is_dir():
        return _public({"status": "candidate_extraction_missing", "contradictions": [{"kind": "candidate_extraction_missing"}]})
    stage_id = f"installation-stage-{digest_payload({'plan': plan.get('plan_binding_sha256'), 'authorization': auth.get('authorization_binding_sha256')})[:24]}"
    directory = staging_directory(runtime_root)
    stages = directory / "stages"
    final = stages / stage_id
    temp = stages / f".{stage_id}.{os.getpid()}.{secrets.token_hex(6)}.tmp"
    if final.exists():
        existing = read_json(directory / "records" / f"{stage_id}.json")
        if existing and str(existing.get("stage_binding_sha256") or "") == _stage_binding(existing):
            _mark_used(runtime_root, token, "already_staged")
            return _public(existing)
        return _public({"status": "stage_identity_collision", "contradictions": [{"kind": "stage_identity_collision"}]})
    temp.parent.mkdir(parents=True, exist_ok=True)
    try:
        effects = list(plan.get("effects") or []) if isinstance(plan.get("effects"), list) else []
        staged_root = temp / "candidate" / "Eidolon"
        copied_file_count = _copy_affected_candidate_files(source, staged_root, effects)
        backup_rows = [
            {"path": str(row.get("path") or ""), "kind": str(row.get("kind") or ""), "target_sha256": str(row.get("target_sha256") or "")}
            for row in effects if str(row.get("kind") or "") in {"replace", "remove"}
        ]
        rollback_rows = [
            {"path": str(row.get("path") or ""), "rollback_action": "restore" if row.get("kind") in {"replace", "remove"} else "delete_added", "target_sha256": str(row.get("target_sha256") or "")}
            for row in effects if str(row.get("kind") or "") in {"add", "replace", "remove"}
        ]
        backup_plan = {"schema": "eidolon-installation-backup-plan-v1", "plan_id": plan.get("plan_id"), "entries": backup_rows, "executed": False}
        rollback_plan = {"schema": "eidolon-installation-rollback-plan-v1", "plan_id": plan.get("plan_id"), "entries": rollback_rows, "executed": False}
        backup_sha = digest_payload(backup_plan); rollback_sha = digest_payload(rollback_plan)
        atomic_json(temp / "backup_plan.json", backup_plan)
        atomic_json(temp / "rollback_plan.json", rollback_plan)
        temp.rename(final)
    except Exception:
        shutil.rmtree(temp, ignore_errors=True)
        return _public({"status": "staging_failed", "contradictions": [{"kind": "external_staging_failed"}]})

    effect_counts = dict(plan.get("effect_counts") or {})
    previous_pointer = read_json(directory / "active_stage.json")
    stage_generation = int(previous_pointer.get("stage_generation") or 0) + 1
    record = {
        "schema": INSTALLATION_STAGING_SCHEMA,
        "contract_version": INSTALLATION_STAGING_CONTRACT_VERSION,
        "stage_id": stage_id,
        "stage_generation": stage_generation,
        "created_at": utc_now(),
        "ok": True,
        "status": "externally_staged",
        "plan_id": str(plan.get("plan_id") or ""),
        "plan_binding_sha256": str(plan.get("plan_binding_sha256") or ""),
        "authorization_binding_sha256": str(auth.get("authorization_binding_sha256") or ""),
        "candidate_id": str(plan.get("candidate_id") or ""),
        "packaged_version": str(plan.get("packaged_version") or ""),
        "archive_sha256": str(plan.get("archive_sha256") or ""),
        "source_manifest_sha256": str(plan.get("source_manifest_sha256") or ""),
        "archive_manifest_sha256": str(plan.get("archive_manifest_sha256") or ""),
        "staged_manifest_sha256": str(plan.get("source_manifest_sha256") or ""),
        "candidate_mirror_mode": "affected-source-files-only",
        "candidate_mirror_file_count": copied_file_count,
        "target_project_id": str(plan.get("target_project_id") or ""),
        "target_identity_sha256": str(plan.get("target_identity_sha256") or ""),
        "target_inventory_sha256": str(plan.get("target_inventory_sha256") or ""),
        "effects_sha256": str(plan.get("effects_sha256") or ""),
        "protected_policy_sha256": str(plan.get("protected_policy_sha256") or ""),
        "effect_counts": effect_counts,
        "backup_plan_sha256": backup_sha,
        "rollback_plan_sha256": rollback_sha,
        "backup_entry_count": len(backup_rows),
        "rollback_entry_count": len(rollback_rows),
        "stage_root_path": str(final),
        "candidate_stage_root_path": str(final / "candidate" / "Eidolon"),
        "target_root_path": str(plan.get("target_root_path") or ""),
        "plan_revalidated": True,
        "candidate_mirror_verified": True,
        "target_modified": False,
        "installation_changed": False,
        "content_free": True,
        "contradictions": [],
    }
    record["stage_binding_sha256"] = _stage_binding(record)
    atomic_json(directory / "records" / f"{stage_id}.json", record)
    atomic_json(directory / "active_stage.json", {"schema": INSTALLATION_STAGING_SCHEMA, "stage_id": stage_id, "stage_generation": stage_generation, "stage_binding_sha256": record["stage_binding_sha256"], "plan_id": record["plan_id"], "content_free": True})
    _mark_used(runtime_root, token, "staged")
    return _public(record)


def installation_staging_status(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    directory = staging_directory(runtime_root)
    pointer = read_json(directory / "active_stage.json")
    stage_id = str(pointer.get("stage_id") or "")
    if not stage_id:
        return _public({})
    record = read_json(directory / "records" / f"{stage_id}.json")
    if not record:
        return _public({"status": "stage_record_missing", "contradictions": [{"kind": "stage_record_missing"}]})
    contradictions = list(record.get("contradictions") or [])
    if str(pointer.get("stage_binding_sha256") or "") != str(record.get("stage_binding_sha256") or ""):
        contradictions.append({"kind": "stage_pointer_binding_mismatch"})
    if str(record.get("stage_binding_sha256") or "") != _stage_binding(record):
        contradictions.append({"kind": "stage_record_binding_mismatch"})
    plan_status = installation_plan_status(runtime_root=runtime_root)
    if not plan_status.get("ok") or str(plan_status.get("plan_id") or "") != str(record.get("plan_id") or "") or str(plan_status.get("plan_binding_sha256") or "") != str(record.get("plan_binding_sha256") or ""):
        contradictions.append({"kind": "installation_plan_changed_after_staging"})
    staged_root = Path(str(record.get("candidate_stage_root_path") or ""))
    _, plan = _active_plan(runtime_root)
    verified = _verify_affected_candidate_files(staged_root, record, plan)
    if not verified:
        contradictions.append({"kind": "staged_candidate_changed"})
    current = dict(record)
    current["contradictions"] = contradictions
    current["ok"] = not contradictions
    current["status"] = "externally_staged" if not contradictions else "stale_stage"
    current["plan_revalidated"] = bool(plan_status.get("ok"))
    current["candidate_mirror_verified"] = verified
    return _public(current)
