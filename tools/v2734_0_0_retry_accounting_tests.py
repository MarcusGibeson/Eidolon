"""v2734.0.0 - retry totals derived from the stages that actually ran.

G-CORROB1 independent review attempt 3 (b6e64bc963efc2b9) reported ``runtime_accounting.retries = 0`` after executing
twenty-seven retries.

Two different things were both being called retries. A *repair* attempt happens inside one stage: ``base._ask``
re-asks the identical input once when a reply fails to arrive, truncates or will not parse, and that ask carries
``attempt == 2``. A *grounding* retry is a whole new stage (``observe:D13:63:retry1``) given to a part whose reply
parsed cleanly but grounded nothing; its ``attempt`` starts at 1 again because it is a fresh ask.

The summary counted ``attempt > 1``, so it reported repair attempts under the name "retries" and grounding retries
not at all. Attempt 3 ran twenty-seven grounding retries and no repairs, and so reported zero. ``recovered_stages``
was empty for a related reason: it looked for one stage id that was both accepted and not accepted.

Per-part ``attempts`` / ``grounding_attempts`` were correct throughout. Only the summary block was wrong, and the
summary block is what a reader skims.

These tests pin the derived totals. Nothing here changes review semantics, grounding, or coverage, and the historical
artifacts are read but never written.

    python tools/v2734_0_0_retry_accounting_tests.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for value in (str(ROOT), str(ROOT / "tools"), str(ROOT / "conscious_agent")):
    if value not in sys.path:
        sys.path.insert(0, value)

import experiment_review_hierarchical as hier  # noqa: E402

CHECKS: list[tuple[str, bool]] = []

ATTEMPT3 = Path("C:/Users/marcu/AppData/Local/Eidolon/data/research_reviews/b6e64bc963efc2b9/review.json")


def require(condition: bool, name: str) -> None:
    CHECKS.append((name, bool(condition)))


def call(stage: str, accepted: bool = True) -> dict:
    return {"stage": stage, "accepted": accepted, "attempt": 1, "rejection": None, "error": None}


def part(stage: str, grounding_attempts: int, reviewed: bool) -> dict:
    return {"stage": stage, "grounding_attempts": grounding_attempts, "attempts": grounding_attempts,
            "reviewed": reviewed}


def main() -> int:
    # --- 1. a clean run reports no retries ---------------------------------------------------------------------
    clean = hier.retry_totals([call("observe:D1:1"), call("observe:D1:2")],
                              [part("observe:D1:1", 1, True), part("observe:D1:2", 1, True)])
    require(clean["retries"] == 0, "no_retry_reports_zero")
    require(clean["retry_stages"] == [], "no_retry_names_no_stages")
    require(clean["recovered_stages"] == [], "no_retry_recovers_nothing")
    require(clean["units_retried"] == 0, "no_retry_counts_no_units")
    require(clean["accounting_contract"] == "retry-accounting.v2", "the_totals_declare_their_contract")

    # --- 2. one retry that recovered ---------------------------------------------------------------------------
    one = hier.retry_totals([call("observe:D1:1"), call("observe:D1:2", accepted=True),
                             call("observe:D1:2:retry1")],
                            [part("observe:D1:1", 1, True), part("observe:D1:2", 2, True)])
    require(one["retries"] == 1, "one_retry_reports_one")
    require(one["retry_stages"] == ["observe:D1:2:retry1"], "the_retry_stage_is_named")
    require(one["recovered_stages"] == ["observe:D1:2"], "a_recovered_unit_is_named_by_its_base_stage")
    require(one["units_retried_without_recovery"] == [], "a_recovered_unit_is_not_also_reported_as_unrecovered")

    # --- 3. several retries across several units ---------------------------------------------------------------
    many = hier.retry_totals(
        [call("observe:D1:1"), call("observe:D1:1:retry1"), call("observe:D2:1"), call("observe:D2:1:retry1"),
         call("observe:D3:7"), call("observe:D3:7:retry1"), call("observe:D4:1")],
        [part("observe:D1:1", 2, True), part("observe:D2:1", 2, True), part("observe:D3:7", 2, False),
         part("observe:D4:1", 1, True)])
    require(many["retries"] == 3, "three_retry_stages_report_three")
    require(many["units_retried"] == 3, "three_distinct_units_retried")
    require(many["recovered_stages"] == ["observe:D1:1", "observe:D2:1"], "only_units_that_succeeded_are_recovered")

    # --- 4. a retry that failed is counted, and never counted as a recovery -------------------------------------
    require(many["units_retried_without_recovery"] == ["observe:D3:7"],
            "a_retry_that_still_grounded_nothing_is_reported_as_unrecovered")
    require("observe:D3:7" not in many["recovered_stages"], "a_failed_retry_is_never_a_recovery")
    require("observe:D3:7:retry1" in many["retry_stages"], "a_failed_retry_still_counts_as_an_executed_retry")

    # --- 5. grounding retries and in-stage repair attempts are counted separately ------------------------------
    # A grounding retry is a fresh stage with attempt == 1; a repair attempt is a second ask inside one stage.
    # Conflating them is what hid twenty-seven retries behind a zero.
    require(all(c["attempt"] == 1 for c in [call("x"), call("x:retry1")]), "the_fixture_matches_how_stages_are_written")
    require(many["repair_attempts"] == 0, "grounding_retries_are_not_counted_as_repairs")
    repaired = hier.retry_totals(
        [call("observe:D1:1"), {**call("observe:D1:1"), "attempt": 2}, call("observe:D2:1"),
         call("observe:D2:1:retry1")],
        [part("observe:D1:1", 1, True), part("observe:D2:1", 2, True)])
    require(repaired["repair_attempts"] == 1, "an_in_stage_repair_is_counted_as_a_repair")
    require(repaired["stages_with_repair_attempts"] == ["observe:D1:1"], "the_repaired_stage_is_named")
    require(repaired["retries"] == 1, "a_repair_is_not_counted_as_a_grounding_retry")
    require(repaired["recovered_stages"] == ["observe:D2:1"], "recovery_still_follows_grounding_not_repair")

    # --- 6. base-unit naming -----------------------------------------------------------------------------------
    require(hier.base_unit_of("observe:D13:63:retry1") == "observe:D13:63", "a_retry_stage_maps_to_its_unit")
    require(hier.base_unit_of("observe:D13:63") == "observe:D13:63", "a_base_stage_maps_to_itself")
    require(hier.base_unit_of("observe:D13:63:retry11") == "observe:D13:63", "a_double_digit_retry_maps_back")
    require(hier.base_unit_of("final:second_half") == "final:second_half", "an_unrelated_stage_is_left_alone")

    # --- 7. per-part accounting stays the source of truth for grounding ----------------------------------------
    # The summary is derived from per-part records; it must never contradict them.
    coverage = [part("observe:D1:1", 2, True), part("observe:D1:2", 1, True), part("observe:D2:1", 3, False)]
    totals = hier.retry_totals([call("observe:D1:1"), call("observe:D1:1:retry1"), call("observe:D2:1"),
                                call("observe:D2:1:retry1"), call("observe:D2:1:retry2")], coverage)
    require(totals["retries"] == 3, "executed_retries_match_the_ledger")
    require(set(totals["recovered_stages"]) == {"observe:D1:1"}, "recovery_follows_the_per_part_reviewed_flag")
    require(all(p["grounding_attempts"] >= 1 for p in coverage), "per_part_accounting_is_untouched")

    # --- 8. the real attempt 3 artifact, read only ---------------------------------------------------------------
    if ATTEMPT3.is_file():
        before = ATTEMPT3.read_bytes()
        art = json.loads(before.decode("utf-8"))
        real = hier.retry_totals(art["ledger"], art["coverage"]["parts"])
        require(real["retries"] == 27, "attempt3_really_ran_twenty_seven_retries")
        require(art["runtime_accounting"]["retries"] == 0, "the_historical_artifact_still_reports_its_own_zero")
        require(len(real["recovered_stages"]) == 26, "twenty_six_of_those_retries_recovered")
        require(real["units_retried_without_recovery"] == ["observe:D13:63"],
                "the_one_retry_that_never_recovered_is_the_blocking_unit")
        require(real["repair_attempts"] == 0,
                "attempt3_ran_no_in_stage_repairs_which_is_why_the_old_counter_read_zero")
        require(ATTEMPT3.read_bytes() == before, "reading_the_historical_artifact_does_not_change_it")

    failed = [name for name, ok in CHECKS if not ok]
    print(json.dumps({"suite": "v2734.0.0-retry-accounting", "checks": len(CHECKS),
                      "passed": len(CHECKS) - len(failed), "failed": failed[:12]}, indent=1))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
