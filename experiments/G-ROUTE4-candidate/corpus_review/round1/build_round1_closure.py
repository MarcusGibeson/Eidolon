"""Close external corpus review round 1 (design order of work 3.7) under the operator's closure ruling.

Binds the ruling verbatim (transcript record id and exact-text sha256), extracts the B7 freeze condition from it
verbatim, re-asserts the four review-stage conditions from the committed records, and binds every round-1 record,
successor and erratum by digest. Nothing earlier is modified; RECONCILIATION_R1_FINAL.md (status OPEN at the time)
is superseded by this closure, not edited.

    python -B build_round1_closure.py <session transcript .jsonl>
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAND = HERE.parents[1]
ADJ = CAND / "adjudication"
sys.path.insert(0, str(ADJ))
import g4_adjudicate as H  # noqa: E402

UUID, DIGEST = "d2591e2a-eb78-4e69-a235-04fa870ae5c1", "76c68e636ae280ccf149c3c7e550583221a5ea73de167af7be4af31a31f9afbc"


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def verbatim(transcript):
    for line in Path(transcript).read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            if r.get("uuid") == UUID:
                c = r["message"]["content"]
                assert hashlib.sha256(c.encode("utf-8")).hexdigest() == DIGEST
                return {"transcript_record_uuid": UUID, "utc": r["timestamp"], "text_sha256": DIGEST, "text": c}
    raise SystemExit("ruling message not found")


def main(transcript):
    ruling = verbatim(transcript)
    text = ruling["text"]
    b7 = text[text.index("«") + 1:text.index("»")]
    rem, ind = load(HERE / "REMEDIATION_CLOSURE_R1.json"), load(CAND / "INDEPENDENCE_REPORT_CR1.json")
    aa, ba = load(ADJ / "A_MAIN_CLOSURE_ADDENDUM_CR1.json"), load(ADJ / "B_MAIN_CLOSURE_ADDENDUM_CR1.json")
    fix_check = load(ADJ / "fixes/cr1_bmain/FIX_CHECK_REPORT.json")
    assert rem["status"].startswith("CLOSED") and not rem["replaced"]
    assert ind["valid"] and ind["bounds_met"] and ind["reproduction_of_frozen_values"]["all_reproduced"]
    assert fix_check["passed"] and not fix_check["problems"]
    assert not aa["latent_defects"]["in_the_final_main_corpus_unfixed"] and not ba["latent_defects"]["in_the_final_main_corpus_unfixed"]
    records = ["outputs/REVIEWER_A_REPORT.md", "outputs/REVIEWER_B_REPORT.md", "outputs/REVIEW_OUTPUTS_RECORD.json",
               "outputs/REVIEWER_A_RESUMPTION_RECORD.json", "REVIEW_MANIFEST.json", "REVIEWER_A_BRIEF.md", "REVIEWER_B_BRIEF.md",
               "OPERATOR_RULINGS_R1.json", "BATCH_START_PROVENANCE.json", "RECONCILIATION_R1.md", "OPERATOR_DISPOSITIONS_R1.json",
               "REMEDIATION_BOUNDARY_R1.json", "REMEDIATION_CLOSURE_R1.json", "RECONCILIATION_R1_FINAL.md"]
    successors = ["INDEPENDENCE_REPORT_CR1.json", "CONTAMINATION_ANALYSIS_CR1.md", "adjudication/A_MAIN_CLOSURE_ADDENDUM_CR1.json",
                  "adjudication/B_MAIN_CLOSURE_ADDENDUM_CR1.json", "adjudication/fixes/cr1_bmain/FIX_CHECK_REPORT.json",
                  "adjudication/errata/B_MAIN_CLOSURE_ERRATUM_1.json", "adjudication/errata/B_MAIN_CLOSURE_ERRATUM_2.json",
                  "adjudication/errata/STEP7_RULING_ANNOTATION.md", "adjudication/O2_AMENDMENT_2026-09-29.md"]
    unchanged = ["INDEPENDENCE_REPORT.json", "CONTAMINATION_ANALYSIS.md", "adjudication/A_MAIN_CLOSURE.json",
                 "adjudication/B_MAIN_CLOSURE.json"]
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=H.ROOT, capture_output=True, text=True, check=True).stdout.strip()
    closure = {
        "schema_version": "g-route4.corpus-review-closure.v1", "round": 1,
        "design_step": "order of work 3.7: the external corpus review",
        "status": "CLOSED",
        "closed_on": ruling["utc"][:10],
        "closed_at_parent_commit": head,
        "operator_ruling_verbatim": ruling,
        "review_stage_conditions": {
            "repaired fixtures completed re-adjudication": rem["status"],
            "every MUST-FIX from Reviewers A and B resolved": "A1, A2, A3 (fixed and re-adjudicated, all kept); B1 (step-7 "
                                                              "ruling and annotation); B2 (erratum 1)",
            "disclosures and errata recorded and bound": "A4-PLAN-R3-04, A4, A5; B3 (O2 disclosure), B9; B10 provenance; "
                                                         "errata 1 and 2 to B_MAIN_CLOSURE.json",
            "the 26-fix corpus passes the frozen checks": f"{fix_check['fixtures_checked']} fixtures, "
                                                          f"{sum(len(v) for v in fix_check['fixes_applied'].values())} fixes, "
                                                          f"{len(fix_check['problems'])} problems",
            "pinned independence tool reproduces the frozen values":
                f"{ind['reproduction_of_frozen_values']['compared']} values reproduced; bounds met; {len(ind['problems'])} problems",
            "historical and sealed artifacts unchanged": "except the authorized O2 disclosure append (B3)",
        },
        "forked_module_recheck": {
            "status": "NOT a corpus-review closure prerequisite (operator ruling): g_route4_independence does not exist and, "
                      "under the frozen design, is created in the implementation stage",
            "pinned_tool_result_role": "evidence that the reviewed 26-fix corpus currently satisfies the frozen independence "
                                       "requirements; not a substitute for the later forked-module qualification",
        },
        "freeze_conditions_carried_forward": {
            "B7": {"condition_verbatim": b7, "status": "OPEN, mandatory; blocks the freeze if it fails; not waivable by the "
                                                       "pinned-tool result"},
            "B8": {"condition": "bind the B′ fix-round per-cell counts in the final freeze records",
                   "status": "counts bound in adjudication/B_MAIN_CLOSURE_ADDENDUM_CR1.json; to be bound in the freeze records"},
        },
        "outcome": {"blocking": 0, "must_fix": {"reviewer_A": 3, "reviewer_B": 2, "resolved": 5},
                    "fixtures_fixed_in_review": sorted(rem["outcome_per_fixture"]), "replaced": 0, "reserves_drawn": 0},
        "final_corpus": {"fixes": 26, "a_main": aa["final_corpus"]["a_main"]["model_facing_sha256"],
                         "a_main_gold": aa["final_corpus"]["a_main"]["gold_sha256"],
                         "b_main": ba["final_corpus"]["b_main"]["model_facing_sha256"],
                         "b_main_gold": ba["final_corpus"]["b_main"]["gold_sha256"]},
        "records_lf_sha256": {f"corpus_review/round1/{p}": H.lf_sha256(HERE / p) for p in records},
        "successors_and_errata_lf_sha256": {p: H.lf_sha256(CAND / p) for p in successors},
        "historical_unchanged_lf_sha256": {p: H.lf_sha256(CAND / p) for p in unchanged},
        "integrity_boundaries": ["no sealed or historical artifact modified (except the authorized O2 disclosure append)",
                                 "main, g-route4/seal and the tag g-route4-seal not moved",
                                 "no completed adjudication reinterpreted", "no freeze criterion weakened"],
        "next_stage": "implementation under frozen design step 4; not begun; requires separate operator authorization",
    }
    (HERE / "CORPUS_REVIEW_R1_CLOSURE.json").write_text(json.dumps(closure, indent=1, ensure_ascii=False) + "\n",
                                                       encoding="utf-8", newline="\n")
    print(closure["status"], "| B7:", b7[:80], "…")


if __name__ == "__main__":
    main(*sys.argv[1:])
