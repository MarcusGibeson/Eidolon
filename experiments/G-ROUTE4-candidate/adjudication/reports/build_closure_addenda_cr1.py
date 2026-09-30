"""Closure addenda after external corpus review round 1: successors to A_MAIN_CLOSURE.json and B_MAIN_CLOSURE.json.

The closed records are not edited; each addendum binds its closure (and, for B′, both errata) by digest and restates
the totals, subsets, per-cell records, final-corpus membership and digests for the final corpus with all 26 recorded
fixes. Reads only committed records.

    python -B build_closure_addenda_cr1.py    # writes adjudication/A_MAIN_CLOSURE_ADDENDUM_CR1.json and B_…
"""

import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ADJ = HERE.parent
CAND = ADJ.parent
sys.path.insert(0, str(ADJ))
import g4_adjudicate as H  # noqa: E402

RA, RB = "g4adj-amain-cr1-20260930T001531Z", "g4adj-bmain-cr1-20260930T001608Z"
B_RUN, B_FIX = "g4adj-bmain-20260929T155837Z", "g4adj-bmain-fix1-20260929T171651Z"


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def overlay(corpus, gold_file, subs):
    fixtures = {f["fixture_id"]: f for f in load(H.SEALED / corpus)["fixtures"]}
    gold = {g["fixture_id"]: g for g in load(H.SEALED / gold_file)["items"]}
    for sub in subs:
        fixtures.update(H.fixed_fixtures(ADJ / "fixes" / sub, corpus=corpus))
        g = H.gold_path_overlay(ADJ / "fixes" / sub, gold_file=gold_file)
        gold.update({k: v for k, v in g.items() if k in H.fixed_fixtures(ADJ / "fixes" / sub, corpus=corpus)})
    return fixtures, gold


def digest(items):
    return H.sha256(H.canonical(sorted(items.values(), key=lambda x: x["fixture_id"])))


def cell(fid):
    return fid.rsplit("-", 1)[0]


def per_cell_slots(*score_files):
    out = collections.defaultdict(lambda: {"slots": 0, "disagreeing_slots": 0})
    for p in score_files:
        if Path(p).exists():
            for r in load(p)["slots"]:
                out[cell(r["fixture_id"])]["slots"] += 1
                out[cell(r["fixture_id"])]["disagreeing_slots"] += r["agree"] is False
    return dict(sorted(out.items()))


def main():
    ind = load(CAND / "INDEPENDENCE_REPORT_CR1.json")
    rem = load(CAND / "corpus_review/round1/REMEDIATION_CLOSURE_R1.json")
    disp = load(CAND / "corpus_review/round1/OPERATOR_DISPOSITIONS_R1.json")["dispositions"]
    assert ind["valid"] and ind["reproduction_of_frozen_values"]["all_reproduced"]
    dec_ra, dec_rb = load(ADJ / "runs" / RA / "decisions.json"), load(ADJ / "runs" / RB / "decisions.json")
    op_rb = load(ADJ / "runs" / RB / "OPERATOR_DECISIONS.json")

    # ---------------- A′
    a_clo_path = ADJ / "A_MAIN_CLOSURE.json"
    a = load(a_clo_path)
    cr1_a = sorted(dec_ra)
    assert cr1_a == ["A4-SYNTH-R1-01"] and all(v["decision"] == "keep" for v in dec_ra.values())
    kept_op = [f for f in a["decisions"]["batch_operator_gold_right_keep"] if f not in cr1_a]
    fixed_a = sorted(a["flagged"]["fixed"] + cr1_a)
    kept_direct = a["decisions"]["batch_keep"]
    assert not set(cr1_a) & set(kept_direct) and set(cr1_a) <= set(a["decisions"]["batch_operator_gold_right_keep"])
    fa, ga = overlay("corpus_a.json", "gold_a.json", ["round1_amain", "cr1_amain"])
    assert digest(fa) == ind["binding"]["final_pool"]["corpus_a.json"]["canonical_sha256"]
    a_totals = {"a_main_fixtures": 80, "kept_directly_by_the_frozen_rule_all_three_agree": len(kept_direct),
                "kept_unchanged_by_operator_decision_gold_right": len(kept_op), "fixed_then_kept": len(fixed_a),
                "fixed_then_kept_by_re_adjudication_all_three_agree": len(a["decisions"]["fix_round_keep_all_three_agree"]) + 1,
                "fixed_then_kept_by_operator_decision_gold_right": len(a["decisions"]["fix_round_operator_gold_right_keep"]),
                "replaced": 0, "unresolved": 0}
    a_totals["automatic_keep"] = a_totals["kept_directly_by_the_frozen_rule_all_three_agree"] + \
        a_totals["fixed_then_kept_by_re_adjudication_all_three_agree"]
    a_totals["operator_keep"] = a_totals["kept_unchanged_by_operator_decision_gold_right"] + \
        a_totals["fixed_then_kept_by_operator_decision_gold_right"]
    a_totals["final_kept"] = len(kept_direct) + len(kept_op) + len(fixed_a)
    assert a_totals["final_kept"] == 80 == a_totals["automatic_keep"] + a_totals["operator_keep"]
    a_cells = {k: dict(v) for k, v in a["per_cell"].items()}
    for f in cr1_a:
        a_cells[cell(f)]["fixed"] += 1
        a_cells[cell(f)]["kept_by_operator"] -= 1
    for k, v in per_cell_slots(ADJ / "runs" / RA / "scores_phase1.json").items():
        a_cells[k].update(remediation_slots=v["slots"], remediation_disagreeing_slots=v["disagreeing_slots"])
    subsets_a = a["descriptive_subsets_step_12_never_gating"]
    a_add = {
        "schema_version": "g-route4.closure-addendum.v1", "addendum_to": {"file": "adjudication/A_MAIN_CLOSURE.json",
                                                                          "lf_sha256": H.lf_sha256(a_clo_path), "unchanged": True},
        "cause": "external corpus review round 1, finding A1: A4-SYNTH-R1-01 (kept unchanged by operator decision in the "
                 "batch) received its one fix (cr1) and was re-adjudicated from scratch: 3 of 3 agree, kept",
        "remediation_run": {"run_id": RA, "contact": rem["contact"][RA]},
        "totals": a_totals,
        "flagged": {"fixed": fixed_a, "replaced": []},
        "descriptive_subsets_step_12_never_gating": {
            "untouched": subsets_a["untouched"],
            "disputed_but_kept_unchanged": {"count": subsets_a["disputed_but_kept_unchanged"]["count"] - len(cr1_a),
                                            "fixtures": [f for f in subsets_a["disputed_but_kept_unchanged"]["fixtures"] if f not in cr1_a]}},
        "per_cell": a_cells,
        "final_corpus": {"a_main": {"fixtures": sorted(fa), "fixed": fixed_a, "fix_rounds": ["round1_amain", "cr1_amain"],
                                    "model_facing_sha256": digest(fa), "gold_sha256": digest(ga)}},
        "latent_defects": {"in_the_final_main_corpus_unfixed": {}, "in_unused_reserves_unfixed": a["latent_defects"]["in_unused_reserves_unfixed"]},
        "disclosures": {"A4-PLAN-R3-04": disp["A4-PLAN-R3-04"]["disclosure"], "A4 (research P4 coverage)": disp["A4"]["disclosure"],
                        "A5 (synthesis constant conclusions)": disp["A5"]["disclosure"]},
    }
    (ADJ / "A_MAIN_CLOSURE_ADDENDUM_CR1.json").write_text(json.dumps(a_add, indent=1, ensure_ascii=False) + "\n",
                                                          encoding="utf-8", newline="\n")

    # ---------------- B′
    b_clo_path = ADJ / "B_MAIN_CLOSURE.json"
    b = load(b_clo_path)
    dec_b = load(ADJ / "runs" / B_RUN / "decisions.json")
    cr1_b = sorted(dec_rb)
    assert all(dec_b[f]["decision"] == "keep" for f in cr1_b), "every cr1 B′ fixture was kept directly in the batch"
    readj = sorted(f for f, v in dec_rb.items() if v["decision"] == "keep")
    opk = sorted(d["fixture_id"] for d in op_rb["decisions"] if d["outcome"].startswith("gold right"))
    assert sorted(readj + opk) == cr1_b
    fixed_b = sorted(b["flagged"]["fixed"] + cr1_b)
    t = b["totals"]
    b_totals = {"b_main_fixtures": 305, "kept_directly_by_the_frozen_rule": t["kept_directly_by_the_frozen_rule"] - len(cr1_b),
                "kept_unchanged_by_operator_decision_gold_right": t["kept_unchanged_by_operator_decision_gold_right"],
                "fixed_then_kept": len(fixed_b),
                "fixed_then_kept_by_re_adjudication": t["fixed_then_kept_by_re_adjudication"] + len(readj),
                "fixed_then_kept_by_operator_decision_gold_right": t["fixed_then_kept_by_operator_decision_gold_right"] + len(opk),
                "replaced": 0, "unresolved": 0}
    b_totals["final_kept"] = b_totals["kept_directly_by_the_frozen_rule"] + \
        b_totals["kept_unchanged_by_operator_decision_gold_right"] + b_totals["fixed_then_kept"]
    assert b_totals["final_kept"] == 305
    fb, gb = overlay("corpus_b.json", "gold_b.json", ["round1_bmain", "cr1_bmain"])
    assert digest(fb) == ind["binding"]["final_pool"]["corpus_b.json"]["canonical_sha256"]
    sb = b["descriptive_subsets_step_12_never_gating"]
    sample = set(H.audit_sample())
    b_cells = {k: dict(v) for k, v in b["per_cell"].items()}
    for f in cr1_b:
        b_cells[cell(f)]["fixed"] += 1
    fix_round_cells = per_cell_slots(ADJ / "runs" / B_FIX / "scores_phase1.json", ADJ / "runs" / B_FIX / "scores_phase2.json")
    cr1_cells = per_cell_slots(ADJ / "runs" / RB / "scores_phase1.json", ADJ / "runs" / RB / "scores_phase2.json")
    b_add = {
        "schema_version": "g-route4.closure-addendum.v1",
        "addendum_to": {"file": "adjudication/B_MAIN_CLOSURE.json", "lf_sha256": H.lf_sha256(b_clo_path), "unchanged": True},
        "errata_bound": {n: H.lf_sha256(ADJ / "errata" / n) for n in ("B_MAIN_CLOSURE_ERRATUM_1.json", "B_MAIN_CLOSURE_ERRATUM_2.json")},
        "cause": "external corpus review round 1, findings A1 (B4-SYNTH-R1-02, B4-SYNTH-R2-15, B4-SYNTH-R3-08), A2 "
                 "(B4-CONV-R1-08) and A3 (B4-CONV-R2-28): each had been kept on the first adjudicator's agreement; each "
                 "received its one fix (cr1) and was re-adjudicated from scratch with the B′ procedure",
        "remediation_run": {"run_id": RB, "contact": rem["contact"][RB],
                            "kept_by_frozen_rule": readj, "kept_by_operator_under_B1_ruling": opk},
        "totals": b_totals,
        "flagged": {"fixed": fixed_b, "replaced": []},
        "audit_sample": {"cr1_fixtures_sampled": sorted(set(cr1_b) & sample),
                         "full_cell_consequence": "NOT TRIGGERED: no cr1 fixture is an audit-sample fixture"},
        "descriptive_subsets_step_12_never_gating": {
            "untouched": {"count": len([f for f in sb["untouched"]["fixtures"] if f not in cr1_b]),
                          "fixtures": [f for f in sb["untouched"]["fixtures"] if f not in cr1_b]},
            "disputed_but_kept_unchanged": {"count": len([f for f in sb["disputed_but_kept_unchanged"]["fixtures"] if f not in cr1_b]),
                                            "fixtures": [f for f in sb["disputed_but_kept_unchanged"]["fixtures"] if f not in cr1_b]}},
        "per_cell": b_cells,
        "per_cell_fix_rounds_B8": {"note": "freeze condition B8: the B′ fix-round per-cell counts, bound here",
                                   B_FIX: fix_round_cells, RB: cr1_cells},
        "final_corpus": {"b_main": {"fixtures": sorted(fb), "fixed": fixed_b, "fix_rounds": ["round1_bmain", "cr1_bmain"],
                                    "model_facing_sha256": digest(fb), "gold_sha256": digest(gb)}},
        "latent_defects": {"in_the_final_main_corpus_unfixed": {},
                           "in_unused_reserves_unfixed": a["latent_defects"]["in_unused_reserves_unfixed"]},
    }
    (ADJ / "B_MAIN_CLOSURE_ADDENDUM_CR1.json").write_text(json.dumps(b_add, indent=1, ensure_ascii=False) + "\n",
                                                          encoding="utf-8", newline="\n")
    print("A′", a_totals)
    print("B′", b_totals)
    print("subsets A′", {k: v["count"] for k, v in a_add["descriptive_subsets_step_12_never_gating"].items()},
          "B′", {k: v["count"] for k, v in b_add["descriptive_subsets_step_12_never_gating"].items()})
    print("B8 fix-round cells:", fix_round_cells, "| cr1:", cr1_cells)


if __name__ == "__main__":
    main()
