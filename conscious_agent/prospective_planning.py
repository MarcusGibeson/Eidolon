from __future__ import annotations

"""Bounded prospective planning and counterfactual evaluation.

Plans compare possible futures, risks, expected outcomes, uncertainty, and
reversibility. A recommendation may become an internal proposal, never an
authorized or executed action. No provider or external system is contacted.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping
import uuid

try:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from persistent_motivation import MotivationStore
    from self_directed_inquiry import InquiryWorkspace
except ImportError:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from persistent_motivation import MotivationStore
    from self_directed_inquiry import InquiryWorkspace

PLANNING_SCHEMA_VERSION = "1"
PLANNING_CONTRACT_VERSION = "v1105.1"
ACTIVE_STATUSES = {"draft", "evaluated", "proposed", "paused"}
TERMINAL_STATUSES = {"completed", "abandoned", "corrected", "superseded"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _clean(value: Any, limit: int = 700) -> str:
    return " ".join(str(value or "").split())[: max(0, int(limit))]


def _bounded(value: Any, minimum: float = 0.0, maximum: float = 1.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = minimum
    return round(max(minimum, min(maximum, number)), 4)


def _digest(*parts: Any) -> str:
    material = "\x1f".join(_clean(part, 2400) for part in parts)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _default_runtime_root() -> Path:
    root = Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data").expanduser().resolve()
    return root / "cognition"


def _default_state() -> dict[str, Any]:
    return {
        "schema_version": PLANNING_SCHEMA_VERSION,
        "contract_version": PLANNING_CONTRACT_VERSION,
        "plans": [],
        "processed_events": [],
        "revision": 0,
        "updated_at": "",
        "resource_limits": {
            "max_open_plans": 16,
            "max_alternatives_per_plan": 8,
            "max_counterfactuals_per_plan": 24,
            "provider_requests_per_evaluation": 0,
        },
        "authority_boundary": {
            "plan_can_authorize_action": False,
            "plan_can_execute_action": False,
            "proposal_is_authorized_action": False,
            "operator_approval_required_for_protected_action": True,
            "operator_authority_unchanged": True,
        },
    }


class ProspectivePlanningStore:
    def __init__(
        self,
        runtime_root: str | Path | None = None,
        *,
        motivation_store: MotivationStore | None = None,
        inquiry_store: InquiryWorkspace | None = None,
        clock: Callable[[], str] | None = None,
        event_history_limit: int = 512,
    ) -> None:
        self.runtime_root = Path(runtime_root).expanduser().resolve() if runtime_root else _default_runtime_root()
        self.path = self.runtime_root / "prospective_planning.json"
        self.motivations = motivation_store or MotivationStore(self.runtime_root)
        self.inquiries = inquiry_store or InquiryWorkspace(self.runtime_root, motivation_store=self.motivations)
        self.clock = clock or _utc_now
        self.event_history_limit = max(64, int(event_history_limit))

    def _load(self) -> dict[str, Any]:
        state = load_json_file(self.path, _default_state(), expected_type=dict)
        if state.get("schema_version") != PLANNING_SCHEMA_VERSION:
            return _default_state()
        for key, default in _default_state().items():
            state.setdefault(key, deepcopy(default))
        return state

    def snapshot(self) -> dict[str, Any]:
        return deepcopy(self._load())

    def _mutate(self, event_id: str, mutator: Callable[[dict[str, Any], str], dict[str, Any]]) -> dict[str, Any]:
        event_id = _clean(event_id, 160)
        if not event_id:
            raise ValueError("event_id is required")
        with metadata_mutation_lock(self.path, timeout_seconds=5.0):
            state = self._load()
            prior = next((row for row in state["processed_events"] if row.get("event_id") == event_id), None)
            if prior:
                return {"ok": True, "status": "duplicate_event_ignored", "result": deepcopy(prior.get("result") or {}), "idempotent": True}
            now = self.clock()
            result = mutator(state, now)
            state["revision"] = int(state.get("revision") or 0) + 1
            state["updated_at"] = now
            state["processed_events"] = (list(state["processed_events"]) + [{
                "event_id": event_id,
                "event_digest": _digest(event_id),
                "occurred_at": now,
                "result": deepcopy(result),
                "content_free": True,
            }])[-self.event_history_limit :]
            write_json_atomic(self.path, state, expected_type=dict, sort_keys=True)
            return {"ok": True, "status": str(result.get("status") or "updated"), "result": deepcopy(result), "idempotent": False}

    @staticmethod
    def _normalize_alternative(value: Mapping[str, Any], index: int) -> dict[str, Any]:
        label = _clean(value.get("label") or value.get("name"), 220)
        if not label:
            raise ValueError("each alternative requires a label")
        return {
            "alternative_id": _clean(value.get("alternative_id"), 120) or f"alternative-{index + 1}-{uuid.uuid4().hex}",
            "label": label,
            "expected_outcomes": [_clean(row, 260) for row in (value.get("expected_outcomes") or []) if _clean(row, 260)][:12],
            "risks": [_clean(row, 260) for row in (value.get("risks") or []) if _clean(row, 260)][:12],
            "expected_benefit": _bounded(value.get("expected_benefit", 0.5)),
            "risk": _bounded(value.get("risk", 0.5)),
            "reversibility": _bounded(value.get("reversibility", 0.5)),
            "confidence": _bounded(value.get("confidence", 0.5)),
            "score": None,
            "rank": None,
        }

    def create_plan(
        self,
        event_id: str,
        *,
        subject: str,
        alternatives: Iterable[Mapping[str, Any]],
        motivation_ids: Iterable[str] = (),
        inquiry_ids: Iterable[str] = (),
        constraints: Iterable[str] = (),
        project_id: str = "",
        plan_id: str = "",
    ) -> dict[str, Any]:
        subject = _clean(subject, 700)
        if not subject:
            raise ValueError("subject is required")
        normalized = [self._normalize_alternative(row, index) for index, row in enumerate(alternatives)]
        if len(normalized) < 2:
            raise ValueError("prospective planning requires at least two alternatives")
        state_limits = self._load()["resource_limits"]
        if len(normalized) > int(state_limits["max_alternatives_per_plan"]):
            raise ValueError("alternative budget exceeded")
        motivation_ids = sorted({_clean(row, 120) for row in motivation_ids if _clean(row, 120)})
        inquiry_ids = sorted({_clean(row, 120) for row in inquiry_ids if _clean(row, 120)})
        active_motivation_ids = {row.get("motivation_id") for row in self.motivations.active_motivations()}
        missing_motivations = [row for row in motivation_ids if row not in active_motivation_ids]
        if missing_motivations:
            raise KeyError(f"active motivation not found: {missing_motivations[0]}")
        inquiry_state = self.inquiries.snapshot()
        known_inquiry_ids = {row.get("inquiry_id") for row in inquiry_state.get("inquiries") or [] if row.get("status") in {"active", "paused", "completed"}}
        missing_inquiries = [row for row in inquiry_ids if row not in known_inquiry_ids]
        if missing_inquiries:
            raise KeyError(f"inquiry not found: {missing_inquiries[0]}")
        constraint_rows = sorted({_clean(row, 260) for row in constraints if _clean(row, 260)})[:16]
        semantic_key = _digest(subject.casefold(), project_id, *motivation_ids, *inquiry_ids)

        def apply(state: dict[str, Any], now: str) -> dict[str, Any]:
            duplicate = next((row for row in state["plans"] if row.get("semantic_key") == semantic_key and row.get("status") in ACTIVE_STATUSES), None)
            if duplicate:
                return {"status": "duplicate_plan_ignored", "plan_id": duplicate["plan_id"], "created": False}
            open_count = sum(1 for row in state["plans"] if row.get("status") in ACTIVE_STATUSES)
            if open_count >= int(state["resource_limits"]["max_open_plans"]):
                raise ValueError("open prospective-plan budget reached")
            item_id = _clean(plan_id, 120) or f"plan-{uuid.uuid4().hex}"
            if any(row.get("plan_id") == item_id for row in state["plans"]):
                raise ValueError("plan_id already exists")
            state["plans"].append({
                "plan_id": item_id,
                "semantic_key": semantic_key,
                "subject": subject,
                "project_id": _clean(project_id, 120),
                "motivation_ids": motivation_ids,
                "inquiry_ids": inquiry_ids,
                "constraints": constraint_rows,
                "alternatives": normalized,
                "counterfactuals": [],
                "evaluations": [],
                "proposals": [],
                "status": "draft",
                "recommended_alternative_id": "",
                "created_at": now,
                "updated_at": now,
                "history": [{
                    "event": "plan_created",
                    "occurred_at": now,
                    "authored_conclusion": "Possible futures were staged for bounded comparison without authorizing action.",
                }],
                "authority": {"authorizes_action": False, "executes_action": False, "requires_external_approval": True},
            })
            return {"status": "plan_created", "plan_id": item_id, "created": True, "alternative_count": len(normalized)}

        return self._mutate(event_id, apply)

    def compare_plan(self, event_id: str, *, plan_id: str) -> dict[str, Any]:
        plan_id = _clean(plan_id, 120)
        if not plan_id:
            raise ValueError("plan_id is required")

        def apply(state: dict[str, Any], now: str) -> dict[str, Any]:
            plan = next((row for row in state["plans"] if row.get("plan_id") == plan_id), None)
            if not plan:
                raise KeyError("plan not found")
            if plan.get("status") in TERMINAL_STATUSES:
                raise ValueError("terminal plan cannot be evaluated")
            ranked = []
            for alternative in plan["alternatives"]:
                score = _bounded(
                    float(alternative.get("expected_benefit") or 0.0) * 0.45
                    + float(alternative.get("reversibility") or 0.0) * 0.25
                    + float(alternative.get("confidence") or 0.0) * 0.20
                    + (1.0 - float(alternative.get("risk") or 0.0)) * 0.10
                )
                alternative["score"] = score
                ranked.append(alternative)
            ranked.sort(key=lambda row: (-float(row.get("score") or 0.0), str(row.get("alternative_id") or "")))
            for index, alternative in enumerate(ranked, start=1):
                alternative["rank"] = index
            recommended = ranked[0]
            plan["recommended_alternative_id"] = recommended["alternative_id"]
            plan["status"] = "evaluated"
            evaluation = {
                "evaluation_id": f"evaluation-{uuid.uuid4().hex}",
                "occurred_at": now,
                "recommended_alternative_id": recommended["alternative_id"],
                "ranking": [{"alternative_id": row["alternative_id"], "score": row["score"], "rank": row["rank"]} for row in ranked],
                "authored_conclusion": "The current recommendation favors expected benefit, reversibility, confidence, and bounded risk; it is not authorization.",
                "provider_contacted": False,
                "action_authorized": False,
            }
            plan["evaluations"] = (list(plan.get("evaluations") or []) + [evaluation])[-32:]
            plan["updated_at"] = now
            return {"status": "plan_evaluated", "plan_id": plan_id, "recommended_alternative_id": recommended["alternative_id"], "ranking": evaluation["ranking"]}

        return self._mutate(event_id, apply)

    def record_counterfactual(
        self,
        event_id: str,
        *,
        plan_id: str,
        alternative_id: str,
        premise: str,
        expected_outcome: str,
        probability: float,
        downside: float,
        reversibility: float,
        supporting_refs: Iterable[str] = (),
    ) -> dict[str, Any]:
        plan_id = _clean(plan_id, 120); alternative_id = _clean(alternative_id, 120)
        premise = _clean(premise, 500); expected_outcome = _clean(expected_outcome, 500)
        if not all((plan_id, alternative_id, premise, expected_outcome)):
            raise ValueError("plan_id, alternative_id, premise, and expected_outcome are required")
        refs = sorted({_digest(_clean(row, 320)) for row in supporting_refs if _clean(row, 320)})[:16]

        def apply(state: dict[str, Any], now: str) -> dict[str, Any]:
            plan = next((row for row in state["plans"] if row.get("plan_id") == plan_id), None)
            if not plan:
                raise KeyError("plan not found")
            if not any(row.get("alternative_id") == alternative_id for row in plan["alternatives"]):
                raise KeyError("alternative not found")
            if len(plan.get("counterfactuals") or []) >= int(state["resource_limits"]["max_counterfactuals_per_plan"]):
                raise ValueError("counterfactual budget reached")
            semantic_key = _digest(plan_id, alternative_id, premise.casefold(), expected_outcome.casefold())
            duplicate = next((row for row in plan.get("counterfactuals") or [] if row.get("semantic_key") == semantic_key), None)
            if duplicate:
                return {"status": "duplicate_counterfactual_ignored", "counterfactual_id": duplicate["counterfactual_id"]}
            item = {
                "counterfactual_id": f"counterfactual-{uuid.uuid4().hex}",
                "semantic_key": semantic_key,
                "alternative_id": alternative_id,
                "premise": premise,
                "expected_outcome": expected_outcome,
                "probability": _bounded(probability),
                "downside": _bounded(downside),
                "reversibility": _bounded(reversibility),
                "supporting_reference_digests": refs,
                "created_at": now,
                "provider_contacted": False,
                "action_authorized": False,
            }
            plan["counterfactuals"].append(item)
            plan["updated_at"] = now
            return {"status": "counterfactual_recorded", "plan_id": plan_id, "counterfactual_id": item["counterfactual_id"]}

        return self._mutate(event_id, apply)

    def propose_intention(
        self,
        event_id: str,
        *,
        plan_id: str,
        alternative_id: str,
        rationale: str,
        supporting_refs: Iterable[str] = (),
    ) -> dict[str, Any]:
        plan_id = _clean(plan_id, 120); alternative_id = _clean(alternative_id, 120); rationale = _clean(rationale, 600)
        if not all((plan_id, alternative_id, rationale)):
            raise ValueError("plan_id, alternative_id, and rationale are required")
        refs = sorted({_digest(_clean(row, 320)) for row in supporting_refs if _clean(row, 320)})[:16]

        def apply(state: dict[str, Any], now: str) -> dict[str, Any]:
            plan = next((row for row in state["plans"] if row.get("plan_id") == plan_id), None)
            if not plan:
                raise KeyError("plan not found")
            alternative = next((row for row in plan["alternatives"] if row.get("alternative_id") == alternative_id), None)
            if not alternative:
                raise KeyError("alternative not found")
            proposal = {
                "proposal_id": f"proposal-{uuid.uuid4().hex}",
                "alternative_id": alternative_id,
                "rationale": rationale,
                "supporting_reference_digests": refs,
                "created_at": now,
                "cognitive_state": "proposal",
                "authorized": False,
                "executed": False,
                "approval_receipt_id": "",
                "operator_action_required": True,
            }
            plan["proposals"] = (list(plan.get("proposals") or []) + [proposal])[-16:]
            plan["status"] = "proposed"
            plan["updated_at"] = now
            return {"status": "intention_proposed", "plan_id": plan_id, "proposal_id": proposal["proposal_id"], "authorized": False, "executed": False}

        return self._mutate(event_id, apply)

    def set_status(self, event_id: str, *, plan_id: str, status: str, reason_code: str, correction_ref: str = "") -> dict[str, Any]:
        plan_id = _clean(plan_id, 120); status = _clean(status, 40).lower(); reason_code = _clean(reason_code, 160)
        if status not in ACTIVE_STATUSES | TERMINAL_STATUSES:
            raise ValueError("unsupported plan status")
        if not plan_id or not reason_code:
            raise ValueError("plan_id and reason_code are required")
        if status == "corrected" and not _clean(correction_ref, 300):
            raise ValueError("corrected plans require correction_ref")

        def apply(state: dict[str, Any], now: str) -> dict[str, Any]:
            plan = next((row for row in state["plans"] if row.get("plan_id") == plan_id), None)
            if not plan:
                raise KeyError("plan not found")
            prior = str(plan.get("status") or "draft")
            plan["status"] = status
            plan["updated_at"] = now
            plan["history"] = (list(plan.get("history") or []) + [{
                "event": "status_changed", "occurred_at": now, "prior_status": prior, "status": status,
                "reason_code": reason_code, "correction_reference_digest": _digest(correction_ref) if correction_ref else "",
            }])[-64:]
            return {"status": "plan_status_changed", "plan_id": plan_id, "prior_status": prior, "new_status": status}

        return self._mutate(event_id, apply)

    def inspection_summary(self, *, item_limit: int = 10) -> dict[str, Any]:
        state = self._load()
        active = [row for row in state["plans"] if row.get("status") in ACTIVE_STATUSES]
        historical = [row for row in state["plans"] if row.get("status") in TERMINAL_STATUSES]
        active.sort(key=lambda row: (0 if row.get("status") == "proposed" else 1, str(row.get("updated_at") or "")), reverse=False)
        proposal_count = sum(len(row.get("proposals") or []) for row in active)
        return {
            "ok": True,
            "contract_version": PLANNING_CONTRACT_VERSION,
            "active_plan_count": len(active),
            "historical_plan_count": len(historical),
            "proposal_count": proposal_count,
            "active_plans": deepcopy(active[: max(1, int(item_limit))]),
            "resource_limits": deepcopy(state["resource_limits"]),
            "authority_boundary": deepcopy(state["authority_boundary"]),
            "revision": int(state.get("revision") or 0),
            "provider_contacted": False,
            "external_action_executed": False,
            "action_authority_changed": False,
            "hidden_reasoning_exposed": False,
        }


def build_prospective_planning_inspection(runtime_root: str | Path | None = None) -> dict[str, Any]:
    return ProspectivePlanningStore(runtime_root).inspection_summary()
