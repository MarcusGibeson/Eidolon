"""Adversarial checks for G-ROUTE4 Grounded Research authoring rules.

Run over all five authored classes so pooled O3/O6/N1 behavior is exercised.

    python -B test_research_corpus.py staging/extraction.json staging/synthesis.json \
        staging/planning.json staging/conversation.json staging/research.json
"""

import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_corpus as C  # noqa: E402
from english_vocabulary import english_vocabulary  # noqa: E402


def research_document(staged):
    return next(d for d in staged if d["task_class"] == "grounded_research_synthesis")


def locate(staged, fid):
    document = research_document(staged)
    fixtures = {row["fixture_id"]: row for row in document["fixtures"]}
    gold = {row["fixture_id"]: row for row in document["gold"]}
    design = {row["fixture_id"]: row for row in document["design"]}
    return fixtures[fid], gold[fid], design[fid]


def first(staged, pattern, sls=None, role=None):
    document = research_document(staged)
    for row in document["design"]:
        features = row["features"]
        if features["pattern"] == pattern and (sls is None or features["sls"] is sls) and \
                (role is None or row["role"] == role):
            return locate(staged, row["fixture_id"])
    raise KeyError((pattern, sls, role))


def source_spec(design, source_id):
    return next(row for row in design["research_contract"]["sources"] if row["source_id"] == source_id)


def wrong_input_shape(staged):
    fixture, _, _ = first(staged, "P1")
    fixture["input"]["unplanned_field"] = True


def wrong_claim_count(staged):
    fixture, _, design = first(staged, "P2")
    fixture["input"]["claims"].pop()
    design["research_contract"]["claims"].pop()


def wrong_source_count(staged):
    fixture, _, design = first(staged, "P3")
    fixture["input"]["sources"].pop()
    design["research_contract"]["sources"].pop()


def bad_claim_identity(staged):
    fixture, _, _ = first(staged, "P4")
    fixture["input"]["claims"][0]["claim_id"] = "C9"


def bad_source_identity(staged):
    fixture, _, _ = first(staged, "P5")
    fixture["input"]["sources"][0]["source_id"] = "S9"


def wrong_recommendations(staged):
    fixture, _, _ = first(staged, "P6")
    fixture["input"]["allowed_recommendations"] = ["hold_record", "accept_record"]


def wrong_uncertainty_contract(staged):
    fixture, _, _ = first(staged, "P7")
    fixture["input"]["allowed_uncertainty_codes"][0]["condition"] = "any support exists"


def broken_name_binding(staged):
    _, _, design = first(staged, "P8")
    design["invented_names"] = list(reversed(design["invented_names"]))


def broken_claim_ledger(staged):
    _, _, design = first(staged, "P1")
    design["research_contract"]["claims"][0]["claim_id"] = "C8"


def claim_text_drift(staged):
    fixture, _, _ = first(staged, "P2")
    fixture["input"]["claims"][0]["text"] += " Extra assertion."


def malformed_source_ledger(staged):
    _, _, design = first(staged, "P3")
    source_spec(design, "S1")["unexpected"] = True


def unknown_source_relation(staged):
    _, _, design = first(staged, "P4")
    source_spec(design, "S1")["relation"] = "maybe"


def source_text_drift(staged):
    fixture, _, _ = first(staged, "P5")
    fixture["input"]["sources"][0]["lineage"] += "-drift"


def p1_loses_independence(staged):
    _, _, design = first(staged, "P1")
    sources = design["research_contract"]["sources"]
    sources[1]["lineage"] = sources[0]["lineage"]


def p2_wrong_direction(staged):
    _, _, design = first(staged, "P2")
    source_spec(design, "S1")["relation"] = "support"


def p3_wrong_subject(staged):
    fixture, _, design = first(staged, "P3")
    source_spec(design, "S1")["relation"] = "support"
    fixture["input"]["sources"][0]["text"] = C.research_source_text(
        source_spec(design, "S1"), design["research_contract"]["claims"],
        design["research_contract"]["context"]["secondary"], design["research_contract"]["context"])


def p4_loses_same_lineage(staged):
    _, _, design = first(staged, "P4", True)
    sources = design["research_contract"]["sources"]
    sources[1]["lineage"] += "-independent"


def p5_loses_conflict(staged):
    _, _, design = first(staged, "P5")
    source_spec(design, "S2")["relation"] = "support"


def p6_loses_scope(staged):
    _, _, design = first(staged, "P6")
    design["research_contract"]["claims"][0]["kind"] = "standard"


def p7_bad_temporal_order(staged):
    _, _, design = first(staged, "P7")
    sources = design["research_contract"]["sources"]
    sources[0]["date"], sources[1]["date"] = sources[1]["date"], sources[0]["date"]


def p8_not_below_threshold(staged):
    _, _, design = first(staged, "P8")
    design["research_contract"]["sources"][0]["actual"] = \
        design["research_contract"]["claims"][0]["threshold"]


def wrong_gold(staged):
    _, gold, _ = first(staged, "P1")
    gold["expected"]["claims"][0]["status"] = "unresolved"


def wrong_reference(staged):
    _, gold, _ = first(staged, "P2")
    gold["reference_output"]["recommendation"] = "accept_record"


def wrong_rationale(staged):
    _, _, design = first(staged, "P5")
    design["research_contract"]["derived_reasons"]["C1"] = "direct_support"


def wrong_sls_feature(staged):
    fixture, _, design = first(staged, "P1", False)
    contract = design["research_contract"]
    spec = next(row for row in contract["sources"] if row["claim_id"] != "C1")
    spec["relation"] = "support"
    rendered = next(row for row in fixture["input"]["sources"] if row["source_id"] == spec["source_id"])
    rendered["text"] = C.research_source_text(
        spec, contract["claims"], contract["context"]["secondary"], contract["context"])


def wrong_decision_rule(staged):
    fixture, _, _ = first(staged, "P7")
    fixture["input"]["decision_rule"] = "Recommend accept_record when convenient."


def reserve_without_main(staged):
    document = research_document(staged)
    reserve = next(row for row in document["design"] if row["phase"] == "A" and row["role"] == "reserve")
    matching = next(row for row in document["design"] if row["phase"] == "A" and row["role"] == "main" and
                    row["risk"] == reserve["risk"] and row["family"] == reserve["family"] and
                    row["features"] == reserve["features"])
    fid = matching["fixture_id"]
    for key in ("fixtures", "gold", "design"):
        document[key] = [row for row in document[key] if row["fixture_id"] != fid]


def repeated_lineage(staged):
    fa, _, da = first(staged, "P1")
    fb, _, db = first(staged, "P2")
    lineage = fa["input"]["sources"][0]["lineage"]
    fb["input"]["sources"][0]["lineage"] = lineage
    db["research_contract"]["sources"][0]["lineage"] = lineage


def duplicate_research_gold(staged):
    _, ga, _ = first(staged, "P2")
    _, gb, _ = first(staged, "P3")
    gb["expected"] = copy.deepcopy(ga["expected"])
    gb["reference_output"] = copy.deepcopy(ga["expected"])


CASES = {
    wrong_input_shape: "research input keys differ from the frozen construct",
    wrong_claim_count: "research claim count differs from family",
    wrong_source_count: "research source count differs from family",
    bad_claim_identity: "research claim identities or keys are invalid",
    bad_source_identity: "research source identities or keys are invalid",
    wrong_recommendations: "research recommendations differ from the authored frozen pair",
    wrong_uncertainty_contract: "research uncertainty code contract differs from the frozen rules",
    broken_name_binding: "research context or invented-name binding is invalid",
    broken_claim_ledger: "research claim ledger binding is invalid",
    claim_text_drift: "research claim text differs from its semantic ledger",
    malformed_source_ledger: "research source ledger identities or keys are invalid",
    unknown_source_relation: "research source ledger has an unknown binding or relation",
    source_text_drift: "research source text, lineage or binding differs from its semantic ledger",
    p1_loses_independence: "research focal evidence does not realize pattern P1",
    p2_wrong_direction: "research focal evidence does not realize pattern P2",
    p3_wrong_subject: "research focal evidence does not realize pattern P3",
    p4_loses_same_lineage: "research focal evidence does not realize pattern P4",
    p5_loses_conflict: "research focal evidence does not realize pattern P5",
    p6_loses_scope: "research narrower-scope binding is invalid",
    p7_bad_temporal_order: "research temporal-governance relation is invalid",
    p8_not_below_threshold: "research quantitative contradiction does not fall below the threshold",
    wrong_gold: "research gold differs from the statuses and evidence recomputed from input",
    wrong_reference: "research reference_output differs from expected",
    wrong_rationale: "research rationale ledger differs from recomputed reasons",
    wrong_sls_feature: "research single_lineage_support outcome differs from the frozen feature",
    wrong_decision_rule: "research decision rule does not express the pattern's frozen decision",
    reserve_without_main: "grounded_research_synthesis reserves without a matching main slot",
    repeated_lineage: "grounded_research_synthesis lineages repeat across fixtures",
    duplicate_research_gold: "N1 identical canonical gold",
}


if __name__ == "__main__":
    staged = [json.loads(Path(path).read_text(encoding="utf-8")) for path in sys.argv[1:]]
    english, _ = english_vocabulary()
    clean, _ = C.check(staged, english)
    assert not clean, clean
    print("clean five-class corpus: 0 problems")
    missed = 0
    for mutation, expected in CASES.items():
        candidate = copy.deepcopy(staged)
        mutation(candidate)
        problems, _ = C.check(candidate, english)
        hits = [problem for problem in problems if expected in problem]
        print(("FIRES " if hits else "MISSED"), mutation.__name__, "->", hits[0] if hits else problems[:3])
        missed += not hits
    print(f"{len(CASES) - missed} of {len(CASES)} planted Research defects caught")
    raise SystemExit(1 if missed else 0)
