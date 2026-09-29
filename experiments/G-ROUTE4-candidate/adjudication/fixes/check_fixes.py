"""Re-check the round-1 fixes before re-adjudication (design: "after every fix ..., before its re-adjudication, the
mechanical independence checks and caps are re-run").

Runs the frozen authoring checker from the staging checkpoint dd8193b over the complete 584-fixture corpus with the
14 fixes applied:
1. export dd8193b (checker, authoring toolchain, staging corpus, tools, blueprint) with `git archive`;
2. prove the staging corpus equals the sealed corpus record for record (fixtures, gold, ledger);
3. overlay the fixed records;
4. run every check over the whole pool (structure, slots, caps, reserves, positions, O3, O5, O6, N1, signatures,
   overlap, reply length, names). The checker's authoring-paraphrase rule is told about exactly the declared fix
   texts, and nothing else; the fixed SY1 construct is asserted directly.

    python -B check_fixes.py            # writes round1_bmain/FIX_CHECK_REPORT.json; exit 1 on any problem
"""

import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
STAGING_COMMIT = "dd8193bfcf1db05c752635dc4f8911a58098c97b"
CLASSES = ("extraction", "synthesis", "planning", "conversation", "research")
sys.path.insert(0, str(HERE))
import build_fixes as BF  # noqa: E402


def export_staging(dest):
    paths = ["experiments/G-ROUTE4-candidate", "tools", "experiments/G-ROUTE3-candidate", "experiments/G-ROUTE1-candidate"]
    tar = Path(dest) / "staging.tar"
    subprocess.run(["git", "-c", "core.autocrlf=false", "archive", "-o", str(tar), STAGING_COMMIT, "--", *paths],
                   cwd=ROOT, check=True)
    with tarfile.open(tar) as t:
        t.extractall(dest)
    return Path(dest)


def main():
    records, fixed_f, fixed_g, fixed_l = BF.build()
    fixed = {f["fixture_id"]: (f, g, d) for f, g, d in zip(fixed_f, fixed_g, fixed_l)}
    tmp = export_staging(tempfile.mkdtemp(prefix="g4-fixcheck-"))
    corpus = tmp / "experiments/G-ROUTE4-candidate/corpus"
    sys.path.insert(0, str(corpus))
    sys.path.insert(0, str(tmp / "tools"))
    import check_corpus as CC
    staged = [json.loads((corpus / "staging" / f"{c}.json").read_text(encoding="utf-8")) for c in CLASSES]
    # 2. the staging corpus is the sealed corpus
    sealed_f = {**BF.load("corpus_a.json", "fixtures"), **BF.load("corpus_b.json", "fixtures"),
                **BF.load("reserve_corpus_a.json", "fixtures"), **BF.load("reserve_corpus_b.json", "fixtures")}
    sealed_g = {**BF.load("gold_a.json", "items"), **BF.load("gold_b.json", "items"),
                **BF.load("reserve_gold_a.json", "items"), **BF.load("reserve_gold_b.json", "items")}
    sealed_l = BF.load("authoring_ledger.json", "items")
    mismatch = [x["fixture_id"] for doc in staged for x in doc["fixtures"] if x != sealed_f[x["fixture_id"]]]
    mismatch += [x["fixture_id"] for doc in staged for x in doc["gold"]
                 if {k: x[k] for k in ("expected", "fixture_id", "rationale", "reference_output")} != sealed_g[x["fixture_id"]]]
    mismatch += [x["fixture_id"] for doc in staged for x in doc["design"] if x != sealed_l[x["fixture_id"]]]
    if mismatch or sum(len(d["fixtures"]) for d in staged) != 584:
        raise SystemExit(f"staging corpus differs from the seal: {mismatch[:5]}")
    # 3. overlay the fixes in place (order preserved)
    for doc in staged:
        for key, idx in (("fixtures", 0), ("gold", 1), ("design", 2)):
            doc[key] = [fixed[x["fixture_id"]][idx] if x["fixture_id"] in fixed else x for x in doc[key]]
    # the authoring-paraphrase rule learns exactly the declared fix texts (keyed by claim text and fix text)
    declared = {}
    for fid, (sid, old, new) in {**BF.P6, **BF.P4}.items():
        d = fixed[fid][2]
        src = next(s for s in d["research_contract"]["sources"] if s["source_id"] == sid)
        claim = next(c for c in d["research_contract"]["claims"] if c["claim_id"] == src["claim_id"])
        declared[(claim["text"], src["relation"], new)] = fid
    original = CC.research_allowed_bodies

    def allowed(topic, claim, source):
        bodies = set(original(topic, claim, source))
        if (claim.get("text"), source.get("relation"), source.get("text")) in declared:
            bodies.add(source["text"])
        return bodies
    CC.research_allowed_bodies = allowed
    # 4. every check over the whole pool
    problems, report = CC.check(staged)
    # the fixed SY1 construct: exactly one 'finding', and it is the observation that states the cause
    for fid in BF.SY1:
        f = fixed[fid][0]
        findings = [o for o in f["input"]["observations"] if o["role"] == "finding"]
        if len(findings) != 1 or "cause" not in findings[0]["text"] and "because" not in findings[0]["text"]:
            problems.append(f"{fid}: fixed SY1 does not have exactly one finding stating the cause")
    # the fixed P6 sources carry no exclusion word
    for fid, (sid, old, new) in BF.P6.items():
        if " only" in new.lower():
            problems.append(f"{fid}: fixed P6 source is still exclusionary")
    out = {"schema_version": "g-route4.fix-check.v1", "staging_commit": STAGING_COMMIT, "fixtures_checked": 584,
           "fixes_applied": sorted(fixed), "staging_equals_seal": True, "problems": problems, "passed": not problems,
           **{k: report[k] for k in ("trigram", "trigram_task_relevant", "o3_entities", "o3_identifier_gate", "o6",
                                     "n1_duplicates", "fine_signature_clashes", "canonical_signature_clashes",
                                     "reply_length", "caps", "research", "conversation")}}
    (HERE / "round1_bmain" / "FIX_CHECK_REPORT.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n",
                                                                  encoding="utf-8", newline="\n")
    for p in problems:
        print("FAIL", p)
    print(f"584 fixtures checked with {len(fixed)} fixes applied; {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
