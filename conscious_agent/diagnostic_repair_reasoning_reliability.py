from __future__ import annotations

"""v1257.6-v1257.8 reliability, recovery inspection, and operator handoff.

The functions here are read-only.  They verify diagnostic-plan/result lineage,
identify missing/tampered or repeated-repair evidence, and summarize the exact
repair history without executing diagnostics, contacting providers, rerunning
tests, or modifying either workspace or selected project.
"""

from typing import Any, Mapping

from diagnostic_repair_reasoning import public_diagnostic_result
from diagnostic_repair_reasoning_foundations import (
    DENIED_AUTHORITY,
    load_diagnostic_plan,
    load_diagnostic_result,
)
from isolated_coding_execution import load_isolated_coding_execution
from ordinary_chat_development_campaign import _digest, _read_json, _store_root

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1257.8"


def _attempt(request_id: str, number: int, runtime_root=None) -> dict[str, Any]:
    path = _store_root(runtime_root) / "isolated_coding_execution_attempts" / request_id / f"attempt-{int(number)}.json"
    row = _read_json(path)
    if not row:
        return {}
    supplied = str(row.get("attempt_record_digest") or "")
    return row if supplied and supplied == _digest({k: v for k, v in row.items() if k != "attempt_record_digest"}) else {}


def inspect_diagnostic_repair_health(request_id: str, *, runtime_root=None) -> dict[str, Any]:
    request_id = str(request_id or "").lower()
    execution = load_isolated_coding_execution(request_id, runtime_root=runtime_root)
    errors: list[str] = []
    warnings: list[str] = []
    if not execution:
        errors.append("isolated_execution_missing_or_invalid")
    result = execution.get("result") if isinstance(execution.get("result"), Mapping) else {}
    attempt_count = int(result.get("attempt_count") or execution.get("attempt_count") or 0)
    attempt_dir = _store_root(runtime_root) / "isolated_coding_execution_attempts" / request_id
    discovered = []
    if attempt_dir.is_dir():
        for path in attempt_dir.glob("attempt-*.json"):
            try:
                discovered.append(int(path.stem.split("-")[-1]))
            except ValueError:
                continue
    if discovered:
        attempt_count = max(attempt_count, max(discovered))
    failed_attempts = 0
    diagnostic_count = 0
    chain: list[dict[str, Any]] = []
    for number in range(1, attempt_count + 1):
        attempt = _attempt(request_id, number, runtime_root)
        if not attempt:
            errors.append(f"attempt_{number}_missing_or_invalid")
            continue
        verification = dict(attempt.get("verification") or {})
        if verification.get("passed") is not False:
            continue
        failed_attempts += 1
        plan = load_diagnostic_plan(request_id, number, runtime_root=runtime_root)
        diagnostic = load_diagnostic_result(request_id, number, runtime_root=runtime_root)
        if not plan:
            plan_path = _store_root(runtime_root) / "diagnostic_repair_reasoning" / request_id / f"attempt-{number}.json"
            errors.append(f"diagnostic_plan_{number}_invalid" if plan_path.exists() else f"diagnostic_plan_{number}_missing")
            continue
        if not diagnostic:
            diagnostic_path = _store_root(runtime_root) / "diagnostic_repair_results" / request_id / f"attempt-{number}.json"
            if diagnostic_path.exists():
                errors.append(f"diagnostic_result_{number}_invalid")
            elif execution.get("phase") == "running":
                warnings.append(f"diagnostic_result_{number}_pending_or_recoverable")
            else:
                errors.append(f"diagnostic_result_{number}_missing")
            continue
        diagnostic_count += 1
        if str(plan.get("attempt_digest") or "") != str(attempt.get("attempt_record_digest") or ""):
            errors.append(f"diagnostic_plan_{number}_attempt_binding_mismatch")
        if str(diagnostic.get("attempt_digest") or "") != str(attempt.get("attempt_record_digest") or ""):
            errors.append(f"diagnostic_result_{number}_attempt_binding_mismatch")
        if str(diagnostic.get("diagnostic_plan_digest") or "") != str(plan.get("diagnostic_plan_digest") or ""):
            errors.append(f"diagnostic_result_{number}_plan_binding_mismatch")
        if diagnostic.get("root_cause_proven") is not False:
            errors.append(f"diagnostic_result_{number}_overclaims_root_cause")
        if diagnostic.get("repeated_failed_repair"):
            warnings.append(f"attempt_{number}_repeated_failed_repair_blocked")
        chain.append({
            "attempt_number": number,
            "attempt_digest": str(attempt.get("attempt_record_digest") or ""),
            "verification_digest": str(verification.get("verification_digest") or ""),
            "diagnostic_plan_digest": str(plan.get("diagnostic_plan_digest") or ""),
            "diagnostic_result_digest": str(diagnostic.get("diagnostic_result_digest") or ""),
            "repair_posture": str(diagnostic.get("repair_posture") or ""),
            "preferred_hypothesis_code": str(diagnostic.get("preferred_hypothesis_code") or ""),
            "repeated_failed_repair": bool(diagnostic.get("repeated_failed_repair")),
        })
    authority_denied = True
    for row in chain:
        diagnostic = load_diagnostic_result(request_id, int(row["attempt_number"]), runtime_root=runtime_root)
        if any(diagnostic.get(key) is not expected for key, expected in DENIED_AUTHORITY.items()):
            authority_denied = False
            errors.append(f"diagnostic_result_{row['attempt_number']}_authority_boundary_invalid")
    chain_digest = _digest(chain)
    record = {
        "ok": not errors,
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": "diagnostic_repair_reasoning_healthy" if not errors else "diagnostic_repair_reasoning_health_blocked",
        "request_id": request_id,
        "execution_phase": str(execution.get("phase") or ""),
        "execution_status": str(result.get("status") or execution.get("status") or ""),
        "attempt_count": attempt_count,
        "failed_attempt_count": failed_attempts,
        "diagnostic_count": diagnostic_count,
        "diagnostic_chain": chain,
        "diagnostic_chain_digest": chain_digest,
        "errors": errors,
        "warnings": warnings,
        "authority_denied": authority_denied,
        "content_minimized": True,
        "read_only": True,
        "provider_contacted_by_inspection": False,
        "diagnostic_commands_executed_by_inspection": False,
        "tests_executed_by_inspection": False,
        "selected_project_modified": False,
        "source_modified": False,
        "native_windows_restart_and_cross_process_validation": "desktop_review_required",
        **DENIED_AUTHORITY,
    }
    record["health_digest"] = _digest(record)
    return record


def build_diagnostic_repair_operator_handoff(request_id: str, *, runtime_root=None) -> dict[str, Any]:
    request_id = str(request_id or "").lower()
    health = inspect_diagnostic_repair_health(request_id, runtime_root=runtime_root)
    execution = load_isolated_coding_execution(request_id, runtime_root=runtime_root)
    result = execution.get("result") if isinstance(execution.get("result"), Mapping) else {}
    diagnostics = []
    for row in health.get("diagnostic_chain") or []:
        diagnostic = load_diagnostic_result(request_id, int(row.get("attempt_number") or 0), runtime_root=runtime_root)
        if diagnostic:
            diagnostics.append(public_diagnostic_result(diagnostic))
    limitations = [
        "Diagnostic conclusions remain evidence-weighted hypotheses; root cause is not declared proven.",
        "Repair generation and focused diagnostics are available only inside the already-authorized isolated execution.",
        "Selected-project application remains governed separately by the v1255 controlled application contract.",
        "Native Windows cross-process restart, long-path, and junction/reparse behavior still requires Desktop Codex validation.",
    ]
    row = {
        "ok": bool(health.get("ok")),
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": "diagnostic_repair_operator_handoff_ready" if health.get("ok") else "diagnostic_repair_operator_handoff_blocked",
        "request_id": request_id,
        "execution_status": str(result.get("status") or execution.get("status") or ""),
        "test_passed": bool(result.get("test_passed")),
        "attempt_count": int(result.get("attempt_count") or execution.get("attempt_count") or 0),
        "repair_attempt_count": int(result.get("repair_attempt_count") or execution.get("repair_attempt_count") or 0),
        "diagnostic_cycle_count": len(diagnostics),
        "diagnostics": diagnostics,
        "diagnostic_chain_digest": str(health.get("diagnostic_chain_digest") or ""),
        "health_digest": str(health.get("health_digest") or ""),
        "limitations": limitations,
        "operator_review_required": True,
        "read_only": True,
        "content_minimized": True,
        "provider_contacted_by_handoff": False,
        "tests_executed_by_handoff": False,
        "selected_project_modified": False,
        "source_modified": False,
        **DENIED_AUTHORITY,
    }
    row["handoff_digest"] = _digest(row)
    return row


__all__ = ["CONTRACT_VERSION", "build_diagnostic_repair_operator_handoff", "inspect_diagnostic_repair_health"]
