"""Adversarial checks for the Synthesis authoring rules, over Extraction + Synthesis together."""

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


def wrong_band(staged):
    f, _, _ = locate(staged, "A4-SYNTH-R1-02")
    f["input"]["observations"].append({"id": "O299", "role": "extra", "text": "Extra bounded note."})
    f["input"]["observations"].append({"id": "O300", "role": "extra_two", "text": "Second extra bounded note."})


def wrong_mergeability(staged):
    f, g, _ = locate(staged, "A4-SYNTH-R1-02")
    first, second = f["input"]["observations"][:2]
    second["role"] = first["role"]
    g["expected"]["roles"][second["id"]] = first["role"]


def wrong_role_gold(staged):
    _, g, _ = locate(staged, "A4-SYNTH-R1-01")
    first = next(iter(g["expected"]["roles"]))
    g["expected"]["roles"][first] = "wrong_role"


def wrong_family_conclusion(staged):
    _, g, _ = locate(staged, "A4-SYNTH-R2-01")
    g["expected"]["conclusion"] = "cause_established"
    g["reference_output"]["conclusion"] = "cause_established"


def ungrounded_anchor(staged):
    _, g, _ = locate(staged, "A4-SYNTH-R3-01")
    first = next(iter(g["expected"]["required_terms"]))
    g["expected"]["required_terms"][first] = ["not_in_observation"]


def dropped_observation(staged):
    _, g, _ = locate(staged, "A4-SYNTH-R4-01")
    g["reference_output"]["statements"].pop()


def mixed_role_merge(staged):
    _, g, _ = locate(staged, "B4-SYNTH-R1-01")
    rows = g["reference_output"]["statements"]
    rows[0]["observation_ids"].append(rows[-1]["observation_ids"][0])
    rows.pop()


def nonverbatim_statement(staged):
    _, g, _ = locate(staged, "B4-SYNTH-R2-01")
    g["reference_output"]["statements"][0]["text"] = "A shortened paraphrase."


def duplicate_canonical_gold(staged):
    first_fixture, first, _ = locate(staged, "B4-SYNTH-R3-01")
    second_fixture, second, _ = locate(staged, "B4-SYNTH-R3-02")
    second_fixture["input"]["observations"] = copy.deepcopy(first_fixture["input"]["observations"])
    second["expected"] = copy.deepcopy(first["expected"])
    second["reference_output"] = copy.deepcopy(first["reference_output"])


CASES = {
    wrong_band: "synthesis observation count",
    wrong_mergeability: "realized mergeable roles",
    wrong_role_gold: "synthesis gold roles",
    wrong_family_conclusion: "synthesis conclusion differs from family semantics",
    ungrounded_anchor: "required terms",
    dropped_observation: "synthesis reference coverage",
    mixed_role_merge: "mixed or incorrect roles",
    nonverbatim_statement: "does not preserve verbatim text",
    duplicate_canonical_gold: "N1 identical canonical gold",
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
    print(f"{len(CASES) - missed} of {len(CASES)} planted Synthesis defects caught")
    raise SystemExit(1 if missed else 0)
