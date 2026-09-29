"""Write CONTAMINATION_ANALYSIS.md from INDEPENDENCE_REPORT.json and A_MAIN_CLOSURE.json (tables computed, prose fixed).

    python -B build_contamination_analysis.py   # writes experiments/G-ROUTE4-candidate/CONTAMINATION_ANALYSIS.md
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ADJ = HERE.parent
CAND = ADJ.parent
sys.path.insert(0, str(ADJ))
import g4_adjudicate as H  # noqa: E402

IND, CLO, OUT = CAND / "INDEPENDENCE_REPORT.json", ADJ / "A_MAIN_CLOSURE.json", CAND / "CONTAMINATION_ANALYSIS.md"
SHORT = {"grounded_research_synthesis": "Research", "hierarchical_semantic_synthesis": "Synthesis",
         "ordinary_conversation": "Conversation", "reflective_planning": "Planning", "structured_extraction": "Extraction"}


def main():
    r, c = json.loads(IND.read_text(encoding="utf-8")), json.loads(CLO.read_text(encoding="utf-8"))
    bc = json.loads((ADJ / "B_MAIN_CLOSURE.json").read_text(encoding="utf-8"))
    bindings = json.loads((CAND.parent / "G-ROUTE1-candidate/model_bindings.json").read_text(encoding="utf-8"))
    f, b, dv = r["result_final"], r["binding"], r["sealed_vs_final"]
    assert r["valid"] and not r["problems"] and r["sealed_baseline"]["passed"]
    assert b["final_pool"]["corpus_a.json"]["canonical_sha256"] != "" and \
        c["final_corpus"]["b_main"]["model_facing_sha256"] == b["final_pool"]["corpus_b.json"]["canonical_sha256"] and \
        c["final_corpus"]["a_main"]["model_facing_sha256"] == b["final_pool"]["corpus_a.json"]["canonical_sha256"]
    classes = sorted(f["trigram"])
    for key in ("trigram", "trigram_task_relevant"):
        for tc, x in dv[key].items():
            assert all(v["sealed"] == v["final"] for v in x.values()), (key, tc)
    for key in ("n1_duplicates", "fine_signature_clashes", "canonical_signature_clashes"):
        assert dv[key]["sealed"] == dv[key]["final"]
    for key in ("o3_entities", "o3_identifier_gate"):
        assert all(v["sealed"] == v["final"] for v in dv[key].values())
    assert dv["o6"]["sealed"] == dv["o6"]["final"]
    eff = r["fix_effects"]

    def moved(pred):
        d = [round(e["max_jaccard_fixed_text"]["value"] - e["max_jaccard_sealed_text"]["value"], 4)
             for fid, e in eff.items() if pred(fid, e)]
        return min(d), max(d), len(d)
    rs = moved(lambda fid, e: e["task_class"] == "grounded_research_synthesis")
    sy = moved(lambda fid, e: e["task_class"] == "hierarchical_semantic_synthesis")
    ex_ = moved(lambda fid, e: e["task_class"] == "structured_extraction")
    L = []
    w = L.append
    w("# G-ROUTE4 contamination and independence analysis")
    w("")
    w("Design order of work, step 3.6. Written over the **final corpus**: the sealed corpus (seal "
      f"`{b['seal_commit'][:7]}`) with the 20 authorized, recorded round-1 fixes overlaid (14 B′, 6 A′). No fixture was "
      "replaced, no reserve was drawn, and the seal is not modified. The measured values are in `INDEPENDENCE_REPORT.json` "
      f"(sha256 `{H.lf_sha256(IND)}`); the adjudication records are in `adjudication/A_MAIN_CLOSURE.json` (sha256 "
      f"`{H.lf_sha256(CLO)}`) and `adjudication/B_MAIN_CLOSURE.json`.")
    w("")
    w("**Result: every frozen independence measure passes on the final corpus, with 0 problems. The same tool gives 0 "
      "problems on the sealed corpus alone, and no class-level measure changes between the two.**")
    w("")
    w("## Binding")
    w("")
    w("| Item | Value |")
    w("|---|---|")
    w(f"| Seal commit | `{b['seal_commit']}` |")
    w(f"| Blueprint commit | `{b['blueprint_commit']}` |")
    w(f"| Audit sample commit | `{b['audit_sample_commit']}` |")
    for label, fx in b["fixes"].items():
        w(f"| Fixes, {label} | commit `{fx['commit']}`; {len(fx['fixtures'])} fixtures; FIX_RECORD sha256 `{fx['fix_record_lf_sha256'][:16]}…` |")
    w(f"| Final A′ main (80), model-facing / gold | `{c['final_corpus']['a_main']['model_facing_sha256']}` / `{c['final_corpus']['a_main']['gold_sha256']}` |")
    w(f"| Final B′ main (305), model-facing / gold | `{c['final_corpus']['b_main']['model_facing_sha256']}` / `{c['final_corpus']['b_main']['gold_sha256']}` |")
    w(f"| Reserves (80 A′, 119 B′), unchanged | `{b['final_pool']['reserve_corpus_a.json']['canonical_sha256'][:16]}…`, `{b['final_pool']['reserve_corpus_b.json']['canonical_sha256'][:16]}…` |")
    w(f"| Tool | `check_corpus.py` at staging `{b['tool']['source_commit'][:7]}` (sha256 `{b['tool']['check_corpus_lf_sha256'][:16]}…`), the authoring-stage independence tool of blueprint §4, which ran before the seal and at every fix re-check |")
    w(f"| Frozen G-ROUTE3 detector | `tools/g_route3_independence.py`, sha256 `{b['tool']['frozen_g3_detector']['lf_sha256'][:16]}…` (pinned; unchanged) |")
    w(f"| Generated at | parent commit `{b['generated_at_parent_commit']}` |")
    w("")
    w("The stage-4 forked module `g_route4_independence` does not exist yet (implementation is order-of-work step 4). "
      "Its byte-identity test (N9) is verified at the implementation review, and the step-8 final re-check before the "
      "freeze is still to come.")
    w("")
    w("## Frozen measures on the final corpus")
    w("")
    w("One pool per class: all 584 G-ROUTE4 fixtures (A′ and B′, main and reserve) plus G-ROUTE3's A and B fixtures of "
      "that class. A fixed text replaces its old text, and boilerplate is recomputed over the whole pool (N7).")
    w("")
    w("| Measure | Frozen criterion | Sealed | Final | Status |")
    w("|---|---|---|---|---|")
    over_s = sum(x["pairs_over_bound"]["sealed"] for x in dv["trigram"].values())
    over_f = sum(x["pairs_over_bound"]["final"] for x in dv["trigram"].values())
    mx = max(x["max_jaccard"]["final"] for x in dv["trigram"].values())
    w(f"| Word-trigram Jaccard, every pair (same-family included), after pinned-text and 25% boilerplate removal | ≤ {r['bounds']['max_trigram_jaccard']} | {over_s} pairs over | {over_f} pairs over (max {mx}) | pass |")
    w(f"| Named entities shared (O3; all classes, main and reserve, pairwise and against all G-ROUTE3) | 0 | {dv['o3_entities']['shared']['sealed']} | {dv['o3_entities']['shared']['final']} ({f['o3_entities']['g4_entities']} G-ROUTE4 entities; {f['o3_entities']['g3_entities_compared']} G-ROUTE3) | pass |")
    w(f"| Identifiers shared (O3 identifier gate) | 0 | {dv['o3_identifier_gate']['shared']['sealed']} | {dv['o3_identifier_gate']['shared']['final']} ({f['o3_identifier_gate']['g4_identifiers']} G-ROUTE4, {f['o3_identifier_gate']['g3_identifiers']} G-ROUTE3) | pass |")
    w(f"| Exact structured values shared (O6) | 0 | {dv['o6']['sealed']['collisions']} | {dv['o6']['final']['collisions']} ({sum(dv['o6']['final']['g4_values_compared_by_class'].values())} G-ROUTE4 values compared) | pass |")
    w(f"| Research source lineages repeated across fixtures | 0 | — | {f['research']['cross_fixture_lineage_repeats']} ({f['research']['unique_lineages']} lineages) | pass |")
    w(f"| Planning action names repeated | 0 | — | {f['planning']['repeated_action_names']} ({f['planning']['g4_action_names']} names) | pass |")
    w(f"| Identical canonical gold (N1) | 0 | {dv['n1_duplicates']['sealed']} | {dv['n1_duplicates']['final']} | pass |")
    w(f"| Fine gold signature repeated A′/B′ in a cell (research, extraction) | 0 | {dv['fine_signature_clashes']['sealed']} | {dv['fine_signature_clashes']['final']} | pass |")
    w(f"| Canonical research signature (decision clause normalized) repeated A′/B′ | 0 | {dv['canonical_signature_clashes']['sealed']} | {dv['canonical_signature_clashes']['final']} | pass |")
    w(f"| O5: boilerplate trigrams in a family template; single-family boilerplate | 0; 0 | — | {sum(len(x['boilerplate_trigrams_in_family_templates']) for x in r['o5'].values())}; {sum(x['single_family_boilerplate_trigrams'] for x in r['o5'].values())} | pass |")
    w(f"| Conversation: 4 options; gold positions within 1 per cell | all; ≤ 1 | — | {f['conversation']['fixtures_with_four_options']} of 142; balanced in every cell | pass |")
    w("")
    w("Conversation has **no gold-structure signature** (O4), as in G-ROUTE3. It relies on the family rules, the answer-"
      "position balance, the no-identical-gold rule and the corpus review. Planning and synthesis are exempt from the "
      "fine-signature rule (declared loosening). Research pattern labels and coarse signatures are shared between A′ and "
      "B′ within a cell by design (declared loosening; 8/8 needs four A′ fixtures per cell).")
    w("")
    w("## Overlap by class")
    w("")
    w("| Class | Pool | Boilerplate trigrams | Max Jaccard (full content) | Max pair | Max Jaccard (ledger-bound text) | Pairs over 0.20 |")
    w("|---|---|---|---|---|---|---|")
    for tc in classes:
        t, tr = f["trigram"][tc], f["trigram_task_relevant"][tc]
        w(f"| {SHORT[tc]} | {t['pool']} | {t['boilerplate_trigrams']} | {t['max_jaccard']} | {t['max_pair'][0]} / {t['max_pair'][1]} | {tr['max_jaccard']} | {t['pairs_over_bound']} |")
    w("")
    w("O6 compared values by class: " + "; ".join(f"{SHORT[k]} {v}" for k, v in sorted(f["o6"]["g4_values_compared_by_class"].items()))
      + ". Fields: " + "; ".join(f"{SHORT[k]}: {v}" for k, v in sorted(r["scope"]["o6_fields"].items())) + ".")
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
    w("Read from the tool's own trigram sets, which are reconstructed and asserted equal to its reported class maxima "
      "before use. The largest is research R2 (" +
      "{0} / {1}), well under 0.20.".format(*r["n8_same_family_a_b_max_jaccard_per_cell"]["grounded_research_synthesis|R2"]["max_pair"]))
    w("")
    w("## Sealed structure against the effects of the 20 fixes")
    w("")
    w("The pre-existing structure is the sealed corpus measured alone: 0 problems. After the fixes, every class-level "
      "value above (pool, boilerplate count, maximum and maximum pair, entity and identifier counts, O6 values, N1, both "
      "signature checks) is **identical** to the sealed value. The fixes moved only their own fixtures' overlap:")
    w("")
    w("| Fixed fixture | Round | Max Jaccard, sealed text | Max Jaccard, fixed text | Partner (fixed) |")
    w("|---|---|---|---|---|")
    for fid, e in r["fix_effects"].items():
        w(f"| {fid} | {e['round']} | {e['max_jaccard_sealed_text']['value']} | {e['max_jaccard_fixed_text']['value']} | {e['max_jaccard_fixed_text']['partner']} |")
    w("")
    w(f"- **Research ({rs[2]} fixtures, 12 source texts:** P6 'only' removed, the P4 anonymity support and the weekend "
      f"support rewritten): each fixture's maximum moved by {rs[0]:+.4f} to {rs[1]:+.4f}. The largest fixed-fixture value is "
      f"{max(e['max_jaccard_fixed_text']['value'] for e in eff.values())}, under the 0.20 bound.")
    w(f"- **Synthesis ({sy[2]} fixtures, SY1 role relabels):** maxima moved by {sy[0]:+.4f} to {sy[1]:+.4f}; the largest is "
      f"{max(e['max_jaccard_fixed_text']['value'] for e in eff.values() if e['task_class'] == 'hierarchical_semantic_synthesis')}.")
    w(f"- **Extraction ({ex_[2]} fixture, schema key rename):** moved by {ex_[0]:+.4f}.")
    ex = r["fix_text_exemption_proof"]
    w(f"- **Declared fix-text exemption.** The tool's authoring-paraphrase rule accepts only authored paraphrase texts, "
      f"so the 12 fixed research source texts are declared to it, keyed by claim, relation and body. Disabled, the tool "
      f"flags exactly those {ex['problems_with_exemption_disabled']} sources and nothing else. This rule is authoring "
      "conformance, not an independence measure; no independence measure is exempted.")
    w("")
    w("## Exposure and contamination")
    w("")
    tiers = ", ".join(f"{x['tier']} `{x['model']}`" for x in bindings["bindings"])
    w(f"**Tested models.** The tiers are the local {bindings['provider']} {bindings['provider_version']} models bound in "
      f"G-ROUTE1's `model_bindings.json` ({tiers}), each pinned by manifest and blob digest. No G-ROUTE4 execution code "
      "exists yet and no Phase A′ or Phase B′ call has been made. The authoring rule forbids pretesting any fixture on a "
      "pinned or Ollama model, and every adjudication journal records only `claude-opus-5-5`. Pinned weights cannot be "
      "changed by anything done here.")
    w("")
    w(f"**Adjudication exposure (declared).** The model-facing text of the 385 main fixtures (never gold) was sent to "
      f"Anthropic's Messages API for gold adjudication, `claude-opus-5-5` under the O2 amendment: "
      f"{c['provider']['messages_api_invocations']} A′ invocations and {bc['provider']['messages_api_sessions']} B′ "
      "sessions, every one logged in a hash-chained "
      "journal. The 199 reserve fixtures were never sent (checked against every journal). The corpus text has therefore "
      "left this machine; it cannot influence the pinned tiers.")
    w("")
    w("**Adjudicator filter (declared residual filter, step 12).** Only fixtures that a Claude adjudicator disputed, or "
      "that the audit sample caught, were scrutinized, so the corpus may drift toward items a frontier model can solve. "
      f"A′ descriptive subsets: {c['descriptive_subsets_step_12_never_gating']['untouched']['count']} untouched and "
      f"{c['descriptive_subsets_step_12_never_gating']['disputed_but_kept_unchanged']['count']} disputed-but-kept-unchanged "
      f"(B′: {bc['descriptive_subsets_step_12_never_gating']['untouched']['count']} and "
      f"{bc['descriptive_subsets_step_12_never_gating']['disputed_but_kept_unchanged']['count']}). These are descriptive "
      "and never gating. Every fixed fixture is flagged.")
    w("")
    bt, at = bc["totals"], c["totals"]
    w("**Authors and operator (declared, N5).** The authors were not blind to G-ROUTE3's outputs or the research "
      "diagnosis, and no item is derived from a G-ROUTE3 item. The operator who decided escalations was not blind "
      f"(declared). 'Gold right → keep' decisions: B′ {bt['kept_unchanged_by_operator_decision_gold_right'] + bt['fixed_then_kept_by_operator_decision_gold_right']} "
      f"({bt['kept_unchanged_by_operator_decision_gold_right']} unchanged, {bt['fixed_then_kept_by_operator_decision_gold_right']} after their fix), "
      f"A′ {at['operator_keep']} ({at['kept_unchanged_by_operator_decision_gold_right']} unchanged, "
      f"{at['fixed_then_kept_by_operator_decision_gold_right']} after their fix); 20 fixtures were fixed once. The corpus "
      "reviewers check difficulty parity per pattern (N5).")
    w("")
    w("**G-ROUTE3.** Read only, as the pool's comparison set. Its corpora, gold and frozen detector are byte-identical to "
      "the staging checkpoint (digests in the report). It is not rescored or reinterpreted; its identifier-branch defect is "
      "disclosed in `sealed/O3_IDENTIFIER_DECISION.md` and not applied backwards.")
    w("")
    w("## Declared blind spots")
    w("")
    w("- **Cross-experiment boilerplate (N3, restated).** A trigram present in all 16 of G-ROUTE3's fixtures of a class "
      "becomes boilerplate, and invisible to the cross-experiment check, once about 22 or more G-ROUTE4 fixtures copy it, "
      "at pools of about 150 (research 152, conversation 158); not \"a few\".")
    w("- **Entity detector:** sentence-initial words and values at the start of JSON strings; the O6 exact-value "
      "comparison covers the latter.")
    w("- **Declared exclusions:** closed-vocabulary values offered as allowed sets, and structural ids (`[A-Z][0-9]+`) "
      "in structural-id fields only.")
    w("- **Signatures:** conversation has none (O4); planning and synthesis are exempt.")
    w("- **Difficulty matching** is the authors' judgment, not measured on any model.")
    w("")
    w("## Warnings and latent issues carried to the corpus review")
    w("")
    for fid, why in c["latent_defects"]["in_the_final_main_corpus_unfixed"].items():
        w(f"- **{fid}** (final main corpus): {why}.")
    w("- **Unused reserves with known defects** (never drawn, never sent): " + "; ".join(
        f"{k}: {', '.join(v)}" for k, v in c["latent_defects"]["in_unused_reserves_unfixed"].items()) + ".")
    w("- Under step 10, a change driven by the corpus review goes through a fix (the fixture's one fix; the 20 fixed "
      "fixtures have used theirs) or a replacement, with re-adjudication, and the independence checks are re-run.")
    w("- Adjudication disagreements were dominated by code-fenced JSON; see the closure records.")
    w("")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT.name}: {len(L)} lines")


if __name__ == "__main__":
    main()
