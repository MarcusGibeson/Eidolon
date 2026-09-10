from __future__ import annotations
"""v1332 evidence-bound tool preconditions.

This layer evaluates supplied environment evidence before a future tool invocation.
It performs no probes or tool calls and grants no execution authority.
"""
from pathlib import Path
from typing import Any, Mapping, Sequence

from cognitive_coding_foundations import digest
from candidate_approaches import PLANNING_DENIED_AUTHORITY
from project_evidence_store import atomic_json, evidence_root, read_json, seal, valid

CONTRACT_VERSION = "v1332.8"
TOOL_PRECONDITION_DENIED_AUTHORITY = {
    **PLANNING_DENIED_AUTHORITY,
    "tool_execution_authorized": False,
    "command_execution_authorized": False,
    "test_execution_authorized": False,
    "source_mutation_authorized": False,
    "approval_granted": False,
}
PRECONDITION_CODES = (
    "registered_capability",
    "availability_evidenced",
    "workspace_identified",
    "cwd_within_workspace",
    "boundary_clean",
    "workspace_mode_compatible",
    "dependencies_satisfied",
    "permissions_satisfied",
    "expected_artifacts_declared",
)
_MUTATING_AUTHORITY_CLASSES = {"workspace_mutation", "workspace_process", "service_process"}


def _path(record_id: str, runtime_root=None) -> Path:
    return evidence_root("tool_preconditions", runtime_root) / "records" / f"{record_id}.json"


def _evidence_digests(value: Mapping[str, Any] | None) -> list[str]:
    return sorted({str(x) for x in (value or {}).get("evidence_digests") or [] if str(x)})[:32]


def _capability(registry: Mapping[str, Any], tool_code: str) -> dict[str, Any]:
    return next((dict(x) for x in registry.get("capabilities") or [] if x.get("tool_code") == tool_code), {})


def evaluate_tool_preconditions(
    *,
    registry: Mapping[str, Any],
    tool_code: str,
    workspace_evidence: Mapping[str, Any] | None = None,
    dependency_requirements: Sequence[str] = (),
    dependency_evidence: Mapping[str, Mapping[str, Any]] | None = None,
    permission_evidence: Mapping[str, Any] | None = None,
    expected_artifacts: Sequence[Mapping[str, Any]] = (),
    risk_plan: Mapping[str, Any] | None = None,
    runtime_root=None,
) -> dict[str, Any]:
    """Evaluate content-minimized preconditions from supplied evidence only."""
    code = str(tool_code or "").strip()
    cap = _capability(registry, code)
    workspace = dict(workspace_evidence or {})
    deps = dependency_evidence or {}
    permission = dict(permission_evidence or {})
    required_deps = tuple(sorted({str(x) for x in dependency_requirements if str(x)}))
    artifacts = [dict(x) for x in expected_artifacts if isinstance(x, Mapping)]
    workspace_digests = _evidence_digests(workspace)
    permission_digests = _evidence_digests(permission)

    dep_rows = []
    for name in required_deps:
        ev = dict(deps.get(name) or {})
        ev_digests = _evidence_digests(ev)
        state = str(ev.get("state") or "unknown")
        dep_rows.append({
            "dependency_code": name,
            "state": state if state in {"present", "missing", "unknown"} else "unknown",
            "evidence_count": len(ev_digests),
            "evidence_digest": digest(ev_digests) if ev_digests else "",
        })

    artifact_rows = []
    for item in artifacts[:64]:
        artifact_code = str(item.get("artifact_code") or "").strip()
        contract_digest = str(item.get("contract_digest") or "").strip()
        if artifact_code:
            artifact_rows.append({"artifact_code": artifact_code, "contract_digest": contract_digest})

    side_effecting = bool(cap.get("side_effect_codes"))
    authority_class = str(cap.get("authority_class") or "")
    mode = str(workspace.get("workspace_mode") or "unknown")
    risk_requires_candidate = str((risk_plan or {}).get("required_isolation") or "") in {
        "disposable_candidate", "isolated_candidate", "fresh_disposable_candidate"
    }
    mode_ok = mode in {"read_only", "owned_workspace", "candidate_workspace"}
    if side_effecting or authority_class in _MUTATING_AUTHORITY_CLASSES:
        mode_ok = mode in {"owned_workspace", "candidate_workspace"}
    if risk_requires_candidate:
        mode_ok = mode == "candidate_workspace"

    checks = {
        "registered_capability": bool(cap),
        "availability_evidenced": bool(cap) and cap.get("availability_state") == "evidence_available" and int(cap.get("availability_evidence_count") or len(cap.get("availability_evidence_digests") or [])) > 0,
        "workspace_identified": bool(workspace.get("workspace_digest")) and bool(workspace_digests),
        "cwd_within_workspace": workspace.get("cwd_within_workspace") is True,
        "boundary_clean": workspace.get("boundary_clean") is True,
        "workspace_mode_compatible": mode_ok,
        "dependencies_satisfied": all(row["state"] == "present" and row["evidence_count"] > 0 for row in dep_rows),
        "permissions_satisfied": permission.get("state") == "permitted" and bool(permission_digests),
        "expected_artifacts_declared": bool(artifact_rows) and all(row["contract_digest"] for row in artifact_rows),
    }
    blocked = [key for key in PRECONDITION_CODES if not checks[key]]
    satisfied = not blocked
    record_id = "preconditions_" + digest({
        "contract": CONTRACT_VERSION,
        "registry_id": registry.get("registry_id"),
        "tool": code,
        "capability": cap.get("capability_digest") or cap.get("schema_digest"),
        "workspace": workspace.get("workspace_digest"),
        "workspace_evidence": workspace_digests,
        "dependencies": dep_rows,
        "permission_evidence": permission_digests,
        "artifacts": artifact_rows,
        "risk_plan": (risk_plan or {}).get("risk_plan_id") or (risk_plan or {}).get("risk_tier"),
    })[:24]
    row = seal({
        "contract_version": CONTRACT_VERSION,
        "precondition_record_id": record_id,
        "registry_id": registry.get("registry_id"),
        "tool_code": code,
        "capability_digest": cap.get("capability_digest") or cap.get("schema_digest"),
        "workspace_digest": workspace.get("workspace_digest"),
        "workspace_evidence_digests": workspace_digests,
        "workspace_mode": mode,
        "dependency_results": dep_rows,
        "permission_state": str(permission.get("state") or "unknown"),
        "permission_evidence_digests": permission_digests,
        "expected_artifacts": artifact_rows,
        "risk_plan_digest": digest(risk_plan) if risk_plan else "",
        "checks": checks,
        "blocked_preconditions": blocked,
        "preconditions_satisfied": satisfied,
        "environment_probes_executed": False,
        "tool_invoked": False,
        "preconditions_are_authority": False,
        "action_executed": False,
        "content_free": True,
        **TOOL_PRECONDITION_DENIED_AUTHORITY,
    })
    atomic_json(_path(record_id, runtime_root), row)
    return {
        "ok": satisfied,
        "status": "tool_preconditions_satisfied_but_unauthorized" if satisfied else "tool_preconditions_blocked",
        "tool_preconditions": public_tool_preconditions(row),
        "action_executed": False,
        **TOOL_PRECONDITION_DENIED_AUTHORITY,
    }


def public_tool_preconditions(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "precondition_record_id": row.get("precondition_record_id"),
        "registry_id": row.get("registry_id"),
        "tool_code": row.get("tool_code"),
        "workspace_digest": row.get("workspace_digest"),
        "workspace_mode": row.get("workspace_mode"),
        "dependency_results": [dict(x) for x in row.get("dependency_results") or []],
        "permission_state": row.get("permission_state"),
        "expected_artifacts": [dict(x) for x in row.get("expected_artifacts") or []],
        "checks": dict(row.get("checks") or {}),
        "blocked_preconditions": list(row.get("blocked_preconditions") or []),
        "preconditions_satisfied": row.get("preconditions_satisfied") is True,
        "environment_probes_executed": False,
        "tool_invoked": False,
        "preconditions_are_authority": False,
        "read_only": True,
        "action_executed": False,
        **TOOL_PRECONDITION_DENIED_AUTHORITY,
    }


def load_tool_preconditions(record_id: str, *, runtime_root=None, include_private: bool = False) -> dict[str, Any]:
    row = read_json(_path(str(record_id), runtime_root))
    if not row or not valid(row):
        return {}
    return row if include_private else public_tool_preconditions(row)


def process_tool_preconditions_control(text: str, *, project_state=None, runtime_root=None, **_) -> dict[str, Any]:
    if str(text or "").strip().lower() not in {"show tool preconditions", "inspect tool preconditions", "check tool preconditions"}:
        return {"active": False}
    state = project_state or {}
    return {"active": True, **evaluate_tool_preconditions(
        registry=state.get("tool_capability_registry") or {},
        tool_code=str(state.get("tool_code") or ""),
        workspace_evidence=state.get("workspace_evidence"),
        dependency_requirements=state.get("dependency_requirements") or (),
        dependency_evidence=state.get("dependency_evidence"),
        permission_evidence=state.get("tool_permission_evidence"),
        expected_artifacts=state.get("expected_artifacts") or (),
        risk_plan=state.get("risk_plan"),
        runtime_root=runtime_root,
    )}


__all__ = [
    "CONTRACT_VERSION", "TOOL_PRECONDITION_DENIED_AUTHORITY", "PRECONDITION_CODES", "evaluate_tool_preconditions",
    "public_tool_preconditions", "load_tool_preconditions", "process_tool_preconditions_control",
]
