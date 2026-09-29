"""Adversarial checks for the pre-seal repair gates, run over all five authored classes.

Each case plants a defect (or builds an attack) and must be caught by the named finding. Covered: filler-free
overlap (padding cannot rescue a failing pair), reply-length overflow and the tokenizer's fail-closed fallback,
substantive required_terms (scaffolding copied without the finding fails the frozen validator), the P7
supporting-lineage count, equivalent decision clauses under the canonical signature, research source parity (no
claim copies or literal negations, no verbatim copying between lineages, no P8 comparison leak, the opening
constraint), conversation realism, the O3
identifier gate pins, the dictionary-free name stream, and blind model-facing file separation.

    python -B test_repairs_corpus.py staging/extraction.json staging/synthesis.json staging/planning.json \
        staging/conversation.json staging/research.json
"""

import copy
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "tools"))
import check_corpus as C  # noqa: E402
import name_stream as NS  # noqa: E402
import seal_layout as SL  # noqa: E402
import adjudicator_config as AC  # noqa: E402
from g_route3_semantics import validate_fixture_output  # noqa: E402


def document(staged, task_class):
    return next(d for d in staged if d["task_class"] == task_class)


def locate(staged, fid):
    for d in staged:
        rows = {r["fixture_id"]: r for r in d["fixtures"]}
        if fid in rows:
            return (rows[fid], next(r for r in d["gold"] if r["fixture_id"] == fid),
                    next(r for r in d["design"] if r["fixture_id"] == fid))
    raise KeyError(fid)


def filler(seed, words=160):
    """Task-irrelevant padding with fresh vocabulary (distinct trigrams), as a filler-based pass would use."""
    rng = random.Random(seed)
    letters = "bdfgklmnprstvz"
    vocab = ["".join(rng.choice(letters) + rng.choice("aeiou") for _ in range(3)) for _ in range(words)]
    return " ".join(f"The {vocab[i]} {vocab[i + 1]} {vocab[i + 2]} rested." for i in range(0, words - 2, 3))


# ---------------------------------------------------------------- filler-free overlap
def conversation_pair(staged):
    """Make B a copy of A's task (names swapped): a pair that genuinely fails the overlap bound."""
    conv = document(staged, "ordinary_conversation")
    rows = [r for r in conv["design"] if r["family"] == "CV1" and r["features"]["depth"] == 2]
    fa, _, da = locate(staged, rows[0]["fixture_id"])
    fb, gb, db = locate(staged, rows[1]["fixture_id"])
    names_a, names_b = da["invented_names"], db["invented_names"]
    units = copy.deepcopy(da["message_units"])
    for unit in units:
        for old, new in zip(names_a, names_b):
            unit["text"] = unit["text"].replace(old, new)
        if unit["option"] is not None:
            unit["option"] = names_b[names_a.index(unit["option"])]
    db["message_units"] = units
    fb["input"]["message"] = " ".join(u["text"] for u in units)
    fb["title"], fb["prompt"] = fa["title"], fa["prompt"]
    return fa, fb, da, db


def copied_pair_fails(staged):
    conversation_pair(staged)


def padded_pair_still_fails(staged):
    """Pad both fixtures of a failing pair with filler sentences: the frozen metric is fooled, the task-relevant
    metric is not, and every filler sentence is itself an unbound-sentence failure."""
    fa, fb, _, _ = conversation_pair(staged)
    fa["input"]["message"] += " " + filler("a")
    fb["input"]["message"] += " " + filler("b")


def padded_pair_fools_frozen_metric(staged):
    """Control for the case above: the padded pair no longer trips the frozen (full-content) metric."""
    padded_pair_still_fails(staged)


def filler_as_factless_unit(staged):
    fa, _, da, _ = conversation_pair(staged)
    da["message_units"].insert(1, {"text": filler("c", 12), "option": None, "facts": []})
    fa["input"]["message"] = " ".join(u["text"] for u in da["message_units"])


def unit_facts_stripped(staged):
    """A sentence kept in the message whose ledger binds no fact to it (filler posing as a unit)."""
    _, _, da, _ = conversation_pair(staged)
    da["message_units"][2]["facts"] = []


def filler_folded_into_bound_sentence(staged):
    _, fb, _, db = conversation_pair(staged)
    unit = db["message_units"][1]
    unit["text"] = unit["text"][:-1] + ", " + filler("d", 30).replace(".", "").replace("The ", "the ") + "."
    fb["input"]["message"] = " ".join(u["text"] for u in db["message_units"])


def research_filler_in_source(staged):
    f, _, d = locate(staged, document(staged, "grounded_research_synthesis")["design"][0]["fixture_id"])
    padded = d["research_contract"]["sources"][0]["text"] + " " + filler("e", 24)
    d["research_contract"]["sources"][0]["text"] = f["input"]["sources"][0]["text"] = padded


def synthesis_filler_observation_sentence(staged):
    f, g, d = locate(staged, document(staged, "hierarchical_semantic_synthesis")["design"][0]["fixture_id"])
    obs = f["input"]["observations"][0]
    obs["text"] += " " + filler("f", 9)
    for row in g["reference_output"]["statements"]:
        if obs["id"] in row["observation_ids"]:
            row["text"] = " ".join(o["text"] for o in f["input"]["observations"] if o["id"] in row["observation_ids"])


# ---------------------------------------------------------------- reply length
def overlong_gold(staged):
    f, g, _ = locate(staged, document(staged, "hierarchical_semantic_synthesis")["design"][0]["fixture_id"])
    for obs in f["input"]["observations"]:
        obs["text"] = obs["text"][:-1] + ", and " + " and ".join(["the same point again in other words"] * 6) + "."
    for row in g["reference_output"]["statements"]:
        row["text"] = " ".join(o["text"] for o in f["input"]["observations"] if o["id"] in row["observation_ids"])


# ---------------------------------------------------------------- required terms
def term_from_scaffolding(staged):
    f, g, _ = locate(staged, document(staged, "hierarchical_semantic_synthesis")["design"][0]["fixture_id"])
    oid = f["input"]["observations"][0]["id"]
    word = next(w for w in f["title"].split() if w.casefold() in f["input"]["observations"][0]["text"].casefold()
                and len(w) > 3)
    g["expected"]["required_terms"][oid] = [word.casefold()]


def term_is_scaffold_word(staged):
    f, g, _ = locate(staged, document(staged, "hierarchical_semantic_synthesis")["design"][1]["fixture_id"])
    obs = f["input"]["observations"][0]
    obs["text"] = obs["text"][:-1] + " in the note."
    for row in g["reference_output"]["statements"]:
        row["text"] = " ".join(o["text"] for o in f["input"]["observations"] if o["id"] in row["observation_ids"])
    g["expected"]["required_terms"][obs["id"]] = ["note"]


def term_not_unique(staged):
    f, g, _ = locate(staged, document(staged, "hierarchical_semantic_synthesis")["design"][2]["fixture_id"])
    first, second = f["input"]["observations"][:2]
    shared = second["text"].split()[-1].strip(".").casefold()
    first["text"] = first["text"][:-1] + f" near the {shared}."
    for row in g["reference_output"]["statements"]:
        row["text"] = " ".join(o["text"] for o in f["input"]["observations"] if o["id"] in row["observation_ids"])
    g["expected"]["required_terms"][first["id"]] = [shared]


# ---------------------------------------------------------------- research: P7, clauses, parity
def p7_supporting_count_ambiguous(staged):
    """A P7 fixture where the later source supports C1 after an earlier denial, and nothing else holds
    single_lineage_support: counted over cited lineages C1 has two, counted over supporting lineages it has one."""
    research = document(staged, "grounded_research_synthesis")
    for row in research["design"]:
        if row["features"]["pattern"] != "P7" or row["features"]["sls"]:
            continue
        f, g, d = locate(staged, row["fixture_id"])
        contract, risk = d["research_contract"], f["consequence_risk"]
        older, newer = [s for s in contract["sources"] if s["claim_id"] == "C1"]
        claim = contract["claims"][0]
        topic = C.research_topic(risk, claim)
        for source, relation, body in ((older, "deny", topic[3]), (newer, "support", topic[1])):
            prefix = source["text"][: len(source["text"]) - len(C.split_source_prefix(source["text"])[2])]
            source["relation"], source["text"] = relation, prefix + body.replace("{S}", claim["subject"])
            next(s for s in f["input"]["sources"] if s["source_id"] == source["source_id"])["text"] = source["text"]
        expected, reasons = C.research_gold("P7", contract["claims"], contract["sources"],
                                            f["input"]["allowed_recommendations"])
        if "single_lineage_support" in expected["uncertainties"] or \
                not C.sls_supporting_reading(contract["sources"], expected):
            continue
        g["expected"], g["reference_output"], contract["derived_reasons"] = expected, copy.deepcopy(expected), reasons
        return
    raise KeyError("no P7 fixture to construct the ambiguity from")


def equivalent_clause_hides_clash(staged):
    """Give a B′ fixture an A′ fixture's exact gold structure, then reword its decision rule into an equivalent
    clause that the frozen signature's raw-text snippet does not match: the canonical signature still clashes."""
    research = document(staged, "grounded_research_synthesis")
    a_row, b_row = next((a, b) for a in research["design"] for b in research["design"]
                        if a["phase"] == "A" and b["phase"] == "B" and a["risk"] == b["risk"] and
                        a["family"] == b["family"] and a["features"]["pattern"] == b["features"]["pattern"])
    fa, ga, da = locate(staged, a_row["fixture_id"])
    fb, gb, db = locate(staged, b_row["fixture_id"])
    fb["input"] = copy.deepcopy(fa["input"])
    gb["expected"], gb["reference_output"] = copy.deepcopy(ga["expected"]), copy.deepcopy(ga["reference_output"])
    db["research_contract"] = copy.deepcopy(da["research_contract"])
    db["invented_names"], fb["prompt"] = list(da["invented_names"]), fa["prompt"]
    pos, neg = fb["input"]["allowed_recommendations"]
    rule = {"all_supported": f"Recommend '{pos}' if all of the claims are supported, and '{neg}' otherwise.",
            "focal_two_lineages": f"Recommend '{pos}' if C1 is backed by at least two lineages, and '{neg}' otherwise.",
            "temporal_all_supported": "Dated sources that disagree are resolved in favour of the most recent date, and "
                                      f"every source about the claim is cited. Recommend '{pos}' if all claims end "
                                      f"up supported, and '{neg}' otherwise."}[da["research_contract"]["decision"]["kind"]]
    assert rule != fa["input"]["decision_rule"] and " only if" not in rule and " only if" in fa["input"]["decision_rule"]
    fb["input"]["decision_rule"] = rule
    staged.append({"_pair": (a_row["fixture_id"], b_row["fixture_id"])})


def source_copies_claim(staged):
    f, _, d = locate(staged, document(staged, "grounded_research_synthesis")["design"][0]["fixture_id"])
    source = d["research_contract"]["sources"][0]
    claim = next(c for c in d["research_contract"]["claims"] if c["claim_id"] == source["claim_id"])
    source["text"] = f["input"]["sources"][0]["text"] = claim["text"]


def source_is_literal_negation(staged):
    research = document(staged, "grounded_research_synthesis")
    row = next(r for r in research["design"] if r["features"]["pattern"] == "P2")
    f, _, d = locate(staged, row["fixture_id"])
    source = next(s for s in d["research_contract"]["sources"] if s["claim_id"] == "C1")
    claim = d["research_contract"]["claims"][0]
    words = claim["text"].split()
    negated = " ".join(words[:2] + ["does", "not"] + words[2:])
    source["text"] = next(s for s in f["input"]["sources"] if s["source_id"] == source["source_id"])["text"] = negated


def independent_sources_copy_wording(staged):
    """P1's two independent lineages state the same sentence word for word."""
    research = document(staged, "grounded_research_synthesis")
    row = next(r for r in research["design"] if r["features"]["pattern"] == "P1")
    f, _, d = locate(staged, row["fixture_id"])
    first, second = d["research_contract"]["sources"][:2]
    second["text"] = f["input"]["sources"][1]["text"] = first["text"]


def p8_states_comparison(staged):
    research = document(staged, "grounded_research_synthesis")
    row = next(r for r in research["design"] if r["features"]["pattern"] == "P8")
    f, _, d = locate(staged, row["fixture_id"])
    source, claim = d["research_contract"]["sources"][0], d["research_contract"]["claims"][0]
    source["text"] = source["text"][:-1] + f", below the required {claim['threshold']}."
    f["input"]["sources"][0]["text"] = source["text"]


def research_wrong_opening(staged):
    f, _, d = locate(staged, document(staged, "grounded_research_synthesis")["design"][0]["fixture_id"])
    body = f["prompt"][len(f"Assess the claims about {d['invented_names'][0]} and {d['invented_names'][1]}"):]
    f["prompt"] = f"Check what {d['invented_names'][0]} and {d['invented_names'][1]} say" + body


def declared_signature_tampered(staged):
    _, _, d = locate(staged, document(staged, "grounded_research_synthesis")["design"][0]["fixture_id"])
    d["research_contract"]["canonical_signature"][-1] = "all_supported_reworded"


# ---------------------------------------------------------------- conversation realism
def conversation_flag_fact(staged):
    conv = document(staged, "ordinary_conversation")
    row = next(r for r in conv["design"] if r["family"] == "CV1" and r["features"]["depth"] == 1)
    row["message_units"][1]["facts"][0]["value"] = True


def conversation_cv3_without_conversion(staged):
    conv = document(staged, "ordinary_conversation")
    row = next(r for r in conv["design"] if r["family"] == "CV3")
    f, _, d = locate(staged, row["fixture_id"])
    for unit in d["message_units"]:
        for fact in unit["facts"]:
            if fact["fmt"][0] == "m":
                base = min(C.CONV_UNIT[fact["fmt"][1]], key=C.CONV_UNIT[fact["fmt"][1]].get)
                new_fmt = ["m", fact["fmt"][1], base]
                new = C.conversation_surface(fact["value"], new_fmt)
                unit["text"] = unit["text"].replace(fact["surface"], new, 1)
                fact["fmt"], fact["surface"] = new_fmt, new
    f["input"]["message"] = " ".join(u["text"] for u in d["message_units"])


def research_lineage_repeats_word(staged):
    f, _, d = locate(staged, document(staged, "grounded_research_synthesis")["design"][0]["fixture_id"])
    old = d["research_contract"]["sources"][0]["lineage"]
    new = old + "-" + old.split("-")[-1]
    d["research_contract"]["sources"][0]["lineage"] = new
    f["input"]["sources"][0]["lineage"] = new


def research_lineage_wrong_topic(staged):
    f, _, d = locate(staged, document(staged, "grounded_research_synthesis")["design"][0]["fixture_id"])
    used = {source["lineage"] for row in document(staged, "grounded_research_synthesis")["fixtures"]
            for source in row["input"]["sources"]}
    wrong = next(name for name in C.RT.lineage_options("performance") if name not in used)
    d["research_contract"]["sources"][0]["lineage"] = wrong
    f["input"]["sources"][0]["lineage"] = wrong


def conversation_cv3_huge_tiny_unit(staged):
    f, _, d = locate(staged, "B4-CONV-R2-03")
    for unit in d["message_units"]:
        for fact in unit["facts"]:
            if fact["attr"] in {"need", "vol"}:
                old = fact["surface"]
                fact["value"] *= 10
                fact["surface"] = C.conversation_surface(fact["value"], fact["fmt"])
                unit["text"] = unit["text"].replace(old, fact["surface"], 1)
    f["input"]["message"] = " ".join(unit["text"] for unit in d["message_units"])


def conversation_cv2_counter_not_clock(staged):
    conv = document(staged, "ordinary_conversation")
    row = next(r for r in conv["design"] if r["family"] == "CV2" and
               r["message_units"][0]["facts"][0]["fmt"][0] == "t")
    f, _, d = locate(staged, row["fixture_id"])
    fact = d["message_units"][0]["facts"][0]
    new = C.conversation_surface(fact["value"], ["n", ""])
    d["message_units"][0]["text"] = d["message_units"][0]["text"].replace(fact["surface"], new, 1)
    fact["fmt"], fact["surface"] = ["n", ""], new
    f["input"]["message"] = " ".join(u["text"] for u in d["message_units"])


# ---------------------------------------------------------------- O3 identifier gate pins, name stream
def o3_gate_pattern_changed(staged):
    C.IDENT_INTENDED = C.re.compile(r"\b([A-Z]{2,5}-?\d[\w.-]*)\b")


def frozen_checker_digest_changed(staged):
    C.FROZEN_G3_INDEPENDENCE_SHA256 = "0" * 64


def name_stream_missing(staged):
    NS.ARTIFACT = HERE / "no_such_name_stream.json"
    NS.load_artifact.__defaults__ = (NS.ARTIFACT, NS.PINNED_STREAM_SHA256)


def name_stream_rejections_tampered(staged):
    data = NS.load_artifact()
    data["screen"]["english_rejections"] = data["screen"]["english_rejections"][1:]
    NS.load_artifact = lambda *a, **k: data


def english_word_as_name(staged):
    f, _, d = locate(staged, document(staged, "grounded_research_synthesis")["design"][0]["fixture_id"])
    old = d["invented_names"][0]
    for key in ("prompt", "title"):
        f[key] = f[key].replace(old, "Here")
    d["invented_names"][0] = "Here"


# the cases: (mutation, expected finding, unused slot kept for per-case notes)
CASES = [
    (copied_pair_fails, "trigram Jaccard", None),
    (padded_pair_still_fails, "task-relevant trigram Jaccard", None),
    (padded_pair_still_fails, "conversation message is not exactly its ledger units", None),
    (filler_as_factless_unit, "conversation ledger is not one request unit and one unit per option", None),
    (unit_facts_stripped, "sentence carries no fact the answer depends on", None),
    (filler_folded_into_bound_sentence, "is not one sentence within the cap (filler)", None),
    (research_filler_in_source, "is not one sentence within the cap (filler)", None),
    (synthesis_filler_observation_sentence, "is not one sentence within the cap (filler)", None),
    (overlong_gold, "over the 250 bound", None),
    (term_from_scaffolding, "satisfiable from scaffolding", None),
    (term_is_scaffold_word, "are not substantive observation content", None),
    (term_not_unique, "all occur in other observations", None),
    (p7_supporting_count_ambiguous, "single_lineage_support is ambiguous", None),
    (equivalent_clause_hides_clash, "canonical research signature (normalized decision clause) repeated", None),
    (source_copies_claim, "is the claim sentence or its literal negation", None),
    (source_is_literal_negation, "is the claim sentence or its literal negation", None),
    (independent_sources_copy_wording, "sources from different lineages share identical wording", None),
    (p8_states_comparison, "states the threshold or a comparison", None),
    (research_wrong_opening, "research opening or invented-name binding is invalid", None),
    (declared_signature_tampered, "declared canonical signature differs", None),
    (conversation_flag_fact, "may not be a pre-evaluated flag", None),
    (conversation_cv3_without_conversion, "CV3 states every quantity in one unit (no conversion)", None),
    (research_lineage_repeats_word, "repeats an issuer or channel word", None),
    (research_lineage_wrong_topic, "does not match its source topic", None),
    (conversation_cv3_huge_tiny_unit, "CV3 uses an implausibly large value in a tiny unit", None),
    (conversation_cv2_counter_not_clock, "is not a real clock/date expression", None),
    (o3_gate_pattern_changed, "O3 identifier gate pattern differs from its pinned digest", None),
    (frozen_checker_digest_changed, "frozen G-ROUTE3 independence checker changed", None),
    (name_stream_missing, "name stream: name-stream artifact missing", None),
    (name_stream_rejections_tampered, "name stream: ", None),
    (english_word_as_name, "declared name draws are not the committed stream slice", None),
]


def run_case(staged, mutation):
    saved = (C.IDENT_INTENDED, C.FROZEN_G3_INDEPENDENCE_SHA256, NS.ARTIFACT, NS.load_artifact,
             NS.load_artifact.__defaults__)
    candidate = copy.deepcopy(staged)
    try:
        mutation(candidate)
        extra = [d for d in candidate if "_pair" in d]
        candidate = [d for d in candidate if "_pair" not in d]
        problems, _ = C.check(candidate)
    finally:
        C.IDENT_INTENDED, C.FROZEN_G3_INDEPENDENCE_SHA256, NS.ARTIFACT, NS.load_artifact = saved[:4]
        NS.load_artifact.__defaults__ = saved[4]
    return problems, extra


def standalone_checks(staged):
    """Checks that are not corpus mutations. Returns [(name, passed, detail)]."""
    out = []
    # 1. padding fools the frozen metric for the copied pair, so only the task-relevant metric can catch it
    problems, _ = run_case(staged, padded_pair_fools_frozen_metric)
    fa, fb, _, _ = conversation_pair(copy.deepcopy(staged))
    frozen_hit = [p for p in problems if p.startswith("trigram Jaccard") and fa["fixture_id"] in p and
                  fb["fixture_id"] in p]
    relevant_hit = [p for p in problems if p.startswith("task-relevant trigram Jaccard") and fa["fixture_id"] in p
                    and fb["fixture_id"] in p]
    out.append(("padding_defeats_frozen_metric_only", not frozen_hit and bool(relevant_hit),
                f"frozen flags pair: {bool(frozen_hit)}; task-relevant flags pair: {bool(relevant_hit)}"))
    # 2. the equivalent clause evades the frozen raw-text signature (so the canonical one is what catches it)
    problems, extra = run_case(staged, equivalent_clause_hides_clash)
    a, b = extra[0]["_pair"]
    out.append(("equivalent_clause_evades_frozen_signature",
                not any(p.startswith("fine signature repeated") and a in p and b in p for p in problems) and
                any(p.startswith("canonical research signature") and a in p and b in p for p in problems),
                f"{a} vs {b}"))
    # 3. scaffolding copied without the finding fails the frozen validator for every Synthesis observation
    synthesis = document(staged, "hierarchical_semantic_synthesis")
    total = caught = 0
    for f in synthesis["fixtures"]:
        g = next(r for r in synthesis["gold"] if r["fixture_id"] == f["fixture_id"])
        opening = f["prompt"].split(" observations.")[0]
        statements = []
        for i, obs in enumerate(f["input"]["observations"]):
            scaffold = (f"{f['title']}. {opening} observations: {obs['role'].replace('_', ' ')} observation "
                        f"{obs['id']} filed as {obs['role']} under {g['expected']['conclusion']}; "
                        f"{f['input']['conclusion_rule']}")
            statements.append({"statement_id": f"S{i + 1}", "role": obs["role"], "observation_ids": [obs["id"]],
                               "text": scaffold})
        reply = json.dumps({"statements": statements, "conclusion": g["expected"]["conclusion"]})
        result = validate_fixture_output(f, g, reply)
        missing = [r for r in result.get("reasons", []) if str(r).startswith("meaning_anchor_missing")]
        total += len(f["input"]["observations"])
        caught += len(missing)
        if result.get("hard_gate_pass"):
            out.append(("scaffolding_copy_fails", False, f"{f['fixture_id']} passed with scaffolding only"))
    out.append(("scaffolding_copy_fails_every_observation", caught == total, f"{caught} of {total} observations"))
    # 4. the reply-length gate fails closed without the pinned tokenizer (bytes bound every byte-level BPE)
    saved = C.pinned_tokenizer
    C.pinned_tokenizer = lambda: (None, "tokenizer withheld by the test")
    try:
        problems, report = C.check([document(staged, "hierarchical_semantic_synthesis")])
    finally:
        C.pinned_tokenizer = saved
    over = [p for p in problems if "over the 250 bound" in p]
    out.append(("reply_gate_fails_closed_without_tokenizer", bool(over) and "UTF-8 bytes" in
                report["reply_length"]["measure"], f"{len(over)} Synthesis replies rejected on the bytes bound"))
    # 5. the pinned tokenizer refuses a file whose digest differs
    saved_digest = C.CL100K_SHA256
    C.CL100K_SHA256 = "f" * 64
    try:
        encode, why = C.pinned_tokenizer()
    finally:
        C.CL100K_SHA256 = saved_digest
    out.append(("tokenizer_digest_pinned", encode is None and "digest" in why, why))
    # 6. the dictionary-free replay reproduces the stream; the checker never imports the dictionary module
    replay = NS.replay_without_dictionary(NS.load_artifact())
    source = (HERE / "check_corpus.py").read_text(encoding="utf-8")
    out.append(("name_stream_dictionary_free", replay["stream_sha256"] == NS.PINNED_STREAM_SHA256 and
                "english_vocabulary" not in source and sys.modules.get("english_vocabulary") is None, str(replay)))
    # 7. a tampered stream (two names swapped, internal digest recomputed) fails the pinned digest
    data = NS.load_artifact()
    data["names"][0], data["names"][1] = data["names"][1], data["names"][0]
    data["stream_sha256"] = NS.stream_digest(data["names"])
    tmp = HERE / "staging" / "_tampered_name_stream.json"
    tmp.write_text(json.dumps(data), encoding="utf-8")
    try:
        NS.load_artifact(tmp)
        refused = False
    except NS.NameStreamUnavailable:
        refused = True
    finally:
        tmp.unlink()
    out.append(("name_stream_pinned_digest", refused, "tampered stream refused"))
    # 8. blind separation of the seal layout, and a planted gold key is caught
    layout = SL.build_layout(copy.deepcopy(staged), AC.config())
    clean = SL.verify_blind(layout)
    planted = copy.deepcopy(layout)
    planted["corpus_b.json"]["fixtures"][0]["input"]["expected"] = "leak"
    leaked = SL.verify_blind(planted)
    planted2 = copy.deepcopy(layout)
    planted2["reserve_corpus_a.json"]["fixtures"][0]["rationale"] = "leak"
    leaked2 = SL.verify_blind(planted2)
    out.append(("blind_model_facing_files", not clean and bool(leaked) and bool(leaked2),
                f"clean: {clean or 'no problems'}; planted input key: {leaked[:1]}; planted top-level: {leaked2[:1]}"))
    # 9. the adjudicator sees only model-facing fixtures, rendered exactly as the models see them
    from g_route3_contract import render_prompt
    fixtures = [f for d in staged for f in d["fixtures"]]
    same = all(AC.render_request(f) == {"system": render_prompt(f)["system"], "user": render_prompt(f)["prompt"]}
               for f in fixtures)
    try:
        AC.render_request(dict(fixtures[0], expected={"answer": "x"}))
        refused = False
    except ValueError:
        refused = True
    out.append(("adjudicator_rendering_blind", same and refused, "identical rendering; gold-bearing input refused"))
    # 10. decision clauses: every authored rule classifies to its pattern's kind; rewordings keep the kind
    kinds = {}
    for f, d in zip(document(staged, "grounded_research_synthesis")["fixtures"],
                    document(staged, "grounded_research_synthesis")["design"]):
        kinds[f["input"]["decision_rule"]] = (C.classify_decision(f["input"]["decision_rule"],
                                                                  *f["input"]["allowed_recommendations"]),
                                              d["research_contract"]["decision"]["kind"])
    out.append(("decision_clauses_normalize", all(a == b for a, b in kinds.values()),
                f"{len(kinds)} distinct rule texts"))
    return out


if __name__ == "__main__":
    staged = [json.loads(Path(path).read_text(encoding="utf-8")) for path in sys.argv[1:]]
    clean, _ = C.check(staged)
    assert not clean, clean[:5]
    print("clean five-class corpus: 0 problems")
    missed = 0
    for mutation, expected, _ in CASES:
        problems, _ = run_case(staged, mutation)
        hits = [p for p in problems if expected in p]
        print(("FIRES " if hits else "MISSED"), mutation.__name__, "->", hits[0][:160] if hits else problems[:3])
        missed += not hits
    results = standalone_checks(staged)
    for name, passed, detail in results:
        print(("PASS  " if passed else "FAIL  "), name, "->", detail[:200])
        missed += not passed
    total = len(CASES) + len(results)
    print(f"{total - missed} of {total} repair-gate checks passed")
    raise SystemExit(1 if missed else 0)
