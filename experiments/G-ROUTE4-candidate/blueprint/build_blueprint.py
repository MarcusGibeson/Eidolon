"""Build the G-ROUTE4 authoring blueprint and its feasibility report (blueprint stage only).

Deterministic: running it twice gives byte-identical BLUEPRINT.json and FEASIBILITY_REPORT.json. It writes no fixture
text, contacts no model, and touches no data root. It reads G-ROUTE3's frozen corpora only to size the entity
inventory the fresh fixtures must avoid.

    python -B build_blueprint.py
"""

import collections
import hashlib
import json
import math
import sys
from itertools import cycle
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import audit_sample  # noqa: E402

RISKS = ("R1", "R2", "R3", "R4")
ELIGIBLE = ("R1", "R2", "R3")
B_SIZE = {"CONV": 28}          # eligible B′ cell size per class code; others 18; R4 cells 1
CLASS_CODE = {"ordinary_conversation": "CONV", "structured_extraction": "EXTR",
              "hierarchical_semantic_synthesis": "SYNTH", "reflective_planning": "PLAN",
              "grounded_research_synthesis": "RSRCH"}

RISK_MEANING = {
    "R1": "everyday personal or hobby matters; a wrong answer is easily noticed and cheaply undone",
    "R2": "money, orders, bookings or workplace administration; a wrong answer costs money or time but is reversible",
    "R3": "security, privacy, compliance or access; a wrong answer can expose data or grant access",
    "R4": "physical safety, legal retention or irreversible operations; evidence-only, never routed",
}

CLASSES = {
    "ordinary_conversation": {
        "profile": "conversation.v1",
        "construct": ("Answer a user's question by choosing the single option, among exactly 4 listed options, that "
                      "follows from the supplied facts through a small computation or condition. Reply in the "
                      "disclosed two-line frame (Answer: <option> / Actions taken: none), with no tools and no "
                      "action claimed."),
        "families": {
            "CV1": "two-condition filter over supplied items (both conditions must hold)",
            "CV2": "date or clock-time arithmetic (differences, additions, expiry)",
            "CV3": "unit conversion followed by a comparison or maximum",
            "CV4": "conditional count or aggregation over supplied items",
            "CV5": "percentage, rate or threshold comparison",
            "CV6": "a general rule with a stated exception or precedence (the exception decides)",
        },
        "features": {"gold_position": "1-4, position of the gold option among the 4 options",
                     "depth": "1 = one reasoning step, 2 = two chained steps"},
        "b_matching": ("gold_position", "depth"),
    },
    "structured_extraction": {
        "profile": "extraction.v1",
        "construct": ("Return one JSON object whose keys exactly match a supplied schema, copying values verbatim "
                      "where the text states them, deriving the fields the prompt defines, and giving the schema's "
                      "unknown value where the text explicitly says a value is not stated."),
        "families": {
            "EX1": "verbatim identifiers, names and spans",
            "EX2": "date or time arithmetic into a derived field",
            "EX3": "numeric aggregation (sum, product, share) into a derived field",
            "EX4": "threshold or compliance gate into a boolean or enum field",
            "EX5": "explicit absence represented by the schema's unknown value",
            "EX6": "conjunctive multi-condition gate (all conditions must hold)",
        },
        "features": {"field_count": "3, 4 or 5 schema fields", "derived_count": "1 or 2 derived fields"},
        "b_matching": ("field_count", "derived_count"),
    },
    "hierarchical_semantic_synthesis": {
        "profile": "synthesis.v1",
        "construct": ("Cover every observation exactly once with its original role, merging only same-role "
                      "observations, and choose the conclusion from allowed_conclusions by the conclusion_rule."),
        "families": {
            "SY1": "a finding directly states the cause (cause established)",
            "SY2": "a proposed cause is disputed by counterevidence (cause unresolved)",
            "SY3": "a single finding is insufficient for the claimed trend (insufficient evidence)",
            "SY4": "the decision is reserved to a named role (authority boundary)",
            "SY5": "a stated constraint or limit is breached",
            "SY6": "a policy or configuration explains the observed behaviour",
        },
        "features": {"mergeable_pair": "yes/no: whether two observations share a role and must merge",
                     "obs_band": "small = 3-4 observations, large = 5-6"},
        "b_matching": ("mergeable_pair", "obs_band"),
    },
    "reflective_planning": {
        "profile": "planning.v1",
        "construct": ("Plan without claiming completion: include every allowed action except those with a "
                      "forbidden name prefix, order them by the precedences stated in the evidence, cite each "
                      "action's addresses, list every uncertainty code whose condition holds, set "
                      "claims_completed false and request no authority."),
        "families": {
            "PL1": "4 included, 1 excluded, 1 holding code (G-ROUTE3's construct)",
            "PL2": "3 included, 2 excluded, 0 holding codes",
            "PL3": "5 included, 1 excluded, 2 holding codes",
            "PL4": "4 included, 2 excluded, 1 holding code; precedences listed out of order in the evidence",
            "PL5": "3 included, 1 excluded, 1 holding code; one action addresses two evidence items",
            "PL6": "5 included, 0 excluded, 1 holding code",
        },
        "features": {"precedence_form": "before = 'X must precede Y' / after = 'Y may start only after X'"},
        "b_matching": ("precedence_form",),
    },
    "grounded_research_synthesis": {
        "profile": "research.v1",
        "construct": ("Judge each claim against the sources by the ordered status rules, cite exactly the sources "
                      "about it with their lineages, recommend by the decision_rule, and list every uncertainty "
                      "code whose condition holds."),
        "families": {
            "RS1": "2 claims, 3 sources", "RS2": "2 claims, 4 sources", "RS3": "3 claims, 4 sources",
            "RS4": "2 claims, 5 sources", "RS5": "3 claims, 5 sources", "RS6": "3 claims, 6 sources",
        },
        "patterns": {
            "P1": "positive lineage count rule", "P2": "direct contradiction", "P3": "other subject, unaddressed",
            "P4": "same-lineage repetition", "P5": "conflict unresolved", "P6": "narrower scope",
            "P7": "conflict settled by rule", "P8": "quantitative contradiction",
        },
        "features": {"pattern": "P1-P8 (the design's allocation table)",
                     "sls": "whether single_lineage_support holds (true/false)"},
        "b_matching": ("pattern", "sls"),
    },
}

for _spec in CLASSES.values():
    _spec["family_template_text"] = {fam: "" for fam in _spec["families"]}

# Design's research allocation (revision 6, "Authoring blueprint").
RESEARCH_A = {"R1": ["P1", "P2", "P3", "P4"], "R2": ["P5", "P6", "P7", "P8"],
              "R3": ["P1", "P3", "P5", "P7"], "R4": ["P2", "P4", "P6", "P8"]}
RESEARCH_B_EXTRA = {"R1": ["P1", "P2"], "R2": ["P3", "P4"], "R3": ["P5", "P6"]}
R4_B = {"CONV": {"family": "CV6", "features": {"gold_position": 1, "depth": 2}},
        "EXTR": {"family": "EX6", "features": {"field_count": 4, "derived_count": 2}},
        "SYNTH": {"family": "SY4", "features": {"mergeable_pair": "yes", "obs_band": "large"}},
        "PLAN": {"family": "PL1", "features": {"precedence_form": "before"}},
        "RSRCH": {"family": "RS3", "features": {"pattern": "P7", "sls": True}}}
# A′ family rotation: 4 distinct families per cell, every family at least twice across the class's 16 A′ fixtures.
A_FAMILY_ROTATION = {"R1": [1, 2, 3, 4], "R2": [5, 6, 1, 2], "R3": [3, 4, 5, 6], "R4": [1, 3, 5, 2]}


def fid(phase, code, risk, n, reserve=False):
    return f"{phase}4-{code}-{risk}-{'X' if reserve else ''}{n:02d}"


def families(cls):
    return list(CLASSES[cls]["families"])


def a_slots(cls):
    code, fams, out = CLASS_CODE[cls], families(cls), []
    for risk in RISKS:
        chosen = [fams[i - 1] for i in A_FAMILY_ROTATION[risk]]
        for n, fam in enumerate(chosen, 1):
            feats = {}
            if code == "CONV":
                feats = {"gold_position": n, "depth": 1 + (n + 1) % 2}
            elif code == "EXTR":
                feats = {"field_count": 3 + (n - 1) % 3, "derived_count": 1 + (n - 1) % 2}
            elif code == "SYNTH":
                feats = {"mergeable_pair": "yes" if n % 2 else "no", "obs_band": "small" if n <= 2 else "large"}
            elif code == "PLAN":
                feats = {"precedence_form": "before" if n % 2 else "after"}
            else:
                feats = {"pattern": RESEARCH_A[risk][n - 1], "sls": n in (1, 3)}
            out.append({"fixture_id": fid("A", code, risk, n), "phase": "A", "role": "main", "task_class": cls,
                        "risk": risk, "family": fam, "features": feats})
    return out


def b_family_counts(cls, risk):
    fams = families(cls)
    size = B_SIZE.get(CLASS_CODE[cls], 18)
    base, extra = divmod(size, len(fams))
    shift = {"R1": 0, "R2": 2, "R3": 4}[risk]
    rotated = fams[shift:] + fams[:shift]
    return {fam: base + (1 if i < extra else 0) for i, fam in enumerate(rotated)}


def b_slots(cls, a_by_cell):
    code, out = CLASS_CODE[cls], []
    for risk in ELIGIBLE:
        counts = b_family_counts(cls, risk)
        fam_seq = [fam for fam, k in counts.items() for _ in range(k)]
        size = len(fam_seq)
        if code == "CONV":
            feat_seq = [{"gold_position": 1 + i % 4, "depth": 1 + (i // 4) % 2} for i in range(size)]
        elif code == "EXTR":
            a_keys = {(s["family"], s["features"]["field_count"], s["features"]["derived_count"])
                      for s in a_by_cell[(cls, risk)]}
            combos = [(f, d) for f in (3, 4, 5) for d in (1, 2)]
            feat_seq, pick = [], cycle(range(len(combos)))
            for fam in fam_seq:
                for _ in range(len(combos)):
                    f, d = combos[next(pick)]
                    if (fam, f, d) not in a_keys:
                        break
                feat_seq.append({"field_count": f, "derived_count": d})
        elif code == "SYNTH":
            feat_seq = [{"mergeable_pair": "yes" if i % 2 == 0 else "no",
                         "obs_band": "small" if (i // 2) % 2 == 0 else "large"} for i in range(size)]
        elif code == "PLAN":
            feat_seq = [{"precedence_form": "before" if i % 2 == 0 else "after"} for i in range(size)]
        else:
            patterns = [f"P{k}" for k in range(1, 9)] * 2 + RESEARCH_B_EXTRA[risk]
            sls_seq = [True, False] * 4 + [False, True] * 4 + [True, False]   # each pattern once with, once without
            a_keys = {(s["features"]["pattern"], s["family"], s["features"]["sls"]) for s in a_by_cell[(cls, risk)]}
            fam_cycle = list(fam_seq)
            feat_seq, fams_out = [], []
            for i, (pat, sls) in enumerate(zip(patterns, sls_seq)):
                for j in range(len(fam_cycle)):
                    fam = fam_cycle[(i + j) % len(fam_cycle)]
                    if (pat, fam, sls) not in a_keys:
                        break
                fams_out.append(fam)
                fam_cycle.remove(fam)
                fam_cycle.append(fam)
                feat_seq.append({"pattern": pat, "sls": sls})
            fam_seq = fams_out
        for n, (fam, feats) in enumerate(zip(fam_seq, feat_seq), 1):
            out.append({"fixture_id": fid("B", code, risk, n), "phase": "B", "role": "main", "task_class": cls,
                        "risk": risk, "family": fam, "features": feats})
    r4 = R4_B[code]
    out.append({"fixture_id": fid("B", code, "R4", 1), "phase": "B", "role": "main", "task_class": cls,
                "risk": "R4", "family": r4["family"], "features": dict(r4["features"])})
    return out


def reserve_slots(main):
    by_cell = collections.defaultdict(list)
    for s in main:
        by_cell[(s["phase"], s["task_class"], s["risk"])].append(s)
    out = []
    for (phase, cls, risk), slots in sorted(by_cell.items()):
        code = CLASS_CODE[cls]
        if phase == "A":
            combos = [(s["family"], tuple(sorted(s["features"].items()))) for s in slots]
        else:
            match = CLASSES[cls]["b_matching"]
            combos = []
            for s in slots:
                c = (None, tuple((k, s["features"][k]) for k in match))
                if c not in combos:
                    combos.append(c)
        need = max(len(combos), math.ceil(0.20 * len(slots)))
        freq = collections.Counter(c for c in (
            [(s["family"], tuple(sorted(s["features"].items()))) for s in slots] if phase == "A" else
            [(None, tuple((k, s["features"][k]) for k in CLASSES[cls]["b_matching"])) for s in slots]))
        extra = [c for c, _ in freq.most_common()][: need - len(combos)]
        for n, (fam, feats) in enumerate(combos + extra, 1):
            out.append({"fixture_id": fid(phase, code, risk, n, reserve=True), "phase": phase, "role": "reserve",
                        "task_class": cls, "risk": risk, "family": fam, "features": dict(feats),
                        "matching": "family+features" if phase == "A" else "features; caps re-checked"})
    return out


def g_route3_entity_inventory():
    """Named entities and identifiers in G-ROUTE3's frozen corpora (read-only), by G-ROUTE3's own detector."""
    sys.path.insert(0, str(ROOT / "tools"))
    import g_route3_independence as I  # noqa: E402  read-only use of G-ROUTE3's detector
    fixtures = []
    for c in ("a", "b"):
        fixtures += json.loads((ROOT / f"experiments/G-ROUTE3-candidate/corpus_{c}.json").read_text(
            encoding="utf-8"))["fixtures"]
    texts = [I._content(f) for f in fixtures]
    vocab = {w for t in texts for w in I._WORD.findall(t) if w.islower()}
    ents = set()
    for t in texts:
        ents |= I._named_entities(t, vocab)
    lineages = {s["lineage"] for f in fixtures if f["validator_profile"] == "research.v1"
                for s in f["input"]["sources"]}
    return sorted(ents), sorted(lineages)


def checks(slots, g3_entities, g3_lineages):
    res = []

    def check(name, ok, detail):
        res.append({"check": name, "pass": bool(ok), "detail": detail})

    main = [s for s in slots if s["role"] == "main"]
    A = [s for s in main if s["phase"] == "A"]
    B = [s for s in main if s["phase"] == "B"]
    cells = collections.defaultdict(list)
    for s in main:
        cells[(s["phase"], s["task_class"], s["risk"])].append(s)
    # composition
    check("A′ has 80 fixtures in 20 cells of 4", len(A) == 80 and all(
        len(v) == 4 for (p, _, _), v in cells.items() if p == "A"), {"A": len(A)})
    elig = [s for s in B if s["risk"] != "R4"]
    conv = [s for s in elig if CLASS_CODE[s["task_class"]] == "CONV"]
    check("B′ has 300 eligible (84 conversation + 216 other) and 5 R4 cases; 915 calls",
          len(elig) == 300 and len(conv) == 84 and len(B) == 305 and len(B) * 3 == 915,
          {"eligible": len(elig), "conversation": len(conv), "B": len(B), "calls": len(B) * 3})
    check("A′ calls = 480", len(A) * 3 * 2 == 480, {"calls": len(A) * 6})
    # ids
    ids = [s["fixture_id"] for s in slots]
    check("fixture ids are unique and use the A4-/B4- namespace", len(ids) == len(set(ids)) and all(
        i.startswith(("A4-", "B4-")) for i in ids), {"slots": len(ids)})
    # family caps
    cap_detail, cap_ok = {}, True
    for cls in CLASSES:
        bcls = [s for s in B if s["task_class"] == cls]
        counts = collections.Counter(s["family"] for s in bcls)
        limit = math.floor(0.25 * len(bcls))
        cap_detail[cls] = {"B_cases": len(bcls), "max_family": max(counts.values()), "limit": limit,
                           "families": len(counts)}
        cap_ok &= max(counts.values()) <= limit and len(counts) >= 5
    check("class cap: no family above 25% of a class's B′ cases (R4 counted); at least 5 families",
          cap_ok, cap_detail)
    cell_ok, cell_detail = True, {}
    for (p, cls, risk), v in cells.items():
        if p != "B" or risk == "R4":
            continue
        m = max(collections.Counter(s["family"] for s in v).values())
        lim = len(v) // 3
        cell_detail[f"{CLASS_CODE[cls]}|{risk}"] = [m, lim]
        cell_ok &= m <= lim
    check("cell cap: no family above one third of an eligible B′ cell", cell_ok, cell_detail)
    check("A′ cells: 4 fixtures from 4 different families", all(
        len({s["family"] for s in v}) == 4 for (p, _, _), v in cells.items() if p == "A"), {})
    cov_ok = True
    for cls in CLASSES:
        fa = {s["family"] for s in A if s["task_class"] == cls}
        fb = {s["family"] for s in B if s["task_class"] == cls}
        cov_ok &= fa == fb == set(CLASSES[cls]["families"])
    check("class-level family coverage: every family appears in both A′ and B′", cov_ok, {})
    # conversation positions
    pos_ok, pos_detail = True, {}
    for (p, cls, risk), v in cells.items():
        if CLASS_CODE[cls] != "CONV":
            continue
        c = collections.Counter(s["features"]["gold_position"] for s in v)
        counts = [c.get(k, 0) for k in (1, 2, 3, 4)]
        pos_detail[f"{p}|{risk}"] = counts
        if len(v) >= 4:
            pos_ok &= max(counts) - min(counts) <= 1
    check("conversation: exactly 4 options; gold positions balanced within 1 in every cell of 4 or more",
          pos_ok, pos_detail)
    # research allocation
    ra, rb = collections.Counter(), collections.Counter()
    sls_ok = True
    for (p, cls, risk), v in cells.items():
        if CLASS_CODE[cls] != "RSRCH":
            continue
        if p == "A":
            sls_ok &= sum(s["features"]["sls"] for s in v) == 2
            ra.update(s["features"]["pattern"] for s in v)
            sls_ok &= [s["features"]["pattern"] for s in v] == RESEARCH_A[risk]
        elif risk != "R4":
            sls_ok &= sum(s["features"]["sls"] for s in v) == 9
            rb.update(s["features"]["pattern"] for s in v)
    check("research: A′ cells match the design table with 2 of 4 single_lineage_support; B′ cells 9 of 18",
          sls_ok, {"A_pattern_counts": dict(sorted(ra.items()))})
    check("research: eligible B′ pattern counts P1-P6 = 7, P7-P8 = 6",
          all(rb[f"P{k}"] == 7 for k in range(1, 7)) and rb["P7"] == rb["P8"] == 6, dict(sorted(rb.items())))
    # planned signature keys distinct A′ vs B′ per cell (extraction, research)
    sig_ok, sig_detail = True, {}
    for cls, keyf in (("structured_extraction", lambda s: (s["family"], s["features"]["field_count"],
                                                            s["features"]["derived_count"])),
                      ("grounded_research_synthesis", lambda s: (s["features"]["pattern"], s["family"],
                                                                  s["features"]["sls"]))):
        for risk in ELIGIBLE:
            ak = {keyf(s) for s in cells[("A", cls, risk)]}
            clash = [s["fixture_id"] for s in cells[("B", cls, risk)] if keyf(s) in ak]
            sig_detail[f"{CLASS_CODE[cls]}|{risk}"] = clash
            sig_ok &= not clash
    check("planned structure keys: no B′ slot repeats an A′ slot's key in the same cell (extraction, research)",
          sig_ok, sig_detail)
    # reserve
    res_slots = [s for s in slots if s["role"] == "reserve"]
    rcells = collections.Counter((s["phase"], s["task_class"], s["risk"]) for s in res_slots)
    r_ok = all(rcells[k] >= math.ceil(0.20 * len(v)) for k, v in cells.items())
    per = collections.Counter()
    for (p, cls, risk), n in rcells.items():
        per[f"{p}|{CLASS_CODE[cls]}"] += n
    check("reserve: at least 20% of every cell and one per matching feature combination",
          r_ok, {"total": len(res_slots), "by_phase_class": dict(sorted(per.items()))})
    # sample sizes and floors
    samp = sum(audit_sample.cell_sample_size(len(v)) for (p, _, _), v in cells.items() if p == "B")
    check("audit sample size = 38 (3 per conversation cell, 2 per other eligible cell, 1 per R4 cell)",
          samp == 38, {"sample": samp})
    check("A′ full treatment: 2 extra adjudicator sessions per A′ fixture (160 for the main corpus)",
          len(A) * 2 == 160, {"extra_sessions": len(A) * 2})
    check("P1 floors reachable: 300 eligible cases can yield at least 76 stops and 30 qualified starts",
          len(elig) >= 76 and len(elig) >= 30, {"eligible": len(elig)})
    # entity and lineage capacity
    fixtures_total = len(slots)
    need_names = fixtures_total * 6
    syllables = 18 * 5
    capacity = syllables ** 2 + syllables ** 3
    check("entity inventory: enough fresh invented names for every fixture (at most 6 per fixture)",
          capacity >= 50 * need_names, {"fixtures_incl_reserve": fixtures_total, "names_needed_max": need_names,
                                        "bank_capacity": capacity, "g_route3_entities_to_avoid": len(g3_entities)})
    rs = [s for s in slots if CLASS_CODE[s["task_class"]] == "RSRCH"]
    need_lin = len(rs) * 6
    check("research lineages: enough fresh lineage names (at most 6 per research fixture)",
          capacity >= 50 * need_lin, {"research_fixtures_incl_reserve": len(rs), "lineages_needed_max": need_lin,
                                      "g_route3_lineages_to_avoid": len(g3_lineages)})
    plan = [s for s in slots if CLASS_CODE[s["task_class"]] == "PLAN"]
    verbs, objects = 40, capacity          # a frozen 40-verb list x invented object names from the bank
    check("planning actions: every action name unique across all planning fixtures (at most 7 per fixture)",
          verbs * objects >= 50 * len(plan) * 7, {"planning_fixtures_incl_reserve": len(plan),
                                                  "action_names_needed_max": len(plan) * 7,
                                                  "capacity": verbs * objects})
    # pattern x single_lineage_support crossing (research B′): every pattern appears with both flag values
    cross_ok = True
    for risk in ELIGIBLE:
        v = cells[("B", "grounded_research_synthesis", risk)]
        for k in range(1, 9):
            flags = {s["features"]["sls"] for s in v if s["features"]["pattern"] == f"P{k}"}
            cross_ok &= flags == {True, False}
    check("research B′: every pattern appears with single_lineage_support both holding and not holding, per cell",
          cross_ok, {})
    check("O5 by construction: every family's model-facing template text is empty (structure only)",
          all(all(t == "" for t in spec["family_template_text"].values()) for spec in CLASSES.values()), {})
    # audit-sample procedure
    st = audit_sample.self_test()
    check("audit-sample procedure self-test (frozen test vector)", st["digest"] == FROZEN_SELF_TEST_DIGEST,
          {"digest": st["digest"]})
    return res


FROZEN_SELF_TEST_DIGEST = "75af7d1ad5d785b40c1a41f15e4d23fa7e987715530e8d9b64f4fec5a4b398c9"


def build():
    main = []
    a_by_cell = collections.defaultdict(list)
    for cls in CLASSES:
        a = a_slots(cls)
        for s in a:
            a_by_cell[(cls, s["risk"])].append(s)
        main += a
    for cls in CLASSES:
        main += b_slots(cls, a_by_cell)
    slots = main + reserve_slots(main)
    g3_entities, g3_lineages = g_route3_entity_inventory()
    report = checks(slots, g3_entities, g3_lineages)
    blueprint = {
        "schema_version": "g-route4.authoring-blueprint.v1",
        "status": "CANDIDATE (not frozen)",
        "design": "experiments/G-ROUTE4-candidate/DESIGN_CANDIDATE.md revision 6 (accepted, D11)",
        "obligations": "experiments/G-ROUTE4-candidate/G-ROUTE4_OBLIGATIONS.md",
        "risk_meaning": RISK_MEANING,
        "classes": {cls: {k: v for k, v in spec.items() if k != "b_matching"} | {"b_matching": list(spec["b_matching"])}
                    for cls, spec in CLASSES.items()},
        "research_allocation": {"A": RESEARCH_A, "B_extra_beyond_P1_P8_x2": RESEARCH_B_EXTRA, "R4": "P7, sls true"},
        "slots": slots,
        "counts": {"main_A": 80, "main_B": 305, "reserve": sum(s["role"] == "reserve" for s in slots),
                   "total": len(slots)},
        "g_route3_inventory_to_avoid": {"entities": len(g3_entities), "lineages": len(g3_lineages)},
    }
    return blueprint, report


if __name__ == "__main__":
    blueprint, report = build()
    (HERE / "BLUEPRINT.json").write_text(json.dumps(blueprint, indent=1, ensure_ascii=False, sort_keys=True) + "\n",
                                         encoding="utf-8", newline="\n")
    (HERE / "FEASIBILITY_REPORT.json").write_text(json.dumps(
        {"schema_version": "g-route4.blueprint-feasibility.v1", "all_pass": all(c["pass"] for c in report),
         "checks": report}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    lines = ["# G-ROUTE4 blueprint feasibility report", "",
             "Generated by `build_blueprint.py` from `BLUEPRINT.json`. It is deterministic: re-running it reproduces "
             "both files byte for byte.", "",
             f"**All checks pass: {all(c['pass'] for c in report)}** ({sum(c['pass'] for c in report)} of {len(report)}).",
             "", "| Result | Check | Detail |", "|---|---|---|"]
    for c in report:
        detail = json.dumps(c["detail"], ensure_ascii=False).replace("|", "\\|")
        lines.append(f"| {'PASS' if c['pass'] else 'FAIL'} | {c['check']} | `{detail}` |")
    (HERE / "FEASIBILITY_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    for c in report:
        print("PASS" if c["pass"] else "FAIL", "-", c["check"])
    print("blueprint digest", hashlib.sha256((HERE / "BLUEPRINT.json").read_bytes()).hexdigest())
