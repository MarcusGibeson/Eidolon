"""G-ROUTE4 A′ round-1 fixes (operator decisions 2026-09-29: input ambiguous -> fix input, 6 fixtures).

Same method as build_fixes.py (B′): each fix is derived from the SEALED A′ fixture, gold and ledger record, changes
only its declared paths, and is written to separate files so the adjudicator's run path never reads gold:

    round1_amain/corpus_fixed.json   model-facing fixed fixtures (the only file the run path reads)
    round1_amain/gold_fixed.json     fixed gold, reference outputs and rationales
    round1_amain/ledger_fixed.json   fixed authoring-ledger records
    round1_amain/FIX_RECORD.json     defect, every changed path (from -> to), sealed and fixed digests

    python -B build_fixes_amain.py
"""

import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_fixes import canonical, sha, load, diff, render  # noqa: E402

OUT = HERE / "round1_amain"
DECISIONS_RUN = "g4adj-amain-20260929T180225Z"

# P6: remove the exclusionary 'only'; the source then states a narrower scope without excluding the rest.
P6 = {
    "A4-RSRCH-R2-02": ("S1", "Hayusu's delivery service operates only in the harbour district.",
                       "Hayusu's delivery service operates in the harbour district."),
    "A4-RSRCH-R4-03": ("S1", "Vamodu's sprinklers protect only the ground floor.",
                       "Vamodu's sprinklers protect the ground floor."),
}
# Weak support: S3 and its same-publisher reissue S5 now state that collection happens every Saturday.
SUPPORT = {
    "A4-RSRCH-R2-01": [("S3", "Parcels can be picked up by Foweye's courier at the weekend.",
                        "Every Saturday, Foweye's courier picks up parcels."),
                       ("S5", "Reissued by the same publisher: Parcels can be picked up by Foweye's courier at the weekend.",
                        "Reissued by the same publisher: Every Saturday, Foweye's courier picks up parcels.")],
}
# SY1: the causal statement becomes the only 'finding'; the symptom finding becomes 'symptom'.
SY1 = ["A4-SYNTH-R2-03", "A4-SYNTH-R4-01"]
SY1_ROLES = {"finding": "symptom", "diagnosis": "finding"}
# Extraction: the undefined field 'venue' is renamed 'town'; the gold value 'Dalihi' is unchanged.
RENAME = {"A4-EXTR-R1-03": ("venue", "town")}
DEFECT = {
    "p6": "P6 narrower-scope source worded with the exclusionary 'only' (reads as a contradiction, not a narrower scope)",
    "support": "support paraphrase ('can be picked up ... at the weekend') did not establish collection every Saturday",
    "sy1": "SY1 causal statement under role 'diagnosis'; the frozen rule requires that a finding states the cause",
    "rename": "extraction field 'venue' undefined; several extractions were reasonable ('school fair in Dalihi', 'school fair', 'Dalihi')",
}


def rename_key(d, old, new):
    return {(new if k == old else k): v for k, v in d.items()}


def build():
    fixtures, gold, ledger = load("corpus_a.json", "fixtures"), load("gold_a.json", "items"), load("authoring_ledger.json", "items")
    records, out_f, out_g, out_l = [], [], [], []
    for fid in sorted(list(P6) + list(SUPPORT) + SY1 + list(RENAME)):
        f, g, d = copy.deepcopy(fixtures[fid]), copy.deepcopy(gold[fid]), copy.deepcopy(ledger[fid])
        if fid in P6 or fid in SUPPORT:
            kind = "p6" if fid in P6 else "support"
            edits = [P6[fid]] if fid in P6 else SUPPORT[fid]
            allowed = set()
            for sid, old, new in edits:
                i = int(sid[1:]) - 1
                src, led = f["input"]["sources"][i], d["research_contract"]["sources"][i]
                assert src["source_id"] == led["source_id"] == sid and src["text"] == old == led["text"], (fid, sid)
                src["text"] = led["text"] = new
                allowed |= {f"input.sources[{i}].text", f"research_contract.sources[{i}].text"}
            changes = {"fixture": diff(fixtures[fid], f), "gold": diff(gold[fid], g), "ledger": diff(ledger[fid], d)}
            assert {c["path"] for c in changes["fixture"] + changes["ledger"]} == allowed and not changes["gold"], fid
        elif fid in SY1:
            kind = "sy1"
            causal = next(o["id"] for o in f["input"]["observations"] if o["role"] == "diagnosis")
            for o in f["input"]["observations"]:
                o["role"] = SY1_ROLES.get(o["role"], o["role"])
            g["expected"]["roles"] = {k: SY1_ROLES.get(v, v) for k, v in g["expected"]["roles"].items()}
            for st in g["reference_output"]["statements"]:
                st["role"] = SY1_ROLES.get(st["role"], st["role"])
            d["merged_role"] = [SY1_ROLES.get(r, r) for r in d["merged_role"]]
            changes = {"fixture": diff(fixtures[fid], f), "gold": diff(gold[fid], g), "ledger": diff(ledger[fid], d)}
            for part in changes.values():
                for c in part:
                    assert c["path"].endswith("role") or c["path"].startswith("expected.roles") or \
                        c["path"].startswith("merged_role"), (fid, c["path"])
            assert g["expected"]["conclusion"] == gold[fid]["expected"]["conclusion"]
            assert g["expected"]["required_terms"] == gold[fid]["expected"]["required_terms"]
            roles = [o["role"] for o in f["input"]["observations"]]
            assert roles.count("finding") == 1 and [o["id"] for o in f["input"]["observations"] if o["role"] == "finding"] == [causal]
            assert sorted(__import__("collections").Counter(roles).values()) == \
                sorted(__import__("collections").Counter(o["role"] for o in fixtures[fid]["input"]["observations"]).values())
        else:
            kind = "rename"
            old, new = RENAME[fid]
            f["input"]["schema"] = rename_key(f["input"]["schema"], old, new)
            g["expected"] = rename_key(g["expected"], old, new)
            g["reference_output"] = rename_key(g["reference_output"], old, new)
            changes = {"fixture": [{"path": f"input.schema.{old}", "from": old, "to": new}],
                       "gold": [{"path": f"expected.{old}", "from": old, "to": new},
                                {"path": f"reference_output.{old}", "from": old, "to": new}],
                       "ledger": diff(ledger[fid], d)}
            assert not changes["ledger"] and f"{new} is " not in f["prompt"] and f"{old}" not in f["prompt"]
            assert g["expected"][new] == gold[fid]["expected"][old] == "Dalihi"
            assert list(f["input"]["schema"].values()) == list(fixtures[fid]["input"]["schema"].values())
            ref = copy.deepcopy(fixtures[fid])
            ref["input"]["schema"] = rename_key(ref["input"]["schema"], old, new)
            assert ref == f, "only the schema key may change"
        records.append({"fixture_id": fid, "round": 1, "fix": "input ambiguous -> fix input", "defect": DEFECT[kind],
                        "sealed_sha256": {"fixture": sha(fixtures[fid]), "gold": sha(gold[fid]), "ledger": sha(ledger[fid])},
                        "fixed_sha256": {"fixture": sha(f), "gold": sha(g), "ledger": sha(d)},
                        "changes": changes,
                        "gold_note": {"sy1": "gold roles and reference-statement roles follow the relabelled input roles; "
                                             "the conclusion, required terms, ids and merges are unchanged",
                                      "rename": "the gold key follows the renamed schema key; the value 'Dalihi' is unchanged"}.get(kind)})
        out_f.append(f)
        out_g.append(g)
        out_l.append(d)
    return records, out_f, out_g, out_l


if __name__ == "__main__":
    records, f, g, d = build()
    OUT.mkdir(parents=True, exist_ok=True)
    head = {"schema_version": "g-route4.fixes.v1", "batch": "A′ main", "round": 1, "decisions_run": DECISIONS_RUN,
            "seal_commit": "50e6b46994299ffd71c97aa3f81f30637efaba1c"}
    (OUT / "corpus_fixed.json").write_text(render(dict(head, fixtures=f)), encoding="utf-8", newline="\n")
    (OUT / "gold_fixed.json").write_text(render(dict(head, items=g)), encoding="utf-8", newline="\n")
    (OUT / "ledger_fixed.json").write_text(render(dict(head, items=d)), encoding="utf-8", newline="\n")
    (OUT / "FIX_RECORD.json").write_text(render(dict(head, fixes=records)), encoding="utf-8", newline="\n")
    for r in records:
        print(r["fixture_id"], "|", "; ".join(f"{c['path']}: {c['from']!r} -> {c['to']!r}" for v in r["changes"].values() for c in v))
