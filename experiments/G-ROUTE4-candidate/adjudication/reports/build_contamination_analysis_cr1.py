"""Write CONTAMINATION_ANALYSIS_CR1.md: the successor contamination and independence analysis for the final corpus
after external corpus review round 1 (26 recorded fixes). Generated from INDEPENDENCE_REPORT_CR1.json, the two closure
addenda, the remediation closure and the round-1 dispositions; CONTAMINATION_ANALYSIS.md is not modified.

    python -B build_contamination_analysis_cr1.py
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ADJ = HERE.parent
CAND = ADJ.parent
sys.path.insert(0, str(ADJ))
import g4_adjudicate as H  # noqa: E402

SHORT = {"grounded_research_synthesis": "Research", "hierarchical_semantic_synthesis": "Synthesis",
         "ordinary_conversation": "Conversation", "reflective_planning": "Planning", "structured_extraction": "Extraction"}


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def main():
    ind_p, aa_p, ba_p = CAND / "INDEPENDENCE_REPORT_CR1.json", ADJ / "A_MAIN_CLOSURE_ADDENDUM_CR1.json", ADJ / "B_MAIN_CLOSURE_ADDENDUM_CR1.json"
    r, aa, ba = load(ind_p), load(aa_p), load(ba_p)
    a, b = load(ADJ / "A_MAIN_CLOSURE.json"), load(ADJ / "B_MAIN_CLOSURE.json")
    rem = load(CAND / "corpus_review/round1/REMEDIATION_CLOSURE_R1.json")
    disp = load(CAND / "corpus_review/round1/OPERATOR_DISPOSITIONS_R1.json")["dispositions"]
    f, rep = r["result_final"], r["reproduction_of_frozen_values"]
    assert r["valid"] and rep["all_reproduced"] and r["bounds_met"]
    assert aa["final_corpus"]["a_main"]["model_facing_sha256"] == r["binding"]["final_pool"]["corpus_a.json"]["canonical_sha256"]
    assert ba["final_corpus"]["b_main"]["model_facing_sha256"] == r["binding"]["final_pool"]["corpus_b.json"]["canonical_sha256"]
    classes = sorted(f["trigram"])
    eff = r["fix_effects"]
    L = []
    w = L.append
    w("# G-ROUTE4 contamination and independence analysis: final corpus after corpus review round 1")
    w("")
    w("Successor to `CONTAMINATION_ANALYSIS.md` (not modified; it remains the record of the 20-fix corpus that the external "
      "corpus review examined). The **final corpus** is the seal with all **26** recorded fixes overlaid: B′ round 1 (14), A′ "
      "round 1 (6) and the review-driven cr1 fixes (6). No fixture was replaced and no reserve was drawn.")
    w("")
    w(f"Values: `INDEPENDENCE_REPORT_CR1.json` (sha256 `{H.lf_sha256(ind_p)}`). Adjudication: `adjudication/A_MAIN_CLOSURE_ADDENDUM_CR1.json` "
      f"(`{H.lf_sha256(aa_p)[:16]}…`) and `adjudication/B_MAIN_CLOSURE_ADDENDUM_CR1.json` (`{H.lf_sha256(ba_p)[:16]}…`).")
    w("")
    w(f"**Result: every frozen independence measure passes on the final corpus, with 0 problems, and all {rep['compared']} "
      "class-level values recorded in the frozen `INDEPENDENCE_REPORT.json` are reproduced exactly.** The re-check uses the "
      "pinned authoring-stage tool that produced those values; the re-check with the stage-4 forked module is a freeze "
      "condition (B7) and has not been run, because that module does not exist yet.")
    w("")
    w("## Binding")
    w("")
    w("| Item | Value |")
    w("|---|---|")
    for label, fx in r["binding"]["fixes"].items():
        w(f"| Fixes, {label} | commit `{fx['commit'][:12]}`; {len(fx['fixtures'])} fixtures |")
    w(f"| Final A′ main (80), model-facing / gold | `{aa['final_corpus']['a_main']['model_facing_sha256']}` / `{aa['final_corpus']['a_main']['gold_sha256']}` |")
    w(f"| Final B′ main (305), model-facing / gold | `{ba['final_corpus']['b_main']['model_facing_sha256']}` / `{ba['final_corpus']['b_main']['gold_sha256']}` |")
    w(f"| Tool | `check_corpus.py` at staging `{r['binding']['tool']['source_commit'][:7]}` (sha256 `{r['binding']['tool']['check_corpus_lf_sha256'][:16]}…`) |")
    w(f"| Generated at | parent commit `{r['binding']['generated_at_parent_commit']}` |")
    w("")
    w("## Frozen measures: frozen report against the final corpus")
    w("")
    w("| Measure | Criterion | Frozen report (20 fixes) | Final (26 fixes) |")
    w("|---|---|---|---|")
    mx = max(x["max_jaccard"] for x in f["trigram"].values())
    w(f"| Trigram Jaccard, every pair | ≤ 0.2 | 0 pairs over | {sum(x['pairs_over_bound'] for x in f['trigram'].values())} pairs over (max {mx}) |")
    for key, label in (("o3_entities.shared", "Shared named entities (O3)"), ("o3_identifier_gate.shared", "Shared identifiers (O3)"),
                       ("n1_duplicates", "Identical canonical gold (N1)"), ("fine_signature_clashes", "Fine signature repeated A′/B′ in a cell"),
                       ("canonical_signature_clashes", "Canonical research signature repeated")):
        v = rep["values"][key]
        w(f"| {label} | 0 | {v['frozen']} | {v['final']} |")
    w(f"| Shared exact values (O6) | 0 | {rep['values']['o6']['frozen']['collisions']} | {f['o6']['collisions']} |")
    w(f"| O5 single-family boilerplate | 0 | 0 | {sum(x['single_family_boilerplate_trigrams'] for x in r['o5'].values())} |")
    w(f"| Conversation near-miss construct | all | 142 | {f['conversation']['near_miss_compliant']} of 142 |")
    w("")
    w("## Overlap by class (final corpus)")
    w("")
    w("| Class | Pool | Boilerplate trigrams | Max Jaccard | Max pair | Pairs over 0.20 |")
    w("|---|---|---|---|---|---|")
    for tc in classes:
        t = f["trigram"][tc]
        w(f"| {SHORT[tc]} | {t['pool']} | {t['boilerplate_trigrams']} | {t['max_jaccard']} | {t['max_pair'][0]} / {t['max_pair'][1]} | {t['pairs_over_bound']} |")
    w("")
    w("## N8: maximum same-family A′–B′ overlap per cell (main corpora)")
    w("")
    w("| Class | R1 | R2 | R3 | R4 |")
    w("|---|---|---|---|---|")
    for tc in classes:
        cells = []
        for risk in ("R1", "R2", "R3", "R4"):
            n = r["n8_same_family_a_b_max_jaccard_per_cell"][f"{tc}|{risk}"]
            cells.append("no same-family pair" if not n["same_family_pairs"] else
                         f"{n['max_jaccard']} ({n['family']}, {n['same_family_pairs']} pair{'s' if n['same_family_pairs'] > 1 else ''})")
        w(f"| {SHORT[tc]} | " + " | ".join(cells) + " |")
    w("")
    w("## Effects of the six review-driven fixes (cr1)")
    w("")
    w("| Fixed fixture | Finding | Max Jaccard, sealed text | Max Jaccard, fixed text |")
    w("|---|---|---|---|")
    fr = load(ADJ / "fixes/cr1_amain/FIX_RECORD.json")["fixes"] + load(ADJ / "fixes/cr1_bmain/FIX_RECORD.json")["fixes"]
    finding = {x["fixture_id"]: x["finding"] for x in fr}
    for fid, e in eff.items():
        if e["round"] == "cr1":
            w(f"| {fid} | {finding[fid]} | {e['max_jaccard_sealed_text']['value']} | {e['max_jaccard_fixed_text']['value']} |")
    w("")
    prev = load(CAND / "INDEPENDENCE_REPORT.json")["fix_effects"]
    moved = {k: (prev[k]["max_jaccard_fixed_text"]["value"], eff[k]["max_jaccard_fixed_text"]["value"], eff[k]["max_jaccard_fixed_text"]["partner"])
             for k in prev if prev[k]["max_jaccard_fixed_text"] != eff[k]["max_jaccard_fixed_text"]}
    w(f"Of the 20 earlier fixed fixtures, {len(moved)} now have a different maximum overlap, all synthesis fixtures sharing "
      "relabelled role names with the new SY1 fixes: " + "; ".join(f"{k} {v[0]} → {v[1]} (with {v[2]})" for k, v in sorted(moved.items()))
      + f". The largest is {max(v[1] for v in moved.values()) if moved else '—'}, under the 0.20 bound; the other "
      f"{20 - len(moved)} are unchanged. The fix-text exemption still covers exactly the 12 declared research source texts; "
      "the cr1 fixes need none.")
    w("")
    w("## Exposure and contamination")
    w("")
    ca, cb = rem["contact"]["g4adj-amain-cr1-20260930T001531Z"], rem["contact"]["g4adj-bmain-cr1-20260930T001608Z"]
    w(f"**Adjudication exposure (declared).** In addition to the sessions recorded in `CONTAMINATION_ANALYSIS.md` (259 A′ and "
      f"507 B′), the review-driven fixes were re-adjudicated in {ca['sessions']} A′ and {cb['sessions']} B′ remediation sessions "
      f"(`claude-opus-5-5`, O2 `7691126e…`; each slot contacted once; 0 retries, 0 in doubt). Only model-facing text was sent; "
      "no reserve fixture was sent. The tested tiers are pinned local models and were not contacted.")
    w("")
    sa, sb = aa["descriptive_subsets_step_12_never_gating"], ba["descriptive_subsets_step_12_never_gating"]
    w(f"**Residual filter (declared, step 12).** Descriptive subsets, never gating: A′ {sa['untouched']['count']} untouched and "
      f"{sa['disputed_but_kept_unchanged']['count']} disputed-but-kept-unchanged; B′ {sb['untouched']['count']} and "
      f"{sb['disputed_but_kept_unchanged']['count']}. Every fixed fixture is flagged (A′ {len(aa['flagged']['fixed'])}, B′ {len(ba['flagged']['fixed'])}).")
    w("")
    at, bt = aa["totals"], ba["totals"]
    w(f"**Operator decisions (declared, non-blind).** 'Gold right → keep': A′ {at['operator_keep']} "
      f"({at['kept_unchanged_by_operator_decision_gold_right']} unchanged, {at['fixed_then_kept_by_operator_decision_gold_right']} after "
      f"their fix); B′ {bt['kept_unchanged_by_operator_decision_gold_right'] + bt['fixed_then_kept_by_operator_decision_gold_right']} "
      f"({bt['kept_unchanged_by_operator_decision_gold_right']} unchanged, {bt['fixed_then_kept_by_operator_decision_gold_right']} after "
      "their fix). Retentions after a fix follow the operator's B1 step-7 ruling (`adjudication/errata/STEP7_RULING_ANNOTATION.md`).")
    w("")
    w("## Disclosures added by corpus review round 1")
    w("")
    for k in ("A4-PLAN-R3-04", "A4", "A5"):
        w(f"- **{k}:** {disp[k]['disclosure']}")
    w("- **Errata to `B_MAIN_CLOSURE.json`** (the closed file is unchanged): erratum 1 (the B′ disagreement causes: 91 fenced "
      "format-only, 16 fenced with a content disagreement, 24 content-only) and erratum 2 (15 reserves with known defects, not 14).")
    w("")
    w("## Latent defects")
    w("")
    w("- **Final main corpus:** no fixture carries a known unfixed defect. The four SY1 fixtures and the two conversation "
      "fixtures named by the review were fixed and re-adjudicated.")
    w("- **Unused reserves with known defects** (never drawn, never sent): " + "; ".join(
        f"{k}: {', '.join(v)}" for k, v in aa["latent_defects"]["in_unused_reserves_unfixed"].items()) + ".")
    w("")
    w("## Declared blind spots and conditions carried to the freeze")
    w("")
    w("- The blind spots in `CONTAMINATION_ANALYSIS.md` are unchanged (N3; the entity detector's sentence-initial and "
      "JSON-string-start cases, covered by O6; the declared exclusions; no conversation signature; planning and synthesis "
      "exempt; difficulty matching by judgment).")
    w("- **B7:** the final independence re-check with the forked module must reproduce these values before the freeze.")
    w("- **B8:** the B′ fix-round per-cell counts are bound in `B_MAIN_CLOSURE_ADDENDUM_CR1.json` for the freeze records.")
    w("")
    (CAND / "CONTAMINATION_ANALYSIS_CR1.md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote CONTAMINATION_ANALYSIS_CR1.md: {len(L)} lines")


if __name__ == "__main__":
    main()
