from __future__ import annotations
"""v1141.1 durable content-free governed sandbox repair work-order candidates."""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
from typing import Any, Callable

from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from repair_implementation_eligibility import RepairImplementationEligibilityStore

CONTRACT_VERSION = "v1141.1"
SCHEMA_VERSION = "1"
STATES = {
    "active",
    "suppressed",
    "deferred",
    "awaiting_prerequisite",
    "awaiting_approval",
    "awaiting_authorization",
    "ready_for_operator_confirmed_materialization",
    "claimed",
    "expired",
    "superseded",
    "retracted",
    "retired",
}
AUTHORITY_KEYS = (
    "can_browse",
    "can_contact_provider",
    "can_generate_patch_text",
    "can_create_sandbox",
    "can_materialize_workspace",
    "can_write_sandbox_files",
    "can_execute_commands",
    "can_run_tests",
    "can_modify_source",
    "can_modify_installation",
    "can_install",
    "can_approve",
    "can_authorize",
    "can_promote",
    "can_certify",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _clean(value: Any, limit: int = 240) -> str:
    return " ".join(str(value or "").split())[:limit]


def _digest(*parts: Any) -> str:
    return hashlib.sha256("\x1f".join(_clean(part, 4000) for part in parts).encode()).hexdigest()


def _unique(values: list[Any] | tuple[Any, ...] | set[Any]) -> list[str]:
    return sorted({_clean(value, 240) for value in values if _clean(value, 240)})


def _root() -> Path:
    return (
        Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data")
        .expanduser()
        .resolve()
        / "cognition"
    )


def _parse_time(value: Any) -> datetime | None:
    token = _clean(value, 80)
    if not token:
        return None
    try:
        return datetime.fromisoformat(token.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _default() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "work_orders": [],
        "processed_events": [],
        "revision": 0,
        "updated_at": "",
        "authority_boundary": {key: False for key in AUTHORITY_KEYS},
    }


class SandboxRepairWorkOrderStore:
    def __init__(self, runtime_root: str | Path | None = None, *, clock: Callable[[], str] | None = None):
        self.runtime_root = Path(runtime_root).resolve() if runtime_root else _root()
        self.path = self.runtime_root / "sandbox_repair_work_orders.json"
        self.clock = clock or _now
        self.eligibility = RepairImplementationEligibilityStore(self.runtime_root)

    def _load(self) -> dict[str, Any]:
        state = load_json_file(self.path, _default(), expected_type=dict)
        for key, value in _default().items():
            state.setdefault(key, deepcopy(value))
        return state

    def snapshot(self) -> dict[str, Any]:
        return deepcopy(self._load())

    def register(
        self,
        event_id: str,
        *,
        eligibility_id: str,
        test_profile_id: str,
        time_budget_seconds: int,
        owner_id: str = "",
        worker_claim_id: str = "",
        preexisting_claim: bool = False,
        execution_token_max_uses: int = 1,
        requested_operation_categories: list[str] | None = None,
        requested_execution_modes: list[str] | None = None,
        requested_component_ids: list[str] | None = None,
        requested_path_digests: list[str] | None = None,
        requested_workspace_manifest_digests: list[str] | None = None,
        requested_isolation_profile_ids: list[str] | None = None,
        requested_command_profile_ids: list[str] | None = None,
        requested_resource_budget_ids: list[str] | None = None,
        prerequisite_ids: list[str] | None = None,
        contradiction_ids: list[str] | None = None,
        retraction_ids: list[str] | None = None,
        supersession_ids: list[str] | None = None,
        retirement_ids: list[str] | None = None,
        tab_session_id: str = "",
    ) -> dict[str, Any]:
        if not _clean(event_id, 180):
            raise ValueError("event_id required")
        eligibility_id = _clean(eligibility_id, 240)
        eligibility = next(
            (row for row in self.eligibility.snapshot().get("eligibility_records", []) if row.get("eligibility_id") == eligibility_id),
            None,
        )
        if not eligibility:
            raise ValueError("exact v1141.0 repair implementation eligibility required")
        test_profile_id = _clean(test_profile_id, 240)
        if not test_profile_id:
            raise ValueError("bounded test profile identifier required")
        time_budget_seconds = max(1, min(int(time_budget_seconds), 86400))
        token_uses = max(1, min(int(execution_token_max_uses), 8))

        bounds = {
            "allowed_operation_categories": _unique(eligibility.get("allowed_operation_categories", [])),
            "allowed_execution_modes": _unique(eligibility.get("allowed_execution_modes", [])),
            "component_ids": _unique(eligibility.get("component_ids", [])),
            "path_digests": _unique(eligibility.get("path_digests", [])),
            "workspace_manifest_digests": _unique(eligibility.get("workspace_manifest_digests", [])),
            "isolation_profile_ids": _unique(eligibility.get("isolation_profile_ids", [])),
            "command_profile_ids": _unique(eligibility.get("command_profile_ids", [])),
            "resource_budget_ids": _unique(eligibility.get("resource_budget_ids", [])),
        }
        requested = {
            "allowed_operation_categories": _unique(requested_operation_categories or bounds["allowed_operation_categories"]),
            "allowed_execution_modes": _unique(requested_execution_modes or bounds["allowed_execution_modes"]),
            "component_ids": _unique(requested_component_ids or bounds["component_ids"]),
            "path_digests": _unique(requested_path_digests or bounds["path_digests"]),
            "workspace_manifest_digests": _unique(requested_workspace_manifest_digests or bounds["workspace_manifest_digests"]),
            "isolation_profile_ids": _unique(requested_isolation_profile_ids or bounds["isolation_profile_ids"]),
            "command_profile_ids": _unique(requested_command_profile_ids or bounds["command_profile_ids"]),
            "resource_budget_ids": _unique(requested_resource_budget_ids or bounds["resource_budget_ids"]),
        }
        immutable_bounds_match = all(requested[key] == value for key, value in bounds.items())
        prerequisites = _unique(list(eligibility.get("prerequisite_ids", [])) + list(prerequisite_ids or []))
        contradictions = _unique(contradiction_ids or [])
        retractions = _unique(retraction_ids or [])
        supersessions = _unique(supersession_ids or [])
        retirements = _unique(retirement_ids or [])
        now_text = self.clock()
        now = _parse_time(now_text) or datetime.now(timezone.utc)
        valid_until = _parse_time(eligibility.get("bounded_valid_until"))
        expired = not valid_until or valid_until <= now or eligibility.get("validity_state") == "expired"

        state = "ready_for_operator_confirmed_materialization"
        reason = "exact_authorized_bounds_ready_for_operator_confirmation"
        eligibility_state = eligibility.get("state")
        if retirements:
            state, reason = "retired", "retirement_lineage"
        elif retractions or eligibility_state == "retracted":
            state, reason = "retracted", "retraction_lineage"
        elif supersessions or eligibility_state == "superseded":
            state, reason = "superseded", "supersession_lineage"
        elif expired or eligibility_state == "expired":
            state, reason = "expired", "bounded_validity_expired"
        elif contradictions or not immutable_bounds_match or eligibility_state == "suppressed":
            state, reason = "suppressed", "contradiction_or_authorized_bound_mismatch"
        elif eligibility_state == "awaiting_approval":
            state, reason = "awaiting_approval", "approval_pending"
        elif eligibility_state == "awaiting_authorization":
            state, reason = "awaiting_authorization", "authorization_pending"
        elif prerequisites or eligibility_state == "awaiting_prerequisite":
            state, reason = "awaiting_prerequisite", "prerequisite_pending"
        elif eligibility_state not in {"eligible", "requires_operator_review"}:
            state, reason = "deferred", "eligibility_not_ready"
        elif preexisting_claim and _clean(worker_claim_id, 240):
            state, reason = "claimed", "preexisting_external_claim_recorded"

        semantic_key = _digest(
            eligibility_id,
            eligibility.get("reviewed_artifact_set_digest"),
            eligibility.get("approval_id"),
            eligibility.get("authorization_id"),
            test_profile_id,
            time_budget_seconds,
            token_uses,
            *bounds["allowed_operation_categories"],
            *bounds["allowed_execution_modes"],
            *bounds["component_ids"],
            *bounds["path_digests"],
            *bounds["workspace_manifest_digests"],
            *bounds["isolation_profile_ids"],
            *bounds["command_profile_ids"],
            *bounds["resource_budget_ids"],
            immutable_bounds_match,
            *requested["allowed_operation_categories"],
            *requested["allowed_execution_modes"],
            *requested["component_ids"],
            *requested["path_digests"],
            *requested["workspace_manifest_digests"],
            *requested["isolation_profile_ids"],
            *requested["command_profile_ids"],
            *requested["resource_budget_ids"],
            *contradictions,
            *retractions,
            *supersessions,
            *retirements,
        )
        with metadata_mutation_lock(self.path, timeout_seconds=5):
            state_doc = self._load()
            prior = next((row for row in state_doc["processed_events"] if row.get("event_id") == _clean(event_id, 180)), None)
            if prior:
                return {"ok": True, **deepcopy(prior["result"]), "idempotent": True}
            duplicate = next(
                (
                    row
                    for row in state_doc["work_orders"]
                    if row.get("semantic_key") == semantic_key
                    and row.get("state") in {
                        "active",
                        "deferred",
                        "awaiting_prerequisite",
                        "awaiting_approval",
                        "awaiting_authorization",
                        "ready_for_operator_confirmed_materialization",
                        "claimed",
                    }
                ),
                None,
            )
            if duplicate:
                result = {
                    "status": "sandbox_repair_work_order_reused",
                    "work_order_id": duplicate["work_order_id"],
                    "state": duplicate["state"],
                    "reason": "cross_tab_or_retry_duplicate_suppressed",
                }
            else:
                work_order_id = f"sandbox-repair-work-order-{semantic_key[:24]}"
                token_id = f"repair-execution-token-{_digest(work_order_id, eligibility.get('authorization_id'))[:24]}"
                row = {
                    "work_order_id": work_order_id,
                    "eligibility_id": eligibility_id,
                    "reviewed_artifact_set_digest": eligibility.get("reviewed_artifact_set_digest", ""),
                    "approval_id": eligibility.get("approval_id", ""),
                    "authorization_id": eligibility.get("authorization_id", ""),
                    "approval_artifact_set_digest": eligibility.get("approval_artifact_set_digest", ""),
                    "authorization_artifact_set_digest": eligibility.get("authorization_artifact_set_digest", ""),
                    "v1140_arbitration_id": eligibility.get("v1140_arbitration_id", ""),
                    "v1140_deliberation_session_id": eligibility.get("v1140_deliberation_session_id", ""),
                    "v1140_candidate_id": eligibility.get("v1140_candidate_id", ""),
                    "v1140_eligibility_ids": deepcopy(eligibility.get("v1140_eligibility_ids", [])),
                    "sandbox_change_arbitration_ids": deepcopy(eligibility.get("sandbox_change_arbitration_ids", [])),
                    "sandbox_change_candidate_ids": deepcopy(eligibility.get("sandbox_change_candidate_ids", [])),
                    "sandbox_change_eligibility_ids": deepcopy(eligibility.get("sandbox_change_eligibility_ids", [])),
                    "test_plan_candidate_ids": deepcopy(eligibility.get("test_plan_candidate_ids", [])),
                    "test_plan_eligibility_ids": deepcopy(eligibility.get("test_plan_eligibility_ids", [])),
                    "specification_candidate_ids": deepcopy(eligibility.get("specification_candidate_ids", [])),
                    "proposal_candidate_ids": deepcopy(eligibility.get("proposal_candidate_ids", [])),
                    "deficiency_candidate_ids": deepcopy(eligibility.get("deficiency_candidate_ids", [])),
                    **bounds,
                    "test_profile_id": test_profile_id,
                    "time_budget_seconds": time_budget_seconds,
                    "containment_requirements": deepcopy(eligibility.get("containment_requirements", [])),
                    "reversibility_requirements": deepcopy(eligibility.get("reversibility_requirements", [])),
                    "recovery_requirements": deepcopy(eligibility.get("recovery_requirements", [])),
                    "rollback_requirements": deepcopy(eligibility.get("rollback_requirements", [])),
                    "prerequisite_ids": prerequisites,
                    "operator_review_required": True,
                    "operator_confirmation_required_for_materialization": True,
                    "bounded_valid_until": eligibility.get("bounded_valid_until", ""),
                    "execution_token_id": token_id,
                    "execution_token_max_uses": token_uses,
                    "execution_token_activated": False,
                    "execution_token_consumed": False,
                    "execution_token_grants_authority": False,
                    "owner_id": _clean(owner_id, 240),
                    "worker_claim_id": _clean(worker_claim_id, 240),
                    "preexisting_claim_recorded": bool(preexisting_claim and _clean(worker_claim_id, 240)),
                    "claim_created_by_work_order": False,
                    "tab_session_digest": _digest(tab_session_id) if _clean(tab_session_id, 240) else "",
                    "contradiction_ids": contradictions,
                    "retraction_ids": retractions,
                    "supersession_ids": supersessions,
                    "retirement_ids": retirements,
                    "immutable_authorized_bounds": True,
                    "authorized_bounds_match": immutable_bounds_match,
                    "semantic_key": semantic_key,
                    "structural_digest": _digest(semantic_key, state, reason, token_id),
                    "state": state,
                    "work_order_reason": reason,
                    "created_at": now_text,
                    "updated_at": now_text,
                    "sandbox_id": "",
                    "workspace_id": "",
                    "candidate_change_id": "",
                    "patch_digest": "",
                    "command_execution_ids": [],
                    "test_execution_ids": [],
                    "structural_receipt_ids": [],
                    "verified_completion_id": "",
                    "installation_id": "",
                    "promotion_id": "",
                    "certification_id": "",
                }
                state_doc["work_orders"].append(row)
                result = {
                    "status": "sandbox_repair_work_order_registered",
                    "work_order_id": work_order_id,
                    "state": state,
                    "reason": reason,
                }
            state_doc["processed_events"].append(
                {"event_id": _clean(event_id, 180), "occurred_at": now_text, "result": deepcopy(result), "content_free": True}
            )
            state_doc["revision"] += 1
            state_doc["updated_at"] = now_text
            write_json_atomic(self.path, state_doc, expected_type=dict, sort_keys=True)
            return {"ok": True, **result, "idempotent": False}

    def inspection_summary(self) -> dict[str, Any]:
        state = self._load()
        counts: dict[str, int] = {}
        for row in state["work_orders"]:
            counts[row.get("state", "")] = counts.get(row.get("state", ""), 0) + 1
        return {
            "ok": True,
            "contract_version": CONTRACT_VERSION,
            "work_order_count": len(state["work_orders"]),
            "state_counts": counts,
            "recognized_states": sorted(STATES),
            "recent_work_orders": deepcopy(state["work_orders"][-24:]),
            "authority_boundary": deepcopy(state["authority_boundary"]),
            "approval_created": False,
            "authorization_created": False,
            "claim_created": False,
            "sandbox_created": False,
            "workspace_materialized": False,
            "patch_text_generated": False,
            "raw_source_exposed": False,
            "commands_exposed": False,
            "test_instructions_exposed": False,
            "hidden_reasoning_exposed": False,
            "commands_executed": False,
            "tests_executed": False,
            "source_modified": False,
            "installation_modified": False,
            "external_action_executed": False,
        }


def build_sandbox_repair_work_order_inspection(runtime_root: str | Path | None = None) -> dict[str, Any]:
    return SandboxRepairWorkOrderStore(runtime_root).inspection_summary()
