"""G-ROUTE4 review-driven fixes (design step 10) from external corpus review round 1, findings A1, A2 and A3.

Operator dispositions 2026-09-29 (corpus_review/round1/OPERATOR_RULINGS_R1.json and the round-1 disposition record):
each is the fixture's one fix ("input ambiguous -> fix input"), none of these fixtures had used its fix, and each is
re-adjudicated from scratch with its batch's frozen procedure. Same method as build_fixes.py: derived from the SEALED
fixture, gold and ledger record, only declared paths change, and the model-facing file is separate from gold.

- A1 (SY1, 4 fixtures): the same role relabel as the 8 recorded SY1 fixes: the causal statement becomes the only
  `finding`; the former `finding` observations become `symptom`. Gold roles follow; conclusion and terms unchanged.
- A2 (B4-CONV-R1-08): each option sentence states when packing starts, when dispatch happens relative to it, and when
  delivery happens relative to dispatch, so the dispatch and delivery dates follow by addition only. Facts, surfaces,
  options, gold and reference output are unchanged.
- A3 (B4-CONV-R2-28): each option sentence states that it finishes a stated number of days after starting, so the end
  date is start + days. Facts, surfaces, options, gold and reference output are unchanged.

    python -B build_fixes_cr1.py      # writes cr1_amain/ and cr1_bmain/
"""

import copy
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_fixes import canonical, sha, load, diff, render  # noqa: E402

TRIGGER = "external corpus review round 1 (reviewer A findings A1-A3); operator dispositions 2026-09-29: FIX"
SY1 = {"A4-SYNTH-R1-01": "A1", "B4-SYNTH-R1-02": "A1", "B4-SYNTH-R2-15": "A1", "B4-SYNTH-R3-08": "A1"}
SY1_ROLES = {"finding": "symptom", "diagnosis": "finding"}
CONV = {
    "B4-CONV-R1-08": ("A2",
                      re.compile(r"^(?P<o>\S+) dispatches on (?P<d>\d{4}-\d\d-\d\d) after (?P<n1>\d+ days) of packing "
                                 r"and then takes (?P<n2>\d+ days) in transit\.$"),
                      "{o} starts packing on {d}, dispatches {n1} later and then delivers {n2} after dispatch."),
    "B4-CONV-R2-28": ("A3",
                      re.compile(r"^(?P<o>\S+) can start on (?P<d>\d{4}-\d\d-\d\d) and needs (?P<n>\d+ days) to deliver "
                                 r"and assemble\.$"),
                      "{o} can start on {d} and finishes delivering and assembling {n} later."),
}
DEFECT = {
    "A1": "SY1 causal statement under role 'diagnosis'; the frozen rule requires that a finding states the cause (the "
          "disclosed latent defect)",
    "A2": "'dispatches on <date> after N days of packing': read literally the stated date is the dispatch date and all "
          "four options qualify; counting days inclusively also changes the answer",
    "A3": "'can start on <date> and needs N days': counting the start day as day 1 makes the near miss finish on time, "
          "so two options qualify",
}


def build():
    fixtures = {**load("corpus_a.json", "fixtures"), **load("corpus_b.json", "fixtures")}
    gold = {**load("gold_a.json", "items"), **load("gold_b.json", "items")}
    ledger = load("authoring_ledger.json", "items")
    out = {"A": ([], [], [], []), "B": ([], [], [], [])}
    for fid in sorted(list(SY1) + list(CONV)):
        f, g, d = copy.deepcopy(fixtures[fid]), copy.deepcopy(gold[fid]), copy.deepcopy(ledger[fid])
        if fid in SY1:
            finding_id = SY1[fid]
            causal = [o["id"] for o in f["input"]["observations"] if o["role"] == "diagnosis"]
            assert len(causal) == 1, fid
            for o in f["input"]["observations"]:
                o["role"] = SY1_ROLES.get(o["role"], o["role"])
            g["expected"]["roles"] = {k: SY1_ROLES.get(v, v) for k, v in g["expected"]["roles"].items()}
            for st in g["reference_output"]["statements"]:
                st["role"] = SY1_ROLES.get(st["role"], st["role"])
            d["merged_role"] = [SY1_ROLES.get(r, r) for r in d["merged_role"]]
            changes = {"fixture": diff(fixtures[fid], f), "gold": diff(gold[fid], g), "ledger": diff(ledger[fid], d)}
            for part in changes.values():
                for c in part:
                    assert c["path"].endswith("role") or ".roles." in c["path"] or c["path"].startswith("merged_role"), \
                        (fid, c["path"])
            assert g["expected"]["conclusion"] == gold[fid]["expected"]["conclusion"]
            assert g["expected"]["required_terms"] == gold[fid]["expected"]["required_terms"]
            roles = [o["role"] for o in f["input"]["observations"]]
            assert [o["id"] for o in f["input"]["observations"] if o["role"] == "finding"] == causal
            assert sorted(__import__("collections").Counter(roles).values()) == \
                sorted(__import__("collections").Counter(o["role"] for o in fixtures[fid]["input"]["observations"]).values())
            kind, note = finding_id, ("gold roles and reference-statement roles follow the relabelled input roles; the "
                                      "conclusion, required terms, ids and merges are unchanged")
        else:
            finding_id, pattern, template = CONV[fid]
            units = d["message_units"]
            for u in units[1:]:
                m = pattern.match(u["text"])
                assert m and m.group("o") == u["option"], (fid, u["text"])
                u["text"] = template.format(**m.groupdict())
                for fact in u["facts"]:
                    assert fact["surface"] in u["text"], (fid, fact)
            f["input"]["message"] = " ".join(u["text"] for u in units)
            changes = {"fixture": diff(fixtures[fid], f), "gold": diff(gold[fid], g), "ledger": diff(ledger[fid], d)}
            assert [c["path"] for c in changes["fixture"]] == ["input.message"] and not changes["gold"], fid
            assert all(c["path"].startswith("message_units[") and c["path"].endswith("].text") for c in changes["ledger"])
            assert len(changes["ledger"]) == 4 and units[0]["text"] == ledger[fid]["message_units"][0]["text"]
            kind, note = finding_id, "gold (answer and reference output) unchanged; every bound fact and surface unchanged"
        record = {"fixture_id": fid, "round": "cr1", "trigger": TRIGGER, "finding": kind,
                  "fix": "input ambiguous -> fix input (design step 10: the fixture's one fix)", "defect": DEFECT[kind],
                  "sealed_sha256": {"fixture": sha(fixtures[fid]), "gold": sha(gold[fid]), "ledger": sha(ledger[fid])},
                  "fixed_sha256": {"fixture": sha(f), "gold": sha(g), "ledger": sha(d)},
                  "changes": changes, "gold_note": note}
        part = out[fid[0]]
        for lst, item in zip(part, (record, f, g, d)):
            lst.append(item)
    return out


if __name__ == "__main__":
    out = build()
    for batch, sub, corpus in (("A", "cr1_amain", "A′ main"), ("B", "cr1_bmain", "B′ main")):
        records, f, g, d = out[batch]
        path = HERE / sub
        path.mkdir(exist_ok=True)
        head = {"schema_version": "g-route4.fixes.v1", "batch": corpus, "round": "cr1",
                "trigger": TRIGGER, "seal_commit": "50e6b46994299ffd71c97aa3f81f30637efaba1c"}
        (path / "corpus_fixed.json").write_text(render(dict(head, fixtures=f)), encoding="utf-8", newline="\n")
        (path / "gold_fixed.json").write_text(render(dict(head, items=g)), encoding="utf-8", newline="\n")
        (path / "ledger_fixed.json").write_text(render(dict(head, items=d)), encoding="utf-8", newline="\n")
        (path / "FIX_RECORD.json").write_text(render(dict(head, fixes=records)), encoding="utf-8", newline="\n")
        for r in records:
            print(r["fixture_id"], r["finding"], "|", "; ".join(f"{c['path']}: {c['from']!r} -> {c['to']!r}"
                                                                for v in r["changes"].values() for c in v)[:400])
