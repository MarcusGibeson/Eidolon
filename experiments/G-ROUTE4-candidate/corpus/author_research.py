"""Author the 136 frozen G-ROUTE4 Grounded Research slots (pre-seal repair revision).

Deterministic corpus authoring only, to the frozen blueprint at commit 1156d06. It contacts no model or adjudicator
and creates no seal.

Repair revision (after the complete-corpus pre-seal review):
- claims are natural statements from per-risk topic libraries (research_topics.py); every source is an independent
  paraphrase, never the claim sentence and never the claim with "not" inserted; there is no provenance padding;
- P8 sources report a value only, never the threshold or the comparison, so the contradiction must be inferred;
- lineages are meaningful publisher names (region-issuer-channel), unique across the corpus; a repeated lineage is
  written as a reissue from the same publisher;
- P7: dated sources disagree and the later-dated source governs; wherever single_lineage_support must be false the
  later source denies, so the code's truth is the same whether lineages are counted as cited or as supporting;
- the opening follows the frozen constraint "Assess the claims about <subject>";
- fine signatures are compared on the canonical decision kind, so rewording a rule can never hide a repeated gold
  structure between A′ and B′ in a cell; filler composition is chosen to keep every cell clash-free;
- the invented-name stream is unchanged (two names per fixture, replayed from name_stream.json).

    python -B author_research.py
"""

import datetime as dt
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools"))
from name_stream import NameStream  # noqa: E402
import research_topics as RT  # noqa: E402

BLUEPRINT = json.loads((ROOT / "experiments/G-ROUTE4-candidate/blueprint/BLUEPRINT.json").read_text(encoding="utf-8"))
TEMPLATE = BLUEPRINT["templates"]["grounded_research_synthesis"]["assembled_template"]
SLOTS = [s for s in BLUEPRINT["slots"] if s["task_class"] == "grounded_research_synthesis"]
FAMILY_SHAPE = {"RS1": (2, 3), "RS2": (2, 4), "RS3": (3, 4), "RS4": (2, 5), "RS5": (3, 5), "RS6": (3, 6)}
UNCERTAINTY_CODES = [
    {"code": "single_lineage_support",
     "condition": "some claim with status supported is supported by exactly one lineage"},
    {"code": "unaddressed_claim", "condition": "some claim is addressed by no source"},
    {"code": "conflicting_sources",
     "condition": "some claim is unresolved because the sources addressing it disagree"},
    {"code": "scope_mismatch",
     "condition": "some claim is unresolved because its only addressing source covers a narrower scope than the claim"},
]
DECISION_KIND = {"P1": "focal_two_lineages", "P4": "focal_two_lineages", "P7": "temporal_all_supported"}
FOCAL_RULES = [
    "Recommend '{pos}' only if C1 is supported by at least two lineages; otherwise '{neg}'.",
    "Recommend '{pos}' only when C1 has support from two or more lineages; otherwise '{neg}'.",
    "Choose '{pos}' only if at least two lineages support C1; otherwise '{neg}'.",
    "Pick '{pos}' only if two or more independent lineages support C1; otherwise '{neg}'.",
    "Recommend '{pos}' if C1 is backed by at least two lineages, and '{neg}' otherwise.",
]
ALL_RULES = [
    "Recommend '{pos}' only if every claim is supported; otherwise '{neg}'.",
    "Recommend '{pos}' only when all claims are supported; otherwise '{neg}'.",
    "Choose '{pos}' only if each claim is supported; otherwise '{neg}'.",
    "Pick '{pos}' only when no claim is left unsupported; otherwise '{neg}'.",
    "Recommend '{pos}' if all of the claims are supported, and '{neg}' otherwise.",
]
TEMPORAL_RULES = [
    "When dated sources disagree about the same claim, the later-dated source governs and all addressing sources "
    "are cited. Recommend '{pos}' only if every claim is then supported; otherwise '{neg}'.",
    "If dated sources conflict on a claim, the source with the later date decides it, and every addressing source is "
    "still cited. Recommend '{pos}' only when all claims are then supported; otherwise '{neg}'.",
    "A conflict between dated sources is settled by the more recent one, with all addressing sources cited. Choose "
    "'{pos}' only if each claim is then supported; otherwise '{neg}'.",
    "Where two dated sources contradict each other on one claim, the newer of the two decides it; cite both. "
    "Pick '{pos}' only if no claim is left unsupported after that; otherwise '{neg}'.",
    "Dated sources that disagree are resolved in favour of the most recent date, and every source about the claim "
    "is cited. Recommend '{pos}' if all claims end up supported, and '{neg}' otherwise.",
    "For claims with conflicting dated sources, trust the one dated later while citing all of them. Recommend "
    "'{pos}' only when every claim comes out supported; otherwise '{neg}'.",
]


class Lineages:
    def __init__(self, avoid):
        combos = [f"{r}-{i}-{c}" for c in RT.LINEAGE_CHANNELS for i in RT.LINEAGE_ISSUERS for r in RT.LINEAGE_REGIONS]
        # spread consecutive draws across regions, issuers and channels
        self.pool = [x for k, x in sorted(enumerate(combos), key=lambda kv: (kv[0] * 7919) % len(combos))
                     if x not in avoid]
        self.i = 0

    def take(self):
        self.i += 1
        return self.pool[self.i - 1]


def derive_gold(pattern, claims, sources, recommendations):
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
        else:
            status, reason = "contradicted", "direct_contradiction"
        results.append({"claim_id": cid, "status": status, "citations": [s["source_id"] for s in about],
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
        eligible = results[0]["status"] == "supported" and len(results[0]["lineages"]) >= 2
    else:
        eligible = all(r["status"] == "supported" for r in results)
    return {"claims": results, "recommendation": recommendations[0 if eligible else 1],
            "uncertainties": uncertainties}, reasons


def sls_supporting_reading(claims, sources, expected):
    """single_lineage_support counting only the lineages of sources that support the claim."""
    for row in expected["claims"]:
        if row["status"] != "supported":
            continue
        supporting = {s["lineage"] for s in sources if s["claim_id"] == row["claim_id"] and s["relation"] == "support"}
        if len(supporting) == 1:
            return True
    return False


DECISION_CLASS = {"focal_two_lineages": "focal_c1_two_lineages", "all_supported": "every_claim_supported",
                  "temporal_all_supported": "every_claim_supported"}


def canonical_signature(expected, n_sources, kind, recommendations):
    """The checker's canonical research signature (JSON form): the decision enters only as its decision class, so
    neither rewording nor a temporal clause (which only settles a status) can hide a repeated gold structure."""
    return json.dumps(["research", sorted([c["status"], len(c["citations"]), len(c["lineages"])]
                                          for c in expected["claims"]),
                       recommendations.index(expected["recommendation"]), list(expected["uncertainties"]),
                       n_sources, DECISION_CLASS[kind]])


def focal_sources(pattern, sls, number, variant):
    """(claim_id, relation, lineage_key, extra) rows for C1; lineage_key groups rows sharing a lineage."""
    if pattern == "P1":
        return [("C1", "support", "a", {}), ("C1", "support", "b", {})]
    if pattern == "P2":
        return [("C1", "deny", "a", {})]
    if pattern == "P3":
        return [("C1", "other_subject", "a", {})]
    if pattern == "P4":
        rows = [("C1", "support", "a", {}), ("C1", "support", "a", {})]
        return rows if sls else rows + [("C1", "support", "b", {})]
    if pattern == "P5":
        return [("C1", "support", "a", {}), ("C1", "deny", "b", {})]
    if pattern == "P6":
        return [("C1", "narrow", "a", {})]
    if pattern == "P7":
        # the later source governs; it denies wherever sls must be false, and alternates otherwise
        later_supports = sls and (number + variant) % 2 == 0
        older, newer = ("deny", "support") if later_supports else ("support", "deny")
        return [("C1", older, "a", {"when": "older"}), ("C1", newer, "b", {"when": "newer"})]
    if pattern == "P8":
        return [("C1", "quantity_deny", "a", {"q": 0}), ("C1", "quantity_deny", "b", {"q": 1})]
    raise ValueError(pattern)


def filler_plans(sls, fillers, remaining):
    """Candidate filler compositions: lists of (claim_id, relation, lineage_key) for the remaining sources."""
    plans = []
    if not fillers or remaining == 0:
        return [[]]
    if sls:
        # (a) every filler supported, each by a single lineage (repeats reuse that lineage)
        plan, k = [], 0
        while len(plan) < remaining:
            cid = fillers[k % len(fillers)]
            plan.append((cid, "support", f"f{cid}"))
            k += 1
        plans.append(plan)
        # (b) first filler single-lineage support, the others contradicted by fresh lineages
        plan = [(fillers[0], "support", f"f{fillers[0]}")]
        k = 1
        while len(plan) < remaining:
            cid = fillers[k % len(fillers)] if len(fillers) > 1 else fillers[0]
            plan.append((cid, "support" if cid == fillers[0] else "deny",
                         f"f{cid}" if cid == fillers[0] else f"g{len(plan)}"))
            k += 1
        plans.append(plan)
        # (c) last filler single-lineage support, first contradicted
        if len(fillers) > 1:
            plan, k = [], 0
            while len(plan) < remaining:
                cid = fillers[k % len(fillers)]
                plan.append((cid, "support", f"f{cid}") if cid == fillers[-1] else (cid, "deny", f"g{len(plan)}"))
                k += 1
            plans.append(plan)
    else:
        # (a) every filler contradicted by fresh lineages
        plan, k = [], 0
        while len(plan) < remaining:
            cid = fillers[k % len(fillers)]
            plan.append((cid, "deny", f"g{len(plan)}"))
            k += 1
        plans.append(plan)
        # (b) first filler supported by two independent lineages, the rest contradicted
        if remaining >= 2:
            plan = [(fillers[0], "support", "s1"), (fillers[0], "support", "s2")]
            k = 1
            while len(plan) < remaining:
                cid = fillers[k % len(fillers)] if len(fillers) > 1 else fillers[0]
                plan.append((cid, "deny", f"g{len(plan)}") if cid != fillers[0] else (cid, "support", f"s{len(plan)}"))
                k += 1
            plans.append(plan)
        # (c) contradicted, but one filler denied twice by the same publisher (a reissued denial)
        if remaining >= 2:
            plan = [(fillers[0], "deny", "r1"), (fillers[0], "deny", "r1")]
            k = 1
            while len(plan) < remaining:
                cid = fillers[k % len(fillers)] if len(fillers) > 1 else fillers[0]
                plan.append((cid, "deny", f"g{len(plan)}"))
                k += 1
            plans.append(plan)
    return plans


def extra_plans(fillers, remaining):
    """Further filler compositions, tried after filler_plans: each filler claim gets a count of sources and a
    treatment (supported or contradicted, by one lineage or by two), with any extra sources written as reissues of
    the claim's first lineage. Sources are interleaved claim by claim. At most two lineages per claim and relation."""
    import itertools
    if not fillers or remaining == 0:
        return []

    def splits(total, parts):
        if parts == 1:
            yield (total,)
            return
        for first in range(1, total - parts + 2):
            for rest in splits(total - first, parts - 1):
                yield (first,) + rest

    treatments = [("support", 1), ("deny", 1), ("support", 2), ("deny", 2)]
    plans = []
    for counts in splits(remaining, len(fillers)):
        for combo in itertools.product(treatments, repeat=len(fillers)):
            per_claim = []
            for cid, n, (relation, lineages) in zip(fillers, counts, combo):
                if lineages > n:
                    break
                prefix = "p" if relation == "support" else "q"
                keys = [f"{prefix}{cid}{'ab'[min(i, lineages - 1)]}" for i in range(n)]
                per_claim.append([(cid, relation, key) for key in keys])
            else:
                plan = []
                for i in range(max(counts)):
                    plan += [rows[i] for rows in per_claim if i < len(rows)]
                plans.append(plan)
    return plans


def cap(text):
    return text[0].upper() + text[1:]


def build():
    stream = NameStream()
    stream.skip_through("ordinary_conversation")
    first_ordinal = stream.position + 1
    sys.path.insert(0, str(ROOT / "experiments/G-ROUTE4-candidate/blueprint"))
    import build_blueprint as B  # noqa: E402  read-only G-ROUTE3 inventory
    _, g3_lineages = B.g_route3_entity_inventory()
    lineage_bank = Lineages(set(g3_lineages))
    body = TEMPLATE[len("{SUBJECT}"):]
    cursor = {k: 0 for k in ("std", "scope", "qty")}
    cursor_by_risk = {}
    signatures = {}
    fixtures, gold, design = [], [], []
    for number, slot in enumerate(SLOTS, 1):
        fid, family, risk = slot["fixture_id"], slot["family"], slot["risk"]
        pattern, sls = slot["features"]["pattern"], slot["features"]["sls"]
        n_claims, n_sources = FAMILY_SHAPE[family]
        primary, secondary = stream.take(2)
        rc = cursor_by_risk.setdefault(risk, {"scope": 0, "qty": 0, "rec": number % 3,
                                              "usage": [0] * len(RT.STANDARD[risk]), "pairs": set(),
                                              "focal": set()})
        std_pool, scope_pool, qty_pool = RT.STANDARD[risk], RT.SCOPE[risk], RT.QUANTITY[risk]
        # greedy topic design: least-used topics first, and no two fixtures of a risk class share a topic pair,
        # so any two fixtures share at most one standard topic. A focal claim cited by two or more sources
        # (P1, P4, P5, P7) uses both paraphrases of its topic, so each such topic is focal in one fixture only.
        need = n_claims - (1 if pattern in ("P6", "P8") else 0)
        multi_focal = pattern in ("P1", "P4", "P5", "P7")
        picked = []
        for slot_i in range(need):
            order = sorted(range(len(std_pool)), key=lambda k: (rc["usage"][k], (k * 7 + number) % len(std_pool)))
            if slot_i == 0 and multi_focal:
                order = [k for k in order if k not in rc["focal"]] or order
            fresh = [k for k in order if k not in picked and
                     all((min(k, p), max(k, p)) not in rc["pairs"] for p in picked)]
            k = (fresh or [k for k in order if k not in picked])[0]
            picked.append(k)
        if multi_focal:
            rc["focal"].add(picked[0])
        for a in picked:
            rc["usage"][a] += 1
            for b in picked:
                if a < b:
                    rc["pairs"].add((a, b))
        picked_iter = iter(picked)

        def next_std():
            k = next(picked_iter)
            return std_pool[k]

        claims = []
        for index in range(1, n_claims + 1):
            subject = primary if index % 2 else secondary
            if index == 1 and pattern == "P6":
                topic = scope_pool[rc["scope"] % len(scope_pool)]
                rc["scope"] += 1
                claims.append({"claim_id": "C1", "kind": "scope", "subject": subject, "topic": topic,
                               "text": topic[0].replace("{S}", subject)})
            elif index == 1 and pattern == "P8":
                topic = qty_pool[rc["qty"] % len(qty_pool)]
                rc["qty"] += 1
                threshold = 20 + (number * 37) % 180
                claims.append({"claim_id": "C1", "kind": "quantity", "subject": subject, "topic": topic,
                               "threshold": threshold,
                               "text": topic[0].replace("{S}", subject).replace("{T}", str(threshold))})
            else:
                topic = next_std()
                claims.append({"claim_id": f"C{index}", "kind": "standard", "subject": subject, "topic": topic,
                               "text": topic[0].replace("{S}", subject)})
        pairs = RT.RECOMMENDATIONS[risk]
        rc.setdefault("rec_use", [0] * len(pairs))
        choice = min(range(len(pairs)), key=lambda k: (rc["rec_use"][k], (k * 5 + number) % len(pairs)))
        rc["rec_use"][choice] += 1
        pos, neg = pairs[choice]
        recommendations = [pos, neg]
        kind = DECISION_KIND.get(pattern, "all_supported")
        fillers = [c["claim_id"] for c in claims[1:]]

        chosen = None
        for variant in range(4):
            focal = focal_sources(pattern, sls, number, variant)
            for plan in filler_plans(sls, fillers, n_sources - len(focal)) +                     extra_plans(fillers, n_sources - len(focal)):
                rows = focal + [(c, rel, key, {}) for c, rel, key in plan]
                ledger = [{"source_id": f"S{i}", "claim_id": c, "relation": rel, "lineage_key": key, **extra}
                          for i, (c, rel, key, extra) in enumerate(rows, 1)]
                # independent publishers never share wording: each topic has two paraphrases per relation, so at
                # most two distinct lineages may state the same relation about the same claim
                groups = {}
                for s in ledger:
                    if s["relation"] in ("support", "deny"):
                        groups.setdefault((s["claim_id"], s["relation"]), set()).add(s["lineage_key"])
                if any(len(keys) > 2 for keys in groups.values()):
                    continue
                probe = [dict(s, lineage=s["lineage_key"],
                              **({"date": "1" if s["when"] == "newer" else "0"} if s.get("when") else {}))
                         for s in ledger]
                expected, _ = derive_gold(pattern, claims, probe, recommendations)
                cited = "single_lineage_support" in expected["uncertainties"]
                supporting = sls_supporting_reading(claims, probe, expected)
                if cited != sls or supporting != sls:
                    continue
                sig = canonical_signature(expected, n_sources, kind, recommendations)
                opposite = signatures.get((risk, "B" if slot["phase"] == "A" else "A"), set())
                if sig in opposite:
                    continue
                chosen = (ledger, sig)
                break
            if chosen:
                break
        if chosen is None:
            raise AssertionError(("no clash-free, unambiguous composition", fid))
        ledger, sig = chosen
        signatures.setdefault((risk, slot["phase"]), set()).add(sig)

        # concrete lineages, dates and texts
        key_to_lineage, seen_keys, variant_of = {}, set(), {}
        base_year = 2040 + number % 20
        for i, s in enumerate(ledger):
            if s["lineage_key"] not in key_to_lineage:
                key_to_lineage[s["lineage_key"]] = lineage_bank.take()
            s["lineage"] = key_to_lineage[s["lineage_key"]]
            claim = claims[int(s["claim_id"][1:]) - 1]
            topic, subject = claim["topic"], claim["subject"]
            # each lineage keeps one paraphrase per (claim, relation); a second lineage gets the other one, and a
            # reissue repeats its own publisher's wording
            group = (s["claim_id"], s["relation"])
            used = variant_of.setdefault(group, {})
            if s["lineage_key"] not in used:
                used[s["lineage_key"]] = (1 + (number + int(s["claim_id"][1:])) % 2) if not used else                     3 - next(iter(used.values()))
            alt = used[s["lineage_key"]]
            if s["relation"] == "support":
                text = topic[alt].replace("{S}", subject)
            elif s["relation"] == "deny":
                text = topic[2 + alt].replace("{S}", subject)
            elif s["relation"] == "other_subject":
                other = secondary if subject == primary else primary
                s["alternate_subject"] = other
                text = topic[alt].replace("{S}", other)
            elif s["relation"] == "narrow":
                text = topic[1].replace("{S}", subject)
            elif s["relation"] == "quantity_deny":
                value = claim["threshold"] - (3 + number % 9) - s["q"] * (2 + number % 5)
                s["value"] = value
                text = topic[1 + s["q"]].replace("{S}", subject).replace("{V}", str(value))
            else:
                raise ValueError(s["relation"])
            if s.get("when"):
                year = base_year + (1 if s["when"] == "newer" else 0)
                date = dt.date(year, 1 + (number * 5 + i) % 12, 1 + (number * 11 + i) % 27).isoformat()
                s["date"] = date
                text = RT.DATE_PREFIXES[(number + i) % len(RT.DATE_PREFIXES)].replace("{D}", date) + text
            if s["lineage_key"] in seen_keys and not s.get("when"):
                text = RT.REISSUE_PREFIXES[(number + i) % len(RT.REISSUE_PREFIXES)] + text
                s["reissue"] = True
            seen_keys.add(s["lineage_key"])
            s["text"] = text
            del s["lineage_key"]
        expected, reasons = derive_gold(pattern, claims, ledger, recommendations)
        assert ("single_lineage_support" in expected["uncertainties"]) is sls, fid
        rules = FOCAL_RULES if pattern in ("P1", "P4") else TEMPORAL_RULES if pattern == "P7" else ALL_RULES
        use = rc.setdefault(f"rule_use_{kind}", [0] * len(rules))
        pick = min(range(len(rules)), key=lambda k: (use[k], (k * 3 + number) % len(rules)))
        use[pick] += 1
        rule = rules[pick]
        decision = rule.replace("{pos}", pos).replace("{neg}", neg)
        opening = f"Assess the claims about {primary} and {secondary}"
        prompt = TEMPLATE.replace("{SUBJECT}", opening)
        assert prompt == opening + body
        inp = {"allowed_recommendations": recommendations, "allowed_uncertainty_codes": UNCERTAINTY_CODES,
               "claims": [{"claim_id": c["claim_id"], "text": c["text"]} for c in claims],
               "decision_rule": decision,
               "sources": [{"source_id": s["source_id"], "lineage": s["lineage"], "text": s["text"]} for s in ledger]}
        rationale = ("; ".join(f"{row['claim_id']} is {row['status']} ({reasons[row['claim_id']]}), citing "
                               f"{', '.join(row['citations']) or 'no source'} across {len(row['lineages'])} lineage(s)"
                               for row in expected["claims"]) +
                     f". The decision rule gives {expected['recommendation']}; holding codes: "
                     f"{', '.join(expected['uncertainties']) or 'none'}.")
        fixtures.append({"consequence_risk": risk, "fixture_id": fid, "input": inp, "prompt": prompt,
                         "task_class": "grounded_research_synthesis",
                         "title": f"Claims about {primary} and {secondary}", "validator_profile": "research.v1"})
        gold.append({"expected": expected, "fixture_id": fid, "rationale": rationale, "reference_output": expected})
        design.append({
            "fixture_id": fid, "phase": slot["phase"], "role": slot["role"], "risk": risk, "family": family,
            "features": slot["features"], "invented_names": [primary, secondary], "identifiers": [],
            "global_name_ordinals": [stream.position - 1, stream.position],
            "research_contract": {
                "claims": [{k: v for k, v in c.items() if k != "topic"} for c in claims],
                "sources": ledger, "decision": {"kind": kind, "positive": pos, "negative": neg},
                "derived_reasons": reasons, "canonical_signature": json.loads(sig)}})
    return {
        "schema_version": "g-route4.authoring-staging.v2", "task_class": "grounded_research_synthesis",
        "blueprint_commit": "1156d06", "status": "authored, not sealed, not adjudicated",
        "name_stream": stream.provenance(),
        "name_sequence": {"first_research_ordinal": first_ordinal, "last_research_ordinal": stream.position},
        "missing_slots": sorted({s["fixture_id"] for s in SLOTS} - {f["fixture_id"] for f in fixtures}),
        "fixtures": fixtures, "gold": gold, "design": design,
    }


if __name__ == "__main__":
    output = build()
    path = HERE / "staging/research.json"
    path.write_text(json.dumps(output, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(output['fixtures'])} fixtures written; missing slots: {output['missing_slots']}")
    print("name sequence", output["name_sequence"])
