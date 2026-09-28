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
    for r_index, risk in enumerate(RISKS):
        chosen = [fams[i - 1] for i in A_FAMILY_ROTATION[risk]]
        for n, fam in enumerate(chosen, 1):
            feats = {}
            m = n + r_index                          # rotate features with the cell (no family-feature lock)
            if code == "CONV":
                feats = {"gold_position": n, "depth": 1 + m % 2}
            elif code == "EXTR":
                feats = {"field_count": 3 + m % 3, "derived_count": 1 + m % 2}
            elif code == "SYNTH":
                feats = {"mergeable_pair": "yes" if m % 2 else "no", "obs_band": "small" if (m // 2) % 2 else "large"}
            elif code == "PLAN":
                feats = {"precedence_form": "before" if m % 2 else "after"}
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
            fams_all = families(cls)
            quota = {f: 3 for f in fams_all}          # 18 = 6 families x 3

            def place(i, chosen):
                if i == len(patterns):
                    return chosen
                pat, sls = patterns[i], sls_seq[i]
                order = sorted(fams_all, key=lambda f: (-quota[f], (fams_all.index(f) - i) % len(fams_all)))
                for fam in order:
                    if quota[fam] and (pat, fam, sls) not in a_keys:
                        quota[fam] -= 1
                        got = place(i + 1, chosen + [fam])
                        if got:
                            return got
                        quota[fam] += 1
                return None
            fam_seq = place(0, [])
            feat_seq = [{"pattern": pat, "sls": sls} for pat, sls in zip(patterns, sls_seq)]
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
    import re as _re                                  # G-ROUTE3's own rule (g_route3_independence.audit)
    vocab = {w for t in texts for w in _re.findall(r"(?<![A-Za-z])[a-z]+", t)}
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
    check("(arithmetic) A′ calls = 480", len(A) * 3 * 2 == 480, {"calls": len(A) * 6})
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
    check("conversation: gold positions balanced within 1 in every cell of 4 or more (the 4-option rule is "
          "enforced at authoring)", pos_ok, pos_detail)
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
    check("reserve: at least 20% of every cell", r_ok,
          {"total": len(res_slots), "by_phase_class": dict(sorted(per.items()))})
    cover_ok = True
    for (p, cls, risk), v in cells.items():
        rs = [s for s in res_slots if (s["phase"], s["task_class"], s["risk"]) == (p, cls, risk)]
        if p == "A":
            key = lambda s: (s["family"], tuple(sorted((k, x) for k, x in s["features"].items()
                                                          if k != "field_types")))
        else:
            key = lambda s, c=cls: tuple((k, s["features"][k]) for k in CLASSES[c]["b_matching"])
        cover_ok &= {key(s) for s in v} <= {key(s) for s in rs}
    check("reserve: every matching feature combination present in a cell has a reserve", cover_ok, {})
    # sample sizes and floors
    samp = sum(audit_sample.cell_sample_size(len(v)) for (p, _, _), v in cells.items() if p == "B")
    check("audit sample size = 38 (3 per conversation cell, 2 per other eligible cell, 1 per R4 cell)",
          samp == 38, {"sample": samp})
    check("(arithmetic) A′ full treatment: 2 extra adjudicator sessions per A′ fixture (160 for the main corpus)",
          len(A) * 2 == 160, {"extra_sessions": len(A) * 2})
    check("(arithmetic) P1 floors reachable: 300 eligible cases can yield at least 76 stops and 30 qualified starts",
          len(elig) >= 76 and len(elig) >= 30, {"eligible": len(elig)})
    # entity and lineage capacity
    fixtures_total = len(slots)
    need_names = fixtures_total * 6
    syllables = 18 * 5
    capacity = syllables ** 2 + syllables ** 3
    check("(arithmetic) entity inventory: enough fresh invented names for every fixture (at most 6 per fixture)",
          capacity >= 50 * need_names, {"fixtures_incl_reserve": fixtures_total, "names_needed_max": need_names,
                                        "bank_capacity": capacity, "g_route3_entities_to_avoid": len(g3_entities)})
    rs = [s for s in slots if CLASS_CODE[s["task_class"]] == "RSRCH"]
    need_lin = len(rs) * 6
    check("(arithmetic) research lineages: enough fresh lineage names (at most 6 per research fixture)",
          capacity >= 50 * need_lin, {"research_fixtures_incl_reserve": len(rs), "lineages_needed_max": need_lin,
                                      "g_route3_lineages_to_avoid": len(g3_lineages)})
    plan = [s for s in slots if CLASS_CODE[s["task_class"]] == "PLAN"]
    verbs, objects = 40, capacity          # a frozen 40-verb list x invented object names from the bank
    check("(arithmetic) planning actions: every action name unique across all planning fixtures (at most 7 per fixture)",
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
    check("(declaration) O5: every family's model-facing template text is recorded as empty (structure only)",
          all(all(t == "" for t in spec["family_template_text"].values()) for spec in CLASSES.values()), {})
    # extraction: real fine signature (sorted abstract field types, derived count), A′ vs B′ main and reserve
    ex_ok, ex_detail = True, {}
    for risk in RISKS:
        grp = [s for s in slots if CLASS_CODE[s["task_class"]] == "EXTR" and s["risk"] == risk]
        a_sig = {(tuple(s["features"]["field_types"]), s["features"]["derived_count"]) for s in grp
                 if s["phase"] == "A"}
        clash = [s["fixture_id"] for s in grp if s["phase"] == "B"
                 and (tuple(s["features"]["field_types"]), s["features"]["derived_count"]) in a_sig]
        ok_types = all(len(s["features"]["field_types"]) == s["features"]["field_count"] for s in grp)
        ex_detail[risk] = clash
        ex_ok &= not clash and ok_types
    check("extraction: planned real fine signature of every B′ main and reserve slot differs from every A′ slot "
          "in its cell", ex_ok, ex_detail)
    # extraction: declared target mix and per-slot rules (NEW-B1)
    ex_slots = [s for s in slots if CLASS_CODE[s["task_class"]] == "EXTR"]
    rules_ok = all(_allowed(tuple(s["features"]["field_types"]), s["family"]) for s in ex_slots)
    mixes = {}
    for phase in ("A", "B"):
        c = collections.Counter(x for s in ex_slots if s["phase"] == phase and s["role"] == "main"
                                for x in s["features"]["field_types"])
        tot = sum(c.values())
        mixes[phase] = {k: round(c[k] / tot, 3) for k in TARGET_MIX}
    mix_ok = all(abs(mixes[p][k] - v) <= 0.08 for p in mixes for k, v in TARGET_MIX.items())
    check("extraction: every slot meets the per-slot type rules; A′ and B′ type mixes each within 0.08 of the "
          "declared target mix (G-ROUTE3's realized mix)", rules_ok and mix_ok,
          {"target": TARGET_MIX, "A": mixes["A"], "B": mixes["B"]})
    # families even within 1 in every eligible B′ cell (all classes)
    even_ok, even_detail = True, {}
    for (p, cls, risk), v in cells.items():
        if p != "B" or risk == "R4":
            continue
        c = collections.Counter(s["family"] for s in v)
        counts = [c.get(f, 0) for f in CLASSES[cls]["families"]]
        even_detail[f"{CLASS_CODE[cls]}|{risk}"] = counts
        even_ok &= max(counts) - min(counts) <= 1
    check("families as even as possible (within 1) in every eligible B′ cell", even_ok, even_detail)
    # B′ reserves: every family receives some reserve across the class (spread)
    spread_ok = True
    for cls in CLASSES:
        got = {s["family"] for s in slots if s["task_class"] == cls and s["phase"] == "B" and s["role"] == "reserve"}
        spread_ok &= got == set(CLASSES[cls]["families"])
    check("B′ reserves: every family receives reserve fixtures somewhere in its class", spread_ok, {})
    # A′: no family tied to a single value of a varying feature (reported)
    locked = []
    for cls in CLASSES:
        for fam in CLASSES[cls]["families"]:
            occ = [s for s in A if s["task_class"] == cls and s["family"] == fam]
            for feat in ("depth", "obs_band", "mergeable_pair", "precedence_form", "derived_count"):
                vals = {s["features"].get(feat) for s in occ if feat in s["features"]}
                if len(occ) >= 2 and len(vals) == 1 and None not in vals:
                    locked.append(f"{fam}:{feat}")
    check("(reported) A′: families tied to a single feature value across their occurrences", True,
          {"count": len(locked), "locked": locked})
    # research: slots that share (family, sls) with an A′ slot and rely on pattern alone to differ (reported)
    rel = {}
    for risk in ELIGIBLE:
        grp = [s for s in slots if CLASS_CODE[s["task_class"]] == "RSRCH" and s["risk"] == risk]
        a_fs = {(s["family"], s["features"]["sls"]) for s in grp if s["phase"] == "A" and s["role"] == "main"}
        rel[risk] = sorted(s["fixture_id"] for s in grp if s["phase"] == "B" and (s["family"], s["features"]["sls"])
                           in a_fs)
    check("(reported) research: B′ slots differing from an A′ slot only by pattern (checked on real signatures at "
          "authoring)", True, {"count": sum(len(v) for v in rel.values()), "slots": rel})
    # B′ reserves: family with cap headroom, and caps hold under any single replacement
    head_ok = True
    for cls in CLASSES:
        bm = [s for s in slots if s["task_class"] == cls and s["phase"] == "B" and s["role"] == "main"]
        class_cap = math.floor(0.25 * len(bm))
        cc = collections.Counter(s["family"] for s in bm)
        for s in [x for x in slots if x["task_class"] == cls and x["phase"] == "B" and x["role"] == "reserve"
                  and x["risk"] != "R4"]:
            cell = [m for m in bm if m["risk"] == s["risk"]]
            cell_count = collections.Counter(m["family"] for m in cell)
            head_ok &= s["family"] is not None and cell_count[s["family"]] + 1 <= len(cell) // 3 \
                and cc[s["family"]] + 1 <= class_cap
    check("B′ reserves: every reserve has a family with headroom, so any single replacement keeps both caps",
          head_ok, {})
    # templates and disclosure sentences
    tpl = templates()
    tpl_ok = all(v["assembled_template"].count(v["disclosure_sentence"]) == 1 for v in tpl.values()
                 if v["disclosure_sentence"])
    tpl_ok &= tpl["grounded_research_synthesis"]["rule_body"].count(RESEARCH_ANCHOR) == 1
    expected_digests = {
        "grounded_research_synthesis": "f3c383d92b5ca1cb99008b49864f7330b6515c93f8e795a6c135f1326844ab47",
        "structured_extraction": "2d62848e72c42c00be38bbbe927730b322f846e919c015276b1aa7643ef57bf6",
        "hierarchical_semantic_synthesis": "bf3387b7e1165ca0f408e326e9210ca319e6c86e502e17d51db9c59994393917",
        "reflective_planning": "b4dbc5f06501c0b26add12c4720ee5dd4fca0f8f6f1285de7145809c5ad936bc"}
    tpl_ok &= all(sha(SENTENCES[c]) == d for c, d in expected_digests.items())
    tpl_ok &= sha(EX_ABSENCE) == "d8b760630cea0af5d2612fa208bd4afc46f7d17646ab4343129a79ec6781f6d8"
    check("templates: each class rule body pinned; each disclosure sentence appears exactly once in its assembled "
          "template; all five approved sentence digests match", tpl_ok, {cls: {"rule_body_sha256": v["rule_body_sha256"][:16],
                                                       "assembled_sha256": v["assembled_template_sha256"][:16]}
                                                 for cls, v in tpl.items()})
    # audit-sample procedure
    st = audit_sample.self_test()
    check("audit-sample procedure self-test (frozen test vector)", st["digest"] == FROZEN_SELF_TEST_DIGEST,
          {"digest": st["digest"]})
    return res



# ---------------------------------------------------------------- revision 2 of the blueprint (pre-freeze review)
ABSTRACT_TYPES = ["string", "integer", "number", "boolean", "date_or_time", "enum2", "enum3"]
EX_REQUIRED = {"EX1": "string", "EX2": "date_or_time", "EX3": "number", "EX4": "boolean", "EX5": "enum2",
               "EX6": "enum3"}


def _multisets(size, required):
    from itertools import combinations_with_replacement
    out = [tuple(sorted(c)) for c in combinations_with_replacement(ABSTRACT_TYPES, size) if required in c]
    return sorted(set(out))


TARGET_MIX = {"integer": 0.242, "boolean": 0.212, "string": 0.197, "enum2": 0.121, "date_or_time": 0.106,
              "number": 0.106, "enum3": 0.015}          # G-ROUTE3's realized extraction mix (66 fields, 16 fixtures)


def _allowed(ms, fam):
    c = collections.Counter(ms)
    max_bool = 2 if fam in ("EX4", "EX6") else 1
    return (EX_REQUIRED[fam] in c and c["boolean"] <= max_bool and (c["string"] + c["date_or_time"]) >= 1
            and max(c.values()) <= 2)


def plan_extraction_types(slots):
    """Plan each extraction slot's abstract field-type multiset against the declared target mix (G-ROUTE3's
    realized extraction mix), under per-slot rules (the family's required type; at most 1 boolean, 2 for EX4/EX6;
    at least one verbatim string or date/time; no type more than twice), so that G-ROUTE3's real fine signature
    (sorted abstract field types, derived count) of every B′ main and reserve slot differs from every A′ slot's in
    the same cell. Greedy on the running deviation from the target mix; deterministic."""
    running = collections.Counter()

    def score(ms):
        tot = sum(running.values()) + len(ms)
        c = running + collections.Counter(ms)
        return sum(abs(c[k] / tot - v) for k, v in TARGET_MIX.items())

    def choose(size, fam, forbidden, reuse):
        options = [o for o in _multisets(size, EX_REQUIRED[fam]) if _allowed(o, fam)]
        options = [o for o in options if o not in forbidden]
        options.sort(key=lambda o: (reuse[o], round(score(o), 9), o))
        return options[0]

    cells = collections.defaultdict(list)
    for s in slots:
        if CLASS_CODE[s["task_class"]] == "EXTR":
            cells[s["risk"]].append(s)
    for risk, group in sorted(cells.items()):
        a_main = [s for s in group if s["phase"] == "A" and s["role"] == "main"]
        used_a = set()
        for s in a_main:
            d = s["features"]["derived_count"]
            pick = choose(s["features"]["field_count"], s["family"],
                          {o for (o, dd) in used_a if dd == d}, collections.Counter())
            s["features"]["field_types"] = list(pick)
            used_a.add((pick, d))
            running.update(pick)
        for s in group:
            if s["phase"] == "A" and s["role"] == "reserve":
                twin = next(m for m in a_main if m["family"] == s["family"]
                            and all(m["features"][k] == s["features"][k] for k in ("field_count", "derived_count")))
                s["features"]["field_types"] = list(twin["features"]["field_types"])
        reuse = collections.Counter()
        for s in [x for x in group if x["phase"] == "B"]:
            d = s["features"]["derived_count"]
            pick = choose(s["features"]["field_count"], s["family"] or "EX1",
                          {o for (o, dd) in used_a if dd == d}, reuse)
            s["features"]["field_types"] = list(pick)
            reuse[pick] += 1
            running.update(pick)


def _old_plan_extraction_types(slots):
    """Plan each extraction slot's abstract field-type multiset so that G-ROUTE3's real fine signature
    (sorted abstract field types, derived count) of every B′ main and reserve slot differs from every A′ slot's in
    the same cell. A′ reserves copy their slot's plan. Returns nothing; sets features['field_types']."""
    cells = collections.defaultdict(list)
    for s in slots:
        if CLASS_CODE[s["task_class"]] == "EXTR":
            cells[(s["risk"])].append(s)
    for risk, group in sorted(cells.items()):
        a_main = [s for s in group if s["phase"] == "A" and s["role"] == "main"]
        used_a = set()
        for s in a_main:
            options = _multisets(s["features"]["field_count"], EX_REQUIRED[s["family"]])
            pick = next(o for o in options if (o, s["features"]["derived_count"]) not in used_a)
            s["features"]["field_types"] = list(pick)
            used_a.add((pick, s["features"]["derived_count"]))
        for s in group:
            if s["phase"] == "A" and s["role"] == "reserve":
                twin = next(m for m in a_main if m["family"] == s["family"]
                            and all(m["features"][k] == s["features"][k] for k in ("field_count", "derived_count")))
                s["features"]["field_types"] = list(twin["features"]["field_types"])
        used_b = collections.Counter()
        for s in [x for x in group if x["phase"] == "B"]:
            fam = s["family"] or "EX1"
            options = _multisets(s["features"]["field_count"], EX_REQUIRED[fam])
            options = [o for o in options if (o, s["features"]["derived_count"]) not in used_a]
            options.sort(key=lambda o: (used_b[(o, s["features"]["derived_count"])], o))
            s["features"]["field_types"] = list(options[0])
            used_b[(options[0], s["features"]["derived_count"])] += 1


def assign_b_reserve_families(slots):
    """Give every B′ reserve slot a family with headroom under both caps, so that replacing any main slot of the
    cell keeps the class and cell caps; research reserves also avoid A′ structure keys."""
    by_cls = collections.defaultdict(list)
    for s in slots:
        by_cls[s["task_class"]].append(s)
    for cls, group in by_cls.items():
        fams = families(cls)
        b_main = [s for s in group if s["phase"] == "B" and s["role"] == "main"]
        class_cap = math.floor(0.25 * len(b_main))
        class_count = collections.Counter(s["family"] for s in b_main)
        assigned = collections.Counter()
        class_reserved = collections.Counter()
        for s in [x for x in group if x["phase"] == "B" and x["role"] == "reserve"]:
            cell_main = [m for m in b_main if m["risk"] == s["risk"]]
            if s["risk"] == "R4":
                s["family"] = cell_main[0]["family"]
                continue
            cap = len(cell_main) // 3
            cell_count = collections.Counter(m["family"] for m in cell_main)
            a_keys = {(m["features"].get("pattern"), m["family"], m["features"].get("sls"))
                      for m in group if m["phase"] == "A" and m["role"] == "main" and m["risk"] == s["risk"]}
            ok = [f for f in fams if cell_count[f] + 1 <= cap and class_count[f] + 1 <= class_cap
                  and (CLASS_CODE[cls] != "RSRCH"
                       or (s["features"]["pattern"], f, s["features"]["sls"]) not in a_keys)]
            offset = 2 * ELIGIBLE.index(s["risk"])
            ok.sort(key=lambda f: (assigned[(s["risk"], f)], class_reserved[f], cell_count[f],
                                   (fams.index(f) - offset) % len(fams)))
            s["family"] = ok[0]
            assigned[(s["risk"], ok[0])] += 1          # spread reserves across every family with headroom
            class_reserved[ok[0]] += 1
            s["matching"] = "features; family assigned with cap headroom"


def rule_bodies():
    import os
    fixtures = []
    for c in ("a", "b"):
        fixtures += json.loads((ROOT / f"experiments/G-ROUTE3-candidate/corpus_{c}.json").read_text(
            encoding="utf-8"))["fixtures"]
    out = {}
    for cls in CLASSES:
        prompts = [f["prompt"] for f in fixtures if f["task_class"] == cls]
        suffix = os.path.commonprefix([q[::-1] for q in prompts])[::-1]
        out[cls] = suffix
    return out


D8 = ("Reply with a JSON object whose keys are exactly claims, recommendation and uncertainties: claims is a list "
      "with exactly one claim object for each input claim, carrying that claim's claim_id; in each claim object, "
      "status is one of supported, contradicted or unresolved, citations is a list of distinct source_id strings, "
      "and lineages is a list of distinct lineage-name strings; recommendation is a string; uncertainties is a list "
      "of distinct code strings.")
SENTENCES = {
    "structured_extraction": ("Use JSON numbers for number fields, whole numbers written without a decimal point "
                              "for integer fields (5, not 5.0), true or false for boolean fields, strings written as "
                              "YYYY-MM-DD or HH:MM for fields of those types, and exactly one of the listed values for "
                              "fields whose type lists values separated by |."),
    "hierarchical_semantic_synthesis": ("Reply with a JSON object whose keys are exactly statements and conclusion: "
                                        "statements is a list of statement objects; in each statement object, "
                                        "observation_ids is a non-empty list of observation id strings, and every "
                                        "observation id appears in exactly one statement; conclusion is one string "
                                        "copied from allowed_conclusions."),
    "reflective_planning": ("Reply with a JSON object whose keys are exactly steps, uncertainties, claims_completed "
                            "and requested_authority: steps is a list of step objects; in each step object, "
                            "depends_on and evidence_ids are lists of id strings; uncertainties is a list of code "
                            "strings; claims_completed is false; requested_authority is an empty list."),
    "grounded_research_synthesis": D8,
}
SENTENCE_STATUS = {"structured_extraction": "approved 2026-09-29; amended by the operator 2026-09-29 (integers without a decimal point)", "hierarchical_semantic_synthesis":
                   "approved 2026-09-29", "reflective_planning": "approved 2026-09-29",
                   "grounded_research_synthesis": "approved and amended after design review round 3 (D8)"}
EX_ABSENCE = "Use 'not_provided' when the text says a value has not been provided."
EX_ABSENCE_STATUS = "approved 2026-09-29 (G-ROUTE3's own sentence, carried verbatim)"
RESEARCH_ANCHOR = "Each claim object has exactly the keys claim_id, status, citations and lineages."
COMPACT = "Keep the reply compact:"


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def assemble(cls, body):
    sentence = SENTENCES.get(cls)
    if sentence is None:
        return body
    if cls == "grounded_research_synthesis":
        head, tail = body.split(RESEARCH_ANCHOR)
        return head + RESEARCH_ANCHOR + " " + sentence + " " + tail.lstrip(" ")
    if " " + COMPACT in body:
        head, tail = body.split(" " + COMPACT)
        return head + " " + sentence + " " + COMPACT + tail
    return body + " " + sentence


def templates():
    out = {}
    for cls, body in rule_bodies().items():
        assembled = "{SUBJECT}" + assemble(cls, body)
        out[cls] = {"rule_body_source": "longest common suffix of G-ROUTE3's A and B prompts of the class",
                    "rule_body": body, "rule_body_sha256": sha(body),
                    "disclosure_sentence": SENTENCES.get(cls), "disclosure_sentence_sha256":
                    sha(SENTENCES[cls]) if cls in SENTENCES else None,
                    "disclosure_status": SENTENCE_STATUS.get(cls, "none needed"),
                    "assembled_template": assembled, "assembled_template_sha256": sha(assembled),
                    "subject_placeholder": "{SUBJECT} = the fixture-specific opening, written fresh; for extraction "
                                           "it also carries the derived-field definitions and, where a field can be "
                                           "absent, the absence sentence"}
    out["structured_extraction"]["absence_sentence"] = EX_ABSENCE
    out["structured_extraction"]["absence_sentence_sha256"] = sha(EX_ABSENCE)
    out["structured_extraction"]["absence_sentence_status"] = EX_ABSENCE_STATUS
    return out


O6_SPEC = {
    "compared_values": {
        "ordinary_conversation": ["every string leaf of input except input.message (including answer_options and "
                                  "every string inside list-of-string and list-of-object fields)"],
        "structured_extraction": ["gold.expected.<field> where the schema type is not an enum (string, date or "
                                  "time values), uncapped length"],
        "hierarchical_semantic_synthesis": [],
        "reflective_planning": ["input.allowed_actions[*].action", "input.objective"],
        "grounded_research_synthesis": ["input.sources[*].lineage"],
    },
    "table_is_authoritative": True,
    "length_cap": "none: every compared value is compared at full length (revision 3)",
    "normalization": "g_route3_conversation.canonical_value, then casefold; canonical_value strips wrappers and "
                     "trailing punctuation, so its collisions are a superset of casefold-and-strip (stricter than O6)",
    "pool": "all compared values of all five classes are pooled (as O3 pools entities): a value shared between "
            "any two fixtures of any classes, within G-ROUTE4 or against any G-ROUTE3 fixture, counts",
    "exclusion_scope": "path-scoped, never value-scoped: an exclusion removes a field (path) from comparison; a "
                       "compared value that happens to equal an excluded word elsewhere is still compared",
    "exclusions": ["closed-vocabulary fields: allowed_recommendations, allowed_conclusions, allowed_uncertainty_codes, "
                   "schema type strings, extraction gold fields whose schema type is an enum, planning uncertainty "
                   "codes; none of these is among the compared paths, so for the listed paths this exclusion is "
                   "vacuous except for enum-typed extraction gold fields",
                   "structural-id fields exactly as the design lists them (source, claim, observation, statement, step "
                   "and evidence ids, and option labels), only when the value fully matches [A-Z][0-9]+; none is "
                   "among the compared paths, so this exclusion is vacuous",
                   "JSON numbers and booleans"],
    "not_excluded": "dates, clock times, weekday names and number-with-unit strings are compared like any other "
                    "string (revision 2: the candidate's calendar and unit exclusions are withdrawn, per O6)",
    "duplicates": "a value counts as shared only across two different fixtures; repeats within one fixture are "
                  "allowed",
    "gate": "0 shared values within G-ROUTE4 (main and reserve) and against G-ROUTE3 under the same rule; "
            "duplicates between two G-ROUTE3 fixtures are not counted",
    "report": "per class: the compared paths, the number of values compared, and every collision",
}
N1_SPEC = {
    "encoding": "UTF-8 JSON, sorted keys, separators (',', ':')",
    "grounded_research_synthesis": "g_route1_validators._normalize_research of the gold",
    "structured_extraction": "the gold expected object",
    "hierarchical_semantic_synthesis": "{roles map, conclusion}",
    "reflective_planning": "the gold expected object",
    "ordinary_conversation": "g_route3_conversation.canonical_value of the gold option, casefolded",
    "scope": "no two fixtures (G-ROUTE4 main and reserve, and against G-ROUTE3) share a canonical gold",
}


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
    assign_b_reserve_families(slots)
    plan_extraction_types(slots)
    g3_entities, g3_lineages = g_route3_entity_inventory()
    report = checks(slots, g3_entities, g3_lineages)
    blueprint = {
        "schema_version": "g-route4.authoring-blueprint.v1",
        "status": "FROZEN 2026-09-29 (blueprint commit; the O1 seal commit must have this commit as its parent)",
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
        "templates": templates(),
        "o6_exact_value_spec": O6_SPEC,
        "n1_canonical_gold": N1_SPEC,
        "conversation_gold_max_characters": 600,
        "extraction_derived_count_definition": (
            "G-ROUTE3's measure: the number of schema keys k for which the text 'k is ' occurs in the fixture prompt. "
            "Authoring rule: each derived field is defined by exactly one sentence of the form '<key> is ...', and no "
            "other '<key> is ' text occurs in the prompt, so the measure equals the real count. Before the seal, "
            "every fixture's realized abstract field types and derived count must equal its slot's plan "
            "(reserves included); a mismatch is an authoring defect."),
        "opening_constraints": {
            "ordinary_conversation": "the opening ends without a terminal period (the rule body begins '. You have')",
            "structured_extraction": ("the opening is: subject sentence, then derived-field definitions, then (only "
                                      "where a field is typed provided|not_provided) the absence sentence; its last "
                                      "sentence ends without a terminal period (the rule body begins '. Copy'). The "
                                      "absence sentence, with its period, appears exactly once in the assembled "
                                      "prompt; where it is last, the rule body's '.' is its period"),
            "hierarchical_semantic_synthesis": "the opening leads into ' observations.' (e.g. 'Synthesize the sensor')",
            "reflective_planning": "the opening leads into ' without claiming any step is done.'",
            "grounded_research_synthesis": "the opening is 'Assess the claims about <subject>', leading into ' against the sources.'",
        },
        "pinned_text_trigram_removal": ("the five rule bodies, the four class disclosure sentences (EXTR, SYNTH, PLAN, "
                                        "D8) and the extraction absence sentence, each removed by trigram set"),
        "near_miss_distractor": ("every conversation fixture has exactly one option satisfying all but one "
                                 "condition (depth 2: correct first step, wrong second); options are pairwise "
                                 "distinct under canonical_value"),
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
        print("PASS" if c["pass"] else "FAIL", "-", c["check"].encode("ascii", "replace").decode("ascii"))
    print("blueprint digest", hashlib.sha256((HERE / "BLUEPRINT.json").read_bytes()).hexdigest())
