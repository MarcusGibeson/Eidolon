from __future__ import annotations

"""G-ROUTE4 differentials against the prior experiment (design "Certification and differential"; O7).

Both differentials run the prior experiment's modules only in a separate child process, so no G-ROUTE4 process loads
them (the module rule), and both sides receive identical injected inputs.

1. Grading differential (the proof that forked grading equals the prior grading where the rules coincide). Entry
   points under test: collect_evaluation, safe_normalize, sealable, attach_semantics, validation.decide and
   scorer.rebuild_records. In each process, the fixture and gold lookups are replaced, where they are bound, by the same
   synthetic fixtures and gold, with ids mapped through the identity table; the raw outputs cover correct, wrong,
   fenced, malformed, non-hashable, lone-surrogate, CRLF and empty outputs; one routing lookup over the 20 shared
   task|risk keys is applied at the decide level, never through verify_table. Required equal, per record:
   normalization, operational results, semantic results, and routing and escalation decisions.

2. Lifecycle differential: see `lifecycle_differential` (a shared four-position non-coding synthetic schedule through
   the prior R7 and this fork, with a shared stub scorer, compared after the design's normalization).

    python -B tools/g_route4_differential.py [--only grading|lifecycle] [--out REPORT.json]
"""

import argparse
import base64
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

PRIOR_PREFIX = "g_route3"
FORK_PREFIX = "g_route4"
# identity table (design "Identity constants"): fork value -> prior value, for ids that differ between the sides
ID_MAP = (("A4-", "A-"), ("B4-", "B-"), ("GROUTE4-", "GROUTE3-"))
TIERS = ("small", "mid", "large")
OUTPUT_KINDS = ("correct", "wrong", "fenced", "malformed", "nonhashable", "lone_surrogate", "crlf", "empty")


def to_prior(text: str) -> str:
    for fork, prior in ID_MAP:
        text = text.replace(fork, prior)
    return text


def to_fork(text: str) -> str:
    for fork, prior in ID_MAP:
        text = text.replace(prior, fork)
    return text


def map_ids(value: Any, fn) -> Any:
    if isinstance(value, str):
        return fn(value)
    if isinstance(value, list):
        return [map_ids(v, fn) for v in value]
    if isinstance(value, dict):
        return {fn(k) if isinstance(k, str) else k: map_ids(v, fn) for k, v in value.items()}
    return value


# ---------------------------------------------------------------- grading differential: the shared inputs
def synthetic_inputs() -> dict[str, Any]:
    """The shared synthetic fixtures and gold (drawn from the G-ROUTE4 corpus: two per class and phase, one R4), the
    raw outputs for every fixture x tier, and the shared routing lookup. Built once, in the parent."""
    import g_route4_contract as C
    fixtures, gold = {}, {}
    for corpus in ("A", "B"):
        index = C.indexed_fixture_gold(corpus)
        for task in C.TASK_CLASSES:
            chosen = [fid for fid in sorted(index) if index[fid][0]["task_class"] == task][:2]
            if corpus == "B":
                chosen += [fid for fid in sorted(index) if index[fid][0]["task_class"] == task
                           and index[fid][0]["consequence_risk"] == "R4"][:1]
            for fid in chosen:
                fixtures[fid], gold[fid] = index[fid]
    outputs = {}
    for fid, fixture in fixtures.items():
        for n, tier in enumerate(TIERS):
            ref = gold[fid]["reference_output"]
            correct = ref if isinstance(ref, str) else json.dumps(ref, sort_keys=True)
            kind = OUTPUT_KINDS[(sum(map(ord, fid)) + n) % len(OUTPUT_KINDS)]
            raw = {"correct": correct,
                   "wrong": correct.replace("Answer: ", "Answer: x") if fixture["validator_profile"] == "conversation.v1"
                   else correct[: len(correct) // 2],
                   "fenced": "```json\n" + correct + "\n```",
                   "malformed": "{not json",
                   "nonhashable": "[" * 5000 + "]" * 5000,
                   "lone_surrogate": correct + "\ud800",
                   "crlf": correct.replace("\n", "\r\n") + "\r\n",
                   "empty": ""}[kind]
            outputs[f"{fid}|{tier}"] = {"kind": kind, "raw": raw}
    lookup = {f"{task}|{risk}": ["mid", "large"] if (len(task) + int(risk[1])) % 2 else ["small"]
              for task in C.TASK_CLASSES for risk in C.RISK_CLASSES}
    return {"fixtures": fixtures, "gold": gold, "outputs": outputs, "lookup": lookup}


def _encode(inputs: dict[str, Any]) -> str:
    """JSON with lone surrogates carried losslessly (surrogatepass, base64)."""
    return base64.b64encode(json.dumps(inputs, ensure_ascii=False).encode("utf-8", "surrogatepass")).decode("ascii")


def _decode(text: str) -> Any:
    return json.loads(base64.b64decode(text).decode("utf-8", "surrogatepass"))


# ---------------------------------------------------------------- grading differential: one side (child process)
def grading_side(side: str, payload: str) -> dict[str, Any]:
    """Run the six entry points of one side on the shared inputs. The prior side's modules are imported only here, in
    its own process."""
    prefix = PRIOR_PREFIX if side == "prior" else FORK_PREFIX
    fn = to_prior if side == "prior" else (lambda s: s)
    inputs = map_ids(_decode(payload), fn)
    contract = __import__(f"{prefix}_contract")
    qualification = __import__(f"{prefix}_qualification")
    validation = __import__(f"{prefix}_validation")
    scorer = __import__(f"{prefix}_scorer")
    platform = __import__(f"{prefix}_platform")
    journal = __import__(f"{prefix}_journal")
    platform.pin_recursion_limit()
    fixtures, gold = inputs["fixtures"], inputs["gold"]
    by_corpus = {c: {fid: f for fid, f in fixtures.items() if fid.startswith(fn(f"{c}4-"))} for c in "AB"}

    def indexed(corpus):
        return {fid: (fixtures[fid], gold[fid]) for fid in by_corpus[corpus]}

    def runtime(corpus):
        return dict(by_corpus[corpus])
    # inject where bound (from-imports bind the names into each module)
    qualification.indexed_fixture_gold = indexed
    validation.runtime_fixtures = runtime
    out: dict[str, Any] = {"records": {}, "decisions": {}, "rebuild": {}}
    records_by_corpus: dict[str, list] = {"A": [], "B": []}
    for key, row in inputs["outputs"].items():
        fid, tier = key.split("|")
        fixture = fixtures[fid]
        raw = row["raw"]
        evaluation = platform.run_pinned(qualification.collect_evaluation, fixture, raw)
        normalized = platform.run_pinned(qualification.safe_normalize, raw, fixture["validator_profile"])
        sealed = qualification.sealable({"contract_version": "x", "accepted": True, "reasons": [],
                                         "parsed_output": _deep(4000)}, gate="accepted")
        record = {"fixture_id": fid, "task_class": fixture["task_class"], "risk_class": fixture["consequence_risk"],
                  "model_tier": tier, "model": "m", "returned_model": "m", "infrastructure_failure": "",
                  "raw_output": raw, **evaluation}
        corpus = "A" if fid.startswith(fn("A4-")) else "B"
        records_by_corpus[corpus].append(record)
        out["records"][key] = {"collect_evaluation": _plain(evaluation), "safe_normalize": _plain(normalized),
                               "sealable": _plain(sealed)}
    for corpus in "AB":
        judged = qualification.attach_semantics(records_by_corpus[corpus], corpus)
        for row in judged:
            out["records"][f"{row['fixture_id']}|{row['model_tier']}"]["attach_semantics"] = _plain(row["semantics"])
    table = {"routing_lookup": inputs["lookup"], "cells": [], "table_sha256": "shared"}
    for decision in validation.decide(records_by_corpus["B"], table):
        out["decisions"][decision["fixture_id"]] = _plain(decision)
    # scorer.rebuild_records over a synthetic journal of the B records
    schedule, entries, previous = [], [], "0" * 64
    for position, row in enumerate(sorted(records_by_corpus["B"], key=lambda r: (r["fixture_id"], r["model_tier"])), 1):
        scheduled = {"call_id": f"{fn('GROUTE4-')}{row['fixture_id']}-R1-{row['model_tier']}", "fixture_id": row["fixture_id"],
                     "model_tier": row["model_tier"], "model": "qwen2.5:7b", "seed": 480000 + position, "position": position,
                     "repeat": 1, "task_class": row["task_class"], "risk_class": row["risk_class"]}
        schedule.append(scheduled)
        body = contract.request_body(fixtures[row["fixture_id"]], scheduled)
        b64, sha = journal.text_to_b64(row["raw_output"])
        envelope = {"model": "qwen2.5:7b", "response": row["raw_output"], "done": True}
        raw_body = json.dumps(envelope).encode("utf-8", "surrogatepass")
        for kind, payload in (("call_started", {"position": position, "call_id": scheduled["call_id"],
                                                "request_sha256": journal.digest(body)}),
                              ("call_recorded", {"position": position, "call_id": scheduled["call_id"],
                                                 "raw_output_b64": b64, "raw_output_sha256": sha,
                                                 "raw_body_b64": base64.b64encode(raw_body).decode("ascii"),
                                                 "raw_body_sha256": hashlib.sha256(raw_body).hexdigest(),
                                                 "returned_model": "qwen2.5:7b", "transport_failure": "",
                                                 "provider_contacted": True, "latency_seconds": 1.0,
                                                 "metrics": {"eval_count": 10}})):
            envelope_entry, _ = journal.make_entry(len(entries) + 1, kind, "run-x", previous, payload)
            previous = envelope_entry["record_sha256"]
            entries.append(envelope_entry)
    if side == "prior":
        rebuilt, mismatched = scorer.rebuild_records(entries, "B", schedule, by_corpus["B"], check_executables=False)
    else:
        rebuilt, mismatched = scorer.rebuild_records(entries, "B", schedule, by_corpus["B"])
    out["rebuild_mismatched"] = {str(k): v for k, v in mismatched.items()}
    for row in rebuilt:
        out["rebuild"][f"{row['fixture_id']}|{row['model_tier']}"] = _plain(
            {k: row[k] for k in ("normalization", "raw_operational_validation", "normalized_operational_validation",
                                 "raw_output", "infrastructure_failure", "request_body_sha256")})
    return map_ids(out, to_fork if side == "prior" else (lambda s: s))


def _deep(depth: int) -> Any:
    value: Any = []
    for _ in range(depth):
        value = [value]
    return value


def _plain(value: Any) -> Any:
    """A JSON-safe copy (lone surrogates kept through surrogatepass round-trips)."""
    return json.loads(json.dumps(value, ensure_ascii=True, default=str))


def _child(side: str, mode: str, payload: str) -> dict[str, Any]:
    code = ("import sys, json; sys.path.insert(0, %r); sys.setrecursionlimit(10000); import g_route4_differential as D; "
            "payload = sys.stdin.read(); "
            "result = D.grading_side(%r, payload) if %r == 'grading' else D.lifecycle_side(%r, payload); "
            "sys.stdout.write(D._encode(result))" % (str(TOOLS), side, mode, side))
    done = subprocess.run([sys.executable, "-B", "-c", code], input=payload, capture_output=True, text=True,
                          timeout=3600)
    if done.returncode != 0:
        raise RuntimeError(f"{side} side failed: {done.stderr[-2000:]}")
    return _decode(done.stdout)


def grading_differential(*, perturb_fork: bool = False) -> dict[str, Any]:
    inputs = synthetic_inputs()
    payload = _encode(inputs)
    fork_inputs = copy.deepcopy(inputs)
    if perturb_fork:                                   # sensitivity: one output differs on the fork side only
        key = next(k for k, v in sorted(fork_inputs["outputs"].items()) if v["kind"] == "correct")
        fork_inputs["outputs"][key]["raw"] = "{not json"
    prior, fork = _child("prior", "grading", payload), _child("fork", "grading", _encode(fork_inputs))
    differences = []
    fields = ("collect_evaluation", "safe_normalize", "sealable", "attach_semantics")
    for key in sorted(set(prior["records"]) | set(fork["records"])):
        p, f = prior["records"].get(key, {}), fork["records"].get(key, {})
        for field in fields:
            if _strip_contract(p.get(field)) != _strip_contract(f.get(field)):
                differences.append({"record": key, "field": field})
    for fid in sorted(set(prior["decisions"]) | set(fork["decisions"])):
        if _strip_contract(prior["decisions"].get(fid)) != _strip_contract(fork["decisions"].get(fid)):
            differences.append({"decision": fid})
    if prior["rebuild_mismatched"] != fork["rebuild_mismatched"]:
        differences.append({"rebuild_mismatched": [prior["rebuild_mismatched"], fork["rebuild_mismatched"]]})
    for key in sorted(set(prior["rebuild"]) | set(fork["rebuild"])):
        if prior["rebuild"].get(key) != fork["rebuild"].get(key):
            differences.append({"rebuild_record": key})
    kinds = {}
    for row in inputs["outputs"].values():
        kinds[row["kind"]] = kinds.get(row["kind"], 0) + 1
    return {"records_compared": len(fork["records"]), "decisions_compared": len(fork["decisions"]),
            "rebuilt_records_compared": len(fork["rebuild"]), "output_kinds": kinds,
            "fields": list(fields) + ["decide", "rebuild_records"], "differences": differences[:50],
            "difference_count": len(differences), "passed": not differences}


# Contract ids of forked modules differ by design (renamed ids); they are the only fields excluded from equality, and
# only under these keys.
CONTRACT_KEYS = ("contract_version",)


def _strip_contract(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _strip_contract(v) for k, v in value.items()
                if not (k in CONTRACT_KEYS and isinstance(v, str) and ("g-route3." in v or "g-route4." in v)
                        and not v.startswith(("g-route3.operational", "g-route3.semantics", "g-route3.conversation",
                                              "g-route3.triggers", "g-route3.routing")))}
    if isinstance(value, list):
        return [_strip_contract(v) for v in value]
    return value


# ---------------------------------------------------------------- lifecycle differential
def lifecycle_side(side: str, payload: str) -> dict[str, Any]:
    raise NotImplementedError("lifecycle differential: see lifecycle_differential")


def lifecycle_differential() -> dict[str, Any]:
    raise NotImplementedError("lifecycle differential not yet implemented")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=("grading", "lifecycle"))
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    report: dict[str, Any] = {"schema_version": "g-route4.differential.v1"}
    if args.only in (None, "grading"):
        report["grading"] = grading_differential()
        sensitivity = grading_differential(perturb_fork=True)
        report["grading_sensitivity"] = {"perturbed_outputs": 1, "differences_found": sensitivity["difference_count"],
                                         "passed": sensitivity["difference_count"] > 0}
    if args.only in (None, "lifecycle"):
        report["lifecycle"] = lifecycle_differential()
    report["passed"] = all(part.get("passed") for key, part in report.items() if isinstance(part, dict))
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: ({kk: vv for kk, vv in v.items() if kk != "differences"} if isinstance(v, dict) else v)
                      for k, v in report.items()}, indent=1))
    for part in report.values():
        if isinstance(part, dict):
            for d in part.get("differences", [])[:10]:
                print("  DIFF", d)
    print("DIFFERENTIAL", "PASS" if report["passed"] else "FAIL")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
