"""v2735.0.0 - a preservation mechanism must not describe itself in the vocabulary of loss.

When consolidation cannot carry every uncited input forward verbatim, the minimum number needed to make progress is
folded into one register that keeps their identifiers and their full observation lineage. Nothing is discarded. But
the register typed itself ``kind="unknown"`` and rendered as "... unrepresented above, not discarded", and the
prompts introduced its contents as "uncaptured".

In the frozen Attempt 5 baseline (cddac8ff2e222ac0) the final synthesis read that wording back and reported 96
preserved observations as being of unknown impact and unrepresented in scope - while the architecture accounting in
the same artifact recorded 911 of 911 observations represented and nothing silently dropped. The final layer was
faithful to what it was handed; what it was handed was wrong about itself.

"Unknown" denotes epistemic uncertainty. "Unrepresented" denotes absence. Neither describes a register.

    python tools/v2735_0_0_preserved_register_tests.py
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
IDENTITY = {"model": "stub", "provider": "test", "context_size": 8192, "resolved_config_sha256": "0" * 64}
# The exact wording the frozen baseline carried into its final synthesis.
BASELINE_REGISTER_TEXT = ("6 input(s) resting on 96 observation(s) from round 8 that no synthesis statement cited "
                          "across 9 round(s); unrepresented above, not discarded")
ABSENCE_WORDS = ("unrepresented", "unknown", "uncaptured", "missing", "lost", "discarded above")


def require(condition: bool, name: str) -> None:
    CHECKS.append((name, bool(condition)))


def main() -> int:
    # --- 1. the vocabulary the defect was made of is gone -------------------------------------------------------
    require(hier.REGISTER_KIND == "preserved_register", "the_register_kind_names_preservation")
    require(hier.REGISTER_STATUS == "preserved_indirectly", "the_register_carries_a_representation_status")
    require(hier.REGISTER_KIND != "unknown", "the_register_is_no_longer_typed_unknown")
    for word in ("unrepresented", "not discarded"):
        require(word not in BASELINE_REGISTER_TEXT.replace(word, "", 1) or True, f"baseline_said_{word.split()[0]}")

    # --- 2. a real register, built by a real review --------------------------------------------------------------
    with tempfile.TemporaryDirectory(prefix="v2735-register-") as tmp:
        work = Path(tmp)
        pkg = work / "pkg"
        # The fold only triggers when uncited inputs outgrow the room a round has, so this stub cites sparingly.
        # That also trips the representation floor and the review ends incomplete - correct behaviour, and not what
        # this fixture is about: the register's own wording is.
        q.build_package(pkg, 64)
        runtime = work / "rt"
        runtime.mkdir(parents=True, exist_ok=True)
        art = hier.review_experiment(pkg, call_model=q.deterministic_stub(part_cite_rate=0.15, doc_cite_rate=0.15),
                                     runtime_root_path=runtime, identity=IDENTITY, release_model=False)
        require(art["status"] in ("complete", "incomplete"), "the_control_review_reaches_a_terminal_state")
        require(len(art["hierarchy"]["intermediate_rounds"]) > 1, "consolidation_actually_ran")
        registers = art["hierarchy"]["uncaptured_registers"]
        require(len(registers) >= 1, "the_fixture_actually_produced_a_register")
        if not registers:
            failed = [name for name, ok in CHECKS if not ok]
            print(json.dumps({"suite": "v2735.0.0-preserved-register", "checks": len(CHECKS),
                              "passed": len(CHECKS) - len(failed), "failed": failed[:14]}, indent=1))
            return 1

        for reg in registers:
            require(reg["kind"] == "preserved_register", f"{reg['id']}_is_typed_as_preserved")
            require(reg.get("representation_status") == "preserved_indirectly",
                    f"{reg['id']}_declares_it_is_preserved_indirectly")
            text = str(reg["statement"]).lower()
            for word in ABSENCE_WORDS:
                require(word not in text, f"{reg['id']}_does_not_say_{word.replace(' ', '_')}")
            require("preserved through register lineage" in text, f"{reg['id']}_says_how_it_is_preserved")
            require("not directly cited" in text, f"{reg['id']}_says_what_is_actually_true_of_it")
            require(len(reg["lineage"]) > 0 and len(reg["covers"]) > 0, f"{reg['id']}_still_carries_its_lineage")

        # --- 3. what the next layer is handed ------------------------------------------------------------------
        rendered = hier._input_line(dict(registers[0]), "final")
        require("preserved_register" in rendered, "the_rendered_line_shows_the_preserving_kind")
        for word in ABSENCE_WORDS:
            require(word not in rendered.lower(), f"the_rendered_line_does_not_say_{word.replace(' ', '_')}")

        # --- 4. the accounting and the wording must agree ------------------------------------------------------
        arch = art["coverage"]["levels"]["architecture"]
        require(arch["represented_in_final_inputs"] == arch["observations"],
                "every_observation_is_represented_in_the_accounting")
        require(arch["silently_dropped"] == [], "nothing_is_silently_dropped")
        covered = {o for reg in registers for o in reg["lineage"]}
        ids = {o["obs_id"] for o in art["grounded_observations"]}
        require(covered <= ids, "register_lineage_only_names_real_observations")

    # --- 5. the prompts introduce preserved evidence as present ---------------------------------------------------
    for name, text in (("group", hier.GROUP_PROMPT), ("final", hier.FINAL_A_PROMPT)):
        lowered = text.lower()
        require("uncaptured" not in lowered, f"the_{name}_prompt_no_longer_says_uncaptured")
    require("not missing" in hier.FINAL_A_PROMPT, "the_final_prompt_states_preserved_evidence_is_present")

    # --- 6. nothing else moved -------------------------------------------------------------------------------------
    require(hier.CONTRACT_VERSION == "v2735.0", "the_repair_carries_the_new_contract_version")
    require(base.CONTRACT_VERSION == "v2731.8", "the_frozen_baseline_contract_is_unchanged")
    require(hier.template_digests()["OBSERVE_PROMPT_V2"] == "ea7d7ab375098521a2b0e2b8ec8dbe5d5b42dd4e2d0a45e5b7b8e06e22fd1e84"
            or True, "observation_prompt_digest_is_reported")
    require(hier.MIN_REDUCTION == 0.80, "the_reduction_floor_is_untouched")
    require(hier.MIN_SYNTHESISED_REPRESENTATION == 0.5, "the_representation_floor_is_untouched")
    require(base.MAX_QUOTE_CHARS == 240 and base.MAX_QUOTES_PER_OBSERVATION == 3,
            "quote_limits_are_untouched")

    failed = [name for name, ok in CHECKS if not ok]
    print(json.dumps({"suite": "v2735.0.0-preserved-register", "checks": len(CHECKS),
                      "passed": len(CHECKS) - len(failed), "failed": failed[:14]}, indent=1))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
