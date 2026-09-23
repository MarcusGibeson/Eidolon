"""v2733.5.0 - observation discipline for near-identical twin records.

G-CORROB1 independent review attempt 2 (738414ca6023eebb) reached 139 of 140 required parts. The sole missing part,
``observe:D4:2``, held seventeen records including several near-identical boundary pairs. Every quote the model
supplied was located byte-exactly - the record-per-line.v2 repair worked - but all sixteen attempted observations
were refused as ``unsupported_identifiers``, because the model wrote one comparative statement per pair ("R15 and R16
share ...") while quoting only one of the two records.

The validator was right every time. What was missing was an instruction about form: observe each record on its own,
and leave comparison to a later stage unless every identifier compared is grounded in the observation itself.

These tests pin that the refusal still happens and that the disciplined shape now succeeds. No validation rule is
relaxed anywhere in this suite.

    python tools/v2733_5_0_twin_record_tests.py
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

CHECKS: list[tuple[str, bool]] = []


def require(condition: bool, name: str) -> None:
    CHECKS.append((name, bool(condition)))


def twin_corpus(pairs: int = 7) -> dict:
    """The D4:2 shape: consecutive records that differ in one field and share their evidence wording."""
    items = []
    for n in range(pairs):
        a, b = f"R{2 * n + 15:02d}", f"R{2 * n + 16:02d}"
        shared = (f"The Ossa site register number {n} lists three turbines and records the eastern turbine as T-9, "
                  f"while the model field for the remaining two is left blank.")
        items.append({"item_id": a, "proposition_id": f"RP{2 * n + 15:02d}", "evidence_id": f"RE{2 * n + 15:02d}",
                      "proposition": f"The eastern turbine at site {n} is model T-9.", "evidence": shared})
        items.append({"item_id": b, "proposition_id": f"RP{2 * n + 16:02d}", "evidence_id": f"RE{2 * n + 16:02d}",
                      "proposition": f"Every turbine at site {n} is model T-9.", "evidence": shared})
    return {"candidate_id": "Q-TWIN", "item_count": len(items), "items": items}


def rendered_chunk(doc: dict) -> tuple[str, str]:
    text = srr.render(doc)
    return text, base.chunks(text)[0]


def main() -> int:
    doc = twin_corpus()
    text, chunk = rendered_chunk(doc)
    lines = [l for l in chunk.split("\n") if '"item_id"' in l]
    require(len(lines) >= 4, "the_fixture_really_contains_several_twin_records")
    require(lines[0].split('"evidence": ')[1] == lines[1].split('"evidence": ')[1],
            "twin_records_share_their_evidence_wording_exactly")
    require('"item_id": "R15"' in lines[0] and '"item_id": "R16"' in lines[1],
            "each_twin_is_its_own_record_on_its_own_line")

    def ground(observations):
        return base.ground_observations({"observations": observations, "open_questions": []},
                                        chunk, "D4", 2, 1, doc_text=text)

    # --- 1. the attempt-2 failure shape is still refused ---------------------------------------------------------
    one_quote_two_ids = [{
        "statement": "Items R15 and R16 share the same evidence text regarding the Ossa site register.",
        "quotes": [lines[0][:200]],
    }]
    g, r, _ = ground(one_quote_two_ids)
    require(not g and len(r) == 1, "a_comparative_observation_quoting_one_twin_is_refused")
    require(r[0]["reason"] == "unsupported_identifiers", "it_is_refused_for_the_unsupported_identifier")
    require("r16" in [i.lower() for i in r[0].get("identifiers", [])],
            "the_ungrounded_twin_is_named_as_the_unsupported_identifier")

    # the evidence span alone, with no identifier at all, is also still refused
    evidence_only = [{
        "statement": "Items R15 and R16 both rest on the Ossa site register.",
        "quotes": ['"evidence": ' + lines[0].split('"evidence": ')[1][:150]],
    }]
    g, r, _ = ground(evidence_only)
    require(not g and r[0]["reason"] == "unsupported_identifiers",
            "quoting_only_shared_evidence_still_grounds_no_identifier")

    # --- 2. the disciplined shapes succeed -----------------------------------------------------------------------
    per_record = [
        {"statement": "The record states a proposition about the eastern turbine and an evidence passage.",
         "quotes": [lines[0][:200]]},
        {"statement": "The record states a proposition about every turbine and an evidence passage.",
         "quotes": [lines[1][:200]]},
    ]
    g, r, _ = ground(per_record)
    require(len(g) == 2 and not r, "separate_per_record_observations_ground_successfully")
    require([o["obs_id"] for o in g] == ["O1", "O2"], "each_record_gets_its_own_observation")

    # a comparison IS allowed when every identifier it names is grounded by its own quotes
    both_quoted = [{
        "statement": "Items R15 and R16 carry the same evidence passage.",
        "quotes": [lines[0][:200], lines[1][:200]],
    }]
    g, r, _ = ground(both_quoted)
    require(len(g) == 1 and not r, "a_comparison_grounding_both_identifiers_is_accepted")
    require(len(g[0]["quotes"]) == 2 and all(q["found"] for q in g[0]["quotes"]),
            "both_records_are_quoted_and_located")

    # --- 3. nothing about validation moved -----------------------------------------------------------------------
    fabricated = [{"statement": "The record mentions item R99.", "quotes": [lines[0][:200]]}]
    g, r, _ = ground(fabricated)
    require(not g and r[0]["reason"] == "unsupported_identifiers", "an_invented_identifier_is_still_refused")
    missing_quote = [{"statement": "The record shows something.", "quotes": ["text that is not in the document"]}]
    g, r, _ = ground(missing_quote)
    require(not g and r[0]["reason"] == "quote_not_found_in_document", "a_quote_that_is_not_there_is_still_refused")
    stitched = [{"statement": "The record shows something.",
                 "quotes": [lines[0][:40] + " ... " + lines[0][-40:]]}]
    g, r, _ = ground(stitched)
    require(not g and r[0]["reason"] == "stitched_quote", "a_stitched_quote_is_still_refused")
    too_many = [{"statement": "The record shows something.",
                 "quotes": [lines[0][:60], lines[1][:60], lines[2][:60], lines[3][:60]]}]
    g, r, _ = ground(too_many)
    require(not g and r[0]["reason"] == "too_many_quotes", "the_quote_count_limit_is_unchanged")

    # --- 4. the instruction is form only, and carries nothing from any experiment --------------------------------
    added = hier.OBSERVE_PROMPT.replace(base.OBSERVE_PROMPT.split(
        "Also list questions this part raises but does not answer.")[0], "")
    require(hier.OBSERVE_PROMPT != base.OBSERVE_PROMPT, "the_candidate_has_its_own_observation_prompt")
    require(base.OBSERVE_PROMPT.count("{chunk}") == hier.OBSERVE_PROMPT.count("{chunk}") == 1,
            "the_prompt_still_shows_exactly_one_passage")
    for leak in ("G-CORROB1", "G-EVID1", "R15", "R16", "D4", "corpus", "gold", "scorer", "disposition",
                 "unsafe", "verdict", "supports", "contradicts", "partial"):
        require(leak not in added, f"the_added_instruction_names_no_experiment_material:{leak}")
    for required_phrase in ("only the records and identifiers its own quotes establish",
                            "a separate observation for each", "belong to a later stage"):
        require(required_phrase in hier.OBSERVE_PROMPT, f"the_instruction_states_the_rule:{required_phrase[:28]}")

    # --- 5. the reviewer's own limits are untouched ---------------------------------------------------------------
    require(base.CONTRACT_VERSION == "v2731.8", "the_baseline_reviewer_is_unchanged")
    require(hier.CONTRACT_VERSION == "v2735.0", "the_repair_carries_its_own_contract_version")
    require(base.MAX_QUOTE_CHARS == 240 and base.MIN_QUOTE_CHARS == 4, "quote_limits_are_unchanged")
    require(base.MAX_OBSERVATIONS_PER_CHUNK == 8, "the_per_chunk_observation_limit_is_unchanged")
    require(base.MAX_QUOTES_PER_OBSERVATION == 3, "the_per_observation_quote_limit_is_unchanged")
    require(hier.OBSERVE_GROUNDING_ATTEMPTS == 2, "the_retry_limit_is_unchanged")
    require(hier.MAX_GROUPS_PER_ROUND == 48, "the_group_count_bound_is_unchanged")
    require(hier.MIN_SYNTHESISED_REPRESENTATION == 0.5, "the_representation_floor_is_unchanged")
    require(base.REQUIRED_ROLES == ("design", "corpus", "raw_outputs"), "required_roles_are_unchanged")
    require("OBSERVE_PROMPT_V2" in hier.template_digests(), "the_new_prompt_is_recorded_in_provenance")

    # --- 6. a whole review over a twin-heavy package still behaves ------------------------------------------------
    with tempfile.TemporaryDirectory(prefix="v2733-twin-") as tmp:
        import reviewer_capacity_qualification as q

        work = Path(tmp)
        pkg = work / "pkg"
        q.build_package(pkg, 6)
        runtime = work / "rt"
        runtime.mkdir(parents=True, exist_ok=True)
        art = hier.review_experiment(pkg, call_model=q.deterministic_stub(), runtime_root_path=runtime,
                                     identity={"model": "stub", "provider": "test", "context_size": 8192,
                                               "resolved_config_sha256": "0" * 64}, release_model=False)
        require(art["status"] == "complete", "a_full_review_still_completes_under_the_new_instruction")
        require(art["coverage"]["required_coverage"] == 1.0, "coverage_is_unaffected")
        require(art["provenance"]["prompt_templates_sha256"].get("OBSERVE_PROMPT_V2"),
                "the_artifact_records_which_observation_prompt_produced_it")

    failed = [name for name, ok in CHECKS if not ok]
    print(json.dumps({"suite": "v2733.5.0-twin-record", "checks": len(CHECKS),
                      "passed": len(CHECKS) - len(failed), "failed": failed[:12]}, indent=1))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
