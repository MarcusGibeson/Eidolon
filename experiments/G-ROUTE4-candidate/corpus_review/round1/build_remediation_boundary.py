"""Record the round-1 remediation re-adjudication at its operator-decision boundary (frozen step 6 within step 7).

Reads only committed run records (journals re-verified by hash chain): session counts, models, configuration digest,
retries, in-doubt records, the answer and score digests, and the frozen-rule decisions. The fence diagnostic is
recorded as diagnostic only; recorded verdicts are unchanged.

    python -B build_remediation_boundary.py <A′ run id> <B′ run id>
"""

import collections
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ADJ = HERE.parents[1] / "adjudication"
sys.path.insert(0, str(ADJ))
import g4_adjudicate as H  # noqa: E402

sys.path.insert(0, str(H.ROOT / "tools"))
from g_route3_operational import validate_operational  # noqa: E402
from g_route3_semantics import validate_fixture_output  # noqa: E402

FENCE = re.compile(r"^\s*```[A-Za-z0-9_-]*\s*\n(.*?)\n?```\s*$", re.S)


def contact(run):
    H.Journal(run / "journal.jsonl")
    recs = [json.loads(line) for line in (run / "journal.jsonl").read_text(encoding="utf-8").splitlines()]
    res = [r for r in recs if r["type"] == "result"]
    intents = collections.Counter((r["fixture_id"], r["slot"]) for r in recs if r["type"] == "intent")
    start = next(r for r in recs if r["type"] == "run_start")
    return {"sessions": sum(intents.values()), "slots": len(intents),
            "exactly_once_per_slot": all(v == 1 for v in intents.values()),
            "final_messages": sum(r["kind"] == "final_message" for r in res),
            "results_by_kind": dict(collections.Counter(r["kind"] for r in res)),
            "refusals": sum(r.get("stop_reason") == "refusal" for r in res),
            "in_doubt": sum(r["type"] == "in_doubt" for r in recs), "stops": sum(r["type"] == "stop" for r in recs),
            "models": sorted({r.get("model") for r in res}),
            "config_digests": sorted({r["config_sha256"] for r in recs if "config_sha256" in r}),
            "harness_commit": start["harness_commit"], "fixes_bound": start["fixes"],
            "tokens": {"input": sum((r.get("usage") or {}).get("input_tokens", 0) for r in res),
                       "output": sum((r.get("usage") or {}).get("output_tokens", 0) for r in res)},
            "first_utc": recs[0]["utc"], "last_utc": recs[-1]["utc"],
            "journal_lf_sha256": H.lf_sha256(run / "journal.jsonl")}


def files(run):
    return {p.name: H.lf_sha256(p) for p in sorted(run.glob("*.json"))}


def main(ra, rb):
    A, B = ADJ / "runs" / ra, ADJ / "runs" / rb
    dec_a, dec_b = json.loads((A / "decisions.json").read_text(encoding="utf-8")), json.loads((B / "decisions.json").read_text(encoding="utf-8"))
    pending = sorted(f for f, v in {**dec_a, **dec_b}.items() if v["decision"] == "operator")
    fx, gold = H.model_facing_b(ADJ / "fixes/cr1_bmain"), H.gold_path_overlay(ADJ / "fixes/cr1_bmain")
    diag = {}
    for fid in pending:
        rows = []
        for ph in (1, 2):
            p = B / f"answers_phase{ph}.json"
            if not p.exists():
                continue
            for a in json.loads(p.read_text(encoding="utf-8"))["slots"]:
                if a["fixture_id"] != fid:
                    continue
                text = H.binding_text(json.loads((B / "raw" / f"{fid}__s{a['slot']}__i{a['binding_invocation']}.body").read_bytes()))
                assert H.sha256(text) == a["binding_text_sha256"]
                m = FENCE.match(text)
                inner = m.group(1) if m else text
                ok = validate_operational(fx[fid], inner).get("accepted") and \
                    validate_fixture_output(fx[fid], gold[fid], inner).get("hard_gate_pass")
                rows.append({"slot": a["slot"], "fenced": bool(m), "content_passes_frozen_validators_against_fixed_gold": bool(ok)})
        diag[fid] = rows
    out = {
        "schema_version": "g-route4.remediation-boundary.v1", "round": "corpus review round 1 remediation (cr1)",
        "status": "AT OPERATOR-DECISION BOUNDARY" if pending else "COMPLETE",
        "config_sha256": H.AMENDED_CONFIG_SHA256,
        "runs": {ra: {"contact": contact(A), "records_lf_sha256": files(A)},
                 rb: {"contact": contact(B), "records_lf_sha256": files(B)}},
        "decisions_by_frozen_rule": {**dec_a, **dec_b},
        "kept_by_frozen_rule": sorted(f for f, v in {**dec_a, **dec_b}.items() if v["decision"] == "keep"),
        "pending_operator": pending,
        "fence_diagnostic_only": diag,
        "verdicts": "recorded verdicts are unchanged; every malformed_json answer remains a disagreement",
        "if_not_kept": {"B4-SYNTH-R2-15": "each fixture has used its one fix; 'not keep' would mean replacement from the "
                                          "matching B′ reserve, B4-SYNTH-R2-X03 (mergeable_pair yes × obs_band large; no known "
                                          "defect); nothing is replaced without the operator"},
    }
    (HERE / "REMEDIATION_BOUNDARY_R1.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n",
                                                      encoding="utf-8", newline="\n")
    print(json.dumps({"kept": out["kept_by_frozen_rule"], "pending": pending, "diag": diag}, indent=1))
    for r in out["runs"].values():
        c = r["contact"]
        print({k: c[k] for k in ("sessions", "exactly_once_per_slot", "final_messages", "refusals", "in_doubt", "stops",
                                 "models", "config_digests", "tokens")})


if __name__ == "__main__":
    main(*sys.argv[1:])
