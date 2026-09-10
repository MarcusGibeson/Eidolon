from __future__ import annotations

"""Durable provider-neutral candidate agenda for bounded internal attention.

The agenda records subjects before attention selection. It is not a generation log,
proposal queue, approval record, or action scheduler. Runtime records may retain a
concise private subject for later bounded reflection, while public inspection only
returns structural metadata and digests.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

try:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
except ImportError:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock

AGENDA_SCHEMA_VERSION = "1"
AGENDA_CONTRACT_VERSION = "v1107.0"
ACTIVE_LIFECYCLES = {"candidate", "deferred"}
INACTIVE_LIFECYCLES = {"completed", "corrected", "retracted", "superseded", "expired"}
ORIGIN_TYPES = {
    "motivation",
    "concern",
    "inquiry",
    "residual_question",
    "reconsideration_schedule",
    "memory",
    "reflection_conclusion",
    "commitment",
    "unfinished_plan",
    "time_change",
    "structural_event",
}


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
    material = "\x1f".join(_clean(part, 3000) for part in parts)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _default_runtime_root() -> Path:
    root = Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data").expanduser().resolve()
    return root / "cognition"


def _default_state() -> dict[str, Any]:
    return {
        "schema_version": AGENDA_SCHEMA_VERSION,
        "contract_version": AGENDA_CONTRACT_VERSION,
        "agenda_items": [],
        "processed_events": [],
        "revision": 0,
        "updated_at": "",
        "controls": {
            "max_items": 512,
            "max_update_history": 64,
            "max_deferral_history": 32,
            "default_resource_budget": 1.0,
        },
        "state_separation": {
            "agenda_candidacy_is_selected_attention": False,
            "selected_attention_is_intention": False,
            "intention_is_proposal": False,
            "proposal_is_authorization": False,
            "authorization_is_execution": False,
        },
        "authority_boundary": {
            "can_authorize_action": False,
            "can_execute_action": False,
            "can_browse_externally": False,
            "can_modify_files": False,
            "can_manage_models": False,
            "can_approve": False,
            "can_promote": False,
            "can_certify": False,
            "operator_authority_unchanged": True,
        },
    }


class AutonomousAttentionAgenda:
    """Transactional agenda ledger with semantic and event-level deduplication."""

    def __init__(
        self,
        runtime_root: str | Path | None = None,
        *,
        clock: Callable[[], str] | None = None,
        event_history_limit: int = 1024,
    ) -> None:
        self.runtime_root = Path(runtime_root).expanduser().resolve() if runtime_root else _default_runtime_root()
        self.path = self.runtime_root / "autonomous_attention_agenda.json"
        self.clock = clock or _utc_now
        self.event_history_limit = max(64, int(event_history_limit))

    def _load(self) -> dict[str, Any]:
        state = load_json_file(self.path, _default_state(), expected_type=dict)
        if state.get("schema_version") != AGENDA_SCHEMA_VERSION:
            return _default_state()
        defaults = _default_state()
        for key, value in defaults.items():
            state.setdefault(key, deepcopy(value))
        for section in ("controls", "authority_boundary"):
            current = state.get(section) if isinstance(state.get(section), dict) else {}
            for key, value in defaults[section].items():
                current.setdefault(key, deepcopy(value))
            state[section] = current
        return state

    def snapshot(self) -> dict[str, Any]:
        return deepcopy(self._load())

    def _mutate(self, event_id: str, mutator: Callable[[dict[str, Any], str], dict[str, Any]]) -> dict[str, Any]:
        event_id = _clean(event_id, 180)
        if not event_id:
            raise ValueError("event_id is required for idempotent agenda mutation")
        with metadata_mutation_lock(self.path, timeout_seconds=5.0):
            state = self._load()
            prior = next((row for row in state["processed_events"] if row.get("event_id") == event_id), None)
            if prior:
                return {
                    "ok": True,
                    "status": "duplicate_event_ignored",
                    "event_id": event_id,
                    "result": deepcopy(prior.get("result") or {}),
                    "revision": int(state.get("revision") or 0),
                    "idempotent": True,
                }
            now = self.clock()
            result = mutator(state, now)
            state["revision"] = int(state.get("revision") or 0) + 1
            state["updated_at"] = now
            receipt = {
                "event_id": event_id,
                "event_digest": _digest(event_id),
                "occurred_at": now,
                "result": deepcopy(result),
                "content_free": True,
            }
            state["processed_events"] = (list(state["processed_events"]) + [receipt])[-self.event_history_limit :]
            write_json_atomic(self.path, state, expected_type=dict, sort_keys=True)
            return {
                "ok": True,
                "status": str(result.get("status") or "updated"),
                "event_id": event_id,
                "result": deepcopy(result),
                "revision": state["revision"],
                "idempotent": False,
            }

    def upsert_candidate(
        self,
        event_id: str,
        *,
        origin_type: str,
        origin_ref: str,
        subject: str,
        subject_key: str = "",
        origin_phase: str = "pre_attention_state",
        source_revision: int = 0,
        worker_generation: int = 0,
        project_id: str = "",
        topic_key: str = "",
        salience: float = 0.5,
        urgency: float = 0.5,
        uncertainty: float = 0.5,
        confidence: float = 0.5,
        eligible: bool = True,
        eligibility_reasons: Iterable[str] = (),
        eligible_after: str = "",
        resource_cost: float = 0.25,
        resource_steps: int = 1,
        lineage_refs: Iterable[str] = (),
        agenda_id: str = "",
    ) -> dict[str, Any]:
        origin_type = _clean(origin_type, 80).lower()
        origin_ref = _clean(origin_ref, 300)
        subject = _clean(subject, 900)
        origin_phase = _clean(origin_phase, 80).lower()
        if origin_type not in ORIGIN_TYPES:
            raise ValueError(f"unsupported agenda origin_type: {origin_type}")
        if not origin_ref or not subject:
            raise ValueError("origin_ref and subject are required")
        if origin_phase in {"post_generation_justification", "dialogue_already_generated"}:
            raise ValueError("agenda candidates cannot be created to rationalize dialogue already generated")
        stable_subject_key = _clean(subject_key, 300) or _digest(subject.casefold())
        semantic_key = _digest(origin_type, origin_ref, stable_subject_key, _clean(project_id, 120))
        reasons = sorted({_clean(row, 120) for row in eligibility_reasons if _clean(row, 120)})[:16]
        lineage_digests = sorted({_digest(_clean(row, 400)) for row in lineage_refs if _clean(row, 400)})[:24]
        requested_id = _clean(agenda_id, 140)
        source_revision = max(0, int(source_revision or 0))
        worker_generation = max(0, int(worker_generation or 0))

        def apply(state: dict[str, Any], now: str) -> dict[str, Any]:
            item = next((row for row in state["agenda_items"] if row.get("semantic_key") == semantic_key), None)
            if item:
                prior_revision = int(item.get("source_revision") or 0)
                prior_generation = int(item.get("worker_generation") or 0)
                if source_revision < prior_revision or (source_revision == prior_revision and worker_generation < prior_generation):
                    return {
                        "status": "stale_candidate_update_ignored",
                        "agenda_id": item["agenda_id"],
                        "created": False,
                        "active_influence": bool(item.get("active_influence")),
                    }
                new_subject_digest = _digest(subject)
                new_eligibility = {
                    "eligible": bool(eligible),
                    "reason_codes": reasons,
                    "eligible_after": _clean(eligible_after, 80),
                }
                new_resource_cost = {
                    "normalized_cost": _bounded(resource_cost),
                    "reflection_steps": max(0, min(8, int(resource_steps or 0))),
                    "provider_calls": 0,
                    "external_actions": 0,
                }
                new_scope = {
                    "project_id": _clean(project_id, 120),
                    "topic_key": _clean(topic_key, 160),
                    "provider_bound": False,
                }
                prior = {
                    "salience": item.get("salience"),
                    "urgency": item.get("urgency"),
                    "uncertainty": item.get("uncertainty"),
                    "confidence": item.get("confidence"),
                    "eligible": item.get("eligibility", {}).get("eligible"),
                    "lifecycle_state": item.get("lifecycle_state"),
                }
                meaningful_change = any((
                    item.get("subject_digest") != new_subject_digest,
                    item.get("salience") != _bounded(salience),
                    item.get("urgency") != _bounded(urgency),
                    item.get("uncertainty") != _bounded(uncertainty),
                    item.get("confidence") != _bounded(confidence),
                    item.get("eligibility") != new_eligibility,
                    item.get("resource_cost_estimate") != new_resource_cost,
                    item.get("scope") != new_scope,
                    list((item.get("origin") or {}).get("lineage_digests") or []) != lineage_digests,
                    item.get("lifecycle_state") != "candidate",
                    item.get("active_influence") is not True,
                    source_revision > prior_revision,
                ))
                item.update({
                    "private_subject": subject,
                    "subject_digest": new_subject_digest,
                    "salience": _bounded(salience),
                    "urgency": _bounded(urgency),
                    "uncertainty": _bounded(uncertainty),
                    "confidence": _bounded(confidence),
                    "source_revision": source_revision,
                    "worker_generation": worker_generation,
                    "updated_at": now,
                    "active_influence": True,
                    "lifecycle_state": "candidate",
                    "scope": new_scope,
                })
                if meaningful_change:
                    item["last_meaningful_change_at"] = now
                item["eligibility"] = new_eligibility
                item["resource_cost_estimate"] = new_resource_cost
                item["origin"]["lineage_digests"] = lineage_digests
                history = list(item.get("update_history") or [])
                history.append({
                    "event": "candidate_updated",
                    "occurred_at": now,
                    "prior": prior,
                    "new": {
                        "salience": item["salience"],
                        "urgency": item["urgency"],
                        "uncertainty": item["uncertainty"],
                        "confidence": item["confidence"],
                        "eligible": bool(eligible),
                        "lifecycle_state": "candidate",
                    },
                    "source_revision": source_revision,
                    "worker_generation": worker_generation,
                    "meaningful_state_change": meaningful_change,
                    "content_free": True,
                })
                item["update_history"] = history[-int(state["controls"]["max_update_history"]) :]
                return {"status": "agenda_candidate_updated", "agenda_id": item["agenda_id"], "created": False, "active_influence": True, "meaningful_state_change": meaningful_change}

            if len(state["agenda_items"]) >= int(state["controls"]["max_items"]):
                inactive = [row for row in state["agenda_items"] if not row.get("active_influence")]
                inactive.sort(key=lambda row: (str(row.get("updated_at") or ""), str(row.get("agenda_id") or "")))
                if inactive:
                    state["agenda_items"].remove(inactive[0])
                else:
                    raise ValueError("agenda item budget reached")
            item_id = requested_id or f"agenda-{semantic_key[:28]}"
            if any(row.get("agenda_id") == item_id for row in state["agenda_items"]):
                raise ValueError("agenda_id already exists with different semantic content")
            item = {
                "agenda_id": item_id,
                "semantic_key": semantic_key,
                "private_subject": subject,
                "subject_digest": _digest(subject),
                "origin": {
                    "type": origin_type,
                    "reference_digest": _digest(origin_ref),
                    "phase": origin_phase,
                    "created_before_attention": True,
                    "lineage_digests": lineage_digests,
                },
                "scope": {"project_id": _clean(project_id, 120), "topic_key": _clean(topic_key, 160), "provider_bound": False},
                "salience": _bounded(salience),
                "urgency": _bounded(urgency),
                "uncertainty": _bounded(uncertainty),
                "confidence": _bounded(confidence),
                "eligibility": {"eligible": bool(eligible), "reason_codes": reasons, "eligible_after": _clean(eligible_after, 80)},
                "deferral_history": [],
                "resource_cost_estimate": {
                    "normalized_cost": _bounded(resource_cost),
                    "reflection_steps": max(0, min(8, int(resource_steps or 0))),
                    "provider_calls": 0,
                    "external_actions": 0,
                },
                "source_revision": source_revision,
                "worker_generation": worker_generation,
                "lifecycle_state": "candidate",
                "active_influence": True,
                "attention_count": 0,
                "last_selected_at": "",
                "last_selected_source_revision": -1,
                "last_meaningful_change_at": now,
                "created_at": now,
                "updated_at": now,
                "update_history": [{
                    "event": "candidate_created",
                    "occurred_at": now,
                    "source_revision": source_revision,
                    "worker_generation": worker_generation,
                    "content_free": True,
                }],
                "state_separation": {
                    "state": "agenda_candidacy",
                    "is_selected_attention": False,
                    "is_intention": False,
                    "is_proposal": False,
                    "is_authorized_action": False,
                    "is_completed_action": False,
                },
                "authority": {"authorizes_action": False, "executes_action": False, "approval_id": "", "authorization_receipt": ""},
            }
            state["agenda_items"].append(item)
            return {"status": "agenda_candidate_created", "agenda_id": item_id, "created": True, "active_influence": True}

        return self._mutate(event_id, apply)

    def defer_candidate(self, event_id: str, agenda_id: str, *, reason_code: str, eligible_after: str = "") -> dict[str, Any]:
        agenda_id = _clean(agenda_id, 140)
        reason_code = _clean(reason_code, 120)
        if not agenda_id or not reason_code:
            raise ValueError("agenda_id and reason_code are required")

        def apply(state: dict[str, Any], now: str) -> dict[str, Any]:
            item = next((row for row in state["agenda_items"] if row.get("agenda_id") == agenda_id), None)
            if not item:
                raise KeyError("agenda item not found")
            item["lifecycle_state"] = "deferred"
            item["eligibility"] = {"eligible": False, "reason_codes": [reason_code], "eligible_after": _clean(eligible_after, 80)}
            item["updated_at"] = now
            history = list(item.get("deferral_history") or [])
            history.append({"occurred_at": now, "reason_code": reason_code, "eligible_after": _clean(eligible_after, 80), "content_free": True})
            item["deferral_history"] = history[-int(state["controls"]["max_deferral_history"]) :]
            return {"status": "agenda_candidate_deferred", "agenda_id": agenda_id, "active_influence": True}

        return self._mutate(event_id, apply)

    def retire_candidate(
        self,
        event_id: str,
        agenda_id: str,
        *,
        outcome: str,
        reason_code: str,
        replacement_ref: str = "",
    ) -> dict[str, Any]:
        outcome = _clean(outcome, 80).lower()
        if outcome not in INACTIVE_LIFECYCLES:
            raise ValueError("unsupported retirement outcome")
        agenda_id = _clean(agenda_id, 140)
        reason_code = _clean(reason_code, 120)

        def apply(state: dict[str, Any], now: str) -> dict[str, Any]:
            item = next((row for row in state["agenda_items"] if row.get("agenda_id") == agenda_id), None)
            if not item:
                raise KeyError("agenda item not found")
            prior = item.get("lifecycle_state")
            item["lifecycle_state"] = outcome
            item["active_influence"] = False
            item["eligibility"] = {"eligible": False, "reason_codes": [reason_code or outcome], "eligible_after": ""}
            item["salience"] = 0.0
            item["urgency"] = 0.0
            item["updated_at"] = now
            history = list(item.get("update_history") or [])
            history.append({
                "event": "candidate_retired",
                "occurred_at": now,
                "prior_state": prior,
                "new_state": outcome,
                "reason_code": reason_code or outcome,
                "replacement_ref_digest": _digest(replacement_ref) if _clean(replacement_ref, 300) else "",
                "content_free": True,
            })
            item["update_history"] = history[-int(state["controls"]["max_update_history"]) :]
            return {"status": f"agenda_candidate_{outcome}", "agenda_id": agenda_id, "active_influence": False}

        return self._mutate(event_id, apply)

    def record_selection(
        self,
        event_id: str,
        agenda_id: str,
        *,
        selection_receipt_id: str,
        meaningful_state_change: bool = False,
    ) -> dict[str, Any]:
        agenda_id = _clean(agenda_id, 140)
        selection_receipt_id = _clean(selection_receipt_id, 180)

        def apply(state: dict[str, Any], now: str) -> dict[str, Any]:
            item = next((row for row in state["agenda_items"] if row.get("agenda_id") == agenda_id), None)
            if not item or not item.get("active_influence"):
                raise KeyError("active agenda item not found")
            item["attention_count"] = int(item.get("attention_count") or 0) + 1
            item["last_selected_at"] = now
            item["last_selected_source_revision"] = int(item.get("source_revision") or 0)
            if meaningful_state_change:
                item["last_meaningful_change_at"] = now
            item["updated_at"] = now
            history = list(item.get("update_history") or [])
            history.append({
                "event": "selected_attention_recorded",
                "occurred_at": now,
                "selection_receipt_digest": _digest(selection_receipt_id),
                "meaningful_state_change": bool(meaningful_state_change),
                "content_free": True,
            })
            item["update_history"] = history[-int(state["controls"]["max_update_history"]) :]
            return {"status": "selected_attention_recorded", "agenda_id": agenda_id, "attention_count": item["attention_count"]}

        return self._mutate(event_id, apply)

    def active_candidates(self) -> list[dict[str, Any]]:
        rows = [
            deepcopy(row)
            for row in self._load()["agenda_items"]
            if row.get("active_influence") and row.get("lifecycle_state") in ACTIVE_LIFECYCLES
        ]
        rows.sort(key=lambda row: (-float(row.get("urgency") or 0), -float(row.get("salience") or 0), str(row.get("agenda_id") or "")))
        return rows

    def sync_from_established_state(
        self,
        event_id: str,
        *,
        memory_records: Iterable[Mapping[str, Any]] = (),
        structural_events: Iterable[Mapping[str, Any]] = (),
    ) -> dict[str, Any]:
        """Gather bounded candidates from established local state without provider use."""
        gathered: list[dict[str, Any]] = []
        try:
            from persistent_motivation import MotivationStore
            motivations = MotivationStore(self.runtime_root).snapshot().get("motivations") or []
            for row in motivations:
                if row.get("lifecycle_state") != "active":
                    continue
                kind = str(row.get("kind") or "motivation")
                origin = "concern" if kind == "concern" else ("commitment" if row.get("cognitive_state") == "commitment" else "motivation")
                gathered.append({
                    "origin_type": origin,
                    "origin_ref": str(row.get("motivation_id") or row.get("semantic_key") or "motivation"),
                    "subject": str(row.get("summary") or kind),
                    "subject_key": str(row.get("semantic_key") or row.get("motivation_id") or ""),
                    "project_id": str((row.get("scope") or {}).get("project_id") or ""),
                    "topic_key": kind,
                    "salience": max(float(row.get("urgency") or 0), abs(float(row.get("valence") or 0))),
                    "urgency": float(row.get("urgency") or 0),
                    "uncertainty": 1.0 - float(row.get("confidence") or 0),
                    "confidence": float(row.get("confidence") or 0),
                    "source_revision": len(row.get("update_history") or []),
                    "lineage_refs": [str((row.get("origin") or {}).get("reference") or "")],
                })
        except (ImportError, OSError, ValueError, TypeError):
            pass
        residual_links_by_child: dict[str, dict[str, Any]] = {}
        try:
            from inquiry_residual_lineage import InquiryResidualLineage
            residual_links = InquiryResidualLineage(self.runtime_root).snapshot().get("links") or []
            residual_links_by_child = {
                str(row.get("child_inquiry_id") or ""): row
                for row in residual_links
                if row.get("active") is True and str(row.get("child_inquiry_id") or "")
            }
        except (ImportError, OSError, ValueError, TypeError):
            residual_links_by_child = {}
        try:
            from self_directed_inquiry import InquiryWorkspace
            inquiries = InquiryWorkspace(self.runtime_root).snapshot().get("inquiries") or []
            for row in inquiries:
                if row.get("status") != "active":
                    continue
                inquiry_id = str(row.get("inquiry_id") or "inquiry")
                residual_link = residual_links_by_child.get(inquiry_id)
                gathered.append({
                    "origin_type": "residual_question" if residual_link else "inquiry",
                    "origin_ref": str((residual_link or {}).get("link_id") or inquiry_id),
                    "subject": str(row.get("question") or (residual_link or {}).get("residual_question") or "Active bounded inquiry"),
                    "subject_key": str(row.get("semantic_key") or inquiry_id),
                    "project_id": str(row.get("project_id") or ""),
                    "topic_key": "residual_question" if residual_link else "inquiry",
                    "salience": float(row.get("priority") or 0.5),
                    "urgency": float(row.get("priority") or 0.5),
                    "uncertainty": float(row.get("uncertainty") or 0.5),
                    "confidence": 1.0 - float(row.get("uncertainty") or 0.5),
                    "source_revision": int(row.get("step_count") or 0) + len((residual_link or {}).get("history") or []),
                    "lineage_refs": [str(row.get("motivation_id") or ""), str((residual_link or {}).get("parent_inquiry_id") or "")],
                })
        except (ImportError, OSError, ValueError, TypeError):
            pass
        try:
            from prospective_planning import ProspectivePlanningStore
            plans = ProspectivePlanningStore(self.runtime_root).snapshot().get("plans") or []
            for row in plans:
                status = str(row.get("status") or "")
                if status not in {"draft", "evaluated", "proposed", "paused"}:
                    continue
                has_recommendation = bool(row.get("recommended_alternative_id"))
                gathered.append({
                    "origin_type": "unfinished_plan",
                    "origin_ref": str(row.get("plan_id") or row.get("semantic_key") or "plan"),
                    "subject": str(row.get("subject") or "Unfinished bounded plan"),
                    "subject_key": str(row.get("semantic_key") or row.get("plan_id") or ""),
                    "project_id": str(row.get("project_id") or ""),
                    "topic_key": "planning",
                    "salience": 0.72 if status == "proposed" else (0.58 if status == "evaluated" else 0.46),
                    "urgency": 0.62 if status == "proposed" else 0.42,
                    "uncertainty": 0.42 if has_recommendation else 0.68,
                    "confidence": 0.58 if has_recommendation else 0.32,
                    "eligible": status != "paused",
                    "eligibility_reasons": ["plan_paused"] if status == "paused" else [],
                    "source_revision": len(row.get("history") or []) + len(row.get("evaluations") or []) + len(row.get("proposals") or []),
                    "lineage_refs": list(row.get("motivation_ids") or []) + list(row.get("inquiry_ids") or []),
                })
        except (ImportError, OSError, ValueError, TypeError):
            pass
        try:
            from knowledge_reconsideration_scheduling import KnowledgeReconsiderationScheduler
            schedules = KnowledgeReconsiderationScheduler(self.runtime_root).snapshot().get("schedules") or []
            for row in schedules:
                if str(row.get("status") or "scheduled") not in {"scheduled", "due", "pending"}:
                    continue
                target_type = str(row.get("target_type") or "knowledge")
                gathered.append({
                    "origin_type": "reconsideration_schedule",
                    "origin_ref": str(row.get("schedule_id") or row.get("semantic_key") or "reconsideration"),
                    "subject": f"Reconsider {target_type} {str(row.get('target_id') or '')}".strip(),
                    "subject_key": str(row.get("semantic_key") or row.get("schedule_id") or ""),
                    "topic_key": target_type,
                    "salience": float(row.get("pressure") or row.get("priority") or 0.55),
                    "urgency": float(row.get("pressure") or row.get("priority") or 0.55),
                    "uncertainty": float(row.get("uncertainty") or 0.6),
                    "confidence": 1.0 - float(row.get("uncertainty") or 0.6),
                    "source_revision": len(row.get("history") or []),
                    "eligible_after": str(row.get("due_at") or ""),
                    "lineage_refs": [str(row.get("target_id") or "")],
                })
        except (ImportError, OSError, ValueError, TypeError):
            pass
        try:
            from endogenous_cognitive_cycle import EndogenousCognitiveCycle
            reflections = EndogenousCognitiveCycle(self.runtime_root).snapshot().get("recent_reflections") or []
            for index, row in enumerate(reflections[-16:]):
                conclusion = str(row.get("conclusion") or row.get("reflection_conclusion") or "")
                if not conclusion:
                    continue
                gathered.append({
                    "origin_type": "reflection_conclusion",
                    "origin_ref": str(row.get("reflection_id") or row.get("cycle_id") or f"reflection-{index}"),
                    "subject": conclusion,
                    "subject_key": str(row.get("motivation_id") or row.get("selected_motivation_id") or _digest(conclusion)),
                    "topic_key": str(row.get("kind") or row.get("selected_kind") or "reflection"),
                    "salience": float(row.get("salience") or 0.4),
                    "urgency": float(row.get("salience") or 0.3),
                    "uncertainty": 0.5,
                    "confidence": 0.5,
                    "source_revision": index + 1,
                })
        except (ImportError, OSError, ValueError, TypeError):
            pass
        for index, row in enumerate(memory_records):
            subject = _clean(row.get("subject") or row.get("summary"), 900)
            ref = _clean(row.get("memory_id") or row.get("reference") or f"memory-{index}", 300)
            if subject:
                gathered.append({
                    "origin_type": "memory",
                    "origin_ref": ref,
                    "subject": subject,
                    "subject_key": _clean(row.get("semantic_key"), 300) or _digest(subject),
                    "project_id": _clean(row.get("project_id"), 120),
                    "topic_key": _clean(row.get("topic_key"), 160) or "memory",
                    "salience": row.get("salience", 0.4),
                    "urgency": row.get("urgency", 0.2),
                    "uncertainty": row.get("uncertainty", 0.4),
                    "confidence": row.get("confidence", 0.6),
                    "source_revision": int(row.get("revision") or 0),
                })
        for index, row in enumerate(structural_events):
            subject = _clean(row.get("subject") or row.get("summary"), 900)
            ref = _clean(row.get("event_id") or row.get("reference") or f"structural-{index}", 300)
            event_type = _clean(row.get("event_type") or "structural_event", 80)
            origin_type = "time_change" if event_type == "time_change" else "structural_event"
            if subject:
                gathered.append({
                    "origin_type": origin_type,
                    "origin_ref": ref,
                    "subject": subject,
                    "subject_key": _clean(row.get("semantic_key"), 300) or _digest(event_type, subject),
                    "project_id": _clean(row.get("project_id"), 120),
                    "topic_key": _clean(row.get("topic_key"), 160) or event_type,
                    "salience": row.get("salience", 0.5),
                    "urgency": row.get("urgency", 0.5),
                    "uncertainty": row.get("uncertainty", 0.3),
                    "confidence": row.get("confidence", 0.7),
                    "source_revision": int(row.get("revision") or 0),
                })

        results: list[dict[str, Any]] = []
        for index, candidate in enumerate(gathered):
            child_event = f"{event_id}:candidate:{index}:{_digest(candidate.get('origin_type'), candidate.get('origin_ref'), candidate.get('subject_key'))[:16]}"
            results.append(self.upsert_candidate(child_event, **candidate))
        return {
            "ok": True,
            "status": "agenda_candidates_gathered",
            "gathered_count": len(gathered),
            "created_count": sum(1 for row in results if (row.get("result") or {}).get("created") is True),
            "updated_or_existing_count": sum(1 for row in results if (row.get("result") or {}).get("created") is not True),
            "provider_contacted": False,
            "external_browsing_performed": False,
            "action_authority_changed": False,
        }

    def inspection_summary(self, *, item_limit: int = 24) -> dict[str, Any]:
        state = self._load()
        active = [row for row in state["agenda_items"] if row.get("active_influence")]
        inactive = [row for row in state["agenda_items"] if not row.get("active_influence")]
        eligible = [row for row in active if (row.get("eligibility") or {}).get("eligible")]
        origin_counts: dict[str, int] = {}
        for row in active:
            origin = str((row.get("origin") or {}).get("type") or "unknown")
            origin_counts[origin] = origin_counts.get(origin, 0) + 1
        rows = sorted(active, key=lambda row: (-float(row.get("urgency") or 0), -float(row.get("salience") or 0), str(row.get("agenda_id") or "")))[: max(0, int(item_limit))]
        public_rows = [{
            "agenda_id": row.get("agenda_id"),
            "subject_digest": row.get("subject_digest"),
            "origin_type": (row.get("origin") or {}).get("type"),
            "project_id": (row.get("scope") or {}).get("project_id"),
            "topic_key": (row.get("scope") or {}).get("topic_key"),
            "salience": row.get("salience"),
            "urgency": row.get("urgency"),
            "uncertainty": row.get("uncertainty"),
            "confidence": row.get("confidence"),
            "eligible": (row.get("eligibility") or {}).get("eligible"),
            "eligibility_reason_codes": list((row.get("eligibility") or {}).get("reason_codes") or []),
            "deferral_count": len(row.get("deferral_history") or []),
            "resource_cost_estimate": deepcopy(row.get("resource_cost_estimate") or {}),
            "attention_count": int(row.get("attention_count") or 0),
            "last_selected_at": row.get("last_selected_at"),
            "lifecycle_state": row.get("lifecycle_state"),
            "active_influence": bool(row.get("active_influence")),
            "private_subject_exposed": False,
        } for row in rows]
        return {
            "ok": True,
            "contract_version": AGENDA_CONTRACT_VERSION,
            "revision": int(state.get("revision") or 0),
            "updated_at": state.get("updated_at") or "",
            "agenda_item_count": len(state["agenda_items"]),
            "active_candidate_count": len(active),
            "eligible_candidate_count": len(eligible),
            "historical_inactive_count": len(inactive),
            "origin_counts": origin_counts,
            "candidates": public_rows,
            "state_separation": deepcopy(state["state_separation"]),
            "authority_boundary": deepcopy(state["authority_boundary"]),
            "privacy": {
                "raw_prompts_exposed": False,
                "private_conversations_exposed": False,
                "provider_payloads_exposed": False,
                "evidence_text_exposed": False,
                "hidden_reasoning_exposed": False,
                "private_subjects_exposed": False,
            },
            "provider_contacted": False,
            "external_browsing_performed": False,
            "runtime_mutated": False,
            "action_authority_changed": False,
        }


def build_autonomous_attention_agenda_inspection(runtime_root: str | Path | None = None) -> dict[str, Any]:
    return AutonomousAttentionAgenda(runtime_root).inspection_summary()
