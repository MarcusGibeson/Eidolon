from __future__ import annotations
"""Reviewed retrieval-policy changes with atomic policy and receipt commits."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
import hashlib
import json
from json_storage import write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from runtime_data_bootstrap import default_runtime_data_dir
from memory_retrieval_policy_review_v2585 import build_memory_retrieval_policy_review_packet

CONTRACT_VERSION = "v2730.9.3"
DEFAULT_POLICY = {"schema_version": "1", "precise_selected_limit": 8, "fallback_selected_limit": 4, "revision": 0}
_DENIED = {"memory_content_mutated": False, "source_mutation_allowed": False, "authority_expanded": False, "automatic_policy_change_permitted": False}


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _root(runtime_root=None) -> Path:
    base = Path(runtime_root).expanduser().resolve() if runtime_root else default_runtime_data_dir()
    if base.is_relative_to(Path(__file__).resolve().parents[1]):
        raise ValueError("external_runtime_root_required")
    return base / "cognition"


def _valid_policy(policy):
    return (isinstance(policy, dict) and set(policy) == set(DEFAULT_POLICY)
            and policy["schema_version"] == "1"
            and type(policy["revision"]) is int and policy["revision"] >= 0
            and type(policy["precise_selected_limit"]) is int and 1 <= policy["precise_selected_limit"] <= 16
            and type(policy["fallback_selected_limit"]) is int and 1 <= policy["fallback_selected_limit"] <= 8)


def _read_state(runtime_root=None):
    path = _root(runtime_root) / "memory_retrieval_policy.json"
    if not path.exists():
        return {"state_schema": 2, "policy": deepcopy(DEFAULT_POLICY), "receipts": []}
    state = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(state, dict):
        raise ValueError("invalid_policy_state")
    if "state_schema" not in state:
        if not _valid_policy(state):
            raise ValueError("invalid_legacy_policy")
        # Old policy is a baseline only: unvalidated old receipts grant no rollback.
        return {"state_schema": 2, "policy": state, "receipts": []}
    unsigned = {k: v for k, v in state.items() if k != "state_digest"}
    if (state.get("state_schema") != 2 or state.get("state_digest") != _digest(unsigned)
            or not _valid_policy(state.get("policy")) or not isinstance(state.get("receipts"), list)):
        raise ValueError("invalid_policy_state")
    for receipt in state["receipts"]:
        if not isinstance(receipt, dict) or receipt.get("receipt_digest") != _digest({k: v for k, v in receipt.items() if k != "receipt_digest"}):
            raise ValueError("invalid_policy_receipt")
        if not _valid_policy(receipt.get("before_policy")) or not _valid_policy(receipt.get("after_policy")):
            raise ValueError("invalid_policy_receipt")
        if receipt.get("before_digest") != _digest(receipt["before_policy"]) or receipt.get("after_digest") != _digest(receipt["after_policy"]):
            raise ValueError("invalid_policy_receipt")
    return unsigned


def load_memory_retrieval_policy(runtime_root=None) -> dict[str, Any]:
    return deepcopy(_read_state(runtime_root)["policy"])


def _canonical_review(review):
    profiles = [{"history_label": "adverse_history", "retrieval_state": x.get("retrieval_state"),
                 "count": x.get("observation_count"), "negative": x.get("negative_count"),
                 "corrections": x.get("correction_count"), "evidence_confidence": x.get("evidence_confidence")}
                for x in review.get("candidates", [])]
    return build_memory_retrieval_policy_review_packet({"profiles": profiles})


def build_memory_retrieval_policy_candidate(review: Mapping[str, Any], *, runtime_root=None) -> dict[str, Any]:
    if dict(review) != _canonical_review(review):
        raise ValueError("validated_policy_review_required")
    changes = {}
    if any(x["negative_count"] > 0 or x["correction_count"] > 0 for x in review["candidates"]):
        changes = {"fallback_selected_limit": 3}
    state = _read_state(runtime_root)
    changes = {k: v for k, v in changes.items() if state["policy"][k] != v}
    out = {"ok": True, "contract_version": CONTRACT_VERSION, "review": dict(review),
           "review_digest": review["review_digest"], "baseline_digest": _digest(state),
           "changes": changes, "operator_confirmation_required": bool(changes), **_DENIED}
    out["candidate_digest"] = _digest(out)
    return out


def _commit(state, receipt, path):
    receipt["receipt_digest"] = _digest(receipt)
    state["receipts"].append(receipt)
    state["policy"] = receipt["after_policy"]
    state["state_digest"] = _digest(state)
    write_json_atomic(path, state, expected_type=dict, sort_keys=True)


def _receipt(kind, before, after, identity):
    return {"kind": kind, "receipt_id": "memory-policy-" + _digest([kind, before, after, identity])[:24],
            "candidate_digest": identity, "before_policy": before, "after_policy": after,
            "before_digest": _digest(before), "after_digest": _digest(after),
            "operator_confirmed": True, "occurred_at": datetime.now(timezone.utc).isoformat(), **_DENIED}


def authorize_and_apply_memory_retrieval_policy(candidate: Mapping[str, Any], *, operator_confirmation: bool, runtime_root=None) -> dict[str, Any]:
    if operator_confirmation is not True:
        return {"ok": False, "status": "explicit_operator_confirmation_required", **_DENIED}
    path = _root(runtime_root) / "memory_retrieval_policy.json"
    with metadata_mutation_lock(path, timeout_seconds=5):
        state = _read_state(runtime_root)
        try:
            expected = build_memory_retrieval_policy_candidate(candidate.get("review", {}), runtime_root=runtime_root)
        except (ValueError, KeyError, TypeError, AttributeError):
            return {"ok": False, "status": "validated_policy_candidate_required", **_DENIED}
        if dict(candidate) != expected or not candidate.get("changes"):
            return {"ok": False, "status": "stale_or_invalid_policy_candidate", **_DENIED}
        if len(state["receipts"]) >= 1024:
            return {"ok": False, "status": "policy_receipt_capacity_reached", **_DENIED}
        before = state["policy"]
        after = dict(before, **candidate["changes"])
        after["revision"] += 1
        receipt = _receipt("apply", before, after, candidate["candidate_digest"])
        _commit(state, receipt, path)
    return {"ok": True, "status": "memory_retrieval_policy_applied", "policy": after, "receipt": receipt, "retrieval_policy_changed": True, **_DENIED}


def authorize_and_rollback_memory_retrieval_policy(receipt_id: str, *, operator_confirmation: bool, runtime_root=None) -> dict[str, Any]:
    if operator_confirmation is not True:
        return {"ok": False, "status": "explicit_operator_confirmation_required", **_DENIED}
    path = _root(runtime_root) / "memory_retrieval_policy.json"
    with metadata_mutation_lock(path, timeout_seconds=5):
        state = _read_state(runtime_root)
        receipt = state["receipts"][-1] if state["receipts"] else {}
        if receipt.get("receipt_id") != receipt_id or receipt.get("kind") != "apply" or state["policy"] != receipt.get("after_policy"):
            return {"ok": False, "status": "stale_policy_rollback_rejected", **_DENIED}
        if len(state["receipts"]) >= 1024:
            return {"ok": False, "status": "policy_receipt_capacity_reached", **_DENIED}
        prior = deepcopy(receipt["before_policy"])
        rollback = _receipt("rollback", state["policy"], prior, receipt_id)
        _commit(state, rollback, path)
    return {"ok": True, "status": "memory_retrieval_policy_rolled_back", "restored_policy": prior,
            "restored_digest": _digest(prior), "source_receipt_id": receipt_id, "receipt": rollback, **_DENIED}


__all__ = ["CONTRACT_VERSION", "DEFAULT_POLICY", "load_memory_retrieval_policy", "build_memory_retrieval_policy_candidate", "authorize_and_apply_memory_retrieval_policy", "authorize_and_rollback_memory_retrieval_policy"]
