"""The future G-ROUTE4 seal layout (defined and tested here; NO seal is created by this module).

The seal commit (G-ROUTE4_OBLIGATIONS.md O1/O2) is the single commit on main whose parent is the frozen blueprint
commit. This module fixes what it will contain and proves the blind separation: the files a model or an adjudicator
reads carry no gold, rationale or authoring-ledger content.

    sealed/corpus_a.json            model-facing A′ main fixtures        (read by models and adjudicators)
    sealed/corpus_b.json            model-facing B′ main fixtures
    sealed/reserve_corpus_a.json    model-facing A′ reserve fixtures
    sealed/reserve_corpus_b.json    model-facing B′ reserve fixtures
    sealed/gold_a.json              A′ main gold, reference outputs and rationales   (never shown to a model)
    sealed/gold_b.json              B′ main gold, reference outputs and rationales
    sealed/reserve_gold_a.json      A′ reserve gold, reference outputs and rationales
    sealed/reserve_gold_b.json      B′ reserve gold, reference outputs and rationales
    sealed/authoring_ledger.json    every design record (semantic ledgers, name draws, signatures)
    sealed/adjudicator_config.json  the frozen O2 configuration
    sealed/SEAL_MANIFEST.json       sha256 of every file above, and of the canonical content of each

    python -B seal_layout.py --dry-run OUT_DIR   # writes the layout to OUT_DIR (never into the repository)
"""

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAYOUT_VERSION = "g-route4.seal-layout.v1"
FIXTURE_KEYS = ("consequence_risk", "fixture_id", "input", "prompt", "task_class", "title", "validator_profile")
GOLD_KEYS = ("expected", "fixture_id", "rationale", "reference_output")
# keys that exist only in gold or in the authoring ledger; none may appear anywhere in a model-facing file
GOLD_ONLY_KEYS = {"expected", "reference_output", "rationale", "required_terms", "roles", "conclusion",
                  "recommendation", "uncertainties", "steps", "claims_completed", "requested_authority", "answer",
                  "max_characters", "statements"}
# ("role" is not listed: observation roles are part of the frozen, model-facing Synthesis input)
LEDGER_ONLY_KEYS = {"invented_names", "unused_stream_draws", "global_name_ordinals", "identifiers", "family",
                    "features", "phase", "risk", "research_contract", "derived_reasons",
                    "canonical_signature", "message_units", "near_miss_option", "facts", "derived_keys",
                    "absence_sentence", "precedence_pairs", "gerunds", "excluded_actions", "holding_codes",
                    "non_holding_codes", "merged_role", "lineage_key", "when", "alternate_subject", "reissue"}
MODEL_FACING = ("corpus_a.json", "corpus_b.json", "reserve_corpus_a.json", "reserve_corpus_b.json")
GOLD_FILES = ("gold_a.json", "gold_b.json", "reserve_gold_a.json", "reserve_gold_b.json")


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def part_of(design):
    return ("reserve_" if design["role"] == "reserve" else "") + {"A": "{}_a", "B": "{}_b"}[design["phase"]]


def build_layout(staged, adjudicator_config=None):
    """{file name: JSON object} for the seal, from the staging documents (all five classes)."""
    layout = {name: {"layout_version": LAYOUT_VERSION, "fixtures": []} for name in MODEL_FACING}
    layout.update({name: {"layout_version": LAYOUT_VERSION, "items": []} for name in GOLD_FILES})
    ledger = {"layout_version": LAYOUT_VERSION, "items": []}
    for document in staged:
        gold = {row["fixture_id"]: row for row in document["gold"]}
        design = {row["fixture_id"]: row for row in document["design"]}
        for fixture in document["fixtures"]:
            fid = fixture["fixture_id"]
            part = part_of(design[fid])
            layout[part.format("corpus") + ".json"]["fixtures"].append({k: fixture[k] for k in FIXTURE_KEYS})
            layout[part.format("gold") + ".json"]["items"].append({k: gold[fid][k] for k in GOLD_KEYS})
            ledger["items"].append(design[fid])
    for name in MODEL_FACING:
        layout[name]["fixtures"].sort(key=lambda row: row["fixture_id"])
    for name in GOLD_FILES:
        layout[name]["items"].sort(key=lambda row: row["fixture_id"])
    ledger["items"].sort(key=lambda row: row["fixture_id"])
    layout["authoring_ledger.json"] = ledger
    if adjudicator_config is not None:
        layout["adjudicator_config.json"] = adjudicator_config
    layout["SEAL_MANIFEST.json"] = {
        "layout_version": LAYOUT_VERSION,
        "files": {name: {"canonical_sha256": sha256_text(canonical(obj)),
                         "count": len(obj.get("fixtures", obj.get("items", [])))}
                  for name, obj in sorted(layout.items())},
        "blind_separation": "model-facing files hold only the fixture keys " + ", ".join(FIXTURE_KEYS),
    }
    return layout


def keys_in(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield key
            yield from keys_in(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from keys_in(value)


def verify_blind(layout):
    """Problems with the blind separation (empty when the layout is sound)."""
    problems = []
    seen = {}
    for name in MODEL_FACING:
        for fixture in layout[name]["fixtures"]:
            if tuple(sorted(fixture)) != FIXTURE_KEYS:
                problems.append(f"{name}: {fixture.get('fixture_id')} has keys beyond the model-facing fixture keys")
            leaked = sorted(set(keys_in(fixture)) & (GOLD_ONLY_KEYS | LEDGER_ONLY_KEYS))
            if leaked:
                problems.append(f"{name}: {fixture.get('fixture_id')} carries gold or ledger keys {leaked}")
            seen.setdefault(fixture["fixture_id"], name)
    gold_ids = {row["fixture_id"]: name for name in GOLD_FILES for row in layout[name]["items"]}
    if set(seen) != set(gold_ids):
        problems.append("model-facing fixtures and gold items do not cover the same fixture ids")
    for fid, name in seen.items():
        if gold_ids.get(fid, "").replace("gold", "corpus") != name:
            problems.append(f"{fid}: gold file does not correspond to its model-facing file")
    for name in GOLD_FILES:
        if any(tuple(sorted(row)) != GOLD_KEYS for row in layout[name]["items"]):
            problems.append(f"{name}: gold items have keys other than {GOLD_KEYS}")
    return problems


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "--dry-run":
        raise SystemExit("usage: python -B seal_layout.py --dry-run OUT_DIR")
    out = Path(sys.argv[2]).resolve()
    if HERE.parents[2] in out.parents or out == HERE.parents[2]:
        raise SystemExit("refusing to write a seal layout inside the repository (the seal is a separate step)")
    staged = [json.loads((HERE / "staging" / f"{c}.json").read_text(encoding="utf-8"))
              for c in ("extraction", "synthesis", "planning", "conversation", "research")]
    import adjudicator_config as AC  # noqa: E402
    layout = build_layout(staged, AC.config())
    problems = verify_blind(layout)
    out.mkdir(parents=True, exist_ok=True)
    for name, obj in layout.items():
        (out / name).write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({name: v["count"] for name, v in layout["SEAL_MANIFEST.json"]["files"].items()}))
    print("blind separation:", "OK" if not problems else problems)
    raise SystemExit(1 if problems else 0)
