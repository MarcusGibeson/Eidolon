from __future__ import annotations

"""Deterministic bounded arbitration for durable internal attention candidates.

One arbitration may select one agenda subject or deliberately select none. The
receipt is structural and content-free. Selection is not intention, proposal,
authorization, execution, communication, browsing, provider use, or a generation
loop.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import time
from typing import Any, Callable, Iterable, Mapping

try:
    from autonomous_attention_agenda import AutonomousAttentionAgenda
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
except ImportError:
    from autonomous_attention_agenda import AutonomousAttentionAgenda
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock

ARBITRATION_SCHEMA_VERSION = "1"
ARBITRATION_CONTRACT_VERSION = "v1107.1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _epoch_now() -> float:
    return time.time()


def _clean(value: Any, limit: int = 500) -> str:
    return " ".join(str(value or "").split())[: max(0, int(limit))]


def _digest(*parts: Any) -> str:
    text = "\x1f".join(_clean(part, 3000) for part in parts)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _default_runtime_root() -> Path:
    root = Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data").expanduser().resolve()
    return root / "cognition"


def _parse_epoch(value: Any) -> float:
    text = _clean(value, 100)
    if not text:
        return 0.0
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _default_state() -> dict[str, Any]:
    return {
        "schema_version": ARBITRATION_SCHEMA_VERSION,
        "contract_version": ARBITRATION_CONTRACT_VERSION,
        "arbitration_receipts": [],
        "processed_events": [],
        "worker_generation": 1,
        "revision": 0,
        "updated_at": "",
        "controls": {
            "minimum_score": 0.24,
            "selection_cooldown_seconds": 900,
            "max_receipts": 512,
            "max_candidates_per_arbitration": 128,
            "max_normalized_resource_cost": 0.75,
            "max_reflection_steps": 1,
            "fairness_weight": 0.18,
            "continuity_weight": 0.14,
            "repetition_penalty_per_attention": 0.07,
            "starvation_horizon_hours": 24,
            "meaningful_state_change_bypasses_cooldown": True,
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


class MotivationAgendaArbitrator:
    def __init__(
        self,
        runtime_root: str | Path | None = None,
        *,
        agenda: AutonomousAttentionAgenda | None = None,
        clock: Callable[[], str] | None = None,
        epoch_clock: Callable[[], float] | None = None,
    ) -> None:
        self.runtime_root = Path(runtime_root).expanduser().resolve() if runtime_root else _default_runtime_root()
        self.path = self.runtime_root / "motivation_agenda_arbitration.json"
        self.agenda = agenda or AutonomousAttentionAgenda(self.runtime_root)
        self.clock = clock or _utc_now
        self.epoch_clock = epoch_clock or _epoch_now

    def _load(self) -> dict[str, Any]:
        state = load_json_file(self.path, _default_state(), expected_type=dict)
        if state.get("schema_version") != ARBITRATION_SCHEMA_VERSION:
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

    def arbitrate(
        self,
        event_id: str,
        *,
        arbitration_key: str = "",
        trigger_type: str = "bounded_cadence",
        worker_id: str = "local-worker",
        worker_generation: int = 1,
        gather_candidates: bool = True,
        provider_available: bool | None = None,
        resource_budget: float | None = None,
        allowed_topic_keys: Iterable[str] = (),
        blocked_topic_keys: Iterable[str] = (),
        quiet: bool | None = None,
        paused: bool | None = None,
        sleeping: bool | None = None,
        cooldown_seconds: int | None = None,
        minimum_score: float | None = None,
    ) -> dict[str, Any]:
        event_id = _clean(event_id, 180)
        if not event_id:
            raise ValueError("event_id is required")
        arbitration_key = _clean(arbitration_key, 220) or event_id
        trigger_type = _clean(trigger_type, 100)
        worker_id = _clean(worker_id, 180)
        worker_generation = max(0, int(worker_generation or 0))
        if gather_candidates:
            self.agenda.sync_from_established_state(f"{event_id}:gather")

        with metadata_mutation_lock(self.path, timeout_seconds=5.0):
            state = self._load()
            prior_event = next((row for row in state["processed_events"] if row.get("event_id") == event_id), None)
            if prior_event:
                return {
                    "ok": True,
                    "status": "duplicate_event_ignored",
                    "event_id": event_id,
                    "result": deepcopy(prior_event.get("result") or {}),
                    "idempotent": True,
                }
            selection_key = _digest(arbitration_key)
            prior_key = next((row for row in state["arbitration_receipts"] if row.get("selection_key") == selection_key), None)
            if prior_key:
                result = {
                    "status": "duplicate_arbitration_ignored",
                    "receipt_id": prior_key.get("receipt_id"),
                    "selected_agenda_id": prior_key.get("selected_agenda_id") or "",
                    "deliberate_no_selection": prior_key.get("selected_agenda_id") in {None, ""},
                    "reflection_handoff": deepcopy(prior_key.get("reflection_handoff") or {}),
                }
                self._record_processed_event(state, event_id, result, self.clock())
                write_json_atomic(self.path, state, expected_type=dict, sort_keys=True)
                return {"ok": True, "status": result["status"], "event_id": event_id, "result": result, "idempotent": True}
            current_generation = int(state.get("worker_generation") or 1)
            if worker_generation < current_generation:
                result = {
                    "status": "stale_worker_no_selection",
                    "receipt_id": "",
                    "selected_agenda_id": "",
                    "deliberate_no_selection": True,
                    "reflection_handoff": {},
                }
                self._record_processed_event(state, event_id, result, self.clock())
                write_json_atomic(self.path, state, expected_type=dict, sort_keys=True)
                return {"ok": True, "status": result["status"], "event_id": event_id, "result": result, "idempotent": False}
            if worker_generation > current_generation:
                state["worker_generation"] = worker_generation

            now = self.clock()
            epoch = float(self.epoch_clock())
            boundaries = self._resolve_boundaries(
                state,
                epoch=epoch,
                quiet=quiet,
                paused=paused,
                sleeping=sleeping,
                resource_budget=resource_budget,
                allowed_topic_keys=allowed_topic_keys,
                blocked_topic_keys=blocked_topic_keys,
                cooldown_seconds=cooldown_seconds,
                minimum_score=minimum_score,
            )
            candidates = self.agenda.active_candidates()[: int(state["controls"]["max_candidates_per_arbitration"])]
            ranked, filtered_counts = self._rank_candidates(candidates, boundaries=boundaries, epoch=epoch)
            selected = ranked[0] if ranked and ranked[0][0] >= boundaries["minimum_score"] and not boundaries["global_blocks"] else None
            receipt_id = f"agenda-selection-{selection_key[:24]}"
            if selected:
                score, item, factors = selected
                handoff = self._reflection_handoff(item, receipt_id)
                agenda_result = self.agenda.record_selection(
                    f"agenda-selection:{selection_key}",
                    str(item.get("agenda_id") or ""),
                    selection_receipt_id=receipt_id,
                    meaningful_state_change=factors["meaningful_state_change"],
                )
                selected_id = str(item.get("agenda_id") or "")
                status = "attention_subject_selected"
                no_selection_reasons: list[str] = []
            else:
                score = 0.0
                handoff = {}
                agenda_result = {}
                selected_id = ""
                status = "deliberate_no_selection"
                no_selection_reasons = list(boundaries["global_blocks"])
                if not no_selection_reasons:
                    if not candidates:
                        no_selection_reasons.append("no_active_candidates")
                    elif not ranked:
                        no_selection_reasons.append("no_eligible_candidates")
                    else:
                        no_selection_reasons.append("no_candidate_exceeded_minimum_score")

            receipt = {
                "receipt_id": receipt_id,
                "selection_key": selection_key,
                "event_digest": _digest(event_id),
                "trigger_type": trigger_type,
                "occurred_at": now,
                "occurred_epoch": round(epoch, 3),
                "worker_digest": _digest(worker_id),
                "worker_generation": worker_generation,
                "status": status,
                "candidate_count": len(candidates),
                "eligible_ranked_count": len(ranked),
                "filtered_counts": filtered_counts,
                "selected_agenda_id": selected_id,
                "selected_subject_digest": str(selected[1].get("subject_digest") or "") if selected else "",
                "selected_origin_type": str((selected[1].get("origin") or {}).get("type") or "") if selected else "",
                "selected_score": round(float(score), 4),
                "deliberate_no_selection": selected is None,
                "no_selection_reason_codes": no_selection_reasons,
                "boundary_state": {
                    "quiet": boundaries["quiet"],
                    "paused": boundaries["paused"],
                    "sleeping": boundaries["sleeping"],
                    "resource_budget": boundaries["resource_budget"],
                    "cooldown_seconds": boundaries["cooldown_seconds"],
                    "allowed_topic_count": len(boundaries["allowed_topics"]),
                    "blocked_topic_count": len(boundaries["blocked_topics"]),
                },
                "reflection_handoff": handoff,
                "agenda_selection_recorded": bool((agenda_result.get("result") or {}).get("status") == "selected_attention_recorded") if selected else False,
                "provider_available": provider_available,
                "provider_contacted": False,
                "provider_call_count": 0,
                "generation_loop_created": False,
                "external_browsing_performed": False,
                "command_executed": False,
                "file_modified": False,
                "model_managed": False,
                "approval_created": False,
                "action_authorized": False,
                "action_executed": False,
                "release_promoted": False,
                "release_certified": False,
                "raw_prompt_stored": False,
                "private_conversation_stored": False,
                "evidence_text_stored": False,
                "hidden_reasoning_stored": False,
            }
            state["arbitration_receipts"] = (list(state["arbitration_receipts"]) + [receipt])[-int(state["controls"]["max_receipts"]) :]
            result = {
                "status": status,
                "receipt_id": receipt_id,
                "selected_agenda_id": selected_id,
                "deliberate_no_selection": selected is None,
                "no_selection_reason_codes": no_selection_reasons,
                "reflection_handoff": deepcopy(handoff),
                "selected_score": round(float(score), 4),
            }
            self._record_processed_event(state, event_id, result, now)
            state["revision"] = int(state.get("revision") or 0) + 1
            state["updated_at"] = now
            write_json_atomic(self.path, state, expected_type=dict, sort_keys=True)
            return {"ok": True, "status": status, "event_id": event_id, "result": result, "idempotent": False}

    def _resolve_boundaries(
        self,
        state: Mapping[str, Any],
        *,
        epoch: float,
        quiet: bool | None,
        paused: bool | None,
        sleeping: bool | None,
        resource_budget: float | None,
        allowed_topic_keys: Iterable[str],
        blocked_topic_keys: Iterable[str],
        cooldown_seconds: int | None,
        minimum_score: float | None,
    ) -> dict[str, Any]:
        cycle_mode = "running"
        quiet_active = False
        if paused is None or sleeping is None:
            try:
                from endogenous_cognitive_cycle import EndogenousCognitiveCycle
                cycle_mode = str((EndogenousCognitiveCycle(self.runtime_root).snapshot().get("controls") or {}).get("mode") or "running")
            except (ImportError, OSError, ValueError, TypeError):
                cycle_mode = "running"
        if quiet is None:
            try:
                from proactive_communication import ProactiveCommunicationStore
                preferences = ProactiveCommunicationStore(self.runtime_root).snapshot().get("preferences") or {}
                quiet_active = preferences.get("quiet_indefinite") is True or float(preferences.get("quiet_until_epoch") or 0) > epoch
            except (ImportError, OSError, ValueError, TypeError):
                quiet_active = False
        else:
            quiet_active = bool(quiet)
        paused_active = bool(paused) if paused is not None else cycle_mode == "paused"
        sleeping_active = bool(sleeping) if sleeping is not None else cycle_mode == "sleeping"
        controls = state.get("controls") or {}
        budget = float(resource_budget if resource_budget is not None else controls.get("max_normalized_resource_cost") or 0.75)
        allowed = {_clean(row, 160) for row in allowed_topic_keys if _clean(row, 160)}
        blocked = {_clean(row, 160) for row in blocked_topic_keys if _clean(row, 160)}
        global_blocks = []
        if quiet_active: global_blocks.append("quiet_boundary_active")
        if paused_active: global_blocks.append("attention_paused")
        if sleeping_active: global_blocks.append("attention_sleeping")
        if budget <= 0: global_blocks.append("resource_budget_exhausted")
        return {
            "quiet": quiet_active,
            "paused": paused_active,
            "sleeping": sleeping_active,
            "resource_budget": max(0.0, min(1.0, budget)),
            "allowed_topics": allowed,
            "blocked_topics": blocked,
            "cooldown_seconds": max(0, int(cooldown_seconds if cooldown_seconds is not None else controls.get("selection_cooldown_seconds") or 900)),
            "minimum_score": max(0.0, min(1.0, float(minimum_score if minimum_score is not None else controls.get("minimum_score") or 0.24))),
            "global_blocks": global_blocks,
            "fairness_weight": float(controls.get("fairness_weight") or 0.18),
            "continuity_weight": float(controls.get("continuity_weight") or 0.14),
            "repetition_penalty_per_attention": float(controls.get("repetition_penalty_per_attention") or 0.07),
            "starvation_horizon_hours": max(1.0, float(controls.get("starvation_horizon_hours") or 24)),
        }

    def _rank_candidates(self, candidates: list[dict[str, Any]], *, boundaries: Mapping[str, Any], epoch: float) -> tuple[list[tuple[float, dict[str, Any], dict[str, Any]]], dict[str, int]]:
        ranked: list[tuple[float, dict[str, Any], dict[str, Any]]] = []
        filtered = {"ineligible": 0, "topic": 0, "resource": 0, "cooldown_repetition": 0, "future_eligible": 0}
        for item in candidates:
            eligibility = item.get("eligibility") or {}
            if eligibility.get("eligible") is not True:
                filtered["ineligible"] += 1; continue
            eligible_after = _parse_epoch(eligibility.get("eligible_after"))
            if eligible_after and epoch < eligible_after:
                filtered["future_eligible"] += 1; continue
            topic = str((item.get("scope") or {}).get("topic_key") or "")
            if topic in boundaries["blocked_topics"] or (boundaries["allowed_topics"] and topic not in boundaries["allowed_topics"]):
                filtered["topic"] += 1; continue
            cost = float((item.get("resource_cost_estimate") or {}).get("normalized_cost") or 0)
            if cost > float(boundaries["resource_budget"]):
                filtered["resource"] += 1; continue
            last_selected_epoch = _parse_epoch(item.get("last_selected_at"))
            last_change_epoch = _parse_epoch(item.get("last_meaningful_change_at"))
            selected_source_value = item.get("last_selected_source_revision")
            selected_source_revision = -1 if selected_source_value is None else int(selected_source_value)
            source_revision = int(item.get("source_revision") or 0)
            meaningful_state_change = not last_selected_epoch or source_revision > selected_source_revision or last_change_epoch > last_selected_epoch
            recent_without_change = bool(last_selected_epoch and epoch - last_selected_epoch < float(boundaries["cooldown_seconds"]) and not meaningful_state_change)
            if recent_without_change:
                filtered["cooldown_repetition"] += 1; continue
            attention_count = int(item.get("attention_count") or 0)
            age_anchor = last_selected_epoch or _parse_epoch(item.get("created_at")) or epoch
            unattended_age_hours = max(0.0, epoch - age_anchor) / 3600.0
            fairness = min(1.0, unattended_age_hours / float(boundaries["starvation_horizon_hours"]) + (0.25 if attention_count == 0 else 0.0))
            continuity = 0.8 if attention_count > 0 and meaningful_state_change else (0.55 if attention_count == 0 else 0.25)
            repetition_penalty = min(0.35, attention_count * float(boundaries["repetition_penalty_per_attention"])) if not meaningful_state_change else 0.0
            score = (
                float(item.get("salience") or 0) * 0.28
                + float(item.get("urgency") or 0) * 0.24
                + float(item.get("uncertainty") or 0) * 0.16
                + continuity * float(boundaries["continuity_weight"])
                + fairness * float(boundaries["fairness_weight"])
                - cost * 0.16
                - repetition_penalty
            )
            factors = {
                "continuity_value": round(continuity, 4),
                "fairness_value": round(fairness, 4),
                "resource_cost": round(cost, 4),
                "repetition_penalty": round(repetition_penalty, 4),
                "meaningful_state_change": meaningful_state_change,
            }
            ranked.append((round(max(0.0, min(1.0, score)), 4), item, factors))
        ranked.sort(key=lambda row: (-row[0], int(row[1].get("attention_count") or 0), str(row[1].get("agenda_id") or "")))
        return ranked, filtered

    @staticmethod
    def _reflection_handoff(item: Mapping[str, Any], receipt_id: str) -> dict[str, Any]:
        origin_type = str((item.get("origin") or {}).get("type") or "")
        if origin_type == "reconsideration_schedule":
            path = "bounded_reconsideration_reflection"
        elif origin_type in {"inquiry", "residual_question"}:
            path = "inquiry_reflection"
        else:
            path = "endogenous_cognitive_cycle"
        return {
            "handoff_id": f"reflection-handoff-{_digest(receipt_id, item.get('agenda_id'))[:24]}",
            "target_path": path,
            "agenda_id": str(item.get("agenda_id") or ""),
            "subject_digest": str(item.get("subject_digest") or ""),
            "origin_type": origin_type,
            "reflection_step_limit": 1,
            "provider_calls_allowed": 0,
            "external_browsing_allowed": False,
            "action_authority_granted": False,
            "generation_loop_created": False,
            "private_subject_exposed": False,
        }

    @staticmethod
    def _record_processed_event(state: dict[str, Any], event_id: str, result: Mapping[str, Any], now: str) -> None:
        state["processed_events"] = (list(state["processed_events"]) + [{
            "event_id": event_id,
            "event_digest": _digest(event_id),
            "occurred_at": now,
            "result": deepcopy(dict(result)),
            "content_free": True,
        }])[-1024:]

    def inspection_summary(self, *, receipt_limit: int = 16) -> dict[str, Any]:
        state = self._load()
        receipts = list(state["arbitration_receipts"])[-max(0, int(receipt_limit)) :]
        public = [{
            "receipt_id": row.get("receipt_id"),
            "status": row.get("status"),
            "occurred_at": row.get("occurred_at"),
            "trigger_type": row.get("trigger_type"),
            "candidate_count": row.get("candidate_count"),
            "eligible_ranked_count": row.get("eligible_ranked_count"),
            "selected_agenda_id": row.get("selected_agenda_id"),
            "selected_subject_digest": row.get("selected_subject_digest"),
            "selected_origin_type": row.get("selected_origin_type"),
            "selected_score": row.get("selected_score"),
            "deliberate_no_selection": row.get("deliberate_no_selection"),
            "no_selection_reason_codes": list(row.get("no_selection_reason_codes") or []),
            "filtered_counts": deepcopy(row.get("filtered_counts") or {}),
            "reflection_handoff": deepcopy(row.get("reflection_handoff") or {}),
            "private_subject_exposed": False,
        } for row in receipts]
        selected_count = sum(1 for row in state["arbitration_receipts"] if row.get("selected_agenda_id"))
        no_selection_count = len(state["arbitration_receipts"]) - selected_count
        return {
            "ok": True,
            "contract_version": ARBITRATION_CONTRACT_VERSION,
            "revision": int(state.get("revision") or 0),
            "updated_at": state.get("updated_at") or "",
            "worker_generation": int(state.get("worker_generation") or 1),
            "arbitration_count": len(state["arbitration_receipts"]),
            "selection_count": selected_count,
            "deliberate_no_selection_count": no_selection_count,
            "recent_receipts": public,
            "controls": deepcopy(state["controls"]),
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
            "command_executed": False,
            "file_modified": False,
            "model_managed": False,
            "action_authority_changed": False,
            "runtime_mutated": False,
        }


def build_motivation_agenda_arbitration_inspection(runtime_root: str | Path | None = None) -> dict[str, Any]:
    return MotivationAgendaArbitrator(runtime_root).inspection_summary()
