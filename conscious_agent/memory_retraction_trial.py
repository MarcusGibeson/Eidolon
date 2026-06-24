from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from memory_application_dry_run_ledger import EXPECTED_MEMORY_CONFIRMATION_PHRASE
from live_memory_write_trial import (
    SAFE_FIRST_LIVE_MEMORY_TEXT,
    LIVE_MEMORY_TRIAL_ROOT_NAME,
    LIVE_MEMORY_TRIAL_FILE,
    _default_live_trial_path,
    _file_hash,
    _is_governed_live_trial_path,
    _read_entries,
    _stable_hash,
    execute_operator_confirmed_live_memory_write_trial,
)

MEMORY_RETRACTION_TRIAL_VERSION = "500.0"
EXPECTED_MEMORY_RETRACTION_CONFIRMATION_PHRASE = "I APPROVE THIS SINGLE MEMORY RETRACTION TRIAL"

MEMORY_RETRACTION_BOUNDARIES: dict[str, bool] = {
    "write_approval_authorizes_retraction": False,
    "retraction_eligibility_is_approval": False,
    "retraction_preview_deletes_memory": False,
    "retraction_runs_without_confirmation": False,
    "retraction_allows_batch": False,
    "retraction_uses_fuzzy_match": False,
    "retraction_deletes_canonical_memory_json": False,
    "retraction_mutates_identity": False,
    "retraction_alters_personality": False,
    "retraction_rewrites_purpose": False,
    "retraction_expands_autonomy": False,
    "audit_grants_future_retraction_authority": False,
    "fresh_retraction_approval_required": True,
    "single_use_retraction_approval_required": True,
    "exact_retraction_confirmation_required": True,
    "prior_write_burnout_required": True,
    "retained_audit_record_required": True,
    "operator_review_required": True,
}


def _load_trial(path: Path) -> dict[str, Any]:
    entries = _read_entries(path)
    active = [row for row in entries if row.get("status") != "retracted"]
    return {"entries": entries, "active_entries": active, "entry_count": len(entries), "active_entry_count": len(active)}


def _default_evidence(evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    merged = dict(evidence or {})
    merged.setdefault("memory_text", SAFE_FIRST_LIVE_MEMORY_TEXT)
    return merged


def _target_entry(path: Path, evidence: dict[str, Any]) -> dict[str, Any] | None:
    entries = _load_trial(path).get("active_entries", [])
    target_id = evidence.get("retraction_target_entry_id") or evidence.get("live_memory_entry_id")
    if target_id:
        for row in entries:
            if row.get("live_memory_entry_id") == target_id:
                return row
        return None
    if len(entries) == 1:
        return entries[0]
    return None


def _ensure_demo_trial(root: str | Path | None, evidence: dict[str, Any]) -> dict[str, Any]:
    path = _default_live_trial_path(root)
    existing = _load_trial(path)
    if existing.get("active_entry_count", 0) >= 1:
        return {"ok": True, "executed": False, "target_path": str(path), "preexisting": True}
    write_evidence = {"operator_confirmation_phrase": EXPECTED_MEMORY_CONFIRMATION_PHRASE, "memory_text": evidence.get("memory_text", SAFE_FIRST_LIVE_MEMORY_TEXT)}
    return execute_operator_confirmed_live_memory_write_trial(root, evidence=write_evidence)


def build_memory_retraction_eligibility_summary(root: str | Path | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = _default_evidence(evidence)
    _ensure_demo_trial(root, evidence)
    path = _default_live_trial_path(root)
    store = _load_trial(path)
    entry = _target_entry(path, evidence)
    blockers: list[str] = []
    if not _is_governed_live_trial_path(path, root):
        blockers.append("retraction-target-not-governed-trial-path")
    if store.get("active_entry_count") != 1:
        blockers.append("exactly-one-active-entry-required")
    if not entry:
        blockers.append("exact-retraction-target-not-found")
    if evidence.get("batch_retraction") is True:
        blockers.append("batch-retraction-requested")
    if evidence.get("fuzzy_match") is True:
        blockers.append("fuzzy-retraction-match-requested")
    if evidence.get("identity_or_personality_mutation") is True:
        blockers.append("identity-personality-mutation-requested")
    if evidence.get("purpose_rewrite") is True:
        blockers.append("purpose-rewrite-requested")
    if evidence.get("autonomy_expansion") is True:
        blockers.append("autonomy-expansion-requested")
    if entry and entry.get("future_authorization_granted") is not False:
        blockers.append("entry-future-authorization-boundary-invalid")
    if entry and entry.get("memory_text_hash") != _stable_hash(evidence.get("memory_text", SAFE_FIRST_LIVE_MEMORY_TEXT)):
        blockers.append("memory-text-hash-drift")
    return {
        "version": MEMORY_RETRACTION_TRIAL_VERSION,
        "state": "memory_retraction_eligibility_review_only",
        "target_store_path": str(path),
        "target_entry": entry,
        "target_entry_id": entry.get("live_memory_entry_id") if entry else None,
        "target_memory_text_hash": entry.get("memory_text_hash") if entry else None,
        "store_hash": _file_hash(path),
        "blockers": blockers,
        "status": "eligible_for_operator_review" if not blockers else "blocked",
        "ok": not blockers,
        "writes_memory": False,
        "deletes_memory": False,
        "retraction_eligibility_is_approval": False,
        "boundaries": dict(MEMORY_RETRACTION_BOUNDARIES),
        "safe_next_action": "Operator may review retraction eligibility. Write approval and retraction eligibility do not authorize retraction.",
    }


def build_memory_retraction_approval_lock_summary(root: str | Path | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = _default_evidence(evidence)
    eligibility = build_memory_retraction_eligibility_summary(root, evidence)
    exact = evidence.get("operator_retraction_confirmation_phrase") == EXPECTED_MEMORY_RETRACTION_CONFIRMATION_PHRASE
    blockers = list(eligibility.get("blockers", []))
    if not exact:
        blockers.append("exact-retraction-confirmation-required")
    if evidence.get("retraction_approval_reused") is True or evidence.get("retraction_approval_burned_out") is True:
        blockers.append("single-use-retraction-approval-already-burned")
    if evidence.get("write_approval_as_retraction_approval") is True:
        blockers.append("write-approval-cannot-authorize-retraction")
    lock = {
        "memory_retraction_approval_lock_id": "memory-retraction-lock-" + _stable_hash({"target": eligibility.get("target_entry_id"), "hash": eligibility.get("target_memory_text_hash")}),
        "target_entry_id": eligibility.get("target_entry_id"),
        "target_memory_text_hash": eligibility.get("target_memory_text_hash"),
        "operator_retraction_confirmation_exact": exact,
        "single_use": True,
        "burned_out": False,
        "approval_reuse_allowed": False,
        "write_approval_authorizes_retraction": False,
    }
    return {
        "version": MEMORY_RETRACTION_TRIAL_VERSION,
        "state": "single_use_memory_retraction_approval_lock_review_only",
        "eligibility": eligibility,
        "approval_lock": lock,
        "blockers": blockers,
        "status": "locked_for_operator_review" if not blockers else "blocked",
        "ok": not blockers,
        "writes_memory": False,
        "deletes_memory": False,
        "safe_next_action": "Operator may review the single-use retraction approval lock. It does not execute retraction.",
    }


def build_memory_retraction_transaction_preview_summary(root: str | Path | None = None, target_path: str | Path | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = _default_evidence(evidence)
    path = Path(target_path) if target_path is not None else _default_live_trial_path(root)
    lock = build_memory_retraction_approval_lock_summary(root, evidence)
    blockers = list(lock.get("blockers", []))
    if not _is_governed_live_trial_path(path, root):
        blockers.append("retraction-target-not-governed-trial-path")
    if str(path).replace("\\", "/").lower().endswith("memory.json"):
        blockers.append("canonical-memory-json-retraction-blocked")
    preview = {
        "memory_retraction_transaction_id": "memory-retraction-tx-" + _stable_hash({"lock": lock.get("approval_lock"), "target": str(path)}),
        "target_trial_memory_store_path": str(path),
        "target_entry_id": lock.get("approval_lock", {}).get("target_entry_id"),
        "target_memory_text_hash": lock.get("approval_lock", {}).get("target_memory_text_hash"),
        "pre_retraction_store_hash": _file_hash(path),
        "expected_post_retraction_store_hash": "computed-after-status-marked-retracted",
        "retained_audit_record": True,
        "physical_delete": False,
        "batch_retraction_allowed": False,
        "fuzzy_match_allowed": False,
        "retraction_preview_deletes_memory": False,
    }
    return {
        "version": MEMORY_RETRACTION_TRIAL_VERSION,
        "state": "memory_retraction_transaction_preview_review_only",
        "approval_lock": lock,
        "transaction_preview": preview,
        "blockers": blockers,
        "status": "reviewable" if not blockers else "blocked",
        "ok": not blockers,
        "writes_memory": False,
        "deletes_memory": False,
        "safe_next_action": "Operator may review exact retraction transaction preview. Preview does not delete memory or grant future authority.",
    }


def execute_operator_confirmed_memory_retraction_trial(root: str | Path | None = None, target_path: str | Path | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = _default_evidence(evidence)
    preview_summary = build_memory_retraction_transaction_preview_summary(root, target_path, evidence)
    preview = dict(preview_summary.get("transaction_preview", {}))
    path = Path(str(preview.get("target_trial_memory_store_path")))
    blockers = list(preview_summary.get("blockers", []))
    if evidence.get("operator_retraction_confirmation_phrase") != EXPECTED_MEMORY_RETRACTION_CONFIRMATION_PHRASE:
        blockers.append("operator-retraction-confirmation-not-exact")
    if evidence.get("retraction_approval_reused") is True or evidence.get("retraction_approval_burned_out") is True:
        blockers.append("retraction-approval-burnout-blocked-reuse")
    if evidence.get("batch_retraction") is True:
        blockers.append("batch-retraction-blocked")
    if evidence.get("fuzzy_match") is True:
        blockers.append("fuzzy-retraction-blocked")
    if not _is_governed_live_trial_path(path, root):
        blockers.append("non-governed-retraction-target-blocked")
    burnout = {
        "approval_lock_id": preview.get("memory_retraction_approval_lock_id"),
        "burned_out": True,
        "reuse_allowed": False,
        "burnout_reason": "blocked-before-retraction" if blockers else "single-use-memory-retraction-consumed",
    }
    if blockers:
        return {**preview_summary, "state": "operator_confirmed_memory_retraction_trial_blocked", "blockers": blockers, "executed": False, "approval_burnout": burnout, "status": "blocked", "ok": False, "writes_memory": False, "deletes_memory": False}
    pre_hash = _file_hash(path)
    payload = {"version": MEMORY_RETRACTION_TRIAL_VERSION, "entries": _read_entries(path)}
    entries = payload["entries"]
    target_id = preview.get("target_entry_id")
    matched = False
    for row in entries:
        if row.get("live_memory_entry_id") == target_id and row.get("status") != "retracted":
            row["status"] = "retracted"
            row["retraction_id"] = "memory-retraction-" + _stable_hash({"target": target_id, "pre": pre_hash})
            row["retracted_timestamp_policy"] = "deterministic-memory-retraction-trial-placeholder"
            row["retraction_approval_burned_out"] = True
            row["physical_delete"] = False
            row["future_retraction_authorization_granted"] = False
            matched = True
            break
    if not matched:
        return {**preview_summary, "state": "operator_confirmed_memory_retraction_trial_blocked", "blockers": ["exact-active-entry-not-found"], "executed": False, "approval_burnout": burnout, "status": "blocked", "ok": False, "writes_memory": False, "deletes_memory": False}
    path.write_text(json.dumps({"version": MEMORY_RETRACTION_TRIAL_VERSION, "entries": entries}, indent=2), encoding="utf-8")
    post_hash = _file_hash(path)
    return {
        "version": MEMORY_RETRACTION_TRIAL_VERSION,
        "state": "operator_confirmed_memory_retraction_trial_marked_retracted",
        "transaction_preview": {**preview, "pre_retraction_store_hash": pre_hash, "post_retraction_store_hash": post_hash},
        "target_entry_id": target_id,
        "executed": True,
        "approval_burnout": {**burnout, "burnout_reason": "single-use-memory-retraction-consumed"},
        "pre_retraction_hash": pre_hash,
        "post_retraction_hash": post_hash,
        "status": "pass",
        "ok": True,
        "writes_memory": True,
        "deletes_memory": False,
        "physical_delete": False,
        "retained_audit_record": True,
        "grants_future_authorization": False,
        "safe_next_action": "Operator may inspect the retained retraction audit record. This success authorizes no future memory retractions.",
    }


def build_memory_retraction_trial_audit_summary(docs: str = "", root: str | Path | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = _default_evidence(evidence or {"operator_retraction_confirmation_phrase": EXPECTED_MEMORY_RETRACTION_CONFIRMATION_PHRASE})
    import tempfile
    with tempfile.TemporaryDirectory(prefix="eidolon_v425_audit_") as tmp:
        trial_root = Path(root) if root is not None else Path(tmp)
        eligibility = build_memory_retraction_eligibility_summary(trial_root, evidence)
        approval_lock = build_memory_retraction_approval_lock_summary(trial_root, evidence)
        preview = build_memory_retraction_transaction_preview_summary(trial_root, evidence=evidence)
        trial = execute_operator_confirmed_memory_retraction_trial(trial_root, evidence=evidence)
        reuse_block = execute_operator_confirmed_memory_retraction_trial(trial_root, evidence={**evidence, "retraction_approval_reused": True})
        wrong_phrase = execute_operator_confirmed_memory_retraction_trial(trial_root, evidence={**evidence, "operator_retraction_confirmation_phrase": "wrong"})
        batch_block = execute_operator_confirmed_memory_retraction_trial(trial_root, evidence={**evidence, "batch_retraction": True})
        fuzzy_block = execute_operator_confirmed_memory_retraction_trial(trial_root, evidence={**evidence, "fuzzy_match": True})
        bad_target = build_memory_retraction_transaction_preview_summary(trial_root, trial_root / "memory.json", evidence)
    required_tokens = [
        "memory-retraction-eligibility",
        "memory-retraction-approval-lock",
        "memory-retraction-transaction-preview",
        "operator-confirmed-memory-retraction-trial",
        "memory-retraction-trial-audit",
        "operator-governed-memory-retraction-trial-v1",
        "memory_retraction_trial.py",
        "write_approval_authorizes_retraction=False",
        "retraction_eligibility_is_approval=False",
        "retained_audit_record_required=True",
    ]
    blockers: list[str] = []
    if eligibility.get("ok") is not True:
        blockers.append("eligibility-blocked")
    if approval_lock.get("ok") is not True:
        blockers.append("approval-lock-blocked")
    if preview.get("ok") is not True or preview.get("deletes_memory") is not False:
        blockers.append("preview-invalid")
    if trial.get("ok") is not True or trial.get("executed") is not True or trial.get("retained_audit_record") is not True:
        blockers.append("single-retraction-not-proven")
    if trial.get("approval_burnout", {}).get("burned_out") is not True:
        blockers.append("retraction-burnout-missing")
    if reuse_block.get("ok") is not False:
        blockers.append("retraction-reuse-not-blocked")
    if wrong_phrase.get("ok") is not False:
        blockers.append("wrong-retraction-phrase-not-blocked")
    if batch_block.get("ok") is not False:
        blockers.append("batch-retraction-not-blocked")
    if fuzzy_block.get("ok") is not False:
        blockers.append("fuzzy-retraction-not-blocked")
    if bad_target.get("ok") is not False:
        blockers.append("bad-target-not-blocked")
    if docs and not all(token in docs for token in required_tokens):
        blockers.append("docs-or-source-token-missing")
    for key, value in MEMORY_RETRACTION_BOUNDARIES.items():
        if key.endswith("required") or key == "operator_review_required":
            if value is not True:
                blockers.append(f"boundary:{key}")
        elif value is not False:
            blockers.append(f"boundary:{key}")
    return {
        "version": MEMORY_RETRACTION_TRIAL_VERSION,
        "state": "memory_retraction_trial_audit",
        "eligibility": eligibility,
        "approval_lock": approval_lock,
        "transaction_preview": preview,
        "trial": trial,
        "reuse_block": reuse_block,
        "wrong_phrase_block": wrong_phrase,
        "batch_block": batch_block,
        "fuzzy_block": fuzzy_block,
        "bad_target_block": bad_target,
        "boundaries": dict(MEMORY_RETRACTION_BOUNDARIES),
        "required_tokens": required_tokens,
        "blockers": blockers,
        "status": "pass" if not blockers else "blocked",
        "ok": not blockers,
        "writes_memory": trial.get("writes_memory") is True,
        "deletes_memory": False,
        "physical_delete": False,
        "grants_future_authorization": False,
        "applies_patches": False,
        "expands_autonomy": False,
        "safe_next_action": "Proceed only to memory lifecycle review design; this audit grants no future memory retraction approval.",
    }


def render_memory_retraction_lines(summary: dict[str, Any]) -> list[str]:
    lines = [
        f"- version: {summary.get('version')}",
        f"- state: {summary.get('state')}",
        f"- status: {summary.get('status')}",
        f"- ok: {summary.get('ok')}",
        f"- writes_memory: {summary.get('writes_memory', False)}",
        f"- deletes_memory: {summary.get('deletes_memory', False)}",
        f"- grants_future_authorization: {summary.get('grants_future_authorization', False)}",
    ]
    if isinstance(summary.get("blockers"), list):
        lines.append("- blockers: " + (", ".join(summary.get("blockers", [])) or "none"))
    lock = summary.get("approval_lock")
    if isinstance(lock, dict):
        lock_payload = lock.get("approval_lock", lock)
        if isinstance(lock_payload, dict):
            lines.append(f"- retraction_lock_id: {lock_payload.get('memory_retraction_approval_lock_id')}")
            lines.append(f"- single_use: {lock_payload.get('single_use')}")
    burnout = summary.get("approval_burnout") or summary.get("trial", {}).get("approval_burnout") if isinstance(summary.get("trial"), dict) else None
    if isinstance(burnout, dict):
        lines.append(f"- approval_burned_out: {burnout.get('burned_out')}")
        lines.append(f"- reuse_allowed: {burnout.get('reuse_allowed')}")
    return lines


# v420.1-v425.0 memory retraction smoke tokens: memory-retraction-eligibility memory-retraction-approval-lock memory-retraction-transaction-preview operator-confirmed-memory-retraction-trial memory-retraction-trial-audit operator-governed-memory-retraction-trial-v1 memory_retraction_trial.py write_approval_authorizes_retraction=False retraction_eligibility_is_approval=False retraction_preview_deletes_memory=False retraction_runs_without_confirmation=False retraction_allows_batch=False retraction_uses_fuzzy_match=False retraction_deletes_canonical_memory_json=False fresh_retraction_approval_required=True single_use_retraction_approval_required=True exact_retraction_confirmation_required=True prior_write_burnout_required=True retained_audit_record_required=True audit_grants_future_retraction_authority=False
