from __future__ import annotations

import hashlib
import json
from typing import Any

from memory_candidate_application_trial import (
    EXPECTED_MEMORY_CONFIRMATION_PHRASE,
    SAFE_FIRST_MEMORY_CANDIDATE,
    build_memory_application_approval_lock_summary,
    build_memory_candidate_selection_packet_summary,
    build_memory_write_transaction_preview_summary,
    build_operator_confirmed_memory_application_trial_summary,
)

MEMORY_APPLICATION_DRY_RUN_LEDGER_VERSION = "1032.0"
MEMORY_APPLICATION_DRY_RUN_BOUNDARIES: dict[str, bool] = {
    "ledger_writes_live_memory": False,
    "ledger_mutates_identity": False,
    "ledger_alters_personality": False,
    "ledger_rewrites_purpose": False,
    "ledger_expands_autonomy": False,
    "ledger_invokes_models": False,
    "ledger_applies_patches": False,
    "ledger_publishes_release": False,
    "ledger_treats_reviewable_as_authorization": False,
    "ledger_reuses_approval": False,
    "ledger_executes_retraction": False,
    "replay_accepts_drift": False,
    "audit_writes_memory": False,
    "operator_review_required": True,
    "single_use_approval_required": True,
    "exact_confirmation_required": True,
    "candidate_hash_required": True,
    "transaction_hash_required": True,
    "retraction_preview_required": True,
    "post_application_audit_required": True,
}

DRY_RUN_LEDGER_FIELDS = [
    "ledger_entry_id",
    "candidate_id",
    "approval_id",
    "candidate_hash",
    "transaction_preview_hash",
    "memory_text_hash",
    "confirmation_supplied",
    "confirmation_exact",
    "status",
    "blockers",
    "operator_decision_placeholder",
]

SAFE_LEDGER_MEMORY_TEXT = SAFE_FIRST_MEMORY_CANDIDATE


def _stable_hash(value: Any) -> str:
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _candidate_id(candidate: dict[str, Any]) -> str:
    return str(candidate.get("candidate_id") or "memory-candidate-v410-001")


def _approval_id(approval: dict[str, Any]) -> str:
    return str(approval.get("approval_id") or "memory-approval-v410-001")


def build_memory_application_dry_run_attempt_summary(request_text: str | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = dict(evidence or {})
    candidate_packet = build_memory_candidate_selection_packet_summary(request_text, evidence)
    approval_lock = build_memory_application_approval_lock_summary(request_text, evidence)
    transaction_preview = build_memory_write_transaction_preview_summary(request_text, evidence)
    harness = build_operator_confirmed_memory_application_trial_summary(request_text, evidence)

    candidate = dict(candidate_packet.get("selected_candidate", {}))
    approval = dict(approval_lock.get("approval", {}))
    memory_text = str(transaction_preview.get("memory_text") or candidate.get("lesson_text") or SAFE_LEDGER_MEMORY_TEXT)
    confirmation_phrase = evidence.get("operator_confirmation_phrase")
    confirmation_supplied = confirmation_phrase is not None and str(confirmation_phrase).strip() != ""
    confirmation_exact = str(confirmation_phrase or "") == EXPECTED_MEMORY_CONFIRMATION_PHRASE

    blockers: list[str] = []
    for label, packet in [
        ("candidate", candidate_packet),
        ("approval", approval_lock),
        ("transaction", transaction_preview),
        ("harness", harness),
    ]:
        if packet.get("status") == "blocked" or packet.get("ok") is False:
            blockers.append(f"{label}-blocked")
    if not confirmation_supplied:
        blockers.append("operator-confirmation-missing")
    if confirmation_supplied and not confirmation_exact:
        blockers.append("operator-confirmation-not-exact")
    if evidence.get("approval_reused") is True:
        blockers.append("approval-reuse-requested")
    if evidence.get("write_live_memory") is True:
        blockers.append("live-memory-write-requested")
    if evidence.get("identity_or_personality_mutation") is True:
        blockers.append("identity-personality-mutation-requested")
    if evidence.get("autonomy_expansion") is True:
        blockers.append("autonomy-expansion-requested")

    entry = {
        "ledger_entry_id": "dry-run-" + _stable_hash({"candidate": candidate, "approval": approval, "memory_text": memory_text}),
        "candidate_id": _candidate_id(candidate),
        "approval_id": _approval_id(approval),
        "candidate_hash": _stable_hash(candidate),
        "transaction_preview_hash": _stable_hash(transaction_preview),
        "memory_text_hash": _stable_hash(memory_text),
        "memory_text_preview": memory_text,
        "confirmation_supplied": confirmation_supplied,
        "confirmation_exact": confirmation_exact,
        "status": "blocked" if blockers else "dry_run_recordable",
        "blockers": blockers,
        "operator_decision_placeholder": "pending_operator_review",
        "created_timestamp_policy": "deterministic-review-placeholder",
        "writes_live_memory": False,
        "reviewable_is_authorization": False,
    }
    return {
        "version": MEMORY_APPLICATION_DRY_RUN_LEDGER_VERSION,
        "state": "memory_application_dry_run_attempt_ledger_review_only",
        "entry": entry,
        "candidate_packet": candidate_packet,
        "approval_lock": approval_lock,
        "transaction_preview": transaction_preview,
        "application_trial": harness,
        "required_fields": DRY_RUN_LEDGER_FIELDS,
        "missing_fields": [field for field in DRY_RUN_LEDGER_FIELDS if entry.get(field) in (None, "", [])],
        "boundaries": dict(MEMORY_APPLICATION_DRY_RUN_BOUNDARIES),
        "status": "blocked" if blockers else "reviewable",
        "ok": not blockers,
        "writes_memory": False,
        "safe_next_action": "Operator may review the dry-run ledger entry. This does not authorize or perform a live memory write.",
    }


def build_memory_application_dry_run_ledger_entry_summary(request_text: str | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    attempt = build_memory_application_dry_run_attempt_summary(request_text, evidence)
    entry = dict(attempt.get("entry", {}))
    return {
        "version": MEMORY_APPLICATION_DRY_RUN_LEDGER_VERSION,
        "state": "memory_application_dry_run_ledger_entry_review_only",
        "ledger_entry": entry,
        "entry_schema": DRY_RUN_LEDGER_FIELDS,
        "entry_is_recordable": bool(attempt.get("ok")),
        "operator_review_required": True,
        "writes_memory": False,
        "status": attempt.get("status"),
        "ok": bool(attempt.get("ok")),
        "blockers": list(entry.get("blockers", [])),
        "safe_next_action": "Store only as a review packet if the operator explicitly chooses; never treat it as memory authorization.",
    }


def build_memory_application_ledger_replay_summary(ledger_entry: dict[str, Any] | None = None, current_evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    if ledger_entry is None:
        ledger_entry = build_memory_application_dry_run_ledger_entry_summary(
            "review only",
            {"operator_confirmation_phrase": EXPECTED_MEMORY_CONFIRMATION_PHRASE},
        )["ledger_entry"]
    ledger_entry = dict(ledger_entry or {})
    current = build_memory_application_dry_run_attempt_summary("review only", current_evidence or {"operator_confirmation_phrase": EXPECTED_MEMORY_CONFIRMATION_PHRASE})["entry"]
    drift: list[str] = []
    for key in ["candidate_id", "approval_id", "candidate_hash", "transaction_preview_hash", "memory_text_hash", "confirmation_exact"]:
        if ledger_entry.get(key) != current.get(key):
            drift.append(key)
    if current.get("blockers"):
        drift.append("current-blockers-present")
    return {
        "version": MEMORY_APPLICATION_DRY_RUN_LEDGER_VERSION,
        "state": "memory_application_ledger_replay_review_only",
        "ledger_entry": ledger_entry,
        "current_entry_preview": current,
        "drift": drift,
        "replay_accepts_drift": False,
        "status": "blocked" if drift else "reviewable",
        "ok": not drift,
        "writes_memory": False,
        "safe_next_action": "If drift exists, discard or rebuild the dry-run packet under fresh operator review.",
    }


def build_memory_application_ledger_audit_summary(docs: str = "", replay: dict[str, Any] | None = None) -> dict[str, Any]:
    replay = dict(replay or build_memory_application_ledger_replay_summary())
    required_tokens = [
        "memory-application-dry-run-ledger",
        "memory-application-ledger-replay",
        "memory-application-ledger-audit",
        "operator-governed-memory-application-dry-run-ledger-v1",
        "memory_application_dry_run_ledger.py",
        "ledger_writes_live_memory=False",
        "replay_accepts_drift=False",
    ]
    blockers: list[str] = []
    if docs and not all(token in docs for token in required_tokens):
        blockers.append("docs-or-source-token-missing")
    if replay.get("replay_accepts_drift") is not False:
        blockers.append("replay-drift-boundary-missing")
    for key, value in MEMORY_APPLICATION_DRY_RUN_BOUNDARIES.items():
        if key.endswith("required") or key == "operator_review_required":
            if value is not True:
                blockers.append(f"boundary:{key}")
        elif value is not False:
            blockers.append(f"boundary:{key}")
    return {
        "version": MEMORY_APPLICATION_DRY_RUN_LEDGER_VERSION,
        "state": "memory_application_dry_run_ledger_audit_review_only",
        "replay": replay,
        "boundaries": dict(MEMORY_APPLICATION_DRY_RUN_BOUNDARIES),
        "required_tokens": required_tokens,
        "blockers": blockers,
        "status": "pass" if not blockers else "blocked",
        "ok": not blockers,
        "writes_memory": False,
        "applies_patches": False,
        "expands_autonomy": False,
        "safe_next_action": "Proceed only to sandbox memory write design after operator review; no live memory write is authorized.",
    }


def render_memory_application_dry_run_ledger_lines(summary: dict[str, Any]) -> list[str]:
    lines = [
        f"- version: {summary.get('version')}",
        f"- state: {summary.get('state')}",
        f"- status: {summary.get('status')}",
        f"- writes_memory: {summary.get('writes_memory', False)}",
    ]
    entry = summary.get("entry") or summary.get("ledger_entry")
    if isinstance(entry, dict):
        lines.extend([
            f"- ledger_entry_id: {entry.get('ledger_entry_id')}",
            f"- candidate_id: {entry.get('candidate_id')}",
            f"- approval_id: {entry.get('approval_id')}",
            f"- confirmation_exact: {entry.get('confirmation_exact')}",
            f"- blockers: {', '.join(entry.get('blockers', [])) or 'none'}",
        ])
    drift = summary.get("drift")
    if isinstance(drift, list):
        lines.append(f"- drift: {', '.join(drift) or 'none'}")
    return lines
