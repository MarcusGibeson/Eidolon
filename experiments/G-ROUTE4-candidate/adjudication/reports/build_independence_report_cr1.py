"""Successor independence report for the final corpus after external corpus review round 1 (26 recorded fixes).

Final corpus: the seal with every recorded fix overlaid: B′ round 1 (14), A′ round 1 (6) and the review-driven cr1
fixes (6: 1 A′, 5 B′). No replacement. Same tool, pool and method as build_independence_report.py (whose helpers are
imported, unchanged): the authoring-stage independence tool `check_corpus.py` at dd8193b, run over the sealed corpus
(baseline), the final corpus with the declared fix-text exemption (binding) and the final corpus with it disabled
(proof). The frozen INDEPENDENCE_REPORT.json is not modified; this report compares every class-level value against it.

    python -B build_independence_report_cr1.py   # writes experiments/G-ROUTE4-candidate/INDEPENDENCE_REPORT_CR1.json
"""

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_independence_report as BIR  # noqa: E402

sys.path.insert(0, str(BIR.FIXES))
import build_fixes_cr1 as BFC  # noqa: E402

H, BFB, BFA, CFB = BIR.H, BIR.BFB, BIR.BFA, BIR.CFB
OUT = BIR.CAND / "INDEPENDENCE_REPORT_CR1.json"
FROZEN = BIR.CAND / "INDEPENDENCE_REPORT.json"
CR1_COMMIT = "2baa3936ddd48a71263a7024c9582cccd6324b35"


def main():
    fixed, records = {}, {}
    for label, mod in (("B′ round 1", BFB), ("A′ round 1", BFA)):
        recs, f, g, d = mod.build()
        fixed.update({x["fixture_id"]: (x, y, z) for x, y, z in zip(f, g, d)})
        records.update({r["fixture_id"]: dict(r, round_label=label) for r in recs})
    for recs, f, g, d in BFC.build().values():
        assert not {x["fixture_id"] for x in f} & set(fixed)
        fixed.update({x["fixture_id"]: (x, y, z) for x, y, z in zip(f, g, d)})
        records.update({r["fixture_id"]: dict(r, round_label="cr1") for r in recs})
    for sub, corpus, gold in (("round1_bmain", "corpus_b.json", "gold_b.json"), ("round1_amain", "corpus_a.json", "gold_a.json"),
                              ("cr1_bmain", "corpus_b.json", "gold_b.json"), ("cr1_amain", "corpus_a.json", "gold_a.json")):
        committed = H.fixed_fixtures(BIR.FIXES / sub, corpus=corpus)
        H.gold_path_overlay(BIR.FIXES / sub, gold_file=gold)
        for fid, f in committed.items():
            assert H.canonical(f) == H.canonical(fixed[fid][0]), fid
    assert len(fixed) == 26

    tmp = CFB.export_staging(tempfile.mkdtemp(prefix="g4-independence-cr1-"))
    corpus_dir = tmp / "experiments/G-ROUTE4-candidate/corpus"
    sys.path.insert(0, str(corpus_dir))
    sys.path.insert(0, str(tmp / "tools"))
    import check_corpus as CC
    sealed_docs = [json.loads((corpus_dir / "staging" / f"{c}.json").read_text(encoding="utf-8")) for c in CFB.CLASSES]
    sealed_f = {**BFB.load("corpus_a.json", "fixtures"), **BFB.load("corpus_b.json", "fixtures"),
                **BFB.load("reserve_corpus_a.json", "fixtures"), **BFB.load("reserve_corpus_b.json", "fixtures")}
    sealed_l = BFB.load("authoring_ledger.json", "items")
    mismatch = [x["fixture_id"] for doc in sealed_docs for x in doc["fixtures"] if x != sealed_f[x["fixture_id"]]]
    mismatch += [x["fixture_id"] for doc in sealed_docs for x in doc["design"] if x != sealed_l[x["fixture_id"]]]
    if mismatch or sum(len(d["fixtures"]) for d in sealed_docs) != 584:
        raise SystemExit(f"staging corpus differs from the seal: {mismatch[:5]}")
    final_docs = copy.deepcopy(sealed_docs)
    for doc in final_docs:
        for key, idx in (("fixtures", 0), ("gold", 1), ("design", 2)):
            doc[key] = [fixed[x["fixture_id"]][idx] if x["fixture_id"] in fixed else x for x in doc[key]]

    declared, declared_sources = set(), []
    edits = [(fid, sid, new) for fid, (sid, old, new) in {**BFB.P6, **BFB.P4, **BFA.P6}.items()]
    edits += [(fid, sid, new) for fid, rows in BFA.SUPPORT.items() for sid, old, new in rows]
    for fid, sid, new in edits:
        d = fixed[fid][2]
        src = next(s for s in d["research_contract"]["sources"] if s["source_id"] == sid)
        claim = next(c for c in d["research_contract"]["claims"] if c["claim_id"] == src["claim_id"])
        declared.add((claim["text"], src["relation"], CC.split_source_prefix(new)[2]))
        declared_sources.append(f"{fid} {sid}")
    original = CC.research_allowed_bodies

    def allowed(topic, claim, source):
        bodies = set(original(topic, claim, source))
        body = CC.split_source_prefix(source.get("text", ""))[2]
        if (claim.get("text"), source.get("relation"), body) in declared:
            bodies.add(body)
        return bodies

    def run(docs, exemption):
        CC.research_allowed_bodies = allowed if exemption else original
        try:
            return CC.check(copy.deepcopy(docs))
        finally:
            CC.research_allowed_bodies = original

    base_problems, base = run(sealed_docs, False)
    problems, final = run(final_docs, True)
    raw_problems, _ = run(final_docs, False)
    flagged = sorted(p for p in raw_problems if p not in problems)
    declared_fids = sorted({s.split()[0] for s in declared_sources})
    exemption_proof = {"declared_fix_sources": sorted(declared_sources), "problems_with_exemption_disabled": len(flagged),
                       "flagged": flagged,
                       "flagged_exactly_the_declared_research_fixtures":
                           sorted({p.split(":")[0] for p in flagged}) == declared_fids and len(flagged) == len(declared_sources),
                       "cr1_fixes_need_no_exemption": True}
    if not exemption_proof["flagged_exactly_the_declared_research_fixtures"]:
        problems.append("the declared fix-text exemption covers something other than the 12 declared source texts")
    for fid in list(BFA.SY1) + list(BFC.SY1):
        obs = fixed[fid][0]["input"]["observations"]
        findings = [o for o in obs if o["role"] == "finding"]
        if len(findings) != 1 or not any(w in findings[0]["text"] for w in ("because", "cause")):
            problems.append(f"{fid}: fixed SY1 does not have exactly one finding stating the cause")
    if base_problems:
        problems.append(f"sealed baseline does not reproduce 0 problems: {base_problems[:3]}")

    sets_final, sets_base = BIR.trigram_sets(CC, final_docs), BIR.trigram_sets(CC, sealed_docs)
    for tc, rep in final["trigram"].items():
        v, a, b = BIR.class_max(sets_final[tc])
        assert round(v, 4) == rep["max_jaccard"] and {a, b} == set(rep["max_pair"]), (tc, v, rep)
        assert len(sets_final[tc]["boilerplate"]) == rep["boilerplate_trigrams"] and sets_final[tc]["pool"] == rep["pool"]

    n8 = {}
    for tc in sorted(final["trigram"]):
        sets = sets_final[tc]
        main_rows = [(fid, s, BIR.slot_of(CC, fid)) for fid, src, s in sets["rows"] if src == "G4" and BIR.slot_of(CC, fid)[1] == "main"]
        for risk in ("R1", "R2", "R3", "R4"):
            best, pairs = (0.0, "", "", ""), 0
            for fa, sa, (pa, _, ra, fam_a) in main_rows:
                if pa != "A" or ra != risk:
                    continue
                for fb, sb, (pb, _, rb, fam_b) in main_rows:
                    if pb == "B" and rb == risk and fam_b == fam_a:
                        pairs += 1
                        v = BIR.jac(sa, sb)
                        if v > best[0] or not best[1]:
                            best = (v, fa, fb, fam_a)
            n8[f"{tc}|{risk}"] = ({"same_family_pairs": pairs, "max_jaccard": round(best[0], 4), "max_pair": list(best[1:3]),
                                   "family": best[3]} if pairs else
                                  {"same_family_pairs": 0, "max_jaccard": None, "max_pair": None, "family": None})

    fix_effects = {}
    for fid in sorted(fixed):
        tc = fixed[fid][0]["task_class"]
        b, f = BIR.fixture_max(sets_base[tc], fid), BIR.fixture_max(sets_final[tc], fid)
        fix_effects[fid] = {"round": records[fid]["round_label"], "task_class": tc, "defect": records[fid]["defect"],
                            "max_jaccard_sealed_text": {"value": b[0], "partner": b[1]},
                            "max_jaccard_fixed_text": {"value": f[0], "partner": f[1]},
                            "sealed_sha256": records[fid]["sealed_sha256"], "fixed_sha256": records[fid]["fixed_sha256"]}

    bp = json.loads((BIR.CAND / "blueprint/BLUEPRINT.json").read_text(encoding="utf-8"))
    o5 = {}
    for tc in sorted(final["trigram"]):
        sets = sets_final[tc]
        templates = bp["classes"][tc]["family_template_text"]
        in_template = [{"family": fam, "trigram": " ".join(tg), "pool_frequency": sets["freq"][tg]}
                       for fam, text in sorted(templates.items()) for tg in sorted(CC.I._trigrams(text) & sets["boilerplate"])]
        o5[tc] = {"boilerplate_trigrams_in_family_templates": in_template,
                  "single_family_boilerplate_trigrams": final["trigram"][tc]["o5_single_family_boilerplate"]}
        if in_template or final["trigram"][tc]["o5_single_family_boilerplate"]:
            problems.append(f"O5: {tc} has boilerplate in a family template or single-family boilerplate")

    # reproduction of the frozen report's class-level values (the values bound in INDEPENDENCE_REPORT.json)
    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
    fr = frozen["result_final"]
    reproduction = {}
    for key in ("trigram", "trigram_task_relevant"):
        for tc in fr[key]:
            for m in ("pool", "boilerplate_trigrams", "max_jaccard", "max_pair", "pairs_over_bound"):
                reproduction[f"{key}.{tc}.{m}"] = {"frozen": fr[key][tc][m], "final": final[key][tc][m]}
    for m in ("n1_duplicates", "fine_signature_clashes", "canonical_signature_clashes"):
        reproduction[m] = {"frozen": fr[m], "final": final[m]}
    for m in ("g4_entities", "shared"):
        reproduction[f"o3_entities.{m}"] = {"frozen": fr["o3_entities"][m], "final": final["o3_entities"][m]}
    for m in ("g4_identifiers", "shared"):
        reproduction[f"o3_identifier_gate.{m}"] = {"frozen": fr["o3_identifier_gate"][m], "final": final["o3_identifier_gate"][m]}
    reproduction["o6"] = {"frozen": fr["o6"], "final": final["o6"]}
    for tc in fr["trigram"]:
        reproduction[f"o5.{tc}.single_family_boilerplate"] = {"frozen": fr["trigram"][tc]["o5_single_family_boilerplate"],
                                                              "final": final["trigram"][tc]["o5_single_family_boilerplate"]}
    # compare as JSON values (the checker returns a pair as a tuple; the frozen report holds it as a JSON list)
    reproduction = json.loads(json.dumps(reproduction))
    differing = sorted(k for k, v in reproduction.items() if v["frozen"] != v["final"])
    bounds_met = all(final["trigram"][tc]["pairs_over_bound"] == 0 and final["trigram_task_relevant"][tc]["pairs_over_bound"] == 0
                     for tc in final["trigram"]) and final["o3_entities"]["shared"] == 0 and \
        final["o3_identifier_gate"]["shared"] == 0 and final["o6"]["collisions"] == 0 and final["n1_duplicates"] == 0 and \
        final["fine_signature_clashes"] == 0 and final["canonical_signature_clashes"] == 0
    if not bounds_met:
        problems.append("a frozen independence bound is not met on the final corpus")

    final_pool = {}
    for name, key, part in (("corpus_a.json", "fixtures", 0), ("corpus_b.json", "fixtures", 0),
                            ("reserve_corpus_a.json", "fixtures", 0), ("reserve_corpus_b.json", "fixtures", 0),
                            ("gold_a.json", "items", 1), ("gold_b.json", "items", 1),
                            ("reserve_gold_a.json", "items", 1), ("reserve_gold_b.json", "items", 1),
                            ("authoring_ledger.json", "items", 2)):
        items = BFB.load(name, key)
        items.update({fid: v[part] for fid, v in fixed.items() if fid in items})
        final_pool[name] = {"records": len(items), "fixed_records": sorted(set(items) & set(fixed)),
                            "canonical_sha256": H.sha256(H.canonical(sorted(items.values(), key=lambda x: x["fixture_id"])))}
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=BIR.ROOT, capture_output=True, text=True, check=True).stdout.strip()
    fixes = {label: {"commit": commit, "fixtures": sorted(f for f, r in records.items() if r["round_label"] == label),
                     "fix_record_lf_sha256": [H.lf_sha256(BIR.FIXES / s / "FIX_RECORD.json") for s in subs]}
             for label, commit, subs in (("B′ round 1", BIR.FIX_COMMITS["B′ round 1"], ["round1_bmain"]),
                                         ("A′ round 1", BIR.FIX_COMMITS["A′ round 1"], ["round1_amain"]),
                                         ("cr1", CR1_COMMIT, ["cr1_amain", "cr1_bmain"]))}
    report = {
        "schema_version": "g-route4.independence-report.v1",
        "design_step": "order of work 3.7 closure: independence re-check over the final corpus after the review-driven "
                       "changes (design step 8: re-run after every fix)",
        "supersedes_for_the_final_corpus": {"file": "INDEPENDENCE_REPORT.json", "lf_sha256": H.lf_sha256(FROZEN),
                                            "note": "the frozen report is not modified; it remains the record for the "
                                                    "20-fix corpus reviewed in round 1"},
        "valid": not problems, "problems": problems,
        "reproduction_of_frozen_values": {"compared": len(reproduction), "differing": differing,
                                          "all_reproduced": not differing, "values": reproduction},
        "bounds_met": bounds_met,
        "binding": {"seal_commit": BIR.SEAL, "blueprint_commit": BIR.BLUEPRINT, "audit_sample_commit": BIR.AUDIT_SAMPLE_COMMIT,
                    "generated_at_parent_commit": head,
                    "sealed_files_lf_sha256": {n: H.lf_sha256(H.SEALED / n) for n in BIR.SEALED_FILES},
                    "fixes": fixes, "replacements": 0, "final_pool": final_pool,
                    "tool": dict(frozen["binding"]["tool"], this_script_lf_sha256=H.lf_sha256(Path(__file__)),
                                 predecessor_script_lf_sha256=H.lf_sha256(HERE / "build_independence_report.py")),
                    "g_route3_files_unchanged": frozen["binding"]["g_route3_files_unchanged"]},
        "bounds": frozen["bounds"], "scope": frozen["scope"],
        "result_final": final,
        "sealed_baseline": {"problems": len(base_problems), "passed": not base_problems},
        "fix_text_exemption_proof": exemption_proof,
        "fix_effects": fix_effects,
        "n8_same_family_a_b_max_jaccard_per_cell": n8,
        "o5": o5,
    }
    OUT.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    for p in problems:
        print("FAIL", p)
    print(f"independence report (26 fixes): {'VALID' if not problems else 'INVALID'}; {len(problems)} problems; "
          f"frozen values reproduced: {not differing} ({len(reproduction)} compared; differing: {differing}); "
          f"bounds met: {bounds_met}")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
