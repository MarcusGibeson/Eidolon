from __future__ import annotations

"""Governed two-phase G-ROUTE3 runner with a hard qualification boundary.

Phase A collects the qualification corpus. Its table is built and frozen by a separate
governed step after an audit. Phase B refuses to start unless that frozen table exists,
verifies by digest, traces to a complete Phase A run, and is named in a second operator
authorization. Collection never loads gold for either corpus.
"""

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any, Callable, Mapping

from g_route1_coding_runner import run_isolated_fixture
from g_route1_contract import ROOT, canonical_digest
from g_route1_persistence import RouteRunStore, TERMINAL, now, verify_terminal_views
from g_route1_provider import ProviderResult
from g_route1_validators import CODING_EVIDENCE_CONTRACT
from g_route2_normalization import normalize
from g_route3_contract import (EXECUTION_FREEZE_PATH, EXPECTED_CALLS, QUALIFICATION_TABLE_PATH, json_digest,
                               load_json, request_body, runtime_fixtures, verify_checked_schedule)
import json
import subprocess

MODEL_CAUSED_CODING_ERRORS = (ValueError, SyntaxError, json.JSONDecodeError, subprocess.TimeoutExpired)


def json_dumps(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True)

CONTRACT_VERSION = "g-route3.runner.v1"
BENCHMARK_ID = "G-ROUTE3"
GUARDED_PATHS = (
    "experiments/G-ROUTE3-candidate/model_bindings.json",
    "experiments/G-ROUTE3-candidate/thresholds.json",
    "experiments/G-ROUTE3-candidate/schedule_a.json",
    "experiments/G-ROUTE3-candidate/schedule_b.json",
    "experiments/G-ROUTE3-candidate/corpus_a.json",
    "experiments/G-ROUTE3-candidate/corpus_b.json",
    "experiments/G-ROUTE3-candidate/gold_a.json",
    "experiments/G-ROUTE3-candidate/gold_b.json",
    "experiments/G-ROUTE1-candidate/prompt_profiles.json",
    "tools/g_route1_validators.py", "tools/g_route1_operational.py", "tools/g_route1_coding_runner.py",
    "tools/g_route1_persistence.py", "tools/g_route1_provider.py", "tools/g_route2_normalization.py",
    "tools/g_route3_operational.py", "tools/g_route3_triggers.py",
    "tools/g_route3_contract.py", "tools/g_route3_qualification.py",
    "tools/g_route3_routing.py", "tools/g_route3_validation.py", "tools/g_route3_runner.py",
)
TABLE_RELATIVE = "experiments/G-ROUTE3-candidate/QUALIFICATION_TABLE.json"
ALLOWED_METRICS = frozenset({"scheduled_calls", "calls_completed", "provider_contacts", "structural_failures",
                             "normalized_outputs", "checkpoint_position"})
ALLOWED_IDENTITIES = frozenset({"current_model_tier", "current_task_class", "current_fixture_id", "phase"})


def utc_run_id(phase: str) -> str:
    return f"groute3{phase.lower()}_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def guarded_dependency_digest(*, include_table: bool, root: Path | None = None) -> str:
    """Digest of every frozen dependency, the execution freeze and, in phase B, the table."""
    base = root or ROOT
    entries = []
    for relative in GUARDED_PATHS:
        path = base / relative
        if not path.is_file():
            raise FileNotFoundError(f"guarded_dependency_missing:{relative}")
        entries.append({"path": relative, "sha256": canonical_digest(path.read_bytes())})
    entries.append({"path": "execution_freeze", "sha256": _freeze_digest()})
    if include_table:
        if not QUALIFICATION_TABLE_PATH.is_file():
            raise FileNotFoundError("guarded_dependency_missing:qualification_table")
        entries.append({"path": TABLE_RELATIVE, "sha256": canonical_digest(QUALIFICATION_TABLE_PATH.read_bytes())})
    return json_digest(entries)


def _freeze_digest() -> str:
    return json_digest(load_json(EXECUTION_FREEZE_PATH)) if EXECUTION_FREEZE_PATH.is_file() else ""


def _freeze_valid() -> bool:
    try:
        from g_route3_freeze import verify_manifest
        manifest = load_json(EXECUTION_FREEZE_PATH)
        return (verify_manifest(manifest)["valid"]
                and manifest.get("status") == "READY_FOR_EXPLICIT_SCIENTIFIC_EXECUTION_AUTHORIZATION")
    except Exception:
        return False


def phase_a_authorized(authorization: Mapping[str, Any] | None) -> bool:
    row = dict(authorization or {})
    digest = _freeze_digest() if EXECUTION_FREEZE_PATH.is_file() else ""
    return (bool(digest) and row.get("benchmark_id") == BENCHMARK_ID and row.get("phase") == "A"
            and row.get("execution_freeze_sha256") == digest and row.get("one_execution_only") is True
            and row.get("consumed") is False
            and row.get("operator_confirmation") == f"Authorize G-ROUTE3 phase A execution {digest}"
            and _freeze_valid())


def phase_a_attempts(phase_a_root: Path) -> list[dict[str, Any]]:
    """Every Phase A run directory, so a table cannot quietly come from the best of several attempts."""
    root = Path(phase_a_root)
    rows = []
    if root.is_dir():
        for run_dir in sorted(p for p in root.iterdir() if p.is_dir()):
            manifest_path = run_dir / "run.json"
            if manifest_path.is_file():
                manifest = load_json(manifest_path)
                rows.append({"run_id": run_dir.name, "state": manifest.get("state"),
                             "synthetic_fixture": bool(manifest.get("synthetic_fixture")),
                             "calls_persisted": manifest.get("calls_persisted")})
    return rows


def phase_b_preconditions(phase_a_root: Path, phase_a_run_id: str, *, allow_synthetic_phase_a: bool = False) -> dict[str, Any]:
    """Every condition that must hold before Corpus B may be contacted at all."""
    from g_route3_qualification import qualify, verify_table

    reasons = []
    if not QUALIFICATION_TABLE_PATH.is_file():
        return {"valid": False, "reasons": ["qualification_table_not_frozen"], "table_sha256": None}
    table = load_json(QUALIFICATION_TABLE_PATH)
    reasons += verify_table(table)["reasons"]
    source = table.get("source", {})
    try:
        store = RouteRunStore(phase_a_root, phase_a_run_id, create=False)
        manifest = store.manifest()
        score = store.score_record()
        if manifest.get("state") != "complete" or manifest.get("phase") != "A":
            reasons.append("phase_a_not_complete")
        if manifest.get("synthetic_fixture") and not allow_synthetic_phase_a:
            reasons.append("phase_a_was_synthetic")
        if manifest.get("execution_freeze_sha256") != _freeze_digest():
            reasons.append("phase_a_ran_under_a_different_freeze")
        if score["record_sha256"] != source.get("score_record_sha256"):
            reasons.append("table_not_derived_from_this_phase_a_score")
        if score.get("cells") != table.get("cells"):
            reasons.append("table_cells_differ_from_sealed_phase_a_score")
        if source.get("run_id") != phase_a_run_id:
            reasons.append("table_run_mismatch")
        if source.get("phase_a_attempts") != phase_a_attempts(phase_a_root):
            reasons.append("phase_a_attempts_not_fully_disclosed")
    except Exception as exc:
        reasons.append(f"phase_a_unverifiable:{type(exc).__name__}")
    if source.get("execution_freeze_binding") != _freeze_digest():
        reasons.append("table_bound_to_different_freeze")
    return {"valid": not reasons, "reasons": sorted(set(reasons)), "table_sha256": table.get("table_sha256")}


def consume_authorization(run_root: Path, phase: str, authorization: Mapping[str, Any], run_id: str) -> Path:
    """Record that a one-shot authorization has been used. A second use is refused."""
    digest = json_digest(dict(authorization))
    path = Path(run_root) / f"authorization-{phase}-{digest[:24]}.consumed.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json_dumps({"phase": phase, "authorization_sha256": digest, "run_id": run_id}))
    except FileExistsError:
        existing = load_json(path)
        if existing.get("run_id") != run_id:
            raise PermissionError("authorization_already_consumed")
    return path


def phase_b_authorized(authorization: Mapping[str, Any] | None, phase_a_root: Path, phase_a_run_id: str) -> bool:
    row = dict(authorization or {})
    pre = phase_b_preconditions(phase_a_root, phase_a_run_id, allow_synthetic_phase_a=False)
    digest = _freeze_digest()
    table_digest = pre.get("table_sha256")
    return (pre["valid"] and row.get("benchmark_id") == BENCHMARK_ID and row.get("phase") == "B"
            and row.get("execution_freeze_sha256") == digest and row.get("qualification_table_sha256") == table_digest
            and row.get("one_execution_only") is True and row.get("consumed") is False
            and row.get("operator_confirmation") == f"Authorize G-ROUTE3 phase B execution {digest} table {table_digest}"
            and _freeze_valid())


class RouteThreeActivity:
    def __init__(self, run_id: str, *, phase: str, root: str | Path, resume: bool = False) -> None:
        source = ROOT / "conscious_agent"
        if str(source) not in sys.path:
            sys.path.insert(0, str(source))
        from activity import Activity

        if resume:
            self.activity = Activity.reopen(run_id, root=root)
        else:
            self.activity = Activity(
                run_id, "adaptive_cognitive_routing_benchmark",
                f"Out-of-sample qualification routing, phase {phase}", BENCHMARK_ID, root=root,
                stages=("preparing", "collection", "scoring", "finalization"),
                identities={"benchmark_id": BENCHMARK_ID, "run_id": run_id, "phase": phase},
                governance={"operational_telemetry_only": True, "production_routing": False,
                            "execution_authority": "external_explicit_authorization_required",
                            "belief_effects": "none"})

    def emit(self, event: str, **kwargs: Any) -> dict[str, Any]:
        metrics = dict(kwargs.pop("metrics", {}) or {})
        identities = dict(kwargs.pop("identities", {}) or {})
        if set(metrics) - ALLOWED_METRICS or set(identities) - ALLOWED_IDENTITIES:
            raise ValueError("route_activity_field_not_allowed")
        return self.activity.update(str(event)[:100], metrics=metrics or None, identities=identities or None, **kwargs)


class NullActivity:
    def __init__(self) -> None:
        self.state = "queued"

    def emit(self, event: str, **kwargs: Any) -> dict[str, Any]:
        self.state = str(kwargs.get("state") or self.state)
        return {"state": self.state}


def _failed_coding_evidence(fixture: Mapping[str, Any]) -> dict[str, Any]:
    return {"producer_contract": CODING_EVIDENCE_CONTRACT, "fixture_id": fixture["fixture_id"],
            "candidate_sha256": canonical_digest(""),
            "focused_test_sha256": canonical_digest(fixture["input"]["focused_test"]),
            "isolated": True, "compile_pass": False, "tests_pass": False, "test_exit_code": 1, "test_count": 0}


def _collect(*, phase: str, provider_call, model_receipts, run_root, run_id, activity, control, guarded_root,
             resume, include_table, manifest_extra) -> dict[str, Any]:
    from g_route1_provider import verify_model_receipts
    from g_route3_qualification import collect_evaluation

    receipts = verify_model_receipts(model_receipts)
    if not receipts["valid"]:
        raise ValueError("g_route3_model_preflight_rejected:" + ",".join(receipts["reasons"]))
    schedule = verify_checked_schedule(phase)
    fixtures = runtime_fixtures(phase)
    guarded = guarded_dependency_digest(include_table=include_table, root=guarded_root)
    activity = activity or NullActivity()
    expected = EXPECTED_CALLS[phase]
    store = RouteRunStore(run_root, run_id, create=not resume, manifest={
        "benchmark_id": BENCHMARK_ID, "phase": phase, "runner_contract": CONTRACT_VERSION,
        "expected_calls": expected, "schedule_sha256": json_digest(schedule), "guarded_digest": guarded,
        "execution_freeze_sha256": _freeze_digest(), "gold_loaded_during_collection": False,
        **manifest_extra} if not resume else None)
    if resume and store.manifest().get("state") in TERMINAL:
        raise ValueError("terminal_route_run_not_resumable")
    checkpoint = store.checkpoint()
    if checkpoint["guarded_digest"] != guarded:
        raise ValueError("resume_dependency_drift")
    existing = store.call_records()
    if [r["schedule_position"] for r in existing] != list(range(1, len(existing) + 1)):
        raise ValueError("resume_record_sequence_mismatch")
    counts = {"completed": len(existing), "provider_contacts": sum(bool(r.get("provider_contacted")) for r in existing),
              "structural_failures": sum(not r["normalized_operational_validation"]["structural_valid"] for r in existing),
              "normalized": sum(bool(r["normalization"]["normalized"]) for r in existing)}

    def telemetry(position: int) -> dict[str, Any]:
        return {"scheduled_calls": expected, "calls_completed": counts["completed"],
                "provider_contacts": counts["provider_contacts"], "structural_failures": counts["structural_failures"],
                "normalized_outputs": counts["normalized"], "checkpoint_position": position}

    activity.emit("benchmark_prepared", state="running", stage="collection",
                  units=(counts["completed"], expected, "calls"), metrics=telemetry(int(checkpoint["next_position"])))
    store.update(state="running")
    with store.lease():
        for scheduled in schedule[int(checkpoint["next_position"]) - 1:]:
            if guarded_dependency_digest(include_table=include_table, root=guarded_root) != guarded:
                store.finish(state="incomplete", reason="guarded_dependency_drift", valid_verdict=False)
                raise RuntimeError("guarded_dependency_drift")
            command = control() if control else "continue"
            if command == "pause":
                store.update(state="paused")
                store.write_checkpoint(next_position=scheduled["position"], state="paused", guarded_digest=guarded)
                activity.emit("benchmark_paused", state="paused", stage="collection",
                              units=(counts["completed"], expected, "calls"), metrics=telemetry(scheduled["position"]))
                return {"state": "paused", "run_id": run_id, "calls_completed": counts["completed"]}
            if command == "cancel":
                store.finish(state="cancelled", reason="operator_cancelled", valid_verdict=False)
                activity.emit("benchmark_cancelled", state="cancelled", stage="finalization",
                              units=(counts["completed"], expected, "calls"))
                return {"state": "cancelled", "run_id": run_id, "calls_completed": counts["completed"]}
            fixture = fixtures[scheduled["fixture_id"]]
            body = request_body(fixture, scheduled)
            activity.emit("benchmark_call_starting", state="running", stage="collection",
                          units=(counts["completed"], expected, "calls"),
                          identities={"phase": phase, "current_model_tier": scheduled["model_tier"],
                                      "current_task_class": scheduled["task_class"],
                                      "current_fixture_id": scheduled["fixture_id"]},
                          metrics=telemetry(scheduled["position"]))
            try:
                result = provider_call(scheduled["call_id"], body)
                result = result.as_dict() if isinstance(result, ProviderResult) else dict(result)
            except Exception as exc:
                reason = f"provider_boundary_exception:{type(exc).__name__}:{exc}"[:500]
                store.write_failure({"failure_type": "infrastructure_failure", "reason": reason,
                                     "call_id": scheduled["call_id"], "schedule_position": scheduled["position"],
                                     "belief_effects": "none"})
                store.finish(state="incomplete", reason=reason, valid_verdict=False)
                activity.emit("benchmark_incomplete", state="incomplete", stage="finalization",
                              units=(counts["completed"], expected, "calls"))
                return {"state": "incomplete", "reason": reason, "run_id": run_id, "calls_completed": counts["completed"]}
            if result.get("provider_contacted"):
                counts["provider_contacts"] += 1
            infrastructure_failure = str(result.get("error") or "")
            if result.get("returned_model") != scheduled["model"]:
                infrastructure_failure = infrastructure_failure or "provider_model_fallback_or_mismatch"
            raw_output = result.get("raw_output")
            canonical = normalize(raw_output, validator_profile=fixture["validator_profile"])
            evidence = None
            if fixture["validator_profile"] == "coding.v1":
                try:
                    evidence = run_isolated_fixture(fixture, canonical["payload"])
                except MODEL_CAUSED_CODING_ERRORS:
                    # malformed answer, disallowed code or a candidate that hangs: the model's failure
                    evidence = _failed_coding_evidence(fixture)
                except Exception as exc:
                    # the sandbox host failed; never charge that to the model
                    evidence = _failed_coding_evidence(fixture)
                    infrastructure_failure = (infrastructure_failure
                                              or f"coding_sandbox_host_failure:{type(exc).__name__}"[:200])
            evaluation = collect_evaluation(fixture, raw_output, evidence)
            metrics = dict(result.get("metrics") or {})
            latency = float(result.get("latency_seconds") or 0.0)
            store.write_call({
                **scheduled, "schedule_position": scheduled["position"],
                "request": {"system": body["system"], "prompt": body["prompt"]},
                "request_body_sha256": json_digest(body),
                "raw_provider_body_b64": str(result.get("raw_body_b64") or ""),
                "raw_provider_body_sha256": str(result.get("raw_body_sha256") or ""),
                "raw_provider_envelope": result.get("envelope"), "raw_output": raw_output,
                **evaluation, "coding_execution_evidence": evidence,
                "infrastructure_failure": infrastructure_failure,
                "requested_model": scheduled["model"], "returned_model": result.get("returned_model"),
                "provider_contacted": bool(result.get("provider_contacted")), "provider_metrics": metrics,
                "latency_seconds": latency,
                "tokens_per_second": round(float(metrics["eval_count"]) / latency, 6)
                if metrics.get("eval_count") and latency > 0 else None,
                "mutation_guard": {"status": "passed", "guarded_digest": guarded},
                "gold_loaded": False, "belief_effects": "none", "production_routing_invoked": False,
            })
            counts["completed"] += 1
            counts["structural_failures"] += int(not evaluation["normalized_operational_validation"]["structural_valid"])
            counts["normalized"] += int(bool(evaluation["normalization"]["normalized"]))
            store.write_checkpoint(next_position=scheduled["position"] + 1, state="running", guarded_digest=guarded)
            activity.emit("benchmark_call_persisted", state="running", stage="collection",
                          units=(counts["completed"], expected, "calls"), metrics=telemetry(scheduled["position"] + 1))
            if infrastructure_failure:
                store.finish(state="incomplete", reason=infrastructure_failure, valid_verdict=False)
                activity.emit("benchmark_incomplete", state="incomplete", stage="finalization",
                              units=(counts["completed"], expected, "calls"))
                return {"state": "incomplete", "reason": infrastructure_failure, "run_id": run_id,
                        "calls_completed": counts["completed"]}
    return {"state": "collected", "run_id": run_id, "store": store, "guarded": guarded, "activity": activity}


def _finish(store, activity, *, phase: str, report: Mapping[str, Any], guarded: str, include_table: bool,
            guarded_root) -> dict[str, Any]:
    expected = EXPECTED_CALLS[phase]
    store.write_score(report)
    if guarded_dependency_digest(include_table=include_table, root=guarded_root) != guarded:
        store.finish(state="incomplete", reason="post_run_dependency_drift", valid_verdict=False)
        raise RuntimeError("post_run_dependency_drift")
    records = store.call_records()
    store.write_terminal_receipt({
        "contract_version": "g-route3.terminal-receipt.v1", "run_id": store.run_id, "phase": phase,
        "state": "complete", "result_state": "complete", "calls_persisted": len(records),
        "completed_position": expected, "next_position": expected + 1,
        "score_record_sha256": store.score_record()["record_sha256"], "guarded_digest": guarded,
        "mutation_guard": "passed", "production_routing_invoked": False, "belief_effects": "none", "completed": now()})
    store.finish(state="complete", reason="completed_and_scored", valid_verdict=True)
    projection = activity.emit("benchmark_complete", state="complete", stage="finalization",
                               units=(expected, expected, "calls"))
    store.seal_terminal_checkpoint(state="complete", expected_calls=expected,
                                   activity_state=str((projection or {}).get("state") or ""))
    views = verify_terminal_views(store, projection or {}, expected_calls=expected)
    if not views["valid"]:
        raise RuntimeError("route_terminal_view_mismatch:" + ",".join(views["reasons"]))
    return {"state": "complete", "run_id": store.run_id, "calls_completed": len(records),
            "score": report, "terminal_views": views}


def execute_phase_a(*, provider_call, model_receipts, run_root, run_id: str | None = None, activity=None,
                    authorization: Mapping[str, Any] | None = None, synthetic_fixture: bool = False,
                    resume: bool = False, control: Callable[[], str] | None = None, guarded_root=None) -> dict[str, Any]:
    if not synthetic_fixture and not phase_a_authorized(authorization):
        raise PermissionError("g_route3_phase_a_not_authorized")
    run_id = run_id or utc_run_id("A")
    if not synthetic_fixture:
        consume_authorization(Path(run_root), "A", authorization or {}, run_id)
    got = _collect(phase="A", provider_call=provider_call, model_receipts=model_receipts, run_root=run_root,
                   run_id=run_id, activity=activity, control=control, guarded_root=guarded_root, resume=resume,
                   include_table=False, manifest_extra={"synthetic_fixture": bool(synthetic_fixture)})
    if got["state"] != "collected":
        return got
    from g_route3_qualification import attach_semantics, qualify

    store, activity = got["store"], got["activity"]
    activity.emit("benchmark_scoring", state="running", stage="scoring",
                  units=(EXPECTED_CALLS["A"], EXPECTED_CALLS["A"], "calls"))
    try:
        judged = attach_semantics(store.call_records(), "A")
        cells = qualify(judged)
        report = {"contract_version": "g-route3.phase-a-score.v1", "phase": "A", "cells": cells,
                  "qualified_cells": sum(c["verdict"] == "qualified" for c in cells),
                  "insufficient_cells": sum(c["verdict"] == "insufficient_evidence" for c in cells),
                  "table_frozen": False, "corpus_b_consulted": False, "belief_effects": "none"}
    except Exception as exc:
        reason = f"scorer_integrity_failure:{type(exc).__name__}:{exc}"[:500]
        store.write_failure({"failure_type": "scorer_integrity_failure", "reason": reason, "belief_effects": "none"})
        store.finish(state="failed", reason=reason, valid_verdict=False)
        return {"state": "failed", "reason": reason, "run_id": run_id}
    return _finish(store, activity, phase="A", report=report, guarded=got["guarded"], include_table=False,
                   guarded_root=guarded_root)


def execute_phase_b(*, provider_call, model_receipts, run_root, phase_a_root, phase_a_run_id: str,
                    run_id: str | None = None, activity=None, authorization: Mapping[str, Any] | None = None,
                    synthetic_fixture: bool = False, resume: bool = False,
                    control: Callable[[], str] | None = None, guarded_root=None) -> dict[str, Any]:
    pre = phase_b_preconditions(Path(phase_a_root), phase_a_run_id, allow_synthetic_phase_a=synthetic_fixture)
    if not pre["valid"]:
        raise PermissionError("g_route3_phase_b_blocked:" + ",".join(pre["reasons"]))
    if not synthetic_fixture and not phase_b_authorized(authorization, Path(phase_a_root), phase_a_run_id):
        raise PermissionError("g_route3_phase_b_not_authorized")
    run_id = run_id or utc_run_id("B")
    if not synthetic_fixture:
        consume_authorization(Path(run_root), "B", authorization or {}, run_id)
    got = _collect(phase="B", provider_call=provider_call, model_receipts=model_receipts, run_root=run_root,
                   run_id=run_id, activity=activity, control=control, guarded_root=guarded_root, resume=resume,
                   include_table=True, manifest_extra={"synthetic_fixture": bool(synthetic_fixture),
                                                       "qualification_table_sha256": pre["table_sha256"],
                                                       "phase_a_run_id": phase_a_run_id})
    if got["state"] != "collected":
        return got
    from g_route3_qualification import load_frozen_table
    from g_route3_validation import score

    store, activity = got["store"], got["activity"]
    table = load_frozen_table(QUALIFICATION_TABLE_PATH)
    if table["table_sha256"] != pre["table_sha256"]:
        store.finish(state="incomplete", reason="qualification_table_mutated", valid_verdict=False)
        raise RuntimeError("qualification_table_mutated")
    activity.emit("benchmark_scoring", state="running", stage="scoring",
                  units=(EXPECTED_CALLS["B"], EXPECTED_CALLS["B"], "calls"))
    try:
        report = score(store.call_records(), table)
    except Exception as exc:
        reason = f"scorer_integrity_failure:{type(exc).__name__}:{exc}"[:500]
        store.write_failure({"failure_type": "scorer_integrity_failure", "reason": reason, "belief_effects": "none"})
        store.finish(state="failed", reason=reason, valid_verdict=False)
        return {"state": "failed", "reason": reason, "run_id": run_id}
    return _finish(store, activity, phase="B", report=report, guarded=got["guarded"], include_table=True,
                   guarded_root=guarded_root)


__all__ = ["CONTRACT_VERSION", "BENCHMARK_ID", "GUARDED_PATHS", "TABLE_RELATIVE", "RouteThreeActivity",
           "NullActivity", "guarded_dependency_digest", "phase_a_authorized", "phase_b_preconditions",
           "phase_a_attempts", "consume_authorization",
           "phase_b_authorized", "execute_phase_a", "execute_phase_b", "utc_run_id"]
