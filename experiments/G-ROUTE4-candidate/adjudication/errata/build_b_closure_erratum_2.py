"""Erratum 2 to the closed B_MAIN_CLOSURE.json (operator disposition on corpus-review note A10, 2026-09-29).

B_MAIN_CLOSURE.json is not edited. Its `residual_limitations` refers to "14 reserves" with known latent defects; the
A′ addendum later identified one more (B4-RSRCH-R2-X04). The count is derived mechanically here: every reserve id
(`…-X…`) named in the defect tables of the two committed latent-defect reports, each checked to exist in the sealed
reserve corpora, and cross-checked against the list bound in A_MAIN_CLOSURE.json.

    python -B build_b_closure_erratum_2.py    # writes B_MAIN_CLOSURE_ERRATUM_2.json next to this script
"""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ADJ = HERE.parent
sys.path.insert(0, str(ADJ))
import g4_adjudicate as H  # noqa: E402

RESERVE_ID = re.compile(r"\b[AB]4-[A-Z]+-R\d-X\d\d\b")
REPORTS = ("fixes/LATENT_DEFECTS.md", "fixes/round1_amain/LATENT_DEFECTS_ADDENDUM.md")


def table_ids(path):
    """Reserve ids in the report's markdown table rows (the defect tables), not in its prose."""
    ids = set()
    for line in (ADJ / path).read_text(encoding="utf-8").splitlines():
        if line.startswith("|"):
            ids |= set(RESERVE_ID.findall(line))
    return ids


def main():
    closure_path = ADJ / "B_MAIN_CLOSURE.json"
    closure = json.loads(closure_path.read_text(encoding="utf-8"))
    stated = next(x for x in closure["residual_limitations"] if "14 reserves" in x)
    per_report = {p: sorted(table_ids(p)) for p in REPORTS}
    reserves = sorted(set().union(*per_report.values()))
    sealed = {f["fixture_id"] for n in ("reserve_corpus_a.json", "reserve_corpus_b.json")
              for f in json.loads((H.SEALED / n).read_text(encoding="utf-8"))["fixtures"]}
    assert set(reserves) <= sealed
    a_closure = json.loads((ADJ / "A_MAIN_CLOSURE.json").read_text(encoding="utf-8"))
    bound = sorted({i for ids in a_closure["latent_defects"]["in_unused_reserves_unfixed"].values() for i in ids})
    assert reserves == bound, (reserves, bound)
    erratum = {
        "schema_version": "g-route4.erratum.v1", "erratum": 2,
        "corrects": {"file": "adjudication/B_MAIN_CLOSURE.json", "lf_sha256": H.lf_sha256(closure_path),
                     "commit": "f07b1a2fa211ec2c4109117e2b5f1b5c742df7e2", "field": "residual_limitations",
                     "stated_text": stated, "unchanged": "the closed file itself is not edited"},
        "authority": "operator disposition on external corpus review round 1 note A10 (Reviewer A), 2026-09-29: issue a "
                     "second erratum; do not edit the closed artifact",
        "correction": {"as_stated": "14 reserves", "correct": f"{len(reserves)} reserves"},
        "derivation": {"reserve_ids_per_report": per_report, "reserves": reserves, "count": len(reserves),
                       "all_in_sealed_reserve_corpora": True,
                       "equals_A_MAIN_CLOSURE_latent_defects_in_unused_reserves_unfixed": True},
        "note": "the 15th reserve (B4-RSRCH-R2-X04, weak weekend paraphrase) was identified after the B′ closure, in "
                "fixes/round1_amain/LATENT_DEFECTS_ADDENDUM.md; the other counts in the stated sentence describe the "
                "state at the B′ closure",
        "bind_in": "the final external-review closure and freeze records",
    }
    assert erratum["correction"]["correct"] == "15 reserves"
    (HERE / "B_MAIN_CLOSURE_ERRATUM_2.json").write_text(json.dumps(erratum, indent=1, ensure_ascii=False) + "\n",
                                                       encoding="utf-8", newline="\n")
    print(erratum["correction"], {k: len(v) for k, v in per_report.items()})


if __name__ == "__main__":
    main()
