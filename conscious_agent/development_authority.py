from __future__ import annotations

"""Digest-bound operator authorization receipts for supervised development.

Receipts are issued only from an exact operator command boundary. Downstream
modules validate the sealed stage, subject, evidence, and optional private scope
digest instead of trusting caller-supplied booleans.
"""

import hashlib
import json
import re
from typing import Any, Mapping


CONTRACT_VERSION = "v1500.0.1"
ALLOWED_STAGES = {
    "candidate_selection",
    "workspace_preparation",
    "workspace_implementation",
    "bounded_repair",
    "installation",
    "operator_review",
}
_HEX64 = re.compile(r"[0-9a-f]{64}")
_SUBJECT = re.compile(r"[A-Za-z0-9_.:-]{1,160}")


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()
    ).hexdigest()


def is_hex64(value: Any) -> bool:
    return bool(_HEX64.fullmatch(str(value or "").casefold()))


def private_scope_digest(value: str) -> str:
    """Bind a private path/scope without exposing it in public evidence."""
    return hashlib.sha256(str(value or "").casefold().encode("utf-8")).hexdigest()


def issue_operator_authorization(
    *,
    stage: str,
    subject_id: str,
    subject_digest: str,
    explicit_operator_text: str,
    expected_operator_text: str,
    scope_digest: str = "",
) -> dict[str, Any]:
    stage_value = str(stage or "").casefold()
    subject_value = str(subject_id or "")
    evidence_value = str(subject_digest or "").casefold()
    scope_value = str(scope_digest or "").casefold()
    exact = str(explicit_operator_text or "").strip() == str(expected_operator_text or "").strip()
    valid = bool(
        exact
        and stage_value in ALLOWED_STAGES
        and _SUBJECT.fullmatch(subject_value)
        and is_hex64(evidence_value)
        and (not scope_value or is_hex64(scope_value))
    )
    core = {
        "contract_version": CONTRACT_VERSION,
        "stage": stage_value,
        "subject_id": subject_value,
        "subject_digest": evidence_value,
        "scope_digest": scope_value,
        "operator_command_digest": digest(str(expected_operator_text or "").strip()),
        "authority": "operator" if valid else "none",
        "authorized": valid,
        "content_free": True,
    }
    core["authorization_id"] = f"dev-auth-{digest(core)[:24]}"
    core["receipt_digest"] = digest(core)
    return core


def validate_operator_authorization(
    receipt: Mapping[str, Any] | None,
    *,
    stage: str,
    subject_id: str,
    subject_digest: str,
    scope_digest: str = "",
) -> dict[str, Any]:
    row = dict(receipt or {})
    supplied_receipt_digest = str(row.pop("receipt_digest", "") or "").casefold()
    expected_scope = str(scope_digest or "").casefold()
    checks = {
        "sealed": is_hex64(supplied_receipt_digest) and supplied_receipt_digest == digest(row),
        "contract": row.get("contract_version") == CONTRACT_VERSION,
        "authorized": row.get("authorized") is True and row.get("authority") == "operator",
        "stage": str(row.get("stage") or "") == str(stage or "").casefold(),
        "subject": str(row.get("subject_id") or "") == str(subject_id or ""),
        "evidence": is_hex64(subject_digest) and str(row.get("subject_digest") or "") == str(subject_digest).casefold(),
        "scope": str(row.get("scope_digest") or "") == expected_scope,
        "command_bound": is_hex64(row.get("operator_command_digest")),
    }
    return {
        "ok": all(checks.values()),
        "checks": checks,
        "authorization_id": str(row.get("authorization_id") or ""),
        "receipt_digest": supplied_receipt_digest,
        "content_free": True,
    }


__all__ = [
    "CONTRACT_VERSION",
    "digest",
    "is_hex64",
    "issue_operator_authorization",
    "private_scope_digest",
    "validate_operator_authorization",
]
