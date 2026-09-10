from __future__ import annotations
"""v2623 review-only binding from an operator-selected portfolio candidate into a queue entry."""
from typing import Any, Mapping
import hashlib, json

CONTRACT_VERSION = "v2623.0"


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def build_portfolio_to_queue_review(
    portfolio_review: Mapping[str, Any],
    operator_selection: Mapping[str, Any],
    queue: Mapping[str, Any],
    readiness: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    readiness = readiness if isinstance(readiness, Mapping) else {}
    selection_ok = bool(operator_selection.get("operator_selection_bound"))
    project_id = str(operator_selection.get("project_id") or "")[:120]
    project_digest = str(operator_selection.get("project_digest") or "")[:64]
    queue_entry = next(
        (
            e for e in (queue.get("entries") or [])
            if isinstance(e, Mapping)
            and str(e.get("project_id") or "") == project_id
            and str(e.get("project_digest") or "") == project_digest
        ),
        None,
    )
    review_digest_matches = bool(portfolio_review.get("review_digest")) and str(operator_selection.get("portfolio_review_digest") or "") == str(portfolio_review.get("review_digest") or "")
    queue_bound = queue_entry is not None
    ready = project_id in {str(x) for x in readiness.get("ready_project_ids") or []}
    valid = selection_ok and review_digest_matches and queue_bound
    out = {
        "ok": valid,
        "contract_version": CONTRACT_VERSION,
        "project_id": project_id if valid else "",
        "project_digest": project_digest if valid else "",
        "portfolio_review_digest": str(portfolio_review.get("review_digest") or "")[:64],
        "selection_digest": str(operator_selection.get("selection_digest") or "")[:64],
        "queue_digest": str(queue.get("queue_digest") or "")[:64],
        "readiness_digest": str(readiness.get("readiness_digest") or "")[:64],
        "queue_entry_status": str(queue_entry.get("status") or "") if queue_entry else "",
        "ready": bool(ready and valid),
        "operator_review_required": True,
        "queue_entry_applied": False,
        "campaign_started": False,
        "automatic_enqueue_permitted": False,
        "automatic_project_start_permitted": False,
        "source_mutation_authorized": False,
        "authority_granted": False,
    }
    out["review_binding_digest"] = _digest(out)
    return out


__all__ = ["CONTRACT_VERSION", "build_portfolio_to_queue_review"]
