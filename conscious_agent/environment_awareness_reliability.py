from __future__ import annotations

"""v1274.6-v1274.8 environment-awareness reliability and Windows handoff."""

import os
import re
import shutil
import time
from pathlib import Path
from typing import Any, Mapping

from environment_awareness_foundations import *
from environment_awareness import environment_aware_operator_status

CONTRACT_VERSION = "v1274.8"
_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:[\\/]")


def classify_windows_path_shape(path_text: str) -> dict[str, Any]:
    """Pure path-shape classification.  This never claims the host is Windows."""
    text = str(path_text or "")
    is_unc = text.startswith("\\\\") or text.startswith("//")
    is_extended = text.startswith("\\\\?\\") or text.startswith("//?/")
    is_drive = bool(_WINDOWS_DRIVE.match(text))
    return {
        "ok": True,
        "status": "windows_path_shape_classified",
        "windows_drive_shape": is_drive,
        "unc_shape": is_unc,
        "extended_length_shape": is_extended,
        "path_length": len(text),
        "host_windows_inferred": False,
        "host_windows_observed": False,
        "raw_path_persisted": False,
        **AUTHORITY_FLAGS,
    }


def reconcile_stale_environment_facts(environment_id: str, *, runtime_root: str | Path | None, now: float | None = None) -> dict[str, Any]:
    clock = float(time.time() if now is None else now)
    row = load_environment_awareness(environment_id, runtime_root=runtime_root)
    if not validate_environment_awareness(row).get("ok"):
        return {"ok": False, "status": "environment_awareness_invalid", **AUTHORITY_FLAGS}
    stale = [x for x in row.get("facts") or [] if clock >= float(x.get("observed_at") or 0.0) + int(x.get("stale_after_seconds") or 0)]
    return {
        "ok": True,
        "status": "environment_refresh_required" if stale else "environment_facts_current",
        "stale_fact_count": len(stale),
        "stale_fact_keys": [f"{x.get('domain')}:{x.get('key')}" for x in stale[:32]],
        "stale_observation_reused_as_current": False,
        "automatic_external_action_performed": False,
        "refresh_required": bool(stale),
        **AUTHORITY_FLAGS,
    }


def evaluate_environment_preflight(environment_id: str, *, runtime_root: str | Path | None, requirements: Mapping[str, Any], now: float | None = None) -> dict[str, Any]:
    """Evaluate requirements only from current observed facts.

    Inferred/assumed facts may explain context but cannot satisfy a mutation- or
    execution-sensitive preflight requirement. Unknown/stale facts fail closed.
    """
    clock = float(time.time() if now is None else now)
    row = load_environment_awareness(environment_id, runtime_root=runtime_root)
    if not validate_environment_awareness(row).get("ok"):
        return {"ok": False, "status": "environment_awareness_invalid", "preflight_passed": False, **AUTHORITY_FLAGS}
    facts = {(str(x.get("domain")), str(x.get("key"))): x for x in row.get("facts") or []}
    checks: list[dict[str, Any]] = []
    for raw_key, expected in list(requirements.items())[:32]:
        key = str(raw_key)
        if ":" not in key:
            raise ValueError("environment_requirement_must_be_domain_colon_key")
        domain, fact_key = key.split(":", 1)
        fact = facts.get((domain, fact_key))
        current = bool(fact) and clock < float(fact.get("observed_at") or 0.0) + int(fact.get("stale_after_seconds") or 0)
        observed = bool(fact) and fact.get("evidence_class") == "observed"
        matches = observed and current and fact.get("value") == expected
        checks.append({
            "requirement": key,
            "expected": expected,
            "fact_present": bool(fact),
            "fact_evidence_class": fact.get("evidence_class") if fact else "unknown",
            "fact_current": current,
            "satisfied_by_current_observation": matches,
        })
    passed = bool(checks) and all(x["satisfied_by_current_observation"] for x in checks)
    return {
        "ok": True,
        "status": "environment_preflight_satisfied" if passed else "environment_preflight_blocked",
        "preflight_passed": passed,
        "checks": checks,
        "assumptions_used_as_authority": False,
        "inferences_used_as_authority": False,
        "unknowns_treated_as_success": False,
        "environment_preflight_is_execution_authority": False,
        **AUTHORITY_FLAGS,
    }



def quarantine_invalid_environment_projection(environment_id: str, *, runtime_root: str | Path | None, now: float | None = None) -> dict[str, Any]:
    """Quarantine malformed environment state; never reconstruct facts from guesses."""
    from environment_awareness_foundations import _path, _read, _root
    path = _path(environment_id, runtime_root)
    if not path.exists():
        return {"ok": False, "status": "environment_projection_missing", **AUTHORITY_FLAGS}
    try:
        row = _read(path)
        if validate_environment_awareness(row).get("ok"):
            return {"ok": True, "status": "environment_projection_valid_no_quarantine", "quarantined": False, **AUTHORITY_FLAGS}
    except Exception:
        pass
    qroot = _root(runtime_root) / "quarantine"
    qroot.mkdir(parents=True, exist_ok=True)
    stamp = int(time.time() if now is None else now)
    target = qroot / f"{environment_id}-{stamp}.json"
    try:
        os.replace(path, target)
    except OSError:
        try:
            shutil.copy2(path, target)
            path.unlink(missing_ok=True)
        except OSError:
            return {"ok": False, "status": "environment_projection_quarantine_failed", **AUTHORITY_FLAGS}
    return {
        "ok": True,
        "status": "environment_projection_quarantined_fresh_observation_required",
        "quarantined": True,
        "facts_reconstructed_from_assumptions": False,
        "fresh_observation_required": True,
        "automatic_external_action_performed": False,
        **AUTHORITY_FLAGS,
    }


def inspect_environment_awareness_health(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    required = [
        "environment_awareness_foundations.py", "environment_awareness.py", "environment_awareness_reliability.py",
        "ownership_concurrency.py", "restart_crash_recovery.py", "long_running_work_sessions.py", "self_development_alpha.py",
    ]
    checks = {name.replace(".py", "_present"): (root / "conscious_agent" / name).is_file() for name in required}
    return {
        "ok": all(checks.values()),
        "status": "environment_awareness_health_ready" if all(checks.values()) else "environment_awareness_health_blocked",
        "checks": checks,
        "native_windows_validation": "desktop_review_required",
        "active_source_modified": False,
        **AUTHORITY_FLAGS,
    }


def build_environment_awareness_operator_handoff(*, source_root: str | Path | None = None) -> dict[str, Any]:
    health = inspect_environment_awareness_health(source_root=source_root)
    return {
        "ok": health.get("ok") is True,
        "contract_version": CONTRACT_VERSION,
        "status": "environment_awareness_operator_handoff_ready" if health.get("ok") else "environment_awareness_operator_handoff_blocked",
        "capabilities": [
            "observed_inferred_assumed_unknown_fact_classes", "privacy_minimized_path_and_configuration_observation",
            "python_environment_observation", "port_state_observation", "permission_observation", "provider_availability_observation",
            "process_state_observation", "resource_limit_observation", "stale_fact_detection", "observed_only_sensitive_preflight",
            "v1273_ownership_lineage_binding",
        ],
        "known_limitations": [
            "provider_availability_requires_an_explicit_local_probe_and_does_not_contact_remote_services_by_default",
            "process_observation_is_bounded_and_does_not_claim_complete_machine_process_inventory",
            "memory_total_is_unknown_without_a_supported_resource_probe",
            "windows_path_shape_is_not_host_os_evidence",
            "native_windows_permissions_long_paths_ports_and_process_state_require_desktop_validation",
            "environment_preflight_never_replaces_exact_stage_authorization",
        ],
        "native_windows_review": [
            "drive_letter_and_unc_paths", "extended_length_long_paths", "ntfs_read_write_permissions", "virtualenv_and_system_python_detection",
            "occupied_and_available_loopback_ports", "local_provider_process_present_absent", "dashboard_and_worker_process_state",
            "cpu_memory_disk_resource_observation", "access_denied_and_sharing_violation_classification", "restart_refreshes_stale_environment_facts",
        ],
        "next_bounded_unit": "v1275 Dependency and Packaging Management",
        "active_source_modified": False,
        **AUTHORITY_FLAGS,
    }


__all__ = [
    "CONTRACT_VERSION", "classify_windows_path_shape", "reconcile_stale_environment_facts", "evaluate_environment_preflight",
    "quarantine_invalid_environment_projection", "inspect_environment_awareness_health", "build_environment_awareness_operator_handoff",
]
