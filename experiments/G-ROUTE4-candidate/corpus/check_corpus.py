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
import g_route1_validators as G1V  # noqa: E402  (read-only; N1 canonical research gold)
from g_route3_operational import validate_operational  # noqa: E402
from g_route3_semantics import validate_fixture_output  # noqa: E402
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
SYNTHESIS_CONCLUSION = {
    "SY1": "cause_established", "SY2": "cause_unresolved", "SY3": "insufficient_evidence",
    "SY4": "decision_reserved", "SY5": "constraint_breached", "SY6": "behavior_by_design",
}
# Planning: forbidden prefixes are read from the frozen rule body itself; family counts from blueprint §2.
PLAN_FORBIDDEN = tuple(p.strip() for p in re.search(
    r"except those whose name begins with one of: ([a-z, ]+)\.",
    TEMPLATES["reflective_planning"]["rule_body"]).group(1).split(","))
PLAN_FAMILY = {"PL1": (4, 1, 1), "PL2": (3, 2, 0), "PL3": (5, 1, 2), "PL4": (4, 2, 1), "PL5": (3, 1, 1),
               "PL6": (5, 0, 1)}                   # included, excluded, holding codes
PLAN_FORM = {"before": "must precede", "after": "may start only after"}

RESEARCH_FAMILY = {
    "RS1": (2, 3), "RS2": (2, 4), "RS3": (3, 4),
    "RS4": (2, 5), "RS5": (3, 5), "RS6": (3, 6),
}
RESEARCH_RELATIONS = {"support", "deny", "narrow", "other_subject", "quantity_deny"}
RESEARCH_UNCERTAINTIES = [
    {"code": "single_lineage_support",
     "condition": "some claim with status supported is supported by exactly one lineage"},
    {"code": "unaddressed_claim", "condition": "some claim is addressed by no source"},
    {"code": "conflicting_sources",
     "condition": "some claim is unresolved because the sources addressing it disagree"},
    {"code": "scope_mismatch",
     "condition": "some claim is unresolved because its only addressing source covers a narrower scope than the claim"},
]


def research_claim_text(spec):
    if spec["kind"] == "scope":
        return (f"{spec['subject']} provides {spec['service']} at every {spec['site']} during "
                f"review cycle {spec['cycle']}.")
    if spec["kind"] == "quantity":
        return (f"{spec['subject']}'s {spec['asset']} carries at least {spec['threshold']} units during "
                f"review cycle {spec['cycle']}.")
    return f"{spec['subject']}'s {spec['asset']} is approved for review cycle {spec['cycle']}."


def research_source_statement(source, claims, alternate):
    spec = claims[int(source["claim_id"][1:]) - 1]
    relation = source["relation"]
    if relation == "support":
        statement = research_claim_text(spec)
    elif relation == "deny":
        statement = f"{spec['subject']}'s {spec['asset']} is not approved for review cycle {spec['cycle']}."
    elif relation == "narrow":
        statement = (f"{spec['subject']} provides {spec['service']} only at the eastern {spec['site']} during "
                     f"review cycle {spec['cycle']}, not at every {spec['site']}.")
    elif relation == "other_subject":
        other = dict(spec)
        other["subject"] = alternate
        statement = research_claim_text(other)
    elif relation == "quantity_deny":
        statement = (f"{spec['subject']}'s {spec['asset']} carries {source['actual']} units during review cycle "
                     f"{spec['cycle']}, below {spec['threshold']} units.")
    else:
        raise ValueError(relation)
    if source.get("date"):
        statement = f"{source['date']} record: {statement}"
    return statement


def research_source_text(source, claims, alternate, context):
    statement = research_source_statement(source, claims, alternate)
    provenance = context["number"] * 1000 + int(source["source_id"][1:]) * 20
    return (f"{statement} {context['primary']} logged {context['secondary']}'s {context['domain']} record "
            f"{context['number']} evidence for record {context['number']}-{source['source_id'][1:]}; "
            f"{context['secondary']} indexed {context['primary']}'s {context['activity']} record "
            f"{context['number']} note with the {context['instrument']} series {context['number']}. "
            f"{context['primary']} cross-checked {context['secondary']}'s {context['domain']} record "
            f"{context['number']} folio against {context['primary']}'s {context['instrument']} record "
            f"{context['number']} docket for the {context['activity']}. Provenance path: ledger {provenance + 1} "
            f"joins folio {provenance + 2}, shelf {provenance + 3}, packet {provenance + 4}, "
            f"index {provenance + 5}, card {provenance + 6}, marker {provenance + 7}, and "
            f"docket {provenance + 8}.")


def research_gold(pattern, claims, sources, recommendations):
    """Recompute research status, evidence bindings, recommendation and uncertainty codes from the ledger."""
    results, reasons = [], {}
    for claim in claims:
        cid = claim["claim_id"]
        about = [s for s in sources if s["claim_id"] == cid and s["relation"] != "other_subject"]
        relations = {s["relation"] for s in about}
        if not about:
            status, reason = "unresolved", "unaddressed"
        elif "support" in relations and "deny" in relations:
            if pattern == "P7" and cid == "C1":
                latest = max(about, key=lambda s: s.get("date", ""))
                status = "supported" if latest["relation"] == "support" else "contradicted"
                reason = "governing_source"
            else:
                status, reason = "unresolved", "conflict"
        elif relations == {"narrow"}:
            status, reason = "unresolved", "scope"
        elif "support" in relations:
            status, reason = "supported", "direct_support"
        elif relations & {"deny", "quantity_deny"}:
            status, reason = "contradicted", "direct_contradiction"
        else:
            raise ValueError(f"unrecognized research relation set for {cid}: {relations}")
        results.append({"claim_id": cid, "status": status,
                        "citations": [s["source_id"] for s in about],
                        "lineages": sorted({s["lineage"] for s in about})})
        reasons[cid] = reason
    uncertainties = []
    if any(row["status"] == "supported" and len(row["lineages"]) == 1 for row in results):
        uncertainties.append("single_lineage_support")
    if "unaddressed" in reasons.values():
        uncertainties.append("unaddressed_claim")
    if "conflict" in reasons.values():
        uncertainties.append("conflicting_sources")
    if "scope" in reasons.values():
        uncertainties.append("scope_mismatch")
    if pattern in ("P1", "P4"):
        eligible = results[0]["status"] == "supported" and len(results[0]["lineages"]) >= 2
    else:
        eligible = all(row["status"] == "supported" for row in results)
    expected = {"claims": results, "recommendation": recommendations[0 if eligible else 1],
                "uncertainties": uncertainties}
    return expected, reasons


CONVERSATION_KEYS = {
    ("CV1", 1): {"answer_options", "candidates", "message"},
    ("CV1", 2): {"answer_options", "candidates", "maximum", "message", "minimum"},
    ("CV2", 1): {"answer_options", "candidates", "duration_cap", "message", "target_minute"},
    ("CV2", 2): {"answer_options", "candidates", "checkpoint_minute", "message", "target_minute"},
    ("CV3", 1): {"answer_options", "candidates", "message", "source_cap", "target_converted"},
    ("CV3", 2): {"answer_options", "candidates", "message", "target_converted", "target_net"},
    ("CV4", 1): {"answer_options", "candidates", "message", "target_count", "target_secondary", "threshold"},
    ("CV4", 2): {"answer_options", "candidates", "message", "target_count", "target_secondary", "threshold"},
    ("CV5", 1): {"answer_options", "candidates", "message", "min_sample", "threshold"},
    ("CV5", 2): {"adjustment", "answer_options", "candidates", "final_threshold", "message", "raw_threshold"},
    ("CV6", 1): {"answer_options", "candidates", "message"},
    ("CV6", 2): {"answer_options", "candidates", "message", "required_priority"},
}


def conversation_conditions(family, depth, inp):
    """Independently recompute the two authoring conditions for every Conversation candidate."""
    candidates = inp.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != 4 or not all(isinstance(c, dict) for c in candidates):
        return [], ["candidates are not four objects"]
    expected_fields = {
        ("CV1", 1): {"condition_one", "condition_two"}, ("CV1", 2): {"adjustment", "base"},
        ("CV2", 1): {"duration", "start"}, ("CV2", 2): {"first_leg", "second_leg", "start"},
        ("CV3", 1): {"amount", "factor"}, ("CV3", 2): {"amount", "factor", "reserve"},
        ("CV4", 1): {"values"}, ("CV4", 2): {"values"},
        ("CV5", 1): {"denominator", "numerator", "sample_size"},
        ("CV5", 2): {"denominator", "numerator"},
        ("CV6", 1): {"exception_applies", "general_allowed", "priority"},
        ("CV6", 2): {"exception_applies", "general_allowed", "priority"},
    }[(family, depth)]
    errors, results = [], []
    for i, row in enumerate(candidates):
        if set(row) != expected_fields:
            errors.append(f"candidate {i + 1} keys differ from the family/depth construct")
            continue
        try:
            if family == "CV1" and depth == 1:
                pair = (row["condition_one"] is True, row["condition_two"] is True)
            elif family == "CV1":
                pair = (row["base"] >= inp["minimum"], row["base"] + row["adjustment"] <= inp["maximum"])
            elif family == "CV2" and depth == 1:
                arrival = row["start"] + row["duration"]
                pair = (arrival == inp["target_minute"], row["duration"] <= inp["duration_cap"])
            elif family == "CV2":
                first = row["start"] + row["first_leg"]
                pair = (first == inp["checkpoint_minute"], first + row["second_leg"] == inp["target_minute"])
            elif family == "CV3" and depth == 1:
                converted = row["amount"] * row["factor"]
                pair = (converted == inp["target_converted"], row["amount"] <= inp["source_cap"])
            elif family == "CV3":
                converted = row["amount"] * row["factor"]
                pair = (converted == inp["target_converted"], converted - row["reserve"] == inp["target_net"])
            elif family == "CV4":
                values = row["values"]
                if not isinstance(values, list) or not values:
                    raise TypeError("values must be a non-empty list")
                qualifying = [v for v in values if v >= inp["threshold"]]
                secondary = len(values) - len(qualifying) if depth == 1 else sum(qualifying)
                pair = (len(qualifying) == inp["target_count"], secondary == inp["target_secondary"])
            elif family == "CV5" and depth == 1:
                percentage = 100 * row["numerator"] / row["denominator"]
                pair = (percentage >= inp["threshold"], row["sample_size"] >= inp["min_sample"])
            elif family == "CV5":
                percentage = 100 * row["numerator"] / row["denominator"]
                pair = (percentage >= inp["raw_threshold"],
                        percentage - inp["adjustment"] >= inp["final_threshold"])
            elif family == "CV6" and depth == 1:
                pair = (row["general_allowed"] is True, row["exception_applies"] is False)
            else:
                pair = (row["general_allowed"] is True and row["priority"] >= inp["required_priority"],
                        row["exception_applies"] is False)
            results.append(pair)
        except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
            errors.append(f"candidate {i + 1} cannot be evaluated: {exc}")
    return results, errors


def plan_sentence(form, before, after):
    if form == "before":
        return f"{before[0].upper() + before[1:]} must precede {after}."
    return f"{after[0].upper() + after[1:]} may start only after {before}."


TYPE_TARGET = {"integer": 0.242, "boolean": 0.212, "string": 0.197, "enum2": 0.121, "date_or_time": 0.106,
               "number": 0.106, "enum3": 0.015}
CLASS_CAP = {"ordinary_conversation": 21}           # blueprint §4; every other class 13
CELL_CAP = {"ordinary_conversation": 9}             # every other class 6
IDENT = re.compile(r"([A-Z]{1,5}-?\d[\w.-]*)")
# Supplementary identifier screen. G-ROUTE3's frozen detector wraps its identifier pattern in literal backspace
# bytes (tools/g_route3_independence.py line 57), so its identifier branch never matches. This screen uses the
# evident intended pattern, is reported separately, and never replaces the frozen detector.
IDENT_INTENDED = re.compile(r"\b([A-Z]{1,5}-?\d[\w.-]*)\b")
STRUCTURAL_KEYS = {"id", "source_id", "claim_id", "statement_id", "addresses", "citations", "observation_ids",
                   "evidence_ids", "depends_on", "label", "option_label"}


def structural_ids(value, key=None):
    """Values of the design's structural-id fields that fully match [A-Z][0-9]+ (excluded by the design)."""
    out = set()
    if isinstance(value, dict):
        for k, v in value.items():
            out |= structural_ids(v, k)
    elif isinstance(value, list):
        for v in value:
            out |= structural_ids(v, key)
    elif isinstance(value, str) and key in STRUCTURAL_KEYS and re.fullmatch(r"[A-Z][0-9]+", value):
        out.add(value)
    return out


def intended_identifiers(fixture, text):
    skip = structural_ids(fixture.get("input", {}))
    return {m for m in IDENT_INTENDED.findall(text) if not re.fullmatch(r"[A-Z]\d", m) and m not in skip}


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
    report["composition"] = {
        tc: dict(sorted(collections.Counter(
            f"{SLOTS[f['fixture_id']]['phase']}_{SLOTS[f['fixture_id']]['role']}"
            for f in fixtures if f["task_class"] == tc
        ).items())) for tc in classes
    }
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
    plan_stats = collections.defaultdict(collections.Counter)
    conversation_stats = collections.defaultdict(collections.Counter)
    research_stats = collections.defaultdict(collections.Counter)
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
        if not str(g.get("rationale", "")).strip():
            problems.append(f"{fid}: no rationale")
        if tc == "structured_extraction" and g.get("reference_output") != g.get("expected"):
            problems.append(f"{fid}: extraction reference_output differs from expected")
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
        if tc == "grounded_research_synthesis":
            inp, expected = f["input"], g["expected"]
            family, pattern, sls = slot["family"], slot["features"]["pattern"], slot["features"]["sls"]
            contract = d.get("research_contract") if isinstance(d.get("research_contract"), dict) else {}
            claims = contract.get("claims") if isinstance(contract.get("claims"), list) else []
            sources = contract.get("sources") if isinstance(contract.get("sources"), list) else []
            context = contract.get("context") if isinstance(contract.get("context"), dict) else {}
            if set(inp) != {"allowed_recommendations", "allowed_uncertainty_codes", "claims",
                            "decision_rule", "sources"}:
                problems.append(f"{fid}: research input keys differ from the frozen construct")
                continue
            claim_count, source_count = RESEARCH_FAMILY[family]
            if len(inp.get("claims", [])) != claim_count or len(claims) != claim_count:
                problems.append(f"{fid}: research claim count differs from family {family}")
            if len(inp.get("sources", [])) != source_count or len(sources) != source_count:
                problems.append(f"{fid}: research source count differs from family {family}")
            claim_ids = [row.get("claim_id") for row in inp.get("claims", []) if isinstance(row, dict)]
            source_ids = [row.get("source_id") for row in inp.get("sources", []) if isinstance(row, dict)]
            if claim_ids != [f"C{i}" for i in range(1, claim_count + 1)] or \
                    any(not isinstance(row, dict) or set(row) != {"claim_id", "text"}
                        for row in inp.get("claims", [])):
                problems.append(f"{fid}: research claim identities or keys are invalid")
            if source_ids != [f"S{i}" for i in range(1, source_count + 1)] or \
                    any(not isinstance(row, dict) or set(row) != {"source_id", "lineage", "text"}
                        for row in inp.get("sources", [])):
                problems.append(f"{fid}: research source identities or keys are invalid")
            if inp.get("allowed_recommendations") != ["accept_record", "hold_record"]:
                problems.append(f"{fid}: research recommendations differ from the authored frozen pair")
            if inp.get("allowed_uncertainty_codes") != RESEARCH_UNCERTAINTIES:
                problems.append(f"{fid}: research uncertainty code contract differs from the frozen rules")
            if set(context) != {"number", "domain", "activity", "instrument", "primary", "secondary"} or \
                    [context.get("primary"), context.get("secondary")] != d.get("invented_names"):
                problems.append(f"{fid}: research context or invented-name binding is invalid")
            claim_spec_ids = [row.get("claim_id") for row in claims if isinstance(row, dict)]
            if claim_spec_ids != [f"C{i}" for i in range(1, claim_count + 1)]:
                problems.append(f"{fid}: research claim ledger binding is invalid")
            else:
                try:
                    rendered_claims = [{"claim_id": row["claim_id"], "text": research_claim_text(row)}
                                       for row in claims]
                except (KeyError, TypeError, ValueError) as exc:
                    problems.append(f"{fid}: research claim ledger cannot render: {exc}")
                    rendered_claims = []
                if rendered_claims != inp.get("claims"):
                    problems.append(f"{fid}: research claim text differs from its semantic ledger")
            source_spec_ids = [row.get("source_id") for row in sources if isinstance(row, dict)]
            allowed_source_keys = ({"source_id", "claim_id", "relation", "lineage"},
                                   {"source_id", "claim_id", "relation", "lineage", "date"},
                                   {"source_id", "claim_id", "relation", "lineage", "actual"})
            malformed_sources = [row for row in sources if not isinstance(row, dict) or set(row) not in allowed_source_keys]
            if source_spec_ids != [f"S{i}" for i in range(1, source_count + 1)] or malformed_sources:
                problems.append(f"{fid}: research source ledger identities or keys are invalid")
            if any(row.get("claim_id") not in set(claim_spec_ids) or row.get("relation") not in RESEARCH_RELATIONS
                   for row in sources if isinstance(row, dict)):
                problems.append(f"{fid}: research source ledger has an unknown binding or relation")
            if claim_spec_ids and source_spec_ids and not malformed_sources and set(context) == \
                    {"number", "domain", "activity", "instrument", "primary", "secondary"}:
                try:
                    rendered_sources = [{"source_id": row["source_id"], "lineage": row["lineage"],
                                         "text": research_source_text(row, claims, context["secondary"], context)}
                                        for row in sources]
                except (KeyError, TypeError, ValueError, IndexError) as exc:
                    problems.append(f"{fid}: research source ledger cannot render: {exc}")
                    rendered_sources = []
                if rendered_sources != inp.get("sources"):
                    problems.append(f"{fid}: research source text, lineage or binding differs from its semantic ledger")

            focal = [row for row in sources if isinstance(row, dict) and row.get("claim_id") == "C1"]
            relations = [row.get("relation") for row in focal]
            if pattern == "P1":
                pattern_ok = relations == ["support", "support"] and \
                    len({row.get("lineage") for row in focal}) == 2
            elif pattern == "P2":
                pattern_ok = relations == ["deny"]
            elif pattern == "P3":
                pattern_ok = relations == ["other_subject"]
            elif pattern == "P4":
                pattern_ok = relations[:2] == ["support", "support"] and len(focal) == (2 if sls else 3) and \
                    focal[0].get("lineage") == focal[1].get("lineage") and \
                    (sls or focal[2].get("lineage") != focal[0].get("lineage"))
            elif pattern == "P5":
                pattern_ok = relations == ["support", "deny"]
            elif pattern == "P6":
                pattern_ok = relations == ["narrow"]
            elif pattern == "P7":
                pattern_ok = set(relations) == {"support", "deny"} and len(focal) == 2
            elif pattern == "P8":
                pattern_ok = relations == ["quantity_deny", "quantity_deny"]
            else:
                pattern_ok = False
            if not pattern_ok:
                problems.append(f"{fid}: research focal evidence does not realize pattern {pattern}")
            decision_text = inp.get("decision_rule", "")
            p7_rule_ok = any(marker in decision_text for marker in (
                "later-dated source", "later calendar date governs", "chronologically newer source",
                "most recent date")) and "cited" in decision_text
            if pattern == "P7":
                dates = [row.get("date") for row in focal]
                if not all(isinstance(x, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", x) for x in dates) or \
                        dates != sorted(dates) or len(set(dates)) != 2 or not p7_rule_ok:
                    problems.append(f"{fid}: research temporal-governance relation is invalid")
                research_stats["temporal"]["governing_pairs"] += 1
            elif any("date" in row for row in sources if isinstance(row, dict)):
                problems.append(f"{fid}: dated research source appears outside P7")
            if pattern == "P6":
                if not claims or claims[0].get("kind") != "scope" or not focal or focal[0].get("relation") != "narrow":
                    problems.append(f"{fid}: research narrower-scope binding is invalid")
                research_stats["scope"]["narrower_scope_cases"] += 1
            elif any(row.get("relation") == "narrow" for row in sources if isinstance(row, dict)):
                problems.append(f"{fid}: narrower-scope source appears outside P6")
            if pattern == "P3" and (not focal or context.get("secondary") not in
                                    research_source_statement(focal[0], claims, context.get("secondary"))):
                problems.append(f"{fid}: research other-subject source is not bound to the alternate subject")
            if pattern == "P8":
                threshold = claims[0].get("threshold") if claims else None
                if not isinstance(threshold, int) or any(not isinstance(row.get("actual"), int) or
                                                         row["actual"] >= threshold for row in focal):
                    problems.append(f"{fid}: research quantitative contradiction does not fall below the threshold")
            try:
                recomputed, derived_reasons = research_gold(pattern, claims, sources,
                                                             inp.get("allowed_recommendations", []))
            except (KeyError, TypeError, ValueError, IndexError) as exc:
                problems.append(f"{fid}: research gold cannot be recomputed: {exc}")
                recomputed, derived_reasons = {}, {}
            if expected != recomputed:
                problems.append(f"{fid}: research gold differs from the statuses and evidence recomputed from input")
            if g.get("reference_output") != expected:
                problems.append(f"{fid}: research reference_output differs from expected")
            if contract.get("derived_reasons") != derived_reasons:
                problems.append(f"{fid}: research rationale ledger differs from recomputed reasons")
            realized_sls = "single_lineage_support" in recomputed.get("uncertainties", [])
            if realized_sls is not sls:
                problems.append(f"{fid}: research single_lineage_support outcome differs from the frozen feature")
            if pattern in ("P1", "P4"):
                decision_ok = "C1" in inp.get("decision_rule", "") and "two lineages" in inp.get("decision_rule", "")
            elif pattern == "P7":
                decision_ok = p7_rule_ok and any(word in decision_text for word in ("all claims", "every claim",
                                                                                    "each claim"))
            else:
                decision_ok = "every claim" in inp.get("decision_rule", "")
            if not decision_ok:
                problems.append(f"{fid}: research decision rule does not express the pattern's frozen decision")
            if recomputed:
                research_stats["status"].update(row["status"] for row in recomputed["claims"])
                research_stats["uncertainties"].update(recomputed["uncertainties"])
                research_stats["citations"]["cited_source_bindings"] += sum(len(row["citations"])
                                                                             for row in recomputed["claims"])
                research_stats["citations"]["distinct_lineage_bindings"] += sum(len(row["lineages"])
                                                                                  for row in recomputed["claims"])
            research_stats["families"][family] += 1
            research_stats["patterns"][pattern] += 1
            research_stats["sls"][str(sls).lower()] += 1
            research_stats[f"{slot['phase']}_{slot['role']}_{slot['risk']}_patterns"][pattern] += 1
            research_stats[f"{slot['phase']}_{slot['role']}_{slot['risk']}_sls"][str(sls).lower()] += 1
        elif tc == "ordinary_conversation":
            inp, expected = f["input"], g["expected"]
            family, depth = slot["family"], slot["features"]["depth"]
            if set(inp) != CONVERSATION_KEYS[(family, depth)]:
                problems.append(f"{fid}: conversation input keys differ from the family/depth construct")
                continue
            options = inp.get("answer_options")
            if not isinstance(options, list) or len(options) != 4:
                problems.append(f"{fid}: conversation must have exactly 4 answer options")
                options = options if isinstance(options, list) else []
            canonical = [canonical_value(v) for v in options]
            if len(canonical) != len(set(canonical)):
                problems.append(f"{fid}: conversation options are not pairwise distinct under canonical_value")
            if set(expected) != {"answer", "max_characters"} or expected.get("max_characters") != 600:
                problems.append(f"{fid}: conversation gold keys or max_characters differ from the frozen contract")
            position = slot["features"]["gold_position"] - 1
            if position >= len(options) or expected.get("answer") != options[position]:
                problems.append(f"{fid}: conversation gold answer is not at the frozen position")
            if options != d.get("invented_names"):
                problems.append(f"{fid}: conversation options differ from the declared global name draws")
            results, errors = conversation_conditions(family, depth, inp)
            for error in errors:
                problems.append(f"{fid}: conversation {error}")
            if len(results) == 4:
                gold_positions = [i for i, pair in enumerate(results) if pair == (True, True)]
                near_positions = [i for i, pair in enumerate(results) if pair == (True, False)]
                far_positions = [i for i, pair in enumerate(results) if pair == (False, False)]
                if gold_positions != [position]:
                    problems.append(f"{fid}: conversation recomputed gold positions {gold_positions} differ from "
                                    f"the frozen position {position}")
                if len(near_positions) != 1 or len(far_positions) != 2 or any(pair == (False, True)
                                                                             for pair in results):
                    problems.append(f"{fid}: conversation needs exactly one first-condition-only near miss and "
                                    "two zero-condition distractors")
                near_option = options[near_positions[0]] if len(near_positions) == 1 else None
                if d.get("near_miss_option") != near_option:
                    problems.append(f"{fid}: declared near-miss option differs from the recomputed near miss")
            if not isinstance(g.get("reference_output"), str):
                problems.append(f"{fid}: conversation reference output is not text")
            else:
                expected_prefix = f"Answer: {expected.get('answer')}\nActions taken: none\n"
                if not g["reference_output"].startswith(expected_prefix):
                    problems.append(f"{fid}: conversation reference does not use the exact disclosed frame")
            conversation_stats["families"][family] += 1
            conversation_stats["depth"][str(depth)] += 1
            conversation_stats[f"{slot['phase']}_{slot['role']}_positions"][str(position + 1)] += 1
            conversation_stats["near_miss"]["compliant"] += int(len(results) == 4 and
                                                                   results.count((True, False)) == 1 and
                                                                   results.count((False, False)) == 2 and
                                                                   results.count((True, True)) == 1)
        elif tc == "structured_extraction":
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
        elif tc == "hierarchical_semantic_synthesis":
            inp, expected, reference = f["input"], g["expected"], g["reference_output"]
            if set(inp) != {"allowed_conclusions", "conclusion_rule", "observations"}:
                problems.append(f"{fid}: synthesis input keys differ from the frozen construct")
                continue
            observations = inp["observations"] if isinstance(inp.get("observations"), list) else []
            ids = [str(row.get("id")) for row in observations if isinstance(row, dict)]
            roles = {str(row.get("id")): str(row.get("role")) for row in observations if isinstance(row, dict)}
            texts = {str(row.get("id")): str(row.get("text")) for row in observations if isinstance(row, dict)}
            band = slot["features"]["obs_band"]
            if len(observations) not in ({3, 4} if band == "small" else {5, 6}):
                problems.append(f"{fid}: synthesis observation count {len(observations)} differs from {band} band")
            if len(ids) != len(set(ids)) or any(set(row) != {"id", "role", "text"} for row in observations):
                problems.append(f"{fid}: synthesis observations have duplicate ids or wrong keys")
            counts = collections.Counter(roles.values())
            mergeable = sorted(n for n in counts.values() if n > 1)
            wanted_merge = slot["features"]["mergeable_pair"] == "yes"
            if wanted_merge != (mergeable == [2]):
                problems.append(f"{fid}: realized mergeable roles {mergeable} differ from plan")
            if set(expected) != {"conclusion", "required_terms", "roles"}:
                problems.append(f"{fid}: synthesis expected keys differ from G-ROUTE3 gold shape")
            if expected.get("roles") != roles or set(expected.get("required_terms", {})) != set(ids):
                problems.append(f"{fid}: synthesis gold roles or required-term bindings differ from observations")
            if expected.get("conclusion") not in inp.get("allowed_conclusions", []):
                problems.append(f"{fid}: synthesis conclusion is not allowed")
            if expected.get("conclusion") != SYNTHESIS_CONCLUSION.get(slot["family"]):
                problems.append(f"{fid}: synthesis conclusion differs from family semantics")
            for oid, terms in expected.get("required_terms", {}).items():
                if not isinstance(terms, list) or not terms or not all(str(term).casefold() in texts.get(oid, "").casefold()
                                                                      for term in terms):
                    problems.append(f"{fid}: required terms for {oid} are empty or not grounded")
            statements = reference.get("statements") if isinstance(reference, dict) else None
            if not isinstance(statements, list) or reference.get("conclusion") != expected.get("conclusion"):
                problems.append(f"{fid}: synthesis reference output has wrong shape or conclusion")
                statements = []
            covered, merged = [], []
            for row in statements:
                if not isinstance(row, dict) or set(row) != {"statement_id", "role", "observation_ids", "text"}:
                    problems.append(f"{fid}: synthesis reference statement has wrong keys")
                    continue
                bound = row["observation_ids"] if isinstance(row["observation_ids"], list) else []
                covered.extend(bound)
                bound_roles = {roles.get(str(oid)) for oid in bound}
                if None in bound_roles or len(bound_roles) != 1 or row["role"] not in bound_roles:
                    problems.append(f"{fid}: synthesis reference statement has mixed or incorrect roles")
                if not all(texts.get(str(oid), "") in str(row["text"]) for oid in bound):
                    problems.append(f"{fid}: synthesis reference statement does not preserve verbatim text")
                if len(bound) > 1:
                    merged.append(sorted(bound))
            if sorted(covered) != sorted(ids) or len(covered) != len(set(covered)):
                problems.append(f"{fid}: synthesis reference coverage is incomplete or duplicated")
            expected_merged = [sorted(oid for oid, role in roles.items() if role == repeated)
                               for repeated, n in counts.items() if n == 2]
            if sorted(merged) != sorted(expected_merged):
                problems.append(f"{fid}: synthesis reference merge does not match planned pair")
        elif tc == "reflective_planning":
            inp, expected = f["input"], g["expected"]
            family, form = slot["family"], slot["features"]["precedence_form"]
            if set(inp) != {"allowed_actions", "allowed_uncertainty_codes", "authority", "evidence", "objective"} \
                    or inp.get("authority") != "planning_only":
                problems.append(f"{fid}: planning input keys or authority differ from the frozen construct")
                continue
            if g.get("reference_output") != expected:
                problems.append(f"{fid}: planning reference_output differs from expected")
            if not isinstance(inp["objective"], str) or inp["objective"] not in opening:
                problems.append(f"{fid}: planning objective is not stated in the opening")
            evidence = {row["id"]: row["text"] for row in inp["evidence"]}
            eids = [row["id"] for row in inp["evidence"]]
            if len(set(eids)) != len(eids) or any(not re.fullmatch(r"F[1-9]", e) for e in eids):
                problems.append(f"{fid}: planning evidence ids are not distinct single-digit structural ids")
            actions = [row["action"] for row in inp["allowed_actions"]]
            addr = {row["action"]: list(row["addresses"]) for row in inp["allowed_actions"]}
            if len(set(actions)) != len(actions) or any(not re.fullmatch(r"[a-z][a-z0-9_]*", a) for a in actions):
                problems.append(f"{fid}: planning action names repeat or are not snake_case")
            if any(e not in evidence for a in addr for e in addr[a]):
                problems.append(f"{fid}: planning address cites unknown evidence")
            included = [a for a in actions if not a.startswith(PLAN_FORBIDDEN)]
            excluded = [a for a in actions if a.startswith(PLAN_FORBIDDEN)]
            n_in, n_ex, n_hold = PLAN_FAMILY[family]
            if (len(included), len(excluded)) != (n_in, n_ex):
                problems.append(f"{fid}: planning included/excluded counts {len(included)}/{len(excluded)} differ "
                                f"from family {family} ({n_in}/{n_ex})")
            if sorted(excluded) != sorted(d.get("excluded_actions", [])):
                problems.append(f"{fid}: declared excluded actions differ from the forbidden-prefix rule")
            # precedences: every pair stated in the slot's form, verbatim; none in the other form
            pairs, gerunds = d.get("precedence_pairs", []), d.get("gerunds", {})
            if set(gerunds) != set(included):
                problems.append(f"{fid}: planning gerund map does not cover exactly the included actions")
            for x, y, eid in pairs:
                if x not in gerunds or y not in gerunds or \
                        evidence.get(eid) != plan_sentence(form, gerunds[x], gerunds[y]):
                    problems.append(f"{fid}: precedence {x} -> {y} is not stated in the '{form}' form at {eid}")
            other = PLAN_FORM["after" if form == "before" else "before"]
            if any(other in t for t in evidence.values()):
                problems.append(f"{fid}: evidence uses the other precedence form ('{other}')")
            if sum(PLAN_FORM[form] in t for t in evidence.values()) != len(pairs):
                problems.append(f"{fid}: precedence statements in evidence differ from the declared pairs")
            succ = {x: y for x, y, _ in pairs}
            starts = [a for a in included if a not in succ.values()]
            order = []
            if len(starts) == 1 and len(succ) == len(pairs):
                a = starts[0]
                while a is not None and a not in order:
                    order.append(a)
                    a = succ.get(a)
            if sorted(order) != sorted(included) or len(order) != len(included):
                problems.append(f"{fid}: stated precedences do not give a unique total order of the included actions")
            listed = [eids.index(eid) for _, _, eid in pairs if eid in eids]
            if family == "PL4" and listed == sorted(listed):
                problems.append(f"{fid}: PL4 precedences are not listed out of order")
            if family != "PL4" and listed != sorted(listed):
                problems.append(f"{fid}: precedences listed out of order outside PL4")
            multi = [a for a in actions if len(addr[a]) > 1]
            if family == "PL5" and not (len(multi) == 1 and len(addr[multi[0]]) == 2 and
                                         all(len(addr[a]) == 1 for a in actions if a not in multi)):
                problems.append(f"{fid}: PL5 needs exactly one action addressing two evidence items, others one")
            if family != "PL5" and len(multi) == 1:
                problems.append(f"{fid}: exactly one multi-address action outside PL5 (PL5's marker)")
            # uncertainty codes: holding iff the evidence says the condition's subject is unknown
            codes, holding, bad = inp["allowed_uncertainty_codes"], [], False
            things = []
            for row in codes:
                m = re.fullmatch(r"evidence says (.+) is unknown", str(row.get("condition", "")))
                if not m or set(row) != {"code", "condition"}:
                    bad = True
                    continue
                things.append(m.group(1).casefold())
                if any(f"{m.group(1)} is unknown".casefold() in t.casefold() for t in evidence.values()):
                    holding.append(row["code"])
            if bad:
                problems.append(f"{fid}: planning uncertainty code without a parsable condition")
            if len(holding) != n_hold or len(codes) <= len(holding):
                problems.append(f"{fid}: {len(holding)} holding of {len(codes)} codes; family {family} needs "
                                f"{n_hold} holding and at least one non-holding")
            stray = [t for t in evidence.values() if " is unknown" in t
                     and not any(f"{th} is unknown" in t.casefold() for th in things)]
            if stray:
                problems.append(f"{fid}: evidence states an unknown that no offered code covers")
            recomputed = {
                "claims_completed": False, "requested_authority": [],
                "steps": [{"action": a, "depends_on": [] if i == 0 else [f"P{i}"],
                           "evidence_ids": sorted(addr[a]), "id": f"P{i + 1}"} for i, a in enumerate(order)],
                "uncertainties": sorted(holding)}
            if expected != recomputed:
                problems.append(f"{fid}: planning gold differs from the gold recomputed from input and the rule body")
            plan_stats[family]["fixtures"] += 1
            plan_stats[family]["multi_address_actions_" + str(len(multi))] += 1
            plan_stats["forms"][form] += 1
        # the frozen validators must accept the gold, operationally and semantically
        ref = g["reference_output"] if isinstance(g["reference_output"], str) else json.dumps(g["reference_output"])
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

    # ---- Research allocation, balance and reserve matching (blueprint research table and authoring rules)
    research_fixtures = [f for f in fixtures if f["task_class"] == "grounded_research_synthesis"]
    if research_fixtures:
        slots_r = [SLOTS[f["fixture_id"]] for f in research_fixtures]
        main_a = [s for s in slots_r if s["phase"] == "A" and s["role"] == "main"]
        main_b = [s for s in slots_r if s["phase"] == "B" and s["role"] == "main"]
        for risk, expected_patterns in BLUEPRINT["research_allocation"]["A"].items():
            actual = collections.Counter(s["features"]["pattern"] for s in main_a if s["risk"] == risk)
            if actual != collections.Counter(expected_patterns):
                problems.append(f"grounded_research_synthesis {risk}: A′ pattern allocation differs from blueprint")
            sls_count = sum(s["features"]["sls"] for s in main_a if s["risk"] == risk)
            if sls_count != 2:
                problems.append(f"grounded_research_synthesis {risk}: A′ does not contain exactly 2 SLS cases")
        for risk in ("R1", "R2", "R3"):
            expected_patterns = list(f"P{i}" for i in range(1, 9)) * 2 + \
                BLUEPRINT["research_allocation"]["B_extra_beyond_P1_P8_x2"][risk]
            cell = [s for s in main_b if s["risk"] == risk]
            actual = collections.Counter(s["features"]["pattern"] for s in cell)
            if actual != collections.Counter(expected_patterns):
                problems.append(f"grounded_research_synthesis {risk}: B′ pattern allocation differs from blueprint")
            if sum(s["features"]["sls"] for s in cell) != 9:
                problems.append(f"grounded_research_synthesis {risk}: B′ does not contain exactly 9 SLS cases")
            for pattern in (f"P{i}" for i in range(1, 9)):
                flags = {s["features"]["sls"] for s in cell if s["features"]["pattern"] == pattern}
                if flags != {False, True}:
                    problems.append(f"grounded_research_synthesis {risk} {pattern}: B′ lacks both SLS states")
        r4 = [s for s in main_b if s["risk"] == "R4"]
        if len(r4) != 1 or r4[0]["features"] != {"pattern": "P7", "sls": True}:
            problems.append("grounded_research_synthesis R4: B′ is not the frozen P7/SLS evidence-only case")

        reserves = [s for s in slots_r if s["role"] == "reserve"]
        unmatched = []
        for reserve in reserves:
            matches = [s for s in slots_r if s["phase"] == reserve["phase"] and s["risk"] == reserve["risk"] and
                       s["role"] == "main" and s["features"] == reserve["features"] and
                       (reserve["phase"] == "B" or s["family"] == reserve["family"])]
            if not matches:
                unmatched.append(reserve["fixture_id"])
        if unmatched:
            problems.append(f"grounded_research_synthesis reserves without a matching main slot: {sorted(unmatched)}")
        lineages = [(f["fixture_id"], row["lineage"]) for f in research_fixtures for row in f["input"]["sources"]]
        lineage_owners = collections.defaultdict(set)
        for fid, lineage in lineages:
            lineage_owners[lineage].add(fid)
        repeated_across = {lineage: sorted(owners) for lineage, owners in lineage_owners.items()
                           if len(owners) > 1}
        if repeated_across:
            problems.append(f"grounded_research_synthesis lineages repeat across fixtures: {repeated_across}")
        report["research"] = {
            "families": dict(sorted(research_stats["families"].items())),
            "patterns": dict(sorted(research_stats["patterns"].items())),
            "single_lineage_support": dict(sorted(research_stats["sls"].items())),
            "claim_status_balance": dict(sorted(research_stats["status"].items())),
            "uncertainty_balance": dict(sorted(research_stats["uncertainties"].items())),
            "cited_source_bindings": research_stats["citations"]["cited_source_bindings"],
            "distinct_lineage_bindings": research_stats["citations"]["distinct_lineage_bindings"],
            "source_records": sum(len(f["input"]["sources"]) for f in research_fixtures),
            "unique_lineages": len(lineage_owners), "cross_fixture_lineage_repeats": len(repeated_across),
            "temporal_governing_pairs": research_stats["temporal"]["governing_pairs"],
            "narrower_scope_cases": research_stats["scope"]["narrower_scope_cases"],
            "reserves_checked": len(reserves), "reserve_mismatches": len(unmatched),
            "cell_patterns": {key.removesuffix("_patterns"): dict(sorted(value.items()))
                              for key, value in sorted(research_stats.items()) if key.endswith("_patterns")},
            "cell_sls": {key.removesuffix("_sls"): dict(sorted(value.items()))
                         for key, value in sorted(research_stats.items()) if key.endswith("_sls")},
        }

    # ---- Conversation balance, reserve matching and authoring-rule summary (blueprint sections 3, 5 and 8)
    conversation_fixtures = [f for f in fixtures if f["task_class"] == "ordinary_conversation"]
    if conversation_fixtures:
        positions = collections.defaultdict(collections.Counter)
        for f in conversation_fixtures:
            slot = SLOTS[f["fixture_id"]]
            answer = gold_by[f["fixture_id"]]["expected"]["answer"]
            try:
                position = f["input"]["answer_options"].index(answer) + 1
            except (KeyError, ValueError):
                continue
            positions[(slot["phase"], slot["role"], slot["risk"])][position] += 1
        for risk in ("R1", "R2", "R3", "R4"):
            if positions[("A", "main", risk)] != collections.Counter({1: 1, 2: 1, 3: 1, 4: 1}):
                problems.append(f"ordinary_conversation {risk}: A main gold positions are not 1/1/1/1")
        for risk in ("R1", "R2", "R3"):
            if positions[("B", "main", risk)] != collections.Counter({1: 7, 2: 7, 3: 7, 4: 7}):
                problems.append(f"ordinary_conversation {risk}: B main gold positions are not 7/7/7/7")
        if positions[("B", "main", "R4")] != collections.Counter({1: 1}):
            problems.append("ordinary_conversation R4: B main gold position is not the frozen position 1")

        authored_slots = [SLOTS[f["fixture_id"]] for f in conversation_fixtures]
        reserves = [s for s in authored_slots if s["role"] == "reserve"]
        unmatched = []
        for reserve in reserves:
            matches = [s for s in authored_slots if s["phase"] == reserve["phase"] and
                       s["risk"] == reserve["risk"] and s["role"] == "main" and
                       s["features"] == reserve["features"] and
                       (reserve["phase"] == "B" or s["family"] == reserve["family"])]
            if not matches:
                unmatched.append(reserve["fixture_id"])
        if unmatched:
            problems.append(f"ordinary_conversation reserves without a matching main slot: {sorted(unmatched)}")
        report["conversation"] = {
            "families": dict(sorted(conversation_stats["families"].items())),
            "depth": dict(sorted(conversation_stats["depth"].items())),
            "option_count": 4,
            "fixtures_with_four_options": sum(len(f["input"].get("answer_options", [])) == 4
                                              for f in conversation_fixtures),
            "gold_positions": {"|".join(key): dict(sorted(value.items()))
                               for key, value in sorted(positions.items())},
            "near_miss_compliant": conversation_stats["near_miss"]["compliant"],
            "reserves_checked": len(reserves), "reserve_mismatches": len(unmatched),
            "fine_signature": "none (declared in the design; conversation relies on reasoning-pattern review)",
        }

    # ---- planning action names unique across every planning fixture (blueprint §4), and against G-ROUTE3's
    plan_rows = [(f, "G4") for f in fixtures if f["task_class"] == "reflective_planning"]
    if plan_rows:
        plan_rows += [(f, "G3") for f, _ in g3_fixtures() if f["task_class"] == "reflective_planning"]
        action_owners = collections.defaultdict(set)
        for f, src in plan_rows:
            for row in f["input"]["allowed_actions"]:
                action_owners[row["action"]].add((src, f["fixture_id"]))
        repeated = {a: sorted(fid for _, fid in w) for a, w in action_owners.items()
                    if len({fid for _, fid in w}) > 1 and any(s == "G4" for s, _ in w)}
        for a, w in sorted(repeated.items()):
            problems.append(f"planning action name {a!r} repeated across fixtures: {w}")
        report["planning"] = {
            "families": {fam: dict(c) for fam, c in sorted(plan_stats.items()) if fam != "forms"},
            "precedence_forms": dict(plan_stats["forms"]),
            "g4_action_names": sum(1 for a, w in action_owners.items() if any(s == "G4" for s, _ in w)),
            "repeated_action_names": len(repeated),
            "forbidden_prefixes": list(PLAN_FORBIDDEN),
            "fine_signature": "exempt (declared in the design; planning and synthesis)"}

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
    # supplementary identifier screen (see IDENT_INTENDED): 0 shared, and every G-ROUTE4 identifier declared
    id_owners = collections.defaultdict(set)
    for f, _, src in pool:
        found = intended_identifiers(f, content[id(f)])
        for x in found:
            id_owners[x].add((src, f["fixture_id"]))
        if src == "G4":
            undeclared_ids = found - set(design_by[f["fixture_id"]]["identifiers"])
            if undeclared_ids:
                problems.append(f"{f['fixture_id']}: identifiers not declared (supplementary screen): "
                                f"{sorted(undeclared_ids)}")
    shared_ids = {x: sorted(fid for _, fid in w) for x, w in id_owners.items()
                  if len({fid for _, fid in w}) > 1 and any(src == "G4" for src, _ in w)}
    for x, w in sorted(shared_ids.items()):
        problems.append(f"O3 supplementary: shared identifier {x!r}: {w}")
    report["o3_identifiers_supplementary"] = {
        "g4_identifiers": len({x for x, w in id_owners.items() if any(s == "G4" for s, _ in w)}),
        "g3_identifiers": len({x for x, w in id_owners.items() if any(s == "G3" for s, _ in w)}),
        "shared": len(shared_ids),
        "note": "the frozen G-ROUTE3 detector's identifier branch never matches (literal backspace bytes); this "
                "supplementary screen uses the intended pattern and excludes the design's structural ids"}
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
        input_text = f["input"].get("text", "") if isinstance(f.get("input"), dict) else ""
        missing_ids = {i.rstrip(".") for i in IDENT.findall(input_text)} - set(d["identifiers"])
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

    # ---- N1 canonical gold uniqueness
    canon = collections.defaultdict(list)
    for f, g, src in pool:
        if f["task_class"] == "structured_extraction":
            value = g["expected"]
        elif f["task_class"] == "hierarchical_semantic_synthesis":
            value = {"roles": g["expected"]["roles"], "conclusion": g["expected"]["conclusion"]}
        elif f["task_class"] == "reflective_planning":
            value = g["expected"]
        elif f["task_class"] == "ordinary_conversation":
            value = canonical_value(g["expected"]["answer"]).casefold()
        elif f["task_class"] == "grounded_research_synthesis":
            normalization_reasons = []
            value = G1V._normalize_research(g["expected"], normalization_reasons)
            if normalization_reasons:
                problems.append(f"{f['fixture_id']}: N1 research gold cannot be normalized: "
                                f"{normalization_reasons}")
        else:
            continue
        canon[json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)].append(
            (src, f["fixture_id"]))
    dup = [[fid for _, fid in owners] for owners in canon.values()
           if len(owners) > 1 and any(src == "G4" for src, _ in owners)]
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
