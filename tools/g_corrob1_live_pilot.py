from __future__ import annotations

"""Separately authorized two-call live mechanical-pilot harness.

The harness reuses production G-CORROB1 request, provider, validation,
governance, comparison, persistence, and Activity components. It never loads
gold and never invokes the production scorer.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Mapping

from g_corrob1_contract import (
    BELIEF_EFFECTS, ScheduledCall, canonical_digest, load_sampling, request_receipt,
    semantic_http_body,
)
from g_corrob1_persistence import RunStore
from g_corrob1_pilot_activity import NullPilotActivity, PilotActivity
from g_corrob1_pilot_envelope_freeze import verify_pilot_authorization
from g_corrob1_pilot_verifier import NAMESPACE, load_fixture, verify_pilot_records
from g_corrob1_policy import compare_pair, process_assessment
from g_corrob1_provider import ProviderResult, verify_preflight_receipt
from g_corrob1_provider_envelope import verify_envelope_record
from g_corrob1_runner import _preflight_matches_execution_manifest


CONTRACT_VERSION = "g-corrob1.mechanical-pilot.runner.2"


def utc_run_id() -> str:
    return "gcorrob1pilot_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _result_dict(value: ProviderResult | Mapping[str, Any]) -> dict[str, Any]:
    return value.as_dict() if isinstance(value, ProviderResult) else dict(value)


def _scheduled(row: Mapping[str, Any]) -> ScheduledCall:
    return ScheduledCall(
        call_id=str(row["call_id"]), pair_id=str(row["pair_id"]), item_id=str(row["item_id"]),
        repeat=int(row["repeat"]), role=str(row["role"]), ordinal=int(row["ordinal"]),
        pair_ordinal=int(row["pair_ordinal"]), seed=int(row["seed"]),
    )


def _consume_authorization(run_root: Path, authorization: Mapping[str, Any]) -> Path:
    authorization_id = str(authorization["authorization_id"])
    if not all(ch.isalnum() or ch in "_-" for ch in authorization_id):
        raise ValueError("invalid_pilot_authorization_id")
    path = run_root / "_pilot_authorizations" / f"{authorization_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "authorization_id": authorization_id,
        "pilot_manifest_sha256": authorization["pilot_manifest_sha256"],
        "consumed_for": "one_two_call_mechanical_pilot",
        "experiment_authorized": False,
        "belief_effects": "none",
    }
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, indent=1, sort_keys=True))
    return path


def _preflight_matches_candidate(receipt: Mapping[str, Any], authorization: Mapping[str, Any]) -> bool:
    return _preflight_matches_execution_manifest(
        receipt, {"execution_manifest": dict(authorization.get("pilot_manifest") or {})}
    )


def _write_terminal_receipt(store: RunStore) -> Path:
    manifest = store.manifest()
    score_path = store.root / "score.json"
    seed = {
        "contract_version": "g-corrob1.mechanical-pilot.terminal-receipt.1",
        "run_id": store.run_id,
        "record_namespace": NAMESPACE,
        "pilot_only": True,
        "production_result": False,
        "semantic_evaluation_performed": False,
        "terminal_state": manifest.get("state"),
        "terminal_reason": manifest.get("reason"),
        "run_manifest_sha256": canonical_digest(store.manifest_path.read_bytes()),
        "call_record_sha256": [str(row.get("record_sha256") or "") for row in store.call_records()],
        "provider_envelope_record_sha256": [
            str(row.get("record_sha256") or "") for row in store.provider_envelope_records()
        ],
        "pair_record_sha256": [str(row.get("record_sha256") or "") for row in store.pair_records()],
        "mechanical_report_sha256": (
            canonical_digest(score_path.read_bytes()) if score_path.is_file() else None
        ),
        "pilot_manifest_sha256": manifest.get("pilot_manifest_sha256"),
        "belief_effects": "none",
    }
    seed["receipt_sha256"] = canonical_digest(json.dumps(seed, sort_keys=True, separators=(",", ":")))
    path = store.root / "terminal_receipt.json"
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(seed, indent=1, ensure_ascii=False, sort_keys=True))
        handle.flush()
        os.fsync(handle.fileno())
    return path


def execute(
    *,
    provider_adapter: Any,
    run_root: str | Path,
    run_id: str | None = None,
    activity: Any | None = None,
    authorization: Mapping[str, Any] | None = None,
    synthetic_fixture: bool = False,
) -> dict[str, Any]:
    """Run one two-call pilot through an injected adapter.

    ``synthetic_fixture`` is an offline test seam only. Live execution requires
    exact pilot authorization, which is consumed before provider inspection.
    """
    root = Path(run_root)
    resolved_run_id = run_id or utc_run_id()
    if not resolved_run_id.startswith("gcorrob1pilot_"):
        raise ValueError("pilot_run_id_namespace_mismatch")

    authorization_check = {"valid": True, "reasons": [], "pilot_manifest_sha256": "f" * 64}
    manifest_sha256 = "f" * 64
    if not synthetic_fixture:
        authorization_check = verify_pilot_authorization(authorization)
        if not authorization_check["valid"]:
            raise PermissionError("g_corrob1_pilot_not_authorized:" + ",".join(authorization_check["reasons"]))
        manifest_sha256 = str(authorization_check["pilot_manifest_sha256"])
        _consume_authorization(root, dict(authorization or {}))
    elif authorization and authorization.get("pilot_manifest_sha256"):
        manifest_sha256 = str(authorization["pilot_manifest_sha256"])

    fixture = load_fixture()
    item = dict(fixture["item"])
    schedule = [_scheduled(row) for row in fixture["schedule"]]
    sampling = load_sampling()
    observer = activity or (NullPilotActivity() if synthetic_fixture else PilotActivity(resolved_run_id, root=root / "activity"))

    def emit(event: str, **kwargs: Any) -> None:
        try:
            observer.emit(event, **kwargs)
        except Exception:
            return None

    store = RunStore(
        root / NAMESPACE,
        resolved_run_id,
        create=True,
        run_manifest={
            "candidate_id": "G-CORROB1-pilot-envelope-r4",
            "runner_contract": CONTRACT_VERSION,
            "record_namespace": NAMESPACE,
            "pilot_only": True,
            "production_result": False,
            "semantic_evaluation_performed": False,
            "intended_calls": 2,
            "intended_pairs": 1,
            "pilot_launch_count": 1,
            "experiment_launch_count": 0,
            "pilot_manifest_sha256": manifest_sha256,
            "fixture_sha256": canonical_digest(json.dumps(fixture, sort_keys=True, separators=(",", ":"))),
            "synthetic_fixture": bool(synthetic_fixture),
        },
    )
    counts = {"calls": 0, "A": 0, "B": 0, "pairs": 0, "validations": 0,
              "structural_failures": 0, "extractions": 0, "extraction_failures": 0}
    emit("pilot_preparing", state="preparing", stage="pilot_preparing", metrics={"scheduled_calls": 2})

    try:
        preflight_receipt = dict(provider_adapter.inspect_model(
            sampling["model_name"], allow_provider_contact=not synthetic_fixture
        ))
        preflight = verify_preflight_receipt(preflight_receipt, require_model_digest=True)
        if not preflight["valid"]:
            store.update(preflight=preflight_receipt, preflight_validation=preflight)
            store.finish(state="incomplete", reason="provider_preflight_rejected", valid_verdict=False)
            _write_terminal_receipt(store)
            emit("pilot_incomplete", state="incomplete", stage="finalization", metrics={"scheduled_calls": 2})
            return {"run_id": resolved_run_id, "state": "incomplete", "reason": "provider_preflight_rejected",
                    "store": str(store.root), "mechanical_pass": False}
        if not synthetic_fixture and not _preflight_matches_candidate(preflight_receipt, dict(authorization or {})):
            store.update(preflight=preflight_receipt, preflight_validation=preflight)
            store.finish(state="incomplete", reason="provider_preflight_not_bound_to_pilot_freeze", valid_verdict=False)
            _write_terminal_receipt(store)
            emit("pilot_incomplete", state="incomplete", stage="finalization", metrics={"scheduled_calls": 2})
            return {"run_id": resolved_run_id, "state": "incomplete",
                    "reason": "provider_preflight_not_bound_to_pilot_freeze", "store": str(store.root),
                    "mechanical_pass": False}
        store.update(state="running", preflight=preflight_receipt, preflight_validation=preflight)

        records: dict[str, dict[str, Any]] = {}
        for scheduled in schedule:
            body = semantic_http_body(item, scheduled, sampling)
            request = request_receipt(item, scheduled, sampling)
            emit(
                "pilot_assessment_requested", state="running", stage="assessment_collection",
                units=(counts["calls"], 2, "calls"),
                metrics={"scheduled_calls": 2, "provider_contacts": counts["calls"],
                         "calls_completed": counts["calls"], "A_completed": counts["A"],
                         "B_completed": counts["B"], "pairs_completed": counts["pairs"]},
            )
            result = _result_dict(provider_adapter.generate(
                scheduled.call_id, body, allow_provider_contact=not synthetic_fixture
            ))
            counts["calls"] += 1
            envelope_path = store.write_provider_envelope({
                "call_id": scheduled.call_id,
                "request_id": str(result.get("request_id") or ""),
                "raw_provider_envelope_b64": str(result.get("raw_provider_envelope_b64") or ""),
                "raw_provider_envelope_sha256": str(result.get("raw_provider_envelope_sha256") or ""),
                "provider_envelope": result.get("provider_envelope"),
                "provider_envelope_sha256": str(result.get("provider_envelope_sha256") or ""),
                "provider_contacted": bool(result.get("provider_contacted")),
                "returned_model": str(result.get("returned_model") or ""),
                "metrics": dict(result.get("metrics") or {}),
                "record_kind": "raw_provider_envelope",
                "record_namespace": NAMESPACE,
                "pilot_only": True,
                "production_result": False,
            })
            envelope_record_sha256 = json.loads(envelope_path.read_text(encoding="utf-8"))["record_sha256"]
            envelope_check = verify_envelope_record(result)
            extraction = dict(result.get("output_extraction") or {})
            counts["extractions"] += 1
            counts["extraction_failures"] += int(extraction.get("status") != "success")
            emit(
                "pilot_provider_response_received", state="running", stage="assessment_collection",
                units=(counts["calls"], 2, "calls"),
                metrics={"scheduled_calls": 2, "provider_contacts": counts["calls"],
                         "calls_completed": counts["calls"],
                         "extractions_completed": counts["extractions"],
                         "extraction_failures": counts["extraction_failures"]},
            )
            emit(
                "pilot_output_extraction_succeeded" if extraction.get("status") == "success"
                else "pilot_output_extraction_failed",
                state="running", stage="structural_validation",
                metrics={"scheduled_calls": 2, "provider_contacts": counts["calls"],
                         "calls_completed": counts["calls"],
                         "extractions_completed": counts["extractions"],
                         "extraction_failures": counts["extraction_failures"]},
            )
            binding_reasons = list(envelope_check["reasons"])
            if result.get("request_id") != scheduled.call_id:
                binding_reasons.append("request_binding_mismatch")
            if result.get("submitted_body_sha256") != request["submitted_body_sha256"]:
                binding_reasons.append("submitted_request_digest_mismatch")
            if result.get("returned_model") != sampling["model_name"]:
                binding_reasons.append("returned_model_mismatch_or_fallback")
            metrics = dict(result.get("metrics") or {})
            truncated = bool(result.get("truncated")) or int(metrics.get("eval_count") or 0) >= int(
                sampling["parameters"]["num_predict"]
            )
            processed = process_assessment(
                str(result.get("extracted_model_output") or ""),
                proposition_id=item["proposition_id"], evidence_id=item["evidence_id"],
                evidence_text=item["evidence"], truncated=truncated,
                binding_error=";".join(binding_reasons) if binding_reasons else None,
            )
            provider_error = str(result.get("error") or "")
            record = {
                **scheduled.identity(),
                "record_namespace": NAMESPACE, "pilot_only": True, "production_result": False,
                "semantic_evaluation_performed": False, "request": request,
                "raw_provider_envelope_b64": str(result.get("raw_provider_envelope_b64") or ""),
                "raw_provider_envelope_sha256": str(result.get("raw_provider_envelope_sha256") or ""),
                "provider_envelope": result.get("provider_envelope"),
                "provider_envelope_sha256": str(result.get("provider_envelope_sha256") or ""),
                "extracted_model_output": str(result.get("extracted_model_output") or ""),
                "output_extraction": extraction,
                "provider_envelope_record_sha256": envelope_record_sha256,
                "raw_response": str(result.get("extracted_model_output") or ""),
                "assessment": processed["assessment"], "parse_error": processed["parse_error"],
                "validation": processed["validation"], "disposition": processed["disposition"],
                "rule": processed["rule"], "rules_fired": processed.get("rules_fired") or [],
                "reason": processed["reason"], "belief_effects": BELIEF_EFFECTS,
                "provider_contacted": bool(result.get("provider_contacted")),
                "provider_error": provider_error, "returned_model": str(result.get("returned_model") or ""),
                "metrics": metrics, "seconds": float(result.get("seconds") or 0),
                "truncated": truncated,
                "submitted_body_sha256": str(result.get("submitted_body_sha256") or ""),
                "runner_contract": CONTRACT_VERSION,
            }
            store.write_call(record)
            records[scheduled.role] = record
            counts[scheduled.role] += 1
            counts["validations"] += 1
            counts["structural_failures"] += int(not processed["validation"]["valid"])
            emit(
                "pilot_assessment_preserved", state="running", stage="structural_validation",
                units=(counts["calls"], 2, "calls"),
                metrics={"scheduled_calls": 2, "provider_contacts": counts["calls"],
                         "calls_completed": counts["calls"], "A_completed": counts["A"],
                         "B_completed": counts["B"], "validation_completed": counts["validations"],
                         "structural_failures": counts["structural_failures"], "pairs_completed": counts["pairs"]},
            )
            if provider_error or binding_reasons or extraction.get("status") != "success" or not processed["validation"]["valid"]:
                if provider_error:
                    reason = "provider_failure"
                elif binding_reasons:
                    reason = "provenance_or_binding_failure"
                elif extraction.get("status") != "success":
                    reason = "output_extraction_failure"
                else:
                    reason = "structural_assessment_rejection"
                store.finish(state="incomplete", reason=reason, valid_verdict=False)
                _write_terminal_receipt(store)
                emit("pilot_incomplete", state="incomplete", stage="finalization",
                     metrics={"scheduled_calls": 2, "provider_contacts": counts["calls"],
                              "calls_completed": counts["calls"], "A_completed": counts["A"],
                              "B_completed": counts["B"], "pairs_completed": 0,
                              "structural_failures": counts["structural_failures"]})
                return {"run_id": resolved_run_id, "state": "incomplete", "reason": reason,
                        "store": str(store.root), "mechanical_pass": False}

        if set(records) != {"A", "B"}:
            raise ValueError("pilot_missing_assessor")
        comparison = compare_pair(records["A"], records["B"])
        pair_record = {
            "pair_id": "PX01-r1", "item_id": "PX01", "repeat": 1,
            "record_namespace": NAMESPACE, "pilot_only": True, "production_result": False,
            "semantic_evaluation_performed": False,
            "A_call_id": records["A"]["call_id"], "B_call_id": records["B"]["call_id"],
            **comparison,
        }
        store.write_pair(pair_record)
        counts["pairs"] = 1
        emit("pilot_pair_compared", state="running", stage="paired_comparison", units=(1, 1, "pairs"),
             metrics={"scheduled_calls": 2, "provider_contacts": counts["calls"], "calls_completed": 2,
                      "A_completed": 1, "B_completed": 1, "pairs_completed": 1,
                      "comparisons_completed": 1, "structural_failures": counts["structural_failures"]})

        emit("pilot_mechanical_verification", state="running", stage="mechanical_verification",
             metrics={"scheduled_calls": 2, "provider_contacts": counts["calls"], "calls_completed": 2,
                      "A_completed": 1, "B_completed": 1, "pairs_completed": 1,
                      "comparisons_completed": 1, "structural_failures": counts["structural_failures"]})
        report = verify_pilot_records(
            store.call_records(), store.pair_records(), fixture=fixture,
            provider_envelopes=store.provider_envelope_records(),
            pilot_manifest_sha256=manifest_sha256,
        )
        store.write_score(report)
        if not report["mechanical_pass"]:
            store.finish(state="failed", reason="pilot_lineage_verification_failed", valid_verdict=False)
            _write_terminal_receipt(store)
            emit("pilot_failed", state="failed", stage="finalization",
                 metrics={"scheduled_calls": 2, "provider_contacts": counts["calls"], "calls_completed": 2,
                          "A_completed": 1, "B_completed": 1, "pairs_completed": 1,
                          "comparisons_completed": 1, "structural_failures": counts["structural_failures"]})
            return {"run_id": resolved_run_id, "state": "failed", "reason": "pilot_lineage_verification_failed",
                    "store": str(store.root), "mechanical_pass": False, "report": report}

        terminal = store.finish(state="complete", reason="mechanical_pilot_passed", valid_verdict=False)
        terminal_receipt = _write_terminal_receipt(store)
        emit("pilot_complete", state="complete", stage="finalization", units=(1, 1, "pairs"),
             metrics={"scheduled_calls": 2, "provider_contacts": counts["calls"], "calls_completed": 2,
                      "A_completed": 1, "B_completed": 1, "validation_completed": 2,
                      "pairs_completed": 1, "comparisons_completed": 1,
                      "structural_failures": counts["structural_failures"]})
        return {"run_id": resolved_run_id, "state": "complete", "store": str(store.root),
                "mechanical_pass": True, "valid_verdict": False, "report": report,
                "terminal": terminal, "terminal_receipt": str(terminal_receipt)}
    except Exception as error:
        manifest = store.manifest()
        if manifest.get("state") not in {"complete", "incomplete", "failed"}:
            store.finish(state="failed", reason=f"{type(error).__name__}:{error}"[:400], valid_verdict=False)
            _write_terminal_receipt(store)
        emit("pilot_failed", state="failed", stage="finalization",
             metrics={"scheduled_calls": 2, "provider_contacts": counts["calls"],
                      "calls_completed": counts["calls"], "A_completed": counts["A"],
                      "B_completed": counts["B"], "pairs_completed": counts["pairs"],
                      "structural_failures": counts["structural_failures"]})
        raise


__all__ = ["CONTRACT_VERSION", "utc_run_id", "execute"]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run one exactly authorized G-CORROB1 two-call live mechanical pilot."
    )
    parser.add_argument("--authorization", required=True, help="Path to a separately approved authorization JSON.")
    parser.add_argument("--run-root", required=True, help="Runtime-only pilot persistence root.")
    parser.add_argument("--run-id")
    parser.add_argument("--endpoint", default="http://localhost:11434")
    args = parser.parse_args()
    authorization = json.loads(Path(args.authorization).read_text(encoding="utf-8"))
    # Importing/constructing the adapter is inert. ``execute`` verifies and consumes
    # the exact authorization before provider inspection or generation.
    from g_corrob1_provider import OllamaExperimentAdapter

    result = execute(
        provider_adapter=OllamaExperimentAdapter(args.endpoint),
        run_root=args.run_root,
        run_id=args.run_id,
        authorization=authorization,
    )
    projection = {
        "run_id": result.get("run_id"),
        "state": result.get("state"),
        "mechanical_pass": result.get("mechanical_pass"),
        "store": result.get("store"),
        "valid_production_verdict": False,
        "experiment_authorized": False,
    }
    print(json.dumps(projection, indent=1, sort_keys=True))
    return 0 if result.get("mechanical_pass") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
