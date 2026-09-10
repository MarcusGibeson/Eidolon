from __future__ import annotations

"""Bounded, content-free reliability projection for the complete action loop.

Callers supply already-bounded lifecycle and follow-up records. This module does
not discover ledgers, invoke tools, retry work, or grant approval, authorization,
or execution authority.
"""

import hashlib
import json
import re
from collections import Counter, defaultdict
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1179.8"
MAX_INPUT_RECORDS = 512
MAX_PUBLIC_RECORDS = 64
MAX_REPORT_BYTES = 12288
STALE_IN_PROGRESS_SECONDS = 5 * 60
KNOWN_STATES = frozenset({
    "proposed", "awaiting_approval", "approved", "rejected", "cancelled",
    "expired", "superseded", "execution_admitted", "execution_in_progress",
    "execution_succeeded", "execution_failed", "execution_cancelled",
    "execution_timed_out",
})
TERMINAL_STATES = frozenset({
    "rejected", "cancelled", "expired", "superseded", "execution_succeeded",
    "execution_failed", "execution_cancelled", "execution_timed_out",
})


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def _id(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if re.fullmatch(r"[a-z0-9_-]{1,80}", text) else ""


def _hex(value: Any) -> str:
    text = str(value or "").lower()
    return text if re.fullmatch(r"[0-9a-f]{64}", text) else ""


def _normalize(item: Mapping[str, Any]) -> dict[str, Any] | None:
    proposal_id = _id(item.get("proposal_id"))
    capability_id = _id(item.get("capability_id"))
    state = str(item.get("state") or item.get("lifecycle_state") or "")
    proposal_digest = _hex(item.get("proposal_digest"))
    if not (proposal_id and capability_id and state in KNOWN_STATES and proposal_digest):
        return None
    if item.get("content_free", True) is not True:
        return None
    row = {
        "proposal_id": proposal_id,
        "capability_id": capability_id,
        "state": state,
        "proposal_digest": proposal_digest,
        "approval_decision_digest": _hex(item.get("approval_decision_digest")),
        "authorization_digest": _hex(item.get("authorization_digest")),
        "execution_admission_digest": _hex(item.get("execution_admission_digest")),
        "execution_attempt_digest": _hex(item.get("execution_attempt_digest")),
        "terminal_result_digest": _hex(item.get("terminal_result_digest") or item.get("execution_result_digest")),
        "updated_at": max(0.0, float(item.get("updated_at") or item.get("recorded_at") or 0.0)),
    }
    required = []
    if state in {"approved", "execution_admitted", "execution_in_progress", "execution_succeeded", "execution_failed", "execution_cancelled", "execution_timed_out"}:
        required.append("approval_decision_digest")
    if state in {"execution_admitted", "execution_in_progress", "execution_succeeded", "execution_failed", "execution_cancelled", "execution_timed_out"}:
        required += ["authorization_digest", "execution_admission_digest"]
    if state == "execution_in_progress":
        required.append("execution_attempt_digest")
    if state in {"execution_succeeded", "execution_failed", "execution_cancelled", "execution_timed_out"}:
        required.append("terminal_result_digest")
    row["coherent"] = all(row[name] for name in required)
    return row


def build_action_loop_reliability(
    records: Iterable[Mapping[str, Any]] = (),
    *,
    follow_up_records: Iterable[Mapping[str, Any]] = (),
    now: float = 0.0,
) -> dict[str, Any]:
    """Return a bounded reliability report without discovering state or taking action."""
    material = list(records)[:MAX_INPUT_RECORDS]
    malformed = 0
    normalized: list[dict[str, Any]] = []
    for item in material:
        row = _normalize(item) if isinstance(item, Mapping) else None
        if row is None:
            malformed += 1
        else:
            normalized.append(row)

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in normalized:
        grouped[row["proposal_id"]].append(row)

    replay_duplicates = 0
    contradictory = 0
    incoherent = 0
    stale_in_progress = 0
    terminal_counts: Counter[str] = Counter()
    public: list[dict[str, Any]] = []
    for proposal_id, rows in grouped.items():
        rows.sort(key=lambda r: (r["updated_at"], r["state"]))
        fingerprints = Counter(_digest({k: r[k] for k in r if k != "updated_at"}) for r in rows)
        replay_duplicates += sum(count - 1 for count in fingerprints.values() if count > 1)
        terminal_states = {r["state"] for r in rows if r["state"] in TERMINAL_STATES}
        terminal_digests = {r["terminal_result_digest"] for r in rows if r["terminal_result_digest"]}
        if len(terminal_states) > 1 or len(terminal_digests) > 1:
            contradictory += 1
        newest = rows[-1]
        if not newest["coherent"]:
            incoherent += 1
        if newest["state"] == "execution_in_progress" and float(now) - newest["updated_at"] > STALE_IN_PROGRESS_SECONDS:
            stale_in_progress += 1
        if newest["state"] in TERMINAL_STATES:
            terminal_counts[newest["state"]] += 1
        public.append({
            "proposal_id": proposal_id,
            "capability_id": newest["capability_id"],
            "state": newest["state"],
            "coherent": newest["coherent"],
            "stale_in_progress": newest["state"] == "execution_in_progress" and float(now) - newest["updated_at"] > STALE_IN_PROGRESS_SECONDS,
            "terminal": newest["state"] in TERMINAL_STATES,
        })

    followups = list(follow_up_records)[:MAX_INPUT_RECORDS]
    pending_followups = 0
    stale_followups = 0
    malformed_followups = 0
    for item in followups:
        if not isinstance(item, Mapping) or not _id(item.get("proposal_id")) or not _hex(item.get("review_digest")):
            malformed_followups += 1
            continue
        if item.get("state") == "pending":
            pending_followups += 1
            if float(now) > float(item.get("expires_at") or 0.0):
                stale_followups += 1

    public = sorted(public, key=lambda r: r["proposal_id"])[-MAX_PUBLIC_RECORDS:]
    input_truncated = len(list(records)) > MAX_INPUT_RECORDS if isinstance(records, (list, tuple)) else False
    posture = "reliable"
    if contradictory or incoherent:
        posture = "blocked"
    elif stale_in_progress or stale_followups or malformed or malformed_followups or replay_duplicates:
        posture = "review_required"

    result = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "reliability_posture": posture,
        "input_record_count": len(material),
        "accepted_record_count": len(normalized),
        "proposal_count": len(grouped),
        "public_record_count": len(public),
        "input_truncated": input_truncated,
        "malformed_record_count": malformed,
        "malformed_follow_up_count": malformed_followups,
        "replay_duplicate_count": replay_duplicates,
        "contradictory_proposal_count": contradictory,
        "incoherent_proposal_count": incoherent,
        "stale_in_progress_count": stale_in_progress,
        "pending_follow_up_count": pending_followups,
        "stale_follow_up_count": stale_followups,
        "terminal_state_counts": dict(sorted(terminal_counts.items())),
        "records": public,
        "automatic_retry": False,
        "automatic_approval": False,
        "automatic_authorization": False,
        "execution_invoked": False,
        "ledger_discovered": False,
        "raw_content_exposed": False,
        "authority_granted": False,
        "content_free": True,
    }
    result["reliability_digest"] = _digest(result)
    if len(json.dumps(result, sort_keys=True, separators=(",", ":")).encode()) > MAX_REPORT_BYTES:
        raise ValueError("Action-loop reliability report exceeded bounded size")
    return result
