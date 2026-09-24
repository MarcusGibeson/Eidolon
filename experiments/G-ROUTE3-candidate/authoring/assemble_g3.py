"""Assemble and self-validate the G-ROUTE3 corpora (round 2). Writes only after every check passes."""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = Path("C:/Users/marcu/Eidolon")
sys.path.insert(0, str(ROOT / "tools"))

import author_g3_part1 as p1
import author_g3_part2  # noqa: F401  (registers fixtures)
import author_g3_part3  # noqa: F401
from g_route1_coding_runner import run_isolated_fixture, validate_candidate_ast
from g_route1_validators import validate_fixture_output
from g_route3_operational import validate_operational
from g_route3_triggers import triggers_for

OUT = ROOT / "experiments" / "G-ROUTE3-candidate"
TASKS = ("ordinary_conversation", "structured_extraction", "grounded_research_synthesis",
         "hierarchical_semantic_synthesis", "coding_generation_repair", "reflective_planning")
PROFILES = json.loads((ROOT / "experiments/G-ROUTE1-candidate/prompt_profiles.json").read_text(encoding="utf-8"))["profiles"]
problems = []


def model_facing(fixture):
    return (PROFILES[fixture["validator_profile"]] + "\n" + fixture["prompt"] + "\n"
            + json.dumps(fixture["input"], ensure_ascii=False, sort_keys=True))


def as_raw(value):
    return value if isinstance(value, str) else json.dumps(value, sort_keys=True)


def judged(fixture, gold, raw):
    evidence = run_isolated_fixture(fixture, raw) if fixture["validator_profile"] == "coding.v1" else None
    op = validate_operational(fixture, raw, execution_evidence=evidence)
    sem = validate_fixture_output(fixture, gold, raw, execution_evidence=evidence)
    return op, sem


by_corpus = defaultdict(list)
for corpus, fixture, gold, design in p1.FIXTURES:
    by_corpus[corpus].append((fixture, gold, design))

for corpus, rows in by_corpus.items():
    ids = [f["fixture_id"] for f, _, _ in rows]
    if len(ids) != 48 or len(set(ids)) != 48:
        problems.append(f"{corpus}:count_or_duplicate:{len(ids)}:{sorted(k for k, n in Counter(ids).items() if n > 1)}")
    if any(not i.startswith(corpus + "-") for i in ids):
        problems.append(f"{corpus}:namespace")
    cells = Counter((f["task_class"], f["consequence_risk"]) for f, _, _ in rows)
    if set(cells.values()) != {2} or len(cells) != 24:
        problems.append(f"{corpus}:cell_balance:{dict(cells)}")

for corpus, rows in by_corpus.items():
    for fixture, gold, design in rows:
        fid, profile = fixture["fixture_id"], fixture["validator_profile"]
        raw = as_raw(gold["reference_output"])
        if profile == "coding.v1":
            try:
                validate_candidate_ast(gold["expected"]["new"])
            except Exception as exc:
                problems.append(f"{fid}:gold_violates_whitelist:{exc}")
            evidence = run_isolated_fixture(fixture, raw)
            if not (evidence["compile_pass"] and evidence["tests_pass"]):
                problems.append(f"{fid}:gold_fails_tests")
            try:
                buggy = run_isolated_fixture(fixture, json.dumps({"path": "app.py", "old": fixture["input"]["source"],
                                                                  "new": fixture["input"]["source"]}))
                if buggy["tests_pass"]:
                    problems.append(f"{fid}:buggy_source_already_passes")
            except Exception:
                pass
        op, sem = judged(fixture, gold, raw)
        if not op["accepted"]:
            problems.append(f"{fid}:reference_rejected_operationally:{op['reasons']}")
        if not sem["hard_gate_pass"]:
            problems.append(f"{fid}:reference_fails_gold:{sem['reasons']}")
        fired = triggers_for(fixture, raw)
        if fired:
            problems.append(f"{fid}:trigger_fires_on_reference:{fired}")
        for text in gold.get("alternative_correct_outputs", []):
            a_op, a_sem = judged(fixture, gold, text)
            if not (a_op["accepted"] and a_sem["hard_gate_pass"]):
                problems.append(f"{fid}:alternative_correct_rejected:{text!r}:{a_op['reasons']}{a_sem['reasons']}")
        for text in gold.get("incorrect_outputs", []):
            w_op, w_sem = judged(fixture, gold, text)
            if w_op["accepted"] and w_sem["hard_gate_pass"]:
                problems.append(f"{fid}:incorrect_answer_accepted:{text!r}")
        if profile == "conversation.v1" and len(gold.get("alternative_correct_outputs", [])) < 3:
            problems.append(f"{fid}:too_few_alternative_phrasings")
        if profile == "conversation.v1" and "600 characters" not in fixture["prompt"]:
            problems.append(f"{fid}:length_limit_not_disclosed")

        text = model_facing(fixture)
        exp = gold["expected"]
        codes = []
        if profile == "research.v1":
            codes = [exp["recommendation"], *exp["uncertainties"]] + [c["status"] for c in exp["claims"]]
        elif profile == "synthesis.v1":
            codes = [exp["conclusion"], *exp["roles"].values()]
            for oid, terms in exp["required_terms"].items():
                obs = next(o["text"] for o in fixture["input"]["observations"] if o["id"] == oid)
                for term in terms:
                    if term.casefold() not in obs.casefold():
                        problems.append(f"{fid}:required_term_not_in_observation:{oid}:{term}")
        elif profile == "planning.v1":
            codes = [s["action"] for s in exp["steps"]] + list(exp["uncertainties"])
            allowed = {a["action"] for a in fixture["input"]["allowed_actions"]}
            chosen = [s["action"] for s in exp["steps"]]
            excluded = {a for a in allowed if any(a.startswith(p) for p in p1.EXCLUDED_PREFIXES)}
            if set(chosen) != allowed - excluded or len(excluded) != 1 or len(chosen) != 4:
                problems.append(f"{fid}:plan_shape_not_normalized")
            evidence_text = " ".join(e["text"] for e in fixture["input"]["evidence"])
            if len(fixture["input"]["evidence"]) != 5:
                problems.append(f"{fid}:plan_evidence_count")
            held = [c for c in fixture["input"]["allowed_uncertainty_codes"]]
            if len(held) != 2 or len(exp["uncertainties"]) != 1:
                problems.append(f"{fid}:plan_uncertainty_shape")
        elif profile == "extraction.v1":
            for key, schema in fixture["input"]["schema"].items():
                if "|" in str(schema) and str(exp[key]) not in str(schema).split("|"):
                    problems.append(f"{fid}:enum_value_not_in_schema:{key}")
                if isinstance(exp[key], str) and "|" not in str(schema) and schema == "string":
                    if exp[key] not in fixture["input"]["text"]:
                        problems.append(f"{fid}:string_value_not_a_verbatim_span:{key}")
        elif profile == "coding.v1":
            for token in ("startswith", "PurePosixPath", ".parts", "raise", "helper functions"):
                if token not in fixture["prompt"]:
                    problems.append(f"{fid}:whitelist_not_fully_disclosed:{token}")
        for code in codes:
            if str(code) not in text:
                problems.append(f"{fid}:gold_code_not_model_visible:{code}")

patterns = defaultdict(lambda: defaultdict(set))
for corpus, fixture, gold, design in p1.FIXTURES:
    patterns[(design["task_class"], design["risk_class"])][corpus].add(design["pattern"])
for cell, per in patterns.items():
    shared = per["A"] & per["B"]
    if shared:
        problems.append(f"cell_pattern_shared:{cell}:{sorted(shared)}")

if problems:
    print("SELF-VALIDATION FAILED")
    for item in problems:
        print("  ", item)
    raise SystemExit(1)

OUT.mkdir(parents=True, exist_ok=True)
for corpus, role in (("A", "qualification"), ("B", "validation")):
    rows = sorted(by_corpus[corpus], key=lambda r: r[0]["fixture_id"])
    corpus_doc = {"schema_version": "g-route3.fixture-corpus.v1", "corpus_id": f"G-ROUTE3-CORPUS-{corpus}",
                  "corpus_role": role, "fixture_count": len(rows), "fixtures_per_cell": 2,
                  "task_classes": list(TASKS), "risk_classes": ["R1", "R2", "R3", "R4"],
                  "model_tiers": ["small", "mid", "large"], "model_input_contains_gold": False,
                  "fixtures": [r[0] for r in rows]}
    gold_doc = {"schema_version": "g-route3.gold.v1", "gold_id": f"G-ROUTE3-GOLD-{corpus}",
                "corpus_id": corpus_doc["corpus_id"], "model_input": False, "item_count": len(rows),
                "ambiguity_count": 0, "items": [r[1] for r in rows]}
    (OUT / f"corpus_{corpus.lower()}.json").write_text(
        json.dumps(corpus_doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (OUT / f"gold_{corpus.lower()}.json").write_text(
        json.dumps(gold_doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
design_doc = {"schema_version": "g-route3.fixture-design.v1", "model_input": False,
              "items": sorted((r[2] for rows in by_corpus.values() for r in rows), key=lambda d: d["fixture_id"])}
(OUT / "fixture_design.json").write_text(json.dumps(design_doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                                         encoding="utf-8", newline="\n")
alternatives = sum(len(r[1].get("alternative_correct_outputs", [])) for rows in by_corpus.values() for r in rows)
incorrect = sum(len(r[1].get("incorrect_outputs", [])) for rows in by_corpus.values() for r in rows)
print("SELF-VALIDATION PASSED")
print(f"  {alternatives} alternative correct answers accepted by both validators; {incorrect} incorrect answers rejected")
for corpus in ("A", "B"):
    print(f"  corpus {corpus}: {len(by_corpus[corpus])} fixtures")
