from __future__ import annotations
"""Era 2 / Arc 7 portable test, debugging, and performance intelligence.

Plans evidence and interprets supplied receipts.  It never runs tests, diagnostics,
projects, providers, or performance probes by itself.
"""
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
import math

from project_evidence_store import DENIED_AUTHORITY, atomic_json, digest, evidence_root, read_json, seal, valid
from deep_project_understanding import build_change_impact_reasoning
from performance_regression import build_performance_regression_receipt

CONTRACT_VERSION = "v1675.9"
TEST_KINDS = ("focused", "integration", "regression", "property", "accessibility", "security", "performance")
FAILURE_CLASSES = {"syntax", "import", "assertion", "timeout", "flaky", "environment", "dependency", "performance", "unknown"}


def _plan_path(pid: str, runtime_root=None) -> Path:
    return evidence_root("test_debug_performance_intelligence", runtime_root) / "plans" / f"{pid}.json"


def _debug_path(did: str, runtime_root=None) -> Path:
    return evidence_root("test_debug_performance_intelligence", runtime_root) / "debug" / f"{did}.json"


def _checkpoint_path(cid: str, runtime_root=None) -> Path:
    return evidence_root("test_debug_performance_intelligence", runtime_root) / "checkpoints" / f"{cid}.json"


def _risk_kinds(impact: Mapping[str, Any]) -> set[str]:
    kinds = set((impact.get("impact_kind_counts") or {}).keys())
    out = {"focused", "regression"}
    if int(impact.get("affected_path_count") or 0) > int(impact.get("known_path_count") or 0):
        out.add("integration")
    if kinds & {"schema_or_storage", "configuration"}:
        out.add("property")
    if kinds & {"user_surface"}:
        out.add("accessibility")
    # High uncertainty or configuration/storage surfaces get security review; this is selection, not proof.
    if int(impact.get("uncertainty_count") or 0) or kinds & {"schema_or_storage", "runtime_state", "private_or_secret"}:
        out.add("security")
    if kinds & {"entry_point_candidate", "user_surface", "schema_or_storage"} or int(impact.get("affected_path_count") or 0) >= 5:
        out.add("performance")
    return out


def build_test_intelligence_plan(source_root: str | Path, changed_paths: Iterable[str], *, runtime_root=None) -> dict[str, Any]:
    impact_result = build_change_impact_reasoning(source_root, changed_paths, runtime_root=runtime_root)
    impact = impact_result["impact_analysis"]
    selected_kinds = sorted(_risk_kinds(impact), key=TEST_KINDS.index)
    reasons = []
    for kind in selected_kinds:
        if kind == "focused": reason = "changed_surface"
        elif kind == "regression": reason = "retained_behavior"
        elif kind == "integration": reason = "transitive_callers"
        elif kind == "property": reason = "structured_state_or_configuration"
        elif kind == "accessibility": reason = "user_surface"
        elif kind == "security": reason = "uncertainty_or_sensitive_surface"
        else: reason = "latency_or_resource_sensitive_surface"
        reasons.append({"test_kind": kind, "reason_code": reason})
    pid = "test-plan-" + digest({"impact": impact.get("analysis_id"), "kinds": selected_kinds})[:24]
    row = seal({
        "contract_version": CONTRACT_VERSION,
        "plan_id": pid,
        "workspace_digest": impact.get("workspace_digest"),
        "source_manifest_digest": impact.get("source_manifest_digest"),
        "impact_analysis_id": impact.get("analysis_id"),
        "selected_test_kinds": selected_kinds,
        "selection_reasons": reasons,
        "candidate_test_count": int(impact.get("candidate_test_count") or 0),
        "uncertainty_count": int(impact.get("uncertainty_count") or 0),
        "plan_complete": bool(impact.get("complete")),
        "tests_executed": False,
        "source_modified": False,
        "provider_contacted": False,
        "action_executed": False,
        **DENIED_AUTHORITY,
    })
    atomic_json(_plan_path(pid, runtime_root), row)
    return {"ok": bool(impact_result.get("ok")), "status": "test_intelligence_plan_ready" if impact.get("complete") else "test_intelligence_plan_uncertain", "plan": public_test_plan(row), "action_executed": False, **DENIED_AUTHORITY}


def public_test_plan(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "plan_id": row.get("plan_id"),
        "workspace_digest": row.get("workspace_digest"),
        "source_manifest_digest": row.get("source_manifest_digest"),
        "impact_analysis_id": row.get("impact_analysis_id"),
        "selected_test_kinds": list(row.get("selected_test_kinds") or []),
        "selection_reasons": list(row.get("selection_reasons") or []),
        "candidate_test_count": int(row.get("candidate_test_count") or 0),
        "uncertainty_count": int(row.get("uncertainty_count") or 0),
        "plan_complete": bool(row.get("plan_complete")),
        "tests_executed": False,
        "raw_paths_exposed": False,
        "raw_source_content_exposed": False,
        "read_only": True,
        "action_executed": False,
        **DENIED_AUTHORITY,
    }


def create_debugging_evidence(*, symptom_codes: Sequence[str], hypotheses: Sequence[Mapping[str, Any]], reproduction_steps: Sequence[str] = (), observed_outcomes: Sequence[str] = (), runtime_root=None) -> dict[str, Any]:
    symptoms = sorted({str(x).strip() for x in symptom_codes if str(x).strip()})[:32]
    if not symptoms:
        return {"ok": False, "status": "symptom_evidence_required", "action_executed": False, **DENIED_AUTHORITY}
    rows = []
    for i, h in enumerate(list(hypotheses)[:12]):
        code = str(h.get("hypothesis_code") or f"hypothesis_{i}").strip()
        cause = str(h.get("cause_class") or "unknown").strip().lower()
        supporting = sorted({str(x) for x in h.get("supporting_evidence") or [] if str(x)})[:16]
        disconfirming = sorted({str(x) for x in h.get("disconfirming_evidence") or [] if str(x)})[:16]
        probe = str(h.get("disproof_probe") or "focused_counterexample_probe")
        confidence = str(h.get("confidence") or "medium").lower()
        if confidence not in {"low", "medium", "high"}: confidence = "low"
        rows.append({
            "hypothesis_code": code,
            "cause_class": cause if cause in FAILURE_CLASSES else "unknown",
            "supporting_evidence_digests": [digest(x) for x in supporting],
            "disconfirming_evidence_digests": [digest(x) for x in disconfirming],
            "disproof_probe_digest": digest(probe),
            "confidence": confidence,
            "status": "contradicted" if disconfirming and not supporting else "contested" if disconfirming else "open",
        })
    did = "debug-evidence-" + digest({"symptoms": symptoms, "hypotheses": rows, "repro": [digest(x) for x in reproduction_steps]})[:24]
    row = seal({
        "contract_version": CONTRACT_VERSION,
        "debug_evidence_id": did,
        "symptom_codes": symptoms,
        "hypotheses": rows,
        "reproduction_step_digests": [digest(x) for x in reproduction_steps][:32],
        "observed_outcome_digests": [digest(x) for x in observed_outcomes][:32],
        "counterexamples_preserved": any(x.get("disconfirming_evidence_digests") for x in rows),
        "root_cause_proven": False,
        "diagnostic_executed": False,
        "tests_executed": False,
        "source_modified": False,
        "action_executed": False,
        **DENIED_AUTHORITY,
    })
    atomic_json(_debug_path(did, runtime_root), row)
    return {"ok": bool(rows), "status": "debugging_evidence_ready" if rows else "hypothesis_required", "debugging_evidence": public_debugging_evidence(row), "action_executed": False, **DENIED_AUTHORITY}


def public_debugging_evidence(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "debug_evidence_id": row.get("debug_evidence_id"),
        "symptom_codes": list(row.get("symptom_codes") or []),
        "hypothesis_count": len(row.get("hypotheses") or []),
        "hypothesis_states": {s: sum(1 for x in row.get("hypotheses") or [] if x.get("status") == s) for s in ("open", "contested", "contradicted")},
        "reproduction_step_count": len(row.get("reproduction_step_digests") or []),
        "observed_outcome_count": len(row.get("observed_outcome_digests") or []),
        "counterexamples_preserved": bool(row.get("counterexamples_preserved")),
        "root_cause_proven": False,
        "diagnostic_executed": False,
        "tests_executed": False,
        "raw_reproduction_exposed": False,
        "raw_output_exposed": False,
        "read_only": True,
        "action_executed": False,
        **DENIED_AUTHORITY,
    }


def classify_flakiness(outcomes: Sequence[str]) -> dict[str, Any]:
    rows = [str(x).strip().lower() for x in outcomes if str(x).strip()]
    accepted = [x for x in rows if x in {"pass", "fail", "timeout", "error"}]
    if len(accepted) < 2:
        status = "insufficient_repeated_evidence"
        flaky = False
    else:
        stable = len(set(accepted)) == 1
        flaky = not stable
        status = "flaky_observed" if flaky else "stable_observed"
    return {
        "contract_version": CONTRACT_VERSION,
        "status": status,
        "sample_count": len(accepted),
        "outcome_counts": {x: accepted.count(x) for x in sorted(set(accepted))},
        "flaky_observed": flaky,
        "flaky_root_cause_proven": False,
        "reruns_executed": False,
        "action_executed": False,
        **DENIED_AUTHORITY,
    }


def build_before_after_performance_evidence(metrics_after: Mapping[str, Iterable[float]], *, metrics_before: Mapping[str, Iterable[float]] | None = None) -> dict[str, Any]:
    receipt = build_performance_regression_receipt(metrics_after, baselines=metrics_before or {})
    return {
        "contract_version": CONTRACT_VERSION,
        "ok": bool(receipt.get("ok")),
        "status": "performance_evidence_ready" if receipt.get("ok") else "performance_regression_or_budget_failure",
        "receipt_digest": receipt.get("receipt_digest"),
        "metric_count": len(receipt.get("metrics") or {}),
        "material_regression_count": sum(1 for x in (receipt.get("metrics") or {}).values() if x.get("material_regression")),
        "median_and_p95_used": bool(receipt.get("median_and_p95_used")),
        "single_sample_release_gate": False,
        "measurements_supplied_not_executed": True,
        "automatic_rollback_authorized": False,
        "release_authorized": False,
        "action_executed": False,
        **DENIED_AUTHORITY,
    }


def run_portable_testing_debugging_checkpoint(cases: Sequence[Mapping[str, Any]], *, runtime_root=None) -> dict[str, Any]:
    rows = []
    for case in cases or []:
        root = case.get("root")
        changed = case.get("changed_paths") or []
        plan = build_test_intelligence_plan(root, changed, runtime_root=runtime_root)
        debug = create_debugging_evidence(
            symptom_codes=case.get("symptom_codes") or ["verification_failed"],
            hypotheses=case.get("hypotheses") or [{"hypothesis_code": "unknown", "cause_class": "unknown"}],
            reproduction_steps=case.get("reproduction_steps") or (),
            observed_outcomes=case.get("outcomes") or (),
            runtime_root=runtime_root,
        )
        flaky = classify_flakiness(case.get("outcomes") or ())
        perf = build_before_after_performance_evidence(case.get("metrics_after") or {}, metrics_before=case.get("metrics_before") or {}) if case.get("metrics_after") else None
        checks = {
            "test_plan": bool(plan.get("plan")),
            "debug_evidence": bool(debug.get("debugging_evidence")),
            "uncertainty_truthful": (plan.get("plan") or {}).get("plan_complete") or (plan.get("plan") or {}).get("uncertainty_count", 0) > 0,
            "no_execution": not (plan.get("plan") or {}).get("tests_executed") and not (debug.get("debugging_evidence") or {}).get("diagnostic_executed"),
            "authority_preserved": not (plan.get("plan") or {}).get("standing_authority_granted") and not (debug.get("debugging_evidence") or {}).get("standing_authority_granted"),
        }
        rows.append({"case_digest": digest(case.get("name") or changed), "checks": checks, "score": sum(bool(v) for v in checks.values()) / len(checks), "flaky_status": flaky.get("status"), "performance_status": perf.get("status") if perf else "not_supplied"})
    cid = "test-debug-checkpoint-" + digest(rows)[:24]
    record = seal({
        "contract_version": CONTRACT_VERSION,
        "checkpoint_id": cid,
        "case_count": len(rows),
        "cases": rows,
        "aggregate_score": round(sum(x["score"] for x in rows) / len(rows), 6) if rows else 0.0,
        "portable_only": True,
        "process_behavior_verified": False,
        "ports_verified": False,
        "browser_rendering_verified": False,
        "native_provider_latency_verified": False,
        "native_memory_cpu_verified": False,
        "native_windows_verified": False,
        "action_executed": False,
        **DENIED_AUTHORITY,
    })
    atomic_json(_checkpoint_path(cid, runtime_root), record)
    public = {
        "contract_version": CONTRACT_VERSION,
        "checkpoint_id": cid,
        "case_count": len(rows),
        "aggregate_score": record["aggregate_score"],
        "portable_only": True,
        "native_evidence_deferred": True,
        "native_windows_verified": False,
        "raw_debug_content_exposed": False,
        "action_executed": False,
        **DENIED_AUTHORITY,
    }
    return {"ok": bool(rows) and all(x["score"] >= 0.8 for x in rows), "status": "portable_testing_debugging_checkpoint_ready", "checkpoint": public, "action_executed": False, **DENIED_AUTHORITY}


__all__ = [
    "CONTRACT_VERSION", "TEST_KINDS", "FAILURE_CLASSES",
    "build_test_intelligence_plan", "public_test_plan", "create_debugging_evidence", "public_debugging_evidence",
    "classify_flakiness", "build_before_after_performance_evidence", "run_portable_testing_debugging_checkpoint",
]
