from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from memory_application_dry_run_ledger import (
    EXPECTED_MEMORY_CONFIRMATION_PHRASE,
    build_memory_application_dry_run_ledger_entry_summary,
    build_memory_application_ledger_replay_summary,
)

SANDBOX_MEMORY_WRITE_TARGET_VERSION = "500.0"
SANDBOX_MEMORY_ROOT_NAME = "sandbox_memory_trials"
SANDBOX_MEMORY_DEFAULT_FILE = "memory_write_trial.json"

SANDBOX_MEMORY_BOUNDARIES: dict[str, bool] = {
    "sandbox_write_target_writes_live_memory": False,
    "sandbox_transaction_is_live_memory_approval": False,
    "sandbox_trial_accepts_non_sandbox_path": False,
    "sandbox_retraction_executes_live_retraction": False,
    "sandbox_audit_grants_future_authorization": False,
    "sandbox_write_mutates_identity": False,
    "sandbox_write_alters_personality": False,
    "sandbox_write_rewrites_purpose": False,
    "sandbox_write_expands_autonomy": False,
    "sandbox_write_invokes_models": False,
    "operator_review_required": True,
    "exact_confirmation_required": True,
    "dry_run_ledger_required": True,
    "before_after_hash_required": True,
    "sandbox_path_required": True,
    "retraction_preview_required": True,
    "live_memory_allowed": False,
}

SAFE_SANDBOX_MEMORY_TEXT = "Eidolon must treat memory application evidence as review-only until a fresh exact operator approval authorizes a single scoped write."


def _stable_hash(value: Any) -> str:
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _sandbox_root(root: str | Path | None = None) -> Path:
    base = Path(root) if root is not None else Path("data")
    return base / SANDBOX_MEMORY_ROOT_NAME


def _default_sandbox_path(root: str | Path | None = None) -> Path:
    return _sandbox_root(root) / SANDBOX_MEMORY_DEFAULT_FILE


def _is_sandbox_path(path: str | Path, root: str | Path | None = None) -> bool:
    target = Path(path)
    parts = set(target.parts)
    if SANDBOX_MEMORY_ROOT_NAME not in parts:
        return False
    lowered = str(target).replace("\\", "/").lower()
    if lowered.endswith("memory.json") or "/live" in lowered or "live_memory" in lowered:
        return False
    if root is not None:
        try:
            target.resolve().relative_to(_sandbox_root(root).resolve())
        except Exception:
            return False
    return True


def _read_json(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict) and isinstance(data.get("entries"), list):
        return [row for row in data.get("entries", []) if isinstance(row, dict)]
    return []


def _file_hash(path: Path) -> str:
    if not path.exists():
        return "missing"
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def build_sandbox_memory_target_schema_summary(root: str | Path | None = None, target_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(target_path) if target_path is not None else _default_sandbox_path(root)
    sandbox_scoped = _is_sandbox_path(path, root)
    return {
        "version": SANDBOX_MEMORY_WRITE_TARGET_VERSION,
        "state": "sandbox_memory_write_target_schema_review_only",
        "sandbox_target_id": "sandbox-memory-target-v415-001",
        "sandbox_file_path": str(path),
        "sandbox_scoped": sandbox_scoped,
        "live_memory_allowed": False,
        "write_allowed_by_default": False,
        "operator_confirmation_required": True,
        "required_fields": ["sandbox_target_id", "sandbox_file_path", "candidate_id", "approval_id", "memory_text", "memory_text_hash", "pre_write_hash", "post_write_hash"],
        "boundaries": dict(SANDBOX_MEMORY_BOUNDARIES),
        "status": "reviewable" if sandbox_scoped else "blocked",
        "ok": sandbox_scoped,
        "writes_live_memory": False,
        "safe_next_action": "Operator may review sandbox target schema. This does not approve a live memory write.",
    }


def build_sandbox_memory_write_transaction_summary(root: str | Path | None = None, target_path: str | Path | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = dict(evidence or {})
    target = build_sandbox_memory_target_schema_summary(root, target_path)
    exact = evidence.get("operator_confirmation_phrase") == EXPECTED_MEMORY_CONFIRMATION_PHRASE
    ledger = build_memory_application_dry_run_ledger_entry_summary("sandbox review", evidence)
    replay = build_memory_application_ledger_replay_summary(ledger.get("ledger_entry", {}), evidence)
    entry = dict(ledger.get("ledger_entry", {}))
    memory_text = str(entry.get("memory_text_preview") or SAFE_SANDBOX_MEMORY_TEXT)
    blockers: list[str] = []
    if target.get("ok") is not True:
        blockers.append("sandbox-target-invalid")
    if ledger.get("ok") is not True:
        blockers.append("dry-run-ledger-blocked")
    if replay.get("ok") is not True:
        blockers.append("dry-run-replay-drift")
    if not exact:
        blockers.append("operator-confirmation-not-exact")
    if evidence.get("live_memory_requested") is True or evidence.get("write_live_memory") is True:
        blockers.append("live-memory-write-requested")
    if evidence.get("identity_or_personality_mutation") is True:
        blockers.append("identity-personality-mutation-requested")
    if evidence.get("autonomy_expansion") is True:
        blockers.append("autonomy-expansion-requested")
    transaction = {
        "sandbox_transaction_id": "sandbox-memory-write-" + _stable_hash({"entry": entry, "target": target.get("sandbox_file_path")}),
        "sandbox_file_path": target.get("sandbox_file_path"),
        "candidate_id": entry.get("candidate_id"),
        "approval_id": entry.get("approval_id"),
        "memory_text": memory_text,
        "memory_text_hash": _stable_hash(memory_text),
        "candidate_hash": entry.get("candidate_hash"),
        "transaction_preview_hash": entry.get("transaction_preview_hash"),
        "confirmation_exact": exact,
        "pre_write_hash": _file_hash(Path(str(target.get("sandbox_file_path")))),
        "post_write_hash": None,
        "sandbox_only": True,
        "live_memory_allowed": False,
        "write_readiness_is_live_approval": False,
    }
    return {
        "version": SANDBOX_MEMORY_WRITE_TARGET_VERSION,
        "state": "sandbox_memory_write_transaction_review_only",
        "target": target,
        "dry_run_ledger": ledger,
        "replay": replay,
        "transaction": transaction,
        "blockers": blockers,
        "status": "reviewable" if not blockers else "blocked",
        "ok": not blockers,
        "writes_live_memory": False,
        "safe_next_action": "Operator may review sandbox write readiness. Sandbox write readiness is not live memory approval.",
    }


def execute_sandbox_memory_write_trial(root: str | Path | None = None, target_path: str | Path | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    transaction_summary = build_sandbox_memory_write_transaction_summary(root, target_path, evidence)
    transaction = dict(transaction_summary.get("transaction", {}))
    path = Path(str(transaction.get("sandbox_file_path")))
    blockers = list(transaction_summary.get("blockers", []))
    if not _is_sandbox_path(path, root):
        blockers.append("non-sandbox-path-blocked")
    if blockers:
        return {**transaction_summary, "state": "sandbox_memory_write_trial_blocked", "blockers": blockers, "status": "blocked", "ok": False, "executed": False, "writes_live_memory": False}
    pre_hash = _file_hash(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = _read_json(path)
    write_entry = {
        "sandbox_entry_id": "sandbox-entry-" + _stable_hash(transaction),
        "candidate_id": transaction.get("candidate_id"),
        "approval_id": transaction.get("approval_id"),
        "memory_text": transaction.get("memory_text"),
        "memory_text_hash": transaction.get("memory_text_hash"),
        "candidate_hash": transaction.get("candidate_hash"),
        "transaction_preview_hash": transaction.get("transaction_preview_hash"),
        "timestamp_policy": "deterministic-sandbox-review-placeholder",
        "sandbox_only": True,
        "live_memory_allowed": False,
    }
    rows.append(write_entry)
    path.write_text(json.dumps({"version": SANDBOX_MEMORY_WRITE_TARGET_VERSION, "entries": rows}, indent=2), encoding="utf-8")
    post_hash = _file_hash(path)
    return {
        "version": SANDBOX_MEMORY_WRITE_TARGET_VERSION,
        "state": "sandbox_memory_write_trial_executed_sandbox_only",
        "transaction": {**transaction, "pre_write_hash": pre_hash, "post_write_hash": post_hash},
        "write_entry": write_entry,
        "entry_count": len(rows),
        "pre_write_hash": pre_hash,
        "post_write_hash": post_hash,
        "executed": True,
        "status": "pass",
        "ok": True,
        "writes_live_memory": False,
        "safe_next_action": "Operator may inspect sandbox output and retraction preview. Sandbox success is not live memory approval.",
    }


def build_sandbox_memory_retraction_preview_summary(write_trial: dict[str, Any] | None = None, root: str | Path | None = None, target_path: str | Path | None = None) -> dict[str, Any]:
    trial = dict(write_trial or execute_sandbox_memory_write_trial(root, target_path, {"operator_confirmation_phrase": EXPECTED_MEMORY_CONFIRMATION_PHRASE}))
    transaction = dict(trial.get("transaction", {}))
    path = Path(str(transaction.get("sandbox_file_path") or target_path or _default_sandbox_path(root)))
    rows = _read_json(path)
    target_hash = str(trial.get("write_entry", {}).get("memory_text_hash") or transaction.get("memory_text_hash") or "")
    matched = [row for row in rows if row.get("memory_text_hash") == target_hash]
    drift = []
    if not _is_sandbox_path(path, root):
        drift.append("non-sandbox-path")
    if not matched:
        drift.append("entry-not-found")
    return {
        "version": SANDBOX_MEMORY_WRITE_TARGET_VERSION,
        "state": "sandbox_memory_retraction_preview_review_only",
        "sandbox_file_path": str(path),
        "matched_entry_count": len(matched),
        "pre_retraction_hash": _file_hash(path),
        "post_retraction_hash_preview": "computed-after-operator-approved-sandbox-retraction-only",
        "drift": drift,
        "retraction_executes_live_memory": False,
        "status": "reviewable" if not drift else "blocked",
        "ok": not drift,
        "writes_live_memory": False,
        "safe_next_action": "Operator may review sandbox retraction preview. Live memory retraction remains separately approved only.",
    }


def build_sandbox_memory_write_audit_summary(docs: str = "", root: str | Path | None = None) -> dict[str, Any]:
    import tempfile
    required_tokens = [
        "sandbox-memory-target-schema",
        "sandbox-memory-write-transaction",
        "sandbox-memory-write-trial",
        "sandbox-memory-retraction-preview",
        "sandbox-memory-write-audit",
        "operator-governed-sandbox-memory-write-target-v1",
        "sandbox_memory_write_target.py",
        "sandbox_write_target_writes_live_memory=False",
        "sandbox_trial_accepts_non_sandbox_path=False",
        "sandbox_retraction_executes_live_retraction=False",
    ]
    blockers: list[str] = []
    if docs and not all(token in docs for token in required_tokens):
        blockers.append("docs-or-source-token-missing")
    for key, value in SANDBOX_MEMORY_BOUNDARIES.items():
        if key in {"operator_review_required", "exact_confirmation_required", "dry_run_ledger_required", "before_after_hash_required", "sandbox_path_required", "retraction_preview_required"}:
            if value is not True:
                blockers.append(f"boundary:{key}")
        elif value is not False:
            blockers.append(f"boundary:{key}")
    with tempfile.TemporaryDirectory(prefix="eidolon_sandbox_memory_audit_") as tmp:
        tmp_root = Path(tmp)
        exact = {"operator_confirmation_phrase": EXPECTED_MEMORY_CONFIRMATION_PHRASE}
        schema = build_sandbox_memory_target_schema_summary(tmp_root)
        transaction = build_sandbox_memory_write_transaction_summary(tmp_root, evidence=exact)
        trial = execute_sandbox_memory_write_trial(tmp_root, evidence=exact)
        retraction = build_sandbox_memory_retraction_preview_summary(trial, tmp_root)
        non_sandbox = build_sandbox_memory_target_schema_summary(tmp_root, tmp_root / "memory.json")
        if schema.get("ok") is not True:
            blockers.append("schema-blocked")
        if transaction.get("ok") is not True:
            blockers.append("transaction-blocked")
        if trial.get("ok") is not True or trial.get("writes_live_memory") is not False:
            blockers.append("sandbox-write-trial-failed")
        if retraction.get("ok") is not True or retraction.get("retraction_executes_live_memory") is not False:
            blockers.append("retraction-preview-blocked")
        if non_sandbox.get("ok") is not False:
            blockers.append("non-sandbox-path-not-blocked")
    return {
        "version": SANDBOX_MEMORY_WRITE_TARGET_VERSION,
        "state": "sandbox_memory_write_target_audit_review_only",
        "required_tokens": required_tokens,
        "boundaries": dict(SANDBOX_MEMORY_BOUNDARIES),
        "blockers": blockers,
        "status": "pass" if not blockers else "blocked",
        "ok": not blockers,
        "writes_live_memory": False,
        "applies_patches": False,
        "expands_autonomy": False,
        "safe_next_action": "Proceed only to operator review of sandbox results. Live memory writes still require a later fresh single-use approval arc.",
    }


def render_sandbox_memory_lines(summary: dict[str, Any]) -> list[str]:
    lines = [
        f"- version: {summary.get('version')}",
        f"- state: {summary.get('state')}",
        f"- status: {summary.get('status')}",
        f"- ok: {summary.get('ok')}",
        f"- writes_live_memory: {summary.get('writes_live_memory', False)}",
    ]
    blockers = summary.get("blockers") or summary.get("drift") or []
    if blockers:
        lines.append("- blockers: " + ", ".join(map(str, blockers)))
    if summary.get("safe_next_action"):
        lines.append("- safe_next_action: " + str(summary.get("safe_next_action")))
    return lines
