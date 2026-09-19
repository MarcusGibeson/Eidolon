from __future__ import annotations

"""G-CORROB1-R2 runner candidate.

There is intentionally no live CLI. Production collection requires an execution
manifest, exact authorization binding, a verified provider preflight receipt, and
an explicitly supplied provider adapter. Tests use deterministic fixtures only.
"""

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from g_corrob1_activity import NullCorrobActivity
from g_corrob1_contract import (
    BELIEF_EFFECTS, DATA, EXPECTED_CALLS, EXPECTED_PAIRS, build_schedule, canonical_digest,
    load_corpus, load_sampling, request_receipt, semantic_http_body,
)
from g_corrob1_persistence import RunStore
from g_corrob1_policy import compare_pair, process_assessment
from g_corrob1_provider import ProviderResult, verify_preflight_receipt


CONTRACT_VERSION = "g-corrob1.r2.runner-candidate.1"


def utc_run_id() -> str:
    return "gcorrob1r2_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _authorization_valid(authorization: Mapping[str, Any] | None) -> bool:
    row = dict(authorization or {})
    expected = str(row.get("execution_manifest_sha256") or "")
    manifest = row.get("execution_manifest")
    if not isinstance(manifest, Mapping):
        return False
    calculated = canonical_digest(json.dumps(dict(manifest), sort_keys=True, separators=(",", ":")))
    try:
        from g_corrob1_freeze import verify_execution_manifest
        freeze_valid = verify_execution_manifest(manifest)["valid"]
    except Exception:
        freeze_valid = False
    return (
        row.get("execution_authorized") is True
        and row.get("execution_frozen") is True
        and len(expected) == 64
        and expected == calculated
        and freeze_valid
        and row.get("operator_confirmation") == f"Authorize G-CORROB1-R2 execution {expected}"
    )


def _result_dict(value: ProviderResult | Mapping[str, Any]) -> dict[str, Any]:
    return value.as_dict() if isinstance(value, ProviderResult) else dict(value)


def execute(
    *,
    provider_call: Callable[[str, Mapping[str, Any]], ProviderResult | Mapping[str, Any]],
    preflight_receipt: Mapping[str, Any],
    run_root: str | Path,
    run_id: str | None = None,
    activity: Any | None = None,
    synthetic_fixture: bool = False,
    authorization: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Collect, compare, and score one run through an injected provider boundary.

    ``synthetic_fixture`` is accepted only for deterministic tests. A real adapter
    additionally requires a separately frozen and exactly confirmed manifest.
    """
    if not synthetic_fixture and not _authorization_valid(authorization):
        raise PermissionError("g_corrob1_execution_not_authorized")

    preflight = verify_preflight_receipt(preflight_receipt, require_model_digest=True)
    if not preflight["valid"]:
        raise ValueError("provider_preflight_rejected:" + ",".join(preflight["reasons"]))

    corpus = load_corpus()
    items = {row["item_id"]: row for row in corpus}
    sampling = load_sampling()
    schedule = build_schedule(corpus)
    activity = activity or NullCorrobActivity()
    def emit(event: str, **kwargs: Any) -> None:
        try:
            activity.emit(event, **kwargs)
        except Exception:
            # Activity is disposable observation. It cannot interrupt or alter the scientific path.
            return None
    resolved_run_id = run_id or utc_run_id()
    store = RunStore(
        run_root, resolved_run_id, create=True,
        run_manifest={
            "candidate_id": "G-CORROB1-candidate-r2", "runner_contract": CONTRACT_VERSION,
            "state": "preparing", "synthetic_fixture": bool(synthetic_fixture),
            "intended_calls": EXPECTED_CALLS, "intended_pairs": EXPECTED_PAIRS,
            "preflight": dict(preflight_receipt), "preflight_validation": preflight,
            "sampling_sha256": canonical_digest(json.dumps(sampling, sort_keys=True, separators=(",", ":"))),
            "execution_manifest_sha256": str((authorization or {}).get("execution_manifest_sha256") or ""),
        },
    )
    counts = {"A": 0, "B": 0, "calls": 0, "pairs": 0, "validations": 0,
              "structural_failures": 0, "grounding_failures": 0}
    records_by_pair: dict[str, dict[str, dict[str, Any]]] = {}
    emit("preflight_verified", state="preparing", stage="preflight_validation",
         metrics={"scheduled_calls": EXPECTED_CALLS})
    store.update(state="running")

    try:
        for scheduled in schedule:
            item = items[scheduled.item_id]
            body = semantic_http_body(item, scheduled, sampling)
            request = request_receipt(item, scheduled, sampling)
            emit(
                "assessment_requested", state="running", stage="assessment_collection",
                units=(counts["calls"], EXPECTED_CALLS, "calls"),
                metrics={"scheduled_calls": EXPECTED_CALLS, "provider_contacts": counts["calls"],
                         "A_completed": counts["A"], "B_completed": counts["B"],
                         "pairs_completed": counts["pairs"]},
            )
            result = _result_dict(provider_call(scheduled.call_id, body))
            counts["calls"] += int(bool(result.get("provider_contacted")))
            provider_error = str(result.get("error") or "")
            binding_reasons = []
            if result.get("request_id") != scheduled.call_id:
                binding_reasons.append("request_binding_mismatch")
            if result.get("submitted_body_sha256") != request["submitted_body_sha256"]:
                binding_reasons.append("submitted_request_digest_mismatch")
            if result.get("returned_model") and result.get("returned_model") != sampling["model_name"]:
                binding_reasons.append("returned_model_mismatch_or_fallback")
            metrics = dict(result.get("metrics") or {})
            truncated = bool(result.get("truncated")) or int(metrics.get("eval_count") or 0) >= int(
                sampling["parameters"]["num_predict"]
            )
            processed = process_assessment(
                str(result.get("raw_response") or ""), proposition_id=item["proposition_id"],
                evidence_id=item["evidence_id"], evidence_text=item["evidence"], truncated=truncated,
                binding_error=";".join(binding_reasons) if binding_reasons else None,
            )
            record = {
                **scheduled.identity(), "request": request, "raw_response": str(result.get("raw_response") or ""),
                "assessment": processed["assessment"], "parse_error": processed["parse_error"],
                "validation": processed["validation"], "disposition": processed["disposition"],
                "rule": processed["rule"], "rules_fired": processed.get("rules_fired") or [],
                "reason": processed["reason"], "belief_effects": BELIEF_EFFECTS,
                "provider_contacted": bool(result.get("provider_contacted")), "provider_error": provider_error,
                "returned_model": str(result.get("returned_model") or ""), "metrics": metrics,
                "seconds": float(result.get("seconds") or 0),
                "prompt_tokens": int(metrics.get("prompt_eval_count") or 0),
                "output_tokens": int(metrics.get("eval_count") or 0),
                "token_accounting_available": "prompt_eval_count" in metrics and "eval_count" in metrics,
                "truncated": truncated, "submitted_body_sha256": str(result.get("submitted_body_sha256") or ""),
                "runner_contract": CONTRACT_VERSION,
            }
            store.write_call(record)
            counts[scheduled.role] += 1
            counts["validations"] += 1
            counts["structural_failures"] += int(not processed["validation"]["valid"])
            counts["grounding_failures"] += int(int(processed["validation"].get("quotes_anchored") or 0) < 1)
            emit(
                "assessment_preserved", state="running", stage="structural_validation",
                units=(counts["calls"], EXPECTED_CALLS, "calls"),
                metrics={"scheduled_calls": EXPECTED_CALLS, "provider_contacts": counts["calls"],
                         "returned_responses": counts["A"] + counts["B"], "A_completed": counts["A"],
                         "B_completed": counts["B"], "validation_completed": counts["validations"],
                         "structural_failures": counts["structural_failures"],
                         "grounding_failures": counts["grounding_failures"], "pairs_completed": counts["pairs"]},
            )
            if provider_error or binding_reasons:
                reason = "provider_failure" if provider_error else "provenance_or_binding_failure"
                store.finish(state="incomplete", reason=reason, valid_verdict=False)
                emit("run_incomplete", state="incomplete", stage="finalization",
                     metrics={"scheduled_calls": EXPECTED_CALLS, "provider_contacts": counts["calls"],
                              "A_completed": counts["A"], "B_completed": counts["B"],
                              "pairs_completed": counts["pairs"],
                              "structural_failures": counts["structural_failures"]})
                return {"run_id": resolved_run_id, "state": "incomplete", "reason": reason,
                        "store": str(store.root), "valid_verdict": False}

            pair_roles = records_by_pair.setdefault(scheduled.pair_id, {})
            if scheduled.role in pair_roles:
                raise ValueError("duplicate_assessor_binding")
            pair_roles[scheduled.role] = record
            if set(pair_roles) == {"A", "B"}:
                comparison = compare_pair(pair_roles["A"], pair_roles["B"])
                pair_record = {
                    "pair_id": scheduled.pair_id, "item_id": scheduled.item_id, "repeat": scheduled.repeat,
                    "A_call_id": pair_roles["A"]["call_id"], "B_call_id": pair_roles["B"]["call_id"],
                    **comparison,
                }
                store.write_pair(pair_record)
                counts["pairs"] += 1
                emit("pair_compared", state="running", stage="paired_comparison",
                     units=(counts["pairs"], EXPECTED_PAIRS, "pairs"),
                     metrics={"scheduled_calls": EXPECTED_CALLS, "provider_contacts": counts["calls"],
                              "A_completed": counts["A"], "B_completed": counts["B"],
                              "pairs_completed": counts["pairs"],
                              "comparisons_completed": counts["pairs"],
                              "structural_failures": counts["structural_failures"]})

        if counts["pairs"] != EXPECTED_PAIRS:
            raise ValueError("missing_pair_after_collection")
        emit("scoring_started", state="running", stage="scoring",
             metrics={"scheduled_calls": EXPECTED_CALLS, "provider_contacts": counts["calls"],
                      "A_completed": counts["A"], "B_completed": counts["B"],
                      "pairs_completed": counts["pairs"], "comparisons_completed": counts["pairs"]})
        # Gold is loaded only after all semantic calls and comparisons are durably preserved.
        from g_corrob1_scorer import score

        report = score(store.call_records(), store.pair_records())
        store.write_score(report)
        store.finish(state="complete", reason="scientific_result_preserved", valid_verdict=True)
        emit("run_complete", state="complete", stage="finalization",
             units=(EXPECTED_PAIRS, EXPECTED_PAIRS, "pairs"),
             metrics={"scheduled_calls": EXPECTED_CALLS, "provider_contacts": counts["calls"],
                      "returned_responses": EXPECTED_CALLS, "A_completed": 96, "B_completed": 96,
                      "validation_completed": EXPECTED_CALLS, "pairs_completed": EXPECTED_PAIRS,
                      "comparisons_completed": EXPECTED_PAIRS, "scoring_units_completed": EXPECTED_PAIRS,
                      "structural_failures": counts["structural_failures"],
                      "grounding_failures": counts["grounding_failures"]})
        return {"run_id": resolved_run_id, "state": "complete", "store": str(store.root),
                "valid_verdict": True, "report": report}
    except Exception as error:
        manifest = store.manifest()
        if manifest.get("state") not in {"complete", "incomplete", "failed"}:
            store.finish(state="failed", reason=f"{type(error).__name__}:{error}"[:400], valid_verdict=False)
        emit("run_failed", state="failed", stage="finalization",
             metrics={"scheduled_calls": EXPECTED_CALLS, "provider_contacts": counts["calls"],
                      "A_completed": counts["A"], "B_completed": counts["B"],
                      "pairs_completed": counts["pairs"],
                      "structural_failures": counts["structural_failures"]})
        raise


__all__ = ["CONTRACT_VERSION", "utc_run_id", "execute"]
