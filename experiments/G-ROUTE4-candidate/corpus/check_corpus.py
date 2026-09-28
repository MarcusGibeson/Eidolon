"""G-ROUTE4 authoring checker (corpus stage; not part of the governed runtime).

Checks authored fixtures against the FROZEN blueprint (experiments/G-ROUTE4-candidate/blueprint, commit 1156d06)
and the accepted design's authoring rules. It never changes a rule: every failure is reported, and a rule that
cannot be met is a conflict to report, not to relax.

It uses G-ROUTE3's own tokenizer, entity detector and content function (read-only), and the frozen G-ROUTE1 and
G-ROUTE3 validators, so the checks are the ones the design names. The pool is fixed per the design: all authored
G-ROUTE4 fixtures (main and reserve) plus G-ROUTE3's A and B fixtures.

    python -B check_corpus.py staging/extraction.json [...]   # writes staging/CHECK_REPORT.json; exit 1 on failure
"""

import collections
import hashlib
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools"))
import g_route3_independence as I  # noqa: E402  (read-only)
from g_route1_operational import validate_operational  # noqa: E402
from g_route1_validators import validate_fixture_output  # noqa: E402
from g_route3_conversation import canonical_value  # noqa: E402

BP_DIR = ROOT / "experiments/G-ROUTE4-candidate/blueprint"
BLUEPRINT = json.loads((BP_DIR / "BLUEPRINT.json").read_text(encoding="utf-8"))
TEMPLATES = BLUEPRINT["templates"]
SLOTS = {s["fixture_id"]: s for s in BLUEPRINT["slots"]}
EXTR = TEMPLATES["structured_extraction"]
ABSENCE = EXTR["absence_sentence"]
PINNED = [t["rule_body"] for t in TEMPLATES.values()] + \
    [t["disclosure_sentence"] for t in TEMPLATES.values() if t["disclosure_sentence"]] + [ABSENCE]
FAMILY_TYPE = {"EX1": "string", "EX2": "date_or_time", "EX3": "number", "EX4": "boolean", "EX5": "enum2",
               "EX6": "enum3"}
TYPE_TARGET = {"integer": 0.242, "boolean": 0.212, "string": 0.197, "enum2": 0.121, "date_or_time": 0.106,
               "number": 0.106, "enum3": 0.015}
CLASS_CAP = {"ordinary_conversation": 21}           # blueprint §4; every other class 13
CELL_CAP = {"ordinary_conversation": 9}             # every other class 6
IDENT = re.compile(r"([A-Z]{1,5}-?\d[\w.-]*)")


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def abstract_type(schema_type: str) -> str:
    return I._field_type(schema_type)


def derived_measure(fixture) -> int:
    """G-ROUTE3's measure, frozen as the definition of derived_count."""
    return sum(f"{key} is " in fixture["prompt"] for key in fixture["input"]["schema"])


def g3_fixtures():
    out = []
    for c in ("a", "b"):
        corpus = json.loads((ROOT / f"experiments/G-ROUTE3-candidate/corpus_{c}.json").read_text(encoding="utf-8"))
        gold = {g["fixture_id"]: g for g in json.loads((ROOT / f"experiments/G-ROUTE3-candidate/gold_{c}.json")
                                                       .read_text(encoding="utf-8"))["items"]}
        for f in corpus["fixtures"]:
            out.append((f, gold[f["fixture_id"]]))
    return out


def o6_values(fixture, gold):
    """The frozen O6 compared values (blueprint §7), path-scoped, canonicalized: {value: path}."""
    vals = {}
    tc, inp = fixture["task_class"], fixture["input"]

    def leaves(x, path):
        if isinstance(x, str):
            yield path, x
        elif isinstance(x, list):
            for i, y in enumerate(x):
                yield from leaves(y, f"{path}[{i}]")
        elif isinstance(x, dict):
            for k, y in x.items():
                yield from leaves(y, f"{path}.{k}")
    pairs = []
    if tc == "ordinary_conversation":
        for k, v in inp.items():
            if k != "message":
                pairs += list(leaves(v, f"input.{k}"))
    elif tc == "structured_extraction":
        for k, t in inp["schema"].items():
            if "|" not in str(t) and isinstance(gold["expected"].get(k), str):
                pairs.append((f"expected.{k}", gold["expected"][k]))
    elif tc == "reflective_planning":
        pairs += [(f"input.allowed_actions[{i}].action", a["action"]) for i, a in
                  enumerate(inp.get("allowed_actions", []))]
        if isinstance(inp.get("objective"), str):
            pairs.append(("input.objective", inp["objective"]))
    elif tc == "grounded_research_synthesis":
        pairs += [(f"input.sources[{i}].lineage", s["lineage"]) for i, s in enumerate(inp.get("sources", []))]
    for path, v in pairs:
        if v.strip():
            vals[canonical_value(v).casefold()] = path
    return vals


def check(staged, english=None):
    problems, report = [], collections.OrderedDict()
    fixtures = [f for s in staged for f in s["fixtures"]]
    gold_by = {g["fixture_id"]: g for s in staged for g in s["gold"]}
    design_by = {d["fixture_id"]: d for s in staged for d in s["design"]}
    ids = [f["fixture_id"] for f in fixtures]
    if len(set(ids)) != len(ids):
        problems.append("duplicate fixture ids")
    classes = sorted({f["task_class"] for f in fixtures})
    report["classes_checked"] = classes
    for tc in classes:
        want = sorted(fid for fid, s in SLOTS.items() if s["task_class"] == tc)
        have = sorted(f["fixture_id"] for f in fixtures if f["task_class"] == tc)
        if want != have:
            problems.append(f"{tc}: authored ids differ from the blueprint slots "
                            f"(missing {sorted(set(want) - set(have))}, extra {sorted(set(have) - set(want))})")

    # ---- pinned text digests (blueprint §6)
    ex_prompts = [f["prompt"] for f in fixtures if f["task_class"] == "structured_extraction"]
    if ex_prompts:
        if sha(EXTR["assembled_template"]) != EXTR["assembled_template_sha256"]:
            problems.append("EXTR assembled template digest mismatch")
        if sha(EXTR["disclosure_sentence"]) != "2d62848e72c42c00be38bbbe927730b322f846e919c015276b1aa7643ef57bf6":
            problems.append("EXTR sentence digest mismatch")
        if sha(ABSENCE) != "d8b760630cea0af5d2612fa208bd4afc46f7d17646ab4343129a79ec6781f6d8":
            problems.append("absence sentence digest mismatch")

    # ---- per-fixture structure
    type_counts = {"A": collections.Counter(), "B": collections.Counter()}
    absence_values = collections.Counter()
    for f in fixtures:
        fid = f["fixture_id"]
        slot, g, d = SLOTS.get(fid), gold_by.get(fid), design_by.get(fid)
        if slot is None or g is None or d is None:
            problems.append(f"{fid}: missing slot, gold or design record")
            continue
        tc = slot["task_class"]
        if f["task_class"] != tc or f["consequence_risk"] != slot["risk"]:
            problems.append(f"{fid}: class or risk differs from the slot")
        if (d["family"], d["features"], d["phase"], d["role"]) != (slot["family"], slot["features"], slot["phase"],
                                                                  slot["role"]):
            problems.append(f"{fid}: design record differs from the slot")
        if set(f) != {"consequence_risk", "fixture_id", "input", "prompt", "task_class", "title",
                      "validator_profile"}:
            problems.append(f"{fid}: fixture keys differ from G-ROUTE3's fixture shape")
        if g.get("reference_output") != g.get("expected") or not str(g.get("rationale", "")).strip():
            problems.append(f"{fid}: reference_output differs from expected, or no rationale")
        if tc == "structured_extraction" and set(g["expected"]) != set(f["input"]["schema"]):
            problems.append(f"{fid}: gold keys differ from the schema keys")
            continue
        if tc == "structured_extraction" and not set(d["derived_keys"]) <= set(f["input"]["schema"]):
            problems.append(f"{fid}: declared derived keys are not schema keys")
            continue
        tpl = TEMPLATES[tc]["assembled_template"]
        body = tpl[len("{SUBJECT}"):]
        if not f["prompt"].endswith(body) or f["prompt"].count(body) != 1:
            problems.append(f"{fid}: prompt is not opening + the frozen assembled template")
            continue
        opening = f["prompt"][: -len(body)]
        if opening.endswith(".") or opening != opening.strip():
            problems.append(f"{fid}: opening ends with a terminal period or whitespace")
        if TEMPLATES[tc]["disclosure_sentence"] and f["prompt"].count(TEMPLATES[tc]["disclosure_sentence"]) != 1:
            problems.append(f"{fid}: class disclosure sentence not present exactly once")
        if tc == "structured_extraction":
            schema = f["input"]["schema"]
            types = sorted(abstract_type(str(t)) for t in schema.values())
            plan = sorted(slot["features"]["field_types"])
            type_counts[slot["phase"]].update(types)
            if types != plan:
                problems.append(f"{fid}: field types {types} != plan {plan}")
            if len(schema) != slot["features"]["field_count"]:
                problems.append(f"{fid}: field count differs from plan")
            if derived_measure(f) != slot["features"]["derived_count"]:
                problems.append(f"{fid}: derived measure {derived_measure(f)} != plan "
                                f"{slot['features']['derived_count']}")
            measured = sorted(k for k in schema if f"{k} is " in f["prompt"])
            if measured != sorted(d["derived_keys"]):
                problems.append(f"{fid}: keys defined by '<key> is' {measured} != declared {d['derived_keys']}")
            keys = list(schema)
            for a in keys:
                for b in keys:
                    if a != b and b.endswith(a):
                        problems.append(f"{fid}: key {a!r} is a suffix of key {b!r}")
                n = f["prompt"].count(f"{a} is ")
                if n > 1:
                    problems.append(f"{fid}: '{a} is ' occurs {n} times in the prompt")
                if n == 1 and f". {a} is " not in opening:
                    problems.append(f"{fid}: definition of {a} is not a sentence of the opening")
                if n == 1 and f". {a} is " in opening:
                    sentence = opening.split(f". {a} is ", 1)[1].split(". ")[0]
                    chained = [k for k in keys if k != a and f"{k} is " in sentence]
                    if chained:
                        problems.append(f"{fid}: chained definition in {a}: {chained}")
            if opening.split(". ")[0].split(" is ")[0] in keys:
                problems.append(f"{fid}: opening does not start with a subject sentence")
            has_absence_field = any(str(t) == "provided|not_provided" for t in schema.values())
            count = f["prompt"].count(ABSENCE[:-1])
            if count > 1 or has_absence_field != (count == 1):
                problems.append(f"{fid}: absence sentence count {count}, absence field present={has_absence_field}")
            if has_absence_field and not opening.endswith(ABSENCE[:-1]):
                problems.append(f"{fid}: the absence sentence is not the opening's last sentence")
            if has_absence_field:
                absence_values.update(v for k, v in g["expected"].items() if schema[k] == "provided|not_provided")
            # per-slot rules (blueprint §3), on the realized types
            c = collections.Counter(types)
            if FAMILY_TYPE[slot["family"]] not in c:
                problems.append(f"{fid}: family {slot['family']} lacks its required type")
            if slot["family"] == "EX5" and "provided|not_provided" not in map(str, schema.values()):
                problems.append(f"{fid}: EX5 without a provided|not_provided field")
            if c["boolean"] > (2 if slot["family"] in ("EX4", "EX6") else 1):
                problems.append(f"{fid}: too many boolean fields")
            if not (c["string"] or c["date_or_time"]):
                problems.append(f"{fid}: no string or date/time field")
            if max(c.values()) > 2:
                problems.append(f"{fid}: a type occurs more than twice")
            # verbatim support: every copied (non-derived, non-enum) value appears in the text as written
            for k, v in g["expected"].items():
                t = str(schema[k])
                if k in d["derived_keys"] or "|" in t or t == "boolean":
                    continue
                if str(v) not in f["input"]["text"]:
                    problems.append(f"{fid}: copied value {k}={v!r} not found verbatim in the text")
            for k in d["derived_keys"]:
                if str(schema[k]) == "string" and str(g["expected"][k]) not in f["input"]["text"]:
                    problems.append(f"{fid}: derived string {k} not found verbatim in the text")
        # the frozen validators must accept the gold, operationally and semantically
        ref = json.dumps(g["expected"])
        op = validate_operational(f, ref)
        if not op["accepted"]:
            problems.append(f"{fid}: operational validator rejects gold: {op.get('reasons')}")
        sem = validate_fixture_output(f, g, ref)
        if not sem.get("hard_gate_pass"):
            problems.append(f"{fid}: semantic validator rejects gold: {sem.get('reasons')}")
        if "integer" in json.dumps(f["input"].get("schema", {})):
            for k, t in f["input"]["schema"].items():
                if t == "integer" and not isinstance(g["expected"][k], int):
                    problems.append(f"{fid}: integer field {k} gold is not an int")
    if any(type_counts.values()):
        mix = {}
        for ph, cnt in type_counts.items():
            tot = sum(cnt.values())
            mix[ph] = {t: round(cnt[t] / tot, 3) for t in TYPE_TARGET} if tot else {}
        report["extraction_type_mix_realized"] = mix
        report["extraction_type_mix_max_deviation"] = round(max(abs(mix[p][t] - TYPE_TARGET[t])
                                                                for p in mix if mix[p] for t in TYPE_TARGET), 3)
        report["absence_field_gold_values"] = dict(absence_values)

    # ---- caps (blueprint §4)
    for tc in classes:
        slots_tc = [SLOTS[f["fixture_id"]] for f in fixtures if f["task_class"] == tc]
        b_main = [s for s in slots_tc if s["phase"] == "B" and s["role"] == "main"]
        a_main = [s for s in slots_tc if s["phase"] == "A" and s["role"] == "main"]
        fam = collections.Counter(s["family"] for s in b_main)
        if fam and max(fam.values()) > CLASS_CAP.get(tc, 13):
            problems.append(f"{tc}: class cap exceeded {dict(fam)}")
        for risk in ("R1", "R2", "R3", "R4"):
            cell = collections.Counter(s["family"] for s in b_main if s["risk"] == risk)
            if cell and max(cell.values()) > CELL_CAP.get(tc, 6):
                problems.append(f"{tc} {risk}: cell cap exceeded {dict(cell)}")
            a_cell = [s["family"] for s in a_main if s["risk"] == risk]
            if len(set(a_cell)) != len(a_cell):
                problems.append(f"{tc} {risk}: A′ families not distinct")
        report.setdefault("caps", {})[tc] = {"b_main_family_counts": dict(sorted(fam.items()))}

    # ---- fine signature: not repeated between A′ and B′ in a cell (research and extraction)
    by_cell = collections.defaultdict(lambda: {"A": [], "B": []})
    for f in fixtures:
        if f["validator_profile"] in ("extraction.v1", "research.v1"):
            s = I.structural_signature(f, gold_by[f["fixture_id"]]["expected"])
            by_cell[(f["task_class"], f["consequence_risk"])][SLOTS[f["fixture_id"]]["phase"]].append(
                (f["fixture_id"], s))
    clashes = [(a, b) for parts in by_cell.values() for a, sa in parts["A"] for b, sb in parts["B"] if sa == sb]
    for a, b in clashes:
        problems.append(f"fine signature repeated between A′ and B′ in a cell: {a} vs {b}")
    report["fine_signature_clashes"] = len(clashes)

    # ---- pool
    g3 = g3_fixtures()
    pool = [(f, gold_by[f["fixture_id"]], "G4") for f in fixtures] + [(f, g, "G3") for f, g in g3]
    content = {id(f): I._content(f) for f, _, _ in pool}
    # lowercase vocabulary per class pool (design: "computed over the pool"; O3: only this uses the class pool)
    vocab = collections.defaultdict(set)
    for f, _, src in pool:
        vocab[f["task_class"]] |= set(re.findall(r"(?<![A-Za-z])[a-z]+", content[id(f)]))
    g3_vocab_all = {w for f, _ in g3 for w in re.findall(r"(?<![A-Za-z])[a-z]+", I._content(f))}
    ents = {}
    for f, _, src in pool:
        e = I._named_entities(content[id(f)], vocab[f["task_class"]])
        if src == "G3":                                   # G-ROUTE3's own screen too, for the strictest set
            e |= I._named_entities(content[id(f)], g3_vocab_all)
        ents[f["fixture_id"]] = e
    owners = collections.defaultdict(set)
    for fid, e in ents.items():
        for x in e:
            owners[x].add(fid)
    shared = {x: sorted(w) for x, w in owners.items()
              if len(w) > 1 and any(v.startswith(("A4-", "B4-")) for v in w)}
    for x, w in sorted(shared.items()):
        problems.append(f"O3 shared named entity or identifier {x!r}: {w}")
    report["o3_entities"] = {"g4_fixtures": len(fixtures),
                             "g4_entities": len({x for f in fixtures for x in ents[f["fixture_id"]]}),
                             "g3_entities_compared": len({x for f, _ in g3 for x in ents[f["fixture_id"]]}),
                             "shared": len(shared), "scope": "all authored G-ROUTE4 fixtures of every class, "
                             "main and reserve, pairwise and against all G-ROUTE3 A and B fixtures"}
    # declared names: every detected entity is declared; cap 6; screens
    all_names = collections.Counter()
    g3_names = {x.casefold() for f, _ in g3 for x in ents[f["fixture_id"]]}
    g3_lineages = {s["lineage"].casefold() for f, _ in g3 for s in f["input"].get("sources", [])
                   if isinstance(s, dict) and "lineage" in s}
    for f in fixtures:
        d = design_by[f["fixture_id"]]
        declared = set(d["invented_names"]) | set(d["identifiers"])
        undeclared = ents[f["fixture_id"]] - declared
        if undeclared:
            problems.append(f"{f['fixture_id']}: detected entities not declared as invented: {sorted(undeclared)}")
        if len(d["invented_names"]) + len(d["identifiers"]) > 6:
            problems.append(f"{f['fixture_id']}: more than 6 new names and identifiers")
        missing_ids = set(IDENT.findall(f["input"]["text"])) - set(d["identifiers"])
        if missing_ids:
            problems.append(f"{f['fixture_id']}: identifiers in the text not declared: {sorted(missing_ids)}")
        for n in d["invented_names"]:
            all_names[n] += 1
            low = n.lower()
            if english is not None and low in english:
                problems.append(f"{f['fixture_id']}: invented name {n} is an English word")
            if low in vocab[f["task_class"]]:
                problems.append(f"{f['fixture_id']}: invented name {n} occurs in lowercase in the pool vocabulary")
            if low in g3_names or low in g3_lineages:
                problems.append(f"{f['fixture_id']}: invented name {n} matches a G-ROUTE3 entity or lineage")
    for n, k in all_names.items():
        if k > 1:
            problems.append(f"invented name {n} used in {k} fixtures")
    report["names"] = {"invented_names": sum(all_names.values()),
                       "max_per_fixture": max((len(design_by[f["fixture_id"]]["invented_names"]) +
                                               len(design_by[f["fixture_id"]]["identifiers"]) for f in fixtures),
                                              default=0),
                       "english_vocabulary_screen": english is not None}

    # ---- trigram Jaccard per class pool, after pinned-text removal and the 25%-frequency boilerplate rule
    pin = set()
    for text in PINNED:
        pin |= I._trigrams(text)
    by_class = collections.defaultdict(list)
    for f, g, src in pool:
        by_class[f["task_class"]].append((f["fixture_id"], src, I._trigrams(content[id(f)]) - pin))
    report["trigram"] = {}
    for tc in classes:
        rows = by_class[tc]
        freq = collections.Counter(tg for _, _, s in rows for tg in s)
        boiler = {tg for tg, n in freq.items() if n >= I.BOILERPLATE_SHARE * len(rows)}
        sets = [(fid, src, s - boiler) for fid, src, s in rows]
        best, over = (0.0, "", ""), 0
        for i in range(len(sets)):
            for j in range(i + 1, len(sets)):
                a, b = sets[i], sets[j]
                if a[1] == "G3" and b[1] == "G3":
                    continue
                u = a[2] | b[2]
                jac = len(a[2] & b[2]) / len(u) if u else 0.0
                if jac > best[0]:
                    best = (jac, a[0], b[0])
                if jac > I.MAX_CROSS_CORPUS_TRIGRAM_JACCARD:
                    over += 1
                    problems.append(f"trigram Jaccard {jac:.3f} > 0.20: {a[0]} vs {b[0]}")
        # O5: no boilerplate trigram specific to a single family
        fam_of = {fid: SLOTS[fid]["family"] for fid, src, _ in rows if src == "G4"}
        single = []
        for tg in boiler:
            fams = {fam_of[fid] for fid, src, s in rows if src == "G4" and tg in s}
            if len(fams) == 1:
                single.append((" ".join(tg), fams.pop()))
        for tg, fam in single:
            problems.append(f"O5: boilerplate trigram '{tg}' is specific to family {fam}")
        report["trigram"][tc] = {"pool": len(rows), "boilerplate_trigrams": len(boiler),
                                 "max_jaccard": round(best[0], 4), "max_pair": best[1:], "pairs_over_bound": over,
                                 "o5_single_family_boilerplate": len(single)}

    # ---- O6 exact values, pooled across all classes and against G-ROUTE3 (G3-G3 duplicates not counted)
    owners6 = collections.defaultdict(set)
    compared = collections.Counter()
    for f, g, src in pool:
        for v, path in o6_values(f, g).items():
            owners6[v].add((src, f["fixture_id"], path))
            if src == "G4":
                compared[f["task_class"]] += 1
    collisions = []
    for v, who in sorted(owners6.items()):
        fids = {w[1] for w in who}
        if len(fids) > 1 and any(src == "G4" for src, _, _ in who):
            collisions.append((v, sorted(fids)))
            problems.append(f"O6 shared value {v!r}: {sorted(fids)}")
    report["o6"] = {"g4_values_compared_by_class": dict(compared), "collisions": len(collisions),
                    "pool": "all classes pooled; G-ROUTE4 main and reserve plus all G-ROUTE3 A and B fixtures"}

    # ---- N1 canonical gold uniqueness (extraction: the expected object)
    canon = collections.defaultdict(list)
    for f, g, src in pool:
        if f["task_class"] == "structured_extraction":
            canon[json.dumps(g["expected"], sort_keys=True, separators=(",", ":"), ensure_ascii=False)].append(
                f["fixture_id"])
    dup = [w for w in canon.values() if len(w) > 1]
    for w in dup:
        problems.append(f"N1 identical canonical gold: {w}")
    report["n1_duplicates"] = len(dup)
    return problems, report


if __name__ == "__main__":
    staged = [json.loads(Path(p).read_text(encoding="utf-8")) for p in sys.argv[1:]]
    from english_vocabulary import english_vocabulary
    english, provenance = english_vocabulary()
    problems, report = check(staged, english)
    report["english_vocabulary"] = provenance
    report["problems"] = problems
    report["passed"] = not problems
    out = HERE / "staging" / "CHECK_REPORT.json"
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    for k, v in report.items():
        if k not in ("problems", "english_vocabulary"):
            print(k, json.dumps(v, ensure_ascii=False))
    for p in problems:
        print("FAIL", p)
    print(f"{sum(len(s['fixtures']) for s in staged)} fixtures checked; {len(problems)} problems")
    sys.exit(1 if problems else 0)
