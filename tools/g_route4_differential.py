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
def _stub_json_digest(value: Any) -> str:
    """The identical injected json_digest of both sides (O7); normalization recomputes with the same function."""
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _unreached(name: str):
    def call(*args, **kwargs):
        raise RuntimeError(f"o7_unreached_call_reached:{name}")
    return call


# O7: the disposition of every function-level import of a per-side module in the lifecycle (both sides). Imports of
# the unchanged G-ROUTE1 modules load the same module in both processes and need none.
O7_DISPOSITIONS = {
    "contract.request_body": "identical injected stub in both processes (the shared request bodies); the "
                             "collection path also reads Runtime.bodies",
    "contract.json_digest": "identical injected stub in both processes (_stub_json_digest)",
    "qualification.verify_table": "identical injected stub in both processes (valid)",
    "contract.EXECUTION_FREEZE_PATH": "inside standard_guarded_files, replaced by a raising stub in both processes "
                                      "(unreached: Runtime.guarded_files injected)",
    "runner.GUARDED_PATHS": "inside standard_guarded_files / load_bound_inputs, both replaced by raising stubs in both "
                            "processes (unreached: Runtime injection)",
    "contract.runtime_fixtures": "inside load_bound_inputs, replaced by a raising stub in both processes (unreached)",
    "contract.verify_checked_schedule": "inside load_bound_inputs, replaced by a raising stub in both processes "
                                        "(unreached)",
    "worker.derive_executable": "prior side only, inside _execute (execution kinds): the prior worker module is "
                                "replaced by a raising stub; unreached, the shared schedule is non-coding",
}


def module_bound_calls(prefix: str) -> list[dict[str, Any]]:
    """Every function-level `from <module> import <name>` in the side's lifecycle module (static reading)."""
    import ast
    source = (Path(__file__).resolve().parent / f"{prefix}_lifecycle.py").read_text(encoding="utf-8")
    found = []
    for function in ast.walk(ast.parse(source)):
        if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for node in ast.walk(function):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("g_route"):
                for alias in node.names:
                    shared = node.module.startswith("g_route1_")
                    key = node.module.split("_", 2)[2] + "." + alias.name
                    found.append({"function": function.name, "line": node.lineno, "module": node.module,
                                  "name": alias.name, "shared_unchanged_module": shared,
                                  "disposition": "same module loaded in both processes" if shared
                                  else O7_DISPOSITIONS.get(key)})
    return sorted(found, key=lambda row: row["line"])


def lifecycle_inputs() -> dict[str, Any]:
    """The shared inputs of the lifecycle differential, built once in the parent: a four-position non-coding
    synthetic schedule per phase (the first four positions of the frozen schedules), their fixtures and request
    bodies, the model receipts, the freeze binding and the guarded-file map. Both sides receive them unchanged."""
    import g_route4_contract as C
    schedules = {p: [dict(row, position=i + 1) for i, row in enumerate(C.verify_checked_schedule(p)[:4])] for p in "AB"}
    fixtures = {p: {row["fixture_id"]: C.runtime_fixtures(p)[row["fixture_id"]] for row in schedules[p]} for p in "AB"}
    bodies = {p: [C.request_body(fixtures[p][row["fixture_id"]], row) for row in schedules[p]] for p in "AB"}
    bindings = C.load_model_bindings()
    receipts = [{"provider_version": bindings["provider_version"], "requested_model": r["model"],
                 "resolved_model": r["model"], "manifest_digest": r["manifest_digest"],
                 "model_blob_sha256": r["model_blob_sha256"], "generation_configuration": bindings["generation_configuration"],
                 "silent_fallback": False} for r in bindings["bindings"]]
    return {"schedules": schedules, "fixtures": fixtures, "bodies": bodies, "receipts": receipts,
            "freeze_binding": "f" * 64, "guarded": {"tools/differential_guarded_stub.py": "a" * 64}}


class _StubProvider:
    """Identical deterministic provider on both sides: the output is a function of the call id alone."""
    synthetic_provider = True

    def __call__(self, call_id: str, body: Any) -> dict[str, Any]:
        raw = f"synthetic output for {call_id}"
        envelope = {"model": body["model"], "response": raw, "done": True, "eval_count": 7, "prompt_eval_count": 11}
        data = json.dumps(envelope, sort_keys=True).encode("utf-8")
        return {"raw_output": raw, "returned_model": body["model"], "raw_body_b64": base64.b64encode(data).decode("ascii"),
                "raw_body_sha256": hashlib.sha256(data).hexdigest(), "output_field": "response",
                "metrics": {"eval_count": 7, "prompt_eval_count": 11}, "latency_seconds": 1.0,
                "provider_contacted": True, "error": ""}


def _shared_stub_scorer(J, contract, specs):
    """The shared stub scorer (identical on both sides): every mode is a pure function of the run's own journal and
    the request, so the derived scored/completed payloads compare equal."""
    def facts(request, phase):
        directory = Path(request["data_root"]) / f"phase_{phase.lower()}" / "runs" / request["run_id"] / "journal"
        files = {q.name: q.read_bytes() for q in directory.iterdir() if J.ENTRY_NAME.match(q.name)}
        replay = J.replay_run(files, specs[phase])
        return [e["payload"].get("raw_output_sha256") for e in replay.entries if e["kind"] == "call_recorded"]

    def cells(values):
        return [{"cell": index, "fact": value, "verdict": "qualified"} for index, value in enumerate(values)]

    def call(request):
        mode = request["mode"]
        if mode == "score_run":
            values = facts(request, request["phase"])
            report = {"facts_digest": J.digest(values), "attempts": list(request.get("attempts") or [])}
            if request["phase"] == "A":
                report["cells"] = cells(values)
            return {"report": report}
        if mode == "phase_a_cells":
            return {"cells": cells(facts(dict(request, phase="A"), "A"))}
        if mode == "attempt_rows":
            return {"rows": list(request.get("attempts") or [])}
        if mode == "build_table":
            audit = Path(request["audit_copy"]).read_bytes()
            body = {"schema_version": "differential.stub-table", "cells": request["cells"],
                    "source": {"run_id": request["run_id"], "execution_freeze_binding": request["freeze_binding"],
                               "phase_a_attempts": json.loads(json.dumps(J.safe_value(request["attempts"])))},
                    "audit": {"document_sha256": hashlib.sha256(audit).hexdigest(), "auditor": request["auditor"],
                              "verdict": request["verdict"]},
                    "r7_binding": {"run_created_sha256": request["run_created_sha256"],
                                   "scored_sha256": request["scored_sha256"],
                                   "terminal_evidence_commit": request["terminal_commit"]}}
            body["table_sha256"] = contract.json_digest(body)
            return {"table": body}
        raise ValueError(f"unknown scorer mode {mode}")
    return call


def lifecycle_side(side: str, payload: str) -> dict[str, Any]:
    """Drive setup, Phase A, the table freeze and Phase B on one side, with the shared inputs, then dump the evidence
    repository's commit chain (every committed file of the data root). Runs in its own process."""
    import tempfile
    prefix = PRIOR_PREFIX if side == "prior" else FORK_PREFIX
    experiment = "G-ROUTE3" if side == "prior" else "G-ROUTE4"
    inputs = _decode(payload)
    J = __import__(f"{prefix}_journal")
    L = __import__(f"{prefix}_lifecycle")
    F = __import__(f"{prefix}_fs")
    P = __import__(f"{prefix}_platform")
    C = __import__(f"{prefix}_contract")
    Q = __import__(f"{prefix}_qualification")
    R = __import__(f"{prefix}_runner")
    P.pin_recursion_limit()
    bodies = inputs["bodies"]
    by_call = {row["call_id"]: bodies[p][i] for p in "AB" for i, row in enumerate(inputs["schedules"][p])}
    # O7: module-bound calls replaced by identical stubs, where they are bound
    C.request_body = lambda fixture, call: by_call[call["call_id"]]
    C.json_digest = _stub_json_digest
    Q.verify_table = lambda doc: {"valid": True, "reasons": [], "table_sha256": doc.get("table_sha256")}
    L.standard_guarded_files = _unreached("standard_guarded_files")
    L.load_bound_inputs = _unreached("load_bound_inputs")
    C.runtime_fixtures = _unreached("runtime_fixtures")
    C.verify_checked_schedule = _unreached("verify_checked_schedule")
    if side == "prior":
        import types
        worker = types.ModuleType(f"{prefix}_worker")
        worker.derive_executable = _unreached("derive_executable")
        sys.modules[worker.__name__] = worker
    specs = {p: J.RunSpec(call_ids=tuple(r["call_id"] for r in inputs["schedules"][p]), coding=frozenset()) for p in "AB"}
    work = Path(tempfile.mkdtemp(prefix=f"g4diff_{side}_"))
    D = work / "D"
    settings = dict(data_root=D, fs=F.RealFs(), provider=_StubProvider(), model_receipts=lambda: inputs["receipts"],
                    verify_receipts=R.verify_model_receipts, freeze_binding=lambda: inputs["freeze_binding"],
                    freeze_valid=lambda: True, guarded_files=lambda phase: dict(inputs["guarded"]),
                    scorer=_shared_stub_scorer(J, C, specs), schedules=inputs["schedules"], fixtures=inputs["fixtures"],
                    synthetic=True, endpoint="synthetic", bodies=bodies, table_on_main=lambda data: True)
    if side == "prior":
        settings["worker"] = lambda request: (_ for _ in ()).throw(RuntimeError("no_worker_in_a_non_coding_schedule"))
    runtime = L.Runtime(**settings)

    def command(method, *args):
        lc = L.Lifecycle(runtime)
        lc.open()
        try:
            return getattr(lc, method)(*args)
        finally:
            lc.close()
    L.Lifecycle(runtime).setup_if_missing()
    binding = inputs["freeze_binding"]
    out_a = command("command_launch", "A", f"Authorize {experiment} phase A execution {binding} attempt 1", 1, False)
    journal = D / "phase_a" / "runs" / out_a["run_id"] / "journal"
    entries = [J.parse_entry(q.read_bytes()) for q in sorted(journal.glob("*.json"))]
    scored = next(e for e in entries if e["kind"] == "scored")
    audit = work / "audit.md"
    audit.write_bytes((f"READY audit of {out_a['run_id']} scored {scored['record_sha256']} "
                       f"run_created {entries[0]['record_sha256']}\n").encode("utf-8"))
    frozen = command("command_freeze_table", 1, binding, audit, "differential", "READY")
    sentence_b = f"Authorize {experiment} phase B execution {binding} table {frozen['table_sha256']} attempt 1"
    out_b = command("command_launch_b", sentence_b, 1, False, frozen["table_sha256"], 1)
    # dump the evidence repository's commit chain
    lc = L.Lifecycle(runtime)
    lc.open()
    try:
        repo = lc.repo
        ref = __import__(f"{prefix}_evidence").REF
        commits = repo.git("rev-list", "--reverse", ref).decode().split()
        chain = []
        for commit in commits:
            raw = repo.git("cat-file", "commit", commit)
            tree = repo.tree(commit)
            chain.append({"id": commit, "raw": base64.b64encode(raw).decode("ascii"), "tree": tree})
        blobs = sorted({b for c in chain for b in c["tree"].values()})
        contents = repo.read_blobs(blobs)
    finally:
        lc.close()
    return {"side": side, "states": {"A": out_a["state"], "table": frozen["state"], "B": out_b["state"]},
            "chain": chain, "blobs": {b: base64.b64encode(contents[b]).decode("ascii") for b in blobs}}


# identity substitutions applied to the prior side (design "Identity constants"; the fork side is the reference)
IDENTITY_SUBSTITUTIONS = (("G-ROUTE3", "G-ROUTE4"), ("g-route3", "g-route4"), ("GROUTE3", "GROUTE4"),
                          ("groute3", "groute4"))
RUN_ID = __import__("re").compile(r"(groute[34][ab]-[0-9]{3,}-)([0-9a-f]{16})")
HEX = __import__("re").compile(r"(?<![0-9a-f])([0-9a-f]{64}|[0-9a-f]{40})(?![0-9a-f])")


def _git_tree(files: dict[str, bytes]) -> tuple[str, dict[str, bytes]]:
    """Git tree objects for {path: bytes}; returns (root tree id, {object id: object bytes})."""
    objects: dict[str, bytes] = {}

    def put(kind: str, body: bytes) -> str:
        data = f"{kind} {len(body)}".encode() + b"\0" + body
        oid = hashlib.sha1(data).hexdigest()
        objects[oid] = data
        return oid

    def build(entries: dict[str, Any]) -> str:
        rows = []
        for name, value in entries.items():
            if isinstance(value, dict):
                rows.append((name + "/", b"40000 " + name.encode() + b"\0" + bytes.fromhex(build(value))))
            else:
                rows.append((name, b"100644 " + name.encode() + b"\0" + bytes.fromhex(put("blob", value))))
        return put("tree", b"".join(row for _, row in sorted(rows)))
    nested: dict[str, Any] = {}
    for path, data in files.items():
        node = nested
        parts = path.split("/")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = data
    return build(nested), objects


def normalize_lifecycle(dump: dict[str, Any], side: str) -> list[dict[str, Any]]:
    """The design's normalization of one side: mask only random tokens (root_id, run tokens); substitute identity
    strings; recompute every derived digest from its substituted preimage (entry and ledger seals, genesis seals,
    sentence and authorization digests, the table and audit digests), never masking one; rebuild the git object chain
    (blob, tree, commit) in order with the substituted identity and message. Returns per commit the rebuilt id and the
    normalized tree."""
    import g_route4_journal as J4
    blobs = {oid: base64.b64decode(data) for oid, data in dump["blobs"].items()}
    chain = dump["chain"]
    final_tree = chain[-1]["tree"]
    root = json.loads(blobs[final_tree["root.json"]].decode("utf-8"))
    root_id = root["root_id"]
    ledger_identity = "g-route3-ledger" if side == "prior" else "g-route4-ledger"

    def substitute(text: str) -> str:
        if side == "prior":
            for old, new in IDENTITY_SUBSTITUTIONS:
                text = text.replace(old, new)
        text = RUN_ID.sub(lambda m: m.group(1) + "RUNTOKEN" + m.group(1)[7:8], text)
        return text.replace(root_id, "ROOTTOKEN")

    mapping: dict[str, str] = {}
    for phase in ("A", "B"):                         # genesis seals: derived from root_id and the ledger identity
        mapping[J4.digest({"genesis": ledger_identity, "phase": phase, "root_id": root_id})] = \
            J4.genesis_seal(phase, "ROOTTOKEN")

    def remap(text: str, own: str | None = None) -> str:
        def one(m):
            value = m.group(1)
            if value == own:
                return value
            return mapping.get(value, value)
        return HEX.sub(one, text)

    # every old derived value, so a reference to one that is not yet recomputed is detected (never left unmapped)
    derived_old = set(mapping) | {c["id"] for c in chain}
    for path, oid in final_tree.items():
        data = blobs[oid]
        if path.endswith(".json") and ("/journal/" in path or "/ledger/" in path):
            envelope = json.loads(data.decode("utf-8"))
            derived_old.add(envelope["record_sha256"])
            sentence = envelope["payload"].get("sentence")
            if sentence is not None:
                derived_old.add(J4.sha256_bytes(sentence.encode("utf-8")))
                derived_old.add(J4.digest({"sentence": sentence, "phase": path.split("/")[0][-1].upper(),
                                           "attempt": envelope["payload"].get("attempt")}))
        if path == "tables/QUALIFICATION_TABLE.json":
            derived_old.add(json.loads(data.decode("utf-8"))["table_sha256"])
        if path == "tables/QUALIFICATION_AUDIT_DOCUMENT":
            derived_old.add(hashlib.sha256(data).hexdigest())

    normalized: dict[str, bytes] = {}

    def unresolved(text: str, own: str | None = None) -> set[str]:
        return {v for v in HEX.findall(text) if v in derived_old and v != own and v not in mapping}

    def try_file(path: str, data: bytes) -> bool:
        text = data.decode("utf-8")
        if path.endswith(".json") and ("/journal/" in path or "/ledger/" in path):
            envelope = json.loads(text)
            own = envelope["record_sha256"]
            sentence = envelope["payload"].get("sentence")
            phase = path.split("/")[0][-1].upper()
            if sentence is not None:
                if unresolved(sentence):
                    return False
                new_sentence = remap(substitute(sentence))
                mapping[J4.sha256_bytes(sentence.encode("utf-8"))] = J4.sha256_bytes(new_sentence.encode("utf-8"))
                mapping[J4.digest({"sentence": sentence, "phase": phase, "attempt": envelope["payload"].get("attempt")})] = \
                    J4.digest({"sentence": new_sentence, "phase": phase, "attempt": envelope["payload"].get("attempt")})
            if unresolved(text, own):
                return False
            fields = json.loads(remap(substitute(text), own))
            new_envelope, new_bytes = J4.make_entry(fields["entry"], fields["kind"], fields["run_id"],
                                                    fields["previous_entry_sha256"], fields["payload"],
                                                    acknowledges=fields["acknowledges"], orphans=fields["orphans"])
            mapping[own] = new_envelope["record_sha256"]
            normalized[path] = new_bytes
            return True
        if path == "tables/QUALIFICATION_TABLE.json":
            table = json.loads(text)
            own = table["table_sha256"]
            if unresolved(text, own):
                return False
            body = {k: v for k, v in json.loads(remap(substitute(text), own)).items() if k != "table_sha256"}
            body["table_sha256"] = _stub_json_digest(body)
            mapping[own] = body["table_sha256"]
            normalized[path] = (json.dumps(body, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
            return True
        if unresolved(text):
            return False
        new = remap(substitute(text)).encode("utf-8")
        if path == "tables/QUALIFICATION_AUDIT_DOCUMENT":
            mapping[hashlib.sha256(data).hexdigest()] = hashlib.sha256(new).hexdigest()
        normalized[path] = new
        return True

    out = []
    seen_paths: set[str] = set()
    for commit in chain:
        pending = [p for p in sorted(commit["tree"]) if p not in seen_paths]
        for _ in range(len(pending) + 1):                 # fixpoint within the commit
            pending = [p for p in pending if not try_file(p, blobs[commit["tree"][p]])]
            if not pending:
                break
        if pending:
            raise ValueError(f"unresolvable derived references in {pending}")
        seen_paths |= set(commit["tree"])
        files = {substitute(p): normalized[p] for p in commit["tree"]}
        tree_id, _ = _git_tree(files)
        raw = base64.b64decode(commit["raw"]).decode("utf-8")
        header, message = raw.split("\n\n", 1)
        lines = []
        for line in header.split("\n"):
            key, _, value = line.partition(" ")
            if key == "tree":
                lines.append("tree " + tree_id)
            elif key == "parent":
                lines.append("parent " + mapping[value])
            else:
                lines.append(substitute(line))
        body = ("\n".join(lines) + "\n\n" + substitute(message)).encode("utf-8")
        new_id = hashlib.sha1(f"commit {len(body)}".encode() + b"\0" + body).hexdigest()
        mapping[commit["id"]] = new_id
        out.append({"id": new_id, "message": substitute(message).strip(),
                    "files": {k: v.decode("utf-8") for k, v in files.items()}})
    return out


def lifecycle_differential() -> dict[str, Any]:
    """The lifecycle differential: a shared four-position non-coding synthetic schedule per phase through the prior R7
    (in its own process) and this fork, with identical injected inputs and a shared stub scorer, from setup through
    Phase A, the table freeze and Phase B; compared after the design's normalization. Zero residual differences are
    allowed. A sensitivity run perturbs one file of the fork side after the run and must be found."""
    payload = _encode(lifecycle_inputs())
    prior, fork = _child("prior", "lifecycle", payload), _child("fork", "lifecycle", payload)
    states = {"prior": prior["states"], "fork": fork["states"]}
    reached = all(s == {"A": "completed", "table": "frozen", "B": "completed"} for s in states.values())
    a, b = normalize_lifecycle(prior, "prior"), normalize_lifecycle(fork, "fork")

    def compare(x, y):
        diffs = []
        if len(x) != len(y):
            diffs.append({"commits": [len(x), len(y)]})
        for i, (cx, cy) in enumerate(zip(x, y)):
            if cx["message"] != cy["message"]:
                diffs.append({"commit": i, "message": [cx["message"], cy["message"]]})
            for path in sorted(set(cx["files"]) | set(cy["files"])):
                if cx["files"].get(path) != cy["files"].get(path):
                    diffs.append({"commit": i, "path": path})
            if cx["id"] != cy["id"]:
                diffs.append({"commit": i, "rebuilt_id": [cx["id"], cy["id"]]})
        return diffs
    differences = compare(a, b)
    # sensitivity: one committed journal file of the fork side altered in one field must be found
    tampered = json.loads(json.dumps(fork))
    target = next(p for p in sorted(tampered["chain"][-1]["tree"]) if p.endswith("/journal/000003.json"))
    oid = tampered["chain"][-1]["tree"][target]
    original = base64.b64decode(tampered["blobs"][oid])
    changed = original.replace(b'"latency_seconds":1.0', b'"latency_seconds":1.5', 1)
    if changed == original:
        raise ValueError("sensitivity perturbation did not apply")
    tampered["blobs"][oid] = base64.b64encode(changed).decode("ascii")
    sensitivity = compare(a, normalize_lifecycle(tampered, "fork"))
    calls = {side: module_bound_calls(PRIOR_PREFIX if side == "prior" else FORK_PREFIX) for side in ("prior", "fork")}
    undisposed = [dict(row, side=side) for side, rows in calls.items() for row in rows if not row["disposition"]]
    return {"states": states, "reached_completed_on_both_sides": reached, "commits_compared": len(b),
            "files_compared": sum(len(c["files"]) for c in b),
            "normalization": "mask only root_id and run tokens; identity substitutions; every derived digest "
                             "recomputed from its substituted preimage; git blob, tree and commit objects rebuilt",
            "o7_module_bound_calls": calls, "o7_undisposed": undisposed,
            "runtime_injections": "identical in both processes: provider, model receipts, freeze binding, guarded "
                                  "files, schedules, fixtures, request bodies, table_on_main and the shared stub "
                                  "scorer (score_run, phase_a_cells, build_table, attempt_rows)",
            "differences": differences[:50], "difference_count": len(differences),
            "sensitivity": {"perturbed_files": 1, "differences_found": len(sensitivity)},
            "passed": reached and not differences and len(sensitivity) > 0 and not undisposed}


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
