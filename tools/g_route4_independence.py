# forked from g_route3_independence
from __future__ import annotations

"""G-ROUTE4 independence module: the design's independence standard over the final G-ROUTE4 corpus.

Design (DESIGN_CANDIDATE.md, "Independence standard"; G-ROUTE4_OBLIGATIONS.md O3, O4, O5, O6, N1, N3, N7, N8, N9):
the measured standard of the G-ROUTE3 module is the floor, computed by this fork.

- The G-ROUTE3 core is carried byte-identical (N9): the tokenizer, the exemption lists, the content function, the
  entity detector, the field-type abstraction and the fine gold signature. The fork only drops the module's
  contract-module import and adds the G-ROUTE4 standard below.
- One pool per class: every sealed G-ROUTE4 fixture (main and reserve) with the recorded fixes overlaid (N7: a fixed
  text replaces its old text; boilerplate is recomputed over the whole pool), plus the prior experiment's A and B
  fixtures of the class, read-only.
- Word-trigram Jaccard at most 0.20 for every pair (same-family included), after trigram-set removal of the pinned
  texts and the 25%-frequency boilerplate rule; measured on full content and on ledger-bound (task-relevant) text.
- O3: 0 shared named entities (the carried detector; lowercase vocabulary per class pool) and 0 shared identifiers
  (the binding prospective identifier gate), across every class and against the prior experiment.
- O5: no boilerplate trigram in a frozen family template, and none specific to a single family.
- O6: 0 shared exact structured values. N1: no identical canonical gold. Research source lineages and planning action
  names never repeat across fixtures.
- Gold structure: the fine signature is not repeated between A′ and B′ in a cell (research, extraction), nor the
  canonical research signature (decision clause normalized) within a risk class. Conversation has no signature (O4);
  planning and synthesis are exempt (declared). Conversation gold positions are balanced per cell.
- N8: the maximum same-family A′–B′ Jaccard per cell (main corpora), reported.

It reads corpora and gold together, which is permissible only because it runs before any contact with the tested
models and is never imported by collection, routing or scoring.

    python -B tools/g_route4_independence.py [OUT.json]
"""

from collections import Counter, defaultdict
from itertools import product
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import g_route1_validators as G1V  # noqa: E402  (imported unchanged; research gold normalization for N1)
from g_route3_conversation import canonical_value  # noqa: E402  (imported unchanged)

CONTRACT_VERSION = "g-route4.independence.v1"
ROOT = Path(__file__).resolve().parents[1]
CAND = ROOT / "experiments/G-ROUTE4-candidate"
SEALED = CAND / "sealed"
FIXES = CAND / "adjudication/fixes"
PRIOR = ROOT / "experiments/G-ROUTE3-candidate"            # read-only comparison set (allowlisted reference)

# ---------------------------------------------------------------- carried core (byte-identical to the original)
MAX_CROSS_CORPUS_TRIGRAM_JACCARD = 0.20
BOILERPLATE_SHARE = 0.25
_WORD = re.compile(r"[a-z0-9][a-z0-9_.\-%:]*")
_ENTITY = re.compile(r"\b(?:[A-Z][a-z]+(?:[A-Z][a-z]+)*|[A-Z]{1,5}-?\d[\w.-]*)\b")
_COMMON = {"The", "A", "An", "Only", "Each", "Every", "No", "Do", "Use", "When", "If", "Plan", "Recommend",
           "Conclude", "Assess", "Synthesize", "Extract", "Repair", "Answer", "Respond", "Tell", "Give", "Offer",
           "Summarize", "Count", "Status", "Include", "Order", "Number", "Set", "List", "Choose", "Restate",
           "Merge", "Cite", "Return", "In", "Not", "Yes", "Our", "Mine", "We", "Your", "It", "This", "Its",
           "Advise", "Explain", "Report", "Decline", "Name", "Name", "Can", "Is", "Has", "Did", "Which", "What",
           "How", "Storage", "Policy", "Press", "Plans", "Weight", "Listed", "Office", "Fully", "Course", "Pause",
           "Delivery", "Backups", "All", "Heavy", "Good", "Applicants", "Edits", "Release", "Firmware", "Panel"}


# Profile-level rule vocabulary shared by design. It defines the task class being qualified,
# is identical wherever it is used, and is declared in the report rather than counted as content.
SHARED_RULE_KEYS = ("allowed_uncertainty_codes", "conclusion_rule", "allowed_conclusions")
# Tokens that come from disclosed profile-level rule text, not fixture content.
SHARED_RULE_TOKENS = {"PurePosixPath"}
_WEEKDAYS_MONTHS = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "January",
                    "February", "March", "April", "May", "June", "July", "August", "September", "October",
                    "November", "December"}


def _content(fixture: dict[str, Any]) -> str:
    data = {k: v for k, v in dict(fixture["input"]).items() if k not in SHARED_RULE_KEYS}
    return fixture["title"] + " " + fixture["prompt"] + " " + json.dumps(data, ensure_ascii=False)


def _named_entities(text: str, lowercase_vocabulary: set[str]) -> set[str]:
    """Proper names and identifiers: mid-sentence capitalized words never used in lowercase,
    and alphanumeric identifiers longer than a structural id such as C1 or F2."""
    out = set()
    for match in re.finditer(r"(?<=[a-z,] )([A-Z][a-z]+(?:[A-Z][a-z]+)*)", text):
        word = match.group(1)
        if (word.lower() not in lowercase_vocabulary and word not in _WEEKDAYS_MONTHS and word not in _COMMON
                and word not in SHARED_RULE_TOKENS):
            out.add(word)
    for match in re.finditer(r"([A-Z]{1,5}-?\d[\w.-]*)", text):
        if not re.fullmatch(r"[A-Z]\d", match.group(1)):
            out.add(match.group(1))
    return out


def _trigrams(text: str) -> set[tuple[str, str, str]]:
    words = _WORD.findall(text.lower())
    return {tuple(words[i:i + 3]) for i in range(len(words) - 2)}



def _field_type(schema: Any) -> str:
    """Abstract schema types so relabelled enum values or date formats cannot hide a shared shape."""
    text = str(schema)
    if "|" in text:
        return f"enum{len(text.split('|'))}"
    if text in ("YYYY-MM-DD", "HH:MM"):
        return "date_or_time"
    return text


def structural_signature(fixture: dict[str, Any], expected: dict[str, Any]) -> Any:
    """Shape of the gold answer, independent of wording and entities. None when no shape is defined."""
    profile = fixture["validator_profile"]
    if profile == "research.v1":
        recommendations = fixture["input"]["allowed_recommendations"]
        return ("research",
                tuple(sorted((c["status"], len(c["citations"]), len(c["lineages"])) for c in expected["claims"])),
                recommendations.index(expected["recommendation"]), tuple(expected["uncertainties"]),
                len(fixture["input"]["sources"]), fixture["input"]["decision_rule"].split(" only if")[1][:40]
                if " only if" in fixture["input"]["decision_rule"] else "")
    if profile == "synthesis.v1":
        return ("synthesis", tuple(sorted(expected["roles"].values())), expected["conclusion"])
    if profile == "extraction.v1":
        derived = sum(f"{key} is " in fixture["prompt"] for key in fixture["input"]["schema"])
        return ("extraction", tuple(sorted(_field_type(v) for v in fixture["input"]["schema"].values())), derived)
    if profile == "planning.v1":
        return ("planning", len(expected["steps"]), len(fixture["input"]["allowed_actions"]),
                len(fixture["input"]["evidence"]), len(expected["uncertainties"]))
    return None


# ---------------------------------------------------------------- G-ROUTE4 standard
# The binding prospective O3 identifier gate (sealed/O3_IDENTIFIER_DECISION.md): the evident intended pattern of the
# carried detector's identifier branch, pinned by digest; structural ids in structural-id fields are excluded.
IDENT_INTENDED = re.compile(r"\b([A-Z]{1,5}-?\d[\w.-]*)\b")
IDENT_GATE_PATTERN_SHA256 = "a3773a982c16579d94cede99539e0b9cacca1347f96774759a84bbb7788adaae"
STRUCTURAL_KEYS = {"id", "source_id", "claim_id", "statement_id", "addresses", "citations", "observation_ids",
                   "evidence_ids", "depends_on", "label", "option_label"}
# The final corpus: the seal with every recorded fix overlaid, in order (no replacement). Each fix record is pinned by
# its LF-normalized digest, so a changed record cannot silently change the pool.
FIX_ROUNDS = (
    ("round1_bmain", "corpus_b.json", "gold_b.json", "d4f81a8e3b439b070fa49e81a344a8e28bbe2640faf29de1a6b0e8e8d5f1f7a2"),
    ("round1_amain", "corpus_a.json", "gold_a.json", "661b75ce861ef545e9ccf21d7ecc6960a29ee8f2e7d8fd37124f9dffa7803677"),
    ("cr1_amain", "corpus_a.json", "gold_a.json", "31ebc828c138e22d9a4bf535fb8ab6cd57b3983317aadab89d230d65cc09a89f"),
    ("cr1_bmain", "corpus_b.json", "gold_b.json", "e9dad640733f1b1d0881c73a8e7cdf4424b7b195425f72115e84e5d9199d0d10"),
)
SEALED_FILES = (("corpus_a.json", "gold_a.json"), ("corpus_b.json", "gold_b.json"),
                ("reserve_corpus_a.json", "reserve_gold_a.json"), ("reserve_corpus_b.json", "reserve_gold_b.json"))
# Canonical research signature: the decision enters only as what it decides on.
DECISION_CLASS = {"focal_two_lineages": "focal_c1_two_lineages", "all_supported": "every_claim_supported",
                  "temporal_all_supported": "every_claim_supported"}


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256(data: str | bytes) -> str:
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode("utf-8")).hexdigest()


def lf_sha256(path: Path) -> str:
    return sha256(Path(path).read_bytes().replace(b"\r\n", b"\n"))


def _load(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def classify_decision(text: str, positive: str, negative: str) -> str | None:
    """A research decision rule normalized to its canonical clause kind, or None when it is not exactly one kind."""
    norm = text.casefold().replace(f"'{positive}'".casefold(), " zzposrec ").replace(f"'{negative}'".casefold(),
                                                                                    " zznegrec ")
    norm = " ".join(re.sub(r"[^a-z0-9 ]", " ", norm).split())
    if norm.split().count("zzposrec") != 1 or norm.split().count("zznegrec") != 1:
        return None
    temporal = any(m in norm for m in ("later dated", "later date", "more recent", "newer", "most recent",
                                       "dated later")) and any(m in norm for m in ("cite", "cited", "citing"))
    focal = "c1" in norm and any(m in norm for m in ("two lineages", "two or more", "2 lineages")) and "lineage" in norm
    every = any(m in norm for m in ("every claim", "all claims", "each claim", "all of the claims",
                                    "no claim is left unsupported"))
    kinds = [k for k, flag in (("temporal_all_supported", temporal and every), ("focal_two_lineages", focal),
                               ("all_supported", every and not temporal)) if flag]
    if temporal and not every:
        return None
    return kinds[0] if len(kinds) == 1 else None


def research_canonical_signature(fixture: dict[str, Any], expected: dict[str, Any]) -> str:
    recommendations = fixture["input"]["allowed_recommendations"]
    kind = classify_decision(fixture["input"].get("decision_rule", ""), *recommendations)
    return canonical_json(["research", sorted([c["status"], len(c["citations"]), len(c["lineages"])]
                                              for c in expected["claims"]),
                           recommendations.index(expected["recommendation"]), list(expected["uncertainties"]),
                           len(fixture["input"]["sources"]), DECISION_CLASS.get(kind)])


def structural_ids(value: Any, key: str | None = None) -> set[str]:
    out: set[str] = set()
    if isinstance(value, dict):
        for k, v in value.items():
            out |= structural_ids(v, k)
    elif isinstance(value, list):
        for v in value:
            out |= structural_ids(v, key)
    elif isinstance(value, str) and key in STRUCTURAL_KEYS and re.fullmatch(r"[A-Z][0-9]+", value):
        out.add(value)
    return out


def intended_identifiers(fixture: dict[str, Any], text: str) -> set[str]:
    skip = structural_ids(fixture.get("input", {}))
    return {m for m in IDENT_INTENDED.findall(text) if not re.fullmatch(r"[A-Z]\d", m) and m not in skip}


def o6_values(fixture: dict[str, Any], gold: dict[str, Any]) -> dict[str, str]:
    """The frozen O6 compared values (blueprint §7), path-scoped, canonicalized: {value: path}."""
    vals: dict[str, str] = {}
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
    pairs: list[tuple[str, str]] = []
    if tc == "ordinary_conversation":
        for k, v in inp.items():
            if k != "message":
                pairs += list(leaves(v, f"input.{k}"))
    elif tc == "structured_extraction":
        for k, t in inp["schema"].items():
            if "|" not in str(t) and isinstance(gold["expected"].get(k), str):
                pairs.append((f"expected.{k}", gold["expected"][k]))
    elif tc == "reflective_planning":
        pairs += [(f"input.allowed_actions[{i}].action", a["action"]) for i, a in enumerate(inp.get("allowed_actions", []))]
        if isinstance(inp.get("objective"), str):
            pairs.append(("input.objective", inp["objective"]))
    elif tc == "grounded_research_synthesis":
        pairs += [(f"input.sources[{i}].lineage", s["lineage"]) for i, s in enumerate(inp.get("sources", []))]
    for path, v in pairs:
        if v.strip():
            vals[canonical_value(v).casefold()] = path
    return vals


def canonical_gold(fixture: dict[str, Any], gold: dict[str, Any]) -> str | None:
    tc, expected = fixture["task_class"], gold["expected"]
    if tc in ("structured_extraction", "reflective_planning"):
        value: Any = expected
    elif tc == "hierarchical_semantic_synthesis":
        value = {"roles": expected["roles"], "conclusion": expected["conclusion"]}
    elif tc == "ordinary_conversation":
        value = canonical_value(expected["answer"]).casefold()
    elif tc == "grounded_research_synthesis":
        reasons: list[str] = []
        value = G1V._normalize_research(expected, reasons)
        if reasons:
            raise ValueError(f"{fixture['fixture_id']}: research gold cannot be normalized: {reasons}")
    else:
        return None
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def task_units(fixture: dict[str, Any], gold: dict[str, Any], ledger: dict[str, Any]) -> list[str] | None:
    """The fixture's ledger-bound free-text sentences (the pre-seal task-relevant gate); None for other classes."""
    tc = fixture["task_class"]
    if tc == "grounded_research_synthesis":
        contract = ledger.get("research_contract") or {}
        return [c["text"] for c in contract.get("claims", [])] + [s["text"] for s in contract.get("sources", [])]
    if tc == "ordinary_conversation":
        return [str(u.get("text")) for u in ledger.get("message_units", []) if u.get("facts")]
    if tc == "hierarchical_semantic_synthesis":
        terms = gold["expected"].get("required_terms", {})
        return [o["text"] for o in fixture["input"]["observations"] if terms.get(o["id"])]
    return None


def task_relevant_fixture(fixture: dict[str, Any], units: list[str] | None) -> dict[str, Any]:
    if units is None:
        return fixture
    out = json.loads(json.dumps(fixture))
    keep, inp = set(units), out["input"]
    if fixture["task_class"] == "ordinary_conversation":
        inp["message"] = " ".join(units)
    elif fixture["task_class"] == "hierarchical_semantic_synthesis":
        inp["observations"] = [o for o in inp.get("observations", []) if o.get("text") in keep]
    elif fixture["task_class"] == "grounded_research_synthesis":
        inp["claims"] = [c for c in inp.get("claims", []) if c.get("text") in keep]
        inp["sources"] = [s for s in inp.get("sources", []) if s.get("text") in keep]
    return out


# ---------------------------------------------------------------- inputs
def load_final_pool() -> dict[str, Any]:
    """The final G-ROUTE4 pool (seal + recorded fixes), the blueprint and the prior experiment's fixtures."""
    fixtures, gold = {}, {}
    for corpus, gold_file in SEALED_FILES:
        fixtures.update({f["fixture_id"]: f for f in _load(SEALED / corpus)["fixtures"]})
        gold.update({g["fixture_id"]: g for g in _load(SEALED / gold_file)["items"]})
    ledger = {d["fixture_id"]: d for d in _load(SEALED / "authoring_ledger.json")["items"]}
    sealed_fixtures, sealed_gold, sealed_ledger = dict(fixtures), dict(gold), dict(ledger)
    applied: dict[str, list[str]] = {}
    for sub, corpus, gold_file, pinned in FIX_ROUNDS:
        folder = FIXES / sub
        if lf_sha256(folder / "FIX_RECORD.json") != pinned:
            raise ValueError(f"fix record {sub} differs from its pinned digest")
        record = {r["fixture_id"]: r for r in _load(folder / "FIX_RECORD.json")["fixes"]}
        parts = {"fixture": _load(folder / "corpus_fixed.json")["fixtures"], "gold": _load(folder / "gold_fixed.json")["items"],
                 "ledger": _load(folder / "ledger_fixed.json")["items"]}
        for part, rows in parts.items():
            target, sealed = {"fixture": (fixtures, sealed_fixtures), "gold": (gold, sealed_gold),
                              "ledger": (ledger, sealed_ledger)}[part]
            for row in rows:
                fid = row["fixture_id"]
                rec = record[fid]
                if fid in applied.get("all", []) and part == "fixture":
                    raise ValueError(f"{fid}: fixed twice")
                if sha256(canonical_json(sealed[fid])) != rec["sealed_sha256"][part] or \
                        sha256(canonical_json(row)) != rec["fixed_sha256"][part]:
                    raise ValueError(f"{fid}: {part} is not bound to its recorded sealed and fixed digests")
                target[fid] = row
        applied[sub] = sorted(record)
        applied.setdefault("all", []).extend(sorted(record))
    prior = []
    for c in ("a", "b"):
        g3_gold = {g["fixture_id"]: g for g in _load(PRIOR / f"gold_{c}.json")["items"]}
        prior += [(f, g3_gold[f["fixture_id"]]) for f in _load(PRIOR / f"corpus_{c}.json")["fixtures"]]
    blueprint = _load(CAND / "blueprint/BLUEPRINT.json")
    return {"fixtures": fixtures, "gold": gold, "ledger": ledger, "prior": prior, "blueprint": blueprint,
            "fixes_applied": {k: v for k, v in applied.items() if k != "all"}}


# ---------------------------------------------------------------- the audit
def audit(pool: dict[str, Any] | None = None) -> dict[str, Any]:
    pool = pool or load_final_pool()
    fixtures, gold, ledger, prior, blueprint = (pool["fixtures"], pool["gold"], pool["ledger"], pool["prior"],
                                                pool["blueprint"])
    slots = {s["fixture_id"]: s for s in blueprint["slots"]}
    templates = blueprint["templates"]
    absence = templates["structured_extraction"]["absence_sentence"]
    pinned_texts = [t["rule_body"] for t in templates.values()] + \
        [t["disclosure_sentence"] for t in templates.values() if t["disclosure_sentence"]] + [absence]
    pinned = set()
    for text in pinned_texts:
        pinned |= _trigrams(text)
    findings: list[str] = []
    g4 = sorted(fixtures)
    classes = sorted({fixtures[f]["task_class"] for f in g4})
    rows = [(fixtures[f], "g4") for f in g4] + [(f, "prior") for f, _ in prior]
    content = {(f["fixture_id"], src): _content(f) for f, src in rows}

    # trigram overlap on full content, and on ledger-bound (task-relevant) text
    def jaccard(contents, label, o5):
        by_class = defaultdict(list)
        for f, src in rows:
            by_class[f["task_class"]].append((f["fixture_id"], src, _trigrams(contents[f["fixture_id"], src]) - pinned))
        out, sets = {}, {}
        for tc in classes:
            members = by_class[tc]
            freq = Counter(tg for _, _, s in members for tg in s)
            boiler = {tg for tg, n in freq.items() if n >= BOILERPLATE_SHARE * len(members)}
            reduced = [(fid, src, s - boiler) for fid, src, s in members]
            best, over = (0.0, "", ""), 0
            for i in range(len(reduced)):
                for j in range(i + 1, len(reduced)):
                    a, b = reduced[i], reduced[j]
                    if a[1] == "prior" and b[1] == "prior":
                        continue
                    u = a[2] | b[2]
                    jac = len(a[2] & b[2]) / len(u) if u else 0.0
                    if jac > best[0]:
                        best = (jac, a[0], b[0])
                    if jac > MAX_CROSS_CORPUS_TRIGRAM_JACCARD:
                        over += 1
                        findings.append(f"{label} {jac:.3f} > 0.20: {a[0]} vs {b[0]}")
            out[tc] = {"pool": len(members), "boilerplate_trigrams": len(boiler), "max_jaccard": round(best[0], 4),
                       "max_pair": sorted(best[1:]), "pairs_over_bound": over}      # an unordered pair, sorted
            sets[tc] = {"reduced": reduced, "boilerplate": boiler, "freq": freq}
            if o5:
                single = []
                for tg in boiler:
                    fams = {slots[fid]["family"] for fid, src, s in members if src == "g4" and tg in s}
                    if len(fams) == 1:
                        single.append((" ".join(tg), next(iter(fams))))
                for tg, fam in sorted(single):
                    findings.append(f"O5: boilerplate trigram '{tg}' is specific to family {fam}")
                out[tc]["o5_single_family_boilerplate"] = len(single)
                in_template = [{"family": fam, "trigram": " ".join(tg), "pool_frequency": freq[tg]}
                               for fam, text in sorted(blueprint["classes"][tc]["family_template_text"].items())
                               for tg in sorted(_trigrams(text) & boiler)]
                for row in in_template:
                    findings.append(f"O5: boilerplate trigram '{row['trigram']}' occurs in family template {row['family']}")
                out[tc]["o5_boilerplate_in_family_templates"] = in_template
        return out, sets

    trigram, sets = jaccard(content, "trigram Jaccard", True)
    relevant = dict(content)
    for fid in g4:
        units = task_units(fixtures[fid], gold[fid], ledger[fid])
        relevant[fid, "g4"] = _content(task_relevant_fixture(fixtures[fid], units))
    trigram_relevant, _ = jaccard(relevant, "task-relevant trigram Jaccard", False)

    # N8: maximum same-family A′–B′ Jaccard per cell, main corpora
    n8 = {}
    for tc in classes:
        main = [(fid, s) for fid, src, s in sets[tc]["reduced"] if src == "g4" and slots[fid]["role"] == "main"]
        for risk in ("R1", "R2", "R3", "R4"):
            best, pairs = None, 0
            for fa, sa in main:
                if slots[fa]["phase"] != "A" or slots[fa]["risk"] != risk:
                    continue
                for fb, sb in main:
                    if slots[fb]["phase"] == "B" and slots[fb]["risk"] == risk and slots[fb]["family"] == slots[fa]["family"]:
                        pairs += 1
                        u = sa | sb
                        jac = len(sa & sb) / len(u) if u else 0.0
                        if best is None or jac > best[0]:
                            best = (jac, fa, fb, slots[fa]["family"])
            n8[f"{tc}|{risk}"] = ({"same_family_pairs": pairs, "max_jaccard": round(best[0], 4),
                                   "max_pair": [best[1], best[2]], "family": best[3]} if pairs else
                                  {"same_family_pairs": 0, "max_jaccard": None, "max_pair": None, "family": None})

    # O3 named entities: lowercase vocabulary per class pool; prior fixtures also screened with their own vocabulary
    vocab = defaultdict(set)
    for f, src in rows:
        vocab[f["task_class"]] |= set(re.findall(r"(?<![A-Za-z])[a-z]+", content[f["fixture_id"], src]))
    prior_vocab = {w for f, _ in prior for w in re.findall(r"(?<![A-Za-z])[a-z]+", _content(f))}
    ents = {}
    for f, src in rows:
        e = _named_entities(content[f["fixture_id"], src], vocab[f["task_class"]])
        if src == "prior":
            e |= _named_entities(content[f["fixture_id"], src], prior_vocab)
        ents[f["fixture_id"], src] = e
    owners = defaultdict(set)
    for key, e in ents.items():
        for x in e:
            owners[x].add(key)
    shared_entities = {x: sorted(fid for fid, _ in w) for x, w in owners.items()
                       if len(w) > 1 and any(src == "g4" for _, src in w)}
    for x, w in sorted(shared_entities.items()):
        findings.append(f"O3 shared named entity {x!r}: {w}")
    # O3 identifier gate
    if sha256(IDENT_INTENDED.pattern) != IDENT_GATE_PATTERN_SHA256:
        findings.append("O3 identifier gate pattern differs from its pinned digest")
    id_owners = defaultdict(set)
    for f, src in rows:
        found = intended_identifiers(f, content[f["fixture_id"], src])
        for x in found:
            id_owners[x].add((src, f["fixture_id"]))
        if src == "g4":
            undeclared = found - set(ledger[f["fixture_id"]].get("identifiers", []))
            if undeclared:
                findings.append(f"{f['fixture_id']}: identifiers not declared (O3 identifier gate): {sorted(undeclared)}")
    shared_ids = {x: sorted(fid for _, fid in w) for x, w in id_owners.items()
                  if len({fid for _, fid in w}) > 1 and any(src == "g4" for src, _ in w)}
    for x, w in sorted(shared_ids.items()):
        findings.append(f"O3 identifier gate: shared identifier {x!r}: {w}")

    # O6 exact values
    owners6, compared = defaultdict(set), Counter()
    for f, src in rows:
        g = gold[f["fixture_id"]] if src == "g4" else next(gg for ff, gg in prior if ff is f)
        for v, path in o6_values(f, g).items():
            owners6[v].add((src, f["fixture_id"]))
            if src == "g4":
                compared[f["task_class"]] += 1
    o6_collisions = sorted((v, sorted({fid for _, fid in who})) for v, who in owners6.items()
                           if len({fid for _, fid in who}) > 1 and any(s == "g4" for s, _ in who))
    for v, w in o6_collisions:
        findings.append(f"O6 shared value {v!r}: {w}")

    # N1 canonical gold
    canon = defaultdict(list)
    for f, src in rows:
        g = gold[f["fixture_id"]] if src == "g4" else next(gg for ff, gg in prior if ff is f)
        key = canonical_gold(f, g)
        if key is not None:
            canon[key].append((src, f["fixture_id"]))
    n1 = [[fid for _, fid in w] for w in canon.values() if len(w) > 1 and any(s == "g4" for s, _ in w)]
    for w in n1:
        findings.append(f"N1 identical canonical gold: {w}")

    # research lineages and planning action names never repeat across fixtures
    lineage_owners = defaultdict(set)
    for fid in g4:
        if fixtures[fid]["task_class"] == "grounded_research_synthesis":
            for s in fixtures[fid]["input"]["sources"]:
                lineage_owners[s["lineage"]].add(fid)
    repeated_lineages = {x: sorted(w) for x, w in lineage_owners.items() if len(w) > 1}
    if repeated_lineages:
        findings.append(f"research lineages repeat across fixtures: {repeated_lineages}")
    action_owners = defaultdict(set)
    for f, src in rows:
        if f["task_class"] == "reflective_planning":
            for a in f["input"]["allowed_actions"]:
                action_owners[a["action"]].add((src, f["fixture_id"]))
    repeated_actions = {a: sorted(fid for _, fid in w) for a, w in action_owners.items()
                        if len({fid for _, fid in w}) > 1 and any(s == "g4" for s, _ in w)}
    for a, w in sorted(repeated_actions.items()):
        findings.append(f"planning action name {a!r} repeated across fixtures: {w}")

    # gold structure: fine signature A′ vs B′ per cell (research, extraction); canonical research signature per risk
    fine = defaultdict(lambda: {"A": [], "B": []})
    canonical = defaultdict(lambda: {"A": [], "B": []})
    for fid in g4:
        f = fixtures[fid]
        if f["validator_profile"] in ("extraction.v1", "research.v1"):
            fine[(f["task_class"], f["consequence_risk"])][slots[fid]["phase"]].append(
                (fid, structural_signature(f, gold[fid]["expected"])))
        if f["validator_profile"] == "research.v1":
            canonical[slots[fid]["risk"]][slots[fid]["phase"]].append((fid, research_canonical_signature(f, gold[fid]["expected"])))
    fine_clashes = [[a, b] for parts in fine.values() for a, sa in parts["A"] for b, sb in parts["B"] if sa == sb]
    canonical_clashes = [[a, b] for parts in canonical.values() for a, sa in parts["A"] for b, sb in parts["B"] if sa == sb]
    for a, b in fine_clashes:
        findings.append(f"fine signature repeated between A′ and B′ in a cell: {a} vs {b}")
    for a, b in canonical_clashes:
        findings.append(f"canonical research signature repeated between A′ and B′: {a} vs {b}")

    # conversation: exactly 4 options; gold positions balanced within 1 in every cell of each corpus part
    positions = defaultdict(Counter)
    four = 0
    for fid in g4:
        f = fixtures[fid]
        if f["task_class"] == "ordinary_conversation":
            options = f["input"]["answer_options"]
            four += len(options) == 4
            s = slots[fid]
            positions[(s["phase"], s["role"], s["risk"])][options.index(gold[fid]["expected"]["answer"]) + 1] += 1
    unbalanced = sorted("|".join(k) for k, c in positions.items()
                        if max(c.get(p, 0) for p in (1, 2, 3, 4)) - min(c.get(p, 0) for p in (1, 2, 3, 4)) > 1)
    conv_total = sum(1 for fid in g4 if fixtures[fid]["task_class"] == "ordinary_conversation")
    if four != conv_total:
        findings.append("conversation: a fixture does not offer exactly 4 options")
    if unbalanced:
        findings.append(f"conversation gold positions unbalanced: {unbalanced}")

    return {
        "contract_version": CONTRACT_VERSION,
        "valid": not findings, "findings": findings,
        "bounds": {"max_trigram_jaccard": MAX_CROSS_CORPUS_TRIGRAM_JACCARD, "boilerplate_share": BOILERPLATE_SHARE},
        "fixes_applied": pool["fixes_applied"],
        "pool": {"g4_fixtures": len(g4), "prior_fixtures": len(prior)},
        "trigram": trigram, "trigram_task_relevant": trigram_relevant,
        "n8_same_family_a_b_max_jaccard_per_cell": n8,
        "o3_entities": {"g4_fixtures": len(g4), "g4_entities": len({x for f in g4 for x in ents[f, "g4"]}),
                        "g3_entities_compared": len({x for f, _ in prior for x in ents[f["fixture_id"], "prior"]}),
                        "shared": len(shared_entities),
                        "scope": "all authored G-ROUTE4 fixtures of every class, main and reserve, pairwise and "
                                 "against all prior-experiment A and B fixtures"},
        "o3_identifier_gate": {"g4_identifiers": len({x for x, w in id_owners.items() if any(s == "g4" for s, _ in w)}),
                               "g3_identifiers": len({x for x, w in id_owners.items() if any(s == "prior" for s, _ in w)}),
                               "shared": len(shared_ids), "pattern_sha256": IDENT_GATE_PATTERN_SHA256},
        "o6": {"g4_values_compared_by_class": dict(compared), "collisions": len(o6_collisions),
               "pool": "all classes pooled; G-ROUTE4 main and reserve plus all prior-experiment A and B fixtures"},
        "n1_duplicates": len(n1),
        "research_lineage_repeats": len(repeated_lineages), "unique_lineages": len(lineage_owners),
        "planning": {"g4_action_names": sum(1 for w in action_owners.values() if any(s == "g4" for s, _ in w)),
                     "repeated_action_names": len(repeated_actions)},
        "fine_signature_clashes": len(fine_clashes),
        "canonical_signature_clashes": len(canonical_clashes),
        "conversation": {"fixtures_with_four_options": four, "fixtures": conv_total,
                         "gold_positions": {"|".join(k): {str(pos): n for pos, n in sorted(v.items())}
                                            for k, v in sorted(positions.items())},
                         "signature": "none (O4)"},
        "structural_check_scope": ("research and extraction compare the fine gold signature A′ against B′ per cell, and "
                                   "research the canonical signature per risk; planning and synthesis are exempt "
                                   "(declared); conversation has no signature (O4)"),
        "shared_rule_keys_excluded_from_content": list(SHARED_RULE_KEYS),
        "shared_rule_tokens_excluded": sorted(SHARED_RULE_TOKENS),
    }


def main() -> int:
    report = audit()
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8",
                                     newline="\n")
    print(json.dumps({k: report[k] for k in ("valid", "fixes_applied", "n1_duplicates", "fine_signature_clashes",
                                             "canonical_signature_clashes")}, ensure_ascii=False))
    for tc, row in report["trigram"].items():
        print(f"  {tc:34s} max {row['max_jaccard']:.4f} {row['max_pair']} over {row['pairs_over_bound']}")
    for f in report["findings"]:
        print("FINDING", f)
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
