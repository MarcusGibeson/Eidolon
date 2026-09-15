from __future__ import annotations

"""Suffix omission in review_experiment (spec 2.20; the two-level synthesis this suite also covered is superseded in 2.21).

Deterministic; no model. Proves the distinction between a safe suffix omission (a single trailing ellipsis after an exact,
uniquely relocatable prefix within one record, with nothing the statement relies on left in the omitted text) and
evidence stitching, which stays rejected in every form.
"""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for value in (str(ROOT), str(AGENT)):
    if value not in sys.path:
        sys.path.insert(0, value)
sys.dont_write_bytecode = True

import experiment_review as er  # noqa: E402

CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


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

print(json.dumps({"suite": "v2731.3.7-omission", "passed": len(CHECKS), "total": len(CHECKS), "ok": True}))
