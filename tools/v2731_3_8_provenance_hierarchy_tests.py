from __future__ import annotations

"""Deterministic provenance, the observation identifier boundary, unit normalization and the three-level synthesis (spec 2.21).

Deterministic stub model; no provider contact. Proves:
- a number with a recognized unit suffix (7.3s) matches the identical number (7.3) and nothing broader: changed values,
  unit families, item, form and run identifiers, versions and unrelated suffixes stay different;
- the system reads record metadata (item, form, run, experiment) from the records a quote sits in and attaches it, so an
  observation may name it without quoting it, while an identifier established by neither quotes nor provenance is
  rejected;
- the hierarchy (observations -> part -> document -> final) cites immediate inputs with lineage to the exact quotes;
  code owns coverage, carrying every uncited input forward explicitly instead of asking the model to cite more, so an
  observation no stage summarizes still reaches the final level and is listed; nothing disappears silently;
- failed stages and budgets fail closed with the point of loss named; every prompt fits the 8,192-token context.
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
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2731-3-8-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

import experiment_review as er  # noqa: E402

CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


# --- the narrow unit rule ----------------------------------------------------------------------------------------------------
for text, evidence in (("warm-up took 7.3s", "warm_up_seconds=7.3"), ("took 7.3s", "took 7.3 seconds"), ("7.3sec", "7.3s"), ("31s", "warm-up 31"),
                       ("7.30s", "7.3"), ("7.3", "7.3s"), ("run r1 in 2019", "run=r1 year 2019")):
    require(er.unsupported_identifiers(text, evidence) == [], f"unit_supported:{text}|{evidence}")
for text, evidence, expected in (("7.4s", "7.3", ["7.4s"]), ("7.3ms", "7.3s", ["7.3ms"]), ("7.3ms", "7.3 s", ["7.3ms"]), ("7.3q", "7.3", ["7.3q"]),
                                 ("7.3st", "7.3", ["7.3st"]), ("7.3", "7.3q", ["7.3"]), ("ST18", "ST19", ["st18"]), ("V1", "V2", ["v1"]),
                                 ("r1", "r2", ["r1"]), ("G-STATE2", "G-STATE", ["state2"]), ("ss4", "ss04", ["ss4"]),
                                 ("qwen3.8:27b", "qwen3.8:26b", ["qwen3.8:27b"]), ("0.34.1", "0.34.0", ["0.34.1"])):
    require(er.unsupported_identifiers(text, evidence) == expected, f"stays_different:{text}|{evidence}")

# --- deterministic record provenance and the observation identifier boundary ------------------------------------------------------
REC = ("form=V1 run=r1 item=ST18 classification=unresolved seconds=1.0\n"
       "form=V1 run=r1 item=ST19 classification=event_only seconds=2.0\n"
       '{"item": "ST01", "group": "borderline", "gold": "unresolved"}\n'
       "experiment=G-STATE2 prompt_form_equivalent=V0 run=r2 recorded=2026-09-14T22:19:03Z item=ST40 classification=continuing\n"
       "classification=unresolved seconds=3.5 item=ST77\n")


def ground(statement, quotes, text=REC):
    grounded, rejected, _ = er.ground_observations({"observations": [{"statement": statement, "quotes": quotes}]}, text, "D5", 1, 1)
    return (grounded[0], None) if grounded else (None, rejected[0])


o, _ = ground("ST18 under V1 in run r1 is unresolved", ["classification=unresolved seconds=1.0"])
require(o and o["provenance"]["metadata"] == {"form": ["V1"], "run": ["r1"], "item": ["ST18"]} and o["provenance"]["records"][0]["line_start"] == 1
        and o["provenance"]["doc_id"] == "D5", "record_metadata_is_attached_so_the_model_need_not_quote_it")
o, r = ground("ST19 under V1 is unresolved", ["classification=unresolved seconds=1.0"])
require(o is None and r["reason"] == "unsupported_identifiers" and r["identifiers"] == ["st19"], "an_identifier_from_another_record_is_rejected")
o, _ = ground("ST01 has gold unresolved", ['"gold": "unresolved"'])
require(o and o["provenance"]["metadata"] == {"item": ["ST01"]}, "json_record_metadata_is_read_too")
o, _ = ground("G-STATE2 run r2 classifies ST40 as continuing under form V0", ["item=ST40 classification=continuing"])
require(o and o["provenance"]["metadata"] == {"experiment": ["G-STATE2"], "prompt_form_equivalent": ["V0"], "run": ["r2"], "item": ["ST40"]},
        "experiment_form_and_run_metadata_are_read_and_recorded_is_not_mistaken_for_record")
o, _ = ground("D5 lists ST18 as unresolved", ["classification=unresolved seconds=1.0"])
require(o is not None, "the_document_id_is_provenance")
o, _ = ground("ST18 is unresolved and ST19 is event_only", ["classification=unresolved seconds=1.0", "classification=event_only seconds=2.0"])
require(o and o["provenance"]["metadata"]["item"] == ["ST18", "ST19"], "a_comparison_draws_metadata_from_each_quoted_record")
o, _ = ground("ST77 is unresolved", ["classification=unresolved seconds=3.5 ..."])
o2, r2 = ground("ST77 is unresolved and has item", ["classification=unresolved seconds=3.5 ..."])
require(o and o["quotes"][0]["omission"] and o2 is None and r2["reason"] == "omission_hides_attributed_content" and r2["hidden_terms"] == ["item"],
        "metadata_values_in_an_omitted_suffix_are_provenance_but_other_omitted_words_stay_hidden")
o, r = ground("ST18 took 1.0s", ["form=V1 run=r1 item=ST18 classification=unresolved seconds=1.0"])
require(o is not None, "a_unit_suffix_matches_the_quoted_number_at_the_observation_level")

# --- the review, with a conforming stub ---------------------------------------------------------------------------------------
OUTPUTS = ("form=V1 item=A classification=unresolved\nform=V1 item=B classification=continuing\n"
           "form=V2 item=A classification=event_only\nform=V2 item=B classification=continuing\n")
DOCS = {"design.txt": ("design", "The experiment asks whether each item keeps its label across prompt forms.\nForms: V1, V2.\n"),
        "items.txt": ("corpus", "item=A gold=unresolved\nitem=B gold=continuing\n"),
        "outputs.txt": ("raw_outputs", OUTPUTS)}
OK_META = {"seconds": 0.0, "metrics": {"eval_count": 50, "prompt_eval_count": 900}}
FIRST = {"experiment_understanding": {"statement": "It checks label stability.", "input_ids": ["DS1"]},
         "observations": [{"statement": "the record lists forms", "input_ids": ["DS1", "DS3"]}], "passed": [], "failed": [], "failure_clusters": [],
         "possible_harness_or_measurement_failures": [], "possible_model_or_reasoning_failures": [], "ambiguous_cases": []}
SECOND = {"competing_hypotheses": [{"hypothesis": "labels move near a boundary", "evidence_for": ["DS3"], "evidence_against": ["DS2"]}],
          "unknowns": [{"statement": "why", "input_ids": ["DS3"]}], "confidence": {"level": "low", "reason": "small", "input_ids": ["DS1"]},
          "discriminating_experiments": [{"experiment": "repeat", "distinguishes": [1], "input_ids": ["DS3"]}],
          "not_established": [{"statement": "a cause", "input_ids": ["DS2"]}]}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_package(base: Path, *, docs: dict = DOCS) -> Path:
    pkg = base / "pkg"
    pkg.mkdir(parents=True, exist_ok=True)
    entries = []
    for n, (name, (role, text)) in enumerate(docs.items(), 1):
        (pkg / name).write_text(text, encoding="utf-8", newline="\n")
        entries.append({"doc_id": f"D{n}", "path": name, "role": role, "description": name, "sha256": sha(pkg / name)})
    (pkg / er.MANIFEST_NAME).write_text(json.dumps({"experiment_id": "TEST", "title": "Test experiment", "task": "independent_review",
                                                    "brief": "Review it.", "documents": entries}), encoding="utf-8")
    return pkg


def good(prompt, m):
    line = prompt.split("---\n", 1)[1].rsplit("\n---\n", 1)[0].strip().splitlines()[0]
    return json.dumps({"observations": [{"statement": f"the part contains {line}", "quotes": [line]}], "open_questions": []}), dict(OK_META)


def listed(prompt):
    part = "Write a part-level synthesis" in prompt
    return re.findall(r"^(O[0-9]+)(?: \[[^\]]*\])?: " if part else r"^((?:PS|O)[0-9]+) \[", prompt, re.M), ("obs_ids" if part else "input_ids")


def cap(prompt):
    return int(re.search(r"Give at most ([0-9]+) statements", prompt).group(1))


def cover(prompt, m):
    ids, key = listed(prompt)
    groups = [ids[i:i + er.MAX_IDS_PER_STATEMENT] for i in range(0, len(ids), er.MAX_IDS_PER_STATEMENT)][:cap(prompt)]
    return json.dumps({"statements": [{"statement": "these inputs are recorded", "kind": "finding", key: g} for g in groups]}), dict(OK_META)


def statements(*rows):
    def reply(prompt, m):
        key = listed(prompt)[1]
        return json.dumps({"statements": [{"statement": s, "kind": k, key: ids} for s, k, ids in rows]}), dict(OK_META)
    return reply


def observations(*items):
    return lambda p, m: (json.dumps({"observations": list(items), "open_questions": []}), dict(OK_META))


BAD = lambda p, m: ("{not json", dict(OK_META))  # noqa: E731


def stage_key(prompt):
    doc = re.search(r"document (D[0-9]+) [(]", prompt)
    if "List up to" in prompt:
        return f"{doc.group(1)}:{re.search(r'[)], part ([0-9]+) of', prompt).group(1)}"
    if "Write a part-level synthesis" in prompt:
        return f"P:{doc.group(1)}:{re.search(r'[)], part ([0-9]+) of', prompt).group(1)}"
    if "Write a document-level synthesis" in prompt:
        return f"D:{doc.group(1)}"
    return "first_half" if "first half" in prompt and "second half" not in prompt else "second_half"


class Stub:
    def __init__(self, script=None, *, first=FIRST, second=SECOND):
        self.script = {k: list(v) for k, v in (script or {}).items()}
        self.first, self.second = first, second
        self.prompts: list[tuple[str, str]] = []

    def __call__(self, prompt, max_tokens):
        key = stage_key(prompt)
        default = {"first_half": lambda p, m: (json.dumps(self.first), dict(OK_META)),
                   "second_half": lambda p, m: (json.dumps(self.second), dict(OK_META))}.get(key, good if re.fullmatch(r"D[0-9]+:[0-9]+", key) else cover)
        self.prompts.append((key, prompt))
        queue = self.script.get(key)
        return (queue.pop(0) if queue else default)(prompt, max_tokens)

    def count(self, prefix):
        return sum(k.startswith(prefix) for k, _ in self.prompts)

    def of(self, key):
        return [p for k, p in self.prompts if k == key]


IDENT = {"model": "stub", "provider": "stub", "context_size": 8192, "resolved_config_sha256": "0" * 64}
base = Path(tempfile.mkdtemp(prefix="eidolon-v2731-3-8-case-"))
counter = iter(range(10_000))


def review(script=None, *, docs=DOCS, first=FIRST, second=SECOND):
    stub = Stub(script, first=first, second=second)
    return er.review_experiment(make_package(base / f"case{next(counter)}", docs=docs), call_model=stub, identity=IDENT), stub


def lineage(art, ids):
    registry = {o["obs_id"]: [o["obs_id"]] for o in art["grounded_observations"]}
    registry.update({s["id"]: s["lineage"] for s in art["hierarchy"]["part_statements"] + art["hierarchy"]["document_statements"]})
    return {o for i in ids for o in registry[i]}


# --- a clean three-level review ----------------------------------------------------------------------------------------------------
art, stub = review()
h, lv = art["hierarchy"], art["coverage"]["levels"]
require(art["status"] == "complete" and len(h["part_units"]) == 3 and len(h["document_units"]) == 3 and lv["architecture"]["coverage"] == 1.0
        and lv["architecture"]["silently_dropped"] == [] and h["final_inputs"] == [s["id"] for s in h["document_statements"]],
        "a_clean_review_runs_part_document_and_final_levels")
units = {u["unit_id"]: u for u in h["part_units"] + h["document_units"]}
require(all(set(s["cites"]) <= set(units[s["unit_id"]]["inputs"]) for s in h["part_statements"] + h["document_statements"])
        and all(set(s["lineage"]) == lineage(art, s["cites"]) for s in h["part_statements"] + h["document_statements"]),
        "every_statement_cites_its_units_immediate_inputs_with_lineage")
entries = [art["review"]["experiment_understanding"], *[e for k in er.SECTIONS_A[1:] for e in art["review"][k]], *art["review"]["unknowns"],
           art["review"]["confidence"], *art["review"]["not_established"]]
require(all(e["input_ids"] and set(e["obs_ids"]) == lineage(art, e["input_ids"]) for e in entries), "every_final_entry_traces_to_original_observations")

# --- code owns coverage: uncited inputs are carried forward, never re-asked for, never lost -----------------------------------------
TWO = observations({"statement": "item B is continuing under both forms", "quotes": ["form=V1 item=B classification=continuing", "form=V2 item=B classification=continuing"]},
                   {"statement": "item A differs between the forms", "quotes": ["form=V1 item=A classification=unresolved", "form=V2 item=A classification=event_only"]})
majority = statements(("item B is continuing under both forms", "finding", ["O3"]))
art, stub = review({"D3:1": [TWO], "P:D3:1": [majority]})
h = art["hierarchy"]
require(art["status"] == "complete" and h["carried_to_document_level"] == ["O4"] and sum(x["stage"] == "part:PU3" for x in art["ledger"]) == 1
        and "O4 [part 1, uncaptured observation; form=V1/V2 item=A]: item A differs between the forms" in stub.of("D:D3")[0],
        "an_observation_a_part_synthesis_leaves_uncited_is_carried_forward_without_asking_again")
art, stub = review({"D3:1": [TWO], "P:D3:1": [majority], "D:D3": [statements(("item B is continuing under both forms", "finding", ["PS3"]))]})
h, lv = art["hierarchy"], art["coverage"]["levels"]
md = (RUNTIME / er.REVIEW_AREA / art["review_id"] / "review.md").read_text(encoding="utf-8")
require(art["status"] == "complete" and h["carried_to_final"] == ["O4"] and "O4" in h["final_inputs"] and "O4" in h["final_inputs_not_cited"]
        and all("O4 [D3 part 1, uncaptured observation" in p for p in stub.of("first_half") + stub.of("second_half"))
        and lv["architecture"]["silently_dropped"] == [] and "## Evidence the final synthesis did not cite" in md and "- O4: item A differs" in md,
        "a_contradicting_observation_no_stage_summarizes_reaches_the_final_level_and_is_listed")
THREE = observations(*json.loads(TWO("", 0)[0])["observations"], {"statement": "form V2 lists item B", "quotes": ["form=V2 item=B classification=continuing"]})
art, _ = review({"D3:1": [THREE], "P:D3:1": [statements(("ST99 differs between the forms", "contradiction", ["O4"]),
                                                        ("item B is continuing under both forms", "finding", ["O3", "O5"]))]})
require(art["status"] == "complete" and art["hierarchy"]["part_units"][2]["max_statements"] == 2
        and (art["hierarchy"]["rejected_statements"] or [{}])[0].get("identifiers") == ["st99"] and art["hierarchy"]["carried_to_document_level"] == ["O4"],
        "a_statement_with_an_unsupported_identifier_is_rejected_and_its_inputs_carried")
art, _ = review({"D3:1": [THREE], "P:D3:1": [statements(("x" * 201, "finding", ["O4"]), ("item B", "finding", ["O3", "O5"]))]})
require((art["hierarchy"]["rejected_statements"] or [{}])[0].get("reason") == "statement_too_long"
        and len((art["hierarchy"]["rejected_statements"] or [{"statement": ""}])[0]["statement"]) == 201
        and art["hierarchy"]["carried_to_document_level"] == ["O4"], "an_overlong_statement_is_rejected_not_truncated")
art, _ = review({"D3:1": [TWO], "P:D3:1": [lambda p, m: statements(*[(f"view {n}", "finding", ["O3", "O4"]) for n in range(cap(p) + 1)])(p, m)]})
require([r["reason"] for r in art["hierarchy"]["rejected_statements"]] == ["over_statement_limit"], "statements_beyond_the_units_cap_are_rejected")
art, _ = review({"D3:1": [TWO], "P:D3:1": [statements(("items A and B", "conclusion", ["O3", "O4"]))]})
require(art["hierarchy"]["rejected_statements"][0]["reason"] == "invalid_kind" and art["hierarchy"]["carried_to_document_level"] == ["O3", "O4"],
        "an_unknown_kind_is_rejected_and_everything_is_carried")

# --- provenance support through the levels ---------------------------------------------------------------------------------------
meta_only = observations({"statement": "item A under V1 is unresolved", "quotes": ["classification=unresolved"]})
art, _ = review({"D3:1": [meta_only], "D:D3": [statements(("V1 gives item A unresolved", "finding", ["PS3"]))]},
                first={**FIRST, "failed": [{"statement": "V1 leaves item A unresolved", "input_ids": ["DS3"]}],
                       "passed": [{"statement": "ST99 passed", "input_ids": ["DS3"]}]})
require(art["status"] == "complete" and art["grounded_observations"][2]["provenance"]["metadata"] == {"form": ["V1"], "item": ["A"]}
        and art["review"]["failed"][0]["statement"] == "V1 leaves item A unresolved"
        and [e["reason"] for e in art["final_rejected_entries"]] == ["unsupported_identifiers"], "record_metadata_supports_identifiers_at_every_level")

# --- stage failures, retries and the final level ------------------------------------------------------------------------------------
art, stub = review({"P:D2:1": [BAD, BAD]})
require(art["status"] == "incomplete" and art["coverage"]["missing"][0]["kind"] == "synthesis_stage_failed" and art["coverage"]["missing"][0]["level"] == "part"
        and stub.count("D:") == 0 and stub.count("first_half") == 0, "a_failed_part_synthesis_is_named_and_stops_later_levels")
art, _ = review({"P:D2:1": [BAD]})
require(art["status"] == "complete" and art["runtime_accounting"]["recovered_stages"] == ["part:PU2"], "the_repair_retry_covers_parse_failures_only")
art, stub = review({"D:D3": [BAD, BAD]})
require(art["status"] == "incomplete" and art["coverage"]["missing"][0]["level"] == "document" and stub.count("first_half") == 0,
        "a_failed_document_synthesis_is_named_and_stops_the_final_level")
art, _ = review({"D3:1": [TWO], "P:D3:1": [majority], "D:D3": [statements(("item B is continuing under both forms", "finding", ["PS3"]))]},
                first={**FIRST, "observations": [{"statement": "item A differs between the forms", "input_ids": ["O4"]}],
                       "failed": [{"statement": "no citation"}, {"statement": "unknown", "input_ids": ["DS42"]}]})
reasons = {e["where"]: e["reason"] for e in art["final_rejected_entries"]}
require(art["review"]["observations"][0]["obs_ids"] == ["O4"] and reasons == {"failed[0]": "untraceable_no_valid_input_ids", "failed[1]": "untraceable_no_valid_input_ids"}
        and art["unknown_references"] == ["DS42"], "the_final_level_may_cite_a_carried_observation_and_rejects_untraceable_entries")
art, _ = review(second={**SECOND, "competing_hypotheses": [{"hypothesis": "no evidence", "evidence_for": [], "evidence_against": []},
                                                            {"hypothesis": "labels move", "evidence_for": ["DS3"], "evidence_against": []}],
                        "discriminating_experiments": [{"experiment": "repeat", "distinguishes": [1, 2], "input_ids": []}]})
e = art["review"]["discriminating_experiments"][0]
require(e["distinguishes"] == [1] and e["distinguishes_dropped"] == [1] and e["obs_ids"] == art["review"]["competing_hypotheses"][0]["obs_ids"],
        "experiments_are_renumbered_to_the_retained_hypotheses")
limit = lambda p, m: (json.dumps(FIRST), {"seconds": 1.0, "metrics": {"eval_count": m, "prompt_eval_count": 900}})  # noqa: E731
art, stub = review({"first_half": [limit, limit]})
require(art["status"] == "incomplete" and art["coverage"]["missing"] == [{"kind": "final_synthesis_failed", "stage": "final:first_half", "reason": "truncated_at_output_limit"}]
        and stub.count("second_half") == 0, "a_truncated_final_first_half_is_named")

# --- bounds: allocation, capacity, the final budget and grouping --------------------------------------------------------------------
require(er.allocate([2, 3], 10) == [2, 3] and sum(er.allocate([10, 10, 1], 6)) <= 6 and min(er.allocate([10, 10, 1], 6)) >= 1
        and all(a <= w for a, w in zip(er.allocate([10, 10, 1], 6), [10, 10, 1])) and er.allocate([10, 10, 1], 6) == er.allocate([10, 10, 1], 6),
        "allocation_keeps_wants_when_they_fit_and_scales_deterministically_when_not")
saved = er.FINAL_DOCUMENT_STATEMENT_BUDGET_CHARS
er.FINAL_DOCUMENT_STATEMENT_BUDGET_CHARS = 2 * 241
try:
    art, stub = review()
finally:
    er.FINAL_DOCUMENT_STATEMENT_BUDGET_CHARS = saved
require(art["coverage"]["missing"][0]["kind"] == "final_capacity_insufficient" and stub.count("D:") == 0, "insufficient_capacity_fails_closed_before_document_calls")
saved = er.FINAL_INPUT_BUDGET_CHARS
er.FINAL_INPUT_BUDGET_CHARS = 50
try:
    art, stub = review({"D3:1": [TWO], "P:D3:1": [majority], "D:D3": [statements(("item B", "finding", ["PS3"]))]})
finally:
    er.FINAL_INPUT_BUDGET_CHARS = saved
require(art["status"] == "incomplete" and art["coverage"]["missing"][0]["kind"] == "final_input_exceeds_budget"
        and art["hierarchy"]["carried_to_final"] == ["O4"] and stub.count("first_half") == 0, "a_final_input_over_budget_fails_closed_without_discarding")
long_outputs = "".join(f"form=V{1 + i % 5} run=r1 item=X{i:03d} classification={'unresolved' if i % 3 else 'event_only'} seconds=1.0\n" for i in range(240))
saved = er.DOCUMENT_UNIT_MAX_INPUTS
er.DOCUMENT_UNIT_MAX_INPUTS = 1
try:
    art, _ = review(docs={**DOCS, "outputs.txt": ("raw_outputs", long_outputs)})
finally:
    er.DOCUMENT_UNIT_MAX_INPUTS = saved
d3 = [u for u in art["hierarchy"]["document_units"] if u["doc_id"] == "D3"]
require(art["status"] == "complete" and len(d3) == len(er.chunks(long_outputs)) and all(len(u["parts"]) == 1 for u in d3),
        "a_document_is_grouped_into_units_of_whole_parts_within_the_input_bounds")

# --- every prompt fits the context ------------------------------------------------------------------------------------------------
line = "O99 [form=V1/V2 run=r1/r2 item=ST18/ST19]: " + "s" * er.MAX_OBSERVATION_CHARS
part_prompt = er.PART_PROMPT.format(title="t" * 120, brief="b" * 500, doc_id="D9", role="raw_outputs", description="d" * 200, part=9, parts=9,
                                    inputs="\n".join([line] * er.MAX_OBSERVATIONS_PER_CHUNK), max_ids=er.MAX_IDS_PER_STATEMENT, max_statements=4,
                                    max_chars=er.MAX_STATEMENT_CHARS, kinds=", ".join(er.SYNTHESIS_KINDS))
doc_prompt = er.DOCUMENT_PROMPT.format(title="t" * 120, brief="b" * 500, doc_id="D9", role="raw_outputs", description="d" * 200,
                                       parts_label="parts 1, 2, 3 of 9", inputs="i" * er.DOCUMENT_UNIT_INPUT_BUDGET_CHARS, max_ids=er.MAX_IDS_PER_STATEMENT,
                                       max_statements=6, max_chars=er.MAX_STATEMENT_CHARS, kinds=", ".join(er.SYNTHESIS_KINDS))
reply = lambda n: json.dumps({"statements": [{"statement": "s" * er.MAX_STATEMENT_CHARS, "kind": "unresolved_relationship",  # noqa: E731
                                              "input_ids": [f"PS{100 + i}" for i in range(er.MAX_IDS_PER_STATEMENT)]}] * n})
final_a = er.FINAL_A_PROMPT.format(title="t" * 120, brief="b" * 500, inputs="s" * er.FINAL_INPUT_BUDGET_CHARS)
final_b = er.FINAL_B_PROMPT.format(title="t" * 120, brief="b" * 500, inputs="s" * er.FINAL_INPUT_BUDGET_CHARS, first_half="f" * er.FIRST_HALF_SUMMARY_CHARS)
require(len(part_prompt) / 2.4 + er.PART_MAX_TOKENS <= 8192 and len(reply(4)) / 3 <= er.PART_MAX_TOKENS, "the_part_prompt_and_reply_fit")
require(len(doc_prompt) / 2.4 + er.DOCUMENT_MAX_TOKENS <= 8192 and len(reply(6)) / 3 <= er.DOCUMENT_MAX_TOKENS
        and er.DOCUMENT_UNIT_MAX_INPUTS // 2 == 6, "the_document_prompt_and_reply_fit")
require(len(final_a) / er.CALIBRATED_CHARS_PER_TOKEN + er.FINAL_A_MAX_TOKENS <= 8192
        and len(final_b) / er.CALIBRATED_CHARS_PER_TOKEN + er.FINAL_B_MAX_TOKENS <= 8192
        and len("DS99 [D99, unresolved_relationship]: ") <= er.FINAL_LINE_OVERHEAD_CHARS
        and er.document_statement_slots() * (er.MAX_STATEMENT_CHARS + er.FINAL_LINE_OVERHEAD_CHARS + 1) <= er.FINAL_DOCUMENT_STATEMENT_BUDGET_CHARS,
        "the_final_prompts_fit_at_the_calibrated_ratio_and_document_statements_fit_their_budget")

# --- omission is a general rule: it grounds in a design document as in raw outputs ------------------------------------------------
art, _ = review({"D1:1": [observations({"statement": "the design states what the experiment asks", "quotes": ["The experiment asks whether each item keeps ..."]})]})
require(art["status"] == "complete" and art["grounded_observations"][0]["quotes"][0]["omission"]["omitted_suffix"] == " its label across prompt forms."
        and art["integrity_metrics"]["omission_quotes"] == 1, "suffix_omission_applies_to_any_document_role")

print(json.dumps({"suite": "v2731.3.8-provenance-hierarchy", "passed": len(CHECKS), "total": len(CHECKS), "ok": True}))
