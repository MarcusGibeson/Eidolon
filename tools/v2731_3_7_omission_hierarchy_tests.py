from __future__ import annotations

"""Suffix omission and hierarchical synthesis in review_experiment (spec 2.20).

Deterministic stub model; no provider contact. Proves the distinction between a safe suffix omission (a single trailing
ellipsis after an exact, uniquely relocatable prefix within one record, with nothing the statement relies on left in the
omitted text) and evidence stitching, which stays rejected in every form. Proves the two-level synthesis keeps evidence
lineage: every intermediate statement cites observations of its own unit and is supported by them, every grounded
observation must be cited (a lone contradicting observation cannot be dropped), every final entry is traceable through
intermediate statements to observations, and a failed intermediate or final stage leaves the review incomplete with the
point of loss named. Also proves the statement allocation keeps the final input inside its budget by construction and
that the intermediate and final prompts fit the 8,192-token context.
"""

import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for value in (str(ROOT), str(AGENT)):
    if value not in sys.path:
        sys.path.insert(0, value)
sys.dont_write_bytecode = True
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2731-3-7-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

import experiment_review as er  # noqa: E402

CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- suffix omission versus stitching ---------------------------------------------------------------------------------------------
TEXT = ("form=V1 item=A classification=unresolved seconds=1.0 attempts=1\n"
        "form=V1 item=B classification=continuing seconds=2.0 attempts=1\n"
        "form=V2 item=A classification=event_only seconds=1.5 attempts=2\n"
        "form=V2 item=B classification=continuing seconds=2.5 attempts=1\n"
        'schema: {"state_relation": "...", "end_cue": null}\n')


def ground(statement, quotes, text=TEXT):
    grounded, rejected, _ = er.ground_observations({"observations": [{"statement": statement, "quotes": quotes}]}, text, "D3", 1, 1)
    return (grounded[0], None) if grounded else (None, rejected[0])


o, _ = ground("item A is unresolved under V1", ["form=V1 item=A classification=unresolved ..."])
q = o["quotes"][0] if o else {}
require(o and q["text"] == "form=V1 item=A classification=unresolved" and q["omission"]["marker"] == "..."
        and q["omission"]["omitted_suffix"] == " seconds=1.0 attempts=1" and q["omission"]["omitted_suffix_chars"] == 23
        and q["omission"]["as_returned"] == "form=V1 item=A classification=unresolved ..." and TEXT[q["char_start"]:q["char_end"]] == q["text"],
        "a_single_trailing_ellipsis_grounds_only_the_exact_prefix_and_records_the_omission")
require("..." not in q["text"] and q["occurrences_in_part"] == 1, "the_ellipsis_itself_is_never_quoted_evidence")
o, _ = ground("item A is unresolved under V1", ["form=V1 item=A classification=unresolved …"])
require(o and o["quotes"][0]["omission"]["marker"] == "…", "the_unicode_ellipsis_is_the_same_marker")
o, _ = ground("the schema shows placeholder values", ['{"state_relation": "...", "end_cue": null}'])
o2, _ = ground("the schema has a placeholder", ['schema: {"state_relation": "...'])
require(o and o["quotes"][0]["omission"] is None and o2 and o2["quotes"][0]["omission"] is None,
        "an_ellipsis_that_is_in_the_source_is_matched_exactly_not_read_as_an_omission")
for name, quotes, reason in (
        ("internal_ellipsis", ["form=V1 ... classification=unresolved"], "stitched_quote"),
        ("internal_and_trailing_ellipsis", ["form=V1 ... classification=unresolved ..."], "stitched_quote"),
        ("skipped_internal_text", ["form=V1 classification=unresolved"], "quote_not_found_in_document"),
        ("assembled_from_two_records", ["classification=unresolved seconds=1.0 attempts=1 form=V1 item=B ..."], "omission_spans_records"),
        ("prefix_not_relocatable", ["form=V9 item=A ..."], "omission_prefix_not_found"),
        ("prefix_ambiguous", ["classification=continuing ..."], "omission_prefix_ambiguous"),
        ("prefix_splits_a_word", ["form=V1 item=A classification=unres ..."], "omission_splits_a_word")):
    o, r = ground("item A is unresolved under V1", quotes)
    require(o is None and r["reason"] == reason, f"rejected:{name}")
o, r = ground("item A took 1.0 seconds under V1", ["form=V1 item=A classification=unresolved ..."])
require(o is None and r["reason"] == "omission_hides_attributed_content" and r["hidden_terms"] == ["seconds"],
        "an_omission_that_hides_what_the_statement_attributes_is_rejected")
o, _ = ground("item A took seconds=1.0 under V1", ["form=V1 item=A classification=unresolved ...", "seconds=1.0 attempts=1"])
require(o and o["quotes"][1]["omission"] is None, "attributed_content_quoted_exactly_elsewhere_is_not_hidden")
o, _ = ground("item A is unresolved under V1", ["form=V1 item=A classification=unresolved ..."], text=TEXT.replace("\n", "\r\n"))
require(o and o["quotes"][0]["omission"]["omitted_suffix"] == " seconds=1.0 attempts=1", "a_crlf_record_end_is_not_part_of_the_omitted_suffix")
o, _ = ground("item A is unresolved under V1 and event_only under V2",
              ["form=V1 item=A classification=unresolved ...", "form=V2 item=A classification=event_only ..."])
require(o and [x["line_start"] for x in o["quotes"]] == [1, 3] and all(x["omission"] for x in o["quotes"]),
        "a_comparison_may_use_one_suffix_omission_per_record")

# --- the review, with a conforming stub ---------------------------------------------------------------------------------------
OUTPUTS = ("form=V1 item=A classification=unresolved\nform=V1 item=B classification=continuing\n"
           "form=V2 item=A classification=event_only\nform=V2 item=B classification=continuing\n")
DOCS = {"design.txt": ("design", "The experiment asks whether each item keeps its label across prompt forms.\nForms: V1, V2.\n"),
        "items.txt": ("corpus", "item=A gold=unresolved\nitem=B gold=continuing\n"),
        "outputs.txt": ("raw_outputs", OUTPUTS)}
OK_META = {"seconds": 0.0, "metrics": {"eval_count": 50, "prompt_eval_count": 900}}
FIRST = {"experiment_understanding": {"statement": "It checks label stability.", "int_ids": ["I1"]},
         "observations": [{"statement": "the record lists forms", "int_ids": ["I1", "I3"]}], "passed": [], "failed": [], "failure_clusters": [],
         "possible_harness_or_measurement_failures": [], "possible_model_or_reasoning_failures": [], "ambiguous_cases": []}
SECOND = {"competing_hypotheses": [{"hypothesis": "labels move near a boundary", "evidence_for": ["I3"], "evidence_against": ["I2"]}],
          "unknowns": [{"statement": "why", "int_ids": ["I3"]}], "confidence": {"level": "low", "reason": "small", "int_ids": ["I1"]},
          "discriminating_experiments": [{"experiment": "repeat", "distinguishes": [1], "int_ids": ["I3"]}],
          "not_established": [{"statement": "a cause", "int_ids": ["I2"]}]}


def make_package(base: Path, *, docs: dict = DOCS, optional: tuple = ()) -> Path:
    pkg = base / "pkg"
    pkg.mkdir(parents=True, exist_ok=True)
    entries = []
    for n, (name, (role, text)) in enumerate(docs.items(), 1):
        (pkg / name).write_text(text, encoding="utf-8", newline="\n")
        entry = {"doc_id": f"D{n}", "path": name, "role": role, "description": name, "sha256": sha(pkg / name)}
        if name in optional:
            entry["optional"] = True
        entries.append(entry)
    (pkg / er.MANIFEST_NAME).write_text(json.dumps({"experiment_id": "TEST", "title": "Test experiment", "task": "independent_review",
                                                    "brief": "Review it.", "documents": entries}), encoding="utf-8")
    return pkg


def good(prompt, m):
    line = prompt.split("---\n", 1)[1].rsplit("\n---\n", 1)[0].strip().splitlines()[0]
    return json.dumps({"observations": [{"statement": f"the part contains {line}", "quotes": [line]}], "open_questions": []}), dict(OK_META)


def unit_ids(prompt):
    return re.findall(r"^(O[0-9]+) [(]part [0-9]+[)]: ", prompt, re.M)


def unit_cap(prompt):
    return int(re.search(r"Give at most ([0-9]+) statements", prompt).group(1))


def cover(prompt, m):
    ids = unit_ids(prompt)
    groups = [ids[i:i + er.MAX_IDS_PER_STATEMENT] for i in range(0, len(ids), er.MAX_IDS_PER_STATEMENT)][:unit_cap(prompt)]
    return json.dumps({"statements": [{"statement": "the unit records these observations", "kind": "finding", "obs_ids": g} for g in groups]}), dict(OK_META)


def statements(*rows, meta=None):
    return lambda p, m: (json.dumps({"statements": [dict(zip(("statement", "kind", "obs_ids"), r)) for r in rows]}), dict(meta or OK_META))


def observations(*items):
    return lambda p, m: (json.dumps({"observations": list(items), "open_questions": []}), dict(OK_META))


BAD = lambda p, m: ("{not json", dict(OK_META))  # noqa: E731
ERROR = lambda p, m: ("", {"seconds": 1.0, "error": "LocalModelHTTPError: connection refused"})  # noqa: E731


class Stub:
    def __init__(self, script=None, *, first=FIRST, second=SECOND):
        self.script = {k: list(v) for k, v in (script or {}).items()}
        self.first, self.second = first, second
        self.prompts: list[tuple[str, str]] = []

    def __call__(self, prompt, max_tokens):
        if "List up to" in prompt:
            key = f"{re.search(r'document (D[0-9]+) [(]', prompt).group(1)}:{re.search(r'[)], part ([0-9]+) of', prompt).group(1)}"
            default = good
        elif "Write a bounded synthesis" in prompt:
            key, default = "I:" + re.search(r"document (D[0-9]+) [(]", prompt).group(1), cover
        elif "first half" in prompt and "second half" not in prompt:
            key, default = "first_half", (lambda p, m: (json.dumps(self.first), dict(OK_META)))
        else:
            key, default = "second_half", (lambda p, m: (json.dumps(self.second), dict(OK_META)))
        self.prompts.append((key, prompt))
        queue = self.script.get(key)
        return (queue.pop(0) if queue else default)(prompt, max_tokens)

    def count(self, prefix):
        return sum(k.startswith(prefix) for k, _ in self.prompts)


IDENT = {"model": "stub", "provider": "stub", "context_size": 8192, "resolved_config_sha256": "0" * 64}
base = Path(tempfile.mkdtemp(prefix="eidolon-v2731-3-7-case-"))
counter = iter(range(10_000))


def review(script=None, *, docs=DOCS, optional=(), first=FIRST, second=SECOND):
    stub = Stub(script, first=first, second=second)
    return er.review_experiment(make_package(base / f"case{next(counter)}", docs=docs, optional=optional), call_model=stub, identity=IDENT), stub


def units_failed(art):
    return {m["unit_id"]: m for m in art["coverage"]["missing"] if m["kind"] == "intermediate_unit_failed"}


# omission is a general rule, not a special case: it grounds in a design document exactly as in raw outputs
art, _ = review({"D1:1": [observations({"statement": "the design states what the experiment asks", "quotes": ["The experiment asks whether each item keeps ..."]})]})
require(art["status"] == "complete" and art["grounded_observations"][0]["quotes"][0]["omission"]["omitted_suffix"] == " its label across prompt forms."
        and art["integrity_metrics"]["omission_quotes"] == 1, "suffix_omission_applies_to_any_document_role")

# --- a clean hierarchy: lineage from final entries through intermediate statements to observations ----------------------------
art, stub = review()
inter = art["intermediate"]
by_int = {s["int_id"]: s for s in inter["statements"]}
unit_of = {u["unit_id"]: u for u in inter["units"]}
lv = art["coverage"]["levels"]
require(art["status"] == "complete" and [u["doc_id"] for u in inter["units"]] == ["D1", "D2", "D3"] and all(u["status"] == "accepted" for u in inter["units"])
        and lv["observations"]["coverage"] == 1.0 and lv["intermediate"]["coverage"] == 1.0 and lv["intermediate"]["delivered_to_final"] == len(by_int),
        "a_clean_hierarchy_reviews_every_level")
require(all(set(s["obs_ids"]) <= set(unit_of[s["unit_id"]]["obs_ids"]) for s in inter["statements"]), "intermediate_statements_cite_only_their_units_observations")
entries = [art["review"]["experiment_understanding"], *[e for k in er.SECTIONS_A[1:] for e in art["review"][k]], *art["review"]["unknowns"],
           art["review"]["confidence"], *art["review"]["not_established"]]
require(all(e["int_ids"] and set(e["obs_ids"]) == {o for i in e["int_ids"] for o in by_int[i]["obs_ids"]} for e in entries)
        and art["review"]["competing_hypotheses"][0]["obs_ids"] == by_int["I3"]["obs_ids"] + by_int["I2"]["obs_ids"],
        "every_final_entry_is_traceable_through_intermediate_statements_to_observations")
inter_prompts = [p for k, p in stub.prompts if k.startswith("I:")]
final_prompts = [p for k, p in stub.prompts if k in ("first_half", "second_half")]
require(all(sum(f"{o['obs_id']} (part" in p for p in inter_prompts) == 1 for o in art["grounded_observations"])
        and not any("(part " in p for p in final_prompts) and all("[D3, finding]: the unit records" in p for p in final_prompts),
        "each_observation_reaches_exactly_one_intermediate_prompt_and_final_prompts_see_only_intermediate_statements")
md = (RUNTIME / er.REVIEW_AREA / art["review_id"] / "review.md").read_text(encoding="utf-8")
require("## Lineage: intermediate syntheses" in md and "cited by intermediate syntheses (100%)" in md, "the_markdown_shows_lineage_and_level_coverage")

# --- a contradicting minority observation cannot be dropped ---------------------------------------------------------------------
TWO = observations({"statement": "item B is continuing under both forms", "quotes": ["form=V1 item=B classification=continuing", "form=V2 item=B classification=continuing"]},
                   {"statement": "item A differs between the forms", "quotes": ["form=V1 item=A classification=unresolved", "form=V2 item=A classification=event_only"]})
majority_only = statements(("item B is continuing under both forms", "finding", ["O3"]))
art, stub = review({"D3:1": [TWO], "I:D3": [majority_only, majority_only]})
failed = units_failed(art)
md = (RUNTIME / er.REVIEW_AREA / art["review_id"] / "review.md").read_text(encoding="utf-8")
require(art["status"] == "incomplete" and failed["U3"]["reason"] == "uncited_observations" and failed["U3"]["uncited_obs_ids"] == ["O4"]
        and stub.count("first_half") == stub.count("second_half") == 0 and "failed: uncited_observations; uncited observations O4" in md,
        "an_intermediate_synthesis_that_leaves_an_observation_uncited_fails_and_names_it")
art, _ = review({"D3:1": [TWO], "I:D3": [majority_only]})
require(art["status"] == "complete" and "intermediate:U3" in art["runtime_accounting"]["recovered_stages"], "the_single_registered_retry_can_recover_citation_coverage")
kept = statements(("item B is continuing under both forms", "finding", ["O3"]), ("item A differs between the forms", "contradiction", ["O4"]))
art, stub = review({"D3:1": [TWO], "I:D3": [kept]})
require(art["status"] == "complete" and all("[D3, contradiction]: item A differs between the forms" in p for k, p in stub.prompts if k in ("first_half", "second_half")),
        "a_contradiction_reaches_the_final_level_labelled_as_one")

# --- no intermediate statement may add evidence, cite outside its unit, or exceed its bounds -------------------------------------
unsupported = statements(("ST99 differs between the forms", "contradiction", ["O4"]), ("item B is continuing under both forms", "finding", ["O3"]))
art, _ = review({"D3:1": [TWO], "I:D3": [unsupported, unsupported]})
require(units_failed(art).get("U3", {}).get("uncited_obs_ids") == ["O4"]
        and (art["intermediate"]["units"][2].get("rejected_statements_last_attempt") or [{}])[0].get("identifiers") == ["st99"],
        "an_intermediate_statement_naming_an_identifier_absent_from_its_observations_is_rejected")
mixed = statements(("ST99 differs", "contradiction", ["O4"]), ("item A differs between V1 and V2", "contradiction", ["O4"]),
                   ("item B is continuing under both forms", "finding", ["O3"]))
art, _ = review({"D3:1": [TWO], "I:D3": [mixed]})
require(art["status"] == "complete" and [s["statement"] for s in art["intermediate"]["statements"] if s["unit_id"] == "U3"][0] == "item A differs between V1 and V2"
        and art["intermediate"]["rejected_statements"][0]["reason"] == "unsupported_identifiers", "a_supported_identifier_passes_and_an_unsupported_one_is_reported")
art, _ = review({"D3:1": [TWO], "I:D3": [statements(("items A and B", "finding", ["O1", "O3", "O4"]))]})
require(art["status"] == "complete" and art["intermediate_dropped_references"] == ["O1"], "a_citation_outside_the_unit_is_dropped_and_reported")
art, _ = review({"D3:1": [observations(*json.loads(TWO("", 0)[0])["observations"], {"statement": "invented", "quotes": ["no such line"]})],
                 "I:D3": [statements(("items A and B", "finding", ["R1", "O3", "O4"]))]})
require(art["status"] == "complete" and art["rejected_observation_references"] == ["R1"], "a_citation_of_a_rejected_observation_is_dropped_and_reported")
art, _ = review({"D3:1": [TWO], "I:D3": [statements(("x" * 201, "finding", ["O3"]), ("items A and B", "finding", ["O3", "O4"]))]})
require(art["status"] == "complete" and art["intermediate"]["rejected_statements"][0]["reason"] == "statement_too_long"
        and len(art["intermediate"]["rejected_statements"][0]["statement"]) == 201, "an_overlong_statement_is_rejected_not_truncated")
art, _ = review({"D3:1": [TWO], "I:D3": [lambda p, m: statements(*[(f"items A and B, view {n}", "finding", ["O3", "O4"]) for n in range(unit_cap(p) + 1)])(p, m)]})
require(art["status"] == "complete" and [r["reason"] for r in art["intermediate"]["rejected_statements"]] == ["over_statement_limit"],
        "statements_beyond_the_units_allocation_are_rejected")
art, _ = review({"D3:1": [TWO], "I:D3": [statements(("items A and B", "conclusion", ["O3", "O4"]), ("items A and B again", "finding", ["O3", "O4"]))]})
require(art["intermediate"]["rejected_statements"][0]["reason"] == "invalid_kind", "an_unknown_statement_kind_is_rejected")
truncated = lambda p, m: (cover(p, m)[0], {"seconds": 1.0, "metrics": {"eval_count": m, "prompt_eval_count": 900}})  # noqa: E731
art, _ = review({"I:D2": [truncated, truncated]})
require(art["status"] == "incomplete" and units_failed(art)["U2"]["reason"] == "truncated_at_output_limit", "a_truncated_intermediate_synthesis_fails_its_unit")
docs = {**DOCS, "notes.txt": ("notes", "Operator note: none.\n")}
art, _ = review({"I:D4": [ERROR, ERROR]}, docs=docs, optional=("notes.txt",))
require(art["status"] == "complete" and art["intermediate"]["units"][3]["status"] == "failed:provider_error" and not units_failed(art),
        "an_optional_documents_unit_failure_does_not_block_and_is_reported")

# --- final entries must be traceable and supported -----------------------------------------------------------------------------
art, _ = review(first={**FIRST, "observations": [{"statement": "the record lists forms", "int_ids": ["O1"]}],
                       "failed": [{"statement": "ST99 failed", "int_ids": ["I1"]}], "passed": [{"statement": "V1 appears in the outputs", "int_ids": ["I3"]}]})
reasons = {e["where"]: e["reason"] for e in art["final_rejected_entries"]}
require(reasons == {"observations[0]": "untraceable_no_valid_int_ids", "failed[0]": "unsupported_identifiers"} and art["unknown_references"] == ["O1"]
        and art["review"]["passed"][0]["statement"] == "V1 appears in the outputs", "final_entries_citing_observations_directly_or_unsupported_identifiers_are_rejected")
art, _ = review(second={**SECOND, "competing_hypotheses": [{"hypothesis": "no evidence given", "evidence_for": [], "evidence_against": []},
                                                            {"hypothesis": "labels move", "evidence_for": ["I3"], "evidence_against": []}],
                        "discriminating_experiments": [{"experiment": "repeat", "distinguishes": [1, 2], "int_ids": []}]})
e = art["review"]["discriminating_experiments"][0]
require([h["original_number"] for h in art["review"]["competing_hypotheses"]] == [2] and e["distinguishes"] == [1] and e["distinguishes_dropped"] == [1]
        and e["obs_ids"] == art["review"]["competing_hypotheses"][0]["obs_ids"], "experiments_are_renumbered_to_the_retained_hypotheses_and_trace_through_them")
limit = lambda p, m: (json.dumps(FIRST), {"seconds": 1.0, "metrics": {"eval_count": m, "prompt_eval_count": 900}})  # noqa: E731
art, stub = review({"first_half": [limit, limit]})
require(art["status"] == "incomplete" and art["coverage"]["missing"] == [{"kind": "final_synthesis_failed", "stage": "final:first_half", "reason": "truncated_at_output_limit"}]
        and stub.count("second_half") == 0, "a_failed_final_first_half_is_named_and_stops_the_review")
art, _ = review({"second_half": [BAD, BAD]})
require(art["status"] == "incomplete" and art["review"]["experiment_understanding"] and "competing_hypotheses" not in art["review"]
        and art["coverage"]["missing"][0]["stage"] == "final:second_half", "a_failed_final_second_half_is_named_and_leaves_the_review_incomplete")

# --- bounded compression: allocation, capacity, splitting and the final budget ---------------------------------------------------
alloc = er.statement_allocation([39, 22, 23, 16, 7, 7, 6, 6], er.final_slots())
require(sum(alloc) <= er.final_slots() and min(alloc) >= er.MIN_STATEMENTS_PER_UNIT and alloc[0] == max(alloc)
        and alloc == er.statement_allocation([39, 22, 23, 16, 7, 7, 6, 6], er.final_slots()), "the_allocation_is_proportional_bounded_and_deterministic")
maximal = lambda p, m: statements(*[(("s" * 180) + f" view {n:03d}"[:20], "finding", unit_ids(p)[:1]) for n in range(unit_cap(p))])(p, m)  # noqa: E731
art, _ = review({f"I:D{n}": [maximal] for n in (1, 2, 3)})
require(art["status"] == "complete" and art["coverage"]["levels"]["intermediate"]["final_input_chars"] <= er.FINAL_INPUT_BUDGET_CHARS
        and art["coverage"]["levels"]["intermediate"]["statements"] == er.final_slots(), "at_maximal_allocation_the_final_input_fits_its_budget_by_construction")
saved = er.FINAL_LINE_OVERHEAD_CHARS
er.FINAL_LINE_OVERHEAD_CHARS = -100
try:
    art, stub = review({f"I:D{n}": [maximal] for n in (1, 2, 3)})
finally:
    er.FINAL_LINE_OVERHEAD_CHARS = saved
require(art["status"] == "incomplete" and art["coverage"]["missing"][0]["kind"] == "final_input_exceeds_budget" and stub.count("first_half") == 0,
        "a_final_input_over_budget_fails_closed_without_discarding_statements")
saved = er.FINAL_INPUT_BUDGET_CHARS
er.FINAL_INPUT_BUDGET_CHARS = 5 * 241
try:
    art, stub = review()
finally:
    er.FINAL_INPUT_BUDGET_CHARS = saved
require(art["coverage"]["missing"][0]["kind"] == "final_capacity_insufficient" and stub.count("I:") == 0, "insufficient_final_capacity_fails_closed_before_intermediate_calls")
long_outputs = "".join(f"form=V{1 + i % 5} run=r1 item=X{i:03d} classification={'unresolved' if i % 3 else 'event_only'} seconds=1.0\n" for i in range(240))
saved = er.INTERMEDIATE_INPUT_BUDGET_CHARS
er.INTERMEDIATE_INPUT_BUDGET_CHARS = 100
try:
    art, _ = review(docs={**DOCS, "outputs.txt": ("raw_outputs", long_outputs)})
finally:
    er.INTERMEDIATE_INPUT_BUDGET_CHARS = saved
d3 = [u for u in art["intermediate"]["units"] if u["doc_id"] == "D3"]
require(art["status"] == "complete" and len(d3) == len(er.chunks(long_outputs)) and all(len(u["parts"]) == 1 for u in d3)
        and sorted(i for u in d3 for i in u["obs_ids"]) == sorted(o["obs_id"] for o in art["grounded_observations"] if o["doc_id"] == "D3"),
        "a_document_over_the_unit_budget_splits_into_units_of_whole_parts_that_cover_it")

# --- the intermediate and final prompts fit the context ----------------------------------------------------------------------------
inter_prompt = er.INTERMEDIATE_PROMPT.format(title="t" * 120, brief="b" * 500, doc_id="D9", role="raw_outputs", description="d" * 200,
                                             parts_label="parts 1, 2, 3 of 9", observations="o" * er.INTERMEDIATE_INPUT_BUDGET_CHARS,
                                             max_ids=er.MAX_IDS_PER_STATEMENT, max_statements=er.MAX_STATEMENTS_PER_UNIT,
                                             max_chars=er.MAX_INTERMEDIATE_STATEMENT_CHARS, kinds=", ".join(er.INTERMEDIATE_KINDS))
worst_reply = json.dumps({"statements": [{"statement": "s" * er.MAX_INTERMEDIATE_STATEMENT_CHARS, "kind": "unresolved_relationship",
                                          "obs_ids": [f"O{100 + i}" for i in range(er.MAX_IDS_PER_STATEMENT)]}] * er.MAX_STATEMENTS_PER_UNIT})
final_a = er.FINAL_A_PROMPT.format(title="t" * 120, brief="b" * 500, statements="s" * er.FINAL_INPUT_BUDGET_CHARS)
final_b = er.FINAL_B_PROMPT.format(title="t" * 120, brief="b" * 500, statements="s" * er.FINAL_INPUT_BUDGET_CHARS, first_half="f" * er.FIRST_HALF_SUMMARY_CHARS)
require(len(inter_prompt) / 2.4 + er.INTERMEDIATE_MAX_TOKENS <= 8192 and len(worst_reply) / 3 <= er.INTERMEDIATE_MAX_TOKENS,
        "the_largest_intermediate_prompt_and_reply_fit_the_context")
require(len(final_a) / 2.64 + er.FINAL_A_MAX_TOKENS <= 8192 and len(final_b) / 2.64 + er.FINAL_B_MAX_TOKENS <= 8192
        and len("I999 [D99, unresolved_relationship]: ") <= er.FINAL_LINE_OVERHEAD_CHARS, "the_largest_final_prompts_fit_the_context")

print(json.dumps({"suite": "v2731.3.7-omission-hierarchy", "passed": len(CHECKS), "total": len(CHECKS), "ok": True}))
