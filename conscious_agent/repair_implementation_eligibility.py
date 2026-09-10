from __future__ import annotations
"""v1141.0 durable content-free authorized repair implementation eligibility."""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
from typing import Any, Callable

from isolated_sandbox_execution_arbitration import IsolatedSandboxExecutionArbitrationStore
from isolated_sandbox_execution_candidates import IsolatedSandboxExecutionCandidateStore
from isolated_sandbox_execution_deliberation_sessions import IsolatedSandboxExecutionDeliberationSessionStore
from isolated_sandbox_execution_eligibility import IsolatedSandboxExecutionEligibilityStore
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from sandbox_change_candidates import SandboxChangeCandidateStore

CONTRACT_VERSION = "v1141.0"
SCHEMA_VERSION = "1"
SUPPORTED_OUTCOMES = {
    "isolated_sandbox_execution_supported",
    "isolated_sandbox_execution_probable",
}
STATES = {
    "eligible",
    "awaiting_prerequisite",
    "awaiting_approval",
    "awaiting_authorization",
    "requires_operator_review",
    "suppressed",
    "expired",
    "superseded",
    "retracted",
    "retired",
}
AUTHORITY_KEYS = (
    "can_browse",
    "can_contact_provider",
    "can_read_raw_source",
    "can_write_patch_text",
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
    "can_execute",
    "can_promote",
    "can_certify",
)
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


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
        "eligibility_records": [],
        "processed_events": [],
        "revision": 0,
        "updated_at": "",
        "authority_boundary": {key: False for key in AUTHORITY_KEYS},
    }


class RepairImplementationEligibilityStore:
    def __init__(self, runtime_root: str | Path | None = None, *, clock: Callable[[], str] | None = None):
        self.runtime_root = Path(runtime_root).resolve() if runtime_root else _root()
        self.path = self.runtime_root / "repair_implementation_eligibility.json"
        self.clock = clock or _now
        self.arbitration = IsolatedSandboxExecutionArbitrationStore(self.runtime_root)
        self.sessions = IsolatedSandboxExecutionDeliberationSessionStore(self.runtime_root)
        self.candidates = IsolatedSandboxExecutionCandidateStore(self.runtime_root)
        self.execution_eligibility = IsolatedSandboxExecutionEligibilityStore(self.runtime_root)
        self.sandbox_candidates = SandboxChangeCandidateStore(self.runtime_root)

    def _load(self) -> dict[str, Any]:
        state = load_json_file(self.path, _default(), expected_type=dict)
        for key, value in _default().items():
            state.setdefault(key, deepcopy(value))
        return state

    def snapshot(self) -> dict[str, Any]:
        return deepcopy(self._load())

    def resolve_lineage(self, arbitration_id: str) -> dict[str, Any]:
        arbitration_id = _clean(arbitration_id, 240)
        outcome = next(
            (row for row in self.arbitration.snapshot().get("outcomes", []) if row.get("arbitration_id") == arbitration_id),
            None,
        )
        if not outcome or outcome.get("outcome") not in SUPPORTED_OUTCOMES:
            raise ValueError("exact supported or probable v1140 isolated-execution arbitration required")

        session_id = _clean(outcome.get("session_id"), 240)
        candidate_id = _clean(outcome.get("candidate_id"), 240)
        session = next((row for row in self.sessions.snapshot().get("sessions", []) if row.get("session_id") == session_id), None)
        candidate = next((row for row in self.candidates._load().get("candidates", []) if row.get("candidate_id") == candidate_id), None)
        if not session or not candidate:
            raise ValueError("exact v1140 deliberation and candidate lineage required")

        eligibility_ids = _unique(list(outcome.get("eligibility_ids", [])) + list(candidate.get("eligibility_ids", [])))
        execution_eligibility_rows = [
            row for row in self.execution_eligibility.snapshot().get("eligibility_records", []) if row.get("eligibility_id") in eligibility_ids
        ]
        if not eligibility_ids or len(execution_eligibility_rows) != len(eligibility_ids):
            raise ValueError("exact v1140 eligibility lineage required")

        sandbox_candidate_ids = _unique(
            [candidate.get("sandbox_change_candidate_id")]
            + list(candidate.get("sandbox_change_candidate_ids", []))
            + [row.get("sandbox_change_candidate_id") for row in execution_eligibility_rows]
        )
        sandbox_rows = [
            row for row in self.sandbox_candidates._load().get("candidates", []) if row.get("candidate_id") in sandbox_candidate_ids
        ]
        if not sandbox_candidate_ids or len(sandbox_rows) != len(sandbox_candidate_ids):
            raise ValueError("exact v1139 sandbox-change candidate lineage required")

        sandbox_arbitration_ids = _unique(
            list(candidate.get("sandbox_change_arbitration_ids", []))
            + [row.get("sandbox_change_arbitration_id") for row in execution_eligibility_rows]
            + [item for row in sandbox_rows for item in row.get("arbitration_ids", [])]
        )
        sandbox_eligibility_ids = _unique(
            list(candidate.get("sandbox_change_eligibility_ids", []))
            + [item for row in execution_eligibility_rows for item in row.get("sandbox_change_eligibility_ids", [])]
            + [item for row in sandbox_rows for item in row.get("eligibility_ids", [])]
        )
        test_plan_candidate_ids = _unique([item for row in sandbox_rows for item in row.get("test_plan_candidate_ids", [])])
        test_plan_eligibility_ids = _unique([item for row in sandbox_rows for item in row.get("test_plan_eligibility_ids", [])])
        specification_candidate_ids = _unique([item for row in sandbox_rows for item in row.get("specification_candidate_ids", [])])
        proposal_candidate_ids = _unique([item for row in sandbox_rows for item in row.get("proposal_candidate_ids", [])])
        deficiency_candidate_ids = _unique(
            list(outcome.get("deficiency_candidate_ids", []))
            + list(candidate.get("deficiency_candidate_ids", []))
            + [item for row in execution_eligibility_rows for item in row.get("deficiency_candidate_ids", [])]
            + [item for row in sandbox_rows for item in row.get("deficiency_candidate_ids", [])]
        )
        component_ids = _unique(
            list(outcome.get("component_ids", []))
            + list(candidate.get("component_ids", []))
            + [item for row in sandbox_rows for item in row.get("component_ids", [])]
        )
        path_digests = _unique([item for row in sandbox_rows for item in row.get("path_digests", [])])
        operation_categories = _unique([item for row in sandbox_rows for item in row.get("operation_categories", [])])
        execution_modes = _unique(list(outcome.get("execution_modes", [])) + list(candidate.get("execution_modes", [])))
        workspace_manifest_digests = _unique(
            list(candidate.get("workspace_manifest_digests", []))
            + [row.get("workspace_manifest_digest") for row in execution_eligibility_rows]
        )
        isolation_profile_ids = _unique(
            list(candidate.get("isolation_profile_ids", []))
            + [row.get("isolation_profile_id") for row in execution_eligibility_rows]
        )
        command_profile_ids = _unique(
            list(candidate.get("command_profile_ids", []))
            + [row.get("command_profile_id") for row in execution_eligibility_rows]
        )
        resource_budget_ids = _unique(
            list(candidate.get("resource_budget_ids", []))
            + [row.get("resource_budget_id") for row in execution_eligibility_rows]
        )
        project_digests = _unique(list(candidate.get("project_digests", [])) + list(outcome.get("project_digests", [])))
        scope_digests = _unique(list(candidate.get("scope_digests", [])) + list(outcome.get("scope_digests", [])))
        prerequisite_ids = _unique(
            list(candidate.get("prerequisite_ids", []))
            + [item for row in execution_eligibility_rows for item in row.get("prerequisite_ids", [])]
        )

        if not all((component_ids, execution_modes, workspace_manifest_digests, isolation_profile_ids, command_profile_ids, resource_budget_ids)):
            raise ValueError("bounded component, execution, workspace, isolation, command, and resource lineage required")
        if not path_digests and not component_ids:
            raise ValueError("path digests or component identifiers required")

        lineage = {
            "v1140_arbitration_id": arbitration_id,
            "v1140_arbitration_outcome": outcome.get("outcome"),
            "v1140_deliberation_session_id": session_id,
            "v1140_candidate_id": candidate_id,
            "v1140_eligibility_ids": eligibility_ids,
            "sandbox_change_arbitration_ids": sandbox_arbitration_ids,
            "sandbox_change_candidate_ids": sandbox_candidate_ids,
            "sandbox_change_eligibility_ids": sandbox_eligibility_ids,
            "test_plan_candidate_ids": test_plan_candidate_ids,
            "test_plan_eligibility_ids": test_plan_eligibility_ids,
            "specification_candidate_ids": specification_candidate_ids,
            "proposal_candidate_ids": proposal_candidate_ids,
            "deficiency_candidate_ids": deficiency_candidate_ids,
            "component_ids": component_ids,
            "path_digests": path_digests,
            "allowed_operation_categories": operation_categories,
            "allowed_execution_modes": execution_modes,
            "workspace_manifest_digests": workspace_manifest_digests,
            "isolation_profile_ids": isolation_profile_ids,
            "command_profile_ids": command_profile_ids,
            "resource_budget_ids": resource_budget_ids,
            "project_digests": project_digests,
            "scope_digests": scope_digests,
            "upstream_prerequisite_ids": prerequisite_ids,
        }
        lineage["reviewed_artifact_set_digest"] = _digest(
            arbitration_id,
            session_id,
            candidate_id,
            *eligibility_ids,
            *sandbox_arbitration_ids,
            *sandbox_candidate_ids,
            *sandbox_eligibility_ids,
            *test_plan_candidate_ids,
            *test_plan_eligibility_ids,
            *specification_candidate_ids,
            *proposal_candidate_ids,
            *deficiency_candidate_ids,
            *component_ids,
            *path_digests,
            *operation_categories,
            *execution_modes,
            *workspace_manifest_digests,
            *isolation_profile_ids,
            *command_profile_ids,
            *resource_budget_ids,
            *project_digests,
            *scope_digests,
        )
        return lineage

    @staticmethod
    def _binding_summary(record: dict[str, Any] | None, *, kind: str, expected_digest: str, approval_id: str = "", now: datetime) -> dict[str, Any]:
        record = record if isinstance(record, dict) else {}
        identifier = _clean(record.get("id") or record.get(f"{kind}_id"), 240)
        status = _clean(record.get("status"), 80).lower()
        artifact_digest = _clean(record.get("reviewed_artifact_set_digest"), 80).lower()
        expires_at = _clean(record.get("expires_at"), 80)
        expiry = _parse_time(expires_at)
        expected_status = "approved" if kind == "approval" else "authorized"
        contradiction = bool(record.get("contradicted") or record.get("retracted") or record.get("superseded"))
        approval_match = kind == "approval" or _clean(record.get("approval_id"), 240) == approval_id
        valid = bool(
            identifier
            and status == expected_status
            and _HEX64.fullmatch(artifact_digest)
            and artifact_digest == expected_digest
            and expiry
            and expiry > now
            and not contradiction
            and approval_match
        )
        reason = "valid"
        if not identifier:
            reason = f"missing_{kind}"
        elif status != expected_status:
            reason = f"{kind}_not_{expected_status}"
        elif artifact_digest != expected_digest:
            reason = f"{kind}_artifact_set_mismatch"
        elif not expiry:
            reason = f"{kind}_bounded_expiry_required"
        elif expiry <= now:
            reason = f"{kind}_expired"
        elif contradiction:
            reason = f"{kind}_contradicted_or_retracted"
        elif not approval_match:
            reason = "authorization_approval_mismatch"
        return {
            f"{kind}_id": identifier,
            f"{kind}_status": status,
            f"{kind}_artifact_set_digest": artifact_digest,
            f"{kind}_expires_at": expires_at,
            f"{kind}_binding_valid": valid,
            f"{kind}_binding_reason": reason,
        }

    def register(
        self,
        event_id: str,
        *,
        arbitration_id: str,
        approval_record: dict[str, Any] | None = None,
        authorization_record: dict[str, Any] | None = None,
        approval_required: bool = True,
        authorization_required: bool = True,
        prerequisite_ids: list[str] | None = None,
        operator_review_required: bool = True,
        containment_requirements: list[str] | None = None,
        reversibility_requirements: list[str] | None = None,
        recovery_requirements: list[str] | None = None,
        rollback_requirements: list[str] | None = None,
        worker_claim_id: str = "",
        worker_generation: int = 0,
        current_generation: int = 0,
        tab_session_id: str = "",
        contradiction_ids: list[str] | None = None,
        retraction_ids: list[str] | None = None,
        supersession_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        if not _clean(event_id, 180):
            raise ValueError("event_id required")
        lineage = self.resolve_lineage(arbitration_id)
        now_text = self.clock()
        now = _parse_time(now_text) or datetime.now(timezone.utc)
        approval = self._binding_summary(
            approval_record,
            kind="approval",
            expected_digest=lineage["reviewed_artifact_set_digest"],
            now=now,
        )
        authorization = self._binding_summary(
            authorization_record,
            kind="authorization",
            expected_digest=lineage["reviewed_artifact_set_digest"],
            approval_id=approval["approval_id"],
            now=now,
        )
        prereqs = _unique(list(lineage["upstream_prerequisite_ids"]) + list(prerequisite_ids or []))
        containment = _unique(containment_requirements or ["os_enforced_isolation", "workspace_manifest_integrity", "no_live_source_write"])
        reversibility = _unique(reversibility_requirements or ["discardable_workspace", "pre_materialization_snapshot", "no_installation_effect"])
        recovery = _unique(recovery_requirements or ["restart_reconciliation", "stale_worker_suppression"])
        rollback = _unique(rollback_requirements or ["discard_candidate_workspace", "preserve_historical_receipts"])
        contradictions = _unique(contradiction_ids or [])
        retractions = _unique(retraction_ids or [])
        supersessions = _unique(supersession_ids or [])
        stale_worker = int(worker_generation) < int(current_generation)

        state = "eligible"
        reason = "exact_reviewed_and_authorized_repair_implementation"
        if retractions:
            state, reason = "retracted", "retraction_lineage"
        elif supersessions:
            state, reason = "superseded", "supersession_lineage"
        elif contradictions or stale_worker:
            state, reason = "suppressed", "contradiction_or_stale_worker"
        elif approval_required and not approval["approval_binding_valid"]:
            state = "awaiting_approval" if approval["approval_binding_reason"] == "missing_approval" else "suppressed"
            reason = approval["approval_binding_reason"]
        elif authorization_required and not authorization["authorization_binding_valid"]:
            state = "awaiting_authorization" if authorization["authorization_binding_reason"] == "missing_authorization" else "suppressed"
            reason = authorization["authorization_binding_reason"]
        elif prereqs:
            state, reason = "awaiting_prerequisite", "prerequisite_pending"
        elif operator_review_required:
            state, reason = "requires_operator_review", "operator_materialization_review_required"

        expiries = [
            expiry
            for expiry in (
                _parse_time(approval.get("approval_expires_at")),
                _parse_time(authorization.get("authorization_expires_at")),
            )
            if expiry
        ]
        bounded_valid_until = min(expiries).isoformat(timespec="milliseconds").replace("+00:00", "Z") if expiries else ""
        validity_state = "bounded_valid" if expiries and min(expiries) > now else "awaiting_binding"
        if expiries and min(expiries) <= now:
            state, reason, validity_state = "expired", "bounded_validity_expired", "expired"

        semantic_key = _digest(
            lineage["reviewed_artifact_set_digest"],
            approval["approval_id"],
            approval["approval_artifact_set_digest"],
            approval["approval_binding_reason"],
            authorization["authorization_id"],
            authorization["authorization_artifact_set_digest"],
            authorization["authorization_binding_reason"],
            stale_worker,
            *contradictions,
            *retractions,
            *supersessions,
            *prereqs,
            *containment,
            *reversibility,
            *recovery,
            *rollback,
        )
        with metadata_mutation_lock(self.path, timeout_seconds=5):
            state_doc = self._load()
            prior = next((row for row in state_doc["processed_events"] if row.get("event_id") == _clean(event_id, 180)), None)
            if prior:
                return {"ok": True, **deepcopy(prior["result"]), "idempotent": True}
            duplicate = next(
                (
                    row
                    for row in state_doc["eligibility_records"]
                    if row.get("semantic_key") == semantic_key
                    and row.get("state") in {
                        "eligible",
                        "awaiting_prerequisite",
                        "awaiting_approval",
                        "awaiting_authorization",
                        "requires_operator_review",
                    }
                ),
                None,
            )
            if duplicate:
                result = {
                    "status": "repair_implementation_eligibility_reused",
                    "eligibility_id": duplicate["eligibility_id"],
                    "state": duplicate["state"],
                    "reason": "cross_tab_or_retry_duplicate_suppressed",
                }
            else:
                eligibility_id = f"repair-implementation-eligibility-{semantic_key[:24]}"
                row = {
                    "eligibility_id": eligibility_id,
                    **lineage,
                    **approval,
                    **authorization,
                    "approval_required": bool(approval_required),
                    "authorization_required": bool(authorization_required),
                    "prerequisite_ids": prereqs,
                    "containment_requirements": containment,
                    "reversibility_requirements": reversibility,
                    "recovery_requirements": recovery,
                    "rollback_requirements": rollback,
                    "operator_review_required": bool(operator_review_required),
                    "bounded_valid_until": bounded_valid_until,
                    "validity_state": validity_state,
                    "worker_claim_id": _clean(worker_claim_id, 240),
                    "worker_generation": int(worker_generation),
                    "current_generation": int(current_generation),
                    "stale_worker_suppressed": stale_worker,
                    "tab_session_digest": _digest(tab_session_id) if _clean(tab_session_id, 240) else "",
                    "contradiction_ids": contradictions,
                    "retraction_ids": retractions,
                    "supersession_ids": supersessions,
                    "semantic_key": semantic_key,
                    "structural_digest": _digest(semantic_key, state, reason, bounded_valid_until),
                    "state": state,
                    "eligibility_reason": reason,
                    "created_at": now_text,
                    "updated_at": now_text,
                    "sandbox_id": "",
                    "workspace_id": "",
                    "patch_digest": "",
                    "candidate_change_id": "",
                    "command_receipt_ids": [],
                    "test_receipt_ids": [],
                    "verified_completion_id": "",
                    "installation_id": "",
                    "promotion_id": "",
                    "certification_id": "",
                }
                state_doc["eligibility_records"].append(row)
                result = {
                    "status": "repair_implementation_eligibility_registered",
                    "eligibility_id": eligibility_id,
                    "state": state,
                    "reason": reason,
                }
            state_doc["processed_events"].append(
                {
                    "event_id": _clean(event_id, 180),
                    "occurred_at": now_text,
                    "result": deepcopy(result),
                    "content_free": True,
                }
            )
            state_doc["revision"] += 1
            state_doc["updated_at"] = now_text
            write_json_atomic(self.path, state_doc, expected_type=dict, sort_keys=True)
            return {"ok": True, **result, "idempotent": False}

    def inspection_summary(self) -> dict[str, Any]:
        state = self._load()
        counts: dict[str, int] = {}
        for row in state["eligibility_records"]:
            counts[row.get("state", "")] = counts.get(row.get("state", ""), 0) + 1
        return {
            "ok": True,
            "contract_version": CONTRACT_VERSION,
            "record_count": len(state["eligibility_records"]),
            "state_counts": counts,
            "recognized_states": sorted(STATES),
            "recent_records": deepcopy(state["eligibility_records"][-24:]),
            "authority_boundary": deepcopy(state["authority_boundary"]),
            "approval_created": False,
            "authorization_created": False,
            "sandbox_created": False,
            "workspace_materialized": False,
            "patch_text_exposed": False,
            "raw_source_exposed": False,
            "commands_exposed": False,
            "test_instructions_exposed": False,
            "private_path_exposed": False,
            "hidden_reasoning_exposed": False,
            "provider_contacted": False,
            "commands_executed": False,
            "tests_executed": False,
            "source_modified": False,
            "installation_modified": False,
            "external_action_executed": False,
        }


def build_repair_implementation_eligibility_inspection(runtime_root: str | Path | None = None) -> dict[str, Any]:
    return RepairImplementationEligibilityStore(runtime_root).inspection_summary()
