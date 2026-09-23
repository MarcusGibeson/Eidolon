"""v2734.2.0 - a record's declared identity is evidence about that record.

An observation may name only identifiers its own evidence establishes. Evidence is the observation's exact quotes
*plus* the metadata the system reads from the record the quote was located in - that second half is what lets an
observation say which record it is about without spending one of its three quotes on the record's id.

The baseline reads that metadata from a fixed list of key names (experiment, form, variant, condition, run, item,
case, record). A package whose records identify themselves some other way matches none of them, so the system
discarded the identity of the very line it had just located the quote in, and every observation naming that record
was refused as ``unsupported_identifiers``. With one record per line and a 240 character quote cap, no single quote
could carry both a long record's id and the field it described, so the refusal was unavoidable rather than
informative.

These tests use neutral compound ids (``X17-r3-A``) and a synthetic raw-output record shape. They pin the contract,
not any particular corpus: nothing here references G-CORROB1 content, and the fix is keyed on the *shape* of an
identity key (``id`` or ``*_id``) rather than on a list of names.

What must still fail, still fails: partial support, genuinely separate identifiers where one is unsupported,
identifiers from a different record, invented identifiers, stitched quotes, and over-long quote lists.

    python tools/v2734_2_0_compound_identifier_tests.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for value in (str(ROOT), str(ROOT / "tools"), str(ROOT / "conscious_agent")):
    if value not in sys.path:
        sys.path.insert(0, value)

import experiment_review as base  # noqa: E402
import experiment_review_hierarchical as hier  # noqa: E402
import structured_record_rendering as srr  # noqa: E402

CHECKS: list[tuple[str, bool]] = []


def require(condition: bool, name: str) -> None:
    CHECKS.append((name, bool(condition)))


def record(n: int, repeat: int, role: str) -> dict:
    """A raw-output style record that identifies itself with a compound id and its components, as such corpora do."""
    return {
        "source_path": f"calls/X{n}-r{repeat}-{role}.json",
        "record": {
            "call_id": f"X{n}-r{repeat}-{role}", "pair_id": f"X{n}-r{repeat}", "item_id": f"X{n}",
            "repeat": repeat, "role": role, "seed": 100000 + n,
            "assessment": {"relation": "supports", "scope": "match", "confidence": "high",
                           "quotes": ["a span of source text that the assessment relied upon and repeats verbatim"]},
            "disposition": "use", "rule": "G10", "rules_fired": ["G10"],
            "note": ("padding so the rendered record is comfortably longer than the quote cap, which is the whole "
                     "reason a single quote cannot carry both the identity and the field it describes " * 3),
        },
    }


def rendered_document() -> str:
    """One record per line, exactly as the review package renderer emits them."""
    doc = {"records": [record(17, 3, "A"), record(21, 2, "B"), record(17, 4, "A")]}
    return srr.render(doc)


def line_of(text: str, needle: str) -> int:
    for i, line in enumerate(text.split("\n"), 1):
        if needle in line:
            return i
    raise AssertionError(f"not found: {needle}")


def metadata_for(text: str, needle: str) -> dict:
    n = line_of(text, needle)
    return hier.record_metadata(text, n, n)


def main() -> int:
    doc = rendered_document()

    # --- 1. the fixture really has the shape the problem needs -------------------------------------------------
    first = doc.split("\n")[line_of(doc, '"call_id": "X17-r3-A"') - 1]
    require(len(first) > base.MAX_QUOTE_CHARS * 3, "a_record_is_far_longer_than_one_quote_may_be")
    require('"call_id": "X17-r3-A"' in first and '"disposition": "use"' in first,
            "identity_and_described_field_share_one_line")
    require(doc.count("\n") >= 2, "records_are_rendered_one_per_line")

    # --- 2. the baseline alone cannot see this record's identity ------------------------------------------------
    n = line_of(doc, '"call_id": "X17-r3-A"')
    require(base.record_metadata(doc, n, n) == {}, "the_baseline_key_list_matches_none_of_these_records_keys")

    # --- 3. the extension reads the identity the record declares about itself -----------------------------------
    meta = metadata_for(doc, '"call_id": "X17-r3-A"')
    require(meta.get("call_id") == ["X17-r3-A"], "the_compound_record_id_is_read")
    require(meta.get("pair_id") == ["X17-r3"], "the_pair_id_is_read")
    require(meta.get("item_id") == ["X17"], "the_item_id_is_read")
    require("seed" not in meta and "repeat" not in meta and "role" not in meta,
            "non_identity_fields_are_not_treated_as_identity")
    require(len(base._metadata_label(meta)) < 200, "the_identity_label_stays_small")

    # --- 4. identity comes only from the record the quote was located in ----------------------------------------
    other = metadata_for(doc, '"call_id": "X21-r2-B"')
    require(other.get("call_id") == ["X21-r2-B"], "a_different_record_reads_its_own_id")
    require("X17-r3-A" not in json.dumps(other), "one_records_identity_never_leaks_into_another")

    # --- 5. what the grounding rule now accepts, and what it still refuses ---------------------------------------
    quote = '"disposition": "use", "rule": "G10", "rules_fired": ["G10"]'
    evidence = base.observation_evidence(
        {"quotes": [{"text": quote}], "provenance": {"metadata": meta, "doc_id": "D1"}})

    require(base.unsupported_identifiers("Record X17-r3-A was processed with disposition use and rule G10.",
                                         evidence) == [],
            "an_observation_may_name_the_record_its_quote_came_from")
    require(base.unsupported_identifiers("Record X17-r3 is the pair of that call.", evidence) == [],
            "a_component_the_record_declares_is_also_established")
    # a record the quote did NOT come from stays unsupported
    require(base.unsupported_identifiers("Record X21-r2-B was processed with disposition use.", evidence) != [],
            "naming_a_record_the_quote_did_not_come_from_still_fails")
    # an identifier nothing declares stays unsupported
    require(base.unsupported_identifiers("Record X99-r9-Z was processed with disposition use.", evidence) != [],
            "an_invented_record_id_still_fails")
    require("g11" in base.unsupported_identifiers("The rule applied was G11.", evidence),
            "a_value_that_appears_nowhere_still_fails")

    # --- 6. genuinely separate identifiers still each need support ----------------------------------------------
    # Two real records: naming both while quoting inside only one must still fail.
    both = "Records X17-r3-A and X21-r2-B both carry disposition use."
    require(base.unsupported_identifiers(both, evidence) != [],
            "comparing_two_records_from_one_records_evidence_still_fails")
    merged = dict(meta)
    for key, values in metadata_for(doc, '"call_id": "X21-r2-B"').items():
        merged.setdefault(key, [])
        merged[key] = list(dict.fromkeys(merged[key] + values))
    evidence_both = base.observation_evidence(
        {"quotes": [{"text": quote}], "provenance": {"metadata": merged, "doc_id": "D1"}})
    require(base.unsupported_identifiers(both, evidence_both) == [],
            "naming_two_records_is_supported_only_when_both_are_established")

    # --- 7. partial support of a compound identity still fails ---------------------------------------------------
    partial = {"item_id": ["X17"]}   # the record declared only its item id, not the full call id
    ev_partial = base.observation_evidence(
        {"quotes": [{"text": quote}], "provenance": {"metadata": partial, "doc_id": "D1"}})
    require(base.unsupported_identifiers("Record X17-r9-Q was processed with disposition use.", ev_partial) != [],
            "partial_identity_does_not_establish_a_different_compound")
    require(base.unsupported_identifiers("Item X17 was processed with disposition use.", ev_partial) == [],
            "the_part_that_is_established_is_accepted_on_its_own")

    # --- 8. no validation rule moved -----------------------------------------------------------------------------
    require(base.MAX_QUOTE_CHARS == 240, "the_quote_length_cap_is_unchanged")
    require(base.MAX_QUOTES_PER_OBSERVATION == 3, "the_quote_count_cap_is_unchanged")
    require(base.MAX_OBSERVATIONS_PER_CHUNK == 8, "the_observation_cap_is_unchanged")
    require(base.MIN_QUOTE_CHARS == 4, "the_minimum_quote_length_is_unchanged")
    require(base.CONTRACT_VERSION == "v2731.8", "the_frozen_baseline_contract_is_unchanged")
    require(base.METADATA_KEYS == ("experiment", "prompt_form_equivalent", "form", "variant", "condition", "run",
                                   "item", "case", "record"), "the_baseline_key_list_itself_is_untouched")
    require(hier.CONTRACT_VERSION == "v2735.0", "the_change_carries_its_own_contract_version")

    # --- 9. the extension is scoped, not global -------------------------------------------------------------------
    require(base.record_metadata is not hier.record_metadata, "the_baseline_is_not_patched_at_import")
    with hier.record_identity_metadata():
        require(base.record_metadata is hier.record_metadata, "the_extension_applies_inside_a_review")
        n2 = line_of(doc, '"call_id": "X17-r3-A"')
        require(base.record_metadata(doc, n2, n2).get("call_id") == ["X17-r3-A"],
                "grounding_sees_the_identity_through_the_baseline_entry_point")
    require(base.record_metadata is not hier.record_metadata, "the_baseline_is_restored_afterwards")
    try:
        with hier.record_identity_metadata():
            with hier.record_identity_metadata():
                pass
        require(False, "reentry_should_be_refused")
    except RuntimeError as exc:
        require("not_reentrant" in str(exc), "reentry_is_refused_rather_than_silently_nested")

    # --- 10. end to end through the real grounding path ------------------------------------------------------------
    with hier.record_identity_metadata():
        parsed = {"observations": [
            {"statement": "Record X17-r3-A was processed with disposition use and rule G10.", "quotes": [quote]},
            {"statement": "Record X99-r9-Z was processed with disposition use.", "quotes": [quote]},
        ], "open_questions": []}
        good, bad, _q = base.ground_observations(parsed, doc, "D1", 1, 1, doc_text=doc, chunk_offset=0,
                                                 rejected_start=1)
    require(len(good) == 1, "the_supported_observation_grounds")
    require(good[0]["provenance"]["metadata"].get("call_id") == ["X17-r3-A"],
            "the_grounded_observation_records_which_record_it_came_from")
    require(len(bad) == 1 and bad[0]["reason"] == "unsupported_identifiers",
            "the_invented_record_is_still_refused_for_unsupported_identifiers")

    # and without the extension the same true observation is refused, which is the defect being fixed
    good2, bad2, _ = base.ground_observations(
        {"observations": [{"statement": "Record X17-r3-A was processed with disposition use and rule G10.",
                           "quotes": [quote]}], "open_questions": []},
        doc, "D1", 1, 1, doc_text=doc, chunk_offset=0, rejected_start=1)
    require(not good2 and bad2[0]["reason"] == "unsupported_identifiers",
            "without_the_extension_the_same_true_observation_is_refused")

    failed = [name for name, ok in CHECKS if not ok]
    print(json.dumps({"suite": "v2734.2.0-compound-identifier", "checks": len(CHECKS),
                      "passed": len(CHECKS) - len(failed), "failed": failed[:14]}, indent=1))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
