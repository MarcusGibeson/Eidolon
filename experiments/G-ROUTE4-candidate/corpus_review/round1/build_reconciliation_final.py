"""External corpus review round 1: final reconciliation (successor to RECONCILIATION_R1.md, which is not modified).

Checks each closing condition set by the operator mechanically against the committed records and writes the status it
finds. The operator's round-1 closing conditions (2026-09-30): the repaired fixtures completed re-adjudication; every
MUST-FIX from both reviewers is resolved; the new disclosures and errata are recorded; and the final independence
re-check, **using the forked module**, reproduces the frozen values.

    python -B build_reconciliation_final.py
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAND = HERE.parents[1]
ADJ = CAND / "adjudication"
sys.path.insert(0, str(ADJ))
import g4_adjudicate as H  # noqa: E402


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def main():
    rem = load(HERE / "REMEDIATION_CLOSURE_R1.json")
    rul = load(HERE / "OPERATOR_RULINGS_R1.json")["dispositions"]
    dsp = load(HERE / "OPERATOR_DISPOSITIONS_R1.json")["dispositions"]
    ind = load(CAND / "INDEPENDENCE_REPORT_CR1.json")
    aa, ba = load(ADJ / "A_MAIN_CLOSURE_ADDENDUM_CR1.json"), load(ADJ / "B_MAIN_CLOSURE_ADDENDUM_CR1.json")
    forked = sorted(p.name for p in (H.ROOT / "tools").glob("g_route4_*"))
    must_fix = {
        "B1": ("RESOLVED", "operator step-7 ruling; historical wording annotated (adjudication/errata/STEP7_RULING_ANNOTATION.md)"),
        "B2": ("RESOLVED", "erratum 1 bound to the unchanged B_MAIN_CLOSURE.json"),
        "A1": ("RESOLVED", "4 fixtures fixed (cr1) and re-adjudicated; all kept"),
        "A2": ("RESOLVED", "B4-CONV-R1-08 fixed (cr1) and re-adjudicated; kept"),
        "A3": ("RESOLVED", "B4-CONV-R2-28 fixed (cr1) and re-adjudicated; kept"),
    }
    assert rul["B1"]["status"].startswith("RESOLVED") and rul["B2"]["status"].startswith("RESOLVED")
    assert rem["status"].startswith("CLOSED") and not rem["replaced"]
    assert sorted(sum(rem["findings_resolved"].values(), [])) == sorted(rem["outcome_per_fixture"])
    conditions = {
        "repaired fixtures completed re-adjudication": (True, rem["status"]),
        "every MUST-FIX from both reviewers resolved": (True, f"{len(must_fix)} MUST-FIX (A1-A3, B1, B2): all resolved"),
        "disclosures and errata recorded": (all(k in dsp for k in ("A4-PLAN-R3-04", "A4", "A5", "A10"))
                                            and (ADJ / "errata/B_MAIN_CLOSURE_ERRATUM_1.json").exists()
                                            and (ADJ / "errata/B_MAIN_CLOSURE_ERRATUM_2.json").exists(),
                                            "A4-PLAN-R3-04, A4, A5 disclosures; errata 1 and 2; B3 O2 disclosure; B10 provenance"),
        "independence re-check (pinned authoring-stage tool) reproduces the frozen values":
            (ind["valid"] and ind["reproduction_of_frozen_values"]["all_reproduced"] and ind["bounds_met"],
             f"{ind['reproduction_of_frozen_values']['compared']} class-level values reproduced; bounds met; 0 problems"),
        "final independence re-check using the forked module reproduces the frozen values":
            (False, "NOT RUN: the forked module g_route4_independence does not exist "
                    f"(tools/g_route4_*: {forked or 'none'}); it is written in design step 4 (implementation), which is "
                    "not authorized; nothing was substituted for it"),
    }
    closable = all(ok for ok, _ in conditions.values())
    L = []
    w = L.append
    w("# G-ROUTE4 external corpus review, round 1: final reconciliation")
    w("")
    w(f"**Status: {'CLOSED' if closable else 'OPEN at an operator decision point'}.** Successor to `RECONCILIATION_R1.md` "
      "(not modified).")
    w("")
    w("## Closing conditions")
    w("")
    w("| Condition | Met | Evidence |")
    w("|---|---|---|")
    for k, (ok, ev) in conditions.items():
        w(f"| {k} | {'yes' if ok else '**no**'} | {ev} |")
    w("")
    w("## MUST-FIX findings (both reviewers)")
    w("")
    w("| Finding | Reviewer | Status | Resolution |")
    w("|---|---|---|---|")
    for k, (st, how) in must_fix.items():
        w(f"| {k} | {'A' if k.startswith('A') else 'B'} | {st} | {how} |")
    w("")
    w("BLOCKING findings: 0 from either reviewer.")
    w("")
    w("## Remediation outcome")
    w("")
    for fid, o in rem["outcome_per_fixture"].items():
        w(f"- {fid}: {o}")
    w("")
    w("## Notes and conditions")
    w("")
    w("- **Recorded disclosures:** A4-PLAN-R3-04 (kept with disclosure), A4 (research P4 coverage), A5 (synthesis constant "
      "conclusions), B3 (O2 reclassification), B9 (gold changes in 9 fixes).")
    w("- **Errata to `B_MAIN_CLOSURE.json`:** 1 (disagreement causes) and 2 (15 reserves).")
    w("- **Freeze conditions:** B7 (the forked-module re-check reproduces the values) and B8 (B′ fix-round per-cell "
      "counts, now bound in `adjudication/B_MAIN_CLOSURE_ADDENDUM_CR1.json`).")
    w("- **No action:** A6, A8, A9, A11, B4, B6.")
    w("")
    w("## Successor records (the closed records are unchanged)")
    w("")
    for p in ("INDEPENDENCE_REPORT_CR1.json", "CONTAMINATION_ANALYSIS_CR1.md", "adjudication/A_MAIN_CLOSURE_ADDENDUM_CR1.json",
              "adjudication/B_MAIN_CLOSURE_ADDENDUM_CR1.json", "adjudication/fixes/cr1_bmain/FIX_CHECK_REPORT.json",
              "corpus_review/round1/REMEDIATION_CLOSURE_R1.json"):
        w(f"- `{p}`: sha256 `{H.lf_sha256(CAND / p)}`")
    w("")
    w(f"Final corpus (26 fixes): A′ `{aa['final_corpus']['a_main']['model_facing_sha256']}` / gold "
      f"`{aa['final_corpus']['a_main']['gold_sha256']}`; B′ `{ba['final_corpus']['b_main']['model_facing_sha256']}` / gold "
      f"`{ba['final_corpus']['b_main']['gold_sha256']}`.")
    w("")
    if not closable:
        w("## Open point")
        w("")
        w("The operator made the forked-module re-check a condition of closing round 1. That module is produced by design "
          "step 4 (implementation), which follows the external corpus review in the frozen order of work and is not "
          "authorized, so the condition cannot be met at this stage. The same re-check is already a freeze condition (B7). "
          "The operator decides how round 1 proceeds; no criterion has been weakened or reinterpreted here.")
        w("")
    (HERE / "RECONCILIATION_R1_FINAL.md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print("closable:", closable)
    for k, (ok, ev) in conditions.items():
        print(" ", "OK " if ok else "NO ", k)


if __name__ == "__main__":
    main()
