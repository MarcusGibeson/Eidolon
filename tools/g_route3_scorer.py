from __future__ import annotations

"""The G-ROUTE3 R7 scorer child: the only process that reads gold (design §8, §12, B-O1, B-O2, C-O5).

It rebuilds R6's exact record shape from the sealed journal, applies ``sanitize_strings`` to the recorded provider
result exactly as R6's collection did, and then calls R6's own functions verbatim:
``collect_evaluation``, ``attach_semantics``, ``qualify``, ``g_route3_validation.score`` and ``build_table``.
Before reporting it verifies every input's digest against ``run_created`` (B-O2) and that every stored
``executable_json`` equals the executable re-derived from its ``call_recorded`` through the same ``run_pinned``
split as the holder (C-O5).

    python tools/g_route3_scorer.py        (JSON request on stdin, JSON result on stdout)
"""

import base64
import json
import sys
from pathlib import Path
from typing import Any, Mapping

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import g_route3_journal as J  # noqa: E402
import g_route3_platform as platform  # noqa: E402


def run_spec(phase: str) -> tuple[J.RunSpec, list, dict]:
    from g_route3_contract import runtime_fixtures, verify_checked_schedule
    schedule = verify_checked_schedule(phase)
    fixtures = runtime_fixtures(phase)
    spec = J.RunSpec(call_ids=tuple(row["call_id"] for row in schedule),
                     coding=frozenset(int(row["position"]) for row in schedule
                                      if fixtures[row["fixture_id"]]["validator_profile"] == "coding.v1"))
    return spec, schedule, fixtures


def read_journal(directory: Path) -> tuple[dict[str, bytes], list[str]]:
    files, extra = {}, []
    if not directory.is_dir():
        return files, extra
    for path in sorted(directory.iterdir()):
        if J.ENTRY_NAME.match(path.name):
            files[path.name] = path.read_bytes()
        else:
            extra.append(path.name)
    return files, extra


def rebuild_records(replay: J.Replay, phase: str, schedule: list, fixtures: Mapping[str, Any],
                    *, check_executables: bool) -> tuple[list[dict[str, Any]], list[int]]:
    """R6-shaped records for every recorded call; positions whose stored executable does not re-derive."""
    from g_route3_contract import request_body
    from g_route3_qualification import collect_evaluation
    from g_route3_runner import _failed_coding_evidence, sanitize_strings
    from g_route3_worker import derive_executable

    records, mismatched = [], []
    executions = {int(e["payload"]["position"]): e for e in replay.entries if e["kind"] == "execution_recorded"}
    started = {int(e["payload"]["position"]): e for e in replay.entries if e["kind"] == "execution_started"}
    for entry in replay.entries:
        if entry["kind"] != "call_recorded":
            continue
        payload = entry["payload"]
        position = int(payload["position"])
        scheduled = schedule[position - 1]
        fixture = fixtures[scheduled["fixture_id"]]
        raw_text = J.b64_to_text(payload["raw_output_b64"])
        envelope: Any = {}
        try:
            raw_body = base64.b64decode(payload.get("raw_body_b64") or "", validate=True)
            parsed = json.loads(raw_body.decode("utf-8")) if raw_body else {}
            envelope = parsed if isinstance(parsed, dict) else {}
        except (ValueError, UnicodeDecodeError, RecursionError):
            envelope = {}
        result = sanitize_strings({"raw_output": raw_text, "envelope": envelope,
                                   "metrics": dict(payload.get("metrics") or {})})
        strings_sanitized = result != {"raw_output": raw_text, "envelope": envelope,
                                       "metrics": dict(payload.get("metrics") or {})}
        raw_output = result["raw_output"]
        infrastructure_failure = str(payload.get("transport_failure") or "")
        evidence = None
        if fixture["validator_profile"] == "coding.v1":
            execution = executions.get(position)
            if execution is not None:
                evidence = execution["payload"].get("evidence")
                infrastructure_failure = infrastructure_failure or str(
                    execution["payload"].get("infrastructure_failure") or "")
                if check_executables and position in started:
                    stored = started[position]["payload"]["executable_json"]
                    if derive_executable(fixture, raw_text) != stored:
                        mismatched.append(position)
            if evidence is None:
                evidence = _failed_coding_evidence(fixture)      # R6: an empty or unexecuted output fails
        evaluation = platform.run_pinned(collect_evaluation, fixture, raw_output, evidence)
        body = request_body(fixture, scheduled)
        metrics = result["metrics"]
        latency = float(payload.get("latency_seconds") or 0.0)
        records.append({
            **scheduled, "schedule_position": position,
            "request": {"system": body["system"], "prompt": body["prompt"]},
            "request_body_sha256": J.digest(body),
            "raw_provider_body_b64": str(payload.get("raw_body_b64") or ""),
            "raw_provider_body_sha256": str(payload.get("raw_body_sha256") or ""),
            "raw_provider_envelope": result["envelope"], "raw_output": raw_output,
            **evaluation, "coding_execution_evidence": evidence,
            "infrastructure_failure": infrastructure_failure,
            "requested_model": scheduled["model"], "returned_model": payload.get("returned_model"),
            "provider_contacted": bool(payload.get("provider_contacted")), "provider_metrics": metrics,
            "latency_seconds": latency,
            "tokens_per_second": round(float(metrics["eval_count"]) / latency, 6)
            if metrics.get("eval_count") and latency > 0 else None,
            "gold_loaded": False, "belief_effects": "none", "production_routing_invoked": False,
            "provider_strings_sanitized": strings_sanitized,
        })
    return records, mismatched


def partial_results(phase: str, data_root: Path, rows: list[Mapping[str, Any]], schedule, fixtures, spec
                    ) -> list[dict[str, Any]]:
    """Partial cells (A) or per-observation correctness (B) for every earlier non-complete attempt (§12)."""
    from g_route3_qualification import attach_semantics, qualify
    out = []
    for row in rows:
        row = dict(row)
        if row.get("outcome") not in ("completed", "this_attempt"):
            files, extra = read_journal(data_root / f"phase_{phase.lower()}" / "runs" / str(row["run_id"]) / "journal")
            entries = [J.parse_entry(data) for name, data in sorted(files.items()) if name.endswith(".json")]
            replay = J.Replay(state="partial", entries=[e for e in entries if e is not None])
            records, mismatched = rebuild_records(replay, phase, schedule, fixtures, check_executables=True)
            records = [r for r in records if r["schedule_position"] not in mismatched]
            judged = attach_semantics(records, phase)
            if phase == "A":
                row["partial_cells"] = qualify(judged)
            else:
                row["partial_observations"] = [
                    {"position": r["schedule_position"], "fixture_id": r["fixture_id"], "model_tier": r["model_tier"],
                     "correct": bool(r["semantics"]["normalized_semantic_evaluation"]["hard_gate_pass"])}
                    for r in judged]
            row["undeterminable_positions"] = mismatched
            row["partial_results_source"] = "sealed records on disk"
        out.append(row)
    return out


def score_run(request: Mapping[str, Any]) -> dict[str, Any]:
    from g_route3_lifecycle import guarded_digest, standard_guarded_files
    from g_route3_qualification import attach_semantics, load_frozen_table, qualify

    phase, run_id, data_root = request["phase"], request["run_id"], Path(request["data_root"])
    spec, schedule, fixtures = run_spec(phase)
    files, extra = read_journal(data_root / f"phase_{phase.lower()}" / "runs" / run_id / "journal")
    replay = J.replay_run(files, spec, extra_names=extra)
    if replay.state not in ("scoring_interrupted", "torn_pending"):
        return {"error": f"scorer_state:{replay.state}"}
    run_created = replay.entries[0]["payload"]
    if guarded_digest(standard_guarded_files(data_root, phase)) != run_created.get("guarded_digest"):
        return {"error": "scorer_inputs_drifted"}                                  # B-O2
    records, mismatched = rebuild_records(replay, phase, schedule, fixtures, check_executables=True)
    if mismatched:
        return {"error": f"stored_executable_differs_from_rederived:{mismatched}"}  # C-O5
    if len(records) != spec.calls:
        return {"error": "scorer_requires_every_record"}
    rows = partial_results(phase, data_root, list(request.get("attempts") or []), schedule, fixtures, spec)
    if phase == "A":
        cells = qualify(attach_semantics(records, "A"))
        report = {"contract_version": "g-route3.phase-a-score.v1", "phase": "A", "cells": cells,
                  "qualified_cells": sum(c["verdict"] == "qualified" for c in cells),
                  "insufficient_cells": sum(c["verdict"] == "insufficient_evidence" for c in cells),
                  "table_frozen": False, "corpus_b_consulted": False, "belief_effects": "none",
                  "attempt_disclosure": rows}
    else:
        from g_route3_validation import score
        table = load_frozen_table(data_root / "tables" / "QUALIFICATION_TABLE.json")
        if table["table_sha256"] != run_created.get("table_sha256"):
            return {"error": "qualification_table_mutated"}
        report = {**score(records, table), "synthetic_fixture": bool(run_created.get("synthetic")),
                  "phase_b_attempts": rows, "phase_a_run_id": run_created.get("phase_a_run_id")}
    return {"report": json.loads(json.dumps(J.safe_value(report)))}


def phase_a_cells(request: Mapping[str, Any]) -> dict[str, Any]:
    """§10.6: cells re-derived from a completed Phase A attempt's facts."""
    from g_route3_qualification import attach_semantics, qualify
    data_root = Path(request["data_root"])
    spec, schedule, fixtures = run_spec("A")
    files, extra = read_journal(data_root / "phase_a" / "runs" / request["run_id"] / "journal")
    replay = J.replay_run(files, spec, extra_names=extra)
    if replay.state != "completed":
        return {"error": f"phase_a_state:{replay.state}"}
    records, mismatched = rebuild_records(replay, "A", schedule, fixtures, check_executables=True)
    if mismatched:
        return {"error": f"stored_executable_differs_from_rederived:{mismatched}"}
    return {"cells": qualify(attach_semantics(records, "A"))}


def build_qualification_table(request: Mapping[str, Any]) -> dict[str, Any]:
    """R6's build_table, verbatim, with the R7 binding block added before the digest (§7 --freeze-table)."""
    from g_route3_qualification import audit_record, build_table, json_digest
    data_root = Path(request["data_root"])
    audit = audit_record(Path(request["audit_copy"]), request["verdict"], request["auditor"],
                         run_id=request["run_id"], score_record_sha256=request["scored_sha256"])
    spec, schedule, fixtures = run_spec("A")
    rows = partial_results("A", data_root, list(request["attempts"]), schedule, fixtures, spec)
    doc = build_table(request["cells"], run_id=request["run_id"], score_record_sha256=request["scored_sha256"],
                      execution_freeze_binding=request["freeze_binding"], audit=audit,
                      phase_a_attempts=rows)
    doc.pop("table_sha256")
    doc["r7_binding"] = {"run_created_sha256": request["run_created_sha256"],
                         "scored_sha256": request["scored_sha256"],
                         "terminal_evidence_commit": request["terminal_commit"],
                         "audit_copy": "tables/" + Path(request["audit_copy"]).name,
                         "data_root": str(data_root)}
    doc["table_sha256"] = json_digest(doc)
    return {"table": doc}


def attempt_rows(request: Mapping[str, Any]) -> dict[str, Any]:
    """The table's attempt disclosure recomputed now (§10.8)."""
    spec, schedule, fixtures = run_spec(request["phase"])
    return {"rows": partial_results(request["phase"], Path(request["data_root"]), list(request["attempts"]),
                                    schedule, fixtures, spec)}


MODES = {"score_run": score_run, "phase_a_cells": phase_a_cells, "build_table": build_qualification_table,
         "attempt_rows": attempt_rows}


def main() -> int:
    platform.pin_recursion_limit()
    platform.join_kill_on_close_job()
    request = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    try:
        result = MODES[request["mode"]](request)
    except Exception as exc:  # noqa: BLE001 - reported to the holder, which refuses (J13)
        result = {"error": f"{type(exc).__name__}:{exc}"[:500]}
    sys.stdout.buffer.write(json.dumps(result, sort_keys=True, ensure_ascii=True).encode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
