"""G-ROUTE4 B′ round-1 fixes (operator decisions 2026-09-29: input ambiguous -> fix input, 14 fixtures).

The seal is never modified. Each fix is derived from the SEALED fixture, gold and ledger record, changes only the
declared paths, and is written to separate files so the adjudicator's run path never reads gold:

    round1_bmain/corpus_fixed.json   model-facing fixed fixtures (the only file the run path reads)
    round1_bmain/gold_fixed.json     fixed gold, reference outputs and rationales
    round1_bmain/ledger_fixed.json   fixed authoring-ledger records
    round1_bmain/FIX_RECORD.json     defect, every changed path (from -> to), sealed and fixed digests

    python -B build_fixes.py            # rebuild and verify that only the declared paths differ from the seal
"""

import copy
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SEALED = ROOT / "experiments/G-ROUTE4-candidate/sealed"
OUT = HERE / "round1_bmain"
DECISIONS_RUN = "g4adj-bmain-20260929T155837Z"

# P6: the exclusionary 'only' is removed; the source then states a narrower scope without excluding the rest
# (as G-ROUTE3's P6 sources do), so C1 stays unresolved with scope_mismatch.
P6 = {
    "B4-RSRCH-R1-06": ("S1", "Gojedo's bus pass covers the town routes only.", "Gojedo's bus pass covers the town routes."),
    "B4-RSRCH-R1-14": ("S1", "Badipa's library opens only on weekdays.", "Badipa's library opens on weekdays."),
    "B4-RSRCH-R2-06": ("S1", "Wanidu's discount applies only to office furniture.", "Wanidu's discount applies to office furniture."),
    "B4-RSRCH-R2-14": ("S1", "Mupafe's helpline answers calls only on working days.", "Mupafe's helpline answers calls on working days."),
    "B4-RSRCH-R3-06": ("S1", "Jevuju's encryption covers only the laptops.", "Jevuju's encryption covers the laptops."),
    "B4-RSRCH-R3-14": ("S1", "Tosepe's privacy notice applies only to the booking app.", "Tosepe's privacy notice applies to the booking app."),
    "B4-RSRCH-R3-18": ("S1", "Jule's audit logging is on only for the payroll servers.", "Jule's audit logging is on for the payroll servers."),
}
# P4: the support paraphrase plainly states anonymity; S1 and S2 (one lineage) and S3 (a second lineage) still
# support C1, so the frozen two-lineage feature and gold are unchanged.
P4 = {"B4-RSRCH-R3-04": ("S3", "Roke's survey tool strips names from submitted answers.",
                         "Roke's survey tool keeps every response anonymous.")}
# SY1: the causal statement becomes the only 'finding' (as the frozen rule and SY1 definition require); the former
# symptom findings become 'symptom'. The role multiset keeps its shape, so band and mergeable pair are unchanged.
SY1 = ["B4-SYNTH-R1-01", "B4-SYNTH-R1-03", "B4-SYNTH-R2-13", "B4-SYNTH-R2-14", "B4-SYNTH-R3-07", "B4-SYNTH-R3-09"]
SY1_ROLES = {"finding": "symptom", "diagnosis": "finding"}
DEFECT = {
    "p6": "P6 narrower-scope source worded with the exclusionary 'only' (reads as a contradiction, not a narrower scope)",
    "p4": "P4 support paraphrase did not establish anonymity (read as one supporting lineage)",
    "sy1": "SY1 causal statement under role 'diagnosis'; the frozen rule requires that a finding states the cause",
}


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha(obj):
    return hashlib.sha256(canonical(obj).encode("utf-8")).hexdigest()


def load(name, key):
    return {x["fixture_id"]: x for x in json.loads((SEALED / name).read_text(encoding="utf-8"))[key]}


def diff(a, b, path=""):
    if isinstance(a, dict) and isinstance(b, dict) and set(a) == set(b):
        return [d for k in sorted(a) for d in diff(a[k], b[k], f"{path}.{k}" if path else k)]
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in diff(x, y, f"{path}[{i}]")]
    return [] if a == b else [{"path": path, "from": a, "to": b}]


def build():
    fixtures, gold, ledger = load("corpus_b.json", "fixtures"), load("gold_b.json", "items"), load("authoring_ledger.json", "items")
    records, out_f, out_g, out_l = [], [], [], []
    for fid in sorted(list(P6) + list(P4) + SY1):
        f, g, d = copy.deepcopy(fixtures[fid]), copy.deepcopy(gold[fid]), copy.deepcopy(ledger[fid])
        if fid in P6 or fid in P4:
            kind = "p6" if fid in P6 else "p4"
            sid, old, new = (P6 if fid in P6 else P4)[fid]
            src = next(s for s in f["input"]["sources"] if s["source_id"] == sid)
            led = next(s for s in d["research_contract"]["sources"] if s["source_id"] == sid)
            assert src["text"] == old == led["text"], fid
            src["text"] = led["text"] = new
            allowed = {f"input.sources[{int(sid[1:]) - 1}].text", f"research_contract.sources[{int(sid[1:]) - 1}].text"}
        else:
            kind = "sy1"
            for o in f["input"]["observations"]:
                o["role"] = SY1_ROLES.get(o["role"], o["role"])
            g["expected"]["roles"] = {k: SY1_ROLES.get(v, v) for k, v in g["expected"]["roles"].items()}
            for st in g["reference_output"]["statements"]:
                st["role"] = SY1_ROLES.get(st["role"], st["role"])
            d["merged_role"] = [SY1_ROLES.get(r, r) for r in d["merged_role"]]
            allowed = None
        changes = {"fixture": diff(fixtures[fid], f), "gold": diff(gold[fid], g), "ledger": diff(ledger[fid], d)}
        if allowed is not None:
            touched = {c["path"] for c in changes["fixture"] + changes["ledger"]}
            assert touched == allowed and not changes["gold"], (fid, touched)
        else:
            for part in ("fixture", "gold", "ledger"):
                for c in changes[part]:
                    assert c["path"].endswith(("role", "merged_role[0]")) or ".roles." in c["path"] or \
                        c["path"].startswith("expected.roles"), (fid, c["path"])
            assert g["expected"]["conclusion"] == gold[fid]["expected"]["conclusion"]
            assert g["expected"]["required_terms"] == gold[fid]["expected"]["required_terms"]
            causal = [o for o in f["input"]["observations"] if o["role"] == "finding"]
            assert len(causal) == 1 and causal[0]["id"] == next(o["id"] for o in fixtures[fid]["input"]["observations"]
                                                                if o["role"] == "diagnosis"), fid
        records.append({"fixture_id": fid, "round": 1, "fix": "input ambiguous -> fix input", "defect": DEFECT[kind],
                        "sealed_sha256": {"fixture": sha(fixtures[fid]), "gold": sha(gold[fid]), "ledger": sha(ledger[fid])},
                        "fixed_sha256": {"fixture": sha(f), "gold": sha(g), "ledger": sha(d)},
                        "changes": changes,
                        "gold_note": None if kind != "sy1" else
                        "gold roles and reference-statement roles follow the relabelled input roles; the conclusion, "
                        "required terms, observation ids and merges are unchanged"})
        out_f.append(f)
        out_g.append(g)
        out_l.append(d)
    return records, out_f, out_g, out_l


def render(obj):
    return json.dumps(obj, indent=1, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    records, f, g, d = build()
    OUT.mkdir(parents=True, exist_ok=True)
    head = {"schema_version": "g-route4.fixes.v1", "batch": "B′ main", "round": 1, "decisions_run": DECISIONS_RUN,
            "seal_commit": "50e6b46994299ffd71c97aa3f81f30637efaba1c"}
    (OUT / "corpus_fixed.json").write_text(render(dict(head, fixtures=f)), encoding="utf-8", newline="\n")
    (OUT / "gold_fixed.json").write_text(render(dict(head, items=g)), encoding="utf-8", newline="\n")
    (OUT / "ledger_fixed.json").write_text(render(dict(head, items=d)), encoding="utf-8", newline="\n")
    (OUT / "FIX_RECORD.json").write_text(render(dict(head, fixes=records)), encoding="utf-8", newline="\n")
    for r in records:
        n = sum(len(v) for v in r["changes"].values())
        print(f"{r['fixture_id']}: {n} changed values ({', '.join(sorted({c['path'].split('[')[0].split('.')[0] for v in r['changes'].values() for c in v}))})")
