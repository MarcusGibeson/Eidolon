"""v2735.1.0 - compression may reduce wording; it may not reduce semantic-role provenance.

The frozen Attempt 5 baseline (cddac8ff2e222ac0) lost a distinction in one merge. GS151 reported a measured gate
result; GS154 reported what the architecture requires. They were glued into GS201, the words "Architecture
specifies" were dropped as redundant prose, and the stripped sentence travelled six consolidation rounds unchanged
until the final layer - reading a bare behavioural claim beside failed gates - filed it under
possible_model_or_reasoning_failures.

Two invariants come out of that, and they are not the same invariant:

* traceability - no role disappears from lineage;
* fidelity - a role that changes interpretation may not fall to inherited-only while the sentence still reads as a
  result, conclusion or observation.

The second is the one Attempt 5 violated. Keeping design_constraint in an ancestry field while the sentence reads
as a deficiency preserves provenance and still misleads the reader.

Fixtures are built from the real transition wherever possible, and from neutral synthetic chains elsewhere. Scoring
is on role survival, never on textual similarity: rewriting "Architecture specifies" as "By design" is success.

    python tools/v2735_1_0_semantic_role_tests.py
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

# The real merge, verbatim from the frozen baseline.
GS151 = "Run completed with 192 calls; gates failed unsafe use (3/12) but passed primary (0/42)."
GS154 = "Architecture specifies model does not emit operational labels like 'use', 'investigate', or 'abstain'."
GS201 = ("Gates failed unsafe use (3/12) but passed primary (0/42); model does not emit operational labels like "
         "'use' or 'abstain'.")


def require(condition: bool, name: str) -> None:
    CHECKS.append((name, bool(condition)))


def sources(**roles):
    return {key: {"direct_roles": list(value), "inherited_roles": []} for key, value in roles.items()}


def judge(text, proposed, items):
    settled = hier.assign_roles(proposed, list(items), items)
    return settled, hier.role_fidelity(text, settled["direct_roles"], settled["role_lineage"])


def main() -> int:
    # --- 1. the vocabulary is closed ----------------------------------------------------------------------------
    require(len(hier.SEMANTIC_ROLES) == 10, "the_role_vocabulary_is_small")
    require("design_constraint" in hier.SEMANTIC_ROLES and "measured_result" in hier.SEMANTIC_ROLES,
            "the_two_roles_the_defect_confused_both_exist")
    require(hier.valid_roles(["architectural_observation_constraintish"]) == [],
            "an_invented_label_is_discarded_not_accepted")
    require(hier.valid_roles("design_constraint") == ["design_constraint"], "a_single_label_is_accepted")
    require(hier.valid_roles(None) == [] and hier.valid_roles(42) == [], "nonsense_proposals_yield_no_roles")

    # --- 2. the real case, all three outcomes -------------------------------------------------------------------
    items = sources(GSa=["measured_result"], GSb=["design_constraint"])

    settled, verdict = judge(GS201, ["measured_result"], items)
    require(not verdict["ok"], "the_attempt5_merge_is_refused")
    require(verdict["reason"] == "role_fidelity_lost", "and_refused_for_losing_the_role")
    require(verdict["roles_missing_from_prose"] == ["design_constraint"], "the_refusal_names_the_lost_role")
    require(settled["inherited_roles"] == ["design_constraint"],
            "the_role_is_still_traceable_even_though_the_statement_is_refused")
    require(settled["role_lineage"]["design_constraint"] == ["GSb"], "and_points_at_the_input_that_carried_it")

    kept_framing = ("By design the model does not emit operational labels; gates failed unsafe use (3/12) but "
                    "passed primary (0/42).")
    settled, verdict = judge(kept_framing, ["measured_result"], items)
    require(verdict["ok"], "prose_that_keeps_the_framing_is_accepted")
    require(verdict["promoted"] == ["design_constraint"], "the_missing_label_is_promoted_deterministically")
    require(verdict["role_promotion"] == "deterministic_required", "and_says_governance_did_it")

    declared = "Architecture specifies no operational labels; gates failed unsafe use (3/12)."
    settled, verdict = judge(declared, ["measured_result", "design_constraint"], items)
    require(verdict["ok"] and not verdict["promoted"], "a_statement_that_declares_both_roles_needs_no_repair")
    require(settled["direct_roles"] == ["design_constraint", "measured_result"], "and_claims_both_directly")

    # wording is free as long as the role survives
    for phrasing in ("By design, no operational labels are emitted; 3/12 diagnostics failed.",
                     "The contract prohibits operational labels; 3/12 diagnostics failed.",
                     "The model is intentionally constrained from emitting labels; 3/12 failed."):
        _, v = judge(phrasing, ["measured_result"], items)
        require(v["ok"], f"rewording_is_not_penalised__{phrasing.split()[1][:12]}")

    # --- 3. the transition table --------------------------------------------------------------------------------
    table = [
        ("design_constraint", "measured_result", "The model does not emit labels and 3/12 gates failed."),
        ("uncertainty", "conclusion", "The run establishes that repetition removes correlated error."),
        ("limitation", "conclusion", "Repeated assessment eliminates unsafe use."),
        ("contradiction", "measured_result", "All records agree on the relation and disposition."),
        ("minority_finding", "conclusion", "Every case followed the same disposition."),
        ("hypothesis", "measured_result", "Correlated error is caused by shared model priors."),
    ]
    for critical, other, flattening_text in table:
        pair = sources(A=[other], B=[critical])
        _, v = judge(flattening_text, [other], pair)
        require(not v["ok"], f"{critical}_may_not_be_demoted_beside_{other}")
        require(critical in v["roles_missing_from_prose"], f"{critical}_is_named_in_the_refusal")

    # --- 3b. an inherited conflict counts, when the sentence asserts something settled ---------------------------
    # G-SYNTH1's single genuine live merge slipped through here: minority_finding was demoted while the role it
    # conflicts with, conclusion, had itself been demoted to inherited, so nothing fired. Being flattened together
    # is no safer than being flattened under a directly claimed role.
    live = {"DS1": {"direct_roles": ["measured_result"], "inherited_roles": []},
            "DS2": {"direct_roles": ["minority_finding"], "inherited_roles": ["conclusion"]}}
    settled = hier.assign_roles(["measured_result"], list(live), live)
    kept = ("Dispositions were consistent across the corpus, with one item out of thirty-two producing a unique "
            "disposition.")
    v = hier.role_fidelity(kept, settled["direct_roles"], settled["role_lineage"], settled["inherited_roles"])
    require(v["ok"] and v["promoted"] == ["minority_finding"],
            "an_inherited_conflict_triggers_the_check_and_prose_that_kept_the_fact_is_promoted")
    v = hier.role_fidelity("Dispositions were consistent across the corpus.", settled["direct_roles"],
                           settled["role_lineage"], settled["inherited_roles"])
    require(not v["ok"] and v["roles_missing_from_prose"] == ["minority_finding"],
            "the_same_merge_with_the_qualifier_stripped_is_refused")
    # Widening the table later subsumed the inherited path for most roles - any assertive role they are claimed
    # beside is now in their conflict set, so the direct check catches it first. It stays load-bearing for
    # uncertainty, whose conflicts deliberately exclude observation: there, only the inherited reading fires.
    narrow = {"A": {"direct_roles": ["observation"], "inherited_roles": ["conclusion", "uncertainty"]}}
    s_narrow = hier.assign_roles(["observation"], ["A"], narrow)
    flat = "Item T04 contradicted its evidence."
    require(hier.role_fidelity(flat, s_narrow["direct_roles"], s_narrow["role_lineage"])["roles_required_direct"]
            == [], "a_direct_only_reading_misses_a_conflict_that_is_itself_inherited")
    require("uncertainty" in hier.role_fidelity(flat, s_narrow["direct_roles"], s_narrow["role_lineage"],
                                                s_narrow["inherited_roles"])["roles_required_direct"],
            "the_inherited_reading_still_catches_it")

    # relevance: an inherited conflict matters only when the sentence asserts something settled
    procedural = {"A": {"direct_roles": ["procedure"], "inherited_roles": ["design_constraint", "measured_result"]}}
    s2 = hier.assign_roles(["procedure"], ["A"], procedural)
    v = hier.role_fidelity("Records were read in fixed order.", s2["direct_roles"], s2["role_lineage"],
                           s2["inherited_roles"])
    require(v["ok"] and not v["promoted"], "a_purely_procedural_statement_is_not_refused_for_its_ancestry")
    asserted = {"A": {"direct_roles": ["observation"], "inherited_roles": ["uncertainty", "conclusion"]}}
    s3 = hier.assign_roles(["observation"], ["A"], asserted)
    v = hier.role_fidelity("Item T04 contradicted its evidence.", s3["direct_roles"], s3["role_lineage"],
                           s3["inherited_roles"])
    require(not v["ok"], "asserting_a_fact_while_its_uncertainty_was_demoted_is_refused")
    require(hier.ASSERTIVE_ROLES == ("measured_result", "conclusion", "observation"),
            "the_assertive_roles_are_named_explicitly")

    # --- 3c. the three merges G-SYNTH1-R2 actually produced, verbatim -------------------------------------------
    # Every one of these is a real live sentence from the R2 run, kept exactly as the model wrote it. Two exposed
    # gaps that the table and the lexicon have since been widened to close; the third is a known limit of a marker
    # check and is recorded as such rather than papered over.
    live_cases = [
        ("contradiction_expressed_as_opposite_relations",
         {"DS2": {"direct_roles": ["contradiction"], "inherited_roles": []},
          "DS3": {"direct_roles": ["observation"], "inherited_roles": []},
          "DS4": {"direct_roles": ["procedure"], "inherited_roles": []}},
         ["measured_result", "procedure"],
         "Records T07-r1 and T07-r2 report opposite relations for the same evidence, while both cited two spans "
         "and were read in fixed order.",
         "promoted", "contradiction"),
        ("minority_finding_written_with_a_numeral",
         {"DS1": {"direct_roles": ["measured_result"], "inherited_roles": []},
          "DS2": {"direct_roles": ["minority_finding"], "inherited_roles": []}},
         ["measured_result"],
         "29/32 items had identical dispositions; 1 item produced a unique disposition (DS1, DS2).",
         "promoted", "minority_finding"),
        ("limitation_expressed_only_as_a_quantity",
         {"DS1": {"direct_roles": ["measured_result"], "inherited_roles": []},
          "DS2": {"direct_roles": ["limitation"], "inherited_roles": []},
          "DS3": {"direct_roles": ["observation"], "inherited_roles": []},
          "DS4": {"direct_roles": ["procedure"], "inherited_roles": []}},
         ["measured_result", "procedure"],
         "Correlated error was observed in three items, which were drawn from a pool of twelve ambiguous items "
         "examined after the primary scoring pass.",
         "refused", "limitation"),
    ]
    for name, items_map, proposed, text, expected, role in live_cases:
        settled_live = hier.assign_roles(proposed, list(items_map), items_map)
        v = hier.role_fidelity(text, settled_live["direct_roles"], settled_live["role_lineage"],
                               settled_live["inherited_roles"])
        require(role in v["roles_required_direct"], f"{name}__is_challenged_at_all")
        if expected == "promoted":
            require(v["ok"] and role in v["promoted"], f"{name}__is_promoted")
            require(v["promotion_markers"].get(role), f"{name}__reports_the_marker_that_triggered_it")
        else:
            require(not v["ok"] and role in v["roles_missing_from_prose"], f"{name}__is_refused")

    require("opposite" in hier.ROLE_MARKERS["contradiction"], "opposite_is_a_contradiction_marker")
    require("1 item" in hier.ROLE_MARKERS["minority_finding"], "a_numeral_minority_is_matched")
    for role in ("minority_finding", "limitation", "hypothesis"):
        require("measured_result" in hier.DEMOTION_FORBIDDEN_WITH[role],
                f"{role}_is_challenged_under_a_measured_result")
        require("observation" in hier.DEMOTION_FORBIDDEN_WITH[role],
                f"{role}_is_challenged_under_an_observation")
    require(hier.matched_markers("nothing here", "contradiction") == [],
            "a_sentence_with_no_marker_reports_none")

    # --- 4. what the table must NOT do ---------------------------------------------------------------------------
    # ordinary ancestry is allowed to be inherited
    deep = {"A": {"direct_roles": ["conclusion"], "inherited_roles": ["procedure", "observation"]}}
    settled, v = judge("The experiment concludes that coverage was complete.", ["conclusion"], deep)
    require(v["ok"], "ordinary_inherited_ancestry_is_not_a_fidelity_failure")
    require("procedure" in settled["inherited_roles"], "and_remains_traceable")

    # a role the sources never carried is never required
    plain = sources(A=["measured_result"])
    _, v = judge("Gates failed unsafe use in 3 of 12 cases.", ["measured_result"], plain)
    require(v["ok"] and v["roles_required_direct"] == [], "a_role_no_source_carried_is_never_demanded")

    # same-role inputs are a control: nothing to lose, nothing to flag
    same = sources(A=["measured_result"], B=["measured_result"])
    _, v = judge("Gates failed 3/12 and passed 0/42.", ["measured_result"], same)
    require(v["ok"] and not v["promoted"], "merging_same_role_inputs_requires_no_repair")

    # --- 5. no union inflation -----------------------------------------------------------------------------------
    many = {"A": {"direct_roles": ["limitation"], "inherited_roles": ["uncertainty", "hypothesis"]},
            "B": {"direct_roles": ["measured_result"], "inherited_roles": ["contradiction", "procedure"]}}
    settled = hier.assign_roles(["conclusion"], ["A", "B"], many)
    require(settled["direct_roles"] == ["conclusion"], "a_statement_claims_only_what_it_expresses")
    ancestry = {r for v in many.values() for r in v["direct_roles"] + v["inherited_roles"]}
    require(set(settled["inherited_roles"]) == ancestry - set(settled["direct_roles"]),
            "everything_its_ancestry_carried_stays_traceable")
    require(set(settled["role_lineage"]) >= set(settled["inherited_roles"]), "and_every_role_names_its_source")

    # --- 6. inheritance when the model says nothing ---------------------------------------------------------------
    settled = hier.assign_roles(None, ["GSa", "GSb"], items)
    require(settled["direct_roles"] == ["design_constraint", "measured_result"],
            "a_statement_proposing_nothing_inherits_its_sources_roles")
    require(settled["proposed_roles"] == [], "and_records_that_the_model_proposed_nothing")
    settled = hier.assign_roles(["not_a_role"], ["GSa", "GSb"], items)
    require(settled["direct_roles"] == ["design_constraint", "measured_result"],
            "an_entirely_invalid_proposal_falls_back_to_inheritance")

    # --- 7. end to end: a real review still runs, and roles reach the artifact ------------------------------------
    with tempfile.TemporaryDirectory(prefix="v2735-roles-") as tmp:
        work = Path(tmp)
        pkg = work / "pkg"
        q.build_package(pkg, 16)
        runtime = work / "rt"
        runtime.mkdir(parents=True, exist_ok=True)
        art = hier.review_experiment(pkg, call_model=q.deterministic_stub(), runtime_root_path=runtime,
                                     identity=IDENTITY, release_model=False)
        require(art["status"] == "complete", "a_whole_review_still_completes_with_roles_enforced")
        require(art["coverage"]["required_coverage"] == 1.0, "coverage_is_unaffected")
        statements = art["hierarchy"]["part_statements"] + art["hierarchy"]["document_statements"]
        require(statements, "the_review_produced_statements")
        for s in statements:
            require(isinstance(s.get("direct_roles"), list) and s["direct_roles"],
                    f"{s['id']}_claims_at_least_one_role")
            require(set(s["direct_roles"]) <= set(hier.SEMANTIC_ROLES), f"{s['id']}_only_claims_known_roles")
            require(set(s.get("inherited_roles") or []) <= set(hier.SEMANTIC_ROLES),
                    f"{s['id']}_only_inherits_known_roles")
            require(not (set(s["direct_roles"]) & set(s.get("inherited_roles") or [])),
                    f"{s['id']}_does_not_both_claim_and_inherit_a_role")
        # no role is lost anywhere in the hierarchy
        by_id = {s["id"]: s for s in statements}
        lost = []
        for s in statements:
            carried = set(s["direct_roles"]) | set(s.get("inherited_roles") or [])
            for cite in s.get("cites") or []:
                parent = by_id.get(cite)
                if parent:
                    missing = (set(parent["direct_roles"]) | set(parent.get("inherited_roles") or [])) - carried
                    if missing:
                        lost.append((s["id"], cite, sorted(missing)))
        require(not lost, "no_role_disappears_between_a_statement_and_its_sources")

    # --- 8. nothing else moved -------------------------------------------------------------------------------------
    require(hier.CONTRACT_VERSION == "v2735.0", "the_work_carries_the_new_contract_version")
    require(base.CONTRACT_VERSION == "v2731.8", "the_frozen_baseline_is_unchanged")
    require(hier.MIN_REDUCTION == 0.80, "the_reduction_floor_is_untouched")
    require(base.MAX_QUOTE_CHARS == 240, "quote_limits_are_untouched")

    failed = [name for name, ok in CHECKS if not ok]
    print(json.dumps({"suite": "v2735.1.0-semantic-role", "checks": len(CHECKS),
                      "passed": len(CHECKS) - len(failed), "failed": failed[:14]}, indent=1))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
