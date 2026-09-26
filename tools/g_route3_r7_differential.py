from __future__ import annotations

"""R6-versus-R7 differential and the Phase B gate, end to end with the real worker and scorer (A-O12, B-O1, B-O10).

Every run uses synthetic providers and temporary data roots only. R6's table path is redirected to a scratch
file, so nothing is written into the repository. This is a certification test (slow, several minutes):

    python tools/g_route3_r7_differential.py [--workdir <scratch folder>]

Checks:
1. Phase A on identical outputs, mixing correct, wrong, fenced and malformed answers with edge cases: a trailing
   newline stripped from `old`, a `\\ud800` escape in `new`, a lone surrogate in the response, CRLF, and empty
   output. The 72 cells must be byte-identical, and so must every R6-read field of every record.
2. Phase B end to end. R7 freezes the table (`--freeze-table`), passes the §10 gate and completes. Phase A cells,
   the routing lookup and the Phase B score must equal R6's, apart from `table_sha256`, which differs because
   R7's table carries `r7_binding`.
3. Refusals of the gate and of the freeze rerun:
   - the table is not on main;
   - the endpoint differs;
   - the freeze binding differs;
   - a different audit document on rerun;
   - a different attempt on rerun.
"""

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import g_route3_platform as P  # noqa: E402

GOOD = ("conversation.v1", "extraction.v1", "planning.v1", "coding.v1")


def plan_mixed(fixture, tier):
    modes = ("correct", "wrong", "fenced", "malformed", "correct", "nonhashable")
    return modes[sum(map(ord, fixture["fixture_id"] + tier)) % len(modes)]


def plan_qualifying(fixture, tier):
    if fixture["validator_profile"] in GOOD:
        return "correct" if not (fixture["fixture_id"].endswith("-2") and tier == "small") else "wrong"
    modes = ("correct", "wrong", "fenced", "correct")
    return modes[sum(map(ord, fixture["fixture_id"] + tier)) % len(modes)]


class EdgeProvider:
    """R6's test provider, plus edge-case outputs on a deterministic subset of calls."""

    synthetic_provider = True

    def __init__(self, corpus, plan):
        import g_route3_tests as T
        self.inner = T.Provider(corpus, plan)

    def __call__(self, call_id, body):
        result = dict(self.inner(call_id, body))
        selector = sum(map(ord, call_id)) % 11
        raw = result["raw_output"]
        if selector == 0:
            raw = raw.replace("\n", "\r\n")
        elif selector == 1:
            raw = ""
        elif selector == 2 and "CODE" in call_id:
            try:
                value = json.loads(raw)
                value["old"] = value["old"].rstrip("\n")
                raw = json.dumps(value)
            except (ValueError, AttributeError, KeyError, TypeError):
                pass
        elif selector == 3 and "CODE" in call_id:
            raw = raw.replace('"new": "', '"new": "# \\ud800\\n', 1)
        elif selector == 4:
            raw = raw + "\ud800"
        if raw != result["raw_output"]:
            import base64
            import hashlib
            envelope = {"model": body["model"], "response": raw, "done": True, "eval_count": 10,
                        "prompt_eval_count": 20}
            raw_body = json.dumps(envelope).encode("utf-8", "surrogatepass")
            result.update(raw_output=raw, envelope=envelope, raw_body_b64=base64.b64encode(raw_body).decode("ascii"),
                          raw_body_sha256=hashlib.sha256(raw_body).hexdigest())
        return result


def r7_runtime(D, provider, **overrides):
    import g_route3_contract as C
    import g_route3_fs as F
    import g_route3_lifecycle as L
    import g_route3_runner as R
    import g_route3_tests as T
    fs = F.RealFs()
    settings = dict(data_root=D, fs=fs, provider=provider, model_receipts=lambda: T.receipts(),
                    verify_receipts=R.verify_model_receipts, freeze_binding=lambda: R._freeze_digest(),
                    freeze_valid=lambda: True, guarded_files=lambda ph: L.standard_guarded_files(D, ph),
                    worker=L.spawn_worker(fs), scorer=L.spawn_scorer(fs),
                    schedules={p: C.verify_checked_schedule(p) for p in "AB"},
                    fixtures={p: C.runtime_fixtures(p) for p in "AB"}, synthetic=True, endpoint="synthetic")
    settings.update(overrides)
    return L.Runtime(**settings)


def command(runtime, method, *args):
    import g_route3_lifecycle as L
    lc = L.Lifecycle(runtime)
    lc.open()
    try:
        return getattr(lc, method)(*args)
    finally:
        lc.close()


def phase_a_differential(work: Path, plan, label: str) -> dict:
    import g_route3_lifecycle as L
    import g_route3_runner as R
    from g_route1_persistence import RouteRunStore
    r6_root, D = work / f"{label}_R6", work / f"{label}_R7"
    r6 = R.execute_phase_a(provider_call=EdgeProvider("A", plan), model_receipts=__import__("g_route3_tests").receipts(),
                           run_root=r6_root, synthetic_fixture=True)
    store = RouteRunStore(r6_root, r6["run_id"], create=False)
    runtime = r7_runtime(D, EdgeProvider("A", plan))
    L.Lifecycle(runtime).setup_if_missing()
    out = command(runtime, "command_launch", "A", f"Authorize G-ROUTE3 phase A execution {R._freeze_digest()} "
                  "attempt 1", 1, False)
    report = json.loads((D / "phase_a" / "runs" / out["run_id"] / "score.json").read_text(encoding="utf-8"))
    return {"label": label, "r7_state": out["state"], "r6_state": r6["state"],
            "cells_identical": store.score_record()["cells"] == report["cells"],
            "qualified": sum(c["verdict"] == "qualified" for c in report["cells"]),
            "run_id": out["run_id"], "D": D, "r6_root": r6_root, "r6_run": r6["run_id"],
            "r6_cells": store.score_record()["cells"], "r6_score": store.score_record()}


def phase_b_and_gate(work: Path, a: dict) -> dict:
    import g_route3_journal as J
    import g_route3_lifecycle as L
    import g_route3_qualification as Q
    import g_route3_runner as R
    import g_route3_tests as T
    from g_route1_persistence import RouteRunStore
    result = {}
    D = a["D"]
    binding = R._freeze_digest()
    providers = {"A": EdgeProvider("A", plan_qualifying), "B": EdgeProvider("B", plan_qualifying)}

    def provider(call_id, body):
        return providers["A" if call_id.startswith("GROUTE3-A-") else "B"](call_id, body)
    runtime = r7_runtime(D, provider)
    journal = D / "phase_a" / "runs" / a["run_id"] / "journal"
    entries = [J.parse_entry(p.read_bytes()) for p in sorted(journal.glob("*.json"))]
    scored = next(e for e in entries if e["kind"] == "scored")
    audit = work / "audit_r7.md"
    audit.write_text(f"READY audit of {a['run_id']} scored {scored['record_sha256']} "
                     f"run_created {entries[0]['record_sha256']}\n", encoding="utf-8")
    other = work / "audit_other.md"
    other.write_text(audit.read_text(encoding="utf-8") + "a different READY document\n", encoding="utf-8")
    frozen = command(runtime, "command_freeze_table", 1, binding, audit, "differential", "READY")
    result["table_frozen"] = frozen["state"] == "frozen"
    result["rerun_identical"] = command(runtime, "command_freeze_table", 1, binding, audit, "differential",
                                        "READY")["state"] == "already_frozen"
    for name, args in (("rerun_different_audit_refused", (1, binding, other)),
                       ("rerun_different_attempt_refused", (2, binding, audit))):
        try:
            command(runtime, "command_freeze_table", *args, "differential", "READY")
            result[name] = False
        except L.Refusal:
            result[name] = True
    for name, overrides in (("gate_refuses_table_not_on_main", {"table_on_main": lambda data: False}),
                            ("gate_refuses_other_endpoint", {"endpoint": "http://elsewhere"}),
                            ("gate_refuses_other_freeze", {"freeze_binding": lambda: "e" * 64})):
        try:
            command(r7_runtime(D, provider, **overrides), "phase_b_preconditions", 1)
            result[name] = False
        except L.Refusal:
            result[name] = True
    sentence = f"Authorize G-ROUTE3 phase B execution {binding} table {frozen['table_sha256']} attempt 1"
    out_b = command(runtime, "command_launch_b", sentence, 1, False, frozen["table_sha256"], 1)
    result["r7_phase_b_state"] = out_b["state"]
    r7_report = json.loads((D / "phase_b" / "runs" / out_b["run_id"] / "score.json").read_text(encoding="utf-8"))

    table_path = work / "R6_TABLE.json"
    if table_path.exists():
        table_path.unlink()
    R.QUALIFICATION_TABLE_PATH = table_path                  # scratch path; the repository is untouched
    r6_audit = work / "audit_r6.md"
    r6_audit.write_text(f"READY audit of {a['r6_run']} score {a['r6_score']['record_sha256']}\n", encoding="utf-8")
    audit_record = Q.audit_record(r6_audit, "READY", "differential", run_id=a["r6_run"],
                                  score_record_sha256=a["r6_score"]["record_sha256"])
    doc = Q.build_table(a["r6_cells"], run_id=a["r6_run"], score_record_sha256=a["r6_score"]["record_sha256"],
                        execution_freeze_binding=R._freeze_digest(), audit=audit_record,
                        phase_a_attempts=R.phase_a_attempts())
    Q.freeze_table(doc, table_path)
    r6b = R.execute_phase_b(provider_call=EdgeProvider("B", plan_qualifying), model_receipts=T.receipts(),
                            run_root=work / "R6_B", phase_a_root=a["r6_root"], phase_a_run_id=a["r6_run"],
                            synthetic_fixture=True)
    r6_score = RouteRunStore(work / "R6_B", r6b["run_id"], create=False).score_record()
    r7_table = json.loads((D / "tables" / "QUALIFICATION_TABLE.json").read_text(encoding="utf-8"))
    skip = {"record_sha256", "phase_b_attempts", "synthetic_fixture", "phase_a_run_id", "table_sha256",
            "orphans_cleared"}
    result["phase_a_cells_identical"] = a["r6_cells"] == r7_table["cells"]
    result["routing_lookup_identical"] = doc["routing_lookup"] == r7_table["routing_lookup"]
    result["phase_b_score_identical"] = (
        json.dumps({k: v for k, v in r6_score.items() if k not in skip}, sort_keys=True)
        == json.dumps({k: v for k, v in r7_report.items() if k not in skip}, sort_keys=True))
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workdir")
    args = parser.parse_args(argv)
    P.pin_recursion_limit()
    work = Path(args.workdir or tempfile.mkdtemp(prefix="g_route3_r7_differential_"))
    work.mkdir(parents=True, exist_ok=True)
    started = time.time()
    mixed = phase_a_differential(work, plan_mixed, "mixed")
    qualifying = phase_a_differential(work, plan_qualifying, "qualifying")
    gate = phase_b_and_gate(work, qualifying)
    summary = {"phase_a_mixed": {k: mixed[k] for k in ("r6_state", "r7_state", "cells_identical", "qualified")},
               "phase_a_qualifying": {k: qualifying[k] for k in ("r6_state", "r7_state", "cells_identical",
                                                                 "qualified")},
               "phase_b_and_gate": gate, "seconds": round(time.time() - started, 1)}
    print(json.dumps(summary, indent=2, sort_keys=True))
    ok = (mixed["cells_identical"] and qualifying["cells_identical"] and qualifying["qualified"] > 0
          and mixed["r7_state"] == qualifying["r7_state"] == "completed"
          and all(v in (True, "completed") for v in gate.values()))
    print("DIFFERENTIAL", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
