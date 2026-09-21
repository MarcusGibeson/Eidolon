"""v2733.2.0 - qualify the hierarchical reviewer at the repaired review-package scale (140 parts).

The G-CORROB1 review package is 140 parts. The hierarchy had been qualified deterministically only to 64, and the
first review never exercised its synthesis stages because it failed closed in the observation pass. At 140 parts with
realistic model behaviour the consolidation tree needs 41 groups in its first round against a limit of 32, so the
review would have spent roughly fourteen hours observing and then produced nothing.

This suite proves what a changed bound must satisfy before it is adopted, and that everything else stays where it was.

    python tools/v2733_2_0_scale_140_qualification_tests.py
"""

import json
import math
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
SCALE = 140
REAL_OBS_PER_PART = 8   # the first review grounded close to the per-chunk cap; this is the worst case for fan-out


def require(condition: bool, name: str) -> None:
    CHECKS.append((name, bool(condition)))


def run(band: str, work: Path, **over):
    return q.qualify(SCALE, work_dir=work, guard_source=False, reviewer=hier,
                     obs_per_part=REAL_OBS_PER_PART, **q.SENSITIVITY[band], **over)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="scale140-") as tmp:
        work = Path(tmp)

        # --- 1. the nominal 140-part case converges -----------------------------------------------------------
        nominal = run("nominal", work / "nominal")
        m = nominal["measurements"]
        it, fb = m["intermediate"], m["final_budget"]
        require(m["status"] == "complete", "the_nominal_140_part_case_completes")
        require(m["part_coverage"]["full"], "full_required_part_coverage_at_140_parts")
        require(it["converged"], "the_consolidation_tree_converges_at_140_parts")
        require(not m["observation_preservation"]["silently_dropped"], "no_observation_is_silently_dropped")
        require(m["uncaptured_accounting"]["balances"], "uncaptured_accounting_balances_at_140_parts")
        require(m["relocatability"]["relocatable"], "every_quote_relocates_exactly_at_140_parts")
        require(m["identifier_validity"]["valid"], "identifiers_stay_valid_at_140_parts")
        require(m["synthesis"]["complete"], "both_final_halves_are_accepted_at_140_parts")

        # --- 2. the configured round limit remains sufficient -------------------------------------------------
        require(it["round_count"] <= hier.MAX_ROUNDS,
                "the_round_limit_still_covers_the_nominal_case")
        require(it["round_count"] < hier.MAX_ROUNDS, "the_round_limit_keeps_headroom_at_this_scale")

        # --- 3. input and character bounds stay enforced ------------------------------------------------------
        require(fb["inputs"] <= hier.FINAL_MAX_INPUTS, "the_final_input_count_bound_holds_at_140_parts")
        require(fb["chars"] <= hier.FINAL_INPUT_BOUND_CHARS, "the_final_character_bound_holds_at_140_parts")
        require(fb["chars"] <= base.FINAL_INPUT_BUDGET_CHARS, "the_final_block_stays_inside_the_model_budget")

        # --- 4. no synthesis unit silently exceeds its bounded contract ---------------------------------------
        widest = max((r["units"] for r in it["rounds"]), default=0)
        require(widest <= hier.MAX_GROUPS_PER_ROUND,
                "no_round_is_wider_than_the_group_count_bound")
        require(all(r["inputs"] >= r["surviving"] for r in it["rounds"]), "every_round_reduces")
        raw = json.loads((work / "nominal" / f"runtime-{SCALE}" / base.REVIEW_AREA /
                          nominal["review_id"] / "review.json").read_text(encoding="utf-8"))
        for unit in raw["hierarchy"]["part_units"] + raw["hierarchy"]["document_units"]:
            require(len(unit["inputs"]) <= max(base.DOCUMENT_UNIT_MAX_INPUTS, base.MAX_OBSERVATIONS_PER_CHUNK),
                    f"a_synthesis_unit_stays_inside_its_input_bound:{unit['unit_id']}")
        for row in raw["coverage"]["levels"]["intermediate_synthesis"]["rounds"]:
            require(row["units"] <= hier.MAX_GROUPS_PER_ROUND, f"round_width_bound_holds:{row['round']}")
        for statement in raw["hierarchy"]["group_statements"]:
            require(len(statement["statement"]) <= base.MAX_STATEMENT_CHARS,
                    f"a_group_statement_stays_inside_its_character_bound:{statement['id']}")

        # --- 5. out-of-envelope behaviour still fails closed ---------------------------------------------------
        pessimistic = run("pessimistic", work / "pessimistic")
        pm = pessimistic["measurements"]
        require(pm["status"] != "complete", "a_model_that_cites_almost_nothing_still_fails_closed_at_140_parts")
        require(pm["mechanical_verification"]["missing"], "the_out_of_envelope_case_names_its_reason")

        # --- 6. the floors and acceptance rules are untouched --------------------------------------------------
        require(hier.MIN_SYNTHESISED_REPRESENTATION == 0.5, "the_representation_floor_is_unchanged")
        require(hier.MIN_REDUCTION == 0.80, "the_per_round_reduction_floor_is_unchanged")
        require(hier.GROUP_MAX_INPUTS == 12, "the_group_input_bound_is_unchanged")
        require(hier.GROUP_MAX_STATEMENTS == 4, "the_group_statement_bound_is_unchanged")
        require(hier.FINAL_MAX_INPUTS == 32, "the_final_input_bound_is_unchanged")
        require(hier.MAX_ROUNDS == 12, "the_round_limit_is_unchanged")
        require(hier.OBSERVE_GROUNDING_ATTEMPTS == 2, "the_retry_limit_is_unchanged")
        require(base.CONTRACT_VERSION == "v2731.8", "the_baseline_reviewer_is_unchanged")
        require(base.MAX_QUOTE_CHARS == 240 and base.MIN_QUOTE_CHARS == 4, "quote_limits_are_unchanged")
        require(base.REQUIRED_ROLES == ("design", "corpus", "raw_outputs"), "required_roles_are_unchanged")
        require(m["disagreement_preservation"]["statement_kinds"], "statement_kinds_are_still_recorded")

        # --- 7. the bound is no larger than the evidence needs -------------------------------------------------
        needed = max((r["units"] for r in it["rounds"]), default=0)
        require(needed > 0, "the_measurement_produced_a_real_width")
        require(hier.MAX_GROUPS_PER_ROUND >= needed, "the_bound_covers_the_measured_width")
        headroom = hier.MAX_GROUPS_PER_ROUND * hier.GROUP_MAX_INPUTS
        first_round_inputs = it["rounds"][0]["inputs"] if it["rounds"] else 0
        require(headroom >= first_round_inputs, "the_bound_covers_the_measured_first_round_input_count")
        require(hier.MAX_GROUPS_PER_ROUND <= 48,
                "the_bound_is_not_enlarged_beyond_the_measured_need_plus_a_small_margin")
        require(math.ceil(first_round_inputs / hier.GROUP_MAX_INPUTS) == needed,
                "round_width_is_exactly_the_input_count_divided_by_the_group_size")

    failed = [name for name, ok in CHECKS if not ok]
    print(json.dumps({"suite": "v2733.2.0-scale-140-qualification", "checks": len(CHECKS),
                      "passed": len(CHECKS) - len(failed), "failed": failed[:10]}, indent=1))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
