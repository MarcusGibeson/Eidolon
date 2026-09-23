"""v2732.2.0 - adversarial tests for the bounded observation-grounding retry.

Reproduces the failure shape that stopped the first G-EVID1 review (review 69d4f0af2c00557f) on synthetic Q-CAP
material, then proves the retry recovers a transient slip without admitting a single unsupported observation.

No G-EVID1 content is used. The failure shapes below are generic model-output defects: ellipsis-stitched quotes and
identifiers named in a statement but absent from its quotes.

    python tools/v2732_2_0_grounding_retry_tests.py
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
import reviewer_capacity_qualification as q  # noqa: E402

CHECKS: list[tuple[str, bool]] = []
IDENT = {"model": "stub", "provider": "test", "context_size": 8192, "resolved_config_sha256": "0" * 64}
TARGET = "part 3 of"          # the part every failing stub sabotages


def require(condition: bool, name: str) -> None:
    CHECKS.append((name, bool(condition)))


def _chunk(prompt: str) -> str:
    """The passage the observe prompt is showing, so a stub can quote real spans out of it."""
    import re

    match = re.search(r"part \d+ of \d+\.\n---\n(.*)\n---\n", prompt, re.S)
    return match.group(1) if match else ""


def stitched_reply(prompt: str):
    """The D4:8 / D5:14 shape: real fragments joined with ellipses, plus one over-claimed identifier."""
    lines = [l for l in _chunk(prompt).split("\n") if l.startswith("ref=")]
    obs = []
    for line in lines[:7]:
        head, tail = line[:28], line[40:80]
        obs.append({"statement": "the record shows alpha bravo charlie delta",
                    "quotes": [f"{head} ... {tail}"]})
    if lines:
        obs.append({"statement": "the records run from item S001 through item S999 in this part",
                    "quotes": [lines[0][:60]]})
    return json.dumps({"observations": obs, "open_questions": []}), {"metrics": {"eval_count": 400}}


def run(pkg: Path, call_model, runtime: Path):
    runtime.mkdir(parents=True, exist_ok=True)
    return hier.review_experiment(pkg, call_model=call_model, runtime_root_path=runtime, identity=IDENT)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="v2732-retry-") as tmp:
        work = Path(tmp)
        pkg = work / "pkg"
        q.build_package(pkg, 19)
        good = q.deterministic_stub()

        # --- 1. the retry is bounded and its preface cannot coach ----------------------------------------------
        require(hier.OBSERVE_GROUNDING_ATTEMPTS == 2, "the_retry_limit_is_strict_and_small")
        pre = hier.GROUNDING_RETRY_PREFACE
        require(isinstance(pre, str) and pre, "the_retry_preface_is_a_fixed_constant")
        for leak in ("G-EVID1", "I27", "I51", "unsafe", "disposition", "gold", "scorer", "verdict", "governing"):
            require(leak.lower() not in pre.lower(),
                    f"the_preface_does_not_mention_experiment_material:{leak}")
        require("relation" not in pre and "supports" not in pre,
                "the_preface_names_no_semantic_category_the_model_should_choose")
        require("ellipses" in pre and "identifier" in pre,
                "the_preface_restates_only_the_mechanical_form_already_required")

        # --- 2. the original failure reproduces: a persistent stitcher fails closed -----------------------------
        def always_bad(prompt: str, max_tokens: int):
            if '"observations"' in prompt and TARGET in prompt:
                return stitched_reply(prompt)
            return good(prompt, max_tokens)

        art = run(pkg, always_bad, work / "rt-bad")
        bad_parts = [p for p in art["coverage"]["parts"] if p["grounded_observations"] == 0]
        require(art["status"] == "incomplete", "a_persistent_stitcher_still_fails_the_review_closed")
        require(any(m["kind"] == "required_part_not_reviewed" for m in art["coverage"]["missing"]),
                "the_unreviewable_part_is_named_exactly_as_before")
        require(all(m["reason"] == "no_grounded_observations"
                    for m in art["coverage"]["missing"] if m["kind"] == "required_part_not_reviewed"),
                "the_reason_is_still_no_grounded_observations")
        require(not art["review"], "no_analysis_is_produced_when_a_required_part_grounds_nothing")
        require(not art["hierarchy"]["part_statements"], "synthesis_is_still_skipped_entirely")
        require(bad_parts and bad_parts[0]["grounding_attempts"] == hier.OBSERVE_GROUNDING_ATTEMPTS,
                "the_failing_part_used_every_permitted_attempt_and_no_more")

        # every rejection is a real grounding failure, not a silent drop
        reasons = {r["reason"] for r in art["rejected_observations"]}
        require(reasons <= {"stitched_quote", "unsupported_identifiers", "quote_not_found_in_document"},
                "rejections_are_genuine_grounding_failures")
        require(any(r["reason"] == "stitched_quote" for r in art["rejected_observations"]),
                "the_stitched_quote_defect_is_reproduced")
        require(any(r["reason"] == "unsupported_identifiers" for r in art["rejected_observations"]),
                "the_unsupported_identifier_defect_is_reproduced")

        # --- 3. both attempts are recorded, nothing is quietly replaced ----------------------------------------
        stages = [x["stage"] for x in art["ledger"]]
        retry_stages = [s for s in stages if ":retry" in s]
        require(retry_stages, "the_retry_attempt_appears_in_the_ledger_as_its_own_stage")
        require(len(retry_stages) == len(set(retry_stages)), "each_retry_stage_is_recorded_once")
        first_round = [r for r in art["rejected_observations"] if r["part"] == bad_parts[0]["part"]]
        require(len(first_round) >= 2 * 7, "rejected_observations_from_BOTH_attempts_are_preserved")
        require(len({r["rej_id"] for r in art["rejected_observations"]}) == len(art["rejected_observations"]),
                "rejected_observation_ids_stay_unique_across_attempts")

        # --- 4. a transient slip now recovers -------------------------------------------------------------------
        seen: dict[str, int] = {}

        def bad_once(prompt: str, max_tokens: int):
            if '"observations"' in prompt and TARGET in prompt:
                key = "target"
                seen[key] = seen.get(key, 0) + 1
                if seen[key] == 1:
                    return stitched_reply(prompt)
            return good(prompt, max_tokens)

        art2 = run(pkg, bad_once, work / "rt-once")
        require(art2["status"] == "complete", "a_transient_slip_now_recovers_on_the_retry")
        require(art2["coverage"]["required_coverage"] == 1.0, "full_required_coverage_is_restored")
        require(not art2["coverage"]["missing"], "nothing_is_missing_after_a_successful_retry")
        recovered = [p for p in art2["coverage"]["parts"] if p.get("grounding_attempts", 1) > 1]
        require(recovered and recovered[0]["grounded_observations"] > 0,
                "the_recovered_part_grounded_real_observations_on_the_second_attempt")
        require(any(r["reason"] == "stitched_quote" for r in art2["rejected_observations"]),
                "the_failed_first_attempt_is_still_preserved_as_evidence")
        require(not art2["coverage"]["levels"]["architecture"]["silently_dropped"],
                "the_retry_introduces_no_silent_loss")

        # --- 5. the retry admits nothing that grounding would refuse -------------------------------------------
        for o in art2["grounded_observations"]:
            for quote in o["quotes"]:
                require(quote["found"] is True, f"every_accepted_quote_is_located:{o['obs_id']}")
                require("..." not in quote["text"] and "…" not in quote["text"],
                        f"no_accepted_quote_is_stitched:{o['obs_id']}")
        texts = {d["doc_id"]: (pkg / d["path"]).read_text(encoding="utf-8")
                 for d in art2["provenance"]["documents"]}
        for o in art2["grounded_observations"]:
            for quote in o["quotes"]:
                span = texts[o["doc_id"]][quote["char_start"]:quote["char_end"]]
                require(span == quote["text"], f"every_accepted_quote_relocates_byte_exactly:{o['obs_id']}")

        # --- 6. parts that already succeeded are never retried --------------------------------------------------
        singles = [p for p in art2["coverage"]["parts"] if p["grounded_observations"] > 0
                   and p.get("grounding_attempts", 1) == 1]
        require(len(singles) >= 15, "parts_that_grounded_first_time_were_not_retried")
        stages2 = [x["stage"] for x in art2["ledger"]]
        require(all(f"{p['stage']}:retry1" not in stages2 for p in singles),
                "no_retry_stage_exists_for_an_already_accepted_part")
        retried_parts = {s.split(":retry")[0] for s in stages2 if ":retry" in s}
        require(len(retried_parts) == 1, "exactly_one_part_was_retried")

        # --- 7. a schema-invalid reply is still handled by the frozen repair path, not by this retry -----------
        def broken(prompt: str, max_tokens: int):
            if '"observations"' in prompt and TARGET in prompt:
                return "not json", {"metrics": {"eval_count": 5}}
            return good(prompt, max_tokens)

        art3 = run(pkg, broken, work / "rt-broken")
        require(art3["status"] == "incomplete", "an_unparseable_part_still_fails_closed")
        require(any(m["kind"] == "required_part_not_reviewed" for m in art3["coverage"]["missing"]),
                "an_unparseable_required_part_is_named")

        # --- 8. the baseline and the grounding contract are untouched -------------------------------------------
        require(base.CONTRACT_VERSION == "v2731.8", "the_baseline_contract_is_unchanged")
        require(hier.CONTRACT_VERSION == "v2735.0", "the_repair_carries_its_own_contract_version")
        require(base.MIN_QUOTE_CHARS == 4 and base.MAX_QUOTE_CHARS == 240,
                "quote_limits_are_unchanged")
        require(base.MAX_OBSERVATIONS_PER_CHUNK == 8, "the_per_chunk_observation_limit_is_unchanged")
        require(base.REQUIRED_ROLES == ("design", "corpus", "raw_outputs"), "required_roles_are_unchanged")
        src = (ROOT / "conscious_agent" / "experiment_review_hierarchical.py").read_text(encoding="utf-8")
        require("def ground_observations" not in src and "def unsupported_identifiers" not in src,
                "the_repair_does_not_reimplement_or_override_grounding")

    failed = [name for name, ok in CHECKS if not ok]
    print(json.dumps({"suite": "v2732.2.0-grounding-retry", "checks": len(CHECKS),
                      "passed": len(CHECKS) - len(failed), "failed": failed}, indent=1))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
