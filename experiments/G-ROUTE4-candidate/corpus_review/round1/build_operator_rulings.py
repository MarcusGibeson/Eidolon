"""Record the operator's rulings on external corpus review round 1 (Reviewer B's findings; Reviewer A's resumption).

The operator's messages are bound verbatim from the session transcript by record id and exact-text sha256 (the step
3.7 authorization, and the rulings); the per-finding dispositions below restate them against each finding id.

    python -B build_operator_rulings.py <session transcript .jsonl>
"""

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ADJ = HERE.parents[1] / "adjudication"
sys.path.insert(0, str(ADJ))
import g4_adjudicate as H  # noqa: E402

MESSAGES = {"step_3_7_authorization": ("8f796fd1-2f4a-4e66-a002-79a7f606a2a8",
                                       "999f25bfb05de9768bfcb7ffbfa923303c4596751adc147eddfcd19552dd1702"),
            "rulings": ("85866ca7-a752-4cfc-8bfe-ba281d11dde6",
                        "e4b86cfa96ee037308d85ebcbac93d24de8063e26631002d6fcba4944081cc9f")}


def verbatim(transcript):
    found = {}
    for line in Path(transcript).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        for key, (uuid, digest) in MESSAGES.items():
            if r.get("uuid") == uuid:
                c = r["message"]["content"]
                if isinstance(c, list):
                    c = "\n".join(x.get("text", "") for x in c if x.get("type") == "text")
                assert hashlib.sha256(c.encode("utf-8")).hexdigest() == digest, key
                found[key] = {"transcript_record_uuid": uuid, "utc": r["timestamp"], "text_sha256": digest, "text": c}
    assert set(found) == set(MESSAGES)
    return found


def main(transcript):
    erratum = ADJ / "errata" / "B_MAIN_CLOSURE_ERRATUM_1.json"
    out = {
        "schema_version": "g-route4.corpus-review-rulings.v1", "round": 1, "decided_by": "operator (Marcus Gibeson)",
        "date": "2026-09-29",
        "reviewer_B_report": {"file": "corpus_review/round1/outputs/REVIEWER_B_REPORT.md",
                              "sha256_exact_bytes": "0eba8701a8cec21df82f846c7faacbba92a78f405abbff88d0b29cb2fe9f3320"},
        "operator_messages_verbatim": verbatim(transcript),
        "dispositions": {
            "reviewer_A": "Decision 1 (a): resume the same session; it is given only three instructions (continue reviewing "
                          "97afe8a; return the completed report as the final hand-back message; do not inspect "
                          "corpus_review/round1/outputs/ or any newly created Reviewer B material). The brief is otherwise "
                          "unchanged; its completed derivation is not re-run or re-seeded.",
            "B1": {"class": "MUST-FIX", "status": "RESOLVED by operator ruling",
                   "ruling": "step 7 does not require automatic replacement merely because a fixed fixture's re-adjudication "
                             "does not literally end in 'keep'; the controlling question is whether re-adjudication establishes "
                             "an unresolved defect in the fixture/gold pair. Applied to the 4 B′ and 5 A′ retained fixtures; no "
                             "re-adjudication.",
                   "record": "adjudication/errata/STEP7_RULING_ANNOTATION.md (annotates the historical 'not keep' / 'did not "
                             "end in keep' wording; the history is not rewritten; the timing difference is disclosed)"},
            "B2": {"class": "MUST-FIX", "status": "RESOLVED by erratum",
                   "record": "adjudication/errata/B_MAIN_CLOSURE_ERRATUM_1.json", "erratum_lf_sha256": H.lf_sha256(erratum),
                   "corrected": json.loads(erratum.read_text(encoding="utf-8"))["corrected"],
                   "closed_artifact_unchanged": {"file": "adjudication/B_MAIN_CLOSURE.json",
                                                 "lf_sha256": H.lf_sha256(ADJ / "B_MAIN_CLOSURE.json")},
                   "bind_in": "the final external-review closure and freeze records"},
            "B3": {"class": "NOTE", "status": "DISCLOSED now", "record": "adjudication/O2_AMENDMENT_2026-09-29.md (appended "
                   "historical disclosure); the historical result is not reinterpreted or re-run"},
            "B4": {"class": "NOTE", "status": "no action (reviewer proposed none)"},
            "B5": {"class": "NOTE", "status": "CARRIED FORWARD, no disposition yet",
                   "fixture": "A4-PLAN-R3-04",
                   "ruling": "not modified (fixture, gold, historical adjudication); to be considered under design step 10 in "
                             "the round-1 reconciliation after Reviewer A reports; the three adjudicator refusals are "
                             "insufficient by themselves to authorize a post hoc gold change"},
            "B6": {"class": "NOTE", "status": "no action (reviewer proposed none)"},
            "B7": {"class": "NOTE", "status": "FREEZE CONDITION",
                   "condition": "the final independence re-check using the forked module must reproduce the sealed values "
                                "(INDEPENDENCE_REPORT.json)"},
            "B8": {"class": "NOTE", "status": "FREEZE CONDITION",
                   "condition": "bind the B′ fix-round per-cell counts in the final freeze records"},
            "B9": {"class": "NOTE", "status": "preserved as an existing disclosure"},
            "B10": {"class": "NOTE", "status": "PROVENANCE BOUND",
                    "record": "corpus_review/round1/BATCH_START_PROVENANCE.json (the original in-chat operator messages of the "
                              "adjudication period, verbatim, bound per transcript record; no synthetic replacement)",
                    "record_lf_sha256": H.lf_sha256(HERE / "BATCH_START_PROVENANCE.json")},
        },
        "round_status": "OPEN: round 1 does not close until Reviewer A's report is preserved and the two reports are "
                        "reconciled, including any disagreements and all MUST-FIX findings",
    }
    (HERE / "OPERATOR_RULINGS_R1.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n",
                                                  encoding="utf-8", newline="\n")
    print("rulings recorded:", ", ".join(out["dispositions"]))


if __name__ == "__main__":
    main(*sys.argv[1:])
