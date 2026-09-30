"""Close the round-1 remediation re-adjudication: the operator's decision on B4-SYNTH-R2-15, and the closure record.

Writes the operator decision into the B′ remediation run (the same schema as the earlier fix rounds) and
REMEDIATION_CLOSURE_R1.json, which binds the fixes, both runs, every decision and the boundary report. The operator's
message is bound verbatim by transcript record id and exact-text sha256. Recorded verdicts are unchanged.

    python -B build_remediation_closure.py <A′ run id> <B′ run id> <session transcript .jsonl>
"""

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ADJ = HERE.parents[1] / "adjudication"
sys.path.insert(0, str(ADJ))
import g4_adjudicate as H  # noqa: E402

UUID, DIGEST = "25710cad-f2fc-4f16-9025-cf317ad6a307", "5747a9b63bcf476402d52d83f23bbddec8bf67d2afac29c459a065de590900cb"


def verbatim(transcript):
    for line in Path(transcript).read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            if r.get("uuid") == UUID:
                c = r["message"]["content"]
                assert hashlib.sha256(c.encode("utf-8")).hexdigest() == DIGEST
                return {"transcript_record_uuid": UUID, "utc": r["timestamp"], "text_sha256": DIGEST, "text": c}
    raise SystemExit("operator message not found")


def main(ra, rb, transcript):
    A, B = ADJ / "runs" / ra, ADJ / "runs" / rb
    boundary = json.loads((HERE / "REMEDIATION_BOUNDARY_R1.json").read_text(encoding="utf-8"))
    dec_b = json.loads((B / "decisions.json").read_text(encoding="utf-8"))
    assert boundary["pending_operator"] == ["B4-SYNTH-R2-15"]
    diag = boundary["fence_diagnostic_only"]["B4-SYNTH-R2-15"]
    assert all(r["content_passes_frozen_validators_against_fixed_gold"] for r in diag)
    assert [r["slot"] for r in diag if r["fenced"]] == [1, 2]
    v = dec_b["B4-SYNTH-R2-15"]
    op = {
        "schema_version": "g-route4.operator-decisions.v1", "run_id": rb, "round": "cr1 (corpus review round 1 remediation)",
        "decided_by": "operator (Marcus Gibeson)", "date": "2026-09-30",
        "rule": "frozen step 6 within the step-7 re-adjudication of a fixed fixture, read under the operator's B1 step-7 "
                "ruling (adjudication/errata/STEP7_RULING_ANNOTATION.md)",
        "operator_message_verbatim": verbatim(transcript),
        "decisions": [{
            "fixture_id": "B4-SYNTH-R2-15", "verdicts": [v["a1"], v["a2"], v["a3"]],
            "outcome": "gold right -> keep",
            "reason": "The fixture completed its authorized fix and re-adjudication. Two adjudicator outputs disagreed only "
                      "because they were code-fenced (malformed for the frozen output-shape rule); after stripping the "
                      "fences both pass the frozen validators against the fixed gold conclusion 'cause_established' "
                      "(diagnostic only). No substantive fixture defect, gold defect or semantic disagreement is "
                      "established.",
            "status_note": "did not reach automatic keep under the historical B′ decision rule; retained by explicit "
                           "operator disposition under the B1 ruling, because the remaining disagreements are fenced "
                           "(non-admissible) answers and the repaired fixture and gold remain defensible",
            "replaced": False, "not_used_reserve": "B4-SYNTH-R2-X03"}],
        "verdicts_unchanged": "the recorded verdicts are unchanged; both fenced answers remain disagreements",
        "full_cell_consequence": "not applicable: B4-SYNTH-R2-15 is not an audit-sample fixture",
    }
    (B / "OPERATOR_DECISIONS.json").write_text(json.dumps(op, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

    dec_a = json.loads((A / "decisions.json").read_text(encoding="utf-8"))
    final = {f: ("keep (frozen rule)" if d["decision"] == "keep" else "gold right -> keep (operator, B1 ruling)")
             for f, d in {**dec_a, **dec_b}.items()}
    assert len(final) == 6
    records = {n: {"lf_sha256": H.lf_sha256(p)} for n, p in {
        f"runs/{ra}/{x}": A / x for x in ("journal.jsonl", "answers_phase1.json", "scores_phase1.json", "decisions.json")}.items()}
    records.update({n: {"lf_sha256": H.lf_sha256(p)} for n, p in {
        f"runs/{rb}/{x}": B / x for x in ("journal.jsonl", "answers_phase1.json", "scores_phase1.json", "answers_phase2.json",
                                          "scores_phase2.json", "decisions.json", "OPERATOR_DECISIONS.json")}.items()})
    for sub in ("cr1_amain", "cr1_bmain"):
        for x in ("FIX_RECORD.json", "corpus_fixed.json", "gold_fixed.json", "ledger_fixed.json"):
            records[f"fixes/{sub}/{x}"] = {"lf_sha256": H.lf_sha256(ADJ / "fixes" / sub / x)}
    records["fixes/cr1_bmain/FIX_CHECK_REPORT.json"] = {"lf_sha256": H.lf_sha256(ADJ / "fixes/cr1_bmain/FIX_CHECK_REPORT.json")}
    closure = {
        "schema_version": "g-route4.remediation-closure.v1", "round": "corpus review round 1 remediation (cr1)",
        "status": "CLOSED: 6 of 6 kept, 0 replaced",
        "findings_resolved": {"A1": ["A4-SYNTH-R1-01", "B4-SYNTH-R1-02", "B4-SYNTH-R2-15", "B4-SYNTH-R3-08"],
                              "A2": ["B4-CONV-R1-08"], "A3": ["B4-CONV-R2-28"]},
        "outcome_per_fixture": final,
        "automatic_keep": sorted(f for f, o in final.items() if o.startswith("keep")),
        "operator_keep": sorted(f for f, o in final.items() if not o.startswith("keep")),
        "replaced": [], "reserves_drawn": [],
        "contact": {r: boundary["runs"][r]["contact"] for r in (ra, rb)},
        "boundary_report_lf_sha256": H.lf_sha256(HERE / "REMEDIATION_BOUNDARY_R1.json"),
        "records": records,
    }
    (HERE / "REMEDIATION_CLOSURE_R1.json").write_text(json.dumps(closure, indent=1, ensure_ascii=False) + "\n",
                                                     encoding="utf-8", newline="\n")
    print(closure["status"], "| automatic", closure["automatic_keep"], "| operator", closure["operator_keep"])


if __name__ == "__main__":
    main(*sys.argv[1:])
