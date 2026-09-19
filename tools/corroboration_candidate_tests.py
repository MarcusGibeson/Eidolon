"""Read-only candidate integrity checks. No provider, runtime or experiment run."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from string import Formatter

import g_evid1_policy as policy

ROOT = Path(__file__).resolve().parents[1]
AREA = ROOT / "experiments/G-CORROB1-candidate"


def digest(path):
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")).hexdigest()


def main():
    checks = []
    def require(name, value):
        checks.append({"name": name, "passed": bool(value)})
        if not value:
            raise AssertionError(name)

    frozen = json.loads((AREA / "CANDIDATE_FREEZE.json").read_text(encoding="utf-8"))
    require("candidate_only", frozen["status"] == "candidate_frozen_not_authorized"
            and frozen["execution_authorized"] is False and frozen["gold_adjudicated"] is False)
    for name, expected in frozen["artifacts"].items():
        require("digest:" + name, digest(ROOT / name) == expected)
    items = json.loads((AREA / "corpus.json").read_text(encoding="utf-8"))["items"]
    gold = json.loads((AREA / "gold_candidate.json").read_text(encoding="utf-8"))
    require("gold_not_model_input", gold["model_input"] is False)
    require("28_unique_items", len(items) == len({i["item_id"] for i in items}) == 28)
    require("binding_ids_unique", len({i["proposition_id"] for i in items}) == len({i["evidence_id"] for i in items}) == 28)
    require("gold_exact_coverage", {i["item_id"] for i in items} == {i["item_id"] for i in gold["items"]}
            and len(gold["items"]) == 28)
    require("seven_balanced_families", sorted(Counter(g["family"] for g in gold["items"]).values()) == [4] * 7)
    require("16_admissible_12_forbidden", sum(g["forbidden_dispositions"] == [] for g in gold["items"]) == 16
            and sum(g["forbidden_dispositions"] == ["use"] for g in gold["items"]) == 12)
    template = (AREA / "prompt.txt").read_text(encoding="utf-8")
    fields = {field for _, field, _, _ in Formatter().parse(template) if field}
    require("explicit_prompt_allowlist", fields == {"proposition_id", "evidence_id", "context", "proposition", "evidence"})
    old = json.loads((ROOT / "experiments/G-EVID1/corpus.json").read_text(encoding="utf-8"))["items"]
    old_text = {row[key].strip().casefold() for row in old for key in ("proposition", "evidence")}
    require("fresh_not_reused_text", all(row[key].strip().casefold() not in old_text for row in items for key in ("proposition", "evidence")))
    for row, expected in zip(items, gold["items"]):
        require(row["item_id"] + ":aligned", row["item_id"] == expected["item_id"])
        rendered = template.format(**{key: row[key] for key in fields})
        require(row["item_id"] + ":blind_prompt", not re.search(r"\b(use|investigate|abstain|unsafe|safe|gold)\b", rendered, re.I)
                and all(key not in row for key in ("family", "rationale", "forbidden_dispositions", "expected_dispositions")))
        # Prospective scoring consistency only; this is not model judgment or gold adjudication.
        for relation, scope, temporal in expected["acceptable_semantics"]:
            sample = {"proposition_id": row["proposition_id"], "evidence_id": row["evidence_id"],
                      "relation": relation, "scope": scope, "temporal": temporal,
                      "confidence": "high", "quotes": [row["evidence"][:180]]}
            result = policy.assess_to_disposition(sample, proposition_id=row["proposition_id"],
                evidence_id=row["evidence_id"], evidence_text=row["evidence"])
            require(row["item_id"] + ":gold_policy_consistency", result["validation"]["valid"]
                    and result["disposition"] in expected["expected_dispositions"]
                    and result["disposition"] not in expected["forbidden_dispositions"]
                    and result["belief_effects"] == "none")
    schedule = [(i, repeat) for i in range(1, 29) for repeat in range(1, 4)]
    require("168_calls_balanced_order", len(schedule) * 2 == 168
            and sum((i + repeat) % 2 == 0 for i, repeat in schedule) == 42)
    require("no_run_artifacts", not (AREA / "runs").exists() and not (AREA / "COMPLETED.json").exists())
    print(json.dumps({"passed": len(checks), "checks": checks, "provider_calls": 0,
                      "experiment_launched": False, "gold_adjudicated": False}, indent=2))


if __name__ == "__main__":
    main()
