from __future__ import annotations

"""The G-ROUTE3 R7 scorer child: the only process that reads gold (design §8, §12, B-O1, B-O2, C-O1, C-O5).

It rebuilds R6's exact record shape from the sealed journal, applies ``sanitize_strings`` to the recorded provider
result exactly as R6's collection did, and then calls R6's own functions verbatim, each through ``run_pinned``:
``collect_evaluation``, ``attach_semantics``, ``qualify``, ``g_route3_validation.score`` and ``build_table``.

Inputs are bound (A-F2, B-O2): every repository module is hashed as it is compiled, and every guarded data file
is read once, checked against the digests recorded in the attempt's ``run_created`` and then served from those
verified bytes. Before reporting, the guarded files are re-read raw from disk and must still match. The holder
also compares the reported module digests with ``run_created``.

    python tools/g_route3_scorer.py        (JSON request on stdin, JSON result on stdout)
"""

import base64
import json
import sys
from pathlib import Path
from typing import Any, Mapping

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import g_route3_platform as platform  # noqa: E402


class InputsDrifted(RuntimeError):
    pass


def _guarded_path(relative: str, data_root: Path) -> Path:
    if relative == "execution_freeze":
        return ROOT / "experiments" / "G-ROUTE3-candidate" / "EXECUTION_FREEZE_CANDIDATE.json"
    if relative.startswith("D/"):
        return data_root / relative[2:]
    return ROOT / relative


def bind_inputs(guarded_files: Mapping[str, str], data_root: Path) -> None:
    """Read every guarded data file once, check it against run_created, and serve those bytes from now on."""
    sealed = {}
    for relative, recorded in guarded_files.items():
        if relative.endswith(".py"):
            continue                                   # code is bound by load-time hashing instead
        path = _guarded_path(relative, data_root)
        data = platform.raw_read(path)
        if platform.canonical_sha256(data) != recorded:
            raise InputsDrifted(f"scorer_inputs_drifted:{relative}")
        sealed[path] = data
    platform.seal_reads(sealed)


def recheck_inputs(guarded_files: Mapping[str, str], data_root: Path) -> None:
    """B-O2 after scoring: the disk, read raw, must still hold exactly the recorded bytes."""
    for relative, recorded in guarded_files.items():
        if platform.canonical_sha256(platform.raw_read(_guarded_path(relative, data_root))) != recorded:
            raise InputsDrifted(f"scorer_inputs_drifted_during_scoring:{relative}")


def run_spec(phase: str):
    import g_route3_journal as J
    from g_route3_contract import runtime_fixtures, verify_checked_schedule
    schedule = verify_checked_schedule(phase)
    fixtures = runtime_fixtures(phase)
    spec = J.RunSpec(call_ids=tuple(row["call_id"] for row in schedule),
                     coding=frozenset(int(row["position"]) for row in schedule
                                      if fixtures[row["fixture_id"]]["validator_profile"] == "coding.v1"))
    return spec, schedule, fixtures


def read_journal(directory: Path) -> tuple[dict[str, bytes], list[str]]:
    import g_route3_journal as J
    files, extra = {}, []
    if not directory.is_dir():
        return files, extra
    for path in sorted(directory.iterdir()):
        if J.ENTRY_NAME.match(path.name):
            files[path.name] = platform.raw_read(path)
        else:
            extra.append(path.name)
    return files, extra


def rebuild_records(entries: list, phase: str, schedule: list, fixtures: Mapping[str, Any],
                    *, check_executables: bool) -> tuple[list[dict[str, Any]], dict[int, str]]:
    """R6-shaped records for every recorded call. Positions whose call id differs from today's schedule, whose
    request body differs from the digest sealed in ``call_started``, or whose stored executable does not re-derive
    are returned as mismatched (undeterminable), each with its reason."""
    import g_route3_journal as J
    from g_route3_contract import request_body
    from g_route3_qualification import collect_evaluation
    from g_route3_runner import _failed_coding_evidence, sanitize_strings
    from g_route3_worker import derive_executable

    records: list[dict[str, Any]] = []
    mismatched: dict[int, str] = {}
    executions = {int(e["payload"]["position"]): e for e in entries if e["kind"] == "execution_recorded"}
    started = {int(e["payload"]["position"]): e for e in entries if e["kind"] == "execution_started"}
    calls = {int(e["payload"]["position"]): e for e in entries if e["kind"] == "call_started"}
    for entry in entries:
        if entry["kind"] != "call_recorded":
            continue
        payload = entry["payload"]
        position = int(payload["position"])
        if position < 1 or position > len(schedule) or payload.get("call_id") != schedule[position - 1]["call_id"]:
            mismatched[position] = "call_id_differs_from_schedule"
            continue
        scheduled = schedule[position - 1]
        fixture = fixtures[scheduled["fixture_id"]]
        body = request_body(fixture, scheduled)
        call = calls.get(position)
        if call is None:
            mismatched[position] = "call_started_missing"
            continue
        if call["payload"].get("request_sha256") != J.digest(body):
            mismatched[position] = "request_body_differs_from_call_started"
            continue
        raw_text = J.b64_to_text(payload["raw_output_b64"])
        envelope: Any = {}
        try:
            raw_body = base64.b64decode(payload.get("raw_body_b64") or "", validate=True)
            parsed = json.loads(raw_body.decode("utf-8")) if raw_body else {}
            envelope = parsed if isinstance(parsed, dict) else {}
        except (ValueError, UnicodeDecodeError, RecursionError):
            envelope = {}
        original = {"raw_output": raw_text, "envelope": envelope, "metrics": dict(payload.get("metrics") or {})}
        result = platform.run_pinned(sanitize_strings, original)
        strings_sanitized = result != original
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
                        mismatched[position] = "stored_executable_does_not_rederive"
                        continue
            elif not infrastructure_failure:
                infrastructure_failure = "execution_not_run"      # B-N2: never graded as a model failure
            if evidence is None:
                evidence = _failed_coding_evidence(fixture)      # R6: an empty or unexecuted output fails
        evaluation = platform.run_pinned(collect_evaluation, fixture, raw_output, evidence)
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


def _inputs_differing_from_today(run_created: Mapping[str, Any], today: Mapping[str, str]) -> list[str]:
    """C-O6: an earlier attempt is graded against today's inputs only if every guarded data file (schedules,
    corpora, gold, thresholds, prompt profiles, model bindings) is the same as in its run_created."""
    recorded = run_created.get("guarded_files") or {}
    data = sorted(path for path in set(recorded) | set(today) if path.startswith("experiments/"))
    return [path for path in data if recorded.get(path) != today.get(path)]


def partial_results(phase: str, data_root: Path, rows: list[Mapping[str, Any]], schedule, fixtures, today
                    ) -> list[dict[str, Any]]:
    """Partial cells (A) or per-observation correctness (B) for every earlier non-complete attempt (§12),
    including sealed call records surviving only in temporary files (B-O5), labelled by source."""
    import g_route3_journal as J
    from g_route3_qualification import attach_semantics, qualify
    out = []
    for row in rows:
        row = dict(row)
        if row.get("outcome") not in ("completed", "this_attempt"):
            directory = data_root / f"phase_{phase.lower()}" / "runs" / str(row["run_id"]) / "journal"
            files, extra = read_journal(directory)
            entries = _individually_sealed(files)                                          # B-N5
            first = next((e for e in entries if e["kind"] == "run_created"), None)
            temp_entries, unparseable = [], []
            for name in sorted(extra):
                if J.ORPHAN_TEMP.match(name) or J.TEMP_NAME.match(name):
                    data = platform.raw_read(directory / name)
                    envelope = J.parse_entry(data)
                    if envelope is not None and envelope["kind"] == "call_recorded":
                        temp_entries.append(envelope)
                    elif envelope is None:
                        unparseable.append({"file": name, "sha256": J.sha256_bytes(data)})
            recorded_positions = {int(e["payload"]["position"]) for e in entries if e["kind"] == "call_recorded"}
            temp_entries = [e for e in temp_entries if int(e["payload"]["position"]) not in recorded_positions]
            differing = ["run_created_missing"] if first is None else \
                _inputs_differing_from_today(first["payload"], today)
            if differing:
                positions = sorted(recorded_positions | {int(e["payload"]["position"]) for e in temp_entries})
                row["undeterminable_positions"] = positions
                row["undeterminable_reasons"] = {str(p): "inputs_differ_from_today" for p in positions}
                row["undeterminable_reason"] = "inputs_differ_from_today:" + ",".join(differing)
                row["partial_results_source"] = "none"
            else:
                records, mismatched = rebuild_records(entries + temp_entries, phase, schedule, fixtures,
                                                      check_executables=True)
                temp_positions = {int(e["payload"]["position"]) for e in temp_entries}
                records = [r for r in records if r["schedule_position"] not in mismatched]
                judged = platform.run_pinned(attach_semantics, records, phase)
                if phase == "A":
                    row["partial_cells"] = platform.run_pinned(qualify, judged)
                else:
                    row["partial_routing_decisions"] = _partial_decisions(records, data_root)
                    row["partial_observations"] = [
                        {"position": r["schedule_position"], "fixture_id": r["fixture_id"],
                         "model_tier": r["model_tier"],
                         "correct": bool(r["semantics"]["normalized_semantic_evaluation"]["hard_gate_pass"]),
                         "source": "temporary_file" if r["schedule_position"] in temp_positions else "journal"}
                        for r in judged]
                row["undeterminable_positions"] = sorted(mismatched)
                row["undeterminable_reasons"] = {str(p): reason for p, reason in sorted(mismatched.items())}
                row["partial_results_source"] = "sealed records on disk"
                row["temporary_file_positions"] = sorted(temp_positions)
            row["unparseable_temporary_files"] = unparseable
        out.append(row)
    return out


def _individually_sealed(files: Mapping[str, bytes]) -> list[dict[str, Any]]:
    """Every entry that seals on its own, one per entry number, preferring n.json over n.torn (B-N5)."""
    import g_route3_journal as J
    chosen: dict[int, dict[str, Any]] = {}
    for name in sorted(files, key=lambda n: (n[:6], not n.endswith(".json"))):
        match = J.ENTRY_NAME.match(name)
        envelope = J.parse_entry(files[name]) if match else None
        if envelope is not None and int(match.group(1)) not in chosen:
            chosen[int(match.group(1))] = envelope
    return [chosen[n] for n in sorted(chosen)]


def _partial_decisions(records: list[dict[str, Any]], data_root: Path) -> list[dict[str, Any]] | str:
    """B-N4: R6's gold-blind routing of the cases whose every tier has a determinable record, pinned, against
    the frozen table. Cases missing any tier are left out, never routed on a partial view."""
    from g_route3_contract import TIER_ORDER
    from g_route3_qualification import load_frozen_table
    from g_route3_validation import decide
    table_path = data_root / "tables" / "QUALIFICATION_TABLE.json"
    if not table_path.is_file():
        return "no_frozen_table"
    table = platform.run_pinned(load_frozen_table, table_path)
    tiers: dict[str, set] = {}
    for record in records:
        tiers.setdefault(record["fixture_id"], set()).add(record["model_tier"])
    complete = {fixture_id for fixture_id, seen in tiers.items() if seen >= set(TIER_ORDER)}
    decisions = platform.run_pinned(decide, [r for r in records if r["fixture_id"] in complete], table)
    return [d for d in decisions if d["fixture_id"] in complete]


def _run_created_of(data_root: Path, phase: str, run_id: str) -> dict[str, Any]:
    import g_route3_journal as J
    data = platform.raw_read(data_root / f"phase_{phase.lower()}" / "runs" / run_id / "journal" / "000001.json")
    envelope = J.parse_entry(data)
    if envelope is None or envelope["kind"] != "run_created":
        raise InputsDrifted("run_created_unreadable")
    return envelope["payload"]


def score_run(request: Mapping[str, Any]) -> dict[str, Any]:
    import g_route3_journal as J
    phase, run_id, data_root = request["phase"], request["run_id"], Path(request["data_root"])
    run_created = _run_created_of(data_root, phase, run_id)
    guarded = run_created["guarded_files"]
    bind_inputs(guarded, data_root)                                                    # B-O2 before
    from g_route3_qualification import attach_semantics, load_frozen_table, qualify
    spec, schedule, fixtures = run_spec(phase)
    files, extra = read_journal(data_root / f"phase_{phase.lower()}" / "runs" / run_id / "journal")
    replay = J.replay_run(files, spec, extra_names=extra)
    if replay.state not in ("scoring_interrupted", "torn_pending"):
        return {"error": f"scorer_state:{replay.state}"}
    records, mismatched = rebuild_records(replay.entries, phase, schedule, fixtures, check_executables=True)
    if mismatched:
        return {"error": f"stored_executable_or_call_differs:{mismatched}"}           # C-O5
    if len(records) != spec.calls:
        return {"error": "scorer_requires_every_record"}
    rows = partial_results(phase, data_root, list(request.get("attempts") or []), schedule, fixtures, guarded)
    orphans = list(request.get("orphans_cleared") or [])
    if phase == "A":
        cells = platform.run_pinned(qualify, platform.run_pinned(attach_semantics, records, "A"))
        report = {"contract_version": "g-route3.phase-a-score.v1", "phase": "A", "cells": cells,
                  "qualified_cells": sum(c["verdict"] == "qualified" for c in cells),
                  "insufficient_cells": sum(c["verdict"] == "insufficient_evidence" for c in cells),
                  "table_frozen": False, "corpus_b_consulted": False, "belief_effects": "none",
                  "attempt_disclosure": rows, "orphans_cleared": orphans}
    else:
        from g_route3_validation import score
        table = platform.run_pinned(load_frozen_table, data_root / "tables" / "QUALIFICATION_TABLE.json")
        if table["table_sha256"] != run_created.get("table_sha256"):
            return {"error": "qualification_table_mutated"}
        report = {**platform.run_pinned(score, records, table), "synthetic_fixture": bool(run_created.get("synthetic")),
                  "phase_b_attempts": rows, "phase_a_run_id": run_created.get("phase_a_run_id"),
                  "orphans_cleared": orphans}
    recheck_inputs(guarded, data_root)                                                 # B-O2 after
    return {"report": json.loads(json.dumps(J.safe_value(report)))}


def phase_a_cells(request: Mapping[str, Any]) -> dict[str, Any]:
    """§10.6: cells re-derived from a completed Phase A attempt's facts."""
    import g_route3_journal as J
    data_root = Path(request["data_root"])
    run_created = _run_created_of(data_root, "A", request["run_id"])
    bind_inputs(run_created["guarded_files"], data_root)
    from g_route3_qualification import attach_semantics, qualify
    spec, schedule, fixtures = run_spec("A")
    files, extra = read_journal(data_root / "phase_a" / "runs" / request["run_id"] / "journal")
    replay = J.replay_run(files, spec, extra_names=extra)
    if replay.state != "completed":
        return {"error": f"phase_a_state:{replay.state}"}
    records, mismatched = rebuild_records(replay.entries, "A", schedule, fixtures, check_executables=True)
    if mismatched:
        return {"error": f"stored_executable_or_call_differs:{mismatched}"}
    cells = platform.run_pinned(qualify, platform.run_pinned(attach_semantics, records, "A"))
    recheck_inputs(run_created["guarded_files"], data_root)
    return {"cells": cells}


def build_qualification_table(request: Mapping[str, Any]) -> dict[str, Any]:
    """R6's build_table, verbatim, with the R7 binding block added before the digest (§7 --freeze-table)."""
    data_root = Path(request["data_root"])
    run_created = _run_created_of(data_root, "A", request["run_id"])
    bind_inputs(run_created["guarded_files"], data_root)
    from g_route3_qualification import audit_record, build_table, json_digest, verify_table
    audit = audit_record(Path(request["audit_copy"]), request["verdict"], request["auditor"],
                         run_id=request["run_id"], score_record_sha256=request["scored_sha256"])
    spec, schedule, fixtures = run_spec("A")
    rows = partial_results("A", data_root, list(request["attempts"]), schedule, fixtures,
                           run_created["guarded_files"])
    doc = platform.run_pinned(build_table, request["cells"], run_id=request["run_id"],
                              score_record_sha256=request["scored_sha256"],
                              execution_freeze_binding=request["freeze_binding"], audit=audit, phase_a_attempts=rows)
    doc.pop("table_sha256")
    doc["r7_binding"] = {"run_created_sha256": request["run_created_sha256"],
                         "scored_sha256": request["scored_sha256"],
                         "terminal_evidence_commit": request["terminal_commit"],
                         "audit_copy": "tables/" + Path(request["audit_copy"]).name,
                         "data_root": str(data_root), "orphans_cleared": list(request.get("orphans_cleared") or [])}
    doc["table_sha256"] = json_digest(doc)
    check = verify_table(doc)
    if not check["valid"]:
        return {"error": "table_does_not_verify:" + ",".join(check["reasons"])}
    recheck_inputs(run_created["guarded_files"], data_root)
    return {"table": doc}


def attempt_rows(request: Mapping[str, Any]) -> dict[str, Any]:
    """The table's attempt disclosure recomputed now (§10.8)."""
    data_root = Path(request["data_root"])
    run_created = _run_created_of(data_root, request["phase"], request["reference_run_id"])
    bind_inputs(run_created["guarded_files"], data_root)
    spec, schedule, fixtures = run_spec(request["phase"])
    return {"rows": partial_results(request["phase"], data_root, list(request["attempts"]), schedule, fixtures,
                                    run_created["guarded_files"])}


MODES = {"score_run": score_run, "phase_a_cells": phase_a_cells, "build_table": build_qualification_table,
         "attempt_rows": attempt_rows}


def main() -> int:
    platform.pin_recursion_limit()
    platform.join_kill_on_close_job()
    platform.install_import_hashing(ROOT)
    platform.record_source(Path(__file__))
    request = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    try:
        result = MODES[request["mode"]](request)
    except Exception as exc:  # noqa: BLE001 - reported to the holder, which refuses (J13)
        result = {"error": f"{type(exc).__name__}:{exc}"[:500]}
    result["module_digests"] = platform.loaded_source_digests()
    sys.stdout.buffer.write(json.dumps(result, sort_keys=True, ensure_ascii=True).encode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
