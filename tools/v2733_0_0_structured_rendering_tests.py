"""v2733.0.0 - adversarial tests for record-per-line rendering of structured review documents.

Reproduces the D5:14 structural shape synthetically - pretty-printed JSON records whose identity line is far from
their field lines - shows that shape defeats grounding, and shows the repaired rendering permits grounded
observations with validation completely unchanged.

No G-EVID1 content is used anywhere in this suite.

    python tools/v2733_0_0_structured_rendering_tests.py
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
import experiment_review_hierarchical as hier  # noqa: E402
import structured_record_rendering as srr  # noqa: E402
import rendered_review_package as rrp  # noqa: E402

CHECKS: list[tuple[str, bool]] = []


def require(condition: bool, name: str) -> None:
    CHECKS.append((name, bool(condition)))


def synthetic_report(count: int = 40) -> dict:
    """The D5:14 shape: an array of records, each an id plus a nested object of properties."""
    return {
        "contract_version": "q-cap.0",
        "primary_gate": {"failures": 3, "passed": False},
        "empty_section": [],
        "transitions": [
            {"item_id": f"S{n:03d}", "repeat": n % 3 + 1,
             "provisional": {"relation": ["supports", "partial", "contradicts"][n % 3],
                             "scope": ["match", "narrower", "mismatch"][n % 3],
                             "confidence": "high", "reasons": []},
             "rules_fired": [f"R{n % 5}"], "governing_rule": f"R{n % 5}",
             "disposition": ["use", "investigate", "abstain"][n % 3]}
            for n in range(count)],
        "cost": {"seconds": 12.5, "calls": count},
    }


def main() -> int:
    doc = synthetic_report()

    # --- 1. the old shape is the problem: identity and fields never share a line ---------------------------------
    pretty = json.dumps(doc, indent=1, ensure_ascii=False)
    plines = [l for l in pretty.split("\n") if l.strip()]
    with_id = [l for l in plines if "item_id" in l]
    both = [l for l in plines if "item_id" in l and "governing_rule" in l]
    require(len(with_id) > 0 and not both,
            "pretty_printed_json_never_puts_identity_and_fields_on_one_line")
    require(sum(len(l) for l in plines) / len(plines) < 40,
            "pretty_printed_lines_are_too_thin_to_carry_a_record")

    # --- 2. the repaired rendering colocates them ----------------------------------------------------------------
    text = srr.render(doc)
    lines = [l for l in text.split("\n") if l]
    records = [l for l in lines if '"item_id"' in l]
    require(records, "records_are_rendered")
    require(all('"governing_rule"' in l for l in records),
            "every_record_line_carries_identity_and_fields_together")
    require(all(l.index('"item_id"') < 60 for l in records),
            "identity_appears_near_the_start_so_a_leading_quote_captures_it")
    require(len(lines) < len(plines) / 5, "one_line_per_record_instead_of_one_line_per_field")

    # --- 3. lossless, no invention, deterministic -----------------------------------------------------------------
    require(srr.reconstruct(text) == doc, "rendering_round_trips_exactly")
    require(srr.render(doc) == text, "rendering_is_deterministic")
    require(srr.render(json.loads(json.dumps(doc))) == text, "rendering_depends_only_on_content")
    rebuilt = srr.reconstruct(text)
    require(json.dumps(rebuilt, sort_keys=False) == json.dumps(doc, sort_keys=False),
            "key_order_survives_the_round_trip")
    require(rebuilt["empty_section"] == [] and "empty_section" in rebuilt,
            "empty_containers_are_preserved_not_dropped")

    # nothing invented: every character of a record body comes from the document
    for line in records:
        _, offset = srr._DECODER.raw_decode(line)
        body = line[offset:].strip()
        require(json.loads(body) in doc["transitions"], "a_record_line_contains_exactly_a_real_record")

    # --- 4. nested objects and arrays survive ----------------------------------------------------------------------
    nested = {"a": {"b": {"c": [1, 2, {"d": "e"}]}}, "list": [[1, 2], [3, [4, 5]]], "null": None, "t": True}
    require(srr.reconstruct(srr.render(nested)) == nested, "nested_objects_and_arrays_round_trip")
    unicode_doc = {"kéy": "välue — dash", "emoji": "\U0001F600", "quote": 'he said "hi"'}
    require(srr.reconstruct(srr.render(unicode_doc)) == unicode_doc, "unicode_and_quotes_round_trip")
    awkward = {"has space": 1, "has.dot": 2, "has[bracket]": 3, "": 4}
    require(srr.reconstruct(srr.render(awkward)) == awkward, "awkward_keys_round_trip")

    # --- 5. long records stay whole; oversized nodes are walked into ----------------------------------------------
    long_doc = {"big": {f"k{n}": "x" * 200 for n in range(50)}}
    long_text = srr.render(long_doc)
    require(srr.reconstruct(long_text) == long_doc, "an_oversized_section_still_round_trips")
    require(all(len(l) <= srr.MAX_RECORD_CHARS + 200 for l in long_text.split("\n") if l),
            "walking_into_a_large_section_keeps_lines_bounded")

    # A long RECORD is never split, because splitting it would separate its identity from its fields - the exact
    # failure this rendering exists to remove.
    huge = {"records": [{"item_id": f"S{n:03d}", "payload": "y" * (srr.MAX_RECORD_CHARS * 2), "rule": f"R{n}"}
                        for n in range(3)]}
    huge_text = srr.render(huge)
    require(srr.reconstruct(huge_text) == huge, "an_oversized_record_round_trips")
    record_lines = [l for l in huge_text.split("\n") if l]
    require(len(record_lines) == 3, "each_oversized_record_is_still_exactly_one_line")
    require(all('"item_id"' in l and '"rule"' in l for l in record_lines),
            "an_oversized_record_keeps_identity_and_fields_on_the_same_line")
    require(all(l.index('"item_id"') < 60 for l in record_lines),
            "an_oversized_record_is_still_quotable_from_its_start")

    # --- 6. record boundaries and chunk boundaries -----------------------------------------------------------------
    big = synthetic_report(400)
    big_text = srr.render(big)
    chunks = base.chunks(big_text)
    require("".join(chunks) == big_text, "chunking_the_rendering_is_lossless")
    require(len(chunks) > 1, "the_test_document_really_does_span_several_parts")
    intact = 0
    for chunk in chunks:
        for line in chunk.split("\n"):
            if line.startswith('["transitions"') and line.endswith("}"):
                intact += 1
    require(intact >= len(big["transitions"]) - len(chunks),
            "almost_every_record_survives_chunking_whole_only_part_edges_split")

    # --- 7. grounding actually succeeds on the repaired shape, with validation untouched ---------------------------
    with tempfile.TemporaryDirectory(prefix="v2733-") as tmp:
        work = Path(tmp)
        source = work / "scorer_report.json"
        source.write_text(json.dumps(doc, indent=1), encoding="utf-8")
        rendered, provenance = rrp.render_source(source, "Q-CAP synthetic scorer report")
        require(provenance["rendering"] == srr.RENDERING_ID, "provenance_records_the_rendering_used")
        require(provenance["canonical_sha256"], "provenance_records_the_canonical_digest")

        chunk = base.chunks(rendered)[0]
        record_line = next(l for l in chunk.split("\n") if '"item_id"' in l)
        quote = record_line[:200]
        parsed = {"observations": [{"statement": "the record names an item and the rule that governed it",
                                    "quotes": [quote]}], "open_questions": []}
        grounded, rejected, _ = base.ground_observations(parsed, chunk, "D1", 1, 1, doc_text=rendered)
        require(len(grounded) == 1 and not rejected,
                "a_single_contiguous_quote_from_one_record_line_now_grounds")
        located = grounded[0]["quotes"][0]
        require(located["found"] is True, "the_quote_is_located")
        require(rendered[located["char_start"]:located["char_end"]] == located["text"],
                "the_quote_relocates_byte_exactly_in_the_rendered_document")
        require('"item_id"' in located["text"], "the_grounded_quote_carries_the_record_identity")

        # the same claim against the OLD shape cannot ground, which is the bug being repaired
        old_text = json.dumps(doc, indent=1, ensure_ascii=False)
        old_chunk = base.chunks(old_text)[0]
        field_line = next(l for l in old_chunk.split("\n") if '"governing_rule"' in l)
        old = {"observations": [{"statement": "item S000 is governed by rule R0",
                                 "quotes": [field_line.strip()]}], "open_questions": []}
        g2, r2, _ = base.ground_observations(old, old_chunk, "D1", 1, 1, doc_text=old_text)
        require(not g2 and r2 and r2[0]["reason"] == "unsupported_identifiers",
                "the_old_shape_still_fails_exactly_as_it_did_on_D5_14")

        # --- 8. validation is genuinely unchanged: bad output still fails ------------------------------------------
        fake = {"observations": [{"statement": "the record shows something",
                                 "quotes": ["this text is nowhere in the document at all"]}], "open_questions": []}
        g3, r3, _ = base.ground_observations(fake, chunk, "D1", 1, 1, doc_text=rendered)
        require(not g3 and r3[0]["reason"] == "quote_not_found_in_document",
                "a_fabricated_quote_is_still_refused")
        stitched = {"observations": [{"statement": "the record shows something",
                                     "quotes": [record_line[:40] + " ... " + record_line[-40:]]}],
                    "open_questions": []}
        g4, r4, _ = base.ground_observations(stitched, chunk, "D1", 1, 1, doc_text=rendered)
        require(not g4 and r4[0]["reason"] == "stitched_quote", "a_stitched_quote_is_still_refused")
        claim = {"observations": [{"statement": "item S999 appears in this record",
                                  "quotes": [quote]}], "open_questions": []}
        g5, r5, _ = base.ground_observations(claim, chunk, "D1", 1, 1, doc_text=rendered)
        require(not g5 and r5[0]["reason"] == "unsupported_identifiers",
                "an_identifier_absent_from_the_quote_is_still_refused")

        # --- 9. a whole package builds, verifies and reviews ------------------------------------------------------
        design = work / "design.md"
        design.write_text("Q-CAP synthetic design note.\nIt describes a made up experiment.\n", encoding="utf-8")
        corpus = work / "corpus.json"
        corpus.write_text(json.dumps({"items": [{"item_id": f"S{n:03d}", "text": f"record {n}"}
                                                for n in range(30)]}, indent=1), encoding="utf-8")
        outputs = work / "raw_outputs.json"
        outputs.write_text(json.dumps({"observations": [{"item_id": f"S{n:03d}", "reply": f"reply {n}"}
                                                        for n in range(30)]}, indent=1), encoding="utf-8")
        pkg = work / "package"
        summary = rrp.build([
            {"path": "design.md", "role": "design", "description": "synthetic design", "source": str(design)},
            {"path": "corpus.txt", "role": "corpus", "description": "synthetic corpus", "source": str(corpus),
             "title": "Q-CAP corpus"},
            {"path": "raw_outputs.txt", "role": "raw_outputs", "description": "synthetic outputs",
             "source": str(outputs), "title": "Q-CAP raw outputs"},
            {"path": "scorer_report.txt", "role": "scorer", "description": "synthetic scorer",
             "source": str(source), "title": "Q-CAP scorer report"},
        ], out_dir=pkg, experiment_id="Q-CAP-RENDERED", title="Q-CAP rendered package",
            brief="Synthetic package for renderer qualification.", canonical_experiment_id="Q-CAP")
        require(summary["total_parts"] >= 1, "the_package_builds")
        checks = rrp.verify(pkg, {"corpus.txt": corpus, "raw_outputs.txt": outputs, "scorer_report.txt": source,
                                  "design.md": design})
        require(checks["all_documents_verified"], "every_document_verifies_against_its_canonical_source")
        require(checks["rendering_id"] == srr.RENDERING_ID, "the_manifest_records_the_rendering_id")
        manifest = json.loads((pkg / base.MANIFEST_NAME).read_text(encoding="utf-8"))
        require(manifest.get("canonical_experiment_id") == "Q-CAP",
                "the_package_names_the_canonical_experiment_it_renders")
        require("not byte-identical" in manifest.get("relationship_to_canonical", ""),
                "the_package_states_plainly_that_it_is_not_the_canonical_artifact")
        for entry in manifest["documents"]:
            require(bool((entry.get("source") or {}).get("canonical_sha256")),
                    f"every_document_traces_to_its_canonical_source:{entry['path']}")

        # a real review over the rendered package, with the deterministic stub
        import reviewer_capacity_qualification as q

        runtime = work / "rt"
        runtime.mkdir(parents=True, exist_ok=True)
        art = hier.review_experiment(pkg, call_model=q.deterministic_stub(), runtime_root_path=runtime,
                                     identity={"model": "stub", "provider": "test", "context_size": 8192,
                                               "resolved_config_sha256": "0" * 64})
        require(art["coverage"]["required_coverage"] == 1.0, "a_rendered_package_reviews_with_full_coverage")
        require(not art["coverage"]["levels"]["architecture"]["silently_dropped"],
                "no_observation_is_lost_reviewing_a_rendered_package")

    # --- 10. the retry limit and the reviewer contract are untouched ------------------------------------------------
    require(hier.OBSERVE_GROUNDING_ATTEMPTS == 2, "the_retry_limit_is_unchanged")
    require(base.CONTRACT_VERSION == "v2731.8", "the_baseline_reviewer_is_unchanged")
    require(base.MIN_QUOTE_CHARS == 4 and base.MAX_QUOTE_CHARS == 240, "quote_limits_are_unchanged")
    require(base.REQUIRED_ROLES == ("design", "corpus", "raw_outputs"), "coverage_requirements_are_unchanged")
    # The module docstring may name the incident that motivated the renderer; that is documentation. What must not
    # exist is executable behaviour keyed to any experiment, document, item or outcome, so this checks the code with
    # docstrings and comments removed rather than the raw text.
    import ast

    source_text = (ROOT / "tools" / "structured_record_rendering.py").read_text(encoding="utf-8")
    tree = ast.parse(source_text)

    class StripText(ast.NodeTransformer):
        """Drop every bare string literal statement, which removes docstrings wherever they sit."""

        def visit_Expr(self, node: ast.Expr):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                return None
            return node

    code_only = ast.unparse(StripText().visit(tree))
    for leak in ("G-EVID1", "I27", "I51", "unsafe_use", "item_id", "disposition", "scorer", "transitions"):
        require(leak not in code_only, f"the_renderer_has_no_experiment_specific_behaviour:{leak}")

    # Emission may branch on size and on container type. It may never branch on what a value says.
    literals = [n for n in ast.walk(ast.parse(code_only)) if isinstance(n, ast.Compare)
                and any(isinstance(c, ast.Constant) and isinstance(c.value, str) for c in n.comparators)]
    require(not literals, "the_renderer_never_compares_a_value_against_a_string_literal")

    failed = [name for name, ok in CHECKS if not ok]
    print(json.dumps({"suite": "v2733.0.0-structured-rendering", "checks": len(CHECKS),
                      "passed": len(CHECKS) - len(failed), "failed": failed}, indent=1))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
