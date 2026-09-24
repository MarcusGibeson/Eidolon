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
from g_route3_semantics import canonical_coding_payload
from g_route3_contract import (DATA, EXECUTION_FREEZE_PATH, EXPECTED_CALLS, QUALIFICATION_TABLE_PATH, json_digest,
                               load_json, load_model_bindings, request_body, runtime_fixtures,
                               verify_checked_schedule)
import json
import subprocess

MODEL_CAUSED_CODING_ERRORS = (ValueError, SyntaxError, json.JSONDecodeError, subprocess.TimeoutExpired)


def json_dumps(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True)

CONTRACT_VERSION = "g-route3.runner.v3"
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
    "experiments/G-ROUTE1-candidate/prompt_profiles.json", "experiments/G-ROUTE1-candidate/model_bindings.json",
    "tools/g_route3_launch.py",
    "tools/g_route1_validators.py", "tools/g_route1_operational.py", "tools/g_route1_coding_runner.py",
    "tools/g_route1_persistence.py", "tools/g_route1_provider.py", "tools/g_route2_normalization.py",
    "tools/g_route1_contract.py", "tools/g_route1_execution_contract.py", "tools/g_route1_freeze.py",
    "tools/g_route3_operational.py", "tools/g_route3_triggers.py", "tools/g_route3_conversation.py",
    "tools/g_route3_semantics.py", "tools/g_route3_freeze.py",
    "tools/g_route3_contract.py", "tools/g_route3_qualification.py",
    "tools/g_route3_routing.py", "tools/g_route3_validation.py", "tools/g_route3_runner.py",
    "conscious_agent/activity.py", "conscious_agent/json_storage.py",
    "conscious_agent/metadata_mutation_coordination.py",
)
TABLE_RELATIVE = "experiments/G-ROUTE3-candidate/QUALIFICATION_TABLE.json"
AUTHORIZATION_LEDGER = DATA / "authorization_ledger"
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


AUTHORIZATION_KEYS = {
    "A": frozenset({"benchmark_id", "phase", "execution_freeze_sha256", "attempt", "one_execution_only", "consumed",
                    "operator_confirmation"}),
    "B": frozenset({"benchmark_id", "phase", "execution_freeze_sha256", "qualification_table_sha256",
                    "phase_a_run_id", "attempt", "one_execution_only", "consumed", "operator_confirmation"}),
}


def confirmation_string(phase: str, attempt: int, *, freeze: str, table: str | None = None) -> str:
    """The exact operator sentence. The attempt number makes every attempt a distinct, explicit authorization."""
    if phase == "A":
        return f"Authorize G-ROUTE3 phase A execution {freeze} attempt {attempt}"
    return f"Authorize G-ROUTE3 phase B execution {freeze} table {table} attempt {attempt}"


def ledger_entries(phase: str) -> list[dict[str, Any]]:
    """Every consumed authorization for a phase, in attempt order. The ledger lives at a fixed path, not in a run root."""
    rows = []
    if AUTHORIZATION_LEDGER.is_dir():
        for path in sorted(AUTHORIZATION_LEDGER.glob(f"phase-{phase}-attempt-*.json")):
            rows.append(load_json(path))
    rows.sort(key=lambda row: int(row["attempt"]))
    if [int(row["attempt"]) for row in rows] != list(range(1, len(rows) + 1)):
        raise ValueError(f"authorization_ledger_not_contiguous:{phase}")
    return rows


NON_COMPLETE_OUTCOMES = frozenset({"incomplete", "failed", "cancelled"})


def attempt_outcome(entry: Mapping[str, Any]) -> dict[str, Any]:
    """An attempt is complete if its run sealed a terminal receipt; otherwise its manifest state and reason."""
    try:
        store = RouteRunStore(Path(str(entry["run_root"])), str(entry["run_id"]), create=False)
    except Exception:
        return {"outcome": "never_started", "reason": "run_directory_missing"}
    try:
        store.terminal_receipt()
        return {"outcome": "complete", "reason": "completed_and_scored"}
    except FileNotFoundError:
        pass
    except Exception as exc:
        return {"outcome": "unverifiable", "reason": f"terminal_receipt_invalid:{type(exc).__name__}"}
    manifest = store.manifest()
    return {"outcome": str(manifest.get("state") or "unknown"), "reason": str(manifest.get("reason") or "")}


def attempts_with_outcomes(phase: str) -> list[dict[str, Any]]:
    return [{"attempt": int(row["attempt"]), "run_id": row["run_id"], "run_root": row["run_root"],
             "operator_confirmation": row["operator_confirmation"], **attempt_outcome(row)}
            for row in ledger_entries(phase)]


def _authorization_ok(phase: str, authorization: Mapping[str, Any] | None, *, run_id: str | None,
                      run_root: Path | None = None, resume: bool = False,
                      table: str | None = None, phase_a_run_id: str | None = None) -> bool:
    row = dict(authorization or {})
    digest = _freeze_digest()
    if not digest or set(row) != AUTHORIZATION_KEYS[phase]:
        return False
    attempt = row.get("attempt")
    if not isinstance(attempt, int) or isinstance(attempt, bool) or attempt < 1:
        return False
    if phase == "B" and (row.get("qualification_table_sha256") != table or row.get("phase_a_run_id") != phase_a_run_id):
        return False
    if (row.get("benchmark_id") != BENCHMARK_ID or row.get("phase") != phase
            or row.get("execution_freeze_sha256") != digest or row.get("one_execution_only") is not True
            or row.get("consumed") is not False
            or row.get("operator_confirmation") != confirmation_string(phase, attempt, freeze=digest, table=table)):
        return False
    entries = ledger_entries(phase)
    fresh = (not resume and attempt == len(entries) + 1
             and all(attempt_outcome(entry)["outcome"] in NON_COMPLETE_OUTCOMES for entry in entries))
    resuming = (resume and attempt == len(entries) and run_id is not None and run_root is not None
                and entries[-1].get("run_id") == run_id
                and Path(str(entries[-1].get("run_root"))).resolve() == Path(run_root).resolve()
                and entries[-1].get("operator_confirmation") == row["operator_confirmation"])
    return (fresh or resuming) and _freeze_valid()


def abandon_attempt(phase: str, reason: str) -> dict[str, Any]:
    """Close the latest attempt of a phase as incomplete when it can neither finish nor resume.

    Only a non-terminal run can be abandoned, and only while no process holds its lease. The reason is
    recorded in the run manifest and disclosed with the attempt's outcome. This makes room for the next
    numbered attempt, which still needs its own explicit authorization.
    """
    if not str(reason).strip():
        raise ValueError("abandon_reason_required")
    entries = ledger_entries(phase)
    if not entries:
        raise ValueError("no_attempt_to_abandon")
    entry = entries[-1]
    store = RouteRunStore(Path(str(entry["run_root"])), str(entry["run_id"]), create=False)
    if store.manifest().get("state") in TERMINAL:
        raise ValueError("attempt_already_terminal")
    with store.lease():
        return store.finish(state="incomplete", reason=f"abandoned_by_operator:{str(reason).strip()}"[:500],
                            valid_verdict=False)


def phase_a_authorized(authorization: Mapping[str, Any] | None, *, run_id: str | None = None,
                       run_root: Path | None = None, resume: bool = False) -> bool:
    return _authorization_ok("A", authorization, run_id=run_id, run_root=run_root, resume=resume)


def consume_authorization(phase: str, authorization: Mapping[str, Any], run_id: str, run_root: Path) -> Path:
    """Write the attempt to the fixed ledger by exclusive creation. Reuse by another run is refused."""
    attempt = int(authorization["attempt"])
    path = AUTHORIZATION_LEDGER / f"phase-{phase}-attempt-{attempt:03d}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {"benchmark_id": BENCHMARK_ID, "phase": phase, "attempt": attempt,
             "operator_confirmation": str(authorization["operator_confirmation"]),
             "authorization_sha256": json_digest(dict(authorization)), "run_id": run_id,
             "run_root": str(Path(run_root)), "consumed_at": now()}
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json_dumps(entry))
    except FileExistsError:
        existing = load_json(path)
        if (existing.get("run_id") != run_id or existing.get("operator_confirmation") != entry["operator_confirmation"]
                or Path(str(existing.get("run_root"))).resolve() != Path(run_root).resolve()):
            raise PermissionError("authorization_already_consumed")
    return path


def phase_a_attempts() -> list[dict[str, Any]]:
    """Every authorized Phase A attempt with its outcome, so a table cannot come from an undisclosed best-of-N."""
    return attempts_with_outcomes("A")


def _call_records_digest(records: list[Mapping[str, Any]]) -> str:
    return json_digest([str(row["record_sha256"]) for row in records])


def phase_b_preconditions(phase_a_root: Path, phase_a_run_id: str, *, allow_synthetic_phase_a: bool = False) -> dict[str, Any]:
    """Every condition that must hold before Corpus B may be contacted at all.

    Nothing about Phase A is taken from its unsealed run manifest. The table is re-derived from the sealed
    call records and must equal both the sealed score and the frozen table; the receipt must chain to the
    records and the score; Phase A must have run under this freeze with today's guarded dependencies; and,
    unless synthetic, it must appear in the authorization ledger, whose full attempt list the table discloses.
    """
    from g_route3_qualification import attach_semantics, qualify, verify_table

    reasons = []
    if not QUALIFICATION_TABLE_PATH.is_file():
        return {"valid": False, "reasons": ["qualification_table_not_frozen"], "table_sha256": None}
    table = load_json(QUALIFICATION_TABLE_PATH)
    reasons += verify_table(table)["reasons"]
    source = table.get("source", {})
    try:
        store = RouteRunStore(phase_a_root, phase_a_run_id, create=False)
        receipt = store.terminal_receipt()
        score = store.score_record()
        records = store.call_records()
        schedule = [row["call_id"] for row in verify_checked_schedule("A")]
        synthetic = receipt.get("synthetic_fixture") is not False
        if receipt.get("phase") != "A" or receipt.get("state") != "complete" or receipt.get("run_id") != phase_a_run_id:
            reasons.append("phase_a_not_complete")
        if store.manifest().get("state") != "complete":
            reasons.append("phase_a_manifest_not_complete")
        if any(row.get("synthetic_fixture") is not synthetic for row in records):
            reasons.append("phase_a_records_disagree_with_receipt_on_synthetic")
        if not synthetic:
            reasons += _provider_evidence_problems(records, "A")
        if synthetic and not allow_synthetic_phase_a:
            reasons.append("phase_a_was_synthetic")
        if receipt.get("execution_freeze_sha256") != _freeze_digest():
            reasons.append("phase_a_ran_under_a_different_freeze")
        if receipt.get("guarded_digest") != guarded_dependency_digest(include_table=False):
            reasons.append("phase_a_guarded_dependencies_differ_from_now")
        if [row["call_id"] for row in records] != schedule or receipt.get("calls_persisted") != len(schedule):
            reasons.append("phase_a_call_records_incomplete")
        if receipt.get("call_records_sha256") != _call_records_digest(records):
            reasons.append("phase_a_receipt_does_not_chain_to_call_records")
        if receipt.get("score_record_sha256") != score["record_sha256"]:
            reasons.append("phase_a_receipt_does_not_chain_to_score")
        if score["record_sha256"] != source.get("score_record_sha256"):
            reasons.append("table_not_derived_from_this_phase_a_score")
        rederived = qualify(attach_semantics(records, "A"))
        if rederived != score.get("cells"):
            reasons.append("sealed_score_differs_from_call_records")
        if rederived != table.get("cells"):
            reasons.append("table_cells_differ_from_call_records")
        if source.get("run_id") != phase_a_run_id:
            reasons.append("table_run_mismatch")
        attempts = phase_a_attempts()
        if source.get("phase_a_attempts") != attempts:
            reasons.append("phase_a_attempts_not_fully_disclosed")
        if not synthetic:
            named = [row for row in attempts if row["run_id"] == phase_a_run_id]
            if not named:
                reasons.append("phase_a_run_not_in_authorization_ledger")
            elif Path(str(named[-1]["run_root"])).resolve() != Path(phase_a_root).resolve():
                reasons.append("phase_a_run_root_differs_from_ledger")
            if [row["run_id"] for row in attempts if row["outcome"] == "complete"] != [phase_a_run_id]:
                reasons.append("phase_a_run_is_not_the_only_complete_attempt")
    except Exception as exc:
        reasons.append(f"phase_a_unverifiable:{type(exc).__name__}")
    if source.get("execution_freeze_binding") != _freeze_digest():
        reasons.append("table_bound_to_different_freeze")
    return {"valid": not reasons, "reasons": sorted(set(reasons)), "table_sha256": table.get("table_sha256")}


def phase_b_authorized(authorization: Mapping[str, Any] | None, phase_a_root: Path, phase_a_run_id: str, *,
                       run_id: str | None = None, run_root: Path | None = None, resume: bool = False) -> bool:
    pre = phase_b_preconditions(phase_a_root, phase_a_run_id, allow_synthetic_phase_a=False)
    return pre["valid"] and _authorization_ok("B", authorization, run_id=run_id, run_root=run_root, resume=resume,
                                              table=pre.get("table_sha256"), phase_a_run_id=phase_a_run_id)


def _provider_evidence_problems(records: list[Mapping[str, Any]], phase: str) -> list[str]:
    """Every record of an authorized run must carry the provider's own raw body, consistent with its fields."""
    import base64
    import hashlib
    from g_route1_provider import extract_output

    fixtures = runtime_fixtures(phase)
    schedule = {row["call_id"]: row for row in verify_checked_schedule(phase)}
    problems = set()
    for row in records:
        try:
            raw = base64.b64decode(str(row.get("raw_provider_body_b64") or ""), validate=True)
            if not raw or hashlib.sha256(raw).hexdigest() != row.get("raw_provider_body_sha256"):
                problems.add("provider_raw_body_digest_mismatch")
                continue
            envelope = json.loads(raw.decode("utf-8"))
            if envelope != row.get("raw_provider_envelope"):
                problems.add("provider_envelope_differs_from_raw_body")
            if envelope.get("model") != row.get("requested_model") or row.get("returned_model") != row.get("requested_model"):
                problems.add("provider_model_differs_from_request")
            if extract_output(envelope)[0] != row.get("raw_output"):
                problems.add("raw_output_differs_from_provider_body")
            call = schedule[row["call_id"]]
            if row.get("request_body_sha256") != json_digest(request_body(fixtures[call["fixture_id"]], call)):
                problems.add("request_body_differs_from_schedule")
        except Exception:
            problems.add("provider_evidence_unreadable")
    return sorted(problems)


def verify_model_receipts(receipts: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Model identity preflight against G-ROUTE3's own frozen, guarded bindings."""
    frozen = load_model_bindings()
    expected = {row["model"]: row for row in frozen["bindings"]}
    reasons: list[str] = []
    if len(receipts) != len(expected):
        reasons.append("model_receipt_count_mismatch")
    for receipt in receipts:
        model = str(receipt.get("requested_model") or "")
        binding = expected.get(model)
        if binding is None:
            reasons.append(f"unknown_model_receipt:{model}")
            continue
        if receipt.get("resolved_model") != model:
            reasons.append(f"model_fallback_or_alias_drift:{model}")
        if receipt.get("manifest_digest") != binding["manifest_digest"]:
            reasons.append(f"model_manifest_digest_mismatch:{model}")
        if receipt.get("model_blob_sha256") != binding["model_blob_sha256"]:
            reasons.append(f"model_blob_digest_mismatch:{model}")
        if receipt.get("provider_version") != frozen["provider_version"]:
            reasons.append(f"provider_version_mismatch:{model}")
        if receipt.get("generation_configuration") != frozen["generation_configuration"]:
            reasons.append(f"generation_configuration_mismatch:{model}")
        if receipt.get("silent_fallback") is not False:
            reasons.append(f"silent_fallback_not_denied:{model}")
    return {"valid": not reasons, "reasons": sorted(set(reasons))}


def _require_declared_synthetic_provider(provider_call) -> None:
    """The synthetic path skips authorization, so it may only drive a provider that declares itself synthetic."""
    if getattr(provider_call, "synthetic_provider", False) is not True or type(provider_call) in REAL_PROVIDER_TYPES:
        raise PermissionError("synthetic_path_requires_declared_synthetic_provider")


class GovernedOllamaProvider:
    """The only provider the authorized path accepts. It builds its own Ollama adapter; nothing is injected."""

    synthetic_provider = False

    def __init__(self, endpoint: str = "http://127.0.0.1:11434") -> None:
        from g_route1_provider import OllamaRouteAdapter
        self.adapter = OllamaRouteAdapter(endpoint)

    def model_receipts(self) -> list[dict[str, Any]]:
        return self.adapter.inspect_models(allow_metadata_inspection=True)

    def __call__(self, call_id: str, body: Mapping[str, Any]):
        return self.adapter.generate(call_id, body, allow_generation=True)


REAL_PROVIDER_TYPES: tuple[type, ...] = (GovernedOllamaProvider,)


def _require_governed_real_path(provider_call, guarded_root) -> None:
    if type(provider_call) not in REAL_PROVIDER_TYPES or getattr(provider_call, "synthetic_provider", False):
        raise PermissionError("authorized_path_requires_governed_ollama_provider")
    if guarded_root is not None:
        raise PermissionError("authorized_path_forbids_guarded_root_override")


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


def _host_baseline_ok(fixture: Mapping[str, Any]) -> bool:
    source = str(fixture["input"]["source"])
    baseline = json.dumps({"path": fixture["input"]["allowed_path"], "old": source, "new": source})
    try:
        run_isolated_fixture(fixture, baseline)
    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return True
    return True


def _collect(*, phase: str, provider_call, model_receipts, run_root, run_id, activity, control, guarded_root,
             resume, include_table, manifest_extra, on_ready: Callable[[], Any] | None = None) -> dict[str, Any]:
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
    synthetic = bool(manifest_extra.get("synthetic_fixture"))
    if bool(store.manifest().get("synthetic_fixture")) != synthetic:
        raise ValueError("resume_synthetic_mode_mismatch")
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
        if on_ready is not None:
            on_ready()      # the authorization is consumed only once this run exists and holds its lease
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
                executable, _ = canonical_coding_payload(fixture, canonical["payload"])
                try:
                    evidence = run_isolated_fixture(fixture, executable)
                except subprocess.TimeoutExpired:
                    # a timeout is the model's only if the unchanged source runs in time on this host right now
                    evidence = _failed_coding_evidence(fixture)
                    if not _host_baseline_ok(fixture):
                        infrastructure_failure = infrastructure_failure or "coding_sandbox_host_slow"
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
                "synthetic_fixture": synthetic,
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
        "contract_version": "g-route3.terminal-receipt.v2", "run_id": store.run_id, "phase": phase,
        "state": "complete", "result_state": "complete", "calls_persisted": len(records),
        "call_records_sha256": _call_records_digest(records),
        "synthetic_fixture": bool(store.manifest().get("synthetic_fixture")),
        "execution_freeze_sha256": _freeze_digest(),
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
    run_id = run_id or utc_run_id("A")
    on_ready = None
    if synthetic_fixture:
        _require_declared_synthetic_provider(provider_call)
    else:
        _require_governed_real_path(provider_call, guarded_root)
        if not phase_a_authorized(authorization, run_id=run_id, run_root=Path(run_root), resume=resume):
            raise PermissionError("g_route3_phase_a_not_authorized")
        on_ready = lambda: consume_authorization("A", authorization or {}, run_id, Path(run_root))  # noqa: E731
    got = _collect(phase="A", provider_call=provider_call, model_receipts=model_receipts, run_root=run_root,
                   run_id=run_id, activity=activity, control=control, guarded_root=guarded_root, resume=resume,
                   include_table=False, manifest_extra={"synthetic_fixture": bool(synthetic_fixture)},
                   on_ready=on_ready)
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
    if synthetic_fixture:
        _require_declared_synthetic_provider(provider_call)
        try:
            phase_a_synthetic = RouteRunStore(Path(phase_a_root), phase_a_run_id, create=False) \
                .terminal_receipt().get("synthetic_fixture") is True
        except Exception:
            phase_a_synthetic = False
        if not phase_a_synthetic:
            raise PermissionError("synthetic_phase_b_requires_a_synthetic_phase_a")
    else:
        _require_governed_real_path(provider_call, guarded_root)
    pre = phase_b_preconditions(Path(phase_a_root), phase_a_run_id, allow_synthetic_phase_a=synthetic_fixture)
    if not pre["valid"]:
        raise PermissionError("g_route3_phase_b_blocked:" + ",".join(pre["reasons"]))
    run_id = run_id or utc_run_id("B")
    on_ready = None
    if not synthetic_fixture:
        if not phase_b_authorized(authorization, Path(phase_a_root), phase_a_run_id, run_id=run_id,
                                  run_root=Path(run_root), resume=resume):
            raise PermissionError("g_route3_phase_b_not_authorized")
        on_ready = lambda: consume_authorization("B", authorization or {}, run_id, Path(run_root))  # noqa: E731
    got = _collect(phase="B", provider_call=provider_call, model_receipts=model_receipts, run_root=run_root,
                   run_id=run_id, activity=activity, control=control, guarded_root=guarded_root, resume=resume,
                   include_table=True, manifest_extra={"synthetic_fixture": bool(synthetic_fixture),
                                                       "qualification_table_sha256": pre["table_sha256"],
                                                       "phase_a_run_id": phase_a_run_id},
                   on_ready=on_ready)
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
        report = {**score(store.call_records(), table), "synthetic_fixture": bool(synthetic_fixture),
                  "phase_b_attempts": attempts_with_outcomes("B"), "phase_a_run_id": phase_a_run_id}
    except Exception as exc:
        reason = f"scorer_integrity_failure:{type(exc).__name__}:{exc}"[:500]
        store.write_failure({"failure_type": "scorer_integrity_failure", "reason": reason, "belief_effects": "none"})
        store.finish(state="failed", reason=reason, valid_verdict=False)
        return {"state": "failed", "reason": reason, "run_id": run_id}
    return _finish(store, activity, phase="B", report=report, guarded=got["guarded"], include_table=True,
                   guarded_root=guarded_root)


__all__ = ["CONTRACT_VERSION", "BENCHMARK_ID", "GUARDED_PATHS", "TABLE_RELATIVE", "AUTHORIZATION_LEDGER",
           "RouteThreeActivity", "NullActivity", "guarded_dependency_digest", "phase_a_authorized",
           "phase_b_preconditions", "phase_a_attempts", "consume_authorization", "confirmation_string",
           "ledger_entries", "verify_model_receipts", "GovernedOllamaProvider", "REAL_PROVIDER_TYPES",
           "attempt_outcome", "attempts_with_outcomes", "abandon_attempt",
           "phase_b_authorized", "execute_phase_a", "execute_phase_b", "utc_run_id"]
