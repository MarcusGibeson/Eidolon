from __future__ import annotations
"""v1370 integrated diagnosis-and-repair checkpoint scorecard."""
import hashlib, json, re
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "v1370.8"
SURFACES = (
    "reproduction_builder", "fault_localization", "root_cause_analysis",
    "repair_proposal", "iterative_repair_loop", "concurrency_diagnosis",
    "data_diagnosis", "provider_diagnosis", "ui_diagnosis",
)
DENIED = {
    "source_mutation_authorized": False,
    "provider_contact_authorized": False,
    "network_authorized": False,
    "release_authorized": False,
    "approval_granted": False,
    "independent_authority_granted": False,
    "repair_execution_authorized": False,
    "application_authorized": False,
}

def _d(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()
    ).hexdigest()

def build_diagnosis_repair_scorecard(
    *,
    source_manifest_digest: str,
    evidence_surfaces: Mapping[str, Mapping[str, Any]],
    benchmark_cases: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if not re.fullmatch(r"[a-f0-9]{64}", str(source_manifest_digest or "")):
        return {"ok": False, "status": "diagnosis_repair_source_lineage_required", "action_executed": False, **DENIED}

    rows = []
    all_surfaces = True
    for name in SURFACES:
        raw = dict(evidence_surfaces.get(name) or {})
        dg = str(raw.get("evidence_digest") or raw.get("record_digest") or "")
        passed = raw.get("passed") is True
        valid = bool(re.fullmatch(r"[a-f0-9]{64}", dg)) and passed
        all_surfaces = all_surfaces and valid
        rows.append({
            "surface": name,
            "evidence_digest": dg if re.fullmatch(r"[a-f0-9]{64}", dg) else "",
            "passed": passed,
            "valid": valid,
        })

    if not benchmark_cases or len(benchmark_cases) > 64:
        return {"ok": False, "status": "diagnosis_repair_benchmark_count_invalid", "action_executed": False, **DENIED}

    cases = []
    seeded = fixed = symptom_only = 0
    seen = set()
    for raw in benchmark_cases:
        cid = str(raw.get("case_id") or "")
        if not re.fullmatch(r"[A-Za-z0-9_.:/-]{1,120}", cid) or cid in seen:
            return {"ok": False, "status": "diagnosis_repair_benchmark_invalid", "action_executed": False, **DENIED}
        seen.add(cid)
        is_seeded = raw.get("seeded_cross_subsystem_defect") is True
        reproduction = raw.get("reproduction_confirmed") is True
        localized = raw.get("fault_localized") is True
        root = raw.get("root_cause_confirmed") is True
        proposal = raw.get("repair_addresses_root_cause") is True
        tested = raw.get("focused_regression_passed") is True
        symptom_absent = raw.get("symptom_absent_after_repair") is True
        trigger_absent = raw.get("root_trigger_absent_after_repair") is True
        no_regression = raw.get("regression_free") is True
        cause_fixed = all((reproduction, localized, root, proposal, tested, symptom_absent, trigger_absent, no_regression))
        if is_seeded:
            seeded += 1
            fixed += int(cause_fixed)
        if symptom_absent and not trigger_absent:
            symptom_only += 1
        cases.append({
            "case_id_digest": _d(cid),
            "seeded_cross_subsystem_defect": is_seeded,
            "reproduction_confirmed": reproduction,
            "fault_localized": localized,
            "root_cause_confirmed": root,
            "repair_addresses_root_cause": proposal,
            "focused_regression_passed": tested,
            "symptom_absent_after_repair": symptom_absent,
            "root_trigger_absent_after_repair": trigger_absent,
            "regression_free": no_regression,
            "cause_fix_verified": cause_fixed,
        })

    benchmark_ok = seeded > 0 and fixed == seeded and symptom_only == 0 and all(
        row["cause_fix_verified"] for row in cases if row["seeded_cross_subsystem_defect"]
    )
    passed = all_surfaces and benchmark_ok
    rec = {
        "contract_version": CONTRACT_VERSION,
        "source_manifest_digest": source_manifest_digest,
        "surface_count": len(rows),
        "surfaces": rows,
        "all_surfaces_valid": all_surfaces,
        "benchmark_case_count": len(cases),
        "benchmark_cases": cases,
        "seeded_cross_subsystem_defect_count": seeded,
        "seeded_root_causes_fixed": fixed,
        "symptom_only_fix_count": symptom_only,
        "root_cause_not_symptom_verified": benchmark_ok,
        "diagnosis_repair_strategy_passed": passed,
        "raw_reports_persisted": False,
        "raw_logs_persisted": False,
        "raw_screenshots_persisted": False,
        "content_free": True,
        "read_only": True,
        "action_executed": False,
        **DENIED,
    }
    rec["record_digest"] = _d(rec)
    return {
        "ok": passed,
        "status": "diagnosis_repair_checkpoint_ready" if passed else "diagnosis_repair_checkpoint_blocked",
        "diagnosis_repair": rec,
        "action_executed": False,
        **DENIED,
    }

def process_diagnosis_repair_control(text: str, *, project_state=None, **_) -> dict[str, Any]:
    if str(text or "").strip().lower() not in {
        "show diagnosis repair checkpoint", "inspect diagnosis repair", "show diagnosis and repair"
    }:
        return {"active": False}
    rec = dict((project_state or {}).get("diagnosis_repair") or {})
    return {
        "active": True,
        "ok": bool(rec),
        "status": "diagnosis_repair_found" if rec else "diagnosis_repair_missing",
        "diagnosis_repair": rec,
        "action_executed": False,
        **DENIED,
    }
