"""Adversarial checks for the Planning authoring rules (and the O3 identifier gate), run over
Extraction + Synthesis + Planning together. Each case plants one defect and must be caught by its own message.

    python -B test_planning_corpus.py staging/extraction.json staging/synthesis.json staging/planning.json
"""

import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_corpus as C  # noqa: E402


def locate(staged, fid):
    for document in staged:
        fixtures = {row["fixture_id"]: row for row in document["fixtures"]}
        if fid in fixtures:
            gold = {row["fixture_id"]: row for row in document["gold"]}
            design = {row["fixture_id"]: row for row in document["design"]}
            return fixtures[fid], gold[fid], design[fid]
    raise KeyError(fid)


def first(staged, family, form=None):
    doc = next(d for d in staged if d["task_class"] == "reflective_planning")
    for row in doc["design"]:
        if row["family"] == family and (form is None or row["features"]["precedence_form"] == form):
            return locate(staged, row["fixture_id"])
    raise KeyError(family)


def set_gold(g, fn):
    fn(g["expected"])
    g["reference_output"] = copy.deepcopy(g["expected"])


def rename_action(f, g, d, old, new):
    for row in f["input"]["allowed_actions"]:
        if row["action"] == old:
            row["action"] = new
    for x in (g["expected"], g["reference_output"]):
        for step in x["steps"]:
            if step["action"] == old:
                step["action"] = new
    if old in d["gerunds"]:
        d["gerunds"][new] = d["gerunds"].pop(old)
    d["precedence_pairs"] = [[new if a == old else a, new if b == old else b, e] for a, b, e in d["precedence_pairs"]]


def forbidden_prefix_included(staged):
    f, g, d = first(staged, "PL1")
    old = g["expected"]["steps"][1]["action"]
    rename_action(f, g, d, old, "payroll_" + old)          # begins with "pay": the rule excludes it


def wrong_order_gold(staged):
    _, g, _ = first(staged, "PL3")
    def swap(x):
        s = x["steps"]
        s[1]["action"], s[2]["action"] = s[2]["action"], s[1]["action"]
    set_gold(g, swap)


def wrong_evidence_ids(staged):
    _, g, _ = first(staged, "PL6")
    set_gold(g, lambda x: x["steps"][0]["evidence_ids"].pop())


def missing_holding_code(staged):
    _, g, _ = first(staged, "PL3")
    set_gold(g, lambda x: x["uncertainties"].pop())


def decoy_made_holding(staged):
    f, _, d = first(staged, "PL1")
    decoy = next(c for c in f["input"]["allowed_uncertainty_codes"] if c["code"] in d["non_holding_codes"])
    thing = decoy["condition"][len("evidence says "):-len(" is unknown")]
    f["input"]["evidence"].append({"id": f"F{len(f['input']['evidence']) + 1}",
                                   "text": thing[0].upper() + thing[1:] + " is unknown."})


def pl4_listed_in_order(staged):
    f, _, d = first(staged, "PL4")
    rows = {r["id"]: r for r in f["input"]["evidence"]}
    chain_ids = [e for _, _, e in d["precedence_pairs"]]
    others = [r for r in f["input"]["evidence"] if r["id"] not in chain_ids]
    f["input"]["evidence"] = others[:1] + [rows[e] for e in chain_ids] + others[1:]


def non_pl4_out_of_order(staged):
    f, _, d = first(staged, "PL1")
    chain_ids = [e for _, _, e in d["precedence_pairs"]]
    rows = {r["id"]: r for r in f["input"]["evidence"]}
    others = [r for r in f["input"]["evidence"] if r["id"] not in chain_ids]
    f["input"]["evidence"] = others[:1] + [rows[e] for e in reversed(chain_ids)] + others[1:]


def pl5_second_multi_address(staged):
    f, _, _ = first(staged, "PL5")
    single = next(r for r in f["input"]["allowed_actions"] if len(r["addresses"]) == 1)
    extra = next(e["id"] for e in f["input"]["evidence"] if e["id"] not in single["addresses"])
    single["addresses"] = sorted(single["addresses"] + [extra])


def exactly_one_multi_outside_pl5(staged):
    f, _, _ = first(staged, "PL2")
    rows = f["input"]["allowed_actions"]
    keep = next(r for r in rows if len(r["addresses"]) > 1)
    for row in rows:
        row["addresses"] = row["addresses"][:2] if row is keep else row["addresses"][:1]


def wrong_precedence_form(staged):
    f, _, d = first(staged, "PL1", "before")
    x, y, eid = d["precedence_pairs"][0]
    row = next(r for r in f["input"]["evidence"] if r["id"] == eid)
    row["text"] = C.plan_sentence("after", d["gerunds"][x], d["gerunds"][y])


def ambiguous_order(staged):
    f, _, d = first(staged, "PL3")
    x, y, eid = d["precedence_pairs"].pop(1)
    row = next(r for r in f["input"]["evidence"] if r["id"] == eid)
    row["text"] = "The team meets on the first floor."


def duplicate_action_across_fixtures(staged):
    fa, ga, da = first(staged, "PL1")
    fb, gb, db = first(staged, "PL2")
    target = ga["expected"]["steps"][0]["action"]
    rename_action(fb, gb, db, gb["expected"]["steps"][0]["action"], target)


def authority_changed(staged):
    f, _, _ = first(staged, "PL6")
    f["input"]["authority"] = "execute_approved"


def claims_completed_true(staged):
    _, g, _ = first(staged, "PL2")
    set_gold(g, lambda x: x.__setitem__("claims_completed", True))


def objective_not_in_opening(staged):
    f, _, _ = first(staged, "PL5")
    f["input"]["objective"] = f["input"]["objective"] + " before winter"


def stray_unknown(staged):
    f, _, _ = first(staged, "PL6")
    f["input"]["evidence"].append({"id": f"F{len(f['input']['evidence']) + 1}",
                                   "text": "The ferry timetable is unknown."})


def shared_identifier(staged):
    for family in ("PL1", "PL2"):
        f, _, d = first(staged, family)
        f["input"]["evidence"][0]["text"] += " The file reference is QX-44719."
        d["identifiers"] = ["QX-44719"]


def undeclared_identifier(staged):
    f, _, _ = first(staged, "PL4")
    f["input"]["evidence"][0]["text"] += " The file reference is QX-44720."


def planning_n1_duplicate(staged):
    fa, ga, da = first(staged, "PL1")
    fb, gb, db = first(staged, "PL1", "after")
    fb["input"] = copy.deepcopy(fa["input"])
    gb["expected"] = copy.deepcopy(ga["expected"])
    gb["reference_output"] = copy.deepcopy(ga["expected"])


CASES = {
    forbidden_prefix_included: "included/excluded counts",
    wrong_order_gold: "planning gold differs from the gold recomputed",
    wrong_evidence_ids: "planning gold differs from the gold recomputed",
    missing_holding_code: "planning gold differs from the gold recomputed",
    decoy_made_holding: "holding of",
    pl4_listed_in_order: "PL4 precedences are not listed out of order",
    non_pl4_out_of_order: "precedences listed out of order outside PL4",
    pl5_second_multi_address: "PL5 needs exactly one action addressing two evidence items",
    exactly_one_multi_outside_pl5: "exactly one multi-address action outside PL5",
    wrong_precedence_form: "is not stated in the 'before' form",
    ambiguous_order: "do not give a unique total order",
    duplicate_action_across_fixtures: "planning action name",
    authority_changed: "planning input keys or authority",
    claims_completed_true: "planning gold differs from the gold recomputed",
    objective_not_in_opening: "objective is not stated in the opening",
    stray_unknown: "evidence states an unknown that no offered code covers",
    shared_identifier: "O3 identifier gate: shared identifier",
    undeclared_identifier: "identifiers not declared (O3 identifier gate)",
    planning_n1_duplicate: "N1 identical canonical gold",
}


if __name__ == "__main__":
    staged = [json.loads(Path(path).read_text(encoding="utf-8")) for path in sys.argv[1:]]
    clean, _ = C.check(staged)
    assert not clean, clean
    print("clean combined corpus: 0 problems")
    missed = 0
    for mutation, expected in CASES.items():
        candidate = copy.deepcopy(staged)
        mutation(candidate)
        problems, _ = C.check(candidate)
        hits = [problem for problem in problems if expected in problem]
        print(("FIRES " if hits else "MISSED"), mutation.__name__, "->", hits[0] if hits else problems[:3])
        missed += not hits
    print(f"{len(CASES) - missed} of {len(CASES)} planted Planning defects caught")
    raise SystemExit(1 if missed else 0)
