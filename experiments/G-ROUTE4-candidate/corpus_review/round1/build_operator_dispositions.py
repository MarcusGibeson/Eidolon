"""Record the operator's round-1 dispositions of Reviewer A's findings (after reconciliation), before any remediation
adjudicator session. The operator's message is bound verbatim from the session transcript by record id and exact-text
sha256; each disposition is restated against its finding, and the review-driven fixes are bound by their records.

    python -B build_operator_dispositions.py <session transcript .jsonl>
"""

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ADJ = HERE.parents[1] / "adjudication"
sys.path.insert(0, str(ADJ))
import g4_adjudicate as H  # noqa: E402

UUID, DIGEST = "295e4a23-ca3c-4565-a1e6-52ad5618f3a6", "9f370c658c25264c01cd10c9ff9090ec8d8d8058dc85c26673042a2bf7d2616c"


def verbatim(transcript):
    for line in Path(transcript).read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            if r.get("uuid") == UUID:
                c = r["message"]["content"]
                assert hashlib.sha256(c.encode("utf-8")).hexdigest() == DIGEST
                return {"transcript_record_uuid": UUID, "utc": r["timestamp"], "text_sha256": DIGEST, "text": c}
    raise SystemExit("dispositions message not found")


def fixes(sub):
    rec = json.loads((ADJ / "fixes" / sub / "FIX_RECORD.json").read_text(encoding="utf-8"))["fixes"]
    return {"dir": f"adjudication/fixes/{sub}", "fix_record_lf_sha256": H.lf_sha256(ADJ / "fixes" / sub / "FIX_RECORD.json"),
            "corpus_fixed_lf_sha256": H.lf_sha256(ADJ / "fixes" / sub / "corpus_fixed.json"),
            "fixtures": {r["fixture_id"]: {"finding": r["finding"], "sealed_sha256": r["sealed_sha256"],
                                           "fixed_sha256": r["fixed_sha256"]} for r in rec}}


def main(transcript):
    out = {
        "schema_version": "g-route4.corpus-review-dispositions.v1", "round": 1, "decided_by": "operator (Marcus Gibeson)",
        "date": "2026-09-29 (message timestamp 2026-09-30T00:09Z)",
        "reviewer_A_report": {"file": "corpus_review/round1/outputs/REVIEWER_A_REPORT.md",
                              "sha256_exact_bytes": "8219822cb9104b106281d22033f7c34335fa0bce88e17fe2bb527c662535b5f5"},
        "reconciliation": {"file": "corpus_review/round1/RECONCILIATION_R1.md",
                           "lf_sha256": H.lf_sha256(HERE / "RECONCILIATION_R1.md")},
        "operator_message_verbatim": verbatim(transcript),
        "dispositions": {
            "A1": {"class": "MUST-FIX", "disposition": "FIX (no replacement)",
                   "fixtures": ["A4-SYNTH-R1-01", "B4-SYNTH-R1-02", "B4-SYNTH-R2-15", "B4-SYNTH-R3-08"],
                   "procedure": "the recorded SY1 role relabel; A′: three adjudicators (kept only if all three agree, "
                                "otherwise the operator); B′: the frozen B′ procedure"},
            "A2": {"class": "MUST-FIX", "disposition": "FIX", "fixtures": ["B4-CONV-R1-08"],
                   "procedure": "frozen B′ procedure; reserve B4-CONV-R1-X08 only if the repaired fixture fails the frozen "
                                "remediation procedure"},
            "A3": {"class": "MUST-FIX", "disposition": "FIX", "fixtures": ["B4-CONV-R2-28"],
                   "procedure": "frozen B′ procedure; reserve B4-CONV-R2-X04 only if the repaired fixture fails the frozen "
                                "remediation procedure",
                   "wording_note": "the operator preferred stating the end date explicitly unless the frozen fixture "
                                   "structure requires otherwise. It does: the CV2 depth-1 construct binds the start date "
                                   "and the duration as facts and computes start + days against the deadline (the checker "
                                   "requires exactly those facts); a stated end date would pre-evaluate that computation. "
                                   "The fix therefore defines the end relative to the start ('finishes ... N days later'), "
                                   "which fixes the end date by addition, without a counting convention."},
            "A4-PLAN-R3-04": {"source": "Reviewer B B5 / Reviewer A A7", "disposition": "KEEP WITH DISCLOSURE",
                              "disclosure": "The three adjudicator refusals are retained as a disclosed limitation of its "
                                            "historical adjudication. Reviewer A independently derived the reference "
                                            "answer and matched gold, and neither reviewer identified a derivability "
                                            "defect. The refusals alone do not justify a fixture or gold change.",
                              "unchanged": "fixture, gold and historical adjudication"},
            "A4": {"class": "NOTE", "disposition": "DISCLOSURE (documented coverage limitation)",
                   "disclosure": "The A′ corpus does not exercise research P4 in the case where reposts are the only "
                                 "support, while B′ does (B4-RSRCH-R1-12, B4-RSRCH-R2-12, B4-RSRCH-R3-12). No fixture is "
                                 "added or modified to eliminate it."},
            "A5": {"class": "NOTE", "disposition": "DISCLOSURE (corpus-structure information for interpreting results)",
                   "disclosure": "Synthesis families SY4, SY5 and SY6 have a constant conclusion within each family "
                                 "(decision_reserved, constraint_breached and behavior_by_design respectively). This is "
                                 "not a defect and does not authorize a corpus change."},
            "A10": {"class": "NOTE", "disposition": "ERRATUM 2",
                    "record": "adjudication/errata/B_MAIN_CLOSURE_ERRATUM_2.json",
                    "erratum_lf_sha256": H.lf_sha256(ADJ / "errata" / "B_MAIN_CLOSURE_ERRATUM_2.json")},
            "A6, A8, A9, A11": {"class": "NOTE", "disposition": "no action"},
        },
        "review_driven_fixes": {"cr1_amain": fixes("cr1_amain"), "cr1_bmain": fixes("cr1_bmain"),
                                "fix_check": {"file": "adjudication/fixes/cr1_bmain/FIX_CHECK_REPORT.json",
                                              "lf_sha256": H.lf_sha256(ADJ / "fixes/cr1_bmain/FIX_CHECK_REPORT.json")}},
        "authorization": "remediation adjudicator sessions for A1-A3 only, under the existing frozen O2 procedure and "
                         "amended configuration 7691126e…; recorded as remediation sessions, bound to the committed "
                         "pre-adjudication fixed fixtures (the run journal binds the fix record digests)",
        "round_status": "OPEN until the repaired fixtures complete re-adjudication, every MUST-FIX is resolved, the "
                        "disclosures and errata are recorded, and the final independence re-check reproduces the "
                        "required values",
    }
    (HERE / "OPERATOR_DISPOSITIONS_R1.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n",
                                                       encoding="utf-8", newline="\n")
    print("dispositions recorded:", ", ".join(out["dispositions"]))


if __name__ == "__main__":
    main(*sys.argv[1:])
