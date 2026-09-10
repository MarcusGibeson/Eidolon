from __future__ import annotations

"""Operator-facing, content-free review overlay for initiative evidence.

The v1501.4-v1508 evidence-review layer deliberately does *not* persist a copy
of development evidence.  Evidence remains owned by its existing production
source (discovery, diagnostics, evaluation findings, tests, and so on).  This
module stores only digest-bound operator review annotations in external runtime
state and reapplies them to a freshly built evidence intake projection.

Review actions never create proposals, prepare workspaces, contact providers,
modify source, install candidates, promote releases, or expand authority.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping

from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import MetadataMutationBusy, metadata_mutation_lock


CONTRACT_VERSION = "v1508.9"
SCHEMA_VERSION = "1"
MAX_ANNOTATIONS = 256
REVIEW_STATES = frozenset({"unreviewed", "confirmed", "deferred", "cancelled", "corrected"})
MUTATING_ACTIONS = frozenset({"confirm", "defer", "cancel", "correct"})
CORRECTABLE_FIELDS = frozenset({"severity", "confidence", "acceptance_criteria"})
SEVERITIES = frozenset({"none", "minor", "low", "medium", "major", "high", "blocking", "critical"})

_SHOW = re.compile(r"^(?:show|inspect) initiative evidence[.!?]*$", re.IGNORECASE)
_CONTROL = re.compile(
    r"^(?P<action>confirm|defer|cancel) initiative evidence "
    r"(?P<evidence_id>initev_[a-f0-9]{24}) digest (?P<digest>[a-f0-9]{16})[.!?]*$",
    re.IGNORECASE,
)
_CORRECT_SEVERITY = re.compile(
    r"^correct initiative evidence (?P<evidence_id>initev_[a-f0-9]{24}) "
    r"digest (?P<digest>[a-f0-9]{16}) severity "
    r"(?P<severity>none|minor|low|medium|major|high|blocking|critical)[.!?]*$",
    re.IGNORECASE,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


def _runtime_root(runtime_root: str | Path | None = None) -> Path:
    if runtime_root is not None:
        return Path(runtime_root).expanduser().resolve()
    return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data").expanduser().resolve()


def _path(runtime_root: str | Path | None = None) -> Path:
    return _runtime_root(runtime_root) / "development_campaigns" / "initiative_evidence_review.json"


def _default() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "revision": 0,
        "updated_at": "",
        "annotations": [],
        "authority_boundary": {
            "proposal_creation_authorized": False,
            "workspace_preparation_authorized": False,
            "provider_contact_authorized": False,
            "source_mutation_authorized": False,
            "project_mutation_authorized": False,
            "approval_granted": False,
            "installation_authorized": False,
            "promotion_authorized": False,
            "independent_authority_granted": False,
        },
    }


def _load(runtime_root: str | Path | None = None) -> dict[str, Any]:
    state = load_json_file(_path(runtime_root), _default(), expected_type=dict)
    if str(state.get("schema_version") or "") != SCHEMA_VERSION:
        return _default()
    for key, value in _default().items():
        state.setdefault(key, deepcopy(value))
    state["annotations"] = [
        dict(row) for row in state.get("annotations") or () if isinstance(row, Mapping)
    ]
    return state


def _normalize_correction(correction: Mapping[str, Any] | None) -> tuple[dict[str, Any], str]:
    supplied = dict(correction or {})
    if not supplied:
        return {}, "evidence_correction_missing"
    if set(supplied) - CORRECTABLE_FIELDS:
        return {}, "evidence_correction_scope_blocked"
    result: dict[str, Any] = {}
    if "severity" in supplied:
        severity = str(supplied.get("severity") or "").strip().lower()
        if severity not in SEVERITIES:
            return {}, "evidence_correction_invalid_severity"
        result["severity"] = severity
    if "confidence" in supplied:
        try:
            confidence = float(supplied.get("confidence"))
        except (TypeError, ValueError):
            return {}, "evidence_correction_invalid_confidence"
        if not 0.0 <= confidence <= 1.0:
            return {}, "evidence_correction_invalid_confidence"
        result["confidence"] = round(confidence, 4)
    if "acceptance_criteria" in supplied:
        criteria = supplied.get("acceptance_criteria")
        if not isinstance(criteria, (list, tuple)):
            return {}, "evidence_correction_invalid_acceptance"
        normalized = [str(value).strip() for value in criteria if str(value).strip()]
        if not normalized or len(normalized) > 8 or any(len(value) > 80 for value in normalized):
            return {}, "evidence_correction_invalid_acceptance"
        result["acceptance_criteria"] = list(dict.fromkeys(normalized))
    return result, ""


def _annotation_key(row: Mapping[str, Any]) -> tuple[str, str]:
    return str(row.get("evidence_id") or ""), str(row.get("source_evidence_digest") or "")


def _latest_annotations(state: Mapping[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for row in state.get("annotations") or ():
        if not isinstance(row, Mapping):
            continue
        key = _annotation_key(row)
        if all(key):
            latest[key] = dict(row)
    return latest


def build_initiative_evidence_review(
    intake: Mapping[str, Any] | None,
    *,
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    """Overlay current evidence with content-free operator review annotations."""

    intake_row = dict(intake or {})
    state = _load(runtime_root)
    latest = _latest_annotations(state)
    current_keys: set[tuple[str, str]] = set()
    records: list[dict[str, Any]] = []
    for raw in intake_row.get("records") or ():
        if not isinstance(raw, Mapping):
            continue
        source = dict(raw)
        evidence_id = str(source.get("evidence_id") or "")
        evidence_digest = str(source.get("evidence_digest") or "")
        if not evidence_id or len(evidence_digest) != 64:
            continue
        key = (evidence_id, evidence_digest)
        current_keys.add(key)
        annotation = dict(latest.get(key) or {})
        overrides = dict(annotation.get("overrides") or {})
        state_name = str(annotation.get("review_state") or "unreviewed")
        if state_name not in REVIEW_STATES:
            state_name = "unreviewed"
        effective = {
            "severity": str(overrides.get("severity") or source.get("severity") or "medium"),
            "confidence": float(overrides.get("confidence", source.get("confidence") or 0.0)),
            "acceptance_criteria": list(overrides.get("acceptance_criteria") or source.get("acceptance_criteria") or ()),
        }
        review_identity = {
            "evidence_id": evidence_id,
            "source_evidence_digest": evidence_digest,
            "annotation_revision": int(annotation.get("revision") or 0),
            "review_state": state_name,
            "overrides": overrides,
        }
        records.append({
            **source,
            "review_state": state_name,
            "operator_overrides": overrides,
            "effective_severity": effective["severity"],
            "effective_confidence": round(max(0.0, min(1.0, effective["confidence"])), 4),
            "effective_acceptance_criteria": effective["acceptance_criteria"],
            "eligible_for_selection": state_name not in {"deferred", "cancelled"},
            "operator_reviewed": state_name != "unreviewed",
            "review_digest": _digest(review_identity),
            "content_free": True,
        })
    stale = [row for key, row in latest.items() if key not in current_keys]
    records.sort(key=lambda row: (-float(row.get("impact_score") or 0.0), str(row.get("evidence_id") or "")))
    result = {
        "ok": True,
        "status": "initiative_evidence_review_ready",
        "contract_version": CONTRACT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "intake_digest": str(intake_row.get("intake_digest") or ""),
        "record_count": len(records),
        "records": records,
        "reviewed_count": sum(bool(row.get("operator_reviewed")) for row in records),
        "deferred_count": sum(row.get("review_state") == "deferred" for row in records),
        "cancelled_count": sum(row.get("review_state") == "cancelled" for row in records),
        "stale_annotation_count": len(stale),
        "revision": int(state.get("revision") or 0),
        "authority_boundary": deepcopy(state.get("authority_boundary") or _default()["authority_boundary"]),
        "runtime_mutated": False,
        "provider_contacted": False,
        "source_modified": False,
        "authority_granted": False,
        "content_free": True,
    }
    result["review_snapshot_digest"] = _digest({
        "intake_digest": result["intake_digest"],
        "records": [(row["evidence_id"], row["review_digest"]) for row in records],
        "revision": result["revision"],
    })
    return result


def _receipt(
    *,
    action: str,
    evidence_id: str,
    source_evidence_digest: str,
    operation_id: str,
    before_state: str,
    after_state: str,
    revision: int,
) -> dict[str, Any]:
    row = {
        "receipt_type": "initiative_evidence_review",
        "contract_version": CONTRACT_VERSION,
        "action": action,
        "evidence_id": evidence_id,
        "source_evidence_digest": source_evidence_digest,
        "operation_id": operation_id,
        "before_state": before_state,
        "after_state": after_state,
        "revision": revision,
        "content_free": True,
    }
    row["receipt_digest"] = _digest(row)
    return row


def control_initiative_evidence_review(
    action: str,
    evidence_id: str,
    supplied_digest: str,
    intake: Mapping[str, Any] | None,
    *,
    correction: Mapping[str, Any] | None = None,
    runtime_root: str | Path | None = None,
    lock_timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    """Apply one exact digest-bound review annotation with exactly-once replay."""

    action = str(action or "").strip().lower()
    if action not in MUTATING_ACTIONS:
        return {
            "active": True,
            "ok": False,
            "status": "unsupported_evidence_review_control",
            "conversation_response": "That evidence review control is unsupported. Nothing changed.",
            "runtime_mutated": False,
        }
    correction_row: dict[str, Any] = {}
    if action == "correct":
        correction_row, error = _normalize_correction(correction)
        if error:
            return {
                "active": True,
                "ok": False,
                "status": error,
                "conversation_response": "That correction is outside the bounded public evidence fields. Nothing changed.",
                "runtime_mutated": False,
            }
    elif correction:
        return {
            "active": True,
            "ok": False,
            "status": "evidence_review_unexpected_correction",
            "conversation_response": "That review action cannot carry a correction payload. Nothing changed.",
            "runtime_mutated": False,
        }

    review = build_initiative_evidence_review(intake, runtime_root=runtime_root)
    current = next((row for row in review["records"] if row.get("evidence_id") == str(evidence_id or "")), None)
    if not current:
        return {
            "active": True,
            "ok": False,
            "status": "initiative_evidence_not_found",
            "conversation_response": "That current initiative evidence record was not found. Nothing changed.",
            "runtime_mutated": False,
        }
    if str(current.get("review_digest") or "")[:16].lower() != str(supplied_digest or "").lower():
        return {
            "active": True,
            "ok": False,
            "status": "initiative_evidence_review_digest_mismatch",
            "conversation_response": "That evidence review digest is stale or mismatched. Nothing changed.",
            "runtime_mutated": False,
        }
    if current.get("review_state") == "cancelled" and action != "cancel":
        return {
            "active": True,
            "ok": False,
            "status": "initiative_evidence_review_cancelled",
            "conversation_response": "That exact evidence revision was cancelled. A new source evidence digest is required before another review action.",
            "runtime_mutated": False,
        }

    target_state = {
        "confirm": "confirmed",
        "defer": "deferred",
        "cancel": "cancelled",
        "correct": "corrected",
    }[action]
    source_digest = str(current.get("evidence_digest") or "")
    operation_identity = {
        "action": action,
        "evidence_id": evidence_id,
        "source_evidence_digest": source_digest,
        "target_state": target_state,
        "correction": correction_row,
    }
    operation_id = f"evrev_{_digest(operation_identity)[:24]}"
    path = _path(runtime_root)
    try:
        with metadata_mutation_lock(path, timeout_seconds=lock_timeout_seconds):
            state = _load(runtime_root)
            prior = next(
                (dict(row) for row in reversed(state.get("annotations") or ()) if row.get("operation_id") == operation_id),
                None,
            )
            if prior:
                receipt = dict(prior.get("receipt") or {})
                return {
                    "active": True,
                    "ok": True,
                    "status": "initiative_evidence_review_replayed",
                    "idempotent": True,
                    "annotation": prior,
                    "receipt": receipt,
                    "conversation_response": "That exact evidence review action was already recorded; I reused its content-free receipt.",
                    "runtime_mutated": False,
                    "provider_contacted": False,
                    "source_modified": False,
                    "authority_granted": False,
                }

            latest = _latest_annotations(state)
            key = (str(evidence_id), source_digest)
            previous = dict(latest.get(key) or {})
            before_state = str(previous.get("review_state") or "unreviewed")
            if before_state == "cancelled" and target_state != "cancelled":
                return {
                    "active": True,
                    "ok": False,
                    "status": "initiative_evidence_review_cancelled",
                    "conversation_response": "That exact evidence revision was cancelled. Nothing changed.",
                    "runtime_mutated": False,
                }
            overrides = dict(previous.get("overrides") or {})
            if action == "correct":
                overrides.update(correction_row)
            now = _now()
            revision = int(state.get("revision") or 0) + 1
            receipt = _receipt(
                action=action,
                evidence_id=str(evidence_id),
                source_evidence_digest=source_digest,
                operation_id=operation_id,
                before_state=before_state,
                after_state=target_state,
                revision=revision,
            )
            annotation = {
                "evidence_id": str(evidence_id),
                "source_evidence_digest": source_digest,
                "review_state": target_state,
                "overrides": overrides,
                "operation_id": operation_id,
                "revision": revision,
                "updated_at": now,
                "receipt": receipt,
                "content_free": True,
            }
            state["annotations"] = (list(state.get("annotations") or ()) + [annotation])[-MAX_ANNOTATIONS:]
            state["revision"] = revision
            state["updated_at"] = now
            write_json_atomic(path, state, expected_type=dict, sort_keys=True)
    except MetadataMutationBusy:
        return {
            "active": True,
            "ok": False,
            "status": "initiative_evidence_review_busy",
            "safe_retry": True,
            "uncertain_result": False,
            "conversation_response": "Evidence review state is busy in another process. Retry the exact digest-bound action after it finishes.",
            "runtime_mutated": False,
        }

    verb = {"confirm": "confirmed", "defer": "deferred", "cancel": "cancelled", "correct": "corrected"}[action]
    return {
        "active": True,
        "ok": True,
        "status": f"initiative_evidence_{verb}",
        "idempotent": False,
        "annotation": annotation,
        "receipt": receipt,
        "conversation_response": (
            f"I {verb} evidence {evidence_id}. The content-free review receipt is {receipt['receipt_digest'][:16]}. "
            "This did not create a proposal, prepare a workspace, contact a provider, modify source, install, or promote anything."
        ),
        "runtime_mutated": True,
        "provider_contacted": False,
        "source_modified": False,
        "authority_granted": False,
    }


def initiative_evidence_review_response(review: Mapping[str, Any]) -> str:
    rows = [dict(row) for row in review.get("records") or ()]
    if not rows:
        return "There is no current initiative evidence to review. No development state changed."
    lines = [f"Current initiative evidence: {len(rows)} attributable content-free record(s)."]
    for row in rows[:8]:
        state = str(row.get("review_state") or "unreviewed")
        lines.append(
            f"- {row.get('evidence_id')} [{row.get('evidence_class')}; {row.get('effective_severity')}; "
            f"impact {float(row.get('impact_score') or 0.0):.2f}; {state}] digest {str(row.get('review_digest') or '')[:16]}"
        )
    if len(rows) > 8:
        lines.append(f"- {len(rows) - 8} additional record(s) are omitted from this concise view.")
    lines.append(
        "Controls are exact and digest-bound: confirm, defer, cancel, or correct severity. "
        "These controls annotate evidence only; they grant no development or installation authority."
    )
    return "\n".join(lines)



def is_initiative_evidence_review_control(user_text: str) -> bool:
    """Return True only for an exact bounded evidence-review command."""

    text = str(user_text or "").strip()
    return bool(_SHOW.fullmatch(text) or _CONTROL.fullmatch(text) or _CORRECT_SEVERITY.fullmatch(text))

def process_initiative_evidence_review_control(
    user_text: str,
    intake: Mapping[str, Any] | None,
    *,
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    """Route exact evidence-review commands; mixed or compound language is inert."""

    text = str(user_text or "").strip()
    if _SHOW.fullmatch(text):
        review = build_initiative_evidence_review(intake, runtime_root=runtime_root)
        return {
            "active": True,
            "ok": True,
            "status": review["status"],
            "evidence_review": review,
            "conversation_response": initiative_evidence_review_response(review),
            "runtime_mutated": False,
            "provider_contacted": False,
            "source_modified": False,
            "authority_granted": False,
        }
    match = _CONTROL.fullmatch(text)
    if match:
        return control_initiative_evidence_review(
            match.group("action").lower(),
            match.group("evidence_id").lower(),
            match.group("digest").lower(),
            intake,
            runtime_root=runtime_root,
        )
    match = _CORRECT_SEVERITY.fullmatch(text)
    if match:
        return control_initiative_evidence_review(
            "correct",
            match.group("evidence_id").lower(),
            match.group("digest").lower(),
            intake,
            correction={"severity": match.group("severity").lower()},
            runtime_root=runtime_root,
        )
    return {"active": False}


__all__ = [
    "CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "REVIEW_STATES",
    "CORRECTABLE_FIELDS",
    "build_initiative_evidence_review",
    "control_initiative_evidence_review",
    "initiative_evidence_review_response",
    "is_initiative_evidence_review_control",
    "process_initiative_evidence_review_control",
]
