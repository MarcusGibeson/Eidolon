from __future__ import annotations

"""Coverage, truncation and grounding repairs to review_experiment (spec 2.19), kept under the hierarchical synthesis of 2.20.

Deterministic stub model; no provider contact. The adversarial cases come from the audit of the first G-INVAR review:
a reply truncated exactly at the output-token limit, a required part that is never reviewed, repair retries that
succeed and fail, a comparison across records grounded by several separate exact quotes, stitched quotes, later stages
that could otherwise run or claim completeness over partial coverage, citations of rejected observations, and a
package missing a required design or corpus document. Also proves that the observation limits are finite and fit the
context, that the observation prompt is byte-identical to Review 2's, and that earlier reviews stay protected.
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
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2731-3-6-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

import experiment_review as er  # noqa: E402
from cognitive_coding_foundations import digest  # noqa: E402

CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


OUTPUTS = ("form=V1 item=A classification=unresolved\nform=V1 item=B classification=continuing\n"
           "form=V2 item=A classification=event_only\nform=V2 item=B classification=continuing\n")
DOCS = {"design.txt": ("design", "The experiment asks whether each item keeps its label across prompt forms.\nForms: V1, V2.\n"),
        "items.txt": ("corpus", "item=A gold=unresolved\nitem=B gold=continuing\n"),
        "outputs.txt": ("raw_outputs", OUTPUTS)}


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
    manifest = {"experiment_id": "TEST", "title": "Test experiment", "task": "independent_review", "brief": "Review it.", "documents": entries}
    (pkg / er.MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
    return pkg


FIRST = {"experiment_understanding": {"statement": "It checks label stability.", "int_ids": ["I1"]},
         "observations": [{"statement": "the record lists forms", "int_ids": ["I1"]}], "passed": [], "failed": [], "failure_clusters": [],
         "possible_harness_or_measurement_failures": [], "possible_model_or_reasoning_failures": [], "ambiguous_cases": []}
SECOND = {"competing_hypotheses": [{"hypothesis": "labels move near a boundary", "evidence_for": ["I1"], "evidence_against": []}],
          "unknowns": [{"statement": "why", "int_ids": ["I1"]}], "confidence": {"level": "low", "reason": "small", "int_ids": ["I1"]},
          "discriminating_experiments": [{"experiment": "repeat", "distinguishes": [1], "int_ids": ["I1"]}],
          "not_established": [{"statement": "a cause", "int_ids": ["I1"]}]}
OK_META = {"seconds": 0.0, "metrics": {"eval_count": 50, "prompt_eval_count": 900}}


def chunk_of(prompt: str) -> str:
    return prompt.split("---\n", 1)[1].rsplit("\n---\n", 1)[0]


def good(prompt: str, max_tokens: int):
    line = chunk_of(prompt).strip().splitlines()[0]
    return json.dumps({"observations": [{"statement": f"the part contains {line}", "quotes": [line]}], "open_questions": []}), dict(OK_META)


def cover(prompt: str, max_tokens: int):
    """A conforming intermediate synthesis: every listed observation cited."""
    ids = re.findall(r"^(O[0-9]+) [(]part [0-9]+[)]: ", prompt, re.M)
    cap = int(re.search(r"Give at most ([0-9]+) statements", prompt).group(1))
    groups = [ids[i:i + er.MAX_IDS_PER_STATEMENT] for i in range(0, len(ids), er.MAX_IDS_PER_STATEMENT)][:cap]
    return json.dumps({"statements": [{"statement": "the unit records these observations", "kind": "finding", "obs_ids": g} for g in groups]}), dict(OK_META)


def reply(observations, meta=None):
    return lambda p, m: (json.dumps({"observations": observations, "open_questions": []}), dict(meta or OK_META))


TRUNCATED = lambda p, m: ('{"observations": [{"statement": "the part lists forms", "quotes": ["form=V1 item=A',  # noqa: E731
                          {"seconds": 1.0, "metrics": {"eval_count": m, "prompt_eval_count": 900}})
VALID_AT_LIMIT = lambda p, m: (good(p, m)[0], {"seconds": 1.0, "metrics": {"eval_count": m, "prompt_eval_count": 900}})  # noqa: E731
BAD = lambda p, m: ("{not json", dict(OK_META))  # noqa: E731
ERROR = lambda p, m: ("", {"seconds": 1.0, "error": "LocalModelHTTPError: connection refused"})  # noqa: E731
TIMEOUT = lambda p, m: ("", {"seconds": 1.0, "error": "LocalModelTimeoutError: Local model request timed out"})  # noqa: E731


class Stub:
    """Scripted replies per stage ("D2:1", "I:D2", "first_half", "second_half"), one entry per attempt; otherwise conforming."""

    def __init__(self, script=None, *, first=FIRST, second=SECOND, hook=None):
        self.script = {k: list(v) for k, v in (script or {}).items()}
        self.first, self.second, self.hook = first, second, hook
        self.prompts: list[str] = []
        self.calls: list[tuple[str, int]] = []

    def __call__(self, prompt: str, max_tokens: int):
        self.prompts.append(prompt)
        if self.hook:
            self.hook(prompt)
        if "List up to" in prompt:
            key = f"{re.search(r'document (D[0-9]+) [(]', prompt).group(1)}:{re.search(r'[)], part ([0-9]+) of', prompt).group(1)}"
            default = good
        elif "Write a bounded synthesis" in prompt:
            key, default = "I:" + re.search(r"document (D[0-9]+) [(]", prompt).group(1), cover
        elif "first half" in prompt and "second half" not in prompt:
            key, default = "first_half", (lambda p, m: (json.dumps(self.first), dict(OK_META)))
        else:
            key, default = "second_half", (lambda p, m: (json.dumps(self.second), dict(OK_META)))
        self.calls.append((key, max_tokens))
        queue = self.script.get(key)
        return (queue.pop(0) if queue else default)(prompt, max_tokens)

    def later_calls(self) -> int:
        return sum(not re.fullmatch(r"D[0-9]+:[0-9]+", k) for k, _ in self.calls)


IDENT = {"model": "stub", "provider": "stub", "context_size": 8192, "resolved_config_sha256": "0" * 64}
base = Path(tempfile.mkdtemp(prefix="eidolon-v2731-3-6-case-"))
counter = iter(range(10_000))


def review(script=None, *, docs=DOCS, optional=(), **kwargs):
    stub = kwargs.pop("stub", None) or Stub(script, **{k: kwargs.pop(k) for k in ("first", "second", "hook") if k in kwargs})
    art = er.review_experiment(make_package(base / f"case{next(counter)}", docs=docs, optional=optional), call_model=stub, identity=IDENT, **kwargs)
    return art, stub


def missing_stages(art) -> dict[str, str]:
    return {m["stage"]: m["reason"] for m in art["coverage"]["missing"] if m["kind"] == "required_part_not_reviewed"}


# --- observation limits are finite and fit the context; the observation prompt is unchanged since Review 2 --------------------
require(isinstance(er.OBSERVE_MAX_TOKENS, int) and 700 < er.OBSERVE_MAX_TOKENS < 8192, "the_observation_limit_is_raised_and_finite")
maximal = json.dumps({"observations": [{"statement": "s" * er.MAX_OBSERVATION_CHARS, "quotes": ["q" * er.MAX_QUOTE_CHARS] * er.MAX_QUOTES_PER_OBSERVATION}]
                      * er.MAX_OBSERVATIONS_PER_CHUNK, "open_questions": ["x" * 300] * er.MAX_QUESTIONS_PER_CHUNK})
require(len(maximal) / 3 <= er.OBSERVE_MAX_TOKENS, "a_maximal_schema_conforming_reply_fits_the_limit_at_3_chars_per_token")
largest = er.OBSERVE_PROMPT.format(title="t" * 120, brief="b" * 500, doc_id="D9", role="raw_outputs", description="d" * 200, part=9, parts=9,
                                   chunk="c" * er.CHUNK_CHARS, max_obs=er.MAX_OBSERVATIONS_PER_CHUNK, max_quotes=er.MAX_QUOTES_PER_OBSERVATION,
                                   max_quote=er.MAX_QUOTE_CHARS)
require(len(largest) / 2.4 + er.OBSERVE_MAX_TOKENS <= 8192, "the_largest_observation_prompt_plus_the_limit_fits_the_8192_token_context")
require(digest(er.OBSERVE_PROMPT) == "e8a061eece3d022cdbe6fbe17a837ed2ff8e595cbc16cfa362d031e1f00333dd"
        and all(t.startswith(er.FRAME) for t in (er.OBSERVE_PROMPT, er.INTERMEDIATE_PROMPT, er.FINAL_A_PROMPT, er.FINAL_B_PROMPT)),
        "the_observation_prompt_is_byte_identical_to_review_2_and_every_template_keeps_the_frame")

# --- a clean review: full coverage at every level --------------------------------------------------------------------------------
art, stub = review()
c, lv = art["coverage"], art["coverage"]["levels"]
require(art["status"] == "complete" and c["complete"] and c["required_coverage"] == 1.0 and c["reviewed_required_parts"] == c["required_parts"] == 3
        and c["missing"] == [] and lv["observations"]["coverage"] == 1.0 and lv["intermediate"]["coverage"] == 1.0
        and lv["final"]["first_half"] == lv["final"]["second_half"] == "accepted", "a_clean_review_reports_full_coverage_at_every_level")
require(all(m == er.OBSERVE_MAX_TOKENS for k, m in stub.calls if re.fullmatch(r"D[0-9]+:[0-9]+", k)), "observation_calls_use_the_raised_limit")
require(art["provenance"]["capability"]["module_sha256"] == sha(AGENT / "experiment_review.py")
        and art["provenance"]["limits"]["observe_max_tokens"] == er.OBSERVE_MAX_TOKENS, "provenance_records_the_capability_digest_and_limits")
md = (RUNTIME / er.REVIEW_AREA / art["review_id"] / "review.md").read_text(encoding="utf-8")
require("Required coverage: 3 of 3 package parts reviewed (100%)" in md and "INCOMPLETE" not in md, "the_markdown_leads_with_coverage")

# --- truncation exactly at the output-token limit ------------------------------------------------------------------------------
art, stub = review({"D3:1": [TRUNCATED, TRUNCATED]})
require(art["status"] == "incomplete" and missing_stages(art) == {"observe:D3:1": "truncated_at_output_limit"}, "truncation_at_the_limit_fails_the_part_closed")
require(art["runtime_accounting"]["truncated_attempts"] == 2 and art["runtime_accounting"]["rejections_by_reason"] == {"truncated_at_output_limit": 2}
        and art["runtime_accounting"]["terminal_stage_failures"] == [{"stage": "observe:D3:1", "reason": "truncated_at_output_limit"}],
        "truncated_attempts_are_counted_and_named")
art, _ = review({"D3:1": [VALID_AT_LIMIT, VALID_AT_LIMIT]})
require(missing_stages(art) == {"observe:D3:1": "truncated_at_output_limit"} and art["status"] == "incomplete",
        "a_reply_that_parses_but_reaches_the_limit_is_still_rejected")
art, _ = review({"D2:1": [lambda p, m: (good(p, m)[0], {"seconds": 1.0, "metrics": {"eval_count": 300, "prompt_eval_count": 7880}})] * 2})
require(missing_stages(art) == {"observe:D2:1": "context_limit_reached"}, "a_reply_that_reaches_the_context_limit_is_rejected")

# --- a required observation stage permanently missing ---------------------------------------------------------------------------
art, stub = review({"D1:1": [ERROR, ERROR]})
require(art["status"] == "incomplete" and not art["coverage"]["complete"] and art["coverage"]["required_coverage"] == round(2 / 3, 4)
        and missing_stages(art) == {"observe:D1:1": "provider_error"} and art["coverage"]["missing"][0]["doc_id"] == "D1"
        and art["coverage"]["missing"][0]["part"] == 1, "a_permanently_missing_required_part_is_identified_with_its_reason")
require(stub.later_calls() == 0 and art["review"] == {} and art["intermediate"]["units"] == [],
        "no_intermediate_or_final_synthesis_is_requested_over_incomplete_coverage")
art, _ = review({"D2:1": [TIMEOUT, TIMEOUT]})
require(missing_stages(art) == {"observe:D2:1": "timeout"} and art["runtime_accounting"]["timeout_attempts"] == 2, "a_timed_out_part_is_named_as_a_timeout")

# --- repair retries -------------------------------------------------------------------------------------------------------------
art, _ = review({"D2:1": [BAD]})
require(art["status"] == "complete" and art["runtime_accounting"]["retries"] == 1 and art["runtime_accounting"]["recovered_stages"] == ["observe:D2:1"]
        and art["ledger"][1]["rejection"] == "unparseable_json" and art["ledger"][2]["accepted"], "a_repair_retry_that_succeeds_recovers_the_part")
art, _ = review({"D3:1": [TRUNCATED]})
require(art["status"] == "complete" and art["runtime_accounting"]["recovered_stages"] == ["observe:D3:1"], "a_truncated_first_attempt_can_be_recovered_by_the_retry")
art, _ = review({"D2:1": [BAD, BAD]})
require(art["status"] == "incomplete" and missing_stages(art) == {"observe:D2:1": "unparseable_json"}
        and sum(x["stage"] == "observe:D2:1" for x in art["ledger"]) == 2, "a_repair_retry_that_fails_leaves_the_part_missing")
art, _ = review({"D2:1": [lambda p, m: ('{"notes": []}', dict(OK_META))] * 2})
require(missing_stages(art) == {"observe:D2:1": "schema_rejected"}, "a_reply_in_the_wrong_shape_is_named_schema_rejected")

# --- several separately grounded exact quotes, with their own provenance ---------------------------------------------------------
compare = {"statement": "item A is unresolved under V1 and event_only under V2",
           "quotes": ["form=V1 item=A classification=unresolved", "form=V2 item=A classification=event_only"]}
art, _ = review({"D3:1": [reply([compare])]})
o = art["grounded_observations"][2]
require(art["status"] == "complete" and o["statement"].startswith("item A") and len(o["quotes"]) == 2
        and [q["line_start"] for q in o["quotes"]] == [1, 3] and all(q["doc_id"] == "D3" and q["part"] == 1 and q["found"] for q in o["quotes"])
        and all(" ".join(OUTPUTS[q["char_start"]:q["char_end"]].split()) == q["text"] and q["omission"] is None for q in o["quotes"])
        and o["quotes"][1]["record_head"].startswith("form=V2 item=A"), "a_multi_record_comparison_grounds_each_quote_separately_with_provenance")
long_outputs = "".join(f"form=V{1 + i % 5} run=r1 item=X{i:03d} classification={'unresolved' if i % 3 else 'event_only'} seconds=1.0\n" for i in range(240))
docs = {**DOCS, "outputs.txt": ("raw_outputs", long_outputs)}
parts = er.chunks(long_outputs)
second_part_lines = parts[1].splitlines()
q1, q2 = second_part_lines[2].split(" seconds")[0], second_part_lines[7].split(" seconds")[0]
art, _ = review({"D3:2": [reply([{"statement": "two records in part 2", "quotes": [q1, q2]}])]}, docs=docs)
o = next(x for x in art["grounded_observations"] if x["part"] == 2 and x["statement"] == "two records in part 2")
first_line_of_part2 = long_outputs[:len(parts[0])].count("\n") + 1
require(len(parts) >= 2 and [q["line_start"] for q in o["quotes"]] == [first_line_of_part2 + 2, first_line_of_part2 + 7]
        and all(long_outputs[q["char_start"]:q["char_end"]] == q["text"] for q in o["quotes"]), "provenance_is_exact_in_later_parts_of_a_document")

# --- stitched or partly invented quotes stay rejected ---------------------------------------------------------------------------
stitched = {"statement": "item A changed", "quotes": ["form=V1 item=A classification=unresolved ... form=V2 item=A classification=event_only"]}
unicode_stitched = {"statement": "item A changed again", "quotes": ["form=V1 item=A … form=V2 item=A"]}
half = {"statement": "item A under V3", "quotes": ["form=V1 item=A classification=unresolved", "form=V3 item=A classification=continuing"]}
too_many = {"statement": "many", "quotes": ["form=V1 item=A", "form=V1 item=B", "form=V2 item=A", "form=V2 item=B"]}
short = {"statement": "tiny", "quotes": ["V1"]}
art, stub = review({"D3:1": [reply([compare, stitched, unicode_stitched, half, too_many, short])]})
reasons = {r["statement"]: r["reason"] for r in art["rejected_observations"]}
require(reasons == {"item A changed": "stitched_quote", "item A changed again": "stitched_quote", "item A under V3": "quote_not_found_in_document",
                    "many": "too_many_quotes", "tiny": "quote_too_short"}, "stitched_invented_excess_and_trivial_quotes_are_rejected")
half_row = next(r for r in art["rejected_observations"] if r["statement"] == "item A under V3")
require([q["found"] for q in half_row["quotes"]] == [True, False] and not any(o["statement"] == "item A under V3" for o in art["grounded_observations"]),
        "one_unfound_quote_rejects_the_whole_observation")
require([r["rej_id"] for r in art["rejected_observations"]] == ["R1", "R2", "R3", "R4", "R5"], "rejected_observations_carry_their_own_ids")
require(not any(s in p for p in stub.prompts if "List up to" not in p for s in reasons), "rejected_observations_never_reach_any_synthesis_prompt")

# --- a part whose accepted reply grounds nothing is not reviewed -----------------------------------------------------------------
art, stub = review({"D2:1": [reply([{"statement": "invented", "quotes": ["nowhere in this document"]}])]})
require(missing_stages(art) == {"observe:D2:1": "no_grounded_observations"} and art["status"] == "incomplete" and stub.later_calls() == 0,
        "an_accepted_reply_with_no_grounded_observation_does_not_count_as_coverage")

# --- a synthesis cannot claim complete coverage --------------------------------------------------------------------------------
art, stub = review({"D1:1": [ERROR, ERROR]})
md = (RUNTIME / er.REVIEW_AREA / art["review_id"] / "review.md").read_text(encoding="utf-8")
require(stub.later_calls() == 0 and "INCOMPLETE" in md and "observe:D1:1 not reviewed: provider_error" in md and "## Competing hypotheses" not in md
        and "Required coverage: 2 of 3 package parts reviewed" in md, "an_incomplete_review_renders_as_incomplete_with_its_missing_parts")
claims = {**FIRST, "coverage": "complete: every package part was reviewed", "status": "complete"}
art, _ = review({"D2:1": [ERROR, ERROR]}, first=claims)
require(art["status"] == "incomplete" and not art["coverage"]["complete"] and "coverage" not in art["review"], "a_synthesis_claim_cannot_make_coverage_complete")
art, _ = review(first=claims)
require(art["status"] == "complete" and "coverage" not in art["review"] and "status" not in art["review"], "coverage_and_status_are_computed_never_taken_from_the_model")

# --- no synthesis level can cite rejected observations -----------------------------------------------------------------------------
cites = {**FIRST, "failed": [{"statement": "A moved", "int_ids": ["R1", "I2"]}]}
second_cites = {**SECOND, "competing_hypotheses": [{"hypothesis": "h", "evidence_for": ["R1"], "evidence_against": ["O9"]}]}
art, _ = review({"D2:1": [reply([{"statement": "item A gold", "quotes": ["item=A gold=unresolved"]}, {"statement": "invented", "quotes": ["no such line"]}])],
                 "I:D2": [lambda p, m: (json.dumps({"statements": [{"statement": "item A gold", "kind": "finding", "obs_ids": ["R1", "O2"]}]}), dict(OK_META))]},
                first=cites, second=second_cites)
i2 = next(s for s in art["intermediate"]["statements"] if s["int_id"] == "I2")
require(art["status"] == "complete" and art["rejected_observation_references"] == ["R1"] and art["unknown_references"] == ["O9"]
        and i2["obs_ids"] == ["O2"] and i2["dropped_obs_ids"] == ["R1"] and art["review"]["failed"][0]["int_ids"] == ["I2"]
        and art["review"]["competing_hypotheses"] == [] and art["review"]["discriminating_experiments"][0]["distinguishes_dropped"] == [1],
        "citations_of_rejected_observations_are_dropped_and_reported_at_every_level")

# --- required design or corpus absent; optional parts designated before the run --------------------------------------------------
for role in ("design", "corpus", "raw_outputs"):
    docs = {k: v for k, v in DOCS.items() if v[0] != role}
    art, stub = review(docs=docs)
    require(art["status"] == "incomplete" and art["coverage"]["absent_required_roles"] == [role] and not stub.prompts
            and art["coverage"]["missing"][0] == {"kind": "required_role_absent", "role": role, "reason": "the package lists no document with this required role"},
            f"an_absent_required_{role}_forces_incomplete_before_any_model_call")
try:
    review(optional=("items.txt",))
    marked = False
except er.ReviewPackageError as exc:
    marked = str(exc) == "required_role_marked_optional"
require(marked, "a_required_role_cannot_be_designated_optional")
docs = {**DOCS, "notes.txt": ("notes", "Operator note: none.\n")}
art, _ = review({"D4:1": [ERROR, ERROR]}, docs=docs, optional=("notes.txt",))
require(art["status"] == "complete" and art["coverage"]["optional_parts"] == 1 and art["coverage"]["reviewed_optional_parts"] == 0
        and art["coverage"]["missing"] == [] and art["coverage"]["parts"][-1]["reason"] == "provider_error", "an_optional_part_designated_before_the_run_does_not_block")
art, _ = review({"D4:1": [ERROR, ERROR]}, docs=docs)
require(art["status"] == "incomplete" and missing_stages(art) == {"observe:D4:1": "provider_error"}, "an_undesignated_document_is_required")

# --- earlier reviews stay protected; a review never overwrites another -------------------------------------------------------------
prior, _ = review()
prior_md = RUNTIME / er.REVIEW_AREA / prior["review_id"] / "review.md"
art, _ = review(hook=lambda p: prior_md.write_text("rewritten", encoding="utf-8") if "List up to" in p else None)
require(art["status"] == "mutation_guard_failed" and any(prior["review_id"] in ch for ch in art["mutation_guard"]["changes"])
        and art["mutation_guard"]["protected"]["excluded"].endswith(art["review_id"]), "a_change_to_an_earlier_review_fails_the_guard")
fixed = lambda: "2026-01-01T00:00:00Z"  # noqa: E731
pkg = make_package(base / "same")
a1 = er.review_experiment(pkg, call_model=Stub(), identity=IDENT, clock=fixed)
a2 = er.review_experiment(pkg, call_model=Stub(), identity=IDENT, clock=fixed)
require(a1["review_id"] != a2["review_id"] and (RUNTIME / er.REVIEW_AREA / a1["review_id"] / "review.json").is_file(),
        "two_reviews_of_the_same_package_in_the_same_second_never_collide")

print(json.dumps({"suite": "v2731.3.6-review-coverage", "passed": len(CHECKS), "total": len(CHECKS), "ok": True}))
