from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from file_tools import safe_project_path
from memory import store_memory
from patch_suggester import (
    load_patch_proposal,
    save_patch_proposal,
    list_patch_proposals,
    patch_proposal_text,
    resolve_patch_id,
)
from paths import DATA_DIR


BACKUPS_DIR = DATA_DIR / "backups"
ACTION_LOG_FILE = DATA_DIR / "action_log.json"


@dataclass
class PatchApplyResult:
    ok: bool
    patch_id: str
    target_file: str = ""
    message: str = ""
    backup_path: str = ""
    error: str = ""
    dry_run: bool = False


@dataclass
class PatchRollbackResult:
    ok: bool
    patch_id: str
    target_file: str = ""
    message: str = ""
    backup_path: str = ""
    error: str = ""
    dry_run: bool = False


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()


def _ensure_storage() -> None:
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)

    if not ACTION_LOG_FILE.exists():
        with ACTION_LOG_FILE.open("w", encoding="utf-8") as file:
            json.dump([], file, indent=2)


def _load_action_log() -> list[dict[str, Any]]:
    _ensure_storage()

    try:
        with ACTION_LOG_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return []

    return data if isinstance(data, list) else []


def _save_action_log(log: list[dict[str, Any]]) -> None:
    _ensure_storage()

    with ACTION_LOG_FILE.open("w", encoding="utf-8") as file:
        json.dump(log, file, indent=2)


def _append_action_log(entry: dict[str, Any]) -> None:
    log = _load_action_log()
    log.append(entry)
    _save_action_log(log)


def _backup_file_path(patch_id: str, target_file: str) -> Path:
    """
    Stores backups under data/backups/<patch_id>/<target_file>.
    This preserves folder structure inside the backup folder.
    """
    normalized_target = target_file.replace("\\", "/").strip("/")
    return BACKUPS_DIR / patch_id / normalized_target


def _validate_patch_for_apply(proposal: dict[str, Any]) -> tuple[bool, str]:
    if not proposal:
        return False, "Patch proposal is empty or missing."

    if proposal.get("status") != "proposed":
        return False, f"Patch status is '{proposal.get('status')}', not 'proposed'."

    if not proposal.get("target_file"):
        return False, "Patch proposal has no target file."

    if "original_content" not in proposal:
        return False, "Patch proposal has no original content field."

    if not proposal.get("proposed_content"):
        return False, "Patch proposal has no proposed content."

    if proposal.get("original_content") == proposal.get("proposed_content"):
        return False, "Original and proposed content are identical."

    return True, ""


def _validate_patch_for_rollback(proposal: dict[str, Any]) -> tuple[bool, str]:
    if not proposal:
        return False, "Patch proposal is empty or missing."

    if proposal.get("status") != "applied":
        return False, f"Patch status is '{proposal.get('status')}', not 'applied'."

    if not proposal.get("target_file"):
        return False, "Patch proposal has no target file."

    if not proposal.get("backup_path"):
        return False, "Patch proposal has no backup path."

    return True, ""


def apply_patch(patch_id: str, dry_run: bool = False) -> PatchApplyResult:
    """
    Applies a saved patch proposal.

    Safety checks:
    - Patch must exist.
    - Patch must still be in proposed state.
    - Target file must be inside active project.
    - Target file must still match original content hash.
    - Backup is created before writing.
    """

    original_patch_id = patch_id
    patch_id = resolve_patch_id(patch_id, status="proposed") or patch_id

    proposal = load_patch_proposal(patch_id)

    if not proposal:
        return PatchApplyResult(
            ok=False,
            patch_id=patch_id,
            error=f"Patch proposal not found: {original_patch_id}",
            dry_run=dry_run,
        )

    target_file = proposal.get("target_file", "")

    valid, error = _validate_patch_for_apply(proposal)
    if not valid:
        return PatchApplyResult(
            ok=False,
            patch_id=patch_id,
            target_file=target_file,
            error=error,
            dry_run=dry_run,
        )

    try:
        target_path = safe_project_path(target_file)
    except PermissionError as error:
        return PatchApplyResult(
            ok=False,
            patch_id=patch_id,
            target_file=target_file,
            error=str(error),
            dry_run=dry_run,
        )

    if not target_path.exists():
        return PatchApplyResult(
            ok=False,
            patch_id=patch_id,
            target_file=target_file,
            error="Target file no longer exists.",
            dry_run=dry_run,
        )

    if not target_path.is_file():
        return PatchApplyResult(
            ok=False,
            patch_id=patch_id,
            target_file=target_file,
            error="Target path is not a file.",
            dry_run=dry_run,
        )

    try:
        current_content = target_path.read_text(encoding="utf-8")
    except OSError as error:
        return PatchApplyResult(
            ok=False,
            patch_id=patch_id,
            target_file=target_file,
            error=f"Could not read target file: {error}",
            dry_run=dry_run,
        )

    expected_hash = proposal.get("original_sha256", "")
    current_hash = _sha256(current_content)

    if expected_hash and current_hash != expected_hash:
        return PatchApplyResult(
            ok=False,
            patch_id=patch_id,
            target_file=target_file,
            error=(
                "Target file has changed since this patch was created. "
                "Regenerate the patch to avoid overwriting newer work."
            ),
            dry_run=dry_run,
        )

    proposed_content = proposal.get("proposed_content", "")

    if dry_run:
        return PatchApplyResult(
            ok=True,
            patch_id=patch_id,
            target_file=target_file,
            message="Dry run passed. Patch is safe to apply based on current checks.",
            dry_run=True,
        )

    _ensure_storage()

    backup_path = _backup_file_path(patch_id, target_file)
    backup_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        backup_path.write_text(current_content, encoding="utf-8")
    except OSError as error:
        return PatchApplyResult(
            ok=False,
            patch_id=patch_id,
            target_file=target_file,
            error=f"Could not create backup: {error}",
            dry_run=dry_run,
        )

    try:
        target_path.write_text(proposed_content, encoding="utf-8")
    except OSError as error:
        return PatchApplyResult(
            ok=False,
            patch_id=patch_id,
            target_file=target_file,
            backup_path=str(backup_path),
            error=f"Backup created, but failed to write target file: {error}",
            dry_run=dry_run,
        )

    applied_at = datetime.now().isoformat(timespec="seconds")

    proposal["status"] = "applied"
    proposal["applied_at"] = applied_at
    proposal["backup_path"] = str(backup_path)
    proposal["applied_sha256"] = _sha256(proposed_content)

    save_patch_proposal(proposal)

    _append_action_log({
        "timestamp": applied_at,
        "action": "apply_patch",
        "patch_id": patch_id,
        "target_file": target_file,
        "backup_path": str(backup_path),
        "status": "success",
    })

    store_memory({
        "type": "patch_apply_event",
        "content": f"Applied patch {patch_id} to '{target_file}'. Backup created at '{backup_path}'.",
        "source": "patch_applier",
        "patch_id": patch_id,
        "file": target_file,
        "backup_path": str(backup_path),
    })

    return PatchApplyResult(
        ok=True,
        patch_id=patch_id,
        target_file=target_file,
        message="Patch applied successfully.",
        backup_path=str(backup_path),
        dry_run=False,
    )


def rollback_patch(patch_id: str, dry_run: bool = False) -> PatchRollbackResult:
    """
    Restores an applied patch from its backup.

    Safety checks:
    - Patch must exist and be in applied state.
    - Backup file must exist.
    - Target file must be inside the active project folder.
    - Current target file must still match the content Eidolon applied.
      This blocks rollback from overwriting newer manual edits.
    """

    original_patch_id = patch_id
    patch_id = resolve_patch_id(patch_id, status="applied") or patch_id

    proposal = load_patch_proposal(patch_id)

    if not proposal:
        return PatchRollbackResult(
            ok=False,
            patch_id=patch_id,
            error=f"Patch proposal not found: {original_patch_id}",
            dry_run=dry_run,
        )

    target_file = proposal.get("target_file", "")

    valid, error = _validate_patch_for_rollback(proposal)
    if not valid:
        return PatchRollbackResult(
            ok=False,
            patch_id=patch_id,
            target_file=target_file,
            error=error,
            dry_run=dry_run,
        )

    try:
        target_path = safe_project_path(target_file)
    except PermissionError as error:
        return PatchRollbackResult(
            ok=False,
            patch_id=patch_id,
            target_file=target_file,
            error=str(error),
            dry_run=dry_run,
        )

    backup_path = Path(proposal.get("backup_path", ""))
    if not backup_path.is_absolute():
        backup_path = (DATA_DIR.parent / backup_path).resolve()

    if not backup_path.exists():
        return PatchRollbackResult(
            ok=False,
            patch_id=patch_id,
            target_file=target_file,
            backup_path=str(backup_path),
            error="Backup file does not exist. Cannot rollback safely.",
            dry_run=dry_run,
        )

    if not backup_path.is_file():
        return PatchRollbackResult(
            ok=False,
            patch_id=patch_id,
            target_file=target_file,
            backup_path=str(backup_path),
            error="Backup path is not a file.",
            dry_run=dry_run,
        )

    if not target_path.exists():
        return PatchRollbackResult(
            ok=False,
            patch_id=patch_id,
            target_file=target_file,
            backup_path=str(backup_path),
            error="Target file no longer exists. Manual restore may be required.",
            dry_run=dry_run,
        )

    try:
        current_content = target_path.read_text(encoding="utf-8")
        backup_content = backup_path.read_text(encoding="utf-8")
    except OSError as error:
        return PatchRollbackResult(
            ok=False,
            patch_id=patch_id,
            target_file=target_file,
            backup_path=str(backup_path),
            error=f"Could not read rollback files: {error}",
            dry_run=dry_run,
        )

    expected_applied_hash = proposal.get("applied_sha256") or proposal.get("proposed_sha256")
    current_hash = _sha256(current_content)

    if expected_applied_hash and current_hash != expected_applied_hash:
        return PatchRollbackResult(
            ok=False,
            patch_id=patch_id,
            target_file=target_file,
            backup_path=str(backup_path),
            error=(
                "Target file has changed since this patch was applied. "
                "Rollback blocked to avoid overwriting newer work. Restore manually if needed."
            ),
            dry_run=dry_run,
        )

    if dry_run:
        return PatchRollbackResult(
            ok=True,
            patch_id=patch_id,
            target_file=target_file,
            backup_path=str(backup_path),
            message="Dry run passed. Rollback is safe based on current checks.",
            dry_run=True,
        )

    try:
        target_path.write_text(backup_content, encoding="utf-8")
    except OSError as error:
        return PatchRollbackResult(
            ok=False,
            patch_id=patch_id,
            target_file=target_file,
            backup_path=str(backup_path),
            error=f"Could not restore backup to target file: {error}",
            dry_run=dry_run,
        )

    rolled_back_at = datetime.now().isoformat(timespec="seconds")

    proposal["status"] = "rolled_back"
    proposal["rolled_back_at"] = rolled_back_at
    proposal["rollback_sha256"] = _sha256(backup_content)

    save_patch_proposal(proposal)

    _append_action_log({
        "timestamp": rolled_back_at,
        "action": "rollback_patch",
        "patch_id": patch_id,
        "target_file": target_file,
        "backup_path": str(backup_path),
        "status": "success",
    })

    store_memory({
        "type": "patch_rollback_event",
        "content": f"Rolled back patch {patch_id} for '{target_file}' from backup '{backup_path}'.",
        "source": "patch_applier",
        "patch_id": patch_id,
        "file": target_file,
        "backup_path": str(backup_path),
    })

    return PatchRollbackResult(
        ok=True,
        patch_id=patch_id,
        target_file=target_file,
        backup_path=str(backup_path),
        message="Patch rolled back successfully.",
        dry_run=False,
    )


def applied_patches() -> list[dict[str, Any]]:
    return [
        proposal
        for proposal in list_patch_proposals()
        if proposal.get("status") == "applied"
    ]


def rolled_back_patches() -> list[dict[str, Any]]:
    return [
        proposal
        for proposal in list_patch_proposals()
        if proposal.get("status") == "rolled_back"
    ]


def print_apply_patch(patch_id: str, dry_run: bool = False) -> None:
    requested_patch_id = patch_id
    patch_id = resolve_patch_id(patch_id, status="proposed") or patch_id
    proposal = load_patch_proposal(patch_id)

    if not proposal:
        print(f"Patch proposal not found: {requested_patch_id}")
        return

    print(patch_proposal_text(proposal, include_full_content=False))
    print()

    result = apply_patch(patch_id, dry_run=dry_run)

    if not result.ok:
        print("Patch was not applied.")
        print(f"Reason: {result.error}")
        return

    if result.dry_run:
        print("Dry run passed.")
        print("No files were changed.")
        print(f"Target file: {result.target_file}")
        print("Apply when ready: python conscious_agent/main.py --apply-patch latest")
        return

    print(result.message)
    print(f"Target file: {result.target_file}")
    print(f"Backup path: {result.backup_path}")
    print("Patch status updated to: applied")
    print("Next suggested step: python conscious_agent/main.py --run-test-workflow latest --auto-review")


def print_rollback_patch(patch_id: str, dry_run: bool = False) -> None:
    requested_patch_id = patch_id
    patch_id = resolve_patch_id(patch_id, status="applied") or patch_id
    proposal = load_patch_proposal(patch_id)

    if not proposal:
        print(f"Patch proposal not found: {requested_patch_id}")
        return

    print(patch_proposal_text(proposal, include_full_content=False))
    print()

    result = rollback_patch(patch_id, dry_run=dry_run)

    if not result.ok:
        print("Patch was not rolled back.")
        print(f"Reason: {result.error}")
        return

    if result.dry_run:
        print("Rollback dry run passed.")
        print("No files were changed.")
        print(f"Target file: {result.target_file}")
        print(f"Backup path: {result.backup_path}")
        print("Rollback when ready: python conscious_agent/main.py --rollback-patch latest")
        return

    print(result.message)
    print(f"Target file: {result.target_file}")
    print(f"Restored from backup: {result.backup_path}")
    print("Patch status updated to: rolled_back")


def print_applied_patches() -> None:
    patches = applied_patches()

    if not patches:
        print("No applied patches found.")
        return

    for patch in patches:
        print(
            f"{patch.get('id')} | "
            f"applied_at={patch.get('applied_at')} | "
            f"risk={patch.get('risk_level')} | "
            f"{patch.get('target_file')}"
        )
        print(f"  Backup: {patch.get('backup_path')}")
        print(f"  Request: {patch.get('request')}")


def print_rolled_back_patches() -> None:
    patches = rolled_back_patches()

    if not patches:
        print("No rolled-back patches found.")
        return

    for patch in patches:
        print(
            f"{patch.get('id')} | "
            f"rolled_back_at={patch.get('rolled_back_at')} | "
            f"risk={patch.get('risk_level')} | "
            f"{patch.get('target_file')}"
        )
        print(f"  Backup: {patch.get('backup_path')}")
        print(f"  Request: {patch.get('request')}")
