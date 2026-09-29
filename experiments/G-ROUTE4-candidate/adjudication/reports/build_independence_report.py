"""G-ROUTE4 independence report over the final corpus (design order of work, step 3.6).

The final corpus is the sealed corpus (seal 50e6b46) with the 20 authorized, recorded round-1 fixes overlaid
(14 B′ in fixes/round1_bmain, 6 A′ in fixes/round1_amain). No fixture was replaced; the seal is not modified.

Every measure is computed by the frozen authoring-stage independence tool, `check_corpus.py` at staging checkpoint
dd8193b (the tool of blueprint §4 that ran before the seal and at every fix re-check), over its one pool per class
(all 584 G-ROUTE4 fixtures, main and reserve, plus G-ROUTE3's A and B fixtures). Nothing in the tool is changed:
- it runs three times: over the sealed corpus (baseline), over the final corpus with the declared fix-text exemption
  (the binding result), and over the final corpus with that exemption disabled (proof that exactly the 12 declared
  research source texts are what the exemption covers);
- N8 (maximum same-family A′–B′ Jaccard per cell) and the per-fix overlap effects are read from the tool's own
  trigram sets (pinned-text removal, then the 25%-frequency boilerplate rule per class pool), reconstructed here and
  asserted equal to the tool's reported per-class maxima before use.

    python -B build_independence_report.py     # writes experiments/G-ROUTE4-candidate/INDEPENDENCE_REPORT.json

No network, dictionary or model is used.
"""

import collections
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ADJ = HERE.parent
CAND = ADJ.parent
ROOT = CAND.parents[1]
FIXES = ADJ / "fixes"
OUT = CAND / "INDEPENDENCE_REPORT.json"
sys.path.insert(0, str(FIXES))
sys.path.insert(0, str(ADJ))
import build_fixes as BFB  # noqa: E402
import build_fixes_amain as BFA  # noqa: E402
import check_fixes as CFB  # noqa: E402
import g4_adjudicate as H  # noqa: E402

SEAL = "50e6b46994299ffd71c97aa3f81f30637efaba1c"
BLUEPRINT = "1156d0645b1b113b91c65e4a485b7f75ffa10061"
AUDIT_SAMPLE_COMMIT = "29f5a477693d703699af62f9fc0e0945c9c66be2"
FIX_COMMITS = {"B′ round 1": "28718001d8e47194a93e444c771ec1167c040c28",
               "A′ round 1": "8774a57a4bfc8d9f0f214d05253c016795385d43"}
SEALED_FILES = ["corpus_a.json", "corpus_b.json", "reserve_corpus_a.json", "reserve_corpus_b.json", "gold_a.json",
                "gold_b.json", "reserve_gold_a.json", "reserve_gold_b.json", "authoring_ledger.json"]
G3_FILES = ["experiments/G-ROUTE3-candidate/corpus_a.json", "experiments/G-ROUTE3-candidate/corpus_b.json",
            "experiments/G-ROUTE3-candidate/gold_a.json", "experiments/G-ROUTE3-candidate/gold_b.json",
            "tools/g_route3_independence.py"]


def lf_sha(data):
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def git_blob(commit, path):
    return subprocess.run(["git", "-c", "core.autocrlf=false", "show", f"{commit}:{path}"], cwd=ROOT,
                          capture_output=True, check=True).stdout


def slot_of(CC, fid):
    s = CC.SLOTS[fid]
    return s["phase"], s["role"], s["risk"], s["family"]


def trigram_sets(CC, staged):
    """The tool's own per-class trigram sets (jaccard_pass): pinned texts removed, then class-pool boilerplate."""
    I = CC.I
    pin = set()
    for text in CC.PINNED:
        pin |= I._trigrams(text)
    pool = [(f, "G4") for s in staged for f in s["fixtures"]] + [(f, "G3") for f, _ in CC.g3_fixtures()]
    by_class = collections.defaultdict(list)
    for f, src in pool:
        by_class[f["task_class"]].append((f["fixture_id"], src, I._trigrams(I._content(f)) - pin))
    out = {}
    for tc, rows in by_class.items():
        freq = collections.Counter(tg for _, _, s in rows for tg in s)
        boiler = {tg for tg, n in freq.items() if n >= I.BOILERPLATE_SHARE * len(rows)}
        out[tc] = {"rows": [(fid, src, s - boiler) for fid, src, s in rows], "boilerplate": boiler, "freq": freq,
                   "pool": len(rows)}
    return out


def jac(a, b):
    u = a | b
    return len(a & b) / len(u) if u else 0.0


def class_max(sets):
    best = (0.0, "", "")
    rows = sets["rows"]
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            if rows[i][1] == "G3" and rows[j][1] == "G3":
                continue
            v = jac(rows[i][2], rows[j][2])
            if v > best[0]:
                best = (v, rows[i][0], rows[j][0])
    return best


def fixture_max(sets, fid):
    rows = sets["rows"]
    me = next(s for f, _, s in rows if f == fid)
    best = (0.0, "")
    for f, _, s in rows:
        if f != fid:
            v = jac(me, s)
            if v > best[0]:
                best = (v, f)
    return round(best[0], 4), best[1]


def main():
    fixed, records = {}, {}
    for label, mod in (("B′ round 1", BFB), ("A′ round 1", BFA)):
        recs, f, g, d = mod.build()
        fixed.update({x["fixture_id"]: (x, y, z) for x, y, z in zip(f, g, d)})
        records.update({r["fixture_id"]: dict(r, round_label=label) for r in recs})
    # the rebuilt fixes are the committed ones, bound to their recorded digests
    for sub, corpus, gold in (("round1_bmain", "corpus_b.json", "gold_b.json"), ("round1_amain", "corpus_a.json", "gold_a.json")):
        committed = H.fixed_fixtures(FIXES / sub, corpus=corpus)
        H.gold_path_overlay(FIXES / sub, gold_file=gold)
        for fid, f in committed.items():
            assert H.canonical(f) == H.canonical(fixed[fid][0]), fid
    assert len(fixed) == 20

    tmp = CFB.export_staging(tempfile.mkdtemp(prefix="g4-independence-"))
    corpus_dir = tmp / "experiments/G-ROUTE4-candidate/corpus"
    sys.path.insert(0, str(corpus_dir))
    sys.path.insert(0, str(tmp / "tools"))
    import check_corpus as CC
    sealed_docs = [json.loads((corpus_dir / "staging" / f"{c}.json").read_text(encoding="utf-8")) for c in CFB.CLASSES]
    sealed_f = {**BFB.load("corpus_a.json", "fixtures"), **BFB.load("corpus_b.json", "fixtures"),
                **BFB.load("reserve_corpus_a.json", "fixtures"), **BFB.load("reserve_corpus_b.json", "fixtures")}
    sealed_g = {**BFB.load("gold_a.json", "items"), **BFB.load("gold_b.json", "items"),
                **BFB.load("reserve_gold_a.json", "items"), **BFB.load("reserve_gold_b.json", "items")}
    sealed_l = BFB.load("authoring_ledger.json", "items")
    mismatch = [x["fixture_id"] for doc in sealed_docs for x in doc["fixtures"] if x != sealed_f[x["fixture_id"]]]
    mismatch += [x["fixture_id"] for doc in sealed_docs for x in doc["gold"]
                 if {k: x[k] for k in ("expected", "fixture_id", "rationale", "reference_output")} != sealed_g[x["fixture_id"]]]
    mismatch += [x["fixture_id"] for doc in sealed_docs for x in doc["design"] if x != sealed_l[x["fixture_id"]]]
    if mismatch or sum(len(d["fixtures"]) for d in sealed_docs) != 584:
        raise SystemExit(f"staging corpus differs from the seal: {mismatch[:5]}")

    final_docs = copy.deepcopy(sealed_docs)
    for doc in final_docs:
        for key, idx in (("fixtures", 0), ("gold", 1), ("design", 2)):
            doc[key] = [fixed[x["fixture_id"]][idx] if x["fixture_id"] in fixed else x for x in doc[key]]

    # declared fix texts (exactly as check_fixes_amain.py): keyed by claim text, relation and prefix-stripped body
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
    # the proof: with the exemption disabled, the extra problems are exactly the declared research source texts
    flagged = sorted(p for p in raw_problems if p not in problems)
    declared_fids = sorted({s.split()[0] for s in declared_sources})
    flagged_fids = sorted({p.split(":")[0] for p in flagged})
    exemption_proof = {
        "declared_fix_sources": sorted(declared_sources),
        "problems_with_exemption_disabled": len(flagged),
        "flagged": flagged,
        "flagged_exactly_the_declared_research_fixtures": flagged_fids == declared_fids and len(flagged) == len(declared_sources)}
    if not exemption_proof["flagged_exactly_the_declared_research_fixtures"]:
        problems.append("the declared fix-text exemption covers something other than the 12 declared source texts")
    # the fixed constructs, asserted exactly as check_fixes_amain.py does
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
    if base_problems:
        problems.append(f"sealed baseline does not reproduce 0 problems: {base_problems[:3]}")

    # the tool's trigram sets, reconstructed and asserted equal to its reported maxima
    sets_final, sets_base = trigram_sets(CC, final_docs), trigram_sets(CC, sealed_docs)
    for tc, rep in final["trigram"].items():
        v, a, b = class_max(sets_final[tc])
        assert round(v, 4) == rep["max_jaccard"] and {a, b} == set(rep["max_pair"]), (tc, v, a, b, rep)
        assert len(sets_final[tc]["boilerplate"]) == rep["boilerplate_trigrams"] and sets_final[tc]["pool"] == rep["pool"]
    for tc, rep in base["trigram"].items():
        v, a, b = class_max(sets_base[tc])
        assert round(v, 4) == rep["max_jaccard"] and {a, b} == set(rep["max_pair"]), (tc, v, rep)

    # N8: maximum same-family A′–B′ Jaccard per cell (main corpora: the members that enter Phase A′ and Phase B′)
    n8 = {}
    for tc in sorted(final["trigram"]):
        sets = sets_final[tc]
        main = [(fid, s, slot_of(CC, fid)) for fid, src, s in sets["rows"] if src == "G4" and slot_of(CC, fid)[1] == "main"]
        for risk in ("R1", "R2", "R3", "R4"):
            best = (0.0, "", "", "")
            pairs = 0
            for fa, sa, (pa, _, ra, fam_a) in main:
                if pa != "A" or ra != risk:
                    continue
                for fb, sb, (pb, _, rb, fam_b) in main:
                    if pb == "B" and rb == risk and fam_b == fam_a:
                        pairs += 1
                        v = jac(sa, sb)
                        if v > best[0] or not best[1]:
                            best = (v, fa, fb, fam_a)
            n8[f"{tc}|{risk}"] = ({"same_family_pairs": pairs, "max_jaccard": round(best[0], 4),
                                   "max_pair": list(best[1:3]), "family": best[3]} if pairs else
                                  {"same_family_pairs": 0, "max_jaccard": None, "max_pair": None, "family": None})

    # effects of the 20 fixes: each fixed fixture's own maximum overlap, sealed text against final text
    fix_effects = {}
    for fid in sorted(fixed):
        tc = fixed[fid][0]["task_class"]
        b, f = fixture_max(sets_base[tc], fid), fixture_max(sets_final[tc], fid)
        fix_effects[fid] = {"round": records[fid]["round_label"], "task_class": tc, "defect": records[fid]["defect"],
                            "max_jaccard_sealed_text": {"value": b[0], "partner": b[1]},
                            "max_jaccard_fixed_text": {"value": f[0], "partner": f[1]},
                            "sealed_sha256": records[fid]["sealed_sha256"], "fixed_sha256": records[fid]["fixed_sha256"]}
    measures = ["n1_duplicates", "fine_signature_clashes", "canonical_signature_clashes"]
    delta = {m: {"sealed": base[m], "final": final[m]} for m in measures}
    delta["o3_entities"] = {k: {"sealed": base["o3_entities"][k], "final": final["o3_entities"][k]}
                            for k in ("g4_entities", "shared")}
    delta["o3_identifier_gate"] = {k: {"sealed": base["o3_identifier_gate"][k], "final": final["o3_identifier_gate"][k]}
                                   for k in ("g4_identifiers", "shared")}
    delta["o6"] = {"sealed": base["o6"], "final": final["o6"]}
    for key in ("trigram", "trigram_task_relevant"):
        delta[key] = {tc: {k: {"sealed": base[key][tc][k], "final": final[key][tc][k]}
                           for k in ("boilerplate_trigrams", "max_jaccard", "max_pair", "pairs_over_bound")}
                      for tc in final[key]}

    # O5: boilerplate trigrams occurring in a frozen family template, with pool frequency
    bp = json.loads((CAND / "blueprint/BLUEPRINT.json").read_text(encoding="utf-8"))
    o5 = {}
    for tc in sorted(final["trigram"]):
        sets = sets_final[tc]
        templates = bp["classes"][tc]["family_template_text"]
        in_template = [{"family": fam, "trigram": " ".join(tg), "pool_frequency": sets["freq"][tg]}
                       for fam, text in sorted(templates.items()) for tg in sorted(CC.I._trigrams(text) & sets["boilerplate"])]
        o5[tc] = {"frozen_family_template_texts": templates,
                  "boilerplate_trigrams_in_family_templates": in_template,
                  "single_family_boilerplate_trigrams": final["trigram"][tc]["o5_single_family_boilerplate"]}
        if in_template or final["trigram"][tc]["o5_single_family_boilerplate"]:
            problems.append(f"O5: {tc} has boilerplate in a family template or single-family boilerplate")

    # bindings
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
    g3 = {p: {"head_lf_sha256": lf_sha((ROOT / p).read_bytes()), "staging_lf_sha256": lf_sha(git_blob(CFB.STAGING_COMMIT, p))}
          for p in G3_FILES}
    if any(v["head_lf_sha256"] != v["staging_lf_sha256"] for v in g3.values()):
        problems.append("a G-ROUTE3 file differs between this checkout and the staging checkpoint")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()

    report = {
        "schema_version": "g-route4.independence-report.v1",
        "design_step": "order of work 3.6: the contamination and independence reports, over the final corpus",
        "valid": not problems,
        "problems": problems,
        "binding": {
            "seal_commit": SEAL, "blueprint_commit": BLUEPRINT, "audit_sample_commit": AUDIT_SAMPLE_COMMIT,
            "generated_at_parent_commit": head,
            "sealed_files_lf_sha256": {n: H.lf_sha256(H.SEALED / n) for n in SEALED_FILES},
            "seal_manifest_lf_sha256": H.lf_sha256(H.SEALED / "SEAL_MANIFEST.json"),
            "fixes": {"B′ round 1": {"commit": FIX_COMMITS["B′ round 1"], "fixtures": sorted(f for f, r in records.items() if r["round_label"] == "B′ round 1"),
                                     "fix_record_lf_sha256": H.lf_sha256(FIXES / "round1_bmain/FIX_RECORD.json")},
                      "A′ round 1": {"commit": FIX_COMMITS["A′ round 1"], "fixtures": sorted(f for f, r in records.items() if r["round_label"] == "A′ round 1"),
                                     "fix_record_lf_sha256": H.lf_sha256(FIXES / "round1_amain/FIX_RECORD.json")}},
            "replacements": 0,
            "final_pool": final_pool,
            "tool": {"name": "check_corpus.py (authoring-stage independence tool, blueprint §4)",
                     "source_commit": CFB.STAGING_COMMIT,
                     "check_corpus_lf_sha256": lf_sha(git_blob(CFB.STAGING_COMMIT, "experiments/G-ROUTE4-candidate/corpus/check_corpus.py")),
                     "frozen_g3_detector": {"path": "tools/g_route3_independence.py",
                                            "lf_sha256": final["o3_identifier_gate"]["frozen_checker_sha256"]},
                     "o3_identifier_gate_pattern_sha256": final["o3_identifier_gate"]["pattern_sha256"],
                     "overlay_scripts_lf_sha256": {p: H.lf_sha256(FIXES / p) for p in
                                                   ("build_fixes.py", "build_fixes_amain.py", "check_fixes.py", "check_fixes_amain.py")},
                     "this_script_lf_sha256": H.lf_sha256(Path(__file__)),
                     "note": "the stage-4 forked module g_route4_independence does not exist yet (implementation is "
                             "order-of-work step 4); N9, its byte-identity test, is verified at IR"},
            "g_route3_files_unchanged": g3,
        },
        "bounds": {"max_trigram_jaccard": CC.I.MAX_CROSS_CORPUS_TRIGRAM_JACCARD, "boilerplate_share": CC.I.BOILERPLATE_SHARE,
                   "shared_entities_identifiers_values_lineages_actions": 0, "identical_canonical_gold": 0,
                   "fine_signature_repeats_A_B_same_cell": 0, "conversation_gold_position_spread_per_cell": 1},
        "scope": {
            "pool": "one pool per class: all 584 G-ROUTE4 fixtures (A′ and B′, main and reserve) with the 20 fixes "
                    "overlaid (N7: a fixed text replaces its old text; boilerplate recomputed over the whole pool), plus "
                    "G-ROUTE3's A and B fixtures of the class; G-ROUTE3 pairs among themselves are not compared",
            "o3": final["o3_entities"]["scope"] + "; lowercase vocabulary per class pool only",
            "o4_conversation": "no signature (conversation relies on the family rules, the answer-position balance, "
                               "the no-identical-gold rule and the corpus review)",
            "fine_signature": "research and extraction, A′ against B′ within a cell; planning and synthesis exempt "
                              "(declared loosening); conversation no signature",
            "o6": final["o6"]["pool"],
            "o6_fields": {"ordinary_conversation": "every input field except the message",
                          "structured_extraction": "gold values of free-text (non-enum) string fields",
                          "reflective_planning": "allowed action names and the objective",
                          "grounded_research_synthesis": "source lineages"},
            "o6_normalization": "canonical_value, casefold, strip; closed-vocabulary sets and structural-id fields excluded",
        },
        "result_final": final,
        "sealed_baseline": {"problems": len(base_problems), "passed": not base_problems,
                            "note": "the sealed corpus alone (no fixes), same tool and pool: the pre-existing structure"},
        "fix_text_exemption_proof": exemption_proof,
        "sealed_vs_final": delta,
        "fix_effects": fix_effects,
        "n8_same_family_a_b_max_jaccard_per_cell": n8,
        "o5": o5,
    }
    OUT.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    for p in problems:
        print("FAIL", p)
    print(f"independence report: {'VALID' if not problems else 'INVALID'}; {len(problems)} problems; "
          f"exemption proof flags {len(flagged)}; N8 cells {len(n8)}")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
