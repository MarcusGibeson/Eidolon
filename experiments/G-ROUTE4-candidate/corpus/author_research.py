"""Author the 136 frozen G-ROUTE4 Grounded Research slots.

Deterministic corpus authoring only, to the frozen blueprint at commit 1156d06. The script replays every name
already assigned to Extraction, Synthesis, Planning and Conversation, then continues the same global stream. It
contacts no model or adjudicator and creates no seal.

The model-facing records keep G-ROUTE3's research.v1 shape. A separate authoring ledger records each claim/source
binding, relation, scope and temporal role so check_corpus.py can reconstruct the gold without trusting it.

    python -B author_research.py
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools"))
from english_vocabulary import english_vocabulary  # noqa: E402
from names import NameBank  # noqa: E402

BLUEPRINT = json.loads((ROOT / "experiments/G-ROUTE4-candidate/blueprint/BLUEPRINT.json").read_text(
    encoding="utf-8"))
TEMPLATE = BLUEPRINT["templates"]["grounded_research_synthesis"]["assembled_template"]
SLOTS = [s for s in BLUEPRINT["slots"] if s["task_class"] == "grounded_research_synthesis"]
PRIOR_NAMES = ("extraction", "synthesis", "planning", "conversation")
PRIOR = [json.loads((HERE / f"staging/{name}.json").read_text(encoding="utf-8")) for name in PRIOR_NAMES]

FAMILY_SHAPE = {
    "RS1": (2, 3), "RS2": (2, 4), "RS3": (3, 4),
    "RS4": (2, 5), "RS5": (3, 5), "RS6": (3, 6),
}
UNCERTAINTY_CODES = [
    {"code": "single_lineage_support",
     "condition": "some claim with status supported is supported by exactly one lineage"},
    {"code": "unaddressed_claim", "condition": "some claim is addressed by no source"},
    {"code": "conflicting_sources",
     "condition": "some claim is unresolved because the sources addressing it disagree"},
    {"code": "scope_mismatch",
     "condition": "some claim is unresolved because its only addressing source covers a narrower scope than the claim"},
]

DOMAINS = [
    "archive room", "boat shed", "canal office", "dairy hall", "engine house", "field station",
    "grain store", "harbour office", "island workshop", "joinery room", "kiln house", "lamp depot",
    "museum store", "nursery office", "observatory annex", "packing house", "quarry office", "rail shed",
    "seed room", "tram workshop", "upland store", "visitor office", "weaving hall", "yard office",
]
ASSETS = [
    "access ledger", "batch register", "cooling permit", "dispatch board", "equipment certificate",
    "filter schedule", "gate record", "humidity report", "inspection permit", "junction register",
    "kiln certificate", "loading record", "mooring permit", "nutrient report", "opening licence",
    "packing certificate", "quality register", "rinse permit", "storage licence", "tool certificate",
    "usage register", "visitor permit", "water report", "yearly licence",
]
ACTIVITIES = [
    "annual inspection", "batch handover", "compliance review", "dispatch audit", "equipment survey",
    "filter inspection", "gate review", "harbour audit", "intake survey", "junction check", "kiln review",
    "loading audit", "mooring survey", "nursery review", "opening check", "packing audit", "quality survey",
    "rinse review", "storage audit", "tool survey", "usage review", "visitor check", "water audit",
    "year-end review",
]
INSTRUMENTS = [
    "amber gauge", "brass counter", "ceramic probe", "dial recorder", "enamel scale", "fibre sampler",
    "glass meter", "hinged ruler", "ink register", "jute marker", "kiln clock", "linen chart",
    "manual counter", "nickel gauge", "oak tablet", "paper recorder", "quartz scale", "reed marker",
    "steel probe", "timber gauge", "umber chart", "vellum register", "wax counter", "yarn scale",
]


def replay_names(bank):
    replayed = []
    for staged in PRIOR:
        for row in staged["design"]:
            for expected in row["invented_names"]:
                actual = bank.take()
                assert actual == expected, (row["fixture_id"], actual, expected)
                replayed.append(actual)
    return replayed


def claim_text(spec):
    if spec["kind"] == "scope":
        return (f"{spec['subject']} provides {spec['service']} at every {spec['site']} during "
                f"review cycle {spec['cycle']}.")
    if spec["kind"] == "quantity":
        return (f"{spec['subject']}'s {spec['asset']} carries at least {spec['threshold']} units during "
                f"review cycle {spec['cycle']}.")
    return (f"{spec['subject']}'s {spec['asset']} is approved for review cycle {spec['cycle']}.")


def denied_text(spec):
    assert spec["kind"] == "standard"
    return f"{spec['subject']}'s {spec['asset']} is not approved for review cycle {spec['cycle']}."


def source_statement(source, claims, alternate):
    spec = claims[int(source["claim_id"][1:]) - 1]
    relation = source["relation"]
    if relation == "support":
        statement = claim_text(spec)
    elif relation == "deny":
        statement = denied_text(spec)
    elif relation == "narrow":
        statement = (f"{spec['subject']} provides {spec['service']} only at the eastern {spec['site']} during "
                     f"review cycle {spec['cycle']}, not at every {spec['site']}.")
    elif relation == "other_subject":
        other = dict(spec)
        other["subject"] = alternate
        statement = claim_text(other)
    elif relation == "quantity_deny":
        statement = (f"{spec['subject']}'s {spec['asset']} carries {source['actual']} units during review cycle "
                     f"{spec['cycle']}, below {spec['threshold']} units.")
    else:
        raise ValueError(relation)
    if source.get("date"):
        statement = f"{source['date']} record: {statement}"
    return statement


def source_text(source, claims, alternate, context):
    statement = source_statement(source, claims, alternate)
    provenance = context["number"] * 1000 + int(source["source_id"][1:]) * 20
    return (f"{statement} {context['primary']} logged {context['secondary']}'s {context['domain']} record "
            f"{context['number']} evidence for "
            f"record {context['number']}-{source['source_id'][1:]}; {context['secondary']} indexed "
            f"{context['primary']}'s {context['activity']} record {context['number']} note with the "
            f"{context['instrument']} series {context['number']}. {context['primary']} cross-checked "
            f"{context['secondary']}'s {context['domain']} record {context['number']} folio against "
            f"{context['primary']}'s {context['instrument']} record {context['number']} docket for the "
            f"{context['activity']}. Provenance path: ledger {provenance + 1} joins folio {provenance + 2}, "
            f"shelf {provenance + 3}, packet {provenance + 4}, index {provenance + 5}, card {provenance + 6}, "
            f"marker {provenance + 7}, and docket {provenance + 8}.")


def make_claims(number, pattern, primary, secondary, count):
    claims = []
    for index in range(1, count + 1):
        subject = primary if index % 2 else secondary
        asset = ASSETS[(number * 5 + index * 7) % len(ASSETS)]
        spec = {"claim_id": f"C{index}", "kind": "standard", "subject": subject, "asset": asset,
                "cycle": 3000 + number * 7 + index}
        claims.append(spec)
    if pattern == "P6":
        claims[0] = {"claim_id": "C1", "kind": "scope", "subject": primary,
                     "service": f"calibration service {number}", "site": f"depot sector {number}",
                     "cycle": 3000 + number * 7 + 1}
    elif pattern == "P8":
        claims[0] = {"claim_id": "C1", "kind": "quantity", "subject": primary,
                     "asset": ASSETS[(number * 5 + 7) % len(ASSETS)], "threshold": 80 + number * 3,
                     "cycle": 3000 + number * 7 + 1}
    return claims


def make_sources(number, pattern, sls, claims, source_count):
    """Construct exact pattern evidence, then fill the family source count without changing the SLS flag."""
    def lineage(index):
        return f"route-four-research-{number:04d}-lineage-{index:02d}"

    rows = []
    if pattern == "P1":
        rows = [{"claim_id": "C1", "relation": "support", "lineage": lineage(1)},
                {"claim_id": "C1", "relation": "support", "lineage": lineage(2)}]
    elif pattern == "P2":
        rows = [{"claim_id": "C1", "relation": "deny", "lineage": lineage(1)}]
    elif pattern == "P3":
        rows = [{"claim_id": "C1", "relation": "other_subject", "lineage": lineage(1)}]
    elif pattern == "P4":
        rows = [{"claim_id": "C1", "relation": "support", "lineage": lineage(1)},
                {"claim_id": "C1", "relation": "support", "lineage": lineage(1)}]
        if not sls:
            rows.append({"claim_id": "C1", "relation": "support", "lineage": lineage(2)})
    elif pattern == "P5":
        rows = [{"claim_id": "C1", "relation": "support", "lineage": lineage(1)},
                {"claim_id": "C1", "relation": "deny", "lineage": lineage(2)}]
    elif pattern == "P6":
        rows = [{"claim_id": "C1", "relation": "narrow", "lineage": lineage(1)}]
    elif pattern == "P7":
        older, newer = 2040 + number, 2041 + number
        first, second = (("deny", "support") if number % 2 else ("support", "deny"))
        rows = [{"claim_id": "C1", "relation": first, "lineage": lineage(1),
                 "date": f"{older}-03-01"},
                {"claim_id": "C1", "relation": second, "lineage": lineage(2),
                 "date": f"{newer}-03-01"}]
    elif pattern == "P8":
        rows = [{"claim_id": "C1", "relation": "quantity_deny", "lineage": lineage(1),
                 "actual": claims[0]["threshold"] - 9},
                {"claim_id": "C1", "relation": "quantity_deny", "lineage": lineage(2),
                 "actual": claims[0]["threshold"] - 11}]
    else:
        raise ValueError(pattern)

    remaining = source_count - len(rows)
    fillers = [c["claim_id"] for c in claims[1:]]
    cursor = 0
    while remaining and fillers:
        claim_id = fillers[cursor % len(fillers)]
        existing = [r for r in rows if r["claim_id"] == claim_id]
        if sls:
            relation = "support"
            lin = existing[0]["lineage"] if existing else lineage(len(rows) + 1)
        else:
            relation = "deny"
            lin = lineage(len(rows) + 1)
        rows.append({"claim_id": claim_id, "relation": relation, "lineage": lin})
        remaining -= 1
        cursor += 1
    assert remaining == 0, (pattern, sls, len(claims), source_count)
    for index, row in enumerate(rows, 1):
        row["source_id"] = f"S{index}"
    return rows


def derive_gold(pattern, claims, sources, positive="accept_record", negative="hold_record"):
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
            raise AssertionError((cid, relations))
        results.append({"claim_id": cid, "status": status,
                        "citations": [s["source_id"] for s in about],
                        "lineages": sorted({s["lineage"] for s in about})})
        reasons[cid] = reason
    uncertainties = []
    if any(r["status"] == "supported" and len(r["lineages"]) == 1 for r in results):
        uncertainties.append("single_lineage_support")
    if "unaddressed" in reasons.values():
        uncertainties.append("unaddressed_claim")
    if "conflict" in reasons.values():
        uncertainties.append("conflicting_sources")
    if "scope" in reasons.values():
        uncertainties.append("scope_mismatch")
    if pattern in ("P1", "P4"):
        focal = results[0]
        eligible = focal["status"] == "supported" and len(focal["lineages"]) >= 2
    else:
        eligible = all(row["status"] == "supported" for row in results)
    return {"claims": results, "recommendation": positive if eligible else negative,
            "uncertainties": uncertainties}, reasons


def build():
    english, provenance = english_vocabulary()
    assert all(provenance == staged["english_vocabulary"] for staged in PRIOR)
    sys.path.insert(0, str(ROOT / "experiments/G-ROUTE4-candidate/blueprint"))
    import build_blueprint as B  # noqa: E402
    g3_entities, g3_lineages = B.g_route3_entity_inventory()
    bank = NameBank(english, set(g3_entities) | set(g3_lineages))
    replayed = replay_names(bank)
    assert PRIOR[-1]["name_sequence"]["last_conversation_ordinal"] == len(replayed)

    body = TEMPLATE[len("{SUBJECT}"):]
    fixtures, gold, design = [], [], []
    drawn = 0
    for number, slot in enumerate(SLOTS, 1):
        fid, family = slot["fixture_id"], slot["family"]
        pattern, sls = slot["features"]["pattern"], slot["features"]["sls"]
        claim_count, source_count = FAMILY_SHAPE[family]
        primary, secondary = bank.take(), bank.take()
        first_ordinal = len(replayed) + drawn + 1
        drawn += 2
        domain = DOMAINS[(number - 1) % len(DOMAINS)]
        activity = ACTIVITIES[(number * 7) % len(ACTIVITIES)]
        instrument = INSTRUMENTS[(number * 11) % len(INSTRUMENTS)]
        claims = make_claims(number, pattern, primary, secondary, claim_count)
        source_specs = make_sources(number, pattern, sls, claims, source_count)
        context = {"number": number, "domain": domain, "activity": activity, "instrument": instrument,
                   "primary": primary, "secondary": secondary}
        input_claims = [{"claim_id": c["claim_id"], "text": claim_text(c)} for c in claims]
        input_sources = [{"source_id": s["source_id"], "lineage": s["lineage"],
                          "text": source_text(s, claims, secondary, context)} for s in source_specs]
        if pattern in ("P1", "P4"):
            decision = (f"Recommend 'accept_record' only if C1 in {primary}'s record is supported by at least two "
                        "lineages; otherwise 'hold_record'.")
        elif pattern == "P7":
            governing = (
                f"When dated sources in {primary}'s record disagree about the same claim, the later-dated source "
                f"governs and all addressing sources are cited. Recommend 'accept_record' only if {secondary}'s "
                "check leaves every claim supported after that rule; otherwise 'hold_record'.",
                f"For {primary}'s record, if dated sources conflict on one claim, the source carrying the later "
                f"calendar date governs and both are cited. Recommend 'accept_record' only if {secondary}'s review "
                "then finds all claims supported; otherwise 'hold_record'.",
                f"In {primary}'s record, a disagreement between dated sources is settled by the chronologically "
                f"newer source while every addressing source is cited. Recommend 'accept_record' only if "
                f"{secondary}'s check then leaves each claim supported; otherwise 'hold_record'.",
                f"For the record kept by {primary}, sources that disagree on a claim are governed by the source "
                f"with the most recent date, with both cited. Recommend 'accept_record' only if {secondary}'s "
                "review consequently marks every claim supported; otherwise 'hold_record'.",
            )
            decision = governing[number % len(governing)]
        else:
            decision = (f"Recommend 'accept_record' only if every claim in {primary}'s record is supported; "
                        "otherwise 'hold_record'.")
        expected, reasons = derive_gold(pattern, claims, source_specs)
        realized_sls = "single_lineage_support" in expected["uncertainties"]
        assert realized_sls is sls, (fid, sls, expected)
        opening = f"Assess evidence record {number} for {primary} at the {domain}"
        prompt = TEMPLATE.replace("{SUBJECT}", opening)
        assert prompt == opening + body
        inp = {
            "allowed_recommendations": ["accept_record", "hold_record"],
            "allowed_uncertainty_codes": UNCERTAINTY_CODES,
            "claims": input_claims,
            "decision_rule": decision,
            "sources": input_sources,
        }
        rationale = ("; ".join(f"{row['claim_id']} is {row['status']} ({reasons[row['claim_id']]}) and cites "
                               f"{','.join(row['citations']) or 'no source'} across "
                               f"{len(row['lineages'])} lineage(s)" for row in expected["claims"]) +
                     f". The decision rule yields {expected['recommendation']}; uncertainty codes are "
                     f"{expected['uncertainties'] or []}.")
        fixtures.append({
            "consequence_risk": slot["risk"], "fixture_id": fid, "input": inp, "prompt": prompt,
            "task_class": "grounded_research_synthesis",
            "title": f"Evidence assessment {number} for {primary} at the {domain}",
            "validator_profile": "research.v1",
        })
        gold.append({"expected": expected, "fixture_id": fid, "rationale": rationale,
                     "reference_output": expected})
        design.append({
            "fixture_id": fid, "phase": slot["phase"], "role": slot["role"], "risk": slot["risk"],
            "family": family, "features": slot["features"], "invented_names": [primary, secondary],
            "identifiers": [], "global_name_ordinals": [first_ordinal, first_ordinal + 1],
            "research_contract": {"context": context, "claims": claims, "sources": source_specs,
                                  "derived_reasons": reasons},
        })
    return {
        "schema_version": "g-route4.authoring-staging.v1", "task_class": "grounded_research_synthesis",
        "blueprint_commit": "1156d06", "status": "authored, not sealed, not adjudicated",
        "english_vocabulary": provenance,
        "name_sequence": {"names_replayed": len(replayed), "first_research_ordinal": len(replayed) + 1,
                          "last_research_ordinal": len(replayed) + drawn},
        "missing_slots": sorted({s["fixture_id"] for s in SLOTS} - {f["fixture_id"] for f in fixtures}),
        "fixtures": fixtures, "gold": gold, "design": design,
    }


if __name__ == "__main__":
    output = build()
    path = HERE / "staging/research.json"
    path.write_text(json.dumps(output, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(output['fixtures'])} fixtures written; missing slots: {output['missing_slots']}")
    print("name sequence", output["name_sequence"])
