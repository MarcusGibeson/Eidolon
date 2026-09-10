from __future__ import annotations

"""Bounded public presentation of authoritative supervised-action results.

This module accepts already-authoritative, content-free terminal receipts. It does
not read ledgers, invoke executors, grant authority, or expose raw output.
"""

import hashlib
import json
import re
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1178.8"
MAX_PRESENTATION_BYTES = 4096
_TERMINAL_STATES = {
    "execution_succeeded", "execution_failed", "execution_cancelled", "execution_timed_out"
}
_STATE_LABELS = {
    "execution_succeeded": "completed successfully",
    "execution_failed": "failed",
    "execution_cancelled": "was cancelled",
    "execution_timed_out": "timed out",
}


def _hex64(value: Any) -> str:
    text = str(value or "").lower()
    return text if re.fullmatch(r"[0-9a-f]{64}", text) else ""


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def build_supervised_result_presentation(
    capability_id: str,
    authoritative_receipts: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Return one exact bounded presentation for a registered capability."""
    capability = str(capability_id or "")[:80]
    valid: list[dict[str, Any]] = []
    for item in authoritative_receipts:
        if not isinstance(item, Mapping):
            continue
        state = str(item.get("state") or "")
        receipt = {
            "proposal_id": str(item.get("proposal_id") or "")[:80],
            "capability_id": str(item.get("capability_id") or "")[:80],
            "state": state,
            "terminal": item.get("terminal") is True,
            "content_free": item.get("content_free") is True,
            "terminal_result_digest": _hex64(item.get("terminal_result_digest")),
            "supervised_result_digest": _hex64(item.get("supervised_result_digest")),
            "outcome_digest": _hex64(item.get("outcome_digest")),
            "error_kind": str(item.get("error_kind") or "")[:80],
            "elapsed_ms": max(0, min(int(item.get("elapsed_ms") or 0), 120000)),
        }
        exact = bool(
            receipt["capability_id"] == capability
            and receipt["state"] in _TERMINAL_STATES
            and receipt["terminal"]
            and receipt["content_free"]
            and receipt["terminal_result_digest"]
            and receipt["supervised_result_digest"]
            and receipt["outcome_digest"]
        )
        if exact:
            valid.append(receipt)
    deduplicated: dict[str, dict[str, Any]] = {}
    for receipt in valid:
        deduplicated[receipt["terminal_result_digest"]] = receipt
    valid = list(deduplicated.values())
    selected = valid[-1] if len(valid) == 1 else None
    state = selected["state"] if selected else "unavailable"
    result = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "capability_id": capability,
        "presentation_status": "authoritative_terminal_result" if selected else ("ambiguous" if len(valid) > 1 else "unavailable"),
        "state": state,
        "status_label": _STATE_LABELS.get(state, "not available"),
        "authoritative_receipt_present": selected is not None,
        "receipt_count": len(valid),
        "terminal_result_digest": selected["terminal_result_digest"] if selected else "",
        "supervised_result_digest": selected["supervised_result_digest"] if selected else "",
        "outcome_digest": selected["outcome_digest"] if selected else "",
        "error_kind": selected["error_kind"] if selected else "",
        "elapsed_ms": selected["elapsed_ms"] if selected else 0,
        "raw_output_included": False,
        "raw_arguments_included": False,
        "authority_granted": False,
        "execution_invoked": False,
        "content_free": True,
    }
    result["presentation_digest"] = _digest(result)
    if len(json.dumps(result, sort_keys=True, separators=(",", ":")).encode()) > MAX_PRESENTATION_BYTES:
        raise ValueError("Supervised result presentation exceeded bounded size")
    return result


def supervised_result_prompt(presentation: Mapping[str, Any]) -> str:
    if presentation.get("authoritative_receipt_present"):
        return (
            "Authoritative supervised-action result presentation (bounded):\n"
            f"- Registered capability: {presentation.get('capability_id')}.\n"
            f"- Terminal state: {presentation.get('state')} ({presentation.get('status_label')}).\n"
            "- State only what this bounded receipt proves. Do not invent raw output, details, causes, fixes, approval, or authority.\n"
            "- The current conversation did not execute the action."
        )
    return (
        "Authoritative supervised-action result presentation (bounded):\n"
        "- No unique authoritative terminal receipt is available for this exact capability.\n"
        "- Do not claim execution, success, failure, output, approval, or authorization."
    )
