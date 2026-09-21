"""v2733.1.0 - every field must be quotable the way JSON writes it.

Regression for the first G-CORROB1 independent review (02f591d6eb9b75e7), which stopped at 135/137 required parts.
Two parts grounded nothing:

* ``observe:D12:2`` (execution_authorization) - all 16 attempted quotes failed to locate;
* ``observe:D4:1`` (corpus) - 4 failed to locate and 12 named an identifier their quote did not contain.

Cause, in the renderer rather than the reviewer: when a dict was too large to emit whole, record-per-line.v1 walked
into it and put each field's name in the *path* - ``["execution_manifest","one_run_only"] true``. The line therefore
contained no ``"one_run_only": true`` for anyone to copy. Every honest citation of such a field failed to locate, and
a part made entirely of such lines could not ground a single observation.

    python tools/v2733_1_0_quotable_field_tests.py
"""

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for value in (str(ROOT), str(ROOT / "tools"), str(ROOT / "conscious_agent")):
    if value not in sys.path:
        sys.path.insert(0, value)

import experiment_review as base  # noqa: E402
import structured_record_rendering as srr  # noqa: E402

CHECKS: list[tuple[str, bool]] = []


def require(condition: bool, name: str) -> None:
    CHECKS.append((name, bool(condition)))


def wide_manifest(fields: int = 60) -> dict:
    """A flat dict far larger than the record budget: the execution_authorization shape."""
    return {"manifest": {f"field_{n:03d}": (f"value-{n:03d}" if n % 3 else n) for n in range(fields)}}


def main() -> int:
    # --- 1. a field name is never left in the path alone ---------------------------------------------------------
    doc = wide_manifest()
    text = srr.render(doc)
    lines = [l for l in text.split("\n") if l]
    require(len(lines) > 1, "a_dict_larger_than_the_budget_really_is_split")
    for line in lines:
        path, offset = srr._DECODER.raw_decode(line)
        body = json.loads(line[offset:].strip())
        require(isinstance(body, dict) and body,
                "a_split_dict_is_emitted_as_object_fragments_not_bare_values")
        require(all(f'"{key}": ' in line for key in body),
                "every_key_in_a_fragment_appears_on_the_line_in_quotable_form")
    for key, value in doc["manifest"].items():
        literal = json.dumps({key: value}, ensure_ascii=False, separators=(", ", ": "))[1:-1]
        require(literal in text, f"the_field_can_be_quoted_as_written:{key}")

    # --- 2. the exact shapes the review failed on are quotable now ------------------------------------------------
    failed_shape = {"execution_manifest": {**{f"pad_{n}": "x" * 40 for n in range(40)},
                                           "one_run_only": True, "expected_pairs": 96,
                                           "chat_input_contract": "exact_manifest_id_only"}}
    rendered = srr.render(failed_shape)
    for probe in ('"one_run_only": true', '"expected_pairs": 96',
                  '"chat_input_contract": "exact_manifest_id_only"'):
        require(probe in rendered, f"the_span_the_reviewer_wrote_now_exists:{probe}")
    require(srr.reconstruct(rendered) == failed_shape, "the_repaired_split_still_round_trips")

    # a top-level metadata block, the corpus.txt shape
    corpus_shape = {"candidate_id": "X", "status": "revised_design_not_authorized", "item_count": 32,
                    "items": [{"item_id": f"R{n:02d}", "evidence": "e" * 80} for n in range(30)]}
    corpus_text = srr.render(corpus_shape)
    for probe in ('"item_count": 32', '"status": "revised_design_not_authorized"', '"item_id": "R00"'):
        require(probe in corpus_text, f"corpus_metadata_is_quotable:{probe}")
    require(srr.reconstruct(corpus_text) == corpus_shape, "the_corpus_shape_round_trips")

    # --- 3. conventional spacing, because that is how a quote gets written ----------------------------------------
    require(srr._SEPARATORS == (", ", ": "), "rendering_uses_conventional_json_spacing")
    sample = srr.render({"a": {"k": 1, "j": 2}})
    require('"k": 1' in sample and '"k":1' not in sample,
            "a_field_is_written_with_the_space_a_reviewer_would_write")

    # --- 4. losslessness survives every fragment case --------------------------------------------------------------
    for name, case in (
        ("wide_flat", wide_manifest(200)),
        ("nested_large", {"a": {"b": {f"k{n}": "y" * 50 for n in range(80)}}}),
        ("mixed", {"small": 1, "big": {f"k{n}": n for n in range(300)}, "list": [1, 2, 3]}),
        ("one_huge_value", {"outer": {"tiny": 1, "huge": {"inner": "z" * (srr.MAX_RECORD_CHARS * 3)}}}),
        ("array_of_records", {"rows": [{"item_id": f"S{n}", "payload": "p" * 300} for n in range(20)]}),
        ("empty_containers", {"a": {}, "b": [], "c": {"d": {}}}),
        ("unicode", {"outer": {f"kéy{n}": "välue — dash" for n in range(60)}}),
        ("awkward_keys", {"outer": {f"has space {n}": n for n in range(60)}}),
        ("null_and_bool", {"outer": {f"k{n}": [None, True, False][n % 3] for n in range(60)}}),
    ):
        rendered_case = srr.render(case)
        require(srr.reconstruct(rendered_case) == case, f"round_trip:{name}")
        require(srr.render(case) == rendered_case, f"deterministic:{name}")

    # --- 5. key order is preserved across fragments ----------------------------------------------------------------
    ordered = {"outer": {f"k{n:03d}": "v" * 60 for n in range(60)}}
    back = srr.reconstruct(srr.render(ordered))
    require(list(back["outer"].keys()) == list(ordered["outer"].keys()),
            "fragmented_dicts_keep_their_original_key_order")

    # --- 6. records are still never split ---------------------------------------------------------------------------
    records = {"rows": [{"item_id": f"S{n}", "body": "b" * (srr.MAX_RECORD_CHARS * 2)} for n in range(3)]}
    row_lines = [l for l in srr.render(records).split("\n") if l]
    require(len(row_lines) == 3, "each_oversized_record_is_still_exactly_one_line")
    require(all('"item_id": ' in l and '"body": ' in l for l in row_lines),
            "an_oversized_record_keeps_identity_and_fields_together")

    # --- 7. grounding really succeeds on the repaired shape, validation untouched -----------------------------------
    rendered_manifest = srr.render(failed_shape)
    chunk = base.chunks(rendered_manifest)[0]
    probe = '"chat_input_contract": "exact_manifest_id_only"'
    if probe in chunk:
        parsed = {"observations": [{"statement": "the manifest fixes the chat input contract",
                                    "quotes": [probe]}], "open_questions": []}
        grounded, rejected, _ = base.ground_observations(parsed, chunk, "D1", 1, 1, doc_text=rendered_manifest)
        require(len(grounded) == 1 and not rejected, "a_field_quote_now_grounds")
        located = grounded[0]["quotes"][0]
        require(rendered_manifest[located["char_start"]:located["char_end"]] == located["text"],
                "the_field_quote_relocates_byte_exactly")
    else:
        require(False, "the_probe_field_landed_in_the_first_part")

    # validation is unchanged: invented and stitched quotes still fail
    bad = {"observations": [{"statement": "the manifest says something",
                             "quotes": ['"not_a_real_field": 1']}], "open_questions": []}
    g, r, _ = base.ground_observations(bad, chunk, "D1", 1, 1, doc_text=rendered_manifest)
    require(not g and r[0]["reason"] == "quote_not_found_in_document", "an_invented_field_is_still_refused")
    first_line = chunk.split("\n")[0]
    stitched = {"observations": [{"statement": "the manifest says something",
                                  "quotes": [first_line[:40] + " ... " + first_line[-40:]]}],
                "open_questions": []}
    g2, r2, _ = base.ground_observations(stitched, chunk, "D1", 1, 1, doc_text=rendered_manifest)
    require(not g2 and r2[0]["reason"] == "stitched_quote", "a_stitched_quote_is_still_refused")

    # --- 8. the old rendering really was unquotable, which is what changed ------------------------------------------
    def v1_walk(path, value, lines):
        body = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        if len(body) <= srr.MAX_RECORD_CHARS or not isinstance(value, dict) or not value:
            lines.append(f"{json.dumps(path, separators=(',', ':'))} {body}")
            return
        for key, item in value.items():
            v1_walk(path + [key], item, lines)

    old_lines: list[str] = []
    v1_walk([], failed_shape, old_lines)
    old_text = "\n".join(old_lines)
    require('"one_run_only": true' not in old_text,
            "the_previous_rendering_did_not_contain_the_field_as_written")
    require('"one_run_only"' in old_text, "the_field_name_existed_only_inside_a_path")
    require('"one_run_only": true' in rendered, "the_repaired_rendering_does_contain_it")

    # --- 9. nothing about the reviewer changed ----------------------------------------------------------------------
    import experiment_review_hierarchical as hier

    require(base.CONTRACT_VERSION == "v2731.8", "the_baseline_reviewer_is_unchanged")
    require(hier.OBSERVE_GROUNDING_ATTEMPTS == 2, "the_retry_limit_is_unchanged")
    require(base.REQUIRED_ROLES == ("design", "corpus", "raw_outputs"), "required_roles_are_unchanged")
    require(base.MAX_QUOTE_CHARS == 240 and base.MIN_QUOTE_CHARS == 4, "quote_limits_are_unchanged")
    require(srr.RENDERING_ID == "record-per-line.v2", "the_rendering_carries_a_new_id")

    failed = [name for name, ok in CHECKS if not ok]
    print(json.dumps({"suite": "v2733.1.0-quotable-field", "checks": len(CHECKS),
                      "passed": len(CHECKS) - len(failed), "failed": failed[:12]}, indent=1))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
