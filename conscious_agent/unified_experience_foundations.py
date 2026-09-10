from __future__ import annotations

"""v1190.0-v1190.2 unified operator-experience foundations.

The contract projects one exact, content-free current-state surface for each
major Eidolon domain. It does not fetch private records, execute work, create
approval, consume approval, or mutate any source/runtime state.
"""

import hashlib
import json
import re
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "v1190.2"
SCHEMA_VERSION = "1"
MAX_CONTRACT_BYTES = 262_144
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")

DOMAINS: tuple[str, ...] = (
    "conversation",
    "cognition",
    "reasoning",
    "planning",
    "campaign",
    "approval",
    "action",
    "result",
    "learning",
)

DOMAIN_STATES: dict[str, frozenset[str]] = {
    "conversation": frozenset({"ready", "active", "waiting", "attention", "complete"}),
    "cognition": frozenset({"idle", "reflecting", "waiting", "blocked", "complete"}),
    "reasoning": frozenset({"unavailable", "pending", "deliberating", "concluded", "blocked"}),
    "planning": frozenset({"unavailable", "draft", "review_required", "approved", "rejected", "deferred", "complete"}),
    "campaign": frozenset({"unavailable", "approved_not_started", "ready", "active", "paused", "blocked", "complete", "abandoned"}),
    "approval": frozenset({"required", "approved_not_executed", "rejected", "deferred", "consumed_no_reuse"}),
    "action": frozenset({"not_started", "eligible_not_executing", "completed", "failed", "blocked"}),
    "result": frozenset({"unavailable", "pending", "passed", "failed", "blocked", "accepted", "rejected"}),
    "learning": frozenset({"unavailable", "pending", "recorded_unapplied", "rejected", "deferred"}),
}

AUTHORITY_STATES = frozenset({
    "none",
    "review_required",
    "approved_not_executed",
    "recorded_no_authority",
    "consumed_no_reuse",
})

_SURFACE_FIELDS = frozenset({
    "schema_version",
    "contract_version",
    "surface_id",
    "domain",
    "state",
    "sequence",
    "context_digest",
    "artifact_digest",
    "receipt_digest",
    "previous_surface_digest",
    "operator_review_digest",
    "authority_state",
    "is_focus",
    "content_free",
    "private_content_included",
    "execution_invoked",
    "automatic_continuation",
    "source_modified",
    "runtime_modified",
    "provider_contacted",
    "model_contacted",
    "authority_granted",
    "surface_digest",
})

_FORBIDDEN_KEY_TOKENS = (
    "prompt",
    "conversation_text",
    "message_text",
    "memory_content",
    "private_reasoning",
    "raw_source",
    "raw_patch",
    "stdout",
    "stderr",
    "provider_payload",
    "secret",
    "credential",
    "token_value",
    "authorization_granted",
    "release_authority",
)


def _digest(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _bounded(value: object) -> bool:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    return len(payload) <= MAX_CONTRACT_BYTES


def _is_digest(value: object) -> bool:
    return bool(DIGEST_RE.fullmatch(str(value or "").lower()))


def _verify_digest(row: Mapping[str, Any], field: str) -> tuple[str, bool]:
    unsigned = dict(row)
    claimed = str(unsigned.pop(field, "")).lower()
    return claimed, bool(_is_digest(claimed) and claimed == _digest(unsigned))


def _contains_forbidden_key(value: object) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            token = str(key).strip().lower()
            if any(forbidden in token for forbidden in _FORBIDDEN_KEY_TOKENS):
                return True
            if _contains_forbidden_key(item):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_contains_forbidden_key(item) for item in value)
    return False


def create_experience_surface(
    *,
    surface_id: str,
    domain: str,
    state: str,
    sequence: int,
    context_digest: str,
    artifact_digest: str,
    receipt_digest: str,
    previous_surface_digest: str = "",
    operator_review_digest: str = "",
    authority_state: str = "none",
    is_focus: bool = False,
) -> dict[str, Any]:
    """Create one exact content-free domain surface.

    Construction does not establish validity. The integration function verifies
    all identifiers, state semantics, lineage links, and authority boundaries.
    """

    row: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "surface_id": str(surface_id or ""),
        "domain": str(domain or ""),
        "state": str(state or ""),
        "sequence": int(sequence),
        "context_digest": str(context_digest or "").lower(),
        "artifact_digest": str(artifact_digest or "").lower(),
        "receipt_digest": str(receipt_digest or "").lower(),
        "previous_surface_digest": str(previous_surface_digest or "").lower(),
        "operator_review_digest": str(operator_review_digest or "").lower(),
        "authority_state": str(authority_state or ""),
        "is_focus": bool(is_focus),
        "content_free": True,
        "private_content_included": False,
        "execution_invoked": False,
        "automatic_continuation": False,
        "source_modified": False,
        "runtime_modified": False,
        "provider_contacted": False,
        "model_contacted": False,
        "authority_granted": False,
    }
    row["surface_digest"] = _digest(row)
    return row


def build_unified_experience_snapshot(
    *,
    experience_id: str,
    context_digest: str,
    surfaces: Sequence[Mapping[str, Any]],
    selected_surface_id: str,
    operator_view_digest: str,
) -> dict[str, Any]:
    """Validate and project one complete cross-domain current experience.

    Exactly one surface per domain is required. The projection is content-free,
    display-only, and authority-free. It never reads the underlying artifacts.
    """

    rows = [dict(item) for item in surfaces] if isinstance(surfaces, Sequence) and not isinstance(surfaces, (str, bytes, bytearray)) else []
    errors: list[str] = []
    experience_token = str(experience_id or "")
    context = str(context_digest or "").lower()
    selected = str(selected_surface_id or "")
    view_digest = str(operator_view_digest or "").lower()

    if not IDENTIFIER_RE.fullmatch(experience_token):
        errors.append("invalid_experience_id")
    if not _is_digest(context):
        errors.append("invalid_context_digest")
    if not _is_digest(view_digest):
        errors.append("invalid_operator_view_digest")
    if len(rows) != len(DOMAINS):
        errors.append("incomplete_domain_set")
    if not _bounded(rows):
        errors.append("oversized_contract")
    if _contains_forbidden_key(rows):
        errors.append("private_or_authority_content_present")

    seen_domains: set[str] = set()
    seen_ids: set[str] = set()
    artifact_digests: set[str] = set()
    receipt_digests: set[str] = set()
    focus_ids: list[str] = []
    previous = ""
    projections: list[dict[str, Any]] = []

    for index, row in enumerate(rows):
        domain = str(row.get("domain") or "")
        surface_id = str(row.get("surface_id") or "")
        state = str(row.get("state") or "")
        authority_state = str(row.get("authority_state") or "")
        surface_digest, digest_ok = _verify_digest(row, "surface_digest")

        unknown_fields = set(row) - _SURFACE_FIELDS
        if unknown_fields:
            errors.append("unsupported_surface_fields")
        if not digest_ok:
            errors.append("tampered_surface")
        if row.get("schema_version") != SCHEMA_VERSION or row.get("contract_version") != CONTRACT_VERSION:
            errors.append("surface_contract_mismatch")
        if domain not in DOMAINS:
            errors.append("unsupported_domain")
        if index >= len(DOMAINS) or domain != DOMAINS[index]:
            errors.append("domain_order_mismatch")
        if domain in seen_domains:
            errors.append("duplicate_domain")
        seen_domains.add(domain)
        if not IDENTIFIER_RE.fullmatch(surface_id):
            errors.append("invalid_surface_id")
        if surface_id in seen_ids:
            errors.append("duplicate_surface_id")
        seen_ids.add(surface_id)
        if row.get("sequence") != index:
            errors.append("sequence_mismatch")
        if row.get("context_digest") != context:
            errors.append("context_lineage_mismatch")
        if index == 0 and row.get("previous_surface_digest"):
            errors.append("unexpected_initial_surface_link")
        if index > 0 and row.get("previous_surface_digest") != previous:
            errors.append("surface_link_mismatch")
        previous = surface_digest
        if state not in DOMAIN_STATES.get(domain, frozenset()):
            errors.append("unsupported_domain_state")
        artifact = str(row.get("artifact_digest") or "").lower()
        receipt = str(row.get("receipt_digest") or "").lower()
        if not _is_digest(artifact):
            errors.append("invalid_artifact_digest")
        if not _is_digest(receipt):
            errors.append("invalid_receipt_digest")
        if artifact in artifact_digests:
            errors.append("duplicate_artifact_digest")
        artifact_digests.add(artifact)
        if receipt in receipt_digests:
            errors.append("duplicate_receipt_digest")
        receipt_digests.add(receipt)
        if authority_state not in AUTHORITY_STATES:
            errors.append("unsupported_authority_state")
        if authority_state in {"review_required", "approved_not_executed", "consumed_no_reuse"} and not _is_digest(row.get("operator_review_digest")):
            errors.append("missing_operator_review_digest")
        if authority_state in {"none", "recorded_no_authority"} and row.get("operator_review_digest") and not _is_digest(row.get("operator_review_digest")):
            errors.append("invalid_operator_review_digest")
        if row.get("content_free") is not True or row.get("private_content_included") is not False:
            errors.append("privacy_contract_violation")
        for field in (
            "execution_invoked",
            "automatic_continuation",
            "source_modified",
            "runtime_modified",
            "provider_contacted",
            "model_contacted",
            "authority_granted",
        ):
            if row.get(field) is not False:
                errors.append("authority_or_execution_expansion")
        if row.get("is_focus") is True:
            focus_ids.append(surface_id)

        projections.append({
            "surface_id": surface_id,
            "domain": domain,
            "state": state,
            "sequence": index,
            "artifact_digest": artifact,
            "receipt_digest": receipt,
            "surface_digest": surface_digest,
            "authority_state": authority_state,
            "is_focus": row.get("is_focus") is True,
            "content_free": True,
        })

    if seen_domains != set(DOMAINS):
        errors.append("domain_set_mismatch")
    if len(focus_ids) != 1:
        errors.append("exactly_one_focus_required")
    elif selected != focus_ids[0]:
        errors.append("selected_surface_mismatch")
    if selected not in seen_ids:
        errors.append("unknown_selected_surface")

    by_domain = {row.get("domain"): row for row in rows}
    approval_state = str((by_domain.get("approval") or {}).get("state") or "")
    action_state = str((by_domain.get("action") or {}).get("state") or "")
    result_state = str((by_domain.get("result") or {}).get("state") or "")
    learning_state = str((by_domain.get("learning") or {}).get("state") or "")

    if approval_state == "approved_not_executed" and action_state not in {"not_started", "eligible_not_executing"}:
        errors.append("approval_action_state_mismatch")
    if action_state in {"completed", "failed", "blocked"} and result_state in {"unavailable", "pending"}:
        errors.append("terminal_action_missing_result")
    if result_state in {"passed", "accepted"} and action_state != "completed":
        errors.append("result_action_state_mismatch")
    if learning_state == "recorded_unapplied" and result_state in {"unavailable", "pending"}:
        errors.append("learning_without_terminal_result")

    errors = sorted(set(errors))
    selected_row = next((row for row in projections if row["surface_id"] == selected), {})
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "experience_id": experience_token,
        "context_digest": context,
        "operator_view_digest": view_digest,
        "status": "ready_for_operator_view" if not errors else "blocked",
        "errors": errors,
        "error_count": len(errors),
        "surface_count": len(projections),
        "domain_count": len({row.get("domain") for row in projections}),
        "domains": list(DOMAINS),
        "selected_surface_id": selected,
        "selected_domain": selected_row.get("domain", ""),
        "selected_state": selected_row.get("state", ""),
        "review_required_count": sum(row.get("authority_state") == "review_required" for row in projections),
        "approved_not_executed_count": sum(row.get("authority_state") == "approved_not_executed" for row in projections),
        "blocked_surface_count": sum(row.get("state") == "blocked" for row in projections),
        "surfaces": projections,
        "content_free": True,
        "private_content_included": False,
        "records_duplicated": False if not ({"duplicate_domain", "duplicate_surface_id", "duplicate_artifact_digest", "duplicate_receipt_digest"} & set(errors)) else True,
        "execution_invoked": False,
        "automatic_continuation": False,
        "source_modified": False,
        "runtime_modified": False,
        "provider_contacted": False,
        "model_contacted": False,
        "approval_created": False,
        "approval_consumed": False,
        "authority_granted": False,
    }
    result["unified_experience_digest"] = _digest(result)
    return result


def unified_experience_public_summary(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Return the bounded dashboard/API summary without private content."""

    return {
        "contract_version": CONTRACT_VERSION,
        "experience_id": snapshot.get("experience_id", ""),
        "status": snapshot.get("status", ""),
        "surface_count": int(snapshot.get("surface_count", 0) or 0),
        "domain_count": int(snapshot.get("domain_count", 0) or 0),
        "selected_domain": snapshot.get("selected_domain", ""),
        "selected_state": snapshot.get("selected_state", ""),
        "review_required_count": int(snapshot.get("review_required_count", 0) or 0),
        "approved_not_executed_count": int(snapshot.get("approved_not_executed_count", 0) or 0),
        "blocked_surface_count": int(snapshot.get("blocked_surface_count", 0) or 0),
        "error_count": int(snapshot.get("error_count", 0) or 0),
        "unified_experience_digest": snapshot.get("unified_experience_digest", ""),
        "content_free": True,
        "authority_granted": False,
        "execution_invoked": False,
    }
