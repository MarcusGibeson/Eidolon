from __future__ import annotations

"""v1204.0-v1204.2 selected-project apply foundations.

A retained, fully bound implementation checkpoint may prepare one digest-only apply
packet. A second exact operator authorization is consumed once and bound to that
packet. Only then may validated workspace changes be applied transactionally to the
selected project, with an external rollback manifest prepared first.
"""

import base64
import hashlib
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Mapping

from ordinary_chat_development_campaign import (
    _atomic_json, _digest, _proposal_lock, _proposal_path, _read_json, _store_root, _validate,
)
from grounded_development_planning import load_grounded_plan
from isolated_implementation_workspace import (
    _record_path as _workspace_record_path, _verify_record as _verify_workspace_record, _workspace_root,
)
from structured_development_generation import _safe_relative

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1204.8"
MAX_APPLY_FILES = 64
MAX_APPLY_BYTES = 2 * 1024 * 1024


def _request_path(pid: str, rev: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "selected_project_apply_requests" / pid / f"revision-{int(rev)}.json"


def _authorization_path(pid: str, rev: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "selected_project_apply_authorizations" / pid / f"revision-{int(rev)}.json"


def _result_path(pid: str, rev: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "selected_project_apply_results" / pid / f"revision-{int(rev)}.json"


def _rollback_path(pid: str, rev: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "selected_project_rollback_manifests" / pid / f"revision-{int(rev)}.json"


def _apply_journal_path(pid: str, rev: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "selected_project_apply_journals" / pid / f"revision-{int(rev)}.json"


def _rollback_journal_path(pid: str, rev: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "selected_project_rollback_journals" / pid / f"revision-{int(rev)}.json"


def _write_journal(path: Path, **fields: Any) -> dict[str, Any]:
    record = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        **fields,
    }
    record["journal_digest"] = _digest(record)
    _atomic_json(path, record)
    return record


def _valid_journal(record: Mapping[str, Any]) -> bool:
    return bool(record and _bound(record, "journal_digest"))


def _validate_manifest(manifest: Mapping[str, Any], *, expected_apply_request_digest: str = "") -> bool:
    if not manifest or not _bound(manifest, "rollback_manifest_digest"):
        return False
    if expected_apply_request_digest and manifest.get("apply_request_digest") != expected_apply_request_digest:
        return False
    entries = list(manifest.get("entries") or [])
    if len(entries) != int(manifest.get("entry_count") or -1) or len(entries) > MAX_APPLY_FILES:
        return False
    seen: set[str] = set()
    total = 0
    try:
        for entry in entries:
            rel = _safe_relative(str(entry.get("relative_path") or ""))
            folded = rel.casefold()
            if folded in seen:
                return False
            seen.add(folded)
            if entry.get("relative_path_digest") != hashlib.sha256(rel.encode()).hexdigest():
                return False
            if entry.get("existed"):
                content = base64.b64decode(str(entry.get("content_b64") or ""), validate=True)
                total += len(content)
                if hashlib.sha256(content).hexdigest() != entry.get("content_digest"):
                    return False
            elif entry.get("content_b64") or entry.get("content_digest"):
                return False
    except Exception:
        return False
    return total <= MAX_APPLY_BYTES


def _path_state(target: Path, *, original: Mapping[str, Any], generated: Mapping[str, Any]) -> str:
    original_exists = bool(original.get("existed"))
    original_digest = str(original.get("content_digest") or "")
    operation = str(generated.get("operation") or "")
    generated_exists = operation != "delete"
    generated_digest = str(generated.get("content_digest") or "")
    if target.is_symlink():
        return "conflict"
    exists = target.is_file()
    digest = _file_digest(target) if exists else ""
    if exists == generated_exists and (not exists or digest == generated_digest):
        return "generated"
    if exists == original_exists and (not exists or digest == original_digest):
        return "original"
    return "conflict"


def _project_scope_state(root: Path, generation: Mapping[str, Any], manifest: Mapping[str, Any]) -> str:
    generated = {str(row.get("relative_path") or ""): row for row in generation.get("files") or []}
    originals = {str(row.get("relative_path") or ""): row for row in manifest.get("entries") or []}
    if set(generated) != set(originals):
        return "conflict"
    states = []
    for rel in sorted(generated):
        safe = _safe_relative(rel)
        states.append(_path_state(root / safe, original=originals[rel], generated=generated[rel]))
    if any(state == "conflict" for state in states):
        return "conflict"
    if states and all(state == "generated" for state in states):
        return "generated"
    if states and all(state == "original" for state in states):
        return "original"
    return "mixed_known"


def _bound(record: Mapping[str, Any], digest_key: str) -> bool:
    supplied = str(record.get(digest_key) or "")
    return bool(supplied and supplied == _digest({k: v for k, v in record.items() if k != digest_key}))


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_final_checkpoint(pid: str, rev: int, runtime_root=None) -> dict[str, Any]:
    # Import lazily so the apply layer supports both completed tool families.
    for module_name, loader_name in (
        ("python_cli_implementation_checkpoint", "load_python_cli_implementation_checkpoint"),
        ("javascript_tool_implementation_checkpoint", "load_javascript_tool_implementation_checkpoint"),
    ):
        try:
            module = __import__(module_name, fromlist=[loader_name])
            record = getattr(module, loader_name)(pid, rev, runtime_root)
        except Exception:
            record = {}
        if record:
            return record
    return {}


def _verify_selected_snapshot(proposal: Mapping[str, Any], plan: Mapping[str, Any]) -> tuple[bool, str, Path | None]:
    target = dict(proposal.get("target") or {})
    if target.get("mode") != "selected_project":
        return False, "selected_project_required", None
    try:
        root = Path(str(target.get("private_path") or "")).expanduser().resolve(strict=True)
    except (OSError, RuntimeError):
        return False, "selected_project_unavailable", None
    if not root.is_dir() or root.is_symlink():
        return False, "selected_project_unavailable", None
    inventory = list(plan.get("inventory") or [])
    expected = {str(row.get("relative_path") or ""): row for row in inventory}
    actual: dict[str, tuple[int, str]] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            return False, "selected_project_symlink_rejected", None
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel not in expected:
            return False, "selected_project_snapshot_changed", None
        actual[rel] = (path.stat().st_size, _file_digest(path))
    if set(actual) != set(expected):
        return False, "selected_project_snapshot_changed", None
    for rel, row in expected.items():
        size, digest = actual[rel]
        if size != int(row.get("size_bytes") or 0) or digest != row.get("content_digest"):
            return False, "selected_project_snapshot_changed", None
    return True, "ok", root


def create_or_resume_apply_request(
    proposal_id: str, *, expected_revision: int, expected_revision_digest: str,
    expected_implementation_checkpoint_digest: str, runtime_root=None,
) -> dict[str, Any]:
    with _proposal_lock(proposal_id, runtime_root):
        existing = _read_json(_request_path(proposal_id, expected_revision, runtime_root))
        if existing:
            if not _bound(existing, "apply_request_digest"):
                return {"ok": False, "status": "apply_request_invalid"}
            bindings = {
                "proposal_revision_digest": expected_revision_digest,
                "implementation_checkpoint_digest": expected_implementation_checkpoint_digest,
            }
            if any(existing.get(k) != v for k, v in bindings.items()):
                return {"ok": False, "status": "stale_apply_request"}
            return {**existing, "operation_status": "resumed"}

        proposal = _read_json(_proposal_path(proposal_id, runtime_root))
        if not proposal or not _validate(proposal):
            return {"ok": False, "status": "proposal_missing_or_tampered"}
        if int(proposal.get("revision") or 0) != int(expected_revision) or proposal.get("revision_digest") != expected_revision_digest:
            return {"ok": False, "status": "stale_proposal_revision"}
        final = _load_final_checkpoint(proposal_id, expected_revision, runtime_root)
        if not final or final.get("implementation_checkpoint_digest") != expected_implementation_checkpoint_digest:
            return {"ok": False, "status": "implementation_checkpoint_missing_or_stale"}
        if final.get("disposition_action") != "retain" or final.get("workspace_retained") is not True:
            return {"ok": False, "status": "retained_result_required"}
        plan = load_grounded_plan(proposal_id, expected_revision, runtime_root=runtime_root)
        if not plan or plan.get("proposal_revision_digest") != expected_revision_digest:
            return {"ok": False, "status": "grounded_plan_missing_or_stale"}
        ok, status, root = _verify_selected_snapshot(proposal, plan)
        if not ok:
            return {"ok": False, "status": status}
        generation_digest = str(final.get("generation_digest") or "")
        workspace_record = _read_json(_workspace_record_path(proposal_id, expected_revision, runtime_root))
        workspace_root = _workspace_root(proposal_id, expected_revision, generation_digest, runtime_root)
        if not workspace_record or not _verify_workspace_record(workspace_record, workspace_root):
            return {"ok": False, "status": "retained_workspace_missing_or_invalid"}
        if workspace_record.get("workspace_digest") != final.get("workspace_digest"):
            return {"ok": False, "status": "stale_workspace_revision"}

        generation = _read_json(_store_root(runtime_root) / "generation" / proposal_id / f"revision-{int(expected_revision)}.json")
        if not generation or generation.get("generation_digest") != generation_digest:
            return {"ok": False, "status": "generation_record_missing_or_stale"}
        operations = []
        total = 0
        for row in generation.get("files") or []:
            rel = _safe_relative(str(row.get("relative_path") or ""))
            op = str(row.get("operation") or "")
            size = int(row.get("size_bytes") or len(str(row.get("content") or "").encode("utf-8")))
            total += size
            operations.append({
                "relative_path": rel,
                "relative_path_digest": hashlib.sha256(rel.encode()).hexdigest(),
                "operation": op,
                "content_digest": str(row.get("content_digest") or ""),
                "size_bytes": size,
            })
        if not operations or len(operations) > MAX_APPLY_FILES or total > MAX_APPLY_BYTES:
            return {"ok": False, "status": "apply_budget_exceeded"}
        record = {
            "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION,
            "ok": True, "status": "selected_project_apply_awaiting_exact_authorization",
            "proposal_id": proposal_id, "proposal_revision": int(expected_revision),
            "proposal_revision_digest": expected_revision_digest,
            "implementation_checkpoint_digest": expected_implementation_checkpoint_digest,
            "planning_digest": plan.get("planning_digest"),
            "project_snapshot_digest": plan.get("project_snapshot_digest"),
            "generation_digest": generation_digest,
            "workspace_digest": workspace_record.get("workspace_digest"),
            "target_digest": (proposal.get("target") or {}).get("target_digest"),
            "operation_count": len(operations), "total_bytes": total,
            "operations": operations,
            "authorization_consumed": False,
            "authorization_consumption_count": 0, "selected_project_modified": False,
            "rollback_prepared": False, "apply_authorized": False, "release_authorized": False,
            "authority_granted": False,
        }
        record["apply_request_digest"] = _digest(record)
        _atomic_json(_request_path(proposal_id, expected_revision, runtime_root), record)
        return {**record, "operation_status": "created", "authorization_phrase": f"APPLY {proposal_id} REVISION {int(expected_revision)} REQUEST {record['apply_request_digest']}"}


def _prepare_rollback(pid: str, rev: int, root: Path, generation: Mapping[str, Any], request: Mapping[str, Any], runtime_root=None) -> dict[str, Any]:
    entries = []
    for row in generation.get("files") or []:
        rel = _safe_relative(str(row.get("relative_path") or ""))
        path = root / rel
        existed = path.is_file() and not path.is_symlink()
        content = path.read_bytes() if existed else b""
        entries.append({
            "relative_path": rel,
            "relative_path_digest": hashlib.sha256(rel.encode()).hexdigest(),
            "existed": existed,
            "content_digest": hashlib.sha256(content).hexdigest() if existed else "",
            "content_b64": base64.b64encode(content).decode("ascii") if existed else "",
        })
    manifest = {
        "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION,
        "ok": True, "status": "rollback_prepared", "proposal_id": pid,
        "proposal_revision": int(rev), "apply_request_digest": request.get("apply_request_digest"),
        "project_snapshot_digest": request.get("project_snapshot_digest"),
        "generation_digest": request.get("generation_digest"),
        "workspace_digest": request.get("workspace_digest"),
        "target_digest": request.get("target_digest"),
        "entries": entries, "entry_count": len(entries), "rollback_executed": False,
        "private_paths_external_only": True,
    }
    manifest["rollback_manifest_digest"] = _digest(manifest)
    _atomic_json(_rollback_path(pid, rev, runtime_root), manifest)
    return manifest


def authorize_and_apply_selected_project(
    proposal_id: str, *, expected_revision: int, expected_revision_digest: str,
    expected_apply_request_digest: str, authorization_phrase: str, runtime_root=None,
) -> dict[str, Any]:
    with _proposal_lock(proposal_id, runtime_root):
        existing_result = _read_json(_result_path(proposal_id, expected_revision, runtime_root))
        if existing_result:
            if not _bound(existing_result, "apply_result_digest"):
                return {"ok": False, "status": "apply_result_invalid"}
            if existing_result.get("apply_request_digest") != expected_apply_request_digest:
                return {"ok": False, "status": "stale_apply_request"}
            return {**existing_result, "operation_status": "resumed"}
        request = _read_json(_request_path(proposal_id, expected_revision, runtime_root))
        if not request or not _bound(request, "apply_request_digest"):
            return {"ok": False, "status": "apply_request_missing_or_invalid"}
        if request.get("apply_request_digest") != expected_apply_request_digest:
            return {"ok": False, "status": "stale_apply_request"}
        if request.get("proposal_revision_digest") != expected_revision_digest:
            return {"ok": False, "status": "stale_proposal_revision"}
        expected_phrase = f"APPLY {proposal_id} REVISION {int(expected_revision)} REQUEST {expected_apply_request_digest}"
        if authorization_phrase.strip() != expected_phrase:
            return {"ok": False, "status": "exact_apply_authorization_required"}
        existing_auth = _read_json(_authorization_path(proposal_id, expected_revision, runtime_root))
        if existing_auth:
            if not _bound(existing_auth, "authorization_receipt_digest") or existing_auth.get("apply_request_digest") != expected_apply_request_digest:
                return {"ok": False, "status": "apply_authorization_receipt_invalid"}
            return _recover_interrupted_apply_locked(
                proposal_id, int(expected_revision), expected_revision_digest, expected_apply_request_digest, runtime_root
            )

        proposal = _read_json(_proposal_path(proposal_id, runtime_root))
        plan = load_grounded_plan(proposal_id, expected_revision, runtime_root=runtime_root)
        if not proposal or not _validate(proposal) or not plan:
            return {"ok": False, "status": "proposal_or_plan_missing"}
        ok, status, root = _verify_selected_snapshot(proposal, plan)
        if not ok or root is None:
            return {"ok": False, "status": status}
        generation = _read_json(_store_root(runtime_root) / "generation" / proposal_id / f"revision-{int(expected_revision)}.json")
        if not generation or generation.get("generation_digest") != request.get("generation_digest"):
            return {"ok": False, "status": "generation_record_missing_or_stale"}
        workspace_record = _read_json(_workspace_record_path(proposal_id, expected_revision, runtime_root))
        workspace_root = _workspace_root(proposal_id, expected_revision, str(request.get("generation_digest") or ""), runtime_root)
        if not workspace_record or not _verify_workspace_record(workspace_record, workspace_root):
            return {"ok": False, "status": "retained_workspace_missing_or_invalid"}

        rollback = _prepare_rollback(proposal_id, expected_revision, root, generation, request, runtime_root)
        auth = {
            "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION,
            "ok": True, "status": "apply_authorization_consumed", "proposal_id": proposal_id,
            "proposal_revision": int(expected_revision), "proposal_revision_digest": expected_revision_digest,
            "apply_request_digest": expected_apply_request_digest,
            "authorization_phrase_digest": hashlib.sha256(expected_phrase.encode()).hexdigest(),
            "consumption_count": 1, "rollback_manifest_digest": rollback["rollback_manifest_digest"],
        }
        auth["authorization_receipt_digest"] = _digest(auth)
        _atomic_json(_authorization_path(proposal_id, expected_revision, runtime_root), auth)
        _write_journal(
            _apply_journal_path(proposal_id, expected_revision, runtime_root),
            proposal_id=proposal_id, proposal_revision=int(expected_revision),
            authorization_receipt_digest=auth["authorization_receipt_digest"],
            phase="applying", completed_count=0, operation_count=len(generation.get("files") or []),
        )

        applied = []
        try:
            for row in generation.get("files") or []:
                rel = _safe_relative(str(row.get("relative_path") or ""))
                target = root / rel
                operation = str(row.get("operation") or "")
                if operation == "delete":
                    target.unlink(missing_ok=True)
                else:
                    source = workspace_root / rel
                    if not source.is_file() or source.is_symlink() or _file_digest(source) != row.get("content_digest"):
                        raise RuntimeError("workspace_content_changed")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=str(target.parent))
                    os.close(fd)
                    temp = Path(temp_name)
                    try:
                        shutil.copyfile(source, temp)
                        os.replace(temp, target)
                    finally:
                        temp.unlink(missing_ok=True)
                applied.append(rel)
                _write_journal(
                    _apply_journal_path(proposal_id, expected_revision, runtime_root),
                    proposal_id=proposal_id, proposal_revision=int(expected_revision),
                    authorization_receipt_digest=auth["authorization_receipt_digest"],
                    phase="applying", completed_count=len(applied), operation_count=len(generation.get("files") or []),
                )
        except Exception as error:
            for entry in rollback["entries"]:
                target = root / _safe_relative(entry["relative_path"])
                if entry["existed"]:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(base64.b64decode(entry["content_b64"]))
                else:
                    target.unlink(missing_ok=True)
            if not _manifest_restored(root, rollback):
                return {"ok": False, "status": "transactional_apply_failed_recovery_required", "error_type": type(error).__name__}
            failure = {
                "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION,
                "ok": False, "status": "transactional_apply_failed_rolled_back",
                "proposal_id": proposal_id, "proposal_revision": int(expected_revision),
                "proposal_revision_digest": expected_revision_digest,
                "apply_request_digest": expected_apply_request_digest,
                "authorization_receipt_digest": auth["authorization_receipt_digest"],
                "authorization_consumption_count": 1,
                "rollback_manifest_digest": rollback["rollback_manifest_digest"],
                "rollback_prepared": True, "rollback_executed": True,
                "applied_count": 0, "applied_path_digests": [],
                "selected_project_modified": False, "implementation_applied": False,
                "apply_authorized": True, "repair_authorized": False,
                "release_authorized": False, "authority_granted": False,
                "error_type": type(error).__name__,
            }
            failure["apply_result_digest"] = _digest(failure)
            _atomic_json(_result_path(proposal_id, expected_revision, runtime_root), failure)
            _write_journal(_apply_journal_path(proposal_id, expected_revision, runtime_root), proposal_id=proposal_id, proposal_revision=int(expected_revision), authorization_receipt_digest=auth["authorization_receipt_digest"], phase="sealed_failed_rolled_back", result_digest=failure["apply_result_digest"])
            return {**failure, "operation_status": "created"}

        result = {
            "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION,
            "ok": True, "status": "selected_project_apply_completed",
            "proposal_id": proposal_id, "proposal_revision": int(expected_revision),
            "proposal_revision_digest": expected_revision_digest,
            "apply_request_digest": expected_apply_request_digest,
            "authorization_receipt_digest": auth["authorization_receipt_digest"],
            "authorization_consumption_count": 1,
            "rollback_manifest_digest": rollback["rollback_manifest_digest"],
            "rollback_prepared": True, "rollback_executed": False,
            "applied_count": len(applied), "applied_path_digests": [hashlib.sha256(x.encode()).hexdigest() for x in applied],
            "selected_project_modified": True, "implementation_applied": True,
            "apply_authorized": True, "repair_authorized": False,
            "release_authorized": False, "authority_granted": False,
        }
        result["apply_result_digest"] = _digest(result)
        _atomic_json(_result_path(proposal_id, expected_revision, runtime_root), result)
        _write_journal(_apply_journal_path(proposal_id, expected_revision, runtime_root), proposal_id=proposal_id, proposal_revision=int(expected_revision), authorization_receipt_digest=auth["authorization_receipt_digest"], phase="sealed_completed", result_digest=result["apply_result_digest"])
        return {**result, "operation_status": "created"}


def public_apply_record(record: Mapping[str, Any]) -> dict[str, Any]:
    if not record:
        return {}
    allowed = {
        "ok", "status", "proposal_id", "proposal_revision", "proposal_revision_digest",
        "implementation_checkpoint_digest", "apply_request_digest", "operation_count", "total_bytes",
        "authorization_consumed", "authorization_consumption_count", "authorization_receipt_digest",
        "rollback_manifest_digest", "rollback_prepared", "rollback_executed", "applied_count",
        "applied_path_digests", "apply_result_digest", "selected_project_modified", "implementation_applied",
        "apply_authorized", "repair_authorized", "release_authorized", "authority_granted", "operation_status",
    }
    public = {key: record.get(key) for key in allowed if key in record}
    public.update({"private_path_exposed": False, "private_content_exposed": False, "rollback_content_exposed": False})
    return public



def _rollback_request_path(pid: str, rev: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "selected_project_rollback_requests" / pid / f"revision-{int(rev)}.json"


def _rollback_authorization_path(pid: str, rev: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "selected_project_rollback_authorizations" / pid / f"revision-{int(rev)}.json"


def _rollback_result_path(pid: str, rev: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "selected_project_rollback_results" / pid / f"revision-{int(rev)}.json"


def _restore_manifest_entries(root: Path, manifest: Mapping[str, Any]) -> list[str]:
    restored: list[str] = []
    for entry in manifest.get("entries") or []:
        rel = _safe_relative(str(entry.get("relative_path") or ""))
        target = root / rel
        if entry.get("existed"):
            content = base64.b64decode(str(entry.get("content_b64") or ""))
            if hashlib.sha256(content).hexdigest() != entry.get("content_digest"):
                raise RuntimeError("rollback_content_digest_mismatch")
            target.parent.mkdir(parents=True, exist_ok=True)
            fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.rollback.", dir=str(target.parent))
            os.close(fd)
            temp = Path(temp_name)
            try:
                temp.write_bytes(content)
                os.replace(temp, target)
            finally:
                temp.unlink(missing_ok=True)
        else:
            target.unlink(missing_ok=True)
        restored.append(rel)
    return restored


def _manifest_restored(root: Path, manifest: Mapping[str, Any]) -> bool:
    for entry in manifest.get("entries") or []:
        rel = _safe_relative(str(entry.get("relative_path") or ""))
        target = root / rel
        if entry.get("existed"):
            if not target.is_file() or target.is_symlink() or _file_digest(target) != entry.get("content_digest"):
                return False
        elif target.exists():
            return False
    return True


def _generation_applied(root: Path, generation: Mapping[str, Any]) -> bool:
    for row in generation.get("files") or []:
        rel = _safe_relative(str(row.get("relative_path") or ""))
        target = root / rel
        if row.get("operation") == "delete":
            if target.exists():
                return False
        elif not target.is_file() or target.is_symlink() or _file_digest(target) != row.get("content_digest"):
            return False
    return True


def _recover_interrupted_apply_locked(
    proposal_id: str, expected_revision: int, expected_revision_digest: str,
    expected_apply_request_digest: str, runtime_root=None,
) -> dict[str, Any]:
    existing = _read_json(_result_path(proposal_id, expected_revision, runtime_root))
    if existing:
        if not _bound(existing, "apply_result_digest"):
            return {"ok": False, "status": "apply_result_invalid"}
        if existing.get("apply_request_digest") != expected_apply_request_digest:
            return {"ok": False, "status": "stale_apply_request"}
        return {**existing, "operation_status": "resumed"}
    request = _read_json(_request_path(proposal_id, expected_revision, runtime_root))
    auth = _read_json(_authorization_path(proposal_id, expected_revision, runtime_root))
    manifest = _read_json(_rollback_path(proposal_id, expected_revision, runtime_root))
    journal = _read_json(_apply_journal_path(proposal_id, expected_revision, runtime_root))
    if not request or not _bound(request, "apply_request_digest") or request.get("apply_request_digest") != expected_apply_request_digest:
        return {"ok": False, "status": "apply_request_missing_or_stale"}
    if request.get("proposal_revision_digest") != expected_revision_digest:
        return {"ok": False, "status": "stale_proposal_revision"}
    if not auth or not _bound(auth, "authorization_receipt_digest") or auth.get("apply_request_digest") != expected_apply_request_digest:
        return {"ok": False, "status": "apply_authorization_not_consumed"}
    if not _validate_manifest(manifest, expected_apply_request_digest=expected_apply_request_digest) or manifest.get("rollback_manifest_digest") != auth.get("rollback_manifest_digest"):
        return {"ok": False, "status": "rollback_manifest_missing_or_invalid"}
    if journal and (not _valid_journal(journal) or journal.get("authorization_receipt_digest") != auth.get("authorization_receipt_digest")):
        return {"ok": False, "status": "apply_journal_invalid"}
    proposal = _read_json(_proposal_path(proposal_id, runtime_root))
    try:
        root = Path(str(((proposal or {}).get("target") or {}).get("private_path") or "")).expanduser().resolve(strict=True)
    except (OSError, RuntimeError):
        return {"ok": False, "status": "selected_project_unavailable"}
    generation = _read_json(_store_root(runtime_root) / "generation" / proposal_id / f"revision-{int(expected_revision)}.json")
    if not generation or generation.get("generation_digest") != request.get("generation_digest"):
        return {"ok": False, "status": "generation_record_missing_or_stale"}
    state = _project_scope_state(root, generation, manifest)
    conflict_observed = state == "conflict"
    if state == "generated":
        status, modified, applied_count, rollback_executed = "selected_project_apply_completed_recovered", True, len(generation.get("files") or []), False
    else:
        try:
            _restore_manifest_entries(root, manifest)
        except Exception as error:
            return {"ok": False, "status": "apply_recovery_rollback_failed", "error_type": type(error).__name__}
        if not _manifest_restored(root, manifest):
            return {"ok": False, "status": "apply_recovery_verification_failed"}
        status, modified, applied_count, rollback_executed = "interrupted_apply_recovered_by_rollback", False, 0, True
    result = {
        "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION, "ok": True, "status": status,
        "proposal_id": proposal_id, "proposal_revision": int(expected_revision), "proposal_revision_digest": expected_revision_digest,
        "apply_request_digest": expected_apply_request_digest, "authorization_receipt_digest": auth.get("authorization_receipt_digest"),
        "authorization_consumption_count": 1, "rollback_manifest_digest": manifest.get("rollback_manifest_digest"),
        "rollback_prepared": True, "rollback_executed": rollback_executed, "applied_count": applied_count,
        "applied_path_digests": [], "selected_project_modified": modified, "implementation_applied": modified,
        "apply_authorized": True, "repair_authorized": False, "release_authorized": False, "authority_granted": False,
        "recovery_performed": True, "recovery_scope_state": state,
        "recovery_conflict_observed": conflict_observed,
    }
    result["apply_result_digest"] = _digest(result)
    _atomic_json(_result_path(proposal_id, expected_revision, runtime_root), result)
    _write_journal(_apply_journal_path(proposal_id, expected_revision, runtime_root), proposal_id=proposal_id, proposal_revision=int(expected_revision), authorization_receipt_digest=auth.get("authorization_receipt_digest"), phase="sealed_recovered", result_digest=result["apply_result_digest"])
    return {**result, "operation_status": "created"}


def recover_interrupted_selected_project_apply(
    proposal_id: str, *, expected_revision: int, expected_revision_digest: str,
    expected_apply_request_digest: str, runtime_root=None,
) -> dict[str, Any]:
    with _proposal_lock(proposal_id, runtime_root):
        return _recover_interrupted_apply_locked(proposal_id, expected_revision, expected_revision_digest, expected_apply_request_digest, runtime_root)


def create_or_resume_rollback_request(
    proposal_id: str, *, expected_revision: int, expected_revision_digest: str,
    expected_apply_result_digest: str, runtime_root=None,
) -> dict[str, Any]:
    with _proposal_lock(proposal_id, runtime_root):
        existing = _read_json(_rollback_request_path(proposal_id, expected_revision, runtime_root))
        if existing:
            if not _bound(existing, "rollback_request_digest"):
                return {"ok": False, "status": "rollback_request_invalid"}
            if existing.get("apply_result_digest") != expected_apply_result_digest:
                return {"ok": False, "status": "stale_apply_result"}
            return {**existing, "operation_status": "resumed"}
        apply_result = _read_json(_result_path(proposal_id, expected_revision, runtime_root))
        manifest = _read_json(_rollback_path(proposal_id, expected_revision, runtime_root))
        if not apply_result or not _bound(apply_result, "apply_result_digest") or apply_result.get("apply_result_digest") != expected_apply_result_digest:
            return {"ok": False, "status": "apply_result_missing_or_stale"}
        if apply_result.get("proposal_revision_digest") != expected_revision_digest:
            return {"ok": False, "status": "stale_proposal_revision"}
        if not apply_result.get("selected_project_modified"):
            return {"ok": False, "status": "applied_project_required"}
        if not _validate_manifest(manifest, expected_apply_request_digest=str(apply_result.get("apply_request_digest") or "")) or manifest.get("rollback_manifest_digest") != apply_result.get("rollback_manifest_digest"):
            return {"ok": False, "status": "rollback_manifest_missing_or_invalid"}
        proposal = _read_json(_proposal_path(proposal_id, runtime_root))
        try:
            root = Path(str(((proposal or {}).get("target") or {}).get("private_path") or "")).expanduser().resolve(strict=True)
        except (OSError, RuntimeError):
            return {"ok": False, "status": "selected_project_unavailable"}
        generation = _read_json(_store_root(runtime_root) / "generation" / proposal_id / f"revision-{int(expected_revision)}.json")
        if not generation or generation.get("generation_digest") != manifest.get("generation_digest"):
            return {"ok": False, "status": "generation_record_missing_or_stale"}
        if _project_scope_state(root, generation, manifest) != "generated":
            return {"ok": False, "status": "selected_project_changed_after_apply"}
        record = {
            "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION,
            "ok": True, "status": "selected_project_rollback_awaiting_exact_authorization",
            "proposal_id": proposal_id, "proposal_revision": int(expected_revision),
            "proposal_revision_digest": expected_revision_digest,
            "apply_result_digest": expected_apply_result_digest,
            "apply_request_digest": apply_result.get("apply_request_digest"),
            "rollback_manifest_digest": manifest.get("rollback_manifest_digest"),
            "entry_count": int(manifest.get("entry_count") or 0),
            "authorization_consumed": False, "authorization_consumption_count": 0,
            "rollback_authorized": False, "rollback_executed": False,
            "release_authorized": False, "authority_granted": False,
        }
        record["rollback_request_digest"] = _digest(record)
        _atomic_json(_rollback_request_path(proposal_id, expected_revision, runtime_root), record)
        phrase = f"ROLLBACK {proposal_id} REVISION {int(expected_revision)} REQUEST {record['rollback_request_digest']}"
        return {**record, "operation_status": "created", "authorization_phrase": phrase}


def _recover_interrupted_rollback_locked(
    proposal_id: str, expected_revision: int, expected_revision_digest: str,
    expected_rollback_request_digest: str, runtime_root=None,
) -> dict[str, Any]:
    existing = _read_json(_rollback_result_path(proposal_id, expected_revision, runtime_root))
    if existing:
        if not _bound(existing, "rollback_result_digest"):
            return {"ok": False, "status": "rollback_result_invalid"}
        if existing.get("rollback_request_digest") != expected_rollback_request_digest:
            return {"ok": False, "status": "stale_rollback_request"}
        return {**existing, "operation_status": "resumed"}
    request = _read_json(_rollback_request_path(proposal_id, expected_revision, runtime_root))
    auth = _read_json(_rollback_authorization_path(proposal_id, expected_revision, runtime_root))
    apply_result = _read_json(_result_path(proposal_id, expected_revision, runtime_root))
    manifest = _read_json(_rollback_path(proposal_id, expected_revision, runtime_root))
    journal = _read_json(_rollback_journal_path(proposal_id, expected_revision, runtime_root))
    if not request or not _bound(request, "rollback_request_digest") or request.get("rollback_request_digest") != expected_rollback_request_digest:
        return {"ok": False, "status": "rollback_request_missing_or_stale"}
    if request.get("proposal_revision_digest") != expected_revision_digest:
        return {"ok": False, "status": "stale_proposal_revision"}
    if not auth or not _bound(auth, "authorization_receipt_digest") or auth.get("rollback_request_digest") != expected_rollback_request_digest:
        return {"ok": False, "status": "rollback_authorization_not_consumed"}
    if not apply_result or not _bound(apply_result, "apply_result_digest") or apply_result.get("apply_result_digest") != request.get("apply_result_digest"):
        return {"ok": False, "status": "apply_result_missing_or_stale"}
    if not _validate_manifest(manifest, expected_apply_request_digest=str(apply_result.get("apply_request_digest") or "")) or manifest.get("rollback_manifest_digest") != request.get("rollback_manifest_digest"):
        return {"ok": False, "status": "rollback_manifest_missing_or_invalid"}
    if journal and (not _valid_journal(journal) or journal.get("authorization_receipt_digest") != auth.get("authorization_receipt_digest")):
        return {"ok": False, "status": "rollback_journal_invalid"}
    proposal = _read_json(_proposal_path(proposal_id, runtime_root))
    try:
        root = Path(str(((proposal or {}).get("target") or {}).get("private_path") or "")).expanduser().resolve(strict=True)
    except (OSError, RuntimeError):
        return {"ok": False, "status": "selected_project_unavailable"}
    generation = _read_json(_store_root(runtime_root) / "generation" / proposal_id / f"revision-{int(expected_revision)}.json")
    if not generation or generation.get("generation_digest") != manifest.get("generation_digest"):
        return {"ok": False, "status": "generation_record_missing_or_stale"}
    state = _project_scope_state(root, generation, manifest)
    if state == "conflict":
        return {"ok": False, "status": "rollback_recovery_conflict_detected"}
    if state != "original":
        try:
            restored = _restore_manifest_entries(root, manifest)
        except Exception as error:
            return {"ok": False, "status": "rollback_recovery_failed", "error_type": type(error).__name__}
    else:
        restored = [str(entry.get("relative_path") or "") for entry in manifest.get("entries") or []]
    if not _manifest_restored(root, manifest):
        return {"ok": False, "status": "rollback_recovery_verification_failed"}
    result = {
        "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION, "ok": True,
        "status": "selected_project_rollback_completed_recovered", "proposal_id": proposal_id,
        "proposal_revision": int(expected_revision), "proposal_revision_digest": expected_revision_digest,
        "apply_result_digest": apply_result.get("apply_result_digest"), "rollback_request_digest": expected_rollback_request_digest,
        "authorization_receipt_digest": auth.get("authorization_receipt_digest"), "authorization_consumption_count": 1,
        "rollback_manifest_digest": manifest.get("rollback_manifest_digest"), "restored_count": len(restored),
        "restored_path_digests": [hashlib.sha256(x.encode()).hexdigest() for x in restored],
        "rollback_authorized": True, "rollback_executed": True, "selected_project_modified": False,
        "implementation_applied": False, "release_authorized": False, "authority_granted": False,
        "recovery_performed": True, "recovery_scope_state": state,
    }
    result["rollback_result_digest"] = _digest(result)
    _atomic_json(_rollback_result_path(proposal_id, expected_revision, runtime_root), result)
    _write_journal(_rollback_journal_path(proposal_id, expected_revision, runtime_root), proposal_id=proposal_id, proposal_revision=int(expected_revision), authorization_receipt_digest=auth.get("authorization_receipt_digest"), phase="sealed_recovered", result_digest=result["rollback_result_digest"])
    return {**result, "operation_status": "created"}


def recover_interrupted_selected_project_rollback(
    proposal_id: str, *, expected_revision: int, expected_revision_digest: str,
    expected_rollback_request_digest: str, runtime_root=None,
) -> dict[str, Any]:
    with _proposal_lock(proposal_id, runtime_root):
        return _recover_interrupted_rollback_locked(proposal_id, expected_revision, expected_revision_digest, expected_rollback_request_digest, runtime_root)


def authorize_and_rollback_selected_project(
    proposal_id: str, *, expected_revision: int, expected_revision_digest: str,
    expected_rollback_request_digest: str, authorization_phrase: str, runtime_root=None,
) -> dict[str, Any]:
    with _proposal_lock(proposal_id, runtime_root):
        existing = _read_json(_rollback_result_path(proposal_id, expected_revision, runtime_root))
        if existing:
            if not _bound(existing, "rollback_result_digest"):
                return {"ok": False, "status": "rollback_result_invalid"}
            if existing.get("rollback_request_digest") != expected_rollback_request_digest:
                return {"ok": False, "status": "stale_rollback_request"}
            return {**existing, "operation_status": "resumed"}
        request = _read_json(_rollback_request_path(proposal_id, expected_revision, runtime_root))
        if not request or not _bound(request, "rollback_request_digest") or request.get("rollback_request_digest") != expected_rollback_request_digest:
            return {"ok": False, "status": "rollback_request_missing_or_stale"}
        if request.get("proposal_revision_digest") != expected_revision_digest:
            return {"ok": False, "status": "stale_proposal_revision"}
        phrase = f"ROLLBACK {proposal_id} REVISION {int(expected_revision)} REQUEST {expected_rollback_request_digest}"
        if authorization_phrase.strip() != phrase:
            return {"ok": False, "status": "exact_rollback_authorization_required"}
        existing_auth = _read_json(_rollback_authorization_path(proposal_id, expected_revision, runtime_root))
        if existing_auth:
            if not _bound(existing_auth, "authorization_receipt_digest") or existing_auth.get("rollback_request_digest") != expected_rollback_request_digest:
                return {"ok": False, "status": "rollback_authorization_receipt_invalid"}
            return _recover_interrupted_rollback_locked(proposal_id, int(expected_revision), expected_revision_digest, expected_rollback_request_digest, runtime_root)
        apply_result = _read_json(_result_path(proposal_id, expected_revision, runtime_root))
        manifest = _read_json(_rollback_path(proposal_id, expected_revision, runtime_root))
        if not apply_result or not _bound(apply_result, "apply_result_digest") or apply_result.get("apply_result_digest") != request.get("apply_result_digest"):
            return {"ok": False, "status": "apply_result_missing_or_stale"}
        if not _validate_manifest(manifest, expected_apply_request_digest=str(apply_result.get("apply_request_digest") or "")) or manifest.get("rollback_manifest_digest") != request.get("rollback_manifest_digest"):
            return {"ok": False, "status": "rollback_manifest_missing_or_invalid"}
        proposal = _read_json(_proposal_path(proposal_id, runtime_root))
        try:
            root = Path(str(((proposal or {}).get("target") or {}).get("private_path") or "")).expanduser().resolve(strict=True)
        except (OSError, RuntimeError):
            return {"ok": False, "status": "selected_project_unavailable"}
        auth = {
            "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION,
            "ok": True, "status": "rollback_authorization_consumed", "proposal_id": proposal_id,
            "proposal_revision": int(expected_revision), "proposal_revision_digest": expected_revision_digest,
            "rollback_request_digest": expected_rollback_request_digest,
            "authorization_phrase_digest": hashlib.sha256(phrase.encode()).hexdigest(), "consumption_count": 1,
        }
        generation = _read_json(_store_root(runtime_root) / "generation" / proposal_id / f"revision-{int(expected_revision)}.json")
        if not generation or generation.get("generation_digest") != manifest.get("generation_digest"):
            return {"ok": False, "status": "generation_record_missing_or_stale"}
        if _project_scope_state(root, generation, manifest) != "generated":
            return {"ok": False, "status": "selected_project_changed_after_apply"}
        auth["authorization_receipt_digest"] = _digest(auth)
        _atomic_json(_rollback_authorization_path(proposal_id, expected_revision, runtime_root), auth)
        _write_journal(_rollback_journal_path(proposal_id, expected_revision, runtime_root), proposal_id=proposal_id, proposal_revision=int(expected_revision), authorization_receipt_digest=auth["authorization_receipt_digest"], phase="rolling_back", completed_count=0, operation_count=len(manifest.get("entries") or []))
        try:
            restored = _restore_manifest_entries(root, manifest)
        except Exception as error:
            return {"ok": False, "status": "selected_project_rollback_failed", "error_type": type(error).__name__}
        if not _manifest_restored(root, manifest):
            return {"ok": False, "status": "selected_project_rollback_verification_failed"}
        result = {
            "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION,
            "ok": True, "status": "selected_project_rollback_completed", "proposal_id": proposal_id,
            "proposal_revision": int(expected_revision), "proposal_revision_digest": expected_revision_digest,
            "apply_result_digest": apply_result.get("apply_result_digest"),
            "rollback_request_digest": expected_rollback_request_digest,
            "authorization_receipt_digest": auth.get("authorization_receipt_digest"),
            "authorization_consumption_count": 1,
            "rollback_manifest_digest": manifest.get("rollback_manifest_digest"),
            "restored_count": len(restored),
            "restored_path_digests": [hashlib.sha256(x.encode()).hexdigest() for x in restored],
            "rollback_authorized": True, "rollback_executed": True,
            "selected_project_modified": False, "implementation_applied": False,
            "release_authorized": False, "authority_granted": False,
        }
        result["rollback_result_digest"] = _digest(result)
        _atomic_json(_rollback_result_path(proposal_id, expected_revision, runtime_root), result)
        _write_journal(_rollback_journal_path(proposal_id, expected_revision, runtime_root), proposal_id=proposal_id, proposal_revision=int(expected_revision), authorization_receipt_digest=auth["authorization_receipt_digest"], phase="sealed_completed", result_digest=result["rollback_result_digest"])
        return {**result, "operation_status": "created"}


def public_rollback_record(record: Mapping[str, Any]) -> dict[str, Any]:
    if not record:
        return {}
    allowed = {
        "ok", "status", "proposal_id", "proposal_revision", "proposal_revision_digest",
        "apply_result_digest", "rollback_request_digest", "rollback_manifest_digest", "entry_count",
        "authorization_consumed", "authorization_consumption_count", "authorization_receipt_digest",
        "rollback_authorized", "rollback_executed", "restored_count", "restored_path_digests",
        "rollback_result_digest", "selected_project_modified", "implementation_applied",
        "release_authorized", "authority_granted", "operation_status", "recovery_performed",
    }
    public = {key: record.get(key) for key in allowed if key in record}
    public.update({"private_path_exposed": False, "private_content_exposed": False, "rollback_content_exposed": False})
    return public
