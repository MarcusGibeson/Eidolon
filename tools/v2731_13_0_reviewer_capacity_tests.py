"""v2731.13.0 - adversarial and deterministic tests for the reviewer capacity qualification harness.

These test the harness and the frozen reviewer's fail-closed behaviour at scale. They never touch G-EVID1.

    python tools/v2731_13_0_reviewer_capacity_tests.py
"""

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for value in (str(ROOT), str(ROOT / "tools"), str(ROOT / "conscious_agent")):
    if value not in sys.path:
        sys.path.insert(0, value)

import experiment_review as er  # noqa: E402
import reviewer_capacity_qualification as q  # noqa: E402

CHECKS: list[tuple[str, bool]] = []


def require(condition: bool, name: str) -> None:
    CHECKS.append((name, bool(condition)))


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="q-cap-tests-") as tmp:
        work = Path(tmp)

        # --- 1. deterministic rebuilds -------------------------------------------------------------------------
        a = q.build_package(work / "a", 28)
        b = q.build_package(work / "b", 28)
        digests = []
        for base in (work / "a", work / "b"):
            digests.append({p.name: er._sha256_file(p) for p in sorted(base.iterdir())})
        require(digests[0] == digests[1], "rebuilding_a_package_is_byte_identical")
        require(a["parts"] == b["parts"] == 28, "the_builder_hits_the_exact_part_count")
        require(a["chars"] == b["chars"], "the_builder_is_deterministic_in_size")

        # --- 2. no oversized parts -----------------------------------------------------------------------------
        oversized = []
        for name, _, _ in q.DOCS:
            text = (work / "a" / name).read_text(encoding="utf-8")
            oversized += [len(c) for c in er.chunks(text) if len(c) > er.CHUNK_CHARS]
        require(not oversized, "no_part_exceeds_the_reviewer_chunk_limit")

        # --- 3. chunking is lossless and ordered ---------------------------------------------------------------
        for name, _, _ in q.DOCS:
            text = (work / "a" / name).read_text(encoding="utf-8")
            require("".join(er.chunks(text)) == text, f"chunking_is_lossless:{name}")

        # --- 4. every record line is unique, so loss and duplication are detectable -----------------------------
        refs: list[str] = []
        for name, _, _ in q.DOCS:
            text = (work / "a" / name).read_text(encoding="utf-8")
            refs += [line.split()[0] for line in text.split("\n") if line.startswith("ref=")]
        require(len(refs) == len(set(refs)), "every_synthetic_record_is_uniquely_identified")

        # --- 5. a clean run at scale preserves everything -------------------------------------------------------
        clean = q.qualify(28, work_dir=work / "clean", guard_source=False)
        m = clean["measurements"]
        require(m["status"] == "complete", "a_calibrated_run_at_28_parts_completes")
        require(m["part_coverage"]["full"], "full_required_part_coverage")
        require(m["observation_preservation"]["no_silent_loss"], "no_observation_is_silently_dropped")
        require(m["uncaptured_accounting"]["balances"], "cited_plus_carried_equals_grounded")
        require(m["relocatability"]["relocatable"], "every_quote_relocates_exactly_in_its_source_document")
        require(m["document_boundaries"]["correct"], "every_quote_falls_inside_its_own_part")
        require(m["identifier_validity"]["valid"], "no_statement_cites_an_identifier_that_does_not_exist")
        require(m["synthesis"]["complete"], "every_synthesis_unit_is_accepted")

        # --- 6. observation loss is caught, not absorbed --------------------------------------------------------
        def silent_stub(prompt: str, max_tokens: int):
            if '"observations"' in prompt and '"open_questions"' in prompt:
                return json.dumps({"observations": [], "open_questions": []}), {"metrics": {"eval_count": 4}}
            return q.deterministic_stub()(prompt, max_tokens)

        pkg = work / "lossy"
        q.build_package(pkg, 28)
        runtime = work / "lossy-runtime"
        runtime.mkdir(parents=True, exist_ok=True)
        art = er.review_experiment(pkg, call_model=silent_stub, runtime_root_path=runtime,
                                   identity={"model": "stub", "provider": "test", "context_size": 8192,
                                             "resolved_config_sha256": "0" * 64})
        require(art["status"] == "incomplete", "a_run_that_grounds_nothing_fails_closed")
        require(any(x["kind"] == "required_part_not_reviewed" for x in art["coverage"]["missing"]),
                "unreviewed_required_parts_are_named")
        require(art["coverage"]["required_coverage"] == 0.0, "coverage_reports_the_loss_rather_than_hiding_it")

        # --- 7. a fabricated quote cannot ground ----------------------------------------------------------------
        def fabricating_stub(prompt: str, max_tokens: int):
            if '"observations"' in prompt and '"open_questions"' in prompt:
                return json.dumps({"observations": [
                    {"statement": "the record shows alpha bravo charlie",
                     "quotes": ["ref=NOTINANYDOCUMENT0000 item=S999 fabricated span"]}],
                    "open_questions": []}), {"metrics": {"eval_count": 40}}
            return q.deterministic_stub()(prompt, max_tokens)

        pkg2 = work / "fabricated"
        q.build_package(pkg2, 28)
        runtime2 = work / "fabricated-runtime"
        runtime2.mkdir(parents=True, exist_ok=True)
        art2 = er.review_experiment(pkg2, call_model=fabricating_stub, runtime_root_path=runtime2,
                                    identity={"model": "stub", "provider": "test", "context_size": 8192,
                                              "resolved_config_sha256": "0" * 64})
        require(not art2["grounded_observations"], "a_quote_that_is_not_in_the_document_never_grounds")
        require(all(r["reason"] == "quote_not_found_in_document" for r in art2["rejected_observations"]),
                "a_fabricated_quote_is_rejected_for_the_right_reason")
        require(art2["status"] == "incomplete", "a_fully_fabricated_run_fails_closed")

        # --- 8. cross-document quoting is a boundary violation and is rejected ----------------------------------
        other = (work / "a" / "evidence.txt").read_text(encoding="utf-8").split("\n")[3]

        def cross_stub(prompt: str, max_tokens: int):
            if '"observations"' in prompt and '"open_questions"' in prompt and "corpus" in prompt:
                return json.dumps({"observations": [
                    {"statement": "the record shows alpha bravo", "quotes": [other[:200]]}],
                    "open_questions": []}), {"metrics": {"eval_count": 40}}
            return q.deterministic_stub()(prompt, max_tokens)

        pkg3 = work / "cross"
        q.build_package(pkg3, 28)
        runtime3 = work / "cross-runtime"
        runtime3.mkdir(parents=True, exist_ok=True)
        art3 = er.review_experiment(pkg3, call_model=cross_stub, runtime_root_path=runtime3,
                                    identity={"model": "stub", "provider": "test", "context_size": 8192,
                                              "resolved_config_sha256": "0" * 64})
        corpus_docs = [d["doc_id"] for d in art3["provenance"]["documents"] if d["role"] == "corpus"]
        leaked = [o for o in art3["grounded_observations"]
                  if o["doc_id"] in corpus_docs and any(q_["text"] in other for q_ in o["quotes"])]
        require(not leaked, "a_quote_borrowed_from_another_document_never_grounds_in_this_one")

        # --- 9. exceeding the final input budget fails closed, it does not degrade quietly ---------------------
        over = q.qualify(28, work_dir=work / "over", guard_source=False, **q.SENSITIVITY["pessimistic"])
        mo = over["measurements"]
        require(mo["status"] == "incomplete", "exceeding_the_final_input_budget_fails_closed")
        require(any(x["kind"] == "final_input_exceeds_budget" for x in mo["mechanical_verification"]["missing"]),
                "the_budget_overflow_is_named_as_the_reason")
        require(not mo["final_budget"]["within"], "the_overflow_is_measured_rather_than_absorbed")
        require(mo["part_coverage"]["full"], "coverage_upstream_of_the_overflow_is_still_reported_honestly")

        # --- 10. the reviewer itself is untouched by qualification ----------------------------------------------
        require(er.CONTRACT_VERSION == "v2731.8", "the_reviewer_contract_version_is_unchanged")
        require(er.CHUNK_CHARS == 6500 and er.FINAL_INPUT_BUDGET_CHARS == 12000,
                "the_reviewer_limits_are_unchanged_by_this_qualification")
        require(clean["reviewer"]["module_sha256"] == er._sha256_file(Path(er.__file__).resolve()),
                "the_qualification_records_the_reviewer_digest_it_actually_ran")

    failed = [name for name, ok in CHECKS if not ok]
    print(json.dumps({"suite": "v2731.13.0-reviewer-capacity", "checks": len(CHECKS),
                      "passed": len(CHECKS) - len(failed), "failed": failed}, indent=1))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
