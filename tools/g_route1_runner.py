from __future__ import annotations

"""Governed, resumable G-ROUTE1 benchmark runner.

There is deliberately no live CLI. Provider generation requires a separately
issued execution authorization bound to the final execution-freeze candidate.
"""

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from g_route1_activity import NullRouteActivity
from g_route1_coding_runner import run_isolated_fixture
from g_route1_contract import DATA, canonical_digest, indexed_fixture_gold
from g_route1_execution_contract import (
    EXECUTION_FREEZE_PATH, EXPECTED_CALLS, SCHEDULE_PATH, build_schedule,
    json_digest, load_json, request_body, validate_schedule, verify_fixture_freeze_current,
)
from g_route1_operational import parse_object, validate_operational
from g_route1_persistence import RouteRunStore, TERMINAL, now, verify_terminal_views
from g_route1_provider import ProviderResult, verify_model_receipts
from g_route1_scorer import score
from g_route1_validators import CODING_EVIDENCE_CONTRACT, validate_fixture_output


CONTRACT_VERSION = "g-route1.runner.v1"
GUARDED_PATHS = (
    "experiments/G-ROUTE1-candidate/FIXTURE_VALIDATOR_FREEZE.json",
    "experiments/G-ROUTE1-candidate/EXECUTION_FREEZE_CANDIDATE.json",
    "experiments/G-ROUTE1-candidate/corpus.json",
    "experiments/G-ROUTE1-candidate/gold.json",
    "experiments/G-ROUTE1-candidate/prompt_profiles.json",
    "experiments/G-ROUTE1-candidate/model_bindings.json",
    "experiments/G-ROUTE1-candidate/thresholds.json",
    "experiments/G-ROUTE1-candidate/schedule.json",
    "tools/g_route1_validators.py",
    "tools/g_route1_contract.py",
    "tools/g_route1_execution_contract.py",
    "tools/g_route1_operational.py",
    "tools/g_route1_coding_runner.py",
    "tools/g_route1_persistence.py",
    "tools/g_route1_activity.py",
    "tools/g_route1_provider.py",
    "tools/g_route1_scorer.py",
    "tools/g_route1_runner.py",
)


def utc_run_id() -> str:
    return "groute1_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def guarded_dependency_digest(root: Path | None = None, paths: tuple[str, ...] = GUARDED_PATHS) -> str:
    base = root or Path(__file__).resolve().parents[1]
    entries = []
    for relative in paths:
        path = base / relative
        if not path.is_file():
            raise FileNotFoundError(f"guarded_dependency_missing:{relative}")
        entries.append({"path": relative, "sha256": canonical_digest(path.read_bytes())})
    return json_digest(entries)


def verify_checked_schedule() -> list[dict[str, Any]]:
    checked = load_json(SCHEDULE_PATH)
    rows = list(checked.get("calls") or [])
    validate_schedule(rows)
    generated = [asdict(row) for row in build_schedule()]
    if rows != generated or checked.get("schedule_content_sha256") != json_digest(rows):
        raise ValueError("checked_schedule_drift")
    return rows


def execution_authorized(authorization: Mapping[str, Any] | None) -> bool:
    row = dict(authorization or {})
    if not EXECUTION_FREEZE_PATH.is_file():
        return False
    manifest = load_json(EXECUTION_FREEZE_PATH)
    digest = json_digest(manifest)
    try:
        from g_route1_execution_freeze import verify_manifest
        freeze_valid = verify_manifest(manifest)["valid"]
    except Exception:
        freeze_valid = False
    return (
        row.get("benchmark_id") == "G-ROUTE1"
        and row.get("execution_freeze_sha256") == digest
        and row.get("benchmark_execution_authorized") is True
        and row.get("provider_generation_authorized") is True
        and row.get("one_execution_only") is True
        and row.get("consumed") is False
        and row.get("operator_confirmation") == f"Authorize G-ROUTE1 execution {digest}"
        and freeze_valid
        and manifest.get("status") == "READY_FOR_EXPLICIT_SCIENTIFIC_EXECUTION_AUTHORIZATION"
        and manifest.get("benchmark_execution_authorized") is False
    )


def _result(value: ProviderResult | Mapping[str, Any]) -> dict[str, Any]:
    return value.as_dict() if isinstance(value, ProviderResult) else dict(value)


def _failed_coding_evidence(fixture: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "producer_contract": CODING_EVIDENCE_CONTRACT, "fixture_id": fixture["fixture_id"],
        "candidate_sha256": canonical_digest(""),
        "focused_test_sha256": canonical_digest(fixture["input"]["focused_test"]),
        "isolated": True, "compile_pass": False, "tests_pass": False,
        "test_exit_code": 1, "test_count": 0,
    }


def execute(
    *, provider_call: Callable[[str, Mapping[str, Any]], ProviderResult | Mapping[str, Any]],
    model_receipts: list[Mapping[str, Any]], run_root: str | Path,
    run_id: str | None = None, activity: Any | None = None,
    authorization: Mapping[str, Any] | None = None, synthetic_fixture: bool = False,
    resume: bool = False, control: Callable[[], str] | None = None,
    guarded_root: Path | None = None,
) -> dict[str, Any]:
    if not synthetic_fixture and not execution_authorized(authorization):
        raise PermissionError("g_route1_execution_not_authorized")
    verify_fixture_freeze_current()
    receipts = verify_model_receipts(model_receipts)
    if not receipts["valid"]:
        raise ValueError("g_route1_model_preflight_rejected:" + ",".join(receipts["reasons"]))
    schedule = verify_checked_schedule()
    guarded = guarded_dependency_digest(guarded_root)
    fixture_gold = indexed_fixture_gold()
    activity = activity or NullRouteActivity()
    resolved_id = run_id or utc_run_id()
    store = RouteRunStore(
        run_root, resolved_id, create=not resume,
        manifest={
            "benchmark_id": "G-ROUTE1", "runner_contract": CONTRACT_VERSION,
            "schedule_sha256": json_digest(schedule), "guarded_digest": guarded,
            "execution_freeze_sha256": json_digest(load_json(EXECUTION_FREEZE_PATH)) if EXECUTION_FREEZE_PATH.is_file() else "",
            "synthetic_fixture": bool(synthetic_fixture), "authorization_present": bool(authorization),
        } if not resume else None,
    )
    if resume and store.manifest().get("state") in TERMINAL:
        raise ValueError("terminal_route_run_not_resumable")
    checkpoint = store.checkpoint()
    if checkpoint["guarded_digest"] != guarded:
        raise ValueError("resume_dependency_drift")
    existing = store.call_records()
    if [row["schedule_position"] for row in existing] != list(range(1, len(existing) + 1)):
        raise ValueError("resume_record_sequence_mismatch")
    start_position = int(checkpoint["next_position"])
    counts = {
        "completed": len(existing), "provider_contacts": sum(bool(row.get("provider_contacted")) for row in existing),
        "structural_failures": sum(not row["operational_validation"]["structural_valid"] for row in existing),
    }
    activity.emit(
        "benchmark_prepared", state="running", stage="collection",
        units=(counts["completed"], EXPECTED_CALLS, "calls"),
        metrics={"scheduled_calls": EXPECTED_CALLS, "calls_completed": counts["completed"],
                 "provider_contacts": counts["provider_contacts"], "structural_failures": counts["structural_failures"],
                 "active_elapsed_seconds": 0, "checkpoint_position": start_position},
    )
    store.update(state="running")
    with store.lease():
        for scheduled in schedule[start_position - 1:]:
            if guarded_dependency_digest(guarded_root) != guarded:
                store.finish(state="incomplete", reason="guarded_dependency_drift", valid_verdict=False)
                raise RuntimeError("guarded_dependency_drift")
            command = control() if control else "continue"
            if command == "pause":
                store.update(state="paused")
                store.write_checkpoint(next_position=scheduled["position"], state="paused", guarded_digest=guarded)
                activity.emit(
                    "benchmark_paused", state="paused", stage="collection",
                    units=(counts["completed"], EXPECTED_CALLS, "calls"),
                    metrics={"scheduled_calls": EXPECTED_CALLS, "calls_completed": counts["completed"],
                             "provider_contacts": counts["provider_contacts"], "structural_failures": counts["structural_failures"],
                             "active_elapsed_seconds": 0, "checkpoint_position": scheduled["position"]},
                )
                return {"state": "paused", "run_id": resolved_id, "calls_completed": counts["completed"]}
            if command == "cancel":
                store.finish(state="cancelled", reason="operator_cancelled", valid_verdict=False)
                activity.emit("benchmark_cancelled", state="cancelled", stage="finalization", units=(counts["completed"], EXPECTED_CALLS, "calls"))
                return {"state": "cancelled", "run_id": resolved_id, "calls_completed": counts["completed"]}

            fixture, gold = fixture_gold[scheduled["fixture_id"]]
            body = request_body(fixture, scheduled)
            prompt = {"system": body["system"], "prompt": body["prompt"]}
            activity.emit(
                "benchmark_call_starting", state="running", stage="collection",
                units=(counts["completed"], EXPECTED_CALLS, "calls"),
                identities={"current_model_tier": scheduled["model_tier"],
                            "current_task_class": scheduled["task_class"],
                            "current_fixture_id": scheduled["fixture_id"]},
                metrics={"scheduled_calls": EXPECTED_CALLS, "calls_completed": counts["completed"],
                         "provider_contacts": counts["provider_contacts"], "structural_failures": counts["structural_failures"],
                         "active_elapsed_seconds": 0, "checkpoint_position": scheduled["position"]},
            )
            try:
                result = _result(provider_call(scheduled["call_id"], body))
            except Exception as exc:
                reason = f"provider_boundary_exception:{type(exc).__name__}:{exc}"[:500]
                store.write_failure({
                    "failure_type": "infrastructure_failure", "reason": reason,
                    "call_id": scheduled["call_id"], "schedule_position": scheduled["position"],
                    "request_body_sha256": json_digest(body), "provider_contact_status": "unknown",
                    "belief_effects": "none",
                })
                store.finish(state="incomplete", reason=reason, valid_verdict=False)
                activity.emit("benchmark_incomplete", state="incomplete", stage="finalization", units=(counts["completed"], EXPECTED_CALLS, "calls"))
                return {"state": "incomplete", "reason": reason, "run_id": resolved_id, "calls_completed": counts["completed"]}
            if result.get("provider_contacted"):
                counts["provider_contacts"] += 1
            infrastructure_failure = str(result.get("error") or "")
            if result.get("returned_model") != scheduled["model"]:
                infrastructure_failure = infrastructure_failure or "provider_model_fallback_or_mismatch"
            raw_output = result.get("raw_output")
            coding_evidence = None
            if fixture["validator_profile"] == "coding.v1":
                try:
                    coding_evidence = run_isolated_fixture(fixture, raw_output)
                except Exception:
                    coding_evidence = _failed_coding_evidence(fixture)
            operational = validate_operational(fixture, raw_output, execution_evidence=coding_evidence)
            semantic = validate_fixture_output(fixture, gold, raw_output, execution_evidence=coding_evidence)
            false_clean = bool(operational["accepted"] and not semantic["hard_gate_pass"])
            metrics = dict(result.get("metrics") or {})
            eval_count = metrics.get("eval_count")
            latency = float(result.get("latency_seconds") or 0.0)
            record = {
                **scheduled, "schedule_position": scheduled["position"],
                "request": prompt, "request_body_sha256": json_digest(body),
                "raw_provider_body_b64": str(result.get("raw_body_b64") or ""),
                "raw_provider_body_sha256": str(result.get("raw_body_sha256") or ""),
                "raw_provider_envelope": result.get("envelope"),
                "raw_output": raw_output, "output_field": str(result.get("output_field") or ""),
                "parsed_output": operational.get("parsed_output"),
                "operational_validation": operational, "semantic_evaluation": semantic,
                "coding_execution_evidence": coding_evidence,
                "false_clean": false_clean, "infrastructure_failure": infrastructure_failure,
                "requested_model": scheduled["model"], "returned_model": result.get("returned_model"),
                "provider_contacted": bool(result.get("provider_contacted")),
                "provider_metrics": metrics, "latency_seconds": latency,
                "tokens_per_second": round(float(eval_count) / latency, 6) if eval_count and latency > 0 else None,
                "gold_linkage": {"gold_id": "G-ROUTE1-GOLD-R1", "fixture_id": fixture["fixture_id"]},
                "mutation_guard": {"status": "passed", "guarded_digest": guarded},
                "belief_effects": "none", "production_routing_invoked": False,
            }
            store.write_call(record)
            counts["completed"] += 1
            counts["structural_failures"] += int(not operational["structural_valid"])
            store.write_checkpoint(next_position=scheduled["position"] + 1, state="running", guarded_digest=guarded)
            activity.emit(
                "benchmark_call_persisted", state="running", stage="collection",
                units=(counts["completed"], EXPECTED_CALLS, "calls"),
                identities={"current_model_tier": scheduled["model_tier"],
                            "current_task_class": scheduled["task_class"],
                            "current_fixture_id": scheduled["fixture_id"]},
                metrics={"scheduled_calls": EXPECTED_CALLS, "calls_completed": counts["completed"],
                         "provider_contacts": counts["provider_contacts"], "structural_failures": counts["structural_failures"],
                         "active_elapsed_seconds": 0, "checkpoint_position": scheduled["position"] + 1},
            )
            if infrastructure_failure:
                store.finish(state="incomplete", reason=infrastructure_failure, valid_verdict=False)
                activity.emit("benchmark_incomplete", state="incomplete", stage="finalization", units=(counts["completed"], EXPECTED_CALLS, "calls"))
                return {"state": "incomplete", "reason": infrastructure_failure, "run_id": resolved_id, "calls_completed": counts["completed"]}

        activity.emit("benchmark_scoring", state="running", stage="scoring", units=(EXPECTED_CALLS, EXPECTED_CALLS, "calls"))
        records = store.call_records()
        try:
            report = score(records)
            store.write_score(report)
        except Exception as exc:
            reason = f"scorer_integrity_failure:{type(exc).__name__}:{exc}"[:500]
            store.write_failure({"failure_type": "scorer_integrity_failure", "reason": reason, "belief_effects": "none"})
            store.finish(state="failed", reason=reason, valid_verdict=False)
            activity.emit("benchmark_failed", state="failed", stage="finalization", units=(len(records), EXPECTED_CALLS, "calls"))
            return {"state": "failed", "reason": reason, "run_id": resolved_id, "calls_completed": len(records)}
        if guarded_dependency_digest(guarded_root) != guarded:
            store.finish(state="incomplete", reason="post_run_dependency_drift", valid_verdict=False)
            raise RuntimeError("post_run_dependency_drift")
        if not report["valid_completed_report"]:
            store.finish(state="incomplete", reason="scorer_denominator_incomplete", valid_verdict=False)
            return {"state": "incomplete", "run_id": resolved_id, "calls_completed": len(records)}
        terminal_receipt = {
            "contract_version": "g-route1.terminal-receipt.v1",
            "run_id": resolved_id, "state": "complete", "result_state": "complete",
            "calls_persisted": len(records), "completed_position": EXPECTED_CALLS,
            "next_position": EXPECTED_CALLS + 1,
            "score_record_sha256": store.score_record()["record_sha256"],
            "guarded_digest": guarded, "mutation_guard": "passed",
            "production_routing_invoked": False, "belief_effects": "none",
            "completed": now(),
        }
        store.write_terminal_receipt(terminal_receipt)
        store.finish(state="complete", reason="completed_and_scored", valid_verdict=True)
        activity_projection = activity.emit(
            "benchmark_complete", state="complete", stage="finalization",
            units=(EXPECTED_CALLS, EXPECTED_CALLS, "calls"),
        )
        store.seal_terminal_checkpoint(
            state="complete", expected_calls=EXPECTED_CALLS,
            activity_state=str((activity_projection or {}).get("state") or ""),
        )
        terminal_views = verify_terminal_views(
            store, activity_projection or {}, expected_calls=EXPECTED_CALLS,
        )
        if not terminal_views["valid"]:
            raise RuntimeError("route_terminal_view_mismatch:" + ",".join(terminal_views["reasons"]))
        return {
            "state": "complete", "run_id": resolved_id, "calls_completed": len(records),
            "score": report, "terminal_views": terminal_views,
        }


__all__ = [
    "CONTRACT_VERSION", "GUARDED_PATHS", "execute", "execution_authorized",
    "guarded_dependency_digest", "verify_checked_schedule",
]
