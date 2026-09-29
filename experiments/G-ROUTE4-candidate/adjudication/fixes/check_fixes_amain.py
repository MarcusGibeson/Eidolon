"""Re-check the A′ round-1 fixes before re-adjudication, over the current effective corpus.

The pool is the complete 584-fixture corpus as it now stands: the sealed corpus (proved equal to the staging corpus
of dd8193b) with the B′ round-1 fixes AND the A′ round-1 fixes overlaid. The frozen checker is told about exactly the
declared fix texts (keyed by claim, relation and source body) and nothing else; the fixed SY1 construct, the P6
wording and the extraction rename are asserted directly.

    python -B check_fixes_amain.py      # writes round1_amain/FIX_CHECK_REPORT.json; exit 1 on any problem
"""

import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_fixes as BFB  # noqa: E402
import build_fixes_amain as BFA  # noqa: E402
import check_fixes as CFB  # noqa: E402


def main():
    fixed = {}
    for mod in (BFB, BFA):
        _, f, g, d = mod.build()
        fixed.update({x["fixture_id"]: (x, y, z) for x, y, z in zip(f, g, d)})
    tmp = CFB.export_staging(tempfile.mkdtemp(prefix="g4-fixcheck-a-"))
    corpus = tmp / "experiments/G-ROUTE4-candidate/corpus"
    sys.path.insert(0, str(corpus))
    sys.path.insert(0, str(tmp / "tools"))
    import check_corpus as CC
    staged = [json.loads((corpus / "staging" / f"{c}.json").read_text(encoding="utf-8")) for c in CFB.CLASSES]
    sealed_f = {**BFB.load("corpus_a.json", "fixtures"), **BFB.load("corpus_b.json", "fixtures"),
                **BFB.load("reserve_corpus_a.json", "fixtures"), **BFB.load("reserve_corpus_b.json", "fixtures")}
    sealed_l = BFB.load("authoring_ledger.json", "items")
    mismatch = [x["fixture_id"] for doc in staged for x in doc["fixtures"] if x != sealed_f[x["fixture_id"]]]
    mismatch += [x["fixture_id"] for doc in staged for x in doc["design"] if x != sealed_l[x["fixture_id"]]]
    if mismatch or sum(len(d["fixtures"]) for d in staged) != 584:
        raise SystemExit(f"staging corpus differs from the seal: {mismatch[:5]}")
    for doc in staged:
        for key, idx in (("fixtures", 0), ("gold", 1), ("design", 2)):
            doc[key] = [fixed[x["fixture_id"]][idx] if x["fixture_id"] in fixed else x for x in doc[key]]
    declared = set()
    edits = [(fid, sid, new) for fid, (sid, old, new) in {**BFB.P6, **BFB.P4, **BFA.P6}.items()]
    edits += [(fid, sid, new) for fid, rows in BFA.SUPPORT.items() for sid, old, new in rows]
    for fid, sid, new in edits:
        d = fixed[fid][2]
        src = next(s for s in d["research_contract"]["sources"] if s["source_id"] == sid)
        claim = next(c for c in d["research_contract"]["claims"] if c["claim_id"] == src["claim_id"])
        declared.add((claim["text"], src["relation"], CC.split_source_prefix(new)[2]))
    original = CC.research_allowed_bodies

    def allowed(topic, claim, source):
        bodies = set(original(topic, claim, source))
        body = CC.split_source_prefix(source.get("text", ""))[2]
        if (claim.get("text"), source.get("relation"), body) in declared:
            bodies.add(body)
        return bodies
    CC.research_allowed_bodies = allowed
    problems, report = CC.check(staged)
    for fid in BFA.SY1:
        obs = fixed[fid][0]["input"]["observations"]
        findings = [o for o in obs if o["role"] == "finding"]
        if len(findings) != 1 or not any(w in findings[0]["text"] for w in ("because", "cause")):
            problems.append(f"{fid}: fixed SY1 does not have exactly one finding stating the cause")
    for fid, (sid, old, new) in BFA.P6.items():
        if " only" in new.lower():
            problems.append(f"{fid}: fixed P6 source is still exclusionary")
    ex = fixed["A4-EXTR-R1-03"]
    if list(ex[0]["input"]["schema"]) != ["town", "items_sold", "takings"] or ex[1]["expected"]["town"] != "Dalihi":
        problems.append("A4-EXTR-R1-03: rename not realized as declared")
    out = {"schema_version": "g-route4.fix-check.v1", "staging_commit": CFB.STAGING_COMMIT, "fixtures_checked": 584,
           "fixes_applied": {"B′ round 1": sorted(BFB.P6) + sorted(BFB.P4) + BFB.SY1,
                             "A′ round 1": sorted(set(fixed) - set(BFB.P6) - set(BFB.P4) - set(BFB.SY1))},
           "staging_equals_seal": True, "problems": problems, "passed": not problems,
           **{k: report[k] for k in ("trigram", "trigram_task_relevant", "o3_entities", "o3_identifier_gate", "o6",
                                     "n1_duplicates", "fine_signature_clashes", "canonical_signature_clashes",
                                     "reply_length", "caps", "research", "conversation")}}
    (HERE / "round1_amain" / "FIX_CHECK_REPORT.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n",
                                                                  encoding="utf-8", newline="\n")
    for p in problems:
        print("FAIL", p)
    print(f"584 fixtures checked with {len(fixed)} fixes applied (14 B′ + 6 A′); {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
