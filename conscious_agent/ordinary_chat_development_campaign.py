from __future__ import annotations

"""Persistent ordinary-chat intake for supervised development campaigns.

This v1200.1-v1200.3 seam turns a grounded ordinary conversational software
request into durable external-runtime proposal state.  It may consume one exact
operator approval for one exact proposal revision, but it never contacts a
provider, generates code, creates an implementation workspace, runs commands,
modifies source, promotes a release, manages models, or grants independent
authority.
"""

import hashlib
import json
import os
import re
import tempfile
import time
from contextlib import ExitStack, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping

from paths import DATA_DIR

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1200.6"
MAX_REQUEST_CHARS = 12000
# Large source-only projects need sealed inventory/workspace receipts larger
# than the original v1200 proposal-only budget. Request text remains separately
# bounded; this is only the maximum external runtime record size.
MAX_FILE_BYTES = 4 * 1024 * 1024
LOCK_TIMEOUT_SECONDS = 60.0
LOCK_STALE_SECONDS = 30.0

ACTIVE_STATES = frozenset({"awaiting_approval", "approval_processing"})
TERMINAL_STATES = frozenset({
    "approved_pending_grounded_specification", "rejected", "cancelled", "unsupported_request",
    "approval_receipt_invalid",
})

_APPROVAL = re.compile(
    r"^(?:i\s+)?approve\s+(?:the\s+)?(?:development\s+)?proposal\s+"
    r"(?P<proposal_id>devc_[a-f0-9]{24})\s+revision\s+(?P<revision>[1-9][0-9]*)[.!?]*$",
    re.I,
)
_REJECTION = re.compile(
    r"^(?:i\s+)?reject\s+(?:the\s+)?(?:development\s+)?proposal\s+"
    r"(?P<proposal_id>devc_[a-f0-9]{24})\s+revision\s+(?P<revision>[1-9][0-9]*)[.!?]*$",
    re.I,
)
_CANCELLATION = re.compile(
    r"^(?:please\s+)?cancel\s+(?:the\s+)?(?:development\s+)?proposal\s+"
    r"(?P<proposal_id>devc_[a-f0-9]{24})\s+revision\s+(?P<revision>[1-9][0-9]*)[.!?]*$",
    re.I,
)

_FORBIDDEN_AUTHORITY = re.compile(
    r"\b(?:modify|edit|rewrite|replace)\b.*\beidolon(?:'s)?(?:\s+source)?\b|"
    r"\b(?:promote|release|certify)\b.*\b(?:eidolon|release)\b|"
    r"\b(?:install|delete|pull|switch|manage|replace)\b.*\b(?:model|provider)\b|"
    r"\b(?:self[- ]modify|autonomous(?:ly)?\s+(?:code|develop|release)|independent authority)\b",
    re.I,
)

_DEVELOPMENT_REQUEST = re.compile(
    r"\b(?:build|create|make|develop|code|implement|modify|edit|rewrite|fix|add|install|delete|pull|switch|manage)\b"
    r".{0,180}\b(?:web\s*(?:page|site|app)?|website|app|application|software|script|tool|utility|cli|"
    r"command[- ]line|code|source|model|provider|browser\s+extension|api|calculator|program|text[- ]to[- ]speech|speech\s+system|voice\s+system)\b",
    re.I | re.S,
)
_UNSUPPORTED_SCOPE = re.compile(
    r"\b(?:native\s+(?:desktop|windows|mac|linux|mobile)|mobile\s+(?:app|application)|"
    r"desktop\s+(?:app|application)|android|ios|accounting\s+suite|erp|production\s+saas|"
    r"kernel|driver|firmware|browser\s+extension|game\s+engine)\b",
    re.I,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _clean(value: Any, limit: int = MAX_REQUEST_CHARS) -> str:
    return " ".join(str(value or "").replace("\x00", " ").split())[:limit]


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _runtime_root(runtime_root: str | Path | None = None) -> Path:
    return Path(runtime_root).expanduser().resolve() if runtime_root else Path(DATA_DIR).resolve()


def _store_root(runtime_root: str | Path | None = None) -> Path:
    return _runtime_root(runtime_root) / "development_campaigns"


def _proposal_path(proposal_id: str, runtime_root: str | Path | None = None) -> Path:
    if not re.fullmatch(r"devc_[a-f0-9]{24}", str(proposal_id or "")):
        raise ValueError("Invalid development proposal id.")
    return _store_root(runtime_root) / "proposals" / f"{proposal_id}.json"


def _intake_index_path(intake_key: str, runtime_root: str | Path | None = None) -> Path:
    if not re.fullmatch(r"[a-f0-9]{64}", str(intake_key or "")):
        raise ValueError("Invalid development intake key.")
    return _store_root(runtime_root) / "intake-index" / f"{intake_key}.json"


def _approval_path(proposal_id: str, revision: int, runtime_root: str | Path | None = None) -> Path:
    return _store_root(runtime_root) / "approvals" / proposal_id / f"revision-{int(revision)}.json"


def _event_path(proposal_id: str, sequence: int, runtime_root: str | Path | None = None) -> Path:
    return _store_root(runtime_root) / "events" / proposal_id / f"{int(sequence):06d}.json"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError(f"Runtime state exceeded {MAX_FILE_BYTES} bytes: {path.name}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Runtime state must be an object: {path.name}")
    return value


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    encoded = (json.dumps(dict(value), indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")
    if len(encoded) > MAX_FILE_BYTES:
        raise ValueError(f"Runtime state exceeded {MAX_FILE_BYTES} bytes: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("wb", delete=False, dir=path.parent, suffix=".tmp") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


@contextmanager
def _named_lock(lock_name: str, runtime_root: str | Path | None = None) -> Iterator[None]:
    clean_name = str(lock_name or "")
    if not re.fullmatch(r"(?:devc_[a-f0-9]{24}|intake-[a-f0-9]{64})", clean_name):
        raise ValueError("Invalid development campaign lock name.")
    lock = _store_root(runtime_root) / "locks" / f"{clean_name}.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
    while True:
        try:
            lock.mkdir()
            (lock / "owner.json").write_text(json.dumps({"pid": os.getpid(), "created_at": _now()}), encoding="utf-8")
            break
        except (FileExistsError, PermissionError):
            # Windows can report sharing contention on an existing directory as
            # AccessDenied rather than FileExists. Treat both as a held lock.
            if not lock.exists():
                time.sleep(0.01)
                continue
            try:
                age = time.time() - lock.stat().st_mtime
            except FileNotFoundError:
                continue
            if age > LOCK_STALE_SECONDS:
                try:
                    for child in lock.iterdir():
                        child.unlink(missing_ok=True)
                    lock.rmdir()
                    continue
                except OSError:
                    pass
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Timed out waiting for development campaign lock: {clean_name}")
            time.sleep(0.01)
    try:
        yield
    finally:
        try:
            for child in lock.iterdir():
                child.unlink(missing_ok=True)
            lock.rmdir()
        except (FileNotFoundError, PermissionError):
            pass


@contextmanager
def _proposal_lock(proposal_id: str, runtime_root: str | Path | None = None) -> Iterator[None]:
    with _named_lock(proposal_id, runtime_root):
        yield


@contextmanager
def _intake_lock(intake_key: str, runtime_root: str | Path | None = None) -> Iterator[None]:
    with _named_lock(f"intake-{intake_key}", runtime_root):
        yield


def _target(project_state: Mapping[str, Any] | None) -> dict[str, Any]:
    project = dict(project_state or {})
    project_id = _clean(project.get("id") or project.get("project_id"), 120)
    project_name = _clean(project.get("name") or project.get("title"), 160)
    private_path = _clean(project.get("path") or project.get("root") or project.get("workspace"), 2000)
    if project_id or private_path:
        path_digest = hashlib.sha256(private_path.encode("utf-8")).hexdigest() if private_path else ""
        target_digest = _digest({"mode": "selected_project", "project_id": project_id, "path_digest": path_digest})
        return {
            "mode": "selected_project",
            "project_id": project_id,
            "project_name": project_name,
            "private_path": private_path,
            "path_digest": path_digest,
            "target_digest": target_digest,
        }
    return {
        "mode": "isolated_workspace",
        "project_id": "",
        "project_name": "New isolated development workspace",
        "private_path": "",
        "path_digest": "",
        "target_digest": _digest({"mode": "isolated_workspace"}),
    }


def _support(request: str) -> dict[str, Any]:
    if _FORBIDDEN_AUTHORITY.search(request):
        return {
            "supported": False,
            "support_status": "unsupported_authority_request",
            "limitation": "Eidolon cannot modify its own source, promote releases, manage models, or acquire independent authority through ordinary chat.",
            "risk_level": "blocked",
        }
    if _UNSUPPORTED_SCOPE.search(request):
        return {
            "supported": False,
            "support_status": "unsupported_current_scope",
            "limitation": "This request is outside the current small-project supervised development scope. It is recorded as unsupported rather than treated as executed.",
            "risk_level": "unknown",
        }
    return {
        "supported": True,
        "support_status": "supported_for_supervised_proposal",
        "limitation": "Implementation remains deferred until grounded inspection, specification, file planning, and test planning are available in v1200.4-v1200.6.",
        "risk_level": "medium",
    }


def _revision_payload(proposal: Mapping[str, Any]) -> dict[str, Any]:
    target = dict(proposal.get("target") or {})
    return {
        "proposal_id": proposal.get("proposal_id"),
        "revision": int(proposal.get("revision") or 0),
        "request_digest": proposal.get("request_digest"),
        "target_digest": target.get("target_digest"),
        "intake_key": proposal.get("intake_key"),
        "support_status": proposal.get("support_status"),
        "risk_level": proposal.get("risk_level"),
    }


def _seal(proposal: dict[str, Any]) -> dict[str, Any]:
    proposal["revision_digest"] = _digest(_revision_payload(proposal))
    proposal["proposal_digest"] = _digest({key: value for key, value in proposal.items() if key != "proposal_digest"})
    return proposal


def _validate(proposal: Mapping[str, Any]) -> bool:
    supplied_revision = str(proposal.get("revision_digest") or "")
    supplied_proposal = str(proposal.get("proposal_digest") or "")
    target = dict(proposal.get("target") or {})
    expected_intake_key = _intake_key(str(proposal.get("request_digest") or ""), str(target.get("target_digest") or ""))
    if proposal.get("intake_key") != expected_intake_key:
        return False
    if supplied_revision != _digest(_revision_payload(proposal)):
        return False
    current = {key: value for key, value in proposal.items() if key != "proposal_digest"}
    return supplied_proposal == _digest(current)


def _intake_key(request_digest: str, target_digest: str) -> str:
    return _digest({"request_digest": request_digest, "target_digest": target_digest})


def _proposal_id_for_generation(intake_key: str, generation: int) -> str:
    return "devc_" + hashlib.sha256(f"{intake_key}:{int(generation)}".encode("ascii")).hexdigest()[:24]


def _next_proposal_id(intake_key: str, runtime_root: str | Path | None = None) -> str:
    store = _store_root(runtime_root)
    for generation in range(1, 1_000_001):
        proposal_id = _proposal_id_for_generation(intake_key, generation)
        occupied = any((
            _proposal_path(proposal_id, runtime_root).exists(),
            (store / "events" / proposal_id).exists(),
            (store / "approvals" / proposal_id).exists(),
        ))
        if not occupied:
            return proposal_id
    raise RuntimeError("Development proposal id space was exhausted.")


def _intake_index_payload(proposal: Mapping[str, Any]) -> dict[str, Any]:
    target = dict(proposal.get("target") or {})
    payload = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "intake_key": proposal.get("intake_key", ""),
        "proposal_id": proposal.get("proposal_id", ""),
        "revision": int(proposal.get("revision") or 0),
        "revision_digest": proposal.get("revision_digest", ""),
        "request_digest": proposal.get("request_digest", ""),
        "target_digest": target.get("target_digest", ""),
        "updated_at": proposal.get("updated_at", ""),
        "content_free": True,
        "private_request_included": False,
        "private_path_included": False,
    }
    payload["index_digest"] = _digest(payload)
    return payload


def _valid_intake_index(index: Mapping[str, Any], intake_key: str) -> bool:
    supplied = str(index.get("index_digest") or "")
    payload = {key: value for key, value in index.items() if key != "index_digest"}
    return bool(
        supplied
        and supplied == _digest(payload)
        and index.get("intake_key") == intake_key
        and _intake_key(str(index.get("request_digest") or ""), str(index.get("target_digest") or "")) == intake_key
        and re.fullmatch(r"devc_[a-f0-9]{24}", str(index.get("proposal_id") or ""))
        and index.get("content_free") is True
        and index.get("private_request_included") is False
        and index.get("private_path_included") is False
    )


def _write_intake_index(proposal: Mapping[str, Any], runtime_root: str | Path | None = None) -> None:
    intake_key = str(proposal.get("intake_key") or "")
    _atomic_json(_intake_index_path(intake_key, runtime_root), _intake_index_payload(proposal))


def _resolve_indexed_proposal(intake_key: str, runtime_root: str | Path | None = None) -> str:
    index = _read_json(_intake_index_path(intake_key, runtime_root))
    if index and _valid_intake_index(index, intake_key):
        proposal_id = str(index.get("proposal_id") or "")
        path = _proposal_path(proposal_id, runtime_root)
        if path.exists():
            proposal = _read_json(path)
            if proposal and _validate(proposal) and proposal.get("intake_key") == intake_key:
                return proposal_id
    directory = _store_root(runtime_root) / "proposals"
    if directory.exists():
        candidates = sorted(directory.glob("devc_*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
        for path in candidates:
            proposal = _read_json(path)
            if proposal and _validate(proposal) and proposal.get("intake_key") == intake_key:
                _write_intake_index(proposal, runtime_root)
                return str(proposal.get("proposal_id") or "")
    return ""


def _event(proposal: dict[str, Any], event_type: str, *, runtime_root: str | Path | None = None, details: Mapping[str, Any] | None = None) -> None:
    sequence = int(proposal.get("event_sequence") or 0) + 1
    proposal["event_sequence"] = sequence
    payload = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "proposal_id": proposal["proposal_id"],
        "revision": proposal["revision"],
        "revision_digest": proposal["revision_digest"],
        "sequence": sequence,
        "event_type": event_type,
        "created_at": _now(),
        "details": dict(details or {}),
        "content_free": True,
        "request_text_included": False,
        "private_path_included": False,
        "provider_contacted": False,
        "implementation_started": False,
        "source_modified": False,
        "authority_granted": False,
    }
    payload["event_digest"] = _digest(payload)
    _atomic_json(_event_path(proposal["proposal_id"], sequence, runtime_root), payload)


def _valid_approval_receipt(receipt: Mapping[str, Any], proposal: Mapping[str, Any]) -> bool:
    supplied = str(receipt.get("receipt_digest") or "")
    payload = {key: value for key, value in receipt.items() if key != "receipt_digest"}
    return bool(
        supplied
        and supplied == _digest(payload)
        and receipt.get("proposal_id") == proposal.get("proposal_id")
        and int(receipt.get("revision") or 0) == int(proposal.get("revision") or 0)
        and receipt.get("revision_digest") == proposal.get("revision_digest")
        and receipt.get("request_digest") == proposal.get("request_digest")
        and receipt.get("target_digest") == (proposal.get("target") or {}).get("target_digest")
        and receipt.get("intake_key") == proposal.get("intake_key")
        and receipt.get("approval_consumed_once") is True
        and receipt.get("content_free") is True
        and receipt.get("private_request_included") is False
        and receipt.get("private_path_included") is False
    )


def _reconcile_locked(proposal: dict[str, Any], *, runtime_root: str | Path | None = None) -> tuple[dict[str, Any], bool]:
    changed = False
    lifecycle_state = str(proposal.get("lifecycle_state") or "")
    receipt_required = lifecycle_state == "approval_processing" or lifecycle_state == "approved_pending_grounded_specification" or bool(proposal.get("approval_consumed"))
    if not receipt_required:
        return proposal, changed

    receipt = _read_json(_approval_path(proposal["proposal_id"], int(proposal["revision"]), runtime_root))
    receipt_valid = bool(receipt and _valid_approval_receipt(receipt, proposal))
    if receipt_valid:
        normalized = {
            "lifecycle_state": lifecycle_state if lifecycle_state in {"grounded_plan_ready", "unsupported_project_type"} else "approved_pending_grounded_specification",
            "approval_consumed": True,
            "approval_receipt_digest": receipt.get("receipt_digest", ""),
            "approval_consumption_count": 1,
            "planned_next_step": "Grounded project inspection and specification planning in v1200.4-v1200.6.",
        }
    elif lifecycle_state == "approval_processing" and not receipt:
        normalized = {
            "lifecycle_state": "awaiting_approval",
            "approval_consumed": False,
            "approval_receipt_digest": "",
            "approval_consumption_count": 0,
        }
    else:
        normalized = {
            "lifecycle_state": "approval_receipt_invalid",
            "approval_consumed": False,
            "approval_receipt_digest": "",
            "approval_consumption_count": 0,
            "planned_next_step": "Stop and require operator review of the missing or invalid approval receipt; do not consume another approval.",
        }

    for key, value in normalized.items():
        if proposal.get(key) != value:
            proposal[key] = value
            changed = True
    if changed:
        proposal["updated_at"] = _now()
    return proposal, changed


def create_or_resume_development_proposal(
    request: str,
    *,
    session_id: str = "",
    project_state: Mapping[str, Any] | None = None,
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    clean = _clean(request)
    if not clean:
        return {"ok": False, "status": "invalid_request", "reason": "empty_request"}
    request_digest = hashlib.sha256(clean.encode("utf-8")).hexdigest()
    target = _target(project_state)
    intake_key = _intake_key(request_digest, target["target_digest"])
    with _intake_lock(intake_key, runtime_root):
        indexed_proposal_id = _resolve_indexed_proposal(intake_key, runtime_root)
        if indexed_proposal_id:
            with _proposal_lock(indexed_proposal_id, runtime_root):
                path = _proposal_path(indexed_proposal_id, runtime_root)
                existing = _read_json(path)
                if not _validate(existing) or existing.get("intake_key") != intake_key:
                    return {"ok": False, "status": "tampered", "proposal_id": indexed_proposal_id}
                existing, changed = _reconcile_locked(existing, runtime_root=runtime_root)
                if changed:
                    _seal(existing)
                    _atomic_json(path, existing)
                    _write_intake_index(existing, runtime_root)
                existing["operation_status"] = "resumed"
                existing["deduplicated"] = True
                return existing

        proposal_id = _next_proposal_id(intake_key, runtime_root)
        with _proposal_lock(proposal_id, runtime_root):
            support = _support(clean)
            created = _now()
            proposal: dict[str, Any] = {
                "schema_version": SCHEMA_VERSION,
                "contract_version": CONTRACT_VERSION,
                "proposal_id": proposal_id,
                "revision": 1,
                "request": clean,
                "request_digest": request_digest,
                "intake_key": intake_key,
                "session_id": _clean(session_id, 200),
                "session_digest": hashlib.sha256(_clean(session_id, 200).encode("utf-8")).hexdigest() if session_id else "",
                "target": target,
                "supported": support["supported"],
                "support_status": support["support_status"],
                "limitation": support["limitation"],
                "risk_level": support["risk_level"],
                "risk_summary": "Workspace changes and test execution require separate later implementation stages." if support["supported"] else support["limitation"],
                "planned_next_step": (
                    "Wait for exact operator approval, then continue to grounded inspection and specification planning in v1200.4-v1200.6."
                    if support["supported"] else "Explain the limitation and wait for a narrower supported request."
                ),
                "approval_requirement": (
                    "One explicit approval bound to this exact proposal id and revision is required."
                    if support["supported"] else "Approval is unavailable while this proposal remains unsupported."
                ),
                "approval_required": bool(support["supported"]),
                "approval_consumed": False,
                "approval_receipt_digest": "",
                "approval_consumption_count": 0,
                "lifecycle_state": "awaiting_approval" if support["supported"] else "unsupported_request",
                "created_at": created,
                "updated_at": created,
                "event_sequence": 0,
                "provider_contacted": False,
                "model_contacted": False,
                "implementation_started": False,
                "workspace_created": False,
                "command_executed": False,
                "source_modified": False,
                "release_authorized": False,
                "authority_granted": False,
            }
            _seal(proposal)
            _event(proposal, "proposal_created", runtime_root=runtime_root, details={"support_status": proposal["support_status"]})
            _seal(proposal)
            _atomic_json(_proposal_path(proposal_id, runtime_root), proposal)
            _write_intake_index(proposal, runtime_root)
            proposal["operation_status"] = "created"
            proposal["deduplicated"] = False
            return proposal


def load_development_campaign_proposal(
    proposal_id: str, *, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    path = _proposal_path(proposal_id, runtime_root)
    if not path.exists():
        return {"ok": False, "status": "not_found", "proposal_id": proposal_id}
    with _proposal_lock(proposal_id, runtime_root):
        proposal = _read_json(path)
        if not _validate(proposal):
            return {"ok": False, "status": "tampered", "proposal_id": proposal_id}
        proposal, changed = _reconcile_locked(proposal, runtime_root=runtime_root)
        if changed:
            _seal(proposal)
            _atomic_json(path, proposal)
        return proposal


def revise_development_campaign_proposal(
    proposal_id: str,
    *,
    expected_revision: int,
    request: str | None = None,
    project_state: Mapping[str, Any] | None = None,
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    path = _proposal_path(proposal_id, runtime_root)
    if not path.exists():
        return {"ok": False, "status": "not_found", "proposal_id": proposal_id}
    initial = _read_json(path)
    if not _validate(initial):
        return {"ok": False, "status": "tampered", "proposal_id": proposal_id}
    clean = _clean(request if request is not None else initial.get("request"))
    if not clean:
        return {"ok": False, "status": "invalid_request", "reason": "empty_request", "proposal_id": proposal_id}
    target = _target(project_state) if project_state is not None else dict(initial.get("target") or {})
    request_digest = hashlib.sha256(clean.encode("utf-8")).hexdigest()
    new_intake_key = _intake_key(request_digest, str(target.get("target_digest") or ""))
    old_intake_key = str(initial.get("intake_key") or "")
    with ExitStack() as locks:
        for intake_key in sorted({old_intake_key, new_intake_key}):
            locks.enter_context(_intake_lock(intake_key, runtime_root))
        with _proposal_lock(proposal_id, runtime_root):
            proposal = _read_json(path)
            if not _validate(proposal):
                return {"ok": False, "status": "tampered", "proposal_id": proposal_id}
            proposal, _ = _reconcile_locked(proposal, runtime_root=runtime_root)
            if int(proposal.get("revision") or 0) != int(expected_revision):
                return {
                    "ok": False, "status": "stale_save_rejected", "proposal_id": proposal_id,
                    "expected_revision": int(expected_revision), "current_revision": int(proposal.get("revision") or 0),
                }
            current_old_intake_key = str(proposal.get("intake_key") or "")
            if current_old_intake_key != old_intake_key:
                return {
                    "ok": False, "status": "stale_save_rejected", "proposal_id": proposal_id,
                    "expected_revision": int(expected_revision), "current_revision": int(proposal.get("revision") or 0),
                }
            indexed_proposal_id = _resolve_indexed_proposal(new_intake_key, runtime_root)
            if indexed_proposal_id and indexed_proposal_id != proposal_id:
                return {
                    "ok": False,
                    "status": "revision_target_conflict",
                    "proposal_id": proposal_id,
                    "conflicting_proposal_id": indexed_proposal_id,
                    "current_revision": int(proposal.get("revision") or 0),
                }
            support = _support(clean)
            proposal.update({
                "revision": int(proposal["revision"]) + 1,
                "request": clean,
                "request_digest": request_digest,
                "intake_key": new_intake_key,
                "target": target,
                "supported": support["supported"],
                "support_status": support["support_status"],
                "limitation": support["limitation"],
                "risk_level": support["risk_level"],
                "risk_summary": "Workspace changes and test execution require separate later implementation stages." if support["supported"] else support["limitation"],
                "planned_next_step": (
                    "Wait for exact operator approval, then continue to grounded inspection and specification planning in v1200.4-v1200.6."
                    if support["supported"] else "Explain the limitation and wait for a narrower supported request."
                ),
                "approval_requirement": (
                    "One explicit approval bound to this exact proposal id and revision is required."
                    if support["supported"] else "Approval is unavailable while this proposal remains unsupported."
                ),
                "approval_required": bool(support["supported"]),
                "approval_consumed": False,
                "approval_receipt_digest": "",
                "approval_consumption_count": 0,
                "lifecycle_state": "awaiting_approval" if support["supported"] else "unsupported_request",
                "updated_at": _now(),
            })
            _seal(proposal)
            _event(proposal, "proposal_revised", runtime_root=runtime_root, details={"previous_revision": int(expected_revision)})
            _seal(proposal)
            _atomic_json(path, proposal)
            if old_intake_key != new_intake_key:
                old_index_path = _intake_index_path(old_intake_key, runtime_root)
                old_index = _read_json(old_index_path)
                if old_index and _valid_intake_index(old_index, old_intake_key) and old_index.get("proposal_id") == proposal_id:
                    old_index_path.unlink(missing_ok=True)
            _write_intake_index(proposal, runtime_root)
            return {**proposal, "ok": True, "status": "revised"}


def approve_development_campaign_proposal(
    proposal_id: str,
    *,
    revision: int,
    revision_digest: str = "",
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    path = _proposal_path(proposal_id, runtime_root)
    if not path.exists():
        return {"ok": False, "status": "not_found", "proposal_id": proposal_id}
    with _proposal_lock(proposal_id, runtime_root):
        proposal = _read_json(path)
        if not _validate(proposal):
            return {"ok": False, "status": "tampered", "proposal_id": proposal_id}
        proposal, changed = _reconcile_locked(proposal, runtime_root=runtime_root)
        if changed:
            _seal(proposal)
            _atomic_json(path, proposal)
        current_revision = int(proposal.get("revision") or 0)
        current_digest = str(proposal.get("revision_digest") or "")
        if current_revision != int(revision) or (revision_digest and revision_digest != current_digest):
            return {
                "ok": False, "status": "stale_approval_rejected", "proposal_id": proposal_id,
                "requested_revision": int(revision), "current_revision": current_revision,
                "current_revision_digest": current_digest,
            }
        if proposal.get("lifecycle_state") in {"rejected", "cancelled", "unsupported_request", "approval_receipt_invalid"}:
            return {"ok": False, "status": "approval_blocked", "reason": proposal.get("lifecycle_state"), "proposal_id": proposal_id}

        receipt_path = _approval_path(proposal_id, current_revision, runtime_root)
        existing = _read_json(receipt_path)
        if existing:
            if not _valid_approval_receipt(existing, proposal):
                return {
                    "ok": False,
                    "status": "approval_receipt_invalid",
                    "reason": "stored_receipt_failed_integrity_validation",
                    "proposal_id": proposal_id,
                    "approval_consumed_now": False,
                    "approval_consumption_count": 0,
                    "implementation_started": False,
                    "source_modified": False,
                    "authority_granted": False,
                }
            return {
                "ok": True,
                "status": "approval_already_consumed",
                "proposal_id": proposal_id,
                "revision": current_revision,
                "revision_digest": current_digest,
                "receipt_digest": existing.get("receipt_digest", ""),
                "approval_consumed_now": False,
                "approval_consumption_count": 1,
                "idempotent_replay": True,
                "implementation_started": False,
                "source_modified": False,
                "authority_granted": False,
            }

        proposal["lifecycle_state"] = "approval_processing"
        proposal["updated_at"] = _now()
        _seal(proposal)
        _atomic_json(path, proposal)
        receipt = {
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "proposal_id": proposal_id,
            "revision": current_revision,
            "revision_digest": current_digest,
            "request_digest": proposal.get("request_digest"),
            "target_digest": (proposal.get("target") or {}).get("target_digest"),
            "intake_key": proposal.get("intake_key"),
            "consumed_at": _now(),
            "approval_consumed_once": True,
            "implementation_authorized_for_current_bundle": False,
            "next_stage_authorized": "grounded_inspection_and_specification_planning",
            "provider_contacted": False,
            "model_contacted": False,
            "workspace_created": False,
            "command_executed": False,
            "source_modified": False,
            "release_authorized": False,
            "authority_granted": False,
            "content_free": True,
            "private_request_included": False,
            "private_path_included": False,
        }
        receipt["receipt_digest"] = _digest(receipt)
        _atomic_json(receipt_path, receipt)
        proposal.update({
            "lifecycle_state": "approved_pending_grounded_specification",
            "approval_consumed": True,
            "approval_receipt_digest": receipt["receipt_digest"],
            "approval_consumption_count": 1,
            "planned_next_step": "Grounded project inspection and specification planning in v1200.4-v1200.6.",
            "updated_at": _now(),
        })
        _seal(proposal)
        _event(proposal, "approval_consumed", runtime_root=runtime_root, details={"receipt_digest": receipt["receipt_digest"]})
        _seal(proposal)
        _atomic_json(path, proposal)
        return {
            "ok": True,
            "status": "approval_consumed",
            "proposal_id": proposal_id,
            "revision": current_revision,
            "revision_digest": current_digest,
            "receipt_digest": receipt["receipt_digest"],
            "approval_consumed_now": True,
            "approval_consumption_count": 1,
            "idempotent_replay": False,
            "implementation_started": False,
            "source_modified": False,
            "authority_granted": False,
        }


def _terminal_decision(
    proposal_id: str,
    *,
    revision: int,
    decision: str,
    revision_digest: str = "",
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    if decision not in {"rejected", "cancelled"}:
        raise ValueError("Invalid proposal decision.")
    path = _proposal_path(proposal_id, runtime_root)
    if not path.exists():
        return {"ok": False, "status": "not_found", "proposal_id": proposal_id}
    with _proposal_lock(proposal_id, runtime_root):
        proposal = _read_json(path)
        if not _validate(proposal):
            return {"ok": False, "status": "tampered", "proposal_id": proposal_id}
        current_revision = int(proposal.get("revision") or 0)
        current_digest = str(proposal.get("revision_digest") or "")
        if current_revision != int(revision) or (revision_digest and revision_digest != current_digest):
            return {
                "ok": False, "status": "stale_decision_rejected", "proposal_id": proposal_id,
                "requested_revision": int(revision), "current_revision": current_revision,
            }
        if proposal.get("approval_consumed"):
            return {"ok": False, "status": "decision_blocked", "reason": "approval_already_consumed", "proposal_id": proposal_id}
        if proposal.get("lifecycle_state") == decision:
            return {"ok": True, "status": f"already_{decision}", "proposal_id": proposal_id, "idempotent_replay": True}
        if proposal.get("lifecycle_state") not in {"awaiting_approval", "unsupported_request"}:
            return {"ok": False, "status": "decision_blocked", "reason": proposal.get("lifecycle_state"), "proposal_id": proposal_id}
        proposal["lifecycle_state"] = decision
        proposal["planned_next_step"] = "No further work is permitted unless the operator submits a new or revised request."
        proposal["updated_at"] = _now()
        _seal(proposal)
        _event(proposal, decision, runtime_root=runtime_root)
        _seal(proposal)
        _atomic_json(path, proposal)
        return {"ok": True, "status": decision, "proposal_id": proposal_id, "revision": current_revision, "idempotent_replay": False}


def reject_development_campaign_proposal(
    proposal_id: str, *, revision: int, revision_digest: str = "", runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    return _terminal_decision(proposal_id, revision=revision, decision="rejected", revision_digest=revision_digest, runtime_root=runtime_root)


def cancel_development_campaign_proposal(
    proposal_id: str, *, revision: int, revision_digest: str = "", runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    return _terminal_decision(proposal_id, revision=revision, decision="cancelled", revision_digest=revision_digest, runtime_root=runtime_root)


def public_development_campaign_proposal(proposal: Mapping[str, Any]) -> dict[str, Any]:
    target = dict(proposal.get("target") or {})
    return {
        "schema_version": proposal.get("schema_version", SCHEMA_VERSION),
        "contract_version": proposal.get("contract_version", CONTRACT_VERSION),
        "proposal_id": proposal.get("proposal_id", ""),
        "revision": int(proposal.get("revision") or 0),
        "revision_digest": proposal.get("revision_digest", ""),
        "proposal_digest": proposal.get("proposal_digest", ""),
        "request_digest": proposal.get("request_digest", ""),
        "target": {
            "mode": target.get("mode", "isolated_workspace"),
            "project_name_digest": hashlib.sha256(str(target.get("project_name") or "").encode("utf-8")).hexdigest() if target.get("project_name") else "",
            "project_id_digest": hashlib.sha256(str(target.get("project_id") or "").encode("utf-8")).hexdigest() if target.get("project_id") else "",
            "path_digest": target.get("path_digest", ""),
            "target_digest": target.get("target_digest", ""),
        },
        "supported": bool(proposal.get("supported")),
        "support_status": proposal.get("support_status", ""),
        "limitation": proposal.get("limitation", ""),
        "risk_level": proposal.get("risk_level", "unknown"),
        "risk_summary": proposal.get("risk_summary", ""),
        "planned_next_step": proposal.get("planned_next_step", ""),
        "approval_requirement": proposal.get("approval_requirement", ""),
        "approval_required": bool(proposal.get("approval_required")),
        "approval_consumed": bool(proposal.get("approval_consumed")),
        "approval_receipt_digest": proposal.get("approval_receipt_digest", ""),
        "approval_consumption_count": int(proposal.get("approval_consumption_count") or 0),
        "lifecycle_state": proposal.get("lifecycle_state", ""),
        "grounded_plan_digest": proposal.get("grounded_plan_digest", ""),
        "project_snapshot_digest": proposal.get("project_snapshot_digest", ""),
        "created_at": proposal.get("created_at", ""),
        "updated_at": proposal.get("updated_at", ""),
        "provider_contacted": False,
        "model_contacted": False,
        "implementation_started": False,
        "workspace_created": False,
        "command_executed": False,
        "source_modified": False,
        "release_authorized": False,
        "authority_granted": False,
        "content_free_public_projection": True,
        "private_request_included": False,
        "private_path_included": False,
    }


def list_development_campaign_proposals(
    *, runtime_root: str | Path | None = None, public: bool = True, limit: int = 50,
) -> dict[str, Any]:
    directory = _store_root(runtime_root) / "proposals"
    rows: list[dict[str, Any]] = []
    recovery_preview_count = 0
    if directory.exists():
        for path in sorted(directory.glob("devc_*.json"), key=lambda item: item.stat().st_mtime, reverse=True)[:max(1, min(int(limit), 200))]:
            proposal = _read_json(path)
            if not proposal or not _validate(proposal):
                continue
            preview = dict(proposal)
            preview, recovered = _reconcile_locked(preview, runtime_root=runtime_root)
            recovery_preview_count += int(recovered)
            if public:
                public_row = public_development_campaign_proposal(preview)
                try:
                    from grounded_development_planning import load_grounded_plan, public_grounded_plan
                    grounded = load_grounded_plan(
                        str(preview.get("proposal_id") or ""),
                        int(preview.get("revision") or 0),
                        runtime_root=runtime_root,
                    )
                    if grounded:
                        public_row["grounded_planning"] = public_grounded_plan(grounded)
                except Exception:
                    public_row["grounded_planning"] = {"ok": False, "status": "grounded_plan_projection_unavailable"}
                try:
                    from small_website_implementation_checkpoint import load_small_website_checkpoint, public_small_website_checkpoint
                    checkpoint = load_small_website_checkpoint(
                        str(preview.get("proposal_id") or ""),
                        int(preview.get("revision") or 0),
                        runtime_root,
                    )
                    if checkpoint:
                        public_checkpoint = public_small_website_checkpoint(checkpoint)
                        public_row["small_website_checkpoint"] = public_checkpoint
                        if public_checkpoint.get("checkpoint_digest"):
                            public_row["current_stage"] = "small_website_checkpoint_ready"
                            public_row["provider_contacted"] = True
                            public_row["implementation_started"] = True
                            public_row["workspace_created"] = True
                            public_row["command_executed"] = int((public_checkpoint.get("test_summary") or {}).get("command_count") or 0) > 0
                            public_row["tests_executed"] = True
                except Exception:
                    public_row["small_website_checkpoint"] = {"ok": False, "status": "checkpoint_projection_unavailable"}
                try:
                    from javascript_tool_test_execution_checkpoint import load_javascript_tool_test_checkpoint, public_javascript_tool_test_checkpoint
                    tested_checkpoint = load_javascript_tool_test_checkpoint(
                        str(preview.get("proposal_id") or ""),
                        int(preview.get("revision") or 0),
                        runtime_root,
                    )
                    if tested_checkpoint:
                        public_tested = public_javascript_tool_test_checkpoint(tested_checkpoint)
                        public_row["javascript_tool_test_checkpoint"] = public_tested
                        if public_tested.get("checkpoint_digest"):
                            public_row["current_stage"] = "javascript_tool_tests_ready"
                            public_row["provider_contacted"] = True
                            public_row["implementation_started"] = True
                            public_row["workspace_created"] = True
                            public_row["command_executed"] = True
                            public_row["tests_executed"] = True
                except Exception:
                    public_row["javascript_tool_test_checkpoint"] = {"ok": False, "status": "checkpoint_projection_unavailable"}
                try:
                    from javascript_tool_result_disposition import (
                        _packet_path as _js_review_packet_path,
                        load_javascript_tool_disposition,
                        public_javascript_tool_disposition,
                        public_javascript_tool_review_packet,
                    )
                    review_packet = _read_json(_js_review_packet_path(
                        str(preview.get("proposal_id") or ""),
                        int(preview.get("revision") or 0),
                        runtime_root,
                    )) or {}
                    if review_packet:
                        public_row["javascript_tool_review_packet"] = public_javascript_tool_review_packet(review_packet)
                        public_row["current_stage"] = "javascript_tool_result_awaiting_disposition"
                    disposition = load_javascript_tool_disposition(
                        str(preview.get("proposal_id") or ""),
                        int(preview.get("revision") or 0),
                        runtime_root,
                    )
                    if disposition:
                        public_row["javascript_tool_disposition"] = public_javascript_tool_disposition(disposition)
                        public_row["current_stage"] = str(disposition.get("status") or "javascript_tool_disposition_recorded")
                except Exception:
                    public_row["javascript_tool_review_packet"] = {"ok": False, "status": "review_projection_unavailable"}
                try:
                    from javascript_tool_implementation_checkpoint import (
                        load_javascript_tool_implementation_checkpoint,
                        public_javascript_tool_implementation_checkpoint,
                    )
                    final_checkpoint = load_javascript_tool_implementation_checkpoint(
                        str(preview.get("proposal_id") or ""),
                        int(preview.get("revision") or 0),
                        runtime_root,
                    )
                    if final_checkpoint:
                        public_final = public_javascript_tool_implementation_checkpoint(final_checkpoint)
                        public_row["javascript_tool_implementation_checkpoint"] = public_final
                        public_row["implementation_checkpoint_stage"] = str(public_final.get("status") or "javascript_tool_implementation_checkpoint_ready")
                        if not public_row.get("javascript_tool_disposition"):
                            public_row["current_stage"] = public_row["implementation_checkpoint_stage"]
                        public_row["provider_contacted"] = True
                        public_row["implementation_started"] = True
                        public_row["workspace_created"] = not bool(public_final.get("workspace_discarded"))
                        public_row["command_executed"] = True
                        public_row["tests_executed"] = True
                except Exception:
                    public_row["javascript_tool_implementation_checkpoint"] = {"ok": False, "status": "final_checkpoint_projection_unavailable"}
                try:
                    from javascript_tool_implementation_foundations import load_javascript_tool_checkpoint, public_javascript_tool_checkpoint
                    js_checkpoint = load_javascript_tool_checkpoint(
                        str(preview.get("proposal_id") or ""),
                        int(preview.get("revision") or 0),
                        runtime_root,
                    )
                    if js_checkpoint:
                        public_js = public_javascript_tool_checkpoint(js_checkpoint)
                        public_row["javascript_tool_checkpoint"] = public_js
                        if public_js.get("checkpoint_digest"):
                            if not public_row.get("javascript_tool_disposition") and not public_row.get("javascript_tool_review_packet"):
                                public_row["current_stage"] = "javascript_tool_checkpoint_ready"
                            public_row["provider_contacted"] = True
                            public_row["implementation_started"] = True
                            public_row["workspace_created"] = True
                            public_row["command_executed"] = int((public_js.get("test_summary") or {}).get("command_count") or 0) > 0
                            public_row["tests_executed"] = True
                except Exception:
                    public_row["javascript_tool_checkpoint"] = {"ok": False, "status": "checkpoint_projection_unavailable"}
                try:
                    from python_cli_test_execution_checkpoint import load_python_cli_test_checkpoint, public_python_cli_test_checkpoint
                    py_checkpoint = load_python_cli_test_checkpoint(str(preview.get("proposal_id") or ""), int(preview.get("revision") or 0), runtime_root)
                    if py_checkpoint:
                        public_py = public_python_cli_test_checkpoint(py_checkpoint)
                        public_row["python_cli_test_checkpoint"] = public_py
                        if public_py.get("checkpoint_digest"):
                            public_row["current_stage"] = "python_cli_tests_ready"
                            public_row["provider_contacted"] = True
                            public_row["implementation_started"] = True
                            public_row["workspace_created"] = True
                            public_row["command_executed"] = True
                            public_row["tests_executed"] = True
                except Exception:
                    public_row["python_cli_test_checkpoint"] = {"ok": False, "status": "checkpoint_projection_unavailable"}
                try:
                    from python_cli_result_disposition import _packet_path as _py_review_packet_path, load_python_cli_disposition, public_python_cli_disposition, public_python_cli_review_packet
                    py_packet = _read_json(_py_review_packet_path(str(preview.get("proposal_id") or ""), int(preview.get("revision") or 0), runtime_root)) or {}
                    if py_packet:
                        public_row["python_cli_review_packet"] = public_python_cli_review_packet(py_packet)
                        public_row["current_stage"] = "python_cli_result_awaiting_disposition"
                    py_disposition = load_python_cli_disposition(str(preview.get("proposal_id") or ""), int(preview.get("revision") or 0), runtime_root)
                    if py_disposition:
                        public_row["python_cli_disposition"] = public_python_cli_disposition(py_disposition)
                        public_row["current_stage"] = str(py_disposition.get("status") or "python_cli_disposition_recorded")
                except Exception:
                    public_row["python_cli_review_packet"] = {"ok": False, "status": "review_projection_unavailable"}
                try:
                    from python_cli_implementation_checkpoint import (
                        load_python_cli_implementation_checkpoint,
                        public_python_cli_implementation_checkpoint,
                    )
                    py_final_checkpoint = load_python_cli_implementation_checkpoint(
                        str(preview.get("proposal_id") or ""),
                        int(preview.get("revision") or 0),
                        runtime_root,
                    )
                    if py_final_checkpoint:
                        public_py_final = public_python_cli_implementation_checkpoint(py_final_checkpoint)
                        public_row["python_cli_implementation_checkpoint"] = public_py_final
                        public_row["implementation_checkpoint_stage"] = str(public_py_final.get("status") or "python_cli_implementation_checkpoint_ready")
                        public_row["current_stage"] = public_row["implementation_checkpoint_stage"]
                        public_row["provider_contacted"] = True
                        public_row["implementation_started"] = True
                        public_row["workspace_created"] = not bool(public_py_final.get("workspace_discarded"))
                        public_row["command_executed"] = True
                        public_row["tests_executed"] = True
                except Exception:
                    public_row["python_cli_implementation_checkpoint"] = {"ok": False, "status": "final_checkpoint_projection_unavailable"}
                try:
                    from selected_project_apply import (
                        _request_path as _selected_apply_request_path,
                        _result_path as _selected_apply_result_path,
                        _rollback_request_path as _selected_rollback_request_path,
                        _rollback_result_path as _selected_rollback_result_path,
                        public_apply_record,
                        public_rollback_record,
                    )
                    selected_apply_request = _read_json(_selected_apply_request_path(
                        str(preview.get("proposal_id") or ""), int(preview.get("revision") or 0), runtime_root
                    )) or {}
                    selected_apply_result = _read_json(_selected_apply_result_path(
                        str(preview.get("proposal_id") or ""), int(preview.get("revision") or 0), runtime_root
                    )) or {}
                    selected_rollback_request = _read_json(_selected_rollback_request_path(
                        str(preview.get("proposal_id") or ""), int(preview.get("revision") or 0), runtime_root
                    )) or {}
                    selected_rollback_result = _read_json(_selected_rollback_result_path(
                        str(preview.get("proposal_id") or ""), int(preview.get("revision") or 0), runtime_root
                    )) or {}
                    if selected_apply_request:
                        public_row["selected_project_apply_request"] = public_apply_record(selected_apply_request)
                    if selected_apply_result:
                        public_row["selected_project_apply_result"] = public_apply_record(selected_apply_result)
                        public_row["current_stage"] = str(selected_apply_result.get("status") or "selected_project_apply_recorded")
                    if selected_rollback_request:
                        public_row["selected_project_rollback_request"] = public_rollback_record(selected_rollback_request)
                    if selected_rollback_result:
                        public_row["selected_project_rollback_result"] = public_rollback_record(selected_rollback_result)
                        public_row["current_stage"] = str(selected_rollback_result.get("status") or "selected_project_rollback_recorded")
                except Exception:
                    public_row["selected_project_apply_projection"] = {"ok": False, "status": "selected_project_projection_unavailable"}
                try:
                    from general_small_project_implementation_checkpoint import (
                        load_general_small_project_implementation_checkpoint,
                        public_general_small_project_implementation_checkpoint,
                    )
                    general_checkpoint = load_general_small_project_implementation_checkpoint(
                        str(preview.get("proposal_id") or ""), int(preview.get("revision") or 0), runtime_root
                    )
                    if general_checkpoint:
                        public_general_checkpoint = public_general_small_project_implementation_checkpoint(general_checkpoint)
                        public_row["general_small_project_implementation_checkpoint"] = public_general_checkpoint
                        public_row["current_stage"] = str(public_general_checkpoint.get("status") or "general_small_project_implementation_checkpoint_ready")
                        public_row["provider_contacted"] = bool(public_general_checkpoint.get("provider_contacted"))
                        public_row["implementation_started"] = True
                        public_row["conversation_command_distinction_audit_status"] = str(public_general_checkpoint.get("conversation_command_distinction_audit_status") or "")
                except Exception:
                    public_row["general_small_project_implementation_checkpoint"] = {"ok": False, "status": "general_small_project_checkpoint_projection_unavailable"}
                try:
                    from browser_runtime_test_adapter import (
                        _runtime_test_path,
                        public_browser_runtime_test,
                    )
                    browser_runtime = _read_json(_runtime_test_path(
                        str(preview.get("proposal_id") or ""), int(preview.get("revision") or 0), runtime_root
                    )) or {}
                    if browser_runtime:
                        public_browser = public_browser_runtime_test(browser_runtime)
                        public_row["browser_runtime_test"] = public_browser
                        public_row["current_stage"] = str(public_browser.get("status") or "browser_runtime_test_recorded")
                        public_row["command_executed"] = bool(public_browser.get("browser_executed"))
                        public_row["tests_executed"] = True
                except Exception:
                    public_row["browser_runtime_test"] = {"ok": False, "status": "browser_runtime_projection_unavailable"}
                try:
                    from browser_runtime_test_adapter_checkpoint import (
                        load_browser_runtime_test_adapter_checkpoint,
                        public_browser_runtime_test_adapter_checkpoint,
                    )
                    browser_checkpoint = load_browser_runtime_test_adapter_checkpoint(
                        str(preview.get("proposal_id") or ""), int(preview.get("revision") or 0), runtime_root
                    )
                    if browser_checkpoint:
                        public_browser_checkpoint = public_browser_runtime_test_adapter_checkpoint(browser_checkpoint)
                        public_row["browser_runtime_test_adapter_checkpoint"] = public_browser_checkpoint
                        public_row["current_stage"] = str(public_browser_checkpoint.get("status") or "browser_runtime_adapter_checkpoint_ready")
                        public_row["command_executed"] = bool(public_browser_checkpoint.get("browser_executed"))
                        public_row["tests_executed"] = True
                except Exception:
                    public_row["browser_runtime_test_adapter_checkpoint"] = {"ok": False, "status": "browser_runtime_checkpoint_projection_unavailable"}
                try:
                    from node_javascript_test_adapter import _result_path as _node_test_result_path, public_node_javascript_test_result
                    node_result = _read_json(_node_test_result_path(
                        str(preview.get("proposal_id") or ""), int(preview.get("revision") or 0), runtime_root
                    )) or {}
                    if node_result:
                        public_node_result = public_node_javascript_test_result(node_result)
                        public_row["node_javascript_test_result"] = public_node_result
                        public_row["current_stage"] = str(public_node_result.get("status") or "node_javascript_test_recorded")
                        public_row["command_executed"] = bool(public_node_result.get("node_executed"))
                        public_row["tests_executed"] = True
                except Exception:
                    public_row["node_javascript_test_result"] = {"ok": False, "status": "node_javascript_test_projection_unavailable"}
                try:
                    from node_javascript_test_adapter_checkpoint import (
                        load_node_javascript_test_adapter_checkpoint,
                        public_node_javascript_test_adapter_checkpoint,
                    )
                    node_checkpoint = load_node_javascript_test_adapter_checkpoint(
                        str(preview.get("proposal_id") or ""), int(preview.get("revision") or 0), runtime_root
                    )
                    if node_checkpoint:
                        public_node_checkpoint = public_node_javascript_test_adapter_checkpoint(node_checkpoint)
                        public_row["node_javascript_test_adapter_checkpoint"] = public_node_checkpoint
                        public_row["current_stage"] = str(public_node_checkpoint.get("status") or "node_javascript_test_adapter_checkpoint_ready")
                        public_row["command_executed"] = bool(public_node_checkpoint.get("node_executed"))
                        public_row["tests_executed"] = True
                except Exception:
                    public_row["node_javascript_test_adapter_checkpoint"] = {"ok": False, "status": "node_javascript_checkpoint_projection_unavailable"}
                try:
                    from python_test_adapter import _result_path as _python_adapter_result_path, public_python_test_result
                    python_result = _read_json(_python_adapter_result_path(str(preview.get("proposal_id") or ""), int(preview.get("revision") or 0), runtime_root)) or {}
                    if python_result:
                        public_python_result = public_python_test_result(python_result)
                        public_row["python_test_adapter_result"] = public_python_result
                        public_row["current_stage"] = str(public_python_result.get("status") or "python_test_adapter_recorded")
                        public_row["command_executed"] = bool(public_python_result.get("python_executed")); public_row["tests_executed"] = True
                except Exception:
                    public_row["python_test_adapter_result"] = {"ok": False, "status": "python_test_adapter_projection_unavailable"}
                try:
                    from python_test_adapter_checkpoint import load_python_test_adapter_checkpoint, public_python_test_adapter_checkpoint
                    python_adapter_checkpoint = load_python_test_adapter_checkpoint(str(preview.get("proposal_id") or ""), int(preview.get("revision") or 0), runtime_root)
                    if python_adapter_checkpoint:
                        public_python_adapter_checkpoint = public_python_test_adapter_checkpoint(python_adapter_checkpoint)
                        public_row["python_test_adapter_checkpoint"] = public_python_adapter_checkpoint
                        public_row["current_stage"] = str(public_python_adapter_checkpoint.get("status") or "python_test_adapter_checkpoint_ready")
                        public_row["command_executed"] = bool(public_python_adapter_checkpoint.get("python_executed")); public_row["tests_executed"] = True
                except Exception:
                    public_row["python_test_adapter_checkpoint"] = {"ok": False, "status": "python_test_checkpoint_projection_unavailable"}
                try:
                    from selected_project_apply_rollback_checkpoint import (
                        load_selected_project_apply_rollback_checkpoint,
                        public_selected_project_apply_rollback_checkpoint,
                    )
                    selected_checkpoint = load_selected_project_apply_rollback_checkpoint(
                        str(preview.get("proposal_id") or ""), int(preview.get("revision") or 0), runtime_root
                    )
                    if selected_checkpoint:
                        public_selected_checkpoint = public_selected_project_apply_rollback_checkpoint(selected_checkpoint)
                        public_row["selected_project_apply_rollback_checkpoint"] = public_selected_checkpoint
                        public_row["current_stage"] = str(public_selected_checkpoint.get("status") or "selected_project_checkpoint_ready")
                        public_row["selected_project_modified"] = bool(public_selected_checkpoint.get("selected_project_modified"))
                        public_row["implementation_applied"] = bool(public_selected_checkpoint.get("implementation_applied"))
                except Exception:
                    public_row["selected_project_apply_rollback_checkpoint"] = {"ok": False, "status": "selected_project_checkpoint_projection_unavailable"}
                rows.append(public_row)
            else:
                rows.append(preview)
    return {
        "ok": True,
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "proposal_count": len(rows),
        "proposals": rows,
        "runtime_data_external": True,
        "public_projection_content_free": bool(public),
        "recovery_preview_count": recovery_preview_count,
        "recovery_preview_persisted": False,
        "provider_contacted": False,
        "implementation_started": False,
        "source_modified": False,
        "authority_granted": False,
    }


def _conversation_text(result: Mapping[str, Any]) -> str:
    event = str(result.get("event") or "")
    proposal = dict(result.get("proposal") or {})
    if event in {"proposal_created", "proposal_resumed"}:
        state = str(proposal.get("lifecycle_state") or "")
        proposal_id = str(proposal.get("proposal_id") or "")
        revision = int(proposal.get("revision") or 0)
        if state == "unsupported_request":
            return (
                f"I recorded development proposal {proposal_id} revision {revision}, but it is unsupported in the current supervised scope. "
                f"{proposal.get('limitation', '')} No provider, files, commands, or source changes were used."
            ).strip()
        if state == "approved_pending_grounded_specification":
            return (
                f"I resumed development proposal {proposal_id} revision {revision}. Its approval remains consumed exactly once. "
                "No implementation has started; the next permitted stage is grounded inspection and specification planning."
            )
        if state in {"rejected", "cancelled"}:
            return (
                f"I resumed development proposal {proposal_id} revision {revision}, which is {state}. "
                "No further work is permitted unless you submit a new or revised request."
            )
        if state == "approval_receipt_invalid":
            return (
                f"I resumed development proposal {proposal_id} revision {revision}, but its approval receipt failed integrity validation. "
                "The proposal is blocked for operator review; no approval was consumed again and no implementation started."
            )
        verb = "created" if event == "proposal_created" else "resumed"
        return (
            f"I {verb} supervised development proposal {proposal_id} revision {revision}. "
            f"Risk is {proposal.get('risk_level', 'medium')}; the target is {((proposal.get('target') or {}).get('mode') or 'isolated_workspace').replace('_', ' ')}. "
            "No implementation, provider generation, workspace creation, command execution, or source change has occurred. "
            f"To approve this exact revision, reply: Approve development proposal {proposal_id} revision {revision}."
        )
    if event == "approval_consumed":
        planning = dict(result.get("grounded_planning") or {})
        if planning.get("planning_status") == "grounded_plan_ready":
            return (
                f"Approval was consumed exactly once for proposal {result.get('proposal_id')} revision {result.get('revision')}. "
                f"Grounded read-only planning is ready for a {planning.get('project_kind', 'small project')} with "
                f"{planning.get('inspected_file_count', 0)} inspected files, {planning.get('planned_file_count', 0)} planned changes, "
                f"and test adapters: {', '.join(planning.get('test_adapters') or []) or 'none'}. "
                "No provider generation, commands, implementation files, or selected-project changes occurred."
            )
        return (
            f"Approval was consumed exactly once for proposal {result.get('proposal_id')} revision {result.get('revision')}. "
            "No implementation started. Grounded planning could not complete automatically; the proposal remains safely paused for review."
        )
    if event == "approval_replayed":
        return (
            f"Proposal {result.get('proposal_id')} revision {result.get('revision')} was already approved. "
            "The approval was not consumed again, and no implementation started."
        )
    if event == "stale_control_rejected":
        return "That control referenced a stale proposal revision, so it was rejected without consuming approval or changing files."
    if event in {"cancelled", "rejected"}:
        return f"Development proposal {result.get('proposal_id')} revision {result.get('revision')} is now {event}. No implementation started."
    if event == "control_blocked":
        return f"The proposal control was blocked: {result.get('reason', 'current lifecycle state does not allow it')}."
    return ""


def process_ordinary_chat_development_turn(
    user_text: str,
    *,
    action_projection: Mapping[str, Any] | None = None,
    session_id: str = "",
    project_state: Mapping[str, Any] | None = None,
    runtime_root: str | Path | None = None,
    provider_generate=None,
    node_executable: str | None = None,
    python_executable: str | None = None,
    chromium_executable: str | None = None,
) -> dict[str, Any]:
    text = _clean(user_text)
    normalized_control = text.strip().lower()

    # v2401-v2499 Era 10 product-maturity / bounded-autonomy controls.
    # These are exact, read-only projections only. They cannot execute background
    # work, tools, install/promote candidates, certify v2500, or expand authority.
    try:
        from era10_product_autonomy import process_era10_control
        era10_state = process_era10_control(text, runtime_root=runtime_root)
        if era10_state.get("active"):
            return era10_state
    except Exception:
        pass

    # v2301-v2399 Era 9 learning/personalization/collaboration/self-model
    # controls. These are exact, read-only projections over retained owners and
    # cannot train, merge, execute, install, promote, or expand authority.
    try:
        from era9_learning_collaboration_self_model import process_era9_control
        era9_state = process_era9_control(text, runtime_root=runtime_root)
        if era9_state.get("active"):
            return era9_state
    except Exception:
        pass

    # v2201-v2299 Era 8 security/recovery/audit controls. These are exact,
    # read-only status surfaces over retained authority/recovery owners and the
    # new portable coordination layer. They never execute tools, disable OS
    # capabilities, notify externally, recover active source, or grant broader
    # authority through ordinary chat.
    try:
        from era8_trustworthy_operation import process_era8_trust_control
        era8_trust = process_era8_trust_control(text, runtime_root=runtime_root)
        if era8_trust.get("active"):
            return era8_trust
    except Exception:
        pass

    # v2101-v2199 Era 7 tools/research/voice/multimodal controls. These
    # surfaces inspect contracts and prepare evidence/packets only. They never
    # execute tools, browse, contact providers, capture devices, or grant
    # install/promotion authority through ordinary chat.
    try:
        from era7_interaction_intelligence import process_era7_interaction_control
        era7_interaction = process_era7_interaction_control(text, runtime_root=runtime_root)
        if era7_interaction.get("active"):
            return era7_interaction
    except Exception:
        pass

    # v2001-v2099 Era 6 attention/initiative controls. These are exact,
    # read-only inspection surfaces over retained attention/proactive owners and
    # never launch background work, deliver messages, contact providers, or
    # grant execution/install authority.
    try:
        from era6_attention_initiative import process_era6_attention_control
        era6_attention = process_era6_attention_control(text, runtime_root=runtime_root)
        if era6_attention.get("active"):
            return era6_attention
    except Exception:
        pass

    # v1901-v1999 Era 5 companion-coherence controls.  These inspection-only
    # surfaces reuse the ordinary-chat authority boundary and never initiate a
    # new turn, mutate personality, or grant execution/install authority.
    try:
        from era5_companion_coherence import process_era5_companion_control
        era5_companion = process_era5_companion_control(text, runtime_root=runtime_root)
        if era5_companion.get("active"):
            return era5_companion
    except Exception:
        pass

    # v1801-v1899 Era 4 memory/world-model controls. These are exact, read-only
    # or proposal-only surfaces over the canonical memory owner and never grant
    # browsing, refresh completion, memory mutation, or execution authority.
    try:
        from memory_world_model_controls import process_memory_world_model_control
        era4_memory = process_memory_world_model_control(text)
        if era4_memory.get("active"):
            return era4_memory
    except Exception:
        pass

    # v1701-v1799 Era 3 portable cognition controls.  These surfaces are
    # deliberately read-only/bookkeeping-only and import lazily so they reuse
    # the retained ordinary-chat authority boundary instead of creating a
    # second command router.
    try:
        from problem_framing_intelligence import process_problem_framing_control
        era3_problem = process_problem_framing_control(text, project_evidence=project_state, runtime_root=runtime_root)
        if era3_problem.get("active"):
            return era3_problem
    except Exception:
        pass
    try:
        from causal_counterfactual_intelligence import process_causal_reasoning_control
        era3_causal = process_causal_reasoning_control(text, runtime_root=runtime_root)
        if era3_causal.get("active"):
            return era3_causal
    except Exception:
        pass
    try:
        from long_horizon_planning_intelligence import process_long_horizon_planning_control
        era3_plan = process_long_horizon_planning_control(text, runtime_root=runtime_root)
        if era3_plan.get("active"):
            return era3_plan
    except Exception:
        pass
    try:
        from epistemic_self_correction import process_epistemic_self_correction_control
        era3_meta = process_epistemic_self_correction_control(text, runtime_root=runtime_root)
        if era3_meta.get("active"):
            return era3_meta
    except Exception:
        pass
    if normalized_control in {"show data migration task", "inspect data migration task", "show gamma migration"}:
        try:
            from representative_data_migration_task import process_data_migration_task_control
            c = process_data_migration_task_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show refactoring task", "inspect refactoring task", "show gamma refactor"}:
        try:
            from representative_refactoring_task import process_refactoring_task_control
            c = process_refactoring_task_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show bug report task", "inspect bug report task", "show gamma bug repair"}:
        try:
            from representative_bug_report_task import process_bug_report_task_control
            c = process_bug_report_task_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show existing project feature", "inspect existing project feature", "show gamma feature task"}:
        try:
            from representative_existing_project_feature import process_existing_project_feature_control
            c = process_existing_project_feature_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show greenfield task", "inspect greenfield task", "show calculator task"}:
        try:
            from representative_greenfield_task import process_greenfield_task_control
            c = process_greenfield_task_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show self modification checkpoint", "inspect self modification checkpoint", "show self modification status"}:
        try:
            from self_modification_checkpoint import process_self_modification_checkpoint_control
            c = process_self_modification_checkpoint_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show update lineage", "inspect update lineage", "show self update lineage"}:
        try:
            from update_lineage import process_update_lineage_control
            c = process_update_lineage_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show self update transaction", "inspect self rollback", "show automatic self rollback"}:
        try:
            from automatic_self_rollback import process_automatic_self_rollback_control
            c = process_automatic_self_rollback_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show canary self update", "inspect canary self update", "show self update canary"}:
        try:
            from canary_self_update import process_canary_self_update_control
            c = process_canary_self_update_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show shadow execution", "inspect shadow execution", "show shadow comparison"}:
        try:
            from shadow_execution import process_shadow_execution_control
            c = process_shadow_execution_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show dogfood verification", "inspect dogfood verification", "show self verification"}:
        try:
            from dogfood_verification import process_dogfood_verification_control
            c = process_dogfood_verification_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show protected core", "inspect protected core", "show protected boundaries"}:
        try:
            from protected_core import process_protected_core_control
            c = process_protected_core_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show self change isolation", "inspect self change isolation", "show self change workspace"}:
        try:
            from self_change_isolation import process_self_change_isolation_control
            c = process_self_change_isolation_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show self improvement backlog", "inspect self improvement backlog", "show improvement backlog"}:
        try:
            from self_improvement_backlog import process_self_improvement_backlog_control
            c = process_self_improvement_backlog_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show self model", "inspect self model", "show eidolon self model"}:
        try:
            from self_model_map import process_self_model_control
            c = process_self_model_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show durable campaign checkpoint", "inspect durable campaign checkpoint", "show campaign checkpoint"}:
        try:
            from durable_campaign_checkpoint import process_durable_campaign_checkpoint_control
            c = process_durable_campaign_checkpoint_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show campaign continuity", "inspect campaign continuity", "show multi day continuity"}:
        try:
            from multi_day_continuity import process_multi_day_continuity_control
            c = process_multi_day_continuity_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show campaign rollback", "inspect campaign rollback", "show rollback plan"}:
        try:
            from campaign_rollback import process_campaign_rollback_control
            c = process_campaign_rollback_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show campaign conflicts", "inspect campaign conflicts", "show conflict reconciliation"}:
        try:
            from conflict_reconciliation import process_conflict_reconciliation_control
            c = process_conflict_reconciliation_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show partial results", "inspect partial results", "show retained work"}:
        try:
            from partial_result_retention import process_partial_result_control
            c = process_partial_result_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show task heartbeat", "inspect task heartbeat", "show long task status"}:
        try:
            from long_task_heartbeats import process_long_task_control
            c = process_long_task_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show parallel plan", "inspect parallel plan", "show bounded parallelism"}:
        try:
            from bounded_parallelism import process_bounded_parallel_control
            c = process_bounded_parallel_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show dependency schedule", "inspect dependency schedule", "show campaign schedule"}:
        try:
            from dependency_scheduling import process_dependency_schedule_control
            c = process_dependency_schedule_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show campaign recovery", "inspect campaign recovery", "show crash recovery"}:
        try:
            from crash_safe_campaign_checkpoints import process_campaign_recovery_control
            c = process_campaign_recovery_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show campaign record", "inspect campaign record", "show campaign state"}:
        try:
            from campaign_records import process_campaign_record_control
            c = process_campaign_record_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show diagnosis repair checkpoint", "inspect diagnosis repair", "show diagnosis and repair"}:
        try:
            from diagnosis_repair_integration import process_diagnosis_repair_control
            c = process_diagnosis_repair_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show ui diagnosis", "inspect ui diagnosis", "show interface diagnosis"}:
        try:
            from ui_diagnosis import process_ui_diagnosis_control
            c = process_ui_diagnosis_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show provider diagnosis", "inspect provider diagnosis", "show provider failure"}:
        try:
            from provider_diagnosis import process_provider_diagnosis_control
            c = process_provider_diagnosis_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show data diagnosis", "inspect data diagnosis", "show storage diagnosis"}:
        try:
            from data_diagnosis import process_data_diagnosis_control
            c = process_data_diagnosis_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show concurrency diagnosis", "inspect concurrency diagnosis", "show concurrency repair"}:
        try:
            from concurrency_diagnosis import process_concurrency_diagnosis_control
            c = process_concurrency_diagnosis_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show iterative repair", "inspect repair loop", "show repair loop"}:
        try:
            from iterative_repair_loop import process_iterative_repair_control
            c = process_iterative_repair_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show repair proposal", "inspect repair proposal", "show proposed repair"}:
        try:
            from repair_proposal import process_repair_proposal_control
            c = process_repair_proposal_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show root cause analysis", "inspect root cause", "show root cause"}:
        try:
            from root_cause_analysis import process_root_cause_control
            c = process_root_cause_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show fault localization", "inspect fault localization", "show likely causes"}:
        try:
            from fault_localization import process_fault_localization_control
            c = process_fault_localization_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show reproduction", "inspect reproduction", "show reproduction builder"}:
        try:
            from reproduction_builder import process_reproduction_control
            c = process_reproduction_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show verification intelligence", "inspect verification intelligence", "show verification checkpoint"}:
        try:
            from verification_intelligence_checkpoint import process_verification_intelligence_control
            c = process_verification_intelligence_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show evidence quality", "inspect evidence quality", "show evidence checks"}:
        try:
            from evidence_quality import process_evidence_quality_control
            c = process_evidence_quality_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show security verification", "inspect security verification", "show security tests"}:
        try:
            from security_verification import process_security_verification_control
            c = process_security_verification_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show performance verification", "inspect performance verification", "show performance tests"}:
        try:
            from performance_verification import process_performance_verification_control
            c = process_performance_verification_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show ui accessibility verification", "inspect ui accessibility verification", "show accessibility tests"}:
        try:
            from ui_accessibility_verification import process_ui_accessibility_control
            c = process_ui_accessibility_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show property fuzz verification", "inspect property fuzz verification", "show fuzz tests"}:
        try:
            from property_fuzz_verification import process_property_fuzz_control
            c = process_property_fuzz_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show integration verification", "inspect integration verification", "show integration tests"}:
        try:
            from integration_test_verification import process_integration_verification_control
            c = process_integration_verification_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show unit contract tests", "inspect unit contract tests", "show generated contract tests"}:
        try:
            from unit_contract_test_generation import process_unit_contract_test_control
            c = process_unit_contract_test_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show test selection", "inspect test selection", "show verification tests"}:
        try:
            from verification_test_selection import process_test_selection_control
            c = process_test_selection_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    if normalized_control in {"show acceptance traceability", "inspect acceptance traceability", "show requirement traceability"}:
        try:
            from acceptance_traceability import process_acceptance_traceability_control
            c = process_acceptance_traceability_control(text, project_state=project_state, runtime_root=runtime_root)
            if c.get("active"):
                return c
        except Exception:
            pass
    # v1350-v1346 Phase 5 inspection controls stay import-lazy on ordinary chat.
    # Their exact command phrases are mirrored here so unrelated conversation never
    # imports the implementation stack merely to discover that no control is active.
    if normalized_control in {"show implementation skill checkpoint", "inspect implementation skill checkpoint", "show implementation benchmark"}:
        try:
            from implementation_skill_benchmark import process_implementation_skill_benchmark_control
            skill_control = process_implementation_skill_benchmark_control(text, project_state=project_state, runtime_root=runtime_root)
            if skill_control.get("active"):
                return skill_control
        except Exception:
            pass
    if normalized_control in {"show cross language change", "inspect cross language change", "show cross-language change"}:
        try:
            from cross_language_changes import process_cross_language_change_control
            cross_language_control = process_cross_language_change_control(text, project_state=project_state, runtime_root=runtime_root)
            if cross_language_control.get("active"):
                return cross_language_control
        except Exception:
            pass
    if normalized_control in {"show dependency selection", "inspect dependency selection", "show dependency evaluation"}:
        try:
            from dependency_selection import process_dependency_selection_control
            dependency_control = process_dependency_selection_control(text, project_state=project_state, runtime_root=runtime_root)
            if dependency_control.get("active"):
                return dependency_control
        except Exception:
            pass
    if normalized_control in {"show framework adaptation", "inspect framework adaptation", "show framework conventions"}:
        try:
            from framework_adaptation import process_framework_adaptation_control
            framework_control = process_framework_adaptation_control(text, project_state=project_state, runtime_root=runtime_root)
            if framework_control.get("active"):
                return framework_control
        except Exception:
            pass
    if normalized_control in {"show cross platform automation", "inspect cross platform automation", "show cross-platform automation"}:
        try:
            from cross_platform_automation import process_cross_platform_automation_control
            cross_platform_control = process_cross_platform_automation_control(text, project_state=project_state, runtime_root=runtime_root)
            if cross_platform_control.get("active"):
                return cross_platform_control
        except Exception:
            pass
    # v1345 exposes content-minimized Windows automation evidence; ordinary chat never edits scripts, executes PowerShell, mutates services, elevates, installs, stages, or commits.
    try:
        from windows_automation import process_windows_automation_control
        windows_control = process_windows_automation_control(text, project_state=project_state, runtime_root=runtime_root)
        if windows_control.get("active"):
            return windows_control
    except Exception:
        pass
    # v1344 exposes content-minimized structured data/schema implementation evidence; ordinary chat never edits, migrates, contacts databases, tests, stages, or commits.
    try:
        from data_schema_implementation import process_data_schema_implementation_control
        data_schema_control = process_data_schema_implementation_control(text, project_state=project_state, runtime_root=runtime_root)
        if data_schema_control.get("active"):
            return data_schema_control
    except Exception:
        pass
    # v1343 exposes content-minimized HTML/CSS implementation evidence; ordinary chat never edits UI files, launches validation, stages, or commits.
    try:
        from html_css_implementation import process_html_css_implementation_control
        html_css_control = process_html_css_implementation_control(text, project_state=project_state, runtime_root=runtime_root)
        if html_css_control.get("active"):
            return html_css_control
    except Exception:
        pass
    # v1342 exposes content-minimized JavaScript/TypeScript implementation evidence; ordinary chat never edits, checks, tests, stages, commits, installs packages, or contacts the network.
    try:
        from javascript_typescript_implementation import process_javascript_typescript_implementation_control
        js_ts_control = process_javascript_typescript_implementation_control(text, project_state=project_state, runtime_root=runtime_root)
        if js_ts_control.get("active"):
            return js_ts_control
    except Exception:
        pass
    # v1341 exposes content-minimized Python implementation evidence; ordinary chat never edits, compiles, tests, stages, or commits.
    try:
        from python_implementation import process_python_implementation_control
        python_control = process_python_implementation_control(text, project_state=project_state, runtime_root=runtime_root)
        if python_control.get("active"):
            return python_control
    except Exception:
        pass
    # v1340 exposes the sealed Phase 4 multi-tool checkpoint receipt; ordinary chat never reruns the campaign.
    try:
        from multi_tool_execution import process_multi_tool_execution_control
        multi_tool_control = process_multi_tool_execution_control(text, project_state=project_state, runtime_root=runtime_root)
        if multi_tool_control.get("active"):
            return multi_tool_control
    except Exception:
        pass
    # v1339 exposes content-minimized tool-result reconciliation; ordinary chat never retries a tool.
    try:
        from tool_result_reconciliation import process_tool_result_reconciliation_control
        reconciliation_control = process_tool_result_reconciliation_control(text, project_state=project_state, runtime_root=runtime_root)
        if reconciliation_control.get("active"):
            return reconciliation_control
    except Exception:
        pass
    # v1338 exposes content-minimized local service-stack state; ordinary chat never starts, restarts, or stops services.
    try:
        from service_orchestration import process_service_orchestration_control
        service_control = process_service_orchestration_control(text, project_state=project_state, runtime_root=runtime_root)
        if service_control.get("active"):
            return service_control
    except Exception:
        pass
    # v1337 exposes content-minimized real-browser validation evidence; ordinary chat never launches a browser.
    try:
        from browser_validation import process_browser_validation_control
        browser_control = process_browser_validation_control(text, project_state=project_state, runtime_root=runtime_root)
        if browser_control.get("active"):
            return browser_control
    except Exception:
        pass
    # v1336 exposes content-minimized process-operation state; ordinary chat never starts or stops a process.
    try:
        from typed_process_operations import process_process_operations_control
        process_control = process_process_operations_control(text, project_state=project_state, runtime_root=runtime_root)
        if process_control.get("active"):
            return process_control
    except Exception:
        pass
    # v1335 exposes typed Git-operation evidence; ordinary chat never stages or commits.
    try:
        from typed_git_operations import process_git_operations_control
        git_control = process_git_operations_control(text, project_state=project_state, runtime_root=runtime_root)
        if git_control.get("active"):
            return git_control
    except Exception:
        pass
    # v1334 exposes content-minimized candidate file-operation evidence; chat inspection never performs a file operation.
    try:
        from structured_file_operations import process_file_operations_control
        file_control = process_file_operations_control(text, project_state=project_state, runtime_root=runtime_root)
        if file_control.get("active"):
            return file_control
    except Exception:
        pass
    # v1333 exposes workspace-isolation state and plans; ordinary chat never materializes or cleans a workspace.
    try:
        from workspace_isolation import process_workspace_isolation_control
        workspace_control = process_workspace_isolation_control(
            text, project_state=project_state, runtime_root=runtime_root,
        )
        if workspace_control.get("active"):
            return workspace_control
    except Exception:
        pass
    # v1332 checks supplied execution preconditions without probing, invoking, or granting authority.
    try:
        from tool_preconditions import process_tool_preconditions_control
        precondition_control = process_tool_preconditions_control(
            text, project_state=project_state, runtime_root=runtime_root,
        )
        if precondition_control.get("active"):
            return precondition_control
    except Exception:
        pass
    # v1331 exposes declared tool schemas and side effects without probing or invoking tools.
    try:
        from tool_capability_registry import process_tool_capability_registry_control
        tool_registry_control = process_tool_capability_registry_control(
            text, availability_evidence=(project_state or {}).get("tool_availability_evidence"), runtime_root=runtime_root,
        )
        if tool_registry_control.get("active"):
            return tool_registry_control
    except Exception:
        pass
    # v1330 exposes the integrated Phase 3 deliberative-planning checkpoint.
    try:
        from deliberative_planning_integration import process_deliberative_planning_control
        integrated_control = process_deliberative_planning_control(
            text, goal=(project_state or {}).get("planning_goal") or (project_state or {}).get("goal"),
            project_understanding=(project_state or {}).get("project_understanding"),
            decision_context=(project_state or {}).get("planning_decision_context"),
            explicit_options=(project_state or {}).get("planning_explicit_options") or (),
            evidence_by_approach=(project_state or {}).get("planning_tradeoff_evidence"),
            assumptions=(project_state or {}).get("planning_assumptions") or (),
            impact_analysis=(project_state or {}).get("impact_analysis"),
            selected_approach_id=str((project_state or {}).get("selected_planning_approach_id") or ""),
            completed_step_codes=(project_state or {}).get("completed_planning_steps") or (),
            evidence_change=(project_state or {}).get("planning_evidence_change"),
            replan_reason_code=str((project_state or {}).get("replan_reason_code") or "new_evidence"),
            replacement_specs=(project_state or {}).get("revised_plan_specs") or (),
            failure_count=int((project_state or {}).get("planning_failure_count") or 0),
            uncertainty=(project_state or {}).get("planning_uncertainty"),
            boundary_conflict=bool((project_state or {}).get("planning_boundary_conflict")),
            resource_exhausted=bool((project_state or {}).get("planning_resource_exhausted")),
            unsafe_side_effect=bool((project_state or {}).get("planning_unsafe_side_effect")),
            outcome_evidence=(project_state or {}).get("plan_outcome_evidence"), runtime_root=runtime_root,
        )
        if integrated_control.get("active"):
            return integrated_control
    except Exception:
        pass
    # v1329 scores plan quality only from observed outcome evidence; absent
    # evidence is explicitly not evaluable rather than rewarded with a guess.
    try:
        from plan_quality_scoring import process_plan_quality_control
        quality_control = process_plan_quality_control(
            text, plan=(project_state or {}).get("constructed_plan") or (project_state or {}).get("plan"),
            outcome_evidence=(project_state or {}).get("plan_outcome_evidence"), runtime_root=runtime_root,
        )
        if quality_control.get("active"):
            return quality_control
    except Exception:
        pass
    # v1328 stops planning on repeated failure, material uncertainty, boundary
    # conflict, exhausted resources, unsafe side effects, or protected surfaces.
    try:
        from planning_stop_escalation import process_stop_escalation_control
        stop_control = process_stop_escalation_control(
            text, failure_count=int((project_state or {}).get("planning_failure_count") or 0),
            uncertainty=(project_state or {}).get("planning_uncertainty"),
            boundary_conflict=bool((project_state or {}).get("planning_boundary_conflict")),
            resource_exhausted=bool((project_state or {}).get("planning_resource_exhausted")),
            unsafe_side_effect=bool((project_state or {}).get("planning_unsafe_side_effect")),
            risk_sensitive_planning=(project_state or {}).get("risk_sensitive_planning"), runtime_root=runtime_root,
        )
        if stop_control.get("active"):
            return stop_control
    except Exception:
        pass
    # v1327 revises only unfinished plan work when evidence changes and preserves
    # completed-step evidence instead of rewriting history.
    try:
        from evidence_dynamic_replanning import process_dynamic_replanning_control
        replan_control = process_dynamic_replanning_control(
            text, plan=(project_state or {}).get("constructed_plan") or (project_state or {}).get("plan"),
            completed_step_codes=(project_state or {}).get("completed_planning_steps") or (),
            evidence_change=(project_state or {}).get("planning_evidence_change"),
            reason_code=str((project_state or {}).get("replan_reason_code") or "new_evidence"),
            replacement_specs=(project_state or {}).get("revised_plan_specs") or (), runtime_root=runtime_root,
        )
        if replan_control.get("active"):
            return replan_control
    except Exception:
        pass
    # v1326 scales planning safeguards to evidence-backed blast radius without
    # converting requirements, scores, or review depth into execution authority.
    try:
        from risk_sensitive_planning import process_risk_sensitive_planning_control
        risk_control = process_risk_sensitive_planning_control(
            text, plan=(project_state or {}).get("constructed_plan") or (project_state or {}).get("plan"),
            plan_critique=(project_state or {}).get("plan_critique"),
            impact_analysis=(project_state or {}).get("impact_analysis"), runtime_root=runtime_root,
        )
        if risk_control.get("active"):
            return risk_control
    except Exception:
        pass
    # v1325 runs an independent bounded plan critique without mutating the plan.
    try:
        from plan_critique import process_plan_critique_control
        critique_control = process_plan_critique_control(
            text, plan=(project_state or {}).get("constructed_plan") or (project_state or {}).get("plan"),
            goal=(project_state or {}).get("planning_goal") or (project_state or {}).get("goal"),
            impact_analysis=(project_state or {}).get("impact_analysis"),
            assumption_ledger=(project_state or {}).get("assumption_ledger"), runtime_root=runtime_root,
        )
        if critique_control.get("active"):
            return critique_control
    except Exception:
        pass
    # v1324 constructs dependency-aware plans with tests, rollback, checkpoints,
    # and exit criteria, while leaving every step unexecuted and unauthorized.
    try:
        from plan_construction import process_plan_construction_control
        plan_control = process_plan_construction_control(
            text, goal=(project_state or {}).get("planning_goal") or (project_state or {}).get("goal"),
            candidate_approaches=(project_state or {}).get("candidate_approaches"),
            tradeoff_evaluation=(project_state or {}).get("tradeoff_evaluation"),
            assumption_ledger=(project_state or {}).get("assumption_ledger"),
            task_specs=(project_state or {}).get("planning_task_specs") or (), runtime_root=runtime_root,
        )
        if plan_control.get("active"):
            return plan_control
    except Exception:
        pass
    # v1323 exposes the evidence-linked assumption ledger behind planning judgments.
    try:
        from assumption_ledger import process_assumption_ledger_control
        assumption_control = process_assumption_ledger_control(
            text, goal=(project_state or {}).get("planning_goal") or (project_state or {}).get("goal"),
            project_understanding=(project_state or {}).get("project_understanding"),
            assumptions=(project_state or {}).get("planning_assumptions"), runtime_root=runtime_root,
        )
        if assumption_control.get("active"):
            return assumption_control
    except Exception:
        pass
    # v1322 compares candidate approaches with calibrated evidence-aware tradeoffs.
    # Recommendations remain advisory and ties are preserved rather than forced.
    try:
        from tradeoff_evaluation import process_tradeoff_evaluation_control
        tradeoff_control = process_tradeoff_evaluation_control(
            text,
            candidate_approaches=(project_state or {}).get("candidate_approaches"),
            project_root=str((project_state or {}).get("project_root") or (project_state or {}).get("source_root") or ""),
            project_understanding=(project_state or {}).get("project_understanding"),
            goal=(project_state or {}).get("planning_goal") or (project_state or {}).get("goal"),
            decision_context=(project_state or {}).get("planning_decision_context"),
            evidence_by_approach=(project_state or {}).get("tradeoff_evidence"),
            runtime_root=runtime_root,
        )
        if tradeoff_control.get("active"):
            return tradeoff_control
    except Exception:
        pass
    # v1321 exposes read-only candidate approaches for an already represented
    # planning goal. Routine reversible choices collapse; consequential tradeoffs
    # remain explicit. No approach grants execution or approval authority.
    try:
        from candidate_approaches import process_candidate_approaches_control
        candidate_control = process_candidate_approaches_control(
            text,
            project_root=str((project_state or {}).get("project_root") or (project_state or {}).get("source_root") or ""),
            project_understanding=(project_state or {}).get("project_understanding"),
            goal=(project_state or {}).get("planning_goal") or (project_state or {}).get("goal"),
            decision_context=(project_state or {}).get("planning_decision_context"),
            runtime_root=runtime_root,
        )
        if candidate_control.get("active"):
            return candidate_control
    except Exception:
        pass
    # v1316-v1320 expose content-minimized project-understanding controls over
    # the selected source root. They are strictly read-only and never convert
    # an inspection request into project, provider, test, update, or release authority.
    selected_project_root = str((project_state or {}).get("project_root") or (project_state or {}).get("source_root") or "")
    for module_name, function_name in (
        ("project_understanding_checkpoint", "process_project_understanding_checkpoint_control"),
        ("project_unknown_detection", "process_project_unknown_control"),
        ("impact_analysis", "process_impact_analysis_control"),
        ("change_history_understanding", "process_change_history_control"),
        ("architecture_summaries", "process_architecture_summary_control"),
    ):
        try:
            module = __import__(module_name, fromlist=[function_name])
            control = getattr(module, function_name)(text, project_root=selected_project_root, runtime_root=runtime_root)
            if control.get("active"):
                return control
        except Exception:
            pass
    # v1249 exposes read-only feature-freeze and final-hardening inspection.
    # It cannot edit source, add features, expand authority, certify, or release.
    try:
        from feature_freeze_final_hardening import process_feature_freeze_final_hardening_control
        freeze_control = process_feature_freeze_final_hardening_control(text, runtime_root=runtime_root)
        if freeze_control.get("active"):
            return freeze_control
    except Exception:
        pass
    # v1248 exposes a read-only integrated mind, conversation, and development
    # benchmark. Its fixtures exercise the ordinary chat path without granting
    # provider, project, cognition, message, or execution authority.
    try:
        from integrated_mind_conversation_development_benchmark import (
            process_integrated_mind_conversation_development_control,
        )
        integrated_benchmark_control = process_integrated_mind_conversation_development_control(
            text, runtime_root=runtime_root
        )
        if integrated_benchmark_control.get("active"):
            return integrated_benchmark_control
    except Exception:
        pass
    # v1247 inspects redacted privacy/security evidence and exact remediation reviews.
    # It never reveals matched values, rotates credentials, deletes files, or grants authority.
    try:
        from privacy_security_secret_management_audit import process_privacy_security_audit_control
        privacy_security_control = process_privacy_security_audit_control(text, runtime_root=runtime_root)
        if privacy_security_control.get("active"):
            return privacy_security_control
    except Exception:
        pass
    # v1246 paces content-free initiative proposals and deliberate silence.
    # It never sends messages or notifications, changes global preferences,
    # or converts a pacing decision into execution authority.
    try:
        from initiative_proposal_pacing import process_initiative_pacing_control
        initiative_pacing_control = process_initiative_pacing_control(text, runtime_root=runtime_root)
        if initiative_pacing_control.get("active"):
            return initiative_pacing_control
    except Exception:
        pass
    # v1245 preserves content-free project understanding across sessions.
    # Remembered state is revalidated against current evidence and never becomes
    # project, cognition, plan, or execution authority.
    try:
        from cross_session_project_understanding import process_project_understanding_control
        project_understanding_control = process_project_understanding_control(text, runtime_root=runtime_root)
        if project_understanding_control.get("active"):
            return project_understanding_control
    except Exception:
        pass
    # v1244 preserves content-free long-running and multi-day session continuity.
    # It records progress, suspension manifests, reconciliation evidence, and exact
    # operator reviews without resuming, retrying, contacting providers, or reusing authority.
    try:
        from long_running_multi_day_session_continuity import process_session_continuity_control
        session_continuity_control = process_session_continuity_control(text, runtime_root=runtime_root)
        if session_continuity_control.get("active"):
            return session_continuity_control
    except Exception:
        pass
    # v1243 prepares and reviews content-free provider/model selection and
    # fallback evidence. It never contacts a provider, transmits prompts,
    # changes model configuration, retries, resumes, or grants authority.
    try:
        from provider_fallback_model_governance import process_provider_model_governance_control
        provider_governance_control = process_provider_model_governance_control(text, runtime_root=runtime_root)
        if provider_governance_control.get("active"):
            return provider_governance_control
    except Exception:
        pass
    # v1242 prepares and reviews content-free installation, upgrade, backup,
    # restore, rollback, and interrupted-transaction recovery evidence. It
    # never invokes lifecycle mutation functions or grants deployment authority.
    try:
        from installation_upgrade_backup_rollback_integration import process_installation_lifecycle_control
        lifecycle_control = process_installation_lifecycle_control(text, runtime_root=runtime_root)
        if lifecycle_control.get("active"):
            return lifecycle_control
    except Exception:
        pass
    # v1241 exposes a unified, privacy-filtered, read-only operator dashboard.
    try:
        from unified_operator_dashboard import process_unified_operator_dashboard_control
        unified_dashboard_control = process_unified_operator_dashboard_control(text, runtime_root=runtime_root)
        if unified_dashboard_control.get("active"):
            return unified_dashboard_control
    except Exception:
        pass
    # v1240 exposes a read-only, content-free Integrated Developer Beta
    # benchmark and scenario registry. It reads no operator runtime data and
    # grants no tool, execution, project, cognition, or release authority.
    try:
        from integrated_developer_beta import process_integrated_developer_beta_control
        integrated_beta_control = process_integrated_developer_beta_control(text, runtime_root=runtime_root)
        if integrated_beta_control.get("active"):
            return integrated_beta_control
    except Exception:
        pass
    # v1239 exposes exact, content-free adversarial boundary inspection and
    # review. It executes no attack and grants no execution or cognition authority.
    try:
        from adversarial_execution_cognitive_boundary import process_adversarial_execution_cognitive_boundary_control
        adversarial_boundary_control = process_adversarial_execution_cognitive_boundary_control(text, runtime_root=runtime_root)
        if adversarial_boundary_control.get("active"):
            return adversarial_boundary_control
    except Exception:
        pass
    # v1238 selects broader project/language adapters from sanitized manifest
    # and layout evidence. It never reads file contents, invokes build tools,
    # installs dependencies, or grants execution authority.
    try:
        from broader_project_language_adapters import process_broader_project_language_adapter_control
        broader_adapter_control = process_broader_project_language_adapter_control(text, runtime_root=runtime_root)
        if broader_adapter_control.get("active"):
            return broader_adapter_control
    except Exception:
        pass
    # v1237 coordinates bounded, content-free multi-tool plans and evidence
    # handoffs. It never invokes a tool or authorizes the next step.
    try:
        from multi_tool_orchestration import process_multi_tool_orchestration_control
        orchestration_control = process_multi_tool_orchestration_control(text, runtime_root=runtime_root)
        if orchestration_control.get("active"):
            return orchestration_control
    except Exception:
        pass
    # v1236 binds sanitized goal and motivation snapshots to one exact
    # operator-governed priority item and optional accepted lesson evidence.
    # Alignment and priority-change proposals remain advisory only.
    try:
        from goal_motivation_work_priority_integration import (
            process_goal_motivation_work_priority_integration_control,
        )
        goal_priority_control = process_goal_motivation_work_priority_integration_control(
            text, runtime_root=runtime_root
        )
        if goal_priority_control.get("active"):
            return goal_priority_control
    except Exception:
        pass
    # v1235 derives bounded, project-scoped lessons from exact v1234
    # assessment and operator-review evidence. Accepted lessons remain external
    # and revisable; they never write cognition or grant execution authority.
    try:
        from evidence_backed_development_outcome_lessons import (
            process_evidence_backed_development_lesson_control,
        )
        lesson_control = process_evidence_backed_development_lesson_control(
            text, runtime_root=runtime_root
        )
        if lesson_control.get("active"):
            return lesson_control
    except Exception:
        pass
    # v1234 evaluates content-free requirements and quality evidence against
    # exact resource admission and optional sealed outcome lineage. Assessment
    # never approves, applies, tests, executes, mutates, or writes cognition.
    try:
        from requirement_quality_assessment import process_requirement_quality_assessment_control
        quality_control = process_requirement_quality_assessment_control(
            text, runtime_root=runtime_root
        )
        if quality_control.get("active"):
            return quality_control
    except Exception:
        pass
    # v1233 evaluates sealed resource claims, bounded concurrency, fairness,
    # and preemption proposals. Admissibility never launches, resumes, leases,
    # preempts, executes, mutates, retries, or reuses authority.
    try:
        from resource_concurrency_governance import process_resource_concurrency_governance_control
        resource_control = process_resource_concurrency_governance_control(
            text, runtime_root=runtime_root
        )
        if resource_control.get("active"):
            return resource_control
    except Exception:
        pass
    # v1232 evaluates sealed dependency evidence and records exact operator
    # readiness reviews. Readiness never launches or resumes work and grants no
    # execution, mutation, retry, provider, model, release, or old-authority use.
    try:
        from dependency_aware_execution import process_dependency_aware_execution_control
        dependency_control = process_dependency_aware_execution_control(
            text, runtime_root=runtime_root
        )
        if dependency_control.get("active"):
            return dependency_control
    except Exception:
        pass
    # v1231 prepares bounded, append-only execution-plan revision evidence
    # and exact operator reviews. Neither proposals nor reviews launch, resume,
    # execute, mutate, retry, or reuse authority.
    try:
        from dynamic_execution_plan_revision import (
            process_dynamic_execution_plan_revision_control,
        )
        plan_revision_control = process_dynamic_execution_plan_revision_control(
            text, runtime_root=runtime_root
        )
        if plan_revision_control.get("active"):
            return plan_revision_control
    except Exception:
        pass
    # v1229 derives sealed execution outcomes, prepares bounded reflection
    # subjects, and records operator-reviewed project-scoped lessons. It does
    # not write cognition, modify projects, change schedules, launch work, or
    # reuse prior execution authority.
    try:
        from execution_outcome_reflection_learning_integration import (
            process_execution_outcome_reflection_learning_control,
        )
        outcome_reflection_control = process_execution_outcome_reflection_learning_control(
            text, runtime_root=runtime_root
        )
        if outcome_reflection_control.get("active"):
            return outcome_reflection_control
    except Exception:
        pass
    # v1228 applies separately authorized pause, resume, cancel, review, and
    # recovery transitions over immutable launch and monitoring evidence.
    # These controls do not grant provider, command, test, workspace, project,
    # cognition, installation, promotion, release, or model authority.
    try:
        from execution_session_pause_resume_cancel_recovery import (
            process_execution_session_pause_resume_cancel_recovery_control,
        )
        execution_session_control = process_execution_session_pause_resume_cancel_recovery_control(
            text, runtime_root=runtime_root
        )
        if execution_session_control.get("active"):
            return execution_session_control
    except Exception:
        pass
    # v1227 exposes sealed, content-free live progress and exact operator
    # intervention requests. Requests do not apply pause, stop, resume, cancel,
    # provider, command, test, workspace, project, or cognition actions.
    try:
        from live_execution_monitoring_operator_intervention import (
            process_live_execution_monitoring_operator_intervention_control,
        )
        live_monitoring_control = process_live_execution_monitoring_operator_intervention_control(
            text, runtime_root=runtime_root
        )
        if live_monitoring_control.get("active"):
            return live_monitoring_control
    except Exception:
        pass
    # v1226 issues one exact, single-use launch authorization for an accepted
    # current v1225 prepared session. Launch creates only a bounded external
    # runtime session namespace; provider, command, test, workspace, project,
    # and cognition authority remain separately gated.
    try:
        from execution_session_authorization_bounded_launch import (
            process_execution_session_authorization_bounded_launch_control,
        )
        bounded_launch_control = process_execution_session_authorization_bounded_launch_control(
            text, runtime_root=runtime_root
        )
        if bounded_launch_control.get("active"):
            return bounded_launch_control
    except Exception:
        pass
    # v1225 prepares one bounded execution session from an accepted current
    # schedule. Preparation and review never launch work or reuse old authority.
    try:
        from supervised_work_dispatch_execution_session_preparation import (
            process_supervised_work_dispatch_control,
        )
        supervised_dispatch_control = process_supervised_work_dispatch_control(
            text, runtime_root=runtime_root
        )
        if supervised_dispatch_control.get("active"):
            return supervised_dispatch_control
    except Exception:
        pass
    # v1224 derives operator-governed priorities and bounded schedules from the
    # current v1223 queue. Rankings and schedules are advisory evidence only and
    # cannot dispatch or execute development work.
    try:
        from operator_governed_work_prioritization_scheduling import (
            process_operator_governed_work_prioritization_control,
        )
        governed_priority_control = process_operator_governed_work_prioritization_control(
            text, runtime_root=runtime_root
        )
        if governed_priority_control.get("active"):
            return governed_priority_control
    except Exception:
        pass
    # v1223 exposes one privacy-safe project work queue over the existing
    # authoritative proposal, history, and resumption receipts. Queue focus and
    # dispositions never reuse approval or execute development work.
    try:
        from unified_development_work_queue import (
            process_unified_development_work_queue_control,
        )
        unified_work_queue_control = process_unified_development_work_queue_control(
            text, runtime_root=runtime_root
        )
        if unified_work_queue_control.get("active"):
            return unified_work_queue_control
    except Exception:
        pass
    # v1222 derives one exact resumption/abandoned-work assessment from the
    # current v1221 history generation. Exact operator decisions may prepare a
    # new approval-gated continuation proposal, but never reuse old authority
    # or execute continuation work.
    try:
        from transaction_resumption_abandoned_work_reconciliation import (
            process_transaction_resumption_control,
        )
        transaction_resumption_control = process_transaction_resumption_control(
            text, runtime_root=runtime_root
        )
        if transaction_resumption_control.get("active"):
            return transaction_resumption_control
    except Exception:
        pass
    # v1221 exposes a bounded, read-only transaction-history inspection command.
    # It derives content-free events from authoritative receipts and cannot
    # execute, retry, or authorize development work.
    try:
        from unified_supervised_development_transaction_history import (
            process_unified_supervised_development_transaction_history_control,
        )
        transaction_history_control = (
            process_unified_supervised_development_transaction_history_control(
                text, runtime_root=runtime_root
            )
        )
        if transaction_history_control.get("active"):
            return transaction_history_control
    except Exception:
        pass
    # v1220 recognizes only an exact digest-bound terminal rollback-result
    # disposition. The review is non-executing and cannot retry rollback or
    # grant any downstream authority.
    try:
        from operator_repaired_candidate_rollback_result_review import (
            process_operator_repaired_candidate_rollback_result_review_control,
        )
        rollback_result_review_control = (
            process_operator_repaired_candidate_rollback_result_review_control(
                text, runtime_root=runtime_root
            )
        )
        if rollback_result_review_control.get("active"):
            try:
                from unified_supervised_development_transaction_history import (
                    attach_unified_supervised_development_transaction_history,
                )
                return attach_unified_supervised_development_transaction_history(
                    rollback_result_review_control, runtime_root=runtime_root
                )
            except Exception:
                return rollback_result_review_control
    except Exception:
        pass
    # v1219 recognizes only the exact digest-bound rollback authorization
    # emitted by v1218. It consumes one attempt, restores the exact pre-apply
    # selected-project state, verifies it, and returns to operator review.
    try:
        from conversational_supervised_repaired_candidate_rollback import (
            process_supervised_repaired_candidate_rollback_control,
        )
        repaired_rollback_control = process_supervised_repaired_candidate_rollback_control(
            text, runtime_root=runtime_root
        )
        if repaired_rollback_control.get("active"):
            try:
                from operator_repaired_candidate_rollback_result_review import (
                    attach_operator_repaired_candidate_rollback_result_review,
                )
                return attach_operator_repaired_candidate_rollback_result_review(
                    repaired_rollback_control, runtime_root=runtime_root
                )
            except Exception:
                return repaired_rollback_control
    except Exception:
        pass
    # v1218 recognizes only an exact digest-bound repaired-candidate apply
    # result disposition. A completed apply may prepare one content-free
    # rollback proposal, but no disposition authorizes or performs rollback.
    try:
        from operator_repaired_candidate_apply_result_review import (
            process_operator_repaired_candidate_apply_result_review_control,
        )
        apply_result_review_control = (
            process_operator_repaired_candidate_apply_result_review_control(
                text, runtime_root=runtime_root
            )
        )
        if apply_result_review_control.get("active"):
            return apply_result_review_control
    except Exception:
        pass
    # v1217 recognizes only the exact digest-bound repaired-candidate apply
    # authorization already emitted by v1216. The transaction is limited to
    # the exact failed project workspace and exact passing repaired workspace,
    # seals rollback evidence before writing, and returns to operator review.
    try:
        from conversational_supervised_repaired_candidate_apply import (
            process_supervised_repaired_candidate_apply_control,
        )
        repaired_apply_control = process_supervised_repaired_candidate_apply_control(
            text, runtime_root=runtime_root
        )
        if repaired_apply_control.get("active"):
            try:
                from operator_repaired_candidate_apply_result_review import (
                    attach_operator_repaired_candidate_apply_result_review,
                )
                return attach_operator_repaired_candidate_apply_result_review(
                    repaired_apply_control, runtime_root=runtime_root
                )
            except Exception:
                return repaired_apply_control
    except Exception:
        # An unavailable optional apply surface must remain inert for ordinary
        # language. Exact controls fail closed inside their own public result.
        pass
    # v1216 recognizes only an exact digest-bound repair-result disposition.
    # A passing repaired candidate may prepare one content-free apply proposal,
    # but no disposition authorizes or performs the apply itself.
    try:
        from operator_repair_result_review import (
            process_operator_repair_result_review_control,
        )
        repair_result_review_control = process_operator_repair_result_review_control(
            text, runtime_root=runtime_root
        )
        if repair_result_review_control.get("active"):
            return repair_result_review_control
    except Exception:
        pass
    # v1215 recognizes only the exact digest-bound repair authorization already
    # emitted by the sealed v1214 proposal.  One accepted phrase may run one
    # isolated repair and retained test pass; its result remains operator-review
    # only and cannot apply, install, promote, release, or grant authority.
    try:
        from conversational_supervised_repair_execution import (
            process_conversational_supervised_repair_control,
        )
        repair_control = process_conversational_supervised_repair_control(
            text,
            runtime_root=runtime_root,
            provider_generate=provider_generate,
            node_executable=node_executable,
            python_executable=python_executable,
            chromium_executable=chromium_executable,
        )
        if repair_control.get("active"):
            try:
                from operator_repair_result_review import (
                    attach_operator_repair_result_review,
                )
                return attach_operator_repair_result_review(
                    repair_control, runtime_root=runtime_root
                )
            except Exception:
                return repair_control
    except Exception:
        # The exact repair contract fails closed in its own public result.  An
        # unavailable optional surface must not reinterpret ordinary language.
        pass
    # v1214 recognizes only an exact, digest-bound operator diagnosis-review
    # decision.  A propose-repair decision may prepare one content-free repair
    # proposal, but cannot authorize or execute repair work.
    try:
        from operator_diagnosis_review import process_operator_diagnosis_review_control
        diagnosis_review_control = process_operator_diagnosis_review_control(
            text, runtime_root=runtime_root
        )
        if diagnosis_review_control.get("active"):
            return diagnosis_review_control
    except Exception:
        pass
    # v1212 recognizes only the exact continuation-attempt authorization.  A
    # terminal continuation result is then eligible for the v1213 bounded,
    # evidence-only automatic diagnosis seam and the v1214 operator-review
    # seam.  Neither layer uses a provider or test runtime, and neither can
    # authorize repair execution or another attempt.
    try:
        from conversational_build_test_continuation import process_conversational_build_test_continuation_control
        continuation_control = process_conversational_build_test_continuation_control(
            text,
            runtime_root=runtime_root,
            provider_generate=provider_generate,
            node_executable=node_executable,
            python_executable=python_executable,
            chromium_executable=chromium_executable,
        )
        if continuation_control.get("active"):
            try:
                from bounded_automatic_diagnosis import attach_bounded_automatic_diagnosis
                diagnosed = attach_bounded_automatic_diagnosis(
                    continuation_control, runtime_root=runtime_root
                )
                try:
                    from operator_diagnosis_review import attach_operator_diagnosis_review
                    return attach_operator_diagnosis_review(diagnosed, runtime_root=runtime_root)
                except Exception:
                    return diagnosed
            except Exception:
                # Diagnosis is subordinate to the authoritative continuation
                # result.  Its own contract fails closed and must never erase
                # or reinterpret the already-sealed build/test outcome.
                return continuation_control
    except Exception:
        pass
    # v1211 recognizes only the exact operator-result decision grammar.  It is
    # checked before the v1210 execution control and otherwise remains inert.
    try:
        from operator_build_test_results import process_operator_build_test_result_control
        result_control = process_operator_build_test_result_control(text, runtime_root=runtime_root)
        if result_control.get("active"):
            return result_control
    except Exception:
        pass
    # v1259.3-v1259.5 distinguishes explicit corrections and cancellations
    # from ordinary discussion while preserving exact existing authority
    # contracts. Generic authorization is recognized but cannot approve or
    # execute anything; ambiguous proposal references fail closed.
    try:
        from conversational_command_integration import process_conversational_development_control
        conversational_command_control = process_conversational_development_control(
            text, session_id=session_id, runtime_root=runtime_root
        )
        if conversational_command_control.get("active"):
            return conversational_command_control
    except Exception:
        pass

    # v1256.3-v1256.5 restores persistent development-session state from the
    # current v1254/v1255 lineage. Resume/status controls are read-only with
    # respect to providers, commands, tests, selected projects, and authority.
    try:
        from persistent_development_sessions import process_persistent_development_session_control
        persistent_session_control = process_persistent_development_session_control(text, runtime_root=runtime_root)
        if persistent_session_control.get("active"):
            return persistent_session_control
    except Exception:
        pass

    # v1255.3-v1255.5 adds a separate controlled selected-project application
    # and rollback authority stage. Preparation remains read-only; only the
    # exact digest-bound application or rollback phrase may mutate the selected
    # project, and neither stage contacts providers or grants release authority.
    try:
        from controlled_application_rollback import process_controlled_application_rollback_control
        controlled_application = process_controlled_application_rollback_control(
            text,
            runtime_root=runtime_root,
            python_executable=python_executable,
            node_executable=node_executable,
        )
        if controlled_application.get("active"):
            try:
                from persistent_development_sessions import attach_persistent_development_session
                return attach_persistent_development_session(controlled_application, runtime_root=runtime_root)
            except Exception:
                return controlled_application
    except Exception:
        pass

    # v1254.3-v1254.5 extends approved selected-project development through the
    # sealed isolated-coding foundation. One exact, digest-bound authorization
    # may contact the provider, change only the disposable workspace, run
    # bounded verification/repair, and seal a reviewable result. Application
    # to the selected project remains a later authority stage.
    try:
        from isolated_coding_execution import process_isolated_coding_execution_control
        isolated_coding_control = process_isolated_coding_execution_control(
            text,
            runtime_root=runtime_root,
            provider_generate=provider_generate,
            python_executable=python_executable,
            node_executable=node_executable,
        )
        if isolated_coding_control.get("active"):
            try:
                from persistent_development_sessions import attach_persistent_development_session
                return attach_persistent_development_session(isolated_coding_control, runtime_root=runtime_root)
            except Exception:
                return isolated_coding_control
    except Exception:
        pass

    # v1210 retains the ordinary chat path: one exact, digest-bound control may
    # start the already-prepared supervised build-and-test loop.  Import lazily
    # to avoid changing proposal-storage ownership or module initialization.
    try:
        from conversational_build_test_loop import process_conversational_build_test_control
        build_test_control = process_conversational_build_test_control(
            text,
            runtime_root=runtime_root,
            provider_generate=provider_generate,
            node_executable=node_executable,
            python_executable=python_executable,
            chromium_executable=chromium_executable,
        )
        if build_test_control.get("active"):
            return build_test_control
    except Exception:
        # A malformed or unavailable optional control surface must not interfere
        # with the retained proposal controls or turn an ordinary message into an
        # action. Exact controls still fail closed in their own public result.
        pass
    for regex, action in ((_APPROVAL, "approve"), (_REJECTION, "reject"), (_CANCELLATION, "cancel")):
        match = regex.fullmatch(text)
        if not match:
            continue
        proposal_id = match.group("proposal_id").lower()
        revision = int(match.group("revision"))
        if action == "approve":
            outcome = approve_development_campaign_proposal(proposal_id, revision=revision, runtime_root=runtime_root)
            if outcome.get("status") == "approval_consumed":
                event = "approval_consumed"
            elif outcome.get("status") == "approval_already_consumed":
                event = "approval_replayed"
            elif outcome.get("status") == "stale_approval_rejected":
                event = "stale_control_rejected"
            else:
                event = "control_blocked"
        elif action == "reject":
            outcome = reject_development_campaign_proposal(proposal_id, revision=revision, runtime_root=runtime_root)
            event = "rejected" if outcome.get("status") in {"rejected", "already_rejected"} else ("stale_control_rejected" if outcome.get("status") == "stale_decision_rejected" else "control_blocked")
        else:
            outcome = cancel_development_campaign_proposal(proposal_id, revision=revision, runtime_root=runtime_root)
            event = "cancelled" if outcome.get("status") in {"cancelled", "already_cancelled"} else ("stale_control_rejected" if outcome.get("status") == "stale_decision_rejected" else "control_blocked")
        result = {"active": True, "event": event, **outcome}
        if event == "approval_consumed":
            try:
                from grounded_development_planning import create_or_resume_grounded_plan, public_grounded_plan
                private_plan = create_or_resume_grounded_plan(
                    proposal_id,
                    expected_revision=revision,
                    expected_revision_digest=str(outcome.get("revision_digest") or ""),
                    runtime_root=runtime_root,
                )
                result["grounded_planning"] = public_grounded_plan(private_plan) if private_plan.get("planning_digest") else {
                    "planning_status": private_plan.get("status", "planning_blocked"),
                    "content_free_public_projection": True,
                }
            except Exception as error:
                result["grounded_planning"] = {
                    "planning_status": "planning_blocked",
                    "reason_digest": hashlib.sha256(str(error).encode("utf-8")).hexdigest(),
                    "content_free_public_projection": True,
                }
            try:
                from isolated_coding_execution import prepare_isolated_coding_from_approved_proposal
                isolated = prepare_isolated_coding_from_approved_proposal(
                    proposal_id,
                    expected_revision=revision,
                    expected_revision_digest=str(outcome.get("revision_digest") or ""),
                    runtime_root=runtime_root,
                )
                if isolated.get("ok"):
                    result["isolated_coding_execution"] = dict(isolated.get("execution") or {})
                    result["isolated_coding_request_id"] = str(isolated.get("request_id") or "")
                elif isolated.get("status") != "isolated_coding_selected_project_required":
                    result["isolated_coding_execution"] = {
                        "ok": False,
                        "status": str(isolated.get("status") or "isolated_coding_preparation_blocked"),
                        "operator_review_required": True,
                        "selected_project_modified": False,
                        "source_application_authorized": False,
                    }
            except Exception as error:
                result["isolated_coding_execution"] = {
                    "ok": False,
                    "status": "isolated_coding_preparation_blocked",
                    "reason_digest": hashlib.sha256(type(error).__name__.encode("utf-8")).hexdigest(),
                    "operator_review_required": True,
                    "selected_project_modified": False,
                    "source_application_authorized": False,
                }
            try:
                from conversational_build_test_loop import (
                    prepare_conversational_build_test_loop,
                    public_conversational_build_test_loop,
                )
                prepared_loop = prepare_conversational_build_test_loop(
                    proposal_id,
                    expected_revision=revision,
                    expected_revision_digest=str(outcome.get("revision_digest") or ""),
                    runtime_root=runtime_root,
                )
                result["build_test_loop"] = public_conversational_build_test_loop(prepared_loop)
            except Exception as error:
                result["build_test_loop"] = {
                    "ok": False,
                    "status": "conversational_build_test_preparation_blocked",
                    "reason_digest": hashlib.sha256(type(error).__name__.encode("utf-8")).hexdigest(),
                    "content_free": True,
                }
        if event == "approval_consumed" and result.get("isolated_coding_request_id"):
            try:
                from persistent_development_sessions import attach_persistent_development_session
                result = attach_persistent_development_session(result, runtime_root=runtime_root)
            except Exception:
                pass
        result["conversation_response"] = _conversation_text(result)
        if event == "approval_consumed" and isinstance(result.get("isolated_coding_execution"), Mapping):
            isolated_loop = result["isolated_coding_execution"]
            if isolated_loop.get("status") == "isolated_coding_execution_authorization_required":
                result["conversation_response"] += (
                    " The selected project is inspected, planned, and copied into a disposable workspace. "
                    "Provider generation, bounded tests, and up to two isolated repair attempts require one separate exact authorization. "
                    f"To start that exact isolated execution, say: {isolated_loop.get('authorization_phrase', '')}"
                )
        elif event == "approval_consumed" and isinstance(result.get("build_test_loop"), Mapping):
            loop = result["build_test_loop"]
            if loop.get("status") == "conversational_build_test_authorization_required":
                result["conversation_response"] += (
                    " The grounded proposal is ready for a separately authorized build-and-test loop. "
                    f"To start that exact loop, say: {loop.get('authorization_phrase', '')}"
                )
        result["public_digest"] = _digest({key: value for key, value in result.items() if key not in {"conversation_response"}})
        return result

    projection = dict(action_projection or {})
    grounding = dict(projection.get("grounding") or {})
    intent = dict(projection.get("intent") or {})
    matched = bool(
        grounding.get("grounding_status") == "matched" and grounding.get("capability_id") == "software_development"
    )
    # v1431+ command distinction operates at clause granularity.  This lets an
    # ordinary conversational turn carry one explicit software-development
    # command without promoting wishes, hypotheticals, quotations, or questions
    # into authority-bearing work.  Raw actionable text stays in-process; the
    # durable mixed-intent evidence remains content-free/digest-only.
    try:
        from unified_companion_developer import actionable_clauses, understand_mixed_intent
        mixed_intent = understand_mixed_intent(text)
        explicit_action_clauses = actionable_clauses(text)
        explicit_development_text = " ".join(explicit_action_clauses)
        mixed_intent_payload = dict(mixed_intent.get("payload") or {})
    except Exception:
        explicit_development_text = text if intent.get("category") == "action_request" else ""
        mixed_intent_payload = {}
    development_shaped_action = bool(
        (explicit_development_text and _DEVELOPMENT_REQUEST.search(explicit_development_text))
        # Forbidden self-authority/model-management requests are intentionally
        # admitted only to the proposal classifier so it can produce a durable,
        # explicit unsupported_request receipt. The mixed-intent clause layer may
        # suppress these actions precisely because they are forbidden; letting
        # that suppression make the development intake inactive loses the safety
        # evidence and breaks conversation-to-governance coherence. This does not
        # grant authority or create an execution path.
        or (intent.get("category") == "action_request" and _FORBIDDEN_AUTHORITY.search(text))
    )
    # Retained grounding metadata may identify the whole turn as development.
    # When the new clause policy positively identifies zero actionable clauses
    # in a suggestion/hypothetical-only turn, it wins over that coarse match.
    if mixed_intent_payload and not explicit_development_text:
        clause_kinds = {str(row.get("intent") or "") for row in mixed_intent_payload.get("clauses") or []}
        if clause_kinds & {"suggestion", "hypothetical", "question"}:
            matched = False
    if not (matched or development_shaped_action):
        return {
            "active": False,
            "event": "inactive",
            "conversation_response": "",
            "provider_contacted": False,
            "runtime_mutated": False,
            "source_modified": False,
            "authority_granted": False,
        }
    proposal_request_text = explicit_development_text or text
    proposal = create_or_resume_development_proposal(
        proposal_request_text, session_id=session_id, project_state=project_state, runtime_root=runtime_root,
    )
    if proposal.get("status") in {"invalid_request", "tampered"}:
        result = {"active": True, "event": "control_blocked", "reason": proposal.get("status"), "proposal_id": proposal.get("proposal_id", "")}
    else:
        event = "proposal_created" if proposal.get("operation_status") == "created" else "proposal_resumed"
        result = {"active": True, "event": event, "proposal": public_development_campaign_proposal(proposal)}
    # v1304 augments the retained development proposal with the same content-free
    # durable goal contract used by imported issues and dashboard actions. It does
    # not replace the legacy proposal response or its exact approval semantics.
    if result.get("event") in {"proposal_created", "proposal_resumed"}:
        try:
            from goal_intake import intake_goal
            source_kind = "casual_conversation_command" if matched else "direct_command"
            workspace_hint = str((project_state or {}).get("workspace_digest") or "")[:64]
            goal_intake_result = intake_goal(
                source_kind=source_kind, request_text=proposal_request_text, workspace_digest=workspace_hint,
                metadata={"proposal_id": str((result.get("proposal") or {}).get("proposal_id") or "")},
            )
            result["goal_intake"] = {
                "status": goal_intake_result.get("status"),
                "source_kind": goal_intake_result.get("source_kind"),
                "source_digest": goal_intake_result.get("source_digest"),
                "goal": dict(goal_intake_result.get("goal") or {}),
                "action_executed": False,
            }
        except Exception:
            result["goal_intake"] = {"status": "goal_intake_unavailable", "action_executed": False}
        # Era 3 augments the proposal with a private-runtime problem frame and
        # bounded clarification judgment.  It does not veto, approve, execute,
        # or expand the proposal; it makes ambiguity visible before later
        # planning stages consume the request.
        try:
            from problem_framing_intelligence import build_problem_frame, judge_clarification
            frame = build_problem_frame(
                proposal_request_text,
                project_evidence={
                    "workspace_digest": str((project_state or {}).get("workspace_digest") or "")[:64],
                    "project_id": str((project_state or {}).get("project_id") or (project_state or {}).get("id") or "")[:120],
                },
                source_kind="ordinary_chat_development_request",
                runtime_root=runtime_root,
            )
            if frame.get("ok") and frame.get("problem_frame_id") and frame.get("problem_frame_digest"):
                judgment = judge_clarification(
                    str(frame["problem_frame_id"]), str(frame["problem_frame_digest"]), runtime_root=runtime_root
                )
                result["problem_framing"] = {
                    "status": frame.get("status"),
                    "problem_frame_id": frame.get("problem_frame_id"),
                    "problem_frame_digest": frame.get("problem_frame_digest"),
                    "counts": dict(frame.get("counts") or {}),
                    "clarification_judgment": judgment.get("judgment"),
                    "clarification_reason_code": judgment.get("reason_code"),
                    "automatic_execution": False,
                    "authority_granted": False,
                }
        except Exception:
            result["problem_framing"] = {"status": "problem_framing_unavailable", "automatic_execution": False, "authority_granted": False}
    result["conversation_response"] = _conversation_text(result)
    result["public_digest"] = _digest({key: value for key, value in result.items() if key not in {"conversation_response"}})
    return result


def development_campaign_conversation_prompt(projection: Mapping[str, Any]) -> str:
    if not projection.get("active"):
        return "Ordinary-chat development campaign lifecycle: inactive for this turn."
    response = str(projection.get("conversation_response") or "")
    return "\n".join((
        "Ordinary-chat development campaign lifecycle (authoritative runtime state):",
        f"- Event: {projection.get('event', 'unknown')}.",
        f"- Required lifecycle response: {response}",
        "- State is persisted only in external runtime data; public evidence is digest-only and excludes request text and private paths.",
        "- Do not imply that implementation, provider generation, file creation, command execution, source mutation, model management, release promotion, or independent authority occurred.",
        "- Approval is valid only through the exact proposal id and revision phrase shown above. 'Go ahead', refreshes, retries, duplicate messages, and multiple tabs are not approval.",
    ))


def development_campaign_public_projection(projection: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {
        "active", "event", "proposal_id", "revision", "revision_digest", "receipt_digest",
        "approval_consumed_now", "approval_consumption_count", "idempotent_replay", "status",
        "reason", "public_digest", "implementation_started", "source_modified", "authority_granted",
    }
    result = {key: projection.get(key) for key in allowed if key in projection}
    if isinstance(projection.get("proposal"), Mapping):
        result["proposal"] = dict(projection["proposal"])
    result.update({
        "conversation_response_required": bool(projection.get("conversation_response")),
        "private_request_included": False,
        "private_path_included": False,
        "content_free": True,
    })
    return result
