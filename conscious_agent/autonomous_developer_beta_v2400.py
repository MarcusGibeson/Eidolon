from __future__ import annotations

"""Era 10 bounded Autonomous Developer Beta coordination.

This state machine composes retained owners across the complete goal-to-candidate
path.  It records evidence and determines which stage may be prepared next; it
never performs installation, promotion, destructive work, model management, or
unreviewed live-source mutation.
"""

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock

CONTRACT_VERSION = "v2475.9"
STAGES = (
    "requirements", "architecture", "planning", "implementation", "testing",
    "repair", "evaluation", "documentation", "handoff", "review_ready",
)
RETAINED_STAGE_OWNERS = {
    "requirements": "problem_framing_v1700",
    "architecture": "deep_project_understanding",
    "planning": "long_horizon_planning_v1700",
    "implementation": "supervised_development_coordinator",
    "testing": "engineering_verification_intelligence",
    "repair": "supervised_repair_intelligence",
    "evaluation": "outcome_learning_governance_v2300",
    "documentation": "engineering_release_lifecycle",
    "handoff": "cooperative_development_v2300",
    "review_ready": "dynamic_development_backlog",
}
PORTFOLIO_CLASSES = {"defect", "capability", "maintenance", "learning"}

_DENIED = {
    "implementation_executed": False,
    "tests_executed": False,
    "source_modified": False,
    "candidate_installed": False,
    "candidate_promoted": False,
    "provider_contacted": False,
    "model_managed": False,
    "authority_expanded": False,
}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _hex64(value: Any) -> bool:
    s = str(value or "").lower()
    return len(s) == 64 and all(c in "0123456789abcdef" for c in s)


def _safe_code(value: Any, *, maximum: int = 160) -> str | None:
    text = str(value or "").strip()
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.:-")
    return text if text and len(text) <= maximum and all(ch in allowed for ch in text) else None


def _finite(value: Any, minimum: float = 0.0, maximum: float = 1.0) -> float | None:
    if isinstance(value, bool): return None
    try: f = float(value)
    except (TypeError, ValueError): return None
    return f if math.isfinite(f) and minimum <= f <= maximum else None


def build_goal_to_candidate_contract(
    *, goal_id: str, goal_digest: str, baseline_source_digest: str,
    scope_digest: str, maximum_stage_failures: int = 2, maximum_replans: int = 3,
) -> dict[str, Any]:
    errors = []
    if not str(goal_id or "").strip(): errors.append("invalid_goal_id")
    for name, value in (("goal_digest", goal_digest), ("baseline_source_digest", baseline_source_digest), ("scope_digest", scope_digest)):
        if not _hex64(value): errors.append(f"invalid_{name}")
    if not isinstance(maximum_stage_failures, int) or not 0 <= maximum_stage_failures <= 8: errors.append("invalid_failure_budget")
    if not isinstance(maximum_replans, int) or not 0 <= maximum_replans <= 8: errors.append("invalid_replan_budget")
    if errors:
        return {"ok": False, "status": "developer_beta_contract_blocked", "errors": errors, "content_free": True, **_DENIED}
    result = {
        "ok": True, "status": "developer_beta_contract_ready", "contract_version": CONTRACT_VERSION,
        "goal_id_digest": hashlib.sha256(str(goal_id).encode()).hexdigest(), "goal_digest": str(goal_digest).lower(),
        "baseline_source_digest": str(baseline_source_digest).lower(), "scope_digest": str(scope_digest).lower(),
        "stages": list(STAGES), "stage_owners": dict(RETAINED_STAGE_OWNERS),
        "budgets": {"maximum_stage_failures": maximum_stage_failures, "maximum_replans": maximum_replans},
        "final_state": "review_ready", "installation_is_out_of_scope": True, "promotion_is_out_of_scope": True,
        "content_free": True, **_DENIED,
    }
    result["contract_digest"] = _digest(result)
    return result


def build_stage_evidence(*, stage: str, artifact_digest: str, outcome: str = "passed", owner: str = "") -> dict[str, Any]:
    name = str(stage or "").strip()
    expected_owner = RETAINED_STAGE_OWNERS.get(name, "")
    supplied_owner = str(owner or expected_owner).strip()
    status = str(outcome or "").strip().lower()
    if name not in STAGES[:-1] or not _hex64(artifact_digest) or supplied_owner != expected_owner or status not in {"passed", "failed", "replan_required"}:
        return {"ok": False, "status": "developer_beta_stage_evidence_blocked", "content_free": True, **_DENIED}
    result = {
        "ok": True, "status": "developer_beta_stage_evidence_ready", "contract_version": CONTRACT_VERSION,
        "stage": name, "owner": expected_owner, "outcome": status, "artifact_digest": str(artifact_digest).lower(),
        "content_free": True, **_DENIED,
    }
    result["evidence_digest"] = _digest(result)
    return result


def _state_path(runtime_root: str | Path, goal_id: str) -> Path:
    safe = hashlib.sha256(str(goal_id).encode()).hexdigest()[:32]
    return Path(runtime_root).expanduser().resolve() / "era10" / "developer_beta" / f"{safe}.json"




def _read_state_strict(path: Path) -> tuple[dict[str, Any], str | None]:
    if not path.exists():
        return {}, None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}, "store_corrupt"
    if not isinstance(value, dict):
        return {}, "store_corrupt"
    return value, None


def _validate_state_semantics(state: Mapping[str, Any], *, expected_goal_id_digest: str | None = None) -> str | None:
    if (
        state.get("schema_version") != "2"
        or state.get("contract_version") != CONTRACT_VERSION
        or not _hex64(state.get("goal_id_digest"))
        or not _hex64(state.get("contract_digest"))
        or not _hex64(state.get("baseline_source_digest"))
        or not _hex64(state.get("scope_digest"))
        or state.get("stage") not in STAGES
        or state.get("status") not in {"active", "review_ready", "repair_or_retry_review_required", "replan_review_required", "blocked_failure_budget", "blocked_replan_budget"}
        or not isinstance(state.get("revision"), int) or isinstance(state.get("revision"), bool) or state.get("revision", 0) < 1
        or not isinstance(state.get("processed_events"), dict)
        or not isinstance(state.get("stage_receipts"), dict)
        or not isinstance(state.get("stage_failures"), dict)
        or not isinstance(state.get("replan_count"), int) or isinstance(state.get("replan_count"), bool) or state.get("replan_count", -1) < 0
    ):
        return "state_semantics_invalid"
    if expected_goal_id_digest is not None and state.get("goal_id_digest") != expected_goal_id_digest:
        return "goal_identity_mismatch"
    budgets = state.get("budgets")
    if not isinstance(budgets, Mapping):
        return "budget_state_invalid"
    for key in ("maximum_stage_failures", "maximum_replans"):
        value = budgets.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 8:
            return "budget_state_invalid"
    for event_digest, request_digest in state["processed_events"].items():
        if not _hex64(event_digest) or not _hex64(request_digest):
            return "processed_event_invalid"
    if len(state["processed_events"]) > 512:
        return "processed_event_invalid"
    for stage, count in state["stage_failures"].items():
        if stage not in STAGES[:-1] or not isinstance(count, int) or isinstance(count, bool) or count < 0:
            return "failure_state_invalid"
    for stage, receipt in state["stage_receipts"].items():
        if stage not in STAGES[:-1] or not isinstance(receipt, Mapping):
            return "receipt_state_invalid"
        receipt_digest = str(receipt.get("receipt_digest") or "")
        unsigned = dict(receipt); unsigned.pop("receipt_digest", None)
        if (
            not _hex64(receipt_digest) or receipt_digest != _digest(unsigned)
            or receipt.get("stage") != stage
            or receipt.get("owner") != RETAINED_STAGE_OWNERS[stage]
            or receipt.get("outcome") != "passed"
            or not _hex64(receipt.get("evidence_digest"))
            or not _hex64(receipt.get("artifact_digest"))
        ):
            return "receipt_state_invalid"
    completed = len(state["stage_receipts"])
    current_index = STAGES.index(str(state.get("stage")))
    if set(state["stage_receipts"]) != set(STAGES[:current_index]):
        return "stage_progression_invalid"
    if state.get("stage") == "review_ready" and (completed != len(STAGES) - 1 or state.get("status") != "review_ready"):
        return "review_ready_state_invalid"
    return None


def start_goal_to_candidate(*, runtime_root: str | Path, event_id: str, contract: Mapping[str, Any]) -> dict[str, Any]:
    cd = str(contract.get("contract_digest") or "")
    unsigned = dict(contract); unsigned.pop("contract_digest", None)
    if not contract.get("ok") or not _hex64(cd) or cd != _digest(unsigned):
        return {"ok": False, "status": "developer_beta_start_blocked", "reason": "invalid_or_tampered_contract", "content_free": True, **_DENIED}
    goal_id_digest = str(contract.get("goal_id_digest") or "")
    if not _hex64(goal_id_digest):
        return {"ok": False, "status": "developer_beta_start_blocked", "reason": "goal_id_digest_invalid", "content_free": True, **_DENIED}
    if not str(event_id or ""):
        return {"ok": False, "status": "developer_beta_start_blocked", "reason": "event_id_invalid", "content_free": True, **_DENIED}
    path = Path(runtime_root).expanduser().resolve() / "era10" / "developer_beta" / f"{goal_id_digest[:32]}.json"; path.parent.mkdir(parents=True, exist_ok=True)
    with metadata_mutation_lock(path, timeout_seconds=5):
        current, read_error = _load_verified(path, expected_goal_id_digest=goal_id_digest)
        if read_error and read_error != "missing":
            return {"ok": False, "status": "developer_beta_store_corrupt", "reason": read_error, "mutation_permitted": False, "content_free": True, **_DENIED}
        event_digest = hashlib.sha256(str(event_id).encode()).hexdigest()
        request_digest = _digest({"operation": "start", "contract_digest": cd})
        if current:
            prior_request = dict(current.get("processed_events") or {}).get(event_digest)
            if current.get("contract_digest") == cd and prior_request == request_digest:
                return {"ok": True, "status": "developer_beta_start_replayed", "state_digest": current.get("state_digest"), "idempotent": True, "content_free": True, **_DENIED}
            if prior_request is not None:
                return {"ok": False, "status": "developer_beta_event_conflict", "content_free": True, **_DENIED}
            return {"ok": False, "status": "developer_beta_existing_state_requires_review", "content_free": True, **_DENIED}
        state = {
            "schema_version": "2", "contract_version": CONTRACT_VERSION,
            "goal_id_digest": goal_id_digest, "contract_digest": cd, "baseline_source_digest": contract["baseline_source_digest"],
            "scope_digest": contract["scope_digest"], "budgets": dict(contract.get("budgets") or {}), "stage": "requirements", "revision": 1,
            "stage_receipts": {}, "stage_failures": {}, "replan_count": 0, "processed_events": {event_digest: request_digest},
            "status": "active", "content_free": True,
        }
        state["state_digest"] = _digest({k: v for k, v in state.items() if k != "state_digest"})
        write_json_atomic(path, state, expected_type=dict, sort_keys=True, coordinate=False)
    return {"ok": True, "status": "developer_beta_started", "stage": "requirements", "state_digest": state["state_digest"], "content_free": True, **_DENIED}


def _load_verified(path: Path, *, expected_goal_id_digest: str | None = None) -> tuple[dict[str, Any], str | None]:
    state, read_error = _read_state_strict(path)
    if read_error: return {}, read_error
    if not state: return {}, "missing"
    sd = str(state.get("state_digest") or ""); unsigned = dict(state); unsigned.pop("state_digest", None)
    if not _hex64(sd) or sd != _digest(unsigned): return state, "state_tampered"
    semantic_error = _validate_state_semantics(state, expected_goal_id_digest=expected_goal_id_digest)
    if semantic_error: return state, semantic_error
    return state, None


def record_stage_receipt(
    *, runtime_root: str | Path, goal_id: str, event_id: str, expected_state_digest: str,
    stage: str, evidence_digest: str, evidence_payload: Mapping[str, Any], outcome: str = "passed",
) -> dict[str, Any]:
    if not str(event_id or ""):
        return {"ok": False, "status": "developer_beta_stage_blocked", "reason": "event_id_invalid", "content_free": True, **_DENIED}
    path = _state_path(runtime_root, goal_id)
    goal_id_digest = hashlib.sha256(str(goal_id).encode()).hexdigest()
    with metadata_mutation_lock(path, timeout_seconds=5):
        state, error = _load_verified(path, expected_goal_id_digest=goal_id_digest)
        if error:
            return {"ok": False, "status": "developer_beta_stage_blocked", "reason": error, "content_free": True, **_DENIED}
        event_digest = hashlib.sha256(str(event_id).encode()).hexdigest()
        request_digest = _digest({
            "operation": "record_stage_receipt", "expected_state_digest": str(expected_state_digest),
            "stage": str(stage), "evidence_digest": str(evidence_digest).lower(), "outcome": str(outcome),
        })
        prior_request = dict(state.get("processed_events") or {}).get(event_digest)
        if prior_request == request_digest:
            return {"ok": True, "status": "developer_beta_stage_replayed", "stage": state.get("stage"), "state_digest": state.get("state_digest"), "idempotent": True, "content_free": True, **_DENIED}
        if prior_request is not None:
            return {"ok": False, "status": "developer_beta_stage_blocked", "reason": "event_payload_conflict", "content_free": True, **_DENIED}
        if str(state.get("state_digest")) != str(expected_state_digest):
            return {"ok": False, "status": "developer_beta_stage_blocked", "reason": "stale_state_digest", "content_free": True, **_DENIED}
        if state.get("status") in {"blocked_failure_budget", "blocked_replan_budget", "review_ready"}:
            return {"ok": False, "status": "developer_beta_stage_blocked", "reason": "campaign_not_mutable", "content_free": True, **_DENIED}
        current = str(state.get("stage") or "")
        payload = dict(evidence_payload or {}) if isinstance(evidence_payload, Mapping) else {}
        payload_digest = str(payload.get("evidence_digest") or "")
        unsigned_payload = dict(payload); unsigned_payload.pop("evidence_digest", None)
        evidence_valid = (
            payload.get("ok") is True
            and payload.get("status") == "developer_beta_stage_evidence_ready"
            and _hex64(payload_digest) and payload_digest == _digest(unsigned_payload)
            and str(evidence_digest).lower() == payload_digest
            and payload.get("stage") == stage
            and payload.get("owner") == RETAINED_STAGE_OWNERS.get(stage)
            and payload.get("outcome") == outcome
            and _hex64(payload.get("artifact_digest"))
        )
        if stage != current or stage not in STAGES or stage == "review_ready" or not evidence_valid:
            return {"ok": False, "status": "developer_beta_stage_blocked", "reason": "stage_or_evidence_invalid", "content_free": True, **_DENIED}
        if outcome not in {"passed", "failed", "replan_required"}:
            return {"ok": False, "status": "developer_beta_stage_blocked", "reason": "invalid_outcome", "content_free": True, **_DENIED}
        processed_events = dict(state.get("processed_events") or {})
        processed_events[event_digest] = request_digest
        state["processed_events"] = dict(list(processed_events.items())[-512:])
        budgets = dict(state.get("budgets") or {})
        if not isinstance(budgets.get("maximum_stage_failures"), int) or not isinstance(budgets.get("maximum_replans"), int):
            return {"ok": False, "status": "developer_beta_stage_blocked", "reason": "budget_state_invalid", "content_free": True, **_DENIED}
        if outcome == "failed":
            failures = dict(state.get("stage_failures") or {}); failures[stage] = int(failures.get(stage, 0)) + 1; state["stage_failures"] = failures
            if failures[stage] > budgets["maximum_stage_failures"]:
                state["status"] = "blocked_failure_budget"; state["revision"] += 1
            else:
                state["status"] = "repair_or_retry_review_required"; state["revision"] += 1
        elif outcome == "replan_required":
            state["replan_count"] = int(state.get("replan_count", 0)) + 1
            state["status"] = "blocked_replan_budget" if state["replan_count"] > budgets["maximum_replans"] else "replan_review_required"
            state["revision"] += 1
        else:
            receipts = dict(state.get("stage_receipts") or {})
            receipt = {"stage": stage, "owner": RETAINED_STAGE_OWNERS[stage], "evidence_digest": str(evidence_digest).lower(), "artifact_digest": str(payload.get("artifact_digest") or "").lower(), "outcome": "passed"}
            receipt["receipt_digest"] = _digest(receipt); receipts[stage] = receipt; state["stage_receipts"] = receipts
            idx = STAGES.index(stage); next_stage = STAGES[idx + 1]
            state["stage"] = next_stage; state["status"] = "review_ready" if next_stage == "review_ready" else "active"; state["revision"] += 1
        state["state_digest"] = _digest({k: v for k, v in state.items() if k != "state_digest"})
        write_json_atomic(path, state, expected_type=dict, sort_keys=True, coordinate=False)
    return {"ok": True, "status": "developer_beta_stage_recorded", "stage": state["stage"], "campaign_status": state["status"], "state_digest": state["state_digest"], "content_free": True, **_DENIED}


def inspect_goal_to_candidate(*, runtime_root: str | Path, goal_id: str) -> dict[str, Any]:
    state, error = _load_verified(_state_path(runtime_root, goal_id), expected_goal_id_digest=hashlib.sha256(str(goal_id).encode()).hexdigest())
    if error: return {"ok": False, "status": f"developer_beta_{error}", "content_free": True, **_DENIED}
    return {
        "ok": True, "status": "developer_beta_state_ready", "goal_id_digest": state.get("goal_id_digest"), "stage": state.get("stage"),
        "campaign_status": state.get("status"), "revision": state.get("revision"), "completed_stage_count": len(state.get("stage_receipts") or {}),
        "failure_count": sum(int(v) for v in dict(state.get("stage_failures") or {}).values()), "replan_count": int(state.get("replan_count", 0)),
        "state_digest": state.get("state_digest"), "review_ready_is_not_installation": True, "content_free": True, **_DENIED,
    }


def rank_portfolio(candidates: Sequence[Mapping[str, Any]], *, budget_units: Any = 1.0) -> dict[str, Any]:
    budget = _finite(budget_units, 0.0, 1e6)
    if budget is None:
        return {"ok": False, "status": "portfolio_ranking_blocked", "reason": "invalid_budget", "content_free": True, **_DENIED}
    rows = []; rejected = 0; seen_ids: set[str] = set(); seen_evidence: set[str] = set()
    class_bonus = {"defect": 0.18, "capability": 0.12, "maintenance": 0.05, "learning": 0.08}
    for row in candidates:
        if not isinstance(row, Mapping): rejected += 1; continue
        cid = _safe_code(row.get("candidate_id")); cls = str(row.get("class") or "").strip().lower(); ev = str(row.get("evidence_digest") or "").lower()
        vals = {k: _finite(row.get(k), 0.0, 1.0) for k in ("value", "evidence_quality", "strategic_alignment", "novelty", "reversibility", "risk")}
        cost = _finite(row.get("cost_units"), 0.0, 1e6)
        deps_value = row.get("dependencies_satisfied", True)
        if (
            not cid or cls not in PORTFOLIO_CLASSES or not _hex64(ev)
            or any(v is None for v in vals.values()) or cost is None
            or not isinstance(deps_value, bool) or cid in seen_ids or ev in seen_evidence
        ):
            rejected += 1; continue
        deps = deps_value; seen_ids.add(cid); seen_evidence.add(ev)
        eligible = deps and cost <= budget
        score = 0.0
        if eligible:
            score = (
                0.28 * vals["value"] + 0.22 * vals["evidence_quality"] + 0.20 * vals["strategic_alignment"] +
                0.12 * vals["novelty"] + 0.10 * vals["reversibility"] - 0.18 * vals["risk"] + class_bonus[cls]
            )
        rows.append({"candidate_id": cid, "class": cls, "evidence_digest": ev.lower(), "eligible": eligible, "score": round(score, 6), "cost_units": cost, "dependencies_satisfied": deps})
    rows.sort(key=lambda r: (-r["score"], r["candidate_id"]))
    result = {
        "ok": True, "status": "portfolio_ranked", "ranked_candidates": rows, "rejected_count": rejected,
        "selected_candidate_id": next((r["candidate_id"] for r in rows if r["eligible"]), ""),
        "portfolio_classes_present": sorted(set(r["class"] for r in rows)), "selection_is_advisory_only": True,
        "content_free": True, **_DENIED,
    }
    result["portfolio_digest"] = _digest(result); return result


__all__ = [
    "CONTRACT_VERSION", "STAGES", "RETAINED_STAGE_OWNERS", "build_goal_to_candidate_contract", "build_stage_evidence",
    "start_goal_to_candidate", "record_stage_receipt", "inspect_goal_to_candidate", "rank_portfolio",
]
