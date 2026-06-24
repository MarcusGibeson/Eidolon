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
from sandbox_memory_write_target import (
    SAFE_SANDBOX_MEMORY_TEXT,
    build_sandbox_memory_write_transaction_summary,
    execute_sandbox_memory_write_trial,
    build_sandbox_memory_retraction_preview_summary,
)

LIVE_MEMORY_WRITE_TRIAL_VERSION = "500.0"
LIVE_MEMORY_TRIAL_ROOT_NAME = "memory_application_trials"
LIVE_MEMORY_TRIAL_FILE = "operator_approved_live_memory_write_trial.json"
SAFE_FIRST_LIVE_MEMORY_TEXT = "Eidolon must not treat sandbox success, eligibility, readiness, or prior approval as authorization for future memory writes."

LIVE_MEMORY_WRITE_BOUNDARIES: dict[str, bool] = {
    "eligibility_is_approval": False,
    "sandbox_success_is_approval": False,
    "approval_lock_reuses_approval": False,
    "transaction_preview_writes_memory": False,
    "live_write_runs_without_confirmation": False,
    "live_write_allows_batch": False,
    "live_write_mutates_identity": False,
    "live_write_alters_personality": False,
    "live_write_rewrites_purpose": False,
    "live_write_expands_autonomy": False,
    "live_write_invokes_models": False,
    "live_write_applies_patches": False,
    "audit_grants_future_authorization": False,
    "exact_confirmation_required": True,
    "single_use_approval_required": True,
    "approval_burnout_required": True,
    "dry_run_ledger_required": True,
    "sandbox_trial_required": True,
    "retraction_preview_required": True,
    "operator_review_required": True,
}


def _stable_hash(value: Any) -> str:
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _trial_root(root: str | Path | None = None) -> Path:
    base = Path(root) if root is not None else Path("data")
    return base / LIVE_MEMORY_TRIAL_ROOT_NAME


def _default_live_trial_path(root: str | Path | None = None) -> Path:
    return _trial_root(root) / LIVE_MEMORY_TRIAL_FILE


def _is_governed_live_trial_path(path: str | Path, root: str | Path | None = None) -> bool:
    target = Path(path)
    lowered = str(target).replace("\\", "/").lower()
    if LIVE_MEMORY_TRIAL_ROOT_NAME not in target.parts:
        return False
    if lowered.endswith("memory.json") or "canonical_memory" in lowered or "identity" in lowered or "personality" in lowered or "purpose" in lowered:
        return False
    if root is not None:
        try:
            target.resolve().relative_to(_trial_root(root).resolve())
        except Exception:
            return False
    return True


def _read_entries(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(data, dict) and isinstance(data.get("entries"), list):
        return [row for row in data["entries"] if isinstance(row, dict)]
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    return []


def _file_hash(path: Path) -> str:
    if not path.exists():
        return "missing"
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _base_evidence(evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    merged = dict(evidence or {})
    merged.setdefault("memory_text", SAFE_FIRST_LIVE_MEMORY_TEXT)
    return merged


def build_live_memory_write_eligibility_summary(root: str | Path | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = _base_evidence(evidence)
    exact = evidence.get("operator_confirmation_phrase") == EXPECTED_MEMORY_CONFIRMATION_PHRASE
    ledger = build_memory_application_dry_run_ledger_entry_summary("live memory review", evidence)
    replay = build_memory_application_ledger_replay_summary(ledger.get("ledger_entry", {}), evidence)
    sandbox_transaction = build_sandbox_memory_write_transaction_summary(root, evidence=evidence)
    sandbox_trial = execute_sandbox_memory_write_trial(root, evidence=evidence)
    sandbox_retraction = build_sandbox_memory_retraction_preview_summary(sandbox_trial, root)
    blockers: list[str] = []
    if ledger.get("ok") is not True:
        blockers.append("dry-run-ledger-not-reviewable")
    if replay.get("ok") is not True:
        blockers.append("dry-run-ledger-replay-drift")
    if sandbox_transaction.get("ok") is not True:
        blockers.append("sandbox-transaction-not-reviewable")
    if sandbox_trial.get("ok") is not True or sandbox_trial.get("executed") is not True:
        blockers.append("sandbox-write-trial-missing")
    if sandbox_retraction.get("ok") is not True:
        blockers.append("sandbox-retraction-preview-missing")
    if not exact:
        blockers.append("operator-confirmation-not-exact")
    if evidence.get("approval_reused") is True or evidence.get("approval_burned_out") is True:
        blockers.append("approval-not-fresh")
    if evidence.get("batch_write") is True:
        blockers.append("batch-memory-write-requested")
    if evidence.get("identity_or_personality_mutation") is True:
        blockers.append("identity-personality-mutation-requested")
    if evidence.get("purpose_rewrite") is True:
        blockers.append("purpose-rewrite-requested")
    if evidence.get("autonomy_expansion") is True:
        blockers.append("autonomy-expansion-requested")
    if evidence.get("sensitive_private_data") is True:
        blockers.append("sensitive-private-data-requested")
    return {
        "version": LIVE_MEMORY_WRITE_TRIAL_VERSION,
        "state": "live_memory_write_eligibility_review_only",
        "ledger": ledger,
        "replay": replay,
        "sandbox_transaction": sandbox_transaction,
        "sandbox_trial_hash": _stable_hash(sandbox_trial.get("write_entry", {})),
        "sandbox_retraction": sandbox_retraction,
        "candidate_id": ledger.get("ledger_entry", {}).get("candidate_id"),
        "approval_id": ledger.get("ledger_entry", {}).get("approval_id"),
        "memory_text": evidence.get("memory_text") or SAFE_FIRST_LIVE_MEMORY_TEXT,
        "memory_text_hash": _stable_hash(evidence.get("memory_text") or SAFE_FIRST_LIVE_MEMORY_TEXT),
        "blockers": blockers,
        "status": "eligible_for_operator_review" if not blockers else "blocked",
        "ok": not blockers,
        "eligibility_is_approval": False,
        "writes_memory": False,
        "boundaries": dict(LIVE_MEMORY_WRITE_BOUNDARIES),
        "safe_next_action": "Operator may review eligibility. Eligibility, sandbox success, and dry-run evidence are not live memory approval.",
    }


def build_live_memory_approval_lock_summary(root: str | Path | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = _base_evidence(evidence)
    eligibility = build_live_memory_write_eligibility_summary(root, evidence)
    exact = evidence.get("operator_confirmation_phrase") == EXPECTED_MEMORY_CONFIRMATION_PHRASE
    blockers = list(eligibility.get("blockers", []))
    if evidence.get("approval_reused") is True or evidence.get("approval_burned_out") is True:
        blockers.append("single-use-approval-already-burned")
    if not exact:
        blockers.append("exact-live-memory-confirmation-required")
    lock = {
        "live_memory_approval_lock_id": "live-memory-lock-" + _stable_hash({"eligibility": eligibility.get("candidate_id"), "memory": eligibility.get("memory_text_hash")}),
        "candidate_id": eligibility.get("candidate_id"),
        "approval_id": eligibility.get("approval_id"),
        "memory_text_hash": eligibility.get("memory_text_hash"),
        "dry_run_ledger_hash": _stable_hash(eligibility.get("ledger", {}).get("ledger_entry", {})),
        "sandbox_trial_hash": eligibility.get("sandbox_trial_hash"),
        "operator_confirmation_exact": exact,
        "single_use": True,
        "burned_out": False,
        "approval_reuse_allowed": False,
    }
    return {
        "version": LIVE_MEMORY_WRITE_TRIAL_VERSION,
        "state": "single_use_live_memory_approval_lock_review_only",
        "eligibility": eligibility,
        "approval_lock": lock,
        "blockers": blockers,
        "status": "locked_for_operator_review" if not blockers else "blocked",
        "ok": not blockers,
        "writes_memory": False,
        "approval_lock_reuses_approval": False,
        "safe_next_action": "Operator may review single-use approval lock. It is not reusable and does not write memory.",
    }


def build_live_memory_transaction_preview_summary(root: str | Path | None = None, target_path: str | Path | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = _base_evidence(evidence)
    lock = build_live_memory_approval_lock_summary(root, evidence)
    path = Path(target_path) if target_path is not None else _default_live_trial_path(root)
    blockers = list(lock.get("blockers", []))
    if not _is_governed_live_trial_path(path, root):
        blockers.append("live-memory-target-not-governed-trial-path")
    memory_text = str(evidence.get("memory_text") or SAFE_FIRST_LIVE_MEMORY_TEXT)
    preview = {
        "live_memory_transaction_id": "live-memory-tx-" + _stable_hash({"lock": lock.get("approval_lock"), "target": str(path), "memory_text": memory_text}),
        "target_memory_store_path": str(path),
        "candidate_id": lock.get("approval_lock", {}).get("candidate_id"),
        "approval_id": lock.get("approval_lock", {}).get("approval_id"),
        "approval_lock_id": lock.get("approval_lock", {}).get("live_memory_approval_lock_id"),
        "memory_text": memory_text,
        "memory_text_hash": _stable_hash(memory_text),
        "pre_write_hash": _file_hash(path),
        "expected_post_write_hash": "computed-after-single-entry-write",
        "rollback_retraction_packet_required": True,
        "single_entry_only": True,
        "batch_write_allowed": False,
        "transaction_preview_writes_memory": False,
    }
    return {
        "version": LIVE_MEMORY_WRITE_TRIAL_VERSION,
        "state": "live_memory_transaction_preview_review_only",
        "approval_lock": lock,
        "transaction_preview": preview,
        "blockers": blockers,
        "status": "reviewable" if not blockers else "blocked",
        "ok": not blockers,
        "writes_memory": False,
        "safe_next_action": "Operator may review exact live memory transaction preview. Preview does not write memory or grant future authority.",
    }


def execute_operator_confirmed_live_memory_write_trial(root: str | Path | None = None, target_path: str | Path | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = _base_evidence(evidence)
    preview_summary = build_live_memory_transaction_preview_summary(root, target_path, evidence)
    preview = dict(preview_summary.get("transaction_preview", {}))
    path = Path(str(preview.get("target_memory_store_path")))
    blockers = list(preview_summary.get("blockers", []))
    if evidence.get("operator_confirmation_phrase") != EXPECTED_MEMORY_CONFIRMATION_PHRASE:
        blockers.append("operator-confirmation-not-exact")
    if evidence.get("approval_reused") is True or evidence.get("approval_burned_out") is True:
        blockers.append("approval-burnout-blocked-reuse")
    if not _is_governed_live_trial_path(path, root):
        blockers.append("non-governed-live-target-blocked")
    burnout = {
        "approval_lock_id": preview.get("approval_lock_id"),
        "burned_out": True,
        "reuse_allowed": False,
        "burnout_reason": "blocked-before-write" if blockers else "single-use-live-memory-write-consumed",
    }
    if blockers:
        return {
            **preview_summary,
            "state": "operator_confirmed_live_memory_write_trial_blocked",
            "blockers": blockers,
            "executed": False,
            "approval_burnout": burnout,
            "status": "blocked",
            "ok": False,
            "writes_memory": False,
        }
    pre_hash = _file_hash(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = _read_entries(path)
    if len(rows) >= 1 and evidence.get("allow_second_write") is not True:
        return {
            **preview_summary,
            "state": "operator_confirmed_live_memory_write_trial_blocked",
            "blockers": ["trial-store-already-has-entry-single-write-only"],
            "executed": False,
            "approval_burnout": burnout,
            "status": "blocked",
            "ok": False,
            "writes_memory": False,
        }
    write_entry = {
        "live_memory_entry_id": "live-memory-entry-" + _stable_hash(preview),
        "candidate_id": preview.get("candidate_id"),
        "approval_id": preview.get("approval_id"),
        "approval_lock_id": preview.get("approval_lock_id"),
        "memory_text": preview.get("memory_text"),
        "memory_text_hash": preview.get("memory_text_hash"),
        "created_timestamp_policy": "deterministic-live-memory-trial-placeholder",
        "identity_mutation": False,
        "personality_mutation": False,
        "purpose_rewrite": False,
        "autonomy_expansion": False,
        "future_authorization_granted": False,
    }
    rows.append(write_entry)
    path.write_text(json.dumps({"version": LIVE_MEMORY_WRITE_TRIAL_VERSION, "entries": rows}, indent=2), encoding="utf-8")
    post_hash = _file_hash(path)
    return {
        "version": LIVE_MEMORY_WRITE_TRIAL_VERSION,
        "state": "operator_confirmed_live_memory_write_trial_executed_single_use",
        "transaction_preview": {**preview, "pre_write_hash": pre_hash, "post_write_hash": post_hash},
        "write_entry": write_entry,
        "entry_count": len(rows),
        "executed": True,
        "approval_burnout": {**burnout, "burnout_reason": "single-use-live-memory-write-consumed"},
        "pre_write_hash": pre_hash,
        "post_write_hash": post_hash,
        "status": "pass",
        "ok": True,
        "writes_memory": True,
        "writes_identity": False,
        "alters_personality": False,
        "rewrites_purpose": False,
        "expands_autonomy": False,
        "safe_next_action": "Operator may inspect the live memory trial and burnout report. This success authorizes no future memory writes.",
    }


def build_live_memory_write_audit_summary(docs: str = "", root: str | Path | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = _base_evidence(evidence or {"operator_confirmation_phrase": EXPECTED_MEMORY_CONFIRMATION_PHRASE})
    import tempfile
    with tempfile.TemporaryDirectory(prefix="eidolon_v420_audit_") as tmp:
        trial_root = Path(root) if root is not None else Path(tmp)
        eligibility = build_live_memory_write_eligibility_summary(trial_root, evidence)
        approval_lock = build_live_memory_approval_lock_summary(trial_root, evidence)
        preview = build_live_memory_transaction_preview_summary(trial_root, evidence=evidence)
        trial = execute_operator_confirmed_live_memory_write_trial(trial_root, evidence=evidence)
        reuse_block = execute_operator_confirmed_live_memory_write_trial(trial_root, evidence={**evidence, "approval_reused": True})
        wrong_phrase = execute_operator_confirmed_live_memory_write_trial(trial_root, evidence={**evidence, "operator_confirmation_phrase": "wrong"})
        bad_target = build_live_memory_transaction_preview_summary(trial_root, trial_root / "memory.json", evidence)
    required_tokens = [
        "live-memory-write-eligibility",
        "live-memory-approval-lock",
        "live-memory-transaction-preview",
        "operator-confirmed-live-memory-write-trial",
        "live-memory-write-audit",
        "operator-governed-live-memory-write-burnout-v1",
        "live_memory_write_trial.py",
        "eligibility_is_approval=False",
        "sandbox_success_is_approval=False",
        "approval_burnout_required=True",
    ]
    blockers: list[str] = []
    if eligibility.get("ok") is not True:
        blockers.append("eligibility-blocked")
    if approval_lock.get("ok") is not True:
        blockers.append("approval-lock-blocked")
    if preview.get("ok") is not True or preview.get("writes_memory") is not False:
        blockers.append("preview-invalid")
    if trial.get("ok") is not True or trial.get("executed") is not True or trial.get("writes_memory") is not True:
        blockers.append("single-live-write-not-proven")
    if trial.get("approval_burnout", {}).get("burned_out") is not True:
        blockers.append("approval-burnout-missing")
    if reuse_block.get("ok") is not False:
        blockers.append("approval-reuse-not-blocked")
    if wrong_phrase.get("ok") is not False:
        blockers.append("wrong-phrase-not-blocked")
    if bad_target.get("ok") is not False:
        blockers.append("bad-target-not-blocked")
    if docs and not all(token in docs for token in required_tokens):
        blockers.append("docs-or-source-token-missing")
    for key, value in LIVE_MEMORY_WRITE_BOUNDARIES.items():
        if key.endswith("required") or key == "operator_review_required":
            if value is not True:
                blockers.append(f"boundary:{key}")
        elif value is not False:
            blockers.append(f"boundary:{key}")
    return {
        "version": LIVE_MEMORY_WRITE_TRIAL_VERSION,
        "state": "live_memory_write_burnout_audit",
        "eligibility": eligibility,
        "approval_lock": approval_lock,
        "transaction_preview": preview,
        "trial": trial,
        "reuse_block": reuse_block,
        "wrong_phrase_block": wrong_phrase,
        "bad_target_block": bad_target,
        "boundaries": dict(LIVE_MEMORY_WRITE_BOUNDARIES),
        "required_tokens": required_tokens,
        "blockers": blockers,
        "status": "pass" if not blockers else "blocked",
        "ok": not blockers,
        "writes_memory": trial.get("writes_memory") is True,
        "grants_future_authorization": False,
        "applies_patches": False,
        "expands_autonomy": False,
        "safe_next_action": "Proceed only to operator-approved memory retraction trial design; this audit grants no future memory-write approval.",
    }


def render_live_memory_write_lines(summary: dict[str, Any]) -> list[str]:
    lines = [
        f"- version: {summary.get('version')}",
        f"- state: {summary.get('state')}",
        f"- status: {summary.get('status')}",
        f"- ok: {summary.get('ok')}",
        f"- writes_memory: {summary.get('writes_memory', False)}",
        f"- grants_future_authorization: {summary.get('grants_future_authorization', False)}",
    ]
    if isinstance(summary.get("blockers"), list):
        lines.append("- blockers: " + (", ".join(summary.get("blockers", [])) or "none"))
    lock = summary.get("approval_lock")
    if isinstance(lock, dict):
        lock_payload = lock.get("approval_lock", lock)
        if isinstance(lock_payload, dict):
            lines.append(f"- approval_lock_id: {lock_payload.get('live_memory_approval_lock_id')}")
            lines.append(f"- single_use: {lock_payload.get('single_use')}")
    burnout = summary.get("approval_burnout") or summary.get("trial", {}).get("approval_burnout") if isinstance(summary.get("trial"), dict) else None
    if isinstance(burnout, dict):
        lines.append(f"- approval_burned_out: {burnout.get('burned_out')}")
        lines.append(f"- reuse_allowed: {burnout.get('reuse_allowed')}")
    return lines


# v415.1-v420.0 live memory write smoke tokens: live-memory-write-eligibility live-memory-approval-lock live-memory-transaction-preview operator-confirmed-live-memory-write-trial live-memory-write-audit operator-governed-live-memory-write-burnout-v1 live_memory_write_trial.py eligibility_is_approval=False sandbox_success_is_approval=False approval_lock_reuses_approval=False transaction_preview_writes_memory=False live_write_runs_without_confirmation=False live_write_allows_batch=False approval_burnout_required=True single_use_approval_required=True exact_confirmation_required=True dry_run_ledger_required=True sandbox_trial_required=True retraction_preview_required=True audit_grants_future_authorization=False
