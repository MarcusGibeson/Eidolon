"""Adversarial checks for G-ROUTE4 Ordinary Conversation authoring rules.

Run over Extraction + Synthesis + Planning + Conversation so pooled O3/O6/N1 behavior is exercised too.

    python -B test_conversation_corpus.py staging/extraction.json staging/synthesis.json staging/planning.json \
        staging/conversation.json
"""

import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_corpus as C  # noqa: E402
from english_vocabulary import english_vocabulary  # noqa: E402


def locate(staged, fid):
    for document in staged:
        fixtures = {row["fixture_id"]: row for row in document["fixtures"]}
        if fid in fixtures:
            gold = {row["fixture_id"]: row for row in document["gold"]}
            design = {row["fixture_id"]: row for row in document["design"]}
            return fixtures[fid], gold[fid], design[fid]
    raise KeyError(fid)


def first(staged, family, depth=None, role=None):
    document = next(d for d in staged if d["task_class"] == "ordinary_conversation")
    for row in document["design"]:
        if row["family"] == family and (depth is None or row["features"]["depth"] == depth) and \
                (role is None or row["role"] == role):
            return locate(staged, row["fixture_id"])
    raise KeyError((family, depth, role))


def wrong_input_shape(staged):
    f, _, _ = first(staged, "CV2", 1)
    f["input"]["unplanned_hint"] = 1


def fifth_option(staged):
    f, _, d = first(staged, "CV3", 1)
    f["input"]["answer_options"].append("Extraoption")
    d["invented_names"].append("Extraoption")


def canonical_duplicate_option(staged):
    f, _, d = first(staged, "CV4", 1)
    f["input"]["answer_options"][1] = f"`{f['input']['answer_options'][0]}`"
    d["invented_names"][1] = f["input"]["answer_options"][1]


def wrong_gold_contract(staged):
    _, g, _ = first(staged, "CV5", 1)
    g["expected"]["max_characters"] = 599


def wrong_gold_position(staged):
    f, _, d = first(staged, "CV6", 1)
    position = d["features"]["gold_position"] - 1
    other = (position + 1) % 4
    f["input"]["answer_options"][position], f["input"]["answer_options"][other] = \
        f["input"]["answer_options"][other], f["input"]["answer_options"][position]
    d["invented_names"] = list(f["input"]["answer_options"])


def options_not_name_draws(staged):
    _, _, d = first(staged, "CV1", 1)
    d["invented_names"] = list(reversed(d["invented_names"]))


def malformed_candidate(staged):
    f, _, _ = first(staged, "CV2", 2)
    f["input"]["candidates"][0].pop("second_leg")


def recomputed_gold_changed(staged):
    f, _, d = first(staged, "CV1", 1)
    position = d["features"]["gold_position"] - 1
    f["input"]["candidates"][position]["condition_two"] = False


def duplicate_near_miss(staged):
    f, _, d = first(staged, "CV1", 1)
    position = d["features"]["gold_position"] - 1
    near = f["input"]["answer_options"].index(d["near_miss_option"])
    far = next(i for i in range(4) if i not in (position, near))
    f["input"]["candidates"][far]["condition_one"] = True


def depth_two_near_miss_lost(staged):
    f, _, d = first(staged, "CV2", 2)
    near = f["input"]["answer_options"].index(d["near_miss_option"])
    f["input"]["candidates"][near]["first_leg"] -= 1


def wrong_declared_near_miss(staged):
    _, g, d = first(staged, "CV3", 2)
    d["near_miss_option"] = g["expected"]["answer"]


def non_text_reference(staged):
    _, g, _ = first(staged, "CV4", 2)
    g["reference_output"] = {"answer": g["expected"]["answer"]}


def wrong_reference_frame(staged):
    _, g, _ = first(staged, "CV5", 2)
    g["reference_output"] = g["reference_output"].replace("Actions taken: none", "Actions taken: filed it")


def reserve_without_main(staged):
    document = next(d for d in staged if d["task_class"] == "ordinary_conversation")
    reserve = next(row for row in document["design"] if row["phase"] == "A" and row["role"] == "reserve")
    matching = next(row for row in document["design"] if row["phase"] == "A" and row["role"] == "main" and
                    row["risk"] == reserve["risk"] and row["family"] == reserve["family"] and
                    row["features"] == reserve["features"])
    fid = matching["fixture_id"]
    for key in ("fixtures", "gold", "design"):
        document[key] = [row for row in document[key] if row["fixture_id"] != fid]


def duplicate_conversation_gold(staged):
    fa, ga, _ = first(staged, "CV1", 1)
    fb, gb, db = first(staged, "CV2", 1)
    answer = ga["expected"]["answer"]
    position = db["features"]["gold_position"] - 1
    fb["input"]["answer_options"][position] = answer
    db["invented_names"][position] = answer
    gb["expected"]["answer"] = answer
    gb["reference_output"] = f"Answer: {answer}\nActions taken: none\nDuplicated solely for the checker test."


def repeated_o6_option(staged):
    fa, ga, _ = first(staged, "CV3", 1)
    fb, gb, db = first(staged, "CV4", 1)
    source = next(option for option in fa["input"]["answer_options"] if option != ga["expected"]["answer"])
    position = next(i for i, option in enumerate(fb["input"]["answer_options"]) if option != gb["expected"]["answer"])
    fb["input"]["answer_options"][position] = source
    db["invented_names"][position] = source


CASES = {
    wrong_input_shape: "conversation input keys differ from the family/depth construct",
    fifth_option: "conversation must have exactly 4 answer options",
    canonical_duplicate_option: "conversation options are not pairwise distinct under canonical_value",
    wrong_gold_contract: "conversation gold keys or max_characters differ from the frozen contract",
    wrong_gold_position: "conversation gold answer is not at the frozen position",
    options_not_name_draws: "conversation options differ from the declared global name draws",
    malformed_candidate: "conversation candidate 1 keys differ from the family/depth construct",
    recomputed_gold_changed: "conversation recomputed gold positions",
    duplicate_near_miss: "conversation needs exactly one first-condition-only near miss",
    depth_two_near_miss_lost: "conversation needs exactly one first-condition-only near miss",
    wrong_declared_near_miss: "declared near-miss option differs from the recomputed near miss",
    non_text_reference: "conversation reference output is not text",
    wrong_reference_frame: "conversation reference does not use the exact disclosed frame",
    reserve_without_main: "ordinary_conversation reserves without a matching main slot",
    duplicate_conversation_gold: "N1 identical canonical gold",
    repeated_o6_option: "O6 shared value",
}


if __name__ == "__main__":
    staged = [json.loads(Path(path).read_text(encoding="utf-8")) for path in sys.argv[1:]]
    english, _ = english_vocabulary()
    clean, _ = C.check(staged, english)
    assert not clean, clean
    print("clean four-class corpus: 0 problems")
    missed = 0
    for mutation, expected in CASES.items():
        candidate = copy.deepcopy(staged)
        mutation(candidate)
        problems, _ = C.check(candidate, english)
        hits = [problem for problem in problems if expected in problem]
        print(("FIRES " if hits else "MISSED"), mutation.__name__, "->", hits[0] if hits else problems[:3])
        missed += not hits
    print(f"{len(CASES) - missed} of {len(CASES)} planted Conversation defects caught")
    raise SystemExit(1 if missed else 0)
