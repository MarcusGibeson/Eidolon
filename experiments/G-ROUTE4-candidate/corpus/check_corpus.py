"""G-ROUTE4 authoring checker (corpus stage; not part of the governed runtime).

Checks authored fixtures against the FROZEN blueprint (experiments/G-ROUTE4-candidate/blueprint, commit 1156d06)
and the accepted design's authoring rules. It never changes a rule: every failure is reported, and a rule that
cannot be met is a conflict to report, not to relax.

It uses G-ROUTE3's own tokenizer, entity detector and content function (read-only), and the frozen G-ROUTE1 and
G-ROUTE3 validators, so the checks are the ones the design names. The pool is fixed per the design: all authored
G-ROUTE4 fixtures (main and reserve) plus G-ROUTE3's A and B fixtures.

Pre-seal repair gates (in addition to the frozen ones): every free-text sentence of Conversation, Research and
Synthesis is bound to the authoring ledger, one sentence per unit within a padding cap, and overlap is also measured
on that task-relevant text; gold replies fit the output cap with headroom (pinned tokenizer, never downloaded);
Synthesis required terms are substantive and not satisfiable from scaffolding; Research sources are the authored
paraphrases (never the claim or its literal negation), P8 sources state no threshold or comparison, the
single_lineage_support code has one truth under both lineage readings, and decision rules are compared by their
normalized clause kind; invented names come from the committed stream, replayed with no dictionary.

    python -B check_corpus.py staging/extraction.json [...]   # writes staging/CHECK_REPORT.json; exit 1 on failure
"""

import base64
import collections
import copy
import datetime
import hashlib
import json
import os
import re
import statistics
import sys
import tempfile
from decimal import Decimal
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
import name_stream as NS  # noqa: E402
import research_topics as RT  # noqa: E402

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


RESEARCH_DECISION_KIND = {"P1": "focal_two_lineages", "P4": "focal_two_lineages", "P7": "temporal_all_supported"}
RESEARCH_SOURCE_KEYS = {"source_id", "claim_id", "relation", "lineage", "text"}
RESEARCH_SOURCE_OPTIONAL = {"when", "date", "q", "value", "alternate_subject", "reissue"}
# P8 sources report a value only: none of these words may appear (they would state the comparison for the model)
COMPARISON_WORDS = {"below", "under", "less", "fewer", "short", "than", "threshold", "least", "exceed", "exceeds",
                    "exceeded", "falls", "fall", "required", "requirement", "claim", "claimed", "insufficient",
                    "enough", "not", "only", "above", "over", "more", "target"}
NEGATION_WORDS = {"not", "no", "never", "does", "do", "did", "doesn't", "don't", "didn't", "isn't", "aren't", "cannot",
                  "can't", "won't", "is", "are", "was", "were"}
# per-sentence padding caps on task units (G-ROUTE3's longest comparable unit in brackets): conversation request
# 34 words and option 21 [G-ROUTE3 message 75 words]; research claim 12 [12] and source 19 [19]; synthesis
# observation 18 [17]. The caps leave headroom and stop filler from being folded into a bound sentence.
UNIT_WORD_CAP = {"conversation_request": 40, "conversation_option": 28, "research_claim": 16, "research_source": 26,
                 "synthesis_observation": 22}
# required_terms must be substantive observation content, never task scaffolding
SCAFFOLD_WORDS = {"observation", "observations", "filed", "file", "record", "records", "note", "notes", "statement",
                  "statements", "finding", "role", "evidence", "logged", "entry", "report", "reported"}


def words(text):
    return re.findall(r"[a-z0-9']+", text.casefold())


def sentence_count(text):
    """Sentences in a unit: terminal punctuation followed by a space and a capital, plus the final one."""
    body = text.strip()
    return len(re.findall(r"[.!?](?=\s+[A-Z])", body)) + (1 if body else 0)


def _stem(word):
    return word[:-1] if len(word) > 3 and word.endswith("s") and not word.endswith("ss") else word


def literal_variant(source_body, claim_text):
    """True when a source is the claim sentence itself, or the claim with negation words inserted or removed."""
    a = [_stem(w) for w in words(source_body) if w not in NEGATION_WORDS]
    b = [_stem(w) for w in words(claim_text) if w not in NEGATION_WORDS]
    return a == b


def classify_decision(text, positive, negative):
    """Normalize a research decision rule to its canonical clause kind, or None when it is not exactly one kind.
    Rewording (synonyms, clause order, quoting) cannot change the kind, so it cannot hide a repeated structure."""
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


def sls_supporting_reading(sources, expected):
    """single_lineage_support when only the lineages of SUPPORTING sources are counted (the other reading of the
    code's condition). A fixture is ambiguous if this differs from the cited-lineage reading used by the gold."""
    for row in expected["claims"]:
        if row["status"] != "supported":
            continue
        supporting = {s["lineage"] for s in sources if s["claim_id"] == row["claim_id"] and s["relation"] == "support"}
        if len(supporting) == 1:
            return True
    return False


# The decision enters the canonical signature only as what it decides on: C1's lineage count, or every claim's
# status. The temporal clause only settles C1's status, which the statuses already record, so a temporal rule and
# a plain all-supported rule are the same decision class (this is stricter than comparing clause kinds).
DECISION_CLASS = {"focal_two_lineages": "focal_c1_two_lineages", "all_supported": "every_claim_supported",
                  "temporal_all_supported": "every_claim_supported"}


def research_canonical_signature(expected, n_sources, kind, recommendations):
    return ["research", sorted([c["status"], len(c["citations"]), len(c["lineages"])] for c in expected["claims"]),
            recommendations.index(expected["recommendation"]), list(expected["uncertainties"]), n_sources,
            DECISION_CLASS.get(kind)]


def research_topic(risk, claim):
    """The authored topic row whose claim renders to this claim's text (research_topics.py is the semantic ledger
    of which paraphrase states which relation)."""
    if claim.get("kind") == "scope":
        pool = RT.SCOPE[risk]
        render = lambda row: row[0].replace("{S}", claim["subject"])  # noqa: E731
    elif claim.get("kind") == "quantity":
        pool = RT.QUANTITY[risk]
        render = lambda row: row[0].replace("{S}", claim["subject"]).replace("{T}", str(claim.get("threshold")))  # noqa: E731
    else:
        pool = RT.STANDARD[risk]
        render = lambda row: row[0].replace("{S}", claim["subject"])  # noqa: E731
    rows = [row for row in pool if render(row) == claim.get("text")]
    return rows[0] if len(rows) == 1 else None


def research_allowed_bodies(topic, claim, source):
    relation, subject = source["relation"], claim["subject"]
    if topic is None:
        return set()
    if claim.get("kind") == "scope":
        return {topic[1].replace("{S}", subject)} if relation == "narrow" else set()
    if claim.get("kind") == "quantity":
        if relation != "quantity_deny" or source.get("q") not in (0, 1):
            return set()
        return {topic[1 + source["q"]].replace("{S}", subject).replace("{V}", str(source.get("value")))}
    if relation == "support":
        return {topic[1].replace("{S}", subject), topic[2].replace("{S}", subject)}
    if relation == "deny":
        return {topic[3].replace("{S}", subject), topic[4].replace("{S}", subject)}
    if relation == "other_subject":
        other = str(source.get("alternate_subject"))
        return {topic[1].replace("{S}", other), topic[2].replace("{S}", other)}
    return set()


def split_source_prefix(text):
    """(prefix kind, date, body): a dated-notice prefix, a reissue prefix, or none."""
    for pattern in RT.DATE_PREFIXES:
        head = pattern.split("{D}")
        m = re.match(re.escape(head[0]) + r"(\d{4}-\d{2}-\d{2})" + re.escape(head[1]), text)
        if m:
            return "date", m.group(1), text[m.end():]
    for prefix in RT.REISSUE_PREFIXES:
        if text.startswith(prefix):
            return "reissue", None, text[len(prefix):]
    return None, None, text


# ---------------------------------------------------------------- Conversation: facts re-derived independently
CONV_UNIT = {"volume": {"ml": 1, "cl": 10, "l": 1000}, "mass": {"g": 1, "kg": 1000, "t": 1000000},
             "length": {"mm": 1, "cm": 10, "m": 1000}}
CONVERSATION_ATTRS = {                       # (request attributes, per-option attributes) per family and depth
    ("CV1", 1): ({"A", "B"}, {"a", "b"}), ("CV1", 2): ({"A", "B"}, {"a1", "a2", "b1", "b2"}),
    ("CV2", 1): ({"E", "T"}, {"dep", "dur"}), ("CV2", 2): ({"X", "Y"}, {"dep", "leg1", "leg2"}),
    ("CV3", 1): ({"need", "max"}, {"vol", "wt"}), ("CV3", 2): ({"need", "net"}, {"count", "size", "waste"}),
    ("CV4", 1): ({"thr", "K", "L"}, {"items"}), ("CV4", 2): ({"thr", "K", "S"}, {"items"}),
    ("CV5", 1): ({"P", "N"}, {"ratio"}), ("CV5", 2): ({"B1", "tax", "B2"}, {"price", "disc"}),
    ("CV6", 1): ({"G", "Ex", "today"}, {"g", "last"}), ("CV6", 2): ({"G", "Ex", "today"}, {"g1", "g2", "last"}),
}
# realism: CV2 facts are clock times or dates, CV3 facts are measured quantities with a unit conversion,
# CV6 facts are calendar dates; nothing anywhere is a pre-evaluated flag
CONVERSATION_FORMS = {"CV2": {"E": "td", "T": "td", "X": "td", "Y": "td", "dep": "td"},
                      "CV3": {"need": "m", "max": "m", "vol": "m", "wt": "m", "size": "m", "waste": "m"},
                      "CV6": {"today": "d", "last": "d"}}


def _fnum(v):
    d = Decimal(str(v)).normalize()
    return format(d, "f") if d != d.to_integral_value() else str(int(d))


def conversation_surface(value, fmt):
    kind = fmt[0]
    if isinstance(value, bool):
        raise TypeError("a fact may not be a pre-evaluated flag")
    if kind == "n":
        return f"{_fnum(value)}{fmt[1]}"
    if kind == "t":
        return f"{value // 60:02d}:{value % 60:02d}"
    if kind == "d":
        return datetime.date.fromordinal(value).isoformat()
    if kind == "m":
        return f"{_fnum(Decimal(value) / CONV_UNIT[fmt[1]][fmt[2]])} {fmt[2]}"
    if kind == "l":
        items = [_fnum(v) for v in value]
        return (", ".join(items[:-1]) + " and " + items[-1]) + fmt[1]
    if kind == "r":
        return f"{value[0]} of {value[1]}{fmt[1]}"
    raise ValueError(kind)


def conversation_conditions(family, depth, c, o):
    """Independently recompute the two authoring conditions for one option from the stated facts."""
    if family == "CV1":
        if depth == 1:
            return o["a"] >= c["A"], o["b"] <= c["B"]
        return o["a1"] * o["a2"] >= c["A"], o["b1"] + o["b2"] <= c["B"]
    if family == "CV2":
        if depth == 1:
            return o["dep"] >= c["E"], o["dep"] + o["dur"] <= c["T"]
        return o["dep"] + o["leg1"] <= c["X"], o["dep"] + o["leg1"] + o["leg2"] <= c["Y"]
    if family == "CV3":
        if depth == 1:
            return o["vol"] >= c["need"], o["wt"] <= c["max"]
        total = o["count"] * o["size"]
        return total >= c["need"], total - o["waste"] >= c["net"]
    if family == "CV4":
        high = [v for v in o["items"] if v >= c["thr"]]
        if depth == 1:
            return len(high) >= c["K"], len(o["items"]) - len(high) <= c["L"]
        return len(high) >= c["K"], sum(high) >= c["S"]
    if family == "CV5":
        if depth == 1:
            x, y = o["ratio"]
            return 100 * x >= c["P"] * y, y >= c["N"]
        sale = Decimal(o["price"]) * (100 - o["disc"]) / 100
        return sale <= c["B1"], sale * (100 + c["tax"]) / 100 <= c["B2"]
    if family == "CV6":
        gap = c["today"] - o["last"]
        if depth == 1:
            return o["g"] >= c["G"], gap >= c["Ex"]
        return o["g1"] + o["g2"] >= c["G"], gap >= c["Ex"]
    raise ValueError(family)


# ---------------------------------------------------------------- reply length (G-ROUTE1 model binding num_predict)
REPLY_CAP_TOKENS = 350                 # experiments/G-ROUTE1-candidate/model_bindings.json num_predict
REPLY_TOKEN_BOUND = 250                # >= 100 tokens (29%) of headroom under the cap
CL100K_URL = "https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken"
CL100K_SHA256 = "223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7"


def pinned_tokenizer():
    """cl100k_base, loaded ONLY from the local tiktoken cache and only if its sha256 is the pinned digest; never
    downloaded. Returns (encode, description) or (None, reason). Without it the gate falls back to UTF-8 bytes,
    a strict upper bound on any byte-level BPE token count, so the fallback can only fail more, never less."""
    try:
        import tiktoken
        from tiktoken_ext.openai_public import ENDOFTEXT, FIM_PREFIX, FIM_MIDDLE, FIM_SUFFIX, ENDOFPROMPT
    except ImportError as exc:
        return None, f"tiktoken unavailable ({exc})"
    cache = Path(os.environ.get("TIKTOKEN_CACHE_DIR") or Path(tempfile.gettempdir()) / "data-gym-cache")
    path = cache / hashlib.sha1(CL100K_URL.encode()).hexdigest()
    if not path.is_file():
        return None, "pinned cl100k_base file not in the local cache (never downloaded)"
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != CL100K_SHA256:
        return None, "local cl100k_base file digest differs from the pinned digest"
    ranks = {base64.b64decode(token): int(rank) for token, rank in (line.split() for line in data.splitlines() if line)}
    pat = r"""'(?i:[sdmt]|ll|ve|re)|[^\r\n\p{L}\p{N}]?+\p{L}++|\p{N}{1,3}+| ?[^\s\p{L}\p{N}]++[\r\n]*+|\s++$|\s*[\r\n]|\s+(?!\S)|\s"""
    enc = tiktoken.Encoding(name="cl100k_base_pinned", pat_str=pat, mergeable_ranks=ranks,
                            special_tokens={ENDOFTEXT: 100257, FIM_PREFIX: 100258, FIM_MIDDLE: 100259,
                                            FIM_SUFFIX: 100260, ENDOFPROMPT: 100276})
    return (lambda text: len(enc.encode(text, disallowed_special=()))), f"cl100k_base sha256 {CL100K_SHA256}"


def reply_text(reference, pretty=False):
    if isinstance(reference, str):
        return reference
    if pretty:
        return "```json\n" + json.dumps(reference, ensure_ascii=False, indent=2) + "\n```"
    return json.dumps(reference, ensure_ascii=False)


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
IDENT_GATE_PATTERN_SHA256 = "a3773a982c16579d94cede99539e0b9cacca1347f96774759a84bbb7788adaae"
FROZEN_G3_INDEPENDENCE_SHA256 = "177aa18abc21057d94b1b34c94f7a05960248f0dd29a6d98763660c445b4509b"
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


def task_relevant_fixture(fixture, units):
    """The fixture with every free-text sentence that is not bound to the authoring ledger removed."""
    if units is None:
        return fixture
    out, keep = copy.deepcopy(fixture), set(units)
    inp = out["input"]
    if fixture["task_class"] == "ordinary_conversation":
        inp["message"] = " ".join(units)
    elif fixture["task_class"] == "hierarchical_semantic_synthesis":
        inp["observations"] = [o for o in inp.get("observations", []) if o.get("text") in keep]
    elif fixture["task_class"] == "grounded_research_synthesis":
        inp["claims"] = [c for c in inp.get("claims", []) if c.get("text") in keep]
        inp["sources"] = [s for s in inp.get("sources", []) if s.get("text") in keep]
    return out


def jaccard_pass(pool, content, classes, problems, label, o5=True):
    pin = set()
    for text in PINNED:
        pin |= I._trigrams(text)
    by_class = collections.defaultdict(list)
    for f, g, src in pool:
        by_class[f["task_class"]].append((f["fixture_id"], src, I._trigrams(content[id(f)]) - pin))
    out = {}
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
                    problems.append(f"{label} {jac:.3f} > 0.20: {a[0]} vs {b[0]}")
        single = []
        if o5:
            # O5: no boilerplate trigram specific to a single family
            fam_of = {fid: SLOTS[fid]["family"] for fid, src, _ in rows if src == "G4"}
            for tg in boiler:
                fams = {fam_of[fid] for fid, src, s in rows if src == "G4" and tg in s}
                if len(fams) == 1:
                    single.append((" ".join(tg), fams.pop()))
            for tg, fam in single:
                problems.append(f"O5: boilerplate trigram '{tg}' is specific to family {fam}")
        out[tc] = {"pool": len(rows), "boilerplate_trigrams": len(boiler), "max_jaccard": round(best[0], 4),
                   "max_pair": best[1:], "pairs_over_bound": over}
        if o5:
            out[tc]["o5_single_family_boilerplate"] = len(single)
    return out


def check(staged, english=None):
    """english: an optional extra English word set to screen names against (the committed stream is always used)."""
    problems, report = [], collections.OrderedDict()
    fixtures = [f for s in staged for f in s["fixtures"]]
    gold_by = {g["fixture_id"]: g for s in staged for g in s["gold"]}
    design_by = {d["fixture_id"]: d for s in staged for d in s["design"]}
    design_order = {s["task_class"]: s["design"] for s in staged if "task_class" in s}
    task_units = {}                        # fixture id -> its ledger-bound free-text sentences
    research_signatures = collections.defaultdict(list)
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
            family, pattern, sls, risk = slot["family"], slot["features"]["pattern"], slot["features"]["sls"], slot["risk"]
            contract = d.get("research_contract") if isinstance(d.get("research_contract"), dict) else {}
            claims = contract.get("claims") if isinstance(contract.get("claims"), list) else []
            sources = contract.get("sources") if isinstance(contract.get("sources"), list) else []
            decision = contract.get("decision") if isinstance(contract.get("decision"), dict) else {}
            names = d.get("invented_names") or []
            if set(inp) != {"allowed_recommendations", "allowed_uncertainty_codes", "claims",
                            "decision_rule", "sources"}:
                problems.append(f"{fid}: research input keys differ from the frozen construct")
                continue
            claim_count, source_count = RESEARCH_FAMILY[family]
            if len(inp.get("claims", [])) != claim_count or len(claims) != claim_count:
                problems.append(f"{fid}: research claim count differs from family {family}")
            if len(inp.get("sources", [])) != source_count or len(sources) != source_count:
                problems.append(f"{fid}: research source count differs from family {family}")
            if any(not isinstance(row, dict) or set(row) != {"claim_id", "text"} for row in inp.get("claims", [])) \
                    or [row.get("claim_id") for row in inp.get("claims", [])] != \
                    [f"C{i}" for i in range(1, claim_count + 1)]:
                problems.append(f"{fid}: research claim identities or keys are invalid")
            if any(not isinstance(row, dict) or set(row) != {"source_id", "lineage", "text"}
                   for row in inp.get("sources", [])) or [row.get("source_id") for row in inp.get("sources", [])] != \
                    [f"S{i}" for i in range(1, source_count + 1)]:
                problems.append(f"{fid}: research source identities or keys are invalid")
            if inp.get("allowed_uncertainty_codes") != RESEARCH_UNCERTAINTIES:
                problems.append(f"{fid}: research uncertainty code contract differs from the frozen rules")
            # the opening follows the frozen constraint "Assess the claims about <subject>"
            if len(names) != 2 or opening != f"Assess the claims about {names[0]} and {names[1]}":
                problems.append(f"{fid}: research opening or invented-name binding is invalid (frozen constraint "
                                "'Assess the claims about <subject>')")
            # recommendations: a fixture-specific snake_case pair, bound to the decision ledger
            recommendations = inp.get("allowed_recommendations")
            if not (isinstance(recommendations, list) and len(recommendations) == 2 and
                    len(set(recommendations)) == 2 and
                    all(isinstance(x, str) and re.fullmatch(r"[a-z]+(_[a-z]+)*", x) for x in recommendations)) or \
                    [decision.get("positive"), decision.get("negative")] != recommendations:
                problems.append(f"{fid}: research recommendation pair is invalid or differs from the decision ledger")
                recommendations = ["?", "??"]
            # claims: the ledger renders the input exactly, and every claim names its subject
            if [c.get("claim_id") if isinstance(c, dict) else None for c in claims] != \
                    [f"C{i}" for i in range(1, claim_count + 1)]:
                problems.append(f"{fid}: research claim ledger binding is invalid")
            if [{"claim_id": c.get("claim_id"), "text": c.get("text")} for c in claims if isinstance(c, dict)] != \
                    inp.get("claims"):
                problems.append(f"{fid}: research claim text differs from its semantic ledger")
            topics = {}
            for c in claims:
                if not isinstance(c, dict) or c.get("subject") not in names or \
                        str(c.get("subject")) not in str(c.get("text")):
                    problems.append(f"{fid}: research claim {c.get('claim_id') if isinstance(c, dict) else c} does "
                                    "not name one of the fixture's subjects")
                    continue
                if len(words(c["text"])) > UNIT_WORD_CAP["research_claim"] or sentence_count(c["text"]) != 1:
                    problems.append(f"{fid}: research claim {c['claim_id']} is not one sentence within the cap")
                topics[c["claim_id"]] = research_topic(risk, c)
                if topics[c["claim_id"]] is None:
                    problems.append(f"{fid}: research claim {c['claim_id']} is not an authored topic claim")
            if (claims[:1] and claims[0].get("kind")) != {"P6": "scope", "P8": "quantity"}.get(pattern, "standard") or \
                    any(c.get("kind") != "standard" for c in claims[1:] if isinstance(c, dict)):
                problems.append(f"{fid}: research claim kinds do not realize pattern {pattern}")
            # sources: ledger renders the input; text is the authored paraphrase for its relation
            malformed = [s for s in sources if not isinstance(s, dict) or not RESEARCH_SOURCE_KEYS <= set(s) or
                         not set(s) <= RESEARCH_SOURCE_KEYS | RESEARCH_SOURCE_OPTIONAL]
            if malformed or [s.get("source_id") for s in sources] != [f"S{i}" for i in range(1, source_count + 1)]:
                problems.append(f"{fid}: research source ledger identities or keys are invalid")
                continue
            if any(s.get("relation") not in RESEARCH_RELATIONS or s.get("claim_id") not in topics for s in sources):
                problems.append(f"{fid}: research source ledger has an unknown binding or relation")
                continue
            if [{"source_id": s["source_id"], "lineage": s["lineage"], "text": s["text"]} for s in sources] != \
                    inp.get("sources"):
                problems.append(f"{fid}: research source text or lineage differs from its semantic ledger")
            seen_lineages = set()
            for s in sources:
                sid, claim = s["source_id"], claims[int(s["claim_id"][1:]) - 1]
                kind_, date, body = split_source_prefix(s["text"])
                if len(words(s["text"])) > UNIT_WORD_CAP["research_source"] or sentence_count(body) != 1:
                    problems.append(f"{fid}: research source {sid} is not one sentence within the cap (filler)")
                if body not in research_allowed_bodies(topics.get(s["claim_id"]), claim, s):
                    problems.append(f"{fid}: research source {sid} text is not the authored paraphrase for its "
                                    f"relation {s['relation']}")
                for c in claims:
                    if s["text"] == c.get("text") or literal_variant(body, str(c.get("text"))):
                        problems.append(f"{fid}: research source {sid} is the claim sentence or its literal negation")
                if s["relation"] == "other_subject":
                    other = s.get("alternate_subject")
                    if other not in names or other == claim["subject"] or other not in body or claim["subject"] in body:
                        problems.append(f"{fid}: research other-subject source {sid} does not name the alternate "
                                        "subject alone")
                elif claim["subject"] not in body:
                    problems.append(f"{fid}: research source {sid} does not name its claim's subject")
                if s["relation"] == "quantity_deny":
                    threshold, value = claim.get("threshold"), s.get("value")
                    if not isinstance(threshold, int) or not isinstance(value, int) or value >= threshold or \
                            str(value) not in re.findall(r"\d+", body) or str(threshold) in re.findall(r"\d+", body) \
                            or set(words(body)) & COMPARISON_WORDS:
                        problems.append(f"{fid}: research quantitative contradiction does not fall below the threshold, "
                                        f"or source {sid} states the threshold or a comparison")
                if pattern == "P7" and s["claim_id"] == "C1":
                    if kind_ != "date" or date != s.get("date") or s.get("when") not in ("older", "newer"):
                        problems.append(f"{fid}: research temporal source {sid} is not a dated notice")
                elif kind_ == "date" or "date" in s or "when" in s:
                    problems.append(f"{fid}: dated research source {sid} appears outside P7's focal pair")
                if (kind_ == "reissue") != bool(s.get("reissue")) or \
                        bool(s.get("reissue")) != (s["lineage"] in seen_lineages and kind_ != "date"):
                    problems.append(f"{fid}: research source {sid} reissue marking differs from its lineage history")
                lineage = s["lineage"]
                if RT.lineage_has_repeated_word(lineage):
                    problems.append(f"{fid}: research lineage {lineage!r} repeats an issuer or channel word")
                if not any(lineage in RT.lineage_options(category) for category in RT.LINEAGE_COMPATIBILITY):
                    problems.append(f"{fid}: research lineage {lineage!r} is not an allowed publisher/channel name")
                elif topics.get(s["claim_id"]) is not None and not RT.lineage_matches_topic(
                        lineage, slot["risk"], claim["kind"], topics[s["claim_id"]]):
                    problems.append(f"{fid}: research lineage {lineage!r} does not match its source topic")
                seen_lineages.add(s["lineage"])
            wording = collections.defaultdict(set)
            for s in sources:
                wording[(s["claim_id"], s["relation"], split_source_prefix(s["text"])[2])].add(s["lineage"])
            if any(len(lineages) > 1 for lineages in wording.values()):
                problems.append(f"{fid}: research sources from different lineages share identical wording "
                                "(independent publishers do not copy each other)")
            focal = [row for row in sources if row["claim_id"] == "C1"]
            relations = [row["relation"] for row in focal]
            if pattern == "P1":
                pattern_ok = relations == ["support", "support"] and len({row["lineage"] for row in focal}) == 2
            elif pattern == "P2":
                pattern_ok = relations == ["deny"]
            elif pattern == "P3":
                pattern_ok = relations == ["other_subject"]
            elif pattern == "P4":
                pattern_ok = relations[:2] == ["support", "support"] and len(focal) == (2 if sls else 3) and \
                    focal[0]["lineage"] == focal[1]["lineage"] and \
                    (sls or focal[2]["lineage"] != focal[0]["lineage"])
            elif pattern == "P5":
                pattern_ok = relations == ["support", "deny"]
            elif pattern == "P6":
                pattern_ok = relations == ["narrow"]
            elif pattern == "P7":
                dates = [row.get("date") for row in focal]
                pattern_ok = set(relations) == {"support", "deny"} and len(focal) == 2
                if not (all(isinstance(x, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", x) for x in dates) and
                        dates == sorted(dates) and len(set(dates)) == 2 and
                        [row.get("when") for row in focal] == ["older", "newer"]):
                    problems.append(f"{fid}: research temporal-governance relation is invalid")
            elif pattern == "P8":
                pattern_ok = relations == ["quantity_deny", "quantity_deny"] and \
                    len({row["lineage"] for row in focal}) == 2
            else:
                pattern_ok = False
            if not pattern_ok:
                problems.append(f"{fid}: research focal evidence does not realize pattern {pattern}")
            if pattern == "P6" and (not claims or claims[0].get("kind") != "scope"):
                problems.append(f"{fid}: research narrower-scope binding is invalid")
            if pattern != "P6" and any(row["relation"] == "narrow" for row in sources):
                problems.append(f"{fid}: narrower-scope source appears outside P6")
            if pattern == "P7":
                research_stats["temporal"]["governing_pairs"] += 1
            if pattern == "P6":
                research_stats["scope"]["narrower_scope_cases"] += 1
            # gold, rationale ledger, both readings of single_lineage_support, and the decision clause kind
            try:
                recomputed, derived_reasons = research_gold(pattern, claims, sources, recommendations)
            except (KeyError, TypeError, ValueError, IndexError) as exc:
                problems.append(f"{fid}: research gold cannot be recomputed: {exc}")
                continue
            if expected != recomputed:
                problems.append(f"{fid}: research gold differs from the statuses and evidence recomputed from input")
            if g.get("reference_output") != expected:
                problems.append(f"{fid}: research reference_output differs from expected")
            if contract.get("derived_reasons") != derived_reasons:
                problems.append(f"{fid}: research rationale ledger differs from recomputed reasons")
            cited_sls = "single_lineage_support" in recomputed["uncertainties"]
            if cited_sls is not sls:
                problems.append(f"{fid}: research single_lineage_support outcome differs from the frozen feature")
            if sls_supporting_reading(sources, recomputed) is not cited_sls:
                problems.append(f"{fid}: single_lineage_support is ambiguous: counting supporting lineages gives a "
                                "different answer from counting cited lineages")
            kind = classify_decision(inp.get("decision_rule", ""), *recommendations)
            if kind is None or kind != RESEARCH_DECISION_KIND.get(pattern, "all_supported") or \
                    decision.get("kind") != kind:
                problems.append(f"{fid}: research decision rule does not express the pattern's frozen decision "
                                f"(normalized clause kind: {kind})")
            signature = research_canonical_signature(recomputed, source_count, kind, recommendations)
            if contract.get("canonical_signature") != signature:
                problems.append(f"{fid}: declared canonical signature differs from the recomputed one")
            research_signatures[(risk, slot["phase"])].append((fid, json.dumps(signature)))
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
            task_units[fid] = [c["text"] for c in claims] + [s["text"] for s in sources]
        elif tc == "ordinary_conversation":
            inp, expected = f["input"], g["expected"]
            family, depth = slot["family"], slot["features"]["depth"]
            if set(inp) != {"answer_options", "message"}:
                problems.append(f"{fid}: conversation input keys are not exactly answer_options and message")
                continue
            options = inp.get("answer_options")
            if not isinstance(options, list) or len(options) != 4:
                problems.append(f"{fid}: conversation must have exactly 4 answer options")
                continue
            canonical = [canonical_value(v) for v in options]
            if len(canonical) != len(set(canonical)):
                problems.append(f"{fid}: conversation options are not pairwise distinct under canonical_value")
            if set(expected) != {"answer", "max_characters"} or expected.get("max_characters") != 600:
                problems.append(f"{fid}: conversation gold keys or max_characters differ from the frozen contract")
            position = slot["features"]["gold_position"] - 1
            if expected.get("answer") != options[position]:
                problems.append(f"{fid}: conversation gold answer is not at the frozen position")
            if options != d.get("invented_names"):
                problems.append(f"{fid}: conversation options differ from the declared global name draws")
            units = d.get("message_units")
            if not isinstance(units, list) or len(units) != 5 or \
                    [u.get("option") if isinstance(u, dict) else "?" for u in units] != [None] + options:
                problems.append(f"{fid}: conversation ledger is not one request unit and one unit per option")
                continue
            if inp["message"] != " ".join(str(u.get("text")) for u in units):
                problems.append(f"{fid}: conversation message is not exactly its ledger units (unbound text)")
            request_attrs, option_attrs = CONVERSATION_ATTRS[(family, depth)]
            forms = CONVERSATION_FORMS.get(family, {})
            values, bad_unit = [], False
            for u in units:
                facts = u.get("facts")
                text = str(u.get("text"))
                label = "request" if u["option"] is None else f"option {u['option']}"
                if not isinstance(facts, list) or not facts:
                    problems.append(f"{fid}: conversation {label} sentence carries no fact the answer depends on")
                    bad_unit = True
                    continue
                if sentence_count(text) != 1 or len(words(text)) > UNIT_WORD_CAP[
                        "conversation_request" if u["option"] is None else "conversation_option"]:
                    problems.append(f"{fid}: conversation {label} is not one sentence within the cap (filler)")
                if u["option"] is not None and u["option"] not in text:
                    problems.append(f"{fid}: conversation {label} sentence does not name its option")
                row = {}
                for fact in facts:
                    try:
                        rendered = conversation_surface(fact["value"], fact["fmt"])
                    except (KeyError, TypeError, ValueError, IndexError, OverflowError) as exc:
                        problems.append(f"{fid}: conversation {label} fact cannot be rendered: {exc}")
                        bad_unit = True
                        continue
                    if rendered != fact.get("surface") or rendered not in text:
                        problems.append(f"{fid}: conversation {label} fact {fact.get('attr')} is not stated as "
                                        f"{rendered!r} in its sentence")
                        bad_unit = True
                    want_form = forms.get(fact.get("attr"))
                    if want_form and fact["fmt"][0] not in want_form:
                        problems.append(f"{fid}: conversation {label} fact {fact.get('attr')} is not a real "
                                        f"{'clock/date' if 'd' in want_form else 'unit'} expression")
                    row[fact.get("attr")] = fact["value"]
                if set(row) != (request_attrs if u["option"] is None else option_attrs):
                    problems.append(f"{fid}: conversation {label} facts differ from the family/depth construct")
                    bad_unit = True
                values.append(row)
            if family == "CV3":
                dims = collections.defaultdict(set)
                for u in units:
                    for fact in u.get("facts") or []:
                        if fact.get("fmt", [None])[0] == "m":
                            dims[fact["fmt"][1]].add(fact["fmt"][2])
                            if fact["fmt"][2] in {"g", "ml"} and fact["value"] >= 5000:
                                problems.append(f"{fid}: CV3 uses an implausibly large value in a tiny unit "
                                                f"({fact['surface']}); express a natural-scale scenario")
                if not any(len(v) > 1 for v in dims.values()):
                    problems.append(f"{fid}: CV3 states every quantity in one unit (no conversion)")
            results = []
            if not bad_unit:
                try:
                    results = [conversation_conditions(family, depth, values[0], o) for o in values[1:]]
                except (KeyError, TypeError, ValueError, ZeroDivisionError, ArithmeticError) as exc:
                    problems.append(f"{fid}: conversation conditions cannot be recomputed: {exc}")
            if len(results) == 4:
                gold_positions = [i for i, pair in enumerate(results) if pair == (True, True)]
                near_positions = [i for i, pair in enumerate(results) if pair == (True, False)]
                far_positions = [i for i, pair in enumerate(results) if pair == (False, False)]
                if gold_positions != [position]:
                    problems.append(f"{fid}: conversation recomputed gold positions {gold_positions} differ from "
                                    f"the frozen position {position}")
                if len(near_positions) != 1 or len(far_positions) != 2:
                    problems.append(f"{fid}: conversation needs exactly one first-condition-only near miss and "
                                    "two zero-condition distractors")
                near_option = options[near_positions[0]] if len(near_positions) == 1 else None
                if d.get("near_miss_option") != near_option:
                    problems.append(f"{fid}: declared near-miss option differs from the recomputed near miss")
            if not isinstance(g.get("reference_output"), str):
                problems.append(f"{fid}: conversation reference output is not text")
            elif not g["reference_output"].startswith(f"Answer: {expected.get('answer')}\nActions taken: none\n"):
                problems.append(f"{fid}: conversation reference does not use the exact disclosed frame")
            conversation_stats["families"][family] += 1
            conversation_stats["depth"][str(depth)] += 1
            conversation_stats["near_miss"]["compliant"] += int(len(results) == 4 and
                                                                 results.count((True, False)) == 1 and
                                                                 results.count((False, False)) == 2 and
                                                                 results.count((True, True)) == 1)
            task_units[fid] = [str(u.get("text")) for u in units if u.get("facts")]
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
            scaffold = " ".join([f["title"], f["prompt"], str(inp.get("conclusion_rule", "")),
                                 " ".join(map(str, inp.get("allowed_conclusions", [])))] +
                                [f"{r.replace('_', ' ')} {r} {o}" for o, r in roles.items()]).casefold()
            for oid in ids:
                text = texts.get(oid, "")
                if sentence_count(text) != 1 or len(words(text)) > UNIT_WORD_CAP["synthesis_observation"]:
                    problems.append(f"{fid}: synthesis observation {oid} is not one sentence within the cap (filler)")
                terms = [str(x) for x in (expected.get("required_terms", {}).get(oid) or [])]
                others = " ".join(v for k, v in texts.items() if k != oid).casefold()
                weak = [x for x in terms if not (any(w not in SCAFFOLD_WORDS for w in re.findall(r"[a-z]{3,}", x.casefold()))
                                                 or len(re.sub(r"\D", "", x)) >= 2)]
                copied = [x for x in terms if x.casefold() in scaffold]
                if weak or copied:
                    problems.append(f"{fid}: synthesis required terms for {oid} are not substantive observation "
                                    f"content (weak {weak}, satisfiable from scaffolding {copied})")
                if terms and all(x.casefold() in others for x in terms):
                    problems.append(f"{fid}: synthesis required terms for {oid} all occur in other observations")
            if d.get("invented_names"):
                problems.append(f"{fid}: synthesis declares invented names; its stream draws are unused_stream_draws")
            task_units[fid] = [texts[o] for o in ids if expected.get("required_terms", {}).get(o)]
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
        "ledger": "message = request unit + one unit per option; every unit carries recomputed facts",
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
            try:
                s = I.structural_signature(f, gold_by[f["fixture_id"]]["expected"])
            except (KeyError, TypeError, ValueError, IndexError, AttributeError) as exc:
                problems.append(f"{f['fixture_id']}: fine signature cannot be computed from its gold ({exc})")
                continue
            by_cell[(f["task_class"], f["consequence_risk"])][SLOTS[f["fixture_id"]]["phase"]].append(
                (f["fixture_id"], s))
    clashes = [(a, b) for parts in by_cell.values() for a, sa in parts["A"] for b, sb in parts["B"] if sa == sb]
    for a, b in clashes:
        problems.append(f"fine signature repeated between A′ and B′ in a cell: {a} vs {b}")
    report["fine_signature_clashes"] = len(clashes)

    # ---- reply length: every gold reply fits the model's output cap with comfortable headroom
    encode, tokenizer = pinned_tokenizer()
    measure = encode or (lambda text: len(text.encode("utf-8")))
    lengths, pretty_lengths = collections.defaultdict(list), collections.defaultdict(list)
    for f in fixtures:
        reference = gold_by[f["fixture_id"]]["reference_output"]
        n = measure(reply_text(reference))
        lengths[f["task_class"]].append(n)
        pretty_lengths[f["task_class"]].append(measure(reply_text(reference, pretty=True)))
        if n > REPLY_TOKEN_BOUND:
            problems.append(f"{f['fixture_id']}: gold reply is {n} {'tokens' if encode else 'bytes'}, over the "
                            f"{REPLY_TOKEN_BOUND} bound ({REPLY_CAP_TOKENS}-token output cap)")
    report["reply_length"] = {
        "measure": tokenizer if encode else f"UTF-8 bytes (strict upper bound; {tokenizer})",
        "bound": REPLY_TOKEN_BOUND, "output_cap_num_predict": REPLY_CAP_TOKENS,
        "by_class": {tc: {"median": statistics.median(v), "max": max(v),
                          "pretty_printed_max_diagnostic": max(pretty_lengths[tc])}
                     for tc, v in sorted(lengths.items())}}

    # ---- canonical research signature: the decision clause is normalized to its kind, so equivalent rewordings
    # of a rule cannot hide a repeated gold structure between A′ and B′ in a cell (the frozen signature compares
    # raw rule text, reported above and kept)
    canonical_clashes = [(a, b) for (risk, phase), rows in sorted(research_signatures.items()) if phase == "A"
                         for a, sa in rows for b, sb in research_signatures.get((risk, "B"), []) if sa == sb]
    for a, b in canonical_clashes:
        problems.append(f"canonical research signature (normalized decision clause) repeated between A′ and B′: "
                        f"{a} vs {b}")
    report["canonical_signature_clashes"] = len(canonical_clashes)

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
    # O3 identifier gate (binding for G-ROUTE4; see O3_IDENTIFIER_DECISION.md). The frozen detector stays
    # byte-identical and is still run above; this pinned supplementary gate is the prospective identifier gate.
    # line endings normalized to LF, so the digest does not depend on a checkout's core.autocrlf
    frozen_digest = hashlib.sha256((ROOT / "tools/g_route3_independence.py").read_bytes()
                                   .replace(b"\r\n", b"\n")).hexdigest()
    if frozen_digest != FROZEN_G3_INDEPENDENCE_SHA256:
        problems.append(f"frozen G-ROUTE3 independence checker changed (sha256 {frozen_digest})")
    if sha(IDENT_INTENDED.pattern) != IDENT_GATE_PATTERN_SHA256:
        problems.append("O3 identifier gate pattern differs from its pinned digest")
    id_owners = collections.defaultdict(set)
    for f, _, src in pool:
        found = intended_identifiers(f, content[id(f)])
        for x in found:
            id_owners[x].add((src, f["fixture_id"]))
        if src == "G4":
            undeclared_ids = found - set(design_by[f["fixture_id"]]["identifiers"])
            if undeclared_ids:
                problems.append(f"{f['fixture_id']}: identifiers not declared (O3 identifier gate): "
                                f"{sorted(undeclared_ids)}")
    shared_ids = {x: sorted(fid for _, fid in w) for x, w in id_owners.items()
                  if len({fid for _, fid in w}) > 1 and any(src == "G4" for src, _ in w)}
    for x, w in sorted(shared_ids.items()):
        problems.append(f"O3 identifier gate: shared identifier {x!r}: {w}")
    report["o3_identifier_gate"] = {
        "g4_identifiers": len({x for x, w in id_owners.items() if any(s == "G4" for s, _ in w)}),
        "g3_identifiers": len({x for x, w in id_owners.items() if any(s == "G3" for s, _ in w)}),
        "shared": len(shared_ids), "pattern_sha256": IDENT_GATE_PATTERN_SHA256,
        "frozen_checker_sha256": FROZEN_G3_INDEPENDENCE_SHA256,
        "status": "binding prospective O3 identifier gate for G-ROUTE4; the frozen G-ROUTE3 detector is unchanged "
                  "and G-ROUTE3 is not rescored"}

    # ---- invented names: the committed stream, replayed without any dictionary; contiguous per-class slices;
    # every declared name used in the fixture; unique; screened against the pool and G-ROUTE3
    stream_ok = False
    try:
        stream_data = NS.load_artifact()
        replay = NS.replay_without_dictionary(stream_data)
        stream_ok = True
    except NS.NameStreamUnavailable as exc:
        problems.append(f"name stream: {exc}")
        replay = None
    if stream_ok:
        offset = 0
        for tc in NS.CLASS_ORDER:
            count = stream_data["class_draws"][tc]
            if tc in design_order:
                drawn = [x for dd in design_order[tc] for x in dd["invented_names"] + dd.get("unused_stream_draws", [])]
                if drawn != stream_data["names"][offset:offset + count]:
                    problems.append(f"{tc}: declared name draws are not the committed stream slice")
                for dd in design_order[tc]:
                    span = dd.get("global_name_ordinals")
                    own = dd["invented_names"] + dd.get("unused_stream_draws", [])
                    if span is not None and stream_data["names"][span[0] - 1:span[1]] != own:
                        problems.append(f"{dd['fixture_id']}: global_name_ordinals do not point at its draws")
            offset += count
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
        facing = json.dumps({k: f[k] for k in ("title", "prompt", "input")}, ensure_ascii=False)
        unused = [n for n in d["invented_names"] if n not in facing]
        if unused:
            problems.append(f"{f['fixture_id']}: declared invented names do not occur in the fixture: {unused}")
        input_text = f["input"].get("text", "") if isinstance(f.get("input"), dict) else ""
        missing_ids = {i.rstrip(".") for i in IDENT.findall(input_text)} - set(d["identifiers"])
        if missing_ids:
            problems.append(f"{f['fixture_id']}: identifiers in the text not declared: {sorted(missing_ids)}")
        for n in d["invented_names"] + d.get("unused_stream_draws", []):
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
    report["names"] = {"invented_names_used": sum(len(design_by[f["fixture_id"]]["invented_names"]) for f in fixtures),
                       "stream_draws": sum(all_names.values()),
                       "max_per_fixture": max((len(design_by[f["fixture_id"]]["invented_names"]) +
                                               len(design_by[f["fixture_id"]]["identifiers"]) for f in fixtures),
                                              default=0),
                       "english_screen": "committed name stream (screened at build against the recorded "
                                         "dictionary digests); replayed here with no dictionary",
                       "dictionary_free_replay": replay,
                       "extra_english_screen_run": english is not None}

    # ---- trigram Jaccard per class pool, after pinned-text removal and the 25%-frequency boilerplate rule.
    # Run twice: on the full fixture content (the frozen metric) and on task-relevant content only (every free-text
    # sentence bound to the authoring ledger; unbound sentences are removed, and are failures in their own right).
    relevant = {f["fixture_id"]: I._content(task_relevant_fixture(f, task_units.get(f["fixture_id"])))
                for f in fixtures}
    report["trigram"] = jaccard_pass(pool, content, classes, problems, "trigram Jaccard")
    report["trigram_task_relevant"] = jaccard_pass(
        pool, {id(f): (relevant[f["fixture_id"]] if src == "G4" else content[id(f)]) for f, _, src in pool},
        classes, problems, "task-relevant trigram Jaccard", o5=False)

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
    problems, report = check(staged)            # no dictionary: names are verified against the committed stream
    report["problems"] = problems
    report["passed"] = not problems
    out = HERE / "staging" / "CHECK_REPORT.json"
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    for k, v in report.items():
        if k != "problems":
            print(k, json.dumps(v, ensure_ascii=False))
    for p in problems:
        print("FAIL", p)
    print(f"{sum(len(s['fixtures']) for s in staged)} fixtures checked; {len(problems)} problems")
    sys.exit(1 if problems else 0)
