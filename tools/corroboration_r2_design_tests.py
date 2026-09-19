"""Read-only G-CORROB1-R2 design checks. No model, pilot, runner, or scorer."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

import g_evid1_harness as old_harness
import g_evid1_policy as policy


ROOT = Path(__file__).resolve().parents[1]
R1 = ROOT / "experiments/G-CORROB1-candidate"
R2 = ROOT / "experiments/G-CORROB1-candidate-r2"


def _json(name):
    return json.loads((R2 / name).read_text(encoding="utf-8"))


def _digest(path):
    data = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest()


def _seed(item_id, repeat, role):
    raw = f"G-CORROB1-R2-seed-v1|{item_id}|{repeat}|{role}".encode("utf-8")
    value = int(hashlib.sha256(raw).hexdigest()[:8], 16) & 0x7FFFFFFF
    return value or 1


def main():
    checks = []

    def require(name, value):
        checks.append({"name": name, "passed": bool(value)})
        if not value:
            raise AssertionError(name)

    # The prior candidate remains immutable historical evidence.
    r1_manifest = json.loads((R1 / "CANDIDATE_FREEZE.json").read_text(encoding="utf-8"))
    for relative, expected in r1_manifest["artifacts"].items():
        require("r1_preserved:" + relative, _digest(ROOT / relative) == expected)

    corpus = _json("corpus.json")
    gold_doc = _json("gold_candidate.json")
    sampling = _json("sampling_proposal.json")
    items = corpus["items"]
    gold = gold_doc["items"]
    by_gold = {row["item_id"]: row for row in gold}

    require("r2_not_authorized", corpus["status"] == "revised_design_not_authorized"
            and sampling["status"] == "sampling_proposal_fixed_not_execution_frozen")
    require("32_unique_items", len(items) == len({x["item_id"] for x in items}) == 32)
    require("unique_binding_ids", len({x["proposition_id"] for x in items}) == 32
            and len({x["evidence_id"] for x in items}) == 32)
    require("gold_exact_coverage", len(gold) == 32 and set(by_gold) == {x["item_id"] for x in items})
    require("28_primary_4_diagnostic", Counter(x["corpus_role"] for x in gold)
            == {"primary": 28, "ambiguity_diagnostic": 4})
    primary = [x for x in gold if x["corpus_role"] == "primary"]
    diagnostic = [x for x in gold if x["corpus_role"] == "ambiguity_diagnostic"]
    require("14_primary_use_14_forbid", sum(x["use_permitted"] for x in primary) == 14
            and sum(not x["use_permitted"] for x in primary) == 14)
    require("primary_disposition_denominators", Counter(x["expected_disposition"] for x in primary)
            == {"use": 14, "abstain": 11, "investigate": 3})
    require("diagnostics_separate", all(x["expected_disposition"] == "investigate"
            and not x["use_permitted"] and x["ambiguity"].startswith("genuine_") for x in diagnostic))
    require("primary_pairs_explicit", Counter(x["pair_id"] for x in primary)
            == {f"P{i:02d}": 2 for i in range(1, 15)})
    require("single_crisp_gold_tuple", all(isinstance(x["gold_relation"], str)
            and isinstance(x["gold_scope"], str) and isinstance(x["gold_temporal"], str) for x in gold))

    r2_template = (R2 / "prompt.txt").read_text(encoding="utf-8").rstrip("\r\n")
    prohibited_coaching = ("entire claim", "population and qualifiers", "persistence of a changeable state")
    require("outcome_derived_coaching_removed", not any(text in r2_template for text in prohibited_coaching))
    require("static_prompt_has_no_evaluation_labels", not re.search(
            r"\b(use|investigate|abstain|unsafe|safe|gold)\b", r2_template, re.I))
    for item in items:
        rendered = r2_template.format(**item)
        old_rendered = old_harness.PROMPT_TEMPLATE.format(
            proposition_id=item["proposition_id"], proposition=item["proposition"],
            purpose=item["intended_use"], evidence_id=item["evidence_id"], evidence=item["evidence"])
        require(item["item_id"] + ":prompt_identity", rendered == old_rendered)
        require(item["item_id"] + ":model_input_has_no_gold_metadata", all(key not in item for key in
                ("family", "pair_id", "gold_relation", "gold_scope", "gold_temporal",
                 "use_permitted", "expected_disposition", "ambiguity", "rationale")))

        expected = by_gold[item["item_id"]]
        sample = {
            "proposition_id": item["proposition_id"], "evidence_id": item["evidence_id"],
            "relation": expected["gold_relation"], "scope": expected["gold_scope"],
            "temporal": expected["gold_temporal"], "confidence": "high",
            "quotes": [item["evidence"][:180]],
        }
        governed = policy.assess_to_disposition(
            sample, proposition_id=item["proposition_id"], evidence_id=item["evidence_id"],
            evidence_text=item["evidence"])
        require(item["item_id"] + ":gold_policy_consistency",
                governed["validation"]["valid"]
                and governed["disposition"] == expected["expected_disposition"]
                and (governed["disposition"] == "use") == expected["use_permitted"]
                and governed["belief_effects"] == "none")

    old_items = json.loads((ROOT / "experiments/G-EVID1/corpus.json").read_text(encoding="utf-8"))["items"]
    r1_items = json.loads((R1 / "corpus.json").read_text(encoding="utf-8"))["items"]
    historical_text = {x[key].strip().casefold() for x in old_items + r1_items
                       for key in ("proposition", "evidence")}
    require("no_exact_historical_text_reuse", all(x[key].strip().casefold() not in historical_text
            for x in items for key in ("proposition", "evidence")))
    require("removed_ids_absent", not ({"C01", "C05", "C06", "C18", "C19", "C20"}
            & {x["item_id"] for x in items}))

    require("sampling_totals", sampling["planned_pairs"] == 96 and sampling["planned_calls"] == 192
            and sampling["items"] == 32 and sampling["repeats_per_item"] == 3)
    seeds = [_seed(item["item_id"], repeat, role) for item in items
             for repeat in range(1, 4) for role in ("A", "B")]
    require("192_distinct_nonzero_seeds", len(seeds) == len(set(seeds)) == 192 and min(seeds) > 0)
    order = [(index, repeat) for index in range(1, 33) for repeat in range(1, 4)]
    require("balanced_within_pair_order", sum((index + repeat) % 2 == 0 for index, repeat in order) == 48)
    require("fixed_sampling_parameters", sampling["parameters"] == {
        "temperature": 0.6, "top_p": 0.9, "top_k": 40, "min_p": 0.0,
        "repeat_penalty": 1.0, "num_ctx": 8192, "num_predict": 350,
        "stop": [], "stream": False})
    require("model_digest_is_future_gate", sampling["model_content_digest"] == "REQUIRED_AT_EXECUTION_FREEZE"
            and sampling["seed_contract"]["unsupported_seed_behavior"] == "block_execution_freeze")

    require("no_runner_scorer_or_pilot", not any((R2 / name).exists() for name in
            ("runner.py", "scorer.py", "comparison.py", "pilot.py", "runs", "COMPLETED.json")))
    print(json.dumps({"candidate": corpus["candidate_id"], "passed": len(checks), "checks": checks,
                      "provider_calls": 0, "pilot_launched": False, "runner_implemented": False,
                      "scorer_implemented": False, "execution_frozen": False}, indent=2))


if __name__ == "__main__":
    main()
