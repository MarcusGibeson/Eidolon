from __future__ import annotations

"""v2509 content-minimized receipts for the general action framework."""

import hashlib
import json
from typing import Any, Mapping

CONTRACT_VERSION = "v2509.7"


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def build_action_review_receipt(intent: Mapping[str, Any], *, review_state: str = "awaiting_operator_review") -> dict[str, Any]:
    if not str(intent.get("intent_digest") or ""):
        raise ValueError("intent_digest_required")
    state = str(review_state or "").strip().lower()
    if state not in {"awaiting_operator_review", "not_ready", "rejected"}:
        raise ValueError("unsupported_review_state")
    row = {
        "contract_version": CONTRACT_VERSION,
        "capability_id": str(intent.get("capability_id") or "")[:80],
        "manifest_digest": str(intent.get("manifest_digest") or "")[:64],
        "intent_digest": str(intent.get("intent_digest") or "")[:64],
        "review_state": state,
        "approval_granted": False,
        "authorization_granted": False,
        "execution_admitted": False,
        "execution_performed": False,
        "adapter_invoked": False,
        "side_effect_performed": False,
        "exactly_once_consumed": False,
        "rollback_performed": False,
        "raw_arguments_stored": False,
        "raw_output_stored": False,
        "content_free": True,
    }
    row["receipt_digest"] = _digest(row)
    return row


__all__ = ["CONTRACT_VERSION", "build_action_review_receipt"]
